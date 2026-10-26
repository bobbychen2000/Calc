// ------------------------------------------------------------------
// Premium Economy seat (ZIM) for the ANA 777-300ER - see REFERENCE777.md
// Seat-local frame and shared materials / helpers (SEATMAT, SEC, loftAt, cushionSecs) live in 09_seats.js.
// New materials for this product: Object.assign(SEATMAT, {...}) at the top of this file (loaded after 09_seats.js).
// ------------------------------------------------------------------
// ================= PREMIUM ECONOMY (ZIM, 19 in, 15.6 in screen, leg rest + bicycle footrest) =================
// PY w1: sp 0.5525 = 05_layout pySp (seat ids / eye points and geometry agreed only to 2-3 cm with the old 0.5715) [D]
const PY = { back: 14 * DEG, hinge: [0.48, -0.09], sp: 0.5525 };
const PYGAP = { c: '#1c1e23', r: 0.9 };   // polishD: cm-scale seat joints (integration L9-L11, econ tuck crease) [D]
const PYGROOVE = { c: '#3e434d', r: 0.9 };   // polishF: recessed seams, mid-dark (w18 A: #2a2e36 rendered near-black in the shaded corner) [D]
// back cushion (QA r2: centre ~3 cm behind its old face between the bolsters, top blending into the headrest; w7: crown
// under the shell rim)
const PYBACK = [SEC(0.0, 0.42, 0.09, -0.01, 0.025), SEC(0.05, 0.44, 0.115, -0.02), SEC(0.18, 0.45, 0.13, -0.032, 0.045), SEC(0.34, 0.45, 0.10, -0.014, 0.042),
  SEC(0.52, 0.45, 0.10, -0.009, 0.042), SEC(0.66, 0.43, 0.10, 0.004, 0.045), SEC(0.80, 0.42, 0.11, 0.015, 0.045),
  SEC(0.89, 0.42, 0.11, 0.02, 0.045), SEC(0.905, 0.39, 0.085, 0.025, 0.035), SEC(0.918, 0.31, 0.045, 0.03, 0.02)];
// back bolster and headrest ear sections (bolster frame: x sd 0.185, z -0.03, yaw -sd 14 deg; ear: x s 0.172, z -0.045, 12 deg)
const PYBOL = [SEC(0.02, 0.07, 0.10, 0, 0.03), SEC(0.10, 0.085, 0.14, -0.016, 0.042), SEC(0.30, 0.07, 0.14, -0.016, 0.034), SEC(0.48, 0.10, 0.15, -0.02, 0.045),
  SEC(0.62, 0.10, 0.13, -0.016, 0.045), SEC(0.68, 0.085, 0.10, -0.01, 0.038), SEC(0.71, 0.05, 0.05, -0.004, 0.02)];
const PYEAR = [SEC(0.672, 0.055, 0.045, 0, 0.022), SEC(0.685, 0.11, 0.09, 0, 0.04), SEC(0.71, 0.125, 0.105, 0, 0.045), SEC(0.85, 0.125, 0.105, 0, 0.045),
  SEC(0.88, 0.11, 0.09, 0, 0.04), SEC(0.898, 0.07, 0.06, 0, 0.028), SEC(0.905, 0.035, 0.028, 0, 0.013)];
