// sha3d placeholder buildings (new): every building footprint of data/sha_airport.js (35 airport buildings + the context
// buildings of the detailed extent) extruded to its height_m, and a generic control-tower stand-in. They are stand-ins:
// all heights are rule defaults or AIP elevations (height_src 'inf' in the data), roof shapes and facades are not
// sourced, and the terminals package (js/live/terminals.js) replaces any building it claims (ext.claimBuildings).
// Materials are object-shader material ids (js/shaders/objects.js: 1 glass curtain wall, 2 concrete panels, 3 parking
// facade, 4 corrugated metal, 5 flat roof, 6 punched windows, 11 parking roof, 12 tower cab glass) [inf].
import { Geo } from '../geom.js';
import { GROUND_Y } from '../geo.js';

const MAT = {
  terminal: { wall: [0.30, 0.32, 0.34, 1], we: [0.3, 0.2, 1, 0], roof: [0.52, 0.53, 0.54, 1], re: [0.7, 0.1, 5, 0] },
  train_station: { wall: [0.30, 0.32, 0.34, 1], we: [0.3, 0.2, 1, 0], roof: [0.50, 0.51, 0.52, 1], re: [0.7, 0.1, 5, 0] },
  business_terminal: { wall: [0.30, 0.32, 0.34, 1], we: [0.3, 0.2, 1, 0], roof: [0.5, 0.5, 0.5, 1], re: [0.8, 0, 5, 0] },
  hangar: { wall: [0.50, 0.53, 0.56, 1], we: [0.5, 0.4, 4, 0], roof: [0.55, 0.56, 0.57, 1], re: [0.6, 0.3, 5, 0] },
  parking: { wall: [0.55, 0.54, 0.52, 1], we: [0.9, 0, 3, 0], roof: [0.33, 0.33, 0.34, 1], re: [0.9, 0, 11, 0] },
  hotel: { wall: [0.48, 0.47, 0.45, 1], we: [0.8, 0, 6, 0], roof: [0.45, 0.45, 0.44, 1], re: [0.9, 0, 5, 0] },
  office: { wall: [0.46, 0.47, 0.47, 1], we: [0.8, 0, 6, 0], roof: [0.45, 0.45, 0.44, 1], re: [0.9, 0, 5, 0] },
  apartments: { wall: [0.50, 0.47, 0.42, 1], we: [0.9, 0, 6, 0], roof: [0.30, 0.29, 0.28, 1], re: [0.9, 0, 5, 0] },
  residential: { wall: [0.50, 0.47, 0.42, 1], we: [0.9, 0, 6, 0], roof: [0.30, 0.29, 0.28, 1], re: [0.9, 0, 5, 0] },
  default: { wall: [0.46, 0.46, 0.45, 1], we: [0.9, 0, 2, 0], roof: [0.33, 0.33, 0.33, 1], re: [0.9, 0, 5, 0] },
};
const area2 = (r) => { let a = 0; for (let i = 0; i < r.length; i++) { const p = r[i], q = r[(i + 1) % r.length]; a += p[0] * q[1] - q[0] * p[1]; } return a; };
// Geo.extrude wants a ring with positive shoelace area in (x, z) (outward walls; tested in docs/phase2/core.md)
const orient = (r) => area2(r) < 0 ? r.slice().reverse() : r;
const tint = (c, k) => [c[0] * k, c[1] * k, c[2] * k, c[3]];
function hashId(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return ((h >>> 0) % 1000) / 1000; }

/** Extrude buildings. opts: {skip: Set of ids, y0}. Returns {geo: Geo.data(), count, skipped, list: [{id, kind, h, src}]} */
export function buildPlaceholderBuildings(buildings, opts = {}) {
  const g = new Geo(); const skip = opts.skip || new Set(); const y0 = opts.y0 ?? GROUND_Y;
  let count = 0, skipped = 0; const list = [];
  for (const b of buildings || []) {
    if (skip.has(b.id)) { skipped++; continue; }
    const h = Math.max(3, +b.height_m || 10); const M = MAT[b.kind] || MAT.default; const k = 0.88 + 0.24 * hashId(b.id);
    for (const ring of [b.ring, ...((b.more_rings || []).map(r => Array.isArray(r[0][0]) ? r[0] : r))]) {
      if (!ring || ring.length < 3) continue;
      const r = orient(ring);
      g.extrude(r, y0 - 0.5, y0 + h, tint(M.wall, k), M.we, tint(M.roof, k), M.re);
    }
    count++; list.push({ id: b.id, kind: b.kind, h, src: b.height_src || 'inf' });
  }
  return { geo: g.data(), count, skipped, list };
}

/** Generic control-tower stand-in at the OSM / AIP tower position: a round shaft, a glazed cab and a roof. The real form
 *  is not sourced (data not_yet_sourced: "control tower form"); height = AIP (mirror) obstacle elevation - ground [inf]. */
export function buildTowerPlaceholder(tower, y0 = GROUND_Y) {
  if (!tower) return null;
  const g = new Geo(); const H = tower.height_m || 44.5; const x = tower.x, z = tower.z;
  const T = (px, py, pz) => new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, px, py, pz, 1]);
  const cabH = 5.5, cabB = y0 + H - cabH - 2.0;
  g.lathe([[3.6, 0], [3.4, cabB - y0 - 2.5], [6.5, cabB - y0 - 0.6], [6.8, cabB - y0]], 24, [0.72, 0.72, 0.70, 1], [0.8, 0, 2, 0], T(x, y0, z));
  g.lathe([[6.8, 0], [7.4, cabH]], 24, [0.05, 0.07, 0.08, 1], [0.1, 0, 12, 0], T(x, cabB, z));
  g.lathe([[7.6, 0], [7.6, 0.6], [4.0, 2.0], [0.01, 2.0]], 24, [0.62, 0.62, 0.62, 1], [0.6, 0.2, 0, 0], T(x, cabB + cabH, z), true);
  return { geo: g.data(), eyeY: cabB + cabH * 0.55, top: y0 + H, pos: [x, y0, z] };
}
