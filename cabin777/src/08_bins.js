// ------------------------------------------------------------------
// Overhead bins (777 Signature Interior, checked against ANA's official photos y_47300/47301, py_37302,
// c_27312 and a THE Suite aisle photo [V]): outboard pivot bins in 2-frame modules (one latch, one seam, one row
// placard every 2 windows: latch spacing vs window 2-pitch in y_47301, seams in py_37302, c_27312 [V]) with a
// near-upright convex door, recessed pill latch 1/3 down the door, row placard above it, single dark seam per
// joint (none at the ends of a run); double-sided centre bins (2-frame) whose lower doors wrap under a narrow PSU
// channel (y_47300 [V shape]); PSU band on the bin bottoms with subtle filler-panel joints, raised gasper/light
// boxes once per window bay outboard (py_37302, y_47301 [V]), per-seat reading-light / gasper rows on the
// centre channel, call button, signs, O2 door [A details]
// ------------------------------------------------------------------
const BIN = { side: 2 * CAB.win.pitch, center: 2 * CAB.win.pitch }, RAIL_Y = 2.163;
const binBottomY = (x) => { const ax = Math.abs(x); return lerp(1.60, 1.795, clamp((2.845 - ax) / (2.845 - 1.53), 0, 1)); };
// outboard door face, lip -> ceiling crease: more upright than SIDEBIN so the latch and placard face the aisle
// as in py_37302 / y_47301 (the whole door is seen up to the ceiling line) [A shape]
const OBIN_DOOR = [[1.53, 1.795], [1.495, 1.83], [1.472, 1.93], [1.469, 2.03], [1.479, 2.115], [1.508, 2.178], [1.56, 2.214], [1.64, 2.228]];
const OBIN = [SIDEBIN[0], ...OBIN_DOOR, ...SIDEBIN.slice(8)];
// centre bin section used by the bins (07_shell's CBIN is only consumed here): the lower doors wrap broadly under
// to a PSU channel |x| < 0.30 (channel / bin width 0.36 in plan: b_sany_y22 from 34E reads ~0.47, y_47300 ~0.27, the
// old 0.51 filled the whole underside in q15 [D mean]) [A ordinates]; top points unchanged so the vault still meets
// the bin at (0.725, 2.262); aisle-edge headroom unchanged (x 0.75 at y 1.935).
// The door ordinates are resampled with a Catmull-Rom spline (3 steps a span) so the wrap shades smoothly as the
// real doors do (y_47301, c_27312 [V]).
function crResample(P, m = 3) {
  const out = [P[0]];
  for (let k = 0; k < P.length - 1; k++) {
    const p0 = P[Math.max(0, k - 1)], p1 = P[k], p2 = P[k + 1], p3 = P[Math.min(P.length - 1, k + 2)];
    for (let j = 1; j <= m; j++) {
      const t = j / m, t2 = t * t, t3 = t2 * t;
      out.push([0, 1].map((c) => 0.5 * (2 * p1[c] + (p2[c] - p0[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2 + (3 * p1[c] - p0[c] - 3 * p2[c] + p3[c]) * t3)));
    }
  }
  return out;
}
const CBIN_DOOR = crResample([[0.30, 1.835], [0.46, 1.843], [0.62, 1.874], [0.75, 1.935], [0.822, 2.03], [0.82, 2.12], [0.78, 2.2], [0.725, 2.262]]);
const CBIN_Q = [...CBIN_DOOR, [0.62, 2.30], [0, 2.315]];
const CBIN_Y = 1.835, CBIN_BAND = 0.60;
const TILT_O = Math.atan2(1.795 - 1.60, 2.845 - 1.53);
// door skin slightly cool (photo samples of lit door faces ~#eeeeed, shaded ones #b4b8be..#bfc5cb) [V colour]
// Centre-bin doors and PSU channel get a small self-lift (e 0.10): they face down/sideways into the dim middle of
// the cabin where the hemisphere fill leaves them 40-90 levels darker than the photos (lower door #c3c7cb in
// c_27312 / y_47301, channel #bebec0..#cacaca in y_47300 [V samples]); the outboard doors already matched [D].
const BINMAT = {
  door: { c: '#e3e5e8', r: 0.34, l: LAYER.plastic },
  doorC: { c: '#e3e5e8', r: 0.34, l: LAYER.plastic, e: 0.10 },
  bandC: { c: '#e4e3df', r: 0.5, l: LAYER.plastic, e: 0.10 },
  signPod: { c: '#2a2e34', r: 0.45 },
  seam: { c: '#a7abb0', r: 0.8 },   // thin mid-grey hairline, not a black arc (c_th1, b_sany_y22 [V])
  lipGap: { c: '#4a4f56', r: 0.8 },
  lip: { c: '#e2e2df', r: 0.36, l: LAYER.plastic },
  bezel: { c: '#d3d5d6', r: 0.4 },
  recess: { c: '#3c4046', r: 0.6 },
  paddle: { c: '#c4c8cc', r: 0.4 },
  // outboard PSU band near-white in every photo (y_47300 #d9d9db..#dddddd, c_27312 #ebf0f4 [V]; was ~#a4a4a5)
  band: { c: '#e4e3df', r: 0.5, l: LAYER.plastic, e: 0.11 },
  well: { c: '#d6d7d7', r: 0.55, l: LAYER.plastic, e: 0.08 },   // recessed stadium well floor, a shade darker [A]
  wellRim: { c: '#b8bcc0', r: 0.6 },                             // shadow line around the well [A]
  smoke: { c: '#ffffff', r: 0.3, l: LAYER.atlasGlow, e: 0.55 },  // smoked sign window (dark ground in the atlas)
  rail: { c: '#e8e8e5', r: 0.36, l: LAYER.plastic },
  groove: { c: '#9aa0a6', r: 0.7 },
  joint: { c: '#dcdedf', r: 0.7 },
  psuBox: { c: '#e6e6e3', r: 0.4, l: LAYER.plastic },
  pod: { c: '#eceae6', r: 0.4, l: LAYER.plastic },
  bezelDark: { c: '#8a9096', r: 0.4 },
  call: { c: '#6f8fb8', r: 0.4 },
  o2gap: { c: '#cfd2d5', r: 0.7 },   // hairline only: no outlined plate reads in y_47300 [V]
  // centre gasper nozzles: small light-grey (y_47300 shows them barely darker than the channel) [V]
  nozzleC: { c: '#d0d3d6', r: 0.35, m: 0.3 },
  grille: { c: '#9ea3a8', r: 0.6, l: LAYER.grille },
};

// Bin decals painted over 06_atlas's versions of the same rects (these decals are only used here; the atlas is
// uploaded right after buildAtlas, before the bins are built):
//  - row placards: dark-grey numerals and seat pictograms printed straight on the door's top rail, no plate
//    (py_37302 '25 ..' above the latch, sany_11 / sany_12 '25' / '31' + seat icons on the lip [V]); ink #4a4f57,
//    numeral 22 px bold [A] (w1: '32' on the rail is readable ~3 m away in b_sany_y22). The 76x30 px rect is stretched onto a PLACARD (0.15 x 0.036 m) quad, so the
//    content is drawn pre-squeezed in x. Centre-bin placards get a lighter ground to match the self-lit centre door.
//  - psuSigns: dark ground, no-smoking icon red-orange #ff5a2a, fasten-belt icon amber #ffa634 (sany_15 [V colours])
function paintBinDecals(A, layout) {
  const g = A.canvas.getContext('2d'), S = A.canvas.width;
  const rect = (name) => { const r = A.rects[name]; return r && [r[0] * S, r[1] * S, (r[2] - r[0]) * S, (r[3] - r[1]) * S]; };
  const INK = '#3a3f47';
  const seatIcon = (x, y, s, bg) => {      // seat pictogram (plan view): rounded square outline, thick backrest edge
    g.fillStyle = INK; g.beginPath(); g.roundRect(x, y - s * 0.5, s, s, s * 0.25); g.fill();
    g.fillStyle = bg; g.beginPath(); g.roundRect(x + s * 0.16, y - s * 0.5 + s * 0.36, s * 0.68, s * 0.48, s * 0.12); g.fill();
  };
  const rows = [...new Set(layout.seats.map((s) => s.row))];
  for (const r of rows) for (let i = 0; i < 3; i++) {
    const q = rect(`row${r}_${i}`);
    if (!q) continue;
    const [x, y, w, h] = q, sx = (w / h) / (PLACARD[0] / PLACARD[1]);
    // ground = door colour after shadeUpper (x0.97) outboard; lighter on the self-lit centre door [D]
    const bg = i === 1 ? '#f6f7f9' : '#e0e1df';
    g.fillStyle = bg; g.fillRect(x, y, w, h);
    const n = layout.seats.filter((s) => s.row === r && (i === 1 ? Math.abs(s.x) <= 1.1 : i === 0 ? s.x < -1.1 : s.x > 1.1)).length;
    g.save(); g.translate(x, y); g.scale(sx, 1);
    const W = w / sx;                         // virtual width before the quad stretch
    g.fillStyle = INK; g.textAlign = 'left'; g.textBaseline = 'middle'; g.font = '700 22px "Helvetica Neue", Helvetica, Arial, sans-serif';
    const tw = g.measureText(String(r)).width, ic = 11, gap = 3;
    const total = tw + 6 + Math.min(n, 4) * (ic + gap);
    let cx = (W - total) / 2;
    g.fillText(String(r), cx, h / 2 + 1); cx += tw + 6;
    for (let k = 0; k < Math.min(n, 4); k++) { seatIcon(cx, h / 2, ic, bg); cx += ic + gap; }
    g.restore();
  }
  const q = rect('psuSigns');
  if (q) {
    // smoked lens: amber cigarette in a red ring + slash, amber belt halves with a red arrow between them
    // (b_lalf_c26 / thrifty_j_overhead-vent close-ups [V]; ground #2b2826 smoke [A])
    const [x, y, w, h] = q, A_ = '#ffa634', R_ = '#e8322a';
    g.fillStyle = '#2b2826'; g.fillRect(x, y, w, h);
    g.lineCap = 'round';
    g.fillStyle = A_; g.fillRect(x + 16, y + 28, 30, 8); g.fillRect(x + 48, y + 28, 5, 8);
    g.fillStyle = '#d8d0c0'; g.fillRect(x + 54, y + 20, 3, 6);
    g.strokeStyle = R_; g.lineWidth = 4;
    g.beginPath(); g.arc(x + 35, y + 32, 21, 0, Math.PI * 2); g.stroke();
    g.beginPath(); g.moveTo(x + 20, y + 17); g.lineTo(x + 50, y + 47); g.stroke();
    g.fillStyle = A_;
    g.beginPath(); g.roundRect(x + 72, y + 25, 20, 14, 3); g.fill();
    g.beginPath(); g.roundRect(x + 114, y + 25, 20, 14, 3); g.fill();
    g.fillStyle = '#2b2826'; g.fillRect(x + 77, y + 29, 10, 6);
    g.strokeStyle = R_; g.lineWidth = 3;
    g.beginPath(); g.moveTo(x + 110, y + 32); g.lineTo(x + 96, y + 32); g.moveTo(x + 102, y + 26); g.lineTo(x + 96, y + 32); g.lineTo(x + 102, y + 38); g.stroke();
  }
}
{ const base = buildAtlas; buildAtlas = function (layout) { const A = base(layout); paintBinDecals(A, layout); return A; }; }

// point + unit tangent on a face polyline at height y (face runs bottom -> top)
function faceAtY(face, y) {
  for (let k = 0; k < face.length - 1; k++) {
    const a = face[k], b = face[k + 1];
    if (y <= b[1] || k === face.length - 2) {
      const t = clamp((y - a[1]) / (b[1] - a[1]), 0, 1), l = Math.hypot(b[0] - a[0], b[1] - a[1]);
      return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), (b[0] - a[0]) / l, (b[1] - a[1]) / l];
    }
  }
}
// frame on a bin door: local X along the fuselage (reading direction for a viewer facing the door), Y up the
// face, Z out of the face; f = +1 when the face looks toward +x
function faceM(x, y, tx, ty, z, f, off = 0) {
  const X = [0, 0, -f], Y = [tx, ty, 0], Z = [-X[2] * ty, X[2] * tx, 0];
  const m = new Float32Array(16);
  m.set([...X, 0, ...Y, 0, ...Z, 0, x + Z[0] * off, y + Z[1] * off, z, 1]);
  return m;
}
// flat rounded-rect / stadium plate: outline in local XY, t thick along Z (gRBox clamps its radius to half the
// thickness, so thin plates came out square-cornered)
const gPlate = (w, h, r, t, seg = 8) => {
  // drop the zero-length straight edges of a full stadium (duplicate points break the cap triangulation)
  const P = rrectPts(w, h, r, seg).filter((p, k, A) => { const q = A[(k + 1) % A.length]; return Math.hypot(p[0] - q[0], p[1] - q[1]) > 1e-6; });
  return gExtrude(P, t, 60);
};
// the same lying flat under a band (w across x, d along z, thickness along y)
const padM = (x, y, z) => M4.trs(x, y, z, 0, Math.PI / 2);
// recessed stadium latch (light rim, dark well, lever paddle in its lower half) as in c_th1 / b_sany_y22 [V shape];
// rim set 1 mm into the door skin so it reads recessed, not proud (no photo shows a raised latch) [A]
function addLatch(B, M) {
  B.add(gPlate(0.14, 0.05, 0.025, 0.006), M4.mul(M, M4.trs(0, 0, -0.001)), BINMAT.bezel);
  B.add(gPlate(0.114, 0.028, 0.014, 0.004), M4.mul(M, M4.trs(0, 0.002, 0.0007)), BINMAT.recess);
  B.add(gPlate(0.1, 0.011, 0.0055, 0.004, 4), M4.mul(M, M4.trs(0, -0.0055, 0.0019)), BINMAT.paddle);
}
// shell around a face polyline, offset along its outward normal (outward = toward the aisle; inward = +1 for the
// outboard door, -1 for the centre bin) so wrapped-under door segments keep their thickness
function faceShell(face, xs, inward, out, inn) {
  const off = (d) => face.map((p, k) => {
    const a = face[Math.max(0, k - 1)], b = face[Math.min(face.length - 1, k + 1)];
    const l = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1, nx = -inward * (b[1] - a[1]) / l, ny = inward * (b[0] - a[0]) / l;
    return [(p[0] + nx * d) * xs, p[1] + ny * d];
  });
  return [...off(out), ...off(-inn).reverse()];
}
// door skin on a face polyline; the joint seam is a separate piece (doorSeam) so a run's ends stay clean
function addDoor(B, face, L, xs, inward, mat = BINMAT.door) {
  B.add(gExtrude(faceShell(face, xs, inward, 0.006, 0.004), L - 0.006, 45), null, mat);
}
// hairline between modules: fills the 6 mm door gap just below the skin (w1: a 12 mm gap read as a black arc)
const doorSeam = (B, face, xs, inward, z = 0) => B.add(gExtrude(faceShell(face, xs, inward, 0.0058, 0.002), 0.0064, 45), M4.trs(0, 0, z), BINMAT.seam);
// baked shading for the bins (the shader's hemisphere fill leaves them flat): x1.0 (ny 0.5) .. x0.95 (facing down),
// continuous in the normal, calibrated on photo samples (y_47301 door #c7c6cb..#dcdcdc, bin bottom #c0c3c8,
// centre bin #c2c3c7; c_27312 centre bin #c3c7cb; py_37302 door #b2bcc6, vault #f0f1ef) [D factors; r2 raised
// from 0.95..0.88 / 0.93, which rendered the centre bins 40-90 levels too dark]
function shadeUpper(geo) {
  const { nrm, col } = geo;
  for (let k = 0; k < nrm.length / 3; k++) {
    const ny = nrm[k * 3 + 1];
    const f = lerp(1.0, 0.95, clamp((0.5 - ny) / 1.5, 0, 1));   // continuous in ny (w1: steps banded the centre door)
    for (let c = 0; c < 3; c++) col[k * 4 + c] = Math.round(col[k * 4 + c] * f);
  }
  return geo;
}

