// sha3d buildings (package P2d): geometry for the parametric terminal parts, towers, hangars, the Hongqiao hub and the
// context LOD blocks of data/sha_buildings3d.js (tools/buildings/build_buildings3d.py) and data/sha_airport.js.
// The wall / cap / rooftop-plant / skylight helpers are forked from sfo3d@e3218d6 js/live/terminals.js (walls(), cap(),
// rooftop(), skylights(), inside(), edgeDist()), rewritten for injected data; NO SFO geometry, dimension or data is used.
//
// Conventions: geometry is built with y = height above the nominal ground (0) and drawn with the model matrix
// translate(0, GROUND_Y, 0), so the object shader's storey patterns (mat 1 / 6: v = local y) start at the ground; the
// control tower is built around its own axis (local origin = tower foot) for the cab-glass mullions (mat 12 uses the local
// angle). Polygons: [[outer, hole, ...], ...], outer rings positive shoelace area in (x, z), holes negative.
// Every colour, band height, depth and spacing below is a rendering parameter [inf] read from the open-licence photos
// (docs/phase1/photos_credits.md: proportions only, nothing textured or traced); heights come from the data (B3 / rules).
// Object-shader materials (js/shaders/objects.js): 1 glass curtain wall, 2 concrete panels, 3 parking facade, 4 corrugated
// metal, 5 flat roof, 6 punched windows, 11 parking roof, 12 tower-cab glass, 13 hangar door, 15 apron-level service facade, 17 bank kerb (fades out at distance).
import { Geo } from '../geom.js';
import { m4, v3 } from '../math.js';
import { earcut } from '../live/earcut.js';

const mat = (c, rough, metal, id, emis = 0) => ({ c: [c[0], c[1], c[2], 1], e: [rough, metal, id, emis] });
export const M = {
  // T2 (photos 09, 11, 14-17): grey-framed glass curtain walls, light-grey metal fascia and roofs, grey apron level
  glass: mat([0.1, 0.1, 0.1], 0.1, 0, 1),
  fascia: mat([0.74, 0.75, 0.76], 0.35, 0.4, 0),
  fasciaDark: mat([0.36, 0.37, 0.39], 0.4, 0.5, 0),
  // roofs (fix round 1, review L5 "snow city"): terminal / hangar roofs ~0.45 grey metal (was 0.52-0.58, read as white
  // from above); aerials 21 / 22 / 24 show mid-grey metal roofs [inf]
  roofMetal: mat([0.44, 0.45, 0.46], 0.45, 0.5, 5),
  roofLight: mat([0.45, 0.45, 0.44], 0.8, 0, 5),
  roofDark: mat([0.33, 0.33, 0.34], 0.9, 0, 5),
  service: mat([0.52, 0.53, 0.55], 0.75, 0.1, 15),
  ceiling: mat([0.80, 0.80, 0.78], 0.7, 0, 0),
  plant: mat([0.70, 0.71, 0.72], 0.5, 0.4, 0),
  vent: mat([0.25, 0.26, 0.27], 0.6, 0.3, 0),
  // T1 (photos 01-05): white concourse bands, dark apron-level recess, silver louvre bands, glazed clerestory; the central
  // hall's airside face is a light fritted glass wall (photo 02)
  frit: mat([0.40, 0.44, 0.47], 0.15, 0.35, 0),
  white: mat([0.86, 0.87, 0.87], 0.45, 0.1, 0),
  recess: mat([0.16, 0.17, 0.18], 0.8, 0.1, 15),
  louvre: mat([0.66, 0.68, 0.70], 0.35, 0.7, 0),
  louvreGap: mat([0.18, 0.19, 0.21], 0.6, 0.3, 0),
  panelLight: mat([0.66, 0.66, 0.64], 0.85, 0, 2),      // fix 1 (L5): 0.78 -> 0.66, 0.74 -> 0.60 (concrete / tile, not paint white) [inf]
  officeLight: mat([0.60, 0.59, 0.56], 0.85, 0, 6),
  whiteWin: mat([0.84, 0.85, 0.85], 0.6, 0, 6),
  // tower (photo 02): pale concrete, dark slot, dark windows, tinted cab glass, light roof slab
  concrete: mat([0.72, 0.71, 0.68], 0.85, 0, 2),
  slot: mat([0.05, 0.06, 0.07], 0.1, 0, 0),
  window: mat([0.05, 0.06, 0.07], 0.12, 0, 0),
  cab: mat([0.05, 0.06, 0.07], 0.05, 0, 12),
  terrace: mat([0.26, 0.26, 0.255], 0.9, 0, 5),          // head-top terrace (roof membrane) [inf]
  console: mat([0.10, 0.095, 0.09], 0.9, 0, 0, 0.3),     // cab floor / consoles: matte charcoal + a faint fill (no AO under the cab roof, so a light floor turns sky-blue in the Tower view) [inf]
  // hangars: light corrugated cladding, door leaves, darker door header
  clad: mat([0.64, 0.65, 0.66], 0.55, 0.35, 4),          // fix 1 (L5): 0.74 -> 0.64 (weathered light metal cladding) [inf]
  cladDark: mat([0.46, 0.47, 0.49], 0.55, 0.35, 4),
  door: mat([0.62, 0.64, 0.66], 0.5, 0.4, 13),
  // hub / others
  parking: mat([0.56, 0.55, 0.53], 0.9, 0, 3),
  parkingRoof: mat([0.34, 0.34, 0.35], 0.9, 0, 11),
  station: mat([0.1, 0.1, 0.1], 0.1, 0, 1),
  column: mat([0.70, 0.70, 0.69], 0.6, 0.2, 0),
};

