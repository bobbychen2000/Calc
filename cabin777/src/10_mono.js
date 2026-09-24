// ------------------------------------------------------------------
// Monuments: lavatories (bidet / accessible / baby-change), galleys, the THE Room self-service bar
// (roller blinds + backlit washi-style panels), closets, flight-deck door, class partitions,
// Type A door linings and flight-attendant jump seats
// ------------------------------------------------------------------
const MONMAT = {
  laminate: { c: '#dcdad4', r: 0.45, l: LAYER.plastic },
  lavDoor: { c: '#e7e5df', r: 0.4, l: LAYER.plastic },
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
  cockpitDoor: { c: '#cfccc5', r: 0.45, l: LAYER.plastic },
  jump: { c: '#3a4049', r: 0.6, l: LAYER.fabric },
  harness: { c: '#1f2329', r: 0.8 },
  closet: { c: '#dedcd6', r: 0.45, l: LAYER.plastic },
  ash: { c: '#cdbfa6', r: 0.5, l: LAYER.wood },
  ashDark: { c: '#8a7560', r: 0.5, l: LAYER.wood },
  darkWood: { c: '#4a3629', r: 0.42, l: LAYER.wood },
  // door-3 bar / door-2 welcome galley, sampled from ANA's official bar-counter render (Jul 2019 press kit) and
  // OMAAT's in-service photos: light ash doors, dark-bronze frames, black basalt counter, black upper unit
  barAsh: { c: '#b9a687', r: 0.5, l: LAYER.ashGrain },
  bronze: { c: '#6f5f50', r: 0.35, m: 0.55, l: LAYER.brushed },
  basalt: { c: '#28262b', r: 0.22, l: LAYER.marble },
  black: { c: '#1b1a20', r: 0.35, l: LAYER.plastic },
  blackGloss: { c: '#0f0e13', r: 0.15 },
  blind: { c: '#1d1c22', r: 0.85, l: LAYER.fabric },                // decorative blind, pulled down (render)
  washi: { c: '#f2f3f6', r: 0.8, l: LAYER.atlasGlow, e: 0.6 },       // neutral-white backlit washi band (render)
  washiGalley: { c: '#d4d3e0', r: 0.8, l: LAYER.atlasGlow, e: 0.45 }, // lavender-grey galley washi (welcome render)
  downlight: { c: '#eef4ff', r: 0.3, e: 1.6 },
  fridgeLit: { c: '#8e9aa8', r: 0.5, e: 0.12 },
  bottleClear: { c: '#9fb2b6', r: 0.05, m: 0.3 },
  bottleBlue: { c: '#2346c8', r: 0.08, e: 0.12 },
  label: { c: '#f4f2ec', r: 0.6 },
  juice: { c: '#f0a526', r: 0.15 },
  tumbler: { c: '#c9d2d6', r: 0.05, m: 0.2 },
  navyPanel: { c: '#16172a', r: 0.35, l: LAYER.plastic },          // welcome end panel (render + sans_09)
  // standard galley inserts (SANspotter PY snack-bar photo): aluminium ovens/trolleys, black beverage makers,
  // black work deck, red-copper turn-button latches
  alu: { c: '#9c9fa3', r: 0.35, m: 0.7, l: LAYER.brushed },
  aluDark: { c: '#8f9194', r: 0.4, m: 0.7, l: LAYER.brushed },
  bevBlack: { c: '#17171a', r: 0.3 },
  copper: { c: '#a4533a', r: 0.3, m: 0.7 },
  deck: { c: '#26252a', r: 0.3, l: LAYER.plastic },
  card: { c: '#ece7c8', r: 0.7 },
  // class curtains sampled from ANA photos: F/J lavender-grey (f_17313), J/PY and PY/Y dark slate (py_37301/37302)
  curtainF: { c: '#8f90a8', r: 0.9, l: LAYER.fabric },
  curtainY: { c: '#474b5e', r: 0.9, l: LAYER.fabric },
  rail: { c: '#dcdbd6', r: 0.4 },
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
function bottle(B, xf, h, r, mat, lbl = true) {
  B.add(gCyl(r, r, h * 0.66, 10), M4.mul(xf, M4.trs(0, h * 0.33, 0)), mat);
  B.add(gCyl(r * 0.36, r, h * 0.24, 10), M4.mul(xf, M4.trs(0, h * 0.78, 0)), mat);
  if (lbl) B.add(gCyl(r * 1.04, r * 1.04, h * 0.2, 10, false), M4.mul(xf, M4.trs(0, h * 0.22, 0)), MONMAT.label);
}
// round flush stainless pull (bar render), on a face
function ringPull(B, xf) {
  B.add(gCyl(0.028, 0.028, 0.008, 16), M4.mul(xf, M4.trs(0, 0, 0.004, 0, Math.PI / 2)), MONMAT.steel);
  B.add(gCyl(0.019, 0.019, 0.008, 12), M4.mul(xf, M4.trs(0, 0, 0.006, 0, Math.PI / 2)), MONMAT.bronze);
  B.add(gBox(0.024, 0.006, 0.008), M4.mul(xf, M4.trs(0, 0, 0.011)), MONMAT.steel);
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
  B.add(gRBox(cw, BAR.deck - 0.02, 0.02, 0.006, 1), V(0, BAR.deck / 2, 0.006), MONMAT.bronze);
  B.add(gBox(cw, 0.07, 0.024), V(0, 0.035, 0.008), MONMAT.black);                         // toe kick
  for (const [a, b] of [[200, 335], [340, 598], [605, 862], [912, 1155], [1160, 1400], [1445, 1700], [1705, 1790]])
    B.add(gRBox(px(b) - px(a) - 0.006, 0.84, 0.014, 0.004, 1), V((px(a) + px(b)) / 2, 0.5, 0.022), MONMAT.barAsh);
  for (const p of [265, 395, 1340, 1640, 1760]) ringPull(B, V(px(p), 0.71, 0.029));
  // counter + stainless grab rail on stand-offs
  B.add(gRBox(w - 0.02, 0.035, BAR.set + 0.05, 0.008, 1), V(0, BAR.deck + 0.0175, (0.05 - BAR.set) / 2), MONMAT.basalt);
  B.add(gRBox(w - 0.03, 0.022, 0.02, 0.008, 1), V(0, BAR.deck - 0.012, 0.062), MONMAT.steel);
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
    for (let k = 0; k < 3; k++) bottle(B, V(up(1372) + k * 0.06, sy + 0.004, oU + 0.1), bh, 0.028, MONMAT.bottleBlue, false);
  }
  B.add(gRBox(0.07, 0.085, 0.02, 0.03, 2), V(up(1362), uy(470), oU + 0.125), MONMAT.bronze);
  B.add(gCyl(0.022, 0.022, 0.012, 14), M4.mul(V(up(1362), uy(470), oU + 0.136), M4.trs(0, 0, 0, 0, Math.PI / 2)), MONMAT.steel);
  // tumblers on the counter (render: four at the left)
  for (const p of [490, 535, 578, 655]) B.add(gCyl(0.04, 0.034, 0.085, 12), V(up(p), BAR.deck + 0.078, p === 655 ? -0.16 : -0.26), MONMAT.tumbler);
  // ash cheeks either side of the upper unit, up to the soffit
  for (const s of [-1, 1]) B.add(gBox((w - uw) / 2 - 0.02, BAR.canopy - uy0, 0.02), V(s * (uw / 2 + (w - uw) / 4), (uy0 + BAR.canopy) / 2, oU + 0.012), MONMAT.barAsh);
  // black soffit over the bar with three downlights, framed by backlit washi bands
  const cd = BAR.set + 0.12, cy = BAR.canopy, co = (0.12 - BAR.set) / 2;
  B.add(gBox(w, 0.05, cd), V(0, cy + 0.025, co), MONMAT.blackGloss);
  B.add(gBox(uw - 0.02, cy - BAR.upTop, 0.02), V(0, (cy + BAR.upTop) / 2, oU + 0.02), MONMAT.blackGloss);
  B.add(gQuad(w - 0.02, 0.10), V(0, cy - 0.001, 0.06, Math.PI / 2), MONMAT.washi, atlasUV('washi'));
  for (const s of [-1, 1]) B.add(gQuad(0.10, cd - 0.12), V(s * (w / 2 - 0.06), cy - 0.001, co - 0.06, Math.PI / 2), MONMAT.washi, atlasUV('washi'));
  B.add(gBox(w, 0.06, 0.012), V(0, cy - 0.03, 0.125), MONMAT.blackGloss);                                 // soffit lip
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
  B.add(gRBox(w - 0.03, 0.03, 0.03, 0.01, 1), V(0, dk + 0.005, 0.04), MONMAT.alu);
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
  const mc = -w / 2 + 0.82;
  B.add(gRBox(0.70, 0.43, 0.03, 0.01, 1), V(mc, 1.66, o + 0.02), SEATMAT.bezel);
  B.add(gQuad(0.66, 0.37), V(mc, 1.66, o + 0.036), SEATMAT.screen, atlasUV('screen'));
  B.add(gRBox(0.74, 0.02, 0.07, 0.006, 1), V(mc, 1.42, o + 0.04), MONMAT.blackGloss);
  B.add(gRBox(0.2, 0.3, 0.2, 0.01, 1), V(mc - 0.2, 1.19, o + 0.1), MONMAT.bevBlack);
  B.add(gCyl(0.05, 0.05, 0.12, 12), V(mc - 0.2, 1.1, o + 0.2), MONMAT.steel);
  B.add(gBox(0.04, 0.02, 0.004), V(mc - 0.17, 1.31, o + 0.202), MONMAT.green);
  B.add(gBox(0.3, 0.34, 0.01), V(mc + 0.17, 1.2, o), { c: '#121115', r: 0.5 });
  // right: tall glass-door cabinet with round latch and a placard above
  const gc = w / 2 - 0.3;
  B.add(gRBox(0.44, 0.8, 0.03, 0.01, 1), V(gc, 1.44, o + 0.02), MONMAT.blackGloss);
  B.add(gQuad(0.34, 0.66), V(gc + 0.02, 1.44, o + 0.037), { c: '#2c3036', r: 0.05, e: 0.06 });
  B.add(gRBox(0.08, 0.1, 0.02, 0.035, 2), V(gc - 0.17, 1.44, o + 0.045), MONMAT.aluDark);
  B.add(gRBox(0.3, 0.07, 0.012, 0.03, 2), V(gc, 1.92, o + 0.02), MONMAT.label);
  // portrait welcome monitors on navy end panels facing each aisle
  for (const s of [-1, 1]) {
    const x = s > 0 ? m.x1 : m.x0, zc = m.face > 0 ? m.z1 - 0.3 : m.z0 + 0.3;
    B.add(gBox(0.02, 2.0, 0.6), M4.trs(x + s * 0.01, 1.0, zc), MONMAT.navyPanel);
    for (const y of [0.35, 0.7]) B.add(gBox(0.012, 0.012, 0.56), M4.trs(x + s * 0.022, y, zc), MONMAT.steel);
    B.add(gRBox(0.3, 0.52, 0.012, 0.008, 1), M4.trs(x + s * 0.026, 1.55, zc, s * Math.PI / 2), SEATMAT.bezel);
    B.add(gQuad(0.27, 0.48), M4.trs(x + s * 0.033, 1.55, zc, s * Math.PI / 2), SEATMAT.screen, atlasUV('screen'));
  }
}

