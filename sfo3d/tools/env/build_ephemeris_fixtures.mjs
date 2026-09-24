// tools/env/build_ephemeris_fixtures.mjs
// Builds tools/env/fixtures/ephemeris_ref.json, the reference data that tools/env/test_ephemeris.mjs checks
// tools/env/ephemeris.mjs against. It reads raw downloads in refs/cache/sun_night/ (gitignored) and stores only the
// numbers needed by the test, with the URL, fetch date and SHA-256 of every raw file.
//
// Raw sources (all fetched 2026-09-24):
//   horizons/{sun,moon}_<date>_{airless,refracted}.json  JPL Horizons API, observer table, SITE_COORD = SFO ARP,
//        quantities 2,4,10,13,20,24, hourly for 24 h on 5 dates. All raw files: python3 tools/env/fetch_ephemeris_refs.py
//   noaa_main.js            https://gml.noaa.gov/grad/solcalc/main.js (the NOAA/GML Solar Calculator's own code).
//                           Its calculation functions are run here in a Node vm to produce the "NOAA values".
//   usno_year_task{0,1,2,3,4}.html  https://aa.usno.navy.mil/calculated/rstt/year?ID=AA&year=2026&task=N
//                           &lat=37.6188&lon=-122.3754&tz=8.00&tz_sign=-1 (0 sun rise/set, 1 moon rise/set,
//                           2 civil, 3 nautical, 4 astronomical twilight; zone 8 h west, no daylight time).
//   usno_moonphases_2026.json       https://aa.usno.navy.mil/api/moon/phases/year?year=2026 (UT)
//   usno_rstt_<date>.json           https://aa.usno.navy.mil/api/rstt/oneday?date=...&coords=...&tz=-8&dst=true
// Run: node tools/env/build_ephemeris_fixtures.mjs
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const RAW = path.join(ROOT, 'refs/cache/sun_night');
const OUT = path.join(HERE, 'fixtures/ephemeris_ref.json');
const SFO = { lat: 37.6188056, lon: -122.3754167, elevM: 4.0 };
const DATES = [['2026-02-11', -8], ['2026-06-21', -7], ['2026-09-23', -7], ['2026-11-03', -8], ['2026-12-21', -8]];
const sources = [];
const read = (rel, url) => {
  const p = path.join(RAW, rel); const buf = fs.readFileSync(p);
  sources.push({ file: 'refs/cache/sun_night/' + rel, url, fetched: '2026-09-24', sha256: crypto.createHash('sha256').update(buf).digest('hex') });
  return buf.toString('utf8');
};
const MON = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };

// ---------------------------------------------------------------------------------------------- Horizons
function horizons(body, date, refr) {
  const rel = `horizons/${body}_${date}_${refr}.json`;
  const js = JSON.parse(read(rel, 'https://ssd.jpl.nasa.gov/api/horizons.api (query in _url field of the raw file)'));
  const r = js.result; const a = r.indexOf('$$SOE'), b = r.indexOf('$$EOE');
  return r.slice(a + 5, b).trim().split('\n').map((line) => {
    const c = line.split(',').map((s) => s.trim());
    const m = /(\d{4})-(\w{3})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/.exec(c[0]);
    const t = new Date(Date.UTC(+m[1], MON[m[2]], +m[3], +m[4], +m[5], +m[6])).toISOString();
    return { t, ra: +c[4], dec: +c[5], az: +c[6], el: +c[7], illum: +c[8], angDiamArcsec: +c[9], distAU: +c[10], sto: +c[12] };
  });
}
const hz = { sun: [], moon: [] };
for (const [d] of DATES) for (const body of ['sun', 'moon']) {
  const A = horizons(body, d, 'airless'), R = horizons(body, d, 'refracted');
  A.forEach((a, i) => {
    const r = R[i]; if (r.t !== a.t) throw new Error('epoch mismatch');
    const row = { t: a.t, airless: { az: a.az, el: a.el, ra: a.ra, dec: a.dec }, refracted: { az: r.az, el: r.el }, distAU: a.distAU, angDiamArcsec: a.angDiamArcsec };
    if (body === 'moon') Object.assign(row, { illumPct: a.illum, phaseAngle: a.sto });
    hz[body].push(row);
  });
}

