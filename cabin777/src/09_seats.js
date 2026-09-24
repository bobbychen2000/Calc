// ------------------------------------------------------------------
// Seat models for the ANA 777-300ER (see REFERENCE777.md)
// Seat-local frame: x across, y up, z = 0 at the seat-back reference, passenger faces -z
// ------------------------------------------------------------------
const SEATMAT = {
  // Economy (Recaro): royal-blue tick jacquard (plus a diamond variant ~1 seat in 3, y_47306 / 47300), slate leatherette
  // headrest covers, off-white shells + arms, cerulean belts, navy pillows -- all read from ANA's official Y photos
  // (ref/ana/y_4730x; REFERENCE777.md). Fabric mean #2a3a70 (ground ~#1f3068, ticks ~#bccdf5 in y_47306); photoBase()
  // compensates the wide-range swatch encoding
  // QA r2: the old #2a3a70 rendered ~3x too dark and too saturated (render #0f163e vs photo #415390 y_47301, #495d99
  // y_47306). The pale ticks carry most of the red, and the ACES toe crushes the dark ground's red, so the seat reads
  // more saturated than its albedo: #5468a8 is the base whose tick swatch averages #415596 through the renderer's tone
  // curve at studio exposure (4x4 texel average, test/sim of 04_shaders toLin + aces) ~ photo #415390 [D]
  yFabric: { c: photoBase('#5468a8', 'y_tick'), r: 0.9, l: LAYER.yJacq },
  yFabricB: { c: photoBase('#5468a8', 'y_diamond'), r: 0.9, l: LAYER.yDiamond },
  yFabricC: { c: '#5064a4', r: 0.9, l: LAYER.yMosaic },   // third variant: dash mosaic (y_47302 left, y_47306 right)
  // headrest cushion: sparse white confetti on cobalt, a different fabric from the back (y_47306 / 47302 wings,
  // REFERENCE777.md) - shares the luminance-only confetti swatch with the PY wings
  // (same tone-curve match: wing photo mean #334276 in y_47306 -> base #4a5a98 averages #324384) [D]
  yHead: { c: photoBase('#4a5a98', 'py_confetti'), r: 0.9, l: LAYER.pyConfetti },
  // slate-grey leatherette cover, lighter + greyer than the fabric (y_47302 #474960-#4d526f, y_47306 #445072,
  // y_47301 #434765; QA r2 was #3e4661 -> rendered as black slabs)
  yCover: { c: '#50566c', r: 0.45, l: LAYER.leather },
  yShell: { c: '#d9dbde', r: 0.42, l: LAYER.plastic },
  yShellDark: { c: '#c2c5c9', r: 0.5, l: LAYER.plastic },
  yTray: { c: '#cfd2d6', r: 0.4, l: LAYER.plastic },
  yBelt: { c: '#3a64a6', r: 0.7, l: LAYER.fabric },        // y_47303 (58,102,173), G/B 0.59
  yPillow: { c: '#2e3860', r: 0.9, l: LAYER.fabric },      // y_47300 (44,53,88)
  arm: { c: '#d3d6d9', r: 0.45, l: LAYER.plastic },
  armPad: { c: '#c6c9cd', r: 0.5, l: LAYER.plastic },
  frame: { c: '#a3a8ae', r: 0.32, m: 0.85, l: LAYER.brushed },
  black: { c: '#15181c', r: 0.45 },
  port: { c: '#0b0c0e', r: 0.4 },
  bezel: { c: '#101215', r: 0.22 },
  screen: { c: '#ffffff', r: 0.2, l: 13, e: 0.9 },
  buckle: { c: '#c3c7cc', r: 0.25, m: 0.9 },
  strap: { c: '#34383f', r: 0.8 },
  pocket: { c: '#2a2e35', r: 0.85, l: LAYER.fabric },
  card: { c: '#d8dde4', r: 0.7 },
  ledG: { c: '#39e07a', r: 0.3, e: 0.8 },
  // Premium Economy (ZIM): charcoal/white dash weave (reads light grey), navy leatherette headrest flap,
  // mid-grey shells + consoles with a silver trim line (ref/ana/py_3730x, ref/web/py san_*). QA r1: white-balanced on the
  // cabin wall both photo sets give near-neutral greys: back fabric (97,97,105) py_37305, wing (94,96,111), shell ~#525352
  // py_37303 -> the blue cast of the old values removed
  // QA r2: darker ground under a high-passed dash swatch at gain 1 so the light dashes carry the brightness (py_37301 back
  // p10/p90 100/201); flap / back luminance 0.43-0.56 (py_37305 41/97, py_37302 69/124): QA r2 render gave 0.61 and an
  // over-saturated navy (ACES toe) with #373f63 -> greyer navy;
  // wings: white flakes (~220) on charcoal-navy (55-65, py_37305). Tone-curve matched as for Y: back #6e7076 averages
  // #5c5f66 (py_37305 back #5f5f68), wing #6e7182 averages #585c6e (py_37305 wing #5d5f6e) [D]
  pyFabric: { c: photoBase('#6e7076', 'py_back'), r: 0.9, l: LAYER.pyFleck },
  pyCover: { c: '#343850', r: 0.5, l: LAYER.leather },   // photo flap #232740, R/B 0.55 (py_37305): less saturated
  pyWing: { c: photoBase('#6e7182', 'py_confetti'), r: 0.9, l: LAYER.pyConfetti },
  pyShell: { c: '#5e6062', r: 0.42, l: LAYER.plastic },
  pyArm: { c: '#595b5e', r: 0.45, l: LAYER.plastic },
  pyArmPad: { c: '#6f7173', r: 0.5, l: LAYER.leather },
  pyBin: { c: '#b8bcc0', r: 0.3, m: 0.85, l: LAYER.brushed },
  pyBay: { c: '#4a4c50', r: 0.6, l: LAYER.plastic },
  pyTrim: { c: '#b9bec4', r: 0.28, m: 0.8, l: LAYER.brushed },
  // THE Room (Safran Fusio custom). Colours sampled from ANA's official seat photos (ref/ana/c_273xx, see REFERENCE777.md):
  // pale grey-beige ash with fine straight grain, charcoal shells with flat charcoal tops (QA r1: shell / console
  // #45484d omaat_room_16, #45454c c_27312; tops #545557 omaat_room_10), silver line only on armrest ledges + door-leaf
  // edges (c_27313 / 27300), charcoal tweed seat, slate Ultraleather headrest flap (#767a7e omaat_room_13), navy pillow
  ash: { c: '#c9c2b3', r: 0.48, l: LAYER.ashGrain },
  ashDark: { c: '#5d6166', r: 0.34, m: 0.35, l: LAYER.brushed },
  rosewood: { c: '#4b403a', r: 0.36, l: LAYER.wood },
  jShell: { c: '#45484d', r: 0.46, l: LAYER.plastic },
  jShellIn: { c: '#3a3d42', r: 0.5, l: LAYER.plastic },
  jCap: { c: '#505358', r: 0.45, l: LAYER.plastic },
  jRail: { c: '#b9bec4', r: 0.26, m: 0.7, l: LAYER.brushed },
  jVoid: { c: '#1d1617', r: 0.9 },
  jBase: { c: '#2a2b2f', r: 0.6 },
  jFabric: { c: '#5c5b61', r: 0.92, l: LAYER.tweed },   // uniform mid grey #5d5d62-#636164 (c_27315, omaat_room_13)
  jLeather: { c: '#4b4d53', r: 0.5, l: LAYER.leather },
  jHead: { c: '#6e7378', r: 0.45, l: LAYER.leather },
  blueAccent: { c: '#233f7a', r: 0.5 },
  slate: { c: '#3f4246', r: 0.55, l: LAYER.marble },
  mattress: { c: '#f0efea', r: 0.9, l: LAYER.fabric },
  duvet: { c: '#34558f', r: 0.95, l: LAYER.fabric },
  pillow: { c: '#eeede8', r: 0.9, l: LAYER.fabric },
  pillowBlue: { c: '#383e6c', r: 0.85, l: LAYER.yagasuri },   // yagasuri jacquard #32355d / #3e457b (c_27302 / 27303)
  lampGlow: { c: '#ffe2b0', r: 0.4, e: 0.35 },
  moodGlow: { c: '#ffd9a0', r: 0.5, e: 0.25 },
  hole: { c: '#0b0d10', r: 1.0 },
  mirror: { c: '#aeb6bf', r: 0.08, m: 0.9 },
  // THE Suite (JAMCO). Colours from ANA's real suite photos f_17313 / f_17314 and OMAAT / TPA in-flight photos
  // (ref/web/suite): warm taupe-grey shells with a thick LIGHTER taupe bullnose cap on every wall top (omaat_f58/f60
  // #9b8d70-#aaa786, tpa_0220 #888482), near-black straight-grain wood (omaat_f60 #322d1a, f2 #2c2217), warm mid-grey
  // tweed seat + ottoman, lavender pillow (omaat_f2/f5/f57 #796fa2 in shade); renders f_17300-17309 give the fluted
  // exterior, floor LED line and window console
  fShell: { c: '#69655f', r: 0.45, l: LAYER.plastic },
  fFlute: { c: '#5a5347', r: 0.5, l: LAYER.plastic },        // rounded door ribs (omaat_f60)
  fFluteGap: { c: '#34302a', r: 0.7 },
  // QA r2: veneer under neutral window light #403430 (up_Privacy-Wall crop, SD 10; the console there reads #74706a ~ fConsole)
  fWood: { c: '#3e332d', r: 0.38, l: LAYER.fWood },
  fDoor: { c: '#736c65', r: 0.45, l: LAYER.plastic },
  fInner: { c: '#6a635d', r: 0.5, l: LAYER.plastic },       // QA r3: +15 %, ottoman base / aisle box read #474141 vs omaat_f11 #70635c
  fFabric: { c: '#6a6362', r: 0.92, l: LAYER.fTweed },      // QA r3: +12 % (omaat_f13 seat #8c7f76 in cabin light)
  fLeather: { c: '#4f4b49', r: 0.48, l: LAYER.leather },
  fFlap: { c: '#666864', r: 0.45, l: LAYER.leather },       // near-neutral warm grey flap, omaat_f13 #7b796f / f2 #5d5d59 (QA r3)
  fCap: { c: '#8a8272', r: 0.42, l: LAYER.plastic },
  fConsole: { c: '#7a736c', r: 0.45, l: LAYER.plastic },
  fCushionBlue: { c: '#7c72b6', r: 0.85, l: LAYER.fabric },
  fShelf: { c: '#3a302a', r: 0.35, l: LAYER.fWood },
  fWarm: { c: '#ffe7c4', r: 0.5, e: 0.55 },
  fLed: { c: '#f4f1ea', r: 0.5, e: 0.7 },
};