// ---- Standard galley (SANspotter "self serve snack bar" photo at door 4): full-size trolleys under a black work
// deck with red-copper turn-button latches; ovens / beverage makers / standard units and stowage in a set-back
// upper bank with a work light under it
function buildGalley(B, m, premium) {
  const w = m.x1 - m.x0, cx = (m.x0 + m.x1) / 2, set = 0.3, dk = 1.03;
  const body = premium ? MONMAT.ash : MONMAT.galleyWhite;
  monoStepBody(B, m, dk, set, body, body);
  const F = (x, y, o) => faceXF(m, x, y, o);
  const nC = m.carts || 2, usable = w - 0.1;
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
      B.add(gRBox(0.03, 0.05, 0.05, 0.01, 1), G(s * (cw / 2 + 0.005), dk - 0.03, 0.05), MONMAT.copper);
      B.add(gRBox(0.05, 0.02, 0.02, 0.008, 1), G(s * (cw / 2 - 0.02), 0.04, 0.06), MONMAT.copper);
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
      for (const s of [-1, 1]) B.add(gRBox(0.02, 0.05, 0.03, 0.008, 1), F(x + s * uW * 0.3, 1.3, o + 0.05), MONMAT.copper);
    } else if (t === 1) { // beverage maker: black face, green-lit button, steel jug in its bay
      B.add(gRBox(uW, 0.32, 0.12, 0.01, 1), F(x, 1.47, o + 0.06), MONMAT.bevBlack);
      B.add(gBox(0.022, 0.018, 0.006), F(x, 1.6, o + 0.122), MONMAT.green);
      B.add(gCyl(0.055, 0.06, 0.14, 12), F(x, 1.39, o + 0.13), MONMAT.steel);
    } else {              // standard unit with recessed pull
      B.add(gRBox(uW, 0.32, 0.03, 0.01, 1), F(x, 1.47, o + 0.015), MONMAT.aluDark);
      B.add(gRBox(0.08, 0.025, 0.02, 0.006, 1), F(x, 1.59, o + 0.035), MONMAT.bevBlack);
    }
    B.add(gRBox(uW, 0.36, 0.03, 0.01, 1), F(x, 1.86, o + 0.015), premium ? MONMAT.ashDark : MONMAT.galleyWhite);
    for (const s of [-1, 1]) B.add(gRBox(0.02, 0.045, 0.03, 0.008, 1), F(x + s * uW * 0.3, 1.69, o + 0.04), MONMAT.copper);
  }
  B.add(gQuad(0.2, 0.04), F(cx, 1.655, o + 0.032), MAT.decal, atlasUV('galleyLbl'));
}

