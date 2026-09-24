// ------------------------------------------------------------------
// Seat models for the ANA 777-300ER (see REFERENCE777.md)
// Seat-local frame: x across, y up, z = 0 at the seat-back reference, passenger faces -z
// ------------------------------------------------------------------
const SEATMAT = {
  // Economy (Recaro): royal-blue tick jacquard, slate leatherette headrest covers, off-white shells + arms,
  // teal belts, navy pillows -- all read from ANA's official Y photos (ref/ana/y_4730x; REFERENCE777.md)
  yFabric: { c: '#3d4d88', r: 0.9, l: LAYER.yJacq },
  yHead: { c: '#3d4d88', r: 0.9, l: LAYER.yJacq },
  yCover: { c: '#3e4661', r: 0.5, l: LAYER.leather },
  yShell: { c: '#d9dbde', r: 0.42, l: LAYER.plastic },
  yShellDark: { c: '#c2c5c9', r: 0.5, l: LAYER.plastic },
  yTray: { c: '#cfd2d6', r: 0.4, l: LAYER.plastic },
  yBelt: { c: '#2f7394', r: 0.7, l: LAYER.fabric },
  yPillow: { c: '#232a4e', r: 0.9, l: LAYER.fabric },
  arm: { c: '#d3d6d9', r: 0.45, l: LAYER.plastic },
  armPad: { c: '#c6c9cd', r: 0.5, l: LAYER.plastic },
  frame: { c: '#a3a8ae', r: 0.32, m: 0.85, l: LAYER.brushed },
  black: { c: '#15181c', r: 0.45 },
  port: { c: '#0b0c0e', r: 0.4 },
  bezel: { c: '#101215', r: 0.22 },
  screen: { c: '#ffffff', r: 0.2, l: 13, e: 0.9 },
  buckle: { c: '#c3c7cc', r: 0.25, m: 0.9 },
  strap: { c: '#34383f', r: 0.8 },
  pocket: { c: '#2a2e35', r: 0.85, l: LAYER.fabric },
  card: { c: '#d8dde4', r: 0.7 },
  ledG: { c: '#39e07a', r: 0.3, e: 0.8 },
  // Premium Economy (ZIM): charcoal/white fleck heather (reads light grey), navy leatherette headrest flap,
  // mid-grey shells + consoles with a silver trim line (ref/ana/py_3730x)
  pyFabric: { c: '#7c8494', r: 0.9, l: LAYER.pyFleck },
  pyCover: { c: '#3d4459', r: 0.5, l: LAYER.leather },
  pyWing: { c: '#5f6676', r: 0.9, l: LAYER.pyConfetti },
  pyShell: { c: '#5c6470', r: 0.42, l: LAYER.plastic },
  pyArm: { c: '#56606c', r: 0.45, l: LAYER.plastic },
  pyArmPad: { c: '#767b82', r: 0.5, l: LAYER.leather },
  pyTrim: { c: '#b9bec4', r: 0.28, m: 0.8, l: LAYER.brushed },
  // THE Room (Safran Fusio custom). Colours sampled from ANA's official seat photos (ref/ana/c_273xx, see REFERENCE777.md):
  // pale grey-beige ash with fine straight grain, charcoal shells with lighter cap rails, charcoal tweed seat,
  // slate Ultraleather headrest flap, navy pillow, dark recessed seat base
  ash: { c: '#c9c2b3', r: 0.48, l: LAYER.ashGrain },
  ashDark: { c: '#5d6166', r: 0.34, m: 0.35, l: LAYER.brushed },
  rosewood: { c: '#4b403a', r: 0.36, l: LAYER.wood },
  jShell: { c: '#505358', r: 0.46, l: LAYER.plastic },
  jShellIn: { c: '#46494e', r: 0.5, l: LAYER.plastic },
  jRail: { c: '#8a8e94', r: 0.26, m: 0.45, l: LAYER.brushed },
  jBase: { c: '#2a2b2f', r: 0.6 },
  jFabric: { c: '#55545b', r: 0.92, l: LAYER.tweed },
  jLeather: { c: '#4b4d53', r: 0.5, l: LAYER.leather },
  jHead: { c: '#6b7582', r: 0.45, l: LAYER.leather },
  blueAccent: { c: '#233f7a', r: 0.5 },
  slate: { c: '#3f4246', r: 0.55, l: LAYER.marble },
  mattress: { c: '#f0efea', r: 0.9, l: LAYER.fabric },
  duvet: { c: '#34558f', r: 0.95, l: LAYER.fabric },
  pillow: { c: '#eeede8', r: 0.9, l: LAYER.fabric },
  pillowBlue: { c: '#262c5a', r: 0.85, l: LAYER.fabric },
  lampGlow: { c: '#ffe2b0', r: 0.4, e: 0.35 },
  moodGlow: { c: '#ffd9a0', r: 0.5, e: 0.25 },
  hole: { c: '#0b0d10', r: 1.0 },
  mirror: { c: '#aeb6bf', r: 0.08, m: 0.9 },
  // THE Suite (JAMCO). Colours from ANA's real suite photos f_17313 / f_17314 (warm taupe-grey shells, dark
  // straight-grain wood, warm mid-grey tweed seat + ottoman, violet-navy pillow); renders f_17300-17309 give the
  // fluted exterior, floor LED line, window console controls and headrest flap
  fShell: { c: '#69655f', r: 0.45, l: LAYER.plastic },
  fFlute: { c: '#5f5852', r: 0.5, l: LAYER.plastic },
  fWood: { c: '#3b322d', r: 0.38, l: LAYER.fWood },
  fDoor: { c: '#736c65', r: 0.45, l: LAYER.plastic },
  fInner: { c: '#5d5752', r: 0.5, l: LAYER.plastic },
  fFabric: { c: '#5e5857', r: 0.92, l: LAYER.fTweed },
  fLeather: { c: '#4f4b49', r: 0.48, l: LAYER.leather },
  fFlap: { c: '#6d6a68', r: 0.45, l: LAYER.leather },
  fCushionBlue: { c: '#3d3875', r: 0.85, l: LAYER.fabric },
  fShelf: { c: '#342b26', r: 0.35, l: LAYER.fWood },
  fWarm: { c: '#ffe7c4', r: 0.5, e: 0.55 },
  fLed: { c: '#f4f1ea', r: 0.5, e: 0.7 },
};

function loftAt(B, secs, xf, mat, seg = 4) { B.add(gLoft(secs, seg), xf, mat); }
const SEC = (y, w, d, z = 0, r = 0.03, x = 0) => ({ y, w, d, z, r, x });
const X = (...m) => m.reduce((a, b) => M4.mul(a, b));

// ================= ECONOMY (Recaro, 17 in, 13.3 in screen, 6-way headrest, footrest) =================
const ECON = { back: 13 * DEG, hinge: [0.47, -0.075], sp: 19 * IN };
function econSeat(B, x0, lod, opts = {}) {
  const [hy, hz] = ECON.hinge;
  const F = SEATMAT.yFabric;
  const BH = M4.trs(x0, hy, hz, 0, ECON.back);
  B.add(gLoft(cushionSecs(0.43, 0.47, 0.095, -0.05, { edge: 0.034, r: 0.03, crown: 0.01 }), lod ? 3 : 4), M4.trs(x0, 0.415, -0.28, 0, 3 * DEG), F);
  B.add(gRBox(0.44, 0.035, 0.46, 0.012, 1), M4.trs(x0, 0.35, -0.27), SEATMAT.yShellDark);
  loftAt(B, [SEC(0.0, 0.40, 0.07, -0.005, 0.02), SEC(0.04, 0.425, 0.09, -0.012), SEC(0.16, 0.43, 0.108, -0.024, 0.036), SEC(0.30, 0.43, 0.095, -0.014, 0.036),
    SEC(0.46, 0.425, 0.086, -0.006, 0.034), SEC(0.58, 0.41, 0.076, 0.0, 0.03), SEC(0.62, 0.38, 0.055, 0.004, 0.022)], BH, F, lod ? 3 : 4);
  // slim rear shell, thicker where the screen sits
  const zr = (y) => 0.075 + 0.014 * Math.sin(Math.PI * clamp(y / 0.74, 0, 1));
  const ds = [[-0.03, 0.03], [0.1, 0.03], [0.3, 0.034], [0.46, 0.05], [0.62, 0.064], [0.70, 0.058], [0.745, 0.04]];
  loftAt(B, ds.map(([y, d]) => SEC(y, 0.446, d, zr(y) - d / 2, 0.018)), BH, SEATMAT.yShell, lod ? 2 : 3);
  // 6-way headrest: centre pad + fold-in wings
  loftAt(B, [SEC(0.62, 0.33, 0.07, -0.004, 0.03), SEC(0.645, 0.35, 0.08, -0.008, 0.034), SEC(0.77, 0.35, 0.082, -0.01, 0.034), SEC(0.81, 0.33, 0.07, -0.006, 0.03), SEC(0.825, 0.29, 0.05, -0.002, 0.022)], BH, SEATMAT.yHead, lod ? 3 : 4);
  for (const s of [-1, 1]) {
    const WX = M4.mul(BH, M4.trs(s * 0.182, 0, -0.012, -s * 20 * DEG));
    loftAt(B, [SEC(0.65, 0.05, 0.07, 0, 0.02), SEC(0.79, 0.05, 0.07, 0, 0.02), SEC(0.81, 0.04, 0.055, 0, 0.018)], WX, SEATMAT.yHead, 2);
  }
  // slate leatherette cover draped over the headrest front + top (y_47302 / 47306)
  B.add(gRBox(0.27, 0.13, 0.008, 0.006, 1), M4.mul(BH, M4.trs(0, 0.76, -0.062)), SEATMAT.yCover);
  B.add(gRBox(0.27, 0.008, 0.06, 0.004, 1), M4.mul(BH, M4.trs(0, 0.822, -0.035)), SEATMAT.yCover);
  if (lod) return;
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz));
  // navy pillow leaning on the back (y_47300)
  if (opts.pillow !== false) B.add(gLoft(cushionSecs(0.30, 0.22, 0.08, -0.04, { edge: 0.035, r: 0.04 }), 3), M4.mul(BH, M4.trs(0, 0.17, -0.135, 0, -80 * DEG)), SEATMAT.yPillow);
  // life-vest pouch tab under the seat front (red pull tab, y_47302)
  B.add(gRBox(0.12, 0.05, 0.03, 0.01, 1), M4.trs(x0, 0.30, -0.52), SEATMAT.yShellDark);
  B.add(gBox(0.018, 0.045, 0.006), M4.trs(x0 + 0.02, 0.27, -0.537), { c: '#c8252b', r: 0.5 });
  if (!opts.noScreen) {
    // 13.3 in touchscreen (0.294 x 0.166): thick off-white surround + black glass border (y_47303 / 47305)
    B.add(gRBox(0.35, 0.215, 0.018, 0.012, 1), on(0.575, 0.001), SEATMAT.yShell);
    B.add(gRBox(0.316, 0.184, 0.004, 0.006, 1), on(0.575, 0.0095), SEATMAT.bezel);
    B.add(gQuad(0.294, 0.166), on(0.575, 0.0125), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.016, 0.007, 0.004), on(0.465, 0.002, -0.03), SEATMAT.port);
    B.add(gCyl(0.004, 0.004, 0.004, 8), M4.mul(on(0.465, 0.002, 0.03), M4.trs(0, 0, 0, 0, Math.PI / 2)), SEATMAT.port);
    // high literature pocket, tray table + latch, cup recess
    B.add(gRBox(0.36, 0.09, 0.02, 0.01, 1), on(0.405, 0.01), SEATMAT.pocket);
    B.add(gRBox(0.40, 0.24, 0.018, 0.01, 1), on(0.235, 0.009), SEATMAT.yTray);
    B.add(gRBox(0.36, 0.2, 0.004, 0.008, 1), on(0.235, 0.019), { c: '#4a4e55', r: 0.5, l: LAYER.plastic });
    B.add(gRBox(0.05, 0.016, 0.012, 0.005, 1), on(0.36, 0.012), SEATMAT.black);
    B.add(gBox(0.17, 0.03, 0.004), on(0.40, 0.022), SEATMAT.card);
  }
  // footrest bar for the passenger behind (folded up under the seat back)
  if (opts.footrest !== false) {
    B.add(gRBox(0.30, 0.03, 0.05, 0.01, 1), M4.trs(x0, 0.16, 0.03), SEATMAT.black);
    for (const s of [-1, 1]) B.add(gBox(0.015, 0.14, 0.015), M4.trs(x0 + s * 0.14, 0.22, 0.02), SEATMAT.frame);
  }
  for (const s of [-1, 1]) {
    B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.trs(x0 + 0.028 * s, 0.473, -0.25), SEATMAT.buckle);
    B.add(gBox(0.045, 0.004, 0.16), M4.trs(x0 + 0.12 * s, 0.471, -0.18, s * 14 * DEG), SEATMAT.yBelt);
  }
  B.add(gRBox(0.30, 0.04, 0.10, 0.01, 1), M4.trs(x0, 0.31, -0.45), SEATMAT.black);
}

