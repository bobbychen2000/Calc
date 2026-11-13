// ATC link-out (hwd3d Phase 2, P4). Replaces sfo3d/js/live/atc.js @ a967f9b (LiveATC KSFO mounts from an Internet
// Archive capture, per-feed player links, "likely on this frequency" roles, an audio-delay slider): fork map 1.1
// "replace (D2: a single link to https://www.liveatc.net/search/?icao=KHWD)".
//
// D2 (docs/PLAN.md 6a): a link-out only, to LiveATC's KHWD search page. No embedded stream, no mount names (LiveATC's
// feed list and terms answer HTTP 403 to automated reads, PLAN 2 / 5 risk 2, so none is verified), no synthetic audio,
// no audio-delay coupling (nothing is played here).
//
// Shown with the link (each value with its source; all verified in docs/PLAN.md section 1, 2026-11-12):
//  - tower hours 0700-2100 local: FAA NASR ATC_BASE (cycle 2026-10-29); FAA-operated ATCT, call "HAYWARD";
//  - when the tower is closed: CTAF 120.2, runway 10L/28R closed, MIRL 10R/28L preset low (pilot-controlled): NASR
//    APT_RMK / FRQ;
//  - frequencies: NASR FRQ (cycle 2026-10-29) and AL-5015; 118.9 is the secondary tower frequency, listed in NASR and
//    the Chart Supplement ("TOWER 120.2 118.9 (1500-0500Z‡)"), not on the diagram (PLAN 1, corrected in the Phase 1 review).
// Tower open / closed at a given instant: js/live/classifier.js towerStatus (P3; America/Los_Angeles local time via Intl).
import { towerStatus } from './classifier.js';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const LIVEATC_URL = 'https://www.liveatc.net/search/?icao=KHWD';
export const TOWER = { hours: '07:00–21:00', open: 7, close: 21, call: 'Hayward Tower', src: 'FAA NASR ATC_BASE, cycle 2026-10-29' };
export const CLOSED_RULES = ['Runway 10L/28R is closed', 'CTAF 120.2', 'Runway 10R/28L edge lights (MIRL) preset low, pilot-controlled'];
export const FREQ_SRC = 'FAA NASR FRQ (cycle 2026-10-29), FAA Chart Supplement SW (29 Oct 2026), airport diagram AL-5015';
export const FREQS = [
  { name: 'Tower', mhz: 120.2, note: 'primary; CTAF when the tower is closed', ctaf: true },
  { name: 'Tower', mhz: 118.9, note: 'secondary (Chart Supplement: 1500–0500Z‡)' },
  { name: 'Ground', mhz: 121.4 },
  { name: 'Clearance Delivery', mhz: 128.05 },
  { name: 'ATIS', mhz: 126.7, note: '24 h' },
  { name: 'NorCal Approach / Departure', mhz: 124.4, note: 'primary' },
  { name: 'UNICOM', mhz: 122.95 },
];
const fmtMhz = (f) => f.toFixed(Math.round(f * 100) % 10 ? 2 : 1);
/** tower state at scene time t (ms): {open, label, chip} */
export function towerAt(t) {
  const open = t != null && Number.isFinite(t) ? towerStatus(t) === 'open' : null;
  return { open, label: open == null ? '' : open ? 'Tower open' : 'Tower closed · CTAF 120.2', chip: open == null ? '' : open ? 'TWR' : 'CTAF' };
}
/** the ATC sheet: the LiveATC link, the tower state at the scene time, tower hours, frequencies */
export function atcHtml({ t = null, mode = 'live' } = {}) {
  const T = towerAt(t);
  const when = mode === 'live' ? 'now' : 'at the scene time (recorded)';
  return `<h3>ATC · Hayward (KHWD)</h3>
<div class="tw ${T.open ? 'open' : 'closed'}"><b>${esc(T.open ? 'Tower open' : 'Tower closed')}</b> <span class="dim">${esc(when)}</span>
${T.open === false ? `<ul>${CLOSED_RULES.map(r => `<li>${esc(r)}</li>`).join('')}</ul>` : ''}</div>
<p>${esc(TOWER.call)} is staffed <b>${esc(TOWER.hours)}</b> local time (Pacific). Outside these hours pilots self-announce on the CTAF, <b class="mono">120.2</b>.</p>
<p><a class="listen" href="${LIVEATC_URL}" target="_blank" rel="noopener">Listen on LiveATC.net ↗</a></p>
<p class="small dim">Opens LiveATC's own KHWD page in a new tab. This app never plays, relays or records ATC audio${mode !== 'live' ? '; LiveATC is live, so it does not match a recorded scene' : ''}.</p>
<h4>Frequencies</h4>
<table class="rt"><tbody>${FREQS.map(f => `<tr><td>${esc(f.name)}</td><td class="mono"><b>${fmtMhz(f.mhz)}</b></td><td class="dim small">${esc(f.note || '')}</td></tr>`).join('')}</tbody></table>
<p class="small dim">Source: ${esc(FREQ_SRC)}; tower hours: ${esc(TOWER.src)}. Not for navigation.</p>`;
}
