// ------------------------------------------------------------------
// THE Suite first class (JAMCO) - see REFERENCE777.md
// Seat-local frame and shared materials / helpers (SEATMAT, SEC, loftAt, cushionSecs) live in 09_seats.js.
// New materials for this product: Object.assign(SEATMAT, {...}) at the top of this file (loaded after 09_seats.js).
// ------------------------------------------------------------------
// ================= THE Suite (JAMCO) =================
// Suite frame: aft wall at z = 0, front wall (43 in screen) at z = -2.20; outer side (window or partition) at -x.
// w = outer width. Seat sits off-centre: full-length shelf on the outer side, slim wardrobe on the aisle side.
// w1 (rater A, omaat_f7 / pb_20 / up_privacy_wall): dark door-leaf frames and the near-black lower console body
Object.assign(SEATMAT, {
  fDoorFrame: { c: '#5c5a50', r: 0.5, l: LAYER.plastic },     // w5: ~1.15x the fluted field, not a light picture frame (omaat_f60 1.17x) [V]
  fTray: { c: '#4a3d33', r: 0.35, l: LAYER.fWood },           // console tray: warm dark striped wood, omaat_f47 #4d3e2e [V]
  fMirror: { c: '#4a545a', r: 0.14, m: 0.5 },                  // w6: dark neutral, about the wood's luminance off-axis (omaat_f5); blue only from reflections (f11) [V]
  lampRing: { c: '#9a9894', r: 0.3, m: 0.9 }, lampLens: { c: '#1b1b1c', r: 0.2 },   // reading spots OFF: chrome ring, dark lens (omaat_f9 / f5)
  fConsoleLow: { c: '#2b2824', r: 0.55, l: LAYER.plastic },   // console body below the taupe fascia, omaat_f7 #1a1a15 [V]
  // w7: olive taupe-grey leaves, R ~ G like the cap (omaat_f60 field #40402f, f7 #423a25 vs the warm #786b57 render); groove
  // only ~0.75x the slat face so the 15-slat field does not alias (w7b) [V hue, D contrast]
  fFlute: { c: '#57554a', r: 0.5, l: LAYER.plastic }, fFluteGap: { c: '#45433a', r: 0.7 },
  fFlank: { c: '#2a221d', r: 0.38, l: LAYER.fWood },          // w7: near-black straight-grain flanks beside the leaves (omaat_f60 flank/field 0.39) [V]
});
function suiteUnit(opts = {}) {
  const B = new Builder();
  const w = opts.w || 1.24, bed = !!opts.bed, lod = !!opts.lod, center = !!opts.center;
  // centre divider height: lowered to the console by default, as in most in-flight photos (omaat_f1 / f3 / f5, tlfl_21);
  // opts.divider = 1 raises it (up_privacy_wall, f_17314)
  const divUp = opts.divider ?? 0;
  // w5: H 1.30 -> 1.24: the rim above the 43 in screen is ~0.05 (omaat_f11 0.044, f32 0.058 scaled by the 0.952 m screen) and the
  // header sits ~0.12 above the seat back (omaat_f9) [D]
  const hx = w / 2, H = 1.24, L = 2.20;
  const shelfW = center ? 0.14 : 0.19;
  const xo = -hx + 0.03;                      // inner face of the outer side
  // w1: seat 34 in incl. side bolsters (thepointsanalyst) -> 0.72 cushion [D]; w2: capped by the room between the console
  // and the armrest so the 1.10 m centre suite (0.63) no longer overlaps its armrest
  const SW = Math.min(0.72, (hx - 0.16) - (xo + shelfW) - 0.14);
  const seatX = xo + shelfW + 0.04 + SW / 2;  // cushion centre
  const xa = hx - 0.16;                       // inner face of the aisle-side wardrobe wall
  // w1: squared flat-topped taupe cap with small edge radii, ~6 mm overhang, top at H + 0.0625 (omaat_f7 / f5, pb_20; the old
  // 0.085 round bullnose read toy-like) [V shape, A size]
  const cap = (cw, cd, x, y, z) => B.add(gRBox(cw + 0.012, 0.06, cd + 0.012, 0.014, 2), M4.trs(x, y + 0.0325, z), SEATMAT.fCap);
  // w2: reading spot (off): black eyeball in a chrome ring, dark lens - no glow in daytime photos (omaat_f9 / f1 / f5 / f46); xf faces +z
  // w3: ~0.075 across (omaat_f9 / f5) [D]
  const spot = (xf) => { B.add(gCyl(0.037, 0.037, 0.02, 16), xf, SEATMAT.fLeather); B.add(gCyl(0.029, 0.029, 0.004, 16), M4.mul(xf, M4.trs(0, 0.011, 0)), SEATMAT.lampRing); B.add(gCyl(0.018, 0.018, 0.004, 14), M4.mul(xf, M4.trs(0, 0.013, 0)), SEATMAT.lampLens); };
  // aft wall (behind the seat) + front wall with the 43 in screen
  B.add(gRBox(w, H, 0.06, 0.02, 1), M4.trs(0, H / 2, -0.07), SEATMAT.fShell);
  cap(w, 0.06, 0, H, -0.07);
  // w7: window suites round the whole outer top corner of the screen wall (r ~0.11) with the taupe rim following the curve down the
  // outer edge; the square shell + cap behind the r 0.08 wood wing still read as a box corner (omaat_f7 / f60 / f11, f_17313) [V shape, D size]
  const rc = center ? -hx - 0.006 : -hx + 0.11;
  if (!center) {
    const cy = H - 0.0725, arc = (R, a0, a1) => Array.from({ length: 9 }, (_, k) => { const a = a0 + (a1 - a0) * k / 8; return [rc + R * Math.cos(a), cy + R * Math.sin(a)]; });
    B.add(gExtrude([[rc + 0.01, 0], [rc + 0.01, cy + 0.10], ...arc(0.10, Math.PI / 2, Math.PI), [rc - 0.10, 0]], 0.12), M4.trs(0, 0, -L + 0.06), SEATMAT.fShell);
    B.add(gExtrude([...arc(0.115, Math.PI / 2, Math.PI), [rc - 0.115, 0.70], [rc - 0.10, 0.70], ...arc(0.10, Math.PI, Math.PI / 2)], 0.132), M4.trs(0, 0, -L + 0.06), SEATMAT.fCap);
    B.add(gRBox(hx - rc, H, 0.12, 0.02, 1), M4.trs((rc + hx) / 2, H / 2, -L + 0.06), SEATMAT.fShell);
  } else B.add(gRBox(w, H, 0.12, 0.02, 1), M4.trs(0, H / 2, -L + 0.06), SEATMAT.fShell);
  B.add(gRBox(hx - rc + 0.006, 0.04, 0.132, 0.012, 2), M4.trs((rc + hx + 0.006) / 2, H + 0.0225, -L + 0.06), SEATMAT.fCap);   // w6: 0.04 screen-wall cap: rim ~0.037 over the screen (omaat_f11 0.036) [D]
  // QA r2 screen wall (omaat_f11 / f7 / f60, f_17300 / 17304): dark straight-grain wood on BOTH sides of the 43 in screen -
  // a ~0.10 wing with a rounded upper outer corner on the window side above the console end, and a ~0.16 pier on the
  // aisle side carrying the reading lamp (outer top corner) and a pill-shaped vanity mirror. Screen edge -> table edge
  // is ~0.07 m on the window side and ~0.16 m on the aisle side in f11 (px scaled by the 0.952 m screen) [D]
  // QA r3: the centre suite (1.07 m between inner faces) cannot fit a 0.10 wing + 0.976 bezel + 0.16 pier; in omaat_f5 /
  // f33 its screen sits against the divider behind a slim taupe edge and the aisle-side pier is narrow [D]
  const wing = center ? 0.0 : 0.10;          // w6: 0.10 wing, 14-17 % of the screen in f11, with the pier steepened to 64 deg [D]
  // w6: centre screens sit right against the board, so the aisle pier gets ~0.19 (omaat_f32 2D pier ~ the screen's height) [D]
  const scx = center ? -hx + 0.014 + 0.488 : xo + wing + 0.488, scy = 0.965;   // w6: screen top 1.2425, just under the wall top
  B.add(gRBox(0.976, 0.555, 0.02, 0.006, 1), M4.trs(scx, scy, -L + 0.13), SEATMAT.bezel);
  B.add(gQuad(0.952, 0.535), M4.trs(scx, scy, -L + 0.141), SEATMAT.screen, atlasUV('screen'));
  // w2: window wing ~0.10 with a well-rounded upper outer corner, small taupe shelf at the console's forward end (omaat_f10 /
  // f47); centre suites: an angled dark-wood fin at the divider end of each screen - the pair forms a V in plan, ~0.28 deep
  // (omaat_f4 1D/1G, f3 2D/2G) [V shape, D size]
  if (!center) {
    // w6: extruded wing outline with an r 0.08 upper outer corner (gRBox clamped its radius to 0.015) (omaat_f11 / f7 / f60) [V shape, D size]
    const wr = 0.08, wp = [[xo + wing - 0.012, 0.68], [xo + wing - 0.012, H]];
    for (let k = 0; k <= 6; k++) { const a = Math.PI / 2 + (k / 6) * Math.PI / 2; wp.push([xo + wr + wr * Math.cos(a), H - wr + wr * Math.sin(a)]); }
    wp.push([xo, 0.68]);
    B.add(gExtrude(wp, 0.03), M4.trs(0, 0, -L + 0.135), SEATMAT.fWood);
    // w5: the console's forward end is a dark-wood plate level with the table, not a floating chip (omaat_f11) [V]
    B.add(gRBox(shelfW, 0.008, 0.24, 0.003, 1), M4.trs(xo + shelfW / 2, 0.667, -L + 0.25), SEATMAT.fShelf);
  } else {
    // w5: ONE thin dark-wood board in the divider plane between the D and G screens (each mirrored unit builds half), from table
    // height to the screen top, ~0.32 deep, with a light taupe edge on its top and aft edges (omaat_f32 2D/2G, f33 1D/1G,
    // tlfl_14 raised) [V shape, D size]; the w4 V-wedge read as a post
    const fy0 = 0.64, fy1 = scy + 0.2775, fz0 = -L + 0.12, fz1 = -L + 0.44;
    B.add(gRBox(0.014, fy1 - fy0, fz1 - fz0, 0.003, 1), M4.trs(-hx + 0.005, (fy0 + fy1) / 2, (fz0 + fz1) / 2), SEATMAT.fWood);
    B.add(gRBox(0.020, 0.02, fz1 - fz0 + 0.01, 0.004, 1), M4.trs(-hx + 0.008, fy1 + 0.01, (fz0 + fz1) / 2 + 0.005), SEATMAT.fCap);   // w6: 0.018 edges (a 1 mm step shimmered); w7: each half 2 mm over the centre plane (seam aliased, w7b)
    B.add(gRBox(0.020, fy1 - fy0 + 0.02, 0.02, 0.004, 1), M4.trs(-hx + 0.008, (fy0 + fy1) / 2 + 0.01, fz1), SEATMAT.fCap);
  }
  // w1: the aisle pier is a wider wood face angled 45 deg (centre 55) toward the seat from the screen edge (omaat_f10: pier 188 px vs
  // screen 610 px; up_forward_look 1D), holding a tall grey-rimmed pill mirror (~0.13 x 0.44, reflective blue-grey #667fa1)
  // and the dome reading lamp at its upper outer corner [D]. All pier parts are placed in the pier's own frame P.
  const pX0 = Math.min(scx + 0.488, hx - 0.07), pAng = (center ? 74 : 64) * DEG, pw = (hx - 0.045 - pX0) / Math.cos(pAng);
  const P = M4.trs(pX0, 0, -L + 0.135, -pAng), pt = (x, y, z, ry = 0, rx = 0) => M4.mul(P, M4.trs(x, y, z, ry, rx));
  B.add(gRBox(pw, H - 0.645, 0.03, 0.01, 1), pt(pw / 2, 0.645 + (H - 0.645) / 2, 0), SEATMAT.fWood);   // w7: from the aisle-box top, not 2 cm into it
  // w2: taupe top closing the open triangle between the angled pier and the screen wall (dark notch from above, w2b)
  const pzE = -L + 0.135 + pw * Math.sin(pAng), pxE = pX0 + pw * Math.cos(pAng);
  B.add(gExtrude([[pX0, L - 0.12], [pxE + 0.015, L - 0.12], [pxE + 0.015, -pzE - 0.015], [pxE, -pzE - 0.015]], 0.02), M4.trs(0, H + 0.01, 0, 0, -Math.PI / 2), SEATMAT.fCap);
  // w7: mirror on the screen side of the pier, lamp alone at the outer top corner (omaat_f11 / f13; the lamp overlapped it, w7b)
  const mW = Math.min(0.13, pw - 0.10), mX = 0.015 + mW / 2;
  B.add(gRBox(mW, 0.44, 0.012, Math.min(0.05, mW / 2 - 0.002), 3), pt(mX, scy, 0.02), SEATMAT.fCap);
  B.add(gRBox(mW - 0.018, 0.422, 0.004, Math.min(0.045, mW / 2 - 0.011), 3), pt(mX, scy, 0.027), SEATMAT.fMirror);
  spot(pt(pw - 0.042, H - 0.09, 0.02, 0, Math.PI / 2));
  // stowed dining table under the screen: dark-wood slab ~0.72 wide (460 / 605 px of the screen width in f11) x 0.20
  // filling the gap between the aisle box and the window console, black front lip (omaat_f11 / f33 / f23) [D]
  const tX0 = xo + shelfW, tX1 = xa - 0.16, tXc = (tX0 + tX1) / 2;
  B.add(gRBox(tX1 - tX0, 0.035, 0.20, 0.008, 1), M4.trs(tXc, 0.645, -L + 0.22), SEATMAT.fShelf);
  B.add(gRBox(tX1 - tX0, 0.03, 0.012, 0.004, 1), M4.trs(tXc, 0.62, -L + 0.325), SEATMAT.black);
  if (!lod) B.add(gRBox(0.05, 0.012, 0.006, 0.003, 1), M4.trs(tXc, 0.62, -L + 0.333), { c: '#b9b6b0', r: 0.35, m: 0.8 });   // PULL tab
  // aisle box beside the ottoman, its top level with the table (f11: box top at the table top) [D]
  const bX0 = xa - 0.16, bX1 = hx - 0.04;
  B.add(gRBox(bX1 - bX0, 0.62, 0.36, 0.015, 1), M4.trs((bX0 + bX1) / 2, 0.31, -L + 0.30), SEATMAT.fInner);
  B.add(gRBox(bX1 - bX0 + 0.01, 0.02, 0.37, 0.008, 1), M4.trs((bX0 + bX1) / 2, 0.63, -L + 0.30), SEATMAT.fConsole);
  if (!lod) B.add(gRBox(0.06, 0.012, 0.025, 0.004, 1), M4.trs(bX0 + 0.05, 0.635, -L + 0.47), SEATMAT.black);   // w5: lid latch (omaat_f11) [V]
  // ottoman (padded, same tweed as the seat) with belt
  const ow = xa - xo - 0.19;
  const ox = xo + ow / 2 + 0.005;
  // w1: cantilevered bench - cushion on a thin taupe tray + front rail, open dark void to a low plinth (omaat_f10, up_empty,
  // pb_30) [V shape, A size]
  B.add(gRBox(ow, 0.05, 0.52, 0.01, 1), M4.trs(ox, 0.335, -L + 0.39), SEATMAT.fInner);
  B.add(gRBox(ow + 0.01, 0.035, 0.025, 0.008, 1), M4.trs(ox, 0.33, -L + 0.645), SEATMAT.fConsole);
  B.add(gRBox(ow, 0.05, 0.40, 0.008, 1), M4.trs(ox, 0.025, -L + 0.33), SEATMAT.fInner);
  B.add(gBox(ow, 0.28, 0.01), M4.trs(ox, 0.19, -L + 0.135), SEATMAT.fConsoleLow);
  B.add(gLoft(cushionSecs(ow - 0.01, 0.52, 0.08, -0.04, { edge: 0.025, r: 0.025 }), 3), M4.trs(ox, 0.40, -L + 0.39), SEATMAT.fFabric);
  if (!lod) for (const s of [-1, 1]) B.add(gBox(0.04, 0.004, 0.2), M4.trs(ox + 0.12 * s, 0.443, -L + 0.42), SEATMAT.strap);
  // outer side: low skirt (window) or full-height partition half (centre), plus the long console
  if (center) {
    // centre divider: a large dark straight-grain wood face above the console in a taupe edge frame, taupe cap
    // (f_17314, tpa_IMG_0220 #24262d-#705850)
    const DH = 0.70 + divUp * (H - 0.70);        // divider top (0.70 lowered: its rail just above the console, omaat_f5)
    B.add(gRBox(0.03, DH, L - 0.14, 0.01, 1), M4.trs(-hx + 0.015, DH / 2, -L / 2), SEATMAT.fDoor);
    if (DH > 0.75) {
      B.add(gRBox(0.006, DH - 0.70, L - 0.34, 0.004, 1), M4.trs(-hx + 0.033, 0.68 + (DH - 0.70) / 2, -L / 2 - 0.04), SEATMAT.fWood);
      for (const z of [-L + 0.44, -0.19]) B.add(gRBox(0.008, DH - 0.70, 0.03, 0.003, 1), M4.trs(-hx + 0.034, 0.68 + (DH - 0.70) / 2, z), SEATMAT.fShell);
    }
    // QA r3: a thin taupe top rail with a small raise/lower tab at mid-length, not the wall bullnose (up_Privacy-Wall,
    // tpa_IMG_0220, f_17314 round tab) [V shape, A size]
    B.add(gRBox(0.035, 0.022, L - 0.14, 0.006, 1), M4.trs(-hx + 0.015, DH + 0.011, -L / 2), SEATMAT.fDoor);
    if (DH <= 0.75) B.add(gRBox(0.034, 0.04, L - 0.16, 0.004, 1), M4.trs(-hx + 0.015, DH - 0.03, -L / 2), SEATMAT.fWood);   // w5: dark-wood band under the rail (omaat_f5) [V]
    B.add(gRBox(0.012, 0.035, 0.07, 0.006, 1), M4.trs(-hx + 0.035, DH - 0.01, -L / 2), SEATMAT.fCap);
  } else B.add(gRBox(0.03, 0.70, L - 0.14, 0.01, 1), M4.trs(-hx + 0.015, 0.35, -L / 2), SEATMAT.fShell);
  // w1: taupe fascia band (~0.16) over a near-black body with a bin-door seam, trim line and long floor grille (omaat_f7,
  // up_empty, up_privacy_wall) [V]
  B.add(gRBox(shelfW, 0.16, L - 0.30, 0.02, 1), M4.trs(xo + shelfW / 2, 0.56, -L / 2 - 0.04), SEATMAT.fConsole);
  B.add(gRBox(shelfW - 0.01, 0.48, L - 0.30, 0.01, 1), M4.trs(xo + shelfW / 2 - 0.005, 0.24, -L / 2 - 0.04), SEATMAT.fConsoleLow);
  B.add(gRBox(shelfW + 0.01, 0.025, L - 0.30, 0.008, 1), M4.trs(xo + shelfW / 2, 0.652, -L / 2 - 0.04), SEATMAT.fShell);
  // QA r3: tapered dark-wood insert (0.14 forward -> 0.09 aft, outer edge straight) in a shallow black-rimmed recess of the
  // console top, forward of the keypad (f_17313 / up_Privacy-Wall / omaat_f58) [D shape from photos, A size]
  const trayXf = M4.trs(xo + 0.025, 0.6655, -0.92, 0, -Math.PI / 2);
  B.add(gExtrude([[-0.006, -0.006], [0.10, -0.006], [0.151, 0.806], [-0.006, 0.806]], 0.004), trayXf, SEATMAT.black);
  B.add(gExtrude([[0, 0], [0.09, 0], [0.14, 0.80], [0, 0.80]], 0.006), M4.mul(M4.trs(0, 0, 0.0015), trayXf), SEATMAT.fTray);
  if (!lod) {
    // QA r2: handset AFT (nearest the seat), keypad directly FORWARD of it on a raised section (up_Privacy-Wall, omaat_f5 /
    // f7). Keypad: light warm-grey panel ~0.12 x 0.13 (#8a8882) with white LINE icons - 3 pill buttons, 3 +/- pairs,
    // 4 icons (omaat_f14) [D]. QA r3: the raised section is a wedge tilted ~12 deg toward the seat (f_17313 / 17314) [A angle]
    // w7: keypad + handset sit on ONE raised aft module ~0.50 long, stepped up ~0.04 over the trough top, with a narrow
    // window-side ledge (the menu card stands on it) (omaat_f57 / f58 / f7, f_17313) [V shape, A size]
    const kx = xo + shelfW / 2, kz = -0.80, ky = 0.681, mdy = 0.04;
    B.add(gRBox(shelfW - 0.035, 0.05, 0.52, 0.012, 2), M4.trs(xo + shelfW / 2 + 0.0175, 0.69, -0.68), SEATMAT.fConsole);
    B.add(gRBox(0.035, 0.075, 0.70, 0.01, 2), M4.trs(xo + 0.0175, 0.70, -0.62), SEATMAT.fConsole);
    const K = M4.trs(kx, 0.678 + mdy, kz, 0, 0, -12 * DEG), kt = (x, y, z, ry = 0, rx = 0) => M4.mul(K, M4.trs(x - kx, y - 0.678, z - kz, ry, rx));
    const flat = (x, y, z) => kt(x, y, z, 0, -Math.PI / 2), glyph = { c: '#d8d8d6', r: 0.4 };   // w7: no glow (white icons on a dark tile, omaat_f57)
    B.add(gRBox(0.13, 0.03, 0.15, 0.006, 1), kt(kx, 0.663, kz), SEATMAT.fConsole);
    B.add(gRBox(0.12, 0.006, 0.13, 0.006, 1), kt(kx, ky - 0.003, kz), { c: '#4a4642', r: 0.6 }   /* w7: a shade darker than the console (omaat_f58 keypad L96 vs console L119; w6 still rendered 1.4x) [V] */);
    // rows run across the console (x), stacked along z; outlines drawn as thin light strokes
    const ring = (x, z, w, d) => { for (const s of [-1, 1]) { B.add(gQuad(w, 0.0015), flat(x, ky + 0.0005, z + s * d / 2), glyph); B.add(gQuad(0.0015, d), flat(x + s * w / 2, ky + 0.0005, z), glyph); } };
    for (let c = 0; c < 3; c++) ring(kx + (c - 1) * 0.034, kz - 0.045, 0.024, 0.010);                     // pill buttons
    for (let c = 0; c < 3; c++) for (const dz of [-0.008, 0.012]) {                                      // - / + pairs
      B.add(gQuad(0.008, 0.0015), flat(kx + (c - 1) * 0.034, ky + 0.0005, kz + dz), glyph);
      if (dz > 0) B.add(gQuad(0.0015, 0.008), flat(kx + (c - 1) * 0.034, ky + 0.0005, kz + dz), glyph);
    }
    for (let c = 0; c < 4; c++) ring(kx + (c - 1.5) * 0.026, kz + 0.045, 0.010, 0.010);                 // icons
    // handset: black landscape controller with rounded ends lying along the console, colour screen + a D-pad at each
    // end (omaat_f15 / f5: ~0.20 x 0.075 m, screen ~0.09 x 0.05) [D]
    const hz = -0.60;
    // QA r3: it lies in a taupe dock tilted like the keypad (f_17313 / 17314)
    const Hs = M4.trs(kx, 0.678 + mdy, hz, 0, 0, -12 * DEG);
    B.add(gRBox(0.10, 0.03, 0.23, 0.008, 1), M4.mul(Hs, M4.trs(0, -0.015, 0)), SEATMAT.fConsole);
    B.add(gRBox(0.075, 0.014, 0.20, 0.03, 3), M4.mul(Hs, M4.trs(0, 0.004, 0)), { c: '#101112', r: 0.3 });
    B.add(gQuad(0.05, 0.09), M4.mul(Hs, M4.trs(0, 0.0115, 0, 0, -Math.PI / 2)), { c: '#3a6fb8', r: 0.2, e: 0.35 });
    for (const dz of [-0.075, 0.075]) B.add(gCyl(0.01, 0.01, 0.003, 12), M4.mul(Hs, M4.trs(0, 0.012, dz)), { c: '#26282b', r: 0.35 });
    // (no outlets pocket on the face: HDMI / USB sit inside the console bin, omaat_f16 / pb_32)
    B.add(gBox(0.004, 0.12, 1.2), M4.trs(xo + shelfW - 0.004, 0.10, -1.10), { c: '#121210', r: 0.8, l: LAYER.grille }); // air grille
    B.add(gBox(0.003, 0.004, 0.9), M4.trs(xo + shelfW - 0.009, 0.45, -1.00), SEATMAT.black);                            // bin-door seam
    B.add(gBox(0.004, 0.012, L - 0.30), M4.trs(xo + shelfW + 0.002, 0.63, -L / 2 - 0.04), { c: '#3b2f26', r: 0.5 });     // trim line
  }
  // aisle side: thick wardrobe wall beside the seat. Its inner face is dark wood with ONE taupe-framed door (safety card
  // / mirror behind it) above the lit literature pocket (omaat_f2 / f5 / f35 / f36); coat hook
  B.add(gRBox(0.16, H, 0.86, 0.02, 1), M4.trs(hx - 0.08, H / 2, -0.53), SEATMAT.fShell);
  cap(0.16, 0.86, hx - 0.08, H, -0.53);
  B.add(gRBox(0.006, H - 0.20, 0.80, 0.004, 1), M4.trs(xa - 0.003, 0.10 + (H - 0.20) / 2, -0.53), SEATMAT.fWood);
  B.add(gRBox(0.014, 0.54, 0.30, 0.012, 1), M4.trs(xa - 0.008, 0.89, -0.62), SEATMAT.fShell);          // w6: door frame ~0.30 x 0.54 (omaat_f13 / f5) [D]
  B.add(gRBox(0.004, 0.48, 0.24, 0.004, 1), M4.trs(xa - 0.016, 0.89, -0.62), SEATMAT.fWood);           // closed door: wood face (f35)
  if (!lod) B.add(gBox(0.003, 0.03, 0.20), M4.trs(xa - 0.0165, 0.675, -0.62), { c: '#cfcac2', r: 0.6 }); // safety label strip
  if (!lod) B.add(gRBox(0.012, 0.07, 0.03, 0.004, 1), M4.trs(xa - 0.008, 0.89, -0.785), SEATMAT.fCap);  // w6: taupe pull at the door's forward edge (omaat_f13) [V]
  if (!lod) {
    // coat hook rail forward of the niche jamb (w2: it was half buried in the jamb); the literature pocket is the armrest's
    // (the separate lit niche poked out between armrest and jamb as a white notch, w2b)
    B.add(gRBox(0.02, 0.018, 0.10, 0.006, 1), M4.trs(xa - 0.01, 1.16, -0.32), SEATMAT.frame);
  }
  // front aisle corner: the aisle box (above) + a thin outer wall holding the parked door, open between it and the
  // pier above the box (f11: taupe side wall left of the pier)
  B.add(gRBox(0.04, H, 0.50, 0.012, 1), M4.trs(hx - 0.02, H / 2, -L + 0.35), SEATMAT.fShell);
  // w2: the forward aisle corner carries a thick rounded taupe hood cantilevered over the aisle and the pier, one smooth
  // rounded prow (w2: a separate down-turned lip read as a knob) (omaat_f4 both aisles, f47 from inside) [V shape, A size]
  // w3: ONE flat-topped arm replacing the corner cap - top flush with the other caps, 0.16 wide (flush with the wardrobe inner
  // face), running aft over the parked leaf and 0.03 forward past the screen wall, with a thick rounded underside (w3b: the
  // separate box read as a bolster)
  // w5: square, flush inboard part + a rounded prow only on the aisle side (from the seat the round arm read as a bolster)
  B.add(gRBox(0.09, 0.06, 0.66, 0.012, 2), M4.trs(hx - 0.084, H + 0.0325, -L + 0.30), SEATMAT.fCap);
  B.add(gRBox(0.06, 0.09, 0.66, 0.035, 3), M4.trs(hx - 0.024, H + 0.0175, -L + 0.30), SEATMAT.fCap);
  // aisle-facing exterior (w1): two EQUAL 0.50 m sliding leaves parked at either end of a ~0.64 m opening (omaat_f7 /
  // up_empty ~1.3 leaf). w6: each leaf runs from 0.10 up to just under the cap, a same-tone frame (0.035 rails, 0.055 outer /
  // 0.026 meeting stiles) round broad FLAT slats with narrow dark grooves (omaat_f60 closed: ~30 % groove, frame ~1.15x the
  // field); the flanks a leaf uncovers are dark wood (omaat_f60 both ends) [V]
  // wave 2: opts.doors = 1 closes the suite - the two leaves slide together and meet mid-opening, ~8 mm proud of the flanks
  // (omaat_f60); geometry only, the seat-card toggle is the integrator's [V]
  const doorsShut = !!opts.doors, zo0 = -L + 0.60, zo1 = -0.96, zm = (zo0 + zo1) / 2;
  if (doorsShut) B.add(gBox(0.03, H - 0.24, zo1 - zo0), M4.trs(hx - 0.02, 0.14 + (H - 0.24) / 2, zm), SEATMAT.fShell);   // leaf inner face (taupe) [A]
  if (!lod) {
    const ly0 = 0.10, ly1 = H - 0.015, lh = ly1 - ly0, yc = (ly0 + ly1) / 2;
    // [z0, z1, meeting edge (-1 front, 1 aft), proud offset]
    const leaves = doorsShut ? [[zm - 0.50, zm, 1, 0.008], [zm, zm + 0.50, -1, 0.008]] : [[-L + 0.10, -L + 0.60, 1, 0], [-0.96, -0.46, -1, 0]];
    const flanks = doorsShut ? [[-L + 0.10, zm - 0.50], [zm + 0.50, -0.08]] : [[-0.46, -0.08]];
    for (const [z0, z1, me, dx] of leaves) {
      const len = z1 - z0, x = hx + dx, w0 = me > 0 ? 0.055 : 0.026, w1 = me > 0 ? 0.026 : 0.055;
      B.add(gBox(0.004, lh - 0.06, len - 0.06), M4.trs(x + 0.002, yc, (z0 + z1) / 2), SEATMAT.fFluteGap);
      // w3: pitch 0.026 (15 per leaf, real ~23) - finer slats alias to moire at cabin distance [A, deliberate]
      for (let z = z0 + w0 + 0.016; z < z1 - w1 - 0.008; z += 0.026) B.add(gBox(0.005, lh - 0.07, 0.020), M4.trs(x + 0.0045, yc, z), SEATMAT.fFlute);
      B.add(gRBox(0.016, lh, w0, 0.006, 1), M4.trs(x + 0.007, yc, z0 + w0 / 2), SEATMAT.fDoorFrame);
      B.add(gRBox(0.016, lh, w1, 0.006, 1), M4.trs(x + 0.007, yc, z1 - w1 / 2), SEATMAT.fDoorFrame);
      for (const y of [ly0 + 0.0175, ly1 - 0.0175]) B.add(gRBox(0.016, 0.035, len, 0.006, 1), M4.trs(x + 0.007, y, (z0 + z1) / 2), SEATMAT.fDoorFrame);
      B.add(gBox(0.006, 0.008, len - 0.02), M4.trs(hx + 0.004, 0.06, (z0 + z1) / 2), SEATMAT.fLed);
      // recessed body-colour pull with a dark pocket at the meeting edge, ~0.55 up (omaat_f60) [V]
      const pz = me > 0 ? z1 - 0.04 : z0 + 0.04;
      B.add(gRBox(0.010, 0.08, 0.022, 0.004, 1), M4.trs(x + 0.017, 0.55, pz), SEATMAT.fDoorFrame);
      B.add(gBox(0.004, 0.06, 0.014), M4.trs(x + 0.021, 0.55, pz), SEATMAT.black);
      B.add(gBox(0.003, 0.007, 0.007), M4.trs(x + 0.0165, ly1 - 0.06, me > 0 ? z0 + 0.028 : z1 - 0.028), { c: '#ff2a1a', r: 0.4, e: 0.8 });   // w7: red status LED, top outer corner (omaat_f60) [V]
    }
    for (const [z0, z1] of flanks) {
      B.add(gBox(0.004, H - 0.115, z1 - z0), M4.trs(hx + 0.002, 0.10 + (H - 0.115) / 2, (z0 + z1) / 2), SEATMAT.fFlank);
      B.add(gBox(0.006, 0.008, z1 - z0 - 0.02), M4.trs(hx + 0.004, 0.06, (z0 + z1) / 2), SEATMAT.fLed);
    }
  }
  // the seat: upholstered base, thin cushion, flat back leaning on the aft wall, slate headrest flap (f_17302 / 17309)
  const S = M4.trs(seatX, 0, -0.14);
  const F = SEATMAT.fFabric;
  B.add(gRBox(SW, 0.34, 0.62, 0.02, 1), M4.mul(S, M4.trs(0, 0.17, -0.36)), F);
  // solid taupe box armrest beside the wardrobe, flat taupe top at ~0.62, literature pocket in its inner face
  // (omaat_f13 both seats, omaat_f5 / f2) [D]
  const ax = xa - seatX - 0.05;               // armrest centre (local), against the wardrobe
  // w5: dark-wood body under a slim rounded taupe pad that overhangs forward (omaat_f9 / f57) [V shape, A size]
  B.add(gRBox(0.10, 0.62, 0.62, 0.02, 1), M4.mul(S, M4.trs(ax, 0.31, -0.40)), SEATMAT.fWood);
  B.add(gRBox(0.085, 0.05, 0.66, 0.024, 3), M4.mul(S, M4.trs(ax, 0.645, -0.41)), SEATMAT.fCap);
  if (!lod) B.add(gRBox(0.006, 0.16, 0.26, 0.004, 1), M4.mul(S, M4.trs(ax - 0.051, 0.45, -0.40)), SEATMAT.fInner);
  // w1: the seat back stands in a sculpted taupe niche - side jambs ~0.10 and a ~0.10 header on the aft wall - with the two
  // black dome reading lamps in the header corners, facing forward (omaat_f5 / f9 / f1) [V shape, D size]
  for (const s of [-1, 1]) B.add(gRBox(0.10, H - 0.66, 0.12, 0.025, 2), M4.trs(seatX + s * (SW / 2 + 0.05), 0.66 + (H - 0.66) / 2, -0.16), SEATMAT.fConsole);
  // w3: niche 1.17x the back (omaat_f9); w7: 0.09 header (clears the 1.14 back top) with r 0.035 inner fillets round the opening
  // (omaat_f9 / f57: thick header, rounded corners carrying the lamps) [V shape, D size]
  B.add(gRBox(SW + 0.20, 0.09, 0.12, 0.025, 2), M4.trs(seatX, H - 0.045, -0.16), SEATMAT.fConsole);
  for (const s of [-1, 1]) {
    const fx = seatX + s * SW / 2, fr = 0.035, fp = [[fx, H - 0.09], [fx, H - 0.09 - fr]];
    for (let k = 0; k <= 5; k++) { const a = Math.PI / 2 * k / 5; fp.push([fx - s * fr * (1 - Math.cos(a)), H - 0.09 - fr + fr * Math.sin(a)]); }
    B.add(gExtrude(s > 0 ? fp : fp.slice().reverse(), 0.06), M4.trs(0, 0, -0.13), SEATMAT.fConsole);
  }
  for (const s of [-1, 1]) spot(M4.trs(seatX + s * (SW / 2 + 0.01), H - 0.045, -0.225, 0, -Math.PI / 2));
  if (bed) {
    // w5: white pad narrower than the tweed bed and offset to the window side, so a ~0.10 tweed margin and the black belt show on
    // the aisle side (omaat_f57) [V]
    B.add(gRBox(SW, 0.05, 1.96, 0.015, 1), M4.trs(seatX - 0.01, 0.405, -1.08), SEATMAT.fFabric);
    B.add(gLoft(cushionSecs(SW - 0.10, 1.96, 0.06, -0.03, { edge: 0.03, r: 0.035, crown: 0.004 }), 3), M4.trs(seatX - 0.06, 0.44, -1.08), { c: '#f0efea', r: 0.9, l: LAYER.fabric });
    B.add(gRBox(ow, 0.44, 0.9, 0.03, 1), M4.trs(ox, 0.22, -1.40), SEATMAT.fInner);
    // w6: duvet across the whole pad over the foot half, draping onto the tweed margin on the aisle side (omaat_f57 / f58 / f59)
    // [V shape, A size]; w7: lofted (~0.065 + crown, soft 0.06 edges), a shade greyer than the pad, the full bed width with a 0.14 drape over the
    // aisle edge, a folded-back band at its head end and soft diagonal creases - the w6 slab vanished white-on-white (w7a);
    // the seat belt lies across the bare pad between the pillows and the fold (omaat_f57) [V]
    const duv = { c: '#dcd8d0', r: 0.95, l: LAYER.fabric }, dw = SW, dx = seatX - 0.01, xe = dx + dw / 2, dz0 = -0.92, dl = 1.14;
    B.add(gLoft(cushionSecs(dw, dl, 0.065, -0.03, { edge: 0.06, r: 0.06, crown: 0.045 }), 3), M4.trs(dx, 0.50, dz0 - dl / 2), duv);
    if (!lod) {
      B.add(gRBox(dw - 0.02, 0.03, 0.20, 0.012, 2), M4.trs(dx, 0.575, dz0 - 0.11, 4 * DEG), { c: '#ece9e3', r: 0.95, l: LAYER.fabric });   // fold-back band
      B.add(gRBox(0.014, 0.15, dl - 0.06, 0.006, 1), M4.trs(xe + 0.005, 0.445, dz0 - dl / 2), duv);                                         // aisle drape
      for (const [cz, cy] of [[-1.30, 25], [-1.55, -20], [-1.80, 30]]) B.add(gRBox(dw * 0.55, 0.012, 0.022, 0.005, 1), M4.trs(dx + 0.04, 0.582, cz, cy * DEG), { c: '#cfcbc3', r: 0.95, l: LAYER.fabric });
      const bz = -0.80, bx = seatX + SW / 2 - 0.21, ba = 25 * DEG;
      for (const sg of [-1, 1]) B.add(gBox(0.035, 0.004, 0.16), M4.trs(bx + sg * 0.09 * Math.cos(ba), 0.476, bz - sg * 0.09 * Math.sin(ba), Math.PI / 2 + ba), SEATMAT.black);
      B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.trs(bx, 0.48, bz), SEATMAT.buckle);
    }
    // w2: pillows propped up against the aft niche, lavender in front (omaat_f46, up_bed_made) [V]
    B.add(gLoft(cushionSecs(0.5, 0.32, 0.13, -0.065, { edge: 0.05, r: 0.05 }), 3), M4.trs(seatX, 0.66, -0.29, 0, -60 * DEG), SEATMAT.pillow);
    B.add(gLoft(cushionSecs(0.44, 0.28, 0.10, -0.05, { edge: 0.04, r: 0.045 }), 3), M4.trs(seatX + 0.04, 0.53, -0.52, 0, -15 * DEG), SEATMAT.fCushionBlue);
  } else {
    B.add(gLoft(cushionSecs(SW, 0.62, 0.075, -0.035, { edge: 0.022, r: 0.02, crown: 0.004 }), lod ? 3 : 4), M4.mul(S, M4.trs(0, 0.375, -0.36, 0, 2 * DEG)), F);
    // w1: taller, nearly upright back - top ~1.14 m, 5 deg (omaat_f5 level view) [D]
    const BH = M4.mul(S, M4.trs(0, 0.42, -0.12, 0, 5 * DEG));
    loftAt(B, [SEC(0.0, SW - 0.02, 0.06, 0, 0.02), SEC(0.025, SW, 0.08, 0, 0.028), SEC(0.70, SW, 0.08, 0, 0.028), SEC(0.725, SW - 0.02, 0.06, 0.002, 0.02)], BH, F, lod ? 2 : 3);
    // flap ~77 % of the back width (w6: SW * 0.78 so the centre seat keeps the ratio), hung from the very top edge and wrapping over it (w2: omaat_f9 / f1 / f5 / f8)
    B.add(gRBox(SW * 0.78, 0.20, 0.012, 0.006, 1), M4.mul(BH, M4.trs(0, 0.625, -0.044)), SEATMAT.fFlap);
    B.add(gRBox(SW * 0.78, 0.014, 0.075, 0.006, 1), M4.mul(BH, M4.trs(0, 0.727, -0.006)), SEATMAT.fFlap);
    if (!lod) {
      // w5: three channel seams (omaat_f9); w7: dark creases, not light hairlines (w7b)
      for (const y of [0.18, 0.36, 0.54]) B.add(gBox(SW - 0.04, 0.007, 0.004), M4.mul(BH, M4.trs(0, y, -0.041)), { c: '#3f3a36', r: 0.95 });
      B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.mul(S, M4.trs(0, 0.418, -0.40)), SEATMAT.buckle);
    }
    // w2: plump pillow tapering to thin edges (omaat_f9 / f5), not a slab
    B.add(gLoft([SEC(0, 0.43, 0.025, 0, 0.012), SEC(0.02, 0.445, 0.07, 0, 0.02), SEC(0.07, 0.45, 0.115, 0, 0.02), SEC(0.15, 0.45, 0.13, 0, 0.02), SEC(0.23, 0.45, 0.115, 0, 0.02), SEC(0.28, 0.445, 0.07, 0, 0.02), SEC(0.30, 0.43, 0.025, 0, 0.012)], 4), M4.mul(BH, M4.trs(-0.08, 0.05, -0.11, 0.25, 6 * DEG)), SEATMAT.fCushionBlue);
    // w1: leg rest flush with the base front (-0.67 local), one seam, no protruding plate (omaat_f9 / f5)
    B.add(gLoft([SEC(0.0, SW - 0.02, 0.05, 0, 0.02), SEC(0.30, SW - 0.01, 0.055, 0, 0.022)], 3), M4.mul(S, M4.trs(0, 0.04, -0.68, 0, -3 * DEG)), F);
  }
  return B.build();
}
function suiteFar(opts = {}) {
  // w7: far LOD matched to the near unit (lowered centre divider, screen position, caps, fluted leaves as flat panels, wood
  // flank) so suites no longer change shape at the LOD switch (w7b)
  const B = new Builder();
  const w = opts.w || 1.24, hx = w / 2, H = 1.24, L = 2.20, c = !!opts.center, DH = c ? 0.70 + (opts.divider ?? 0) * (H - 0.70) : 0.70;
  B.add(gBox(w, H, 0.06), M4.trs(0, H / 2, -0.07), SEATMAT.fShell);
  B.add(gBox(w, H, 0.12), M4.trs(0, H / 2, -L + 0.06), SEATMAT.fShell);
  B.add(gBox(0.16, H, 0.86), M4.trs(hx - 0.08, H / 2, -0.53), SEATMAT.fShell);
  B.add(gBox(0.04, H, 0.50), M4.trs(hx - 0.02, H / 2, -L + 0.35), SEATMAT.fShell);
  for (const [cw, cx, cz, cd] of [[w, 0, -L + 0.06, 0.13], [w, 0, -0.07, 0.07], [0.17, hx - 0.08, -0.53, 0.87], [0.17, hx - 0.08, -L + 0.30, 0.66]]) B.add(gBox(cw, 0.05, cd), M4.trs(cx, H + 0.025, cz), SEATMAT.fCap);
  B.add(gBox(0.03, DH, L), M4.trs(-hx + 0.015, DH / 2, -L / 2), c ? SEATMAT.fDoor : SEATMAT.fShell);
  B.add(gBox(0.19, 0.66, L - 0.30), M4.trs(-hx + 0.125, 0.33, -L / 2 - 0.04), SEATMAT.fConsole);
  B.add(gRBox(0.66, 0.5, 0.7, 0.04, 1), M4.trs(-hx + 0.6, 0.25, -0.45), SEATMAT.fFabric);
  B.add(gBox(0.66, 0.72, 0.08), M4.trs(-hx + 0.6, 0.78, -0.24), SEATMAT.fFabric);
  for (const [z0, z1] of [[-L + 0.10, -L + 0.60], [-0.96, -0.46]]) B.add(gBox(0.008, H - 0.115, z1 - z0), M4.trs(hx + 0.004, 0.10 + (H - 0.115) / 2, (z0 + z1) / 2), SEATMAT.fFlute);
  B.add(gBox(0.006, H - 0.115, 0.38), M4.trs(hx + 0.003, 0.10 + (H - 0.115) / 2, -0.27), SEATMAT.fFlank);
  const scx = c ? -hx + 0.502 : -hx + 0.618;
  B.add(gQuad(0.952, 0.535), M4.trs(scx, 0.965, -L + 0.141), SEATMAT.screen, atlasUV('screen'));
  return B.build();
}
