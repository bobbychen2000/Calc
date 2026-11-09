# Environment track: requests to other tracks (close-out)

The environment track (lighting, day / night, METAR weather, fog, rain, exposure; spec
`docs/research/environment_spec.md`, log `docs/research/environment_impl.md`) edits only its own files. What it needs
from other tracks' files is listed here, per round. Each request says the file, the change, why, and how to check it.

## Round 3 (close-out round 3, fix round 1, 2026-11-07)

Findings `docs/requests/closeout3_findings.json` `groups.env` (env-1 .. env-16); log `environment_impl.md` R3.1-R3.13.

### R3.1 Static track: `js/live/airport.js` — tone of the OSM-asphalt airside paths in the old renderer (env-11)

**[Round 5: the encoding below is superseded by R5.1 (G premultiplied by coverage, B = coverage); the rest stands.]**

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

**[Done - Round 5: commit 904dcfe drops the retired polygons and exports `retiredParts`.]**

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
`tools/env/test_c3.mjs` (29 checks), `refs/cache/env_src/easa/` (EASA CS-ADR-DSN Issue 2 PDF: local-only licence, the
SOURCES.json travels; `tools/cache/sync.py` lists the PDF in MANIFEST.json).

### R3.6 Engine track / lead: fog aureole fill rate (env-3)

`js/three/lights.js` now sizes each fog aureole's quad to where it falls below ~1/255 of display white (two parts: the
diffraction core, ≤ 5 core radii, and a broad refraction lobe of 20.5°, ≤ 4 × that). A landing light seen in its beam
in dense fog can cover most of the screen with one additive quad, by design (the in-beam glow). Desktop / ultra: please
check the frame time of the E7a view (night_fog, an arrival on short final 28R, camera in the landing beams) on a real
GPU (owner item OD-7); the phone tier draws no lobe (`aurTail: false`) and caps the core at 3 radii (close-out round 5:
2 radii, the round-2 fill rate; R5 below).

### R3.7 All tracks: live3 renders taken ~06:40Z-07:08Z on 2026-11-07 have NO light sprites

An env edit to `js/three/renderer3.js` (line 408, the Sprites constructor) put a `//` comment in front of
`E.fxScene.add(this.sprites.mesh)` on the same line, so live3.html drew no light sprites at all (airfield lights, aircraft
lights, mast lamps, fog aureoles) from ~06:40Z until the fix at 07:08:22Z (file time). Found by the env track's own light-pass readback
(0 non-zero pixels with 1,221 records). Any live3 render or measurement your track took in that window that involves
lights should be re-taken; renders loaded before ~06:40Z or after 07:08:22Z are unaffected. live.html was not affected.

## Round 5 (close-out round 5, residuals: c3 verify-1 env findings 1-10; 9 Nov 2026)

Findings: scratchpad `c3_verify1_env.json` (10 minors); log `environment_impl.md` "Close-out round 5". Before = the files at
the start of round 5 (frozen copy, scratchpad `c5/runtime/root_before`), after = the working tree; the same scripts for both
arms. Env gates (`tools/env/run_gates.sh`): all pass before and after; `tools/env/test_c3.mjs` 29/29 -> 37/37 (the 8 new
checks below).

