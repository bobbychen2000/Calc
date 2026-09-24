// Procedural airliner geometry. Local frame: x forward, y up, z right (starboard).
// Origin: ground contact point below the main gear (gear down, level attitude).
import { Geo } from '../geom.js';
import { m4, v3 } from '../math.js';

import { TYPES } from './types.js';
export { TYPES };

// part ids for shader
export const PART = { generic: 0, fuselage: 1, wing: 2, fin: 3, nacelle: 4, fan: 5, tire: 6, gear: 7, hstab: 8, exhaust: 10, lip: 11, pylon: 12, flap: 13, hub: 14 };
const E = (part, rough = 0.3, metal = 0) => [rough, metal, part, 0];

export function fuselageSection(T, xn) { // xn: distance from nose. returns {yt, yb, y0, w} relative to centerline
  const { L, R, Ln, Lt } = T; const top = (T.top || 1.03) * R;
  let yt = top, yb = -R, w = R;
  if (xn < Ln) {
    const s = 1 - xn / Ln; // 1 at tip
    const yTip = -(T.noseTip ?? 0.2) * R;
    const q = Math.max(0, 1 - s * s);
    const nz = T.nose || { pt: 0.85, pb: 0.85, pw: 0.67 }; // exponents: higher = pointier (Boeing), lower = rounder (Airbus)
    // upper profile: either a smooth power curve, or (for noses with a distinct windshield "knee") a monotone spline
    // through control points: gently rising radome, steeper windshield facet, then the crown.
    yt = yTip + (top - yTip) * (T.noseTop ? noseSpline(T.noseTop, xn / Ln) : Math.pow(q, nz.pt));
    yb = yTip - (R + yTip) * Math.pow(q, nz.pb);
    w = R * Math.pow(q, nz.pw);
  } else if (xn > L - Lt) {
    const s = (xn - (L - Lt)) / Lt;
    const endY = T.pointyTail ? 0.45 : 0.6;
    yt = top * (1 - (1 - endY - 0.05) * Math.pow(s, 2.0));
    yb = -R + R * (1 + endY) * Math.pow(s, 1.25);
    w = R * (1 - 0.95 * Math.pow(s, T.pointyTail ? 1.3 : 1.5));
  }
  const y0 = (yt + yb) / 2 * (xn < Ln || xn > L - Lt ? 1 : 0) + (xn >= Ln && xn <= L - Lt ? (top - R) / 2 : 0);
  if (T.hump) { // 747 upper deck
    const H = T.hump; const ramp = smooth01((xn - 1.2) / 6.8) * (1 - smooth01((xn - (H.x1 - 11)) / 11));
    yt += H.h * ramp;
  }
  return { yt, yb, w, y0 };
}
const smooth01 = (x) => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };
// monotone cubic (Fritsch-Carlson) through [[u, f]...]; square-root start gives the rounded (vertical-tangent) nose tip
function noseSpline(P, u) {
  u = Math.max(0, Math.min(1, u));
  if (u < P[1][0]) return P[1][1] * Math.sqrt(u / P[1][0]);
  const n = P.length; if (!P._m) {
    const d = []; for (let i = 0; i < n - 1; i++) d.push((P[i + 1][1] - P[i][1]) / (P[i + 1][0] - P[i][0]));
    const m = [d[0]]; for (let i = 1; i < n - 1; i++) m.push(d[i - 1] * d[i] <= 0 ? 0 : 2 / (1 / d[i - 1] + 1 / d[i])); m.push(0);
    m[1] = Math.min(m[1], 3 * d[1]); P._m = m;
  }
  const m = P._m; let i = 1; while (i < n - 2 && u > P[i + 1][0]) i++;
  const h = P[i + 1][0] - P[i][0], t = (u - P[i][0]) / h, t2 = t * t, t3 = t2 * t;
  return (2 * t3 - 3 * t2 + 1) * P[i][1] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * P[i + 1][1] + (t3 - t2) * h * m[i + 1];
}

function airfoil(n, tc) { // closed loop from TE along upper to LE to lower back to TE: returns [[xi, y]]
  const pts = [];
  const th = (x) => 5 * tc * (0.2969 * Math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x * x * x - 0.1036 * x * x * x * x);
  const camber = (x) => 0.02 * Math.sin(Math.PI * Math.pow(x, 0.8)) * tc * 3;
  for (let i = 0; i <= n; i++) { const x = 0.5 * (1 + Math.cos(Math.PI * i / n)); pts.push([x, camber(x) + th(x)]); } // TE->LE upper
  for (let i = 1; i < n; i++) { const x = 0.5 * (1 - Math.cos(Math.PI * i / n)); pts.push([x, camber(x) - th(x) * 0.85]); } // LE->TE lower
  return pts;
}