function loftAt(B, secs, xf, mat, seg = 4) { B.add(gLoft(secs, seg), xf, mat); }
const SEC = (y, w, d, z = 0, r = 0.03, x = 0) => ({ y, w, d, z, r, x });
const X = (...m) => m.reduce((a, b) => M4.mul(a, b));

// Product builders: 09a_econ.js, 09b_py.js, 09c_room.js, 09d_suite.js (concatenated after this file by build.py).

function mirrorGeo(geo) {
  const g = { p: Array.from(geo.pos), n: Array.from(geo.nrm), u: Array.from(geo.uv), i: [] };
  for (let k = 0; k < g.p.length; k += 3) { g.p[k] = -g.p[k]; g.n[k] = -g.n[k]; }
  const rects = Object.values(ATL.rects);
  for (let k = 0; k < g.u.length / 2; k++) {
    if (geo.mat[k * 4 + 2] < 13 || geo.mat[k * 4 + 2] > 15) continue;
    const u = g.u[k * 2], v = g.u[k * 2 + 1];
    const r = rects.find((q) => u >= q[0] - 1e-5 && u <= q[2] + 1e-5 && v >= q[1] - 1e-5 && v <= q[3] + 1e-5);
    if (r) g.u[k * 2] = r[0] + r[2] - u;
  }
  for (let t = 0; t < geo.idx.length; t += 3) g.i.push(geo.idx[t], geo.idx[t + 2], geo.idx[t + 1]);
  const b = geo.bounds;
  return { pos: new Float32Array(g.p), nrm: new Float32Array(g.n), uv: new Float32Array(g.u), col: geo.col, mat: geo.mat, idx: g.i, bounds: [[-b[1][0], b[0][1], b[0][2]], [-b[0][0], b[1][1], b[1][2]]] };
}