| Finding | Status | Before -> after |
|---|---|---|
| SSR under-occlusion (env-2 residual) | fixed | `js/three/ssr.js` subtracts `specOcc x L_env` (three's own specular occlusion from the pre-pass GTAO, `engine.js aoScreen`); E9 render at a fixed EV (`R.ssrAO` 0 / 1, same frame): apron pixels darkened by SSR > 12 levels 1,967 -> 1,352, > 20 levels 186 -> 42, only in the contact zones under bridges / aircraft / GSE (environment_impl R5.1) |
| phone aureole quad (env-3 residual) | fixed | low tier: core quad 3 -> **2 radii** (the round-2 fill rate; `AUR_K_CORE_LOW`), the cut-off energy folded back into the core; test_c3: quad 2.00 radii, energy within 0.15 % |
| test_c3 aureole mirror | fixed | the CPU mirror now draws what the shader draws (soft rim, tan-mapped billboard, cos^3 solid angle); round-3 shader vs mirror 12.0 % (desktop) / 3.6 % (phone) low -> 0.15 % / 0.15 % with the fold-back gains (`lights.js aurCoreGain / aurLobeGain`) |
| WET_TAILWIND_KT misreading | fixed | FAA Order 8400.9 §7d(2)(b) (read in the cached PDF, `refs/cache/env_src/`): "No tailwind component may be present except the nominal range of winds reported as calm (0-3 knots) may be considered to have no tailwind component" - the 3 kt applies to the reported wind speed (gusts included), not to the tail component. `state.js WET_CALM_KT` 3; test_c3 +4 cases (18004KT -RA SE, 18003KT -RA W, 18003G12KT -RA SE, 30008KT -RA W); 58 recorded METARs: non-West plans 7 -> 8 (101915Z 18005KT +RA: West -> Southeast) |
| paint.g encoding vs R3.1 | fixed (request revised: R5.1) | `js/shaders/ground.js BAKE_APT_FS` reads G = albedo / 0.5 x coverage (premultiplied), B = coverage, un-premultiplies and mixes by coverage (edge texels / far mips keep the asphalt) |
| live.html sprite halo (env-6) | partly (request R5.2) | `js/shaders/sprites.js` draws no halo for a lens record (`iData.x`); live.html noon render below |
| clipped-pixel veil evidence (env-3) | partly | re-measured 2.5 EV darker (unclipped): fuselage / nose / fin vs the air at the same lamp distances 0.94 / 0.99 / 1.06 (air controls 1.00-1.01) - veiled, no cut-out; the quarter-view centre hole not re-checked (strobes dark at both shot instants), open |
| lakes vs terrain mesh (env-14) | fixed | built mesh, lakes San Andreas / Lower / Upper Crystal Springs visible: step 15 (high) 94.3 / 73.2 / 68.6 % -> **96.7 / 95.7 / 98.7 %**; step 30 (phone) -> **95.9 / 95.1 / 98.3 %** (`js/world/terrain.js`: bed mirrors the bank slope + grid lines across the lake boxes, 80 m) |
| backwards night own-shadow doc | fixed | environment_impl.md R3.5: "at night own = 0 (no facade shadow)" |
| env-12 extract2d | closed | R3.2 below is done (commit 904dcfe) |

### R5.1 Static track: `js/live/airport.js` - R3.1 encoding REVISED (supersedes the G-only text of R3.1)

Write the airside-path tone into the paint texture's **G and B channels**: `B = round(cov x 255)` (the stroke's coverage,
anti-aliased edge included) and `G = round(min(1, alb / 0.5) x cov x 255)` (premultiplied by the coverage), with `alb` as in
R3.1 (`pathToneTexture`, js/three/ground.js). The bake shader un-premultiplies (`G / B`) and mixes by `B`, so the linear
filtering and the mips of the paint texture (created with `mips: true`) blend the path tone with the asphalt instead of
reading a partial G as near-black asphalt (c3 verifier: a dark outline along every path). Today both channels are 0 and the
shader branch is a no-op (`pc.y > 0.004`). Check as R3.1.

### R5.2 Owner of `js/scene.js` (old renderer core; realtime / lead): pack the lens flag (env-6, live.html) - DONE in round 6 (R6.1)