function econUnit(n, lod = false, opts = {}) {
  const B = new Builder();
  const sp = ECON.sp;
  const xs = []; for (let k = 0; k < n; k++) xs.push((k - (n - 1) / 2) * sp);
  xs.forEach((x) => econSeat(B, x, lod, opts));
  const arms = []; for (let k = 0; k <= n; k++) arms.push((k - n / 2) * sp);
  for (const xa of arms) {
    loftAt(B, [SEC(0.61, 0.046, 0.30, -0.235, 0.018), SEC(0.645, 0.05, 0.31, -0.235, 0.022), SEC(0.665, 0.048, 0.30, -0.235, 0.02)], M4.trs(xa, 0, 0), SEATMAT.arm, 2);
    B.add(gRBox(0.048, 0.012, 0.26, 0.006, 1), M4.trs(xa, 0.668, -0.24), SEATMAT.armPad);
    B.add(gRBox(0.032, 0.21, 0.05, 0.01, 1), M4.trs(xa, 0.52, -0.09), SEATMAT.arm);
    if (!lod) B.add(gCyl(0.006, 0.006, 0.01, 8), M4.trs(xa, 0.64, -0.39, 0, Math.PI / 2), SEATMAT.frame);
  }
  const W = n * sp;
  const legX = n >= 3 ? [-(W / 2 - 0.24), W / 2 - 0.24] : [-0.24, 0.24];
  for (const lx of legX) {
    B.add(gRBox(0.035, 0.31, 0.045, 0.01, 1), M4.trs(lx, 0.155, -0.06), SEATMAT.frame);
    B.add(gRBox(0.035, 0.34, 0.045, 0.01, 1), M4.trs(lx, 0.16, -0.36, 0, -22 * DEG), SEATMAT.frame);
    B.add(gRBox(0.04, 0.05, 0.46, 0.01, 1), M4.trs(lx, 0.31, -0.22), SEATMAT.frame);
    B.add(gBox(0.05, 0.025, 0.12), M4.trs(lx, 0.012, -0.06), SEATMAT.black);
    B.add(gBox(0.05, 0.025, 0.12), M4.trs(lx, 0.012, -0.44), SEATMAT.black);
  }
  for (const zb of [-0.1, -0.40]) B.add(gCyl(0.02, 0.02, W - 0.04, 10), M4.trs(0, 0.30, zb, 0, 0, Math.PI / 2), SEATMAT.frame);
  if (!lod) {
    B.add(gRBox(0.22, 0.10, 0.30, 0.012, 1), M4.trs(xs[xs.length - 1] - 0.05, 0.19, -0.22), SEATMAT.black);
    // universal AC outlets near the seat pocket (ANA: easy-to-reach position)
    for (const x of xs) B.add(gRBox(0.04, 0.03, 0.01, 0.004, 1), M4.trs(x + 0.16, 0.36, 0.085), SEATMAT.black);
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
    B.add(gRBox(0.35, 0.2, 0.08, 0.03, 1), M4.mul(BH, M4.trs(0, 0.72, -0.008)), SEATMAT.yHead);
    B.add(gBox(0.27, 0.13, 0.01), M4.mul(BH, M4.trs(0, 0.76, -0.055)), SEATMAT.yCover);
    B.add(gQuad(0.294, 0.166), M4.mul(BH, M4.trs(0, 0.575, 0.09)), SEATMAT.screen, atlasUV('screen'));
  }
  for (let k = 0; k <= n; k++) B.add(gBox(0.048, 0.05, 0.30), M4.trs((k - n / 2) * sp, 0.64, -0.235), SEATMAT.arm);
  return B.build();
}

