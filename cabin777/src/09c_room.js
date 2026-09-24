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
  jBezel: { c: '#2c2e32', r: 0.35, l: LAYER.plastic },
  jPillowBack: { c: '#6b665e', r: 0.8, l: LAYER.fabric },
  jPanelEdge: { c: '#5d6166', r: 0.34, m: 0.5, l: LAYER.brushed },
  jLens: { c: '#55585d', r: 0.25 },   // reading-lamp lens, switched off (c_27315 / 27316 lamps read dark grey) [V]
});
const ROOM = { hx: 0.585, hz: 1.359, top: 0.66, wall: 1.12, bed: 0.43 };
// seat itself (passenger faces -z, back at z = 0): upright or bed. Per c_27302/27315/27316: thin flat cushion and a flat
// upholstered back (one horizontal seam) over a dark recessed base; headrest is a slate flap hanging from the back top
// w: cushion width (O is 0.58 beside its window / centreline console, QA w1; E 0.64)
function roomSeatCore(B, bed, lod, w = 0.64) {
  const F = SEATMAT.jFabric, k = w - 0.64;
  B.add(gRBox(0.54 + k, 0.33, 0.50, 0.015, 1), M4.trs(0, 0.165, -0.36), SEATMAT.jBase);
  if (bed) {
    B.add(gLoft(cushionSecs(w, 0.66, 0.075, -0.035, { edge: 0.02, r: 0.02, crown: 0.003 }), 4), M4.trs(0, 0.39, -0.35), F);
    return;
  }
  B.add(gLoft(cushionSecs(w, 0.60, 0.075, -0.035, { edge: 0.022, r: 0.02, crown: 0.004 }), lod ? 3 : 4), M4.trs(0, 0.39, -0.34, 0, 2 * DEG), F);
  const BH = M4.trs(0, 0.43, -0.17, 0, 12 * DEG);     // top of the back leans on the shell (shell face at z = -0.005)
  loftAt(B, [SEC(0.0, w - 0.02, 0.06, 0, 0.02), SEC(0.025, w, 0.075, 0, 0.026), SEC(0.60, w, 0.075, 0, 0.026), SEC(0.625, w - 0.02, 0.06, 0.002, 0.02)], BH, F, lod ? 2 : 3);
  // flap ~0.38 x 0.28 (60 % of the back width), hanging from the back top (omaat_room_13, c_27313 / 27315) [D]
  B.add(gRBox(0.38, 0.28, 0.018, 0.008, 1), M4.mul(BH, M4.trs(0.05, 0.485, -0.052, 0, -8 * DEG)), SEATMAT.jHead);
  if (lod) return;
  B.add(gBox(w - 0.04, 0.005, 0.004), M4.mul(BH, M4.trs(0, 0.29, -0.0385)), SEATMAT.jBase);            // stitched seam
  B.add(gBox(w - 0.04, 0.005, 0.004), M4.mul(M4.trs(0, 0.39, -0.34, 0, 2 * DEG), M4.trs(0, 0.041, -0.10, 0, Math.PI / 2)), SEATMAT.jBase);
  B.add(gRBox(0.03, 0.05, 0.012, 0.004, 1), M4.mul(BH, M4.trs(0.05, 0.335, -0.05)), SEATMAT.jHead); // flap tab
  // leg rest hanging from the pan front
  B.add(gLoft([SEC(0.0, 0.56 + k, 0.045, 0, 0.015), SEC(0.30, 0.60 + k, 0.05, 0, 0.018)], 3), M4.trs(0, 0.06, -0.64, 0, -14 * DEG), F);
  // teal shoulder belt (c_27313 / 27316 show it lying on the cushion)
  B.add(gBox(0.045, 0.004, 0.34), M4.trs(-0.12, 0.433, -0.30, 0.5), { c: '#2f5f66', r: 0.7 });
  B.add(gRBox(0.05, 0.012, 0.035, 0.005, 1), M4.trs(-0.04, 0.436, -0.44), SEATMAT.buckle);
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
  B.add(gRBox(0.05, h, 0.04, 0.014, 2), M4.trs(x, 0.14 + h / 2, z), SEATMAT.jShell);
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
  planSlab(B, footwellPlan(x0, x1, zm + s * 0.04, zf - s * 0.04, wall), 0.01, 0.36, SEATMAT.jVoid);
  B.add(gRBox(x1 - x0, 0.02, 0.16, 0.006, 1), M4.trs((x0 + x1) / 2, 0.12, zm + s * 0.08), SEATMAT.jShellIn);
}
// monitor + under-strip on the central monument face (plane z = zf, facing dir): charcoal frame round the 0.531 x 0.299
// display (QA w1: 0.605 x 0.38, ~3.5 cm sides and a thicker bottom lip; frame/screen 1.14 x 1.27 in omaat_room_16) [D], blue-lit literature slot + charcoal drawer with a green LED below (omaat_room_16, c_27316) [D]
function roomMonitor(B, xm, zf, dir, slotSide) {
  const zo = (d) => zf + dir * d, ry = dir > 0 ? 0 : Math.PI;
  B.add(gRBox(0.605, 0.38, 0.03, 0.015, 1), M4.trs(xm, 0.835, zo(0.015)), SEATMAT.jBezel);
  B.add(gQuad(0.531, 0.299), M4.trs(xm, 0.85, zo(0.032), ry), SEATMAT.screen, atlasUV('screen'));
  // literature slot: dark recess glowing soft blue from inside, charcoal lip on its top edge (omaat_room_14 / 16, c_27305);
  // QA r2 was a bright flat blue quad
  const sx = xm + slotSide * 0.20;
  B.add(gRBox(0.14, 0.05, 0.03, 0.004, 1), M4.trs(sx, 0.60, zo(-0.013)), SEATMAT.jShellIn);
  B.add(gQuad(0.124, 0.036), M4.trs(sx, 0.597, zo(0.0025), ry), { c: '#2a4f9a', r: 0.5, e: 0.15 });
  B.add(gRBox(0.146, 0.005, 0.01, 0.002, 1), M4.trs(sx, 0.6225, zo(0.004)), SEATMAT.jBase);
  B.add(gRBox(0.30, 0.06, 0.012, 0.004, 1), M4.trs(xm - slotSide * 0.09, 0.60, zo(0.006)), SEATMAT.jShellIn);
  B.add(gCyl(0.003, 0.003, 0.004, 8), M4.mul(M4.trs(xm - slotSide * 0.21, 0.60, zo(0.013)), M4.trs(0, 0, 0, 0, Math.PI / 2)), SEATMAT.ledG);
}
// closed cabinet door beside the monitor on the same plane: plain ash with fine horizontal grain, 0.34 x 0.38 with its
// top level with the monitor frame top, 4 mm silver bottom trim (omaat_room_16; mirror + navy interior only when open,
// omaat_room_21) [D]
// QA r2: the door is split ~0.06 above its bottom into a lower ash band, with slim grey side stiles (c_27305 split ~0.07
// above the bottom; omaat_room_16 lower band 45 / 255 px of the cabinet height; tt_storage-3) [D]
function roomCabinet(B, xc, zf, dir) {
  const z = zf + dir * 0.004;
  B.add(gRBox(0.34, 0.31, 0.012, 0.004, 1), M4.trs(xc, ROOM.top + 0.225, z), SEATMAT.ash);
  B.add(gRBox(0.34, 0.058, 0.012, 0.004, 1), M4.trs(xc, ROOM.top + 0.035, z), SEATMAT.ash);
  B.add(gBox(0.34, 0.006, 0.008), M4.trs(xc, ROOM.top + 0.067, zf + dir * 0.002), SEATMAT.jShell);      // 4 mm split
  for (const s of [-1, 1]) B.add(gRBox(0.008, 0.38, 0.014, 0.002, 1), M4.trs(xc + s * 0.174, ROOM.top + 0.19, z), SEATMAT.jShell);
  B.add(gBox(0.34, 0.004, 0.016), M4.trs(xc, ROOM.top + 0.002, z), SEATMAT.jRail);
}
// seat controls on the console's vertical face: black button panel with a blue ring + a handset with a colour screen in
// a charcoal recess (omaat_room_16 / 18, c_27308 / 27316). xf places the pair: local x along the face, +z out of it
// QA w1: handset ~0.15 x 0.075 with a colour screen, button pod ~0.11 x 0.075 with a blue-ring button in a 2 x 4 icon
// grid (omaat_room_16: handset ~0.28 x the 0.53 m screen width; tt_seat-controls, c_27316) [D]
function roomControls(B, xf, side) {
  B.add(gRBox(0.15, 0.075, 0.01, 0.02, 1), M4.mul(xf, M4.trs(0, 0.565, 0.003)), SEATMAT.black);
  B.add(gQuad(0.075, 0.045), M4.mul(xf, M4.trs(-side * 0.02, 0.565, 0.0085)), { c: '#3a7bd5', r: 0.3, e: 0.4 });
  for (let b = 0; b < 3; b++) B.add(gRBox(0.012, 0.012, 0.003, 0.003, 1), M4.mul(xf, M4.trs(side * 0.05, 0.585 - b * 0.02, 0.009)), SEATMAT.jBezel);
  B.add(gRBox(0.11, 0.075, 0.008, 0.012, 1), M4.mul(xf, M4.trs(side * 0.16, 0.555, 0.002)), SEATMAT.black);
  B.add(gCyl(0.011, 0.011, 0.003, 14), M4.mul(xf, M4.trs(side * 0.16, 0.555, 0.0065, 0, Math.PI / 2)), { c: '#6c9cff', r: 0.4, e: 0.3 });
  B.add(gCyl(0.0075, 0.0075, 0.004, 12), M4.mul(xf, M4.trs(side * 0.16, 0.555, 0.007, 0, Math.PI / 2)), SEATMAT.black);
  for (let b = 0; b < 8; b++) {
    const bx = side * (0.16 + (b % 4 < 2 ? -1 : 1) * (0.028 + (b % 2) * 0.014)), by = 0.555 + (b < 4 ? 0.02 : -0.02);
    B.add(gCyl(0.005, 0.005, 0.003, 8), M4.mul(xf, M4.trs(bx, by, 0.0065, 0, Math.PI / 2)), SEATMAT.card);
  }
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
  B.add(gCyl(0.028, 0.028, 0.012, 16), M4.trs(x, y, z + dir * 0.004, 0, rx), { c: '#1a1b1e', r: 0.4 });
  B.add(gCyl(0.022, 0.022, 0.02, 14), M4.trs(x, y, z + dir * 0.008, 0, rx), SEATMAT.black);
  B.add(gCyl(0.015, 0.015, 0.004, 12), M4.trs(x, y, z + dir * 0.0185, 0, rx), SEATMAT.jLens);   // off: dark frosted lens
  B.add(gCyl(0.014, 0.014, 0.014, 12), M4.trs(x, y - 0.045, z + dir * 0.006, 0, rx), SEATMAT.black);
}
// QA w1: tall charcoal column on the far side of the monitor from the cabinet, from the console top to the shell top,
// carrying the big reading lamp over a smaller air nozzle and the blue safety-card pocket at its foot (c_27316 left of
// the monitor, c_27315 top right + foreground, c_27312 centre, omaat_room_14) [V]; ~0.08 wide, stands ~0.11 proud [D]
function roomColumn(B, x, zf, dir, y0) {
  const d = 0.11, z = zf + dir * d / 2, zf2 = zf + dir * d, h = MON.top - y0;
  B.add(gRBox(0.08, h, d, 0.012, 1), M4.trs(x, y0 + h / 2, z), SEATMAT.jShell);
  capRail(B, 0.08, d, x, MON.top, z);
  roomLamp(B, x, zf2, dir, 0.99);
  B.add(gQuad(0.045, 0.075), M4.trs(x, y0 + 0.06, zf2 + dir * 0.002, dir > 0 ? 0 : Math.PI), { c: '#35568f', r: 0.5 });
  B.add(gQuad(0.037, 0.018), M4.trs(x, y0 + 0.07, zf2 + dir * 0.003, dir > 0 ? 0 : Math.PI), { c: '#b8c0cc', r: 0.6 });
}
// aisle armrest ledge: silver stepped ledge (6 mm lower step on its aisle edge) with a dark lengthwise slot holding the
// grey-metal top edge of the retracted pop-up privacy panel (omaat_room_13, c_27313 bottom corners; QA r3 had an ash strip) [V]
function roomLedge(B, w, x, z, L) {
  const y = ROOM.top;
  const xg = x + w / 2 - 0.05;
  B.add(gRBox(w - 0.03, 0.03, L + 0.02, 0.012, 2), M4.trs(x - 0.015, y + 0.01, z), SEATMAT.jRail);
  B.add(gRBox(0.03, 0.03, L + 0.02, 0.008, 1), M4.trs(x + w / 2 - 0.015, y + 0.004, z), SEATMAT.jRail);
  B.add(gBox(0.03, 0.008, L), M4.trs(xg, y + 0.023, z), SEATMAT.jVoid);
  B.add(gBox(0.012, 0.004, L - 0.02), M4.trs(xg, y + 0.026, z), SEATMAT.jPanelEdge);
}

