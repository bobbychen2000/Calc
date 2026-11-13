// Forked from sfo3d/js/env/wx/taf.js @ a967f9b. Kept: the TAF decoder (unused at HWD: no KHWD TAF exists, aviationweather.gov returns [] - fork map 2.1). Changed: nothing. Dropped: nothing.
// TAF -> the prevailing forecast conditions at a time t (docs/research/environment_spec.md §3.3: "Beyond the latest METAR
// (time machine forward): use the TAF period in force (decode_taf, FM/TEMPO/BECMG/PROB) and label the scene 'forecast'").
// Input: a TAF decoded by js/env/wx/metar.js decodeTaf (port of tools/env/metar_decode.py). Output: a METAR-shaped
// decoded object (wind, visibility, weather, sky, ceiling, flight category) that render_params / EnvState consume.
// Pure ES module, no DOM; tests: tools/env/test_taf.mjs.
//
// Change-group semantics, FAA AIM 7-1-28 + "Forecast Change Indicators" (aim_html/chap7_section_1.html, fetched
// 2026-11-05, refs/cache/weather/aim/; V, quotes verbatim):
//  - FM: "used when a rapid change, usually occurring in less than one hour, in prevailing conditions is expected";
//    the date/hour/minute "the change is expected to begin and continues until the next change group or until the end
//    of the current forecast"; "Each 'FM' group contains all the required elements-wind, visibility, weather, and sky
//    condition. Weather will be omitted in 'FM' groups when it is not significant to aviation."
//    -> from its time on, an FM group REPLACES every prevailing element (no weather group = none).
//  - BECMG: "The gradual change will occur at an unspecified time within this time period. Only the changing forecast
//    meteorological conditions are included in BECMG groups. The omitted conditions are carried over from the previous
//    time group." ("The NWS does not use BECMG in the TAF.") -> its elements are merged into the prevailing set from the
//    END of its window, when the change is complete in any case (I: the time inside the window is unspecified).
//  - TEMPO: "expected to last for generally less than an hour at a time (occasional), and ... to occur during less than
//    half the time period"; PROB30/40: "probable condition in the period" -> never prevailing: listed in `groups` for the
//    QA HUD, not rendered (I: a deterministic scene shows the prevailing forecast).
//  - NSW: "NSW only refers to weather phenomena ... Omitted conditions, such as sky conditions, visibility, winds, etc.,
//    are carried over from the previous time group" -> clears the weather group only.
//  - Valid period "0918/1024": "valid from 18Z on the 9th to 24Z on the 10th" (hour 24 = 00Z of the next day).
// Times DDhh / DDhhmm are resolved from the issue time DDhhmmZ (its month / year from the reference time, as the METAR
// day group, js/env/wx/metar.js resolveDay); a day number below the issue day lies in the next month.
import { derive } from './metar.js';

const HOUR = 3600e3, DAY = 86400e3;
/** Issue time (ms) of 'DDhhmmZ' = the latest such instant not after ref + 1 day (Python _resolve_day rule). */
export function tafIssueMs(issued, refMs) {
  const m = /^(\d{2})(\d{2})(\d{2})Z$/.exec(issued || ''); if (!m) return null;
  const d = +m[1], h = +m[2], mi = +m[3];
  const ref = new Date(refMs);
  let y = ref.getUTCFullYear(), mo = ref.getUTCMonth();
  for (let k = 0; k < 3; k++) {
    const c = Date.UTC(y, mo, d, h, mi);
    if (new Date(c).getUTCDate() === d && c - refMs <= DAY) return c;
    mo -= 1; if (mo < 0) { mo = 11; y -= 1; }
  }
  return null;
}
/** 'DDhh' or 'DDhhmm' -> ms, in the issue month (or the next one when the day number is below the issue day). */
export function tafTimeMs(code, issueMs) {
  if (!code || issueMs == null) return null;
  const d = +code.slice(0, 2), h = +code.slice(2, 4), mi = code.length >= 6 ? +code.slice(4, 6) : 0;
  const iss = new Date(issueMs);
  let y = iss.getUTCFullYear(), mo = iss.getUTCMonth();
  if (d < iss.getUTCDate()) { mo += 1; if (mo > 11) { mo = 0; y += 1; } }
  return Date.UTC(y, mo, d, 0, 0) + h * HOUR + mi * 60e3;          // h = 24 -> 00Z of the next day (AIM 7-1-28)
}
const ELEMENTS = ['wind', 'visibility', 'weather', 'sky'];
const clone = (x) => (x == null ? x : JSON.parse(JSON.stringify(x)));
const groupText = (p) => (p.change === 'BASE' ? 'BASE' : p.change === 'FM' ? 'FM' + p.from : `${p.change}${p.prob && p.change === 'PROB' ? p.prob : ''} ${p.from}/${p.to}`);