// ================= PREMIUM ECONOMY (ZIM, 19 in, 15.6 in screen, leg rest + bicycle footrest) =================
const PY = { back: 14 * DEG, hinge: [0.48, -0.09], sp: 0.5715 };
function pySeat(B, x0, lod, opts = {}) {
  const [hy, hz] = PY.hinge;
  const F = SEATMAT.pyFabric;
  const BH = M4.trs(x0, hy, hz, 0, PY.back);
  B.add(gLoft(cushionSecs(0.48, 0.50, 0.115, -0.06, { edge: 0.04, r: 0.035, crown: 0.012 }), lod ? 3 : 4), M4.trs(x0, 0.425, -0.30, 0, 3 * DEG), F);
  B.add(gRBox(0.49, 0.05, 0.48, 0.012, 1), M4.trs(x0, 0.335, -0.29), SEATMAT.pyShell);
  loftAt(B, [SEC(0.0, 0.44, 0.09, -0.01, 0.025), SEC(0.05, 0.47, 0.115, -0.02), SEC(0.18, 0.48, 0.13, -0.032, 0.045), SEC(0.34, 0.48, 0.12, -0.024, 0.045),
    SEC(0.52, 0.47, 0.11, -0.014, 0.042), SEC(0.64, 0.45, 0.095, -0.008, 0.036), SEC(0.68, 0.42, 0.07, 0.0, 0.028)], BH, F, lod ? 3 : 4);
  // thick rear shell
  const zr = (y) => 0.105 + 0.014 * Math.sin(Math.PI * clamp(y / 0.84, 0, 1));
  const ds = [[-0.04, 0.04], [0.12, 0.04], [0.34, 0.046], [0.5, 0.064], [0.68, 0.074], [0.78, 0.066], [0.85, 0.05]];
  loftAt(B, ds.map(([y, d]) => SEC(y, 0.505, d, zr(y) - d / 2, 0.022)), BH, SEATMAT.pyShell, lod ? 2 : 3);
  // 6-way headrest with wings
  loftAt(B, [SEC(0.68, 0.37, 0.08, -0.006, 0.032), SEC(0.71, 0.39, 0.092, -0.012, 0.04), SEC(0.85, 0.39, 0.092, -0.012, 0.04), SEC(0.895, 0.37, 0.075, -0.006, 0.032), SEC(0.91, 0.33, 0.05, -0.002, 0.02)], BH, F, lod ? 3 : 4);
  for (const s of [-1, 1]) {
    // large rounded wing pads either side of the flap (py_37301 / 37302)
    const WX = M4.mul(BH, M4.trs(s * 0.195, 0, -0.03, -s * 18 * DEG));
    loftAt(B, [SEC(0.69, 0.08, 0.09, 0, 0.03), SEC(0.72, 0.095, 0.11, 0, 0.042), SEC(0.87, 0.095, 0.11, 0, 0.042), SEC(0.90, 0.08, 0.08, 0, 0.03)], WX, SEATMAT.pyWing, lod ? 2 : 3);
  }
  // navy leatherette flap over the headrest front + top, silver trim line low on the back shell (py_37303)
  B.add(gRBox(0.27, 0.20, 0.008, 0.006, 1), M4.mul(BH, M4.trs(0, 0.795, -0.064)), SEATMAT.pyCover);
  B.add(gRBox(0.27, 0.008, 0.07, 0.004, 1), M4.mul(BH, M4.trs(0, 0.904, -0.03)), SEATMAT.pyCover);
  B.add(gBox(0.50, 0.008, 0.006), M4.mul(BH, M4.trs(0, 0.04, zr(0.04) + 0.022)), SEATMAT.pyTrim);
  // fold-up leg rest (stowed below the pan front)
  B.add(gLoft([SEC(0.0, 0.44, 0.05, 0, 0.018), SEC(0.30, 0.46, 0.06, 0, 0.022)], 3), M4.trs(x0, 0.07, -0.545, 0, -4 * DEG), F);
  B.add(gRBox(0.46, 0.02, 0.05, 0.008, 1), M4.trs(x0, 0.075, -0.54), SEATMAT.pyArm);            // leg-rest foot bar
  if (lod) return;
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz));
  if (!opts.noScreen) {
    // 15.6 in screen (0.345 x 0.194), pocket + outer net, coat hook
    B.add(gRBox(0.372, 0.22, 0.014, 0.009, 1), on(0.625, 0.004), SEATMAT.bezel);
    B.add(gQuad(0.345, 0.194), on(0.625, 0.0115), SEATMAT.screen, atlasUV('screen'));
    B.add(gRBox(0.40, 0.15, 0.024, 0.012, 1), on(0.36, 0.012), SEATMAT.pocket);
    B.add(gRBox(0.34, 0.08, 0.008, 0.006, 1), on(0.33, 0.026), { c: '#1c1f24', r: 0.9, l: LAYER.grille });
    B.add(gRBox(0.02, 0.05, 0.02, 0.006, 1), on(0.64, 0.012, 0.215), SEATMAT.frame);
  }
  // bicycle-style footrest for the passenger behind (folded)
  B.add(gCyl(0.009, 0.009, 0.32, 8), M4.trs(x0, 0.13, 0.14, 0, 0, Math.PI / 2), SEATMAT.frame);
  for (const s of [-1, 1]) B.add(gRBox(0.12, 0.015, 0.075, 0.006, 1), M4.trs(x0 + s * 0.085, 0.125, 0.18, 0, 12 * DEG), SEATMAT.black);
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
    const w = inner ? 0.085 : 0.07;
    if (inner) {
      // floor-standing console between seats: blue-grey body, silver trim round the top, cubbies + controls on
      // its front face, red life-vest tab at the bottom (py_37301)
      B.add(gRBox(w, 0.62, 0.52, 0.014, 1), M4.trs(xa, 0.31, -0.28), SEATMAT.pyArm);
      loftAt(B, [SEC(0.62, w + 0.01, 0.53, -0.28, 0.02), SEC(0.645, w + 0.014, 0.54, -0.28, 0.025), SEC(0.665, w + 0.006, 0.53, -0.28, 0.02)], M4.trs(xa, 0, 0), SEATMAT.pyArmPad, 2);
      B.add(gBox(w + 0.016, 0.008, 0.545), M4.trs(xa, 0.618, -0.28), SEATMAT.pyTrim);
      if (!lod) {
        for (const [y, h] of [[0.52, 0.07], [0.43, 0.07]]) B.add(gRBox(w - 0.02, h, 0.006, 0.006, 1), M4.trs(xa, y, -0.543), SEATMAT.pyShell);
        B.add(gRBox(w - 0.03, 0.05, 0.004, 0.004, 1), M4.trs(xa, 0.33, -0.544), SEATMAT.black);
        B.add(gBox(0.02, 0.07, 0.006), M4.trs(xa, 0.12, -0.545), { c: '#c8252b', r: 0.5 });
      }
    } else {
      // aisle / window end: large rounded arm shroud from the floor with a silver strip low down (py_37301 / 37303)
      const o = k === 0 ? -1 : 1;
      B.add(gRBox(0.05, 0.64, 0.62, 0.025, 2), M4.trs(xa + o * 0.01, 0.32, -0.27), SEATMAT.pyShell);
      loftAt(B, [SEC(0.62, w, 0.46, -0.27, 0.02), SEC(0.648, w + 0.006, 0.47, -0.27, 0.028), SEC(0.668, w - 0.004, 0.46, -0.27, 0.02)], M4.trs(xa, 0, 0), SEATMAT.pyArmPad, 2);
      B.add(gBox(0.006, 0.012, 0.58), M4.trs(xa + o * 0.037, 0.13, -0.27, 0, 8 * DEG), SEATMAT.pyTrim);
    }
    if (inner && !lod) {      // cocktail table + bottle holders, controls, AC + USB, gooseneck reading light
      B.add(gRBox(w + 0.03, 0.012, 0.12, 0.004, 1), M4.trs(xa, 0.69, -0.02), SEATMAT.pyTrim);
      for (const s of [-1, 1]) B.add(gCyl(0.022, 0.022, 0.1, 12), M4.trs(xa + s * 0.018, 0.63, -0.02), SEATMAT.black);
      B.add(gRBox(0.05, 0.006, 0.08, 0.004, 1), M4.trs(xa, 0.676, -0.3), SEATMAT.black);
      B.add(gBox(0.016, 0.008, 0.004), M4.trs(xa - 0.02, 0.56, -0.502), SEATMAT.port);
      B.add(gBox(0.03, 0.018, 0.004), M4.trs(xa + 0.02, 0.56, -0.502), SEATMAT.port);
      B.add(gTube([[xa, 0.69, 0.02], [xa, 0.86, 0.04], [xa + 0.02, 0.96, 0.0], [xa + 0.05, 0.99, -0.06]], 0.006, 6), null, SEATMAT.black);
      B.add(gCyl(0.016, 0.012, 0.04, 10), M4.trs(xa + 0.06, 0.985, -0.075, 0, 0.9), SEATMAT.black);
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

// ================= THE Room (nested pair unit) =================
// Unit frame: x in [-0.585, 0.585], outer column (window or centreline) at -x, aisle at +x;
// z in [-1.359, 1.359]; forward = -z. O = odd-row seat (rear-facing, outer column, forward half),
// E = even-row seat (forward-facing, aisle column, aft half). Each seat's footwell runs under the other
// seat's side table; each seat's 24 in monitor stands on the neighbour's console (see REFERENCE777.md).
const ROOM = { hx: 0.585, hz: 1.359, top: 0.66, wall: 1.12, bed: 0.43 };
// seat itself (passenger faces -z, back at z = 0): upright or bed. Per c_27302/27315/27316: thin flat cushion and a flat
// upholstered back (one horizontal seam) over a dark recessed base; headrest is a slate flap hanging from the back top
function roomSeatCore(B, bed, lod) {
  const F = SEATMAT.jFabric;
  B.add(gRBox(0.54, 0.33, 0.50, 0.015, 1), M4.trs(0, 0.165, -0.36), SEATMAT.jBase);
  if (bed) {
    B.add(gLoft(cushionSecs(0.64, 0.66, 0.075, -0.035, { edge: 0.02, r: 0.02, crown: 0.003 }), 4), M4.trs(0, 0.39, -0.35), F);
    return;
  }
  B.add(gLoft(cushionSecs(0.64, 0.60, 0.075, -0.035, { edge: 0.022, r: 0.02, crown: 0.004 }), lod ? 3 : 4), M4.trs(0, 0.39, -0.34, 0, 2 * DEG), F);
  const BH = M4.trs(0, 0.43, -0.17, 0, 12 * DEG);     // top of the back leans on the shell (shell face at z = -0.005)
  loftAt(B, [SEC(0.0, 0.62, 0.06, 0, 0.02), SEC(0.025, 0.64, 0.075, 0, 0.026), SEC(0.60, 0.64, 0.075, 0, 0.026), SEC(0.625, 0.62, 0.06, 0.002, 0.02)], BH, F, lod ? 2 : 3);
  B.add(gRBox(0.36, 0.19, 0.02, 0.008, 1), M4.mul(BH, M4.trs(0.05, 0.50, -0.052, 0, -8 * DEG)), SEATMAT.jHead);
  if (lod) return;
  B.add(gBox(0.60, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.29, -0.0385)), SEATMAT.jBase);            // stitched seam
  B.add(gBox(0.60, 0.005, 0.004), M4.mul(M4.trs(0, 0.39, -0.34, 0, 2 * DEG), M4.trs(0, 0.041, -0.10, 0, Math.PI / 2)), SEATMAT.jBase);
  B.add(gRBox(0.03, 0.05, 0.012, 0.004, 1), M4.mul(BH, M4.trs(0.05, 0.385, -0.06)), SEATMAT.jHead); // flap tab
  // leg rest hanging from the pan front
  B.add(gLoft([SEC(0.0, 0.56, 0.045, 0, 0.015), SEC(0.30, 0.60, 0.05, 0, 0.018)], 3), M4.trs(0, 0.06, -0.64, 0, -14 * DEG), F);
  // teal shoulder belt (c_27313 / 27316 show it lying on the cushion)
  B.add(gBox(0.045, 0.004, 0.34), M4.trs(-0.12, 0.433, -0.30, 0.5), { c: '#2f5f66', r: 0.7 });
  B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.trs(-0.04, 0.436, -0.44), SEATMAT.buckle);
}