// Central monument of a pair between z = MON.zO (O's face, looking -z at O) and MON.zE (E's face, +z): O's monitor
// (outer column) back to back with E's cabinet, O's cabinet (aisle column) back to back with E's monitor; both footwells
// run under it (omaat_room_14 / 16, c_27316: cabinet flush beside the monitor frame, footwell mouth under the monitor)
const MON = { zO: -0.21, zE: 0.035, top: 1.05, bot: 0.555 };
const CON = { top: 0.60 };   // outer console top (c_27316 / 27303: ~0.17 above the cushion) [A]
// QA w1 pillow: flat piped rectangle ~0.44 x 0.34 x 0.07, navy check jacquard face, grey-taupe reverse panel + piping
// (c_27303, omaat_room_13) [V]
function roomPillow(B, xf) {
  B.add(gLoft(cushionSecs(0.44, 0.34, 0.07, -0.035, { edge: 0.015, r: 0.02 }), 3), xf, SEATMAT.pillowBlue);
  B.add(gRBox(0.43, 0.004, 0.33, 0.015, 1), M4.mul(xf, M4.trs(0, -0.035, 0)), SEATMAT.jPillowBack);
}
// QA w1 duvet: desaturated slate grey-blue quilted comforter that hangs over the mattress edges (tt_bed-2 crop ~(102,104,
// 107) under warm night light) [V]; 0.12 m quilting channels as darker seams [A]
function roomDuvet(B, x, z, w) {
  B.add(gLoft(cushionSecs(w + 0.04, 1.1, 0.07, -0.05, { edge: 0.06, r: 0.06, crown: 0.02 }), 3), M4.trs(x, ROOM.bed + 0.07, z), SEATMAT.duvet);
  for (let k = -3; k <= 4; k++) B.add(gBox(w - 0.04, 0.003, 0.006), M4.trs(x, ROOM.bed + 0.113, z + k * 0.12 - 0.06), { c: '#4a5364', r: 0.95 });
}
function roomPart(part, opts = {}) {
  const B = new Builder();
  const bed = !!opts.bed, lod = !!opts.lod;
  const { hx, hz, top, wall } = ROOM;
  const shell = SEATMAT.jShell, ash = SEATMAT.ash;
  if (part === 'O') {
    // --- the seat: back against the forward end, facing aft (+z)
    const S = M4.trs(-0.21, 0, -1.27, Math.PI);
    const tmp = new Builder(); roomSeatCore(tmp, bed, lod, 0.58); B.addBuilt(tmp.build(), S);
    // back shell: charcoal wall, dark padded band above the seat back, cap, reading light in the corner
    B.add(gRBox(0.70, wall, 0.07, 0.03, 2), M4.trs(-0.235, wall / 2, -1.31), shell);
    B.add(gRBox(0.64, 0.30, 0.02, 0.012, 1), M4.trs(-0.24, 0.93, -1.268), SEATMAT.jLeather);
    capRail(B, 0.70, 0.07, -0.235, wall, -1.31);
    roomLamp(B, -0.52, -1.258, 1);
    // aisle corner: LOW armrest ledge (0.66) holding the retracted pop-up privacy panel (only its ash top edge shows)
    B.add(gRBox(0.50, top, 0.28, 0.02, 1), M4.trs(0.335, top / 2, -1.20), shell);
    B.add(gRBox(0.16, 0.035, 0.28, 0.014, 2), M4.trs(0.17, top + 0.012, -1.20), SEATMAT.jLeather);
    roomLedge(B, 0.34, 0.415, -1.20, 0.26);
    roomAisleAsh(B, hx, -1.34, -1.06);
    if (!lod) B.add(gRBox(0.08, 0.05, 0.004, 0.004, 1), M4.trs(0.42, 0.50, -1.0585), SEATMAT.black);   // stowage latch
    // O's side table over E's footwell (aisle column): ash top with a large-radius rounded front corner, thin silver band
    // under it, charcoal console body whose seat-facing face carries the controls (omaat_room_14 / 18, c_27316)
    const tx0 = 0.12, tx1 = 0.55, tz0 = -0.62, R = 0.11;
    planSlab(B, planRRect(tx0, tx1, tz0, MON.zO, [R, 0.01, 0.004, 0.004]), top - 0.035, 0.035, ash);
    planSlab(B, planRRect(tx0 + 0.004, tx1, tz0 + 0.004, MON.zO, [R - 0.004, 0.004, 0.004, 0.004]), top - 0.041, 0.006, SEATMAT.jRail);
    planSlab(B, planBand(tx0 + 0.012, tx1, tz0 + 0.012, MON.zO, R - 0.012, 0.02), 0, top - 0.041, shell);
    if (!lod) roomControls(B, M4.trs(0.30, 0, tz0 + 0.012, Math.PI), -1);
    // tall ash monument end at the aisle with a wide flat cap (seat plaques lie on it, c_27313) + kick
    const ez0 = -0.58, ez1 = MON.zE, ezc = (ez0 + ez1) / 2;
    B.add(gRBox(0.04, wall, ez1 - ez0, 0.012, 1), M4.trs(0.565, wall / 2, ezc), ash);
    B.add(gRBox(0.045, 0.10, ez1 - ez0, 0.01, 1), M4.trs(0.565, 0.05, ezc), shell);
    ashFrameX(B, 0.565, 0.04, 0.10, wall, ez0, ez1);
    // shared aisle-end cap: mid grey, a little darker than the plaques, oval finger recess between them (c_27314)
    B.add(gRBox(0.10, 0.02, ez1 - ez0 + 0.006, 0.006, 1), M4.trs(0.54, wall + 0.01, ezc), { c: '#7c7f84', r: 0.45, l: LAYER.plastic });
    if (!lod) B.add(gCyl(1, 1, 1, 16), M4.trs(0.545, wall + 0.0205, ezc, 0, 0, 0, 0.0175, 0.003, 0.035), SEATMAT.jBase);
    // E's footwell under the table + monument (aisle column), mouth under E's monitor
    B.add(gRBox(0.41, 0.02, MON.zO - tz0 - 0.03, 0.006, 1), M4.trs(0.3375, 0.57, (MON.zO + tz0 + 0.03) / 2), SEATMAT.jShellIn);
    roomFootwell(B, 0.135, 0.545, MON.zE, tz0 + 0.035, 1);
    // sliding door parked in the monument; its leading edge (ash face, charcoal frame, finger pull) faces aft
    doorEdge(B, 0.56, -0.60, wall - 0.14);
    // central monument body (both columns) + the pillar between the two footwell mouths
    B.add(gRBox(1.13, MON.top - MON.bot, MON.zE - MON.zO, 0.01, 1), M4.trs(-0.02, (MON.top + MON.bot) / 2, (MON.zO + MON.zE) / 2), shell);
    B.add(gRBox(0.245, MON.bot, MON.zE - MON.zO, 0.01, 1), M4.trs(0.0075, MON.bot / 2, (MON.zO + MON.zE) / 2), shell);
    // O's face: monitor (outer column) + O's cabinet (aisle column)
    roomMonitor(B, -0.20, MON.zO, -1, 1);
    roomCabinet(B, 0.275, MON.zO, -1);
    roomColumn(B, -0.545, MON.zO, -1, CON.top);
    // O's footwell under E's console (outer column), mouth under O's monitor
    B.add(gRBox(0.44, 0.02, 0.585, 0.006, 1), M4.trs(-0.35, 0.57, 0.33), SEATMAT.jShellIn);
    roomFootwell(B, -0.56, -0.13, MON.zO, 0.62, -1);
    if (bed) {
      B.add(gLoft(cushionSecs(0.56, 1.76, 0.05, -0.02, { edge: 0.02, r: 0.03, crown: 0.004 }), 3), M4.trs(-0.22, ROOM.bed + 0.02, -0.40), SEATMAT.mattress);
      roomDuvet(B, -0.22, -0.05, 0.58);
      B.add(gLoft(cushionSecs(0.46, 0.30, 0.12, -0.06, { edge: 0.05, r: 0.05 }), 3), M4.trs(-0.21, ROOM.bed + 0.08, -1.08), SEATMAT.pillow);
    } else {
      roomPillow(B, M4.mul(M4.trs(-0.31, 0.575, -1.04, Math.PI), M4.trs(0, 0, 0, 0.25, -76 * DEG)));
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
    const tmp = new Builder(); roomSeatCore(tmp, bed, lod); B.addBuilt(tmp.build(), S);
    B.add(gRBox(0.69, wall, 0.07, 0.03, 2), M4.trs(0.235, wall / 2, 1.31), shell);
    B.add(gRBox(0.62, 0.30, 0.02, 0.012, 1), M4.trs(0.21, 0.93, 1.268), SEATMAT.jLeather);
    capRail(B, 0.69, 0.07, 0.235, wall, 1.31);
    roomLamp(B, -0.07, 1.258, -1);
    // narrow aisle armrest with the pop-up privacy panel retracted inside (ash edge flush in the cap)
    B.add(gRBox(0.09, top, 0.60, 0.02, 1), M4.trs(0.54, top / 2, 0.95), shell);
    roomLedge(B, 0.10, 0.54, 0.95, 0.60);
    roomAisleAsh(B, hx, 0.65, 1.25);
    // wide console by the outer column (window / centreline) from the monument to the back shell, hollow under its
    // forward half (O's footwell); ash top on a thin silver band
    const cz0 = MON.zE, cz1 = 1.30, czc = (cz0 + cz1) / 2;
    B.add(gRBox(0.45, 0.035, cz1 - cz0, 0.01, 1), M4.trs(-0.355, top - 0.018, czc), ash);
    B.add(gRBox(0.452, 0.006, cz1 - cz0 - 0.004, 0.003, 1), M4.trs(-0.352, top - 0.038, czc), SEATMAT.jRail);
    B.add(gRBox(0.44, top - 0.041, 0.66, 0.02, 1), M4.trs(-0.355, (top - 0.041) / 2, 0.95), SEATMAT.jShellIn);
    B.add(gRBox(0.02, top - 0.041, cz1 - cz0, 0.008, 1), M4.trs(-0.125, (top - 0.041) / 2, czc), shell);
    if (!lod) {
      B.add(gRBox(0.02, 0.05, 0.10, 0.004, 1), M4.trs(-0.114, 0.50, 1.0), { c: '#b3262a', r: 0.5 });   // life-vest tab (red, c_27302)
      roomControls(B, M4.trs(-0.115, 0, 0.70, Math.PI / 2), -1);
    }
    // E's face of the monument: E's cabinet (outer column) + E's monitor (aisle column); mouth of E's footwell below
    roomCabinet(B, -0.325, MON.zE, 1);
    roomMonitor(B, 0.15, MON.zE, 1, -1);
    roomColumn(B, 0.495, MON.zE, 1, MON.bot);
    // E's sliding door parked in the monitor monument; leading edge faces aft toward E's entry
    doorEdge(B, 0.56, 0.06, wall - 0.14);
    if (bed) {
      B.add(gLoft(cushionSecs(0.58, 1.80, 0.05, -0.02, { edge: 0.02, r: 0.03, crown: 0.004 }), 3), M4.trs(0.24, ROOM.bed + 0.02, 0.38), SEATMAT.mattress);
      roomDuvet(B, 0.24, 0.05, 0.56);
      B.add(gLoft(cushionSecs(0.46, 0.30, 0.12, -0.06, { edge: 0.05, r: 0.05 }), 3), M4.trs(0.20, ROOM.bed + 0.08, 1.08), SEATMAT.pillow);
    } else {
      roomPillow(B, M4.mul(M4.trs(0.10, 0.575, 1.04), M4.trs(0, 0, 0, -0.25, -76 * DEG)));
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
    B.add(gBox(0.70, wall, 0.07), M4.trs(-0.235, wall / 2, -1.31), SEATMAT.jShell);
    B.add(gRBox(0.62, 0.45, 0.6, 0.03, 1), M4.trs(-0.24, 0.225, -0.95), SEATMAT.jFabric);
    B.add(gRBox(0.58, 0.6, 0.12, 0.04, 1), M4.mul(M4.trs(-0.24, 0.43, -1.2, Math.PI), M4.trs(0, 0.3, 0, 0, 17 * DEG)), SEATMAT.jFabric);
    B.add(gBox(0.50, top, 0.28), M4.trs(0.335, top / 2, -1.20), SEATMAT.jShell);
    B.add(gBox(0.04, wall, 0.655), M4.trs(0.565, wall / 2, -0.2925), SEATMAT.ash);
    B.add(gBox(0.43, top, 0.41), M4.trs(0.335, top / 2, -0.415), SEATMAT.jShell);
    B.add(gBox(1.13, MON.top, MON.zE - MON.zO), M4.trs(-0.02, MON.top / 2, (MON.zO + MON.zE) / 2), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(-0.20, 0.85, MON.zO - 0.002, Math.PI), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.34, 0.38, 0.01), M4.trs(0.275, top + 0.19, MON.zO - 0.004), SEATMAT.ash);
  } else {
    B.add(gBox(0.69, wall, 0.07), M4.trs(0.235, wall / 2, 1.31), SEATMAT.jShell);
    B.add(gRBox(0.58, 0.45, 0.6, 0.03, 1), M4.trs(0.2, 0.225, 0.95), SEATMAT.jFabric);
    B.add(gRBox(0.58, 0.6, 0.12, 0.04, 1), M4.mul(M4.trs(0.2, 0.43, 1.2), M4.trs(0, 0.3, 0, 0, 17 * DEG)), SEATMAT.jFabric);
    B.add(gBox(0.45, top, 1.265), M4.trs(-0.355, top / 2, 0.6675), SEATMAT.jShell);
    B.add(gQuad(0.531, 0.299), M4.trs(0.15, 0.85, MON.zE + 0.002), SEATMAT.screen, atlasUV('screen'));
    B.add(gBox(0.34, 0.38, 0.01), M4.trs(-0.325, top + 0.19, MON.zE + 0.004), SEATMAT.ash);
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
