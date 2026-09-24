// ------------------------------------------------------------------
// Monuments: lavatories (bidet / accessible / baby-change), galleys, the THE Room self-service bar
// (roller blinds + backlit washi-style panels), closets, flight-deck door, class partitions,
// Type A door linings and flight-attendant jump seats
// ------------------------------------------------------------------
const MONMAT = {
  // [V] near-white monument laminate: ANA photos sample #efefed (y_47300 aft wall), #dcdbd6 (y_47302), #d1d7df
  //     (py_37302, cool balance); the old #dcdad4 rendered #bcbcbb under the bins (QA r1 q19)
  laminate: { c: '#eceae6', r: 0.45, l: LAYER.plastic },
  lavDoor: { c: '#f0efeb', r: 0.4, l: LAYER.plastic },
  steel: { c: '#b5bbc2', r: 0.3, m: 0.85, l: LAYER.brushed },
  steelDark: { c: '#8e949c', r: 0.35, m: 0.8, l: LAYER.brushed },
  ovenGlass: { c: '#101318', r: 0.1 },
  galleyWhite: { c: '#d6d3cc', r: 0.4, l: LAYER.plastic },       // galley structure, warm light grey (sans_38)
  workLight: { c: '#fff6e6', r: 0.4, e: 0.8 },
  green: { c: '#35d06a', r: 0.4, e: 0.7 },
  blueLed: { c: '#3d8bff', r: 0.4, e: 0.8 },
  amber: { c: '#ff9a3a', r: 0.4, e: 0.8 },
  red: { c: '#c62828', r: 0.5 },
  partition: { c: '#d0d2d4', r: 0.5, l: LAYER.plastic },
  // [V] flight-deck door + corridor walls: dark ebony wood-grain laminate with reddish streaks (tpa_IMG_0260 samples
  //     #322f2f..#43393b), white/aluminium door frame and white bolt-plate frames
  cockpitDoor: { c: '#3a3332', r: 0.4, l: LAYER.wood },
  cockpitFrame: { c: '#c9ccd0', r: 0.35, m: 0.5, l: LAYER.brushed },
  plateWhite: { c: '#e9e9e6', r: 0.45, l: LAYER.plastic },
  jump: { c: '#8a8987', r: 0.6, l: LAYER.fabric },     // [V] mid-grey, ~0.55 of the door lining (lalf_133 #594c4c / #a28c79)
  harness: { c: '#5c5f66', r: 0.8 },
  jumpBase: { c: '#a3a19d', r: 0.5, l: LAYER.plastic }, // [V] grey stowage pedestal under the seat (lalf_133 #736c65)
  closet: { c: '#dedcd6', r: 0.45, l: LAYER.plastic },
  ash: { c: '#cdbfa6', r: 0.5, l: LAYER.wood },
  ashDark: { c: '#8a7560', r: 0.5, l: LAYER.wood },
  darkWood: { c: '#38302e', r: 0.42, l: LAYER.wood },     // [V] F-zone ebony, as the flight-deck corridor (tpa_IMG_0260)
  darkWoodDoor: { c: '#3f3533', r: 0.4, l: LAYER.wood },
  // door-3 bar / door-2 welcome galley, sampled from ANA's official bar-counter render (Jul 2019 press kit) and
  // OMAAT's in-service photos: light ash doors, dark-bronze frames, black basalt counter, black upper unit
  barAsh: { c: '#b9a687', r: 0.5, l: LAYER.ashGrain },
  bronze: { c: '#6f5f50', r: 0.35, m: 0.55, l: LAYER.brushed },
  barPost: { c: '#9d8f7c', r: 0.35, m: 0.55, l: LAYER.brushed },     // [V] warm light grey-bronze posts (samchui_11 #8e7f6d)
  steelBright: { c: '#d4d6d8', r: 0.25, m: 0.9, l: LAYER.brushed },  // [V] bright counter nosing (samchui_11 #c5c0b9, lalf_134)
  // [V] door-2 aft wall (lalf_133): flat ash with aluminium-framed stowage flaps, red latches, aluminium rails; dark warm
  //     soffit with downlights over the galley passage (lalf_133 #655b54, lalf_134 #696567 at ~0.6 of white)
  soffit: { c: '#4a423d', r: 0.35, l: LAYER.wood },
  basalt: { c: '#28262b', r: 0.22, l: LAYER.marble },
  black: { c: '#1b1a20', r: 0.35, l: LAYER.plastic },
  blackGloss: { c: '#0f0e13', r: 0.15 },
  blind: { c: '#1d1c22', r: 0.85, l: LAYER.fabric },                // decorative blind, pulled down (render)
  washi: { c: '#f2f3f6', r: 0.8, l: LAYER.atlasGlow, e: 0.6 },       // neutral-white backlit washi band (render)
  washiGalley: { c: '#d4d3e0', r: 0.8, l: LAYER.atlasGlow, e: 0.45 }, // lavender-grey galley washi (welcome render)
  downlight: { c: '#eef4ff', r: 0.3, e: 1.6 },
  fridgeLit: { c: '#2c2f36', r: 0.08, e: 0.03 },     // [V] smoked-glass door: #3a3941 (render), #3b3834 (omaat_room_32)
  latch: { c: '#7a7d82', r: 0.35, m: 0.6 },           // [V] light-grey oval fridge latch (render)
  bottleClear: { c: '#9fb2b6', r: 0.05, m: 0.3 },
  bottleBlue: { c: '#2346c8', r: 0.5 },              // w2: blue label on clear water bottles (the solid blue read as blobs)
  label: { c: '#f4f2ec', r: 0.6 },
  juice: { c: '#f0a526', r: 0.15 },
  tumbler: { c: '#c9d2d6', r: 0.05, m: 0.2 },
  navyPanel: { c: '#2d2b29', r: 0.35, l: LAYER.plastic },          // [V] welcome end panel: warm charcoal (sp_09 #46433b dim; render's navy was a tint)
  // standard galley inserts (SANspotter PY snack-bar photo): aluminium ovens/trolleys, black beverage makers,
  // black work deck, red-copper turn-button latches
  alu: { c: '#9c9fa3', r: 0.35, m: 0.7, l: LAYER.brushed },
  aluDark: { c: '#8f9194', r: 0.4, m: 0.7, l: LAYER.brushed },
  bevBlack: { c: '#17171a', r: 0.3 },
  copper: { c: '#8f3a2c', r: 0.3, m: 0.4 },   // [V] small red turn-buttons (sp_09); the orange blocks dominated m01/m12
  deck: { c: '#26252a', r: 0.3, l: LAYER.plastic },
  card: { c: '#ece7c8', r: 0.7 },
  // class curtains sampled from in-service photos: F/J charcoal from both sides (omaatF_2 #5b5650/#554f4d under warm
  // light, omaat_room_36 #35343a; the f_17313 render's lavender-grey was a render tint), J/PY and PY aft-end dark slate
  // (py_37302 #424455), rear economy curtains light grey (y_47300 far end #888785..#9c9b99)
  // w1: the charcoal albedos rendered near-black (#202028 in m07); lifted to the photo samples (tpg_The-Room-small-cabin-
  // front_71 #5e5655, omaatF_2 #5b5650) [V]
  curtainF: { c: '#6e665f', r: 0.95, l: LAYER.fabric },   // + tpg_147 #4a453a at 0.34 of white, omaatF_2 #56504b
  curtainTie: { c: '#2e2b2d', r: 0.8, l: LAYER.fabric },
  curtainY: { c: '#474b5e', r: 0.9, l: LAYER.fabric },
  curtainRear: { c: '#8e8d8a', r: 0.9, l: LAYER.fabric },
  curtainC: { c: '#6b635d', r: 0.95, l: LAYER.fabric },   // w2: #5a524d still rendered #2a2523 in shade (m07)  // [V] J-cabin charcoal curtains (omaat_room_36 #302f35-#3d3c42, tpg_71 #5e5655)
  rail: { c: '#dcdbd6', r: 0.4 },
  // full-height class bulkheads (QA r1): F side of F/J = pale mottled washi print (omaatF_2 samples #c0bcb1 under warm
  // light -> #c9cad2, atlas washi fibres multiplied in); J faces = warm cream laminate (omaat_room_36 #c7bda9; #ddd5c3
  // rendered #8c877c..#969288 under the bins, lifted [A] to #e6dccb); PY face of J/PY = off-white laminate (py_37303)
  bulkF: { c: '#c9cad2', r: 0.7, l: LAYER.atlasLit },
  // w1: the F walls are a soft grey-green sumi ink-cloud print on a pale ground, not paper fibres (the stretched atlas
  // washi read as marble veins): tpg_The-Suite-cabin_147 ground #c8c9c2, clouds ~#8f958a; tpg_63 #bdbca6 [V]
  inkGround: { c: '#dddbd0', r: 0.75, l: LAYER.plastic },   // w2: warmer ground, ~18 % cloud contrast (was ~5 %)
  inkCloud: '#7c8279',
  bulkJ: { c: '#e6dccb', r: 0.5, l: LAYER.plastic },
  seamJ: { c: '#b3aa98', r: 0.6 },                          // [V] inset panel seam ~1.45 m (omaat_room_36)
  placardBlue: { c: '#2f5fb8', r: 0.5 },                    // [V] small blue placards ~1.75 m (omaat_room_36)
  bulkPY: { c: '#e3e3df', r: 0.45, l: LAYER.plastic },
  bulkCore: { c: '#d8d6d0', r: 0.5, l: LAYER.plastic },
  kick: { c: '#5a6478', r: 0.5, l: LAYER.plastic },       // [V] slate-grey kick strip (py_37303, py_37302)
  monHousing: { c: '#9ba1a9', r: 0.45, l: LAYER.plastic }, // [V] light-grey tilted monitor housings (py_37303)
  monFrame: { c: '#4a4d53', r: 0.4, l: LAYER.plastic },    // [V] charcoal flat monitor frame, in service (alv_IMG_7207 / 7209)
  pouch: { c: '#7d7f83', r: 0.85, l: LAYER.fabric },       // [V] grey fabric floor pouches (alv_IMG_7207)
  pouchBand: { c: '#5d5f64', r: 0.8, l: LAYER.fabric },
  pocketGrey: { c: '#aeb3ba', r: 0.5, l: LAYER.plastic },  // [V] grey literature pockets (py_37303)
  pocketWhite: { c: '#e6e4de', r: 0.45, l: LAYER.plastic }, // [V] white framed pockets (y_47302)
  wallBox: { c: '#cfd0c8', r: 0.45, l: LAYER.plastic },     // [V] J wall boxes (omaat_room_36, omaatF_2)
  cardWhite: { c: '#f2f2ee', r: 0.7 },
  cardBlue: { c: '#2f6fb8', r: 0.6 },                       // [V] B777-300 safety-card cover bands (py_37303, y_47302)
  cardGreen: { c: '#3c9a6a', r: 0.6 },
};

function monoSection(x0, x1, h) {
  const pts = [];
  const right = x1 > 0 && Math.abs(x1) >= Math.abs(x0);
  const n = 10;
  if (right) {
    pts.push([x0, 0]);
    for (let k = 0; k <= n; k++) { const y = (h * k) / n; pts.push([Math.min(x1, wallAt(y)[0] - 0.012), y]); }
    pts.push([x0, h]);
  } else {
    pts.push([x1, 0]); pts.push([x1, h]);
    for (let k = n; k >= 0; k--) { const y = (h * k) / n; pts.push([Math.max(x0, -wallAt(y)[0] + 0.012), y]); }
  }
  return pts.filter((p, i) => i === 0 || Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]) > 1e-4);
}
function monoBody(B, m, mat) {
  const sec = monoSection(m.x0, m.x1, m.h);
  B.add(gExtrude(sec, m.z1 - m.z0, 20), M4.trs(0, 0, (m.z0 + m.z1) / 2), mat);
}
function faceXF(m, x, y, out = 0) {
  const zf = m.face > 0 ? m.z1 : m.z0;
  return M4.trs(x, y, zf + m.face * out, m.face > 0 ? 0 : Math.PI);
}
// cabin class at a z (for finishes)
function clsAt(layout, z) {
  if (z < layout.suiteZ[2] + 0.2) return 'F';
  if (z < layout.z20 + 0.2) return 'J';
  if (z < layout.doorsZ[3][0]) return 'PY';
  return 'Y';
}

