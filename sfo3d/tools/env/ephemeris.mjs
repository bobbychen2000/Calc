// tools/env/ephemeris.mjs
// Sun and Moon ephemeris for SFO Live 3D: positions (azimuth/elevation), rise/set, civil/nautical/astronomical
// twilight, Moon phase, illuminated fraction, bright-limb angle, natural illuminance (USNO Circular 171) and
// photographic exposure helpers (EV100). Pure ES module, no dependencies; runs in browsers and in Node >= 16.
// Research deliverable (docs/research/sun_night.md); nothing in js/ imports it yet.
//
// Verification (tools/env/test_ephemeris.mjs, fixtures in tools/env/fixtures/ephemeris_ref.json):
//   - NOAA mode reproduces the NOAA/GML Solar Calculator code (https://gml.noaa.gov/grad/solcalc/main.js,
//     fetched 2026-09-24) to < 1e-6 deg at SFO on 5 dates;
//   - Sun and Moon against JPL Horizons (DE441, topocentric apparent, https://ssd.jpl.nasa.gov/api/horizons.api):
//     5 dates x 25 hourly epochs: Sun max |d el| 0.0066 deg, |d az cos el| 0.0070 deg; Moon 0.0008 / 0.0010 deg,
//     illuminated fraction 0.008 percentage points, phase angle 0.007 deg (docs/research/sun_night.md section 2);
//   - sunrise/sunset/twilight and moonrise/moonset against the USNO 2026 tables for SFO
//     (https://aa.usno.navy.mil/calculated/rstt/year), Moon phases against USNO (https://aa.usno.navy.mil/api/moon/phases).
//
// Sources for the algorithms (verbatim constants; each function names its source):
//   [NOAA]  NOAA/GML Solar Calculator main.js and "Solar Calculation Details" (https://gml.noaa.gov/grad/solcalc/calcdetails.html):
//           Meeus-based sun (ecliptic longitude, obliquity, equation of time) and NOAA refraction.
//   [M]     J. Meeus, Astronomical Algorithms, 2nd ed. (Willmann-Bell 1998): ch. 12 sidereal time, ch. 13 coordinate
//           transforms, ch. 14 parallactic angle, ch. 16 refraction (Saemundsson 16.4), ch. 22 nutation (low accuracy),
//           ch. 40 topocentric parallax, ch. 47 Moon (ELP-2000/82 truncated; Tables 47.A/47.B transcribed from the MIT
//           `astronomia` 4.2.0 package, src/moonposition.js, (c) 2013 Sonia Keys, 2016 commenthol), ch. 48 illumination.
//   [USNO]  USNO "Rise, Set, and Twilight Definitions" (https://aa.usno.navy.mil/faq/RST_defs): sunrise = centre of the
//           Sun geometrically 50' below the horizon; twilight = centre geometrically 6/12/18 deg below; moonrise = geocentric
//           zenith distance 90.5666 deg + semidiameter - horizontal parallax.
//   [C171]  Janiczek & DeYoung, "Computer Programs for Sun and Moon Illuminance", USNO Circular 171 (1987),
//           FORTRAN listing pp. 20-23 (https://archive.org/details/DTIC_ADA182110). US Government work.
//   [IERS]  IERS Bulletin A (fetched 2026-09-24): TAI-UTC = 37 s since 2017-01-01, UT1-UTC = -0.015 s (Sept 2026);
//           no leap second at the end of 2026. Hence Delta T = TT - UT1 = 32.184 + 37 + 0.015 = 69.2 s.
//   [FB]    Lagarde & de Rousiers, "Moving Frostbite to Physically Based Rendering 3.0", SIGGRAPH 2014 course notes
//           v3.2, sections 4.3 and 5.1 (EV100 with K = 12.5; saturation-based max luminance 1.2 * 2^EV100).
//
// Conventions: angles in degrees; azimuth from north through east (0 = N, 90 = E); elevation above the horizon.
// Times are JS Date (UTC instants). Observer: { lat, lon (east positive), elevM }.

const DEG = Math.PI / 180;
const sind = (x) => Math.sin(x * DEG), cosd = (x) => Math.cos(x * DEG), tand = (x) => Math.tan(x * DEG);
const asind = (x) => Math.asin(Math.max(-1, Math.min(1, x))) / DEG;
const acosd = (x) => Math.acos(Math.max(-1, Math.min(1, x))) / DEG;
const atan2d = (y, x) => Math.atan2(y, x) / DEG;
const mod360 = (x) => ((x % 360) + 360) % 360;
const wrap180 = (x) => { const y = mod360(x); return y > 180 ? y - 360 : y; };