// section of a lofted list at height y (linear in w / d / z / r, as the loft's rings are)
function secAt(secs, y) {
  let i = 0;
  while (i < secs.length - 2 && secs[i + 1].y < y) i++;
  const a = secs[i], b = secs[i + 1], t = clamp((y - a.y) / (b.y - a.y), 0, 1), L = (k) => (a[k] || 0) + t * ((b[k] || 0) - (a[k] || 0));
  return { y, w: L('w'), d: L('d'), z: L('z'), r: L('r'), x: L('x') };
}
// polishF: path where a fabric part's outer face (lofted secs under transform T, outer side sd) enters a surface whose
// signed distance is sdf(y, x, z), walked front (-z) to back; one point per y, gaps where the face never meets it
function seamPath(secs, T, sd, sdf, y0, y1, n) {
  const runs = [[]];
  for (let k = 0; k <= n; k++) {
    const y = y0 + ((y1 - y0) * k) / n, s = secAt(secs, y);
    const pts = rrectPts(s.w, s.d, Math.max(0.0005, Math.min(s.r, s.w / 2 - 1e-4, s.d / 2 - 1e-4)), 6, s.x, s.z)
      .filter(([x]) => sd * (x - s.x) > 0).sort((p, q) => p[1] - q[1]).map(([x, z]) => M4.point(T, [x, y, z]));
    let hit = null;
    for (let i = 1; i < pts.length && !hit; i++) {
      const fa = sdf(pts[i - 1][1], pts[i - 1][0], pts[i - 1][2]), fb = sdf(pts[i][1], pts[i][0], pts[i][2]);
      if (fa >= 0 && fb < 0) { const t = fa / (fa - fb); hit = [0, 1, 2].map((j) => pts[i - 1][j] + t * (pts[i][j] - pts[i - 1][j])); }
    }
    if (hit) runs[runs.length - 1].push(hit); else if (runs[runs.length - 1].length) runs.push([]);
  }
  return runs.filter((r) => r.length > 2);
}
const PYREAR = { c: '#5e636b', r: 0.42, l: LAYER.plastic };   // rear face of the shell + literature bucket (py_37304, san_26) [D]
function pySeat(B, x0, lod, opts = {}) {
  const [hy, hz] = PY.hinge;
  // w11 (gap): ANA alternates two trims - A dash-weave back + cushion with petal ears, B petal back + cushion with dash ears;
  // the centre block's aisle seats D / G carry B (py_37302 foreground, san_12 26G vs 26F); both window-pair seats are A (py_37301) [V]
  const F = opts.trim ? SEATMAT.pyWing : SEATMAT.pyFabric, WG = opts.trim ? SEATMAT.pyWingB : SEATMAT.pyEar;
  const BH = M4.trs(x0, hy, hz, 0, PY.back);
  B.add(gLoft(cushionSecs(0.415, 0.50, 0.115, -0.06, { edge: 0.04, r: 0.035, crown: 0.012 }), lod ? 3 : 4), M4.trs(x0, 0.425, -0.30, 0, 3 * DEG), F);
  B.add(gRBox(0.415, 0.05, 0.48, 0.012, 1), M4.trs(x0, 0.335, -0.29), { c: '#3a3f4a', r: 0.5, l: LAYER.plastic });   // w10 (A): dark pan frame (py_37304, san_26)
  // QA r2: the centre of the back sits ~3 cm behind its old face between the bolsters (d 0.10 at y 0.34-0.52), and the top
  // blends into the headrest (overlapping sections instead of a step)
  loftAt(B, PYBACK, BH, F, lod ? 3 : 4);
  // ANA: the patterned back forms the rounded top of the seat level with the headrest and runs beside + behind the
  // wings (py_37301 right seat, py_37303 side view); the headrest stands ~2 cm proud of it [D]
  // sculpted side bolsters standing ~5 cm proud of the centre, narrow at the waist (~0.30 above the cushion), flaring
  // at the shoulders (py_37301 / 37303) [D]
  // w6 (B): neck step under the headrest (shoulder / headrest width 1.21 in py_37301), wider shoulder flare [D]
  for (const sd of [-1, 1]) {
    const BX = M4.mul(BH, M4.trs(sd * 0.185, 0, -0.03, -sd * 14 * DEG));
    loftAt(B, PYBOL, BX, F, lod ? 2 : 3);   // w9 (A + B): end under the ears
  }
  // w8 (B): curved hourglass seams sweeping in at the waist (py_37301), a darker welt ~2 mm proud of the back face [D]
  if (!lod) for (const sd of [-1, 1]) B.add(gTube([[0.14, 0.10, -0.088], [0.145, 0.30, -0.074], [0.125, 0.48, -0.063], [0.13, 0.60, -0.056]].map(([x, y, z]) => M4.point(BH, [sd * x, y, z])), 0.0025, 6), null, { c: '#5c6476', r: 0.95 });   // w9 (B): along the bolster edge, seam-shadow tone
  // thick rear shell that wraps round the back's sides (grey edge visible from the front)
  const zr = (y) => 0.105 + 0.014 * Math.sin(Math.PI * clamp(y / 0.84, 0, 1));
  // QA r2: the shell's rounded top rises above the headrest (to 0.97, headrest 0.91) and frames the screen from behind
  // (san_13 / san_24, py_37304); the top sections are rounded to half their depth
  // PY w2: the top is a large-radius arch that ends level with the headrest (0.925 vs 0.91), not a square board 6 cm
  // above it (py_37302 / 37303, san_13, alv_02; raters A + B) [D]
  // ANA: grey flank ~0.10 deep at the headrest, ~0.13 at the lumbar (py_37303), rear face rounding into the sides over
  // ~4 cm (py_37304); square-shouldered top so the wings never show from behind [D]
  // w6 (A + B): tapers above the lumbar to ~0.45 round the screen (shell / bezel 1.14-1.17 in py_37304 / san_26, was
  // 1.40) with a soft arched top (~6 cm corners) [D]
  // w7: rim ~3 cm above the fabric (san_13, py_37304); w8 (A + B): shoulders 0.48 so the wings beside the flap stay hidden
  // from behind, continuous soft arch (no crease between the top sections) [D]
  const ds = [[-0.04, 0.08, 0.525], [0.12, 0.09, 0.525], [0.34, 0.10, 0.52], [0.5, 0.11, 0.50], [0.68, 0.115, 0.48], [0.78, 0.11, 0.47],
    [0.84, 0.10, 0.475], [0.88, 0.095, 0.48], [0.905, 0.085, 0.48], [0.925, 0.07, 0.475], [0.938, 0.062, 0.455], [0.95, 0.05, 0.43],
    [0.958, 0.035, 0.38], [0.964, 0.02, 0.30], [0.967, 0.008, 0.20]];
  loftAt(B, ds.map(([y, d, w]) => SEC(y, w, d, zr(y) - d / 2 + 0.01, Math.min(d / 2 - 0.002, 0.045))), BH, SEATMAT.pyShell, lod ? 2 : 3);
  if (!lod) {
    // polishF (integration L13, medium): the back fabric meets the shell in a recessed joint (py_37301 / 37302, sanpy:
    // a dark line down both sides of every seat). A 4 mm mid-dark bead centred on the line where the back cushion's
    // outer face enters the shell surface, so only a soft sliver shows in the corner, not a strip on either face [D]
    const dsSecs = ds.map(([sy, d, w]) => SEC(sy, w, d));
    const shellSD = (y, x, z) => {
      const dd = secAt(dsSecs, y), r = Math.min(dd.d / 2 - 0.002, 0.045), zc = zr(y) - dd.d / 2 + 0.01;
      const qx = Math.abs(x) - (dd.w / 2 - r), qz = Math.abs(z - zc) - (dd.d / 2 - r);
      return Math.hypot(Math.max(qx, 0), Math.max(qz, 0)) + Math.min(Math.max(qx, qz), 0) - r;
    };
    // (the bolsters and ears stop ~5 mm short of the shell; the back cushion behind them is what enters it)
    // w18 (A high): an 8 mm square 16-step tube stood proud of the curved rim as a black cord up close -> 3 mm round,
    // 32 steps, sunk 1 mm into the shell, lighter tone
    for (const sd of [-1, 1]) for (const run of seamPath(PYBACK, M4.trs(0, 0, 0), sd, shellSD, 0.02, 0.9, 32))
        B.add(gTube(run.map(([x, y, z]) => M4.point(BH, [x, y, z + 0.001])), 0.0015, 6), null, PYGROOVE);   // ~770 tris a seat
  }
  // 6-way headrest with wings
  loftAt(B, [SEC(0.67, 0.40, 0.085, -0.008, 0.036), SEC(0.71, 0.37, 0.092, -0.012, 0.04), SEC(0.85, 0.37, 0.092, -0.012, 0.04), SEC(0.895, 0.35, 0.075, -0.006, 0.032), SEC(0.91, 0.31, 0.05, -0.002, 0.02)], BH, F, lod ? 3 : 4);
  for (const s of [-1, 1]) {
    // soft round pillow bolsters either side of the flap, ~0.10 wide x 0.25 tall with domed ends, bulging ~3.5 cm
    // forward of the flap (py_37301 / 37305)
    // ANA: each wing ~0.45 of the flap width (py_37301 85 / 185 px), ~0.21 tall with its top just under the flap fold,
    // facing inward ~30 deg (py_37302 foreground wings read as narrow ellipses) [D]
    // w8 (A + B): the pads sit BESIDE the flap, its edges lying over their inner rims (visible flap / headrest 0.60-0.70
    // in py_37301 / 37302 vs 0.38-0.45 with the pads in front); ~0.095 wide, 0.10 deep, 12 deg, tops ~1 cm under the fold [D]
    const WX = M4.mul(BH, M4.trs(s * 0.172, 0, -0.045, -s * 12 * DEG));   // pads bulge ~4 cm proud of the flap (py_37301)
    // w9 (A + B): short puffy ears with domed top and bottom ends, a gap above the bolsters (py_37301 / 37305) [D]
    // w11 (A): broader, flatter-fronted pillows (py_37305 left seat, san_14: ear wider than the bolster below, flat face) [D]
    loftAt(B, PYEAR, WX, WG, lod ? 2 : 3);
  }
  // navy leatherette flap over the headrest front + top, silver trim line low on the back shell (py_37303)
  // flap ~0.28 x 0.25, hanging a little below the wing pads (py_37301 seat C: 98 x 92 px on a 158 px headrest) [D]
  // w6 (A + B): 0.26 wide on the narrower headrest; the lower half hangs free and curls ~6 deg forward (py_37305) [D]
  // w7 (A + B): one thin sheet lying on the headrest face (front ~-0.058), lower half overlapping 1 cm and curling 3 deg;
  // the over-top piece set back so it does not overhang; flush stitched hem close to the flap colour [D]
  // w8: 0.28 wide (py_37301), one sheet (the w7 split showed a lit seam, A + B), edges rolled forward onto the
  // wing rims, over-top piece lower and set back below the shell rim (A + B) [D]
  const FL = M4.mul(BH, M4.trs(0, 0.905, -0.0605, 0, 1.5 * DEG));   // w8: one sheet hung from the fold, foot ~4 mm forward (no seam)
  B.add(gRBox(0.29, 0.225, 0.005, 0.0025, 1), M4.mul(FL, M4.trs(0, -0.1125, 0)), SEATMAT.pyCover);   // w9 (A): 0.68-0.905, visible h/w ~0.95 (py_37301 / 37302)
  // w11 (A + B): no over-top strip (from behind only the grey rim shows, py_37304 / san_14 / san_26)
  for (const s of [-1, 1]) B.add(gRBox(0.02, 0.2, 0.005, 0.0025, 1), M4.mul(BH, M4.trs(s * 0.152, 0.795, -0.066, -s * 25 * DEG)), SEATMAT.pyCover);
  if (!lod) {   // folded hem band ~22 mm with a tone-on-tone topstitch (py_37305)
    B.add(gBox(0.284, 0.014, 0.001), M4.mul(FL, M4.trs(0, -0.216, -0.0032)), { c: '#2a3560', r: 0.5, l: LAYER.leather });
    B.add(gBox(0.27, 0.0015, 0.001), M4.mul(FL, M4.trs(0, -0.208, -0.0038)), { c: '#2f3a62', r: 0.6 });
  }
  B.add(gBox(0.49, 0.008, 0.006), M4.mul(BH, M4.trs(0, 0.04, zr(0.04) + 0.022)), SEATMAT.pyTrim);
  // fold-up leg rest (stowed below the pan front)
  // ANA py_37301, top to bottom: cushion nose, a ~5 cm fabric skirt, a prominent dark fluted roller (~55 mm) standing
  // ~1.5 cm proud, then the fabric leg rest hanging almost vertically to ~0.04 [D]
  B.add(gLoft([SEC(0.0, 0.40, 0.05, 0, 0.018), SEC(0.25, 0.41, 0.06, 0, 0.022)], 3), M4.trs(x0, 0.03, -0.535, 0, -2 * DEG), F);
  B.add(gRBox(0.41, 0.05, 0.025, 0.01, 1), M4.trs(x0, 0.35, -0.535), F);                           // skirt
  // polishD (integration L9-L11): soft shadow band tucked behind the skirt under the cushion nose (py_37301 crease
  // L50-90, w16 A + B: a hard black line read drawn) and a dark gap under the hinge roller [D]
  B.add(gRBox(0.39, 0.024, 0.006, 0.003, 1), M4.trs(x0, 0.378, -0.543), { c: '#3a3f4c', r: 0.95 });
  B.add(gRBox(0.39, 0.012, 0.012, 0.004, 1), M4.trs(x0, 0.272, -0.548), PYGAP);
  B.add(gRBox(0.40, 0.02, 0.05, 0.008, 1), M4.trs(x0, 0.035, -0.53), SEATMAT.pyArm);            // leg-rest foot bar
  // dark-grey hinge roller across the top of the stowed leg rest under the cushion nose, dark side links down to the
  // foot bar (py_37301, san_17) [D]
  B.add(gCyl(0.032, 0.032, 0.405, lod ? 8 : 14), M4.trs(x0, 0.305, -0.562, 0, 0, Math.PI / 2), SEATMAT.pyArm);   // w9 (A): chunkier, proud (py_37301)
  if (!lod) for (const s of [-1, 1]) B.add(gCyl(0.034, 0.034, 0.012, 14), M4.trs(x0 + s * 0.205, 0.305, -0.562, 0, 0, Math.PI / 2), { c: '#2e3239', r: 0.5 });
  if (!lod) for (let k = 0; k < 6; k++) B.add(gBox(0.40, 0.002, 0.002), M4.trs(x0, 0.305 + 0.032 * Math.cos(-1.2 + k * 0.5), -0.562 - 0.032 * Math.sin(-1.2 + k * 0.5)), { c: '#2e3239', r: 0.6 });   // flutes (w5: soft grooves)
  if (!lod) for (const s of [-1, 1]) B.add(gRBox(0.015, 0.26, 0.03, 0.006, 1), M4.trs(x0 + s * 0.205, 0.17, -0.55), SEATMAT.pyArm);
  // w5 (A): darker rear face skin over the shell back (py_37304 rear shell / wall 0.41 vs 0.64-0.76 rendered; the side
  // faces already matched 0.62 / 0.63); rear fittings sit on it, 5 mm out [D]
  loftAt(B, [1, 2, 3, 4, 5, 6, 7].map((i) => SEC(ds[i][0], ds[i][2] - 0.075, 0.006, zr(ds[i][0]) + 0.011, 0.003)), BH, PYREAR, 2);
  if (lod) return;
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz + 0.005));
  if (!opts.noScreen) {
    // 15.6 in screen: black bezel 0.373 x 0.26 (active 0.345 x 0.195) in a grey housing ~0.44 x 0.30 that projects ~4 cm
    // and tilts top-back, its top just under the shell rim (py_37304: 1614 px/m; san_24) [D]
    const scr = (dz) => M4.mul(on(0.785, 0), M4.trs(0, 0, dz, 0, -6 * DEG));   // w9 (B): rim above the bezel ~0.19 of its height (py_37304 0.16-0.18)
    // ANA py_37304: bezel 0.376 x 0.263 set ~1 cm proud into the shell with a thin dark gap, framed by the shell rim
    // (~5 cm above it, 18 % of the bezel height) - no separate housing; placards 0.12 x 0.021, 1.7 cm under it [D]
    B.add(gRBox(0.405, 0.29, 0.014, 0.008, 1), scr(0.006), { c: '#3a3d42', r: 0.45, l: LAYER.plastic });   // w5: ~2 cm dark-grey frame (san_26) [D]
    B.add(gRBox(0.376, 0.263, 0.012, 0.008, 1), scr(0.016), { c: '#2a2c33', r: 0.4 });   // w12 (B): bezel #282932 in py_37304, not black; w13 (B): r 0.4 (gloss read black)
    B.add(gQuad(0.345, 0.194), scr(0.0235), SEATMAT.screen, atlasUV('screen'));
    for (const sx of [-0.113, 0.113]) B.add(gQuad(0.12, 0.022), on(0.63, 0.0115, sx), { c: '#e8e8e6', r: 0.6 });
  }
  {   // (row 25 backs too: seen from row 26)
    // w5 (A + B): moulded literature bucket right under the placards (san_20 / san_26, b_gf_a380): slim rim at the mouth,
    // the bucket bulging ~5 cm aft toward its rounded bottom, black mesh band across its lower front [D]
    const py0 = 0.27;   // w13 (A + B): lower, ~0.3 of plain shell under it was too much (san_26, b_san_20, san_14) [D]
    // w11 (B, san_26 / b_san_20 at ~1100 px/m): a dark recess under the placards; in it an open tray pocket whose grey front
    // rises at the sides and dips in a deep smile, contents showing above it, mesh across the lower bulge [D]
    // w12 (A): recess ~0.62 of the frame width (0.255) running down to ~2 cm above the shell's lower edge; the tray fills
    // its lower third (rim dip at ~30 % of the recess height), the mesh band follows the smile; a pale safety card [D]
    B.add(gRBox(0.255, 0.31, 0.003, 0.02, 1), on(py0 + 0.155, 0.0105), { c: '#3a3d43', r: 0.6, l: LAYER.plastic });
    B.add(gBox(0.21, 0.09, 0.006), on(py0 + 0.215, 0.014), { c: '#4a4e55', r: 0.55, l: LAYER.plastic });   // w13 (A): rear holder plate behind the tray (san_26)
    const BK = M4.mul(BH, M4.trs(0, py0 + 0.005, zr(py0 + 0.06) + 0.011));
    // tray front lofted across x so its grey top edge follows the smile (sections = columns, w = front height) [D]
    const rimY = (x) => 0.07 + 0.045 * ((x / 0.112) ** 2) ** 1.5, XS = [-0.112, -0.09, -0.055, 0, 0.055, 0.09, 0.112];
    B.add(gLoft(XS.map((x) => SEC(x, rimY(x), 0.045, 0.0225, 0.012, rimY(x) / 2)), 3), M4.mul(BK, M4.trs(0, 0, 0, 0, 0, Math.PI / 2)), PYREAR);
    B.add(gTube(XS.map((x) => M4.point(BK, [x * 0.985, rimY(x), 0.043])), 0.005, 6), null, PYREAR);   // smile rim
    B.add(gLoft(XS.slice(1, -1).map((x) => SEC(x, 0.035, 0.003, 0.0465, 0.001, rimY(x) - 0.03)), 1, [false, false]), M4.mul(BK, M4.trs(0, 0, 0, 0, 0, Math.PI / 2)),
      { c: '#25282c', r: 0.9, l: LAYER.grille });   // mesh band following the smile (san_26)
    B.add(gQuad(0.16, 0.07), M4.mul(BK, M4.trs(0, 0.10, 0.016, -6 * DEG)), { c: '#b4b3ae', r: 0.7 });   // w13 (A + B): wide leaflet, centred   // safety card in the mouth (san_26, b_san_20)
  }
  if (!opts.noScreen) {
    // gooseneck reading light: leaves the shell side at headrest height, arcs down + forward to a brushed-aluminium
    // head with a black lens at shoulder height; one per seat, on the console side (py_37305 / 37301, san_14)
    const sd = x0 > 0 ? -1 : 1, P = (x, y, z) => M4.point(BH, [sd * x, y, z]);
    // root: silver bullet on the shell side near the top pointing forward, round grey button ~8 cm below (py_37303 / 37305)
    const sil = { c: '#c9ccd0', r: 0.25, m: 0.9, l: LAYER.brushed };
    B.add(gCyl(0.015, 0.018, 0.06, 10), M4.mul(BH, M4.trs(sd * 0.24, 0.84, zr(0.84) - 0.035, 0, Math.PI / 2)), sil);
    B.add(gCyl(0.01, 0.01, 0.006, 10), M4.mul(BH, M4.trs(sd * 0.238, 0.76, zr(0.76) - 0.03, 0, 0, Math.PI / 2)), { c: '#c7c9cc', r: 0.4 });
    // w5 (B): stowed, the head hangs just ahead of the shell flank at wing height (py_37301 / 37303, san_26) [D]
    // w8 (A + B): slim arm running down along the shell flank in one smooth curve (Bezier, 10 points), head hanging
    // nearly vertical beside the wing with its lens facing forward and a dark end ring (py_37301 / 37305) [D]
    const C = [[0.24, 0.84, zr(0.84) - 0.065], [0.268, 0.78, -0.04], [0.255, 0.64, -0.11], [0.236, 0.59, -0.128]];   // w10 (A + B): longer hose down to a lower head
    const bz = (t) => [0, 1, 2].map((k) => (1 - t) ** 3 * C[0][k] + 3 * (1 - t) ** 2 * t * C[1][k] + 3 * (1 - t) * t * t * C[2][k] + t ** 3 * C[3][k]);
    B.add(gTube([...Array(10)].map((_, i) => P(...bz(i / 9))), 0.0095, 8), null, SEATMAT.black);   // w12 (A + B): hose ~0.5 of the head diameter
    // w10 (A + B): stowed heads near-vertical, ~mid-back, ~9 cm between neighbours (py_37301 / 37302 / 37303, san_26; the w9
    // splay copied py_37305, a pulled-out pose, and crossed the neighbours' heads into a V) [D]
    const hd = M4.mul(BH, M4.trs(sd * 0.232, 0.53, -0.13, 0, 12 * DEG));
    B.add(gCyl(0.017, 0.019, 0.11, 12), hd,   // head ~38 x 115 mm (alv_17) [D]
    { c: '#b4b8bd', r: 0.2, m: 0.95, l: LAYER.brushed });   // polished chrome
    B.add(gCyl(0.017, 0.017, 0.004, 12), M4.mul(hd, M4.trs(0, -0.056, 0)), { c: '#3a3d42', r: 0.5 });   // end ring
    B.add(gCyl(0.007, 0.007, 0.002, 10), M4.mul(hd, M4.trs(0, -0.03, -0.0192, 0, Math.PI / 2)), SEATMAT.black);   // lens facing forward
  }
  // PY w2: ONE fold-down footrest for the passenger behind (alv_05 / alv_06, san_10): two ribbed dark pads (~0.13 m) on a
  // common axle with silver end caps + centre hub, hung from the seat pan on one silver arm just off centre (w3; alv_06) [D]
  const fy = 0.30, fz = 0.13;
  for (const s of [-1, 1]) {
    B.add(gCyl(0.021, 0.021, 0.09, 12), M4.trs(x0 + s * 0.065, fy, fz, 0, 0, Math.PI / 2), SEATMAT.black);
    B.add(gCyl(0.023, 0.023, 0.014, 12), M4.trs(x0 + s * 0.117, fy, fz, 0, 0, Math.PI / 2), SEATMAT.frame);
  }
  for (const s of [-1, 1]) B.add(gRBox(0.018, 0.17, 0.02, 0.006, 1), M4.trs(x0 + s * 0.03, fy + 0.085, fz - 0.01), SEATMAT.frame);   // w5: two vertical arms (san_20) [V]
  B.add(gCyl(0.024, 0.024, 0.03, 12), M4.trs(x0, fy, fz, 0, 0, Math.PI / 2), SEATMAT.frame);
  if (!lod) for (const s of [-1, 1]) for (let k = -1; k <= 1; k++)                                     // pad ribs (w11: 3, under the pan)
    B.add(gBox(0.08, 0.003, 0.004), M4.trs(x0 + s * 0.065, fy + 0.02 * Math.cos(k * 0.35), fz + 0.02 * Math.sin(k * 0.35)), SEATMAT.hole);
  for (const s of [-1, 1]) {
    B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.trs(x0 + 0.03 * s, 0.488, -0.26), SEATMAT.buckle);
    B.add(gBox(0.045, 0.004, 0.16), M4.trs(x0 + 0.13 * s, 0.486, -0.19, s * 14 * DEG), { c: '#3c3f47', r: 0.7 });
  }
}
function pyUnit(n, lod = false, opts = {}) {
  const B = new Builder();
  const sp = PY.sp;
  const xs = []; for (let k = 0; k < n; k++) xs.push((k - (n - 1) / 2) * sp);
  const aisle = (k) => n === 4 && (k === 0 || k === 3);   // trim B on the centre block's aisle seats D / G (w11; window pairs A, py_37301)
  xs.forEach((x, k) => pySeat(B, x, lod, { ...opts, trim: aisle(k) }));
  const arms = []; for (let k = 0; k <= n; k++) arms.push((k - n / 2) * sp);
  arms.forEach((xa, k) => {
    const inner = k > 0 && k < n;
    // PY w2: console face ~0.12 (alv_08 / 09 two universal sockets side by side, py_37301 console / cushion 0.28-0.35;
    // raters measured 0.13-0.15 but the 0.5525 seat spacing then leaves < 0.42 of cushion) [D]
    const w = inner ? 0.135 : 0.07;   // ANA py_37301: console / cushion 0.31 -> 0.135 with a 0.415 cushion [D]
    if (inner) {
      // floor-standing console between seats: blue-grey body, silver trim round the top, cubbies + controls on
      // its front face, red life-vest tab at the bottom (py_37301)
      B.add(gRBox(w, 0.62, 0.52, 0.014, 2), M4.trs(xa, 0.31, -0.28), SEATMAT.pyArm);   // polishD: seg 2 so the edges catch a highlight
      B.add(gBox(w + 0.004, 0.012, 0.50), M4.trs(xa, 0.006, -0.28), PYGAP);   // polishD: dark foot on the carpet (py_37301) [D]
      if (!lod) for (const s of [-1, 1]) B.add(gBox(0.002, 0.006, 0.46), M4.trs(xa + s * (w / 2 + 0.0005), 0.40, -0.30), PYGAP);   // polishD: 6 mm side-panel split [D]
      // lid: light blue-grey with a groove along it (ANA py_37303 / 37301; the dark stitched lid is a later generation)
      loftAt(B, [SEC(0.62, w + 0.004, 0.46, -0.235, 0.02), SEC(0.645, w + 0.008, 0.47, -0.235, 0.025), SEC(0.665, w, 0.46, -0.235, 0.02)], M4.trs(xa, 0, 0), SEATMAT.pyArmPad, 2);   // w8 (A): reaches the nose
      // nose: short square light-grey block with two cups side by side (py_37303, alv_18) [D]
      // w5 (A + B): flush with the lid top (0.665), cups recessed as dark wells with a light rim (py_37303, san_16) [D]
      B.add(gRBox(w + 0.004, 0.022, 0.095, 0.008, 2), M4.trs(xa, 0.654, -0.495), SEATMAT.pyArmPad);
      if (!lod) for (const s of [-1, 1]) {
        B.add(gCyl(0.03, 0.03, 0.002, 16), M4.trs(xa + s * 0.032, 0.6655, -0.495), { c: '#8e9195', r: 0.5 });
        B.add(gCyl(0.026, 0.026, 0.003, 16), M4.trs(xa + s * 0.032, 0.667, -0.495), { c: '#3e4248', r: 0.7 });
      }
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
          // w9 (A): dark recessed side panel with the lit button strip and the tray-latch bar (py_37301) [D]
          B.add(gRBox(0.003, 0.15, 0.26, 0.02, 1), M4.trs(fx, 0.53, -0.30), { c: '#2c313d', r: 0.55, l: LAYER.plastic });   // w11 (A + B): ~0.6x pyArm
          B.add(gRBox(0.003, 0.11, 0.022, 0.006, 1), M4.trs(fx + s * 0.0015, 0.54, -0.455), SEATMAT.black);
          for (let k = 0; k < 4; k++) B.add(gBox(0.002, 0.008, 0.008), M4.trs(fx + s * 0.003, 0.505 + k * 0.022, -0.455), { c: '#6f8fd6', r: 0.4, e: 0.15 });
        }
      }
      B.add(gBox(w + 0.004, 0.006, 0.52), M4.trs(xa, 0.618, -0.275), SEATMAT.pyTrim);
      if (!lod) {
        // front face (alv_08 / alv_09, py_37306): two open moulded cubbies (upper larger) with a royal-blue triangle in
        // the corner, a black panel with two universal AC + USB sockets, then a lower block with the red life-vest tab
        // each cubby: a grey front plate standing ~2.5 cm proud over the lower 3/4, dark opening only above it
        for (const [y, h] of [[0.51, 0.10], [0.35, 0.10]]) {     // ANA py_37301: two equal pockets
          B.add(gBox(w - 0.026, 0.016, 0.004), M4.trs(xa, y + h / 2 - 0.012, -0.543), { c: '#16181c', r: 0.9 });   // polishF (L13): cubby mouths as dark recesses [D]
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
      B.add(gRBox(0.05, 0.64, 0.62, 0.025, 3), M4.trs(xa + o * 0.01, 0.32, -0.27), { c: '#575d67', r: 0.42, l: LAYER.plastic });
      B.add(gBox(0.054, 0.012, 0.60), M4.trs(xa + o * 0.01, 0.006, -0.27), PYGAP);   // polishD: dark foot on the carpet [D]   // w7: shroud/back 0.46 (py_37303, A) vs 0.82 (py_37301, B) -> between [D]
      // dark-grey arm cap running to the shroud front, where it rounds over and turns down ~6 cm (py_37301 right seat,
      // san_13); recessed darker panel on the shroud's outer face above the silver strip (py_37303)
      const cap = { c: '#50555d', r: 0.35, l: LAYER.plastic };   // glossy charcoal cap (py_37301 right seat)
      loftAt(B, [SEC(0.62, w, 0.52, -0.30, 0.02), SEC(0.648, w + 0.006, 0.53, -0.30, 0.028), SEC(0.668, w - 0.004, 0.52, -0.30, 0.02)], M4.trs(xa, 0, 0), cap, 2);
      B.add(gCyl(0.024, 0.024, w, 12), M4.trs(xa, 0.644, -0.556, 0, 0, Math.PI / 2), cap);
      B.add(gRBox(w, 0.06, 0.03, 0.012, 1), M4.trs(xa, 0.61, -0.565), cap);
      // ANA py_37303: silver strip ~0.25 above the floor, nearly level; lighter recessed panel from under the cap down to
      // it, large radius on its top-rear corner; darker base band with a D-shaped handle recess below the strip [D]
      if (!lod) {
        B.add(gRBox(0.006, 0.28, 0.50, 0.04, 1), M4.trs(xa + o * 0.033, 0.44, -0.30), { c: '#66707a', r: 0.45, l: LAYER.plastic });
        B.add(gRBox(0.004, 0.03, 0.10, 0.012, 1), M4.trs(xa + o * 0.034, 0.215, -0.33), SEATMAT.black);
        B.add(gRBox(0.004, 0.22, 0.58, 0.02, 1), M4.trs(xa + o * 0.0335, 0.12, -0.27), { c: '#4a5058', r: 0.5, l: LAYER.plastic });
      }
      B.add(gBox(0.006, 0.012, 0.58), M4.trs(xa + o * 0.037, 0.25, -0.27), SEATMAT.pyTrim);
    }
    if (inner && !lod) {
      // brushed-aluminium two-cell bottle bin on the console rear at knee height for the row behind (san_16 / 17 / 18)
      // PY w2: floor-standing silver bin, two square ~7 cm cups at the top (~0.44), white placard (alv_07, san_07) [D]
      B.add(gRBox(0.145, 0.37, 0.08, 0.012, 1), M4.trs(xa, 0.185, 0.045), { c: '#55595f', r: 0.4, m: 0.5, l: LAYER.brushed });   // w6 (A): dark housing, silver cups only (san_20)
      // w7 (B): chunky brushed cup block (~1 cm rims) on the dark housing, two dark wells (san_17 / san_20) [V]
      B.add(gRBox(0.145, 0.07, 0.08, 0.012, 1), M4.trs(xa, 0.405, 0.045), SEATMAT.pyBin);
      for (const s of [-1, 1]) B.add(gRBox(0.055, 0.065, 0.06, 0.01, 1), M4.trs(xa + s * 0.033, 0.41, 0.045), { c: '#5c6066', r: 0.45, m: 0.6 });
      B.add(gQuad(0.08, 0.025), M4.trs(xa, 0.395, 0.0855), { c: '#e6e6e2', r: 0.6 });   // placard on the silver front
    }
  });
  const W = n * sp;
  const legX = n >= 3 ? [-(W / 2 - 0.28), W / 2 - 0.28] : [-0.28, 0.28];
  for (const lx of legX) {
    // w3: pale champagne leg frames with a diagonal rear strut, seen from the row behind (san_05, alv_03; rater A) [A]
    const leg = { c: '#9a9ea4', r: 0.35, m: 0.8, l: LAYER.brushed };   // w6 (A): aluminium grey, not beige   // w4: light warm aluminium (A: champagne, B: cool alu)
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
    const x0 = (k - (n - 1) / 2) * sp, FF = n === 4 && (k === 0 || k === 3) ? SEATMAT.pyWing : SEATMAT.pyFabric;
    B.add(gRBox(0.48, 0.115, 0.50, 0.045, 1), M4.trs(x0, 0.425, -0.30, 0, 3 * DEG), FF);
    const BH = M4.trs(x0, PY.hinge[0], PY.hinge[1], 0, PY.back);
    B.add(gRBox(0.48, 0.68, 0.12, 0.04, 1), M4.mul(BH, M4.trs(0, 0.34, -0.02)), FF);
    B.add(gRBox(0.505, 0.88, 0.05, 0.015, 1), M4.mul(BH, M4.trs(0, 0.40, 0.095)), SEATMAT.pyShell);
    B.add(gRBox(0.39, 0.21, 0.09, 0.035, 1), M4.mul(BH, M4.trs(0, 0.80, -0.012)), FF);
    B.add(gBox(0.30, 0.17, 0.01), M4.mul(BH, M4.trs(0, 0.80, -0.062)), SEATMAT.pyCover);
    B.add(gQuad(0.345, 0.194), M4.mul(BH, M4.trs(0, 0.755, 0.121)), SEATMAT.screen, atlasUV('screen'));
  }
  for (let k = 0; k <= n; k++) {
    if (k === opts.win) B.add(gBox(0.05, 0.07, 0.34), M4.trs((k - n / 2) * sp, 0.605, -0.30), SEATMAT.pyArm);
    else B.add(gBox(k > 0 && k < n ? 0.135 : 0.07, 0.34, 0.44), M4.trs((k - n / 2) * sp, 0.49, -0.27), SEATMAT.pyArm);
  }
  return B.build();
}
