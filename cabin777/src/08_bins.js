// ------------------------------------------------------------------
// Overhead bins (777): outboard pivot bins (4-frame modules, outward-curving doors, bottom-centre latch),
// double-sided centre bins (2-frame modules), cove LEDs, PSUs with gaspers, row placards
// ------------------------------------------------------------------
const BIN = { side: 4 * CAB.win.pitch, center: 2 * CAB.win.pitch };
const binBottomY = (x) => { const ax = Math.abs(x); return lerp(1.60, 1.795, clamp((2.845 - ax) / (2.845 - 1.53), 0, 1)); };

function sideBinModule(side) {
  const L = BIN.side;
  const B = new Builder();
  const poly = SIDEBIN.map(([x, y]) => [x * side, y]);
  B.add(gExtrude(poly, L - 0.012, 20), null, MAT.bin);
  // door skin on the aisle face (lip -> top edge)
  const face = SIDEBIN.slice(1, 8);
  const skin = [];
  for (const [x, y] of face) skin.push([(x - 0.006) * side, y]);
  for (const [x, y] of face.slice().reverse()) skin.push([(x + 0.004) * side, y]);
  B.add(gExtrude(skin, L - 0.03, 25), null, MAT.binDoor);
  // gasket seams at the module ends
  for (const zz of [-(L / 2 - 0.008), L / 2 - 0.008]) B.add(profileRibbon(face.map(([x, y]) => [x - 0.0075, y]), side, zz, 0.006, 0.0), null, MAT.doorGap);
  // bottom lip + recessed latch handle (bottom centre of the door)
  B.add(gRBox(0.03, 0.02, L - 0.03, 0.008, 1), M4.trs(1.512 * side, 1.806, 0), MAT.binLip);
  B.add(gRBox(0.014, 0.035, 0.24, 0.008, 1), M4.trs(1.482 * side, 1.852, 0), { c: '#8d9399', r: 0.45 });
  B.add(gRBox(0.022, 0.02, 0.2, 0.008, 1), M4.trs(1.476 * side, 1.855, 0), MAT.latch);
  // cove LED along the top inner edge (washes the aisle panel) + sidewall wash lens under the bin
  B.add(gBox(0.05, 0.01, L - 0.03), M4.trs(1.70 * side, 2.238, 0), MAT.led);
  B.add(gBox(0.045, 0.006, L - 0.03), M4.trs(2.80 * side, 1.607, 0, 0, 0, side * 0.12), { c: '#ffffff', r: 0.4, l: 12, e: 0.35 });
  return B.build();
}
function centerBinModule() {
  const L = BIN.center;
  const B = new Builder();
  const half = CBIN;
  const poly = [...half.map(([x, y]) => [x, y]), ...half.slice(0, -1).reverse().map(([x, y]) => [-x, y])];
  B.add(gExtrude(poly, L - 0.012, 20), null, MAT.bin);
  for (const s of [-1, 1]) {
    const face = half.slice(0, 6);
    const skin = [];
    for (const [x, y] of face) skin.push([(x + 0.006) * s, y]);
    for (const [x, y] of face.slice().reverse()) skin.push([(x - 0.004) * s, y]);
    B.add(gExtrude(skin, L - 0.03, 25), null, MAT.binDoor);
    B.add(gRBox(0.014, 0.035, 0.22, 0.008, 1), M4.trs(0.818 * s, 1.89, 0), { c: '#8d9399', r: 0.45 });
    B.add(gRBox(0.02, 0.02, 0.18, 0.008, 1), M4.trs(0.824 * s, 1.893, 0), MAT.latch);
    for (const zz of [-(L / 2 - 0.008), L / 2 - 0.008]) B.add(profileRibbon(face.map(([x, y]) => [x + 0.0075, y]), s, zz, 0.006, 0.0), null, MAT.doorGap);
    B.add(gBox(0.05, 0.01, L - 0.03), M4.trs(0.70 * s, 2.268, 0), MAT.led);
  }
  B.add(gBox(1.56, 0.01, L - 0.02), M4.trs(0, 1.842, 0), MAT.binLip);
  return B.build();
}