export const AU_KM = 149597870.7;            // IAU 2012 (also the Horizons header)
export const EARTH_A_KM = 6378.137;          // WGS-84 equatorial radius (Horizons "Center radii")
export const EARTH_F = 1 / 298.257223563;    // WGS-84 flattening
export const MOON_RADIUS_KM = 1737.4;        // Horizons "Target radii" for 301
export const SUN_SD_1AU_ARCSEC = 959.63;     // solar semidiameter at 1 au [M ch. 55]

// SFO airport reference point: AirNav/FAA "37-37-07.7000N 122-22-31.5000W", field elevation 13.1 ft (js/geo.js ARP).
export const SFO = { lat: 37.6188056, lon: -122.3754167, elevM: 4.0 };

// ------------------------------------------------------------------------------------------------ time
/** Julian Day (UT) of a JS Date. UTC is used for UT1 (|UT1-UTC| < 0.9 s by definition). */
export function julianDay(date) { return date.getTime() / 86400000 + 2440587.5; }
export function dateFromJulianDay(jd) { return new Date((jd - 2440587.5) * 86400000); }

/** Delta T = TT - UT in seconds. >= 2017: IERS (32.184 + 37 - (UT1-UTC)); 1986-2016: Espenak & Meeus polynomials
 *  (NASA eclipse web site, "Polynomial expressions for Delta T"); earlier: 0 (unsupported, rendering only). */
export function deltaT(date) {
  const y = date.getUTCFullYear() + (date.getUTCMonth() + 0.5) / 12;
  if (y >= 2017) return 32.184 + 37 + 0.015;
  const t = y - 2000;
  if (y >= 2005) return 62.92 + 0.32217 * t + 0.005589 * t * t;
  if (y >= 1986) return 63.86 + 0.3345 * t - 0.060374 * t ** 2 + 0.0017275 * t ** 3 + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5;
  return 0;
}

/** Greenwich mean sidereal time in degrees [M 12.4]; jd in UT. */
export function gmst(jd) {
  const T = (jd - 2451545) / 36525;
  return mod360(280.46061837 + 360.98564736629 * (jd - 2451545) + 0.000387933 * T * T - T * T * T / 38710000);
}

/** Nutation in longitude/obliquity (deg) and mean obliquity (deg), low-accuracy series [M ch. 22, ~0.5"/0.1"]. */
export function nutation(jde) {
  const T = (jde - 2451545) / 36525;
  const om = 125.04452 - 1934.136261 * T, L = 280.4665 + 36000.7698 * T, Lp = 218.3165 + 481267.8813 * T;
  const dpsi = (-17.20 * sind(om) - 1.32 * sind(2 * L) - 0.23 * sind(2 * Lp) + 0.21 * sind(2 * om)) / 3600;
  const deps = (9.20 * cosd(om) + 0.57 * cosd(2 * L) + 0.10 * cosd(2 * Lp) - 0.09 * cosd(2 * om)) / 3600;
  const eps0 = 23 + 26 / 60 + (21.448 - 46.8150 * T - 0.00059 * T * T + 0.001813 * T * T * T) / 3600;
  return { dpsi, deps, eps0, eps: eps0 + deps };
}

// ------------------------------------------------------------------------------------------------ coordinates
/** Geocentric equatorial (deg) -> local horizontal. ha = local hour angle (deg). [M 13.5, 13.6] */
export function equatorialToHorizontal(ha, dec, lat) {
  const el = asind(sind(lat) * sind(dec) + cosd(lat) * cosd(dec) * cosd(ha));
  const az = mod360(atan2d(sind(ha), cosd(ha) * sind(lat) - tand(dec) * cosd(lat)) + 180); // Meeus azimuth is from S
  return { az, el };
}

/** Observer's geocentric constants rho*sin(phi'), rho*cos(phi') (Earth radii) [M ch. 11]. */
function observerRho(lat, elevM) {
  const ba = 1 - EARTH_F, u = Math.atan(ba * tand(lat));
  const h = (elevM || 0) / (EARTH_A_KM * 1000);
  return { rs: ba * Math.sin(u) + h * sind(lat), rc: Math.cos(u) + h * cosd(lat) };
}

/** Topocentric RA/Dec from geocentric [M 40.2, 40.3]. distKm geocentric distance. Returns {ra, dec, ha, distKm}. */
function topocentric(ra, dec, distKm, lstDeg, obs) {
  const { rs, rc } = observerRho(obs.lat, obs.elevM);
  const sinPi = EARTH_A_KM / distKm, H = lstDeg - ra;
  const dA = atan2d(-rc * sinPi * sind(H), cosd(dec) - rc * sinPi * cosd(H));
  const decT = atan2d((sind(dec) - rs * sinPi) * cosd(dA), cosd(dec) - rc * sinPi * cosd(H));
  // topocentric distance: |geocentric vector - observer vector| (Earth radii -> km)
  const x = distKm * cosd(dec) * cosd(H) - rc * EARTH_A_KM, y = distKm * cosd(dec) * sind(H), z = distKm * sind(dec) - rs * EARTH_A_KM;
  return { ra: ra + dA, dec: decT, ha: H - dA, distKm: Math.hypot(x, y, z) };
}

