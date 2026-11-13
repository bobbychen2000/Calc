// HWD site model (new for hwd3d; fork map 2.4 contract). Pure JS, Node-importable: no DOM, no WebGL, no canvas.
// It answers the physical questions every package asks about the ground - how high it is, whether it is paved, what
// surface it is, which runway / apron / building is there - from data/hwd_airport.json (Phase 1, frozen) and the FAA
// NASR runway helpers of js/geo.js. It replaces sfo3d's flat GROUND_Y = 3 and the rendered pavement mask (apt.paved).
//
//   buildSite(airport, { res = 0.5, bres = 1.0 }) -> Site
//   Site.rect {x0, z0, w, h, res}         world-axis raster extent (m) covering the aerodrome data + 40 m
//   Site.groundY(x, z) -> y               NAVD 88 m (see GROUND below)
//   Site.paved(x, z) -> bool              runways ∪ open/closed taxi ribbons ∪ aprons ∪ helipads (raster, res)
//   Site.surface(x, z) -> 'runway'|'taxiway'|'taxilane'|'apron'|'helipad'|'closed'|'grass'
//   Site.runwayAt(x, z) -> {id, along, across, end} | null   inside the NASR rectangle (exact geometry, not raster);
//                                         along from the runway's first end (10L / 10R), across > 0 = right of it,
//                                         end = the end whose half of the runway holds the point
//   Site.apronAt(x, z) -> {id, name} | null                  OSM apron polygons (exact point-in-polygon)
//   Site.building(x, z) -> bool           building / hangar footprints (raster, bres = 1 m)
//   Site.buildingAt(x, z) -> {id, kind, name, height_m, height_src} | null
//   Site.hangars [{id, letter, name, kind, ring, height_m, height_src, height_rule, role}]
//   Site.buildings [{id, kind, name, ring, height_m, height_src, height_rule}]   every drawn footprint (hangars included)
//   Site.anchors {tower: {x, z, y, eyeY, src}, aprons: {name: [x, z]}, windsock: [x, z], thresholds: {end: [x, z]}}
//   Site.stats {...}
//
// GROUND (y = NAVD 88 height, m; geo.js header). Observed: the FAA NASR runway end and displaced-threshold elevations
// (8.44-15.88 m), interpolated linearly along each runway (geo.js rwySurfaceY, [inf] between the surveyed points); the
// runway cross-section is taken flat (no crown) [inf]. Elsewhere there is no elevation source yet (USGS 3DEP is optional,
// PLAN §2), so the field surface is an inverse-square-distance blend of the two runway profiles [inf]:
//   y = Σ w_i h_i / Σ w_i,  h_i = runway i surface at the point's along position (clamped to the runway ends),
//   w_i = 1 / (d_i² + 1 m²), d_i = distance to runway i's NASR rectangle;
// inside a rectangle y is exactly that runway's surface. The blend is continuous at the rectangle edges (the other
// runway's weight there is < 1e-4) and smooth elsewhere; beyond the runway ends it holds the end elevations.
import { RWY_PAIRS, RWY_DATA, FT, rwyAxis, rwySurfaceY, endWorld, thrWorld } from '../geo.js';

export const SURFACES = ['grass', 'closed', 'apron', 'taxilane', 'taxiway', 'helipad', 'runway'];   // index = priority
const S = Object.fromEntries(SURFACES.map((k, i) => [k, i]));

