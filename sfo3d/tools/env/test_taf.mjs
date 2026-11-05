// Tests for js/env/wx/taf.js (prevailing TAF conditions at a time, environment_spec.md §3.3 "beyond the latest METAR")
// and its use in EnvState. Cases: the KSFO TAF in force at the snapshot time (NWS TAFSFO 231727Z, IEM AFOS archive),
// the AIM 7-1-28 example TAF KORD 051130Z (FM, TEMPO, PROB40, BECMG + NSW; FAA AIM chap7_section_1, fetched
// 2026-11-05), a month rollover, and a sweep over every cached KSFO TAF. No GPU, no network.
//   node tools/env/test_taf.mjs
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
import { decodeTaf } from '../../js/env/wx/metar.js';
import { tafAt, tafTimeMs, tafIssueMs } from '../../js/env/wx/taf.js';
import { buildEnvState, envHudLines } from '../../js/env/state.js';
import { SNAPSHOT_TAF } from '../../data/sfo_env_presets.js';
import { SNAPSHOT_METAR } from '../../data/snapshot.js';

const HERE = path.dirname(fileURLToPath(import.meta.url)), ROOT = path.join(HERE, '..', '..');
let fails = 0, n = 0;
const check = (name, ok, got) => { n++; if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${got !== undefined ? ' | ' + (typeof got === 'string' ? got : JSON.stringify(got)) : ''}`); };
const T = (s) => Date.parse(s);
const at = (taf, t) => tafAt(taf, T(t));
const sum = (r) => r && { applied: r.applied.join('+'), text: r.text, ceil: r.d.ceiling_ft, cat: r.d.flight_category, groups: r.groups.map(g => g.id) };

// ---- 1. the snapshot TAF (valid 2318/2424)
const S = decodeTaf(SNAPSHOT_TAF.raw);
check('snapshot TAF issue time resolved (231727Z, Sep 2026)', tafIssueMs(S.issued, T('2026-09-24T04:00Z')) === T('2026-09-23T17:27Z'));
check('valid end "2424" = 25 Sep 00Z (AIM: "to 24Z on the 10th")', tafTimeMs('2424', T('2026-09-23T17:27Z')) === T('2026-09-25T00:00Z'));
check('17:00Z: before the issue time -> none', at(S, '2026-09-23T17:00Z') === null);
check('17:51Z (snapshot): issued but before the valid period (18Z) -> none', at(S, '2026-09-23T17:51Z') === null);
let r = at(S, '2026-09-23T18:00Z');
check('18:00Z -> base VRB05KT P6SM SCT200', r && r.applied.join() === 'BASE' && r.text === 'VRB05KT P6SM SCT200', sum(r));
r = at(S, '2026-09-23T19:59Z'); check('19:59Z -> still base', r && r.applied.join() === 'BASE', sum(r));
r = at(S, '2026-09-23T20:00Z'); check('20:00Z -> FM232000 29015KT P6SM FEW200', r && r.applied.join() === 'FM232000' && r.text === '29015KT P6SM FEW200', sum(r));
r = at(S, '2026-09-24T04:01:07Z'); check('24 Sep 04:01Z (light mode Night) -> FM232000', r && r.applied.join() === 'FM232000' && r.d.wind.dir_true_deg === 290 && r.d.wind.speed_kt === 15, sum(r));
r = at(S, '2026-09-24T11:30Z'); check('24 Sep 11:30Z -> FM241100 BKN010: ceiling 1000 ft, MVFR', r && r.applied.join() === 'FM241100' && r.d.ceiling_ft === 1000 && r.d.flight_category === 'MVFR', sum(r));
r = at(S, '2026-09-24T23:59Z'); check('24 Sep 23:59Z -> FM242100', r && r.applied.join() === 'FM242100', sum(r));
check('25 Sep 00:00Z: end of the valid period -> none', at(S, '2026-09-25T00:00Z') === null);

// ---- 2. AIM 7-1-28 example (FM, TEMPO, PROB40, BECMG, NSW), dated November 2026 for the month
const K = decodeTaf('TAF KORD 051130Z 0512/0618 14008KT 5SM BR BKN030 TEMPO 0513/0516 1 1/2SM BR FM051600 16010KT P6SM SKC FM052300 20013G20KT 4SM SHRA OVC020 PROB40 0600/0606 2SM TSRA OVC008CB BECMG 0606/0608 21015KT P6SM NSW SCT040');
r = at(K, '2026-11-05T14:00Z');
check('AIM KORD 05 14Z -> base 14008KT 5SM BR BKN030; TEMPO listed, not applied', r && r.applied.join() === 'BASE' && r.text === '14008KT 5SM BR BKN030' && r.groups.map(g => g.id).join() === 'TEMPO 0513/0516', sum(r));
r = at(K, '2026-11-05T16:00Z'); check('AIM KORD 05 16Z -> FM051600 (SKC, no weather)', r && r.applied.join() === 'FM051600' && r.d.weather.length === 0 && r.d.flight_category === 'VFR', sum(r));
r = at(K, '2026-11-06T03:00Z');
check('AIM KORD 06 03Z -> FM052300 20013G20KT 4SM SHRA OVC020; PROB40 listed, not applied', r && r.applied.join() === 'FM052300' && r.text === '20013G20KT 4SM SHRA OVC020' && r.groups.map(g => g.id).join() === 'PROB40 0600/0606', sum(r));
r = at(K, '2026-11-06T07:00Z'); check('AIM KORD 06 07Z (inside the BECMG window) -> FM052300 unchanged', r && r.applied.join() === 'FM052300' && r.d.weather.length === 1, sum(r));
r = at(K, '2026-11-06T08:00Z');
check('AIM KORD 06 08Z (BECMG complete) -> 21015KT P6SM, NSW clears the weather only, SCT040, no ceiling', r && r.applied.join('+') === 'FM052300+BECMG 0606/0608' && r.text === '21015KT P6SM SCT040' && r.d.ceiling_ft === null, sum(r));

// ---- 3. month rollover (issue on the 30th, valid from the 1st of the next month)
const M = decodeTaf('TAF KSFO 302320Z 0100/0206 28010KT P6SM SKC FM010600 30005KT P6SM FEW010');
check('rollover: issue 302320Z with ref 1 Oct -> 30 Sep 23:20Z', tafIssueMs(M.issued, T('2026-10-01T03:00Z')) === T('2026-09-30T23:20Z'));
r = at(M, '2026-10-01T07:00Z'); check('rollover: 1 Oct 07Z -> FM010600', r && r.applied.join() === 'FM010600', sum(r));
check('rollover: 30 Sep 23:50Z -> before the valid period', at(M, '2026-09-30T23:50Z') === null);

// ---- 4. sweep: every cached KSFO TAF (IEM 23 Sep 2026 + the live AWC sample), hourly over its valid period
const tafs = [];
const iem = path.join(ROOT, 'refs', 'cache', 'weather', 'iem_afos_TAFSFO_20260923.txt');
if (fs.existsSync(iem)) for (const m of fs.readFileSync(iem, 'utf8').matchAll(/(TAF(?: AMD| COR)?\s+KSFO\s+\d{6}Z.*?)=/gs)) tafs.push([m[1].split(/\s+/).join(' '), '2026-09-23T23:59Z']);
for (const t of JSON.parse(fs.readFileSync(path.join(HERE, 'fixtures', 'awc_taf_ksfo_20261105T0300Z.json'), 'utf8'))) tafs.push([t.rawTAF, '2026-11-05T03:00Z']);
let hours = 0, bad = [];
for (const [raw, ref] of tafs) {
  const D = decodeTaf(raw); const iss = tafIssueMs(D.issued, T(ref)); const [v0, v1] = D.valid.split('/');
  const a = tafTimeMs(v0, iss), b = tafTimeMs(v1, iss);
  for (let t = a; t < b; t += 3600e3) {
    hours++; const x = tafAt(D, t, T(ref));
    if (t < iss) { if (x !== null) bad.push(raw.slice(0, 30) + ' before issue'); continue; }
    if (!x || !x.applied.length || !x.d.wind || !x.d.visibility) bad.push(raw.slice(0, 30) + ' @' + new Date(t).toISOString());
  }
}
check(`sweep: ${tafs.length} cached KSFO TAFs, ${hours} valid hours: a prevailing set with wind + visibility every hour after issue`, tafs.length >= 11 && bad.length === 0, bad.slice(0, 3));

// ---- 5. EnvState: forecast only beyond the latest METAR (stale > 90 min or none), labelled, provenance I
const reports = SNAPSHOT_METAR.split('\n').filter(Boolean);
check('data/snapshot.js SNAPSHOT_METAR read', !!reports && reports.length === 3, reports && reports.length);
const env = (t) => buildEnvState(T(t), { mode: 'snapshot', reports, taf: SNAPSHOT_TAF.raw });
let E = env('2026-09-23T17:51:25Z');
check('EnvState 17:51Z: SPECI 231722Z current, no forecast, wx prov V', E.wx.forecast === null && /231722Z/.test(E.wx.raw) && /^V/.test(E.prov.wx), E.prov.wx);
E = env('2026-09-23T18:52:30Z');
check('EnvState 18:52Z: SPECI 31 -> 90.5 min old (stale) -> forecast base VRB05KT P6SM SCT200', E.wx.stale && E.wx.forecast && E.wx.forecast.applied.join() === 'BASE' && E.wind.fromTrue === null && E.clouds.map(c => c.cover + c.baseFt).join() === 'SCT20000', E.wx.forecast && E.wx.forecast.text);
E = env('2026-09-24T04:01:06.943Z');
check('EnvState light-mode Night (24 Sep 04:01Z): forecast FM232000 drives wind 290°T 15 kt, FEW200, stars visible, prov I', E.wx.forecast && E.wind.fromTrue === 290 && Math.abs(E.wind.speed - 15 * 1852 / 3600) < 1e-9 && E.clouds.length === 1 && E.clouds[0].baseFt === 20000 && E.nightSky.stars === 'visible' && /^I/.test(E.prov.wx), { wind: E.wind.fromTrue, clouds: E.clouds.map(c => c.cover + c.baseFt), prov: E.prov.wx });
check('EnvState forecast: P6SM is a lower bound -> clear-air σ', E.atm.visLowerBound && E.atm.sigmaSurface <= 3.3e-5 + 1e-12, E.atm.sigmaSurface);
check('EnvState forecast: runway configuration from the forecast wind (290° 15 kt -> 28 / West plan, tailwind rule)', E.runway.plan === 'west' && /West Plan/.test(E.runway.source), E.runway.source);
const hud = envHudLines(E).join('\n');
check('?qa=env HUD shows the FORECAST line with the TAF issue and group', /FORECAST TAF 231727Z FM232000: 29015KT P6SM FEW200 \[I\]/.test(hud), hud.split('\n').find(l => l.startsWith('FORECAST')));
E = env('2026-09-25T01:00Z');
check('EnvState 25 Sep 01Z: the TAF has expired -> no forecast, the stale SPECI is kept and flagged', E.wx.forecast === null && E.wx.stale && /231722Z/.test(E.wx.raw), E.wx.ageMin);
E = buildEnvState(T('2026-09-23T15:00Z'), { mode: 'snapshot', reports, taf: SNAPSHOT_TAF.raw });
check('EnvState 15:00Z: no report yet and the TAF not issued -> neither (clear-air defaults)', E.wx.forecast === null && E.wx.raw === null);

console.log(fails ? `\n${fails} FAILED of ${n}` : `\nALL PASSED (${n}/${n})`);
process.exit(fails ? 1 : 0);
