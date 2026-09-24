// About panel & attribution text (data sources, licences, and what is and isn't real).
export function aboutHtml({ mode, relay }) {
  const live = mode === 'live';
  return `
<h3>About SFO Live 3D</h3>
<p>${live ? 'Aircraft positions come from public ADS-B aggregators and update every few seconds.' : '<b>This copy is showing a recorded ADS-B snapshot</b> (23 Sep 2026, 10:51 PDT) because pages hosted inside Claude cannot reach live data services. Open the standalone file for the live feed.'}</p>
<h4>What's real</h4>
<ul>
<li><b>Positions, altitudes, speeds, callsigns, tail numbers and types</b> are exactly what the aircraft broadcast (ADS-B) plus the aggregators' aircraft database.${live ? ' Motion is shown about 8 seconds behind real time so it can be interpolated smoothly between reports.' : ''}</li>
<li><b>Airlines</b> are decoded from the callsign prefix; <b>routes</b> (origin → destination) come from the adsb.lol route database, which is schedule-based and can occasionally be wrong. They are only shown when adsb.lol marks them as plausible for the aircraft's position.</li>
<li><b>Gates</b>: an aircraft is placed at a gate when its reported ground position matches that gate's stand. Many aircraft switch their transponder off at the gate, so gates can look emptier than they are. Aircraft seen arriving at a gate are remembered on this device for up to 8 hours and marked with the time of their last signal.</li>
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
<h4>Sources &amp; licences</h4>
<ul class="src">
<li>ADS-B data: <a href="https://adsb.lol" target="_blank" rel="noopener">adsb.lol</a> (ODbL 1.0) and <a href="https://adsb.fi" target="_blank" rel="noopener">adsb.fi</a> open data (personal, non-commercial use).</li>
<li>Routes: adsb.lol route API; airline &amp; aircraft-type names: <a href="https://github.com/vradarserver/standing-data" target="_blank" rel="noopener">Virtual Radar Server standing data</a>.</li>
<li>Airport geometry: <a href="https://github.com/sfomuseum-data/sfomuseum-data-architecture" target="_blank" rel="noopener">SFO Museum architecture data</a> (CDLA-Permissive-1.0).</li>
<li>Aircraft models: <a href="https://github.com/Ysurac/FlightAirMap-3dmodels" target="_blank" rel="noopener">FlightAirMap 3D models</a> and the <a href="https://github.com/FGMEMBERS/737-800" target="_blank" rel="noopener">FlightGear 737-800</a> (GNU GPL v2 per each model's licence file; the A220 models carry no licence file in that repository).</li>
<li>Weather: NOAA Aviation Weather Center METAR.</li>
</ul>
<p class="dim">Not for navigation or operational use.</p>`;
}
export function attribHtml({ mode }) {
  return `ADS-B: <a href="https://adsb.lol" target="_blank" rel="noopener">adsb.lol</a> · <a href="https://adsb.fi" target="_blank" rel="noopener">adsb.fi</a> · Airport: SFO Museum · Models: FlightGear/FlightAirMap (GPL)${mode === 'snapshot' ? ' · <b>Recorded snapshot</b>' : ''}`;
}
