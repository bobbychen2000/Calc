// Airfield lighting: runway edge/centerline/threshold/TDZ, PAPI, approach light systems (with sequenced flashers), taxiway edge
import { APPROACH_LIGHTS, APPROACH_STRUCTURES, PAPI, TDZ_LIGHTS, GROUND_Y, stToWorld } from '../geo.js';
import { RWY, RWY_W, TAXIWAYS } from '../world/airfield.js';
import { runwayFrame } from './traffic.js';
import { v3, m4 } from '../math.js';
import { Geo } from '../geom.js';
import { END_ZONES, EMAS_SETBACK } from '../live/airport.js';

const Y = GROUND_Y + 0.35;
const WHITE = [1, 0.93, 0.8], YELLOW = [1, 0.75, 0.25], RED = [1, 0.08, 0.04], GREEN = [0.2, 1, 0.45], BLUE = [0.2, 0.35, 1];

export function buildAirfieldLights(level = 1, opts = {}) {
  const L = []; // static sprites {p, c, i, s, dir, k}
  const flashers = []; // {p, order, period, dir}
  const papis = [];
  const piers = []; // approach light piers for geometry
  for (const r of RWY) {
    for (const [endIdx, name] of [[0, r.name[0]], [1, r.name[1]]]) {
      const F = runwayFrame(name);
      const len = F.length;
      if (endIdx === 1) continue; // edge lights added once per runway
      // edge lights both sides every 61 m
      for (let x = 0; x <= len + 1; x += 60.96) for (const sg of [-1, 1]) {
        const p = v3.add(v3.add(F.start, v3.mul(F.dir, x)), v3.mul(F.right, sg * (RWY_W / 2 + 1.0))); p[1] = Y;
        L.push({ p, c: WHITE, i: 30 * level, s: 0.25 });
      }
      // centerline lights every 15 m
      for (let x = 15; x < len - 5; x += 15.24) {
        const p = v3.add(F.start, v3.mul(F.dir, x)); p[1] = GROUND_Y + 0.08;
        const fromEnd = len - x; const c = (fromEnd < 300 || x < 300) ? ((fromEnd < 300 || x < 300) && Math.floor(x / 15.24) % 2 ? RED : WHITE) : WHITE;
        L.push({ p, c, i: 18 * level, s: 0.18, dir: v3.mul(F.dir, -1), k: 1.5 });
        L.push({ p, c: WHITE, i: 18 * level, s: 0.18, dir: F.dir, k: 1.5 });
      }
    }
    // thresholds/end lights & TDZ for both ends
    for (const name of r.name) {
      const F = runwayFrame(name);
      for (let k = -9; k <= 9; k++) {
        const p = v3.add(F.thr, v3.mul(F.right, k * 3.2)); p[1] = GROUND_Y + 0.25;
        L.push({ p, c: GREEN, i: 45 * level, s: 0.25, dir: v3.mul(F.dir, -1), k: 1.2 });
        const pe = v3.add(F.start, v3.mul(F.right, k * 3.2)); pe[1] = GROUND_Y + 0.25;
        L.push({ p: pe, c: RED, i: 35 * level, s: 0.25, dir: F.dir, k: 1.2 });
      }
      if (TDZ_LIGHTS.includes(name)) {   // NASR: TDZ lights only at 28R and 19L
        for (let x = 30; x < 900; x += 30.48) for (const sg of [-1, 1]) for (let j = 0; j < 3; j++) {
          const p = v3.add(v3.add(F.thr, v3.mul(F.dir, x)), v3.mul(F.right, sg * (11 + j * 1.5))); p[1] = GROUND_Y + 0.08;
          L.push({ p, c: WHITE, i: 14 * level, s: 0.16, dir: v3.mul(F.dir, -1), k: 2.5 });
        }
      }
      const PP = PAPI.find(q => q.end === name);
      if (PP) {
        // 4-box PAPI left of the runway at the glide-path intercept (geo.js PAPI.dist, from NASR TCH and angle); boxes
        // ~15 m from the edge, 9 m apart; unit settings angle +30', +10', -10', -30' from the runway side outwards
        const left = v3.mul(F.right, -1); const a = PP.angle;
        for (let j = 0; j < 4; j++) {
          const p = v3.add(v3.add(F.thr, v3.mul(F.dir, PP.dist)), v3.mul(left, RWY_W / 2 + 15 + j * 9)); p[1] = GROUND_Y + 1.0;
          papis.push({ p, dir: v3.mul(F.dir, -1), angle: [a + 0.5, a + 1 / 6, a - 1 / 6, a - 0.5][j] });
        }
      }
    }
  }
  // approach light systems (over water for 28s)
  for (const A of APPROACH_LIGHTS) {
    const F = runwayFrame(A.end); const back = v3.mul(F.dir, -1);
    // world point `dft` ft out from the threshold, `lat` m right of the OUTWARD axis (= left of the landing direction)
    const at = (dft, lat = 0) => v3.add(v3.add(F.thr, v3.mul(back, dft * 0.3048)), v3.mul(F.right, -lat));
    // Structures measured on NAIP 2024 where they exist (js/geo.js APPROACH_STRUCTURES, review round 3): a light station
    // over the water sits on the nearest imaged station; the crossbar lights stay on the imaged crossbar.
    const ST = APPROACH_STRUCTURES[A.end] || null;
    const snap = (dft) => { if (!ST || dft <= ST.seawallFt) return dft; let b = dft, e = 51; for (const s of ST.stationsFt) if (Math.abs(s - dft) < e) { e = Math.abs(s - dft); b = s; } return b; };
    const barAt = (dft) => ST ? ST.crossbars.find(c => Math.abs(c.ft - dft) < 30) : null;
    // FAA standard layouts (AIM Fig. 2-1-1): ALSF-2 bars every 100 ft to 2400 ft, red side rows in the inner 1000 ft,
    // 1000-ft crossbar, sequenced flashers from 1000 ft out; MALS(R/F) bars every 200 ft to 1400 ft with the 1000-ft
    // crossbar; MALSF flashers on the three outer bars (1000-1400 ft); MALSR RAIL = flashers only, 1600-2400 ft.
    const step = (A.type === 'ALSF2' ? 100 : 200), n = Math.floor(A.len / (step * 0.3048) + 1e-6);
    // lights approx level with threshold. opts.lightPlane {end: world y} (environment step 2, js/live/app.js): the imaged
    // over-water structures are built 0.1 m below the ALS light plane (threshold elevation, JO 6850.2C 201a), so the
    // fixture lights of data/sfo_lighting.js (js/env/lighting/airfield.js, placed by alsPlacement below) sit on them
    const hLight = opts.lightPlane && opts.lightPlane[A.end] != null ? opts.lightPlane[A.end] - 0.6 : GROUND_Y + 0.8;
    // paved ground beyond the threshold: the displaced runway (F.disp) plus the blast pad / EMAS bed of that end
    // (js/live/airport.js END_ZONES, NAIP-measured). Lights there are semi-flush inset lights (no post, at the surface);
    // review round 3: they had floated 1.4 m above the pavement.
    const ri = RWY.findIndex(r => r.name.includes(A.end));
    const ez = ri >= 0 ? END_ZONES.find(z => z.rw === ri && z.end === (RWY[ri].name[0] === A.end ? 0 : 1)) : null;
    const pavedM = (F.disp || 0) + (ez ? (ez.type === 2 ? EMAS_SETBACK + ez.len : ez.len) : 0);
    for (let i = 1; i <= n; i++) {
      const dNom = i * step; const dft = snap(dNom); const base = at(dft); const d = dft * 0.3048;
      const steady = A.type === 'ALSF2' || dNom <= 1400.5;
      // on land (between the threshold and the seawall of an imaged structure, or everywhere without one) every light
      // stands on its own post (review round 3: the land stations of 28L / 28R had lost their posts and floated)
      const inset = d <= pavedM + 1.0;                       // on the displaced runway / blast pad / EMAS: inset lights
      const onLand = !inset && (!ST || dft <= ST.seawallFt);
      // on an EMAS bed the surface rises from 0.25 m (entry) to 0.6 m (far end), world.js buildEMAS
      const uE = ez && ez.type === 2 ? d - (F.disp || 0) - EMAS_SETBACK : -1;
      const yL = !inset ? hLight + 0.6 : GROUND_Y + 0.12 + (uE >= 0 && uE <= ez.len ? 0.25 + 0.35 * uE / ez.len : 0);
      if (steady) {
        for (let j = -2; j <= 2; j++) { const p = v3.add(base, v3.mul(F.right, j * 1.05)); p[1] = yL; L.push({ p, c: WHITE, i: 60 * level, s: 0.3, dir: back, k: 3 }); }
        if (onLand) piers.push({ kind: 'post', base, right: F.right, water: false, h: hLight, bar: 2.6 });
      }
      if (A.type === 'ALSF2' && dNom < 1000) for (const sg of [-1, 1]) {
        for (let j = 0; j < 3; j++) { const p = v3.add(base, v3.mul(F.right, sg * (11 + j * 1.5))); p[1] = yL; L.push({ p, c: RED, i: 40 * level, s: 0.28, dir: back, k: 3 }); }
        // red side-row barrette (11-14 m out): over the water it sits on the imaged crossbar (28R 692-892 ft: +-16..20 m),
        // on land on its own post
        if (onLand) piers.push({ kind: 'post', base: v3.add(base, v3.mul(F.right, sg * 12.5)), right: F.right, water: false, h: hLight, bar: 1.8 });
      }
      if (Math.abs(dNom - 1000) < 1) {
        // 1000-ft crossbar: lights every 1.5 m from 4.5 m out to the FAA 50 ft (15.24 m) half-length, never beyond the
        // imaged bar (28L: 12.7 / 12.9 m); the imaged 28R bars are wider (+-16.5..19.7 m) and carry the standard 15 m
        const cb = barAt(dft);
        for (const sg of [-1, 1]) {
          const lim = Math.min(15.24, cb ? (sg > 0 ? -cb.l : cb.r) - 0.3 : 15.24);   // F.right side sg>0 = LEFT of the outward axis
          for (let j = 3; j * 1.5 <= lim + 1e-6; j++) { const p = v3.add(base, v3.mul(F.right, sg * j * 1.5)); p[1] = yL; L.push({ p, c: WHITE, i: 60 * level, s: 0.3, dir: back, k: 3 }); }
          if (onLand) piers.push({ kind: 'crossbar', base, right: F.right, lo: sg > 0 ? 4.0 : -lim - 0.2, hi: sg > 0 ? lim + 0.2 : -4.0, water: false, h: hLight, src: 'inferred' });
        }
      }
      const flash = A.type === 'ALSF2' ? dNom >= 999 : A.type === 'MALSR' ? dNom >= 1599 : dNom >= 999;
      if (flash) { const p = v3.add(base, [0, 1.6, 0]); p[1] = inset ? yL + 0.03 : hLight + 1.6; flashers.push({ p, order: -d, dir: back, end: A.end }); }
      if (flash && onLand && !steady) piers.push({ kind: 'post', base, right: F.right, water: false, h: hLight });   // RAIL flasher on land
    }
    if (ST) {
      // observed structure: one continuous catwalk from the seawall to the last station, a pier at every imaged
      // station, the imaged crossbars and huts (buildPierGeometry)
      const last = ST.stationsFt[ST.stationsFt.length - 1];
      piers.push({ kind: 'catwalk', a: at(ST.seawallFt, ST.catwalkLat), b: at(last + 3, ST.catwalkLat), right: F.right, water: true, h: hLight, src: 'naip' });
      for (const ft of ST.stationsFt) piers.push({ kind: 'station', base: at(ft), right: F.right, cw: -ST.catwalkLat, water: true, h: hLight, src: 'naip' });
      for (const c of ST.crossbars) piers.push({ kind: 'crossbar', base: at(c.ft), right: F.right, lo: -c.r, hi: -c.l, water: true, h: hLight, src: c.inferred ? 'inferred' : 'naip' });
      for (const u of ST.huts) piers.push({ kind: u.platform ? 'platform' : 'hut', base: at((u.ft0 + u.ft1) / 2), right: F.right, lo: -u.r, hi: -u.l, len: (u.ft1 - u.ft0) * 0.3048, water: true, h: hLight, src: 'naip' });
    }
  }
  // taxiway edge lights (blue), sparse
  if (opts.taxiways !== false) for (const tw of TAXIWAYS) {
    for (let i = 0; i < tw.pts.length - 1; i++) {
      const a = tw.pts[i], b = tw.pts[i + 1]; const Ls = Math.hypot(b[0] - a[0], b[1] - a[1]); const d = [(b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls]; const nrm = [-d[1], d[0]];
      for (let x = 0; x < Ls; x += 45) for (const sg of [-1, 1]) {
        const s = a[0] + d[0] * x + nrm[0] * sg * 13.5, t = a[1] + d[1] * x + nrm[1] * sg * 13.5;
        if (RWY.some(r => { const u = r.axis === 0 ? s : t, v = r.axis === 0 ? t : s; return u > r.a0 - 20 && u < r.a1 + 20 && Math.abs(v - r.c) < 45; })) continue;
        L.push({ p: stToWorld(s, t, GROUND_Y + 0.4), c: BLUE, i: 10 * level, s: 0.2 });
      }
    }
  }
  // group flashers per system
  const sys = {}; flashers.forEach(f => { const key = f.dir.map(v => v.toFixed(2)).join(',') + Math.round(f.p[0] / 400); });
  return { L, flashers, papis, piers };
}

// ALS light placement on the approach-light structures (environment step 2, docs/research/environment_impl.md §2):
// returns place(stationFt, latM) -> {p: [x, y, z], kind: 'inset' | 'pier' | 'land' | 'water'} for a fixture `stationFt`
// ft out from the landing threshold (FAA nominal station, data/sfo_lighting.js) and `latM` m right of the OUTWARD axis.
// Same frame, station snapping and pavement test as the builder above, so the lights stand on the geometry it makes:
// over the water the station moves to the nearest NAIP-imaged station within 51 ft (js/geo.js APPROACH_STRUCTURES, obs)
// at the light plane `planeY` (threshold elevation, JO 6850.2C 201a); on the displaced runway / blast pad / EMAS the
// light is a semi-flush inset light at the surface (EMAS: its rising top); over the bay without an imaged structure
// ('water': 19L, whose pier is not in APPROACH_STRUCTURES) at the light plane on piles (buildMountGeometry); elsewhere on
// land on a low frangible mount at max(planeY, GROUND_Y + 0.35 m) (I: the app's terrain is flat at field level, above
// the 12.6-12.9 ft light plane of 28L/28R and 2.6 ft above that of 19L). isWater(x, z): optional land/water test.
export function alsPlacement(end, planeY) {
  const A = APPROACH_LIGHTS.find(a => a.end === end); if (!A) return null;
  const F = runwayFrame(end); const back = v3.mul(F.dir, -1);
  const ST = APPROACH_STRUCTURES[end] || null;
  const ri = RWY.findIndex(r => r.name.includes(end));
  const ez = ri >= 0 ? END_ZONES.find(z => z.rw === ri && z.end === (RWY[ri].name[0] === end ? 0 : 1)) : null;
  const pavedM = (F.disp || 0) + (ez ? (ez.type === 2 ? EMAS_SETBACK + ez.len : ez.len) : 0);
  const yMount = Math.max(planeY, GROUND_Y + 0.35);
  return (stationFt, latM, isWater) => {
    let dft = stationFt;
    if (ST && dft > ST.seawallFt) { let e = 51; for (const s of ST.stationsFt) if (Math.abs(s - stationFt) < e) { e = Math.abs(s - stationFt); dft = s; } }
    const d = dft * 0.3048;
    const p = v3.add(v3.add(F.thr, v3.mul(back, d)), v3.mul(F.right, -latM));
    let kind;
    if (d <= pavedM + 1.0) {
      const uE = ez && ez.type === 2 ? d - (F.disp || 0) - EMAS_SETBACK : -1;
      p[1] = GROUND_Y + 0.12 + (uE >= 0 && uE <= ez.len ? 0.25 + 0.35 * uE / ez.len : 0); kind = 'inset';
    } else if (ST && dft > ST.seawallFt && dft <= ST.stationsFt[ST.stationsFt.length - 1] + 1) { p[1] = planeY; kind = 'pier'; }
    else if (isWater && isWater(p[0], p[2])) { p[1] = planeY; kind = 'water'; }   // piles from the water (no imaged pier)
    else { p[1] = yMount; kind = 'land'; }
    return { p, kind, dft };
  };
}
// Low mounts under the land / unsupported ALS lights (environment step 2; replaces the builder's land 'post' piers when
// the fixture lights are used): one post per light group (station, side cluster) from the ground (land) or 2 m below
// the water surface (piles, 'water') up to 6 cm under the lights, and a bar carrying the group's lights.
// groups: [{x, z, yTop, lo, hi, right: [x, y, z], water}] (lo / hi: lateral extent along `right`, m); {box: true}:
// a PAPI lamp housing behind the light (local x = cross(right, up) = the beam direction).
export function buildMountGeometry(groups) {
  const g = new Geo(); const col = [0.35, 0.33, 0.3, 1], ext = [0.7, 0.4, 0, 0];
  for (const G of groups) {
    const f = v3.norm(v3.cross(G.right, [0, 1, 0]));
    const M = m4.basis(f, [0, 1, 0], [G.x, 0, G.z]);
    if (G.box) {   // PAPI lamp housing (L-880 LHA; size NV, I: 0.9 m along the beam x 0.6 m) behind the light, on two legs
      const yb = G.yTop + 0.12, ya = G.yTop - 0.25;
      g.box([-0.95, ya, -0.3], [-0.05, yb, 0.3], [0.55, 0.55, 0.5, 1], ext, M);
      for (const x of [-0.8, -0.2]) g.box([x - 0.05, GROUND_Y, -0.05], [x + 0.05, ya, 0.05], col, ext, M);
      continue;
    }
    const y0 = G.water ? -2.0 : GROUND_Y, top = G.yTop - 0.06;
    if (top <= y0 + 0.02) continue;
    const mid = (G.lo + G.hi) / 2;
    g.box([-0.07, y0, mid - 0.07], [0.07, top, mid + 0.07], col, ext, M);
    if (G.hi - G.lo > 0.3) g.box([-0.06, top - 0.1, G.lo - 0.15], [0.06, top, G.hi + 0.15], col, ext, M);
  }
  return g.data();
}

export function lightSpriteFn(sys) {
  return (t, camPos) => {
    const out = sys.L.slice();
    // sequenced flashers: each approach system runs its rabbit twice per second, farthest first
    const byDir = {};
    for (const f of sys.flashers) (byDir[f.end] = byDir[f.end] || []).push(f);
    for (const k in byDir) {
      const list = byDir[k].sort((a, b) => a.order - b.order);
      const n = list.length; const phase = (t * 2 + k.length * 0.13) % 1; const idx = Math.floor(phase * (n + 4));
      for (let i = 0; i < n; i++) if (i === idx) out.push({ p: list[i].p, c: [1, 1, 1], i: 900, s: 0.4, dir: list[i].dir, k: 2 });
    }
    // PAPI color by viewing elevation angle
    if (camPos) for (const P of sys.papis) {
      const d = v3.sub(camPos, P.p); const horiz = Math.hypot(d[0], d[2]); const ang = Math.atan2(d[1], horiz) * 180 / Math.PI;
      out.push({ p: P.p, c: ang > P.angle ? WHITE : RED, i: 120, s: 0.35, dir: P.dir, k: 4 });
    }
    return out;
  };
}

// approach light pier structures as boxes. Pier kinds (review round 3): 'post' = a single post under a light station
// on land (no imaged structure); 'catwalk' = the continuous deck a -> b; 'station' = piles under the light bar and the
// catwalk with a cross-member; 'crossbar' = the imaged crossbar from lo to hi (m along `right`) on piles; 'hut' = an
// equipment hut on the structure; 'platform' = a flat deck on the catwalk. Local frame: x along the runway axis, z = right (runway frame), y up.
export function buildPierGeometry(piers) {
  const g = new Geo(); const col = [0.35, 0.33, 0.3, 1], ext = [0.7, 0.4, 0, 0], deck = [0.3, 0.3, 0.3, 1], rail = [0.35, 0.35, 0.35, 1];
  for (const P of piers) {
    const top = P.h + 0.5; const f = v3.norm(v3.cross(P.right, [0, 1, 0]));
    if (P.kind === 'catwalk') {
      const d = v3.sub(P.b, P.a); const L = Math.hypot(d[0], d[2]); const u = v3.norm([d[0], 0, d[2]]);
      const M = m4.basis(u, [0, 1, 0], [P.a[0], 0, P.a[2]]);
      g.box([0, top - 0.9, -0.6], [L, top - 0.75, 0.6], deck, ext, M);
      for (const sg of [-1, 1]) g.box([0, top - 0.75, sg * 0.6 - 0.03], [L, top - 0.1, sg * 0.6 + 0.03], rail, ext, M);
      continue;
    }
    const M = m4.basis(f, [0, 1, 0], [P.base[0], 0, P.base[2]]); // local x along runway axis, z = right
    const y0 = P.water ? -2.0 : GROUND_Y;
    if (P.kind === 'station') {
      for (const z of [-0.9, 0.9, P.cw]) g.box([-0.18, y0, z - 0.18], [0.18, top - 0.25, z + 0.18], col, ext, M);
      g.box([-0.15, top - 0.25, -2.6], [0.15, top, 2.6], col, ext, M);                                   // light-bar beam
      g.box([-0.12, top - 0.95, Math.min(0, P.cw)], [0.12, top - 0.8, Math.max(0, P.cw)], col, ext, M);   // link to the catwalk
    } else if (P.kind === 'crossbar') {
      g.box([-0.2, top - 0.35, P.lo], [0.2, top - 0.05, P.hi], col, ext, M);
      for (let z = P.lo; z <= P.hi + 1e-6; z += Math.max(4, (P.hi - P.lo) / Math.ceil((P.hi - P.lo) / 6))) g.box([-0.16, y0, z - 0.16], [0.16, top - 0.35, z + 0.16], col, ext, M);
    } else if (P.kind === 'platform') {
      // a flat service platform on the catwalk (deck + railing), imaged as a light rectangle without a roof shadow
      g.box([-P.len / 2, top - 0.9, P.lo], [P.len / 2, top - 0.75, P.hi], deck, ext, M);
      for (const z of [P.lo, P.hi]) g.box([-P.len / 2, top - 0.75, z - 0.03], [P.len / 2, top - 0.1, z + 0.03], rail, ext, M);
      for (const x of [-P.len / 2 + 0.3, P.len / 2 - 0.3]) for (const z of [P.lo + 0.3, P.hi - 0.3]) g.box([x - 0.16, y0, z - 0.16], [x + 0.16, top - 0.9, z + 0.16], col, ext, M);
    } else if (P.kind === 'hut') {
      g.box([-P.len / 2, top - 0.9, P.lo], [P.len / 2, top + 1.9, P.hi], [0.55, 0.55, 0.52, 1], ext, M);
      for (const x of [-P.len / 2 + 0.3, P.len / 2 - 0.3]) for (const z of [P.lo + 0.3, P.hi - 0.3]) g.box([x - 0.16, y0, z - 0.16], [x + 0.16, top - 0.9, z + 0.16], col, ext, M);
    } else {
      // 'post' on land: a frangible post under the light bar (and the bar itself, `bar` m long, when given)
      g.box([-0.12, GROUND_Y, -0.12], [0.12, top, 0.12], col, ext, M);
      if (P.bar) g.box([-0.1, top - 0.2, -P.bar / 2], [0.1, top, P.bar / 2], col, ext, M);
    }
  }
  return g.data();
}
