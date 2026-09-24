// ------------------------------------------------------------------
// THE Suite first class (JAMCO) - see REFERENCE777.md
// Seat-local frame and shared materials / helpers (SEATMAT, SEC, loftAt, cushionSecs) live in 09_seats.js.
// New materials for this product: Object.assign(SEATMAT, {...}) at the top of this file (loaded after 09_seats.js).
// ------------------------------------------------------------------
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
  // QA r3: the centre suite (1.07 m between inner faces) cannot fit a 0.10 wing + 0.976 bezel + 0.16 pier; in omaat_f5 /
  // f33 its screen sits against the divider behind a slim taupe edge and the aisle-side pier is narrow [D]
  const wing = center ? 0.02 : 0.10;
  const scx = xo + wing + 0.488;
  B.add(gRBox(0.976, 0.555, 0.02, 0.006, 1), M4.trs(scx, 0.95, -L + 0.13), SEATMAT.bezel);
  B.add(gQuad(0.952, 0.535), M4.trs(scx, 0.95, -L + 0.141), SEATMAT.screen, atlasUV('screen'));
  B.add(gRBox(wing - 0.012, H - 0.68, 0.03, center ? 0.004 : 0.03, center ? 1 : 2), M4.trs(xo + wing / 2, 0.68 + (H - 0.68) / 2, -L + 0.135), center ? SEATMAT.fShell : SEATMAT.fWood);
  const pX0 = Math.min(scx + 0.488, hx - 0.07), pX = (pX0 + hx) / 2;   // pier from the screen edge to the aisle wall (window 0.158, centre 0.074)
  B.add(gRBox(hx - pX0, H - 0.62, 0.03, 0.01, 1), M4.trs(pX, 0.62 + (H - 0.62) / 2, -L + 0.135), SEATMAT.fWood);
  // mirror: dark glass in a thin taupe rim, lit edge on the aisle side (omaat_f11 left pier, omaat_f5 1D/1G, f_17313);
  // sized to the pier so it never leaves the shell (QA r3)
  const mW = Math.min(0.10, hx - pX0 - 0.016), mX = center ? pX : pX0 + 0.058;
  B.add(gRBox(mW, 0.36, 0.012, Math.min(0.045, mW / 2 - 0.002), 3), M4.trs(mX, 0.97, -L + 0.155), SEATMAT.fShell);
  B.add(gRBox(mW - 0.015, 0.345, 0.004, Math.min(0.04, mW / 2 - 0.009), 3), M4.trs(mX, 0.97, -L + 0.162), { c: '#1c1d20', r: 0.08 });
  if (!lod) B.add(gBox(0.004, 0.28, 0.004), M4.trs(mX + mW / 2 - 0.002, 0.97, -L + 0.162), SEATMAT.fLed);
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
    // QA r3: a thin taupe top rail with a small raise/lower tab at mid-length, not the wall bullnose (up_Privacy-Wall,
    // tpa_IMG_0220, f_17314 round tab) [V shape, A size]
    B.add(gRBox(0.035, 0.022, L - 0.14, 0.006, 1), M4.trs(-hx + 0.015, H + 0.011, -L / 2), SEATMAT.fDoor);
    B.add(gRBox(0.012, 0.035, 0.07, 0.006, 1), M4.trs(-hx + 0.035, H - 0.01, -L / 2), SEATMAT.fCap);
  } else B.add(gRBox(0.03, 0.70, L - 0.14, 0.01, 1), M4.trs(-hx + 0.015, 0.35, -L / 2), SEATMAT.fShell);
  B.add(gRBox(shelfW, 0.64, L - 0.30, 0.02, 1), M4.trs(xo + shelfW / 2, 0.32, -L / 2 - 0.04), SEATMAT.fConsole);
  B.add(gRBox(shelfW + 0.01, 0.025, L - 0.30, 0.008, 1), M4.trs(xo + shelfW / 2, 0.652, -L / 2 - 0.04), SEATMAT.fShell);
  // QA r3: tapered dark-wood insert (0.14 forward -> 0.09 aft, outer edge straight) in a shallow black-rimmed recess of the
  // console top, forward of the keypad (f_17313 / up_Privacy-Wall / omaat_f58) [D shape from photos, A size]
  const trayXf = M4.trs(xo + 0.025, 0.6655, -0.92, 0, -Math.PI / 2);
  B.add(gExtrude([[-0.006, -0.006], [0.10, -0.006], [0.151, 0.806], [-0.006, 0.806]], 0.004), trayXf, SEATMAT.black);
  B.add(gExtrude([[0, 0], [0.09, 0], [0.14, 0.80], [0, 0.80]], 0.006), M4.mul(M4.trs(0, 0, 0.0015), trayXf), SEATMAT.fShelf);
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
    B.add(gLoft(cushionSecs(0.70, 1.55, 0.05, -0.025, { edge: 0.04, r: 0.06 }), 3), M4.trs(seatX - 0.01, 0.50, -1.12), { c: '#e2dfd8', r: 0.95, l: LAYER.fabric });
    // QA r3: not a flat slab - a turned-down top fold across the chest and a few shallow wrinkles (omaat_f57 / f58, f_17304) [A]
    if (!lod) {
      const duv = { c: '#e2dfd8', r: 0.95, l: LAYER.fabric };
      B.add(gLoft(cushionSecs(0.73, 0.20, 0.035, -0.0175, { edge: 0.016, r: 0.03, crown: 0.004 }), 3), M4.trs(seatX - 0.01, 0.545, -0.50, 0, 3 * DEG), duv);
      for (const [dz, ry, ln] of [[-0.95, 0.35, 0.42], [-1.30, -0.25, 0.36], [-1.62, 0.15, 0.30]])
        B.add(gCyl(0.012, 0.012, ln, 8, false, -Math.PI / 2, Math.PI), M4.trs(seatX + 0.03, 0.530, dz, ry, 0, Math.PI / 2), duv);
    }
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