// viewer-relative placement on a monument face: u = metres to the right of the face centre as seen from the
// aisle, o = out of the face; rx tilts the local frame (PI/2 turns a +z quad to face down)
function faceUV(m, u, y, o, rx = 0) {
  const xf = faceXF(m, (m.x0 + m.x1) / 2 + u * m.face, y, o);
  return rx ? M4.mul(xf, M4.trs(0, 0, 0, 0, rx)) : xf;
}
// body split into a full-depth lower part (to the work deck) and an upper part set back by `set`
function monoStepBody(B, m, deckY, set, lowMat, upMat) {
  monoBody(B, { ...m, h: deckY }, lowMat);
  const up = { ...m };
  if (m.face > 0) up.z1 = m.z1 - set; else up.z0 = m.z0 + set;
  monoBody(B, up, upMat);
}
function bottle(B, xf, h, r, mat, lbl = true, lblMat = MONMAT.label) {
  B.add(gCyl(r, r, h * 0.66, 10), M4.mul(xf, M4.trs(0, h * 0.33, 0)), mat);
  B.add(gCyl(r * 0.36, r, h * 0.24, 10), M4.mul(xf, M4.trs(0, h * 0.78, 0)), mat);
  if (lbl) B.add(gCyl(r * 1.04, r * 1.04, h * 0.2, 10, false), M4.mul(xf, M4.trs(0, h * 0.22, 0)), lblMat);
}
// round flush stainless pull (bar render), on a face
function ringPull(B, xf) {
  B.add(gCyl(0.028, 0.028, 0.008, 16), M4.mul(xf, M4.trs(0, 0, 0.004, 0, Math.PI / 2)), MONMAT.steel);
  B.add(gCyl(0.019, 0.019, 0.008, 12), M4.mul(xf, M4.trs(0, 0, 0.006, 0, Math.PI / 2)), MONMAT.bronze);
  B.add(gBox(0.024, 0.006, 0.008), M4.mul(xf, M4.trs(0, 0, 0.011)), MONMAT.steel);
}

// open-top literature pocket / wall box on a face frame xf (+z out of the face): box w x h, cards sticking out of the
// top [V py_37303: ~0.25 m wide grey pockets; y_47302: white framed pockets; omaat_room_36: shallow wall boxes]
function litPocket(B, xf, mat, h = 0.26, w = 0.25) {
  B.add(gRBox(w, h, 0.05, 0.01, 1), M4.mul(xf, M4.trs(0, 0, 0.025)), mat);
  B.add(gBox(w - 0.03, 0.01, 0.036), M4.mul(xf, M4.trs(0, h / 2 - 0.006, 0.024)), { c: '#3b3d42', r: 0.8 });   // opening
  B.add(gQuad(w - 0.03, 0.10), M4.mul(xf, M4.trs(0, h / 2 - 0.01, 0.045)), MONMAT.cardWhite);
  B.add(gQuad(w - 0.03, 0.035), M4.mul(xf, M4.trs(0, h / 2 + 0.015, 0.0455)), mat === MONMAT.pocketWhite ? MONMAT.cardGreen : MONMAT.cardBlue);
}
// shared monitor in a thick light-grey housing tilted down (py_37303) on a face frame xf (+z out of the face)
function tiltMonitor(B, xf) {
  const T = M4.mul(xf, M4.trs(0, 0, 0.045, 0, 0.17));   // +rx leans the top out, the screen normal points down
  B.add(gRBox(0.48, 0.32, 0.07, 0.02, 1), T, MONMAT.monHousing);
  B.add(gRBox(0.42, 0.25, 0.01, 0.006, 1), M4.mul(T, M4.trs(0, 0, 0.034)), SEATMAT.bezel);
  B.add(gQuad(0.40, 0.23), M4.mul(T, M4.trs(0, 0, 0.0395)), SEATMAT.screen, atlasUV('screen'));
  B.add(gBox(0.16, 0.05, 0.05), M4.mul(xf, M4.trs(0, 0.1, 0.012)), MONMAT.monHousing);                     // wall bracket
}

// ---- Door-3 self-service bar ("New self-service bar counter with monitor and mini-fridge", ANA 2019 press kit).
// Layout read off the official render (ref/web/mono/tda_barcounter, = ANA 20190711-008): 7 light-ash doors with
// dark-bronze frames + round flush pulls, stainless grab rail, black basalt counter; set back behind it a black
// upper unit (blind pulled down on the left, ~24 in monitor over a closed cubby + open bottle shelf, glass-door
// mini-fridge with round latch on the right); black soffit with three downlights framed by backlit washi bands.
// Render px -> metres: counter front 155..1845 px = monument width; the set-back upper unit at 1.9 mm/px (sized
// off the 720 ml sake bottles, ~0.30 m = 160 px), giving a ~2.0 m wide unit, ~35 in monitor, 0.35 m wide fridge.
const BAR = { deck: 1.0, set: 0.5, K: 0.0019, upW: 1045 * 0.0019, upTop: 1.035 + 550 * 0.0019, canopy: 2.13 };
function buildBar(B, m) {
  const w = m.x1 - m.x0, V = (u, y, o, rx) => faceUV(m, u, y, o, rx);
  monoStepBody(B, m, BAR.deck, BAR.set, MONMAT.barAsh, MONMAT.barAsh);
  // lower: bronze frame, 7 ash doors, pulls
  const cw = w - 0.06, px = (p) => ((p - 1000) / 1690) * cw;
  B.add(gRBox(cw, BAR.deck - 0.02, 0.02, 0.006, 1), V(0, BAR.deck / 2, 0.006), MONMAT.barPost);
  for (const sx of [-1, 1]) B.add(gBox(0.03, BAR.deck - 0.02, 0.026), V(sx * (cw / 2 - 0.015), BAR.deck / 2, 0.01), MONMAT.bronze);   // dark outer frame
  B.add(gBox(cw, 0.07, 0.024), V(0, 0.035, 0.008), MONMAT.black);                         // toe kick
  for (const [a, b] of [[200, 335], [340, 598], [605, 862], [912, 1155], [1160, 1400], [1445, 1700], [1705, 1790]])
    B.add(gRBox(px(b) - px(a) - 0.006, 0.84, 0.014, 0.004, 1), V((px(a) + px(b)) / 2, 0.5, 0.022), MONMAT.barAsh);
  for (const p of [265, 395, 1340, 1640, 1760]) ringPull(B, V(px(p), 0.71, 0.029));
  // counter + stainless grab rail on stand-offs
  B.add(gRBox(w - 0.02, 0.035, BAR.set + 0.05, 0.008, 1), V(0, BAR.deck + 0.0175, (0.05 - BAR.set) / 2), MONMAT.basalt);
  B.add(gRBox(w - 0.03, 0.04, 0.035, 0.012, 1), V(0, BAR.deck - 0.02, 0.062), MONMAT.steelBright);
  for (const u of [-0.9, -0.3, 0.3, 0.9]) B.add(gBox(0.016, 0.014, 0.04), V(u * w / 2.2, BAR.deck - 0.012, 0.04), MONMAT.steel);
  // upper black unit
  const oU = -BAR.set, uw = BAR.upW, uy0 = BAR.deck + 0.035, uh = BAR.upTop - uy0;
  const up = (p) => (p - 1002) * BAR.K, uy = (p) => uy0 + (715 - p) * BAR.K;
  const box = (a, b, ya, yb, d, o, mat) => B.add(gRBox(up(b) - up(a), uy(ya) - uy(yb), d, 0.004, 1), V((up(a) + up(b)) / 2, (uy(ya) + uy(yb)) / 2, o), mat);
  B.add(gRBox(uw, uh, 0.06, 0.01, 1), V(0, uy0 + uh / 2, oU + 0.03), MONMAT.black);
  B.add(gBox(uw + 0.01, 0.05, 0.065), V(0, BAR.upTop - 0.025, oU + 0.034), MONMAT.blackGloss);        // fascia
  // left: blind pulled down (fine slat lines), bronze bottom rail
  box(490, 850, 210, 700, 0.012, oU + 0.066, MONMAT.blind);
  for (let k = 1; k < 9; k++) B.add(gBox(up(850) - up(490) - 0.01, 0.003, 0.004), V((up(490) + up(850)) / 2, uy(700) + (k * (uy(210) - uy(700))) / 9, oU + 0.073), MONMAT.blackGloss);
  B.add(gBox(up(850) - up(490) + 0.01, 0.018, 0.02), V((up(490) + up(850)) / 2, uy(700), oU + 0.07), MONMAT.bronze);
  // monitor (screen 405 x 235 px = 0.77 x 0.45 m, ~35 in class) with bezel + shelf lip under it
  box(862, 1318, 210, 480, 0.03, oU + 0.075, SEATMAT.bezel);
  B.add(gQuad(up(1290) - up(885), uy(225) - uy(460)), V((up(885) + up(1290)) / 2, (uy(225) + uy(460)) / 2, oU + 0.091), SEATMAT.screen, atlasUV('screen'));
  B.add(gRBox(up(1310) - up(870), 0.02, 0.07, 0.006, 1), V((up(870) + up(1310)) / 2, uy(490), oU + 0.09), MONMAT.blackGloss);
  // closed cubby door + open bottle shelf (7 clear sake/water bottles, one juice)
  box(865, 1060, 510, 695, 0.012, oU + 0.066, MONMAT.blackGloss);
  const sx0 = up(1070), sx1 = up(1310), sc = (sx0 + sx1) / 2;
  B.add(gBox(sx1 - sx0, uy(510) - uy(695), 0.01), V(sc, (uy(510) + uy(695)) / 2, oU + 0.02), { c: '#2a2a30', r: 0.5 });
  B.add(gBox(sx1 - sx0, 0.01, 0.08), V(sc, uy(690), oU + 0.07), MONMAT.blackGloss);
  B.add(gBox(sx1 - sx0, 0.025, 0.006), V(sc, uy(680), oU + 0.108), { c: '#2a2a30', r: 0.3 });   // shelf fence
  for (let k = 0; k < 8; k++) bottle(B, V(sx0 + 0.03 + (k * (sx1 - sx0 - 0.06)) / 7, uy(690) + 0.005, oU + 0.07), k ? 0.30 : 0.2, k ? 0.036 : 0.032, k ? MONMAT.bottleClear : MONMAT.juice);
  // glass-door mini-fridge: frame, lit interior, two shelves of blue bottles, round latch on a pill
  const fc = (up(1325) + up(1510)) / 2;
  box(1325, 1510, 250, 700, 0.02, oU + 0.07, MONMAT.blackGloss);
  B.add(gQuad(up(1480) - up(1345), uy(275) - uy(670)), V((up(1345) + up(1480)) / 2, (uy(275) + uy(670)) / 2, oU + 0.081), MONMAT.fridgeLit);
  for (const [sy, bh] of [[uy(668), 0.3], [uy(470), 0.3]]) {
    B.add(gBox(up(1480) - up(1345), 0.008, 0.02), V(fc, sy, oU + 0.086), MONMAT.bronze);
    for (let k = 0; k < 3; k++) bottle(B, V(up(1372) + k * 0.06, sy + 0.004, oU + 0.1), bh, 0.028, MONMAT.bottleClear, true, MONMAT.bottleBlue);
  }
  B.add(gRBox(0.07, 0.11, 0.02, 0.035, 2), V(up(1362), uy(470), oU + 0.125), MONMAT.latch);          // oval latch plate
  B.add(gCyl(0.022, 0.022, 0.012, 14), M4.mul(V(up(1362), uy(470), oU + 0.136), M4.trs(0, 0, 0, 0, Math.PI / 2)), MONMAT.steel);
  // tumblers on the counter (render: four at the left)
  for (const p of [490, 535, 578, 655]) B.add(gCyl(0.04, 0.034, 0.085, 12), V(up(p), BAR.deck + 0.078, p === 655 ? -0.16 : -0.26), MONMAT.tumbler);
  // ash cheeks either side of the upper unit, up to the soffit
  for (const s of [-1, 1]) B.add(gBox((w - uw) / 2 - 0.02, BAR.canopy - uy0, 0.02), V(s * (uw / 2 + (w - uw) / 4), (uy0 + BAR.canopy) / 2, oU + 0.012), MONMAT.barAsh);
  // black soffit over the bar with three downlights, framed by backlit washi bands
  const cd = BAR.set + 0.12, cy = BAR.canopy, co = (0.12 - BAR.set) / 2;
  B.add(gBox(w, 0.05, cd), V(0, cy + 0.025, co), MONMAT.blackGloss);
  B.add(gBox(uw - 0.02, cy - BAR.upTop, 0.02), V(0, (cy + BAR.upTop) / 2, oU + 0.02), MONMAT.blackGloss);
  // soffit fascia (front + sides, 0.14 m deep) whose undersides carry the lit washi bands, so the bands frame the
  // black soffit as in the render instead of hiding behind a thin lip (QA r1 m02)
  const fy = cy - 0.06, bw = 0.14;
  B.add(gBox(w, 0.06, bw), V(0, cy - 0.03, 0.131 - bw / 2), MONMAT.blackGloss);
  B.add(gQuad(w - 0.02, bw - 0.02), V(0, fy - 0.002, 0.131 - bw / 2, Math.PI / 2), MONMAT.washi, atlasUV('washi'));
  B.add(gQuad(w - 0.02, 0.04), V(0, cy - 0.032, 0.1325), MONMAT.washi, atlasUV('washi'));                  // lit fascia edge
  for (const s of [-1, 1]) {
    const sd = cd - bw + 0.012, sz = 0.131 - bw - sd / 2;
    B.add(gBox(bw, 0.06, sd), V(s * (w / 2 - bw / 2), cy - 0.03, sz), MONMAT.blackGloss);
    B.add(gQuad(bw - 0.02, sd - 0.01), V(s * (w / 2 - bw / 2), fy - 0.002, sz, Math.PI / 2), MONMAT.washi, atlasUV('washi'));
  }
  for (const u of [-0.5, 0, 0.5]) {
    B.add(gCyl(0.045, 0.045, 0.006, 16), V(u, cy - 0.003, -0.22), MONMAT.steel);
    B.add(gCyl(0.034, 0.034, 0.006, 16), V(u, cy - 0.005, -0.22), MONMAT.downlight);
  }
}

