# Phase 2 fork map: sfo3d @ a967f9b → hwd3d (the contract for P1–P4)

Written 2026-11-13 for the Phase 2 builders. This is the contract all four packages follow:
- **P1**: relay, replay and taxigraph;
- **P2**: world and renderer;
- **P3**: traffic;
- **P4**: app shell and harness.

The packages build in parallel. Each edits only its own files (FILE OWNERSHIP in the workflow brief, repeated in §1).
Each reaches the others only through the interfaces in §2.

Labels:
- **[obs]**: read in the sfo3d code at a967f9b, or measured here.
- **[inf]**: inferred, or a design choice made in this map. Choices can be reversed by the orchestrator.
- **[verify]**: the owning package must check this against the original source before it ships, and record the
  check in its `docs/phase2_*.md`.
- **contract**: a binding interface. Changing it needs the orchestrator, because other packages build against it.

---

## 0. What sfo3d runs today

**Pages** [obs]
- `sfo_live_server.py` `do_GET` (line 1709) answers `/` with a 302 to **`live3.html`**, keeping the query string.
- `live3.html` is the three.js r186 renderer (WebGPU, with a WebGL 2 fallback). An import map swaps four modules:
  `js/gl.js`, `js/renderer.js`, `js/scene.js` and `js/world/world.js` → `js/three/compat/*`.
- `live.html` is the same app on the custom WebGL2 renderer. `docs/research/engine_impl.md` says "live.html and its
  renderer are untouched".
- Both pages load the same entry module, **`js/live/entry.js`** → `js/live/app.js` `startApp(cfg)`.

**Decision for hwd3d (contract).** hwd3d forks the **`live.html` path**: plain ES modules and the custom WebGL2
renderer, as the workflow brief and PLAN §4 require. `js/three/**` (5,363 lines) and `vendor/three` are not forked.
`hwd_live_server.py` answers `/` with a 302 to `live.html`.

**Import graph of `js/live/entry.js`** [obs]
- Measured with a small probe that walks the static and dynamic `import` statements.
- 86 modules: 68 JS modules (19,512 lines) and 18 `data/*.js` modules.
- JS files that are not in the graph:
  - `js/main.js`, `js/shots.js`, `js/overlay.js` and `js/livedata.js`: the video era (`index.html`, `render.mjs`);
  - `js/env/atmo/exposure.js`;
  - `js/three/**`.

**Boot** (`startApp`, app.js lines 76–533) [obs]
1. `UI` is created.
2. `initGL(canvas)`, then the float render-target check.
3. `new Renderer(rw, rh, {msaa, shadowRes})`.
4. `buildLiveWorld(R, airport, log, {terrainStep, mapRes, details, buildings, stands, paint, pavement, runways})`.
5. Water and reservoir items are added.
6. `new Scene(R, world)`.
7. `LiveGateSystem` (jet bridges).
8. `AirfieldLighting` (3,633 fixture faces from `data/sfo_lighting.js`).
9. `AppEnv`, then `applyEnv()`: sky, fog, clouds and the ground bake.
10. `new Traffic({gates, airport, persist, centerlines, taxigraph, stands, onGateChange})`.
11. Bridge hooks (`bridgeK`, `pushClearEta`, `canDock` …).
12. `new GroundPhysics({paved, building, net, bridges})`.
13. `CameraRig`.
14. The feed: snapshot reload every 90 s, `StreamFeed` (relay SSE) or `Feed` (direct polling).
15. Polling of `/api/gates`, `/api/routeset`, `/api/metar` and `/api/taf`.
16. The `tick` loop.

**Per frame** (`tick`) [obs]
1. `traffic.update(now, dt)`.
2. `physics.resolve(traffic, dt)`.
3. `syncViews(now)`: tracks → `LiveAircraft` or a marker sprite.
4. `rig.update(dt)`.
5. `applyEnv` every 30 s.
6. `scene.frame(simT, camPos)`.
7. `R.render(fr, cam, simT, post)`, `scene.commit()` and `R.present(...)`.
8. `labels(C, now)`.
9. List and status every 1 s; the selected card every 0.5 s.
10. Dynamic resolution, targeting 33 ms.

**Relay** (`sfo_live_server.py`, 1,979 lines, VERSION 0.3, Python stdlib) [obs]
- `Poller` threads poll adsb.lol (1.0–1.5 s with jitter) and adsb.fi (every 2 s at an even second + 0.3 s).
  - On HTTP 429 the poller backs off exponentially.
  - It also keeps an adaptive floor: ×1.5 per 429, ×0.9 per success.
- `Hub._merge` merges per aircraft: the freshest position wins, with MLAT/TIS-B hygiene, surface `track` dropped, and a
  sticky `_veh` flag.
- SSE fan-out at `/api/stream`: full and delta events.
- `Metar`: conditional upstream fetches; cached METARs in replay.
- `--replay` re-times recorder files to wall time.
- `--record` writes `record.py`-format files. (amended, fix round 2) The directory is accepted only when, inside hwd3d/, it
  is under `refs/cache/local/` or `out/` (exact case, not `out/replay/`) and, anywhere in a git work tree, `git
  check-ignore` says it is ignored (`record_dir_check`).
- Static serving denies `refs`, `tools`, `node_modules`, `out`, `jobs` and dotfiles.
- SFO-only parts: `FaaRegistry` (transport types), `Routes` (adsb.lol routeset / VRS mirror) and `Gates` (flysfo.com).

**Tools and harness** [obs]
- `tools/live/build_taxigraph.py`: OSM segments, plus runway centrelines from the FAA ends.
- `build_stream.py`: recordings → the exact SSE event sequence, through the Hub on a fake clock.
- `replay_engine.mjs` / `invariants.mjs`: the traffic engine in Node on that stream.
- `tools/build3/replay_pack.py` + `replay_shim.js`: a packed window of real traffic. The phone artifact replays it
  in the page through fake relay endpoints.
- `livetest.mjs`: a static server, a mock relay built from `data/snapshot.js`, headless Chromium and screenshots;
  each job script exports `default async ({page, shot, base, W, H, OUT})`.

**Not read in full for this map**
- In `traffic.js`: the bodies of `airLogic`, `groundLogic`, `ctlGround`, `ctlAir` and `target` (about 2,000 lines).
- `gates.js`, `signs.js` / `markings.js` internals, `env/state.js` internals and the shader bodies.

Their interfaces and their SFO couplings are listed below. P2 and P3 read the bodies they fork.

---

## 1. Module table

Columns:
- **Verdict**:
  - *copy*: unchanged apart from the fork header;
  - *adapt*: kept, with the listed changes;
  - *replace*: new HWD code takes its role;
  - *drop*: not needed.
- **Pkg**: the package that owns the hwd3d target.

Every forked file starts with the header pattern of `hwd3d/js/geo.js`:

```
// Forked from sfo3d/<path> @ a967f9b. Kept: …. Changed: …. Dropped: ….
```

### 1.1 Page, shell, harness (P4)

| sfo3d file | Lines | Purpose | SFO-specific dependencies | Verdict | Pkg | hwd3d target |
|---|---|---|---|---|---|---|
| `live.html` | 13 | page, fonts, `#app`, entry module | title | adapt | P4 | `live.html` |
| `live3.html` | 34 | three.js import map | three.js path | drop | — | — |
| `live.css` | 254 | mobile-first UI styles | none of note | adapt | P4 | `live.css` |
| `js/live/entry.js` | 36 | mode, relay detection (`j.sfolive`), taxigraph, models, `startApp` | 7 `data/sfo_*.js` imports, `MODEL_KEYS`, `SFO_EMBED`, `__sfoReady` | replace | P4 | `js/live/entry.js` |
| `js/live/app.js` | 596 | boot, loop, env glue, views, labels, QA hooks | stands and bridges (75 lines mention gate/bridge/dock/stand), `RUNWAY_SIGNS` 10L/10R/1L/1R, ALS planes, reservoirs and shore, flysfo plan, routes, LiveATC tuning, `GROUND_Y` = 3, camera presets in SFO coordinates, `window.SFO` | adapt (rewritten around §2) | P4 | `js/live/app.js` |
| `js/live/ui.js` | 371 | status bar, list, card, labels, sheets | SFO plan, gate and route text, ATC sheet | adapt | P4 | `js/live/ui.js` |
| `js/live/controls.js` | 171 | `CameraRig`: pan, zoom, tilt, follow, tower | `GROUND_Y` in ground picking; far 160–180 km, orbit near/split scaled to the camera distance | adapt (`heightAt` from the site, near/far for a 2 km field) | P4 | `js/live/controls.js` |
| `js/live/about.js` | 46 | About and credits HTML | SFO sources | replace (notices of `docs/ATTRIBUTION.md`) | P4 | `js/live/about.js` |
| `js/live/atc.js` | 172 | LiveATC mounts, roles, audio delay | SFO mounts, Chart Supplement edition | replace (D2: a single link to `https://www.liveatc.net/search/?icao=KHWD`) | P4 | `js/live/atc.js` |
| `js/live/stats.js` | 118 | runway statistics from the engine events | 4 SFO runways, arrival/departure semantics | adapt (HWD event kinds, §2.8) | P4 | `js/live/stats.js` |
| `livetest.mjs` | 84 | static server, mock relay, Chromium, `shot()` | mock reads `data/snapshot.js`; `/api/ping` returns `sfolive`; mock METAR KSFO; routeset mock | adapt (§2.10) | P4 | `livetest.mjs` |
| `jobs/*.mjs` | 34 files | QA, UI, relay, memory and perf jobs | gate, dock, lineup and bridge views | adapt `qa3`, `uitest`, `relaytest`, `memtest`; drop the gate/dock/bridge jobs | P4 | `jobs/**` |
| `package.json` | 7 | playwright, esbuild, three | three | adapt (no three) | P4 | `package.json` |
| `tools/build3/phone_artifact.sh`, `phone_artifact_page.py`, `phone_artifact_template.html` | — | single-page phone artifact | three.js bundle | adapt later (Phase 6); a Phase 2 artifact build may live in `jobs/` | P4 | `jobs/` |

### 1.2 Renderer core and shaders (P2)

| sfo3d file | Lines | Purpose | SFO-specific dependencies | Verdict | Pkg | hwd3d target |
|---|---|---|---|---|---|---|
| `js/gl.js` | 211 | WebGL2 context, `Program`, `Mesh`, `texture`, `FBO`, chunks | none | copy | P2 | `js/gl.js` |
| `js/math.js` | 143 | `v3`, `m4`, noise, `Path` | none | copy | P2 | `js/math.js` |
| `js/geom.js` | 127 | `Geo` builder (`box`, `extrude`, `lathe`, `cylinder`, `merge`, `data()`), earcut | none | copy | P2 | `js/geom.js` |
| `js/renderer.js` | 334 | 3 shadow cascades, MSAA, sky precompute, main and far passes, motion blur, bloom, post | default `shadowSplits` [120, 700, 3500] are airliner scale; far range | adapt (retune for 8–15 m aircraft) | P2 | `js/renderer.js` |
| `js/scene.js` | 83 | static items + aircraft items + sprite batch + smoke | imports `aircraft/fleet.js`, `aircraft/model.js`, `shaders/aircraft*.js`, `world/gates.js`; `parkAtGates` (video era) | adapt: no `js/aircraft/**` import, generic drawables (§2.5) | P2 | `js/scene.js` |
| `js/shaders/common.js` | 171 | chunks, sky precompute, fullscreen VS | none | copy | P2 | `js/shaders/common.js` |
| `js/shaders/ground.js` | 467 | terrain/airfield shading, runway SDF glyphs, thresholds, displaced-threshold arrows, blast-pad chevrons, bakes (airfield, aux, city, far city) | airport (s,t) grid (`uVw`/`uUw`, `APT_RECT`), `uRw` with runway axis 0/1 for 4 runways, `END_ZONES` / EMAS, city bakes | adapt (HWD grid along 10/28, 2 parallel runways, PIR/NPI markings, no city) | P2 | `js/shaders/ground.js` |
| `js/shaders/env.js` | 210 | sky, environment map, water, decal, cloud | Bay water (optional at HWD) | copy | P2 | `js/shaders/env.js` |
| `js/shaders/objects.js` | 151 | generic PBR-ish object shader (`obj`, `objI` instanced) | none | copy | P2 | `js/shaders/objects.js` |
| `js/shaders/post.js` | 92 | motion blur, bloom, final grade | none | copy | P2 | `js/shaders/post.js` |
| `js/shaders/sprites.js` | 71 | light sprites, smoke | none | copy | P2 | `js/shaders/sprites.js` |
| `js/shaders/aircraft.js` | 201 | procedural airliner shader (livery uniforms) | airliner | drop (placeholders use `obj`, §2.9) | — | — |
| `js/shaders/aircraft_real.js` | 149 | imported-model shader | airliner atlases | drop for Phase 2; Phase 3 may bring it back as `acr` | — | — |

