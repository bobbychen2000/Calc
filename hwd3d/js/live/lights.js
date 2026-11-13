// HWD airfield markers and lights that a source places: the lighted windsock and the segmented circle around it, the five
// unlit wind cones, the visual glide slope indicators (VASI 10R / 28L, PAPI 10L / 28R) and the rotating beacon.
// Replaces sfo3d/js/live/lights.js @ a967f9b (SFO ALS structures and taxi-edge positions; fork map 1.3: "static sprites
// only where sourced, e.g. the lighted windsock; fixtures in Phase 4"). Simple solid objects + light sprites; Phase 4 adds
// fixture detail and the full photometry (sfo3d js/env/lighting/airfield.js style).
//
// Placed (each with its source; dimensions are [inf] unless stated):
//   windsock (lit)    OSM node 12658043150 (obs), lighted (NASR WIND_INDCR_FLAG Y-L); 12 ft (3.66 m) sock, 36 in throat
//                     [inf: the FAA L-807 size-2 cone as remembered, AC 150/5345-27 not re-read] on a 5.5 m mast [inf]; it
//                     points downwind and droops with the EnvState sock extension (js/env/state.js wind.sockExt);
//   unlit wind cones  5, at the AL-5015 "Wind Cone, unlit" symbols where NAIP 2024 shows a 1-2 m object (Phase 1 cross-check
//                     docs/phase1_crosscheck.md section 4 #7; the object at each position re-checked here on 0.1 m NAIP
//                     resamplings, docs/phase2_world.md section 5); identity from the chart symbol only; 8 ft sock on a
//                     4.3 m mast [inf: size-1 cone as remembered];
//   segmented circle  NASR SEG_CIRCLE_MKR_FLAG Y + NAIP 2024 (obs); centred on the windsock, 31.5 m across (by eye, inf);
//                     16 red / white segments on a paved disc ~39 m across (counted on NAIP 2024 0.1 m resampling,
//                     +-2 segments / +-1 m, inf); segment size 3.0 x 0.9 x 0.3 m [inf];
//   VASI / PAPI       light-unit positions measured on NAIP 2024 (js/world/fixtures_naip.js, dev/measure_fixtures.py: VASI
//                     red-lens blobs +-0.5 m, PAPI units +-1 m); type, side, glide angle and TCH from NASR / the Chart
//                     Supplement (data runways[].ends[].vgsi). The measured layout confirms the NASR code letters: V4R =
//                     2 bars x 2 boxes right of 10R (35.5 / 248.8 m past the threshold, 700 ft apart), V4L = 2 x 2 left of
//                     28L (91.7 / 244.2 m, 500 ft apart), P4L = 4 units left of 10L (185.4 m) and of 28R (279.3 m). Box
//                     sizes [inf]. Light colour by the viewer's elevation angle: PAPI white above / red below each unit's
//                     aiming angle, GPA +30' / +10' / -10' / -30' from the unit nearest the runway outward (FAA JO 6850.2C
//                     Table 5-2, as verified in sfo3d docs/research/airfield_lighting.md V6; transition js/env/lighting/
//                     photometry.js papiWhite, AC 150/5345-28H 3.2.1); VASI 2-bar: on path the downwind bar shows white and
//                     the upwind bar red (FAA AIM 2-1-2 behaviour, from memory [verify]); the bar transitions are set at
//                     GPA -0.25 deg / +0.25 deg [inf]. Schedule (NASR APT_RMK LGT_SKED / CS): VASI on while the tower is open
//                     and SS-SR when it is closed; PAPI 10L / 28R unavailable when the tower is closed. Intensities [inf].
//   beacon            NASR BCN_LENS_COLOR WG, BCN_LGT_SKED SS-SR; on the tower [inf, data buildings[].beacon]; white /
//                     green alternating flashes, 24 flashes per minute [inf: AC 150/5345-12 range "24 to 30 flashes per
//                     minute" as remembered, not re-read].
//   runway edge lights MIRL 10R/28L and 10L/28R (fix round 1): type obs (NASR / CS), positions INFERRED from the standard
//                     layout (AC 150/5340-30 as remembered, not re-read; a periodic-dot search along all four edges on NAIP
//                     2024 found no 200-ft pattern, so no position is observed) - drawn because an unlit runway at night is
//                     a worse picture than lights at the standard spacing, and the inventory marks them inf.
// NOT placed (no position in any source read; not visible on NAIP 2024 at 0.6 m): REIL 10R / 28L (candidate objects near
// the 28L threshold, not certain), taxiway edge lights or reflectors, the segmented circle's L-shaped traffic-pattern
// indicators (seen on NAIP 2024, shape not measured).
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { m4, v3 } from '../math.js';
import { rwyAxis, thrWorld, FT } from '../geo.js';
import { FIXTURES_NAIP } from '../world/fixtures_naip.js';
import { papiWhite, lampUnits } from '../env/lighting/photometry.js';

