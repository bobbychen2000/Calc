// Flight-deck window panes as flat glass facets fitted to each type's nose surface.
// Each pane is a convex quad whose corners are placed on the fuselage surface (starboard side; port is mirrored).
// Corner spec (normalized to the nose): u = distance from nose tip / Ln; then one of
//   post: true      -> on the windshield centre post (z = post half-width)
//   v               -> height above fuselage centreline / R (side-view coordinate)
//   d               -> depth below the local crown line / R
// The shader projects fragments onto each pane plane and evaluates an exact rounded-quad distance, which gives
// crisp anti-aliased outlines, rubber seals, painted posts between panes and a single flat reflection per pane.
import { fuselageSection } from './model.js';

const SPECS = {
  // Airbus A320/A330/A380 family: straight (level) lower edge on the side windows; rear window has the clipped
  // ("notched") upper-rear corner; round nose.
  airbus: { post: 0.06, r: 0.06, panes: [
    [{ u: 0.325, post: true }, { u: 0.470, post: true }, { u: 0.500, d: 0.140 }, { u: 0.400, v: 0.313 }],
    [{ u: 0.420, v: 0.303 }, { u: 0.505, d: 0.200 }, { u: 0.583, d: 0.230 }, { u: 0.583, v: 0.303 }],
    [{ u: 0.605, v: 0.303 }, { u: 0.605, d: 0.230 }, { u: 0.640, d: 0.235 }, { u: 0.687, d: 0.350 }, { u: 0.687, v: 0.303 }],
  ] },
  // Boeing 737/757/767/777: lower edges form a shallow "V" in side view (windshield edge falls toward the
  // No.1/No.2 post, side-window edges rise toward the rear); angular panes; pointier nose.
  boeing: { post: 0.045, r: 0.045, panes: [
    [{ u: 0.335, post: true }, { u: 0.470, post: true }, { u: 0.510, d: 0.130 }, { u: 0.420, v: 0.223 }],
    [{ u: 0.440, v: 0.234 }, { u: 0.535, d: 0.250 }, { u: 0.635, d: 0.280 }, { u: 0.620, v: 0.310 }],
    [{ u: 0.645, v: 0.320 }, { u: 0.655, d: 0.285 }, { u: 0.705, d: 0.300 }, { u: 0.725, v: 0.365 }],
  ] },
  // 747: squarer side windows (upper deck)
  b747: { post: 0.045, r: 0.045, panes: [
    [{ u: 0.3125, post: true }, { u: 0.473, post: true }, { u: 0.509, d: 0.136 }, { u: 0.420, v: 0.300 }],
    [{ u: 0.443, v: 0.300 }, { u: 0.475, d: 0.160 }, { u: 0.600, d: 0.170 }, { u: 0.600, v: 0.300 }],
    [{ u: 0.625, v: 0.300 }, { u: 0.625, d: 0.170 }, { u: 0.700, d: 0.180 }, { u: 0.700, v: 0.300 }],
  ] },
  // 787: four large panes; side windows taper toward the rear
  '787': { post: 0.05, r: 0.07, panes: [
    [{ u: 0.300, post: true }, { u: 0.460, post: true }, { u: 0.500, d: 0.130 }, { u: 0.400, v: 0.320 }],
    [{ u: 0.425, v: 0.310 }, { u: 0.520, d: 0.150 }, { u: 0.680, d: 0.180 }, { u: 0.660, v: 0.600 }],
  ] },
  // A350: six curved-edge panes inside the black "Zorro" mask
  a350: { post: 0.06, r: 0.09, mask: 0.2, panes: [
    [{ u: 0.300, post: true }, { u: 0.455, post: true }, { u: 0.490, d: 0.150 }, { u: 0.400, v: 0.320 }],
    [{ u: 0.425, v: 0.300 }, { u: 0.510, d: 0.170 }, { u: 0.590, d: 0.190 }, { u: 0.585, v: 0.300 }],
    [{ u: 0.610, v: 0.300 }, { u: 0.615, d: 0.190 }, { u: 0.655, d: 0.190 }, { u: 0.690, v: 0.300 }],
  ] },
  // Embraer E-Jets: four panes (windshield + one side window per side), straight lower edge, no notch
  ejet: { post: 0.05, r: 0.05, panes: [
    [{ u: 0.300, post: true }, { u: 0.470, post: true }, { u: 0.510, d: 0.140 }, { u: 0.410, v: 0.300 }],
    [{ u: 0.435, v: 0.300 }, { u: 0.535, d: 0.150 }, { u: 0.680, d: 0.190 }, { u: 0.700, v: 0.300 }],
  ] },
  // A220: four-pane windshield arrangement, sharper nose
  a220: { post: 0.05, r: 0.055, panes: [
    [{ u: 0.335, post: true }, { u: 0.470, post: true }, { u: 0.510, d: 0.130 }, { u: 0.420, v: 0.240 }],
    [{ u: 0.440, v: 0.250 }, { u: 0.535, d: 0.240 }, { u: 0.670, d: 0.290 }, { u: 0.690, v: 0.330 }],
  ] },
};

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

