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
const BIN = { side: 2 * CAB.win.pitch, center: 2 * CAB.win.pitch };
const binBottomY = (x) => { const ax = Math.abs(x); return lerp(1.60, 1.795, clamp((2.845 - ax) / (2.845 - 1.53), 0, 1)); };
// outboard door face, lip -> ceiling crease: more upright than SIDEBIN so the latch and placard face the aisle
// as in py_37302 / y_47301 (the whole door is seen up to the ceiling line) [A shape]
const OBIN_DOOR = [[1.53, 1.795], [1.495, 1.83], [1.472, 1.93], [1.469, 2.03], [1.479, 2.115], [1.508, 2.178], [1.56, 2.214], [1.64, 2.228]];
const OBIN = [SIDEBIN[0], ...OBIN_DOOR, ...SIDEBIN.slice(8)];
// centre bin section used by the bins (07_shell's CBIN is only consumed here): the lower door wraps under to a
// narrow PSU channel (|x| < 0.42, ~70 % of the channel between the door edges in y_47300 [V]; the door-edge lines
// slope ~0.57 px/px toward the vanishing point there) [A ordinates]; top points unchanged so the vault still meets
// the bin at (0.725, 2.262). Aisle-edge headroom rises (x 0.75 at y 1.93 instead of 0.795 at 1.845).
// The 7 door ordinates are resampled with a Catmull-Rom spline (3 steps a span, 19 points) so the wrap shades
// smoothly as the real doors do (y_47301, c_27312 [V]); end points (0.42, 1.835) and (0.725, 2.262) kept.
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
const CBIN_DOOR = crResample([[0.42, 1.835], [0.60, 1.86], [0.75, 1.93], [0.825, 2.03], [0.82, 2.12], [0.78, 2.2], [0.725, 2.262]]);
const CBIN_Q = [...CBIN_DOOR, [0.62, 2.30], [0, 2.315]];
const CBIN_Y = 1.835, CBIN_BAND = 0.84;
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
  seam: { c: '#3d4147', r: 0.8 },
  lipGap: { c: '#4a4f56', r: 0.8 },
  lip: { c: '#e2e2df', r: 0.36, l: LAYER.plastic },
  bezel: { c: '#d3d5d6', r: 0.4 },
  recess: { c: '#3c4046', r: 0.6 },
  paddle: { c: '#c4c8cc', r: 0.4 },
  band: { c: '#e4e3df', r: 0.5, l: LAYER.plastic, e: 0.05 },
  joint: { c: '#dcdedf', r: 0.7 },
  psuBox: { c: '#e6e6e3', r: 0.4, l: LAYER.plastic },
  pod: { c: '#eceae6', r: 0.4, l: LAYER.plastic },
  bezelDark: { c: '#8a9096', r: 0.4 },
  call: { c: '#6f8fb8', r: 0.4 },
  o2gap: { c: '#b2b6ba', r: 0.7 },
  grille: { c: '#9ea3a8', r: 0.6, l: LAYER.grille },
};

