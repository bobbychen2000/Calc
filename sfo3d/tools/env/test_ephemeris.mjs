// tools/env/test_ephemeris.mjs
// Checks tools/env/ephemeris.mjs against published reference values (tools/env/fixtures/ephemeris_ref.json, built by
// tools/env/build_ephemeris_fixtures.mjs from raw NOAA, JPL Horizons and USNO downloads):
//   A  Meeus worked examples 47.a (Moon position) and 48.a (illuminated fraction)
//   B  NOAA mode vs the NOAA/GML Solar Calculator's own code (main.js), 125 epochs at SFO on 5 dates
//   C  sunrise / sunset / solar noon vs NOAA's calcSunriseSet / calcSolNoon on the same 5 dates
//   D  Sun (accurate mode) vs JPL Horizons DE441 topocentric apparent Az/El, airless and refracted
//   E  Moon vs JPL Horizons: Az/El, illuminated fraction, phase angle, angular diameter, distance
//   F  USNO 2026 tables for SFO: sunrise/sunset, civil, nautical, astronomical twilight, every day of the year
//   G  USNO 2026 moonrise/moonset, every day
//   H  USNO 2026 principal Moon phases (50)
//   I  USNO Circular 171 sample run (natural illuminance)
// Run: node tools/env/test_ephemeris.mjs        (exit code 1 on any failure; prints an error table)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as E from './ephemeris.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REF = JSON.parse(fs.readFileSync(path.join(HERE, 'fixtures/ephemeris_ref.json'), 'utf8'));
const OBS = REF.meta.observer;
let failures = 0; const rows = [];
const angDiff = (a, b) => { const d = ((a - b) % 360 + 540) % 360 - 180; return d; };
const stats = (arr) => { const a = arr.map(Math.abs); return { n: a.length, max: Math.max(...a), rms: Math.sqrt(a.reduce((s, x) => s + x * x, 0) / a.length) }; };
function check(name, value, tol, unit, extra = '') {
  const ok = value <= tol; if (!ok) failures++;
  rows.push(`${ok ? 'PASS' : 'FAIL'} | ${name} | ${typeof value === 'number' ? +value.toPrecision(3) : value} ${unit} | tol ${tol} ${unit} ${extra}`);
}

