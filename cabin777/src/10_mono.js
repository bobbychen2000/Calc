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
  cockpitDoor: { c: '#3a3332', r: 0.4, l: LAYER.fWood },    // w5: striped ebony layer (was flat LAYER.wood, w5a/b)
  cockpitFrame: { c: '#c9ccd0', r: 0.35, m: 0.5, l: LAYER.brushed },
  plateWhite: { c: '#e9e9e6', r: 0.45, l: LAYER.plastic },
  jump: { c: '#5f5e5c', r: 0.6, l: LAYER.fabric },     // w9b: rendered #a4a4a6 ~ the lining; lalf_133 #6b6b6d / #575350 vs lining #e1cdb2 [V]
  harness: { c: '#5c5f66', r: 0.8 },
  jumpBase: { c: '#77736d', r: 0.5, l: LAYER.plastic }, // w9b: darker pedestal (lalf_133 #736c65) [V]
  closet: { c: '#dedcd6', r: 0.45, l: LAYER.plastic },
  ash: { c: '#cdbfa6', r: 0.5, l: LAYER.wood },
  ashDark: { c: '#8a7560', r: 0.5, l: LAYER.wood },
  darkWood: { c: '#38302e', r: 0.42, l: LAYER.fWood },     // [V] F-zone ebony, as the flight-deck corridor (tpa_IMG_0260)
  darkWoodDoor: { c: '#3f3533', r: 0.4, l: LAYER.fWood },
  // door-3 bar / door-2 welcome galley, sampled from ANA's official bar-counter render (Jul 2019 press kit) and
  // OMAAT's in-service photos: light ash doors, dark-bronze frames, black basalt counter, black upper unit
  barAsh: { c: '#b9a687', r: 0.5, l: LAYER.ashGrain },
  bronze: { c: '#6f5f50', r: 0.35, m: 0.55, l: LAYER.brushed },
  barPost: { c: '#9d8f7c', r: 0.35, m: 0.55, l: LAYER.brushed },     // [V] warm light grey-bronze posts (samchui_11 #8e7f6d)
  steelBright: { c: '#d4d6d8', r: 0.25, m: 0.9, l: LAYER.brushed },  // [V] bright counter nosing (samchui_11 #c5c0b9, lalf_134)
  // [V] door-2 aft wall (lalf_133): flat ash with aluminium-framed stowage flaps, red latches, aluminium rails; dark warm
  //     soffit with downlights over the galley passage (lalf_133 #655b54, lalf_134 #696567 at ~0.6 of white)
  soffit: { c: '#4a423d', r: 0.35, l: LAYER.wood },
  basalt: { c: '#1e1d21', r: 0.2, l: LAYER.marble },   // w11a: near-black gloss counter (lalf_134 #111119)
  black: { c: '#1b1a20', r: 0.35, l: LAYER.plastic },
  blackGloss: { c: '#0f0e13', r: 0.15 },
  blind: { c: '#3b3a3c', r: 0.85, l: LAYER.fabric, e: 0.05 },   // w7: #1d1c22 rendered a black void                // decorative blind, pulled down (render)
  washi: { c: '#f2f3f6', r: 0.8, l: LAYER.atlasGlow, e: 0.6 },       // neutral-white backlit washi band (render)
  washiGalley: { c: '#d4d3e0', r: 0.8, l: LAYER.atlasGlow, e: 0.45 }, // lavender-grey galley washi (welcome render)
  downlight: { c: '#eef4ff', r: 0.3, e: 1.6 },
  fridgeLit: { c: '#2c2f36', r: 0.08, e: 0.03 },     // [V] smoked-glass door: #3a3941 (render), #3b3834 (omaat_room_32)
  latch: { c: '#7a7d82', r: 0.35, m: 0.6 },           // [V] light-grey oval fridge latch (render)
  bottleClear: { c: '#4b5458', r: 0.04, m: 0.5 },   // w11a/b: dark see-through glass (samchui_render_11 #4b4749), white label + cap   // w10a: clear bottles lit by the shelf (were opaque grey)
  bottleBlue: { c: '#3d4f8a', r: 0.3 },              // w2: blue label on clear water bottles (the solid blue read as blobs)
  label: { c: '#f4f2ec', r: 0.6 },
  juice: { c: '#f0a526', r: 0.15 },
  tumbler: { c: '#3c4043', r: 0.04, m: 0.5 },     // w11a: dark rocks glasses (render #383539), not paper cups
  // [V] welcome galley upper unit: dark warm charcoal with visible frames, not black (omaat_room_32 #1a1911..#3a362a,
  //     kna_31_full; w5b rendered #050507)
  recessGrey: { c: '#d3d0ca', r: 0.45, l: LAYER.plastic },   // w9a: welcome recess side walls + ceiling (lalf_134, omaat_room_32) [V]
  welcomeChar: { c: '#5e5a52', r: 0.4, l: LAYER.plastic },     // w6a: #4a4740 rendered #22211d vs omaat_room_32 #565350
  navyPanel: { c: '#3a3734', r: 0.35, l: LAYER.plastic },          // [V] welcome end panel: warm charcoal (sp_09 #46433b dim; render's navy was a tint)
  // standard galley inserts (SANspotter PY snack-bar photo): aluminium ovens/trolleys, black beverage makers,
  // black work deck, red-copper turn-button latches
  // w5: inserts rendered #353535-#464646 in the set-back bank; omaat_room_32 ovens #928e79, lighter than the ash doors
  // w9 (gap analysis): the real inserts are satin anodised, light warm grey with smudges, not brushed mirrors - sansY_44 oven
  // #776a55 at 0.61 of the wall, cart 0.78; omaat_room_32 inserts the brightest part of the galley [V]; wear tile LAYER.gAlu
  alu: { c: '#bdb8ae', r: 0.55, m: 0.12, l: LAYER.gAlu },
  aluDark: { c: '#aaa69d', r: 0.55, m: 0.12, l: LAYER.gAlu },
  compartment: { c: '#b4b1a9', r: 0.5, m: 0.1, l: LAYER.gAlu },   // w9: upper stowage doors grey metal, ~0.8 of the wall (sans_38)
  insertSeam: { c: '#2c2b29', r: 0.7 },                           // w9: ~4 mm dark gap round each insert (sans_38 / sansY_44)
  ovenLabel: { c: '#c9c77e', r: 0.5, e: 0.06 },                   // w9: yellow-green meal-label window on the ovens (sansY_44 #666338 lit)
  jug: { c: '#ffffff', r: 0.12, m: 0.5 },                             // w9: polished jug, no brushed layer (rings read as stacked cups); sansY_44 jug #605a4e
  brewMetal: { c: '#8e8a82', r: 0.45, m: 0.3, l: LAYER.gAlu },    // w9: brewer stainless frame (sans_38 #59544c, ~ the jug's tone) [V]
  bevBlack: { c: '#17171a', r: 0.3 },
  copper: { c: '#b5643a', r: 0.3, m: 0.5 },   // w9: chunky copper-orange anodised turn-buttons (sansY_44 #59382d shaded, warm highlights)   // [V] small red turn-buttons (sp_09); the orange blocks dominated m01/m12
  deck: { c: '#26252a', r: 0.3, l: LAYER.plastic },
  card: { c: '#ece7c8', r: 0.7 },
  // class curtains sampled from in-service photos: F/J charcoal from both sides (omaatF_2 #5b5650/#554f4d under warm
  // light, omaat_room_36 #35343a; the f_17313 render's lavender-grey was a render tint), J/PY and PY aft-end dark slate
  // (py_37302 #424455), rear economy curtains light grey (y_47300 far end #888785..#9c9b99)
  // w1: the charcoal albedos rendered near-black (#202028 in m07); lifted to the photo samples (tpg_The-Room-small-cabin-
  // front_71 #5e5655, omaatF_2 #5b5650) [V]
  curtainF: { c: '#57504a', r: 0.95, l: LAYER.fabric },   // w3: F front read too light (0.55 of wall vs 0.36-0.39)   // + tpg_147 #4a453a at 0.34 of white, omaatF_2 #56504b
  curtainFF: { c: '#6d6b6b', r: 0.95, l: LAYER.fabric },  // w6b: F front loose drape rendered #27231f-#332d29 vs omaatF_40 #4c4644 / #423c3b in the open
  doorArc: { c: '#b53a62', r: 0.45 },   // [V] painted crimson-magenta arc + OPEN (lalf_133); MAT.handleRed read pure red
  curtainTie: { c: '#2e2b2d', r: 0.8, l: LAYER.fabric },
  curtainY: { c: '#66697c', r: 0.9, l: LAYER.fabric },   // w4: rendered #212330 vs py_37302 #545868 (b - r ~19)
  curtainRear: { c: '#a8a7a4', r: 0.9, l: LAYER.fabric },   // w5: rendered #66676a vs y_47300 #888785..#9c9b99
  curtainC: { c: '#6b635d', r: 0.95, l: LAYER.fabric },   // w2: #5a524d still rendered #2a2523 in shade (m07)  // [V] J-cabin charcoal curtains (omaat_room_36 #302f35-#3d3c42, tpg_71 #5e5655)
  rail: { c: '#dcdbd6', r: 0.4 },
  // full-height class bulkheads (QA r1): F side of F/J = pale mottled washi print (omaatF_2 samples #c0bcb1 under warm
  // light -> #c9cad2, atlas washi fibres multiplied in); J faces = warm cream laminate (omaat_room_36 #c7bda9; #ddd5c3
  // rendered #8c877c..#969288 under the bins, lifted [A] to #e6dccb); PY face of J/PY = off-white laminate (py_37303)
  bulkF: { c: '#c9cad2', r: 0.7, l: LAYER.atlasLit },
  // w1: the F walls are a soft grey-green sumi ink-cloud print on a pale ground, not paper fibres (the stretched atlas
  // washi read as marble veins): tpg_The-Suite-cabin_147 ground #c8c9c2, clouds ~#8f958a; tpg_63 #bdbca6 [V]
  inkGround: { c: '#dddbd0', r: 0.75, l: LAYER.plastic },   // w2: warmer ground, ~18 % cloud contrast (was ~5 %)
  inkCloud: '#6a665f',   // w11a/b: warm-neutral cloud core (omaatF_2 p10 #a8a399 under warm light), R >= G >= B
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
  cardGreen: { c: '#2f6f55', r: 0.6 },   // w3: the bright band read as an emissive block (d4L)
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
  B.add(gCyl(r * 0.4, r, h * 0.12, 10), M4.mul(xf, M4.trs(0, h * 0.72, 0)), mat);          // w10a: shoulder + slim neck + cap
  B.add(gCyl(r * 0.3, r * 0.3, h * 0.16, 8), M4.mul(xf, M4.trs(0, h * 0.86, 0)), mat);
  B.add(gCyl(r * 0.34, r * 0.34, h * 0.05, 8), M4.mul(xf, M4.trs(0, h * 0.965, 0)), MONMAT.label);
  if (lbl) B.add(gCyl(r * 1.04, r * 1.04, h * 0.2, 10, false), M4.mul(xf, M4.trs(0, h * 0.22, 0)), lblMat);
}
// round flush stainless pull (bar render), on a face
function ringPull(B, xf) {
  B.add(gCyl(0.028, 0.028, 0.008, 16), M4.mul(xf, M4.trs(0, 0, 0.004, 0, Math.PI / 2)), MONMAT.steel);
  B.add(gCyl(0.019, 0.019, 0.008, 12), M4.mul(xf, M4.trs(0, 0, 0.006, 0, Math.PI / 2)), MONMAT.bronze);
  B.add(gBox(0.024, 0.006, 0.008), M4.mul(xf, M4.trs(0, 0, 0.011)), MONMAT.steel);
}