// Building heights. Only the control tower has a source (OSM height=15.85 on way 204803620). Everything else is a rule
// [inf] until Phase 4 measures them (NAIP shadow lengths calibrated on the tower, or photos):
export const HEIGHT_RULES = {
  control_tower: { h: null, src: 'obs', rule: 'OSM way 204803620 height=15.85 (top of the structure)' },
  t_hangar_row: { h: 4.5, src: 'inf', rule: 'T-hangar row for ADG I singles: single storey, ~3.4 m door + structure + low-pitch roof; no source' },
  box_hangar: { h: null, src: 'inf', rule: 'box hangar: height = clamp(4 m + 0.12 x shorter side, 6 m, 12 m); no source (door height scales with the span it serves)' },
  terminal_admin: { h: 7.5, src: 'inf', rule: 'two storeys x 3.75 m; no source' },
  fire_station: { h: 6.0, src: 'inf', rule: 'apparatus bay ~ 4.3 m doors + structure; no source' },
  building: { h: 4.5, src: 'inf', rule: 'single storey; no source' },
};
// control-tower eye height: OSM gives only the top (15.85 m); cab roof / glazing / floor are not sourced. Eye = top -
// 2.4 m (0.9 m roof + 1.5 m above the eye line of a standing controller) [inf]
export const TOWER_EYE_BELOW_TOP = 2.4;
// Fire station footprint [inf]: read by eye on a 0.15 m north-up resampling of NAIP 2024 centred at world (290, 585)
// (+-1 m): a main block 55.8 x 18.5 m and a 6 m deep lower strip along its north side (~1,300 m2; AL-5015 block ~1,270 m2)
export const FIRE_STATION_NAIP = {
  id: 'naip:fire_station', name: 'Hayward Fire Station Number 6',
  parts: [{ suffix: '#main', ring: [[271.7, 579.3], [327.5, 579.3], [327.5, 597.8], [271.7, 597.8]], h: 7.0 },
    { suffix: '#north', ring: [[274.3, 573.3], [328.3, 573.3], [328.3, 579.3], [274.3, 579.3]], h: 4.0 }],
  height_rule: 'apparatus-bay block 7.0 m, lower strip 4.0 m; no source',
};

function ringArea(r) { let a = 0; for (let i = 0; i < r.length; i++) { const p = r[i], q = r[(i + 1) % r.length]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; }
function centroid(r) {
  let a = 0, cx = 0, cz = 0;
  for (let i = 0; i < r.length; i++) { const p = r[i], q = r[(i + 1) % r.length]; const k = p[0] * q[1] - q[0] * p[1]; a += k; cx += (p[0] + q[0]) * k; cz += (p[1] + q[1]) * k; }
  if (Math.abs(a) < 1e-9) { const n = r.length; return [r.reduce((s, p) => s + p[0], 0) / n, r.reduce((s, p) => s + p[1], 0) / n]; }
  return [cx / (3 * a), cz / (3 * a)];
}
export function pointInRing(x, z, r) {
  let inside = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const a = r[i], b = r[j];
    if (((a[1] > z) !== (b[1] > z)) && (x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0])) inside = !inside;
  }
  return inside;
}
// minimum rectangle (rotating calipers over the hull edges, brute force on the ring edges is enough for <= 30 vertices)
export function minRect(r) {
  let best = null;
  for (let i = 0; i < r.length; i++) {
    const a = r[i], b = r[(i + 1) % r.length]; let ux = b[0] - a[0], uz = b[1] - a[1]; const L = Math.hypot(ux, uz); if (L < 1e-6) continue; ux /= L; uz /= L;
    let s0 = 1e9, s1 = -1e9, t0 = 1e9, t1 = -1e9;
    for (const p of r) { const s = p[0] * ux + p[1] * uz, t = -p[0] * uz + p[1] * ux; s0 = Math.min(s0, s); s1 = Math.max(s1, s); t0 = Math.min(t0, t); t1 = Math.max(t1, t); }
    const area = (s1 - s0) * (t1 - t0);
    if (!best || area < best.area) best = { area, u: [ux, uz], len: s1 - s0, wid: t1 - t0 };
  }
  if (best && best.wid > best.len) { const t = best.len; best.len = best.wid; best.wid = t; best.u = [-best.u[1], best.u[0]]; }
  return best;
}

