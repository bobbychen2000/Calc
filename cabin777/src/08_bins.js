// ------------------------------------------------------------------
// Overhead bins (777 Signature Interior, checked against ANA's official photos y_47300/47301, py_37302,
// c_27312 and a THE Suite aisle photo [V]): outboard pivot bins (4-frame modules) with a near-upright
// convex door, recessed pill latch 1/3 down the door, row placard above it, single dark seam per joint;
// double-sided centre bins (2-frame) with the same latch; PSU band on the bin bottoms with filler-panel
// joints, per-seat reading-light / gasper pods, call button, signs, O2 door [A details]
// ------------------------------------------------------------------
const BIN = { side: 4 * CAB.win.pitch, center: 2 * CAB.win.pitch };
const binBottomY = (x) => { const ax = Math.abs(x); return lerp(1.60, 1.795, clamp((2.845 - ax) / (2.845 - 1.53), 0, 1)); };
// outboard door face, lip -> ceiling crease: more upright than SIDEBIN so the latch and placard face the aisle
// as in py_37302 / y_47301 (the whole door is seen up to the ceiling line) [A shape]
const OBIN_DOOR = [[1.53, 1.795], [1.495, 1.83], [1.472, 1.93], [1.469, 2.03], [1.479, 2.115], [1.508, 2.178], [1.56, 2.214], [1.64, 2.228]];
const OBIN = [SIDEBIN[0], ...OBIN_DOOR, ...SIDEBIN.slice(8)];
const CBIN_DOOR = CBIN.slice(0, 6);
const TILT_O = Math.atan2(1.795 - 1.60, 2.845 - 1.53);
const BINMAT = {
  seam: { c: '#3d4147', r: 0.8 },
  lipGap: { c: '#4a4f56', r: 0.8 },
  lip: { c: '#e2e2df', r: 0.36, l: LAYER.plastic },
  bezel: { c: '#d3d5d6', r: 0.4 },
  recess: { c: '#3c4046', r: 0.6 },
  paddle: { c: '#c4c8cc', r: 0.4 },
  band: { c: '#e4e3df', r: 0.5, l: LAYER.plastic, e: 0.05 },
  joint: { c: '#cbced1', r: 0.7 },
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
// recessed pill latch (light bezel, dark recess, lever paddle in its lower half) as in the ANA photos [V shape]
function addLatch(B, M) {
  B.add(gRBox(0.14, 0.05, 0.006, 0.024, 1), M4.mul(M, M4.trs(0, 0, 0.0005)), BINMAT.bezel);
  B.add(gRBox(0.114, 0.028, 0.004, 0.013, 1), M4.mul(M, M4.trs(0, 0.002, 0.0022)), BINMAT.recess);
  B.add(gBox(0.1, 0.011, 0.004), M4.mul(M, M4.trs(0, -0.0055, 0.0034)), BINMAT.paddle);
}
// door skin + one seam per module (at -L/2; the neighbour's +L/2 end meets it) on a face polyline
function addDoor(B, face, L, xs, inward) {
  const skin = [...face.map(([x, y]) => [(x - 0.006 * inward) * xs, y]), ...face.slice().reverse().map(([x, y]) => [(x + 0.004 * inward) * xs, y])];
  B.add(gExtrude(skin, L - 0.012, 25), null, MAT.binDoor);
  const gap = [...face.map(([x, y]) => [(x - 0.004 * inward) * xs, y]), ...face.slice().reverse().map(([x, y]) => [(x + 0.002 * inward) * xs, y])];
  B.add(gExtrude(gap, 0.013, 25), M4.trs(0, 0, -L / 2), BINMAT.seam);
}

function sideBinModule(side) {
  const L = BIN.side;
  const B = new Builder();
  B.add(gExtrude(OBIN.map(([x, y]) => [x * side, y]), L - 0.006, 20), null, MAT.bin);
  addDoor(B, OBIN_DOOR, L, side, 1);
  // bottom edge lip of the door + dark gap line to the PSU band
  B.add(gRBox(0.028, 0.016, L - 0.014, 0.007, 1), M4.trs(1.516 * side, 1.804, 0), BINMAT.lip);
  B.add(gBox(0.012, 0.002, L), M4.trs(1.548 * side, binBottomY(1.548) - 0.0015, 0, 0, 0, -TILT_O * side), BINMAT.lipGap);
  // latch 1/3 down the door (py_37302), module centre
  const [hx, hy, htx, hty] = faceAtY(OBIN_DOOR, 2.065);
  addLatch(B, faceM((hx - 0.006) * side, hy, htx * side, hty, 0, -side));
  // PSU band over the bin bottom, filler-panel joints every 1/12 module (y_47301 shows many narrow panels) [A pitch]
  const bw = 1.19, bx = 2.155, by = binBottomY(bx) - 0.003;
  B.add(gBox(bw, 0.004, L - 0.004), M4.trs(bx * side, by, 0, 0, 0, -TILT_O * side), BINMAT.band);
  for (let k = 0; k < 12; k++) B.add(gBox(bw - 0.02, 0.002, 0.003), M4.trs(bx * side, by - 0.0025, -L / 2 + (k + 0.5) * L / 12, 0, 0, -TILT_O * side), BINMAT.joint);
  // cove LED along the top inner edge (washes the aisle panel) + sidewall wash lens under the bin
  B.add(gBox(0.05, 0.01, L - 0.03), M4.trs(1.70 * side, 2.238, 0), MAT.led);
  B.add(gBox(0.045, 0.006, L - 0.03), M4.trs(2.80 * side, 1.607, 0, 0, 0, side * 0.12), { c: '#ffffff', r: 0.4, l: 12, e: 0.35 });
  return B.build();
}
function centerBinModule() {
  const L = BIN.center;
  const B = new Builder();
  const poly = [...CBIN.map(([x, y]) => [x, y]), ...CBIN.slice(0, -1).reverse().map(([x, y]) => [-x, y])];
  B.add(gExtrude(poly, L - 0.006, 20), null, MAT.bin);
  const [hx, hy, htx, hty] = faceAtY(CBIN_DOOR, 2.09);
  for (const s of [-1, 1]) {
    addDoor(B, CBIN_DOOR, L, s, -1);
    addLatch(B, faceM((hx + 0.006) * s, hy, htx * s, hty, 0, s));
    B.add(gBox(0.05, 0.01, L - 0.03), M4.trs(0.70 * s, 2.268, 0), MAT.led);
    // dark gap between the door bottom edge and the PSU panel (the two converging lines in y_47300)
    B.add(gBox(0.012, 0.002, L), M4.trs(0.784 * s, 1.8435, 0), BINMAT.lipGap);
  }
  B.add(gBox(1.55, 0.004, L - 0.004), M4.trs(0, 1.8425, 0), BINMAT.band);
  for (let k = 0; k < 8; k++) B.add(gBox(1.52, 0.002, 0.004), M4.trs(0, 1.8395, -L / 2 + (k + 0.5) * L / 8), BINMAT.joint);
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

function fitModules(z0, z1, nominal) {
  const n = Math.max(1, Math.round((z1 - z0) / nominal));
  const L = (z1 - z0) / n, out = [];
  for (let k = 0; k < n; k++) out.push([z0 + L * (k + 0.5), L / nominal]);
  return out;
}
const psuXF = (x, z) => Math.abs(x) < 1.1 ? M4.trs(x, 1.8405, z) : M4.trs(x, binBottomY(x) - 0.005, z, 0, 0, -TILT_O * Math.sign(x));
// row placard high on the door face, above the latch (py_37302: "25 ..." at the top edge of each door) [V]
function placardXF(group, z) {
  const out = [];
  if (group !== 1) { const s = group === 0 ? -1 : 1, [x, y, tx, ty] = faceAtY(OBIN_DOOR, 2.165); out.push(faceM((x - 0.006) * s, y, tx * s, ty, z, -s, 0.0015)); }
  else { const [x, y, tx, ty] = faceAtY(CBIN_DOOR, 2.19); for (const s of [-1, 1]) out.push(faceM((x + 0.006) * s, y, tx * s, ty, z, s, 0.0015)); }
  return out;
}

function buildBins(gl, layout) {
  const zones = layout.zones.filter((z) => z.type === 'seat');
  const side = [], center = [];
  for (const zn of zones) {
    for (const [zc, s] of fitModules(zn.z0, zn.z1, BIN.side)) side.push(M4.trs(0, 0, zc, 0, 0, 0, 1, 1, s));
    for (const [zc, s] of fitModules(zn.z0, zn.z1, BIN.center)) center.push(M4.trs(0, 0, zc, 0, 0, 0, 1, 1, s));
  }
  const meshes = {
    binR: gl.mesh(sideBinModule(1), { name: 'binR', layer: 'upper', instances: side }),
    binL: gl.mesh(sideBinModule(-1), { name: 'binL', layer: 'upper', instances: side }),
    binC: gl.mesh(centerBinModule(), { name: 'binC', layer: 'upper', instances: center }),
  };
  // ---- PSUs per seat block per row: compact pods outboard, a full-width row on the centre bins ----
  const psu = {};
  const byRow = {};
  for (const s of layout.seats) (byRow[s.row] = byRow[s.row] || []).push(s);
  for (const ss of Object.values(byRow)) {
    const blocks = [ss.filter((s) => s.x < -1.1), ss.filter((s) => Math.abs(s.x) <= 1.1), ss.filter((s) => s.x > 1.1)];
    blocks.forEach((b, bi) => {
      if (!b.length) return;
      const k0 = b[0].kind, fj = k0 === 'room' || k0 === 'suite';
      const n = fj ? 1 : Math.min(4, b.length);
      const cx = b.reduce((a, s) => a + s.x, 0) / b.length;
      const z = k0 === 'econ' ? b[0].z - 0.45 : k0 === 'py' ? b[0].z - 0.5 : b[0].z;
      const key = bi === 1 && !fj ? 'c' + n : 'o' + n;
      const xs = bi !== 1 ? [clamp(Math.abs(cx), 1.95, 2.45) * Math.sign(cx)] : fj ? [-0.4, 0.4] : [0];
      for (const x of xs) (psu[key] = psu[key] || []).push(psuXF(x, z));
    });
  }
  // centre-row unit pitch 0.34 m: 4 units span most of the 1.55 m bin bottom in y_47300 [A]
  for (const [key, inst] of Object.entries(psu)) meshes['psu' + key] = gl.mesh(psuModule(+key.slice(1), true, key[0] === 'c' ? 0.34 : 0.15), { name: 'psu' + key, layer: 'upper', instances: inst, castShadow: false });

  // ---- row placards ----
  const D = new Builder();
  for (const [row, ss] of Object.entries(byRow)) {
    const k0 = ss[0].kind;
    const z = k0 === 'econ' ? ss[0].z - 0.34 : k0 === 'py' ? ss[0].z - 0.4 : ss[0].z;
    const groups = [ss.filter((s) => s.x < -1.1), ss.filter((s) => Math.abs(s.x) <= 1.1), ss.filter((s) => s.x > 1.1)];
    groups.forEach((gr, i) => {
      const name = `row${row}_${i}`;
      if (!gr.length || !ATL.rects[name]) return;
      for (const m of placardXF(i, z)) D.add(gQuad(0.08, 0.031), m, MAT.decal, atlasUV(name));
    });
  }
  meshes.placards = gl.mesh(D.build(), { name: 'placards', layer: 'upper', castShadow: false });
  return meshes;
}

// studio slice: two outboard modules a side, four centre modules, aisle ceilings, Y-style PSUs and placards
function ceilingSlice() {
  const B = new Builder();
  const L = BIN.side;
  buildCeilings(B, { zones: [{ type: 'seat', z0: -L, z1: L, cls: 'Y' }], seats: [] });
  const side = { R: sideBinModule(1), L: sideBinModule(-1), C: centerBinModule() };
  for (const zc of [-L / 2, L / 2]) for (const k of ['R', 'L']) B.addBuilt(side[k], M4.trs(0, 0, zc));
  for (const zc of [-1.5, -0.5, 0.5, 1.5]) B.addBuilt(side.C, M4.trs(0, 0, zc * BIN.center));
  for (const z of [-0.9, -0.036, 0.828]) {
    for (const x of [-2.2, 2.2]) B.addBuilt(psuModule(3), psuXF(x, z));
    B.addBuilt(psuModule(4, true, 0.34), psuXF(0, z));
  }
  for (const [g, name] of [[0, 'row31_0'], [1, 'row31_1'], [2, 'row31_2']]) if (ATL.rects[name]) for (const m of placardXF(g, 0.1)) B.add(gQuad(0.08, 0.031), m, MAT.decal, atlasUV(name));
  return B.build();
}
