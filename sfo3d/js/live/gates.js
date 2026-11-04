// Contact-gate equipment driven by live occupancy:
//  - apron-drive passenger boarding bridges (PBB) built from the stand data (data/sfo_stands.json, OSM + NAIP; fields in
//    docs/research/stands_rebuild.md §8): fixed walkway along the mapped polyline (walkW) on columns, rotunda on its
//    pedestal at the mapped rotunda (rotundaW, drum radius <= rotundaMaxR), rotunda corridor, two or three TELESCOPING
//    tunnel sections (they slide inside each other; lengths fixed, only their overlap changes), drive column with wheel
//    bogie on the outer tunnel, pre-conditioned-air unit, cab bubble with the rotating cab, bellows closure, service
//    landing + stair, floodlight, beacon, gate-number signs on the tunnel
//  - stand equipment: gate identification sign and visual docking guidance display (VDGS), placed on the stand
//    centreline where no bridge part reaches it in any pose (rest, docking path, docked)
//  - ground service vehicles placed around the actually parked aircraft, rejected if they would hit the aircraft,
//    a bridge (its real solids) or a neighbouring aircraft
//
// Bridge kinematics (sources):
//  * Oshkosh AeroTech, "Jetway Glass & Steel Truss Passenger Boarding Bridges" sell sheet (2025), cached
//    refs/cache/sun_night/oshkosh_jetway_steelglass.pdf (https://oshkoshaerotech.com/hubfs/images/Jetway%20SteelGlass_
//    Truss_Sell-Sheet_2025.pdf): models AT2 (two tunnels) / AT3 (three tunnels) "41/55" ... "72/150"; fully retracted /
//    fully extended lengths "from the center of the rotunda to the end of the cab spacer", operational retraction /
//    extension "from the center of the rotunda to the center of the cab pivot" (table PBB below); rotunda swing 175 deg
//    (87.5 cw / 87.5 ccw of centerline); cab rotation 125 deg (92.5 cw / 32.5 ccw), optional 185 deg; cab rotation speed
//    145 deg/min; vertical rate 3.5 ft/min (1.09 m/min); horizontal travel 0-90 ft/min (0-27 m/min); service door,
//    landing and stairs: option C/D "right/left-hand side of outboard telescoping tunnel aft of cab bubble"; minimum
//    interior cab width 3.10 m. Pivot -> end of cab spacer = fully retracted - operational retraction (2.378 m AT2,
//    2.225 m AT3). Which bridge model each SFO bridge is (`model`, `ext_range`) is the stand data's inference.
//  * FAA AC 150/5220-21C "Aircraft Boarding Equipment" (2012), cached refs/cache/pbb/AC_150_5220-21C.pdf: §3.3.b
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
//    rest. The engine holds a departing aircraft until extension(g) is 0.
//  * Rest pose: the data's `stowW` (tunnel end = cab pivot at rest, clear of every accepted type's envelope + 1 m, of
//    the other bridges at rest and docked, of the building; cab straight on the tunnel).
//  * Upper-deck bridges (`bridges_upper`, A6 / A11 / G13) dock the A380's U1L door: Airbus A380 Aircraft
//    Characteristics (AC380, Dec 01/25, refs/cache/acap/airbus_AC_A380_20251201.pdf): U1L 20.94 m from the nose
//    (FIGURE-2-7-0-991-002), sill 7.87-7.89 m at MRW (FIGURE-2-3-0-991-001).
// Inferred (no source; stated where used): the terminal's departure level at the fixed walkways (5.4 m: the terminal model's
// ramp level is 0-5 m, js/live/terminals.js), tunnel overlaps (1.0 m) and retracted stagger (0.3 m), drive-column
// position on the outer tunnel, final approach speed, section cross-sections (inside the AC's minimum interior sizes).
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { rng, m4, v3 } from '../math.js';
import { stToWorld, worldToST, GROUND_Y } from '../geo.js';
import { TYPES, ICAO_TYPES } from '../aircraft/types.js';
import '../aircraft/fit.js'; // fits the imported models to the published dimensions: T.dockX1/2, T.dockSill/2, T.dockHW
import { inst, buildVehicleMeshes, BELT_SILL, beltShape } from '../world/gates.js';
import { makeAtlas } from './signs.js';
import { familyOf } from './traffic.js';
import { STANDS } from '../../data/sfo_stands.js';
import { BUILDINGS } from '../../data/sfo_buildings.js';

