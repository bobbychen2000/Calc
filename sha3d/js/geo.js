// Geographic reference for Shanghai Hongqiao (ZSSS / SHA). Replaces sfo3d@e3218d6 js/geo.js (pattern only: no SFO
// constant is kept). JS twin of tools/common/frame.py, constant for constant; tools/common/test_geo_js.mjs checks this
// module against frame.py (grid of points, both directions, heights) and against the coordinates in data/sha_airport.json.
//
// World frame 'ltp-wgs84-zsss' (data/sha_airport.json `frame`, owner decision OD0):
// - x = east (m), y = up (m), z = south (m). Origin = centre of RWY 18L/36R = arithmetic mean of the two end nodes of OSM
//   way 16714125 (31.2131135 N 121.3354641 E and 31.1825842 N 121.3371157 E) = 31.19784885 N, 121.3362899 E (the AIP ARP
//   definition; the AIP's own printed ARP is only to 0.1').
// - Datum WGS 84 for every input (OSM, Sentinel-2, Umbra, ADS-B): no datum shift (sfo3d's NAD83 shift is gone).
// - Projection: exact local tangent plane on the WGS 84 ellipsoid at the origin, h = 0 (lat/lon -> ECEF -> east/north).
//   Flat world: y is height above the ground point. Plane vs geodesic distance < 0.5 mm within 5 km.
// - Headings are DEGREES TRUE at every module boundary: hdgVec(h) = [sin h, -cos h] with h in degrees (sfo3d's took
//   radians; arch.md R6). Radians only inside a module.
// - Heights: y = metres in the AIP height datum (AIP mirror; datum not stated, Wusong inferred). FIELD_ELEV_Y 3.0 (AD
//   ELEV), GROUND_Y 2.5 = NOMINAL flat ground (mean of the 8 AIP THR / DTHR elevations, 2.49 m [inf]). Ellipsoidal
//   (GNSS / ADS-B alt_geom) height h = y - K_DEM + N(x, z) (EGM2008 plane fit). sfo3d's GROUND_Y 3 and GEOID_M 32.29 are
//   gone.
// Runway helpers come from the injected airport data (initGeo(window.SHA_AIRPORT)): the module itself holds no airport
// geometry, so it runs unchanged in Node.

export const FRAME_ID = 'ltp-wgs84-zsss';
export const ORIGIN = { lat: 31.19784885, lon: 121.3362899 };   // OD0 (header)
export const ARP = ORIGIN;   // (name kept for code that asks for the ARP: the frame origin IS the AIP ARP definition)
const WGS84_A = 6378137.0, WGS84_F = 1 / 298.257223563, E2 = WGS84_F * (2 - WGS84_F), D2R = Math.PI / 180;
// vertical chain (tools/common/frame.py header; data/sha_airport.json frame)
export const FIELD_ELEV_Y = 3.0;        // AIP (mirror) AD 2.2 AD ELEV
export const GROUND_Y = 2.5;            // nominal flat ground [inf] (frame.ground_y_nominal)
export const K_DEM = 1.30;              // y - H_EGM2008 (Copernicus GLO-30) at the 8 AIP runway points [obs, +-2 m]
export const GEOID_N0 = 11.267, GEOID_DN_DX = 4.184e-5, GEOID_DN_DZ = 8.77e-6;   // EGM2008 N(x, z) plane fit (NGA grid)

function ecef(lat, lon, h = 0) {
  const sl = Math.sin(lat * D2R), cl = Math.cos(lat * D2R);
  const N = WGS84_A / Math.sqrt(1 - E2 * sl * sl);
  return [(N + h) * cl * Math.cos(lon * D2R), (N + h) * cl * Math.sin(lon * D2R), (N * (1 - E2) + h) * sl];
}
const O = ecef(ORIGIN.lat, ORIGIN.lon);
const S0 = Math.sin(ORIGIN.lat * D2R), C0 = Math.cos(ORIGIN.lat * D2R), SL = Math.sin(ORIGIN.lon * D2R), CL = Math.cos(ORIGIN.lon * D2R);
const W0 = Math.sqrt(1 - E2 * S0 * S0);
export const M_PER_DEG_LAT = WGS84_A * (1 - E2) / (W0 * W0 * W0) * D2R;   // 110872.871 m (meridian radius at the origin)
export const M_PER_DEG_LON = WGS84_A / W0 * C0 * D2R;                     // 95306.513 m