// ------------------------------------------------------------------------------------------------ refraction
/** Refraction (deg) to ADD to a true (airless) elevation to get the apparent one.
 *  'bennett': Saemundsson's inversion of Bennett [M 16.4], scaled by (P/1010)(283/(273+T)) [M ch. 16]; default
 *             P = 1010 hPa, T = 10 C (the same standard conditions Horizons states for its refraction model).
 *  'noaa':    NOAA calculator piecewise formula (calcRefraction in main.js; applied to the airless elevation).
 *  'none':    0. Below -1 deg (bennett) the body is not visible; the value is clamped at its -1 deg value. */
export function refraction(trueElDeg, model = 'bennett', pressureHPa = 1010, tempC = 10) {
  if (model === 'none') return 0;
  if (model === 'noaa') {
    const e = trueElDeg; if (e > 85) return 0;
    const te = tand(e); let c;
    if (e > 5) c = 58.1 / te - 0.07 / te ** 3 + 0.000086 / te ** 5;
    else if (e > -0.575) c = 1735 + e * (-518.2 + e * (103.4 + e * (-12.79 + e * 0.711)));
    else c = -20.774 / te;
    return c / 3600;
  }
  const h = Math.max(trueElDeg, -1);
  if (h > 89.9) return 0;
  const Rarcmin = 1.02 / tand(h + 10.3 / (h + 5.11)) + 0.0019279; // +0.0019279' makes R(90 deg) = 0 [M 16.4 note]
  return Math.max(0, Rarcmin) / 60 * (pressureHPa / 1010) * (283 / (273 + tempC));
}

// ------------------------------------------------------------------------------------------------ Sun
/** Geocentric apparent Sun [NOAA/M ch. 25 low accuracy]; T in Julian centuries from J2000 (NOAA passes UT here). */
export function sunCoordinates(T) {
  const L0 = mod360(280.46646 + T * (36000.76983 + T * 0.0003032));
  const M = 357.52911 + T * (35999.05029 - 0.0001537 * T);
  const e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T);
  const C = sind(M) * (1.914602 - T * (0.004817 + 0.000014 * T)) + sind(2 * M) * (0.019993 - 0.000101 * T) + sind(3 * M) * 0.000289;
  const trueLong = L0 + C, v = M + C;
  const R = 1.000001018 * (1 - e * e) / (1 + e * cosd(v));
  const omega = 125.04 - 1934.136 * T;
  const lambda = trueLong - 0.00569 - 0.00478 * sind(omega);
  const eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60;
  const eps = eps0 + 0.00256 * cosd(omega);
  const ra = mod360(atan2d(cosd(eps) * sind(lambda), cosd(lambda)));
  const dec = asind(sind(eps) * sind(lambda));
  const y = tand(eps / 2) ** 2;
  const eqTime = 4 / DEG * (y * sind(2 * L0) - 2 * e * sind(M) + 4 * e * y * sind(M) * cosd(2 * L0) - 0.5 * y * y * sind(4 * L0) - 1.25 * e * e * sind(2 * M));
  return { lambda: mod360(lambda), ra, dec, R, eqTime, eps };
}

/**
 * Sun position for an observer.
 * opts.mode: 'accurate' (default) = sun coordinates at TT, hour angle from apparent sidereal time, topocentric
 *   parallax, refraction per opts.refraction ('bennett' default). 'noaa' = exact NOAA web-calculator arithmetic
 *   (UT as time argument, hour angle from the equation of time, NOAA refraction, no parallax).
 * Returns { az, el (apparent), elTrue (airless topocentric), ra, dec, distAU, eqTime (min), semidiameter (deg), ha }.
 */
export function sunPosition(date, obs = SFO, opts = {}) {
  const mode = opts.mode || 'accurate';
  const jd = julianDay(date);
  if (mode === 'noaa') {
    const T = (jd - 2451545) / 36525; const s = sunCoordinates(T);
    const utcMin = ((jd + 0.5) % 1) * 1440;
    let tst = utcMin + s.eqTime + 4 * obs.lon; tst = ((tst % 1440) + 1440) % 1440;
    let ha = tst / 4 - 180; if (ha < -180) ha += 360;
    const h = equatorialToHorizontal(ha, s.dec, obs.lat);
    const refr = opts.refraction === 'none' ? 0 : refraction(h.el, 'noaa');
    return { az: h.az, el: h.el + refr, elTrue: h.el, ra: s.ra, dec: s.dec, distAU: s.R, eqTime: s.eqTime, semidiameter: SUN_SD_1AU_ARCSEC / 3600 / s.R, ha };
  }
  const jde = jd + deltaT(date) / 86400, T = (jde - 2451545) / 36525;
  const s = sunCoordinates(T), n = nutation(jde);
  const lst = gmst(jd) + n.dpsi * cosd(n.eps) + obs.lon;
  const t = topocentric(s.ra, s.dec, s.R * AU_KM, lst, obs);
  const h = equatorialToHorizontal(t.ha, t.dec, obs.lat);
  const refr = refraction(h.el, opts.refraction || 'bennett', opts.pressureHPa, opts.tempC);
  return { az: h.az, el: h.el + refr, elTrue: h.el, ra: mod360(t.ra), dec: t.dec, distAU: s.R, eqTime: s.eqTime,
    semidiameter: SUN_SD_1AU_ARCSEC / 3600 / s.R, ha: wrap180(t.ha), lambda: s.lambda };
}

