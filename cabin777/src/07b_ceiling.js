// ------------------------------------------------------------------
// Ceilings (777 Signature Interior): curved aisle panels between the outboard and centre bins with the cove
// up-light and a slotted light/air grille only along the OUTBOARD bin top (b_lalf_c119, b_sany_y12/y22 both aisles,
// thrifty_j_cabin-1, sany_py_10, y_47300 [V]; y_47301 seems to show it on the centre side - see questions_ceiling); faint panel joints on the 2-frame grid, a raised
// rounded-rect panel and a small lens fitting on every panel (sany_10/11/12 [V]), flush EXIT signs on the header
// at the zone ends over the aisles near exits (roame THE Suite aisle, y_47300 [V]); raised curved ceilings in the
// door areas; flat over monuments
// ------------------------------------------------------------------
const VAULT_A = [1.655, 2.232], VAULT_B = [0.735, 2.262], VAULT_CROWN = 2.44;
function vaultY(t) {
  const s = Math.sin(Math.PI * clamp(t, 0, 1));
  return lerp(VAULT_A[1], VAULT_B[1], t) + (VAULT_CROWN - (VAULT_A[1] + VAULT_B[1]) / 2) * Math.pow(s, 0.7);
}
function vaultAt(t) {
  const x = lerp(VAULT_A[0], VAULT_B[0], t), y = vaultY(t);
  const e = 0.002;
  const t0 = clamp(t - e, 0, 1), t1 = clamp(t + e, 0, 1);
  const dx = lerp(VAULT_A[0], VAULT_B[0], t1) - lerp(VAULT_A[0], VAULT_B[0], t0), dy = vaultY(t1) - vaultY(t0);
  const l = Math.hypot(dx, dy) || 1;
  return [x, y, -dy / l, dx / l];
}
const VAULT = (() => {
  const pts = [[1.70, 2.236], [1.668, 2.244]];
  const N = 26;
  for (let k = 0; k <= N; k++) { const [x, y] = vaultAt(k / N); pts.push([x, y]); }
  pts.push([0.722, 2.268], [0.70, 2.262]);
  return pts;
})();

const FRAME = CAB.win.pitch;
// slotted grille on the outboard side only (see header), inboard of a bright cove diffuser band 1.5-3x the grille
// width that runs from the bin crest to the grille (b_lalf_c119, b_sany_y22 [V ratio]): grille at t = 0.20, diffuser
// t 0.015..0.16 [D]; w 0.08 m [A]. 4-5 fore-aft slots in segments of ~0.5 m (2 per 2-frame panel, a bridge on every
// panel joint) with ~25 mm solid bridges (b_lalf_c119 close-up, sany_py_10 [V pattern, A lengths])
const TROUGH = { ts: [0.20], w: 0.08, seg: 2, gap: 0.025, cove: [0.015, 0.16] };
function zoneModules(z0, z1, target = 2 * FRAME) {
  const n = Math.max(1, Math.round((z1 - z0) / target));
  const L = (z1 - z0) / n, b = [];
  for (let k = 0; k <= n; k++) b.push(z0 + L * k);
  return b;
}