/** WGS 84 lat/lon (deg) -> [east, north] m in the tangent plane at the origin. */
export function llToEN(lat, lon) {
  const p = ecef(lat, lon), dx = p[0] - O[0], dy = p[1] - O[1], dz = p[2] - O[2];
  return [-SL * dx + CL * dy, -S0 * CL * dx - S0 * SL * dy + C0 * dz];
}
/** Inverse (point on the ellipsoid): fixed-Jacobian Newton, < 1e-8 m. */
export function enToLL(e, n) {
  let lat = ORIGIN.lat + n / M_PER_DEG_LAT, lon = ORIGIN.lon + e / M_PER_DEG_LON;
  for (let i = 0; i < 12; i++) {
    const q = llToEN(lat, lon), de = e - q[0], dn = n - q[1];
    lat += dn / M_PER_DEG_LAT; lon += de / M_PER_DEG_LON;
    if (Math.abs(de) + Math.abs(dn) < 1e-10) break;
  }
  return [lat, lon];
}
/** WGS 84 lat/lon -> world [x, z] (metres). The one entry point for OSM, ADS-B, GNSS, Sentinel-2. */
export function wgs84ToWorld(lat, lon) { const [e, n] = llToEN(lat, lon); return [e, -n]; }
/** world (x, z) -> WGS 84 [lat, lon]. */
export function worldToWgs84(x, z) { return enToLL(x, -z); }
export const llToWorld = wgs84ToWorld, worldToLL = worldToWgs84;

// ------------------------------------------------------------------------------------------------ headings (degrees)
/** world (x, z) unit vector of a true heading in DEGREES: [sin h, -cos h]. */
export function hdgVec(hDeg) { return [Math.sin(hDeg * D2R), -Math.cos(hDeg * D2R)]; }
/** true heading (deg, 0..360) of a world (x, z) direction. */
export function vecHdg(dx, dz) { return ((Math.atan2(dx, -dz) / D2R) % 360 + 360) % 360; }

// ------------------------------------------------------------------------------------------------ heights
/** EGM2008 geoid undulation N (m) at world (x, z). */
export const geoidN = (x = 0, z = 0) => GEOID_N0 + GEOID_DN_DX * x + GEOID_DN_DZ * z;
/** world y -> WGS 84 ellipsoidal height (ADS-B alt_geom, GNSS). */
export const haeFromY = (y, x = 0, z = 0) => y - K_DEM + geoidN(x, z);
export const yFromHae = (h, x = 0, z = 0) => h + K_DEM - geoidN(x, z);
export const yFromEgm2008 = (H) => H + K_DEM;
/** ADS-B alt_baro (pressure altitude, ft) -> world y (m) with a QNH (hPa), ISA troposphere (frame.py y_from_pressure_alt). */
export function yFromPressureAlt(altFt, qnhHpa) {
  const hp = altFt * 0.3048; const p = 1013.25 * Math.pow(1 - hp / 44330.77, 5.25588);
  return 44330.77 * (1 - Math.pow(p / qnhHpa, 1 / 5.25588));
}
/** Ground height at world (x, z). Phase 2: the flat nominal ground everywhere (no terrain model; the runway profiles
 *  differ by <= 0.5 m, rwyProfileY). The terrain / site package may replace it via setGroundModel(fn). */
let groundModel = null;
export function groundY(x, z) { return groundModel ? groundModel(x, z) : GROUND_Y; }
export function setGroundModel(fn) { groundModel = typeof fn === 'function' ? fn : null; }

