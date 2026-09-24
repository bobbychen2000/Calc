// ------------------------------------------------------------------
// Cabin shell (777-300ER): floor, near-vertical sidewalls with 10 x 15 in window reveals,
// Type A door surrounds, window shades (electric two-stage in First/Business, manual pull-down in PY/Y)
// ------------------------------------------------------------------
const MAT = {
  sidewall: { c: '#e9e7e2', r: 0.52, l: LAYER.plastic },
  dado: { c: '#b4b6b8', r: 0.55, l: LAYER.plastic },
  grille: { c: '#8a8e93', r: 0.6, l: LAYER.grille },
  ceiling: { c: '#f1f0ec', r: 0.75, l: LAYER.plastic },
  bin: { c: '#e6e4df', r: 0.42, l: LAYER.plastic },
  binDoor: { c: '#eeede9', r: 0.34, l: LAYER.plastic },
  binLip: { c: '#c6c8cb', r: 0.4 },
  latch: { c: '#6a7078', r: 0.35, m: 0.4 },
  led: { c: '#ffffff', r: 0.5, l: 12, e: 1.0 },
  reveal: { c: '#e4e2dc', r: 0.45, l: LAYER.plastic },
  carpet: { c: '#3b3f4a', r: 0.95, l: LAYER.carpet },
  carpetJ: { c: '#3d3a3b', r: 0.95, l: LAYER.carpet },
  vinyl: { c: '#8d9096', r: 0.55, l: LAYER.vinyl },
  pathStrip: { c: '#d9dcc4', r: 0.6, e: 0.02 },
  door: { c: '#dddbd5', r: 0.45, l: LAYER.plastic },
  doorGap: { c: '#2a2d31', r: 0.8 },
  handle: { c: '#b8bcc1', r: 0.3, m: 0.85 },
  handleRed: { c: '#b3262a', r: 0.4 },
  slide: { c: '#d3d0c9', r: 0.5, l: LAYER.plastic },
  darkPlastic: { c: '#24282d', r: 0.4 },
  psu: { c: '#dcdad5', r: 0.45, l: LAYER.plastic },
  lens: { c: '#fff4dc', r: 0.2 },
  nozzle: { c: '#b9bdc2', r: 0.3, m: 0.6 },
  exitGlow: { c: '#ffffff', r: 0.5, l: LAYER.atlasGlow, e: 0.8 },
  decal: { c: '#ffffff', r: 0.6, l: LAYER.atlasLit },
  wallEnd: { c: '#e4e2dc', r: 0.5, l: LAYER.plastic },
  shade: { c: '#dcd9d2', r: 0.55, l: LAYER.plastic },
  shadeRail: { c: '#bdbab3', r: 0.45 },
  sheer: { c: '#f3f0e8', r: 0.9, l: LAYER.fabric, e: 0.32 },
  blackout: { c: '#44474d', r: 0.85, l: LAYER.fabric },
  shadeBtn: { c: '#9a9ea4', r: 0.35 },
};

const circX = (y) => Math.sqrt(Math.max(0, CAB.R * CAB.R - (y - CAB.yc) * (y - CAB.yc)));
// Sidewall profile: v (height) -> [x, y, nx, ny] for the RIGHT side (inward normal)
const DADO = [[2.70, 0], [2.725, 0.10], [2.785, 0.25], [2.846, 0.34], [circX(0.40), 0.40]];
function wallAt(v) {
  if (v <= 0.40) {
    for (let k = 0; k < DADO.length - 1; k++) {
      const a = DADO[k], b = DADO[k + 1];
      if (v <= b[1] + 1e-9) {
        const t = (v - a[1]) / (b[1] - a[1]);
        const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy);
        return [lerp(a[0], b[0], t), v, -dy / l, dx / l];
      }
    }
  }
  const x = circX(v);
  return [x, v, -x / CAB.R, -(v - CAB.yc) / CAB.R];
}
// rounded-rect signed distance (centered)
function sdRRect(px, py, hw, hh, r) {
  const qx = Math.abs(px) - (hw - r), qy = Math.abs(py) - (hh - r);
  return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
}
// point on rounded-rect boundary along direction angle th
function rrectRay(th, hw, hh, r) {
  const dx = Math.cos(th), dy = Math.sin(th);
  let lo = 0, hi = Math.hypot(hw, hh) * 1.2;
  for (let i = 0; i < 28; i++) { const m = (lo + hi) / 2; if (sdRRect(dx * m, dy * m, hw, hh, r) < 0) lo = m; else hi = m; }
  return [dx * lo, dy * lo];
}

