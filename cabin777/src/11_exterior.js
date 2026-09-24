// ------------------------------------------------------------------
// Exterior seen through the windows: 777-300ER wing (raked tips) + GE90-115B nacelles.
// Source: Boeing D6-58329-2 "777-200LR/-300ER Airplane Characteristics for Airport Planning" (ACAP):
//   2.2.2 general dimensions (span 64.80, nose->wing LE at side of body 26.89, nose->inlet 25.76, nacelle 9.61 off CL,
//   nose->tip 48.50 / 49.11), 2.3.2 ground clearances, 2.7.1 door stations (D3 32.92), 9.9.1 1:500 plan (planform,
//   slat breaks, spoilers, aileron and flap-track marks digitised) [V]. Stations are ACAP nose stations shifted so ACAP
//   door 3 lands on the model's door 3; heights are above the cabin floor (ACAP floor 5.08 m above ground) [D].
//   Check [D]: gross area 449.7 m2 (LE extended to CL) vs 436.8 m2 reference, c/4 sweep 31.1 deg vs 31.6 deg.
// Colours: ANA 777-300ER photos (JA787A/791A/796A/797A, 2024-25): white cowls with no titles, silver inlet lip, grey
// core cowl, black spinner with a white swirl, grey wing with bare-metal slat noses [V].
// ------------------------------------------------------------------
function naca(x, t) { return 5 * t * (0.2969 * Math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x * x * x - 0.1036 * x * x * x * x); }
const WING = {
  dz: CAB.doors[2] - 32.92,        // ACAP nose station -> model z (door-3 anchor) [D]
  s0: 2.9,                         // root buried in the body side (6.20 m fuselage); tip at 32.40 = 64.80 m span [V]
  // leading / trailing edge [spanwise from CL, nose station]; LE sweep 34.2 deg to the rake, TE straight to the
  // yehudi kink at ~9-12 m then ~20 deg; raked tip from 31.1 m [D, ACAP 9.9.1]
  le: [[3.10, 26.89], [31.10, 45.93], [31.40, 46.42], [31.80, 47.22], [32.10, 47.90], [32.40, 48.50]],
  te: [[3.10, 39.96], [8.60, 39.96], [10.0, 40.17], [11.0, 40.36], [12.0, 40.69], [20.0, 43.40], [29.5, 47.05], [31.0, 47.98], [32.40, 49.05]],
  // upper-surface crest above the floor: ACAP front view, 5.2 deg on the ground [D], plus 1g cruise bending that lifts the
  // tip ~1.5 m (quadratic outboard of the root; the leading edge curves up to the tip in F-GSQR_1/_2 window views [V
  // shape], magnitude [A] tuned on a 17A render vs F-GSQR_2). Inboard of the nacelle it adds < 0.06 m, so the engine
  // and pylon keep the ground-static height.
  crest: (s) => -0.02 + (s - 4) * 0.0915 + 1.5 * Math.pow(Math.max(0, s - 4) / 28.4, 2),
  th: [0.155, 0.115],              // NACA thickness param root -> tip (x0.81 with the flattened lower side): ~12.6 -> 9.3 % [A]
  eng: { s: 9.61, y: -2.19, x0: 25.76 },   // nacelle axis off CL [V], axis height [D ACAP side view], inlet highlight [V]
  slats: [11.7, 13.6, 16.6, 19.6, 22.6, 25.4, 28.1, 31.0],   // 7 outboard slats (ACAP break ticks) + 1 inboard 3.3-8.2 [D]
  // 4 flap-track fairings per side outboard of the root (plus the pylon aft fairing): HL8007 planform photo, 14.5 px/m
  // from the 73.86 m fuselage, canoes at s ~ 8.7 / 10.7-11.5 / 13.6-14.6 / 19.1-20.5 m [V photo, D positions]; lengths [D ACAP 9.9.1]
  // w1: outboard pair moved to the outboard-flap supports ~25 % from each flap end [V NASA CR-1998-196709 via rater B;
  // spacing checked on ANA JA795A seat-26K photos alv_*_7329/_7331]
  canoes: [[8.4, 4.6], [11.1, 3.8], [14.7, 4.3], [20.4, 3.4]],
};
function pwl(tab, s) {
  let k = 0;
  while (k < tab.length - 2 && s > tab[k + 1][0]) k++;
  const [a, b] = [tab[k], tab[k + 1]];
  return a[1] + ((s - a[0]) / (b[0] - a[0])) * (b[1] - a[1]);
}
function wingStation(s) {
  const le = pwl(WING.le, s), te = pwl(WING.te, s), c = te - le;
  const th = lerp(WING.th[0], WING.th[1], clamp((s - 3) / 29.4, 0, 1));
  const y0 = WING.crest(s) - (0.018 * Math.sin(0.3 * Math.PI) + naca(0.3, th)) * c;
  return { s, le, c, th, y0 };
}
function wingSurf(st, cx, sgn, side, lift = 0) {
  cx = clamp(cx, 0, 1);
  const yy = (0.018 * Math.sin(Math.PI * cx) + sgn * naca(Math.max(cx, 1e-4), st.th) * (sgn < 0 ? 0.62 : 1)) * st.c;
  return [st.s * side, st.y0 + yy + lift * sgn, st.le + cx * st.c + WING.dz];
}
// upper (sgn 1) / lower (-1) surface point at spanwise s and nose station xn
const wingAt = (s, xn, side, sgn = 1, lift = 0) => { const st = wingStation(s); return wingSurf(st, (xn - st.le) / st.c, sgn, side, lift); };

