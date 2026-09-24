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
  // QA r3: AO weight on the hemisphere eased (0.85 -> 0.70) + bounce x1.15 + the sRGB display encode lift the
  // shadowed faces; exposures trimmed to hold the photo's lit tops and tone thirds [V: c_27312 thirds 190/109/88, p5 17].
  // Boarding keeps the white sidewall of ANA's official photos (c_27312, y_47300, py_37302, sans_14 at HND: no blue
  // band; from_integration / from_shell 1): a near-white lens with a light band cut. The saturated blue band that runs
  // down past the windows is the in-service cruise look [V: tlfl_IMG_9217 #5c5dc6, belt #736a88; sany_12 #556df7,
  // window line #5362e0; stwis_img_6082 #1961f9]
  boarding: { label: 'Boarding', hemiTop: [0.97, 0.99, 1.03], hemiBot: [0.36, 0.37, 0.40], wash: [0.25, 0.26, 0.28], led: [1.0, 0.98, 0.92], sideLed: [0.30, 0.31, 0.33], bandCut: 0.25, k: 1.05, exposure: 1.20 },
  cruise: { label: 'Cruise', hemiTop: [0.86, 0.88, 0.98], hemiBot: [0.24, 0.24, 0.28], wash: [0.25, 0.26, 0.30], led: [1.0, 0.98, 0.92], sideLed: [0.02, 0.05, 1.5], bandCut: 1.0, sideLow: 0.25, k: 0.95, exposure: 1.0 },
  // dining / sunrise, QA r2: ANA's amber phase is a saturated amber LED line on the bin lens and cove, amber-washed bin
  // faces and a much darker lower cabin, not a beige high key [V: ff_door-gap lens #ffa43d (h32 s0.76), bins #955b2d /
  // #673e1e (s ~0.7)]. Sunrise uses the same levels with a pinker LED [A: no ANA sunrise photo]
  // QA r3: led / sideLed inverted through ACES for #ffa33c at the cove / lens gains (the r2 [1, 0.22, 0.02] put G at
  // ~1.5 before ACES and clipped to lemon #fce04f) [D]; the vault wash is soft warm beige [V: ff_seat-with-door-closed
  // ceiling #d9b77d]; lowTint neutralises the amber below 1.25 m, so seat-level ash stays grey [V: ff_door-gap ash
  // #afafaf / #acb1ba, grey shell #6f7982]
  dining: { label: 'Dining', hemiTop: [0.62, 0.30, 0.11], hemiBot: [0.15, 0.07, 0.025], wash: [0.30, 0.14, 0.05], led: [0.55, 0.042, 0.009], sideLed: [1.25, 0.10, 0.02], sideLow: 0, sideWall: 0.4, bandCut: 0.3, vault: [1.1, 0.55, 0.24], lowTint: [0.93, 1.87, 4.7], k: 0.9, exposure: 1.3, strips: true },
  // night, QA r2: THE Room in service at night is near-black and neutral-warm; the light comes from the IFE screens, the
  // warm strip under each screen, small white reading lamps and amber PSU lamps [V: ucr_room-night-lighting ceiling
  // #1e1915, sidewall #24211c, bins #322a1f, PSU lamp #9e5e38, strip #ffeb97, mean RGB 39/34/33]. The blue night refs
  // used in r1 (roame_7672, sany_10) were boarding shots on the ground (daylight in the windows), so not the night scene
  // QA r3: cove / lens saturated amber (was warm white) [V: stwis_img_6223 cove #dc9340 / #b0671a (h25-32, s0.71-0.85),
  // ucr PSU lamp #9f5e39]; hemi unchanged (image mean already matches ucr 39/35/33)
  sleep: { label: 'Night', hemiTop: [0.030, 0.027, 0.024], hemiBot: [0.010, 0.009, 0.008], wash: [0.012, 0.010, 0.008], led: [0.070, 0.024, 0.004], sideLed: [0.035, 0.012, 0.002], sideLow: 0, vault: [0.045, 0.030, 0.018], k: 1, exposure: 2.2, readingLights: true, strips: true, screenGain: 0.6 },
  wake: { label: 'Sunrise', hemiTop: [0.62, 0.30, 0.16], hemiBot: [0.15, 0.07, 0.035], wash: [0.30, 0.14, 0.07], led: [0.55, 0.05, 0.03], sideLed: [1.2, 0.11, 0.06], sideLow: 0, sideWall: 0.4, bandCut: 0.3, vault: [1.1, 0.5, 0.34], lowTint: [0.93, 1.87, 3.3], k: 0.9, exposure: 1.3 },
};
// winExp: the view behind the glass at interior exposure; cabin photos show day windows near-white with a glowing
// reveal (tlfl_IMG_9217 / 9518, pane ~#eef3f8) [V]; eases back to 1 when the eye is at the window (looking out)
const SKIES = {
  // QA r3: winExp 1.6 -> 3.0: day panes must be the brightest thing in a cabin view, near-white against the wall
  // [V: c_27316 pane #ffffff vs wall #d1d1d1-#e2e2e2; y_47300 #fcfcfb; tlfl_IMG_9217 #fefefc]. Deeper day sky for the
  // look-out view (winExp eases to 1 at the window) [V: F-GSQR_1/_2 zenith #114892-#2472ca, from_exterior 2].
  // Exterior w5 (user: deep-blue cruise sky): zenith / horizon fitted with skyK 12 to #8fb8e6 (1 deg) #5d8cc4 (3) #3a66a0
  // (8.5) #2a4f86 (15) #1f4274 (25), between F-GSQR_1 and _2 [V photos, D fit].
  // extBounce = the lit deck seen by the exterior's undersides (0.55 x cloudLit) and extSun the exterior's sun scale
  // (the sun side of the cowl saturated at 5.2) [D: from_exterior 1 / 6; alv_ANA77W_NH211_26K cowl #9fabb7-#a9c0ce]
  day: { label: 'Day', sunEl: 30, sunAz: -60, sun: [5.2, 4.9, 4.4], zenith: [0.019, 0.05, 0.095], horizon: [0.20, 0.37, 1.0], skyK: 12, haze: [0.55, 0.66, 0.85], cloudLit: [1.25, 1.25, 1.25], cloudShade: [0.62, 0.68, 0.78], skyTop: [0.55, 0.68, 0.95], skyBot: [0.55, 0.55, 0.58], extBounce: [0.69, 0.69, 0.69], extSun: 0.6, winGlow: [0.45, 0.52, 0.62], winExp: 3.0, sunVis: 1, night: 0, sheer: 1.0 },
  // QA r3: dim blue-grey deck under a narrow orange horizon band, blue upper sky [V: Air_France_777-300ER_Greenland_
  // Sunrise deck #50595d-#646a67, band #d2a46d, sky #9cabaa; Emirates_77W_wing_view / alv_7282 zenith #527dc2]; dark cool
  // deck bounce and a grazing sun at 0.35 on the exterior, so the wing takes the sky colour (from_exterior 3)
  sunset: { label: 'Sunset', sunEl: 5, sunAz: 110, sun: [4.2, 2.2, 0.9], zenith: [0.08, 0.14, 0.42], horizon: [1.1, 0.55, 0.30], haze: [0.10, 0.11, 0.12], cloudLit: [0.075, 0.085, 0.095], cloudShade: [0.018, 0.024, 0.034], skyTop: [0.18, 0.24, 0.55], skyBot: [0.4, 0.26, 0.2], extBounce: [0.07, 0.08, 0.10], extSun: 0.35, winGlow: [0.22, 0.12, 0.08], sunVis: 1, night: 0, sheer: 0.7 },
  night: { label: 'Night', sunEl: 38, sunAz: -40, sun: [0.07, 0.08, 0.12], zenith: [0.004, 0.006, 0.016], horizon: [0.02, 0.028, 0.05], haze: [0.018, 0.022, 0.036], cloudLit: [0.05, 0.055, 0.07], cloudShade: [0.012, 0.014, 0.02], skyTop: [0.02, 0.025, 0.04], skyBot: [0.01, 0.01, 0.015], extBounce: [0.028, 0.030, 0.038], extSun: 1, winGlow: [0.0, 0.0, 0.0], sunVis: 0, night: 1, sheer: 0.06 },
};
// QA r3 ambient-occlusion tuning [D: q06 / q15 / q03 / q05 / q14 against c_27312, y_47300, omaat_f11, f_17313,
// py_37301]: hemi = unoccluded share of the hemisphere fill (was 0.15), bounce = interreflection gain, emitLens /
// emitCtr = sky value of the air under the outboard bins (sidewall lens band) and under the centre bins, kAttF = voxel
// attenuation inside THE Suite zone (1.35 elsewhere)
const AO_TUNE = { hemi: 0.22, bounce: 1.0, emitLens: 0.45, emitCtr: 0.35, kAttF: 0.8 };
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
    // ~8.3 cm voxels (QA r1: 10 cm cells could not resolve the 0.1 m footwells / console gaps) [D]
    const nx = 72, ny = 34, nz = 712;
    const min = [-3.0, 0, 2.6], size = [6.0, 2.8, 59.2];
    const cell = [size[0] / nx, size[1] / ny, size[2] / nz];
    const occ = new Float32Array(nx * ny * nz);
    const solid = new Uint8Array(nx * ny * nz);   // bins, monuments and the space outside the wall (not seat voxels)
    const idx = (i, j, k) => (k * ny + j) * nx + i;
    const box = (x0, x1, y0, y1, z0, z1, d = 1) => {
      const i0 = Math.max(0, Math.floor((x0 - min[0]) / cell[0])), i1 = Math.min(nx - 1, Math.floor((x1 - min[0]) / cell[0]));
      const j0 = Math.max(0, Math.floor((y0 - min[1]) / cell[1])), j1 = Math.min(ny - 1, Math.floor((y1 - min[1]) / cell[1]));
      const k0 = Math.max(0, Math.floor((z0 - min[2]) / cell[2])), k1 = Math.min(nz - 1, Math.floor((z1 - min[2]) / cell[2]));
      for (let k = k0; k <= k1; k++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) { const q = idx(i, j, k); occ[q] = Math.min(1, occ[q] + d); if (d >= 1) solid[q] = 1; }
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
      for (let i = 0; i < nx; i++) { const x = min[0] + (i + 0.5) * cell[0]; if (Math.abs(x) > xw) for (let k = 0; k < nz; k++) { occ[idx(i, j, k)] = 1; solid[idx(i, j, k)] = 1; } }
    }
    // QA r3: THE Suite geometry occludes less (kAtt 0.8 in the F zone): the 1.3 m shells are open-topped under the
    // bright ceiling, and the ottoman / console / pier read near-black next to a white wall where the daylight photos
    // show mid-tones [V: f_17300, omaat_f2 / f5 / f11 ottoman #9f8c85, console #514537; q03 #312f2d]
    const kAtt = 1.35, kAttF = AO_TUNE.kAttF;
    const fz = this.layout.zones.find((zn) => zn.cls === 'F');
    const kf0 = fz ? Math.floor((fz.z0 - min[2]) / cell[2]) : -1, kf1 = fz ? Math.floor((fz.z1 - min[2]) / cell[2]) : -1;
    const att = new Float32Array(occ.length);
    for (let q = 0; q < occ.length; q++) { const k = Math.floor(q / (nx * ny)); att[q] = Math.exp(-(k >= kf0 && k <= kf1 && !solid[q] ? kAttF : kAtt) * occ[q]); }
    // QA r3: emitter cells. The sweep only sees the ceiling, so everything under the outboard bins read 0 (window seats,
    // the inside of THE Suite) although the sidewall lens, the lit bin undersides and the windows light it. Air cells in
    // the lens band (y 1.30-1.60, |x| 1.55 to the wall) count as sky at 0.45 and the strip under the centre bins
    // (y 1.74-1.84, |x| < 0.83) at 0.35, in the seat zones (bins above) [D: probe of the volume; q05 ottoman 62 -> 98 L
    // vs f_17313 97, q14 median 68 -> 114 vs py_37301 117; 0.55 overshot the suite caps under the lens]
    const emit = new Float32Array(occ.length);
    for (const zn of this.layout.zones) {
      if (zn.type !== 'seat') continue;
      const k0 = Math.max(0, Math.floor((zn.z0 - min[2]) / cell[2])), k1 = Math.min(nz - 1, Math.floor((zn.z1 - min[2]) / cell[2]));
      for (let j = 0; j < ny; j++) {
        const y = min[1] + (j + 0.5) * cell[1];
        const xw = wallAt(y)[0];
        for (let i = 0; i < nx; i++) {
          const ax = Math.abs(min[0] + (i + 0.5) * cell[0]);
          const e = y > 1.30 && y < 1.60 && ax > 1.55 && ax < xw ? AO_TUNE.emitLens : y > 1.74 && y < 1.84 && ax < 0.83 ? AO_TUNE.emitCtr : 0;
          if (e) for (let k = k0; k <= k1; k++) { const q = idx(i, j, k); if (!solid[q]) emit[q] = e; }
        }
      }
    }
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
          if (emit[q] > V) V = emit[q];
          acc[q] += wgt * V;
          cur[k * nx + i] = V * att[q];
        }
        const t = prev; prev = cur; cur = t;
      }
    }
    // QA r3: three separable [1/4, 1/2, 1/4] passes (i, j, k) smooth the 9-direction sweep's V-shaped wedges on flat
    // walls (q19 closet faces vs py_37302 uniform bulkhead); solid cells (walls, bins, monuments) are not averaged in,
    // so the faces next to them do not darken [D]
    const tmp = new Float32Array(acc.length);
    for (const [di, n, stride] of [[0, nx, 1], [1, ny, nx], [2, nz, nx * ny]]) {
      tmp.set(acc);
      for (let k = 0; k < nz; k++) for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
        const q = idx(i, j, k);
        if (solid[q]) continue;
        const c = di === 0 ? i : di === 1 ? j : k;
        const a = c > 0 && !solid[q - stride] ? tmp[q - stride] : tmp[q];
        const b = c < n - 1 && !solid[q + stride] ? tmp[q + stride] : tmp[q];
        acc[q] = 0.25 * a + 0.5 * tmp[q] + 0.25 * b;
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
    // flat 16-gon oval facing down, 0.10 m fore-aft x 0.045 m across
    const oval = raw();
    oval.p.push(0, 0, 0); oval.n.push(0, -1, 0); oval.u.push(0.5, 0.5);
    for (let k = 0; k < 16; k++) {
      const a = (k / 16) * Math.PI * 2;
      oval.p.push(Math.sin(a) * 0.0225, 0, Math.cos(a) * 0.05); oval.n.push(0, -1, 0); oval.u.push(0.5 + Math.sin(a) / 2, 0.5 + Math.cos(a) / 2);
      oval.i.push(0, 1 + k, 1 + ((k + 1) % 16));
    }
    fixWinding(oval);
    const lens = new Builder();
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
      // amber PSU lamp above each lit seat. QA r3: a crisp emissive oval lens (0.10 x 0.045 m) flush under the PSU
      // plus a 3 cm core sprite, not a 7 cm halo floating in front of the bin [V: ucr_room-night-lighting sharp ~2:1
      // oval lenses, core #ac6437, small halo; size A; e 0.25 gives the #ac6437 core at the night gains D]
      const px = s.x * 0.92, ctr = Math.abs(px) < 1.1;
      const py = ctr ? CBIN_Y - 0.011 : binBottomY(px) - 0.0085;
      const pz = s.kind === 'econ' || s.kind === 'py' ? p[2] + 0.12 : s.z;
      rm.push(M4.trs(px, py - 0.004, pz, 0, 0, 0, 0.03, 0.03, 0.03)); rt.push([1.1, 0.6, 0.3, 0]);
      lens.add(oval, M4.trs(px, py, pz, 0, 0, ctr ? 0 : -TILT_O * Math.sign(px)), { c: '#c07040', r: 0.4, e: 0.25 });
    }
    gl.setInstances(this.readingMesh, rm, rt);
    this.psuLensMesh = gl.mesh(lens.build(), { name: 'psuLens', castShadow: false });
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
    // QA r3: 4096 texels (1.4 cm, was 5.8 cm) and 0 between the windows: the skin is opaque, so the sun only enters
    // through a pane (was 0.92 everywhere, leaving the shadow map alone to stop it: hairline streaks on the seat backs,
    // q15). rgb = shade transmittance over the glass +-0.127 m [V: 10 in] with a 3 cm soft edge; alpha = the reveal
    // glow, full over +-0.22 m and cosine-feathered to 0 at +-0.30 m (was a hard 0.48 m block: pale rectangles round
    // each window, from_shell 2)
    const N = 4096, d = new Uint8Array(N * 2 * 4);
    const z0 = this.ao ? this.ao.min[2] : 2.6, z1 = z0 + 59.2, dz = (z1 - z0) / N;
    let open = 0;
    this.layout.windows.forEach((w, i) => {
      const lv = this.winLevels[i];
      const T = SHADE_STATE.T(w, lv);
      open += SHADE_STATE.open(w, lv);
      const r = w.side > 0 ? 1 : 0;
      const a = Math.floor((w.z - 0.30 - z0) / dz), b = Math.ceil((w.z + 0.30 - z0) / dz);
      for (let x = Math.max(0, a); x <= Math.min(N - 1, b); x++) {
        const u = Math.abs(z0 + (x + 0.5) * dz - w.z), o = (r * N + x) * 4;
        const e = clamp((0.157 - u) / 0.03, 0, 1), tr = e * e * (3 - 2 * e);
        const gw = u < 0.22 ? 1 : 0.5 + 0.5 * Math.cos(Math.PI * clamp((u - 0.22) / 0.08, 0, 1));
        for (let c = 0; c < 3; c++) d[o + c] = Math.max(d[o + c], Math.round(T[c] * tr * 255));
        d[o + 3] = Math.max(d[o + 3], Math.round(gw * 255));
      }
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

  // sun shadow map. QA r3: fitted to a cabin slice round the camera (zc +-11 m: ~4x the texel density of the whole
  // 59 m cabin, so the sun-patch edges no longer stair-step [V: omaat_f57 / f58 soft patches]); render() re-fits it when
  // the slice centre moves 2 m. No zc (studio) = the whole cabin. Seats outside the slice are left out of the pass
  renderShadow(zc) {
    const G = this.gl, gl = G.gl;
    const L = this.sunDir();
    const full = zc === undefined;
    const za = full ? 2.6 : clamp(zc - 11, 2.6, 50.6), zb = full ? 61.6 : za + 22;
    const center = [0, 1.2, (za + zb) / 2];
    const view = M4.lookAt(V3.add(center, V3.scale(L, 45)), center, Math.abs(L[1]) > 0.95 ? [0, 0, 1] : [0, 1, 0]);
    const corners = [];
    for (const x of [-3.1, 3.1]) for (const y of [-0.1, 2.6]) for (const z of [za, zb]) corners.push(M4.point(view, [x, y, z]));
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
    for (const g of Object.values(this.seatGroups)) {
      let buf = g.master, n = g.n;
      if (!full) {
        buf = g.hiBuf || (g.hiBuf = new Float32Array(g.n * 20)); n = 0;
        for (let i = 0; i < g.n; i++) {
          const o = i * 20, z = g.master[o + 14];
          if (g.master[o + 13] > -10 && z > za - 1.5 && z < zb + 1.5) { buf.set(g.master.subarray(o, o + 20), n * 20); n++; }
        }
      }
      G.setInstancesRaw(g.hi, buf, n); if (g.lo) G.setInstancesRaw(g.lo, g.master, 0); g.dirty = true;
    }
    for (const m of this.opaque) if (m.castShadow && m.visible) G.draw(m);
    gl.disable(gl.POLYGON_OFFSET_FILL);
    gl.enable(gl.CULL_FACE);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    this.shadowDirty = false;
    this.shadowZ = full ? null : zc;
  }

  render(cam, w, h, time) {
    const G = this.gl, gl = G.gl;
    G.stats.calls = 0; G.stats.tris = 0;
    const sky = SKIES[this.sky], mood = MOODS[this.mood];
    const zc = clamp(cam.pos[2] + cam.fwd[2] * 5, 2.6, 61.6);   // slice centre 5 m ahead of the eye
    if (this.shadowDirty || this.shadowZ == null || Math.abs(zc - this.shadowZ) > 2) this.renderShadow(zc);
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
    G.set('u_vault', mood.vault || mood.led);
    G.set('u_lowTint', mood.lowTint || [1, 1, 1]);
    G.set('u_aoTune', [AO_TUNE.hemi, AO_TUNE.bounce]);
    G.set('u_bandCut', mood.bandCut ?? 0.65); G.set('u_sideLow', [mood.sideLow ?? 0.4, mood.sideWall ?? 1]);
    G.set('u_extBounce', [0, 0, 0]);
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
    // QA r3: the THE Room mood strips are lit only in the dimmed moods (day photos c_27312 / ff_seat-with-door-closed
    // show nothing lit under the monitor; ucr_room-night-lighting at night does) [V]; PSU amber lenses with the reading lamps
    if (mood.strips) G.draw(this.stripMesh);
    if (mood.readingLights && !this.xray) G.draw(this.psuLensMesh);
    if (!this.xray) {
      G.set('u_exterior', 1);
      G.set('u_exposure', winExp);
      // exterior: cloud-deck bounce and a lower sun (from_exterior 1 / 6: the sun side of the cowl saturated at 5.2)
      G.set('u_extBounce', sky.extBounce);
      G.set('u_sunCol', sky.sun.map((v) => v * sky.extSun));
      // up to two exterior lights with a `light` gain light the airframe at night, blinking like their glow sprite
      const pp = new Float32Array(8), pc = new Float32Array(6);
      let np = 0;
      for (const l of this.ext.lights) {
        if (!l.light || !sky.night || np > 1) continue;
        const on = l.blink > 1.5 ? ((time * 0.9 + l.blink) % 1 >= 0.92 ? 1 : 0) : 1;
        pp.set([...l.p, 1], np * 4); pc.set(l.c.map((v) => v * l.light * on), np * 3); np++;
      }
      G.set('u_extPtP', pp); G.set('u_extPtC', pc);
      G.draw(this.ext.mesh);
      G.set('u_extBounce', [0, 0, 0]); G.set('u_extPtP', new Float32Array(8));   // the studio (same program) keeps its plain fill
    }
    gl.depthFunc(gl.LEQUAL);
    gl.depthMask(false);
    const S = this.progs.sky;
    G.use(S);
    G.set('u_invViewProj', M4.invert(vp));
    G.set('u_camPos', cam.pos);
    G.set('u_sunDir', L);
    G.set('u_time', time);
    G.set('u_zenith', sky.zenith); G.set('u_horizon', sky.horizon); G.set('u_haze', sky.haze); G.set('u_skyK', sky.skyK || 0);
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
