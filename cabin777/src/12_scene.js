// ------------------------------------------------------------------
// Scene assembly: meshes, ambient-visibility volume, sun shadows, lighting moods, window shades, rendering
// ------------------------------------------------------------------
const MOODS = {
  boarding: { label: 'Boarding', hemiTop: [1.0, 0.94, 0.86], hemiBot: [0.42, 0.39, 0.36], wash: [0.62, 0.57, 0.50], led: [1.0, 0.86, 0.68], k: 1.05, exposure: 1.05 },
  cruise: { label: 'Cruise', hemiTop: [0.86, 0.88, 0.98], hemiBot: [0.34, 0.34, 0.38], wash: [0.46, 0.48, 0.56], led: [0.62, 0.72, 1.0], k: 0.95, exposure: 1.05 },
  dining: { label: 'Dining', hemiTop: [1.0, 0.80, 0.60], hemiBot: [0.40, 0.31, 0.23], wash: [0.62, 0.46, 0.32], led: [1.0, 0.64, 0.32], k: 0.9, exposure: 1.08 },
  sleep: { label: 'Night', hemiTop: [0.06, 0.065, 0.15], hemiBot: [0.022, 0.024, 0.05], wash: [0.05, 0.05, 0.14], led: [0.26, 0.24, 0.72], k: 1, exposure: 1.9, readingLights: true },
  wake: { label: 'Sunrise', hemiTop: [0.95, 0.66, 0.56], hemiBot: [0.34, 0.24, 0.22], wash: [0.60, 0.40, 0.34], led: [1.0, 0.50, 0.36], k: 0.9, exposure: 1.08 },
};
const SKIES = {
  day: { label: 'Day', sunEl: 30, sunAz: -60, sun: [5.2, 4.9, 4.4], zenith: [0.10, 0.26, 0.72], horizon: [0.62, 0.78, 0.98], haze: [0.72, 0.80, 0.92], cloudLit: [1.25, 1.25, 1.25], cloudShade: [0.62, 0.68, 0.78], skyTop: [0.55, 0.68, 0.95], skyBot: [0.55, 0.55, 0.58], winGlow: [0.20, 0.25, 0.32], sunVis: 1, night: 0, sheer: 1.0 },
  sunset: { label: 'Sunset', sunEl: 5, sunAz: 110, sun: [4.2, 2.2, 0.9], zenith: [0.10, 0.14, 0.38], horizon: [1.1, 0.55, 0.30], haze: [0.75, 0.48, 0.38], cloudLit: [1.3, 0.72, 0.48], cloudShade: [0.36, 0.28, 0.34], skyTop: [0.45, 0.35, 0.45], skyBot: [0.4, 0.26, 0.2], winGlow: [0.22, 0.12, 0.08], sunVis: 1, night: 0, sheer: 0.7 },
  night: { label: 'Night', sunEl: 38, sunAz: -40, sun: [0.07, 0.08, 0.12], zenith: [0.004, 0.006, 0.016], horizon: [0.02, 0.028, 0.05], haze: [0.018, 0.022, 0.036], cloudLit: [0.05, 0.055, 0.07], cloudShade: [0.012, 0.014, 0.02], skyTop: [0.02, 0.025, 0.04], skyBot: [0.01, 0.01, 0.015], winGlow: [0.0, 0.0, 0.0], sunVis: 0, night: 1, sheer: 0.06 },
};
// Shade states per window: 0 open, 1 half (manual) / sheer (electric), 2 closed (manual) / blackout (electric)
const SHADE_STATE = {
  label: (w, lv) => (w.electric ? ['open', 'sheer blind', 'blackout'] : ['open', 'half down', 'closed'])[lv],
  T: (w, lv) => (lv === 0 ? [0.92, 0.92, 0.92] : w.electric ? (lv === 1 ? [0.30, 0.29, 0.27] : [0.02, 0.02, 0.02]) : (lv === 1 ? [0.92, 0.92, 0.92] : [0.03, 0.03, 0.03])),
  open: (w, lv) => (lv === 0 ? 1 : lv === 1 ? (w.electric ? 0.35 : 0.55) : 0),
};

