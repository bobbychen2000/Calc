// Contact-gate equipment driven by live occupancy:
//  - apron-drive passenger boarding bridges (PBB) built from the stand data (data/sfo_stands.json, OSM + NAIP; fields in
//    docs/research/stands_rebuild.md §8): fixed walkway along the mapped polyline (walkW) on columns, rotunda on its
//    pedestal at the mapped rotunda (rotundaW, drum radius <= rotundaMaxR), rotunda corridor, two or three TELESCOPING
//    tunnel sections (they slide inside each other; lengths fixed, only their overlap changes), drive column with wheel
//    bogie on the outer tunnel, pre-conditioned-air unit, cab bubble with the rotating cab, bellows closure, service
//    landing + stair, floodlight, beacon, gate-number signs on the tunnel
//  - stand equipment: gate identification sign and visual docking guidance display (VDGS), placed on the stand
//    centreline where no bridge part reaches it in any pose (rest, docking path, docked); on the terminal face only
//    where a pier / hall wall stands behind it, else on its own post
//  - ground service vehicles placed around the actually parked aircraft (belt loaders on the cargo-door sills of the
//    737 / A320 families: the fitted model's own door / the published sill, at the rendered skin), their mesh hulls
//    sampled against the aircraft (the rendered, pitched fuselage skin - js/aircraft/fit.js keelAt / skinHW - and the
//    elliptical section, wings, engines, tail), the neighbouring aircraft, the bridges' real solids, the terminal and each
//    other
//
// Bridge kinematics (sources):
//  * Oshkosh AeroTech, "Jetway Glass & Steel Truss Passenger Boarding Bridges" sell sheet (2025), cached
//    refs/cache/pbb/oshkosh_jetway_steelglass_2025.pdf (+ .txt; https://oshkoshaerotech.com/hubfs/images/Jetway%20SteelGlass_
//    Truss_Sell-Sheet_2025.pdf): models AT2 (two tunnels) / AT3 (three tunnels) "41/55" ... "72/150"; fully retracted /
//    fully extended lengths "from the center of the rotunda to the end of the cab spacer", operational retraction /
//    extension "from the center of the rotunda to the center of the cab pivot" (table PBB below); rotunda swing 175 deg
//    (87.5 cw / 87.5 ccw of centerline); cab rotation 125 deg (92.5 cw / 32.5 ccw), "optional 185 deg available" (no
//    cw / ccw split given); cab rotation speed 145 deg/min; "Vertical rate of travel/lift 3.5'/min (1.09 m/min)";
//    "Horizontal rate of travel 0 to 90'/min (0-27 m/min)" - the sheet names no reference point, so every path keeps
//    the cab pivot, the fastest point of the horizontal drive (it is further out than the drive column), at or under
//    27 m/min at every instant (segPeak: each segment is timed by its peak, not its mean speed); service door,
//    landing and stairs: option C/D "right/left-hand side of outboard telescoping tunnel aft of cab bubble"; minimum
//    interior cab width 3.10 m. Pivot -> end of cab spacer = fully retracted - operational retraction (2.378 m AT2,
//    2.225 m AT3). Which bridge model each SFO bridge is (`model`, `ext_range`) is the stand data's inference.
//  * FAA AC 150/5220-21C "Aircraft Boarding Equipment" (2012), cached refs/cache/pbb/AC_150_5220-21C.pdf (public domain,
//    https://www.faa.gov/documentLibrary/media/Advisory_Circular/150_5220_21c.pdf): §3.3.b
//    "telescoping tunnels ... rectangular in cross section, with the largest cross section located closest to the
//    aircraft"; §3.4.b(1)(a)(ii) cab rotation 0-4 deg/s; §3.4.h(2)(a) vertical pre-positioning before the aircraft
//    arrives; slopes §2.2.d(3)(b) / Figure 6: recommended 1:16-1:20, max 1:12 for unassisted access, 1:8 for runs of
//    5 ft or less, 1:4 for assisted access ("the level landing requirement does not apply ... to PBBs"); §3.4.b(6): a
//    PBB that must slope more than 1:4 needs a ramp mated to it. So 1:12 is the design target (warned), 1:4 the limit
//    beyond which this model does not dock (the bridge stays at rest).
//  * Docking sequence (engine contract, docs/requests/realtime_round1.md): setOccupant(g, type, animate, now, pose) once
//    the drawn aircraft is at rest; the bridge pre-positions its height, drives (tunnel swing + telescoping + cab turn)
//    to a stand-off point 1.5 m out on the door normal, then creeps in to the door; setOccupant(g, null) retracts along
//    the same path (back off on the door normal first). The joint path is checked against the parked aircraft; if the
//    direct path would pass through it, a retract-swing-extend path is used, and if none is clear the bridge stays at
//    rest. Departures (engine API, docs/requests/bridges_closeout.md "Round 2 API for realtime"): the real bridge is
//    retracted before the push-back, so the engine starts it on its earliest departure signal with undockEarly(g, now)
//    (the sheet's rates, the aircraft stays on the stand; redock(g, now) undoes a false signal); a departure seen only
//    once the push has begun gets hurryUndock(g, s, now) (the sheet's maximum rates, 16-91 s from docked - never squeezed). The
//    engine reads pushClearEta(g, now) (seconds until every bridge is clear of the aircraft's straight push-back: the cab
//    backed off the door: from docked at the maximum rates p50 1.0 s, p99 4.7 s, max 25 s - F13 A333 / A339, F15 B779 - over
//    2,883 stand x type dockings) and undockEta(g, now) (seconds until the tunnels are back at
//    rest, extension(g) 0); it does not have to hold the body for the full retraction. Any docking requested while the
//    bridges are not at rest (the same aircraft back, another pose, another aircraft) goes on from where each bridge is
//    (setOccupant -> dockFrom: no jump; review round 2 v5), every leg - back to rest too - tested against the NEW
//    occupant (close-out round 3); send setOccupant(g, null) before a different occupant (the real bridge retracts first).
//  * Rest pose: the data's `stowW` (tunnel end = cab pivot at rest, clear of every accepted type's envelope + 1 m, of
//    the other bridges at rest and docked, of the building; cab straight on the tunnel). After an undocking the cab
//    settles from the door's height to the rest height (rest tunnel <= 1:12) at the sheet's lift rate. Per occupant
//    (close-out round 7, PARK_*): a bridge that does not dock the aircraft at its stand or at a stand around it parks
//    retracted / swung where its data rest is inside that aircraft's ICAO stand clearance (wing, engines, tailplane) or
//    its straight push-back, and returns PARK_RETURN_S after the departure. The engine sees the parked pose through
//    pose() / solids(g, b, 0); the setOccupant() contract is unchanged (the park starts with it: the aircraft is at rest).
//  * Solid-body rules (review 2026-11-04): the drum is at least DRUM_MIN (1.5 m) - the corridor it carries is 2.4 m wide -
//    with the rotunda moved off a neighbour's walkway / drum / the outline (the drawn terminal AND the SFO Museum
//    footprints the 3-D building assets are built from, except the bridge's own walkway strip in them: ownStrip) by the
//    deficit (<= 2 m) - a guard only: the stand data carries the moves of review orch-1 (static patch_stands P6) and
//    today no rotunda is moved; no moving part ever enters those outlines or a sky bridge (bldHit, exact); the rotunda
//    corridor, tunnels, drive column and cab never pass through another bridge's fixed walkway, drum or pedestal, nor
//    any moving part through the bridge's own fixed walkway (jointOk / pathHits: such dockings stay at rest; the corridor
//    starts where it leaves that walkway, neckParts);
//    twin heads (a walkway through one rotunda to a second 3.4 m on: F15, G12) share one floor level.
//  * Fast retraction for a departing aircraft: hurryUndock(g, s, now) - the same path at the sheet's maximum rates.
//  * Upper-deck bridges (`bridges_upper`, A6 / A11 / G13) dock the A380's U1L door: Airbus A380 Aircraft
//    Characteristics (AC380, Dec 01/25, refs/cache/acap/airbus_AC_A380_20251201.pdf): U1L 20.94 m from the nose
//    (FIGURE-2-7-0-991-002), sill 7.87-7.89 m at MRW (FIGURE-2-3-0-991-001).
// Inferred (no source; stated where used): the bridge level of BA-A / BA-B / BA-C (DEPARTURE_LEVELS: per pier, BA-G and
// BA-D measured on photos, T3 published), tunnel overlaps (1.0 m) and retracted stagger (0.3 m), drive-column
// position on the outer tunnel, final approach speed, section cross-sections (inside the AC's minimum interior sizes).
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { rng, m4, v3 } from '../math.js';
import { stToWorld, worldToST, GROUND_Y } from '../geo.js';
import { TYPES, ICAO_TYPES } from '../aircraft/types.js';
import '../aircraft/fit.js'; // fits the imported models to the published dimensions: T.dockX1/2, T.dockSill/2, T.dockHW
import { bellowsShape, bellowsGeo } from '../aircraft/dock.js'; // the bellows closure fitted to the drawn fuselage skin
import { inst, buildVehicleMeshes, beltShape, beltFamily, beltDoor, beltEndY, BELT_RAIL_GAP, cateringFloor, cateringBoxes } from '../world/gates.js';
import { makeAtlas } from './signs.js';
import { familyOf } from './traffic.js';
import { STANDS } from '../../data/sfo_stands.js';
import { BUILDINGS } from '../../data/sfo_buildings.js';
import { AIRPORT } from '../../data/sfo_airport.js';
import { B3D_INTEGRATION } from '../../data/buildings3d/integration.js'; // 3-D asset footprints (VDGS brackets)

// terminal outlines the bridges must stay out of: ramp-level complex and the piers / halls (js/live/terminals.js builds
// them from these rings; the elevated sky-bridge walkways are left out - fixed walkways run under / beside them)
const BLD = [], BLD_H = []; // (BLD_H: wall top above the apron - ramp-level complex 5 m, piers / halls their roof h)
for (const r of (BUILDINGS && BUILDINGS.complex) || []) { BLD.push(r); BLD_H.push(5.0); }
for (const p of (BUILDINGS && BUILDINGS.parts) || []) if (p.kind !== 'walkway') for (const r of p.rings) { BLD.push(r); BLD_H.push(p.h || 5.0); }
const NBLD = BLD.length; // (the outline js/live/terminals.js draws: the fixed walkway starts where it leaves it)
// + the SFO Museum terminal-complex and boarding-area outlines (data/sfo_airport.js, outer rings) as CLEARANCE outlines:
// the 3-D building assets draw the piers from them (data/buildings3d/manifest.json itb: "SFO Museum Boarding Area A /
// G") and tools/stands/check_stands.py tests against them; near the facades they reach up to ~2.3 m (A10) and at the
// B-pier tip ~20 m beyond the sfo_buildings rings. A bridge clears every outline a renderer may draw (review orch-1:
// A10 L1's drum stood 1.2 m inside Boarding Area A, its docked corridor 0.3 m2; 40 drums overlapped these outlines)
for (const P of (AIRPORT && AIRPORT.terminalComplex) || []) { BLD.push(P[0]); BLD_H.push(0); }
for (const ba of (AIRPORT && AIRPORT.boardingAreas) || []) for (const P of ba.polys) { BLD.push(P[0]); BLD_H.push(0); }
const NCL = BLD.length; // + the elevated sky bridges (only for the rotunda drum, which reaches their height)
for (const p of (BUILDINGS && BUILDINGS.parts) || []) if (p.kind === 'walkway') for (const r of p.rings) BLD.push(r);
const BLD_BB = BLD.map(r => { let a = 1e9, b = 1e9, c = -1e9, d = -1e9; for (const p of r) { a = Math.min(a, p[0]); c = Math.max(c, p[0]); b = Math.min(b, p[1]); d = Math.max(d, p[1]); } return [a, b, c, d]; });
// edge index of every outline (exact tests, no sampling; the SFO Museum rings made the sampled tests ~35x slower - the
// app's start-up and every docking plan): EC m grid cells -> [ring k, ax, az, bx, bz]; per ring, its edges in EZ m bands
// of z (point-in-ring tests only cross the band's edges)
const EC = 8, EZ = 4, ECELL = new Map(), EBAND = BLD.map(() => new Map());
BLD.forEach((r, k) => { for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[j], b = r[i]; const e = [k, a[0], a[1], b[0], b[1]];
  for (let cx = Math.floor(Math.min(a[0], b[0]) / EC); cx <= Math.floor(Math.max(a[0], b[0]) / EC); cx++) for (let cz = Math.floor(Math.min(a[1], b[1]) / EC); cz <= Math.floor(Math.max(a[1], b[1]) / EC); cz++) { const key = cx * 65536 + cz; let L = ECELL.get(key); if (!L) ECELL.set(key, L = []); L.push(e); }
  for (let bz = Math.floor(Math.min(a[1], b[1]) / EZ); bz <= Math.floor(Math.max(a[1], b[1]) / EZ); bz++) { let L = EBAND[k].get(bz); if (!L) EBAND[k].set(bz, L = []); L.push(e); } } });
function inRingK(x, z, k) { const L = EBAND[k].get(Math.floor(z / EZ)); if (!L) return false; let c = false; for (const e of L) if (((e[2] > z) !== (e[4] > z)) && (x < (e[3] - e[1]) * (z - e[2]) / (e[4] - e[2]) + e[1])) c = !c; return c; }
// inside a building: the clearance outlines (drawn + SFO Museum); all: + the sky bridges; drawn: only what
// js/live/terminals.js draws (the fixed walkway's start / interior vertices); ex: a bridge's own-strip test (b._strip,
// ownStrip below) - a point in a Museum ring that is that bridge's own walkway strip is not inside
const isMus = (k) => k >= NBLD && k < NCL;
function inBuilding(x, z, all = false, drawn = false, ex = null) { const n = drawn ? NBLD : all ? BLD.length : NCL; for (let i = 0; i < n; i++) { const bb = BLD_BB[i]; if (x < bb[0] || x > bb[2] || z < bb[1] || z > bb[3]) continue; if (inRingK(x, z, i) && !(ex && isMus(i) && ex.inStrip(x, z, i))) return true; } return false; }
// nearest outline point within 24 m incl. the sky bridges (drawn: terminals.js outline only): {d (0 inside; 1e9 and p
// null when nothing is that near), p, inside} - every caller asks about clearances of a few metres
function nearestBuilding(x, z, drawn = false, own = null, noMus = false) { // (own: a bridge's own-strip test - its strip edges are skipped; noMus: no SFO Museum edges)
  let d = 1e9, P = null; const n = drawn ? NBLD : BLD.length; const R = 3, c0 = Math.floor(x / EC), r0 = Math.floor(z / EC);
  for (let cx = c0 - R; cx <= c0 + R; cx++) for (let cz = r0 - R; cz <= r0 + R; cz++) { const L = ECELL.get(cx * 65536 + cz); if (!L) continue;
    for (const e of L) { if (e[0] >= n || (own && own.edges.has(e)) || (noMus && isMus(e[0]))) continue; const ex = e[3] - e[1], ez = e[4] - e[2]; const L2 = ex * ex + ez * ez || 1; const t = clampN(((x - e[1]) * ex + (z - e[2]) * ez) / L2, 0, 1); const qx = e[1] + ex * t, qz = e[2] + ez * t; const dd = Math.hypot(qx - x, qz - z); if (dd < d) { d = dd; P = [qx, qz]; } } }
  let inside = false; if (noMus) { for (let k = 0; k < n && !inside; k++) { if (isMus(k)) continue; const bb = BLD_BB[k]; if (x >= bb[0] && x <= bb[2] && z >= bb[1] && z <= bb[3] && inRingK(x, z, k)) inside = true; } }
  else inside = inBuilding(x, z, !drawn, drawn, own);
  return { d: inside ? 0 : d, p: P, inside };
}
// a moving bridge part (solid {c, u, hl, hw, lo, hi}) inside a building: the clearance outlines (any height below their
// roofs - every bridge part is) or a sky bridge it reaches up to (BUILDINGS walkway parts y0..h above the apron). Exact:
// the box (less 5 cm all round) meets a ring when an outline edge crosses it or its centre lies in the ring
const SKY_Y = []; for (const p of (BUILDINGS && BUILDINGS.parts) || []) if (p.kind === 'walkway') for (const r of p.rings) SKY_Y.push([p.y0 ?? 6, p.h ?? 10.5]);
function segInBox(e, bx, hl, hw) { // Liang-Barsky clip of edge e in the box frame
  const ax = e[1] - bx.c[0], az = e[2] - bx.c[1], bxx = e[3] - bx.c[0], bz = e[4] - bx.c[1];
  const x0 = ax * bx.u[0] + az * bx.u[1], y0 = -ax * bx.u[1] + az * bx.u[0], x1 = bxx * bx.u[0] + bz * bx.u[1], y1 = -bxx * bx.u[1] + bz * bx.u[0];
  let t0 = 0, t1 = 1; const dx = x1 - x0, dy = y1 - y0;
  for (const [p, q] of [[-dx, x0 + hl], [dx, hl - x0], [-dy, y0 + hw], [dy, hw - y0]]) { if (Math.abs(p) < 1e-12) { if (q < 0) return false; continue; } const r = q / p; if (p < 0) { if (r > t1) return false; if (r > t0) t0 = r; } else { if (r < t0) return false; if (r < t1) t1 = r; } }
  return t0 <= t1;
}
// (own: a bridge's own-strip test - a moving part over its own walkway's Museum strip is tested against the walkway slab
// itself, fixedHit; the strip's edges and a centre inside the strip do not count)
function solidInBuilding(bx, own = null) {
  const v = [-bx.u[1], bx.u[0]]; const hl = Math.max(0.01, bx.hl - 0.05), hw = Math.max(0.01, bx.hw - 0.05);
  const ex = Math.abs(bx.u[0]) * hl + Math.abs(v[0]) * hw, ez = Math.abs(bx.u[1]) * hl + Math.abs(v[1]) * hw;
  const ok = (k) => { if (k < NCL) return true; const [y0, y1] = SKY_Y[k - NCL]; return bx.hi > G + y0 && bx.lo < G + y1; };
  let any = false;
  for (let k = 0; k < BLD.length; k++) { const bb = BLD_BB[k]; if (bx.c[0] + ex < bb[0] || bx.c[0] - ex > bb[2] || bx.c[1] + ez < bb[1] || bx.c[1] - ez > bb[3] || !ok(k)) continue;
    any = true; if (!inRingK(bx.c[0], bx.c[1], k)) continue;
    if (!(own && isMus(k) && own.inStrip(bx.c[0], bx.c[1], k))) return true;
    // (centre in the own strip: no edge separates the strip from the rest of the ring, so the corners are tested too)
    for (const [i, j] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) { const x = bx.c[0] + bx.u[0] * hl * i + v[0] * hw * j, z = bx.c[1] + bx.u[1] * hl * i + v[1] * hw * j; if (inRingK(x, z, k) && !own.inStrip(x, z, k)) return true; } }
  if (!any) return false;
  for (let cx = Math.floor((bx.c[0] - ex) / EC); cx <= Math.floor((bx.c[0] + ex) / EC); cx++) for (let cz = Math.floor((bx.c[1] - ez) / EC); cz <= Math.floor((bx.c[1] + ez) / EC); cz++) {
    const L = ECELL.get(cx * 65536 + cz); if (!L) continue;
    for (const e of L) if (ok(e[0]) && !(own && own.edges.has(e)) && segInBox(e, bx, hl, hw)) return true; }
  return false;
}
// the 3-D building assets' footprints (data/buildings3d/integration.js B3D_INTEGRATION.physics: plan rings [[outer, hole...]]
// of the LOD0 assets, 0.1 m): the VDGS wall bracket (vdgsSpot) - the plan face is what it reaches for
const ASSET = ((B3D_INTEGRATION && B3D_INTEGRATION.physics && B3D_INTEGRATION.physics.rings) || []).map(P => { let a = 1e9, b = 1e9, c = -1e9, d = -1e9; for (const p of P[0]) { a = Math.min(a, p[0]); c = Math.max(c, p[0]); b = Math.min(b, p[1]); d = Math.max(d, p[1]); } return { P, bb: [a, b, c, d] }; });
const inRingXZ = (x, z, r) => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[i], b = r[j]; if (((a[1] > z) !== (b[1] > z)) && (x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0])) c = !c; } return c; };
function inAsset(x, z) { for (const A of ASSET) { if (x < A.bb[0] || x > A.bb[2] || z < A.bb[1] || z > A.bb[3]) continue; let c = false; for (const r of A.P) if (inRingXZ(x, z, r)) c = !c; if (c) return true; } return false; }
// ... and WITH their height bands (B3D_INTEGRATION.footprints.units[group][unit].tiers: part 'body' from grade to its top or
// 'over' from an overhang's underside to its top, world y, rings [[outer, hole...]] grown by the ring tolerance so that every
// LOD0 / LOD1 vertex lies inside - integration-5, close-out round 3 r22): a moving bridge part may not enter a 3-D asset at
// its height (bldHit; close-out round 5, bridges-6 - before, only the plan-only SFO Museum proxy below stood for the
// assets). The Museum proxy, the own-walkway strip and the walkway start at the drawn outline stay until the switch the
// buildings track rebuilds with (docs/requests/bridges_closeout.md R5.3): both renderers share these bridges, and the
// walkway length sets the rotunda floors (1:12 band)
const TIERS = [], TIER_CELL = 40, TIER_GRID = new Map(), TIER_EC = new Map(); { const U = (B3D_INTEGRATION && B3D_INTEGRATION.footprints && B3D_INTEGRATION.footprints.units) || {};
  for (const grp in U) for (const unit in U[grp]) for (const t of (U[grp][unit].tiers || [])) for (const P of (t.rings || [])) {
    if (!P || !P[0] || P[0].length < 3) continue; let a = 1e9, b = 1e9, c = -1e9, d = -1e9; for (const p of P[0]) { a = Math.min(a, p[0]); c = Math.max(c, p[0]); b = Math.min(b, p[1]); d = Math.max(d, p[1]); }
    const T = { y0: t.y[0], y1: t.y[1], bb: [a, b, c, d], band: new Map(), tag: grp + '/' + unit + ':' + t.part, k: TIERS.length }; TIERS.push(T);
    for (let cx = Math.floor(a / TIER_CELL); cx <= Math.floor(c / TIER_CELL); cx++) for (let cz = Math.floor(b / TIER_CELL); cz <= Math.floor(d / TIER_CELL); cz++) { const key = cx * 65536 + cz; let L = TIER_GRID.get(key); if (!L) TIER_GRID.set(key, L = []); L.push(T); }
    // (edges in EC-m cells for the box test, and per tier in EZ-m bands of z for the point-in-ring test, as the outlines above)
    for (const r of P) for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const A = r[j], B = r[i]; const e = [T.k, A[0], A[1], B[0], B[1]];
      for (let cx = Math.floor(Math.min(A[0], B[0]) / EC); cx <= Math.floor(Math.max(A[0], B[0]) / EC); cx++) for (let cz = Math.floor(Math.min(A[1], B[1]) / EC); cz <= Math.floor(Math.max(A[1], B[1]) / EC); cz++) { const key = cx * 65536 + cz; let L = TIER_EC.get(key); if (!L) TIER_EC.set(key, L = []); L.push(e); }
      for (let bz = Math.floor(Math.min(A[1], B[1]) / EZ); bz <= Math.floor(Math.max(A[1], B[1]) / EZ); bz++) { let L = T.band.get(bz); if (!L) T.band.set(bz, L = []); L.push(e); } } } }
// a solid {c, u, hl, hw, lo, hi} (world y) in a tier it overlaps in height (by > 0.05 m): its centre in the tier's rings or
// a ring edge through the box less TIER_TOL all round - the tiers' rings are rounded to 0.1 m and grown by that tolerance
// to hold every LOD0 / LOD1 vertex (b3d_integrate.py tiers), so a 0.1-m graze is not a contact (G10 L1's corridor grazed the
// ITB hall's body tier by 0.02 m2 just outside its drum, which abuts the facade; +0.05 as solidInBuilding: 0.15 m, as the
// VDGS bracket's asset face); the tier's tag, or null. Exact, indexed like the outlines above (start-up: 571 tiers)
const TIER_TOL = 0.15;
const tierOn = (T, bx) => Math.min(bx.hi, T.y1) - Math.max(bx.lo, T.y0) > 0.05;
function solidInAsset(bx) {
  const v = [-bx.u[1], bx.u[0]]; const hl = Math.max(0.01, bx.hl - TIER_TOL), hw = Math.max(0.01, bx.hw - TIER_TOL);
  const ex = Math.abs(bx.u[0]) * hl + Math.abs(v[0]) * hw, ez = Math.abs(bx.u[1]) * hl + Math.abs(v[1]) * hw;
  const C = TIER_GRID.get(Math.floor(bx.c[0] / TIER_CELL) * 65536 + Math.floor(bx.c[1] / TIER_CELL));
  if (C) for (const T of C) { const bb = T.bb; if (bx.c[0] < bb[0] || bx.c[0] > bb[2] || bx.c[1] < bb[1] || bx.c[1] > bb[3] || !tierOn(T, bx)) continue;
    const L = T.band.get(Math.floor(bx.c[1] / EZ)); if (!L) continue; let inn = false; const x = bx.c[0], z = bx.c[1];
    for (const e of L) if (((e[2] > z) !== (e[4] > z)) && (x < (e[3] - e[1]) * (z - e[2]) / (e[4] - e[2]) + e[1])) inn = !inn;
    if (inn) return T.tag; }
  for (let cx = Math.floor((bx.c[0] - ex) / EC); cx <= Math.floor((bx.c[0] + ex) / EC); cx++) for (let cz = Math.floor((bx.c[1] - ez) / EC); cz <= Math.floor((bx.c[1] + ez) / EC); cz++) {
    const L = TIER_EC.get(cx * 65536 + cz); if (!L) continue;
    for (const e of L) { const T = TIERS[e[0]]; if (tierOn(T, bx) && segInBox(e, bx, hl, hw)) return T.tag; } }
  return null;
}
// top of the terminal wall the point (x, z) lies in (0: none) - js/live/terminals.js: complex 0-5 m, parts 5 m - h
function wallTop(x, z) { let h = 0; for (let i = 0; i < NBLD; i++) { const bb = BLD_BB[i]; if (x < bb[0] || x > bb[2] || z < bb[1] || z > bb[3]) continue; if (inRingK(x, z, i)) h = Math.max(h, BLD_H[i]); } return h; }

const G = GROUND_Y;
const stW = (p, h = 0) => stToWorld(p[0], p[1], h);
const stD = (d) => { const a = stToWorld(d[0], d[1], 0), o = stToWorld(0, 0, 0); return v3.norm([a[0] - o[0], 0, a[2] - o[2]]); };
const hash = (s) => { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return (h >>> 0) % 100000 + 1; };
const DEG = Math.PI / 180;
const wrap = (a) => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
const clampN = (x, a, b) => Math.min(b, Math.max(a, x));
const dirOf = (a) => [Math.cos(a), 0, Math.sin(a)];                       // world yaw a (x east, z south) -> unit vector
const yawOf = (x, z) => Math.atan2(z, x);
// signed angle from u to v, + = clockwise seen from above (x east, z south) - tools/stands/geom.py angle()
const turnOf = (u, v) => Math.atan2(u[0] * v[2] - u[2] * v[0], u[0] * v[0] + u[2] * v[2]);

