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
  const N = 48;   // w8b: finer arc, smoother falloff
  for (let k = 0; k <= N; k++) { const [x, y] = vaultAt(k / N); pts.push([x, y]); }
  pts.push([0.722, 2.268], [0.70, 2.262]);
  return pts;
})();

const FRAME = CAB.win.pitch;
// slotted grille on the outboard side only (see header), inboard of a bright cove diffuser band 1.5-3x the grille
// width that runs from the bin crest to the grille (b_lalf_c119, b_sany_y22 [V ratio]): grille at t = 0.24, diffuser
// t 0.004..0.215 [D]; w 0.05 m, slim mid-grey (w3b) [A]. 4-5 fore-aft slots in segments of ~0.5 m (2 per 2-frame panel, a bridge on every
// panel joint) with ~25 mm solid bridges (b_lalf_c119 close-up, sany_py_10 [V pattern, A lengths])
const TROUGH = { ts: [0.29], w: 0.045, seg: 3, gap: 0.022, cove: [0.004, 0.265] };   // w5b: from the aisle the band read only 1-1.4x the grille (c119 ~2x, rb_omaat_room37 ~3x) [V ratio]; 3 segments a panel (c120)
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
//  - 'grille': the slotted grille as a texture across the strip: 4 fore-aft slits #8a8e93 (w2a/w3b thin; w7a: c120 reads a backlit white louvre, ~210 mean) between white bars
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
  g.fillStyle = '#8a8e93';
  for (let i = 0; i < 4; i++) g.fillRect(x, y + 14 + i * 14, 48, 6);
  put('grille', x + 16, y + 8, 16, 64);
}
{ const base = buildAtlas; buildAtlas = function (layout) { const A = base(layout); paintCeilingDecals(A); return A; }; }