// ------------------------------------------------------------------------------------------------ Moon
// Meeus, Astronomical Algorithms 2nd ed., Table 47.A: [D, M, Mp, F, sum_l (1e-6 deg), sum_r (1e-3 km)]
const MOON_TA = [[0,0,1,0,6288774,-20905355],[2,0,-1,0,1274027,-3699111],[2,0,0,0,658314,-2955968],[0,0,2,0,213618,-569925],[0,1,0,0,-185116,48888],[0,0,0,2,-114332,-3149],[2,0,-2,0,58793,246158],[2,-1,-1,0,57066,-152138],[2,0,1,0,53322,-170733],[2,-1,0,0,45758,-204586],[0,1,-1,0,-40923,-129620],[1,0,0,0,-34720,108743],[0,1,1,0,-30383,104755],[2,0,0,-2,15327,10321],[0,0,1,2,-12528,0],[0,0,1,-2,10980,79661],[4,0,-1,0,10675,-34782],[0,0,3,0,10034,-23210],[4,0,-2,0,8548,-21636],[2,1,-1,0,-7888,24208],[2,1,0,0,-6766,30824],[1,0,-1,0,-5163,-8379],[1,1,0,0,4987,-16675],[2,-1,1,0,4036,-12831],[2,0,2,0,3994,-10445],[4,0,0,0,3861,-11650],[2,0,-3,0,3665,14403],[0,1,-2,0,-2689,-7003],[2,0,-1,2,-2602,0],[2,-1,-2,0,2390,10056],[1,0,1,0,-2348,6322],[2,-2,0,0,2236,-9884],[0,1,2,0,-2120,5751],[0,2,0,0,-2069,0],[2,-2,-1,0,2048,-4950],[2,0,1,-2,-1773,4130],[2,0,0,2,-1595,0],[4,-1,-1,0,1215,-3958],[0,0,2,2,-1110,0],[3,0,-1,0,-892,3258],[2,1,1,0,-810,2616],[4,-1,-2,0,759,-1897],[0,2,-1,0,-713,-2117],[2,2,-1,0,-700,2354],[2,1,-2,0,691,0],[2,-1,0,-2,596,0],[4,0,1,0,549,-1423],[0,0,4,0,537,-1117],[4,-1,0,0,520,-1571],[1,0,-2,0,-487,-1739],[2,1,0,-2,-399,0],[0,0,2,-2,-381,-4421],[1,1,1,0,351,0],[3,0,-2,0,-340,0],[4,0,-3,0,330,0],[2,-1,2,0,327,0],[0,2,1,0,-323,1165],[1,1,-1,0,299,0],[2,0,3,0,294,0],[2,0,-1,-2,0,8752]];
// Table 47.B: [D, M, Mp, F, sum_b (1e-6 deg)]
const MOON_TB = [[0,0,0,1,5128122],[0,0,1,1,280602],[0,0,1,-1,277693],[2,0,0,-1,173237],[2,0,-1,1,55413],[2,0,-1,-1,46271],[2,0,0,1,32573],[0,0,2,1,17198],[2,0,1,-1,9266],[0,0,2,-1,8822],[2,-1,0,-1,8216],[2,0,-2,-1,4324],[2,0,1,1,4200],[2,1,0,-1,-3359],[2,-1,-1,1,2463],[2,-1,0,1,2211],[2,-1,-1,-1,2065],[0,1,-1,-1,-1870],[4,0,-1,-1,1828],[0,1,0,1,-1794],[0,0,0,3,-1749],[0,1,-1,1,-1565],[1,0,0,1,-1491],[0,1,1,1,-1475],[0,1,1,-1,-1410],[0,1,0,-1,-1344],[1,0,0,-1,-1335],[0,0,3,1,1107],[4,0,0,-1,1021],[4,0,-1,1,833],[0,0,1,-3,777],[4,0,-2,1,671],[2,0,0,-3,607],[2,0,2,-1,596],[2,-1,1,-1,491],[2,0,-2,1,-451],[0,0,3,-1,439],[2,0,2,1,422],[2,0,-3,-1,421],[2,1,-1,1,-366],[2,1,0,1,-351],[4,0,0,1,331],[2,-1,1,1,315],[2,-2,0,-1,302],[0,0,1,3,-283],[2,1,1,-1,-229],[1,1,0,-1,223],[1,1,0,1,223],[0,1,-2,-1,-220],[2,1,-1,-1,-220],[1,0,1,1,-185],[2,-1,-2,-1,181],[0,1,2,1,-177],[4,0,-2,-1,176],[4,-1,-1,-1,166],[1,0,1,-1,-164],[4,0,1,-1,132],[1,0,-1,-1,-119],[4,-1,0,-1,115],[2,-2,0,1,107]];

