// ------------------------------------------------------------------
// Economy seat (Recaro) for the ANA 777-300ER - see REFERENCE777.md
// Seat-local frame and shared materials / helpers (SEATMAT, SEC, loftAt, cushionSecs) live in 09_seats.js.
// New materials for this product: Object.assign(SEATMAT, {...}) at the top of this file (loaded after 09_seats.js).
// ------------------------------------------------------------------
// ================= ECONOMY (Recaro, 17 in, 13.3 in screen, 6-way headrest, footrest) =================
const ECON = { back: 13 * DEG, hinge: [0.47, -0.075], sp: 19 * IN };
function econSeat(B, x0, lod, opts = {}) {
  const [hy, hz] = ECON.hinge;
  const F = opts.fab || SEATMAT.yFabric;
  const BH = M4.trs(x0, hy, hz, 0, ECON.back);
  B.add(gLoft(cushionSecs(0.43, 0.47, 0.095, -0.05, { edge: 0.034, r: 0.03, crown: 0.01 }), lod ? 3 : 4), M4.trs(x0, 0.415, -0.28, 0, 3 * DEG), F);
  B.add(gRBox(0.44, 0.035, 0.46, 0.012, 1), M4.trs(x0, 0.35, -0.27), SEATMAT.yShellDark);
  loftAt(B, [SEC(0.0, 0.40, 0.07, -0.005, 0.02), SEC(0.04, 0.425, 0.09, -0.012), SEC(0.16, 0.43, 0.108, -0.024, 0.036), SEC(0.30, 0.43, 0.095, -0.014, 0.036),
    SEC(0.46, 0.425, 0.086, -0.006, 0.034), SEC(0.58, 0.41, 0.076, 0.0, 0.03), SEC(0.62, 0.38, 0.055, 0.004, 0.022)], BH, F, lod ? 3 : 4);
  // slim rear shell, thicker where the screen sits
  const zr = (y) => 0.075 + 0.014 * Math.sin(Math.PI * clamp(y / 0.74, 0, 1));
  const ds = [[-0.03, 0.03], [0.1, 0.03], [0.3, 0.034], [0.46, 0.05], [0.62, 0.064], [0.70, 0.058], [0.745, 0.04]];
  loftAt(B, ds.map(([y, d]) => SEC(y, 0.446, d, zr(y) - d / 2, 0.018)), BH, SEATMAT.yShell, lod ? 2 : 3);
  // 6-way headrest: a proud cushion (~3-4 cm in front of the back) with the wing bolsters merged in as rounded ends
  // (y_47306 / 47302 / 47300)
  loftAt(B, [SEC(0.62, 0.35, 0.07, -0.02, 0.03), SEC(0.645, 0.37, 0.09, -0.03, 0.04), SEC(0.77, 0.37, 0.092, -0.032, 0.042), SEC(0.81, 0.35, 0.08, -0.026, 0.036), SEC(0.83, 0.31, 0.055, -0.018, 0.025)], BH, SEATMAT.yHead, lod ? 3 : 4);
  // slate leatherette cover draped over the headrest front + top, hanging ~0.22 below the top (height/width 0.86-1.0 in
  // y_47300 / 47302 / 47306) [D]
  B.add(gRBox(0.27, 0.22, 0.008, 0.01, 1), M4.mul(BH, M4.trs(0, 0.725, -0.082)), SEATMAT.yCover);
  B.add(gRBox(0.27, 0.008, 0.07, 0.004, 1), M4.mul(BH, M4.trs(0, 0.838, -0.045)), SEATMAT.yCover);
  if (lod) return;
  // small light-grey ANA mark in the flap's lower corner (viewer's right from the front, y_47306)
  B.add(gQuad(0.02, 0.012), M4.mul(BH, M4.trs(-0.11, 0.625, -0.0865, Math.PI)), { c: '#9aa0ae', r: 0.45 });
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz));
  // navy pillow resting on the cushion at the crease (y_47300)
  if (opts.pillow !== false) B.add(gLoft(cushionSecs(0.27, 0.21, 0.08, -0.04, { edge: 0.035, r: 0.04 }), 3), M4.mul(BH, M4.trs(0, 0.12, -0.13, 0, -80 * DEG)), SEATMAT.yPillow);
  // life-vest pouch: dark holder well under the seat with the red pull tab hanging from it (y_47302)
  B.add(gRBox(0.12, 0.05, 0.03, 0.01, 1), M4.trs(x0, 0.24, -0.30), { c: '#2e3136', r: 0.6 });
  B.add(gBox(0.018, 0.06, 0.006), M4.trs(x0 + 0.02, 0.19, -0.31), { c: '#c8252b', r: 0.5 });
  if (!opts.noScreen) {
    // 13.3 in touchscreen (0.294 x 0.166): thick off-white surround + black glass border 0.315 x 0.205 (y_47305: 600 x
    // 390 px at 1905 px/m, colour (29,26,38)) [D]
    B.add(gRBox(0.36, 0.235, 0.018, 0.012, 1), on(0.575, 0.001), SEATMAT.yShell);
    B.add(gRBox(0.316, 0.205, 0.004, 0.006, 1), on(0.574, 0.0095), { c: '#1d1a26', r: 0.22 });
    B.add(gQuad(0.294, 0.166), on(0.575, 0.0125), SEATMAT.screen, atlasUV('screen'));
    // IFE handset: small dark pill docked 18 mm under the bezel, ~0.157 x 0.045, round D-pad + coloured keys (y_47305) [D]
    B.add(gRBox(0.16, 0.045, 0.018, 0.02, 1), on(0.431, 0.012), { c: '#2a2f43', r: 0.35 });
    const key = (dx, r, c) => B.add(gCyl(r, r, 0.004, 12), M4.mul(on(0.431, 0.022, dx), M4.trs(0, 0, 0, 0, Math.PI / 2)), { c, r: 0.35, e: c === '#15181c' ? 0 : 0.2 });
    key(-0.03, 0.016, '#15181c');
    [['#3aa0ff', 0.02], ['#e04040', 0.035], ['#40c070', 0.05]].forEach(([c, dx]) => key(dx, 0.004, c));
    // plain light-grey tray + grey latch; light leatherette literature flap holding the blue safety card; dark mesh bag
    // at the bottom; AC / USB plate in a light recess (y_47303 enlarged, y_47307)
    B.add(gRBox(0.40, 0.20, 0.018, 0.01, 1), on(0.30, 0.009), SEATMAT.yTray);
    B.add(gRBox(0.05, 0.012, 0.012, 0.005, 1), on(0.39, 0.02), { c: '#9ea3a9', r: 0.4 });
    B.add(gQuad(0.12, 0.024), on(0.188, 0.018), { c: '#2c5fb0', r: 0.6 });
    B.add(gRBox(0.30, 0.10, 0.012, 0.008, 1), on(0.135, 0.02), { c: '#c9ccd1', r: 0.5, l: LAYER.leather });
    B.add(gRBox(0.34, 0.10, 0.02, 0.01, 1), on(0.05, 0.018), { c: '#4c5058', r: 0.85, l: LAYER.grille });
    B.add(gRBox(0.06, 0.07, 0.006, 0.006, 1), on(0.20, 0.011, 0.185), { c: '#c2c5c9', r: 0.45 });
    B.add(gRBox(0.04, 0.05, 0.004, 0.004, 1), on(0.20, 0.015, 0.185), SEATMAT.black);
  }
  // footrest for the passenger behind: two off-white hanger arms from the rear spreader carrying ribbed aluminium pedals
  // (y_47304)
  if (opts.footrest !== false) {
    for (const s of [-1, 1]) {
      B.add(gRBox(0.025, 0.20, 0.03, 0.008, 1), M4.trs(x0 + s * 0.13, 0.21, -0.04, 0, -24 * DEG), SEATMAT.arm);
      B.add(gRBox(0.13, 0.02, 0.05, 0.008, 1), M4.trs(x0 + s * 0.07, 0.11, 0.0), { c: '#9a9ea4', m: 0.8, r: 0.35, l: LAYER.brushed });
    }
  }
  // belt: silver tongue one side, light-grey plastic buckle cover the other (y_47303)
  for (const s of [-1, 1]) {
    B.add(s < 0 ? gRBox(0.05, 0.012, 0.035, 0.005, 1) : gRBox(0.05, 0.014, 0.04, 0.006, 1), M4.trs(x0 + 0.028 * s, 0.473, -0.25), s < 0 ? SEATMAT.buckle : { c: '#cfd2d6', r: 0.4 });
    B.add(gBox(0.045, 0.004, 0.16), M4.trs(x0 + 0.12 * s, 0.471, -0.18, s * 14 * DEG), SEATMAT.yBelt);
  }
  // pan-front stiffener in the light-grey structure colour (y_47300 / 47302: fabric pan fronts over light-grey structure,
  // no black bar) - QA r2, was black
  B.add(gRBox(0.30, 0.04, 0.10, 0.01, 1), M4.trs(x0, 0.31, -0.45), SEATMAT.yShellDark);
}

