// ------------------------------------------------------------------
// ANA 777-300ER "New 212 seats": 8 THE Suite / 64 THE Room / 24 Premium Economy / 116 Economy
// Coordinates: meters. z = distance aft of the nose (forward = -z). x = right (+) / left (-). y = up, floor = 0.
// Row / door / monument relations: ANA seat map (b777_300er_1), SeatGuru layout 4, TPG, OMAAT.
// Door spacing derived from verified pitches (THE Room 107 in per nested pair [Safran], PY 38 in, Y 34 in [ANA])
// and cross-checked with 777-200ER NTSB zone stations + 777-300 plug offsets (see REFERENCE777.md).
// ------------------------------------------------------------------
const CAB = {
  R: 2.935, yc: 0.92,            // interior trim circle: 5.87 m cabin width at the window belt
  zFront: 2.80, zAft: 61.40,
  doors: [5.40, 16.80, 32.70, 44.30, 58.70],
  doorW: 1.07, doorH: 1.88,      // Type A, 42 x 74 in
  win: { w: 0.254, h: 0.381, yc: 1.02, pitch: 0.5334, holeW: 0.305, holeH: 0.445 },
  floorHalf: 2.70,
  pairLen: 107 * 0.0254,         // THE Room nested pair
};
const IN = 0.0254;

const CLASS_INFO = {
  F: {
    name: 'THE Suite · First', short: 'THE Suite', config: '1-2-1', color: '#c9a86a',
    specs: [['Screen', '43 in 4K'], ['Bed', 'about 76–81 in'], ['Door', 'Sliding, open top'], ['Maker', 'JAMCO']],
  },
  J: {
    name: 'THE Room · Business', short: 'THE Room', config: '1-2-1', color: '#5f93d6',
    specs: [['Seat width', 'about 35–38 in'], ['Bed', 'about 72 in'], ['Screen', '24 in 4K'], ['Door', 'Sliding + pop-up panel']],
  },
  PY: {
    name: 'Premium Economy', short: 'Premium Economy', config: '2-4-2', color: '#8b7fd0',
    specs: [['Seat pitch', '38 in'], ['Seat width', 'about 19 in'], ['Screen', '15.6 in'], ['Leg rest', 'Leg rest + footrest']],
  },
  Y: {
    name: 'Economy', short: 'Economy', config: '3-4-3', color: '#9aa7ba',
    specs: [['Seat pitch', '34 in'], ['Seat width', 'about 17 in'], ['Screen', '13.3 in'], ['Headrest', '6-way']],
  },
};

// THE Room lateral units (outer column x0 -> aisle): side units against the wall, centre units at the centreline
const ROOM_UNITS = [
  { q: 'L', x: -2.275, mir: false, odd: 'A', even: 'C', outer: 'window' },
  { q: 'LC', x: -0.585, mir: true, odd: 'E', even: 'D', outer: 'center' },
  { q: 'RC', x: 0.585, mir: false, odd: 'F', even: 'G', outer: 'center' },
  { q: 'R', x: 2.275, mir: true, odd: 'K', even: 'H', outer: 'window' },
];
// THE Suite: window suites A/K, centre suites D/G (partition between them)
const SUITE_UNITS = [
  { L: 'A', x: -2.24, mir: false, pos: 'window' },
  { L: 'D', x: -0.56, mir: true, pos: 'center' },
  { L: 'G', x: 0.56, mir: false, pos: 'center' },
  { L: 'K', x: 2.24, mir: true, pos: 'window' },
];