// PSU under a bin: n reading lights + gaspers + call button + signs
function psuModule(n, lights = true) {
  const B = new Builder();
  const w = n * 0.15 + 0.08;
  B.add(gRBox(w, 0.02, 0.2, 0.008, 1), null, MAT.psu);
  for (let k = 0; k < n; k++) {
    const x = (k - (n - 1) / 2) * 0.15;
    if (lights) B.add(gCyl(0.02, 0.02, 0.01, 10), M4.trs(x - 0.03, -0.013, -0.04), MAT.lens);
    B.add(gCyl(0.017, 0.021, 0.022, 10), M4.trs(x + 0.035, -0.018, -0.04), MAT.nozzle);
    B.add(gCyl(0.008, 0.008, 0.008, 6), M4.trs(x + 0.035, -0.03, -0.04), MAT.darkPlastic);
  }
  B.add(gRBox(0.03, 0.008, 0.02, 0.004, 1), M4.trs(w / 2 - 0.04, -0.012, 0.05), { c: '#6f8fb8', r: 0.4 });
  B.add(gQuad(0.105, 0.048), M4.trs(0, -0.0105, 0.055, 0, Math.PI / 2), { ...MAT.exitGlow, e: 0.35 }, atlasUV('psuSigns'));
  return B.build();
}

function fitModules(z0, z1, nominal) {
  const n = Math.max(1, Math.round((z1 - z0) / nominal));
  const L = (z1 - z0) / n, out = [];
  for (let k = 0; k < n; k++) out.push([z0 + L * (k + 0.5), L / nominal]);
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
  // ---- PSUs per seat block per row ----
  const psu = { 3: [], 2: [], 4: [], 1: [] };
  const byRow = {};
  for (const s of layout.seats) (byRow[s.row] = byRow[s.row] || []).push(s);
  const tiltO = Math.atan2(1.795 - 1.60, 2.845 - 1.53);
  for (const ss of Object.values(byRow)) {
    const blocks = [ss.filter((s) => s.x < -1.1), ss.filter((s) => Math.abs(s.x) <= 1.1), ss.filter((s) => s.x > 1.1)];
    blocks.forEach((b, bi) => {
      if (!b.length) return;
      const k0 = b[0].kind;
      const n = k0 === 'econ' || k0 === 'py' ? Math.min(4, b.length) : 1;
      const cx = b.reduce((a, s) => a + s.x, 0) / b.length;
      const z = k0 === 'econ' ? b[0].z - 0.45 : k0 === 'py' ? b[0].z - 0.5 : b[0].z;
      if (bi === 1) {
        const xs = (k0 === 'room' || k0 === 'suite') ? [-0.4, 0.4] : [0];
        for (const x of xs) (psu[n] || psu[4]).push(M4.trs(x, 1.842 - 0.012, z));
      } else {
        const x = clamp(Math.abs(cx), 1.95, 2.45) * Math.sign(cx);
        (psu[n] || psu[4]).push(M4.trs(x, binBottomY(x) - 0.012, z, 0, 0, tiltO * (x > 0 ? 1 : -1)));
      }
    });
  }
  for (const n of [1, 2, 3, 4]) meshes['psu' + n] = gl.mesh(psuModule(n, n > 1), { name: 'psu' + n, layer: 'upper', instances: psu[n], castShadow: false });

  // ---- row placards on the bin lips ----
  const D = new Builder();
  for (const [row, ss] of Object.entries(byRow)) {
    const k0 = ss[0].kind;
    const z = k0 === 'econ' ? ss[0].z - 0.34 : k0 === 'py' ? ss[0].z - 0.4 : ss[0].z;
    const groups = [ss.filter((s) => s.x < -1.1), ss.filter((s) => Math.abs(s.x) <= 1.1), ss.filter((s) => s.x > 1.1)];
    groups.forEach((gr, i) => {
      if (!gr.length) return;
      const name = `row${row}_${i}`;
      if (!ATL.rects[name]) return;
      const q = gQuad(0.095, 0.037);
      if (i === 0) D.add(q, M4.trs(-1.497, 1.812, z, Math.PI / 2, 0, 0), MAT.decal, atlasUV(name));
      if (i === 2) D.add(q, M4.trs(1.497, 1.812, z, -Math.PI / 2, 0, 0), MAT.decal, atlasUV(name));
      if (i === 1) {
        D.add(q, M4.trs(0.826, 1.87, z, Math.PI / 2, 0, 0), MAT.decal, atlasUV(name));
        D.add(q, M4.trs(-0.826, 1.87, z, -Math.PI / 2, 0, 0), MAT.decal, atlasUV(name));
      }
    });
  }
  meshes.placards = gl.mesh(D.build(), { name: 'placards', layer: 'upper', castShadow: false });
  return meshes;
}
