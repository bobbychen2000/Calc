# Requests from the engine (three.js, live3.html) track: review round 3 close-out, 4 Nov 2026

From: owner of `live3.html`, `js/three/**`, `vendor/**`, `tools/build3/**`, `tools/blender/**`,
`docs/research/engine_impl.md`, `package.json` devDependencies. What changed on this side is in
`docs/research/engine_impl.md` §4.7. Below: what needs another track's files. Nothing here blocks live3.html.

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

## 6. Owner of `js/shaders/sprites.js` (old renderer, informational)

Round-3 reviewer: live.html draws a green glow at the near wingtip of a parked aircraft at 38 m in daylight, live3
does not. A position light by day is a small coloured lens, not a glow: 14 CFR 25.1391 asks 40 cd forward (recalled,
not re-checked here); through a lens of ~0.01 m² that is ~4,000 cd/m², below sunlit white paint (~100 klx x 0.8 / pi
~ 25,000 cd/m²). A visible halo in sunlight is therefore not physical; consider capping the old sprite's day halo.
(live3's own finding: see engine_impl.md §4.7 for what the wingtip probe showed.)
