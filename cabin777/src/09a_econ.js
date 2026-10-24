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
const econPan = (k, n, rot) => [SEATMAT.yFabric, SEATMAT.yFabricD, SEATMAT.yFabricC, SEATMAT.yFabric, SEATMAT.yFabricB][(k * 3 + n * 5 + (rot || 0) + 2) % 5];
// w11 A: tick on ~half the backs (y_47300 tick / fleck / tick / fleck, y_47301 mostly tick) -> 6-cycle, tick x3 [D]
// w17 A: the q15 hero row now reads tick / fleck / tick / fleck as in y_47300; fleck on a third of the backs (the commonest
// in service, question 9), tick a third, mosaic and diamond a sixth each [D]
const econFab = (k, n, rot) => [SEATMAT.yFabricC, SEATMAT.yFabricD, SEATMAT.yFabric, SEATMAT.yFabricD, SEATMAT.yFabric, SEATMAT.yFabricB][(k * 7 + n * 3 + (rot || 0)) % 6];
// econ w10 gap analysis (silhouette): the back was a rounded-rectangle slab - two vertices across a dead-flat 0.43 face and
// 2-3.6 cm corners, where y_47306 / 47300 show ~1.2 cm of crown and rolled side edges 2.6-4.4 cm wide (6-10 % of the seat
// width) [D]. Same loft as gLoft, but each ring's front (-z) face is subdivided and crowned, and the side roll is fuller.
function econCrownLoft(secs, segC, crownAt) {
  const K = 8, g = { p: [], n: [], u: [], i: [] };
  const rings = secs.map((s) => {
    const r = Math.max(0.0005, Math.min(Math.max(s.r, 0.045), s.w / 2 - 1e-3, s.d / 2 - 1e-3));
    const pts = rrectPts(s.w, s.d, r, segC, s.x || 0, s.z || 0), out = [], q = segC + 1, c = crownAt(s.y);
    for (let k = 0; k < pts.length; k++) {
      out.push(pts[k]);
      if (k === 3 * q - 1) {           // straight front edge from corner 3 (180-270 deg) to corner 4 (270-360 deg)
        const a = pts[k], b = pts[k + 1];
        for (let j = 1; j < K; j++) { const t = j / K, u = 2 * t - 1; out.push([a[0] + (b[0] - a[0]) * t, a[1] - c * (1 - u * u)]); }
      }
    }
    return out;
  });
  const n = rings[0].length;
  for (let j = 0; j < secs.length; j++) for (let i = 0; i < n; i++) { g.p.push(rings[j][i][0], secs[j].y, rings[j][i][1]); g.n.push(0, 1, 0); g.u.push(i / n, j / (secs.length - 1)); }
  for (let j = 0; j < secs.length - 1; j++) for (let i = 0; i < n; i++) { const a = j * n + i, b = j * n + ((i + 1) % n); g.i.push(a, b, b + n, a, b + n, a + n); }
  computeNormals(g);
  let dot = 0;                                              // side normals outward (as gLoft)
  for (let i = 0; i < n; i++) { const k = i * 3; dot += g.n[k] * (g.p[k] - (secs[0].x || 0)) + g.n[k + 2] * (g.p[k + 2] - (secs[0].z || 0)); }
  if (dot < 0) for (let k = 0; k < g.n.length; k++) g.n[k] = -g.n[k];
  const top = secs.length - 1, c0 = g.p.length / 3, st = secs[top];
  g.p.push(st.x || 0, st.y, st.z || 0); g.n.push(0, 1, 0); g.u.push(0.5, 0.5);
  for (const [x, z] of rings[top]) { g.p.push(x, st.y, z); g.n.push(0, 1, 0); g.u.push(0, 0); }
  for (let i = 0; i < n; i++) g.i.push(c0, c0 + 1 + ((i + 1) % n), c0 + 1 + i);
  return fixWinding(g);
}
const ECON_PAN = { ...SEATMAT.yFabric, c: photoBase('#44507c', 'y_tick') };
function econSeat(B, x0, lod, opts = {}) {
  const [hy, hz] = ECON.hinge;
  const F = opts.fab || SEATMAT.yFabric;
  const BH = M4.trs(x0, hy, hz, 0, ECON.back);
  // pan: the diamond seats carry the diamonds on the back only, the pan is the tick weave (y_47302 middle seat) [V]
  // w7 A + B: pans mix independently of the backs (y_47300: fleck back / tick pan, tick / diamond, fleck / mosaic) [V]
  let PF = opts.panFab || (F === SEATMAT.yFabricB ? SEATMAT.yFabric : F);
  if (PF === SEATMAT.yFabric) PF = ECON_PAN;   // w10-w12 A: tick pans pale / grey (B/R 1.52-1.55 vs 1.74-1.90 in y_47300 / 47303)
  // w14 gap: a deep ~5 cm fabric bullnose that tucks under to a narrower base (y_47302), set in a grey tray 5 cm behind
  // the pan front (the wide white tray showed as a 1.5-2 cm light lip under every pan) [D]
  const ps = cushionSecs(0.43, 0.47, 0.095, -0.05, { edge: 0.05, r: 0.05, crown: 0.01 });
  ps[0] = { ...ps[0], w: 0.39, d: 0.41, z: 0.02 };
  ps[1] = { ...ps[1], y: ps[0].y + 0.03 };
  ps.splice(1, 0, { ...ps[1], y: ps[0].y + 0.012, w: 0.415, d: 0.45, z: 0.008 });
  B.add(gLoft(ps, lod ? 3 : 4), M4.trs(x0, 0.415, -0.28, 0, 3 * DEG), PF);
  B.add(gRBox(0.39, 0.03, 0.40, 0.012, 1), M4.trs(x0, 0.35, -0.25), { c: '#7d8187', r: 0.5 });
  // back: rises above the headrest cushion to a rounded top (y_47306 all three seats, y_47301, sanspotter 13;
  // back length ~0.87 from the pan crease, y_47302 right seat) [D]
  B.add(econCrownLoft([SEC(0.0, 0.40, 0.07, -0.005, 0.02), SEC(0.04, 0.425, 0.09, -0.012), SEC(0.16, 0.43, 0.108, -0.024, 0.036), SEC(0.30, 0.43, 0.095, -0.014, 0.036),
    SEC(0.46, 0.43, 0.086, -0.006, 0.034), SEC(0.58, 0.425, 0.076, 0.0, 0.03), SEC(0.70, 0.422, 0.07, 0.004, 0.028), SEC(0.818, 0.415, 0.062, 0.006, 0.026),
    SEC(0.838, 0.403, 0.062, 0.010, 0.026), SEC(0.853, 0.37, 0.058, 0.014, 0.024), SEC(0.858, 0.334, 0.052, 0.018, 0.02), SEC(0.866, 0.30, 0.044, 0.02, 0.016), SEC(0.874, 0.25, 0.034, 0.024, 0.012)], lod ? 3 : 4, (y) => 0.012 * clamp((0.685 - y) / 0.08, 0.35, 1)), BH, F);   // w10 gap: crowned, crown eased behind the headrest; w14: the top rolls over the shell cap; w17 B: upper back 1 cm wider over the hood sides
  // w6 B: the back is ~0.44 wide at headrest height round a narrower cushion (y_47300: a margin of back fabric shows
  // round the pad); w6 A: it ends 12 mm under the shell cap (the caps were coplanar at 0.868 and z-fought) [D]
  // rear shell: a slim lower panel (tray + pockets) under a deep sculpted hood that wraps the screen and caps the top of
  // the seat - from behind only a thin blue rim shows at the hood's sides (sanspotter 15 / 25-28, y_47305); hood ~0.37
  // wide (glass 0.85-0.89 of it), ~0.03 m of shell above the bezel, ~0.04 m proud of the tray face (y_47303 side view);
  // the skirt reaches below the pan top so no pan fabric shows under it (w2 B); the tray band is narrower (0.345) than the
  // hood and the pocket zone, so the hood overhangs it (sanspotter 15, w3 B) [D]
  // [y, rear-face z, depth, width, corner r]
  const RS = [[-0.12, 0.066, 0.03, 0.44, 0.018], [-0.06, 0.07, 0.03, 0.446, 0.018], [0.1, 0.078, 0.03, 0.446, 0.018], [0.2, 0.08, 0.032, 0.44, 0.018],
    [0.24, 0.081, 0.034, 0.345, 0.016], [0.44, 0.086, 0.04, 0.345, 0.016], [0.49, 0.106, 0.06, 0.37, 0.015], [0.53, 0.12, 0.08, 0.376, 0.015], [0.80, 0.122, 0.09, 0.374, 0.015],
    [0.835, 0.114, 0.09, 0.374, 0.025], [0.855, 0.10, 0.092, 0.365, 0.03], [0.866, 0.086, 0.058, 0.30, 0.02]];   // w8 B: thinner cap from the front; w14 A + B: cap 8 mm aft and under the fabric roll (y_47300: fabric to the top, no white rim head-on)
  // w6 A + B: flat hood face with tight corners, 0.40 wide -> bezel 0.79 of it (y_47305 0.81, sans 15 / 22 0.86-0.87;
  // the 0.03 radius curled the sides away, 0.89-0.93); the top row caps the back top 7 mm above it, its front face ~1.5 cm
  // behind the fabric front so a ~1 cm navy rim shows from behind (sans 15 / 22, fr57325 124234) [D]
  // econ w5 (A high): the shell's rounded top rolls forward over the back top, so from behind only a ~1 cm navy rim shows
  // (sans 15, fr57325 124234: no fabric above the white hood) [V]
  // w15 / w16 B: hood ~2.6 cm narrower (0.374; bezel ring 0.88 of it, y_47305 0.81-0.87), so its white sides hide behind the
  // ~0.41 back fabric head-on (3-3.5 cm bands vs ~1 cm in y_47300) [D]
  const rs = (y, j) => { let k = 1; while (k < RS.length - 1 && RS[k][0] < y) k++; const a = RS[k - 1], b = RS[k], t = clamp((y - a[0]) / (b[0] - a[0]), 0, 1); return a[j] + (b[j] - a[j]) * t; };
  const zr = (y) => rs(y, 1);
  loftAt(B, RS.map(([y, z, d, w, r]) => SEC(y, w, d, z - d / 2, r)), BH, SEATMAT.yShell, lod ? 2 : 3);
  // 6-way headrest: a separate cushion ~0.2 tall, ~0.065 proud of the back, with rounded wing ends (y_47306 / 47302 /
  // 47300, w2 A + B); w5 A: wing ends bulge to soft domes mid-height [D]
  // w6 B: narrower pad (0.355) with an undercut at its foot, so a shadow line and a margin of back fabric outline it
  // (y_47300); w6 A: each cushion in a different weave from its back (y_47306: diamond back / mosaic pad, tick / fleck,
  // mosaic / diamond); fleck backs keep fleck pads (y_47300 seats 2 / 4) [V]
  // w9 B: fleck backs keep fleck pads (a 4x crop of y_47300 seats 2 / 4 shows fine speckle; the w8 mosaic pads were wrong)
  // w14 gap: the whole headrest 2.5 cm higher, so the back rises ~3 cm above the cover fold (y_47300 0-1 cm, y_47301 ~3,
  // y_47302 ~4; only y_47306 shows the lowered ~5.5 cm) [D]
  // w17 B: fleck backs carry a tick pad and tick backs a fleck pad (y_47300 seats 1-4)
  const econHead = (F) => F === SEATMAT.yFabricB ? SEATMAT.yFabricC : F === SEATMAT.yFabricC ? SEATMAT.yFabricB : F === SEATMAT.yFabricD ? SEATMAT.yFabric : SEATMAT.yHead;
  const HF = econHead(F);
  // w7 A + B: a U-shaped pad ~0.39 wide (0.90-0.96 of the back in y_47306 / 47302, sans 13) - a centre panel behind the
  // cover and two round wing bolsters ~2 cm proud of it at both ends; 0.025 lower so the back rises ~5.5 cm above the
  // cover fold (y_47306 0.053-0.073, y_47301 ~0.06; the fold showed above the hood from behind) [D]
  loftAt(B, [SEC(0.605, 0.30, 0.03, -0.02, 0.012), SEC(0.62, 0.33, 0.085, -0.048, 0.04), SEC(0.695, 0.34, 0.09, -0.05, 0.042), SEC(0.77, 0.335, 0.088, -0.049, 0.04), SEC(0.79, 0.31, 0.065, -0.043, 0.03), SEC(0.8, 0.27, 0.04, -0.038, 0.02)], BH, HF, lod ? 3 : 4);
  for (const sx of [-0.163, 0.163]) loftAt(B, [SEC(0.61, 0.045, 0.06, -0.035, 0.02, sx), SEC(0.625, 0.06, 0.105, -0.056, 0.029, sx), SEC(0.7, 0.066, 0.12, -0.062, 0.032, sx), SEC(0.77, 0.064, 0.115, -0.06, 0.031, sx), SEC(0.79, 0.055, 0.09, -0.052, 0.026, sx), SEC(0.802, 0.04, 0.05, -0.042, 0.018, sx)], BH, HF, lod ? 2 : 4);
  // slate leatherette cover lying on the cushion front, wrapped ~3 cm over its top and hanging ~2.5 cm below it (the
  // flap hangs past the cushion onto the back, y_47306 right seat) [D]
  // one piece: plate on the cushion front, a fold overlapping both it and the cushion top, a hem tucking back (w3 B)
  // w6 B: 0.255 wide (y_47300 0.23 / y_47306 0.73 of the pad); the hem hangs nearly flat (at -20 deg it read as a shelf)
  // w8 B: a soft flap, not a tablet - the plate bows ~4 mm forward mid-height, the fold is a thin strip bent over the
  // pad top, with a stitch line above the hem (y_47301, y_47306)
  // w20 (gap19): bow cut 4 -> ~1.5 mm (the bulge mirrored the ceiling as a crinkle head-on); w20 B: ~2.5 mm (flat, it mirrored as one broad band)
  // w10 A + B: the flap hangs ~3 cm below the pad (y_47306 / sans 13: 24-29 % of the pad height), its foot tipped a
  // little forward, and rolls round the pad top in a soft radius (was a hard bevel)
  loftAt(B, [SEC(0.575, 0.255, 0.005, -0.12, 0.002), SEC(0.61, 0.256, 0.005, -0.111, 0.002), SEC(0.655, 0.257, 0.005, -0.1025, 0.002), SEC(0.705, 0.258, 0.005, -0.103, 0.002), SEC(0.755, 0.257, 0.005, -0.1025, 0.002), SEC(0.791, 0.255, 0.005, -0.0985, 0.002)], BH, SEATMAT.yCover, lod ? 1 : 2);
  loftAt(B, [SEC(0.789, 0.255, 0.006, -0.0985, 0.003), SEC(0.8, 0.255, 0.012, -0.094, 0.005), SEC(0.807, 0.255, 0.02, -0.086, 0.007), SEC(0.81, 0.255, 0.028, -0.073, 0.008), SEC(0.807, 0.255, 0.02, -0.06, 0.006)], BH, SEATMAT.yCover, lod ? 1 : 3);
  if (lod) return;
  // small ANA mark in the flap's lower corner (viewer's right from the front, y_47306); w5 B: a thin grey logotype, not a sticker
  // w19 A: the hem, stitch and mark were quads 6-9 mm behind the plate (its foot tips forward since w10) and never showed;
  // now thin bands lofted over the plate, following its slope (plate centre z -0.12 at y 0.575 -> -0.111 at 0.61)
  const cz = (y) => -0.12 + (y - 0.575) / 0.035 * 0.009;
  loftAt(B, [SEC(0.577, 0.253, 0.0064, cz(0.577), 0.002), SEC(0.596, 0.254, 0.0064, cz(0.596), 0.002)], BH, { c: '#3a4264', r: 0.45 }, 1);   // w21 A + B: hem 1.15x the face vs 1.55-1.6 in y_47306 -> lighter, with a rolled foot; w20 A: dark (a light hem + stitch read as a screen chin head-on); w9 A: stitched hem band ~10 % of the cover height (y_47306)
  B.add(gTube([[-0.1265, 0, 0], [0.1265, 0, 0]], 0.004, 8), M4.mul(BH, M4.trs(0, 0.577, cz(0.577) - 0.0005)), { c: '#3a4264', r: 0.45 });   // rolled foot catching the light (y_47306)
  loftAt(B, [SEC(0.5965, 0.24, 0.0072, cz(0.5965), 0.001), SEC(0.5977, 0.24, 0.0072, cz(0.5977), 0.001)], BH, { c: '#3e4562', r: 0.6 }, 1);   // stitch line, light thread (b_ss_14)
  loftAt(B, [SEC(0.5985, 0.01, 0.0068, cz(0.5985), 0.0005, -0.105), SEC(0.6025, 0.01, 0.0068, cz(0.6025), 0.0005, -0.105)], BH, { c: '#3a4058', r: 0.5 }, 1);   // small ANA mark, viewer's right (y_47306)
  // w11 B: contact darkening where the back fabric tucks into the shell sides (y_47306 dark crease) and along the strip
  for (const sx of [-1, 1]) loftAt(B, [SEC(0.05, 0.014, 0.003, -0.048, 0.001, sx * 0.199), SEC(0.55, 0.014, 0.003, -0.043, 0.001, sx * 0.203), SEC(0.80, 0.014, 0.003, -0.032, 0.001, sx * 0.2)], BH, { c: '#283052', r: 0.95 }, 1);   // w12 A + B: soft crease, not a drawn line
  // w9 A: a ~0.12 m centre strip in a contrasting weave runs from the pad top to the back top (headrest track cover,
  // y_47306 right / middle seats) [V]
  loftAt(B, [SEC(0.803, 0.12, 0.004, -0.0295, 0.002), SEC(0.818, 0.12, 0.004, -0.0275, 0.002), SEC(0.842, 0.115, 0.004, -0.0235, 0.002)], BH, F === SEATMAT.yFabricD ? F : { ...SEATMAT.yFabric, c: photoBase('#4b5577', 'y_tick') }, 1);   // w16 A: no tick patch on fleck backs   // w11 B: darker tick / chevron weave, not diamond (y_47306)
  const on = (y, dz = 0, dx = 0) => M4.mul(BH, M4.trs(dx, y, zr(y) + dz));   // on the rear face
  // navy pillow resting on the cushion at the crease, ~0.35 x 0.24 (y_47300 aspect 0.65-0.7; sans 14 ~0.8 of the pan) [D]
  // w5 B: soft pillow, not a bevelled slab - a squashed sphere with pinched corners, slightly concave sides and a ~7 cm
  // dome that thins to a seamed rim (y_47300 all four pillows, sans 13) [D]
  if (opts.pillow !== false) {
    const g = gSphere(1, 24, 12);
    for (let k = 0; k < g.p.length; k += 3) {
      const sx = g.p[k + 1], sy = -g.p[k], sz = g.p[k + 2], l = Math.hypot(sx, sz) || 1;   // w11: sphere poles at the thin side tips (a pole on the face read as a tuft)
      const X = sx * (1 + 0.35 * sz * sz) * (0.92 + 0.08 * l), Z = sz * (1 + 0.35 * sx * sx) * (0.92 + 0.08 * l);   // w10 gap: smooth squircle (|t|^0.45 creased the middle)
      // w6: wider (0.39 = 0.8 of the pan, y_47300 0.81 / sans 14 0.83), bow-tie outline with pinched corners
      const pull = 1 + 0.15 * Math.abs(X * Z);                                  // w9 A: corners pulled out (y_47300)
      g.p[k] = 0.165 * X * (1 - 0.06 * (1 - Z * Z)) * pull; g.p[k + 2] = 0.135 * Z * (1 - 0.1 * (1 - X * X) - (Z > 0 ? 0.04 * (1 - X * X) : 0)) * pull;   // w14 gap: concave top edge   // w10 B: waist eased (read as a bone)
      g.p[k + 1] = sy * (0.006 + 0.046 * Math.pow(Math.max(0, 1 - Math.pow(l, 3)), 0.6));   // thins to the seamed rim; w14 gap: ~10 cm full (p90/p10 1.3 vs 2.2-2.8 in y_47300 read as a board)
    }
    computeNormals(g);
    // w20 (gap19): 0.33 x 0.27 (0.77 of the back, y_47300 matched view; 0.93 read as one dark strip), 4 cm higher and 4 deg
    // more upright so its foot just meets the pan instead of sinking into the crease [D]
    B.add(g, M4.mul(BH, M4.trs(0, 0.19, -0.115, 0, -80 * DEG)), SEATMAT.yPillow);
    // w19 A + B: a ~4 mm piped seam round the rim (y_47300 pillows), the same outline law at l = 1 [D]
    const rim = []; for (let i = 0; i <= 48; i++) {
      const t = i / 48 * 2 * Math.PI, sx = Math.cos(t), sz = Math.sin(t), X = sx * (1 + 0.35 * sz * sz), Z = sz * (1 + 0.35 * sx * sx), pull = 1 + 0.15 * Math.abs(X * Z);
      rim.push([0.165 * X * (1 - 0.06 * (1 - Z * Z)) * pull, 0, 0.135 * Z * (1 - 0.1 * (1 - X * X) - (Z > 0 ? 0.04 * (1 - X * X) : 0)) * pull]);
    }
    B.add(gTube(rim, 0.0035, 6, false), M4.mul(BH, M4.trs(0, 0.19, -0.115, 0, -80 * DEG)), { ...SEATMAT.yPillow, c: '#343e5c' });   // w20 A + B: pillow-coloured piping (a darker ring read as an outline)
  }
  // life-vest pouch: dark saucer-shaped holder under the pan front with a red pull strap hanging from its rim (y_47302:
  // ~0.15-0.18 m discs under each seat) [D]
  B.add(gCyl(0.085, 0.075, 0.035, 14), M4.trs(x0, 0.215, -0.34, 0, -12 * DEG), { c: '#2b2e33', r: 0.6 });
  B.add(gBox(0.02, 0.10, 0.004), M4.trs(x0 + 0.015, 0.15, -0.425, 0, 8 * DEG), { c: '#c8252b', r: 0.5 });
  if (!opts.noScreen) {
    // 13.3 in touchscreen (0.294 x 0.166) in a black glass border 0.316 x 0.205 set flush in the hood face, top ~0.03
    // below the hood's rounded top (y_47305: 600 x 390 px at 1905 px/m, colour (29,26,38); 55 px of shell above) [D]
    const SY = 0.7275;
    B.add(gRBox(0.328, 0.217, 0.004, 0.008, 1), on(SY, -0.0005), { c: '#5a6072', r: 0.35 });     // w9 A: ~4 mm lighter grey frame ring round the glass (y_47305)
    B.add(gRBox(0.316, 0.205, 0.004, 0.006, 1), on(SY, 0.001), { c: '#2a2932', r: 0.12 });   // w8 A: glossy dark-grey glass (y_47305), not flat black; w9 A #16161c rendered vs #1d1926
    B.add(gQuad(0.294, 0.166), on(SY + 0.004, 0.0035), SEATMAT.screen, atlasUV('screen'));   // w9 B: chin 11 % of the glass height (y_47305)
    // IFE handset docked in a dark recess 0.04 below the bezel (y_47305, sanspotter 15/27): dark-navy pill with an oval
    // key, a D-pad ring + OK, +/- rockers, a round key and four colour keys in a diamond (blue top, green left, red
    // right, yellow bottom) [D]
    const HY = 0.577, hz = (y, dz, dx) => M4.mul(on(y, dz, dx), M4.trs(0, 0, 0, 0, Math.PI / 2));
    B.add(gRBox(0.20, 0.054, 0.01, 0.024, 1), on(HY, 0.0), { c: '#15171d', r: 0.5 });   // w11 A + B: handset 0.39 -> ~0.5 of the bezel width (y_47305)
    // black handset filling ~0.76 of the dock, with the separate release key at the dock's left end (w3 A) [D]
    const HX = 0.012;
    B.add(gRBox(0.155, 0.044, 0.012, 0.02, 1), on(HY, 0.004, HX), { c: '#1a1b20', r: 0.35 });
    const key = (dx, dy, r, c, h = 0.003) => B.add(gCyl(r, r, h, r > 0.008 ? 16 : 8, true), hz(HY + dy, 0.0105, dx), { c, r: 0.35, e: /^#(3a|40|e0)/.test(c) ? 0.25 : 0 });
    key(-0.085, 0, 0.006, '#3a3f52', 0.004);
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
    B.add(gQuad(0.059, 0.026), on(0.425, 0.0183, -0.10), { c: '#9a9ea4', r: 0.5 });     // w7 A: label border
    for (const dx of [-0.016, 0, 0.016]) B.add(gQuad(0.009, 0.011), on(0.425, 0.0189, -0.10 + dx), { c: '#8e939b', r: 0.5 });   // w6 B pictograms (sans 15); w11 A + B: black squares + red read as a 3-port box -> faint grey
    // off-white mushroom coat-hook knob near the top of the hood side (sans 22) [V]; side unconfirmed (questions_econ 11)
    B.add(gCyl(0.014, 0.011, 0.014, 14), M4.mul(on(0.70, -0.015, 0.207), M4.trs(0, 0, 0, 0, 0, Math.PI / 2)), SEATMAT.yShell);   // w13 A + B: lower / aft, out of the front view
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
    // w8 A + B: the card's white pictogram half shows above the flap under the purple header (sans 20 / 21)
    B.add(gRBox(0.21, 0.06, 0.003, 0.002, 1), on(0.165, 0.016, 0.035), { c: '#f4f4f6', r: 0.6 });
    B.add(gQuad(0.21, 0.014), on(0.188, 0.0177, 0.035), { c: '#5b3a8e', r: 0.6 });
    B.add(gQuad(0.10, 0.005), on(0.188, 0.0179, 0.035), { c: '#ffffff', r: 0.6 });
    for (let k = 0; k < 5; k++) B.add(gQuad(0.024, 0.017), on(0.168, 0.0176, -0.035 + k * 0.035), { c: '#8a8d94', r: 0.6 });
    B.add(gLoft([SEC(-0.035, 0.26, 0.012, 0, 0.005), SEC(0.0, 0.27, 0.022, 0.004, 0.008), SEC(0.035, 0.26, 0.012, 0, 0.005)], 2), on(0.115, 0.022), { c: '#bdc0c4', r: 0.5, l: LAYER.plastic });
    B.add(gCyl(0.004, 0.004, 0.27, 8), M4.mul(on(0.15, 0.032), M4.trs(0, 0, 0, 0, 0, Math.PI / 2)), { c: '#a9acb1', r: 0.5 });
    // w5 A + B: the net is a see-through black mesh reaching ~0.02 past the flap each side, with a ruched elastic top
    // (sans 23); no alpha here, so a lighter mesh tone lets the grille pattern read as holes [D]
    // w7 A + B: a dark back panel behind a lattice of thin strands, so the net reads as see-through mesh (sans 20 / 23)
    // w8 A + B: two bowed mesh pouches either side of a grey centre strap, each with a pleated grey hem (sans 20 / 22 / 23)
    B.add(gQuad(0.31, 0.07), on(0.05, 0.011), { c: '#121316', r: 0.9 });
    for (const px of [-0.08, 0.08]) {
      // w9 A + B: a fine net (~6 mm cells, sans 20) of thin strands on quads; dark pleated hems just under the flap
      for (let i = 0; i < 24; i++) { const u = i / 23; B.add(gQuad(0.0012, 0.068), on(0.05, 0.016 + 0.008 * Math.sin(u * Math.PI), px - 0.07 + u * 0.14), { c: '#34363c', r: 0.8 }); }
      for (let j = 0; j < 11; j++) B.add(gQuad(0.14, 0.0012), on(0.018 + j * 0.006, 0.022), { c: '#34363c', r: 0.8 });
      for (let k = 0; k < 9; k++) B.add(gCyl(0.006, 0.006, 0.0165, 8), M4.mul(on(0.075, 0.024 + 0.002 * (k % 2), px - 0.066 + k * 0.0165), M4.trs(0, 0, 0, 0, 0, Math.PI / 2)), { c: '#4a4c52', r: 0.9, l: LAYER.fabric });
    }
    B.add(gBox(0.02, 0.078, 0.004), on(0.047, 0.026), { c: '#3a3c42', r: 0.7 });   // w9 B: charcoal strap
  }
  // footrest for the passenger behind: two off-white hanger arms clamped to the rear spreader tube, carrying ribbed
  // aluminium pedals (y_47304)
  // w5 B: the hangers come down at the seat centreline, ~0.07 apart (sans 23), and land on the joint between the two
  // pedals (y_47304), each one bowed flat arm [V]
  if (opts.footrest !== false) {
    for (const s of [-1, 1]) {
      const hx = x0 + s * 0.035;
      B.add(gRBox(0.035, 0.03, 0.04, 0.008, 1), M4.trs(hx, 0.30, -0.10), SEATMAT.frame);
      // w6 A + B: one smooth bowed bar per hanger (four boxes read as beads; y_47304, sans 23) [D]
      loftAt(B, [SEC(0.115, 0.046, 0.022, -0.012, 0.009), SEC(0.13, 0.045, 0.022, -0.03, 0.009), SEC(0.18, 0.042, 0.022, -0.064, 0.009), SEC(0.24, 0.039, 0.022, -0.088, 0.009), SEC(0.30, 0.036, 0.022, -0.10, 0.009)], M4.trs(hx, 0, 0), SEATMAT.arm, 3);
      // brushed pedal (~0.15 each, w4 B) with longitudinal grooves ~5 mm apart and a dark cap at its outer end (y_47304)
      const px = x0 + s * 0.085;
      B.add(gRBox(0.15, 0.02, 0.05, 0.008, 1), M4.trs(px, 0.11, 0.0), { c: '#9a9ea4', m: 0.8, r: 0.35, l: LAYER.brushed });
      for (let g = -3; g <= 3; g++) B.add(gQuad(0.138, 0.0018), M4.trs(px, 0.1205, g * 0.006, 0, -Math.PI / 2), { c: '#6d7178', m: 0.7, r: 0.5 });
      B.add(gBox(0.01, 0.022, 0.052), M4.trs(px + s * 0.077, 0.11, 0.0), { c: '#4a4e55', r: 0.5 });
    }
    B.add(gBox(0.02, 0.024, 0.054), M4.trs(x0, 0.11, 0.0), { c: '#9a9ea4', m: 0.8, r: 0.35, l: LAYER.brushed });   // shared joint block, silver (w6 A, y_47304)
  }
  // belt: silver tongue one side, light-grey plastic buckle cover the other (y_47303); w5 A: the webbing drapes across the
  // pan from the side creases and the latch sits at mid-pan (y_47302 / 47301 / 47303) [V]
  for (const s of [-1, 1]) {
    B.add(s < 0 ? gRBox(0.05, 0.012, 0.035, 0.005, 1) : gRBox(0.05, 0.014, 0.04, 0.006, 1), M4.trs(x0 + 0.03 * s, 0.478, -0.31), s < 0 ? SEATMAT.buckle : { c: '#cfd2d6', r: 0.4 });
    B.add(gBox(0.045, 0.004, 0.25), M4.trs(x0 + 0.115 * s, 0.474, -0.195, s * 38 * DEG), s < 0 ? SEATMAT.yBelt : { ...SEATMAT.yBelt, c: '#262c48' });   // w10 B: teal tongue strap, navy buckle strap (y_47303)
  }
  // pan-front stiffener in the light-grey structure colour (y_47300 / 47302: fabric pan fronts over light-grey structure,
  // no black bar) - QA r2, was black
  B.add(gRBox(0.30, 0.04, 0.10, 0.01, 1), M4.trs(x0, 0.31, -0.42), { c: '#5d6168', r: 0.5 });   // w14 gap: under the pan overhang, in its shadow
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
  xs.forEach((x, k) => econSeat(B, x, lod, { ...opts, fab: econFab(k, n, opts.rot), panFab: econPan(k, n, opts.rot) }));
  const arms = []; for (let k = 0; k <= n; k++) arms.push((k - n / 2) * sp);
  arms.forEach((xa, k) => {
    const armTilt = M4.mul(M4.trs(xa, 0.66, -0.08, 0, -4 * DEG), M4.trs(0, -0.66, 0.08));
    // sculpted off-white armrest (thick, rounded, slightly drooping nose) on a rear pivot post (y_47302 / 47303)
    // w5 B: a slim ~5.5 cm bar (y_47303 28 px on a 0.33 m / 160 px arm; fr57325 124108) with a drooping nose [D]
    loftAt(B, [SEC(0.625, 0.046, 0.32, -0.24, 0.016), SEC(0.64, 0.054, 0.34, -0.24, 0.024), SEC(0.668, 0.052, 0.335, -0.24, 0.024), SEC(0.68, 0.044, 0.32, -0.235, 0.018)], armTilt, SEATMAT.arm, 3);   // w11 B: nose ~2 cm down (y_47303)
    // w8 A: no separate knuckle block on the nose (the loft's rounded end carries it, y_47303)
    B.add(gRBox(0.05, 0.008, 0.24, 0.004, 1), M4.mul(armTilt, M4.trs(0, 0.678, -0.235)), SEATMAT.armPad);
    if (!opts.noScreen) {
      // w19 A + B: regular rows carry one C moulding, open at the front - the arm, a broad sweep down under its rear end and
      // a ~5.5 cm lower bar running forward at pan-top height to a rounded nose, ~6 cm under the arm (y_47303 near / right
      // aisle seats, sans b_ss_18); no front bracket, paddle or aisle-end panel (those are the exit-row arms, y_47302) [D]
      // w20 A + B: the lower member is a flat moulded plate (~2 x 6 cm; at the block ends a deep ~11 cm panel, b_ss_18
      // 1.75x the arm, y_47301), not a round rail - lofted in y, its z extent shaped into the rounded nose [D]
      const cp = [[0, 0.636, -0.078], [0, 0.60, -0.074]];
      for (let i = 1; i <= 8; i++) { const t = i / 8, u = 1 - t; cp.push([0, u * u * 0.60 + 2 * u * t * 0.52 + t * t * 0.50, u * u * -0.074 + 2 * u * t * -0.08 + t * t * -0.17]); }
      const ct = gTube(cp, 0.028, 12); for (let k = 0; k < ct.p.length; k += 3) ct.p[k] *= 0.38; computeNormals(ct);   // w21 B: 2.1 cm, as the plate (3.1 cm stepped at the joint)
      B.add(ct, M4.trs(xa, 0, 0), SEATMAT.arm);
      const zs = (y, z0, z1, w) => SEC(y, w, z0 - z1, (z0 + z1) / 2, 0.009);
      const end = k === 0 || k === arms.length - 1;
      loftAt(B, end ? [zs(0.415, -0.13, -0.33, 0.024), zs(0.43, -0.12, -0.375, 0.024), zs(0.46, -0.10, -0.398, 0.024), zs(0.50, -0.08, -0.40, 0.024), zs(0.525, -0.08, -0.392, 0.024), zs(0.538, -0.09, -0.37, 0.024), zs(0.543, -0.145, -0.33, 0.02)]
        : [zs(0.48, -0.14, -0.365, 0.02), zs(0.488, -0.13, -0.383, 0.022), zs(0.51, -0.125, -0.392, 0.022), zs(0.532, -0.13, -0.383, 0.022), zs(0.54, -0.14, -0.365, 0.02)], M4.trs(xa + (end ? (k === 0 ? -0.013 : 0.013) : 0), 0, 0), SEATMAT.arm, 3);
    } else {
      // front end: one continuous grey bracket from under the arm nose down past the pan, with a pivot ring at pan height;
      // the white paddle hangs from it (y_47302 / 47303; w2 B: was a ball on a stick) [D]
      loftAt(B, [SEC(0.30, 0.036, 0.032, -0.37, 0.014), SEC(0.46, 0.04, 0.036, -0.385, 0.016), SEC(0.62, 0.04, 0.036, -0.395, 0.016)], M4.trs(xa, 0, 0), SEATMAT.armPost, 2);   // w5 B: slimmer
      if (!lod) {
        B.add(gCyl(0.02, 0.02, 0.064, 12), M4.trs(xa, 0.46, -0.39, 0, 0, Math.PI / 2), { c: '#9ea3a9', r: 0.4 });
        B.add(gCyl(0.009, 0.009, 0.066, 8), M4.trs(xa, 0.46, -0.39, 0, 0, Math.PI / 2), { c: '#3a3e45', r: 0.4 });
      }
      // w14 gap: J-shaped support - a beam rising diagonally from the rear, then running forward ~7.5 cm under the arm into
      // the front bracket (y_47303; the raked blade read as a box on posts) [D]
      const beam = { ...SEATMAT.armPost, c: '#b4b9c2' };
      // w16 A + B: one smooth swept moulding (two straight pieces + an elbow read as an open bracket with a strut)
      const jp = []; for (let i = 0; i <= 12; i++) { const t = i / 12, u = 1 - t; jp.push([0, u * u * 0.625 + 2 * u * t * 0.505 + t * t * 0.512, u * u * -0.085 + 2 * u * t * -0.215 + t * t * -0.375]); }
      const jt = gTube(jp, 0.028, 12); for (let k = 0; k < jt.p.length; k += 3) jt.p[k] *= 0.45; computeNormals(jt);   // w17 A: a flat ~2.5 x 5.6 cm moulding, not a round tube
      B.add(jt, M4.trs(xa, 0, 0), beam);
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
    B.add(gRBox(0.43, 0.10, 0.47, 0.05, 1), M4.trs(x0, 0.41, -0.28, 0, 3 * DEG), econPan(k, n, rot) === SEATMAT.yFabric ? ECON_PAN : econPan(k, n, rot));
    const BH = M4.trs(x0, ECON.hinge[0], ECON.hinge[1], 0, ECON.back);
    B.add(gRBox(0.42, 0.86, 0.08, 0.035, 1), M4.mul(BH, M4.trs(0, 0.43, -0.005)), f);   // same mix as econUnit
    B.add(gRBox(0.446, 0.62, 0.045, 0.015, 1), M4.mul(BH, M4.trs(0, 0.25, 0.058)), SEATMAT.yShell);
    B.add(gRBox(0.40, 0.37, 0.12, 0.015, 1), M4.mul(BH, M4.trs(0, 0.665, 0.062)), SEATMAT.yShell);    // screen hood under the back top (w5; w6 0.40, tight corners; w14 gap: top 0.85, its white cap showed on every far back)
    B.add(gRBox(0.39, 0.2, 0.11, 0.04, 1), M4.mul(BH, M4.trs(0, 0.70, -0.058)), f === SEATMAT.yFabricB ? SEATMAT.yFabricC : f === SEATMAT.yFabricC ? SEATMAT.yFabricB : f === SEATMAT.yFabricD ? SEATMAT.yFabric : SEATMAT.yHead);
    B.add(gBox(0.255, 0.235, 0.01), M4.mul(BH, M4.trs(0, 0.6825, -0.11)), SEATMAT.yCover);
    B.add(gQuad(0.316, 0.205), M4.mul(BH, M4.trs(0, 0.7275, 0.1245)), SEATMAT.bezel);
    B.add(gQuad(0.294, 0.166), M4.mul(BH, M4.trs(0, 0.7275, 0.1265)), SEATMAT.screen, atlasUV('screen'));
  }
  for (let k = 0; k <= n; k++) B.add(gBox(0.048, 0.05, 0.30), M4.trs((k - n / 2) * sp, 0.64, -0.235), SEATMAT.arm);
  return B.build();
}
