# Requests from the engine (three.js, live3.html) track: review round 3 close-out, 4 Nov 2026

From: owner of `live3.html`, `js/three/**`, `vendor/**`, `tools/build3/**`, `tools/blender/**`,
`docs/research/engine_impl.md`, `package.json` devDependencies. What changed on this side is in
`docs/research/engine_impl.md` §4.7. Below: what needs another track's files. Nothing here blocks live3.html.

## 0. Lead: commit state and the phone artifact

(Updated 5 Nov 2026, close-out round 2, review finding engine-v4.) Everything listed here in round 3 is committed: the
start-up fixes, chevrons, denoise, glass, tiers in 0e92158, and the persistent shadow nodes (`engine.js CSM3.dispose`,
`flood.js MastSpot`), the spot share (`flood.js spotShare`), the branchless light sprites (`lights.js`) and the docs in
40a32e3. The round-2 work below (glass, position lights, dev page, jobs) was picked up by the WIP commits 7921394,
32dc769 and d1927ab and the next hourly commit. What remains for the lead: rebuild and republish the phone test artifact
from a commit that contains all of it (`sh tools/build3/phone_artifact.sh`); the published one still has the round-3
start-up crash. `tools/blender/` was not created by this track.

## 1. Lead / repository owner: Playwright version in `package.json` (minor)

`package.json` pins `"playwright": "1.56"`, and `package-lock.json` locks it. The harness only works with 1.63.0,
which is installed with `--no-save` to match the preinstalled Chromium in `/opt/pw-browsers` (environment note of
4 Nov 2026). I did NOT change `package.json`: without a matching lock update, `npm ci` would fail on the mismatch, and
agents may not run npm here. Please, when convenient: `npm install -D --save-exact playwright@1.63.0 playwright-core@1.63.0`
(this updates the lock), then commit both files. Until then, do not run `npm ci` / `npm i` in this container.

## 2. `js/world/terrain.js` / the world owner, and the owner of `js/renderer.js`: San Andreas valley (minor, unverified)