/** Check a data file's frame block against these constants. Returns {ok, diffs[]}. */
export function checkFrame(F) {
  const diffs = [];
  if (!F) return { ok: false, diffs: ['no frame block'] };
  const near = (a, b, tol, what) => { if (a == null || Math.abs(a - b) > tol) diffs.push(`${what}: data ${a} vs geo.js ${b}`); };
  if (F.id !== FRAME_ID) diffs.push(`id: data ${F.id} vs geo.js ${FRAME_ID}`);
  near(F.origin_wgs84 && F.origin_wgs84[0], ORIGIN.lat, 1e-9, 'origin lat'); near(F.origin_wgs84 && F.origin_wgs84[1], ORIGIN.lon, 1e-9, 'origin lon');
  near(F.ellipsoid && F.ellipsoid.a, WGS84_A, 1e-6, 'ellipsoid a'); near(F.ellipsoid && F.ellipsoid.inv_f, 1 / WGS84_F, 1e-6, 'ellipsoid 1/f');
  near(F.m_per_deg_lat, M_PER_DEG_LAT, 1e-3, 'm per deg lat'); near(F.m_per_deg_lon, M_PER_DEG_LON, 1e-3, 'm per deg lon');
  near(F.field_elev_y, FIELD_ELEV_Y, 1e-9, 'field_elev_y'); near(F.ground_y_nominal, GROUND_Y, 1e-9, 'ground_y_nominal');
  near(F.k_dem_m, K_DEM, 1e-9, 'k_dem');
  const G = F.geoid_egm2008 || {}; near(G.n0_m, GEOID_N0, 1e-9, 'geoid n0'); near(G.dn_dx, GEOID_DN_DX, 1e-12, 'geoid dn_dx'); near(G.dn_dz, GEOID_DN_DZ, 1e-12, 'geoid dn_dz');
  return { ok: diffs.length === 0, diffs };
}