function econUnit(n, lod = false, opts = {}) {
  const B = new Builder();
  const sp = ECON.sp;
  const xs = []; for (let k = 0; k < n; k++) xs.push((k - (n - 1) / 2) * sp);
  // ANA mixes three fabric patterns seat by seat (y_47302: mosaic / diamond / ticks left to right; y_47306: diamond /
  // ticks / mosaic)
  const fabs = [SEATMAT.yFabric, SEATMAT.yFabricB, SEATMAT.yFabricC];
  xs.forEach((x, k) => econSeat(B, x, lod, { ...opts, fab: fabs[(k * 7 + n * 3) % 3] }));
  const arms = []; for (let k = 0; k <= n; k++) arms.push((k - n / 2) * sp);
  arms.forEach((xa, k) => {
    // sculpted off-white armrest (thick, rounded, slightly drooping nose) on a rear pivot post (y_47302 / 47303)
    loftAt(B, [SEC(0.60, 0.050, 0.33, -0.235, 0.02), SEC(0.63, 0.056, 0.34, -0.235, 0.026), SEC(0.66, 0.054, 0.335, -0.235, 0.026), SEC(0.672, 0.046, 0.32, -0.235, 0.02)], M4.trs(xa, 0, 0), SEATMAT.arm, 3);
    B.add(gRBox(0.052, 0.07, 0.05, 0.022, 2), M4.trs(xa, 0.625, -0.405, 0, 18 * DEG), SEATMAT.arm);
    B.add(gRBox(0.05, 0.008, 0.24, 0.004, 1), M4.trs(xa, 0.674, -0.235), SEATMAT.armPad);
    B.add(gRBox(0.036, 0.23, 0.06, 0.014, 1), M4.trs(xa, 0.51, -0.09), SEATMAT.arm);
    // off-white fairing hanging under the arm nose down to ~0.14 m above the floor (the white "paddles" in y_47302:
    // 0.54 -> 0.14 m at 422 px/m) [D]
    B.add(gRBox(0.03, 0.40, 0.14, 0.012, 2), M4.trs(xa, 0.34, -0.36, 0, -6 * DEG), SEATMAT.arm);
    if (k === 0 || k === arms.length - 1) {
      // block end: sculpted off-white side panel under the armrest, tapering from the full arm length down + forward
      // toward the front leg (y_47302 right-hand aisle seat, y_47301 aisle ends)
      const o = k === 0 ? -1 : 1;
      loftAt(B, [SEC(0.16, 0.018, 0.14, -0.36, 0.007), SEC(0.40, 0.018, 0.30, -0.31, 0.007), SEC(0.62, 0.018, 0.44, -0.25, 0.007)], M4.trs(xa + o * 0.012, 0, 0), SEATMAT.yShell, 2);
      B.add(gRBox(0.02, 0.09, 0.05, 0.008, 1), M4.trs(xa + o * 0.024, 0.46, -0.40), SEATMAT.yShellDark);
    }
    if (!lod) B.add(gCyl(0.008, 0.008, 0.06, 10), M4.trs(xa, 0.63, -0.08, 0, 0, Math.PI / 2), SEATMAT.frame);
  });
  const W = n * sp;
  const legX = n >= 3 ? [-(W / 2 - 0.24), W / 2 - 0.24] : [-0.24, 0.24];
  for (const lx of legX) {
    B.add(gRBox(0.035, 0.31, 0.045, 0.01, 1), M4.trs(lx, 0.155, -0.06), SEATMAT.frame);
    B.add(gRBox(0.035, 0.34, 0.045, 0.01, 1), M4.trs(lx, 0.16, -0.36, 0, -22 * DEG), SEATMAT.frame);
    B.add(gRBox(0.04, 0.05, 0.46, 0.01, 1), M4.trs(lx, 0.31, -0.22), SEATMAT.frame);
    // silver track fittings (y_47303 / 47304), QA r2 was black
    B.add(gBox(0.05, 0.025, 0.12), M4.trs(lx, 0.012, -0.06), SEATMAT.frame);
    B.add(gBox(0.05, 0.025, 0.12), M4.trs(lx, 0.012, -0.30), SEATMAT.frame);         // under the raked front leg's foot
  }
  for (const zb of [-0.1, -0.40]) B.add(gCyl(0.02, 0.02, W - 0.04, 10), M4.trs(0, 0.30, zb, 0, 0, Math.PI / 2), SEATMAT.frame);
  if (!lod) {
    B.add(gRBox(0.22, 0.10, 0.30, 0.012, 1), M4.trs(xs[xs.length - 1] - 0.05, 0.19, -0.22), SEATMAT.black);
  }
  return B.build();
}
function econUnitFar(n) {
  const B = new Builder();
  const sp = ECON.sp;
  for (let k = 0; k < n; k++) {
    const x0 = (k - (n - 1) / 2) * sp;
    B.add(gRBox(0.43, 0.10, 0.47, 0.04, 1), M4.trs(x0, 0.41, -0.28, 0, 3 * DEG), SEATMAT.yFabric);
    const BH = M4.trs(x0, ECON.hinge[0], ECON.hinge[1], 0, ECON.back);
    B.add(gRBox(0.43, 0.62, 0.10, 0.035, 1), M4.mul(BH, M4.trs(0, 0.31, -0.012)), SEATMAT.yFabric);
    B.add(gRBox(0.446, 0.74, 0.045, 0.015, 1), M4.mul(BH, M4.trs(0, 0.35, 0.064)), SEATMAT.yShell);
    B.add(gRBox(0.37, 0.2, 0.08, 0.03, 1), M4.mul(BH, M4.trs(0, 0.72, -0.028)), SEATMAT.yHead);
    B.add(gBox(0.27, 0.22, 0.01), M4.mul(BH, M4.trs(0, 0.715, -0.07)), SEATMAT.yCover);
    B.add(gQuad(0.294, 0.166), M4.mul(BH, M4.trs(0, 0.575, 0.09)), SEATMAT.screen, atlasUV('screen'));
  }
  for (let k = 0; k <= n; k++) B.add(gBox(0.048, 0.05, 0.30), M4.trs((k - n / 2) * sp, 0.64, -0.235), SEATMAT.arm);
  return B.build();
}