const ringArea = (r) => { let a = 0; for (let i = 0; i < r.length; i++) { const p = r[i], q = r[(i + 1) % r.length]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; };
function inRing(r, x, z) { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[i], b = r[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
export function insidePolys(polys, x, z) { return polys.some(pl => inRing(pl[0], x, z) && !pl.slice(1).some(h => inRing(h, x, z))); }
export function edgeDist(polys, x, z) {
  let d = 1e9;
  for (const pl of polys) for (const r of pl) for (let i = 0; i < r.length; i++) {
    const a = r[i], b = r[(i + 1) % r.length]; const dx = b[0] - a[0], dz = b[1] - a[1]; const l2 = dx * dx + dz * dz || 1;
    const t = Math.max(0, Math.min(1, ((x - a[0]) * dx + (z - a[1]) * dz) / l2)); d = Math.min(d, Math.hypot(x - a[0] - dx * t, z - a[1] - dz * t));
  }
  return d;
}
// deterministic pseudo-random sequence (Park-Miller, as sfo3d)
let seed = 7; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
export function hash01(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return ((h >>> 0) % 10007) / 10007; }

// ------------------------------------------------------------------------------------------------ walls, caps, slabs
// walls of one ring from the layers [[y0, y1, mat], ...]; outward = true for outer rings (positive area), false for holes
// (walls face into the hole). Quads are given counter-clockwise as seen from outside (Geo.quad convention).
export function wallRing(g, ring, layers, outward = true) {
  const pos = ringArea(ring) > 0; const n = ring.length;
  for (let i = 0; i < n; i++) {
    const a = ring[i], b = ring[(i + 1) % n]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); if (L < 0.05) continue;
    // left-normal order (a, b) faces left; outward normal of a positive ring is the right normal -> reverse
    const leftOut = (pos !== outward);
    const Ls = typeof layers === 'function' ? layers(leftOut ? -(b[1] - a[1]) / L : (b[1] - a[1]) / L, leftOut ? (b[0] - a[0]) / L : -(b[0] - a[0]) / L) : layers;
    for (const [y0, y1, mt] of Ls) {
      if (y1 - y0 < 0.02) continue;
      const A0 = [a[0], y0, a[1]], B0 = [b[0], y0, b[1]], B1 = [b[0], y1, b[1]], A1 = [a[0], y1, a[1]];
      if (leftOut) g.quad(A0, B0, B1, A1, mt.c, mt.e); else g.quad(B0, A0, A1, B1, mt.c, mt.e);
    }
  }
}
export function wallPolys(g, polys, layers) { for (const pl of polys) pl.forEach((r, i) => wallRing(g, r, layers, i === 0)); }
// horizontal cap of polygons (with holes) at y; up = true faces up
export function capPolys(g, polys, y, mt, up = true) {
  for (const pl of polys) {
    const flat = [], holes = [];
    pl.forEach((r, i) => { if (i) holes.push(flat.length / 2); r.forEach(p => flat.push(p[0], p[1])); });
    const tri = earcut(flat, holes); const base = g.nv;
    for (let i = 0; i < flat.length; i += 2) g.vert([flat[i], y, flat[i + 1]], [0, up ? 1 : -1, 0], mt.c, mt.e, [flat[i], flat[i + 1]]);
    for (let i = 0; i < tri.length; i += 3) {
      const a = tri[i], b = tri[i + 1], c = tri[i + 2];
      const cr = (flat[b * 2] - flat[a * 2]) * (flat[c * 2 + 1] - flat[a * 2 + 1]) - (flat[b * 2 + 1] - flat[a * 2 + 1]) * (flat[c * 2] - flat[a * 2]);
      // a triangle with positive (x, z) cross product is seen clockwise from above (+y): flip for an upward face
      if ((cr > 0) === up) g.idx.push(base + a, base + c, base + b); else g.idx.push(base + a, base + b, base + c);
    }
  }
}
// a slab between y0 and y1 (top, underside, edges)
export function slab(g, polys, y0, y1, top, edge, under) { capPolys(g, polys, y1, top, true); capPolys(g, polys, y0, under || edge, false); wallPolys(g, polys, [[y0, y1, edge]]); }
// parapet: a thin upstand along the outer rings (inner face omitted: only seen from above at a distance)
export function parapet(g, polys, y, hgt, mt) { wallPolys(g, polys, [[y, y + hgt, mt]]); }

// ------------------------------------------------------------------------------------------------ roof furniture
// rooftop plant (air handlers, fans, louvred enclosures) inside the roof, away from its edges (sfo3d rooftop())
export function rooftop(g, part, y, per = 900, minEdge = 6) {
  const R = part.polys; const [cx, cz] = part.center; const ax = part.axis, ay = [-ax[1], ax[0]];
  const span = part.len / 2 + 10, wspan = part.wid / 2 + 10; const n = Math.round(part.area / per);
  for (let k = 0, tries = 0; k < n && tries < n * 14; tries++) {
    const s = (rnd() * 2 - 1) * span, t = (rnd() * 2 - 1) * wspan; const x = cx + ax[0] * s + ay[0] * t, z = cz + ax[1] * s + ay[1] * t;
    if (!insidePolys(R, x, z) || edgeDist(R, x, z) < minEdge) continue;
    const Mx = m4.basis([ax[0], 0, ax[1]], [0, 1, 0], [x, y, z]); const kind = rnd();
    if (kind < 0.45) { const l = 4 + rnd() * 5, w = 2.2 + rnd() * 1.5, h = 1.6 + rnd() * 0.8; g.box([-l / 2, 0, -w / 2], [l / 2, h, w / 2], M.plant.c, M.plant.e, Mx); for (let f = 0; f < Math.floor(l / 1.6); f++) g.cylinder(0.55, 0.25, 10, M.vent.c, M.vent.e, m4.mul(Mx, m4.translate(-l / 2 + 0.8 + f * 1.6, h, 0)), true); }
    else if (kind < 0.75) { const r = 0.5 + rnd() * 0.4; g.cylinder(r, 0.9, 10, M.plant.c, M.plant.e, Mx, true); g.cylinder(r * 1.25, 0.12, 10, M.vent.c, M.vent.e, m4.mul(Mx, m4.translate(0, 0.9, 0)), true); }
    else { const l = 6 + rnd() * 6, w = 4 + rnd() * 3; g.box([-l / 2, 0, -w / 2], [l / 2, 2.6, w / 2], M.fascia.c, M.fascia.e, Mx); }
    k++;
  }
}
// glazed ridge skylight along the principal axis where the axis lies well inside the roof (sfo3d skylights())
export function skylights(g, part, y, minEdge = 7, halfW = 1.8) {
  const R = part.polys; const [cx, cz] = part.center; const ax = part.axis;
  let run = null; const out = [];
  for (let s = -part.len / 2; s <= part.len / 2; s += 3) {
    const x = cx + ax[0] * s, z = cz + ax[1] * s; const ok = insidePolys(R, x, z) && edgeDist(R, x, z) > minEdge;
    if (ok) { if (!run) run = [s, s]; else run[1] = s; } else if (run) { out.push(run); run = null; }
  }
  if (run) out.push(run);
  for (const [s0, s1] of out) {
    if (s1 - s0 < 12) continue;
    const c = [cx + ax[0] * (s0 + s1) / 2, cz + ax[1] * (s0 + s1) / 2]; const Mx = m4.basis([ax[0], 0, ax[1]], [0, 1, 0], [c[0], y, c[1]]);
    const L = s1 - s0 - 4; g.box([-L / 2, 0, -halfW], [L / 2, 0.5, halfW], M.fascia.c, M.fascia.e, Mx);
    for (let q = -L / 2; q <= L / 2 + 0.01; q += 3.0) g.box([q - 0.07, 0.5, -halfW + 0.18], [q + 0.07, 1.52, halfW - 0.18], M.fascia.c, M.fascia.e, Mx);
    const P = (a, b, h) => m4.xform(Mx, [a, h, b]);
    g.quad(P(L / 2, -halfW + 0.2, 0.5), P(-L / 2, -halfW + 0.2, 0.5), P(-L / 2, 0, 1.5), P(L / 2, 0, 1.5), M.glass.c, M.glass.e);
    g.quad(P(-L / 2, halfW - 0.2, 0.5), P(L / 2, halfW - 0.2, 0.5), P(L / 2, 0, 1.5), P(-L / 2, 0, 1.5), M.glass.c, M.glass.e);
  }
}

// ------------------------------------------------------------------------------------------------ parts by style
// facade layers per style (y above ground); h = roof (parapet base) height [inf, photos]
function louvreLayers(y0, y1) {   // stacked horizontal louvre bands (T1 landside, photos 01 / 03): 0.95 m blade, 0.35 m gap
  const L = []; for (let y = y0; y < y1 - 0.2; y += 1.3) { L.push([y, Math.min(y1, y + 0.35), M.louvreGap]); L.push([Math.min(y1, y + 0.35), Math.min(y1, y + 1.3), M.louvre]); }
  return L;
}
export function layersFor(style, h) {
  switch (style) {
    case 't2_pier': return [[0, 4.5, M.service], [4.5, h - 1.6, M.glass], [h - 1.6, h, M.fascia]];
    case 't2_concourse': return [[0, 4.5, M.service], [4.5, h - 2.0, M.glass], [h - 2.0, h, M.fascia]];
    case 't2_hall': return [[0, 0.6, M.fasciaDark], [0.6, h - 2.2, M.glass], [h - 2.2, h, M.fascia]];
    case 't1_concourse': return [[0, 4.2, M.recess], [4.2, 5.2, M.white], [5.2, 7.6, M.glass], [7.6, h, M.white]];
    case 't1_concourse_rear': return [[0, 9.0, M.white], [9.0, 11.6, M.glass], [11.6, h, M.white]];
    case 't1_core': return [[0, 1.0, M.white], [1.0, h - 1.2, M.officeLight], [h - 1.2, h, M.white]];
    case 't1_louvre': return [[0, 7.0, M.glass], [7.0, 8.2, M.fasciaDark], ...louvreLayers(8.2, h - 5.0), [h - 5.0, h - 0.9, M.glass], [h - 0.9, h, M.white]];
    case 't1_hall': {   // airside (west-facing) walls: fritted glass from the concourse roof up (photo 02); others: louvres
      const land = layersFor('t1_louvre', h), air = [[0, 13.0, M.white], [13.0, h - 1.2, M.frit], [h - 1.2, h, M.white]];
      return (nx) => nx < -0.6 ? air : land;
    }
    case 't1_annex': return [[0, 3.8, M.recess], [3.8, 4.6, M.white], [4.6, h - 1.0, M.whiteWin], [h - 1.0, h, M.white]];
    case 'glass_pavilion': return [[0, 0.5, M.fasciaDark], [0.5, h - 1.2, M.glass], [h - 1.2, h, M.white]];
    case 'office': case 'hotel': return [[0, 4.0, M.glass], [4.0, h - 1.0, M.officeLight], [h - 1.0, h, M.panelLight]];
    case 'parking': return [[0, h - 0.8, M.parking], [h - 0.8, h, M.panelLight]];
    case 'station': return [[0, h - 1.6, M.station], [h - 1.6, h, M.fascia]];
    default: return [[0, 1.2, M.cladDark], [1.2, h, M.clad]];   // other airport buildings: light metal-clad service blocks [inf]
  }
}
const ROOF = { generic: 'roofLight', t1_annex: 'roofLight', t2_pier: 'roofMetal', t2_concourse: 'roofMetal', t2_hall: 'roofMetal', t1_concourse: 'roofLight', t1_concourse_rear: 'roofLight', t1_core: 'roofLight',
  t1_louvre: 'roofMetal', t1_hall: 'roofMetal', glass_pavilion: 'roofLight', office: 'roofDark', hotel: 'roofDark', parking: 'parkingRoof', station: 'roofMetal' };

/** one part of data/sha_buildings3d.js parts[] (terminal volumes, hub, other airport buildings) */
export function buildPart(g, p) {
  const h = +p.h; seed = 11 + Math.floor(hash01(p.id) * 1e4);
  if (p.style === 'canopy') return buildCanopy(g, p);
  if (p.roof_form && p.roof_form.kind === 'arch') return buildArchPart(g, p);
  wallPolys(g, p.polys, layersFor(p.style, h));
  const roof = M[ROOF[p.style] || 'roofDark'];
  if (p.roof_polys) {   // roof slab with an overhang beyond the walls (T2 hall, T1 halls, station) [inf]
    slab(g, p.roof_polys, h, h + 1.3, roof, M.fascia, M.ceiling);
  } else {
    capPolys(g, p.polys, h, roof, true);
    parapet(g, p.polys, h, p.style === 'parking' ? 1.1 : 0.6, p.style === 'parking' ? M.panelLight : (/^t1/.test(p.style) ? M.white : M.fascia));
  }
  const top = h + (p.roof_polys ? 1.3 : 0);
  if (/^t2_pier|t2_concourse/.test(p.style)) { skylights(g, p, top); rooftop(g, p, top, 1600); }
  else if (/t2_hall|t1_hall|t1_louvre|station/.test(p.style)) rooftop(g, p, top, 1100, 8);
  else if (/t1_core|office|hotel|glass_pavilion|generic/.test(p.style) && p.area > 1500) rooftop(g, p, top, 1400);
}
// ---- arch roof (fix round 1, review L2: the T1 central hall's raised roof volume, photo 02) ----------------------------
// data roof_form {kind 'arch', rise, exp, dir}: the crest stays at h + 1.3 (the B3 height + the slab, as the flat roof
// before), the walls stop at the eaves he = h - rise; above them a 1.3 m roof slab follows y(s) = rise (1 - |s|^exp), s
// = -1..1 along dir across the roof outline (with its overhang). The faces under the slab ("gables") continue the wall
// below: fritted glass on the airside (west) face, white elsewhere; the slab edge is white, its top grey metal [inf].
function clipHalf(ring, f, keepGE) {   // Sutherland-Hodgman: keep f(p) >= 0 (keepGE) or <= 0
  const out = []; const s = keepGE ? 1 : -1;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i], b = ring[(i + 1) % ring.length]; const fa = s * f(a), fb = s * f(b);
    if (fa >= 0) out.push(a);
    if ((fa >= 0) !== (fb >= 0)) { const t = fa / (fa - fb); out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); }
  }
  return out;
}
function sideWall(g, a, b, ya0, yb0, ya1, yb1, mt, outN) {   // one wall quad a-b with sloped bottom / top, facing outN
  const A0 = [a[0], ya0, a[1]], B0 = [b[0], yb0, b[1]], B1 = [b[0], yb1, b[1]], A1 = [a[0], ya1, a[1]];
  const n = v3.cross(v3.sub(B0, A0), v3.sub(A1, A0));
  if (n[0] * outN[0] + n[2] * outN[1] >= 0) g.quad(A0, B0, B1, A1, mt.c, mt.e); else g.quad(B0, A0, A1, B1, mt.c, mt.e);
}
function buildArchPart(g, p) {
  const rf = p.roof_form; const h = +p.h, rise = +rf.rise || 7, ex = +rf.exp || 2, T = 1.3; const he = h - rise;
  const d = rf.dir || [0, 1]; const tOf = (q) => q[0] * d[0] + q[1] * d[1];
  const roofP = p.roof_polys || p.polys; const outer = roofP[0][0];
  let t0 = Infinity, t1 = -Infinity; for (const q of outer) { const t = tOf(q); t0 = Math.min(t0, t); t1 = Math.max(t1, t); }
  const tc = (t0 + t1) / 2, hw = (t1 - t0) / 2;
  const yA = (t) => rise * (1 - Math.pow(Math.min(1, Math.abs((t - tc) / hw)), ex));
  const dyA = (t) => { const s = (t - tc) / hw; return -rise * ex * Math.pow(Math.min(1, Math.abs(s)), ex - 1) * Math.sign(s) / hw; };
  const NS = 32; const cuts = []; for (let k = 0; k <= NS; k++) cuts.push(t0 + (t1 - t0) * k / NS);
  // split an edge at the strip cuts (so a curved top is piecewise linear between cut lines)
  const split = (a, b) => { const ta = tOf(a), tb = tOf(b); const pts = [a]; const ks = cuts.filter(c => (c - ta) * (c - tb) < 0).sort((x, y) => (x - ta) / (tb - ta) - (y - ta) / (tb - ta));
    for (const c of ks) { const f = (c - ta) / (tb - ta); pts.push([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]); } pts.push(b); return pts; };
  // walls to the eaves: the airside (west) face fritted glass from 13 m up to the eaves (it continues in the gable)
  const land = layersFor('t1_louvre', he), air = [[0, 13.0, M.white], [13.0, he, M.frit]];
  wallPolys(g, p.polys, (nx) => nx < -0.6 ? air : land);
  // gables under the arch slab, along the wall outline
  for (const pl of p.polys) pl.forEach((r, ri) => {
    const pos = ringArea(r) > 0; const outward = ri === 0;
    for (let i = 0; i < r.length; i++) {
      const a = r[i], b = r[(i + 1) % r.length]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); if (L < 0.05) continue;
      let n = [(b[1] - a[1]) / L, -(b[0] - a[0]) / L]; if (pos !== outward) n = [-n[0], -n[1]];
      const mt = n[0] < -0.6 ? M.frit : M.white; const pts = split(a, b);
      for (let k = 0; k + 1 < pts.length; k++) { const u = pts[k], w = pts[k + 1]; sideWall(g, u, w, he, he, he + yA(tOf(u)), he + yA(tOf(w)), mt, n); }
    }
  });
  // the arch slab: strips across dir, each clipped from the roof outline, earcut, vertices lifted to the arch
  const roofMt = M.roofMetal;
  for (let k = 0; k < NS; k++) {
    let ring = clipHalf(outer, (q) => tOf(q) - cuts[k], true); if (ring.length >= 3) ring = clipHalf(ring, (q) => tOf(q) - cuts[k + 1], false);
    if (ring.length < 3) continue;
    const flat = []; for (const q of ring) flat.push(q[0], q[1]); const tri = earcut(flat, []);
    for (const up of [true, false]) {
      const base = g.nv; const mt = up ? roofMt : M.ceiling;
      for (const q of ring) { const t = tOf(q), s = dyA(t); const nn = up ? v3.norm([-s * d[0], 1, -s * d[1]]) : [0, -1, 0]; g.vert([q[0], he + yA(t) + (up ? T : 0), q[1]], nn, mt.c, mt.e, q); }
      for (let i = 0; i < tri.length; i += 3) {
        const a = tri[i], b = tri[i + 1], c = tri[i + 2];
        const cr = (flat[b * 2] - flat[a * 2]) * (flat[c * 2 + 1] - flat[a * 2 + 1]) - (flat[b * 2 + 1] - flat[a * 2 + 1]) * (flat[c * 2] - flat[a * 2]);
        if ((cr > 0) === up) g.idx.push(base + a, base + c, base + b); else g.idx.push(base + a, base + b, base + c);
      }
    }
  }
  // slab edge (white fascia) along the roof outline
  const rpos = ringArea(outer) > 0;
  for (let i = 0; i < outer.length; i++) {
    const a = outer[i], b = outer[(i + 1) % outer.length]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); if (L < 0.05) continue;
    let n = [(b[1] - a[1]) / L, -(b[0] - a[0]) / L]; if (!rpos) n = [-n[0], -n[1]];
    const pts = split(a, b);
    for (let k = 0; k + 1 < pts.length; k++) { const u = pts[k], w = pts[k + 1], yu = he + yA(tOf(u)), yw = he + yA(tOf(w)); sideWall(g, u, w, yu, yw, yu + T, yw + T, M.white, n); }
  }
}
// platform canopies (Hongqiao station): a roof slab on a 24 m column grid [inf]
function buildCanopy(g, p) {
  const h = +p.h; slab(g, p.polys, h - 0.9, h, M.roofMetal, M.fascia, M.ceiling);
  const ax = p.axis, ay = [-ax[1], ax[0]]; const [cx, cz] = p.center;
  for (let s = -p.len / 2; s <= p.len / 2; s += 24) for (let t = -p.wid / 2; t <= p.wid / 2; t += 18) {
    const x = cx + ax[0] * s + ay[0] * t, z = cz + ax[1] * s + ay[1] * t;
    if (!insidePolys(p.polys, x, z) || edgeDist(p.polys, x, z) < 3) continue;
    g.box([-0.4, 0, -0.4], [0.4, h - 0.9, 0.4], M.column.c, M.column.e, m4.basis([ax[0], 0, ax[1]], [0, 1, 0], [x, 0, z]));
  }
}

