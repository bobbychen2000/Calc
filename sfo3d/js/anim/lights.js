// Airfield lighting: runway edge/centerline/threshold/TDZ, PAPI, approach light systems (with sequenced flashers), taxiway edge
import { APPROACH_LIGHTS, GROUND_Y, stToWorld } from '../geo.js';
import { RWY, RWY_W, TAXIWAYS } from '../world/airfield.js';
import { runwayFrame } from './traffic.js';
import { v3, m4 } from '../math.js';
import { Geo } from '../geom.js';

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
      if (name.startsWith('28')) {
        for (let x = 30; x < 900; x += 30.48) for (const sg of [-1, 1]) for (let j = 0; j < 3; j++) {
          const p = v3.add(v3.add(F.thr, v3.mul(F.dir, x)), v3.mul(F.right, sg * (11 + j * 1.5))); p[1] = GROUND_Y + 0.08;
          L.push({ p, c: WHITE, i: 14 * level, s: 0.16, dir: v3.mul(F.dir, -1), k: 2.5 });
        }
        // PAPI on left side, ~ 350 m past threshold
        const left = v3.mul(F.right, -1);
        for (let j = 0; j < 4; j++) {
          const p = v3.add(v3.add(F.thr, v3.mul(F.dir, 360)), v3.mul(left, RWY_W / 2 + 15 + j * 9)); p[1] = GROUND_Y + 1.0;
          papis.push({ p, dir: v3.mul(F.dir, -1), angle: [3.5, 3.17, 2.83, 2.5][j] });
        }
      }
    }
  }
  // approach light systems (over water for 28s)
  for (const A of APPROACH_LIGHTS) {
    const F = runwayFrame(A.end); const back = v3.mul(F.dir, -1);
    const n = Math.floor(A.len / 30.48);
    for (let i = 1; i <= n; i++) {
      const d = i * 30.48; const base = v3.add(F.thr, v3.mul(back, d));
      const hLight = Math.max(GROUND_Y + 0.8, GROUND_Y + 0.8 - d * 0.0) ; // lights approx level with threshold
      for (let j = -2; j <= 2; j++) { const p = v3.add(base, v3.mul(F.right, j * 1.05)); p[1] = hLight + 0.6; L.push({ p, c: WHITE, i: 60 * level, s: 0.3, dir: back, k: 3 }); }
      if (A.type === 'ALSF2' && d < 300) for (const sg of [-1, 1]) for (let j = 0; j < 3; j++) { const p = v3.add(base, v3.mul(F.right, sg * (11 + j * 1.5))); p[1] = hLight + 0.6; L.push({ p, c: RED, i: 40 * level, s: 0.28, dir: back, k: 3 }); }
      if (Math.abs(d - 304.8) < 16) for (const sg of [-1, 1]) for (let j = 3; j <= 10; j++) { const p = v3.add(base, v3.mul(F.right, sg * j * 1.5)); p[1] = hLight + 0.6; L.push({ p, c: WHITE, i: 60 * level, s: 0.3, dir: back, k: 3 }); }
      if (d > 290 || A.type !== 'ALSF2') { const p = v3.add(base, [0, 1.6, 0]); p[1] = hLight + 1.6; flashers.push({ p, order: -d, dir: back, end: A.end }); }
      piers.push({ base, right: F.right, water: d > 150 && A.end.startsWith('28'), h: hLight });
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

// approach light pier structures (steel posts & crossbars) as instanced boxes
export function buildPierGeometry(piers) {
  const g = new Geo(); const col = [0.35, 0.33, 0.3, 1], ext = [0.7, 0.4, 0, 0];
  for (const P of piers) {
    const top = P.h + 0.5; const f = v3.norm(v3.cross(P.right, [0, 1, 0]));
    const M = m4.basis(f, [0, 1, 0], [P.base[0], 0, P.base[2]]); // local x along runway axis, z = right
    if (P.water) {
      for (const sg of [-1, 1]) g.box([-0.18, -2.0, sg * 1.6 - 0.18], [0.18, top, sg * 1.6 + 0.18], col, ext, M);
      g.box([-0.15, top - 0.25, -2.6], [0.15, top, 2.6], col, ext, M);
      g.box([-15.2, top - 0.9, -0.4], [15.2, top - 0.75, 0.4], [0.3, 0.3, 0.3, 1], ext, M);
      for (const sg of [-1, 1]) g.box([-15.2, top - 0.75, sg * 0.4 - 0.03], [15.2, top - 0.1, sg * 0.4 + 0.03], [0.35, 0.35, 0.35, 1], ext, M);
    } else {
      g.box([-0.12, GROUND_Y, -0.12], [0.12, top, 0.12], col, ext, M);
    }
  }
  return g.data();
}