function sideBinModule(side) {
  const L = BIN.side;
  const B = new Builder();
  B.add(gExtrude(OBIN.map(([x, y]) => [x * side, y]), L - 0.006, 20), null, MAT.bin);
  addDoor(B, OBIN_DOOR, L, side, 1);
  // bottom edge lip of the door + dark gap line to the PSU band
  B.add(gRBox(0.028, 0.016, L - 0.014, 0.007, 1), M4.trs(1.516 * side, 1.804, 0), BINMAT.lip);
  B.add(gBox(0.012, 0.002, L), M4.trs(1.548 * side, binBottomY(1.548) - 0.0015, 0, 0, 0, -TILT_O * side), BINMAT.lipGap);
  // latch 1/3 down the door (py_37302), module centre: one per 2-frame module [V]
  const [hx, hy, htx, hty] = faceAtY(OBIN_DOOR, 2.065);
  addLatch(B, faceM((hx - 0.006) * side, hy, htx * side, hty, 0, -side));
  // top rail carrying the row placard, divided from the face by a groove (c_th1 '13'/'14', b_sany_y22 '32' [V];
  // ~5 cm deep, 3 mm proud [A])
  const [gx, gy, gtx, gty] = faceAtY(OBIN_DOOR, RAIL_Y);
  B.add(gExtrude(faceShell([[gx, gy], ...OBIN_DOOR.filter((p) => p[1] > RAIL_Y + 0.005 && p[1] < 2.22)], side, 1, 0.009, 0.001), L - 0.014, 45), null, BINMAT.rail);
  B.add(gBox(L - 0.02, 0.003, 0.002), faceM(gx * side, gy - 0.002, gtx * side, gty, 0, -side, 0.0062), BINMAT.groove);
  // PSU band over the bin bottom, filler-panel joints ~0.27 m apart (py_37302, thrifty_j_overhead-vent [V pitch])
  const bw = 1.19, bx = 2.155, by = binBottomY(bx) - 0.003;
  B.add(gBox(bw, 0.004, L - 0.004), M4.trs(bx * side, by, 0, 0, 0, -TILT_O * side), BINMAT.band);
  for (let k = 0; k < 4; k++) B.add(gBox(bw - 0.02, 0.002, 0.0015), M4.trs(bx * side, by - 0.0025, -L / 2 + (k + 0.5) * L / 4, 0, 0, -TILT_O * side), BINMAT.joint);
  // cove LED along the top inner edge (washes the aisle panel) + sidewall wash lens under the bin
  B.add(gBox(0.05, 0.01, L - 0.03), M4.trs(1.70 * side, 2.238, 0), MAT.led);
  B.add(gBox(0.045, 0.006, L - 0.03), M4.trs(2.80 * side, 1.607, 0, 0, 0, side * 0.12), { c: '#ffffff', r: 0.4, l: 12, e: 0.35 });
  return shadeUpper(B.build());
}
function centerBinModule() {
  const L = BIN.center;
  const B = new Builder();
  const poly = [...CBIN_Q.map(([x, y]) => [x, y]), ...CBIN_Q.slice(0, -1).reverse().map(([x, y]) => [-x, y])];
  B.add(gExtrude(poly, L - 0.006, 20), null, MAT.bin);
  const [hx, hy, htx, hty] = faceAtY(CBIN_DOOR, 2.09);
  for (const s of [-1, 1]) {
    addDoor(B, CBIN_DOOR, L, s, -1, BINMAT.doorC);
    addLatch(B, faceM((hx + 0.006) * s, hy, htx * s, hty, 0, s));
    // plain crease filler where the vault meets the centre-bin crest (no cove light on this edge: see 07b header)
    B.add(gBox(0.05, 0.01, L - 0.006), M4.trs(0.70 * s, 2.268, 0), BINMAT.door);
    // dark gap between the wrapped door edge and the PSU channel (the two converging lines in y_47300)
    B.add(gBox(0.012, 0.002, L), M4.trs((CBIN_DOOR[0][0] + 0.005) * s, CBIN_Y - 0.0065, 0), BINMAT.lipGap);
  }
  B.add(gBox(CBIN_BAND, 0.004, L - 0.004), M4.trs(0, CBIN_Y - 0.0045, 0), BINMAT.bandC);
  // channel filler-panel joints, irregular (b_sany_y22 shows unequal panels, not a slatted run [V look, A spacing])
  for (const f of [-0.41, -0.16, 0.13, 0.37]) B.add(gBox(CBIN_BAND - 0.03, 0.002, 0.0015), M4.trs(0, CBIN_Y - 0.0075, f * L), BINMAT.joint);
  return shadeUpper(B.build());
}
// seams between neighbouring modules (instanced at the joints only, so no dark outline at the run ends)
function binSeams(which) {
  const B = new Builder();
  if (which === 'C') for (const s of [-1, 1]) doorSeam(B, CBIN_DOOR, s, -1);
  else doorSeam(B, OBIN_DOOR, which === 'R' ? 1 : -1, 1);
  return B.build();
}