// charcoal frame round an ash panel (every ash face in the photos sits in a ~3 cm dark frame, c_27312-27315):
// panel in the plane x = px (thickness t) spanning y0..y1, z0..z1
function ashFrameX(B, px, t, y0, y1, z0, z1) {
  const f = 0.028, T = t + 0.008, m = SEATMAT.jShell;
  for (const z of [z0 + f / 2, z1 - f / 2]) B.add(gRBox(T, y1 - y0, f, 0.006, 1), M4.trs(px, (y0 + y1) / 2, z), m);
  for (const y of [y0 + f / 2, y1 - f / 2]) B.add(gRBox(T, f, z1 - z0, 0.006, 1), M4.trs(px, y, (z0 + z1) / 2), m);
}
// panel in the plane z = pz spanning x0..x1, y0..y1
function ashFrameZ(B, pz, t, x0, x1, y0, y1) {
  const f = 0.028, T = t + 0.008, m = SEATMAT.jShell;
  for (const x of [x0 + f / 2, x1 - f / 2]) B.add(gRBox(f, y1 - y0, T, 0.006, 1), M4.trs(x, (y0 + y1) / 2, pz), m);
  for (const y of [y0 + f / 2, y1 - f / 2]) B.add(gRBox(x1 - x0, f, T, 0.006, 1), M4.trs((x0 + x1) / 2, y, pz), m);
}
// shared bits of the shell: rounded cap rail on a wall top, door leading edge with a finger pull
function capRail(B, w, d, x, y, z) { B.add(gRBox(w + 0.012, 0.03, d + 0.012, 0.012, 2), M4.trs(x, y + 0.012, z), SEATMAT.jRail); }
function doorEdge(B, x, z, h) {
  B.add(gRBox(0.05, h, 0.04, 0.014, 2), M4.trs(x, 0.14 + h / 2, z), SEATMAT.jShell);
  B.add(gRBox(0.046, h - 0.06, 0.006, 0.004, 1), M4.trs(x, 0.14 + h / 2, z + 0.021), SEATMAT.ash);
  B.add(gRBox(0.012, 0.16, 0.02, 0.005, 1), M4.trs(x - 0.02, 0.86, z + 0.025), SEATMAT.jBase);
}

