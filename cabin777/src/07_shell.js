// ------------------------------------------------------------------
// Cabin shell (777-300ER): floor, near-vertical sidewalls with tall 777 window recesses (10 x 15 in pane), dark dado
// with air-return grilles, Type A door surrounds, window shades (electric pleated sheer + blackout in F/J, manual in PY/Y)
// ------------------------------------------------------------------
const MAT = {
  // QA r1: sidewall / reveal / lining / end walls carry no detail layer: the plastic bump layer read as stucco under
  // grazing window light; real panels and reveals are smooth satin [V: ref/web/windows tt_window, omaat_24, lalf_37, f_17313]
  sidewall: { c: '#e9e7e2', r: 0.52 },
  // bluer slate dado. QA r2: the floor-level AO / bounce falloff crushed #464d5c to #1e222d in the cabin (photo slate
  // #374157 / #363f4c, dado:wall ~0.33 on py_37301 / py_37303), so the albedo is raised to land there in-cabin [V: tone]
  dado: { c: '#6c7690', r: 0.6, l: LAYER.plastic },
  // louvre slats about dado-toned over a dark plenum, so the grille averages #394156 like the photo (slats light,
  // gaps dark; py_37301 grille #394156, dado beside it #30394e) [V]
  grille: { c: '#707b96', r: 0.55 },
  ceiling: { c: '#f1f0ec', r: 0.75, l: LAYER.plastic },
  bin: { c: '#e6e4df', r: 0.42, l: LAYER.plastic },
  binDoor: { c: '#eeede9', r: 0.34, l: LAYER.plastic },
  binLip: { c: '#c6c8cb', r: 0.4 },
  latch: { c: '#6a7078', r: 0.35, m: 0.4 },
  led: { c: '#ffffff', r: 0.5, l: 12, e: 1.0 },
  reveal: { c: '#e7e4dd', r: 0.45 },
  // Y/PY: dark navy with cyan flecks (photo swatch y_47304); F/J: dark warm charcoal-brown (c_27313, f_17300)
  // QA r2: #2c3345 rendered #232a41 (Y) / #181c2a (PY) against photo #36445f (y_47301) / #282f41-#354156 (py_37302)
  carpet: { c: '#3d4659', r: 0.95, l: LAYER.yCarpet },  // swatch layer adds the blue; kept greyer [V: tone]
  // F/J: plain fine heather, no motif [V: c_27312 aisle sampled #403638 / #3e3537, #463d3b further aft, f_17313
  // footwell #312825]; QA r2: #3a3033 rendered plum #1a1517 in the aisle between the tall shells, so warmer
  // brown-grey, raised until the q06 aisle renders near the photo; the fine fabric layer
  // stands in for the heather (no J carpet swatch is mapped) [A: grain]
  carpetJ: { c: '#645554', r: 0.95, l: LAYER.fabric },
  vinyl: { c: '#8d9096', r: 0.55, l: LAYER.vinyl },
  // QA r2: no aisle path strips are visible in any ANA photo (y_47301, y_47304, py_37301/02, c_27312), so none are
  // modelled; Y instead shows glossy royal-blue seat-track covers along each seat-leg line [V: y_47304 #2965bd, y_47301]
  trackCover: { c: '#2965bd', r: 0.35 },
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
  wallEnd: { c: '#e4e2dc', r: 0.5 },
  shade: { c: '#e2e0da', r: 0.5, l: LAYER.plastic },           // manual PY/Y shade [A: colour]
  shadeRail: { c: '#c4c2bc', r: 0.4 },                          // its finger grip (grey lip, py_37301 / y_47303)
  // translucent pleated sheer: backlit glow raised 0.32 -> 0.5 (QA r1: read as an opaque slab; kn_36 / gstp_23 show it glowing)
  sheer: { c: '#e6e1d6', r: 0.9, l: LAYER.fabric, e: 0.5 },
  blackout: { c: '#cbc7bf', r: 0.85, l: LAYER.fabric },         // opaque pleated blackout, light grey (KN Aviation night photo)
  shadeBtn: { c: '#d9d6cf', r: 0.35 },
};