class Scene {
  constructor(gl, opts = {}) {
    this.gl = gl;
    this.q = opts.quality || 'high';
    const t0 = performance.now();
    this.layout = buildLayout();
    buildAtlas(this.layout);
    this.tex = {
      detail: gl.textureArray(buildDetailLayers(256), 256),
      atlas: gl.texture2D(ATL.canvas, { srgb: false }),
      cloud: gl.texture2D(buildCloudNoise(256), { w: 256, h: 256 }),
    };
    this.shell = buildShell(gl, this.layout);
    this.bins = buildBins(gl, this.layout);
    const sr = buildSeats(gl, this.layout);
    this.seats = sr.meshes; this.seatGroups = sr.groups;
    this.mono = buildMonuments(gl, this.layout);
    this.ext = buildExterior(gl);
    this.progs = {
      main: gl.program(SH.mainVS, SH.mainFS),
      depth: gl.program(SH.depthVS, SH.depthFS),
      sky: gl.program(SH.skyVS, SH.skyFS),
      glass: gl.program(SH.mainVS, SH.glassFS),
      glow: gl.program(SH.glowVS, SH.glowFS),
    };
    this.emptyVAO = gl.gl.createVertexArray();
    this.buildGlows();
    const sm = this.shell.meshes;
    this.opaque = [
      sm.shell, sm.upper, sm.revealR, sm.revealL, sm.shadeBtns,
      sm.shade_manual, sm.shade_sheer, sm.shade_blackout, sm.shadeRail_manual, sm.shadeRail_sheer, sm.shadeRail_blackout,
      ...Object.values(this.bins), ...Object.values(this.seats), this.mono.mesh,
    ];
    this.computeAO();
    this.winTex = null;
    this.winLevels = this.layout.windows.map(() => 0);
    this.mood = 'cruise'; this.sky = 'day'; this.globalShade = 0;
    this.xray = false;
    this.shadowDirty = true;
    this.updateWindowLUT();
    this.buildTime = performance.now() - t0;
  }