// ---- Door-2 welcome galley (OMAAT in-service photo "ANA business class galley 777": black upper unit with the
// landscape welcome monitor, control panel, two ovens with blue LED readouts, beverage maker, glass-door
// cabinet under a "return to seat" placard; black counter, ash lower doors with aluminium edge) + portrait
// welcome monitors on navy end panels facing the aisles (ANA "new welcome monitors" render, SANspotter photo)
function buildWelcomeGalley(B, m) {
  const w = m.x1 - m.x0, V = (u, y, o, rx) => faceUV(m, u, y, o, rx), set = 0.38, dk = 1.0;
  monoStepBody(B, m, dk, set, MONMAT.barAsh, MONMAT.black);
  const cw = w - 0.06, n = 6;
  B.add(gRBox(cw, dk - 0.02, 0.02, 0.006, 1), V(0, dk / 2, 0.006), MONMAT.bronze);
  B.add(gBox(cw, 0.07, 0.024), V(0, 0.035, 0.008), MONMAT.black);
  for (let k = 0; k < n; k++) {
    const u = -cw / 2 + (cw / n) * (k + 0.5);
    B.add(gRBox(cw / n - 0.01, 0.84, 0.014, 0.004, 1), V(u, 0.5, 0.022), MONMAT.barAsh);
    ringPull(B, V(u + (k % 2 ? -1 : 1) * (cw / n / 2 - 0.05), 0.82, 0.029));
  }
  B.add(gRBox(w - 0.02, 0.035, set + 0.05, 0.008, 1), V(0, dk + 0.0175, (0.05 - set) / 2), MONMAT.basalt);
  // [V] lalf_134: thick rounded satin-aluminium nosing wrapping the aisle ends, aluminium picture-frame edge round the opening
  B.add(gRBox(w - 0.03, 0.05, 0.04, 0.018, 1), V(0, dk + 0.005, 0.035), MONMAT.steelBright);
  for (const sx of [-1, 1]) {
    B.add(gRBox(0.035, 0.05, set + 0.05, 0.015, 1), V(sx * (w / 2 - 0.02), dk + 0.005, (0.05 - set) / 2 + 0.03), MONMAT.steelBright);
    B.add(gRBox(0.05, 2.02 - dk, 0.05, 0.02, 1), V(sx * (w / 2 - 0.025), (dk + 2.02) / 2, 0.0), MONMAT.alu);
    B.add(gBox(0.03, 2.0 - dk, set), V(sx * (w / 2 - 0.02), (dk + 2.0) / 2, -set / 2), MONMAT.barAsh);             // ash cheeks
  }
  B.add(gRBox(w, 0.05, 0.05, 0.02, 1), V(0, 2.02, 0.0), MONMAT.alu);
  B.add(gBox(w, m.h - 1.995, set), V(0, (1.995 + m.h) / 2, -set / 2), MONMAT.barAsh);                               // ash head
  const o = -set + 0.012;
  B.add(gBox(w - 0.04, 0.05, 0.03), V(0, 1.98, o + 0.02), MONMAT.blackGloss);
  // left column: control panel over two ovens
  const lc = -w / 2 + 0.26;
  B.add(gRBox(0.40, 0.2, 0.02, 0.006, 1), V(lc, 1.78, o + 0.01), MONMAT.alu);
  for (let k = 0; k < 4; k++) B.add(gCyl(0.008, 0.008, 0.01, 8), M4.mul(V(lc - 0.12 + k * 0.035, 1.76, o + 0.025), M4.trs(0, 0, 0, 0, Math.PI / 2)), k < 2 ? MONMAT.red : MONMAT.amber);
  B.add(gRBox(0.1, 0.03, 0.01, 0.004, 1), V(lc + 0.1, 1.76, o + 0.022), MONMAT.ovenGlass);
  for (const s of [-1, 1]) {
    const x = lc + s * 0.1;
    B.add(gRBox(0.19, 0.48, 0.04, 0.008, 1), V(x, 1.36, o + 0.02), MONMAT.alu);
    B.add(gRBox(0.15, 0.05, 0.01, 0.004, 1), V(x, 1.56, o + 0.042), MONMAT.bevBlack);
    B.add(gBox(0.02, 0.006, 0.004), V(x - 0.05, 1.56, o + 0.048), MONMAT.blueLed);
    B.add(gRBox(0.03, 0.14, 0.03, 0.012, 1), V(x, 1.33, o + 0.055), MONMAT.aluDark);
    B.add(gQuad(0.09, 0.07), V(x, 1.44, o + 0.041), MONMAT.card);
  }
  // centre: landscape welcome monitor; beverage maker + open cubby beneath it
  // [D] screen taller than the ovens beside it (omaat_ANA-Business-Class-The-Room-32: 280 vs 255 px) -> ~0.86 x 0.49 m
  const mc = -w / 2 + 0.92;
  B.add(gRBox(0.90, 0.54, 0.03, 0.01, 1), V(mc, 1.68, o + 0.02), SEATMAT.bezel);
  B.add(gQuad(0.86, 0.49), V(mc, 1.68, o + 0.036), SEATMAT.screen, atlasUV('screen'));
  B.add(gRBox(0.92, 0.02, 0.07, 0.006, 1), V(mc, 1.39, o + 0.04), MONMAT.blackGloss);
  // two open bays under the monitor (omaat 32): the brewer stands inside the left one, the right one is empty
  for (const u of [-0.225, 0.225]) {
    B.add(gBox(0.43, 0.34, 0.004), V(mc + u, 1.2, o + 0.002), { c: '#121115', r: 0.5 });
    for (const sx of [-1, 1]) B.add(gBox(0.014, 0.36, 0.1), V(mc + u + sx * 0.222, 1.2, o + 0.05), MONMAT.black);
  }
  B.add(gBox(0.9, 0.014, 0.1), V(mc, 1.375, o + 0.05), MONMAT.black);
  B.add(gRBox(0.18, 0.24, 0.12, 0.01, 1), V(mc - 0.28, 1.17, o + 0.064), MONMAT.bevBlack);
  B.add(gCyl(0.045, 0.045, 0.1, 12), V(mc - 0.28, 1.1, o + 0.09), MONMAT.steel);
  B.add(gBox(0.04, 0.02, 0.004), V(mc - 0.25, 1.26, o + 0.126), MONMAT.green);
  // right: tall glass-door cabinet with round latch and a placard above
  const gc = w / 2 - 0.3;
  B.add(gRBox(0.44, 0.8, 0.03, 0.01, 1), V(gc, 1.44, o + 0.02), MONMAT.blackGloss);
  B.add(gQuad(0.34, 0.66), V(gc + 0.02, 1.44, o + 0.037), { c: '#2c3036', r: 0.05, e: 0.06 });
  B.add(gRBox(0.08, 0.1, 0.02, 0.035, 2), V(gc - 0.17, 1.44, o + 0.045), MONMAT.aluDark);
  B.add(gRBox(0.3, 0.07, 0.012, 0.03, 2), V(gc, 1.92, o + 0.02), MONMAT.label);
  welcomeEnds(B, m);
}
// portrait welcome monitors on navy end panels facing each aisle, with three steel rub strips at 0.3 / 0.5 / 0.7 m
// (sans_09 looks down the door-2 galley passage: the lit portrait monitor on a dark end panel at the aisle, galley
// units on both sides; tda_welcome3 = ANA's render of the same panels)
function welcomeEnds(B, m) {
  const d = Math.min(0.6, m.z1 - m.z0 - 0.1);
  for (const s of [-1, 1]) {
    const x = s > 0 ? m.x1 : m.x0, zc = m.face > 0 ? m.z1 - d / 2 - 0.02 : m.z0 + d / 2 + 0.02;
    B.add(gBox(0.02, 2.0, d), M4.trs(x + s * 0.01, 1.0, zc), MONMAT.navyPanel);
    for (const y of [0.3, 0.5, 0.7]) B.add(gBox(0.012, 0.012, d - 0.04), M4.trs(x + s * 0.022, y, zc), MONMAT.steel);
    // [V] portrait monitor fills the top third of the panel (sp_09), ~0.33 x 0.60 m centred at 1.68 m
    B.add(gRBox(0.36, 0.64, 0.012, 0.008, 1), M4.trs(x + s * 0.026, 1.68, zc, s * Math.PI / 2), SEATMAT.bezel);
    B.add(gQuad(0.33, 0.60), M4.trs(x + s * 0.033, 1.68, zc, s * Math.PI / 2), SEATMAT.screen, atlasUV('screen'));
  }
}