// terminal outlines the bridges must stay out of: ramp-level complex and the piers / halls (js/live/terminals.js builds
// them from these rings; the elevated sky-bridge walkways are left out - fixed walkways run under / beside them)
const BLD = [], BLD_H = []; // (BLD_H: wall top above the apron - ramp-level complex 5 m, piers / halls their roof h)
for (const r of (BUILDINGS && BUILDINGS.complex) || []) { BLD.push(r); BLD_H.push(5.0); }
for (const p of (BUILDINGS && BUILDINGS.parts) || []) if (p.kind !== 'walkway') for (const r of p.rings) { BLD.push(r); BLD_H.push(p.h || 5.0); }
const NBLD = BLD.length; // + the elevated sky bridges (only for the rotunda drum, which reaches their height)
for (const p of (BUILDINGS && BUILDINGS.parts) || []) if (p.kind === 'walkway') for (const r of p.rings) BLD.push(r);
const BLD_BB = BLD.map(r => { let a = 1e9, b = 1e9, c = -1e9, d = -1e9; for (const p of r) { a = Math.min(a, p[0]); c = Math.max(c, p[0]); b = Math.min(b, p[1]); d = Math.max(d, p[1]); } return [a, b, c, d]; });
function inRing(x, z, r) { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[i], b = r[j]; if (((a[1] > z) !== (b[1] > z)) && (x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0])) c = !c; } return c; }
function inBuilding(x, z, all = false) { for (let i = 0; i < (all ? BLD.length : NBLD); i++) { const bb = BLD_BB[i]; if (x < bb[0] || x > bb[2] || z < bb[1] || z > bb[3]) continue; if (inRing(x, z, BLD[i])) return true; } return false; }
function nearestBuilding(x, z) { // nearest outline point incl. the sky bridges: {d (0 inside), p}
  let d = 1e9, P = null;
  for (let i = 0; i < BLD.length; i++) { const bb = BLD_BB[i]; if (x < bb[0] - d || x > bb[2] + d || z < bb[1] - d || z > bb[3] + d) continue; const r = BLD[i];
    for (let k = 0, j = r.length - 1; k < r.length; j = k++) { const a = r[j], b = r[k]; const ex = b[0] - a[0], ez = b[1] - a[1]; const L2 = ex * ex + ez * ez || 1; const t = clampN(((x - a[0]) * ex + (z - a[1]) * ez) / L2, 0, 1); const q = [a[0] + ex * t, a[1] + ez * t]; const dd = Math.hypot(q[0] - x, q[1] - z); if (dd < d) { d = dd; P = q; } } }
  return { d: inBuilding(x, z, true) ? 0 : d, p: P, inside: inBuilding(x, z, true) };
}
function distBuilding(x, z) { return nearestBuilding(x, z).d; }
// top of the terminal wall the point (x, z) lies in (0: none) - js/live/terminals.js: complex 0-5 m, parts 5 m - h
function wallTop(x, z) { let h = 0; for (let i = 0; i < NBLD; i++) { const bb = BLD_BB[i]; if (x < bb[0] || x > bb[2] || z < bb[1] || z > bb[3]) continue; if (inRing(x, z, BLD[i])) h = Math.max(h, BLD_H[i]); } return h; }

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
const DEPARTURE_LEVEL = 5.4;                              // m above the apron: terminal upper floor (ramp-level walls 0-5 m + slab, js/live/terminals.js; inferred)
const OVERLAP = 1.0, STAGGER = 0.3;                       // m, minimum tunnel overlap at full extension / retracted stagger (inferred)
// sign convention of the sheet's "cw" in the data (data/sfo_stands.json cab_convention, inferred by the stand builder)
const CW = (STANDS.cab_convention && /^clockwise/.test(STANDS.cab_convention.cw_is || '')) ? 1 : -1;
// A380 upper deck door U1L (Airbus AC380 Dec 01/25, see header); rendered fuselage half width at the door from the fitted
// type (T.dockX3 / T.dockSill3 / T.dockHW3 are used instead when js/aircraft/fit.js provides them)
const A388_U1 = { x: 20.94, sill: 7.88 };
const DOCK_DELAY = 12;                                    // s after the engine reports the aircraft at rest
const DOCK_TIME = 22, UNDOCK_TIME = 16;                   // s, fallback only (paths are timed from the sheet's rates)
// exterior cross-sections (width, height) of tunnel sections A (rotunda) .. C (cab): AC 150/5220-21C §3.5.a(1) minimum
// interior 50 in corridor / 80 in height; sheet minimum A tunnel interior 1.47 x 2.13 m; exterior inferred
const SEC_WH = { 2: [[2.55, 2.85], [2.82, 3.12]], 3: [[2.55, 2.85], [2.68, 2.98], [2.82, 3.12]] };
const WALK_W = 2.6, WALK_H = 3.0, CAB_W = 3.6, CAB_BACK = 1.6;
// minimum rotunda drum radius: half the rotunda corridor (2.4 m) / tunnel A exterior (2.55 m, SEC_WH) + 0.2 m (inferred)
const DRUM_MIN = 1.5;

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

// representative (largest common) aircraft of a stand class (only used for a stand without stand data)
const REF_TYPE = { B: 'crj9', C: 'b38m', CL: 'a21n', D: 'b763', E: 'b789', EL: 'b77w', F: 'a388' };
const ICAO_OF = {}; for (const [icao, k] of Object.entries(ICAO_TYPES)) if (!ICAO_OF[k]) ICAO_OF[k] = icao;
// Where the bridge cab meets the aircraft (js/aircraft/fit.js): door `which` = 1 is door 1L, 2 the door the second bridge
// of a wide-body stand docks to (T.dock2, from the manufacturers' documents), 3 the A380 upper-deck door U1L (upper-deck
// bridges). x = door CENTRE station from the nose tip (the rendered door of the imported model where it has one, else the
// published centre), cab floor = published door sill above the ground, and the cab stops at the rendered fuselage side at
// door height (T.dockHW).
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
  const d = v3.add(v3.sub(nose, v3.mul(f, x)), v3.mul(left, (T.dockHW ?? T.R) + 0.15)); d[1] = G + sill;
  return { door: d, left };
}
export { doorOf, acHit, boxHitsAc, PBB };

// ---------------------------------------------------------------- aircraft solid for the bridge-path test
// (x metres behind the nose, y to the right, heights above the apron). The fuselage tapers over the nose (types.js Ln)
// as the rendered airframe does; wing / tailplane / engines as the ground-physics planform with their heights.
// ell: the fuselage as its elliptical cross-section (half width x crown - centre line) instead of the enclosing box -
// for the ground vehicles that reach under its lower lobe (belt loaders at the cargo doors)
function acHit(T, x, y, lo, hi, mg, ell = false) {
  const R = T.R, L = T.L, Hc = T.Hc;
  if (x > -mg && x < L + mg) {
    const Ln = T.Ln || 4; const xx = clampN(x, 0, Ln); let hw = x < Ln ? R * Math.sqrt(Math.max(0, 1 - (1 - xx / Ln) ** 2)) : R;
    const crown = (T.fit && T.fit.renderedCrown) || Hc + R;
    if (ell) { const a = Math.max(0.5, crown - Hc) + mg, W = hw + mg; if (Math.abs(y) < W) { const v = a * Math.sqrt(1 - (y / W) ** 2); if (lo < Hc + v && hi > Hc - v) return 'fus'; } }
    else if (Math.abs(y) < hw + mg && lo < crown + mg && hi > Hc - R - mg) return 'fus';
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
    const top = T.hstab.tTail ? (T.fit && T.fit.renderedH) || T.H || Hc + 8 : Hc + R + 1;
    if (lo < top + mg && hi > Hc - R) return 'tail';
  }
  return null;
}
// any sample point of an oriented box {c:[x,z], u, hl, hw, lo, hi} inside the aircraft (nose [x,z], f [x,z] forward)
function boxHitsAc(bx, T, nose, f, mg) {
  const reach = T.L + (T.wing ? T.wing.span / 2 : T.R) + bx.hl + bx.hw + mg; // cheap reject: out of reach of the airframe
  if (Math.abs(bx.c[0] - nose[0]) > reach || Math.abs(bx.c[1] - nose[1]) > reach) return null;
  const r = [-f[1], f[0]]; const nx = Math.max(1, Math.ceil(bx.hl / 0.7)), ny = Math.max(1, Math.ceil(bx.hw / 0.7));
  const v = [-bx.u[1], bx.u[0]];
  for (let i = -nx; i <= nx; i++) for (let j = -ny; j <= ny; j++) {
    const px = bx.c[0] + bx.u[0] * bx.hl * i / nx + v[0] * bx.hw * j / ny, pz = bx.c[1] + bx.u[1] * bx.hl * i / nx + v[1] * bx.hw * j / ny;
    const dx = px - nose[0], dz = pz - nose[1];
    const x = -(dx * f[0] + dz * f[1]), y = dx * r[0] + dz * r[1];
    const k = acHit(T, x, y, bx.lo - G, bx.hi - G, mg); if (k) return k;
  }
  return null;
}

