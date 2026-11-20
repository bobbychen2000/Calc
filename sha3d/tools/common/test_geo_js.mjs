// Twin test of js/geo.js (the app's world frame) against tools/common/frame.py and against data/sha_airport.json.
//   node tools/common/test_geo_js.mjs        (from sha3d/; needs python3 for the frame.py side)
// Checks: (1) frame constants vs the data's frame block; (2) a 41 x 41 grid over +-6 km, lat/lon -> world and back, JS vs
// Python to 1 mm (both directions) and the round trip to 1e-6 m; (3) every lat_lon + xz pair in sha_airport.json (runway
// ends / DTHRs, holds, tower, navaids) reproduced to the data's 0.01 m rounding; (4) heights (hae, pressure altitude).
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import * as G from '../../js/geo.js';
const here = path.dirname(fileURLToPath(import.meta.url)); const root = path.resolve(here, '../..');
const A = JSON.parse(readFileSync(path.join(root, 'data/sha_airport.json'), 'utf8'));
let fails = 0; const ok = (c, msg) => { if (!c) { fails++; console.log('FAIL', msg); } };
// (1)
const chk = G.checkFrame(A.frame); ok(chk.ok, 'frame block: ' + chk.diffs.join('; '));
// (2)
const pts = []; for (let i = -20; i <= 20; i++) for (let j = -20; j <= 20; j++) pts.push([G.ORIGIN.lat + j * 0.0027, G.ORIGIN.lon + i * 0.0031]);
const py = `import sys, json; sys.path.insert(0, ${JSON.stringify(here)}); import frame as F
P = json.loads(sys.stdin.read()); out = []
for lat, lon in P['ll']: out.append(F.ll_to_world(lat, lon))
inv = [F.world_to_ll(x, z) for x, z in P['xz']]
print(json.dumps({'w': out, 'inv': inv, 'hae': F.hae_from_y(2.5, 300.0, -800.0), 'pa': F.y_from_pressure_alt(3000, 1022.0)}))`;
const xz = pts.map((p, k) => [(k % 41 - 20) * 300.3, (Math.floor(k / 41) - 20) * 299.7]);
const R = JSON.parse(execFileSync('python3', ['-I', '-c', py], { input: JSON.stringify({ ll: pts, xz }) }).toString());
let dMax = 0, dInv = 0, dRt = 0;
pts.forEach((p, k) => { const w = G.wgs84ToWorld(p[0], p[1]); dMax = Math.max(dMax, Math.hypot(w[0] - R.w[k][0], w[1] - R.w[k][1]));
  const b = G.worldToWgs84(w[0], w[1]); dRt = Math.max(dRt, Math.hypot((b[0] - p[0]) * G.M_PER_DEG_LAT, (b[1] - p[1]) * G.M_PER_DEG_LON)); });
xz.forEach((q, k) => { const ll = G.worldToWgs84(q[0], q[1]); dInv = Math.max(dInv, Math.hypot((ll[0] - R.inv[k][0]) * G.M_PER_DEG_LAT, (ll[1] - R.inv[k][1]) * G.M_PER_DEG_LON)); });
ok(dMax < 1e-3, `ll->world JS vs frame.py max ${dMax} m`); ok(dInv < 1e-3, `world->ll JS vs frame.py max ${dInv} m`); ok(dRt < 1e-6, `round trip ${dRt} m`);
// (3)
const pairs = [];
for (const r of A.runways) for (const e of r.ends) for (const k of ['end', 'dthr']) if (e[k] && e[k].lat_lon) pairs.push([`${e.id}.${k}`, e[k].lat_lon, e[k].xz]);
for (const h of A.holds) if (h.lat_lon) pairs.push([h.id, h.lat_lon, [h.x, h.z]]);
if (A.control_tower && A.control_tower.lat_lon) pairs.push(['tower', A.control_tower.lat_lon, [A.control_tower.x, A.control_tower.z]]);
for (const n of A.navaids || []) if (n.lat_lon) pairs.push([n.id, n.lat_lon, [n.x, n.z]]);
let dData = 0, worst = null;
for (const [id, ll, q] of pairs) { const w = G.wgs84ToWorld(ll[0], ll[1]); const d = Math.hypot(w[0] - q[0], w[1] - q[1]); if (d > dData) { dData = d; worst = id; } }
// data xz are rounded to 0.01 m and lat_lon to 1e-7 / 1e-8 deg (up to 5.5 mm): tolerance 0.012 m
ok(dData < 0.012, `data lat_lon -> xz max ${dData} m (${worst})`);
// (4)
ok(Math.abs(G.haeFromY(2.5, 300, -800) - R.hae) < 1e-9, 'haeFromY'); ok(Math.abs(G.yFromPressureAlt(3000, 1022) - R.pa) < 1e-6, 'yFromPressureAlt');
// runway helpers
const I = G.initGeo(A); ok(I.runways.length === 2 && Object.keys(I.ends).length === 4, 'runways / ends from data');
for (const R2 of G.RUNWAYS) { const m = G.rwyToWorld(R2, R2.len / 2, 0); const st = G.rwyAlongAcross(R2, m[0], m[1]); ok(Math.abs(st[0] - R2.len / 2) < 1e-6 && Math.abs(st[1]) < 1e-6, 'rwyAlongAcross inverse ' + R2.id);
  ok(Math.abs(G.vecHdg(R2.dir[0], R2.dir[1]) - R2.hdg) < 0.01, `runway dir vs heading ${R2.id}: ${G.vecHdg(R2.dir[0], R2.dir[1]).toFixed(3)} vs ${R2.hdg}`); }
const h = G.hdgVec(90); ok(Math.abs(h[0] - 1) < 1e-12 && Math.abs(h[1]) < 1e-12, 'hdgVec(90) = east'); const h2 = G.hdgVec(180); ok(Math.abs(h2[1] - 1) < 1e-12, 'hdgVec(180) = +z (south)');
console.log(`geo.js twin test: ${pts.length} grid points, ${pairs.length} data points; ll->world ${dMax.toExponential(2)} m, world->ll ${dInv.toExponential(2)} m, round trip ${dRt.toExponential(2)} m, data ${dData.toFixed(4)} m (${worst}); ${fails ? fails + ' FAILED' : 'all passed'}`);
process.exit(fails ? 1 : 0);