// ---- Door-2 aft centre monument, across the galley passage from the welcome galley (lalf_133): a flat ash wall with
// aluminium-framed stowage flaps (~0.55 x 0.85 m at 0.85-1.70 m, red latch at the top centre) and two low aluminium rails
function buildAshWall(B, m) {
  const w = m.x1 - m.x0, cx = (m.x0 + m.x1) / 2, F = (x, y, o) => faceXF(m, x, y, o);
  monoBody(B, m, MONMAT.barAsh);
  const n = Math.max(1, Math.round(w / 0.62)), pw = Math.min(0.55, w / n - 0.07);
  for (let k = 0; k < n; k++) {
    const x = m.x0 + (w / n) * (k + 0.5);
    B.add(gRBox(pw, 0.85, 0.012, 0.004, 1), F(x, 1.28, 0.006), MONMAT.barAsh);
    for (const [bw, bh, bx, by] of [[pw + 0.06, 0.03, 0, 0.44], [pw + 0.06, 0.03, 0, -0.44], [0.03, 0.85, pw / 2 + 0.015, 0], [0.03, 0.85, -pw / 2 - 0.015, 0]])
      B.add(gBox(bw, bh, 0.016), F(x + bx, 1.28 + by, 0.008), MONMAT.alu);
    B.add(gRBox(0.04, 0.025, 0.02, 0.006, 1), F(x, 1.69, 0.02), MONMAT.red);
  }
  for (const y of [0.35, 0.80]) B.add(gRBox(w - 0.12, 0.022, 0.03, 0.01, 1), F(cx, y, 0.03), MONMAT.alu);
  B.add(gBox(w - 0.02, 0.07, 0.02), F(cx, 0.035, 0.01), MONMAT.black);
}
// dark warm soffit over the door-2 galley passage, 6 downlights in two rows and a vent grille (lalf_133 / lalf_134)
function passageSoffit(B, x0, x1, z0, z1) {
  const y = 2.13, zc = (z0 + z1) / 2;
  B.add(gBox(x1 - x0, 0.02, z1 - z0), M4.trs((x0 + x1) / 2, y + 0.01, zc), MONMAT.soffit);
  for (const x of [-1.85, -1.35, -0.5, 0, 0.5, 1.35, 1.85]) for (const dz of [-0.22, 0.22]) {
    B.add(gCyl(0.04, 0.04, 0.006, 16), M4.trs((x0 + x1) / 2 + x, y - 0.002, zc + dz), MONMAT.steel);
    B.add(gCyl(0.03, 0.03, 0.006, 16), M4.trs((x0 + x1) / 2 + x, y - 0.004, zc + dz), MONMAT.downlight);
  }
  B.add(gQuad(0.3, 0.12), M4.mul(M4.trs((x0 + x1) / 2 + 0.25, y - 0.001, zc), M4.trs(0, 0, 0, 0, Math.PI / 2)), MAT.grille);
}

// ---- Standard galley (SANspotter "self serve snack bar" photo at door 4): full-size trolleys under a black work
// deck with red-copper turn-button latches; ovens / beverage makers / standard units and stowage in a set-back
// upper bank with a work light under it
function buildGalley(B, m, premium) {
  const w = m.x1 - m.x0, cx = (m.x0 + m.x1) / 2, set = 0.3, dk = 1.03;
  // standard aluminium/white inserts in every class (omaatF_33: grey aluminium units at the F galley too); ash stays on
  // the door-3 bar and the door-2 welcome galley only
  const body = MONMAT.galleyWhite;
  monoStepBody(B, m, dk, set, m.ashDoors ? MONMAT.barAsh : body, body);
  const F = (x, y, o) => faceXF(m, x, y, o);
  if (m.ashDoors) {
    // door-2 premium galleys: ash lower doors with an aluminium counter edge on both sides of the passage (sp_09,
    // omaat_ANA-Business-Class-The-Room-32) instead of bare carts [V]
    const cw = w - 0.06, n = Math.max(2, Math.round(cw / 0.36));
    B.add(gBox(cw, 0.07, 0.024), F(cx, 0.035, 0.008), MONMAT.black);
    for (let k = 0; k < n; k++) {
      const x = m.x0 + 0.03 + (cw / n) * (k + 0.5);
      if (Math.abs(x) > wallAt(0.5)[0] - 0.15 || (m.jumpX !== undefined && Math.abs(x - m.jumpX) < 0.3)) continue;
      B.add(gRBox(cw / n - 0.01, 0.90, 0.014, 0.004, 1), F(x, 0.54, 0.012), MONMAT.barAsh);
      ringPull(B, faceXF(m, x + (k % 2 ? -1 : 1) * m.face * (cw / n / 2 - 0.05), 0.84, 0.019));
    }
  }
  const nC = m.ashDoors ? 0 : m.carts || 2, usable = w - 0.1;
  const cw = Math.min(0.31, usable / nC - 0.02);
  for (let k = 0; k < nC; k++) {
    const x = m.x0 + 0.05 + (usable / nC) * (k + 0.5);
    if (Math.abs(x) > wallAt(0.5)[0] - 0.2) continue;
    const G = (dx, y, o) => F(x + dx, y, o);
    B.add(gRBox(cw, 0.98, 0.05, 0.012, 1), G(0, 0.5, 0.02), MONMAT.alu);
    B.add(gRBox(cw - 0.03, 0.03, 0.02, 0.008, 1), G(0, 0.94, 0.05), MONMAT.aluDark);            // push handle
    B.add(gQuad(0.12, 0.08), G(0, 0.8, 0.046), MONMAT.card);
    if (k % 2 === 0) B.add(gQuad(cw * 0.55, 0.16), G(0, 0.26, 0.046), MAT.grille);             // air-chilled vent
    for (const s of [-1, 1]) {
      B.add(gRBox(0.022, 0.035, 0.03, 0.008, 1), G(s * (cw / 2 + 0.005), dk - 0.03, 0.05), MONMAT.copper);
      B.add(gRBox(0.04, 0.016, 0.018, 0.006, 1), G(s * (cw / 2 - 0.02), 0.04, 0.06), MONMAT.copper);
    }
  }
  B.add(gRBox(w - 0.04, 0.035, set + 0.03, 0.008, 1), F(cx, dk + 0.0175, (0.03 - set) / 2), MONMAT.deck);
  B.add(gRBox(w - 0.06, 0.03, 0.025, 0.01, 1), F(cx, dk + 0.005, 0.03), MONMAT.alu);
  const o = 0.01 - set;
  B.add(gBox(w - 0.12, 0.012, 0.03), F(cx, 1.285, o + 0.02), MONMAT.workLight);
  const nU = Math.max(2, Math.round(w / 0.38));
  for (let k = 0; k < nU; k++) {
    const x = m.x0 + 0.05 + ((w - 0.1) / nU) * (k + 0.5);
    if (Math.abs(x) > wallAt(1.5)[0] - 0.25) continue;
    const uW = (w - 0.1) / nU - 0.03, t = k % 3;
    if (t === 0) {        // oven: aluminium door, meal-label window, lever latch
      B.add(gRBox(uW, 0.32, 0.04, 0.01, 1), F(x, 1.47, o + 0.02), MONMAT.alu);
      B.add(gRBox(uW * 0.55, 0.12, 0.01, 0.006, 1), F(x - uW * 0.12, 1.55, o + 0.042), { c: '#9c9a74', r: 0.2, e: 0.05 });
      B.add(gRBox(uW * 0.5, 0.035, 0.03, 0.01, 1), F(x - uW * 0.12, 1.4, o + 0.05), MONMAT.aluDark);
      for (const s of [-1, 1]) B.add(gRBox(0.016, 0.03, 0.02, 0.006, 1), F(x + s * uW * 0.3, 1.3, o + 0.05), MONMAT.copper);
    } else if (t === 1) { // beverage maker (sans_38): black brew head with green-lit key over a recessed bay; the steel
      //                     jug stands inside the bay on a drip tray, under the head
      B.add(gRBox(uW, 0.12, 0.12, 0.01, 1), F(x, 1.57, o + 0.06), MONMAT.bevBlack);
      B.add(gBox(0.022, 0.018, 0.006), F(x, 1.6, o + 0.122), MONMAT.green);
      B.add(gBox(uW, 0.2, 0.01), F(x, 1.41, o + 0.005), MONMAT.bevBlack);                                   // bay back
      for (const s of [-1, 1]) B.add(gBox(0.015, 0.2, 0.12), F(x + s * (uW / 2 - 0.0075), 1.41, o + 0.06), MONMAT.bevBlack);
      B.add(gBox(uW - 0.04, 0.01, 0.1), F(x, 1.295, o + 0.06), MONMAT.steelDark);                          // drip tray
      B.add(gCyl(0.05, 0.055, 0.13, 12), F(x, 1.365, o + 0.06), MONMAT.steel);
      B.add(gBox(0.04, 0.02, 0.05), F(x, 1.5, o + 0.07), MONMAT.steelDark);                                // brew spout
    } else {              // standard unit with recessed pull
      B.add(gRBox(uW, 0.32, 0.03, 0.01, 1), F(x, 1.47, o + 0.015), MONMAT.aluDark);
      B.add(gRBox(0.08, 0.025, 0.02, 0.006, 1), F(x, 1.59, o + 0.035), MONMAT.bevBlack);
    }
    B.add(gRBox(uW, 0.36, 0.03, 0.01, 1), F(x, 1.86, o + 0.015), MONMAT.galleyWhite);
    B.add(gRBox(uW - 0.04, 0.32, 0.004, 0.006, 1), F(x, 1.86, o + 0.032), { c: '#c9c6bf', r: 0.45 });        // inset panel
    B.add(gQuad(0.07, 0.03), F(x, 1.99, o + 0.0345), MONMAT.card);
    B.add(gRBox(0.06, 0.018, 0.012, 0.006, 1), F(x, 1.72, o + 0.036), MONMAT.aluDark);                          // paddle
    for (const s of [-1, 1]) B.add(gRBox(0.016, 0.03, 0.02, 0.006, 1), F(x + s * uW * 0.3, 1.69, o + 0.04), MONMAT.copper);
  }
  B.add(gQuad(0.2, 0.04), F(cx, 1.655, o + 0.032), MAT.decal, atlasUV('galleyLbl'));
}

// ---- Class curtains: ceiling track across the aisle opening, curtain gathered open as a pleated bundle at xg, tied back
// at ~1.15 m and flaring to ~0.3 m at the hem (tpg_The-Room-small-cabin-front_71, tpg_The-Suite-cabin_147) [V shape, A sizes]
const CURTAIN_H = 2.18;
let _curtainGeo = null, _curtainTie = null;
function curtainLoft(levels, n = 44) {
  const g = raw();
  for (const [y, s, d = s] of levels) for (let k = 0; k <= n; k++) {
    const a = (k / n) * Math.PI * 2, r = 1 + 0.16 * Math.sin(a * 11);
    g.p.push(Math.cos(a) * 0.10 * r * s, y, Math.sin(a) * 0.065 * r * d); g.n.push(Math.cos(a) * 0.6, 0, Math.sin(a)); g.u.push(k / n, y);
  }
  for (let j = 0; j + 1 < levels.length; j++) for (let k = 0; k < n; k++) {
    const q = j * (n + 1) + k; g.i.push(q, q + n + 1, q + 1, q + 1, q + n + 1, q + n + 2);
  }
  return fixWinding(g);
}
// Two forms (w2, tpg_70/_71/_147, alv_IMG_7182/7207/7209): 'tied' (F/J + J lines) pressed against the panel edge, tied
// at ~1.5 m, ~0.2 m wide at the hem and fanning to ~0.3 m under the track; 'panel' (F front, J/PY, PY aft, rear) a wide
// untied pleated panel ~0.3 m across, gathered against the panel edge. xg = bundle centre, ~0.16 m off that edge.
let _curtainPanel = null;
function addCurtain(B, xa, xb, z, xg, mat, tied = false) {
  if (!_curtainGeo) {
    _curtainGeo = curtainLoft([[0.02, 1.0, 0.9], [0.8, 0.9, 0.8], [1.42, 0.52], [1.55, 0.52], [1.8, 1.1, 0.9], [CURTAIN_H - 0.01, 1.5, 0.9]]);
    _curtainTie = curtainLoft([[1.44, 0.58], [1.53, 0.58]]);
    _curtainPanel = curtainLoft([[0.02, 1.55, 1.3], [1.0, 1.5, 1.25], [CURTAIN_H - 0.01, 1.45, 1.2]]);
  }
  B.add(gBox(Math.abs(xb - xa), 0.02, 0.035), M4.trs((xa + xb) / 2, CURTAIN_H + 0.01, z), MONMAT.rail);
  if (!tied) { B.add(_curtainPanel, M4.trs(xg, 0, z), mat); return; }
  B.add(_curtainGeo, M4.trs(xg, 0, z), mat);
  B.add(_curtainTie, M4.trs(xg, 0, z), MONMAT.curtainTie);
}

