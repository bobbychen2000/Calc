// Geographic reference for KHWD (Hayward Executive). Python twin: tools/common/hwd_frame.py (keep identical;
// tools/common/test_hwd_frame.py checks >= 50 points both ways to 1 mm, the WGS 84 and UTM functions, the runway helpers,
// and both twins against pyproj and the FAA NASR rows).
//
// Forked from sfo3d/js/geo.js @ a967f9b. Kept: frame design, llToEN/enToLL, llToWorld/worldToLL, wgs84ToWorld/
// worldToWgs84, DATUM, RUNWAYS records and runwayByEnd (same interface; disp now from the surveyed thresholds), GROUND_Y
// (new meaning, below). Added: hdgVec/vecHdg (twins of hwd_frame.py hdg_vec/vec_hdg). Changed: origin = HWD ARP,
// FRAME_ID, datum displacement for HWD @ 2026.86, FAA NASR runway data (10L/28R, 10R/28L), vertical reference
// y = NAVD 88 height (GROUND_Y is now a nominal fallback). New: UTM 10N (EPSG:26910, NAIP), runway along/across and
// surface-profile helpers. Dropped (SFO only): the s/t airport grid, terminal/pier layout, bay shoreline and land
// polygons, approach lights/structures, PAPI/TDZ tables (the HWD VGSI data now sit in RWY_ENDS), regional landmarks.
//
// World frame 'ltp-nad83-2011-hwd': x = east (m), y = up (m), z = south (m), origin = ARP.
// - Datum NAD83(2011): FAA NASR coordinates are NAD 83 (realisation inferred, as in sfo3d), USDA NAIP is EPSG:26910.
// - Projection: exact local tangent plane (ENU) on the GRS80 ellipsoid at the ARP, at ellipsoidal height 0
//   (lat/lon -> ECEF -> east/north at the ARP). Flat world: y is height, so the horizontal position never depends on
//   it. Distances equal geodesic ones to < 0.1 mm within 5 km (0.5 m at 50 km).
// - ARP: FAA NASR APT_BASE (cycle 2026-10-29) LAT_DECIMAL 37.65893166, LONG_DECIMAL -122.12173888 (3RD PARTY SURVEY
//   2023/07/05), rounded to 1e-7 deg (origin 4.4 mm N, 1.8 mm W of the NASR decimal).
// - y = orthometric height in metres above NAVD 88 (~ MSL) = NASR elevation ft * 0.3048 [NAVD 88 inferred]. The field
//   is not flat: runway ends 27.7-52.1 ft (8.44-15.88 m). GROUND_Y = 11.4 is only a nominal flat-ground level (mean of
//   the six NASR runway points) for code without terrain [inferred]; use rwySurfaceY on runways.
// - WGS 84 inputs (ADS-B, OSM, GNSS) go through wgs84ToWorld: NAD83(2011) -> WGS 84 (G2296)/ITRF2020 at the HWD ARP,
//   epoch 2026.86, moves a fixed ground point by dE -1.568 m, dN +0.162 m, dH -0.512 m (pyproj 3.8.0 / PROJ 9.8.1,
//   EPSG:6319 -> EPSG:10605 = inverse "ITRF2020 to NAD83(2011) (1)" time-dependent Helmert + inverse "WGS 84 (G2296) to
//   ITRF2020 (1)"; rate -1.37 cm/yr E, -1.31 cm/yr N; 0.6 mm spatial variation within 5 km). Same chain at the SFO ARP
//   @ 2026.73 gives -1.5679 / +0.1589 = sfo3d's value. Intraplate Bay Area motion since 2010.0 is not modelled
//   [unverified, est. 0.2-0.4 m].
// - UTM 10N: transverse Mercator on GRS80 by the Krueger n-series to 6th order (Karney 2011, J. Geodesy 85:475),
//   checked against pyproj EPSG:26910 to 1 mm by the test.
export const ARP = { lat: 37.6589317, lon: -122.1217389 };
export const FRAME_ID = 'ltp-nad83-2011-hwd';
const GRS80_A = 6378137.0, GRS80_F = 1 / 298.257222101, E2 = GRS80_F * (2 - GRS80_F), D2R = Math.PI / 180;
export const FT = 0.3048;
function ecef(lat, lon) {
  const sl = Math.sin(lat * D2R), cl = Math.cos(lat * D2R);
  const N = GRS80_A / Math.sqrt(1 - E2 * sl * sl);
  return [N * cl * Math.cos(lon * D2R), N * cl * Math.sin(lon * D2R), N * (1 - E2) * sl];
}
const O = ecef(ARP.lat, ARP.lon);
const S0 = Math.sin(ARP.lat * D2R), C0 = Math.cos(ARP.lat * D2R), SL = Math.sin(ARP.lon * D2R), CL = Math.cos(ARP.lon * D2R);
const W0 = Math.sqrt(1 - E2 * S0 * S0);
export const M_PER_DEG_LAT = GRS80_A * (1 - E2) / (W0 * W0 * W0) * D2R; // meridian radius at the ARP (m/deg)
export const M_PER_DEG_LON = GRS80_A / W0 * C0 * D2R;
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
// NAD83(2011) lat/lon (FAA NASR, NAIP) -> world [x, y=h, z]
export function llToWorld(lat, lon, h = 0) { const [e, n] = llToEN(lat, lon); return [e, h, -n]; }
export function worldToLL(x, z) { return enToLL(x, -z); }
// WGS 84 lat/lon (ADS-B, OSM, GNSS; current realisation) <-> world. dE/dN = displacement of a fixed ground point from
// its NAD83(2011) to its WGS 84 coordinates (m east/north) at DATUM.epoch; dH ellipsoidal (information only).
export const DATUM = { world: 'NAD83(2011)', wgs84: 'WGS 84 (G2296) = ITRF2020', epoch: 2026.86, dE: -1.568, dN: 0.162, dH: -0.512, rateE: -0.0137, rateN: -0.0131 };
export function wgs84ToWorld(lat, lon, h = 0) { const [e, n] = llToEN(lat, lon); return [e - DATUM.dE, h, -(n - DATUM.dN)]; }
export function worldToWgs84(x, z) { return enToLL(x + DATUM.dE, -z + DATUM.dN); }

