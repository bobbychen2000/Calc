// ------------------------------------------------------------------
// THE Room business seat (Safran Fusio custom) nested pair - see REFERENCE777.md
// Seat-local frame and shared materials / helpers (SEATMAT, SEC, loftAt, cushionSecs) live in 09_seats.js.
// New materials for this product: Object.assign(SEATMAT, {...}) at the top of this file (loaded after 09_seats.js).
// ------------------------------------------------------------------
// ================= THE Room (nested pair unit) =================
// Unit frame: x in [-0.585, 0.585], outer column (window or centreline) at -x, aisle at +x;
// z in [-1.359, 1.359]; forward = -z. O = odd-row seat (rear-facing, outer column, forward half),
// E = even-row seat (forward-facing, aisle column, aft half). Each seat's footwell runs under the other
// seat's side table; each seat's 24 in monitor stands on the neighbour's console (see REFERENCE777.md).
// QA w1: monitor bezel dark charcoal with a slight sheen, not black (omaat_room_16, c_27316 #2c2e32) [V]; pillow reverse
// panel + piping grey-taupe (c_27303, omaat_room_13) [V]; ledge slot + retracted privacy-panel edge (omaat_room_13) [V]
Object.assign(SEATMAT, {
  jBezel: { c: '#3a3c42', r: 0.35, l: LAYER.plastic },   // QA w3: rendered near-black (L 18-29 vs photos 34-45)
  jSeam: { c: '#46444b', r: 0.95 },
  jCavity: { c: '#2c2d32', r: 0.9 },   // QA w4: footwell space reads charcoal, not black (tpg_53, c_27316) [V]
  jPillowBack: { c: '#6b665e', r: 0.8, l: LAYER.fabric },
  jPanelEdge: { c: '#5d6166', r: 0.34, m: 0.5, l: LAYER.brushed },
  jLedge: { c: '#8f959c', r: 0.3, m: 0.6, l: LAYER.brushed },   // ledge top, darker than the edge trim (c_27313 #788087-#b2bbc8) [V]
  jSill: { c: '#8e9399', r: 0.35, m: 0.4, l: LAYER.brushed },   // silver-grey sill + drawer under the monitor (tpg_53) [V]
  jLens: { c: '#55585d', r: 0.25 },   // reading-lamp lens, switched off (c_27315 / 27316 lamps read dark grey) [V]
});
const ROOM = { hx: 0.585, hz: 1.359, top: 0.66, wall: 1.12, bed: 0.43 };
// seat itself (passenger faces -z, back at z = 0): upright or bed. Per c_27302/27315/27316: thin flat cushion and a flat
// upholstered back (one horizontal seam) over a dark recessed base; headrest is a slate flap hanging from the back top
// w: cushion width (QA w2: the rear-facing O seat is a wide bench, ~0.8 m between its outer console and a narrow aisle
// armrest, holding two pillows side by side - tpg_31, tpg_42 [V]/[D]; E 0.64 (c_27303) [D]); fs: aisle side in seat-local x
function roomSeatCore(B, bed, lod, w = 0.64, fs = 1) {
  const F = SEATMAT.jFabric, k = w - 0.64;
  B.add(gRBox(0.54 + k, 0.33, 0.50, 0.015, 1), M4.trs(0, 0.165, -0.36), SEATMAT.jBase);
  if (bed) {
    B.add(gLoft(cushionSecs(w, 0.66, 0.075, -0.035, { edge: 0.02, r: 0.02, crown: 0.003 }), 4), M4.trs(0, 0.39, -0.35), F);
    return;
  }
  B.add(gLoft(cushionSecs(w, 0.60, 0.075, -0.035, { edge: 0.022, r: 0.02, crown: 0.004 }), lod ? 3 : 4), M4.trs(0, 0.39, -0.34, 0, 2 * DEG), F);
  const BH = M4.trs(0, 0.43, -0.17, 0, 12 * DEG);     // top of the back leans on the shell (shell face at z = -0.005)
  loftAt(B, [SEC(0.0, w - 0.02, 0.06, 0, 0.02), SEC(0.025, w, 0.075, 0, 0.026), SEC(0.52, w, 0.075, 0, 0.026), SEC(0.545, w - 0.02, 0.06, 0.002, 0.02)], BH, F, lod ? 2 : 3);
  // QA w3: back 0.545 tall so a ~0.16 padded header band shows above it on the shell (tpg_31 / 42) [D]
  // flap ~60 % of the back width, height / width ~0.38, hanging from the back top flush toward the aisle side (QA w2:
  // tpg_31 185 / 305 px, 70 / 185 px; omaat_room_13, c_27313 / 27315) [D]
  const fw = 0.6 * w, fx = fs * (w / 2 - 0.05 - fw / 2);
  B.add(gRBox(fw, 0.20, 0.018, 0.008, 1), M4.mul(BH, M4.trs(fx, 0.445, -0.058, 0, -3 * DEG)), SEATMAT.jHead);
  if (lod) return;
  // QA w3: soft fabric-toned channels ~0.58 / 0.82 of the back height down from its top (tpg_31, c_27315) [D]
  // QA w4: one continuous sofa - the back rolls into the cushion (fabric fillet) with three soft grooves across its lower
  // half (c_27315, c_27313, tpg_31) [V]
  for (const sy of [0.07, 0.15, 0.23]) B.add(gRBox(w - 0.04, 0.008, 0.004, 0.002, 1), M4.mul(BH, M4.trs(0, sy, -0.0385)), SEATMAT.jSeam);
  B.add(gRBox(w - 0.02, 0.07, 0.09, 0.03, 2), M4.trs(0, 0.445, -0.075), F);
  B.add(gBox(w - 0.04, 0.005, 0.004), M4.mul(M4.trs(0, 0.39, -0.34, 0, 2 * DEG), M4.trs(0, 0.041, -0.10, 0, Math.PI / 2)), SEATMAT.jBase);
  B.add(gRBox(0.03, 0.05, 0.012, 0.004, 1), M4.mul(BH, M4.trs(fx, 0.33, -0.05)), SEATMAT.jHead); // flap tab
  // seat front: continuous fabric apron (the stowed leg rest) from the cushion nose down to a dark kick strip (QA w2:
  // was a detached board; c_27313 / 27315) [V]
  B.add(gRBox(w - 0.02, 0.29, 0.04, 0.015, 1), M4.trs(0, 0.225, -0.62), F);
  B.add(gBox(w - 0.06, 0.08, 0.03), M4.trs(0, 0.04, -0.615), SEATMAT.jBase);
  B.add(gBox(w - 0.06, 0.004, 0.004), M4.trs(0, 0.25, -0.641), SEATMAT.jBase);                      // leg-rest seam
  // teal shoulder belt (c_27313 / 27316 show it lying on the cushion)
  // QA w4: on the half away from the pillows so it shows, diagonal with the silver buckle (tpg_31 / 42) [V]
  B.add(gBox(0.045, 0.004, 0.34), M4.trs(0.14, 0.433, -0.30, -0.5), { c: '#2f5f66', r: 0.7 });
  B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.trs(0.06, 0.436, -0.44), SEATMAT.buckle);
}