/** Prevailing forecast at tMs from a decoded TAF (decodeTaf). Returns null when the TAF is unusable or t lies outside
 *  its valid period or before its issue; otherwise {d (METAR-shaped decoded weather), key, issuedMs, validFromMs,
 *  validToMs, applied [group ids that set the prevailing state], groups [TEMPO / PROB in force at t: not rendered],
 *  text (the prevailing elements, METAR-like), reason}. */
export function tafAt(taf, tMs, refMs = tMs) {
  if (!taf || taf.error || !taf.periods || !taf.periods.length || !taf.valid) return null;
  const issuedMs = tafIssueMs(taf.issued, refMs);
  if (issuedMs == null || tMs < issuedMs) return null;              // never a forecast issued after t
  const [v0, v1] = taf.valid.split('/');
  const validFromMs = tafTimeMs(v0, issuedMs), validToMs = tafTimeMs(v1, issuedMs);
  if (validFromMs == null || validToMs == null || tMs < validFromMs || tMs >= validToMs) return null;
  const cur = { wind: null, visibility: null, weather: [], sky: [] };
  const applied = [], groups = [];
  for (const p of taf.periods) {
    const from = p.change === 'BASE' ? validFromMs : tafTimeMs(p.from, issuedMs);
    const to = p.to ? tafTimeMs(p.to, issuedMs) : null;
    if (p.change === 'BASE' || p.change === 'FM') {
      if (from != null && from <= tMs) {                              // replaces every element
        cur.wind = clone(p.wind) || null; cur.visibility = clone(p.visibility) || null;
        cur.weather = (clone(p.weather) || []).filter(w => !w.nsw); cur.sky = clone(p.sky) || [];
        applied.length = 0; applied.push(groupText(p));
      }
    } else if (p.change === 'BECMG') {
      if (to != null && to <= tMs) {                                  // change complete at the window end (I)
        for (const k of ELEMENTS) if (p[k] !== undefined) cur[k] = k === 'weather' ? (clone(p[k]) || []).filter(w => !w.nsw) : clone(p[k]);
        applied.push(groupText(p));
      }
    } else if (from != null && to != null && from <= tMs && tMs < to) {
      groups.push({ id: groupText(p), change: p.change, prob: p.prob, wind: p.wind || null, visibility: p.visibility || null, weather: p.weather || null, sky: p.sky || null });
    }
  }
  const d = { raw: `${taf.raw.split(' ').slice(0, 4).join(' ')} … ${applied.join(' + ')}`, type: 'TAF', station: taf.station || null,
    modifier: taf.modifier || [], rmk: {}, wind: cur.wind, visibility: cur.visibility, weather: cur.weather, sky: cur.sky, forecast: true };
  if (!d.wind) delete d.wind; if (!d.visibility) delete d.visibility;
  derive(d);                                                          // ceiling (JO 7900.5E 10.4a) + flight category
  const fmtWind = (w) => (!w ? '' : (w.calm ? '00000KT' : (w.variable && w.dir_true_deg == null ? 'VRB' : String(w.dir_true_deg).padStart(3, '0')) + String(w.speed_kt).padStart(2, '0') + (w.gust_kt ? 'G' + w.gust_kt : '') + 'KT'));
  const text = [fmtWind(cur.wind), cur.visibility ? cur.visibility.raw : '', ...cur.weather.map(w => w.raw), ...cur.sky.map(s => s.raw || (s.cover + (s.height_ft != null ? String(s.height_ft / 100).padStart(3, '0') : '') + (s.type || '')))].filter(Boolean).join(' ');
  return { d, key: `TAF ${taf.issued} ${applied.join('+')}`, issuedMs, validFromMs, validToMs, applied: applied.slice(), groups, text,
    reason: 'latest report stale (> 90 min) or none: prevailing TAF conditions (AIM 7-1-28 FM / BECMG; TEMPO / PROB not rendered)' };
}
