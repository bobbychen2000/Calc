// ------------------------------------------------------------------
// Ceilings (777 Signature Interior): curved aisle panels between the outboard and centre bins with cove
// up-lighting at both edges and a slatted light/air grille run hard against a bin top edge (seen in y_47301,
// c_27312, sany_10/11/12 and a THE Suite aisle photo [V]); faint panel joints on the 2-frame grid, a raised
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
// slatted grilles run hard against both bin top edges: against the outboard bin in c_27312 and sany_10/11
// (right aisle looking fwd, left aisle looking aft), against the centre bin in y_47301 (right aisle looking aft) [V].
// Outboard t = 0.10: the vault's first ~5 cm (t < 0.06) sits behind the outboard door crest seen from the aisle,
// so the grille starts where the visible panel starts [D]; centre t = 0.96. w 0.08 m [A]. Slat runs of 0.55 m with
// 0.05 m solid bridges (breaks in the run in the y_47301 crop) [A lengths]
const TROUGH = { ts: [0.10, 0.96], w: 0.08, run: 0.6, gap: 0.05 };
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
//  - 'grille': the slatted light/air grille as a stripe texture (22 mm pitch, 13 mm white slat #efeeea / 9 mm dark
//    slot #7d8288, sany_10/11/12 [V look, A pitch]) so the mipmaps blend it into a fine even stripe at distance
//    instead of the zigzag moire of per-slat geometry. GRILLE_RUN metres of grille = GRILLE_PX canvas pixels.
const GRILLE_PITCH = 0.022, GRILLE_N = 25, GRILLE_PX = 10;
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
  // grille stripes, painted with a margin of the same pattern so the lower mip levels do not pick up the atlas grey
  y = 820;
  const W = GRILLE_N * GRILLE_PX;
  for (let i = -2; i < GRILLE_N + 2; i++) {
    g.fillStyle = '#7d8288'; g.fillRect(x + i * GRILLE_PX + 16, y, GRILLE_PX, 40);
    g.fillStyle = '#efeeea'; g.fillRect(x + i * GRILLE_PX + 16 + 2, y, 6, 40);
  }
  put('grille', x + 16, y + 16, W, 8);
}
{ const base = buildAtlas; buildAtlas = function (layout) { const A = base(layout); paintCeilingDecals(A); return A; }; }