// ---------------------------------------------------------------- Oshkosh AeroTech Jetway sell sheet 2025 (see header)
// model: [tunnels, fully extended, fully retracted, operational extension, operational retraction] (m)
const PBB = {
  'AT2 41/55': [2, 16.764, 12.224, 12.264, 9.846], 'AT2 46/65': [2, 19.812, 13.748, 15.312, 11.370], 'AT2 51/75': [2, 22.860, 15.272, 18.360, 12.894],
  'AT2 56/85': [2, 25.908, 16.796, 21.408, 14.418], 'AT2 61/95': [2, 28.956, 18.320, 24.456, 15.942], 'AT2 66/105': [2, 32.004, 19.844, 27.504, 17.466],
  'AT2 72/116': [2, 35.357, 21.673, 30.857, 19.294], 'AT2 77/126': [2, 38.405, 23.197, 33.905, 20.818], 'AT2 82/136': [2, 41.453, 24.721, 36.953, 22.342],
  'AT2 88/147': [2, 44.806, 26.549, 40.306, 24.171],
  'AT3 42/70': [3, 21.528, 12.501, 16.997, 10.276], 'AT3 47/85': [3, 26.100, 14.025, 21.569, 11.800], 'AT3 52/100': [3, 30.672, 15.549, 26.141, 13.324],
  'AT3 58/116': [3, 35.549, 17.378, 31.018, 15.152], 'AT3 61/127': [3, 38.749, 18.445, 34.219, 16.219], 'AT3 65/133': [3, 40.730, 19.512, 36.200, 17.286],
  'AT3 68/144': [3, 43.931, 20.579, 39.400, 18.353], 'AT3 72/150': [3, 45.912, 21.645, 41.381, 19.420],
};
const CAB_CW = 92.5, CAB_CCW = 32.5, CAB_OPT_HALF = 92.5; // deg; optional 185 deg cab split not given: +-92.5 (inferred, = geom.py)
const ROT_SWING = 87.5;                                   // deg either side of the rotunda centreline
const CAB_RATE = 145 / 60 * DEG;                          // rad/s (sheet; AC 150/5220-21C allows 0-4 deg/s)
const LIFT_RATE = 1.09 / 60;                              // m/s
const DRIVE_V = 27 / 60;                                  // m/s, maximum horizontal travel
const APPROACH_V = 0.15;                                  // m/s final creep to the door (inferred, ~1/3 of the maximum)
const STANDOFF = 1.5;                                     // m, pre-dock point on the door normal (inferred)
const SLOPE_TARGET = 1 / 12, SLOPE_MAX = 1 / 4;           // AC 150/5220-21C Figure 6 (unassisted / assisted), §3.4.b(6)
// floor of the fixed walkway where it leaves the building (the pier's bridge level), m above the apron, per boarding area
// (g.pier = the stand letter) - close-out round 3 bridges-1: one inferred 5.4 m for every pier put the BA-G walkway tops
// (8.4 m) through the 6.5-7.1 m bridge-head bump-outs and the BA-C / BA-D walkways above concourses whose measured roofs
// (7.2 / 8.49 m) leave 0.4 / 1.7 m of headroom over a 5.4 m floor (data/buildings3d/manifest.json itb / domestic conflicts):
//  G  2.7 [obs, low] photo a2 (Wikimedia Commons "Aerial view of San Francisco International Airport station, September
//     2025", CC BY-SA 4.0; refs/cache/buildings/review_likeness/a2.jpg) with the ITB group's solved camera
//     (out/buildings3d/itb_a2_camera.json): at the G2 / G5 / G6 bridge heads the walkway / drum roofs read 5.5-6.6 m and
//     the tunnels leave the drums at 1.9-2.9 m (1 m ticks projected at the attach points, +0.3..0.7 m for the camera's
//     ground offset at B1; scratchpad c3/bridges/photo/a2_G_walk2.png); the ITB group reads the walkway roofs 1-1.4 m
//     under the 6.5-7.1 m bump-out roofs (top <= 6.0 m). 2.7 + WALK_H 3.0 = 5.7 m at the attach point.
//  E, F  4.88 [pub] Terminal 3 L2 departures TOC 27'-0" vs L1 arrivals 11'-0" (16.0 ft) - T3W Civic Design Review, 95 %
//     construction documents, Oct 2023 (refs/cache/buildings/domestic/src/verify/231004_CDRC_CD_FINAL.pdf, sheets
//     5A-A5.01.01/.02; docs/research/buildings_domestic.md §5.1); L1 at the apron [inf: the datum is not stated]
//  D  3.65 [obs, low] photo a1 (Wikimedia Commons "Aerial view of SFO from departing flight, September 2025"): at the BA-D
//     near end the concourse glazing spans 0.44-0.79 of the 8.49 m roof-edge height and the walkways enter at it, with
//     about one walkway height of facade above them: floor 3.5-3.8 m (domestic group, manifest domestic.conflicts)
//  C  3.2 [inf] the BA-D layout on a1 (BA-C is too small there to measure): glazing foot 0.44 x the measured 7.2 m roof
//     edge; 3.2 m clear under the 6.4 m roof slab
//  A, B  5.4 [inf] no photo or published level yet (the terminal model's ramp level 0-5 m + slab, js/live/terminals.js)
const DEPARTURE_LEVEL = 5.4;                              // m, the default (stands of an unlisted pier; inferred)
export const DEPARTURE_LEVELS = {
  A: { h: 5.4, tag: 'inf', src: 'terminal model ramp level 0-5 m + slab (no photo / published level)' },
  B: { h: 5.4, tag: 'inf', src: 'terminal model ramp level 0-5 m + slab (no photo / published level)' },
  C: { h: 3.2, tag: 'inf', src: 'photo a1 BA-D layout (glazing foot 0.44 of the roof edge) on the measured 7.2 m BA-C roof' },
  D: { h: 3.65, tag: 'obs-low', src: 'photo a1 ratios at the BA-D near end: concourse floor 3.5-3.8 m' },
  E: { h: 4.88, tag: 'pub', src: 'T3 L2 departures 16.0 ft above L1 (T3W CDR 95 % CD, Oct 2023); L1 at the apron inf' },
  F: { h: 4.88, tag: 'pub', src: 'T3 L2 departures 16.0 ft above L1 (T3W CDR 95 % CD, Oct 2023); L1 at the apron inf' },
  G: { h: 2.7, tag: 'obs-low', src: 'photo a2 + solved camera: walkway / drum roofs 5.5-6.6 m, tunnels leave the drums at 1.9-2.9 m' },
};
const departureLevel = (g) => DEPARTURE_LEVELS[g && (g.pier || g.letter || (g.name || '')[0])] || { h: DEPARTURE_LEVEL, tag: 'inf', src: 'default' };
const OVERLAP = 1.0, STAGGER = 0.3;                       // m, minimum tunnel overlap at full extension / retracted stagger (inferred)
// sign convention of the sheet's "cw" in the data (data/sfo_stands.json cab_convention, inferred by the stand builder)
const CW = (STANDS.cab_convention && /^clockwise/.test(STANDS.cab_convention.cw_is || '')) ? 1 : -1;
// A380 upper deck door U1L (Airbus AC380 Dec 01/25, see header); rendered fuselage half width at the door from the fitted
// type (T.dockX3 / T.dockSill3 / T.dockHW3 are used instead when js/aircraft/fit.js provides them)
const A388_U1 = { x: 20.94, sill: 7.88 };
const DOCK_DELAY = 12;                                    // s after the engine reports the aircraft at rest
const DOCK_TIME = 22, UNDOCK_TIME = 16;                   // s, fallback only (paths are timed from the sheet's rates)
// rest pose per occupant (close-out round 7; static closeout R5.2 / R6.2): a bridge that does not dock the aircraft parked
// at its stand (an L2 beside a narrow body, a freighter, a refused type) or at a stand within PARK_NEAR m keeps the data's
// rest only where that rest holds the ICAO stand clearance to the aircraft's wing, engines and tailplane (Annex 14 3.13.6:
// code A/B 3.0, C 4.5, D-F 7.5 m - tools/stands/geom.py icao_clear) and is clear of its straight push-back; else it parks
// retracted along its rest line and / or swung up to PARK_SWING deg, the smallest move that holds the clearance (else the
// largest clearance gained, >= 0.5 m), clear of the building, the fixed walkways, the other bridges' rest and docked poses,
// every accepted type of the stands around it (0.5 m) and their push-backs. It returns to the data rest PARK_RETURN_S after
// the last departure signal (the push-back and taxi-out; PARK_EARLY_S after an early undock, the engine's EARLY_MAX_MS
// bound + PARK_RETURN_S) unless another aircraft keeps it parked. [inferred: PARK_SWING, PARK_RETURN_S, PARK_NEAR]
const PARK_SWING = 30, PARK_RETURN_S = 180, PARK_EARLY_S = 3600 + 180, PARK_NEAR = 110;
// pre-arrival park (close-out round 7 verifier, R7.4.1): how long an announced arrival (expectArrival) keeps the bridges
// parked for it without being renewed by the engine [inferred: EXPECT_HOLD_S]
const EXPECT_HOLD_S = 600;
// ...and the margin its body keeps from a rest pose while it taxis in (parkChoose touch test; 0.5 m for a parked one): the
// reported stop is not the stop mark -- DAL672 B763 stopped 2.6 m short and 1.4 m off C9V's line (4 Nov 21:42Z) with C9 L1's
// data rest 0.5+ m clear of the mark pose and touching the aircraft [inferred: EXPECT_MG]
const EXPECT_MG = 3.0;
const icaoClear = (span) => span < 24 ? 3.0 : span < 36 ? 4.5 : 7.5;
// exterior cross-sections (width, height) of tunnel sections A (rotunda) .. C (cab): AC 150/5220-21C §3.5.a(1) minimum
// interior 50 in corridor / 80 in height; sheet minimum A tunnel interior 1.47 x 2.13 m; exterior inferred
const SEC_WH = { 2: [[2.55, 2.85], [2.82, 3.12]], 3: [[2.55, 2.85], [2.68, 2.98], [2.82, 3.12]] };
const WALK_W = 2.6, WALK_H = 3.0, CAB_W = 3.6, CAB_BACK = 1.6;
// minimum rotunda drum radius: half the rotunda corridor (2.4 m) / tunnel A exterior (2.55 m, SEC_WH) + 0.2 m (inferred)
const DRUM_MIN = 1.5;
// ---------------------------------------------------------------- the bridge's own fixed walkway in the SFO Museum rings
// The SFO Museum boarding-area outlines (clearance outlines above) trace the roofs of some fixed walkways as narrow
// strips of the ring - at the Boarding Area B tip the strips of B3-B27 L1, 1.8-5.0 m wide across the walkway (review
// round 2, verifier walkin.mjs). The 3-D domestic asset does not draw them (docs/research/buildings3d.md, domestic:
// "bridge-head fingers and the fixed-walkway strips at the BA-B tip are left to the app's bridges"; its footprints in
// data/buildings3d/integration.json contain none of the walkway columns), so such a strip is the bridge's OWN walkway,
// not building: it neither drops the walkway's support columns nor pushes the drum along its own walkway, and the
// moving parts are tested against the walkway slab itself (fixedHit) there. A Museum ring point is own-strip for a
// bridge when, on the line across the bridge's mapped walkway polyline through the nearest centreline point (or a
// point up to the lean, 2.1 m, along it - a strip ending short of the rotunda or starting beyond the facade), it lies in
// a piece of the ring every point of which is within STRIP_W of the walkway polyline and some within STRIP_HW of the
// centreline (the OSM line runs along one edge of most strips: the lean), and the walkway carries such pieces for at
// least STRIP_MIN_L; an outline edge is own-strip when all of it is (sampled every 0.25 m). The pier bodies reach
// further than STRIP_W from the walkway, so they never are.
const STRIP_LEAN = 2.1;                                   // m, OSM / Museum roof lean (data bridge_geom_note: 1.3-2.1 m)
const STRIP_W = WALK_W + 2 * STRIP_LEAN, STRIP_HW = STRIP_W / 2; // walkway slab + the lean on both sides
// a walkway strip runs at least STRIP_MIN_L along the walkway: the Boarding Area B tip strips run 6.3-50.8 m, the
// bumps of the pier faces around the other walkways' starts (which the 3-D assets draw) at most 3.3 m (review round 2)
const STRIP_MIN_L = 5.0;
// own-strip test of a bridge from its mapped walkway polyline W ([[x, z], ...], last = rotunda): {W, inStrip(x, z, k), edges}
function ownStrip(W) {
  const S = { W, edges: new Set(), inStrip: () => false };
  const seg = []; for (let i = 1; i < (W || []).length; i++) { const A = W[i - 1], B = W[i]; const L = Math.hypot(B[0] - A[0], B[1] - A[1]); if (L > 0.01) seg.push({ A, u: [(B[0] - A[0]) / L, (B[1] - A[1]) / L], L }); }
  if (!seg.length) return S;
  const near = (x, z) => { let best = null; seg.forEach((s, i) => { const t = clampN((x - s.A[0]) * s.u[0] + (z - s.A[1]) * s.u[1], 0, s.L); const d = Math.hypot(s.A[0] + s.u[0] * t - x, s.A[1] + s.u[1] * t - z); if (!best || d < best.d) best = { d, i, t }; }); return best; };
  // the pieces of ring k on the line across segment i at t (0.25 m grid): [[s0, s1, own]], s = metres to the left; own:
  // every point of the piece is within STRIP_W of the walkway polyline (it may run along a bend's other leg) and some
  // within STRIP_HW of the centreline there - a piece of a pier body reaches further (or the line leaves it only
  // beyond SFAR: not own)
  const SFAR = 20, secs = new Map();
  const section = (k, i, t) => { const tq = clampN(Math.round(t / 0.25) * 0.25, 0, seg[i].L); const key = k + ':' + i + ':' + tq; let X = secs.get(key); if (X) return X; X = [];
    const sg = seg[i], cx = sg.A[0] + sg.u[0] * tq, cz = sg.A[1] + sg.u[1] * tq, n = [-sg.u[1], sg.u[0]];
    const lo = []; for (let sv = -0.1; ; sv -= 0.1) { const ins = inRingK(cx + n[0] * sv, cz + n[1] * sv, k); lo.push(ins); if ((!ins && sv < -STRIP_W - 0.5) || sv < -SFAR) break; }
    const hi = []; for (let sv = 0; ; sv += 0.1) { const ins = inRingK(cx + n[0] * sv, cz + n[1] * sv, k); hi.push(ins); if ((!ins && sv > STRIP_W + 0.5) || sv > SFAR) break; }
    const F = lo.reverse().concat(hi), s0 = -0.1 * lo.length; let a = null, far = false;
    for (let j = 0; j <= F.length; j++) { const ins = j < F.length && F[j]; const sv = s0 + 0.1 * j;
      if (ins) { if (a == null) { a = sv; far = j === 0; } if (!far && near(cx + n[0] * sv, cz + n[1] * sv).d > STRIP_W) far = true; }
      else if (a != null) { const b = sv - 0.1; X.push([a, b, !far && j < F.length && b >= -STRIP_HW && a <= STRIP_HW]); a = null; } }
    secs.set(key, X); return X; };
  // runs of the walkway along which a ring has an own piece on the line across it (arc length from W[0], per ring k):
  // a walkway strip is a long run; a short one is a bump of the pier face around the walkway's start (the 3-D assets
  // draw those, review round 2: integration.json footprints cover 75-100 % of them)
  const rings = new Set(); { let a = 1e9, b = 1e9, c = -1e9, d = -1e9; for (const p of W) { a = Math.min(a, p[0]); c = Math.max(c, p[0]); b = Math.min(b, p[1]); d = Math.max(d, p[1]); }
    for (let k = NBLD; k < NCL; k++) { const bb = BLD_BB[k]; if (bb[0] < c + STRIP_W && bb[2] > a - STRIP_W && bb[1] < d + STRIP_W && bb[3] > b - STRIP_W) rings.add(k); } }
  const runs = new Map(); let acc0 = 0; const arc = []; seg.forEach((sg) => { arc.push(acc0); acc0 += sg.L; });
  for (const k of rings) { const R = []; let r0 = null, last = null;
    seg.forEach((sg, i) => { for (let t = 0; t <= sg.L + 1e-6; t += 0.25) { const own = section(k, i, t).some(iv => iv[2]); const sA = arc[i] + t;
      if (own) { if (r0 == null) r0 = sA; last = sA; } else if (r0 != null) { R.push([r0, last]); r0 = null; } } });
    if (r0 != null) R.push([r0, last]); runs.set(k, R); }
  S.runs = runs;
  // (the line through the nearest centreline point, or one up to the lean further along / back: where the strip ends
  // short of the rotunda or starts beyond the facade, the mapped and the traced lines are that far apart)
  const offs = [0]; for (let o = 0.25; o <= STRIP_LEAN + 1e-6; o += 0.25) offs.push(-o, o);
  const at = (i, t, o) => { t += o; while (t < 0 && i > 0) { i--; t += seg[i].L; } while (t > seg[i].L && i < seg.length - 1) { t -= seg[i].L; i++; } return t < -1e-6 || t > seg[i].L + 1e-6 ? null : [i, t]; };
  // true / false; null: no piece of the ring next to the point on any of those lines (a zero-width spike of the outline)
  const test = (x, z, k) => {
    const c = near(x, z); if (!c || c.d > STRIP_W) return false; let found = false;
    for (const o of offs) { const q = at(c.i, c.t, o); if (!q) continue; const [i, t] = q; const sg = seg[i]; const tq = clampN(Math.round(t / 0.25) * 0.25, 0, sg.L);
      const sP = (x - sg.A[0] - sg.u[0] * tq) * -sg.u[1] + (z - sg.A[1] - sg.u[1] * tq) * sg.u[0];
      const iv = section(k, i, t).find(([a, b]) => sP >= a - 0.15 && sP <= b + 0.15);
      if (iv) { const sA = arc[i] + tq; if (iv[2] && (runs.get(k) || []).some(([r0, r1]) => r1 - r0 >= STRIP_MIN_L && sA >= r0 - 0.01 && sA <= r1 + 0.01)) return true; found = true; } }
    return found ? false : null;
  };
  S.inStrip = (x, z, k) => test(x, z, k) === true;
  // the Museum outline edges near the walkway that are own-strip along their whole length
  let a = 1e9, b = 1e9, c = -1e9, d = -1e9; for (const p of W) { a = Math.min(a, p[0]); c = Math.max(c, p[0]); b = Math.min(b, p[1]); d = Math.max(d, p[1]); }
  const seen = new Set();
  for (let cx = Math.floor((a - STRIP_W - 1) / EC); cx <= Math.floor((c + STRIP_W + 1) / EC); cx++) for (let cz = Math.floor((b - STRIP_W - 1) / EC); cz <= Math.floor((d + STRIP_W + 1) / EC); cz++) {
    for (const e of ECELL.get(cx * 65536 + cz) || []) { if (!isMus(e[0]) || seen.has(e)) continue; seen.add(e);
      if (near(e[1], e[2]).d > STRIP_W || near(e[3], e[4]).d > STRIP_W) continue;
      const L = Math.hypot(e[3] - e[1], e[4] - e[2]); const n = Math.max(1, Math.ceil(L / 0.25)); let all = true, any = false;
      for (let j = 0; j <= n && all; j++) { const r = test(e[1] + (e[3] - e[1]) * j / n, e[2] + (e[4] - e[2]) * j / n, e[0]); if (r === false) all = false; else if (r) any = true; }
      if (all && any) S.edges.add(e); } }
  return S;
}

const C = {
  panel: [0.86, 0.87, 0.88, 1], panelE: [0.45, 0.25, 9, 0], cab: [0.8, 0.81, 0.82, 1], cabE: [0.4, 0.3, 9, 0],
  steel: [0.46, 0.47, 0.49, 1], steelE: [0.45, 0.7, 0, 0], dark: [0.07, 0.07, 0.08, 1], darkE: [0.85, 0, 0, 0],
  yellow: [0.9, 0.7, 0.08, 1], yellowE: [0.5, 0, 0, 0], tyre: [0.05, 0.05, 0.05, 1], tyreE: [0.9, 0, 0, 0],
  unit: [0.74, 0.75, 0.76, 1], unitE: [0.5, 0.2, 0, 0], lamp: [1, 0.93, 0.82, 1], lampE: [0.15, 0, 14, 0], amber: [1, 0.55, 0.05, 1], amberE: [0.2, 0, 14, 0],
  walk: [0.84, 0.85, 0.86, 1], neck: [0.78, 0.79, 0.8, 1],
};

// rectangular tube along a->b (floor on the a->b line), with window-strip UVs (mat 9: u = metres along, v = 0..1)
function tube(g, a, b, w, h, col, ext) {
  const d = v3.sub(b, a); const L = v3.len(d); if (L < 0.1) return null; const f = v3.mul(d, 1 / L);
  const r = v3.norm(v3.cross(f, [0, 1, 0])); const u = v3.cross(r, f);
  const P = (s, x, y) => v3.add(v3.add(v3.add(a, v3.mul(f, s)), v3.mul(r, x)), v3.mul(u, y));
  const hw = w / 2;
  const side = (x0, y0, x1, y1, n) => {
    const base = g.nv;
    const pts = [P(0, x0, y0), P(L, x0, y0), P(L, x1, y1), P(0, x1, y1)];
    const uvs = [[0, 0], [L, 0], [L, 1], [0, 1]];
    for (let i = 0; i < 4; i++) g.vert(pts[i], n, col, ext, uvs[i]);
    const gn = v3.cross(v3.sub(pts[1], pts[0]), v3.sub(pts[3], pts[0]));
    if (v3.dot(gn, n) > 0) g.idx.push(base, base + 1, base + 2, base, base + 2, base + 3); else g.idx.push(base, base + 2, base + 1, base, base + 3, base + 2);
  };
  side(hw, 0, hw, h, r); side(-hw, 0, -hw, h, v3.mul(r, -1));
  const flat = (y, n, col2, ext2) => { const base = g.nv; const pts = [P(0, -hw, y), P(0, hw, y), P(L, hw, y), P(L, -hw, y)]; for (const p of pts) g.vert(p, n, col2, ext2, [0, 0]); const gn = v3.cross(v3.sub(pts[1], pts[0]), v3.sub(pts[3], pts[0])); if (v3.dot(gn, n) > 0) g.idx.push(base, base + 1, base + 2, base, base + 2, base + 3); else g.idx.push(base, base + 2, base + 1, base, base + 3, base + 2); };
  flat(h, u, col, [ext[0], ext[1], 0, 0]); flat(0, v3.mul(u, -1), C.steel, C.steelE);
  for (const s of [0.05, L - 0.05]) g.box([-0.08, -0.05, -hw - 0.06], [0.08, h + 0.06, hw + 0.06], C.steel, C.steelE, m4.basis(f, [0, 1, 0], P(s, 0, 0)));
  return { f, r, u, P, L };
}
function cyl(g, p, r, h, col, ext, seg = 16) { g.cylinder(r, h, seg, col, ext, m4.translate(p[0], p[1], p[2]), true); }
// box spanning a -> b (floor on the line a -> b, sloping allowed), width w, height h
function slab(g, a, b, w, h, col, ext) {
  const d = v3.sub(b, a); const L = v3.len(d); if (L < 0.05) return;
  g.box([0, 0, -w / 2], [L, h, w / 2], col, ext, m4.basis(d, [0, 1, 0], a));
}
// the full-width rotunda corridor a -> b (floor on the line a -> b, width w, height h square to that line, as slab()) with
// a VERTICAL start face - flush with the vertical ends of the neckShape prisms and the drum (slab()'s start face is square
// to the sloping floor, so where the tunnel slopes down its roof edge stood forward of the start: a V-groove across the
// 2.4 m roof, 0.11 m wide at A12 L1 - c5 runtime verifier). Its roof runs on into tunnel A (T = {o: tunnel A's floor origin
// at F, f: its axis, h: its height}): where tunnel A slopes down more steeply than this floor line, slab()'s end face
// (square to the floor line) left the roof edge BEHIND tunnel A's end frame - a slot across the roof (0.02-0.03 m x
// 0.3-0.4 m deep at A12 / F17 / F21 L1 docked, up to 0.25 m wide at A5 L1); the end face is turned towards square to
// tunnel A (parallel to its end frame) but no further than keeps the roof edge 0.02 m under tunnel A's roof (at the 1:4
// limit the edge stops at the frame's back face). Where tunnel A rises, the end stays square to the floor line (the frame
// leans back over the roof there) unless the roof would stand above tunnel A's roof past the frame (tube()'s end frame:
// 0.05 +- 0.08 m along the axis, top h + 0.06; up to 0.047 m at the steepest up-slopes, G8 L1): then it ends inside the
// frame - unless the flat roof would then stand above the frame's sloped top at its back face (up to 0.012 m over a
// 4-8 cm strip at G8 / G7 L1, 1:4.0-1:4.3 - c6 runtime verifier): then it ends flush with that back face, a closed step of
// at most that height down onto the frame (close-out round 7). T null - a part that ends short of tunnel A: square to the
// floor line
function neckSlab(g, a, b, T, w, h, col, ext) {
  const d = v3.sub(b, a); const L = v3.len(d); if (L < 0.05) return;
  const f = v3.mul(d, 1 / L), r = v3.norm(v3.cross(f, [0, 1, 0])), n = v3.cross(r, f); // n: square to the floor line (up)
  let t = 0; if (T) { const fa = v3.norm(T.f), ua = v3.cross(r, fa); const fx = v3.dot(f, fa), fu = v3.dot(f, ua);
    const P0 = v3.sub(v3.add(b, v3.mul(n, h)), T.o), xs = v3.dot(P0, fa), ys = v3.dot(P0, ua), yMax = T.h - 0.02; // (roof edge at t = 0, tunnel A frame)
    if (fx > 0.5 && fu > 1e-6) t = clampN(Math.min(-h * v3.dot(n, fa) / fx, (yMax - ys) / fu), 0, h); // down: towards square to tunnel A, under its roof
    else if (fx > 0.5 && fu < -1e-6) { // up: ends inside the frame where it would stand above tunnel A's roof past it, and
      // behind the frame's back face (x = -0.03) where it would stand above the frame's sloped top (h + 0.06) there
      let xe = xs > 0.13 && ys + (0.13 - xs) / fx * fu > yMax ? 0.12 : xs;
      if (xe > -0.03 && ys + (-0.03 - xs) / fx * fu > T.h + 0.055) xe = -0.0305;
      if (xe !== xs) t = Math.max(-h, (xe - xs) / fx); } }
  const hw = v3.mul(r, w / 2), up = [0, h / Math.max(0.5, n[1]), 0], top = v3.add(v3.add(b, v3.mul(n, h)), v3.mul(f, t));
  const S0 = [v3.sub(a, hw), v3.add(a, hw)], S1 = S0.map(p => v3.add(p, up)), E0 = [v3.sub(b, hw), v3.add(b, hw)], E1 = [v3.sub(top, hw), v3.add(top, hw)];
  const C0 = v3.add(v3.mul(v3.add(a, b), 0.5), v3.mul(v3.add(up, v3.mul(n, h)), 0.25)); // (inside: mid-length, mid-height)
  const face = (p0, p1, p2, p3) => { const nn = v3.cross(v3.sub(p1, p0), v3.sub(p3, p0)); const fc = v3.mul(v3.add(v3.add(p0, p1), v3.add(p2, p3)), 0.25);
    if (v3.dot(nn, v3.sub(fc, C0)) >= 0) g.quad(p0, p1, p2, p3, col, ext); else g.quad(p0, p3, p2, p1, col, ext); };
  face(S0[0], S0[1], S1[1], S1[0]); face(E0[0], E0[1], E1[1], E1[0]); // start (vertical), end
  face(S0[0], E0[0], E0[1], S0[1]); face(S1[0], E1[0], E1[1], S1[1]); // floor, roof
  face(S0[0], E0[0], E1[0], S1[0]); face(S0[1], E0[1], E1[1], S1[1]); // sides
}

// representative (largest common) aircraft of a stand class (only used for a stand without stand data)
const REF_TYPE = { B: 'crj9', C: 'b38m', CL: 'a21n', D: 'b763', E: 'b789', EL: 'b77w', F: 'a388' };
const ICAO_OF = {}; for (const [icao, k] of Object.entries(ICAO_TYPES)) if (!ICAO_OF[k]) ICAO_OF[k] = icao;
// Where the bridge cab meets the aircraft (js/aircraft/fit.js): door `which` = 1 is door 1L, 2 the door the second bridge
// of a wide-body stand docks to (T.dock2, from the manufacturers' documents), 3 the A380 upper-deck door U1L (upper-deck
// bridges). x = door CENTRE station from the nose tip (the rendered door of the imported model where it has one, else the
// published centre), cab floor = published door sill above the ground, and the cab stops at the rendered fuselage side at
// that door (T.dockHW, T.dockHW2 for the second bridge's door, T.dockHW3 for U1L: the widest skin over the door opening).
function doorOf(nose, f, T, which) {
  const left = v3.mul(v3.norm(v3.cross(f, [0, 1, 0])), -1);
  if (which === 3) {
    const x3 = T.dockX3 ?? A388_U1.x, sill3 = T.dockSill3 ?? A388_U1.sill;
    let hw3 = T.dockHW3;
    if (hw3 == null) { // ellipse through the rendered crown, the centre line and the half width, at door mid height
      const crown = (T.fit && T.fit.renderedCrown) || (T.Hc + T.R); const a = Math.max(0.5, crown - T.Hc), y = sill3 + 0.95 - T.Hc;
      hw3 = T.R * Math.sqrt(Math.max(0.05, 1 - (y / a) ** 2));
    }
    const d3 = v3.add(v3.sub(nose, v3.mul(f, x3)), v3.mul(left, hw3 + 0.15)); d3[1] = G + sill3;
    return { door: d3, left };
  }
  const two = which >= 2 && T.dockX2 != null;
  // (a type without a documented second-bridge door, e.g. the 767-300 whose door 2 is optional, is not docked by the
  // second bridge (docks()); its retracted bridge still points at door 2 or the aft door)
  const x = two ? T.dockX2 : which >= 2 ? ((T.doorsOpt && T.doorsOpt[0]) ?? T.doors[1] ?? T.dockX1) : (T.dockX1 ?? T.doors[0]);
  const sill = two ? (T.dockSill2 ?? T.dockSill) : (T.dockSill ?? (T.sill ?? T.Hc - 0.3 * T.R));
  const hw = (two ? T.dockHW2 : null) ?? T.dockHW ?? T.R;   // skin half width at that door (js/aircraft/fit.js)
  const d = v3.add(v3.sub(nose, v3.mul(f, x)), v3.mul(left, hw + 0.15)); d[1] = G + sill;
  return { door: d, left };
}
export { doorOf, acHit, boxHitsAc, boxHitsSwept, PBB, inBuilding, solidInBuilding, solidInAsset, nearestBuilding };