// ---------------- per-kind helpers used by the app (pick boxes, eyes, beds) ----------------
function unitXF(s) { return s.kind === 'room' ? M4.trs(s.ux, 0, s.uz) : M4.trs(s.x, 0, s.z); }
function localToWorld(s, p) { const q = [s.mir ? -p[0] : p[0], p[1], p[2]]; return M4.point(unitXF(s), q); }
function seatPickBox(s) {
  if (s.kind === 'econ') return [s.x - 0.24, s.x + 0.24, 0, 1.22, s.z - 0.5, s.z + 0.09];
  if (s.kind === 'py') return [s.x - 0.28, s.x + 0.28, 0, 1.32, s.z - 0.56, s.z + 0.12];
  let a, b;
  if (s.kind === 'room') { a = s.odd ? [-0.585, 0, -1.345] : [-0.12, 0, -0.55]; b = s.odd ? [0.10, 1.12, 0.55] : [0.585, 1.12, 1.345]; }
  else { const hx = (s.pos === 'center' ? 1.10 : 1.24) / 2; a = [-hx, 0, -2.2]; b = [hx, 1.3, 0]; }
  const p = localToWorld(s, a), q = localToWorld(s, b);
  return [Math.min(p[0], q[0]), Math.max(p[0], q[0]), 0, b[1], Math.min(p[2], q[2]), Math.max(p[2], q[2])];
}
function seatEye(s, bed) {
  if (s.kind === 'econ') return { pos: [s.x, 1.15, s.z - 0.2], yaw: 0, pitch: -0.1 };
  if (s.kind === 'py') return { pos: [s.x, 1.18, s.z - 0.24], yaw: 0, pitch: -0.1 };
  if (s.kind === 'room') {
    const p = s.odd ? (bed ? [-0.24, 0.78, -1.0] : [-0.24, 1.13, -1.0]) : (bed ? [0.20, 0.78, 1.0] : [0.20, 1.13, 1.0]);
    return { pos: localToWorld(s, p), yaw: s.odd ? Math.PI : 0, pitch: bed ? -0.1 : -0.12 };
  }
  const hx = (s.pos === 'center' ? 1.10 : 1.24) / 2;
  const seatX = -hx + 0.03 + (s.pos === 'center' ? 0.14 : 0.19) + 0.08 + 0.325;
  const p = bed ? [seatX, 0.80, -0.5] : [seatX, 1.17, -0.42];
  return { pos: localToWorld(s, p), yaw: 0, pitch: bed ? -0.12 : -0.1 };
}
function seatBedCenter(s) {
  if (s.kind === 'room') return localToWorld(s, s.odd ? [-0.26, 0.45, -0.4] : [0.24, 0.45, 0.38]);
  if (s.kind === 'suite') return localToWorld(s, [-0.1, 0.45, -1.1]);
  return [s.x, 0.45, s.z - 0.5];
}
const seatHasBed = (s) => s.kind === 'room' || s.kind === 'suite';