// Window cell band (the part of the wall that carries the window hole) and the sidewall top (bins start)
const WALL = { vb0: 0.84, vb1: 1.40, vTop: 1.60, bottomRows: [0, 0.10, 0.25, 0.34, 0.40, 0.62, 0.84] };
const HOLE_R = 0.105;
function windowCellPattern(cellW, holeW, holeH, holeR, vc) {
  const hw = cellW / 2, hh0 = vc - WALL.vb0, hh1 = WALL.vb1 - vc;
  const cornerAng = [Math.atan2(hh1, hw), Math.PI - Math.atan2(hh1, hw), Math.PI + Math.atan2(hh0, hw), 2 * Math.PI - Math.atan2(hh0, hw)];
  const base = [];
  const N = 44;
  for (let i = 0; i < N; i++) base.push((i / N) * Math.PI * 2);
  const angs = [...new Set([...base, ...cornerAng].map((a) => +a.toFixed(6)))].sort((a, b) => a - b);
  const ring = angs.map((th) => {
    const h = rrectRay(th, holeW / 2, holeH / 2, holeR);
    const dx = Math.cos(th), dy = Math.sin(th);
    const hy = dy >= 0 ? hh1 : hh0;
    const t = 1 / Math.max(Math.abs(dx) / hw, Math.abs(dy) / hy);
    let o = [dx * t, dy * t];
    if (Math.abs(Math.abs(o[0]) - hw) < 1e-7) o[0] = Math.sign(o[0]) * hw;
    return { th, h, o };
  });
  const sideV = ring.filter((p) => Math.abs(p.o[0] - hw) < 1e-6).map((p) => p.o[1]).sort((a, b) => a - b);
  const botZ = ring.filter((p) => Math.abs(p.o[1] + hh0) < 1e-6).map((p) => p.o[0]).sort((a, b) => a - b);
  const topZ = ring.filter((p) => Math.abs(p.o[1] - hh1) < 1e-6).map((p) => p.o[0]).sort((a, b) => a - b);
  return { ring, sideV, botZ, topZ, hw, vc };
}

function wallGrid(g, side, zs, vs) {
  const b = g.p.length / 3;
  for (const v of vs) {
    const [x, y, nx, ny] = wallAt(v);
    for (const z of zs) { g.p.push(x * side, y, z); g.n.push(nx * side, ny, 0); g.u.push(z, v); }
  }
  const nz = zs.length;
  for (let j = 0; j < vs.length - 1; j++) for (let i = 0; i < nz - 1; i++) {
    const a = b + j * nz + i, c = a + nz;
    g.i.push(a, a + 1, c + 1, a, c + 1, c);
  }
}

function buildSidewallRun(g, side, za, zb, holesZ, pat, vTop) {
  const hw = pat.hw;
  const topRows = [WALL.vb1, 1.50, vTop];
  const allV = [...WALL.bottomRows.slice(0, -1), ...pat.sideV.map((v) => v + pat.vc), ...topRows.slice(1)];
  const vset = [...new Set(allV.map((v) => +v.toFixed(5)))].sort((a, b) => a - b);
  const hs = holesZ.filter((z) => z - hw >= za - 1e-6 && z + hw <= zb + 1e-6).sort((a, b) => a - b);
  let cur = za;
  const filler = (z0, z1) => {
    if (z1 - z0 < 1e-4) return;
    const n = Math.max(1, Math.ceil((z1 - z0) / 0.55));
    const zs = []; for (let k = 0; k <= n; k++) zs.push(z0 + ((z1 - z0) * k) / n);
    wallGrid(g, side, zs, vset);
  };
  for (const hz of hs) {
    filler(cur, hz - hw);
    windowCell(g, side, hz, pat, topRows);
    cur = hz + hw;
  }
  filler(cur, zb);
}