const circX = (y) => Math.sqrt(Math.max(0, CAB.R * CAB.R - (y - CAB.yc) * (y - CAB.yc)));
// Sidewall profile: v (height) -> [x, y, nx, ny] for the RIGHT side (inward normal)
// dado: one planar facet 0.05-0.33 m carrying the grilles, kicked out to the window-belt circle at 0.40 m
const DADO = [[2.70, 0], [2.712, 0.05], [2.830, 0.33], [2.852, 0.37], [circX(0.40), 0.40]];
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

// Window cell band (the part of the wall that carries the window recess) and the sidewall top (bins start)
const WALL = { vb0: 0.74, vb1: 1.58, vTop: 1.60, dadoTop: 0.40, bottomRows: [0, 0.05, 0.33, 0.37, 0.40, 0.58, 0.74] };
const HOLE_R = 0.105;
// 777 window recess, relative to the pane centre (y 1.13): a tall "bathtub" bezel, round-topped just under the bins,
// with a sill below the pane that carries the shade button. Width/height from ANA + review photos scaled by the
// 21 in window pitch: recess ~0.39 wide, bottom ~0.14 below the pane, top at the bin line (see notes in REFERENCE777)
const REC = { hw: 0.195, top: 0.42, bot: -0.33, rTop: 0.15, rBot: 0.075, depth: 0.034, btn: -0.268 };
const WMAT = {
  lining: { c: '#c3bfb7', r: 0.5 },           // grey tunnel lining round the pane (c_27300, tt photo)
  seam: { c: '#b3b1ac', r: 0.6 },                               // sidewall panel joint, every second window
  grilleBack: { c: '#1c212c', r: 0.8 },                         // plenum behind the louvres, keeps their depth [A]
  // rounded frame round the grille, lighter than the dado panel (py_37301 frame #5c6a82-#5f6e8a vs panel #30394e) [V]
  grilleFrame: { c: '#8894ae', r: 0.5 },
  label: { c: '#ecebe6', r: 0.5 },                              // small white placards on the dado (py_37301/37303)
  halo: { c: '#4467ff', r: 0.3, e: 0.8 },                       // blue LED ring round the shade button (LALF/OMAAT photos)
  pin: { c: '#2a2c30', r: 0.6 },
};
function sdRecess(px, py) {
  const cy = (REC.top + REC.bot) / 2, hh = (REC.top - REC.bot) / 2;
  return sdRRect(px, py - cy, REC.hw, hh, py > cy ? REC.rTop : REC.rBot);
}
function recessRay(th) {
  const dx = Math.cos(th), dy = Math.sin(th);
  let lo = 0, hi = 1.0;
  for (let i = 0; i < 28; i++) { const m = (lo + hi) / 2; if (sdRecess(dx * m, dy * m) < 0) lo = m; else hi = m; }
  return [dx * lo, dy * lo];
}
function windowCellPattern(cellW, holeW, holeH, holeR, vc, rayFn) {
  const hw = cellW / 2, hh0 = vc - WALL.vb0, hh1 = WALL.vb1 - vc;
  const cornerAng = [Math.atan2(hh1, hw), Math.PI - Math.atan2(hh1, hw), Math.PI + Math.atan2(hh0, hw), 2 * Math.PI - Math.atan2(hh0, hw)];
  const base = [];
  if (rayFn) {                                                  // recess: 48 angles spaced evenly along its outline
    const M = 720, pts = [], acc = [0], NR = 48;                // (was 32: faceted corners on the soft lip, QA r1)
    for (let i = 0; i <= M; i++) pts.push(rayFn((i / M) * Math.PI * 2));
    for (let i = 1; i <= M; i++) acc.push(acc[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    for (let k = 0, i = 0; k < NR; k++) { while (acc[i] < (k / NR) * acc[M]) i++; base.push((i / M) * Math.PI * 2); }
  } else for (let i = 0; i < 44; i++) base.push((i / 44) * Math.PI * 2);
  const angs = [...new Set([...base, ...cornerAng].map((a) => +a.toFixed(6)))].sort((a, b) => a - b);
  const ring = angs.map((th) => {
    const h = rayFn ? rayFn(th) : rrectRay(th, holeW / 2, holeH / 2, holeR);
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

// wall grid; rows below the dado top go to g.dado when the target carries one (seat/monument runs)
function wallGrid(g, side, zs, vs) {
  if (g.dado && vs[0] < WALL.dadoTop - 1e-6) {
    const lo = vs.filter((v) => v <= WALL.dadoTop + 1e-6), hi = vs.filter((v) => v >= WALL.dadoTop - 1e-6);
    if (lo.length > 1) wallGrid(g.dado, side, zs, lo);
    if (hi.length > 1) wallGrid({ p: g.p, n: g.n, u: g.u, i: g.i }, side, zs, hi);
    return;
  }
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
  const topRows = [WALL.vb1, vTop];
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

// Local frame on the wall: X along the cabin (+z on the right, -z on the left), Y up the wall tangent,
// Z = inward normal (toward the cabin); at height yc + dv, origin pushed out by `depth` behind the wall surface.
function windowFrame(side, depth = 0, dv = 0) {
  const W = CAB.win;
  const [x, y, nx, ny] = wallAt(W.yc + dv);
  const N = [nx * side, ny, 0];
  const Y = side > 0 ? [ny, -nx, 0] : [-ny, -nx, 0];
  const X = [0, 0, side];
  const o = [x * side - N[0] * depth, y - N[1] * depth, 0];
  return [X[0], X[1], X[2], 0, Y[0], Y[1], Y[2], 0, N[0], N[1], N[2], 0, o[0], o[1], o[2], 1];
}

// turn every triangle of g toward `hint`, then smooth normals
function faceTo(g, hint) {
  const P = g.p, I = g.i;
  for (let t = 0; t < I.length; t += 3) {
    const [a, b, c] = [I[t] * 3, I[t + 1] * 3, I[t + 2] * 3];
    const fn = V3.cross([P[b] - P[a], P[b + 1] - P[a + 1], P[b + 2] - P[a + 2]], [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]]);
    if (V3.dot(fn, hint) < 0) { const tmp = I[t + 1]; I[t + 1] = I[t + 2]; I[t + 2] = tmp; }
  }
  computeNormals(g);
  return g;
}
// loft of closed rings [[pts2d, depth], ...] through a mapping (a, b, d) -> xyz; every face turned toward `hint`
function ringLoft(rings, map, hint) {
  const g = raw(), n = rings[0][0].length;
  for (const [pts, d] of rings) for (const [a, b] of pts) { g.p.push(...map(a, b, d)); g.n.push(0, 0, 0); g.u.push(0, 0); }
  for (let r = 0; r < rings.length - 1; r++) for (let i = 0; i < n; i++) {
    const a = r * n + i, b = r * n + ((i + 1) % n);
    g.i.push(a, b, b + n, a, b + n, a + n);
  }
  return faceTo(g, hint);
}

// Window recess + pane tunnel + glass + dado grille in the cabin frame (window centre at z = 0) for a side.
// Recess: rolled lip -> drafted wall -> floor (sill) -> rolled opening (holeW x holeH) -> grey lining -> pane (10 x 15 in).
function windowParts(side, pat) {
  const W = CAB.win, vc = W.yc;
  const [, , cnx, cny] = wallAt(vc);
  const out = [-cnx, -cny], hint = [cnx * side, cny, 0];
  const map = (dz, dv, d) => { const [x, y] = wallAt(vc + dv); return [(x + out[0] * d) * side, y + out[1] * d, dz]; };
  const ths = pat.ring.map((p) => p.th);
  const rec = pat.ring.map((p) => p.h);                         // identical to the wall hole ring -> watertight
  const open = ths.map((th) => rrectRay(th, W.holeW / 2, W.holeH / 2, HOLE_R));
  const pane = ths.map((th) => rrectRay(th, W.w / 2, W.h / 2, 0.09));
  const inset = (pts, s) => pts.map(([a, b]) => { const l = Math.hypot(a, b) || 1; return [a * (1 - s / l), b * (1 - s / l)]; });
  const scl = (pts, k) => pts.map(([a, b]) => [a * k, b * k]);
  const D = REC.depth;
  // outer lip: soft quarter-round (r ~16 mm) tangent to the wall, then a slightly drafted wall to the sill.
  // QA r1: the old 5 mm / 11 mm step drew a crisp double outline; real 777 reveals roll in softly
  // [V: tt_window, lalf_37, f_17313; A: radius]. Ring 0 takes the wall normal so the roll-in has no seam.
  const q = [0, 20, 40, 60, 75, 90].map((a) => (a * Math.PI) / 180), LR = 0.016;
  const lip = ringLoft([...q.map((a) => [inset(rec, LR * Math.sin(a)), LR * (1 - Math.cos(a))]), [inset(rec, 0.019), D]], map, hint);
  for (let i = 0; i < rec.length; i++) { const [, , wnx, wny] = wallAt(vc + rec[i][1]); lip.n.splice(i * 3, 3, wnx * side, wny, 0); }
  const parts = [
    [lip, MAT.reveal],
    [ringLoft([[inset(rec, 0.019), D], [scl(open, 1.085), D]], map, hint), MAT.reveal],
    [ringLoft([[scl(open, 1.085), D], [scl(open, 1.02), D + 0.007], [scl(open, 0.992), D + 0.026]], map, hint), MAT.reveal],
    // lining: straight shade channel (both shades run here), then necks down to the pane
    [ringLoft([[scl(open, 0.992), D + 0.026], [scl(open, 0.986), D + 0.056], [pane, 0.106]], map, hint), WMAT.lining],
  ];
  // dado air-return grille under the window: louvred panel in a rounded frame (py_37301 / py_37303); modelled
  // proud of the dado skin (frame 6 mm, louvres behind it) so the dado needs no cut-out
  const gmap = (dz, v, off) => { const [x, y, nx, ny] = wallAt(v); return [(x + nx * off) * side, y + ny * off, dz]; };
  const gc = 0.19, ghw = 0.205, ghh = 0.112;
  const gr = (hw, hh, r) => rrectPts(hw * 2, hh * 2, r, 3).map(([a, b]) => [a, gc + b]), NG = gr(0.1, 0.1, 0.02).length;
  const gm = (a, b, d) => gmap(a, b, d);
  const ghint = [wallAt(gc)[2] * side, wallAt(gc)[3], 0];
  parts.push([ringLoft([[gr(ghw + 0.012, ghh + 0.012, 0.036), 0.0004], [gr(ghw + 0.004, ghh + 0.004, 0.03), 0.0064], [gr(ghw - 0.001, ghh - 0.001, 0.027), 0.0012]], gm, ghint), WMAT.grilleFrame]);
  const back = raw();
  back.p.push(...gm(0, gc, 0.0012)); back.n.push(0, 0, 0); back.u.push(0, 0);
  for (const [a, b] of gr(ghw - 0.001, ghh - 0.001, 0.027)) { back.p.push(...gm(a, b, 0.0012)); back.n.push(0, 0, 0); back.u.push(0, 0); }
  for (let i = 0; i < NG; i++) back.i.push(0, 1 + i, 1 + ((i + 1) % NG));
  parts.push([faceTo(back, ghint), WMAT.grilleBack]);
  const lv = raw();
  const quad = (p0, p1, p2, p3) => {
    const b = lv.p.length / 3; lv.p.push(...p0, ...p1, ...p2, ...p3); for (let k = 0; k < 4; k++) { lv.n.push(0, 0, 0); lv.u.push(0, 0); }
    lv.i.push(b, b + 1, b + 2, b, b + 2, b + 3);
  };
  const nSl = 30, v0 = gc - ghh + 0.008, v1 = gc + ghh - 0.008;  // ~30 fine slats [V: py_37301 crop, QA r1]
  for (let k = 0; k < nSl; k++) {                               // horizontal louvres, tilted down-and-out
    const v = lerp(v0, v1, (k + 0.5) / nSl), zz = ghw - 0.012;
    quad(gm(-zz, v, 0.0055), gm(zz, v, 0.0055), gm(zz, v - 0.005, 0.0018), gm(-zz, v - 0.005, 0.0018));
  }
  for (let k = 0; k < 9; k++) {                                 // vertical ribs (9, py_37301)
    const z = lerp(-ghw + 0.02, ghw - 0.02, k / 8);
    quad(gm(z - 0.002, v0 - 0.004, 0.0058), gm(z + 0.002, v0 - 0.004, 0.0058), gm(z + 0.002, v1 + 0.004, 0.0058), gm(z - 0.002, v1 + 0.004, 0.0058));
  }
  parts.push([faceTo(lv, ghint), MAT.grille]);
  const lb = raw(), lz = W.pitch / 2 - 0.006, lp = [[lz - 0.024, 0.205], [lz + 0.024, 0.205], [lz + 0.024, 0.219], [lz - 0.024, 0.219]].map(([a, b]) => gmap(a, b, 0.0012));
  lb.p.push(...lp.flat()); lb.u.push(0, 0, 0, 0, 0, 0, 0, 0); lb.n.push(...Array(12).fill(0));
  lb.i.push(0, 1, 2, 0, 2, 3);
  parts.push([faceTo(lb, ghint), WMAT.label]);
  // glass (drawn by the glass program: multiplies the sky behind)
  const N = 40, gl_ = raw();
  const glass = []; for (let i = 0; i < N; i++) glass.push(rrectRay((i / N) * Math.PI * 2, W.w / 2, W.h / 2, 0.09));
  gl_.p.push(...map(0, 0, 0.106)); gl_.n.push(cnx * side, cny, 0); gl_.u.push(0.5, 0.5);
  for (const [a, b] of glass) { gl_.p.push(...map(a, b, 0.106)); gl_.n.push(cnx * side, cny, 0); gl_.u.push(0, 0); }
  for (let i = 0; i < N; i++) gl_.i.push(0, 1 + i, 1 + ((i + 1) % N));
  fixWinding(gl_);
  return { parts, glass: gl_ };
}

// Shade geometry in the window-local frame: unit panel spanning y in [-H/2, H/2]; scaled per instance by the
// closed fraction (anchored at the top of the opening). Electric shades are cellular pleated fabric (~11 mm pleats,
// OMAAT / LALF / KN photos); the PY/Y shade is a plain panel whose grip lip stays visible at the top when open.
const SHADE = { w: 0.320, h: CAB.win.holeH, depth: REC.depth + 0.046 };  // wider than the tunnel: edges hide behind the lining
function shadePanelGeo(kind) {
  const B = new Builder();
  const { w, h } = SHADE;
  if (kind === 'manual') {
    B.add(gBox(w, h, 0.003), null, MAT.shade);
  } else {
    const g = raw(), n = 80;                                    // 40 pleats (~11 mm, kn_36 / omaat_24 / gstp_23)
    for (let k = 0; k <= n; k++) {
      const y = -h / 2 + (h * k) / n, zz = (k % 2) * 0.005;       // 5 mm zig-zag (was 3 mm: shaded flat, QA r1) [A]
      g.p.push(-w / 2, y, zz, w / 2, y, zz); g.n.push(0, 0, 1, 0, 0, 1); g.u.push(0, k / n, 1, k / n);
    }
    for (let k = 0; k < n; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
    computeNormals(g);
    let dot = 0; for (let v = 2; v < g.n.length; v += 3) dot += g.n[v];
    if (dot < 0) { for (let v = 0; v < g.n.length; v++) g.n[v] = -g.n[v]; for (let t = 0; t < g.i.length; t += 3) { const tmp = g.i[t + 1]; g.i[t + 1] = g.i[t + 2]; g.i[t + 2] = tmp; } }
    B.add(g, null, kind === 'sheer' ? MAT.sheer : MAT.blackout);
    // pleat stripes baked into vertex colour: valley rows x0.86, crest rows x1.0 (QA r1: closed shades read as plain
    // slabs; the photos show distinct horizontal stripes) [A: contrast]
    const geo = B.build();
    for (let k = 0; k < geo.col.length / 4; k++) if (((k >> 1) & 1) === 0) for (let c = 0; c < 3; c++) geo.col[k * 4 + c] = Math.round(geo.col[k * 4 + c] * 0.86);
    return geo;
  }
  return B.build();
}
function shadeRailGeo(kind) {
  const B = new Builder();
  if (kind === 'manual') {
    B.add(gRBox(SHADE.w, 0.016, 0.014, 0.006, 1), M4.trs(0, 0, 0.006), MAT.shadeRail);                 // grip lip
    B.add(gRBox(0.09, 0.006, 0.006, 0.0028, 1), M4.trs(0, -0.004, 0.0125), { c: '#a9a7a1', r: 0.45 }); // finger scoop
  } else B.add(gRBox(SHADE.w, 0.011, 0.009, 0.004, 1), M4.trs(0, 0, 0.004), kind === 'sheer' ? { c: '#b3aea5', r: 0.4 } : { c: '#bab6ad', r: 0.4 });
  return B.build();
}
// instance transforms for a window's shade state (f = closed fraction 0..1). The rail runs from its stowed
// position (hidden above the opening for electric, grip showing under the top edge for manual) to the sill.
function shadeMats(w, f, depthOff = 0) {
  const F = windowFrame(w.side, SHADE.depth + depthOff);
  const Tz = M4.trs(0, 0, w.z);
  const top = SHADE.h / 2, man = !w.electric;
  const railY = man ? lerp(top - 0.020, -top + 0.017, f) : lerp(top + 0.012, -top + 0.009, f);
  const hgt = Math.max(top - railY, 0.0004);
  const s = hgt / SHADE.h;
  // stowed electric shade (f = 0): collapse the instance entirely. QA r2: the 0.4 mm sliver left at the top of the
  // opening rasterised as a dotted line in the shadow map, printing a "chain" of dots through every sun patch [V: q07]
  const panel = !man && f <= 0 ? M4.mul(Tz, M4.mul(F, M4.trs(0, top, 0, 0, 0, 0, 0, 0, 0)))
    : M4.mul(Tz, M4.mul(F, M4.mul(M4.trs(0, top - hgt / 2, 0), M4.trs(0, 0, 0, 0, 0, 0, 1, s, 1))));
  const rail = M4.mul(Tz, M4.mul(F, M4.trs(0, railY, 0)));
  return { panel, rail };
}
// Shade control under each electric window: split up/down pill with a blue LED ring and a pinhole (LALF close-up)
function shadeButtonGeo() {
  const B = new Builder();
  const pill = (w, h) => rrectPts(w, h, w / 2 - 1e-4, 5);
  const ring = raw(), o = pill(0.022, 0.046), iN = pill(0.0165, 0.0405), n = o.length;
  for (const [a, b] of o) { ring.p.push(a, b, 0.0012); ring.n.push(0, 0, 1); ring.u.push(0, 0); }
  for (const [a, b] of iN) { ring.p.push(a, b, 0.0012); ring.n.push(0, 0, 1); ring.u.push(0, 0); }
  for (let i = 0; i < n; i++) { const j = (i + 1) % n; ring.i.push(i, j, n + j, i, n + j, n + i); }
  fixWinding(ring);
  B.add(ring, null, WMAT.halo);
  const half = rrectPts(0.0155, 0.0195, 0.0065, 4).map(([a, b]) => [a, Math.max(b, -0.0078)]);
  B.add(gExtrude(half, 0.004), M4.trs(0, 0.0102, 0.0022), MAT.shadeBtn);
  B.add(gExtrude(half, 0.004), M4.trs(0, -0.0102, 0.0022, 0, 0, Math.PI), MAT.shadeBtn);
  B.add(gBox(0.0022, 0.0022, 0.001), M4.trs(0, -0.031, 0.0005), WMAT.pin);
  return B.build();
}

// Studio review unit: a 6-window wall run (left side) with dado, grilles, panel seams and every shade state:
// manual open / half / closed, electric open / sheer / blackout (+ buttons), sky-lit panes
function windowStudioGeo() {
  const B = new Builder();
  const W = CAB.win, P = W.pitch;
  const pat = windowCellPattern(P, W.holeW, W.holeH, HOLE_R, W.yc, recessRay);
  const zs = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5].map((k) => k * P);
  const g = raw(); g.dado = raw();
  buildSidewallRun(g, -1, -P * 3, P * 3, zs, pat, WALL.vTop);
  fixWinding(g); fixWinding(g.dado);
  B.add(g, null, MAT.sidewall); B.add(g.dado, null, MAT.dado);
  B.addBuilt(wallSeamGeo(-1, zs.filter((z, k) => k % 2 === 1).map((z) => z + P / 2)));
  const wp = windowParts(-1, pat);
  const states = [['manual', 0], ['manual', 0.5], ['manual', 1], ['sheer', 0], ['sheer', 1], ['blackout', 1]];
  const sky = { c: '#bcd3ec', r: 1, e: 0.9 };
  zs.forEach((z, k) => {
    for (const [pg, m] of wp.parts) B.add(pg, M4.trs(0, 0, z), m);
    B.add(wp.glass, M4.trs(0, 0, z), sky);
    const [kind, f] = states[k];
    const w = { z, side: -1, electric: kind !== 'manual' };
    const kinds = kind === 'manual' ? [['manual', f]] : [['sheer', kind === 'sheer' ? f : 1], ['blackout', kind === 'blackout' ? f : 0]];
    for (const [kk, ff] of kinds) {
      const m = shadeMats(w, ff, kk === 'blackout' ? -0.012 : 0);
      if (ff > 0) B.addBuilt(shadePanelGeo(kk), m.panel);
      B.addBuilt(shadeRailGeo(kk), m.rail);
    }
    if (w.electric) B.addBuilt(shadeButtonGeo(), M4.mul(M4.trs(0, 0, z), windowFrame(-1, REC.depth, REC.btn)));
  });
  return B.build();
}
// vertical panel joints on the sidewall (ANA photos show one every second window, mid-pier)
function wallSeamGeo(side, zs) {
  const B = new Builder(), vs = [WALL.dadoTop, 0.58, 0.74, 0.9, 1.1, 1.3, 1.45, WALL.vTop];
  for (const z of zs) {
    const g = raw();
    for (const v of vs) {
      const [x, y, nx, ny] = wallAt(v);
      for (const dz of [-0.0012, 0.0012]) { g.p.push((x + nx * 0.0006) * side, y + ny * 0.0006, z + dz); g.n.push(nx * side, ny, 0); g.u.push(0, 0); }
    }
    for (let j = 0; j < vs.length - 1; j++) { const a = j * 2; g.i.push(a, a + 1, a + 3, a, a + 3, a + 2); }
    fixWinding(g);
    B.add(g, null, WMAT.seam);
  }
  return B.build();
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

function buildShell(gl, layout) {
  const zones = layout.zones;
  const shell = new Builder();
  const upper = new Builder();
  const W = CAB.win;
  const pat = windowCellPattern(W.pitch, W.holeW, W.holeH, HOLE_R, W.yc, recessRay);

  // ---- floor ----
  // the seat zone aft of door 3 holds THE Room rows 19-20 and PY rows 25-27: split it at z20 (the J/PY partition) so
  // PY gets the navy Y/PY carpet (QA r1: PY had the brown J carpet; py_37301 / py_37303 show navy) [V]
  const floorZones = [];
  for (const zn of zones) {
    if (zn.type === 'seat' && zn.cls === 'J' && layout.z20 > zn.z0 && layout.z20 < zn.z1) {
      floorZones.push({ ...zn, z1: layout.z20 }, { ...zn, z0: layout.z20, cls: 'PY' });
    } else floorZones.push(zn);
  }
  for (const zn of floorZones) {
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
      const g = raw(); g.dado = raw();
      buildSidewallRun(g, side, za, zb, hz, pat, WALL.vTop);
      fixWinding(g); fixWinding(g.dado);
      shell.add(g, null, MAT.sidewall); shell.add(g.dado, null, MAT.dado);
      // panel joints mid-pier after every second window (air-return grilles + recesses are instanced with the reveals)
      const sz = hz.filter((z) => z > za && z < zb).sort((a, b) => a - b).filter((z, k) => k % 2 === 1).map((z) => z + W.pitch / 2).filter((z) => z < zb - 0.05);
      shell.addBuilt(wallSeamGeo(side, sz));
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
  // ---- Y seat-track covers (QA r2: replace the aisle path strips no photo shows) ----
  // one glossy royal-blue cover along each economy seat-leg line, 45 x 5 mm, running under its rows [V: y_47304 cover
  // beside the track fitting, y_47301 blue bar under the ABC block]; leg lines follow econUnit (09_seats: legs at
  // +-(W/2 - 0.24) of the block centre, +-0.24 for two-seat blocks), so the taper rows 39-42 get their own lines [D].
  // PY is left bare: py_37301 / py_37302 show no covers on the darker carpet
  const tracks = new Map();
  const ySeats = layout.seats.filter((q) => q.kind === 'econ');
  for (const r of new Set(ySeats.map((q) => q.row))) {
    const rs = ySeats.filter((q) => q.row === r);
    for (const b of [rs.filter((q) => q.x < -1.1), rs.filter((q) => Math.abs(q.x) <= 1.1), rs.filter((q) => q.x > 1.1)]) {
      if (!b.length) continue;
      const cx = b.reduce((a, q) => a + q.x, 0) / b.length, hw = b.length >= 3 ? (b.length * 19 * IN) / 2 - 0.24 : 0.24;
      for (const lx of [cx - hw, cx + hw]) {
        const k = lx.toFixed(2), t = tracks.get(k) || { x: lx, z0: 1e9, z1: -1e9 };
        t.z0 = Math.min(t.z0, b[0].z - 0.60); t.z1 = Math.max(t.z1, b[0].z + 0.25);
        tracks.set(k, t);
      }
    }
  }
  for (const t of tracks.values()) shell.add(gRBox(0.045, 0.010, t.z1 - t.z0, 0.004, 1), M4.trs(t.x, 0.001, (t.z0 + t.z1) / 2), MAT.trackCover);

  const meshes = {
    shell: gl.mesh(shell.build(), { name: 'shell', layer: 'shell' }),
    upper: gl.mesh(upper.build(), { name: 'upper', layer: 'upper' }),
  };

  // ---- window reveals + glass (instanced per side), shades (instanced per kind) ----
  const inst = { R: [], L: [] };
  layout.windows.forEach((w, i) => { (w.side > 0 ? inst.R : inst.L).push({ w, i }); });
  const winParts = {};
  for (const [key, side] of [['R', 1], ['L', -1]]) {
    const wp = windowParts(side, pat);
    winParts[key] = wp;
    const mats = inst[key].map(({ w }) => M4.trs(0, 0, w.z));
    const rb = new Builder(); for (const [pg, m] of wp.parts) rb.add(pg, null, m);
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
  // shade button on the sill of every electric window (one press: sheer, again: blackout)
  const btn = new Builder(), bg = shadeButtonGeo();
  for (const w of layout.windows) if (w.electric) btn.addBuilt(bg, M4.mul(M4.trs(0, 0, w.z), windowFrame(w.side, REC.depth, REC.btn)));
  meshes.shadeBtns = gl.mesh(btn.build(), { name: 'shadeBtns', castShadow: false });
  return { meshes, inst, winParts, shades };
}
