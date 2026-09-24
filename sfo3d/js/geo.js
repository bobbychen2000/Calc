// Geographic reference for KSFO. Python twin: tools/geo_frame.py (keep identical; tools/test_geo_frame.py checks
// 50 points to 1 mm, both directions, plus the WGS 84 functions).
//
// World frame 'ltp-nad83-2011' (since 24 Sep 2026): x = east (m), y = up (m), z = south (m), origin = ARP.
// - Datum NAD83(2011): the datum of the FAA NASR coordinates ("All US coordinate information provided currently
//   references NAD 83", NASR CSV_README, cycle 2026-09-03), of USDA NAIP (EPSG:26910) and of the SFO Museum geometry.
// - Projection: exact local tangent plane (ENU) on the GRS80 ellipsoid at the ARP, at ellipsoidal height 0
//   (lat/lon -> ECEF -> east/north at the ARP). Flat world: y is height above the ground point, so the horizontal
//   position never depends on h. Distances equal geodesic ones to < 0.1 mm within 5 km (0.5 m at 50 km).
//   Replaces the spherical equirectangular formula (111320*cos(lat0) m/deg lon), which was 0.124 % short east-west
//   (docs/research/imagery.md s.4). Data made in that legacy frame were migrated by tools/geo_frame.py legacy_to_world.
// - ARP: FAA NASR APT_BASE (cycle 2026-09-03) 37-37-07.7000N 122-22-31.5000W, rounded to 1e-7 deg (< 0.5 mm).
// - WGS 84 inputs (ADS-B, OSM, GNSS) go through wgs84ToWorld: NAD83(2011) -> WGS 84 (G2296)/ITRF2020 at SFO, epoch
//   2026.73, moves a fixed ground point by dE -1.568 m, dN +0.159 m (pyproj 3.7.2 / PROJ 9.5.1, EPSG "ITRF2020 to
//   NAD83(2011) (1)" time-dependent Helmert; rate -1.4 cm/yr E, -1.3 cm/yr N; < 1.1 cm spatial variation within
//   50 km). Intraplate Bay Area motion since 2010.0 is not modelled [unverified, est. 0.2-0.4 m].
export const ARP = { lat: 37.6188056, lon: -122.3754167 };
export const FRAME_ID = 'ltp-nad83-2011';
const GRS80_A = 6378137.0, GRS80_F = 1 / 298.257222101, E2 = GRS80_F * (2 - GRS80_F), D2R = Math.PI / 180;
function ecef(lat, lon) {
  const sl = Math.sin(lat * D2R), cl = Math.cos(lat * D2R);
  const N = GRS80_A / Math.sqrt(1 - E2 * sl * sl);
  return [N * cl * Math.cos(lon * D2R), N * cl * Math.sin(lon * D2R), N * (1 - E2) * sl];
}
const O = ecef(ARP.lat, ARP.lon);
const S0 = Math.sin(ARP.lat * D2R), C0 = Math.cos(ARP.lat * D2R), SL = Math.sin(ARP.lon * D2R), CL = Math.cos(ARP.lon * D2R);
const W0 = Math.sqrt(1 - E2 * S0 * S0);
export const M_PER_DEG_LAT = GRS80_A * (1 - E2) / (W0 * W0 * W0) * D2R; // 110989.28 m (meridian radius at the ARP)
export const M_PER_DEG_LON = GRS80_A / W0 * C0 * D2R;                    // 88285.15 m
// NAD83(2011) lat/lon (deg) -> [east, north] m
export function llToEN(lat, lon) {
  const p = ecef(lat, lon), dx = p[0] - O[0], dy = p[1] - O[1], dz = p[2] - O[2];
  return [-SL * dx + CL * dy, -S0 * CL * dx - S0 * SL * dy + C0 * dz];
}
// inverse (point on the ellipsoid): fixed-Jacobian Newton iteration, converges to < 1e-9 m
export function enToLL(e, n) {
  let lat = ARP.lat + n / M_PER_DEG_LAT, lon = ARP.lon + e / M_PER_DEG_LON;
  for (let i = 0; i < 12; i++) {
    const q = llToEN(lat, lon), de = e - q[0], dn = n - q[1];
    lat += dn / M_PER_DEG_LAT; lon += de / M_PER_DEG_LON;
    if (Math.abs(de) + Math.abs(dn) < 1e-10) break;
  }
  return [lat, lon];
}
// NAD83(2011) lat/lon (FAA, NAIP, SFO Museum) -> world [x, y=h, z]
export function llToWorld(lat, lon, h = 0) { const [e, n] = llToEN(lat, lon); return [e, h, -n]; }
export function worldToLL(x, z) { return enToLL(x, -z); }
// WGS 84 lat/lon (ADS-B, OSM, GNSS; current realisation) <-> world. WGS84_MINUS_NAD83 = displacement of a fixed
// ground point from its NAD83(2011) to its WGS 84 coordinates, in metres east/north, at epoch DATUM.epoch.
export const DATUM = { world: 'NAD83(2011)', wgs84: 'WGS 84 (G2296) = ITRF2020', epoch: 2026.73, dE: -1.568, dN: 0.159, rateE: -0.0136, rateN: -0.0132 };
export function wgs84ToWorld(lat, lon, h = 0) { const [e, n] = llToEN(lat, lon); return [e - DATUM.dE, h, -(n - DATUM.dN)]; }
export function worldToWgs84(x, z) { return enToLL(x + DATUM.dE, -z + DATUM.dN); }
const dms = (d, m) => d + m / 60;