// Loft a lifting surface through stations: {x (LE), y, z, c, tc, twist}; axis: 'z' spanwise (wing) or 'y' (fin)
function loftSurface(g, stations, n, col, ext, opts = {}) {
  const loops = stations.map(st => airfoil(n, st.tc).map(([xi, yy]) => {
    const cx = st.x + xi * st.c; const cy = yy * Math.abs(st.c);
    if (opts.vertical) return [cx, st.y, st.z + cy]; // fin: thickness along z
    // twist about quarter chord
    const tw = (st.twist || 0) * Math.PI / 180; const dx = cx - (st.x + 0.25 * st.c);
    return [st.x + 0.25 * st.c + dx * Math.cos(tw) + cy * Math.sin(tw), st.y + cy * Math.cos(tw) - dx * Math.sin(tw), st.z];
  }));
  const m = loops[0].length; const base = g.nv;
  // normals via neighbors
  for (let j = 0; j < loops.length; j++) {
    for (let i = 0; i < m; i++) {
      const p = loops[j][i]; const pa = loops[j][(i + m - 1) % m], pb = loops[j][(i + 1) % m];
      const q = loops[Math.min(loops.length - 1, j + 1)][i], r = loops[Math.max(0, j - 1)][i];
      let n1 = v3.norm(v3.cross(v3.sub(pb, pa), v3.sub(q, r)));
      if (opts.flip) n1 = v3.mul(n1, -1);
      g.vert(p, n1, col, ext, [j / (loops.length - 1), i / m]);
    }
  }
  for (let j = 0; j < loops.length - 1; j++) for (let i = 0; i < m; i++) {
    const a = base + j * m + i, b = base + j * m + (i + 1) % m, c = a + m, d = b + m;
    if (opts.flip) g.idx.push(a, b, c, b, d, c); else g.idx.push(a, c, b, b, c, d);
  }
  // end caps
  for (const j of [0, loops.length - 1]) {
    if (opts.noCap && opts.noCap.includes(j)) continue;
    const ctr = loops[j].reduce((s, p) => v3.add(s, p), [0, 0, 0]).map(v => v / m);
    const nn = v3.norm(v3.sub(ctr, loops[j === 0 ? 1 : loops.length - 2].reduce((s, p) => v3.add(s, p), [0, 0, 0]).map(v => v / m)));
    const c0 = g.vert(ctr, nn, col, ext); const b0 = g.nv;
    loops[j].forEach(p => g.vert(p, nn, col, ext));
    for (let i = 0; i < m; i++) { const i1 = b0 + i, i2 = b0 + (i + 1) % m; if ((j === 0) !== !!opts.flip) g.idx.push(c0, i1, i2); else g.idx.push(c0, i2, i1); }
  }
}