/** Geocentric Moon, mean equinox of date, no nutation [M ch. 47]: {lambda, beta (deg), distKm}. */
export function moonEcliptic(jde) {
  const T = (jde - 2451545) / 36525;
  const Lp = 218.3164477 + T * (481267.88123421 + T * (-0.0015786 + T * (1 / 538841 - T / 65194000)));
  const D = 297.8501921 + T * (445267.1114034 + T * (-0.0018819 + T * (1 / 545868 - T / 113065000)));
  const M = 357.5291092 + T * (35999.0502909 + T * (-0.0001536 + T / 24490000));
  const Mp = 134.9633964 + T * (477198.8675055 + T * (0.0087414 + T * (1 / 69699 - T / 14712000)));
  const F = 93.2720950 + T * (483202.0175233 + T * (-0.0036539 + T * (-1 / 3526000 + T / 863310000)));
  const A1 = 119.75 + 131.849 * T, A2 = 53.09 + 479264.290 * T, A3 = 313.45 + 481266.484 * T;
  const E = 1 - 0.002516 * T - 0.0000074 * T * T, E2 = E * E;
  let sl = 3958 * sind(A1) + 1962 * sind(Lp - F) + 318 * sind(A2), sr = 0;
  let sb = -2235 * sind(Lp) + 382 * sind(A3) + 175 * sind(A1 - F) + 175 * sind(A1 + F) + 127 * sind(Lp - Mp) - 115 * sind(Lp + Mp);
  for (const [d, m, mp, f, l, r] of MOON_TA) {
    const arg = d * D + m * M + mp * Mp + f * F, k = m === 0 ? 1 : (Math.abs(m) === 1 ? E : E2);
    sl += l * k * sind(arg); sr += r * k * cosd(arg);
  }
  for (const [d, m, mp, f, b] of MOON_TB) {
    const k = m === 0 ? 1 : (Math.abs(m) === 1 ? E : E2);
    sb += b * k * sind(d * D + m * M + mp * Mp + f * F);
  }
  return { lambda: mod360(Lp + sl / 1e6), beta: sb / 1e6, distKm: 385000.56 + sr / 1000 };
}

/** Ecliptic -> equatorial (deg) [M 13.3, 13.4]. */
export function eclipticToEquatorial(lambda, beta, eps) {
  const ra = mod360(atan2d(sind(lambda) * cosd(eps) - tand(beta) * sind(eps), cosd(lambda)));
  const dec = asind(sind(beta) * cosd(eps) + cosd(beta) * sind(eps) * sind(lambda));
  return { ra, dec };
}