export const WINDSOCK = { mastH: 5.5, sockL: 3.66, throatD: 0.91, tipD: 0.46, src: 'inf' };
export const WINDCONE_UNLIT = { mastH: 4.3, sockL: 2.44, throatD: 0.46, tipD: 0.23, src: 'inf' };
// docs/phase1_crosscheck.md section 4 #7 (world x, z; AL-5015 symbol + NAIP 2024 object)
export const UNLIT_CONES = [
  { id: 'cone_10L', near: '10L', x: -410.5, z: -399.0 }, { id: 'cone_10R', near: '10R', x: -412.0, z: -253.7 },
  { id: 'cone_28R', near: '28R', x: 268.5, z: 95.2 }, { id: 'cone_28L', near: '28L', x: 537.5, z: 440.0 },
  { id: 'cone_south', near: 'south of 10R/28L', x: 258.5, z: 280.5 },
];
export const SEG_CIRCLE = { segments: 16, segL: 3.0, segW: 0.9, segH: 0.3, discD: 39, src: 'inf' };
export const BEACON = { fpm: 24, colours: ['W', 'G'], src: 'inf' };
// light units [inf]: VASI box 1.6 m across x 1.0 m deep x 0.6 m on 0.3 m legs (lens height 0.6 m); PAPI unit 1.0 x 0.8 x
// 0.45 m on 0.35 m legs (lens height 0.55 m). NAIP 2024 shows the VASI box tops orange-red and the PAPI units light.
const VASI_BOX = { w: 1.6, d: 1.0, h: 0.6, leg: 0.3, lens: 0.6 }, PAPI_BOX = { w: 1.0, d: 0.8, h: 0.45, leg: 0.35, lens: 0.55 };
// nominal on-axis intensities (cd) [inf: Phase 4 replaces them with the AC 150/5345-28H isocandela of sfo3d photometry]
const VGSI_CD = { day: 12000, night: 2400 };
// tower hours 0700-2100 local (NASR ATC_BASE, PLAN section 1)
export const TOWER_HOURS = [7, 21];
const DEG = Math.PI / 180;
const AV_WHITE = [1.0, 0.94, 0.82], AV_RED = [1.0, 0.08, 0.04];

function coneGeo(D, colours) {
  const s = new Geo(); const n = 5;
  for (let k = 0; k < n; k++) {
    const r0 = (D.throatD + (D.tipD - D.throatD) * k / n) / 2, r1 = (D.throatD + (D.tipD - D.throatD) * (k + 1) / n) / 2;
    const c = colours[k % colours.length];
    // lathe around y, then rotate so the axis is +x
    const R = m4.mul(m4.translate(D.sockL * k / n, 0, 0), m4.rotZ(-Math.PI / 2));
    s.lathe([[r0, 0], [r1, D.sockL / n]], 14, c, [0.9, 0, 0, 0], R, false);
  }
  return s.data();
}

