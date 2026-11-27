// forked from sfo3d@e3218d6 js/live/gates.js
// SHA Live 3D (ZSSS): contact-stand equipment - apron-drive jet bridges, VDGS, stand-number signs - and ground service
// equipment around parked aircraft, driven by stand occupancy. The sfo3d engine is kept: bridge kinematics from the
// Oshkosh AeroTech sell sheet, docking paths tested against the aircraft and the fixed parts, oriented-box solids, rest
// poses per occupant, VDGS placement clear of every bridge pose, GSE hull tests. Changes for sha3d (arch.md R4, PLAN §4):
//  - NO module-scope data. Stands come in as gate objects (js/live/gates.js shaGates(window.SHA_STANDS)); the terminal
//    outlines, their wall tops, the apron lanes and the pavement test come in through setGateWorld() (the OSM T1 / T2
//    rings of window.SHA_AIRPORT, the taxi graph of window.SHA_TAXIGRAPH). sfo3d's SFO Museum clearance rings, sky
//    bridges and 3-D asset tiers do not exist here: those indexes are empty (inAsset / solidInAsset always miss).
//  - World coordinates throughout: g.nose, g.dir and every bridge point are world [x, z] (sfo3d: the SFO s,t grid);
//    stW / stD are the identity (x east, z south).
//  - Bridge model and rest pose are not in the SHA data: autoModel() picks the sell-sheet model covering the docked
//    extensions of the stand's accepted types (weighted: class reference, common SHA types, others), the shortest-
//    retracting among equals; a bridge without a data rest pose (all of them) rests fully retracted towards the class
//    reference's door 1, turned (up to 80 deg) / extended (up to 3 m) where that pose meets the stand's accepted aircraft
//    (3.75 m: MH 5001-2021 table 4.13.5 note a), the neighbours' aircraft (0.5 m), the fixed parts or the buildings
//    (autoRest in finishPrep). The Oshkosh AT2 / AT3 table stays as an INF PLACEHOLDER: the bridge make at ZSSS is unknown.
//  - The rotunda floor is fitted to the common SHA types' door sills (SHA_MAIN) where the bridge docks any of them.
//  - Departure level per terminal (DEPARTURE_LEVELS, inf); the cab sense CW = sfo3d's inferred sense unless the data has
//    a cab_convention; the class reference airframes (REF_TYPE) are the SHA class references where a model exists.
//  - Signs: js/live/gate_signs.js atlas (CAAC MH 5001-2021 8.5 stand-number sign: yellow face, black numerals, internally
//    lit) above the VDGS display (8.5.3: on the stand centreline extension) and as a bridge-mounted triangular prism on the
//    rotunda roof (8.5.2 / 8.5.8: on the bridge's fixed end; replaces sfo3d's FAA-style gate numbers on the tunnel); remote
//    stands and the alternative positions get a post-mounted stand-number sign (remoteGeo; photos 17 / 09 / 14 of
//    docs/phase1/photos_credits.md show yellow boards with black digits at ZSSS).
//  - Remote stands (no bridge): self-propelled passenger stairs at the doors and an apron bus beside a parked aircraft,
//    an idle stair unit at the stand head as a cue (all inf; js/world/gates.js stairDoors / stairShape / BUS_HULL), plus
//    sfo3d's GSE set (belt loaders, baggage train, catering, fuel, GPU, cones), every hull tested as in sfo3d.
//  - The US references below (FAA AC 150/5220-21C slopes and sizes, 36 CFR 1191 ramps) are aircraft-boarding-equipment
//    design values carried from the donor as inf placeholders; no FAA marking / sign / lighting constant is used here.
// The donor's header follows unchanged (its SFO stand / pier notes describe sfo3d, not ZSSS).
//
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
import { GROUND_Y } from '../geo.js';
import { TYPES, ICAO_TYPES } from '../aircraft/types.js';
import '../aircraft/fit.js'; // fits the imported models to the published dimensions: T.dockX1/2, T.dockSill/2, T.dockHW
import { bellowsShape, bellowsGeo } from '../aircraft/dock.js'; // the bellows closure fitted to the drawn fuselage skin
import { inst, buildVehicleMeshes, beltShape, beltFamily, beltDoor, beltEndY, BELT_RAIL_GAP, cateringFloor, cateringBoxes, stairShape, stairHull, stairDoors, BUS_HULL } from '../world/gates.js';
import { makeGateAtlas } from './gate_signs.js';
import { MODEL_DIMS, MODEL_FEATURES } from '../../data/models/manifest.js'; // (sfo3d model metadata: nose-gear contact)
import { CAAC, val } from './caac_markings.js'; // the ONE CAAC parameter table (table 4.9.5 separations for the masts)
// ---- stand stop convention (sha3d fix round 1, review M5). The stand's stop point g.nose (data `nose`, the OSM
// aeroway=parking_position node, where the painted stop line is drawn) is the NOSE-WHEEL stop of every type:
//  - CAAC MH 5001-2021 6.2.16-7: with manual or equipment guidance the stop line is set at the nose-wheel position of the
//    intended stop point, square to the alignment line (without guidance: at the left-seat pilot). Every ZSSS stand has
//    guidance (VDGS or marshaller, AIP (mirror) AD 2.20 3.2.2.3);
//  - OSM tagging of aeroway=parking_position: "Put a node where the nose wheel stops"; the last node of the way "where
//    the nose wheel is parked" (OSM wiki).
// A type T therefore parks with its nose-gear contact on the node and its nose tip noseGearX(T) metres AHEAD of it: the
// drawn model's own nose-gear contact (sfo3d model metadata MODEL_FEATURES[m].contact, through the fitted station map
// T.fit.rx) for the models standing on their own gear, else the published nose-gear station T.xNose (js/aircraft/types.js,
// where the procedural gear is drawn). The engine's "nose" is the nose tip throughout (doors, footprints, clearances);
// standTip(g, T) converts. Phase 3 traffic parks the same way: setOccupant(g, key, ..., {nose: standTip(g, T), dir}).
// (sfo3d's per-family type_stops do not exist for ZSSS: familyOf is null, the nose-gear offset replaces them.)
const familyOf = () => null;
const _ngx = new Map();
export function noseGearX(T, modelKey) {
  if (!T) return 0;
  const f = T.fit; const ck = (T.key || '') + '|' + (modelKey === undefined ? '*' : modelKey || '-');
  if (_ngx.has(ck) && _ngx.get(ck).fit === f) return _ngx.get(ck).x;
  let x = Number.isFinite(T.xNose) ? T.xNose : (T.gear && T.gear.nose ? T.gear.nose.x : 0);
  const m = f && f.model; const C = m && MODEL_FEATURES[m] && MODEL_FEATURES[m].contact;
  if (C && C.nose && typeof f.rx === 'function' && MODEL_DIMS[m] && MODEL_DIMS[m].hasGear && (modelKey === undefined || modelKey === m)) x = f.rx(C.nose.st);
  x = +x.toFixed(3); _ngx.set(ck, { fit: f, x }); return x;
}
// the nose tip [x, y, z] of type T parked at stand s (its nose wheel on the stop node, heading s.dir)
export function standTip(s, T, modelKey) { const f = [s.dir[0], 0, s.dir[1]]; const L = Math.hypot(f[0], f[2]) || 1; const x = noseGearX(T, modelKey); return [s.nose[0] + f[0] / L * x, GROUND_Y, s.nose[1] + f[2] / L * x]; }

// terminal outlines the bridges must stay out of (sha3d: injected by setGateWorld - the OSM T1 / T2 outlines of
// window.SHA_AIRPORT, the same rings the stand builder took the bridge attach points from; BLD_H = wall top above the
// apron, inf). No clearance-only rings (sfo3d's SFO Museum outlines) and no sky bridges: NCL = NBLD = BLD.length.
let BLD = [], BLD_H = [], NBLD = 0, NCL = 0, BLD_BB = [], SKY_Y = [];
// edge index of every outline (exact tests, no sampling): EC m grid cells -> [ring k, ax, az, bx, bz]; per ring, its
// edges in EZ m bands of z (point-in-ring tests only cross the band's edges)
const EC = 8, EZ = 4; let ECELL = new Map(), EBAND = [];
// apron lanes (taxiway / taxilane centrelines of the taxi graph, without stand lead-ins: [[x0, z0, x1, z1, halfClear]])
// and the pavement test (world.pavedAt) for the remote-stand equipment placement (sha3d)
let LANES = [], PAVED = null;
export function setGateWorld({ outlines = [], lanes = [], pavedAt = null, cabConvention = null } = {}) {
  BLD = []; BLD_H = []; for (const o of outlines) { if (o && o.ring && o.ring.length >= 3) { BLD.push(o.ring); BLD_H.push(o.h ?? 10); } }
  NBLD = NCL = BLD.length; SKY_Y = [];
  BLD_BB = BLD.map(r => { let a = 1e9, b = 1e9, c = -1e9, d = -1e9; for (const p of r) { a = Math.min(a, p[0]); c = Math.max(c, p[0]); b = Math.min(b, p[1]); d = Math.max(d, p[1]); } return [a, b, c, d]; });
  ECELL = new Map(); EBAND = BLD.map(() => new Map());
  BLD.forEach((r, k) => { for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[j], b = r[i]; const e = [k, a[0], a[1], b[0], b[1]];
    for (let cx = Math.floor(Math.min(a[0], b[0]) / EC); cx <= Math.floor(Math.max(a[0], b[0]) / EC); cx++) for (let cz = Math.floor(Math.min(a[1], b[1]) / EC); cz <= Math.floor(Math.max(a[1], b[1]) / EC); cz++) { const key = cx * 65536 + cz; let L = ECELL.get(key); if (!L) ECELL.set(key, L = []); L.push(e); }
    for (let bz = Math.floor(Math.min(a[1], b[1]) / EZ); bz <= Math.floor(Math.max(a[1], b[1]) / EZ); bz++) { let L = EBAND[k].get(bz); if (!L) EBAND[k].set(bz, L = []); L.push(e); } } });
  LANES = lanes || []; PAVED = pavedAt || null;
  CW = (cabConvention && /^clockwise/.test(cabConvention.cw_is || '')) ? 1 : -1;
}
// distance from (x, z) to the nearest apron lane, less that lane's half clearance (<0: on it); 1e9 when none is near
function laneClear(x, z) { let d = 1e9; for (const L of LANES) { if (Math.min(L[0], L[2]) > x + 40 || Math.max(L[0], L[2]) < x - 40 || Math.min(L[1], L[3]) > z + 40 || Math.max(L[1], L[3]) < z - 40) continue;
  const ex = L[2] - L[0], ez = L[3] - L[1]; const t = clampN(((x - L[0]) * ex + (z - L[1]) * ez) / (ex * ex + ez * ez || 1), 0, 1); d = Math.min(d, Math.hypot(L[0] + ex * t - x, L[1] + ez * t - z) - L[4]); } return d; }
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
// (sha3d: SKY_Y is set by setGateWorld - empty, no sky bridges)
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
// sha3d: no 3-D building assets (sfo3d B3D_INTEGRATION footprints / tiers): nothing to reach or to enter
function inAsset() { return false; }
function solidInAsset() { return null; }
// top of the terminal wall the point (x, z) lies in (0: none) - js/live/terminals.js: complex 0-5 m, parts 5 m - h
function wallTop(x, z) { let h = 0; for (let i = 0; i < NBLD; i++) { const bb = BLD_BB[i]; if (x < bb[0] || x > bb[2] || z < bb[1] || z > bb[3]) continue; if (inRingK(x, z, i)) h = Math.max(h, BLD_H[i]); } return h; }

const G = GROUND_Y;
// sha3d: gate points are world [x, z] already (sfo3d: SFO s,t grid) - identity maps keep the donor's call sites
const stW = (p, h = 0) => [p[0], h, p[1]];
const stD = (d) => v3.norm([d[0], 0, d[1]]);
const worldToST = (x, z) => [x, z];
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
const SLOPE_TARGET = 1 / 12, SLOPE_MAX = 1 / 4;           // AC 150/5220-21C Figure 6 (unassisted / assisted), §3.4.b(6) (sha3d: inf placeholder - US boarding-equipment design values, no CAAC value transcribed)
// floor of the fixed walkway where it leaves the building (the terminal's bridge level), m above the apron, per terminal
// (g.terminal), and the steepest the fixed walkway may slope (slope; default 1:12). sha3d: no published level.
//  T1 4.5 m [inf]: the T1 airside concourse roof reads 8.9 m (7.3-10.8) on photo 02 (docs/phase1/standards_refs.md §3.4),
//     so 4.5 m leaves the 3.0 m walkway (WALK_H) under it; 1:12 as sfo3d
//  T2 5.0 m, near level (1:60) [obs-low]: photo 09 (T2 airside, 2013) shows the long glazed fixed links running level, one
//     storey up, over the apron service road and its vehicles to the rotundas (eye estimate of the clearance, ~4.5 m)
const DEPARTURE_LEVEL = 4.5;                              // m, the default (inferred)
export const DEPARTURE_LEVELS = {
  T1: { h: 4.5, tag: 'inf', src: 'one storey over the apron, under the 8.9 m T1 concourse roof (photo 02 ratio, standards_refs.md 3.4); no published level' },
  T2: { h: 5.0, slope: 1 / 60, tag: 'obs-low', src: 'photo 09 (T2 airside, 2013): level glazed fixed links one storey up over the service road (clearance ~4.5 m, eye estimate); no published level' },
};
const departureLevel = (g) => DEPARTURE_LEVELS[g && g.terminal] || { h: DEPARTURE_LEVEL, tag: 'inf', src: 'default' };
const OVERLAP = 1.0, STAGGER = 0.3;                       // m, minimum tunnel overlap at full extension / retracted stagger (inferred)
// sign convention of the sheet's "cw" in the data (data/sfo_stands.json cab_convention, inferred by the stand builder)
// (sha3d: the SHA data has no cab_convention - sfo3d's inferred sense, 'counter-clockwise seen from above', stays: CW -1;
// setGateWorld({cabConvention}) takes a data block when one exists)
let CW = -1;
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
// (sha3d: CAAC MH 5001-2021 4.13.5, table 4.13.5 gives the same minimum clearances by code letter: A / B 3.0, C 4.5,
// D-F 7.5 m; the code letter is taken from the span as here)
const icaoClear = (span) => span < 24 ? 3.0 : span < 36 ? 4.5 : 7.5;
// (sha3d fix round 1) apron floodlight masts (review M2) and idle airstair staging (review L4) - all inferred:
const MAST_H = 30.0;            // m, mast height to the lamp head (inf: photos 02 / 09 / 14 show 25-35 m masts)
const MAST_SPACING = 80.0;      // m, at least between masts (inf: about one per two stands at the 38-45 m T2 stand spacing)
const MAST_BRIDGE_CLEAR = 6.0;  // m, from any jet-bridge tunnel axis (rest pose and every docking path) (inf)
const MAST_CAM_STRICT_REMOTE = false; // (fix round 2, N1) false: a remote stand keeps one stand-camera side clear, not side +1 (inf)
// (fix round 3, review_visual_fix2.md V2 / V4) a side of a stand camera is clear when no mast is in its subject / centre
// margins (standCamPos) AND none is in its near field (standCamNear). MAST_CAM_CONTACT 'side1': a contact stand keeps
// side +1 (the bridge side) clear; 'either': one side, as a remote stand (inf)
const MAST_CAM_CONTACT = 'side1';
const MAST_EQUIP_CLEAR = 2.0;   // m, the base plate clear of every painted equipment area (6.2.20 设备区) by at least this (inf)
// m, the base plate (1.6 m square) and the pavement margin around it: the review's 1 m (V4) plus 1 m for the ground map's
// CPU copy (pavedAt reads 2 m cells, so a corner 1-2 m inside the drawn edge can read < 0.5 there) (inf)
const MAST_PLATE_HALF = 0.8, MAST_PAVE_MARGIN = 2.0;
const MAST_GAP_R = 120;         // m, a stand "has a mast nearby" within this of its stop node (coverage, gap fill) (inf)
// the gap fill's polar grid about the stop node: radii r0 .. r1 by dr m, every da deg (inf; fix round 3: [24, 108, 12, 15];
// fix round 4: finer, so that the stands the 55 m near field and the Tower view leave without a mast get one again)
const MAST_GAP_GRID = [18, 114, 6, 7.5];
// (fix round 4, review_visual_fix3.md F4) m, the base plate clear of every painted stand envelope (the red safety line,
// SHA.markings.apron().envelopes) by at least this, as for the equipment areas: the foot >= 2 + 0.8 x sqrt 2 = 3.13 m from
// the line (the gap-fill mast "289" stood 1.18 m from the 290 line, its plate 0.4 m from it) (inf)
const MAST_ENV_CLEAR = 2.0;
// (fix round 4 verification, review F3-gapfill-frames-subject / NAMED-231-mast) the gap fill took the NEAREST candidate that
// passed every rule, so its masts stood 55-70 m in front of the stand cameras (268: 69 m left of the nose, 259: 58 m in its
// own view, heads 56-67 px at 1440 x 900). Now it ranks its candidates by the largest lamp head they show in any stand's
// "Fly to stand" camera (contact stands side +1, remote stands the side they take) and in the Tower view: candidates whose
// head stays under MAST_GAP_HEAD in all of them are equal (nearest first, as before), the others follow by ascending head
// size. MAST_GAP_HEAD = tan 3.0 deg of a 4.4 m head (headR x 2): depth >= 84 m, < 40 px at 1280 x 720 and < 50 px at
// 1440 x 900 with the 50 deg field (the gates job's "middle distance" band starts at 40 px at 1280 x 720); in the Tower view
// the same rank uses TOWER_CAM.headDeg (1.0 deg). MAST_GAP_SUBJ 2: a candidate closer than 2 x the subject margin
// (standCamPos d < 2, i.e. within 8 deg of the stand's subject) in one of those cameras ranks as if its head were 2 / d
// times the limit (the pole beside the parked aircraft; dry passes, out/fix4/v1: gap-fill heads >= 60 px at 1440 x 900
// 10 -> 5 stands, contact 5 -> 1; the "323" mast in its own view 62 -> 50 px). inf.
const MAST_GAP_HEAD = Math.tan(3.0 * DEG), MAST_GAP_SUBJ = 2;
// (sha3d fix round 2, review N1) the app's own stand camera, defined once here: js/live/shell.js flyToStand ("Fly to
// stand") and the named stand views (app.js SHA.qa.stand, side +1) look from ahead-left of the stand (side +1 = the
// aircraft's left, the bridge side; side -1 = its right) back at a target `back` m behind the stop node, horizontally along
// fwd * heading + left * side * (heading turned left), pitched `pitch` deg down, `dist` m away (`big` classes farther).
// A mast pole (0 .. poleH m) "stands in the camera" when, projected into that camera and not wholly behind the subject, it
// passes within subjDeg of the subject's image: the convex hull of the target, the stop node and (camSubject) the class
// reference parked there (nose tip, wing tips, tail) and the bridge rotundas and docked cabs, at the heights subjH; or when,
// in front of the target, it crosses the centre band +-centreDeg of the frame. A test in the image, not on the ground: the
// review's ground strip (+-12 m about the sight line) let a pole 14 m off the line at 248 stand right beside the nose (a
// tall pole near the camera sweeps across the subject). subjDeg 4 = about 55 px at 1280 x 720. All values inf (a UI camera
// choice, not an airfield parameter).
export const STAND_CAM = { back: 18, fwd: 0.75, left: 0.66, pitch: 24, fov: 50, dist: 90, distBig: 120, big: ['E', 'EL', 'F'],
  subjDeg: 4, centreDeg: 8, poleH: 31, subjH: { target: 3, node: 1, tip: 3, wing: 4, tail: 9, rotunda: 5, cab: 4 },
  nearDepth: 55, nearDist: 25, nearPoleMin: 10, headR: 2.2, headDy: -0.8, aspect: 16 / 9, src: 'inf' };   // (near*: fix round 3, V2; nearDepth 45 -> 55 m: fix round 4, F3; standCamNear)