const vec = (ra, dec, r) => [r * cosd(dec) * cosd(ra), r * cosd(dec) * sind(ra), r * sind(dec)];
const angleBetween = (a, b) => acosd((a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (Math.hypot(...a) * Math.hypot(...b)));

/**
 * Moon position and appearance for an observer (topocentric, apparent).
 * Returns { az, el, elTrue, ra, dec, distKm (topocentric), geoDistKm, angularDiameter (deg), horizontalParallax (deg),
 *   phaseAngle (deg, Sun-Moon-observer), illuminatedFraction (0..1), elongation (deg, geocentric, 0..360 = Moon
 *   minus Sun apparent longitude), waxing, phaseName, brightLimbAngle (deg, position angle of the bright limb's
 *   midpoint from celestial north through east [M 48.5]), parallacticAngle (deg [M 14.1]),
 *   brightLimbZenithAngle (deg, bright-limb direction measured from the observer's zenith, = chi - q),
 *   geoElTrue (deg, geocentric airless elevation, for rise/set per USNO) }.
 */
export function moonPosition(date, obs = SFO, opts = {}) {
  const jd = julianDay(date), jde = jd + deltaT(date) / 86400;
  const n = nutation(jde), m = moonEcliptic(jde);
  const lam = m.lambda + n.dpsi;
  const eq = eclipticToEquatorial(lam, m.beta, n.eps);
  const lst = gmst(jd) + n.dpsi * cosd(n.eps) + obs.lon;
  const t = topocentric(eq.ra, eq.dec, m.distKm, lst, obs);
  const h = equatorialToHorizontal(t.ha, t.dec, obs.lat);
  const geo = equatorialToHorizontal(lst - eq.ra, eq.dec, obs.lat);
  const refr = refraction(h.el, opts.refraction || 'bennett', opts.pressureHPa, opts.tempC);
  // Sun (geocentric apparent) for phase: vectors in the equatorial frame of date (km)
  const s = sunCoordinates((jde - 2451545) / 36525);
  const S = vec(s.ra, s.dec, s.R * AU_KM), Mo = vec(eq.ra, eq.dec, m.distKm);
  const { rs, rc } = observerRho(obs.lat, obs.elevM);
  const O = [rc * EARTH_A_KM * cosd(lst), rc * EARTH_A_KM * sind(lst), rs * EARTH_A_KM];
  const toSun = [S[0] - Mo[0], S[1] - Mo[1], S[2] - Mo[2]], toObs = [O[0] - Mo[0], O[1] - Mo[1], O[2] - Mo[2]];
  const phaseAngle = angleBetween(toSun, toObs);
  const elong = mod360(lam - s.lambda);
  // position angle of the bright limb [M 48.5] (topocentric Moon, geocentric Sun) and parallactic angle [M 14.1]
  const chi = mod360(atan2d(cosd(s.dec) * sind(s.ra - t.ra), sind(s.dec) * cosd(t.dec) - cosd(s.dec) * sind(t.dec) * cosd(s.ra - t.ra)));
  const q = atan2d(sind(t.ha), tand(obs.lat) * cosd(t.dec) - sind(t.dec) * cosd(t.ha));
  return {
    az: h.az, el: h.el + refr, elTrue: h.el, geoElTrue: geo.el, ra: mod360(t.ra), dec: t.dec,
    distKm: t.distKm, geoDistKm: m.distKm, angularDiameter: 2 * asind(MOON_RADIUS_KM / t.distKm),
    horizontalParallax: asind(EARTH_A_KM / m.distKm), phaseAngle, illuminatedFraction: (1 + cosd(phaseAngle)) / 2,
    elongation: elong, waxing: elong < 180, phaseName: moonPhaseName(elong),
    brightLimbAngle: chi, parallacticAngle: q, brightLimbZenithAngle: mod360(chi - q),
    lambda: mod360(lam), beta: m.beta,
  };
}

/** Phase name from the Moon-minus-Sun longitude (deg). The four principal phases are instants [USNO]; for a label
 *  we give them a +-6.1 deg window (about 12 h either side; our choice, not a USNO rule). */
export function moonPhaseName(elong) {
  const e = mod360(elong), w = 6.1;
  if (e < w || e > 360 - w) return 'New Moon';
  if (Math.abs(e - 90) < w) return 'First Quarter';
  if (Math.abs(e - 180) < w) return 'Full Moon';
  if (Math.abs(e - 270) < w) return 'Last Quarter';
  if (e < 90) return 'Waxing Crescent'; if (e < 180) return 'Waxing Gibbous';
  if (e < 270) return 'Waning Gibbous'; return 'Waning Crescent';
}

// ------------------------------------------------------------------------------------------------ events
/** Find instants in [t0, t1) where f crosses 0 (scan + bisection to ~1 s). Returns [{date, rising}] */
function findCrossings(f, t0, t1, stepMin = 10) {
  const out = [], step = stepMin * 60000;
  let ta = t0.getTime(), fa = f(new Date(ta));
  for (let tb = ta + step; ta < t1.getTime(); tb += step) {
    const fb = f(new Date(tb));
    if ((fa < 0 && fb >= 0) || (fa >= 0 && fb < 0)) {
      let lo = ta, hi = tb, flo = fa;
      for (let i = 0; i < 40 && hi - lo > 500; i++) {
        const mid = (lo + hi) / 2, fm = f(new Date(mid));
        if ((flo < 0) === (fm < 0)) { lo = mid; flo = fm; } else hi = mid;
      }
      const tc = (lo + hi) / 2; if (tc >= t0.getTime() && tc < t1.getTime()) out.push({ date: new Date(tc), rising: fa < 0 });
    }
    ta = tb; fa = fb;
  }
  return out;
}

/** Local civil day [start, end) for a calendar date y-m-d at a fixed UTC offset (hours, e.g. -8 PST / -7 PDT). */
export function localDay(y, m, d, utcOffsetH) {
  const start = new Date(Date.UTC(y, m - 1, d) - utcOffsetH * 3600000);
  return [start, new Date(start.getTime() + 86400000)];
}

export const SUN_EVENT_DEPRESSION = { riseSet: 50 / 60, civil: 6, nautical: 12, astronomical: 18 }; // [USNO]

/**
 * Sun events in a local day (fixed UTC offset). Geometric (airless) elevation of the Sun's centre is compared with
 * -50' (rise/set) and -6/-12/-18 deg (twilight), as USNO defines them; observer height is ignored like USNO.
 * Returns { sunrise, sunset, civilDawn, civilDusk, nauticalDawn, nauticalDusk, astronomicalDawn, astronomicalDusk,
 *   transit, transitEl } (Dates or null).
 */
export function sunEvents(y, m, d, utcOffsetH, obs = SFO) {
  const [t0, t1] = localDay(y, m, d, utcOffsetH);
  const o = { ...obs, elevM: 0 };
  const el = (dt) => sunPosition(dt, o, { refraction: 'none' }).elTrue;
  const res = {};
  for (const [k, dep] of Object.entries(SUN_EVENT_DEPRESSION)) {
    const c = findCrossings((dt) => el(dt) + dep, t0, t1);
    const up = c.find((e) => e.rising), dn = c.find((e) => !e.rising);
    const names = { riseSet: ['sunrise', 'sunset'], civil: ['civilDawn', 'civilDusk'], nautical: ['nauticalDawn', 'nauticalDusk'], astronomical: ['astronomicalDawn', 'astronomicalDusk'] }[k];
    res[names[0]] = up ? up.date : null; res[names[1]] = dn ? dn.date : null;
  }
  const tr = findCrossings((dt) => wrap180(sunPosition(dt, o, { refraction: 'none' }).ha), t0, t1).find((e) => e.rising);
  res.transit = tr ? tr.date : null; res.transitEl = tr ? el(tr.date) : null;
  return res;
}

/** Moonrise/moonset in a local day per USNO: geocentric zenith distance of the centre = 90.5666 + SD - HP. */
export function moonEvents(y, m, d, utcOffsetH, obs = SFO) {
  const [t0, t1] = localDay(y, m, d, utcOffsetH);
  const f = (dt) => {
    const p = moonPosition(dt, { ...obs, elevM: 0 }, { refraction: 'none' });
    const sd = asind(MOON_RADIUS_KM / p.geoDistKm);
    return p.geoElTrue - (-0.5666 - sd + p.horizontalParallax);
  };
  const c = findCrossings(f, t0, t1);
  const up = c.find((e) => e.rising), dn = c.find((e) => !e.rising);
  return { moonrise: up ? up.date : null, moonset: dn ? dn.date : null };
}

/** Principal Moon phases between two dates: instants when the geocentric apparent Moon-minus-Sun ecliptic longitude
 *  is 0/90/180/270 deg (the USNO/almanac definition). Returns [{date, phase}] sorted. */
export function moonPhases(t0, t1) {
  const names = ['New Moon', 'First Quarter', 'Full Moon', 'Last Quarter'];
  const el = (dt) => { const jde = julianDay(dt) + deltaT(dt) / 86400; const n = nutation(jde);
    return mod360(moonEcliptic(jde).lambda + n.dpsi - sunCoordinates((jde - 2451545) / 36525).lambda); };
  const out = [];
  names.forEach((name, i) => {
    const c = findCrossings((dt) => wrap180(el(dt) - 90 * i), t0, t1, 360);
    for (const e of c) if (e.rising) out.push({ date: e.date, phase: name });
  });
  return out.sort((a, b) => a.date - b.date);
}

// ------------------------------------------------------------------------------------------------ illuminance [C171]
/** Air-mass/extinction factor M of Circular 171 (SUBROUTINE ATMOS) for apparent elevation ha (deg). */
function c171Atmos(ha) {
  const U = sind(ha), X = 753.66156;
  const S = Math.asin(X * cosd(ha) / (X + 1));
  let M = X * (Math.cos(S) - U) + Math.cos(S);
  M = Math.exp(-0.21 * M) * U + 0.0289 * Math.exp(-0.042 * M) * (1 + (ha + 90) * U / 57.29577951);
  return M;
}
/** Circular 171 SUBROUTINE REFR: apparent from geometric elevation (Bennett's formula with one constant changed). */
function c171Refr(h) { return h < -5 / 6 ? h : h + 1 / Math.tan((h + 8.6 / (h + 4.42)) * DEG) / 60; }

/**
 * Natural horizontal illuminance at sea level (lux), USNO Circular 171 (Janiczek & DeYoung 1987), transcribed from
 * the FORTRAN listing (statements 660-805, SUBROUTINES REFR and ATMOS). Inputs are GEOCENTRIC airless elevations of
 * the Sun and Moon (deg) and the Moon's geocentric elongation from the Sun (deg, 0..180); sky = Brown's cloud divisor
 * (1 clear/<70% cover, 2 thin cloud over the disc, 3 average cloud, 10 dark stratus). The code adds 0.0005 lx for
 * the night sky; the report's Appendix B says 0.0003 lx (the code is used here). The authors state results are
 * good to one or two digits and the model is fitted from the zenith down to nautical twilight.
 */
export function naturalIlluminance(sunGeoEl, moonGeoEl, moonElongDeg, sky = 1) {
  const sun = 133775 * c171Atmos(c171Refr(sunGeoEl)) / sky;
  let moon = 0;
  if (moonGeoEl != null) {
    const Z = moonGeoEl * DEG;                                 // geocentric altitude (rad), statement 660+2
    const hTopo = moonGeoEl - 0.95 * cosd(moonGeoEl);          // parallax, 0.95 deg
    const E = Math.abs(moonElongDeg) * DEG; const e = E > Math.PI ? 2 * Math.PI - E : E;
    let P = 0.892 * Math.exp(-3.343 / Math.pow(Math.tan(e / 2), 0.632)) + 0.0344 * (Math.sin(e) - e * Math.cos(e));
    P = 0.418 * P / (1 - 0.005 * Math.cos(e) - 0.03 * Math.sin(Z));
    moon = P * c171Atmos(c171Refr(hTopo)) / sky;
  }
  const background = 0.0005 / sky;
  return { sun: Math.max(0, sun), moon: Math.max(0, moon), background, total: Math.max(0, sun) + Math.max(0, moon) + background };
}

/** Convenience: natural illuminance at a date for an observer (uses this module's Sun/Moon). */
export function naturalIlluminanceAt(date, obs = SFO, sky = 1) {
  const o = { ...obs, elevM: 0 };
  const jd = julianDay(date), jde = jd + deltaT(date) / 86400, n = nutation(jde);
  const s = sunCoordinates((jde - 2451545) / 36525);                       // geocentric apparent Sun
  const sunGeo = equatorialToHorizontal(gmst(jd) + n.dpsi * cosd(n.eps) + obs.lon - s.ra, s.dec, obs.lat).el;
  const mo = moonPosition(date, o, { refraction: 'none' });
  const el = mo.elongation > 180 ? 360 - mo.elongation : mo.elongation;
  // Circular 171 uses the true elongation acos(cos(dlambda) cos(beta)), not the longitude difference
  const trueElong = acosd(cosd(el) * cosd(mo.beta));
  return naturalIlluminance(sunGeo, mo.geoElTrue, trueElong, sky);
}

// ------------------------------------------------------------------------------------------------ exposure [FB]
/** EV100 from average scene luminance (cd/m^2), reflected-light meter constant K = 12.5 [FB eq. 11, ISO 2720]. */
export const ev100FromLuminance = (L, K = 12.5) => Math.log2(L * 100 / K);
/** Luminance (cd/m^2) that EV100 meters as mid-exposure [FB eq. 12]: L = 2^(EV100 - 3). */
export const luminanceFromEV100 = (ev) => Math.pow(2, ev - 3);
/** EV100 from camera settings [FB 5.1]: log2(N^2 / t * 100 / S). */
export const ev100FromCamera = (aperture, shutterS, iso) => Math.log2(aperture * aperture / shutterS * 100 / iso);
/** Scale factor applied to scene luminance before tone mapping, saturation-based sensitivity [FB listing 26-27]:
 *  Lmax = 1.2 * 2^EV100, exposure = 1 / Lmax. */
export const exposureFromEV100 = (ev) => 1 / (1.2 * Math.pow(2, ev));
/** EV100 for a Lambertian surface of reflectance rho under illuminance E (lux): L = rho E / pi. */
export const ev100ForIlluminance = (E, rho = 0.18, K = 12.5) => ev100FromLuminance(rho * E / Math.PI, K);

/** Night-sky luminance (cd/m^2) from a surface brightness in mag/arcsec^2: L = 10.8e4 * 10^(-0.4 m)
 *  (Unihedron conversion quoted by Kyba et al. 2011, PLoS ONE 6(3):e17307; 22.0 -> 1.71e-4, cf. Falchi 2016's 174e-6). */
export const skyLuminanceFromMag = (m) => 10.8e4 * Math.pow(10, -0.4 * m);

// ------------------------------------------------------------------------------------------------ renderer helper
/** Unit vector toward a body in the app's world frame (x = east, y = up, z = south), matching js/world/textures.js
 *  sunVector(az, el) = [sin az cos el, sin el, -cos az cos el]. */
export function directionWorld(az, el) { return [sind(az) * cosd(el), sind(el), -cosd(az) * cosd(el)]; }

/** One call for the renderer: sun, moon, twilight phase and natural illuminance at an instant. */
export function skyState(date, obs = SFO, opts = {}) {
  const sun = sunPosition(date, obs, opts), moon = moonPosition(date, obs, opts);
  const e = sun.elTrue;
  const phase = e > -50 / 60 ? 'day' : e > -6 ? 'civil' : e > -12 ? 'nautical' : e > -18 ? 'astronomical' : 'night';
  return { sun, moon, phase, sunDir: directionWorld(sun.az, sun.el), moonDir: directionWorld(moon.az, moon.el),
    illuminance: naturalIlluminanceAt(date, obs, opts.sky || 1) };
}