// ------------------------------------------------------------------------------------------------ hangars
// walls: corrugated cladding to the eaves; the door wall (the OSM edges along the door side found by the data tool) gets
// door leaves up to doorH and a darker header; roof: flat (+ parapet), 'barrel' (one vault, ridge parallel to the door)
// or 'multi' (n vaults front-to-back, one per bay); vault rise and door height are [inf].
export function buildHangar(g, hg) {
  const h = +hg.h; const doorH = Math.max(8, Math.min(26, h * 0.72)); const D = hg.door || null;
  const [ea, eb] = D ? D.edge : [[0, 0], [0, 0]]; const dn = D ? D.normal : [0, 0];
  const dt = [eb[0] - ea[0], eb[1] - ea[1]]; const dl = Math.hypot(dt[0], dt[1]) || 1; dt[0] /= dl; dt[1] /= dl;
  const onDoor = (a, b) => {
    if (!D) return false; const ex = b[0] - a[0], ez = b[1] - a[1]; const L = Math.hypot(ex, ez); if (L < 8) return false;
    const par = Math.abs((ex * dt[0] + ez * dt[1]) / L); const mx = (a[0] + b[0]) / 2 - ea[0], mz = (a[1] + b[1]) / 2 - ea[1];
    return par > 0.97 && Math.abs(mx * dn[0] + mz * dn[1]) < 5;
  };
  for (const pl of hg.polys) pl.forEach((r, ri) => {
    for (let i = 0; i < r.length; i++) {
      const a = r[i], b = r[(i + 1) % r.length];
      if (ri === 0 && onDoor(a, b)) {
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]); const u = [(b[0] - a[0]) / L, (b[1] - a[1]) / L]; const jamb = Math.min(5, L * 0.06);
        const A2 = [a[0] + u[0] * jamb, a[1] + u[1] * jamb], B2 = [b[0] - u[0] * jamb, b[1] - u[1] * jamb];
        wallRing(g, [a, A2], [[0, h, M.clad]], true); wallRing(g, [B2, b], [[0, h, M.clad]], true);
        segWall(g, a, A2, 0, h, M.clad, r); segWall(g, B2, b, 0, h, M.clad, r);
        segWall(g, A2, B2, 0, doorH, M.door, r); segWall(g, A2, B2, doorH, h, M.cladDark, r);
      } else segWall(g, a, b, 0, h, M.clad, r, ri !== 0);
    }
  });
  // roof over the minimum rectangle (centre / axis / len / wid from the data tool)
  const ax = hg.axis, ay = [-ax[1], ax[0]]; const [cx, cz] = hg.center; const L = hg.len, W = hg.wid;
  const P = (s, t, y) => [cx + ax[0] * s + ay[0] * t, y, cz + ax[1] * s + ay[1] * t];
  if (hg.roof === 'flat' || !D) { capPolys(g, hg.polys, h, M.roofLight, true); parapet(g, hg.polys, h, 0.8, M.cladDark); return; }
  // door normal in (s, t): which rectangle axis runs front-to-back
  const nS = Math.abs(dn[0] * ax[0] + dn[1] * ax[1]) > 0.7;          // door normal along the long axis?
  const depth = nS ? L : W, width = nS ? W : L;
  const F = (u, v, y) => nS ? P(v, u, y) : P(u, v, y);              // u along the door, v front-to-back
  const vaults = hg.roof === 'multi' ? Math.max(2, hg.bays || 2) : 1;
  const NS = 12;
  if (vaults === 1) {   // one vault, ridge parallel to the door: y(v) over the depth
    const rise = Math.min(0.06 * depth, 4.5); const yv = (v) => h + rise * (1 - Math.pow(2 * v / depth, 2));
    for (let k = 0; k < NS; k++) {
      const v0 = -depth / 2 + depth * k / NS, v1 = v0 + depth / NS;
      quadUp(g, F(-width / 2, v0, yv(v0)), F(width / 2, v0, yv(v0)), F(width / 2, v1, yv(v1)), F(-width / 2, v1, yv(v1)), M.roofLight);
      for (const su of [-1, 1]) tri(g, F(su * width / 2, v0, h), F(su * width / 2, v0, yv(v0)), F(su * width / 2, v1, yv(v1)), M.clad, [su * (nS ? ay[0] : ax[0]), 0, su * (nS ? ay[1] : ax[1])], F(su * width / 2, v1, h));
    }
  } else {              // n vaults front-to-back, side by side along the door
    const bw = width / vaults; const rise = Math.min(0.1 * bw, 5); const yu = (u) => { const f = ((u + width / 2) / bw) % 1; return h + rise * (1 - Math.pow(2 * f - 1, 2)); };
    for (let b = 0; b < vaults; b++) for (let k = 0; k < NS; k++) {
      const u0 = -width / 2 + b * bw + bw * k / NS, u1 = u0 + bw / NS; const y0 = yu(u0 + 1e-6), y1 = k === NS - 1 ? h : yu(u1);
      quadUp(g, F(u0, -depth / 2, y0), F(u1, -depth / 2, y1), F(u1, depth / 2, y1), F(u0, depth / 2, y0), M.roofLight);
      for (const sv of [-1, 1]) tri(g, F(u0, sv * depth / 2, h), F(u0, sv * depth / 2, y0), F(u1, sv * depth / 2, y1), M.clad, [sv * (nS ? ax[0] : ay[0]), 0, sv * (nS ? ax[1] : ay[1])], F(u1, sv * depth / 2, h));
    }
  }
}
// a single wall segment a-b facing away from the ring's interior (outer) or into the hole
function segWall(g, a, b, y0, y1, mt, ring, hole = false) {
  const pos = ringArea(ring) > 0; const leftOut = (pos === hole);
  const A0 = [a[0], y0, a[1]], B0 = [b[0], y0, b[1]], B1 = [b[0], y1, b[1]], A1 = [a[0], y1, a[1]];
  if (leftOut) g.quad(A0, B0, B1, A1, mt.c, mt.e); else g.quad(B0, A0, A1, B1, mt.c, mt.e);
}
// quad whose normal is forced upward-facing; tri() = gable infill (a quad with an outward normal n)
function quadUp(g, p0, p1, p2, p3, mt) { const n = v3.cross(v3.sub(p1, p0), v3.sub(p3, p0)); if (n[1] >= 0) g.quad(p0, p1, p2, p3, mt.c, mt.e); else g.quad(p1, p0, p3, p2, mt.c, mt.e); }
function tri(g, a, b, c, mt, n, d) { const q = v3.cross(v3.sub(c, a), v3.sub(b, a)); if (v3.dot(q, n) >= 0) g.quad(a, d, c, b, mt.c, mt.e); else g.quad(a, b, c, d, mt.c, mt.e); }