// ---------------------------------------------------------------- raster helpers (pure JS scanline)
class Raster {
  constructor(x0, z0, nx, nz, res, Arr) { this.x0 = x0; this.z0 = z0; this.nx = nx; this.nz = nz; this.res = res; this.a = new Arr(nx * nz); }
  idx(x, z) { const i = Math.floor((x - this.x0) / this.res), j = Math.floor((z - this.z0) / this.res); return (i < 0 || j < 0 || i >= this.nx || j >= this.nz) ? -1 : j * this.nx + i; }
  get(x, z) { const k = this.idx(x, z); return k < 0 ? 0 : this.a[k]; }
  // set cells whose centre lies in [xa, xb] on row j, through put(k)
  span(j, xa, xb, put) {
    const i0 = Math.max(0, Math.ceil((xa - this.x0) / this.res - 0.5)), i1 = Math.min(this.nx - 1, Math.floor((xb - this.x0) / this.res - 0.5));
    for (let i = i0, k = j * this.nx + i0; i <= i1; i++, k++) put(k);
  }
  // even-odd polygon fill (rings: list of [[x, z], ...])
  fillRings(rings, put) {
    let z0 = 1e9, z1 = -1e9; for (const r of rings) for (const p of r) { z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); }
    const j0 = Math.max(0, Math.ceil((z0 - this.z0) / this.res - 0.5)), j1 = Math.min(this.nz - 1, Math.floor((z1 - this.z0) / this.res - 0.5));
    const xs = [];
    for (let j = j0; j <= j1; j++) {
      const z = this.z0 + (j + 0.5) * this.res; xs.length = 0;
      for (const r of rings) for (let i = 0, k = r.length - 1; i < r.length; k = i++) {
        const a = r[i], b = r[k]; if ((a[1] > z) !== (b[1] > z)) xs.push(a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
      }
      xs.sort((p, q) => p - q);
      for (let m = 0; m + 1 < xs.length; m += 2) this.span(j, xs[m], xs[m + 1], put);
    }
  }
  // capsule ribbon of half-width hw along a polyline: one convex quad per segment + a disc at every vertex
  fillRibbon(pts, hw, put) {
    for (let n = 1; n < pts.length; n++) {
      const a = pts[n - 1], b = pts[n]; let dx = b[0] - a[0], dz = b[1] - a[1]; const L = Math.hypot(dx, dz); if (L < 1e-6) continue;
      const nx = -dz / L * hw, nz = dx / L * hw;
      this.fillRings([[[a[0] + nx, a[1] + nz], [b[0] + nx, b[1] + nz], [b[0] - nx, b[1] - nz], [a[0] - nx, a[1] - nz]]], put);
    }
    for (const p of pts) {
      const j0 = Math.max(0, Math.ceil((p[1] - hw - this.z0) / this.res - 0.5)), j1 = Math.min(this.nz - 1, Math.floor((p[1] + hw - this.z0) / this.res - 0.5));
      for (let j = j0; j <= j1; j++) { const dz = this.z0 + (j + 0.5) * this.res - p[1]; const h = hw * hw - dz * dz; if (h < 0) continue; const dx = Math.sqrt(h); this.span(j, p[0] - dx, p[0] + dx, put); }
    }
  }
}

// paved half-width of a taxiway / taxilane: the NAIP grey-test width where Phase 1 marked it obs (6 ways), else the
// AC 150/5300-13B Table 4-2 default of the data (TDG 2 taxiway 35 ft / TDG 1 taxilane 25 ft, inf)
export function wayWidth(w) {
  const W = w.width || {};
  if (W.naip_src === 'obs' && W.naip_grey_width_m) return { m: W.naip_grey_width_m, src: 'obs', basis: 'NAIP 2024 grey-test width (Phase 1)' };
  return { m: W.default_m || (w.kind === 'taxilane' ? 7.62 : 10.67), src: 'inf', basis: W.default_basis || 'AC 150/5300-13B Table 4-2 default' };
}