// one monument, z-facing (face +1: front at z1 facing aft, -1: front at z0 facing forward)
function buildMon(B, m, layout, cls) {
  const w = m.x1 - m.x0, cx = (m.x0 + m.x1) / 2;
  const inner = Math.abs(m.x0) < Math.abs(m.x1) ? m.x0 : m.x1;
  const premium = cls === 'F' || cls === 'J';
  const F = (x, y, o) => faceXF(m, x, y, o);
  if (m.kind === 'lav') {
    // exterior per the bar render (J lavs flanking the bar): ash door with dark-bronze frame lines, occupancy
    // plate (VACANT window) inboard of a recessed square pull, small ashtray high on the outboard side, lit sign
    monoBody(B, m, cls === 'F' ? MONMAT.darkWood : premium ? MONMAT.ash : MONMAT.laminate);
    const dw = Math.min(m.access ? 0.78 : m.jumpX !== undefined ? 0.56 : 0.62, w - 0.14);
    const dx = Math.abs(inner) < 0.05 ? cx : inner + Math.sign(cx - inner) * (dw / 2 + (m.jumpX !== undefined ? 0.03 : 0.06));
    const J = cls === 'J', hw = MONMAT.steelDark;
    const so = Math.abs(cx) < 0.05 ? 1 : Math.sign(cx) * m.face;          // viewer-right sign of the outboard side
    const at = (u, y, o) => F(dx + u * m.face, y, o);
    B.add(gRBox(dw, 1.86, 0.02, 0.01, 1), F(dx, 0.95, 0.008), cls === 'F' ? MONMAT.darkWoodDoor : J ? MONMAT.barAsh : MONMAT.lavDoor);
    if (J) {
      // [V] omaat_ANA-Business-Class-The-Room-32 (the only in-service view of a THE Room lav): plain ash leaf, white
      // 0.04 m bi-fold seam strip, white vertical grab handle 0.04 x 0.25 m at 1.0-1.25 m, small white lock slot at
      // ~0.88 m; no bronze frame (that was the press render)
      B.add(gBox(0.04, 1.8, 0.024), F(dx, 0.95, 0.009), MONMAT.plateWhite);
      B.add(gRBox(0.04, 0.25, 0.03, 0.015, 1), at(so * dw * 0.38, 1.12, 0.035), MONMAT.plateWhite);
      B.add(gRBox(0.03, 0.05, 0.012, 0.01, 1), at(so * dw * 0.38, 0.88, 0.024), MONMAT.plateWhite);
      B.add(gBox(0.014, 0.02, 0.004), at(so * dw * 0.38, 0.88, 0.031), MONMAT.green);
    } else {
      B.add(gBox(0.006, 1.8, 0.024), F(dx, 0.95, 0.009), { c: '#9ea3a9', r: 0.5 });                 // bi-fold seam
      B.add(gRBox(0.075, 0.085, 0.012, 0.006, 1), at(so * dw * 0.38, 1.15, 0.024), hw);                // recessed pull
      B.add(gRBox(0.05, 0.055, 0.01, 0.004, 1), at(so * dw * 0.38, 1.15, 0.028), MONMAT.bevBlack);
    }
    if (!J) {
      B.add(gRBox(0.11, 0.05, 0.012, 0.006, 1), at(so * dw * 0.18, 1.15, 0.024), hw);                  // occupancy plate
      B.add(gRBox(0.08, 0.022, 0.006, 0.003, 1), at(so * dw * 0.18, 1.15, 0.03), { c: '#dfe6dc', r: 0.4, e: 0.25 });
      B.add(gBox(0.03, 0.006, 0.004), at(so * dw * 0.18 - 0.02, 1.15, 0.034), MONMAT.green);
    }
    B.add(gRBox(0.06, 0.07, 0.014, 0.006, 1), at(so * (dw / 2 + 0.07), 1.62, 0.008), J ? MONMAT.bevBlack : hw);   // ashtray (black, tpg_71)
    B.add(gRBox(0.045, 0.02, 0.008, 0.003, 1), at(so * (dw / 2 + 0.07), 1.64, 0.016), MONMAT.bevBlack);
    B.add(gRBox(dw - 0.1, 0.12, 0.006, 0.004, 1), F(dx, 0.12, 0.02), MAT.grille);
    B.add(gQuad(0.17, 0.082), F(dx, 1.99, 0.021), MAT.exitGlow, atlasUV('lav'));
    if (m.access) B.add(gRBox(0.09, 0.09, 0.006, 0.01, 1), F(dx - dw * 0.3, 1.45, 0.02), { c: '#2d62b8', r: 0.5 });
  } else if (m.kind === 'sideStorage') {
    monoBody(B, m, MONMAT.closet);
    B.add(gRBox(Math.abs(m.x1 - m.x0) - 0.06, 0.02, m.z1 - m.z0 - 0.06, 0.01, 1), M4.trs(cx, m.h + 0.005, (m.z0 + m.z1) / 2), { c: '#cfccc5', r: 0.4, l: LAYER.plastic });
  } else if (m.kind === 'closet') {
    monoBody(B, m, cls === 'F' ? MONMAT.darkWood : premium ? MONMAT.ash : MONMAT.closet);
    // m.jumpX: a folded jump seat shares the face, so the door narrows to the inboard part
    const dw = m.jumpX !== undefined ? Math.min(0.42, w - 0.52) : Math.min(0.72, w - 0.1);
    const dcx = m.jumpX !== undefined ? (Math.abs(m.x0) < Math.abs(m.x1) ? m.x0 + 0.03 + dw / 2 : m.x1 - 0.03 - dw / 2) : cx;
    B.add(gRBox(dw, m.h - 0.12, 0.02, 0.01, 1), F(dcx, m.h / 2, 0.008), premium ? (cls === 'F' ? MONMAT.darkWoodDoor : MONMAT.ashDark) : MONMAT.lavDoor);
    B.add(gRBox(0.03, 0.14, 0.03, 0.01, 1), F(dcx - dw * 0.38 * Math.sign(dcx - cx || -1), Math.min(1.05, m.h * 0.6), 0.03), MONMAT.steel);
    if (m.low) B.add(gRBox(w - 0.02, 0.03, m.z1 - m.z0 - 0.02, 0.01, 1), M4.trs(cx, m.h + 0.012, (m.z0 + m.z1) / 2), cls === 'F' ? MONMAT.darkWood : MONMAT.ash);
  } else if (m.kind === 'bar') {
    buildBar(B, m);
  } else if (m.kind === 'galley') {
    if (m.welcome) buildWelcomeGalley(B, m); else if (m.ashWall) buildAshWall(B, m); else buildGalley(B, m, premium);
    if (m.soffitTo !== undefined) { const xs = Math.min(2.15, wallAt(2.13)[0] - 0.05); passageSoffit(B, -xs, xs, Math.min(m.z1, m.soffitTo), Math.max(m.z1, m.soffitTo)); }
    if (m.welcomeEnd) welcomeEnds(B, m);
    if (!premium && m.face === -1 && !m.xFacing && clsAt(layout, m.z1 + 0.5) === 'Y') {
      // aft face over the first centre row (row 31 D-G): one shared monitor per seat (4 blue bars on the ANA seat map)
      // + bassinet mounts
      const zb = m.z1 + 0.004;
      for (const x of [-0.75, -0.25, 0.25, 0.75]) tiltMonitor(B, M4.trs(x, 1.78, zb));   // housings as on the J/PY wall (py_37303)
      B.add(gQuad(0.09, 0.06), M4.trs(0, 1.30, zb), MAT.decal, atlasUV('bassinet'));
      B.add(gRBox(0.3, 0.03, 0.02, 0.01, 1), M4.trs(0, 1.22, zb + 0.008), MONMAT.steelDark);
    }
  } else if (m.kind === 'cockpit') {
    // [V] tpa_IMG_0260: ebony leaf in a white/aluminium frame, two white-framed bolt plates (upper one with the
    // "CREW ONLY" placard + viewer), lever on the right, yellow/black kick plate
    const m2 = { ...m, face: 1 }, dw = w - 0.06, P = (x, y, o) => faceXF(m2, cx + x, y, o);
    B.add(gRBox(w, 2.02, 0.04, 0.006, 1), P(0, 1.01, -0.01), MONMAT.cockpitFrame);
    B.add(gRBox(dw, 1.96, 0.05, 0.01, 1), P(0, 0.99, 0.0), MONMAT.cockpitDoor);
    for (const y of [1.55, 0.55]) {
      const pw = Math.min(0.3, dw - 0.14);
      for (const [bw, bh, bx, by] of [[pw, 0.03, 0, 0.135], [pw, 0.03, 0, -0.135], [0.03, 0.3, pw / 2 - 0.015, 0], [0.03, 0.3, 0.015 - pw / 2, 0]])
        B.add(gBox(bw, bh, 0.012), P(bx, y + by, 0.03), MONMAT.plateWhite);
      B.add(gBox(0.07, 0.05, 0.014), P(0, y - 0.15, 0.03), MONMAT.plateWhite);                  // bolt tab
    }
    B.add(gQuad(0.08, 0.035), P(0, 1.64, 0.026), MONMAT.label);                                   // CREW ONLY placard
    B.add(gQuad(0.03, 0.03), P(0, 1.60, 0.0262), MONMAT.red);
    B.add(gCyl(0.012, 0.012, 0.01, 10), M4.mul(P(0, 1.52, 0.03), M4.trs(0, 0, 0, 0, Math.PI / 2)), MONMAT.steel);
    B.add(gRBox(0.08, 0.14, 0.03, 0.02, 1), P(dw / 2 - 0.08, 1.02, 0.035), MONMAT.plateWhite);   // lever housing
    B.add(gRBox(0.03, 0.12, 0.03, 0.01, 1), P(dw / 2 - 0.08, 0.98, 0.055), MONMAT.steel);
    B.add(gBox(dw, 0.05, 0.012), P(0, 0.035, 0.03), { c: '#b8962a', r: 0.5 });                   // kick plate
    // access keypad on the corridor's right-hand wall, just aft of the door
    B.add(gQuad(0.08, 0.1), M4.trs(m.x1 + 0.012, 1.25, m.z1 + 0.25, -Math.PI / 2), MAT.decal, atlasUV('keypad'));
  } else if (m.kind === 'partition') {
    buildBulkhead(B, m, layout);
  } else if (m.kind === 'skin') {
    // thin wall lining, e.g. the ebony flight-deck corridor side of the forward centre galley (tpa_IMG_0260)
    B.add(gBox(w, m.h, m.z1 - m.z0), M4.trs(cx, m.h / 2, (m.z0 + m.z1) / 2), MONMAT[m.mat] || MONMAT.laminate);
  } else if (m.kind === 'curtain') {
    // explicit curtain: M('curtain', xa, xb, z, z, { xg, tone: 'F' | 'Y' | 'C' }) - track xa..xb, gathered at xg
    addCurtain(B, m.x0, m.x1, m.z0, m.xg ?? m.x0 + 0.16, { F: MONMAT.curtainF, C: MONMAT.curtainC, R: MONMAT.curtainRear }[m.tone] || MONMAT.curtainY, m.tone === 'C');
  }
  if (m.back && !m.xFacing) monoBack(B, m);
  if (m.cap) B.add(gBox(w, m.cap - m.h, m.z1 - m.z0), M4.trs(cx, (m.h + m.cap) / 2, (m.z0 + m.z1) / 2), MONMAT.galleyWhite);   // closes the lit slot to the ceiling
  // shared monitor for the row across the cross-aisle (row 30 behind door 4: blue bars under the wheelchair lav and the
  // right galley on the ANA map); on a galley it hangs on the set-back upper bank, above the work deck
  if (m.rowMonitor !== undefined) {
    const zf = m.face > 0 ? m.z1 : m.z0, o = m.kind === 'galley' ? -0.3 + 0.01 : 0.004;
    tiltMonitor(B, M4.trs(m.rowMonitor, m.kind === 'galley' ? 1.88 : 1.80, zf + m.face * o, m.face > 0 ? 0 : Math.PI));
  }
  // door-4 lav facing the door-4 cross-aisle: white framed literature pockets outboard of its door (y_47302: pair at
  // ~0.95 / 1.35 m on the wall ahead of the exit row)
  if (m.kind === 'lav' && m.face === 1 && !m.xFacing && Math.abs(m.z1 - layout.doorsZ[3][0]) < 0.05 && Math.abs(cx) > 1.2)
    for (const y of [0.95, 1.35]) litPocket(B, M4.trs(Math.sign(cx) * 2.42, y, m.z1 + 0.002), MONMAT.pocketWhite);
}