// w9: chunky copper-orange turn-button latch (sans_38 / sansY_44: ~35 x 50 mm block with a round barrel face) on a face xf
function turnLatch(B, xf) {
  B.add(gRBox(0.03, 0.05, 0.022, 0.008, 1), M4.mul(xf, M4.trs(0, 0, 0.011)), MONMAT.copper);
  B.add(gCyl(0.012, 0.012, 0.022, 10), M4.mul(xf, M4.trs(0, -0.008, 0.026, 0, Math.PI / 2)), MONMAT.copper);
}
// w9: dark ~4 mm gap behind an insert face (w x h, centred at xf), drawn as a slightly larger dark backing plate
function insertGap(B, xf, w, h) { B.add(gBox(w + 0.008, h + 0.008, 0.004), xf, MONMAT.insertSeam); }
// w9: galley beverage maker (sans_38 / sansY_44, real ANA 777-300ER): satin-metal brew head with a black control strip
// (green-lit key) and a dark window, metal cheeks round an open bay with a black back, a fold-out brew handle and a
// bulbous polished jug with a black handle and lid standing on the drip tray. uW wide; P(dx, y, o) places on the face.
function brewer(B, P, uW, y0) {
  // w10 (A/B): shallow (0.05 m) so it sits nearly flush with the ovens, polished jug with a baked highlight and reflection
  B.add(gRBox(uW, 0.13, 0.05, 0.01, 1), P(0, y0 + 0.165, 0.025), MONMAT.brewMetal);                     // head
  B.add(gBox(uW - 0.02, 0.025, 0.004), P(0, y0 + 0.215, 0.051), MONMAT.bevBlack);                     // control strip
  B.add(gBox(0.014, 0.01, 0.004), P(-uW * 0.3, y0 + 0.215, 0.054), MONMAT.green);
  B.add(gQuad(uW * 0.5, 0.012), P(0, y0 + 0.17, 0.0505), MONMAT.label);                              // w11a: caution label (the window read as a microwave)
  B.add(gBox(uW * 0.7, 0.05, 0.05), P(0, y0 + 0.075, 0.03), MONMAT.aluDark);                          // w11a: brew-basket drawer + side arm (sansY_44)
  B.add(gBox(0.012, 0.012, 0.06), P(uW * 0.3, y0 + 0.08, 0.06), MONMAT.bevBlack);
  B.add(gBox(uW, 0.2, 0.006), P(0, y0, 0.003), MONMAT.bevBlack);                                       // bay back
  for (const s of [-1, 1]) B.add(gBox(0.01, 0.21, 0.05), P(s * (uW / 2 - 0.005), y0, 0.025), MONMAT.brewMetal);
  B.add(gBox(uW - 0.02, 0.01, 0.06), P(0, y0 - 0.105, 0.035), MONMAT.steelDark);                      // drip tray
  // w11a/b: squat polished vacuum pot filling the bay, wide black lid; the polish is baked into the vertex colours as soft
  // azimuthal bands (the flat highlight quads read as stickers)
  const r = uW / 2 - 0.014, prof = [[0.001, 0], [r * 0.96, 0.004], [r, 0.03], [r * 0.97, 0.07], [r * 0.82, 0.095], [r * 0.66, 0.105], [0.001, 0.106]];
  for (let i = 0; i < 12; i++) {   // one wedge per segment, shaded by azimuth (also works through the x-facing proxy builder)
    const ph = (i + 0.5) * Math.PI / 6, t = 0.25 + 0.75 * (0.5 + 0.5 * Math.cos(ph - 0.5)) ** 2.5;   // one broad soft highlight (zebra bands read striped)
    B.add(gLathe(prof, 1, i * Math.PI / 6, Math.PI / 6), P(0, y0 - 0.1, 0.03), { ...MONMAT.jug, c: '#' + hexRGB('#4a4843').map((v, c) => Math.round(lerp(v, hexRGB('#d6d4ce')[c], t)).toString(16).padStart(2, '0')).join('') });
  }
  B.add(gCyl(r * 0.68, r * 0.66, 0.02, 12), P(0, y0 + 0.015, 0.03), MONMAT.bevBlack);                   // lid
  B.add(gTube([[r * 0.7, 0.1, 0], [r + 0.02, 0.095, 0], [r + 0.02, 0.035, 0], [r - 0.004, 0.02, 0]], 0.007, 4), P(0, y0 - 0.1, 0.03), MONMAT.bevBlack);   // handle
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
  for (let k = 1; k < 9; k++) B.add(gBox(up(850) - up(490) - 0.01, 0.003, 0.004), V((up(490) + up(850)) / 2, uy(700) + (k * (uy(210) - uy(700))) / 9, oU + 0.073), { c: '#4a4846', r: 0.5 });   // w10a: blind slat lines visible
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
  for (let k = 0; k < 7; k++) bottle(B, V(sx0 + 0.035 + (k * (sx1 - sx0 - 0.07)) / 6, uy(690) + 0.005, oU + 0.07), k ? 0.30 : 0.2, k ? 0.028 : 0.032, k ? MONMAT.bottleClear : MONMAT.juice);   // w10b: slimmer, spaced
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
  // low steel guard rail along the back of the counter and its ends, in front of the upper unit (samchui_11)
  B.add(gBox(uw, 0.012, 0.012), V(0, BAR.deck + 0.1, oU + 0.12), MONMAT.steelBright);
  for (const sx of [-1, 1]) {
    B.add(gBox(0.012, 0.012, 0.3), V(sx * uw / 2, BAR.deck + 0.1, oU + 0.27), MONMAT.steelBright);
    for (const dzz of [0.12, 0.42]) B.add(gBox(0.012, 0.065, 0.012), V(sx * uw / 2, BAR.deck + 0.067, oU + dzz), MONMAT.steelBright);
  }
  // tumblers on the counter (render: four at the left)
  for (const p of [490, 535, 578, 655]) B.add(gCyl(0.035, 0.03, 0.06, 12), V(up(p), BAR.deck + 0.065, p === 655 ? -0.16 : -0.26), MONMAT.tumbler);
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
  monoStepBody(B, m, dk, set, MONMAT.barAsh, MONMAT.welcomeChar);
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
    // w9a: the recess is lined in light grey laminate (lalf_134, omaat_room_32: pale side wall + lit ceiling); ash only
    // as a thin skin on the outer face
    B.add(gBox(0.03, 2.0 - dk, set), V(sx * (w / 2 - 0.02), (dk + 2.0) / 2, -set / 2), MONMAT.recessGrey);
  }
  B.add(gRBox(w, 0.05, 0.05, 0.02, 1), V(0, 2.02, 0.0), MONMAT.alu);
  B.add(gBox(w, m.h - 1.995, set), V(0, (1.995 + m.h) / 2, -set / 2), MONMAT.recessGrey);
  B.add(gBox(w, m.h - 2.045, 0.012), V(0, (2.045 + m.h) / 2, 0.006), MONMAT.barAsh);                                // ash head skin
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
  B.add(gRBox(0.90, 0.54, 0.012, 0.01, 1), V(mc, 1.68, o - 0.002), SEATMAT.bezel);                  // w11: flush in the tower (omaat_room_32)
  B.add(gQuad(0.86, 0.49), V(mc, 1.68, o + 0.0045), SEATMAT.screen, atlasUV('screen'));
  B.add(gRBox(0.92, 0.02, 0.07, 0.006, 1), V(mc, 1.39, o + 0.04), MONMAT.blackGloss);
  // two open bays under the monitor (omaat 32): the brewer stands inside the left one, the right one is empty
  for (const u of [-0.225, 0.225]) {
    B.add(gBox(0.43, 0.34, 0.004), V(mc + u, 1.2, o + 0.002), { c: '#1d1c19', r: 0.5 });
    for (const sx of [-1, 1]) B.add(gBox(0.014, 0.36, 0.1), V(mc + u + sx * 0.222, 1.2, o + 0.05), MONMAT.welcomeChar);
  }
  B.add(gBox(0.9, 0.014, 0.1), V(mc, 1.375, o + 0.05), MONMAT.welcomeChar);
  brewer(B, (dx, y, oo) => V(mc - 0.28 + dx, y, o + oo), 0.18, 1.13);   // w9: satin brewer + polished jug (omaat_room_32)
  // right: tall glass-door cabinet with round latch and a placard above
  const gc = w / 2 - 0.3;
  // w5 (omaat_room_32, kna_31_full): smoked glass with the shelves and boxes visible behind it, charcoal stiles, a round
  // latch boss on an oval plate at the fwd stile, white caution text block at the top
  // w9 (A/B w8-w9: the opaque pane + drawn shelf lines read as a panelled door): no pane quad; the lit interior, shelves
  // and contents are drawn darkened ~0.55x as seen through the smoked glass (omaat_room_32 pane p10/50/90 28/60/82, papers
  // and boxes visible), with two narrow upright sheen strips on the glass plane and the black caution plate on the top rail
  // w10a: no pane quad (any opaque pane reads as a panelled door) - the lit interior at the photos' tone instead
  // (omaat_room_32 #4e4c4b, lalf_134 #605154), a white tray (lalf_134), one faint reflection line by the hinge stile
  // w11a/b: interior back to ~0.75x with the photos' mauve tint (lalf_134 #514345, omaat_room_32 #3c3935), no glow; the
  // glass reads from a bright bead round the pane opening and a deep top rail carrying the caution plate (omaat_room_32)
  B.add(gBox(0.40, 0.76, 0.004), V(gc + 0.02, 1.44, o + 0.003), { c: '#463c3e', r: 0.6, e: 0.02 });
  for (const y of [1.2, 1.45, 1.7]) B.add(gBox(0.38, 0.012, 0.07), V(gc + 0.02, y, o + 0.04), { c: '#6a6062', r: 0.5 });
  for (const [u, y, bw, bh, cc] of [[-0.08, 1.27, 0.12, 0.13, '#5a5452'], [0.07, 1.25, 0.14, 0.09, '#6e6866'], [0.0, 1.53, 0.2, 0.15, '#4c4746'],
    [-0.1, 1.64, 0.1, 0.1, '#45403f'], [0.09, 1.52, 0.03, 0.12, '#7e7876'], [0.08, 1.64, 0.13, 0.025, '#7a7472']])
    B.add(gBox(bw, bh, 0.05), V(gc + 0.02 + u, y, o + 0.035), { c: cc, r: 0.6 });
  B.add(gBox(0.3, 0.012, 0.06), V(gc + 0.02, 1.215, o + 0.04), { c: '#a8a2a0', r: 0.4 });                  // white tray
  for (const sx of [-1, 1]) B.add(gBox(0.05, 0.8, 0.03), V(gc + 0.02 + sx * 0.195, 1.44, o + 0.085), MONMAT.welcomeChar);
  B.add(gBox(0.44, 0.05, 0.03), V(gc + 0.02, 1.065, o + 0.085), MONMAT.welcomeChar);
  B.add(gBox(0.44, 0.13, 0.03), V(gc + 0.02, 1.775, o + 0.085), MONMAT.welcomeChar);                       // deep top rail
  const bead = { c: '#8a8380', r: 0.12, m: 0.4 };                                                            // pane bead
  for (const sx of [-1, 1]) B.add(gBox(0.008, 0.62, 0.006), V(gc + 0.02 + sx * 0.166, 1.40, o + 0.087), bead);
  for (const y of [1.094, 1.706]) B.add(gBox(0.34, 0.008, 0.006), V(gc + 0.02, y, o + 0.087), bead);
  B.add(gQuad(0.2, 0.05), V(gc + 0.06, 1.79, o + 0.1005), MONMAT.bevBlack);                                // caution plate on the top rail
  for (let i = 0; i < 3; i++) B.add(gQuad(0.15 - i * 0.03, 0.005), V(gc + 0.06 - i * 0.015, 1.805 - i * 0.013, o + 0.101), MONMAT.label);
  B.add(gCyl(0.05, 0.05, 0.016, 20), M4.mul(V(gc - 0.17, 1.44, o + 0.104), M4.trs(0, 0, 0, 0, Math.PI / 2)), MONMAT.welcomeChar);   // round boss
  B.add(gCyl(0.028, 0.028, 0.016, 16), M4.mul(V(gc - 0.17, 1.44, o + 0.118), M4.trs(0, 0, 0, 0, Math.PI / 2)), MONMAT.latch);
  B.add(gRBox(0.26, 0.07, 0.012, 0.035, 2), V(gc, 1.92, o + 0.02), { c: '#e9e2cf', r: 0.5 });          // w7: single cream oval tag
  B.add(gQuad(0.03, 0.03), V(gc - 0.07, 1.92, o + 0.0265), { c: '#5a5650', r: 0.6 });                      // w10a: pictogram + 2 text lines (omaat_room_32)
  for (const y of [1.93, 1.91]) B.add(gQuad(0.09, 0.005), V(gc + 0.03, y, o + 0.0265), { c: '#8d887e', r: 0.6 });
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
      B.add(gBox(bw, bh, 0.016), F(x + bx, 1.28 + by, 0.008), MONMAT.steel);   // w11a: brushed silver frames (lalf_133)
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
    if (Math.abs(x) > wallAt(0.5)[0] - 0.2 || (m.jumpX !== undefined && Math.abs(x - m.jumpX) < 0.3)) continue;
    const G = (dx, y, o) => F(x + dx, y, o);
    insertGap(B, G(0, 0.5, 0.003), cw, 0.98);
    B.add(gRBox(cw, 0.98, 0.05, 0.012, 1), G(0, 0.5, 0.02), MONMAT.alu);
    B.add(gRBox(cw - 0.03, 0.03, 0.02, 0.008, 1), G(0, 0.94, 0.05), MONMAT.aluDark);            // push handle
    B.add(gQuad(0.12, 0.08), G(0, 0.8, 0.046), MONMAT.card);
    if (k % 2 === 0) B.add(gQuad(cw * 0.55, 0.16), G(0, 0.26, 0.046), MAT.grille);             // air-chilled vent
    for (const s of [-1, 1]) {
      turnLatch(B, G(s * (cw / 2 + 0.005), dk - 0.04, 0.045));
      B.add(gRBox(0.04, 0.016, 0.018, 0.006, 1), G(s * (cw / 2 - 0.02), 0.04, 0.06), MONMAT.copper);
    }
  }
  // w6b: a jump seat on the galley face (jumpX) gets a flush full-height white panel; the deck, nosing, work light and
  // upper inserts stop either side of it instead of running behind the seat (m13, lalf_133: seat on a plain panel)
  const jx = m.jumpX, segs = jx === undefined ? [[m.x0, m.x1]] : [[m.x0, jx - 0.27], [jx + 0.27, m.x1]].filter(([a, b]) => b - a > 0.35);   // w10a: no stub deck beside the 2R seat
  for (const [a, b] of segs) {
    const sw = b - a, sc = (a + b) / 2;
    B.add(gRBox(sw - 0.04, 0.035, set + 0.03, 0.008, 1), F(sc, dk + 0.0175, (0.03 - set) / 2), MONMAT.deck);
    B.add(gRBox(sw - 0.06, 0.03, 0.025, 0.01, 1), F(sc, dk + 0.005, 0.03), MONMAT.alu);
    B.add(gBox(Math.max(0.02, sw - 0.12), 0.012, 0.03), F(sc, 1.285, 0.03 - set), MONMAT.workLight);
  }
  if (jx !== undefined) B.add(gBox(0.52, m.h - dk, set), F(jx, (dk + m.h) / 2, -set / 2), body);
  const o = 0.01 - set;
  const nU = Math.max(2, Math.round(w / 0.38));
  for (let k = 0; k < nU; k++) {
    const x = m.x0 + 0.05 + ((w - 0.1) / nU) * (k + 0.5);
    if (Math.abs(x) > wallAt(1.5)[0] - 0.25 || (jx !== undefined && Math.abs(x - jx) < 0.3)) continue;
    const uW = (w - 0.1) / nU - 0.03, t = k % 3, G = (dx, y, oo) => F(x + dx * m.face, y, oo);
    // w9 (gap analysis, sans_38 / sansY_44): satin inserts in dark 4 mm gaps, chunky copper turn-buttons
    insertGap(B, F(x, 1.47, o + 0.002), uW, 0.32);
    if (t === 0) {        // oven: satin door, yellow-green meal-label window top-left, riveted lever latch, display top-right
      B.add(gRBox(uW, 0.32, 0.04, 0.01, 1), F(x, 1.47, o + 0.02), MONMAT.alu);
      B.add(gRBox(uW * 0.48, 0.095, 0.006, 0.004, 1), G(-uW * 0.2, 1.57, o + 0.042), MONMAT.aluDark);
      B.add(gQuad(uW * 0.44, 0.08), G(-uW * 0.2, 1.57, o + 0.0455), MONMAT.ovenLabel);
      B.add(gRBox(uW * 0.2, 0.11, 0.006, 0.006, 1), G(uW * 0.3, 1.55, o + 0.042), MONMAT.insertSeam);   // display / timer window
      B.add(gBox(0.03, 0.008, 0.004), G(uW * 0.3, 1.58, o + 0.046), MONMAT.blueLed);
      B.add(gBox(uW * 0.5, 0.06, 0.004), G(-uW * 0.08, 1.43, o + 0.041), MONMAT.insertSeam);             // latch recess
      B.add(gRBox(uW * 0.46, 0.035, 0.025, 0.01, 1), G(-uW * 0.08, 1.43, o + 0.05), MONMAT.aluDark);     // lever
      for (const s of [-1, 1]) turnLatch(B, F(x + s * uW * 0.3, 1.3, o + 0.04));
    } else if (t === 1) { // beverage maker: satin head + black strip, polished jug in the bay (sans_38 / sansY_44)
      for (const sx of [-1, 1]) brewer(B, (dx, y, oo) => G(sx * uW / 4 + dx, y, o + oo), uW / 2 - 0.006, 1.41);   // w10: two narrow makers per slot (sans_38)
      B.add(gBox(uW * 0.4, 0.016, 0.003), G(-uW * 0.1, 1.29, o + 0.007), MONMAT.card);                  // 'Water Filter Inside' tag
    } else {              // standard unit with recessed pull
      B.add(gRBox(uW, 0.32, 0.03, 0.01, 1), F(x, 1.47, o + 0.015), MONMAT.aluDark);
      B.add(gRBox(0.08, 0.025, 0.02, 0.006, 1), F(x, 1.59, o + 0.035), MONMAT.bevBlack);
      B.add(gQuad(0.05, 0.022), G(uW * 0.3, 1.36, o + 0.0305), MONMAT.card);
    }
    insertGap(B, F(x, 1.86, o + 0.002), uW, 0.36);
    B.add(gRBox(uW, 0.36, 0.03, 0.01, 1), F(x, 1.86, o + 0.015), MONMAT.compartment);
    if (k % 3 !== 2) B.add(gQuad(k % 2 ? 0.1 : 0.06, 0.03), F(x + (k % 2 ? 0.04 : -0.03), k % 4 === 1 ? 1.74 : 1.99, o + 0.0305), MONMAT.card);   // w5: varied labels
    B.add(gRBox(0.06, 0.018, 0.012, 0.006, 1), F(x, 1.72, o + 0.036), MONMAT.aluDark);                          // paddle
    for (const s of [-1, 1]) turnLatch(B, F(x + s * uW * 0.3, 1.70, o + 0.03));
  }
  B.add(gQuad(0.2, 0.04), F(cx, 1.655, o + 0.032), MAT.decal, atlasUV('galleyLbl'));
}