export class LiveGateSystem {
  constructor(gates, { atlasExtra = [] } = {}) {
    this.gates = gates; this.anims = new Map(); this.settles = new Map(); this.dirty = true; this.live = true;
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
  // upper-deck (A380 U1L) bridges from the stand data (data/sfo_stands.json bridges_upper, door 3); standGates() does not
  // pass them, so they are read here and kept apart from g.bridges (the engine, the tools and the L1/L2 logic use those)
  attachUpper() {
    const byName = new Map((STANDS.stands || []).map(s => [s.name, s]));
    for (const g of this.gates) {
      const s = byName.get(g.name); if (!s || !g.bridge || !(s.bridges_upper && s.bridges_upper.length)) continue;
      g.bridgesUpper = s.bridges_upper.map(b => ({ gate: b.gate, attach: worldToST(b.attach[0], b.attach[1]), attachW: b.attach, door: 3, upper: true,
        rotundaW: b.rotunda || null, cabW: b.cab || null, walkW: b.walk || null, cabPose: b.cab_pose || null, stowW: b.stow || null,
        rotundaMaxR: b.rotunda_max_r ?? null, extRange: b.ext_range || null, model: b.model || null, dockTypesOut: b.dock_types_out || [], stowLen: b.stow_len ?? null }));
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
      const sh = Math.hypot(rot[0] - r0[0], rot[2] - r0[2]); if (sh > 0.005) b.rotShift = +sh.toFixed(2); }
    let walk = (b.walkW && b.walkW.length >= 2) ? b.walkW.map(cz) : [att, rot];
    if (b.rotShift) walk[walk.length - 1] = rot.slice();
    if (Math.hypot(walk[walk.length - 1][0] - rot[0], walk[walk.length - 1][2] - rot[2]) > 0.05) walk.push(rot.slice());
    walk = walk.filter((p, i) => i === 0 || Math.hypot(p[0] - walk[i - 1][0], p[2] - walk[i - 1][2]) > 0.05);
    // the mapped walkway may start inside the (+-5 m) terminal outline: the fixed walkway begins where the polyline last
    // leaves the building (the part inside is the building's own corridor)
    for (let i = walk.length - 2; i >= 0; i--) {
      if (!inBuilding(walk[i][0], walk[i][2])) continue;
      const A = walk[i], B = walk[i + 1]; if (inBuilding(B[0], B[2])) break;
      let lo = 0, hi = 1; for (let k = 0; k < 20; k++) { const mid = (lo + hi) / 2; if (inBuilding(A[0] + (B[0] - A[0]) * mid, A[2] + (B[2] - A[2]) * mid)) lo = mid; else hi = mid; }
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
            const x = A[0] + u[0] * t + v[0] * w * WALK_W / 2, z = A[2] + u[1] * t + v[1] * w * WALK_W / 2; if (!inBuilding(x, z)) continue;
            const nb = nearestBuilding(x, z); if (!nb.p) continue; const d = Math.hypot(nb.p[0] - x, nb.p[1] - z); if (!best || d > best.d) best = { d, x, z, p: nb.p }; } }
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
    const stowL = b.stowW ? Math.hypot(b.stowW[0] - rot[0], b.stowW[1] - rot[2]) : null;
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
    if (b.stowW) { b.a0 = yawOf(b.stowW[0] - rot[0], b.stowW[1] - rot[2]); b.e0 = clampN(stowL, opR, mechE); }
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
    const out = []; const nb = nearestBuilding(x, z);
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
    b.Hb = b.upper ? DEPARTURE_LEVEL + WALK_H + 0.6 : DEPARTURE_LEVEL; const dh = b.upper ? 0 : b.walkLen / 12;
    b._tgH = tg;
    const Hr = this.pickHr(g, [b], b._tgH, b.Hb - dh, b.Hb + dh);
    this.applyHeights(b, Hr, tg, b._tgH);
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
  bandH(b, e, h, slope) { const lim = Math.max(0, e - b.m.F) * slope; return clampN(h, b.Hr - lim, b.Hr + lim); }
  // the moving parts of bridge b in joint state q against its obstacles (the fixed walkways, drums and pedestals of the
  // bridges around it and its own fixed walkway outside its drum): the first contact 'part x part', or null
  fixedHit(b, q, kk = 0) {
    const O = b._obs; if (!O || !O.length) return null;
    for (const bx of this.solidsQ(b, q, kk)) { if (bx.part === 'stair') continue; // (its side is chosen against these in finishPrep)
      const br = Math.hypot(bx.hl, bx.hw);
      for (const o of O) { if (o.own && bx.part === 'neck') continue; // (the rotunda junction, below)
        if (Math.abs(o.c[0] - bx.c[0]) > o.rr + br + 0.1 || Math.abs(o.c[1] - bx.c[1]) > o.rr + br + 0.1) continue;
        if (bx.hi > o.lo && o.hi > bx.lo && solidOverlap(bx, o, 0.05)) return bx.part + ' x ' + (o.own ? 'own ' : '') + o.part; } }
    return null;
  }
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
      // (own walkway: beyond 0.6 m from the drum, against the tunnels, drive column and cab - not against the rotunda
      // corridor: where the walkway and the corridor meet the drum, the two boxes overlap whenever they are less than
      // ~110 deg apart, and the data's docked / rest poses of A12, F5, F14, F17, F19, F21 L1 fold back to 41-45 deg from
      // the mapped walkway - a junction our boxes cannot draw; listed in docs/requests/bridges_closeout.md)
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
        const q0 = { a: b.a0, e: b.e0, t: 0, h: b.h0 }; if (!this.fixedHit(b, q0, 0)) continue;
        const own = this.standAircraft(g); const nb = [];
        for (const o of this.gates) { if (o === g || !o.bridge && !(o.sharesBridgesOf)) continue; const on = stW(o.nose, G); if (Math.hypot(on[0] - b.rot[0], on[2] - b.rot[2]) > 120) continue; for (const A of this.standAircraft(o)) nb.push(A); }
        const others = all.filter(x => x.b !== b && Math.hypot(x.b.rot[0] - b.rot[0], x.b.rot[2] - b.rot[2]) < 80).map(x => restS.get(x.b)).flat();
        const clear = (q) => { if (this.fixedHit(b, q, 0)) return false; const S = this.solidsQ(b, q, 0);
          for (const bx of S) { if (own.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 1.0)) || nb.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 0.5))) return false;
            if (others.some(o => bx.hi > o.lo && o.hi > bx.lo && solidOverlap(bx, o, 0.3))) return false;
            if (bx.part !== 'stair' && [[0, 0], [1, 1], [1, -1], [-1, 1], [-1, -1]].some(([i, j]) => inBuilding(bx.c[0] + bx.u[0] * bx.hl * i - bx.u[1] * bx.hw * j, bx.c[1] + bx.u[1] * bx.hl * i + bx.u[0] * bx.hw * j))) return false; }
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
    const restOf = new Map(all.map(({ b }) => [b, this.solidsQ(b, { a: b.a0, e: b.e0, t: 0, h: b.h0 }, 0, true)]));
    for (const { g, b } of all) {
      const others = all.filter(o => o.b !== b && Math.hypot(o.b.rot[0] - b.rot[0], o.b.rot[2] - b.rot[2]) < 70).map(o => restOf.get(o.b)).flat()
        .map(o => ({ o, r: Math.hypot(o.hl, o.hw) }));
      const acs = this.standAircraft(g); const tg = b._tg || [];
      const q0 = { a: b.a0, e: b.e0, t: 0, h: b.h0 };
      const poses = [{ q: q0, ac: acs }].concat(tg.map(t => ({ q: { a: t.a, e: t.e, t: 0, h: t.sill }, ac: [{ T: TYPES[t.key], nose: [t.nose[0], t.nose[2]], f: [t.f[0], t.f[2]] }] })),
        this.sweepQ(g, b, false).filter((q, i) => i % 3 === 0).map(q => ({ q, ac: [] }))); // (every candidate docking path, sampled)
      const bad = {};
      for (const sd of [1, -1]) { b.stairSide = sd; let n = 0;
        for (const P of poses) { const S = this.stairBoxes(b, P.q);
          if (S.some(bx => P.ac.some(A => boxHitsAc(bx, A.T, A.nose, A.f, 0.5)))) n += 2;
          if (S.some(bx => { const rb = Math.hypot(bx.hl, bx.hw) + 0.3; return others.some(({ o, r }) => Math.abs(o.c[0] - bx.c[0]) < r + rb && Math.abs(o.c[1] - bx.c[1]) < r + rb && o.hi > bx.lo && o.lo < bx.hi && solidOverlap(bx, o, 0.3)); })) n += 1;
          if (S.some(bx => { const v = [-bx.u[1], bx.u[0]]; return [[1, 1], [1, -1], [-1, 1], [-1, -1], [0, 0]].some(([i, j]) => inBuilding(bx.c[0] + bx.u[0] * bx.hl * i + v[0] * bx.hw * j, bx.c[1] + bx.u[1] * bx.hl * i + v[1] * bx.hw * j)); })) n += 2; }
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
    // spacer - where a parked aircraft stands beyond it: the tunnels can travel there, the data's model is an inference)
    // (below the operational retraction the sections cannot telescope any further: sections() clamps there)
    if (q.e < m.opR - 1e-6 || q.e > Math.max(m.opE, m.mechE - 0.3)) return { ok: false, why: `extension ${q.e.toFixed(1)} m outside ${m.opR}-${m.opE} (mechanical ${m.mechE.toFixed(1)})` };
    if (opt ? Math.abs(turn) > CAB_OPT_HALF : (turn > CAB_CW || turn < -CAB_CCW)) return { ok: false, why: `cab turn ${turn.toFixed(0)} deg` };
    if (!b.swingFree && Math.abs(wrap(q.a - b.ac)) > ROT_SWING * DEG + 1e-6) return { ok: false, why: `rotunda swing ${(wrap(q.a - b.ac) / DEG).toFixed(0)} deg` };
    const fh = this.fixedHit(b, q, 1); if (fh) return { ok: false, why: `${fh} (fixed bridge parts)` };
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
      if (h !== 'fixed') fixedOnly = false;
    }
    return no(fixedOnly ? 'every docking path passes through a fixed walkway / drum' : 'every docking path passes through the aircraft');
  }
  // undocking plan: the docking path backwards, the cab at the door's height as far as the tunnel allows - each pose at
  // most 1:4 (AC 150/5220-21C §3.4.b(6)), so a short rest tunnel moves the cab towards the rotunda floor on the way
  // (timed at the sheet's lift rate); at rest the cab then settles to the rest height h0 (step(): settles)
  levelPlan(b, P) {
    const n = P.path.length; const path = P.path.map((q, i) => ({ ...q, h: i === n - 1 ? P.q1.h : this.bandH(b, q.e, P.q1.h, SLOPE_MAX) }));
    const dur = []; for (let i = 1; i < path.length; i++) dur.push(this.segTime(b, path[i - 1], path[i], i === path.length - 1));
    return { ...P, path, q0: path[0], dur, total: dur.reduce((x, y) => x + y, 0) };
  }
  // a segment at the sheet's maximum rates, without the 3 s allowance per motion and with the back-off from the door at
  // the drive speed (the engine's fast retraction: hurryUndock)
  segTimeMin(b, A, B) {
    let L = 0, pp = null; for (let i = 0; i <= 12; i++) { const q = this.qLerp(b, A, B, i / 12); const p = [b.rot[0] + Math.cos(q.a) * q.e, b.rot[2] + Math.sin(q.a) * q.e]; if (pp) L += Math.hypot(p[0] - pp[0], p[1] - pp[1]); pp = p; }
    return Math.max(0.5, L / DRIVE_V, Math.abs(B.t - A.t) / CAB_RATE, Math.abs(B.h - A.h) / LIFT_RATE);
  }
  segTime(b, A, B, approach) {
    if (approach) return Math.max(2, Math.hypot(B.e - A.e, wrap(B.a - A.a) * B.e) / APPROACH_V, Math.abs(B.h - A.h) / LIFT_RATE);
    let L = 0, pp = null; for (let i = 0; i <= 12; i++) { const q = this.qLerp(b, A, B, i / 12); const p = [b.rot[0] + Math.cos(q.a) * q.e, b.rot[2] + Math.sin(q.a) * q.e]; if (pp) L += Math.hypot(p[0] - pp[0], p[1] - pp[1]); pp = p; }
    return 3 + Math.max(L / DRIVE_V, Math.abs(B.t - A.t) / CAB_RATE, Math.abs(B.h - A.h) / LIFT_RATE);
  }
  qLerp(b, A, B, u) {
    const oa = wrap(A.a - b.ac), ob = wrap(B.a - b.ac); // rotunda angle relative to its centreline (stays inside the swing)
    return { a: b.ac + oa + (ob - oa) * u, e: A.e + (B.e - A.e) * u, t: A.t + (B.t - A.t) * u, h: A.h + (B.h - A.h) * u };
  }
  pathHits(b, pts, T, nose, f) {
    for (let i = 1; i < pts.length; i++) {
      const last = i === pts.length - 1; const n = last ? 4 : 16;
      for (let k = 0; k <= n; k++) {
        const q = this.qLerp(b, pts[i - 1], pts[i], k / n);
        if (this.fixedHit(b, q, last && k > 0 ? 1 : 0)) return 'fixed'; // through a fixed walkway / drum (own or another bridge's)
        for (const bx of this.solidsQ(b, q, last && k > 0 ? 1 : 0)) {
          if (last && (bx.part === 'cab' || bx.part === 'bellows')) continue; // the closure meets the door by design
          if (boxHitsAc(bx, T, nose, f, bx.part === 'cab' ? 0.3 : 0.5)) return 'aircraft';
        }
      }
    }
    return false;
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
    const q = k <= 0 && !(a && a.plans) ? { a: b.a0, e: b.e0, t: 0, h: b.hRest ?? b.h0 } : this.qAt(b, P, k);
    const T = P.T || TYPES[g.acType] || TYPES[g._lastType] || TYPES[REF_TYPE[g.cls] || 'b38m'];
    let door = P.door;
    if (!door) { const dn = g.dock ? g.dock.nose : g.nose, dd = g.dock ? g.dock.dir : g.dir; door = doorOf(stW(dn, G), stD(dd), T, b.door).door; }
    const approach = P.ok && P.dur.length ? clampN((clampN(k, 0, 1) * P.total - (P.total - P.dur[P.dur.length - 1])) / P.dur[P.dur.length - 1], 0, 1) : 0;
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
    seg(b.rotR * 0.8, m.F, 2.4, 2.8, 'neck');
    const secs = this.sections(b, q.e);
    secs.forEach(([s0, s1, w, h], i) => seg(s0, s1, w, h, 'tunnel' + (i + 1)));
    // drive column (legs + bogie) on the outer tunnel
    const dc = this.driveAt(b, q.e); const cx = rot[0] + u[0] * dc, cz = rot[2] + u[2] * dc;
    out.push({ c: [cx, cz], u: [u[0], u[2]], hl: 0.6, hw: 1.45, lo: G, hi: fl(dc), part: 'column' });
    // cab (body + closure), about the pivot, facing q.a + q.t
    const fc = dirOf(q.a + q.t); const piv = [rot[0] + u[0] * q.e, rot[2] + u[2] * q.e]; const front = m.spacer - 0.45 + 0.45 + 0.15 * kk;
    out.push({ c: [piv[0] + fc[0] * (front - CAB_BACK) / 2, piv[1] + fc[2] * (front - CAB_BACK) / 2], u: [fc[0], fc[2]], hl: (front + CAB_BACK) / 2, hw: CAB_W / 2, lo: G + q.h - 0.3, hi: G + q.h + 3.6, part: 'cab' });
    // landing + stair (aft of the cab bubble, beside the outer tunnel)
    for (const bx of this.stairBoxes(b, q)) out.push(bx);
    return out;
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
    // tube (it enters the building at the attach point), the others as slabs; columns every ~14 m outside the building
    const segs = this.ownWalk(b);
    segs.forEach((S, n) => { if (n === 0) tube(geo, S.first ? v3.add(S.A, v3.mul(S.d, -0.3)) : S.drawA, S.B, WALK_W, WALK_H, C.walk, C.panelE); else slab(geo, S.A, S.B, WALK_W, WALK_H, C.walk, C.panelE); });
    let run = 0;
    for (const S of segs) {
      const L = Math.hypot(S.B[0] - S.A[0], S.B[2] - S.A[2]);
      for (let d = 7 - (run % 14); d < L; d += 14) { const t = d / L; const p = v3.lerp(S.A, S.B, t); if (d < 1.5 || L - d < b.rotR + 1.5 && S.last || inBuilding(p[0], p[2]) || distBuilding(p[0], p[2]) < 0.6) continue; cyl(geo, [p[0], G, p[2]], 0.35, p[1] - G - 0.3, C.steel, C.steelE, 10); }
      run += L;
    }
    // rotunda on its pedestal (drum radius limited by the neighbouring rotundas, data rotundaMaxR)
    cyl(geo, [rot[0], G, rot[2]], 0.6, b.Hr - 0.3, C.steel, C.steelE, 12);
    cyl(geo, [rot[0], G + b.Hr - 0.3, rot[2]], b.rotR, 3.6, C.panel, [0.45, 0.25, 0, 0], 24);
    // rotunda corridor (turns with the tunnel) from the drum to tunnel A
    slab(geo, at(b.rotR * 0.8, fl(b.rotR * 0.8) - 0.1), at(m.F + 0.2, fl(m.F + 0.2) - 0.1), 2.4, 2.9, C.neck, C.panelE);
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
    for (let i = 0; i < 5; i++) geo.box([fr + i * bell / 5, 0.05, -1.55 - (i % 2) * 0.05], [fr + (i + 1) * bell / 5, 3.0, 1.55 + (i % 2) * 0.05], C.dark, C.darkE, cabM);
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
          const along = v3.mul(hdir, -sg); // text runs left-to-right for a viewer facing -n
          const u0 = v3.add(c, v3.mul(along, -Lw / 2)), u1 = v3.add(c, v3.mul(along, Lw / 2));
          signQuad(sgn, [v3.add(u0, [0, -Lh / 2, 0]), v3.add(u1, [0, -Lh / 2, 0]), v3.add(u1, [0, Lh / 2, 0]), v3.add(u0, [0, Lh / 2, 0])], n, r, true);
        }
      }
    }
    return P;
  }
  // ------------------------------------------------------------ stand sign + VDGS
  // on the stand centreline ahead of the nose: on the terminal face when the stop point is close to it, else on its own
  // post; the first spot (facade first, then posts 12, 11, 13, 10, ... m ahead of the nose) that no bridge part of this
  // or a neighbouring stand reaches in any pose (rest, docking paths, docked for every type it docks) with 0.5 m clearance
  vdgsSpot(g) {
    if (g._vdgs) return g._vdgs;
    const nose = stW(g.nose, G), f = stD(g.dir);
    // the terminal face on the stand centreline (the outline the terminal model is built from), else the walkway start
    // (no building on the centreline within 60 m - A13, G10, G13: posts only; review 2026-11-04 found their facade units
    // floating 7-11 m up with no wall within 22-30 m)
    let tf = null; for (let t = 1; t <= 60; t += 0.5) { const p = v3.add(nose, v3.mul(f, t)); if (inBuilding(p[0], p[2])) { tf = t - 0.25; break; } }
    const tmax = tf == null ? 40 : tf - 2.5;
    // a facade unit only where the wall behind it (0.6-3 m) reaches above the unit (H0 + 4.2 m): the piers / halls,
    // not the 5 m ramp-level complex
    const tries = []; const fac = (H0) => { if (tf == null) return; const t = Math.max(1, tf - 0.35);
      if ([0.6, 1.5, 3.0].every(d => { const p = v3.add(nose, v3.mul(f, t + d)); return wallTop(p[0], p[2]) >= H0 + 4.2; })) tries.push({ t, post: false, H0 }); };
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
      let hit = false;
      for (const a of boxes) { for (const s of sweep) if (s.hi > a.lo - 0.5 && s.lo < a.hi + 0.5 && solidOverlap(a, s, 0.5)) { hit = true; break; } if (hit) break; }
      if (!hit) { pick = c; break; }
    } }
    if (!pick) { pick = tries[0]; this.vdgsBlocked = (this.vdgsBlocked || 0) + 1; (this.vdgsBlockedAt || (this.vdgsBlockedAt = [])).push(g.name); }
    return (g._vdgs = { t: pick.t, post: pick.post, H0: pick.H0, W });
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
  // current extension of a stand's bridges (0 = every bridge at rest .. 1 = docked); the engine holds a departing
  // aircraft until this is 0 (docs/requests/realtime_round1.md 1b)
  extension(g) { const a = this.anims.get(g.id); if (a) return a.k; return g.acType && this.bridgesOf(g).some(b => this.docks(g, b)) ? 1 : 0; }
  // seconds the current undock (or a future one from the docked state) takes: the sheet's rates along the docking path
  undockTime(g) { let t = 0; for (const b of this.bridgesOf(g)) { const P = this.planFor(g, b); if (P.ok) t = Math.max(t, P.total); } return t; }
  // typeKey: TYPES key of the parked aircraft (null = empty); pose: {nose:[s,t], dir:[s,t]}; icao: type designator;
  // opts.freighter: the occupant is a freighter (js/live/lookup.js isFreighter): only the door-1 bridge docks
  setOccupant(g, typeKey, animate, now, pose, icao, opts = {}) {
    if (typeKey) { g.dock = pose || null; g.dockType = icao || null; g.dockCargo = !!opts.freighter; }
    // a new docking stops a rest-height settle where it is (the docking pre-positions from there)
    if (typeKey && this.settles) for (const b of this.bridgesOf(g)) if (this.settles.delete(b)) b._plans.clear();
    const was = !!g.acType; g.acType = typeKey || null; g.empty = !typeKey;
    if (typeKey) g._lastType = typeKey;
    if (g.bridge && animate && was !== !!typeKey) {
      const cur = this.anims.get(g.id); const k0 = cur ? cur.k : (was ? 1 : 0);
      // the plans of this docking (arrival) or of the docking being undone (departure): the same path both ways
      let plans = cur && cur.plans ? cur.plans : new Map();
      if (typeKey && !(cur && cur.to === 1)) { plans = new Map(); for (const b of this.bridgesOf(g)) { const P = this.planFor(g, b); if (P.ok) plans.set(b, P); } }
      // undocking from the docked state: the same path back, but the bridge keeps the door's height (no vertical travel;
      // it rests there until the next docking pre-positions it)
      if (!typeKey && !(cur && cur.to === 1)) { plans = new Map(); for (const b of this.bridgesOf(g)) { const P = this.planFor(g, b); if (P.ok) plans.set(b, this.levelPlan(b, P)); } }
      let total = 0; for (const P of plans.values()) total = Math.max(total, P.total);
      if (!total) total = typeKey ? DOCK_TIME : UNDOCK_TIME;
      if (!typeKey && opts.undockS) total = Math.max(total, opts.undockS); // never faster than the sheet's rates
      const span = Math.abs((typeKey ? 1 : 0) - k0) || 1;
      this.anims.set(g.id, { from: k0, to: typeKey ? 1 : 0, t0: now + (typeKey ? DOCK_DELAY : 0) * 1000, dur: total * span * 1000, k: k0, plans });
    }
    this.dirty = true;
  }
  // the engine's fast retraction of a departing aircraft's bridges (docs/requests/realtime_round2.md §1a; js/live/app.js
  // and tools/live/invariants.mjs call it right after setOccupant(g, null)): the undocking restarts now from where the
  // bridges are, along the same path, at the Oshkosh AeroTech sheet's maximum rates (27 m/min, cab 145 deg/min, lift
  // 1.09 m/min; no 3 s allowance per motion, the back-off from the door at the drive speed) - in `s` seconds when that
  // is slower, never faster. Returns the seconds the retraction takes (0: nothing to hurry).
  hurryUndock(g, s = 0, now = Date.now()) {
    const a = this.anims.get(g.id); if (!a || a.to !== 0 || !a.plans || !a.plans.size) return 0;
    const u = a.dur > 0 ? clampN((now - a.t0) / a.dur, 0, 1) : 1; const kc = a.from + (a.to - a.from) * u; if (kc <= 1e-4) return 0;
    const plans = new Map(); let T = 0;
    for (const [b, P] of a.plans) {
      if (!P.ok || !P.total) continue;
      // the pose now, and the path from the rest pose up to it
      let t = clampN(kc, 0, 1) * P.total, i = 0; for (; i < P.dur.length - 1 && t > P.dur[i]; i++) t -= P.dur[i];
      const qc = this.qLerp(b, P.path[i], P.path[i + 1], P.dur[i] ? clampN(t / P.dur[i], 0, 1) : 1);
      const path = P.path.slice(0, i + 1).concat([qc]); const dur = []; for (let j = 1; j < path.length; j++) dur.push(this.segTimeMin(b, path[j - 1], path[j]));
      const total = dur.reduce((x, y) => x + y, 0); T = Math.max(T, total);
      plans.set(b, { ...P, path, dur, total, q1: qc });
    }
    if (!plans.size) return 0;
    const dur = Math.max(s, T); this.anims.set(g.id, { from: 1, to: 0, t0: now, dur: dur * 1000, k: 1, plans, fast: true }); this.dirty = true;
    return dur;
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
    if (this.anims.size || (this.settles && this.settles.size)) {
      const dyn = new Geo(), dsgn = newSignGeo();
      for (const g of this.gates) { if (!g.bridge) continue; const a = this.anims.get(g.id); if (a) { for (const b of this.bridgesOf(g)) this.bridgeGeo(g, b, a.plans && a.plans.has(b) ? a.k : 0, dyn, dsgn); } else if (this.settling(g)) for (const b of this.bridgesOf(g)) this.bridgeGeo(g, b, 0, dyn, dsgn); }
      this.dynMesh = dyn.nv ? meshOf(dyn) : null; this.dynSign = dsgn.pos.length ? meshOfSign(dsgn) : null;
    }
    this.sprites = (this.staticSprites || []).concat(this.dynSprites);
  }
  settling(g) { return !!(this.settles && this.settles.size && this.bridgesOf(g).some(b => this.settles.has(b))); }
  // advance the docking animations to `now` (called by items(); a checker without the renderer may call it directly)
  step(now) {
    let moving = false; const S = this.settles || (this.settles = new Map());
    for (const [id, a] of this.anims) {
      const u = Math.min(1, Math.max(0, (now - a.t0) / a.dur)); a.k = a.from + (a.to - a.from) * u; moving = true;
      if (u >= 1) {
        this.anims.delete(id); this.dirty = true;
        // a retracted bridge ends at the height its undocking plan left it (the door's, within 1:4) and then settles to
        // its rest height h0 (rest tunnel <= 1:12) at the sheet's lift rate (1.09 m/min); the engine does not wait for it
        if (a.to === 0) for (const [b, P] of a.plans || []) { if (P.ok) { b.hRest = P.path[0].h; b._plans.clear(); if (Math.abs(b.hRest - b.h0) > 0.005) S.set(b, { from: b.hRest, t0: now, dur: Math.abs(b.h0 - b.hRest) / LIFT_RATE * 1000 }); } }
      }
    }
    for (const [b, st] of S) {
      const u = Math.min(1, Math.max(0, (now - st.t0) / st.dur)); b.hRest = st.from + (b.h0 - st.from) * u; moving = true;
      if (u >= 1) { S.delete(b); b.hRest = b.h0; b._plans.clear(); this.dirty = true; }
    }
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
    const no = (why) => { if (this.gseWhy) this.gseWhy.push(why); return false; }; // (gseWhy: checkers' diagnostics)
    const ok = (v, boxes, belt = null) => {
      const rt = [-v.d[2], v.d[0]]; const W = (x, z) => [v.p[0] + v.d[0] * x + rt[0] * z, v.p[2] + v.d[2] * x + rt[1] * z];
      const smp = []; // [x, z (world), lo, hi (above the apron), margin, closure]
      for (const [x0, x1, z0, z1, y0, y1] of boxes) { const nx = Math.max(1, Math.ceil((x1 - x0) / 0.3)), nz = Math.max(1, Math.ceil((z1 - z0) / 0.3));
        for (let i = 0; i <= nx; i++) for (let j = 0; j <= nz; j++) smp.push([...W(x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz), y0, y1, 0.3, false]); }
      if (belt) { const n = Math.ceil(belt.len / 0.3); for (let i = 0; i <= n; i++) { const s = belt.len * i / n; const x = belt.x0 + s * Math.cos(belt.th), y = belt.y0 + s * Math.sin(belt.th);
        for (const z of [-belt.w / 2, 0, belt.w / 2]) smp.push([...W(x, z), y, y + belt.h, 0.1, x > belt.xe - 1.0]); } }
      for (const [x, z, lo, hi, mg, closure] of smp) {
        const dx = x - n2[0], dz = z - n2[1]; const ax = -(dx * f2[0] + dz * f2[1]), ay = dx * r2[0] + dz * r2[1];
        const h = acHit(T, ax, ay, lo, hi, closure ? 0 : mg, true); if (h && !(closure && h === 'fus')) return no('own ' + h);
        for (const o of this.keepOut) if (o.gate !== g && hitsAircraft(o, [x, z], hi)) return no('other aircraft');
        if (inBuilding(x, z)) return no('building');
      }
      const hb = boxes.map(([x0, x1, z0, z1, y0, y1]) => { const c = W((x0 + x1) / 2, (z0 + z1) / 2); return { c, u: [v.d[0], v.d[2]], hl: (x1 - x0) / 2, hw: (z1 - z0) / 2, lo: G + y0, hi: G + y1 }; });
      if (belt) { const xm = belt.x0 + belt.len * Math.cos(belt.th) / 2; hb.push({ c: W(xm, 0), u: [v.d[0], v.d[2]], hl: belt.len * Math.cos(belt.th) / 2, hw: belt.w / 2, lo: G + belt.y0, hi: G + belt.y0 + belt.len * Math.sin(belt.th) + belt.h }); }
      for (const vb of hb) { for (const s of solids) if (s.lo < vb.hi + 0.3 && s.hi > vb.lo && solidOverlap(vb, s, 0.5)) return no('bridge ' + s.part); for (const o of placed) if (solidOverlap(vb, o, 0.3)) return no('vehicle'); }
      for (const vb of hb) placed.push(vb); return true;
    };
    const tint = () => { const cs = [[0.95, 0.95, 0.95], [0.9, 0.75, 0.1], [0.15, 0.3, 0.6], [0.85, 0.3, 0.1], [0.4, 0.42, 0.45]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    const B = this.vehicleBuckets;
    const HULL = { tug: [[-1.4, 1.4, -0.92, 0.92, 0, 2.1]], cart: [[-1.5, 1.5, -0.85, 0.85, 0, 1.6]], catering: [[-3.5, 4.55, -1.2, 1.2, 0, 6.2]], fuel: [[-3.8, 4.55, -1.3, 1.3, 0, 3.2]], gpu: [[-1.2, 1.2, -0.7, 0.7, 0, 1.5]], cone: [[-0.22, 0.22, -0.22, 0.22, 0, 0.75]] };
    const put = (bucket, v, color) => { if (ok(v, HULL[bucket])) { B[bucket].push(inst(v.M, color || tint())); return true; } return false; };
    const fuse = T.R + 0.4;
    // cargo doors are on the right (starboard) side: forward ahead of the wing, aft behind it (stations inferred)
    const fwdCargo = T.L * 0.22, aftCargo = T.L * 0.66;
    const cartCol = () => { const cs = [[0.34, 0.37, 0.4], [0.16, 0.24, 0.42], [0.2, 0.3, 0.24], [0.55, 0.56, 0.57]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    const tugCol = () => { const cs = [[0.9, 0.72, 0.1], [0.92, 0.92, 0.9], [0.12, 0.2, 0.42]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    // belt loaders (narrow bodies with a sourced lower-deck sill: Boeing 737 and Airbus A320 families, js/world/gates.js
    // BELT_SILL; the wide bodies' holds are container-loaded and not modelled): the conveyor's top end on the sill at the
    // fuselage side (the cross-section's half width at that height + 0.1 m), the vehicle angled 18 deg off square with
    // its low end away from the wing
    const tk = this.typeKeyOf(T); const bk = /^b73\d$|^b3[789x]m$/.test(tk) ? 'beltLoader' : /^a3(18|19|20|21)$|^a(19|20|21)n$/.test(tk) ? 'beltLoaderA' : null;
    if (bk) { const S = BELT_SILL[bk], sh = beltShape(S); const crown = (T.fit && T.fit.renderedCrown) || T.Hc + T.R; const a = crown - T.Hc;
      // (the end against the side skin at the sill, or 0.3 m above the model's lowest skin where the published sill lies
      // below it: 737 1.30-1.45 m vs the fitted model's 1.62 m)
      const yEnd = T.R * Math.sqrt(Math.max(0, 1 - ((Math.max(S, T.Hc - a + 0.3) - T.Hc) / a) ** 2)) + 0.05;
      const belt = { x0: sh.x0, y0: sh.y0, len: sh.len, th: sh.th, w: sh.w, h: sh.thick + 0.25, xe: sh.xe };
      const boxes = [[-2.5, 2.4, -1.05, 1.05, 0, sh.chassisTop], [-2.55, -1.2, -1.08, -0.5, 0, sh.cabTop]];
      for (const [X, pr, sgn] of [[fwdCargo, 0.85, -1], [aftCargo, 0.6, 1]]) { if (R() >= pr) continue;
        for (const yaw of [72, 90, 60]) { const c = sgn * Math.cos(yaw * DEG), sn = -Math.sin(yaw * DEG); const d = v3.norm(v3.add(v3.mul(f, c), v3.mul(r, sn)));
          const e = v3.add(v3.sub(nose, v3.mul(f, X)), v3.mul(r, yEnd)); const p = v3.sub(e, v3.mul(d, sh.xe));
          const v = { M: m4.basis(d, [0, 1, 0], [p[0], G, p[2]]), p, d }; if (ok(v, boxes, belt)) { B[bk].push(inst(v.M, tint())); break; } } } }
    // baggage train alongside the aft fuselage behind the wing, tug facing forward, carts trailing
    if (R() < 0.75) { const y = fuse + 6.8, a0 = aftCargo + 2.5; if (put('tug', at(a0, y, 0), tugCol())) for (let i = 0; i < 3; i++) put('cart', at(a0 + 3.4 + i * 3.4, y, 0), cartCol()); }
    if (R() < 0.45 && T.doors[1] != null) put('catering', at(T.doors[1] + 1, fuse + 4.4, -Math.PI / 2), [0.95, 0.95, 0.95, 1]);
    if (R() < 0.35 && T.eng.length) put('fuel', at(T.xMain - 5, T.eng[T.eng.length - 1].z + 7.5, 0), [0.85, 0.85, 0.85, 1]);
    if (R() < 0.6) put('gpu', at(3.5, fuse + 3.4, 0.3));
    const span = T.wing ? T.wing.span / 2 : 18;
    for (const [a, s] of [[-2.5, 0], [T.wing ? T.wing.rootLE + (span) * Math.tan((T.wing.sweep || 25) * Math.PI / 180) + 1 : T.L * 0.5, span + 1.2], [T.wing ? T.wing.rootLE + span * Math.tan((T.wing.sweep || 25) * Math.PI / 180) + 1 : T.L * 0.5, -(span + 1.2)], [T.L + 2, 0]]) { const v = at(a, s); if (ok(v, HULL.cone)) B.cone.push(inst(v.M)); }
  }
  typeKeyOf(T) { if (!this._tk) { this._tk = new Map(); for (const [k, t] of Object.entries(TYPES)) if (t) this._tk.set(t, k); } return this._tk.get(T) || ''; }
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