// ---------------------------------------------------------------- A: Meeus examples
{
  const m = E.moonEcliptic(2448724.5);   // 1992-04-12 0h TD
  check('A Meeus 47.a lambda', Math.abs(m.lambda - 133.162655), 1e-6, 'deg');
  check('A Meeus 47.a beta', Math.abs(m.beta - -3.229126), 1e-6, 'deg');
  check('A Meeus 47.a distance', Math.abs(m.distKm - 368409.7), 0.1, 'km');
  check('A Meeus 47.a parallax', Math.abs(E.moonPosition(new Date(Date.UTC(1992, 3, 12) - 0)).horizontalParallax - 0.991990), 2e-4, 'deg', '(UT vs TD epoch)');
  // 48.a: Moon alpha 134.6885 delta 13.7684 dist 368410; Sun alpha 20.6579 delta 8.6964 dist 149971520 -> i = 69.0756, k = 0.6775
  const v = (ra, dec, r) => [r * Math.cos(dec * Math.PI / 180) * Math.cos(ra * Math.PI / 180), r * Math.cos(dec * Math.PI / 180) * Math.sin(ra * Math.PI / 180), r * Math.sin(dec * Math.PI / 180)];
  const Mo = v(134.6885, 13.7684, 368410), S = v(20.6579, 8.6964, 149971520);
  const a = S.map((s, i) => s - Mo[i]), b = Mo.map((x) => -x);
  const i = Math.acos((a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (Math.hypot(...a) * Math.hypot(...b))) * 180 / Math.PI;
  check('A Meeus 48.a phase angle (vector method)', Math.abs(i - 69.0756), 1e-3, 'deg');
  // k = (1 + cos i) / 2 [M 48.1] with i = 69.0756 gives 0.67858. (0.6775 in astronomia's test is the cruder
  // distance-free method 48.2/48.4, not the value for i = 69.0756.)
  check('A Meeus 48.a k from i (48.1)', Math.abs((1 + Math.cos(i * Math.PI / 180)) / 2 - (1 + Math.cos(69.0756 * Math.PI / 180)) / 2), 1e-5, '');
}

// ---------------------------------------------------------------- B: NOAA code
{
  const dAz = [], dEl = [];
  for (const r of REF.noaa.azel) {
    const p = E.sunPosition(new Date(r.t), OBS, { mode: 'noaa' });
    dEl.push(p.el - r.el); if (r.el > -89) dAz.push(angDiff(p.az, r.az));
  }
  check('B NOAA-mode elevation vs NOAA main.js', stats(dEl).max, 1e-6, 'deg', `(n=${dEl.length})`);
  check('B NOAA-mode azimuth vs NOAA main.js', stats(dAz).max, 1e-6, 'deg');
}

// ---------------------------------------------------------------- C: NOAA rise/set/noon
{
  const d = [];
  for (const day of REF.noaa.days) {
    const [y, m, dd] = day.date.split('-').map(Number);
    const ev = E.sunEvents(y, m, dd, day.tz, OBS);
    const loc = (dt) => ((dt.getTime() / 60000 + day.tz * 60) % 1440 + 1440) % 1440;
    d.push(loc(ev.sunrise) - day.sunriseMin, loc(ev.sunset) - day.sunsetMin, loc(ev.transit) - day.noonMin);
  }
  check('C sunrise/sunset/noon vs NOAA calcSunriseSet/calcSolNoon', stats(d).max * 60, 30, 's', `(n=${d.length}, rms ${(stats(d).rms * 60).toFixed(1)} s)`);
}

// ---------------------------------------------------------------- D: Sun vs Horizons
{
  const dAz = [], dEl = [], dElR = [], dElR5 = [], dElNoaa = [], dAzNoaa = [], dSD = [];
  for (const r of REF.horizons.sun) {
    const t = new Date(r.t);
    const p = E.sunPosition(t, OBS, { refraction: 'none' });
    dEl.push(p.elTrue - r.airless.el); dAz.push(angDiff(p.az, r.airless.az) * Math.cos(r.airless.el * Math.PI / 180));
    dSD.push(2 * p.semidiameter * 3600 - r.angDiamArcsec);
    const q = E.sunPosition(t, OBS, { mode: 'noaa', refraction: 'none' });
    dElNoaa.push(q.elTrue - r.airless.el); dAzNoaa.push(angDiff(q.az, r.airless.az) * Math.cos(r.airless.el * Math.PI / 180));
    if (r.refracted.el > 0) { const pr = E.sunPosition(t, OBS); dElR.push(pr.el - r.refracted.el); if (r.refracted.el > 5) dElR5.push(pr.el - r.refracted.el); }
  }
  check('D Sun elevation (airless) vs Horizons', stats(dEl).max, 0.01, 'deg', `(n=${dEl.length}, rms ${stats(dEl).rms.toFixed(4)})`);
  check('D Sun azimuth x cos(el) (airless) vs Horizons', stats(dAz).max, 0.01, 'deg', `(rms ${stats(dAz).rms.toFixed(4)})`);
  check('D Sun elevation NOAA-mode (airless) vs Horizons', stats(dElNoaa).max, 0.02, 'deg', `(rms ${stats(dElNoaa).rms.toFixed(4)})`);
  check('D Sun azimuth x cos(el) NOAA-mode vs Horizons', stats(dAzNoaa).max, 0.02, 'deg', `(rms ${stats(dAzNoaa).rms.toFixed(4)})`);
  check('D Sun apparent elevation (Bennett, el > 5) vs Horizons refracted', stats(dElR5).max, 0.01, 'deg', `(n=${dElR5.length})`);
  check('D Sun apparent elevation (Bennett, 0 < el) vs Horizons refracted', stats(dElR).max, 0.05, 'deg', `(n=${dElR.length})`);
  check('D Sun angular diameter vs Horizons', stats(dSD).max, 1.0, 'arcsec');
}

// ---------------------------------------------------------------- E: Moon vs Horizons
{
  const dAz = [], dEl = [], dElR = [], dK = [], dI = [], dD = [], dR = [];
  for (const r of REF.horizons.moon) {
    const t = new Date(r.t);
    const p = E.moonPosition(t, OBS, { refraction: 'none' });
    dEl.push(p.elTrue - r.airless.el); dAz.push(angDiff(p.az, r.airless.az) * Math.cos(r.airless.el * Math.PI / 180));
    dK.push(p.illuminatedFraction * 100 - r.illumPct); dI.push(p.phaseAngle - r.phaseAngle);
    dD.push(p.angularDiameter * 3600 - r.angDiamArcsec); dR.push(p.distKm - r.distAU * E.AU_KM);
    if (r.refracted.el > 5) dElR.push(E.moonPosition(t, OBS).el - r.refracted.el);
  }
  check('E Moon elevation (airless) vs Horizons', stats(dEl).max, 0.01, 'deg', `(n=${dEl.length}, rms ${stats(dEl).rms.toFixed(4)})`);
  check('E Moon azimuth x cos(el) vs Horizons', stats(dAz).max, 0.01, 'deg', `(rms ${stats(dAz).rms.toFixed(4)})`);
  check('E Moon apparent elevation (el > 5) vs Horizons refracted', stats(dElR).max, 0.01, 'deg', `(n=${dElR.length})`);
  check('E Moon illuminated fraction vs Horizons Illu%', stats(dK).max, 0.1, 'pct-pt');
  check('E Moon phase angle vs Horizons S-T-O', stats(dI).max, 0.02, 'deg');
  check('E Moon angular diameter vs Horizons', stats(dD).max, 0.5, 'arcsec');
  check('E Moon topocentric distance vs Horizons', stats(dR).max, 50, 'km');
}

// ---------------------------------------------------------------- F/G: USNO year tables (UTC-8, HHMM)
const hhmm = (s) => s == null ? null : (+s.slice(0, 2)) * 60 + (+s.slice(2));
const locMin = (dt, tz) => dt == null ? null : Math.round(((dt.getTime() / 60000 + tz * 60) % 1440 + 1440) % 1440 * 1e6) / 1e6;
function compareUsno(name, table, fn, keyA, keyB, tolMin) {
  let n = 0, exact = 0, worst = 0, mism = 0; const tz = REF.usno.tz;
  for (const [mo, d, a, b] of table) {
    const ev = fn(2026, mo, d, tz, OBS);
    for (const [ref, ours] of [[a, ev[keyA]], [b, ev[keyB]]]) {
      if (ref == null && ours == null) continue;
      if (ref == null || ours == null) { mism++; continue; }
      const dm = Math.abs(Math.round(locMin(ours, tz)) - hhmm(ref)); // round ours to the nearest minute like USNO
      const dd = Math.min(dm, 1440 - dm); n++; if (dd === 0) exact++; worst = Math.max(worst, dd);
    }
  }
  check(`${name} (${n} events, ${(100 * exact / n).toFixed(1)}% identical to the minute)`, worst, tolMin, 'min', mism ? `; ${mism} present/absent mismatches` : '');
  if (mism) failures++;
}
compareUsno('F USNO sunrise/sunset 2026', REF.usno.riseSet, E.sunEvents, 'sunrise', 'sunset', 1);
compareUsno('F USNO civil twilight 2026', REF.usno.civil, E.sunEvents, 'civilDawn', 'civilDusk', 1);
compareUsno('F USNO nautical twilight 2026', REF.usno.nautical, E.sunEvents, 'nauticalDawn', 'nauticalDusk', 1);
compareUsno('F USNO astronomical twilight 2026', REF.usno.astronomical, E.sunEvents, 'astronomicalDawn', 'astronomicalDusk', 1);
compareUsno('G USNO moonrise/moonset 2026', REF.usno.moon, E.moonEvents, 'moonrise', 'moonset', 1);

// ---------------------------------------------------------------- H: USNO phases
{
  const ours = E.moonPhases(new Date('2025-12-31T00:00:00Z'), new Date('2027-01-02T00:00:00Z'));
  const d = []; let missing = 0;
  for (const p of REF.usno.phases) {
    const t = new Date(p.t).getTime();
    const m = ours.filter((o) => o.phase === p.phase).sort((a, b) => Math.abs(a.date - t) - Math.abs(b.date - t))[0];
    if (!m || Math.abs(m.date - t) > 86400000) { missing++; continue; }
    d.push((m.date - t) / 60000 - 0); // USNO minute is truncated or rounded: compare to the minute start
  }
  // USNO prints HH:MM. Our minus USNO has mean +0.65 min over 2026, consistent with USNO truncating seconds (+0.5)
  // plus ~10 s of our own bias; the spread comes mostly from the low-precision Sun longitude (<= 0.007 deg = ~50 s).
  const mean = d.reduce((a, b) => a + b, 0) / d.length;
  check(`H USNO Moon phases 2026 (n=${d.length}, ours - USNO: mean ${mean.toFixed(2)} min, range ${Math.min(...d).toFixed(2)}..${Math.max(...d).toFixed(2)})`, Math.max(...d.map(Math.abs)), 2, 'min', missing ? `; ${missing} missing` : '');
  if (missing) failures++;
}

// ---------------------------------------------------------------- I: Circular 171 sample
{
  const c = REF.c171; const t = new Date(c.date); const obs = { lat: c.lat, lon: c.lon, elevM: 0 };
  const I = E.naturalIlluminanceAt(t, obs, c.sky);
  const s = E.sunPosition(t, obs), m = E.moonPosition(t, obs);
  rows.push(`INFO | I C171 sample 1987-05-11 22:15 UT 58N 4W: ours sun az ${s.az.toFixed(1)} el ${s.el.toFixed(2)} -> ${I.sun.toFixed(4)} lx (printed 332 / -10 / 0.0278); moon az ${m.az.toFixed(1)} el ${m.el.toFixed(2)} ${(100 * m.illuminatedFraction).toFixed(0)}% -> ${I.moon.toFixed(4)} lx (printed 172 / 18 / 97% / 0.0317); total ${I.total.toFixed(4)} (printed 0.0600)`);
  // relative error |ours/printed - 1|; the printed run used the Circular's own 0.5-deg-class positions
  check('I C171 sample: solar illuminance vs printed 0.0278 lx', Math.abs(I.sun / c.out.sunLux - 1), 0.3, '(relative)');
  check('I C171 sample: lunar illuminance vs printed 0.0317 lx', Math.abs(I.moon / c.out.moonLux - 1), 0.15, '(relative)');
  check('I C171 sample: total illuminance vs printed 0.0600 lx', Math.abs(I.total / c.out.totalLux - 1), 0.2, '(relative)');
  // model sanity values quoted in the report: zenith sun, full moon at zenith
  const z = E.naturalIlluminance(90, 90, 180);
  rows.push(`INFO | I C171 model: sun at zenith ${z.sun.toFixed(0)} lx (paper: "124000 lux" upper end); full Moon at zenith ${z.moon.toFixed(3)} lx`);
}

console.log(rows.join('\n'));
console.log(failures ? `\n${failures} FAILED` : '\nALL PASSED');
process.exit(failures ? 1 : 0);