### 1.3 World and airport (P2)

| sfo3d file | Lines | Purpose | SFO-specific dependencies | Verdict | Pkg | hwd3d target |
|---|---|---|---|---|---|---|
| `js/world/world.js` | 112 | `buildBaseWorld` (video era), `bakeGround`, `CITY_RECT` | SFO city bakes, `APT_RECT` | adapt: keep `bakeGround` and drop the city | P2 | `js/world/world.js` |
| `js/world/terrain.js` | 347 | procedural 120-km region, Bay, reservoirs, `polySDF` | `data/sfo_shore.js`, reservoirs, `BAY_WATER_KM`, `AIRPORT_LAND_ST` | replace: field surface from the NASR runway profiles (`geo.js rwySurfaceY`) + nominal ground [inf]; USGS 3DEP optional later | P2 | `js/world/terrain.js` |
| `js/world/airfield.js` | 274 | `APT_RECT`, `RWY` in (s,t), hard-coded SFO taxiways/aprons, painter | all SFO | replace (an HWD grid aligned with 10/28, see §4.2 R14) | P2 | `js/world/grid.js` (new) |
| `js/world/textures.js` | 157 | glyph atlas, wave, cloud and noise textures | none | copy | P2 | `js/world/textures.js` |
| `js/world/buildings.js` | 151 | video-era SFO buildings, `MAT` table | SFO | drop (copy `MAT` if useful) | — | — |
| `js/world/gates.js` | 309 | `GateSystem` bridges, GSE meshes | SFO | drop | — | — |
| — | — | **site model** (pure, Node-importable): ground height, pavement, surfaces, buildings | — | new (§2.4) | P2 | `js/world/site.js` |
| `js/live/world.js` | 141 | `buildLiveWorld`: terrain, water, ground uniforms, markings, signs, masts, EMAS, buildings | SFO data, EMAS, masts, Blender asset groups | replace (`buildHwdWorld`, §2.4) | P2 | `js/live/world.js` |
| `js/live/airport.js` | 439 | stands (`standGates`), pavement/concrete/paint map, end zones, buildings | SFO Museum polygons, stands, EMAS | replace (airport map from `HWD_AIRPORT`) | P2 | `js/live/airport.js` |
| `js/live/markings.js` | 201 | anti-aliased decal ribbons (centrelines, hold bars, edges, stand lead-ins, red boxes) | `sfo_details` centrelines, stand marks | adapt (taxiway centrelines, measured hold bars, Green Ramp tee rows) | P2 | `js/live/markings.js` |
| `js/live/signs.js` | 216 | sign atlas + placement | SFO sign list | adapt: keep the atlas and shader; place **no** HWD signs until they are sourced (`not_yet_sourced`) | P2 | `js/live/signs.js` |
| `js/live/terminals.js` | 233 | terminals, ITB, tower | SFO | replace (tower from OSM way 204803620, 15.85 m [obs OSM]) | P2 | `js/live/buildings.js` |
| `js/live/items.js` | 33 | floodlight masts | SFO OSM masts | drop | — | — |
| `js/live/lights.js` | 41 | ALS structures, taxi-edge positions | SFO ALS | replace (static sprites only where sourced, e.g. the lighted windsock; fixtures in Phase 4) | P2 | `js/live/lights.js` |
| `js/live/earcut.js` | 177 | triangulation | none | copy | P2 | `js/world/earcut.js` |

### 1.4 Environment (P2, `js/env/**`)

| sfo3d file | Lines | Purpose | SFO-specific dependencies | Verdict | hwd3d target |
|---|---|---|---|---|---|
| `js/env/app_env.js` | 90 | data clock, reports, EnvState, HUD | KSFO presets | adapt (station `KHWD`, no TAF) | `js/env/app_env.js` |
| `js/env/clock.js` | 92 | `DataClock`, TZ, query overrides | `TZ = 'America/Los_Angeles'` (also right for Hayward [inf]) | copy | `js/env/clock.js` |
| `js/env/ephemeris.js` | 429 | Sun/Moon (Meeus), illuminance | `SFO` observer constant | adapt (HWD observer from `geo.js ARP`) | `js/env/ephemeris.js` |
| `js/env/state.js` | 466 | EnvState: fog slabs, clouds, wind, runway configuration, photocell | `FIELD_ELEV_FT = 13.1`, SFO West/Southeast plans, `IAP_ENDS`, routine minute 56, 'FG IN GAP' patches | adapt: 52.1 ft; flow from ADS-B and wind; KHWD routine minute (§2.6) | `js/env/state.js` |
| `js/env/presets.js` + `data/sfo_env_presets.js` | 19 + 11 | KSFO weather presets and snapshot TAFs | KSFO | replace (empty, or KHWD presets later) | `js/env/presets.js` |
| `js/env/wx/metar.js` | 604 | METAR/SPECI decoder → render parameters | `routineMinute = 56` default | copy (station-agnostic decoder; pass 54) | `js/env/wx/metar.js` |
| `js/env/wx/taf.js` | 94 | TAF decoder | — | copy (unused: there is no KHWD TAF, §2.1) | `js/env/wx/taf.js` |
| `js/env/atmo/sky_model.js` | 321 | sky, fog transmittance, slabs | none | copy | `js/env/atmo/sky_model.js` |
| `js/env/atmo/weather_fx.js` | 164 | rain, lightning, wetness | none | copy | `js/env/atmo/weather_fx.js` |
| `js/env/aircraft_lights.js` | 218 | aircraft light states and sprites (14 CFR 25.1385–1401) | airliner (Part 25) | adapt; for GA, check Part 23 [verify] | `js/env/aircraft_lights.js` |
| `js/env/lighting/photometry.js` | 158 | cd, Allard, beams, PAPI optics | none | copy | `js/env/lighting/photometry.js` |
| `js/env/lighting/airfield.js`, `controller.js`, `fixtures.js` + `data/sfo_lighting.js` | 307 + 149 + 146 | 3,633 SFO fixture faces, JO 7110.65 controller | SFO ALS, REIL, TDZ | replace in Phase 4 (HWD MIRL, VASI, PAPI, REIL; positions not sourced) | — |
| `js/env/shore_field.js`, `reservoirs_data.js` | 59 + 2 | seawall foam, reservoirs | SFO | drop | — |
| — | — | env → renderer glue (moved out of app.js) | — | new (§2.6) | `js/env/render_env.js` |

### 1.5 Traffic, physics, feed and identity (P3)

| sfo3d file | Lines | Purpose | SFO-specific dependencies | Verdict | hwd3d target |
|---|---|---|---|---|---|
| `js/live/traffic.js` | 3,247 | ingest hygiene, Hermite + dead reckoning, kinematic body (`ctlGround`/`ctlAir`/`attitude`), phase machine, `TaxiNet`, stand matching, bridges, flysfo plan, parked persistence | 1,230 lines mention gate/bridge/dock/stand/plan/push/tow/block/lead-in [obs grep]; `STANDS` import; `inAirport` SFO box; 4-runway `RWY`/`PARALLEL`; `LIFTOFF_KT` airliner table; 40 kt "airplanes do not fly below" rule; `GEOID_M = 32.29` (SFO); `ANT = 0.2 L`; `DR_MAX_S = 5`; `DELAY_MAX = 3000`; `STORE_KEY` `sfolive.parked.v4` | adapt by extraction. Keep ingest/report hygiene, `sampleReps`, the kinematic body, fades/cuts, stale/parked persistence and `TaxiNet` (+ routing). Drop stands, bridges, plan, silent docking, push-back/tow. Phases → `classifier.js`, spots → `parking.js` | `js/live/traffic.js` |
| — | — | GA phase classifier | — | new (§2.8, §3) | `js/live/classifier.js` |
| — | — | parking model (tie-downs, ramp spots, hangar aprons, helipads, hangared) | — | new (§2.8) | `js/live/parking.js` |
| `js/live/ground.js` | 465 | `GroundPhysics`: solid planforms, pavement, buildings, bridges | jet bridges (`restBridgeField`, `liveBridges`), airliner planform (`samples`: sweep 27°, nose gear 3 m, track 6 m defaults), ICAO Annex 14 codes, `GROUND_Y` | adapt (GA planforms incl. taildraggers and rotors; no bridges; site `groundY`) | `js/live/ground.js` |
| `js/live/feed.js` | 163 | `normalizeAircraft`, `parsePayload`, `Feed`, `StreamFeed`, `Routes`, `fetchMetar`/`Taf`/`Gates` | `SOURCES` 40 nm, routes, gates, KSFO default | adapt (keep `normalizeAircraft`/`parsePayload`/`StreamFeed`/`fetchMetar`; add `_masked`/`_mx`/`nac_p`; drop `Routes`/`fetchGates`) | `js/live/feed.js` |
| `js/live/lookup.js` + `data/lookup.js`, `data/brands.js` | 214 | airline, brand and livery lookup, `nNumberFromHex` | airline tables | replace (identity record, D1, type class; §2.7) | `js/live/lookup.js` |
| `js/live/aircraft.js` | 218 | `LiveAircraft` (imported model + procedural fallback + livery) | airliner models | replace (`AircraftViews` + GA placeholder drawables, §2.9) | `js/live/aircraft.js` |
| `js/live/models.js` | 296 | `.sfom` decoder, registration texture | airliner atlases | Phase 2: copy only `decodeModel`, `registrationLayout`/`registrationTexture` if needed; Phase 3 adapts | `js/live/models.js` |
| `tools/live/replay_engine.mjs`, `invariants.mjs`, `replay_app.mjs` | 156 + 681 + 139 | engine in Node on the real stream; invariants per frame | bridges, stands, SFO data | adapt (no bridge classes; add the GA classes of §3) | `tools/traffic/` |

### 1.6 Aircraft (P3, `js/aircraft/**`)

| sfo3d file | Lines | Purpose | Verdict | hwd3d target |
|---|---|---|---|---|
| `js/aircraft/types.js` | 411 | airliner `TYPES` (dims, wing, doors, windows, lights) | replace | `js/aircraft/ga_dims.js` (generated from `data/ga_types.json` by `tools/traffic/build_ga_dims.py`) |
| `fit.js`, `model.js`, `fleet.js`, `stretch.js`, `cockpit.js`, `liveries.js`, `dock.js` | 798 + 343 + 146 + 133 + 116 + 72 + 131 | airliner procedural airframe, model fitting, liveries, bridge foot | drop (Phase 3 may reuse `model.js` patterns) | — |
| — | — | GA placeholder geometry + drawable | new (§2.9) | `js/aircraft/placeholder.js` |

### 1.7 Relay and live tools (P1)

| sfo3d file | Lines | Purpose | SFO-specific dependencies | Verdict | hwd3d target |
|---|---|---|---|---|---|
| `sfo_live_server.py` | 1,979 | relay | `ARP` KSFO; radius 40 nm; `FaaRegistry`/`faa_icao`; `Routes`; `Gates` (flysfo); KSFO METAR/TAF and TTL schedule around hh:56; `/` → `live3.html`; `sfolive` ping | adapt (§2.1). Keep `Http`, `Poller`, `RecordWriter` (adsb.lol only), `Clock`, `Hub` merge and hygiene, `Metar` (KHWD), replay, `StaticGzip`, handler and SSE. Drop lines 108–187 (FAA) and 790–1406 (routes, flight/stand helpers, gates). Add Mictronics enrichment, D1 masking, pack serving | `hwd_live_server.py` |
| `tools/live/recio.py` | 54 | robust gzip JSON-lines reader | — | copy + an `.xz` reader (rec_pack) | `tools/live/recio.py` |
| `tools/live/record.py` | 100 | recorder (both providers) | SFO centre | adapt optional: adsb.lol only, HWD centre; never record adsb.fi | `tools/live/record.py` |
| `tools/live/build_stream.py` | 91 | recordings → SSE sequence through the Hub | imports `sfo_live_server` | adapt (rec_pack `.jsonl.xz` input) | `tools/live/build_stream.py` |
| `tools/build3/replay_pack.py` + `replay_shim.js` | — | pack v2 (field deltas) + in-page fake relay | routes, `sfolive` | adapt (§2.2) | `tools/live/build_pack.py`, `tools/live/replay_shim.js` |
| `tools/live/build_snapshot.py` + `data/snapshot.js` | 80 | one-instant snapshot | KSFO; `data/snapshot.js` mixes adsb.fi records (licence conflict, sfo3d `docs/ATTRIBUTION.md`) | drop (the pack replaces it) | — |
| `tools/live/build_taxigraph.py` | 109 | OSM segment soup + runways + aprons + lead-ins | SFO OSM, retired pavement | replace (input `data/hwd_airport.json`; node graph, §2.3) | `tools/live/build_taxigraph.py` |
| `tools/live/test_relay.py`, `relay_smoke.py` | 298 + 178 | relay tests | SFO | adapt | `tools/live/` |
| `tools/live/replay_*.py`, `analyze_feeds.py`, `gatecheck.py`, `drgap.py`, `card_replay.mjs` | — | SFO replay audits, flysfo checks | SFO | drop (Phase 5 may fork `replay_score`/`replay_events`) | — |