`js/scene.js` line 63, the sprite record packer `put(s)`: add `B[o + 12] = s.lens ? 1 : 0;` (the 13th float = `iData.x` of
`js/shaders/sprites.js`, unused today and always 0). With it, live.html draws a position light's lens by day without the
fixed 8 % halo, as live3 does (js/env/aircraft_lights.js sets `lens: true`). Evidence: live.html noon, E75L red light 14.4 m
away, 640 x 360 (scratchpad `c5/runtime/render/c5o_day_navlens*.png`, the flag written by a page-side hook on the sprite
upload = this request): peak (213, 100, 112) -> (205, 100, 112) on the wing's (129, 126, 123); the halo ring 2.5-4.6 px R
148.6 -> 141.1, 4.5-7 px 117.7 -> 113.7 (G / B unchanged). A small red dot either way; the flag removes the ~+8 R glow.

### R5.3 Engine track / lead: GPU cost of this round's changes (owner item OD-7, with R3.4 / R3.6)

- SSR: one extra AO texture read per SSR fragment (wet pavement only, prepass tiers).
- Aureoles: phone core quads back to 2 radii (less fill than round 3); desktop unchanged in size.
- Terrain: the lake-box grid lines add 14 % vertices on the high tier (611,524 -> 699,244) and 25 % on the phone tier
  (220,900 -> 275,613); the mesh builds faster than before (bucketed lake test: node, 4.89 -> 3.81 s and 1.69 -> 1.47 s).

### R3.2 status: done (env-12)

`jobs/extract2d.mjs` (commit 904dcfe) leaves `DETAILS.pavementRetired` out of `pave.taxiways` and exports `retiredParts`
for subtraction by its consumers (they are not subtracted there; tools/drawing reads them).

### R5.4 Spec owner (`docs/research/environment_spec.md`): FAA 8400.9 paragraph and the wet rule - DONE in round 6 (R6.2)