// PSU fittings sit in recessed stadium wells (long axis across the band): a darker shadow line around a slightly
// darker floor, nothing proud but the fittings (thrifty_j_overhead-vent, b_lalf_c26, b_sany_y22 [V]; rim 3 mm [A])
function stadiumWell(B, w, d, x, z) {
  B.add(gPlate(w + 0.006, d + 0.006, (d + 0.006) / 2, 0.001), padM(x, -0.0005, z), BINMAT.wellRim);
  B.add(gPlate(w, d, d / 2, 0.001), padM(x, -0.0009, z), BINMAT.well);
}
function eyeball(B, x, z, r = 0.02) {       // reading light: light bezel, dark socket, lens ball (b_lalf_c26 [V])
  B.add(gCyl(r, r, 0.003, 18), M4.trs(x, -0.0018, z), BINMAT.pod);
  B.add(gCyl(r * 0.72, r * 0.72, 0.002, 16), M4.trs(x, -0.0032, z), BINMAT.bezelDark);
  B.add(gSphere(r * 0.52, 12, 8), M4.trs(x, -0.003, z, 0, 0, 0, 1, 0.6, 1), MAT.lens);
}
function gasper(B, x, z, r = 0.019) {       // gasper: bezel ring, conical nozzle, dark orifice (thrifty close-up [V])
  B.add(gCyl(r, r, 0.003, 18), M4.trs(x, -0.0018, z), BINMAT.pod);
  B.add(gCyl(r * 0.55, r * 0.68, 0.009, 14), M4.trs(x, -0.0065, z), BINMAT.nozzleC);
  B.add(gCyl(r * 0.22, r * 0.22, 0.002, 8), M4.trs(x, -0.0112, z), MAT.darkPlastic);
}
// smoked no-smoking / fasten-belt window in a band-coloured pill recess (b_lalf_c26, thrifty close-up: flush pill in
// the band plastic, icons lit amber + red behind a smoked lens [V]; 0.16 x 0.048 m [A])
function signWindow(B, x, z, w = 0.16, d = 0.048) {
  stadiumWell(B, w, d, x, z);
  B.add(gQuad(w - 0.03, d - 0.012), M4.trs(x, -0.0014, z, 0, Math.PI / 2), BINMAT.smoke, atlasUV('psuSigns'));
}
// centre PSU for one seat group (built flat, hanging from y=0): two wells across the channel, the forward one with
// n eyeball reading lights, the aft one with n gaspers (b_sany_y22: a stadium well holding a row of 4 round fittings,
// ~0.7 of the channel; y_47300: two slim transverse rows [V]); sign window, call button and a hairline O2 door flush
// on the channel [A]. pitch = fitting spacing.
function psuModule(n, pitch = PSU_C_PITCH) {
  const B = new Builder();
  const w = (n - 1) * pitch + 0.058;
  stadiumWell(B, w, 0.05, 0, -0.10);
  stadiumWell(B, w, 0.05, 0, -0.03);
  for (let k = 0; k < n; k++) {
    const x = (k - (n - 1) / 2) * pitch;
    eyeball(B, x, -0.10);
    gasper(B, x, -0.03);
  }
  signWindow(B, 0, 0.06, 0.13, 0.042);
  B.add(gPlate(0.022, 0.014, 0.004, 0.003), padM(Math.max(w / 2, 0.1) + 0.01, -0.0015, 0.06), BINMAT.call);
  const ow = Math.max(0.26, w);
  B.add(gBox(ow + 0.006, 0.001, 0.106), M4.trs(0, -0.0005, 0.16), BINMAT.o2gap);
  B.add(gBox(ow, 0.001, 0.1), M4.trs(0, -0.0012, 0.16), BINMAT.bandC);
  return B.build();
}
// outboard sign pod: the same flush smoked window once per seat row on the band
function signPodModule() {
  const B = new Builder();
  signWindow(B, 0, 0);
  return B.build();
}
// outboard PSU: one stadium well per window bay across the band, 0.26 x 0.10 m, holding two eyeball reading lights
// or two gaspers on alternate bays (thrifty_j_overhead-vent: gasper well, light well, sign pill in adjacent band
// panels; b_lalf_c26: 2 eyeballs ~1/3 and 2/3 along the well [V]; sizes [A]). Symmetric in x, so no mirror needed.
function psuBoxModule(air = false) {
  const B = new Builder();
  stadiumWell(B, 0.26, 0.10, 0, 0);
  for (const x of [-0.065, 0.065]) air ? gasper(B, x, 0, 0.026) : eyeball(B, x, 0, 0.03);
  return B.build();
}