function roomPart(part, opts = {}) {
  const B = new Builder();
  const bed = !!opts.bed, lod = !!opts.lod;
  const { hx, hz, top, wall } = ROOM;
  const shell = SEATMAT.jShell, ash = SEATMAT.ash;
  if (part === 'O') {
    // --- the seat: back against the forward end, facing aft (+z)
    const S = M4.trs(-0.24, 0, -1.27, Math.PI);
    const tmp = new Builder(); roomSeatCore(tmp, bed, lod); B.addBuilt(tmp.build(), S);
    // back shell: charcoal wall, dark padded band above the seat back, cap rail, reading light in the corner
    B.add(gRBox(0.70, wall, 0.07, 0.03, 2), M4.trs(-0.235, wall / 2, -1.31), shell);
    B.add(gRBox(0.64, 0.30, 0.02, 0.012, 1), M4.trs(-0.24, 0.93, -1.268), SEATMAT.jLeather);
    capRail(B, 0.70, 0.07, -0.235, wall, -1.31);
    B.add(gCyl(0.024, 0.024, 0.02, 14), M4.trs(-0.52, 1.03, -1.265, 0, -Math.PI / 2), SEATMAT.jRail);
    B.add(gCyl(0.015, 0.015, 0.004, 12), M4.trs(-0.52, 1.03, -1.254, 0, -Math.PI / 2), SEATMAT.lampGlow);
    // aisle corner: LOW armrest ledge (0.66) holding the retracted pop-up privacy panel (only its ash top edge shows)
    B.add(gRBox(0.50, top, 0.28, 0.02, 1), M4.trs(0.335, top / 2, -1.20), shell);
    B.add(gRBox(0.16, 0.035, 0.28, 0.014, 2), M4.trs(0.17, top + 0.012, -1.20), SEATMAT.jLeather);
    B.add(gRBox(0.34, 0.03, 0.28, 0.012, 2), M4.trs(0.415, top + 0.01, -1.20), SEATMAT.jRail);
    B.add(gBox(0.022, 0.006, 0.26), M4.trs(0.48, top + 0.027, -1.20), ash);
    if (!lod) B.add(gRBox(0.08, 0.05, 0.004, 0.004, 1), M4.trs(0.42, 0.50, -1.0585), SEATMAT.black);   // stowage latch
    // side table block over E's footwell (aisle column): ash top, ash monument end at the aisle with cap + kick
    B.add(gRBox(0.45, 0.035, 0.56, 0.01, 1), M4.trs(0.345, top - 0.018, -0.30), ash);
    B.add(gRBox(0.04, wall, 0.56, 0.012, 1), M4.trs(0.565, wall / 2, -0.30), ash);
    B.add(gRBox(0.045, 0.10, 0.56, 0.01, 1), M4.trs(0.565, 0.05, -0.30), SEATMAT.jShell);
    ashFrameX(B, 0.565, 0.04, 0.10, wall, -0.58, -0.02);
    capRail(B, 0.04, 0.56, 0.565, wall, -0.30);
    B.add(gRBox(0.02, top - 0.02, 0.56, 0.008, 1), M4.trs(0.13, (top - 0.02) / 2, -0.30), shell); // inner face beside O's legs
    B.add(gRBox(0.40, 0.03, 0.56, 0.01, 1), M4.trs(0.345, 0.58, -0.30), SEATMAT.jShellIn);     // footwell ceiling
    // cabinet with swivel mirror + literature pocket at the aft end of the side table
    // (cabinet rises to the monitor top: ash door with swivel mirror inside, c_27305 / 27311 / 27312)
    B.add(gRBox(0.30, 0.52, 0.17, 0.015, 1), M4.trs(0.28, top + 0.26, -0.12), ash);
    capRail(B, 0.30, 0.17, 0.28, top + 0.52, -0.12);
    B.add(gRBox(0.26, 0.46, 0.006, 0.006, 1), M4.trs(0.28, top + 0.26, -0.207), ash);
    ashFrameZ(B, -0.205, 0.004, 0.13, 0.43, top, top + 0.52);
    B.add(gBox(0.004, 0.40, 0.004), M4.trs(0.415, top + 0.26, -0.211), SEATMAT.jShellIn);
    B.add(gRBox(0.10, 0.12, 0.006, 0.004, 1), M4.trs(0.22, top + 0.30, -0.212), SEATMAT.mirror);
    B.add(gRBox(0.04, 0.02, 0.012, 0.004, 1), M4.trs(0.38, top + 0.36, -0.21), SEATMAT.blueAccent);
    // seat controls (knob, slider, presets) in a dark rounded pod on the side table (c_27308)
    if (!lod) {
      B.add(gRBox(0.12, 0.012, 0.20, 0.006, 1), M4.trs(0.22, top + 0.008, -0.46), SEATMAT.jShell);
      B.add(gRBox(0.10, 0.004, 0.18, 0.004, 1), M4.trs(0.22, top + 0.016, -0.46), SEATMAT.black);
      B.add(gCyl(0.022, 0.022, 0.02, 16), M4.trs(0.22, top + 0.024, -0.41), SEATMAT.frame);
      for (let b = 0; b < 3; b++) B.add(gCyl(0.008, 0.008, 0.004, 10), M4.trs(0.20 + b * 0.02, top + 0.02, -0.50), { c: '#8ab4e6', r: 0.4, e: 0.25 });
      B.add(gBox(0.02, 0.012, 0.006), M4.trs(0.52, 0.6, -0.40), SEATMAT.port);
    }
    B.add(gBox(0.42, 0.012, 0.03), M4.trs(0.345, top + 0.004, -0.575), SEATMAT.slate);          // slate accent on the table edge
    // sliding door parked in the monument; its leading edge (ash face, charcoal frame, finger pull) faces aft
    doorEdge(B, 0.56, -0.60, wall - 0.14);
    // O's monitor on the forward face of a panel rising from E's console (outer column)
    B.add(gRBox(0.54, 0.60, 0.05, 0.02, 1), M4.trs(-0.31, top + 0.30, 0.53), shell);
    capRail(B, 0.54, 0.05, -0.31, top + 0.60, 0.53);
    B.add(gRBox(0.56, 0.33, 0.016, 0.01, 1), M4.trs(-0.31, 0.93, 0.50), SEATMAT.bezel);
    B.add(gQuad(0.531, 0.299), M4.trs(-0.31, 0.93, 0.4915, Math.PI), SEATMAT.screen, atlasUV('screen'));
    // rosewood-grain table stowed under the monitor + mood light, ottoman in the footwell
    B.add(gRBox(0.46, 0.035, 0.05, 0.01, 1), M4.trs(-0.31, top - 0.05, 0.50), SEATMAT.rosewood);
    B.add(gBox(0.40, 0.01, 0.02), M4.trs(-0.33, 0.585, 0.49), SEATMAT.moodGlow);
    if (bed) {
      B.add(gRBox(0.42, ROOM.bed, 0.52, 0.02, 1), M4.trs(-0.35, ROOM.bed / 2, 0.26), SEATMAT.jShellIn);
      B.add(gLoft(cushionSecs(0.62, 1.76, 0.05, -0.02, { edge: 0.02, r: 0.03, crown: 0.004 }), 3), M4.trs(-0.26, ROOM.bed + 0.02, -0.40), SEATMAT.mattress);
      B.add(gLoft(cushionSecs(0.56, 1.1, 0.06, -0.03, { edge: 0.03, r: 0.05 }), 3), M4.trs(-0.28, ROOM.bed + 0.07, -0.05), SEATMAT.duvet);
      B.add(gLoft(cushionSecs(0.46, 0.30, 0.12, -0.06, { edge: 0.05, r: 0.05 }), 3), M4.trs(-0.24, ROOM.bed + 0.08, -1.08), SEATMAT.pillow);
    } else {
      B.add(gRBox(0.40, 0.40, 0.40, 0.03, 1), M4.trs(-0.35, 0.20, 0.30), SEATMAT.jShellIn);
      B.add(gLoft(cushionSecs(0.40, 0.40, 0.05, -0.025, { edge: 0.02, r: 0.03 }), 3), M4.trs(-0.35, 0.42, 0.30), SEATMAT.jFabric);
      B.add(gLoft(cushionSecs(0.40, 0.28, 0.1, -0.05, { edge: 0.04, r: 0.045 }), 3), M4.mul(M4.trs(-0.34, 0.575, -1.04, Math.PI), M4.trs(0, 0, 0, 0.25, -76 * DEG)), SEATMAT.pillowBlue);
    }
    // outer side: low console (window) with cap
    B.add(gRBox(0.025, top, 1.39, 0.01, 1), M4.trs(-0.572, top / 2, -0.66), shell);
    capRail(B, 0.025, 1.39, -0.572, top, -0.66);
  } else {
    // --- E: back at the aft end, facing forward (-z), aisle column
    const S = M4.trs(0.20, 0, 1.27);
    const tmp = new Builder(); roomSeatCore(tmp, bed, lod); B.addBuilt(tmp.build(), S);
    B.add(gRBox(0.69, wall, 0.07, 0.03, 2), M4.trs(0.235, wall / 2, 1.31), shell);
    B.add(gRBox(0.62, 0.30, 0.02, 0.012, 1), M4.trs(0.21, 0.93, 1.268), SEATMAT.jLeather);
    capRail(B, 0.69, 0.07, 0.235, wall, 1.31);
    B.add(gCyl(0.024, 0.024, 0.02, 14), M4.trs(-0.07, 1.03, 1.265, 0, Math.PI / 2), SEATMAT.jRail);
    B.add(gCyl(0.015, 0.015, 0.004, 12), M4.trs(-0.07, 1.03, 1.254, 0, Math.PI / 2), SEATMAT.lampGlow);
    // narrow aisle armrest with the pop-up privacy panel retracted inside (ash edge flush in the cap)
    B.add(gRBox(0.09, top, 0.60, 0.02, 1), M4.trs(0.54, top / 2, 0.95), shell);
    B.add(gRBox(0.10, 0.03, 0.62, 0.012, 2), M4.trs(0.54, top + 0.01, 0.95), SEATMAT.jRail);
    B.add(gBox(0.022, 0.006, 0.58), M4.trs(0.555, top + 0.027, 0.95), ash);
    // wide console by the outer column (window / centreline), hollow under its forward half (O's footwell)
    B.add(gRBox(0.45, 0.035, 1.28, 0.01, 1), M4.trs(-0.355, top - 0.018, 0.66), ash);
    B.add(gRBox(0.44, top - 0.035, 0.66, 0.02, 1), M4.trs(-0.355, (top - 0.035) / 2, 0.95), SEATMAT.jShellIn);
    B.add(gRBox(0.02, top - 0.02, 1.28, 0.008, 1), M4.trs(-0.125, (top - 0.02) / 2, 0.66), shell);
    if (!lod) B.add(gRBox(0.02, 0.05, 0.10, 0.004, 1), M4.trs(-0.114, 0.50, 1.0), { c: '#b3262a', r: 0.5 });   // life-vest tab (red, c_27302)
    // cabinet (mirror + pouches, deep-blue interior) just aft of O's monitor panel
    B.add(gRBox(0.34, 0.52, 0.18, 0.015, 1), M4.trs(-0.33, top + 0.26, 0.66), ash);
    capRail(B, 0.34, 0.18, -0.33, top + 0.52, 0.66);
    B.add(gRBox(0.30, 0.46, 0.006, 0.006, 1), M4.trs(-0.33, top + 0.26, 0.752), ash);
    ashFrameZ(B, 0.75, 0.004, -0.50, -0.16, top, top + 0.52);
    B.add(gBox(0.004, 0.40, 0.004), M4.trs(-0.485, top + 0.26, 0.756), SEATMAT.jShellIn);
    B.add(gRBox(0.10, 0.12, 0.006, 0.004, 1), M4.trs(-0.26, top + 0.30, 0.758), SEATMAT.mirror);
    if (!lod) {
      B.add(gRBox(0.12, 0.012, 0.20, 0.006, 1), M4.trs(-0.30, top + 0.008, 1.02), SEATMAT.jShell);
      B.add(gRBox(0.10, 0.004, 0.18, 0.004, 1), M4.trs(-0.30, top + 0.016, 1.02), SEATMAT.black);
      B.add(gCyl(0.022, 0.022, 0.02, 16), M4.trs(-0.30, top + 0.024, 1.07), SEATMAT.frame);
      for (let b = 0; b < 3; b++) B.add(gCyl(0.008, 0.008, 0.004, 10), M4.trs(-0.32 + b * 0.02, top + 0.02, 0.98), { c: '#8ab4e6', r: 0.4, e: 0.25 });
    }
    // E's monitor panel at the aft end of O's side table (aisle column), screen facing aft
    B.add(gRBox(0.64, 0.58, 0.05, 0.02, 1), M4.trs(0.265, top + 0.29, -0.01), shell);
    capRail(B, 0.64, 0.05, 0.265, top + 0.58, -0.01);
    B.add(gRBox(0.56, 0.33, 0.016, 0.01, 1), M4.trs(0.24, 0.93, 0.022), SEATMAT.bezel);
    B.add(gQuad(0.531, 0.299), M4.trs(0.24, 0.93, 0.0305), SEATMAT.screen, atlasUV('screen'));
    B.add(gRBox(0.46, 0.035, 0.05, 0.01, 1), M4.trs(0.30, top - 0.05, 0.02), SEATMAT.rosewood);
    B.add(gBox(0.36, 0.01, 0.02), M4.trs(0.33, 0.585, 0.035), SEATMAT.moodGlow);
    // E's sliding door parked in the monitor monument; leading edge faces aft toward E's entry
    doorEdge(B, 0.56, 0.05, wall - 0.14);
    if (bed) {
      B.add(gRBox(0.40, ROOM.bed, 0.52, 0.02, 1), M4.trs(0.34, ROOM.bed / 2, -0.30), SEATMAT.jShellIn);
      B.add(gLoft(cushionSecs(0.58, 1.80, 0.05, -0.02, { edge: 0.02, r: 0.03, crown: 0.004 }), 3), M4.trs(0.24, ROOM.bed + 0.02, 0.38), SEATMAT.mattress);
      B.add(gLoft(cushionSecs(0.54, 1.1, 0.06, -0.03, { edge: 0.03, r: 0.05 }), 3), M4.trs(0.25, ROOM.bed + 0.07, 0.05), SEATMAT.duvet);
      B.add(gLoft(cushionSecs(0.46, 0.30, 0.12, -0.06, { edge: 0.05, r: 0.05 }), 3), M4.trs(0.20, ROOM.bed + 0.08, 1.08), SEATMAT.pillow);
    } else {
      B.add(gRBox(0.38, 0.40, 0.40, 0.03, 1), M4.trs(0.34, 0.20, -0.30), SEATMAT.jShellIn);
      B.add(gLoft(cushionSecs(0.38, 0.40, 0.05, -0.025, { edge: 0.02, r: 0.03 }), 3), M4.trs(0.34, 0.42, -0.30), SEATMAT.jFabric);
      B.add(gLoft(cushionSecs(0.40, 0.28, 0.1, -0.05, { edge: 0.04, r: 0.045 }), 3), M4.mul(M4.trs(0.10, 0.575, 1.04), M4.trs(0, 0, 0, -0.25, -76 * DEG)), SEATMAT.pillowBlue);
    }
    B.add(gRBox(0.025, top, 1.33, 0.01, 1), M4.trs(-0.572, top / 2, 0.69), shell);
    capRail(B, 0.025, 1.33, -0.572, top, 0.69);
  }
  return B.build();
}
function roomPartFar(part) {
  const B = new Builder();
  const { top, wall } = ROOM;
  if (part === 'O') {
    B.add(gBox(0.70, wall, 0.07), M4.trs(-0.235, wall / 2, -1.31), SEATMAT.jShell);
    B.add(gRBox(0.62, 0.45, 0.6, 0.03, 1), M4.trs(-0.24, 0.225, -0.95), SEATMAT.jFabric);
    B.add(gRBox(0.58, 0.6, 0.12, 0.04, 1), M4.mul(M4.trs(-0.24, 0.43, -1.2, Math.PI), M4.trs(0, 0.3, 0, 0, 17 * DEG)), SEATMAT.jFabric);
    B.add(gBox(0.50, top, 0.28), M4.trs(0.335, top / 2, -1.20), SEATMAT.jShell);
    B.add(gBox(0.04, wall, 0.56), M4.trs(0.565, wall / 2, -0.30), SEATMAT.ash);
    B.add(gBox(0.41, top, 0.56), M4.trs(0.325, top / 2, -0.30), SEATMAT.jShellIn);
    B.add(gBox(0.54, 0.6, 0.05), M4.trs(-0.31, top + 0.30, 0.53), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(-0.31, 0.93, 0.50, Math.PI), SEATMAT.screen, atlasUV('screen'));
  } else {
    B.add(gBox(0.69, wall, 0.07), M4.trs(0.235, wall / 2, 1.31), SEATMAT.jShell);
    B.add(gRBox(0.58, 0.45, 0.6, 0.03, 1), M4.trs(0.2, 0.225, 0.95), SEATMAT.jFabric);
    B.add(gRBox(0.58, 0.6, 0.12, 0.04, 1), M4.mul(M4.trs(0.2, 0.43, 1.2), M4.trs(0, 0.3, 0, 0, 17 * DEG)), SEATMAT.jFabric);
    B.add(gBox(0.45, top, 1.28), M4.trs(-0.355, top / 2, 0.66), SEATMAT.ash);
    B.add(gBox(0.64, 0.58, 0.05), M4.trs(0.265, top + 0.29, -0.01), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(0.24, 0.93, 0.03), SEATMAT.screen, atlasUV('screen'));
  }
  return B.build();
}
// centre dividers of a pair (between E/F rear-facing seats and between the D/G consoles)
function roomDivider() {
  // centreline wall between the E/F (D/G) seats: dark lower band with stowage + red life-vest tab, pale ash upper band,
  // charcoal cap rail; the upper band on the aft half is the retractable privacy divider (c_27313 / c_27314)
  const B = new Builder();
  B.add(gRBox(0.05, 0.66, 2.62, 0.012, 1), M4.trs(0, 0.33, 0.0), SEATMAT.jShell);
  B.add(gRBox(0.036, 0.40, 1.30, 0.012, 1), M4.trs(0, 0.86, -0.66), SEATMAT.ash);
  B.add(gRBox(0.036, 0.36, 1.26, 0.012, 1), M4.trs(0, 0.84, 0.68), SEATMAT.ash);
  for (const z of [-0.66, 0.68]) B.add(gRBox(0.06, 0.035, 1.26, 0.012, 2), M4.trs(0, 0.675, z), SEATMAT.jRail);
  for (const z of [-1.30, -0.02, 0.06, 1.30]) B.add(gRBox(0.05, 0.40, 0.03, 0.008, 1), M4.trs(0, 0.86, z), SEATMAT.jShell);
  B.add(gRBox(0.05, 0.03, 2.6, 0.012, 2), M4.trs(0, 1.07, 0.0), SEATMAT.jRail);
  for (const [z, s] of [[-0.9, 1], [0.9, -1], [-0.9, -1], [0.9, 1]]) {
    B.add(gRBox(0.004, 0.14, 0.34, 0.004, 1), M4.trs(s * 0.026, 0.45, z), SEATMAT.jShellIn);     // stowage door
    B.add(gRBox(0.006, 0.05, 0.02, 0.003, 1), M4.trs(s * 0.028, 0.45, z + 0.22 * s), { c: '#b3262a', r: 0.5 });
  }
  return B.build();
}

