// ------------------------------------------------------------------
// Monuments: lavatories (bidet / accessible / baby-change), galleys, the THE Room self-service bar
// (roller blinds + backlit washi-style panels), closets, flight-deck door, class partitions,
// Type A door linings and flight-attendant jump seats
// ------------------------------------------------------------------
const MONMAT = {
  laminate: { c: '#dcdad4', r: 0.45, l: LAYER.plastic },
  lavDoor: { c: '#e7e5df', r: 0.4, l: LAYER.plastic },
  steel: { c: '#b5bbc2', r: 0.3, m: 0.85, l: LAYER.brushed },
  steelDark: { c: '#8e949c', r: 0.35, m: 0.8, l: LAYER.brushed },
  ovenGlass: { c: '#101318', r: 0.1 },
  galleyWhite: { c: '#e3e3df', r: 0.4, l: LAYER.plastic },
  workLight: { c: '#fff6e6', r: 0.4, e: 0.8 },
  green: { c: '#35d06a', r: 0.4, e: 0.7 },
  red: { c: '#c62828', r: 0.5 },
  blue: { c: '#2d62b8', r: 0.5 },
  partition: { c: '#d0d2d4', r: 0.5, l: LAYER.plastic },
  cockpitDoor: { c: '#cfccc5', r: 0.45, l: LAYER.plastic },
  jump: { c: '#3a4049', r: 0.6, l: LAYER.fabric },
  harness: { c: '#1f2329', r: 0.8 },
  closet: { c: '#dedcd6', r: 0.45, l: LAYER.plastic },
  ash: { c: '#cdbfa6', r: 0.5, l: LAYER.wood },
  ashDark: { c: '#8a7560', r: 0.5, l: LAYER.wood },
  darkWood: { c: '#4a3629', r: 0.42, l: LAYER.wood },
  washi: { c: '#ffffff', r: 0.8, l: LAYER.atlasGlow, e: 0.55 },
  blind: { c: '#d8d2c4', r: 0.8, l: LAYER.fabric },
  bottle: { c: '#6d8a6a', r: 0.15 },
  snack: { c: '#c9793d', r: 0.6 },
};

function monoSection(x0, x1, h) {
  const pts = [];
  const right = x1 > 0 && Math.abs(x1) >= Math.abs(x0);
  const n = 10;
  if (right) {
    pts.push([x0, 0]);
    for (let k = 0; k <= n; k++) { const y = (h * k) / n; pts.push([Math.min(x1, wallAt(y)[0] - 0.012), y]); }
    pts.push([x0, h]);
  } else {
    pts.push([x1, 0]); pts.push([x1, h]);
    for (let k = n; k >= 0; k--) { const y = (h * k) / n; pts.push([Math.max(x0, -wallAt(y)[0] + 0.012), y]); }
  }
  return pts.filter((p, i) => i === 0 || Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]) > 1e-4);
}
function monoBody(B, m, mat) {
  const sec = monoSection(m.x0, m.x1, m.h);
  B.add(gExtrude(sec, m.z1 - m.z0, 20), M4.trs(0, 0, (m.z0 + m.z1) / 2), mat);
}
function faceXF(m, x, y, out = 0) {
  const zf = m.face > 0 ? m.z1 : m.z0;
  return M4.trs(x, y, zf + m.face * out, m.face > 0 ? 0 : Math.PI);
}
// cabin class at a z (for finishes)
function clsAt(layout, z) {
  if (z < layout.suiteZ[2] + 0.2) return 'F';
  if (z < layout.z20 + 0.2) return 'J';
  if (z < layout.doorsZ[3][0]) return 'PY';
  return 'Y';
}