const CEILMAT = {
  vault: { c: '#f3f2ee', r: 0.82, l: 12, e: 0.05 },
  seam: { c: '#c4c7ca', r: 0.8 },
  trough: { c: '#7d8288', r: 0.7 },   // dark slots in a white frame (sany_10/11 [V])
  troughRim: { c: '#e9e8e4', r: 0.45, l: LAYER.plastic },
  slat: { c: '#ffffff', r: 0.5, l: LAYER.atlasLit },   // stripe texture carries the slat/slot colours
  emerg: { c: '#fff7e8', r: 0.3, e: 0.2 },
  emergBase: { c: '#2a2e34', r: 0.4 },
  // per-panel raised panel: lit by the same cove wash as the vault around it (sany_10/11 show it barely darker) [A e]
  bezel: { c: '#f1f0ec', r: 0.7, l: LAYER.plastic, e: 0.12 },
  bezelIn: { c: '#e4e4e0', r: 0.6, l: LAYER.plastic, e: 0.08 },
  flat: { c: '#efeeea', r: 0.72, l: LAYER.plastic },
  lightPanel: { c: '#fffaf0', r: 0.5, e: 0.45 },
  // narrow warm fore-aft light strip along the edge of the flat door-area panel (up_F_Forward-Look [V shape, colour])
  lightStrip: { c: '#fff4d6', r: 0.5, e: 0.8 },
  signBox: { c: '#2a2e34', r: 0.45 },
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
  for (let k = 0; k <= n; k++) {
    const u = -w / 2 + (w * k) / n, [x, y, nx, ny] = vaultAt(tc + u / dsdt);
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
        // curved aisle panel; cove LEDs at both edges wash up onto it, extra glow beside the grille (c_27312, sany_11)
        const xg = TROUGH.ts.map((t) => lerp(VAULT_A[0], VAULT_B[0], t));
        const eFn = (p) => {
          const ax = Math.abs(p[0]);
          if (ax > 1.66 || ax < 0.73) return 0.85;
          const d = Math.min(1.655 - ax, (ax - 0.735) * 1.1);
          return Math.max(0.05 + 0.34 * Math.exp(-Math.max(d, 0) / 0.13), 0.05 + 0.5 * Math.exp(-Math.min(...xg.map((g) => Math.abs(ax - g))) / 0.10));
        };
        const prof = VAULT.map(([x, y]) => [x * side, y]);
        upper.add(gSweep(prof, z0, z1, { side: side > 0 ? 1 : -1, zsteps: mods.length - 1 }), null, { ...CEILMAT.vault, eFn });
        for (let k = 1; k < mods.length - 1; k++) upper.add(profileRibbon(VAULT.slice(2, -2), side, mods[k], 0.004, 0.0015), null, CEILMAT.seam);
        // slatted grilles flush against the bin tops: white frame, dark slot, one striped strip per slat run
        // (22 mm pitch in the atlas stripe, see paintCeilingDecals) between solid white bridges
        const sl = raw(), sg = raw();
        const push = (g, q) => { const b = g.p.length / 3; g.p.push(...q.p); g.n.push(...q.n); g.u.push(...q.u); g.i.push(...q.i.map((v) => v + b)); };
        const run = TROUGH.run - TROUGH.gap, gr = ATL.rects.grille;
        for (const tg of TROUGH.ts) {
          upper.add(vaultStrip(tg, side, z0 + 0.03, z1 - 0.03, TROUGH.w + 0.024, 0.0012), null, CEILMAT.troughRim);
          upper.add(vaultStrip(tg, side, z0 + 0.04, z1 - 0.04, TROUGH.w, 0.0024), null, CEILMAT.trough);
          for (let za = z0 + 0.05; za < z1 - 0.06; za += TROUGH.run) {
            const zb = Math.min(za + run, z1 - 0.05), q = vaultStrip(tg, side, za, zb, TROUGH.w - 0.006, 0.0034);
            // uv: u across (0..1) -> atlas v, z along the run -> atlas u (GRILLE_N slats per GRILLE_N * pitch)
            for (let k = 0; k < q.u.length; k += 2) {
              const across = q.u[k], along = (q.u[k + 1] - za) / (GRILLE_N * GRILLE_PITCH);
              q.u[k] = gr[0] + along * (gr[2] - gr[0]); q.u[k + 1] = gr[1] + across * (gr[3] - gr[1]);
            }
            push(sl, q);
            // solid white bridge after the run
            if (zb + TROUGH.gap < z1 - 0.05) push(sg, vaultStrip(tg, side, zb, zb + TROUGH.gap, TROUGH.w, 0.0034));
          }
        }
        upper.add(sl, null, CEILMAT.slat, (k, g) => [g.u[k * 2], g.u[k * 2 + 1]]);
        upper.add(sg, null, CEILMAT.troughRim);
        // every panel: raised rounded-rect panel near the centre-bin side (long side across the aisle) and a small
        // dark-windowed fitting with a lens near mid-vault (sany_10/11/12 [V]; sizes [A]); the lens fitting doubles
        // as the emergency light
        for (let k = 0; k < mods.length - 1; k++) {
          const zc = (mods[k] + mods[k + 1]) / 2;
          // n = 24 columns so the 25-30 mm corner radii read round, not octagonal (sany_11/12 [V])
          upper.add(vaultPanel(0.78, side, zc, 0.33, 0.15, 0.03, 0.0015, 24), null, CEILMAT.seam);
          upper.add(vaultPanel(0.78, side, zc, 0.322, 0.142, 0.027, 0.003, 24), null, CEILMAT.bezel);
          upper.add(vaultPanel(0.78, side, zc, 0.30, 0.12, 0.025, 0.0045, 24), null, CEILMAT.bezelIn);
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
          upper.add(gQuad(0.33, 0.08), M4.trs(X, y, zs + f * 0.0155, f > 0 ? 0 : Math.PI), MAT.exitGlow, atlasUV('exitJ'));
        }
      }
      upper.add(gBox(1.30, 0.02, z1 - z0), M4.trs(0, 2.325, (z0 + z1) / 2), MAT.ceiling);
    } else if (zn.type === 'door') {
      const zc = (z0 + z1) / 2;
      for (const side of [-1, 1]) {
        const prof = DOME.map(([x, y]) => [x * side, y]);
        const eFn = (p) => { const ax = Math.abs(p[0]); return ax > 2.55 ? 0.5 : 0.03 + 0.16 * Math.exp(-(2.55 - ax) / 0.3); };
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
        upper.add(gRBox(1.1, 0.012, Math.min(0.55, len * 0.5), 0.03, 1), M4.trs(0, 2.229, (z0 + z1) / 2), CEILMAT.lightPanel);
        for (const s of [-1, 1]) upper.add(gCyl(0.04, 0.04, 0.01, 12), M4.trs(1.7 * s, 2.214, (z0 + z1) / 2), { c: '#fffaf0', r: 0.4, e: 0.7 });
      }
    }
  }
}