// ================= THE Suite (JAMCO) =================
// Suite frame: aft wall at z = 0, front wall (43 in screen) at z = -2.20; outer side (window or partition) at -x.
// w = outer width. Seat sits off-centre: full-length shelf on the outer side, slim wardrobe on the aisle side.
function suiteUnit(opts = {}) {
  const B = new Builder();
  const w = opts.w || 1.24, bed = !!opts.bed, lod = !!opts.lod, center = !!opts.center;
  const hx = w / 2, H = 1.30, L = 2.20;
  const shelfW = center ? 0.14 : 0.19;
  const xo = -hx + 0.03;                      // inner face of the outer side
  const seatX = xo + shelfW + 0.08 + 0.325;   // cushion centre
  const xa = hx - 0.16;                       // inner face of the aisle-side wardrobe wall
  const cap = (cw, cd, x, y, z) => B.add(gRBox(cw + 0.014, 0.035, cd + 0.014, 0.014, 2), M4.trs(x, y + 0.012, z), SEATMAT.fWood);
  // aft wall (behind the seat) + front wall with the 43 in screen; dark wood caps on every wall top (f_17313)
  B.add(gRBox(w, H, 0.06, 0.02, 1), M4.trs(0, H / 2, -0.07), SEATMAT.fShell);
  cap(w, 0.06, 0, H, -0.07);
  B.add(gRBox(w, H, 0.12, 0.02, 1), M4.trs(0, H / 2, -L + 0.06), SEATMAT.fShell);
  cap(w, 0.12, 0, H, -L + 0.06);
  const scx = (xo + xa) / 2;
  B.add(gRBox(1.00, 0.60, 0.02, 0.01, 1), M4.trs(scx - 0.04, 0.95, -L + 0.13), SEATMAT.bezel);
  B.add(gQuad(0.952, 0.535), M4.trs(scx - 0.04, 0.95, -L + 0.141), SEATMAT.screen, atlasUV('screen'));
  // dark-wood pier beside the screen (aisle side) with a vertical light line and reading spot (f_17306 / 17313)
  B.add(gRBox(0.13, H - 0.66, 0.03, 0.01, 1), M4.trs(xa - 0.08, 0.66 + (H - 0.66) / 2, -L + 0.135), SEATMAT.fWood);
  B.add(gBox(0.012, 0.42, 0.006), M4.trs(xa - 0.03, 0.98, -L + 0.152), SEATMAT.fLed);
  B.add(gCyl(0.022, 0.022, 0.02, 14), M4.trs(xa - 0.08, 1.20, -L + 0.155, 0, Math.PI / 2), SEATMAT.fLeather);
  B.add(gCyl(0.013, 0.013, 0.004, 12), M4.trs(xa - 0.08, 1.20, -L + 0.166, 0, Math.PI / 2), SEATMAT.lampGlow);
  // table stowed under the screen on its rails, small cabinet beside the ottoman (aisle side)
  B.add(gRBox(0.78, 0.04, 0.10, 0.012, 1), M4.trs(scx - 0.06, 0.62, -L + 0.19), SEATMAT.fInner);
  B.add(gRBox(0.74, 0.008, 0.08, 0.004, 1), M4.trs(scx - 0.06, 0.643, -L + 0.19), SEATMAT.fShelf);
  B.add(gRBox(0.16, 0.56, 0.36, 0.015, 1), M4.trs(xa - 0.08, 0.28, -L + 0.30), SEATMAT.fInner);
  B.add(gRBox(0.17, 0.02, 0.37, 0.008, 1), M4.trs(xa - 0.08, 0.565, -L + 0.30), SEATMAT.fShelf);
  // ottoman (padded, same tweed as the seat) with belt
  const ow = xa - xo - 0.19;
  const ox = xo + ow / 2 + 0.005;
  B.add(gRBox(ow, 0.36, 0.52, 0.02, 1), M4.trs(ox, 0.18, -L + 0.39), SEATMAT.fInner);
  B.add(gLoft(cushionSecs(ow - 0.01, 0.52, 0.08, -0.04, { edge: 0.025, r: 0.025 }), 3), M4.trs(ox, 0.40, -L + 0.39), SEATMAT.fFabric);
  if (!lod) for (const s of [-1, 1]) B.add(gBox(0.04, 0.004, 0.2), M4.trs(ox + 0.12 * s, 0.443, -L + 0.42), SEATMAT.strap);
  // outer side: low skirt (window) or full-height partition half (centre), plus the long console
  if (center) B.add(gRBox(0.03, H, L - 0.14, 0.01, 1), M4.trs(-hx + 0.015, H / 2, -L / 2), SEATMAT.fDoor);
  else B.add(gRBox(0.03, 0.70, L - 0.14, 0.01, 1), M4.trs(-hx + 0.015, 0.35, -L / 2), SEATMAT.fShell);
  B.add(gRBox(shelfW, 0.64, L - 0.30, 0.02, 1), M4.trs(xo + shelfW / 2, 0.32, -L / 2 - 0.04), SEATMAT.fInner);
  B.add(gRBox(shelfW + 0.01, 0.025, L - 0.30, 0.008, 1), M4.trs(xo + shelfW / 2, 0.652, -L / 2 - 0.04), SEATMAT.fShell);
  // recessed dark-wood tray in the console top, forward of the controls
  B.add(gRBox(shelfW - 0.05, 0.006, 0.95, 0.004, 1), M4.trs(xo + shelfW / 2, 0.666, -1.25), SEATMAT.fShelf);
  if (!lod) {
    // keypad + small touch remote in the console beside the seat (f_17300 / 17302 / 17313)
    B.add(gRBox(0.07, 0.006, 0.12, 0.004, 1), M4.trs(xo + shelfW / 2, 0.667, -0.58), SEATMAT.black);
    for (let r = 0; r < 3; r++) for (let c = 0; c < 2; c++) B.add(gCyl(0.007, 0.007, 0.003, 8), M4.trs(xo + shelfW / 2 - 0.015 + c * 0.03, 0.671, -0.62 + r * 0.03), { c: '#9fb8d8', r: 0.4, e: 0.2 });
    B.add(gRBox(0.075, 0.008, 0.13, 0.006, 1), M4.trs(xo + shelfW / 2, 0.667, -0.80), SEATMAT.black);
    B.add(gQuad(0.055, 0.10), M4.mul(M4.trs(xo + shelfW / 2, 0.672, -0.80), M4.trs(0, 0, 0, 0, -Math.PI / 2)), { c: '#3a6fb8', r: 0.2, e: 0.35 });
    B.add(gRBox(0.02, 0.06, 0.12, 0.004, 1), M4.trs(xo + shelfW + 0.001, 0.58, -1.05), SEATMAT.black); // outlets pocket
    // air grille low on the console face (f_17302)
    B.add(gBox(0.004, 0.10, 0.70), M4.trs(xo + shelfW + 0.001, 0.14, -1.35), { c: '#2a2724', r: 0.8, l: LAYER.grille });
  }
  // aisle side: thick wardrobe wall beside the seat with recessed panel doors, coat hook, literature pocket
  B.add(gRBox(0.16, H, 0.86, 0.02, 1), M4.trs(hx - 0.08, H / 2, -0.53), SEATMAT.fShell);
  cap(0.16, 0.86, hx - 0.08, H, -0.53);
  for (const [zc, len] of [[-0.33, 0.36], [-0.73, 0.36]]) {
    B.add(gRBox(0.008, H - 0.36, len, 0.008, 1), M4.trs(xa - 0.002, 0.16 + (H - 0.36) / 2, zc), SEATMAT.fDoor);
    B.add(gRBox(0.006, H - 0.46, len - 0.08, 0.006, 1), M4.trs(xa - 0.006, 0.16 + (H - 0.36) / 2, zc), SEATMAT.fInner);
  }
  B.add(gRBox(0.012, 0.16, 0.02, 0.006, 1), M4.trs(xa - 0.012, 0.86, -0.53), SEATMAT.frame);
  if (!lod) {
    B.add(gRBox(0.02, 0.018, 0.10, 0.006, 1), M4.trs(xa - 0.02, 1.16, -0.25), SEATMAT.frame);                  // coat hook rail
    B.add(gRBox(0.05, 0.10, 0.20, 0.008, 1), M4.trs(xa - 0.03, 0.66, -0.20), SEATMAT.fInner);                   // lit literature niche
    B.add(gBox(0.004, 0.06, 0.16), M4.trs(xa - 0.056, 0.67, -0.20), SEATMAT.fWarm);
  }
  B.add(gRBox(0.13, H, 0.26, 0.02, 1), M4.trs(hx - 0.065, H / 2, -L + 0.25), SEATMAT.fShell);
  cap(0.13, 0.26, hx - 0.065, H, -L + 0.25);
  // aisle-facing exterior: vertical flutes + LED line at the floor (f_17300 / 17301)
  if (!lod) {
    for (const [z0, z1] of [[-0.96, -0.10], [-L + 0.12, -L + 0.38]]) {
      for (let z = z0 + 0.02; z < z1 - 0.01; z += 0.028) B.add(gBox(0.008, H - 0.22, 0.014), M4.trs(hx + 0.004, 0.14 + (H - 0.22) / 2, z), SEATMAT.fFlute);
      B.add(gBox(0.006, 0.008, z1 - z0 - 0.02), M4.trs(hx + 0.004, 0.06, (z0 + z1) / 2), SEATMAT.fLed);
    }
  }
  // sliding doors (open, parked in the wardrobe wall and the front pier), fluted like the exterior
  for (const [zc, len] of [[-0.53, 0.5], [-L + 0.26, 0.24]]) B.add(gRBox(0.03, H - 0.12, len, 0.01, 1), M4.trs(hx - 0.012, (H - 0.12) / 2 + 0.06, zc), SEATMAT.fFlute);
  if (!lod) for (const zz of [-0.80, -L + 0.39]) B.add(gRBox(0.02, 0.18, 0.025, 0.008, 1), M4.trs(hx + 0.005, 0.95, zz), SEATMAT.frame);
  // the seat: upholstered base, thin cushion, flat back leaning on the aft wall, slate headrest flap (f_17302 / 17309)
  const S = M4.trs(seatX, 0, -0.14);
  const F = SEATMAT.fFabric;
  B.add(gRBox(0.66, 0.34, 0.62, 0.02, 1), M4.mul(S, M4.trs(0, 0.17, -0.36)), F);
  // tall padded armrest post at the aisle side of the seat
  B.add(gRBox(0.08, 0.66, 0.12, 0.035, 2), M4.mul(S, M4.trs(0.37, 0.33, -0.66)), SEATMAT.fLeather);
  B.add(gRBox(0.08, 0.06, 0.60, 0.03, 2), M4.mul(S, M4.trs(0.37, 0.62, -0.36)), SEATMAT.fLeather);
  // reading spot on the aft wall corner
  B.add(gCyl(0.024, 0.024, 0.02, 14), M4.trs(xa - 0.06, 1.15, -0.10, 0, -Math.PI / 2), SEATMAT.fLeather);
  B.add(gCyl(0.015, 0.015, 0.004, 12), M4.trs(xa - 0.06, 1.15, -0.089, 0, -Math.PI / 2), SEATMAT.lampGlow);
  if (bed) {
    B.add(gLoft(cushionSecs(0.66, 1.96, 0.06, -0.03, { edge: 0.03, r: 0.035, crown: 0.004 }), 3), M4.trs(seatX - 0.01, 0.44, -1.08), { c: '#f0efea', r: 0.9, l: LAYER.fabric });
    B.add(gRBox(ow, 0.44, 0.9, 0.03, 1), M4.trs(ox, 0.22, -1.40), SEATMAT.fInner);
    B.add(gLoft(cushionSecs(0.6, 1.2, 0.06, -0.03, { edge: 0.03, r: 0.05 }), 3), M4.trs(seatX - 0.01, 0.50, -1.25), { c: '#6f7c93', r: 0.95, l: LAYER.fabric });
    B.add(gLoft(cushionSecs(0.5, 0.32, 0.13, -0.065, { edge: 0.05, r: 0.05 }), 3), M4.trs(seatX, 0.52, -0.32), SEATMAT.pillow);
  } else {
    B.add(gLoft(cushionSecs(0.66, 0.62, 0.075, -0.035, { edge: 0.022, r: 0.02, crown: 0.004 }), lod ? 3 : 4), M4.mul(S, M4.trs(0, 0.375, -0.36, 0, 2 * DEG)), F);
    const BH = M4.mul(S, M4.trs(0, 0.42, -0.10, 0, 11 * DEG));
    loftAt(B, [SEC(0.0, 0.64, 0.06, 0, 0.02), SEC(0.025, 0.66, 0.08, 0, 0.028), SEC(0.64, 0.66, 0.08, 0, 0.028), SEC(0.665, 0.64, 0.06, 0.002, 0.02)], BH, F, lod ? 2 : 3);
    B.add(gRBox(0.40, 0.16, 0.02, 0.008, 1), M4.mul(BH, M4.trs(0.04, 0.55, -0.052, 0, -6 * DEG)), SEATMAT.fFlap);
    if (!lod) {
      B.add(gBox(0.62, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.30, -0.041)), SEATMAT.fInner);
      B.add(gRBox(0.03, 0.05, 0.012, 0.004, 1), M4.mul(BH, M4.trs(0.04, 0.455, -0.062)), SEATMAT.fLeather);
      B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.mul(S, M4.trs(0, 0.418, -0.40)), SEATMAT.buckle);
    }
    B.add(gLoft(cushionSecs(0.44, 0.1, 0.30, -0.15, { edge: 0.04, r: 0.045 }), 3), M4.mul(BH, M4.trs(-0.08, 0.20, -0.10, 0.25, 6 * DEG)), SEATMAT.fCushionBlue);
    B.add(gLoft([SEC(0.0, 0.58, 0.05, 0, 0.02), SEC(0.30, 0.60, 0.055, 0, 0.022)], 3), M4.mul(S, M4.trs(0, 0.06, -0.70, 0, -14 * DEG)), F);
  }
  return B.build();
}
function suiteFar(opts = {}) {
  const B = new Builder();
  const w = opts.w || 1.24, hx = w / 2, H = 1.30, L = 2.20;
  B.add(gBox(w, H, 0.06), M4.trs(0, H / 2, -0.07), SEATMAT.fShell);
  B.add(gBox(w, H, 0.12), M4.trs(0, H / 2, -L + 0.06), SEATMAT.fShell);
  B.add(gBox(0.16, H, 0.86), M4.trs(hx - 0.08, H / 2, -0.53), SEATMAT.fShell);
  B.add(gBox(0.03, opts.center ? H : 0.7, L), M4.trs(-hx + 0.015, (opts.center ? H : 0.7) / 2, -L / 2), SEATMAT.fShell);
  B.add(gRBox(0.66, 0.5, 0.7, 0.04, 1), M4.trs(-hx + 0.6, 0.25, -0.45), SEATMAT.fFabric);
  B.add(gQuad(0.952, 0.535), M4.trs(-0.05, 0.93, -L + 0.151), SEATMAT.screen, atlasUV('screen'));
  return B.build();
}