function fitModules(z0, z1, nominal) {
  const n = Math.max(1, Math.round((z1 - z0) / nominal));
  const L = (z1 - z0) / n, out = [];
  for (let k = 0; k < n; k++) out.push([z0 + L * (k + 0.5), L / nominal]);
  return out;
}
// (outboard origin 1.5 mm under the band so the filler-panel joint strips never poke through a well)
const psuXF = (x, z) => Math.abs(x) < 1.1 ? M4.trs(x, CBIN_Y - 0.009, z) : M4.trs(x, binBottomY(x) - 0.0065, z, 0, 0, -TILT_O * Math.sign(x));
// row placard on the outboard door's top rail, above the latch (py_37302, c_th1, b_sany_y22 [V])
function placardXF(group, z) {
  const out = [];
  if (group !== 1) { const s = group === 0 ? -1 : 1, [x, y, tx, ty] = faceAtY(OBIN_DOOR, 2.19); out.push(faceM(x * s, y, tx * s, ty, z, -s, 0.0105)); }
  else { const [x, y, tx, ty] = faceAtY(CBIN_DOOR, 2.19); for (const s of [-1, 1]) out.push(faceM((x + 0.006) * s, y, tx * s, ty, z, s, 0.0015)); }
  return out;
}

function buildBins(gl, layout) {
  const zones = layout.zones.filter((z) => z.type === 'seat');
  const side = [], center = [], seamO = [], seamC = [];
  for (const zn of zones) {
    fitModules(zn.z0, zn.z1, BIN.side).forEach(([zc, s], k) => { side.push(M4.trs(0, 0, zc, 0, 0, 0, 1, 1, s)); if (k) seamO.push(M4.trs(0, 0, zc - BIN.side * s / 2)); });
    fitModules(zn.z0, zn.z1, BIN.center).forEach(([zc, s], k) => { center.push(M4.trs(0, 0, zc, 0, 0, 0, 1, 1, s)); if (k) seamC.push(M4.trs(0, 0, zc - BIN.center * s / 2)); });
  }
  const meshes = {
    binR: gl.mesh(sideBinModule(1), { name: 'binR', layer: 'upper', instances: side }),
    binL: gl.mesh(sideBinModule(-1), { name: 'binL', layer: 'upper', instances: side }),
    binC: gl.mesh(centerBinModule(), { name: 'binC', layer: 'upper', instances: center }),
    seamR: gl.mesh(binSeams('R'), { name: 'seamR', layer: 'upper', instances: seamO, castShadow: false }),
    seamL: gl.mesh(binSeams('L'), { name: 'seamL', layer: 'upper', instances: seamO, castShadow: false }),
    seamC: gl.mesh(binSeams('C'), { name: 'seamC', layer: 'upper', instances: seamC, castShadow: false }),
  };
  // ---- PSUs: outboard a raised box per window bay in every cabin (c_27312 shows the same per-bay row of round
  // fittings under the J outboard bins [V]); centre a unit per seat group per row ----
  const psu = {}, box = [[], []];
  const inSeatZone = (z) => zones.some((zn) => z > zn.z0 + 0.15 && z < zn.z1 - 0.15);
  for (const w of layout.windows) if (inSeatZone(w.z)) box[Math.round(w.z / CAB.win.pitch) & 1].push(psuXF(PSU_BOX_X * w.side, w.z));
  const byRow = {};
  for (const s of layout.seats) (byRow[s.row] = byRow[s.row] || []).push(s);
  for (const ss of Object.values(byRow)) {
    const b = ss.filter((s) => Math.abs(s.x) <= 1.1);
    if (!b.length) continue;
    const k0 = b[0].kind, fj = k0 === 'room' || k0 === 'suite';
    const n = fj ? 2 : Math.min(4, b.length);
    const z = k0 === 'econ' ? b[0].z - 0.45 : k0 === 'py' ? b[0].z - 0.5 : b[0].z;
    const key = (fj ? 'o' : 'c') + n;
    // F/J centre units (one 2-fitting unit per seat) sit inside the 0.60 m channel
    for (const x of fj ? [-0.15, 0.15] : [0]) (psu[key] = psu[key] || []).push(psuXF(x, z));
  }
  for (const [key, inst] of Object.entries(psu)) meshes['psu' + key] = gl.mesh(psuModule(+key.slice(1), key[0] === 'c' ? PSU_C_PITCH : 0.06), { name: 'psu' + key, layer: 'upper', instances: inst, castShadow: false });
  meshes.psuBox = gl.mesh(psuBoxModule(false), { name: 'psuBox', layer: 'upper', instances: box[0], castShadow: false });
  meshes.psuAir = gl.mesh(psuBoxModule(true), { name: 'psuAir', layer: 'upper', instances: box[1], castShadow: false });
  // sign pods on the outboard bands, one per seat row with outboard seats, just aft of the row placard z
  const pods = [];
  for (const ss of Object.values(byRow)) for (const sd of [-1, 1]) {
    const o = ss.filter((s) => s.x * sd > 1.1);
    if (!o.length) continue;
    const k0 = o[0].kind, z = (k0 === 'econ' ? o[0].z - 0.45 : k0 === 'py' ? o[0].z - 0.5 : o[0].z) + 0.12;
    pods.push(psuXF(SIGN_POD_X * sd, z));
  }
  meshes.signPods = gl.mesh(signPodModule(), { name: 'signPods', layer: 'upper', instances: pods, castShadow: false });

  // ---- row placards (~0.8 of the latch width, py_37302 / c_27312 [V ratio]) ----
  const D = new Builder();
  for (const [row, ss] of Object.entries(byRow)) {
    const k0 = ss[0].kind;
    const z = k0 === 'econ' ? ss[0].z - 0.34 : k0 === 'py' ? ss[0].z - 0.4 : ss[0].z;
    const groups = [ss.filter((s) => s.x < -1.1), ss.filter((s) => Math.abs(s.x) <= 1.1), ss.filter((s) => s.x > 1.1)];
    groups.forEach((gr, i) => {
      const name = `row${row}_${i}`;
      if (!gr.length || !ATL.rects[name]) return;
      for (const m of placardXF(i, z)) D.add(gQuad(PLACARD[0], PLACARD[1]), m, MAT.decal, atlasUV(name));
    });
  }
  meshes.placards = gl.mesh(D.build(), { name: 'placards', layer: 'upper', castShadow: false });
  return meshes;
}
// sign pods 0.2 m aisle-side of the per-bay PSU wells so the two never overlap; centre fittings 75 mm apart so a
// 4-seat well is ~0.28 m, ~0.7 of the 0.40 m usable channel (b_sany_y22 [V ratio, A pitch])
const PSU_BOX_X = 2.15, PSU_C_PITCH = 0.075, PLACARD = [0.15, 0.036], SIGN_POD_X = PSU_BOX_X - 0.2;