const CEILMAT = {
  vault: { c: '#e6e4df', r: 0.82, l: 12, e: 0.05 },   // w5a/w5b: vault 0.96..0.86 of the band, photos 0.83..0.58 (c119, c120, y22) [V ratio]
  seam: { c: '#d6d8da', r: 0.8 },
  rib: { c: '#ecebe7', r: 0.6, l: LAYER.plastic, e: 0.02 },   // raised light panel rib (c120, c119 [V]); ~1.1x the vault (w7a: 1.4x read as white lines)
  ribShadow: { c: '#c6c5c1', r: 0.8 },                          // its aft shadow lip [A]
  // door-3 cross-aisle: dark bronze recessed tray with downlights, a louvre and a speaker (b_lalf_c133/c134 [V]; #5c524d sampled under warm light)
  barTray: { c: '#5c524d', r: 0.35 },
  barSoffit: { c: '#4f4743', r: 0.4 },
  barFrame: { c: '#8a8079', r: 0.4 },   // tray edge: a mid-tone trim, not a white frame (c133; w6a dark, w6b light) [A]
  downlight: { c: '#fffaf0', r: 0.4, e: 0.85 },
  trough: { c: '#9a9ea3', r: 0.7 },   // dark slots in a white frame (sany_10/11 [V])
  troughRim: { c: '#e9e8e4', r: 0.45, l: LAYER.plastic, e: 0.19 },   // the bars glow with the cove behind them (c120 bars ~254) [V]; polish B: 0.2 took the lamp branch, white bars at night (ucr_room-night-lighting ceiling L13-55)
  slat: { c: '#ffffff', r: 0.5, l: LAYER.atlasLit, e: 0.3 },   // stripe texture carries the slat/slot colours
  // emergency light: light frame round a grey lens slot (b_lalf_c119 [V], w2a)
  emerg: { c: '#8e9297', r: 0.3, e: 0.05 },
  emergBase: { c: '#eceae6', r: 0.5, l: LAYER.plastic, e: 0.06 },
  // per-panel raised panel: lit by the same cove wash as the vault around it (sany_10/11 show it barely darker) [A e]
  bezel: { c: '#e6e4df', r: 0.7, l: LAYER.plastic },   // vault tone (c120 speaker 188 on a 188 vault; w6a/w6b: a bright plank)
  bezelIn: { c: '#dedcd7', r: 0.7, l: LAYER.plastic },   // smooth face (w9a: c120 shows no slats)   // perforated pocket a little darker than the vault (c120); baked with the vault since w7 [V look, A tone]
  bezelShadow: { c: '#b4b2ae', r: 0.8 },   // polish B (w14a-1): #8f8d89 read near-black once the vault brightened (c120 129 on 176)
  crestGroove: { c: '#a9acb1', r: 0.3, m: 0.3 },   // polish B (w14a-2): #86898e read 0.40 of the vault (v15 87 on 222; c120 ~0.75)
  crestHi: { c: '#d4d6d9', r: 0.25, m: 0.4 },   // metallic highlight along the channel's upper lip (c120 [V])   // vault/crest-rail channel (c120 [V look])
  flat: { c: '#efeeea', r: 0.72, l: LAYER.plastic },
  lightPanel: { c: '#fffaf0', r: 0.5, e: 0.3 },   // w11b: a flat 251 wedge beside the door-4 dome
  // narrow warm fore-aft light strip along the edge of the flat door-area panel (up_F_Forward-Look [V shape, colour])
  lightStrip: { c: '#fff4d6', r: 0.5, e: 0.8 },
  stripHousing: { c: '#cfcecb', r: 0.6 },   // recess round the door-area strips [A]
  ringLight: { c: '#d9d7d2', r: 0.4 },      // downlight trim ring [A]
  // cove diffuser band on the cove LED circuit (layer 12 = u_led): near white like the c119 / y22 band [V]
  cove: { c: '#ffffff', r: 0.5, l: 12, e: 0.36 },   // w6b: the inner half fell to 227 (c120 one bright field)   // the brightest thing in the ceiling (w3a)
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
function vaultPanel(tc, side, zc, w, d, r, off, n = 10, bow = 0) {
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
    const b = bow * (1 - Math.pow(2 * k / n - 1, 2));
    for (const z of [zc - h + b, zc + h + b]) { g.p.push((x + nx * off) * side, y + ny * off, z); g.n.push(nx * side, ny, 0); g.u.push(k / n, z); }
  }
  for (let k = 0; k < n; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
  return fixWinding(g);
}
// raised panel joint rib: runs across the vault from the cove, then turns forward on a radius R into the fore-aft crest
// rib along the centre-bin side (b_lalf_c120 / c119 looking forward: joints curve away from the camera into a rib along
// the crease [V shape]; R 0.3 m [A]).
// Built on the vault surface with its width perpendicular to the path, so the turned part keeps its width.
const RIB = { t0: 0.6, R: 0.3 }, RIB_T0 = TROUGH.ts[0] + 0.035;   // ribs stop at the grille frame (c120, w7a)
function ribPath() {
  const pts = []; let s = 0, prev = null, sTurn = null;
  for (let k = 0; k <= 60; k++) {
    const t = RIB_T0 + (1 - RIB_T0) * k / 60, [x, y, nx, ny] = vaultAt(t);
    if (prev) s += Math.hypot(x - prev[0], y - prev[1]);
    prev = [x, y];
    if (t >= RIB.t0 && sTurn === null) sTurn = s;
    const q = sTurn === null ? 0 : (s - sTurn) / RIB.R;
    if (q > 1) break;
    pts.push({ t, x, y, nx, ny, dz: -RIB.R * (1 - Math.sqrt(1 - q * q)) });
  }
  return pts;
}
const RIB_PATH = ribPath(), RIB_TEND = RIB_PATH[RIB_PATH.length - 1].t;
function vaultRib(side, z, w, off, dz0 = 0) {
  const g = raw(), P = RIB_PATH;
  for (let k = 0; k < P.length; k++) {
    const a = P[Math.max(0, k - 1)], b = P[Math.min(P.length - 1, k + 1)], p = P[k];
    const T = [(b.x - a.x) * side, b.y - a.y, b.dz - a.dz], N = [p.nx * side, p.ny, 0];
    let W = [N[1] * T[2] - N[2] * T[1], N[2] * T[0] - N[0] * T[2], N[0] * T[1] - N[1] * T[0]];
    const l = Math.hypot(...W) || 1; W = W.map((v) => v / l);
    if (W[2] < 0) W = W.map((v) => -v);
    const c = [(p.x + p.nx * off) * side, p.y + p.ny * off, z + p.dz + dz0];
    for (const h of [-w / 2, w / 2]) { g.p.push(c[0] + W[0] * h, c[1] + W[1] * h, c[2] + W[2] * h); g.n.push(...N); g.u.push(0, 0); }
  }
  for (let k = 0; k < P.length - 1; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
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
          if (ax > xg + TROUGH.w / 2 + 0.012) return 0.85;   // the cove field up to the grille (w7b)
          // polish B (from_integration r3): the cove-lit vault is the brightest large surface in the photos (vault / bin
          // 1.15-1.37: c_27312, y_47301, sany_10) but rendered 0.83-0.87 of the bins -> higher, flatter falloff [V ratio]
          // (0.14 / 0.10 + 0.10 exp(/0.35) rendered q06 vault L240, clipping the joint ribs)
          if (ax < 0.73) return 0.11;
          return 0.06 + 0.07 * Math.exp(-Math.max(xg - ax, 0) / 0.30);   // was 0.08 / 0.02 + 0.03 exp(/0.18) (w4a/w4b, w5b, w6a/w6b)
        };
        const prof = VAULT.map(([x, y]) => [x * side, y]);
        const v0 = upper.p.length / 3;
        upper.add(gSweep(prof, z0, z1, { side: side > 0 ? 1 : -1, zsteps: mods.length - 1 }), null, { ...CEILMAT.vault, eFn });
        // polish B w14b F1: fittings on the vault take its own emission (cove-LED layer + eFn), so they keep the vault tone in
        // every mood once the vault eFn rose (ribs 184 / speaker 178 on a 231 vault, night speaker 17 on 65; c120 188 on 188) [V]
        const onVault = (m, k = 1, d = 0) => ({ ...m, l: 12, e: 0.05, eFn: (p) => eFn(p) * k + d });
        // raised joint ribs (light face + aft shadow lip) turning forward into the crest rib (c120, w5a/w5b: flat hairlines)
        for (let k = 0; k < mods.length - 1; k++) {
          if (k) { upper.add(vaultRib(side, mods[k], 0.014, 0.004), null, onVault(CEILMAT.rib, 1, 0.01)); upper.add(vaultRib(side, mods[k], 0.005, 0.0022, 0.0085), null, CEILMAT.ribShadow); }
        }
        {   // crest rib along the centre-bin side, from the zone start to the last joint's turn
          const zb = mods.length > 2 ? mods[mods.length - 2] - RIB.R : z1 - 0.03;
          upper.add(vaultStrip(RIB_TEND, side, z0 + 0.03, zb, 0.014, 0.004), null, onVault(CEILMAT.rib, 1, 0.01));
          upper.add(vaultStrip(RIB_TEND + 0.012, side, z0 + 0.03, zb, 0.005, 0.0022), null, CEILMAT.ribShadow); }
        // dark metallic channel where the vault meets the centre-bin crest rail (c120 [V]; ~15 mm along the arc [A]).
        // Seen from the aisle the rail hides the bin face behind it, so the channel is the vault's own steep last strip
        // (w9a-w11b: boxes in 08_bins under the vault edge never showed)
        { // on the sweep's last chord (VAULT[N+2] -> VAULT[N+3]): the true arc bulges outside it there, so strips on vaultAt
          // sank behind the mesh (w12 red/green test); lower 65 % of the chord, against the rail, with a light top line
          const N = VAULT.length - 3, a = VAULT[N - 1], b = VAULT[N];
          const L = Math.hypot(a[0] - b[0], a[1] - b[1]), nx = (a[1] - b[1]) / L, ny = -(a[0] - b[0]) / L;   // aisle-side, downward normal
          const q = (u0, u1, off) => { const g = raw();
            for (const u of [u0, u1]) for (const z of [z0 + 0.03, z1 - 0.03]) {
              g.p.push((lerp(b[0], a[0], u) + nx * off) * side, lerp(b[1], a[1], u) + ny * off, z); g.n.push(nx * side, ny, 0); g.u.push(u, z); }
            g.i.push(0, 1, 3, 0, 3, 2); return fixWinding(g); };
          // polish B (w14a-2): 0.65 of the chord at #86898e read 0.40 of the brighter vault (c120 0.73-0.79) -> 0.45, lighter
          upper.add(q(0, 0.45, 0.003), null, CEILMAT.crestGroove);   // 1.2 mm sank into the smoothed sweep
          upper.add(q(0.45, 0.52, 0.003), null, CEILMAT.crestHi);
        }
        // cove diffuser: a continuous near-white lit band between the outboard bin crest and the grille
        // 4 facets following the arc: one flat chord sank its ends behind the curved vault, so only its middle read
        // bright (w7b: lit field 1-1.5x the grille, c120 ~3x)
        { const [c0, c1] = TROUGH.cove, NF = 4;
          for (let j = 0; j < NF; j++) {
            const ta = lerp(c0, c1, j / NF), tb = lerp(c0, c1, (j + 1) / NF), a = vaultAt(ta), b = vaultAt(tb);
            upper.add(vaultStrip((ta + tb) / 2, side, z0 + 0.03, z1 - 0.03, Math.hypot(b[0] - a[0], b[1] - a[1]) + 0.004, 0.0016), null, CEILMAT.cove);
          } }
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
        // shape]; 0.34 x 0.10 m [A]; t 0.70 clears the crest rib, w6b) and a small dark-windowed fitting with a lens near mid-vault (the emergency light)
        for (let k = 0; k < mods.length - 1; k++) {
          const zc = (mods[k] + mods[k + 1]) / 2;
          upper.add(vaultPanel(0.70, side, zc, 0.34, 0.10, 0.025, 0.0015, 12, 0.03), null, onVault(CEILMAT.bezel));   // outer ring in vault tone (c120 ~1.06x; w7a)
          upper.add(vaultPanel(0.70, side, zc, 0.332, 0.092, 0.022, 0.003, 12, 0.03), null, onVault(CEILMAT.bezel));
          upper.add(vaultPanel(0.70, side, zc, 0.312, 0.074, 0.014, 0.0036, 12, 0.03), null, onVault(CEILMAT.bezelIn, 0.92));
          // recess shadow: a dark crescent inside the rim along one long edge (c120 [V]; w8-w11: a faint pale bar)
          upper.add(vaultPanel(0.70, side, zc + 0.031, 0.30, 0.008, 0.004, 0.0039, 12, 0.03), null, CEILMAT.bezelShadow);
          upper.add(gRBox(0.07, 0.008, 0.04, 0.005, 1), vaultXF(0.45, side, zc + 0.25, 0.003), onVault(CEILMAT.emergBase));
          upper.add(gRBox(0.05, 0.004, 0.022, 0.004, 1), vaultXF(0.45, side, zc + 0.25, 0.0068), CEILMAT.emerg);
        }
        // baked falloff x0.85 at the grille -> x0.66 at the centre-bin crease, over the vault and everything on it (ribs,
        // speaker, emergency light: w7a found them 1.3-1.4x the vault unbaked); cove + grille keep full tone: emissive
        // alone cannot darken a lit white surface (b_sany_y22: ~0.8 -> ~0.6 of the band; c119/c120 0.83 -> 0.58) [D]
        { const xc = xg - (TROUGH.w + 0.024) / 2 - 0.001;
          for (let k = v0; k < upper.p.length / 3; k++) {
            const ax = Math.abs(upper.p[k * 3]);
            const f = ax > xc ? 1 : lerp(0.85, 0.66, clamp((xg - ax) / (xg - 0.735), 0, 1));
            for (let c = 0; c < 3; c++) upper.c[k * 4 + c] = Math.round(upper.c[k * 4 + c] * f);
          } }
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
      { // centre board under the crest; its 4 cm overlap into a neighbour showed white under the door-3 tray (w11b/w12b hairline)
        const isBar = (q) => q && q.type === 'door' && q.door === 2;
        const za = z0 - (isBar(zones[zi - 1]) ? 0 : 0.04), zb = z1 + (isBar(zones[zi + 1]) ? 0 : 0.04);
        upper.add(gBox(1.30, 0.02, zb - za), M4.trs(0, 2.325, (za + zb) / 2), MAT.ceiling); }
      // header closures at the zone ends: the open vault sweep let the sky show between the centre-bin end, the vault
      // and the door dome (w2b v3 leak)
      for (const side of [-1, 1]) {
        const poly = [...VAULT.map(([x, y]) => [x * side, y]), [0, 2.27], [0, 2.62], [VAULT[0][0] * side, 2.62]];   // over the centre-bin crest too (w3b sliver)
        // closures facing the dark door-3 soffit take its colour (w8b: white arch round the tray in v3)
        const bar = (q) => q && q.type === 'door' && q.door === 2;
        for (const [z, q] of [[z0 - 0.006, zones[zi - 1]], [z1 + 0.006, zones[zi + 1]]]) {
          upper.add(gExtrude(poly, 0.01), M4.trs(0, 0, z), bar(q) ? CEILMAT.barSoffit : CEILMAT.flat);
          // ...and on to the outboard bin top, over the cove / grille / bin-crest ends (w9a/w9b/w10b: white arcs)
          // every door, not just door 3: the dome stands ~0.1 m above the bin top there (w11a d4b: keyhole onto the next EXIT sign)
          if (q && q.type === 'door') upper.add(gExtrude([[1.62 * side, 2.22], [2.35 * side, 2.22], [2.35 * side, 2.62], [1.62 * side, 2.62]], 0.01), M4.trs(0, 0, z), bar(q) ? CEILMAT.barSoffit : CEILMAT.flat);
        }
      }
    } else if (zn.type === 'door') {
      const zc = (z0 + z1) / 2, vz = upper.p.length / 3;
      for (const side of [-1, 1]) {
        const prof = DOME.map(([x, y]) => [x * side, y]);
        // emission ramps up toward the door instead of stepping to 0.5 (w11b: a flat 254 band at the door end) [A]
        const eFn = (p) => { const ax = Math.abs(p[0]); const q = clamp((ax - 1.7) / 1.05, 0, 1); return 0.06 + 0.14 * q * q * (3 - 2 * q); };   // w12b: 0.2 still clipped at the door wall   // w1: floor 0.03 read grey #c8c8c8
        // door 3: the whole soffit is dark wall to wall (b_lalf_c133/c134; w6b: a dark patch inside a white dome)
        upper.add(gSweep(prof, z0, z1, { side: side > 0 ? 1 : -1, zsteps: 6 }), null, zn.door === 2 ? CEILMAT.barSoffit : { ...CEILMAT.vault, eFn });
        if (zn.door !== 2) {
          // two transverse panel joints (raised rib + aft shadow lip, as on the aisle vault) splitting the dome into
          // three panels (c133: a light panelled ceiling outboard of the bar tray [V look]; 0.4 m panels [A])
          for (const f of [-1, 1]) {
            const zj = zc + f * 0.2;
            upper.add(profileRibbon(DOME, side, zj, 0.014, 0.004), null, CEILMAT.rib);
            upper.add(profileRibbon(DOME, side, zj + 0.0085, 0.005, 0.0022), null, CEILMAT.ribShadow);
          }
        }
      }
      if (zn.door === 2) {
        // door-3 (bar) cross-aisle: a flat dark tray across the aisle in a light frame, two rows of round downlights
        // along it, one louvred vent and a speaker grille (b_lalf_c133/c134 [V]; 3.0 m wide at y 2.40, lights 0.7 m
        // apart [A])
        const len = z1 - z0 - 0.08, TY = 2.40;
        upper.add(gBox(3.1, 0.006, z1 - z0), M4.trs(0, 2.43, zc), CEILMAT.barSoffit);   // flat soffit, straight far edge (w6a)
        upper.add(gBox(3.0, 0.006, len), M4.trs(0, TY, zc), CEILMAT.barTray);
        for (const f of [-1, 1]) {   // light edge trim round the tray, just under it (w6b: a frame above the tray never showed)
          upper.add(gBox(3.0, 0.004, 0.025), M4.trs(0, TY - 0.004, zc + f * (len / 2 - 0.0125)), CEILMAT.barFrame);
          upper.add(gBox(0.025, 0.004, len), M4.trs(f * 1.4875, TY - 0.004, zc), CEILMAT.barFrame);
        }
        for (const x of [-1.2, -0.6, 0, 0.6, 1.2]) for (const f of [-1, 1]) {   // spread across the aisle-to-aisle soffit (c133: 6-8 in view; w7a/w7b)
          const z = zc + f * len * 0.3;
          upper.add(gCyl(0.04, 0.04, 0.004, 16), M4.trs(x, TY - 0.004, z), CEILMAT.barFrame);
          upper.add(gCyl(0.03, 0.03, 0.004, 16), M4.trs(x, TY - 0.005, z), CEILMAT.downlight);
        }
        upper.add(gBox(0.16, 0.006, 0.14), M4.trs(0.9, TY - 0.004, zc), CEILMAT.barFrame);   // louvre: light slats on a dark ground
        for (let k = 0; k < 5; k++) upper.add(gBox(0.13, 0.008, 0.012), M4.trs(0.9, TY - 0.008, zc - 0.05 + k * 0.025), { c: '#ece9e3', r: 0.5 });
        upper.add(gBox(0.17, 0.004, 0.11), M4.trs(1.15, TY - 0.005, zc), { c: '#9a9188', r: 0.5 });   // speaker beside the louvre (c133): dark face, light rim 2 mm proud
        upper.add(gBox(0.15, 0.004, 0.09), M4.trs(1.15, TY - 0.0075, zc), { c: '#4a4441', r: 0.6, l: LAYER.grille });   // ~0.8x the soffit (c133; w8a: black hole)
      } else {
        // entry lights: two narrow fore-aft strips along the edges of the flat centre panel (up_F_Forward-Look [V];
        // 70 mm wide, x = ±0.55 [A])
        // strips sit in a recessed light-grey housing, lit lower (w11b: two bare 253 planks) [A]
        const ls = Math.max(0.2, z1 - z0 - 0.25), yc = ceilOutline('door', 0), lit = [];
        for (const s of [-1, 1]) {
          upper.add(gRBox(0.10, 0.006, ls + 0.03, 0.02, 1), M4.trs(0.55 * s, ceilOutline('door', 0.55) - 0.001, zc), CEILMAT.stripHousing);
          lit.push([gRBox(0.07, 0.008, ls, 0.02, 1), M4.trs(0.55 * s, ceilOutline('door', 0.55) - 0.003, zc), { ...CEILMAT.lightStrip, e: 0.55 }]);
        }
        // downlights with a trim ring, as at door 3 (c133 [V])
        for (const dx of [-1.45, 1.45]) {
          const y = ceilOutline('door', dx), a = Math.atan2(ceilOutline('door', Math.abs(dx) + 0.01) - ceilOutline('door', Math.abs(dx) - 0.01), 0.02) * Math.sign(dx);
          upper.add(gCyl(0.055, 0.055, 0.006, 18), M4.trs(dx, y - 0.003, zc, 0, 0, a), CEILMAT.ringLight);
          lit.push([gCyl(0.04, 0.04, 0.006, 18), M4.trs(dx, y - 0.005, zc, 0, 0, a), CEILMAT.downlight]);
        }
        // on the flat crown between the strips: a rounded speaker grille, an emergency light and a smoke detector
        // (c133: speaker + small lit fitting on the door-area soffit [V]; positions [A])
        upper.add(gRBox(0.30, 0.006, 0.10, 0.025, 1), M4.trs(0, yc - 0.002, zc - 0.32), CEILMAT.bezel);
        upper.add(gRBox(0.27, 0.004, 0.075, 0.02, 1), M4.trs(0, yc - 0.005, zc - 0.32), { c: '#a9a7a3', r: 0.7, l: LAYER.grille });
        upper.add(gRBox(0.07, 0.008, 0.04, 0.005, 1), M4.trs(0.25, yc - 0.004, zc), CEILMAT.emergBase);
        upper.add(gRBox(0.05, 0.004, 0.022, 0.004, 1), M4.trs(0.25, yc - 0.0085, zc), CEILMAT.emerg);
        upper.add(gCyl(0.05, 0.05, 0.02, 18), M4.trs(-0.25, yc - 0.01, zc), CEILMAT.flat);
        upper.add(gCyl(0.03, 0.03, 0.004, 18), M4.trs(-0.25, yc - 0.021, zc), CEILMAT.ribShadow);
        // baked falloff across the whole arc, x0.90 at the door wall -> x0.64 at the crown, over the dome, ribs and
        // fittings but not the lit strips / downlights (w11: one flat 229 field; w12a/b: crown 217, 1.2x the 178 aisle
        // vault, flat side bands) [D]
        for (let k = vz; k < upper.p.length / 3; k++) {
          const q = clamp(Math.abs(upper.p[k * 3]) / 2.6, 0, 1), f = lerp(0.64, 0.9, q * q * (3 - 2 * q));
          for (let c = 0; c < 3; c++) upper.c[k * 4 + c] = Math.round(upper.c[k * 4 + c] * f);
        }
        for (const [g, m, mat] of lit) upper.add(g, m, mat);
      }
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
