// ------------------------------------------------------------------
// Scene assembly: meshes, ambient-visibility volume, sun shadows, lighting moods, window shades, rendering
// ------------------------------------------------------------------
const MOODS = {
  // boarding = the ANA photo look: neutral-cool white LED light, high key (ref/ana y_47300, c_27312, py_37302)
  // QA r1: two LED circuits. led = ceiling cove (stays near-white in boarding/cruise: aisle ceiling + aisle-side bins lit
  // white), sideLed = the lens under the outboard bins, ANA's saturated blue sidewall band fading to white at the window
  // belt [V: tlfl_IMG_9217 #5b5cc4 (cruise), sany_10 #5466e8 / sany_12 #4c5edc (boarding), roame_7672 #5e7fef].
  // hemiBot lowered and exposure raised with the fill/AO rework (u_fill 0.7 -> 0.45) so mean tones stay put while
  // undersides, footwells and the floor darken [V: tlfl_IMG_9217 PSU underside #615c5d, c_27312 footwell #2d2c30]
  // QA r2: sideLed raised so the band under the outboard bins reads saturated blue now that the shader cuts the white
  // hemi / bounce / wash inside the band [V: tlfl_IMG_9217 #5d5eca at the lens, #867db2 at the window tops; sany_12
  // boarding #4c5edc]
  boarding: { label: 'Boarding', hemiTop: [0.97, 0.99, 1.03], hemiBot: [0.36, 0.37, 0.40], wash: [0.25, 0.26, 0.28], led: [1.0, 0.98, 0.92], sideLed: [0.0, 0.03, 0.62], k: 1.05, exposure: 1.40 },
  cruise: { label: 'Cruise', hemiTop: [0.86, 0.88, 0.98], hemiBot: [0.24, 0.24, 0.28], wash: [0.25, 0.26, 0.30], led: [1.0, 0.98, 0.92], sideLed: [0.06, 0.04, 0.46], k: 0.95, exposure: 1.15 },
  // dining / sunrise, QA r2: ANA's amber phase is a saturated amber LED line on the bin lens and cove, amber-washed bin
  // faces and a much darker lower cabin, not a beige high key [V: ff_door-gap lens #ffa43d (h32 s0.76), bins #955b2d /
  // #673e1e (s ~0.7)]. Sunrise uses the same levels with a pinker LED [A: no ANA sunrise photo]
  dining: { label: 'Dining', hemiTop: [0.62, 0.23, 0.055], hemiBot: [0.14, 0.052, 0.013], wash: [0.30, 0.11, 0.03], led: [1.0, 0.22, 0.02], sideLed: [0.90, 0.24, 0.03], k: 0.9, exposure: 1.3, strips: true },
  // night, QA r2: THE Room in service at night is near-black and neutral-warm; the light comes from the IFE screens, the
  // warm strip under each screen, small white reading lamps and amber PSU lamps [V: ucr_room-night-lighting ceiling
  // #1e1915, sidewall #24211c, bins #322a1f, PSU lamp #9e5e38, strip #ffeb97, mean RGB 39/34/33]. The blue night refs
  // used in r1 (roame_7672, sany_10) were boarding shots on the ground (daylight in the windows), so not the night scene
  sleep: { label: 'Night', hemiTop: [0.030, 0.027, 0.024], hemiBot: [0.010, 0.009, 0.008], wash: [0.012, 0.010, 0.008], led: [0.045, 0.038, 0.030], sideLed: [0.020, 0.020, 0.024], k: 1, exposure: 2.2, readingLights: true, strips: true, screenGain: 0.6 },
  wake: { label: 'Sunrise', hemiTop: [0.62, 0.26, 0.12], hemiBot: [0.14, 0.058, 0.027], wash: [0.30, 0.12, 0.06], led: [1.0, 0.22, 0.10], sideLed: [0.90, 0.22, 0.12], k: 0.9, exposure: 1.3 },
};
// winExp: the view behind the glass at interior exposure; cabin photos show day windows near-white with a glowing
// reveal (tlfl_IMG_9217 / 9518, pane ~#eef3f8) [V]; eases back to 1 when the eye is at the window (looking out)
const SKIES = {
  day: { label: 'Day', sunEl: 30, sunAz: -60, sun: [5.2, 4.9, 4.4], zenith: [0.10, 0.26, 0.72], horizon: [0.62, 0.78, 0.98], haze: [0.72, 0.80, 0.92], cloudLit: [1.25, 1.25, 1.25], cloudShade: [0.62, 0.68, 0.78], skyTop: [0.55, 0.68, 0.95], skyBot: [0.55, 0.55, 0.58], winGlow: [0.45, 0.52, 0.62], winExp: 1.6, sunVis: 1, night: 0, sheer: 1.0 },
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
      photo: gl.textureArray(buildPhotoLayers(256), 256),
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
      ...Object.values(this.bins), ...Object.values(this.seats), this.mono.mesh, this.stripMesh,
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
    // ~8.3 cm voxels (QA r1: 10 cm cells could not resolve the 0.1 m footwells / console gaps) [D]
    const nx = 72, ny = 34, nz = 712;
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
    // seats: voxelise the real instanced geometry (surface samples every ~5 cm, each adds partial occupancy) so
    // footwells, seat undersides, shell corners and console gaps get soft occlusion that matches their shapes
    const dOcc = 0.34, step2 = 0.05 * 0.05;
    const mark = (x, y, z) => {
      const i = Math.floor((x - min[0]) / cell[0]), j = Math.floor((y - min[1]) / cell[1]), k = Math.floor((z - min[2]) / cell[2]);
      if (i < 0 || j < 0 || k < 0 || i >= nx || j >= ny || k >= nz) return;
      const q = idx(i, j, k); occ[q] = Math.min(1, occ[q] + dOcc);
    };
    for (const g of Object.values(this.seatGroups || {})) {
      const P = g.geo.pos, I = g.geo.idx;
      const samples = [];   // local-space sample points of this unit, reused for every instance
      for (let t = 0; t < I.length; t += 3) {
        const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
        const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2];
        const vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
        const cx = uy * vz - uz * vy, cy = uz * vx - ux * vz, cz = ux * vy - uy * vx;
        const area = 0.5 * Math.hypot(cx, cy, cz);
        const n = Math.min(64, Math.ceil(area / step2));
        for (let m = 0; m < n; m++) {
          let r1 = ((m * 0.618034 + t * 0.1234) % 1), r2 = ((m * 0.754878 + t * 0.4321) % 1);
          if (r1 + r2 > 1) { r1 = 1 - r1; r2 = 1 - r2; }
          samples.push(P[a] + ux * r1 + vx * r2, P[a + 1] + uy * r1 + vy * r2, P[a + 2] + uz * r1 + vz * r2);
        }
      }
      for (const M of g.mats) for (let q = 0; q < samples.length; q += 3) {
        const x = samples[q], y = samples[q + 1], z = samples[q + 2];
        mark(M[0] * x + M[4] * y + M[8] * z + M[12], M[1] * x + M[5] * y + M[9] * z + M[13], M[2] * x + M[6] * y + M[10] * z + M[14]);
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
    // QA r1: a small lit lens (4 cm sprite) at the lamp + a warm pool on the seat from the shader spot term, not a floating
    // halo [V: tlfl_IMG_9377 / roame_7672 dimmed cabins: small lens, pool of light on the seat]
    this.spots = [];
    for (const s of this.layout.seats) {
      if (rnd() > 0.18) continue;
      let p, t;
      if (s.kind === 'room') { p = localToWorld(s, s.odd ? [0.03, 1.02, -1.18] : [-0.07, 1.02, 1.18]); t = localToWorld(s, s.odd ? [-0.24, 0.55, -0.75] : [0.20, 0.55, 0.75]); }
      else if (s.kind === 'suite') { p = localToWorld(s, [0.1, 1.06, -0.2]); t = localToWorld(s, [-0.1, 0.55, -0.55]); }
      else {
        const y = Math.abs(s.x) < 1.1 ? 1.82 : binBottomY(s.x * 0.92) - 0.03;
        p = [s.x * 0.92, y, s.z - (s.kind === 'py' ? 0.5 : 0.45)]; t = [s.x, 0.62, s.z - 0.3];
      }
      rm.push(M4.trs(p[0], p[1], p[2], 0, 0, 0, 0.04, 0.04, 0.04)); rt.push([2.4, 2.0, 1.4, 0]);
      this.spots.push({ p, t });
      // QA r2: amber PSU lens above each lit seat (~0.10 x 0.05 m lens, a 7 cm sprite peaking at #c07040)
      // [V: ucr_room-night-lighting PSU lamps #9e5e38; size A]
      const px = s.x * 0.92, py = Math.abs(s.x) < 1.1 ? 1.82 : binBottomY(px) - 0.03;
      const pz = s.kind === 'econ' || s.kind === 'py' ? p[2] + 0.12 : s.z;
      rm.push(M4.trs(px, py, pz, 0, 0, 0, 0.07, 0.07, 0.07)); rt.push([0.75, 0.44, 0.25, 0]);
    }
    gl.setInstances(this.readingMesh, rm, rt);
    // THE Room seat mood strips: warm LED line under each monitor bezel (bottom edge 0.645 m) and along the ottoman
    // toe line under the footwell mouth, SEATMAT.moodGlow [V: ucr_room-night-lighting strip under the screen #ffeb97;
    // upperclassroom review: mood lighting under the TV and the ottoman; strip sizes D from the 0.64 m bezel / 0.43 m
    // footwell mouth]. Their light on the console / footwell is the shader strip term (u_stripP, nearest 8)
    const sb = new Builder();
    this.strips = [];
    for (const s of this.layout.seats) {
      if (s.kind !== 'room') continue;
      const [xm, zf, dir, xo, zm] = s.odd ? [-0.245, MON.zO, -1, -0.345, MON.zO] : [0.21, MON.zE, 1, 0.34, MON.zE];
      for (const [x, y, z, w] of [[xm, 0.642, zf + dir * 0.02, 0.56], [xo, 0.03, zm - dir * 0.02, 0.40]]) {
        sb.add(gBox(w, 0.006, 0.012), M4.mul(unitXF(s), M4.trs(s.mir ? -x : x, y, z)), SEATMAT.moodGlow);
        const c = localToWorld(s, [x, y, z]), e = localToWorld(s, [x + w / 2, y, z]);
        this.strips.push({ p: c, a: V3.sub(e, c) });
      }
    }
    this.stripMesh = gl.mesh(sb.build(), { name: 'moodStrips', castShadow: false });
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
    for (let r = 0; r < 2; r++) for (let x = 0; x < N; x++) { const o = (r * N + x) * 4; d[o] = d[o + 1] = d[o + 2] = 235; d[o + 3] = 0; }
    let open = 0;
    this.layout.windows.forEach((w, i) => {
      const lv = this.winLevels[i];
      const T = SHADE_STATE.T(w, lv);
      open += SHADE_STATE.open(w, lv);
      const r = w.side > 0 ? 1 : 0;
      // alpha marks the window span (reveal glow in the shader), rgb the shade transmittance
      const a = Math.floor(((w.z - 0.24 - z0) / (z1 - z0)) * N), b = Math.ceil(((w.z + 0.24 - z0) / (z1 - z0)) * N);
      for (let x = Math.max(0, a); x <= Math.min(N - 1, b); x++) { const o = (r * N + x) * 4; d[o] = T[0] * 255; d[o + 1] = T[1] * 255; d[o + 2] = T[2] * 255; d[o + 3] = 255; }
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
    const winExp = this.xray ? 1 : 1 + ((sky.winExp || 1) - 1) * (1 - clamp((Math.abs(cam.pos[0]) - 2.0) / 0.45, 0, 1));
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
    G.set('u_sideLed', mood.sideLed || mood.led);
    // reading-light pools: the 8 lit lamps nearest the eye [A: count, a phone-sized loop]
    const sp = new Float32Array(32), st = new Float32Array(32);
    if (mood.readingLights && !this.xray) {
      const near = this.spots.map((q) => [V3.len(V3.sub(q.p, cam.pos)), q]).sort((a, b) => a[0] - b[0]).slice(0, 8);
      near.forEach(([, q], i) => { sp.set([...q.p, 1], i * 4); st.set([...q.t, 0], i * 4); });
    }
    G.set('u_spotP', sp); G.set('u_spotT', st);
    G.set('u_spotCol', [1.0, 0.85, 0.65].map((v) => v * 0.5));   // warm lamp colour [V: tlfl_IMG_9377], gain [A]
    // seat mood strips light the console top / footwell only in the dimmed moods (#ffd9a0 x 0.25 = SEATMAT.moodGlow)
    const spp = new Float32Array(32), spa = new Float32Array(32);
    if (mood.strips && !this.xray) {
      const near = this.strips.map((q) => [V3.len(V3.sub(q.p, cam.pos)), q]).sort((a, b) => a[0] - b[0]).slice(0, 8);
      near.forEach(([, q], i) => { spp.set([...q.p, 1], i * 4); spa.set([...q.a, 0], i * 4); });
    }
    G.set('u_stripP', spp); G.set('u_stripA', spa);
    G.set('u_stripCol', [0.25, 0.173, 0.087]);
    G.set('u_winGlow', winGlow);
    G.tex('u_ao', 1, this.ao.tex, gl.TEXTURE_3D);
    G.set('u_aoMin', this.ao.min);
    G.set('u_aoSize', this.ao.size);
    G.tex('u_detail', 2, this.tex.detail, gl.TEXTURE_2D_ARRAY);
    G.tex('u_photo', 5, this.tex.photo, gl.TEXTURE_2D_ARRAY); G.set('u_photoOn', PHOTO_PIX ? 1 : 0);
    const lp = new Float32Array(N_LAYERS * 4);
    for (const [kk, v] of Object.entries(LAYER_PARAMS)) lp.set(v, +kk * 4);
    G.set('u_layer', lp);
    G.tex('u_atlas', 3, this.tex.atlas);
    G.set('u_screenStep', ATL.screenStep);
    G.set('u_emisGain', this.mood === 'sleep' ? 0.55 : 1.0);
    G.set('u_screenGain', mood.screenGain || 0.8);   // QA r2 night 0.35 -> 0.6: the screen stays the brightest element [V: ucr_room-night-lighting]
    G.tex('u_win', 4, this.winTex);
    G.set('u_winZ', this.winZ);
    G.set('u_R', CAB.R + 0.10);
    G.set('u_yc', CAB.yc);
    G.set('u_exposure', mood.exposure);
    G.set('u_fill', this.fill ?? 0.45);   // QA r1: 0.7 flattened AO and the ceiling-to-floor falloff [V: c_27312 shell gradients]
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
      G.set('u_exposure', winExp);
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
    G.set('u_exposure', winExp);
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