// ------------------------------------------------------------------------------------------------ towers
// East control tower (data dims from photo 02, see tools/buildings/build_buildings3d.py), built in local coordinates
// around the tower axis: square shaft with a dark slot on the face towards the runways (west), inverted frustum head with
// two rows of small windows, octagonal (chamfered-square) cab leaning outward, roof slab and roof block, all at or below
// the AIP obstacle top [form inf].
export function buildControlTower(t) {
  const g = new Geo(); const D = t.dims; const H = +t.h;
  const yaw = (t.yaw_deg || 0) * Math.PI / 180; const f = [Math.sin(yaw), 0, -Math.cos(yaw)]; const r = [-f[2], 0, f[0]];
  // local frame: X = r (across the runway grid), Z = f (along it); the slot goes on the side facing west (-x world)
  const B = m4.basis(r, [0, 1, 0], [0, 0, 0]);
  const P = (x, y, z) => m4.xform(B, [x, y, z]);
  const hw = D.shaft_w / 2;
  g.box([-hw, 0, -hw], [hw, D.flare_y0, hw], M.concrete.c, M.concrete.e, B);
  g.box([-hw - 2.5, 0, -hw - 2.5], [hw + 2.5, 4.0, hw + 2.5], M.concrete.c, M.concrete.e, B);   // entrance plinth [inf]
  // dark vertical slot on the face whose outward normal points most to the west (-x world)
  const faces = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const westFace = faces.reduce((best, fc) => { const w = m4.xform(B, [fc[0], 0, fc[1]]); return (w[0] < best.w) ? { fc, w: w[0] } : best; }, { fc: null, w: 1e9 }).fc;
  const sw = D.slot_w / 2, so = hw + 0.04;
  const panel = (fc, s0, s1, y0, y1, off, mt) => {
    const n = [fc[0], 0, fc[1]], tng = [fc[1], 0, -fc[0]];   // tng x up = n (right-handed: right of the viewer facing the face)
    const p = (s, y) => P(n[0] * off + tng[0] * s, y, n[2] * off + tng[2] * s);
    g.quad(p(s0, y0), p(s1, y0), p(s1, y1), p(s0, y1), mt.c, mt.e);
  };
  panel(westFace, -sw, sw, 4.0, D.flare_y0 + 1.0, so, M.slot);
  // head: inverted frustum from flare_y0 (shaft width) to head_y1 (head_w), 4 slanted faces + windows
  const y0 = D.flare_y0, y1 = D.head_y1, w0 = hw, w1 = D.head_w / 2;
  for (const fc of faces) {
    const n = [fc[0], 0, fc[1]], tng = [fc[1], 0, -fc[0]];
    const p = (s, y, w) => P(n[0] * w + tng[0] * s, y, n[2] * w + tng[2] * s);
    g.quad(p(-w0, y0, w0), p(w0, y0, w0), p(w1, y1, w1), p(-w1, y1, w1), M.concrete.c, M.concrete.e);
    // windows: lower row 1 per face, upper row 3 per face (photo 02), 1.0 x 1.1 m, just proud of the slanted face
    for (const [yr, nwin] of [[D.window_rows[0], 1], [D.window_rows[1], 3]]) {
      const k = (yr - y0) / (y1 - y0); const wk = w0 + (w1 - w0) * k + 0.06; const sp = wk * 0.42;
      for (let i = 0; i < nwin; i++) { const s = nwin === 1 ? (fc === westFace ? -sp : 0) : (i - 1) * sp; const kk = (yr + 0.55 - y0) / (y1 - y0), wk2 = w0 + (w1 - w0) * kk + 0.06; const kk0 = (yr - 0.55 - y0) / (y1 - y0), wk0 = w0 + (w1 - w0) * kk0 + 0.06;
        g.quad(p(s - 0.5, yr - 0.55, wk0), p(s + 0.5, yr - 0.55, wk0), p(s + 0.5, yr + 0.55, wk2), p(s - 0.5, yr + 0.55, wk2), M.window.c, M.window.e); }
    }
  }
  // terrace floor at head_y1 (closes the frustum top): grey roof membrane on top (fix round 1: the pale concrete top glared
  // white across the lower part of the in-app Tower view) [inf]
  g.box([-w1, y1 - 0.4, -w1], [w1, y1, w1], M.concrete.c, M.concrete.e, B, ['px', 'nx', 'pz', 'nz', 'ny']);
  g.box([-w1, y1 - 0.4, -w1], [w1, y1, w1], M.terrace.c, M.terrace.e, B, ['py']);
  // cab: chamfered square (octagon with long / short sides), glazing from head_y1 to cab_y1, leaning outward
  const oct = (w, ch) => [[w, -w + ch], [w, w - ch], [w - ch, w], [-w + ch, w], [-w, w - ch], [-w, -w + ch], [-w + ch, -w], [w - ch, -w]];
  const cb = oct(D.cab_w0 / 2, D.cab_w0 * 0.17), ct = oct(D.cab_w1 / 2, D.cab_w1 * 0.17);
  const cy0 = y1, cy1 = D.cab_y1;
  for (let i = 0; i < 8; i++) {
    const j = (i + 1) % 8; const a0 = P(cb[i][0], cy0, cb[i][1]), b0 = P(cb[j][0], cy0, cb[j][1]), b1 = P(ct[j][0], cy1, ct[j][1]), a1 = P(ct[i][0], cy1, ct[i][1]);
    // octagon is listed counter-clockwise in (X, Z) local = clockwise seen from above; order for outward faces
    g.quad(b0, a0, a1, b1, M.cab.c, M.cab.e);
  }
  // cab floor / console band (matte: it fills the lower part of the in-app Tower view) and roof slab (cab_y1 .. H)
  g.box([-D.cab_w0 / 2, cy0, -D.cab_w0 / 2], [D.cab_w0 / 2, cy0 + 0.6, D.cab_w0 / 2], M.console.c, M.console.e, B);
  // the AIP obstacle elevation is the highest point, so everything stays at or below H: roof slab to H - 0.6, then a
  // set-back roof block (plant / railing) to H; no mast above it [inf]
  const rw = D.roof_w / 2;
  g.box([-rw, cy1, -rw], [rw, H - 0.6, rw], M.white.c, M.white.e, B);
  g.box([-rw + 1.2, H - 0.6, -rw + 1.2], [rw - 1.2, H, rw - 1.2], M.fascia.c, M.fascia.e, B);
  return { geo: g.data(), eye: (cy0 + 1.6), top: H };
}
// untyped SW towers: the OSM footprint extruded to the rule height, a dark band near the top, a rooftop mast [inf]
export function buildBlockTower(g, t) {
  const h = +t.h;
  wallPolys(g, t.polys, [[0, h - 5.5, M.concrete], [h - 5.5, h - 1.5, M.glass], [h - 1.5, h, M.concrete]]);
  capPolys(g, t.polys, h, M.roofDark, true); parapet(g, t.polys, h, 0.8, M.concrete);
  g.cylinder(0.25, 8, 8, M.vent.c, M.vent.e, m4.translate(t.center[0], h, t.center[1]), true);
}