function mirrorGeo(geo) {
  const g = { p: Array.from(geo.pos), n: Array.from(geo.nrm), u: Array.from(geo.uv), i: [] };
  for (let k = 0; k < g.p.length; k += 3) { g.p[k] = -g.p[k]; g.n[k] = -g.n[k]; }
  const rects = Object.values(ATL.rects);
  for (let k = 0; k < g.u.length / 2; k++) {
    if (geo.mat[k * 4 + 2] < 13 || geo.mat[k * 4 + 2] > 15) continue;
    const u = g.u[k * 2], v = g.u[k * 2 + 1];
    const r = rects.find((q) => u >= q[0] - 1e-5 && u <= q[2] + 1e-5 && v >= q[1] - 1e-5 && v <= q[3] + 1e-5);
    if (r) g.u[k * 2] = r[0] + r[2] - u;
  }
  for (let t = 0; t < geo.idx.length; t += 3) g.i.push(geo.idx[t], geo.idx[t + 2], geo.idx[t + 1]);
  const b = geo.bounds;
  return { pos: new Float32Array(g.p), nrm: new Float32Array(g.n), uv: new Float32Array(g.u), col: geo.col, mat: geo.mat, idx: g.i, bounds: [[-b[1][0], b[0][1], b[0][2]], [-b[0][0], b[1][1], b[1][2]]] };
}

// ---------------- per-kind helpers used by the app (pick boxes, eyes, beds) ----------------
function unitXF(s) { return s.kind === 'room' ? M4.trs(s.ux, 0, s.uz) : M4.trs(s.x, 0, s.z); }
function localToWorld(s, p) { const q = [s.mir ? -p[0] : p[0], p[1], p[2]]; return M4.point(unitXF(s), q); }
function seatPickBox(s) {
  if (s.kind === 'econ') return [s.x - 0.24, s.x + 0.24, 0, 1.22, s.z - 0.5, s.z + 0.09];
  if (s.kind === 'py') return [s.x - 0.28, s.x + 0.28, 0, 1.32, s.z - 0.56, s.z + 0.12];
  let a, b;
  if (s.kind === 'room') { a = s.odd ? [-0.585, 0, -1.345] : [-0.12, 0, -0.55]; b = s.odd ? [0.10, 1.12, 0.55] : [0.585, 1.12, 1.345]; }
  else { const hx = (s.pos === 'center' ? 1.10 : 1.24) / 2; a = [-hx, 0, -2.2]; b = [hx, 1.3, 0]; }
  const p = localToWorld(s, a), q = localToWorld(s, b);
  return [Math.min(p[0], q[0]), Math.max(p[0], q[0]), 0, b[1], Math.min(p[2], q[2]), Math.max(p[2], q[2])];
}
function seatEye(s, bed) {
  if (s.kind === 'econ') return { pos: [s.x, 1.15, s.z - 0.2], yaw: 0, pitch: -0.1 };
  if (s.kind === 'py') return { pos: [s.x, 1.18, s.z - 0.24], yaw: 0, pitch: -0.1 };
  if (s.kind === 'room') {
    const p = s.odd ? (bed ? [-0.24, 0.78, -1.0] : [-0.24, 1.13, -1.0]) : (bed ? [0.20, 0.78, 1.0] : [0.20, 1.13, 1.0]);
    return { pos: localToWorld(s, p), yaw: s.odd ? Math.PI : 0, pitch: bed ? -0.1 : -0.12 };
  }
  const hx = (s.pos === 'center' ? 1.10 : 1.24) / 2;
  const seatX = -hx + 0.03 + (s.pos === 'center' ? 0.14 : 0.19) + 0.08 + 0.325;
  const p = bed ? [seatX, 0.80, -0.5] : [seatX, 1.17, -0.42];
  return { pos: localToWorld(s, p), yaw: 0, pitch: bed ? -0.12 : -0.1 };
}
function seatBedCenter(s) {
  if (s.kind === 'room') return localToWorld(s, s.odd ? [-0.26, 0.45, -0.4] : [0.24, 0.45, 0.38]);
  if (s.kind === 'suite') return localToWorld(s, [-0.1, 0.45, -1.1]);
  return [s.x, 0.45, s.z - 0.5];
}
const seatHasBed = (s) => s.kind === 'room' || s.kind === 'suite';

