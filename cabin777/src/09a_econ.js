// ------------------------------------------------------------------
// Economy seat (Recaro) for the ANA 777-300ER - see REFERENCE777.md
// Seat-local frame and shared materials / helpers (SEATMAT, SEC, loftAt, cushionSecs) live in 09_seats.js.
// New materials for this product: Object.assign(SEATMAT, {...}) at the top of this file (loaded after 09_seats.js).
// ------------------------------------------------------------------
// ================= ECONOMY (Recaro, 17 in, 13.3 in screen, 6-way headrest, footrest) =================
const ECON = { back: 13 * DEG, hinge: [0.47, -0.075], sp: 19 * IN, backS: 0.955 };   // w48 (w47b-3 / w47a-1): at the landmark-matched q17 camera the back tops and the forward row's screens sit 27-30 px (~6 cm) above y_47303 while the arms and windows match within 2-5 px; head-on q15 reads ~4 % tall for its width -> the whole back 4.5 % shorter in its own up axis (top 1.32 -> ~1.28 m) [D]
// ANA mixes four fabric patterns seat by seat (y_47302: mosaic / diamond / ticks left to right; y_47306: diamond / ticks /
// mosaic; y_47300 front row: tick / fleck / tick / fleck). econ w5 (A high): the petal fleck is the commonest (sans 13 / 14,
// fr57325 124108) -> ~40 % fleck, 20 % each of the others [D]
// w25 (w24a-1 / w24b-3, matched q15): hero row pans read mosaic / diamond / fleck / tick vs y_47300 tick / tick / diamond /
// mosaic -> list reordered (same mix) [V]
const econPan = (k, n, rot) => [SEATMAT.yFabricD, SEATMAT.yFabricB, SEATMAT.yFabric, SEATMAT.yFabricC, SEATMAT.yFabric][(k * 3 + n * 5 + (rot || 0) + 2) % 5];
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
const ECON_PAN = { ...SEATMAT.yFabric, c: photoBase('#4d5472', 'y_tick') };   // w39: kept (w38b-6: the w38 pan darkening came from the 9624e60 lighting edit, not econ); w38 (w37a-4 / w37b-2): B/R 1.99 vs 1.74-1.82 -> less blue;   // w33 (w33a-5): L92-97 vs 75-83, B/R 1.62-1.69 vs 1.75-1.82 -> darker, bluer; w27 (w26b-4): B/R 1.61-1.67 vs 1.74-1.81 -> a touch bluer; w26 (w25a-5 / w25b-2): L69-74 vs 77-91, still blue; w25 (w24b-4): tick pans B/R 2.17 vs ~1.8 -> less blue
// w25 (w24a-1 / w24b-3): the diamond pan read as a bold field of light stars head-on (L99-101 vs 74 in y_47300) -> darker
const ECON_PAN_B = { ...SEATMAT.yFabricB, c: photoBase('#44496b', 'y_diamond'), l: LAYER.yDiamondPan };   // w33 (w33a / w33b): B/R 1.66-1.67 vs 1.87 -> halfway back; w32 (w31a-4 / w31b-2): washed out (L85 vs 75, stars gone) -> gain 0.9 (PHOTO_GAIN 34), base back down; w32a-3: B/R 1.95 vs 1.81 -> #464a68   // w31 (w30a-5 / w30b-3): the 0.7x star band left separate stars on a dark ground -> L +8   // w28 (w27a-1 / w27b-1, high): photoBase lifts for the full-gain tile mean (2c = 0.4); at gain g the mean is 1 - 0.6 g, so the pan rendered ~1.8x too light (L107 vs 74) -> #4e5676 x (1 / (1 - 0.6 x 0.8)) / 2.5 x 0.88 in linear = #414862 (gain 0.8); w27 (w26a-1 / w26b-1): own layer at 0.45 gain (stars bright 0.21 vs 0.09); w26b: B/R 1.61 grey -> #4e5676; w26 (w25a-1 / w25b-1): B/R 2.27-2.41 vs 1.81
// w30 (w29a-6): tick backs alternate a light heather pad (y_47300 seat D, L102-107, few flecks) and a dark fleck pad
// (seat F, L57; L126 / bright share 0.06 in the matched q15 box ; a 3x crop shows a light cloudy mottle -> the diamond tile on a light base; the mosaic tile read busy, a plain weave read as plastic); every tick-back pad was one mid fleck (L75-81) [D]
const ECON_HEAD_L = { ...SEATMAT.yFabricB, c: photoBase('#65739f', 'y_diamond'), l: LAYER.yDiamondPan }, ECON_HEAD_D = { ...SEATMAT.yHead, c: photoBase('#454f73', 'y_fleck') };   // w31 (w30a-6 / w30b-10): the light pad was blotchy close up -> the pan's lower-gain layer 34, base x0.77 in linear for its brighter mean; w32: x1.13 for gain 0.9, x0.92 (w31a-3)
const econHead = (F, k = 0, rot = 0) => F === SEATMAT.yFabricB ? SEATMAT.yFabricC : F === SEATMAT.yFabricC ? SEATMAT.yFabricB : F === SEATMAT.yFabricD ? SEATMAT.yFabric
  : (((k >> 1) + rot) % 2 ? ECON_HEAD_D : ECON_HEAD_L);
