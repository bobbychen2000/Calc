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
  fDoorFrame: { c: '#655d53', r: 0.5, l: LAYER.plastic },     // w2: between pb_20 (night, #423631) and omaat_f4 (cabin light, ~rib crest tone) [V]
  fTray: { c: '#4a3d33', r: 0.35, l: LAYER.fWood },           // console tray: warm dark striped wood, omaat_f47 #4d3e2e [V]
  fMirror: { c: '#8593a8', r: 0.18, m: 0.25 },                 // pill mirror reflecting wood + cabin, omaat_f10 #5b6680 [V]
  lampRing: { c: '#9a9894', r: 0.3, m: 0.9 }, lampLens: { c: '#1b1b1c', r: 0.2 },   // reading spots OFF: chrome ring, dark lens (omaat_f9 / f5)
  fConsoleLow: { c: '#2b2824', r: 0.55, l: LAYER.plastic },   // console body below the taupe fascia, omaat_f7 #1a1a15 [V]
});
function suiteUnit(opts = {}) {
  const B = new Builder();
  const w = opts.w || 1.24, bed = !!opts.bed, lod = !!opts.lod, center = !!opts.center;
  // centre divider height: lowered to the console by default, as in most in-flight photos (omaat_f1 / f3 / f5, tlfl_21);
  // opts.divider = 1 raises it (up_privacy_wall, f_17314)
  const divUp = opts.divider ?? 0;
  const hx = w / 2, H = 1.30, L = 2.20;
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
  B.add(gRBox(w, H, 0.12, 0.02, 1), M4.trs(0, H / 2, -L + 0.06), SEATMAT.fShell);
  cap(w, 0.12, 0, H, -L + 0.06);
  // QA r2 screen wall (omaat_f11 / f7 / f60, f_17300 / 17304): dark straight-grain wood on BOTH sides of the 43 in screen -
  // a ~0.10 wing with a rounded upper outer corner on the window side above the console end, and a ~0.16 pier on the
  // aisle side carrying the reading lamp (outer top corner) and a pill-shaped vanity mirror. Screen edge -> table edge
  // is ~0.07 m on the window side and ~0.16 m on the aisle side in f11 (px scaled by the 0.952 m screen) [D]
  // QA r3: the centre suite (1.07 m between inner faces) cannot fit a 0.10 wing + 0.976 bezel + 0.16 pier; in omaat_f5 /
  // f33 its screen sits against the divider behind a slim taupe edge and the aisle-side pier is narrow [D]
  const wing = center ? 0.0 : 0.08;          // w3: 0.08 wing so the 60-deg pier reaches ~0.22 (omaat_f10 pier ~0.28, 1.24 m suite)          // w1: 0.08 window wing (omaat_f10 ~0.14 incl. its curve) leaves room for the pier
  const scx = xo + wing + 0.488;
  B.add(gRBox(0.976, 0.555, 0.02, 0.006, 1), M4.trs(scx, 0.95, -L + 0.13), SEATMAT.bezel);
  B.add(gQuad(0.952, 0.535), M4.trs(scx, 0.95, -L + 0.141), SEATMAT.screen, atlasUV('screen'));
  // w2: window wing ~0.10 with a well-rounded upper outer corner, small taupe shelf at the console's forward end (omaat_f10 /
  // f47); centre suites: an angled dark-wood fin at the divider end of each screen - the pair forms a V in plan, ~0.28 deep
  // (omaat_f4 1D/1G, f3 2D/2G) [V shape, D size]
  if (!center) {
    B.add(gRBox(wing - 0.012, H - 0.68, 0.03, 0.033, 3), M4.trs(xo + wing / 2, 0.68 + (H - 0.68) / 2, -L + 0.135), SEATMAT.fWood);
    B.add(gRBox(0.12, 0.02, 0.14, 0.008, 1), M4.trs(xo + 0.06, 0.70, -L + 0.19), SEATMAT.fCap);
  } else {
    // w4: a SOLID half-wedge from the divider plane to an 18-deg face; with the mirrored neighbour the pair is one dark-wood
    // wedge opening aft (w3b: an X; w4b: two thin boards read as open cabinet doors)
    const fz = 0.27, fx = fz * Math.tan(18 * DEG) + 0.012;
    B.add(gExtrude([[-hx, L - 0.12], [-hx + 0.012, L - 0.12], [-hx + fx, L - 0.12 - fz], [-hx, L - 0.12 - fz]], H - 0.62), M4.trs(0, 0.62 + (H - 0.62) / 2, 0, 0, -Math.PI / 2), SEATMAT.fWood);
  }
  // w1: the aisle pier is a wider wood face angled 45 deg (centre 55) toward the seat from the screen edge (omaat_f10: pier 188 px vs
  // screen 610 px; up_forward_look 1D), holding a tall grey-rimmed pill mirror (~0.13 x 0.44, reflective blue-grey #667fa1)
  // and the dome reading lamp at its upper outer corner [D]. All pier parts are placed in the pier's own frame P.
  const pX0 = Math.min(scx + 0.488, hx - 0.07), pAng = (center ? 55 : 60) * DEG, pw = (hx - 0.045 - pX0) / Math.cos(pAng);
  const P = M4.trs(pX0, 0, -L + 0.135, -pAng), pt = (x, y, z, ry = 0, rx = 0) => M4.mul(P, M4.trs(x, y, z, ry, rx));
  B.add(gRBox(pw, H - 0.62, 0.03, 0.01, 1), pt(pw / 2, 0.62 + (H - 0.62) / 2, 0), SEATMAT.fWood);
  // w2: taupe top closing the open triangle between the angled pier and the screen wall (dark notch from above, w2b)
  const pzE = -L + 0.135 + pw * Math.sin(pAng), pxE = pX0 + pw * Math.cos(pAng);
  B.add(gExtrude([[pX0, L - 0.12], [pxE + 0.015, L - 0.12], [pxE + 0.015, -pzE - 0.015], [pxE, -pzE - 0.015]], 0.02), M4.trs(0, H + 0.01, 0, 0, -Math.PI / 2), SEATMAT.fCap);
  const mW = Math.min(0.13, pw - 0.05), mX = pw / 2 - 0.005;
  B.add(gRBox(mW, 0.44, 0.012, Math.min(0.05, mW / 2 - 0.002), 3), pt(mX, 0.95, 0.02), SEATMAT.fCap);
  B.add(gRBox(mW - 0.018, 0.422, 0.004, Math.min(0.045, mW / 2 - 0.011), 3), pt(mX, 0.95, 0.027), SEATMAT.fMirror);
  spot(pt(Math.max(0.03, pw - 0.035), 1.20, 0.02, 0, Math.PI / 2));
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
      for (const z of [-L + 0.17, -0.19]) B.add(gRBox(0.008, DH - 0.70, 0.03, 0.003, 1), M4.trs(-hx + 0.034, 0.68 + (DH - 0.70) / 2, z), SEATMAT.fShell);
    }
    // QA r3: a thin taupe top rail with a small raise/lower tab at mid-length, not the wall bullnose (up_Privacy-Wall,
    // tpa_IMG_0220, f_17314 round tab) [V shape, A size]
    B.add(gRBox(0.035, 0.022, L - 0.14, 0.006, 1), M4.trs(-hx + 0.015, DH + 0.011, -L / 2), SEATMAT.fDoor);
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
    const kx = xo + shelfW / 2, kz = -0.80, ky = 0.681;
    const K = M4.trs(kx, 0.678, kz, 0, 0, -12 * DEG), kt = (x, y, z, ry = 0, rx = 0) => M4.mul(K, M4.trs(x - kx, y - 0.678, z - kz, ry, rx));
    const flat = (x, y, z) => kt(x, y, z, 0, -Math.PI / 2), glyph = { c: '#f2f2f2', r: 0.4, e: 0.1 };
    B.add(gRBox(0.13, 0.03, 0.15, 0.006, 1), kt(kx, 0.663, kz), SEATMAT.fConsole);
    B.add(gRBox(0.12, 0.006, 0.13, 0.006, 1), kt(kx, ky - 0.003, kz), { c: '#8a8882', r: 0.5 });
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
    const Hs = M4.trs(kx, 0.678, hz, 0, 0, -12 * DEG);
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
  B.add(gRBox(0.014, 0.42, 0.32, 0.012, 1), M4.trs(xa - 0.008, 0.96, -0.62), SEATMAT.fShell);          // door frame ~0.30 x 0.40 [D]
  B.add(gRBox(0.004, 0.36, 0.26, 0.004, 1), M4.trs(xa - 0.016, 0.96, -0.62), SEATMAT.fWood);           // closed door: wood face (f35)
  if (!lod) B.add(gBox(0.003, 0.03, 0.20), M4.trs(xa - 0.0165, 0.795, -0.62), { c: '#cfcac2', r: 0.6 }); // safety label strip
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
  B.add(gRBox(0.13, 0.09, 0.66, 0.035, 3), M4.trs(hx - 0.059, H + 0.0175, -L + 0.30), SEATMAT.fCap);   // w4: outboard so the inner edge clears the pier
  // aisle-facing exterior (w1): two EQUAL 0.50 m sliding leaves parked at either end of a ~0.64 m opening (omaat_f7 /
  // up_empty ~1.3 leaf), each a dark frame round flat vertical slats with dark grooves, pitch ~0.024, ~20 per leaf (pb_20
  // closed, omaat_f49); the fixed wardrobe run aft of the aft leaf is dark wood in a dark frame (pb_20 flanks) + LED line
  if (!lod) {
    const yc = 0.14 + (H - 0.24) / 2;
    for (const [z0, z1] of [[-0.96, -0.46], [-L + 0.10, -L + 0.60]]) {
      const len = z1 - z0;
      B.add(gBox(0.004, H - 0.30, len - 0.06), M4.trs(hx + 0.002, yc, (z0 + z1) / 2), SEATMAT.fFluteGap);
      // w2: 0.055 stiles / rails (~12 % of the leaf, pb_20), rounded ribs with a ~45 % dark groove (omaat_f4 / f7 convex ribs).
      // w3: pitch 0.026 (15 per leaf, real pb_20 ~23 at ~0.017) - finer ribs alias to moire at cabin distance [A, deliberate]
      for (let z = z0 + 0.068; z < z1 - 0.058; z += 0.026) B.add(gCyl(0.0075, 0.0075, H - 0.34, 4, false, -Math.PI / 2, Math.PI), M4.trs(hx + 0.002, yc, z), SEATMAT.fFlute);   // 8-tri half-round rib (a gRBox was 108)
      for (const z of [z0 + 0.0275, z1 - 0.0275]) B.add(gRBox(0.016, H - 0.24, 0.055, 0.006, 1), M4.trs(hx + 0.007, yc, z), SEATMAT.fDoorFrame);
      for (const y of [0.14 + 0.0275, H - 0.10 - 0.0275]) B.add(gRBox(0.016, 0.055, len, 0.006, 1), M4.trs(hx + 0.007, y, (z0 + z1) / 2), SEATMAT.fDoorFrame);
      B.add(gBox(0.006, 0.008, len - 0.02), M4.trs(hx + 0.004, 0.06, (z0 + z1) / 2), SEATMAT.fLed);
    }
  }
  if (!lod) {
    B.add(gBox(0.004, H - 0.28, 0.32), M4.trs(hx + 0.003, 0.14 + (H - 0.24) / 2, -0.27), SEATMAT.fWood);
    for (const z of [-0.46 + 0.012, -0.08 - 0.012]) B.add(gRBox(0.012, H - 0.24, 0.024, 0.004, 1), M4.trs(hx + 0.006, 0.14 + (H - 0.24) / 2, z), SEATMAT.fDoorFrame);
    for (const y of [0.14 + 0.012, H - 0.10 - 0.012]) B.add(gRBox(0.012, 0.024, 0.38, 0.004, 1), M4.trs(hx + 0.006, y, -0.27), SEATMAT.fDoorFrame);
    B.add(gBox(0.006, 0.008, 0.36), M4.trs(hx + 0.004, 0.06, -0.27), SEATMAT.fLed);
  }
  // (the sliding doors are parked inside the wardrobe wall and the front outer wall; QA r2: the old parked-door boxes
  // stood 3 mm proud of the rib plane and showed as pale bands above / below the rib frames)
  // small silver pulls on the frame stiles at the leaves' meeting edges, ~0.6 m up (omaat_f60 / f33)
  if (!lod) for (const zz of [-0.96 + 0.035, -L + 0.60 - 0.035]) B.add(gRBox(0.012, 0.09, 0.02, 0.004, 1), M4.trs(hx + 0.019, 0.60, zz), { c: '#b9b6b0', r: 0.3, m: 0.85 });
  // the seat: upholstered base, thin cushion, flat back leaning on the aft wall, slate headrest flap (f_17302 / 17309)
  const S = M4.trs(seatX, 0, -0.14);
  const F = SEATMAT.fFabric;
  B.add(gRBox(SW, 0.34, 0.62, 0.02, 1), M4.mul(S, M4.trs(0, 0.17, -0.36)), F);
  // solid taupe box armrest beside the wardrobe, flat taupe top at ~0.62, literature pocket in its inner face
  // (omaat_f13 both seats, omaat_f5 / f2) [D]
  const ax = xa - seatX - 0.05;               // armrest centre (local), against the wardrobe
  B.add(gRBox(0.10, 0.62, 0.62, 0.02, 1), M4.mul(S, M4.trs(ax, 0.31, -0.40)), SEATMAT.fConsole);
  B.add(gRBox(0.11, 0.025, 0.63, 0.01, 1), M4.mul(S, M4.trs(ax, 0.632, -0.40)), SEATMAT.fShell);
  if (!lod) B.add(gRBox(0.006, 0.16, 0.26, 0.004, 1), M4.mul(S, M4.trs(ax - 0.051, 0.45, -0.40)), SEATMAT.fInner);
  // w1: the seat back stands in a sculpted taupe niche - side jambs ~0.10 and a ~0.10 header on the aft wall - with the two
  // black dome reading lamps in the header corners, facing forward (omaat_f5 / f9 / f1) [V shape, D size]
  for (const s of [-1, 1]) B.add(gRBox(0.10, H - 0.66, 0.12, 0.025, 2), M4.trs(seatX + s * (SW / 2 + 0.05), 0.66 + (H - 0.66) / 2, -0.16), SEATMAT.fConsole);
  B.add(gRBox(SW + 0.20, 0.10, 0.12, 0.025, 2), M4.trs(seatX, H - 0.05, -0.16), SEATMAT.fConsole);   // w3: niche 1.17x the back (omaat_f9)
  for (const s of [-1, 1]) spot(M4.trs(seatX + s * (SW / 2 + 0.01), H - 0.05, -0.225, 0, -Math.PI / 2));
  if (bed) {
    B.add(gLoft(cushionSecs(SW, 1.96, 0.06, -0.03, { edge: 0.03, r: 0.035, crown: 0.004 }), 3), M4.trs(seatX - 0.01, 0.44, -1.08), { c: '#f0efea', r: 0.9, l: LAYER.fabric });
    B.add(gRBox(ow, 0.44, 0.9, 0.03, 1), M4.trs(ox, 0.22, -1.40), SEATMAT.fInner);
    // white duvet from the pillows to the ottoman, white pillow + lavender pillow (omaat_f57 / f58 / f59, f_17304)
    B.add(gLoft(cushionSecs(SW + 0.08, 1.55, 0.07, -0.045, { edge: 0.06, r: 0.06, crown: 0.015 }), 3), M4.trs(seatX - 0.01, 0.50, -1.12), { c: '#e2dfd8', r: 0.95, l: LAYER.fabric });
    // QA r3: not a flat slab - a turned-down top fold across the chest, sides draping over the pad edge, soft crown (w1: the ridge wrinkles read as rings) (omaat_f57 / f58, f_17304) [A]
    if (!lod) {
      const duv = { c: '#e2dfd8', r: 0.95, l: LAYER.fabric };
      B.add(gLoft(cushionSecs(SW + 0.07, 0.20, 0.035, -0.0175, { edge: 0.016, r: 0.03, crown: 0.004 }), 3), M4.trs(seatX - 0.01, 0.545, -0.50, 0, 3 * DEG), duv);
    }
    // w2: pillows propped up against the aft niche, lavender in front (omaat_f46, up_bed_made) [V]
    B.add(gLoft(cushionSecs(0.5, 0.32, 0.13, -0.065, { edge: 0.05, r: 0.05 }), 3), M4.trs(seatX, 0.66, -0.29, 0, -60 * DEG), SEATMAT.pillow);
    B.add(gLoft(cushionSecs(0.44, 0.28, 0.10, -0.05, { edge: 0.04, r: 0.045 }), 3), M4.trs(seatX + 0.04, 0.53, -0.52, 0, -15 * DEG), SEATMAT.fCushionBlue);
  } else {
    B.add(gLoft(cushionSecs(SW, 0.62, 0.075, -0.035, { edge: 0.022, r: 0.02, crown: 0.004 }), lod ? 3 : 4), M4.mul(S, M4.trs(0, 0.375, -0.36, 0, 2 * DEG)), F);
    // w1: taller, nearly upright back - top ~1.14 m, 5 deg (omaat_f5 level view) [D]
    const BH = M4.mul(S, M4.trs(0, 0.42, -0.12, 0, 5 * DEG));
    loftAt(B, [SEC(0.0, SW - 0.02, 0.06, 0, 0.02), SEC(0.025, SW, 0.08, 0, 0.028), SEC(0.70, SW, 0.08, 0, 0.028), SEC(0.725, SW - 0.02, 0.06, 0.002, 0.02)], BH, F, lod ? 2 : 3);
    // flap ~77 % of the back width, hung from the very top edge and wrapping over it (w2: omaat_f9 / f1 / f5 / f8)
    B.add(gRBox(0.56, 0.20, 0.012, 0.006, 1), M4.mul(BH, M4.trs(0, 0.625, -0.044)), SEATMAT.fFlap);
    B.add(gRBox(0.56, 0.014, 0.075, 0.006, 1), M4.mul(BH, M4.trs(0, 0.727, -0.006)), SEATMAT.fFlap);
    if (!lod) {
      B.add(gBox(SW - 0.04, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.36, -0.041)), SEATMAT.fInner);
      B.add(gBox(SW - 0.04, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.18, -0.041)), SEATMAT.fInner);
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