// ----- vertical reference: y = NAVD 88 height (m) [inferred from the NASR MSL elevations]
export const Y_REF = 'NAVD 88 orthometric height (m) [inferred from NASR MSL elevations]';
export const FIELD_ELEV_FT = 52.1;               // FAA NASR APT_BASE ELEV (3RD PARTY SURVEY 2023/07/05)
export const FIELD_ELEV_Y = FIELD_ELEV_FT * FT;  // 15.880 m
export const GROUND_Y = 11.4;                    // nominal flat ground [inferred]: mean of the 6 NASR runway points
export const elevFtToY = ft => ft * FT;

// ----- UTM zone 10N (EPSG:26910 = NAD83 / UTM 10N; NAIP): Krueger series, order 6 (Karney 2011)
export const UTM10 = { k0: 0.9996, lon0: -123.0, fe: 500000.0, fn: 0.0 };
const TN = GRS80_F / (2 - GRS80_F), TE = Math.sqrt(E2);
const n2 = TN ** 2, n3 = TN ** 3, n4 = TN ** 4, n5 = TN ** 5, n6 = TN ** 6;
const TM_A = GRS80_A / (1 + TN) * (1 + n2 / 4 + n4 / 64 + n6 / 256);
const ALPHA = [
  TN / 2 - 2 * n2 / 3 + 5 * n3 / 16 + 41 * n4 / 180 - 127 * n5 / 288 + 7891 * n6 / 37800,
  13 * n2 / 48 - 3 * n3 / 5 + 557 * n4 / 1440 + 281 * n5 / 630 - 1983433 * n6 / 1935360,
  61 * n3 / 240 - 103 * n4 / 140 + 15061 * n5 / 26880 + 167603 * n6 / 181440,
  49561 * n4 / 161280 - 179 * n5 / 168 + 6601661 * n6 / 7257600,
  34729 * n5 / 80640 - 3418889 * n6 / 1995840,
  212378941 * n6 / 319334400];