function buildSeats(gl, layout) {
  const meshes = {};
  const inst = {};
  const push = (key, m, tint, ref) => { (inst[key] = inst[key] || { mats: [], tints: [], refs: [] }); inst[key].mats.push(m); inst[key].tints.push(tint); inst[key].refs.push(ref); };
  const rnd = mulberry32(777);
  const screenVar = () => [1, 1, 1, Math.floor(rnd() * 4)];
  const byRow = {};
  for (const s of layout.seats) (byRow[s.row] = byRow[s.row] || []).push(s);
  const pairsDone = new Set();
  for (const ss of Object.values(byRow)) {
    const k0 = ss[0].kind;
    if (k0 === 'suite') {
      for (const s of ss) {
        const key = 'suite' + (s.pos === 'center' ? 'C' : 'W') + (s.mir ? 'M' : '');
        s.meshKey = key;
        push(key, M4.trs(s.x, 0, s.z), screenVar(), s);
      }
      continue;
    }
    if (k0 === 'room') {
      for (const s of ss) {
        const key = 'room' + (s.odd ? 'O' : 'E') + (s.mir ? 'M' : '');
        s.meshKey = key;
        push(key, M4.trs(s.ux, 0, s.uz), screenVar(), s);
        const pk = s.uz.toFixed(3);
        if (!pairsDone.has(pk)) { pairsDone.add(pk); push('roomDiv', M4.trs(0, 0, s.uz), [1, 1, 1, 0], null); }
      }
      continue;
    }
    const blocks = [ss.filter((s) => s.x < -1.1), ss.filter((s) => Math.abs(s.x) <= 1.1), ss.filter((s) => s.x > 1.1)];
    for (const b of blocks) {
      if (!b.length) continue;
      const cx = b.reduce((a, s) => a + s.x, 0) / b.length;
      const n = b.length;
      let key = (k0 === 'py' ? 'py' : 'y') + n;
      if (b[0].exitRow) key += 'x';                        // exit row: screen in the armrest (none in the back)
      if (b.some((s) => s.row === 42)) key += 'l';          // last row: no footrest behind
      b.forEach((s) => { s.meshKey = key; });
      push(key, M4.trs(cx, 0, b[0].z), screenVar(), b);
    }
  }
  const geos = {
    roomO: (l) => (l ? roomPartFar('O') : roomPart('O')), roomOM: (l) => mirrorGeo(l ? roomPartFar('O') : roomPart('O')),
    roomE: (l) => (l ? roomPartFar('E') : roomPart('E')), roomEM: (l) => mirrorGeo(l ? roomPartFar('E') : roomPart('E')),
    roomDiv: () => roomDivider(),
    suiteW: (l) => (l ? suiteFar() : suiteUnit()), suiteWM: (l) => mirrorGeo(l ? suiteFar() : suiteUnit()),
    suiteC: (l) => (l ? suiteFar({ w: 1.10, center: true }) : suiteUnit({ w: 1.10, center: true })), suiteCM: (l) => mirrorGeo(l ? suiteFar({ w: 1.10, center: true }) : suiteUnit({ w: 1.10, center: true })),
  };
  const econGeo = (key, lod) => {
    const kind = key.startsWith('py') ? 'py' : 'y';
    const n = +key.replace(/[^0-9]/g, '');
    const opts = { noScreen: key.includes('x'), footrest: !key.includes('l') };
    if (kind === 'py') return lod ? pyUnitFar(n) : pyUnit(n, false, opts);
    return lod ? econUnitFar(n) : econUnit(n, false, opts);
  };
  const groups = {};
  for (const [key, v] of Object.entries(inst)) {
    const hasLod = key !== 'roomDiv';
    const n = v.mats.length;
    const master = new Float32Array(n * 20);
    v.mats.forEach((m, i) => { master.set(m, i * 20); master.set(v.tints[i], i * 20 + 16); });
    const gen = geos[key] || ((l) => econGeo(key, l));
    const hiGeo = gen(false);
    const hi = gl.mesh(hiGeo, { name: key, layer: 'seats', instances: v.mats, tints: v.tints });
    const lo = hasLod ? gl.mesh(gen(true), { name: key + 'Lo', layer: 'seats', instances: [], castShadow: false }) : null;
    groups[key] = { key, hi, lo, master, n, refs: v.refs, dirty: true, geo: hiGeo, mats: v.mats, nearK: /^(y|py)/.test(key) ? 0.66 : 1.25 };
    meshes[key] = hi;
    if (lo) meshes[key + 'Lo'] = lo;
  }
  // bed variants (shown for the one seat that is lying flat)
  const bedGeo = {
    roomO: () => roomPart('O', { bed: true }), roomOM: () => mirrorGeo(roomPart('O', { bed: true })),
    roomE: () => roomPart('E', { bed: true }), roomEM: () => mirrorGeo(roomPart('E', { bed: true })),
    suiteW: () => suiteUnit({ bed: true }), suiteWM: () => mirrorGeo(suiteUnit({ bed: true })),
    suiteC: () => suiteUnit({ w: 1.10, center: true, bed: true }), suiteCM: () => mirrorGeo(suiteUnit({ w: 1.10, center: true, bed: true })),
  };
  for (const [k, f] of Object.entries(bedGeo)) meshes['bed_' + k] = gl.mesh(f(), { name: 'bed_' + k, layer: 'seats', instances: [] });
  // seat-number plaques: dark rounded tiles with lit characters lying FLAT on the aisle-corner cap, reading from the aisle
  // (Suite: forward end of the wardrobe cap, omaat_f58 / f60 / f7, tpa_IMG_0220, f_17301; Room: top of the aisle-end
  // post, c_27313 '17E' / '18D', c_27314 / 27315, omaat_room_14). World space, not instanced.
  const T = new Builder();
  const tagGlow = { c: '#ffffff', r: 0.4, l: LAYER.atlasGlow, e: 0.3 };
  for (const s of layout.seats) {
    if (!ATL.rects['tag' + s.id]) continue;
    let p, plate;
    // QA r2: neutral grey rounded squares slightly lighter than the cap (c_27314 cap #878787)
    if (s.kind === 'room') { p = localToWorld(s, [0.545, ROOM.wall + 0.0205, s.odd ? -0.50 : -0.06]); plate = '#6b6e72'; }
    else { const hx = (s.pos === 'center' ? 1.10 : 1.24) / 2; p = localToWorld(s, [hx - 0.08, 1.30 + 0.0625, -0.80]); plate = '#2b2b2e'; }
    const face = s.mir ? -1 : 1;             // text top points away from the aisle
    const room = s.kind === 'room';
    T.add(room ? gRBox(0.055, 0.004, 0.065, 0.012, 1) : gRBox(0.032, 0.004, 0.06, 0.008, 1), M4.trs(p[0], p[1] + 0.002, p[2]), { c: plate, r: 0.45 });
    T.add(room ? gQuad(0.058, 0.03) : gQuad(0.055, 0.028), M4.trs(p[0], p[1] + 0.0045, p[2], face * Math.PI / 2, -Math.PI / 2), tagGlow, atlasUV('tag' + s.id));
  }
  meshes.seatTags = gl.mesh(T.build(), { name: 'seatTags', layer: 'seats', castShadow: false });
  return { meshes, groups };
}