// ---- Class bulkheads (F/J and J/PY), full height to the bin line and following the sidewall (omaatF_2,
// omaat_room_36, py_37303 / py_37302). The finish is per face and per cabin: F = washi print, J = cream laminate,
// PY = off-white laminate, each with a slate kick strip; literature pockets / wall boxes on the outboard panels,
// tilted shared monitors + bassinet mounts on the J/PY aft face.
// washi-print UVs across the cabin width (x) and up a wall of height H (the atlas 'washi' panel)
// F-zone ink-cloud wall: a 0.1 m grid following the sidewall, clouds baked into vertex colours (denser low, fading up)
function inkWall(B, x0, x1, H, zf, f) {
  const g = raw(), nx = Math.max(2, Math.ceil((x1 - x0) / 0.1)), ny = Math.ceil(H / 0.1);
  for (let j = 0; j <= ny; j++) {
    const y = (H * j) / ny, a = Math.max(x0, -wallAt(y)[0] + 0.012), b = Math.min(x1, wallAt(y)[0] - 0.012);
    for (let i = 0; i <= nx; i++) { g.p.push(lerp(a, b, i / nx), y, zf); g.n.push(0, 0, f); g.u.push(0, 0); }
  }
  for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const q = j * (nx + 1) + i; g.i.push(q, q + 1, q + nx + 2, q, q + nx + 2, q + nx + 1); }
  fixWinding(g);
  const base = B.p.length / 3, g0 = hexRGB(MONMAT.inkGround.c), c1 = hexRGB(MONMAT.inkCloud);
  B.add(g, null, MONMAT.inkGround);
  for (let k = base; k < B.p.length / 3; k++) {
    const x = B.p[k * 3], y = B.p[k * 3 + 1];
    const n = fbm(x / 0.5 + 40, y / 0.38 + 3, 256, 4, 23), lowY = clamp(1.15 - 0.45 * y / H, 0.5, 1);
    const t = clamp((n - 0.40) / 0.26, 0, 1) ** 1.3 * lowY;
    for (let c = 0; c < 3; c++) B.c[k * 4 + c] = Math.round(lerp(g0[c], c1[c], t));
  }
}
function washiUV(H) {
  const wr = ATL.rects.washi;
  return (k, g) => [wr[0] + clamp((g.p[k * 3] + 2.9) / 5.8, 0, 1) * (wr[2] - wr[0]), wr[1] + clamp(1 - g.p[k * 3 + 1] / H, 0, 1) * (wr[3] - wr[1])];
}
// exposed back of a door-zone monument facing a seat zone (m.back = 'F' | 'J' | 'PY'), finished like the class
// bulkheads: F = washi print (omaatF_2 / tpa_IMG_0220: full-height pale mottled wall ahead of row 1), J = cream laminate
// with a wall box on outboard panels, PY = off-white laminate with two small grey boxes at head height (py_37302:
// wall behind row 27, ~0.25 x 0.15 m at ~1.7 m, x ~ +-0.5)
function monoBack(B, m) {
  const f = -m.face, zf = f > 0 ? m.z1 : m.z0, H = m.h, w = m.x1 - m.x0, cx = (m.x0 + m.x1) / 2;
  const mat = m.back === 'F' ? MONMAT.bulkF : m.back === 'J' ? MONMAT.bulkJ : MONMAT.bulkPY;
  if (m.back === 'F') inkWall(B, m.x0, m.x1, H, zf + f * 0.002, f);
  else B.add(gExtrude(monoSection(m.x0, m.x1, H), 0.004, 20), M4.trs(0, 0, zf + f * 0.002), mat);
  B.add(gBox(w - 0.02, 0.08, 0.006), M4.trs(cx, 0.04, zf + f * 0.006), MONMAT.kick);
  const X = (x, y, o = 0.005) => M4.trs(x, y, zf + f * o, f > 0 ? 0 : Math.PI);
  if (m.back === 'PY') {
    for (const u of [-0.45, 0.45]) {
      B.add(gRBox(0.26, 0.14, 0.06, 0.012, 1), M4.mul(X(cx + u, 1.72), M4.trs(0, 0, 0.03)), MONMAT.pocketGrey);
      B.add(gBox(0.2, 0.012, 0.004), M4.mul(X(cx + u, 1.66), M4.trs(0, 0, 0.061)), { c: '#6d7178', r: 0.6 });
    }
  } else if (Math.abs(cx) > 1.3) litPocket(B, X(cx - Math.sign(cx) * 0.1, 1.62), MONMAT.wallBox, 0.14, 0.26);   // [V] just under the bins (tpg_71, tt cabin-1)
  else if (m.back === 'J' && w > 1.2) for (const u of [-0.5, 0.5]) litPocket(B, X(cx + u * (w - 0.4) / 1.2, 1.55), MONMAT.wallBox, 0.20, 0.42);   // [V] tpg_70 / _71 centre wall boxes
}

// J/PY shared monitor, in-service form (alv_IMG_7207 / 7209, 2026): flat-mounted landscape screen in a rounded charcoal
// frame ~0.50 x 0.34 m at seated eye height, ~1.5 m [V]; ANA's py_37303 shows light-grey tilted housings (older fit)
function flatMonitor(B, xf) {
  B.add(gRBox(0.50, 0.34, 0.04, 0.03, 2), M4.mul(xf, M4.trs(0, 0, 0.02, 0, 0.04)), MONMAT.monFrame);
  B.add(gQuad(0.42, 0.25), M4.mul(xf, M4.trs(0, 0.005, 0.0405, 0, 0.04)), SEATMAT.screen, atlasUV('screen'));
}
function buildBulkhead(B, m, layout) {
  const t = m.z1 - m.z0, w = m.x1 - m.x0, cx = (m.x0 + m.x1) / 2, outboard = Math.abs(cx) > 1.3;
  // [V] alv_IMG_7209: the J/PY outboard panels stop at ~1.8 m with a capped top and an open gap up to the bins; the
  // centre panel runs up to the ceiling
  const jpy = clsAt(layout, m.z1 + 0.5) === 'PY', H = jpy && outboard ? 1.80 : Math.max(m.h, 2.10);
  const sec = monoSection(m.x0, m.x1, H);
  B.add(gExtrude(sec, t - 0.008, 20), M4.trs(0, 0, (m.z0 + m.z1) / 2), MONMAT.bulkCore);
  if (jpy && outboard) {                                              // rounded cap rail on the open top
    const xw = wallAt(H)[0] - 0.012, a = Math.max(m.x0, -xw), b = Math.min(m.x1, xw);
    B.add(gRBox(b - a, 0.025, t + 0.02, 0.01, 1), M4.trs((a + b) / 2, H + 0.0125, (m.z0 + m.z1) / 2), MONMAT.bulkPY);
  }
  const face = gExtrude(sec, 0.004, 20);
  for (const f of [-1, 1]) {                     // -1: forward face (z0), +1: aft face (z1)
    const zf = f > 0 ? m.z1 : m.z0, c = clsAt(layout, zf + f * 0.5), other = clsAt(layout, zf - f * 0.5);
    const mat = c === 'F' ? MONMAT.bulkF : c === 'J' ? MONMAT.bulkJ : MONMAT.bulkPY;
    if (c === 'F') inkWall(B, m.x0, m.x1, H, zf + f * 0.001, f);
    else B.add(face, M4.trs(0, 0, zf - f * 0.002), mat);
    B.add(gBox(w - 0.02, 0.08, 0.006), M4.trs(cx, 0.04, zf + f * 0.002), MONMAT.kick);
    const X = (x, y) => M4.trs(x, y, zf + f * 0.003, f > 0 ? 0 : Math.PI);
    if (c === 'J' && other === 'F' && !outboard) {
      // J face of F/J (omaat_room_36): inset horizontal panel seam at ~1.45 m, two small blue placards at ~1.75 m
      B.add(gBox(w - 0.2, 0.006, 0.004), X(cx, 1.45), MONMAT.seamJ);
      for (const u of [-0.35, 0.35]) B.add(gQuad(0.08, 0.05), M4.mul(X(cx + u, 1.75), M4.trs(0, 0, 0.001)), MONMAT.placardBlue);
      for (const u of [-0.62, 0.62]) litPocket(B, X(cx + u, 1.58), MONMAT.wallBox, 0.20, 0.42);   // [V] centre wall boxes (tpg_71)
    }
    if (!outboard) continue;
    // PY outboard panel: two grey fabric pouches with an elastic top at floor level under the monitors (alv_IMG_7207) [V]
    if (c === 'PY') for (const u of [-0.26, 0.26]) {
      B.add(gRBox(0.22, 0.26, 0.07, 0.03, 2), M4.mul(X(cx + u, 0.22), M4.trs(0, 0, 0.035)), MONMAT.pouch);
      B.add(gRBox(0.2, 0.02, 0.075, 0.01, 1), M4.mul(X(cx + u, 0.345), M4.trs(0, 0, 0.037)), MONMAT.pouchBand);
      B.add(gQuad(0.12, 0.05), M4.mul(X(cx + u, 0.37), M4.trs(0, 0, 0.05)), MONMAT.cardBlue);
    }
    else litPocket(B, X(cx - Math.sign(cx) * 0.1, 1.62), MONMAT.wallBox, 0.14, 0.26);                               // F / J wall box, under the bins
  }
  const zf = m.z1 + 0.004;
  if (m.bassinet) {
    const n = Math.max(1, Math.round(w / 0.9));
    for (let k = 0; k < n; k++) {
      const x = m.x0 + (w / n) * (k + 0.5);
      if (Math.abs(x) > 2.5) continue;
      B.add(gQuad(0.09, 0.06), M4.trs(x, 0.95, zf), MAT.decal, atlasUV('bassinet'));                   // [V] sticker ~0.95 m (alv_IMG_7207)
      B.add(gRBox(0.3, 0.03, 0.02, 0.01, 1), M4.trs(x, 1.08, zf + 0.008), MONMAT.steelDark);
    }
  }
  // one shared monitor per seat pair / seat: 2 per outboard panel (A/C, H/K) and 4 in the centre (D-G) as the blue
  // bars on the ANA map; py_37303 shows the two housings side by side on the outboard panel
  if (m.monitor) for (const x of Math.abs(cx) < 0.1 ? [-0.84, -0.28, 0.28, 0.84] : [cx - 0.285, cx + 0.285]) flatMonitor(B, M4.trs(x, 1.50, zf));
}

