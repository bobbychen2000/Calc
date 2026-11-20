# Phase 2a: core fork (app skeleton, ZSSS frame, world, extension points, harness)

Date: 2026-11-14. Package P2a of Phase 2 (docs/PLAN.md §7). Fork base: sfo3d @ **e3218d6**, `live.html` path (plain
WebGL2, working default Q7). Nothing in `sfo3d/`, `pc12/` or `hwd3d/` was modified; nothing was committed.

Result: `sha3d/live.html` opens a static, sun-lit, weather-aware ZSSS scene with the airfield pavement, the
surroundings of the 23.5 km² detailed extent, placeholder buildings and a tower stand-in. There is no traffic (Phase 3).
Four other packages can now work in parallel through one registration call each (§5).

Tags as in docs/PLAN.md: **obs** (seen in a source / measured), **inf** (inferred: rule, default or placeholder).

---

## 1. File map

Every copied file starts with `forked from sfo3d@e3218d6 <path>`. "Adapted" = forked, then changed as listed.

| File | Status | What changed |
|---|---|---|
| `live.html` | adapted | title; loads `data/sha_airport.js`, `sha_stands.js`, `sha_taxigraph.js`, `sha_ground_s2.js` (window globals) before the module |
| `live.css` | adapted | brand `SHA`; legend slot `#legend`, source chips `.srcchip.obs/.inf`, list note; compact panel while there is no traffic |
| `js/gl.js`, `math.js`, `geom.js`, `renderer.js` | copied | none (no SFO dependency) |
| `js/scene.js` | adapted | no SFO grid import, no `parkAtGates` (random parked aircraft: never synthetic traffic); `scene.gateSys.items(now)` hook kept |
| `js/shaders/common.js` | adapted | the `vout` / `fout` chunks moved here (were at the top of sfo3d's `shaders/ground.js`, which is not forked) |
| `js/shaders/objects.js` | adapted | ground-contact AO used the literal `3.0` (SFO ground): now `uniform uGroundY` (set by app.js) |
| `js/shaders/env.js`, `post.js`, `sprites.js`, `aircraft.js`, `aircraft_real.js` | copied | none |
| `js/shaders/ground.js` | **new** | ZSSS ground shader (§3); no FAA runway markings; paint hook chunk `sha_ground_paint` |
| `js/world/textures.js` | copied | none (noise, clouds, waves; its SDF glyph atlas is generic and unused) |
| `js/world/ground.js` | **new** | airfield map, context map, Sentinel-2 hint, flat ground mesh, `pavedAt()` |
| `js/world/placeholders.js` | **new** | extruded building placeholders, control-tower stand-in |
| `js/geo.js` | **new** (sfo3d pattern) | ZSSS frame, twin of `tools/common/frame.py` (§2) |
| `js/aircraft/*` (8 files) | copied | none (airliner geometry, fit, liveries) |
| `js/aircraft/liveries.js` | adapted | `SHA_LIVERY_RES`, `SHA_LIVERY_BASE` (default `../sfo3d/data/liveries/`) |
| `js/live/models.js` | adapted | `SHA_EMBED`, `SHA_MODEL_BASE` (default `../sfo3d/data/models/`: sfo3d's `.sfom` by URL, not copied), `SHA_MODEL_EXT` |
| `js/live/aircraft.js` | adapted | `window.SFO` -> `window.SHA` |
| `js/live/lookup.js`, `earcut.js` | copied | none (see open issue 7) |
| `js/live/controls.js` | adapted | default pose; `GROUND_Y` is the ZSSS nominal 2.5 m |
| `js/live/ui.js` | adapted | SHA brand and views; clock `Asia/Shanghai`; no ATC sheet (Q4), no SFO gate-plan rows, flysfo links, US regional brands or runway-stats sheet; traffic label functions from `traffic_api.js`; `setLegend()`, `setNote()` |
| `js/live/entry.js` | adapted | data injection from `window.SHA_*`; imports the three extension files and `relay.js`; models by URL |
| `js/live/app.js` | adapted (rewritten around the contracts) | static scene; env glue, views, QA hooks, `window.SHA` (§6) |
| `js/live/world.js` | **new** (sfo3d role) | world assembly + extension calls (§5) |
| `js/live/ext.js` | **new** | extension registry (§5) |
| `js/live/markings.js`, `gates.js`, `terminals.js` | **new stubs** | one owner package each (§5) |
| `js/live/relay.js` | **new** | relay client config, OFF by default (§7) |
| `js/live/traffic_api.js` | **new** | Phase 2 stubs of `phaseLabel` / `category` / `gateLabel` (Phase 3 re-exports its engine's) |
| `js/live/about.js` | **new** | sources, licences, observed vs inferred |
| `js/env/clock.js` | adapted | `TZ = 'Asia/Shanghai'` |
| `js/env/ephemeris.js` | adapted | observer `SITE` = frame origin, AD ELEV 3.0 m (was `SFO`) |
| `js/env/state.js` | adapted | §4 |
| `js/env/app_env.js`, `atmo/*`, `wx/taf.js`, `aircraft_lights.js` | copied | `aircraft_lights.js` takes `DAY_GAIN` from the new `lighting/display.js` |
| `js/env/wx/metar.js` | adapted | ICAO trend groups cut (§4); routine-minute default 0 |
| `js/env/presets.js` | adapted | no KSFO presets (empty, same exports) |
| `js/env/lighting/photometry.js` | adapted | FAA fixture photometry removed (beams, PAPI) |
| `js/env/lighting/controller.js` | **new stub** | replaces the FAA JO 7110.65 controller: nothing switched, `tag: 'inf'` |
| `js/env/lighting/display.js` | **new** | `DAY_GAIN = 30` (sfo3d display constant) |
| `data/models/manifest.js`, `dock_foot.js`, `data/liveries/manifest.js`, `data/lookup.js`, `data/brands.js` | copied | model / livery metadata, VRS names (CC0); `.sfom` and livery textures stay in sfo3d |
| `data/sha_ground_s2.js` | **new** (generated) | Sentinel-2 colour hint (§3.3) |
| `tools/terrain/s2_ground_hint.py` | **new** | generator of `sha_ground_s2.js` |
| `tools/common/test_geo_js.mjs` | **new** | `js/geo.js` vs `frame.py` and the data |
| `livetest.mjs` | adapted | repo-root server, optional mock relay, no ADS-B mock (§8) |
| `jobs/views.mjs` | **new** | named views + orientation checks |
| `.gitignore` | edited | `out/` (harness default output) |

Not forked (SFO- or FAA-specific, or another package's): sfo3d `js/shaders/ground.js` (FAA runway marks, SFO city
bakes), `js/world/{terrain,airfield,buildings,gates,world}.js`, `js/live/{traffic,ground,gates,airport,markings,signs,
terminals,items,lights,feed,stats,atc}.js`, `js/env/lighting/{airfield,fixtures}.js`, `js/env/shore_field.js`,
`reservoirs_data.js`, `js/anim/*`, `js/three/**`, all `data/sfo_*`, `snapshot.js`, `buildings3d/`. No vendor file is
needed by the `live.html` path.

## 2. The ZSSS frame (`js/geo.js`)

- Constants copied from `tools/common/frame.py` (frame `ltp-wgs84-zsss`): origin 31.19784885 N 121.3362899 E (OD0),
  WGS 84 ellipsoid, exact local tangent plane, x east / z south / y up. `FIELD_ELEV_Y` 3.0, `GROUND_Y` 2.5 (nominal,
  inf), `K_DEM` 1.30, EGM2008 plane `N = 11.267 + 4.184e-5 x + 8.77e-6 z`.
- API: `wgs84ToWorld` / `worldToWgs84` (aliases `llToWorld` / `worldToLL`), `llToEN` / `enToLL`, **degree** headings
  `hdgVec(h) = [sin h, -cos h]`, `vecHdg`, `geoidN`, `haeFromY`, `yFromHae`, `yFromPressureAlt`, `groundY(x, z)` (flat,
  replaceable with `setGroundModel`), `checkFrame(frameBlock)`.
- Runway helpers from the injected data: `initGeo(airport)` fills `RUNWAYS` (id, heading, unit dir, pavement ends,
  length, width, shoulder, blast pads, surface segments, profile) and `RUNWAY_ENDS` (`18L` ... with landing threshold =
  DTHR, end of TORA, PAPI / ALS facts, declared distances); `rwyAlongAcross`, `rwyToWorld`, `rwyProfileY` (AIP THR /
  DTHR elevations, inf), `rwySurfaceAt`, `runwayAt`. `onRunwayHeadings(fn)` passes the four headings to the env stack.
- Gone: SFO ARP, NAD83 shift, the 117.83 / 27.83 grid, `GROUND_Y 3`, `GEOID_M 32.29`, SFO piers / ITB / bay polygons.

`node tools/common/test_geo_js.mjs` (run 2026-11-14): frame block matches; 1,681-point grid over ±6 km: JS vs
frame.py 8.3e-10 m (lat/lon -> world) and 2.8e-9 m (world -> lat/lon), round trip 1.8e-9 m; the 50 lat/lon + xz pairs
in `sha_airport.json` reproduced to 6.6 mm (the data round xz to 0.01 m); heights and pressure altitude identical;
runway directions match their headings to < 0.01°. **All passed.**

## 3. World

### 3.1 Ground pipeline

The sfo3d ground (a 120 km procedural region in the SFO s,t grid, a CPU airport map baked into albedo, FAA runway
markings in the shader) is replaced by:

| Layer | Content | Resolution | Source and status |
|---|---|---|---|
| Airfield map R | airside pavement: `surfaces.runway`, `runway_shoulders_blast_pads`, `taxiway`, `taxiway_shoulders`, aprons, helipads, extension pads | 1.0 m (high) / 1.25 / 1.6 (low) / 0.75 (ultra), 2,364 × 4,815 px at 1 m | OSM outlines (obs); surface widths inf (AIP widths on OSM axes) |
| G | concrete: runway segments from `aip_facts.surface_segments_m`; aprons (255), taxiways and helipads (204) | same | runways **obs (AIP mirror)**: 18L/36R asphalt with 100 m concrete ends, 18R/36L concrete; aprons / taxiways **inf** (no OSM surface tag; they are as bright as the concrete 18R/36L on Sentinel-2) |
| B | shoulders and blast pads, drawn as lighter asphalt | same | inf |
| A | landside roads inside the airfield rect | same | OSM (obs); width = lanes × 3.5 m or a class default (inf); tunnels and layer < 0 skipped; viaducts drawn at ground level (inf) |
| Context map R | water areas + waterway lines (river 16, canal 10, stream 5 m; ditch / drain 3 m as damp ground) | 4 m (6 m low), extent bbox + 900 m | OSM (obs); widths inf |
| G / B | roads / rail (5 m per line; no subway, no tunnels) | same | OSM (obs); widths inf |
| A | 0.5 × extent mask (blurred ~±350 m) + 0.5 × aerodrome mask (~±30 m) | same | extent = convex hull + 1 km (PLAN §6b Q3), aerodrome relation 21913346 |
| Sentinel-2 hint | surface reflectance colour of unpaved ground | 10 m, 457 × 703 px | obs (Copernicus) §3.3 |

The shader (`js/shaders/ground.js`) re-sharpens the bilinear map at magnification (threshold 0.5 with a derivative
width), so pavement edges stay crisp at stand distance from a 1 m map; concrete gets 5 m slabs on the runway grid
(177.3°; slab size inf), joints faded with distance; water gets a dark body plus Fresnel sky reflection; outside the
extent everything fades to one neutral grey-green (the luminance of the mean Sentinel-2 reflectance). The ground is flat
at `GROUND_Y` 2.5 m (the AIP runway profile varies 2.0-2.7 m: not drawn). Night: a faint urban glow outside the
aerodrome and a faint even apron level (inf; no fixture positions until the lighting package). Painted 3.17 km² of
airside pavement; ground build 1.2-1.7 s at 1 m on this sandbox (0.6 s at the low tier).

### 3.2 Buildings and the tower

- 436 placeholders (35 airport + 401 context buildings of `sha_airport.js`), extruded from footprint to `height_m`
  (all `height_src: inf`: rule defaults or AIP elevations), flat roofs, object-shader materials by kind (terminal glass,
  hangar metal, parking, punched windows, concrete). One item tagged `placeholder: 'buildings', src: 'inf'`.
- Control-tower stand-in at the OSM / AIP tower node (499.8, 130.2), 44.5 m (AIP elevation 47 m − ground, inf): a round
  shaft, glazed cab and roof. Form not sourced. **The tower node lies inside the OSM Terminal 1 outline** (osm:way/93184730,
  `source=estimation`), so the stand-in rises out of the 25 m T1 placeholder roof; the terminals package should resolve it.
- Anchors from the data: `world.anchors.t1` / `t2` (centroids of the OSM terminal outlines: T1 (581, 182) east of the
  runways, T2 (−1222, 218) west), `tower` ({pos, eyeY, top}).

### 3.3 Sentinel-2 ground-colour hint (optional item, done)

`python3 -I tools/terrain/s2_ground_hint.py` resamples the committed crop `refs/cache/s2/S2B_51RUQ_20261014_0_L2A`
(B04/B03/B02, 10 m, UTM 51N) onto the world frame through `frame.world_to_ll` + pyproj, 10 m pixels over the extent
bbox, nodata outside the extent polygon, and writes `data/sha_ground_s2.js` (PNG, 425 KB as JS). Reflectance = DN ×
0.0001: although the STAC bands list an offset of −0.1, `earthsearch:boa_offset_applied = true` and the pixel statistics
show the offset is already removed (5th-percentile DN 256 / 366 / 239; median red DN 925 ≈ TCI mean × 2000 / 255) [inf
from those statistics]. Mean reflectance of the extent 0.107 / 0.102 / 0.084. Attribution "Contains modified Copernicus
Sentinel data 2026" is in the About panel and the always-visible credit line. Colour only, no geometry. The extent
(23.5 km²) is not exceeded.

## 4. Environment (sun, sky, night, weather)

- Sun / Moon: sfo3d's ephemeris with the observer at the frame origin; clock and light modes (Real / Dawn / Day / Dusk /
  Night) in `Asia/Shanghai`. Node check: 2026-11-14 03:00Z (11:00 local): sun az 167.9°, el 39.7° (plausible for 31.2° N
  in mid-November; not re-verified against Horizons at ZSSS).
- METAR: **trend groups are cut** (`NOSIG` / `BECMG` / `TEMPO` end the observation; text kept in `trend`). Checked with
  the three ZSSS reports of sources_sim.md: `… BKN006 18/17 Q1017 BECMG TL0340 BKN011` now decodes one layer (BKN006),
  not two. MPS winds, metric visibility, CAVOK and Q groups were already handled.
- `state.js`: observer `SITE`; `FIELD_ELEV_FT` from AD ELEV 3.0 m; runway headings injected (`setRunwayHeadings`); the
  SFO West / Southeast plan fallback and its FAA Order 8400.9 limits are removed: the runway configuration is
  `not modelled (Phase 3 simulator: AIP runway mode + METAR wind)`, tag inf, with per-end headwind components for the
  HUD; the airfield-lighting controller is the inf stub; the remaining US photocell values (ASOS 0.5-3 fc, PAPI and
  obstruction photocells, Allard thresholds, USNO tower night) are labelled "inf placeholder" in place; HUD open-question
  text replaced.
- Without a relay there is no live weather (clear default, or `?metar=<raw>`); with a relay the app polls its METAR
  endpoint every 60 s (relay-side cache). Low BKN/OVC decks draw as the sfo3d cloud planes (checked with a mock BKN012 BR
  report, `core_wx_rwy_36L.png`).

## 5. Extension points (for the parallel packages)

`js/live/ext.js` holds a registry; each package owns one file that calls `registerExtension({...})`, and
`js/live/entry.js` already imports all three. Members (all optional except `name`):

| Member | Called by | Use |
|---|---|---|
| `shaderChunks: {sha_ground_paint: glsl}` | world.js, before any program compiles | procedural paint in the ground shader: `vec4 shaGroundPaint(vec3 wp, float fw, vec4 apt, float paved, inout float rough)` returns paint albedo + coverage (apt = airfield-map sample, paved = sharpened pavement coverage) |
| `groundUniforms(ctx)` | world.js | extra uniforms for that chunk (textures, parameter tables) |
| `pavement(api, airport)` | ground.js, while the airfield map is painted | `api.fill(rings, kind)` / `api.line(pts, w, kind)`, kind `paved` / `concrete` / `apron` / `shoulder` |
| `claimBuildings(airport)` | world.js | building ids (and `'tower'`) the package draws itself; the placeholders skip them |
| `buildWorld(ctx)` | world.js, after the core | returns `{items, sprites, gates, anchors, info}`; ctx = `{R, airport, stands, taxigraph, geo, groundY, quality, ground, textures, log, addItems}` |
| `start(app)` | app.js, once the scene exists | live systems: e.g. `app.scene.gateSys = sys` (its `items(nowMs)` are drawn every frame) |
| `frame(t, app)` / `lights(t, app)` | scene every frame | extra items / light sprites |

All hooks were exercised with throw-away test extensions (a paint stripe through the chunk + uniform, a pad through
`pavement`, T1 and the tower claimed and replaced, a light sprite, a `start` call), rendered, then the stubs restored.

The relay package owns `js/live/relay.js` (`RELAY` config, `detectRelay()`, `fetchMetarList()`); the Phase 3 traffic
package owns `js/live/traffic_api.js` (re-export its engine's label functions) and removes `body.no-traffic`.

## 6. `window.SHA` and the QA hooks

`window.SHA = {R, scene, rig, ui, world, view, applyEnv, qa, env(), envCore, geo, data, extensions, frameNow}`;
readiness `window.__shaReady` / `__shaError`; storage prefix `shalive.`. `SHA.qa`:
`hideUI`, `look(target, yawDeg, pitchDeg, dist, fov)`, `view(name)` (overview, t1, t2, runways, tower, top),
`threshold(end)` (behind the landing threshold, looking along the landing direction), `stand(name, dist, side, pitch)`,
`tower(dist, yaw, pitch)` (orbit), `placeModel(stand, icao)` (**QA only**: a neutral-livery model parked nose-in for
scale checks, never called by the app), `clearModels()`, `info()`.

## 7. Rules carried

- Relay OFF by default (`?relay=1` or `window.SHA_RELAY`); the browser never polls a provider in Phase 2; no OpenSky;
  adsb.lol ≤ 1 request / 180 s is recorded in `RELAY.adsbMinIntervalMs` for the relay; the harness mock answers only
  `/api/ping` and `/api/metar`. No User-Agent is sent by this package (no relay code here).
- No FAA marking / sign / lighting constants in the sha3d code path: the FAA runway marks, marking decals, signs, ALS /
  fixture data, the JO 7110.65 controller and the FAA beam / PAPI photometry are not forked or are removed; what remains
  of US origin is labelled `inf placeholder` (photocell thresholds) or is aircraft-side (14 CFR 25 aircraft lights, FAA
  aircraft characteristics in `fit.js`, the jet-bridge closure note in `dock.js` for the gates package). Audit:
  `grep -rn "117\.83\|27\.83\|32\.29\|37\.6188\|KSFO\|sfolive\|Los_Angeles\|window\.SFO\|SFO_" js` finds comments only
  (provenance notes and KSFO-specific decoder remarks in `metar.js`).
- Observed vs inferred: data `src` fields are kept; world items carry `placeholder` / `src: 'inf'`; list rows can show
  `obs` / `inf` chips; `ui.setLegend(html)` is the slot for the planned legend (`?legend=1` shows a one-line default).

## 8. Harness and renders

`livetest.mjs` serves the **repository root** (so `../sfo3d/data/models/` resolves) and opens `/sha3d/live.html`;
Playwright through `require('playwright')`; `SOFTGL=1` = Mesa llvmpipe as in sfo3d; Google Fonts are answered locally
(no route here). `jobs/views.mjs` prints orientation checks computed from the app's own data and renders named views at
deviceScaleFactor 1 (`?fixedres=1&quality=high&t=2026-11-14T03:00:00Z`, 11:00 local):

```
SOFTGL=1 OUT=docs/phase2 PREFIX=core node livetest.mjs jobs/views.mjs
check: T2 x -1222 < runway x min -445 -> T2 WEST ok
check: T1 x 581 > runway x max 79 -> T1 EAST ok
check: runway headings 18L/36R 177.34, 18R/36L 177.31 N-S ok
```

| Render | View | What I checked |
|---|---|---|
| `core_overview.png` | from the south-east, looking north-west | the extent "island" with the neutral fade; T2 + piers + the Hongqiao rail station on the west (left), T1 on the east (right); runways run away from the viewer |
| `core_top.png` | top, north up | runways vertical (N-S), T2 left = west, T1 right = east; matches the Sentinel-2 hint and Phase 1 plates |
| `core_runways.png` | from the south, looking north along both runways | T2 complex left (west), T1 right; east runway darker (asphalt), west runway concrete |
| `core_rwy_18L.png`, `core_rwy_36R.png` | behind the threshold of each end, looking along the landing direction | 45 m asphalt runway with the 100 m concrete end and the 60 m blast pad beyond it (AIP mirror); no markings yet |
| `core_rwy_18R.png`, `core_rwy_36L.png` | same | 60 m concrete runway, taxiway pattern and shoulders |
| `core_t1.png`, `core_t2.png` | terminals from their airside | T1 placeholder east, T2 with its piers and aprons west |
| `core_tower.png`, `core_towercab.png` | tower stand-in (orbit) and the app's cab view | stand-in on the T1 roof (see §3.2); cab eye 42.5 m looking west over the runways |
| `core_stand_233_A320.png` | stand 233 (T2 apron, heading 257°) with a QA-only A320 (sfo3d `a320.sfom` by URL) | scale: the 37.6 m aircraft spans about 7.5 concrete slabs of 5 m and sits on the apron, nose at the stop node |
| `core_night_t2.png` | 21:30 local | dark scene, lit terminal glazing, faint apron level; no airfield lights yet |
| `core_wx_rwy_36L.png` | mock relay METAR `5000 BR BKN012` | overcast deck and mist from the relay METAR path |
| `core_phone_overview.png` | 390 × 844, iPhone UA, touch, low tier, HUD on | top bar fits; view buttons scroll horizontally; bottom sheet with the "no traffic yet" note |
| `core_laptop_t2.png` | 1280 × 720, HUD on | top bar, view bar, compact list panel, credit line |

Render times on this sandbox (llvmpipe, 1280 × 720, high tier): about 15 s per view including model loads.

## 9. Open issues

1. **Neutral fade looks like an island** from overview heights: by design (nothing beyond the Q3 extent), but a softer
   horizon (e.g. a wider fade or more haze) may read better. Owner taste.
2. **No terrain heights**: everything is flat at 2.5 m; the runway profile (2.0-2.7 m) and canal banks are not drawn.
   Water is a ground-shader material at ground level.
3. **Roads**: viaducts and bridges (269 OSM ways with bridge / layer > 0, much of the Hongqiao hub) are drawn at ground
   level; road and water widths are class defaults.
4. **Aprons and taxiways are drawn concrete** by rule (inf). Slab size 5 m is inf. Shoulder and blast-pad tone inf.
5. **Tower inside the T1 outline** (§3.2): for the terminals package. The OSM T1 outline is `source=estimation`.
6. **Night** is only a placeholder glow; airfield lighting (AD 2.14: PALS CAT I, PAPI, RCLL, REDL, RWSL, stop bars) needs
   the lighting package and CAAC photometry. The env HUD's photocell thresholds are sfo3d / US values (inf).
7. **Copied US-oriented tables**: `data/brands.js` (US DOT BTS registration -> brand) and the SFO-observed freighter /
   cargo rules in `js/live/lookup.js` are inert without traffic; the fleet / livery package should replace them.
8. **METAR QNH**: `metarSummary().altim` is US inHg-only, so a ZSSS `Q1021` gives no `altim` (only needed by the Phase 3
   traffic engine for baro altitudes).
9. **Fonts**: `live.html` still links Google Fonts (R10); the UI falls back to system fonts without them.
10. Sun / Moon positions were not re-verified against JPL Horizons at ZSSS (same algorithm as sfo3d's verified one).
11. The relay itself (`sha_live_server.py`) and the Observed / Inferred legend content are other packages.
