// About panel and the always-visible credit line for SHA Live 3D (replaces sfo3d@e3218d6 js/live/about.js; P2e owns it).
// All notices in one place: what is observed and what is inferred, the statement that Hongqiao traffic is simulated /
// inferred, and every source and licence notice (OSM ODbL, adsb.lol ODbL, Copernicus Sentinel and DEM, Umbra CC BY 4.0,
// ESA WorldCover CC BY 4.0, VRS standing data CC0, Mictronics ODC-By, NOAA/NWS METAR, the AIP (mirror) short-facts notice,
// the CAAC MH 5001-2021 cited parameters, the aircraft-model licences, the airline trademark notice). Wording follows
// docs/phase1/*.md (sources_sim.md s.3.1, standards_refs.md, observed_elsewhere.md attribution), docs/PLAN.md s.2 and
// sfo3d docs/ATTRIBUTION_models.md. Other packages may append their own section (e.g. terminals: buildings); the shell
// (js/live/shell.js) moves the tail (Not included, Controls, closing notice) to the end after they did.
const A = (href, text) => `<a href="${href}" target="_blank" rel="noopener">${text}</a>`;
const CCBY = A('https://creativecommons.org/licenses/by/4.0/', 'CC BY 4.0');
const ODBL = A('https://opendatacommons.org/licenses/odbl/1-0/', 'ODbL 1.0');
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** One line about the current mode (also used by the status pill tooltip). */
export function modeLine({ mode, relay, relayInfo, relayWanted, relayError, snapshot }) {
  if (mode === 'live' && relay) {
    const f = (relayInfo && relayInfo.features) || {};
    return `<b>Live</b> through the local relay: ZSSS weather (METAR / TAF) ${f.metar ? 'on' : 'off'}; observed ADS-B (adsb.lol) ${f.adsb ? 'on, at most one request per 180 s' : 'off'}.`;
  }
  if (mode === 'snapshot') {
    const t = snapshot && snapshot.nowUtc ? snapshot.nowUtc.replace('T', ' ').replace(':00Z', 'Z') : '';
    return `<b>Snapshot</b> (static, no network): recorded ZSSS weather at ${esc(t)} (${(snapshot && snapshot.metars || []).length} METARs, ${(snapshot && snapshot.tafs || []).length} TAF), no traffic.` +
      (relayWanted ? ` <span class="warn">The relay was requested but did not answer${relayError ? ' (' + esc(relayError) + ')' : ''}.</span>` : '');
  }
  return '<b>Static scene</b> on the wall clock: no relay, so no live weather (clear default) and no traffic.';
}