function buildSeats(gl, layout) {
  const meshes = {};
  const inst = {};
  const push = (key, m, tint, ref) => { (inst[key] = inst[key] || { mats: [], tints: [], refs: [] }); inst[key].mats.push(m); inst[key].tints.push(tint); inst[key].refs.push(ref); };
  const rnd = mulberry32(777);
  const screenVar = () => [1, 1, 1, Math.floor(rnd() * 4)];
  const byRow = {};
  for (const s of layout.seats) (byRow[s.row] = byRow[s.row] || []).push(s);
  const pairsDone = new Set();
  for (const ss of Object.values(byRow)) {
    const k0 = ss[0].kind;
    if (k0 === 'suite') {
      for (const s of ss) {
        const key = 'suite' + (s.pos === 'center' ? 'C' : 'W') + (s.mir ? 'M' : '');
        s.meshKey = key;
        push(key, M4.trs(s.x, 0, s.z), screenVar(), s);
      }
      continue;
    }
    if (k0 === 'room') {
      for (const s of ss) {
        const key = 'room' + (s.odd ? 'O' : 'E') + (s.mir ? 'M' : '');
        s.meshKey = key;
        push(key, M4.trs(s.ux, 0, s.uz), screenVar(), s);
        const pk = s.uz.toFixed(3);
        if (!pairsDone.has(pk)) { pairsDone.add(pk); push('roomDiv', M4.trs(0, 0, s.uz), [1, 1, 1, 0], null); }
      }
      continue;
    }
    const blocks = [ss.filter((s) => s.x < -1.1), ss.filter((s) => Math.abs(s.x) <= 1.1), ss.filter((s) => s.x > 1.1)];
    for (const b of blocks) {
      if (!b.length) continue;
      const cx = b.reduce((a, s) => a + s.x, 0) / b.length;
      const n = b.length;
      let key = (k0 === 'py' ? 'py' : 'y') + n;
      if (b[0].exitRow) key += 'x';                        // exit row: screen in the armrest (none in the back)
      if (b.some((s) => s.row === 42)) key += 'l';          // last row: no footrest behind
      b.forEach((s) => { s.meshKey = key; });
      push(key, M4.trs(cx, 0, b[0].z), screenVar(), b);
    }
  }
  const geos = {
    roomO: (l) => (l ? roomPartFar('O') : roomPart('O')), roomOM: (l) => mirrorGeo(l ? roomPartFar('O') : roomPart('O')),
    roomE: (l) => (l ? roomPartFar('E') : roomPart('E')), roomEM: (l) => mirrorGeo(l ? roomPartFar('E') : roomPart('E')),
    roomDiv: () => roomDivider(),
    suiteW: (l) => (l ? suiteFar() : suiteUnit()), suiteWM: (l) => mirrorGeo(l ? suiteFar() : suiteUnit()),
    suiteC: (l) => (l ? suiteFar({ w: 1.10, center: true }) : suiteUnit({ w: 1.10, center: true })), suiteCM: (l) => mirrorGeo(l ? suiteFar({ w: 1.10, center: true }) : suiteUnit({ w: 1.10, center: true })),
  };
  const econGeo = (key, lod) => {
    const kind = key.startsWith('py') ? 'py' : 'y';
    const n = +key.replace(/[^0-9]/g, '');
    const opts = { noScreen: key.includes('x'), footrest: !key.includes('l') };
    if (kind === 'py') return lod ? pyUnitFar(n) : pyUnit(n, false, opts);
    return lod ? econUnitFar(n) : econUnit(n, false, opts);
  };
  const groups = {};
  for (const [key, v] of Object.entries(inst)) {
    const hasLod = key !== 'roomDiv';
    const n = v.mats.length;
    const master = new Float32Array(n * 20);
    v.mats.forEach((m, i) => { master.set(m, i * 20); master.set(v.tints[i], i * 20 + 16); });
    const gen = geos[key] || ((l) => econGeo(key, l));
    const hiGeo = gen(false);
    const hi = gl.mesh(hiGeo, { name: key, layer: 'seats', instances: v.mats, tints: v.tints });
    const lo = hasLod ? gl.mesh(gen(true), { name: key + 'Lo', layer: 'seats', instances: [], castShadow: false }) : null;
    groups[key] = { key, hi, lo, master, n, refs: v.refs, dirty: true, geo: hiGeo, mats: v.mats, nearK: /^(y|py)/.test(key) ? 0.66 : 1.25 };
    meshes[key] = hi;
    if (lo) meshes[key + 'Lo'] = lo;
  }
  // bed variants (shown for the one seat that is lying flat)
  const bedGeo = {
    roomO: () => roomPart('O', { bed: true }), roomOM: () => mirrorGeo(roomPart('O', { bed: true })),
    roomE: () => roomPart('E', { bed: true }), roomEM: () => mirrorGeo(roomPart('E', { bed: true })),
    suiteW: () => suiteUnit({ bed: true }), suiteWM: () => mirrorGeo(suiteUnit({ bed: true })),
    suiteC: () => suiteUnit({ w: 1.10, center: true, bed: true }), suiteCM: () => mirrorGeo(suiteUnit({ w: 1.10, center: true, bed: true })),
  };
  for (const [k, f] of Object.entries(bedGeo)) meshes['bed_' + k] = gl.mesh(f(), { name: 'bed_' + k, layer: 'seats', instances: [] });
  // seat-number plaques on the aisle faces of the suites / rooms (world space, not instanced)
  const T = new Builder();
  for (const s of layout.seats) {
    if (!ATL.rects['tag' + s.id]) continue;
    let p, face;
    if (s.kind === 'room') { p = localToWorld(s, s.odd ? [0.588, 0.56, -1.20] : [0.588, 0.56, 0.95]); face = s.mir ? -1 : 1; }
    else { const hx = (s.pos === 'center' ? 1.10 : 1.24) / 2; p = localToWorld(s, [hx + 0.003, 1.12, -0.35]); face = s.mir ? -1 : 1; }
    T.add(gQuad(0.07, 0.036), M4.trs(p[0], p[1], p[2], face > 0 ? Math.PI / 2 : -Math.PI / 2), MAT.decal, atlasUV('tag' + s.id));
  }
  meshes.seatTags = gl.mesh(T.build(), { name: 'seatTags', layer: 'seats', castShadow: false });
  return { meshes, groups };
}

// Distance LOD + coarse view culling for seat instances
function updateSeatLOD(G, groups, cam, opts = {}) {
  const near = opts.near ?? 9.5;
  const [px, py, pz] = cam.pos;
  const fwd = cam.fwd;
  const cosCull = opts.cosCull ?? -1;
  for (const g of Object.values(groups)) {
    const hiBuf = g.hiBuf || (g.hiBuf = new Float32Array(g.n * 20));
    const loBuf = g.loBuf || (g.loBuf = new Float32Array(g.n * 20));
    let nh = 0, nl = 0;
    for (let i = 0; i < g.n; i++) {
      const o = i * 20;
      const x = g.master[o + 12] - px, y = g.master[o + 13] + 0.6 - py, z = g.master[o + 14] - pz;
      if (g.master[o + 13] < -10) continue;
      const d = Math.hypot(x, y, z);
      if (d > 3.0 && fwd && (x * fwd[0] + y * fwd[1] + z * fwd[2]) / d < cosCull) continue;
      if (!g.lo || (d < near * g.nearK && !opts.allLo)) { hiBuf.set(g.master.subarray(o, o + 20), nh * 20); nh++; }
      else { loBuf.set(g.master.subarray(o, o + 20), nl * 20); nl++; }
    }
    G.setInstancesRaw(g.hi, hiBuf, nh);
    if (g.lo) G.setInstancesRaw(g.lo, loBuf, nl);
    g.dirty = false;
  }
}
function groupSetTint(g, i, t) { g.master.set(t, i * 20 + 16); g.dirty = true; }
function groupSetMatrix(g, i, m) { g.master.set(m, i * 20); g.dirty = true; }

// Studio catalogue of units for design review
const UNITS = {
  econ3: () => econUnit(3),
  econ4: () => econUnit(4),
  py2: () => pyUnit(2),
  py4: () => pyUnit(4),
  roomO: () => roomPart('O'),
  roomE: () => roomPart('E'),
  roomPair: () => { const B = new Builder(); B.addBuilt(roomPart('O')); B.addBuilt(roomPart('E')); return B.build(); },
  roomBedO: () => { const B = new Builder(); B.addBuilt(roomPart('O', { bed: true })); B.addBuilt(roomPart('E')); return B.build(); },
  roomCentre: () => { const B = new Builder(); B.addBuilt(mirrorGeo(roomPart('O')), M4.trs(-0.585, 0, 0)); B.addBuilt(mirrorGeo(roomPart('E')), M4.trs(-0.585, 0, 0)); B.addBuilt(roomPart('O'), M4.trs(0.585, 0, 0)); B.addBuilt(roomPart('E'), M4.trs(0.585, 0, 0)); B.addBuilt(roomDivider()); return B.build(); },
  suiteW: () => suiteUnit(),
  suiteBed: () => suiteUnit({ bed: true }),
  suiteC: () => { const B = new Builder(); B.addBuilt(mirrorGeo(suiteUnit({ w: 1.10, center: true })), M4.trs(-0.56, 0, 0)); B.addBuilt(suiteUnit({ w: 1.10, center: true }), M4.trs(0.56, 0, 0)); return B.build(); },
};