function buildLayout() {
  const W = CAB.win;
  const seats = [];
  const mon = [];   // {kind, x0,x1,z0,z1,h, face: +1 (front faces aft) / -1 (faces fwd)}
  const add = (s) => { seats.push(s); return s; };
  const D = CAB.doors;
  const dz = D.map((c) => [c - 0.60, c + 0.60]); // cross-aisle / door zones

  // ---------------- THE Suite rows 1-2 (suite depth 2.20 m, z = aft wall of the suite) ----------------
  const FP = 2.20;
  const suiteZ = { 1: 9.80, 2: 12.00 };
  for (const r of [1, 2]) for (const u of SUITE_UNITS) {
    const notes = [];
    if (u.pos === 'window') notes.push('Window suite: narrow shelf along the windows, wardrobe in the thick aisle-side door');
    else notes.push('Centre suite: the full-height partition to the neighbour can be lowered');
    if (r === 1) notes.push('Front row, closest to door 1 and the galley');
    if (r === 1 && u.L === 'A') notes.push('A lavatory with a bidet is directly in front');
    add({ id: r + u.L, row: r, letter: u.L, cls: 'F', kind: 'suite', x: u.x, z: suiteZ[r], mir: u.mir, pos: u.pos, notes, len: FP });
  }

  // ---------------- THE Room rows 5-20: nested pairs (odd rear-facing at the outer column, even forward-facing by the aisle)
  // pair z = centre of the 2.718 m unit; odd seat back at the forward end, even seat back at the aft end
  const PL = CAB.pairLen;
  const pairStart = { 5: 12.12, 7: dz[1][1] + 0.02, 17: dz[2][1] + 0.02 };
  const roomPairs = [];
  for (const r0 of [5, 7, 9, 11, 13, 15, 17, 19]) {
    let z0;
    if (r0 === 5) z0 = pairStart[5];
    else if (r0 < 17) z0 = pairStart[7] + ((r0 - 7) / 2) * PL;
    else z0 = pairStart[17] + ((r0 - 17) / 2) * PL;
    roomPairs.push({ r0, z0, zc: z0 + PL / 2 });
  }
  for (const pr of roomPairs) {
    for (const u of ROOM_UNITS) {
      for (const odd of [true, false]) {
        const row = odd ? pr.r0 : pr.r0 + 1;
        const L = odd ? u.odd : u.even;
        const notes = [];
        if (odd) notes.push(u.outer === 'window' ? 'Rear-facing, right against the windows, away from the aisle' : 'Rear-facing centre pair: the divider between the two seats lowers for couples');
        else notes.push(u.outer === 'window' ? 'Forward-facing seat by the aisle; wide console next to the window' : 'Forward-facing centre seat on the aisle; consoles meet in the middle');
        if (row === 5 || row === 6) notes.push('Mini cabin of eight seats between doors 1 and 2');
        if (row === 6 || row === 7) notes.push('Near the lavatories and galley at door 2');
        if (row === 16 || row === 17) notes.push('Near the lavatories and self-service bar at door 3');
        if ((row === 16 || row === 20) && (L === 'D' || L === 'H')) notes.push('Bassinet position');
        if (row === 13 && L === 'K') notes.push('Reported to line up with just one window');
        // seat reference (hip area) used for picking / eye; x of the seat column inside the unit
        const sgn = u.mir ? -1 : 1;                    // local +x = aisle for unmirrored units
        const colX = odd ? -0.20 : 0.25;               // outer column vs aisle column (local)
        const sx = u.x + sgn * colX;
        const sz = odd ? pr.zc - 0.95 : pr.zc + 0.95;  // hip point
        add({ id: row + L, row, letter: L, cls: 'J', kind: 'room', x: sx, z: sz, ux: u.x, uz: pr.zc, mir: u.mir, odd,
          pos: odd && u.outer === 'window' ? 'window' : (odd ? 'center' : 'aisle'), notes });
      }
    }
  }

  // ---------------- Premium Economy rows 25-27 (A C | D E F G | H K) ----------------
  // z = seat-back reference (aft face of the seat back at the hinge)
  const pyZ = { 25: 40.30 };
  pyZ[26] = pyZ[25] + 38 * IN; pyZ[27] = pyZ[26] + 38 * IN;
  const pySp = 0.5525;
  const pyX = { A: -2.337 - pySp / 2, C: -2.337 + pySp / 2, D: -1.5 * pySp, E: -0.5 * pySp, F: 0.5 * pySp, G: 1.5 * pySp, H: 2.337 - pySp / 2, K: 2.337 + pySp / 2 };
  for (const r of [25, 26, 27]) for (const L of Object.keys(pyX)) {
    const pos = (L === 'A' || L === 'K') ? 'window' : (L === 'E' || L === 'F') ? 'middle' : 'aisle';
    const notes = [];
    if (r === 25) { notes.push('Bulkhead row: shared monitor ahead, no floor storage for take-off'); if ('AEFK'.includes(L)) notes.push('Bassinet position'); }
    if (r === 27 && (L === 'A' || L === 'C')) notes.push('Directly beside the wheelchair-accessible lavatory');
    if (r === 27) notes.push('Close to the galley and lavatory at door 4');
    add({ id: r + L, row: r, letter: L, cls: 'PY', kind: 'py', x: pyX[L], z: pyZ[r], pos, notes, bulkhead: r === 25 });
  }

  // ---------------- Economy rows 30-42 ----------------
  const ySp = 19 * IN;             // 17 in seat + 2 in armrest
  const tri = 2.172;               // triple-block centre
  const yX = { A: -tri - ySp, B: -tri, C: -tri + ySp, D: -1.5 * ySp, E: -0.5 * ySp, F: 0.5 * ySp, G: 1.5 * ySp, H: tri - ySp, J: tri, K: tri + ySp };
  const rowZ = { 30: 46.14 };
  for (let r = 31; r <= 42; r++) rowZ[r] = 47.00 + (r - 31) * 34 * IN;
  for (let r = 30; r <= 42; r++) {
    let letters = Object.keys(yX);
    if (r === 30) letters = ['A', 'B', 'C', 'H', 'J', 'K'];
    if (r >= 39 && r <= 41) letters = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'K'];
    if (r === 42) letters = ['A', 'C', 'D', 'E', 'F', 'G'];
    const taper = r >= 39;
    for (const L of letters) {
      let x = yX[L];
      // rows 39-42: two-seat side blocks sit where B/C (H/J) are; the window seat moves inboard
      if (taper && L === 'A') x = yX.B; if (taper && L === 'K') x = yX.J;
      if (taper && L === 'H') x = yX.H;
      const pos = (L === 'A' || L === 'K') ? 'window' : ('BEFJ'.includes(L) && !taper) ? 'middle' : (taper && (L === 'E' || L === 'F')) ? 'middle' : 'aisle';
      const notes = [];
      if (r === 30) {
        notes.push('Exit row behind door 4: most legroom, tray and screen in the armrest');
        if (L === 'A' || L === 'K') notes.push('No window at this seat');
      }
      if (r === 31 && 'DEFG'.includes(L)) notes.push('Bulkhead: shared monitor ahead, fixed armrests');
      if (r === 31 && (L === 'E' || L === 'F')) notes.push('Bassinet position');
      if (r >= 39 && r <= 41) notes.push('Rear section narrows: two seats by each window');
      if (r >= 41) notes.push('Limited recline, wall behind; near the rear lavatories');
      if ((r === 38) && (L === 'C' || L === 'H')) notes.push('Aisle traffic from the rear');
      add({ id: r + L, row: r, letter: L, cls: 'Y', kind: 'econ', x, z: rowZ[r], pos, notes, bulkhead: r === 30 || (r === 31 && 'DEFG'.includes(L)), exitRow: r === 30 });
    }
  }

  // ---------------- Monuments ----------------
  const M = (kind, x0, x1, z0, z1, extra = {}) => mon.push({ kind, x0, x1, z0, z1, h: extra.h || 2.15, ...extra });
  // Front of door 1: lav (L), flight-deck door (C), galley (R)
  M('lav', -2.70, -1.35, 2.80, 4.78, { face: 1 });
  M('closet', -1.30, -0.50, 2.80, 3.40, { face: 1 });
  M('cockpit', -0.50, 0.50, 2.66, 2.82, { face: 1 });
  M('galley', 0.50, 2.70, 2.80, 4.78, { face: 1, carts: 4 });
  // Aft of door 1: bidet lav in front of 1A, closets in front of the centre suites and 1K
  M('lav', -2.70, -1.62, dz[0][1], 7.52, { face: -1, wide: true });
  M('closet', -1.10, 1.10, dz[0][1], 6.90, { face: -1, h: 1.35, low: true });
  M('closet', 1.62, 2.70, dz[0][1], 7.40, { face: -1 });
  // F/J bulkhead with curtain openings at the aisles
  const part = (z, t, segs, extra = {}) => segs.forEach(([a, b]) => M('partition', a, b, z, z + t, { h: 1.80, ...extra }));
  part(12.00, 0.08, [[-2.70, -1.69], [-1.17, 1.17], [1.69, 2.70]], { wood: true });
  // Door 2: two lavs behind 6C / 6H, galley in the centre
  M('lav', -2.70, -1.62, 14.86, dz[1][0], { face: 1 });
  M('galley', -1.10, 1.10, 14.86, dz[1][0], { face: 1, carts: 3, welcome: true });
  M('lav', 1.62, 2.70, 14.86, dz[1][0], { face: 1 });
  // Door 3: two lavs (bidets) + self-service bar between rows 16 and 17
  const z16 = pairStart[7] + 5 * PL;
  M('lav', -2.70, -1.62, z16 + 0.03, dz[2][0], { face: 1 });
  M('bar', -1.10, 1.10, z16 + 0.03, dz[2][0], { face: 1 });
  M('lav', 1.62, 2.70, z16 + 0.03, dz[2][0], { face: 1 });
  // J / PY bulkhead (shared monitors + bassinets on its aft face)
  const z20 = pairStart[17] + 2 * PL;
  part(z20 + 0.02, 0.08, [[-2.70, -1.62], [-1.12, 1.12], [1.62, 2.70]], { bassinet: true, monitor: true, wood: true });
  // Door 4: wheelchair-accessible lav beside 27A/C, stowage on the right, galley in front of row 31 (centre)
  M('lav', -2.70, -1.25, pyZ[27] + 0.14, dz[3][0], { face: 1, wide: true, access: true });
  M('closet', 1.62, 2.70, pyZ[27] + 0.14, dz[3][0], { face: 1, h: 1.9 });
  M('galley', -1.00, 1.00, dz[3][1], 45.96, { face: -1, carts: 3 });
  // Rear (door 5): three lavatories + stowage behind 41H/K; aft galley
  const zb = rowZ[42] + 0.12;
  M('lav', -2.70, -1.25, zb, dz[4][0], { face: 1 });
  M('closet', -1.00, 0.0, zb, dz[4][0], { face: 1, h: 1.9 });
  M('lav', 0.0, 1.00, zb, dz[4][0], { face: 1, baby: true });
  M('closet', 1.25, 2.70, rowZ[41] + 0.12, zb - 0.02, { face: -1, h: 1.25, low: true });
  M('lav', 1.25, 2.70, zb, dz[4][0], { face: 1 });
  M('galley', -2.50, 2.50, dz[4][1], CAB.zAft, { face: -1, carts: 7 });
  // side ledges where the fuselage narrows (rows 39-42 lose the window seat position)
  for (const r of [39, 40, 41, 42]) for (const sx of [-1, 1]) {
    if (r === 42 && sx > 0) continue;
    M('sideStorage', sx < 0 ? -2.70 : 2.40, sx < 0 ? -2.40 : 2.70, rowZ[r] - 0.80, rowZ[r] + 0.06, { h: 0.62 });
  }

  // ---------------- Zones along z (drive ceilings/bins) ----------------
  const zones = [
    { type: 'mono', z0: CAB.zFront, z1: dz[0][0] },
    { type: 'door', z0: dz[0][0], z1: dz[0][1], door: 0 },
    { type: 'mono', z0: dz[0][1], z1: 7.52 },
    { type: 'seat', z0: 7.52, z1: 14.86, cls: 'F' },
    { type: 'mono', z0: 14.86, z1: dz[1][0] },
    { type: 'door', z0: dz[1][0], z1: dz[1][1], door: 1 },
    { type: 'seat', z0: dz[1][1], z1: z16 + 0.03, cls: 'J' },
    { type: 'mono', z0: z16 + 0.03, z1: dz[2][0] },
    { type: 'door', z0: dz[2][0], z1: dz[2][1], door: 2 },
    { type: 'seat', z0: dz[2][1], z1: pyZ[27] + 0.14, cls: 'J' },
    { type: 'mono', z0: pyZ[27] + 0.14, z1: dz[3][0] },
    { type: 'door', z0: dz[3][0], z1: dz[3][1], door: 3 },
    { type: 'seat', z0: dz[3][1], z1: zb, cls: 'Y' },
    { type: 'mono', z0: zb, z1: dz[4][0] },
    { type: 'door', z0: dz[4][0], z1: dz[4][1], door: 4 },
    { type: 'mono', z0: dz[4][1], z1: CAB.zAft },
  ];

  // ---------------- Windows: one per frame bay (21 in), none across the door cut-outs ----------------
  const windows = [];
  const P = W.pitch;
  // frame grid anchored on door 1; windows skip a door's two bays plus one each side
  for (let k = -3; k * P + D[0] < CAB.zAft - 0.6; k++) {
    const z = D[0] + P * 0.5 + k * P;
    if (z < 3.3) continue;
    if (D.some((c) => Math.abs(z - c) < 0.95)) continue;
    windows.push(z);
  }
  const winList = [];
  for (const z of windows) for (const side of [-1, 1]) {
    const cls = z < 12.0 ? 'F' : z < z20 ? 'J' : z < dz[3][0] ? 'PY' : 'Y';
    winList.push({ z, side, level: 0, electric: cls === 'F' || cls === 'J', cls });
  }

  // ---------------- Walkable areas (x0,x1,z0,z1) ----------------
  const walk = [];
  const Wk = (x0, x1, z0, z1) => walk.push([x0, x1, z0, z1]);
  for (const [a, b] of dz) Wk(-2.30, 2.30, a, b);
  Wk(-1.32, 1.58, 4.60, dz[0][0]);                  // galley/cockpit area ahead of door 1
  Wk(-1.60, -1.12, dz[0][1], 14.9); Wk(1.12, 1.60, dz[0][1], 14.9);  // F + forward J aisles
  Wk(-1.6, 1.6, 6.90, 7.50);                         // area ahead of the suites
  Wk(-1.62, -1.17, dz[1][1], z16 + 0.1); Wk(1.17, 1.62, dz[1][1], z16 + 0.1);
  Wk(-1.62, -1.17, dz[2][1], z20 + 0.1); Wk(1.17, 1.62, dz[2][1], z20 + 0.1);
  Wk(-1.52, -1.16, z20, dz[3][0]); Wk(1.16, 1.52, z20, dz[3][0]);   // PY aisles
  Wk(-1.40, 1.40, dz[3][1], 45.4);                   // exit row + galley front
  Wk(-1.40, -1.00, 45.3, zb + 0.05); Wk(1.00, 1.40, 45.3, zb + 0.05);  // economy aisles
  Wk(-1.20, 1.20, dz[4][0] - 0.05, dz[4][1] + 0.4);

  return monoLayoutQA({ seats, mon, zones, windows: winList, walk, suiteZ, roomPairs, pyZ, rowZ, doorsZ: dz, z16, z20, zb });
}

