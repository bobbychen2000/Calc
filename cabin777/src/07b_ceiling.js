// ------------------------------------------------------------------
// Ceilings (777 Signature Interior): curved aisle panels between the outboard and centre bins with cove
// up-lighting at both edges and a continuous slatted light/air trough running down each aisle (seen in
// y_47301, c_27312 and a THE Suite aisle photo [V]); faint panel joints on the 2-frame grid, small emergency
// lights, EXIT signs over the aisles near exits; raised curved ceilings in the door areas; flat over monuments
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
const TROUGH = { t: 0.66, w: 0.07 };
function zoneModules(z0, z1, target = 2 * FRAME) {
  const n = Math.max(1, Math.round((z1 - z0) / target));
  const L = (z1 - z0) / n, b = [];
  for (let k = 0; k <= n; k++) b.push(z0 + L * k);
  return b;
}

const CEILMAT = {
  vault: { c: '#f3f2ee', r: 0.82, l: 12, e: 0.05 },
  seam: { c: '#c4c7ca', r: 0.8 },
  trough: { c: '#a4a9ae', r: 0.7 },
  troughRim: { c: '#e9e8e4', r: 0.45, l: LAYER.plastic },
  slat: { c: '#efeeea', r: 0.5, e: 0.12 },
  emerg: { c: '#fff7e8', r: 0.3, e: 0.25 },
  emergBase: { c: '#d8d7d2', r: 0.4 },
  flat: { c: '#efeeea', r: 0.72, l: LAYER.plastic },
  lightPanel: { c: '#fffaf0', r: 0.5, e: 0.45 },
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
        // curved aisle panel; cove LEDs at both edges wash up onto it
        const eFn = (p) => {
          const ax = Math.abs(p[0]);
          if (ax > 1.66 || ax < 0.73) return 0.85;
          const d = Math.min(1.655 - ax, (ax - 0.735) * 1.1);
          return 0.05 + 0.34 * Math.exp(-Math.max(d, 0) / 0.13);
        };
        const prof = VAULT.map(([x, y]) => [x * side, y]);
        upper.add(gSweep(prof, z0, z1, { side: side > 0 ? 1 : -1, zsteps: mods.length - 1 }), null, { ...CEILMAT.vault, eFn });
        for (let k = 1; k < mods.length - 1; k++) upper.add(profileRibbon(VAULT.slice(2, -2), side, mods[k], 0.004, 0.0015), null, CEILMAT.seam);
        // slatted trough, nearer the centre bin (continuous down the aisle in the photos) [V]; slat pitch 22 mm [A]
        upper.add(vaultStrip(TROUGH.t, side, z0 + 0.03, z1 - 0.03, TROUGH.w + 0.024, 0.0012), null, CEILMAT.troughRim);
        upper.add(vaultStrip(TROUGH.t, side, z0 + 0.04, z1 - 0.04, TROUGH.w, 0.0024), null, CEILMAT.trough);
        const sl = raw();
        for (let z = z0 + 0.06; z < z1 - 0.05; z += 0.022) {
          const q = vaultStrip(TROUGH.t, side, z - 0.0065, z + 0.0065, TROUGH.w - 0.006, 0.0034), b = sl.p.length / 3;
          sl.p.push(...q.p); sl.n.push(...q.n); sl.u.push(...q.u); sl.i.push(...q.i.map((v) => v + b));
        }
        upper.add(sl, null, CEILMAT.slat);
        // small emergency lights along the outboard side of the panel [A spacing]
        for (let k = 0; k < mods.length - 1; k += 3) {
          const zc = (mods[k] + mods[k + 1]) / 2;
          upper.add(gRBox(0.12, 0.01, 0.045, 0.01, 1), vaultXF(0.22, side, zc - 0.2, 0.003), CEILMAT.emergBase);
          upper.add(gRBox(0.09, 0.008, 0.026, 0.008, 1), vaultXF(0.22, side, zc - 0.2, 0.007), CEILMAT.emerg);
        }
        // EXIT signs over the aisle near the exits (both directions)
        const prev = zones[zi - 1], next = zones[zi + 1];
        const nearDoor = (zz) => zones.some((q) => q.type === 'door' && Math.abs((q.z0 + q.z1) / 2 - zz) < 2.4);
        const signs = [];
        if (prev && (prev.type === 'door' || nearDoor(z0))) signs.push(z0 + 1.1);
        if (next && (next.type === 'door' || nearDoor(z1))) signs.push(z1 - 1.1);
        for (const zs of signs) {
          const [x, y] = vaultAt(0.5);
          const X = x * side;
          upper.add(gBox(0.02, 0.08, 0.02), M4.trs(X, y - 0.04, zs), CEILMAT.signBox);
          upper.add(gRBox(0.32, 0.12, 0.035, 0.012, 1), M4.trs(X, y - 0.14, zs), CEILMAT.signBox);
          for (const f of [-1, 1]) upper.add(gQuad(0.28, 0.10), M4.trs(X, y - 0.14, zs + f * 0.0185, f > 0 ? 0 : Math.PI), MAT.exitGlow, atlasUV('exit'));
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
      // recessed entry lights
      upper.add(gRBox(1.2, 0.012, Math.min(0.5, (z1 - z0) * 0.45), 0.04, 1), M4.trs(0, 2.512, zc), CEILMAT.lightPanel);
      for (const dx of [-1.45, 1.45]) upper.add(gCyl(0.045, 0.045, 0.012, 14), M4.trs(dx, ceilOutline('door', dx) - 0.008, zc), { c: '#fffaf0', r: 0.4, e: 0.75 });
      // EXIT signs on the fascia facing fore and aft
      for (const f of [-1, 1]) {
        const xf = M4.trs(0, 2.35, (f > 0 ? z1 : z0) + 0.012 * f, f > 0 ? 0 : Math.PI);
        upper.add(gRBox(0.36, 0.14, 0.03, 0.012, 1), M4.mul(xf, M4.trs(0, 0, -0.016)), CEILMAT.signBox);
        upper.add(gQuad(0.31, 0.11), xf, MAT.exitGlow, atlasUV('exit'));
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
