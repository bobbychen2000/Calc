// SFO layout from SFO Museum architecture data: buildings, gates/stands, pavement map, stand markings.
import { Geo } from '../geom.js';
import { m4, v3, rng } from '../math.js';
import { GROUND_Y, worldToST, stToWorld } from '../geo.js';
import { MAT } from '../world/buildings.js';
import { APT_RECT, RWY, RWY_W, APRONS, landside } from '../world/airfield.js';
import { earcut } from './earcut.js';
import { buildTerminals, buildTower } from './terminals.js';

const G = GROUND_Y;
const ringArea = (r) => { let a = 0; for (let i = 0; i < r.length; i++) { const p = r[i], q = r[(i + 1) % r.length]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; };

// ------------------------------------------------------------------ extrusion helpers (world x,z rings)
// walls: outward normals; roof: earcut with holes. Rings are [x,z]; data convention: outer ring has negative shoelace in raw [x,z].
function extrudePoly(g, rings, y0, y1, wall, roof, opts = {}) {
  rings.forEach((ring, ri) => {
    // orient so that walls face outward: outer ring CW in (x,z) raw (negative area) -> keep; holes opposite
    const n = ring.length;
    const outer = ri === 0; const neg = ringArea(ring) < 0;
    const flip = outer ? !neg : neg;
    for (let i = 0; i < n; i++) {
      let a = ring[i], b = ring[(i + 1) % n]; if (flip) { const t = a; a = b; b = t; }
      const dx = b[0] - a[0], dz = b[1] - a[1]; const L = Math.hypot(dx, dz); if (L < 0.05) continue;
      // outward normal for a ring with negative raw area (CW in x,z screen == CCW in east/north)
      const nx = -dz / L, nz = dx / L;
      const base = g.nv; const c = wall.c, e = wall.e;
      const u0 = opts.u0 || 0;
      g.vert([a[0], y0, a[1]], [nx, 0, nz], c, e, [u0, 0]); g.vert([b[0], y0, b[1]], [nx, 0, nz], c, e, [u0 + L, 0]);
      g.vert([b[0], y1, b[1]], [nx, 0, nz], c, e, [u0 + L, y1 - y0]); g.vert([a[0], y1, a[1]], [nx, 0, nz], c, e, [u0, y1 - y0]);
      g.idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
  });
  if (roof) {
    const flat = [], holes = [];
    rings.forEach((r, i) => { if (i) holes.push(flat.length / 2); r.forEach(p => flat.push(p[0], p[1])); });
    const tri = earcut(flat, holes);
    const base = g.nv;
    for (let i = 0; i < flat.length; i += 2) g.vert([flat[i], y1, flat[i + 1]], [0, 1, 0], roof.c, roof.e, [flat[i], flat[i + 1]]);
    for (let i = 0; i < tri.length; i += 3) {
      // ensure upward facing (counter-clockwise when viewed from +y): check with first triangle orientation
      const a = tri[i], b = tri[i + 1], c = tri[i + 2];
      const ax = flat[a * 2], az = flat[a * 2 + 1], bx = flat[b * 2], bz = flat[b * 2 + 1], cx = flat[c * 2], cz = flat[c * 2 + 1];
      const cr = (bx - ax) * (cz - az) - (bz - az) * (cx - ax);
      if (cr < 0) g.idx.push(base + a, base + b, base + c); else g.idx.push(base + a, base + c, base + b);
    }
  }
}

function centroid(ring) { let x = 0, z = 0; ring.forEach(p => { x += p[0]; z += p[1]; }); return [x / ring.length, z / ring.length]; }

// ------------------------------------------------------------------ gates / stands
// Stand layout (data/sfo_stands.js, rebuilt 24 Sep 2026 by tools/stands/build_stands.py from OSM lead-ins, SFO stand
// names, NAIP 2024 and ADS-B; docs/research/stands_rebuild.md): one entry per physical stand position with its nose
// stop point, parked heading, largest aircraft class, jet bridges (building attach, rotunda, parked cab), and the
// fields the matcher can use: gate (display number), excl (stands that cannot be occupied at the same time),
// alt_of (alternative position of another stand, e.g. B5S of B5), span_max / len_max (per-stand limits where the class
// envelope is too coarse, e.g. E10U/E12, F9/F10), a380 (only these stands may take an A380 / 747-8), leadin (the painted
// lead-in polyline, OSM way, world x/z) and the bridge fields below.
const CLASS_MAX = { B: { span: 28.5, len: 37 }, C: { span: 36.5, len: 45 }, CL: { span: 38.5, len: 48 }, D: { span: 52, len: 62 }, E: { span: 61, len: 68 }, EL: { span: 65.5, len: 77 }, F: { span: 80, len: 80 } };
export function standGates(stands) {
  const o = worldToST(0, 0);
  const dirST = (d) => { const p = worldToST(d[0], d[1]); const v = [p[0] - o[0], p[1] - o[1]]; const l = Math.hypot(v[0], v[1]); return [v[0] / l, v[1] / l]; };
  const gates = [];
  for (const s of stands.stands) {
    const h = s.hdg * Math.PI / 180; const fw = [Math.sin(h), -Math.cos(h)]; // world (x,z) unit vector of the parked heading
    const dir = dirST(fw); const nose = worldToST(s.nose[0], s.nose[1]);
    // bridge fields from the data (review round 1): rotundaW (OSM rotunda, moved back along the walkway where it was
    // infeasible), walkW (fixed walkway polyline building -> rotunda), cabW + cabPose ('docked' / 'parked' as OSM mapped
    // it - do not use a docked cab as the rest pose), stowW (a rest pose for the tunnel end clear of every aircraft the
    // stand and its neighbours accept), rotundaMaxR (how large the rotunda may be drawn without touching another)
    const bridges = s.bridges.map(b => ({ gate: b.gate, attach: worldToST(b.attach[0], b.attach[1]), attachW: b.attach, door: b.door,
      rotundaW: b.rotunda || null, cabW: b.cab || null, walkW: b.walk || null, cabPose: b.cab_pose || null, stowW: b.stow || null,
      rotundaMaxR: b.rotunda_max_r ?? null }));
    const cm = CLASS_MAX[s.cls] || CLASS_MAX.C; const wide = cm.span > 40;
    const maxSpan = s.span_max ? Math.min(cm.span, s.span_max + 0.1) : cm.span;
    const maxLen = s.len_max ? Math.min(cm.len, s.len_max + 0.1) : cm.len;
    gates.push({
      id: s.name, name: s.name, alias: s.alias || [], letter: s.letter, pier: s.letter, cls: s.cls, maxSpan, maxLen, src: s.src,
      gate: s.gate || s.name, excl: s.excl || [], altOf: s.alt_of || null, aodb: s.aodb || [], a380: !!s.a380, tightWith: s.tight_with || [],
      leadinW: s.leadin || null, sharesBridgesOf: s.shares_bridges_of || null,
      nose, dir, outN: [-dir[0], -dir[1]], attach: bridges.length ? bridges[0].attach : nose, bridges, wide, len: cm.len, span: cm.span,
      bridge: bridges.length > 0, remote: false, hdg: s.hdg, world: { x: s.nose[0], z: s.nose[1], hdg: s.hdg }, empty: true, acType: null, dynamic: false,
    });
  }
  for (const r of stands.remote || []) {
    const nose = worldToST(r.x, r.z);
    const dir = r.hdg != null ? dirST([Math.sin(r.hdg * Math.PI / 180), -Math.cos(r.hdg * Math.PI / 180)]) : [0, 1];
    gates.push({ id: r.name, name: r.name, alias: [], letter: r.name[0], pier: r.name[0], cls: 'E', maxSpan: 65.5, maxLen: 77, nose, dir, outN: [-dir[0], -dir[1]], attach: nose, bridges: [], gate: r.name, excl: [], hdg: r.hdg,
      wide: true, len: 70, span: 64, bridge: false, remote: true, world: { x: r.x, z: r.z, hdg: r.hdg ?? undefined }, empty: true, acType: null, dynamic: false });
  }
  return gates;
}
export function liveGates(data) {
  const gates = [];
  const o = worldToST(0, 0);
  const dirST = (d) => { const p = worldToST(d[0], d[1]); const v = [p[0] - o[0], p[1] - o[1]]; const l = Math.hypot(v[0], v[1]); return [v[0] / l, v[1] / l]; };
  const wideLetters = new Set(['A', 'G']);
  for (const g of data.gates) {
    if (g.dup) continue;
    const bridge = g.level === 2 && !g.variant;
    const attach = worldToST(g.edge[0], g.edge[1]);
    const outN = dirST(g.out);
    const wide = wideLetters.has(g.letter);
    const gap = wide ? 26 : 22;
    const nose = bridge ? [attach[0] + outN[0] * gap, attach[1] + outN[1] * gap] : worldToST(g.x, g.z);
    gates.push({
      id: g.name, name: g.name, letter: g.letter, pier: g.letter, attach, outN, dir: [-outN[0], -outN[1]], nose, wide, cls: wide ? 'E' : 'C', len: wide ? 70 : 42, span: wide ? 64 : 36,
      bridge, remote: !bridge, world: { x: g.x, z: g.z, edge: g.edge, out: g.out }, empty: true, acType: null, dynamic: false,
    });
  }
  return gates;
}

// ------------------------------------------------------------------ buildings
const HALL_H = { 'Harvey Milk Terminal 1': 21, 'Terminal 2': 19, 'Terminal 3': 21, 'International Terminal': 27 };
const STRUCT_H = { atc: 10, garage: 18, building: 18, hangar: 32, hotel: 36, airtrain: 13 };
const STRUCT_H_BY_NAME = { 'Central Parking Garage': 22, 'Garage A': 21, 'Garage G': 21, 'Long-Term Parking Garage 1': 16, 'Long-Term Parking Garage 2': 16, 'Rental Car Center': 26, 'Consolidated Administration Campus': 20, 'Grand Hyatt Hotel': 38, 'Super Bay Hangar Building': 34 };

export function buildLiveBuildings(data, parts = null) {
  const g = new Geo();
  if (parts) {
    // terminal complex part by part (see terminals.js)
    buildTerminals(parts, g);
  } else {
    // terminal complex: concourse level + glass upper storey
    for (const poly of data.terminalComplex) {
      extrudePoly(g, poly, G, G + 5.0, MAT.concreteDark, null);
      extrudePoly(g, poly, G + 5.0, G + 13.5, MAT.glass, MAT.roof);
    }
    // main halls rise above the concourses
    for (const t of data.terminals) {
      const h = HALL_H[t.name] || 20;
      for (const poly of t.polys) {
        if (Math.abs(ringArea(poly[0])) < 4000) continue;
        extrudePoly(g, poly, G + 13.5, G + h, MAT.glass, MAT.metalRoof);
      }
    }
  }
  // structures
  const tower = data.structures.find(s => s.kind === 'atc');
  const seen = new Set();
  for (const s of data.structures) {
    if (s.kind === 'rail' || s.kind === 'atc') continue;
    const key = s.name.replace(/\s+/g, ' ').toLowerCase().replace(/garaga/, 'garage');
    if (s.kind === 'airtrain') { if (seen.has(key)) continue; seen.add(key); }
    const h = STRUCT_H_BY_NAME[s.name] || STRUCT_H[s.kind] || 12;
    const wall = s.kind === 'garage' ? MAT.garage : s.kind === 'hangar' ? MAT.corrugated : s.kind === 'hotel' ? MAT.hotel : s.kind === 'airtrain' ? MAT.concrete : MAT.concrete;
    const roof = s.kind === 'garage' ? MAT.parkRoof : s.kind === 'hangar' ? MAT.metalRoof : MAT.roof;
    for (const poly of s.polys) {
      if (s.kind === 'airtrain') { extrudePoly(g, poly, G + 7.5, G + h, MAT.glass, MAT.metalRoof); extrudePoly(g, poly.map(r => shrink(r, 0.35)), G, G + 7.5, MAT.concrete, null); }
      else extrudePoly(g, poly, G, G + h, wall, roof);
    }
  }
  // control tower (lathe) at the ATC footprint
  let towerPos = null;
  if (tower && parts) { const T = buildTower(g, tower.polys[0][0]); towerPos = T.cab; }
  else if (tower) {
    const c = centroid(tower.polys[0][0]); towerPos = [c[0], G, c[1]];
    extrudePoly(g, tower.polys[0], G, G + 10, MAT.concrete, MAT.roof);
    const M = m4.translate(c[0], G, c[1]);
    g.lathe([[6.8, 0], [6.8, 10], [6.0, 14], [4.9, 28], [4.3, 44], [5.0, 50], [7.5, 54], [9.0, 56.5]], 40, MAT.towerShaft.c, MAT.towerShaft.e, M);
    g.lathe([[9.0, 56.5], [9.4, 57.2]], 40, MAT.darkMetal.c, MAT.darkMetal.e, M);
    g.lathe([[9.4, 57.2], [10.4, 63.4]], 40, MAT.towerGlass.c, MAT.towerGlass.e, M);
    g.lathe([[10.4, 63.4], [11.2, 64.2], [11.2, 65.4], [8.0, 66.4], [3.0, 67.2]], 40, MAT.white.c, MAT.white.e, M, true);
    g.cylinder(0.35, 9, 8, MAT.darkMetal.c, MAT.darkMetal.e, m4.translate(c[0], G + 67, c[1]));
  }
  // AirTrain guideway: thin elevated deck from the rail footprint, on columns sampled along its outline
  const rail = data.structures.find(s => s.kind === 'rail');
  if (rail) {
    for (const poly of rail.polys) {
      extrudePoly(g, poly, G + 9.0, G + 10.6, MAT.concrete, MAT.concrete);
      const r = poly[0]; let acc = 0;
      for (let i = 0; i < r.length; i++) { const a = r[i], b = r[(i + 1) % r.length]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); acc += L; if (acc > 45) { acc = 0; g.box([a[0] - 0.8, G, a[1] - 0.8], [a[0] + 0.8, G + 9.0, a[1] + 0.8], MAT.concrete.c, MAT.concrete.e); } }
    }
  }
  return { geo: g.data(), towerPos };
}
function shrink(ring, f) { const c = centroid(ring); return ring.map(p => [c[0] + (p[0] - c[0]) * (1 - f * 0.1), c[1] + (p[1] - c[1]) * (1 - f * 0.1)]); }

// rectangle around a stand's largest aircraft (airport grid s,t): `fwd` m ahead of the nose, `side` m beyond each
// wing tip, `aft` m behind the tail
export function standEnvelopeST(g, fwd = 5, side = 7.5, aft = 7.5) {
  const d = g.dir, n = [-d[1], d[0]]; const hw = (g.maxSpan || g.span) / 2 + side, L = (g.maxLen || g.len);
  const a = [g.nose[0] + d[0] * fwd, g.nose[1] + d[1] * fwd], b = [g.nose[0] - d[0] * (L + aft), g.nose[1] - d[1] * (L + aft)];
  return [[a[0] + n[0] * hw, a[1] + n[1] * hw], [a[0] - n[0] * hw, a[1] - n[1] * hw], [b[0] - n[0] * hw, b[1] - n[1] * hw], [b[0] + n[0] * hw, b[1] + n[1] * hw]];
}
export function inStandEnvelope(gates, x, z, margin = 0) {
  const st = worldToST(x, z);
  for (const g of gates) {
    if (!g.bridge) continue; const d = g.dir; const rx = st[0] - g.nose[0], rt = st[1] - g.nose[1];
    const along = -(rx * d[0] + rt * d[1]), lat = rx * -d[1] + rt * d[0];
    if (along > -5 - margin && along < (g.maxLen || g.len) + 7.5 + margin && Math.abs(lat) < (g.maxSpan || g.span) / 2 + 7.5 + margin) return g;
  }
  return null;
}
// runway end zones beyond the pavement ends (re-measured 24 Sep 2026 on NAIP 2024, USDA public domain, 0.5 m world
// raster; oriented strips along the NASR runway axes, tools/stands/ README in docs/research/stands_rebuild.md §6):
//   blast pads (type 1, runway width 200 ft, yellow chevrons ~30.5 m apart):
//     10L 269 m (dark pad edge; OSM stopway 270 m, FAA diagram ~260 m), 10R 231 m (chevrons end at ~230 m, the pad
//     merges into taxiway pavement - length from OSM 231 m, FAA diagram ~240 m), 28R 98 m, 28L 98 m (pad edge at
//     the seawall road; OSM 91 / 95 m, FAA diagram ~90 m). The earlier 108 m (Google screenshots) is replaced.
//   EMAS beds at 1L/1R/19L/19R (type 2): 35 ft (10.7 m) beyond the runway end (Runway Safe SFO reference). Measured on
//     NAIP 2024 (oriented patches along the NASR axes, 0.25 m/px, 24 Sep 2026; review round 1 + re-check): imaged far
//     edge from the runway end 1L ~143.9 m, 19R ~135.5 m, 1R ~124.1 m, 19L ~134.8 m -> bed lengths (far edge - 10.67)
//     1L 133.2, 19R 124.8, 1R 113.4, 19L 124.1 m; imaged width 69.2-69.4 m at all four (centred on the axis within
//     0.25 m) -> EMAS_W 69.3 m (was 66 m).
//   EMAS chevrons (review round 2, re-measured 24 Sep 2026: yellow peaks on the runway axis, 0.05 m samples, NAIP 2024):
//     first apex beyond the runway end 1L 17.0, 19R 16.05, 1R 17.1, 19L 16.5 m -> chev0 = that - EMAS_SETBACK (m from the
//     bed entry); apex spacing 30.4-30.8 m at all four = 100 ft (30.48 m). Blast-pad chevrons (drawn by js/shaders/ground.js,
//     not owned here): first apex 10L 16.9, 10R 16.45, 28R 17.2, 28L 16.9 m beyond the end, spacing 30.5 m.
export const END_ZONES = [
  { rw: 0, end: 0, type: 1, len: 269 }, { rw: 1, end: 0, type: 1, len: 231 },
  { rw: 0, end: 1, type: 1, len: 98 }, { rw: 1, end: 1, type: 1, len: 98 },
  { rw: 2, end: 0, type: 2, len: 133.2, chev0: 6.3 }, { rw: 2, end: 1, type: 2, len: 124.8, chev0: 5.4 },
  { rw: 3, end: 0, type: 2, len: 113.4, chev0: 6.4 }, { rw: 3, end: 1, type: 2, len: 124.1, chev0: 5.8 },
];
export const EMAS_SETBACK = 10.67, EMAS_W = 69.3;
export function endZoneRects() {
  return END_ZONES.map(z => {
    const r = RWY[z.rw]; const hw = z.type === 2 ? EMAS_W / 2 + 2 : RWY_W / 2;
    const u0 = z.end === 0 ? r.a0 - z.len - (z.type === 2 ? EMAS_SETBACK + 3 : 0) : r.a1, u1 = z.end === 0 ? r.a0 : r.a1 + z.len + (z.type === 2 ? EMAS_SETBACK + 3 : 0);
    const rect = r.axis === 0 ? [[u0, r.c - hw], [u1, r.c - hw], [u1, r.c + hw], [u0, r.c + hw]] : [[r.c - hw, u0], [r.c + hw, u0], [r.c + hw, u1], [r.c - hw, u1]];
    return { ...z, rect };
  });
}
export function rwEndUniform() {
  const u = new Array(16).fill(0);
  for (const z of END_ZONES) { u[z.rw * 4 + z.end * 2] = z.type; u[z.rw * 4 + z.end * 2 + 1] = z.type === 2 ? EMAS_SETBACK : z.len; }
  return u;
}
// ------------------------------------------------------------------ pavement map (same channel layout as paintAirportMap)
export function paintAirportMapReal(data, gates, res = APT_RECT.res, details = null, extra = {}) {
  const W = Math.round(APT_RECT.w / res), H = Math.round(APT_RECT.h / res);
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const cx = cv.getContext('2d', { willReadFrequently: true });
  const P = (s, t) => [(s - APT_RECT.s0) / res, (APT_RECT.t0 + APT_RECT.h - t) / res];
  const Pw = (x, z) => { const st = worldToST(x, z); return P(st[0], st[1]); };
  const pathRings = (rings) => { cx.beginPath(); for (const r of rings) { r.forEach((p, i) => { const q = Pw(p[0], p[1]); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.closePath(); } };
  const polyST = (pts) => { cx.beginPath(); pts.forEach((p, i) => { const q = P(p[0], p[1]); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.closePath(); };
  const lineST = (pts, w) => { cx.lineWidth = w / res; cx.beginPath(); pts.forEach((p, i) => { const q = P(p[0], p[1]); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.stroke(); };
  cx.lineJoin = 'round'; cx.lineCap = 'round';
  const layer = (fn) => { cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H); cx.fillStyle = '#fff'; cx.strokeStyle = '#fff'; fn(); return cx.getImageData(0, 0, W, H).data; };
  const complexRings = data.terminalComplex.flat();
  const apron = () => {
    if (details && details.apron) {
      // inferred ramp outline (tools/build_airfield_details.py) + the building footprint itself
      for (const poly of details.apron) { pathRings(poly); cx.fill('evenodd'); }
      for (const poly of data.terminalComplex) { pathRings([poly[0]]); cx.fill(); cx.lineWidth = 2 * 6 / res; cx.stroke(); }
    } else {
      // fallback: ramp around the terminal complex as a buffer of its outline
      for (const poly of data.terminalComplex) { pathRings([poly[0]]); cx.fill(); cx.lineWidth = 2 * 105 / res; cx.stroke(); }
    }
    // remote stands
    gates.filter(g => g.remote).forEach(g => { const q = Pw(g.world.x, g.world.z); cx.beginPath(); cx.arc(q[0], q[1], 40 / res, 0, 7); cx.fill(); });
    // every surveyed stand is paved (the whole aircraft envelope plus clearance)
    for (const g of gates) { if (!g.bridge) continue; polyST(standEnvelopeST(g, 6, 6, 14)); cx.fill(); }
    // extra pavement patches where aircraft have been seen parked outside the mapped ramp
    for (const pt of (details && details.patches) || []) { const q = Pw(pt[0], pt[1]); cx.beginPath(); cx.arc(q[0], q[1], pt[2] / res, 0, 7); cx.fill(); }
  };
  const farFromTerminal = (a) => { const c = a.pts.reduce((s, p) => [s[0] + p[0] / a.pts.length, s[1] + p[1] / a.pts.length], [0, 0]); return Math.hypot(c[0] + 900, c[1] + 850) > 750; };
  const pave = layer(() => {
    apron();
    if (!details) APRONS.filter(farFromTerminal).forEach(a => { polyST(a.pts); cx.fill(); });
    RWY.forEach(r => { const hw = RWY_W / 2 + 7.5; const pts = r.axis === 0 ? [[r.a0 - 60, r.c - hw], [r.a1, r.c - hw], [r.a1, r.c + hw], [r.a0 - 60, r.c + hw]] : [[r.c - hw, r.a0 - 60], [r.c + hw, r.a0 - 60], [r.c + hw, r.a1 + 60], [r.c - hw, r.a1 + 60]]; polyST(pts); cx.fill(); });
    for (const t of data.taxiways) for (const poly of t.polys) { pathRings(poly); cx.fill('evenodd'); cx.lineWidth = 3.0 / res; cx.stroke(); }
    for (const r of data.runways) for (const poly of r.polys) { pathRings(poly); cx.fill('evenodd'); }
    landside().forEach(l => { if (l.kind === 'roadline') lineST(l.pts, l.w); else { polyST(l.pts); cx.fill(); } });
    // blast pads / EMAS beds beyond the runway ends, and the paved islands carrying the green no-taxi paint
    for (const z of extra.endZones || []) { polyST(z.rect); cx.fill(); }
    for (const poly of (extra.paint && extra.paint.polys) || []) { pathRings(poly); cx.fill('evenodd'); }
    for (const poly of (extra.pavement && extra.pavement.polys) || []) { pathRings(poly); cx.fill('evenodd'); }
  });
  const paint = extra.paint ? layer(() => { for (const poly of extra.paint.polys) { pathRings(poly); cx.fill('evenodd'); } }) : null;
  const conc = layer(() => {
    apron(); if (!details) APRONS.filter(a => a.conc && farFromTerminal(a)).forEach(a => { polyST(a.pts); cx.fill(); });
    const P2 = extra.pavement; if (P2) P2.polys.forEach((poly, i) => { if (P2.conc && P2.conc[i]) { pathRings(poly); cx.fill('evenodd'); } });
  });
  const wear = layer(() => {
    // tyre and oil wear on the surveyed stands: nose-gear track along the lead-in line, stains under the main gear
    gates.filter(g => g.bridge).forEach(g => {
      cx.globalAlpha = 0.35; lineST([g.nose, [g.nose[0] - g.dir[0] * (g.len + 25), g.nose[1] - g.dir[1] * (g.len + 25)]], 2.5);
      const n = [-g.dir[1], g.dir[0]]; const ex = g.wide ? 5.5 : 3.8; const c = [g.nose[0] - g.dir[0] * g.len * 0.42, g.nose[1] - g.dir[1] * g.len * 0.42];
      cx.globalAlpha = 0.5;
      for (const sg of [-1, 1]) { const q = P(c[0] + n[0] * ex * sg, c[1] + n[1] * ex * sg); cx.beginPath(); cx.ellipse(q[0], q[1], 2.2 / res, 2.2 / res, 0, 0, 7); cx.fill(); }
      const q = P(g.nose[0] - g.dir[0] * 5, g.nose[1] - g.dir[1] * 5); cx.beginPath(); cx.ellipse(q[0], q[1], 1.6 / res, 1.6 / res, 0, 0, 7); cx.fill();
    });
    cx.globalAlpha = 1;
  });
  const cat = layer(() => { landside().forEach(l => { cx.fillStyle = cx.strokeStyle = l.kind === 'parking' ? '#999' : '#fff'; if (l.kind === 'roadline') lineST(l.pts, l.w); else { polyST(l.pts); cx.fill(); } }); });
  // pavement inside the terminal footprint is building, not ramp: keep as pavement (hidden under roofs)
  const out = new Uint8Array(W * H * 4);
  for (let i = 0; i < W * H; i++) { out[i * 4] = pave[i * 4]; out[i * 4 + 1] = conc[i * 4]; out[i * 4 + 2] = wear[i * 4]; out[i * 4 + 3] = cat[i * 4]; }
  let paintRGBA = null;
  if (paint) { paintRGBA = new Uint8Array(W * H * 4); for (let i = 0; i < W * H; i++) { paintRGBA[i * 4] = paint[i * 4]; paintRGBA[i * 4 + 3] = 255; } }
  cv.width = cv.height = 1; // release the canvas backing store
  // paved-surface lookup (world x,z) for placing edge lights
  const paved = (x, z) => { const q = Pw(x, z); const i = Math.floor(q[0]), j = Math.floor(q[1]); if (i < 0 || j < 0 || i >= W || j >= H) return false; return out[(j * W + i) * 4] > 127; };
  return { data: out, w: W, h: H, paved, paint: paintRGBA };
}

// ------------------------------------------------------------------ stand lead-in lines & stop bars (yellow ribbons)
export function buildStandMarkings(gates) {
  const pos = [], col = [], idx = [];
  const Y = G + 0.02; const yellow = [0.85, 0.62, 0.08, 1], red = [0.7, 0.08, 0.06, 1];
  const quad = (a, b, w, c) => {
    const dx = b[0] - a[0], dy = b[1] - a[1]; const L = Math.hypot(dx, dy); if (L < 1e-3) return;
    const nx = -dy / L * w / 2, ny = dx / L * w / 2; const base = pos.length / 3;
    [[a[0] + nx, a[1] + ny], [a[0] - nx, a[1] - ny], [b[0] - nx, b[1] - ny], [b[0] + nx, b[1] + ny]].forEach(p => { const wp = stToWorld(p[0], p[1], Y); pos.push(...wp); col.push(...c); });
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  };
  for (const g of gates) {
    if (!g.bridge) continue;
    const d = g.dir; const n = [-d[1], d[0]];
    const start = [g.nose[0] + d[0] * 2, g.nose[1] + d[1] * 2];
    const end = [g.nose[0] - d[0] * 95, g.nose[1] - d[1] * 95];
    quad(start, end, 0.18, yellow);
    // stop bar for the nose gear (~ 5 m behind the nose) and a red envelope line near the building
    const sb = [g.nose[0] - d[0] * 5, g.nose[1] - d[1] * 5];
    quad([sb[0] + n[0] * 1.5, sb[1] + n[1] * 1.5], [sb[0] - n[0] * 1.5, sb[1] - n[1] * 1.5], 0.3, yellow);
    const env = [g.attach[0] + g.outN[0] * 6, g.attach[1] + g.outN[1] * 6];
    quad([env[0] + n[0] * 9, env[1] + n[1] * 9], [env[0] - n[0] * 9, env[1] - n[1] * 9], 0.25, red);
  }
  return { pos: new Float32Array(pos), col: new Float32Array(col), idx: new Uint32Array(idx) };
}
