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

  return { seats, mon, zones, windows: winList, walk, suiteZ, roomPairs, pyZ, rowZ, doorsZ: dz, z16, z20, zb };
}
