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
  jPillowBack: { c: '#4e4847', r: 0.75, l: LAYER.fabric },   // w12b: dark grey-taupe piping (kn_17, tpg_81; rendered 0.89 of the white pillow); w8a/b: warm neutral grey flange (omaat_room_15, blue-cast #595b7e -> neutral) [V]
  jPanelEdge: { c: '#5d6166', r: 0.34, m: 0.5, l: LAYER.brushed },
  jLedge: { c: '#8f959c', r: 0.3, m: 0.6, l: LAYER.brushed },   // ledge top, darker than the edge trim (c_27313 #788087-#b2bbc8) [V]
  jSill: { c: '#8e9399', r: 0.35, m: 0.4, l: LAYER.brushed },   // silver-grey sill + drawer under the monitor (tpg_53) [V]
  jLens: { c: '#55585d', r: 0.25 },   // reading-lamp lens, switched off (c_27315 / 27316 lamps read dark grey) [V]
  jBand: { c: '#656b73', r: 0.4, l: LAYER.leather },
  // w13a: the aisle-end posts and door leaves read pale, nearly plain cream (c_27312 (205,201,190), c_27314 (226,227,223),
  // tpg_60), the cabinets and table inlays darker greige (SEATMAT.ash) [V]
  ashDoor: { c: '#ece7dc', r: 0.36, l: LAYER.ashDoor },   // w14a: own layer, faint grain   // w6a: header band 0.9-1.35x the fabric, a touch darker than the flap (tpg_42, c_27313) [V]
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
  // QA w4: one continuous sofa - the back rolls into the cushion (fabric fillet) with soft grooves across its lower
  // half (c_27315, c_27313, tpg_31) [V]; room w5b: two, at 57 % / 80 % down (tpg_42) [V]
  for (const sy of [0.11, 0.235]) B.add(gRBox(w - 0.04, 0.008, 0.004, 0.002, 1), M4.mul(BH, M4.trs(0, sy, -0.0385)), SEATMAT.jSeam);
  // w7: the back is a pad with a fine piped seam ~1.5 cm in from its top and sides (tpg_42, c_27313) [V]
  B.add(gRBox(w - 0.05, 0.005, 0.005, 0.002, 1), M4.mul(BH, M4.trs(0, 0.525, -0.038)), SEATMAT.jSeam);
  for (const s of [-1, 1]) B.add(gRBox(0.005, 0.50, 0.005, 0.002, 1), M4.mul(BH, M4.trs(s * (w / 2 - 0.025), 0.275, -0.038)), SEATMAT.jSeam);
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
  // w11a: in the cushion's tilted frame, just proud of its top (was buried at y 0.433 - c_27313/15/16, omaat_room_15) [V]
  const CU = M4.trs(0, 0.39, -0.34, 0, 2 * DEG);
  // w12/w15: near-black slate-teal webbing (kn_17 #213342) to the seat crease, buckle at its front end clear of the bundle (kn_17 #213342, c_27313) [V]
  B.add(gBox(0.045, 0.004, 0.54), M4.mul(CU, M4.trs(0.15, 0.047, 0.04, -0.45)), { c: '#243440', r: 0.8, l: LAYER.fabric });
  // w14a: chrome buckle ~7 x 5 cm with its lift lever, the latch tongue + webbing stub on the open cushion (kn_17, tpg_46) [V]
  const BK = M4.mul(CU, M4.trs(0.25, 0.051, -0.17, -0.45)), CH = { c: '#dde1e5', r: 0.08, m: 1 };
  B.add(gRBox(0.05, 0.014, 0.07, 0.006, 1), BK, CH);
  B.add(gRBox(0.034, 0.006, 0.036, 0.004, 1), M4.mul(BK, M4.trs(0, 0.009, -0.008, 0, -4 * DEG)), { c: '#aeb3b8', r: 0.2, m: 0.9 });   // lift lever
  B.add(gBox(0.045, 0.004, 0.10), M4.mul(CU, M4.trs(0.34, 0.047, -0.17, 0.3)), { c: '#243440', r: 0.8, l: LAYER.fabric });
  B.add(gRBox(0.032, 0.006, 0.05, 0.003, 1), M4.mul(CU, M4.trs(0.32, 0.050, -0.10, 0.3)), CH);   // latch tongue
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
  B.add(gRBox(0.046, h - 0.06, 0.006, 0.004, 1), M4.trs(x, 0.14 + h / 2, z + 0.021), SEATMAT.ashDoor);
  B.add(gRBox(0.012, 0.16, 0.02, 0.005, 1), M4.trs(x - 0.02, 0.86, z + 0.025), SEATMAT.jBase);
  B.add(gBox(0.046, 0.004, 0.044), M4.trs(x, 0.142, z), SEATMAT.jRail);                          // silver leaf bottom edge
}
// closed sliding door across the entry, z0..z1 at the aisle (x 0.545-0.585), leading edge at zl: aisle face an ash panel
// in a charcoal frame like the aisle-end panels, seat face charcoal, silver bottom edge, top level with the aisle-end cap
// (door height = the monument end, c_27312 / c_27313 [D]; closed doors: user toggle, geometry [A])
function roomDoorClosed(B, z0, z1, zl) {
  const h = ROOM.wall - 0.14, zc = (z0 + z1) / 2, L = z1 - z0;
  B.add(gRBox(0.04, h, L, 0.012, 1), M4.trs(0.565, 0.14 + h / 2, zc), SEATMAT.jShell);
  B.add(gRBox(0.006, h - 0.07, L - 0.05, 0.003, 1), M4.trs(0.585, 0.14 + h / 2, zc), SEATMAT.ashDoor);
  B.add(gBox(0.04, 0.004, L), M4.trs(0.565, 0.142, zc), SEATMAT.jRail);
  B.add(gRBox(0.012, 0.16, 0.02, 0.005, 1), M4.trs(0.537, 0.86, zl - Math.sign(zl - zc) * 0.04), SEATMAT.jBase);   // finger pull
}
// raised pop-up privacy panel out of the armrest ledge slot (x = slot centre): charcoal panel with the grey-metal top edge,
// ~0.40 up to just under the shell cap (retracted edge omaat_room_13 [V]; raised height [A])
function roomPopUp(B, xg, z, L) {
  B.add(gRBox(0.012, 0.40, L - 0.02, 0.004, 1), M4.trs(xg, ROOM.top + 0.225, z), SEATMAT.jShellIn);
  B.add(gRBox(0.016, 0.012, L - 0.02, 0.005, 1), M4.trs(xg, ROOM.top + 0.428, z), SEATMAT.jPanelEdge);
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
  B.add(gRBox(0.595, 0.405, 0.03, 0.015, 1), M4.trs(xm, 0.8725, zo(0.015)), SEATMAT.jBezel);   // w7/w8b: frame up to 1.075 level with the cabinet, borders 5.3 top / 4.7 bottom (tpg_53)
  B.add(gQuad(0.531, 0.299), M4.trs(xm, 0.8725, zo(0.032), ry), SEATMAT.screen, atlasUV('screen'));
  const x0 = xm - slotSide * 0.2975, sc = x0 + slotSide * 0.245, y = 0.625;
  B.add(gRBox(0.49, 0.084, 0.03, 0.006, 1), M4.trs(sc, y, zo(0.01)), SEATMAT.jSill);
  const dx = x0 + slotSide * 0.145, lx = x0 + slotSide * 0.38;
  B.add(gRBox(0.27, 0.06, 0.008, 0.004, 1), M4.trs(dx, y, zo(0.027)), SEATMAT.jSill);                    // drawer face
  B.add(gBox(0.002, 0.058, 0.004), M4.trs(dx + slotSide * 0.136, y, zo(0.026)), SEATMAT.jBase);        // drawer gap
  B.add(gBox(0.09, 0.005, 0.004), M4.trs(dx, y + 0.012, zo(0.031)), SEATMAT.jShellIn);                   // pull lip
  B.add(gCyl(0.003, 0.003, 0.004, 8), M4.mul(M4.trs(dx + slotSide * 0.07, y - 0.005, zo(0.032)), M4.trs(0, 0, 0, 0, Math.PI / 2)), SEATMAT.ledG);
  // literature slot: recess glowing soft blue from inside, the sill forms its lip (tpg_53, omaat_room_14 / 16)
  B.add(gBox(0.19, 0.05, 0.004), M4.trs(lx, y - 0.004, zo(0.0255)), SEATMAT.jVoid);
  B.add(gQuad(0.18, 0.04), M4.trs(lx, y - 0.006, zo(0.028), ry), { c: '#0e1330', r: 0.7 });   // QA w3/w6b: unlit dark navy, far darker than the drawer (tpg_53 ~0.13x) [V]
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
  B.add(gRBox(0.008, 0.52, z1 - z0 - 0.02, 0.003, 1), M4.trs(px + 0.002, 0.36, (z0 + z1) / 2), SEATMAT.ashDoor);
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
function roomLedge(B, w, x, z, L, up = false) {
  const y = ROOM.top;
  const xg = x + w / 2 - 0.05;
  B.add(gRBox(w - 0.03, 0.03, L + 0.02, 0.012, 1), M4.trs(x - 0.015, y + 0.01, z), SEATMAT.jLedge);
  for (const e of [-1, 1]) for (let k = 0; k < 3; k++) B.add(gBox(w - 0.03, 0.008, 0.006), M4.trs(x - 0.015, y - 0.012 - k * 0.018, z + e * (L / 2 + 0.013)), SEATMAT.jRail);
  B.add(gRBox(0.03, 0.03, L + 0.02, 0.008, 1), M4.trs(x + w / 2 - 0.015, y + 0.004, z), SEATMAT.jRail);
  B.add(gBox(0.03, 0.008, L), M4.trs(xg, y + 0.023, z), SEATMAT.jVoid);
  if (up) roomPopUp(B, xg, z, L); else B.add(gBox(0.012, 0.004, L - 0.02), M4.trs(xg, y + 0.026, z), SEATMAT.jPanelEdge);
}

// Central monument of a pair between z = MON.zO (O's face, looking -z at O) and MON.zE (E's face, +z): O's monitor
// (outer column) back to back with E's cabinet, O's cabinet (aisle column) back to back with E's monitor; both footwells
// run under it (omaat_room_14 / 16, c_27316: cabinet flush beside the monitor frame, footwell mouth under the monitor)
const MON = { zO: -0.21, zE: 0.035, top: 1.09, bot: 0.555 };   // QA w2: top raised to clear the 0.43 cabinet; w7: level with the cabinet top, no charcoal strip over the monitor (tpg_53) [V]
const CON = { top: 0.60 };   // outer console top (c_27316 / 27303: ~0.17 above the cushion) [A]
// QA w1 pillow: flat piped rectangle ~0.44 x 0.34 x 0.07, navy check jacquard face, grey-taupe reverse panel + piping
// (c_27303, omaat_room_13) [V]
// boarding bundle under the pillows (tpg_31 / tpg_42, w7: restored from 5a42e29): a folded white mattress pad with the
// royal-blue duvet folded on it, a pillow's footprint, each in clear plastic - glossy, the duvet read paler through the film
// (tpg_42 pad #d1ccbf, duvet band #6675ba vs pillow #3b55a9; layers ~0.04 each, duvet inset ~0.02) [V]; the blue slipper
// pack in its bag beside it (tpg_42 #0a4db9, tpg_31) [V] on side ps; dir = +1 when the seat faces +z (O)
function roomBundle(B, x, z, dir, ps) {
  B.add(gRBox(0.46, 0.042, 0.31, 0.016, 1), M4.trs(x, 0.452, z), { c: '#e2ded4', r: 0.3 });
  B.add(gRBox(0.43, 0.034, 0.28, 0.014, 1), M4.trs(x + 0.005, 0.49, z - dir * 0.012), { c: '#3d4688', r: 0.5 });   // w14a: matte, darker (kn_17 0.41/0.49/0.76); w13a: duvet tone through the glossy film (kn_17 0.46/0.53/0.71 of the white pillow; was a pale lilac slab) [V]
  B.add(gRBox(0.452, 0.002, 0.29, 0.001, 1), M4.trs(x, 0.4735, z + dir * 0.003), { c: '#eef0f2', r: 0.15 });   // pad fold seam under the film
  // w14a: the clear film shows as a few glossy pale crease glints over the duvet (kn_17) [V]
  for (const [dx, dz, a, L] of [[-0.12, -0.06, 0.5, 0.16], [0.08, 0.07, -0.3, 0.2], [0.15, -0.09, 1.1, 0.10]]) B.add(gBox(0.006, 0.0015, L), M4.trs(x + dx, 0.5075, z + dz, a), { c: '#c9cde0', r: 0.08 });
  // w7: slipper pack beside the bundle; w13: white slippers in clear film, a grey sole line (kn_17, tpg_76) [V]
  const P = M4.trs(x + ps * 0.29, 0.444, z + dir * 0.03, ps * 0.5);
  B.add(gLoft(cushionSecs(0.11, 0.19, 0.024, 0, { edge: 0.011, r: 0.03, crown: 0.004 }), 3), M4.mul(P, M4.trs(0, -0.011, 0)), { c: '#dddbd5', r: 0.35 });   // w13: white slippers in clear film (kn_17 2021, tpg_76 2020; navy pouch only in omaat_room_15) [V]
  B.add(gRBox(0.10, 0.008, 0.05, 0.004, 1), M4.mul(P, M4.trs(0, 0.012, 0.06)), { c: '#b9b6ae', r: 0.6 });
}
// w7 pillows (omaat_room_15, tpg_31 / 42): plump, ~0.44 x 0.34 x 0.10; the blue one a royal-blue check jacquard with a
// ~15 mm grey flange round its seam [V]; the white one the same size behind it [V]
function roomPillow(B, xf, mat = SEATMAT.pillowBlue) {
  const half = cushionSecs(0.44, 0.34, 0.05, 0, { edge: 0.035, r: 0.025, crown: 0.012 });
  B.add(gLoft(half, 3), xf, mat);
  B.add(gLoft(half, 3), M4.mul(xf, M4.trs(0, 0, 0, 0, Math.PI)), mat);
  // w8a: the flange follows the pillow outline, neutral grey (omaat_room_15) [V]
  if (mat === SEATMAT.pillowBlue) B.add(gLoft(cushionSecs(0.458, 0.358, 0.008, -0.004, { edge: 0.002, r: 0.03, crown: 0 }), 3), xf, SEATMAT.jPillowBack);
}
// QA w2 duvet: indigo comforter open over the bed from below the pillow to the foot (fb_a96b7a65 #4b5789, fb_d8b6dc0d
// #606ea0 daylight) [V]; white pillow + the blue one leaning on it (fb_a96b7a65) [V]
// w7: a draped cloth sheet, no longer a slab with stitch lines (w6a/b: stiff slab, z-fighting stitches): a height field
// over the mattress with soft diagonal folds 2-4 cm high, a turned-down head fold, the aisle edge rolling over the mattress
// edge and hanging ~6 cm, the white pad showing at the outer side and the foot (tpg_72 / 74 / 75, fb_a96b7a65) [V]/[A]
const DUVET_FOLDS = [[-0.10, -0.30, 35, 0.60, 0.04, 0.05], [0.12, 0.05, -30, 0.50, 0.034, 0.04], [-0.06, 0.32, 62, 0.45, 0.03, 0.04],
  [0.18, -0.45, 12, 0.32, 0.024, 0.035], [-0.20, 0.0, 80, 0.38, 0.022, 0.035], [0.05, -0.12, -70, 0.28, -0.012, 0.05],
  [0.22, 0.42, -45, 0.30, 0.02, 0.03], [-0.15, 0.55, 20, 0.25, 0.016, 0.03]];
// bounds(z) -> [xl, xr, mr]: cloth edges and the mattress edge it rolls over (xr > mr); z0..z1 in unit coordinates, head
// at z0 (hd = 1) or z1 (hd = -1); folds placed about (xc, zc). Height 0 = the cloth's top resting on the mattress.
function duvetSheet(bounds, z0, z1, hd, xc, foldK = 1, nu = 36, nv = 64, wob = 1, zf = null) {
  const rho = 0.025, t = 0.035,   // w12: 3-4 cm thick edges (tpg_81) [V]
    zc = (z0 + z1) / 2, k = (z1 - z0) / 1.23;
  const fold = (x, z, xl, mr) => {
    let f = 0;
    for (const [cx, cz, a, len, A, sg] of DUVET_FOLDS) {
      const c = Math.cos(a * DEG), sn = Math.sin(a * DEG), dx = x - xc - cx, dz = (z - zc) - hd * cz * k;
      const par = dx * sn + dz * c, per = dx * c - dz * sn;
      f += 0.5 * foldK * A * Math.exp(-((per / sg) ** 2)) * Math.exp(-((par / (len / 2)) ** 4));   // w9a: folds halved so the quilt reads
    }
    if (zf !== null) f *= 1 - smooth(zf - 0.15, zf + 0.05, hd * (z - zf) + zf);   // w12a: no folds squeezed into the footwell taper
    const zh = hd > 0 ? z - z0 : z1 - z;   // turned-down head fold: a doubled band with a soft roll at its edge
    f += 0.012 * (1 - smooth(0.11, 0.15, zh)) + 0.008 * Math.exp(-(((zh - 0.135) / 0.018) ** 2));
    // w8a: a quilted comforter - lofted ~1.5 cm away from its edges, stitched on a ~0.33 m grid (tpg_70 / 72) [V]
    const e = smooth(0, 0.09, Math.min(x - xl, mr - x) + 0.01), q = 0.33, gx = x - xc + (hd > 0 ? 0.02 : 0.07),   // w11b: O grid phased so a seam crosses the sheet
      gz = z - z0 - 0.02;
    const dq = Math.min(Math.abs(gx - q * Math.round(gx / q)), Math.abs(gz - q * Math.round(gz / q)));
    return f * smooth(0, 0.05, Math.min(x - xl, mr - x) + 0.01) + e * (0.024 - 0.020 * Math.exp(-((dq / 0.034) ** 2)));   // w12b: dip wider than ~2 grid cells (no diagonal ripples)
  };
  const at = (u, v) => {   // u, v in [0, 1] -> point on the cloth's top
    const z = lerp(z0, z1, v), [xl0, xr, mr] = bounds(z), xl = xl0 + wob * (0.006 * Math.sin(5.5 * z + 0.7) + 0.002 * Math.sin(17 * z));   // w12: a long low wave, not a pie-crust (tpg_81) [V]
    const xp = lerp(xl, xr, u), d = xp - mr;
    if (d <= 0) return [xp, fold(xp, z, xl, mr), z];
    const s = Math.min(d, rho * Math.PI / 2), th = s / rho;
    return [mr + rho * Math.sin(th), -rho * (1 - Math.cos(th)) - (d - s), z];
  };
  const g = raw(), P = [];
  for (let j = 0; j <= nv; j++) for (let i = 0; i <= nu; i++) {
    const p = at(i / nu, j / nv); P.push(p); g.p.push(...p); g.u.push(i / nu * 1.2, j / nv * 2.2);
  }
  for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) { const a = j * (nu + 1) + i, b = a + 1, c = a + nu + 1, d = c + 1; g.i.push(a, c, b, b, c, d); }
  computeNormals(g);
  if (g.n[((nv >> 1) * (nu + 1) + (nu >> 1)) * 3 + 1] < 0) { for (let q = 0; q < g.n.length; q++) g.n[q] = -g.n[q]; for (let q = 0; q < g.i.length; q += 3) { const m = g.i[q + 1]; g.i[q + 1] = g.i[q + 2]; g.i[q + 2] = m; } }
  // thickness skirt round the border, down to the mattress (normals: outward in the cloth plane)
  const S = raw(), ring = [];
  for (let i = 0; i <= nu; i++) ring.push([i, 0, [0, 0, -1]]);
  for (let j = 1; j <= nv; j++) ring.push([nu, j, [1, 0, 0]]);
  for (let i = nu - 1; i >= 0; i--) ring.push([i, nv, [0, 0, 1]]);
  for (let j = nv - 1; j >= 1; j--) ring.push([0, j, [-1, 0, 0]]);
  ring.push(ring[0]);
  for (let q = 0; q < ring.length - 1; q++) {
    const b0 = S.p.length / 3;
    for (const [i, j, nn] of [ring[q], ring[q + 1]]) {
      const p = P[j * (nu + 1) + i], hang = p[1] < -0.01, n = hang ? [0, -1, 0] : nn, lo = hang ? 0.004 : t;   // a hanging edge: its bottom faces down
      S.p.push(p[0], p[1], p[2], p[0], p[1] - lo, p[2]); S.n.push(...n, ...n); S.u.push(0, 0, 0, 0.02);
    }
    S.i.push(b0, b0 + 1, b0 + 2, b0 + 2, b0 + 1, b0 + 3);
  }
  fixWinding(S);
  return [g, S];
}
// footwell wedge edges at z (as footwellPlan): [x at the outer wall, x at the inboard edge]
function footwellEdges(x0, x1, zm, zf, wall, z, inset) {
  const t = clamp((z - zm) / (zf - zm), 0, 1), w = lerp(x1 - x0, 0.30, t) + 0.04 * Math.sin(Math.PI * t) - 2 * inset;
  return wall < 0 ? [x0 + inset, x0 + inset + w] : [x1 - inset - w, x1 - inset];
}
// bed: mattress pad over the seat, beside the side table and into the footwell wedge, duvet over it (w7: the w6 bed was one
// rectangle running through the side-table wall and into the neighbour's legroom; fb_a96b7a65 / tpg_72 show the bed
// narrowing past the table into the footwell) [V]/[D]
const MAT_TOP = 0.054;   // mattress top above ROOM.bed
function roomBed(B, part) {
  const y = ROOM.bed, M = SEATMAT.mattress, mat = (x0, x1, z0, z1, dy = 0) => B.add(gLoft(cushionSecs(x1 - x0, z1 - z0, 0.05, -0.02, { edge: 0.02, r: 0.02, crown: 0.004 }), 3), M4.trs((x0 + x1) / 2, y + 0.02 + dy, (z0 + z1) / 2), M);
  const fw = part === 'O' ? [-0.505, -0.03, MON.zO, 0.585, -1] : [0.0, 0.44, MON.zE, -0.585, 1];
  planSlab(B, footwellPlan(fw[0], fw[1], fw[2], fw[3], fw[4], 0.022), 0.44, y + MAT_TOP - 0.44, M);
  let bounds, z0, z1, hd, xc;
  if (part === 'O') {
    mat(-0.475, 0.285, -1.28, -0.62); mat(-0.475, -0.032, -0.64, MON.zO - 0.005, -0.002);
    // aisle edge rolls over the mattress beside the seat; beside the table it ends at the console wall; then the footwell
    bounds = (z) => {
      const [fl, fr] = footwellEdges(fw[0], fw[1], fw[2], fw[3], -1, z, 0.02), a = smooth(-0.68, -0.57, z), b = smooth(MON.zO - 0.06, MON.zO + 0.06, z);   // w13b: wide over the whole wide bed up to the table corner (tpg_81) [V]
      const mr = lerp(lerp(0.285, -0.012, a), fr + 0.01, b);
      return [lerp(-0.455, fl, b), lerp(lerp(0.25, -0.03, a), fr, b), mr];   // w12: laid wide over the pad (tpg_81) [V]
    };
    z0 = -0.90; z1 = 0.55; hd = 1; xc = -0.12;
  } else {
    mat(-0.035, 0.495, MON.zE - 0.02, 0.63); mat(-0.118, 0.495, 0.62, 1.28, -0.002);   // w8b: full seat width aft of the table (r10) [D]
    bounds = (z) => {
      const [fl, fr] = footwellEdges(fw[0], fw[1], fw[2], fw[3], 1, z, 0.02), b = 1 - smooth(MON.zE - 0.04, MON.zE + 0.04, z);
      return [lerp(0.02, fl, b), lerp(0.47, fr, b), lerp(0.49, fr + 0.01, b)];
    };
    z0 = -0.535; z1 = 0.86; hd = -1; xc = 0.22;
  }
  const O = part === 'O';
  for (const g of duvetSheet(bounds, z0, z1, hd, xc, O ? 0.45 : 1, O ? 54 : 36, 64, O ? 0.5 : 1, O ? MON.zO : null)) B.add(g, M4.trs(0, y + MAT_TOP + 0.02, 0), SEATMAT.duvet);
}
function roomPart(part, opts = {}) {
  const B = new Builder();
  const bed = !!opts.bed, lod = !!opts.lod, doors = !!opts.doors;   // doors: sliding door + pop-up panel closed (seat-card toggle)
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
    B.add(gRBox(0.95, 0.155, 0.05, 0.02, 1), M4.trs(-0.07, 1.0425, -1.25), SEATMAT.jBand);   // padded header band over the seat only, charcoal aisle post beyond (w5b: tpg_42) [V]
    capRail(B, 1.17, 0.07, 0, wall, -1.31);
    roomLamp(B, -0.515, -1.225, 1);
    roomLamp(B, 0.375, -1.225, 1);
    // narrow aisle armrest (~0.24) along the seat, LOW ledge (0.66) holding the retracted pop-up privacy panel, stowage
    // pocket on its seat-facing side (tpg_31 / 42, c_27313) [V]
    B.add(gRBox(hx - ax0, top, az1 + 1.34, 0.02, 1), M4.trs((ax0 + hx) / 2, top / 2, (az1 - 1.34) / 2), shell);
    roomLedge(B, hx - ax0, (ax0 + hx) / 2, (az1 - 1.34) / 2, az1 + 1.32, doors);
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
    B.add(gRBox(0.04, wall, ez1 - ez0, 0.012, 1), M4.trs(0.565, wall / 2, ezc), SEATMAT.ashDoor);
    B.add(gRBox(0.045, 0.10, ez1 - ez0, 0.01, 1), M4.trs(0.565, 0.05, ezc), shell);
    ashFrameX(B, 0.565, 0.04, 0.10, wall, ez0, ez1);
    // shared aisle-end cap: mid grey, a little darker than the plaques, oval finger recess between them (c_27314)
    B.add(gRBox(0.10, 0.02, ez1 - ez0 + 0.006, 0.006, 1), M4.trs(0.54, wall + 0.01, ezc), { c: '#6c6e71', r: 0.28, m: 0.35, l: LAYER.brushed });   // QA w3: slight metallic sheen (tpg_78); w11b: cap/ash 0.58 (c_27313), was 0.92
    if (!lod) B.add(gCyl(1, 1, 1, 16), M4.trs(0.545, wall + 0.0205, (MON.zO + MON.zE) / 2, 0, 0, 0, 0.0175, 0.003, 0.035), SEATMAT.jShellIn);   // QA w3: was a black hole
    // E's footwell under the table + monument (aisle column), mouth under E's monitor
    // QA w2: both footwell mouths sit square under their monitors, ~0.475 wide from the column-side frame edge, split by a
    // thin 0.05 pillar (tpg_53: opening under the monitor, 0.475 m) [D]
    B.add(gRBox(0.44, 0.02, MON.zO - tz0 - 0.03, 0.006, 1), M4.trs(0.22, 0.57, (MON.zO + tz0 + 0.03) / 2), SEATMAT.jShellIn);
    roomFootwell(B, 0.0, 0.44, MON.zE, tz0 + 0.035, 1);   // w5b: wing wall now reaches the floor at x 0.4475; pillar thinned to 0.03 [D]
    // sliding door parked in the monument; its leading edge (ash face, charcoal frame, finger pull) faces aft
    if (doors) roomDoorClosed(B, az1, -0.58, az1); else doorEdge(B, 0.56, -0.60, wall - 0.14);
    // central monument body (both columns) + the pillar between the two footwell mouths
    B.add(gRBox(1.13, MON.top - MON.bot, MON.zE - MON.zO, 0.01, 1), M4.trs(-0.02, (MON.top + MON.bot) / 2, (MON.zO + MON.zE) / 2), shell);
    B.add(gRBox(0.03, MON.bot, MON.zE - MON.zO, 0.01, 1), M4.trs(-0.015, MON.bot / 2, (MON.zO + MON.zE) / 2), shell);
    // w9a/b: the top reads as an O housing and an E housing split by a slim spine with a metal top rail running inboard
    // from the aisle-end cap between the seat plaques (c_27313 / 27314) [V]: dark grooves either side of a 0.03 spine [D]
    const mz = (MON.zO + MON.zE) / 2, MX = { c: '#9aa0a7', r: 0.3, m: 0.6, l: LAYER.brushed };   // c_27313 top metal #969b9e [V]
    // w10b: the spine stops at the aisle cap (x 0.49) so it meets the cap between the two plaques, no stub over them
    for (const gz of [-0.023, 0.023]) B.add(gBox(1.03, 0.004, 0.010), M4.trs(-0.035, MON.top + 0.0005, mz + gz), SEATMAT.jVoid);
    B.add(gRBox(1.045, 0.04, 0.028, 0.008, 1), M4.trs(-0.0325, MON.top + 0.02, mz), shell);   // w11b: clear of the centreline fins inboard
    B.add(gRBox(1.049, 0.006, 0.032, 0.003, 1), M4.trs(-0.0325, MON.top + 0.043, mz), MX);
  B.add(gRBox(0.05, 0.03, 0.07, 0.012, 1), M4.trs(0.47, MON.top + 0.035, mz), shell);   // w12: flared T into the aisle cap (c_27313) [V]
    // w10a: light grey-metal edges along the housing tops on both faces (c_27313 / 27315) [V]
    for (const ez of [MON.zO + 0.008, MON.zE - 0.008]) B.add(gBox(1.10, 0.004, 0.016), M4.trs(-0.035, MON.top + 0.0005, ez), MX);
    // O's face: monitor (outer column) + O's cabinet (aisle column)
    roomMonitor(B, -0.20, MON.zO, -1, 1);
    roomCabinet(B, 0.275, MON.zO, -1);
    roomWing(B, -0.4975, -0.585, MON.zO, -1, CON.top, -0.075, -1.0);
    if (!lod) roomCard(B, -0.4995, 1, 0.36, -0.33);
    // O's footwell under E's console (outer column), mouth under O's monitor
    B.add(gRBox(0.52, 0.02, 0.585, 0.006, 1), M4.trs(-0.30, 0.57, 0.33), SEATMAT.jShellIn);
    roomFootwell(B, -0.505, -0.03, MON.zO, 0.585, -1);   // w9b: ends at E's table end, not through its walls
    if (bed) {
      // the bed narrows to ~0.62 past the seat into the footwell; mattress + duvet follow the seat width (fb_a96b7a65) [A]
      roomBed(B, 'O');
      // w7/w8a: the white pillow propped against the back shell (~42 deg), the blue one leaning on it (tpg_72, fb_a96b7a65) [V]
      roomPillow(B, M4.mul(M4.trs(SX - 0.10, ROOM.bed + 0.19, -1.11, Math.PI), M4.trs(0, 0, 0, 0.06, -42 * DEG)), SEATMAT.pillow);
      roomPillow(B, M4.mul(M4.trs(SX - 0.04, ROOM.bed + 0.15, -0.94, Math.PI), M4.trs(0, 0, 0, -0.12, -22 * DEG)));
    } else {
      // white pillow leaning on the back with the blue one in front of it, toward the aisle half (tpg_31 / 42) [V]
      // w7: the blue pillow rests on the bundle, the white one stands behind it, its top showing (tpg_31 / 42) [V]
      roomBundle(B, 0.10, -0.80, 1, -1);   // w7: at the cushion front, toward the aisle (omaat_room_15) [V]
      roomPillow(B, M4.mul(M4.trs(0.115, 0.70, -1.00, Math.PI), M4.trs(0, 0, 0, 0.03, -72 * DEG)), SEATMAT.pillow);
      roomPillow(B, M4.mul(M4.trs(0.09, 0.665, -0.81, Math.PI), M4.trs(0, 0, 0, 0.02, -60 * DEG)));
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
    B.add(gRBox(0.69, 0.155, 0.05, 0.02, 1), M4.trs(0.235, 1.0425, 1.25), SEATMAT.jBand);        // padded header band (as O)
    capRail(B, 0.69, 0.07, 0.235, wall, 1.31);
    roomLamp(B, -0.07, 1.225, -1);
    roomLamp(B, 0.50, 1.225, -1);
    // narrow aisle armrest with the pop-up privacy panel retracted inside (ash edge flush in the cap)
    B.add(gRBox(0.09, top, 0.60, 0.02, 1), M4.trs(0.54, top / 2, 0.95), shell);
    roomLedge(B, 0.10, 0.54, 0.95, 0.60, doors);
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
    roomWing(B, 0.4475, 0.535, MON.zE, 1, 0, 0.20, 1.0);   // w5b: down to the floor as the footwell side wall (lalf_18, tpg_53) [V]
    // E's sliding door parked in the monitor monument; leading edge faces aft toward E's entry
    if (doors) roomDoorClosed(B, MON.zE, 0.65, 0.65); else doorEdge(B, 0.56, 0.06, wall - 0.14);
    B.add(gRBox(0.05, 0.14, 0.04, 0.01, 1), M4.trs(0.56, 0.07, 0.06), shell);   // w5b: kick under the parked leaf (was a floating strip)
    if (bed) {
      roomBed(B, 'E');
      roomPillow(B, M4.mul(M4.trs(0.26, ROOM.bed + 0.19, 1.11), M4.trs(0, 0, 0, -0.06, -42 * DEG)), SEATMAT.pillow);
      roomPillow(B, M4.mul(M4.trs(0.20, ROOM.bed + 0.15, 0.94), M4.trs(0, 0, 0, 0.12, -22 * DEG)));
    } else {
      roomBundle(B, 0.23, 0.80, -1, -1);
      roomPillow(B, M4.mul(M4.trs(0.265, 0.70, 1.00), M4.trs(0, 0, 0, -0.03, -72 * DEG)), SEATMAT.pillow);
      roomPillow(B, M4.mul(M4.trs(0.22, 0.665, 0.81), M4.trs(0, 0, 0, -0.02, -60 * DEG)));
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
    B.add(gBox(0.04, wall, 0.655), M4.trs(0.565, wall / 2, -0.2925), SEATMAT.ashDoor);
    B.add(gBox(0.55, top, 0.41), M4.trs(0.275, top / 2, -0.415), SEATMAT.jShell);
    B.add(gBox(1.13, MON.top, MON.zE - MON.zO), M4.trs(-0.02, MON.top / 2, (MON.zO + MON.zE) / 2), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(-0.20, 0.8725, MON.zO - 0.002, Math.PI), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.34, 0.43, 0.01), M4.trs(0.275, top + 0.215, MON.zO - 0.004), SEATMAT.ash);
  } else {
    B.add(gBox(0.69, wall, 0.07), M4.trs(0.235, wall / 2, 1.31), SEATMAT.jShell);
    B.add(gRBox(0.58, 0.45, 0.6, 0.03, 1), M4.trs(0.2, 0.225, 0.95), SEATMAT.jFabric);
    B.add(gRBox(0.58, 0.6, 0.12, 0.04, 1), M4.mul(M4.trs(0.2, 0.43, 1.2), M4.trs(0, 0.3, 0, 0, 17 * DEG)), SEATMAT.jFabric);
    B.add(gBox(0.45, top, 0.585), M4.trs(-0.355, top / 2, 0.3275), SEATMAT.jShell);
    B.add(gBox(0.45, CON.top, 0.68), M4.trs(-0.355, CON.top / 2, 0.96), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(0.15, 0.8725, MON.zE + 0.002), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.34, 0.43, 0.01), M4.trs(-0.325, top + 0.215, MON.zE + 0.004), SEATMAT.ash);
  }
  return B.build();
}
// centre dividers of a pair (between E/F rear-facing seats and between the D/G consoles)
function roomDivider() {
  // centreline wall between the E/F (D/G) seats: dark lower band to the console tops, then the privacy fins
  const B = new Builder();
  B.add(gRBox(0.05, 0.66, 2.62, 0.012, 1), M4.trs(0, 0.33, 0.0), SEATMAT.jShell);
  // w7: above the consoles the privacy divider is two slim charcoal fins with a gap, grey-metal top edges, rising to the
  // monument tops (c_27313 / 27314; w5a / w6a: was one broad ash wall) [V]; fin height ~1.10 [D]
  for (const sx of [-1, 1]) for (const z of [-0.66, 0.66]) {
    B.add(gRBox(0.018, 0.44, 1.26, 0.006, 1), M4.trs(sx * 0.024, 0.88, z), SEATMAT.jShell);
    B.add(gRBox(0.022, 0.012, 1.26, 0.005, 1), M4.trs(sx * 0.024, 1.105, z), SEATMAT.jPanelEdge);
  }
  for (const z of [-0.66, 0.66]) B.add(gRBox(0.07, 0.03, 1.26, 0.012, 2), M4.trs(0, 0.675, z), SEATMAT.jCap);
  // (QA w1: the stowage doors + red tabs now sit on the O units' outer consoles either side of this wall)
  return B.build();
}
