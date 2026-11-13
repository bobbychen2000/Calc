// HWD buildings: hangar rows (T-hangar / box), the control tower, the terminal / airport administration building, the
// FBO hangars, the fire station and the other OSM buildings inside the aerodrome - simple solid prisms on the real
// footprints (Phase 4 adds doors, detail and measured heights).
// Replaces sfo3d/js/live/terminals.js @ a967f9b (fork map 1.3: "replace (tower from OSM way 204803620, 15.85 m)"). Kept
// from sfo3d: the Geo builder and the object shader material ids (2 concrete panels, 4 corrugated metal, 5 flat roof,
// 6 punched windows, 12 tower cab glass, js/shaders/objects.js), one render item per building with a world bbox.
// Sources: footprints = OpenStreetMap (data/hwd_airport.json hangars[] / buildings[], ODbL); heights = js/world/site.js
// HEIGHT_RULES (only the tower's 15.85 m is sourced, OSM height tag; every other height is [inf] and reported as such);
// roof shapes, wall colours and the tower's glazing band are [inf] (NAIP 2024 shows white hangar roofs with a ridge
// line, refs/cache/naip/naip_visual_notes.json; it does not show walls or doors).
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { v3 } from '../math.js';
import { earcut } from '../world/earcut.js';
import { minRect } from '../world/site.js';

// [rough, metal, matID, emissive] (js/shaders/objects.js)
const E_METAL = [0.55, 0.35, 4, 0], E_ROOF = [0.7, 0.1, 5, 0], E_CONC = [0.85, 0, 2, 0], E_WIN = [0.6, 0, 6, 0], E_CAB = [0.1, 0, 12, 0], E_PLAIN = [0.85, 0, 0, 0];
// colours (linear albedo) [inf]: hangar walls light grey / off-white metal, roofs white (NAIP 2024 roofs read white)
const C_TWALL = [0.55, 0.55, 0.52, 1], C_BWALL = [0.50, 0.52, 0.54, 1], C_ROOF = [0.62, 0.62, 0.60, 1], C_BLD = [0.55, 0.52, 0.47, 1], C_TWR = [0.58, 0.56, 0.52, 1], C_FIRE = [0.50, 0.30, 0.25, 1];