function windowCell(g, side, zc, pat, topRows) {
  wallGrid(g, side, pat.botZ.map((z) => zc + z), WALL.bottomRows);
  wallGrid(g, side, pat.topZ.map((z) => zc + z), topRows);
  const R = pat.ring, n = R.length;
  const rings = [0, 0.35, 1].map((t) => R.map((p) => [lerp(p.h[0], p.o[0], t), lerp(p.h[1], p.o[1], t)]));
  const b = g.p.length / 3;
  for (const ring of rings) for (const [dz, dv] of ring) {
    const v = pat.vc + dv;
    const [x, y, nx, ny] = wallAt(v);
    g.p.push(x * side, y, zc + dz); g.n.push(nx * side, ny, 0); g.u.push(zc + dz, v);
  }
  for (let r = 0; r < 2; r++) for (let i = 0; i < n; i++) {
    const a = b + r * n + i, a2 = b + r * n + ((i + 1) % n), c = a + n, c2 = a2 + n;
    g.i.push(a, a2, c2, a, c2, c);
  }
}

// Local frame at the window centre: X along the cabin (+z on the right, -z on the left), Y up the wall tangent,
// Z = inward normal (toward the cabin); origin pushed out by `depth` into the reveal.
function windowFrame(side, depth = 0) {
  const W = CAB.win;
  const [x, y, nx, ny] = wallAt(W.yc);
  const N = [nx * side, ny, 0];
  const Y = side > 0 ? [ny, -nx, 0] : [-ny, -nx, 0];
  const X = [0, 0, side];
  const o = [x * side - N[0] * depth, y - N[1] * depth, 0];
  return [X[0], X[1], X[2], 0, Y[0], Y[1], Y[2], 0, N[0], N[1], N[2], 0, o[0], o[1], o[2], 1];
}

// Window reveal (tunnel) + glass in the cabin frame (window centre at z = 0) for a side
function windowParts(side) {
  const W = CAB.win;
  const depth = 0.10;
  const vc = W.yc;
  const N = 40;
  const angs = []; for (let i = 0; i < N; i++) angs.push((i / N) * Math.PI * 2);
  const hole = angs.map((th) => rrectRay(th, W.holeW / 2, W.holeH / 2, HOLE_R));
  const glass = angs.map((th) => rrectRay(th, W.w / 2, W.h / 2, 0.09));
  const [cx, cy, cnx, cny] = wallAt(vc);
  const out = [-cnx, -cny];
  const map = (dz, dv, d) => { const [x, y] = wallAt(vc + dv); return [(x + out[0] * d) * side, y + out[1] * d, dz]; };
  const rv = raw();
  const rings = [
    hole.map(([a, b]) => map(a, b, -0.004)),
    hole.map(([a, b]) => map(a * 0.985, b * 0.99, 0.02)),
    glass.map(([a, b]) => map(a * 1.05, b * 1.035, depth * 0.72)),
    glass.map(([a, b]) => map(a, b, depth)),
  ];
  for (const ring of rings) for (const p of ring) { rv.p.push(...p); rv.u.push(0, 0); }
  for (let r = 0; r < rings.length; r++) for (let i = 0; i < N; i++) {
    const p = rings[r][i];
    const ax = [(cx + out[0] * 0.05) * side, cy + out[1] * 0.05, 0];
    let n = V3.norm(V3.sub(ax, p));
    n = V3.norm(V3.add(n, V3.scale([cnx * side, cny, 0], r === 0 ? 1.2 : 0.25)));
    rv.n.push(...n);
  }
  for (let r = 0; r < rings.length - 1; r++) for (let i = 0; i < N; i++) {
    const a = r * N + i, b = r * N + ((i + 1) % N), c = a + N, d = b + N;
    rv.i.push(a, b, d, a, d, c);
  }
  fixWinding(rv);
  const gl_ = raw();
  const c0 = map(0, 0, depth);
  gl_.p.push(...c0); gl_.n.push(cnx * side, cny, 0); gl_.u.push(0.5, 0.5);
  for (const [a, b] of glass) { gl_.p.push(...map(a, b, depth)); gl_.n.push(cnx * side, cny, 0); gl_.u.push(0, 0); }
  for (let i = 0; i < N; i++) gl_.i.push(0, 1 + i, 1 + ((i + 1) % N));
  fixWinding(gl_);
  return { reveal: rv, glass: gl_ };
}