const BETA = [
  TN / 2 - 2 * n2 / 3 + 37 * n3 / 96 - n4 / 360 - 81 * n5 / 512 + 96199 * n6 / 604800,
  n2 / 48 + n3 / 15 - 437 * n4 / 1440 + 46 * n5 / 105 - 1118711 * n6 / 3870720,
  17 * n3 / 480 - 37 * n4 / 840 - 209 * n5 / 4480 + 5569 * n6 / 90720,
  4397 * n4 / 161280 - 11 * n5 / 504 - 830251 * n6 / 7257600,
  4583 * n5 / 161280 - 108847 * n6 / 3991680,
  20648693 * n6 / 638668800];
// NAD83 lat/lon (deg) -> [E, N] (m, EPSG:26910)
export function llToUtm10(lat, lon) {
  const phi = lat * D2R, lam = (lon - UTM10.lon0) * D2R, tau = Math.tan(phi);
  const sig = Math.sinh(TE * Math.atanh(TE * tau / Math.sqrt(1 + tau * tau)));
  const taup = tau * Math.sqrt(1 + sig * sig) - sig * Math.sqrt(1 + tau * tau);
  const xip = Math.atan2(taup, Math.cos(lam)), etap = Math.asinh(Math.sin(lam) / Math.sqrt(taup * taup + Math.cos(lam) ** 2));
  let xi = xip, eta = etap;
  for (let j = 1; j <= 6; j++) {
    const a = ALPHA[j - 1];
    xi += a * Math.sin(2 * j * xip) * Math.cosh(2 * j * etap);
    eta += a * Math.cos(2 * j * xip) * Math.sinh(2 * j * etap);
  }
  return [UTM10.fe + UTM10.k0 * TM_A * eta, UTM10.fn + UTM10.k0 * TM_A * xi];
}
// [E, N] (m, EPSG:26910) -> NAD83 [lat, lon] (deg)
export function utm10ToLL(E, N) {
  const xi = (N - UTM10.fn) / (UTM10.k0 * TM_A), eta = (E - UTM10.fe) / (UTM10.k0 * TM_A);
  let xip = xi, etap = eta;
  for (let j = 1; j <= 6; j++) {
    const b = BETA[j - 1];
    xip -= b * Math.sin(2 * j * xi) * Math.cosh(2 * j * eta);
    etap -= b * Math.cos(2 * j * xi) * Math.sinh(2 * j * eta);
  }
  const taup = Math.sin(xip) / Math.sqrt(Math.sinh(etap) ** 2 + Math.cos(xip) ** 2);
  const lam = Math.atan2(Math.sinh(etap), Math.cos(xip));
  let tau = taup;
  for (let i = 0; i < 8; i++) { // Newton for tau from tau' (Karney 2011)
    const sig = Math.sinh(TE * Math.atanh(TE * tau / Math.sqrt(1 + tau * tau)));
    const ti = tau * Math.sqrt(1 + sig * sig) - sig * Math.sqrt(1 + tau * tau);
    const dt = (taup - ti) / Math.sqrt(1 + ti * ti) * (1 + (1 - E2) * tau * tau) / ((1 - E2) * Math.sqrt(1 + tau * tau));
    tau += dt;
    if (Math.abs(dt) < 1e-14) break;
  }
  return [Math.atan(tau) / D2R, UTM10.lon0 + lam / D2R];
}
// NAIP / EPSG:26910 [E, N] -> world [x, y=h, z]
export function utm10ToWorld(E, N, h = 0) { const [la, lo] = utm10ToLL(E, N); return llToWorld(la, lo, h); }
export function worldToUtm10(x, z) { const [la, lo] = worldToLL(x, z); return llToUtm10(la, lo); }

