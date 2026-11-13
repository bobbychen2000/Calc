// HWD airfield markers and lights that the data places: the lighted windsock, the segmented circle around it, and the
// rotating beacon (on the tower). Replaces sfo3d/js/live/lights.js @ a967f9b (SFO ALS structures and taxi-edge
// positions; fork map 1.3: "static sprites only where sourced, e.g. the lighted windsock; fixtures in Phase 4").
//
// Placed (data/hwd_airport.json):
//   windsock          OSM node 12658043150 (obs), lighted (NASR WIND_INDCR_FLAG Y-L); dimensions [inf]: 12 ft (3.66 m)
//                     sock, 36 in throat - the size-2 windcone of FAA AC 150/5345-27 as remembered, not re-read
//                     [unverified] - on a 5.5 m mast [inf]; it points downwind and droops with the EnvState sock
//                     extension (js/env/state.js wind.sockExt);
//   segmented circle  NASR SEG_CIRCLE_MKR_FLAG Y + NAIP 2024 (obs); centred on the windsock, 31.5 m across (by eye, inf);
//                     16 red / white segments on a paved disc ~39 m across (counted and read by eye on a 0.1 m NAIP
//                     2024 resampling, +-2 segments / +-1 m, inf); segment size 3.0 x 0.9 x 0.3 m [inf];
//   beacon            NASR BCN_LENS_COLOR WG, BCN_LGT_SKED SS-SR; on the tower [inf, data buildings[].beacon]; white /
//                     green alternating flashes, 12 rpm per lens pair = 24 flashes per minute [inf: AC 150/5345-12
//                     range "24 to 30 flashes per minute" as remembered, not re-read].
// NOT placed (no position in any source read; data not_yet_sourced): runway edge lights (MIRL 10R/28L and 10L/28R),
// VASI V4R 10R / V4L 28L, PAPI P4L 10L and 28R, REIL 10R / 28L, taxiway edge lights or reflectors, the five unlit wind
// cones of AL-5015, the segmented circle's L-shaped traffic-pattern indicators (seen on NAIP 2024, shape not read).
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { m4, v3 } from '../math.js';

export const WINDSOCK = { mastH: 5.5, sockL: 3.66, throatD: 0.91, tipD: 0.46, src: 'inf' };
export const SEG_CIRCLE = { segments: 16, segL: 3.0, segW: 0.9, segH: 0.3, discD: 39, src: 'inf' };
export const BEACON = { fpm: 24, colours: ['W', 'G'], src: 'inf' };