// ------------------------------------------------------------------------------------------------ runways (from data)
// Filled by initGeo(airport). RUNWAYS[i] = { id '18L/36R', ends ['18L', '36R'], hdg (deg, first end's direction),
//   dir [x, z] (unit, from the first end's runway end towards the second), a / b (physical runway ends = start of the
//   pavement, [x, z]), len, width, shoulder, blastPad [m, m], segments [[s0, s1, 'CONC'|'ASPH']] (s from a),
//   profile [[s, y]], centreline, outline, src }.
// RUNWAY_ENDS['18L'] = { id, rw (runway), hdg (landing / take-off direction, deg), end [x, z] (runway end), thr [x, z]
//   (landing threshold: displaced threshold where there is one), thrS (s of thr from rw.a), dthrM, endOfTora, papi, als,
//   elev {thr, dthr}, declared, src }.
export const RUNWAYS = [];
export const RUNWAY_ENDS = {};
let airportRef = null;
export function initGeo(airport) {
  airportRef = airport || null;
  RUNWAYS.length = 0; for (const k of Object.keys(RUNWAY_ENDS)) delete RUNWAY_ENDS[k];
  const chk = airport ? checkFrame(airport.frame) : { ok: false, diffs: ['no airport data'] };
  if (!chk.ok && typeof console !== 'undefined') console.warn('[geo] frame block differs from js/geo.js:', chk.diffs);
  for (const r of (airport && airport.runways) || []) {
    const f = r.aip_facts || {}; const E = r.ends || [];
    const a = E[0] && E[0].end ? E[0].end.xz : r.centreline.pts[0], b = E[1] && E[1].end ? E[1].end.xz : r.centreline.pts[r.centreline.pts.length - 1];
    const dx = b[0] - a[0], dz = b[1] - a[1], len = Math.hypot(dx, dz);
    const R = { id: r.id, ends: E.map(e => e.id), hdg: r.heading_true_deg, dir: [dx / len, dz / len], a: a.slice(), b: b.slice(), len,
      width: f.width_m || null, shoulder: f.shoulder_m || 0, blastPad: f.blast_pad_m || [0, 0], segments: f.surface_segments_m || [],
      profile: (r.profile_y && r.profile_y.points_s_y) || [], profileS0: E[0] && E[0].end ? E[0].end.s_m : 0,
      centreline: r.centreline, outline: r.outline, shoulders: r.shoulders, blastPads: r.blast_pads || [], src: r.src, refs: r.refs };
    RUNWAYS.push(R);
    for (const e of E) {
      const fe = (f.ends || {})[e.id] || {};
      const thr = e.dthr ? e.dthr.xz : e.end.xz;
      const s0 = alongOf(R, thr[0], thr[1]);
      RUNWAY_ENDS[e.id] = { id: e.id, rw: R, hdg: e.heading_true_deg, end: e.end.xz.slice(), thr: thr.slice(), thrS: s0,
        dthrM: fe.thr_displaced_m || 0, endDisplacedM: fe.end_displaced_m || 0, endOfTora: e.end_of_tora ? e.end_of_tora.xz.slice() : null,
        papi: e.papi || null, als: e.approach_lights || null, elev: fe.elev_m || null, declared: fe.declared_m || null, src: e.dthr ? e.dthr.src : e.end.src };
    }
  }
  // the env stack's runway headings (js/env/state.js; HUD headwind components)
  if (setRwyHdgHook) setRwyHdgHook(Object.fromEntries(Object.values(RUNWAY_ENDS).map(e => [e.id, e.hdg])));
  return { ok: chk.ok, diffs: chk.diffs, runways: RUNWAYS, ends: RUNWAY_ENDS };
}
let setRwyHdgHook = null;
/** js/live/app.js connects js/env/state.js setRunwayHeadings here (geo.js does not import the env stack). */
export function onRunwayHeadings(fn) { setRwyHdgHook = fn; if (fn && Object.keys(RUNWAY_ENDS).length) fn(Object.fromEntries(Object.values(RUNWAY_ENDS).map(e => [e.id, e.hdg]))); }
export const airportData = () => airportRef;
function alongOf(R, x, z) { return (x - R.a[0]) * R.dir[0] + (z - R.a[1]) * R.dir[1]; }
export const runwayById = (id) => RUNWAYS.find(r => r.id === id) || null;
export const runwayEnd = (id) => RUNWAY_ENDS[id] || null;
/** [s along the runway from its first end's pavement start, t across (+ = to the right of the s direction)] */
export function rwyAlongAcross(R, x, z) { const px = x - R.a[0], pz = z - R.a[1]; return [px * R.dir[0] + pz * R.dir[1], -px * R.dir[1] + pz * R.dir[0]]; }
/** inverse of rwyAlongAcross -> world [x, z] */
export function rwyToWorld(R, s, t = 0) { return [R.a[0] + R.dir[0] * s - R.dir[1] * t, R.a[1] + R.dir[1] * s + R.dir[0] * t]; }
/** runway surface height at s (linear in the AIP (mirror) THR / DTHR elevations, data runways[].profile_y [inf]) */
export function rwyProfileY(R, s) {
  const P = R.profile; if (!P || !P.length) return GROUND_Y;
  const q = s + (R.profileS0 || 0);   // profile s is measured from the OSM north end node
  if (q <= P[0][0]) return P[0][1]; for (let i = 1; i < P.length; i++) if (q <= P[i][0]) { const k = (q - P[i - 1][0]) / (P[i][0] - P[i - 1][0]); return P[i - 1][1] + k * (P[i][1] - P[i - 1][1]); }
  return P[P.length - 1][1];
}
/** surface type at s along the runway: 'CONC' | 'ASPH' | null (AIP (mirror) AD 2.12 surface sections) */
export function rwySurfaceAt(R, s) { for (const [s0, s1, t] of R.segments) if (s >= s0 && s <= s1) return t; return null; }
/** the runway (and s, t) whose pavement contains (x, z), or null */
export function runwayAt(x, z, margin = 0) {
  for (const R of RUNWAYS) { const [s, t] = rwyAlongAcross(R, x, z); if (s >= -margin && s <= R.len + margin && Math.abs(t) <= (R.width || 45) / 2 + margin) return { rw: R, s, t }; }
  return null;
}