// ---------------------------------------------------------------------------------------------- NOAA (their code)
const ctx = vm.createContext({ Math });
vm.runInContext(read('noaa_main.js', 'https://gml.noaa.gov/grad/solcalc/main.js'), ctx);
const noaaAzel = hz.sun.map((h) => {
  const jd = new Date(h.t).getTime() / 86400000 + 2440587.5;
  const d = new Date(h.t); const mins = d.getUTCHours() * 60 + d.getUTCMinutes() + d.getUTCSeconds() / 60;
  const T = ctx.calcTimeJulianCent(jd);
  const r = ctx.calcAzEl(T, mins, SFO.lat, SFO.lon, 0);
  return { t: h.t, az: r.azimuth, el: r.elevation };
});
const noaaDays = DATES.map(([d, tz]) => {
  const [y, m, dd] = d.split('-').map(Number); const jd = ctx.getJD(y, m, dd);
  const rise = ctx.calcSunriseSet(1, jd, SFO.lat, SFO.lon, tz), set = ctx.calcSunriseSet(0, jd, SFO.lat, SFO.lon, tz);
  return { date: d, tz, sunriseMin: rise.timelocal, sunsetMin: set.timelocal, noonMin: ctx.calcSolNoon(jd, SFO.lon, tz), sunriseAz: rise.azimuth, sunsetAz: set.azimuth };
});

// ---------------------------------------------------------------------------------------------- USNO
function usnoYear(task) {
  const html = read(`usno_year_task${task}.html`, `https://aa.usno.navy.mil/calculated/rstt/year?ID=AA&year=2026&task=${task}&lat=37.6188&lon=-122.3754&label=SFO&tz=8.00&tz_sign=-1&submit=Get+Data`);
  const pre = html.slice(html.indexOf('<pre'), html.indexOf('</pre>')).replace(/<[^>]+>/g, '');
  const rows = [];
  for (const line of pre.split('\n')) {
    if (!/^\d\d  /.test(line)) continue;
    const day = +line.slice(0, 2);
    for (let mo = 0; mo < 12; mo++) {
      const a = line.slice(4 + 11 * mo, 8 + 11 * mo).trim(), b = line.slice(9 + 11 * mo, 13 + 11 * mo).trim();
      if (!a && !b) continue;
      rows.push([mo + 1, day, a || null, b || null]);
    }
  }
  return rows;
}
const usno = {
  tz: -8, note: 'Local standard time (UTC-8) all year; HHMM strings; null = no event that day. Rounded to the minute.',
  riseSet: usnoYear(0), civil: usnoYear(2), nautical: usnoYear(3), astronomical: usnoYear(4), moon: usnoYear(1),
  phases: JSON.parse(read('usno_moonphases_2026.json', 'https://aa.usno.navy.mil/api/moon/phases/year?year=2026')).phasedata
    .map((p) => ({ phase: p.phase, t: new Date(Date.UTC(p.year, p.month - 1, p.day, +p.time.slice(0, 2), +p.time.slice(3, 5))).toISOString() })),
  oneday: DATES.map(([d]) => {
    const f = d === '2026-09-23' ? 'usno_rstt_20260923.json' : `usno_rstt_${d}.json`;
    const js = JSON.parse(read(f, `https://aa.usno.navy.mil/api/rstt/oneday?date=${d}&coords=37.6188,-122.3754&tz=-8&dst=true`)).properties.data;
    return { date: d, isdst: js.isdst, fracillum: js.fracillum, curphase: js.curphase, sundata: js.sundata, moondata: js.moondata };
  }),
};

// ---------------------------------------------------------------------------------------------- Circular 171 sample run
// Figure 3 (p. 5): "AT -4.0 DEG LONGITUDE, 58.0 DEG LATITUDE, DATA FOR 1987, MONTH 5, DAY 11, AT 2215 HOURS",
// sky condition 1. Output: solar azimuth 332, altitude -10, illuminance 0.0278 lx; lunar azimuth 172, altitude 18,
// illuminance 0.0317 lx, 97 % illuminated; total 0.0600 lx. The program's longitude is entered as -4.0 for 4 deg W
// with zone time = UT: the printed solar meridian passage 1212 matches 4 deg W in UT (12:00 + 16 min - equation of
// time 3.6 min on 11 May = 12:12.4). Source: https://archive.org/details/DTIC_ADA182110 (PDF p. 5, code pp. 20-23).
const c171 = { date: '1987-05-11T22:15:00Z', lat: 58.0, lon: -4.0, sky: 1,
  out: { sunAz: 332, sunAlt: -10, sunLux: 0.0278, moonAz: 172, moonAlt: 18, moonLux: 0.0317, moonPct: 97, totalLux: 0.0600 } };

const out = { meta: { generated: new Date().toISOString(), observer: SFO, dates: DATES, sources, note: 'Built by tools/env/build_ephemeris_fixtures.mjs; see docs/research/sun_night.md' },
  horizons: hz, noaa: { azel: noaaAzel, days: noaaDays }, usno, c171 };
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('wrote', OUT, (fs.statSync(OUT).size / 1024).toFixed(1), 'KiB;', hz.sun.length, 'sun +', hz.moon.length, 'moon Horizons epochs;',
  usno.riseSet.length, 'USNO days;', usno.phases.length, 'phases');