### 1.8 Data modules

| sfo3d data | Replaced by | Owner |
|---|---|---|
| `data/sfo_airport.js`, `sfo_details.js`, `sfo_buildings.js`, `sfo_stands.js`, `sfo_paint.js`, `sfo_pavement.js`, `sfo_landside.js`, `buildings3d/integration.js` | `data/hwd_airport.js` (`HWD_AIRPORT`, Phase 1, frozen) | — |
| `data/sfo_taxigraph.js` | `data/hwd_taxigraph.{json,js}` (`TAXIGRAPH`) | P1 |
| `data/sfo_shore.js`, `sfo_lighting.js`, `sfo_env_presets.js`, `js/env/reservoirs_data.js` | nothing in Phase 2 | — |
| `data/lookup.js`, `brands.js`, `liveries/manifest.js`, `models/manifest.js`, `models/dock_foot.js`, `models/*.sfom` | `js/aircraft/ga_dims.js` (generated); models in Phase 3 | P3 |
| `data/snapshot.js` | `out/replay/pack.json.gz` (generated, gitignored, §2.2) | P1 |

### 1.9 Not forked

- `js/three/**`, `vendor/three`, `live3.html`, `tools/build3/*` (except the replay pack and shim).
- `index.html`, `render.mjs`, `bench.*`.
- `js/main.js`, `shots.js`, `overlay.js`, `livedata.js`.
- `js/anim/lights.js` (263) and `js/anim/traffic.js` (126): SFO ALS and video kinematics.
- `js/live/gates.js` (2,091 lines of jet bridges, VDGS and GSE).

### 1.10 Frozen files and ownership gaps

**Frozen (Phase 1).** No Phase 2 package edits these files; all packages read them:
- `js/geo.js` and its twin `tools/common/hwd_frame.py`;
- `data/hwd_airport.{json,js}` and `data/ga_types.json`;
- `refs/**` and `tools/{airport,adsb,osm,imagery,faa,registry,types}/**`.

A needed change goes to the orchestrator as a request. Wishes for sfo3d are collected in §5; the orchestrator moves
them to `docs/requests_to_sfo3d.md`.

**New files** fit the ownership lists as follows:
- `js/world/site.js`, `js/world/grid.js`, `js/world/earcut.js` and `js/env/render_env.js`: P2.
- `js/live/classifier.js`, `js/live/parking.js`, `js/aircraft/ga_dims.js` and `js/aircraft/placeholder.js`: P3.
  Taxi-graph routing lives in `js/live/traffic.js` (`TaxiNet`), as in sfo3d.
- `tools/live/build_pack.py` and `tools/live/replay_shim.js`: P1. The shim is copied into `out/replay/` at pack time.

---

## 2. Interface contracts

### 2.0 Shared conventions (all packages)

**World frame and units** [obs `js/geo.js`]
- World frame `ltp-nad83-2011-hwd`: x = east, z = south, y = up, in metres. The origin is the NASR ARP.
- **y is the NAVD 88 height in metres, not a constant ground.**
  - The runway surfaces run from 8.44 m (10R end) to 15.88 m (28L end): `geo.js rwySurfaceY`.
  - `GROUND_Y = 11.4` is only a nominal fallback.
  - Everything that stands on the ground uses **`site.groundY(x, z)`** (§2.4). sfo3d's `GROUND_Y = 3` appears in
    `traffic.js`, `ground.js`, `controls.js`, `app.js` and `scene.js`; every such use must be replaced.
- ADS-B and OSM WGS 84 → world: `wgs84ToWorld(lat, lon, h)`. FAA NASR and NAIP use NAD83 → `llToWorld`.

**Headings** (contract)
- Across package boundaries a heading is in **degrees true**, [0, 360), clockwise from north, matching
  `hwd_airport.json`, `geo.js` and ADS-B.
- The world unit vector is `geo.js hdgVec(deg) = [sin, −cos]`. That function takes **degrees**.
- sfo3d's `traffic.js` `hdgVec` takes **radians**. Never import both into one module. Inside a package, radians are
  fine.
- Attitude: `pitch` and `roll` are in radians, nose up and right wing down positive (sfo3d `Aircraft.matrix`).
- Drawables are oriented by `fwd` = a unit [x, 0, z] vector.

**Time**
- Data and display times are epoch milliseconds.
- The relay's `_pt` is epoch **seconds** on the relay clock (sfo3d semantics).
- `displayTime(now) = now − delay`.

**Track keys** (contract): a string.
- A lower-case ICAO hex (`a1b2c3`).
- `~xxxxxx` for non-ICAO / anonymous targets (readsb semantics).
- `x` + 8 hex characters for a **D1-masked** aircraft (§2.1).
- A key is an internal handle. **No UI text, label, URL or log line shown to users may contain a key.**

**Provenance.** Every derived element or decision carries `src: 'obs' | 'inf'`. A rule-made classification also
carries `rule` (a short id, e.g. `hwd_events.touch_and_go.contact`) and `evidence` (a short text). The UI shows `inf`
visibly: an "inferred" marker on the card.

**D1** (privacy; §2.1 for the mechanism)
- An aircraft flagged LADD or PIA shows its **type only**: no registration, callsign, operator or address, anywhere in
  the UI.
- No committed file holds a per-aircraft identity derived from ADS-B.
- `out/` (generated) is gitignored [obs `hwd3d/.gitignore`: `out/`, `refs/cache/local/`].

**Node-pure modules** (contract). These modules import nothing that touches WebGL or the DOM at module scope, so
`tools/traffic/` and `tools/live/` can run them in Node:
- `js/geo.js`, `js/math.js`, `js/geom.js`;
- `js/world/site.js`, `js/world/grid.js`, `js/world/earcut.js`;
- `js/env/wx/metar.js`, `js/env/ephemeris.js`, `js/env/clock.js`;
- `js/live/{traffic,classifier,parking,ground,feed,lookup}.js`;
- `js/aircraft/ga_dims.js`, and the geometry builder of `js/aircraft/placeholder.js`.

A drawable imports `js/gl.js` but creates its `Mesh` lazily.

**Names**

| Item | sfo3d | hwd3d |
|---|---|---|
| Debug hook | `window.SFO` | `window.HWD` |
| Readiness flag | `window.__sfoReady` | `window.__hwdReady` |
| Error flag | `window.__sfoError` | `window.__hwdError` |
| localStorage key prefix | `sfolive.` | `hwdlive.` |
| Mode override | `SFO_MODE` | `HWD_MODE` |

The storage prefix matters: both apps can be served from the same origin.

**Cross-package imports.** A package may import another package's exported functions and classes. It never edits that
package's files. The allowed dependency directions:

```
P4 app shell ──> P2 world/renderer/env ──> geo.js, math.js, geom.js (P2, pure)
     │                      ▲
     └──> P3 traffic/aircraft ──┘ (P3 imports P2's gl.js Mesh, math.js, geom.js, env/aircraft_lights.js; never scene.js)
P1 relay/pack/taxigraph: no JS imports; its outputs are data files + endpoints (+ the replay shim loaded by P4)
P2 never imports P3 or P4. scene.js (P2) never imports js/aircraft/**.
```

### 2.1 Relay: `hwd_live_server.py` (P1)

**CLI** (contract)

```
python3 hwd_live_server.py [--port 8000] [--host 127.0.0.1] [--radius NM] [--no-adsbfi] [--no-ident]
       [--replay SRC [--from ISO] [--until ISO] [--speed 1] [--loop] [--lookahead S]] [--record DIR] [--quiet]
```

- `SRC` is either `rec_pack`, which means `../sfo3d/refs/cache/rec_pack/adsblol_*.jsonl.xz` (read-only), or a
  `record.py` directory.
- Agents testing in the sandbox use a free port from 8700 to 8799.

**Polling.**
- Keep sfo3d's `Poller`: one request in flight, exponential back-off on 429, and the adaptive floor.
- There is one shared poll for all clients. Polling stops 60 s after the last client request (`IDLE_AFTER`).
- **adsb.lol:** `GET https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}` at the HWD ARP.
  - The radius must be ≥ 8 nm, so that a track exists before it enters the 5-nm display scope of D6 [inf].
  - The base period comes from adsb.lol's published terms. P1 reads them and records the quote; sfo3d's README quote
    is "Rate limits are dynamic based on the environment load" (sfo3d `docs/research/realtime_feeds.md`,
    "Verification (adversarial check)" table, row 4) [verify].
  - Measured budget from this sandbox's egress [obs `hwd_events.json` sampling]: 4,782 of 5,541 one-minute bursts end
    with HTTP 429 after 10 polls.
  - So the base period starts at ≥ 6 s, about 10 per minute. The adaptive floor keeps it from cycling through
    refusals.
  - P1 reports the period actually used in `/api/ping` `poll`.
- **adsb.fi:** live only, optional; off with `--no-adsbfi`. Its terms are personal and non-commercial.
  - It is never written by `--record`, never in a pack, never in a committed file.
  - Its attribution is shown while it is used.

**Merge** (copy of `Hub._merge` / `_merge_one`)
- The freshest position wins.
- Same-report fill.
- MLAT/TIS-B hold (10 s) and the jump test.
- On the ground, `track`, `track_rate` and the MLAT-listed fields are dropped (`_drop`).
- A sticky `_veh` flag for C1–C7 and SERV/GRND.
- Positions older than 60 s → `lastPosition`.
- `_src`, `_prov` and `_pt` are set on every record.

**Identity enrichment** (contract)
- When `refs/cache/local/registry/mictronics_lookup.json` exists (local, gitignored, ODC-By 1.0, 455,928 aircraft
  [obs]), the relay loads it in the background.
- It adds `_mx: {r, t, d, op}` to records it can resolve:
  - `r`, `t`, `d`: registration, ICAO type and description from the `aircraft` table;
  - `op`: the operator name from the `operators` table, for an ICAO-style callsign prefix such as EJA.
- The relay keeps the readsb fields as they are. P3 prefers the broadcast `r`/`t` and uses `_mx` to fill gaps.

**D1 masking** (contract; the last step before a record leaves the relay)
- **Rule.** A record is masked when `dbFlags & 4` (PIA) or `dbFlags & 8` (LADD).
  - Bit meanings per readsb `README-json.md` @ 843d8e3, as confirmed by sfo3d `docs/research/realtime_feeds.md`,
    "Verification (adversarial check)" table, row 22. P1 re-reads it and quotes it in `docs/phase2_relay.md` [verify].
  - Whether the Mictronics `flags` field also encodes LADD/PIA is unknown [verify]. Until verified, only `dbFlags`
    triggers masking.
- **What masking does:**
  - removes `flight`, `r`, `ownOp`, `year`, `squawk`, `dbFlags`, `_mx` and `_dbalt`;
  - keeps `t`, `desc`, `category`, `emergency` and the kinematic and quality fields;
  - replaces `hex` with `x` + the first 8 hex characters of HMAC-SHA256(salt, hex). The salt is random per relay
    process or pack build and is never written anywhere;
  - sets `_masked` to `'d1'` (flagged LADD / PIA) or `'type-only'` (everyone masked by the relay / pack mode); the
    client reads any truthy value as masked (amended in Phase 2 review fix round 1: it was `1`).
