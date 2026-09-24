// Static airport buildings: terminals, piers, ITB, tower, garages, hangars, cargo, hotel, tanks
import { Geo } from '../geom.js';
import { stToWorld, TERMINAL_CENTER, PIERS, ITB, GROUND_Y } from '../geo.js';
import { m4, rng } from '../math.js';
import { pierFrame, pierOutline } from './airfield.js';

const G = GROUND_Y;
export const MAT = {
  glass: { c: [0.1, 0.1, 0.1, 1], e: [0.1, 0, 1, 0] },
  concrete: { c: [0.64, 0.62, 0.58, 1], e: [0.85, 0, 2, 0] },
  concreteDark: { c: [0.46, 0.45, 0.43, 1], e: [0.9, 0, 2, 0] },
  roof: { c: [0.58, 0.58, 0.56, 1], e: [0.9, 0, 5, 0] },
  roofDark: { c: [0.36, 0.36, 0.37, 1], e: [0.9, 0, 5, 0] },
  metalRoof: { c: [0.74, 0.76, 0.78, 1], e: [0.32, 0.85, 0, 0] },
  garage: { c: [0.62, 0.6, 0.56, 1], e: [0.9, 0, 3, 0] },
  parkRoof: { c: [0.34, 0.34, 0.35, 1], e: [0.9, 0, 11, 0] },
  corrugated: { c: [0.78, 0.79, 0.8, 1], e: [0.45, 0.6, 4, 0] },
  corrugatedBlue: { c: [0.25, 0.36, 0.52, 1], e: [0.45, 0.5, 4, 0] },
  hangarDoor: { c: [0.82, 0.83, 0.85, 1], e: [0.45, 0.5, 13, 0] },
  hotel: { c: [0.78, 0.74, 0.68, 1], e: [0.8, 0, 6, 0] },
  white: { c: [0.85, 0.85, 0.83, 1], e: [0.6, 0, 0, 0] },
  towerShaft: { c: [0.84, 0.84, 0.82, 1], e: [0.55, 0, 2, 0] },
  towerGlass: { c: [0.05, 0.06, 0.07, 1], e: [0.05, 0, 12, 0] },
  darkMetal: { c: [0.2, 0.21, 0.22, 1], e: [0.5, 0.7, 0, 0] },
};

const W = (s, t, h = 0) => stToWorld(s, t, h);
const W2 = (s, t) => { const p = stToWorld(s, t, 0); return [p[0], p[2]]; };
function area(poly) { let a = 0; for (let i = 0; i < poly.length; i++) { const p = poly[i], q = poly[(i + 1) % poly.length]; a += p[0] * q[1] - q[0] * p[1]; } return a; }
function ccw(poly) { return area(poly) > 0 ? poly : poly.slice().reverse(); }
function extrudeST(g, polyST, y0, y1, wall, roof) { g.extrude(ccw(polyST.map(p => W2(p[0], p[1]))), y0, y1, wall.c, wall.e, roof && roof.c, roof && roof.e); }
function rectST(cs, ct, ds, dt, ang = 0) { // rectangle centered, sizes along rotated axes (ang radians in s,t)
  const c = Math.cos(ang), s = Math.sin(ang); const pts = [[-ds / 2, -dt / 2], [ds / 2, -dt / 2], [ds / 2, dt / 2], [-ds / 2, dt / 2]];
  return pts.map(([a, b]) => [cs + a * c - b * s, ct + a * s + b * c]);
}
function arcST(r0, r1, a0, a1, n) { // annulus sector polygon (degrees)
  const [cs, ct] = TERMINAL_CENTER; const out = [];
  for (let i = 0; i <= n; i++) { const a = (a0 + (a1 - a0) * i / n) * Math.PI / 180; out.push([cs + Math.cos(a) * r1, ct + Math.sin(a) * r1]); }
  for (let i = n; i >= 0; i--) { const a = (a0 + (a1 - a0) * i / n) * Math.PI / 180; out.push([cs + Math.cos(a) * r0, ct + Math.sin(a) * r0]); }
  return out;
}

