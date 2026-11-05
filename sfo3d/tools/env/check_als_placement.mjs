// tools/env/check_als_placement.mjs (environment step 2, docs/research/environment_impl.md §2.4)
// Physical check of the ALS light placement (environment step 2): every ALS light either inset on pavement, on an
// imaged pier station / crossbar (over water), or on a mount (land / unsupported water); no light inside or under a
// structure, none floating. Run: node tools/env/check_als_placement.mjs (exit 1 on failure) 
import { LIGHTING_SPEC, LIGHTING_FIXTURES } from '../../data/sfo_lighting.js';
import { AirfieldLighting } from '../../js/env/lighting/airfield.js';
import { alsPlacement, buildAirfieldLights } from '../../js/anim/lights.js';
import { APPROACH_STRUCTURES, GROUND_Y, worldToST } from '../../js/geo.js';
import { polySDF } from '../../js/world/terrain.js';
import { AIRPORT_LAND_ST } from '../../js/geo.js';
const FT = 0.3048;
const plane = {}; for (const R of LIGHTING_SPEC.runways) for (const [E, e] of Object.entries(R.ends)) if (e.als && e.landing_threshold) plane[E] = GROUND_Y + (e.landing_threshold.elev_ft - 13.1) * FT;
const isWater = (x, z) => { const [s, t] = worldToST(x, z); return polySDF(s, t, AIRPORT_LAND_ST) < 0; };
const place = Object.fromEntries(Object.entries(plane).map(([E, y]) => [E, alsPlacement(E, y)]));
const placeW = Object.fromEntries(Object.entries(place).map(([E, f]) => [E, (st, lat) => f(st, lat, isWater)]));
const AL = new AirfieldLighting(LIGHTING_FIXTURES, LIGHTING_SPEC, { groundY: GROUND_Y, alsPlace: placeW });
const sys = buildAirfieldLights(1.0, { taxiways: false, lightPlane: plane });
const piers = sys.piers.filter(P => P.water);
console.log('plane', JSON.stringify(plane), 'kinds', JSON.stringify(AL.alsKinds));
const bad = [], info = []; const byEnd = {};
for (const r of AL.recs) {
  if (!r.place) continue;
  const k = r.end + ' ' + r.place; byEnd[k] = (byEnd[k] || 0) + 1;
  if (r.place === 'pier') {
    // support: the station beam (+-2.6 m of the axis) at the snapped station, or an imaged crossbar there
    const ST = APPROACH_STRUCTURES[r.end];
    const near = ST.stationsFt.reduce((a, b) => Math.abs(b - r.station) < Math.abs(a - r.station) ? b : a);
    const cb = ST.crossbars.find(c => Math.abs(c.ft - near) < 30);
    const ok = Math.abs(r.lat) <= 2.6 || (cb && r.lat >= cb.l - 0.05 && r.lat <= cb.r + 0.05);
    const top = plane[r.end] - 0.6 + 0.5;   // station beam top (buildPierGeometry: h + 0.5)
    if (!ok) bad.push(`${r.system} ${r.end} st ${r.station} lat ${r.lat.toFixed(2)}: no structure under it`);
    if (r.p[1] < top - 1e-6) bad.push(`${r.system} ${r.end} st ${r.station}: light below the structure top`);
  }
  if (r.place === 'land' && isWater(r.p[0], r.p[2])) bad.push(`${r.system} ${r.end} st ${r.station}: 'land' over water`);
  if (r.place === 'inset' && r.p[1] < GROUND_Y) bad.push(`inset below ground`);
  if (r.place === 'inset' && isWater(r.p[0], r.p[2])) info.push(`${r.system} ${r.end} st ${r.station}: inset on the EMAS / blast pad (END_ZONES, NAIP) where AIRPORT_LAND_ST says water`);
}
const M = AL.mountGroups();
console.log('placements', JSON.stringify(byEnd));
console.log('mount groups', M.length, 'water piles', M.filter(g => g.water).length, 'max bar', Math.max(...M.map(g => g.hi - g.lo)).toFixed(2), 'min height', Math.min(...M.map(g => g.yTop - (g.water ? -2 : GROUND_Y))).toFixed(2));
console.log('pier tops', [...new Set(piers.map(P => (P.h + 0.5).toFixed(3)))].join(' '));
if (info.length) console.log('INFO ' + info.length + ': ' + info[0]);
console.log(bad.length ? 'FAIL ' + bad.length + '\n' + bad.slice(0, 20).join('\n') : 'PASS: every ALS light supported (inset / pier / mount)');
process.exit(bad.length ? 1 : 0);
