// About panel & attribution text for SHA Live 3D (replaces sfo3d@e3218d6 js/live/about.js: sources, licences, and what
// is observed and what is inferred). Phase 2: a static scene, no traffic.
export function aboutHtml({ mode, relay, s2 }) {
  return `
<h3>About SHA Live 3D</h3>
<p>A 3-D model of Shanghai Hongqiao International Airport (ZSSS / SHA). <b>Phase 2 core:</b> the airfield, its surroundings, the sun,
sky and weather. There is <b>no traffic yet</b>: open ADS-B sources do not see Hongqiao, so traffic will be simulated and labelled
<i>inferred</i> (Phase 3).</p>
<h4>Observed and inferred</h4>
<ul>
<li><b>Observed:</b> runway, taxiway, apron, building and stand positions mapped in OpenStreetMap; runway ends measured on
Sentinel-2 and Umbra SAR imagery; runway dimensions, displaced thresholds and surfaces from the AIP (unofficial mirror copy);
the ground colour from Sentinel-2.</li>
<li><b>Inferred:</b> pavement widths, taxiway shoulders, which surfaces are concrete, building heights (rules), the control-tower
form, water widths, road widths. Markings, signs, airfield lights, jet bridges and terminal detail come in later packages.</li>
</ul>
<h4>Controls</h4>
<p>Drag to pan · right-drag (or two-finger twist / tilt) to rotate · scroll or pinch to zoom.</p>
<h4>Sources &amp; licences</h4>
<ul class="src">
<li>Airport geometry, buildings, roads, rail and water © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>, available under the Open Database License (ODbL 1.0).</li>
<li>Contains modified Copernicus Sentinel data 2026 (runway-end measurements${s2 ? ', ground colour' : ''}).</li>
<li>Umbra Lab, Inc., Umbra SAR Open Data, <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>, modified (runway-end and stand measurements).</li>
<li>Runway facts: AIP China AD 2 ZSSS (CAAC), unofficial mirror copy (EFF 2026-07-08), short cited facts as reference only.</li>
<li>Aircraft models: FlightAirMap 3D models and FlightGear aircraft (GPL-2.0), as converted for SFO Live 3D.</li>
${relay ? '<li>Weather: NOAA/NWS Aviation Weather Center (ZSSS METAR via the local relay).</li>' : ''}
</ul>
<p class="dim">Not for navigation or operational use.</p>`;
}
// always-visible credit line
export function attribHtml() {
  return `© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors (ODbL) · Contains modified Copernicus Sentinel data 2026 · Umbra Open Data (CC BY 4.0)`;
}
