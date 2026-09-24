// SFO terminal complex, part by part (footprints: SFO Museum; parts & exposed-wall analysis: tools/build_terminal_parts.py)
//  - apron (ramp) level 0-5 m: service facade with roll-up doors
//  - boarding areas (piers): glass curtain walls to 13.4 m, white fascia, light roof with skylight spine & rooftop plant
//  - terminal halls: taller glazed halls; International Terminal great hall (705 x 210 ft, up to 83 ft) under a
//    wing-shaped roof of balanced double-cantilever trusses (380 ft centre span, 160 ft cantilevers)
//  - elevated walkways (sky bridges) as glazed tubes on the upper level
//  - airport traffic control tower: 221 ft, curved tapering shaft, glass ribbon/LED "waterfall" on the west face,
//    offset cab with 24 slanted frameless panes over 270 degrees, cantilevered roof; 3-storey base building
import { Geo } from '../geom.js';
import { m4, v3 } from '../math.js';
import { GROUND_Y } from '../geo.js';
import { earcut } from './earcut.js';

const G = GROUND_Y, FT = 0.3048;
const M = {
  apron: { c: [0.66, 0.67, 0.68, 1], e: [0.75, 0.1, 15, 0] },
  glass: { c: [0.1, 0.1, 0.1, 1], e: [0.1, 0, 1, 0] },
  fascia: { c: [0.88, 0.89, 0.9, 1], e: [0.35, 0.35, 0, 0] },
  roof: { c: [0.56, 0.57, 0.56, 1], e: [0.9, 0, 5, 0] },
  roofMetal: { c: [0.8, 0.82, 0.84, 1], e: [0.3, 0.8, 4, 0] },
  ceiling: { c: [0.9, 0.9, 0.88, 1], e: [0.6, 0, 0, 0] },
  plant: { c: [0.72, 0.73, 0.74, 1], e: [0.5, 0.4, 0, 0] },
  vent: { c: [0.25, 0.26, 0.27, 1], e: [0.6, 0.3, 0, 0] },
  concrete: { c: [0.8, 0.79, 0.76, 1], e: [0.85, 0, 2, 0] },
  towerGlass: { c: [0.05, 0.06, 0.07, 1], e: [0.05, 0, 12, 0] },
  led: { c: [0.08, 0.1, 0.14, 1], e: [0.08, 0, 16, 0] },
  dark: { c: [0.18, 0.19, 0.2, 1], e: [0.5, 0.6, 0, 0] },
  white: { c: [0.9, 0.9, 0.89, 1], e: [0.45, 0.2, 0, 0] },
};
const ringArea = (r) => { let a = 0; for (let i = 0; i < r.length; i++) { const p = r[i], q = r[(i + 1) % r.length]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; };

// walls of one ring between yb (per-edge, from the exposed-wall analysis) and y1; hole rings face into the hole
function walls(g, ring, bases, isHole, y0, y1, mat, splits = null) {
  const n = ring.length; const pos = ringArea(ring) > 0;
  for (let i = 0; i < n; i++) {
    const a = ring[i], b = ring[(i + 1) % n];
    const dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz); if (L < 0.05) continue;
    let nx = -dz / L, nz = dx / L; // left normal: inward for positive-area rings
    if (pos !== isHole) { nx = -nx; nz = -nz; }
    const yb = Math.max(y0, G + (bases ? bases[i] : 0));
    const layers = splits || [[y0, y1, mat]];
    for (const [ya, yc, mt] of layers) {
      const lo = Math.max(ya, yb), hi = yc; if (hi - lo < 0.05) continue;
      const base = g.nv;
      g.vert([a[0], lo, a[1]], [nx, 0, nz], mt.c, mt.e, [0, lo]); g.vert([b[0], lo, b[1]], [nx, 0, nz], mt.c, mt.e, [L, lo]);
      g.vert([b[0], hi, b[1]], [nx, 0, nz], mt.c, mt.e, [L, hi]); g.vert([a[0], hi, a[1]], [nx, 0, nz], mt.c, mt.e, [0, hi]);
      // winding: outward-facing (renderer culls back faces for 'obj')
      if ((nx * (-dz) + nz * dx) > 0) g.idx.push(base, base + 1, base + 2, base, base + 2, base + 3); else g.idx.push(base, base + 2, base + 1, base, base + 3, base + 2);
    }
  }
}
function cap(g, rings, y, mat, down = false) {
  const flat = [], holes = [];
  rings.forEach((r, i) => { if (i) holes.push(flat.length / 2); r.forEach(p => flat.push(p[0], p[1])); });
  const tri = earcut(flat, holes); const base = g.nv;
  for (let i = 0; i < flat.length; i += 2) g.vert([flat[i], y, flat[i + 1]], [0, down ? -1 : 1, 0], mat.c, mat.e, [flat[i], flat[i + 1]]);
  for (let i = 0; i < tri.length; i += 3) {
    const a = tri[i], b = tri[i + 1], c = tri[i + 2];
    const cr = (flat[b * 2] - flat[a * 2]) * (flat[c * 2 + 1] - flat[a * 2 + 1]) - (flat[b * 2 + 1] - flat[a * 2 + 1]) * (flat[c * 2] - flat[a * 2]);
    const up = cr < 0; if (up !== down) g.idx.push(base + a, base + b, base + c); else g.idx.push(base + a, base + c, base + b);
  }
}
function inRing(r, x, z) { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[i], b = r[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
function inside(rings, x, z) { return inRing(rings[0], x, z) && !rings.slice(1).some(h => inRing(h, x, z)); }
function edgeDist(rings, x, z) { let d = 1e9; for (const r of rings) for (let i = 0; i < r.length; i++) { const a = r[i], b = r[(i + 1) % r.length]; const dx = b[0] - a[0], dz = b[1] - a[1]; const l2 = dx * dx + dz * dz || 1; const t = Math.max(0, Math.min(1, ((x - a[0]) * dx + (z - a[1]) * dz) / l2)); d = Math.min(d, Math.hypot(x - a[0] - dx * t, z - a[1] - dz * t)); } return d; }
let seed = 7; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };

// rooftop plant: air handlers, exhaust fans and louvred enclosures scattered inside the roof, away from its edges
function rooftop(g, part, y) {
  const R = part.rings; const [cx, cz] = part.center; const ax = part.axis, ay = [-ax[1], ax[0]];
  const span = part.len / 2 + 20, wspan = part.wid / 2 + 20;
  const n = Math.round(part.area / 900);
  for (let k = 0, tries = 0; k < n && tries < n * 12; tries++) {
    const s = (rnd() * 2 - 1) * span, t = (rnd() * 2 - 1) * wspan; const x = cx + ax[0] * s + ay[0] * t, z = cz + ax[1] * s + ay[1] * t;
    if (!inside(R, x, z) || edgeDist(R, x, z) < 6) continue;
    const Mx = m4.basis([ax[0], 0, ax[1]], [0, 1, 0], [x, y, z]);
    const kind = rnd();
    if (kind < 0.45) { const l = 4 + rnd() * 5, w = 2.2 + rnd() * 1.5, h = 1.6 + rnd() * 0.8; g.box([-l / 2, 0, -w / 2], [l / 2, h, w / 2], M.plant.c, M.plant.e, Mx); for (let f = 0; f < Math.floor(l / 1.6); f++) g.cylinder(0.55, 0.25, 12, M.vent.c, M.vent.e, m4.mul(Mx, m4.translate(-l / 2 + 0.8 + f * 1.6, h, 0)), true); }
    else if (kind < 0.75) { const r = 0.5 + rnd() * 0.4; g.cylinder(r, 0.9, 12, M.plant.c, M.plant.e, Mx, true); g.cylinder(r * 1.25, 0.12, 12, M.vent.c, M.vent.e, m4.mul(Mx, m4.translate(0, 0.9, 0)), true); }
    else { const l = 6 + rnd() * 6, w = 4 + rnd() * 3; g.box([-l / 2, 0, -w / 2], [l / 2, 2.6, w / 2], M.fascia.c, M.fascia.e, Mx); }
    k++;
  }
}
// skylight spine along the principal axis (only where the axis lies well inside the roof)
function skylights(g, part, y) {
  const R = part.rings; const [cx, cz] = part.center; const ax = part.axis;
  let run = null; const out = [];
  for (let s = -part.len / 2; s <= part.len / 2; s += 3) {
    const x = cx + ax[0] * s, z = cz + ax[1] * s; const ok = inside(R, x, z) && edgeDist(R, x, z) > 7;
    if (ok) { if (!run) run = [s, s]; else run[1] = s; } else if (run) { out.push(run); run = null; }
  }
  if (run) out.push(run);
  for (const [s0, s1] of out) {
    if (s1 - s0 < 12) continue;
    const c = [cx + ax[0] * (s0 + s1) / 2, cz + ax[1] * (s0 + s1) / 2]; const Mx = m4.basis([ax[0], 0, ax[1]], [0, 1, 0], [c[0], y, c[1]]);
    const L = s1 - s0 - 4; g.box([-L / 2, 0, -1.8], [L / 2, 0.5, 1.8], M.fascia.c, M.fascia.e, Mx);
    for (let q = -L / 2; q <= L / 2 + 0.01; q += 3.0) g.box([q - 0.07, 0.5, -1.62], [q + 0.07, 1.52, 1.62], M.fascia.c, M.fascia.e, Mx); // glazing bars
    // glazed ridge
    const P = (a, b, h) => m4.xform(Mx, [a, h, b]);
    g.quad(P(L / 2, -1.6, 0.5), P(-L / 2, -1.6, 0.5), P(-L / 2, 0, 1.5), P(L / 2, 0, 1.5), M.glass.c, M.glass.e);
    g.quad(P(-L / 2, 1.6, 0.5), P(L / 2, 1.6, 0.5), P(L / 2, 0, 1.5), P(-L / 2, 0, 1.5), M.glass.c, M.glass.e);
  }
}

export function buildTerminals(B, gIn = null) {
  const g = gIn || new Geo(); seed = 11;
  // apron (ramp) level of the whole complex
  const big = B.complex.reduce((a, r) => Math.abs(ringArea(r)) > Math.abs(ringArea(a)) ? r : a, B.complex[0]); const sgn = Math.sign(ringArea(big));
  for (const r of B.complex) walls(g, r, null, Math.sign(ringArea(r)) !== sgn, G, G + 5.0, M.apron);
  const itb = B.parts.filter(p => p.kind === 'hall' && /International/.test(p.name)).sort((a, b) => b.area - a.area)[0];
  for (const p of B.parts) {
    const top = G + p.h;
    if (p.kind === 'walkway') {
      const y0 = G + (p.y0 || 6), y1 = G + p.h;
      p.rings.forEach((r, i) => walls(g, r, null, i > 0, y0, y1, M.glass, [[y0, y0 + 0.8, M.fascia], [y0 + 0.8, y1 - 0.7, M.glass], [y1 - 0.7, y1, M.fascia]]));
      cap(g, p.rings, y1, M.roofMetal); cap(g, p.rings, y0, M.fascia, true);
      continue;
    }
    const isITB = p === itb;
    const roofY = isITB ? G + 16 : top;
    const layers = [[G + 5.0, roofY - 1.2, M.glass], [roofY - 1.2, roofY, M.fascia]];
    p.rings.forEach((r, i) => walls(g, r, p.base[i], i > 0, G + 5.0, roofY, M.glass, layers));
    cap(g, p.rings, roofY, M.roof);
    // parapet
    p.rings.forEach((r, i) => walls(g, r, null, i > 0, roofY, roofY + 0.6, M.fascia));
    if (p.kind === 'pier') { skylights(g, p, roofY); rooftop(g, p, roofY); }
    else if (!isITB) rooftop(g, p, roofY);
  }
  if (itb) greatHall(g, itb);
  return gIn ? null : g.data();
}

// International Terminal great hall under its wing roof (published: 705 x 210 ft hall, up to 83 ft; trusses up to 29 ft
// deep, 380 ft centre span and 160 ft cantilevers). Placed on the terminal footprint's principal axis.
function greatHall(g, p) {
  const ax = [p.axis[0], 0, p.axis[1]]; const ay = [-p.axis[1], 0, p.axis[0]];
  const c = [p.center[0], G, p.center[1]];
  const hallL = 705 * FT, hallW = 210 * FT, span = 380 * FT, cant = 160 * FT, roofL = span + 2 * cant + 2 * 12, roofW = hallW + 2 * 9;
  const colS = span / 2;
  // roof top & truss depth along the length (m): highest over the column lines, thinner at the centre and the tips
  const top = (s) => { const a = Math.abs(s); const t = a < colS ? 0.86 + 0.14 * Math.pow(a / colS, 1.6) : 1 - 0.2 * Math.pow((a - colS) / (roofL / 2 - colS), 1.3); return G + 83 * FT * t + 1.2; };
  const depth = (s) => { const a = Math.abs(s); return a < colS ? 2.2 + (29 * FT - 2.2) * Math.pow(a / colS, 2) : 29 * FT - (29 * FT - 1.0) * Math.pow((a - colS) / (roofL / 2 - colS), 1.1); };
  const P = (s, t, y) => [c[0] + ax[0] * s + ay[0] * t, y, c[2] + ax[2] * s + ay[2] * t];
  const NS = 44, NT = 8;
  // roof surfaces: top (metal), underside (ceiling), long edges (fascia), ends
  const grid = (fy, mat, down) => {
    const base = g.nv;
    for (let i = 0; i <= NS; i++) for (let j = 0; j <= NT; j++) {
      const s = -roofL / 2 + roofL * i / NS, t = -roofW / 2 + roofW * j / NT;
      const y = fy(s, t); const h = 0.5; const ny = [0, 1, 0];
      const dy = (fy(s + h, t) - fy(s - h, t)) / (2 * h);
      const n = v3.norm([-ax[0] * dy, 1, -ax[2] * dy]);
      g.vert(P(s, t, y), down ? v3.mul(n, -1) : n, mat.c, mat.e, [s, t]);
    }
    for (let i = 0; i < NS; i++) for (let j = 0; j < NT; j++) {
      const a = base + i * (NT + 1) + j, b = a + NT + 1;
      if (!down) g.idx.push(a, a + 1, b, b, a + 1, b + 1); else g.idx.push(a, b, a + 1, b, b + 1, a + 1);
    }
  };
  const crown = (s, t) => top(s) + 0.6 * (1 - Math.pow(t / (roofW / 2), 2));
  grid(crown, M.roofMetal, false);
  grid((s, t) => top(s) - depth(s), M.ceiling, true);
  // fascia along both long edges and the two ends
  for (const sg of [-1, 1]) {
    for (let i = 0; i < NS; i++) {
      const s0 = -roofL / 2 + roofL * i / NS, s1 = s0 + roofL / NS; const t = sg * roofW / 2;
      const q = [P(s0, t, top(s0) - depth(s0)), P(s1, t, top(s1) - depth(s1)), P(s1, t, crown(s1, t)), P(s0, t, crown(s0, t))];
      if (sg > 0) g.quad(q[0], q[1], q[2], q[3], M.fascia.c, M.fascia.e); else g.quad(q[1], q[0], q[3], q[2], M.fascia.c, M.fascia.e);
    }
    const s = sg * roofL / 2;
    for (let j = 0; j < NT; j++) {
      const t0 = -roofW / 2 + roofW * j / NT, t1 = t0 + roofW / NT;
      const q = [P(s, t0, top(s) - depth(s)), P(s, t1, top(s) - depth(s)), P(s, t1, crown(s, t1)), P(s, t0, crown(s, t0))];
      if (sg < 0) g.quad(q[0], q[1], q[2], q[3], M.fascia.c, M.fascia.e); else g.quad(q[1], q[0], q[3], q[2], M.fascia.c, M.fascia.e);
    }
  }
  // glazed hall walls from the ramp level up to the roof underside
  const walls2 = (s0, t0, s1, t1, flip) => {
    const n = 24; for (let i = 0; i < n; i++) {
      const a0 = i / n, a1 = (i + 1) / n; const sA = s0 + (s1 - s0) * a0, sB = s0 + (s1 - s0) * a1, tA = t0 + (t1 - t0) * a0, tB = t0 + (t1 - t0) * a1;
      const q = [P(sA, tA, G + 5), P(sB, tB, G + 5), P(sB, tB, top(sB) - depth(sB)), P(sA, tA, top(sA) - depth(sA))];
      if (flip) g.quad(q[1], q[0], q[3], q[2], M.glass.c, M.glass.e); else g.quad(q[0], q[1], q[2], q[3], M.glass.c, M.glass.e);
    }
  };
  walls2(-hallL / 2, hallW / 2, hallL / 2, hallW / 2, false); walls2(-hallL / 2, -hallW / 2, hallL / 2, -hallW / 2, true);
  walls2(hallL / 2, -hallW / 2, hallL / 2, hallW / 2, true); walls2(-hallL / 2, -hallW / 2, -hallL / 2, hallW / 2, false);
  // twenty cantilevered columns (2 x 10) rising from the departures level at the column lines
  for (const sg of [-1, 1]) for (let j = 0; j < 10; j++) {
    const t = -hallW / 2 + 2 + (hallW - 4) * j / 9; const s = sg * colS; const p0 = P(s, t, G + 11);
    g.box([-0.7, 0, -0.7], [0.7, top(s) - depth(s) - (G + 11), 0.7], M.white.c, M.white.e, m4.basis(ax, [0, 1, 0], p0));
  }
}

// ---------------------------------------------------------------- control tower
export function buildTower(g, ring) {
  let cx = 0, cz = 0; ring.forEach(p => { cx += p[0] / ring.length; cz += p[1] / ring.length; });
  // three-storey integrated base building on the ATC footprint
  const r2 = ring.slice(); const neg = ringArea(r2) < 0;
  walls(g, r2, null, false, G, G + 14, M.concrete, [[G, G + 1.2, M.concrete], [G + 1.2, G + 13, M.glass], [G + 13, G + 14, M.fascia]]);
  cap(g, [r2], G + 14, M.roof);
  const T = m4.translate(cx, G, cz);
  // shaft: curved taper ("ascends in a graceful arc"), 30 in core walls at the base
  const prof = [[5.6, 14], [5.2, 20], [4.6, 28], [4.2, 36], [4.2, 44], [4.6, 50], [5.6, 54], [7.2, 57.2]];
  g.lathe(prof, 36, M.white.c, [0.55, 0, 2, 0], T, false);
  // vertical glass ribbon with LED "waterfall" (147 ft) on the west face
  const wf = m4.mul(T, m4.rotY(Math.PI)); // local +x -> world -x (west)
  for (let i = 0; i < prof.length - 1; i++) {
    const [ra, ya] = prof[i], [rb, yb] = prof[i + 1]; if (ya < 14 || yb > 14 + 147 * FT + 1) continue;
    const q = [[ra + 0.08, ya, -1.1], [ra + 0.08, ya, 1.1], [rb + 0.08, yb, 1.1], [rb + 0.08, yb, -1.1]].map(p => m4.xform(wf, p));
    g.quad(q[0], q[1], q[2], q[3], M.led.c, M.led.e);
  }
  // cab: floor slab, 24 slanted frameless panes over 270 degrees (outward lean), solid 90-degree segment, cantilever roof
  const off = [1.6, 0]; const C = m4.translate(cx + off[0], G, cz + off[1]);
  g.lathe([[7.2, 57.2], [7.6, 57.6], [7.6, 58.4]], 36, M.dark.c, M.dark.e, C, false);
  const r0 = 7.4, lean = 25 * Math.PI / 180, ph = 9 * FT; const y0 = G + 58.4, y1 = y0 + ph * Math.cos(lean), r1 = r0 + ph * Math.sin(lean);
  const a0 = Math.PI * 0.75; // start angle of the glazed arc (270 degrees, open side toward the terminals)
  for (let i = 0; i < 32; i++) {
    const A = a0 + i * (2 * Math.PI / 32), Bn = a0 + (i + 1) * (2 * Math.PI / 32);
    const glazed = i < 24; const mat = glazed ? M.towerGlass : M.white;
    const p = (a, r, y) => [cx + off[0] + Math.cos(a) * r, y, cz + off[1] + Math.sin(a) * r];
    g.quad(p(A, r0, y0), p(A, r1, y1), p(Bn, r1, y1), p(Bn, r0, y0), mat.c, mat.e);
  }
  g.lathe([[r1 + 0.1, y1], [r1 + 1.6, y1 + 0.35], [r1 + 1.6, y1 + 1.0], [2.5, y1 + 1.5]], 36, M.white.c, M.white.e, C, true);
  g.cylinder(0.18, 7, 8, M.dark.c, M.dark.e, m4.translate(cx + off[0], y1 + 1.4, cz + off[1]), true);
  return { cab: [cx + off[0], y0 + 1.5, cz + off[1]], top: y1 + 8.4 };
}