// studio slice: two outboard modules a side, four centre modules, aisle ceilings, Y-style PSUs and placards
function ceilingSlice() {
  const B = new Builder();
  const L = 2 * BIN.center;
  buildCeilings(B, { zones: [{ type: 'seat', z0: -L, z1: L, cls: 'Y' }], seats: [] });
  const side = { R: sideBinModule(1), L: sideBinModule(-1), C: centerBinModule() };
  const seam = { R: binSeams('R'), L: binSeams('L'), C: binSeams('C') };
  for (const zc of [-1.5, -0.5, 0.5, 1.5]) for (const k of ['R', 'L', 'C']) B.addBuilt(side[k], M4.trs(0, 0, zc * BIN.center));
  for (const zc of [-1, 0, 1]) for (const k of ['R', 'L', 'C']) B.addBuilt(seam[k], M4.trs(0, 0, zc * BIN.center));
  const pb = [psuBoxModule(false), psuBoxModule(true)];
  for (let k = -3.5; k <= 3.5; k++) for (const x of [-PSU_BOX_X, PSU_BOX_X]) B.addBuilt(pb[(k + 3.5) & 1], psuXF(x, k * CAB.win.pitch));
  for (const z of [-0.9, -0.036, 0.828]) {
    B.addBuilt(psuModule(4), psuXF(0, z));
    for (const x of [-SIGN_POD_X, SIGN_POD_X]) B.addBuilt(signPodModule(), psuXF(x, z + 0.12));
  }
  for (const [g, name] of [[0, 'row31_0'], [1, 'row31_1'], [2, 'row31_2']]) if (ATL.rects[name]) for (const m of placardXF(g, 0.1)) B.add(gQuad(PLACARD[0], PLACARD[1]), m, MAT.decal, atlasUV(name));
  return B.build();
}