Lines ~226 and ~911 cite "FAA Order 8400.9 §4b"; in the cached order the wind criteria are **¶7d** ("7. Operational
safety criteria ... d. Winds": (1) clear and dry, (2) not clear or not dry). Please change the citation to ¶7d and the
§12.1 / table wet entry to "wet: crosswind incl. gusts <= 15 kt; no tailwind component unless the reported wind incl.
gusts is calm, 0-3 kt (¶7d(2)(b))" - what `js/env/state.js` now implements. (Not this track's file this round.)

### R5.5 Render QA (owner item / next round): the quarter-view strobe hole

One live3 shot of E7a from the front-left quarter (34 deg, 45 m) with the strobes forced on (e.g. freeze the flash phase
in `js/env/aircraft_lights.js` or a QA hook), depthOn 1 and 0: a centre hole that disappears with depthOn 0 on a lamp that
is geometrically hidden is the intended veil (core occluded, aureole kept); on a visible lamp it is a bug.

### R5.6 Lead: files changed by this track for env this round

`js/env/state.js`, `js/three/ssr.js`, `js/three/lights.js`, `js/three/engine.js` (aoScreen), `js/three/renderer3.js`
(ssrAO uniform, fatal -> onFatal), `js/shaders/ground.js`, `js/shaders/sprites.js`, `js/world/terrain.js`,
`tools/env/test_c3.mjs`, `docs/research/environment_impl.md`, `docs/research/engine_impl.md` (§4.8), this file,
`docs/requests/engine_closeout.md`.

## Round 6 (close-out round 6, residuals of the round-5 verifier and this track's own round-5 requests; 9 Nov 2026)

Inputs: scratchpad `c5_r5verify1_runtime.json` (finding 2: lakes on the lite path), `c5_r5fix1_runtime.json` (open requests
R5.2, R5.4). Work log: scratchpad `c6/runtime/NOTES.md`. No asset rebuilt; no tools/live replays (no harness involved).

| Item | Status | Evidence |
|---|---|---|
| R5.2 live.html lens halo (env-6) | **fixed** | `js/scene.js` `put(s)`: `B[o + 12] = s.lens ? 1 : 0` (the only change in that file); `js/shaders/sprites.js` comment updated |
| R5.4 FAA 8400.9 citation + wet rule in the spec | **fixed** | `environment_spec.md` §3.5 item 3 and the §12.1 table row (R6.2) |
| verifier finding 2: lakes on the lite phone path (`SFO_LITE`, terrainStep 40) | not done - owner directive | the LITE artifact is frozen (9 Nov): no lite-only work. Recorded for a later round: at step 40 San Andreas Lake is 94.9 % visible (gate 95 %), +33 % terrain vertices / +35 chunks (verifier's vlake.mjs) |
| R5.1 (static, paint G/B), R5.3 (OD-7 GPU cost), R5.5 (strobe re-shot) | open, unchanged | not in this round's scope |

### R6.1 live.html lens flag (R5.2): one render, numeric pixel check

live.html (old WebGL 2 renderer) noon preset, snapshot mode, 640 x 360 (SwiftShader), the red position light of a taxiing
aircraft 14.4 m from the camera (scratchpad `c6/runtime/render/job_c6o.mjs`, `c6o_check.json`). One page session, two shots:
A = the lens flag forced to 0 on the sprite upload by a page hook (= `put()` before this change), B = as shipped now (no hook).

- Upload buffer (native, B): the one record with the day-lens signature (s 0.08 m, k 0) carries flag 1, every other record 0
  (8 uploaded records at the shot: flag 1 on 1, signature on 1, flag without signature 0, signature without flag 0).
- Pixels at the lens (320, 180): peak (216, 111, 115) -> **(209, 110, 115)**; ring 2.5-4.6 px R 147.8 -> **139.8** (G / B 114.2 /
  119.8 unchanged); ring 4.5-7 px R 116.6 -> 112.8. Pixels changed by > 2 levels: 125 within 8 px of the lens (max 15), 22
  elsewhere (max 4, sky at the top edge). The same direction and size as the round-5 hook A/B (`c5o`: ring R 151.7 -> 143.9
  measured the same way). PNGs `c6o_A_flag0.png` (md5 d9162766), `c6o_B_native.png` (6ceea228), crop `c6o_crop_AB.png`.
- The page served the working tree (other tracks' edits included); 0 page errors, ready in 177 s.

### R6.2 environment_spec.md (R5.4): what changed

Re-read in the cached order (`refs/cache/env_src/faa_order_8400-9.pdf`, md5 54499cd2, pdftotext): "7. OPERATIONAL SAFETY
CRITERIA ... d. Winds. (1) Clear and Dry Runways. (a) ... crosswind component ... (including gust values) must not be greater
than 20 knots ... (b) ... the tailwind component must not be greater than 5 knots ... (c) ... 7 knots [touchdown-zone
anemometers] ... (2) Runways Not Clear or Not Dry. (a) The crosswind component (including gust values) must not exceed 15
knots ... (b) No tailwind component may be present except the nominal range of winds reported as calm (0-3 knots) may be
considered to have no tailwind component." The spec now cites ¶7d (¶7d(1), ¶7d(2), ¶7d(2)(b) quoted; the old "§4b" noted as
wrong), states the wet rule as "no tailwind component unless the reported wind is calm, 0-3 kt" (**V**) with the two
inferences tagged **I** (precipitation in the METAR = not dry; the gust counts toward the 3 kt), adds the round-5 effect
(58 recorded METARs, non-West 7 -> 8, environment_impl.md R5.3), and the §12.1 table row matches (`WET_CALM_KT` 3). Only those
citation lines were edited.

### R6.3 Lead: files changed by this track for env this round

`js/scene.js` (line 63, `put()` only), `js/shaders/sprites.js` (comment), `docs/research/environment_spec.md` (8400.9 lines
~226-234 and the §12.1 row), this file.

## Round 7 (9 Nov 2026)

No env items were assigned to this track in round 7, and no env file changed (js/env/**, js/shaders/sprites.js and
js/scene.js are untouched since round 6: scene.js 8417e2ce, sprites.js fd418713). The open owner item is unchanged: lakes
on the lite path (step 40), which waits for Lite to be unfrozen. The bridge work of this round is in bridges_closeout.md
Round 7.