export function buildBuildings() {
  const g = new Geo();
  const [cs, ct] = TERMINAL_CENTER;
  // --- terminal ring segments (T1, T2, T3) ---
  for (const [a0, a1, h] of [[-150, -50, 20], [-45, 18, 23], [23, 150, 19]]) {
    extrudeST(g, arcST(172, 238, a0, a1, 36), G, G + 6, MAT.concreteDark, null);
    extrudeST(g, arcST(172, 238, a0, a1, 36), G + 6, G + h, MAT.glass, MAT.roof);
    // clerestory
    extrudeST(g, arcST(195, 215, a0 + 3, a1 - 3, 30), G + h, G + h + 4, MAT.glass, MAT.metalRoof);
  }
  // --- piers ---
  for (const p of PIERS) {
    const f = pierFrame(p); const poly = pierOutline(p);
    extrudeST(g, poly, G, G + 5.2, MAT.concreteDark, null);
    extrudeST(g, poly, G + 5.2, G + 12.5, MAT.glass, MAT.roof);
    const hw = p.w / 2; const P = (r, o) => [p.root[0] + f.d[0] * r + f.n[0] * o, p.root[1] + f.d[1] * r + f.n[1] * o];
    const inner = [P(5, -hw * 0.35), P(p.len - (p.end === 'rotunda' ? p.R : hw) - 4, -hw * 0.35), P(p.len - (p.end === 'rotunda' ? p.R : hw) - 4, hw * 0.35), P(5, hw * 0.35)];
    extrudeST(g, inner, G + 12.5, G + 15.5, MAT.glass, MAT.metalRoof);
    if (p.end === 'rotunda') { const c = P(p.len - p.R * 0.6, 0); const pts = []; for (let i = 0; i < 24; i++) { const a = i / 24 * Math.PI * 2; pts.push([c[0] + Math.cos(a) * p.R * 0.55, c[1] + Math.sin(a) * p.R * 0.55]); } extrudeST(g, pts, G + 12.5, G + 17, MAT.glass, MAT.metalRoof); }
  }
  // --- International Terminal (gull-wing roof) ---
  {
    const ic = [ITB.s, ITB.t]; const hs = ITB.hs, ht = ITB.ht; // half sizes in s,t
    // glass walls
    extrudeST(g, rectST(ic[0], ic[1], hs * 2, ht * 2), G, G + 22, MAT.glass, null);
    // roof: profile along s, extruded along t
    const prof = []; const N = 48;
    for (let i = 0; i <= N; i++) { const x = -hs - 6 + (2 * hs + 12) * i / N; const ax = Math.abs(x) / (hs + 6); const y = 22 + 13 * Math.sin(Math.PI * Math.min(1, ax * 1.0)) * (0.35 + 0.65 * ax) + 2.0 * (1 - ax); prof.push([x, y]); }
    const segT = 30; const base = g.nv; const c = MAT.metalRoof.c, e = MAT.metalRoof.e;
    for (let j = 0; j <= segT; j++) {
      const t = ic[1] - ht - 8 + (2 * ht + 16) * j / segT;
      for (let i = 0; i <= N; i++) {
        const [x, y] = prof[i]; const [xa, ya] = prof[Math.max(0, i - 1)], [xb, yb] = prof[Math.min(N, i + 1)];
        const dx = xb - xa, dy = yb - ya; const l = Math.hypot(dx, dy); const nS = -dy / l, nY = dx / l;
        const p = W(ic[0] + x, t, G + y);
        // normal from s-direction component
        const ws = W(1, 0, 0), w0 = W(0, 0, 0); const sdir = [ws[0] - w0[0], 0, ws[2] - w0[2]];
        g.vert(p, [sdir[0] * nS, nY, sdir[2] * nS], c, e);
      }
    }
    for (let j = 0; j < segT; j++) for (let i = 0; i < N; i++) { const a = base + j * (N + 1) + i, b = a + 1, cc = a + N + 1, d = cc + 1; g.idx.push(a, b, cc, b, d, cc); g.idx.push(a, cc, b, b, cc, d); }
    // gable walls under roof at both t ends (glass)
    for (const sgn of [-1, 1]) {
      const t = ic[1] + sgn * ht; const b0 = g.nv;
      const tdir = W(0, 1, 0), t0 = W(0, 0, 0); const n = [(tdir[0] - t0[0]) * sgn, 0, (tdir[2] - t0[2]) * sgn];
      for (let i = 0; i <= N; i++) { const [x, y] = prof[i]; const xc = Math.max(-hs, Math.min(hs, x)); g.vert(W(ic[0] + xc, t, G + 22), n, MAT.glass.c, MAT.glass.e); g.vert(W(ic[0] + xc, t, G + y - 0.3), n, MAT.glass.c, MAT.glass.e); }
      for (let i = 0; i < N; i++) { const a = b0 + i * 2; g.idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); g.idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
    }
  }
  // --- central garage ---
  {
    const poly = rectST(cs, ct, 205, 205, 0.0);
    extrudeST(g, poly, G, G + 17, MAT.garage, MAT.parkRoof);
    // stair/elevator cores
    for (const [a, b] of [[-60, -60], [60, 60], [-60, 60], [60, -60]]) extrudeST(g, rectST(cs + a, ct + b, 9, 9), G + 17, G + 22, MAT.concrete, MAT.roofDark);
  }
  // elevated departures roadway ring + AirTrain guideway
  {
    const ring = (r0, r1, y0, y1, mat) => extrudeST(g, arcST(r0, r1, -178, 178, 72), y0, y1, mat, mat);
    ring(148, 170, G + 7.2, G + 8.4, MAT.concrete);
    ring(157, 161, G + 13.0, G + 14.8, MAT.concrete);
    for (let a = -175; a < 175; a += 9) { const r = 159, rr = a * Math.PI / 180; const p = [cs + Math.cos(rr) * r, ct + Math.sin(rr) * r]; extrudeST(g, rectST(p[0], p[1], 1.6, 1.6), G, G + 13, MAT.concrete, null); }
  }
  // --- control tower (between T1/T2) ---
  {
    const a = -16 * Math.PI / 180, r = 262; const tc = [cs + Math.cos(a) * r, ct + Math.sin(a) * r];
    extrudeST(g, rectST(tc[0], tc[1], 30, 24, a), G, G + 10, MAT.concrete, MAT.roof);
    const wp = W(tc[0], tc[1], G);
    const M = m4.translate(wp[0], wp[1], wp[2]);
    g.lathe([[6.8, 0], [6.8, 10], [6.0, 14], [4.9, 28], [4.3, 44], [5.0, 50], [7.5, 54], [9.0, 56.5]], 40, MAT.towerShaft.c, MAT.towerShaft.e, M);
    g.lathe([[9.0, 56.5], [9.4, 57.2]], 40, MAT.darkMetal.c, MAT.darkMetal.e, M);
    g.lathe([[9.4, 57.2], [10.4, 63.4]], 40, MAT.towerGlass.c, MAT.towerGlass.e, M);
    g.lathe([[10.4, 63.4], [11.2, 64.2], [11.2, 65.4], [8.0, 66.4], [3.0, 67.2]], 40, MAT.white.c, MAT.white.e, M, true);
    g.cylinder(0.35, 9, 8, MAT.darkMetal.c, MAT.darkMetal.e, m4.translate(wp[0], wp[1] + 67, wp[2]));
    g.cylinder(1.2, 1.2, 12, MAT.white.c, MAT.white.e, m4.translate(wp[0] + 3, wp[1] + 67, wp[2]));
  }
  // --- ITB garages A & G, rental car center ---
  for (const [s, t] of [[-1330, -1085], [-1330, -615]]) extrudeST(g, rectST(s, t, 110, 140), G, G + 19, MAT.garage, MAT.parkRoof);
  extrudeST(g, rectST(-2150, -260, 260, 150), G, G + 21, MAT.garage, MAT.parkRoof);
  // --- hotel (curved slab) ---
  {
    const pts = []; const R0 = 260, cxs = -1420 - R0, cts = -420; const n = 12;
    for (let i = 0; i <= n; i++) { const a = (-18 + 36 * i / n) * Math.PI / 180; pts.push([cxs + Math.cos(a) * (R0 + 9), cts + Math.sin(a) * (R0 + 9)]); }
    for (let i = n; i >= 0; i--) { const a = (-18 + 36 * i / n) * Math.PI / 180; pts.push([cxs + Math.cos(a) * (R0 - 9), cts + Math.sin(a) * (R0 - 9)]); }
    extrudeST(g, pts, G, G + 42, MAT.hotel, MAT.roof);
  }
  // --- cargo warehouses (north) ---
  for (const s of [-1650, -1360, -1070, -780]) { extrudeST(g, rectST(s, 690, 260, 55), G, G + 13, MAT.corrugated, MAT.roof); }
  // --- maintenance hangars (barrel roofs) ---
  for (const s of [-960, -770, -580, -390]) {
    const hs = 85, t0 = 1285, t1 = 1395, hWall = 24, hTop = 36;
    extrudeST(g, rectST(s, (t0 + t1) / 2, hs * 2, t1 - t0), G, G + hWall, MAT.corrugatedBlue, null);
    // door panel on apron side
    extrudeST(g, rectST(s, t0 - 0.6, hs * 1.8, 1.2), G, G + hWall - 2, MAT.hangarDoor, null);
    // barrel roof along t
    const N = 24; const base = g.nv;
    for (let j = 0; j <= 1; j++) { const t = j ? t1 : t0; for (let i = 0; i <= N; i++) { const x = -hs + 2 * hs * i / N; const u = x / hs; const y = hWall + (hTop - hWall) * (1 - u * u); const sd = W(1, 0, 0), s0 = W(0, 0, 0); const slope = -2 * u * (hTop - hWall) / hs; const l = Math.hypot(slope, 1); g.vert(W(s + x, t, G + y), [(sd[0] - s0[0]) * -slope / l, 1 / l, (sd[2] - s0[2]) * -slope / l], MAT.corrugated.c, [0.45, 0.7, 4, 0]); } }
    for (let i = 0; i < N; i++) { const a = base + i, b = a + 1, c = a + N + 1, d = c + 1; g.idx.push(a, b, c, b, d, c, a, c, b, b, c, d); }
    // gable ends
    for (const t of [t0, t1]) { const b0 = g.nv; for (let i = 0; i <= N; i++) { const x = -hs + 2 * hs * i / N; const u = x / hs; const y = hWall + (hTop - hWall) * (1 - u * u); g.vert(W(s + x, t, G + hWall), [0, 0, 1], MAT.corrugatedBlue.c, MAT.corrugatedBlue.e); g.vert(W(s + x, t, G + y), [0, 0, 1], MAT.corrugatedBlue.c, MAT.corrugatedBlue.e); } for (let i = 0; i < N; i++) { const a = b0 + i * 2; g.idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2, a, a + 2, a + 1, a + 1, a + 2, a + 3); } }
  }
  // --- fuel farm ---
  for (const s of [-2080, -2030, -1980]) for (const t of [830, 885]) { const p = W(s, t, G); g.cylinder(17, 14, 32, MAT.white.c, MAT.white.e, m4.translate(p[0], p[1], p[2])); }
  // --- misc service buildings ---
  const R = rng(42);
  const spots = [[-560, -1560, 60, 35, 10], [-420, -1580, 40, 30, 8], [-1700, 560, 50, 40, 9], [-300, 560, 70, 40, 12], [-1150, 760, 90, 45, 11], [-600, 740, 50, 30, 9], [300, -1560, 30, 20, 6], [-1500, -1450, 80, 40, 10]];
  for (const [s, t, a, b, h] of spots) extrudeST(g, rectST(s, t, a, b), G, G + h, R() < 0.5 ? MAT.concrete : MAT.corrugated, MAT.roof);
  return g.data();
}
