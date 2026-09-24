// ------------------------------------------------------------------
// Seat models for the ANA 777-300ER (see REFERENCE777.md)
// Seat-local frame: x across, y up, z = 0 at the seat-back reference, passenger faces -z
// ------------------------------------------------------------------
const SEATMAT = {
  // Economy (Recaro): royal-blue tick jacquard (plus a diamond variant ~1 seat in 3, y_47306 / 47300), slate leatherette
  // headrest covers, off-white shells + arms, cerulean belts, navy pillows -- all read from ANA's official Y photos
  // (ref/ana/y_4730x; REFERENCE777.md). Fabric mean #2a3a70 (ground ~#1f3068, ticks ~#bccdf5 in y_47306); photoBase()
  // compensates the wide-range swatch encoding
  // QA r2: the old #2a3a70 rendered ~3x too dark and too saturated (render #0f163e vs photo #415390 y_47301, #495d99
  // y_47306). The pale ticks carry most of the red, and the ACES toe crushes the dark ground's red, so the seat reads
  // more saturated than its albedo: #5468a8 is the base whose tick swatch averages #415596 through the renderer's tone
  // curve at studio exposure (4x4 texel average, test/sim of 04_shaders toLin + aces) ~ photo #415390 [D]
  yFabric: { c: photoBase('#5468a8', 'y_tick'), r: 0.9, l: LAYER.yJacq },
  yFabricB: { c: photoBase('#5468a8', 'y_diamond'), r: 0.9, l: LAYER.yDiamond },
  yFabricC: { c: '#5064a4', r: 0.9, l: LAYER.yMosaic },   // third variant: dash mosaic (y_47302 left, y_47306 right)
  // headrest cushion: sparse white confetti on cobalt, a different fabric from the back (y_47306 / 47302 wings,
  // REFERENCE777.md) - shares the luminance-only confetti swatch with the PY wings
  // (same tone-curve match: wing photo mean #334276 in y_47306 -> base #4a5a98 averages #324384) [D]
  yHead: { c: photoBase('#4a5a98', 'py_confetti'), r: 0.9, l: LAYER.pyConfetti },
  // slate-grey leatherette cover, lighter + greyer than the fabric (y_47302 #474960-#4d526f, y_47306 #445072,
  // y_47301 #434765; QA r2 was #3e4661 -> rendered as black slabs)
  yCover: { c: '#50566c', r: 0.45, l: LAYER.leather },
  yShell: { c: '#d9dbde', r: 0.42, l: LAYER.plastic },
  yShellDark: { c: '#c2c5c9', r: 0.5, l: LAYER.plastic },
  yTray: { c: '#cfd2d6', r: 0.4, l: LAYER.plastic },
  yBelt: { c: '#3a64a6', r: 0.7, l: LAYER.fabric },        // y_47303 (58,102,173), G/B 0.59
  yPillow: { c: '#2e3860', r: 0.9, l: LAYER.fabric },      // y_47300 (44,53,88)
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
  // Premium Economy (ZIM): charcoal/white dash weave (reads light grey), navy leatherette headrest flap,
  // mid-grey shells + consoles with a silver trim line (ref/ana/py_3730x, ref/web/py san_*). QA r1: white-balanced on the
  // cabin wall both photo sets give near-neutral greys: back fabric (97,97,105) py_37305, wing (94,96,111), shell ~#525352
  // py_37303 -> the blue cast of the old values removed
  // QA r2: darker ground under a high-passed dash swatch at gain 1 so the light dashes carry the brightness (py_37301 back
  // p10/p90 100/201); flap / back luminance 0.43-0.56 (py_37305 41/97, py_37302 69/124): QA r2 render gave 0.61 and an
  // over-saturated navy (ACES toe) with #373f63 -> greyer navy;
  // wings: white flakes (~220) on charcoal-navy (55-65, py_37305). Tone-curve matched as for Y: back #6e7076 averages
  // #5c5f66 (py_37305 back #5f5f68), wing #6e7182 averages #585c6e (py_37305 wing #5d5f6e) [D]
  pyFabric: { c: photoBase('#6e7076', 'py_back'), r: 0.9, l: LAYER.pyFleck },
  pyCover: { c: '#343850', r: 0.5, l: LAYER.leather },   // photo flap #232740, R/B 0.55 (py_37305): less saturated
  pyWing: { c: photoBase('#6e7182', 'py_confetti'), r: 0.9, l: LAYER.pyConfetti },
  pyShell: { c: '#5e6062', r: 0.42, l: LAYER.plastic },
  pyArm: { c: '#595b5e', r: 0.45, l: LAYER.plastic },
  pyArmPad: { c: '#6f7173', r: 0.5, l: LAYER.leather },
  pyBin: { c: '#b8bcc0', r: 0.3, m: 0.85, l: LAYER.brushed },
  pyBay: { c: '#4a4c50', r: 0.6, l: LAYER.plastic },
  pyTrim: { c: '#b9bec4', r: 0.28, m: 0.8, l: LAYER.brushed },
  // THE Room (Safran Fusio custom). Colours sampled from ANA's official seat photos (ref/ana/c_273xx, see REFERENCE777.md):
  // pale grey-beige ash with fine straight grain, charcoal shells with flat charcoal tops (QA r1: shell / console
  // #45484d omaat_room_16, #45454c c_27312; tops #545557 omaat_room_10), silver line only on armrest ledges + door-leaf
  // edges (c_27313 / 27300), charcoal tweed seat, slate Ultraleather headrest flap (#767a7e omaat_room_13), navy pillow
  ash: { c: '#c9c2b3', r: 0.48, l: LAYER.ashGrain },
  ashDark: { c: '#5d6166', r: 0.34, m: 0.35, l: LAYER.brushed },
  rosewood: { c: '#4b403a', r: 0.36, l: LAYER.wood },
  jShell: { c: '#45484d', r: 0.46, l: LAYER.plastic },
  jShellIn: { c: '#3a3d42', r: 0.5, l: LAYER.plastic },
  jCap: { c: '#505358', r: 0.45, l: LAYER.plastic },
  jRail: { c: '#b9bec4', r: 0.26, m: 0.7, l: LAYER.brushed },
  jVoid: { c: '#1d1617', r: 0.9 },
  jBase: { c: '#2a2b2f', r: 0.6 },
  jFabric: { c: '#5c5b61', r: 0.92, l: LAYER.tweed },   // uniform mid grey #5d5d62-#636164 (c_27315, omaat_room_13)
  jLeather: { c: '#4b4d53', r: 0.5, l: LAYER.leather },
  jHead: { c: '#6e7378', r: 0.45, l: LAYER.leather },
  blueAccent: { c: '#233f7a', r: 0.5 },
  slate: { c: '#3f4246', r: 0.55, l: LAYER.marble },
  mattress: { c: '#f0efea', r: 0.9, l: LAYER.fabric },
  duvet: { c: '#34558f', r: 0.95, l: LAYER.fabric },
  pillow: { c: '#eeede8', r: 0.9, l: LAYER.fabric },
  pillowBlue: { c: '#383e6c', r: 0.85, l: LAYER.yagasuri },   // yagasuri jacquard #32355d / #3e457b (c_27302 / 27303)
  lampGlow: { c: '#ffe2b0', r: 0.4, e: 0.35 },
  moodGlow: { c: '#ffd9a0', r: 0.5, e: 0.25 },
  hole: { c: '#0b0d10', r: 1.0 },
  mirror: { c: '#aeb6bf', r: 0.08, m: 0.9 },
  // THE Suite (JAMCO). Colours from ANA's real suite photos f_17313 / f_17314 and OMAAT / TPA in-flight photos
  // (ref/web/suite): warm taupe-grey shells with a thick LIGHTER taupe bullnose cap on every wall top (omaat_f58/f60
  // #9b8d70-#aaa786, tpa_0220 #888482), near-black straight-grain wood (omaat_f60 #322d1a, f2 #2c2217), warm mid-grey
  // tweed seat + ottoman, lavender pillow (omaat_f2/f5/f57 #796fa2 in shade); renders f_17300-17309 give the fluted
  // exterior, floor LED line and window console
  fShell: { c: '#69655f', r: 0.45, l: LAYER.plastic },
  fFlute: { c: '#5a5347', r: 0.5, l: LAYER.plastic },        // rounded door ribs (omaat_f60)
  fFluteGap: { c: '#34302a', r: 0.7 },
  // QA r2: veneer under neutral window light #403430 (up_Privacy-Wall crop, SD 10; the console there reads #74706a ~ fConsole)
  fWood: { c: '#3e332d', r: 0.38, l: LAYER.fWood },
  fDoor: { c: '#736c65', r: 0.45, l: LAYER.plastic },
  fInner: { c: '#5d5752', r: 0.5, l: LAYER.plastic },
  fFabric: { c: '#5e5857', r: 0.92, l: LAYER.fTweed },
  fLeather: { c: '#4f4b49', r: 0.48, l: LAYER.leather },
  fFlap: { c: '#66706f', r: 0.45, l: LAYER.leather },       // cool slate-teal flap, omaat_f2 / f13
  fCap: { c: '#8a8272', r: 0.42, l: LAYER.plastic },
  fConsole: { c: '#7a736c', r: 0.45, l: LAYER.plastic },
  fCushionBlue: { c: '#7c72b6', r: 0.85, l: LAYER.fabric },
  fShelf: { c: '#3a302a', r: 0.35, l: LAYER.fWood },
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

// ================= PREMIUM ECONOMY (ZIM, 19 in, 15.6 in screen, leg rest + bicycle footrest) =================
const PY = { back: 14 * DEG, hinge: [0.48, -0.09], sp: 0.5715 };
function pySeat(B, x0, lod, opts = {}) {
  const [hy, hz] = PY.hinge;
  const F = SEATMAT.pyFabric;
  const BH = M4.trs(x0, hy, hz, 0, PY.back);
  B.add(gLoft(cushionSecs(0.48, 0.50, 0.115, -0.06, { edge: 0.04, r: 0.035, crown: 0.012 }), lod ? 3 : 4), M4.trs(x0, 0.425, -0.30, 0, 3 * DEG), F);
  B.add(gRBox(0.49, 0.05, 0.48, 0.012, 1), M4.trs(x0, 0.335, -0.29), SEATMAT.pyShell);
  // QA r2: the centre of the back sits ~3 cm behind its old face between the bolsters (d 0.10 at y 0.34-0.52), and the top
  // blends into the headrest (overlapping sections instead of a step)
  loftAt(B, [SEC(0.0, 0.44, 0.09, -0.01, 0.025), SEC(0.05, 0.47, 0.115, -0.02), SEC(0.18, 0.48, 0.13, -0.032, 0.045), SEC(0.34, 0.48, 0.10, -0.014, 0.042),
    SEC(0.52, 0.47, 0.10, -0.009, 0.042), SEC(0.64, 0.45, 0.095, -0.008, 0.036), SEC(0.68, 0.44, 0.09, -0.006, 0.036)], BH, F, lod ? 3 : 4);
  // sculpted side bolsters standing ~5 cm proud of the centre, narrow at the waist (~0.30 above the cushion), flaring
  // at the shoulders (py_37301 / 37303) [D]
  for (const sd of [-1, 1]) {
    const BX = M4.mul(BH, M4.trs(sd * 0.205, 0, -0.03, -sd * 14 * DEG));
    loftAt(B, [SEC(0.02, 0.07, 0.10, 0, 0.03), SEC(0.10, 0.085, 0.14, -0.016, 0.042), SEC(0.30, 0.07, 0.14, -0.016, 0.034), SEC(0.48, 0.09, 0.13, -0.012, 0.042),
      SEC(0.60, 0.08, 0.10, -0.006, 0.036), SEC(0.66, 0.06, 0.08, 0, 0.028)], BX, F, lod ? 2 : 3);
  }
  if (!lod) B.add(gBox(0.40, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.30, -0.071)), { c: '#3c3e44', r: 0.8 });   // lumbar crease
  // thick rear shell that wraps round the back's sides (grey edge visible from the front)
  const zr = (y) => 0.105 + 0.014 * Math.sin(Math.PI * clamp(y / 0.84, 0, 1));
  // QA r2: the shell's rounded top rises above the headrest (to 0.97, headrest 0.91) and frames the screen from behind
  // (san_13 / san_24, py_37304); the top sections are rounded to half their depth
  const ds = [[-0.04, 0.05], [0.12, 0.06], [0.34, 0.07], [0.5, 0.084], [0.68, 0.09], [0.78, 0.085], [0.88, 0.08], [0.94, 0.06], [0.97, 0.035]];
  loftAt(B, ds.map(([y, d]) => SEC(y, 0.535, d, zr(y) - d / 2 + 0.01, y > 0.85 ? d / 2 - 0.002 : 0.026)), BH, SEATMAT.pyShell, lod ? 2 : 3);
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
  B.add(gBox(0.50, 0.008, 0.006), M4.mul(BH, M4.trs(0, 0.04, zr(0.04) + 0.022)), SEATMAT.pyTrim);
  // fold-up leg rest (stowed below the pan front)
  B.add(gLoft([SEC(0.0, 0.44, 0.05, 0, 0.018), SEC(0.30, 0.46, 0.06, 0, 0.022)], 3), M4.trs(x0, 0.07, -0.545, 0, -4 * DEG), F);
  B.add(gRBox(0.46, 0.02, 0.05, 0.008, 1), M4.trs(x0, 0.075, -0.54), SEATMAT.pyArm);            // leg-rest foot bar
  if (lod) return;
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz));
  if (!opts.noScreen) {
    // 15.6 in screen: black bezel 0.373 x 0.26 (active 0.345 x 0.195) in a grey housing ~0.44 x 0.30 that projects ~4 cm
    // and tilts top-back, its top just under the shell rim (py_37304: 1614 px/m; san_24) [D]
    const scr = (dz) => M4.mul(on(0.68, 0), M4.trs(0, 0, dz, 0, -6 * DEG));
    B.add(gRBox(0.44, 0.30, 0.04, 0.02, 1), scr(0.02), SEATMAT.pyShell);
    B.add(gRBox(0.373, 0.26, 0.012, 0.008, 1), scr(0.042), SEATMAT.bezel);
    B.add(gQuad(0.345, 0.194), scr(0.0495), SEATMAT.screen, atlasUV('screen'));
    // two white placards under the housing, grey pocket bay with a black mesh pocket (san_18 / san_20)
    for (const sx of [-0.12, 0.12]) B.add(gQuad(0.13, 0.03), on(0.505, 0.0115, sx), { c: '#e8e8e6', r: 0.6 });
    B.add(gRBox(0.36, 0.20, 0.006, 0.005, 1), on(0.38, 0.011), SEATMAT.pyBay);
    B.add(gRBox(0.30, 0.07, 0.01, 0.005, 1), on(0.32, 0.016), { c: '#1c1f24', r: 0.9, l: LAYER.grille });
    // coat hook: horizontal silver bullet high on the shell side + small round grey button below it (san_24)
    B.add(gCyl(0.012, 0.016, 0.07, 10), M4.mul(on(0.80, 0.03, 0.235), M4.trs(0, 0, 0, 0, Math.PI / 2)), SEATMAT.frame);
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
      // dark-grey arm cap running to the shroud front, where it rounds over and turns down ~6 cm (py_37301 right seat,
      // san_13); recessed darker panel on the shroud's outer face above the silver strip (py_37303)
      loftAt(B, [SEC(0.62, w, 0.52, -0.30, 0.02), SEC(0.648, w + 0.006, 0.53, -0.30, 0.028), SEC(0.668, w - 0.004, 0.52, -0.30, 0.02)], M4.trs(xa, 0, 0), SEATMAT.pyArmPad, 2);
      B.add(gCyl(0.024, 0.024, w, 12), M4.trs(xa, 0.644, -0.556, 0, 0, Math.PI / 2), SEATMAT.pyArmPad);
      B.add(gRBox(w, 0.06, 0.03, 0.012, 1), M4.trs(xa, 0.61, -0.565), SEATMAT.pyArmPad);
      if (!lod) B.add(gRBox(0.006, 0.28, 0.44, 0.01, 1), M4.trs(xa + o * 0.033, 0.36, -0.25), { c: '#55575a', r: 0.5, l: LAYER.plastic });
      B.add(gBox(0.006, 0.012, 0.58), M4.trs(xa + o * 0.037, 0.13, -0.27, 0, 8 * DEG), SEATMAT.pyTrim);
    }
    if (inner && !lod) {      // controls, AC + USB; clean padded console top (py_37303)
      B.add(gRBox(0.05, 0.006, 0.08, 0.004, 1), M4.trs(xa, 0.676, -0.3), SEATMAT.black);
      B.add(gBox(0.016, 0.008, 0.004), M4.trs(xa - 0.02, 0.56, -0.502), SEATMAT.port);
      B.add(gBox(0.03, 0.018, 0.004), M4.trs(xa + 0.02, 0.56, -0.502), SEATMAT.port);
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
  // flap ~0.38 x 0.28 (60 % of the back width), hanging from the back top (omaat_room_13, c_27313 / 27315) [D]
  B.add(gRBox(0.38, 0.28, 0.018, 0.008, 1), M4.mul(BH, M4.trs(0.05, 0.485, -0.052, 0, -8 * DEG)), SEATMAT.jHead);
  if (lod) return;
  B.add(gBox(0.60, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.29, -0.0385)), SEATMAT.jBase);            // stitched seam
  B.add(gBox(0.60, 0.005, 0.004), M4.mul(M4.trs(0, 0.39, -0.34, 0, 2 * DEG), M4.trs(0, 0.041, -0.10, 0, Math.PI / 2)), SEATMAT.jBase);
  B.add(gRBox(0.03, 0.05, 0.012, 0.004, 1), M4.mul(BH, M4.trs(0.05, 0.335, -0.05)), SEATMAT.jHead); // flap tab
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
// shared bits of the shell: flat charcoal cap on a wall top (shell tops read as flat charcoal, #545557-#717277 in
// omaat_room_10 / 13; the silver line is only on armrest ledges + door-leaf edges), door leading edge with a finger pull
function capRail(B, w, d, x, y, z) { B.add(gRBox(w + 0.006, 0.02, d + 0.006, 0.006, 1), M4.trs(x, y + 0.01, z), SEATMAT.jCap); }
function doorEdge(B, x, z, h) {
  B.add(gRBox(0.05, h, 0.04, 0.014, 2), M4.trs(x, 0.14 + h / 2, z), SEATMAT.jShell);
  B.add(gRBox(0.046, h - 0.06, 0.006, 0.004, 1), M4.trs(x, 0.14 + h / 2, z + 0.021), SEATMAT.ash);
  B.add(gRBox(0.012, 0.16, 0.02, 0.005, 1), M4.trs(x - 0.02, 0.86, z + 0.025), SEATMAT.jBase);
  B.add(gBox(0.046, 0.004, 0.044), M4.trs(x, 0.142, z), SEATMAT.jRail);                          // silver leaf bottom edge
}
// plan-view (x, z) outline -> slab of height h with its bottom at y0 (gExtrude runs along its own z: turn it to y)
function planSlab(B, pts, y0, h, mat) { B.add(gExtrude(pts.map(([x, z]) => [x, -z]), h), M4.trs(0, y0 + h / 2, 0, 0, -Math.PI / 2), mat); }
// rounded rectangle in plan, corner radii [x0z0, x1z0, x1z1, x0z1]
function planRRect(x0, x1, z0, z1, r, seg = 6) {
  const cs = [[x0 + r[0], z0 + r[0], r[0], Math.PI], [x1 - r[1], z0 + r[1], r[1], 1.5 * Math.PI], [x1 - r[2], z1 - r[2], r[2], 0], [x0 + r[3], z1 - r[3], r[3], 0.5 * Math.PI]];
  const pts = [];
  for (const [cx, cz, rr, a0] of cs) for (let k = 0; k <= seg; k++) { const a = a0 + (k / seg) * Math.PI / 2; pts.push([cx + Math.cos(a) * rr, cz + Math.sin(a) * rr]); }
  return pts;
}
// thin wall following the x0 side and the z0 end of a plan rectangle, rounded (radius R) at the x0z0 corner
function planBand(x0, x1, z0, z1, R, t, seg = 6) {
  const cx = x0 + R, cz = z0 + R, pts = [[x0, z1]];
  for (let k = 0; k <= seg; k++) { const a = Math.PI + (k / seg) * Math.PI / 2; pts.push([cx + Math.cos(a) * R, cz + Math.sin(a) * R]); }
  pts.push([x1, z0], [x1, z0 + t]);
  for (let k = seg; k >= 0; k--) { const a = Math.PI + (k / seg) * Math.PI / 2; pts.push([cx + Math.cos(a) * (R - t), cz + Math.sin(a) * (R - t)]); }
  pts.push([x0 + t, z1]);
  return pts;
}
// footwell under a monitor: grey upholstered pad on a shelf in a dark cavity, open below with a low step
// (omaat_room_16 / 17, c_27316: pad #66656b ~0.04 thick; REFERENCE777: mouth 21 in, 14 in high) [D]/[A]
// QA r2: the pad is a wedge in plan - full width at the mouth (the model's 0.41-0.43 m gap; 21 in written), 12 in (0.30)
// at the far end - straight along the unit's outer wall (wall = -1: x0 side, +1: x1 side), the inboard edge a convex
// arc bulging 0.04 (omaat_room_17, c_27316 / omaat_room_16) [V]/[D]
function footwellPlan(x0, x1, zm, zf, wall, inset = 0) {
  const xw = wall < 0 ? x0 + inset : x1 - inset, sx = -wall, wm = x1 - x0 - 2 * inset, wf = 0.30 - 2 * inset;
  const zmi = zm + Math.sign(zf - zm) * inset, zfi = zf - Math.sign(zf - zm) * inset;
  const pts = [[xw, zmi], [xw + sx * wm, zmi]];
  for (let k = 1; k < 6; k++) {
    const t = k / 6;
    pts.push([xw + sx * (lerp(wm, wf, t) + 0.04 * Math.sin(Math.PI * t)), lerp(zmi, zfi, t)]);
  }
  pts.push([xw + sx * wf, zfi], [xw, zfi]);
  return pts;
}
function roomFootwell(B, x0, x1, zm, zf, wall) {
  const s = Math.sign(zf - zm);
  planSlab(B, footwellPlan(x0, x1, zm, zf, wall), 0.38, 0.02, SEATMAT.jShellIn);
  planSlab(B, footwellPlan(x0, x1, zm, zf, wall, 0.012), 0.40, 0.04, SEATMAT.jFabric);
  planSlab(B, footwellPlan(x0, x1, zm + s * 0.04, zf - s * 0.04, wall), 0.01, 0.36, SEATMAT.jVoid);
  B.add(gRBox(x1 - x0, 0.02, 0.16, 0.006, 1), M4.trs((x0 + x1) / 2, 0.12, zm + s * 0.08), SEATMAT.jShellIn);
}
// monitor + under-strip on the central monument face (plane z = zf, facing dir): charcoal frame 0.64 x 0.40 round the
// 0.531 x 0.299 display, blue-lit literature slot + charcoal drawer with a green LED below (omaat_room_16, c_27316) [D]
function roomMonitor(B, xm, zf, dir, slotSide) {
  const zo = (d) => zf + dir * d, ry = dir > 0 ? 0 : Math.PI;
  B.add(gRBox(0.64, 0.40, 0.03, 0.015, 1), M4.trs(xm, 0.845, zo(0.015)), SEATMAT.bezel);
  B.add(gQuad(0.531, 0.299), M4.trs(xm, 0.85, zo(0.032), ry), SEATMAT.screen, atlasUV('screen'));
  // literature slot: dark recess glowing soft blue from inside, charcoal lip on its top edge (omaat_room_14 / 16, c_27305);
  // QA r2 was a bright flat blue quad
  const sx = xm + slotSide * 0.20;
  B.add(gRBox(0.14, 0.05, 0.03, 0.004, 1), M4.trs(sx, 0.60, zo(-0.013)), SEATMAT.jShellIn);
  B.add(gQuad(0.124, 0.036), M4.trs(sx, 0.597, zo(0.0025), ry), { c: '#2a4f9a', r: 0.5, e: 0.15 });
  B.add(gRBox(0.146, 0.005, 0.01, 0.002, 1), M4.trs(sx, 0.6225, zo(0.004)), SEATMAT.jBase);
  B.add(gRBox(0.30, 0.06, 0.012, 0.004, 1), M4.trs(xm - slotSide * 0.09, 0.60, zo(0.006)), SEATMAT.jShellIn);
  B.add(gCyl(0.003, 0.003, 0.004, 8), M4.mul(M4.trs(xm - slotSide * 0.21, 0.60, zo(0.013)), M4.trs(0, 0, 0, 0, Math.PI / 2)), SEATMAT.ledG);
}
// closed cabinet door beside the monitor on the same plane: plain ash with fine horizontal grain, 0.34 x 0.38 with its
// top level with the monitor frame top, 4 mm silver bottom trim (omaat_room_16; mirror + navy interior only when open,
// omaat_room_21) [D]
// QA r2: the door is split ~0.06 above its bottom into a lower ash band, with slim grey side stiles (c_27305 split ~0.07
// above the bottom; omaat_room_16 lower band 45 / 255 px of the cabinet height; tt_storage-3) [D]
function roomCabinet(B, xc, zf, dir) {
  const z = zf + dir * 0.004;
  B.add(gRBox(0.34, 0.31, 0.012, 0.004, 1), M4.trs(xc, ROOM.top + 0.225, z), SEATMAT.ash);
  B.add(gRBox(0.34, 0.058, 0.012, 0.004, 1), M4.trs(xc, ROOM.top + 0.035, z), SEATMAT.ash);
  B.add(gBox(0.34, 0.006, 0.008), M4.trs(xc, ROOM.top + 0.067, zf + dir * 0.002), SEATMAT.jShell);      // 4 mm split
  for (const s of [-1, 1]) B.add(gRBox(0.008, 0.38, 0.014, 0.002, 1), M4.trs(xc + s * 0.174, ROOM.top + 0.19, z), SEATMAT.jShell);
  B.add(gBox(0.34, 0.004, 0.016), M4.trs(xc, ROOM.top + 0.002, z), SEATMAT.jRail);
}
// seat controls on the console's vertical face: black button panel with a blue ring + a handset with a colour screen in
// a charcoal recess (omaat_room_16 / 18, c_27308 / 27316). xf places the pair: local x along the face, +z out of it
function roomControls(B, xf, side) {
  B.add(gRBox(0.12, 0.05, 0.008, 0.012, 1), M4.mul(xf, M4.trs(0, 0.575, 0.002)), SEATMAT.black);
  B.add(gQuad(0.05, 0.03), M4.mul(xf, M4.trs(0, 0.575, 0.0065)), { c: '#3a7bd5', r: 0.3, e: 0.4 });
  B.add(gRBox(0.10, 0.07, 0.006, 0.008, 1), M4.mul(xf, M4.trs(side * 0.14, 0.55, 0.001)), SEATMAT.black);
  B.add(gCyl(0.009, 0.009, 0.003, 12), M4.mul(xf, M4.trs(side * 0.12, 0.565, 0.004, 0, Math.PI / 2)), { c: '#6c9cff', r: 0.4, e: 0.3 });
  for (let b = 0; b < 3; b++) B.add(gCyl(0.005, 0.005, 0.003, 8), M4.mul(xf, M4.trs(side * (0.12 + b * 0.02), 0.535, 0.004, 0, Math.PI / 2)), SEATMAT.card);
}
// ash panels in ~28 mm charcoal frames on an aisle face (x = px) below the armrest ledge, charcoal kick below
// (c_27313 bottom row, omaat_room_10)
function roomAisleAsh(B, px, z0, z1) {
  B.add(gRBox(0.008, 0.52, z1 - z0 - 0.02, 0.003, 1), M4.trs(px + 0.002, 0.36, (z0 + z1) / 2), SEATMAT.ash);
  ashFrameX(B, px + 0.002, 0.008, 0.10, 0.62, z0 + 0.005, z1 - 0.005);
}
// reading light in the shell corner: large black lamp in a bezel ring + small fitting below (omaat_room_13, c_27315)
function roomLamp(B, x, z, dir) {
  const rx = dir > 0 ? Math.PI / 2 : -Math.PI / 2;
  B.add(gCyl(0.028, 0.028, 0.012, 16), M4.trs(x, 1.03, z + dir * 0.004, 0, rx), { c: '#1a1b1e', r: 0.4 });
  B.add(gCyl(0.022, 0.022, 0.02, 14), M4.trs(x, 1.03, z + dir * 0.008, 0, rx), SEATMAT.black);
  B.add(gCyl(0.015, 0.015, 0.004, 12), M4.trs(x, 1.03, z + dir * 0.0185, 0, rx), SEATMAT.lampGlow);
  B.add(gCyl(0.014, 0.014, 0.014, 12), M4.trs(x, 0.985, z + dir * 0.006, 0, rx), SEATMAT.black);
}

