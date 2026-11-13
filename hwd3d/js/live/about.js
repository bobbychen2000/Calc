// About panel and the always-visible credit line (hwd3d Phase 2, P4). Replaces sfo3d/js/live/about.js @ a967f9b (SFO
// sources, airliner models, flysfo gates, VRS routes, the FAA registry): fork map 1.1 "replace (notices of
// docs/ATTRIBUTION.md)". Kept from it: the two exports (aboutHtml for the About sheet, attribHtml for the footer line,
// sfo3d realtime_feeds.md s.1: the ADS-B notice must be visible wherever live data is shown) and the "what is real / what
// is approximate" structure.
//
// NOTICES = the block "Notices to show in the app (About / credits panel) and in any distribution" of
// docs/ATTRIBUTION.md, word for word (the two ODbL lines are required: ODbL 4.3 for the app as a Produced Work; the
// Mictronics line is required by ODC-By 4.2-4.3; the FAA and USDA lines are courtesy credits, USDA asks for its credit).
// Added here, each with its source:
//  - adsb.fi, only while the relay uses it (live only): its README @ 9fe1c9a "You must cite adsb.fi and include a link to
//    our home page", "personal, non-commercial use only" (quoted by P1, docs/phase2_relay.md section 3);
//  - weather: NOAA / NWS Aviation Weather Center METAR KHWD (US Government work; aviationweather.gov, P1 section 3);
//  - the ground texture is USDA NAIP 2024 imagery (P2 docs/phase2_world.md section 3; same USDA credit as the measurement
//    line; P2 asks the orchestrator to confirm the NAIP licence texts before Phase 2 publishes credits);
//  - LiveATC.net: linked, never embedded (D2; its terms could not be read: HTTP 403 to automated requests, PLAN 2).
// Not used and therefore not credited: Google imagery (never), the FAA aircraft registry (not obtained), the City of
// Hayward layout map (reference only).
import { LIVEATC_URL, TOWER, FREQS } from './atc.js';

const A = (href, text) => `<a href="${href}" target="_blank" rel="noopener">${text}</a>`;
const ODBL = 'https://opendatacommons.org/licenses/odbl/1-0/';
const ODCBY = 'https://opendatacommons.org/licenses/by/1-0/';
// docs/ATTRIBUTION.md "Notices to show in the app", 2026-11-13 (one entry per block, links as written there)
export const NOTICES = [
  `Airfield data © OpenStreetMap contributors, available under the Open Database License (ODbL 1.0) - ${A('https://www.openstreetmap.org/copyright', 'https://www.openstreetmap.org/copyright')}`,
  `Contains information from ADSB.lol (${A('https://adsb.lol', 'https://adsb.lol')}), made available under the ODbL 1.0 (${A(ODBL, ODBL)})`,
  `The Hayward airport data set (<code>data/hwd_airport.json</code> / <code>.js</code>) is a derived database made available under the Open Database License 1.0. The file, and the tools and pinned inputs that build it, are in this repository.`,
  `Imagery measurements: USDA NAIP 2024 / 2022 (USDA Farm Production and Conservation Business Center, Geospatial Enterprise Operations), public domain`,
  `Runway, lighting, airport and chart data: FAA NASR (cycle 2026-10-29), FAA Chart Supplement Southwest U.S. (29 Oct 2026), FAA airport diagram AL-5015 (d-TPP cycle 2611), FAA Aircraft Characteristics Database; design and marking values from FAA AC 150/5300-13B Chg 1 and AC 150/5340-1M Chg 1; based aircraft and operations from the FAA Terminal Area Forecast (2025 edition). These are U.S. Government works.`,
  `Aircraft identity (registration, type, model, operator): Mictronics aircraft database (${A('https://github.com/Mictronics/aircraft-database', 'https://github.com/Mictronics/aircraft-database')}), Open Data Commons Attribution License 1.0 (${A(ODCBY, ODCBY)})`,
];
const usesFi = (relayInfo) => !!(relayInfo && ((relayInfo.providers || []).some(p => /adsb\.fi/i.test(p)) || (relayInfo.poll && relayInfo.poll.adsbfi)));