// w30 (w29b-6, w27b-6): the mosaic pan read light and blue in q15 (L98 B/R 1.86 vs y_47300 87 / 1.72) -> its own base [D]
const ECON_PAN_C = { ...SEATMAT.yFabricC, c: photoBase('#474e69', 'y_mosaic') };   // w38 (w37a-4 / w37b-2): B/R 2.06 vs 1.79 -> less blue;   // w36 (w35a-2): still the lightest pan (L103 vs 82) -> -8 %;   // w34a-2: L108 B/R 1.55 vs y_47300 82 / 1.80 (part of the gap is the lighting lift) -> darker, bluer
const ECON_PLATE = { ...SEATMAT.armPost, c: '#55575d' };   // w46 (gap w46-3)   // w32 (w31a-2 / w31b-5): #9a9b9f still a light second bar (L114-133 vs ~76)
const econPanMat = (F) => F === SEATMAT.yFabric ? ECON_PAN : F === SEATMAT.yFabricB ? ECON_PAN_B : F === SEATMAT.yFabricC ? ECON_PAN_C : F;
function econSeat(B, x0, lod, opts = {}) {
  const [hy, hz] = ECON.hinge;
  const F = opts.fab || SEATMAT.yFabric;
  const BH = M4.trs(x0, hy, hz, 0, ECON.back, 0, 1, ECON.backS);
  // pan: the diamond seats carry the diamonds on the back only, the pan is the tick weave (y_47302 middle seat) [V]
  // w7 A + B: pans mix independently of the backs (y_47300: fleck back / tick pan, tick / diamond, fleck / mosaic) [V]
  let PF = opts.panFab || (F === SEATMAT.yFabricB ? SEATMAT.yFabric : F);
  PF = econPanMat(PF);   // w10-w12 A: tick pans pale / grey (B/R 1.52-1.55 vs 1.74-1.90 in y_47300 / 47303)
  // w14 gap: a deep ~5 cm fabric bullnose that tucks under to a narrower base (y_47302), set in a grey tray 5 cm behind
  // the pan front (the wide white tray showed as a 1.5-2 cm light lip under every pan) [D]
  // w30 (w29a-4): dark 11-23 px gaps between neighbouring pans in q15 where y_47300's pans abut under the arms -> 2.5 cm
  // wider (edge 3 mm inside the arm's lower plate) [D]
  // w33 (gap33-1 / w33a-1, sans 13 / 23, y_47302): the zone under the pan is near-black (q15 luma 32-50 vs 19-23); the
  // light tray, stiffener and spreader tubes showed as three grey bars under every pan -> dark tray tucked back [V]
  // w33 (gap33-2 / w33a-3): the pan was a 5 cm roll on all four sides, opening a ~0.13 m V between neighbours (the dark
  // joints, 8-13 px vs 2-3 in y_47300); sans 13 / 18 / y_47302 show a ~3.5 cm front roll over a near-vertical fabric face,
  // square in plan, the sides abutting under the arms -> 0.47 wide, side roll 1.6 cm, front roll 3.2 cm, 5 deg; w33b-2: the
  // front read ~9.5 cm thick vs ~7 in y_47302 -> 8.5 cm, bottom 1.5 cm higher, top unchanged [D]
  const ex = 0.01, ez = 0.032, py0 = -0.04, ph = 0.085, ps = [{ y: py0, w: 0.45, d: 0.42, z: 0.02, r: 0.02 }, { y: py0 + 0.012, w: 0.474, d: 0.456, z: 0.008, r: 0.026 }, { y: py0 + 0.03, w: 0.478, d: 0.47, r: 0.03 }];   // w34a-1 / w34b-4: joints still 4-8 px (top 0.438 on a 0.4826 pitch) -> 0.478, side roll 1.0 cm
  for (let k = 0; k <= 5; k++) { const th = k / 5 * Math.PI / 2, c = 1 - Math.cos(th); ps.push({ y: py0 + ph - ez + ez * Math.sin(th) + 0.01 * Math.sin(th) * (k === 5 ? 1 : 0.6), w: 0.478 - 2 * ex * c, d: 0.47 - 2 * ez * c, r: 0.03 + ex * c * 0.6 }); }
  B.add(gLoft(ps, lod ? 3 : 4), M4.trs(x0, 0.415, -0.28, 0, 5 * DEG), PF);
  B.add(gRBox(0.40, 0.02, 0.39, 0.008, 1), M4.trs(x0, 0.364, -0.25), { c: '#2c2f35', r: 0.8 });   // w41 (w40b-2): 2 cm further back, matt (a hard black lip under every pan front in e11)
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
    [0.24, 0.081, 0.034, 0.345, 0.016], [0.44, 0.086, 0.04, 0.345, 0.016], [0.478, 0.087, 0.04, 0.345, 0.016], [0.492, 0.117, 0.074, 0.372, 0.012], [0.53, 0.12, 0.08, 0.376, 0.015], [0.80, 0.122, 0.09, 0.374, 0.015],
    [0.835, 0.114, 0.09, 0.374, 0.025], [0.855, 0.10, 0.092, 0.365, 0.03], [0.866, 0.086, 0.058, 0.30, 0.02]];   // w46 (gap w46-1): the 9 cm ramp under the hood -> a 3 cm shelf over 1.4 cm, so it casts the dark band under the handset (y_47303 / y_47305); w8 B: thinner cap from the front; w14 A + B: cap 8 mm aft and under the fabric roll (y_47300: fabric to the top, no white rim head-on)
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
  const HF = econHead(F, opts.hk || 0, opts.rot || 0);
  // w7 A + B: a U-shaped pad ~0.39 wide (0.90-0.96 of the back in y_47306 / 47302, sans 13) - a centre panel behind the
  // cover and two round wing bolsters ~2 cm proud of it at both ends; 0.025 lower so the back rises ~5.5 cm above the
  // cover fold (y_47306 0.053-0.073, y_47301 ~0.06; the fold showed above the hood from behind) [D]
  // w49 (w48a-1 / w48b-1, medium, both): in y_47303 the cover drapes over a convex cushion and the wing rolls bulge forward
  // and down; the q17 cover read 84 x 90 px vs 106 x 110 -> the cushion 2 cm fuller in front at mid-height, 1.5 cm taller at
  // the top (q15 cover top 12 px low vs y_47300) and the wings 2 cm further down [D]
  loftAt(B, [SEC(0.59, 0.30, 0.03, -0.02, 0.012), SEC(0.605, 0.33, 0.09, -0.05, 0.04), SEC(0.68, 0.34, 0.11, -0.06, 0.045), SEC(0.75, 0.338, 0.104, -0.057, 0.044), SEC(0.795, 0.322, 0.075, -0.045, 0.032), SEC(0.815, 0.27, 0.04, -0.038, 0.02)], BH, HF, lod ? 3 : 4);
  for (const sx of [-0.163, 0.163]) loftAt(B, [SEC(0.585, 0.045, 0.05, -0.03, 0.02, sx), SEC(0.602, 0.06, 0.095, -0.051, 0.03, sx), SEC(0.69, 0.068, 0.118, -0.061, 0.036, sx), SEC(0.77, 0.066, 0.11, -0.058, 0.034, sx), SEC(0.802, 0.056, 0.08, -0.046, 0.027, sx), SEC(0.817, 0.04, 0.0416, -0.0378, 0.018, sx)], BH, HF, lod ? 2 : 4);   // w49: 2 cm fuller in front, 2.5 cm lower foot, 1.5 cm higher top   // w45 (w44a-1 / w43a-3): front face ~2 cm aft, back face kept (the wings hid the q17 cover: y_47303 shows the flap in front of them)
  // slate leatherette cover lying on the cushion front, wrapped ~3 cm over its top and hanging ~2.5 cm below it (the
  // flap hangs past the cushion onto the back, y_47306 right seat) [D]
  // one piece: plate on the cushion front, a fold overlapping both it and the cushion top, a hem tucking back (w3 B)
  // w6 B: 0.255 wide (y_47300 0.23 / y_47306 0.73 of the pad); the hem hangs nearly flat (at -20 deg it read as a shelf)
  // w8 B: a soft flap, not a tablet - the plate bows ~4 mm forward mid-height, the fold is a thin strip bent over the
  // pad top, with a stitch line above the hem (y_47301, y_47306)
  // w20 (gap19): bow cut 4 -> ~1.5 mm (the bulge mirrored the ceiling as a crinkle head-on); w20 B: ~2.5 mm (flat, it mirrored as one broad band)
  // w10 A + B: the flap hangs ~3 cm below the pad (y_47306 / sans 13: 24-29 % of the pad height), its foot tipped a
  // little forward, and rolls round the pad top in a soft radius (was a hard bevel)
  // w36 (w35a-1 / w35b-1, both medium): with the height right the cover reads 1.15-1.17x too wide head-on (0.46 of the
  // pitch vs 0.37-0.41 in y_47300) -> 0.22 wide (sans 13 hangs a wider cover, so not the full 0.215); hem, foot, stitch, mark follow [D]
  // w44 (w43a-3 / w42a-4, medium, both raters): in the q17 / y_47303 side view the cover is a large flap standing off the
  // pad (~120 x 95 px); ours lay 2 cm behind the wing bolsters' front and showed as a 15-40 px strip -> the plate hangs
  // forward from the fold, its foot ~1 cm proud of the wings, and the wing bolsters 2 cm shallower in front (w45) [V]
  // w49 (w48a-1 / w48b-1): a convex drape over the fuller cushion, foot 1 cm lower (2 cm read h/w ~0.93 head-on in q15 vs ~0.7-0.8) and ~1.5 cm more proud, fold 1.5 cm higher [D]
  const CPL = [[0.615, -0.149], [0.638, -0.1445], [0.665, -0.1395], [0.70, -0.1325], [0.745, -0.1235], [0.78, -0.1135], [0.806, -0.0995]];
  loftAt(B, CPL.map(([y, z], i) => SEC(y, i === 0 || i === CPL.length - 1 ? 0.22 : 0.222, 0.005, z, 0.002)), BH, SEATMAT.yCover, lod ? 1 : 2);   // w45 (w44a-1): back to 0.22 (0.232 read 77-78 px head-on vs 71-72 in y_47300)
  // w35 (question 21-23; w34b-1 / w33b-7, every round): head-on h / w 0.85-0.88 vs ~0.7 in y_47300 AND in the real head-on
  // sans 13 near seat (both end level with the pad foot) -> the plate foot 3 cm higher; hem, stitch and mark move with it [V]
  // w25 (w24b-1, matched q15): head-on h / w 0.92-0.94 vs 0.70-0.77 in y_47300, hang ~4 cm vs 2-3 cm (b_ss_13) -> the plate
  // starts 2 cm higher and is 0.245 wide; hem, foot, stitch and mark move up with it [D]
  loftAt(B, [SEC(0.804, 0.232, 0.006, -0.0995, 0.003), SEC(0.815, 0.232, 0.012, -0.095, 0.005), SEC(0.822, 0.232, 0.02, -0.087, 0.007), SEC(0.825, 0.232, 0.028, -0.073, 0.008), SEC(0.822, 0.232, 0.02, -0.06, 0.006)], BH, SEATMAT.yCover, lod ? 1 : 3);   // w49: fold 1.5 cm higher
  if (lod) return;
  // small ANA mark in the flap's lower corner (viewer's right from the front, y_47306); w5 B: a thin grey logotype, not a sticker
  // w19 A: the hem, stitch and mark were quads 6-9 mm behind the plate (its foot tips forward since w10) and never showed;
  // now thin bands lofted over the plate, following its slope (plate centre z -0.12 at y 0.575 -> -0.111 at 0.61)
  const cz = (y) => { let i = 1; while (i < CPL.length - 1 && CPL[i][0] < y) i++; const [y0, z0] = CPL[i - 1], [y1, z1] = CPL[i]; return z0 + (z1 - z0) * (y - y0) / (y1 - y0); };   // w49: follows the drape   // w44: follows the plate brought forward
  loftAt(B, [SEC(0.617, 0.218, 0.0064, cz(0.617), 0.002), SEC(0.636, 0.219, 0.0064, cz(0.636), 0.002)], BH, { c: '#2a3049', r: 0.6 }, 1);   // w22 A + B: a light band read as a screen chin head-on -> dark, the lift from the rolled foot only; w21 A + B: hem 1.15x the face vs 1.55-1.6 in y_47306 -> lighter, with a rolled foot; w20 A: dark (a light hem + stitch read as a screen chin head-on); w9 A: stitched hem band ~10 % of the cover height (y_47306)
  B.add(gTube([[-0.104, 0, 0], [0.104, 0, 0]], 0.0045, 8), M4.mul(BH, M4.trs(0, 0.617, cz(0.617) + 0.001)), { c: '#4a5478', r: 0.38 });   // w22 B: inside the plate edge, 1 mm back (a <= 2 px lip head-on)   // rolled foot catching the light (y_47306)
  loftAt(B, [SEC(0.6365, 0.205, 0.0072, cz(0.6365), 0.001), SEC(0.6377, 0.205, 0.0072, cz(0.6377), 0.001)], BH, { c: '#3e4562', r: 0.6 }, 1);   // stitch line, light thread (b_ss_14)
  loftAt(B, [SEC(0.6385, 0.01, 0.0068, cz(0.6385), 0.0005, -0.088), SEC(0.6425, 0.01, 0.0068, cz(0.6425), 0.0005, -0.088)], BH, { c: '#3a4058', r: 0.5 }, 1);   // small ANA mark, viewer's right (y_47306)
  // w11 B: contact darkening where the back fabric tucks into the shell sides (y_47306 dark crease) and along the strip
  for (const sx of [-1, 1]) loftAt(B, [SEC(0.05, 0.014, 0.003, -0.048, 0.001, sx * 0.199), SEC(0.55, 0.014, 0.003, -0.043, 0.001, sx * 0.203), SEC(0.80, 0.014, 0.003, -0.032, 0.001, sx * 0.2)], BH, { c: '#283052', r: 0.95 }, 1);   // w12 A + B: soft crease, not a drawn line
  // w9 A: a ~0.12 m centre strip in a contrasting weave runs from the pad top to the back top (headrest track cover,
  // y_47306 right / middle seats) [V]
  loftAt(B, [SEC(0.816, 0.12, 0.004, -0.0285, 0.002), SEC(0.826, 0.12, 0.004, -0.0272, 0.002), SEC(0.842, 0.115, 0.004, -0.0235, 0.002)], BH, F === SEATMAT.yFabricD ? F : { ...SEATMAT.yFabric, c: photoBase('#4b5577', 'y_tick') }, 1);   // w16 A: no tick patch on fleck backs   // w11 B: darker tick / chevron weave, not diamond (y_47306)
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
      const pull = 1 + 0.45 * Math.pow(Math.abs(X * Z), 3);   // w27 (w26a-4): softer, the w26 1.5 power read as a bone close up; w26 (w25b-5): dog-ear corners                                  // w9 A: corners pulled out (y_47300)
      g.p[k] = 0.165 * X * (1 - 0.05 * (1 - Z * Z)) * pull; g.p[k + 2] = 0.11 * Z * (1 - 0.12 * (1 - X * X) - (Z > 0 ? 0.02 * (1 - X * X) : 0)) * pull;   // w31 (w30a-4 / w30b-4): bow-tie waist on both long edges (y_47300 3x crop: ~10 % of the height)   // w14 gap: concave top edge   // w10 B: waist eased (read as a bone)
      g.p[k + 1] = sy * (0.006 + 0.054 * Math.pow(Math.max(0, 1 - Math.pow(l, 3)), 0.6));   // w32 (w31a-4 / w31b-4): 0.42 read flatter (p90/50 1.12 vs 1.24-1.73) -> 0.6; waist 0.12, corner pull 0.45   // w30 (w29a-5 / w29b-5): fuller dome, crisper dog-ears (pull ^3 x 0.3)   // thins to the seamed rim; w14 gap: ~10 cm full (p90/p10 1.3 vs 2.2-2.8 in y_47300 read as a board)
    }
    computeNormals(g);
    // w20 (gap19): 0.33 x 0.27 (0.77 of the back, y_47300 matched view; 0.93 read as one dark strip), 4 cm higher and 4 deg
    // more upright so its foot just meets the pan instead of sinking into the crease [D]
    // w25 (w24b-2 / w24a-5, matched q15): height 0.64 of the back width vs 0.46, ~4 cm too high -> half-height 0.11, 3.5 cm
    // lower and tipped back 6 deg so it rests on the pan (y_47300) [D]
    B.add(g, M4.mul(BH, M4.trs(0, 0.155, -0.112, 0, -74 * DEG)), SEATMAT.yPillow);
    // w19 A + B: a ~4 mm piped seam round the rim (y_47300 pillows), the same outline law at l = 1 [D]
    const rim = []; for (let i = 0; i <= 48; i++) {
      const t = i / 48 * 2 * Math.PI, sx = Math.cos(t), sz = Math.sin(t), X = sx * (1 + 0.35 * sz * sz), Z = sz * (1 + 0.35 * sx * sx), pull = 1 + 0.45 * Math.pow(Math.abs(X * Z), 3);
      rim.push([0.165 * X * (1 - 0.05 * (1 - Z * Z)) * pull, 0, 0.11 * Z * (1 - 0.12 * (1 - X * X) - (Z > 0 ? 0.02 * (1 - X * X) : 0)) * pull]);
    }
    B.add(gTube(rim, 0.0022, 6, false), M4.mul(BH, M4.trs(0, 0.155, -0.112, 0, -74 * DEG)), { ...SEATMAT.yPillow, c: '#363c55' });   // w27 (w26b-5): pillow-coloured (a darker tube still read as a rim)   // w26 (w25b-5): thinner, darker (read as a light ring)   // w20 A + B: pillow-coloured piping (a darker ring read as an outline)
  }
  // life-vest pouch: dark saucer-shaped holder under the pan front with a red pull strap hanging from its rim (y_47302:
  // ~0.15-0.18 m discs under each seat) [D]
  // w33 (w33a-2 / gap33-4, y_47302 crop): a flat smoky see-through half-disc (~0.19 wide) hanging face-forward, tipped
  // ~25 deg nose-down (w33b-3) under the seat, the vest a darker core inside, a red strap with a blue tag folded down its face (was an opaque puck) [V]
  // w39 (w38a-3 / w38b-2): the disc swung down-aft, its face up-aft, so the high front views (e1 / e7 / e11) saw it edge-on;
  // now it swings down-forward (rx -55 deg, the other half), face up-forward as y_47302's fan, strap and tag on its face
  B.add(gCyl(0.095, 0.095, 0.012, 14, true, Math.PI, Math.PI), M4.trs(x0 + 0.03, 0.235, -0.36, 0, -(Math.PI / 2 - 35 * DEG)), { c: '#767983', r: 0.3 });   // w41 (w40a-8 / w40b-3): satin smoky plastic (r 0.12 read as a flat plate)   // w38 (w37a-5 / w37b-3): L~40 vs y_47302 60-80, faced forward where the photo lies flatter -> lighter   // final (w36a-5 / w36b-2): a brown bowl -> cool smoky grey (y_47302 #43444d), thin rim round a dark cool vest; w36 (w35a-4): a pale rim round a black core read as a gauge -> smoky, the vest showing through; w34b-2: read opaque near-black
  B.add(gCyl(0.085, 0.085, 0.016, 12, true, Math.PI, Math.PI), M4.trs(x0 + 0.03, 0.232, -0.362, 0, -(Math.PI / 2 - 35 * DEG)), { c: '#43454d', r: 0.45 });   // w41 (w40a-8 / w40b-3): darker vest core inside the lighter rim, so the shell reads see-through (y_47302)   // w38 (w37a-5 / w37b-3): core (32,34,41) vs y_47302 48-60 -> lighter
  B.add(gBox(0.018, 0.12, 0.004), M4.trs(x0 + 0.035, 0.19, -0.40, 0, 35 * DEG), { c: '#c8252b', r: 0.5 });   // w41 (w40b-3): ~4 cm of the pull strap hangs past the rim (y_47302)
  B.add(gBox(0.02, 0.012, 0.005), M4.trs(x0 + 0.035, 0.232, -0.376, 0, 35 * DEG), { c: '#2f5fb0', r: 0.5 });   // w41 (w40a-8): proud of the face (it was buried at rim height)
  B.add(gBox(0.018, 0.018, 0.006), M4.mul(M4.trs(x0 + 0.03, 0.232, -0.362, 0, -(Math.PI / 2 - 35 * DEG)), M4.trs(-0.025, 0, -0.045, 0.4)), { c: '#8a6238', r: 0.7 });   // w41 (w40b-3): orange vest fleck through the shell (y_47302)
  if (!opts.noScreen) {
    // 13.3 in touchscreen (0.294 x 0.166) in a black glass border 0.316 x 0.205 set flush in the hood face, top ~0.03
    // below the hood's rounded top (y_47305: 600 x 390 px at 1905 px/m, colour (29,26,38); 55 px of shell above) [D]
    const SY = 0.7275;
    B.add(gRBox(0.328, 0.217, 0.004, 0.008, 1), on(SY, -0.0005), { c: '#5a6072', r: 0.35 });     // w9 A: ~4 mm lighter grey frame ring round the glass (y_47305)
    B.add(gRBox(0.316, 0.205, 0.004, 0.006, 1), on(SY, 0.001), { c: '#2a2932', r: 0.12 });   // w8 A: glossy dark-grey glass (y_47305), not flat black; w9 A #16161c rendered vs #1d1926
    B.add(gQuad(0.294, 0.166), on(SY + 0.004, 0.0035), SEATMAT.screen, atlasUV('screen'));   // w9 B: chin 11 % of the glass height (y_47305)
    // w46 (gap w46-4): a raised ~1.6 cm lip each side of the bezel with a shaded valley inside it (y_47305 profile 200-215 then 178-184; e5 was flat) [D]
    for (const s of [-1, 1]) B.add(gRBox(0.016, 0.30, 0.006, 0.003, 1), on(SY - 0.01, 0.002, s * 0.177), SEATMAT.yShell);
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
    B.add(gRBox(0.052, 0.022, 0.014, 0.004, 1), on(0.462, 0.012), { c: '#6f737a', r: 0.4 });   // w46: under the new hood shelf
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
    B.add(gCyl(0.0045, 0.0045, 0.175, 8), M4.mul(on(0.145, 0.012), M4.trs(0, 0, 0, 0, 0, Math.PI / 2)), { c: '#b9bdc4', r: 0.6, l: LAYER.fabric });   // w49: the pouch's elastic hem (the w8 flap bar is gone)
    // w49 (w48a-3 / w47b-5, medium A): the w48 pouches read as a flat dark grille. y_47303 (left block, q17 crop): a
    // light-grey fabric pouch bulging out toward its foot holds the safety card, whose white body and diagonal blue header
    // stand out of the mouth tipped back; black-edged mesh panels with a lit grey weave at its sides (L88, highlights to
    // L170 vs our L74) [V]
    B.add(gQuad(0.31, 0.16), on(0.035, 0.011), { c: '#454a53', r: 0.9 });
    const bul = (y) => 0.008 + 0.034 * Math.pow(Math.sin(Math.PI * clamp((0.15 - y) / 0.235, 0, 1)), 0.8) * (y < 0.03 ? 1 : 0.75 + 0.25 * (0.15 - y) / 0.12);
    loftAt(B, [0.145, 0.12, 0.09, 0.06, 0.03, 0.0, -0.03, -0.06, -0.08].map((y) => { const d = bul(y); return SEC(y, 0.17 + 0.012 * (0.15 - y) / 0.23, d, zr(y) + d / 2, Math.min(d / 2, 0.012)); }), BH, { c: '#9298a1', r: 0.85, l: LAYER.fabric }, 3);
    // the card in the pouch: its top 3 cm out of the mouth, tipped ~9 deg back; blue diagonal header over a white body
    const card = (dy, dx, w, h, dz, c, roll = 0) => B.add(gQuad(w, h), M4.mul(M4.mul(on(0.13, 0.014), M4.trs(0, 0, 0, 0, 9 * DEG)), M4.trs(dx, dy, dz, 0, 0, roll)), { c, r: 0.6 });
    card(0.0, 0.0, 0.15, 0.09, 0.0, '#eef0f3');
    card(0.032, 0.0, 0.15, 0.022, 0.0006, '#2f62b0');
    card(0.02, -0.012, 0.15, 0.012, 0.0006, '#3d6fc0', 0.16);
    card(0.034, -0.03, 0.06, 0.006, 0.0012, '#ffffff');
    // side mesh panels, bowed out at the foot: a dark rim round a lit grey 6 mm weave
    for (const s of [-1, 1]) {
      const cx = s * 0.122, mb = (y) => 0.006 + 0.022 * Math.sin(Math.PI * clamp((0.14 - y) / 0.22, 0, 1));
      for (let j = 0; j <= 34; j++) { const y = -0.075 + j * 0.0062; B.add(gQuad(0.066, 0.0022), on(y, 0.004 + mb(y), cx), { c: '#c3c9d3', r: 0.75 }); }
      for (let i = 0; i <= 10; i++) for (let q = 0; q < 4; q++) { const y = -0.075 + (q + 0.5) * 0.054; B.add(gQuad(0.0022, 0.056), on(y, 0.0035 + mb(y), cx - 0.031 + i * 0.0062), { c: '#b9bfc9', r: 0.75 }); }
      for (const ex of [-0.035, 0.035]) for (let q = 0; q < 4; q++) { const y = -0.075 + (q + 0.5) * 0.054; B.add(gBox(0.006, 0.056, 0.006), on(y, 0.004 + mb(y), cx + ex), { c: '#1f2126', r: 0.6 }); }
      B.add(gBox(0.076, 0.008, 0.008), on(-0.078, 0.008, cx), { c: '#1f2126', r: 0.6 });
    }
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
  // w42 (w41a-3, medium): the side views show the belts laid across the pans (y_47301 / y_47303: teal tongue strap and navy
  // buckle strap from the rear side creases to a latch at mid-pan; teal px 80 vs 3785 in q17), while the y_47300 hero
  // row has them tucked -> the 3-seat side blocks drape, the centre block stays tucked [V]
  if (opts.drape) {
    const panY = (z) => 0.47 + (-0.28 - z) * 0.0875;   // pan top (loft top 0.055 above 0.415, 5 deg, front up)
    // w46 (w45b-1 / w45a-2 / gap w46-5): y_47303 read in seat axes: the straps lie unlatched across the REAR half of the
    // pan, one anchored at each rear side crease, not a V latched up front. Near right seat (even k): the teal tongue
    // strap crosses from the far-side crease to its steel tongue by the aisle-side armrest; the navy buckle strap runs
    // from under that armrest diagonally forward to the buckle cover at mid-pan. Near left seat (odd k): the teal strap
    // comes out of the arm gap (dropping into it) to the buckle cover; the navy runs from the far crease to the tongue.
    // a = the aisle-side arm (C and H both on the aisle; K mirrored to its window arm) [V]
    const a = (opts.hk || 0) === 2 ? 1 : -1, odd = (opts.hk || 0) % 2 === 1;
    const strap = (x1, z1, x2, z2, c, h1 = 0) => {
      const L = Math.hypot(x2 - x1, z2 - z1), yaw = Math.atan2(x2 - x1, z2 - z1), y1 = panY(z1) + h1, y2 = panY(z2);
      B.add(gBox(0.048, 0.003, Math.hypot(L, y2 - y1)), M4.trs((x1 + x2) / 2, (y1 + y2) / 2 + 0.006, (z1 + z2) / 2, yaw, -Math.atan2(y2 - y1, L)), { ...SEATMAT.yBelt, c });
    };
    const TEAL = '#4a75a5', NAVY = '#353b4e', STEEL = { c: '#93a5bf', m: 0.7, r: 0.3 };   // w46a-3: steel hardware, not white plastic
    let xt, zt, xb, zb;
    if (!odd) {
      xt = x0 + 0.13 * a; zt = -0.20; xb = x0 - 0.075 * a; zb = -0.33;
      strap(x0 - 0.04 * a, -0.13, xt - 0.03 * a, zt + 0.005, TEAL);   // w48 (w47b-2): a short run to the tongue, not along the arm
      strap(x0 + 0.20 * a, -0.21, xb + 0.03 * a, zb + 0.012, NAVY, -0.01);   // w48 (w47b-2): from under the arm's front half
    } else {
      xb = x0 + 0.01 * a; zb = -0.29; xt = x0 - 0.06 * a; zt = -0.25;
      strap(x0 + 0.19 * a, -0.22, xb + 0.03 * a, zb + 0.01, TEAL, -0.008);
      B.add(gBox(0.003, 0.05, 0.048), M4.trs(x0 + 0.205 * a, panY(-0.22) - 0.018, -0.22), { ...SEATMAT.yBelt, c: TEAL });   // dropping into the arm gap
      strap(x0 - 0.19 * a, -0.13, xt - 0.025 * a, zt + 0.012, NAVY);
    }
    B.add(gRBox(0.045, 0.006, 0.034, 0.004, 1), M4.trs(xt, panY(zt) + 0.007, zt, 0.6 * a), STEEL);   // steel tongue
    B.add(gRBox(0.05, 0.013, 0.042, 0.006, 1), M4.trs(xb, panY(zb) + 0.009, zb, -0.5 * a), { c: '#c4cad2', m: 0.35, r: 0.32 });   // light buckle cover (w47a-5: lighter) (y_47303)
  } else for (const s of [-1, 1]) {
    B.add(s < 0 ? gRBox(0.05, 0.012, 0.035, 0.005, 1) : gRBox(0.05, 0.014, 0.04, 0.006, 1), M4.trs(x0 + 0.012 * s, s < 0 ? 0.468 : 0.465, s < 0 ? -0.165 : -0.17), s < 0 ? SEATMAT.buckle : { c: '#3a3f52', r: 0.4 });   // w39 (w38b-1): still two light blocks at the pillow foot -> under its edge, navy-grey cover;   // w37 (w37a-3): the V and two light blocks still on every q15 pan -> tucked under the pillow foot, darker cover   // w36 (w35a-3): the V and light buckles below every pillow (y_47300 shows none) -> nearer the crease, shorter, a grey cover   // w25 (w24b-5): the light covers dominated the pans head-on   // w41 (w40a-5): the silver tongue tip out from under the pillow (light px 15-25 vs y_47300 32-40; w42 (w41a-4): 0.5 cm back, it overshot on F / G)
    B.add(gBox(0.045, 0.004, 0.06), M4.trs(x0 + 0.035 * s, 0.474, -0.175, s * 15 * DEG), s < 0 ? SEATMAT.yBelt : { ...SEATMAT.yBelt, c: '#262c48' });   // w10 B: teal tongue strap, navy buckle strap (y_47303)   // w41 (w40a-5 / w40b-4): strap stubs still read as a V beside the buckle -> shorter, flatter, under the pillow foot
  }
  // w33: the pan-front stiffener (r2 light grey, w14 shadowed) is gone - the dark tray closes the pan base and a separate
  // dark slab read as a bar under every pan (e10 / e11)
  // white seat-electronics box under the pan front, dark face (y_47302) [D]
  {
    // w34b-3: hangs from the tray just behind the pan face (it floated 3 cm low, 9 cm back)
    // w33 (gap33-4, y_47302 crop): light grey, tucked up against the pan base, dark display in its upper half, blue LED [V]
    B.add(gRBox(0.075, 0.085, 0.05, 0.008, 1), M4.trs(x0 - 0.13, 0.315, -0.455), { c: '#c8cacc', r: 0.5, l: LAYER.plastic });   // w41: 1 cm aft with the tray
    B.add(gQuad(0.04, 0.03), M4.trs(x0 - 0.13, 0.33, -0.4805, Math.PI), { c: '#1c1f25', r: 0.3 });
    B.add(gQuad(0.004, 0.004), M4.trs(x0 - 0.115, 0.305, -0.4807, Math.PI), { c: '#4a90ff', r: 0.3, e: 0.8 });
  }
}