// ceiling decals painted into the shared atlas after 06_atlas has drawn it (the atlas texture is uploaded right after
// buildAtlas, before the ceiling is built):
//  - 'exitJ': ANA's bilingual ceiling EXIT sign '← 非常口 EXIT →', dark red on a light face, ~4:1
//    (up_F_Forward-Look, sign over the door-1 cross-aisle [V text/colours]; 280x72 px, red #c21e1e [A shade])
//  - 'grille': the slotted grille as a texture across the strip: 5 thin dark fore-aft slits #464a50 (5 of every 12 px, w2a) between white bars
//    #efeeea (b_lalf_c119 close-up [V look]); constant along the run, so it cannot alias into a moire.
function paintCeilingDecals(A) {
  const g = A.canvas.getContext('2d'), S = A.canvas.width;
  const put = (name, x, y, w, h) => { A.rects[name] = [x / S, y / S, (x + w) / S, (y + h) / S]; };
  // free column under the four seatback-screen variants (x 0..320, y >= 720)
  let x = 8, y = 732;
  g.fillStyle = '#f4f1ea'; g.fillRect(x, y, 280, 72);
  g.fillStyle = '#c21e1e'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.font = '800 34px "Helvetica Neue", Helvetica, Arial, "Hiragino Sans", "Noto Sans JP", "WenQuanYi Zen Hei", sans-serif';
  g.fillText('非常口 EXIT', x + 140, y + 38, 200);
  for (const s of [-1, 1]) {           // arrows at both ends
    const ax = x + 140 + s * 118;
    g.beginPath(); g.moveTo(ax + s * 14, y + 36); g.lineTo(ax - s * 2, y + 24); g.lineTo(ax - s * 2, y + 48); g.closePath(); g.fill();
    g.fillRect(Math.min(ax - s * 2, ax - s * 16), y + 33, 14, 6);
  }
  put('exitJ', x, y, 280, 72);
  // grille slots across a 64 px tall rect (u along the run is constant), with a white margin for the mips
  y = 816;
  g.fillStyle = '#efeeea'; g.fillRect(x, y, 48, 80);
  g.fillStyle = '#464a50';
  for (let i = 0; i < 5; i++) g.fillRect(x, y + 12 + i * 12, 48, 5);
  put('grille', x + 16, y + 8, 16, 64);
}
{ const base = buildAtlas; buildAtlas = function (layout) { const A = base(layout); paintCeilingDecals(A); return A; }; }

const CEILMAT = {
  vault: { c: '#f3f2ee', r: 0.82, l: 12, e: 0.05 },
  seam: { c: '#d6d8da', r: 0.8 },
  trough: { c: '#7d8288', r: 0.7 },   // dark slots in a white frame (sany_10/11 [V])
  troughRim: { c: '#e9e8e4', r: 0.45, l: LAYER.plastic },
  slat: { c: '#ffffff', r: 0.5, l: LAYER.atlasLit },   // stripe texture carries the slat/slot colours
  // emergency light: light frame round a grey lens slot (b_lalf_c119 [V], w2a)
  emerg: { c: '#8e9297', r: 0.3, e: 0.05 },
  emergBase: { c: '#eceae6', r: 0.5, l: LAYER.plastic, e: 0.06 },
  // per-panel raised panel: lit by the same cove wash as the vault around it (sany_10/11 show it barely darker) [A e]
  bezel: { c: '#f1f0ec', r: 0.7, l: LAYER.plastic, e: 0.12 },
  bezelIn: { c: '#d9d9d5', r: 0.7, l: LAYER.grille, e: 0.06 },   // recessed perforated slot [A tone]
  flat: { c: '#efeeea', r: 0.72, l: LAYER.plastic },
  lightPanel: { c: '#fffaf0', r: 0.5, e: 0.45 },
  // narrow warm fore-aft light strip along the edge of the flat door-area panel (up_F_Forward-Look [V shape, colour])
  lightStrip: { c: '#fff4d6', r: 0.5, e: 0.8 },
  // cove diffuser band on the cove LED circuit (layer 12 = u_led): near white like the c119 / y22 band [V]
  cove: { c: '#ffffff', r: 0.5, l: 12, e: 0.17 },
  signBox: { c: '#e2e1dd', r: 0.45, l: LAYER.plastic },   // light housing (thrifty_j_cabin-1 header sign [V])
};