// Bin decals painted over 06_atlas's versions of the same rects (these decals are only used here; the atlas is
// uploaded right after buildAtlas, before the bins are built):
//  - row placards: small dark-grey numerals and seat pictograms printed straight on the white door top edge, no plate
//    (py_37302 '25 ..' above the latch, sany_11 / sany_12 '25' / '31' + seat icons on the lip [V]); ink #4a4f57,
//    numeral 19 px bold [A]. The 76x30 px rect is stretched onto a PLACARD (0.115 x 0.032 m, 3.6:1) quad, so the
//    content is drawn pre-squeezed in x. Centre-bin placards get a lighter ground to match the self-lit centre door.
//  - psuSigns: dark ground, no-smoking icon red-orange #ff5a2a, fasten-belt icon amber #ffa634 (sany_15 [V colours])
function paintBinDecals(A, layout) {
  const g = A.canvas.getContext('2d'), S = A.canvas.width;
  const rect = (name) => { const r = A.rects[name]; return r && [r[0] * S, r[1] * S, (r[2] - r[0]) * S, (r[3] - r[1]) * S]; };
  const INK = '#4a4f57';
  const seatIcon = (x, y, s) => {          // seat pictogram: backrest + cushion as rounded squares
    g.beginPath(); g.roundRect(x, y - s * 0.5, s * 0.34, s, s * 0.12); g.fill();
    g.beginPath(); g.roundRect(x + s * 0.2, y + s * 0.12, s * 0.7, s * 0.38, s * 0.12); g.fill();
  };
  const rows = [...new Set(layout.seats.map((s) => s.row))];
  for (const r of rows) for (let i = 0; i < 3; i++) {
    const q = rect(`row${r}_${i}`);
    if (!q) continue;
    const [x, y, w, h] = q, sx = (w / h) / (PLACARD[0] / PLACARD[1]);
    g.fillStyle = i === 1 ? '#f6f7f9' : '#e3e5e8'; g.fillRect(x, y, w, h);
    const n = layout.seats.filter((s) => s.row === r && (i === 1 ? Math.abs(s.x) <= 1.1 : i === 0 ? s.x < -1.1 : s.x > 1.1)).length;
    g.save(); g.translate(x, y); g.scale(sx, 1);
    const W = w / sx;                         // virtual width before the quad stretch
    g.fillStyle = INK; g.textAlign = 'left'; g.textBaseline = 'middle'; g.font = '700 19px "Helvetica Neue", Helvetica, Arial, sans-serif';
    const tw = g.measureText(String(r)).width, ic = 11, gap = 3;
    const total = tw + 6 + Math.min(n, 4) * (ic + gap);
    let cx = (W - total) / 2;
    g.fillText(String(r), cx, h / 2 + 1); cx += tw + 6;
    for (let k = 0; k < Math.min(n, 4); k++) { seatIcon(cx, h / 2, ic); cx += ic + gap; }
    g.restore();
  }
  const q = rect('psuSigns');
  if (q) {
    const [x, y, w, h] = q;
    g.fillStyle = '#0c0f13'; g.fillRect(x, y, w, h);
    g.lineCap = 'round';
    // no smoking: cigarette with smoke, ringed and struck through
    g.strokeStyle = g.fillStyle = '#ff5a2a'; g.lineWidth = 4;
    g.beginPath(); g.arc(x + 34, y + 32, 22, 0, Math.PI * 2); g.stroke();
    g.fillRect(x + 20, y + 30, 22, 6); g.fillRect(x + 44, y + 30, 4, 6);
    g.beginPath(); g.moveTo(x + 18, y + 16); g.lineTo(x + 50, y + 48); g.stroke();
    // fasten seat belt: buckle with two belt halves
    g.strokeStyle = g.fillStyle = '#ffa634';
    g.beginPath(); g.moveTo(x + 80, y + 32); g.lineTo(x + 97, y + 32); g.moveTo(x + 111, y + 32); g.lineTo(x + 128, y + 32); g.stroke();
    g.beginPath(); g.roundRect(x + 94, y + 24, 20, 16, 4); g.fill();
    g.fillStyle = '#0c0f13'; g.fillRect(x + 99, y + 29, 10, 6);
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
// recessed pill latch (light bezel, dark recess, lever paddle in its lower half) as in the ANA photos [V shape];
// bezel set 1 mm into the door skin so it reads recessed, not proud (no photo shows a raised latch) [A]
function addLatch(B, M) {
  B.add(gRBox(0.14, 0.05, 0.006, 0.024, 1), M4.mul(M, M4.trs(0, 0, -0.001)), BINMAT.bezel);
  B.add(gRBox(0.114, 0.028, 0.004, 0.013, 1), M4.mul(M, M4.trs(0, 0.002, 0.0007)), BINMAT.recess);
  B.add(gBox(0.1, 0.011, 0.004), M4.mul(M, M4.trs(0, -0.0055, 0.0019)), BINMAT.paddle);
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
  B.add(gExtrude(faceShell(face, xs, inward, 0.006, 0.004), L - 0.012, 25), null, mat);
}
const doorSeam = (B, face, xs, inward, z = 0) => B.add(gExtrude(faceShell(face, xs, inward, 0.004, 0.002), 0.013, 25), M4.trs(0, 0, z), BINMAT.seam);
// baked shading for the bins (the shader's hemisphere fill leaves them flat): down-facing surfaces x0.99..0.95,
// aisle-facing door faces x0.97, calibrated on photo samples (y_47301 door #c7c6cb..#dcdcdc, bin bottom #c0c3c8,
// centre bin #c2c3c7; c_27312 centre bin #c3c7cb; py_37302 door #b2bcc6, vault #f0f1ef) [D factors; r2 raised
// from 0.95..0.88 / 0.93, which rendered the centre bins 40-90 levels too dark]
function shadeUpper(geo) {
  const { nrm, col } = geo;
  for (let k = 0; k < nrm.length / 3; k++) {
    const ny = nrm[k * 3 + 1];
    const f = ny < -0.3 ? lerp(0.99, 0.95, clamp((-ny - 0.3) / 0.5, 0, 1)) : ny < 0.5 ? 0.97 : 1;
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
  // PSU band over the bin bottom, subtle filler-panel joints 3 per bay (y_47301 shows many narrow panels) [A pitch]
  const bw = 1.19, bx = 2.155, by = binBottomY(bx) - 0.003;
  B.add(gBox(bw, 0.004, L - 0.004), M4.trs(bx * side, by, 0, 0, 0, -TILT_O * side), BINMAT.band);
  for (let k = 0; k < 6; k++) B.add(gBox(bw - 0.02, 0.002, 0.0015), M4.trs(bx * side, by - 0.0025, -L / 2 + (k + 0.5) * L / 6, 0, 0, -TILT_O * side), BINMAT.joint);
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
    B.add(gBox(0.05, 0.01, L - 0.03), M4.trs(0.70 * s, 2.268, 0), MAT.led);
    // dark gap between the wrapped door edge and the PSU channel (the two converging lines in y_47300)
    B.add(gBox(0.012, 0.002, L), M4.trs(0.425 * s, CBIN_Y - 0.0065, 0), BINMAT.lipGap);
  }
  B.add(gBox(CBIN_BAND, 0.004, L - 0.004), M4.trs(0, CBIN_Y - 0.0045, 0), BINMAT.bandC);
  for (let k = 0; k < 8; k++) B.add(gBox(CBIN_BAND - 0.03, 0.002, 0.0015), M4.trs(0, CBIN_Y - 0.0075, -L / 2 + (k + 0.5) * L / 8), BINMAT.joint);
  return shadeUpper(B.build());
}
// seams between neighbouring modules (instanced at the joints only, so no dark outline at the run ends)
function binSeams(which) {
  const B = new Builder();
  if (which === 'C') for (const s of [-1, 1]) doorSeam(B, CBIN_DOOR, s, -1);
  else doorSeam(B, OBIN_DOOR, which === 'R' ? 1 : -1, 1);
  return B.build();
}

// PSU for one seat group (built flat, hanging from y=0): two slim near-flush transverse rows as in y_47300 [V]:
// oval reading lights on a linked light rail, then small gaspers in round bezels; no raised base plate (none in
// the photo). Nothing hangs more than 15 mm [A depths]. Call button, signs, oxygen-mask door and a speaker grille
// flush on the channel. pitch = seat-to-seat spacing of the units.
function psuModule(n, lights = true, pitch = 0.15) {
  const B = new Builder();
  const w = Math.max(0.26, (n - 1) * pitch + 0.16);
  if (lights) B.add(gRBox(w, 0.006, 0.035, 0.003, 1), M4.trs(0, -0.003, -0.10), BINMAT.pod);
  for (let k = 0; k < n; k++) {
    const x = (k - (n - 1) / 2) * pitch;
    if (lights) {
      B.add(gCyl(0.02, 0.02, 0.008, 12), M4.trs(x, -0.007, -0.10, 0, 0, 0, 2.4, 1, 1), BINMAT.pod);
      B.add(gCyl(0.013, 0.013, 0.004, 10), M4.trs(x - 0.02, -0.0105, -0.10), MAT.lens);
      B.add(gBox(0.014, 0.003, 0.010), M4.trs(x + 0.028, -0.0105, -0.10), BINMAT.bezelDark);
    }
    B.add(gCyl(0.022, 0.022, 0.004, 12), M4.trs(x, -0.002, -0.02), BINMAT.pod);
    B.add(gCyl(0.013, 0.016, 0.010, 10), M4.trs(x, -0.009, -0.02), MAT.nozzle);
    B.add(gCyl(0.005, 0.005, 0.002, 6), M4.trs(x, -0.0142, -0.02), MAT.darkPlastic);
  }
  B.add(gBox(0.028, 0.004, 0.02), M4.trs(w / 2 - 0.04, -0.002, 0.05), BINMAT.call);
  B.add(gQuad(0.105, 0.048), M4.trs(0, -0.0012, 0.065, 0, Math.PI / 2), { ...MAT.exitGlow, e: 0.6 }, atlasUV('psuSigns'));
  // oxygen-mask door: flush panel with a hairline gap
  const ow = Math.min(w - 0.04, 0.34);
  B.add(gBox(ow + 0.006, 0.001, 0.106), M4.trs(0, -0.0005, 0.15), BINMAT.o2gap);
  B.add(gBox(ow, 0.001, 0.1), M4.trs(0, -0.0012, 0.15), BINMAT.band);
  if (w > 0.4) B.add(gCyl(0.028, 0.028, 0.002, 10), M4.trs(-w / 2 + 0.05, -0.001, 0.06), BINMAT.grille);
  return B.build();
}
// no-smoking / fasten-belt sign pod on the outboard PSU band once per seat row: dark housing with the lit icon pair
// (sany_15 from 35B: dark oval housing, red-orange cigarette + amber belt icons over the outboard block [V];
// 0.12 x 0.05 m [A])
function signPodModule() {
  const B = new Builder();
  B.add(gRBox(0.12, 0.012, 0.05, 0.02, 2), M4.trs(0, -0.004, 0), BINMAT.signPod);
  B.add(gQuad(0.10, 0.042), M4.trs(0, -0.0102, 0, 0, Math.PI / 2), { ...MAT.exitGlow, e: 0.6 }, atlasUV('psuSigns'));
  return B.build();
}

// outboard PSU: raised light-grey housing (~0.16 m) with one round gasper face and one reading lens, once per
// window bay (py_37302: 5 boxes under two bin modules; y_47301: one per bay) [V]; sizes [A]
function psuBoxModule() {
  const B = new Builder();
  B.add(gRBox(0.16, 0.03, 0.14, 0.012, 1), M4.trs(0, -0.013, 0), BINMAT.psuBox);
  B.add(gCyl(0.034, 0.034, 0.006, 14), M4.trs(-0.028, -0.029, 0.005), BINMAT.pod);
  B.add(gCyl(0.022, 0.024, 0.012, 10), M4.trs(-0.028, -0.034, 0.005), MAT.nozzle);
  B.add(gCyl(0.007, 0.007, 0.006, 6), M4.trs(-0.028, -0.041, 0.005), MAT.darkPlastic);
  B.add(gRBox(0.05, 0.004, 0.034, 0.012, 1), M4.trs(0.045, -0.0285, -0.02), BINMAT.bezelDark);
  B.add(gCyl(0.013, 0.013, 0.004, 10), M4.trs(0.045, -0.031, -0.02), MAT.lens);
  B.add(gBox(0.016, 0.004, 0.012), M4.trs(0.045, -0.029, 0.035), BINMAT.bezelDark);
  return B.build();
}

function fitModules(z0, z1, nominal) {
  const n = Math.max(1, Math.round((z1 - z0) / nominal));
  const L = (z1 - z0) / n, out = [];
  for (let k = 0; k < n; k++) out.push([z0 + L * (k + 0.5), L / nominal]);
  return out;
}
const psuXF = (x, z) => Math.abs(x) < 1.1 ? M4.trs(x, CBIN_Y - 0.007, z) : M4.trs(x, binBottomY(x) - 0.005, z, 0, 0, -TILT_O * Math.sign(x));
// row placard high on the door face, above the latch (py_37302: "25 ..." at the top edge of each door) [V]
function placardXF(group, z) {
  const out = [];
  if (group !== 1) { const s = group === 0 ? -1 : 1, [x, y, tx, ty] = faceAtY(OBIN_DOOR, 2.165); out.push(faceM((x - 0.006) * s, y, tx * s, ty, z, -s, 0.0015)); }
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
  const psu = {}, box = [];
  const inSeatZone = (z) => zones.some((zn) => z > zn.z0 + 0.15 && z < zn.z1 - 0.15);
  for (const w of layout.windows) if (inSeatZone(w.z)) box.push(psuXF(PSU_BOX_X * w.side, w.z));
  const byRow = {};
  for (const s of layout.seats) (byRow[s.row] = byRow[s.row] || []).push(s);
  for (const ss of Object.values(byRow)) {
    const b = ss.filter((s) => Math.abs(s.x) <= 1.1);
    if (!b.length) continue;
    const k0 = b[0].kind, fj = k0 === 'room' || k0 === 'suite';
    const n = fj ? 1 : Math.min(4, b.length);
    const z = k0 === 'econ' ? b[0].z - 0.45 : k0 === 'py' ? b[0].z - 0.5 : b[0].z;
    const key = (fj ? 'o' : 'c') + n;
    // F/J centre units (one per seat) sit inside the 0.84 m channel
    for (const x of fj ? [-0.25, 0.25] : [0]) (psu[key] = psu[key] || []).push(psuXF(x, z));
  }
  // centre-row unit pitch 0.20 m: 4 units span ~0.76 m, ~70 % of the channel width in y_47300 [V ratio, A pitch]
  for (const [key, inst] of Object.entries(psu)) meshes['psu' + key] = gl.mesh(psuModule(+key.slice(1), true, key[0] === 'c' ? PSU_C_PITCH : 0.15), { name: 'psu' + key, layer: 'upper', instances: inst, castShadow: false });
  meshes.psuBox = gl.mesh(psuBoxModule(), { name: 'psuBox', layer: 'upper', instances: box, castShadow: false });
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
// sign pods 0.2 m aisle-side of the per-bay PSU boxes so the two never overlap [A]
const PSU_BOX_X = 2.15, PSU_C_PITCH = 0.2, PLACARD = [0.115, 0.032], SIGN_POD_X = PSU_BOX_X - 0.2;

// studio slice: two outboard modules a side, four centre modules, aisle ceilings, Y-style PSUs and placards
function ceilingSlice() {
  const B = new Builder();
  const L = 2 * BIN.center;
  buildCeilings(B, { zones: [{ type: 'seat', z0: -L, z1: L, cls: 'Y' }], seats: [] });
  const side = { R: sideBinModule(1), L: sideBinModule(-1), C: centerBinModule() };
  const seam = { R: binSeams('R'), L: binSeams('L'), C: binSeams('C') };
  for (const zc of [-1.5, -0.5, 0.5, 1.5]) for (const k of ['R', 'L', 'C']) B.addBuilt(side[k], M4.trs(0, 0, zc * BIN.center));
  for (const zc of [-1, 0, 1]) for (const k of ['R', 'L', 'C']) B.addBuilt(seam[k], M4.trs(0, 0, zc * BIN.center));
  for (let k = -3.5; k <= 3.5; k++) for (const x of [-PSU_BOX_X, PSU_BOX_X]) B.addBuilt(psuBoxModule(), psuXF(x, k * CAB.win.pitch));
  for (const z of [-0.9, -0.036, 0.828]) {
    B.addBuilt(psuModule(4, true, PSU_C_PITCH), psuXF(0, z));
    for (const x of [-SIGN_POD_X, SIGN_POD_X]) B.addBuilt(signPodModule(), psuXF(x, z + 0.12));
  }
  for (const [g, name] of [[0, 'row31_0'], [1, 'row31_1'], [2, 'row31_2']]) if (ATL.rects[name]) for (const m of placardXF(g, 0.1)) B.add(gQuad(PLACARD[0], PLACARD[1]), m, MAT.decal, atlasUV(name));
  return B.build();
}