function econUnit(n, lod = false, opts = {}) {
  const B = new Builder();
  const sp = ECON.sp;
  const xs = []; for (let k = 0; k < n; k++) xs.push((k - (n - 1) / 2) * sp);
  xs.forEach((x, k) => econSeat(B, x, lod, { ...opts, fab: econFab(k, n, opts.rot), hk: k, panFab: econPan(k, n, opts.rot), drape: n === 3, pillow: opts.pillow !== false && n !== 3 }));   // w44 (w43a-1 / w42a-1, medium): y_47301 / y_47303 show no pillows on the side blocks (they hid the draped belts); the y_47300 centre block keeps them
  const arms = []; for (let k = 0; k <= n; k++) arms.push((k - n / 2) * sp);
  arms.forEach((xa, k) => {
    const armTilt = M4.mul(M4.trs(xa, 0.66, -0.08, 0, -4 * DEG), M4.trs(0, -0.66, 0.08));
    // sculpted off-white armrest (thick, rounded, slightly drooping nose) on a rear pivot post (y_47302 / 47303)
    // w5 B: a slim ~5.5 cm bar (y_47303 28 px on a 0.33 m / 160 px arm; fr57325 124108) with a drooping nose [D]
    loftAt(B, [SEC(0.625, 0.04, 0.30, -0.23, 0.014), SEC(0.64, 0.047, 0.32, -0.23, 0.021), SEC(0.668, 0.046, 0.315, -0.23, 0.021), SEC(0.68, 0.039, 0.30, -0.225, 0.016)], armTilt, SEATMAT.arm, 3);   // w30 (w29a-1): 1.4x wide head-on (33-35 px vs 24-25 in y_47300) -> 0.054 -> 0.047 (B: 8.4, kept above A's 0.044)   // w11 B: nose ~2 cm down (y_47303)
    // w8 A: no separate knuckle block on the nose (the loft's rounded end carries it, y_47303)
    B.add(gRBox(0.043, 0.008, 0.22, 0.004, 1), M4.mul(armTilt, M4.trs(0, 0.678, -0.225)), SEATMAT.armPad);   // w32 (w31a-2 / w31b-5): arm nose 2 cm back (q15 arm ends y525 vs 485)
    if (!opts.noScreen) {
      // w19 A + B: regular rows carry one C moulding, open at the front - the arm, a broad sweep down under its rear end and
      // a ~5.5 cm lower bar running forward at pan-top height to a rounded nose, ~6 cm under the arm (y_47303 near / right
      // aisle seats, sans b_ss_18); no front bracket, paddle or aisle-end panel (those are the exit-row arms, y_47302) [D]
      // w20 A + B: the lower member is a flat moulded plate (~2 x 6 cm; at the block ends a deep ~11 cm panel, b_ss_18
      // 1.75x the arm, y_47301), not a round rail - lofted in y, its z extent shaped into the rounded nose [D]
      const cp = [[0, 0.636, -0.078], [0, 0.60, -0.074]];
      for (let i = 1; i <= 8; i++) { const t = i / 8, u = 1 - t; cp.push([0, u * u * 0.60 + 2 * u * t * 0.52 + t * t * 0.50, u * u * -0.074 + 2 * u * t * -0.08 + t * t * -0.17]); }
      const end = k === 0 || k === arms.length - 1;
      const ct = gTube(cp, 0.028, 12); for (let k = 0; k < ct.p.length; k += 3) ct.p[k] *= 0.38; computeNormals(ct);   // w21 B: 2.1 cm, as the plate (3.1 cm stepped at the joint)
      if (!end) B.add(ct, M4.trs(xa, 0, 0), SEATMAT.arm);
      // w31 (w30a-2 / w30b-8): still two white bars head-on; under the arm y_47300 shows mid-grey mechanism -> grey plate [D]
      const zs = (y, z0, z1, w) => SEC(y, w, z0 - z1, (z0 + z1) / 2, 0.009);
      // w33 (w33a-4, y_47303 aisle seats): the end plate was ~1.55x the arm's depth head-on (41-43 px vs 26-28) -> ~8 cm deep;
      // w34a-5: a 14-16 px gap under the arm (y_47303 2-8 px) -> 4.5 cm higher; w48 (w47a-2): reverted - measured at the old q17
      // camera; at the matched one the raised plate stacked as a second white bar under the arm [D]
      // w46 (gap w46-3): q17 showed four grey pills under the arms (1400 dark-grey px vs 547 in y_47303) -> 2.5 cm lower, nose 4 cm back, darker; w30 (w29a-1): regular-row plate nose 3 cm further back, so the arm hides it head-on (y_47300 shows one bar) [D]
      if (end) {
        // w49 (w48a-2 / w48b-2, medium, both): the block-end plate stacked as a second white bar under the arm. y_47303 crop
        // (q17, landmark camera): one swept J moulding - a ~5 cm bar at y ~0.42-0.47 whose rounded nose stands ~8 cm ahead of
        // the arm nose (z ~-0.50), running back level to ~z -0.33, then rising diagonally to merge under the arm's rear
        // (gap under the arm 34-44 px vs 11-15) [D]
        const jp = [[0, 0.442, -0.49], [0, 0.435, -0.462], [0, 0.432, -0.41], [0, 0.433, -0.33], [0, 0.437, -0.27], [0, 0.448, -0.235], [0, 0.47, -0.205], [0, 0.51, -0.17], [0, 0.555, -0.13], [0, 0.595, -0.095], [0, 0.625, -0.068]];   // straight bar, a crisp elbow at z ~-0.22, a ~50 deg diagonal into the arm's rear
        const jt = gTube(jp, 0.031, 14); for (let q = 0; q < jt.p.length; q += 3) jt.p[q] *= 0.6;   // ~6 x 3.7 cm computeNormals(jt);
        B.add(jt, M4.trs(xa + (k === 0 ? -0.013 : 0.013), 0, 0), SEATMAT.arm);
      } else loftAt(B, [zs(0.455, -0.14, -0.295, 0.02), zs(0.463, -0.13, -0.313, 0.022), zs(0.485, -0.125, -0.322, 0.022), zs(0.507, -0.13, -0.313, 0.022), zs(0.515, -0.14, -0.295, 0.02)], M4.trs(xa, 0, 0), ECON_PLATE, 3);
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
  // w33 (gap33-3 / w33a-1, y_47303 aisle feet, sans 23): slim round silver tubes - a rear post and a raked front strut on a
  // floor rail that closes them into an open frame over the track, dark track fittings; the side beams and spreader tubes
  // under the pan are in its shadow (y_47302 #222631 there) -> dark metal; the baggage bar stays silver [D]
  const UND = { c: '#3a3d44', r: 0.45, m: 0.6 };
  for (const lx of legX) {
    B.add(gTube([[lx, 0.30, -0.07], [lx, 0.035, -0.05]], 0.013, 8), M4.trs(0, 0, 0), SEATMAT.frame);
    B.add(gTube([[lx, 0.30, -0.35], [lx, 0.14, -0.32], [lx, 0.035, -0.30]], 0.012, 8), M4.trs(0, 0, 0), SEATMAT.frame);
    B.add(gTube([[lx, 0.025, -0.33], [lx, 0.025, -0.02]], 0.01, 8), M4.trs(0, 0, 0), SEATMAT.frame);
    B.add(gRBox(0.04, 0.05, 0.46, 0.01, 1), M4.trs(lx, 0.31, -0.22), UND);
    for (const zf of [-0.05, -0.30]) B.add(gBox(0.04, 0.016, 0.07), M4.trs(lx, 0.008, zf), { c: '#4a4e55', r: 0.5, m: 0.5 });
  }
  for (const zb of [-0.1, -0.35]) B.add(gCyl(0.02, 0.02, W - 0.04, 10), M4.trs(0, 0.30, zb, 0, 0, Math.PI / 2), UND);   // front tube behind the electronics boxes
  // low silver baggage bar across the front legs (y_47302)
  B.add(gCyl(0.011, 0.011, W - 0.06, 8), M4.trs(0, 0.10, -0.34, 0, 0, Math.PI / 2), SEATMAT.frame);
  if (!lod) {
    B.add(gRBox(0.22, 0.10, 0.30, 0.012, 1), M4.trs(xs[xs.length - 1] - 0.05, 0.19, -0.18), { c: '#33363c', r: 0.5 });   // w34b-6: a flat black brick in e10 / e7 -> charcoal, 4 cm back
  }
  return B.build();
}
// w36 (w35a-2 / w35b-3, far rows snowy for three rounds): beyond the LOD switch the photo tiles alias into white snow; the
// far LOD takes each fabric's mean colour (the photoBase source hex, x0.92 for the darker tile mean) on the low-contrast
// generic weave layer [D]
// w38 (w37b-1): far box L134 B/R 1.31 vs y_47300 112 / 1.48 -> ~10 % darker, bluer
const ECON_FAR = new Map([[SEATMAT.yFabric, '#4c5682'], [SEATMAT.yFabricB, '#4c5690'], [SEATMAT.yFabricC, '#46507a'], [SEATMAT.yFabricD, '#3e4763'],
  [ECON_PAN, '#454d72'], [ECON_PAN_B, '#3f4465'], [ECON_PAN_C, '#3f466b'], [ECON_HEAD_L, '#52608c'], [ECON_HEAD_D, '#3f486a']]);
// w38 (w37a-1 / w37b-1): the flat mean colours read as plain royal-blue blocks once the switch moved to ~4.3 m (the near
// rows of y_47300 are mottled); the far LOD keeps each fabric's photo tile (the shader eases its contrast with distance)
// on a base ~15 % darker in linear light (far box L134 vs 112) [D]
const econFarMat = (m) => ECON_FAR.has(m) ? { ...m, c: '#' + hexRGB(m.c).map((v) => Math.round(v * 0.92).toString(16).padStart(2, '0')).join('') } : m;
function econUnitFar(n, rot = 0) {
  const B = new Builder();
  const sp = ECON.sp;
  for (let k = 0; k < n; k++) {
    const x0 = (k - (n - 1) / 2) * sp;
    const f = econFab(k, n, rot);
    B.add(gRBox(0.47, 0.085, 0.47, 0.03, 1), M4.trs(x0, 0.418, -0.28, 0, 5 * DEG), econFarMat(econPanMat(econPan(k, n, rot))));   // w33: the near pan (0.47, 3 cm rolls, 5 deg)
    const BH = M4.trs(x0, ECON.hinge[0], ECON.hinge[1], 0, ECON.back, 0, 1, ECON.backS);
    B.add(gRBox(0.42, 0.86, 0.08, 0.035, 1), M4.mul(BH, M4.trs(0, 0.43, -0.005)), econFarMat(f));   // same mix as econUnit
    B.add(gRBox(0.446, 0.62, 0.045, 0.015, 1), M4.mul(BH, M4.trs(0, 0.25, 0.058)), SEATMAT.yShell);
    B.add(gRBox(0.40, 0.37, 0.12, 0.015, 1), M4.mul(BH, M4.trs(0, 0.665, 0.062)), SEATMAT.yShell);    // screen hood under the back top (w5; w6 0.40, tight corners; w14 gap: top 0.85, its white cap showed on every far back)
    B.add(gRBox(0.39, 0.23, 0.12, 0.04, 1), M4.mul(BH, M4.trs(0, 0.70, -0.062)), econFarMat(econHead(f, k, rot)));
    B.add(gBox(0.22, 0.21, 0.01), M4.mul(BH, M4.trs(0, 0.72, -0.127, 0, 0.12)), SEATMAT.yCover);   // w49: the near LOD's longer drape   // w44: proud, as the near LOD   // w35: foot 3 cm higher, as the near LOD
    B.add(gQuad(0.316, 0.205), M4.mul(BH, M4.trs(0, 0.7275, 0.1245)), SEATMAT.bezel);
    B.add(gQuad(0.294, 0.166), M4.mul(BH, M4.trs(0, 0.7275, 0.1265)), SEATMAT.screen, atlasUV('screen'));
    if (n !== 3) B.add(gBox(0.32, 0.07, 0.21), M4.mul(BH, M4.trs(0, 0.155, -0.10, 0, -74 * DEG)), SEATMAT.yPillow);   // w33 (gap33-5): pillow; w44: centre block only
  }
  // w33 (gap33-5, y_47301 / 47300 far rows): a dark block under the pans and the silver baggage bar, so far rows get the
  // dark under-seat band; a grey lower plate under every arm and the white member on the block ends (the row of white Cs
  // along the aisle) [D]
  const W = n * sp;
  B.add(gBox(W - 0.04, 0.2, 0.40), M4.trs(0, 0.25, -0.24), { c: '#24272c', r: 0.6 });
  B.add(gBox(W - 0.06, 0.02, 0.02), M4.trs(0, 0.10, -0.34), SEATMAT.frame);
  for (let k = 0; k <= n; k++) {
    const end = k === 0 || k === n, xe = (k - n / 2) * sp + (end ? (k ? 0.013 : -0.013) : 0);
    if (!end) { B.add(gBox(0.022, 0.05, 0.26), M4.trs(xe, 0.51, -0.25), ECON_PLATE); continue; }
    B.add(gBox(0.025, 0.05, 0.21), M4.trs(xe, 0.446, -0.40), SEATMAT.arm);   // w49: the near LOD's J moulding - a low bar and a diagonal up to the arm rear
    B.add(gBox(0.025, 0.05, 0.25), M4.trs(xe, 0.53, -0.205, 0, -42 * DEG), SEATMAT.arm);
  }
  for (let k = 0; k <= n; k++) B.add(gBox(0.048, 0.05, 0.30), M4.trs((k - n / 2) * sp, 0.64, -0.235), SEATMAT.arm);
  return B.build();
}