// Shade geometry in the window-local frame: unit panel spanning y in [-H/2, H/2]; scaled per instance by the
// closed fraction (anchored at the top). Accordion pleats for the electric shades.
const SHADE = { w: 0.292, h: 0.428, depth: 0.028 };
function shadePanelGeo(kind) {
  const B = new Builder();
  const { w, h } = SHADE;
  if (kind === 'manual') {
    B.add(gBox(w, h, 0.004), null, MAT.shade);
  } else {
    // accordion: 14 pleats (zig-zag in depth), compresses naturally when the panel is scaled in y
    const g = raw(), n = 28;
    for (let k = 0; k <= n; k++) {
      const y = -h / 2 + (h * k) / n, zz = (k % 2) * 0.006;
      g.p.push(-w / 2, y, zz, w / 2, y, zz); g.n.push(0, 0, 1, 0, 0, 1); g.u.push(0, k / n, 1, k / n);
    }
    for (let k = 0; k < n; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
    computeNormals(g);
    let dot = 0; for (let v = 2; v < g.n.length; v += 3) dot += g.n[v];
    if (dot < 0) { for (let v = 0; v < g.n.length; v++) g.n[v] = -g.n[v]; for (let t = 0; t < g.i.length; t += 3) { const tmp = g.i[t + 1]; g.i[t + 1] = g.i[t + 2]; g.i[t + 2] = tmp; } }
    B.add(g, null, kind === 'sheer' ? MAT.sheer : MAT.blackout);
  }
  return B.build();
}
function shadeRailGeo(kind) {
  const B = new Builder();
  if (kind === 'manual') {
    B.add(gRBox(SHADE.w, 0.022, 0.012, 0.005, 1), M4.trs(0, 0, 0.004), MAT.shadeRail);
    B.add(gRBox(0.07, 0.012, 0.012, 0.004, 1), M4.trs(0, -0.009, 0.012), MAT.shadeRail);  // finger lip
  } else B.add(gRBox(SHADE.w, 0.012, 0.01, 0.004, 1), M4.trs(0, 0, 0.004), kind === 'sheer' ? { c: '#d9d6cf', r: 0.4 } : { c: '#303338', r: 0.4 });
  return B.build();
}
// instance transforms for a window's shade state (f = closed fraction 0..1)
function shadeMats(w, f, depthOff = 0) {
  const F = windowFrame(w.side, SHADE.depth + depthOff);
  const Tz = M4.trs(0, 0, w.z);
  const H = SHADE.h, top = H / 2 + 0.004;
  const fc = Math.max(f, 0.0001);
  const panel = M4.mul(Tz, M4.mul(F, M4.mul(M4.trs(0, top - (fc * H) / 2 - 0.004, 0), M4.trs(0, 0, 0, 0, 0, 0, 1, fc, 1))));
  const rail = M4.mul(Tz, M4.mul(F, M4.trs(0, top - fc * H - 0.004, 0)));
  return { panel, rail };
}

// ---------------- Ceiling / bin profiles (x >= 0 half) ----------------
// Outboard pivot bin: bottom (PSU face) rises from the sidewall to the aisle lip; outward-curving door
const SIDEBIN = [[2.845, 1.60], [1.53, 1.795], [1.492, 1.83], [1.468, 1.93], [1.472, 2.03], [1.50, 2.115], [1.555, 2.18], [1.64, 2.225], [1.80, 2.248], [2.30, 2.255], [2.60, 2.13], [2.72, 1.96], [2.80, 1.76]];
// Centre bin (double-sided, 162 cm across, 55 cm tall incl. structure)
const CBIN = [[0.795, 1.845], [0.818, 1.88], [0.832, 1.99], [0.822, 2.10], [0.788, 2.19], [0.725, 2.262], [0.62, 2.30], [0, 2.315]];
function domeProfile() {
  const pts = [];
  const y0 = 2.02, x0 = circX(y0);
  for (let k = 0; k <= 16; k++) {
    const t = k / 16;
    pts.push([x0 * Math.cos((t * Math.PI) / 2), y0 + 0.50 * Math.sin((t * Math.PI) / 2)]);
  }
  return pts;
}
const DOME = domeProfile();
const MONOC = [[circX(2.0), 2.0], [2.62, 2.12], [2.40, 2.19], [1.8, 2.225], [0, 2.235]];

// outline (upper boundary) of a zone's ceiling cross-section as y(|x|)
function ceilOutline(type, x) {
  x = Math.abs(x);
  const interp = (pts) => {
    const s = [...pts].sort((a, b) => a[0] - b[0]);
    if (x <= s[0][0]) return s[0][1];
    for (let k = 0; k < s.length - 1; k++) if (x <= s[k + 1][0]) return lerp(s[k][1], s[k + 1][1], (x - s[k][0]) / (s[k + 1][0] - s[k][0]));
    return s[s.length - 1][1];
  };
  if (type === 'door') return x > DOME[0][0] ? 2.02 : interp(DOME);
  if (type === 'mono') return interp(MONOC);
  if (x <= 0.725) return 2.30;
  if (x <= 1.66) return interp(VAULT);
  return interp(SIDEBIN.slice(7, 11));
}

const AISLE_STRIPS = { F: [1.14, 1.58], J: [1.21, 1.65], PY: [1.18, 1.70], Y: [1.03, 1.38] };

function buildShell(gl, layout) {
  const zones = layout.zones;
  const shell = new Builder();
  const upper = new Builder();
  const W = CAB.win;
  const pat = windowCellPattern(W.pitch, W.holeW, W.holeH, HOLE_R, W.yc);

  // ---- floor ----
  for (const zn of zones) {
    const carpet = zn.type === 'seat';
    const f = gBox(CAB.floorHalf * 2, 0.02, zn.z1 - zn.z0);
    shell.add(f, M4.trs(0, -0.01, (zn.z0 + zn.z1) / 2), carpet ? (zn.cls === 'F' || zn.cls === 'J' ? MAT.carpetJ : MAT.carpet) : MAT.vinyl);
  }
  // ---- sidewalls (continuous through seat + monument zones; door zones get their own surround) ----
  const runs = [];
  for (const zn of zones) {
    if (zn.type === 'door') continue;
    const last = runs[runs.length - 1];
    if (last && Math.abs(last[1] - zn.z0) < 1e-6) last[1] = zn.z1; else runs.push([zn.z0, zn.z1]);
  }
  for (const side of [-1, 1]) {
    const hz = layout.windows.filter((w) => w.side === side).map((w) => w.z);
    for (const [za, zb] of runs) {
      const g = raw();
      buildSidewallRun(g, side, za, zb, hz, pat, WALL.vTop);
      fixWinding(g);
      shell.add(g, null, MAT.sidewall);
    }
  }
  // dado air-return grille band in seat zones
  for (const zn of zones) {
    if (zn.type !== 'seat') continue;
    for (const side of [-1, 1]) {
      const prof = [[2.728, 0.11], [2.776, 0.23]].map(([x, y]) => [x - 0.004, y]);
      shell.add(gSweep(prof.map(([x, y]) => [x * side, y]), zn.z0 + 0.05, zn.z1 - 0.05, { side: side > 0 ? 1 : -1 }), null, MAT.grille);
    }
  }
  // upper sidewall above the bin line where there are no bins (monument + door zones)
  for (const zn of zones) {
    if (zn.type === 'seat') continue;
    for (const side of [-1, 1]) {
      const prof = [];
      const y1 = zn.type === 'door' ? 2.02 : 2.0;
      for (let k = 0; k <= 5; k++) { const y = lerp(WALL.vTop - 0.01, y1, k / 5); prof.push([(circX(y) + 0.002) * side, y]); }
      shell.add(gSweep(prof, zn.z0, zn.z1, { side: side > 0 ? 1 : -1 }), null, MAT.sidewall);
    }
  }

  // ---- door surrounds (door-leaf lining with a small window at the cabin window height) ----
  for (let di = 0; di < CAB.doors.length; di++) {
    const zn = zones.find((z) => z.type === 'door' && z.door === di);
    for (const side of [-1, 1]) {
      const g = raw();
      const c = CAB.doors[di];
      const cellW = 1.14;
      const dp = windowCellPattern(cellW, W.holeW * 0.92, W.holeH * 0.92, HOLE_R, W.yc);
      const topRows = [WALL.vb1, 1.60, 1.80, 2.02];
      windowCell(g, side, c, dp, topRows);
      const vset = [...new Set([...WALL.bottomRows.slice(0, -1), ...dp.sideV.map((v) => v + dp.vc), ...topRows.slice(1)].map((v) => +v.toFixed(5)))].sort((a, b) => a - b);
      if (c - cellW / 2 - zn.z0 > 1e-3) wallGrid(g, side, [zn.z0, c - cellW / 2], vset);
      if (zn.z1 - (c + cellW / 2) > 1e-3) wallGrid(g, side, [c + cellW / 2, zn.z1], vset);
      fixWinding(g);
      shell.add(g, null, MAT.door);
    }
  }

  buildCeilings(upper, layout);
  // ---- headers between zones of different ceiling outline ----
  for (let k = 0; k < zones.length - 1; k++) {
    const a = zones[k], b = zones[k + 1], z = a.z1;
    if (a.type === b.type) continue;
    const g = raw();
    const N = 64;
    const xs = []; for (let i = 0; i <= N; i++) xs.push(-2.80 + (5.60 * i) / N);
    const base = g.p.length / 3;
    for (const x of xs) {
      const ya = ceilOutline(a.type, x), yb = ceilOutline(b.type, x);
      const lo = Math.min(ya, yb) - 0.005, hi = Math.max(ya, yb) + 0.005;
      g.p.push(x, lo, z, x, hi, z); g.n.push(0, 0, 1, 0, 0, 1); g.u.push(x, lo, x, hi);
    }
    for (let i = 0; i < N; i++) { const q = base + i * 2; g.i.push(q, q + 2, q + 3, q, q + 3, q + 1); }
    fixWinding(g);
    upper.add(g, null, MAT.wallEnd);
    const g2 = { p: g.p.slice(), n: g.n.map((v, i) => (i % 3 === 2 ? -v : v)), u: g.u.slice(), i: [] };
    for (let t = 0; t < g.i.length; t += 3) g2.i.push(g.i[t], g.i[t + 2], g.i[t + 1]);
    upper.add(g2, null, MAT.wallEnd);
  }
  // ---- front and aft end walls ----
  for (const [z, f] of [[CAB.zFront - 0.02, -1], [CAB.zAft + 0.02, 1]]) {
    const pts = [];
    for (let k = 0; k <= 24; k++) { const v = lerp(0, 2.0, k / 24); const [x] = wallAt(v); pts.push([x, v]); }
    for (const [x, y] of MONOC.slice(1, -1)) pts.push([x, y]);
    const full = [...pts, [0, 2.24], ...pts.slice().reverse().map(([x, y]) => [-x, y])];
    shell.add(gExtrude(full, 0.04, 5), M4.trs(0, 0, z + f * 0.02), MAT.wallEnd);
  }
  // ---- floor path strips along aisles ----
  for (const zn of zones) {
    if (zn.type !== 'seat') continue;
    const xs = AISLE_STRIPS[zn.cls] || AISLE_STRIPS.Y;
    for (const side of [-1, 1]) for (const x of xs) {
      shell.add(gBox(0.018, 0.004, zn.z1 - zn.z0 - 0.1), M4.trs(x * side, 0.002, (zn.z0 + zn.z1) / 2), MAT.pathStrip);
    }
  }

  const meshes = {
    shell: gl.mesh(shell.build(), { name: 'shell', layer: 'shell' }),
    upper: gl.mesh(upper.build(), { name: 'upper', layer: 'upper' }),
  };

  // ---- window reveals + glass (instanced per side), shades (instanced per kind) ----
  const inst = { R: [], L: [] };
  layout.windows.forEach((w, i) => { (w.side > 0 ? inst.R : inst.L).push({ w, i }); });
  const winParts = {};
  for (const [key, side] of [['R', 1], ['L', -1]]) {
    const wp = windowParts(side);
    winParts[key] = wp;
    const mats = inst[key].map(({ w }) => M4.trs(0, 0, w.z));
    const rb = new Builder(); rb.add(wp.reveal, null, MAT.reveal);
    meshes['reveal' + key] = gl.mesh(rb.build(), { name: 'reveal' + key, instances: mats });
    const gb = new Builder(); gb.add(wp.glass, null, { c: '#ffffff' });
    meshes['glass' + key] = gl.mesh(gb.build(), { name: 'glass' + key, instances: mats, tints: mats.map(() => [0.93, 0.95, 0.96, 0]), castShadow: false });
  }
  // shade meshes: manual (PY/Y), electric sheer + blackout (F/J)
  const shadeInst = { manual: [], sheer: [], blackout: [] };
  layout.windows.forEach((w, i) => {
    if (w.electric) { shadeInst.sheer.push(i); shadeInst.blackout.push(i); } else shadeInst.manual.push(i);
  });
  const shades = {};
  for (const kind of ['manual', 'sheer', 'blackout']) {
    const list = shadeInst[kind];
    const pm = list.map((i) => shadeMats(layout.windows[i], 0, kind === 'blackout' ? -0.012 : 0).panel);
    const rm = list.map((i) => shadeMats(layout.windows[i], 0, kind === 'blackout' ? -0.012 : 0).rail);
    const cast = kind !== 'sheer';
    meshes['shade_' + kind] = gl.mesh(shadePanelGeo(kind), { name: 'shade_' + kind, instances: pm, castShadow: cast });
    meshes['shadeRail_' + kind] = gl.mesh(shadeRailGeo(kind), { name: 'shadeRail_' + kind, instances: rm, castShadow: false });
    shades[kind] = { list, panel: meshes['shade_' + kind], rail: meshes['shadeRail_' + kind] };
  }
  // shade buttons under the electric windows (two buttons: sheer / blackout)
  const btn = new Builder();
  for (const w of layout.windows) {
    if (!w.electric) continue;
    const F = M4.mul(M4.trs(0, 0, w.z), windowFrame(w.side, -0.004));
    const P = M4.mul(F, M4.trs(0, -W.holeH / 2 - 0.05, 0));
    btn.add(gRBox(0.06, 0.028, 0.008, 0.004, 1), P, { c: '#cfccc5', r: 0.4 });
    for (const dx of [-0.014, 0.014]) btn.add(gRBox(0.02, 0.014, 0.006, 0.003, 1), M4.mul(P, M4.trs(dx, 0, 0.004)), MAT.shadeBtn);
  }
  meshes.shadeBtns = gl.mesh(btn.build(), { name: 'shadeBtns', castShadow: false });
  return { meshes, inst, winParts, shades };
}