// charcoal frame round an ash panel (every ash face in the photos sits in a ~3 cm dark frame, c_27312-27315):
// panel in the plane x = px (thickness t) spanning y0..y1, z0..z1
function ashFrameX(B, px, t, y0, y1, z0, z1) {
  const f = 0.028, T = t + 0.008, m = SEATMAT.jShell;
  for (const z of [z0 + f / 2, z1 - f / 2]) B.add(gRBox(T, y1 - y0, f, 0.006, 1), M4.trs(px, (y0 + y1) / 2, z), m);
  for (const y of [y0 + f / 2, y1 - f / 2]) B.add(gRBox(T, f, z1 - z0, 0.006, 1), M4.trs(px, y, (z0 + z1) / 2), m);
}
// panel in the plane z = pz spanning x0..x1, y0..y1
function ashFrameZ(B, pz, t, x0, x1, y0, y1) {
  const f = 0.028, T = t + 0.008, m = SEATMAT.jShell;
  for (const x of [x0 + f / 2, x1 - f / 2]) B.add(gRBox(f, y1 - y0, T, 0.006, 1), M4.trs(x, (y0 + y1) / 2, pz), m);
  for (const y of [y0 + f / 2, y1 - f / 2]) B.add(gRBox(x1 - x0, f, T, 0.006, 1), M4.trs((x0 + x1) / 2, y, pz), m);
}
// shared bits of the shell: flat charcoal cap on a wall top (shell tops read as flat charcoal, #545557-#717277 in
// omaat_room_10 / 13; the silver line is only on armrest ledges + door-leaf edges), door leading edge with a finger pull
function capRail(B, w, d, x, y, z) { B.add(gRBox(w + 0.006, 0.02, d + 0.006, 0.006, 1), M4.trs(x, y + 0.01, z), SEATMAT.jCap); }
function doorEdge(B, x, z, h) {
  B.add(gRBox(0.05, h, 0.04, 0.014, 1), M4.trs(x, 0.14 + h / 2, z), SEATMAT.jShell);
  B.add(gRBox(0.046, h - 0.06, 0.006, 0.004, 1), M4.trs(x, 0.14 + h / 2, z + 0.021), SEATMAT.ash);
  B.add(gRBox(0.012, 0.16, 0.02, 0.005, 1), M4.trs(x - 0.02, 0.86, z + 0.025), SEATMAT.jBase);
  B.add(gBox(0.046, 0.004, 0.044), M4.trs(x, 0.142, z), SEATMAT.jRail);                          // silver leaf bottom edge
}
// plan-view (x, z) outline -> slab of height h with its bottom at y0 (gExtrude runs along its own z: turn it to y)
function planSlab(B, pts, y0, h, mat) { B.add(gExtrude(pts.map(([x, z]) => [x, -z]), h), M4.trs(0, y0 + h / 2, 0, 0, -Math.PI / 2), mat); }
// rounded rectangle in plan, corner radii [x0z0, x1z0, x1z1, x0z1]
function planRRect(x0, x1, z0, z1, r, seg = 6) {
  const cs = [[x0 + r[0], z0 + r[0], r[0], Math.PI], [x1 - r[1], z0 + r[1], r[1], 1.5 * Math.PI], [x1 - r[2], z1 - r[2], r[2], 0], [x0 + r[3], z1 - r[3], r[3], 0.5 * Math.PI]];
  const pts = [];
  for (const [cx, cz, rr, a0] of cs) for (let k = 0; k <= seg; k++) { const a = a0 + (k / seg) * Math.PI / 2; pts.push([cx + Math.cos(a) * rr, cz + Math.sin(a) * rr]); }
  return pts;
}
// thin wall following the x0 side and the z0 end of a plan rectangle, rounded (radius R) at the x0z0 corner
function planBand(x0, x1, z0, z1, R, t, seg = 6) {
  const cx = x0 + R, cz = z0 + R, pts = [[x0, z1]];
  for (let k = 0; k <= seg; k++) { const a = Math.PI + (k / seg) * Math.PI / 2; pts.push([cx + Math.cos(a) * R, cz + Math.sin(a) * R]); }
  pts.push([x1, z0], [x1, z0 + t]);
  for (let k = seg; k >= 0; k--) { const a = Math.PI + (k / seg) * Math.PI / 2; pts.push([cx + Math.cos(a) * (R - t), cz + Math.sin(a) * (R - t)]); }
  pts.push([x0 + t, z1]);
  return pts;
}
// footwell under a monitor: grey upholstered pad on a shelf in a dark cavity, open below with a low step
// (omaat_room_16 / 17, c_27316: pad #66656b ~0.04 thick; REFERENCE777: mouth 21 in, 14 in high) [D]/[A]
// QA r2: the pad is a wedge in plan - full width at the mouth (the model's 0.41-0.43 m gap; 21 in written), 12 in (0.30)
// at the far end - straight along the unit's outer wall (wall = -1: x0 side, +1: x1 side), the inboard edge a convex
// arc bulging 0.04 (omaat_room_17, c_27316 / omaat_room_16) [V]/[D]
function footwellPlan(x0, x1, zm, zf, wall, inset = 0) {
  const xw = wall < 0 ? x0 + inset : x1 - inset, sx = -wall, wm = x1 - x0 - 2 * inset, wf = 0.30 - 2 * inset;
  const zmi = zm + Math.sign(zf - zm) * inset, zfi = zf - Math.sign(zf - zm) * inset;
  const pts = [[xw, zmi], [xw + sx * wm, zmi]];
  for (let k = 1; k < 6; k++) {
    const t = k / 6;
    pts.push([xw + sx * (lerp(wm, wf, t) + 0.04 * Math.sin(Math.PI * t)), lerp(zmi, zfi, t)]);
  }
  pts.push([xw + sx * wf, zfi], [xw, zfi]);
  return pts;
}
function roomFootwell(B, x0, x1, zm, zf, wall) {
  const s = Math.sign(zf - zm);
  planSlab(B, footwellPlan(x0, x1, zm, zf, wall), 0.38, 0.02, SEATMAT.jShellIn);
  planSlab(B, footwellPlan(x0, x1, zm, zf, wall, 0.012), 0.40, 0.04, SEATMAT.jFabric);
  planSlab(B, footwellPlan(x0, x1, zm + s * 0.04, zf - s * 0.04, wall), 0.01, 0.36, SEATMAT.jCavity);
  B.add(gRBox(x1 - x0, 0.02, 0.16, 0.006, 1), M4.trs((x0 + x1) / 2, 0.12, zm + s * 0.08), SEATMAT.jShellIn);
}
// monitor + sill on the central monument face (plane z = zf, facing dir). QA w2 (tpg_53 square-on at 1073 px/m, omaat_room_16,
// c_27316): charcoal frame 0.595 x 0.405 round the 0.531 x 0.299 display, thickest border on top (~0.05); under it one
// silver-grey sill 0.49 x 0.084 from the column-side frame edge: a 0.28 drawer with a green LED on the column side and a
// 0.21 blue-lit literature slot toward the cabinet (slotSide) [D]
function roomMonitor(B, xm, zf, dir, slotSide) {
  const zo = (d) => zf + dir * d, ry = dir > 0 ? 0 : Math.PI;
  B.add(gRBox(0.595, 0.405, 0.03, 0.015, 1), M4.trs(xm, 0.8475, zo(0.015)), SEATMAT.jBezel);
  B.add(gQuad(0.531, 0.299), M4.trs(xm, 0.85, zo(0.032), ry), SEATMAT.screen, atlasUV('screen'));
  const x0 = xm - slotSide * 0.2975, sc = x0 + slotSide * 0.245, y = 0.60;
  B.add(gRBox(0.49, 0.084, 0.03, 0.006, 1), M4.trs(sc, y, zo(0.01)), SEATMAT.jSill);
  const dx = x0 + slotSide * 0.145, lx = x0 + slotSide * 0.38;
  B.add(gRBox(0.27, 0.06, 0.008, 0.004, 1), M4.trs(dx, y, zo(0.027)), SEATMAT.jSill);                    // drawer face
  B.add(gBox(0.002, 0.058, 0.004), M4.trs(dx + slotSide * 0.136, y, zo(0.026)), SEATMAT.jBase);        // drawer gap
  B.add(gBox(0.09, 0.005, 0.004), M4.trs(dx, y + 0.012, zo(0.031)), SEATMAT.jShellIn);                   // pull lip
  B.add(gCyl(0.003, 0.003, 0.004, 8), M4.mul(M4.trs(dx + slotSide * 0.07, y - 0.005, zo(0.032)), M4.trs(0, 0, 0, 0, Math.PI / 2)), SEATMAT.ledG);
  // literature slot: recess glowing soft blue from inside, the sill forms its lip (tpg_53, omaat_room_14 / 16)
  B.add(gBox(0.19, 0.05, 0.004), M4.trs(lx, y - 0.004, zo(0.0255)), SEATMAT.jVoid);
  B.add(gQuad(0.18, 0.04), M4.trs(lx, y - 0.006, zo(0.028), ry), { c: '#1f2c7a', r: 0.6, e: 0.04 });   // QA w3: unlit navy lining (tpg_53)
  B.add(gBox(0.19, 0.004, 0.006), M4.trs(lx, y - 0.028, zo(0.029)), SEATMAT.jSill);
}
// closed cabinet door beside the monitor on the same plane: plain ash with fine horizontal grain, 0.34 x 0.38 with its
// top level with the monitor frame top, 4 mm silver bottom trim (omaat_room_16; mirror + navy interior only when open,
// omaat_room_21) [D]
// QA r2: the door is split ~0.06 above its bottom into a lower ash band, with slim grey side stiles (c_27305 split ~0.07
// above the bottom; omaat_room_16 lower band 45 / 255 px of the cabinet height; tt_storage-3) [D]
// QA w2: 0.43 tall, top ~0.015 above the monitor frame (tpg_53 / omaat_room_16 measured 0.43-0.44) [D]
function roomCabinet(B, xc, zf, dir) {
  const z = zf + dir * 0.004, H = 0.43;
  B.add(gRBox(0.34, H - 0.07, 0.012, 0.004, 1), M4.trs(xc, ROOM.top + 0.07 + (H - 0.07) / 2, z), SEATMAT.ash);
  B.add(gRBox(0.34, 0.058, 0.012, 0.004, 1), M4.trs(xc, ROOM.top + 0.035, z), SEATMAT.ash);
  B.add(gBox(0.34, 0.006, 0.008), M4.trs(xc, ROOM.top + 0.067, zf + dir * 0.002), SEATMAT.jShell);      // 4 mm split
  for (const s of [-1, 1]) B.add(gBox(0.008, H, 0.014), M4.trs(xc + s * 0.174, ROOM.top + H / 2, z), SEATMAT.jShell);
  B.add(gBox(0.34, 0.004, 0.016), M4.trs(xc, ROOM.top + 0.002, z), SEATMAT.jRail);
}
// seat controls on the console's vertical face (QA w2: tpg_53 / tpg_51 at 1073 px/m, gstp_ana-the-room-38, tt_seat-controls,
// c_27316): a mid-grey curved plate ~0.14 x 0.15 with white-outline icon buttons printed on it in four rows - thumb wheel,
// 3 round buttons (middle one blue: lie-flat), a long pill with the seat-position icons, round + pill + round [V]; beside
// it a black gamepad-shaped handset ~0.13 x 0.075 with a colour screen between two round button pads [V].
// xf: local x along the face, +z out of it
const RING = { c: '#d8dde3', r: 0.4, e: 0.15 };
// QA w3 (tpg_53, c_27316): on O's table the handset sits on the monitor side just under the table edge, plate ~0.08 lower
function roomControls(B, xf, side, dy = 0, hy = 0.555) {
  const P0 = (x, y, z, rx = 0) => M4.mul(xf, M4.trs(x, y, z, 0, rx)), P = (x, y, z, rx) => P0(x, y + dy, z, rx);
  B.add(gRBox(0.14, 0.15, 0.006, 0.03, 1), P(0, 0.545, 0.002), SEATMAT.jCap);
  B.add(gRBox(0.09, 0.02, 0.006, 0.01, 1), P(0, 0.598, 0.005), SEATMAT.black);                      // thumb wheel
  const ring = (x, y, r, blue) => {
    B.add(gCyl(r, r, 0.002, 10, !!blue), P(x, y, 0.0055, Math.PI / 2), blue ? { c: '#6c9cff', r: 0.4, e: 0.35 } : RING);
    if (blue) return;                                   // lie-flat key: a filled glowing blue disc (gstp-38) [V]
    B.add(gCyl(r - 0.0025, r - 0.0025, 0.002, 10), P(x, y, 0.0065, Math.PI / 2), SEATMAT.jCap);
  };
  const pill = (x, y, w) => {
    B.add(gRBox(w, 0.024, 0.002, 0.011, 1), P(x, y, 0.0055), RING);
    B.add(gRBox(w - 0.005, 0.019, 0.002, 0.0085, 1), P(x, y, 0.0065), SEATMAT.jCap);
  };
  for (const [x, b] of [[-0.044, 0], [0, 1], [0.044, 0]]) ring(x, 0.566, b ? 0.015 : 0.013, b);
  pill(0, 0.532, 0.105);
  ring(-0.044, 0.497, 0.012); pill(0.004, 0.497, 0.055); ring(0.05, 0.50, 0.01);
  // handset: black gamepad capsule in a dark recess, colour screen between two round button pads
  const hx = side * 0.16;
  B.add(gRBox(0.14, 0.085, 0.004, 0.035, 1), P0(hx, hy, 0.001), SEATMAT.jBase);
  B.add(gRBox(0.13, 0.075, 0.016, 0.034, 1), P0(hx, hy, 0.008), SEATMAT.black);
  B.add(gQuad(0.074, 0.064), P0(hx, hy + 0.001, 0.0165), SEATMAT.screen, atlasUV('screen'));   // QA w3: screen ~57 % x 90 % (tpg_53)
  // QA w4: a dark ring pad at one end, four coloured keys at the other (tpg_53, gstp-38) [V]
  B.add(gCyl(0.012, 0.012, 0.003, 10), P0(hx - 0.051, hy, 0.016, Math.PI / 2), SEATMAT.jBezel);
  B.add(gCyl(0.009, 0.009, 0.002, 10, false), P0(hx - 0.051, hy, 0.0175, Math.PI / 2), { c: '#8a9098', r: 0.3, m: 0.5 });
  ['#c8423a', '#3aa55a', '#3a6fd0', '#d8b23a'].forEach((c, k) => B.add(gCyl(0.004, 0.004, 0.003, 8), P0(hx + 0.051 + 0.008 * Math.cos(k * Math.PI / 2), hy + 0.008 * Math.sin(k * Math.PI / 2), 0.0165, Math.PI / 2), { c, r: 0.4 }));
}
// ash panels in ~28 mm charcoal frames on an aisle face (x = px) below the armrest ledge, charcoal kick below
// (c_27313 bottom row, omaat_room_10)
function roomAisleAsh(B, px, z0, z1) {
  B.add(gRBox(0.008, 0.52, z1 - z0 - 0.02, 0.003, 1), M4.trs(px + 0.002, 0.36, (z0 + z1) / 2), SEATMAT.ash);
  ashFrameX(B, px + 0.002, 0.008, 0.10, 0.62, z0 + 0.005, z1 - 0.005);
}
// reading light in the shell corner: large black lamp in a bezel ring + small fitting below (omaat_room_13, c_27315)
function roomLamp(B, x, z, dir, y = 1.03) {
  const rx = dir > 0 ? Math.PI / 2 : -Math.PI / 2;
  B.add(gCyl(0.028, 0.028, 0.012, 12), M4.trs(x, y, z + dir * 0.004, 0, rx), { c: '#9aa0a8', r: 0.3, m: 0.6 });   // ring bezel (ff_17e, fb_a96b7a65) [V]
  B.add(gCyl(0.022, 0.022, 0.02, 10, false), M4.trs(x, y, z + dir * 0.008, 0, rx), SEATMAT.black);
  B.add(gCyl(0.015, 0.015, 0.004, 10), M4.trs(x, y, z + dir * 0.0185, 0, rx), SEATMAT.jLens);   // off: dark frosted lens
  B.add(gCyl(0.014, 0.014, 0.014, 10), M4.trs(x, y - 0.045, z + dir * 0.006, 0, rx), SEATMAT.black);
}
// QA w3: angled charcoal wing on the far side of the monitor from the cabinet (c_27316 / tpg_53: ~0.15 long, running from
// the frame edge back toward the passenger, top flush with the monument), the big reading lamp over a round air nozzle on
// its face [V]; (xa, zf) = hinge at the frame edge, (xb, zf + dir * 0.12) = free edge; faces the passenger at (px, pz)
function roomWing(B, xa, xb, zf, dir, y0, px, pz) {
  const zb = zf + dir * 0.12, L = Math.hypot(xb - xa, zb - zf), h = MON.top + 0.02 - y0;
  let nx = (zb - zf) / L, nz = -(xb - xa) / L;
  const cx = (xa + xb) / 2, cz = (zf + zb) / 2;
  if (nx * (px - cx) + nz * (pz - cz) < 0) { nx = -nx; nz = -nz; }
  const ry = Math.atan2(nx, nz);
  B.add(gRBox(L, h, 0.03, 0.008, 1), M4.trs(cx - nx * 0.015, y0 + h / 2, cz - nz * 0.015, ry), SEATMAT.jShell);
  const T = new Builder(); roomLamp(T, 0, 0, 1, 1.0); B.addBuilt(T.build(), M4.trs(cx, 0, cz, ry));
}
// full-size safety card (~0.20 x 0.25, white with a blue header 'B777-300') in a pocket on the wall beside the footwell
// mouth (tpg_53, c_27316, up_ANA-The-Room-Seat-6H) [V]; plane x = px facing +x (s = 1) or -x
function roomCard(B, px, s, y, z) {
  const ry = s * Math.PI / 2;
  B.add(gRBox(0.006, 0.20, 0.22, 0.004, 1), M4.trs(px + s * 0.002, y - 0.02, z), SEATMAT.jShellIn);
  B.add(gQuad(0.20, 0.25), M4.trs(px + s * 0.0055, y, z, ry), { c: '#e6e9ef', r: 0.7 });
  B.add(gQuad(0.20, 0.05), M4.trs(px + s * 0.006, y + 0.09, z, ry), { c: '#2d5bb0', r: 0.6 });
  B.add(gRBox(0.008, 0.13, 0.22, 0.004, 1), M4.trs(px + s * 0.012, y - 0.07, z), SEATMAT.jShellIn);   // pocket front
}
// aisle armrest ledge: silver stepped ledge (6 mm lower step on its aisle edge) with a dark lengthwise slot holding the
// grey-metal top edge of the retracted pop-up privacy panel (omaat_room_13, c_27313 bottom corners; QA r3 had an ash strip) [V]
function roomLedge(B, w, x, z, L) {
  const y = ROOM.top;
  const xg = x + w / 2 - 0.05;
  B.add(gRBox(w - 0.03, 0.03, L + 0.02, 0.012, 1), M4.trs(x - 0.015, y + 0.01, z), SEATMAT.jLedge);
  for (const e of [-1, 1]) for (let k = 0; k < 3; k++) B.add(gBox(w - 0.03, 0.008, 0.006), M4.trs(x - 0.015, y - 0.012 - k * 0.018, z + e * (L / 2 + 0.013)), SEATMAT.jRail);
  B.add(gRBox(0.03, 0.03, L + 0.02, 0.008, 1), M4.trs(x + w / 2 - 0.015, y + 0.004, z), SEATMAT.jRail);
  B.add(gBox(0.03, 0.008, L), M4.trs(xg, y + 0.023, z), SEATMAT.jVoid);
  B.add(gBox(0.012, 0.004, L - 0.02), M4.trs(xg, y + 0.026, z), SEATMAT.jPanelEdge);
}