export function buildSite(airport, { res = 0.5, bres = 1.0 } = {}) {
  const t0 = (typeof performance !== 'undefined' ? performance : Date).now();
  const A = airport;
  // ---------------------------------------------------------------- runways (FAA NASR via geo.js)
  const rws = RWY_PAIRS.map(([a, b]) => {
    const id = `${a}/${b}`, ax = rwyAxis(a), hw = RWY_DATA[id].widthFt * FT / 2;
    return { id, a, b, ax, hw, L: ax.length };
  });
  const rwLocal = (r, x, z) => { const px = x - r.ax.origin[0], pz = z - r.ax.origin[1]; return [px * r.ax.dir[0] + pz * r.ax.dir[1], px * r.ax.right[0] + pz * r.ax.right[1]]; };
  function runwayAt(x, z) {
    for (const r of rws) {
      const [al, ac] = rwLocal(r, x, z);
      if (al >= 0 && al <= r.L && Math.abs(ac) <= r.hw) return { id: r.id, along: al, across: ac, end: al <= r.L / 2 ? r.a : r.b };
    }
    return null;
  }
  function groundY(x, z) {
    let sw = 0, sh = 0;
    for (const r of rws) {
      const [al, ac] = rwLocal(r, x, z);
      const alc = al < 0 ? 0 : al > r.L ? r.L : al;
      const h = rwySurfaceY(r.a, alc);
      const da = al - alc, dc = Math.max(0, Math.abs(ac) - r.hw);
      const d2 = da * da + dc * dc;
      if (d2 === 0) return h;
      const w = 1 / (d2 + 1); sw += w; sh += w * h;
    }
    return sh / sw;
  }
  // ---------------------------------------------------------------- raster extent
  const pts = [];
  for (const k of ['taxiways', 'taxilanes']) for (const w of A[k]) pts.push(...w.pts);
  for (const k of ['aprons', 'hangars', 'buildings', 'helipads']) for (const e of A[k]) if (e.ring) pts.push(...e.ring);
  for (const r of A.runways) pts.push(...r.outline.ring);
  let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; for (const p of pts) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); }
  const M = 40; x0 = Math.floor((x0 - M) / 10) * 10; z0 = Math.floor((z0 - M) / 10) * 10; x1 = Math.ceil((x1 + M) / 10) * 10; z1 = Math.ceil((z1 + M) / 10) * 10;
  const nx = Math.round((x1 - x0) / res), nz = Math.round((z1 - z0) / res);
  const rect = { x0, z0, w: nx * res, h: nz * res, res };
  const surf = new Raster(x0, z0, nx, nz, res, Uint8Array);
  const putS = (v) => (k) => { if (surf.a[k] < v) surf.a[k] = v; };
  // aprons (OSM polygons), closed ways, taxilanes, taxiways, helipads, runways - the higher class wins in each cell
  for (const ap of A.aprons) surf.fillRings([ap.ring], putS(S.apron));
  const ribbons = { taxiway: 0, taxilane: 0, closed: 0, width_obs: 0 };
  for (const k of ['taxilanes', 'taxiways']) for (const w of A[k]) {
    const W = wayWidth(w); const cls = w.status === 'open' ? S[w.kind] : S.closed;
    surf.fillRibbon(w.pts, W.m / 2, putS(cls)); ribbons[w.status === 'open' ? w.kind : 'closed']++; if (W.src === 'obs') ribbons.width_obs++;
  }
  for (const hp of A.helipads) surf.fillRings([hp.ring], putS(S.helipad));
  for (const r of A.runways) surf.fillRings([r.outline.ring], putS(S.runway));
  // ---------------------------------------------------------------- buildings and hangars
  const blds = [];
  const heightOf = (kind, ring, given) => {
    if (kind === 'control_tower' && given) return { h: given, src: 'obs', rule: HEIGHT_RULES.control_tower.rule };
    const R = HEIGHT_RULES[kind] || HEIGHT_RULES.building;
    if (kind === 'box_hangar') { const mr = minRect(ring); const h = Math.min(12, Math.max(6, 4 + 0.12 * mr.wid)); return { h: Math.round(h * 10) / 10, src: 'inf', rule: R.rule }; }
    return { h: R.h, src: R.src, rule: R.rule };
  };
  for (const h of A.hangars) {
    const H = heightOf(h.kind, h.ring);
    blds.push({ id: h.id, kind: h.kind, name: h.name, letter: h.letter, role: h.role || null, ring: h.ring, height_m: H.h, height_src: H.src, height_rule: H.rule, hangar: true });
  }
  for (const b of A.buildings) {
    if (!b.ring || b.ring.length < 3) continue;   // the fire station is an OSM node only (no footprint): not a building here
    const H = heightOf(b.kind, b.ring, b.height_m);
    blds.push({ id: b.id, kind: b.kind, name: b.name || null, ring: b.ring, height_m: H.h, height_src: H.src, height_rule: H.rule, hangar: false });
  }
  // the fire station: OSM maps only a node (GNIS import) 45 m west of the AL-5015 FIRE STATION block, where NAIP 2024
  // shows a building with roof solar panels (Phase 1 cross-check section 4 #9); its footprint is read by eye here
  for (const part of FIRE_STATION_NAIP.parts) blds.push({ id: FIRE_STATION_NAIP.id + part.suffix, kind: 'fire_station', name: FIRE_STATION_NAIP.name, ring: part.ring, height_m: part.h, height_src: 'inf', height_rule: FIRE_STATION_NAIP.height_rule, hangar: false, footprint_src: 'inf (by eye on NAIP 2024 at the AL-5015 FIRE STATION block)' });
  const bnx = Math.round((x1 - x0) / bres), bnz = Math.round((z1 - z0) / bres);
  const occ = new Raster(x0, z0, bnx, bnz, bres, Int16Array); occ.a.fill(-1);
  blds.forEach((b, i) => { b.area_m2 = Math.abs(ringArea(b.ring)); b.centroid = centroid(b.ring); occ.fillRings([b.ring], (k) => { occ.a[k] = i; }); });
  const buildingAt = (x, z) => { const k = occ.idx(x, z); if (k < 0 || occ.a[k] < 0) return null; const b = blds[occ.a[k]]; return { id: b.id, kind: b.kind, name: b.name, height_m: b.height_m, height_src: b.height_src }; };
  // ---------------------------------------------------------------- aprons, anchors
  const aprons = A.aprons.map(a => {
    let ax0 = 1e9, ax1 = -1e9, az0 = 1e9, az1 = -1e9; for (const p of a.ring) { ax0 = Math.min(ax0, p[0]); ax1 = Math.max(ax1, p[0]); az0 = Math.min(az0, p[1]); az1 = Math.max(az1, p[1]); }
    return { id: a.id, name: a.name || null, ring: a.ring, bb: [ax0, az0, ax1, az1] };
  });
  const apronAt = (x, z) => { for (const a of aprons) if (x >= a.bb[0] && x <= a.bb[2] && z >= a.bb[1] && z <= a.bb[3] && pointInRing(x, z, a.ring)) return { id: a.id, name: a.name }; return null; };
  const tw = blds.find(b => b.kind === 'control_tower');
  const anchors = { aprons: {}, thresholds: {}, tower: null, windsock: null };
  if (tw) {
    const [cx, cz] = tw.centroid; const y = groundY(cx, cz);
    anchors.tower = { x: cx, z: cz, y, eyeY: y + tw.height_m - TOWER_EYE_BELOW_TOP, top: y + tw.height_m, id: tw.id, src: 'obs footprint (OSM) / inf eye height', eyeRule: `top (OSM 15.85 m) - ${TOWER_EYE_BELOW_TOP} m [inf]` };
  }
  for (const a of aprons) if (a.name) anchors.aprons[a.name] = centroid(a.ring);
  const ws = (A.markers || []).find(m => m.kind === 'windsock'); if (ws) anchors.windsock = [ws.x, ws.z];
  for (const [a, b] of RWY_PAIRS) for (const e of [a, b]) { const p = thrWorld(e); anchors.thresholds[e] = [p[0], p[2]]; const q = endWorld(e); anchors.thresholds[e + '_end'] = [q[0], q[2]]; }
  // ---------------------------------------------------------------- stats
  const counts = new Array(SURFACES.length).fill(0); for (let i = 0; i < surf.a.length; i++) counts[surf.a[i]]++;
  const area = Object.fromEntries(SURFACES.map((k, i) => [k, Math.round(counts[i] * res * res)]));
  const t1 = (typeof performance !== 'undefined' ? performance : Date).now();
  const site = {
    rect, res, bres,
    groundY,
    paved: (x, z) => surf.get(x, z) > 0,
    surface: (x, z) => SURFACES[surf.get(x, z)],
    surfaceCode: (x, z) => surf.get(x, z),
    runwayAt, apronAt,
    building: (x, z) => { const k = occ.idx(x, z); return k >= 0 && occ.a[k] >= 0; },
    buildingAt,
    hangars: blds.filter(b => b.hangar).map(b => ({ id: b.id, letter: b.letter || null, name: b.name, kind: b.kind, role: b.role, ring: b.ring, height_m: b.height_m, height_src: b.height_src, height_rule: b.height_rule })),
    buildings: blds,
    runways: rws.map(r => ({ id: r.id, ends: [r.a, r.b], origin: r.ax.origin, dir: r.ax.dir, right: r.ax.right, length: r.L, halfWidth: r.hw })),
    aprons,
    anchors,
    // raw rasters for renderers / tools that want them (do not mutate)
    rasters: { surface: surf, building: occ },
    stats: { raster: `${nx} x ${nz} @ ${res} m`, buildingRaster: `${bnx} x ${bnz} @ ${bres} m`, area_m2: area, ribbons, buildings: blds.length, ms: Math.round(t1 - t0) },
  };
  return site;
}