// ---- Monument layout amendments (monuments QA r2, folded in from 10_mono.js), applied to the base map at the end of
// buildLayout. They follow the official ANA seat map (ref/web/monuments/ana_b-777-300ER-n212map.png) and move whole
// row groups (the guard skips the pass if the door-3 bar already stands aft of door 3).
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
  // w5: one loose untied drape per aisle, gathered against the centre wall (omaatF_ANA-First-Class-Suite-777-40, ml_DSC_1914)
  for (const [a, b] of [[-1.68, -0.88], [0.82, 1.62]]) M('curtain', a, b, 7.43, 7.43, { xg: a < 0 ? b - 0.2 : a + 0.2, tone: 'F', h: 0 });
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
  M('galley', 1.62, 2.70, pz27 + 0.14, dz[3][0], { face: 1, carts: 2, rowMonitor: 2.2, jumpX: 2.32 });
  // dark slate PY curtains in both aisles right behind row 27 (py_37302), gathered against the centre galley
  const zc4 = pz27 + ML.pyRecline - 0.07;
  M('curtain', -1.62, -1.05, zc4, zc4, { xg: -1.10, tone: 'Y', h: 0 });
  M('curtain', 1.07, 1.62, zc4, zc4, { xg: 1.12, tone: 'Y', h: 0 });

  // ---- door 5: drop the outboard lavs ahead of it and the transverse aft galley; fore-aft galleys + outboard lavs
  del((m) => m.kind === 'lav' && near(m.z1, dz[4][0]) && Math.abs(m.x0 + m.x1) > 2);
  del((m) => m.kind === 'galley' && near(m.z0, dz[4][1]) && m.x1 - m.x0 > 3);
  M('galley', -1.52, -0.63, dz[4][1], CAB.zAft, { face: '+x', carts: 6 });
  M('galley', 0.60, 1.46, dz[4][1], CAB.zAft, { face: '-x', carts: 6 });
  M('lav', -2.35, -1.55, dz[4][1], dz[4][1] + 1.2, { face: -1 });
  M('lav', 1.46, 2.31, dz[4][1], dz[4][1] + 1.2, { face: -1 });
  // light-grey curtains across both aisles at the end of economy (y_47300)
  M('curtain', -1.70, -1.00, zb, zb, { xg: -1.20, tone: 'R', h: 0 });     // w5: wide drapes, inner edge at the centre block
  M('curtain', 1.00, 1.62, zb, zb, { xg: 1.20, tone: 'R', h: 0 });

  // ---- jump seats: plain lav / closet walls and the door-5 galley end panels
  L.jumps = [[-2.2, dz[0][0], 1], [2.2, dz[0][1], -1], [-2.46, dz[1][1], -1], [2.42, dz[1][1], -1], [-2.45, dz[2][1], -1], [2.45, dz[2][1], -1],
    [2.32, dz[3][0], 1], [-1.30, dz[4][1], -1], [-0.86, dz[4][1], -1], [1.03, dz[4][1], -1]];   // map: two boxes at the left door-5 galley

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