// ---------------------------------------------------------------- aircraft solid for the bridge-path test
// (x metres behind the nose, y to the right, heights above the apron). The fuselage tapers over the nose (types.js Ln)
// as the rendered airframe does; wing / tailplane / engines as the ground-physics planform with their heights.
// ell: for the ground vehicles that reach under its lower lobe - true: the fuselage as its elliptical cross-section (half
// width x crown - centre line) instead of the enclosing box; 'skin': the fitted model's RENDERED skin (pitch, stance,
// plugs: js/aircraft/fit.js keelAt / skinHW; the belt loaders' conveyors, close-out round 3 bridges-3 - the unpitched
// ellipse put the 737 MAX's forward belly 0.25 m too low); 'both': the skin or the ellipse (the other vehicles, kept
// conservative where the skin table reads a gear-well roof). Procedural airframes: the ellipse
function fusSkinHit(T, x, y, lo, hi, mg) {
  const ay = Math.abs(y); if (ay > T.R + 1 + mg) return false;
  const k = T.fit.keelAt(x); if (k == null) return false;
  const y0 = Math.max(lo, k - mg), y1 = Math.min(hi, (T.fit.renderedCrown || T.Hc + T.R) + mg); if (y0 > y1) return false;
  const n = Math.max(1, Math.ceil((y1 - y0) / 0.1));
  for (let i = 0; i <= n; i++) { const w = T.fit.skinHW(x, y0 + (y1 - y0) * i / n); if (w != null && ay < w + mg) return true; }
  return false;
}
function acHit(T, x, y, lo, hi, mg, ell = false, noFus = false) { // (noFus: wing / engines / tailplane only - the parts
  // the ICAO stand clearance is measured to, tools/stands/check_stands.py GM.wings; parkFor())
  const R = T.R, L = T.L, Hc = T.Hc;
  if (!noFus && x > -mg && x < L + mg) {
    const Ln = T.Ln || 4; const xx = clampN(x, 0, Ln); let hw = x < Ln ? R * Math.sqrt(Math.max(0, 1 - (1 - xx / Ln) ** 2)) : R;
    const crown = (T.fit && T.fit.renderedCrown) || Hc + R;
    const skin = ell && ell !== true && T.fit && T.fit.skinHW && T.fit.keelAt;
    if (skin && fusSkinHit(T, x, y, lo, hi, mg)) return 'fus';
    if (ell && (!skin || ell === 'both')) { const a = Math.max(0.5, crown - Hc) + mg, W = hw + mg; if (Math.abs(y) < W) { const v = a * Math.sqrt(1 - (y / W) ** 2); if (lo < Hc + v && hi > Hc - v) return 'fus'; } }
    else if (!ell && Math.abs(y) < hw + mg && lo < crown + mg && hi > Hc - R - mg) return 'fus';
  }
  const w = T.wing, ay = Math.abs(y);
  if (w) {
    const tn = Math.tan((w.sweep || 25) * DEG); const le = w.rootLE + ay * tn;
    const chord = w.rootC - (w.rootC - w.tipC) * Math.min(1, ay / (w.span / 2));
    const hw = Hc - (w.y || 0.6) * R + ay * Math.tan((w.dihedral || 5) * DEG);
    if (ay < w.span / 2 + mg && x > le - mg && x < le + chord + mg && lo < hw + 0.8 + mg && hi > hw - 1.0) return 'wing';
    for (const e of T.eng || []) {
      const ex = w.rootLE + Math.abs(e.z) * tn - (e.fwd || 3);
      if (Math.abs(ay - e.z) < e.r + mg && x > ex - mg && x < ex + e.len * 1.12 + mg && lo < Hc && hi > 0) return 'eng';
    }
  }
  if (T.rear && x > T.rear.x - mg && x < T.rear.x + T.rear.len + mg && ay < T.rear.z + T.rear.r + mg && lo < Hc + R + 1) return 'eng';
  if (T.hstab && x > T.hstab.x - mg && x < L + mg && ay < T.hstab.span / 2 + mg) {
    // beside the fuselage only the swept, tapered tailplane planform as js/aircraft/model.js lofts it: root section at
    // z0 = 0.35 R from the centre line (T-tail: 0.2 m), LE at x + (|y| - z0) tan(sweep), chord tapering from z0 to the tip
    // (review round 2 v8: measured from the centre line, this sat 0.4-0.8 m behind the drawn tailplane; before round 1:
    // the whole rectangle from the root LE station to the tail, which kept every catering truck off a narrow body's
    // door 2). (The T-tail keeps hs.x, 0.5 m ahead of model.js's fin-top root: conservative.)
    const hs = T.hstab; const z0 = hs.tTail ? 0.2 : 0.35 * R, ex = Math.max(0, ay - z0);
    const ple = hs.x + ex * Math.tan((hs.sweep || 30) * DEG), pch = hs.rootC - (hs.rootC - hs.tipC) * Math.min(1, ex / Math.max(0.5, hs.span / 2 - z0));
    const top = hs.tTail ? (T.fit && T.fit.renderedH) || T.H || Hc + 8 : Hc + R + 1;
    if ((ay <= R + mg || (x > ple - mg && x < ple + pch + mg)) && lo < top + mg && hi > Hc - R) return 'tail';
  }
  return null;
}
// any sample point of an oriented box {c:[x,z], u, hl, hw, lo, hi} inside the aircraft (nose [x,z], f [x,z] forward)
function boxHitsAc(bx, T, nose, f, mg, noFus = false) {
  const reach = T.L + (T.wing ? T.wing.span / 2 : T.R) + bx.hl + bx.hw + mg; // cheap reject: out of reach of the airframe
  if (Math.abs(bx.c[0] - nose[0]) > reach || Math.abs(bx.c[1] - nose[1]) > reach) return null;
  const r = [-f[1], f[0]]; const nx = Math.max(1, Math.ceil(bx.hl / 0.7)), ny = Math.max(1, Math.ceil(bx.hw / 0.7));
  const v = [-bx.u[1], bx.u[0]];
  for (let i = -nx; i <= nx; i++) for (let j = -ny; j <= ny; j++) {
    const px = bx.c[0] + bx.u[0] * bx.hl * i / nx + v[0] * bx.hw * j / ny, pz = bx.c[1] + bx.u[1] * bx.hl * i / nx + v[1] * bx.hw * j / ny;
    const dx = px - nose[0], dz = pz - nose[1];
    const x = -(dx * f[0] + dz * f[1]), y = dx * r[0] + dz * r[1];
    const k = acHit(T, x, y, bx.lo - G, bx.hi - G, mg, false, noFus); if (k) return k;
  }
  return null;
}
// as boxHitsAc, against the aircraft swept straight backward (a push-back) by 0..D metres: a point x metres behind the
// parked nose is reached by the part of the body at x - d (d in [0, D]; nothing lies ahead of the nose)
function boxHitsSwept(bx, T, nose, f, mg, D) {
  const reach = T.L + D + (T.wing ? T.wing.span / 2 : T.R) + bx.hl + bx.hw + mg;
  if (Math.abs(bx.c[0] - nose[0]) > reach || Math.abs(bx.c[1] - nose[1]) > reach) return null;
  const r = [-f[1], f[0]]; const nx = Math.max(1, Math.ceil(bx.hl / 0.7)), ny = Math.max(1, Math.ceil(bx.hw / 0.7));
  const v = [-bx.u[1], bx.u[0]];
  for (let i = -nx; i <= nx; i++) for (let j = -ny; j <= ny; j++) {
    const px = bx.c[0] + bx.u[0] * bx.hl * i / nx + v[0] * bx.hw * j / ny, pz = bx.c[1] + bx.u[1] * bx.hl * i / nx + v[1] * bx.hw * j / ny;
    const dx = px - nose[0], dz = pz - nose[1];
    const x = -(dx * f[0] + dz * f[1]), y = dx * r[0] + dz * r[1];
    const x0 = Math.max(x - D, -mg - 0.5);
    for (let xx = x; xx >= x0 - 1e-9; xx -= 0.35) { const k = acHit(T, xx, y, bx.lo - G, bx.hi - G, mg); if (k) return k; }
  }
  return null;
}
// two dock poses ({nose: [s, t], dir: [s, t]}) the same within 5 cm / 0.1 deg (null = null)
function samePose(p, q) {
  if (!p || !q) return !p && !q;
  return Math.hypot(p.nose[0] - q.nose[0], p.nose[1] - q.nose[1]) < 0.05 && Math.abs(wrap(Math.atan2(p.dir[1], p.dir[0]) - Math.atan2(q.dir[1], q.dir[0]))) < 0.1 * DEG; // (wrapped: 13 stands point within 2 deg of the branch cut)
}