// Central monument of a pair between z = MON.zO (O's face, looking -z at O) and MON.zE (E's face, +z): O's monitor
// (outer column) back to back with E's cabinet, O's cabinet (aisle column) back to back with E's monitor; both footwells
// run under it (omaat_room_14 / 16, c_27316: cabinet flush beside the monitor frame, footwell mouth under the monitor)
const MON = { zO: -0.21, zE: 0.035, top: 1.10, bot: 0.555 };   // QA w2: top raised to clear the 0.43 cabinet
const CON = { top: 0.60 };
// boarding set-up: duvet folded on a white mattress pad, both in clear plastic, under the pillows (tpg_31, tpg_42) [V];
// the plastic reads as a sheen -> low roughness [A]
function roomBundle(B, x, z) {
  B.add(gRBox(0.44, 0.03, 0.34, 0.012, 1), M4.trs(x, 0.448, z), { c: '#eceae4', r: 0.25 });
  B.add(gRBox(0.42, 0.045, 0.30, 0.018, 1), M4.trs(x + 0.01, 0.485, z - 0.01), { c: '#5a5c9a', r: 0.25, l: LAYER.fabric });
}   // outer console top (c_27316 / 27303: ~0.17 above the cushion) [A]
// QA w1 pillow: flat piped rectangle ~0.44 x 0.34 x 0.07, navy check jacquard face, grey-taupe reverse panel + piping
// (c_27303, omaat_room_13) [V]
function roomPillow(B, xf) {
  B.add(gLoft(cushionSecs(0.44, 0.34, 0.07, -0.035, { edge: 0.015, r: 0.02 }), 3), xf, SEATMAT.pillowBlue);
  B.add(gRBox(0.43, 0.004, 0.33, 0.015, 1), M4.mul(xf, M4.trs(0, -0.035, 0)), SEATMAT.jPillowBack);
}
// QA w2 duvet: indigo comforter with a square ~0.26 m quilt grid, open over the bed from below the pillow to the foot and
// hanging over the mattress edges (fb_a96b7a65 #4b5789, fb_d8b6dc0d #606ea0 daylight; w1's slate read of tt_bed-2 was a
// night-light cast) [V]; white pillow + the blue one lying beside it (fb_a96b7a65) [V]
function roomDuvet(B, x, z, w, L) {
  // QA w4: thinner, softer comforter with flush stitch lines (was a rigid slab with raised grid)
  const W = w + 0.08, y = ROOM.bed + 0.0915, q = { c: '#4a4c84', r: 0.95 };
  B.add(gLoft(cushionSecs(W, L, 0.045, -0.035, { edge: 0.05, r: 0.045, crown: 0.012 }), 3), M4.trs(x, ROOM.bed + 0.07, z), SEATMAT.duvet);
  for (let k = 1; k * 0.26 < L - 0.05; k++) B.add(gBox(W - 0.10, 0.001, 0.005), M4.trs(x, y, z - L / 2 + k * 0.26), q);
  for (const dx of [-0.13, 0.13]) B.add(gBox(0.005, 0.001, L - 0.10), M4.trs(x + dx, y, z), q);
}
function roomPart(part, opts = {}) {
  const B = new Builder();
  const bed = !!opts.bed, lod = !!opts.lod;
  const { hx, hz, top, wall } = ROOM;
  const shell = SEATMAT.jShell, ash = SEATMAT.ash;
  if (part === 'O') {
    // --- the seat: back against the forward end, facing aft (+z)
    // QA w2: wide bench (0.84) from the outer console to a narrow aisle armrest (tpg_31 / 42) [D]
    const SX = -0.075, SW = 0.84, ax0 = SX + SW / 2, az1 = -0.80;
    const S = M4.trs(SX, 0, -1.27, Math.PI);
    const tmp = new Builder(); roomSeatCore(tmp, bed, lod, SW, -1); B.addBuilt(tmp.build(), S);
    // back shell across the whole unit: charcoal wall, padded band above the seat back, cap, a reading light at each end
    // (tpg_31 / 42: lamps in both top corners) [V]
    B.add(gRBox(1.17, wall, 0.07, 0.03, 2), M4.trs(0, wall / 2, -1.31), shell);
    B.add(gRBox(1.17, 0.155, 0.05, 0.02, 1), M4.trs(0, 1.0425, -1.25), SEATMAT.jHead);          // padded header band, same pale slate leather as the flap (QA w4b: tpg_42 band = flap) [V]
    capRail(B, 1.17, 0.07, 0, wall, -1.31);
    roomLamp(B, -0.50, -1.225, 1);
    roomLamp(B, 0.45, -1.225, 1);
    // narrow aisle armrest (~0.24) along the seat, LOW ledge (0.66) holding the retracted pop-up privacy panel, stowage
    // pocket on its seat-facing side (tpg_31 / 42, c_27313) [V]
    B.add(gRBox(hx - ax0, top, az1 + 1.34, 0.02, 1), M4.trs((ax0 + hx) / 2, top / 2, (az1 - 1.34) / 2), shell);
    roomLedge(B, hx - ax0, (ax0 + hx) / 2, (az1 - 1.34) / 2, az1 + 1.32);
    roomAisleAsh(B, hx, -1.34, az1);
    if (!lod) {
      B.add(gRBox(0.004, 0.16, 0.30, 0.004, 1), M4.trs(ax0 - 0.002, 0.44, -1.02), SEATMAT.jShellIn);     // side pocket
      B.add(gRBox(0.08, 0.05, 0.004, 0.004, 1), M4.trs(0.47, 0.50, az1 + 0.0015), SEATMAT.black);        // stowage latch
    }
    // O's side table over E's footwell (aisle column): ash top with a large-radius rounded front corner, thin silver band
    // under it, charcoal console body whose seat-facing face carries the controls (omaat_room_14 / 18, c_27316)
    const tx0 = 0.0, tx1 = 0.55, tz0 = -0.62, R = 0.11;   // QA w2: over the whole E footwell mouth (tpg_53) [D]
    // QA w3: ash inlay in a ~22 mm charcoal rim with a fine silver lip, not a solid ash slab (fb_a96b7a65, tpg_53, c_27316) [V]
    planSlab(B, planRRect(tx0, tx1, tz0, MON.zO, [R, 0.01, 0.004, 0.004]), top - 0.035, 0.033, SEATMAT.jShellIn);
    planSlab(B, planRRect(tx0 + 0.001, tx1 - 0.001, tz0 + 0.001, MON.zO, [R - 0.001, 0.009, 0.004, 0.004]), top - 0.006, 0.004, SEATMAT.jRail);
    planSlab(B, planRRect(tx0 + 0.022, tx1 - 0.022, tz0 + 0.022, MON.zO - 0.004, [R - 0.022, 0.004, 0.004, 0.004]), top - 0.004, 0.005, ash);
    planSlab(B, planRRect(tx0 + 0.004, tx1, tz0 + 0.004, MON.zO, [R - 0.004, 0.004, 0.004, 0.004]), top - 0.041, 0.006, SEATMAT.jRail);
    planSlab(B, planBand(tx0 + 0.012, tx1, tz0 + 0.012, MON.zO, R - 0.012, 0.02), 0, top - 0.041, shell);
    if (!lod) roomControls(B, M4.trs(0.33, 0, tz0 + 0.012, Math.PI), 1, -0.08, 0.568);
    // tall ash monument end at the aisle with a wide flat cap (seat plaques lie on it, c_27313) + kick
    const ez0 = -0.58, ez1 = MON.zE, ezc = (ez0 + ez1) / 2;
    B.add(gRBox(0.04, wall, ez1 - ez0, 0.012, 1), M4.trs(0.565, wall / 2, ezc), ash);
    B.add(gRBox(0.045, 0.10, ez1 - ez0, 0.01, 1), M4.trs(0.565, 0.05, ezc), shell);
    ashFrameX(B, 0.565, 0.04, 0.10, wall, ez0, ez1);
    // shared aisle-end cap: mid grey, a little darker than the plaques, oval finger recess between them (c_27314)
    B.add(gRBox(0.10, 0.02, ez1 - ez0 + 0.006, 0.006, 1), M4.trs(0.54, wall + 0.01, ezc), { c: '#86837e', r: 0.28, m: 0.35, l: LAYER.brushed });   // QA w3: slight metallic sheen (tpg_78)
    if (!lod) B.add(gCyl(1, 1, 1, 16), M4.trs(0.545, wall + 0.0205, ezc, 0, 0, 0, 0.0175, 0.003, 0.035), SEATMAT.jShellIn);   // QA w3: was a black hole
    // E's footwell under the table + monument (aisle column), mouth under E's monitor
    // QA w2: both footwell mouths sit square under their monitors, ~0.475 wide from the column-side frame edge, split by a
    // thin 0.05 pillar (tpg_53: opening under the monitor, 0.475 m) [D]
    B.add(gRBox(0.45, 0.02, MON.zO - tz0 - 0.03, 0.006, 1), M4.trs(0.2375, 0.57, (MON.zO + tz0 + 0.03) / 2), SEATMAT.jShellIn);
    roomFootwell(B, 0.02, 0.455, MON.zE, tz0 + 0.035, 1);
    // sliding door parked in the monument; its leading edge (ash face, charcoal frame, finger pull) faces aft
    doorEdge(B, 0.56, -0.60, wall - 0.14);
    // central monument body (both columns) + the pillar between the two footwell mouths
    B.add(gRBox(1.13, MON.top - MON.bot, MON.zE - MON.zO, 0.01, 1), M4.trs(-0.02, (MON.top + MON.bot) / 2, (MON.zO + MON.zE) / 2), shell);
    B.add(gRBox(0.05, MON.bot, MON.zE - MON.zO, 0.01, 1), M4.trs(-0.005, MON.bot / 2, (MON.zO + MON.zE) / 2), shell);
    // O's face: monitor (outer column) + O's cabinet (aisle column)
    roomMonitor(B, -0.20, MON.zO, -1, 1);
    roomCabinet(B, 0.275, MON.zO, -1);
    roomWing(B, -0.4975, -0.585, MON.zO, -1, CON.top, -0.075, -1.0);
    if (!lod) roomCard(B, -0.4995, 1, 0.36, -0.33);
    // O's footwell under E's console (outer column), mouth under O's monitor
    B.add(gRBox(0.52, 0.02, 0.585, 0.006, 1), M4.trs(-0.30, 0.57, 0.33), SEATMAT.jShellIn);
    roomFootwell(B, -0.505, -0.03, MON.zO, 0.62, -1);
    if (bed) {
      // the bed narrows to ~0.62 past the seat into the footwell; mattress + duvet follow the seat width (fb_a96b7a65) [A]
      B.add(gLoft(cushionSecs(0.76, 1.76, 0.05, -0.02, { edge: 0.02, r: 0.03, crown: 0.004 }), 3), M4.trs(SX - 0.02, ROOM.bed + 0.02, -0.40), SEATMAT.mattress);
      roomDuvet(B, SX - 0.02, -0.20, 0.72, 1.35);
      B.add(gLoft(cushionSecs(0.46, 0.30, 0.12, -0.06, { edge: 0.05, r: 0.05 }), 3), M4.trs(SX - 0.12, ROOM.bed + 0.08, -1.08), SEATMAT.pillow);
      roomPillow(B, M4.trs(SX + 0.20, ROOM.bed + 0.075, -1.04, 0, 0.1));
    } else {
      // white pillow leaning on the back with the blue one in front of it, toward the aisle half (tpg_31 / 42) [V]
      roomBundle(B, 0.07, -0.92);
      B.add(gLoft(cushionSecs(0.50, 0.34, 0.10, -0.05, { edge: 0.04, r: 0.04 }), 3), M4.mul(M4.trs(0.06, 0.61, -1.10, Math.PI), M4.trs(0, 0, 0, 0.05, -74 * DEG)), SEATMAT.pillow);
      roomPillow(B, M4.mul(M4.trs(0.08, 0.575, -1.02, Math.PI), M4.trs(0, 0, 0, 0.08, -68 * DEG)));
    }
    // outer side (window / centreline): the thin outer wall, then a console 0.085 deep with a charcoal cap along the seat
    // up to the monitor monument, red life-vest tab + stowage latch on its seat face (c_27316 left, c_27303 / 27300 window
    // side, c_27314 centre: console under the ash band) [V]; a low toe kick under the seat keeps the 777 dado + grille
    // (07_shell DADO, x 2.70 at the floor) out of the unit (QA r3 high) [D]
    B.add(gRBox(0.025, top, 1.39, 0.01, 1), M4.trs(-0.572, top / 2, -0.66), shell);
    capRail(B, 0.025, 1.39, -0.572, top, -0.66);
    const cz0 = -1.275, cz1 = MON.zO, czc = (cz0 + cz1) / 2;
    B.add(gRBox(0.085, CON.top, cz1 - cz0, 0.01, 1), M4.trs(-0.5425, CON.top / 2, czc), shell);
    capRail(B, 0.085, cz1 - cz0, -0.5425, CON.top, czc);
    B.add(gRBox(0.16, 0.22, cz1 - cz0 + 0.04, 0.01, 1), M4.trs(-0.505, 0.11, czc + 0.02), SEATMAT.jShellIn);
    if (!lod) {
      B.add(gRBox(0.006, 0.05, 0.02, 0.003, 1), M4.trs(-0.4985, 0.47, -0.52), { c: '#b3262a', r: 0.5 });
      B.add(gRBox(0.004, 0.14, 0.34, 0.004, 1), M4.trs(-0.499, 0.42, -0.78), SEATMAT.jShellIn);         // stowage door
      B.add(gRBox(0.006, 0.03, 0.05, 0.004, 1), M4.trs(-0.497, 0.44, -0.62), SEATMAT.black);
    }
  } else {
    // --- E: back at the aft end, facing forward (-z), aisle column
    const S = M4.trs(0.20, 0, 1.27);
    const tmp = new Builder(); roomSeatCore(tmp, bed, lod, 0.64, 1); B.addBuilt(tmp.build(), S);
    B.add(gRBox(0.69, wall, 0.07, 0.03, 2), M4.trs(0.235, wall / 2, 1.31), shell);
    B.add(gRBox(0.69, 0.155, 0.05, 0.02, 1), M4.trs(0.235, 1.0425, 1.25), SEATMAT.jHead);        // padded header band (as O)
    capRail(B, 0.69, 0.07, 0.235, wall, 1.31);
    roomLamp(B, -0.07, 1.225, -1);
    roomLamp(B, 0.50, 1.225, -1);
    // narrow aisle armrest with the pop-up privacy panel retracted inside (ash edge flush in the cap)
    B.add(gRBox(0.09, top, 0.60, 0.02, 1), M4.trs(0.54, top / 2, 0.95), shell);
    roomLedge(B, 0.10, 0.54, 0.95, 0.60);
    roomAisleAsh(B, hx, 0.65, 1.25);
    // outer column beside E: ash side table only over O's footwell (monument to z 0.62, large-radius seat-side corner),
    // then a charcoal console at the outer-console height to the back shell (QA w2: the old 1.27 m ash slab; c_27315
    // 14D, fb_a96b7a65 bed from above, c_27314: ash only at the monument end) [V]
    const cz0 = MON.zE, zT = 0.62, cz1 = 1.30, czc = (cz0 + zT) / 2, R = 0.11;
    const tx1 = -0.03;   // QA w2: over the whole O footwell mouth (tpg_53) [D]
    planSlab(B, planRRect(-0.58, tx1, cz0, zT, [0.004, 0.004, R, 0.004]), top - 0.035, 0.033, SEATMAT.jShellIn);
    planSlab(B, planRRect(-0.579, tx1 - 0.001, cz0, zT - 0.001, [0.004, 0.004, R - 0.001, 0.004]), top - 0.006, 0.004, SEATMAT.jRail);
    planSlab(B, planRRect(-0.558, tx1 - 0.022, cz0 + 0.004, zT - 0.022, [0.004, 0.004, R - 0.022, 0.004]), top - 0.004, 0.005, ash);
    planSlab(B, planRRect(-0.576, tx1, cz0, zT - 0.004, [0.004, 0.004, R - 0.004, 0.004]), top - 0.041, 0.006, SEATMAT.jRail);
    planSlab(B, planBand(-tx1 + 0.012, 0.572, -zT + 0.012, -cz0, R - 0.012, 0.02).map(([x, z]) => [-x, -z]), 0, top - 0.041, shell);
    B.add(gRBox(0.45, CON.top, cz1 - zT, 0.01, 1), M4.trs(-0.355, CON.top / 2, (zT + cz1) / 2), shell);
    capRail(B, 0.45, cz1 - zT, -0.355, CON.top, (zT + cz1) / 2);
    if (!lod) {
      B.add(gRBox(0.006, 0.05, 0.02, 0.003, 1), M4.trs(-0.1285, 0.45, 1.08), { c: '#b3262a', r: 0.5 });   // life-vest tab (red, c_27302)
      B.add(gRBox(0.004, 0.14, 0.30, 0.004, 1), M4.trs(-0.129, 0.40, 0.95), SEATMAT.jShellIn);           // stowage lid
      roomControls(B, M4.trs(-0.13, -0.10, 0.78, Math.PI / 2), -1);
    }
    // E's face of the monument: E's cabinet (outer column) + E's monitor (aisle column); mouth of E's footwell below
    roomCabinet(B, -0.325, MON.zE, 1);
    roomMonitor(B, 0.15, MON.zE, 1, -1);
    roomWing(B, 0.4475, 0.535, MON.zE, 1, MON.bot, 0.20, 1.0);
    // E's sliding door parked in the monitor monument; leading edge faces aft toward E's entry
    doorEdge(B, 0.56, 0.06, wall - 0.14);
    if (bed) {
      B.add(gLoft(cushionSecs(0.58, 1.80, 0.05, -0.02, { edge: 0.02, r: 0.03, crown: 0.004 }), 3), M4.trs(0.24, ROOM.bed + 0.02, 0.38), SEATMAT.mattress);
      roomDuvet(B, 0.24, 0.20, 0.54, 1.35);
      B.add(gLoft(cushionSecs(0.46, 0.30, 0.12, -0.06, { edge: 0.05, r: 0.05 }), 3), M4.trs(0.30, ROOM.bed + 0.08, 1.08), SEATMAT.pillow);
      roomPillow(B, M4.trs(0.06, ROOM.bed + 0.075, 1.02, 0, -0.1));
    } else {
      roomBundle(B, 0.10, 0.92);
      B.add(gLoft(cushionSecs(0.48, 0.32, 0.10, -0.05, { edge: 0.04, r: 0.04 }), 3), M4.mul(M4.trs(0.04, 0.60, 1.08), M4.trs(0, 0, 0, -0.30, -72 * DEG)), SEATMAT.pillow);
      roomPillow(B, M4.mul(M4.trs(0.10, 0.575, 1.00), M4.trs(0, 0, 0, -0.25, -70 * DEG)));
    }
    B.add(gRBox(0.025, top, 1.33, 0.01, 1), M4.trs(-0.572, top / 2, 0.69), shell);
    capRail(B, 0.025, 1.33, -0.572, top, 0.69);
  }
  return B.build();
}
function roomPartFar(part) {
  const B = new Builder();
  const { top, wall } = ROOM;
  if (part === 'O') {
    B.add(gBox(1.17, wall, 0.07), M4.trs(0, wall / 2, -1.31), SEATMAT.jShell);
    B.add(gRBox(0.84, 0.45, 0.6, 0.03, 1), M4.trs(-0.075, 0.225, -0.95), SEATMAT.jFabric);
    B.add(gRBox(0.82, 0.6, 0.12, 0.04, 1), M4.mul(M4.trs(-0.075, 0.43, -1.2, Math.PI), M4.trs(0, 0.3, 0, 0, 17 * DEG)), SEATMAT.jFabric);
    B.add(gBox(0.24, top, 0.54), M4.trs(0.465, top / 2, -1.07), SEATMAT.jShell);
    B.add(gBox(0.085, CON.top, 1.065), M4.trs(-0.5425, CON.top / 2, -0.7425), SEATMAT.jShell);
    B.add(gBox(0.04, wall, 0.655), M4.trs(0.565, wall / 2, -0.2925), SEATMAT.ash);
    B.add(gBox(0.55, top, 0.41), M4.trs(0.275, top / 2, -0.415), SEATMAT.jShell);
    B.add(gBox(1.13, MON.top, MON.zE - MON.zO), M4.trs(-0.02, MON.top / 2, (MON.zO + MON.zE) / 2), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(-0.20, 0.85, MON.zO - 0.002, Math.PI), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.34, 0.43, 0.01), M4.trs(0.275, top + 0.215, MON.zO - 0.004), SEATMAT.ash);
  } else {
    B.add(gBox(0.69, wall, 0.07), M4.trs(0.235, wall / 2, 1.31), SEATMAT.jShell);
    B.add(gRBox(0.58, 0.45, 0.6, 0.03, 1), M4.trs(0.2, 0.225, 0.95), SEATMAT.jFabric);
    B.add(gRBox(0.58, 0.6, 0.12, 0.04, 1), M4.mul(M4.trs(0.2, 0.43, 1.2), M4.trs(0, 0.3, 0, 0, 17 * DEG)), SEATMAT.jFabric);
    B.add(gBox(0.45, top, 0.585), M4.trs(-0.355, top / 2, 0.3275), SEATMAT.jShell);
    B.add(gBox(0.45, CON.top, 0.68), M4.trs(-0.355, CON.top / 2, 0.96), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(0.15, 0.85, MON.zE + 0.002), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.34, 0.43, 0.01), M4.trs(-0.325, top + 0.215, MON.zE + 0.004), SEATMAT.ash);
  }
  return B.build();
}
// centre dividers of a pair (between E/F rear-facing seats and between the D/G consoles)
function roomDivider() {
  // centreline wall between the E/F (D/G) seats: dark lower band with stowage + red life-vest tab, pale ash upper band,
  // charcoal cap rail; the upper band on the aft half is the retractable privacy divider (c_27313 / c_27314)
  const B = new Builder();
  B.add(gRBox(0.05, 0.66, 2.62, 0.012, 1), M4.trs(0, 0.33, 0.0), SEATMAT.jShell);
  B.add(gRBox(0.036, 0.40, 1.30, 0.012, 1), M4.trs(0, 0.86, -0.66), SEATMAT.ash);
  B.add(gRBox(0.036, 0.36, 1.26, 0.012, 1), M4.trs(0, 0.84, 0.68), SEATMAT.ash);
  for (const z of [-0.66, 0.68]) B.add(gRBox(0.06, 0.035, 1.26, 0.012, 2), M4.trs(0, 0.675, z), SEATMAT.jRail);
  for (const z of [-1.30, -0.02, 0.06, 1.30]) B.add(gRBox(0.05, 0.40, 0.03, 0.008, 1), M4.trs(0, 0.86, z), SEATMAT.jShell);
  B.add(gRBox(0.056, 0.02, 2.6, 0.006, 1), M4.trs(0, 1.07, 0.0), SEATMAT.jCap);
  // (QA w1: the stowage doors + red tabs now sit on the O units' outer consoles either side of this wall)
  return B.build();
}