// Central monument of a pair between z = MON.zO (O's face, looking -z at O) and MON.zE (E's face, +z): O's monitor
// (outer column) back to back with E's cabinet, O's cabinet (aisle column) back to back with E's monitor; both footwells
// run under it (omaat_room_14 / 16, c_27316: cabinet flush beside the monitor frame, footwell mouth under the monitor)
const MON = { zO: -0.21, zE: 0.035, top: 1.05, bot: 0.555 };
function roomPart(part, opts = {}) {
  const B = new Builder();
  const bed = !!opts.bed, lod = !!opts.lod;
  const { hx, hz, top, wall } = ROOM;
  const shell = SEATMAT.jShell, ash = SEATMAT.ash;
  if (part === 'O') {
    // --- the seat: back against the forward end, facing aft (+z)
    const S = M4.trs(-0.24, 0, -1.27, Math.PI);
    const tmp = new Builder(); roomSeatCore(tmp, bed, lod); B.addBuilt(tmp.build(), S);
    // back shell: charcoal wall, dark padded band above the seat back, cap, reading light in the corner
    B.add(gRBox(0.70, wall, 0.07, 0.03, 2), M4.trs(-0.235, wall / 2, -1.31), shell);
    B.add(gRBox(0.64, 0.30, 0.02, 0.012, 1), M4.trs(-0.24, 0.93, -1.268), SEATMAT.jLeather);
    capRail(B, 0.70, 0.07, -0.235, wall, -1.31);
    roomLamp(B, -0.52, -1.258, 1);
    // aisle corner: LOW armrest ledge (0.66) holding the retracted pop-up privacy panel (only its ash top edge shows)
    B.add(gRBox(0.50, top, 0.28, 0.02, 1), M4.trs(0.335, top / 2, -1.20), shell);
    B.add(gRBox(0.16, 0.035, 0.28, 0.014, 2), M4.trs(0.17, top + 0.012, -1.20), SEATMAT.jLeather);
    B.add(gRBox(0.34, 0.03, 0.28, 0.012, 2), M4.trs(0.415, top + 0.01, -1.20), SEATMAT.jRail);
    B.add(gBox(0.022, 0.006, 0.26), M4.trs(0.48, top + 0.027, -1.20), ash);
    roomAisleAsh(B, hx, -1.34, -1.06);
    if (!lod) B.add(gRBox(0.08, 0.05, 0.004, 0.004, 1), M4.trs(0.42, 0.50, -1.0585), SEATMAT.black);   // stowage latch
    // O's side table over E's footwell (aisle column): ash top with a large-radius rounded front corner, thin silver band
    // under it, charcoal console body whose seat-facing face carries the controls (omaat_room_14 / 18, c_27316)
    const tx0 = 0.12, tx1 = 0.55, tz0 = -0.62, R = 0.11;
    planSlab(B, planRRect(tx0, tx1, tz0, MON.zO, [R, 0.01, 0.004, 0.004]), top - 0.035, 0.035, ash);
    planSlab(B, planRRect(tx0 + 0.004, tx1, tz0 + 0.004, MON.zO, [R - 0.004, 0.004, 0.004, 0.004]), top - 0.041, 0.006, SEATMAT.jRail);
    planSlab(B, planBand(tx0 + 0.012, tx1, tz0 + 0.012, MON.zO, R - 0.012, 0.02), 0, top - 0.041, shell);
    if (!lod) roomControls(B, M4.trs(0.30, 0, tz0 + 0.012, Math.PI), -1);
    // tall ash monument end at the aisle with a wide flat cap (seat plaques lie on it, c_27313) + kick
    const ez0 = -0.58, ez1 = MON.zE, ezc = (ez0 + ez1) / 2;
    B.add(gRBox(0.04, wall, ez1 - ez0, 0.012, 1), M4.trs(0.565, wall / 2, ezc), ash);
    B.add(gRBox(0.045, 0.10, ez1 - ez0, 0.01, 1), M4.trs(0.565, 0.05, ezc), shell);
    ashFrameX(B, 0.565, 0.04, 0.10, wall, ez0, ez1);
    // shared aisle-end cap: mid grey, a little darker than the plaques, oval finger recess between them (c_27314)
    B.add(gRBox(0.10, 0.02, ez1 - ez0 + 0.006, 0.006, 1), M4.trs(0.54, wall + 0.01, ezc), { c: '#7c7f84', r: 0.45, l: LAYER.plastic });
    if (!lod) B.add(gCyl(1, 1, 1, 16), M4.trs(0.545, wall + 0.0205, ezc, 0, 0, 0, 0.0175, 0.003, 0.035), SEATMAT.jBase);
    // E's footwell under the table + monument (aisle column), mouth under E's monitor
    B.add(gRBox(0.41, 0.02, MON.zO - tz0 - 0.03, 0.006, 1), M4.trs(0.3375, 0.57, (MON.zO + tz0 + 0.03) / 2), SEATMAT.jShellIn);
    roomFootwell(B, 0.135, 0.545, MON.zE, tz0 + 0.035, 1);
    // sliding door parked in the monument; its leading edge (ash face, charcoal frame, finger pull) faces aft
    doorEdge(B, 0.56, -0.60, wall - 0.14);
    // central monument body (both columns) + the pillar between the two footwell mouths
    B.add(gRBox(1.13, MON.top - MON.bot, MON.zE - MON.zO, 0.01, 1), M4.trs(-0.02, (MON.top + MON.bot) / 2, (MON.zO + MON.zE) / 2), shell);
    B.add(gRBox(0.245, MON.bot, MON.zE - MON.zO, 0.01, 1), M4.trs(0.0075, MON.bot / 2, (MON.zO + MON.zE) / 2), shell);
    // O's face: monitor (outer column) + O's cabinet (aisle column)
    roomMonitor(B, -0.245, MON.zO, -1, 1);
    roomCabinet(B, 0.255, MON.zO, -1);
    // O's footwell under E's console (outer column), mouth under O's monitor
    B.add(gRBox(0.44, 0.02, 0.585, 0.006, 1), M4.trs(-0.35, 0.57, 0.33), SEATMAT.jShellIn);
    roomFootwell(B, -0.56, -0.13, MON.zO, 0.62, -1);
    if (bed) {
      B.add(gLoft(cushionSecs(0.62, 1.76, 0.05, -0.02, { edge: 0.02, r: 0.03, crown: 0.004 }), 3), M4.trs(-0.26, ROOM.bed + 0.02, -0.40), SEATMAT.mattress);
      B.add(gLoft(cushionSecs(0.56, 1.1, 0.06, -0.03, { edge: 0.03, r: 0.05 }), 3), M4.trs(-0.28, ROOM.bed + 0.07, -0.05), SEATMAT.duvet);
      B.add(gLoft(cushionSecs(0.46, 0.30, 0.12, -0.06, { edge: 0.05, r: 0.05 }), 3), M4.trs(-0.24, ROOM.bed + 0.08, -1.08), SEATMAT.pillow);
    } else {
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
    roomLamp(B, -0.07, 1.258, -1);
    // narrow aisle armrest with the pop-up privacy panel retracted inside (ash edge flush in the cap)
    B.add(gRBox(0.09, top, 0.60, 0.02, 1), M4.trs(0.54, top / 2, 0.95), shell);
    B.add(gRBox(0.10, 0.03, 0.62, 0.012, 2), M4.trs(0.54, top + 0.01, 0.95), SEATMAT.jRail);
    B.add(gBox(0.022, 0.006, 0.58), M4.trs(0.555, top + 0.027, 0.95), ash);
    roomAisleAsh(B, hx, 0.65, 1.25);
    // wide console by the outer column (window / centreline) from the monument to the back shell, hollow under its
    // forward half (O's footwell); ash top on a thin silver band
    const cz0 = MON.zE, cz1 = 1.30, czc = (cz0 + cz1) / 2;
    B.add(gRBox(0.45, 0.035, cz1 - cz0, 0.01, 1), M4.trs(-0.355, top - 0.018, czc), ash);
    B.add(gRBox(0.452, 0.006, cz1 - cz0 - 0.004, 0.003, 1), M4.trs(-0.352, top - 0.038, czc), SEATMAT.jRail);
    B.add(gRBox(0.44, top - 0.041, 0.66, 0.02, 1), M4.trs(-0.355, (top - 0.041) / 2, 0.95), SEATMAT.jShellIn);
    B.add(gRBox(0.02, top - 0.041, cz1 - cz0, 0.008, 1), M4.trs(-0.125, (top - 0.041) / 2, czc), shell);
    if (!lod) {
      B.add(gRBox(0.02, 0.05, 0.10, 0.004, 1), M4.trs(-0.114, 0.50, 1.0), { c: '#b3262a', r: 0.5 });   // life-vest tab (red, c_27302)
      roomControls(B, M4.trs(-0.115, 0, 0.70, Math.PI / 2), -1);
    }
    // E's face of the monument: E's cabinet (outer column) + E's monitor (aisle column); mouth of E's footwell below
    roomCabinet(B, -0.30, MON.zE, 1);
    roomMonitor(B, 0.21, MON.zE, 1, -1);
    // E's sliding door parked in the monitor monument; leading edge faces aft toward E's entry
    doorEdge(B, 0.56, 0.06, wall - 0.14);
    if (bed) {
      B.add(gLoft(cushionSecs(0.58, 1.80, 0.05, -0.02, { edge: 0.02, r: 0.03, crown: 0.004 }), 3), M4.trs(0.24, ROOM.bed + 0.02, 0.38), SEATMAT.mattress);
      B.add(gLoft(cushionSecs(0.54, 1.1, 0.06, -0.03, { edge: 0.03, r: 0.05 }), 3), M4.trs(0.25, ROOM.bed + 0.07, 0.05), SEATMAT.duvet);
      B.add(gLoft(cushionSecs(0.46, 0.30, 0.12, -0.06, { edge: 0.05, r: 0.05 }), 3), M4.trs(0.20, ROOM.bed + 0.08, 1.08), SEATMAT.pillow);
    } else {
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
    B.add(gBox(0.04, wall, 0.655), M4.trs(0.565, wall / 2, -0.2925), SEATMAT.ash);
    B.add(gBox(0.43, top, 0.41), M4.trs(0.335, top / 2, -0.415), SEATMAT.jShell);
    B.add(gBox(1.13, MON.top, MON.zE - MON.zO), M4.trs(-0.02, MON.top / 2, (MON.zO + MON.zE) / 2), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(-0.245, 0.85, MON.zO - 0.002, Math.PI), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.34, 0.38, 0.01), M4.trs(0.255, top + 0.19, MON.zO - 0.004), SEATMAT.ash);
  } else {
    B.add(gBox(0.69, wall, 0.07), M4.trs(0.235, wall / 2, 1.31), SEATMAT.jShell);
    B.add(gRBox(0.58, 0.45, 0.6, 0.03, 1), M4.trs(0.2, 0.225, 0.95), SEATMAT.jFabric);
    B.add(gRBox(0.58, 0.6, 0.12, 0.04, 1), M4.mul(M4.trs(0.2, 0.43, 1.2), M4.trs(0, 0.3, 0, 0, 17 * DEG)), SEATMAT.jFabric);
    B.add(gBox(0.45, top, 1.265), M4.trs(-0.355, top / 2, 0.6675), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(0.21, 0.85, MON.zE + 0.002), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.34, 0.38, 0.01), M4.trs(-0.30, top + 0.19, MON.zE + 0.004), SEATMAT.ash);
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
  B.add(gRBox(0.056, 0.02, 2.6, 0.006, 1), M4.trs(0, 1.07, 0.0), SEATMAT.jCap);
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
  // thick rounded taupe cap overhanging every wall top by 2.5 cm each side (omaat_f58 / f60 / f7, tpa_IMG_0220) [A size]
  const cap = (cw, cd, x, y, z) => B.add(gRBox(cw + 0.05, 0.085, cd + 0.05, 0.038, 3), M4.trs(x, y + 0.02, z), SEATMAT.fCap);
  // aft wall (behind the seat) + front wall with the 43 in screen
  B.add(gRBox(w, H, 0.06, 0.02, 1), M4.trs(0, H / 2, -0.07), SEATMAT.fShell);
  cap(w, 0.06, 0, H, -0.07);
  B.add(gRBox(w, H, 0.12, 0.02, 1), M4.trs(0, H / 2, -L + 0.06), SEATMAT.fShell);
  cap(w, 0.12, 0, H, -L + 0.06);
  // QA r2 screen wall (omaat_f11 / f7 / f60, f_17300 / 17304): dark straight-grain wood on BOTH sides of the 43 in screen -
  // a ~0.10 wing with a rounded upper outer corner on the window side above the console end, and a ~0.16 pier on the
  // aisle side carrying the reading lamp (outer top corner) and a pill-shaped vanity mirror. Screen edge -> table edge
  // is ~0.07 m on the window side and ~0.16 m on the aisle side in f11 (px scaled by the 0.952 m screen) [D]
  const scx = xo + 0.10 + 0.476;
  B.add(gRBox(0.976, 0.555, 0.02, 0.006, 1), M4.trs(scx, 0.95, -L + 0.13), SEATMAT.bezel);
  B.add(gQuad(0.952, 0.535), M4.trs(scx, 0.95, -L + 0.141), SEATMAT.screen, atlasUV('screen'));
  B.add(gRBox(0.088, H - 0.68, 0.03, 0.03, 2), M4.trs(xo + 0.044, 0.68 + (H - 0.68) / 2, -L + 0.135), SEATMAT.fWood);
  const pX0 = scx + 0.488, pX = (pX0 + hx) / 2;       // pier from the screen edge to the outer aisle wall (0.158 wide)
  B.add(gRBox(hx - pX0, H - 0.62, 0.03, 0.01, 1), M4.trs(pX, 0.62 + (H - 0.62) / 2, -L + 0.135), SEATMAT.fWood);
  // mirror: dark glass in a thin taupe rim, lit edge on the aisle side (omaat_f11 left pier, omaat_f5 1D/1G, f_17313)
  const mX = pX0 + 0.058;
  B.add(gRBox(0.10, 0.36, 0.012, 0.045, 3), M4.trs(mX, 0.97, -L + 0.155), SEATMAT.fShell);
  B.add(gRBox(0.085, 0.345, 0.004, 0.04, 3), M4.trs(mX, 0.97, -L + 0.162), { c: '#1c1d20', r: 0.08 });
  if (!lod) B.add(gBox(0.004, 0.28, 0.004), M4.trs(mX + 0.048, 0.97, -L + 0.162), SEATMAT.fLed);
  B.add(gCyl(0.022, 0.022, 0.02, 14), M4.trs(hx - 0.035, 1.20, -L + 0.155, 0, Math.PI / 2), SEATMAT.fLeather);
  B.add(gCyl(0.013, 0.013, 0.004, 12), M4.trs(hx - 0.035, 1.20, -L + 0.166, 0, Math.PI / 2), SEATMAT.lampGlow);
  // stowed dining table under the screen: dark-wood slab ~0.72 wide (460 / 605 px of the screen width in f11) x 0.20
  // filling the gap between the aisle box and the window console, black front lip (omaat_f11 / f33 / f23) [D]
  const tX0 = xo + shelfW, tX1 = xa - 0.16, tXc = (tX0 + tX1) / 2;
  B.add(gRBox(tX1 - tX0, 0.035, 0.20, 0.008, 1), M4.trs(tXc, 0.625, -L + 0.22), SEATMAT.fShelf);
  B.add(gRBox(tX1 - tX0, 0.03, 0.012, 0.004, 1), M4.trs(tXc, 0.60, -L + 0.325), SEATMAT.black);
  if (!lod) B.add(gRBox(0.05, 0.012, 0.006, 0.003, 1), M4.trs(tXc, 0.60, -L + 0.333), { c: '#b9b6b0', r: 0.35, m: 0.8 });   // PULL tab
  // aisle box beside the ottoman, its top level with the table (f11: box top at the table top) [D]
  const bX0 = xa - 0.16, bX1 = hx - 0.04;
  B.add(gRBox(bX1 - bX0, 0.60, 0.36, 0.015, 1), M4.trs((bX0 + bX1) / 2, 0.30, -L + 0.30), SEATMAT.fInner);
  B.add(gRBox(bX1 - bX0 + 0.01, 0.02, 0.37, 0.008, 1), M4.trs((bX0 + bX1) / 2, 0.61, -L + 0.30), SEATMAT.fConsole);
  // ottoman (padded, same tweed as the seat) with belt
  const ow = xa - xo - 0.19;
  const ox = xo + ow / 2 + 0.005;
  B.add(gRBox(ow, 0.36, 0.52, 0.02, 1), M4.trs(ox, 0.18, -L + 0.39), SEATMAT.fInner);
  B.add(gLoft(cushionSecs(ow - 0.01, 0.52, 0.08, -0.04, { edge: 0.025, r: 0.025 }), 3), M4.trs(ox, 0.40, -L + 0.39), SEATMAT.fFabric);
  if (!lod) for (const s of [-1, 1]) B.add(gBox(0.04, 0.004, 0.2), M4.trs(ox + 0.12 * s, 0.443, -L + 0.42), SEATMAT.strap);
  // outer side: low skirt (window) or full-height partition half (centre), plus the long console
  if (center) {
    // centre divider: a large dark straight-grain wood face above the console in a taupe edge frame, taupe cap
    // (f_17314, tpa_IMG_0220 #24262d-#705850)
    B.add(gRBox(0.03, H, L - 0.14, 0.01, 1), M4.trs(-hx + 0.015, H / 2, -L / 2), SEATMAT.fDoor);
    B.add(gRBox(0.006, H - 0.70, L - 0.34, 0.004, 1), M4.trs(-hx + 0.033, 0.68 + (H - 0.70) / 2, -L / 2 - 0.04), SEATMAT.fWood);
    for (const z of [-L + 0.17, -0.19]) B.add(gRBox(0.008, H - 0.70, 0.03, 0.003, 1), M4.trs(-hx + 0.034, 0.68 + (H - 0.70) / 2, z), SEATMAT.fShell);
    cap(0.03, L - 0.14, -hx + 0.015, H, -L / 2);
  } else B.add(gRBox(0.03, 0.70, L - 0.14, 0.01, 1), M4.trs(-hx + 0.015, 0.35, -L / 2), SEATMAT.fShell);
  B.add(gRBox(shelfW, 0.64, L - 0.30, 0.02, 1), M4.trs(xo + shelfW / 2, 0.32, -L / 2 - 0.04), SEATMAT.fConsole);
  B.add(gRBox(shelfW + 0.01, 0.025, L - 0.30, 0.008, 1), M4.trs(xo + shelfW / 2, 0.652, -L / 2 - 0.04), SEATMAT.fShell);
  // recessed dark-wood tray in the console top, forward of the keypad (starts forward of z -0.90, omaat_f5)
  B.add(gRBox(shelfW - 0.05, 0.006, 0.80, 0.004, 1), M4.trs(xo + shelfW / 2, 0.666, -1.32), SEATMAT.fShelf);
  if (!lod) {
    // QA r2: handset AFT (nearest the seat), keypad directly FORWARD of it on a raised section (up_Privacy-Wall, omaat_f5 /
    // f7). Keypad: light warm-grey panel ~0.12 x 0.13 (#8a8882) with white LINE icons - 3 pill buttons, 3 +/- pairs,
    // 4 icons (omaat_f14) [D]
    const kx = xo + shelfW / 2, flat = (x, y, z) => M4.trs(x, y, z, 0, -Math.PI / 2), glyph = { c: '#f2f2f2', r: 0.4, e: 0.1 };
    const kz = -0.80, ky = 0.675;
    B.add(gRBox(0.13, 0.012, 0.15, 0.006, 1), M4.trs(kx, 0.668, kz), SEATMAT.fConsole);
    B.add(gRBox(0.12, 0.006, 0.13, 0.006, 1), M4.trs(kx, ky, kz), { c: '#8a8882', r: 0.5 });
    // rows run across the console (x), stacked along z; outlines drawn as thin light strokes
    const ring = (x, z, w, d) => { for (const s of [-1, 1]) { B.add(gQuad(w, 0.0015), flat(x, ky + 0.0035, z + s * d / 2), glyph); B.add(gQuad(0.0015, d), flat(x + s * w / 2, ky + 0.0035, z), glyph); } };
    for (let c = 0; c < 3; c++) ring(kx + (c - 1) * 0.034, kz - 0.045, 0.024, 0.010);                     // pill buttons
    for (let c = 0; c < 3; c++) for (const dz of [-0.008, 0.012]) {                                      // - / + pairs
      B.add(gQuad(0.008, 0.0015), flat(kx + (c - 1) * 0.034, ky + 0.0035, kz + dz), glyph);
      if (dz > 0) B.add(gQuad(0.0015, 0.008), flat(kx + (c - 1) * 0.034, ky + 0.0035, kz + dz), glyph);
    }
    for (let c = 0; c < 4; c++) ring(kx + (c - 1.5) * 0.026, kz + 0.045, 0.010, 0.010);                 // icons
    // handset: black landscape controller with rounded ends lying along the console, colour screen + a D-pad at each
    // end (omaat_f15 / f5: ~0.20 x 0.075 m, screen ~0.09 x 0.05) [D]
    const hz = -0.60;
    B.add(gRBox(0.075, 0.014, 0.20, 0.03, 3), M4.trs(kx, 0.671, hz), { c: '#101112', r: 0.3 });
    B.add(gQuad(0.05, 0.09), flat(kx, 0.6785, hz), { c: '#3a6fb8', r: 0.2, e: 0.35 });
    for (const dz of [-0.075, 0.075]) B.add(gCyl(0.01, 0.01, 0.003, 12), M4.trs(kx, 0.679, hz + dz), { c: '#26282b', r: 0.35 });
    B.add(gRBox(0.02, 0.06, 0.12, 0.004, 1), M4.trs(xo + shelfW + 0.001, 0.58, -1.05), SEATMAT.black); // outlets pocket
    // air grille low on the console face (f_17302)
    B.add(gBox(0.004, 0.10, 0.70), M4.trs(xo + shelfW + 0.001, 0.14, -1.35), { c: '#2a2724', r: 0.8, l: LAYER.grille });
  }
  // aisle side: thick wardrobe wall beside the seat. Its inner face is dark wood with ONE taupe-framed door (safety card
  // / mirror behind it) above the lit literature pocket (omaat_f2 / f5 / f35 / f36); coat hook
  B.add(gRBox(0.16, H, 0.86, 0.02, 1), M4.trs(hx - 0.08, H / 2, -0.53), SEATMAT.fShell);
  cap(0.16, 0.86, hx - 0.08, H, -0.53);
  B.add(gRBox(0.006, H - 0.20, 0.80, 0.004, 1), M4.trs(xa - 0.003, 0.10 + (H - 0.20) / 2, -0.53), SEATMAT.fWood);
  B.add(gRBox(0.014, 0.42, 0.32, 0.012, 1), M4.trs(xa - 0.008, 0.96, -0.62), SEATMAT.fShell);          // door frame ~0.30 x 0.40 [D]
  B.add(gRBox(0.004, 0.36, 0.26, 0.004, 1), M4.trs(xa - 0.016, 0.96, -0.62), SEATMAT.fWood);           // closed door: wood face (f35)
  if (!lod) B.add(gBox(0.003, 0.03, 0.20), M4.trs(xa - 0.0165, 0.795, -0.62), { c: '#cfcac2', r: 0.6 }); // safety label strip
  if (!lod) {
    B.add(gRBox(0.02, 0.018, 0.10, 0.006, 1), M4.trs(xa - 0.02, 1.16, -0.25), SEATMAT.frame);                  // coat hook rail
    B.add(gRBox(0.05, 0.10, 0.20, 0.008, 1), M4.trs(xa - 0.03, 0.66, -0.20), SEATMAT.fInner);                   // lit literature niche
    B.add(gBox(0.004, 0.06, 0.16), M4.trs(xa - 0.056, 0.67, -0.20), SEATMAT.fWarm);
  }
  // front aisle corner: the aisle box (above) + a thin outer wall holding the parked door, open between it and the
  // pier above the box (f11: taupe side wall left of the pier)
  B.add(gRBox(0.04, H, 0.26, 0.012, 1), M4.trs(hx - 0.02, H / 2, -L + 0.25), SEATMAT.fShell);
  cap(0.04, 0.26, hx - 0.02, H, -L + 0.25);
  // aisle-facing exterior: framed door panels of rounded vertical ribs (omaat_f60 / f33 / f7: ~20 ribs per 0.55 m door,
  // pitch ~0.022, ~0.035 taupe frame) + LED line at the floor (f_17300 / 17301)
  if (!lod) {
    const yc = 0.14 + (H - 0.24) / 2;
    for (const [z0, z1] of [[-0.96, -0.10], [-L + 0.12, -L + 0.38]]) {
      const len = z1 - z0;
      B.add(gBox(0.004, H - 0.30, len - 0.06), M4.trs(hx + 0.002, yc, (z0 + z1) / 2), SEATMAT.fFluteGap);
      for (let z = z0 + 0.04; z < z1 - 0.03; z += 0.022) B.add(gCyl(0.007, 0.007, H - 0.30, 6, false, -Math.PI / 2, Math.PI), M4.trs(hx + 0.002, yc, z), SEATMAT.fFlute);
      for (const z of [z0 + 0.0175, z1 - 0.0175]) B.add(gRBox(0.014, H - 0.24, 0.035, 0.005, 1), M4.trs(hx + 0.006, yc, z), SEATMAT.fShell);
      for (const y of [0.14 + 0.0175, H - 0.10 - 0.0175]) B.add(gRBox(0.014, 0.035, len, 0.005, 1), M4.trs(hx + 0.006, y, (z0 + z1) / 2), SEATMAT.fShell);
      B.add(gBox(0.006, 0.008, len - 0.02), M4.trs(hx + 0.004, 0.06, (z0 + z1) / 2), SEATMAT.fLed);
    }
  }
  // (the sliding doors are parked inside the wardrobe wall and the front outer wall; QA r2: the old parked-door boxes
  // stood 3 mm proud of the rib plane and showed as pale bands above / below the rib frames)
  // small silver pulls on the frame stiles at the leaves' meeting edges, ~0.6 m up (omaat_f60 / f33)
  if (!lod) for (const zz of [-0.10 - 0.035, -L + 0.12 + 0.035]) B.add(gRBox(0.012, 0.09, 0.02, 0.004, 1), M4.trs(hx + 0.019, 0.60, zz), { c: '#b9b6b0', r: 0.3, m: 0.85 });
  // the seat: upholstered base, thin cushion, flat back leaning on the aft wall, slate headrest flap (f_17302 / 17309)
  const S = M4.trs(seatX, 0, -0.14);
  const F = SEATMAT.fFabric;
  B.add(gRBox(0.66, 0.34, 0.62, 0.02, 1), M4.mul(S, M4.trs(0, 0.17, -0.36)), F);
  // solid taupe box armrest beside the wardrobe, flat taupe top at ~0.62, literature pocket in its inner face
  // (omaat_f13 both seats, omaat_f5 / f2) [D]
  B.add(gRBox(0.10, 0.62, 0.62, 0.02, 1), M4.mul(S, M4.trs(0.38, 0.31, -0.40)), SEATMAT.fConsole);
  B.add(gRBox(0.11, 0.025, 0.63, 0.01, 1), M4.mul(S, M4.trs(0.38, 0.632, -0.40)), SEATMAT.fShell);
  if (!lod) B.add(gRBox(0.006, 0.16, 0.26, 0.004, 1), M4.mul(S, M4.trs(0.329, 0.45, -0.40)), SEATMAT.fInner);
  // two black dome reading lamps, one in each upper corner of the aft wall beside the seat back (omaat_f13 / f2)
  for (const lx of [xa - 0.06, xo + shelfW + 0.05]) {
    B.add(gCyl(0.024, 0.024, 0.02, 14), M4.trs(lx, 1.15, -0.10, 0, -Math.PI / 2), SEATMAT.fLeather);
    B.add(gCyl(0.015, 0.015, 0.004, 12), M4.trs(lx, 1.15, -0.089, 0, -Math.PI / 2), SEATMAT.lampGlow);
  }
  if (bed) {
    B.add(gLoft(cushionSecs(0.66, 1.96, 0.06, -0.03, { edge: 0.03, r: 0.035, crown: 0.004 }), 3), M4.trs(seatX - 0.01, 0.44, -1.08), { c: '#f0efea', r: 0.9, l: LAYER.fabric });
    B.add(gRBox(ow, 0.44, 0.9, 0.03, 1), M4.trs(ox, 0.22, -1.40), SEATMAT.fInner);
    // white duvet from the pillows to the ottoman, white pillow + lavender pillow (omaat_f57 / f58 / f59, f_17304)
    B.add(gLoft(cushionSecs(0.70, 1.55, 0.05, -0.025, { edge: 0.04, r: 0.06 }), 3), M4.trs(seatX - 0.01, 0.50, -1.12), { c: '#ebe8e2', r: 0.95, l: LAYER.fabric });
    B.add(gLoft(cushionSecs(0.5, 0.32, 0.13, -0.065, { edge: 0.05, r: 0.05 }), 3), M4.trs(seatX, 0.52, -0.25), SEATMAT.pillow);
    B.add(gLoft(cushionSecs(0.44, 0.28, 0.10, -0.05, { edge: 0.04, r: 0.045 }), 3), M4.trs(seatX + 0.05, 0.56, -0.40), SEATMAT.fCushionBlue);
  } else {
    B.add(gLoft(cushionSecs(0.66, 0.62, 0.075, -0.035, { edge: 0.022, r: 0.02, crown: 0.004 }), lod ? 3 : 4), M4.mul(S, M4.trs(0, 0.375, -0.36, 0, 2 * DEG)), F);
    const BH = M4.mul(S, M4.trs(0, 0.42, -0.10, 0, 11 * DEG));
    loftAt(B, [SEC(0.0, 0.64, 0.06, 0, 0.02), SEC(0.025, 0.66, 0.08, 0, 0.028), SEC(0.64, 0.66, 0.08, 0, 0.028), SEC(0.665, 0.64, 0.06, 0.002, 0.02)], BH, F, lod ? 2 : 3);
    // flap ~75 % of the back width (omaat_f2 / f13)
    B.add(gRBox(0.48, 0.15, 0.02, 0.008, 1), M4.mul(BH, M4.trs(0.02, 0.55, -0.052, 0, -6 * DEG)), SEATMAT.fFlap);
    if (!lod) {
      B.add(gBox(0.62, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.30, -0.041)), SEATMAT.fInner);
      B.add(gBox(0.62, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.18, -0.041)), SEATMAT.fInner);
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
  // seat-number plaques: dark rounded tiles with lit characters lying FLAT on the aisle-corner cap, reading from the aisle
  // (Suite: forward end of the wardrobe cap, omaat_f58 / f60 / f7, tpa_IMG_0220, f_17301; Room: top of the aisle-end
  // post, c_27313 '17E' / '18D', c_27314 / 27315, omaat_room_14). World space, not instanced.
  const T = new Builder();
  const tagGlow = { c: '#ffffff', r: 0.4, l: LAYER.atlasGlow, e: 0.3 };
  for (const s of layout.seats) {
    if (!ATL.rects['tag' + s.id]) continue;
    let p, plate;
    // QA r2: neutral grey rounded squares slightly lighter than the cap (c_27314 cap #878787)
    if (s.kind === 'room') { p = localToWorld(s, [0.545, ROOM.wall + 0.0205, s.odd ? -0.50 : -0.06]); plate = '#6b6e72'; }
    else { const hx = (s.pos === 'center' ? 1.10 : 1.24) / 2; p = localToWorld(s, [hx - 0.08, 1.30 + 0.0625, -0.80]); plate = '#2b2b2e'; }
    const face = s.mir ? -1 : 1;             // text top points away from the aisle
    const room = s.kind === 'room';
    T.add(room ? gRBox(0.055, 0.004, 0.065, 0.012, 1) : gRBox(0.045, 0.004, 0.08, 0.01, 1), M4.trs(p[0], p[1] + 0.002, p[2]), { c: plate, r: 0.45 });
    T.add(room ? gQuad(0.058, 0.03) : gQuad(0.07, 0.036), M4.trs(p[0], p[1] + 0.0045, p[2], face * Math.PI / 2, -Math.PI / 2), tagGlow, atlasUV('tag' + s.id));
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