- **Late flag (amended, fix round 1):** a key flagged only after it was published unmasked is purged from `/api/ident`
  and the `?history` buffer, and the open SSE streams get `event: forget` with data `{"forget": [keys], "seq"}` (never
  in the full snapshot or history). `StreamFeed({..., onForget})` -> `traffic.forget(keys)`.
  (amended, fix round 2) Every forget event is kept for `FORGET_KEEP_S` (600 s): a stream gets ALL events after its own
  `seq` (not only the newest), and a polling client that sends `GET /api/adsb?since=<seq of its last answer>` gets
  `"forget": [keys]` in the answer for the keys it could have seen (first published at or before that `seq`). `feed.js`
  polls with `?since=` and calls `onForget` before the new list. `traffic.forget` sets `maskWhy: 'd1'`.
  (amended, fix round 3, m6; contract written down in review round 3 iteration 2) **Reconnects and horizons:**
  - every live `event: adsb` / `event: delta` carries `id: <seq>` (`?history` payloads carry none). The relay's seq base
    is the process start time in ms, so the seqs of two relay processes never overlap;
  - `GET /api/stream?since=<seq>` and the browser's `Last-Event-ID` header (its own SSE reconnect) both mean "the client
    has everything up to this seq": the stream first sends the forget events after it, for keys first published at or
    before it;
  - when that cannot be answered - the seq is older than the oldest kept forget event (`FORGET_KEEP_S` 600 s), below this
    process's seq base (another relay process), or above any seq published here - the relay sends
    `event: forget_horizon` `{since, seq, floor[, upto]}` on the stream (before the snapshot `upto` refers to) and
    `"forget_horizon": {...}` in `/api/adsb?since=` answers. `/api/ping` `features.forget` = `{keep_s, last_event_id,
    since, horizon}`; `/api/status` `merge.forget` holds counts only;
  - `StreamFeed({..., onForget, onHorizon})`: a horizon is applied once the map holds the snapshot it refers to; every
    key handed out since the last horizon that the snapshot does not contain (masked `x` keys excepted) is `absent`, and
    `onHorizon({present, absent, since, seq, floor})` is called - without `onHorizon` the feed falls back to
    `onForget(absent)`. **P4 must pass `onHorizon: (h) => traffic.forgetHorizon(h)`** (`js/live/app.js`, review round 3
    iteration 2, F7): `forgetHorizon` keeps every body and shows the absent tracks by type only (`ident.withheld =
    'horizon'`, not claimed LADD / PIA) until the relay re-publishes the key unmasked, and purges the persisted parked
    records. The fallback marked every silent and parked aircraft LADD / PIA and faded it out on each relay restart.
    Checked end to end by `jobs/horizon.mjs` (a foreign `?since=` through the page's real reconnect path).
- **Consequences:**
  - Tracks stay continuous within a relay session.
  - A masked parked aircraft is a new track after a relay restart [inf, accepted].
  - `/api/status` counts masked records; it never lists them.
- **No identity lookup endpoint.** Enrichment happens inline, for three reasons:
  - one place applies D1;
  - no per-address query API turns the local Mictronics copy into a public registry service;
  - snapshot and pack modes need the same fields without a relay.

**Endpoints** (contract)

| Endpoint | Shape |
|---|---|
| `GET /` | 302 → `live.html` (query kept) |
| `GET /api/ping` | `{"hwdlive": 1, "v": "0.1", "mode": "live"\|"replay", "stream": true, "delta": true, "dataNow": ms\|null, "center": {"lat": 37.6589317, "lon": -122.1217389, "radius_nm": N}, "poll": {"adsblol_s": s, "adsbfi": bool}, "features": {"metar": "KHWD", "taf": null, "ident": "mictronics 479e4d0"\|null, "d1": "dbFlags & 12", "replay": null \| {"src", "from": ms, "until": ms, "speed", "loop", "lookahead_s": 60}}, "providers": ["adsb.lol", …], "attribution": {"adsb": "…", "metar": "…", "ident": "…"}}`. P4 detects the relay by `j.hwdlive === 1`; an sfo3d relay (`sfolive`) is not accepted. |
| `GET /api/adsb[?since=seq]` | readsb jv2: `{"now": ms (relay wall clock), "dataNow": ms (data clock: recording time in replay), "seq": n, "total": n, "_source": "adsb.lol+adsb.fi", "msg": "No error", "ac": [record…]}`; with `since` (fix round 2) also `"forget": [keys]` when a D1 late flag hit keys that client was shown, and (fix round 3) `"forget_horizon": {since, seq, floor}` when the relay cannot answer that seq |
| `GET /api/stream[?delta=1][&history=S][&since=seq]` | SSE as sfo3d. `retry: 2000`, then `event: adsb` (full payload as `/api/adsb`). With delta: `event: delta` `{"now", "dataNow", "seq", "ac": [changed records], "gone": [keys]}`; a full event on every seq gap and at least every 30 s; `: keepalive` every 15 s. (amended, fix round 3) Live adsb / delta events carry `id: <seq>`; `since` / `Last-Event-ID` first replay the forget events after that seq, or send `event: forget_horizon` when they cannot (see the late-flag paragraph above). |
| `GET /api/metar?ids=KHWD[&format=json]` | Raw lines by default, newest first, for the last 3 h; `format=json` gives the aviationweather.gov objects (`icaoId`, `obsTime` epoch s, `reportTime`, `rawOb`, …). Header `X-Data-Now`. Replay: only reports observed at or before the replay time; HTTP 502 `{"error"}` when none is within 90 min (never today's weather in a replay). Only `KHWD` is accepted. |
| `GET /api/status` | provider health, latency and 429 counts, merge counters, ident loader state, masked count, replay position. No identities. |
| removed | `/api/gates`, `/api/routeset`, `/api/taf` (404). |

**Record fields the app reads** (contract; P3's `normalizeAircraft`)
- readsb: `hex type flight r t desc category lat lon lastPosition alt_baro alt_geom gs track true_heading mag_heading
  track_rate roll baro_rate geom_rate squawk emergency nav_altitude_mcp nav_qnh nic nac_p seen seen_pos mlat tisb
  dbFlags`;
- relay: `_pt _src _prov _veh _drop _masked _mx`.

**METAR facts** [obs: a probe of aviationweather.gov, 2 requests, 2026-11-13]
- `metar?ids=KHWD&format=json&hours=3` returned 2 reports. The newest:
  `METAR KHWD 130154Z 16005KT 10SM FEW060 19/12 A2974 RMK AO2 SLP080 T01890122` (an ASOS, AO2).
  - The routine minute appears to be **:54**, not KSFO's :56: one observation only; P1 confirms over 24 h [verify].
  - The upstream TTL schedule of sfo3d (`wx_ttl`: 60 s from hh:59 to hh:03) shifts to bracket hh:54.
- `taf?ids=KHWD&format=json` returned `[]`: **there is no KHWD TAF**. `features.taf` is `null`, and the app never
  asks.

**Static serving**
- Denied as in sfo3d: `refs/**`, `tools/**`, `node_modules`, `jobs/**` and dotfiles.
- `out/**` is denied **except `out/replay/`**, where the pack and its shim live.
- `refs/cache/local/**` (Mictronics, per-aircraft files) must never be served. A test asserts it.

**Replay** (`--replay`)
- The same Hub, re-timed to wall time; `dataNow` = recording time.
- `features.replay.lookahead_s` (default 60) tells the app to display that far behind, so every polling hole up to
  about 55 s is interpolated between two real fixes (§4.2 R3).

### 2.2 Replay pack and shim (P1 → P4)

**Build** (contract)

```
python3 tools/live/build_pack.py --from 2026-11-08T19:00Z --minutes 60 \
       [--radius-nm 6] [--max-alt-ft 4000] [--ident full|type-only] [--out out/replay/]
```

- **Input:** `sfo3d/refs/cache/rec_pack/adsblol_*.jsonl.xz` (adsb.lol only, ODbL 1.0), through `build_stream.py`
  (the relay's own Hub on a fake clock).
- **Spatial window:** every rec_pack record within `radius_nm` of the HWD ARP, at or below `max-alt-ft` MSL or on the
  ground.
  - rec_pack is trimmed to 25 nm of SFO, and HWD is 12.3 nm from SFO.
  - So any radius ≤ 12.7 nm around HWD lies wholly inside the trim [inf, geometry].
- **D1:** applied exactly as in §2.1.
- **Identity** (`--ident`):
  - `full`: Mictronics `_mx` for unmasked aircraft;
  - `type-only`: strips `flight`, `r`, `ownOp` and `_mx` from **every** record and keys every aircraft as `x…`.
  - **A pack meant for a published artifact uses `type-only` unless the owner decides otherwise** (§4.2 R11).

**Outputs** (all generated, gitignored, never committed): `out/replay/pack.json.gz`, `out/replay/pack_meta.json` and
`out/replay/replay_shim.js` (a copy of `tools/live/replay_shim.js`).

**Format `hwd-pack/1`**: sfo3d's `replay_pack.py` v2 (per-aircraft field deltas), plus the HWD fields.

```
{ "v": "hwd-pack/1", "made_by": "tools/live/build_pack.py", "made_at": ISO,
  "source": {"rec_pack": "sfo3d/refs/cache/rec_pack @ a967f9b", "hours": ["20261108_19", …]},
  "licence": "ODbL 1.0", "attribution": ["Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL 1.0 …",
                                         "Weather: NOAA/NWS Aviation Weather Center …", "(ident full) Mictronics … ODC-By 1.0"],
  "from": s, "until": s, "lookahead_s": 60,
  "filter": {"radius_nm": 6, "max_alt_ft": 4000, "ground": true},
  "d1": {"rule": "dbFlags & 4 (PIA) | dbFlags & 8 (LADD)", "masked_aircraft": n, "ident": "full"|"type-only"},
  "sampling": {"ok_polls": n, "http429": n, "gaps_over_30s": n, "max_gap_s": s},
  "events": [{"T": s (relay send time, recording clock),
              "p": {"now": ms, "dataNow": ms, "seq": n, "_source": "adsb.lol",
                    "d": [[key, {fields changed since this key's previous record}, [fields removed]?], …]}}],
  "metar": [{"obsTime": s, "rawOb": "METAR KHWD …"}] }
```

- Each event lists every aircraft present; an absent key is gone. This is sfo3d v2 semantics.
- Fields kept are those of §2.1 "Record fields the app reads".
- **Sizing** [obs: two busy hours of rec_pack, 6 nm / ≤ 4,000 ft or ground]:

  | Hour (UTC) | OK polls | HTTP 429 | Aircraft per poll (median / max) | Distinct aircraft | LADD/PIA-flagged | Raw JSON in the window |
  |---|---|---|---|---|---|---|
  | 2026-11-08 20 | 593 | 60 | 20 / 26 | 72 | 7 | 5.25 MB |
  | 2026-11-07 21 | 599 | 60 | 18 / 25 | 61 | 1 | 4.57 MB |

  Poll gaps: p50 1.3–1.4 s, p90 2.9–4.6 s, max 50.6–52.4 s. With deltas and gzip a 60-min pack should be about 1 MB
  [inf, by sfo3d's 109 MB → 4.5 MB ratio].
- **METAR for the window:** KHWD reports observed in the window from aviationweather.gov, if its look-back covers it,
  else from an archive. P1 checks the archive's terms and records the source [verify]. METARs are US Government data.

**Shim** (contract): `out/replay/replay_shim.js` is an ES module.

```js
export async function installReplay({ url = 'out/replay/pack.json.gz', loop = true } = {}) -> { from, until, lookahead_s }
```

- It patches `window.fetch` for `api/ping`, `api/adsb` and `api/metar`, and `window.EventSource` for `api/stream`.
- The fake ping is `{"hwdlive": 1, "mode": "replay", "stream": true, "delta": true, "features": {"metar": "KHWD",
  "taf": null, "replay": {from, until, lookahead_s, pack: true}}}`.
- **Timing**, as in sfo3d's shim:
  - every payload's `now` and each record's `_pt` move by `offset = page start − pack.from`;
  - `dataNow` keeps the recording clock.
- **Requirements:**
  - the first frame must not wait `lookahead_s`;
  - every hole of at most `lookahead_s − 5` s must be interpolated between real fixes;
  - at the window end the replay restarts or stops (`loop`).
- **P4 contract:** with `?mode=replay`, or when no relay answers and `out/replay/pack.json.gz` exists, `entry.js`
  `await import('../../out/replay/replay_shim.js')` and calls `installReplay()` **before** `detectRelay()`. The app then
  runs its live code path.

### 2.3 Taxigraph: `data/hwd_taxigraph.{json,js}` (P1 → P3, P2)

**Build:** `python3 tools/live/build_taxigraph.py` reads only `data/hwd_airport.json` and `js/geo.js` /
`hwd_frame.py` constants. It is deterministic.

**Output:**
- `data/hwd_taxigraph.json`;
- its twin `data/hwd_taxigraph.js` = `export const TAXIGRAPH = {…}`, with an ODbL header (OSM-derived).

**Format `hwd-taxigraph/1`** (contract): a superset of sfo3d's, so `TaxiNet` keeps working.

```
{ "v": "hwd-taxigraph/1", "frame": "ltp-nad83-2011-hwd", "made_by", "source": "data/hwd_airport.json sha256 …",
  "licence": "ODbL 1.0", "attribution": ["© OpenStreetMap contributors …", "Contains information from ADSB.lol …"],
  "halfWidth": m,                                     // default paved half-width for TaxiNet.paved [inf, AC 150/5300-13B T4-2]
  "ways":  [{"id": "osm:way/…"|"nasr:10R/28L", "ref": "A"|null, "kind": "taxiway"|"taxilane"|"runway"|"connector",
             "width_m": m, "width_src": "obs"|"inf", "max_span_m": m|null, "restriction": text|null, "src": "obs"|"inf"}],
  "edges": [[x0, z0, x1, z1, wayIndex], …],           // sfo3d-compatible segments (TaxiNet grid, match, paved)
  "nodes": [{"id": "n0", "x", "z", "kind": "junction"|"end"|"hold"|"runway"|"spot"|"helipad", "ways": [wayIndex…],
             "hold": holdId?, "runway": "10R/28L"?, "along_m": m?}],
  "links": [{"a": nodeIndex, "b": nodeIndex, "way": wayIndex, "len": m, "pts": [[x, z]…], "runway": "10R/28L"|null}],
  "holds": [{"id": "osm:node/…", "node": i, "runway": "10L/28R", "x", "z", "dir": [dx, dz], "cl_dist_m", "src"}],
  "spots": [{"id": "TW029N258", "node": i|null, "len": m, "pts": [[x, z]…], "why_none": text?}],   // parking → network
  "helipads": [{"id": "osm:way/…", "node": i|null}],
  "runways": [{"id": "10R/28L", "ends": ["10R", "28L"], "way": i, "nodes": [{"node": i, "along_m": m}]}],
  "aprons": [[[x, z]…], …],                           // open apron outer rings (sfo3d key)
  "closed": [{"id", "pts", "status": "abandoned"|"disused"}],   // not routable
  "checks": {"components": n, "largest_nodes": n, "unreachable_spots": [ids], "holds_unattached": [ids]} }
```

**Rules** (contract)
- **Nodes** are the Phase 1 junction vertices, plus way ends, holds (projected onto their way), runway entry points
  and spot/helipad connectors.
  - The data report counts 167 junction vertices, 166 of them shared, plus 1 shallow fork.
  - This map's probe found 165 vertices shared by two or more **open** ways, rounded to 0.01 m [obs]. P1 reconciles
    the count in `checks`.
- **Ways.** Only `status: open` ways are routable: 61 taxiways and 78 taxilanes.
- **Runways.** Their centrelines come from the NASR ends (`geo.js endWorld`), as in sfo3d.
  - A taxiway part inside the NASR rectangle with `on_runway.runway_overlap` (13 ways > 50 m [obs data report]) is
    split, and its runway part becomes `runway` links.
- **Wingspan limits:** `max_span_m` on A1 (100 ft) and Z1 (94 ft), from NASR.
- **Spot connectors** run straight over the apron from the spot to the nearest open line, clear of buildings. When
  none is clear, `node` is `null` and `why_none` says why.
- **Units:** coordinates in metres to 0.01 m; `len` is the polyline length.

### 2.4 Site model and world build (P2 → P3, P4)

**Site model** (pure, Node-importable; contract)

```js
// js/world/site.js
export function buildSite(airport /* HWD_AIRPORT */, { res = 0.5 } = {}) -> Site
Site = {
  rect: { x0, z0, w, h, res },                       // raster extent covering the aerodrome
  groundY(x, z) -> y,                                // NAVD 88 m: runway rwySurfaceY profile; elsewhere a smooth field
                                                     // surface from the NASR points [inf], or 3DEP when added
  paved(x, z) -> bool,                               // runways ∪ open taxi ribbons (width) ∪ aprons ∪ helipads (raster)
  surface(x, z) -> 'runway'|'taxiway'|'taxilane'|'apron'|'helipad'|'closed'|'grass',
  runwayAt(x, z) -> { id: '10R/28L', along, across, end } | null,   // inside the NASR rectangle
  apronAt(x, z) -> { id, name } | null,              // e.g. name '28L Run-up', '28R Runup', '10L Runup', 'Green Ramp'
  building(x, z) -> bool,                            // occupancy of hangars, tower, buildings (1 m)
  buildingAt(x, z) -> { id, kind, height_m, height_src } | null,
  hangars: [{ id, letter, kind, ring, height_m, height_src }],
  anchors: { tower: { x, z, y, eyeY, src }, aprons: { [name]: [x, z] }, windsock: [x, z] },
  // (amended, fix round 1) tower.x/z = centre of the tower's tall part (site.js TOWER_TALL, NAIP by eye, inf), not the
  // OSM ring centroid; surface()/paved()/apronAt() also cover HELI_APRON_NAIP (the NAIP-segmented helicopter pad complex,
  // id 'naip:heli_apron', 4 pads 'naip:heli_pad/1..4' as 'helipad'). airport.js naipTexture(level, {blobs}) in-paints
  // the catalogued NAIP 2024 aircraft (naipAircraft(airport)); lights.js buildMarkers also returns edgeLights (MIRL, inf).
  stats: { … }
}
```

- `paved` replaces sfo3d's rendered mask (`apt.paved`); `TaxiNet.paved` still unions with it (`pavedUnion`).
- Building heights are unsourced except the tower (OSM 15.85 m). Every other height is `height_src: 'inf'`, with its
  rule.

**World build** (contract)

```js
// js/live/world.js
export function buildHwdWorld(R, airport, { site, quality, taxigraph = null, log = () => {} }) -> World
World = { items: RenderItem[],                // static items (§2.5)
          site,                               // the Site above (same object)
          towerPos: [x, y, z], towerEye: [x, y, z],
          textures, groundU, waterU|null,     // renderer internals (bakes)
          staticSprites(t) -> Sprite[],       // sourced static lights only
          stats: { … } }
export function releaseAirportMap(world)      // after the first bake (as sfo3d)
```

What Phase 2 draws, each element with its `src`:
- **Ground:** the field surface.
- **Pavement:** runways (NASR outline), taxiway and taxilane ribbons, aprons and helipads.
- **Markings:** where the data or the AC give them:
  - runway PIR on 10R/28L and NPI on 10L/28R;
  - displaced-threshold bars and arrows (826 / 676 ft);
  - the yellow centrelines;
  - the 16 NAIP-measured hold bars;
  - the Green Ramp tie-down tees.
- **Buildings:** 34 hangars, the tower, 17 buildings.
- **Markers:** the windsock and the segmented circle.

**Marking dimensions.** The committed AC extract covers AC 150/5340-1M paras 2.8, 2.9.1 and 3.3.4.1 only. Every other
dimension (threshold stripes, designators, aiming point, TDZ) must be read from AC 150/5340-1M itself [verify].

**Not drawn in Phase 2:** signs, light fixtures and the fuel island (`not_yet_sourced` / `not_placed`). There is no
look-alike for anything unsourced.

### 2.5 Renderer, scene, items, sprites, camera (P2 → P3, P4)

**Renderer** [obs sfo3d API, kept as contract]

```js
new Renderer(w, h, { msaa, shadowRes })
R.addProgram(name, vs, fs, defines)
R.setupSky(env)
R.render(frame, cam, t, post) -> C
R.present(cw, ch)
R.resize(w, h)
R.light = { skyUp, skyHorizon, ground }
R.extraCommon
R.envState
R.curCam
R.H
R.onFatal = fn(html)
```

**Programs.** `buildHwdWorld` registers at least `ground`, `decal`, `obj`, `objI` and `mark` (plus `sign` if it is
used). `Scene` registers `sprite` and `smoke`.

**Camera and frame**
- `cam = {pos, target | dir, up?, fov (vertical, rad), near, split, far, shadowSplits?: [m, m, m]}`.
- The returned `C = {pos, dir, up, view, vpNear, vpFar, fov, aspect, near, split, far}`; P4 projects labels with
  `C.vpNear`.
- `post = {exposure, shutter, bloom, vignette, grain, sat}`.

**Render item** (contract; sfo3d `CLAUDE.md` + `renderer.js drawItems` [obs])

| Field | Meaning |
|---|---|
| `mesh` | a `gl.js` `Mesh` built from `{pos, nrm, uv, col, extra, idx, bbox}` (`Geo.data()`) |
| `prog` | program name |
| `model` / `prevModel` | `Float32Array(16)` column-major world matrices; `prevModel` for motion vectors |
| `uniforms` | object or `() => object` |
| `bbox` | world `[x0, y0, z0, x1, y1, z1]`, or `null` (never culled) |
| `castShadow` | boolean |
| `shadowMaxCascade` | cascades 0 … n−1 only |
| `noCull` | disables back-face culling |
| `blend` | `'alpha'` or `'add'` |
| `bothPasses` | drawn in both the near and the far pass |
| `sortKey` | `(camPos) => number` |
| `polyOffset` | `[factor, units]` |
| `nearOnly` / `farOnly` | restrict the item to one range |
| `alpha` | (amended, fix round 1) 0..1 for the `obj` program: screen-door (4x4 Bayer) dithered fade, `uAlpha`; `1` or absent = opaque. `AircraftViews` sets it from `tr.disp.alpha`, so a re-placement cross-fades |

Vertex `extra` is `(roughness, metal, matID, emissive)` (`geom.js`).

**Sprite** (contract): `{p: [x, y, z], c: [r, g, b], i: intensity, s: size (m), dir?: [x, y, z], k?: beam exponent,
lens?: bool, phys?: bool, marker?: bool}`.

**Scene** (contract)

```js
new Scene(R, world)
scene.add(drawable)
scene.remove(drawable)
scene.staticLights.push(sprite | (t) => Sprite[])
scene.frame(t, camPos) -> { items }
scene.commit()
```

- A **drawable** is any object with `items(camPos) -> RenderItem[]`, `lightSprites(t) -> Sprite[]`, `commit()` and
  `visible`.
- `scene.frame` sorts by program (occluders first), appends the sprite batch, and calls `commit()` on every drawable
  after rendering.

**Scale.**
- sfo3d's orbit camera uses near = 0.008 × distance (0.25–40 m), split = 3.5 × distance (350–6,000 m) and far
  180 km; the tower camera uses near 1 m, split 2,500 m, far 160 km. The renderer's default shadow splits are
  [120, 700, 3500] [obs `controls.js`, `renderer.js`].
- At HWD aircraft are 8–15 m long and the field is about 2 km. P2 retunes the cascades; P4 sets near/split/far in
  `controls.js`. A starting point: near 0.5, split 1,500, far 40,000; shadow splits [60, 400, 2500] [inf].

### 2.6 Environment (P2 → P4)

The environment glue moves out of `app.js` into P2's own module, so P4 does not re-implement sfo3d's SFO-tuned fog,
cloud and exposure logic (app.js `applyEnv` and `setClouds`, lines 181–258).

```js
// js/env/app_env.js (adapted)
const env = new AppEnv({ mode, relayInfo, snapshotNow: null, snapshotMetar: '', search: location.search, station: 'KHWD' })
env.setDataNow(ms, recvNow)
env.setReports(list /* /api/metar JSON */)
env.update(now, runwayFlow | null) -> EnvState
env.summary() -> { raw, windDir, windKt, visSM, visPrefix, clouds: [{cover, ft}], altim } | null
env.clockNote()
env.setLightMode('real' | …)
env.attachHud(root)
env.state

// js/env/render_env.js (new)
export function applyEnvToRenderer(R, world, E, { quality, force = false }) -> { exposure, nightF, changed }
//   sky + fog + clouds + light floors + ground bake when the sun has moved (> 2° el / 4° az) — the work of sfo3d applyEnv
```

- P4 calls `env.update` and `applyEnvToRenderer` at start and every 30 s, and polls `/api/metar` every 60 s.
- Station constants:
  - field elevation 52.1 ft (NASR);
  - KHWD routine minute 54 [verify, §2.1];
  - TZ `America/Los_Angeles`.
- There is no TAF.

### 2.7 Traffic engine (P3 → P4)

```js
// js/live/traffic.js
export const DELAY_MS, DELAY_MIN, DELAY_MAX
export class Traffic {
  constructor({ airport /* HWD_AIRPORT */, taxigraph /* TAXIGRAPH | null */, site /* Site */, parking /* ParkingModel */,
                persist = true, delay = DELAY_MS })
  ingest(payload /* parsePayload(json) */, recvNow = Date.now())
  update(now, dt)
  displayTime(now) -> ms
  tracks: Map<key, Track>
  events: TrafficEvent[]  // data time, capped
  onEvent: (e) => void
  delay, delayTarget, adaptDelay
  net: TaxiNet            // .match(x, z, hdgRad, prevWay), .paved(x, z), .route(fromNode, toNode) -> { nodes, len, pts }
                          // (amended, round 3 iteration 3: new TaxiNet(taxigraph, site) - each link carries its building
                          // clearance .clr (m); routes with opt.span penalise links narrower than span / 2 + 1 m)
  counters: { … }
  remove(tr)
  clearParked()
  forget(keys /* string[] */)   // (amended, fix round 1) drop these tracks and their identity at once (relay 'forget' event)
  // (amended, round 3 iteration 3) Track.phaseInfo.label may differ from PHASES[phase].label: 'Stopped' / 'Stopped on the
  // runway' for a taxi / runway_taxi body at rest > 10 s (inferred, provisional); the phase key is unchanged
}
// js/live/motion.js (new, fix round 1; Node-pure) - the motion primitives traffic.js plans with
export function polyOf(pts) -> { pts, s /* cumulative */, len }
export function polyAt(poly, s) -> { x, z, ux, uz }
export function filletPath(pts, r, ok /* (x, z, tx, tz) -> bool */) -> pts      // corners rounded where ok() allows
export function profilePath(R, D, v0, v1, opt) -> P   // drivable speed profile over a path in D s: {tmin, feasible, dwell, ...}
export function profAt(P, t) -> { s, v }
export function geoHermite(p0, d0, s0, p1, d1, s1, D) -> { at(t) -> { x, z, vx, vz, s, v }, len }   // air-hole curve
// (fix round 2) turn-limited air paths where the Hermite shape turns tighter than ~30 deg of bank at the flown speed:
export function hermiteMaxCurv(G, D) -> 1/m
export function dubinsCSC(p0, d0, p1, d1, r) -> { pts, len } | null
export function turnFlight(p0, d0, s0, p1, d1, s1, D, r, { final, initial }) -> { at(t), len, k /* flown / reported speed */ }
export function phaseLabel(tr, now) -> string
export function category(tr) -> 'hwd_air' | 'hwd_ground' | 'heli' | 'overflight' | 'vehicle' | 'unknown'
```

**Track, read-only for P4** (contract)

```
tr.key                         internal handle (§2.0); never displayed
tr.ident = { masked, maskWhy /* 'd1' | 'type-only' | 'unknown' (fix round 1) */, label, reg, regSrc, callsign, operator,
             icaoType, typeName, category, src }
           // regSrc 'adsb_db' = the aggregator's database (r / t / desc are not broadcast); a registration derived from
           // the ICAO address (nNumberFromHex) is shown only with a known type and marked [inf] (fix round 1)
           // label: masked → type designator (e.g. "C172"), or "Aircraft" when the type is unknown;
           //        else callsign, else registration, else type
           // reg / callsign / operator: null when masked
tr.dims                        GA dimension record (§2.9)
tr.disp = { x, y, z, hdg /* deg true */, pitch, roll /* rad */, gs, vs /* m/s */, ground, valid,
            alpha /* 0..1 fade */, gear, flaps, extrap /* s past the newest fix */ }
tr.phase                       display phase id (§3)
tr.phaseInfo = { label, rwy, leg, src, rule, since /* data ms */, provisional /* may still change */, tower /* 'open'|'closed' */ }
tr.scope                       'hwd' | 'overflight' | 'pending' (D6)
tr.inView                      inside the D6 display window (≈ 5 nm, ≤ 3,000 ft AGL, with hysteresis)
tr.park = { spotId, kind, zone, src, inside /* hangared */, pose: { x, z, hdg } } | null
tr.stale, tr.removed, tr.noData, tr.lastFixT, tr.lastRecv, tr.vehicle
           // (amended, fix round 2) tr.stale: a ground aircraft whose signal ended is KEPT where it was last placed - parked
           // (tr.park, phase 'parked' / 'hangared') on an apron / helipad / hangar-door taxilane, else phase 'no_signal'
           // (src inf) on a taxiway, run-up pad or runway - and fades out only after LOST_KEEP_MS (30 min) / PARK_KEEP_MS
           // (8 h) without a report. Heard again, it moves on from that pose (a continuation anchor), never re-placed
```

**Delays**
- Live: the delay adapts to the report ages (sfo3d `adapt`). `DELAY_MAX` is raised to cover the relay's poll period
  (`ping.poll.adsblol_s`) [inf].
- Replay or pack: `delay = lookahead_s × 1000` with `adaptDelay = false` (§2.1, §2.2).

**Physics**
- `new GroundPhysics({ site, net: traffic.net })`, then `physics.resolve(traffic, dt)` and `physics.stats`.
- Planform samples come from `tr.dims` (§2.9). There are no bridges.
- The ICAO Annex 14 stand clearances are replaced by the spot's own `size.capacity_span_m` gap (1.0 m) for parked
  aircraft, and by 3 m for others [inf; data report §2].

**`normalizeAircraft`** (`feed.js`) adds:
- `masked` (from `_masked`, any truthy value) and `maskWhy` (`'d1'` / `'type-only'`, fix round 1);
- `mx: {r, t, d, op} | null`;
- `nacp` (from `nac_p`);
- `nic`;
- `srcType` (already there).

`parsePayload`, `StreamFeed` (`api/stream?delta=1`, poll fallback `api/adsb`) and `fetchMetar('KHWD',
'/api/metar?ids=KHWD&format=json')` keep their sfo3d signatures.

**Heights.** h (ft AGL) = `alt_geom` − `GEOM_OFF` − the NASR runway surface (ft).
- `GEOM_OFF` = −108.09 ft, calibrated in `hwd_events.json` `calibration` (n = 797; IQR −112.0 to −94.2) [obs].
- The barometric fallback uses a running-median offset (`baro_global` −148.6 ft).
- This replaces sfo3d's `GEOID_M = 32.29`, an SFO value.
- 100-ft altitude quantum transponders use `H_CONTACT_COARSE` (80 ft).

### 2.8 Classifier, parking and events (P3; read by P4)

```js
// js/live/classifier.js (pure)
export const PHASES          // ids of §3, with { label, group, airborne }
export const RULES           // the hwd_events.json rules constants + run-up constants, each with its source key
export class PhaseClassifier {
  constructor({ airport, taxigraph, site })
  step(track, fix, now) -> { phase, src, rule, rwy, leg, provisional, events: [TrafficEvent] }
}

// js/live/parking.js (pure)
export class ParkingModel {
  constructor({ airport /* parking, hangars, helipads, unspotted_aircraft */, taxigraph, site })
  match(pose, dims) -> { spot, d, ok } | null       // tie-down / ramp / hangar_apron / helipad
  occupy(key, spot)
  release(key)
  occupancy() -> Map<spotId, key>
  spots                                             // the 177 spots with their src, size and zone labels
}
```

**Spots.** Labels are the descriptive Phase 1 zones ("Green Ramp row 1, tie-down 1"), never official numbers (D3).
A parked aircraft takes the spot's pose when the spot has a heading (80 tie-downs, 9 rule hangar aprons, 1 door spot
[obs data report]); otherwise its median report pose, made valid by physics.

**TrafficEvent** (contract; no identity fields)

```
{ t /* data ms */, kind, key, rwy: '28L'|null, spot: id|null, src: 'obs'|'inf', rule, cls /* type class */, dur_s? }
kind ∈ takeoff | landing | touch_and_go | stop_and_go | go_around | low_pass | runway_taxi
     | lift_off | touch_down | hover_taxi | runup | hold_short | line_up | park | unpark
     | hangar_in | hangar_out | scope_hwd | overflight
```

`stats.js` (P4) aggregates the events:
- movements per runway end per hour;
- touch-and-goes and circuits (the median circuit interval in the data is 239.5 s [obs `hwd_events.json`]);
- helicopter operations;
- after-hours operations (tower closed outside 07:00–21:00 local [obs NASR]).

### 2.9 GA placeholders and views (P3 → P4; renders through P2)

**Dimension record**

```js
// js/aircraft/ga_dims.js (generated by tools/traffic/build_ga_dims.py from data/ga_types.json)
export function gaDims(icaoType, category /* DO-260B emitter category */) -> Dims
Dims = {
  type: 'C172'|null, name, cls: 'single_hw'|'single_lw'|'twin'|'turboprop'|'jet'|'heli'|'glider'|'ultralight'|'unknown',
  L, span, H /* tail height */, rotor: m|null, mtow_kg,
  R /* fuselage half-width */, Hc /* fuselage centre height above ground */,
  xNose, xMain, track, gearKind: 'tricycle'|'tail'|'skid',
  wing: { span, rootLE, rootC, tipC, sweep, pos: 'high'|'low' },
  hstab: { x, span, rootC },
  ant /* GNSS antenna, m behind the nose */,
  src: 'obs'|'inf', basis /* e.g. "FAA ACD row 137" or "class default (A1) [inf]" */
}
```

- The field names are those `ground.js samples()` and the labels read in sfo3d (`L R Hc xNose xMain track wing hstab
  name`).
- `L`, `span`, `H` and `mtow` are `obs` from the FAA ACD for 67 of the 90 types [obs `ga_types.json`].
- The other 23, including **every helicopter** (B06, EC45, R44, A109, EC30, B407, R22, H60), have no ACD row.
  - They use class defaults marked `inf`, or values from a cited manufacturer source [verify].
- Unknown types fall back by emitter category, always `inf`:
  - A1 → C172-sized high-wing single;
  - A2 → twin or turboprop;
  - A3 → bizjet;
  - A7 → light helicopter.
- The category meanings follow DO-260B, from memory [verify].
- **`ant` is inferred:** sfo3d's 0.2 L is an airliner value. For a GA single, Phase 1 assumed the antenna 1–3 m from
  the planform centre [inf].

**Drawable**

```js
// js/aircraft/placeholder.js
export function placeholderGeo(dims, { colour }) -> { pos, nrm, col, extra, idx, bbox }   // pure, local frame
export class GaAircraft {          // a drawable (§2.5)
  constructor(dims, { id, colour, lodDist, shadowDist })
  pos       // [x, y, z] main-gear contact midpoint (world)
  fwd       // [x, 0, z] unit
  pitch, roll, gear, visible, selected, lightsOn: { nav, beacon, strobe, landing, taxi }
  T         // = dims
  ready     // Promise
  items(camPos)
  lightSprites(t)
  commit()
  dispose()
}
```

- **Local frame**, as sfo3d `Aircraft`: +x forward, +y up, +z right (starboard). The origin is the main-gear ground
  contact. Rendering uses `prog: 'obj'` with `model`/`prevModel`, a world `bbox` and `castShadow: true`.
- **The placeholder is plainly a placeholder:**
  - it is sized from the record;
  - its shape follows the class (wing position, tail, fixed gear for singles, a rotor disc and skids for helicopters);
  - it uses neutral colours;
  - it has no registration decal and no livery.

**Views**

```js
// js/live/aircraft.js
export class AircraftViews {
  constructor(scene, { quality })
  sync(traffic, now, { nightF, selectedKey })   // creates, updates, removes drawables; antenna -> main gear from dims.ant;
                                                // y = site.groundY on the ground
  get(key) -> GaAircraft | null
  modelNote(tr) -> string                       // e.g. "Placeholder sized to C172 (FAA ACD); shape generic"
  dispose()
}
```

Light states come from `js/env/aircraft_lights.js` `aircraftLightStates({phase, ground, gs, altAgl, stale})`. P3 maps
the GA phases to its inputs.

### 2.10 App shell, QA hooks and harness (P4)

**`startApp(cfg)`**

```js
cfg = { mode: 'live' | 'replay', relayInfo /* ping JSON | null */, airport: HWD_AIRPORT, taxigraph: TAXIGRAPH | null,
        about: html, attrib: html }
```

- The entry imports `data/hwd_airport.js` and loads `data/hwd_taxigraph.js` dynamically (optional, as in sfo3d).
- It sets `window.__hwdReady` or `__hwdError`.

**Boot order inside `startApp`** (the integration sequence)

```
UI → initGL → Renderer → site = buildSite(airport) → world = buildHwdWorld(R, airport, {site, quality, taxigraph})
→ scene = new Scene(R, world); scene.staticLights.push(world.staticSprites)
→ env = new AppEnv({...}); applyEnvToRenderer(R, world, env.update(now), {force: true})
→ parking = new ParkingModel({airport, taxigraph, site})
→ traffic = new Traffic({airport, taxigraph, site, parking, persist: mode === 'live'})
→ physics = new GroundPhysics({site, net: traffic.net})
→ views = new AircraftViews(scene, {quality})
→ rig = new CameraRig(canvas, {heightAt: site.groundY, onTap})
→ feed = new StreamFeed({onData: p => traffic.ingest(p, Date.now()), onStatus}); feed.start(); metar poll 60 s
loop: traffic.update → physics.resolve → views.sync → rig.update → (30 s) env → scene.frame → R.render → scene.commit
      → R.present → labels (tr.ident.label, tr.disp, tr.dims.H) → list/status
```

**Debug hook**

```
window.HWD = { R, scene, world, site, traffic, physics, parking, views, rig, ui, env, qa }
qa = {
  hideUI(on),
  look(target, yawDeg, pitchDeg, dist, fovDeg),
  view(name),       // 'overview', 'tower', 'green', 'fbo_ne', 'fbo_s', 'west', 'runup28l', 'runup28r', 'heli', 'final28l', …
  spot(id, dist),
  hold(id, dist),
  thr(end, dist),
  aircraft(key, dist),
  tracks(),         // [{key, label, phase, scope, park, ground}] — labels only, D1-safe
  counts()          // phases, scope, spots occupied, physics stats
}
```

Views are built from `site.anchors` and `geo.js` thresholds.

**Harness.** `livetest.mjs` keeps sfo3d's interface (`node livetest.mjs <job.mjs>`; the job exports
`default async ({page, shot, base, W, H, OUT})`).
- The mock relay serves `/api/ping` `{hwdlive: 1, mock: true}`, `/api/adsb` from the pack's events (built first with
  `build_pack.py`), and `/api/metar` with a KHWD report.
- `RELAY=http://127.0.0.1:87xx` proxies to a running `hwd_live_server.py`.
- Environment variables, as sfo3d: `PORT` (free, 8700–8799), `W`/`H`/`DPR`, `MOBILE=1` (phone viewport and UA),
  `SWS=1` (SwiftShader, the default here), `VIEWS="view:green;spot:TW029N258;look:x,y,z,yaw,pitch,dist"`, `PREFIX`.
- Keep resolutions modest. Every render a builder describes must first be looked at.

---

## 3. GA phase set (P3 classifier output)

**Evidence keys** in the table:
- `E.rules.X`: a constant of `refs/cache/adsb/hwd_events.json` `rules`;
- `E.counts.k`: an event total over the 111 rec_pack hours [obs];
- `U.*`: `refs/cache/adsb/hwd_runup_holds.json`;
- `A.*`: `data/hwd_airport.json`.

**Units**, inferred from `rules_text`: heights in ft above the runway surface; times in s; speeds in kt; distances in
m.

**Fix states** (as `hwd_events.json` defines them)
- **R:** runway contact. On a runway strip, (ground flag or h ≤ `H_CONTACT` 30 ft), and aligned within `ALIGN_DEG`
  30°.
- **L:** low on a runway corridor. |across| ≤ `CORR_M` 75 m, along ∈ [−2,000 m, L + 1,000 m], h ≤ `H_LOW` 400 ft.
- **G:** the ground flag and not R.
- **A:** airborne otherwise.

**"Ground"** also includes ground by kinematics: h ≤ `GK_H` 30 ft and gs < `GK_GS` 35 kt. The reason is in the rules
text: "Many GA ADS-B units have no weight-on-wheels input and report 'airborne' while rolling."

### 3.1 Phase table

| Phase id | Meaning | Rule (live, causal) | Evidence and source | src |
|---|---|---|---|---|
| `parked` | stationary at a parking place | still (< `U.rules.STILL_GS` 1 kt) ≥ 60 s [inf] off runway strips and away from holds and run-up aprons; matched to an `A.parking` spot when within its size | 177 spots (113 obs / 64 inf); `hwd_parked_stays.json` 522 sessions; 143 aircraft logged ≥ 20 stationary ground fixes over > 10 min (PLAN §3) | obs (fixes) / the spot's own src |
| `hangared` | inside a hangar (signal lost at a hangar, or first heard there) | last or first fix within 8 m of a hangar outline or at a door spot, then no signal | `A.hangars[].adsb_signal_edges_8m`; door spot HE623S150; hangar-apron spots | **always inf** |
| `taxi` | moving on taxiways, taxilanes or aprons (`taxi_out` / `taxi_in` by context) | ground (flag or kinematics), gs ≥ 1 kt, off runway strips; map-matched to the taxigraph | `E.rules.GK_H`/`GK_GS`; taxi-gap figures (median 1.3 s, p99 52 s: the recorder holes) | obs |
| `runup` | engine run-up before departure | still 30–600 s (`U.rules.MIN_S`/`MAX_S`) inside an apron named `28L Run-up`, `28R Runup` or `10L Runup` | `U.summary.by_kind.runup_apron` 144 (28R Runup 97, 28L Run-up 47) | place obs / purpose inf |
| `hold_short` | holding short of a runway | still within `U.rules.HOLD_R` 25 m of an `A.holds` bar, on the taxiway side | `U.by_kind.hold_short` 195 (first stop before departure: 158) | place obs / clearance inf |
| `line_up` | lined up on the runway (line up and wait) | R, aligned, gs < 5 kt, no take-off roll yet | `U.by_kind.line_up` 22 | obs |
| `runway_taxi` | back-taxi, crossing or slow exit on a runway | R at taxi speed with ground context on both sides | `E.counts.runway_ground_move` 22 | obs |
| `takeoff_roll` | take-off roll | R accelerating; ground → R → air; `E.rules.LIFT_GS` 40 kt | `E.counts.takeoff` 318. Hidden transition (G → L/A within `HID_GAP` 100 s, `HID_NEAR` 150 m) gives inf | obs / inf |
| `initial_climb` | climb-out after lift-off, straight ahead | airborne after R/takeoff, aligned, until a turn or until within 300 ft of the TPA | AIM 4-3-3 traffic pattern [verify]; NASR TPA 652 ft MSL (10R/28L) / 852 ft MSL (10L/28R) | inf (thresholds) |
| `upwind` | parallel to the runway in the landing direction, offset (side-step, after a go-around) | aligned ±30°, offset beyond the strip, near pattern height | AIM 4-3-3 [verify] | inf |
| `crosswind` | perpendicular to the runway past the departure end, toward the pattern side | track ⊥ runway ±30°, beyond the departure end, on the NASR pattern side | NASR: 10R right, 10L left, 28L left, 28R right [obs] | inf |
| `downwind` | parallel, opposite to the landing direction, on the pattern side | track anti-parallel ±30°, offset 0.4–1.5 nm on the pattern side [inf], within ±300 ft of the TPA [inf] | NASR TPA; circuit interval median 239.5 s (`E.quality.circuit_interval_s`) | inf |
| `base` | perpendicular toward the extended centreline beyond the approach end | track ⊥ ±30°, beyond the threshold, descending | AIM [verify] | inf |
| `final` | on the extended centreline, descending to the runway | L state (`CORR_M` 75 m; along −2,000 m to the threshold); beyond 2 km a widening corridor [inf] | `E.rules.CORR_*`, `H_LOW`, `ALIGN_DEG` | obs (L) / inf (beyond 2 km) |
| `landing_roll` | after touchdown, decelerating to the exit | air → R; until off the strip or gs < `EXIT_GS` 30 kt | `E.counts.full_stop_landing` 341 (obs 279, inf 62); `landing_unresolved` 10 | obs; **provisional** until it is no T&G |
| `touch_and_go` | touchdown and take-off without stopping | air → R → air; obs with contact evidence (ground flag, kinematics, ≥ 2 R fixes, or min gs < `DECEL_RATIO` 0.85 × approach gs) | `E.counts.touch_and_go` 390. From a low pass with a slow hole (< `SLOW_RATIO` 0.9): inf | obs / inf |
| `stop_and_go` | full stop on the runway, then take-off | as `touch_and_go`, with min gs < `STOP_GS` 15 kt (obs), or a hole mean < `STOP_HOLE_GS` 25 kt (inf) | `E.counts.stop_and_go` 7 | obs / inf |
| `go_around` | low approach or go-around (no touchdown) | low pass (L run ≥ `PASS_MIN_N` 3 fixes, min h ≤ `H_PASS` 300 ft at ≥ `PASS_GS` 35 kt) seen descending and climbing within one burst | `E.counts.low_approach_go_around` 2 | obs |
| `low_pass` | low pass, unresolved (touch-and-go or low approach) | a low pass whose lowest point fell in a polling hole | `E.counts.low_pass_unresolved` 142 | **inf**; labelled "Low pass (touch-and-go or low approach)" |
| `departing` | leaving the pattern or the area | climbing away beyond the pattern, or above TPA + 500 ft, not in a leg [inf] | — | inf |
| `arriving` | inbound to HWD, not yet in a leg (e.g. a 45° entry) | descending toward the pattern within the scope, with HWD evidence pending | — | inf |
| `heli_ground` | helicopter on the ground (helipad or ramp) | ground flag; spot kind helipad when matched | 16 helipad spots (13 obs); `E.counts.touch_down` 79 / `lift_off` 81 (events) | obs |
| `heli_hover_taxi` | helicopter hover-taxi | H state (airborne, h ≤ `HELI_H` 150 ft, gs ≤ `HELI_GS` 40 kt, within `HELI_R` 2 km) moving ≥ `HOVER_MIN_M` 30 m | `E.counts.hover_taxi` 64 (taxiway 30, off OSM pavement 17, apron 10, runway 5) | obs |
| `heli_hover` | stationary hover | H state moving < 30 m | — (new) | inf |
| `heli_air` | helicopter airborne near HWD, arriving or departing | A state after `lift_off` / before `touch_down` | `E.rules.HELI_*` | obs |
| `overflight` | not HWD traffic (D6): OAK/SFO arrivals and departures, transits, helicopter low transits without ground contact | in the scope, but no R/G fix on HWD pavement, no L corridor and no pattern-leg sequence; airliner categories (A3+) on OAK flows | PLAN §3: OAK arrivals within 3 nm below 3,000 ft; `E.counts.low_transit` 9 (helicopters) | inf (until evidence) |
| `vehicle` | ground vehicle | emitter category C1–C7, type SERV/GRND, or a sticky `_veh` | sfo3d hygiene | obs |
| `no_signal` | No signal · last position | (amended, fix round 2) a ground aircraft whose signal ended away from a parking place, drawn where it was last placed until heard again or 30 min pass | traffic.js `groundLost` | inf |
| `unknown` | not enough evidence | new track, no altitude, TIS-B with NACp 0 (8 % of on-field fixes, PLAN §3), or scope pending | — | — |

### 3.2 Notes for P3

- **Runway end** comes from the direction of motion: the circular mean track against the axes 119.9° / 299.9° true
  [obs `hwd_events.json`].
- **Parallel runways.** The 10L end lies 152.6 m left of the 10R axis [obs, `geo.js` probe]. The two strips and the
  two L corridors (±75 m) do not overlap.
- **Tower hours** are 07:00–21:00 local (NASR) [obs]. While the tower is closed, 10L/28R is closed (NASR remark). The
  classifier lowers its prior for 10L/28R then and tags every event `tower: 'closed'`. In the recording, 15 landings
  were after hours, all on 28L.
- **Causal versus offline.** The `hwd_events.json` rules are retrospective: their context window is `CTX_GAP` 150 s on
  both sides.
  - Live, the classifier decides with only the display delay of lookahead. In pack mode that is 60 s, which is less
    than `CTX_GAP`.
  - So `landing_roll` and `low_pass` are shown **provisionally**: `phaseInfo.provisional = true`.
  - The label history is revised when the outcome is known, back-dated as sfo3d `setPhase(tStart)` does.
- **Acceptance test** (`tools/traffic/`): run the engine in Node over all rec_pack hours and compare its event counts
  per kind with `hwd_events.json` `counts`:

  | Kind | Count in `hwd_events.json` |
  |---|---|
  | touch_and_go | 390 |
  | full_stop_landing | 341 |
  | takeoff | 318 |
  | low_pass_unresolved | 142 |
  | lift_off | 81 |
  | touch_down | 79 |
  | hover_taxi | 64 |
  | runway_ground_move | 22 |
  | landing_unresolved | 10 |
  | low_transit | 9 |
  | stop_and_go | 7 |
  | low_approach_go_around | 2 |

  Also check the sequence sanity `quality.consecutive_pairs_within_1h`: TT 3 and LL 3 should stay near 0. P3 sets
  and reports the tolerances.
- **Pattern-leg rules are new.** They are not in `hwd_events.json`, so their thresholds are inferred and must be
  calibrated on the recording. Only one west-flow week exists: 92 % of low fixes were westbound (PLAN §3). East-flow
  legs are untested.

---

## 4. Risks of the fork

### 4.1 SFO-only systems that are dropped, and what replaces them

| SFO system (sfo3d files) | Why it does not apply | HWD replacement (owner) |
|---|---|---|
| Jet bridges, VDGS, GSE (`js/live/gates.js` 2,091 lines, `js/world/gates.js`, `js/aircraft/dock.js`, bridge hooks in `app.js`/`traffic.js`/`ground.js`) | HWD has no contact gates | none; parked aircraft rest on tie-downs or ramp spots (P3 parking) |
| Surveyed stands and stand matching (`data/sfo_stands.js`, `standGates`, `matchGate`, lead-ins, `ANT_REF`) | no stands | `A.parking` 177 spots with src, size and heading (P3 `parking.js`); hangars / hangared state |
| SFO's gate plan from flysfo (`/api/gates`, `Gates`, `planFor`, `planType`) | SFO-only, unlicensed | none |
| Routes (`/api/routeset`, VRS mirror) | GA flights have no published routes | none in Phase 2 |
| FAA registry `_faa` (transport types only; `faa_icao`) | blocked registry download; transport types only | Mictronics `_mx` enrichment in the relay (P1) |
| Airline, brand and livery lookup (`lookup.js`, `data/lookup.js`, `brands.js`, `liveries/`) | airline fleets | GA identity record + D1 (P3 `lookup.js`); liveries and N-numbers in Phase 3 |
| Airliner models and procedural airframes (`js/aircraft/*`, `.sfom`, `shaders/aircraft*.js`) | airliners | GA placeholders sized from `ga_types.json` (P3); real models in Phase 3 |
| EMAS, blast pads, `END_ZONES`, 4-runway shader layout | not at HWD | PIR/NPI markings and displaced thresholds of 10R/28L (P2) |
| Terminals, ITB, piers, landside (`terminals.js`, `sfo_buildings`, `sfo_landside`) | SFO | hangars (34), tower, 17 OSM buildings (P2 `buildings.js`) |
| SFO lighting (`sfo_lighting.js`, ALS / REIL / TDZ controller, `anim/lights.js`) | SFO fixtures | none until fixtures are sourced (Phase 4) |
| Bay, shore, reservoirs, procedural region (`terrain.js`, `shore_field.js`, `reservoirs_data.js`) | SFO | field surface from the NASR profiles (P2); 3DEP optional |
| KSFO weather presets, runway plans, routine minute 56 (`state.js`, `presets.js`) | SFO | KHWD station constants (P2); no TAF |
| LiveATC mounts, roles, audio delay (`atc.js`) | D2 | a single link-out (P4) |
| `data/snapshot.js` (mixed adsb.fi licence) | licence conflict | the generated adsb.lol-only pack (P1) |
| three.js renderer (`live3.html`, `js/three/**`) | not the fork path | the custom WebGL2 renderer (P2) |

### 4.2 Technical risks

1. **Heading units** (P3, P4). sfo3d's `traffic.js` uses radians (`hdgVec(h) = [sin h, −cos h]`, `disp.hdg` in rad).
   hwd3d's `geo.js hdgVec` takes degrees.
   - Mixing them gives aircraft rotated by a factor of 57.3.
   - **Mitigation:** degrees at the package boundaries (§2.0). P3 converts on output.
   - A harness check compares a taxiing track's `disp.hdg` with its displacement bearing.
2. **Flat ground** (P2, P3, P4). sfo3d puts everything at `GROUND_Y = 3`. HWD's runway surfaces span 7.4 m, from
   8.44 to 15.88 m.
   - With a constant, aircraft would float or sink by up to about 4 m against the drawn runway.
   - **Mitigation:** `site.groundY` everywhere. A check asserts that the gear height of every ground aircraft is
     within 0.2 m of `groundY` [inf tolerance].
3. **Polling holes of 46 s** (P1, P3, P4). The rec_pack sees about 14 s of each minute. Gaps are up to 52.4 s in the
   two measured hours.
   - sfo3d dead-reckons for at most 5 s (`DR_MAX_S`) and runs 1–3 s behind.
   - In 46 s an aircraft at 70 kt flies about 1.7 km: a whole pattern leg.
   - **Mitigation:** in replay and pack modes the display runs `lookahead_s` (60 s) behind, so holes are interpolated
     between real fixes.
   - Ground holes are routed along the taxigraph, never straight across grass or buildings (`TaxiNet.route`).
   - Live mode depends on the relay's actual poll period (§2.1).
4. **Rate limits** (P1). adsb.lol's limits are "dynamic", and this sandbox's egress hit 429 after 10 polls per
   minute. The owner's machine may get a different budget.
   - **Mitigation:** the adaptive floor, a base period ≥ 6 s, one shared poll, polling stops when idle.
   - The period used is reported in `ping.poll`.
   - Never work around a 403 or a bot check.
5. **Airliner kinematics in the engine** (P3).
   - SFO-tuned rules that are wrong for GA:
     - "airplanes do not fly below 40 kt" (light singles stall near 40–50 kt; helicopters hover);
     - `LIFTOFF_KT` (airliners only), `VR_CLIMB`, `DECEL_TD` 1.6 kt/s;
     - the 50 kt take-off-roll test;
     - the `inAirport` SFO box;
     - the 75-km drop radius;
     - the 2.8° surface-heading grid assumptions.
   - **Mitigation:** extract only the generic machinery and re-derive every threshold from `hwd_events.json`,
     recording its source.
6. **Planform physics for GA** (P3). `ground.js samples()` assumes an airliner: nose gear at 3 m, track 6 m, sweep
   27°.
   - Taildraggers (Citabria, Pitts, Cub types) have a tail wheel.
   - Helicopters have skids and a rotor disc of up to about 11 m [inf].
   - High-wing and low-wing aircraft parked 1.15 m apart at tie-downs (the Green Ramp pitch is 12.15 m) need tight
     tolerances.
   - Ground fixes have NACp 10–11 for 74 % and 8–9 for 18 % (PLAN §3).
   - **Mitigation:** dims-driven samples (§2.9); spot snapping before physics; the invariants re-run on the pack.
7. **Node testability** (P3). sfo3d's `traffic.js` imports `aircraft.js` → `gl.js`, `fleet.js`, models and liveries.
   The replay tools stub the DOM (`@napi-rs/canvas`).
   - **Mitigation:** the Node-pure list of §2.0. `site.js` rasterises in pure JS, with no canvas.
8. **Cross-package coupling in `scene.js`** (P2). sfo3d's `scene.js` imports the aircraft modules and the GateSystem.
   - **Mitigation:** generic drawables (§2.5). P3 never edits `scene.js`; P2 never imports `js/aircraft/**`.
9. **The (s,t) airport grid** (P2). sfo3d's ground shader and bakes work in an airport grid with runways
   axis-aligned (`APT_RECT`, `uRw` axis 0/1). hwd3d's `geo.js` dropped the grid (its header says so).
   - **Mitigation:** an HWD grid in `js/world/grid.js`, along the 10/28 axis (119.86°, `rwyAxis('10L').hdg`). Both
     runways are parallel, so only axis 0 is used.
   - `geo.js` stays frozen.
10. **D1 leaks** (P1, P3, P4). A LADD or PIA address is itself identity, and sfo3d displays `tr.hex.toUpperCase()`
    when there is no callsign or registration.
    - Other leak paths: the parked-aircraft persistence in localStorage, the QA hooks, the logs, and published packs.
    - **Mitigation:** masking at the relay and in the pack (§2.1), with `x…` keys; `tr.ident.label` only in the UI.
    - A harness check scans the DOM, labels and `qa.tracks()` for any 6-hex token or N-number of the pack's original
      records (built locally, never committed).
11. **Publishing a pack** (P1, P4, owner). A Claude artifact with a `full`-identity pack distributes registrations of
    the unflagged aircraft. It is not a committed file, but it is published.
    - **Default:** `--ident type-only` for any artifact until the owner decides (an extension of Q1).
12. **The relay serves `out/`** (P1). sfo3d denies the whole `out/` tree, and the pack and shim live in
    `out/replay/`.
    - **Mitigation:** an `out/replay/` exception.
    - A test asserts that `refs/cache/local/**`, `refs/**`, `tools/**` and other `out/` paths answer 404.
13. **Missing or unverified dimensions** (P3, P2).
    - 23 types, including all helicopters, have no FAA ACD row.
    - The GA antenna position is inferred.
    - Building heights are unknown except the tower (15.85 m, OSM).
    - Marking dimensions beyond the committed AC extract are unread.
    - **Mitigation:** every such value is `inf` with a basis, and shown as inferred. No look-alikes; sourced values
      replace the defaults when found.
14. **Feature loss against live3** (P2). Features added only to sfo3d's three.js path are not available on the custom
    renderer: GTAO, MSDF signs, environment slabs, Blender building assets, TRAA.
    - `app.js` already lists the old renderer's limits (`envCore.rendererNote`).
    - For a 2-km GA field this is acceptable for Phase 2 [inf]; revisit at Phase 4/6 QA.
15. **Phone performance** (P2, P4). The owner mostly uses a phone. sfo3d's quality tiers were tuned for SFO; the
    software rendering here does not show phone GPU limits.
    - **Mitigation:** the `low` tier as the phone default; `MOBILE=1` harness runs; texture caps; LOD and shadow
      distances retuned to GA sizes.
16. **Chart and data drift.** AL-5015 cycle 2611 expires 26 Nov 2026 (PLAN risk 7), and the sample week is a single
    west-flow week (PLAN risk 9). Classifier thresholds learned from it may not hold in east flow.
17. **Time zone and storage collisions** (P4). The `hwdlive.` prefix (§2.0). Both apps are `America/Los_Angeles`, so
    no conversion bug hides there, and none is tested by a TZ change either.

### 4.3 Open verifications, collected

Each owner checks these against the original source and records the check:
- P1: adsb.lol's API terms and rate limits.
- P1: the readsb `dbFlags` bit meanings (PIA 4, LADD 8).
- P1, P3: the Mictronics `flags` semantics.
- P1: the KHWD routine METAR minute, over 24 h.
- P1: the METAR archive source and terms for past packs.
- P2: the AC 150/5340-1M marking dimensions beyond paras 2.8, 2.9.1 and 3.3.4.1.
- P2: whether 14 CFR Part 23 light values differ from Part 25.
- P3: the AIM 4-3-3 traffic-pattern leg definitions.
- P3: the DO-260B emitter-category meanings.
- P3: helicopter dimensions from manufacturer sources.

---

## 5. Candidate requests to sfo3d (for the orchestrator to move into `docs/requests_to_sfo3d.md`)

1. sfo3d `CLAUDE.md` "Run" still says the live relay is "not written yet" (`docs/HANDOFF.md` P2). `sfo_live_server.py`
   0.3 exists, and its `/` opens `live3.html`, not `live.html`.
2. sfo3d `CLAUDE.md` describes `live.html` as the app. The relay's default page is `live3.html` (three.js r186).
   Worth stating which page is canonical.
3. `tools/build3/replay_pack.py` packs from the relay's own recording (`refs/cache/rec`). A `--rec-pack` input (the
   committed `.jsonl.xz` hours) would let a fresh clone build a replay. hwd3d writes its own (`tools/live/build_pack.py`).