export function aboutHtml(info = {}) {
  const { s2 } = info;
  return `
<h3>About SHA Live 3D</h3>
<p>A 3-D model of <b>Shanghai Hongqiao International Airport</b> (ZSSS / SHA), built from open data. Times are Beijing time (UTC+8).</p>
<p class="note-strong"><b>Hongqiao traffic is simulated and inferred, not observed.</b> Open ADS-B receivers do not cover Hongqiao:
in three full days of the open adsb.lol archive (8, 10 and 12 November 2026) none of its about 780 daily movements was seen. When traffic is added (Phase 3) every
aircraft will be generated from published facts and rules and labelled <span class="srcchip inf">inf</span>; real flights seen by
ADS-B elsewhere may lend identity and timing ("observed elsewhere"); the rare aircraft seen live near Shanghai would be
<span class="srcchip obs">obs</span>. This version shows the airfield and the weather, and <b>no traffic yet</b>.</p>
<p class="mode" id="about-mode">${modeLine(info)}</p>

<h4>Observed and inferred</h4>
<ul>
<li><span class="srcchip obs">obs</span> <b>Observed:</b> seen in a source or measured by us: runway, taxiway, apron, stand and building
outlines mapped in OpenStreetMap; runway ends and jet bridges seen on Sentinel-2 and Umbra radar images; runway dimensions,
displaced thresholds and surfaces from the AIP (mirror); the ZSSS weather reports; ADS-B positions.</li>
<li><span class="srcchip inf">inf</span> <b>Inferred:</b> made by a stated rule or a default: pavement widths and shoulders, which
surfaces are concrete, stand size classes without image evidence, jet-bridge models and rest poses, painted markings and
signs (CAAC dimensions, placement from the map: ZSSS paint is not surveyed), building heights and forms, the control-tower
form, the runway direction in use, and all traffic.</li>
<li>Labels and lists carry the chips; the legend at the bottom of the screen lists each layer.</li>
</ul>

<h4>Weather and runway in use</h4>
<ul>
<li>ZSSS METARs are decoded from their raw text: wind in m/s, visibility in metres, QNH in hPa. The trend part (NOSIG,
BECMG, TEMPO) is a forecast and is never drawn as the current sky.</li>
<li>The runway direction is <span class="srcchip inf">inf</span>: the AIP (mirror) names no preferred direction. The default rule turns
the runways after two reports with more than 1.5 m/s tail wind, or one with more than 4 m/s (agreement with the runway named in
ZSSS reports 2023-2026: 86 % in sample, 78 % out of sample); the fallback is "always into the wind" (80.5 %), selectable in
Settings. Arrivals use 18L/36R and departures 18R/36L (AIP (mirror) AD 2.20).</li>
</ul>

<h4>Sources and licences</h4>
<ul class="src">
<li>Airport geometry, stands, taxiways, buildings, roads, rail and water © ${A('https://www.openstreetmap.org/copyright', 'OpenStreetMap contributors')},
available under the Open Database License (${ODBL}). Our data files are Derivative Databases under the same licence.</li>
<li>Contains modified Copernicus Sentinel data 2023-2026 (runway-end and stand measurements${s2 ? ', ground colour' : ''}).</li>
<li>Building-height measurements: produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space
GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved (Copernicus DEM GLO-30, modified).</li>
<li>Umbra Lab, Inc., Umbra SAR Open Data, ${CCBY}, modified (runway ends, stands, jet bridges, heights).</li>
<li>Land cover beyond the detailed area: © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021)
processed by ESA WorldCover consortium, ${CCBY}.</li>
<li>Aircraft positions, live and archived: contains information from ${A('https://adsb.lol', 'ADSB.lol')}, made available under the
${ODBL}. Live positions only when the local relay runs with its adsb.lol option, and only ADS-B (adsb_icao) records count as
observed. Coverage statistics from the adsb.lol archive.</li>
<li>Routes and airline / aircraft-type names: ${A('https://github.com/vradarserver/standing-data', 'Virtual Radar Server standing data')} (CC0 1.0).</li>
<li>Aircraft registrations and types: ${A('https://www.mictronics.de/aircraft-database/', 'Mictronics aircraft database')},
Open Data Commons Attribution License (ODC-By 1.0).</li>
<li>Weather: NOAA/NWS Aviation Weather Center (${A('https://aviationweather.gov', 'aviationweather.gov')}) data, and the Iowa
Environmental Mesonet, Iowa State University (archive). The ZSSS reports are issued by the CAAC aviation meteorological
service. Not official NOAA material.</li>
<li>Runway, stand and procedure facts: AIP China AD 2 ZSSS (CAAC), EFF 2026-07-08, read in an unofficial mirror copy
("AIP (mirror)") and used as reference only. Only short facts are cited, no AIP list is reproduced, and they may be out of
date. These facts are not covered by the ODbL.</li>
<li>Marking, sign and stand-sign dimensions: CAAC MH 5001-2021 Aerodrome technical standards (with amendments 1-4), cited
parameters with their clause numbers; © CAAC, not reproduced. Their presence and placement at ZSSS are inferred.</li>
<li>Aircraft models: FlightGear aircraft (FGMEMBERS, GPL-2.0 or later) via FlightAirMap-3dmodels; Boeing 737-800, 777-200ER
and 777-300ER from FGMEMBERS / FlightGear (GPL-2.0), converted for SFO Live 3D. The A380 textures may still be under CC BY-NC 3.0
(non-commercial). Corresponding source: the pinned FlightGear repositories and SFO Live 3D's converter.</li>
<li>Airline names, logos and liveries are trademarks of their respective owners. They are re-drawn for a non-commercial
depiction; no endorsement is implied. Aircraft type names are trademarks of their manufacturers.</li>
<li>Fonts: Barlow Semi Condensed and IBM Plex Mono (SIL Open Font License 1.1), when the browser can load them.</li>
</ul>

<div class="about-tail">
<h4>Not included</h4>
<ul>
<li>No ATC audio: no lawful, verified source exists for Hongqiao.</li>
<li>No airport flight-board data, no Google, Baidu or Amap imagery, no OpenSky data.</li>
<li><b>Airfield lighting: not modelled yet (Phase 5).</b> Night views show no runway or taxiway lights, stop bars, guard
lights or approach lights, so they are not a picture of the real airfield at night. The apron glow (also on the aircraft,
vehicles and jet bridges standing on the apron), the floodlight-mast lamps and the lit signs and windows are inferred.</li>
</ul>

<h4>Controls</h4>
<p>Drag to pan · right-drag or two-finger twist / tilt to rotate · scroll or pinch to zoom · tap a stand label for its card ·
search a stand number in the list.</p>
<p class="dim about-end">Not for navigation or operational use. Not affiliated with or endorsed by CAAC, the Shanghai airport
authority, any airline or any data provider.</p>
</div>`;
}
// always-visible credit line (short; the About panel has the full notices)
export function attribHtml() {
  return `© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors (ODbL) · Contains modified Copernicus Sentinel data · Umbra Open Data (CC BY 4.0) · <a href="#" data-about>About &amp; licences</a>`;
}
