// Dumps the HWD paint geometry (js/live/markings.js, Node-pure part) as world-frame triangles for the NAIP overlay check
// (dev/naip_compare.py). Ribbon vertices are expanded to their painted half width (as the shader does near the camera).
//   node dev/paint_dump.mjs [out/phase2/paint_tris.json]
import fs from 'node:fs';
import { buildSite } from '../js/world/site.js';
import { buildPaintData } from '../js/live/markings.js';
import { HWD_AIRPORT } from '../data/hwd_airport.js';
import { endWorld, thrWorld, RWY_PAIRS } from '../js/geo.js';

const out = process.argv[2] || new URL('../out/phase2/paint_tris.json', import.meta.url).pathname;
const site = buildSite(HWD_AIRPORT);
const D = buildPaintData(site, HWD_AIRPORT);
const P = D.P; const n = P.pos.length / 3;
const xz = new Float32Array(n * 2);
for (let i = 0; i < n; i++) {
  const hw = P.ext[i * 4], side = P.ext[i * 4 + 1];
  let x = P.pos[i * 3], z = P.pos[i * 3 + 2];
  if (hw >= 0) { x += P.nrm[i * 3] * side * hw; z += P.nrm[i * 3 + 2] * side * hw; }
  xz[i * 2] = x; xz[i * 2 + 1] = z;
}
const tris = [];
for (let k = 0; k < P.idx.length; k += 3) {
  const a = P.idx[k], b = P.idx[k + 1], c = P.idx[k + 2];
  const col = P.col[a * 4 + 1] < 0.7 ? 'Y' : 'W';
  tris.push([+xz[a * 2].toFixed(3), +xz[a * 2 + 1].toFixed(3), +xz[b * 2].toFixed(3), +xz[b * 2 + 1].toFixed(3), +xz[c * 2].toFixed(3), +xz[c * 2 + 1].toFixed(3), col]);
}
fs.writeFileSync(out, JSON.stringify({ tris, inventory: D.inventory }));
console.log(`${tris.length} triangles -> ${out}`);
// site dump for the comparison crops: runway ends / thresholds and every extruded footprint
const ends = {};
for (const pr of RWY_PAIRS) for (const e of pr) { const a = endWorld(e), t = thrWorld(e); ends[e] = [a[0], a[2]]; ends[e + '_thr'] = [t[0], t[2]]; }
const sOut = out.replace(/paint_tris\.json$/, 'site_dump.json');
fs.writeFileSync(sOut, JSON.stringify({ ends, rings: site.buildings.map(b => b.ring), tower: site.anchors.tower, windsock: site.anchors.windsock }));
console.log('site -> ' + sOut);
