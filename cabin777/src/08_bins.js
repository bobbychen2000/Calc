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
const CBIN_Q = [[0.42, 1.835], [0.60, 1.86], [0.75, 1.93], [0.825, 2.03], [0.82, 2.12], [0.78, 2.2], [0.725, 2.262], [0.62, 2.30], [0, 2.315]];
const CBIN_DOOR = CBIN_Q.slice(0, 7);
const CBIN_Y = 1.835, CBIN_BAND = 0.84;
const TILT_O = Math.atan2(1.795 - 1.60, 2.845 - 1.53);
// door skin slightly cool (photo samples of lit door faces ~#eeeeed, shaded ones #b4b8be..#bfc5cb) [V colour]
const BINMAT = {
  door: { c: '#e3e5e8', r: 0.34, l: LAYER.plastic },
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
function addDoor(B, face, L, xs, inward) {
  B.add(gExtrude(faceShell(face, xs, inward, 0.006, 0.004), L - 0.012, 25), null, BINMAT.door);
}
const doorSeam = (B, face, xs, inward, z = 0) => B.add(gExtrude(faceShell(face, xs, inward, 0.004, 0.002), 0.013, 25), M4.trs(0, 0, z), BINMAT.seam);
// baked shading for the bins (the shader's hemisphere fill leaves them flat): down-facing surfaces x0.95..0.88,
// aisle-facing door faces x0.93, calibrated on photo samples (y_47301 door #c7c6cb..#dcdcdc, bin bottom #c0c3c8,
// py_37302 door #b2bcc6, vault #f0f1ef) [D factors]
function shadeUpper(geo) {
  const { nrm, col } = geo;
  for (let k = 0; k < nrm.length / 3; k++) {
    const ny = nrm[k * 3 + 1];
    const f = ny < -0.3 ? lerp(0.95, 0.88, clamp((-ny - 0.3) / 0.5, 0, 1)) : ny < 0.5 ? 0.93 : 1;
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
    addDoor(B, CBIN_DOOR, L, s, -1);
    addLatch(B, faceM((hx + 0.006) * s, hy, htx * s, hty, 0, s));
    B.add(gBox(0.05, 0.01, L - 0.03), M4.trs(0.70 * s, 2.268, 0), MAT.led);
    // dark gap between the wrapped door edge and the PSU channel (the two converging lines in y_47300)
    B.add(gBox(0.012, 0.002, L), M4.trs(0.425 * s, CBIN_Y - 0.0065, 0), BINMAT.lipGap);
  }
  B.add(gBox(CBIN_BAND, 0.004, L - 0.004), M4.trs(0, CBIN_Y - 0.0045, 0), BINMAT.band);
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

// PSU for one seat group (built flat, hanging from y=0): per seat a reading-light pod (oval housing, lens,
// switch) and a gasper in a round bezel behind it (the two transverse rows in y_47300); call button,
// signs, oxygen-mask door and a speaker grille on the panel. pitch = seat-to-seat spacing of the units.
function psuModule(n, lights = true, pitch = 0.15) {
  const B = new Builder();
  const w = Math.max(0.26, (n - 1) * pitch + 0.16);
  B.add(gRBox(w, 0.012, 0.36, 0.006, 1), M4.trs(0, -0.002, 0.02), BINMAT.band);
  for (let k = 0; k < n; k++) {
    const x = (k - (n - 1) / 2) * pitch;
    if (lights) {
      B.add(gCyl(0.025, 0.025, 0.012, 12), M4.trs(x, -0.012, -0.10, 0, 0, 0, 2.2, 1, 1), BINMAT.pod);
      B.add(gCyl(0.017, 0.017, 0.006, 8), M4.trs(x - 0.025, -0.017, -0.10), MAT.lens);
      B.add(gBox(0.018, 0.004, 0.012), M4.trs(x + 0.03, -0.0175, -0.10), BINMAT.bezelDark);
    }
    B.add(gCyl(0.03, 0.03, 0.006, 10), M4.trs(x, -0.010, -0.02), BINMAT.pod);
    B.add(gCyl(0.017, 0.021, 0.018, 8), M4.trs(x, -0.020, -0.02), MAT.nozzle);
    B.add(gCyl(0.007, 0.007, 0.006, 6), M4.trs(x, -0.030, -0.02), MAT.darkPlastic);
  }
  B.add(gBox(0.028, 0.006, 0.02), M4.trs(w / 2 - 0.04, -0.009, 0.05), BINMAT.call);
  B.add(gQuad(0.105, 0.048), M4.trs(0, -0.0085, 0.065, 0, Math.PI / 2), { ...MAT.exitGlow, e: 0.35 }, atlasUV('psuSigns'));
  // oxygen-mask door: flush panel with a hairline gap
  const ow = Math.min(w - 0.04, 0.34);
  B.add(gBox(ow + 0.006, 0.001, 0.106), M4.trs(0, -0.0085, 0.15), BINMAT.o2gap);
  B.add(gBox(ow, 0.001, 0.1), M4.trs(0, -0.0092, 0.15), BINMAT.band);
  if (w > 0.4) B.add(gCyl(0.028, 0.028, 0.003, 10), M4.trs(-w / 2 + 0.05, -0.009, 0.06), BINMAT.grille);
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
const PSU_BOX_X = 2.15, PSU_C_PITCH = 0.2, PLACARD = [0.115, 0.032];

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
  for (const z of [-0.9, -0.036, 0.828]) B.addBuilt(psuModule(4, true, PSU_C_PITCH), psuXF(0, z));
  for (const [g, name] of [[0, 'row31_0'], [1, 'row31_1'], [2, 'row31_2']]) if (ATL.rects[name]) for (const m of placardXF(g, 0.1)) B.add(gQuad(PLACARD[0], PLACARD[1]), m, MAT.decal, atlasUV(name));
  return B.build();
}
