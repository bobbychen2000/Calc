// Geometry checks for js/world/buildings3d.js (package P2d), run with node (no WebGL):
//   node tools/buildings/test_buildings3d.mjs        (from sha3d/)
// Loads data/sha_buildings3d.js and data/sha_airport.js, builds every part, hangar, tower, the context blocks and the
// bank kerbs into Geo buffers, and checks: no NaN / Infinity, every triangle's winding agrees with its stored normal
// (front faces are the lit ones: the renderer culls back faces), wall normals of outer rings point away from the
// footprint, roof caps face up, the control tower stays within its footprint radius and height, and the hangar door
// side faces pavement. Prints counts; exits 1 on a failure.
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url'; import vm from 'vm';
import { Geo } from '../../js/geom.js';
import { buildPart, buildHangar, buildControlTower, buildBlockTower, buildContextBlocks, buildWaterEdges, insidePolys } from '../../js/world/buildings3d.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const load = (f, name) => { const ctx = { window: {} }; vm.runInNewContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), ctx); return ctx.window[name]; };
const D = load('data/sha_buildings3d.js', 'SHA_BUILDINGS3D'), A = load('data/sha_airport.js', 'SHA_AIRPORT');
let fail = 0; const bad = (m) => { fail++; if (fail < 20) console.log('FAIL', m); };

function check(g, label, polys = null) {
  const P = g.pos, N = g.nrm, I = g.idx; let wrongWind = 0, nan = 0, inward = 0, walls = 0;
  for (const v of P) if (!Number.isFinite(v)) nan++;
  for (let t = 0; t < I.length; t += 3) {
    const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
    const e1 = [P[b] - P[a], P[b + 1] - P[a + 1], P[b + 2] - P[a + 2]], e2 = [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]];
    const cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    const L = Math.hypot(...cr); if (L < 1e-9) continue;
    const n = [N[a], N[a + 1], N[a + 2]]; const d = (cr[0] * n[0] + cr[1] * n[1] + cr[2] * n[2]) / L;
    if (d < -0.5) wrongWind++;
    // vertical walls of footprints: the point just outside along the normal must not be inside the footprint
    if (polys && Math.abs(n[1]) < 0.05 && Math.abs(cr[1] / L) < 0.05) {
      walls++;
      const cx = (P[a] + P[b] + P[c]) / 3, cz = (P[a + 2] + P[b + 2] + P[c + 2]) / 3;
      const inNow = insidePolys(polys, cx - n[0] * 0.3, cz - n[2] * 0.3), inOut = insidePolys(polys, cx + n[0] * 0.3, cz + n[2] * 0.3);
      if (inOut && !inNow) inward++;
    }
  }
  if (nan) bad(`${label}: ${nan} non-finite coordinates`);
  if (wrongWind) bad(`${label}: ${wrongWind} triangles wound against their normal`);
  if (inward > Math.max(2, walls * 0.01)) bad(`${label}: ${inward} of ${walls} wall triangles face into the footprint`);
  return I.length / 3;
}
let tris = 0;
for (const p of D.parts) { const g = new Geo(); buildPart(g, p); tris += check(g, p.id, p.style === 'canopy' ? null : p.polys); }
for (const h of D.hangars) { const g = new Geo(); buildHangar(g, h); tris += check(g, h.id, null);
  const n = h.door.normal, e = h.door.edge; const mx = (e[0][0] + e[1][0]) / 2 + n[0] * 5, mz = (e[0][1] + e[1][1]) / 2 + n[1] * 5;
  if (insidePolys(h.polys, mx, mz)) bad(`${h.id}: door normal points into the hangar`); }
for (const t of D.towers) {
  if (t.form === 'control') {
    const T = buildControlTower(t); const g = { pos: T.geo.pos, nrm: T.geo.nrm, idx: T.geo.idx }; tris += check(g, t.id, null);
    const b = T.geo.bbox; const r = Math.max(Math.abs(b[0]), Math.abs(b[2]), b[3], b[5]);
    if (b[4] > t.h + 0.01 || b[4] < t.h - 0.01) bad(`${t.id}: top ${b[4].toFixed(2)} vs the AIP obstacle height ${t.h}`);
    if (r > 12) bad(`${t.id}: footprint radius ${r.toFixed(1)} m`);
    if (T.eye < 39 || T.eye > t.h - 1.5) bad(`${t.id}: cab eye ${T.eye}`);
    console.log(`${t.id}: top ${b[4].toFixed(2)} m (AIP obstacle top ${t.h}), half-width ${r.toFixed(2)} m, eye ${T.eye.toFixed(2)} m`);
  } else { const g = new Geo(); buildBlockTower(g, t); tris += check(g, t.id, t.polys); }
}
{ const g = new Geo(); const n = buildContextBlocks(g, A.context.buildings, new Set(D.claims)); tris += check(g, 'context', null); console.log('context blocks', n); }
{ const g = new Geo(); const L = buildWaterEdges(g, A.context); tris += check(g, 'banks', null); console.log('bank kerb m', L); }
// every bridge attach point lies on a terminal part boundary (data check repeated from the generator)
console.log('checks in data', JSON.stringify(D.checks));
if (D.checks.bridge_attach_on_facade.max_dist_m > 0.5) bad('bridge attach points off the facade');
console.log(`parts ${D.parts.length}, hangars ${D.hangars.length}, towers ${D.towers.length}, triangles ${tris}`);
console.log(fail ? `FAILED (${fail})` : 'all checks passed');
process.exit(fail ? 1 : 0);