function buildMonuments(gl, layout, opts = {}) {
  const B = new Builder();
  for (const m of layout.mon) {
    const cls = clsAt(layout, (m.z0 + m.z1) / 2);
    if (m.face === '+x' || m.face === '-x') {
      // x-facing monument (e.g. the fore-aft door-5 galley blocks): built z-facing in a local frame whose width runs
      // along world z, then turned about y so the front points to +x / -x. No sidewall clipping in this frame, so
      // use it only for monuments inboard of the sidewall.
      const L = m.z1 - m.z0, D = m.x1 - m.x0;
      const R = M4.trs((m.x0 + m.x1) / 2, 0, (m.z0 + m.z1) / 2, m.face === '+x' ? Math.PI / 2 : -Math.PI / 2);
      const P = { add: (g, xf, mat, uv) => B.add(g, xf ? M4.mul(R, xf) : R, mat, uv) };
      buildMon(P, { ...m, x0: -L / 2, x1: L / 2, z0: -D / 2, z1: D / 2, face: 1, xFacing: true }, layout, cls);
    } else buildMon(B, m, layout, cls);
  }
  // ---- door-5 galley work aisle: the aft wall between the two fore-aft galleys carries stowage compartments (2 x 3
  //      latched doors over a waste flap) instead of a blank wall [A: standard 777 aft galley, no photo of this fit]
  const gl5 = layout.mon.filter((m) => m.kind === 'galley' && (m.face === '+x' || m.face === '-x') && Math.abs(m.z1 - CAB.zAft) < 0.05);
  if (gl5.length === 2) {
    const xa = Math.min(gl5[0].x1, gl5[1].x1), xb = Math.max(gl5[0].x0, gl5[1].x0), zw = CAB.zAft - 0.03, cw = (xb - xa - 0.04) / 3;
    const Wf = (x, y, o = 0) => M4.trs(x, y, zw - o, Math.PI);
    B.add(gBox(xb - xa, 2.1, 0.03), M4.trs((xa + xb) / 2, 1.05, zw + 0.015), MONMAT.galleyWhite);
    for (let i = 0; i < 3; i++) for (const y of [1.30, 1.72]) {
      const x = xa + 0.02 + cw * (i + 0.5);
      B.add(gRBox(cw - 0.02, 0.38, 0.02, 0.008, 1), Wf(x, y, 0.01), MONMAT.aluDark);
      B.add(gRBox(0.016, 0.03, 0.02, 0.006, 1), Wf(x, y + 0.15, 0.025), MONMAT.copper);
      B.add(gQuad(0.1, 0.05), Wf(x, y - 0.1, 0.021), MONMAT.card);
    }
    B.add(gBox(xb - xa - 0.04, 0.035, 0.3), M4.trs((xa + xb) / 2, 1.03, zw - 0.15), MONMAT.deck);
    B.add(gRBox(0.36, 0.5, 0.02, 0.01, 1), Wf((xa + xb) / 2, 0.45, 0.01), MONMAT.alu);                    // waste flap
    B.add(gRBox(0.2, 0.03, 0.03, 0.01, 1), Wf((xa + xb) / 2, 0.66, 0.025), MONMAT.aluDark);
  }
  // ---- class curtains, drawn open: in each aisle gap of the F/J and J/PY bulkheads (f_17313, py_37301/37302),
  //      gathered at the centre side. The PY aft-end and rear-economy curtains are explicit 'curtain' monuments.
  const parts = layout.mon.filter((m) => m.kind === 'partition').sort((a, b) => a.z0 - b.z0 || a.x0 - b.x0);
  for (let k = 0; k + 1 < parts.length; k++) {
    const a = parts[k], b = parts[k + 1];
    if (Math.abs(a.z0 - b.z0) > 0.01 || b.x0 - a.x1 < 0.2) continue;
    const zc = (a.z0 + a.z1) / 2, right = a.x1 > 0, F = clsAt(layout, a.z0 - 0.5) === 'F';
    // gathered against the outboard panel: F/J tied (tpg_71, tt cabin-1), J/PY untied (alv_IMG_7207 / 7209)
    addCurtain(B, a.x1, b.x0, zc, right ? b.x0 - (F ? 0.16 : 0.18) : a.x1 + (F ? 0.16 : 0.18), F ? MONMAT.curtainF : MONMAT.curtainY, F);
  }
  // ---- Type A door linings (translating door): outline, lever handle, arming flag, viewing window,
  //      assist handles, girt bar / slide bustle at the foot ----
  for (let di = 0; di < (opts.noDoors ? 0 : CAB.doors.length); di++) {
    const c = CAB.doors[di];
    for (const side of [-1, 1]) {
      const at = (v, inset) => { const [x, y, nx, ny] = wallAt(v); return [x * side + nx * side * inset, y + ny * inset]; };
      for (const zz of [c - 0.535, c + 0.535]) {
        const g = raw();
        for (let k = 0; k <= 12; k++) {
          const v = lerp(0.03, 1.9, k / 12);
          const [x, y, nx, ny] = wallAt(v);
          for (const dz of [-0.0025, 0.0025]) { g.p.push((x + nx * 0.003) * side, y + ny * 0.003, zz + dz); g.n.push(nx * side, ny, 0); g.u.push(0, 0); }   // 5 mm seam (from_shell)
        }
        for (let k = 0; k < 12; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
        fixWinding(g);
        B.add(g, null, MAT.doorGap);
      }
      for (const v of [0.03, 1.9]) {
        const [x, y] = at(v, 0.003);
        const [, , nx, ny] = wallAt(v);
        const tilt = Math.atan2(ny, Math.abs(nx));
        B.add(gBox(0.004, 0.012, 1.07), M4.trs(x, y, c, 0, 0, side > 0 ? -tilt : tilt), MAT.doorGap);
      }
      const [hx, hy] = at(1.05, 0.045);
      B.add(gRBox(0.05, 0.42, 0.06, 0.02, 1), M4.trs(hx, hy + 0.02, c + 0.26, 0, 0, side * 0.12), MAT.handle);
      B.add(gRBox(0.06, 0.06, 0.08, 0.02, 1), M4.trs(hx + side * 0.01, hy - 0.19, c + 0.26), MAT.handle);
      // red arming arc (~0.2 m semicircle) at ~1.15 m on the door centre line (sans_09 / sp_py_09 / lalf_133)
      const arc = [];
      for (let k = 0; k <= 12; k++) { const t = (k / 12) * Math.PI, [ax, ay] = at(1.15 + 0.1 * Math.sin(t), 0.008); arc.push([ax, ay, c + 0.1 * Math.cos(t)]); }
      B.add(gTube(arc, 0.008, 6), null, MAT.handleRed);
      const [px, py] = at(0.95, 0.006);
      B.add(gQuad(0.2, 0.106), M4.trs(px, py, c - 0.2, side > 0 ? -Math.PI / 2 : Math.PI / 2), MAT.decal, atlasUV('doorPlacard'));
      // slide bustle: full-width off-white box from the floor to ~0.80 m with a ledge on top (sans_09, from_shell)
      const [sx, sy] = at(0.41, 0.08);
      const [, , snx, sny] = wallAt(0.41), sr = side > 0 ? -Math.atan2(sny, -snx) : Math.atan2(sny, -snx);
      B.add(gRBox(0.16, 0.78, 0.98, 0.05, 2), M4.trs(sx, sy, c, 0, 0, sr), MAT.slide);
      const [lx, ly] = at(0.815, 0.09);
      B.add(gRBox(0.18, 0.03, 1.0, 0.012, 1), M4.trs(lx, ly, c, 0, 0, sr), MAT.slide);
      for (const dz of [-0.64, 0.64]) {
        const p0 = at(0.95, 0.06), p1 = at(1.55, 0.06);
        B.add(gTube([[p0[0], p0[1], c + dz], [p1[0], p1[1], c + dz]], 0.014, 8), null, MAT.handle);
      }
    }
  }
  // ---- Flight attendant jump seats (folded) on monument faces beside each door: only on plain lav / closet walls
  //      or galley end panels, never over a work deck or lav door (QA r2: the door-2 pair stood in the welcome-galley
  //      counter; sans_09 / tda_welcome3 show none there). The small boxes ahead of the door-5 galleys on the ANA map
  //      are the aft pair. [A] positions; no free wall at doors 3 / 4 (counters and lav doors only), so none there.
  const dz = layout.doorsZ;
  const jumps0 = layout.jumps || [[-1.9, dz[0][0], 1], [2.3, dz[0][0], 1], [-0.75, dz[1][0], 1], [0.75, dz[1][0], 1], [2.1, dz[3][0], 1], [-0.6, dz[4][1], -1], [0.6, dz[4][1], -1]];
  const onCounter = (x, z) => layout.mon.some((m) => (m.kind === 'galley' || m.kind === 'bar') && (m.face === 1 || m.face === -1) && m.jumpX === undefined &&
    x + 0.23 > m.x0 && x - 0.23 < m.x1 && Math.abs((m.face > 0 ? m.z1 : m.z0) - z) < 0.06);
  const jumps = opts.noDoors ? [] : jumps0.filter(([x, z]) => !onCounter(x, z));
  for (const [x, z, f] of jumps) {
    const xf = M4.trs(x, 0, z + f * 0.05, f > 0 ? 0 : Math.PI);
    B.add(gRBox(0.46, 0.5, 0.07, 0.02, 1), M4.mul(xf, M4.trs(0, 0.78, 0)), MONMAT.jump);
    B.add(gRBox(0.44, 0.34, 0.06, 0.02, 1), M4.mul(xf, M4.trs(0, 1.25, -0.005)), MONMAT.jump);
    for (const s of [-1, 1]) B.add(gBox(0.04, 0.6, 0.012), M4.mul(xf, M4.trs(s * 0.12, 1.1, 0.04)), MONMAT.harness);
    B.add(gRBox(0.40, 0.46, 0.14, 0.02, 1), M4.mul(xf, M4.trs(0, 0.25, 0.02)), MONMAT.jumpBase);
  }
  const geo = B.build();
  return { mesh: gl ? gl.mesh(geo, { name: 'monuments', layer: 'mono' }) : null, geo };
}

// ---- Monument layout amendments (QA r2), applied on top of 05_layout's map by wrapping buildLayout. They follow the
// official ANA seat map (ref/web/monuments/ana_b-777-300ER-n212map.png) and move whole row groups, so they belong in
// buildLayout; they live here because this fixer may edit 10_mono.js only. Fold them into 05_layout.js later (the
// guard skips the pass once the door-3 bar already stands aft of door 3).
//   door 1  [V map + tpa_IMG_0260 + reviews "two lavatories at the very front, left larger than right"]: both F lavs
//           ahead of door 1 (left bidet lav, centre lav opening into the flight-deck corridor on the left of centre),
//           centre galley behind the centre lav; aft of door 1 only closets + a small galley unit ahead of 1G, all
//           full height (omaatF_2 / tpa_IMG_0220: pale washi wall up to the bins) and washi on their suite side
//   door 2  [V map, sans_09]: galley on both sides of the cross-aisle; centre + 7K galleys and a 7A closet aft of it
//   door 3  [V map]: row 16 sits against the cross-aisle; lavs + bar are aft of it, facing forward, then row 17
//   door 4  [V map, py_37302]: centre galley ahead of door 4 behind row 27 (plain wall + two grey boxes on the PY side),
//           galley (not a closet) on the right, dark PY curtains in both aisles right behind row 27, row-30 monitors
//   door 5  [V map]: no lavs ahead of door 5; aft of it two fore-aft galleys facing a centre work aisle, a lav outboard
//           of each, light-grey rear curtains at the end of economy (y_47300)
// Depths [A]: door-2 aft monuments 0.85 / 0.70 m, door-3 monuments 1.05 m (lav class), PY bulkhead legroom 0.92 m (row 25
// hinge to the J/PY wall), 0.32 m recline room behind row 27; the door-4 forward galley keeps the rest (~0.6 m).
const MONO_LAYOUT = { d2aft: 0.85, d2side: 0.70, d3: 1.05, pyLeg: 0.92, pyRecline: 0.32 };
function monoLayoutQA(L) {
  const bar = L.mon.find((m) => m.kind === 'bar');
  if (!bar || bar.face !== 1 || bar.z1 > L.doorsZ[2][0] + 0.01) return L;
  const dz = L.doorsZ, PL = CAB.pairLen, ML = MONO_LAYOUT, mon = L.mon;
  const near = (a, b, e = 0.02) => Math.abs(a - b) < e;
  const del = (pred) => { for (let k = mon.length - 1; k >= 0; k--) if (pred(mon[k])) mon.splice(k, 1); };
  const M = (kind, x0, x1, z0, z1, extra = {}) => { const m = { kind, x0, x1, z0, z1, h: extra.h ?? 2.15, ...extra }; mon.push(m); return m; };
  const find = (kind, x0, z1) => mon.find((m) => m.kind === kind && near(m.x0, x0) && near(m.z1, z1));

  // ---- row shifts: THE Room 7-16 behind the door-2 aft galleys, 17-20 behind the door-3 monuments, PY behind the wall
  const rp = (r0) => L.roomPairs.find((p) => p.r0 === r0);
  const s2 = dz[1][1] + ML.d2aft + 0.02 - rp(7).z0;
  const s3 = dz[2][1] + ML.d3 + 0.02 - rp(17).z0;
  for (const p of L.roomPairs) { const d = p.r0 >= 17 ? s3 : p.r0 >= 7 ? s2 : 0; p.z0 += d; p.zc += d; }
  const oldZ20 = L.z20, oldZ16 = L.z16;
  L.z16 += s2; L.z20 += s3;
  const sPY = L.z20 + 0.10 + ML.pyLeg - L.pyZ[25];
  for (const r of [25, 26, 27]) L.pyZ[r] += sPY;
  for (const s of L.seats) {
    if (s.kind === 'room') { const d = s.row >= 17 ? s3 : s.row >= 7 ? s2 : 0; s.z += d; s.uz += d; }
    else if (s.kind === 'py') s.z += sPY;
    if (s.id === '1A') s.notes = s.notes.map((n) => (/lavatory/.test(n) ? 'The larger First lavatory (with bidet) is just ahead of door 1 on this side' : n));
  }
  const pz27 = L.pyZ[27], zb = L.zb;

  // ---- door 1, forward: left bidet lav (larger), flight-deck corridor, centre lav opening into it, centre + right galleys
  const d1L = find('lav', -2.70, 4.78); if (d1L) d1L.x1 = -1.10;
  del((m) => m.kind === 'closet' && near(m.x0, -1.30) && near(m.z1, 3.40));
  const ck = mon.find((m) => m.kind === 'cockpit'); if (ck) { ck.x0 = -1.08; ck.x1 = -0.44; }
  M('lav', -0.42, 0.60, 2.80, 3.45, { face: '-x' });
  M('galley', -0.42, 0.60, 3.47, 4.78, { face: 1, carts: 2, cap: 2.24 });
  M('skin', -0.43, -0.42, 3.45, 4.60, { h: 2.10, mat: 'darkWood' });                  // ebony corridor wall
  const d1G = find('galley', 0.50, 4.78); if (d1G) Object.assign(d1G, { x0: 0.62, z1: 4.60, cap: 2.24 });   // map: right unit shallower
  // ---- door 1, aft: full-height closets + a small galley unit, washi on the suite side
  del((m) => m.kind === 'lav' && near(m.z0, dz[0][1]) && near(m.z1, 7.52));
  del((m) => m.kind === 'closet' && m.low && near(m.z0, dz[0][1]));
  // w2: one continuous front wall at z 7.40 (ffF / tpa_IMG_0220 / map), curtains at both edges of each aisle opening
  M('closet', -2.70, -1.68, dz[0][1], 7.40, { face: -1, h: 2.10, back: 'F' });
  M('closet', -0.88, 0.28, dz[0][1], 7.40, { face: -1, h: 2.10, back: 'F' });
  M('galley', 0.28, 0.82, dz[0][1], 7.40, { face: -1, carts: 1, h: 2.10, back: 'F' });
  const d1R = find('closet', 1.62, 7.40); if (d1R) d1R.back = 'F';
  // w1: charcoal curtains in both F aisles at the front wall (ffF_cabin-overview-from-aisle, tpa_IMG_0220, tpg_147)
  for (const [a, b] of [[-1.68, -0.88], [0.82, 1.62]]) for (const xg of [a + 0.18, b - 0.18]) M('curtain', a, b, 7.43, 7.43, { xg, tone: 'F', h: 0 });
  // w1: door-2 forward monuments seen from rows 5-6 are cream J laminate with wall boxes (tpg_70 / _71), curtains tied
  // back at both aisle openings; the passage between the two centre galleys has a dark soffit (lalf_133)
  for (const m of mon) if (near(m.z0, 14.86) && near(m.z1, dz[1][0])) { m.back = 'J'; if (m.welcome) m.soffitTo = dz[1][1]; }
  M('curtain', -1.62, -1.10, 14.84, 14.84, { xg: -1.46, tone: 'C', h: 0 });
  M('curtain', 1.10, 1.62, 14.84, 14.84, { xg: 1.46, tone: 'C', h: 0 });

  // ---- door 2, aft: centre galley (welcome monitors on its aisle ends), 7K galley, 7A closet; cream J backs
  // w1: centre = flat ash wall with stowage flaps (lalf_133); 7K galley with ash lower doors (sp_09); the 7A closet door
  // shares its face with the door-2 jump seat (lalf_133: grey jump seat on the aft monument beside the door)
  M('galley', -0.80, 0.82, dz[1][1], dz[1][1] + ML.d2aft, { face: -1, ashWall: true, welcomeEnd: true, back: 'J' });
  M('galley', 1.80, 2.70, dz[1][1], dz[1][1] + ML.d2side, { face: -1, carts: 2, ashDoors: true, back: 'J', jumpX: 2.42 });
  M('closet', -2.70, -1.80, dz[1][1], dz[1][1] + ML.d2side, { face: -1, back: 'J', jumpX: -2.46 });
  const zJ = dz[1][1] + ML.d2side - 0.05;                   // J curtains aft of the door-2 monuments (tt cabin-1)
  M('curtain', -1.80, -0.80, zJ, zJ, { xg: -1.63, tone: 'C', h: 0 });
  M('curtain', 0.82, 1.80, zJ, zJ, { xg: 1.63, tone: 'C', h: 0 });

  // ---- door 3: lavs + bar aft of the cross-aisle, facing forward
  for (const m of mon) if ((m.kind === 'lav' || m.kind === 'bar') && near(m.z0, oldZ16 + 0.03) && near(m.z1, dz[2][0])) {
    m.z0 = dz[2][1]; m.z1 = dz[2][1] + ML.d3; m.face = -1; m.back = 'J';
    if (m.kind === 'lav') m.jumpX = Math.sign(m.x0) * 2.45;          // [A] jump seat outboard of a narrowed lav door
  }
  // ---- J/PY bulkhead follows row 20
  for (const m of mon) if (m.kind === 'partition' && near(m.z0, oldZ20 + 0.02)) { m.z0 += s3; m.z1 += s3; }

  // ---- door 4, forward: wheelchair lav (inboard edge on the aisle line), centre galley, right galley; row-30 monitors
  const d4L = mon.find((m) => m.kind === 'lav' && m.access);
  if (d4L) Object.assign(d4L, { x1: -1.62, z0: pz27 + 0.14, rowMonitor: -2.33 });
  del((m) => m.kind === 'closet' && near(m.x0, 1.62) && near(m.z1, dz[3][0]));
  M('galley', -1.05, 1.07, pz27 + ML.pyRecline, dz[3][0], { face: 1, carts: 3, back: 'PY' });
  M('galley', 1.62, 2.70, pz27 + 0.14, dz[3][0], { face: 1, carts: 2, rowMonitor: 2.2 });
  // dark slate PY curtains in both aisles right behind row 27 (py_37302), gathered against the centre galley
  const zc4 = pz27 + ML.pyRecline - 0.07;
  M('curtain', -1.62, -1.05, zc4, zc4, { xg: -1.23, tone: 'Y', h: 0 });
  M('curtain', 1.07, 1.62, zc4, zc4, { xg: 1.25, tone: 'Y', h: 0 });

  // ---- door 5: drop the outboard lavs ahead of it and the transverse aft galley; fore-aft galleys + outboard lavs
  del((m) => m.kind === 'lav' && near(m.z1, dz[4][0]) && Math.abs(m.x0 + m.x1) > 2);
  del((m) => m.kind === 'galley' && near(m.z0, dz[4][1]) && m.x1 - m.x0 > 3);
  M('galley', -1.52, -0.63, dz[4][1], CAB.zAft, { face: '+x', carts: 6 });
  M('galley', 0.60, 1.46, dz[4][1], CAB.zAft, { face: '-x', carts: 6 });
  M('lav', -2.35, -1.55, dz[4][1], dz[4][1] + 1.2, { face: -1 });
  M('lav', 1.46, 2.31, dz[4][1], dz[4][1] + 1.2, { face: -1 });
  // light-grey curtains across both aisles at the end of economy (y_47300)
  M('curtain', -1.70, -1.00, zb, zb, { xg: -1.18, tone: 'R', h: 0 });
  M('curtain', 1.00, 1.62, zb, zb, { xg: 1.18, tone: 'R', h: 0 });

  // ---- jump seats: plain lav / closet walls and the door-5 galley end panels
  L.jumps = [[-2.2, dz[0][0], 1], [2.2, dz[0][1], -1], [-2.46, dz[1][1], -1], [2.42, dz[1][1], -1], [-2.45, dz[2][1], -1], [2.45, dz[2][1], -1],
    [-1.075, dz[4][1], -1], [1.03, dz[4][1], -1]];

  // ---- zones, window classes and walkable areas re-derived with the new stations
  const Z = (type, z0, z1, extra = {}) => ({ type, z0, z1, ...extra });
  L.zones = [
    Z('mono', CAB.zFront, dz[0][0]), Z('door', dz[0][0], dz[0][1], { door: 0 }), Z('mono', dz[0][1], 7.52),
    Z('seat', 7.52, 14.86, { cls: 'F' }), Z('mono', 14.86, dz[1][0]), Z('door', dz[1][0], dz[1][1], { door: 1 }),
    Z('mono', dz[1][1], dz[1][1] + ML.d2aft), Z('seat', dz[1][1] + ML.d2aft, dz[2][0], { cls: 'J' }),
    Z('door', dz[2][0], dz[2][1], { door: 2 }), Z('mono', dz[2][1], dz[2][1] + ML.d3),
    Z('seat', dz[2][1] + ML.d3, pz27 + 0.14, { cls: 'J' }), Z('mono', pz27 + 0.14, dz[3][0]),
    Z('door', dz[3][0], dz[3][1], { door: 3 }), Z('seat', dz[3][1], zb, { cls: 'Y' }), Z('mono', zb, dz[4][0]),
    Z('door', dz[4][0], dz[4][1], { door: 4 }), Z('mono', dz[4][1], CAB.zAft),
  ];
  for (const w of L.windows) {
    w.cls = w.z < 12.0 ? 'F' : w.z < L.z20 ? 'J' : w.z < dz[3][0] ? 'PY' : 'Y';
    w.electric = w.cls === 'F' || w.cls === 'J';
  }
  const walk = [], Wk = (x0, x1, z0, z1) => walk.push([x0, x1, z0, z1]);
  for (const [a, b] of dz) Wk(-2.30, 2.30, a, b);
  Wk(-1.06, 1.58, 4.80, dz[0][0]);                                     // galley area ahead of door 1
  Wk(-1.06, -0.46, 2.90, 4.64);                                        // flight-deck corridor
  Wk(-1.60, -1.12, dz[0][1], 14.9); Wk(1.12, 1.60, dz[0][1], 14.9);   // F + forward J aisles
  for (const s of [-1, 1]) {
    const [a, b] = s < 0 ? [-1.62, -1.17] : [1.17, 1.62];
    Wk(a, b, dz[1][1], dz[2][0] + 0.1); Wk(a, b, dz[2][1], L.z20 + 0.1);
    Wk(s < 0 ? -1.52 : 1.16, s < 0 ? -1.16 : 1.52, L.z20, dz[3][0]);  // PY aisles
    Wk(s < 0 ? -1.40 : 1.00, s < 0 ? -1.00 : 1.40, 45.3, zb + 0.05);  // economy aisles
  }
  Wk(-1.40, 1.40, dz[3][1], 45.4);                                     // exit row + galley front
  Wk(-1.20, 1.20, dz[4][0] - 0.05, dz[4][1]);
  Wk(-0.58, 0.55, dz[4][1] - 0.05, CAB.zAft - 0.35);                   // aft galley work aisle
  L.walk = walk;
  return L;
}
const _buildLayoutMap = buildLayout;
buildLayout = function () { return monoLayoutQA(_buildLayoutMap()); };