/** the stand camera of a stand (stop node `nose` [x, z], heading vector `h` [x, z], class `cls`) on `side` (+1 / -1).
 *  `subj`: extra subject points {p: [x, z], y: height above the apron} (LiveGateSystem.camSubject). Returns {T: target
 *  [x, z], o: horizontal unit direction target -> camera, dist, side, cam (above the apron), F / R / U (camera basis),
 *  S: the subject points projected [X, Y, depth] (X, Y = tangent of the angle off the view axis), hull, zMax} */
export function standCamWedge(nose, h, cls, side = 1, subj = []) {
  const K = STAND_CAM; const hl = Math.hypot(h[0], h[1]) || 1; const f = [h[0] / hl, h[1] / hl], lf = [f[1], -f[0]];
  const T = [nose[0] - f[0] * K.back, nose[1] - f[1] * K.back];
  const off = [f[0] * K.fwd + lf[0] * K.left * side, f[1] * K.fwd + lf[1] * K.left * side]; const ol = Math.hypot(off[0], off[1]) || 1; const o = [off[0] / ol, off[1] / ol];
  const dist = K.big.includes(cls) ? K.distBig : K.dist; const cp = Math.cos(K.pitch * DEG), sp = Math.sin(K.pitch * DEG);
  const W = { T, o, dist, side, cam: [T[0] + o[0] * dist * cp, dist * sp, T[1] + o[1] * dist * cp], F: [-o[0] * cp, -sp, -o[1] * cp], R: [o[1], 0, -o[0]] };
  W.U = [W.R[1] * W.F[2] - W.R[2] * W.F[1], W.R[2] * W.F[0] - W.R[0] * W.F[2], W.R[0] * W.F[1] - W.R[1] * W.F[0]];
  const pts = [{ p: T, y: K.subjH.target }, { p: nose, y: K.subjH.node }].concat(subj.filter(q => q && q.p));
  W.S = pts.map(q => standCamProject(W, [q.p[0], q.y, q.p[1]])).filter(Boolean);
  W.hull = hull2(W.S); W.zMax = Math.max(...W.S.map(q => q[2]));
  return W;
}
/** camera-space projection of [x, y above the apron, z]: [X, Y, depth] or null behind the camera */
export function standCamProject(W, P) {
  const v = [P[0] - W.cam[0], P[1] - W.cam[1], P[2] - W.cam[2]]; const z = v[0] * W.F[0] + v[1] * W.F[1] + v[2] * W.F[2]; if (z < 0.5) return null;
  return [(v[0] * W.R[0] + v[1] * W.R[1] + v[2] * W.R[2]) / z, (v[0] * W.U[0] + v[1] * W.U[1] + v[2] * W.U[2]) / z, z];
}
const hull2 = (P) => { const p = P.map(q => [q[0], q[1]]).sort((a, b) => a[0] - b[0] || a[1] - b[1]); if (p.length < 3) return p;
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); const lo = [], up = [];
  for (const q of p) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
  return lo.slice(0, -1).concat(up.slice(0, -1)); };
const ptSeg2 = (q, a, b) => { const ex = b[0] - a[0], ey = b[1] - a[1]; const t = clampN(((q[0] - a[0]) * ex + (q[1] - a[1]) * ey) / (ex * ex + ey * ey || 1), 0, 1); return Math.hypot(a[0] + ex * t - q[0], a[1] + ey * t - q[1]); };
const segX2 = (a, b, c, d) => { const o = (p, q, r) => Math.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])); return o(a, b, c) * o(a, b, d) < 0 && o(c, d, a) * o(c, d, b) < 0; };
const inPoly2 = (q, H) => { let c = false; for (let i = 0, j = H.length - 1; i < H.length; j = i++) if (((H[i][1] > q[1]) !== (H[j][1] > q[1])) && (q[0] < (H[j][0] - H[i][0]) * (q[1] - H[i][1]) / (H[j][1] - H[i][1]) + H[i][0])) c = !c; return c; };
// distance (tangent units) from segment a-b to the convex polygon H (0: they overlap)
const segPoly2 = (a, b, H) => { if (!H.length) return Infinity; if (H.length === 1) return ptSeg2(H[0], a, b); if (H.length >= 3 && (inPoly2(a, H) || inPoly2(b, H))) return 0;
  let d = Infinity; for (let i = 0, j = H.length - 1; i < H.length; j = i++) { if (segX2(a, b, H[j], H[i])) return 0; d = Math.min(d, ptSeg2(a, H[j], H[i]), ptSeg2(b, H[j], H[i]), ptSeg2(H[i], a, b)); } return d; };
/** a mast pole at ground point q [x, z] in the stand camera W: d = its clearance as a fraction of the margins (the angle to
 *  the subject's image / subjDeg unless the pole is wholly behind the subject; in front of the target also the angle to the
 *  frame centre / centreDeg); in = d < 1 */
export function standCamPos(W, q) {
  const K = STAND_CAM; let A = [q[0], 0, q[1]], B = [q[0], K.poleH, q[1]];
  const zf = (A[0] - W.cam[0]) * W.F[0] + (A[1] - W.cam[1]) * W.F[1] + (A[2] - W.cam[2]) * W.F[2], zh = (B[0] - W.cam[0]) * W.F[0] + (B[1] - W.cam[1]) * W.F[1] + (B[2] - W.cam[2]) * W.F[2];
  if (zf < 0.5 && zh < 0.5) return { d: Infinity, in: false };
  if (zf < 0.5 || zh < 0.5) { const t = (0.5 - zf) / (zh - zf) + 1e-6; const M = [A[0], A[1] + (B[1] - A[1]) * t, A[2]]; if (zf < 0.5) A = M; else B = M; }
  const a = standCamProject(W, A), b = standCamProject(W, B); if (!a || !b) return { d: Infinity, in: false };
  let d = Infinity; const ts = Math.tan(K.subjDeg * DEG), tc = Math.tan(K.centreDeg * DEG), ty = W.tanY || Math.tan(K.fov / 2 * DEG);   // (W.tanY: the Tower view cameras, fix round 4)
  if (Math.min(zf, zh) < W.zMax) d = segPoly2(a, b, W.hull) / ts;
  const zT = W.S.length ? W.S[0][2] : Infinity;
  if (Math.min(zf, zh) < zT) { // in front of the target: the part of the pole inside the frame height, its nearest approach to the centre column
    const y0 = Math.max(-ty, Math.min(a[1], b[1])), y1 = Math.min(ty, Math.max(a[1], b[1]));
    if (y0 <= y1) { const xAt = (y) => Math.abs(b[1] - a[1]) < 1e-9 ? a[0] : a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]); const x0 = xAt(y0), x1 = xAt(y1);
      d = Math.min(d, (x0 * x1 <= 0 ? 0 : Math.min(Math.abs(x0), Math.abs(x1))) / tc); } }
  return { d, in: d < 1 };
}
/** the smallest clearance (standCamPos d) of mast poles at the ground points pts [[x, z], ...] (Infinity: none in view) */
export function standCamClearance(W, pts) { let m = Infinity; for (const p of pts) m = Math.min(m, standCamPos(W, p).d); return m; }
// (sha3d fix round 3, review_visual_fix2.md V2) the near field of a stand camera. The subject / centre test above lets a
// 30 m mast stand 10-39 m from the camera anywhere else in the frame, where its head is the largest object in the picture
// (238A: 10 m, 226 px; 264: 14 m; 270: 15 m). A mast is in the near field of camera W when
//  - its head (a sphere of STAND_CAM.headR about MAST_H - 0.8 m: the six-lamp head with its platform, 4.2 x 2.7 m) or
//    its pole above nearPoleMin m projects into the frame (vertical fov, width aspect x the height: the 16:9 laptop frame;
//    a portrait phone sees a narrower part of the same frame) at a depth under nearDepth m, or
//  - the pole (0 .. poleH m) comes within nearDist m (3-D) of the camera position (flying in, orbiting a little).
// All values inf (a UI camera choice). nearDepth was 45 m in fix round 3 (the review's figure: a 3 m head about 50 px);
// (fix round 4, review_visual_fix3.md F3) 55 m: past 45 m the 4.2 m wide head was still 60-72 px at 1280 x 720 and, beside
// the parked aircraft, framed the subject (274: the pole between the rotunda and the nose, head 71 px; 9 stands >= 60 px).
// At 55 m a head in the frame is <= ~59 px. (The review's alternative, a pole nearer than 60 m keeping 2 x subjDeg from the
// subject, was tried with it: no candidate it rejects survives the 55 m rule, so it is not kept.) The 4 extra uncovered
// stands this costs are recovered by the gap fill's finer grid (MAST_GAP_GRID).
// (fix round 4, F1) The same test serves the app's Tower view cameras (towerViewCams): their frame (W.tanX / W.tanY) and
// near depth (W.nearDepth 90 m) are per camera.
/** a mast at ground point q [x, z] (height h to the lamp head) in the near field of stand camera W: {near, why, depth, dist} */
export function standCamNear(W, q, h = 30) {
  const K = STAND_CAM; const c = W.cam; const ty = W.tanY || Math.tan(K.fov / 2 * DEG), tx = W.tanX || ty * K.aspect, ND = W.nearDepth || K.nearDepth;
  // 3-D distance camera -> pole segment
  const dy = c[1] > K.poleH ? c[1] - K.poleH : c[1] < 0 ? -c[1] : 0; const dist = Math.hypot(q[0] - c[0], dy, q[1] - c[2]);
  if (dist < K.nearDist) return { near: true, why: 'pole within ' + K.nearDist + ' m', depth: null, dist: +dist.toFixed(1) };
  // (a point in the frame at depth z is at most z * hypot(1, tx, ty) from the camera: farther poles cannot be in the near field)
  if (dist > Math.hypot(1, tx, ty) * (ND + K.headR) + 1) return { near: false, why: null, depth: null, dist: +dist.toFixed(1) };
  const depthOf = (y) => (q[0] - c[0]) * W.F[0] + (y - c[1]) * W.F[1] + (q[1] - c[2]) * W.F[2];
  // the head
  const yh = h + K.headDy, zh = depthOf(yh);
  if (zh > 0.5 && zh - K.headR < ND) { const P = standCamProject(W, [q[0], yh, q[1]]); const r = K.headR / zh;
    if (P && Math.abs(P[0]) < tx + r && Math.abs(P[1]) < ty + r) return { near: true, why: 'head in frame', depth: +zh.toFixed(1), dist: +dist.toFixed(1) }; }
  // a pole segment y0 .. y1 clipped to depths 0.6 .. zLim: [t0, t1] along it, or null
  const clipZ = (y0, y1, zLim) => { const z0 = depthOf(y0), z1 = depthOf(y1); let t0 = 0, t1 = 1;
    const clip = (za, zb, lim, lower) => { // keep the part with z >= lim (lower) or z <= lim
      if (Math.abs(zb - za) < 1e-9) return lower ? za >= lim : za <= lim; const t = (lim - za) / (zb - za);
      if (lower) { if (zb > za) t0 = Math.max(t0, t); else t1 = Math.min(t1, t); } else { if (zb > za) t1 = Math.min(t1, t); else t0 = Math.max(t0, t); } return t0 <= t1; };
    return clip(z0, z1, 0.6, true) && clip(z0, z1, zLim, false) ? { t0, t1, z0, z1 } : null; };
  // the pole above nearPoleMin, clipped to depths 0.5 .. nearDepth, against the frame rectangle (Liang-Barsky)
  const y0 = K.nearPoleMin, y1 = h; const C1 = clipZ(y0, y1, ND);
  if (C1) { const { t0, t1, z0, z1 } = C1;
    const A = standCamProject(W, [q[0], y0 + (y1 - y0) * t0, q[1]]), B = standCamProject(W, [q[0], y0 + (y1 - y0) * t1, q[1]]);
    if (A && B) { let u0 = 0, u1 = 1; const dx = B[0] - A[0], dyy = B[1] - A[1]; let ok = true;
      for (const [p, qq] of [[-dx, A[0] + tx], [dx, tx - A[0]], [-dyy, A[1] + ty], [dyy, ty - A[1]]]) { if (Math.abs(p) < 1e-12) { if (qq < 0) { ok = false; break; } continue; } const r = qq / p; if (p < 0) u0 = Math.max(u0, r); else u1 = Math.min(u1, r); if (u0 > u1) { ok = false; break; } }
      if (ok) return { near: true, why: 'pole above ' + y0 + ' m in frame', depth: +Math.min(z0 + (z1 - z0) * t0, z0 + (z1 - z0) * t1).toFixed(1), dist: +dist.toFixed(1) }; } }
  return { near: false, why: null, depth: null, dist: +dist.toFixed(1) };
}
/** the masts M [{p: [x, z], h, stand}, ...] in the near field of stand camera W (list of {stand, why, depth, dist}) */
/** the lamp head of a mast at ground point q [x, z] (head centre y m above the apron) in camera W: its width in tan units
 *  (2 x headR / depth) when its centre is in the frame (+ the head radius), else 0 (fix round 4 verification: gap-fill rank) */