export function buildMarkers(site, airport, { R = null } = {}) {
  const items = [], inventory = [];
  const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  const objItem = (d, extra = {}) => ({ mesh: new Mesh(d), prog: 'obj', model: I4, bbox: d.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 }, ...extra });
  const ws = (airport.markers || []).find(m => m.kind === 'windsock');
  const sc = (airport.markers || []).find(m => m.kind === 'segmented_circle');
  const socks = [];   // {item, base, D}
  const addSock = (x, z, D, colours, what) => {
    const y0 = site.groundY(x, z); const g = new Geo();
    g.cylinder(0.06, D.mastH, 10, [0.75, 0.75, 0.72, 1], [0.5, 0.6, 0, 0], m4.translate(x, y0 - 0.2, z), false);
    g.cylinder(0.25, 0.25, 10, [0.6, 0.6, 0.58, 1], [0.8, 0, 2, 0], m4.translate(x, y0 - 0.1, z), true);   // footing [inf]
    const d = g.data(); items.push(objItem(d, { groundRef: y0 }));
    const sock = coneGeo(D, colours);
    const it = { mesh: new Mesh(sock), prog: 'obj', model: I4.slice(), bbox: [x - D.sockL - 1, y0, z - D.sockL - 1, x + D.sockL + 1, y0 + D.mastH + 1, z + D.sockL + 1], castShadow: true, noCull: true, groundRef: y0, uniforms: { uEmissiveBoost: 1 } };
    items.push(it); socks.push({ item: it, base: [x, y0 + D.mastH - 0.25, z], D, what });
  };
  // international orange / white bands [inf]
  const ORANGE = [0.85, 0.22, 0.04, 1], WHITE = [0.80, 0.80, 0.78, 1];
  if (ws) {
    addSock(ws.x, ws.z, WINDSOCK, [ORANGE, WHITE], 'lit');
    inventory.push({ element: 'windsock (lighted)', at: [ws.x, ws.z], src: 'obs position (OSM, NASR lighted); dimensions inf' });
  }
  for (const c of UNLIT_CONES) addSock(c.x, c.z, WINDCONE_UNLIT, [ORANGE], 'unlit');
  inventory.push({ element: 'unlit wind cones', count: UNLIT_CONES.length, at: UNLIT_CONES.map(c => [c.x, c.z]), src: 'obs position (AL-5015 symbol + NAIP 2024 object, Phase 1 cross-check #7); identity from the chart symbol; dimensions inf' });
  if (sc) {
    const y0 = site.groundY(sc.x, sc.z); const g = new Geo();
    // paved disc (flat, 2 cm above the ground; drawn with a polygon offset)
    const disc = []; const N = 48; for (let i = 0; i < N; i++) { const a = i / N * 2 * Math.PI; disc.push([sc.x + Math.cos(a) * SEG_CIRCLE.discD / 2, sc.z + Math.sin(a) * SEG_CIRCLE.discD / 2]); }
    const dg = new Geo(); const base = dg.nv;
    dg.vert([sc.x, site.groundY(sc.x, sc.z) + 0.02, sc.z], [0, 1, 0], [0.42, 0.41, 0.39, 1], [0.9, 0, 0, 0]);
    for (const p of disc) dg.vert([p[0], site.groundY(p[0], p[1]) + 0.02, p[1]], [0, 1, 0], [0.42, 0.41, 0.39, 1], [0.9, 0, 0, 0]);
    for (let i = 0; i < N; i++) dg.tri(base, base + 1 + ((i + 1) % N), base + 1 + i);
    const dd = dg.data();
    items.push(objItem(dd, { castShadow: false, polyOffset: [-1, -2], groundRef: y0 }));
    const Rr = sc.diameter_m / 2;
    for (let k = 0; k < SEG_CIRCLE.segments; k++) {
      const a = (k + 0.5) / SEG_CIRCLE.segments * 2 * Math.PI; const c = [sc.x + Math.cos(a) * Rr, sc.z + Math.sin(a) * Rr]; const yy = site.groundY(c[0], c[1]);
      const M = m4.mul(m4.translate(c[0], yy, c[1]), m4.rotY(-a));   // local x radial, z tangential
      g.box([-SEG_CIRCLE.segW / 2, 0, -SEG_CIRCLE.segL / 2], [SEG_CIRCLE.segW / 2, SEG_CIRCLE.segH, 0], [0.85, 0.85, 0.83, 1], [0.8, 0, 0, 0], M);
      g.box([-SEG_CIRCLE.segW / 2, 0, 0], [SEG_CIRCLE.segW / 2, SEG_CIRCLE.segH, SEG_CIRCLE.segL / 2], [0.75, 0.12, 0.06, 1], [0.8, 0, 0, 0], M);
    }
    const d = g.data(); items.push(objItem(d, { groundRef: y0 }));
    inventory.push({ element: 'segmented circle', at: [sc.x, sc.z], src: `obs (NASR flag, NAIP); diameter ${sc.diameter_m} m inf; ${SEG_CIRCLE.segments} segments counted by eye (inf)` });
  }
  // ---------------------------------------------------------------- VASI / PAPI (NAIP 2024 positions)
  const ends = {}; for (const r of airport.runways) for (const e of r.ends) ends[e.id] = e;
  const vg = new Geo(); const lights = [];
  const groups = {};
  for (const u of FIXTURES_NAIP.units) (groups[u.group] = groups[u.group] || []).push(u);
  for (const [gid, units] of Object.entries(groups)) {
    const end = units[0].end; const E = ends[end]; const V = E && E.vgsi; if (!V) continue;
    const isPapi = V.type === 'PAPI'; const B = isPapi ? PAPI_BOX : VASI_BOX; const ax = rwyAxis(end);
    const u = ax.dir, back = [-u[0], 0, -u[1]];   // the lens faces the approach (opposite the landing direction)
    // per-unit transition angle (deg): PAPI by rank from the runway (nearest first); VASI by bar (downwind / upwind)
    const sorted = units.slice().sort((a, b) => Math.abs(a.across_m) - Math.abs(b.across_m));
    const isDown = /downwind/.test(gid);
    sorted.forEach((un, rank) => {
      const aim = isPapi ? V.glide_deg + [30, 10, -10, -30][rank] / 60 : V.glide_deg + (isDown ? -0.25 : 0.25);
      const y0 = site.groundY(un.x, un.z);
      // local frame: x along the landing direction, z = right of it (world), y up
      const M = new Float32Array([u[0], 0, u[1], 0, 0, 1, 0, 0, ax.right[0], 0, ax.right[1], 0, un.x, y0, un.z, 1]);
      const col = isPapi ? [0.72, 0.70, 0.62, 1] : [0.78, 0.30, 0.10, 1];
      vg.box([-B.d / 2, B.leg, -B.w / 2], [B.d / 2, B.leg + B.h, B.w / 2], col, [0.7, 0.1, 0, 0], M);
      for (const sz of [-1, 1]) vg.box([-0.04, 0, sz * (B.w / 2 - 0.1) - 0.04], [0.04, B.leg, sz * (B.w / 2 - 0.1) + 0.04], [0.5, 0.5, 0.5, 1], [0.6, 0.5, 0, 0], M);   // legs
      vg.box([-B.d / 2 - 0.01, B.leg + 0.12, -B.w / 2 + 0.12], [-B.d / 2, B.leg + B.h - 0.1, B.w / 2 - 0.12], [0.05, 0.04, 0.04, 1], [0.15, 0, 0, 0], M);   // lens face (toward the approach)
      lights.push({ id: un.id, system: V.code, end, p: [un.x - u[0] * (B.d / 2 + 0.05), y0 + B.leg + B.h / 2, un.z - u[1] * (B.d / 2 + 0.05)], back, aim, papi: isPapi });
    });
    inventory.push({ element: `${isPapi ? 'PAPI' : 'VASI'} ${end} (${V.code}) ${isPapi ? '' : gid.replace(/.*_/, '') + ' bar'}`.trim(), count: units.length,
      at: units.map(q => [q.x, q.z]), along_thr_m: +(units.reduce((s, q) => s + q.along_thr_m, 0) / units.length).toFixed(1), across_m: units.map(q => q.across_m),
      src: `obs position (NAIP 2024, ${FIXTURES_NAIP.made_by}); type / side / angle ${V.glide_deg} deg / TCH ${V.tch_ft} ft obs (NASR, CS); unit size inf` });
  }
  if (vg.nv) { const d = vg.data(); items.push(objItem(d)); }
  // beacon on the tower roof [inf position]
  const tw = site.anchors.tower; let beacon = null;
  if (tw) { beacon = [tw.x, tw.top + 1.0, tw.z]; inventory.push({ element: 'rotating beacon (WG)', at: [tw.x, tw.z], src: 'inf position (on the tower, data buildings[].beacon); colours / schedule obs (NASR)' }); }
  for (const what of ['REIL 10R / 28L', 'taxiway edge lights / reflectors', 'segmented-circle traffic-pattern indicators'])
    inventory.push({ element: what, at: null, src: 'not placed: no position in any source read (not resolvable on NAIP 2024)' });
  // runway edge lights (fix round 1: at night the runways were invisible). MIRL on both runways (NASR RWY_LGT_CODE MED, CS
  // "MIRL") [obs type]; positions [inf]: the standard layout of FAA AC 150/5340-30 as remembered (not re-read) - both edges,
  // 2 ft outside the runway edge, evenly spaced at <= 200 ft from end to end, white (the yellow caution zone of instrument
  // runways and the threshold / end lights are not drawn). Schedule [obs, NASR APT_RMK LGT_SKED]: tower open - on at night
  // (on SS-SR while the tower is open [inf]); tower closed - 10R/28L preset low intensity (pilot-controlled, CTAF), 10L/28R
  // closed (off). Intensity 200 cd medium / 50 cd preset low [inf].
  const edge = [];
  for (const R0 of airport.runways || []) {
    const S0 = (site.runways || []).find(q => q.id === R0.id); if (!S0 || !R0.edge_lights) continue;
    const n = Math.ceil(S0.length / (200 * FT)), off = S0.halfWidth + 2 * FT;
    for (let k = 0; k <= n; k++) { const al = S0.length * k / n;
      for (const sd of [-1, 1]) { const x = S0.origin[0] + S0.dir[0] * al + S0.right[0] * off * sd, z = S0.origin[1] + S0.dir[1] * al + S0.right[1] * off * sd;
        edge.push({ p: [x, site.groundY(x, z) + 0.35, z], rwy: R0.id, closedWhenTwrClosed: !!R0.closed_when_tower_closed }); } }
    inventory.push({ element: `runway edge lights ${R0.id} (${R0.edge_lights.type})`, count: (n + 1) * 2, at: null, spacing_m: +(S0.length / n).toFixed(1),
      src: `type obs (NASR / CS); positions inf (AC 150/5340-30 standard layout as remembered: <= 200 ft spacing, 2 ft outside the edge)` });
  }
  // ---------------------------------------------------------------- dynamic parts
  const state = { fromDeg: 290, speed: 4, ext: 0.6 };
  function setWind(fromDeg, speedMs, ext) {
    state.fromDeg = fromDeg == null ? state.fromDeg : fromDeg; state.speed = speedMs || 0; state.ext = ext == null ? Math.min(1, state.speed / 7.7) : ext;
    const to = (state.fromDeg + 180) * DEG; const dir = [Math.sin(to), 0, -Math.cos(to)];
    const droop = (1 - Math.max(0, Math.min(1, state.ext))) * 75 * DEG;   // limp sock hangs down [inf]
    const fwd = v3.norm([dir[0] * Math.cos(droop), -Math.sin(droop), dir[2] * Math.cos(droop)]);
    const side = v3.norm(v3.cross(fwd, [0, 1, 0])); const up = v3.cross(side, fwd);
    for (const s of socks) s.item.model = new Float32Array([fwd[0], fwd[1], fwd[2], 0, up[0], up[1], up[2], 0, side[0], side[1], side[2], 0, s.base[0], s.base[1], s.base[2], 1]);
  }
  setWind(null, 4, 0.6);
  // light sprites. env = {sunEl, nightW (ASOS photocell weight 0 day .. 1 night), towerOpen, sigma (surface extinction 1/m)}
  function sprites(t, env = {}) {
    const out = []; const sunEl = env.sunEl ?? 30, night = sunEl < 0;
    const cam = R && R.curCam ? R.curCam.pos : null;
    if (beacon && night) {
      const period = 60 / BEACON.fpm; const ph = (t / 1000) / period; const k = Math.floor(ph); const f = ph - k;
      const on = Math.max(0, 1 - Math.abs(f - 0.5) / 0.12);   // ~0.25 s pulse per flash [inf]
      if (on > 0) out.push({ p: beacon, c: k % 2 ? [0.1, 1.0, 0.45] : [1, 0.97, 0.9], i: 40 * on, s: 0.8 });
    }
    if (night && socks.length && socks[0].what === 'lit') { const b = socks[0].base; out.push({ p: [b[0], b[1] + 0.6, b[2]], c: [1, 0.95, 0.85], i: 3, s: 0.5 }); }
    if (night && edge.length && cam) {
      const open = env.towerOpen !== false, sig = env.sigma ?? 3.3e-5;
      for (const L of edge) {
        if (!open && L.closedWhenTwrClosed) continue;
        const cd = open ? 200 : 50; const d = Math.hypot(cam[0] - L.p[0], cam[1] - L.p[1], cam[2] - L.p[2]) || 1;
        out.push({ p: L.p, c: [1.0, 0.93, 0.78], i: lampUnits(cd * Math.exp(-sig * d), 0.25), s: 0.25, phys: true });
      }
    }
    if (cam) {
      const open = env.towerOpen !== false;
      const w = env.nightW ?? (night ? 1 : 0); const cd = VGSI_CD.night + (VGSI_CD.day - VGSI_CD.night) * (1 - w);
      const sig = env.sigma ?? 3.3e-5;
      for (const L of lights) {
        const on = L.papi ? open : (open || night);
        if (!on) continue;
        const dx = cam[0] - L.p[0], dy = cam[1] - L.p[1], dz = cam[2] - L.p[2]; const d = Math.hypot(dx, dy, dz) || 1;
        const along = dx * L.back[0] + dz * L.back[2]; if (along <= 1) continue;               // behind the unit: no beam
        const el = Math.atan2(dy, along) / DEG, dh = Math.atan2(Math.abs(dx * L.back[2] - dz * L.back[0]), along) / DEG;
        if (dh > 15) continue;                                                                   // outside the beam [inf +-15 deg]
        // vertical cut-off (fix round 1: seen from steeply above at midday a PAPI showed as white glare discs). PAPI: the
        // outermost isocandela contour of AC 150/5345-28H Fig 3-1 spans +-4 deg about the beam axis (sfo3d
        // tools/env/lighting_spec.json PAPI_LHA, as read there) - no beam beyond it; VASI: the same about the
        // aiming angle, +6 deg upward [inf, the L-880 vertical spread not read]
        const dv = el - L.aim; if (dv > (L.papi ? 4 : 6) || dv < -4) continue;
        const vf = Math.max(0, 1 - Math.max(0, Math.abs(dv) - 2) / 3);                            // fade over the outer 2 deg [inf]
        const wf = papiWhite(L.aim, el, dh);
        const c = [AV_RED[0] + (AV_WHITE[0] - AV_RED[0]) * wf, AV_RED[1] + (AV_WHITE[1] - AV_RED[1]) * wf, AV_RED[2] + (AV_WHITE[2] - AV_RED[2]) * wf];
        const I = cd * (0.15 + 0.85 * wf) * Math.exp(-sig * d) * Math.max(0, 1 - dh / 15) * vf;     // red filter ~15 % [inf]
        const s = 0.35;
        // display gain by day: 8 ^ (1 - ASOS night weight) [inf, tuned by eye on out/phase2/lights_*.png; the aircraft lights
        // use DAY_GAIN 30 (js/env/aircraft_lights.js), which made a white PAPI unit a glare disc at 1.5 km]
        out.push({ p: L.p, c, i: lampUnits(I, s) * Math.pow(8, 1 - w), s, phys: true });
      }
    }
    return out;
  }
  return { items, inventory, setWind, sprites, windState: state, vgsi: lights, edgeLights: edge };
}

/** Tower open (0700-2100 local, NASR ATC_BASE) at epoch ms, local time from Intl (America/Los_Angeles, DST-correct). */
export function towerOpenAt(ms) {
  if (!(ms > 0)) return true;
  try {
    const h = +new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', hour12: false }).format(new Date(ms)) % 24;
    return h >= TOWER_HOURS[0] && h < TOWER_HOURS[1];
  } catch (e) { return true; }
}