export function buildAircraft(typeName, lod = 1) {
  const T = TYPES[typeName]; const { L, R, Hc, xMain } = T;
  const X = (xn) => xMain - xn; // nose-based distance -> local x
  const parts = {};
  const body = new Geo();
  const white = [0.9, 0.9, 0.9, 1];
  const hi = lod > 0.5;
  // ---------- fuselage (two half-ellipses per section) ----------
  const nAround = hi ? 56 : 18, nAlong = hi ? 110 : 30;
  const W = T.wing;
  {
    const base = body.nv; const xs = [];
    for (let i = 0; i <= nAlong; i++) { const u = i / nAlong;
      let xn; if (u < 0.22) xn = T.Ln * 1.5 * Math.pow(u / 0.22, 1.6); else if (u > 0.78) xn = L - T.Lt * 1.15 * Math.pow((1 - u) / 0.22, 1.1); else xn = T.Ln * 1.5 + (L - T.Lt * 1.15 - T.Ln * 1.5) * (u - 0.22) / 0.56; xs.push(Math.min(L, Math.max(0, xn))); }
    xs[0] = 0.0001;
    const bx0 = W.rootLE - 3, bx1 = W.rootLE + W.rootC + 4;
    for (const xn of xs) {
      const S = fuselageSection(T, xn);
      let bump = 0; if (xn > bx0 && xn < bx1) { const t = (xn - bx0) / (bx1 - bx0); bump = Math.sin(Math.PI * t) ** 0.7; }
      const ring = [];
      for (let k = 0; k <= nAround; k++) {
        const th = k / nAround * Math.PI * 2; const c = Math.cos(th), s = Math.sin(th);
        let y = c >= 0 ? S.y0 + (S.yt - S.y0) * c : S.y0 + (S.y0 - S.yb) * c; let z = S.w * s;
        if (c < 0) { y -= bump * 0.15 * R * (-c) ** 1.5; z *= 1 + bump * 0.11 * (-c); }
        ring.push([y, z, c, s]);
      }
      // arc length from the top centreline (both sides), used to place flight-deck windows on the surface
      const arc = new Array(nAround + 1).fill(0);
      for (let k = 1; k <= nAround / 2; k++) arc[k] = arc[k - 1] + Math.hypot(ring[k][0] - ring[k - 1][0], ring[k][1] - ring[k - 1][1]);
      for (let k = nAround - 1; k > nAround / 2; k--) arc[k] = arc[k + 1] + Math.hypot(ring[k][0] - ring[k + 1][0], ring[k][1] - ring[k + 1][1]);
      for (let k = 0; k <= nAround; k++) {
        const [y, z, c, s] = ring[k]; const dTop = S.yt - y;
        const e = E(PART.fuselage, 0.28, 0); e[3] = arc[k];
        body.vert([X(xn), Hc + y, z], [0, c, s], [0.9, 0.9, 0.9, dTop], e, [xn, y]);
      }
    }
    const cols = nAround + 1;
    for (let i = 0; i < xs.length; i++) for (let k = 0; k <= nAround; k++) {
      const idx = base + i * cols + k; const P = (ii, kk) => { const id = base + Math.min(xs.length - 1, Math.max(0, ii)) * cols + ((kk + nAround) % nAround); return [body.pos[id * 3], body.pos[id * 3 + 1], body.pos[id * 3 + 2]]; };
      const du = v3.sub(P(i + 1, k), P(i - 1, k)), dv = v3.sub(P(i, k + 1), P(i, k - 1));
      let n = v3.norm(v3.cross(dv, du)); if (i === 0) n = [1, 0, 0];
      body.nrm[idx * 3] = n[0]; body.nrm[idx * 3 + 1] = n[1]; body.nrm[idx * 3 + 2] = n[2];
    }
    for (let i = 0; i < xs.length - 1; i++) for (let k = 0; k < nAround; k++) { const a = base + i * cols + k, b = a + 1, c = a + cols, d = c + 1; body.idx.push(a, b, c, b, d, c); }
  }
  // ---------- wings ----------
  const nAf = hi ? 22 : 8;
  const tanS = Math.tan(W.sweep * Math.PI / 180), tanD = Math.tan(W.dihedral * Math.PI / 180);
  const z0 = R * 0.88, semi = W.span / 2 - (W.tip === 'raked' ? W.tipH * 0.9 : 0) - (['sharklet', 'blended', 'split', 'curved', 'small'].includes(W.tip) ? 0.35 : 0);
  const wingY = (z) => Hc - W.y * R + (z - z0) * tanD + W.flex * Math.pow(Math.max(0, z - z0) / (semi - z0), 2);
  const leX = (z) => X(W.rootLE) - (z - z0) * tanS;
  const chordAt = (z) => z < W.kinkZ ? W.rootC + (W.kinkC - W.rootC) * (z - z0) / (W.kinkZ - z0) : W.kinkC + (W.tipC - W.kinkC) * (z - W.kinkZ) / (semi - W.kinkZ);
  const tcAt = (z) => W.tcRoot + (W.tcTip - W.tcRoot) * Math.min(1, Math.max(0, (z - z0) / (semi - z0)));
  const stAt = (z) => { const c = chordAt(z); const tw = -2.5 * (z - z0) / (semi - z0); return { x: leX(z), y: wingY(z), cFull: c, twist: -tw }; };
  const flapZ0 = z0 + 0.4, flapZ1 = z0 + (semi - z0) * 0.72, flapFrac = 0.74;
  const wcol = [0.78, 0.79, 0.8, 1], wext = E(PART.wing, 0.42, 0.35);
  const buildWing = (sg) => {
    const g = new Geo();
    const zs = (a, b, n) => Array.from({ length: n + 1 }, (_, i) => a + (b - a) * i / n);
    const inner = zs(z0 - 0.3, flapZ1, hi ? 8 : 3).map(z => { const s = stAt(z); return { x: s.x, y: s.y, z: z * sg, c: -s.cFull * flapFrac, tc: tcAt(z) / flapFrac * 0.9, twist: s.twist }; });
    const outer = zs(flapZ1, semi, hi ? 8 : 3).map(z => { const s = stAt(z); return { x: s.x, y: s.y, z: z * sg, c: -s.cFull, tc: tcAt(z), twist: s.twist }; });
    loftSurface(g, inner, nAf, wcol, wext, { flip: sg < 0 });
    loftSurface(g, outer, nAf, wcol, wext, { flip: sg < 0 });
    const tip = stAt(semi); const tc = tcAt(semi);
    const tipLoft = (fn, n = 5, tcx = 0.1) => { const ws = []; for (let i = 0; i <= n; i++) { const t = i / n; const q = fn(t); ws.push({ x: q.x, y: q.y, z: q.z * sg, c: -q.c, tc: tcx }); } loftSurface(g, ws, nAf, wcol, wext, { flip: sg < 0 }); };
    const h = W.tipH || 0;
    if (W.tip === 'sharklet') tipLoft(t => { const a = Math.min(1, t * 1.6); return { x: tip.x - t * t * 1.2 - 0.25 * tip.cFull * a, y: tip.y + h * Math.pow(t, 0.9) + 0.25 * a, z: semi + 0.55 * Math.sin(a * 1.57), c: tip.cFull * (1 - 0.6 * t) }; }, 6, 0.09);
    else if (W.tip === 'blended') tipLoft(t => { const a = Math.min(1, t * 1.3); return { x: tip.x - t * 1.5 - 0.2 * tip.cFull * a, y: tip.y + h * Math.pow(t, 1.3), z: semi + 0.8 * Math.sin(a * 1.57), c: tip.cFull * (1 - 0.62 * t) }; }, 7, 0.09);
    else if (W.tip === 'split') { tipLoft(t => ({ x: tip.x - t * 1.3 - 0.2 * tip.cFull, y: tip.y + h * Math.pow(t, 1.1), z: semi + 0.5 * Math.min(1, t * 2), c: tip.cFull * (1 - 0.6 * t) }), 6, 0.09); tipLoft(t => ({ x: tip.x - 0.25 * tip.cFull - t * 0.9, y: tip.y - 0.9 * t, z: semi + 0.35 * t, c: tip.cFull * 0.7 * (1 - 0.6 * t) }), 3, 0.09); }
    else if (W.tip === 'raked') tipLoft(t => ({ x: tip.x - t * h * 1.05, y: tip.y + t * t * 0.3, z: semi + t * h * 0.9, c: tip.cFull * (1 - 0.82 * t) }), 5, tc);
    else if (W.tip === 'curved') tipLoft(t => { const a = t * 1.45; return { x: tip.x - t * 1.8, y: tip.y + h * (1 - Math.cos(a)), z: semi + h * 0.95 * Math.sin(a), c: tip.cFull * (1 - 0.65 * t) }; }, 8, tc);
    else if (W.tip === 'small') tipLoft(t => ({ x: tip.x - t * 0.9 - 0.15 * tip.cFull, y: tip.y + h * t, z: semi + 0.3 * Math.min(1, t * 2), c: tip.cFull * (1 - 0.55 * t) }), 4, 0.09);
    else if (W.tip === 'fence') { tipLoft(t => ({ x: tip.x + 0.2 - t * 0.9, y: tip.y + h * 0.62 * t, z: semi + 0.05, c: tip.cFull * (1 - 0.35 * t) }), 3, 0.06); tipLoft(t => ({ x: tip.x + 0.2 - t * 0.5, y: tip.y - h * 0.38 * t, z: semi + 0.05, c: tip.cFull * 0.8 * (1 - 0.3 * t) }), 3, 0.06); }
    return g;
  };
  const buildFlap = (sg, zA, zB) => {
    const g = new Geo(); const col = [0.72, 0.73, 0.75, 1]; const ext = E(PART.flap, 0.45, 0.3);
    const zs = Array.from({ length: 4 }, (_, i) => zA + (zB - zA) * i / 3);
    const sts = zs.map(z => { const s = stAt(z); return { x: s.x - s.cFull * flapFrac, y: s.y - 0.01 * s.cFull, z: z * sg, c: -s.cFull * (1 - flapFrac) * 1.05, tc: 0.35 * tcAt(z) / (1 - flapFrac) * 0.5 }; });
    loftSurface(g, sts, 8, col, ext, { flip: sg < 0 });
    const sm = stAt((zA + zB) / 2);
    return { g, hinge: [sm.x - sm.cFull * flapFrac, sm.y, (zA + zB) / 2 * sg], chord: sm.cFull * (1 - flapFrac) };
  };
  const buildSpoiler = (sg, zA, zB) => {
    const g = new Geo(); const col = [0.7, 0.71, 0.73, 1]; const ext = E(PART.flap, 0.45, 0.3);
    const sA = { ...stAt(zA), z: zA }, sB = { ...stAt(zB), z: zB };
    const f0 = 0.52, f1 = flapFrac - 0.01;
    const top = (s, f) => { const xi = f; const tcz = tcAt(s.z); const yy = 5 * tcz * (0.2969 * Math.sqrt(xi) - 0.126 * xi - 0.3516 * xi * xi + 0.2843 * xi ** 3 - 0.1036 * xi ** 4) * s.cFull + 0.02 * Math.sin(Math.PI * Math.pow(xi, 0.8)) * tcz * 3 * s.cFull; return [s.x - f * s.cFull, s.y + yy + 0.035, s.z * sg]; };
    const p0 = top(sA, f0), p1 = top(sA, f1), p2 = top(sB, f1), p3 = top(sB, f0);
    if (sg > 0) g.quad(p0, p3, p2, p1, col, ext); else g.quad(p0, p1, p2, p3, col, ext);
    return { g, hinge: p0, hinge2: p3 };
  };
  body.merge(buildWing(1)); body.merge(buildWing(-1));
  parts.flaps = []; parts.spoilers = [];
  for (const sg of [1, -1]) {
    parts.flaps.push({ ...buildFlap(sg, flapZ0, W.kinkZ), side: sg, kind: 'inboard' });
    parts.flaps.push({ ...buildFlap(sg, W.kinkZ + 0.3, flapZ1), side: sg, kind: 'outboard' });
    const n = hi ? 4 : 2; for (let i = 0; i < n; i++) { const zA = W.kinkZ * 0.6 + (flapZ1 - W.kinkZ * 0.6) * i / n, zB = W.kinkZ * 0.6 + (flapZ1 - W.kinkZ * 0.6) * (i + 1) / n - 0.1; parts.spoilers.push({ ...buildSpoiler(sg, zA, zB), side: sg }); }
  }
  // ---------- vertical fin (+ dorsal) ----------
  const F = T.fin; const tSf = Math.tan(F.sweep * Math.PI / 180);
  const finRootY = Hc + fuselageSection(T, F.x + F.rootC * 0.5).yt - 0.3;
  {
    const sts = [0, 0.33, 0.66, 1].map(f => { const h = F.h * f; const c = F.rootC + (F.tipC - F.rootC) * f; return { x: X(F.x) - h * tSf, y: finRootY + h, c: -c, tc: 0.11 }; });
    const loops = sts.map(s => airfoil(nAf, s.tc).map(([xi, yy]) => [s.x + xi * s.c, s.y, yy * Math.abs(s.c) * 0.9]));
    const m = loops[0].length; const base = body.nv;
    for (let j = 0; j < loops.length; j++) for (let i = 0; i < m; i++) {
      const p = loops[j][i]; const pa = loops[j][(i + m - 1) % m], pb = loops[j][(i + 1) % m];
      body.vert(p, v3.norm(v3.cross([0, 1, 0], v3.sub(pb, pa))), white, E(PART.fin, 0.28, 0), [j / 3, (p[1] - finRootY) / F.h]);
    }
    for (let j = 0; j < loops.length - 1; j++) for (let i = 0; i < m; i++) { const a = base + j * m + i, b = base + j * m + (i + 1) % m, c = a + m, d = b + m; body.idx.push(a, b, c, b, d, c); }
    const topC = loops[3].reduce((s, p) => v3.add(s, p), [0, 0, 0]).map(v => v / m); const c0 = body.vert(topC, [0, 1, 0], white, E(PART.fin, 0.28, 0), [1, 1]); const b0 = body.nv;
    loops[3].forEach(p => body.vert(p, [0, 1, 0], white, E(PART.fin, 0.28, 0), [1, 1]));
    for (let i = 0; i < m; i++) body.idx.push(c0, b0 + (i + 1) % m, b0 + i);
    if (F.dorsal) { // small fillet ahead of the fin root
      const d = [0, 1].map(f => ({ x: X(F.x) + 3.2 * (1 - f) , y: finRootY + f * 1.1, c: -(3.2 + F.rootC * 0.25) * (1 - f) - F.rootC * 0.25 * f - 0.3, tc: 0.12 }));
      const dl = d.map(s => airfoil(8, s.tc).map(([xi, yy]) => [s.x + xi * s.c, s.y, yy * Math.abs(s.c) * 0.5]));
      const mm = dl[0].length; const bb = body.nv;
      for (let j = 0; j < 2; j++) for (let i = 0; i < mm; i++) { const p = dl[j][i]; const pa = dl[j][(i + mm - 1) % mm], pb = dl[j][(i + 1) % mm]; body.vert(p, v3.norm(v3.cross([0, 1, 0], v3.sub(pb, pa))), white, E(PART.fin, 0.28, 0), [0, 0]); }
      for (let i = 0; i < mm; i++) { const a = bb + i, b = bb + (i + 1) % mm, c = a + mm, dd = b + mm; body.idx.push(a, b, c, b, dd, c); }
    }
  }
  // ---------- horizontal stabilizer ----------
  {
    const H = T.hstab; const tS = Math.tan(H.sweep * Math.PI / 180), tD = Math.tan(H.dihedral * Math.PI / 180);
    const hz0 = H.tTail ? 0.2 : 0.35 * R;
    const hx = H.tTail ? X(F.x) - F.h * tSf - 0.3 : X(H.x);
    const hy = H.tTail ? finRootY + F.h - 0.1 : Hc + H.y * R + 0.3;
    for (const sg of [1, -1]) {
      const sts = [0, 0.5, 1].map(f => { const z = hz0 + (H.span / 2 - hz0) * f; const c = H.rootC + (H.tipC - H.rootC) * f; return { x: hx - (z - hz0) * tS, y: hy + (z - hz0) * tD, z: z * sg, c: -c, tc: 0.11 }; });
      loftSurface(body, sts, nAf, [0.85, 0.86, 0.87, 1], E(PART.hstab, 0.32, 0.1), { flip: sg < 0 });
    }
  }
  // ---------- engines ----------
  const nSeg = hi ? 40 : 14; const engines = [];
  const nacelle = (M, r, len, flat, chevron) => {
    const S = flat ? m4.mul(M, m4.scale(1, 1, 1)) : M;
    const prof = [[r * 0.84, 0], [r * 0.95, 0.05 * len], [r * 1.0, 0.18 * len], [r * 1.0, 0.45 * len], [r * 0.92, 0.72 * len], [r * 0.78, 0.9 * len], [r * 0.74, 0.93 * len]];
    body.lathe(prof.slice(0, 2), nSeg, [0.75, 0.76, 0.78, 1], E(PART.lip, 0.18, 1.0), S);
    body.lathe(prof.slice(1), nSeg, white, E(PART.nacelle, 0.3, 0), S);
    body.lathe([[r * 0.84, 0], [r * 0.82, 0.06 * len], [r * 0.8, 0.14 * len]], nSeg, [0.25, 0.26, 0.28, 1], E(PART.generic, 0.5, 0.6), S);
    body.lathe([[r * 0.8, 0.14 * len], [r * 0.25, 0.14 * len], [r * 0.22, 0.12 * len], [r * 0.12, 0.08 * len], [0.01, 0.06 * len]], nSeg, [0.12, 0.12, 0.13, 1], E(PART.fan, 0.35, 0.8), S);
    body.lathe([[r * 0.74, 0.93 * len], [r * 0.62, 1.05 * len], [r * 0.5, 1.12 * len]], nSeg, [0.35, 0.33, 0.3, 1], E(chevron ? PART.exhaust : PART.exhaust, 0.5, 0.7), S);
    body.lathe([[r * 0.5, 1.12 * len], [r * 0.38, 1.16 * len], [r * 0.2, 1.25 * len], [0.02, 1.3 * len]], nSeg, [0.28, 0.26, 0.24, 1], E(PART.exhaust, 0.55, 0.6), S);
  };
  for (const eg of T.eng) for (const sg of [1, -1]) {
    const zE = eg.z * sg; const wingLEatE = leX(eg.z); const xFront = wingLEatE + eg.fwd; const yE = wingY(eg.z) - eg.y;
    let M = m4.mul(m4.translate(xFront, yE, zE), m4.rotZ(Math.PI / 2));
    if (eg.flat) M = m4.mul(m4.translate(xFront, yE, zE), m4.mul(m4.scale(1, eg.flat, 1), m4.mul(m4.translate(0, 0, 0), m4.rotZ(Math.PI / 2))));
    nacelle(M, eg.r, eg.len, eg.flat, eg.chevron);
    // pylon
    const r = eg.r, len = eg.len; const pw = r * 0.2;
    const px0 = xFront - 0.25 * len, px1 = xFront - 1.05 * len; const yTop = wingY(eg.z) - 0.1, yBot = yE + r * 0.85 * (eg.flat || 1);
    const pts = [[px0, yBot], [px1, yBot + r * 0.1], [px1 + 0.3, yTop], [wingLEatE + 0.4, yTop + 0.15], [px0 + 0.8, yBot + (yTop - yBot) * 0.3]];
    for (let i = 0; i < pts.length; i++) { const a = pts[i], b = pts[(i + 1) % pts.length]; body.quad([a[0], a[1], zE - pw], [b[0], b[1], zE - pw], [b[0], b[1], zE + pw], [a[0], a[1], zE + pw], white, E(PART.pylon, 0.35, 0)); }
    body.quad([pts[0][0], pts[0][1], zE + pw], [pts[1][0], pts[1][1], zE + pw], [pts[2][0], pts[2][1], zE + pw], [pts[3][0], pts[3][1], zE + pw], white, E(PART.pylon, 0.35, 0));
    body.quad([pts[3][0], pts[3][1], zE - pw], [pts[2][0], pts[2][1], zE - pw], [pts[1][0], pts[1][1], zE - pw], [pts[0][0], pts[0][1], zE - pw], white, E(PART.pylon, 0.35, 0));
    engines.push({ front: [xFront, yE, zE], r, len });
  }
  if (T.rear) { // fuselage-mounted engines (CRJ)
    const e = T.rear;
    for (const sg of [1, -1]) {
      const xFront = X(e.x); const yE = Hc + e.y * R; const zE = sg * e.z;
      nacelle(m4.mul(m4.translate(xFront, yE, zE), m4.rotZ(Math.PI / 2)), e.r, e.len, false, false);
      // stub pylon to fuselage
      const px0 = xFront - e.len * 0.3, px1 = xFront - e.len * 0.8; const zin = sg * R * 0.6, zout = sg * (e.z - e.r * 0.8);
      const q = [[px0, yE - 0.18, zin], [px1, yE - 0.18, zin], [px1, yE - 0.18, zout], [px0, yE - 0.18, zout]];
      const q2 = q.map(p => [p[0], p[1] + 0.36, p[2]]);
      body.quad(q2[0], q2[1], q2[2], q2[3], white, E(PART.pylon, 0.35, 0)); body.quad(q[3], q[2], q[1], q[0], white, E(PART.pylon, 0.35, 0));
      body.quad(q[0], q2[0], q2[3], q[3], white, E(PART.pylon, 0.35, 0)); body.quad(q[2], q2[2], q2[1], q[1], white, E(PART.pylon, 0.35, 0));
      engines.push({ front: [xFront, yE, zE], r: e.r, len: e.len });
    }
  }
  // ---------- landing gear ----------
  const gearCol = [0.72, 0.73, 0.74, 1], tireCol = [0.06, 0.06, 0.065, 1], hubCol = [0.55, 0.56, 0.57, 1];
  const wheel = (g, cx, cy, cz, rw, ww) => {
    const M = m4.mul(m4.translate(cx, cy, cz + ww / 2), m4.rotX(Math.PI / 2));
    g.lathe([[rw * 0.55, 0], [rw * 0.93, -0.01], [rw, -ww * 0.2], [rw, -ww * 0.8], [rw * 0.93, -ww * 0.99], [rw * 0.55, -ww]], hi ? 24 : 10, tireCol, E(PART.tire, 0.85, 0), M);
    g.lathe([[rw * 0.55, -ww * 0.02], [rw * 0.3, -ww * 0.08], [0.01, -ww * 0.1]], 12, hubCol, E(PART.hub, 0.4, 0.8), M, false);
    g.lathe([[0.01, -ww * 0.9], [rw * 0.3, -ww * 0.92], [rw * 0.55, -ww * 0.98]], 12, hubCol, E(PART.hub, 0.4, 0.8), M, false);
  };
  const strut = (g, x, y0, y1, z, r) => g.cylinder(r, y1 - y0, 12, gearCol, E(PART.gear, 0.3, 0.9), m4.translate(x, y0, z));
  const rw = T.gear.r, ww = T.gear.w;
  parts.gear = [];
  for (const unit of T.gear.main) for (const sg of [1, -1]) {
    const g = new Geo(); const zg = sg * unit.z; const xg = X(unit.x);
    const isBody = unit.z < R * 0.9;
    const pivotY = isBody ? Hc - R * 0.75 : Math.min(wingY(unit.z) - 0.2, Hc - R * 0.2);
    const heavy = unit.wheels > 2;
    strut(g, xg, rw, pivotY, zg, heavy ? 0.26 : 0.14);
    if (unit.wheels === 2) { wheel(g, xg, rw, zg + 0.46, rw, ww); wheel(g, xg, rw, zg - 0.46, rw, ww); }
    else {
      const nAx = unit.wheels / 2; const sp = 1.45;
      g.box([xg - (nAx - 1) * sp / 2 - 0.3, rw - 0.12, zg - 0.12], [xg + (nAx - 1) * sp / 2 + 0.3, rw + 0.12, zg + 0.12], gearCol, E(PART.gear, 0.3, 0.9));
      for (let a = 0; a < nAx; a++) { const x = xg - (nAx - 1) * sp / 2 + a * sp; wheel(g, x, rw, zg + 0.68, rw, ww); wheel(g, x, rw, zg - 0.68, rw, ww); }
    }
    if (!isBody) g.box([xg - 0.9, rw + 0.9, zg + sg * 0.35], [xg + 0.9, pivotY - 0.2, zg + sg * 0.42], white, E(PART.generic, 0.3, 0));
    parts.gear.push(isBody ? { g, pivot: [xg, pivotY, zg], axis: [0, 0, 1], angle: -Math.PI / 2 * 0.95, kind: 'body' } : { g, pivot: [xg, pivotY, zg], axis: [1, 0, 0], angle: sg * Math.PI / 2 * 0.98, kind: 'main' });
  }
  {
    const g = new Geo(); const xg = X(T.gear.nose.x); const rn = T.gear.nose.r; const pivotY = Hc - R * 0.7;
    strut(g, xg, rn, pivotY, 0, rn > 0.45 ? 0.16 : 0.1);
    wheel(g, xg, rn, rn * 0.9, rn, rn * 0.7); wheel(g, xg, rn, -rn * 0.9, rn, rn * 0.7);
    parts.gear.push({ g, pivot: [xg, pivotY, 0], axis: [0, 0, 1], angle: Math.PI / 2 * 0.95, kind: 'nose' });
  }
  // lights (local positions)
  const tipY = wingY(semi) + (W.tipH || 0) * (W.tip === 'raked' ? 0.05 : 0.08);
  const tipZ = semi + (W.tip === 'raked' ? W.tipH * 0.9 : 0.4);
  const lights = {
    navL: [leX(tipZ) - 0.3, tipY, -tipZ - 0.2], navR: [leX(tipZ) - 0.3, tipY, tipZ + 0.2],
    strobeL: [leX(semi) - chordAt(semi) * 0.8, tipY, -tipZ - 0.1], strobeR: [leX(semi) - chordAt(semi) * 0.8, tipY, tipZ + 0.1],
    tail: [X(L) + 0.2, Hc + 0.6 * R, 0], beaconTop: [X(L * 0.45), Hc + fuselageSection(T, L * 0.45).yt + 0.1, 0], beaconBot: [X(L * 0.5), Hc - R * 1.1, 0],
    landL: [leX(R * 1.5) - 0.5, wingY(R * 1.5) - 0.2, -R * 1.5], landR: [leX(R * 1.5) - 0.5, wingY(R * 1.5) - 0.2, R * 1.5],
    taxi: [X(T.gear.nose.x), T.gear.nose.r + 1.4, 0],
  };
  return { type: typeName, T, body: body.data(), flaps: parts.flaps.map(f => ({ ...f, data: f.g.data() })), spoilers: parts.spoilers.map(s => ({ ...s, data: s.g.data() })), gear: parts.gear.map(gg => ({ ...gg, data: gg.g.data() })), engines, lights, dims: { L, R, Hc, xMain, span: W.span } };
}