export class LiveGateSystem {
  constructor(gates, { atlasExtra = [] } = {}) {
    this.gates = gates; this.anims = new Map(); this.settles = new Map(); this.parks = new Map(); this.dirty = true; this.live = true;
    this.vehicleMeshes = buildVehicleMeshes();
    this.attachUpper();
    const faces = []; const seen = new Set();
    const add = (kind, text) => { const k = kind + ':' + text; if (!seen.has(k)) { seen.add(k); faces.push({ key: k, kind, text }); } };
    for (const g of gates) if (g.bridge) { add('gate', g.name); add('vdgs', g.name); add('gate', g.gate || g.name); add('vdgs', g.gate || g.name); for (const b of this.bridgesOf(g)) add('gate', b.gate); }
    for (const t of atlasExtra) add('vdgs', t);
    this.atlas = makeAtlas(faces);
    this.bbox = [1e9, 0, 1e9, -1e9, 40, -1e9];
    for (const g of gates) { const p = stW(g.nose, 0); this.bbox[0] = Math.min(this.bbox[0], p[0] - 150); this.bbox[2] = Math.min(this.bbox[2], p[2] - 150); this.bbox[3] = Math.max(this.bbox[3], p[0] + 150); this.bbox[5] = Math.max(this.bbox[5], p[2] + 150); }
    for (const g of gates) for (const b of this.bridgesOf(g)) this.prepBridge(g, b);
    this.finishPrep();
    this.sprites = []; this.aircraftFootprints = null;
  }
  // upper-deck (A380 U1L) bridges: standGates() (js/live/airport.js) passes them as g.bridgesUpper (data/sfo_stands.json
  // bridges_upper; same fields as g.bridges, door 3, upper: true) - one source for gates.js, the engine and the tools
  // (close-out round 3 bridges-11: this used to re-read STANDS itself). Kept apart from g.bridges (the engine, the tools and
  // the L1 / L2 logic use those); a gate without the stand flag `bridge` gets none
  attachUpper() {
    for (const g of this.gates) {
      if (!g.bridge || !(g.bridgesUpper && g.bridgesUpper.length)) { if (g.bridgesUpper && !g.bridge) g.bridgesUpper = null; continue; }
      for (const b of g.bridgesUpper) { b.door = 3; b.upper = true; }
    }
  }
  bridgesOf(g) { return g.bridgesUpper ? (g.bridges || []).concat(g.bridgesUpper) : (g.bridges || []); }
  // ------------------------------------------------------------ static bridge geometry (per bridge, once)
  // prepGeom: rotunda, fixed walkway, model, drum, rest pose; prepKin: rotunda centreline, docking targets, heights.
  // finishPrep() runs prepKin again once every bridge is placed, with the fixed parts of the other bridges (and the
  // bridge's own fixed walkway) as obstacles of the moving parts.
  prepBridge(g, b) { this.prepGeom(g, b); this.prepKin(g, b); }
  prepGeom(g, b) {
    const cz = (p) => [p[0], G, p[1]];
    if (b._attachData === undefined) b._attachData = b.attachW || null; // the data's [x, z]; b.attachW becomes the 3-D point (tools read it)
    const att = b._attachData ? cz(b._attachData.length === 3 ? [b._attachData[0], b._attachData[2]] : b._attachData) : stW(b.attach, G);
    let rot = b.rotundaW ? cz(b.rotundaW) : null;
    const nose = stW(g.nose, G);
    if (!rot) { const o = stD(g.outN || [-g.dir[0], -g.dir[1]]); rot = v3.add(att, v3.mul(o, -4)); } // no data rotunda: 4 m out
    // the bridge's own walkway strip in the SFO Museum rings (ownStrip): from the data's walkway polyline + rotunda
    { const W = (b.walkW && b.walkW.length >= 2 ? b.walkW : [[att[0], att[2]]]).map(p => [p[0], p.length === 3 ? p[2] : p[1]]);
      const e = W[W.length - 1]; if (Math.hypot(e[0] - rot[0], e[1] - rot[2]) > 0.05) W.push([rot[0], rot[2]]); b._strip = ownStrip(W); }
    // a drum of the minimum radius (DRUM_MIN) needs 0.2 m to the terminal outline, 0.1 m to another bridge's fixed
    // walkway and 0.2 m to another drum: a rotunda closer than that (the outline is +-5 m, several data rotundas are
    // inferred "against the facade"; G10 L1 is 2.7 m from the axis of G10 L2's walkway) is moved straight away from the
    // nearest one by the deficit, at most 2.0 m in all (the data's OSM roofs lean 1.3-2.1 m, data bridge_geom_note)
    { const r0 = rot.slice();
      for (let it = 0; it < 12; it++) {
        let worst = null, def = 0.005;
        for (const c of this.drumLimits(b, rot[0], rot[2])) { if (c.inside) continue; const dd = DRUM_MIN + c.extra - c.d; if (dd > def) { def = dd; worst = c; } }
        if (!worst) break;
        const dx = rot[0] - worst.p[0], dz = rot[2] - worst.p[1], l = Math.hypot(dx, dz) || 1;
        rot = [rot[0] + dx / l * (def + 0.02), G, rot[2] + dz / l * (def + 0.02)];
        const sh = Math.hypot(rot[0] - r0[0], rot[2] - r0[2]); if (sh > 2.0) { rot = [r0[0] + (rot[0] - r0[0]) * 2 / sh, G, r0[2] + (rot[2] - r0[2]) * 2 / sh]; break; }
      }
      const sh = Math.hypot(rot[0] - r0[0], rot[2] - r0[2]); b.rotShiftV = null; if (sh > 0.005) { b.rotShift = +sh.toFixed(2); b.rotShiftV = [rot[0] - r0[0], rot[2] - r0[2]]; } }
    // (the rest cab stays at the data's stow, which is clear of the neighbours' docked poses; where a shift would shorten
    // the rest tunnel below the model's retraction the pivot rests at the retraction on the same line - round 1 had six
    // such rests, B11, B15, B16, B20, G4, G7 L1; the data now carries the moves and its stows (static P6), 0 shifts today.
    // Moving the stow with the rotunda instead put B15 L1's cab in B16 L1's B744 path.)
    const stowW = b.stowW;
    let walk = (b.walkW && b.walkW.length >= 2) ? b.walkW.map(cz) : [att, rot];
    if (b.rotShift) walk[walk.length - 1] = rot.slice();
    if (Math.hypot(walk[walk.length - 1][0] - rot[0], walk[walk.length - 1][2] - rot[2]) > 0.05) walk.push(rot.slice());
    walk = walk.filter((p, i) => i === 0 || Math.hypot(p[0] - walk[i - 1][0], p[2] - walk[i - 1][2]) > 0.05);
    // the mapped walkway may start inside the (+-5 m) terminal outline: the fixed walkway begins where the polyline last
    // leaves the building (the part inside is the building's own corridor)
    for (let i = walk.length - 2; i >= 0; i--) {
      if (!inBuilding(walk[i][0], walk[i][2], false, true)) continue;
      const A = walk[i], B = walk[i + 1]; if (inBuilding(B[0], B[2], false, true)) break;
      let lo = 0, hi = 1; for (let k = 0; k < 20; k++) { const mid = (lo + hi) / 2; if (inBuilding(A[0] + (B[0] - A[0]) * mid, A[2] + (B[2] - A[2]) * mid, false, true)) lo = mid; else hi = mid; }
      const E = [A[0] + (B[0] - A[0]) * hi, G, A[2] + (B[2] - A[2]) * hi]; b.walkTrim = i + 1;
      walk = [E].concat(walk.slice(i + 1)); break;
    }
    // a walkway whose 2.6 m wide slab runs into the outline beyond its start (A15 L1: the OSM line runs along the
    // pier face and half the slab lies in Boarding Area A for 4 m): its interior vertices are moved straight out of the
    // outline, by at most 2.0 m each (the same OSM roof lean as above; the start at the building and the rotunda stay)
    { const deepest = (i) => { let best = null;
        for (const [j0, j1] of [[i - 1, i], [i, i + 1]]) { if (j0 === 0) continue; // (the first segment leaves the building)
          const A = walk[j0], B = walk[j1]; const L = Math.hypot(B[0] - A[0], B[2] - A[2]); if (L < 0.05) continue;
          const u = [(B[0] - A[0]) / L, (B[2] - A[2]) / L], v = [-u[1], u[0]];
          for (let t = 0; t <= L + 1e-6; t += 0.25) for (const w of [-1, -0.5, 0, 0.5, 1]) {
            const x = A[0] + u[0] * t + v[0] * w * WALK_W / 2, z = A[2] + u[1] * t + v[1] * w * WALK_W / 2; if (!inBuilding(x, z, false, true)) continue;
            const nb = nearestBuilding(x, z, true); if (!nb.p) continue; const d = Math.hypot(nb.p[0] - x, nb.p[1] - z); if (!best || d > best.d) best = { d, x, z, p: nb.p }; } }
        return best; };
      for (let i = 1; i < walk.length - 1; i++) { const v0 = walk[i].slice();
        for (let it = 0; it < 16; it++) { const D = deepest(i); if (!D) break; const l = Math.hypot(D.p[0] - D.x, D.p[1] - D.z) || 1; const m = Math.min(0.5, D.d + 0.1);
          const nv = [walk[i][0] + (D.p[0] - D.x) / l * m, G, walk[i][2] + (D.p[1] - D.z) / l * m]; if (Math.hypot(nv[0] - v0[0], nv[2] - v0[2]) > 2.0) break; walk[i] = nv; }
        const mv = Math.hypot(walk[i][0] - v0[0], walk[i][2] - v0[2]); if (mv > 0.005) b.walkNudge = Math.max(b.walkNudge || 0, +mv.toFixed(2)); } }
    let wl = 0; for (let i = 1; i < walk.length; i++) wl += Math.hypot(walk[i][0] - walk[i - 1][0], walk[i][2] - walk[i - 1][2]);
    // rotunda centreline: the direction the fixed walkway arrives in (prepKin turns it to the arc the bridge serves)
    const n = walk.length; let cl = n >= 2 ? [walk[n - 1][0] - walk[n - 2][0], walk[n - 1][2] - walk[n - 2][2]] : null;
    if (!cl || Math.hypot(cl[0], cl[1]) < 0.5) cl = [nose[0] - rot[0], nose[2] - rot[2]];
    b.walk = walk; b.walkLen = wl; b.acWalk = yawOf(cl[0], cl[1]); b.ac = b.acWalk;
    // model and telescoping geometry
    // the data's model; a bridge the data found no single model for carries the range of the model covering most of its
    // dockings (ext_range) - that model is used
    let spec = PBB[b.model]; if (!spec && b.extRange) { const hit = Object.entries(PBB).find(([, m]) => Math.abs(m[4] - b.extRange[0]) < 0.01 && Math.abs(m[3] - b.extRange[1]) < 0.01); if (hit && !b.upper) { spec = hit[1]; b.modelUsed = hit[0]; } }
    // (which model each bridge is, is the data's inference - "the smallest-retracting model covering the observed
    // dockings" - so its reach decides which parked aircraft the bridge can dock; an aircraft beyond it keeps the bridge
    // at rest)
    let nT, opR, opE, mechE, spacer;
    if (spec) { [nT, , , opE, opR] = spec; spacer = spec[2] - spec[4]; mechE = spec[1] - spacer; }
    else { nT = 3; [opR, opE] = b.extRange || [10.276, 41.381]; spacer = 2.225; mechE = opE + 2.3; }
    const stowL = stowW ? Math.hypot(stowW[0] - rot[0], stowW[1] - rot[2]) : null;
    if (!spec && b.upper) { // upper-deck bridge (no model in the data): the smallest AT3 covering the rest length and the U1L docking
      const eD = this.upperDockExt(g, b, rot);
      // (the smallest datasheet model whose range holds the data's rest length and the U1L docking, +-1 m; else the one
      // that reaches the docking - the bridge then rests at that model's shortest length)
      const fit = (m, tol) => m[4] <= (stowL ?? m[4]) + tol && (stowL == null || m[1] - (m[2] - m[4]) >= stowL) && (eD == null || (m[4] <= eD + 1 && m[3] >= eD - 1));
      // (the rest pose must stay the data's: a model that cannot retract to stow_len is not used)
      let cands = Object.entries(PBB).filter(([, m]) => fit(m, 0.01));
      if (cands.length) cands.sort((a, c) => a[1][4] - c[1][4] || a[1][3] - c[1][3]);
      else if (stowL != null) cands = Object.entries(PBB).filter(([, m]) => m[4] <= stowL && m[1] - (m[2] - m[4]) >= stowL).sort((a, c) => c[1][3] - a[1][3]); // cannot reach U1L: longest model holding the rest pose
      if (cands.length) { const m = cands[0][1]; b.modelUsed = cands[0][0]; [nT, , , opE, opR] = m; spacer = m[2] - m[4]; mechE = m[1] - spacer; }
    }
    const s = (mechE - opR) / (nT - 1) + OVERLAP + STAGGER, F = opR - s - (nT - 1) * STAGGER;
    b.m = { n: nT, opR, opE, mechE, spacer, s, F, wh: SEC_WH[nT] };
    // drum radius: 2.45 m (inferred), at most the data's rotundaMaxR - 0.25 m (half the distance to the neighbouring
    // rotunda / walkway: 0.5 m between drums), clear of the terminal outline (0.2 m), of the other bridges' fixed
    // walkways (0.1 m) and drums; never below DRUM_MIN (the corridor and tunnel A it carries are 2.4 / 2.55 m wide; the
    // rotunda was moved above so that DRUM_MIN fits)
    { let lim = Math.min(2.45, (b.rotundaMaxR ?? 2.7) - 0.25);
      for (const c of this.drumLimits(b, rot[0], rot[2])) if (!c.inside) lim = Math.min(lim, c.kind === 'rotunda' ? (c.d - 0.2) / 2 : c.d - c.extra);
      b.rotR = clampN(lim, DRUM_MIN, 2.45); }
    b.rot = rot; b.att = walk[0];
    // rest pose (data stowW: the cab pivot at rest; cab straight on the tunnel)
    const f = stD(g.dir);
    if (stowW) { b.a0 = yawOf(stowW[0] - rot[0], stowW[1] - rot[2]); b.e0 = clampN(stowL, opR, mechE); }
    else { const dp = doorOf(nose, f, TYPES[REF_TYPE[g.cls] || 'b38m'], b.door).door; b.a0 = yawOf(dp[0] - rot[0], dp[2] - rot[2]); b.e0 = opR; }
    b.stairSide = b.stairSide || 1;
    // legacy fields read by tools (jobs/extract2d.mjs, tools/live/invariants.mjs)
    b.attachW = att; b.attachW3 = att; const lu = [rot[0] - walk[Math.max(0, n - 2)][0], 0, rot[2] - walk[Math.max(0, n - 2)][2]]; b.u = Math.hypot(lu[0], lu[2]) > 0.05 ? v3.norm(lu) : dirOf(b.acWalk);
    b.fixedLen = wl; b.rc = [rot[0], G, rot[2]]; b.parkDir = dirOf(b.a0); b.reach = b.e0;
  }
  // clearance limits of a drum centred at (x, z): the terminal outline (0.2 m), other bridges' mapped fixed walkways
  // (half width + 0.1 m; segments that start or end at this drum - a twin head's connector - or that this bridge's
  // own walkway shares are skipped) and other rotundas (0.2 m between two drums of the minimum radius):
  // [{d, extra, p, kind, inside}] - a drum of radius r fits when d >= r + extra
  drumLimits(b, x, z) {
    const out = []; const nb = nearestBuilding(x, z, false, b._strip); // (not the bridge's own walkway strip, ownStrip)
    if (nb.p) out.push({ d: nb.d, extra: 0.2, p: nb.p, inside: nb.inside, kind: 'building' });
    const own = b.walkW || []; const near = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 0.3;
    for (const o of this.gates) for (const ob of this.bridgesOf(o)) {
      if (ob === b) continue; const ro = ob.rotundaW;
      if (ro && Math.abs(ro[0] - x) < 30 && Math.abs(ro[1] - z) < 30) out.push({ d: Math.hypot(ro[0] - x, ro[1] - z), extra: DRUM_MIN + 0.2, p: ro, kind: 'rotunda' });
      const W = (ob.walkW || []).slice(); if (ro && W.length && Math.hypot(W[W.length - 1][0] - ro[0], W[W.length - 1][1] - ro[1]) > 0.05) W.push(ro);
      for (let i = 1; i < W.length; i++) {
        const A = W[i - 1], B = W[i];
        if (Math.min(A[0], B[0]) > x + 10 || Math.max(A[0], B[0]) < x - 10 || Math.min(A[1], B[1]) > z + 10 || Math.max(A[1], B[1]) < z - 10) continue;
        if (Math.hypot(A[0] - x, A[1] - z) < 0.6 || Math.hypot(B[0] - x, B[1] - z) < 0.6) continue; // connector at this drum
        if (own.some(p => near(p, A)) && own.some(p => near(p, B))) continue;                       // shared walkway
        const ex = B[0] - A[0], ez = B[1] - A[1]; const t = clampN(((x - A[0]) * ex + (z - A[1]) * ez) / (ex * ex + ez * ez || 1), 0, 1);
        const p = [A[0] + ex * t, A[1] + ez * t]; out.push({ d: Math.hypot(p[0] - x, p[1] - z), extra: WALK_W / 2 + 0.1, p, kind: 'walkway' });
      }
    }
    return out;
  }
  prepKin(g, b) {
    b.ac = b.acWalk; b._plans = new Map(); b._own = null; b._restS = b._sq = b._sqX = b._static = b._staticX = null;
    // rotunda centreline (not in the data): the middle of the smallest arc holding the rest pose and every docked pose the
    // bridge serves, when that arc fits the 175 deg swing (the bridge was installed for them); else the walkway direction
    b.swingFree = true; const tg0 = this.dockTargets(g, b); b.swingFree = false;
    { const angs = [b.a0, ...tg0.map(t => t.a)].map(a => wrap(a - b.ac)).sort((x, y) => x - y);
      let gap = -1, gi = 0; for (let i = 0; i < angs.length; i++) { const nx = i + 1 < angs.length ? angs[i + 1] : angs[0] + 2 * Math.PI; if (nx - angs[i] > gap) { gap = nx - angs[i]; gi = i; } }
      const lo = angs[(gi + 1) % angs.length], span = 2 * Math.PI - gap;
      b.swingWide = null; if (span <= 2 * ROT_SWING * DEG) b.ac = wrap(b.ac + lo + span / 2); else b.swingWide = +(span / DEG).toFixed(1); }
    const tg = this.dockTargets(g, b);
    // heights: fixed walkway from the terminal's departure level, sloping at most 1:12 to the rotunda (36 CFR 1191
    // App. D 405.2 ramp slope); rotunda floor chosen so that the docked tunnel slopes as little as possible (minimax over
    // the door sills of every type it docks), with the drum 0.3 m clear above the wings of the stand's aircraft. (Taking
    // only the types observed at the stand, review 2026-11-04, changes nothing for them - observed dockings steeper
    // than 1:12 102 -> 105 of 534, steepest 1:4.4 both ways - because the 1:12 walkway band from the inferred departure
    // level, not the type mix, decides the rotunda height on short walkways.) Upper-deck
    // bridges: a level walkway from an upper level above the main-deck fixed walkways (their roof + 0.6 m; inferred), the
    // tunnel takes the slope down to U1L.
    // (Hb: the pier's bridge level, DEPARTURE_LEVELS - b.HbTag / b.HbSrc for the tools.) The upper level is taken over the
    // highest main-deck roof of the gate that it crosses in plan (0.3 m) - walkway or drum, at rest (solidsQ) - + 0.6 m,
    // i.e. 0.3 m clear under the walkway's 0.3 m floor (and never under level + WALK_H + 0.6): the main-deck walkways rise
    // from a low pier level to their rotunda (BA-G 2.7 m: G13 L2 to 4.54 m, drum roof 7.84 m; with level + WALK_H + 0.6
    // the G13 upper walkway ran through the G13 L1 / L2 walkways, verifier bcheck2 'rest-bridge' x 8, close-out round 3).
    // g.bridges are prepared before g.bridgesUpper (bridgesOf).
    const DL = departureLevel(g);
    if (b.upper) { let top = DL.h + WALK_H; const W = [];
      for (let j = 1; j < (b.walk || []).length; j++) { const P0 = b.walk[j - 1], P1 = b.walk[j]; const d = [P1[0] - P0[0], P1[2] - P0[2]]; const L = Math.hypot(d[0], d[1]); if (L > 0.05) W.push({ c: [(P0[0] + P1[0]) / 2, (P0[2] + P1[2]) / 2], u: [d[0] / L, d[1] / L], hl: L / 2, hw: WALK_W / 2 }); }
      for (const o of g.bridges || []) { if (o.Hr == null || o.h0 == null) continue;
        for (const s of this.solidsQ(o, { a: o.a0, e: o.e0, t: 0, h: o.h0 }, 0, true)) if ((s.part === 'walkway' || s.part === 'rotunda') && W.some(w => solidOverlap(w, s, 0.3))) top = Math.max(top, s.hi - G); }
      b.Hb = +(top + 0.6).toFixed(3); b.HbTag = 'inf'; b.HbSrc = 'upper deck: main-deck walkway / drum roofs it crosses + 0.6 m (inferred; pier ' + DL.tag + ')'; }
    else { b.Hb = DL.h; b.HbTag = DL.tag; b.HbSrc = DL.src; }
    const dh = b.upper ? 0 : b.walkLen / 12;
    b._tgH = tg;
    const Hr = this.pickHr(g, [b], b._tgH, b.Hb - dh, b.Hb + dh);
    this.applyHeights(b, Hr, tg, b._tgH);
    // (HrPinned: the rotunda floor sits on the edge of the walkway's 1:12 band from the pier's bridge level - the level,
    // not the type mix, decides the slope; tools label such slopes with b.HbTag: 'inf' for BA-A / BA-B / BA-C)
    b.HrPinned = tg.length > 0 && (Math.abs(b.Hr - (b.Hb - dh)) < 0.03 || Math.abs(b.Hr - (b.Hb + dh)) < 0.03);
    b._tg = tg; b.reach = b.e0;
  }
  // rotunda floor in [lo, hi] (on the walkway's 1:12 band) minimising the steepest docked tunnel slope of the targets,
  // with every drum of `drums` 0.3 m above the wings of the stand's aircraft where possible
  pickHr(g, drums, tg, lo, hi) {
    const Hb = drums[0].Hb; let Hr = clampN(Hb, lo, hi), best = 1e9;
    const wingAc = this.standAircraft(g);
    const drumOk = (H) => drums.every(d => { const bx = { c: [d.rot[0], d.rot[2]], u: [1, 0], hl: d.rotR, hw: d.rotR, lo: G + H - 0.3, hi: G + H + 3.3 }; return !wingAc.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 0.3)); });
    const worst = (H) => { let w = 0; for (const t of tg) w = Math.max(w, Math.abs(H - t.sill) / Math.max(1, t.e - t.F)); return w; };
    let Hmin = null; for (let H = lo; H <= hi + 1e-6; H += 0.1) if (drumOk(H)) { Hmin = H; break; } // (higher only clears more)
    for (const d of drums) d.drumOverWing = false;
    if (tg.length && Hmin != null) for (let H = Hmin; H <= hi + 1e-6; H += 0.02) { const w = worst(H); if (w < best - 1e-9 || (Math.abs(w - best) < 1e-9 && Math.abs(H - Hb) < Math.abs(Hr - Hb))) { best = w; Hr = H; } }
    if (tg.length && best > 1e8) { for (const d of drums) d.drumOverWing = true; for (let H = lo; H <= hi + 1e-6; H += 0.02) { const w = worst(H); if (w < best) { best = w; Hr = H; } } }
    else if (!tg.length && Hmin != null) Hr = Math.min(hi, Math.max(Hb, Hmin));
    return Hr;
  }
  // rotunda floor Hr; rest height h0 = middle of the sills of the height targets, on a rest tunnel sloping <= 1:12
  // (the height is pre-positioned when docking)
  applyHeights(b, Hr, tg, tgH) {
    b.Hr = +Hr.toFixed(3); let w = 0; for (const t of tg) w = Math.max(w, Math.abs(b.Hr - t.sill) / Math.max(1, t.e - b.m.F)); b.slopeMax = w;
    const sills = (tgH || tg).map(t => t.sill); b.h0 = sills.length ? (Math.min(...sills) + Math.max(...sills)) / 2 : b.Hr;
    b.h0 = this.bandH(b, b.e0, b.h0, SLOPE_TARGET); b.hRest = b.h0; b._own = null; b._restS = null; b._plans = new Map();
  }
  // height h clamped to the band where the tunnel at pivot distance e slopes at most `slope`
  // (1e-9 m inside the band: on its edge, Hr + lim - Hr over (e - F) read 0.25000000000000006 > 1:4 in the verifier)
  bandH(b, e, h, slope) { const lim = Math.max(0, Math.max(0, e - b.m.F) * slope - 1e-9); return clampN(h, b.Hr - lim, b.Hr + lim); }
  // the moving parts of bridge b in joint state q against its obstacles (the fixed walkways, drums and pedestals of the
  // bridges around it and its own fixed walkway outside its drum): the first contact 'part x part', or null
  fixedHit(b, q, kk = 0) {
    const O = b._obs; if (!O || !O.length) return null;
    for (const bx of this.solidsQ(b, q, kk)) { if (bx.part === 'stair') continue; // (its side is chosen against these in finishPrep)
      const br = Math.hypot(bx.hl, bx.hw);
      for (const o of O) { // (the rotunda corridor starts clear of the own walkway: neckStart - no exemption since round 3)
        if (Math.abs(o.c[0] - bx.c[0]) > o.rr + br + 0.1 || Math.abs(o.c[1] - bx.c[1]) > o.rr + br + 0.1) continue;
        if (bx.hi > o.lo && o.hi > bx.lo && solidOverlap(bx, o, 0.05)) return bx.part + ' x ' + (o.own ? 'own ' : '') + o.part; } }
    return null;
  }
  // the first moving part of bridge b in joint state q inside a building outline (solidInBuilding: the outline
  // js/live/terminals.js draws, the SFO Museum outlines of the 3-D building assets, the sky bridges at their height) or in
  // a 3-D asset at its height (solidInAsset, close-out round 5), or null
  bldHit(b, q, kk = 0) { for (const bx of this.solidsQ(b, q, kk)) if (bx.part !== 'stair' && (solidInBuilding(bx, b._strip) || solidInAsset(bx))) return bx.part; return null; }
  // a fixed-walkway support column (r 0.35 m) at p: outside every outline (the bridge's own Museum walkway strip
  // excepted, ownStrip) and 0.6 m clear of the drawn outline and the sky bridges, as before the Museum outlines were
  // added (the Museum strips' edges run along the mapped walkways, 0-0.5 m off; tools: the column count per bridge)
  columnOk(b, p) { return !inBuilding(p[0], p[2], true, false, b._strip) && nearestBuilding(p[0], p[2], false, null, true).d >= 0.6; }
  // the part of an own walkway solid outside the bridge's drum (the walkway enters the drum by design), or null
  outsideDrum(b, s, R = b.rotR) {
    const A = [s.c[0] - s.u[0] * s.hl, s.c[1] - s.u[1] * s.hl], L = 2 * s.hl; const dist = (t) => Math.hypot(A[0] + s.u[0] * t - b.rot[0], A[1] + s.u[1] * t - b.rot[2]);
    let t0 = 0, t1 = L; if (dist(0) < R) { let lo = 0, hi = L; if (dist(L) < R) return null; for (let k = 0; k < 24; k++) { const m = (lo + hi) / 2; if (dist(m) < R) lo = m; else hi = m; } t0 = hi; }
    if (dist(L) < R) { let lo = t0, hi = L; for (let k = 0; k < 24; k++) { const m = (lo + hi) / 2; if (dist(m) < R) hi = m; else lo = m; } t1 = lo; }
    if (t1 - t0 < 0.05) return null; const c = (t0 + t1) / 2;
    return { ...s, c: [A[0] + s.u[0] * c, A[1] + s.u[1] * c], hl: (t1 - t0) / 2 };
  }
  // service landing + stair on the outer tunnel aft of the cab bubble (sheet options C / D; standard: the right-hand
  // side): the side where it meets nothing - no docked aircraft of a type the bridge serves, no aircraft of the stand
  // while the bridge rests, no other bridge at rest (checked at rest and in every docked pose)
  finishPrep() {
    if (this._fin) return; this._fin = true;
    const all = []; for (const g of this.gates) for (const b of this.bridgesOf(g)) { if (!b.m) this.prepBridge(g, b); all.push({ g, b }); }
    for (const g of this.gates) if (g.bridges && g.bridges.length > 1) this.shareWalks(g);
    // obstacles of the moving parts: the fixed walkways, drums and pedestals of every other bridge within reach, and the
    // bridge's own fixed walkway outside its drum (a rotunda corridor never swings through a fixed walkway: review
    // 2026-11-04, F15 L1's corridor through F15 L2's twin connector)
    const fixed = new Map(all.map(({ b }) => [b, this.solidsQ(b, { a: b.a0, e: b.e0, t: 0, h: b.h0 }, 0, true).filter(s => s.part === 'walkway' || s.part === 'rotunda' || s.part === 'pedestal')]));
    for (const { b } of all) {
      const reach = b.m.mechE + b.m.spacer + 4; const O = [];
      for (const { b: o } of all) { if (o === b) continue; for (const s of fixed.get(o)) if (Math.hypot(s.c[0] - b.rot[0], s.c[1] - b.rot[2]) - Math.hypot(s.hl, s.hw) < reach) O.push(s); }
      // (own walkway: beyond 0.6 m from the drum, against every moving part - the rotunda corridor too: it starts where it
      // leaves the walkway (neckParts; before round 3 it was exempt and drawn through the walkway of A12, F5, F14, F17,
      // F19, F21 L1, whose data poses fold back to 41-45 deg from the mapped walkway)
      for (const s of fixed.get(b)) if (s.part === 'walkway') { const c = this.outsideDrum(b, s, b.rotR + 0.6); if (c) O.push({ ...c, own: true }); }
      b._obs = O.map(o => ({ ...o, rr: o.round || Math.hypot(o.hl, o.hw) }));
    }
    // a data rest pose (stowW) whose corridor / tunnel lies in a fixed walkway (A12, F5, F14, F17, F19, F21 L1: the
    // stow folds back to 41-45 deg from the bridge's own walkway, so the 2.4 m corridor runs through it) is turned
    // away from it, by the smallest angle (<= 60 deg) that clears every fixed part, every aircraft its stand and the
    // alternative positions accept (1 m, the stow criterion of the stand data), the aircraft of the stands around it
    // (0.5 m) and the other bridges at rest; where none does, the data pose stays (b.restBlocked)
    { const restS = new Map(all.map(({ b }) => [b, this.solidsQ(b, { a: b.a0, e: b.e0, t: 0, h: b.h0 }, 0, true)]));
      for (const { g, b } of all) {
        const q0 = { a: b.a0, e: b.e0, t: 0, h: b.h0 }; if (!this.fixedHit(b, q0, 0) && !this.bldHit(b, q0, 0)) continue;
        const own = this.standAircraft(g); const nb = [];
        for (const o of this.gates) { if (o === g || !o.bridge && !(o.sharesBridgesOf)) continue; const on = stW(o.nose, G); if (Math.hypot(on[0] - b.rot[0], on[2] - b.rot[2]) > 120) continue; for (const A of this.standAircraft(o)) nb.push(A); }
        const others = all.filter(x => x.b !== b && Math.hypot(x.b.rot[0] - b.rot[0], x.b.rot[2] - b.rot[2]) < 80).map(x => restS.get(x.b)).flat();
        const clear = (q) => { if (this.fixedHit(b, q, 0) || this.bldHit(b, q, 0)) return false; const S = this.solidsQ(b, q, 0);
          for (const bx of S) { if (own.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 1.0)) || nb.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 0.5))) return false;
            if (others.some(o => bx.hi > o.lo && o.hi > bx.lo && solidOverlap(bx, o, 0.3))) return false;
            if (bx.part !== 'stair' && [[0, 0], [1, 1], [1, -1], [-1, 1], [-1, -1]].some(([i, j]) => inBuilding(bx.c[0] + bx.u[0] * bx.hl * i - bx.u[1] * bx.hw * j, bx.c[1] + bx.u[1] * bx.hl * i + bx.u[0] * bx.hw * j, false, false, b._strip))) return false; }
          return true; };
        let pick = null; for (let d = 1; d <= 60 && !pick; d++) for (const sg of [1, -1]) { const q = { ...q0, a: b.a0 + sg * d * DEG }; if (clear(q)) { pick = { q, d: sg * d }; break; } }
        if (pick) { b.restTurn = pick.d; b.a0 = pick.q.a; b.parkDir = dirOf(b.a0); restS.set(b, this.solidsQ(b, pick.q, 0, true)); } else b.restBlocked = true;
      } }
    for (const { g, b } of all) this.prepKin(g, b);
    // twin heads (a walkway branching through one rotunda to a second one 3.4 m away: F15, G12): both drums on one floor
    // level (the connector between them is level; before, it met the first drum 0.7 m above its floor)
    for (const { g, b } of all) if (b.twinOf) {
      const o = b.twinOf; const dh = o.walkLen / 12;
      const Hr = this.pickHr(g, [o, b], o._tgH.concat(b._tgH), o.Hb - dh, o.Hb + dh);
      this.applyHeights(o, Hr, o._tg, o._tgH); this.applyHeights(b, Hr, b._tg, b._tgH);
    }
    // (an upper-deck bridge's level follows its gate's main-deck rotunda floors, which the twin step may have moved)
    for (const { g, b } of all) if (b.upper && (g.bridges || []).some(o => o.twinOf)) this.prepKin(g, b);
    // own-walkway clip check (review 2026-11-04 bridges-v3): the rotunda corridor parts vs the bridge's own walkway outside
    // the drum at rest and docked. Since round 3 (neckParts) it is 0 everywhere - before, A12, F5, F14, F17, F19, F21 L1
    // (data poses folded back to 41-45 deg from the walkway) drew 0.18-0.56 m2 of corridor through it. b.ownClip = {rest,
    // docked (m2, exact plan overlap), poses (n of m)} or null, for the tools
    for (const { g, b } of all) { const W = this.solidsQ(b, { a: b.a0, e: b.e0, t: 0, h: b.h0 }, 0, true).filter(x => x.part === 'walkway').map(x => this.outsideDrum(b, x, b.rotR)).filter(Boolean); b.ownClip = null; if (!W.length) continue;
      const area = (q) => { let A = 0; for (const nk of this.solidsQ(b, q, 0)) if (nk.part === 'neck') for (const w of W) if (nk.hi > w.lo && w.hi > nk.lo) A += obbArea(nk, w); return A; };
      const rest = area({ a: b.a0, e: b.e0, t: 0, h: b.h0 }); let worst = rest, n = rest > 0.05 ? 1 : 0; const tg = b._tg || [];
      for (const t of tg) { const A = area({ a: t.a, e: t.e, t: 0, h: t.sill }); if (A > 0.05) n++; worst = Math.max(worst, A); }
      b.ownClip = worst > 0.05 ? { rest: +rest.toFixed(2), docked: +worst.toFixed(2), poses: n + '/' + (tg.length + 1) } : null; }
    const restOf = new Map(all.map(({ b }) => [b, this.solidsQ(b, { a: b.a0, e: b.e0, t: 0, h: b.h0 }, 0, true)]));
    for (const { g, b } of all) {
      const others = all.filter(o => o.b !== b && Math.hypot(o.b.rot[0] - b.rot[0], o.b.rot[2] - b.rot[2]) < 70).map(o => restOf.get(o.b)).flat()
        .map(o => ({ o, r: Math.hypot(o.hl, o.hw) }));
      const acs = this.standAircraft(g); const tg = b._tg || [];
      const q0 = { a: b.a0, e: b.e0, t: 0, h: b.h0 };
      const poses = [{ q: q0, ac: acs }].concat(tg.map(t => ({ q: { a: t.a, e: t.e, t: 0, h: t.sill }, ac: [{ T: TYPES[t.key], nose: [t.nose[0], t.nose[2]], f: [t.f[0], t.f[2]] }] })),
        this.sweepQ(g, b, false).filter((q, i) => i % 3 === 0).map(q => ({ q, ac: [] }))); // (every candidate docking path, sampled)
      const bad = {};
      // (weighted by how long a pose lasts: the rest pose for hours (x10), a docked pose for the turnaround (x4), a path
      // sample for seconds (x1) - G7 L1, its rotunda moved 0.8 m off Boarding Area G, took the side whose stair rests in
      // G7 L2's drum over one whose stair crosses the Museum outline for 4 of 97 path samples)
      for (const sd of [1, -1]) { b.stairSide = sd; let n = 0;
        poses.forEach((P, i) => { const S = this.stairBoxes(b, P.q); const w = i === 0 ? 10 : i <= tg.length ? 4 : 1;
          if (S.some(bx => P.ac.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 0.5)))) n += 2 * w;
          if (S.some(bx => { const rb = Math.hypot(bx.hl, bx.hw) + 0.3; return others.some(({ o, r }) => Math.abs(o.c[0] - bx.c[0]) < r + rb && Math.abs(o.c[1] - bx.c[1]) < r + rb && o.hi > bx.lo && o.lo < bx.hi && solidOverlap(bx, o, 0.3)); })) n += w;
          if (S.some(bx => { const v = [-bx.u[1], bx.u[0]]; return [[1, 1], [1, -1], [-1, 1], [-1, -1], [0, 0]].some(([i, j]) => inBuilding(bx.c[0] + bx.u[0] * bx.hl * i + v[0] * bx.hw * j, bx.c[1] + bx.u[1] * bx.hl * i + v[1] * bx.hw * j)); })) n += 2 * w; });
        bad[sd] = n; }
      b.stairSide = bad[-1] < bad[1] ? -1 : 1;
    }
  }
  // every accepted type of the stand (and of the alternative positions sharing its bridges) at its stop: {T, nose, f}
  standAircraft(g) {
    if (g._acs) return g._acs; const out = [];
    for (const { s } of this.standPoses(g)) for (const A of this.acceptedTypes(s)) {
      const fam = familyOf(A.icao); const st = fam && s.typeStops && s.typeStops[fam]; const along = st && Number.isFinite(st.along) ? Math.min(0, st.along) : 0;
      const f = stD(s.dir); const n = v3.add(stW(s.nose, G), v3.mul(f, along)); out.push({ T: A.T, key: A.key, nose: [n[0], n[2]], f: [f[0], f[2]] });
    }
    return (g._acs = out);
  }
  // docking extension of an upper-deck bridge to the A380's U1L at the stand
  upperDockExt(g, b, rot) {
    const T = TYPES.a388; if (!T) return null; const { door, left } = doorOf(stW(g.nose, G), stD(g.dir), T, 3);
    const p = v3.add(door, v3.mul(left, 2.225)); return Math.hypot(p[0] - rot[0], p[2] - rot[2]);
  }
  // the aircraft this bridge docks at its stand (and the alternative positions sharing its bridges): accepted types
  // (js/live/traffic.js standFits, replicated: class limits, span_max / len_max, types_ok, A380 only on a380 stands) at
  // their stop points (types_stops), each with the feasibility of its docked pose (range, cab turn, rotunda swing)
  acceptedTypes(g) {
    if (g._acc && g._accKey === (g.typesOk || []).join() + g.maxSpan + g.maxLen) return g._acc;
    const ok = g.typesOk && g.typesOk.length ? new Set(g.typesOk) : null; const out = [];
    for (const [k, T] of Object.entries(TYPES)) {
      if (!T || !T.wing || !T.doors || k.startsWith('biz_') || T.cls === 'H') continue;
      const icao = ICAO_OF[k]; if (!icao) continue;
      if (ok && !ok.has(icao)) continue;
      const span = T.wing.span; const fits = !g.maxSpan || (span <= g.maxSpan + 0.6 && T.L <= g.maxLen + 2) || (!!g.a380 && span <= 80);
      if (fits) out.push({ key: k, icao, T });
    }
    g._accKey = (g.typesOk || []).join() + g.maxSpan + g.maxLen; return (g._acc = out);
  }
  standPoses(g) { // [{g0 (stand), nose world, f}] for the stand itself and its alternative positions sharing its bridges
    const out = [{ s: g }];
    for (const o of this.gates || []) if (o !== g && o.sharesBridgesOf === g.name && !(o.bridges && o.bridges.length)) out.push({ s: o });
    return out;
  }
  dockTargets(g, b) {
    const out = [];
    for (const { s } of this.standPoses(g)) for (const A of this.acceptedTypes(s)) {
      if (b.upper && A.key !== 'a388') continue;
      if (!b.upper && b.door === 2 && A.T.dockX2 == null) continue;
      const fam = familyOf(A.icao); const st = fam && s.typeStops && s.typeStops[fam]; const along = st && Number.isFinite(st.along) ? Math.min(0, st.along) : 0;
      const f = stD(s.dir); const nose = v3.add(stW(s.nose, G), v3.mul(f, along));
      const q = this.dockPose(b, A.T, nose, f, b.door);
      if (!q || !this.jointOk(b, q, A.icao).ok) continue;
      out.push({ key: A.key, icao: A.icao, sill: q.h, e: q.e, a: q.a, F: b.m.F, nose, f, stand: s.name });
    }
    return out;
  }
  // docked joint state {a, e, t, h} for type T with its nose at `nose`, heading f (world); pivot = door + left * spacer
  dockPose(b, T, nose, f, which, standoff = 0) {
    if (!T || !b.m) return null;
    const { door, left } = doorOf(nose, f, T, which);
    const p = v3.add(door, v3.mul(left, b.m.spacer + standoff));
    const a = yawOf(p[0] - b.rot[0], p[2] - b.rot[2]); const e = Math.hypot(p[0] - b.rot[0], p[2] - b.rot[2]);
    const c = yawOf(-left[0], -left[2]);
    return { a, e, t: wrap(c - a), h: door[1] - G, door, left, pivot: p };
  }
  // sheet limits for a joint state: operational range (-1 m / up to the mechanical stop, below), cab turn, rotunda swing
  jointOk(b, q, icao) {
    const m = b.m; const turn = CW * q.t / DEG; const opt = b.cabOption && /^optional/.test(b.cabOption);
    if (icao && b.dockTypesOut && b.dockTypesOut.includes(icao)) return { ok: false, why: 'dock_types_out' };
    // (reach: the sheet's operational range; up to 0.3 m short of the mechanical stop - fully extended minus the cab
    // spacer - where a parked aircraft stands beyond it: the tunnels can travel there, the data's model is an inference.
    // INFERRED allowance: review 2026-11-04 counted 199 of 3,282 dockings beyond the operational extension, by up to
    // 1.05 m; the fix belongs to the data's model choice - docs/requests/bridges_closeout.md. The optional 185 deg cab
    // split, CAB_OPT_HALF, is inferred too: 17 dockings turn it 38.7-48.2 deg ccw, on bridges whose data cab_option
    // says "optional 185 deg cab needed (inferred)".)
    // (below the operational retraction the sections cannot telescope any further: sections() clamps there)
    if (q.e < m.opR - 1e-6 || q.e > Math.max(m.opE, m.mechE - 0.3)) return { ok: false, why: `extension ${q.e.toFixed(1)} m outside ${m.opR}-${m.opE} (mechanical ${m.mechE.toFixed(1)})` };
    if (opt ? Math.abs(turn) > CAB_OPT_HALF : (turn > CAB_CW || turn < -CAB_CCW)) return { ok: false, why: `cab turn ${turn.toFixed(0)} deg` };
    if (!b.swingFree && Math.abs(wrap(q.a - b.ac)) > ROT_SWING * DEG + 1e-6) return { ok: false, why: `rotunda swing ${(wrap(q.a - b.ac) / DEG).toFixed(0)} deg` };
    const fh = this.fixedHit(b, q, 1); if (fh) return { ok: false, why: `${fh} (fixed bridge parts)` };
    const bh = this.bldHit(b, q, 1); if (bh) return { ok: false, why: `${bh} inside the building outline` };
    return { ok: true };
  }
  // ------------------------------------------------------------ docking plan (joint path) for the current occupant
  planKey(g, b) { const T = g.acType || g._lastType || ''; const d = g.dock; return T + '|' + (d ? d.nose[0].toFixed(2) + ',' + d.nose[1].toFixed(2) + ',' + d.dir[0].toFixed(4) + ',' + d.dir[1].toFixed(4) : 'stand') + '|' + (g.dockType || ''); }
  planFor(g, b) {
    if (!b.m) this.prepBridge(g, b);
    const key = this.planKey(g, b); let P = b._plans.get(key); if (P) return P;
    P = this.makePlan(g, b); if (b._plans.size > 24) b._plans.clear(); b._plans.set(key, P); return P;
  }
  makePlan(g, b, opts = {}) {
    const tk = g.acType || g._lastType; const T = tk ? TYPES[tk] : null; const icao = g.dockType || (tk && ICAO_OF[tk]) || null;
    const q0 = { a: b.a0, e: b.e0, t: 0, h: b.hRest ?? b.h0 };
    const no = (why) => ({ ok: false, why, T, q0, path: [q0], dur: [], total: 0 });
    if (!T) return no('no aircraft');
    if (b.upper) { if (tk !== 'a388') return no('upper deck: A380 only'); }
    else if (b.door === 2 && T.dockX2 == null) return no('no second-bridge door');
    const dn = g.dock ? g.dock.nose : g.nose, dd = g.dock ? g.dock.dir : g.dir;
    const f = stD(dd), nose = stW(dn, G);
    const q1 = this.dockPose(b, T, nose, f, b.door); if (!q1) return no('no door');
    const j = this.jointOk(b, q1, icao); if (!j.ok) return no(j.why);
    const slope = this.slopeOf(b, q1.e, q1.h);
    if (slope > SLOPE_MAX) return no(`slope 1:${(1 / slope).toFixed(1)} steeper than 1:4`);
    let so = STANDOFF, qs = null;
    for (; so >= 0.4; so -= 0.3) { qs = this.dockPose(b, T, nose, f, b.door, so); if (qs.e <= b.m.mechE && this.jointOk(b, qs, null).ok) break; qs = null; }
    if (!qs) return no('no stand-off point');
    qs.h = this.bandH(b, qs.e, qs.h, SLOPE_MAX); // (the stand-off point is nearer the rotunda: at most 1:4 there too)
    const nose2 = [nose[0], nose[2]], f2 = [f[0], f[2]];
    const mk = (pts) => { const dur = []; for (let i = 1; i < pts.length; i++) dur.push(this.segTime(b, pts[i - 1], pts[i], i === pts.length - 1)); return { pts, dur }; };
    // candidate paths: direct; retract - swing - extend; swing at the rest extension. (Swinging half or fully extended
    // was tried for F11 L2 to a 777, review 2026-11-04: from its data rest pose every swing passes the 777's wing or
    // engine, so no other family docks it.) The height is pre-positioned while the tunnels move but never at a
    // retracted, steep length: it stays the rest height (within 1:4) until the final extension to the stand-off point
    // (the old retract path put the door height on the retracted tunnel: 1:2.9); a linear segment between two poses
    // within 1:4 stays within 1:4 (|Hr - h| / (e - F) is monotonic along it)
    const hR = this.bandH(b, b.m.opR, q0.h, SLOPE_MAX);
    const cands = [
      [q0, { ...qs }, q1],
      [q0, { a: q0.a, e: b.m.opR, t: 0, h: hR }, { a: qs.a, e: b.m.opR, t: qs.t, h: hR }, qs, q1],
      [q0, { a: qs.a, e: q0.e, t: qs.t, h: q0.h }, qs, q1],
    ];
    if (opts.all) { // every candidate path, unchecked (a superset of the path actually used: VDGS clearance sweeps)
      return { ok: true, T, q0, q1, qs, path: cands[0], alts: cands.map(p => p), dur: mk(cands[0]).dur, total: 1, slope, door: q1.door };
    }
    let fixedOnly = true;
    for (const pts of cands) {
      const { dur } = mk(pts);
      const h = this.pathHits(b, pts, T, nose2, f2);
      if (!h) { const total = dur.reduce((x, y) => x + y, 0); return { ok: true, T, q0, q1, qs, path: pts, dur, total, slope, door: q1.door }; }
      if (h === 'aircraft') fixedOnly = false;
    }
    return no(fixedOnly ? 'every docking path passes through a fixed walkway / drum / the building' : 'every docking path passes through the aircraft');
  }
  // undocking plan: the docking path backwards, the cab at the door's height as far as the tunnel allows - each pose at
  // most 1:4 (AC 150/5220-21C §3.4.b(6)), so a short rest tunnel moves the cab towards the rotunda floor on the way
  // (timed at the sheet's lift rate); at rest the cab then settles to the rest height h0 (step(): settles)
  levelPlan(b, P) {
    const n = P.path.length; const path = P.path.map((q, i) => ({ ...q, h: i === n - 1 ? P.q1.h : this.bandH(b, q.e, P.q1.h, SLOPE_MAX) }));
    const dur = []; for (let i = 1; i < path.length; i++) dur.push(this.segTime(b, path[i - 1], path[i], i === path.length - 1));
    return { ...P, path, q0: path[0], dur, total: dur.reduce((x, y) => x + y, 0), _pk: undefined, _h1: undefined, _level: undefined };
  }
  // a segment at the sheet's maximum rates, without the 3 s allowance per motion and with the back-off from the door at
  // the drive speed (the engine's fast retraction: hurryUndock)
  segTimeMin(b, A, B) {
    return Math.max(0.5, this.segPeak(b, A, B) / DRIVE_V, Math.abs(B.t - A.t) / CAB_RATE, Math.abs(B.h - A.h) / LIFT_RATE);
  }
  segTime(b, A, B, approach) {
    if (approach) return Math.max(2, this.segPeak(b, A, B) / APPROACH_V, Math.abs(B.h - A.h) / LIFT_RATE);
    return 3 + Math.max(this.segPeak(b, A, B) / DRIVE_V, Math.abs(B.t - A.t) / CAB_RATE, Math.abs(B.h - A.h) / LIFT_RATE);
  }
  // peak horizontal speed of the cab pivot along a segment per unit of the segment parameter (m): qLerp moves the angle
  // and the extension linearly, so |dp/du| = hypot(de, e(u) * da) peaks at the longer end - exact, no sampling. Timing a
  // segment by it keeps the pivot (and the drive column, which is nearer the rotunda: always slower) at or under the
  // sheet's 27 m/min at every instant (review 2026-11-04: timed by the mean, the drive column peaked at 0.486 m/s)
  segPeak(b, A, B) {
    const oa = wrap(A.a - b.ac), ob = wrap(B.a - b.ac);
    return Math.hypot(B.e - A.e, Math.max(A.e, B.e) * (ob - oa));
  }
  qLerp(b, A, B, u) {
    const oa = wrap(A.a - b.ac), ob = wrap(B.a - b.ac); // rotunda angle relative to its centreline (stays inside the swing)
    return { a: b.ac + oa + (ob - oa) * u, e: A.e + (B.e - A.e) * u, t: A.t + (B.t - A.t) * u, h: A.h + (B.h - A.h) * u };
  }
  // (toDoor: the path ends at the door - its last segment deploys the closure, so the cab / bellows may meet the skin there;
  // false: a way back to rest, every part tested on every segment. count: go on and return {fixed, n, n0} - n = sampled
  // poses with a part within the clearance of the aircraft, n0 = in it (no clearance), fixed = a fixed walkway / drum /
  // building was met)
  pathHits(b, pts, T, nose, f, toDoor = true, count = false) {
    let n0 = 0, nIn = 0, fx = false;
    for (let i = 1; i < pts.length; i++) {
      const last = i === pts.length - 1; const n = last ? 4 : 16; const door = toDoor && last;
      for (let k = 0; k <= n; k++) {
        const q = this.qLerp(b, pts[i - 1], pts[i], k / n);
        if (this.fixedHit(b, q, door && k > 0 ? 1 : 0)) { if (!count) return 'fixed'; fx = true; } // through a fixed walkway / drum (own or another bridge's)
        if (this.bldHit(b, q, door && k > 0 ? 1 : 0)) { if (!count) return 'building'; fx = true; } // through a terminal outline (drawn or SFO Museum)
        for (const bx of this.solidsQ(b, q, door && k > 0 ? 1 : 0)) {
          if (door && (bx.part === 'cab' || bx.part === 'bellows')) continue; // the closure meets the door by design
          if (boxHitsAc(bx, T, nose, f, bx.part === 'cab' ? 0.3 : 0.5)) { if (!count) return 'aircraft'; n0++; if (this.solidsQ(b, q, door && k > 0 ? 1 : 0).some(c => !(door && (c.part === 'cab' || c.part === 'bellows')) && boxHitsAc(c, T, nose, f, 0))) nIn++; break; }
        }
      }
    }
    return count ? { fixed: fx, n: n0, n0: nIn } : false;
  }

  // joint state at animation parameter k (0 rest .. 1 docked) along a plan's path (time-proportional)
  qAt(b, P, k) {
    if (!P.ok || !P.total) return P.q0;
    let t = clampN(k, 0, 1) * P.total;
    for (let i = 0; i < P.dur.length; i++) { if (t <= P.dur[i] || i === P.dur.length - 1) return this.qLerp(b, P.path[i], P.path[i + 1], P.dur[i] ? clampN(t / P.dur[i], 0, 1) : 1); t -= P.dur[i]; }
    return P.q1;
  }
  // ------------------------------------------------------------ pose: key points of a bridge at extension k
  pose(g, b, k) {
    if (!this._fin) this.finishPrep();
    if (!b.m) this.prepBridge(g, b);
    const a = this.anims && this.anims.get(g.id);
    let P = (a && a.plans && a.plans.get(b)) || null;
    if (!P) P = this.planFor(g, b);
    const q = !P.ok || (k <= 0 && !(a && a.plans)) ? this.restNow(b) : this.qAt(b, P, k); // (a bridge that does not dock: its rest per occupant)
    const T = P.T || TYPES[g.acType] || TYPES[g._lastType] || TYPES[REF_TYPE[g.cls] || 'b38m'];
    let door = P.door;
    if (!door) { const dn = g.dock ? g.dock.nose : g.nose, dd = g.dock ? g.dock.dir : g.dir; door = doorOf(stW(dn, G), stD(dd), T, b.door).door; }
    const approach = P.ok && P.dur.length && !P.toRest ? clampN((clampN(k, 0, 1) * P.total - (P.total - P.dur[P.dur.length - 1])) / P.dur[P.dur.length - 1], 0, 1) : 0;
    return this.poseQ(b, q, { T, door, kk: approach, plan: P });
  }
  poseQ(b, q, extra = {}) {
    const u = dirOf(q.a); const piv = [b.rot[0] + u[0] * q.e, G + q.h, b.rot[2] + u[2] * q.e];
    const facing = dirOf(q.a + q.t);
    return { attach: b.att, u: b.u, rc: b.rc, floorY: G + b.Hr, cab: piv, facing, door: extra.door || null, T: extra.T || null, kk: extra.kk || 0, q, dir: u, walk: b.walk, plan: extra.plan || null };
  }
  // ------------------------------------------------------------ solids (oriented boxes, world heights) of a bridge
  // {c: [x, z], u: [ux, uz], hl, hw (half sizes), lo, hi (world y), part} - the collision shape of the drawn bridge, used
  // for the docking-path test, the GSE and VDGS placement and by the checkers (tools/live/invariants.mjs,
  // jobs/extract2d.mjs may use solids(g, b, k) instead of re-deriving the parts)
  solids(g, b, k) { const P = this.pose(g, b, k); return this.solidsQ(b, P.q, P.kk, true); }
  solidsQ(b, q, kk = 0, fixed = false) {
    const out = []; const m = b.m; const u = dirOf(q.a); const rot = b.rot;
    const fl = (s) => G + this.floorAt(b, q, s);  // tunnel floor height at distance s from the rotunda centre
    const seg = (s0, s1, w, h, part, lo0 = null) => { const cx = rot[0] + u[0] * (s0 + s1) / 2, cz = rot[2] + u[2] * (s0 + s1) / 2; const a = Math.min(fl(s0), fl(s1)), c = Math.max(fl(s0), fl(s1)); out.push({ c: [cx, cz], u: [u[0], u[2]], hl: (s1 - s0) / 2, hw: w / 2, lo: (lo0 ?? a) - 0.15, hi: c + h, part }); };
    if (fixed) {
      for (const S of this.ownWalk(b)) { const A = S.A, B = S.B; const d = [B[0] - A[0], B[2] - A[2]]; const L = Math.hypot(d[0], d[1]); if (L < 0.05) continue; out.push({ c: [(A[0] + B[0]) / 2, (A[2] + B[2]) / 2], u: [d[0] / L, d[1] / L], hl: L / 2, hw: WALK_W / 2, lo: Math.min(A[1], B[1]) - 0.3, hi: Math.max(A[1], B[1]) + WALK_H, part: 'walkway', seg: S.i }); }
      out.push({ c: [rot[0], rot[2]], u: [1, 0], hl: b.rotR, hw: b.rotR, lo: G + b.Hr - 0.3, hi: G + b.Hr + 3.3, part: 'rotunda', round: b.rotR });
      out.push({ c: [rot[0], rot[2]], u: [1, 0], hl: 0.6, hw: 0.6, lo: G, hi: G + b.Hr - 0.3, part: 'pedestal', round: 0.6 });
    }
    for (const N of this.neckParts(b, q.a)) { const sc = (N.s0 + N.s1) / 2, rr = [-u[2], u[0]]; out.push({ c: [rot[0] + u[0] * sc + rr[0] * N.off, rot[2] + u[2] * sc + rr[1] * N.off], u: [u[0], u[2]], hl: (N.s1 - N.s0) / 2, hw: N.hw, lo: Math.min(fl(N.s0), fl(N.s1)) - 0.15, hi: Math.max(fl(N.s0), fl(N.s1)) + 2.8, part: 'neck' }); }
    const secs = this.sections(b, q.e);
    secs.forEach(([s0, s1, w, h], i) => seg(s0, s1, w, h, 'tunnel' + (i + 1)));
    // drive column (legs + bogie + cross beam, +-1.55 m) on the outer tunnel, its control box on the right-hand leg, and
    // the pre-conditioned-air unit + hose basket slung under the outer tunnel (as bridgeGeo draws them)
    const dc = this.driveAt(b, q.e); const cx = rot[0] + u[0] * dc, cz = rot[2] + u[2] * dc; const rt = [-u[2], u[0]];
    out.push({ c: [cx, cz], u: [u[0], u[2]], hl: 0.6, hw: 1.6, lo: G, hi: fl(dc), part: 'column' });
    { const y = fl(dc) - 0.15; out.push({ c: [cx + rt[0] * 1.7, cz + rt[1] * 1.7], u: [u[0], u[2]], hl: 0.35, hw: 0.2, lo: y - 0.9, hi: y, part: 'drive_ctrl' }); }
    { const ps = Math.max(secs[secs.length - 1][0] + 0.7, dc - 1.8); const y = fl(ps) - 0.15; const c = [rot[0] + u[0] * ps, rot[2] + u[2] * ps];
      if (y - G > 1.8) out.push({ c, u: [u[0], u[2]], hl: 0.6, hw: 1.2, lo: y - 1.5, hi: y - 0.15, part: 'pca' });
      if (y - G > 2.3) out.push({ c, u: [u[0], u[2]], hl: 0.45, hw: 0.5, lo: y - 2.0, hi: y - 1.5, part: 'pca_basket' }); }
    // cab (body + closure), about the pivot, facing q.a + q.t
    const fc = dirOf(q.a + q.t); const piv = [rot[0] + u[0] * q.e, rot[2] + u[2] * q.e]; const front = m.spacer - 0.45 + 0.45 + 0.15 * kk;
    out.push({ c: [piv[0] + fc[0] * (front - CAB_BACK) / 2, piv[1] + fc[2] * (front - CAB_BACK) / 2], u: [fc[0], fc[2]], hl: (front + CAB_BACK) / 2, hw: CAB_W / 2, lo: G + q.h - 0.3, hi: G + q.h + 3.6, part: 'cab' });
    // landing + stair (aft of the cab bubble, beside the outer tunnel)
    for (const bx of this.stairBoxes(b, q)) out.push(bx);
    return out;
  }
  // where the rotunda corridor (2.4 m wide, to tunnel A's hinge at F) starts along the tunnel direction a: 0.8 of the
  // drum radius (it enters the drum) - or, where it would cross the bridge's own fixed walkway outside the drum, where it
  // leaves the walkway slab (+0.06 m), so that nothing is drawn through the walkway (close-out round 3 bridges-2: the
  // data's rest / docked poses of A12, F5, F14, F17, F19, F21 L1 fold the tunnel back to 41-45 deg from the walkway and the
  // corridor ran 0.2-0.65 m2 through it; the walkway and the drum close that junction instead). Exact (separating axes,
  // bisection to 1 mm); tunnel A and the parts beyond are still tested against the walkway (fixedHit)
  // (off / hw: a strip of the corridor, its centre `off` m to the right of the axis - neckParts)
  neckStart(b, a, off = 0, hw = 1.2) {
    const s0 = b.rotR * 0.8, Fm = b.m.F; const W = this.ownOut(b); if (!W.length || Fm - 0.3 <= s0) return s0;
    const u = [Math.cos(a), Math.sin(a)], r = [-u[1], u[0]];
    const hit = (s) => { const bx = { c: [b.rot[0] + u[0] * (s + Fm) / 2 + r[0] * off, b.rot[2] + u[1] * (s + Fm) / 2 + r[1] * off], u, hl: (Fm - s) / 2, hw }; return W.some(w => obbOverlap(bx, w, 0.06)); };
    if (!hit(s0)) return s0;
    let lo = s0, hi = Fm - 0.3; if (hit(hi)) return Fm; // (no start clears it: none of this strip is drawn)
    while (hi - lo > 0.001) { const mid = (lo + hi) / 2; if (hit(mid)) lo = mid; else hi = mid; }
    return hi;
  }
  // the rotunda corridor as tested (solidsQ 'neck' boxes): [{s0, s1, off, hw}] - the full width from neckStart to F, and
  // where that start moved out, the corridor between the drum and that start minus the walkway, as lateral bands of
  // <= 0.3 m (neckShape: from the drum to where the band meets the walkway and from where it leaves the walkway to the
  // full-width start, each 0.06 m clear of the walkway outside the drum, the neckStart criterion). Never empty (a pose in
  // which no part clears the walkway keeps the full corridor from 0.3 m before F: fixedHit then refuses it, except at a
  // data rest pose). Before close-out round 5 the walkway-side half was dropped from the drum to the full-width start, a
  // 0.8-1.3 m x 1.2 m open notch beside the drum at A12, F5, F14, F17, F19, F21 L1 (c3 verifier, neckgap.mjs)
  neckParts(b, a) {
    const K = this.neckShape(b, a), s = K.s, s0 = b.rotR * 0.8, Fm = b.m.F; const out = [];
    if (s < Fm - 0.01) out.push({ s0: s, s1: Fm, off: 0, hw: 1.2 });
    if (K.bands) for (const B of K.bands) out.push(B);
    if (!out.length) out.push({ s0: Math.max(s0, Fm - 0.3), s1: Fm, off: 0, hw: 1.2 });
    return out;
  }
  // the rotunda corridor's plan outline between the drum (0.8 rotR) and the full-width start s = neckStart (only where s
  // moved out): per lateral position l (right of the tunnel axis, every 0.05 m and at the walkway corners) the corridor
  // runs from the drum to near[i] (where it meets the drawn walkway) and from far[i] (where it leaves it) to s - so
  // that drum, walkway and corridor close the junction without the corridor entering the walkway (bridgeGeo draws these
  // outlines; neckParts tests bands inside them). The walkway is the drawn one (ownWalk, through to 0.8 rotR in the
  // drum; the first segment's tube from 0.3 m inside the building). {s, l, near, far} (near / far null: untrimmed),
  // cached per bridge and angle
  neckShape(b, a) {
    const Wk = this.ownWalk(b); if (b._nkOf !== Wk) { b._nkOf = Wk; b._nk = new Map(); }
    const key = Math.round(a * 1e6); let K = b._nk.get(key); if (K) return K;
    const s = this.neckStart(b, a), s0 = b.rotR * 0.8, Fm = b.m.F; K = { s, l: null, near: null, far: null };
    if (s > s0 + 0.05) {
      const u = [Math.cos(a), Math.sin(a)], r = [-u[1], u[0]], top = Math.min(s, Fm);
      const W = []; for (const S of Wk) { const A = S.first ? v3.add(S.A, v3.mul(S.d, -0.3)) : S.A, B = S.B; const d = [B[0] - A[0], B[2] - A[2]]; const L = Math.hypot(d[0], d[1]); if (L < 0.05) continue;
        W.push({ c: [(A[0] + B[0]) / 2, (A[2] + B[2]) / 2], u: [d[0] / L, d[1] / L], hl: L / 2, hw: WALK_W / 2 }); }
      // [entry, exit] distance along u of the ray at lateral l through plan box w, or null
      const span = (l, w) => { const px = b.rot[0] + r[0] * l - w.c[0], pz = b.rot[2] + r[1] * l - w.c[1]; let t0 = -1e9, t1 = 1e9;
        for (const [ax, h] of [[w.u, w.hl], [[-w.u[1], w.u[0]], w.hw]]) { const o = px * ax[0] + pz * ax[1], dd = u[0] * ax[0] + u[1] * ax[1];
          if (Math.abs(dd) < 1e-9) { if (Math.abs(o) > h) return null; continue; } let ta = (-h - o) / dd, tb = (h - o) / dd; if (ta > tb) [ta, tb] = [tb, ta]; t0 = Math.max(t0, ta); t1 = Math.min(t1, tb); }
        return t0 <= t1 + 1e-9 ? [t0, t1] : null; };
      const ls = new Set(); for (let i = 0; i <= 48; i++) ls.add(Math.round((-1.2 + i * 0.05) * 1e4) / 1e4);
      for (const w of W) for (const [i, j] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) { const l = (w.c[0] + w.u[0] * w.hl * i - w.u[1] * w.hw * j - b.rot[0]) * r[0] + (w.c[1] + w.u[1] * w.hl * i + w.u[0] * w.hw * j - b.rot[2]) * r[1]; for (const e of [-1e-4, 0, 1e-4]) if (l + e > -1.2 && l + e < 1.2) ls.add(l + e); } // (and either side of each corner: the outline jumps there)
      K.l = [...ls].sort((x, y) => x - y); K.near = []; K.far = [];
      for (const l of K.l) { let n = top, f = s0;
        for (const w of W) { const sp = span(l, w); if (!sp || sp[1] <= s0 || sp[0] >= top) continue; n = Math.min(n, Math.max(s0, sp[0])); f = Math.max(f, Math.min(top, sp[1])); }
        K.near.push(n); K.far.push(f > s0 ? f : top); }
      // the tested boxes: per lateral band of 0.3 m, the longest box from the drum and the longest one to the full-width
      // start inside that outline that clear the walkway outside the drum (ownOut) by 0.06 m (bisection to 1 mm);
      // adjacent bands of the same reach merged
      const O = this.ownOut(b); const clear = (s1, s2, la, lb) => { const sc = (s1 + s2) / 2, lc = (la + lb) / 2; const bx = { c: [b.rot[0] + u[0] * sc + r[0] * lc, b.rot[2] + u[1] * sc + r[1] * lc], u, hl: (s2 - s1) / 2, hw: (lb - la) / 2 }; return !O.some(w => obbOverlap(bx, w, 0.06)); };
      const raw = [];
      for (let la = -1.2; la < 1.19; la += 0.3) { const lb = la + 0.3; let n = top, f = top;
        K.l.forEach((l, i) => { if (l >= la - 1e-6 && l <= lb + 1e-6) { n = Math.min(n, K.near[i]); f = Math.min(f, K.far[i]); } });
        let hiN = n; if (hiN - s0 > 0.05 && !clear(s0, hiN, la, lb)) { let lo = s0; while (hiN - lo > 0.001) { const m = (lo + hiN) / 2; if (clear(s0, m, la, lb)) lo = m; else hiN = m; } hiN = lo; }
        let loF = Math.max(...K.l.map((l, i) => l >= la - 1e-6 && l <= lb + 1e-6 && K.far[i] < top ? K.far[i] : s0));
        if (loF <= s0) loF = top; // (no walkway in this band: the near box covers it)
        if (top - loF > 0.05 && !clear(loF, top, la, lb)) { let hi = top; while (hi - loF > 0.001) { const m = (loF + hi) / 2; if (clear(m, top, la, lb)) hi = m; else loF = m; } loF = hi; }
        raw.push([la, lb, hiN, loF]); }
      K.bands = [];
      for (const lo of [true, false]) { let cur = null;
        const push = () => { if (cur) K.bands.push({ s0: cur.a0, s1: cur.a1, off: (cur.la + cur.lb) / 2, hw: (cur.lb - cur.la) / 2 }); cur = null; };
        for (const [la, lb, n, f] of raw) { const a0 = lo ? s0 : f, a1 = lo ? n : top; if (a1 - a0 <= 0.05) { push(); continue; }
          if (cur && Math.abs(cur.a0 - a0) < 0.03 && Math.abs(cur.a1 - a1) < 0.03) { cur.lb = lb; cur.a0 = Math.max(cur.a0, a0); cur.a1 = Math.min(cur.a1, a1); continue; }
          push(); cur = { la, lb, a0, a1 }; }
        push(); }
    }
    if (b._nk.size > 4096) b._nk.clear(); b._nk.set(key, K); return K;
  }
  // the bridge's own fixed-walkway slabs outside its drum (plan boxes; cached with ownWalk)
  ownOut(b) {
    const W = this.ownWalk(b); if (b._ownOutOf === W) return b._ownOut; const out = [];
    for (const S of W) { const d = [S.B[0] - S.A[0], S.B[2] - S.A[2]]; const L = Math.hypot(d[0], d[1]); if (L < 0.05) continue;
      const c = this.outsideDrum(b, { c: [(S.A[0] + S.B[0]) / 2, (S.A[2] + S.B[2]) / 2], u: [d[0] / L, d[1] / L], hl: L / 2, hw: WALK_W / 2 }, b.rotR); if (c) out.push(c); }
    b._ownOutOf = W; return (b._ownOut = out);
  }
  // floor height above the apron at distance s from the rotunda centre: level through the rotunda and its corridor
  // (to tunnel A's hinge at F), then a straight slope to the cab floor at the pivot
  floorAt(b, q, s) { const F = b.m.F; return b.Hr + (q.h - b.Hr) * clampN((s - F) / Math.max(q.e - F, 0.1), 0, 1); }
  slopeOf(b, e, h) { return Math.abs(b.Hr - h) / Math.max(1, e - b.m.F); }
  // the fixed-walkway segments this bridge draws (world, floor heights): from the building (or, where its polyline
  // shares its first vertices with a sibling bridge's - one walkway branching - from where it leaves the sibling's
  // walkway / rotunda) to the edge of its own drum
  ownWalk(b) {
    if (b._own) return b._own; const out = []; const W = b.walk; const i0 = b.walkFrom || 0;
    for (let i = i0 + 1; i < W.length; i++) {
      let A = [W[i - 1][0], G + this.walkY(b, i - 1), W[i - 1][2]]; let B = [W[i][0], G + this.walkY(b, i), W[i][2]];
      const L = Math.hypot(B[0] - A[0], B[2] - A[2]); if (L < 0.05) continue; const d = [(B[0] - A[0]) / L, 0, (B[2] - A[2]) / L];
      let a0 = i === i0 + 1 ? (b.walkOff || 0) : 0, a1 = L - (i === W.length - 1 ? Math.min(b.rotR * 0.8, 0.9 * L) : 0);
      if (a1 - a0 < 0.1) { if (out.length || i < W.length - 1) continue; a0 = Math.max(0, a1 - 0.1); } // (nothing own left: a 0.1 m stub inside the own drum)
      const P = (t) => [A[0] + d[0] * t, A[1] + (B[1] - A[1]) * t / L, A[2] + d[2] * t];
      const ad = i === i0 + 1 && b.walkDrawOff != null ? Math.min(a0, b.walkDrawOff) : a0;
      out.push({ A: P(a0), B: P(a1), drawA: P(ad), d, i, first: i === 1 && !a0, last: i === W.length - 1 });
    }
    return (b._own = out);
  }
  // shared walkway prefixes between the bridges of one stand, twin rotundas (one junction for two tunnels)
  shareWalks(g) {
    const Bs = (g.bridges || []);
    for (let j = 1; j < Bs.length; j++) for (let k = 0; k < j; k++) {
      const b = Bs[j], o = Bs[k]; let n = 0; while (n < b.walk.length && n < o.walk.length && Math.hypot(b.walk[n][0] - o.walk[n][0], b.walk[n][2] - o.walk[n][2]) < 0.3) n++;
      // (o's rotunda as a vertex of b's walkway: a twin head)
      let twin = false; if (n === o.walk.length && n < b.walk.length) twin = true;
      if (n < 2 || (b.walkFrom || 0) >= n - 1) continue;
      b.walkFrom = n - 1; const V = b.walk[n - 1], N = b.walk[n];
      const du = [N[0] - V[0], N[2] - V[2]]; const Lu = Math.hypot(du[0], du[1]) || 1;
      // twin head: the connector from o's drum to b's runs level between the two drums (finishPrep puts both on one
      // floor); it is drawn from where its corners meet o's drum (a closed junction), its solid starts at o's drum
      if (twin) { const D = Math.hypot(b.rot[0] - o.rot[0], b.rot[2] - o.rot[2]); const r = Math.max(DRUM_MIN, Math.min(b.rotR, o.rotR, (D - 0.3) / 2)); b.rotR = o.rotR = r; b.walkOff = r + 0.005; b.walkDrawOff = Math.sqrt(Math.max(0, r * r - WALK_W * WALK_W / 4)); b.twinOf = o; }
      else { // start clear of the sibling's walkway (its segment through V, both sides)
        // (each sibling segment at V as a ray from V: the start face's corners must be half a width off its axis)
        let off = WALK_W / 2 + 0.5; for (const [P0, P1] of [[o.walk[n - 1], o.walk[n - 2]], [o.walk[n - 1], o.walk[n]]]) { if (!P0 || !P1) continue; const dv = [P1[0] - P0[0], P1[2] - P0[2]]; const Lv = Math.hypot(dv[0], dv[1]) || 1;
          const c = (du[0] * dv[0] + du[1] * dv[1]) / (Lu * Lv); if (c <= 0) continue; const sn = Math.sqrt(Math.max(0.01, 1 - c * c)); off = Math.max(off, Math.min(Lv, (WALK_W / 2) * (1 + c) / sn + 0.5)); }
        b.walkOff = off; }
      b._own = null; o._own = null;
    }
  }
  walkY(b, i) { // floor height (above the apron) at walkway vertex i: departure level at the building, rotunda floor at the end
    if (b.twinOf && i >= (b.walkFrom || 0)) return b.Hr; // twin connector: level between the two drums (one floor)
    let L = 0; for (let j = 1; j <= i; j++) L += Math.hypot(b.walk[j][0] - b.walk[j - 1][0], b.walk[j][2] - b.walk[j - 1][2]);
    return b.Hb + (b.Hr - b.Hb) * (b.walkLen > 0 ? L / b.walkLen : 1);
  }
  // telescoping sections [s0, s1, width, height] along the tunnel for pivot distance e: A fixed to the rotunda corridor,
  // the outer section fixed to the cab, B centred between them (equal overlaps); lengths never change
  sections(b, e) {
    const { n, s, F, wh } = b.m; e = Math.max(e, F + s + (n - 1) * STAGGER);
    if (n === 2) return [[F, F + s, ...wh[0]], [e - s, e, ...wh[1]]];
    const b0 = (F + e - s) / 2; return [[F, F + s, ...wh[0]], [b0, b0 + s, ...wh[1]], [e - s, e, ...wh[2]]];
  }
  driveAt(b, e) { return e - clampN(0.35 * b.m.s, 2.5, 6.0); } // drive column on the outer tunnel (inferred position)
  stairBoxes(b, q) {
    const u = dirOf(q.a); const rt = [-u[2], 0, u[0]]; const sd = b.stairSide || 1; const rot = b.rot;
    const fl = (s) => this.floorAt(b, q, s);
    const sL = q.e - 3.3; const lat = sd * 2.15; const hL = fl(sL);
    const P = (s, l) => [rot[0] + u[0] * s + rt[0] * l, rot[2] + u[2] * s + rt[2] * l];
    const out = [{ c: P(sL, lat), u: [u[0], u[2]], hl: 0.65, hw: 0.55, lo: G + hL - 0.3, hi: G + hL + 1.1, part: 'stair' }];
    const run = Math.max(0.5, (hL - 0.1) / Math.tan(40 * DEG));
    out.push({ c: P(sL - 0.65 - run / 2, lat), u: [u[0], u[2]], hl: run / 2, hw: 0.55, lo: G, hi: G + hL + 1.0, part: 'stair' });
    return out;
  }
  // ------------------------------------------------------------ geometry
  bridgeGeo(g, b, k, geo, sgn) {
    const P = this.pose(g, b, k); const q = P.q; const m = b.m; const rot = b.rot; const u = P.dir;
    const side = v3.norm(v3.cross(u, [0, 1, 0])); // right of the tunnel direction
    const at = (s, y) => [rot[0] + u[0] * s, y, rot[2] + u[2] * s];
    const fl = (s) => G + this.floorAt(b, q, s);
    // fixed walkway along the mapped polyline, sloping from the terminal level to the rotunda floor; first segment as a
    // tube (it enters the building at the attach point), the others as slabs; columns every ~14 m outside the building:
    // not in, or within 0.6 m of, a terminal outline or a sky bridge - where an SFO Museum ring is the walkway's own roof
    // trace (ownStrip: the Boarding Area B tip strips, which the 3-D domestic asset leaves to the bridges) the columns
    // stay (review round 2: the Museum strips had dropped 27 of the 72 columns, B26 / B27 L1 spans of 42-53 m)
    const segs = this.ownWalk(b);
    segs.forEach((S, n) => { if (n === 0) tube(geo, S.first ? v3.add(S.A, v3.mul(S.d, -0.3)) : S.drawA, S.B, WALK_W, WALK_H, C.walk, C.panelE); else slab(geo, S.A, S.B, WALK_W, WALK_H, C.walk, C.panelE); });
    let run = 0;
    for (const S of segs) {
      const L = Math.hypot(S.B[0] - S.A[0], S.B[2] - S.A[2]);
      for (let d = 7 - (run % 14); d < L; d += 14) { const t = d / L; const p = v3.lerp(S.A, S.B, t); if (d < 1.5 || L - d < b.rotR + 1.5 && S.last || !this.columnOk(b, p)) continue; cyl(geo, [p[0], G, p[2]], 0.35, p[1] - G - 0.3, C.steel, C.steelE, 10); }
      run += L;
    }
    // rotunda on its pedestal (drum radius limited by the neighbouring rotundas, data rotundaMaxR)
    cyl(geo, [rot[0], G, rot[2]], 0.6, b.Hr - 0.3, C.steel, C.steelE, 12);
    cyl(geo, [rot[0], G + b.Hr - 0.3, rot[2]], b.rotR, 3.6, C.panel, [0.45, 0.25, 0, 0], 24);
    // rotunda corridor (turns with the tunnel) from the drum - or from where it leaves the bridge's own fixed walkway
    // (neckStart) - to tunnel A
    // (where that start moved out: the outline between the drum and the walkway, neckShape - drawn as prisms, the tested
    // boxes lie inside them)
    { const K = this.neckShape(b, q.a), Fm = m.F;
      // (full width: neckSlab - vertical start face at s; its roof runs on under tunnel A, whose axis is the sections' floor line)
      const tunA = { o: at(Fm, fl(Fm)), f: v3.sub(at(Fm + m.s, fl(Fm + m.s)), at(Fm, fl(Fm))), h: m.wh[0][1] };
      let toA = false; // (a full-width part runs into tunnel A)
      for (const N of this.neckParts(b, q.a)) if (N.hw > 1) { const e1 = N.s1 + 0.2, A = N.s1 >= Fm - 1e-6; toA = toA || A; neckSlab(geo, at(N.s0, fl(N.s0) - 0.1), at(e1, fl(e1) - 0.1), A ? tunA : null, 2.4, 2.9, C.neck, C.panelE); }
      // (none - every full-width start meets the walkway, F5 L1 at rest: the prisms run to F, where tunnel A's frame leans
      // forward over a downward slope; a 0.2 m full-width piece inside tunnel A carries their roof under it)
      if (K.near && !toA) { const s1 = Math.min(K.s, Fm), e1 = Fm + 0.2; neckSlab(geo, at(s1, fl(s1) - 0.1), at(e1, fl(e1) - 0.1), tunA, 2.4, 2.9, C.neck, C.panelE); }
      if (K.near) { const y0 = G + b.Hr - 0.1, s0 = b.rotR * 0.8, top = Math.min(K.s, Fm); const P = (s, l) => [rot[0] + u[0] * s + side[0] * l, rot[2] + u[2] * s + side[2] * l];
        const prism = (pts) => { if (pts.length < 3) return; let A2 = 0; for (let i = 0; i < pts.length; i++) { const p = pts[i], n = pts[(i + 1) % pts.length]; A2 += p[0] * n[1] - n[0] * p[1]; } if (Math.abs(A2) < 2e-3) return;
          if (A2 < 0) pts.reverse(); geo.extrude(pts, y0, y0 + 2.9, C.neck, C.panelE, C.neck, C.panelE); geo.cap(pts, y0, C.neck, C.panelE, false); };
        // runs of lateral samples with something to draw: near (drum -> walkway) and far (walkway -> full-width start)
        for (const [lo, arr] of [[true, K.near], [false, K.far]]) { let run = [];
          const flush = () => { if (run.length > 1) { const pts = lo ? [P(s0, run[0][0]), ...run.map(([l, v]) => P(v, l)), P(s0, run[run.length - 1][0])] : [P(top, run[0][0]), ...run.map(([l, v]) => P(v, l)), P(top, run[run.length - 1][0])]; prism(pts); } run = []; };
          K.l.forEach((l, i) => { const v = arr[i]; if (lo ? v - s0 > 0.005 : top - v > 0.005) run.push([l, v]); else flush(); }); flush(); } } }
    // telescoping tunnel sections (fixed lengths, nested: largest nearest the aircraft), floors on the rotunda -> cab line
    const secs = this.sections(b, q.e); let last = null;
    secs.forEach(([s0, s1, w, h], i) => { const dy = (h - secs[0][3]) / 2; last = tube(geo, at(s0, fl(s0) - dy), at(s1, fl(s1) - dy), w, h, C.panel, C.panelE); });
    // drive column on the outer tunnel: two legs, cross beam, bogie with two wheels, control box
    const dcs = this.driveAt(b, q.e); const du = at(dcs, fl(dcs) - 0.15); const hdir = [u[0], 0, u[2]];
    for (const sg of [-1, 1]) {
      const leg = v3.add(du, v3.mul(side, sg * 1.25));
      geo.box([-0.16, 0, -0.16], [0.16, Math.max(0.2, du[1] - G - 0.95), 0.16], C.steel, C.steelE, m4.basis(hdir, [0, 1, 0], [leg[0], G + 0.95, leg[2]]));
      geo.cylinder(0.48, 0.34, 14, C.tyre, C.tyreE, m4.mul(m4.basis(hdir, [0, 1, 0], [leg[0], G + 0.48, leg[2]]), m4.mul(m4.rotX(Math.PI / 2), m4.translate(0, -0.17, 0))), true);
    }
    geo.box([-0.35, 0.72, -1.55], [0.35, 1.1, 1.55], C.steel, C.steelE, m4.basis(hdir, [0, 1, 0], [du[0], G, du[2]]));
    geo.box([-0.35, -0.9, 1.5], [0.35, 0, 1.9], C.yellow, C.yellowE, m4.basis(hdir, [0, 1, 0], du));
    // pre-conditioned-air unit slung under the outer tunnel, ahead of the column (towards the rotunda), with its hose basket
    const ps = Math.max(secs[secs.length - 1][0] + 0.7, dcs - 1.8); const pu = at(ps, fl(ps) - 0.15);
    const clear = pu[1] - G;
    if (clear > 1.8) { geo.box([-0.6, -1.5, -1.2], [0.6, -0.15, 1.2], C.unit, C.unitE, m4.basis(hdir, [0, 1, 0], pu)); if (clear > 2.3) geo.box([-0.45, -2.0, -0.5], [0.45, -1.5, 0.5], C.yellow, C.yellowE, m4.basis(hdir, [0, 1, 0], pu)); }
    // cab bubble at the pivot (on the outer tunnel), rotating cab + bellows closure
    const piv = P.cab; const fc = P.facing;
    geo.cylinder(1.55, 3.05, 18, C.panel, C.panelE, m4.translate(piv[0], piv[1] - 0.1, piv[2]), true);
    const cabM = m4.basis(fc, [0, 1, 0], piv); const fr = m.spacer - 0.45;
    geo.box([-CAB_BACK, -0.1, -CAB_W / 2], [fr, 3.2, CAB_W / 2], C.cab, C.cabE, cabM);
    geo.box([-CAB_BACK - 0.1, 3.2, -CAB_W / 2 - 0.15], [fr + 0.15, 3.4, CAB_W / 2 + 0.15], C.steel, C.steelE, cabM);
    const bell = 0.45 + 0.15 * P.kk;
    // closure: fitted to the drawn fuselage skin while it deploys (js/aircraft/dock.js; aircraft track), else flat
    const shp = P.kk > 0 && P.plan && P.plan.ok ? bellowsShape(P.T, b.upper ? 3 : (b.door || 1), P.kk) : null;
    if (shp) bellowsGeo(geo, cabM, fr, bell, shp, C.dark, C.darkE);
    else for (let i = 0; i < 5; i++) geo.box([fr + i * bell / 5, 0.05, -1.55 - (i % 2) * 0.05], [fr + (i + 1) * bell / 5, 3.0, 1.55 + (i % 2) * 0.05], C.dark, C.darkE, cabM);
    // floodlight on the cab roof, amber beacon
    geo.box([fr - 0.6, 3.4, -0.35], [fr - 0.2, 3.65, 0.35], C.dark, C.darkE, cabM);
    geo.box([fr - 0.22, 3.42, -0.3], [fr - 0.19, 3.62, 0.3], C.lamp, C.lampE, cabM);
    geo.cylinder(0.14, 0.25, 10, C.amber, C.amberE, m4.mul(cabM, m4.translate(-1.2, 3.4, 1.4)), true);
    this.sprites.push({ p: m4.xform(cabM, [-1.2, 3.8, 1.4]), c: [1, 0.55, 0.08], i: 70, s: 0.25, beacon: true, moving: k > 0.001 && k < 0.999 });
    this.sprites.push({ p: m4.xform(cabM, [fr - 0.18, 3.52, 0]), c: [1, 0.92, 0.8], i: 500, s: 0.35, dir: v3.norm(m4.xdir(cabM, [1, -0.8, 0])), k: 3, night: true });
    // service landing + stair beside the outer tunnel aft of the cab bubble (sheet option C / D)
    const sd = b.stairSide || 1; const sL = q.e - 3.3; const hL = fl(sL);
    const lp = v3.add(at(sL, hL), v3.mul(side, sd * 2.15));
    geo.box([-0.65, -0.14, -0.55], [0.65, 0, 0.55], C.steel, C.steelE, m4.basis(hdir, [0, 1, 0], lp));
    for (const zz of [-0.5, 0.5]) geo.box([-0.65, 0.86, zz - 0.025], [0.65, 0.92, zz + 0.025], C.yellow, C.yellowE, m4.basis(hdir, [0, 1, 0], lp));
    const stTop = v3.add(lp, v3.mul(hdir, -0.65)); const hgt = stTop[1] - G - 0.05;
    if (hgt > 0.6) {
      const rn = hgt / Math.tan(40 * DEG); const stBot = v3.add(stTop, v3.mul(hdir, -rn)); stBot[1] = G;
      const sDir = v3.norm(v3.sub(stBot, stTop)); const lat = v3.norm(v3.cross(sDir, [0, 1, 0])); const up = v3.cross(lat, sDir);
      const sM = m4.basis(sDir, up, stTop); const sl = v3.dist(stTop, stBot);
      for (const zz of [-0.5, 0.5]) geo.box([0, -0.28, zz - 0.05], [sl, 0.0, zz + 0.05], C.steel, C.steelE, sM);
      geo.box([0, -0.14, -0.5], [sl, -0.06, 0.5], C.steel, C.steelE, sM);
      for (const zz of [-0.5, 0.5]) geo.box([0, 0.86, zz - 0.025], [sl, 0.92, zz + 0.025], C.yellow, C.yellowE, sM);
    }
    // gate number signs on both sides of the outer tunnel section (lit panels from the sign atlas)
    if (last && sgn) {
      const r = this.atlas.map['gate:' + b.gate];
      if (r) {
        const Lh = 0.85, Lw = Lh * r.aspect; const os = secs[secs.length - 1]; const ms = (os[0] + os[1]) / 2 - 0.5; const hw = os[2] / 2 + 0.04;
        for (const sg of [-1, 1]) {
          const n = v3.mul(side, sg); const c = v3.add(v3.add(at(ms, fl(ms)), v3.mul(n, hw)), [0, os[3] - 0.75, 0]);
          // text runs left-to-right for a viewer on the n side looking at the sign (viewer's right = cross(-n, up) = sg *
          // hdir; close-out round 3 bridges-8: -sg * hdir read mirrored on BOTH sides - review B13 / D10; scratch signs.mjs)
          const along = v3.mul(hdir, sg);
          const u0 = v3.add(c, v3.mul(along, -Lw / 2)), u1 = v3.add(c, v3.mul(along, Lw / 2));
          signQuad(sgn, [v3.add(u0, [0, -Lh / 2, 0]), v3.add(u1, [0, -Lh / 2, 0]), v3.add(u1, [0, Lh / 2, 0]), v3.add(u0, [0, Lh / 2, 0])], n, r, true);
        }
      }
    }
    return P;
  }
  // ------------------------------------------------------------ stand sign + VDGS
  // (every VDGS position is inferred - no survey of SFO's units; F5's is a post: its facade spot lies in the Museum / asset