export function standCamHead(W, q, y = MAST_H + STAND_CAM.headDy) {
  const K = STAND_CAM; const P = standCamProject(W, [q[0], y, q[1]]); if (!P) return 0; const r = K.headR / P[2];
  const ty = W.tanY || Math.tan(K.fov / 2 * DEG), tx = W.tanX || ty * K.aspect;
  return Math.abs(P[0]) < tx + r && Math.abs(P[1]) < ty + r ? 2 * K.headR / P[2] : 0;
}
export function standCamNearList(W, M) { const out = []; for (const m of M || []) { const p = m.p || m; const r = standCamNear(W, p, m.h || 30); if (r.near) out.push({ mast: m.stand || null, why: r.why, depth: r.depth, dist: r.dist }); } return out; }
// (fix round 4, review_visual_fix3.md F1) the app's Tower view (js/live/app.js view('tower'), the same formulas): the eye
// 0.5 m inside the glass of the cab face nearest to the view direction, at anchors.tower.eyeY, looking at the RWY 18L/36R
// midpoint; landscape (laptop): vertical field 46 deg, the frame's lower edge 1 deg below the cab terrace edge
// (terraceHalf / terraceY), pitch -11 .. -4 deg, width 16:9; portrait (phone): pitch -11 deg, vertical field 58-72 deg with
// a ~40 deg horizontal field - tested as one frame that holds every portrait phone of aspect 0.46-0.66 (tan of the half
// width 0.364 = tan 20 deg, half height 36 deg; iPhone 15 at 393 x 659: 62.8 deg; widened below). The mast placement keeps both clear of
// the near field (standCamNear with nearDepth 90 m, 250 m since the verification round: see below) and of the subject / centre
// band (standCamPos: the view target, i.e. the runway midpoint, and +-centreDeg in front of it). The review asked for about
// 70 m: that re-placed the T1 west face mast "115" at 79 m, still the largest object in the frame (45 px, lower left);
// at 90 m the gap fill puts it out of both frames (and covers 121 as well). jobs/gates.mjs checks the app's real camera
// against the masts (both framings). All inf (a UI camera choice).
// (fix round 4 verification, review F1-wide-aspect) app.js keeps the 46 deg vertical field on EVERY landscape aspect, so a
// wider window sees more to the sides (1920 x 970: 80 deg horizontal; iPhone 15 landscape 734 x 343: 84 deg); the 16:9 frame
// alone let the gap-fill mast "112" stand at 139 m, 38.5 deg off the axis, head 45 px at 1920 x 970. The landscape frame is
// now the widest one the app shows in practice, aspect 2.4 (21:9 monitors 2.33-2.39; every narrower landscape frame lies
// inside it, the pitch does not depend on the aspect), and the portrait frame the union of every portrait aspect
// 0.3-1 (half width tan 29 deg = tan(58 / 2) x 1 at aspect 1 - tablets, a narrow window -, half height 36 deg). The near
// field is stated as an angle: a mast head (4.2 m) in either frame must subtend < 1.0 deg (< 15 px at 1280 x 720,
// < 20 px at 1920 x 970, < 22 px at 1920 x 1080), i.e. nearDepth = 4.4 m / tan 1.0 deg = 250 m (was 90 m). All inf.
// Cost: the T1 west face stands 113, 114, 115 and 120 lose their mast within 120 m (MAST_GAP_R): every position the other
// rules leave for them is in the Tower frame 100-181 m from the eye (dry passes with nearDepth 90 / 120 / 150 / 200 m,
// out/fix4/v1/exp.mjs); they stay lit to the stand level by the light map's floors (fix round 3, V1).
export const TOWER_CAM = { nearDepth: 250, headDeg: 1.0, land: { fov: 46, aspect: 2.4 }, port: { fovMax: 72, tanX: Math.tan(29 * DEG), pitch: -11 }, src: 'inf' };
// (fix round 4, review_visual_fix3.md F7) a 32-bit FNV-1a hasher over numbers (to 0.01), strings, functions (their source
// text) and nested arrays / objects (keys sorted): the mast placement's inputs hash (placeMasts) and the pavement signature
// (js/live/gates.js vectorPavement)
export function fnvHash() {
  let h = 2166136261 >>> 0;
  const byte = (b) => { h ^= b & 255; h = Math.imul(h, 16777619) >>> 0; };
  const int = (v) => { v |= 0; byte(v); byte(v >>> 8); byte(v >>> 16); byte(v >>> 24); };
  const H = {
    num: (v) => { int(Number.isFinite(v) ? Math.round(v * 100) : -2147483647); return H; },
    str: (t) => { int(t.length); for (let i = 0; i < t.length; i++) { const c = t.charCodeAt(i); byte(c); if (c > 255) byte(c >>> 8); } return H; },
    any: (x) => { if (x == null) int(-1); else if (typeof x === 'number') H.num(x); else if (typeof x === 'string') H.str(x); else if (typeof x === 'boolean') int(x ? 1 : 0);
      else if (typeof x === 'function') H.str(x.toString()); else if (Array.isArray(x) || ArrayBuffer.isView(x)) { int(x.length); for (const v of x) H.any(v); }
      else { const k = Object.keys(x).sort(); int(k.length); for (const kk of k) { H.str(kk); H.any(x[kk]); } } return H; },
    hex: () => h.toString(16).padStart(8, '0') };
  return H;
}
/** the Tower view cameras [landscape, portrait] in the stand-camera form (cam above the apron, F / R / U, tanX / tanY,
 *  nearDepth, subject S / hull = the view target) from anchors.tower {pos, eyeY, cabHalf, cabYaw, terraceHalf, terraceY}
 *  and the runways [{id, a, b}]; [] without a tower anchor */