// ---- Class curtains: ceiling track across the aisle opening, curtain gathered open as a pleated bundle at xg, tied back
// at ~1.15 m and flaring to ~0.3 m at the hem (tpg_The-Room-small-cabin-front_71, tpg_The-Suite-cabin_147) [V shape, A sizes]
const CURTAIN_H = 2.18;
let _curtainGeo = null, _curtainTie = null;
// w3: deep folds (amp 0.3-0.35, 7-9 lobes) with baked crease shading (see addCurtain) so bundles stop reading as posts
function curtainLoft(levels, { n = 36, hx = 0.085, hz = 0.06, amp = 0.3, lobes = 7 } = {}) {
  const g = raw();
  for (const [y, s, d = s] of levels) for (let k = 0; k <= n; k++) {
    const a = (k / n) * Math.PI * 2, r = 1 + amp * Math.sin(a * lobes);
    g.p.push(Math.cos(a) * hx * r * s, y, Math.sin(a) * hz * r * d); g.n.push(Math.cos(a) * 0.6, 0, Math.sin(a)); g.u.push(k / n, y);
  }
  for (let j = 0; j + 1 < levels.length; j++) for (let k = 0; k < n; k++) {
    const q = j * (n + 1) + k; g.i.push(q, q + n + 1, q + 1, q + 1, q + n + 1, q + n + 2);
  }
  return fixWinding(g);
}
// Two forms (w2, tpg_70/_71/_147, alv_IMG_7182/7207/7209): 'tied' (F/J + J lines) pressed against the panel edge, tied
// at ~1.5 m, ~0.2 m wide at the hem and fanning to ~0.3 m under the track; 'panel' (F front, J/PY, PY aft, rear) a wide
// untied pleated panel ~0.3 m across, gathered against the panel edge. xg = bundle centre, ~0.16 m off that edge.
// w3 sizes: tied ~0.22 m at the hem, ~0.11 m at the tie, ~0.31 m under the track; panel ~0.24 m across, ~0.09 m deep,
// top tucked under a 0.05 m rail (both raters: the r2 panels blocked the aisles)
// w5: 'wide' loose drape (F front, rear economy): ~0.45 m across, 13 folds, irregular hem (omaatF_40: ~0.45 m drape at
// the F front; y_47300 rear) - its crease shading also varies with height so the folds do not read as uniform flutes
let _curtainPanel = null, _curtainWide = null;
function addCurtain(B, xa, xb, z, xg, mat, tied = false, wide = false) {
  if (!_curtainGeo) {
    _curtainGeo = curtainLoft([[0.02, 1.0, 0.9], [0.8, 0.9, 0.8], [1.42, 0.5], [1.55, 0.5], [1.8, 1.05, 0.9], [CURTAIN_H - 0.03, 1.4, 0.8]]);
    _curtainTie = curtainLoft([[1.44, 0.56], [1.53, 0.56]], { amp: 0.1 });
    // w4: wider gathered drape (~0.4 m at the hem, ~0.3 m under the track; py_37302 / y_47300), fuller at the hem
    _curtainPanel = curtainLoft([[0.02, 1.0, 1.1], [0.7, 0.9], [1.4, 0.82], [CURTAIN_H - 0.03, 0.72, 0.7]], { hx: 0.16, hz: 0.035, amp: 0.3, lobes: 11 });
    _curtainWide = curtainLoft([[0.0, 1.0, 1.2], [0.06, 1.02, 1.15], [0.5, 0.94, 1.0], [1.1, 0.86, 0.9], [1.7, 0.8, 0.8], [CURTAIN_H - 0.03, 0.74, 0.7]], { n: 52, hx: 0.21, hz: 0.04, amp: 0.32, lobes: 13 });
    for (let k = 0; k <= 52; k++) _curtainWide.p[k * 3 + 1] = 0.01 + 0.035 * Math.abs(Math.sin(k * 1.7));   // uneven hem
  }
  B.add(gBox(Math.abs(xb - xa), 0.02, 0.05), M4.trs((xa + xb) / 2, CURTAIN_H + 0.01, z), MONMAT.rail);
  const base = B.p.length / 3;
  B.add(tied ? _curtainGeo : wide ? _curtainWide : _curtainPanel, M4.trs(xg, 0, z), mat);
  const lobes = tied ? 7 : wide ? 13 : 11;
  for (let k = base; k < B.p.length / 3; k++) {          // darker creases between the folds
    const v = B.u[k * 2 + 1], ph = wide ? 0.6 * Math.sin(v * 2.3 + 1.1) : 0;
    const f = 0.62 + 0.38 * Math.max(0, Math.sin(B.u[k * 2] * Math.PI * 2 * lobes + ph));
    for (let c = 0; c < 3; c++) B.c[k * 4 + c] = Math.round(B.c[k * 4 + c] * f);
  }
  if (tied) B.add(_curtainTie, M4.trs(xg, 0, z), MONMAT.curtainTie);
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
    // w11a/b (tpa_Image-2-3): brushed-aluminium bolt frames ~0.62 of the leaf width (upper taller), aluminium hinge jamb
    for (const [y, fh] of [[1.55, 0.42], [0.55, 0.36]]) {
      const pw = Math.min(dw * 0.62, dw - 0.12), h2 = fh / 2 - 0.0175;
      for (const [bw, bh, bx, by] of [[pw, 0.035, 0, h2], [pw, 0.035, 0, -h2], [0.035, fh, pw / 2 - 0.0175, 0], [0.035, fh, 0.0175 - pw / 2, 0]])
        B.add(gBox(bw, bh, 0.012), P(bx, y + by, 0.03), MONMAT.cockpitFrame);
      B.add(gBox(0.08, 0.06, 0.014), P(0, y - fh / 2 - 0.01, 0.03), MONMAT.cockpitFrame);         // bolt tab
    }
    B.add(gBox(0.06, 1.98, 0.012), P(-dw / 2 + 0.03, 0.99, 0.03), MONMAT.cockpitFrame);
    B.add(gBox(dw, 0.14, 0.012), P(0, 0.13, 0.03), MONMAT.cockpitFrame);                            // kick panel
    B.add(gQuad(0.08, 0.035), P(0, 1.64, 0.026), MONMAT.label);                                   // CREW ONLY placard
    B.add(gQuad(0.03, 0.03), P(0, 1.60, 0.0262), MONMAT.red);
    B.add(gCyl(0.012, 0.012, 0.01, 10), M4.mul(P(0, 1.52, 0.03), M4.trs(0, 0, 0, 0, Math.PI / 2)), MONMAT.steel);
    B.add(gRBox(0.08, 0.14, 0.03, 0.02, 1), P(dw / 2 - 0.08, 1.02, 0.035), MONMAT.plateWhite);   // lever housing
    B.add(gRBox(0.03, 0.12, 0.03, 0.01, 1), P(dw / 2 - 0.08, 0.98, 0.055), MONMAT.steel);
    // w10a (tpa_Image-2-3): yellow / black chevron kick strip, round lock boss on a satin plate on the latch side
    for (let i = 0; i < 10; i++) B.add(gBox(dw / 10, 0.05, 0.012), P(-dw / 2 + dw / 20 + (i * dw) / 10, 0.035, 0.03), i % 2 ? { c: '#151515', r: 0.5 } : { c: '#d8b52a', r: 0.5 });
    B.add(gRBox(0.06, 0.16, 0.012, 0.01, 1), P(dw / 2 - 0.08, 1.30, 0.032), MONMAT.cockpitFrame);
    B.add(gCyl(0.025, 0.025, 0.02, 14), M4.mul(P(dw / 2 - 0.08, 1.30, 0.045), M4.trs(0, 0, 0, 0, Math.PI / 2)), MONMAT.steel);
    // access keypad on the corridor's right-hand wall, just aft of the door
    B.add(gQuad(0.08, 0.1), M4.trs(m.x1 + 0.012, 1.25, m.z1 + 0.25, -Math.PI / 2), MAT.decal, atlasUV('keypad'));
  } else if (m.kind === 'partition') {
    buildBulkhead(B, m, layout);
  } else if (m.kind === 'skin') {
    // thin wall lining, e.g. the ebony flight-deck corridor side of the forward centre galley (tpa_IMG_0260)
    B.add(gBox(w, m.h, m.z1 - m.z0), M4.trs(cx, m.h / 2, (m.z0 + m.z1) / 2), MONMAT[m.mat] || MONMAT.laminate);
  } else if (m.kind === 'curtain') {
    // explicit curtain: M('curtain', xa, xb, z, z, { xg, tone: 'F' | 'Y' | 'C' }) - track xa..xb, gathered at xg
    addCurtain(B, m.x0, m.x1, m.z0, m.xg ?? m.x0 + 0.13, { F: MONMAT.curtainFF, C: MONMAT.curtainC, R: MONMAT.curtainRear }[m.tone] || MONMAT.curtainY, m.tone === 'C', m.tone !== 'C');   // w6a: PY aft drapes wide too (py_37302 ~0.4-0.6 m)
  }
  if (m.back && !m.xFacing) monoBack(B, m);
  // w9 (gap analysis, tpa_Image-2-3): satin aluminium edge guard on the aisle-side front corner of lavs and closets
  if ((m.kind === 'lav' || m.kind === 'closet') && !m.xFacing && Math.abs(inner) < 1.7 && Math.abs(inner) > 0.05)
    B.add(gBox(0.02, Math.min(1.9, m.h - 0.05), 0.02), M4.trs(inner, Math.min(1.9, m.h - 0.05) / 2 + 0.02, m.face > 0 ? m.z1 : m.z0), MONMAT.alu);
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
    const n = fbm(x / 0.9 + 40, y / 0.25 + 3, 256, 4, 23), lowY = clamp(1.25 - 0.4 * y / H, 0.65, 1);   // w10a: horizontal strata (omaatF_2)
    const t = clamp((n - 0.36) / 0.22, 0, 1) ** 1.1 * lowY;   // w11b: wider, deeper clouds (omaatF_2 spread ~69 levels)
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
  // w9 (gap analysis, omaat_room_36): panel band just above the seat shells - seams at 1.06 / 1.22 m with vertical joints
  // ~0.9 m apart, a satin bead on its top edge [V layout, A heights]
  if (m.back !== 'F') {
    const xw = wallAt(1.2)[0] - 0.03, a = Math.max(m.x0, -xw), b = Math.min(m.x1, xw), bw = b - a;
    if (bw > 0.3) {
      for (const y of [1.06, 1.22]) B.add(gBox(bw, 0.004, 0.003), M4.trs((a + b) / 2, y, zf + f * 0.0045), MONMAT.seamJ);
      B.add(gBox(bw, 0.008, 0.006), M4.trs((a + b) / 2, 1.226, zf + f * 0.006), MONMAT.alu);
      const nj = Math.max(1, Math.round(bw / 0.9));
      for (let k = 1; k < nj; k++) B.add(gBox(0.004, 0.16, 0.003), M4.trs(a + (bw * k) / nj, 1.14, zf + f * 0.0045), MONMAT.seamJ);
    }
  }
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
      for (const u of [-0.62, 0.62]) B.add(gQuad(0.08, 0.04), M4.mul(X(cx + u, 1.71), M4.trs(0, 0, 0.001)), MONMAT.placardBlue);   // w6: label just above each box
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
      insertGap(B, Wf(x, y, 0.002), cw - 0.02, 0.38);
      B.add(gRBox(cw - 0.02, 0.38, 0.02, 0.008, 1), Wf(x, y, 0.01), MONMAT.compartment);
      turnLatch(B, Wf(x, y + 0.15, 0.02));
      if ((i + (y > 1.5 ? 1 : 0)) % 3 !== 1) B.add(gQuad(i % 2 ? 0.07 : 0.11, 0.045), Wf(x + (i - 1) * 0.03, y - 0.1, 0.021), MONMAT.card);   // w6a: varied labels
    }
    B.add(gBox(xb - xa - 0.04, 0.035, 0.3), M4.trs((xa + xb) / 2, 1.03, zw - 0.15), MONMAT.deck);
    B.add(gRBox(0.36, 0.5, 0.02, 0.01, 1), Wf((xa + xb) / 2, 0.45, 0.01), MONMAT.alu);                    // waste flap
    B.add(gRBox(0.2, 0.03, 0.03, 0.01, 1), Wf((xa + xb) / 2, 0.66, 0.025), MONMAT.aluDark);
    // w5b: no open box under the counter: a stack of three drawers either side of the waste flap [A]
    for (const s of [-1, 1]) for (let r = 0; r < 3; r++) {
      const x = (xa + xb) / 2 + s * ((xb - xa) / 2 - 0.02 - cw / 2 + 0.05), y = 0.17 + r * 0.29;
      insertGap(B, Wf(x, y, 0.002), cw - 0.12, 0.27);
      B.add(gRBox(cw - 0.12, 0.27, 0.02, 0.008, 1), Wf(x, y, 0.01), MONMAT.aluDark);
      B.add(gRBox(0.12, 0.02, 0.02, 0.006, 1), Wf(x, y + 0.09, 0.025), MONMAT.bevBlack);
      turnLatch(B, Wf(x, y + 0.11, 0.02));
    }
  }
  // ---- class curtains, drawn open: in each aisle gap of the F/J and J/PY bulkheads (f_17313, py_37301/37302),
  //      gathered at the centre side. The PY aft-end and rear-economy curtains are explicit 'curtain' monuments.
  const parts = layout.mon.filter((m) => m.kind === 'partition').sort((a, b) => a.z0 - b.z0 || a.x0 - b.x0);
  for (let k = 0; k + 1 < parts.length; k++) {
    const a = parts[k], b = parts[k + 1];
    if (Math.abs(a.z0 - b.z0) > 0.01 || b.x0 - a.x1 < 0.2) continue;
    const zc = (a.z0 + a.z1) / 2, right = a.x1 > 0, F = clsAt(layout, a.z0 - 0.5) === 'F';
    // gathered against the outboard panel and tied: F/J (tpg_71, tt cabin-1) and J/PY in the J charcoal (alv_IMG_7209 #38312b)
    addCurtain(B, a.x1, b.x0, zc, right ? b.x0 - 0.13 : a.x1 + 0.13, F ? MONMAT.curtainF : MONMAT.curtainC, true);
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
      // w7: mirrored fore-aft (H = -1): lalf_133 / lalf_134 look at L2 (welcome galley forward of the passage, beside the
      // door-2 lavs in omaat_room_32; 2L jump seat on the aft closet) and show the viewing window FORWARD of the handle
      // housing, the arming window upper AFT and the arrowhead on the forward side. Offsets below are written in the
      // original spec frame and multiplied by H. The shell's window (07_shell wz) must sit at c - 0.28 (from_monuments).
      const H = -1;
      // w5: lining furniture rebuilt from the corrected from_shell spec (ANA 777 door-lining photos yt_vEERVra5lKs /
      // yt_R7MKjYHQ1Uk, tpg door 2L, a 777 door trainer) [V layout, A sizes +-3 cm]. Hinge forward on both sides, so
      // "fwd" = c - dz. LF places a part on the lining: local x = out of the wall (times -side), y = up, z = aft.
      const LF = (v, inset, dz, extra) => {
        const [x, y] = at(v, inset), [, , nx, ny] = wallAt(v);
        const m = M4.trs(x, y, c + H * dz, 0, 0, side > 0 ? -Math.atan2(ny, -nx) : Math.atan2(ny, -nx));
        return extra ? M4.mul(m, extra) : m;
      };
      const Qf = M4.trs(0, 0, 0, side > 0 ? -Math.PI / 2 : Math.PI / 2), hd = 0.12, hf = hd + 0.003;
      // handle housing: cream box across the upper middle (y 0.85-1.28, fwd end c-0.48; aft end stops at c+0.20 so the
      // viewing-window glass at c+0.21..0.35 stays clear), oval recess at its fwd upper corner
      B.add(gRBox(hd, 0.43, 0.68, 0.03, 2), LF(1.065, hd / 2, -0.14), MAT.door);
      B.add(gRBox(0.006, 0.05, 0.09, 0.02, 2), LF(1.22, hf, -0.40), { c: '#8f887c', r: 0.5 });
      // horizontal pocket with a brushed grip block (0.33 x 0.14 / 0.22 x 0.12 at c-0.26, y 0.97)
      B.add(gQuad(0.33, 0.14), LF(0.97, hf, -0.26, Qf), { c: '#8a847b', r: 0.6 });   // w9a: mid-grey pocket (lalf_133), was near-black
      B.add(gRBox(0.035, 0.11, 0.22, 0.02, 1), LF(0.97, hf + 0.012, -0.26), MONMAT.steelBright);   // brushed silver grip (lalf_133)
      // painted red arc, r 0.29 about (c-0.10, 0.93): from a stop bar by the grip, over the top, arrowhead on the aft side
      const arc = [];
      for (let k = 0; k <= 20; k++) { const t = lerp(2.75, 0.45, k / 20), [ax, ay] = at(0.93 + 0.29 * Math.sin(t), hf + 0.002); arc.push([ax, ay, c + H * (-0.10 + 0.29 * Math.cos(t))]); }
      B.add(gTube(arc, 0.0125, 6), null, MONMAT.doorArc);
      B.add(gBox(0.008, 0.095, 0.035), LF(0.93 + 0.29 * Math.sin(2.75), hf + 0.002, -0.10 + 0.29 * Math.cos(2.75) - 0.02), MONMAT.doorArc);   // stop bar
      B.add(gCyl(0.032, 0.002, 0.06, 3), LF(0.93 + 0.29 * Math.sin(0.45) - 0.04, hf + 0.004, -0.10 + 0.29 * Math.cos(0.45), M4.trs(0, 0, 0, 0, 0, 0, 0.25, 1, 1)), MONMAT.doorArc);   // arrowhead, pointing down
      B.add(gQuad(0.13, 0.069), LF(0.90, hf + 0.001, 0.08, Qf), MAT.decal, atlasUV('doorPlacard'));            // red "OPEN" label
      // arming-indicator window in the upper fwd corner (0.19 x 0.27 at c-0.41, y 1.54): pictogram strip, lever with a
      // green / red band, red flag; two placards just aft at 1.45-1.55
      B.add(gRBox(0.012, 0.29, 0.21, 0.008, 1), LF(1.54, 0.006, -0.41), MAT.slide);
      B.add(gQuad(0.17, 0.25), LF(1.54, 0.0125, -0.41, Qf), { c: '#a9a8a2', r: 0.3 });      // w6a: light grey window (lalf_133)
      B.add(gQuad(0.13, 0.045), LF(1.63, 0.014, -0.41, Qf), MONMAT.cardWhite);
      B.add(gRBox(0.012, 0.11, 0.025, 0.006, 1), LF(1.52, 0.02, -0.44), MAT.handle);
      B.add(gQuad(0.025, 0.02), LF(1.555, 0.027, -0.44, Qf), MONMAT.green);
      B.add(gQuad(0.025, 0.02), LF(1.535, 0.027, -0.44, Qf), MONMAT.red);
      B.add(gQuad(0.03, 0.035), LF(1.46, 0.014, -0.37, Qf), MONMAT.red);
      for (const y of [1.47, 1.53]) B.add(gQuad(0.09, 0.045), LF(y, 0.004, -0.23, Qf), MONMAT.cardWhite);
      // slide bustle: ~1.0 m wide, top 0.75 m, 0.25 m deep, rounded front edge, rib at 0.40, black gauge window on top
      B.add(gRBox(0.25, 0.75, 1.0, 0.05, 2), LF(0.375, 0.125, 0), MAT.slide);
      B.add(gRBox(0.24, 0.05, 0.98, 0.025, 2), LF(0.735, 0.13, 0, M4.trs(0, 0, 0, 0, 0, side * 0.12)), MAT.slide);   // sloped top
      B.add(gBox(0.012, 0.022, 1.0), LF(0.40, 0.252, 0), MAT.slide);
      B.add(gQuad(0.10, 0.05), LF(0.765, 0.16, 0.40, M4.trs(0, 0, 0, side > 0 ? -Math.PI / 2 : Math.PI / 2, -Math.PI / 2)), { c: '#141416', r: 0.1 });
      // assist grab bar on 0.08 m standoffs (0.51 m, c-0.50..c+0.01, y 0.70) with a red-orange strap on its fwd half
      const g0 = at(0.70, 0.33);
      B.add(gTube([[g0[0], g0[1], c - H * 0.50], [g0[0], g0[1], c + H * 0.01]], 0.02, 10), null, MONMAT.steelBright);
      for (const dz of [-0.46, -0.03]) B.add(gBox(0.08, 0.02, 0.02), LF(0.70, 0.29, dz), MAT.handle);
      // w6a/b: crimson strap wrapped round the bar, its tail hanging below (lalf_133 #694755, lalf_134 #653441)
      B.add(gRBox(0.05, 0.05, 0.12, 0.012, 1), LF(0.70, 0.33, -0.33), { c: '#7a3442', r: 0.7, l: LAYER.fabric });
      B.add(gRBox(0.008, 0.09, 0.11, 0.004, 1), LF(0.63, 0.345, -0.33), { c: '#7a3442', r: 0.7, l: LAYER.fabric });
      // jamb assist handles: 0.25 m vertical grips in dark pockets at ~1.45 m; small EXIT placard on the aft jamb at 1.05
      for (const dz of [-0.64, 0.64]) {
        const p0 = at(1.325, 0.05), p1 = at(1.575, 0.05);
        B.add(gRBox(0.01, 0.30, 0.07, 0.01, 1), LF(1.45, 0.005, dz), { c: '#5a5650', r: 0.6 });
        B.add(gTube([[p0[0], p0[1], c + dz], [p1[0], p1[1], c + dz]], 0.014, 8), null, MAT.handle);
      }
      B.add(gQuad(0.07, 0.035), LF(1.05, 0.004, 0.64, Qf), MONMAT.cardWhite);
      // w8a: cream '非常口 EXIT' plate on the upper lining above the housing (lalf_133)
      B.add(gQuad(0.26, 0.094), LF(1.84, 0.004, 0, Qf), MAT.decal, atlasUV('exit'));
      // plain upper door with a horizontal seam at ~1.73 m
      B.add(gBox(0.004, 0.005, 1.04), LF(1.73, 0.002, 0), MAT.doorGap);
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