// FAA NASR (APT_RWY_END.csv, cycle 2026-09-03) = AirNav runway ends, degrees-decimal-minutes, NAD83; elevations ft;
// displaced thresholds ft (DISPLACED_THR_LEN). Verified in docs/research/stands_xcheck.md s.6.
export const RWY_ENDS = {
  '10L': { lat: dms(37, 37.724323), lon: -dms(122, 23.603512), elev: 5.5, disp: 0 },
  '28R': { lat: dms(37, 36.812017), lon: -dms(122, 21.428467), elev: 13.0, disp: 300 },
  '10R': { lat: dms(37, 37.577467), lon: -dms(122, 23.586327), elev: 7.1, disp: 0 },
  '28L': { lat: dms(37, 36.702717), lon: -dms(122, 21.500950), elev: 12.6, disp: 300 },
  '1L': { lat: dms(37, 36.473872), lon: -dms(122, 22.975710), elev: 10.7, disp: 640 },
  '19R': { lat: dms(37, 37.588882), lon: -dms(122, 22.236565), elev: 9.2, disp: 0 },
  '1R': { lat: dms(37, 36.379793), lon: -dms(122, 22.862445), elev: 11.4, disp: 560 },
  '19L': { lat: dms(37, 37.640532), lon: -dms(122, 22.026650), elev: 10.5, disp: 0 },
};
const FT = 0.3048;

// Airport grid frame: s along heading ~117.8 deg true (10 -> 28), t along heading ~27.8 deg (1 -> 19)
const e10L = llToEN(RWY_ENDS['10L'].lat, RWY_ENDS['10L'].lon), e28R = llToEN(RWY_ENDS['28R'].lat, RWY_ENDS['28R'].lon);
const hdgV = Math.atan2(e28R[0] - e10L[0], e28R[1] - e10L[1]);
export const V = [Math.sin(hdgV), Math.cos(hdgV)]; // (e,n)
export const U = [Math.sin(hdgV - Math.PI / 2), Math.cos(hdgV - Math.PI / 2)];
export const HDG_28 = (hdgV * 180 / Math.PI + 180) % 360; // true heading of rwy 28
export function stToEN(s, t) { return [s * V[0] + t * U[0], s * V[1] + t * U[1]]; }
export function enToST(e, n) { return [e * V[0] + n * V[1], e * U[0] + n * U[1]]; }
export function stToWorld(s, t, h = 0) { const [e, n] = stToEN(s, t); return [e, h, -n]; }
export function worldToST(x, z) { return enToST(x, -z); }
// direction vectors in world (x,z)
export const DIR_S = [V[0], 0, -V[1]]; // toward 28 end (ESE)
export const DIR_T = [U[0], 0, -U[1]]; // toward 19 end (NNE)

export const GROUND_Y = 3.0; // nominal airfield elevation (m) above bay datum

function rw(a, b, width) {
  const A = RWY_ENDS[a], B = RWY_ENDS[b];
  const pa = llToEN(A.lat, A.lon), pb = llToEN(B.lat, B.lon);
  const sa = enToST(...pa), sb = enToST(...pb);
  return {
    ends: [a, b], a: pa, b: pb, st0: sa, st1: sb, width: width * FT,
    length: Math.hypot(pb[0] - pa[0], pb[1] - pa[1]),
    dispA: A.disp * FT, dispB: B.disp * FT,
    elevA: A.elev * FT, elevB: B.elev * FT,
    hdgA: (Math.atan2(pb[0] - pa[0], pb[1] - pa[1]) * 180 / Math.PI + 360) % 360,
  };
}
export const RUNWAYS = [
  rw('10L', '28R', 200), rw('10R', '28L', 200), rw('1L', '19R', 200), rw('1R', '19L', 200),
];
// convenience: runway lookup by threshold name -> {thr (en), dir (en unit), rw}
export function runwayByEnd(name) {
  for (const r of RUNWAYS) {
    const [a, b] = r.ends;
    if (name === a || name === b) {
      const from = name === a ? r.a : r.b, to = name === a ? r.b : r.a;
      const L = Math.hypot(to[0] - from[0], to[1] - from[1]);
      const dir = [(to[0] - from[0]) / L, (to[1] - from[1]) / L];
      const disp = name === a ? r.dispA : r.dispB;
      return { rw: r, from, to, dir, length: L, disp, thr: [from[0] + dir[0] * disp, from[1] + dir[1] * disp] };
    }
  }
}

