// Landing-gear retraction of the models with their own gear (js/live/models.js gearLegs / gearPivots), on what the app
// draws: every type whose fit uses a gear-carrying model, its stretch applied as in decodeModel (legs on the unstretched
// mesh, pivots on the stretched one). Kinematic checks with the shader formulas (js/three/aircraft.js realMaterial,
// js/shaders/aircraft_real.js ACR_VS), after the 13 Nov 2026 verifier findings:
//   nose   98 % of the folded tyre vertices above the belly skin (lowest non-gear skin surface at the vertex's cell)
//   mains  port and starboard rigid legs >= 0.05 apart at full fold; the lowest leg point never more than 0.10 below its
//          static level during the swing; no rigid leg vertex above the top skin (vertical ray-cast, +0.05) at 25-100 %
//   roles  zone integer kept (floor(x + 0.5)); every type gets the same role counts as its model's unstretched mesh
// usage: node tools/models/test_gear_rig.mjs   (exit 1 on failure)
import fs from 'fs'; import zlib from 'zlib';
import { gearLegs, gearPivots, skinMap } from '../../js/live/models.js';
import { applyStretch } from '../../js/aircraft/stretch.js';
import { TYPES } from '../../js/aircraft/types.js';
import { stretchFor } from '../../js/aircraft/fit.js';
let fail = 0; const ok = (c, m) => { if (!c) fail++; console.log(c ? 'ok  ' : 'FAIL', m); return c; };
const STEP = 0.05, raw = {};
function load(key) {
  if (raw[key]) return raw[key];
  let b = fs.readFileSync(`data/models/${key}.sfom`); if (b[0] === 0x1f && b[1] === 0x8b) b = zlib.gunzipSync(b);
  const ab = b.buffer.slice(b.byteOffset, b.byteOffset + b.length), dv = new DataView(ab);
  const hl = dv.getUint32(8, true), head = JSON.parse(new TextDecoder().decode(new Uint8Array(ab, 12, hl)));
  const B = 12 + hl, nv = head.nv, q = head.quant, o = head.offsets;
  const pq = new Uint16Array(ab, B + o.pos, nv * 3), zone = new Uint8Array(ab, B + o.zone, nv).slice(), pos = new Float32Array(nv * 3);
  for (let i = 0; i < nv * 3; i++) pos[i] = q.pmin[i % 3] + pq[i] * q.pscale[i % 3];
  const idx = head.idxType === 'u16' ? new Uint16Array(ab, B + o.idx, head.ni).slice() : new Uint32Array(ab, B + o.idx, head.ni).slice();
  return (raw[key] = { head, nv, zone, pos, idx });
}
const models = new Set(['b738', 'b772', 'b77w']);
const types = Object.keys(TYPES).filter(t => { const f = TYPES[t].fit; return f && models.has(f.model); });
ok(types.length >= 3, `types on gear-carrying models: ${types.join(' ')}`);
for (const t of types) {
  const key = TYPES[t].fit.model, R0 = load(key), nv = R0.nv, zone = R0.zone, pos = R0.pos.slice(), extra = new Float32Array(nv * 4);
  for (let i = 0; i < nv; i++) extra[i * 4] = zone[i];
  const legs = gearLegs(pos, zone, extra, nv); const dims = { ...R0.head.dims }; const st = stretchFor(t, key);
  if (st) applyStretch(pos, zone, nv, st, dims);
  const t0 = Date.now(); const G = legs && gearPivots(pos, zone, extra, nv, legs, R0.idx); const ms = Date.now() - t0;
  if (!ok(!!G, `${t} (${key}) rig ${G && G.map(v => v.toFixed(2)).join(', ')} (${ms} ms)`)) continue;
  const [xN, yN, yM, zM, aN, aM] = G;
  const code = i => Math.round((extra[i * 4] - zone[i]) / STEP); let bad = 0; const cnt = {};
  for (let i = 0; i < nv; i++) { if (zone[i] !== 3 && zone[i] !== 4) continue; if (Math.floor(extra[i * 4] + 0.5) !== zone[i]) bad++; const k = zone[i] + ':' + code(i); cnt[k] = (cnt[k] || 0) + 1; }
  ok(bad === 0, `${t} zone kept; roles ${JSON.stringify(cnt)}`);
  // nose
  const SK = skinMap(pos, zone, R0.idx);   // belly = lowest non-gear skin at the vertex's (x, z) cell (as the solver)
  let ny0 = 1e9, ny1 = -1e9; for (let i = 0; i < nv; i++) if (zone[i] === 3 && code(i) === 1 && legs.strut[i]) { ny0 = Math.min(ny0, pos[i * 3 + 1]); ny1 = Math.max(ny1, pos[i * 3 + 1]); }
  let nT = 0, nIn = 0; const c = Math.cos(aN), s = Math.sin(aN);
  for (let i = 0; i < nv; i++) { if (zone[i] !== 3 || code(i) !== 1 || pos[i * 3 + 1] > ny0 + 0.35 * (ny1 - ny0)) continue; nT++;
    const dx = pos[i * 3] - xN, dy = pos[i * 3 + 1] - yN, x = c * dx - s * dy + xN, y = s * dx + c * dy + yN, b = SK.bot(x, pos[i * 3 + 2]); if (b === undefined || y > b + 0.02) nIn++; }
  ok(nT > 0 && nIn / nT >= 0.98, `${t} nose folds ${(aN * 180 / Math.PI).toFixed(0)} deg: ${(100 * nIn / nT).toFixed(1)} % of ${nT} tyre vertices inside the belly`);
  // mains: rigid legs (codes 2 / 3)
  const rot = (i, u) => { const sg = code(i) === 3 ? 1 : -1, a = u * aM * sg, cc = Math.cos(a), ss = Math.sin(a), zp = zM * sg, dy = pos[i * 3 + 1] - yM, dz = pos[i * 3 + 2] - zp; return [cc * dy - ss * dz + yM, ss * dy + cc * dz + zp]; };
  let low0 = 1e9; for (let i = 0; i < nv; i++) if (zone[i] === 3 && (code(i) === 2 || code(i) === 3)) low0 = Math.min(low0, pos[i * 3 + 1]);
  let dip = 0; for (let u = 0.05; u <= 1.0001; u += 0.05) { let lo = 1e9; for (let i = 0; i < nv; i++) if (zone[i] === 3 && (code(i) === 2 || code(i) === 3)) lo = Math.min(lo, rot(i, u)[0]); dip = Math.max(dip, low0 - lo); }
  ok(dip <= 0.10, `${t} main gear: lowest point dips ${dip.toFixed(3)} below its static level during the swing (<= 0.10)`);
  let pMax = -1e9, sMin = 1e9; for (let i = 0; i < nv; i++) { if (zone[i] !== 3) continue; const cd = code(i); if (cd !== 2 && cd !== 3) continue; const z = rot(i, 1)[1]; if (cd === 2) pMax = Math.max(pMax, z); else sMin = Math.min(sMin, z); }
  ok(sMin - pMax >= 0.05, `${t} folded mains: port max z ${pMax.toFixed(2)}, starboard min z ${sMin.toFixed(2)} (gap ${(sMin - pMax).toFixed(2)} >= 0.05)`);
  // nothing rigid above the skin: vertical ray at the folded vertex's (x, z) against the zone-0 skin triangles; fail when the
  // vertex lies above the topmost hit (sticking out above the wing / body); 0.5-unit (x, z) grid of triangle boxes
  const T = R0.idx, grid = new Map(), C = 0.5;
  for (let t3 = 0; t3 < T.length; t3 += 3) {
    const a = T[t3], b2 = T[t3 + 1], c2 = T[t3 + 2]; const sk = v => zone[v] !== 3 && zone[v] !== 4 && zone[v] !== 8; if (!sk(a) || !sk(b2) || !sk(c2)) continue;
    const xs = [pos[a * 3], pos[b2 * 3], pos[c2 * 3]], zs = [pos[a * 3 + 2], pos[b2 * 3 + 2], pos[c2 * 3 + 2]];
    for (let gx = Math.floor(Math.min(...xs) / C); gx <= Math.floor(Math.max(...xs) / C); gx++) for (let gz = Math.floor(Math.min(...zs) / C); gz <= Math.floor(Math.max(...zs) / C); gz++) { const k = gx + ',' + gz; let L = grid.get(k); if (!L) grid.set(k, L = []); L.push(t3); }
  }
  const topHit = (x, z) => { const L = grid.get(Math.floor(x / C) + ',' + Math.floor(z / C)); if (!L) return null; let best = null;
    for (const t3 of L) { const P = [T[t3], T[t3 + 1], T[t3 + 2]].map(v => [pos[v * 3], pos[v * 3 + 1], pos[v * 3 + 2]]);
      const d = (P[1][2] - P[2][2]) * (P[0][0] - P[2][0]) + (P[2][0] - P[1][0]) * (P[0][2] - P[2][2]); if (Math.abs(d) < 1e-12) continue;
      const w0 = ((P[1][2] - P[2][2]) * (x - P[2][0]) + (P[2][0] - P[1][0]) * (z - P[2][2])) / d, w1 = ((P[2][2] - P[0][2]) * (x - P[2][0]) + (P[0][0] - P[2][0]) * (z - P[2][2])) / d, w2 = 1 - w0 - w1;
      if (w0 < -1e-6 || w1 < -1e-6 || w2 < -1e-6) continue; const y = w0 * P[0][1] + w1 * P[1][1] + w2 * P[2][1]; if (best === null || y > best) best = y; }
    return best; };
  let above = 0, worst = 0, W = null;
  for (const u of [0.25, 0.5, 0.75, 1]) for (let i = 0; i < nv; i++) { if (zone[i] !== 3) continue; const cd = code(i); if (cd !== 2 && cd !== 3) continue; const [y, z] = rot(i, u); const tp = topHit(pos[i * 3], z); if (tp !== null && y > tp + 0.05) { above++; if (y - tp > worst) { worst = y - tp; W = [u, pos[i * 3].toFixed(2), pos[i * 3 + 1].toFixed(2), pos[i * 3 + 2].toFixed(2), '->', y.toFixed(2), z.toFixed(2), 'top', tp.toFixed(2)]; } } }
  ok(above === 0, `${t} rigid main-leg vertices above the top skin (ray-cast) at 25-100 % travel: ${above} (worst ${worst.toFixed(2)}${W ? ' at ' + W.join(' ') : ''})`);
}
process.exit(fail ? 1 : 0);