function buildMonuments(gl, layout, opts = {}) {
  const B = new Builder();
  for (const m of layout.mon) {
    const w = m.x1 - m.x0, cx = (m.x0 + m.x1) / 2;
    const inner = Math.abs(m.x0) < Math.abs(m.x1) ? m.x0 : m.x1;
    const cls = clsAt(layout, (m.z0 + m.z1) / 2);
    const premium = cls === 'F' || cls === 'J';
    const F = (x, y, o) => faceXF(m, x, y, o);
    if (m.kind === 'lav') {
      monoBody(B, m, cls === 'F' ? MONMAT.darkWood : premium ? MONMAT.ash : MONMAT.laminate);
      const dw = Math.min(m.access ? 0.78 : 0.62, w - 0.14);
      const dx = Math.abs(inner) < 0.05 ? cx : inner + Math.sign(cx - inner) * (dw / 2 + 0.06);
      B.add(gRBox(dw, 1.86, 0.02, 0.01, 1), F(dx, 0.95, 0.008), premium ? (cls === 'F' ? { c: '#5a4536', r: 0.4, l: LAYER.wood } : MONMAT.ashDark) : MONMAT.lavDoor);
      B.add(gBox(0.006, 1.8, 0.024), F(dx, 0.95, 0.009), { c: '#9ea3a9', r: 0.5 });
      B.add(gRBox(0.10, 0.03, 0.03, 0.01, 1), F(dx + dw * 0.36, 1.02, 0.03), MONMAT.steel);
      B.add(gRBox(0.07, 0.025, 0.012, 0.005, 1), F(dx + dw * 0.36, 1.12, 0.022), MONMAT.green);
      B.add(gRBox(dw - 0.1, 0.12, 0.006, 0.004, 1), F(dx, 0.12, 0.02), MAT.grille);
      B.add(gQuad(0.17, 0.082), F(dx, 1.99, 0.021), MAT.exitGlow, atlasUV('lav'));
      if (m.access) B.add(gRBox(0.09, 0.09, 0.006, 0.01, 1), F(dx - dw * 0.3, 1.45, 0.02), { c: '#2d62b8', r: 0.5 });
    } else if (m.kind === 'sideStorage') {
      monoBody(B, m, MONMAT.closet);
      B.add(gRBox(Math.abs(m.x1 - m.x0) - 0.06, 0.02, m.z1 - m.z0 - 0.06, 0.01, 1), M4.trs(cx, m.h + 0.005, (m.z0 + m.z1) / 2), { c: '#cfccc5', r: 0.4, l: LAYER.plastic });
    } else if (m.kind === 'closet') {
      monoBody(B, m, premium ? MONMAT.ash : MONMAT.closet);
      const dw = Math.min(0.72, w - 0.1);
      B.add(gRBox(dw, m.h - 0.12, 0.02, 0.01, 1), F(cx, m.h / 2, 0.008), premium ? (cls === 'F' ? MONMAT.darkWood : MONMAT.ashDark) : MONMAT.lavDoor);
      B.add(gRBox(0.03, 0.14, 0.03, 0.01, 1), F(cx - dw * 0.38, Math.min(1.05, m.h * 0.6), 0.03), MONMAT.steel);
      if (m.low) B.add(gRBox(w - 0.02, 0.03, m.z1 - m.z0 - 0.02, 0.01, 1), M4.trs(cx, m.h + 0.012, (m.z0 + m.z1) / 2), cls === 'F' ? MONMAT.darkWood : MONMAT.ash);
    } else if (m.kind === 'galley' || m.kind === 'bar') {
      const back = { ...m };
      if (m.face > 0) back.z1 = m.z1 - 0.02; else back.z0 = m.z0 + 0.02;
      monoBody(B, back, premium ? MONMAT.ash : MONMAT.galleyWhite);
      const usable = w - 0.1;
      if (m.kind === 'galley') {
        const nC = m.carts || 2;
        const cw = Math.min(0.31, usable / nC - 0.02);
        for (let k = 0; k < nC; k++) {
          const x = m.x0 + 0.05 + (usable / nC) * (k + 0.5);
          if (Math.abs(x) > wallAt(0.5)[0] - 0.2) continue;
          const G = (dx, y, o) => faceXF(m, x + dx, y, o);
          B.add(gRBox(cw, 1.02, 0.05, 0.012, 1), G(0, 0.53, 0.02), MONMAT.steel);
          for (let r = -2; r <= 2; r++) B.add(gBox(0.008, 0.9, 0.008), G(r * cw * 0.2, 0.54, 0.047), MONMAT.steelDark);
          B.add(gRBox(cw * 0.6, 0.04, 0.03, 0.01, 1), G(0, 0.97, 0.06), k % 2 ? MONMAT.red : MONMAT.blue);
        }
        B.add(gRBox(w - 0.08, 0.035, 0.18, 0.01, 1), F(cx, 1.06, 0.08), MONMAT.steel);
        B.add(gBox(w - 0.12, 0.012, 0.03), F(cx, 1.265, 0.035), MONMAT.workLight);
        const nU = Math.max(2, Math.round(w / 0.38));
        for (let k = 0; k < nU; k++) {
          const x = m.x0 + 0.05 + ((w - 0.1) / nU) * (k + 0.5);
          if (Math.abs(x) > wallAt(1.5)[0] - 0.25) continue;
          const uW = (w - 0.1) / nU - 0.03;
          if (k % 3 === 0) { B.add(gRBox(uW, 0.30, 0.03, 0.01, 1), F(x, 1.46, 0.02), MONMAT.steel); B.add(gRBox(uW * 0.8, 0.2, 0.01, 0.006, 1), F(x, 1.46, 0.04), MONMAT.ovenGlass); }
          else if (k % 3 === 1) { B.add(gRBox(uW, 0.30, 0.1, 0.01, 1), F(x, 1.46, 0.05), MONMAT.steelDark); B.add(gRBox(0.05, 0.02, 0.01, 0.004, 1), F(x, 1.56, 0.105), MONMAT.green); }
          else { B.add(gRBox(uW, 0.30, 0.03, 0.01, 1), F(x, 1.46, 0.02), MONMAT.galleyWhite); B.add(gRBox(0.08, 0.025, 0.02, 0.006, 1), F(x, 1.58, 0.04), MONMAT.steelDark); }
          B.add(gRBox(uW, 0.36, 0.03, 0.01, 1), F(x, 1.86, 0.02), premium ? MONMAT.ashDark : MONMAT.galleyWhite);
        }
        B.add(gQuad(0.2, 0.04), F(cx, 1.635, 0.041), MAT.decal, atlasUV('galleyLbl'));
        if (m.welcome) B.add(gRBox(0.9, 0.5, 0.02, 0.01, 1), F(cx, 1.85, 0.045), MONMAT.darkWood);
      } else {
        // self-service bar: counter, snacks and drinks, mini-fridges, roller blinds up, backlit washi panels
        B.add(gRBox(w - 0.1, 0.04, 0.34, 0.012, 1), F(cx, 1.02, 0.14), MONMAT.darkWood);
        B.add(gRBox(w - 0.14, 0.94, 0.04, 0.012, 1), F(cx, 0.5, 0.04), MONMAT.ashDark);
        for (const fx of [-0.55, 0.55]) {
          B.add(gRBox(0.36, 0.5, 0.02, 0.01, 1), F(cx + fx, 0.45, 0.065), { c: '#2c2e31', r: 0.2, m: 0.3 });
          B.add(gRBox(0.02, 0.3, 0.02, 0.006, 1), F(cx + fx + 0.14, 0.5, 0.08), MONMAT.steel);
        }
        const panels = 4, pw = (w - 0.2) / panels;
        for (let k = 0; k < panels; k++) {
          const x = m.x0 + 0.1 + pw * (k + 0.5);
          B.add(gQuad(pw - 0.05, 0.62), F(x, 1.52, 0.012), MONMAT.washi, atlasUV('washi'));
          B.add(gRBox(pw - 0.02, 0.022, 0.03, 0.008, 1), F(x, 1.85, 0.03), MONMAT.darkWood);     // blind roll housing
          B.add(gRBox(pw - 0.06, 0.05, 0.012, 0.006, 1), F(x, 1.815, 0.025), MONMAT.blind);       // rolled-up blind
          for (let j = 0; j < 3; j++) B.add(gRBox(0.05, 0.1, 0.05, 0.01, 1), F(x - 0.08 + j * 0.08, 1.10, 0.09 + (j % 2) * 0.08), j === 1 ? MONMAT.bottle : MONMAT.snack);
        }
        for (let k = 0; k <= panels; k++) B.add(gBox(0.02, 0.66, 0.03), F(m.x0 + 0.1 + pw * k, 1.52, 0.02), MONMAT.darkWood);
        B.add(gBox(w - 0.16, 0.012, 0.03), F(cx, 1.18, 0.12), MONMAT.workLight);
      }
    } else if (m.kind === 'cockpit') {
      const m2 = { ...m, face: 1 };
      B.add(gRBox(0.90, 1.96, 0.05, 0.01, 1), faceXF(m2, 0, 0.99, 0.0), MONMAT.cockpitDoor);
      B.add(gRBox(0.05, 0.1, 0.03, 0.01, 1), faceXF(m2, 0.34, 1.02, 0.03), MONMAT.steel);
      B.add(gCyl(0.012, 0.012, 0.01, 10), faceXF(m2, 0, 1.55, 0.03), MONMAT.ovenGlass);
      B.add(gQuad(0.08, 0.1), faceXF(m2, 0.56, 1.25, 0.0), MAT.decal, atlasUV('keypad'));
    } else if (m.kind === 'partition') {
      const wood = m.wood;
      B.add(gRBox(w, m.h, m.z1 - m.z0, 0.01, 1), M4.trs(cx, m.h / 2, (m.z0 + m.z1) / 2), wood ? MONMAT.ash : MONMAT.partition);
      B.add(gBox(w - 0.02, 0.12, m.z1 - m.z0 + 0.006), M4.trs(cx, 0.06, (m.z0 + m.z1) / 2), MONMAT.darkWood);
      const zf = m.z1 + 0.004;
      if (m.bassinet) {
        const n = Math.max(1, Math.round(w / 0.9));
        for (let k = 0; k < n; k++) {
          const x = m.x0 + (w / n) * (k + 0.5);
          if (Math.abs(x) > 2.5) continue;
          B.add(gQuad(0.09, 0.06), M4.trs(x, 1.30, zf), MAT.decal, atlasUV('bassinet'));
          B.add(gRBox(0.3, 0.03, 0.02, 0.01, 1), M4.trs(x, 1.22, zf + 0.008), MONMAT.steelDark);
        }
      }
      if (m.monitor) {
        const xs = Math.abs(cx) < 0.1 ? [-0.55, 0.55] : [cx];
        for (const x of xs) {
          B.add(gRBox(0.40, 0.25, 0.03, 0.012, 1), M4.trs(x, 1.52, zf + 0.012), SEATMAT.bezel);
          B.add(gQuad(0.36, 0.2), M4.trs(x, 1.52, zf + 0.029), SEATMAT.screen, atlasUV('screen'));
        }
      }
    }
  }
  // ---- Type A door linings (translating door): outline, lever handle, arming flag, viewing window,
  //      assist handles, girt bar / slide bustle at the foot ----
  for (let di = 0; di < (opts.noDoors ? 0 : CAB.doors.length); di++) {
    const c = CAB.doors[di];
    for (const side of [-1, 1]) {
      const at = (v, inset) => { const [x, y, nx, ny] = wallAt(v); return [x * side + nx * side * inset, y + ny * inset]; };
      for (const zz of [c - 0.535, c + 0.535]) {
        const g = raw();
        for (let k = 0; k <= 12; k++) {
          const v = lerp(0.03, 1.9, k / 12);
          const [x, y, nx, ny] = wallAt(v);
          for (const dz of [-0.006, 0.006]) { g.p.push((x + nx * 0.003) * side, y + ny * 0.003, zz + dz); g.n.push(nx * side, ny, 0); g.u.push(0, 0); }
        }
        for (let k = 0; k < 12; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
        fixWinding(g);
        B.add(g, null, MAT.doorGap);
      }
      for (const v of [0.03, 1.9]) {
        const [x, y] = at(v, 0.003);
        const [, , nx, ny] = wallAt(v);
        const tilt = Math.atan2(ny, Math.abs(nx));
        B.add(gBox(0.004, 0.012, 1.07), M4.trs(x, y, c, 0, 0, side > 0 ? -tilt : tilt), MAT.doorGap);
      }
      const [hx, hy] = at(1.05, 0.045);
      B.add(gRBox(0.05, 0.42, 0.06, 0.02, 1), M4.trs(hx, hy + 0.02, c + 0.26, 0, 0, side * 0.12), MAT.handle);
      B.add(gRBox(0.06, 0.06, 0.08, 0.02, 1), M4.trs(hx + side * 0.01, hy - 0.19, c + 0.26), MAT.handle);
      const [rx, ry] = at(1.62, 0.02);
      B.add(gRBox(0.03, 0.05, 0.10, 0.01, 1), M4.trs(rx, ry, c - 0.25), MAT.handleRed);
      const [px, py] = at(0.95, 0.006);
      B.add(gQuad(0.2, 0.106), M4.trs(px, py, c - 0.2, side > 0 ? -Math.PI / 2 : Math.PI / 2), MAT.decal, atlasUV('doorPlacard'));
      const [sx, sy] = at(0.30, 0.05);
      const [, , snx, sny] = wallAt(0.30);
      B.add(gRBox(0.10, 0.36, 0.92, 0.04, 2), M4.trs(sx, sy, c, 0, 0, side > 0 ? -Math.atan2(sny, -snx) : Math.atan2(sny, -snx)), MAT.slide);
      for (const dz of [-0.64, 0.64]) {
        const p0 = at(0.95, 0.06), p1 = at(1.55, 0.06);
        B.add(gTube([[p0[0], p0[1], c + dz], [p1[0], p1[1], c + dz]], 0.014, 8), null, MAT.handle);
      }
    }
  }
  // ---- Flight attendant jump seats (folded) on monument faces beside each door ----
  const dz = layout.doorsZ;
  const jumps = opts.noDoors ? [] : [[-1.9, dz[0][0], 1], [2.3, dz[0][0], 1], [-0.75, dz[1][0], 1], [0.75, dz[1][0], 1], [2.1, dz[3][0], 1], [-0.6, dz[4][1], -1], [0.6, dz[4][1], -1]];
  for (const [x, z, f] of jumps) {
    const xf = M4.trs(x, 0, z + f * 0.05, f > 0 ? 0 : Math.PI);
    B.add(gRBox(0.46, 0.5, 0.07, 0.02, 1), M4.mul(xf, M4.trs(0, 0.78, 0)), MONMAT.jump);
    B.add(gRBox(0.44, 0.34, 0.06, 0.02, 1), M4.mul(xf, M4.trs(0, 1.25, -0.005)), MONMAT.jump);
    for (const s of [-1, 1]) B.add(gBox(0.04, 0.6, 0.012), M4.mul(xf, M4.trs(s * 0.12, 1.1, 0.04)), MONMAT.harness);
  }
  const geo = B.build();
  return { mesh: gl ? gl.mesh(geo, { name: 'monuments', layer: 'mono' }) : null, geo };
}