function profileRibbon(prof, side, z, dz, off) {
  const g = raw();
  for (let k = 0; k < prof.length; k++) {
    const a = prof[Math.max(0, k - 1)], b = prof[Math.min(prof.length - 1, k + 1)];
    const tx = b[0] - a[0], ty = b[1] - a[1], l = Math.hypot(tx, ty) || 1;
    let nx = -ty / l, ny = tx / l;
    if (ny > 0) { nx = -nx; ny = -ny; }
    const x = (prof[k][0] + nx * off) * side, y = prof[k][1] + ny * off;
    g.p.push(x, y, z - dz / 2, x, y, z + dz / 2);
    g.n.push(nx * side, ny, 0, nx * side, ny, 0); g.u.push(0, 0, 1, 0);
  }
  for (let k = 0; k < prof.length - 1; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
  return fixWinding(g);
}
function vaultStrip(t, side, z0, z1, width, off) {
  const [x, y, nx, ny] = vaultAt(t);
  const tx = -ny, ty = nx;
  const g = raw();
  for (const s of [-0.5, 0.5]) for (const z of [z0, z1]) {
    g.p.push((x + tx * width * s + nx * off) * side, y + ty * width * s + ny * off, z);
    g.n.push(nx * side, ny, 0); g.u.push(s + 0.5, z);
  }
  g.i.push(0, 1, 3, 0, 3, 2);
  return fixWinding(g);
}
// rounded rectangle (w across the aisle along the arc, d along the cabin, corner radius r) conforming to the vault,
// offset off below it: a flat box would sink into the arch at its ends
function vaultPanel(tc, side, zc, w, d, r, off, n = 10) {
  const e = 0.01, a = vaultAt(tc - e), b = vaultAt(tc + e), dsdt = Math.hypot(b[0] - a[0], b[1] - a[1]) / (2 * e);
  const g = raw();
  // columns concentrated in the rounded ends (n/2 per corner, sine-spaced) so the ends read round, not octagonal
  const m = Math.max(2, n >> 1), us = [];
  for (let j = 0; j <= m; j++) { const c = w / 2 - r + r * Math.sin((j / m) * Math.PI / 2); us.push(-c, c); }
  us.sort((p, q) => p - q);
  n = us.length - 1;
  for (let k = 0; k <= n; k++) {
    const u = us[k], [x, y, nx, ny] = vaultAt(tc + u / dsdt);
    const q = Math.max(0, Math.abs(u) - (w / 2 - r)), h = d / 2 - r + Math.sqrt(Math.max(0, r * r - q * q));
    for (const z of [zc - h, zc + h]) { g.p.push((x + nx * off) * side, y + ny * off, z); g.n.push(nx * side, ny, 0); g.u.push(k / n, z); }
  }
  for (let k = 0; k < n; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
  return fixWinding(g);
}
function vaultXF(t, side, z, off = 0) {
  const [x, y, nx, ny] = vaultAt(t);
  const ang = Math.atan2(nx * side, -ny);
  return M4.trs((x + nx * off) * side, y + ny * off, z, 0, 0, ang);
}

function buildCeilings(upper, layout) {
  const zones = layout.zones;
  for (let zi = 0; zi < zones.length; zi++) {
    const zn = zones[zi];
    const z0 = zn.z0, z1 = zn.z1;
    if (zn.type === 'seat') {
      const mods = zoneModules(z0, z1);
      for (const side of [-1, 1]) {
        // curved aisle panel; the outboard cove LED washes it from that edge only, extra glow beside the grille;
        // the vault fades toward the plain centre-bin crease (b_sany_y22: #cfc8bb by the cove, much darker at the
        // centre bin in the same exposure [V]; floor 0.08 [A]: w2a found 0.04 too dark vs y_47300)
        const xg = lerp(VAULT_A[0], VAULT_B[0], TROUGH.ts[0]);
        const eFn = (p) => {
          const ax = Math.abs(p[0]);
          if (ax > 1.66) return 0.85;
          if (ax < 0.73) return 0.08;
          return 0.08 + 0.26 * Math.exp(-Math.max(xg - ax, 0) / 0.16) + 0.30 * Math.exp(-Math.abs(ax - xg) / 0.08);
        };
        const prof = VAULT.map(([x, y]) => [x * side, y]);
        upper.add(gSweep(prof, z0, z1, { side: side > 0 ? 1 : -1, zsteps: mods.length - 1 }), null, { ...CEILMAT.vault, eFn });
        for (let k = 1; k < mods.length - 1; k++) upper.add(profileRibbon(VAULT.slice(2, -2), side, mods[k], 0.008, 0.0015), null, CEILMAT.seam);
        // cove diffuser: a continuous near-white lit band between the outboard bin crest and the grille
        { const [c0, c1] = TROUGH.cove, tm = (c0 + c1) / 2, a = vaultAt(c0), b = vaultAt(c1);
          upper.add(vaultStrip(tm, side, z0 + 0.03, z1 - 0.03, Math.hypot(b[0] - a[0], b[1] - a[1]), 0.0014), null, CEILMAT.cove); }
        // slotted grille flush against the outboard bin top: white frame, dark channel, one slotted strip per
        // segment (TROUGH.seg per panel) between solid white bridges
        const sl = raw(), sg = raw();
        const push = (g, q) => { const b = g.p.length / 3; g.p.push(...q.p); g.n.push(...q.n); g.u.push(...q.u); g.i.push(...q.i.map((v) => v + b)); };
        const gr = ATL.rects.grille, tg = TROUGH.ts[0];
        upper.add(vaultStrip(tg, side, z0 + 0.03, z1 - 0.03, TROUGH.w + 0.024, 0.0012), null, CEILMAT.troughRim);
        upper.add(vaultStrip(tg, side, z0 + 0.04, z1 - 0.04, TROUGH.w, 0.0024), null, CEILMAT.trough);
        for (let k = 0; k < mods.length - 1; k++) {
          const L = (mods[k + 1] - mods[k]) / TROUGH.seg;
          for (let j = 0; j < TROUGH.seg; j++) {
            const za = mods[k] + j * L + TROUGH.gap / 2, zb = za + L - TROUGH.gap;
            const q = vaultStrip(tg, side, Math.max(za, z0 + 0.04), Math.min(zb, z1 - 0.04), TROUGH.w - 0.006, 0.0034);
            // uv: across (0..1) -> atlas v over the 5 slots, along the run -> a constant atlas u
            for (let i = 0; i < q.u.length; i += 2) { const across = side > 0 ? q.u[i] : 1 - q.u[i]; q.u[i] = (gr[0] + gr[2]) / 2; q.u[i + 1] = gr[1] + across * (gr[3] - gr[1]); }
            push(sl, q);
            if (zb + TROUGH.gap < z1 - 0.04) push(sg, vaultStrip(tg, side, zb, zb + TROUGH.gap, TROUGH.w, 0.0034));
          }
        }
        upper.add(sl, null, CEILMAT.slat, (k, g) => [g.u[k * 2], g.u[k * 2 + 1]]);
        upper.add(sg, null, CEILMAT.troughRim);
        // every panel: a raised rounded-rect speaker fitting near the centre-bin side (long side across the aisle,
        // ~3.4:1, small corner radii, a thin rim round a perforated face: b_lalf_c119 close-up, b_sany_y12/y22 [V
        // shape]; 0.34 x 0.10 m [A]) and a small dark-windowed fitting with a lens near mid-vault (the emergency light)
        for (let k = 0; k < mods.length - 1; k++) {
          const zc = (mods[k] + mods[k + 1]) / 2;
          upper.add(vaultPanel(0.78, side, zc, 0.34, 0.10, 0.025, 0.0015, 12), null, CEILMAT.seam);
          upper.add(vaultPanel(0.78, side, zc, 0.332, 0.092, 0.022, 0.003, 12), null, CEILMAT.bezel);
          upper.add(vaultPanel(0.78, side, zc, 0.312, 0.074, 0.014, 0.0036, 12), null, CEILMAT.bezelIn);
          upper.add(gRBox(0.07, 0.008, 0.04, 0.005, 1), vaultXF(0.45, side, zc + 0.25, 0.003), CEILMAT.emergBase);
          upper.add(gRBox(0.05, 0.004, 0.022, 0.004, 1), vaultXF(0.45, side, zc + 0.25, 0.0068), CEILMAT.emerg);
        }
        // EXIT signs fixed flush under the ceiling on the zone-end header over the aisle, facing into the zone;
        // wide bilingual '← 非常口 EXIT →' face ~4:1 (up_F_Forward-Look [V]; 0.36 x 0.09 m [A])
        const prev = zones[zi - 1], next = zones[zi + 1];
        const nearDoor = (zz) => zones.some((q) => q.type === 'door' && Math.abs((q.z0 + q.z1) / 2 - zz) < 2.4);
        const signs = [];
        if (prev && (prev.type === 'door' || nearDoor(z0))) signs.push([z0 + 0.03, 1]);
        if (next && (next.type === 'door' || nearDoor(z1))) signs.push([z1 - 0.03, -1]);
        for (const [zs, f] of signs) {
          const [x] = vaultAt(0.5), y = vaultY(0.5) - 0.07, X = x * side;
          upper.add(gRBox(0.36, 0.09, 0.03, 0.01, 1), M4.trs(X, y, zs), CEILMAT.signBox);
          for (const g of [f, -f]) upper.add(gQuad(0.33, 0.08), M4.trs(X, y, zs + g * 0.0155, g > 0 ? 0 : Math.PI), MAT.exitGlow, atlasUV('exitJ'));   // double-faced
        }
      }
      upper.add(gBox(1.30, 0.02, z1 - z0 + 0.08), M4.trs(0, 2.325, (z0 + z1) / 2), MAT.ceiling);
      // header closures at the zone ends: the open vault sweep let the sky show between the centre-bin end, the vault
      // and the door dome (w2b v3 leak)
      for (const side of [-1, 1]) {
        const poly = [...VAULT.map(([x, y]) => [x * side, y]), [VAULT[VAULT.length - 1][0] * side, 2.62], [VAULT[0][0] * side, 2.62]];
        for (const z of [z0 - 0.006, z1 + 0.006]) upper.add(gExtrude(poly, 0.01), M4.trs(0, 0, z), CEILMAT.flat);
      }
    } else if (zn.type === 'door') {
      const zc = (z0 + z1) / 2;
      for (const side of [-1, 1]) {
        const prof = DOME.map(([x, y]) => [x * side, y]);
        const eFn = (p) => { const ax = Math.abs(p[0]); return ax > 2.55 ? 0.5 : 0.07 + 0.16 * Math.exp(-(2.55 - ax) / 0.3); };   // w1: floor 0.03 read grey #c8c8c8
        upper.add(gSweep(prof, z0, z1, { side: side > 0 ? 1 : -1, zsteps: 2 }), null, { ...CEILMAT.vault, eFn });
      }
      // entry lights: two narrow fore-aft strips along the edges of the flat centre panel (up_F_Forward-Look [V];
      // 70 mm wide, x = ±0.55 [A])
      for (const s of [-1, 1]) upper.add(gRBox(0.07, 0.012, Math.max(0.2, z1 - z0 - 0.25), 0.02, 1), M4.trs(0.55 * s, 2.505, zc), CEILMAT.lightStrip);
      for (const dx of [-1.45, 1.45]) upper.add(gCyl(0.045, 0.045, 0.012, 14), M4.trs(dx, ceilOutline('door', dx) - 0.008, zc), { c: '#fffaf0', r: 0.4, e: 0.75 });
      // bilingual EXIT signs on the fascia facing fore and aft (up_F_Forward-Look [V]; 0.40 x 0.10 m face [A])
      for (const f of [-1, 1]) {
        const xf = M4.trs(0, 2.35, (f > 0 ? z1 : z0) + 0.012 * f, f > 0 ? 0 : Math.PI);
        upper.add(gRBox(0.44, 0.12, 0.03, 0.012, 1), M4.mul(xf, M4.trs(0, 0, -0.016)), CEILMAT.signBox);
        upper.add(gQuad(0.40, 0.10), xf, MAT.exitGlow, atlasUV('exitJ'));
      }
    } else {
      for (const side of [-1, 1]) {
        const prof = MONOC.map(([x, y]) => [x * side, y]);
        upper.add(gSweep(prof, z0, z1, { side: side > 0 ? 1 : -1 }), null, CEILMAT.flat);
      }
      const len = z1 - z0;
      if (len > 0.6) {
        upper.add(gBox(1.1, 0.003, Math.min(0.55, len * 0.5)), M4.trs(0, 2.2335, (z0 + z1) / 2), CEILMAT.lightPanel);   // near-flush (w2b: a 12 mm box read as a black frame)
        for (const s of [-1, 1]) upper.add(gCyl(0.04, 0.04, 0.01, 12), M4.trs(1.7 * s, 2.214, (z0 + z1) / 2), { c: '#fffaf0', r: 0.4, e: 0.7 });
      }
    }
  }
}