function area2(r) { let a = 0; for (let i = 0; i < r.length; i++) { const p = r[i], q = r[(i + 1) % r.length]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; }
const ccw = (r) => area2(r) > 0 ? r : r.slice().reverse();   // positive (x, z) shoelace area: walls face outward
// vertical walls of ring r from y0 to y1(i, point) (per-vertex top height)
function walls(g, r, y0, ytop, c, e) {
  for (let i = 0; i < r.length; i++) {
    const a = r[i], b = r[(i + 1) % r.length];
    g.quad([a[0], y0, a[1]], [a[0], ytop(a), a[1]], [b[0], ytop(b), b[1]], [b[0], y0, b[1]], c, e);
  }
}
// flat cap with explicit up orientation
function cap(g, r, y, c, e) {
  const flat = []; for (const p of r) flat.push(p[0], p[1]);
  const t = earcut(flat); const base = g.nv;
  for (const p of r) g.vert([p[0], y, p[1]], [0, 1, 0], c, e);
  for (let i = 0; i < t.length; i += 3) {
    const A = r[t[i]], B = r[t[i + 1]], C = r[t[i + 2]];
    const ny = (B[1] - A[1]) * (C[0] - A[0]) - (B[0] - A[0]) * (C[1] - A[1]);   // y of cross(B-A, C-A)
    if (ny >= 0) g.tri(base + t[i], base + t[i + 1], base + t[i + 2]); else g.tri(base + t[i], base + t[i + 2], base + t[i + 1]);
  }
}
// gable roof over a 4-vertex near-rectangular footprint: ridge along the long axis, `rise` m above the eave
function gable(g, r, yE, rise, cRoof, eRoof, cWall, eWall) {
  const mr = minRect(r); const u = mr.u;
  // order so that edges 0-1 and 2-3 are the long sides
  let k0 = 0, best = -1; for (let i = 0; i < 4; i++) { const a = r[i], b = r[(i + 1) % 4]; const d = Math.abs((b[0] - a[0]) * u[0] + (b[1] - a[1]) * u[1]); if (d > best) { best = d; k0 = i; } }
  const c = [0, 1, 2, 3].map(i => r[(k0 + i) % 4]);
  const m03 = [(c[0][0] + c[3][0]) / 2, (c[0][1] + c[3][1]) / 2], m12 = [(c[1][0] + c[2][0]) / 2, (c[1][1] + c[2][1]) / 2];
  const P = (p, y) => [p[0], y, p[1]]; const yR = yE + rise;
  const quadOut = (a, b, cc, d, want) => { const n = v3.cross(v3.sub(b, a), v3.sub(d, a)); if (v3.dot(n, want) < 0) g.quad(a, d, cc, b, cRoof, eRoof); else g.quad(a, b, cc, d, cRoof, eRoof); };
  const ctr = [(c[0][0] + c[2][0]) / 2, 0, (c[0][1] + c[2][1]) / 2];
  const outOf = (q) => v3.add(v3.sub([q[0], 0, q[1]], ctr), [0, 2 * Math.max(1, rise), 0]);
  quadOut(P(c[0], yE), P(c[1], yE), P(m12, yR), P(m03, yR), outOf([(c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2]));
  quadOut(P(c[2], yE), P(c[3], yE), P(m03, yR), P(m12, yR), outOf([(c[2][0] + c[3][0]) / 2, (c[2][1] + c[3][1]) / 2]));
  // gable-end triangles (wall material)
  for (const [a, b, m] of [[c[1], c[2], m12], [c[3], c[0], m03]]) {
    const A = P(a, yE), B = P(b, yE), M = P(m, yR); const want = v3.sub([m[0], 0, m[1]], ctr);
    const n = v3.cross(v3.sub(B, A), v3.sub(M, A)); const nn = v3.norm(v3.dot(n, want) < 0 ? v3.mul(n, -1) : n);
    const i0 = g.vert(A, nn, cWall, eWall), i1 = g.vert(B, nn, cWall, eWall), i2 = g.vert(M, nn, cWall, eWall);
    if (v3.dot(n, want) < 0) g.tri(i0, i2, i1); else g.tri(i0, i1, i2);
  }
}

/** One render item per building. Returns {items, stats, list}. */
export function buildBuildings(site) {
  const items = [], list = [];
  const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  const add = (g, b, groundRef) => { const d = g.data(); items.push({ mesh: new Mesh(d), prog: 'obj', model: I4, bbox: d.bbox, castShadow: true, groundRef, uniforms: { uEmissiveBoost: 1 }, building: b.id }); return d.idx.length / 3; };
  let tris = 0;
  for (const b of site.buildings) {
    const r = ccw(b.ring); const g = new Geo();
    let ymin = 1e9; for (const p of r) ymin = Math.min(ymin, site.groundY(p[0], p[1]));
    const yG = site.groundY(b.centroid[0], b.centroid[1]); const y0 = ymin - 0.3; const H = b.height_m;
    const rect = r.length === 4 && minRect(r).len * minRect(r).wid <= Math.abs(area2(r)) * 1.1;
    if (b.kind === 't_hangar_row' || b.kind === 'box_hangar') {
      const rise = b.kind === 't_hangar_row' ? 0.8 : Math.min(1.6, 0.06 * minRect(r).wid);   // low-pitch roof [inf]
      const yE = yG + H - (rect ? rise : 0);
      const cw = b.kind === 't_hangar_row' ? C_TWALL : C_BWALL;
      walls(g, r, y0, () => yE, cw, E_METAL);
      if (rect) gable(g, r, yE, rise, C_ROOF, E_METAL, cw, E_METAL); else cap(g, r, yE, C_ROOF, E_ROOF);
    } else if (b.kind === 'control_tower') {
      // OSM footprint and total height (15.85 m, obs). Fix round 1: only the tall part (site TOWER_TALL, by eye on NAIP,
      // [inf]) rises to 15.85 m with the cab glazing band; the rest of the ring is a single-storey base [inf]. The base is
      // the whole ring (the shaft stands on it), so no inner wall is needed.
      const T = b.tall; const yTop = yG + H, yGl0 = yTop - 3.25, yGl1 = yTop - 0.85;
      const yB = T ? yG + T.baseH : yGl0; const rt = T ? ccw(T.ring) : r;
      if (T) { walls(g, r, y0, () => yB, C_BLD, E_CONC); cap(g, r, yB, C_ROOF, E_ROOF); }
      walls(g, rt, T ? yB - 0.1 : y0, () => yGl0, C_TWR, E_CONC);
      walls(g, rt, yGl0, () => yGl1, [0.05, 0.06, 0.07, 1], E_CAB);
      walls(g, rt, yGl1, () => yTop, C_TWR, E_CONC);
      cap(g, rt, yTop, C_ROOF, E_ROOF);
    } else {
      walls(g, r, y0, () => yG + H, b.kind === 'fire_station' && H > 5 ? C_FIRE : C_BLD, b.kind === 'terminal_admin' ? E_WIN : E_CONC);
      cap(g, r, yG + H, C_ROOF, E_ROOF);
    }
    tris += add(g, b, yG);
    list.push({ id: b.id, kind: b.kind, name: b.name, height_m: H, height_src: b.height_src, footprint_src: b.footprint_src || 'obs (OSM)', ...(b.tall ? { tall_part: 'inf (NAIP 2022 + 2024 by eye, ~8 x 9 m)', base_h_m: b.tall.baseH } : {}) });
  }
  return { items, list, stats: { buildings: list.length, tris } };
}
