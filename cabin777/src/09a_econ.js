// ------------------------------------------------------------------
// Economy seat (Recaro) for the ANA 777-300ER - see REFERENCE777.md
// Seat-local frame and shared materials / helpers (SEATMAT, SEC, loftAt, cushionSecs) live in 09_seats.js.
// New materials for this product: Object.assign(SEATMAT, {...}) at the top of this file (loaded after 09_seats.js).
// ------------------------------------------------------------------
// ================= ECONOMY (Recaro, 17 in, 13.3 in screen, 6-way headrest, footrest) =================
const ECON = { back: 13 * DEG, hinge: [0.47, -0.075], sp: 19 * IN };
// ANA mixes four fabric patterns seat by seat (y_47302: mosaic / diamond / ticks left to right; y_47306: diamond / ticks /
// mosaic; y_47300 front row: tick / fleck / tick / fleck). econ w5 (A high): the petal fleck is the commonest (sans 13 / 14,
// fr57325 124108) -> ~40 % fleck, 20 % each of the others [D]
const econFab = (k, n, rot) => [SEATMAT.yFabric, SEATMAT.yFabricD, SEATMAT.yFabricC, SEATMAT.yFabricD, SEATMAT.yFabricB][(k * 7 + n * 3 + (rot || 0)) % 5];
function econSeat(B, x0, lod, opts = {}) {
  const [hy, hz] = ECON.hinge;
  const F = opts.fab || SEATMAT.yFabric;
  const BH = M4.trs(x0, hy, hz, 0, ECON.back);
  // pan: the diamond seats carry the diamonds on the back only, the pan is the tick weave (y_47302 middle seat) [V]
  const PF = F === SEATMAT.yFabricB ? SEATMAT.yFabric : F;
  B.add(gLoft(cushionSecs(0.43, 0.47, 0.095, -0.05, { edge: 0.034, r: 0.03, crown: 0.01 }), lod ? 3 : 4), M4.trs(x0, 0.415, -0.28, 0, 3 * DEG), PF);
  B.add(gRBox(0.44, 0.035, 0.46, 0.012, 1), M4.trs(x0, 0.35, -0.27), SEATMAT.yShellDark);
  // back: rises ~0.05-0.065 above the headrest cushion to a rounded top (y_47306 all three seats, y_47301, sanspotter 13;
  // back length ~0.87 from the pan crease, y_47302 right seat) [D]
  loftAt(B, [SEC(0.0, 0.40, 0.07, -0.005, 0.02), SEC(0.04, 0.425, 0.09, -0.012), SEC(0.16, 0.43, 0.108, -0.024, 0.036), SEC(0.30, 0.43, 0.095, -0.014, 0.036),
    SEC(0.46, 0.425, 0.086, -0.006, 0.034), SEC(0.58, 0.41, 0.076, 0.0, 0.03), SEC(0.70, 0.40, 0.07, 0.004, 0.028), SEC(0.818, 0.39, 0.062, 0.006, 0.026),
    SEC(0.838, 0.382, 0.062, 0.010, 0.026), SEC(0.853, 0.361, 0.058, 0.014, 0.024), SEC(0.863, 0.334, 0.052, 0.018, 0.02), SEC(0.868, 0.29, 0.044, 0.02, 0.016)], BH, F, lod ? 3 : 4);
  // rear shell: a slim lower panel (tray + pockets) under a deep sculpted hood that wraps the screen and caps the top of
  // the seat - from behind only a thin blue rim shows at the hood's sides (sanspotter 15 / 25-28, y_47305); hood ~0.37
  // wide (glass 0.85-0.89 of it), ~0.03 m of shell above the bezel, ~0.04 m proud of the tray face (y_47303 side view);
  // the skirt reaches below the pan top so no pan fabric shows under it (w2 B); the tray band is narrower (0.345) than the
  // hood and the pocket zone, so the hood overhangs it (sanspotter 15, w3 B) [D]
  // [y, rear-face z, depth, width, corner r]
  const RS = [[-0.12, 0.066, 0.03, 0.44, 0.018], [-0.06, 0.07, 0.03, 0.446, 0.018], [0.1, 0.078, 0.03, 0.446, 0.018], [0.2, 0.08, 0.032, 0.44, 0.018],
    [0.24, 0.081, 0.034, 0.345, 0.016], [0.44, 0.086, 0.04, 0.345, 0.016], [0.49, 0.106, 0.06, 0.37, 0.026], [0.53, 0.12, 0.08, 0.38, 0.03], [0.80, 0.122, 0.09, 0.372, 0.032],
    [0.835, 0.114, 0.085, 0.37, 0.03], [0.855, 0.10, 0.09, 0.365, 0.03], [0.868, 0.072, 0.062, 0.30, 0.02]];
  // econ w5 (A high): the shell's rounded top rolls forward over the back top, so from behind only a ~1 cm navy rim shows
  // (sans 15, fr57325 124234: no fabric above the white hood) [V]
  const rs = (y, j) => { let k = 1; while (k < RS.length - 1 && RS[k][0] < y) k++; const a = RS[k - 1], b = RS[k], t = clamp((y - a[0]) / (b[0] - a[0]), 0, 1); return a[j] + (b[j] - a[j]) * t; };
  const zr = (y) => rs(y, 1);
  loftAt(B, RS.map(([y, z, d, w, r]) => SEC(y, w, d, z - d / 2, r)), BH, SEATMAT.yShell, lod ? 2 : 3);
  // 6-way headrest: a separate cushion ~0.2 tall, ~0.065 proud of the back, with rounded wing ends (y_47306 / 47302 /
  // 47300, w2 A + B); w5 A: wing ends bulge to soft domes mid-height [D]
  loftAt(B, [SEC(0.60, 0.33, 0.06, -0.035, 0.028), SEC(0.62, 0.37, 0.09, -0.05, 0.045), SEC(0.695, 0.38, 0.10, -0.052, 0.049), SEC(0.77, 0.375, 0.095, -0.05, 0.047), SEC(0.79, 0.35, 0.07, -0.045, 0.035), SEC(0.80, 0.30, 0.04, -0.038, 0.02)], BH, F === SEATMAT.yFabricC ? SEATMAT.yFabric : F === SEATMAT.yFabricD ? F : SEATMAT.yHead, lod ? 3 : 4);   // w5: fleck seats, fleck cushion (y_47300 seats 2 / 4)   // w4 A: cushion vanished on mosaic backs
  // slate leatherette cover lying on the cushion front, wrapped ~3 cm over its top and hanging ~2.5 cm below it (the
  // flap hangs past the cushion onto the back, y_47306 right seat) [D]
  // one piece: plate on the cushion front, a fold overlapping both it and the cushion top, a hem tucking back (w3 B)
  B.add(gRBox(0.27, 0.19, 0.005, 0.006, 1), M4.mul(BH, M4.trs(0, 0.705, -0.1005)), SEATMAT.yCover);
  B.add(gRBox(0.27, 0.016, 0.046, 0.008, 2), M4.mul(BH, M4.trs(0, 0.799, -0.080)), SEATMAT.yCover);
  B.add(gRBox(0.27, 0.04, 0.005, 0.003, 1), M4.mul(BH, M4.trs(0, 0.593, -0.094, 0, -20 * DEG)), SEATMAT.yCover);
  if (lod) return;
  // small ANA mark in the flap's lower corner (viewer's right from the front, y_47306); w5 B: a thin grey logotype, not a sticker
  B.add(gQuad(0.014, 0.006), M4.mul(BH, M4.trs(-0.11, 0.625, -0.1035, Math.PI)), { c: '#5a6079', r: 0.45 });
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz));   // on the rear face
  // navy pillow resting on the cushion at the crease, ~0.35 x 0.24 (y_47300 aspect 0.65-0.7; sans 14 ~0.8 of the pan) [D]
  // w5 B: soft pillow, not a bevelled slab - a squashed sphere with pinched corners, slightly concave sides and a ~7 cm
  // dome that thins to a seamed rim (y_47300 all four pillows, sans 13) [D]
  if (opts.pillow !== false) {
    const g = gSphere(1, 20, 10);
    for (let k = 0; k < g.p.length; k += 3) {
      const sx = g.p[k], sy = g.p[k + 1], sz = g.p[k + 2], l = Math.hypot(sx, sz) || 1;
      const X = Math.sign(sx) * Math.pow(Math.abs(sx / l), 0.45) * l, Z = Math.sign(sz) * Math.pow(Math.abs(sz / l), 0.45) * l;
      g.p[k] = 0.175 * X * (1 - 0.07 * (1 - Z * Z)); g.p[k + 2] = 0.12 * Z * (1 - 0.08 * (1 - X * X));
      g.p[k + 1] = sy * (0.004 + 0.034 * Math.sqrt(Math.max(0, (1 - Math.pow(Math.abs(X), 4)) * (1 - Math.pow(Math.abs(Z), 4)))));
    }
    computeNormals(g);
    B.add(g, M4.mul(BH, M4.trs(0, 0.14, -0.10, 0, -80 * DEG)), SEATMAT.yPillow);
  }
  // life-vest pouch: dark saucer-shaped holder under the pan front with a red pull strap hanging from its rim (y_47302:
  // ~0.15-0.18 m discs under each seat) [D]
  B.add(gCyl(0.085, 0.075, 0.035, 14), M4.trs(x0, 0.215, -0.34, 0, -12 * DEG), { c: '#2b2e33', r: 0.6 });
  B.add(gBox(0.02, 0.10, 0.004), M4.trs(x0 + 0.015, 0.15, -0.425, 0, 8 * DEG), { c: '#c8252b', r: 0.5 });
  if (!opts.noScreen) {
    // 13.3 in touchscreen (0.294 x 0.166) in a black glass border 0.316 x 0.205 set flush in the hood face, top ~0.03
    // below the hood's rounded top (y_47305: 600 x 390 px at 1905 px/m, colour (29,26,38); 55 px of shell above) [D]
    const SY = 0.7275;
    B.add(gRBox(0.322, 0.211, 0.004, 0.007, 1), on(SY, -0.0005), { c: '#9ea2a8', r: 0.5 });      // shadow gap round the glass
    B.add(gRBox(0.316, 0.205, 0.004, 0.006, 1), on(SY, 0.001), { c: '#1d1a26', r: 0.22 });
    B.add(gQuad(0.294, 0.166), on(SY, 0.0035), SEATMAT.screen, atlasUV('screen'));
    // IFE handset docked in a dark recess 0.04 below the bezel (y_47305, sanspotter 15/27): dark-navy pill with an oval
    // key, a D-pad ring + OK, +/- rockers, a round key and four colour keys in a diamond (blue top, green left, red
    // right, yellow bottom) [D]
    const HY = 0.577, hz = (y, dz, dx) => M4.mul(on(y, dz, dx), M4.trs(0, 0, 0, 0, Math.PI / 2));
    B.add(gRBox(0.165, 0.05, 0.01, 0.022, 1), on(HY, 0.0), { c: '#15171d', r: 0.5 });
    // black handset filling ~0.76 of the dock, with the separate release key at the dock's left end (w3 A) [D]
    const HX = 0.012;
    B.add(gRBox(0.125, 0.04, 0.012, 0.018, 1), on(HY, 0.004, HX), { c: '#1a1b20', r: 0.35 });
    const key = (dx, dy, r, c, h = 0.003) => B.add(gCyl(r, r, h, r > 0.008 ? 16 : 8, true), hz(HY + dy, 0.0105, dx), { c, r: 0.35, e: /^#(3a|40|e0)/.test(c) ? 0.25 : 0 });
    key(-0.068, 0, 0.006, '#3a3f52', 0.004);
    key(HX - 0.033, 0, 0.0125, '#3a3f52'); key(HX - 0.033, 0, 0.0100, '#20242f', 0.004); key(HX - 0.033, 0, 0.0045, '#3a3f52', 0.005);
    for (const dy of [0.008, -0.008]) B.add(gBox(0.006, 0.011, 0.005), on(HY + dy, 0.011, HX - 0.012), { c: '#3a3f52', r: 0.35 });
    key(HX + 0.004, 0, 0.0045, '#3a3f52');
    [['#3aa0ff', 0, 0.008], ['#40c070', -0.008, 0], ['#e04040', 0.008, 0], ['#e0c040', 0, -0.008]].forEach(([c, dx, dy]) => key(HX + 0.036 + dx, dy, 0.0034, c));
    // stowed tray reaching up under the hood lip, carrying the pictogram placard (left), the dark latch and the round
    // cup / coat-hook recess (right) (sanspotter 15, y_47303); the long "stow and latch handset" placard along its foot
    // above the metal rail; flat arms drop from hinge blocks at the rail ends to off-white barrel hubs at pocket-top
    // level (sanspotter 15 / 23, y_47307; w4 A: the w3 arms stood up the wrong way) [D]
    B.add(gRBox(0.33, 0.235, 0.018, 0.01, 1), on(0.353, 0.009), SEATMAT.yTray);
    B.add(gQuad(0.055, 0.022), on(0.425, 0.0185, -0.10), { c: '#eceded', r: 0.5 });
    B.add(gCyl(0.027, 0.027, 0.004, 16), hz(0.415, 0.0185, 0.10), { c: '#b9bdc3', r: 0.45 });
    B.add(gCyl(0.02, 0.02, 0.004, 16), hz(0.415, 0.02, 0.10), { c: '#c9ccd0', r: 0.45 });
    B.add(gRBox(0.052, 0.022, 0.014, 0.004, 1), on(0.47, 0.012), { c: '#6f737a', r: 0.4 });
    B.add(gQuad(0.24, 0.018), on(0.252, 0.0185), { c: '#eef0f2', r: 0.5 });
    B.add(gQuad(0.20, 0.003), on(0.25, 0.019), { c: '#8a8e94', r: 0.5 });
    B.add(gCyl(0.008, 0.008, 0.40, 8), M4.mul(on(0.222, 0.012), M4.trs(0, 0, 0, 0, 0, Math.PI / 2)), SEATMAT.frame);
    for (const s of [-1, 1]) {
      const xa = (y, dz, dx) => M4.mul(on(y, dz, dx), M4.trs(0, 0, 0, 0, 0, Math.PI / 2));
      B.add(gRBox(0.022, 0.032, 0.03, 0.006, 1), on(0.222, 0.012, s * 0.198), SEATMAT.armPost);
      B.add(gRBox(0.02, 0.11, 0.018, 0.006, 1), on(0.165, 0.012, s * 0.205), SEATMAT.armPost);
      B.add(gCyl(0.03, 0.03, 0.045, 12), xa(0.105, 0.022, s * 0.198), SEATMAT.arm);      // w5 B: inside the shell side
      for (const g of [-0.011, 0.011]) B.add(gCyl(0.0305, 0.0305, 0.003, 12, false), xa(0.105, 0.022, s * 0.198 + g), { c: '#9ea3a9', r: 0.45 });
    }
    // universal AC socket (portrait, ~0.046 x 0.054) with a lit blue USB port and green LED in a square light bezel, left,
    // between the tray rail and the pocket (y_47307, sanspotter 21) [V]
    B.add(gRBox(0.062, 0.062, 0.006, 0.006, 1), on(0.18, 0.004, -0.15), { c: '#c2c5c9', r: 0.45 });
    B.add(gRBox(0.046, 0.054, 0.004, 0.003, 1), on(0.18, 0.007, -0.15), { c: '#26282c', r: 0.45 });
    B.add(gQuad(0.014, 0.005), on(0.198, 0.0092, -0.15), { c: '#4a90ff', r: 0.3, e: 0.8 });
    B.add(gQuad(0.004, 0.004), on(0.188, 0.0092, -0.137), { c: '#40e060', r: 0.3, e: 0.9 });
    for (const [dx, dy] of [[0, 0.004], [-0.013, -0.014], [0.013, -0.014]]) B.add(gQuad(0.007, 0.009), on(0.18 + dy, 0.0092, -0.15 + dx), SEATMAT.port);
    // literature pocket between the hubs: a bulging light-grey flap (~0.27 wide) with piping over a see-through black
    // net, the purple-headed "B777-300" safety card (~0.21 wide) standing above the flap (sanspotter 20 / 21 / 23) [V]
    B.add(gQuad(0.26, 0.01), on(0.147, 0.0135), { c: '#3a3c42', r: 0.7 });                       // pocket mouth
    B.add(gRBox(0.21, 0.055, 0.003, 0.002, 1), on(0.152, 0.016, 0.035), { c: '#f4f4f6', r: 0.6 });
    B.add(gQuad(0.21, 0.024), on(0.168, 0.0177, 0.035), { c: '#5b3a8e', r: 0.6 });
    B.add(gQuad(0.10, 0.008), on(0.168, 0.0179, 0.035), { c: '#ffffff', r: 0.6 });
    for (let k = 0; k < 4; k++) B.add(gQuad(0.015, 0.012), on(0.15, 0.0176, -0.02 + k * 0.035), { c: '#8a8d94', r: 0.6 });
    B.add(gLoft([SEC(-0.035, 0.26, 0.012, 0, 0.005), SEC(0.0, 0.27, 0.022, 0.004, 0.008), SEC(0.035, 0.26, 0.012, 0, 0.005)], 2), on(0.115, 0.022), { c: '#bdc0c4', r: 0.5, l: LAYER.plastic });
    B.add(gCyl(0.004, 0.004, 0.27, 8), M4.mul(on(0.15, 0.032), M4.trs(0, 0, 0, 0, 0, Math.PI / 2)), { c: '#a9acb1', r: 0.5 });
    // w5 A + B: the net is a see-through black mesh reaching ~0.02 past the flap each side, with a ruched elastic top
    // (sans 23); no alpha here, so a lighter mesh tone lets the grille pattern read as holes [D]
    B.add(gRBox(0.31, 0.07, 0.014, 0.02, 2), on(0.05, 0.02), { c: '#2a2c31', r: 0.8, l: LAYER.grille });
    B.add(gCyl(0.007, 0.007, 0.31, 8), M4.mul(on(0.084, 0.027), M4.trs(0, 0, 0, 0, 0, Math.PI / 2)), { c: '#303238', r: 0.9, l: LAYER.fabric });
  }
  // footrest for the passenger behind: two off-white hanger arms clamped to the rear spreader tube, carrying ribbed
  // aluminium pedals (y_47304)
  // w5 B: the hangers come down at the seat centreline, ~0.07 apart (sans 23), and land on the joint between the two
  // pedals (y_47304), each one bowed flat arm [V]
  if (opts.footrest !== false) {
    for (const s of [-1, 1]) {
      const hx = x0 + s * 0.035;
      B.add(gRBox(0.035, 0.03, 0.04, 0.008, 1), M4.trs(hx, 0.30, -0.10), SEATMAT.frame);
      for (let i = 0; i < 4; i++) B.add(gRBox(0.036, 0.062, 0.022, 0.009, 1), M4.trs(hx, 0.27 - i * 0.05, -0.095 + i * 0.026 + i * i * 0.004, 0, (-12 - i * 9) * DEG), SEATMAT.arm);
      // brushed pedal (~0.15 each, w4 B) with longitudinal grooves ~5 mm apart and a dark cap at its outer end (y_47304)
      const px = x0 + s * 0.085;
      B.add(gRBox(0.15, 0.02, 0.05, 0.008, 1), M4.trs(px, 0.11, 0.0), { c: '#9a9ea4', m: 0.8, r: 0.35, l: LAYER.brushed });
      for (let g = -3; g <= 3; g++) B.add(gQuad(0.138, 0.0018), M4.trs(px, 0.1205, g * 0.006, 0, -Math.PI / 2), { c: '#6d7178', m: 0.7, r: 0.5 });
      B.add(gBox(0.01, 0.022, 0.052), M4.trs(px + s * 0.077, 0.11, 0.0), { c: '#4a4e55', r: 0.5 });
    }
    B.add(gBox(0.02, 0.024, 0.054), M4.trs(x0, 0.11, 0.0), { c: '#4a4e55', r: 0.5 });   // shared joint block
  }
  // belt: silver tongue one side, light-grey plastic buckle cover the other (y_47303); w5 A: the webbing drapes across the
  // pan from the side creases and the latch sits at mid-pan (y_47302 / 47301 / 47303) [V]
  for (const s of [-1, 1]) {
    B.add(s < 0 ? gRBox(0.05, 0.012, 0.035, 0.005, 1) : gRBox(0.05, 0.014, 0.04, 0.006, 1), M4.trs(x0 + 0.03 * s, 0.478, -0.31), s < 0 ? SEATMAT.buckle : { c: '#cfd2d6', r: 0.4 });
    B.add(gBox(0.045, 0.004, 0.25), M4.trs(x0 + 0.115 * s, 0.474, -0.195, s * 38 * DEG), SEATMAT.yBelt);
  }
  // pan-front stiffener in the light-grey structure colour (y_47300 / 47302: fabric pan fronts over light-grey structure,
  // no black bar) - QA r2, was black
  B.add(gRBox(0.30, 0.04, 0.10, 0.01, 1), M4.trs(x0, 0.31, -0.45), SEATMAT.yShellDark);
  // white seat-electronics box under the pan front, dark face (y_47302) [D]
  {
    B.add(gRBox(0.07, 0.07, 0.05, 0.008, 1), M4.trs(x0 - 0.12, 0.26, -0.43), SEATMAT.yShell);
    B.add(gQuad(0.05, 0.04), M4.trs(x0 - 0.12, 0.26, -0.4555, Math.PI), { c: '#22252b', r: 0.5 });
  }
}

function econUnit(n, lod = false, opts = {}) {
  const B = new Builder();
  const sp = ECON.sp;
  const xs = []; for (let k = 0; k < n; k++) xs.push((k - (n - 1) / 2) * sp);
  xs.forEach((x, k) => econSeat(B, x, lod, { ...opts, fab: econFab(k, n, opts.rot) }));
  const arms = []; for (let k = 0; k <= n; k++) arms.push((k - n / 2) * sp);
  arms.forEach((xa, k) => {
    // sculpted off-white armrest (thick, rounded, slightly drooping nose) on a rear pivot post (y_47302 / 47303)
    // w5 B: a slim ~5.5 cm bar (y_47303 28 px on a 0.33 m / 160 px arm; fr57325 124108) with a drooping nose [D]
    loftAt(B, [SEC(0.625, 0.046, 0.32, -0.24, 0.016), SEC(0.64, 0.054, 0.34, -0.24, 0.024), SEC(0.668, 0.052, 0.335, -0.24, 0.024), SEC(0.68, 0.044, 0.32, -0.235, 0.018)], M4.trs(xa, 0, 0), SEATMAT.arm, 3);
    B.add(gRBox(0.05, 0.045, 0.05, 0.02, 2), M4.trs(xa, 0.64, -0.40, 0, -20 * DEG), SEATMAT.arm);
    // front end: one continuous grey bracket from under the arm nose down past the pan, with a pivot ring at pan height;
    // the white paddle hangs from it (y_47302 / 47303; w2 B: was a ball on a stick) [D]
    loftAt(B, [SEC(0.30, 0.036, 0.032, -0.37, 0.014), SEC(0.46, 0.04, 0.036, -0.385, 0.016), SEC(0.62, 0.04, 0.036, -0.395, 0.016)], M4.trs(xa, 0, 0), SEATMAT.armPost, 2);   // w5 B: slimmer
    if (!lod) {
      B.add(gCyl(0.02, 0.02, 0.064, 12), M4.trs(xa, 0.46, -0.39, 0, 0, Math.PI / 2), { c: '#9ea3a9', r: 0.4 });
      B.add(gCyl(0.009, 0.009, 0.066, 8), M4.trs(xa, 0.46, -0.39, 0, 0, Math.PI / 2), { c: '#3a3e45', r: 0.4 });
    }
    B.add(gRBox(0.05, 0.008, 0.24, 0.004, 1), M4.trs(xa, 0.678, -0.235), SEATMAT.armPad);
    B.add(gRBox(0.036, 0.23, 0.06, 0.014, 1), M4.trs(xa, 0.51, -0.09), SEATMAT.arm);
    // off-white fairing hanging under the arm nose down to ~0.14 m above the floor (the white "paddles" in y_47302:
    // 0.54 -> 0.14 m at 422 px/m) [D]
    B.add(gRBox(0.03, 0.32, 0.14, 0.012, 2), M4.trs(xa, 0.30, -0.35, 0, -6 * DEG), SEATMAT.arm);
    if (k === 0 || k === arms.length - 1) {
      // block end: sculpted off-white side panel under the armrest, tapering from the full arm length down + forward
      // toward the front leg (y_47302 right-hand aisle seat, y_47301 aisle ends)
      const o = k === 0 ? -1 : 1;
      loftAt(B, [SEC(0.16, 0.018, 0.12, -0.34, 0.007), SEC(0.40, 0.018, 0.26, -0.28, 0.007), SEC(0.62, 0.018, 0.36, -0.23, 0.007)], M4.trs(xa + o * 0.012, 0, 0), SEATMAT.yShell, 2);
      B.add(gRBox(0.02, 0.09, 0.05, 0.008, 1), M4.trs(xa + o * 0.024, 0.46, -0.40), { c: '#1d1f24', r: 0.4 });   // black button strip (y_47302)
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
  // low silver baggage bar across the front legs (y_47302)
  B.add(gCyl(0.011, 0.011, W - 0.06, 8), M4.trs(0, 0.10, -0.34, 0, 0, Math.PI / 2), SEATMAT.frame);
  if (!lod) {
    B.add(gRBox(0.22, 0.10, 0.30, 0.012, 1), M4.trs(xs[xs.length - 1] - 0.05, 0.19, -0.22), SEATMAT.black);
  }
  return B.build();
}
function econUnitFar(n, rot = 0) {
  const B = new Builder();
  const sp = ECON.sp;
  for (let k = 0; k < n; k++) {
    const x0 = (k - (n - 1) / 2) * sp;
    const f = econFab(k, n, rot);
    B.add(gRBox(0.43, 0.10, 0.47, 0.04, 1), M4.trs(x0, 0.41, -0.28, 0, 3 * DEG), f === SEATMAT.yFabricB ? SEATMAT.yFabric : f);
    const BH = M4.trs(x0, ECON.hinge[0], ECON.hinge[1], 0, ECON.back);
    B.add(gRBox(0.42, 0.86, 0.08, 0.035, 1), M4.mul(BH, M4.trs(0, 0.43, -0.005)), f);   // same mix as econUnit
    B.add(gRBox(0.446, 0.62, 0.045, 0.015, 1), M4.mul(BH, M4.trs(0, 0.25, 0.058)), SEATMAT.yShell);
    B.add(gRBox(0.375, 0.40, 0.12, 0.035, 1), M4.mul(BH, M4.trs(0, 0.68, 0.062)), SEATMAT.yShell);    // screen hood, capping the back top (w5)
    B.add(gRBox(0.37, 0.2, 0.09, 0.035, 1), M4.mul(BH, M4.trs(0, 0.70, -0.05)), f === SEATMAT.yFabricC ? SEATMAT.yFabric : f === SEATMAT.yFabricD ? f : SEATMAT.yHead);
    B.add(gBox(0.27, 0.225, 0.01), M4.mul(BH, M4.trs(0, 0.6875, -0.1)), SEATMAT.yCover);
    B.add(gQuad(0.316, 0.205), M4.mul(BH, M4.trs(0, 0.7275, 0.1245)), SEATMAT.bezel);
    B.add(gQuad(0.294, 0.166), M4.mul(BH, M4.trs(0, 0.7275, 0.1265)), SEATMAT.screen, atlasUV('screen'));
  }
  for (let k = 0; k <= n; k++) B.add(gBox(0.048, 0.05, 0.30), M4.trs((k - n / 2) * sp, 0.64, -0.235), SEATMAT.arm);
  return B.build();
}
