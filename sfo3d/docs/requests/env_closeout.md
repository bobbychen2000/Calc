# Environment track: requests to other tracks (close-out)

The environment track (lighting, day / night, METAR weather, fog, rain, exposure; spec
`docs/research/environment_spec.md`, log `docs/research/environment_impl.md`) edits only its own files. What it needs
from other tracks' files is listed here, per round. Each request says the file, the change, why, and how to check it.

## Round 3 (close-out round 3, fix round 1, 2026-11-07)

Findings `docs/requests/closeout3_findings.json` `groups.env` (env-1 .. env-16); log `environment_impl.md` R3.1-R3.13.

### R3.1 Static track: `js/live/airport.js` — tone of the OSM-asphalt airside paths in the old renderer (env-11)

live3.html now bakes the 12.5 km of OSM `surface=asphalt` airside paths (the perimeter road 112508632 included) with the
NAIP-measured tone of `data/sfo_landside.json` `naip_grey` (`js/three/ground.js pathToneTexture`: albedo = 0.355 x
naip_grey / 203, clamped 0.6-1.1 x; 203 = the concrete paths' NAIP median, 0.355 the PCC albedo) instead of the 0.13
fresh-asphalt albedo, which drew them dark although NAIP images them as light as the concrete paths (static verifier:
asphalt median 200 vs concrete 208). live.html's bake shader already reads the same tone (`js/shaders/ground.js
BAKE_APT_FS`: `texture(uPaint, vUV).g` = albedo / 0.5, used where `apt.g < 0.5`, i.e. off the movement area), but the
paint texture's G channel is written by `js/live/airport.js paintAirportMapReal` (`paintRGBA`), which leaves it 0: a
no-op until then. **Please**: when building `paintRGBA`, stroke each drawn `airside_paths` piece with
`asphalt` material at its width `w` and write `G = round(min(1, alb / 0.5) x 255)` with `alb` as above (the exact code is
`pathToneTexture` in js/three/ground.js, lines ~30-50). Alternative: flag those paths `concrete` for the albedo only.
Check: one perimeter view in live.html (e.g. `look:1384,3,1020,0,25,110`) — the road reads light grey, like NAIP.

### R3.2 Static track: `jobs/extract2d.mjs` — retired pavement (env-12, static_closeout R2.3)

The env track now skips `DETAILS.pavementRetired` and subtracts `pavementRetiredParts` in the lighting spec
(`tools/env/build_lighting_spec.py`), the taxiway-edge lights (`js/live/lights.js`) and the sign placement
(`js/live/signs.js MOVE`); `js/three` has no other consumer of the taxiway rings. `jobs/extract2d.mjs` (static's) still
treats every `AIRPORT.taxiways` polygon as taxiway.

### R3.3 Buildings track: `js/three/buildings3d.js` — local ground bounce; tower LED; glass shadows (env-10, env-16)

- **Ground bounce (env-10):** objects and aircraft now take their light from below from the local airfield-bake albedo
  around them, not the whole-airfield mean with grass and sand (`js/three/tsl/ground_bounce.js`, header has the model;
  apron concrete vs field mean: x 1.06 / 1.11 / 1.27 per channel). The Blender assets do not yet. **Please** add
  `groundBounce(albedo, metalness, ao, normalWorld)` to the emissive node of the buildings' node materials, as
  `js/three/objects.js` (matId branches) and `js/three/aircraft.js` (`realMaterial` / `procMaterial`) do; it returns
  vec3(0) until renderer3 has set the bake (`setGroundRef`). A/B: `R.gb.on.value = 0 / 1` or `?gbounce=0`.
- **Tower LED (env-16):** tone mapping is unchanged (AgX), so the compensated LED colour needs no re-measure.
- **Tower metering (env-16):** by day the exposure is now bounded to ±1 EV of the incident target
  (`js/env/atmo/exposure.js incidentBound`); a cab-interior view no longer meters on the windows (9.0 → 14.0 vs target
  15.0). The ambient-only interior materials are not needed for the exposure any more.
- **PCF penumbra behind alpha glass (env-16): deferred, keep your workaround.** The noise is the 5-tap PCF of the sun
  shadow, rotated per pixel and per frame (`js/three/engine.js pcfTemporal`) so that TRAA averages it - and TRAA is on in
  every tier (`QUALITY3 ... traa: true`; corrected after the restart: an earlier line here said the low tier had none). What
  TRAA does not average is that noise SEEN THROUGH the alpha-blended glass: the reprojection / neighbourhood clamp works on
  the depth and velocity the glass writes in front of the floor (inferred, not isolated; floor high-pass 50.5 → 0.65 with
  receiveShadow off, your doubt 2). Candidate fixes, each needing an A/B on a real GPU (owner item OD-7): the cab glass
  with `depthWrite: false` (your material) or a wider, non-rotated PCF for receivers behind glass (engine). Until then the
  ambient-only interior (receiveShadow off) is the right workaround.
- **SSR (env-2):** nothing to do: the wet apron mirrors whatever the pre-pass depth and the resolved frame hold,
  buildings included.

### R3.4 Engine track / lead: SSR performance (env-2)

`js/three/ssr.js` adds, on wet pavement only (film > 0.05) and only on the prepass tiers, up to 24 + 6 depth samples
per ground fragment within 900 m. llvmpipe gives no performance number; please measure on a real GPU (phone and
desktop): `R.ssrForce = 0 / 1` or `?ssr=0` A/B on the E9 rain_day gate view (owner item OD-7). If the medium tier is
too slow, gate `ssr` to high / ultra in renderer3 (`Q.ao === 'prepass' && hist && E.depthNode`).

### R3.5 Lead: files changed this round (for the hourly commit)

`js/env/atmo/exposure.js`, `js/env/aircraft_lights.js`, `js/env/state.js`, `js/env/shore_field.js` (new),
`js/env/reservoirs_data.js` (new, generated), `js/three/renderer3.js`, `js/three/lights.js`, `js/three/objects.js`,
`js/three/aircraft.js`, `js/three/ground.js`, `js/three/ssr.js` (new), `js/three/tsl/ground_bounce.js` (new),
`js/three/signs.js`, `js/three/flood.js`, `js/three/dev/skytest.html`, `js/live/app.js` (hooks), `js/live/signs.js`,
`js/live/lights.js`, `js/shaders/env.js`, `js/shaders/ground.js`, `js/renderer.js` (near / far pass filter),
`js/world/terrain.js`, `tools/env/build_lighting_spec.py`, `tools/env/build_reservoirs.py` (new),
`tools/env/lighting_spec.json`, `tools/env/lighting_fixtures.json`, `data/sfo_lighting.js`, `tools/env/test_c3.mjs`
(new), `tools/env/run_gates.sh`, `refs/cache/env_src/**` (FAA Order 8400.9 PDF, OSM extracts, SOURCES.json),
`docs/research/environment_spec.md`, `docs/research/environment_impl.md`, `docs/research/engine_impl.md` (§4.8 notes,
env-9), `docs/requests/engine_closeout.md` (R2.1 done), this file.
Added after the 06:12Z container restart (same round): `js/three/lights.js` (two-part fog aureole, env-3),
`js/three/renderer3.js` (phone tier: no broad aureole lobe), `js/three/flood.js` (EASA citation, comment only),
`tools/env/test_c3.mjs` (28 checks), `refs/cache/env_src/easa/` (EASA CS-ADR-DSN Issue 2 PDF: local-only licence, the
SOURCES.json travels; `tools/cache/sync.py` lists the PDF in MANIFEST.json).

### R3.6 Engine track / lead: fog aureole fill rate (env-3)

`js/three/lights.js` now sizes each fog aureole's quad to where it falls below ~1/255 of display white (two parts: the
diffraction core, ≤ 5 core radii, and a broad refraction lobe of 20.5°, ≤ 4 × that). A landing light seen in its beam
in dense fog can cover most of the screen with one additive quad, by design (the in-beam glow). Desktop / ultra: please
check the frame time of the E7a view (night_fog, an arrival on short final 28R, camera in the landing beams) on a real
GPU (owner item OD-7); the phone tier draws no lobe (`aurTail: false`) and caps the core at 3 radii.

### R3.7 All tracks: live3 renders taken ~06:40Z-07:08Z on 2026-11-07 have NO light sprites

An env edit to `js/three/renderer3.js` (line 408, the Sprites constructor) put a `//` comment in front of
`E.fxScene.add(this.sprites.mesh)` on the same line, so live3.html drew no light sprites at all (airfield lights, aircraft
lights, mast lamps, fog aureoles) from ~06:40Z until the fix at 07:08:22Z (file time). Found by the env track's own light-pass readback
(0 non-zero pixels with 1,221 records). Any live3 render or measurement your track took in that window that involves
lights should be re-taken; renders loaded before ~06:40Z or after 07:08:22Z are unaffected. live.html was not affected.