Overview parity difference found by the round-3 reviewer (`out/engine_rev/cmp_overview_lake.png`, old top / new
bottom): live.html shows a blue, water-coloured area with a straight edge west of the airport; live3.html shows grass
and a diagonal strip of grey city blocks there.
- The world has no water there: `js/world/terrain.js` has no lake or reservoir data (the comment "crystal springs /
  san andreas valley lakes carve" at line ~207 is stale: the code under it flattens the airport, it carves no lake).
  Read on 4 Nov 2026. So the old renderer's blue patch is not data-driven water. The straight edge suggests a terrain
  chunk missing in `js/renderer.js` (the sea-level water plane seen through the hole): **please check** by listing the
  culled / missing terrain chunks at the overview camera in live.html.
- Reality (general knowledge, not verified against a source here): San Andreas Lake and Crystal Springs Reservoir lie
  in that valley along I-280, inside the SFPUC Peninsula Watershed, which has no urban development. If confirmed
  (e.g. OSM `natural=water` / USGS NHD for the lakes, OSM `landuse` or NLCD for the watershed), the world needs (a) the
  reservoirs as water at their own surface elevation and (b) no city blocks in the watershed (the city bake's urban mask,
  `NATURE_KM` in terrain.js). Both renderers would follow; live3.html's city bake reads the same region texture.

## 3. Ground-shader owner (`js/shaders/ground.js`): seawall foam from `data/sfo_shore.js` (shared, still open)

`docs/requests/static_geometry_round3.md` §6 asks both renderers to compute the seawall-foam distance from
`data/sfo_shore.js` instead of the 16-vertex `AIRPORT_LAND_ST` polygon (up to ~100 m off the real seawall).
`js/three/ground.js` (`aptPoly()`, `auxMaterial()`) does exactly what `js/shaders/ground.js` does today, for parity.
When the ground-shader owner moves to `sfo_shore.js`, tell this track and the same distance texture will be baked here.

## 4. `js/live/signs.js`, `js/live/models.js`, `js/live/aircraft.js`: exports that remove the replicas (minor, open since 24 Sep)

Three pieces of other tracks' logic are copied in `js/three/` because they are not exported. They are at parity
today (read side by side on 4 Nov 2026: no differences), but any change on the other side diverges silently:
- `js/live/signs.js`: return `atlasMap: A.map` from `buildSigns` and export `locName` (engine_exports.md §2); then
  `js/three/signs.js worldSignAtlasMap` goes.
- `js/live/models.js`: export the registration layout of `registrationTexture` (row / cap / flag / port-over-starboard
  placement) as a function `registrationLayout(reg, flag)` returning the draw list; `js/three/aircraft.js RegAtlas`
  would draw from it.
- `js/live/aircraft.js`: export the per-frame LOD decision of `items()` (model vs procedural, livery pending, tip
  devices, gear) as `ac.lodState(camPos)`; `js/three/aircraft.js` would call it instead of re-deriving it. Also make
  `_livNeutral` public (`livNeutral`), as asked on 25 Sep.

## 5. `js/live/app.js` (real-time track): still open from engine_exports.md §5

- §5.1: `marker: true` on `markerSprites()` records (live3 still recognises markers heuristically).
- §5.2: a fatal-error hook `R.onFatal = (html) => ui.fail(html)` and a `ui.fail` that works after load. Round 3 found
  why it matters: a renderer exception inside `new Scene(...)` left the app's loading overlay up for good. live3 now
  shows its own message (`renderer3.js fatal()`), and no longer blames the browser for code errors.

## 6. `js/live/app.js` (real-time track): the 'dusk' light preset is a clock time (minor)

`lightDate()` maps 'day' / 'dusk' / 'night' to fixed local times (13:00 / 19:45 / 22:30, as "PDT" = UTC-7) on today's
date. On 4 Nov 2026 19:45 is ~1.7 h after sunset (sunset ~17:05 PST): the 'dusk' preset rendered as full night in both
renderers (live3 `debugInfo().eKeyLux` 20 = floods only; 26 Sep it gave 31.8 lx with the twilight sky). Please define
the presets by solar elevation (e.g. dusk = -4.5 deg, the value the round-1 checks used), so QA and users get dusk
all year; the UTC-7 offset is also wrong in winter (PST = UTC-8).

## 7. `js/live/gates.js` (bridges / GSE track): tank truck under the UAL B39M wingtip at D10 (please check)

In live3 renders of the snapshot at the close-up `ac:a12a82,38,-,6` (D10), a fuel tank truck stands under the
starboard wingtip / split-tip device (`out/engine_r3/run1/r3_day_ac8.png`, `r3_day_ac_orbit.png`); it was not there
in the reviewer's frame (vehicles follow the gate timeline). From these angles the clearance cannot be judged: please
run the GSE hull test against the wing and tip device (B39M span with split tips) for that placement.

## 8. Owner of `js/shaders/sprites.js` (old renderer, informational)

Round-3 reviewer: live.html draws a green glow at the near wingtip of a parked aircraft at 38 m in daylight, live3
does not. A position light by day is a small coloured lens, not a glow: 14 CFR 25.1391 asks 40 cd forward (recalled,
not re-checked here); through a lens of ~0.01 m² that is ~4,000 cd/m², below sunlit white paint (~100 klx x 0.8 / pi
~ 25,000 cd/m²). A visible halo in sunlight is therefore not physical; consider capping the old sprite's day halo.
live3's own nav lights were missing for a different reason (every 2.2-12 px sprite was dropped by a branch in its
TSL vertex code, day and night; fixed, engine_impl.md §4.7 #8). They now draw as small coloured points with live3's
capped halo (0.5 in exposed units).

## Round 2 (close-out round 2, 5 Nov 2026): engine-v1 .. engine-v5

What changed on this side is in `docs/research/engine_impl.md` §4.8 (evidence: `out/engine_r3/close2/`,
`out/engine_r3/ultra/`, `out/engine_r3/glassdev/`). Nothing below blocks live3.html.

### R2.1 Lead: commit and the phone artifact

Round-2 files of this track: `js/three/objects.js`, `js/three/renderer3.js`, `js/three/lights.js`,
`js/three/compat/scene.js`, `js/three/dev/glasstest.html`, `tools/build3/job_close2.mjs`, `tools/build3/job_glass.mjs`,
`tools/build3/glass_meas.py`, `docs/research/engine_impl.md`, this file. After they are committed, rebuild and republish
the phone test artifact (`sh tools/build3/phone_artifact.sh`, §0); the published one predates round 3.

### R2.2 Owner of `js/aircraft/fleet.js` (aircraft track): position-light record intensities (minor)

live3 now keeps aircraft position lights at their night calibration by day (one intensity day and night, as the lights
have). At that calibration the `lightSprites` records give 26 cd (nav: i 40, s 0.22) and 13 cd (tail: i 25, s 0.2):
E = i x 13.2 s^2 cd (`js/three/lights.js` header). 14 CFR 25.1391 asks at least 40 cd forward red / green (0-10 deg off
dead ahead) and 20 cd rear white (eCFR, read by this track on 5 Nov 2026). Meeting the minimum needs nav i ~63 and tail
i ~38; both renderers read these records, so live.html's night look would change too (x 1.5). Please decide and, if
agreed, change the records; live3 needs no code change.

### R2.3 Owner decision: the IBL ground (round-3 open question, still open)

The curtain walls no longer depend on it: they mirror a local apron (the airfield bake's concrete mean
(0.321, 0.306, 0.269) and the facade's own shadow; A/B in §4.8: new vs new + paved IBL ground, lum 27.7 / 28.9). Every
other object's light from below still uses the whole-airfield mean (0.303, 0.275, 0.211: grass and sand). Moving it to
the concrete mean would brighten and cool the shade under aircraft and near terminals by ~6-28 % per channel and needs
a full re-verification pass, so it was not done.

### R2.4 Buildings track / spec owners: mullion finish of the pier curtain walls (minor, unverified)

`refs/cache/buildings/review_likeness/a2.jpg` (Boarding Area G, Sept 2025) shows light, silver-white mullions and
transoms; `js/three/objects.js` draws the curtain-wall frame as dark grey metal (albedo 0.28, metalness 0.8, inherited
from `js/shaders/objects.js`). If a source for the mullion finish of the piers (B-G) exists or turns up, please record it
in the building spec; the material will follow. Not changed on a single photo of one pier.

### R2.5 Bridges / GSE track: tank truck under the UAL B39M's starboard wingtip at D10 (§7, still present)

Still in the round-2 renders of the snapshot (`out/engine_r3/close2/c2_day_ac8.png`, `out/engine_r3/ultra/u_day_ac8.png`).