// ----- headings: world (x, z) unit vector of a true heading
export const hdgVec = h => [Math.sin(h * D2R), -Math.cos(h * D2R)];
export const vecHdg = (dx, dz) => ((Math.atan2(dx, -dz) / D2R) % 360 + 360) % 360;

// ----- FAA runway ends: NASR APT_RWY_END.csv, cycle 2026-10-29 (refs/cache/faa/nasr_2026-10-29_HWD.json), surveyed
// 2023/07/05. Field meanings and sources: tools/common/hwd_frame.py RWY_ENDS (identical values). lat/lon NAD 83 decimals;
// elev/thrElev/tdzElev ft; disp = DISPLACED_THR_LEN ft; thrLat/thrLon = surveyed displaced threshold; vgsi P4L PAPI
// left, V4R/V4L VASI right/left; gpa deg; tch ft; marking PIR/NPI; rhTraffic (28L: NASR field empty -> standard
// left-hand [inferred]); trueAln = NASR TRUE_ALIGNMENT (whole degrees); reil = RWY_END_LGTS_FLAG; brg = geodesic
// forward azimuth to the opposite end (deg true, GRS80, pyproj Geod; checked by the test).
export const RWY_ENDS = {
  '10L': { lat: 37.66247844, lon: -122.12726369, elev: 28.1, disp: 0, thrLat: null, thrLon: null, thrElev: null,
    tdzElev: 36.9, vgsi: 'P4L', gpa: 3.0, tch: 29, marking: 'NPI', rhTraffic: false, trueAln: 120, ils: null, reil: false, brg: 119.85699 },
  '28R': { lat: 37.65822866, lon: -122.11795213, elev: 37.1, disp: 0, thrLat: null, thrLon: null, thrElev: null,
    tdzElev: 37.2, vgsi: 'P4L', gpa: 3.0, tch: 44, marking: 'NPI', rhTraffic: true, trueAln: 300, ils: null, reil: false, brg: 299.86268 },
  '10R': { lat: 37.66204722, lon: -122.12979350, elev: 27.7, disp: 826, thrLat: 37.66091861, thrLon: -122.12731986, thrElev: 29.3,
    tdzElev: 41.7, vgsi: 'V4R', gpa: 3.0, tch: 25, marking: 'PIR', rhTraffic: true, trueAln: 120, ils: null, reil: true, brg: 119.85159 },
  '28L': { lat: 37.65426300, lon: -122.11273616, elev: 52.1, disp: 676, thrLat: 37.65518672, thrLon: -122.11475980, thrElev: 50.0,
    tdzElev: 50.0, vgsi: 'V4L', gpa: 4.0, tch: 35, marking: 'PIR', rhTraffic: false, trueAln: 300, ils: 'LOC/DME', reil: true, brg: 299.86201 },
};
// FAA NASR APT_RWY.csv (same cycle): length / width ft, surface, treatment, condition, edge lights (MED = MIRL), strength
export const RWY_DATA = {
  '10L/28R': { ends: ['10L', '28R'], lenFt: 3108, widthFt: 75, surface: 'ASPH', treatment: 'NONE', cond: 'GOOD', lights: 'MED', gwSW: 13, gwDW: null },
  '10R/28L': { ends: ['10R', '28L'], lenFt: 5694, widthFt: 150, surface: 'ASPH', treatment: 'GRVD', cond: 'EXCELLENT', lights: 'MED', gwSW: 30, gwDW: 75 },
};
export const RWY_PAIRS = [['10L', '28R'], ['10R', '28L']];
const OPP = { '10L': '28R', '28R': '10L', '10R': '28L', '28L': '10R' };
export function endEN(name) { const E = RWY_ENDS[name]; return llToEN(E.lat, E.lon); }
export function endWorld(name, h = 0) { const E = RWY_ENDS[name]; return llToWorld(E.lat, E.lon, h); }