// bump around F5 L1's walkway start, no source for its real mounting)
// on the stand centreline ahead of the nose: on the terminal face when the stop point is close to it, else on its own
  // post; the first spot (facade first, then posts 12, 11, 13, 10, ... m ahead of the nose) that no bridge part of this
  // or a neighbouring stand reaches in any pose (rest, docking paths, docked for every type it docks) with 0.5 m clearance
  vdgsSpot(g) {
    if (g._vdgs) return g._vdgs;
    const nose = stW(g.nose, G), f = stD(g.dir);
    // the terminal face on the stand centreline: the outline js/live/terminals.js draws (td; none within 60 m - A13, G10,
    // G13: posts only; review 2026-11-04 found their facade units floating 7-11 m up with no wall within 22-30 m) and,
    // where the SFO Museum ring the 3-D building assets are built from lies in front of it (by at most the OSM lean,
    // 2.1 m), that one (tf: the outer face). A facade unit is mounted 0.25 m clear of the outer face - the assets' walls
    // lie 0-0.2 m in front of the Museum ring at these stands (data/buildings3d/integration.json footprints) - on a
    // bracket reaching back 0.1 m into the drawn wall (inside the 3-D asset's wall when that is drawn). Review round 2
    // v7: mounted in front of the drawn wall only, the units at A10, E3, E7, F5, F12, F14, G2, G3, G7, G9 lay inside the
    // Museum ring (0.2-0.8 m in front of the drawn wall) and became posts 2.4-3 m nearer the aircraft
    const P = (t) => v3.add(nose, v3.mul(f, t)); const W0 = [-f[2], f[0]];
    const first = (test, t0, t1) => { let t = null; for (let x = t0; x <= t1 + 1e-9; x += 0.5) if (test(x)) { t = x; break; } if (t == null || t === t0) return t;
      let lo = t - 0.5, hi = t; for (let k = 0; k < 12; k++) { const m = (lo + hi) / 2; if (test(m)) hi = m; else lo = m; } return hi; };
    const td = first(t => { const p = P(t); return inBuilding(p[0], p[2], false, true); }, 1, 60);
    let tf = td;
    if (td != null) { const t0 = Math.max(1, td - STRIP_LEAN); const inC = (t) => { const p = P(t); return inBuilding(p[0], p[2]); }; const tm = first(inC, t0, td);
      // (only a face continuous with the drawn wall: no gap between them - not a walkway strip crossing the centreline)
      if (tm != null && tm > t0 && tm < td) { let ok = true; for (let t = tm + 0.05; t < td; t += 0.1) if (!inC(t)) { ok = false; break; } if (ok) tf = tm; } }
    // (the 3-D asset's wall behind a facade unit: where it lies behind the drawn wall - B2 0.94 / 1.34 m, C8 0.44 / 0.40 m
    // behind the unit's back - the bracket reaches it too, close-out round 3 bridges-5; ASSET: B3D_INTEGRATION physics
    // footprints, the arms at +-0.475 m: the first point inside a footprint up to 3 m behind the unit, else none)
    const assetFace = (t) => { let a = -1e9; for (const w of [-0.475, 0.475]) for (let x = t; x <= t + 3; x += 0.02) { const p = P(x); if (inAsset(p[0] + W0[0] * w, p[2] + W0[1] * w)) { a = Math.max(a, x); break; } } return a; };
    const tmax = td == null ? 40 : 1 + Math.ceil((td - 1) / 0.5 - 1e-9) * 0.5 - 2.75; // (posts ~2.5 m off the drawn wall: as before, on its 0.5 m search grid)
    // a facade unit only where the drawn wall behind it (0.6-3 m) reaches above the unit (H0 + 4.2 m): the piers / halls,
    // not the 5 m ramp-level complex
    // (0.25 m off the outer face on the centreline, else up to 1 m where the face is oblique or stepped under the unit's
    // 2.6 m width; the bracket reaches back to the drawn wall)
    const tries = []; const fac = (H0) => { if (tf == null || ![0.6, 1.5, 3.0].every(d => { const p = P(td + d); return wallTop(p[0], p[2]) >= H0 + 4.2; })) return;
      for (const off of [0.25, 0.5, 0.75, 1.0]) { const t = Math.max(1, tf - off); tries.push({ t, post: false, H0, bracket: Math.max(0, td + 0.1 - t, assetFace(t) + 0.15 - t) }); } }; // (+0.15: the shipped rings are rounded to 0.1 m)
    if (tf != null && tf <= 14) fac(7.2);
    for (const d of [0, -1, 1, -2, 2, -3, 3, -4, 4, -5, -6, -7, -8]) { const t = 12 + d; if (t >= 3.5 && t <= tmax) tries.push({ t, post: true, H0: 5.2 }); }
    for (let t = 17; t <= Math.min(40, tmax); t++) tries.push({ t, post: true, H0: 5.2 });
    if (tf != null && tf > 14 && tf <= 45) fac(7.2);
    if (tf != null && tf <= 45) fac(9.6); // high on the facade, above the tunnels that pass in front
    if (!tries.length) for (let t = 3.5; t <= 12; t += 0.5) tries.push({ t, post: true, H0: 5.2 }); // (a post close to the nose)
    const W = [-f[2], f[0]];
    let pick = null;
    for (const exact of [false, true]) { if (pick) break; const sweep = this.sweptSolids(g, exact, tries.map(c => { const p = v3.add(nose, v3.mul(f, c.t)); return [p[0], p[2]]; }));
    for (const c of tries) {
      const p = v3.add(nose, v3.mul(f, c.t)); const H0 = c.H0;
      const boxes = c.post ? [{ c: [p[0], p[2]], u: [f[0], f[2]], hl: 0.5, hw: 0.5, lo: G, hi: G + H0 + 4.6 }, { c: [p[0] - f[0] * 0.35, p[2] - f[2] * 0.35], u: [f[0], f[2]], hl: 0.35, hw: 1.3, lo: G + H0 - 0.4, hi: G + H0 + 4.6 }]
        : [{ c: [p[0] - f[0] * 0.35, p[2] - f[2] * 0.35], u: [f[0], f[2]], hl: 0.35, hw: 1.3, lo: G + H0 - 0.4, hi: G + H0 + 4.2 }];
      let hit = boxes.some(a => solidInBuilding(a)) ? 'building' : null;
      if (!hit) for (const a of boxes) { for (const s of sweep) if (s.hi > a.lo - 0.5 && s.lo < a.hi + 0.5 && solidOverlap(a, s, 0.5)) { hit = 'bridge ' + s.part; break; } if (hit) break; }
      if (this.vdgsWhy) this.vdgsWhy.push([g.name, c.post ? 'post' : 'facade', +c.t.toFixed(2), c.H0, hit]); // (checkers' diagnostics)
      if (!hit) { pick = c; break; }
    } }
    if (!pick) { pick = tries[0]; this.vdgsBlocked = (this.vdgsBlocked || 0) + 1; (this.vdgsBlockedAt || (this.vdgsBlockedAt = [])).push(g.name); }
    return (g._vdgs = { t: pick.t, post: pick.post, H0: pick.H0, W, bracket: pick.post ? 0 : (pick.bracket || 0) });
  }
  // every solid of the bridges within 90 m of the stand, at rest, along the docking paths and docked, for every type
  // each of them docks at its stand (sampled)
  sweptSolids(g, exact = false, near = null) {
    const nose = stW(g.nose, G); const out = [];
    const segD = (p, A, B) => { const ex = B[0] - A[0], ez = B[1] - A[1]; const t = clampN(((p[0] - A[0]) * ex + (p[1] - A[1]) * ez) / (ex * ex + ez * ez || 1), 0, 1); return Math.hypot(A[0] + ex * t - p[0], A[1] + ez * t - p[1]); };
    for (const o of this.gates) {
      if (!o.bridge) continue; const on = stW(o.nose, G); if (Math.hypot(on[0] - nose[0], on[2] - nose[2]) > 140) continue;
      for (const b of this.bridgesOf(o)) {
        if (!b.m) this.prepBridge(o, b);
        if (Math.hypot(b.rot[0] - nose[0], b.rot[2] - nose[2]) > 90) continue;
        for (const s of (b._restS || (b._restS = this.solidsQ(b, { a: b.a0, e: b.e0, t: 0, h: b.h0 }, 0, true)))) out.push(s);
        for (const q of this.sweepQ(o, b, exact)) {
          if (near) { const A = [b.rot[0], b.rot[2]], B = [b.rot[0] + Math.cos(q.a) * q.e, b.rot[2] + Math.sin(q.a) * q.e]; if (!near.some(p => segD(p, A, B) < 9)) continue; }
          for (const s of this.solidsQ(b, q, 0)) out.push(s);
        }
      }
    }
    return out;
  }
  // joint states along every docking path of a bridge (deduplicated to 1 deg / 0.5 m / 5 deg cab / 0.5 m height)
  sweepQ(o, b, exact) {
    const key = exact ? '_sqX' : '_sq'; if (b[key]) return b[key]; const seen = new Set(), out = [];
    for (const P of this.staticPlans(o, b, exact)) for (let i = 1; i < P.path.length; i++) for (let k = 0; k <= 5; k++) {
      const q = this.qLerp(b, P.path[i - 1], P.path[i], k / 5); const id = Math.round(q.a / DEG) + ',' + Math.round(q.e * 2) + ',' + Math.round(q.t / DEG / 5) + ',' + Math.round(q.h * 2);
      if (!seen.has(id)) { seen.add(id); out.push(q); }
    }
    return (b[key] = out);
  }
  // docking plans of a bridge for the accepted types of its stand (and alternative positions) at their stop points
  // (exact = false: every candidate path unchecked, a superset - cheap; exact: the checked path each docking really takes)
  staticPlans(g, b, exact = false) {
    const key = exact ? '_staticX' : '_static'; if (b[key]) return b[key]; const out = [];
    for (const { s } of this.standPoses(g)) for (const A of this.acceptedTypes(s)) {
      const fam = familyOf(A.icao); const st = fam && s.typeStops && s.typeStops[fam]; const along = st && Number.isFinite(st.along) ? Math.min(0, st.along) : 0;
      const f = stD(s.dir); const nose = v3.add(stW(s.nose, G), v3.mul(f, along));
      const gp = { ...g, acType: A.key, _lastType: A.key, dockType: A.icao, dock: { nose: worldToST(nose[0], nose[2]), dir: s.dir } };
      const P = this.makePlan(gp, b, exact ? {} : { all: true }); if (P.ok) { if (exact) out.push(P); else for (const path of P.alts) out.push({ ...P, path }); }
    }
    return (b[key] = out);
  }
  standGeo(g, geo, sgn) {
    const nose = stW(g.nose, G), f = stD(g.dir);
    const V = this.vdgsSpot(g); const post = V.post, t = V.t;
    const c = v3.add(nose, v3.mul(f, t));
    const outW = v3.mul(f, -1); // display faces the arriving aircraft
    const face = v3.add(c, v3.mul(outW, 0.35));
    const tW = v3.norm(v3.cross(outW, [0, 1, 0]));
    const H0 = V.H0 || (post ? 5.2 : 7.2);
    if (post) { geo.box([-0.18, 0, -0.18], [0.18, H0, 0.18], C.steel, C.steelE, m4.basis(tW, [0, 1, 0], [c[0], G, c[2]])); geo.box([-0.5, 0, -0.5], [0.5, 0.25, 0.5], [0.55, 0.55, 0.55, 1], [0.5, 0.3, 0, 0], m4.basis(tW, [0, 1, 0], [c[0], G, c[2]])); }
    const M = m4.basis(v3.mul(tW, -1), [0, 1, 0], [face[0], G + H0, face[2]]);
    geo.box([-0.75, 0, -0.35], [0.75, 2.4, 0.25], [0.2, 0.21, 0.22, 1], [0.5, 0.4, 0, 0], M);
    // wall bracket of a facade unit: four arms from its back into the drawn wall (vdgsSpot; inside a 3-D asset's wall)
    if (!post && V.bracket > 0.02) for (const x of [-0.55, 0.4]) for (const y of [0.25, 2.0]) geo.box([x, y, -0.35 - V.bracket], [x + 0.15, y + 0.15, -0.35], C.steel, C.steelE, M);
    geo.box([-0.8, -0.35, -0.3], [0.8, 0, 0.2], C.yellow, C.yellowE, M);
    const gname = g.gate || g.name;
    const vr = (g.acType && g.dockType && this.atlas.map['vdgs:' + g.dockType]) || this.atlas.map['vdgs:' + gname] || this.atlas.map['vdgs:' + g.name];
    const dh = 0.8, dw = Math.min(1.35, dh * vr.aspect);
    const d0 = v3.add([face[0], G + H0 + 1.35, face[2]], v3.mul(outW, 0.27));
    signQuad(sgn, [v3.add(d0, v3.add(v3.mul(tW, dw / 2), [0, -dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, -dw / 2), [0, -dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, -dw / 2), [0, dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, dw / 2), [0, dh / 2, 0]))], outW, vr, true);
    // stand number (the gate number as signed: B5 for the alternative position B5S) above the display
    const gr = this.atlas.map['gate:' + gname] || this.atlas.map['gate:' + g.name]; const gh = 1.4, gw = gh * gr.aspect;
    const g0 = v3.add([face[0], G + H0 + 3.1, face[2]], v3.mul(outW, 0.1));
    if (post) geo.box([-gw / 2 - 0.1, -gh / 2 - 0.1, -0.12], [gw / 2 + 0.1, gh / 2 + 0.1, 0.02], [0.2, 0.21, 0.22, 1], [0.5, 0.4, 0, 0], m4.basis(v3.mul(tW, -1), [0, 1, 0], g0));
    signQuad(sgn, [v3.add(g0, v3.add(v3.mul(tW, gw / 2), [0, -gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, -gw / 2), [0, -gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, -gw / 2), [0, gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, gw / 2), [0, gh / 2, 0]))], outW, gr, true);
  }
  // ------------------------------------------------------------ occupancy and animation
  // does bridge b dock the current occupant: L1 docks door 1, the second bridge only a type with a documented
  // second-bridge door (T.dockX2), an upper-deck bridge only the A380's U1L; and only when the datasheet limits
  // (extension range, cab turn, rotunda swing, slope <= 1:4) allow it and a path clear of the aircraft exists
  docks(g, b) {
    const T = TYPES[g.acType] || TYPES[g._lastType]; if (!T) return false;
    if (b.upper) { if ((g.acType || g._lastType) !== 'a388') return false; }
    else if (b.door !== 1 && T.dockX2 == null) return false;
    else if (b.door !== 1 && g.dockCargo) return false;   // a freighter has no second passenger door (opts.freighter)
    return !!this.planFor(g, b).ok;
  }
  // current extension of a stand's bridges (0 = every bridge at rest .. 1 = docked). It is 0 as soon as the tunnels are
  // back at rest (the cab's height settle after that, `settles`, needs no hold). Departing aircraft: see the header and
  // docs/requests/bridges_closeout.md "Round 2 API for realtime" - the engine holds the body only until pushClearEta(g)
  // is 0, not until this is 0 (a retraction at the sheet's maximum rates takes 16-91 s)
  extension(g) { const a = this.anims.get(g.id); if (a) return a.k; return g.acType && this.bridgesOf(g).some(b => this.docks(g, b)) ? 1 : 0; }
  // seconds the current undock (or a future one from the docked state) takes: the sheet's rates along the docking path
  undockTime(g) { let t = 0; for (const b of this.bridgesOf(g)) { const P = this.planFor(g, b); if (P.ok) t = Math.max(t, P.total); } return t; }
  // typeKey: TYPES key of the parked aircraft (null = empty); pose: {nose:[s,t], dir:[s,t]}; icao: type designator;
  // opts.freighter: the occupant is a freighter (js/live/lookup.js isFreighter): only the door-1 bridge docks
  setOccupant(g, typeKey, animate, now, pose, icao, opts = {}) {
    const was = !!g.acType; if (typeKey) g._incoming = null; // (the announced arrival is here: its own clearance from now on)
    // the occupant whose door the bridges are at, retracting from or docking to; `same`: this one again (type, designator,
    // freighter, pose within 5 cm / 0.1 deg) - e.g. a departure signal that proved false (redock())
    const prev = { type: g.acType || g._lastType || null, pose: g.dock || null, icao: g.dockType || null, cargo: !!g.dockCargo };
    const same = !!typeKey && prev.type === typeKey && samePose(prev.pose, pose || null) && prev.icao === (icao || null) && prev.cargo === !!opts.freighter;
    // a docking requested while the bridges are not at rest (a retraction running, docked / docking to another pose):
    // where every bridge is now and the way it came, taken before the occupant changes (dockFrom; review round 2 v5)
    const L = typeKey && g.bridge && animate && (!was || !same) ? new Map(this.bridgesOf(g).map(b => [b, this.legsNow(g, b, now)])) : null;
    if (typeKey) { g.dock = pose || null; g.dockType = icao || null; g.dockCargo = !!opts.freighter; g._early = null; }
    // a new docking stops a rest-height settle where it is (the docking pre-positions from there)
    if (typeKey && this.settles) for (const b of this.bridgesOf(g)) if (this.settles.delete(b)) b._plans.clear();
    g.acType = typeKey || null; g.empty = !typeKey;
    if (typeKey) g._lastType = typeKey;
    if (g.bridge && animate && L && [...L].some(([b, l]) => l.post && (!l.park || this.docks(g, b)))) this.dockFrom(g, L, now, same && !was);
    else if (g.bridge && animate && was !== !!typeKey) {
      const cur = this.anims.get(g.id); const k0 = cur ? this.animK(cur, now) : (was ? 1 : 0);
      // the plans of this docking (arrival) or of the docking being undone (departure): the same path both ways
      let plans = cur && cur.plans ? cur.plans : new Map();
      if (typeKey && !(cur && cur.to === 1)) { plans = new Map(); for (const b of this.bridgesOf(g)) { const P = this.planFor(g, b); if (P.ok) plans.set(b, P); } }
      // undocking from the docked state: the same path back (levelPlan): the cab keeps the door's height only as far as
      // the tunnel stays within 1:4, then (at rest) settles to its rest height h0 at the sheet's lift rate (step())
      if (!typeKey && !(cur && cur.to === 1)) plans = this.undockPlans(g);
      let total = 0; for (const P of plans.values()) total = Math.max(total, P.total);
      if (!total) total = typeKey ? DOCK_TIME : UNDOCK_TIME;
      if (!typeKey && opts.undockS) total = Math.max(total, opts.undockS); // never faster than the sheet's rates
      const span = Math.abs((typeKey ? 1 : 0) - k0) || 1;
      this.anims.set(g.id, { from: k0, to: typeKey ? 1 : 0, t0: now + (typeKey ? DOCK_DELAY : 0) * 1000, dur: total * span * 1000, k: k0, plans });
    }
    // rest poses per occupant: the departing aircraft holds the bridges it parked for PARK_RETURN_S (an early undock: PARK_EARLY_S)
    if (typeKey) g._parkHold = null;
    else if (prev.type) { g._parkHold = { type: prev.type, pose: prev.pose, until: now + (opts.early ? PARK_EARLY_S : PARK_RETURN_S) * 1000 }; (this._holdG || (this._holdG = new Set())).add(g); }
    this._now = now; this.parkNear(g, now, !animate);
    this.dirty = true;
  }
  // bridge b now: its joint state q, the way it came from rest (pre: [rest .. q]) and the way on to the door it is
  // docking to / retracting from / docked at (post: [q .. door]; null at rest) - the running plan split at the animation's
  // k (a hurried retraction goes on along its tail: the rest of the path it was hurried on), else the docked or rest pose
  legsNow(g, b, now) {
    const a = this.anims.get(g.id); const P = a && a.plans && a.plans.get(b);
    if (P && P.ok && P.total) {
      let t = clampN(this.animK(a, now), 0, 1) * P.total, i = 0; for (; i < P.dur.length - 1 && t > P.dur[i]; i++) t -= P.dur[i];
      const q = this.qLerp(b, P.path[i], P.path[i + 1], P.dur[i] ? clampN(t / P.dur[i], 0, 1) : 1);
      const post = [q].concat(P.path.slice(i + 1)); const tail = a.tail && a.tail.get(b); if (tail) post.push(...tail.slice(1));
      return { q, pre: P.path.slice(0, i + 1).concat([q]), post, toRest: !!P.toRest };
    }
    if (!a && g.acType && this.docks(g, b)) { const Q = this.planFor(g, b); return { q: Q.q1, pre: Q.path.slice(), post: [Q.q1] }; }
    const r = { a: b.a0, e: b.e0, t: 0, h: b.hRest ?? b.h0 };
    if (this.parks && (this.parks.has(b) || b._parkQ)) { const q = this.restNow(b); return { q, pre: [r, q], post: [q, r], toRest: true, park: true }; } // (parked per occupant)
    return { q: r, pre: [r], post: null };
  }
  // a docking requested while bridges are not at rest (L: legsNow of every bridge before the occupant changed): every
  // bridge goes on from where it is - the same occupant back along the way it came (its post); another pose / aircraft
  // straight to the new stand-off point and in to the door, else back to rest and along the normal docking path, else
  // lifted; a bridge that does not dock it back to rest (the way it came, or retract - swing - extend, each also lifted).
  // EVERY one of these legs is tested against the NEW occupant (pathHits): the first clear one, else the fewest poses in
  // the body; a bridge with a part already in it moves at once (no DOCK_DELAY). Each new plan starts at rest (pre,
  // the way the bridge came, so an undocking or a hurry during it retracts along the same path), every segment timed at
  // the sheet's rates (segTime) and never faster (the pre parts are stretched so that all bridges sit at one animation
  // parameter k0 now). Before (review round 2 v5): the new plan was started at the running animation's k - the cabs
  // jumped by up to 8.3 m (a pose 10 cm off), 2.6 m (the same pose after a normal undock), 9.6 m (after a hurry)
  dockFrom(g, L, now, same) {
    const T = TYPES[g.acType]; const dn = g.dock ? g.dock.nose : g.nose, dd = g.dock ? g.dock.dir : g.dir;
    const f = stD(dd), nose = stW(dn, G); const n2 = [nose[0], nose[2]], f2 = [f[0], f[2]];
    const near = (A, B) => Math.abs(wrap(A.a - B.a)) < 1e-4 && Math.abs(A.e - B.e) < 1e-3 && Math.abs(A.t - B.t) < 1e-4 && Math.abs(A.h - B.h) < 1e-3;
    const dedupe = (P) => P.filter((q, i) => i === 0 || !near(q, P[i - 1]));
    const parts = []; let inside = false;
    // (close-out round 3 bridges-4: every leg is now tested against the NEW occupant - before, the way back to rest and
    // the leg of a bridge that does not dock it were not, so a bridge already in the new body waited there for DOCK_DELAY
    // and backed out through it, and an undocking during this one retraced the old way into it)
    const restQ = (b) => ({ a: b.a0, e: b.e0, t: 0, h: b.hRest ?? b.h0 });
    const cost = (b, pts, toDoor) => this.pathHits(b, pts, T, n2, f2, toDoor, true);
    const pick = (C) => { // C: [{pts, toDoor}] in order of preference: the first clear one, else the fewest poses in the
      // aircraft (then within its clearance)
      let best = null; for (const c of C) { c.k = cost(c.b, c.pts, c.toDoor); if (!c.k.fixed && !c.k.n) return c;
        if (!c.k.fixed && (!best || c.k.n0 < best.k.n0 || (c.k.n0 === best.k.n0 && c.k.n < best.k.n))) best = c; }
      return best || C[0]; };
    const inNow = (b, q) => this.solidsQ(b, q, 0).some(bx => boxHitsAc(bx, T, n2, f2, 0));
    for (const b of this.bridgesOf(g)) {
      const l = L.get(b); const Pn = this.docks(g, b) ? this.planFor(g, b) : null;
      if (l.park) { if (!Pn) continue; this.parks.delete(b); b._parkQ = null; } // (parked per occupant: stays so unless it docks)
      if (!l.post) { if (Pn) parts.push({ b, pre: [l.q], post: Pn.path.slice(), Pn }); continue; }  // at rest: the normal docking
      // the way back to rest: the way it came (reversed), or straight back - retract at its angle (cab straightened), swing
      // at the operational retraction, extend to the rest pose (all within 1:4)
      // (and both of these lifted first by 1.5 / 2.5 m where the 1:4 band allows: over a wing that came to lie under it)
      const r = restQ(b), q = l.q, bh = (e, h) => this.bandH(b, e, h, SLOPE_MAX), oR = b.m.opR;
      const retract = (dh) => { const h1 = bh(q.e, q.h + dh), h2 = bh(oR, h1); return dedupe([q, { ...q, h: h1 }, { a: q.a, e: oR, t: 0, h: h2 }, { a: r.a, e: oR, t: 0, h: bh(oR, h2) }, { ...r, h: bh(r.e, h2) }, r]); };
      const backs = [{ b, pts: dedupe(l.pre.slice().reverse().concat([r])), toDoor: false, way: 'pre' }, { b, pts: retract(0), toDoor: false, way: 'retract' },
        { b, pts: retract(1.5), toDoor: false, way: 'retract+1.5' }, { b, pts: retract(2.5), toDoor: false, way: 'retract+2.5' }];
      // a part already in the new body: the bridge moves at once (no DOCK_DELAY hold), on the way out with the fewest poses in it
      if (inNow(b, q)) inside = true;
      let post, pre = l.pre;
      if (Pn && same && !l.toRest && near(l.post[l.post.length - 1], Pn.q1)) post = l.post; // (the same occupant: back the way it came)
      else {
        const back = pick(backs); pre = back.pts.slice().reverse(); // (an undocking during this one retraces the chosen way back)
        if (!Pn) post = back.pts;
        else { const via = { b, pts: back.pts.concat(Pn.path.slice(1)), toDoor: true }; const qs = Pn.qs;
          const up = (dh) => { const h1 = bh(q.e, q.h + dh); return dedupe([q, { ...q, h: h1 }, { ...qs, h: bh(qs.e, h1) }, { ...qs }, Pn.q1]); };
          const ch = pick([{ b, pts: [q, { ...qs }, Pn.q1], toDoor: true }, via, { b, pts: up(1.5), toDoor: true }, { b, pts: up(2.5), toDoor: true }]); post = ch.pts;
          if (ch === via) pre = back.pts.slice().reverse(); }
        b._dockFromHit = back.k && (back.k.n0 || back.k.fixed) ? { n0: back.k.n0, fixed: back.k.fixed, way: back.way, t: now } : null; // (checkers' diagnostics)
      }
      parts.push({ b, pre, post, Pn });
    }
    const time = (b, pts, door) => { const d = []; for (let i = 1; i < pts.length; i++) d.push(this.segTime(b, pts[i - 1], pts[i], door && i === pts.length - 1)); return d; };
    const sum = (d) => d.reduce((x, y) => x + y, 0);
    for (const p of parts) { p.pre = dedupe(p.pre); p.post = dedupe(p.post); p.dPre = time(p.b, p.pre, false); p.dPost = time(p.b, p.post, !!p.Pn); p.tPre = sum(p.dPre); p.tPost = sum(p.dPost); }
    const D = Math.max(0, ...parts.map(p => p.tPost));
    if (!(D > 0)) { this.anims.delete(g.id); return; } // (every bridge already where it ends)
    for (const p of parts) if (!(p.tPost > 0)) { p.post = [p.post[0], p.post[0]]; p.dPost = [D]; p.tPost = D; } // (stays put meanwhile)
    const k0 = Math.min(0.999, Math.max(...parts.map(p => p.tPre / (p.tPre + p.tPost))));
    const plans = new Map();
    for (const p of parts) {
      const want = k0 / (1 - k0) * p.tPost; let pre = p.pre, dPre = p.dPre;
      if (pre.length < 2) { if (want > 1e-6) { pre = [pre[0], pre[0]]; dPre = [want]; } } else if (p.tPre < want) dPre = dPre.map(x => x * want / p.tPre);
      const path = pre.concat(p.post.slice(1)), dur = dPre.concat(p.dPost);
      plans.set(p.b, { ok: true, T: (p.Pn && p.Pn.T) || T || null, q0: path[0], q1: path[path.length - 1], qs: p.Pn ? p.Pn.qs : null, path, dur, total: sum(dur),
        slope: p.Pn ? p.Pn.slope : 0, door: p.Pn ? p.Pn.door : null, toRest: !p.Pn, trans: true });
    }
    this.anims.set(g.id, { from: k0, to: 1, t0: now + (same || inside ? 0 : DOCK_DELAY) * 1000, dur: D * 1000, k: k0, plans });
  }
  // undocking plans of the current occupant from the docked state (levelPlan of each docking bridge's plan; cached)
  // ------------------------------------------------------------ rest pose per occupant (close-out round 7, PARK_* above)
  // where a bridge that is not docking / docked rests now: on its way to / back from a parked pose (this.parks: {pts, dur,
  // total, t0}), parked (b._parkQ) or the data rest (cab height: b.hRest, the undocking settle)
  restNow(b) {
    const p = this.parks && this.parks.get(b);
    if (p) { let t = ((this._now ?? Date.now()) - p.t0) / 1000; if (t <= 0) return p.pts[0];
      for (let i = 0; i < p.dur.length; i++) { if (t <= p.dur[i]) return this.qLerp(b, p.pts[i], p.pts[i + 1], p.dur[i] ? t / p.dur[i] : 1); t -= p.dur[i]; }
      return p.pts[p.pts.length - 1]; }
    return b._parkQ || { a: b.a0, e: b.e0, t: 0, h: b.hRest ?? b.h0 };
  }
  // the stands whose aircraft can reach the bridges of stand g (nose within PARK_NEAR m)
  nearStands(g) {
    if (g._nearS) return g._nearS; const n = stW(g.nose, G);
    return (g._nearS = (this.gates || []).filter(o => { if (o === g || !o.nose) return false; const m = stW(o.nose, G); return Math.hypot(m[0] - n[0], m[2] - n[2]) < PARK_NEAR; }));
  }
  // the aircraft bridge b of stand g must keep its stand clearance to: the one parked at g when b does not dock it, those
  // parked at the stands around, and - while b is parked - a departing one for its hold (o._parkHold)
  parkOcc(g, b, holds = !!b._parkQ) {
    const out = []; const now = this._now ?? Date.now();
    const add = (o, tk, pose, mg = 0.5) => { const T = TYPES[tk]; if (!T || !T.wing) return; const f = stD(pose ? pose.dir : o.dir), n = stW(pose ? pose.nose : o.nose, G);
      out.push({ tk, T, nose: [n[0], n[2]], f: [f[0], f[2]], need: icaoClear(T.wing.span), mg }); };
    for (const o of [g].concat(this.nearStands(g))) {
      if (o.acType) { if (o !== g || !this.docks(g, b)) add(o, o.acType, o.dock); }
      else if (holds && o._parkHold && o._parkHold.until > now) add(o, o._parkHold.type, o._parkHold.pose);
      // (an arrival announced for stand o -- expectArrival: every bridge, the ones that will dock it too, keeps its clearance
      // and its taxi-in sweep from its stand pose, so a rest in its way parks before it passes; R7.4.1)
      if (!o.acType && o._incoming && o._incoming.until > now) add(o, o._incoming.type, o._incoming.pose, EXPECT_MG);
    }
    return out;
  }
  // the rest pose for the aircraft around (null: the data rest), cached per set of aircraft and poses
  parkTarget(g, b) {
    if (b.upper || !b.m) return null; const occ = this.parkOcc(g, b); if (!occ.length) return null;
    const key = occ.map(o => o.tk + '@' + o.nose[0].toFixed(1) + ',' + o.nose[1].toFixed(1) + ',' + o.f[0].toFixed(3) + ',' + o.f[1].toFixed(3) + '~' + o.mg).sort().join('|');
    if (b._parkC && b._parkC.key === key) return b._parkC.q;
    const q = this.parkChoose(g, b, occ); b._parkC = { key, q }; return q;
  }
  // the other stands' bridges' solids a parked pose must not overlap (0.05 m, as fixedHit): at rest (fixed parts too) and in
  // every docked pose (their docking does not test the other bridges' moving parts); the own stand's other bridges: below
  parkObs(g, b) {
    if (b._parkObs) return b._parkObs; const out = []; const sib = new Set(this.bridgesOf(g));
    for (const o of [g].concat(this.nearStands(g))) { if (!o.bridge) continue; for (const ob of this.bridgesOf(o)) {
      if (ob === b || sib.has(ob)) continue; if (!ob.m) this.prepBridge(o, ob); if (Math.hypot(ob.rot[0] - b.rot[0], ob.rot[2] - b.rot[2]) > b.e0 + ob.e0 + 12) continue;
      for (const s of this.solidsQ(ob, { a: ob.a0, e: ob.e0, t: 0, h: ob.h0 }, 0, true)) out.push(s);
      for (const t of ob._tg || []) for (const s of this.solidsQ(ob, { a: t.a, e: t.e, t: 0, h: t.sill }, 1)) out.push(s); } }
    for (const s of out) s.rr = s.round || Math.hypot(s.hl, s.hw);
    return (b._parkObs = out);
  }
  // the way from pose A to pose B at rest: retract (or extend last), swing at the shorter length - each sample clear of the
  // fixed walkways, the building and (0.3 m) every aircraft in occ; null if none is
  parkPath(b, A, B, occ) {
    const e = Math.min(A.e, B.e), hm = this.bandH(b, e, A.e <= B.e ? A.h : B.h, SLOPE_MAX);
    const near = (p, q) => Math.abs(wrap(p.a - q.a)) < 1e-4 && Math.abs(p.e - q.e) < 1e-3 && Math.abs(p.h - q.h) < 1e-3;
    const pts = [A, { a: A.a, e, t: 0, h: hm }, { a: B.a, e, t: 0, h: hm }, B].filter((q, i, P) => i === 0 || !near(q, P[i - 1]));
    const fx0 = !!this.fixedHit(b, A), bl0 = !!this.bldHit(b, A); // (a data rest already in a fixed walkway / outline - A12, F5, F14, F17, F19, F21 L1: only new contacts count)
    for (let i = 1; i < pts.length; i++) for (let k = 1; k <= 8; k++) { const q = this.qLerp(b, pts[i - 1], pts[i], k / 8);
      if ((!fx0 && this.fixedHit(b, q)) || (!bl0 && this.bldHit(b, q))) return null;
      if (this.solidsQ(b, q, 0).some(bx => occ.some(O => boxHitsAc(bx, O.T, O.nose, O.f, 0.3)))) return null; }
    return pts;
  }
  parkChoose(g, b, occ) {
    const M = { a: b.a0, e: b.e0, t: 0, h: b.h0 }; const S = (q) => this.solidsQ(b, q, 0);
    const touch = (q) => S(q).some(bx => occ.some(O => boxHitsAc(bx, O.T, O.nose, O.f, O.mg ?? 0.5) || boxHitsSwept(bx, O.T, O.nose, O.f, Math.max(0.3, (O.mg ?? 0.5) - 0.2), O.T.L + 15)));
    const short = (q, d = 0) => S(q).some(bx => occ.some(O => boxHitsAc(bx, O.T, O.nose, O.f, Math.max(0.5, O.need - d), true))); // inside the clearance
    if (!short(M) && !touch(M)) return null; // the data rest holds the clearance: it stays
    const obs = this.parkObs(g, b); const sibs = this.bridgesOf(g).filter(o => o !== b && g.acType && this.docks(g, o));
    const live = []; // (0.3 m: the own stand's bridges docking the occupant now - their path and door - and the bridges parked now)
    for (const o of sibs) { const P = this.planFor(g, o); for (let i = 1; i < P.path.length; i++) for (let k = 0; k <= 6; k++) live.push(...this.solidsQ(o, this.qLerp(o, P.path[i - 1], P.path[i], k / 6), 0)); }
    for (const o of [g].concat(this.nearStands(g))) if (o.bridge) for (const ob of this.bridgesOf(o)) if (ob !== b && ob._parkQ) live.push(...this.solidsQ(ob, ob._parkQ, 0));
    for (const s of live) s.rr = s.round || Math.hypot(s.hl, s.hw);
    const accs = []; for (const o of [g].concat(this.nearStands(g))) for (const A of this.standAircraft(o)) if (Math.hypot(A.nose[0] - b.rot[0], A.nose[1] - b.rot[2]) < 95) accs.push(A);
    const free = (q, swung) => { if (!this.jointOk(b, q, null).ok) return false;
      for (const bx of S(q)) { const r = Math.hypot(bx.hl, bx.hw) + 0.3;
        for (const [L, cl] of [[obs, 0.05], [live, 0.3]]) for (const o of L) if (Math.abs(o.c[0] - bx.c[0]) < o.rr + r && Math.abs(o.c[1] - bx.c[1]) < o.rr + r && o.hi > bx.lo && bx.hi > o.lo && solidOverlap(bx, o, cl)) return false;
        if (swung && accs.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 0.5))) return false; } // (a swung pose leaves the data rest's footprint)
      return true; };
    const C = [];
    for (let e = b.e0; e >= b.m.opR - 0.25; e -= 0.5) for (let da = 0; da <= PARK_SWING; da += 5) for (const sg of da ? [1, -1] : [1]) {
      const q = { a: b.a0 + sg * da * DEG, e: Math.max(e, b.m.opR), t: 0 }; q.h = this.bandH(b, q.e, b.h0, SLOPE_TARGET); C.push({ q, da, cost: da * DEG * q.e + (b.e0 - q.e) }); }
    C.sort((x, y) => x.cost - y.cost);
    for (const c of C) if (!short(c.q) && !touch(c.q) && free(c.q, c.da > 0) && this.parkPath(b, M, c.q, occ)) return c.q;
    // none holds the full clearance: the largest gain (>= 0.5 m) among the full retraction and the swings at it
    const gap = (q) => { let d = 0; while (d < 7.5 && short(q, d)) d += 0.25; return d; }; const g0 = gap(M); let best = null;
    for (const c of C) if (c.da === 0 || c.q.e <= b.m.opR + 1e-6) { if (touch(c.q) || !free(c.q, c.da > 0)) continue; const d = gap(c.q); if (d <= g0 - 0.5 && (!best || d < best.d) && this.parkPath(b, M, c.q, occ)) best = { q: c.q, d }; }
    return best ? best.q : null;
  }
  // pre-arrival rest poses (close-out round 7 verifier, R7.4.1): the engine announces the arrival that is about to take stand
  // g (traffic.js expectStand: the lead-in it is docking to, or SFO's arrival record within EXPECT_M of the stop), so a bridge
  // whose rest is inside that aircraft's clearance or taxi-in sweep parks BEFORE it passes, not after it has stopped (DAL672
  // C9 L1, SWA375 D3 L1 at rest in the arrival's way). A bridge that docks it docks from the parked pose (dockFrom). A null
  // type withdraws the announcement; it lapses EXPECT_HOLD_S after the last renewal; setOccupant() replaces it
  // pose: { nose: [s, t], dir: [ds, dt] } (as setOccupant) -- the arrival's own stop pose on its stand (app.js poseST of
  // traffic.js tr._expPose); null: stand g's own pose
  expectArrival(g, typeKey, pose = null, now = Date.now()) {
    const samePose = (p, q) => (!p && !q) || (p && q && Math.hypot(p.nose[0] - q.nose[0], p.nose[1] - q.nose[1]) < 0.5 && Math.abs(p.dir[0] - q.dir[0]) + Math.abs(p.dir[1] - q.dir[1]) < 0.01);
    if (!g || !g.bridge) return; const tk = typeKey && TYPES[typeKey] ? typeKey : null; const prev = g._incoming;
    if (!tk) { if (!prev) return; g._incoming = null; }
    else if (prev && prev.type === tk && samePose(prev.pose, pose)) { prev.until = now + EXPECT_HOLD_S * 1000; return; }
    else { g._incoming = { type: tk, pose: pose || null, until: now + EXPECT_HOLD_S * 1000 }; (this._incG || (this._incG = new Set())).add(g); }
    this._now = now; this.parkNear(g, now); this.dirty = true;
  }
  // start (or snap) the bridges of stand g - and of the stands around it - towards their rest poses for the aircraft around
  parkNear(g, now, snap = false) { this.parkUpdate(g, now, snap); for (const o of this.nearStands(g)) if (o.bridge) this.parkUpdate(o, now, snap); }
  parkUpdate(g, now, snap = false) {
    if (!g.bridge) return; const PK = this.parks || (this.parks = new Map()); const a = this.anims.get(g.id);
    const near = (p, q) => Math.abs(wrap(p.a - q.a)) < 1e-4 && Math.abs(p.e - q.e) < 1e-3 && Math.abs(p.h - q.h) < 1e-3;
    for (const b of this.bridgesOf(g)) {
      if (b.upper || !b.m || (a && a.plans && a.plans.has(b)) || (g.acType && this.docks(g, b))) continue; // (the stand's animation moves it)
      const T = this.parkTarget(g, b), to = T || { a: b.a0, e: b.e0, t: 0, h: b.hRest ?? b.h0 };
      const P0 = PK.get(b), end = P0 ? P0.pts[P0.pts.length - 1] : (b._parkQ || { a: b.a0, e: b.e0, t: 0, h: b.hRest ?? b.h0 });
      if (near(end, to)) { if (!P0) b._parkQ = T; continue; }
      if (snap) { PK.delete(b); b._parkQ = T; this.dirty = true; continue; }
      const pts = this.parkPath(b, this.restNow(b), to, this.parkOcc(g, b, true)); if (!pts) continue; // (no clear way: stays; re-checked at the next change)
      const dur = []; for (let i = 1; i < pts.length; i++) dur.push(this.segTime(b, pts[i - 1], pts[i], false));
      PK.set(b, { pts, dur, total: dur.reduce((x, y) => x + y, 0), t0: now }); b._parkQ = T; this.dirty = true;
    }
  }
  undockPlans(g) {
    const plans = new Map(); if (!g.acType && !g._lastType) return plans;
    for (const b of this.bridgesOf(g)) { if (!this.docks(g, b)) continue; const P = this.planFor(g, b); plans.set(b, P._level || (P._level = this.levelPlan(b, P))); }
    return plans;
  }
  // ------------------------------------------------------------ departures (engine API, bridges_closeout.md "Round 2")
  // The real bridge is retracted BEFORE the push-back; ADS-B shows a departure only once the push is under way. So:
  //  * undockEarly(g, now): the engine's earliest departure signal (SFO allocation window ending, beacon / engine start,
  //    a push clearance, ...): the bridges retract now at the sheet's rates while the aircraft stays parked; the ground
  //    equipment leaves with it. Returns the seconds until extension(g) is 0.
  //  * redock(g, now): undo a false signal - the running retraction reverses along its own path to the door.
  //  * hurryUndock(g, s, now): the push has begun with the bridge still out - the running retraction continues from
  //    where it is at the sheet's maximum rates (16-91 s from docked, p50 27 s; never squeezed).
  //  * pushClearEta(g, now): seconds until every bridge is clear of the occupant's straight push-back (its body swept
  //    backward along its heading by its length + 15 m, 0.3 m clearance): the cab backed off the door and out of the
  //    way - the only hold the body needs. For a docked stand with no retraction running, the hold a hurryUndock() now
  //    would need. undockEta(g, now): seconds until extension(g) is 0 (likewise).
  undockEarly(g, now = Date.now()) {
    if (!g.bridge || !g.acType) return this.undockEta(g, now);
    const e = { type: g.acType, pose: g.dock, icao: g.dockType, freighter: g.dockCargo, t: now };
    this.setOccupant(g, null, true, now, null, null, { early: true }); g._early = e;
    const a = this.anims.get(g.id); if (a) a.early = true;
    return this.undockEta(g, now);
  }
  redock(g, now = Date.now()) {
    const e = g._early; if (!e) return 0;
    // the early occupant again: setOccupant() with the same type, designator and pose reverses every bridge from where it
    // is along the way it came (dockFrom; a hurried retraction along its tail), or docks it normally once back at rest
    g._early = null; this.setOccupant(g, e.type, true, now, e.pose, e.icao, { freighter: e.freighter });
    return this.dockEta(g, now);
  }
  animK(a, now) { const u = a.dur > 0 ? clampN((now - a.t0) / a.dur, 0, 1) : 1; return a.from + (a.to - a.from) * u; }
  // seconds until a docking in progress reaches the door (0: none running)
  dockEta(g, now = Date.now()) { const a = this.anims.get(g.id); if (!a || a.to !== 1) return 0; let t = Math.max(0, a.t0 + a.dur - now); for (let n = a.next; n; n = n.next) t += n.dur; return t / 1000; }
  // the retraction from animation parameter kc of `plans` at the sheet's maximum rates (rest .. the pose at kc): {plans, T}
  hurryPlans(plans, kc) {
    const out = new Map(); let T = 0;
    for (const [b, P] of plans) {
      if (!P.ok || !P.total) continue;
      if (kc >= 1 - 1e-9 && P._h1) { out.set(b, P._h1); T = Math.max(T, P._h1.total); continue; }
      // the pose now, and the path from the rest pose up to it
      let t = clampN(kc, 0, 1) * P.total, i = 0; for (; i < P.dur.length - 1 && t > P.dur[i]; i++) t -= P.dur[i];
      const qc = this.qLerp(b, P.path[i], P.path[i + 1], P.dur[i] ? clampN(t / P.dur[i], 0, 1) : 1);
      const path = P.path.slice(0, i + 1).concat([qc]); const dur = []; for (let j = 1; j < path.length; j++) dur.push(this.segTimeMin(b, path[j - 1], path[j]));
      const total = dur.reduce((x, y) => x + y, 0); T = Math.max(T, total);
      const H = { ...P, path, dur, total, q1: qc, _pk: undefined, _h1: undefined, _level: undefined }; out.set(b, H);
      if (kc >= 1 - 1e-9) P._h1 = H;
    }
    return { plans: out, T };
  }
  // the engine's fast retraction of a departing aircraft's bridges (docs/requests/realtime_round2.md §1a; js/live/app.js
  // and tools/live/invariants.mjs call it right after setOccupant(g, null)): the undocking restarts now from where the
  // bridges are, along the same path, at the Oshkosh AeroTech sheet's maximum rates (27 m/min at the cab pivot, cab 145
  // deg/min, lift 1.09 m/min; no 3 s allowance per motion, the back-off from the door at the drive speed) - in `s`
  // seconds when that is slower, never faster. Returns the seconds the retraction takes (0: nothing to hurry). The
  // engine holds the body only for pushClearEta(g) (from docked p50 1.0 s, p99 4.7 s, max 25 s), not for this.
  hurryUndock(g, s = 0, now = Date.now()) {
    const a = this.anims.get(g.id); if (!a || a.to !== 0 || !a.plans || !a.plans.size) return 0;
    const kc = this.animK(a, now); if (kc <= 1e-4) return 0;
    if (a.fast && s <= a.dur / 1000) return Math.max(0, a.t0 + a.dur - now) / 1000; // (already at the maximum rates)
    const { plans, T } = this.hurryPlans(a.plans, kc); if (!plans.size) return 0;
    // (tail: the rest of the path to the door from where it is hurried - a re-dock goes back along it; a second hurry
    // keeps the first one's tail: review round 2 v5, the original path was lost and a re-dock snapped 10.5 m)
    const tail = new Map(); for (const b of plans.keys()) tail.set(b, this.legsNow(g, b, now).post);
    const dur = Math.max(s, T); this.anims.set(g.id, { from: 1, to: 0, t0: now, dur: dur * 1000, k: 1, plans, fast: true, early: a.early, tail }); this.dirty = true;
    return dur;
  }
  undockEta(g, now = Date.now()) {
    const a = this.anims.get(g.id);
    if (a && a.to === 0) return Math.max(0, a.t0 + a.dur - now) / 1000;
    if (a && a.to === 1) return this.hurryPlans(a.plans, this.animK(a, now)).T;
    if (!g.acType) return 0;
    return this.hurryPlans(this.undockPlans(g), 1).T;
  }
  pushClearEta(g, now = Date.now()) {
    const e = g._early; const tk = g.acType || (e && e.type) || g._lastType; const T = tk && TYPES[tk]; const pose = (e && e.pose) || g.dock;
    if (!T || !pose) return 0;
    const nose = stW(pose.nose, G), f = stD(pose.dir); const n2 = [nose[0], nose[2]], f2 = [f[0], f[2]];
    let a = this.anims.get(g.id);
    if (a && a.to === 1 && a._pc && Math.abs(now - a._pc.t) < 500) return a._pc.v; // (a docking in progress: re-planned twice a second)
    if (!a || a.to !== 0) { // no retraction running: the one a hurryUndock() would start now
      const P0 = a ? a.plans : (g.acType ? this.undockPlans(g) : null); if (!P0 || !P0.size) return 0;
      const H = this.hurryPlans(P0, a ? this.animK(a, now) : 1); if (!H.plans.size) return 0;
      a = { from: 1, to: 0, t0: now, dur: H.T * 1000, plans: H.plans };
    }
    let eta = 0;
    for (const [b, P] of a.plans) {
      const kh = P._pk ?? (P._pk = this.pushHitK(b, P, T, n2, f2)); if (kh < 0) continue;   // -1: never touches
      const t = a.t0 + a.dur * (a.from - kh) / Math.max(1e-9, a.from - a.to);             // when k falls to kh
      eta = Math.max(eta, (t - now) / 1000);
    }
    const A0 = this.anims.get(g.id); if (A0 && A0.to === 1) A0._pc = { t: now, v: Math.max(0, eta) };
    return Math.max(0, eta);
  }
  // the animation parameter at and below which bridge b's plan P stays clear of the straight push-back of type T (nose
  // [x, z], heading f): the last clear sample below the lowest pose that touches it (-1: no pose touches it; 0: even the
  // rest pose does - then clear only at rest)
  pushHitK(b, P, T, nose, f) {
    if (!P.ok || !P.total || !T) return -1;
    let acc = 0, kPrev = 0;
    for (let i = 0; i < P.dur.length; i++) {
      const n = clampN(Math.ceil(P.dur[i] / 0.5), 2, 24); const last = i === P.dur.length - 1;
      for (let j = i ? 1 : 0; j <= n; j++) {
        const u = j / n, k = (acc + P.dur[i] * u) / P.total; const q = this.qLerp(b, P.path[i], P.path[i + 1], u);
        for (const bx of this.solidsQ(b, q, last ? u : 0)) if (boxHitsSwept(bx, T, nose, f, 0.3, T.L + 15)) return kPrev;
        kPrev = k;
      }
      acc += P.dur[i];
    }
    return -1;
  }
  // full: rebuild the static set (bridges at rest, stand equipment, vehicles); always rebuild moving bridges
  build(now, full) {
    if (full) {
      this.staticSprites = [];
      const geo = new Geo(), sgn = newSignGeo();
      this.vehicleBuckets = {}; for (const k in this.vehicleMeshes) this.vehicleBuckets[k] = [];
      this.keepOut = this.aircraftFootprints ? this.aircraftFootprints() : [];
      this.sprites = this.staticSprites;
      for (const g of this.gates) {
        if (!g.bridge) continue;
        if (!this.anims.has(g.id) && !this.settling(g)) { const Ps = this.bridgesOf(g).map(b => this.bridgeGeo(g, b, g.acType && this.docks(g, b) ? 1 : 0, geo, sgn)); if (g.acType) this.placeVehicles(g, Ps); }
        this.standGeo(g, geo, sgn);
      }
      if (this.staticMesh) this.staticMesh.dispose(); if (this.signMesh) this.signMesh.dispose();
      this.staticMesh = meshOf(geo); this.signMesh = meshOfSign(sgn);
      for (const k in this.vehicleBuckets) { const list = this.vehicleBuckets[k]; this.vehicleMeshes[k].setInstances(new Float32Array(list.flat()), list.length); }
    }
    if (this.dynMesh) { this.dynMesh.dispose(); this.dynMesh = null; } if (this.dynSign) { this.dynSign.dispose(); this.dynSign = null; }
    this.dynSprites = []; this.sprites = this.dynSprites;
    if (this.anims.size || (this.settles && this.settles.size) || (this.parks && this.parks.size)) {
      const dyn = new Geo(), dsgn = newSignGeo();
      for (const g of this.gates) { if (!g.bridge) continue; const a = this.anims.get(g.id); if (a) { for (const b of this.bridgesOf(g)) this.bridgeGeo(g, b, a.plans && a.plans.has(b) ? a.k : 0, dyn, dsgn); } else if (this.settling(g)) for (const b of this.bridgesOf(g)) this.bridgeGeo(g, b, 0, dyn, dsgn); }
      this.dynMesh = dyn.nv ? meshOf(dyn) : null; this.dynSign = dsgn.pos.length ? meshOfSign(dsgn) : null;
    }
    this.sprites = (this.staticSprites || []).concat(this.dynSprites);
  }
  settling(g) { return !!((this.settles && this.settles.size && this.bridgesOf(g).some(b => this.settles.has(b))) || (this.parks && this.parks.size && this.bridgesOf(g).some(b => this.parks.has(b)))); }
  // advance the docking animations to `now` (called by items(); a checker without the renderer may call it directly)
  step(now) {
    let moving = false; const S = this.settles || (this.settles = new Map());
    for (const [id, a] of this.anims) {
      const u = Math.min(1, Math.max(0, (now - a.t0) / a.dur)); a.k = a.from + (a.to - a.from) * u; moving = true;
      if (u >= 1 && a.next) { this.anims.set(id, { ...a.next, t0: now, k: a.next.from }); continue; } // (redock(): chained leg)
      if (u >= 1) {
        this.anims.delete(id); this.dirty = true; (this._parkG || (this._parkG = [])).push(id); // (rest per occupant: re-checked below)
        // a retracted bridge ends at the height its undocking plan left it (the door's, within 1:4) and then settles to
        // its rest height h0 (rest tunnel <= 1:12) at the sheet's lift rate (1.09 m/min); the engine does not wait for it
        if (a.to === 0) for (const [b, P] of a.plans || []) { if (P.ok) { b.hRest = P.path[0].h; b._plans.clear(); if (Math.abs(b.hRest - b.h0) > 0.005) S.set(b, { from: b.hRest, t0: now, dur: Math.abs(b.h0 - b.hRest) / LIFT_RATE * 1000 }); } }
      }
    }
    for (const [b, st] of S) {
      const u = Math.min(1, Math.max(0, (now - st.t0) / st.dur)); b.hRest = st.from + (b.h0 - st.from) * u; moving = true;
      if (u >= 1) { S.delete(b); b.hRest = b.h0; b._plans.clear(); this.dirty = true; }
    }
    this._now = now;
    if (this.parks) for (const [b, p] of this.parks) { if (now - p.t0 >= p.total * 1000) { this.parks.delete(b); this.dirty = true; } else moving = true; }
    if (this._parkG && this._parkG.length) { const ids = new Set(this._parkG); this._parkG = []; for (const g of this.gates) if (ids.has(g.id)) this.parkNear(g, now); }
    if (this._holdG && this._holdG.size) for (const g of [...this._holdG]) if (!g._parkHold || g._parkHold.until <= now) { this._holdG.delete(g); g._parkHold = null; this.parkNear(g, now); }
    if (this._incG && this._incG.size) for (const g of [...this._incG]) if (!g._incoming || g._incoming.until <= now) { this._incG.delete(g); if (g._incoming) { g._incoming = null; this.parkNear(g, now); } }
    // rest-pose version (close-out round 7 verifier, R7.4.2): counts the changes of any bridge's rest per occupant (a park
    // starting / ending, a parked pose taken or dropped) so ground.js restBridgeField rebuilds the rest-bridge grid
    let rc = false; for (const g of this.gates) for (const b of g.bridges || []) { const sg = (this.parks && this.parks.get(b)) || b._parkQ || null; if (b._restSig !== sg) { b._restSig = sg; rc = true; } }
    if (rc) this.restVer = (this.restVer || 0) + 1;
    return moving;
  }
  items(now = Date.now()) {
    const moving = this.step(now);
    if (this.dirty || !this.staticMesh) { this.dirty = false; this.build(now, true); }
    else if (moving || this._hadDyn) this.build(now, false);
    this._hadDyn = moving;
    const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
    const out = [];
    if (this.staticMesh) out.push({ mesh: this.staticMesh, prog: 'obj', model: I4, bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
    if (this.dynMesh) out.push({ mesh: this.dynMesh, prog: 'obj', model: I4, bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
    if (this.signMesh) out.push({ mesh: this.signMesh, prog: 'sign', bbox: this.bbox, castShadow: false, noCull: true, nearOnly: true, uniforms: { uAtlas: this.atlas.tex } });
    if (this.dynSign) out.push({ mesh: this.dynSign, prog: 'sign', bbox: this.bbox, castShadow: false, noCull: true, nearOnly: true, uniforms: { uAtlas: this.atlas.tex } });
    for (const k in this.vehicleMeshes) out.push({ mesh: this.vehicleMeshes[k], prog: 'objI', bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 }, shadowMaxCascade: 2 });
    return out;
  }
  // ground service vehicles around the parked aircraft (actual pose), with collision rejection: each vehicle's hull
  // (the extents of its mesh, js/world/gates.js buildVehicleMeshes) is sampled every 0.3 m with its heights against the
  // parked aircraft (fuselage cross-section, wings, engines, tail), the other parked aircraft, the bridges' solids, the
  // terminal outline and the vehicles already placed (review 2026-11-04: belt loaders were never placed - their test
  // box reached into the height-blind fuselage band - and the fuel truck's mesh overhung its test box)
  placeVehicles(g, Ps) {
    if (!g.dock || !Ps.length) return;
    const P = Ps[0];
    const R = rng(hash(g.id)); const T = P.T;
    const f = stD(g.dock.dir); const r = v3.norm(v3.cross(f, [0, 1, 0])); const nose = stW(g.dock.nose, G);
    const n2 = [nose[0], nose[2]], f2 = [f[0], f[2]], r2 = [-f2[1], f2[0]];
    const self = footprint(nose, f, T, g);
    const at = (along, sideOff, yaw = 0) => { const p = v3.add(v3.sub(nose, v3.mul(f, along)), v3.mul(r, sideOff)); const c = Math.cos(yaw), s = Math.sin(yaw); const d = v3.norm(v3.add(v3.mul(f, c), v3.mul(r, s))); return { M: m4.basis(d, [0, 1, 0], [p[0], G, p[2]]), p, d }; };
    // the bridges' real solids (docked or at rest), 0.5 m clearance
    const solids = []; for (const b of this.bridgesOf(g)) for (const s of this.solids(g, b, this.docks(g, b) ? 1 : 0)) solids.push(s);
    const placed = [];
    // hull of a vehicle at v: local boxes [x0, x1, z0, z1, y0, y1] (x forward, z right), plus an optional sloped conveyor
    // {x0, y0, len, th, w, h, xe} whose last 1.0 m (the end and its bumper on the cargo-door sill) may touch the fuselage
    // and whose rest keeps 0.1 m under the lower lobe (the chassis and the other vehicles 0.3 m)
    let label = ''; const no = (why) => { if (this.gseWhy) this.gseWhy.push(label + ': ' + why); return false; }; // (gseWhy: checkers' diagnostics)
    const ok = (v, boxes, belt = null, lab = '') => { label = lab;
      const rt = [-v.d[2], v.d[0]]; const W = (x, z) => [v.p[0] + v.d[0] * x + rt[0] * z, v.p[2] + v.d[2] * x + rt[1] * z];
      const smp = []; // [x, z (world), lo, hi (above the apron), margin, closure]
      for (const [x0, x1, z0, z1, y0, y1] of boxes) { const nx = Math.max(1, Math.ceil((x1 - x0) / 0.3)), nz = Math.max(1, Math.ceil((z1 - z0) / 0.3));
        for (let i = 0; i <= nx; i++) for (let j = 0; j <= nz; j++) smp.push([...W(x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz), y0, y1, 0.3, false, false]); }
      if (belt) { const n = Math.ceil(belt.len / 0.3); for (let i = 0; i <= n; i++) { const s = belt.len * i / n; const x = belt.x0 + s * Math.cos(belt.th), y = belt.y0 + s * Math.sin(belt.th);
        for (const z of [-belt.w / 2, 0, belt.w / 2]) smp.push([...W(x, z), y, y + (x > belt.xe - belt.railGap ? belt.thick : belt.h), 0.1, x > belt.xe - 1.0, true]); } } // (no rails on the end section)
      for (const [x, z, lo, hi, mg, closure, isBelt] of smp) {
        const dx = x - n2[0], dz = z - n2[1]; const ax = -(dx * f2[0] + dz * f2[1]), ay = dx * r2[0] + dz * r2[1];
        // (the conveyor against the rendered, pitched skin; everything else also against the ellipse: acHit ell)
        const h = acHit(T, ax, ay, lo, hi, closure ? 0 : mg, isBelt ? 'skin' : 'both'); if (h && !(closure && h === 'fus')) return no('own ' + h);
        for (const o of this.keepOut) if (o.gate !== g && hitsAircraft(o, [x, z], hi)) return no('other aircraft');
        if (inBuilding(x, z)) return no('building');
      }
      // the conveyor's end face (its last 1.0 m may touch the fuselage above: the sill) must itself stay outside the
      // rendered skin - corners and between, bottom to top edge (close-out round 5, c4 F3: none of it was tested)
      if (belt && belt.end) { const xb = belt.x0 + belt.len * Math.cos(belt.th), yb = belt.y0 + belt.len * Math.sin(belt.th);
        for (const t of [0, 0.5, 1]) { const ex = xb - t * belt.thick * Math.sin(belt.th), ey = yb + t * belt.thick * Math.cos(belt.th);
          for (const z of [-0.5, -0.25, 0, 0.25, 0.5]) { const [x, zz] = W(ex, z * belt.w); const dx = x - n2[0], dz = zz - n2[1];
            if (acHit(T, -(dx * f2[0] + dz * f2[1]), dx * r2[0] + dz * r2[1], ey, ey, 0, 'skin') === 'fus') return no('own fus (conveyor end)'); } } }
      const hb = boxes.map(([x0, x1, z0, z1, y0, y1]) => { const c = W((x0 + x1) / 2, (z0 + z1) / 2); return { c, u: [v.d[0], v.d[2]], hl: (x1 - x0) / 2, hw: (z1 - z0) / 2, lo: G + y0, hi: G + y1 }; });
      if (belt) { const xm = belt.x0 + belt.len * Math.cos(belt.th) / 2; hb.push({ c: W(xm, 0), u: [v.d[0], v.d[2]], hl: belt.len * Math.cos(belt.th) / 2, hw: belt.w / 2, lo: G + belt.y0, hi: G + belt.y0 + belt.len * Math.sin(belt.th) + belt.h }); }
      for (const vb of hb) { for (const s of solids) if (s.lo < vb.hi + 0.3 && s.hi > vb.lo && solidOverlap(vb, s, 0.5)) return no('bridge ' + s.part); for (const o of placed) if (solidOverlap(vb, o, 0.3)) return no('vehicle'); }
      for (const vb of hb) placed.push(vb); return true;
    };
    const tint = () => { const cs = [[0.95, 0.95, 0.95], [0.9, 0.75, 0.1], [0.15, 0.3, 0.6], [0.85, 0.3, 0.1], [0.4, 0.42, 0.45]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    const B = this.vehicleBuckets;
    const HULL = { tug: [[-1.4, 1.4, -0.92, 0.92, 0, 2.1]], cart: [[-1.5, 1.5, -0.85, 0.85, 0, 1.6]], fuel: [[-3.8, 4.55, -1.3, 1.3, 0, 3.2]], gpu: [[-1.2, 1.2, -0.7, 0.7, 0, 1.5]], cone: [[-0.22, 0.22, -0.22, 0.22, 0, 0.75]] };
    const put = (bucket, v, color, hull = HULL[bucket]) => { if (ok(v, hull, null, bucket)) { B[bucket].push(inst(v.M, color || tint())); return true; } return false; };
    // the mesh of a lift setting (js/world/gates.js vehicleSettings: one per conveyor top / catering box floor, built for
    // the fitted types at start-up); a type re-seated later (fit.js seatType) takes the nearest one: [key, value]
    const setting = (pre, val) => { let best = null, bd = 1e9; for (const k in B) if (k.startsWith(pre) && /^\d+$/.test(k.slice(pre.length))) { const x = +k.slice(pre.length) / 100, d = Math.abs(x - val); if (d < bd) { bd = d; best = [k, x]; } } return best; };
    const fuse = T.R + 0.4;
    // (aftCargo: where the baggage train starts, behind the wing on the right, starboard, side; the belt loaders take the
    // cargo doors themselves from beltDoor)
    const fwdCargo = T.L * 0.22, aftCargo = T.L * 0.66;
    const cartCol = () => { const cs = [[0.34, 0.37, 0.4], [0.16, 0.24, 0.42], [0.2, 0.3, 0.24], [0.55, 0.56, 0.57]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    const tugCol = () => { const cs = [[0.9, 0.72, 0.1], [0.92, 0.92, 0.9], [0.12, 0.2, 0.42]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    // belt loaders (narrow bodies with sourced lower-deck sills: Boeing 737 and Airbus A320 families; the wide bodies'
    // holds are container-loaded and not modelled): per cargo door (js/world/gates.js beltDoor: the fitted model's own
    // cargo door - station and rendered sill - or the published station / sill, never under the rendered keel), the
    // conveyor's top end on that sill against the RENDERED starboard skin (beltEndY: skin half width at the sill + 0.03 m;
    // close-out round 3 bridges-3 - the unpitched ellipse had put it 0.29-0.36 m below a 737 MAX's forward belly and up to
    // 0.88 m off the 737 NG's aft door), the vehicle angled 18 deg off square with its low end away from the wing
    const tk = this.typeKeyOf(T); const fam = beltFamily(tk);
    if (fam) {
      for (const [pr, sgn, door] of [[0.85, -1, 'fwd'], [0.6, 1, 'aft']]) { if (R() >= pr) continue;
        const D = beltDoor(T, fam, door); if (!D) continue; const X = D.X;
        const st = setting('belt', D.S); if (!st) continue; const [bk, S] = st; const sh = beltShape(S);
        const belt = { x0: sh.x0, y0: sh.y0, len: sh.len, th: sh.th, w: sh.w, h: sh.thick + 0.25, thick: sh.thick, railGap: BELT_RAIL_GAP, xe: sh.xe, end: true };
        const boxes = [[-2.5, 2.4, -1.05, 1.05, 0, sh.chassisTop], [-2.55, -1.2, -1.08, -0.5, 0, sh.cabTop]];
        for (const yaw of [72, 90, 60]) { const c = sgn * Math.cos(yaw * DEG), sn = -Math.sin(yaw * DEG); const d = v3.norm(v3.add(v3.mul(f, c), v3.mul(r, sn)));
          // (the end face's corners at this yaw - station aft and outboard of its centre: beltEndY keeps the whole top edge
          // 0.03 m off the rendered skin; close-out round 5, aircraft verifier c4 F3: by the centre line alone a corner went
          // 0.04-0.12 m into the closed cargo door where the keel rises aft)
          const rl = v3.norm(v3.cross(d, [0, 1, 0])); const yEnd = beltEndY(T, X, S, [-v3.dot(rl, f) * sh.w / 2, v3.dot(rl, r) * sh.w / 2]);
          const e = v3.add(v3.sub(nose, v3.mul(f, X)), v3.mul(r, yEnd)); const p = v3.sub(e, v3.mul(d, sh.xe));
          const v = { M: m4.basis(d, [0, 1, 0], [p[0], G, p[2]]), p, d }; if (ok(v, boxes, belt, bk)) { B[bk].push(inst(v.M, tint())); break; } } } }
    // baggage train alongside the aft fuselage behind the wing, tug facing forward, carts trailing
    // (beside the aft belt loader's low end, or further out where that is in the way)
    if (R() < 0.75) { const tc = tugCol(), cc = [cartCol(), cartCol(), cartCol()]; const a0 = aftCargo + 2.5;
      for (const y of [fuse + 6.8, fuse + 10.5]) if (put('tug', at(a0, y, 0), tc)) { for (let i = 0; i < 3; i++) put('cart', at(a0 + 3.4 + i * 3.4, y, 0), cc[i]); break; } }
    // (catering truck square to the door, its front 0.7 m off the fuselage side: the mesh reaches 4.55 m ahead of its origin)
    // (its box lifted to the door's floor: cateringFloor; the hull is the chassis, cab, column and the lifted box)
    if (R() < 0.45 && T.doors[1] != null) { const F = cateringFloor(T); const st = F != null && setting('catering', F); if (st) put(st[0], at(T.doors[1] + 1, fuse + 4.85, -Math.PI / 2), [0.95, 0.95, 0.95, 1], cateringBoxes(st[1])); }
    if (R() < 0.35 && T.eng.length) put('fuel', at(T.xMain - 5, T.eng[T.eng.length - 1].z + 7.5, 0), [0.85, 0.85, 0.85, 1]);
    if (R() < 0.6) put('gpu', at(3.5, fuse + 3.4, 0.3));
    const span = T.wing ? T.wing.span / 2 : 18;
    for (const [a, s] of [[-2.5, 0], [T.wing ? T.wing.rootLE + (span) * Math.tan((T.wing.sweep || 25) * Math.PI / 180) + 1 : T.L * 0.5, span + 1.2], [T.wing ? T.wing.rootLE + span * Math.tan((T.wing.sweep || 25) * Math.PI / 180) + 1 : T.L * 0.5, -(span + 1.2)], [T.L + 2, 0]]) { const v = at(a, s); if (ok(v, HULL.cone)) B.cone.push(inst(v.M)); }
  }
  typeKeyOf(T) { if (!this._tk) { this._tk = new Map(); for (const [k, t] of Object.entries(TYPES)) if (t) this._tk.set(t, k); } return this._tk.get(T) || ''; }
}

// exact plan intersection area of two oriented boxes ({c, u, hl, hw}): A clipped by B's four half-planes (Sutherland-Hodgman)
function obbArea(A, B) {
  const corners = (S) => { const v = [-S.u[1], S.u[0]]; return [[1, 1], [-1, 1], [-1, -1], [1, -1]].map(([i, j]) => [S.c[0] + S.u[0] * S.hl * i + v[0] * S.hw * j, S.c[1] + S.u[1] * S.hl * i + v[1] * S.hw * j]); };
  let P = corners(A); const v = [-B.u[1], B.u[0]];
  for (const [n, h] of [[B.u, B.hl], [[-B.u[0], -B.u[1]], B.hl], [v, B.hw], [[-v[0], -v[1]], B.hw]]) {
    const dist = (p) => h - ((p[0] - B.c[0]) * n[0] + (p[1] - B.c[1]) * n[1]); const Q = [];
    for (let i = 0; i < P.length; i++) { const p = P[i], q = P[(i + 1) % P.length]; const dp = dist(p), dq = dist(q);
      if (dp >= 0) Q.push(p); if ((dp >= 0) !== (dq >= 0)) { const t = dp / (dp - dq); Q.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]); } }
    P = Q; if (P.length < 3) return 0; }
  let a = 0; for (let i = 0; i < P.length; i++) { const p = P[i], q = P[(i + 1) % P.length]; a += p[0] * q[1] - q[0] * p[1]; } return Math.abs(a) / 2;
}
// plan overlap of two solids, circles (`round`) handled exactly
export function solidOverlap(a, b, cl = 0) {
  const cb = (c, r, B) => { const d = [c[0] - B.c[0], c[1] - B.c[1]]; const x = d[0] * B.u[0] + d[1] * B.u[1], y = -d[0] * B.u[1] + d[1] * B.u[0]; return Math.hypot(Math.max(0, Math.abs(x) - B.hl), Math.max(0, Math.abs(y) - B.hw)) < r + cl; };
  if (a.round && b.round) return Math.hypot(a.c[0] - b.c[0], a.c[1] - b.c[1]) < a.round + b.round + cl;
  if (a.round) return cb(a.c, a.round, b); if (b.round) return cb(b.c, b.round, a); return obbOverlap(a, b, cl);
}
// separating-axis overlap of two oriented boxes in plan ({c, u, hl, hw}; `round` boxes as squares), with clearance cl
export function obbOverlap(A, B, cl = 0) {
  const ax = [A.u, [-A.u[1], A.u[0]]], bx = [B.u, [-B.u[1], B.u[0]]];
  const d = [B.c[0] - A.c[0], B.c[1] - A.c[1]];
  for (const n of [...ax, ...bx]) {
    const ra = A.hl * Math.abs(A.u[0] * n[0] + A.u[1] * n[1]) + A.hw * Math.abs(-A.u[1] * n[0] + A.u[0] * n[1]);
    const rb = B.hl * Math.abs(B.u[0] * n[0] + B.u[1] * n[1]) + B.hw * Math.abs(-B.u[1] * n[0] + B.u[0] * n[1]);
    if (Math.abs(d[0] * n[0] + d[1] * n[1]) > ra + rb + cl) return false;
  }
  return true;
}

// ---------------------------------------------------------------- aircraft footprints for collision tests
export function footprint(nose, f, T, gate = null) { return { nose: [nose[0], nose[2]], f: [f[0], f[2]], r: [-f[2], f[0]], T, gate }; }
export function hitsAircraft(fp, q, tall) {
  const dx = q[0] - fp.nose[0], dz = q[1] - fp.nose[1];
  const x = -(dx * fp.f[0] + dz * fp.f[1]); // metres behind the nose
  const y = dx * fp.r[0] + dz * fp.r[1];      // metres to the right
  const T = fp.T;
  if (x > -1 && x < T.L + 1 && Math.abs(y) < T.R + 0.6) return true;                       // fuselage
  const w = T.wing;
  if (w) {
    const ay = Math.abs(y); const le = w.rootLE + ay * Math.tan((w.sweep || 25) * Math.PI / 180);
    const chord = w.rootC - (w.rootC - w.tipC) * Math.min(1, ay / (w.span / 2));
    if (ay < w.span / 2 + 0.5 && x > le - 0.5 && x < le + chord + 0.5 && tall > 2.2) return true;  // under the wing only if low enough
  }
  for (const e of T.eng || []) for (const sg of [-1, 1]) {
    const ex = (w ? w.rootLE + Math.abs(e.z) * Math.tan((w.sweep || 25) * Math.PI / 180) : T.L * 0.4) - (e.fwd || 3);
    if (Math.abs(y - sg * e.z) < e.r + 0.8 && x > ex - 1.5 && x < ex + e.len + 1.5) return true;
  }
  if (T.rear && x > T.rear.x - 1 && x < T.rear.x + T.rear.len + 1 && Math.abs(y) < T.rear.z + T.rear.r + 0.8 && tall > 2.5) return true;
  if (T.hstab && x > T.hstab.x - 1 && x < T.L + 1 && Math.abs(y) < T.hstab.span / 2 + 0.5 && tall > 4.5) return true;
  return false;
}

// ---------------------------------------------------------------- sign geometry (sign program: pos, nrm, uv, extra)
function newSignGeo() { return { pos: [], nrm: [], uv: [], ext: [], idx: [] }; }
function signQuad(s, q, n, r, lit) {
  const b = s.pos.length / 3; for (const p of q) s.pos.push(p[0], p[1], p[2]);
  for (let i = 0; i < 4; i++) { s.nrm.push(n[0], n[1], n[2]); s.ext.push(lit ? 1 : 0, 0, 0, 0); }
  s.uv.push(r.u0, r.v1, r.u1, r.v1, r.u1, r.v0, r.u0, r.v0); s.idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
}
function meshOf(g) { return new Mesh(g.data()); }
function meshOfSign(s) { return new Mesh({ pos: new Float32Array(s.pos), nrm: new Float32Array(s.nrm), uv: new Float32Array(s.uv), extra: new Float32Array(s.ext), idx: new Uint32Array(s.idx) }); }