  // ---------------- ambient visibility volume ----------------
  computeAO() {
    const nx = 60, ny = 28, nz = 592;
    const min = [-3.0, 0, 2.6], size = [6.0, 2.8, 59.2];
    const cell = [size[0] / nx, size[1] / ny, size[2] / nz];
    const occ = new Float32Array(nx * ny * nz);
    const idx = (i, j, k) => (k * ny + j) * nx + i;
    const box = (x0, x1, y0, y1, z0, z1, d = 1) => {
      const i0 = Math.max(0, Math.floor((x0 - min[0]) / cell[0])), i1 = Math.min(nx - 1, Math.floor((x1 - min[0]) / cell[0]));
      const j0 = Math.max(0, Math.floor((y0 - min[1]) / cell[1])), j1 = Math.min(ny - 1, Math.floor((y1 - min[1]) / cell[1]));
      const k0 = Math.max(0, Math.floor((z0 - min[2]) / cell[2])), k1 = Math.min(nz - 1, Math.floor((z1 - min[2]) / cell[2]));
      for (let k = k0; k <= k1; k++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) { const q = idx(i, j, k); occ[q] = Math.min(1, occ[q] + d); }
    };
    // local box of a unit (room / suite) -> world
    const boxL = (s, x0, x1, y0, y1, z0, z1, d = 1) => {
      const a = localToWorld(s, [x0, y0, z0]), b = localToWorld(s, [x1, y1, z1]);
      box(Math.min(a[0], b[0]), Math.max(a[0], b[0]), y0, y1, Math.min(a[2], b[2]), Math.max(a[2], b[2]), d);
    };
    for (const s of this.layout.seats) {
      const x = s.x, z = s.z;
      if (s.kind === 'room') {
        if (s.odd) {
          boxL(s, -0.585, 0.10, 0, 0.48, -1.345, 0.52, 0.8);
          boxL(s, -0.585, 0.115, 0, 1.12, -1.345, -1.275);
          boxL(s, 0.12, 0.585, 0, 0.66, -0.58, -0.02);
          boxL(s, 0.545, 0.585, 0.66, 1.12, -0.58, -0.02);
          boxL(s, 0.08, 0.585, 0, 1.12, -1.345, -1.09, 0.8);
          boxL(s, -0.585, -0.04, 0.66, 1.24, 0.50, 0.56);
        } else {
          boxL(s, -0.12, 0.585, 0, 0.48, -0.58, 1.345, 0.8);
          boxL(s, -0.10, 0.585, 0, 1.12, 1.275, 1.345);
          boxL(s, -0.585, -0.13, 0, 0.66, 0.02, 1.30);
          boxL(s, -0.06, 0.585, 0.66, 1.24, -0.04, 0.02);
          boxL(s, 0.49, 0.585, 0, 0.7, 0.66, 1.25, 0.8);
        }
      } else if (s.kind === 'suite') {
        const hx = (s.pos === 'center' ? 1.10 : 1.24) / 2;
        boxL(s, -hx, hx, 0, 1.30, -2.20, -2.08);
        boxL(s, -hx, hx, 0, 1.30, -0.10, -0.04);
        boxL(s, hx - 0.16, hx, 0, 1.30, -0.96, -0.10);
        boxL(s, hx - 0.13, hx, 0, 1.30, -2.20, -1.95);
        boxL(s, -hx, -hx + 0.03, 0, s.pos === 'center' ? 1.30 : 0.70, -2.20, 0);
        boxL(s, -hx + 0.2, hx - 0.16, 0, 0.5, -2.08, -0.10, 0.7);
      } else {
        const hw = s.kind === 'py' ? 0.29 : 0.24;
        box(x - hw, x + hw, 0.33, 0.47, z - 0.5, z - 0.02);
        box(x - hw, x + hw, 0.47, s.kind === 'py' ? 1.30 : 1.22, z - 0.1, z + 0.1);
        box(x - hw, x + hw, 0.02, 0.33, z - 0.46, z - 0.02, 0.28);
      }
    }
    for (const zn of this.layout.zones) {
      if (zn.type !== 'seat') continue;
      box(1.46, 2.95, 1.60, 2.30, zn.z0, zn.z1); box(-2.95, -1.46, 1.60, 2.30, zn.z0, zn.z1);
      box(-0.83, 0.83, 1.84, 2.34, zn.z0, zn.z1);
    }
    for (const m of this.layout.mon) if (m.h > 0) box(m.x0, m.x1, 0, m.h, m.z0, m.z1);
    for (let j = 0; j < ny; j++) {
      const y = min[1] + (j + 0.5) * cell[1];
      const xw = wallAt(Math.min(y, 2.3))[0];
      for (let i = 0; i < nx; i++) { const x = min[0] + (i + 0.5) * cell[0]; if (Math.abs(x) > xw) for (let k = 0; k < nz; k++) occ[idx(i, j, k)] = 1; }
    }
    const kAtt = 1.35;
    const att = new Float32Array(occ.length);
    for (let q = 0; q < occ.length; q++) att[q] = Math.exp(-kAtt * occ[q]);
    const acc = new Float32Array(nx * ny * nz);
    const dirs = [[0, 0, 0.28]];
    for (const [ox, oz] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) dirs.push([ox, oz, 0.09]);
    const layerA = new Float32Array(nx * nz), layerB = new Float32Array(nx * nz);
    for (const [ox, oz, wgt] of dirs) {
      let prev = layerA, cur = layerB;
      prev.fill(1);
      for (let j = ny - 1; j >= 0; j--) {
        for (let k = 0; k < nz; k++) for (let i = 0; i < nx; i++) {
          const pi = i + ox, pk = k + oz;
          let V;
          if (pi < 0 || pi >= nx) V = 0; else if (pk < 0 || pk >= nz) V = 1; else V = prev[pk * nx + pi];
          const q = idx(i, j, k);
          acc[q] += wgt * V;
          cur[k * nx + i] = V * att[q];
        }
        const t = prev; prev = cur; cur = t;
      }
    }
    const vis = new Uint8Array(nx * ny * nz);
    for (let q = 0; q < acc.length; q++) vis[q] = Math.round(clamp(acc[q], 0, 1) * 255);
    this.ao = { tex: this.gl.texture3D(vis, nx, ny, nz), min, size };
  }