// Runway axis used from end `name`, world (x, z): origin = that end, dir toward the opposite end, right = pilot's right.
export function rwyAxis(name) {
  const a = endWorld(name), b = endWorld(OPP[name]);
  const dx = b[0] - a[0], dz = b[2] - a[2], L = Math.hypot(dx, dz), d = [dx / L, dz / L];
  return { end: name, opp: OPP[name], origin: [a[0], a[2]], dir: d, right: [-d[1], d[0]], length: L, hdg: vecHdg(dx, dz) };
}
// world (x, z) -> [along, across] m: along from end `name` toward the opposite end, across > 0 to the right
export function rwyAlongAcross(name, x, z) {
  const A = rwyAxis(name), px = x - A.origin[0], pz = z - A.origin[1];
  return [px * A.dir[0] + pz * A.dir[1], px * A.right[0] + pz * A.right[1]];
}
export function rwyToWorld(name, along, across = 0, h = 0) {
  const A = rwyAxis(name);
  return [A.origin[0] + along * A.dir[0] + across * A.right[0], h, A.origin[1] + along * A.dir[1] + across * A.right[1]];
}
// landing threshold: the surveyed NASR displaced threshold (on the axis to 1 mm) or the runway end
export function thrWorld(name, h = 0) { const E = RWY_ENDS[name]; return E.thrLat != null ? llToWorld(E.thrLat, E.thrLon, h) : endWorld(name, h); }
// threshold displacement along the axis (m) from the surveyed position (NASR DISPLACED_THR_LEN rounds to whole ft)
export function thrDispM(name) { if (RWY_ENDS[name].thrLat == null) return 0; const t = thrWorld(name); return rwyAlongAcross(name, t[0], t[2])[0]; }
// NASR surveyed surface points along the runway used from `name`: [[along m, y m], ...] ascending
export function rwyProfile(name) {
  const opp = OPP[name], L = rwyAxis(name).length, P = [[0, RWY_ENDS[name].elev * FT]];
  if (RWY_ENDS[name].thrLat != null) P.push([thrDispM(name), RWY_ENDS[name].thrElev * FT]);
  if (RWY_ENDS[opp].thrLat != null) P.push([L - thrDispM(opp), RWY_ENDS[opp].thrElev * FT]);
  P.push([L, RWY_ENDS[opp].elev * FT]);
  return P.sort((p, q) => p[0] - q[0]);
}
// runway surface y (m NAVD 88) `along` m from end `name`: linear between the surveyed points ([inferred] between them)
export function rwySurfaceY(name, along) {
  const P = rwyProfile(name);
  if (along <= P[0][0]) return P[0][1];
  for (let i = 1; i < P.length; i++) if (along <= P[i][0]) return P[i - 1][1] + (P[i][1] - P[i - 1][1]) * (along - P[i - 1][0]) / (P[i][0] - P[i - 1][0]);
  return P[P.length - 1][1];
}

// sfo3d-compatible runway records (a, b, from, to, thr in [east, north] like sfo3d; lengths m)
function rw(a, b) {
  const D = RWY_DATA[`${a}/${b}`], A = rwyAxis(a);
  return {
    id: `${a}/${b}`, ends: [a, b], a: endEN(a), b: endEN(b), width: D.widthFt * FT,
    length: A.length, lengthNasr: D.lenFt * FT, hdgA: A.hdg,
    dispA: thrDispM(a), dispB: thrDispM(b), elevA: RWY_ENDS[a].elev * FT, elevB: RWY_ENDS[b].elev * FT,
  };
}
export const RUNWAYS = RWY_PAIRS.map(([a, b]) => rw(a, b));
// runway lookup by end name -> {rw, from, to (en), dir (en unit), length, disp (m), thr (en)} (sfo3d interface)
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