// Distance LOD + coarse view culling for seat instances
function updateSeatLOD(G, groups, cam, opts = {}) {
  const near = opts.near ?? 9.5;
  const [px, py, pz] = cam.pos;
  const fwd = cam.fwd;
  const cosCull = opts.cosCull ?? -1;
  for (const g of Object.values(groups)) {
    const hiBuf = g.hiBuf || (g.hiBuf = new Float32Array(g.n * 20));
    const loBuf = g.loBuf || (g.loBuf = new Float32Array(g.n * 20));
    let nh = 0, nl = 0;
    for (let i = 0; i < g.n; i++) {
      const o = i * 20;
      const x = g.master[o + 12] - px, y = g.master[o + 13] + 0.6 - py, z = g.master[o + 14] - pz;
      if (g.master[o + 13] < -10) continue;
      const d = Math.hypot(x, y, z);
      if (d > 3.0 && fwd && (x * fwd[0] + y * fwd[1] + z * fwd[2]) / d < cosCull) continue;
      if (!g.lo || (d < near * g.nearK && !opts.allLo)) { hiBuf.set(g.master.subarray(o, o + 20), nh * 20); nh++; }
      else { loBuf.set(g.master.subarray(o, o + 20), nl * 20); nl++; }
    }
    G.setInstancesRaw(g.hi, hiBuf, nh);
    if (g.lo) G.setInstancesRaw(g.lo, loBuf, nl);
    g.dirty = false;
  }
}
function groupSetTint(g, i, t) { g.master.set(t, i * 20 + 16); g.dirty = true; }
function groupSetMatrix(g, i, m) { g.master.set(m, i * 20); g.dirty = true; }

