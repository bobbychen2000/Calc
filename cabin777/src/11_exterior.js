// ------------------------------------------------------------------
// Exterior seen through the windows: 777-300ER wings (64.8 m span incl. raked tips, 31.6 deg quarter-chord
// sweep) and GE90-115B nacelles (fan 3.25 m, nacelle max ~4 m, ~9.9 m from the centreline)
// Wing root leading edge placed ~7 m ahead of the overwing door 3 (door in Section 44 near the rear spar).
// ------------------------------------------------------------------
function naca(x, t) { return 5 * t * (0.2969 * Math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x * x * x - 0.1036 * x * x * x * x); }
const WING = { x0: 3.10, x1: 32.40, rootLE: 25.6, rootY: -1.30, leSweep: 34, kinkX: 10.8, teRoot: 38.4 };

function wingGeo(side) {
  const g = raw();
  const NS = 32, NC = 18;
  const { x0, x1 } = WING;
  const stations = [];
  for (let s = 0; s <= NS; s++) {
    const t = s / NS;
    const x = lerp(x0, x1, t);
    const span = x - x0, S = x1 - x0;
    let le = WING.rootLE + span * Math.tan(WING.leSweep * DEG);
    if (t > 0.9) le += Math.pow((t - 0.9) / 0.1, 2) * 1.6;               // raked tip
    // trailing edge: nearly straight inboard (yehudi), swept ~24 deg outboard of the kink
    const teK = WING.teRoot + (WING.kinkX - x0) * 0.12;
    let te = x < WING.kinkX ? WING.teRoot + (x - x0) * 0.12 : teK + (x - WING.kinkX) * Math.tan(24 * DEG);
    if (t > 0.9) te = lerp(te, le + 0.7, Math.pow((t - 0.9) / 0.1, 1.3));
    const chord = te - le;
    const th = lerp(0.14, 0.095, t);
    const y = WING.rootY + span * Math.tan(6 * DEG) + 1.3 * Math.pow(span / S, 2);
    stations.push({ x, le, chord, th, y });
  }
  const pts = [];
  for (let k = 0; k <= NC; k++) pts.push([Math.pow(k / NC, 1.7), 1]);
  for (let k = NC - 1; k >= 1; k--) pts.push([Math.pow(k / NC, 1.7), -1]);
  const NP = pts.length;
  for (const st of stations) {
    for (const [cx, sgn] of pts) {
      const camber = 0.018 * Math.sin(Math.PI * cx);
      const yy = (camber + sgn * naca(Math.max(cx, 1e-4), st.th) * (sgn < 0 ? 0.62 : 1)) * st.chord;
      g.p.push(st.x * side, st.y + yy, st.le + cx * st.chord); g.n.push(0, 1, 0); g.u.push(cx, st.x);
    }
  }
  for (let s = 0; s < NS; s++) for (let k = 0; k < NP; k++) {
    const a = s * NP + k, b = s * NP + ((k + 1) % NP), c = a + NP, d = b + NP;
    g.i.push(a, b, d, a, d, c);
  }
  computeNormals(g);
  const topIdx = Math.floor(NC / 2);
  if (g.n[topIdx * 3 + 1] < 0) { for (let k = 0; k < g.n.length; k++) g.n[k] = -g.n[k]; for (let t = 0; t < g.i.length; t += 3) { const tmp = g.i[t + 1]; g.i[t + 1] = g.i[t + 2]; g.i[t + 2] = tmp; } }
  return { g, stations };
}

function nacelleGeo() {
  // lathe along -y then rotated to +z; ~7.9 m long, max radius ~1.98 m, inlet lip radius ~1.78 m
  const outer = [[1.74, 0.0], [1.86, 0.14], [1.95, 0.6], [1.98, 1.6], [1.93, 3.4], [1.74, 5.0], [1.46, 5.9], [1.30, 6.2]];
  const core = [[1.18, 6.15], [1.05, 6.8], [0.86, 7.4], [0.58, 7.9]];
  const inlet = [[1.74, 0.0], [1.66, 0.3], [1.63, 0.95]];
  return { outer: gLathe(outer.map(([r, y]) => [r, -y]), 40), core: gLathe(core.map(([r, y]) => [r, -y]), 30), inlet: gLathe(inlet.map(([r, y]) => [r, -y]), 40) };
}

