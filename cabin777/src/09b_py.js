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
  B.add(gLoft(cushionSecs(0.415, 0.50, 0.115, -0.06, { edge: 0.04, r: 0.035, crown: 0.012 }), lod ? 3 : 4), M4.trs(x0, 0.425, -0.30, 0, 3 * DEG), F);
  B.add(gRBox(0.415, 0.05, 0.48, 0.012, 1), M4.trs(x0, 0.335, -0.29), SEATMAT.pyArm);
  // QA r2: the centre of the back sits ~3 cm behind its old face between the bolsters (d 0.10 at y 0.34-0.52), and the top
  // blends into the headrest (overlapping sections instead of a step)
  loftAt(B, [SEC(0.0, 0.42, 0.09, -0.01, 0.025), SEC(0.05, 0.44, 0.115, -0.02), SEC(0.18, 0.45, 0.13, -0.032, 0.045), SEC(0.34, 0.45, 0.10, -0.014, 0.042),
    SEC(0.52, 0.45, 0.10, -0.009, 0.042), SEC(0.66, 0.46, 0.10, 0.004, 0.045), SEC(0.80, 0.46, 0.11, 0.015, 0.045),
    SEC(0.89, 0.45, 0.11, 0.02, 0.045), SEC(0.925, 0.42, 0.09, 0.03, 0.035), SEC(0.945, 0.34, 0.05, 0.04, 0.02)], BH, F, lod ? 3 : 4);
  // ANA: the patterned back forms the rounded top of the seat level with the headrest and runs beside + behind the
  // wings (py_37301 right seat, py_37303 side view); the headrest stands ~2 cm proud of it [D]
  // sculpted side bolsters standing ~5 cm proud of the centre, narrow at the waist (~0.30 above the cushion), flaring
  // at the shoulders (py_37301 / 37303) [D]
  for (const sd of [-1, 1]) {
    const BX = M4.mul(BH, M4.trs(sd * 0.19, 0, -0.03, -sd * 14 * DEG));
    loftAt(B, [SEC(0.02, 0.07, 0.10, 0, 0.03), SEC(0.10, 0.085, 0.14, -0.016, 0.042), SEC(0.30, 0.07, 0.14, -0.016, 0.034), SEC(0.48, 0.09, 0.13, -0.012, 0.042),
      SEC(0.62, 0.085, 0.11, -0.01, 0.04), SEC(0.76, 0.07, 0.09, -0.004, 0.032), SEC(0.82, 0.05, 0.06, 0, 0.024)], BX, F, lod ? 2 : 3);
  }
  // thick rear shell that wraps round the back's sides (grey edge visible from the front)
  const zr = (y) => 0.105 + 0.014 * Math.sin(Math.PI * clamp(y / 0.84, 0, 1));
  // QA r2: the shell's rounded top rises above the headrest (to 0.97, headrest 0.91) and frames the screen from behind
  // (san_13 / san_24, py_37304); the top sections are rounded to half their depth
  // PY w2: the top is a large-radius arch that ends level with the headrest (0.925 vs 0.91), not a square board 6 cm
  // above it (py_37302 / 37303, san_13, alv_02; raters A + B) [D]
  // ANA: grey flank ~0.10 deep at the headrest, ~0.13 at the lumbar (py_37303), rear face rounding into the sides over
  // ~4 cm (py_37304); square-shouldered top so the wings never show from behind [D]
  const ds = [[-0.04, 0.08, 0.525], [0.12, 0.09, 0.525], [0.34, 0.10, 0.525], [0.5, 0.11, 0.525], [0.68, 0.115, 0.525], [0.78, 0.11, 0.522],
    [0.84, 0.10, 0.52], [0.88, 0.095, 0.515], [0.905, 0.085, 0.505], [0.925, 0.065, 0.475], [0.94, 0.04, 0.41], [0.948, 0.015, 0.30]];
  loftAt(B, ds.map(([y, d, w]) => SEC(y, w, d, zr(y) - d / 2 + 0.01, Math.min(d / 2 - 0.002, 0.045))), BH, SEATMAT.pyShell, lod ? 2 : 3);
  // 6-way headrest with wings
  loftAt(B, [SEC(0.67, 0.42, 0.085, -0.008, 0.036), SEC(0.71, 0.39, 0.092, -0.012, 0.04), SEC(0.85, 0.39, 0.092, -0.012, 0.04), SEC(0.895, 0.37, 0.075, -0.006, 0.032), SEC(0.91, 0.33, 0.05, -0.002, 0.02)], BH, F, lod ? 3 : 4);
  for (const s of [-1, 1]) {
    // soft round pillow bolsters either side of the flap, ~0.10 wide x 0.25 tall with domed ends, bulging ~3.5 cm
    // forward of the flap (py_37301 / 37305)
    // ANA: each wing ~0.45 of the flap width (py_37301 85 / 185 px), ~0.21 tall with its top just under the flap fold,
    // facing inward ~30 deg (py_37302 foreground wings read as narrow ellipses) [D]
    const WX = M4.mul(BH, M4.trs(s * 0.175, 0, -0.045, -s * 28 * DEG));
    loftAt(B, [SEC(0.68, 0.05, 0.05, 0, 0.024), SEC(0.70, 0.095, 0.10, 0, 0.045), SEC(0.73, 0.115, 0.115, 0, 0.052), SEC(0.85, 0.115, 0.115, 0, 0.052),
      SEC(0.88, 0.095, 0.10, 0, 0.045), SEC(0.895, 0.05, 0.05, 0, 0.024)], WX, SEATMAT.pyWing, lod ? 2 : 3);
  }
  // navy leatherette flap over the headrest front + top, silver trim line low on the back shell (py_37303)
  // flap ~0.28 x 0.25, hanging a little below the wing pads (py_37301 seat C: 98 x 92 px on a 158 px headrest) [D]
  B.add(gRBox(0.28, 0.265, 0.008, 0.006, 1), M4.mul(BH, M4.trs(0, 0.772, -0.064)), SEATMAT.pyCover);   // 0.64-0.905, h/w 0.95 (py_37301)
  B.add(gRBox(0.28, 0.008, 0.07, 0.004, 1), M4.mul(BH, M4.trs(0, 0.904, -0.03)), SEATMAT.pyCover);
  if (!lod) {   // folded hem band ~22 mm with a tone-on-tone topstitch, soft vertical dent mid-flap (py_37305)
    B.add(gBox(0.276, 0.022, 0.002), M4.mul(BH, M4.trs(0, 0.652, -0.0685)), { c: '#2c365e', r: 0.5, l: LAYER.leather });
    B.add(gBox(0.26, 0.002, 0.002), M4.mul(BH, M4.trs(0, 0.664, -0.0695)), { c: '#46507a', r: 0.6 });
  }
  B.add(gBox(0.49, 0.008, 0.006), M4.mul(BH, M4.trs(0, 0.04, zr(0.04) + 0.022)), SEATMAT.pyTrim);
  // fold-up leg rest (stowed below the pan front)
  // ANA py_37301, top to bottom: cushion nose, a ~5 cm fabric skirt, a prominent dark fluted roller (~55 mm) standing
  // ~1.5 cm proud, then the fabric leg rest hanging almost vertically to ~0.04 [D]
  B.add(gLoft([SEC(0.0, 0.40, 0.05, 0, 0.018), SEC(0.25, 0.41, 0.06, 0, 0.022)], 3), M4.trs(x0, 0.03, -0.535, 0, -2 * DEG), F);
  B.add(gRBox(0.41, 0.05, 0.025, 0.01, 1), M4.trs(x0, 0.35, -0.535), F);                           // skirt
  B.add(gRBox(0.40, 0.02, 0.05, 0.008, 1), M4.trs(x0, 0.035, -0.53), SEATMAT.pyArm);            // leg-rest foot bar
  // dark-grey hinge roller across the top of the stowed leg rest under the cushion nose, dark side links down to the
  // foot bar (py_37301, san_17) [D]
  B.add(gCyl(0.028, 0.028, 0.405, lod ? 8 : 14), M4.trs(x0, 0.305, -0.555, 0, 0, Math.PI / 2), SEATMAT.pyArm);
  if (!lod) for (let k = 0; k < 6; k++) B.add(gBox(0.40, 0.003, 0.004), M4.trs(x0, 0.305 + 0.028 * Math.cos(-1.2 + k * 0.5), -0.555 - 0.028 * Math.sin(-1.2 + k * 0.5)), SEATMAT.black);   // flutes
  if (!lod) for (const s of [-1, 1]) B.add(gRBox(0.015, 0.26, 0.03, 0.006, 1), M4.trs(x0 + s * 0.205, 0.17, -0.55), SEATMAT.pyArm);
  if (lod) return;
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz));
  if (!opts.noScreen) {
    // 15.6 in screen: black bezel 0.373 x 0.26 (active 0.345 x 0.195) in a grey housing ~0.44 x 0.30 that projects ~4 cm
    // and tilts top-back, its top just under the shell rim (py_37304: 1614 px/m; san_24) [D]
    const scr = (dz) => M4.mul(on(0.755, 0), M4.trs(0, 0, dz, 0, -6 * DEG));
    // ANA py_37304: bezel 0.376 x 0.263 set ~1 cm proud into the shell with a thin dark gap, framed by the shell rim
    // (~5 cm above it, 18 % of the bezel height) - no separate housing; placards 0.12 x 0.021, 1.7 cm under it [D]
    B.add(gRBox(0.385, 0.272, 0.008, 0.006, 1), scr(0.006), SEATMAT.black);
    B.add(gRBox(0.376, 0.263, 0.012, 0.008, 1), scr(0.016), SEATMAT.bezel);
    B.add(gQuad(0.345, 0.194), scr(0.0235), SEATMAT.screen, atlasUV('screen'));
    for (const sx of [-0.113, 0.113]) B.add(gQuad(0.12, 0.022), on(0.60, 0.0115, sx), { c: '#e8e8e6', r: 0.6 });
  }
  {   // (row 25 backs too: seen from row 26)
    // literature pocket ~3 cm under the placards (san_05 / san_08, alv_13; ANA shows no rear view this low): rigid tray
    // lip, a flat grey panel with a shallow black mesh window and stitched border [D]
    const py0 = 0.325;
    B.add(gRBox(0.44, 0.045, 0.05, 0.014, 1), on(0.232 + py0, 0.024), SEATMAT.pyShell);
    B.add(gRBox(0.36, 0.17, 0.016, 0.012, 1), on(0.135 + py0, 0.01), SEATMAT.pyShell);
    B.add(gBox(0.30, 0.065, 0.003), on(0.12 + py0, 0.019), { c: '#16181b', r: 0.9, l: LAYER.grille });
    for (const [sx, sy, w_, h_] of [[0, 0.156, 0.32, 0.002], [0, 0.084, 0.32, 0.002], [-0.16, 0.12, 0.002, 0.074], [0.16, 0.12, 0.002, 0.074]])
      B.add(gBox(w_, h_, 0.002), on(sy + py0, 0.0185, sx), { c: '#9a9ca0', r: 0.6 });                            // stitched border
    B.add(gBox(0.36, 0.008, 0.006), on(0.216 + py0, 0.036), SEATMAT.black);                         // pocket mouth shadow
  }
  if (!opts.noScreen) {
    // gooseneck reading light: leaves the shell side at headrest height, arcs down + forward to a brushed-aluminium
    // head with a black lens at shoulder height; one per seat, on the console side (py_37305 / 37301, san_14)
    const sd = x0 > 0 ? -1 : 1, P = (x, y, z) => M4.point(BH, [sd * x, y, z]);
    // root: silver bullet on the shell side near the top pointing forward, round grey button ~8 cm below (py_37303 / 37305)
    const sil = { c: '#c9ccd0', r: 0.25, m: 0.9, l: LAYER.brushed };
    B.add(gCyl(0.015, 0.018, 0.06, 10), M4.mul(BH, M4.trs(sd * 0.262, 0.84, zr(0.84) - 0.035, 0, Math.PI / 2)), sil);
    B.add(gCyl(0.01, 0.01, 0.006, 10), M4.mul(BH, M4.trs(sd * 0.264, 0.76, zr(0.76) - 0.03, 0, 0, Math.PI / 2)), { c: '#c7c9cc', r: 0.4 });
    B.add(gTube([P(0.262, 0.84, zr(0.84) - 0.065), P(0.262, 0.83, -0.02), P(0.265, 0.74, -0.10), P(0.24, 0.62, -0.16)], 0.0095, 8), null, SEATMAT.black);
    const hd = M4.mul(BH, M4.trs(sd * 0.238, 0.583, -0.204, 0, 50 * DEG));   // w4: head points forward-down ~45 deg (py_37305)
    B.add(gCyl(0.019, 0.019, 0.11, 12), hd,   // head ~38 x 115 mm (alv_17) [D]
    { c: '#c9ccd0', r: 0.25, m: 0.9, l: LAYER.brushed });
    B.add(gCyl(0.007, 0.007, 0.002, 10), M4.mul(hd, M4.trs(0, -0.025, 0.0192, 0, Math.PI / 2)), SEATMAT.black);   // lens on the side (py_37305)
  }
  // PY w2: ONE fold-down footrest for the passenger behind (alv_05 / alv_06, san_10): two ribbed dark pads (~0.13 m) on a
  // common axle with silver end caps + centre hub, hung from the seat pan on one silver arm just off centre (w3; alv_06) [D]
  const fy = 0.30, fz = 0.13;
  for (const s of [-1, 1]) {
    B.add(gCyl(0.021, 0.021, 0.13, 12), M4.trs(x0 + s * 0.08, fy, fz, 0, 0, Math.PI / 2), SEATMAT.black);
    B.add(gCyl(0.023, 0.023, 0.014, 12), M4.trs(x0 + s * 0.152, fy, fz, 0, 0, Math.PI / 2), SEATMAT.frame);
  }
  B.add(gRBox(0.018, 0.17, 0.024, 0.006, 1), M4.trs(x0 + 0.03, fy + 0.085, fz - 0.045, 0, 32 * DEG), SEATMAT.frame);   // one arm (alv_06)
  B.add(gCyl(0.024, 0.024, 0.03, 12), M4.trs(x0, fy, fz, 0, 0, Math.PI / 2), SEATMAT.frame);
  if (!lod) for (const s of [-1, 1]) for (let k = -2; k <= 2; k++)                                     // pad ribs
    B.add(gBox(0.12, 0.003, 0.004), M4.trs(x0 + s * 0.08, fy + 0.02 * Math.cos(k * 0.35), fz + 0.02 * Math.sin(k * 0.35)), SEATMAT.hole);
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
    // PY w2: console face ~0.12 (alv_08 / 09 two universal sockets side by side, py_37301 console / cushion 0.28-0.35;
    // raters measured 0.13-0.15 but the 0.5525 seat spacing then leaves < 0.42 of cushion) [D]
    const w = inner ? 0.135 : 0.07;   // ANA py_37301: console / cushion 0.31 -> 0.135 with a 0.415 cushion [D]
    if (inner) {
      // floor-standing console between seats: blue-grey body, silver trim round the top, cubbies + controls on
      // its front face, red life-vest tab at the bottom (py_37301)
      B.add(gRBox(w, 0.62, 0.52, 0.014, 1), M4.trs(xa, 0.31, -0.28), SEATMAT.pyArm);
      // lid: light blue-grey with a groove along it (ANA py_37303 / 37301; the dark stitched lid is a later generation)
      loftAt(B, [SEC(0.62, w + 0.004, 0.38, -0.2, 0.02), SEC(0.645, w + 0.008, 0.39, -0.2, 0.025), SEC(0.665, w, 0.38, -0.2, 0.02)], M4.trs(xa, 0, 0), SEATMAT.pyArmPad, 2);
      // nose: short square light-grey block with two cups side by side (py_37303, alv_18) [D]
      B.add(gRBox(w + 0.004, 0.05, 0.09, 0.012, 1), M4.trs(xa, 0.64, -0.495), SEATMAT.pyBin);
      if (!lod) for (const s of [-1, 1]) B.add(gCyl(0.029, 0.029, 0.004, 16), M4.trs(xa + s * 0.032, 0.664, -0.495), { c: '#8e9195', r: 0.5 });
      if (!lod) {
        B.add(gBox(0.006, 0.003, 0.36), M4.trs(xa, 0.6655, -0.21), { c: '#4a5058', r: 0.7 });            // lid groove
        // each side face: silver plaque ~0.16 x 0.028 with the seat letter + two buttons (py_37303 'H'), black handset
        // dock at the front, tray-table seam with a small silver latch (py_37303) [D]
        for (const s of [-1, 1]) {
          const fx = xa + s * (w / 2 + 0.002);
          B.add(gRBox(0.003, 0.028, 0.16, 0.005, 1), M4.trs(fx, 0.625, -0.37), SEATMAT.pyTrim);
          B.add(gBox(0.002, 0.018, 0.018), M4.trs(fx + s * 0.002, 0.625, -0.43), { c: '#e2e2de', r: 0.6 });
          for (const bz of [-0.39, -0.365]) B.add(gBox(0.002, 0.014, 0.018), M4.trs(fx + s * 0.002, 0.625, bz), SEATMAT.black);
          B.add(gRBox(0.004, 0.14, 0.035, 0.008, 1), M4.trs(fx, 0.52, -0.505), SEATMAT.black);
          B.add(gBox(0.003, 0.004, 0.36), M4.trs(fx, 0.45, -0.30), SEATMAT.black);
          B.add(gBox(0.004, 0.012, 0.02), M4.trs(fx, 0.45, -0.475), SEATMAT.pyTrim);
        }
      }
      B.add(gBox(w + 0.01, 0.008, 0.535), M4.trs(xa, 0.618, -0.28), SEATMAT.pyTrim);
      if (!lod) {
        // front face (alv_08 / alv_09, py_37306): two open moulded cubbies (upper larger) with a royal-blue triangle in
        // the corner, a black panel with two universal AC + USB sockets, then a lower block with the red life-vest tab
        // each cubby: a grey front plate standing ~2.5 cm proud over the lower 3/4, dark opening only above it
        for (const [y, h] of [[0.51, 0.10], [0.35, 0.10]]) {     // ANA py_37301: two equal pockets
          B.add(gBox(w - 0.026, 0.016, 0.004), M4.trs(xa, y + h / 2 - 0.012, -0.543), { c: '#2a2c30', r: 0.8 });
          B.add(gRBox(w - 0.02, h * 0.74, 0.028, 0.007, 1), M4.trs(xa, y - h * 0.13, -0.554), SEATMAT.pyArm);
          // royal-blue right-angled triangle: top-left corner on the upper cubby, top-right on the lower (alv_09) [V]
          const up = y > 0.43;
          const L = 0.026, sx = up ? 1 : -1;   // legs along the plate's top edge and outer side (top-left / top-right seen from the front)
          B.add(gExtrude([[0, 0], [-sx * L, 0], [0, -L]], 0.002), M4.trs(xa + sx * (w / 2 - 0.013), y + h * 0.24 - 0.008, -0.5695), { c: '#2f47a8', r: 0.6 });
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
    } else if (k === opts.win) {
      // window end: only a slim armrest from the seat side, dark slate with a light top edge, fully rounded front and a
      // small white seat-letter square; seat side + leg-rest link visible below, no panel to the floor
      // (ANA py_37301 left seat, py_37302 left pair, py_37303 rear seat) [D]
      const o = k === 0 ? -1 : 1, arm = { c: '#4c5058', r: 0.5, l: LAYER.plastic };
      B.add(gRBox(0.05, 0.07, 0.34, 0.032, 2), M4.trs(xa + o * 0.005, 0.605, -0.30), arm);
      B.add(gRBox(0.052, 0.012, 0.32, 0.006, 1), M4.trs(xa + o * 0.005, 0.641, -0.30), { c: '#9aa0a8', r: 0.4, l: LAYER.plastic });
      B.add(gRBox(0.04, 0.12, 0.08, 0.015, 1), M4.trs(xa + o * 0.005, 0.56, -0.10), arm);
      if (!lod) B.add(gBox(0.002, 0.02, 0.02), M4.trs(xa + o * 0.031, 0.60, -0.43), { c: '#e2e2de', r: 0.6 });
    } else {
      // aisle end: large rounded arm shroud from the floor (py_37301 / 37303)
      const o = k === 0 ? -1 : 1;
      B.add(gRBox(0.05, 0.64, 0.62, 0.025, 2), M4.trs(xa + o * 0.01, 0.32, -0.27), SEATMAT.pyShell);
      // dark-grey arm cap running to the shroud front, where it rounds over and turns down ~6 cm (py_37301 right seat,
      // san_13); recessed darker panel on the shroud's outer face above the silver strip (py_37303)
      const cap = { c: '#50555d', r: 0.35, l: LAYER.plastic };   // glossy charcoal cap (py_37301 right seat)
      loftAt(B, [SEC(0.62, w, 0.52, -0.30, 0.02), SEC(0.648, w + 0.006, 0.53, -0.30, 0.028), SEC(0.668, w - 0.004, 0.52, -0.30, 0.02)], M4.trs(xa, 0, 0), cap, 2);
      B.add(gCyl(0.024, 0.024, w, 12), M4.trs(xa, 0.644, -0.556, 0, 0, Math.PI / 2), cap);
      B.add(gRBox(w, 0.06, 0.03, 0.012, 1), M4.trs(xa, 0.61, -0.565), cap);
      // ANA py_37303: silver strip ~0.25 above the floor, nearly level; lighter recessed panel from under the cap down to
      // it, large radius on its top-rear corner; darker base band with a D-shaped handle recess below the strip [D]
      if (!lod) {
        B.add(gRBox(0.006, 0.28, 0.50, 0.04, 1), M4.trs(xa + o * 0.033, 0.44, -0.30), { c: '#8a929c', r: 0.45, l: LAYER.plastic });
        B.add(gRBox(0.004, 0.03, 0.10, 0.012, 1), M4.trs(xa + o * 0.034, 0.215, -0.33), SEATMAT.black);
        B.add(gRBox(0.004, 0.22, 0.58, 0.02, 1), M4.trs(xa + o * 0.0335, 0.12, -0.27), { c: '#5c626c', r: 0.5, l: LAYER.plastic });
      }
      B.add(gBox(0.006, 0.012, 0.58), M4.trs(xa + o * 0.037, 0.25, -0.27), SEATMAT.pyTrim);
    }
    if (inner && !lod) {
      // brushed-aluminium two-cell bottle bin on the console rear at knee height for the row behind (san_16 / 17 / 18)
      // PY w2: floor-standing silver bin, two square ~7 cm cups at the top (~0.44), white placard (alv_07, san_07) [D]
      B.add(gRBox(0.145, 0.44, 0.08, 0.012, 1), M4.trs(xa, 0.22, 0.045), SEATMAT.pyBin);
      for (const s of [-1, 1]) {        // recessed brushed cups with thin walls, grey floor (alv_07)
        B.add(gRBox(0.056, 0.004, 0.058, 0.01, 1), M4.trs(xa + s * 0.033, 0.4405, 0.045), { c: '#6e7276', r: 0.45, m: 0.6 });   // shadowed cup floor
      }
      B.add(gQuad(0.08, 0.03), M4.trs(xa, 0.36, 0.0855), { c: '#e6e6e2', r: 0.6 });
    }
  });
  const W = n * sp;
  const legX = n >= 3 ? [-(W / 2 - 0.28), W / 2 - 0.28] : [-0.28, 0.28];
  for (const lx of legX) {
    // w3: pale champagne leg frames with a diagonal rear strut, seen from the row behind (san_05, alv_03; rater A) [A]
    const leg = { c: '#bab7ae', r: 0.35, m: 0.75, l: LAYER.brushed };   // w4: light warm aluminium (A: champagne, B: cool alu)
    B.add(gRBox(0.035, 0.44, 0.045, 0.01, 1), M4.trs(lx, 0.19, 0.0, 0, 35 * DEG), leg);
    B.add(gRBox(0.04, 0.34, 0.05, 0.01, 1), M4.trs(lx, 0.16, -0.40, 0, -20 * DEG), leg);
    B.add(gBox(0.055, 0.025, 0.14), M4.trs(lx, 0.012, -0.08), SEATMAT.black);
    B.add(gBox(0.055, 0.025, 0.14), M4.trs(lx, 0.012, -0.46), SEATMAT.black);
  }
  for (const zb of [-0.12, -0.44]) B.add(gCyl(0.022, 0.022, W - 0.05, 10), M4.trs(0, 0.30, zb, 0, 0, Math.PI / 2), SEATMAT.frame);
  return B.build();
}
function pyUnitFar(n, opts = {}) {
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
    B.add(gQuad(0.345, 0.194), M4.mul(BH, M4.trs(0, 0.755, 0.121)), SEATMAT.screen, atlasUV('screen'));
  }
  for (let k = 0; k <= n; k++) {
    if (k === opts.win) B.add(gBox(0.05, 0.07, 0.34), M4.trs((k - n / 2) * sp, 0.605, -0.30), SEATMAT.pyArm);
    else B.add(gBox(k > 0 && k < n ? 0.135 : 0.07, 0.34, 0.44), M4.trs((k - n / 2) * sp, 0.49, -0.27), SEATMAT.pyArm);
  }
  return B.build();
}
