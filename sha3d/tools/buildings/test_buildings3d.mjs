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
// fix round 1 (review L2): the T1 hall arch keeps its crest at the B3 height + the 1.3 m slab, eaves rise lower
for (const p of D.parts.filter(p => p.roof_form && p.roof_form.kind === 'arch')) {
  const g = new Geo(); buildPart(g, p); let top = -1e9, lo = 1e9; for (let i = 1; i < g.pos.length; i += 3) top = Math.max(top, g.pos[i]);
  for (let i = 1; i < g.pos.length; i += 3) if (g.nrm[i] > 0.5) lo = Math.min(lo, g.pos[i]);
  if (Math.abs(top - (p.h + 1.3)) > 0.05) bad(`${p.id}: arch crest ${top.toFixed(2)} vs h + 1.3 = ${(p.h + 1.3).toFixed(2)}`);
  if (Math.abs(lo - (p.h - p.roof_form.rise + 1.3)) > 0.3) bad(`${p.id}: lowest up-facing roof ${lo.toFixed(2)} vs eaves + slab ${(p.h - p.roof_form.rise + 1.3).toFixed(2)}`);
  console.log(`${p.id}: arch crest ${top.toFixed(2)} m, eaves roof ${lo.toFixed(2)} m (rise ${p.roof_form.rise}, src ${p.roof_form.src})`);
}
// fix round 1 (review L5): context palette - wall luminance 0.18-0.58 (no white blocks), roofs darker than walls
{ const { contextColours } = await import('../../js/world/buildings3d.js'); const lum = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; let n = 0, hi = 0, inv = 0;
  for (const b of A.context.buildings) { const C = contextColours(b.id, b.kind || 'building'); n++; if (lum(C.wall) > 0.58 || lum(C.wall) < 0.18) hi++; if (lum(C.roof) >= lum(C.wall)) inv++; }
  if (hi) bad(`context palette: ${hi} walls outside luminance 0.18-0.58`); if (inv) bad(`context palette: ${inv} roofs not darker than their walls`);
  console.log(`context palette: ${n} buildings, walls outside range ${hi}, roofs >= walls ${inv}`); }
// fix round 1 (review H2): airside fill exists, and every fixed link (attach -> rotunda) runs over the fill or an apron
{ const S = load('data/sha_stands.js', 'SHA_STANDS'); const F = D.airside_fill; const aprons = A.aprons.map(a => [a.ring, ...(a.holes || [])]);
  if (!F || !F.polys.length || F.src !== 'inf' || F.kind !== 'paved') bad('airside_fill missing or not tagged inf / paved');
  let pts = 0, off = 0;
  for (const s of S.stands) for (const br of s.bridges || []) { const [a, r] = [br.walk[0], br.walk[br.walk.length - 1]];
    if (Math.hypot(r[0] - a[0], r[1] - a[1]) < 1) continue;   // no fixed link (T1 west: the rotunda is at the facade, on the apron edge)
    for (let k = 0; k <= 10; k++) { const x = a[0] + (r[0] - a[0]) * k / 10, z = a[1] + (r[1] - a[1]) * k / 10; pts++;
      // points on the facade line (k = 0) may fall just inside the building: test 1 m out along the link
      const L = Math.hypot(r[0] - a[0], r[1] - a[1]) || 1, xx = k ? x : x + (r[0] - a[0]) / L, zz = k ? z : z + (r[1] - a[1]) / L;
      if (!insidePolys(F.polys, xx, zz) && !insidePolys(F.apron_polys || [], xx, zz) && !insidePolys(aprons, xx, zz)) off++; } }
  if (off) bad(`airside fill: ${off} of ${pts} fixed-link points over neither the fill nor an apron`);
  // fix round 3 (N6): the part beyond the service band is tagged apron
  if (F && F.apron_polys && (F.apron_kind !== 'apron' || !F.apron_polys.length)) bad('airside_fill apron part missing or not tagged apron');
  console.log(`airside fill: ${F ? F.polys.length : 0} rings, ${F && F.polys.reduce((s, p) => s + p.length - 1, 0)} holes (service band ${F && F.service_w_m} m) + ${F && F.apron_polys ? F.apron_polys.length : 0} apron rings; fixed-link points off pavement ${off} / ${pts}`); }
// fix round 2 (review_visual_fix1.md R1): stand-head fill exists (tagged inf / apron), and every stop node (= nose-wheel stop,
// MH 5001-2021 6.2.16-7), class nose tip (class_ref nose_gear_m ahead) and envelope front (+ stand.noseE, table 4.13.5 note a)
// lies on pavement (OSM aprons / surfaces, the airside fill or the stand-head fill)
{ const S = load('data/sha_stands.js', 'SHA_STANDS'); const H = D.stand_head_fill; const { CAAC, val } = await import('../../js/live/caac_markings.js');
  if (!H || !H.polys.length || H.src !== 'inf' || H.kind !== 'apron') bad('stand_head_fill missing or not tagged inf / apron');
  const SU = A.surfaces || {}; const pav = [...A.aprons.map(a => [a.ring, ...(a.holes || [])]),
    ...['runway', 'taxiway', 'taxiway_shoulders', 'runway_shoulders_blast_pads'].flatMap(k => (SU[k] || []).map(p => [p.ring, ...(p.holes || [])]))];
  const on = (x, z) => insidePolys(pav, x, z) || insidePolys(D.airside_fill.polys, x, z) || insidePolys(D.airside_fill.apron_polys || [], x, z) || (H && insidePolys(H.polys, x, z));
  const refs = S.class_ref || {}; const E = val(CAAC.stand.noseE); const off = { node: [], tip: [], front: [] };
  for (const s of S.stands) { const h = s.hdg * Math.PI / 180, f = [Math.sin(h), -Math.cos(h)]; const ng = (refs[s.cls] || refs.C || {}).nose_gear_m || 0;
    const at = (t) => [s.nose[0] + f[0] * t, s.nose[1] + f[1] * t];
    if (!on(...s.nose)) off.node.push(s.name); if (!on(...at(ng))) off.tip.push(s.name); if (!on(...at(ng + E))) off.front.push(s.name); }
  for (const k in off) if (off[k].length) bad(`stand heads: ${k} off pavement at ${off[k].join(', ')}`);
  console.log(`stand-head fill: ${H ? H.polys.length : 0} rings for ${H ? H.stands.length : 0} stands; off pavement: nodes ${off.node.length}, nose tips ${off.tip.length}, envelope fronts ${off.front.length} of ${S.stands.length}`); }
// every bridge attach point lies on a terminal part boundary (data check repeated from the generator)
console.log('checks in data', JSON.stringify(D.checks));
if (D.checks.bridge_attach_on_facade.max_dist_m > 0.5) bad('bridge attach points off the facade');
console.log(`parts ${D.parts.length}, hangars ${D.hangars.length}, towers ${D.towers.length}, triangles ${tris}`);
console.log(fail ? `FAILED (${fail})` : 'all checks passed');
process.exit(fail ? 1 : 0);