  buildGlows() {
    const gl = this.gl;
    const q = raw();
    q.p.push(-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0); q.n.push(0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1);
    q.u.push(0, 0, 1, 0, 1, 1, 0, 1); q.i.push(0, 1, 2, 0, 2, 3);
    const b = new Builder(); b.add(q, null, { c: '#ffffff' });
    this.glowMesh = gl.mesh(b.build(), { name: 'glow', instances: [] });
    this.readingMesh = gl.mesh(b.build(), { name: 'reading', instances: [] });
    const mats = [], tints = [];
    for (const l of this.ext.lights) { mats.push(M4.trs(l.p[0], l.p[1], l.p[2], 0, 0, 0, l.s, l.s, l.s)); tints.push([...l.c, l.blink]); }
    gl.setInstances(this.glowMesh, mats, tints);
    const rnd = mulberry32(42);
    const rm = [], rt = [];
    for (const s of this.layout.seats) {
      if (rnd() > 0.18) continue;
      if (s.kind === 'room' || s.kind === 'suite') {
        const p = s.kind === 'room' ? localToWorld(s, s.odd ? [0.03, 1.02, -1.18] : [-0.07, 1.02, 1.18]) : localToWorld(s, [0.1, 1.06, -0.2]);
        rm.push(M4.trs(p[0], p[1], p[2], 0, 0, 0, 0.14, 0.14, 0.14)); rt.push([1.4, 1.1, 0.7, 0]);
        continue;
      }
      const y = Math.abs(s.x) < 1.1 ? 1.82 : binBottomY(s.x * 0.92) - 0.03;
      rm.push(M4.trs(s.x * 0.92, y, s.z - (s.kind === 'py' ? 0.5 : 0.45), 0, 0, 0, 0.12, 0.12, 0.12)); rt.push([1.6, 1.3, 0.85, 0]);
    }
    gl.setInstances(this.readingMesh, rm, rt);
  }

  // shade geometry for one window (no upload when batch = true)
  applyShade(i, level, batch) {
    const w = this.layout.windows[i];
    const S = this.shell.shades, G = this.gl;
    const put = (mesh, j, m) => { if (batch) mesh.idata.set(m, j * 20); else G.setMatrix(mesh, j, m); };
    if (w.electric) {
      const js = S.sheer.list.indexOf(i), jb = S.blackout.list.indexOf(i);
      const ms = shadeMats(w, level >= 1 ? 1 : 0, 0), mb = shadeMats(w, level >= 2 ? 1 : 0, -0.012);
      put(S.sheer.panel, js, ms.panel); put(S.sheer.rail, js, ms.rail);
      put(S.blackout.panel, jb, mb.panel); put(S.blackout.rail, jb, mb.rail);
    } else {
      const j = S.manual.list.indexOf(i);
      const m = shadeMats(w, [0, 0.5, 1][level], 0);
      put(S.manual.panel, j, m.panel); put(S.manual.rail, j, m.rail);
    }
  }
  setWindow(i, level) {
    this.winLevels[i] = level;
    this.applyShade(i, level, false);
    this.updateWindowLUT();
    this.shadowDirty = true;
  }
  setAllWindows(level) {
    this.globalShade = level;
    for (let i = 0; i < this.winLevels.length; i++) { this.winLevels[i] = level; this.applyShade(i, level, true); }
    const S = this.shell.shades, G = this.gl;
    for (const k of ['manual', 'sheer', 'blackout']) for (const m of [S[k].panel, S[k].rail]) G.setInstancesRaw(m, m.idata, m.instances);
    this.updateWindowLUT();
    this.shadowDirty = true;
  }
  updateSheerTint() {
    const k = SKIES[this.sky].sheer;
    const m = this.shell.shades.sheer.panel;
    for (let i = 0; i < m.instances; i++) { m.idata[i * 20 + 16] = k; m.idata[i * 20 + 17] = k; m.idata[i * 20 + 18] = k; }
    this.gl.setInstancesRaw(m, m.idata, m.instances);
  }
  updateWindowLUT() {
    const N = 1024, d = new Uint8Array(N * 2 * 4);
    const z0 = this.ao ? this.ao.min[2] : 2.6, z1 = z0 + 59.2;
    for (let r = 0; r < 2; r++) for (let x = 0; x < N; x++) { const o = (r * N + x) * 4; d[o] = d[o + 1] = d[o + 2] = 235; d[o + 3] = 255; }
    let open = 0;
    this.layout.windows.forEach((w, i) => {
      const lv = this.winLevels[i];
      const T = SHADE_STATE.T(w, lv);
      open += SHADE_STATE.open(w, lv);
      const r = w.side > 0 ? 1 : 0;
      const a = Math.floor(((w.z - 0.24 - z0) / (z1 - z0)) * N), b = Math.ceil(((w.z + 0.24 - z0) / (z1 - z0)) * N);
      for (let x = Math.max(0, a); x <= Math.min(N - 1, b); x++) { const o = (r * N + x) * 4; d[o] = T[0] * 255; d[o + 1] = T[1] * 255; d[o + 2] = T[2] * 255; }
    });
    this.openness = open / Math.max(1, this.layout.windows.length);
    const gl = this.gl.gl;
    if (!this.winTex) {
      this.winTex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, this.winTex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }
    gl.bindTexture(gl.TEXTURE_2D, this.winTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, N, 2, 0, gl.RGBA, gl.UNSIGNED_BYTE, d);
    this.winZ = [z0, z1];
  }