// Studio catalogue of units for design review
const UNITS = {
  econ3: () => econUnit(3),
  econ4: () => econUnit(4),
  py2: () => pyUnit(2),
  py4: () => pyUnit(4),
  roomO: () => roomPart('O'),
  roomE: () => roomPart('E'),
  roomPair: () => { const B = new Builder(); B.addBuilt(roomPart('O')); B.addBuilt(roomPart('E')); return B.build(); },
  roomBedO: () => { const B = new Builder(); B.addBuilt(roomPart('O', { bed: true })); B.addBuilt(roomPart('E')); return B.build(); },
  roomCentre: () => { const B = new Builder(); B.addBuilt(mirrorGeo(roomPart('O')), M4.trs(-0.585, 0, 0)); B.addBuilt(mirrorGeo(roomPart('E')), M4.trs(-0.585, 0, 0)); B.addBuilt(roomPart('O'), M4.trs(0.585, 0, 0)); B.addBuilt(roomPart('E'), M4.trs(0.585, 0, 0)); B.addBuilt(roomDivider()); return B.build(); },
  suiteW: () => suiteUnit(),
  suiteBed: () => suiteUnit({ bed: true }),
  suiteC: () => { const B = new Builder(); B.addBuilt(mirrorGeo(suiteUnit({ w: 1.10, center: true })), M4.trs(-0.56, 0, 0)); B.addBuilt(suiteUnit({ w: 1.10, center: true }), M4.trs(0.56, 0, 0)); return B.build(); },
};