export function buildMarkers(site, airport) {
  const items = [], inventory = [];
  const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  const ws = (airport.markers || []).find(m => m.kind === 'windsock');
  const sc = (airport.markers || []).find(m => m.kind === 'segmented_circle');
  let sock = null, sockBase = null;
  if (ws) {
    const y0 = site.groundY(ws.x, ws.z);
    const g = new Geo();
    g.cylinder(0.06, WINDSOCK.mastH, 10, [0.75, 0.75, 0.72, 1], [0.5, 0.6, 0, 0], m4.translate(ws.x, y0 - 0.2, ws.z), false);
    g.cylinder(0.25, 0.25, 10, [0.6, 0.6, 0.58, 1], [0.8, 0, 2, 0], m4.translate(ws.x, y0 - 0.1, ws.z), true);   // footing [inf]
    const d = g.data();
    items.push({ mesh: new Mesh(d), prog: 'obj', model: I4, bbox: d.bbox, castShadow: true, groundRef: y0, uniforms: { uEmissiveBoost: 1 } });
    // sock: a truncated cone along local +x from the pivot, 5 orange / white bands (international orange; [inf])
    const s = new Geo(); const n = 5;
    for (let k = 0; k < n; k++) {
      const r0 = (WINDSOCK.throatD + (WINDSOCK.tipD - WINDSOCK.throatD) * k / n) / 2, r1 = (WINDSOCK.throatD + (WINDSOCK.tipD - WINDSOCK.throatD) * (k + 1) / n) / 2;
      const c = k % 2 ? [0.80, 0.80, 0.78, 1] : [0.85, 0.22, 0.04, 1];
      // lathe around y, then rotate so the axis is +x
      const R = m4.mul(m4.translate(WINDSOCK.sockL * k / n, 0, 0), m4.rotZ(-Math.PI / 2));
      s.lathe([[r0, 0], [r1, WINDSOCK.sockL / n]], 14, c, [0.9, 0, 0, 0], R, false);
    }
    sock = s.data(); sockBase = [ws.x, y0 + WINDSOCK.mastH - 0.25, ws.z];
    const it = { mesh: new Mesh(sock), prog: 'obj', model: I4.slice(), bbox: [ws.x - 5, y0, ws.z - 5, ws.x + 5, y0 + 7, ws.z + 5], castShadow: true, noCull: true, groundRef: y0, uniforms: { uEmissiveBoost: 1 } };
    items.push(it); sock.item = it;
    inventory.push({ element: 'windsock (lighted)', at: [ws.x, ws.z], src: 'obs position (OSM, NASR lighted); dimensions inf' });
  }
  if (sc) {
    const y0 = site.groundY(sc.x, sc.z); const g = new Geo();
    // paved disc (flat, 2 cm above the ground; drawn with a polygon offset)
    const disc = []; const N = 48; for (let i = 0; i < N; i++) { const a = i / N * 2 * Math.PI; disc.push([sc.x + Math.cos(a) * SEG_CIRCLE.discD / 2, sc.z + Math.sin(a) * SEG_CIRCLE.discD / 2]); }
    const dg = new Geo(); const base = dg.nv;
    dg.vert([sc.x, site.groundY(sc.x, sc.z) + 0.02, sc.z], [0, 1, 0], [0.42, 0.41, 0.39, 1], [0.9, 0, 0, 0]);
    for (const p of disc) dg.vert([p[0], site.groundY(p[0], p[1]) + 0.02, p[1]], [0, 1, 0], [0.42, 0.41, 0.39, 1], [0.9, 0, 0, 0]);
    for (let i = 0; i < N; i++) dg.tri(base, base + 1 + ((i + 1) % N), base + 1 + i);
    const dd = dg.data();
    items.push({ mesh: new Mesh(dd), prog: 'obj', model: I4, bbox: dd.bbox, castShadow: false, polyOffset: [-1, -2], groundRef: y0, uniforms: { uEmissiveBoost: 1 } });
    const R = sc.diameter_m / 2;
    for (let k = 0; k < SEG_CIRCLE.segments; k++) {
      const a = (k + 0.5) / SEG_CIRCLE.segments * 2 * Math.PI; const c = [sc.x + Math.cos(a) * R, sc.z + Math.sin(a) * R]; const yy = site.groundY(c[0], c[1]);
      const M = m4.mul(m4.translate(c[0], yy, c[1]), m4.rotY(-a));   // local x radial, z tangential
      g.box([-SEG_CIRCLE.segW / 2, 0, -SEG_CIRCLE.segL / 2], [SEG_CIRCLE.segW / 2, SEG_CIRCLE.segH, 0], [0.85, 0.85, 0.83, 1], [0.8, 0, 0, 0], M);
      g.box([-SEG_CIRCLE.segW / 2, 0, 0], [SEG_CIRCLE.segW / 2, SEG_CIRCLE.segH, SEG_CIRCLE.segL / 2], [0.75, 0.12, 0.06, 1], [0.8, 0, 0, 0], M);
    }
    const d = g.data();
    items.push({ mesh: new Mesh(d), prog: 'obj', model: I4, bbox: d.bbox, castShadow: true, groundRef: y0, uniforms: { uEmissiveBoost: 1 } });
    inventory.push({ element: 'segmented circle', at: [sc.x, sc.z], src: `obs (NASR flag, NAIP); diameter ${sc.diameter_m} m inf; ${SEG_CIRCLE.segments} segments counted by eye (inf)` });
  }
  // beacon on the tower roof [inf position]
  const tw = site.anchors.tower; let beacon = null;
  if (tw) { beacon = [tw.x, tw.top + 1.0, tw.z]; inventory.push({ element: 'rotating beacon (WG)', at: [tw.x, tw.z], src: 'inf position (on the tower, data buildings[].beacon); colours / schedule obs (NASR)' }); }
  for (const what of ['runway edge lights (MIRL)', 'VASI 10R (V4R) / 28L (V4L)', 'PAPI 10L / 28R (P4L)', 'REIL 10R / 28L', 'taxiway edge lights / reflectors', 'five unlit wind cones (AL-5015)', 'segmented-circle traffic-pattern indicators'])
    inventory.push({ element: what, at: null, src: 'not placed: no position in the data (not_yet_sourced)' });
  // ---- dynamic parts
  const state = { fromDeg: 290, speed: 4, ext: 0.6 };
  function setWind(fromDeg, speedMs, ext) {
    if (!sock) return;
    state.fromDeg = fromDeg == null ? state.fromDeg : fromDeg; state.speed = speedMs || 0; state.ext = ext == null ? Math.min(1, state.speed / 7.7) : ext;
    const to = (state.fromDeg + 180) * Math.PI / 180; const dir = [Math.sin(to), 0, -Math.cos(to)];
    const droop = (1 - Math.max(0, Math.min(1, state.ext))) * 75 * Math.PI / 180;   // limp sock hangs down [inf]
    const fwd = v3.norm([dir[0] * Math.cos(droop), -Math.sin(droop), dir[2] * Math.cos(droop)]);
    const side = v3.norm(v3.cross(fwd, [0, 1, 0])); const up = v3.cross(side, fwd);
    const M = new Float32Array([fwd[0], fwd[1], fwd[2], 0, up[0], up[1], up[2], 0, side[0], side[1], side[2], 0, sockBase[0], sockBase[1], sockBase[2], 1]);
    sock.item.model = M;
  }
  setWind(null, 4, 0.6);
  // light sprites: beacon flashes and the windsock flood light, only between sunset and sunrise (world.sunEl < 0)
  function sprites(t, sunEl) {
    const out = []; if (sunEl == null || sunEl > 0) return out;
    if (beacon) {
      const period = 60 / BEACON.fpm; const ph = (t / 1000) / period; const k = Math.floor(ph); const f = ph - k;
      const on = Math.max(0, 1 - Math.abs(f - 0.5) / 0.12);   // ~0.25 s pulse per flash [inf]
      if (on > 0) out.push({ p: beacon, c: k % 2 ? [0.1, 1.0, 0.45] : [1, 0.97, 0.9], i: 40 * on, s: 0.8 });
    }
    if (sockBase) out.push({ p: [sockBase[0], sockBase[1] + 0.6, sockBase[2]], c: [1, 0.95, 0.85], i: 3, s: 0.5 });
    return out;
  }
  return { items, inventory, setWind, sprites, windState: state };
}