// ------------------------------------------------------------------------------------------------ context LOD blocks
// context buildings of the detailed extent (data/sha_airport.js context.buildings, minus the hub parts drawn above):
// one low-detail block each - walls to the data height (rule heights, inf), a parapet, a flat roof; facade by kind
// (punched windows for housing / offices, concrete panels otherwise, glass for tall offices); wall tint per building from
// a palette by id hash, roofs darker than walls [all inf].
// Fix round 1 (review L5, "snow city"): the old tints (linear 0.50-0.66) and the uniform 0.30-0.38 roofs read as white
// blocks from above. Walls now come from a Shanghai-like palette (linear luminance ~0.25-0.52: grey concrete, beige / buff
// tile, brick, warm white tile, blue-grey) with a +-8 % per-building variation from a second hash; roofs are 0.16-0.30
// grey (asphalt / concrete / gravel) and a share of industrial / commercial roofs are blue or grey steel (aerials 21 / 24:
// blue steel roofs on factory sheds) [inf: palette and shares read from the open aerials, not measured].
const WALLS = [
  [0.40, 0.40, 0.39], [0.46, 0.45, 0.43], [0.34, 0.34, 0.34],   // grey concrete
  [0.50, 0.44, 0.35], [0.44, 0.39, 0.31],                       // beige / buff tile
  [0.36, 0.21, 0.15], [0.30, 0.19, 0.14],                       // brick
  [0.55, 0.53, 0.49],                                           // warm white tile
  [0.33, 0.36, 0.40],                                           // blue-grey
];
const W_SHARE = [0.13, 0.13, 0.10, 0.13, 0.10, 0.08, 0.05, 0.18, 0.10];   // cumulative pick by hash
function pickWall(k) { let a = 0; for (let i = 0; i < WALLS.length; i++) { a += W_SHARE[i]; if (k < a) return WALLS[i]; } return WALLS[WALLS.length - 1]; }
export const CONTEXT_PALETTE = { walls: WALLS, shares: W_SHARE, roofGrey: [0.16, 0.30], steelBlue: [0.10, 0.17, 0.27], steelGrey: [0.30, 0.31, 0.33], src: 'inf (aerials 21 / 24, photos 02 / 22)' };
export function contextColours(id, kind) {
  const k = hash01(id), k2 = hash01(id + '#v'), k3 = hash01(id + '#r');
  const v = 0.92 + 0.16 * k2; const w = pickWall(k).map(c => c * v);
  let roof; const g = 0.16 + 0.14 * k3;
  if (/industrial|commercial/.test(kind) && k3 > 0.6) roof = k3 > 0.8 ? CONTEXT_PALETTE.steelBlue : CONTEXT_PALETTE.steelGrey;
  else roof = [g, g * 0.99, g * 0.96];
  // roofs stay darker than their walls (<= 0.8 x the wall luminance; brick walls are dark)
  const lum = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; const kr = Math.min(1, 0.8 * lum(w) / lum(roof));
  return { wall: w, roof: roof.map(c => c * kr) };
}
export function buildContextBlocks(g, buildings, skip) {
  let n = 0;
  for (const b of buildings) {
    if (skip.has(b.id)) continue;
    const h = Math.max(3, +b.height_m || 10);
    const kind = b.kind || 'building'; const C = contextColours(b.id, kind); const tint = C.wall;
    let wall;
    if (/apartments|residential|house|hotel/.test(kind)) wall = { c: [...tint, 1], e: [0.9, 0, 6, 0] };
    else if (/office|commercial/.test(kind)) wall = h >= 28 ? { c: [0.1, 0.1, 0.1, 1], e: [0.1, 0, 1, 0] } : { c: [...tint, 1], e: [0.85, 0, 6, 0] };
    else if (/industrial/.test(kind)) wall = { c: [0.50, 0.51, 0.53, 1], e: [0.6, 0.3, 4, 0] };
    else wall = { c: [...tint, 1], e: [0.9, 0, 2, 0] };
    const rings = [b.ring, ...((b.more_rings || []).map(r => Array.isArray(r[0][0]) ? r[0] : r))].filter(r => r && r.length >= 3);
    const polys = rings.map(r => [ringArea(r) > 0 ? r : r.slice().reverse()]);
    wallPolys(g, polys, [[-0.5, h, wall]]);
    const roof = { c: [...C.roof, 1], e: [0.9, 0, 5, 0] };
    capPolys(g, polys, h, roof, true);
    if (h > 6) parapet(g, polys, h, 0.7, { c: [tint[0] * 0.85, tint[1] * 0.85, tint[2] * 0.85, 1], e: [0.9, 0, 0, 0] });
    n++;
  }
  return n;
}

