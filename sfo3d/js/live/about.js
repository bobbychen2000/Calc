// About panel & attribution text (data sources, licences, and what is and isn't real).
export function aboutHtml({ mode, relay }) {
  const live = mode === 'live';
  return `
<h3>About SFO Live 3D</h3>
<p>${live ? (relay ? 'Aircraft positions come from public ADS-B aggregators through the local relay, which merges them into one stream (about one update a second).' : 'Aircraft positions come from public ADS-B aggregators and update every few seconds.') : '<b>This copy is showing a recorded ADS-B snapshot</b> (23 Sep 2026, 10:51 PDT) because pages hosted inside Claude cannot reach live data services. Open the standalone file for the live feed.'}</p>
<h4>What's real</h4>
<ul>
<li><b>Positions, altitudes, speeds, callsigns, tail numbers and types</b> are exactly what the aircraft broadcast (ADS-B) plus the aggregators' aircraft database.${live ? (relay ? ' The picture runs 1–3 seconds behind real time (shown in the status bar) so motion can be interpolated between reports; each aircraft is drawn as a physical body that follows its reports with realistic acceleration and turning, so a late or noisy report never makes it jump.' : ' Motion is shown about 9 seconds behind real time so it can be interpolated smoothly between reports.') : ''}</li>
<li><b>Landings and take-offs</b> are detected from the aircraft's own motion — touchdown where it starts braking, lift-off where it starts climbing — not from the transponder's air/ground switch, which flips at about 100 kt (and about 50 kt on E175s) rather than at touchdown or lift-off. The runway comes from where the aircraft lines up on final. Runway counts in the panel are what this page has seen since it opened.</li>
<li><b>Airlines</b> are decoded from the callsign prefix; <b>routes</b> (origin → destination) come from the adsb.lol route database, which is schedule-based and can occasionally be wrong. They are only shown when adsb.lol marks them as plausible for the aircraft's position.</li>
<li><b>Gates</b>: ${relay ? 'when the relay can read SFO\'s own flight-status page (flysfo.com), an aircraft parked near the stand SFO assigned to its flight is shown at that stand (the card says "per SFO ✓"; when the stand seen from the aircraft\'s position differs, the card shows both); otherwise ' : ''}an aircraft is placed at a gate when its reported ground position and heading match that gate's stand. Taxiing aircraft follow the real taxiway centrelines (OpenStreetMap). Many aircraft switch their transponder off at the gate, so gates can look emptier than they are. Aircraft seen arriving at a gate are remembered on this device for up to 8 hours and marked with the time of their last signal.</li>
<li><b>Airport layout</b> (terminals, boarding areas, gate positions, taxiways, runways) comes from the SFO Museum architecture dataset; runway ends from FAA survey data.</li>
<li><b>Sun position</b> follows the real time at SFO; weather (wind, visibility, low cloud) follows the KSFO METAR when it can be fetched.</li>
</ul>
<h4>What's approximate</h4>
<ul>
<li>3D aircraft models are community models (FlightGear / FlightAirMap). A few types are adapted from a close relative (e.g. 737 MAX from the 737-800, 787-9/-10 from the 787-8); the 777 family uses a simplified procedural airframe; business jets use a generic scaled airframe. Aircraft without a model appear as markers.</li>
<li>Airline liveries are simplified colour schemes — no logos or lettering.</li>
<li>Terrain, city and water are stylised; jet-bridge motion and ground vehicles are illustrative.</li>
</ul>
<h4>Controls</h4>
<p>Drag to pan · right-drag (or two-finger twist/tilt) to rotate · scroll or pinch to zoom · tap an aircraft or list row to follow it.</p>
${live && !relay ? `<h4>If the live feed says "unavailable"</h4><p>Some browsers block direct requests to the ADS-B services from a local file. Run the included helper <code>sfo_live_server.py</code> (Python 3, no installs) in the same folder and open the address it prints — it relays the public feeds for your browser and also lets phones on the same Wi-Fi connect.</p>` : ''}
<h4>ATC audio</h4>
<p>The <b>ATC</b> button lists LiveATC.net's San Francisco feeds by role (Tower, Ground, Approach, Departure…) with their frequencies — marked <i>FAA</i> when the frequency is published for SFO (FAA Chart Supplement, NASR, approach and departure charts) or <i>LiveATC label</i> when only LiveATC names it. “Listen” opens LiveATC's own player in a new tab; this app never plays, relays or records the audio. “Highlight” marks the aircraft that are <i>likely</i> on that frequency, inferred from their phase and position (controllers choose the hand-off points, and the app cannot know who is talking). The audio-delay slider holds the whole scene back so it lines up with LiveATC, which runs up to about 20 s behind.</p>
<h4>Sources &amp; licences</h4>
<ul class="src">
<li>Aircraft data: <a href="https://adsb.lol" target="_blank" rel="noopener">ADSB.lol</a> — contains information from ADSB.lol, which is made available here under the <a href="https://opendatacommons.org/licenses/odbl/1-0/" target="_blank" rel="noopener">Open Database License (ODbL)</a> — and <a href="https://adsb.fi" target="_blank" rel="noopener">adsb.fi</a> open data (personal, non-commercial use). Routes: ADSB.lol / <a href="https://github.com/vradarserver/standing-data" target="_blank" rel="noopener">VRS standing data</a> (CC0).</li>
<li>Stand, jet-bridge and parking-position data, taxiway centrelines and aprons © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>, available under the Open Database License (ODbL 1.0) (the derived <code>data/sfo_stands.json</code> and <code>data/sfo_taxigraph.js</code> are ODbL too).</li>
<li>Airport geometry: SFO Museum, <a href="https://github.com/sfomuseum-data/sfomuseum-data-architecture" target="_blank" rel="noopener">sfomuseum-data-architecture</a> (CDLA-Permissive-1.0).</li>
<li>Measurements on imagery: USDA NAIP 2024 (USDA Farm Production and Conservation Business Center, Geospatial Enterprise Operations) — public domain.</li>
<li>Runway, lighting and airport data: FAA National Airspace System Resources (NASR), cycle 2026-09-03; FAA Airport Diagram AL-375 — U.S. Government works. ATC frequencies: FAA Chart Supplement Southwest (3 Sep – 29 Oct 2026), NASR 2026-09-03, d-TPP cycle 2609.</li>
<li>Stand names: San Francisco International Airport (DataSF dataset chfu-j7tc, PDDL; flysfo.com).</li>
${relay ? `<li>Gates and stands: San Francisco International Airport <a href="https://www.flysfo.com/flight-info/flight-status" target="_blank" rel="noopener">flight status</a>. Unofficial use of SFO's public flight-status data; no terms of use are published. The relay reads it at most every 10 minutes (switch it off with <code>--no-sfo-gates</code>).</li>` : ''}
<li>ATC audio: <a href="https://www.liveatc.net" target="_blank" rel="noopener">LiveATC.net</a> (linked, not embedded; personal, non-commercial use per LiveATC's terms).</li>
<li>Weather: NOAA/NWS Aviation Weather Center METAR.</li>
<li>Aircraft models: <a href="https://github.com/Ysurac/FlightAirMap-3dmodels" target="_blank" rel="noopener">FlightAirMap 3D models</a> and the <a href="https://github.com/FGMEMBERS/737-800" target="_blank" rel="noopener">FlightGear 737-800</a> (GNU GPL v2 per each model's licence file; the A220 models carry no licence file in that repository).</li>
</ul>
<p class="dim">Not for navigation or operational use.</p>`;
}
// always-visible credit line (realtime_feeds.md s.1: the ADS-B notice must be visible wherever live data is shown)
export function attribHtml({ mode }) {
  return `Aircraft data: <a href="https://adsb.lol" target="_blank" rel="noopener">ADSB.lol</a> (<a href="https://opendatacommons.org/licenses/odbl/1-0/" target="_blank" rel="noopener">ODbL</a>) · <a href="https://adsb.fi" target="_blank" rel="noopener">adsb.fi</a> open data · Routes: VRS (CC0) · © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors (ODbL) · SFO Museum · FAA · USDA NAIP · Models: FlightGear/FlightAirMap (GPL)${mode === 'snapshot' ? ' · <b>Recorded snapshot</b>' : ''}`;
}