// ----- Terminal complex (approximate layout in airport s,t frame) -----
export const TERMINAL_CENTER = [-800, -850];
// piers: angle (deg, 0=+s, 90=+t), inner radius, length, width, name
export const ITB = { s: -1160, t: -850, hs: 65, ht: 165 };
// piers: root (s,t), direction angle (deg in s,t frame), length, width, end style
const polar = (ang, r) => [TERMINAL_CENTER[0] + Math.cos(ang * Math.PI / 180) * r, TERMINAL_CENTER[1] + Math.sin(ang * Math.PI / 180) * r];
export const PIERS = [
  { name: 'A', root: [-1135, -1005], ang: -55, len: 385, w: 36, wide: 0.8, end: 'round' },
  { name: 'B', root: polar(-82, 232), ang: -82, len: 330, w: 30, wide: 0.1, end: 'round' },
  { name: 'C', root: polar(-42, 232), ang: -42, len: 205, w: 24, wide: 0.05, end: 'rotunda', R: 38 },
  { name: 'D', root: polar(-3, 232), ang: -3, len: 215, w: 24, wide: 0.1, end: 'rotunda', R: 40 },
  { name: 'E', root: polar(36, 232), ang: 36, len: 250, w: 28, wide: 0.15, end: 'round' },
  { name: 'F', root: polar(74, 232), ang: 74, len: 300, w: 32, wide: 0.5, end: 'hammer', cross: 150 },
  { name: 'G', root: [-1135, -695], ang: 55, len: 385, w: 36, wide: 0.8, end: 'round' },
];

// Bay shoreline for the regional map, in km (e,n); polygon of WATER (San Francisco Bay, simplified)
// Airport land is added separately (see airportLand).
export const BAY_WATER_KM = [
  // west shore going north from south
  [16, -22], [12.5, -14], [11.8, -10.5], [10.8, -7.3], [9.4, -6.2], [7.2, -5.6], [5.4, -3.9], [4.6, -3.1], [3.2, -2.9],
  [1.8, -2.55], [0.9, -2.2], [-0.2, -1.95],
  // (airport occupies here; its land is drawn on top)
  [-0.45, -1.62], [-0.8, -0.5], [-0.8, 1.5], [-0.2, 2.6], [0.2, 3.6], [0.2, 4.6], [1.1, 5.0], [1.4, 5.4], [0.4, 5.6],
  [-0.2, 6.1], [0.3, 6.8], [-0.5, 7.4], [-0.9, 8.6], [-0.6, 9.7], [0.2, 10.4], [0.6, 11.0], [1.6, 11.6], [1.2, 12.6], [0.2, 13.4],
  [0.3, 15.0], [-0.6, 16.6], [-1.3, 18.3], [-1.6, 19.4], [-2.6, 20.6], [-4.6, 21.4], [-6.5, 22.0], [-8.0, 23.5], [-8.0, 26],
  [-2, 30], [4, 30], [6.5, 26],
  // east shore going south
  [5.8, 24.2], [6.2, 22.8], [5.0, 20.8], [4.2, 19.2], [4.6, 17.6], [6.4, 16.8], [8.5, 15.6], [10.2, 14.8], [12.2, 13.8], [13.2, 12.4],
  [13.4, 11.0], [14.8, 9.6], [16.2, 8.2], [17.4, 6.0], [18.6, 3.6], [19.8, 1.4], [20.8, 0.2], [21.6, -1.6], [22.6, -4.2],
  [24.2, -7.8], [26, -12], [27, -16], [26, -22],
];

// Airport landfill polygon in s,t (m). Mainland meets it on the west.
export const AIRPORT_LAND_ST = [
  [-2600, -1650], [-600, -1650], [-300, -1660], [420, -1640], [470, -1500], [420, -200], [1790, -210], [1850, -60],
  [1850, 330], [1790, 460], [470, 460], [470, 1320], [300, 1400], [-900, 1400], [-1500, 1350], [-2600, 1200],
];

// Approach light systems (lights into the bay). ALSF-2 on 28L/28R 2400ft, MALSF 1400ft on 1L/1R/19L/19R
export const APPROACH_LIGHTS = [
  { end: '28R', len: 2400 * FT, type: 'ALSF2' },
  { end: '28L', len: 2400 * FT, type: 'MALSR' },
  { end: '10L', len: 2400 * FT, type: 'ALSF2' },
  { end: '10R', len: 1400 * FT, type: 'MALSR' },
  { end: '1L', len: 1400 * FT, type: 'MALSF' },
  { end: '1R', len: 1400 * FT, type: 'MALSF' },
  { end: '19L', len: 1400 * FT, type: 'MALSF' },
  { end: '19R', len: 1400 * FT, type: 'MALSF' },
];

// Regional landmarks (lat, lon, height m)
export const LANDMARKS = {
  sfDowntown: llToWorld(37.7897, -122.3972),
  bayBridgeSF: llToWorld(37.7880, -122.3880),
  yerbaBuena: llToWorld(37.8105, -122.3650),
  oaklandTouchdown: llToWorld(37.8260, -122.3000),
  sanMateoBridgeW: llToWorld(37.5845, -122.2560),
  sanMateoBridgeE: llToWorld(37.6190, -122.1400),
  sanMateoBridgeHigh: llToWorld(37.5920, -122.2300),
};