function wingGeo(side) {
  const g = raw();
  const S = [WING.s0, 3.6, 4.5, 5.5, 6.5, 7.5, 8.6, 9.3, 10, 10.5, 11, 11.5, 12];
  for (let s = 13; s <= 30; s++) S.push(s);
  S.push(30.5, 31.0, 31.2, 31.4, 31.6, 31.8, 32.0, 32.2, 32.4);
  const NC = 24, pts = [];
  for (let k = 0; k <= NC; k++) pts.push([0.5 - 0.5 * Math.cos(Math.PI * (NC - k) / NC), 1]);   // upper TE -> LE
  for (let k = 1; k < NC; k++) pts.push([0.5 - 0.5 * Math.cos(Math.PI * k / NC), -1]);          // lower LE -> TE
  const NP = pts.length, stations = S.map(wingStation);
  for (const st of stations) for (const [cx, sgn] of pts) { g.p.push(...wingSurf(st, cx, sgn, side)); g.n.push(0, 1, 0); g.u.push(cx, st.s); }
  for (let s = 0; s < S.length - 1; s++) for (let k = 0; k < NP; k++) {
    const a = s * NP + k, b = s * NP + ((k + 1) % NP), c = a + NP, d = b + NP;
    g.i.push(a, b, d, a, d, c);
  }
  computeNormals(g);
  const topIdx = Math.floor(NC / 2);
  if (g.n[topIdx * 3 + 1] < 0) { for (let k = 0; k < g.n.length; k++) g.n[k] = -g.n[k]; for (let t = 0; t < g.i.length; t += 3) { const tmp = g.i[t + 1]; g.i[t + 1] = g.i[t + 2]; g.i[t + 2] = tmp; } }
  // root + tip caps (fans)
  for (const [j, dir] of [[0, -side], [S.length - 1, side]]) {
    const c0 = g.p.length / 3, base = j * NP;
    let cx = 0, cy = 0, cz = 0;
    for (let k = 0; k < NP; k++) { cx += g.p[(base + k) * 3] / NP; cy += g.p[(base + k) * 3 + 1] / NP; cz += g.p[(base + k) * 3 + 2] / NP; }
    g.p.push(cx, cy, cz); g.n.push(dir, 0, 0); g.u.push(0.5, S[j]);
    for (let k = 0; k < NP; k++) { g.p.push(g.p[(base + k) * 3], g.p[(base + k) * 3 + 1], g.p[(base + k) * 3 + 2]); g.n.push(dir, 0, 0); g.u.push(0.5, S[j]); }
    for (let k = 0; k < NP; k++) {
      const a = c0 + 1 + k, b = c0 + 1 + ((k + 1) % NP), p = g.p;
      const e1 = [p[a * 3] - cx, p[a * 3 + 1] - cy, p[a * 3 + 2] - cz], e2 = [p[b * 3] - cx, p[b * 3 + 1] - cy, p[b * 3 + 2] - cz];
      if (V3.cross(e1, e2)[0] * dir > 0) g.i.push(c0, a, b); else g.i.push(c0, b, a);
    }
  }
  return { g, stations };
}