  sunDir() {
    const s = SKIES[this.sky];
    const el = s.sunEl * DEG, az = s.sunAz * DEG;
    return V3.norm([Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el)]);
  }

  renderShadow() {
    const G = this.gl, gl = G.gl;
    const L = this.sunDir();
    const center = [0, 1.2, 32];
    const view = M4.lookAt(V3.add(center, V3.scale(L, 45)), center, Math.abs(L[1]) > 0.95 ? [0, 0, 1] : [0, 1, 0]);
    const corners = [];
    for (const x of [-3.1, 3.1]) for (const y of [-0.1, 2.6]) for (const z of [2.6, 61.6]) corners.push(M4.point(view, [x, y, z]));
    const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    for (const c of corners) for (let a = 0; a < 3; a++) { mn[a] = Math.min(mn[a], c[a]); mx[a] = Math.max(mx[a], c[a]); }
    const ex = mx[0] - mn[0], ey = mx[1] - mn[1];
    const W = Math.min(4096, G.maxTex);
    const H = clamp(Math.ceil((W * ey / ex) * 1.15 / 64) * 64, 256, Math.min(2048, G.maxTex));
    if (!this.shadow || this.shadow.w !== W || this.shadow.h !== H) this.shadow = G.shadowTarget(W, H);
    const proj = M4.ortho(mn[0] - 0.05, mx[0] + 0.05, mn[1] - 0.05, mx[1] + 0.05, -mx[2] - 1, -mn[2] + 1);
    this.shadowMat = M4.mul(proj, view);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.shadow.fb);
    gl.viewport(0, 0, W, H);
    gl.clear(gl.DEPTH_BUFFER_BIT);
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.POLYGON_OFFSET_FILL);
    gl.polygonOffset(2.0, 3.0);
    G.use(this.progs.depth);
    G.set('u_viewProj', this.shadowMat);
    for (const g of Object.values(this.seatGroups)) { G.setInstancesRaw(g.hi, g.master, g.n); if (g.lo) G.setInstancesRaw(g.lo, g.master, 0); g.dirty = true; }
    for (const m of this.opaque) if (m.castShadow && m.visible) G.draw(m);
    gl.disable(gl.POLYGON_OFFSET_FILL);
    gl.enable(gl.CULL_FACE);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    this.shadowDirty = false;
  }

  render(cam, w, h, time) {
    const G = this.gl, gl = G.gl;
    G.stats.calls = 0; G.stats.tris = 0;
    const sky = SKIES[this.sky], mood = MOODS[this.mood];
    if (this.shadowDirty) this.renderShadow();
    const lc = this.lodCam;
    const moved = !lc || V3.len(V3.sub(lc.pos, cam.pos)) > 0.35 || V3.dot(lc.fwd, cam.fwd) < 0.985 || lc.xray !== this.xray;
    if (moved || Object.values(this.seatGroups).some((g) => g.dirty)) {
      const cosCull = Math.cos(Math.min(Math.PI * 0.95, cam.halfDiag + 0.35));
      updateSeatLOD(G, this.seatGroups, cam, { cosCull: this.xray ? -2 : cosCull, near: this.xray ? 0 : 9.5 });
      this.lodCam = { pos: [...cam.pos], fwd: [...cam.fwd], xray: this.xray };
    }
    gl.viewport(0, 0, w, h);
    if (this.xray) gl.clearColor(0.043, 0.07, 0.125, 1); else gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const vp = M4.mul(cam.proj, cam.view);
    const L = this.sunDir();
    const op = this.openness ?? 1;
    const winGlow = sky.winGlow.map((v) => v * (0.15 + 0.85 * op));
    const P = this.progs.main;
    G.use(P);
    G.set('u_viewProj', vp);
    G.set('u_camPos', cam.pos);
    G.set('u_sunDir', L);
    G.set('u_sunCol', sky.sun);
    G.set('u_shadowMat', this.shadowMat);
    G.tex('u_shadow', 0, this.shadow.tex);
    G.set('u_shadowTexel', [1 / this.shadow.w, 1 / this.shadow.h]);
    const k = mood.k;
    G.set('u_hemiTop', mood.hemiTop.map((v) => v * k));
    G.set('u_hemiBot', mood.hemiBot.map((v) => v * k));
    G.set('u_wash', mood.wash);
    G.set('u_led', mood.led);
    G.set('u_winGlow', winGlow);
    G.tex('u_ao', 1, this.ao.tex, gl.TEXTURE_3D);
    G.set('u_aoMin', this.ao.min);
    G.set('u_aoSize', this.ao.size);
    G.tex('u_detail', 2, this.tex.detail, gl.TEXTURE_2D_ARRAY);
    const lp = new Float32Array(N_LAYERS * 4);
    for (const [kk, v] of Object.entries(LAYER_PARAMS)) lp.set(v, +kk * 4);
    G.set('u_layer', lp);
    G.tex('u_atlas', 3, this.tex.atlas);
    G.set('u_screenStep', ATL.screenStep);
    G.set('u_emisGain', this.mood === 'sleep' ? 0.55 : 1.0);
    G.set('u_screenGain', this.mood === 'sleep' ? 0.35 : 0.8);
    G.tex('u_win', 4, this.winTex);
    G.set('u_winZ', this.winZ);
    G.set('u_R', CAB.R + 0.10);
    G.set('u_yc', CAB.yc);
    G.set('u_exposure', mood.exposure);
    G.set('u_exterior', 0);
    G.set('u_skyTop', sky.skyTop);
    G.set('u_skyBot', sky.skyBot);
    G.set('u_detailOn', this.q === 'low' ? 0 : 1);
    for (const m of this.opaque) {
      if (this.xray && (m.layer === 'upper')) continue;
      G.draw(m);
    }
    if (!this.xray) {
      G.set('u_exterior', 1);
      G.set('u_exposure', 1.0);
      G.draw(this.ext.mesh);
    }
    gl.depthFunc(gl.LEQUAL);
    gl.depthMask(false);
    const S = this.progs.sky;
    G.use(S);
    G.set('u_invViewProj', M4.invert(vp));
    G.set('u_camPos', cam.pos);
    G.set('u_sunDir', L);
    G.set('u_time', time);
    G.set('u_zenith', sky.zenith); G.set('u_horizon', sky.horizon); G.set('u_haze', sky.haze);
    G.set('u_sunTint', sky.sun.map((v) => v / 5));
    G.set('u_night', sky.night);
    G.set('u_cloudLit', sky.cloudLit); G.set('u_cloudShade', sky.cloudShade);
    G.set('u_exposure', 1.0);
    G.set('u_sunVis', sky.sunVis);
    G.tex('u_cloud', 0, this.tex.cloud);
    gl.bindVertexArray(this.emptyVAO);
    if (!this.xray) gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.depthFunc(gl.LESS);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.DST_COLOR, gl.ZERO);
    gl.disable(gl.CULL_FACE);
    G.use(this.progs.glass);
    G.set('u_viewProj', vp);
    G.draw(this.shell.meshes.glassR); G.draw(this.shell.meshes.glassL);
    gl.blendFunc(gl.ONE, gl.ONE);
    G.use(this.progs.glow);
    G.set('u_viewProj', vp);
    G.set('u_camRight', cam.right); G.set('u_camUp', cam.up);
    G.set('u_time', time);
    if (sky.night && !this.xray) G.draw(this.glowMesh);
    if (mood.readingLights) G.draw(this.readingMesh);
    gl.enable(gl.CULL_FACE);
    gl.disable(gl.BLEND);
    gl.depthMask(true);
  }
}