export function cockpitPanes(T) {
  if (T._panes) return T._panes;
  const C = T.cockpit; const S0 = SPECS[C.style] || SPECS.boeing;
  const Ln = T.Ln, R = T.R; const post = (C.post ?? S0.post) * Math.min(1.3, R / 1.9);
  const du = C.du ?? 0, dv = C.dv ?? 0, dAdd = C.dAdd ?? 0, uk = C.uk ?? 1;   // uk: stations of the spec scaled (777)
  const surf = (xn, th) => { const S = fuselageSection(T, xn); return [T.xMain - xn, T.Hc + S.y0 + (S.yt - S.y0) * Math.cos(th), S.w * Math.sin(th)]; };
  const corner = (c) => {
    const xn = (c.u * uk + du) * Ln; const S = fuselageSection(T, xn); let th;
    if (c.post) th = Math.asin(Math.min(1, post / S.w));
    else { const y = c.d != null ? S.yt - (c.d + dAdd) * R : (c.v + dv) * R; th = Math.acos(Math.max(-1, Math.min(1, (y - S.y0) / (S.yt - S.y0)))); }
    return { xn, th };
  };
  // arc length from the top centreline to angle th on the section at xn (matches the per-vertex value in model.js)
  const arcAt = (xn, th) => { const S = fuselageSection(T, xn); const n = 64; let a = 0, py = S.yt, pz = 0;
    for (let i = 1; i <= n; i++) { const t = th * i / n; const y = S.y0 + (S.yt - S.y0) * Math.cos(t), z = S.w * Math.sin(t); a += Math.hypot(y - py, z - pz); py = y; pz = z; } return a; };
  const panes = [];
  for (const spec of S0.panes) {
    const cs = spec.map(corner);
    const P = cs.map(c => surf(c.xn, c.th));
    const xc = cs.reduce((s, c) => s + c.xn, 0) / cs.length, tc = cs.reduce((s, c) => s + c.th, 0) / cs.length;
    const pc = surf(xc, tc);
    let n = norm(cross(sub(P[2], P[0]), sub(P[P.length - 1], P[1])));
    const Sc = fuselageSection(T, xc); const axis = [T.xMain - xc, T.Hc + Sc.y0, 0];
    if (dot(n, sub(pc, axis)) < 0) n = n.map(v => -v);
    const e1 = norm(cross([0, 1, 0], n)); const e2 = cross(n, e1);
    let q = cs.map(c => [c.xn, arcAt(c.xn, c.th)]); // unwrapped surface coordinates (m)
    const N = q.length;
    let area = 0; for (let i = 0; i < N; i++) { const a = q[i], b = q[(i + 1) % N]; area += a[0] * b[1] - b[0] * a[1]; }
    if (area < 0) q = q.reverse();
    // inset by corner radius (convex polygon offset)
    const r = S0.r; const lines = [];
    for (let i = 0; i < N; i++) { const a = q[i], b = q[(i + 1) % N]; const ex = b[0] - a[0], ey = b[1] - a[1]; const l = Math.hypot(ex, ey); const nx = -ey / l, ny = ex / l; lines.push({ p: [a[0] + nx * r, a[1] + ny * r], d: [ex / l, ey / l] }); }
    const qi = [];
    for (let i = 0; i < N; i++) { const L1 = lines[(i + N - 1) % N], L2 = lines[i]; const den = L1.d[0] * L2.d[1] - L1.d[1] * L2.d[0]; const t = ((L2.p[0] - L1.p[0]) * L2.d[1] - (L2.p[1] - L1.p[1]) * L2.d[0]) / den; qi.push([L1.p[0] + L1.d[0] * t, L1.p[1] + L1.d[1] * t]); }
    while (qi.length < 5) qi.push(qi[qi.length - 1]); // pad quads to 5 vertices (degenerate edge)
    const size = [Math.hypot(P[3][0] - P[0][0], P[3][1] - P[0][1], P[3][2] - P[0][2]), Math.hypot(P[1][0] - P[0][0], P[1][1] - P[0][1], P[1][2] - P[0][2])];
    const rad = Math.max(...P.map(p => Math.hypot(p[0] - pc[0], p[1] - pc[1], p[2] - pc[2])));
    panes.push({ c: pc, n, e1, e2, q: qi, size, rad, qRaw: q, corners: cs.map(c => [c.xn, arcAt(c.xn, c.th)]) });
  }
  const U = { uPaneC: [], uPaneN: [], uPaneE1: [], uPaneE2: [], uPaneQ: [] };
  for (let k = 0; k < 3; k++) {
    const p = panes[k] || { c: [1e4, 1e4, 1e4], n: [0, 1, 0], e1: [1, 0, 0], e2: [0, 0, 1], q: [[-9, -9], [-9, -9], [-9, -9], [-9, -9], [-9, -9]] };
    U.uPaneRad = U.uPaneRad || []; U.uPaneRad.push(p.rad ?? 0);
    U.uPaneC.push(...p.c); U.uPaneN.push(...p.n); U.uPaneE1.push(...p.e1); U.uPaneE2.push(...p.e2); U.uPaneQ.push(...p.q.flat(), 0, 0);
  }
  // parked windshield wiper on pane 0: runs from near the centre post along the lower edge (unwrapped coords)
  { const q = panes[0].qRaw; const A = q.find((p, i) => i === q.indexOf(q.reduce((m, p) => p[1] < m[1] ? p : m))) ; // lowest-s corner = post side
    const qa = panes[0].corners; const a = qa[0], dcorner = qa[3];
    const dirx = dcorner[0] - a[0], diry = dcorner[1] - a[1]; const L = Math.hypot(dirx, diry);
    const ux = dirx / L, uy = diry / L; const off = 0.075; // inset from bottom edge toward pane interior (+x = aft)
    const nx = uy, ny = -ux; const sgn = (nx * (qa[1][0] - a[0]) + ny * (qa[1][1] - a[1])) > 0 ? 1 : -1;
    const p0 = [a[0] + ux * 0.14 + nx * off * sgn, a[1] + uy * 0.14 + ny * off * sgn], p1 = [a[0] + ux * L * 0.62 + nx * off * 1.4 * sgn, a[1] + uy * L * 0.62 + ny * off * 1.4 * sgn];
    U.uWiper = [p0[0], p0[1], p1[0], p1[1]]; }
  U.uPaneInfo = [S0.r, panes.length, S0.mask || 0, (T.xMain - 0.85 * Ln)];
  T._panes = { U, panes };
  return T._panes;
}