export function towerViewCams(tower, runways = []) {
  if (!tower || !tower.pos || tower.eyeY == null) return [];
  const G = tower.pos[1] || 0; const R0 = runways.find(r => /18L/.test(r.id || '')) || runways[0];
  const mid = R0 ? [(R0.a[0] + R0.b[0]) / 2, (R0.a[1] + R0.b[1]) / 2] : [0, 0];
  const yaw = (Math.atan2(mid[0] - tower.pos[0], -(mid[1] - tower.pos[2])) / DEG + 360) % 360;
  const fy = tower.cabYaw != null ? tower.cabYaw : yaw; const dA = ((((yaw - fy) % 90) + 135) % 90) - 45;
  const hv = [Math.sin(yaw * DEG), -Math.cos(yaw * DEG)], off = tower.cabHalf ? Math.max(0, tower.cabHalf - 0.5) / Math.cos(dA * DEG) : 0;
  const eye = [tower.pos[0] + hv[0] * off, tower.eyeY - G, tower.pos[2] + hv[1] * off];
  const K = TOWER_CAM; let pl = off ? -11 : -5;
  if (off && tower.terraceHalf && tower.terraceY != null) { const run = tower.terraceHalf / Math.cos(dA * DEG) - off, edge = Math.atan2(tower.eyeY - tower.terraceY, Math.max(0.5, run)) / DEG;
    pl = Math.min(-4, Math.max(-11, -(edge + 1 - K.land.fov / 2))); }
  const cam = (frame, pitch, tanY, tanX) => { const cp = Math.cos(pitch * DEG), sp = Math.sin(pitch * DEG);
    const W = { kind: 'tower', frame, cam: eye.slice(), F: [hv[0] * cp, sp, hv[1] * cp], R: [-hv[1], 0, hv[0]], tanX, tanY, nearDepth: K.nearDepth, yaw, pitch, side: 0 };
    W.U = [W.R[1] * W.F[2] - W.R[2] * W.F[1], W.R[2] * W.F[0] - W.R[0] * W.F[2], W.R[0] * W.F[1] - W.R[1] * W.F[0]];
    W.T = mid; W.S = [standCamProject(W, [mid[0], STAND_CAM.subjH.target, mid[1]])].filter(Boolean); W.hull = hull2(W.S); W.zMax = Math.max(...W.S.map(q => q[2]), 0);
    return W; };
  const tyL = Math.tan(K.land.fov / 2 * DEG);
  return [cam('landscape', pl, tyL, tyL * K.land.aspect), cam('portrait', off ? K.port.pitch : -5, Math.tan(K.port.fovMax / 2 * DEG), K.port.tanX)];
}
const IDLE_PER = 4;             // remote stands per staged idle stair unit (inf: review L4 asks for at most one per 3-4)
const IDLE_BUSY = 60.0;         // m: a staged unit is not drawn while an aircraft is parked at a stand this close (inf)
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
  mast: [0.62, 0.63, 0.64, 1], concrete: [0.6, 0.59, 0.56, 1], concreteE: [0.9, 0, 0, 0], // (fix round 1: floodlight masts, galvanised grey, inf)
  // (sha3d) glazed tunnel and fixed-link sides: the objects shader's curtain-wall glass (mat 1: 1.8 m mullions). ZSSS
  // photos 09 / 14 / 15 / 16 (docs/phase1/photos_credits.md) show glass-walled bridge tunnels and two-level glazed fixed
  // links at T2 (obs, appearance only); T1 is assumed alike (inf)
  glassE: [0.1, 0, 1, 0],
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
  // (sha3d: a glazed side material - mat 1 - only on the two long sides; roof, floor and ends stay plain panel)
  if (ext[2] === 1) { const M = m4.basis(d, [0, 1, 0], a); g.box([0, 0, -w / 2], [L, h, w / 2], col, ext, M, ['pz', 'nz']); g.box([0, 0, -w / 2], [L, h, w / 2], col, [ext[0], ext[1], 0, 0], M, ['px', 'nx', 'py', 'ny']); return; }
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
// (sha3d: the SHA class references of data/sha_stands.json class_ref - C909 / A321 / 757-300 / 767-300ER / A330-300 /
// 777-300ER / 747-8 - on the nearest modelled airframe: the C909 is not modelled yet (Phase 4), CRJ900 stands in for B)
const REF_TYPE = { B: 'crj9', C: 'a321', CL: 'b753', D: 'b763', E: 'a333', EL: 'b77w', F: 'b748' };
// (sha3d) the types that make up most of the SHA mix (docs/PLAN.md §1 fleet row: A320 family 45-55 %, 737 23-37 %,
// wide-bodies 14-26 %, an estimate - inf): autoModel weights them above the rare accepted types (regional jets)
const SHA_MAIN = new Set(['a319', 'a320', 'a321', 'a20n', 'a21n', 'b737', 'b738', 'b739', 'b38m', 'a332', 'a333', 'a339', 'a359', 'b788', 'b789', 'b78x', 'b772', 'b77w', 'b763', 'b744', 'b748']);
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
    // (sha3d: every stand has a stand-number sign; VDGS faces for the contact stands and the type designators it shows)
    for (const g of gates) { add('stand', g.name); if (g.bridge) add('vdgs', g.name); }
    for (const t of atlasExtra) add('vdgs', t);
    this.atlas = makeGateAtlas(faces);
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
    else if (!b.upper && !b.extRange && (spec = this.autoModel(g, b, rot))) { [nT, , , opE, opR] = spec; spacer = spec[2] - spec[4]; mechE = spec[1] - spacer; } // (sha3d)
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
    // (sha3d: no data rest pose - fully retracted towards the class reference's door; finishPrep turns it clear of the
    // aircraft, the fixed parts and the building where it is not: autoRest)
    else { const RT = TYPES[REF_TYPE[g.cls] || 'b38m']; const dp = doorOf(standTip(g, RT), f, RT, b.door).door; // (M5: nose wheel on the stop node)
      b.a0 = yawOf(dp[0] - rot[0], dp[2] - rot[2]); b.e0 = opR; b.autoRest = true; }
    b.stairSide = b.stairSide || 1;
    // legacy fields read by tools (jobs/extract2d.mjs, tools/live/invariants.mjs)
    b.attachW = att; b.attachW3 = att; const lu = [rot[0] - walk[Math.max(0, n - 2)][0], 0, rot[2] - walk[Math.max(0, n - 2)][2]]; b.u = Math.hypot(lu[0], lu[2]) > 0.05 ? v3.norm(lu) : dirOf(b.acWalk);
    b.fixedLen = wl; b.rc = [rot[0], G, rot[2]]; b.parkDir = dirOf(b.a0); b.reach = b.e0;
  }
  // sha3d autoModel: the bridge model is not in the SHA data (the make at ZSSS is unknown, PLAN §4), so it is inferred as
  // the sfo3d stand builder inferred SFO's: per sell-sheet model the docked pivot distances (door + the model's cab
  // spacer, from the rotunda) of the stand's accepted types at its stop are tested against its range (operational
  // retraction .. max(operational extension, mechanical stop - 0.3 m), as jointOk); the model covering the most weight
  // wins - the stand's class reference type (REF_TYPE) 100, the common SHA types (SHA_MAIN, PLAN §1 fleet row) 10, any
  // other accepted type 1 - and among equals the one that retracts shortest (the rest pose stays clear), then the shorter
  // extension. b.modelUsed / b.modelWhy record it (inf). null: no type at all (the default AT3 range is used).
  autoModel(g, b, rot) {
    const pts = []; const ref = REF_TYPE[g.cls];
    for (const { s } of this.standPoses(g)) for (const A of this.acceptedTypes(s)) {
      if (b.door === 2 && A.T.dockX2 == null) continue;
      const { door, left } = doorOf(standTip(s, A.T), stD(s.dir), A.T, b.door);
      pts.push({ key: A.key, door, left, w: A.key === ref ? 100 : SHA_MAIN.has(A.key) ? 10 : 1 });
    }
    if (!pts.length) return null;
    let best = null;
    for (const [name, m] of Object.entries(PBB)) {
      const sp = m[2] - m[4], mech = m[1] - sp, hi = Math.max(m[3], mech - 0.3); let score = 0, n = 0;
      for (const P of pts) { const q = v3.add(P.door, v3.mul(P.left, sp)); const e = Math.hypot(q[0] - rot[0], q[2] - rot[2]); if (e >= m[4] - 1e-6 && e <= hi) { score += P.w; n++; } }
      if (!best || score > best.score || (score === best.score && (m[4] < best.m[4] - 1e-9 || (Math.abs(m[4] - best.m[4]) < 1e-9 && m[3] < best.m[3])))) best = { name, m, score, n };
    }
    // (no model reaches any type: the longest unit - it rests and looks like the long bridge the data maps)
    if (!best.score) { const L = Object.entries(PBB).sort((a, c) => c[1][1] - a[1][1])[0]; best = { name: L[0], m: L[1], score: 0, n: 0 }; }
    b.modelUsed = best.name; b.modelSrc = 'inf'; b.modelWhy = `autoModel: ${best.n} of ${pts.length} accepted types in range` + (pts.some(P => P.w === 100) ? (best.score >= 100 ? ', class reference covered' : ', class reference NOT covered') : '');
    return best.m;
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
    const dh = b.upper ? 0 : b.walkLen * (DL.slope ?? 1 / 12);
    // (sha3d: the height targets are the common SHA types the bridge docks, SHA_MAIN, where it docks any - the regional
    // jets' low sills otherwise pull a C stand's rotunda floor down to ~2.5 m; the other types still dock within 1:4)
    b._tgH = tg.some(t => SHA_MAIN.has(t.key)) ? tg.filter(t => SHA_MAIN.has(t.key)) : tg;
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
        const q0 = { a: b.a0, e: b.e0, t: 0, h: b.h0 }; if (!b.autoRest && !this.fixedHit(b, q0, 0) && !this.bldHit(b, q0, 0)) continue;
        const own = this.standAircraft(g); const nb = [];
        for (const o of this.gates) { if (o === g || !o.bridge && !(o.sharesBridgesOf)) continue; const on = stW(o.nose, G); if (Math.hypot(on[0] - b.rot[0], on[2] - b.rot[2]) > 120) continue; for (const A of this.standAircraft(o)) nb.push(A); }
        const others = all.filter(x => x.b !== b && Math.hypot(x.b.rot[0] - b.rot[0], x.b.rot[2] - b.rot[2]) < 80).map(x => restS.get(x.b)).flat();
        const clear = (q) => { if (this.fixedHit(b, q, 0) || this.bldHit(b, q, 0)) return false; const S = this.solidsQ(b, q, 0);
          // (sha3d autoRest: 3.75 m to the stand's own aircraft - MH 5001-2021 table 4.13.5 note a: at a nose-in VDGS stand
          // the clearance from the nose to the movable end of a bridge at its return point may be reduced to 3.75 m)
          for (const bx of S) { if (own.some(A => boxHitsAc(bx, A.T, A.nose, A.f, b.autoRest ? 3.75 : 1.0)) || nb.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 0.5))) return false;
            if (others.some(o => bx.hi > o.lo && o.hi > bx.lo && solidOverlap(bx, o, 0.3))) return false;
            if (bx.part !== 'stair' && [[0, 0], [1, 1], [1, -1], [-1, 1], [-1, -1]].some(([i, j]) => inBuilding(bx.c[0] + bx.u[0] * bx.hl * i - bx.u[1] * bx.hw * j, bx.c[1] + bx.u[1] * bx.hl * i + bx.u[0] * bx.hw * j, false, false, b._strip))) return false; }
          return true; };
        // (sha3d autoRest: the inferred rest pose is kept when it is clear, else turned by up to 80 deg - the rotunda
        // swings 87.5 deg either way - and, failing that, also extended by up to 3 m)
        if (b.autoRest && clear(q0)) continue;
        let pick = null; const dMax = b.autoRest ? 80 : 60;
        for (const de of (b.autoRest ? [0, 1, 2, 3] : [0])) { if (pick) break; for (let d = 1; d <= dMax && !pick; d++) for (const sg of [1, -1]) { const q = { ...q0, a: b.a0 + sg * d * DEG, e: Math.min(b.m.mechE, q0.e + de) }; if (clear(q)) { pick = { q, d: sg * d }; break; } } }
        if (pick) { b.restTurn = pick.d; b.a0 = pick.q.a; b.e0 = pick.q.e; b.parkDir = dirOf(b.a0); b.reach = b.e0; restS.set(b, this.solidsQ(b, pick.q, 0, true)); } else b.restBlocked = true;
      } }
    for (const { g, b } of all) this.prepKin(g, b);
    // twin heads (a walkway branching through one rotunda to a second one 3.4 m away: F15, G12): both drums on one floor
    // level (the connector between them is level; before, it met the first drum 0.7 m above its floor)
    for (const { g, b } of all) if (b.twinOf) {
      const o = b.twinOf; const dh = o.walkLen * (departureLevel(g).slope ?? 1 / 12);
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
  // (M5) the stand's front: the farthest-forward nose tip of its accepted types and its class reference, each parked with
  // the nose wheel on the stop node - the VDGS unit, the stand-number post and the idle-equipment rules measure from it
  frontOf(g) {
    if (g._front) return g._front;
    let x = noseGearX(TYPES[REF_TYPE[g.cls]] || TYPES.a320);
    for (const A of this.acceptedTypes(g)) x = Math.max(x, noseGearX(A.T));
    g._frontX = +x.toFixed(2); return (g._front = [g.nose[0] + g.dir[0] * x, G, g.nose[1] + g.dir[1] * x]);
  }
  // every accepted type of the stand (and of the alternative positions sharing its bridges) at its stop: {T, nose, f}
  standAircraft(g) {
    if (g._acs) return g._acs; const out = [];
    for (const { s } of this.standPoses(g)) for (const A of this.acceptedTypes(s)) {
      const fam = familyOf(A.icao); const st = fam && s.typeStops && s.typeStops[fam]; const along = (st && Number.isFinite(st.along) ? Math.min(0, st.along) : 0) + noseGearX(A.T); // (M5: nose wheel on the stop node)
      const f = stD(s.dir); const n = v3.add(stW(s.nose, G), v3.mul(f, along)); out.push({ T: A.T, key: A.key, nose: [n[0], n[2]], f: [f[0], f[2]] });
    }
    return (g._acs = out);
  }
  // docking extension of an upper-deck bridge to the A380's U1L at the stand
  upperDockExt(g, b, rot) {
    const T = TYPES.a388; if (!T) return null; const { door, left } = doorOf(standTip(g, T), stD(g.dir), T, 3);
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
      const fam = familyOf(A.icao); const st = fam && s.typeStops && s.typeStops[fam]; const along = (st && Number.isFinite(st.along) ? Math.min(0, st.along) : 0) + noseGearX(A.T); // (M5: nose wheel on the stop node)
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
    const dd = g.dock ? g.dock.dir : g.dir;
    const f = stD(dd), nose = g.dock ? stW(g.dock.nose, G) : standTip(g, T); // (M5: without a pose, the nose wheel on the stop node)
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
    if (!door) { const dd = g.dock ? g.dock.dir : g.dir; door = doorOf(g.dock ? stW(g.dock.nose, G) : standTip(g, T), stD(dd), T, b.door).door; }
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
    segs.forEach((S, n) => { if (n === 0) tube(geo, S.first ? v3.add(S.A, v3.mul(S.d, -0.3)) : S.drawA, S.B, WALK_W, WALK_H, C.walk, C.glassE); else slab(geo, S.A, S.B, WALK_W, WALK_H, C.walk, C.glassE); });
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
    secs.forEach(([s0, s1, w, h], i) => { const dy = (h - secs[0][3]) / 2; last = tube(geo, at(s0, fl(s0) - dy), at(s1, fl(s1) - dy), w, h, C.panel, C.glassE); });
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
    // stand-number sign, bridge-mounted (sha3d; replaces sfo3d's gate numbers on both tunnel sides): a triangular prism on
    // a short mast on the rotunda roof - CAAC MH 5001-2021 8.5: stand number signs yellow with black characters,
    // internally lit, numerals >= 600 mm, bridge-mounted ones triangular prisms (docs/phase1/standards_refs.md 1.5). The
    // mounting point is inferred: photo 09 (T2, 2013) shows "256" on a yellow board above the bridge head, photo 14 (T2,
    // 2023) "247" - "249" above the fixed links. Face 1.2 m tall (the atlas numerals fill ~0.55 of it: ~0.66 m), one face
    // towards the arriving aircraft, the others at +-120 deg.
    if (sgn && !b.upper && !b.twinOf) {
      const r = this.atlas.map['stand:' + g.name];
      if (r) {
        const Fh = 1.2, w = Fh * r.aspect, ap = w / (2 * Math.sqrt(3)); const y0 = G + b.Hr + 3.3 + 0.55;
        const n0 = stD([-g.dir[0], -g.dir[1]]); const rotY = (v, a) => [v[0] * Math.cos(a) - v[2] * Math.sin(a), 0, v[0] * Math.sin(a) + v[2] * Math.cos(a)];
        const cc = [rot[0], y0, rot[2]];
        cyl(geo, [rot[0], G + b.Hr + 3.3, rot[2]], 0.12, 0.6, C.steel, C.steelE, 8);
        const tri = []; for (let k2 = 0; k2 < 3; k2++) { const n = rotY(n0, k2 * 2 * Math.PI / 3); const rt = v3.cross(v3.mul(n, -1), [0, 1, 0]);
          const c = v3.add(cc, v3.mul(n, ap)); tri.push([c[0] + rt[0] * w / 2, c[2] + rt[2] * w / 2]);
          const cf = v3.add(c, v3.mul(n, 0.012)); const u0 = v3.add(cf, v3.mul(rt, -w / 2)), u1 = v3.add(cf, v3.mul(rt, w / 2));
          signQuad(sgn, [u0, u1, v3.add(u1, [0, Fh, 0]), v3.add(u0, [0, Fh, 0])], n, r, true); }
        // housing: the prism itself (dark frame), bottom and top caps; tri is clockwise seen from above here -> reversed
        const poly = tri.slice().reverse(); let A2 = 0; for (let i2 = 0; i2 < 3; i2++) { const p = poly[i2], q2 = poly[(i2 + 1) % 3]; A2 += p[0] * q2[1] - q2[0] * p[1]; } if (A2 < 0) poly.reverse();
        geo.extrude(poly, y0 - 0.06, y0 + Fh + 0.06, C.dark, C.darkE, C.steel, C.steelE); geo.cap(poly, y0 - 0.06, C.steel, C.steelE, false);
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
    const nose = this.frontOf(g), f = stD(g.dir); // (M5: ahead of the farthest-forward nose tip of the accepted types)
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
    if (tf != null && tf <= 14) { fac(7.2); fac(4.6); } // (sha3d: 4.6 m - a unit that fits under a low concourse roof, the 8.9 m T1 concourse; inf)
    for (const d of [0, -1, 1, -2, 2, -3, 3, -4, 4, -5, -6, -7, -8]) { const t = 12 + d; if (t >= 3.5 && t <= tmax) tries.push({ t, post: true, H0: 5.2 }); }
    for (let t = 17; t <= Math.min(40, tmax); t++) tries.push({ t, post: true, H0: 5.2 });
    if (tf != null && tf > 14 && tf <= 45) { fac(7.2); fac(4.6); }
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
      const fam = familyOf(A.icao); const st = fam && s.typeStops && s.typeStops[fam]; const along = (st && Number.isFinite(st.along) ? Math.min(0, st.along) : 0) + noseGearX(A.T); // (M5: nose wheel on the stop node)
      const f = stD(s.dir); const nose = v3.add(stW(s.nose, G), v3.mul(f, along));
      const gp = { ...g, acType: A.key, _lastType: A.key, dockType: A.icao, dock: { nose: worldToST(nose[0], nose[2]), dir: s.dir } };
      const P = this.makePlan(gp, b, exact ? {} : { all: true }); if (P.ok) { if (exact) out.push(P); else for (const path of P.alts) out.push({ ...P, path }); }
    }
    return (b[key] = out);
  }
  standGeo(g, geo, sgn) {
    const nose = this.frontOf(g), f = stD(g.dir); // (vdgsSpot's t is measured from the same point)
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
    const gname = g.name; // (sha3d: the stand number; the OSM boarding-gate ref g.gate is not what the stand signs show)
    const vr = (g.acType && g.dockType && this.atlas.map['vdgs:' + g.dockType]) || this.atlas.map['vdgs:' + gname];
    const dh = 0.8, dw = Math.min(1.35, dh * vr.aspect);
    const d0 = v3.add([face[0], G + H0 + 1.35, face[2]], v3.mul(outW, 0.27));
    signQuad(sgn, [v3.add(d0, v3.add(v3.mul(tW, dw / 2), [0, -dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, -dw / 2), [0, -dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, -dw / 2), [0, dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, dw / 2), [0, dh / 2, 0]))], outW, vr, true);
    // stand number above the display (sha3d: CAAC MH 5001-2021 8.5 stand-number sign face from the atlas - yellow, black
    // numerals, lit; 1.4 m face: numerals ~0.77 m >= 600 mm)
    const gr = this.atlas.map['stand:' + gname]; const gh = 1.4, gw = gh * gr.aspect;
    const g0 = v3.add([face[0], G + H0 + 3.1, face[2]], v3.mul(outW, 0.1));
    // (sha3d: the housing behind the face - the basis' local z is outW, so z <= -0.02; sfo3d's [-0.12, 0.02] hid the face)
    if (post) geo.box([-gw / 2 - 0.1, -gh / 2 - 0.1, -0.16], [gw / 2 + 0.1, gh / 2 + 0.1, -0.02], [0.2, 0.21, 0.22, 1], [0.5, 0.4, 0, 0], m4.basis(v3.mul(tW, -1), [0, 1, 0], g0));
    signQuad(sgn, [v3.add(g0, v3.add(v3.mul(tW, gw / 2), [0, -gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, -gw / 2), [0, -gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, -gw / 2), [0, gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, gw / 2), [0, gh / 2, 0]))], outW, gr, true);
  }
  // ------------------------------------------------------------ stands without a bridge of their own (sha3d)
  // Remote stands and the alternative positions sharing a base stand's bridge: a post-mounted stand-number sign
  // (MH 5001-2021 8.5.1 / 8.5.3: on the extension of the stand centreline ahead of the stop, else offset to the left of
  // the centreline as the aircraft enters; 8.5.4 yellow / black, internally lit; 8.5.6 numerals >= 600 mm). Position, post
  // and mounting height are inferred (photo 17, T2 2018: "213" on a yellow board on a post). Parked aircraft: the GSE
  // (placeVehicles: stairs + bus at remote stands); empty remote stand: an idle stair unit at the stand head (cue, inf).
  remoteSpot(g) {
    if (g._sign) return g._sign;
    const nose = this.frontOf(g), f = stD(g.dir), left = v3.norm(v3.cross([0, 1, 0], f)); // (aircraft's left: up x forward)
    const nb = this.neighbourPrints(g);
    const okAt = (p, rad) => !inBuilding(p[0], p[2]) && nearestBuilding(p[0], p[2]).d > rad && laneClear(p[0], p[2]) > rad
      && !nb.some(fp => hitsAircraft(fp, [p[0], p[2]], 6)); // (pavement or grass: a sign post stands on either)
    let pick = null;
    if (g.sharesBridgesOf) { const V = this.vdgsSpot(g); pick = { p: v3.add(nose, v3.mul(f, V.t)), t: V.t, lat: 0, post: V.post, H0: V.H0 }; }
    for (const t of [10, 8, 12, 14, 6, 16, 18, 20, 24]) { if (pick) break; const p = v3.add(nose, v3.mul(f, t)); if (okAt(p, 1.5)) pick = { p, t, lat: 0, post: true }; }
    for (const lat of [4, 6, 8, 10]) { if (pick) break; for (const t of [6, 10, 3, 14]) { const p = v3.add(v3.add(nose, v3.mul(f, t)), v3.mul(left, lat)); if (okAt(p, 1.5)) { pick = { p, t, lat, post: true }; break; } } }
    if (!pick) pick = { p: v3.add(nose, v3.mul(f, 10)), t: 10, lat: 0, post: true, blocked: true };
    return (g._sign = pick);
  }
  // footprints of the class reference aircraft at the stands within 120 m (for sign / idle-equipment placement)
  neighbourPrints(g) {
    if (g._nbp) return g._nbp; const n0 = stW(g.nose, G); const out = [];
    for (const o of this.gates) { if (o === g) continue; const on = stW(o.nose, G); if (Math.hypot(on[0] - n0[0], on[2] - n0[2]) > 120) continue;
      const T = TYPES[REF_TYPE[o.cls]] || TYPES.a320; if (T) out.push(footprint(standTip(o, T), stD(o.dir), T, o)); }
    { const T = TYPES[REF_TYPE[g.cls]] || TYPES.a320; if (T) out.push(footprint(standTip(g, T), stD(g.dir), T, g)); }
    return (g._nbp = out);
  }
  remoteGeo(g, geo, sgn) {
    const f = stD(g.dir); const S = this.remoteSpot(g);
    const r = this.atlas.map['stand:' + g.name];
    if (r) {
      const outW = v3.mul(f, -1), tW = v3.norm(v3.cross(outW, [0, 1, 0]));
      const Fh = 1.1, w = Fh * r.aspect;                       // numerals 0.55 x 1.1 = 0.6 m (8.5.6 >= 600 mm)
      const yb = G + (S.post ? 3.2 : (S.H0 || 5.2) + 2.6);     // face bottom (inf)
      const c = [S.p[0], yb, S.p[2]];
      if (S.post) { cyl(geo, [S.p[0], G, S.p[2]], 0.09, yb - G + 0.1, C.steel, C.steelE, 8); geo.box([-0.35, 0, -0.35], [0.35, 0.2, 0.35], [0.55, 0.55, 0.55, 1], [0.5, 0.3, 0, 0], m4.basis(tW, [0, 1, 0], [S.p[0], G, S.p[2]])); }
      geo.box([-w / 2 - 0.06, -0.06, -0.16], [w / 2 + 0.06, Fh + 0.06, -0.02], C.dark, C.darkE, m4.basis(v3.mul(tW, -1), [0, 1, 0], c)); // (local z = outW: behind the face)
      const d0 = c;
      signQuad(sgn, [v3.add(d0, v3.mul(tW, w / 2)), v3.add(d0, v3.mul(tW, -w / 2)), v3.add(v3.add(d0, v3.mul(tW, -w / 2)), [0, Fh, 0]), v3.add(v3.add(d0, v3.mul(tW, w / 2)), [0, Fh, 0])], outW, r, true);
    }
    if (g.acType && g.dock) { this.placeVehicles(g, []); return; }
    // (fix round 1, review L4: the idle stair units are no longer parked at every empty remote stand head; they are staged
    // once for the whole apron, at most one per IDLE_PER remote stands - stageIdleStairs / idleGeo)
  }
  // ------------------------------------------------------------ idle airstairs (sha3d fix round 1, review L4)
  // A cue that the remote stands board by stairs (inf; not an observation): at most one unit per IDLE_PER remote stands
  // (non-business remote stands grouped by area in stand-number order), parked in a painted equipment area of the group
  // (MH 5001-2021 6.2.20 设备区: js/live/caac_decals.js, SHA.markings.apron().equipment) along its long side, else at the
  // apron edge ahead of the group's stand fronts; always on pavement, off the lanes and the buildings and outside every
  // class-reference planform (nose wheel on the stop node; 4 m). A unit is not drawn while an aircraft is parked at a stand
  // within IDLE_BUSY m of it: placeVehicles then draws the stairs at that aircraft's doors.
  stageIdleStairs(equipment = [], paved = null) {   // (paved: fix round 3, review N5 - the tier-independent pavement test)
    const S = 3.2, hull = stairHull(S), x0 = Math.min(...hull.map(h => h[0])), len = -x0, wid = 2.2;
    const remote = this.gates.filter(g => g.remote && g.service !== 'business' && !g.sharesBridgesOf)
      .sort((a, b) => (a.area || '').localeCompare(b.area || '') || (parseInt(a.name, 10) - parseInt(b.name, 10)) || a.name.localeCompare(b.name));
    const byArea = new Map(); for (const g of remote) { const k = g.area || ''; if (!byArea.has(k)) byArea.set(k, []); byArea.get(k).push(g); }
    const eqBy = new Map(); for (const e of equipment || []) { if (!e || !e.ring || e.ring.length < 4) continue; if (!eqBy.has(e.stand)) eqBy.set(e.stand, []); eqBy.get(e.stand).push(e); }
    const out = [];
    const fits = (p, d, g) => { const rt = [-d[1], d[0]]; const nb = this.neighbourPrints(g);
      for (const [hx0, hx1, z0, z1] of hull) for (const [x, z] of [[hx0, z0], [hx0, z1], [hx1, z0], [hx1, z1], [(hx0 + hx1) / 2, (z0 + z1) / 2]]) {
        const q = [p[0] + d[0] * x + rt[0] * z, p[1] + d[1] * x + rt[1] * z];
        if (inBuilding(q[0], q[1]) || laneClear(q[0], q[1]) < 1.5 || (paved ? !paved(q[0], q[1]) : PAVED && PAVED(q[0], q[1]) < 0.5) || nb.some(fp => hitsAircraft(fp, q, 4))) return false; }
      return !out.some(o => Math.hypot(o.p[0] - p[0], o.p[1] - p[1]) < 9); };
    for (const [area, list] of byArea) for (let i = 0; i < list.length; i += IDLE_PER) {
      const grp = list.slice(i, i + IDLE_PER); const mid = Math.floor((grp.length - 1) / 2);
      const order = grp.map((g, k) => [g, Math.abs(k - mid)]).sort((a, b) => a[1] - b[1]).map(x => x[0]);
      let pick = null;
      for (const g of order) { if (pick) break; for (const e of eqBy.get(g.name) || []) {
        const R = e.ring; const ax = [R[1][0] - R[0][0], R[1][1] - R[0][1]], aw = [R[3][0] - R[0][0], R[3][1] - R[0][1]];
        let La = Math.hypot(ax[0], ax[1]), Lw = Math.hypot(aw[0], aw[1]); let d = [ax[0] / La, ax[1] / La], w = [aw[0] / Lw, aw[1] / Lw];
        if (Lw > La) { [La, Lw] = [Lw, La]; [d, w] = [w, d]; }
        if (La < len + 0.8 || Lw < wid + 0.8) continue;
        const c = [(R[0][0] + R[1][0] + R[2][0] + R[3][0]) / 4, (R[0][1] + R[1][1] + R[2][1] + R[3][1]) / 4];
        const p = [c[0] + d[0] * len / 2, c[1] + d[1] * len / 2];                // (the unit's front; it reaches len m back)
        if (fits(p, d, g)) { pick = { p, d, host: g.name, where: 'equipment area (6.2.20)' }; break; } } }
      for (const g of order) { if (pick) break; const f = g.dir, lf = [f[1], -f[0]]; const F = this.frontOf(g);
        for (const a of [10, 14, 18, 22]) { if (pick) break; for (const l of [0, 6, -6, 12, -12, 18, -18]) {
          const p = [F[0] + f[0] * (a + len) + lf[0] * l, F[2] + f[1] * (a + len) + lf[1] * l];
          if (fits(p, f, g)) { pick = { p, d: f.slice(), host: g.name, where: 'apron edge ahead of the stand' }; break; } } } }
      if (pick) out.push({ ...pick, p: pick.p.map(v => +v.toFixed(2)), d: pick.d.map(v => +v.toFixed(4)), area, group: grp.map(g => g.name), src: 'inf' });
    }
    this.idleSpots = out; this.idleStats = { remoteStands: remote.length, groups: [...byArea.values()].reduce((n, l) => n + Math.ceil(l.length / IDLE_PER), 0), placed: out.length,
      inEquipmentAreas: out.filter(o => /^equipment/.test(o.where)).length, perStands: IDLE_PER };
    this.dirty = true; return out;
  }
  idleGeo() {
    if (!this.idleSpots || !this.vehicleBuckets) return;
    const st = Object.keys(this.vehicleBuckets).filter(k => /^stairs\d+$/.test(k)).map(k => [k, +k.slice(6) / 100]).sort((a, b) => Math.abs(a[1] - 3.2) - Math.abs(b[1] - 3.2))[0]; if (!st) return;
    const busy = this.gates.filter(o => o.acType).map(o => o.nose);
    for (const s of this.idleSpots) {
      if (busy.some(n => Math.hypot(n[0] - s.p[0], n[1] - s.p[1]) < IDLE_BUSY)) continue;
      (this._idleBoxes || (this._idleBoxes = [])).push(s.p.slice());
      this.vehicleBuckets[st[0]].push(inst(m4.basis([s.d[0], 0, s.d[1]], [0, 1, 0], [s.p[0], G, s.p[1]]), [0.9, 0.9, 0.9, 1]));
    }
  }
  // ------------------------------------------------------------ apron floodlight masts (sha3d fix round 1, review M2)
  // Photos 02, 09, 14, 16 and 17 (docs/phase1/photos_credits.md) show 25-35 m high-mast floodlights with a multi-lamp head
  // at regular spacing along the ZSSS aprons; photo 09 (T2 north pier, 2013) shows them on the apron edge of the service
  // road, about on the line of the rotundas, between the stands. Positions, height (MAST_H), head (6 lamps) and spacing
  // are inferred (src inf); the make is unknown. Candidates per stand, in preference order: at a contact stand beside its
  // rotunda along the facade (+-8 .. 30 m) on the rotunda line or up to 6 m apron-side of it; at a remote stand ahead of
  // its front (the farthest-forward nose tip), between the stands. A candidate is taken when it is clear of:
  //  - the terminal outlines (4 m) and the runway strips (150 m from a runway centreline, MH 5001-2021 4.4: strip of a code
  //    3 / 4 instrument runway);
  //  - every stand's planform (class reference with its nose wheel on the stop node) grown by the table 4.13.5 clearance
  //    (3.0 / 4.5 / 7.5 m), and every painted stand envelope when the markings package gives them (+1 m);
  //  - the swept path of every lead-in (the class reference along it, the same clearance; for code C this equals the
  //    table 4.9.5 col. (13) taxilane-to-object distance 22.5 m within 0.1 m);
  //  - apron lanes: taxiway centrelines by table 4.9.5 col. (11), taxilane centrelines by col. (13), for the largest code
  //    letter among the stands within 150 m (C 26.0 / 22.5, D 37.0 / 33.5, E 43.5 / 40.0, F 51.0 / 47.5 m);
  //  - the jet bridges: fixed walkways and drums (3 m) and every tunnel axis from the rotunda to the cab in the rest pose and
  //    along every docking path of the accepted types (MAST_BRIDGE_CLEAR); the VDGS and stand-sign posts (3 m);
  //  - the masts already placed (stands in area / number order): at least max(MAST_SPACING, 1.8 x the stand's spacing to
  //    its nearest neighbour), so about one mast per two stands;
  //  - and it stands on pavement (fix round 2 integration: the 12 m grass-verge tolerance of the remote rows is dropped now
  //    that the stand-head fill paves the remote stand heads, review_visual_fix1.md R1 (3)); (fix round 3, review V4) the
  //    whole base plate with a MAST_PAVE_MARGIN margin (its centre and the four corners of the plate grown by 2 m: the
  //    review's 1 m plus 1 m for the 2 m cells of the ground map's CPU copy), by the tier-independent
  //    pavement test `paved` (js/live/gates.js vectorPavement: the polygons the ground map is painted from; review N5:
  //    the ground map's pavedAt is sampled at the tier's resolution, and edge candidates flipped between tiers);
  //  - (fix round 3, review V4) the painted equipment areas (6.2.20 设备区, SHA.markings.apron().equipment): the base plate
  //    at least MAST_EQUIP_CLEAR clear of them;
  //  - (fix round 2, review N1) and out of the app's own stand cameras (STAND_CAM / standCamPos: the pole projected into
  //    each stand's camera, both sides, must clear the subject points and the centre band): a contact stand keeps side +1
  //    clear (the bridge side: "Fly to stand" and the named stand views), a remote stand keeps at least one side clear
  //    (flyToStand takes the clear side). MAST_CAM_STRICT_REMOTE = true asks side +1 of the remote stands too.
  //    (fix round 3, review V2) a side is clear only when no mast is in its near field either (standCamNear: the head or the
  //    pole above 10 m in the frame at a depth under 45 m, or the pole within 25 m of the camera), so that "Fly to stand"
  //    never has a mast head in the foreground. The alternative positions on a base stand's bridge (238A, 259A) have their
  //    own camera (their node and heading, the base stand's bridges as subject), as the app builds it (shell.js standCam).
  // The service roads are not in the data (no airside road geometry); the rotunda-line rule keeps the masts off the band
  // between the facade and the rotundas where photo 09 shows the road.
  // rules: QA overrides of the module rules (experiments; the app passes none): {contact, equipClear, paveMargin, near,
  // spacing, strictRemote, gapFill}. A stand still without a mast within MAST_GAP_R after the pass gets a gap-fill try
  // (below). stats.hash = FNV-1a of the positions (equal on every quality tier, review N5).
  // (fix round 4, review_visual_fix3.md) F1: `tower` (anchors.tower) - the app's Tower view cameras (towerViewCams, landscape
  // and portrait) are kept clear like a contact stand's side +1: no mast in their near field (TOWER_CAM.nearDepth, 250 m since the verification round) or their subject / centre
  // band; F4: the base plate MAST_ENV_CLEAR clear of every painted envelope line; F3: the stand cameras' near field is 55 m.
  // `dry`: return {masts, stats, uncovered} without placing them (QA: SHA.qa.mastsLive()).
  // (fix round 4, F7) `cache`: a stored placement {inputs, masts, uncovered, stats} (data/sha_masts.json, written by
  // jobs/gates.mjs SET=masts from this same pass): it is used when its `inputs` equals the hash of this pass's inputs - the
  // source text of the placement code (this method, the camera tests, the geometry helpers), its constants and rules, and
  // every derived input (stands, footprints, lead-in sweeps, bridge parts and docking sweeps, posts, building outlines,
  // lanes, runways, painted envelopes and equipment areas, the pavement signature, the stand and Tower view cameras);
  // otherwise the live pass runs (stats.source 'live', cacheInputs = the stored hash). Either way the list is the same on
  // every quality tier (the inputs are tier-independent).
  placeMasts({ runways = [], envelopes = [], equipment = [], paved = null, tower = null, rules = {}, dry = false, cache = null } = {}) {
    if (!this._fin) this.finishPrep();
    const RU = { contact: MAST_CAM_CONTACT, equipClear: MAST_EQUIP_CLEAR, envClear: MAST_ENV_CLEAR, paveMargin: MAST_PAVE_MARGIN, near: true, spacing: MAST_SPACING, strictRemote: MAST_CAM_STRICT_REMOTE, gapFill: true, gapGrid: MAST_GAP_GRID, gapOrder: 'head', gapHead: MAST_GAP_HEAD, gapHeadTower: Math.tan(TOWER_CAM.headDeg * DEG), gapSubj: MAST_GAP_SUBJ, tower: true, towerSubject: true, ...rules };
    const t0 = performance.now();
    const letter = { B: 'C', C: 'C', CL: 'D', D: 'D', E: 'E', EL: 'E', F: 'F' }, ORD = 'CDEF';
    const TWY_OBJ = val(CAAC.separation.twyCLToObject), TWL_OBJ = val(CAAC.separation.taxilaneCLToObject); // MH 5001-2021 table 4.9.5 col. (11) / (13), 9.2.7 (js/live/caac_markings.js)
    const refT = (g) => TYPES[REF_TYPE[g.cls]] || TYPES.a320;
    const prints = this.gates.map(g => { const T = refT(g); return { fp: footprint(standTip(g, T), stD(g.dir), T, g), m: icaoClear(T.wing.span), R: T.L + T.wing.span / 2 + 8 }; });
    const sweep = [];
    for (const g of this.gates) { const W = g.leadinW; if (!W || W.length < 2) continue; const T = refT(g); const xg = noseGearX(T); const m = icaoClear(T.wing.span);
      for (let i = 1; i < W.length; i++) { const A = W[i - 1], B = W[i]; const L = Math.hypot(B[0] - A[0], B[1] - A[1]); if (L < 0.1) continue; const u = [(B[0] - A[0]) / L, (B[1] - A[1]) / L];
        for (let t = 0; t < L; t += 6) { const p = [A[0] + u[0] * t, A[1] + u[1] * t]; const tip = [p[0] + u[0] * xg, G, p[1] + u[1] * xg]; sweep.push({ fp: footprint(tip, [u[0], 0, u[1]], T, g), m, R: T.L + T.wing.span / 2 + 8 }); } } }
    const envHit = (P, q) => { const fp = P.fp; const dx = q[0] - fp.nose[0], dz = q[1] - fp.nose[1]; if (dx * dx + dz * dz > P.R * P.R) return false;
      const x = -(dx * fp.f[0] + dz * fp.f[1]), y = dx * fp.r[0] + dz * fp.r[1], T = fp.T, m = P.m;
      if (x > -m && x < T.L + m && Math.abs(y) < T.R + m) return true;
      const w = T.wing; if (w) { const ay = Math.abs(y), yy = Math.min(ay, w.span / 2), le = w.rootLE + yy * Math.tan((w.sweep || 25) * DEG), ch = w.rootC - (w.rootC - w.tipC) * Math.min(1, yy / (w.span / 2));
        if (ay < w.span / 2 + m && x > le - m && x < le + ch + m) return true; }
      return !!(T.hstab && x > T.hstab.x - m && x < T.L + m && Math.abs(y) < T.hstab.span / 2 + m); };
    const segD = (p, A, B) => { const ex = B[0] - A[0], ez = B[1] - A[1]; const t = clampN(((p[0] - A[0]) * ex + (p[1] - A[1]) * ez) / (ex * ex + ez * ez || 1), 0, 1); return Math.hypot(A[0] + ex * t - p[0], A[1] + ez * t - p[1]); };
    const arms = []; const fixed = [];
    for (const g of this.gates) for (const b of this.bridgesOf(g)) { if (!b.m) this.prepBridge(g, b); const r = [b.rot[0], b.rot[2]];
      fixed.push({ c: r, r: (b.rotR || 2.45) + 3 }); for (let i = 1; i < (b.walk || []).length; i++) fixed.push({ A: [b.walk[i - 1][0], b.walk[i - 1][2]], B: [b.walk[i][0], b.walk[i][2]], r: WALK_W / 2 + 3 });
      const qs = [{ a: b.a0, e: b.e0 }].concat(this.sweepQ(g, b, false)); for (const q of qs) arms.push({ A: r, B: [r[0] + Math.cos(q.a) * (q.e + 2.5), r[1] + Math.sin(q.a) * (q.e + 2.5)] }); }
    const posts = []; for (const g of this.gates) { const F = this.frontOf(g); if (g.bridge) { const V = this.vdgsSpot(g); posts.push([F[0] + g.dir[0] * V.t, F[2] + g.dir[1] * V.t]); } else { const S = this.remoteSpot(g); posts.push([S.p[0], S.p[2]]); } }
    const strips = runways.map(rw => ({ A: rw.a, B: rw.b }));
    const inRing = (R, x, z) => { let c = false; for (let i = 0, j = R.length - 1; i < R.length; j = i++) if (((R[i][1] > z) !== (R[j][1] > z)) && (x < (R[j][0] - R[i][0]) * (z - R[i][1]) / (R[j][1] - R[i][1]) + R[i][0])) c = !c; return c; };
    // (fix round 4, F4) the painted envelopes: inside the ring, or the base plate within RU.envClear of the line (the foot
    // within envClear + the plate's half diagonal, 3.13 m)
    const EVC = RU.envClear + MAST_PLATE_HALF * Math.SQRT2;
    const envBB = envelopes.filter(e => e && e.ring && e.ring.length >= 3).map(e => { let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const p of e.ring) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); } return { ring: e.ring, bb: [x0 - EVC - 1, z0 - EVC - 1, x1 + EVC + 1, z1 + EVC + 1] }; });
    const envLineD = (E, q) => { let d = Infinity; const R = E.ring; for (let i = 0, j = R.length - 1; i < R.length; j = i++) d = Math.min(d, segD(q, R[j], R[i])); return d; };
    // (fix round 4, F1) the app's Tower view cameras (landscape / portrait)
    const towerW = RU.tower ? towerViewCams(tower, runways) : [];
    const nearest = new Map(this.gates.map(g => { let d = 1e9; for (const o of this.gates) if (o !== g && !o.sharesBridgesOf && !g.sharesBridgesOf) d = Math.min(d, Math.hypot(o.nose[0] - g.nose[0], o.nose[1] - g.nose[1])); return [g, d]; }));
    // (fix round 3, V4) the painted equipment areas, grown by MAST_EQUIP_CLEAR from the base plate (the foot centre at least
    // MAST_EQUIP_CLEAR + the plate's half diagonal, 3.13 m, from the ring: the review asked 2 m from the foot)
    const EC = RU.equipClear + MAST_PLATE_HALF * Math.SQRT2; const eqBB = (equipment || []).filter(e => e && e.ring && e.ring.length >= 3).map(e => { let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const p of e.ring) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); } return { ring: e.ring, bb: [x0 - EC, z0 - EC, x1 + EC, z1 + EC] }; });
    const inEquip = (q) => eqBB.some(E => { if (q[0] < E.bb[0] || q[0] > E.bb[2] || q[1] < E.bb[1] || q[1] > E.bb[3]) return false; if (inRing(E.ring, q[0], q[1])) return true;
      for (let i = 0, j = E.ring.length - 1; i < E.ring.length; j = i++) if (segD(q, E.ring[j], E.ring[i]) < EC) return true; return false; });
    // (fix round 3, V4 / N5) the base plate and a margin on pavement: tier-independent `paved` (else the ground map >= 0.5)
    const onPave = paved || ((x, z) => !PAVED || PAVED(x, z) >= 0.5); const PC = MAST_PLATE_HALF + RU.paveMargin;
    const plateOnPave = (q, fc) => { if (!onPave(q[0], q[1])) return false; const l = [-fc[1], fc[0]];
      for (const a of [-PC, PC]) for (const b of [-PC, PC]) if (!onPave(q[0] + fc[0] * a + l[0] * b, q[1] + fc[1] * a + l[1] * b)) return false; return true; };
    // (fix round 2, N1) the stand cameras: both sides of every stand, and which sides the masts placed so far block -
    // (fix round 3, V2) by the subject / centre margins (blkS) or by the near field (blkN); blk = either
    const cams = this.gates.map(g => { const subj = this.camSubject(g);
      return { g, strict: g.contact ? RU.contact !== 'either' : RU.strictRemote, w: [standCamWedge(g.nose, g.dir, g.cls, 1, subj), standCamWedge(g.nose, g.dir, g.cls, -1, subj)], blk: [false, false], blkS: [false, false], blkN: [false, false] }; });
    // (the near field reaches ~45 m past a camera up to ~130 m from its stop node: cameras within 200 m are tested)
    const camHits = (q) => { const H = []; for (const c of cams) { if (Math.abs(c.g.nose[0] - q[0]) > 200 || Math.abs(c.g.nose[1] - q[1]) > 200) continue;
      const sa = standCamPos(c.w[0], q).in, sb = standCamPos(c.w[1], q).in, na = RU.near && standCamNear(c.w[0], q, MAST_H).near, nb = RU.near && standCamNear(c.w[1], q, MAST_H).near;
      if (sa || sb || na || nb) H.push([c, sa || na, sb || nb, [sa, sb], [na, nb]]); } return H; };
    const why = {}; let mine = null; const fail = (k) => { why[k] = (why[k] || 0) + 1; if (mine) mine[k] = (mine[k] || 0) + 1; return false; };
    const ok = (q, g, fc) => {
      if (inBuilding(q[0], q[1])) return fail('building'); if (nearestBuilding(q[0], q[1]).d < 4) return fail('building');
      if (strips.some(s => segD(q, s.A, s.B) < 150)) return fail('runway strip');
      let code = 0; for (const o of this.gates) if (Math.hypot(o.nose[0] - q[0], o.nose[1] - q[1]) < 150) code = Math.max(code, ORD.indexOf(letter[o.cls] || 'C'));
      for (const L of LANES) { const lim = L[4] > 10 ? TWY_OBJ[ORD[code]] : TWL_OBJ[ORD[code]]; if (Math.min(L[0], L[2]) > q[0] + lim || Math.max(L[0], L[2]) < q[0] - lim || Math.min(L[1], L[3]) > q[1] + lim || Math.max(L[1], L[3]) < q[1] - lim) continue;
        if (segD(q, [L[0], L[1]], [L[2], L[3]]) < lim) return fail('lane'); }
      if (prints.some(P => envHit(P, q))) return fail('stand envelope');
      const envNear = envBB.filter(E => q[0] > E.bb[0] && q[0] < E.bb[2] && q[1] > E.bb[1] && q[1] < E.bb[3]);
      if (envNear.some(E => inRing(E.ring, q[0], q[1]))) return fail('painted envelope');
      if (envNear.some(E => envLineD(E, q) < EVC)) return fail('envelope clearance');
      if (sweep.some(P => envHit(P, q))) return fail('lead-in sweep');
      if (fixed.some(F => F.c ? Math.hypot(F.c[0] - q[0], F.c[1] - q[1]) < F.r : segD(q, F.A, F.B) < F.r)) return fail('bridge fixed part');
      if (arms.some(A => segD(q, A.A, A.B) < MAST_BRIDGE_CLEAR)) return fail('bridge sweep');
      if (posts.some(p => Math.hypot(p[0] - q[0], p[1] - q[1]) < 3)) return fail('post');
      // on pavement (fix round 2 integration, review_visual_fix1.md R1 (3), buildings hand-off: the stand-head fill now paves
      // the remote stand heads, so the 12 m grass-verge tolerance of the remote rows is dropped)
      if (!plateOnPave(q, fc)) return fail('not paved');
      if (inEquip(q)) return fail('equipment area');
      for (const [c, a, b, S] of camHits(q)) if (c.strict ? a : (a || c.blk[0]) && (b || c.blk[1])) return fail((c.strict ? S[0] : (S[0] || c.blkS[0]) && (S[1] || c.blkS[1])) ? 'stand camera' : 'stand camera near field');
      for (const W of towerW) { if (standCamNear(W, q, MAST_H).near) return fail('tower view near field'); if (RU.towerSubject && standCamPos(W, q).in) return fail('tower view'); }
      return true; };
    const order = this.gates.filter(g => !g.sharesBridgesOf)
      .sort((a, b) => (a.area || '').localeCompare(b.area || '') || (parseInt(a.name, 10) - parseInt(b.name, 10)) || a.name.localeCompare(b.name));
    // (fix round 4, F7) the inputs hash (see above) and the cached placement
    const msPrep = Math.round(performance.now() - t0); const tH = performance.now();
    const wingOf = (T) => T.wing ? [T.wing.span, T.wing.rootLE, T.wing.sweep || 25, T.wing.rootC, T.wing.tipC] : null;
    const IH = fnvHash().any([
      [this.placeMasts, this.camSubject, standCamWedge, standCamProject, standCamPos, standCamNear, standCamNearList, standCamHead, towerViewCams, footprint, inBuilding, inRingK, nearestBuilding, icaoClear, noseGearX, standTip, hull2, segPoly2, ptSeg2, segX2, inPoly2],
      { MAST_H, MAST_SPACING, MAST_BRIDGE_CLEAR, MAST_EQUIP_CLEAR, MAST_ENV_CLEAR, MAST_PLATE_HALF, MAST_PAVE_MARGIN, MAST_GAP_R, MAST_GAP_GRID, MAST_GAP_HEAD, MAST_GAP_SUBJ, STAND_CAM, TOWER_CAM, RU, TWY_OBJ, TWL_OBJ },
      this.gates.map(g => [g.name, g.area || '', g.cls, !!g.contact, g.nose, g.dir, g.sharesBridgesOf || '']), order.map(g => g.name), order.map(g => nearest.get(g)),
      prints.map(P => [P.fp.nose, P.fp.f, P.m, P.R, P.fp.T.L, P.fp.T.R, wingOf(P.fp.T), P.fp.T.hstab ? [P.fp.T.hstab.x, P.fp.T.hstab.span] : null]),
      sweep.map(P => [P.fp.nose, P.fp.f, P.m]), arms.map(A => [A.A, A.B]), fixed.map(F => F.c ? [F.c, F.r] : [F.A, F.B, F.r]), posts, strips.map(S => [S.A, S.B]),
      envBB.map(E => E.ring), eqBB.map(E => E.ring), BLD, LANES, paved ? (paved.sig || 'vector') : 'raster', towerW.map(W => [W.cam, W.F, W.tanX, W.tanY, W.hull]),
      cams.map(c => c.w.map(W => [W.cam, W.F, W.hull, W.zMax]))]).hex();
    const msHash = Math.round(performance.now() - tH);
    if (cache && !dry && cache.inputs === IH && Array.isArray(cache.masts)) {
      const stats = { ...(cache.stats || {}), source: 'cache', inputs: IH, ms: Math.round(performance.now() - t0), msPrep, msHash, msLive: cache.stats && cache.stats.msLive };
      this.masts = cache.masts.map(m => ({ ...m, p: m.p.slice(), face: m.face.slice() })); this.mastStats = stats; this.mastUncovered = (cache.uncovered || []).map(u => ({ ...u }));
      this.dirty = true; return this.masts;
    }
    const masts = []; const perStand = new Map();
    const take = (g, cands, spacing) => { for (const c of cands) {
      if (masts.some(M => Math.hypot(M.p[0] - c.q[0], M.p[1] - c.q[1]) < spacing)) { fail('spacing'); continue; }
      if (!ok(c.q, g, c.face)) continue;
      for (const [cc, a, b, S, N] of camHits(c.q)) { for (const k of [0, 1]) { if (S[k]) cc.blkS[k] = true; if (N[k]) cc.blkN[k] = true; } if (a) cc.blk[0] = true; if (b) cc.blk[1] = true; }
      masts.push({ p: c.q.map(v => +v.toFixed(2)), face: c.face.map(v => +v.toFixed(4)), h: MAST_H, stand: g.name, area: g.area, at: c.at, src: 'inf' }); return true; } return false; };
    for (const g of order) {
      mine = {}; perStand.set(g.name, mine);
      const spacing = Math.max(RU.spacing, 1.8 * Math.min(nearest.get(g), 70));
      const f = g.dir, lf = [f[1], -f[0]]; const cands = [];
      const b = (g.bridges || [])[0];
      if (b && b.rot) { // along the facade beside the rotunda: u = out of the building (walkway direction), t = along the facade
        const r = [b.rot[0], b.rot[2]]; const u = b.u ? [b.u[0], b.u[2]] : [-f[0], -f[1]]; const ul = Math.hypot(u[0], u[1]) || 1; const uo = [u[0] / ul, u[1] / ul], t = [-uo[1], uo[0]];
        for (const s of [0, 2, 4, 6]) for (const l of [8, -8, 11, -11, 14, -14, 18, -18, 22, -22, 26, -26, 30, -30]) cands.push({ q: [r[0] + t[0] * l + uo[0] * s, r[1] + t[1] * l + uo[1] * s], face: uo, at: 'rotunda line' });
      } else { // ahead of the stand front, between the stands
        const F = this.frontOf(g); const half = Math.min(35, nearest.get(g) / 2);
        // (a = 0 / -3: between the noses of neighbouring stands, ahead of their wings - for the rows whose heads end at the
        // apron edge or face a lane)
        for (const a of [8, 12, 6, 3, 16, 0, -3, 20, 26]) for (const l of [half, -half, half * 0.7, -half * 0.7, 0]) cands.push({ q: [F[0] + f[0] * a + lf[0] * l, F[2] + f[1] * a + lf[1] * l], face: [-f[0], -f[1]], at: a > 0 ? 'ahead of the stand front' : 'between the stand noses' });
      }
      take(g, cands, spacing);
    }
    // (fix round 3, review V2) gap fill. The near-field rule clears the rotunda line in front of most contact-stand cameras
    // (their cameras hover over the facade 45-55 m to the left of the stand). A stand left with no mast within MAST_GAP_R
    // gets one more try on a polar grid about its stop node (MAST_GAP_GRID: radii 18-114 m by 6 m, every 7.5 deg; was 24-108 m by 12 m, every 15 deg) under every
    // rule above, the head facing the stop node: masts stay visible along the rows without entering a stand camera.
    // (fix round 4 verification, F3) the grid is ranked by headCost (MAST_GAP_HEAD / MAST_GAP_SUBJ; nearest first among the
    // candidates under the limits) instead of nearest first.
    // the largest head a candidate shows in the camera each stand takes ("Fly to stand": side +1 of a contact stand, else
    // side +1 while it is clear, side -1 otherwise) and in the Tower view cameras (cameras of stands within 260 m: a head
    // farther from a camera than ~120 m is under RU.gapHead anyway)
    const headCost = (q) => { let c = 0;
      for (const cc of cams) { if (Math.abs(cc.g.nose[0] - q[0]) > 260 || Math.abs(cc.g.nose[1] - q[1]) > 260) continue;
        const W = cc.strict || !cc.blk[0] ? cc.w[0] : cc.w[1]; c = Math.max(c, standCamHead(W, q) / RU.gapHead);
        if (RU.gapSubj) { const d = standCamPos(W, q).d; if (d < RU.gapSubj) c = Math.max(c, RU.gapSubj / Math.max(0.05, d)); } }
      for (const W of towerW) c = Math.max(c, standCamHead(W, q) / RU.gapHeadTower);
      return c; };
    if (RU.gapFill) for (const g of order) {
      if (masts.some(M => Math.hypot(M.p[0] - g.nose[0], M.p[1] - g.nose[1]) < MAST_GAP_R)) continue;
      mine = perStand.get(g.name); const spacing = Math.max(RU.spacing, 1.8 * Math.min(nearest.get(g), 70)); const cands = [];
      const [r0, r1, dr, da] = RU.gapGrid; for (let r = r0; r <= r1 + 1e-6; r += dr) for (let k = 0; k * da < 360 - 1e-6; k++) { const a = k * da * DEG; const d = [Math.sin(a), -Math.cos(a)]; cands.push({ q: [g.nose[0] + d[0] * r, g.nose[1] + d[1] * r], face: [-d[0], -d[1]], at: 'gap fill' }); }
      // (fix round 4 verification, F3) rank: heads under RU.gapHead in every taken stand camera and the Tower view first
      // (nearest first), then by ascending head size (headCost); a stable sort on the grid order, so deterministic
      if (RU.gapOrder === 'head') { const key = cands.map((c, i) => [Math.max(1, headCost(c.q)), i]); key.sort((a, b) => a[0] - b[0] || a[1] - b[1]); const C0 = cands.slice(); cands.length = 0; for (const [, i] of key) cands.push(C0[i]); }
      take(g, cands, spacing);
    }
    mine = null;
    const by = {}; for (const M of masts) by[M.area] = (by[M.area] || 0) + 1;
    // stands with no mast within 120 m of their stop node, and why their own candidates failed (QA / report)
    const uncovered = order.filter(g => !masts.some(M => Math.hypot(M.p[0] - g.nose[0], M.p[1] - g.nose[1]) < MAST_GAP_R)).map(g => { const r = perStand.get(g.name) || {}; delete r.spacing; return { stand: g.name, area: g.area, why: r }; });
    // (fix round 2, N1) the stand cameras after placement: sides with a mast in the sight wedge (QA; contact side +1 must be 0)
    // (fix round 3, V2) contactSide1 = contact stands with side +1 blocked (subject or near field); contactNear1 = by the near
    // field; contactClear = contact stands with a clear side; remoteNoClear = remote stands with neither side clear (all
    // must be empty / complete with the default rules)
    const cb = { contactSide1: cams.filter(c => c.g.contact && c.blk[0]).map(c => c.g.name), contactNear1: cams.filter(c => c.g.contact && c.blkN[0]).map(c => c.g.name),
      contactClear: cams.filter(c => c.g.contact && !(c.blk[0] && c.blk[1])).length, contact: cams.filter(c => c.g.contact).length,
      remoteSide1: cams.filter(c => !c.g.contact && c.blk[0]).length, remoteSide2: cams.filter(c => !c.g.contact && c.blk[1]).length,
      remoteNear: [cams.filter(c => !c.g.contact && c.blkN[0]).length, cams.filter(c => !c.g.contact && c.blkN[1]).length],
      bothSides: cams.filter(c => c.blk[0] && c.blk[1]).map(c => c.g.name), subjDeg: STAND_CAM.subjDeg, centreDeg: STAND_CAM.centreDeg,
      near: { depth: STAND_CAM.nearDepth, dist: STAND_CAM.nearDist, poleMin: STAND_CAM.nearPoleMin }, strictRemote: RU.strictRemote, contactRule: RU.contact,
      // (fix round 4, F1) the Tower view cameras: the masts in their near field / subject band (both must be empty)
      tower: towerW.map(W => ({ frame: W.frame, eye: W.cam.map(v => +v.toFixed(2)), yaw: +W.yaw.toFixed(2), pitch: +W.pitch.toFixed(2), nearDepth: W.nearDepth,
        near: standCamNearList(W, masts).map(n => n.mast), subject: masts.filter(M => standCamPos(W, M.p).in).map(M => M.stand) })), src: 'inf' };
    // a hash of the mast list (FNV-1a over the positions to 0.01 m): equal on every quality tier (review N5)
    let hh = 2166136261; for (const M of masts) for (const v of M.p) { const t = v.toFixed(2); for (let i = 0; i < t.length; i++) { hh ^= t.charCodeAt(i); hh = Math.imul(hh, 16777619) >>> 0; } }
    const msAll = Math.round(performance.now() - t0);
    const stats = { masts: masts.length, standsConsidered: order.length, byArea: by, rejected: why, uncovered: uncovered.length, cameras: cb, hash: hh.toString(16),
      paved: paved ? 'vector (tier-independent)' : 'ground map (tier resolution)', equipmentAreas: eqBB.length, envelopes: envBB.length, rules: RU, ms: msAll, msPrep, msHash, msLive: msAll, h: MAST_H,
      source: cache ? 'live (cache stale: inputs ' + cache.inputs + ')' : 'live', inputs: IH, src: 'inf' };
    if (dry) return { masts, stats, uncovered };
    this.masts = masts; this.mastStats = stats; this.mastUncovered = uncovered;
    this.dirty = true; return masts;
  }
  // (fix round 2, N1) the stand camera's subject points besides the target and the stop node (STAND_CAM.subjH heights): the
  // class reference parked with its nose wheel on the node (nose tip, wing tips, tail), every bridge's rotunda (as placed)
  // and docked cab (data cab). (The VDGS display was tried as a subject point too: 61 masts, 20 stands without one within
  // 120 m, the whole T2 north pier tip among them - so it is not one; the VDGS stays visible beside the masts.)
  camSubject(g) {
    const RT = TYPES[REF_TYPE[g.cls]] || TYPES.a320; const tip = standTip(g, RT); const H = STAND_CAM.subjH; const r2 = (v) => +v.toFixed(2);
    const fl = Math.hypot(g.dir[0], g.dir[1]) || 1, f = [g.dir[0] / fl, g.dir[1] / fl], lf = [f[1], -f[0]]; const at = (x, y) => [r2(tip[0] - f[0] * x + lf[0] * y), r2(tip[2] - f[1] * x + lf[1] * y)];
    const subj = [{ p: at(0, 0), y: H.tip }, { p: at(RT.L, 0), y: H.tail }];
    const w = RT.wing; if (w) { const yy = w.span / 2, xw = w.rootLE + yy * Math.tan((w.sweep || 25) * DEG) + (w.tipC || 1) / 2; subj.push({ p: at(xw, yy), y: H.wing }, { p: at(xw, -yy), y: H.wing }); }
    const B = g.sharesBridgesOf ? this.gates.find(o => o.name === g.sharesBridgesOf) || g : g;
    for (const b of this.bridgesOf(B)) { if (!b.rot && !b.m) this.prepBridge(B, b); if (b.rot) subj.push({ p: [+b.rot[0].toFixed(2), +b.rot[2].toFixed(2)], y: H.rotunda }); if (b.cabW) subj.push({ p: b.cabW.slice(0, 2), y: H.cab }); }
    return subj;
  }
  mastGeo(geo) {
    for (const M of this.masts || []) {
      const p = M.p, H = M.h, f3 = [M.face[0], 0, M.face[1]];
      geo.box([-0.8, 0, -0.8], [0.8, 0.45, 0.8], C.concrete, C.concreteE, m4.basis(f3, [0, 1, 0], [p[0], G, p[1]]));
      cyl(geo, [p[0], G + 0.45, p[1]], 0.36, 10, C.mast, C.steelE, 12); cyl(geo, [p[0], G + 10.45, p[1]], 0.3, 10, C.mast, C.steelE, 12); cyl(geo, [p[0], G + 20.45, p[1]], 0.24, H - 20.45, C.mast, C.steelE, 10);
      const Mh = m4.basis(f3, [0, 1, 0], [p[0], G + H, p[1]]);
      geo.box([-0.15, -0.12, -2.0], [0.15, 0.12, 2.0], C.steel, C.steelE, Mh);                       // head frame (two bars)
      geo.box([-0.15, -1.32, -2.0], [0.15, -1.08, 2.0], C.steel, C.steelE, Mh);
      geo.box([-1.1, -2.05, -2.1], [0.7, -1.95, 2.1], C.steel, C.steelE, Mh);                        // service platform
      // six lamp housings in two rows, aimed 25 deg down towards the apron (inf)
      const c = Math.cos(25 * DEG), s = Math.sin(25 * DEG); const fd = [f3[0] * c, -s, f3[2] * c], up = [f3[0] * s, c, f3[2] * s];
      for (const y of [0, -1.2]) for (const z of [-1.3, 0, 1.3]) {
        const o = m4.xform(Mh, [0.35, y, z]); const L = m4.basis(fd, up, o);
        geo.box([0, -0.38, -0.5], [0.42, 0.38, 0.5], C.dark, C.darkE, L);
        geo.box([0.42, -0.32, -0.44], [0.46, 0.32, 0.44], C.lamp, C.lampE, L);
        this.staticSprites.push({ p: m4.xform(L, [0.75, 0, 0]), c: [1.0, 0.74, 0.45], i: 650, s: 0.5, dir: fd, k: 1.2, night: true, mast: true }); // (warm white, high-pressure-sodium-like; inf)
      }
      // a faint all-round glow of the head (seen from behind and the side, where the aimed lamps are not visible)
      this.staticSprites.push({ p: m4.xform(Mh, [0.4, -0.6, 0]), c: [1.0, 0.74, 0.45], i: 45, s: 1.6, night: true, mast: true });
    }
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
    const T = TYPES[g.acType]; const dd = g.dock ? g.dock.dir : g.dir;
    const f = stD(dd), nose = g.dock ? stW(g.dock.nose, G) : standTip(g, T); const n2 = [nose[0], nose[2]], f2 = [f[0], f[2]];
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
    const add = (o, tk, pose, mg = 0.5) => { const T = TYPES[tk]; if (!T || !T.wing) return; const f = stD(pose ? pose.dir : o.dir), n = pose ? stW(pose.nose, G) : standTip(o, T);
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
      this.keepOut = this.aircraftFootprints ? this.aircraftFootprints() : []; this._idleBoxes = [];
      this.sprites = this.staticSprites;
      for (const g of this.gates) {
        // (sha3d: stands without a bridge of their own - remote stands and the alternative positions sharing a base
        // stand's bridge - get a post-mounted stand-number sign; remote ones the stairs / bus equipment, remoteGeo)
        if (!g.bridge) { this.remoteGeo(g, geo, sgn); continue; }
        if (!this.anims.has(g.id) && !this.settling(g)) { const Ps = this.bridgesOf(g).map(b => this.bridgeGeo(g, b, g.acType && this.docks(g, b) ? 1 : 0, geo, sgn)); if (g.acType) this.placeVehicles(g, Ps); }
        this.standGeo(g, geo, sgn);
      }
      this.idleGeo(); this.mastGeo(geo); // (fix round 1: staged idle stairs L4, floodlight masts M2)
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
    // (Phase 3 P3-E, additive: with the gate adapter attached - this._exact - the engine's own timers are retired at their
    // own due times first (advance) and times are integer ms, so a forward play and a resetTo() give the same state; the
    // static set is built per stand with caches (buildChunked). Both are off unless js/live/gate_sync.js turns them on.)
    if (this._exact) { now = Math.floor(now); this.advance(now); }
    const moving = this.step(now);
    if (this._chunked) {
      if (this.dirty || !this._chunkSet) { this.dirty = false; this.buildChunked(now, true); }
      else if (moving || this._hadDyn) this.build(now, false);
    } else
    if (this.dirty || !this.staticMesh) { this.dirty = false; this.build(now, true); }
    else if (moving || this._hadDyn) this.build(now, false);
    this._hadDyn = moving;
    const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
    const out = [];
    // (sha3d: objProg / objUniforms - the gates extension draws the bridges with its own instance of the object program so
    // that it can dim the glazed sides' night glow without touching the other buildings' uniforms)
    const OP = this.objProg || 'obj', OU = this.objUniforms || { uEmissiveBoost: 1 };
    if (this.staticMesh) out.push({ mesh: this.staticMesh, prog: OP, model: I4, bbox: this.bbox, castShadow: true, uniforms: OU });
    if (this._chunked && this._chunkSet) for (const G of this._chunkSet.groups) { // (P3-E chunked build: one mesh per stand group)
      if (G.mesh) out.push({ mesh: G.mesh, prog: OP, model: I4, bbox: G.bbox, castShadow: true, uniforms: OU });
      if (G.sign) out.push({ mesh: G.sign, prog: 'gsign', bbox: G.bbox, castShadow: false, noCull: true, nearOnly: true, uniforms: { uAtlas: this.atlas.tex } }); }
    if (this.dynMesh) out.push({ mesh: this.dynMesh, prog: OP, model: I4, bbox: this.bbox, castShadow: true, uniforms: OU });
    if (this.signMesh) out.push({ mesh: this.signMesh, prog: 'gsign', bbox: this.bbox, castShadow: false, noCull: true, nearOnly: true, uniforms: { uAtlas: this.atlas.tex } });
    if (this.dynSign) out.push({ mesh: this.dynSign, prog: 'gsign', bbox: this.bbox, castShadow: false, noCull: true, nearOnly: true, uniforms: { uAtlas: this.atlas.tex } });
    for (const k in this.vehicleMeshes) out.push({ mesh: this.vehicleMeshes[k], prog: 'objI', bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 }, shadowMaxCascade: 2 });
    return out;
  }
  // ground service vehicles around the parked aircraft (actual pose), with collision rejection: each vehicle's hull
  // (the extents of its mesh, js/world/gates.js buildVehicleMeshes) is sampled every 0.3 m with its heights against the
  // parked aircraft (fuselage cross-section, wings, engines, tail), the other parked aircraft, the bridges' solids, the
  // terminal outline and the vehicles already placed (review 2026-11-04: belt loaders were never placed - their test
  // box reached into the height-blind fuselage band - and the fuel truck's mesh overhung its test box)
  placeVehicles(g, Ps) {
    // (Phase 3 P3-E, additive: a cold stand - setService(g, 'cold') - has no GSE, stairs or bus; the chunked build of
    // the gate adapter takes the stand's placement from its cache. Neither is ever set by Phase 2 code.)
    if (g._service === 'cold') return;
    if (this._gseHit && this._gseHit(g, Ps)) return;
    // (sha3d: also at stands without a bridge - Ps empty: the type comes from the occupant; stairs + bus first)
    const T = Ps.length ? Ps[0].T : TYPES[g.acType]; if (!g.dock || !T || !T.wing) return;
    const R = rng(hash(g.id));
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
      for (const [x0, x1, z0, z1, y0, y1, cls] of boxes) { const nx = Math.max(1, Math.ceil((x1 - x0) / 0.3)), nz = Math.max(1, Math.ceil((z1 - z0) / 0.3));
        for (let i = 0; i <= nx; i++) for (let j = 0; j <= nz; j++) smp.push([...W(x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz), y0, y1, cls ? 0 : 0.3, !!cls, false]); }
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
    const HULL = { tug: [[-1.4, 1.4, -0.92, 0.92, 0, 2.1]], cart: [[-1.5, 1.5, -0.85, 0.85, 0, 1.6]], fuel: [[-3.8, 4.55, -1.3, 1.3, 0, 3.2]], gpu: [[-1.2, 1.2, -0.7, 0.7, 0, 1.5]], cone: [[-0.22, 0.22, -0.22, 0.22, 0, 0.75]], bus: BUS_HULL };
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
    // sha3d - remote stands (no bridge: AIP (mirror) AD 2.20 3.2.2.3 stand-off stands use marshaller guidance; bus boarding
    // inf, data remote[].service): self-propelled passenger stairs square to the door, the platform's front edge at the
    // widest skin over the door opening (T.dockHW, as the bridge cab) + 0.15 m - door 1L and the last left door (narrow
    // bodies, front + rear boarding) or door 2L (wide bodies) - and an apron bus beside the forward fuselage ahead of the
    // wing, parallel to it. Positions, the two-stair practice and the vehicles are inferred (no ZSSS ground-handling source).
    if (!Ps.length && g.remote && g.service !== 'business') {
      const left = v3.mul(r, -1), d = r; // (the stair faces the fuselage from the left side: forward = towards the aircraft)
      for (const D of stairDoors(T)) {
        const st = setting('stairs', D.S); if (!st) continue; const [sk, S2] = st; const sh = stairShape(S2);
        const front = v3.add(v3.sub(nose, v3.mul(f, D.x)), v3.mul(left, D.hw + 0.15)); const p = v3.sub(front, v3.mul(d, sh.xFront));
        const v = { M: m4.basis(d, [0, 1, 0], [p[0], G, p[2]]), p, d };
        if (ok(v, stairHull(S2), null, sk)) B[sk].push(inst(v.M, [0.9, 0.9, 0.9, 1]));
      }
      // apron bus (doors on its right side, towards the aircraft): beside the forward fuselage, ahead of the wing root,
      // parallel to it (one for a narrow body, two for a wide body; inf)
      const wide = T.R > 2.6; const x1 = T.dockX1 ?? T.doors[0];
      const busAt = (along, lat) => { const p = v3.add(v3.sub(nose, v3.mul(f, along)), v3.mul(left, lat)); return { M: m4.basis(f, [0, 1, 0], [p[0], G, p[2]]), p, d: f }; };
      let nb = 0; const nbus = wide ? 2 : 1;
      for (const lat of [T.R + 9, T.R + 11.5, T.R + 14, T.R + 17]) { for (const along of [x1 + 8, x1 + 5, x1 + 11, x1 + 2, x1 + 15, x1 + 20]) { if (nb >= nbus) break; if (put('bus', busAt(along, lat), [0.92, 0.93, 0.94, 1])) nb++; } if (nb >= nbus) break; }
    }
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
  // ============================================================ Phase 3 package E: gate and time adapter (additive)
  // docs/phase3/design.md §1.5 / §4.3 / §6.4 / §7.1, docs/phase3/gates_time.md. Nothing below runs unless the gate adapter
  // (js/live/gate_sync.js) or a test calls it; every Phase 2 path (DEBUG ?park=, the jobs) is unchanged.
  //  - now() / setTimeSource(fn): the engine's clock. Sim time (integer ms) while traffic runs, Date.now() otherwise
  //    (js/scene.js asks gateSys.now() for items()). The DEBUG park keeps Date.now() and is refused while traffic runs.
  //  - setService(g, 'turn' | 'cold', t): a cold stand keeps its aircraft and docked bridges but has no GSE, stairs or bus.
  //  - dockAt / undockAt / pushAt: the three engine calls of a turnaround (setOccupant with the arrival; undockEarly at the
  //    sim's undock time; setOccupant(g, null) at push start, with hurryUndock for a retraction still running), each also
  //    in a snapped form (animate = false) for resetTo().
  //  - advance(t): retires every engine timer (dock / undock animations, rest-height settles, rest-pose parks, departure
  //    holds, announced arrivals) at its own due time, the first integer ms at which step() would retire it, so the state
  //    no longer depends on when frames happen to come (with integer-ms frame times a forward play and a jump agree).
  //  - resetTo(t, occupants): clears every runtime state and replays the occupants' engine calls: calls older than
  //    t - RESET_HORIZON_S snapped (their animations and timers are long over), the rest animated at their own sim times
  //    with advance() between them - the state of a forward play at t (docking, docked, early, pushing, empty).
  //  - buildChunked(now, full) (with setChunked(true)): the static set per stand, cached by a signature of everything the
  //    stand's geometry and GSE depend on, the GSE also in a small per-stand LRU, the stands' chunks merged in groups of
  //    CHUNK_GROUP stands (one mesh per group): a change rebuilds only that stand and its neighbours (review M7).
  now() { const f = this._timeSrc; if (f) { const t = f(); if (Number.isFinite(t)) return Math.floor(t); } return Date.now(); }
  setTimeSource(fn) { this._timeSrc = typeof fn === 'function' ? fn : null; this._exact = !!this._timeSrc; return this._exact; }
  trafficRunning() { return !!this._timeSrc; }
  serviceOf(g) { return g && g._service === 'cold' ? 'cold' : 'turn'; }
  setService(g, mode, t = this.now()) {
    if (!g) return false; const m = mode === 'cold' ? 'cold' : 'turn';
    if (this.serviceOf(g) === m) return false;
    g._service = m; g._serviceT = t; this.dirty = true; return true;
  }
  dockAt(g, typeKey, t, pose, icao = null, opts = {}, animate = true) {
    if (!g || !typeKey || !TYPES[typeKey]) return false;
    this.setOccupant(g, typeKey, !!animate, t, pose, icao, { freighter: !!opts.freighter });
    g._service = opts.service === 'cold' ? 'cold' : 'turn'; return true;
  }
  undockAt(g, t, animate = true) {
    if (!g || !g.bridge || !g.acType) return 0;
    if (animate) return this.undockEarly(g, t);
    const e = { type: g.acType, pose: g.dock, icao: g.dockType, freighter: g.dockCargo, t };
    this.setOccupant(g, null, false, t, null, null, { early: true }); g._early = e; return 0;
  }
  pushAt(g, t, animate = true) {
    if (!g) return 0; const was = !!(g.acType || g._early);
    this.setOccupant(g, null, !!animate, t, null, null);
    g._early = null; g._service = null;
    return was && animate ? this.hurryUndock(g, 0, t) : 0; // (a retraction still running finishes at the maximum rates)
  }
  // the first integer ms at which step() retires the engine's next timer (null: none; this._now: one pending now)
  nextDue() {
    let d = Infinity;
    const first = (ok, m) => { let x = Math.ceil(m); while (ok(x - 1)) x--; while (!ok(x)) x++; return x; };
    for (const a of this.anims.values()) d = Math.min(d, a.dur > 0 ? first((n) => Math.min(1, Math.max(0, (n - a.t0) / a.dur)) >= 1, a.t0 + a.dur) : this._now ?? 0);
    if (this.settles) for (const s of this.settles.values()) d = Math.min(d, first((n) => Math.min(1, Math.max(0, (n - s.t0) / s.dur)) >= 1, s.t0 + s.dur));
    if (this.parks) for (const p of this.parks.values()) d = Math.min(d, first((n) => n - p.t0 >= p.total * 1000, p.t0 + p.total * 1000));
    if (this._holdG) for (const g of this._holdG) d = Math.min(d, g._parkHold ? Math.ceil(g._parkHold.until) : this._now ?? 0);
    if (this._incG) for (const g of this._incG) d = Math.min(d, g._incoming ? Math.ceil(g._incoming.until) : this._now ?? 0);
    if (this._parkG && this._parkG.length) d = Math.min(d, this._now ?? 0);
    return d === Infinity ? null : d;
  }
  advance(t) {
    let last = null, same = 0;
    for (let i = 0; i < 20000; i++) {
      const d = this.nextDue(); if (d == null || d > t) break;
      if (d === last && ++same > 50) { this._advanceStuck = (this._advanceStuck || 0) + 1; break; } // (guard: never loops)
      if (d !== last) same = 0; last = d; this.step(Math.max(d, this._now ?? d));
    }
  }
  // occupants: [{gate (object or id), typeKey, icao, pose {nose: [x, z], dir}, freighter, service, state: 'empty' | 'docking'
  //   | 'docked' | 'early' | 'pushing', tDock, tUndock, tPush (ms, sim; null: before the day / not known), prev: {typeKey,
  //   icao, pose, freighter, tDock, tUndock, tPush} - the departed occupant whose holds may still run}]
  resetTo(t, occupants = [], opts = {}) {
    const p0 = (typeof performance !== 'undefined' ? performance : Date).now();
    t = Math.floor(t); const H = (opts.horizonS ?? RESET_HORIZON_S) * 1000, tH = t - H, tLong = t - 48 * 3600e3;
    // 1. every runtime state the forward play builds up (design §1.5, review H1)
    this.anims.clear(); if (this.settles) this.settles.clear(); if (this.parks) this.parks.clear();
    this._parkG = []; if (this._holdG) this._holdG.clear(); if (this._incG) this._incG.clear();
    for (const g of this.gates) {
      g.acType = null; g.empty = true; g.dock = null; g.dockType = null; g.dockCargo = false; g._lastType = null;
      g._early = null; g._parkHold = null; g._incoming = null; g._service = null; g._serviceT = null;
      for (const b of this.bridgesOf(g)) { if (!b.m) continue; if ((b.hRest ?? b.h0) !== b.h0 && b._plans) b._plans.clear(); b.hRest = b.h0; b._parkQ = null; }
    }
    this._now = tLong;
    // 2. the engine calls of every occupant (and of the departed one, for its holds), in (t, kind, stand) order
    const byId = this._byId || (this._byId = new Map(this.gates.map(g => [g.id, g])));
    const calls = []; let bad = 0;
    const add = (tc, kind, g, o) => { if (kind !== 'dock' && tc == null) return; calls.push({ t: tc == null ? tLong : Math.floor(tc), kind, g, o, i: calls.length }); };
    // (an early stand without its undock time: undocked long ago; a pushing one without its push time: pushes now)
    const life = (g, o, st) => { add(o.tDock, 'dock', g, o);
      if (st === 'early' || st === 'pushing' || st === 'gone') { const tu = o.tUndock ?? (st === 'early' ? tLong + 1 : null); if (tu != null) add(tu, 'undock', g, o); }
      if (st === 'pushing' || st === 'gone') add(o.tPush ?? t, 'push', g, o); };
    for (const o of occupants || []) {
      const g = o && (typeof o.gate === 'object' ? o.gate : byId.get(o.gate)); if (!g) { bad++; continue; }
      if (o.prev && o.prev.typeKey && TYPES[o.prev.typeKey] && o.prev.tPush != null) life(g, o.prev, 'gone');
      if (o.state && o.state !== 'empty' && o.typeKey && TYPES[o.typeKey]) life(g, o, o.state); else if (o.state && o.state !== 'empty') bad++;
    }
    const gi = this._gi || (this._gi = new Map(this.gates.map((g, i) => [g, i])));
    calls.sort((a, b) => (a.t - b.t) || (EV_ORDER[a.kind] - EV_ORDER[b.kind]) || (gi.get(a.g) - gi.get(b.g)) || (a.i - b.i));
    let snapped = 0, animated = 0;
    for (const c of calls) {
      if (c.t > t) continue;
      const anim = c.t >= tH;
      this.advance(c.t); this.step(Math.max(c.t, this._now ?? c.t));
      if (c.kind === 'dock') this.dockAt(c.g, c.o.typeKey, c.t, c.o.pose || null, c.o.icao || null, { freighter: c.o.freighter }, anim);
      else if (c.kind === 'undock') this.undockAt(c.g, c.t, anim);
      else this.pushAt(c.g, c.t, anim);
      if (anim) animated++; else snapped++;
    }
    this.advance(t); this.step(Math.max(t, this._now ?? t));
    // 3. the service of every occupied stand (a field: GSE only, no timer)
    for (const o of occupants || []) { const g = o && (typeof o.gate === 'object' ? o.gate : byId.get(o.gate)); if (g && g.acType && o.service === 'cold') g._service = 'cold'; }
    this.dirty = true;
    const ms = (typeof performance !== 'undefined' ? performance : Date).now() - p0;
    return (this.lastReset = { t, ms: +ms.toFixed(1), calls: calls.length, snapped, animated, bad, horizonS: H / 1000 });
  }
  // the aircraft the engine knows at the stands (occupants and early departures): footprints for the GSE keep-out
  occupantFootprints() {
    const out = [];
    for (const g of this.gates) { const e = g._early; const tk = g.acType || (e && e.type); const pose = g.acType ? g.dock : e && e.pose; const T = tk && TYPES[tk];
      if (!T || !pose) continue; out.push(footprint([pose.nose[0], G, pose.nose[1]], [pose.dir[0], 0, pose.dir[1]], T, g)); }
    return out;
  }
  // ------------------------------------------------------------ chunked static build (P3-E, review M7)
  setChunked(on) {
    on = !!on; if (on === !!this._chunked) return on;
    this._chunked = on; this._gseHit = null;
    if (on) { if (this.staticMesh) { this.staticMesh.dispose(); this.staticMesh = null; } if (this.signMesh) { this.signMesh.dispose(); this.signMesh = null; } }
    else if (this._chunkSet) { for (const G of this._chunkSet.groups) { if (G.mesh) G.mesh.dispose(); if (G.sign) G.sign.dispose(); } this._chunkSet = null; this._chunks = null; this._gse = null; }
    this.dirty = true; return on;
  }
  // place every deferred GSE now (a render job's screenshot; never needed for correctness)
  flushGse(now = this.now()) { const b = this.gseBudgetMs; this.gseBudgetMs = Infinity; try { if (this._gsePending && this._gsePending.size) { this.dirty = true; this.items(now); } } finally { this.gseBudgetMs = b; } return this._gsePending ? this._gsePending.size : 0; }
  // everything stand g's static chunk depends on (geometry: its bridges' static poses, the VDGS face; GSE: the occupant,
  // its pose and service, the own bridges' solids, the other aircraft near it), exact (full float text)
  standSig(g) {
    let s = (g.acType || '') + '|' + (g._lastType || '') + '|' + (g.dockType || '') + '|' + (g.dockCargo ? 1 : 0) + '|' + (g._service || '') + '|';
    if (g.dock) s += g.dock.nose[0] + ',' + g.dock.nose[1] + ',' + g.dock.dir[0] + ',' + g.dock.dir[1];
    if (g.bridge) { s += this.anims.has(g.id) || this.settling(g) ? '|A' : '|S';
      for (const b of this.bridgesOf(g)) { const q = b._parkQ; s += '|' + (b.hRest ?? b.h0) + (q ? ':' + q.a + ',' + q.e + ',' + q.t + ',' + q.h : ''); } }
    if (g.acType) s += '|K' + this.keepSig(g);
    return s;
  }
  keepSig(g) {
    let s = '';
    for (const o of this.keepNear(g)) s += o.nose[0] + ',' + o.nose[1] + ',' + o.f[0] + ',' + o.f[1] + ',' + this.typeKeyOf(o.T) + ';';
    return s;
  }
  // the keep-out footprints that can touch stand g's ground equipment: those whose planform box (hitsAircraft cannot hit
  // outside it) overlaps the box every GSE hull of g lies in (its aircraft's planform grown by 12 m fore and aft and to
  // max(span / 2, R + 18) + 8 m either side: belt loaders, baggage train, catering, fuel, GPU, cones, stairs, buses) - the
  // same placement as with the whole list
  keepNear(g) {
    const T = TYPES[g.acType]; const pose = g.dock; if (!T || !pose || !this.keepOut || !this.keepOut.length) return [];
    const span = T.wing ? T.wing.span / 2 : 18;
    const A = rectBox(pose.nose, pose.dir, -12, T.L + 12, Math.max(span, T.R + 18) + 8);
    return this.keepOut.filter(o => { if (o.gate === g) return false; const B = o._box || (o._box = fpBox(o)); return B[0] <= A[2] && B[2] >= A[0] && B[1] <= A[3] && B[3] >= A[1]; });
  }
  standChunk(g) {
    const geo = new Geo(), sgn = newSignGeo(); const VB = {}; for (const k in this.vehicleMeshes) VB[k] = [];
    const keepV = this.vehicleBuckets, keepS = this.sprites; this.vehicleBuckets = VB; this.sprites = [];
    // (the keep-out list cut to the aircraft within 200 m: hitsAircraft cannot hit beyond an aircraft's own extent, < 90 m
    // from its nose, and every vehicle stays within ~90 m of this stand's nose - the same placement, about 10x faster)
    const keepK = this.keepOut; this.keepOut = this.keepNear(g);
    let spr;
    try {
      if (!g.bridge) this.remoteGeo(g, geo, sgn);
      else { if (!this.anims.has(g.id) && !this.settling(g)) { const Ps = this.bridgesOf(g).map(b => this.bridgeGeo(g, b, g.acType && this.docks(g, b) ? 1 : 0, geo, sgn)); if (g.acType) this.placeVehicles(g, Ps); }
        this.standGeo(g, geo, sgn); }
    } finally { spr = this.sprites; this.vehicleBuckets = keepV; this.sprites = keepS; this.keepOut = keepK; }
    const S = sgn.pos.length ? { pos: new Float32Array(sgn.pos), nrm: new Float32Array(sgn.nrm), uv: new Float32Array(sgn.uv), extra: new Float32Array(sgn.ext), idx: new Uint32Array(sgn.idx) } : null;
    return { geo: geo.nv ? geo.data() : null, sgn: S, veh: VB, spr };
  }
  buildChunked(now, full) {
    if (!full) return this.build(now, false);
    const p0 = (typeof performance !== 'undefined' ? performance : Date).now();
    this.keepOut = this.aircraftFootprints ? this.aircraftFootprints() : []; this._idleBoxes = [];
    const C = this._chunks || (this._chunks = new Map()); const LRU = this._gse || (this._gse = new Map());
    if (!this._chunkSet) {   // stand groups: area, then stand order; CHUNK_GROUP stands per mesh
      const order = this.gates.slice().sort((a, b) => (a.area || '').localeCompare(b.area || '') || (parseInt(a.name, 10) - parseInt(b.name, 10)) || a.name.localeCompare(b.name));
      const groups = []; for (let i = 0; i < order.length; i += CHUNK_GROUP) groups.push({ gates: order.slice(i, i + CHUNK_GROUP), ver: '', mesh: null, sign: null, bbox: this.bbox });
      this._chunkSet = { groups, mast: null, mastKey: null };
    }
    let rebuilt = 0, gseHits = 0, gsePlaced = 0, deferred = 0; const P0 = (typeof performance !== 'undefined' ? performance : Date);
    // the GSE of a stand from its LRU (key: the occupant, pose, service, the own bridges' state, the aircraft around); past
    // the build's GSE budget (gseBudgetMs) a placement is deferred to the next build: the stand's geometry is current at
    // once, its vehicles follow a frame later (a cold cache - the first build, a long jump - fills over several frames)
    let curKey = null, skip = false; const budget = this.gseBudgetMs ?? GSE_BUDGET_MS; let spent = 0;
    const pend = this._gsePending || (this._gsePending = new Set()); pend.clear();
    this._gseHit = (g) => { const hit = curKey && LRU.get(curKey); if (hit) { for (const k in hit) for (const v of hit[k]) this.vehicleBuckets[k].push(v); gseHits++; return true; } return skip; };
    for (const G of this._chunkSet.groups) {
      if (G === this._chunkSet.mastG) continue;
      let ver = '';
      for (const g of G.gates) {
        const sig = this.standSig(g); let c = C.get(g.id);
        if (c && c.sig === sig + '#gse-pending' && !LRU.has(g.id + '#' + sig) && (spent >= budget || (spent > 0 && spent + ((this._gseCost && this._gseCost.get(g.id)) ?? 6) > budget))) { pend.add(g.id); deferred++; }   // (still deferred: keep its chunk)
        else if (!c || c.sig !== sig) {
          curKey = g.acType ? g.id + '#' + sig : null;
          // (over budget: no GSE this build; a placement whose last measured cost would overrun the budget waits unless it is
          // the build's first one)
          const est = (this._gseCost && this._gseCost.get(g.id)) ?? 6;
          skip = !!curKey && !LRU.has(curKey) && g._service !== 'cold' && (spent >= budget || (spent > 0 && spent + est > budget));
          const t1 = P0.now();
          c = this.standChunk(g); c.ver = (this._chunkVer = (this._chunkVer || 0) + 1); C.set(g.id, c); rebuilt++;
          if (skip) { c.sig = sig + '#gse-pending'; pend.add(g.id); deferred++; }
          else { c.sig = sig;
            if (curKey && !LRU.has(curKey)) { const dt = P0.now() - t1; spent += dt; (this._gseCost || (this._gseCost = new Map())).set(g.id, dt); LRU.set(curKey, c.veh); gsePlaced++;
              const mine = [...LRU.keys()].filter(k => k.startsWith(g.id + '#')); if (mine.length > GSE_LRU) LRU.delete(mine[0]); } }
          curKey = null; skip = false;
        }
        ver += c.ver + ',';
      }
      if (ver !== G.ver) { G.ver = ver; if (G.mesh) G.mesh.dispose(); if (G.sign) G.sign.dispose(); const cs = G.gates.map(g => C.get(g.id));
        const M = concatGeo(cs.map(c => c.geo)); G.mesh = M ? new Mesh(M) : null; G.bbox = M ? M.bbox : this.bbox;
        const S = concatGeo(cs.map(c => c.sgn)); G.sign = S ? new Mesh(S) : null; }
    }
    this._gseHit = null;
    // the floodlight masts (fixed once placed) and the staged idle stairs (cheap; they depend on every stand's occupancy)
    const mk = (this.mastStats && this.mastStats.hash) + ':' + (this.masts || []).length;
    if (this._chunkSet.mastKey !== mk) { const geo = new Geo(); const keep = this.staticSprites; this.staticSprites = []; this.mastGeo(geo); const spr = this.staticSprites; this.staticSprites = keep;
      if (this._chunkSet.mast && this._chunkSet.mast.mesh) this._chunkSet.mast.mesh.dispose(); const D = geo.nv ? geo.data() : null;
      this._chunkSet.mast = { mesh: D ? new Mesh(D) : null, bbox: D ? D.bbox : this.bbox, spr }; this._chunkSet.mastKey = mk;
      if (!this._chunkSet.groups.includes(this._chunkSet.mastG)) { this._chunkSet.mastG = { gates: [], ver: 'masts', mesh: null, sign: null, bbox: this.bbox }; this._chunkSet.groups.push(this._chunkSet.mastG); }
      this._chunkSet.mastG.mesh = this._chunkSet.mast.mesh; this._chunkSet.mastG.bbox = this._chunkSet.mast.bbox; }
    this.vehicleBuckets = {}; for (const k in this.vehicleMeshes) this.vehicleBuckets[k] = [];
    const spr = [];
    for (const g of this.gates) { const c = C.get(g.id); if (!c) continue; for (const k in c.veh) for (const v of c.veh[k]) this.vehicleBuckets[k].push(v); for (const s of c.spr) spr.push(s); }
    this.staticSprites = spr.concat(this._chunkSet.mast ? this._chunkSet.mast.spr : []); this.sprites = this.staticSprites;
    this.idleGeo();
    for (const k in this.vehicleBuckets) { const list = this.vehicleBuckets[k]; this.vehicleMeshes[k].setInstances(new Float32Array(list.flat()), list.length); }
    if (pend.size) this.dirty = true;   // (the deferred placements: next build)
    this.lastBuild = { ms: +((typeof performance !== 'undefined' ? performance : Date).now() - p0).toFixed(1), rebuilt, gseHits, gsePlaced, deferred, groups: this._chunkSet.groups.length };
    return this.build(now, false);
  }
  typeKeyOf(T) { if (!this._tk) { this._tk = new Map(); for (const [k, t] of Object.entries(TYPES)) if (t) this._tk.set(t, k); } return this._tk.get(T) || ''; }
}
// (Phase 3 P3-E) resetTo(): calls older than this are snapped (their animations, settles, parks and holds are over: the
// longest chain - an undock, its rest-height settle, the 180 s departure hold and the rest-pose return after it - is about
// 5 min; inf); the order of engine calls at one sim ms (gate_sync.js applies events in the same order); the stands per
// mesh of the chunked build; the GSE placements kept per stand (a scrub back and forth re-uses them); the GSE placement
// time one build may spend before it defers the rest to the next frames (one placement is 2-12 ms here). All inf.
export const RESET_HORIZON_S = 1200;
export const EV_ORDER = { dock: 0, undock: 1, push: 2, service: 3 };
const CHUNK_GROUP = 8, GSE_LRU = 3, GSE_BUDGET_MS = 12;
// world [x0, z0, x1, z1] of the rectangle x in [a, b] metres behind a nose at n (heading d), |y| <= w to either side
function rectBox(n, d, a, b, w) {
  const r = [-d[1], d[0]]; let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9;
  for (const x of [a, b]) for (const y of [-w, w]) { const px = n[0] - d[0] * x + r[0] * y, pz = n[1] - d[1] * x + r[1] * y; x0 = Math.min(x0, px); x1 = Math.max(x1, px); z0 = Math.min(z0, pz); z1 = Math.max(z1, pz); }
  return [x0, z0, x1, z1];
}
// the box hitsAircraft(fp, ...) can return true in: fuselage, wings, engines, rear engines, tailplane (+ its margins)
function fpBox(fp) {
  const T = fp.T; let w = T.R + 0.6; if (T.wing) w = Math.max(w, T.wing.span / 2 + 0.5);
  for (const e of T.eng || []) w = Math.max(w, Math.abs(e.z) + e.r + 0.8); if (T.rear) w = Math.max(w, T.rear.z + T.rear.r + 0.8); if (T.hstab) w = Math.max(w, T.hstab.span / 2 + 0.5);
  let b = T.L + 1; for (const e of T.eng || []) b = Math.max(b, (T.wing ? T.wing.rootLE + Math.abs(e.z) * Math.tan((T.wing.sweep || 25) * Math.PI / 180) : T.L * 0.4) - (e.fwd || 3) + e.len + 1.5);
  if (T.wing) b = Math.max(b, T.wing.rootLE + (T.wing.span / 2) * Math.tan((T.wing.sweep || 25) * Math.PI / 180) + T.wing.rootC + 0.5);
  if (T.rear) b = Math.max(b, T.rear.x + T.rear.len + 1);
  let a = -1; for (const e of T.eng || []) a = Math.min(a, (T.wing ? T.wing.rootLE + Math.abs(e.z) * Math.tan((T.wing.sweep || 25) * Math.PI / 180) : T.L * 0.4) - (e.fwd || 3) - 1.5);
  return rectBox(fp.nose, fp.f, a - 0.5, b + 0.5, w + 0.5);
}
// merge per-stand geometry ({pos, nrm, uv, extra, idx[, col, bbox]} typed arrays, or null) into one mesh data object
function concatGeo(list) {
  let nv = 0, ni = 0, col = false; for (const d of list) if (d && d.pos.length) { nv += d.pos.length / 3; ni += d.idx.length; if (d.col) col = true; }
  if (!nv) return null;
  const pos = new Float32Array(nv * 3), nrm = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), extra = new Float32Array(nv * 4), idx = new Uint32Array(ni), C = col ? new Float32Array(nv * 4) : null;
  const bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]; let ov = 0, oi = 0;
  for (const d of list) {
    if (!d || !d.pos.length) continue; const n = d.pos.length / 3;
    pos.set(d.pos, ov * 3); nrm.set(d.nrm, ov * 3); uv.set(d.uv, ov * 2); extra.set(d.extra, ov * 4); if (C) { if (d.col) C.set(d.col, ov * 4); else C.fill(1, ov * 4, (ov + n) * 4); }
    for (let i = 0; i < d.idx.length; i++) idx[oi + i] = d.idx[i] + ov;
    const b = d.bbox; if (b) for (let k = 0; k < 3; k++) { bb[k] = Math.min(bb[k], b[k]); bb[k + 3] = Math.max(bb[k + 3], b[k + 3]); }
    else for (let i = 0; i < d.pos.length; i += 3) for (let k = 0; k < 3; k++) { bb[k] = Math.min(bb[k], d.pos[i + k]); bb[k + 3] = Math.max(bb[k + 3], d.pos[i + k]); }
    ov += n; oi += d.idx.length;
  }
  const out = { pos, nrm, uv, extra, idx, bbox: bb }; if (C) out.col = C; return out;
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
