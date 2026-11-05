// Gates A-SUN (state part) and A-CLK (docs/research/environment_spec.md §11.3) plus the EnvState preset vectors.
//  1. EnvState (js/env/state.js) reproduces the environment fields of all 14 presets in
//     tools/env/fixtures/env_presets.json (written by tools/env/env_spec_checks.py: the reference): Sun el/az, phase,
//     tower night, Moon el / lit, E_clear, D, E, EV100, ASOS night weight, σ day / night / blend, lower bound,
//     category, ceiling, RVR, cloud layers, sun-visible P, KC ratio, fog, precip (incl. the X9 clamp), wind, lightning.
//     Tolerances = the fixture's own rounding.
//  2. A-CLK: METAR selection by data clock: at 2026-09-23 17:51Z the current report is the SPECI 231722Z
//     (data/snapshot.js SNAPSHOT_METAR); a report observed after t_env is never selected; > 90 min -> stale.
//  3. Data clock: snapshot = cfg.snapshot.now; replay = relay dataNow + elapsed display time; ?t= override; light-mode
//     instants from sunEvents on the local (America/Los_Angeles, DST-correct) date; the old UTC-7 presets are gone.
//  4. Sun direction = ephemeris directionWorld (x east, y up, z south) = the old sunVector convention.
// Run: node tools/env/test_env_state.mjs   (exit 1 on failure)
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { buildEnvState, indexReports, selectReport, envHudLines } from '../../js/env/state.js';
import { DataClock, parseEnvQuery, lightModeTime, utcOffsetHours, localDate } from '../../js/env/clock.js';
import { sunEvents, sunPosition, SFO } from '../../js/env/ephemeris.js';
import { presetById, presetRunway, ENV_PRESETS } from '../../js/env/presets.js';
import { SNAPSHOT, SNAPSHOT_METAR } from '../../data/snapshot.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const P = JSON.parse(fs.readFileSync(path.join(HERE, 'fixtures', 'env_presets.json'), 'utf8')).presets;
let fails = 0, n = 0;
const check = (name, ok, info = '') => { n++; if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${info !== '' ? ' | ' + info : ''}`); };
const r = (x, k) => (x == null ? null : Math.round(x * 10 ** k) / 10 ** k);
const g3 = (x) => (x == null ? null : +Number(x).toPrecision(3));
const close = (a, b, tol) => (a == null && b == null) || (a != null && b != null && Math.abs(a - b) <= tol);

// ---------------------------------------------------------------------------------------------- 1. presets
let worst = { sunEl: 0, sunAz: 0 };
for (const p of P) {
  const raw = /^(METAR|SPECI)/.test(p.metar) ? p.metar : 'METAR ' + p.metar;
  const t = Date.parse(p.time_utc);
  const S = buildEnvState(t, { mode: 'preset', overridden: true, reports: [raw] });
  const pr = S.wx.params;
  const got = {
    sun_el_deg: r(S.sun.el, 2), sun_az_deg: r(S.sun.az, 1), phase: S.phase, tower_night: S.towerNight,
    moon_el_deg: r(S.moon.el, 1), moon_lit: r(S.moon.lit, 2), E_clear_lux: g3(S.natural.E_clear), cloud_divisor: r(S.natural.D, 2),
    E_lux: g3(S.natural.E), EV100_natural: r(S.exposure.ev100Target, 1), night_weight_asos: r(S.photocell.asosNightW, 2),
    sigma_day: g3(S.atm.sigmaDay), sigma_night: g3(S.atm.sigmaNight), sigma_blend: g3(S.atm.sigmaASOS), visibility_lower_bound: S.atm.visLowerBound,
    flight_category: S.wx.decoded.flight_category, ceiling_ft: S.wx.decoded.ceiling_ft,
    rvr28r_min_ft: ((S.wx.decoded.rvr || []).find(x => x.runway === '28R') || {}).min_ft ?? null,
    cloud_layers: pr.cloud_layers.map(L => ({ cover: L.cover, height_ft: L.height_ft, summation: L.summation, own_fraction: L.own_fraction })),
    sun_visible_probability: S.sunVisibleP, kc_ratio: S.kcRatio, fog: pr.fog, wind: pr.wind, lightning: pr.lightning,
    precip: pr.precip ? { ...pr.precip, ...(S.precip.kind === 'rain' ? { rate_mm_h_spec: S.precip.rateMmH } : {}) } : null,
  };
  const want = Object.fromEntries(Object.keys(got).map(k => [k, p[k]]));
  const bad = [];
  for (const k of Object.keys(got)) {
    const a = got[k], b = want[k];
    const ok = typeof b === 'number' ? close(a, b, k === 'sun_el_deg' ? 0.0101 : k === 'sun_az_deg' ? 0.101 : Math.abs(b) * 1e-9 + 1e-12) : JSON.stringify(a) === JSON.stringify(b);
    if (!ok) bad.push(`${k}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`);
  }
  worst.sunEl = Math.max(worst.sunEl, Math.abs(S.sun.el - p.sun_el_deg)); worst.sunAz = Math.max(worst.sunAz, Math.abs(S.sun.az - p.sun_az_deg));
  check(`preset ${p.id.padEnd(17)} EnvState = env_presets.json (${Object.keys(got).length} fields)`, bad.length === 0, bad.length ? bad.join('; ') : `sun el ${got.sun_el_deg}° ${got.phase}, E ${got.E_lux} lx, w ${got.night_weight_asos}, σ ${got.sigma_blend}`);
}
console.log(`INFO | preset Sun vs fixture (2-decimal rounding): max |Δel| ${worst.sunEl.toFixed(4)}°, max |Δaz| ${worst.sunAz.toFixed(3)}°`);

// ---------------------------------------------------------------------------------------------- 2. A-CLK
const snapReports = SNAPSHOT_METAR.split('\n');
const tSnap = SNAPSHOT.now;
check('snapshot clock = data/snapshot.js now (2026-09-23T17:51:25Z)', new DataClock({ mode: 'snapshot', snapshotNow: tSnap }).now(Date.now()).tEnv === tSnap, new Date(tSnap).toISOString());
const Ssnap = buildEnvState(tSnap, { mode: 'snapshot', reports: snapReports });
check('A-CLK: at 17:51Z the current report is the SPECI 231722Z (not the 1656Z METAR)', /^SPECI KSFO 231722Z/.test(Ssnap.wx.raw), Ssnap.wx.raw);
const t1700 = Date.parse('2026-09-23T17:00:00Z');
check('A-CLK: at 17:00Z the 1656Z METAR is current (the 1722Z SPECI is in the future)', /231656Z/.test(buildEnvState(t1700, { reports: snapReports }).wx.raw));
const t1550 = Date.parse('2026-09-23T15:50:00Z');
check('A-CLK: before the oldest report (15:50Z) nothing is selected', buildEnvState(t1550, { reports: snapReports }).wx.raw === null);
// exhaustive: every minute 15:00..20:00Z never selects a report observed after t_env
const idx = indexReports(snapReports, tSnap);
let viol = 0, cnt = 0;
for (let t = Date.parse('2026-09-23T15:00:00Z'); t <= Date.parse('2026-09-23T20:00:00Z'); t += 60e3) { const c = selectReport(idx, t); cnt++; if (c && c.obsMs > t) viol++; }
check('A-CLK: no selected report observed after t_env (301 minutes 15:00-20:00Z)', viol === 0, `${viol} violations / ${cnt}`);
const tLate = Date.parse('2026-09-23T19:00:00Z');
const Slate = buildEnvState(tLate, { reports: snapReports });
check('A-CLK: report older than 90 min -> stale, kept, age shown', Slate.wx.stale && /231722Z/.test(Slate.wx.raw) && Math.round(Slate.wx.ageMin) === 98, `age ${Slate.wx.ageMin.toFixed(1)} min`);
// relay JSON objects (obsTime s) are honoured over the DDhhmmZ resolution
const relayList = JSON.parse(fs.readFileSync(path.join(HERE, 'fixtures', 'awc_metar_ksfo_20261105T0300Z.json'), 'utf8'));
const tR = relayList[0].obsTime * 1000 + 5 * 60e3;
const SR = buildEnvState(tR, { mode: 'live', live: true, reports: relayList });
check('relay JSON reports: newest obsTime selected live', SR.wx.raw === relayList.slice().sort((a, b) => b.obsTime - a.obsTime)[0].rawOb.trim(), SR.wx.raw.slice(0, 40));
// replay clock
const wall0 = 1_800_000_000_000;
const traffic = { displayTime: (w) => w - 1500 };
const RC = new DataClock({ mode: 'live', replay: { speed: 2 }, traffic }); RC.setDataNow(tSnap, wall0);
const rc = RC.now(wall0 + 10_000);
check('replay clock: t_env = dataNow + (displayTime − wall at dataNow) × speed', rc.tEnv === tSnap + (10_000 - 1500) * 2 && rc.mode === 'replay', `${new Date(rc.tEnv).toISOString()}`);
const LC = new DataClock({ mode: 'live', traffic });
check('live clock: t_env = traffic.displayTime(wall)', LC.now(wall0).tEnv === wall0 - 1500);
const q = parseEnvQuery('?t=2026-09-24T02:30:00Z&wx=dusk&qa=env,prov&rwy=arr:28L,28R;dep:1L,1R');
check('?t= / ?wx= / ?qa= / ?rwy= parsed', q.t === Date.parse('2026-09-24T02:30:00Z') && q.wx === 'dusk' && q.qa.has('env') && q.qa.has('prov') && JSON.stringify(q.rwy.dep) === '["1L","1R"]');
const OC = new DataClock({ mode: 'snapshot', snapshotNow: tSnap, override: { t: q.t } });
const oc = OC.now();
check('?t= override: environment time moves, traffic time stays, overridden flag', oc.tEnv === q.t && oc.tTraffic === tSnap && oc.overridden);
check('?wx=<id>: 14 presets available, dusk preset time + runway input', ENV_PRESETS.length === 14 && presetById('dusk').time_utc === '2026-09-24T02:30:00Z' && presetRunway(presetById('dusk')).arr['28L'] === 'visual');

// ---------------------------------------------------------------------------------------------- 3. light modes
check('UTC offset from Intl: PDT −7 on 23 Sep 2026, PST −8 on 7 Jan 2025', utcOffsetHours(tSnap) === -7 && utcOffsetHours(Date.parse('2025-01-07T09:39:00Z')) === -8);
const ld = localDate(Date.parse('2026-09-24T02:30:00Z'));
check('local date of 2026-09-24T02:30Z is 23 Sep (PDT)', ld.y === 2026 && ld.m === 9 && ld.d === 23);
const E = sunEvents(2026, 9, 23, -7);
const dusk = lightModeTime('dusk', tSnap), night = lightModeTime('night', tSnap), day = lightModeTime('day', tSnap), dawn = lightModeTime('dawn', tSnap);
check('Dusk = civil dusk − 10 min (local 23 Sep)', dusk.t === Math.round(E.civilDusk.getTime() - 600e3), new Date(dusk.t).toISOString());
check('Night = nautical dusk + 60 min', night.t === Math.round(E.nauticalDusk.getTime() + 3600e3), new Date(night.t).toISOString());
check('Day = solar transit', day.t === Math.round(E.transit.getTime()), new Date(day.t).toISOString());
check('Dawn = midpoint of civil dawn and sunrise', dawn.t === Math.round((E.civilDawn.getTime() + E.sunrise.getTime()) / 2), new Date(dawn.t).toISOString());
const sDusk = sunPosition(new Date(dusk.t)), sNight = sunPosition(new Date(night.t)), sDay = sunPosition(new Date(day.t));
check('light-mode Sun: dusk −5…0°, night < −12°, day = transit elevation', sDusk.elTrue < 0 && sDusk.elTrue > -6 && sNight.elTrue < -12 && Math.abs(sDay.elTrue - E.transitEl) < 1e-6,
  `dusk ${sDusk.el.toFixed(2)}°, night ${sNight.el.toFixed(2)}°, day ${sDay.el.toFixed(2)}°`);
// the old presets were "13:00 / 19:45 / 22:30 local = UTC+7": in PST (Jan) that is 1 h off; the new rule follows the date
const jan = lightModeTime('dusk', Date.parse('2025-01-07T20:00:00Z'));
const Ej = sunEvents(2025, 1, 7, -8);
check('January dusk follows the PST date (not 19:45 + 7 h)', jan.t === Math.round(Ej.civilDusk.getTime() - 600e3) && new Date(jan.t).getUTCHours() !== 2, new Date(jan.t).toISOString());
const SC = new DataClock({ mode: 'snapshot', snapshotNow: tSnap }); SC.setLightMode('night');
check('DataClock light mode night -> overridden, Sun below −12°', SC.now().overridden && sunPosition(new Date(SC.now().tEnv)).elTrue < -12);

// ---------------------------------------------------------------------------------------------- 4. sun vector
const sv = (az, el) => [Math.sin(az * Math.PI / 180) * Math.cos(el * Math.PI / 180), Math.sin(el * Math.PI / 180), -Math.cos(az * Math.PI / 180) * Math.cos(el * Math.PI / 180)];   // js/world/textures.js sunVector
const dv = sv(Ssnap.sun.az, Ssnap.sun.el);
check('EnvState sun.dir = js/world/textures.js sunVector(az, el) convention (x east, y up, z south)', dv.every((v, i) => Math.abs(v - Ssnap.sun.dir[i]) < 1e-12), JSON.stringify(Ssnap.sun.dir.map(v => +v.toFixed(4))));
const hud = envHudLines(Ssnap);
check('?qa=env HUD lines carry tags and the METAR in use', hud.length >= 10 && hud.every(l => /\[[A-Z/+]+.*\]|t_env/.test(l)) && hud.some(l => l.includes('231722Z')), hud.length + ' lines');
console.log('INFO | snapshot HUD:\n  ' + hud.join('\n  '));
console.log(`\n${fails ? 'FAILED (' + fails + ')' : 'ALL PASSED'} (${n - fails}/${n})`);
process.exit(fails ? 1 : 0);