// ------------------------------------------------------------------------------------------------ canal and river banks
// low embankment kerbs (0.5 m high, 0.35 m wide) along the OSM water areas and along canal / river / stream lines that do
// not run inside a water area, offset by the core's drawn half-width (js/world/ground.js WATER_W) [inf: form, height,
// widths]; the water itself stays the ground shader's (core). Ditches and drains get none.
const BANK_W = { river: 16, canal: 10, stream: 5 };
const BANK = { c: [0.46, 0.45, 0.42, 1], e: [0.85, 0, 17, 0] };   // mat 17: kerb, fades out beyond ~650-850 m (fix 1, review M6) [inf]
function kerb(g, a, b, h = 0.5, w = 0.35) {
  const dx = b[0] - a[0], dz = b[1] - a[1]; const L = Math.hypot(dx, dz); if (L < 0.5) return 0;
  g.box([-L / 2, -0.4, -w / 2], [L / 2, h, w / 2], BANK.c, BANK.e, m4.basis([dx / L, 0, dz / L], [0, 1, 0], [(a[0] + b[0]) / 2, 0, (a[1] + b[1]) / 2]), ['px', 'nx', 'py', 'pz', 'nz']);
  return L;
}
function offsetLine(pts, d) {   // polyline offset by d (left positive), mitred, mitre clamped
  const out = [];
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
    const n0 = i > 0 ? nrm(a, p) : nrm(p, b), n1 = i < pts.length - 1 ? nrm(p, b) : nrm(a, p);
    let nx = n0[0] + n1[0], nz = n0[1] + n1[1]; const l = Math.hypot(nx, nz) || 1; nx /= l; nz /= l;
    const k = Math.min(2.5, 1 / Math.max(0.3, nx * n0[0] + nz * n0[1]));
    out.push([p[0] + nx * d * k, p[1] + nz * d * k]);
  }
  return out;
}
function nrm(a, b) { const dx = b[0] - a[0], dz = b[1] - a[1]; const l = Math.hypot(dx, dz) || 1; return [-dz / l, dx / l]; }
export function buildWaterEdges(g, context) {
  const areas = (context.water_areas || []).map(w => [w.ring, ...(w.holes || [])]);
  const inArea = (x, z) => areas.some(pl => inRing(pl[0], x, z) && !pl.slice(1).some(h => inRing(h, x, z)));
  let len = 0;
  for (const pl of areas) for (const r of pl) for (let i = 0; i < r.length; i++) len += kerb(g, r[i], r[(i + 1) % r.length]);
  for (const w of context.water_lines || []) {
    const hw = BANK_W[w.waterway]; if (!hw || (w.tunnel && w.tunnel !== 'no')) continue;
    for (const ln of w.lines || []) {
      // split the line into runs outside the water areas
      let run = [];
      const flush = () => { if (run.length >= 2) for (const s of [hw / 2, -hw / 2]) { const o = offsetLine(run, s); for (let i = 0; i + 1 < o.length; i++) len += kerb(g, o[i], o[i + 1]); } run = []; };
      for (let i = 0; i < ln.length; i++) { if (inArea(ln[i][0], ln[i][1])) flush(); else run.push(ln[i]); }
      flush();
    }
  }
  return Math.round(len);
}
