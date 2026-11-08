// Full-length check of the lower-fuselage skin API (js/aircraft/fit.js T.fit.skinHW / keelAt, the belt-loader and GSE
// consumers' query) against the mesh the app draws: at every station X (0.5 m step) and keel + h (h = 0.05 .. 1.4 m) the
// starboard half width of a planar cut of the placed model (tools/models/dock_foot.mjs rendered(), zones 0 / 4 / 5,
// outermost crossing) vs T.fit.skinHW(X, keel + h). Close-out round 4 (verifier finding 3): the cargo-station rows of the
// round-3 belly check missed a regression away from the cargo doors (777 keel + 1 m 0.7 against 1.98 m, A330 wing box
// 4.4 against 2.2 m). Gear wells and wing boxes are outside the API's validity (the centre-plane keel finds the well roof /
// the fairing), so this is a report, not a pass / fail gate: compare the counts with the last recorded run
// (docs/requests/aircraft_closeout.md, close-out round 4, 46 types, 11,519 rows at keel + <= 0.3 m: > 0.15 m off 854,
// > 0.5 m 428 (round-3 hwLow: 1045 / 688); 737 family 77 / 24; A320 family 88 / 74 (round 3: 136 / 126); every height
// > 0.5 m 1587 (2237)). The cut ignores crossings wider than 1.3 R (the wing).
// Usage: node tools/models/skin_check.mjs [types,comma,separated]   (default: every type with a fitted model)
import path from 'path';
import { fileURLToPath } from 'url';
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const DF = await import(path.join(ROOT, 'tools/models/dock_foot.mjs'));
const { TYPES } = await import(path.join(ROOT, 'js/aircraft/types.js'));
const fit = await import(path.join(ROOT, 'js/aircraft/fit.js'));
const H = [0.05, 0.15, 0.3, 0.6, 1.0, 1.4];
const FAM = { '737': ['b736', 'b737', 'b738', 'b739', 'b37m', 'b38m', 'b39m', 'b3xm'], A320: ['a319', 'a19n', 'a320', 'a20n', 'a321', 'a21n'] };
function cut(G, xs) { const { W: P, D } = G; const segs = [];
  for (let t = 0; t < D.idx.length; t += 3) { const a = D.idx[t], b = D.idx[t + 1], c = D.idx[t + 2];
    if (![0, 4, 5].includes(D.zone[a]) || ![0, 4, 5].includes(D.zone[b]) || ![0, 4, 5].includes(D.zone[c])) continue;
    const pa = P[a * 3] - xs, pb = P[b * 3] - xs, pc = P[c * 3] - xs; if (Math.min(pa, pb, pc) >= 0 || Math.max(pa, pb, pc) <= 0) continue;
    const v = [a, b, c], s = [pa, pb, pc], pts = [];
    for (const [i, j] of [[0, 1], [1, 2], [2, 0]]) if ((s[i] < 0) !== (s[j] < 0)) { const u = s[i] / (s[i] - s[j]);
      pts.push([P[v[i] * 3 + 1] + u * (P[v[j] * 3 + 1] - P[v[i] * 3 + 1]), P[v[i] * 3 + 2] + u * (P[v[j] * 3 + 2] - P[v[i] * 3 + 2])]); }
    if (pts.length === 2) segs.push(pts); }
  return segs; }
const cross = (segs, val) => { const r = []; for (const [p, q] of segs) if ((p[0] - val) * (q[0] - val) <= 0 && p[0] !== q[0]) { const u = (val - p[0]) / (q[0] - p[0]); r.push(p[1] + u * (q[1] - p[1])); } return r; };
const types = process.argv[2] ? process.argv[2].split(',') : Object.keys(TYPES).filter(t => TYPES[t].key === t && fit.TYPE_MODEL[t] && TYPES[t].fit && TYPES[t].fit.skinHW);
const rows = {};
for (const t of types) {
  const T = TYPES[t], m = fit.TYPE_MODEL[t]; if (!m || !T.fit || !T.fit.skinHW) continue;
  const G = DF.rendered(t, m); const R = rows[t] = [];
  for (let X = 1; X < T.L - 1; X += 0.5) { const k = T.fit.keelAt(X); if (k == null) continue; const segs = cut(G, T.xMain - X);
    for (const h of H) { const zz = cross(segs, k + h).filter(z => z > 0 && z < 1.3 * T.R); if (!zz.length) continue;   // (wider: the wing)
      const mesh = Math.max(...zz), api = T.fit.skinHW(X, k + h); R.push({ X, h, mesh, api, e: api == null ? null : api - mesh }); } }
}
function summary(name, ts, hmax) {
  let n = 0, nul = 0, a15 = 0, a50 = 0, wide = 0; const E = [];
  for (const t of ts) for (const r of rows[t] || []) { if (r.h > hmax) continue; n++; if (r.e == null) { nul++; continue; } const a = Math.abs(r.e); E.push(a); if (a > 0.15) { a15++; if (r.e > 0) wide++; } if (a > 0.5) a50++; }
  E.sort((x, y) => x - y); const q = (p) => E.length ? E[Math.min(E.length - 1, Math.floor(p * E.length))].toFixed(3) : '-';
  console.log(`${name.padEnd(24)} rows ${String(n).padStart(5)}  null ${nul}  |err| median ${q(0.5)} p90 ${q(0.9)}  > 0.15 m: ${a15} (${wide} wide)  > 0.5 m: ${a50}`);
}
const all = Object.keys(rows);
summary('all types, keel + <= 0.3', all, 0.3); summary('all types, every height', all, 9);
summary('737 family, keel + <= 0.3', FAM['737'].filter(t => rows[t]), 0.3); summary('A320 family, keel + <= 0.3', FAM.A320.filter(t => rows[t]), 0.3);
for (const t of all) { const w = rows[t].filter(r => r.e != null).sort((a, b) => Math.abs(b.e) - Math.abs(a.e))[0];
  if (w) console.log(`  ${t.padEnd(5)} worst X ${w.X} keel + ${w.h}: api ${w.api} mesh ${w.mesh.toFixed(3)} (${w.e > 0 ? '+' : ''}${w.e.toFixed(3)})`); }
