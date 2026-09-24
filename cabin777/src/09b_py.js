// ------------------------------------------------------------------
// Premium Economy seat (ZIM) for the ANA 777-300ER - see REFERENCE777.md
// Seat-local frame and shared materials / helpers (SEATMAT, SEC, loftAt, cushionSecs) live in 09_seats.js.
// New materials for this product: Object.assign(SEATMAT, {...}) at the top of this file (loaded after 09_seats.js).
// ------------------------------------------------------------------
// ================= PREMIUM ECONOMY (ZIM, 19 in, 15.6 in screen, leg rest + bicycle footrest) =================
// PY w1: sp 0.5525 = 05_layout pySp (seat ids / eye points and geometry agreed only to 2-3 cm with the old 0.5715) [D]
const PY = { back: 14 * DEG, hinge: [0.48, -0.09], sp: 0.5525 };
function pySeat(B, x0, lod, opts = {}) {
  const [hy, hz] = PY.hinge;
  const F = SEATMAT.pyFabric;
  const BH = M4.trs(x0, hy, hz, 0, PY.back);
  B.add(gLoft(cushionSecs(0.455, 0.50, 0.115, -0.06, { edge: 0.04, r: 0.035, crown: 0.012 }), lod ? 3 : 4), M4.trs(x0, 0.425, -0.30, 0, 3 * DEG), F);
  B.add(gRBox(0.46, 0.05, 0.48, 0.012, 1), M4.trs(x0, 0.335, -0.29), SEATMAT.pyArm);
  // QA r2: the centre of the back sits ~3 cm behind its old face between the bolsters (d 0.10 at y 0.34-0.52), and the top
  // blends into the headrest (overlapping sections instead of a step)
  loftAt(B, [SEC(0.0, 0.44, 0.09, -0.01, 0.025), SEC(0.05, 0.46, 0.115, -0.02), SEC(0.18, 0.47, 0.13, -0.032, 0.045), SEC(0.34, 0.47, 0.10, -0.014, 0.042),
    SEC(0.52, 0.46, 0.10, -0.009, 0.042), SEC(0.64, 0.45, 0.095, -0.008, 0.036), SEC(0.68, 0.44, 0.09, -0.006, 0.036)], BH, F, lod ? 3 : 4);
  // sculpted side bolsters standing ~5 cm proud of the centre, narrow at the waist (~0.30 above the cushion), flaring
  // at the shoulders (py_37301 / 37303) [D]
  for (const sd of [-1, 1]) {
    const BX = M4.mul(BH, M4.trs(sd * 0.198, 0, -0.03, -sd * 14 * DEG));
    loftAt(B, [SEC(0.02, 0.07, 0.10, 0, 0.03), SEC(0.10, 0.085, 0.14, -0.016, 0.042), SEC(0.30, 0.07, 0.14, -0.016, 0.034), SEC(0.48, 0.09, 0.13, -0.012, 0.042),
      SEC(0.60, 0.08, 0.10, -0.006, 0.036), SEC(0.66, 0.06, 0.08, 0, 0.028)], BX, F, lod ? 2 : 3);
  }
  if (!lod) B.add(gBox(0.40, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.30, -0.071)), { c: '#3c3e44', r: 0.8 });   // lumbar crease
  // thick rear shell that wraps round the back's sides (grey edge visible from the front)
  const zr = (y) => 0.105 + 0.014 * Math.sin(Math.PI * clamp(y / 0.84, 0, 1));
  // QA r2: the shell's rounded top rises above the headrest (to 0.97, headrest 0.91) and frames the screen from behind
  // (san_13 / san_24, py_37304); the top sections are rounded to half their depth
  const ds = [[-0.04, 0.05], [0.12, 0.06], [0.34, 0.07], [0.5, 0.084], [0.68, 0.09], [0.78, 0.085], [0.88, 0.08], [0.94, 0.06], [0.97, 0.035]];
  loftAt(B, ds.map(([y, d]) => SEC(y, 0.525, d, zr(y) - d / 2 + 0.01, y > 0.85 ? d / 2 - 0.002 : 0.026)), BH, SEATMAT.pyShell, lod ? 2 : 3);
  // 6-way headrest with wings
  loftAt(B, [SEC(0.67, 0.42, 0.085, -0.008, 0.036), SEC(0.71, 0.39, 0.092, -0.012, 0.04), SEC(0.85, 0.39, 0.092, -0.012, 0.04), SEC(0.895, 0.37, 0.075, -0.006, 0.032), SEC(0.91, 0.33, 0.05, -0.002, 0.02)], BH, F, lod ? 3 : 4);
  for (const s of [-1, 1]) {
    // soft round pillow bolsters either side of the flap, ~0.10 wide x 0.25 tall with domed ends, bulging ~3.5 cm
    // forward of the flap (py_37301 / 37305)
    const WX = M4.mul(BH, M4.trs(s * 0.195, 0, -0.045, -s * 18 * DEG));
    loftAt(B, [SEC(0.66, 0.05, 0.05, 0, 0.024), SEC(0.69, 0.085, 0.095, 0, 0.042), SEC(0.72, 0.10, 0.11, 0, 0.05), SEC(0.87, 0.10, 0.11, 0, 0.05),
      SEC(0.90, 0.085, 0.095, 0, 0.042), SEC(0.92, 0.05, 0.05, 0, 0.024)], WX, SEATMAT.pyWing, lod ? 2 : 3);
  }
  // navy leatherette flap over the headrest front + top, silver trim line low on the back shell (py_37303)
  // flap ~0.28 x 0.25, hanging a little below the wing pads (py_37301 seat C: 98 x 92 px on a 158 px headrest) [D]
  B.add(gRBox(0.28, 0.25, 0.008, 0.006, 1), M4.mul(BH, M4.trs(0, 0.78, -0.064)), SEATMAT.pyCover);
  B.add(gRBox(0.28, 0.008, 0.07, 0.004, 1), M4.mul(BH, M4.trs(0, 0.904, -0.03)), SEATMAT.pyCover);
  B.add(gBox(0.49, 0.008, 0.006), M4.mul(BH, M4.trs(0, 0.04, zr(0.04) + 0.022)), SEATMAT.pyTrim);
  // fold-up leg rest (stowed below the pan front)
  B.add(gLoft([SEC(0.0, 0.44, 0.05, 0, 0.018), SEC(0.30, 0.46, 0.06, 0, 0.022)], 3), M4.trs(x0, 0.07, -0.545, 0, -4 * DEG), F);
  B.add(gRBox(0.44, 0.02, 0.05, 0.008, 1), M4.trs(x0, 0.075, -0.54), SEATMAT.pyArm);            // leg-rest foot bar
  // dark-grey hinge roller across the top of the stowed leg rest under the cushion nose, dark side links down to the
  // foot bar (py_37301, san_17) [D]
  B.add(gCyl(0.026, 0.026, 0.44, lod ? 8 : 14), M4.trs(x0, 0.345, -0.55, 0, 0, Math.PI / 2), SEATMAT.pyArm);
  if (!lod) for (const s of [-1, 1]) B.add(gRBox(0.015, 0.28, 0.03, 0.006, 1), M4.trs(x0 + s * 0.222, 0.21, -0.55), SEATMAT.pyArm);
  if (lod) return;
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz));
  if (!opts.noScreen) {
    // 15.6 in screen: black bezel 0.373 x 0.26 (active 0.345 x 0.195) in a grey housing ~0.44 x 0.30 that projects ~4 cm
    // and tilts top-back, its top just under the shell rim (py_37304: 1614 px/m; san_24) [D]
    const scr = (dz) => M4.mul(on(0.68, 0), M4.trs(0, 0, dz, 0, -6 * DEG));
    B.add(gRBox(0.44, 0.30, 0.04, 0.02, 1), scr(0.02), SEATMAT.pyShell);
    B.add(gRBox(0.373, 0.26, 0.012, 0.008, 1), scr(0.042), SEATMAT.bezel);
    B.add(gQuad(0.345, 0.194), scr(0.0495), SEATMAT.screen, atlasUV('screen'));
    // two white placards under the housing (py_37304, alv_13)
    for (const sx of [-0.12, 0.12]) B.add(gQuad(0.13, 0.03), on(0.505, 0.0115, sx), { c: '#e8e8e6', r: 0.6 });
  }
  {   // (row 25 backs too: seen from row 26)
    // literature pocket low on the shell, just above the foot bar (alv_05, san_10, san_05): hard grey frame with a
    // rounded lip standing ~5 cm proud, black mesh basket below it that narrows toward the bottom (trapezoid) [D]
    B.add(gRBox(0.38, 0.035, 0.055, 0.012, 1), on(0.215, 0.028), SEATMAT.pyShell);
    for (const s of [-1, 1]) B.add(gRBox(0.02, 0.17, 0.05, 0.008, 1), M4.mul(on(0.13, 0.024, s * 0.18), M4.trs(0, 0, 0, 0, 0, s * 9 * DEG)), SEATMAT.pyShell);
    loftAt(B, [SEC(0.035, 0.29, 0.02, 0.012, 0.008), SEC(0.10, 0.33, 0.042, 0.022, 0.012), SEC(0.20, 0.35, 0.046, 0.024, 0.012)],
      M4.mul(BH, M4.trs(0, 0, zr(0.13))), { c: '#16181b', r: 0.9, l: LAYER.grille }, 2);
    B.add(gBox(0.34, 0.012, 0.008), on(0.20, 0.052), SEATMAT.black);                                // pocket mouth shadow
  }
  if (!opts.noScreen) {
    // coat hook: horizontal silver bullet high on the shell side + small round grey button below it (san_24)
    B.add(gCyl(0.012, 0.016, 0.07, 10), M4.mul(on(0.80, 0.03, 0.235), M4.trs(0, 0, 0, 0, Math.PI / 2)), { c: '#c9ccd0', r: 0.25, m: 0.9, l: LAYER.brushed });
    B.add(gCyl(0.009, 0.009, 0.006, 10), M4.mul(on(0.74, 0.012, 0.235), M4.trs(0, 0, 0, 0, Math.PI / 2)), { c: '#c7c9cc', r: 0.4 });
    // gooseneck reading light: leaves the shell side at headrest height, arcs down + forward to a brushed-aluminium
    // head with a black lens at shoulder height; one per seat, on the console side (py_37305 / 37301, san_14)
    const sd = x0 > 0 ? -1 : 1, P = (x, y, z) => M4.point(BH, [sd * x, y, z]);
    B.add(gCyl(0.012, 0.012, 0.03, 10), M4.mul(BH, M4.trs(sd * 0.265, 0.80, zr(0.80) - 0.02, 0, 0, Math.PI / 2)), SEATMAT.frame);
    B.add(gTube([P(0.262, 0.80, zr(0.80) - 0.02), P(0.262, 0.80, 0.0), P(0.265, 0.74, -0.10), P(0.24, 0.62, -0.16)], 0.006, 6), null, SEATMAT.black);
    const hd = M4.mul(BH, M4.trs(sd * 0.238, 0.585, -0.177, 0, 26 * DEG));
    B.add(gCyl(0.015, 0.015, 0.075, 12), hd, { c: '#c9ccd0', r: 0.25, m: 0.9, l: LAYER.brushed });
    B.add(gCyl(0.006, 0.006, 0.002, 10), M4.mul(hd, M4.trs(0, -0.0385, 0)), SEATMAT.black);
  }
  // padded black foot bar under the pocket with silver end fittings, hung from the shell bottom (san_18)
  B.add(gCyl(0.02, 0.02, 0.20, 12), M4.trs(x0, 0.38, 0.07, 0, 0, Math.PI / 2), SEATMAT.black);
  for (const s of [-1, 1]) {
    B.add(gCyl(0.024, 0.024, 0.02, 12), M4.trs(x0 + s * 0.11, 0.38, 0.07, 0, 0, Math.PI / 2), SEATMAT.frame);
    B.add(gRBox(0.015, 0.08, 0.02, 0.005, 1), M4.trs(x0 + s * 0.11, 0.42, 0.05), SEATMAT.frame);
  }
  // bicycle-style footrest for the passenger behind (folded): aluminium pedals (san_18)
  B.add(gCyl(0.009, 0.009, 0.32, 8), M4.trs(x0, 0.13, 0.14, 0, 0, Math.PI / 2), SEATMAT.frame);
  for (const s of [-1, 1]) B.add(gRBox(0.12, 0.015, 0.075, 0.006, 1), M4.trs(x0 + s * 0.085, 0.125, 0.18, 0, 12 * DEG), SEATMAT.frame);
  for (const s of [-1, 1]) {
    B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.trs(x0 + 0.03 * s, 0.488, -0.26), SEATMAT.buckle);
    B.add(gBox(0.045, 0.004, 0.16), M4.trs(x0 + 0.13 * s, 0.486, -0.19, s * 14 * DEG), { c: '#3c3f47', r: 0.7 });
  }
}
function pyUnit(n, lod = false, opts = {}) {
  const B = new Builder();
  const sp = PY.sp;
  const xs = []; for (let k = 0; k < n; k++) xs.push((k - (n - 1) / 2) * sp);
  xs.forEach((x) => pySeat(B, x, lod, opts));
  const arms = []; for (let k = 0; k <= n; k++) arms.push((k - n / 2) * sp);
  arms.forEach((xa, k) => {
    const inner = k > 0 && k < n;
    const w = inner ? 0.095 : 0.07;     // PY w1: console fits two universal sockets side by side (alv_08) [D]
    if (inner) {
      // floor-standing console between seats: blue-grey body, silver trim round the top, cubbies + controls on
      // its front face, red life-vest tab at the bottom (py_37301)
      B.add(gRBox(w, 0.62, 0.52, 0.014, 1), M4.trs(xa, 0.31, -0.28), SEATMAT.pyArm);
      // lid: long dark leatherette pad with a stitched seam round its top (san_06, alv_04) [V]; grey plastic nose
      loftAt(B, [SEC(0.62, w + 0.01, 0.46, -0.25, 0.02), SEC(0.645, w + 0.014, 0.47, -0.25, 0.025), SEC(0.665, w + 0.006, 0.46, -0.25, 0.02)], M4.trs(xa, 0, 0), SEATMAT.pyArmPad, 2);
      B.add(gRBox(w + 0.012, 0.05, 0.08, 0.014, 1), M4.trs(xa, 0.64, -0.505), SEATMAT.pyArm);
      if (!lod) {
        for (const s of [-1, 1]) B.add(gBox(0.002, 0.002, 0.44), M4.trs(xa + s * (w / 2 - 0.006), 0.6655, -0.25), { c: '#8a8c90', r: 0.7 });
        // seat-letter plaque on the aisle side of the nose + two small buttons (san_06 'G', alv_10 'K')
        for (const s of [-1, 1]) {
          B.add(gBox(0.002, 0.026, 0.026), M4.trs(xa + s * (w / 2 + 0.007), 0.635, -0.51), { c: '#e2e2de', r: 0.6 });
          B.add(gBox(0.002, 0.016, 0.022), M4.trs(xa + s * (w / 2 + 0.007), 0.635, -0.47), SEATMAT.black);
        }
      }
      B.add(gBox(w + 0.016, 0.008, 0.545), M4.trs(xa, 0.618, -0.28), SEATMAT.pyTrim);
      if (!lod) {
        // front face (alv_08 / alv_09, py_37306): two open moulded cubbies (upper larger) with a royal-blue triangle in
        // the corner, a black panel with two universal AC + USB sockets, then a lower block with the red life-vest tab
        // each cubby: a grey front plate standing ~2.5 cm proud over the lower 3/4, dark opening only above it
        for (const [y, h] of [[0.50, 0.10], [0.37, 0.08]]) {
          B.add(gBox(w - 0.03, 0.02, 0.004), M4.trs(xa, y + h / 2 - 0.012, -0.543), SEATMAT.hole);
          B.add(gRBox(w - 0.012, h * 0.74, 0.028, 0.007, 1), M4.trs(xa, y - h * 0.13, -0.554), SEATMAT.pyArm);
          B.add(gBox(0.014, 0.014, 0.002), M4.trs(xa + w / 2 - 0.016, y + h * 0.24 - 0.01, -0.5685, 0, 0, Math.PI / 4), { c: '#2f47a8', r: 0.6 });
        }
        for (const s of [-1, 1]) {
          B.add(gRBox(0.037, 0.045, 0.004, 0.003, 1), M4.trs(xa + s * 0.021, 0.245, -0.542), SEATMAT.port);
          B.add(gBox(0.012, 0.005, 0.002), M4.trs(xa + s * 0.021, 0.262, -0.544), { c: '#3a3d44', r: 0.5 });     // USB
          B.add(gBox(0.006, 0.02, 0.002), M4.trs(xa + s * 0.021, 0.238, -0.544), { c: '#26282c', r: 0.5 });      // socket slot
        }
        B.add(gBox(w - 0.004, 0.004, 0.006), M4.trs(xa, 0.205, -0.542), SEATMAT.black);               // lower block split
        B.add(gRBox(0.016, 0.012, 0.01, 0.003, 1), M4.trs(xa, 0.175, -0.546), { c: '#2f47a8', r: 0.5 });
        B.add(gBox(0.022, 0.085, 0.004), M4.trs(xa, 0.125, -0.546), { c: '#c8252b', r: 0.5, l: LAYER.fabric });
      }
    } else {
      // aisle / window end: large rounded arm shroud from the floor with a silver strip low down (py_37301 / 37303)
      const o = k === 0 ? -1 : 1;
      B.add(gRBox(0.05, 0.64, 0.62, 0.025, 2), M4.trs(xa + o * 0.01, 0.32, -0.27), SEATMAT.pyShell);
      // dark-grey arm cap running to the shroud front, where it rounds over and turns down ~6 cm (py_37301 right seat,
      // san_13); recessed darker panel on the shroud's outer face above the silver strip (py_37303)
      loftAt(B, [SEC(0.62, w, 0.52, -0.30, 0.02), SEC(0.648, w + 0.006, 0.53, -0.30, 0.028), SEC(0.668, w - 0.004, 0.52, -0.30, 0.02)], M4.trs(xa, 0, 0), SEATMAT.pyArmPad, 2);
      B.add(gCyl(0.024, 0.024, w, 12), M4.trs(xa, 0.644, -0.556, 0, 0, Math.PI / 2), SEATMAT.pyArmPad);
      B.add(gRBox(w, 0.06, 0.03, 0.012, 1), M4.trs(xa, 0.61, -0.565), SEATMAT.pyArmPad);
      if (!lod) B.add(gRBox(0.006, 0.28, 0.44, 0.01, 1), M4.trs(xa + o * 0.033, 0.36, -0.25), { c: '#55575a', r: 0.5, l: LAYER.plastic });
      B.add(gBox(0.006, 0.012, 0.58), M4.trs(xa + o * 0.037, 0.13, -0.27, 0, 8 * DEG), SEATMAT.pyTrim);
    }
    if (inner && !lod) {
      // brushed-aluminium two-cell bottle bin on the console rear at knee height for the row behind (san_16 / 17 / 18)
      B.add(gRBox(0.06, 0.30, 0.08, 0.01, 1), M4.trs(xa, 0.37, 0.0), SEATMAT.pyArm);
      B.add(gRBox(0.11, 0.26, 0.065, 0.008, 1), M4.trs(xa, 0.38, 0.07), SEATMAT.pyBin);
      for (const s of [-1, 1]) B.add(gBox(0.045, 0.004, 0.05), M4.trs(xa + s * 0.026, 0.511, 0.07), SEATMAT.hole);
    }
  });
  const W = n * sp;
  const legX = n >= 3 ? [-(W / 2 - 0.28), W / 2 - 0.28] : [-0.28, 0.28];
  for (const lx of legX) {
    B.add(gRBox(0.04, 0.3, 0.05, 0.01, 1), M4.trs(lx, 0.15, -0.08), SEATMAT.frame);
    B.add(gRBox(0.04, 0.34, 0.05, 0.01, 1), M4.trs(lx, 0.16, -0.40, 0, -20 * DEG), SEATMAT.frame);
    B.add(gBox(0.055, 0.025, 0.14), M4.trs(lx, 0.012, -0.08), SEATMAT.black);
    B.add(gBox(0.055, 0.025, 0.14), M4.trs(lx, 0.012, -0.46), SEATMAT.black);
  }
  for (const zb of [-0.12, -0.44]) B.add(gCyl(0.022, 0.022, W - 0.05, 10), M4.trs(0, 0.30, zb, 0, 0, Math.PI / 2), SEATMAT.frame);
  return B.build();
}
function pyUnitFar(n) {
  const B = new Builder();
  const sp = PY.sp;
  for (let k = 0; k < n; k++) {
    const x0 = (k - (n - 1) / 2) * sp;
    B.add(gRBox(0.48, 0.115, 0.50, 0.045, 1), M4.trs(x0, 0.425, -0.30, 0, 3 * DEG), SEATMAT.pyFabric);
    const BH = M4.trs(x0, PY.hinge[0], PY.hinge[1], 0, PY.back);
    B.add(gRBox(0.48, 0.68, 0.12, 0.04, 1), M4.mul(BH, M4.trs(0, 0.34, -0.02)), SEATMAT.pyFabric);
    B.add(gRBox(0.505, 0.88, 0.05, 0.015, 1), M4.mul(BH, M4.trs(0, 0.40, 0.095)), SEATMAT.pyShell);
    B.add(gRBox(0.39, 0.21, 0.09, 0.035, 1), M4.mul(BH, M4.trs(0, 0.80, -0.012)), SEATMAT.pyFabric);
    B.add(gBox(0.30, 0.17, 0.01), M4.mul(BH, M4.trs(0, 0.80, -0.062)), SEATMAT.pyCover);
    B.add(gQuad(0.345, 0.194), M4.mul(BH, M4.trs(0, 0.625, 0.121)), SEATMAT.screen, atlasUV('screen'));
  }
  for (let k = 0; k <= n; k++) B.add(gBox(k > 0 && k < n ? 0.085 : 0.07, 0.34, 0.44), M4.trs((k - n / 2) * sp, 0.49, -0.27), SEATMAT.pyArm);
  return B.build();
}