export function aboutHtml({ mode, relayInfo, replayInfo, snapshot } = {}) {
  const live = mode === 'live';
  const R = relayInfo && relayInfo.features && relayInfo.features.replay;
  // every aircraft type-only: a relay run with --ident type-only, or a pack built type-only (P1's default)
  const typeOnly = (relayInfo && relayInfo.features && relayInfo.features.d1_mode === 'type-only') || (replayInfo && replayInfo.d1 && replayInfo.d1.ident === 'type-only')
    || (snapshot && snapshot.pack && snapshot.pack.d1 && snapshot.pack.d1.ident === 'type-only');
  const dataLine = live
    ? 'Aircraft positions come from public ADS-B aggregators through the local relay (<code>hwd_live_server.py</code>), which polls them once for every viewer, inside their published rate limits. Because adsb.lol allows 500 requests a day without a key, the relay polls every 7–60 s, and the picture runs up to about a minute behind real time (shown in the status bar) so that motion can be interpolated between real reports.'
    : mode === 'snapshot'
      ? '<b>This is one recorded instant</b> of an hour of adsb.lol ADS-B data from November 2026, frozen. Nothing moves except rotors; parked and taxiing aircraft stand where they were.'
      : `<b>This is a recorded hour</b> of adsb.lol ADS-B data (${replayInfo && replayInfo.desc ? replayInfo.desc : R && R.src ? 'recording ' + R.src : 'November 2026'}), replayed at real speed${R && R.loop !== false ? ' in a loop' : ''}. The recorder saw about 14 s of every minute (adsb.lol answered HTTP 429 after ~10 polls), so the scene runs ${R && R.lookahead_s ? R.lookahead_s : 60} s behind and every gap of up to ~55 s lies between two real reports: the aircraft are interpolated, never invented.`;
  return `
<h3>About Hayward Live 3D</h3>
<p>Hayward Executive Airport (KHWD), Hayward, California. ${dataLine}</p>
<h4>What's real</h4>
<ul>
<li><b>Positions, altitudes, speeds, callsigns, registrations and types</b> are what the aircraft broadcast (ADS-B), filled in from the Mictronics aircraft database where a field is missing. Each aircraft follows its reports as a solid body with GA-like acceleration and turning; on the ground it stays on pavement and moves along the taxiway centrelines (OpenStreetMap).</li>
<li><b>Privacy (LADD / PIA).</b> Aircraft whose owners asked the FAA to limit or hide their data (the LADD and PIA flags in the ADS-B databases) are shown by <b>type only</b>: no registration, callsign, operator or address.${typeOnly ? ' <b>This recording shows every aircraft by type only.</b>' : ''}</li>
<li><b>Runways and lights</b>: runway ends, displaced thresholds, VASI / PAPI angles and the tower hours come from FAA NASR; runway paint follows FAA AC 150/5340-1M, checked against NAIP imagery.</li>
<li><b>Tower hours</b>: Hayward Tower is open 07:00–21:00 local time; when it is closed, 120.2 is the CTAF and runway 10L/28R is closed (FAA NASR).</li>
<li><b>Sun and weather</b> follow the scene time and the KHWD METAR.</li>
</ul>
<h4>What's inferred (marked <span class="inf">inf</span>)</h4>
<ul>
<li><b>Flight phases</b> (pattern legs, touch-and-go, run-up, hover-taxi …) are inferred from each aircraft's own motion by rules calibrated on a week of recordings; a phase that may still change is marked “provisional”.</li>
<li><b>Parking spots</b> are tie-downs and ramp spots found on NAIP imagery and in recorded parked stays. Their names are descriptive (“Green Ramp row 1, tie-down 1”), never official numbers. An aircraft whose signal ended next to a hangar is shown as “in hangar”.</li>
<li><b>HWD traffic or overflight</b>: everything within about 5 NM and below 3,000 ft is drawn; only aircraft that use HWD's runways, taxiways or ramps, or fly its pattern, count as HWD traffic. Oakland and SFO traffic overhead is an overflight.</li>
</ul>
<h4>What's approximate</h4>
<ul>
<li>Aircraft are <b>placeholders</b> sized to their type (FAA Aircraft Characteristics Database where it has the type); their shape only shows the class (high or low wing, twin, jet, helicopter). No liveries or registrations are painted.</li>
<li>Building heights other than the tower's are estimates. Signs, edge lights and REILs are not drawn yet (no source for their positions).</li>
</ul>
<h4>Controls</h4>
<p>One finger drags the map · two fingers pinch to zoom, twist to rotate, move up / down to tilt · tap an aircraft or a list row for its card · <i>Follow</i> keeps it in view. Mouse: drag pans, right-drag rotates, wheel zooms.</p>
<h4>ATC</h4>
<p>The <b>ATC</b> button opens ${A(LIVEATC_URL, 'LiveATC.net')}'s KHWD page in a new tab; this app never plays, relays or records audio. Tower ${TOWER.hours} local; ${FREQS.filter(f => f.ctaf).map(f => 'CTAF ' + f.mhz.toFixed(1)).join('')} when closed.</p>
<h4>Sources &amp; licences</h4>
<ul class="src">
${NOTICES.map(n => `<li>${n}</li>`).join('\n')}
<li>Ground imagery: USDA NAIP 2024 (USDA Farm Production and Conservation Business Center, Geospatial Enterprise Operations), public domain.</li>
<li>Weather: NOAA / NWS Aviation Weather Center (aviationweather.gov), METAR KHWD. U.S. Government work.</li>
${usesFi(relayInfo) ? `<li>Live positions also from ${A('https://adsb.fi', 'adsb.fi')} open data (personal, non-commercial use only; never recorded or redistributed by this app).</li>` : ''}
<li>ATC audio: ${A(LIVEATC_URL, 'LiveATC.net')} (linked, not embedded).</li>
</ul>
<p class="dim">Not for navigation or operational use. No affiliation with the City of Hayward, the FAA or any data provider.</p>`;
}

// always-visible credit line (the ODbL notices must be visible wherever the data is shown; ODbL 4.3)
export function attribHtml({ mode, relayInfo } = {}) {
  return `© ${A('https://www.openstreetmap.org/copyright', 'OpenStreetMap')} contributors (ODbL) · Aircraft data: ${A('https://adsb.lol', 'ADSB.lol')} (${A(ODBL, 'ODbL')})${usesFi(relayInfo) ? ' · ' + A('https://adsb.fi', 'adsb.fi') : ''} · Mictronics (ODC-By) · FAA · USDA NAIP${mode === 'snapshot' ? ' · <b>Recorded instant</b>' : mode === 'replay' ? ' · <b>Recorded replay</b>' : ''}`;
}