// recolour vertices [v0, end) of a Builder where fn(p, uv) returns a material
function paintVerts(B, v0, fn) {
  for (let k = v0; k < B.vcount; k++) {
    const m = fn([B.p[k * 3], B.p[k * 3 + 1], B.p[k * 3 + 2]], [B.u[k * 2], B.u[k * 2 + 1]]);
    if (!m) continue;
    const c = hexRGB(m.c);
    B.c[k * 4] = c[0]; B.c[k * 4 + 1] = c[1]; B.c[k * 4 + 2] = c[2];
    B.m[k * 4] = Math.round(clamp(m.r ?? 0.6, 0.02, 1) * 255); B.m[k * 4 + 1] = Math.round(clamp(m.m ?? 0, 0, 1) * 255);
  }
}
// multiply the baked colour of vertices [v0, v1) by fn(p, n) (cheap occlusion term)
function shadeVerts(B, v0, v1, fn) {
  for (let k = v0; k < v1; k++) {
    const f = fn([B.p[k * 3], B.p[k * 3 + 1], B.p[k * 3 + 2]], [B.n[k * 3], B.n[k * 3 + 1], B.n[k * 3 + 2]]);
    if (f >= 1) continue;
    for (let c = 0; c < 3; c++) B.c[k * 4 + c] = Math.round(B.c[k * 4 + c] * f);
  }
}
// thin strip lying on the wing surface along a polyline in (s, nose station) space
function wingLine(B, side, path, mat, w = 0.035, sgn = 1, lift = 0.012) {
  const g = raw();
  for (let k = 0; k < path.length; k++) {
    const a = path[Math.max(0, k - 1)], b = path[Math.min(path.length - 1, k + 1)];
    const ts = b[0] - a[0], tx = b[1] - a[1], l = Math.hypot(ts, tx) || 1;
    const ps = (-tx / l) * w / 2, px = (ts / l) * w / 2;
    // lifted 12 mm off the skin: 6 mm z-fought (shimmer) at the 20-30 m window-view range [A]
    g.p.push(...wingAt(path[k][0] + ps, path[k][1] + px, side, sgn, lift), ...wingAt(path[k][0] - ps, path[k][1] - px, side, sgn, lift));
    // skin normal (finite differences) so a strip is lit like the panel it lies on, not brighter
    const [s0, x0] = path[k], p0 = wingAt(s0, x0, side, sgn), dS = V3.sub(wingAt(s0 + 0.05, x0, side, sgn), p0), dX = V3.sub(wingAt(s0, x0 + 0.05, side, sgn), p0);
    let nn = V3.norm(V3.cross(dS, dX)); if (nn[1] * sgn < 0) nn = nn.map((v) => -v);
    g.n.push(...nn, ...nn); g.u.push(0, 0, 1, 0);
  }
  for (let k = 0; k < path.length - 1; k++) { const q = k * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
  B.add(fixWinding(g), null, mat);
}
const spanPath = (s0, s1, xnFn, n = 12) => Array.from({ length: n + 1 }, (_, k) => { const s = lerp(s0, s1, k / n); return [s, xnFn(s)]; });
const chordPath = (s, x0, x1) => [[s, x0], [s, lerp(x0, x1, 0.5)], [s, x1]];

function nacelleGeo() {
  // lathe profiles [r, x aft of the inlet highlight] along +y, rotated onto +z. Max 4.18 m (164-166 in) [V Wikipedia/GE
  // via a.net], inlet 3.43 m (135 in) [V a.net], fan 3.25 m / 22 blades [V], fan nozzle 2.96 m, core 2.1 -> 1.6 m,
  // plug to 7.28 m (engine length 7.281 m) [D ACAP side view + V Wikipedia]; lip/section shapes [A]
  const lip = [[1.715, 0.0], [1.79, 0.035], [1.87, 0.11], [1.94, 0.26]];
  const cowl = [[1.94, 0.26], [2.02, 0.6], [2.07, 1.1], [2.09, 1.7], [2.09, 2.4], [2.06, 3.1], [1.99, 3.8], [1.87, 4.4], [1.70, 4.84], [1.50, 5.0]];
  const nozIn = [[1.50, 5.0], [1.44, 4.82], [1.40, 4.55]].reverse();
  const inlet = [[1.715, 0.0], [1.695, 0.08], [1.665, 0.3], [1.645, 0.75], [1.635, 1.3]].reverse();
  const core = [[1.13, 4.3], [1.10, 5.0], [1.02, 5.6], [0.92, 6.1], [0.84, 6.35]];
  const coreIn = [[0.84, 6.35], [0.76, 6.3], [0.70, 6.1]].reverse();
  const plug = [[0.64, 6.1], [0.62, 6.45], [0.52, 6.8], [0.34, 7.08], [0.10, 7.25], [0.0, 7.28]];
  const spinner = [[0.0, 0.42], [0.1, 0.46], [0.22, 0.56], [0.34, 0.72], [0.44, 0.94], [0.51, 1.2], [0.53, 1.45]];
  const L = (p, seg = 48) => gLathe(p.map(([r, x]) => [r, x]), seg);
  return { lip: L(lip), cowl: L(cowl), nozIn: L(nozIn), inlet: L(inlet), core: L(core, 40), coreIn: L(coreIn, 40), plug: L(plug, 32), spinner: L(spinner, 32) };
}
function fanBlades(n = 22) {
  // swept, twisted composite blades: chord 0.32 -> 0.60 m, stagger 28 -> 58 deg (hub -> tip) [A]
  const g = raw();
  for (let b = 0; b < n; b++) {
    const a0 = (b / n) * Math.PI * 2, base = g.p.length / 3;
    for (let j = 0; j <= 4; j++) {
      const t = j / 4, r = lerp(0.5, 1.615, t), ch = lerp(0.32, 0.60, t), st = lerp(28, 58, t) * DEG, sw = 0.10 * t * t;
      const a = a0 + sw / r;
      for (const e of [-0.5, 0.5]) {
        const dt = e * ch * Math.sin(st), dx = e * ch * Math.cos(st);
        const aa = a + dt / r;
        g.p.push(Math.cos(aa) * r, 1.42 + dx + 0.06 * t, Math.sin(aa) * r); g.n.push(0, -1, 0); g.u.push(e + 0.5, t);
      }
    }
    for (let j = 0; j < 4; j++) { const q = base + j * 2; g.i.push(q, q + 1, q + 3, q, q + 3, q + 2); }
  }
  computeNormals(g);
  // back faces: duplicate with flipped winding and normals (the exterior is drawn with culling)
  const nv = g.p.length / 3, ni = g.i.length;
  for (let k = 0; k < nv; k++) { g.p.push(g.p[k * 3], g.p[k * 3 + 1], g.p[k * 3 + 2]); g.n.push(-g.n[k * 3], -g.n[k * 3 + 1], -g.n[k * 3 + 2]); g.u.push(g.u[k * 2], g.u[k * 2 + 1]); }
  for (let t = 0; t < ni; t += 3) g.i.push(g.i[t] + nv, g.i[t + 2] + nv, g.i[t + 1] + nv);
  return g;
}

function buildExterior(gl) {
  const B = new Builder();
  // Boeing grey wing. Albedo tuned so the sunlit upper wing renders ~#9098a0 in the day sky, matching cabin photos
  // F-GSQR_1 (lit wing #8c8d8f-#a3a4a8 under a #6585ab sky) and F-GSQR_2 (#aeb1b8 under a brighter sky) [V photos, D value]
  const paint = { c: '#636466', r: 0.5, m: 0.1 };   // w1: r 0.6 -> 0.5, gloss sheen toward the sky in ANA 26K photos [V shape, A value]
  const paintLow = { c: '#5c5d5f', r: 0.62, m: 0.1 };
  const metal = { c: '#c3c7cc', r: 0.26, m: 0.85 };             // bare slat nose / inlet lip
  // control-surface / slat / spoiler gaps read as near-black hairlines: F-GSQR_1 row y=800 wing #a3a4a8 -> gap
  // #232732 / #2d3447 -> wing #9ba1a1; spoiler panel seams dark too, a shade lighter [V photos, Boeing_777_(4139974954)]
  const line = { c: '#343940', r: 0.95 };   // matte: a glossy strip mirrors the sky at grazing view [A]
  const gap = { c: '#1e2228', r: 1.0, m: 0 };
  const cowl = { c: '#d6d9dd', r: 0.3, m: 0.1 };                // ANA white fan cowl, no titles [V photos]; w2: w1 gloss mirrored the
                                                                // pale sky into a flat blob; darkening now baked from the normal below [A]
  const seam = { c: '#b9bdc2', r: 0.4 };
  const core = { c: '#8e9398', r: 0.34, m: 0.7 };
  const plug = { c: '#6e6b67', r: 0.4, m: 0.6 };
  const dark = { c: '#141619', r: 0.55, m: 0.3 };
  const blade = { c: '#2b2e33', r: 0.35, m: 0.6 };
  const spin = { c: '#16181b', r: 0.22, m: 0.2 };
  const white = { c: '#f2f2f2', r: 0.3 };
  const lights = [];
  const E = WING.eng;
  for (const side of [-1, 1]) {
    const v0 = B.vcount;
    const { g, stations } = wingGeo(side);
    B.add(g, null, paint);
    // bare-metal slat nose band ~0.045 chord (0.022 read as a hairline; ANA 11A _137 shows a broad bright LE) [V photo, A width];
    // +-3 % tone per skin panel (~2.2 m spanwise x chord quarters): panel-to-panel paint shade seen in the 26K photos [V, A amount]
    paintVerts(B, v0, (p, uv) => {
      if (uv[0] < 0.045) return metal;
      const h = Math.sin(Math.floor(uv[1] / 2.2) * 12.9898 + Math.floor(uv[0] * 4) * 78.233) * 43758.5453, f = 1 + 0.10 * (h - Math.floor(h) - 0.5);
      const c = hexRGB(paint.c).map((v) => Math.round(clamp(v * f, 0, 255)).toString(16).padStart(2, '0'));
      return { c: '#' + c.join(''), r: paint.r, m: paint.m };
    });
    // slats (outboard 7 + inboard 1): chord line and breaks
    wingLine(B, side, spanPath(11.7, 31.0, (s) => pwl(WING.le, s) + 0.66, 16), gap, 0.03);
    for (const s of WING.slats) wingLine(B, side, chordPath(s, pwl(WING.le, s) - 0.05, pwl(WING.le, s) + 0.66), gap, 0.03);
    wingLine(B, side, spanPath(3.3, 8.2, (s) => pwl(WING.le, s) + 0.95, 4), gap, 0.03);
    for (const s of [3.3, 8.2]) wingLine(B, side, chordPath(s, pwl(WING.le, s) - 0.05, pwl(WING.le, s) + 0.95), gap, 0.03);
    // spoilers: 2 inboard (37.82-38.82) + 5 outboard ahead of the outboard flap [D ACAP 9.9.1]; split of the inboard pair [A]
    const spF = (s) => pwl(WING.te, s) - lerp(1.6, 1.2, (s - 11.8) / 9.2), spA = (s) => pwl(WING.te, s) - lerp(0.75, 0.55, (s - 11.8) / 9.2);
    wingLine(B, side, spanPath(4.5, 8.6, () => 37.82, 2), line);
    wingLine(B, side, spanPath(3.1, 9.8, () => 38.82, 3), gap);
    for (const s of [4.5, 6.55, 8.6]) wingLine(B, side, chordPath(s, 37.82, 38.82), line);
    wingLine(B, side, spanPath(11.8, 21.0, spF, 8), line);
    wingLine(B, side, spanPath(11.8, 23.3, (s) => (s < 21 ? spA(s) : spA(21) + (s - 21) * 0.34), 10), gap);
    for (let k = 0; k <= 5; k++) { const s = lerp(11.8, 21.0, k / 5); wingLine(B, side, chordPath(s, spF(s), spA(s)), line); }
    // gear-alignment (taxi camera) stripe: matte black chordwise band on the upper skin at the outboard edge of the main
    // gear, "aligned with the outboard edge of the main landing gear" [V aerospaceglobalnews / supercarblondie]; ~0.38 m
    // wide at s = 6.4 m, from ~1 m ahead of the flap TE 5.6 m forward (overhead 777-300ER agn_Boeing-777-wing-stripes-1,
    // band ~0.35 m in F-GSQR_1/_2) [D photo scale]. Lifted 18 mm, 6 mm clear of the spoiler seams it crosses [A]. ANA's
    // yellow ice-detection spot on the stripe (airlinercafe forum) is left out: size and position not found [open].
    wingLine(B, side, Array.from({ length: 9 }, (_, k) => [6.4, lerp(33.2, 38.8, k / 8)]),
      { c: '#15171a', r: 0.9, m: 0 }, 0.46, 1, 0.018);   // w1: 0.38 -> 0.46 m, half a spoiler panel in ANA 26K _7242 [D]
    // upper-skin panel seams: spanwise splice at ~45 % chord and chordwise butt joints ~2.4 m apart between the slat line and
    // the spoilers, faint (a shade under the paint) and 25 mm wide so they do not alias at 20-30 m [V seams visible in ANA 26K
    // _7250/_7331 and F-GSQR_1; A positions]
    const skin = { c: '#55575a', r: 0.7, m: 0.05 }, lef = (s) => pwl(WING.le, s), mid = (s) => lef(s) + 0.45 * (pwl(WING.te, s) - lef(s));
    wingLine(B, side, spanPath(4.0, 29.0, mid, 18), skin, 0.025);
    for (let s = 12.6; s < 29; s += 2.4) wingLine(B, side, chordPath(s, lef(s) + 0.7, s < 21 ? pwl(WING.te, s) - lerp(1.6, 1.2, (s - 11.8) / 9.2) : pwl(WING.te, s) - 0.7), skin, 0.025);
    // right-wing registration JA795A on the upper skin [V: ANA JA795A seat-26K photos alv_*_7250/_7331/_7345, new 212-seat
    // layout, NH211 2026]: dark block capitals ~1.25 m tall at ~50 % chord (a letter-high band of skin ahead of it, bottoms just ahead of the spoilers) from s 13.5 outboard, J inboard, glyph tops toward
    // the leading edge, so it reads upright left-to-right from the aft K seats (zoomed _7345; the raters' "upside down" was
    // perspective) [V photo], glyph size / spacing [D photo scale]
    if (side > 0) {
      const GL = {
        J: [[[0.7, 1], [0.7, 0.22], [0.55, 0.03], [0.15, 0.03], [0.02, 0.22]]],
        A: [[[0, 0], [0.35, 1], [0.7, 0]], [[0.15, 0.36], [0.55, 0.36]]],
        7: [[[0, 0.98], [0.7, 0.98], [0.28, 0]]],
        9: [[[0.7, 0.62], [0.5, 0.46], [0.18, 0.46], [0.02, 0.62], [0.02, 0.84], [0.18, 0.98], [0.52, 0.98], [0.68, 0.84], [0.68, 0.22], [0.5, 0.02], [0.08, 0.02]]],
        5: [[[0.68, 0.98], [0.06, 0.98], [0.02, 0.55], [0.48, 0.6], [0.68, 0.42], [0.68, 0.16], [0.5, 0.02], [0.02, 0.05]]],
      };
      const ink = { c: '#3a3e44', r: 0.85, m: 0 };   // w2: photo ink ~#4e555e under overcast, not black [V _7345]
      [...'JA795A'].forEach((ch, k) => {
        const sC = 13.5 + k * 1.15, xc = lef(sC + 0.45) + 0.50 * (pwl(WING.te, sC + 0.45) - lef(sC + 0.45));
        for (const st of GL[ch]) {
          const path = [];
          for (let q = 0; q < st.length - 1; q++) for (let t = 0; t < 1; t += 0.25) path.push([lerp(st[q][0], st[q + 1][0], t), lerp(st[q][1], st[q + 1][1], t)]);
          path.push(st[st.length - 1]);
          wingLine(B, 1, path.map(([u, v]) => [sC + u * 0.9, xc - (v - 0.5) * 1.4]), ink, 0.27, 1, 0.016);
        }
      });
    }
    // flaperon behind the engine (9.8-11.8) [A span], outboard flap to 23.3, aileron 23.3-29.3 [D ACAP]
    const te = (s) => pwl(WING.te, s);
    wingLine(B, side, spanPath(9.8, 11.8, (s) => te(s) - 1.15, 3), gap);
    for (const s of [9.8, 11.8]) wingLine(B, side, chordPath(s, te(s) - 1.15, te(s) + 0.02), gap, 0.03);
    wingLine(B, side, chordPath(23.3, te(23.3) - 0.62, te(23.3) + 0.02), gap, 0.03);
    wingLine(B, side, spanPath(23.3, 29.3, (s) => te(s) - lerp(0.62, 0.40, (s - 23.3) / 6), 8), gap);
    wingLine(B, side, chordPath(29.3, te(29.3) - 0.40, te(29.3) + 0.02), gap, 0.03);
    // flap-track fairings (canoes) under the trailing edge: ~60 % of each ahead of the TE [A from HL8007 photo]. 0.46 m wide
    // x 0.85 m deep; w1: in flaps-up cruise the tail tapers to a narrow rounded end ~40 % of the max depth (ANA 26K _7329/
    // _7331; the r2 blunt tail came from a ground photo with flaps extended) [V photo, D proportions]
    const vW = B.vcount, vC = B.vcount;
    for (const [cs, len] of WING.canoes) {
      const RE = 0.22, x1 = te(cs) + 0.4 * len - RE, x0 = x1 - len + RE, secs = [];
      const topAt = (xn) => (xn < te(cs) ? wingAt(cs, xn, side, -1)[1] + 0.03 : wingAt(cs, te(cs), side, -1)[1] + 0.03 - (xn - te(cs)) * 0.03);
      const sec = (xn, rw, rd) => {
        const d = 0.85 * rd + 0.04, w = 0.46 * rw + 0.03;
        return { y: xn + WING.dz, x: cs * side, z: -(topAt(xn) - d / 2), w, d, r: w * 0.48 };   // w2: rounded teardrop sections [V ANA 26K]
      };
      for (let k = 0; k <= 12; k++) {
        const t = k / 12, c = Math.cos(((t - 0.22) / 0.78) * Math.PI / 2);
        const rise = t < 0.22 ? Math.sin((t / 0.22) * Math.PI / 2) : 0;
        secs.push(sec(lerp(x0, x1, t), t < 0.22 ? rise : lerp(0.35, 1, Math.pow(c, 0.6)), t < 0.22 ? rise : lerp(0.25, 1, Math.pow(c, 0.8))));
      }
      // rounded end: quarter-ellipse over RE, closed by the loft cap
      for (const u of [0.35, 0.62, 0.84, 0.97]) { const e = Math.sqrt(1 - u * u); secs.push(sec(x1 + u * RE, 0.35 * e, 0.25 * e)); }
      B.add(gLoft(secs, 3), M4.trs(0, 0, 0, 0, Math.PI / 2), paint);
    }
    // GE90-115B nacelle
    const vN = B.vcount;
    const nac = nacelleGeo();
    const rot = M4.trs(E.s * side, E.y, E.x0 + WING.dz, 0, Math.PI / 2);
    B.add(nac.lip, rot, metal); B.add(nac.cowl, rot, cowl); B.add(nac.nozIn, rot, dark); B.add(nac.inlet, rot, { c: '#3a3e44', r: 0.6 });
    B.add(nac.core, rot, core); B.add(nac.coreIn, rot, dark); B.add(nac.plug, rot, plug); B.add(nac.spinner, rot, spin);
    for (const [x, r] of [[1.3, 2.075], [3.15, 2.055]]) B.add(gCyl(r + 0.004, r + 0.004, 0.025, 48, false), M4.mul(rot, M4.trs(0, x, 0)), seam);   // cowl splits [A photo]
    // inboard nacelle strake (vortex chine): 1.3 x 0.26 m plate standing radially out of the fan cowl 25 deg above the
    // horizontal on the inboard side, centred 2.45 m aft of the highlight, inside the middle cowl panel (w2, B-KQZ_074140) [V shape: ANA 11A _136/_137, B-KQZ_074140; D size].
    // Lathe space: +y = aft, +x = world x, +z = world down, so inboard = -side on x
    const ca = Math.cos(25 * DEG), sa = Math.sin(25 * DEG);
    const stM = M4.mul(rot, M4.trs(-side * ca * 2.18, 2.45, -sa * 2.18, side < 0 ? 25 * DEG : 155 * DEG));
    B.add(gRBox(0.26, 1.3, 0.06, 0.02, 1), stM, { c: '#9aa0a8', r: 0.4, m: 0.3 });   // w2: 6 cm, grey so it reads edge-on [A]
    B.add(gBox(0.04, 1.34, 0.09), M4.mul(stM, M4.trs(-0.12, 0, 0)), dark);            // dark root seam
    // round access panel on the upper cowl, 2.6 m aft, 15 deg outboard of top dead centre [V B-KQZ_074140 / EVA p97zMaCMWRg; A size]
    { const d = [side * Math.sin(15 * DEG), 0, -Math.cos(15 * DEG)], R = 2.087, e2 = [d[2], 0, -d[0]], ring = [];
      for (let k = 0; k <= 24; k++) { const a = (k / 24) * Math.PI * 2, u = Math.cos(a) * 0.26, w = Math.sin(a) * 0.26; ring.push([d[0] * R + e2[0] * w, 2.6 + u, d[2] * R + e2[2] * w]); }
      B.add(gTube(ring, 0.018, 4, false), rot, { c: '#8e949b', r: 0.5 }); }
    B.add(gCyl(1.64, 1.64, 0.02, 40), M4.mul(rot, M4.trs(0, 1.62, 0)), dark);    // fan-case back face behind the blades
    B.add(fanBlades(22), rot, blade);
    const sw = [];   // white swirl on the spinner [V photo JA796A]
    for (let k = 0; k <= 16; k++) { const t = k / 16, x = lerp(0.47, 1.4, t), r = pwl([[0.42, 0], [0.46, 0.1], [0.56, 0.22], [0.72, 0.34], [0.94, 0.44], [1.2, 0.51], [1.45, 0.53]], x) + 0.006, a = t * Math.PI * 1.6; sw.push([Math.cos(a) * r, x, Math.sin(a) * r]); }
    B.add(gTube(sw, 0.02, 5), rot, white);
    const vP = B.vcount;
    // pylon: fairing over the fan cowl rising as a swept ridge (0.10 -> 0.45 m above the cowl) into the wing LE, strut
    // under the wing with the aft fairing ending near the flap hinge [A; ridge seen in the p97zMaCMWRg GE90 view, painted
    // wing grey like the strut in the JA797A EGLL crop, V colour]
    const leE = pwl(WING.le, E.s), nacTop = (x) => E.y + pwl([[0, 1.715], [0.6, 2.02], [1.7, 2.09], [2.4, 2.09], [3.8, 1.99], [5.0, 1.5], [5.6, 1.02], [6.35, 0.84]], x);
    const secs = [];
    for (let k = 0; k <= 20; k++) {
      const x = lerp(1.4, 10.6, k / 20), xn = E.x0 + x;
      const wl = wingAt(E.s, Math.max(xn, leE), side, -1)[1];
      const bot = x < 6.35 ? nacTop(x) - 0.30 : lerp(nacTop(6.35), wl - 0.05, (x - 6.35) / 4.25);
      const ridge = nacTop(x) + lerp(0.0, 0.60, Math.pow(smooth(1.4, leE - E.x0, x), 0.9));
      const top = xn >= leE ? wl + 0.12 : lerp(ridge, Math.max(wl + 0.12, ridge), smooth(leE - E.x0 - 2.0, leE - E.x0, x));
      // w1: broad, low forward fairing hump (~0.9 m wide where it leaves the cowl, base sunk 0.3 m so the flanks meet the
      // curved cowl at a shallow angle) rising to ~0.6 m over the aft cowl into a saddle under the LE, not a rail
      // [V ANA 11A _137; D width from B-KQZ_074140 at 187 px/m], nose blended over 0.6 m
      const w = (x < 6.35 ? lerp(1.2, 1.0, smooth(2.0, 6.35, x)) : lerp(0.85, 0.40, (x - 6.35) / 4.25)) * lerp(0.05, 1, smooth(1.4, 3.2, x));
      secs.push({ y: xn + WING.dz, x: E.s * side, z: -(top + bot) / 2, w, d: top - bot, r: Math.min(w * 0.48, (top - bot) * 0.45) });
    }
    // fairing over the cowl in cowl white, strut under the wing in wing grey [V ANA 11A _137 / JA797A EGLL]
    const kLE = secs.findIndex((q) => q.y - WING.dz >= leE);
    B.add(gLoft(secs.slice(0, kLE + 1), 8, [true, false]), M4.trs(0, 0, 0, 0, Math.PI / 2), cowl);
    const vS = B.vcount;
    B.add(gLoft(secs.slice(kLE), 4, [false, true]), M4.trs(0, 0, 0, 0, Math.PI / 2), paint);
    // pylon flanks: the exterior pass has no bounce light, so the side away from the sun rendered sky-blue (#46536a) where
    // photos show it light grey like the wing (JA797A EGLL crop) [V]; bake the fill from the sunlit cowl + cloud deck
    // as x1.6 albedo on the flanks [A]
    for (let k = vS; k < B.vcount; k++) {   // strut only; w2: the white fairing was lifted above the cowl
      const f = 1 + 0.6 * smooth(0.3, 0.9, Math.abs(B.n[k * 3])) * (B.n[k * 3 + 1] > -0.3 ? 1 : 0);
      for (let c = 0; c < 3; c++) B.c[k * 4 + c] = Math.min(255, Math.round(B.c[k * 4 + c] * f));
    }
    // baked occlusion (the exterior pass has no shadow map): canoe and pylon undersides -25 %, nacelle lower half
    // down to x0.7, lower wing skin in the canoe / pylon footprint -25 % [A; shading seen in Boeing_777_(4139974954)_(2)
    // and the p97zMaCMWRg GE90 wing view, nacelle half in shadow]
    // canoes: flanks filled like the pylon (lit flank #d3d6d3 vs wing #c0ccd4, belly #59636c in ANA 26K _7331) [V], belly -35 %
    for (let k = vC; k < vN; k++) {
      const f = 1 + 0.1 * smooth(0.2, 0.9, Math.abs(B.n[k * 3])) * (B.n[k * 3 + 1] > -0.4 ? 1 : 0);
      for (let c = 0; c < 3; c++) B.c[k * 4 + c] = Math.min(255, Math.round(B.c[k * 4 + c] * f));
    }
    shadeVerts(B, vC, vN, (p, n) => 1 - 0.35 * Math.max(0, -n[1]));
    // w2: visible flank falls ~0.6 from top to lower cowl (#8d96a6 -> #556171 in ANA 11A _136) [V]: f = 0.62 + 0.38 * ((n.y+1)/2)^1.3
    shadeVerts(B, vN, vP, (p, n) => 0.62 + 0.38 * Math.pow((n[1] + 1) / 2, 1.3));
    shadeVerts(B, vP, B.vcount, (p, n) => 1 - 0.25 * Math.max(0, -n[1]));
    const foot = [...WING.canoes.map(([cs]) => cs), E.s];
    shadeVerts(B, v0, vW, (p, n) => {
      if (n[1] > -0.3) return 1;
      const d = Math.min(...foot.map((cs) => Math.abs(Math.abs(p[0]) - cs)));
      return 1 - 0.25 * (1 - smooth(0.3, 0.9, d));
    });
    // nav (red L / green R) + white strobe at the raked tip [A positions]
    const tip = stations[stations.length - 1];
    B.add(gSphere(0.07, 10, 6), M4.trs(tip.s * side, tip.y0 + 0.02, tip.le + 0.12 + WING.dz, 0, 0, 0, 1, 0.7, 2.2), { c: side < 0 ? '#c83a36' : '#3ab86a', r: 0.15, e: 2.5 });
    // w1: brighter point source (a star point with glow at dusk in ANA 26K _7282) [V]
    lights.push({ p: [tip.s * side, tip.y0 + 0.05, tip.le + 0.1 + WING.dz], c: side < 0 ? [2.5, 0.12, 0.08] : [0.1, 2.2, 0.35], s: 1.6, blink: 0 });
    // static dischargers on the aileron and raked-tip trailing edges (~8 per side in ANA 26K _7282) [V count, A positions]
    for (const s of [24.0, 25.5, 27.0, 28.5, 30.2, 31.2, 31.8, 32.3]) {
      const p = wingAt(s, pwl(WING.te, s) - 0.02, side);
      B.add(gCyl(0.008, 0.008, 0.28, 4), M4.trs(p[0], p[1] - 0.01, p[2] + 0.14, 0, Math.PI / 2), { c: '#2a2d31', r: 0.6 });
    }
    lights.push({ p: [tip.s * side, tip.y0 + 0.06, tip.le + tip.c * 0.8 + WING.dz], c: [4, 4, 4], s: 2.2, blink: side < 0 ? 2.0 : 2.5 });
  }
  // wing-to-body fairing below the cabin (nose stations ~26 -> 43.3, belly 2.35 m above ground) [D ACAP side view]
  B.add(gRBox(6.3, 1.9, 17.3, 0.8, 3), M4.trs(0, -1.78, 34.65 + WING.dz), paintLow);
  const geo = B.build();
  return { mesh: gl ? gl.mesh(geo, { name: 'exterior', layer: 'exterior', castShadow: false }) : null, lights, geo };
}