function buildExterior(gl) {
  const B = new Builder();
  const paint = { c: '#c9ced4', r: 0.42, m: 0.15 };
  const paintDark = { c: '#a0a7af', r: 0.38, m: 0.4 };
  const cowl = { c: '#dde0e4', r: 0.35, m: 0.1 };
  const fanDark = { c: '#1a1d22', r: 0.5, m: 0.5 };
  const lights = [];
  for (const side of [-1, 1]) {
    const { g, stations } = wingGeo(side);
    B.add(g, null, paint);
    const tip = stations[stations.length - 1];
    B.add(gSphere(0.12, 8, 6), M4.trs(tip.x * side, tip.y, tip.le + tip.chord * 0.4), paint);
    // flap track fairings (canoes) under the trailing edge
    for (const fx of [7.4, 14.6, 19.8, 24.6]) {
      const st = stations.reduce((a, b) => (Math.abs(b.x - fx) < Math.abs(a.x - fx) ? b : a));
      const len = Math.max(2.6, st.chord * 0.62);
      const zc = st.le + st.chord * 0.66 + len * 0.45;
      const secs = [];
      const N = 10;
      for (let k = 0; k <= N; k++) {
        const t = k / N;
        const r = (t < 0.25 ? Math.sin((t / 0.25) * Math.PI / 2) : Math.pow(Math.cos(((t - 0.25) / 0.75) * Math.PI / 2), 0.7)) * 0.24 + 0.012;
        secs.push({ y: -len / 2 + t * len, x: 0, z: 0, w: r * 1.3, d: r * 1.9, r: r * 0.62 });
      }
      B.add(gLoft(secs, 3), M4.mul(M4.trs(fx * side, st.y - 0.18, zc), M4.trs(0, 0, 0, 0, -Math.PI / 2)), paintDark);
    }
    // panel lines: slat line, hinge line, flap / aileron breaks
    const top = (st, cx) => { const camber = 0.018 * Math.sin(Math.PI * cx); return [st.x * side, st.y + (camber + naca(Math.max(cx, 1e-4), st.th)) * st.chord + 0.004, st.le + cx * st.chord]; };
    const line = { c: '#8f969e', r: 0.5 };
    const spanLine = (cx, i0, i1) => {
      const g2 = raw();
      for (let i = i0; i <= i1; i++) { const p = top(stations[i], cx), q = top(stations[i], cx + 0.012); g2.p.push(...p, ...q); g2.n.push(0, 1, 0, 0, 1, 0); g2.u.push(0, 0, 1, 0); }
      for (let i = 0; i < i1 - i0; i++) { const q = i * 2; g2.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
      B.add(fixWinding(g2), null, line);
    };
    spanLine(0.12, 3, 29);
    spanLine(0.72, 2, 27);
    for (const fx of [WING.kinkX, 14.6, 19.8, 24.6, 28.2]) {
      const i = stations.reduce((bi, b, k) => (Math.abs(b.x - fx) < Math.abs(stations[bi].x - fx) ? k : bi), 0);
      const g3 = raw();
      for (let k = 0; k <= 8; k++) { const cx = 0.72 + (0.28 * k) / 8; const p = top(stations[i], cx); g3.p.push(p[0] - 0.02 * side, p[1], p[2], p[0] + 0.02 * side, p[1], p[2]); g3.n.push(0, 1, 0, 0, 1, 0); g3.u.push(0, 0, 1, 0); }
      for (let k = 0; k < 8; k++) { const q = k * 2; g3.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
      B.add(fixWinding(g3), null, line);
    }
    // GE90-115B nacelle + pylon
    const est = stations.reduce((a, b) => (Math.abs(b.x - 9.9) < Math.abs(a.x - 9.9) ? b : a));
    const ex = 9.9 * side, ey = est.y - 2.45, ez = est.le - 4.2;
    const nac = nacelleGeo();
    const rot = M4.trs(ex, ey, ez, 0, -Math.PI / 2);
    B.add(nac.outer, rot, cowl);
    B.add(nac.inlet, rot, paintDark);
    B.add(nac.core, rot, paintDark);
    B.add(gCyl(1.62, 1.62, 0.02, 40), M4.mul(rot, M4.trs(0, -0.95, 0)), fanDark);
    B.add(gCyl(0.02, 0.42, 0.55, 16), M4.mul(rot, M4.trs(0, -0.68, 0)), { c: '#e6e8ea', r: 0.3, m: 0.7 });
    B.add(gRBox(0.55, 1.7, 7.4, 0.24, 2), M4.trs(ex, est.y - 0.75, est.le + 0.6, 0, -5 * DEG), paint);
    lights.push({ p: [tip.x * side, tip.y + 0.05, tip.le + tip.chord * 0.35], c: side < 0 ? [2.5, 0.12, 0.08] : [0.1, 2.2, 0.35], s: 0.9, blink: 0 });
    lights.push({ p: [tip.x * side, tip.y + 0.08, tip.le + tip.chord * 0.7], c: [4, 4, 4], s: 2.2, blink: side < 0 ? 2.0 : 2.5 });
  }
  // wing-to-body fairing below the cabin between the wing roots
  B.add(gRBox(6.2, 1.6, 17.0, 0.7, 3), M4.trs(0, -2.25, 32.0), paint);
  const geo = B.build();
  return { mesh: gl ? gl.mesh(geo, { name: 'exterior', layer: 'exterior', castShadow: false }) : null, lights, geo };
}