// ---- Class curtains: ceiling track across the aisle opening, curtain gathered open as a pleated bundle at xg
const CURTAIN_H = 2.18;
let _curtainGeo = null;
function addCurtain(B, xa, xb, z, xg, mat) {
  if (!_curtainGeo) {
    const pts = [];
    for (let k = 0; k < 44; k++) { const a = (k / 44) * Math.PI * 2, r = 1 + 0.16 * Math.sin(a * 11); pts.push([Math.cos(a) * 0.085 * r, Math.sin(a) * 0.05 * r]); }
    _curtainGeo = gExtrude(pts, CURTAIN_H - 0.03, 55);
  }
  B.add(gBox(Math.abs(xb - xa), 0.02, 0.035), M4.trs((xa + xb) / 2, CURTAIN_H + 0.01, z), MONMAT.rail);
  B.add(_curtainGeo, M4.trs(xg, CURTAIN_H / 2 + 0.01, z, 0, Math.PI / 2), mat);
}

function buildMonuments(gl, layout, opts = {}) {
  const B = new Builder();
  for (const m of layout.mon) {
    const w = m.x1 - m.x0, cx = (m.x0 + m.x1) / 2;
    const inner = Math.abs(m.x0) < Math.abs(m.x1) ? m.x0 : m.x1;
    const cls = clsAt(layout, (m.z0 + m.z1) / 2);
    const premium = cls === 'F' || cls === 'J';
    const F = (x, y, o) => faceXF(m, x, y, o);
    if (m.kind === 'lav') {
      // exterior per the bar render (J lavs flanking the bar): ash door with dark-bronze frame lines, occupancy
      // plate (VACANT window) inboard of a recessed square pull, small ashtray high on the outboard side, lit sign
      monoBody(B, m, cls === 'F' ? MONMAT.darkWood : premium ? MONMAT.ash : MONMAT.laminate);
      const dw = Math.min(m.access ? 0.78 : 0.62, w - 0.14);
      const dx = Math.abs(inner) < 0.05 ? cx : inner + Math.sign(cx - inner) * (dw / 2 + 0.06);
      const J = cls === 'J', hw = J ? MONMAT.bronze : MONMAT.steelDark;
      const so = Math.abs(cx) < 0.05 ? 1 : Math.sign(cx) * m.face;          // viewer-right sign of the outboard side
      const at = (u, y, o) => F(dx + u * m.face, y, o);
      B.add(gRBox(dw, 1.86, 0.02, 0.01, 1), F(dx, 0.95, 0.008), cls === 'F' ? { c: '#5a4536', r: 0.4, l: LAYER.wood } : J ? MONMAT.barAsh : MONMAT.lavDoor);
      B.add(gBox(0.006, 1.8, 0.024), F(dx, 0.95, 0.009), { c: '#9ea3a9', r: 0.5 });                   // bi-fold seam
      if (J) {
        for (const s of [-1, 1]) B.add(gBox(0.014, 1.86, 0.026), at(s * (dw / 2 + 0.007), 0.95, 0.01), MONMAT.bronze);
        B.add(gBox(dw + 0.03, 0.014, 0.026), at(0, 1.887, 0.01), MONMAT.bronze);
      }
      B.add(gRBox(0.075, 0.085, 0.012, 0.006, 1), at(so * dw * 0.38, 1.15, 0.024), hw);                  // recessed pull
      B.add(gRBox(0.05, 0.055, 0.01, 0.004, 1), at(so * dw * 0.38, 1.15, 0.028), MONMAT.bevBlack);
      B.add(gRBox(0.11, 0.05, 0.012, 0.006, 1), at(so * dw * 0.18, 1.15, 0.024), hw);                    // occupancy plate
      B.add(gRBox(0.08, 0.022, 0.006, 0.003, 1), at(so * dw * 0.18, 1.15, 0.03), { c: '#dfe6dc', r: 0.4, e: 0.25 });
      B.add(gBox(0.03, 0.006, 0.004), at(so * dw * 0.18 - 0.02, 1.15, 0.034), MONMAT.green);
      B.add(gRBox(0.06, 0.07, 0.014, 0.006, 1), at(so * (dw / 2 + 0.07), 1.62, 0.008), hw);             // ashtray
      B.add(gRBox(0.045, 0.02, 0.008, 0.003, 1), at(so * (dw / 2 + 0.07), 1.64, 0.016), MONMAT.bevBlack);
      B.add(gRBox(dw - 0.1, 0.12, 0.006, 0.004, 1), F(dx, 0.12, 0.02), MAT.grille);
      B.add(gQuad(0.17, 0.082), F(dx, 1.99, 0.021), MAT.exitGlow, atlasUV('lav'));
      if (m.access) B.add(gRBox(0.09, 0.09, 0.006, 0.01, 1), F(dx - dw * 0.3, 1.45, 0.02), { c: '#2d62b8', r: 0.5 });
    } else if (m.kind === 'sideStorage') {
      monoBody(B, m, MONMAT.closet);
      B.add(gRBox(Math.abs(m.x1 - m.x0) - 0.06, 0.02, m.z1 - m.z0 - 0.06, 0.01, 1), M4.trs(cx, m.h + 0.005, (m.z0 + m.z1) / 2), { c: '#cfccc5', r: 0.4, l: LAYER.plastic });
    } else if (m.kind === 'closet') {
      monoBody(B, m, premium ? MONMAT.ash : MONMAT.closet);
      const dw = Math.min(0.72, w - 0.1);
      B.add(gRBox(dw, m.h - 0.12, 0.02, 0.01, 1), F(cx, m.h / 2, 0.008), premium ? (cls === 'F' ? MONMAT.darkWood : MONMAT.ashDark) : MONMAT.lavDoor);
      B.add(gRBox(0.03, 0.14, 0.03, 0.01, 1), F(cx - dw * 0.38, Math.min(1.05, m.h * 0.6), 0.03), MONMAT.steel);
      if (m.low) B.add(gRBox(w - 0.02, 0.03, m.z1 - m.z0 - 0.02, 0.01, 1), M4.trs(cx, m.h + 0.012, (m.z0 + m.z1) / 2), cls === 'F' ? MONMAT.darkWood : MONMAT.ash);
    } else if (m.kind === 'bar') {
      buildBar(B, m);
    } else if (m.kind === 'galley') {
      if (m.welcome) buildWelcomeGalley(B, m); else buildGalley(B, m, premium);
      if (!premium && m.face < 0) {
        // aft face over the first centre row (row 31 D-G): shared monitors + bassinet mounts (ANA seat map)
        const zb = m.z1 + 0.004;
        for (const x of [-0.5, 0.5]) {
          B.add(gRBox(0.40, 0.25, 0.03, 0.012, 1), M4.trs(x, 1.62, zb + 0.012), SEATMAT.bezel);
          B.add(gQuad(0.36, 0.2), M4.trs(x, 1.62, zb + 0.029), SEATMAT.screen, atlasUV('screen'));
        }
        B.add(gQuad(0.09, 0.06), M4.trs(0, 1.30, zb), MAT.decal, atlasUV('bassinet'));
        B.add(gRBox(0.3, 0.03, 0.02, 0.01, 1), M4.trs(0, 1.22, zb + 0.008), MONMAT.steelDark);
      }
    } else if (m.kind === 'cockpit') {
      const m2 = { ...m, face: 1 };
      B.add(gRBox(0.90, 1.96, 0.05, 0.01, 1), faceXF(m2, 0, 0.99, 0.0), MONMAT.cockpitDoor);
      B.add(gRBox(0.05, 0.1, 0.03, 0.01, 1), faceXF(m2, 0.34, 1.02, 0.03), MONMAT.steel);
      B.add(gCyl(0.012, 0.012, 0.01, 10), faceXF(m2, 0, 1.55, 0.03), MONMAT.ovenGlass);
      B.add(gQuad(0.08, 0.1), faceXF(m2, 0.56, 1.25, 0.0), MAT.decal, atlasUV('keypad'));
    } else if (m.kind === 'partition') {
      const wood = m.wood;
      B.add(gRBox(w, m.h, m.z1 - m.z0, 0.01, 1), M4.trs(cx, m.h / 2, (m.z0 + m.z1) / 2), wood ? MONMAT.ash : MONMAT.partition);
      B.add(gBox(w - 0.02, 0.12, m.z1 - m.z0 + 0.006), M4.trs(cx, 0.06, (m.z0 + m.z1) / 2), MONMAT.darkWood);
      const zf = m.z1 + 0.004;
      if (m.bassinet) {
        const n = Math.max(1, Math.round(w / 0.9));
        for (let k = 0; k < n; k++) {
          const x = m.x0 + (w / n) * (k + 0.5);
          if (Math.abs(x) > 2.5) continue;
          B.add(gQuad(0.09, 0.06), M4.trs(x, 1.30, zf), MAT.decal, atlasUV('bassinet'));
          B.add(gRBox(0.3, 0.03, 0.02, 0.01, 1), M4.trs(x, 1.22, zf + 0.008), MONMAT.steelDark);
        }
      }
      if (m.monitor) {
        const xs = Math.abs(cx) < 0.1 ? [-0.55, 0.55] : [cx];
        for (const x of xs) {
          B.add(gRBox(0.40, 0.25, 0.03, 0.012, 1), M4.trs(x, 1.52, zf + 0.012), SEATMAT.bezel);
          B.add(gQuad(0.36, 0.2), M4.trs(x, 1.52, zf + 0.029), SEATMAT.screen, atlasUV('screen'));
        }
      }
    }
  }
  // ---- class curtains, drawn open: in each aisle gap of the F/J and J/PY bulkheads (f_17313, py_37301/37302) and
  //      in the aisles beside the door-4 galley's aft face at the PY/Y break (y_47300); gathered at the centre side
  const parts = layout.mon.filter((m) => m.kind === 'partition').sort((a, b) => a.z0 - b.z0 || a.x0 - b.x0);
  for (let k = 0; k + 1 < parts.length; k++) {
    const a = parts[k], b = parts[k + 1];
    if (Math.abs(a.z0 - b.z0) > 0.01 || b.x0 - a.x1 < 0.2) continue;
    const zc = (a.z0 + a.z1) / 2, right = a.x1 > 0;
    addCurtain(B, a.x1, b.x0, zc, right ? a.x1 + 0.09 : b.x0 - 0.09, clsAt(layout, a.z0 - 0.5) === 'F' ? MONMAT.curtainF : MONMAT.curtainY);
  }
  for (const m of layout.mon) {
    if (m.kind !== 'galley' || m.face > 0 || clsAt(layout, m.z0) !== 'Y' || m.x1 - m.x0 > 3) continue;
    for (const s of [-1, 1]) {
      const xi = s > 0 ? m.x1 : m.x0;
      addCurtain(B, xi, xi + s * 0.52, m.z1 - 0.04, xi + s * 0.09, MONMAT.curtainY);
    }
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
          for (const dz of [-0.006, 0.006]) { g.p.push((x + nx * 0.003) * side, y + ny * 0.003, zz + dz); g.n.push(nx * side, ny, 0); g.u.push(0, 0); }
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
      const [rx, ry] = at(1.62, 0.02);
      B.add(gRBox(0.03, 0.05, 0.10, 0.01, 1), M4.trs(rx, ry, c - 0.25), MAT.handleRed);
      const [px, py] = at(0.95, 0.006);
      B.add(gQuad(0.2, 0.106), M4.trs(px, py, c - 0.2, side > 0 ? -Math.PI / 2 : Math.PI / 2), MAT.decal, atlasUV('doorPlacard'));
      const [sx, sy] = at(0.30, 0.05);
      const [, , snx, sny] = wallAt(0.30);
      B.add(gRBox(0.10, 0.36, 0.92, 0.04, 2), M4.trs(sx, sy, c, 0, 0, side > 0 ? -Math.atan2(sny, -snx) : Math.atan2(sny, -snx)), MAT.slide);
      for (const dz of [-0.64, 0.64]) {
        const p0 = at(0.95, 0.06), p1 = at(1.55, 0.06);
        B.add(gTube([[p0[0], p0[1], c + dz], [p1[0], p1[1], c + dz]], 0.014, 8), null, MAT.handle);
      }
    }
  }
  // ---- Flight attendant jump seats (folded) on monument faces beside each door ----
  const dz = layout.doorsZ;
  const jumps = opts.noDoors ? [] : [[-1.9, dz[0][0], 1], [2.3, dz[0][0], 1], [-0.75, dz[1][0], 1], [0.75, dz[1][0], 1], [2.1, dz[3][0], 1], [-0.6, dz[4][1], -1], [0.6, dz[4][1], -1]];
  for (const [x, z, f] of jumps) {
    const xf = M4.trs(x, 0, z + f * 0.05, f > 0 ? 0 : Math.PI);
    B.add(gRBox(0.46, 0.5, 0.07, 0.02, 1), M4.mul(xf, M4.trs(0, 0.78, 0)), MONMAT.jump);
    B.add(gRBox(0.44, 0.34, 0.06, 0.02, 1), M4.mul(xf, M4.trs(0, 1.25, -0.005)), MONMAT.jump);
    for (const s of [-1, 1]) B.add(gBox(0.04, 0.6, 0.012), M4.mul(xf, M4.trs(s * 0.12, 1.1, 0.04)), MONMAT.harness);
  }
  const geo = B.build();
  return { mesh: gl ? gl.mesh(geo, { name: 'monuments', layer: 'mono' }) : null, geo };
}
