# Phase 0 / arch: architecture and reuse map for sha3d (SHA Live 3D, ZSSS)

Date checked: **2026-11-13**. Scope: local code only, no web access, no downloads.
Read for this note:
- `sfo3d/` at the fork base **e3218d6**. `git diff e3218d6 HEAD -- sfo3d` is empty, so the current checkout is the
  fork base.
  - `sfo3d/CLAUDE.md` and `sfo3d/docs/HANDOFF.md`.
  - `docs/research/engine_impl.md` §1–3.
  - Every module header of `js/live/*`.
  - `js/geo.js`, the runway-marking part of `js/shaders/ground.js`, `js/env/wx/metar.js` and `js/env/state.js`.
  - The `js/three/*` imports, `sfo_live_server.py`, `livetest.mjs`, the headers of the tools, and `data/sfo_stands.json`.
- The sibling fork **hwd3d**, read only through git and never checked out (branch `origin/claude/hwd-live-3d`, head
  eb34f7d): `hwd3d/CLAUDE.md`, `docs/PLAN.md`, `docs/phase2_fork_map.md`, `docs/requests_to_sfo3d.md`, the headers of
  `js/geo.js` and `js/world/grid.js`, the User-Agent lines of `hwd_live_server.py`, and `git ls-tree`.

Two neighbouring outputs of this Phase 0 are cited where they matter, as **secondary**: `docs/phase0/geo.md` and
`docs/phase0/terrain.md`, and the caches in `refs/cache/ourairports_runways/`, `xplane_gateway/` and `adsb/`.

Legend:
- **[obs]**: read in the code or the git history in this session.
- **[inf]**: my inference or a design proposal.
- **[verify]**: must be checked against the original source by the owning key or phase before anyone relies on it.

Fact status (table in §10) uses the owner's scale: verified / secondary / unverified / contradicted. For code facts,
"verified" means that the primary artefact, the code at the stated commit, was read.

---

## 0. Verdict

1. **SHA is an airliner hub, so most of sfo3d's airliner machinery is reusable.** This is the opposite of hwd3d, which
   dropped jet bridges, stands, airline liveries and the airliner models.
   - Reusable: the traffic engine's airliner phase machine, jet bridges with VDGS and GSE, the stand model, the 23
     `.sfom` models and their fitting, the liveries for CES, CCA, CSN, CPA, EVA, CAL, JAL, ANA and KAL, the renderer,
     and the environment stack.
   - The **airport-specific layer** has to be rebuilt:
     - the geo frame and runway grid;
     - every data module;
     - the FAA marking, sign and lighting rules;
     - SFO's gate plan (flysfo);
     - the US data tools.
2. **Use two donors** [inf]:
   - **sfo3d @ e3218d6** for the airliner systems: `gates.js`, `traffic.js`, `aircraft/*`, `models.js`, liveries and
     stands.
   - **hwd3d @ eb34f7d** for the pieces it has already decoupled from SFO:
     - the geo-frame pattern with runway helpers and degree headings;
     - `js/world/site.js` (`groundY`, `paved`, `surface`) and `js/world/grid.js`;
     - `js/env/render_env.js`;
     - a relay with a generic User-Agent, D1 masking and pack serving;
     - `tools/live/build_pack.py` and `replay_shim.js`;
     - a `livetest.mjs` that mocks from a pack.

   Every forked file records its donor and commit in its header, as hwd3d does.
3. **Renderer path is an owner decision** (Q1).
   - sfo3d's relay opens **`live3.html`**, the three.js r186 WebGPU renderer (`sfo_live_server.py` L1714) [obs].
   - hwd3d forked the plain WebGL2 **`live.html`** path.
   - The two share every app module through a four-module import-map swap (`engine_impl.md` §2) [obs]. So the app
     can be forked once and both pages kept, but `js/three/**` has its own SFO couplings (§3.3).
   - Proposal [inf]: build Phase 2 on `live.html` first, keeping the module contracts the swap needs, and port the
     `js/three` couplings in the fidelity phase. One fact argues for live3 sooner: hwd3d's owner decision OD1 ("one
     quality level: the full-feature, highest-resolution, complex-shading version") [obs hwd3d CLAUDE.md]. Whether OD1
     also binds sha3d is unknown.
4. **The biggest architectural risk is not code. It is data.**
   - **ADS-B coverage.** The adsb.lol globe_history scan held 0 traces within 150 km of ZSSS on 2026-11-10 and
     2026-11-12 [secondary: sibling key, `refs/cache/adsb/zsss_*.json.gz`]. Every live, replay and snapshot module
     assumes a stream exists.
   - **Imagery.** The owner's rule for sha3d is stricter than for sfo3d: Google, Baidu and Amap images are "reference
     only, never geometry or texture". sfo3d measured its stands, bridges, paint and pavement on NAIP and on Google
     screenshots. At ZSSS the only open imagery is Sentinel-2 at 10 m.
     - Paint lines, hold bars, lead-ins and jet bridges therefore cannot be measured from imagery [inf].
     - They must come from OSM, the CAAC eAIP charts and the standards.
     - OSM at ZSSS has **no jet bridges** and no runway or taxiway surface polygons [secondary: geo.md].

---

## 1. The fork base (what sfo3d is at e3218d6)

- **Pages** [obs]
  - `live.html` (13 lines) is the custom WebGL2 renderer.
  - `live3.html` (34 lines) adds an import map that swaps `js/gl.js`, `js/renderer.js`, `js/scene.js` and
    `js/world/world.js` for `js/three/compat/*`.
  - Both load `js/live/entry.js` → `app.js startApp(cfg)`.
- **Size** [obs `wc -l`]
  - All of `js/`: 26,012 lines.
  - The live app in `js/live/`: 9,838 lines. The largest files are `traffic.js` (3,247) and `gates.js` (2,091).
  - The three.js path `js/three/`: 5,734 lines (all `.js` files, incl. `dev/` and `tsl/`).
  - Vendor: `vendor/three` 4.6 MB (MIT).
  - The relay `sfo_live_server.py`: 1,979 lines, Python stdlib.
  - The harness `livetest.mjs`: 84 lines.
  - Tools: about 79,000 lines of code (`.py`/`.mjs`/`.js`/`.sh`). Most of it is SFO-specific measurement (`tools/blender` 27k, `tools/buildings` 10.8k,
    `tools/liveries` 6.1k, `tools/live` 5.7k, `tools/env` 5.0k, `tools/stands` 5.0k).
- **Changes since hwd3d's base a967f9b** (`git diff --stat a967f9b e3218d6 -- sfo3d`) [obs]:
  - `js/live/models.js`: +148 lines, animated gear retraction.
  - `aircraft_real.js`, `js/three/aircraft.js`: gear.
  - `lookup.js`, `aircraft.js`: a registration-decal cache fix.
  - `world/terrain.js`: a 5-line terrain pit.
  - `tools/trailer/track/*`: tracking films.
  - More `rec_pack` hours.

  All of these are airliner-side, which is the part sha3d keeps. So sha3d must take these files from e3218d6, not from
  hwd3d.

---

## 2. Proposed shape of sha3d [inf]

### Contracts

These carry over from hwd3d fork-map §2.0, adapted.

- **World frame `ltp-wgs84-zsss`.** x = east, z = south, y = up, in metres. The origin is the ARP, taken from the eAIP
  AD 2.2 [verify].
  - The frame is an exact local tangent plane on the WGS 84 ellipsoid.
  - **There is no NAD83 shift.** ADS-B, OSM, Sentinel-2 (UTM 51N, EPSG:32651) and the AIP (WGS-84 per ICAO Annex 15)
    all enter through a single `wgs84ToWorld`.
  - sfo3d's `DATUM` (dE −1.568 m, dN +0.159 m) must not be copied.
  - **GCJ-02 is never an input.** If a GCJ-02 test helper is needed (`tools/geo/gcj02.py` exists for the test), it
    stays in tools and is never imported by the app.
  - Open: whether the CAAC AIP coordinates are CGCS2000 or WGS-84 at a current epoch. The difference is of the order of
    1 m from plate motion since 2000.0 [inf, verify].
- **Vertical.**
  - y is height (in the datum of the field elevation, decided by the AIP and terrain keys). Ground contact always goes
    through `site.groundY(x, z)`.
  - sfo3d uses the constant `GROUND_Y = 3` 111 times in the live/world/env path, plus 35 times in `js/three` [obs grep].
  - The ADS-B geometric height needs the geoid undulation at ZSSS. sfo3d's `GEOID_M = 32.29` is an SFO value.
- **Runway grid.**
  - One axis along 18→36, as hwd3d's `grid.js`, because both runways are parallel.
  - OurAirports gives 176° / 356° true [secondary]. The real axis comes from the eAIP threshold coordinates [verify].
- **Headings at package boundaries are in degrees true.** Inside a module, radians are fine. sfo3d's `traffic.js`
  `hdgVec` takes radians, while hwd3d's `geo.js` `hdgVec` takes degrees (hwd fork-map risk R1).
- **Data is injected, not imported at module scope.**
  - `gates.js` builds its building index at import time from `STANDS`, `BUILDINGS`, `AIRPORT` and `B3D_INTEGRATION`
    (L88–106) [obs].
  - The sha3d fork takes these through its constructor, so the same code runs in Node tools.
- **Names.**

  | Item | sha3d name |
  |---|---|
  | Debug hook | `window.SHA` |
  | Readiness and error flags | `__shaReady` / `__shaError` |
  | Mode override | `SHA_MODE` |
  | Embedded models | `SHA_EMBED` |
  | Model base path | `SHA_MODEL_BASE` |
  | localStorage prefix | `shalive.` (sfo3d `sfolive.`, hwd3d `hwdlive.`: all three can share an origin) |
  | Relay ping | `{"shalive": 1}` |
  | Relay file | `sha_live_server.py` |

- **Time zone `Asia/Shanghai`** (UTC+8, no DST) [verify against AIP GEN 2.1]. sfo3d hard-codes
  `America/Los_Angeles` in `env/clock.js`, `live/ui.js` (×3) and `live/stats.js` [obs].
- **Provenance.** `src: 'obs' | 'inf'` (plus `rule` / `evidence`) on stands, bridges, holds, signs and phases, as in
  sfo3d and hwd3d. The UI shows "inferred".

### Directory layout

It mirrors sfo3d and hwd3d:

- the top level: `live.html`, `live.css`, `sha_live_server.py`, `livetest.mjs`;
- `js/{geo,gl,math,geom,renderer,scene}.js`;
- `js/{live,world,env,aircraft,shaders}/`, plus `js/three/` if Q1 says so;
- `data/` (generated);
- `tools/{common,osm,aip,s2,stands,live,env,models,liveries,cache}/`;
- `jobs/`;
- `docs/`;
- `refs/cache/<topic>/` with a `SOURCES.json` in each.

---

## 3. Module-by-module map

Verdicts:
- **copy**: unchanged apart from the fork header;
- **adapt**: kept, with the listed changes;
- **replace**: new code takes the role;
- **drop**: not needed.

Donor: **S** = sfo3d @ e3218d6; **H** = hwd3d @ eb34f7d.

Effort is in package-hours of focused agent work: **S** < 1 h, **M** 1–3 h, **L** 3–8 h, **XL** > 8 h, over several
sessions. The calibration is hwd3d's Phase 2: about 25 modules plus the relay and the pack, built by 4 parallel
packages between 11:13Z and 16:28Z on 2026-11-13, so roughly 20 package-hours [obs git timestamps; the scale is inf].

### 3.1 Page, shell, harness

| sfo3d module (lines) | Verdict, donor | What changes for ZSSS | Effort |
|---|---|---|---|
| `live.html` (13), `live.css` (254) | adapt, S | title and brand; fonts (Google Fonts links: a phone in mainland China may not reach fonts.googleapis.com [inf, verify]; consider self-hosting an OFL font) | S |
| `live3.html` (34) | adapt or later, S | only if Q1 = three.js | S |
| `js/live/entry.js` (36) | replace, H+S | data imports (`sha_*`); relay detection `j.shalive`; the replay-shim hook (H); `MODEL_KEYS` (S, plus any C919/ARJ21 keys); `SHA_*` globals | S |
| `js/live/app.js` (596) | adapt (rewrite around the contracts), S+H | keep the bridge/gate hooks, ALS planes, routes and views; drop the reservoirs, shore foam, flysfo plan, `RUNWAY_SIGNS` 10L/10R/1L/1R, KSFO METAR and SFO camera presets (`[-450, GROUND_Y, 150]` …); env glue via H `render_env.js`; `window.SHA`; storage prefix `shalive.` | L |
| `js/live/ui.js` (371) | adapt, S | TZ; remove "gate vs SFO's plan" and flysfo deep links; stand labels from the AIP stand numbers; optionally bilingual labels (Q6) | M |
| `js/live/controls.js` (171) | adapt, S+H | `heightAt` = `site.groundY`; initial target and distance (SFO `[-600, 3, 200]`, 5,200 m); near/split/far can stay at airliner scale | S |
| `js/live/about.js` (46) | replace | notices from `docs/ATTRIBUTION.md`: OSM ODbL, adsb.lol ODbL, Copernicus Sentinel / DEM, CAAC AIP terms [verify], model licences | S |
| `js/live/atc.js` (172) | replace or drop | the KSFO LiveATC mounts and the Chart Supplement edition are SFO-only; whether LiveATC has any ZSSS feed and its terms are unknown (liveatc.net answers 403 here) → a link-out only, after Q4 | S |
| `js/live/stats.js` (118) | adapt, S | 4 SFO runways → 18L/36R and 18R/36L; TZ | S |
| `livetest.mjs` (84) | adapt, H | the mock reads `data/snapshot.js` and uses `cos(37.6188)` / 110,990 m per degree (L28); ping `sfolive`; mock METAR `KSFO`; SFO routeset callsigns → a pack-based mock (H) with the ZSSS latitude, METAR `ZSSS`, `{shalive:1}` | M |
| `jobs/*.mjs` (34) | adapt, S | views `gate:<stand>`, `hold:i`, `tower`, `thr:<end>` keep their syntax with new names | M |
| `package.json` | copy or adapt | three only if Q1 = three.js | S |
| `tools/build3/phone_artifact*` | adapt later, S | the artifact build (snapshot/replay mode, ≤ 16 MB) | M (later) |

### 3.2 Geo frame and grid

| Module | Verdict, donor | What changes | Effort |
|---|---|---|---|
| `js/geo.js` (210) + `tools/geo_frame.py` (242) + `tools/test_geo_frame.py` (122) | replace, pattern from H `js/geo.js`, `tools/common/hwd_frame.py`, `test_hwd_frame.py` | ARP and runway ends from the eAIP; WGS-84 frame without the NAD83 shift (§2); UTM 51N helpers (Sentinel-2) instead of UTM 10N (NAIP); `rwyAxis` / `rwyAlongAcross` / `rwySurfaceY` from the AIP threshold elevations; drop the SFO `TERMINAL_CENTER`, `PIERS`, `ITB`, `BAY_WATER_KM`, `AIRPORT_LAND_ST`, `APPROACH_LIGHTS` and the 8-end `RWY_ENDS`; JS and Python twins tested both ways to 1 mm | M |
| `js/world/airfield.js` (274: `APT_RECT`, `RWY` in (s,t), hand-drawn SFO taxiways) | replace by H `js/world/grid.js` | one axis along 18→36; `APT_RECT` derived from the OSM aerodrome polygon (6.7 km², geo.md) | S |
| (none) → H `js/world/site.js` | adapt, H | `groundY` (field model from the AIP and the DEM; terrain.md warns that the GLO-30 airport heights are flattened planes), `paved` / `surface` (OSM has only centrelines with width, so the surfaces are built from OSM width × centreline, the apron polygons and Sentinel-2 checks [inf]), `building`, `anchors` (tower, views) | L |

### 3.3 Renderer core and shaders

| Module (lines) | Verdict, donor | What changes | Effort |
|---|---|---|---|
| `js/gl.js` (211), `math.js` (143), `geom.js` (127), `shaders/common.js` (171), `env.js` (210), `objects.js` (151), `post.js` (92), `sprites.js` (71), `world/textures.js` (157), `live/earcut.js` (177) | copy, S | none (no SFO dependency) [obs imports] | S |
| `js/renderer.js` (334) | copy, S | the airliner-scale shadow splits [120, 700, 3500] suit SHA (hwd3d had to retune; we do not) [inf] | S |
| `js/scene.js` (83) | adapt, S (plus H's generic-drawable idea) | imports `aircraft/fleet.js`, `aircraft/model.js` and `world/gates.js` and uses `GROUND_Y`; the airliner drawables stay, but the parked-at-gates video helper (`parkAtGates`) is dropped | S |
| `js/shaders/ground.js` (467) | adapt (major), S | see §4. Hard-coded: `uRw[4]` (4 runways), half-width 30.48 m (a 200 ft runway), 16 FAA stripes of 5.75 ft, aiming point at 1,020 ft (310.9–356.6 m), FAA TDZ bars at 500/1,500/2,000/2,500/3,000 ft, "letter then number" layout, blast-pad chevrons and EMAS set-back, rubber "28s land on the x1 side" (`i < 2`, L145) [obs]. City and far-city bakes are SFO. All of these become per-runway uniforms from the AIP (width, LDA, displaced threshold, designation, landing direction) with an ICAO/CAAC pattern table | L |
| `js/shaders/aircraft.js` (201), `aircraft_real.js` (163) | copy, S | airliner shaders, kept (hwd3d dropped them) | S |
| `js/world/world.js` (112) | adapt, S | keep `bakeGround`; replace `CITY_RECT` / `CITYFAR_RECT` (SFO peninsula) with a Shanghai urban bake from ESA WorldCover or Sentinel-2 [inf, terrain key] | M |
| `js/three/**` (5,734) and `vendor/three` | adapt (if Q1), S | SFO couplings [obs grep]: `ground.js` imports `CITY_RECT`, `APT_RECT`, `LANDSIDE` (sfo_landside), `shoreField` (sfo_shore), `worldToST`, and **duplicates the FAA runway-marking geometry** (L331–407): a second copy to change. `flood.js`: SFO OSM masts, `MAST_H`, `GROUND_Y`, calibrated to the ICAO 20 lx design value. `objects.js`: `DIR_S`/`DIR_T`, SFO glass. `renderer3.js`: imports `data/sfo_buildings.js`. `buildings3d.js`: SFO Blender assets (`B3D_INTEGRATION`), replace or disable. `sky.js`: `GROUND_Y`. Generic (copy): `engine`, `lights`, `rain`, `ssr`, `perf`, `convert`, `tsl/*`, `compat/*`, `markings`, `signs` (MSDF, Liberation fonts, SIL OFL), `bridges`, `aircraft` | L–XL |

### 3.4 World, airport, markings, signs, buildings

| Module (lines) | Verdict | What changes for ZSSS | Effort |
|---|---|---|---|
| `js/world/terrain.js` (350: a procedural 120 km region, the Bay, reservoirs, `data/sfo_shore.js`) | replace | DEM (Copernicus GLO-30), land cover (WorldCover) and water (OSM rivers and canals) around ZSSS; no Bay or seawall [inf, terrain key] | L |
| `js/env/shore_field.js` (59), `reservoirs_data.js` (2) | drop | SFO-only | — |
| `js/live/world.js` (141, `buildLiveWorld`) | adapt | the assembly stays; inputs change (`site`, `grid`, sha data); EMAS geometry dropped unless the AIP lists arresting beds (unlikely [inf]) | M |
| `js/live/airport.js` (439) | adapt | keep `standGates` / `liveGates` / `inStandEnvelope` / `buildStandMarkings` (the schema is generic); `CLASS_MAX` (SFO classes B, C, CL, D, E, EL, F) → ICAO code letters A–F with the AIP max span / length per stand [verify]; `HALL_H` / `STRUCT_H_BY_NAME` (SFO buildings) → OSM / sourced heights; `END_ZONES` (SFO pads / EMAS) → from AIP AD 2.12 (stopway, RESA) [verify]; `LANDSIDE` (sfo_landside) → OSM | L |
| `js/live/markings.js` (201) | adapt | header: "built to FAA AC 150/5340-1 dimensions" [obs]. Re-dimension to ICAO Annex 14 / CAAC (§4): centreline, holding position patterns A / B, intermediate holds, stand lead-ins, stop and safety lines; drop the FAA enhanced centreline unless the ZSSS standard or charts show it | M |
| `js/live/signs.js` (216) | adapt | keep `makeAtlas` and the shader; the SFO sign list from `sfo_airport` / `sfo_details` goes; the FAA distance-remaining signs go unless sourced; CAAC sign set and colours (§4). Follow hwd3d: place **no** sign until its position is sourced (`not_yet_sourced`) | M |
| `js/live/terminals.js` (233: SFO T1–T3, ITB, 221 ft tower) | replace | Hongqiao T1 and T2 (+ piers), the tower, hangars: footprints from OSM (4 terminal objects, 4 hangars, 1 tower node [secondary geo.md]); heights and facades from sourced documents or photos with an open licence [verify]; a fidelity phase | XL |
| `js/live/items.js` (33, masts) | adapt | the 70 SFO OSM masts → ZSSS masts if OSM maps any [verify] | S |
| `js/live/lights.js` (41) + `js/anim/lights.js` (263) | replace | SFO ALS piers / MALSR → the ICAO/CAAC approach-lighting systems from AIP AD 2.14 [verify] | M |
| Building assets `tools/blender` (27k) | method reused later; drop the data | SFO assets measured on NAIP and Google screenshots; for ZSSS the glTF-with-LOD path is reusable, but the measurements are not | XL (later) |

### 3.5 Stands, jet bridges, GSE (the main reuse that hwd3d did not have)

| Module (lines) | Verdict | What changes for ZSSS | Effort |
|---|---|---|---|
| `data/sfo_stands.json` schema (108 stands: 66 obs / 42 inf; classes C 60, EL 21, E 8, CL 7, B 6, F 3, D 3 [obs]) | keep the schema, new data | per stand: `name`, `alias`, `nose`, `hdg`, `cls`, `src`, `bridges[{attach, rotunda, cab, walk, door, model, ext_range, stow…}]`, `typeStops`, `redBoxes`, `antenna_ref`. Add `kind: contact | remote | cargo | maintenance`, the boarding mode (bridge / bus / walk) and the ICAO code letter | — |
| `tools/stands/build_stands.py` (1,624) + `osm_src.py`, `geom.py`, `check_stands.py` | adapt | sources: OSM `aeroway=parking_position` (geo.md: 164 stand nodes with ref 101–608, 461 lead-in lines [secondary]) and the AIP aircraft parking / docking chart with its stand coordinate table, if the eAIP has one [verify]. **Names** from the AIP (instead of flysfo AODB and DataSF). **Classes** from the AIP stand table (instead of flysfo types). **Bridges:** OSM has none at ZSSS [secondary], NAIP does not exist, and Google may not be used as geometry, so bridge position and length are `inf` from the facade and the stand (the S `geom.py` envelope checks stay) unless the AIP or the airport publishes a contact-stand plan [verify]. `naip_ac.py` / `naip_axis.py` / `naip_relief.py` / `redboxes_naip.py`: drop (no imagery that fine) | L |
| `tools/stands/adsb_parked.py` (131) | adapt | the method is generic, but it ties stays to SFO's AODB windows. At ZSSS it needs ADS-B ground coverage, and the sibling scan found none (§8 R1) | S (blocked by data) |
| `js/live/gates.js` (2,091) | adapt | the bridge kinematics (Oshkosh AT2/AT3 sell sheet, FAA AC 150/5220-21C slopes), VDGS and GSE logic are generic. Changes: module-scope SFO data (`STANDS`, `BUILDINGS`, `AIRPORT`, `B3D_INTEGRATION`, L88–106) → injected; `DEPARTURE_LEVELS` (per SFO pier) → per ZSSS pier [verify]; the bridge make and model at ZSSS is unknown (possibly a Chinese manufacturer [unverified]): keep the S kinematics as `inf` until sourced; VDGS make unknown [verify]; **remote stands** need bus boarding and stair trucks, which sfo3d does not draw (new GSE types) | L (+ M for remote-stand GSE) |
| `js/world/gates.js` (309: GSE meshes, belt loaders, catering) | copy | generic. **Chinese GSE liveries and layouts** are a fidelity item | S |
| `js/aircraft/dock.js` (131), `data/models/dock_foot.js` | copy | airliner door and bellows fit | S |
| `js/live/ground.js` (465: `GroundPhysics`) | adapt | keep the planforms, ICAO clearances and bridge fields; `GROUND_Y` → `site.groundY`; `buildingGrid` from the sha buildings; `pavedUnion` with the sha `TaxiNet` | M |

### 3.6 Traffic, phase classifier, feed, identity

| Module (lines) | Verdict | What changes for ZSSS | Effort |
|---|---|---|---|
| `js/live/traffic.js` (3,247) | adapt | **Keep:** ingest hygiene, Hermite + dead reckoning, the kinematic body (`ctlGround` / `ctlAir` / `attitude`), the airliner phase machine (final, approach, go-around, departure, take-off, line-up, landing, taxi, push-back, holding, pushed, gate, parked, vehicle), `TaxiNet`, stand matching (`matchGate`, `gateScore`, `standFits`), docking, silent docking, bridge sync, parked persistence. **Change:** <br>• `RWY` / `PARALLEL` built from the new `geo.js`; <br>• `inAirport` (an SFO box, L276) → the ZSSS polygon; <br>• `ground-other` → ZSPD and the other nearby fields; <br>• the 75 km drop radius (L573), retuned; <br>• `GEOID_M = 32.29` (L31) → the undulation at ZSSS; <br>• the SFO-observed tables `LIFTOFF_KT`, `TD_PRED_M = 770`, `DECEL_TD` and the "E175 WOW ~50 kt" note → re-learned on ZSSS data, or kept as `inf` priors; <br>• `STORE_KEY 'sfolive.parked.v4'` → `shalive.`; <br>• radians → degrees at the boundary; <br>• the 24 `GROUND_Y` uses → `site.groundY`; <br>• the **92 lines of flysfo plan logic** (`planFor`, `stalePlanGone`, `offBlockAhead`, `standRealloc`, `expectStand` …) → off: `planFor()` returns null unless an SHA stand-allocation source appears (Q5). The engine already has the geometry + heading fallback [obs header]. `ANT` / `ANT_REF` (GNSS antenna position per family) are type properties learned at SFO, so they are kept as `inf` priors | XL |
| — new: runway-flow / config detector | new or adapt | which runways ZSSS uses for arrivals and departures in north and south flow: learned from ADS-B, else from the AIP / wind (replaces the SFO West / Southeast plans in `env/state.js`) | M |
| `js/live/feed.js` (163) | adapt | keep `normalizeAircraft`, `parsePayload`, `Feed`, `StreamFeed`, `fetchMetar`, `fetchTaf`; `Routes` (adsb.lol routeset / VRS standing data, CC0) only if its coverage of Chinese domestic flights is adequate [verify]; drop `fetchGates`; default station `ZSSS` | S |
| `js/live/lookup.js` (217) + `data/lookup.js` (VRS standing data, worldwide) | adapt | `AIRLINES` / `TYPE_NAMES` already list CES, CSH, CQH, DKH, CCA, CSN, CHH, CSZ, CXA, HXA, CPA, EVA, CAL, JAL, ANA, KAL [obs]. `nNumberFromHex` is US-only: Chinese B-registrations cannot be derived from the 24-bit address [inf], so take the feed `r` or the Mictronics database (H `tools/registry/mictronics_db.py`, ODC-By) | M |
| `data/brands.js` + `tools/liveries/build_brands_js.py`, `brands_meta.py` | replace | US DOT BTS regional-airframe → brand logic is SFO/US-only; Chinese carriers need callsign → brand plus group subsidiaries (fleet key) | M |
| D1 (LADD / PIA masking, H) | adapt, H | `dbFlags` LADD / PIA are FAA programmes, rarely set at ZSSS; keep the H masking (it costs nothing) and the rule that no committed file holds a per-aircraft identity [inf] | S |
| `tools/live/replay_engine.mjs`, `invariants.mjs`, `replay_app.mjs` | adapt | bridges and stands stay (hwd3d dropped them); flysfo checks go; input = sha3d recordings | M |

### 3.7 Aircraft, models, liveries

| Module (lines) | Verdict | What changes | Effort |
|---|---|---|---|
| `js/aircraft/types.js` (411), `fit.js` (798), `model.js` (343), `fleet.js` (146), `stretch.js` (133), `cockpit.js` (116) | copy, S | add **C919** and **ARJ21 / C909** (ICAO designators [verify]) with dims, doors, wing and antenna; no such entries exist [obs `ICAO_TYPES`] (fleet key) | S + M per new type |
| `js/live/aircraft.js` (222), `js/live/models.js` (442, incl. the e3218d6 gear retraction) | copy, S | `SFO_EMBED` / `SFO_MODEL_BASE` → `SHA_*` | S |
| `data/models/*.sfom` (23: a319 … md11) | copy, S | FlightAirMap / FGMEMBERS, GPL-2.0 per model (sfo3d `docs/ATTRIBUTION_models.md`) [obs]; A220 licence open (HANDOFF §7.12); C919 / ARJ21 models do not exist here | S |
| `js/aircraft/liveries.js` (72) + `data/liveries/*` (57 brands incl. CES, CCA, CSN, CPA, EVA, CAL, JAL, ANA, KAL [obs]) | copy + add | missing: Shanghai Airlines (CSH), Spring (CQH), Juneyao (DKH), Hainan (CHH), Shenzhen (CSZ), Xiamen (CXA), Sichuan, Shandong, China Express … (fleet key); trademark question as at SFO | M per livery |
| `js/env/aircraft_lights.js` (218, 14 CFR 25) | copy | CCAR-25 mirrors Part 25 [unverified] | S |

### 3.8 Environment, weather, airfield lighting

| Module (lines) | Verdict | What changes | Effort |
|---|---|---|---|
| `js/env/clock.js` (92) | adapt | `TZ = 'America/Los_Angeles'` (L18) → `Asia/Shanghai` | S |
| `js/env/ephemeris.js` (429) | adapt | `SFO` observer constant (L53) → the ZSSS ARP | S |
| `js/env/app_env.js` (90), `presets.js` (19) + `data/sfo_env_presets.js` | adapt / replace | station `ZSSS`; KSFO presets and TAFs → empty, or ZSSS later | S |
| `js/env/state.js` (466) | adapt | `FIELD_ELEV_FT = 13.1`; `RWY_HDG {28: 297.83, 10: 117.83, 19: 207.83, 1: 27.83}` (L47); the SFO West / Southeast plans; `IAP_ENDS`; the "SFO 2500'/5" minima; `FG IN GAP` and marine-layer patches; Kyba Berlin sky glow "applied to SFO"; routine minute 56 (L373). Replace them with ZSSS flow logic and haze/fog regimes [inf]. Remove the FAA JO 7110.65 runway-use rule or keep it only as a labelled fallback | L |
| `js/env/wx/metar.js` (604) | adapt | It already handles `MPS` winds, `CAVOK`, `9999` / metric visibility and `Qxxxx` [obs L128–168]. Gaps: **ICAO trend groups (`NOSIG`, `BECMG`, `TEMPO`) are not cut off before `parseBody`**, so trend weather and cloud would enter the observation (L360–381) [obs code; the effect is inf]. `renderParams(..., routineMinute = 56)` (L490); the US-only remark parsing is harmless. Chinese METARs are half-hourly [unverified]. Golden tests with real ZSSS reports | M |
| `js/env/wx/taf.js` (94) | copy | ZSSS has a TAF [verify] (KHWD had none) | S |
| `js/env/atmo/sky_model.js`, `weather_fx.js`, `exposure.js` | copy | perhaps retune the haze and sky glow for Shanghai [inf] | S |
| `js/env/lighting/photometry.js` (158) | copy | generic | S |
| `js/env/lighting/airfield.js` (307), `controller.js` (149: FAA JO 7110.65), `fixtures.js` (146) + `data/sfo_lighting.js` (3,633 fixture faces) + `tools/env/build_lighting_spec.py` (919) | replace | fixtures from AIP AD 2.14 (approach, threshold, TDZ, centreline, edge, PAPI) and AD 2.15, to Annex 14 photometry; the controller logic becomes the ICAO intensity steps [verify] | L |

### 3.9 Relay, recording, snapshot / replay, persistence

| Module (lines) | Verdict | What changes for ZSSS | Effort |
|---|---|---|---|
| `sfo_live_server.py` (1,979) → `sha_live_server.py` | adapt, H as base + S parts | **Keep:** `Http`, `Poller` (back-off, adaptive floor), `Hub._merge` hygiene, SSE full/delta, `Metar`, replay, `StaticGzip`, deny rules. **Remove:** `ARP` (37.6188056, −122.3754167); `--radius 40` (NM around SFO); `FaaRegistry` (L105–187); `Gates` (flysfo, L1084–1420); KSFO METAR/TAF handling and the hh:56 TTL schedule; `/` → `live3.html`; `sfolive`. **The User-Agent:** S builds it from `CONTACT`, the owner's repository URL (L56–57), and sends it to every provider. H replaced it with a generic UA without names or URL (H L98–99). sha3d must use the generic form, under the owner's privacy rule. **Endpoints:** `/api/ping {shalive}`, `/api/adsb`, `/api/stream`, `/api/metar?ids=ZSSS`, `/api/taf` (if ZSSS has a TAF), `/api/status`; `/api/routeset` only after Q-verify; `/api/gates` removed unless Q5 finds a source. **Providers:** make them pluggable. The sibling recorder already logs adsb.lol, adsb.fi and OpenSky (`tools/rec/live_rec.py`); OpenSky terms are [verify] before any use beyond local research | L |
| `tools/live/record.py` (100), `recio.py` (54), `build_stream.py` (91) | adapt / copy, H | centre ZSSS; never commit adsb.fi records (licence) | S |
| `data/snapshot.js` + `tools/live/build_snapshot.py` | drop | the sfo3d snapshot mixes adsb.fi records (licence conflict, OD-11, sfo3d `docs/ATTRIBUTION.md`) | — |
| `tools/build3/replay_pack.py` + `replay_shim.js` | replace by H `tools/live/build_pack.py` + `replay_shim.js` | input = sha3d's own adsb.lol recordings (SFO's `rec_pack` is trimmed to 25 nm of SFO: useless here); with no coverage the pack may be empty (R1) | M |
| `tools/live/build_taxigraph.py` (109) | replace, H node-graph version | input OSM via **api.openstreetmap.org** (Overpass mirrors do not answer here; H's `osm_attic_api.py` with member geometry); runways from the AIP ends; holds from OSM (37 nodes, no designators) | M |
| `tools/xcheck/fetch_osm.py` | adapt, H | H strips `user` / `uid` (privacy) and queries lifecycle keys; pin the date | S |
| `tools/xcheck/fetch_xplane.py`, `parse_aptdat.py` | copy | X-Plane gateway ZSSS: cross-check only (GPL, Gateway licence unverified; sibling SOURCES.json) | S |
| `tools/cache/sync.py` (263), `restore.sh` | adapt | paths and patterns for `sha3d/refs/cache`; `sha3d/.gitignore` already follows the same rule [obs] | S |
| `tools/live/gatecheck.py`, `replay_score.py`, `drgap.py`, `analyze_feeds.py`, `replay_*` audits | drop / fork later | flysfo-tied SFO audits; `drgap` / `replay_score` are worth a fork once SHA recordings exist | — |

### 3.10 Data modules

Every `data/sfo_*.js` is replaced by generated `data/sha_*` from the sha3d tools. None may be copied:

- `sfo_airport` (SFO Museum, CDLA);
- `sfo_details` (centrelines, holds, apron, masts);
- `sfo_buildings`, `sfo_landside`;
- `sfo_stands` (OSM, NAIP, flysfo);
- `sfo_paint`, `sfo_pavement` (Google-screenshot classification);
- `sfo_shore`;
- `sfo_lighting`, `sfo_env_presets`;
- `sfo_taxigraph`;
- `buildings3d/*`;
- `snapshot.js`.

The following stay with their licences, as copies:
- `data/lookup.js` (VRS standing data, CC0);
- `data/models/*` (GPL-2.0 per model);
- `data/liveries/*` (own textures);
- `data/models/dock_foot.js`.

---

## 4. ICAO / CAAC versus FAA: what must become parameters

**Every row below is unverified.** It was written from memory, not read in a standard. The markings key, or Phase 1,
must check each one against ICAO Annex 14 Vol I chapter 5 and the CAAC aerodrome standard. That standard is believed to
be **MH 5001-2021 民用机场飞行区技术标准**, but the designation itself is [unverified]; the task text's "MH/T 5001?" is
not confirmed. Check them also against the ZSSS eAIP charts.

The code facts in the middle column are [obs].

| Item | sfo3d today (FAA) [obs code] | ZSSS candidate (to verify) |
|---|---|---|
| Runway width / half-width in shader | 30.48 m fixed (200 ft) | per runway from AIP AD 2.12 (OurAirports: 18L/36R 148 ft, 18R/36L 197 ft [secondary]) |
| Threshold stripes | 16 × 5.75 ft, double centre gap, 150 ft long | Annex 14: count by runway width (e.g. 16 at 60 m, 12 at 45 m), stripes ≥ 30 m long, about 1.8 m wide [unverified] |
| Designation | letter nearer the threshold, then the number; FAA numeral glyphs (SDF atlas) | Annex 14 numeral and letter forms and placement [unverified]; a new glyph set may be needed |
| Aiming point | at 1,020 ft, 150 ft long | Annex 14: distance by LDA (e.g. 400 m for LDA ≥ 2,400 m) [unverified] |
| TDZ marking | FAA 3-2-2-1-1 bars at 500 ft intervals | Annex 14: pairs by LDA, pattern A or B [unverified] |
| Displaced threshold, blast pad, EMAS | arrows, chevrons, EMAS beds at SFO ends | only where the AIP lists them [verify] |
| Taxiway centreline | 6 in yellow; enhanced centreline (FAA-only) before holds | ICAO 15 cm yellow; no FAA enhanced centreline [unverified] |
| Runway-holding position | FAA 4 lines 12 in | ICAO pattern A (two solid, two dashed) and pattern B (CAT II/III) [unverified]; mandatory instruction marking painted on the pavement where required |
| Signs | FAA mandatory (red / white), location (yellow on black), distance-remaining (white on black) | ICAO / CAAC colours much the same [unverified]; whether Chinese characters appear on airfield signs, and on which sign types [unverified]; distance-remaining signs only if sourced |
| Stand markings | lead-ins, stop bars, red equipment boxes (`redBoxes` measured on imagery) | CAAC stand number, lead-in, stop lines and red safety or clearance lines [unverified]; no imagery to measure them (§0) |
| Approach lighting | MALSR / ALSF-2 at SFO (`APPROACH_LIGHTS`, `anim/lights.js`) | ICAO precision approach CAT I/II/III systems per AIP AD 2.14 [verify] |

---

## 5. sfo3d hard-coded values that must not leak into sha3d

All rows are [obs].

| Value | Where (file:line at e3218d6) | sha3d replacement |
|---|---|---|
| ARP 37.6188056, −122.3754167 | `js/geo.js:17`, `sfo_live_server.py:55`, `js/env/ephemeris.js:53`, `livetest.mjs:28` (`cos(37.6188)`), `js/live/atc.js` | the eAIP ARP in a WGS-84 frame |
| NAD83(2011) → WGS 84 shift dE −1.568, dN +0.159 m | `js/geo.js` `DATUM` | none (a WGS-84 frame) |
| Runway grid along 117.83° / 27.83° (s, t; `V`, `U`, `DIR_S`, `DIR_T`, `HDG_28`) | `js/geo.js:66–81`, `env/state.js:47` (`RWY_HDG`), `traffic.js`; 119 grid uses across live / world / three / shaders | one axis along 18→36 from the eAIP (`grid.js`) |
| `GROUND_Y = 3.0` ("above bay datum") | `js/geo.js:83`; 111 uses (live / world / env / anim) + 35 (`js/three`) | `site.groundY(x, z)` |
| `GEOID_M = 32.29` (EGM96 at SFO) | `js/live/traffic.js:31` | the geoid undulation at ZSSS (terrain / AIP keys) |
| `FIELD_ELEV_FT = 13.1` | `js/env/state.js:45`, `env/lighting/fixtures.js` | AIP AD 2.2 elevation (with its datum) |
| `inAirport` box (−2,700 < x < 1,950, −2,350 < z < 1,800) | `js/live/traffic.js:276` | the OSM aerodrome polygon |
| 4 runways, 8 ends, `RWY_ENDS` with disp 300 / 640 / 560 ft | `js/geo.js`, `shaders/ground.js` `uRw[4]`, `three/ground.js` | 2 runways, 4 ends from the AIP |
| FAA marking dimensions (16 stripes, 1,020 ft, TDZ table, 6 in / 12 in lines) | `shaders/ground.js:80–107`, `three/ground.js:331–407`, `live/markings.js:1–10` | ICAO / CAAC table (§4) |
| `LIFTOFF_KT`, `TD_PRED_M = 770`, `DECEL_TD = 1.6` (SFO observations) | `js/live/traffic.js:149–155` | re-learn on ZSSS data or label `inf` |
| `TZ 'America/Los_Angeles'` | `env/clock.js:18`, `live/ui.js` (×3), `live/stats.js:90` | `Asia/Shanghai` |
| KSFO station and routine minute 56 | `sfo_live_server.py` (21 KSFO hits), `env/wx/metar.js:490`, `env/state.js:373`, `live/app.js`, `feed.js` | `ZSSS`; its routine minutes [verify] |
| `sfolive` (ping), `sfolive.` (storage), `sfolive.parked.v4` | relay `:1721`, `entry.js:18`, `app.js:58`, `traffic.js:146` | `shalive` |
| `window.SFO`, `__sfoReady`, `SFO_EMBED` / `SFO_MODEL_BASE` / `SFO_LITE` / `SFO_B3D_*` | `app.js`, `entry.js`, `models.js`, `liveries.js`, `js/three/*` | `SHA_*` |
| Relay User-Agent with the owner's repository URL | `sfo_live_server.py:56–57` | generic UA (hwd3d pattern) |
| flysfo gate plan (`/api/gates`, `planFor` …) | relay `Gates`, `traffic.js` (92 lines), `ui.js`, `about.js`, `feed.js` | off (Q5) |
| SFO camera presets and views (`overview` `[-450, 3, 150]`, `final28`, `runways1`, tower eye `GROUND_Y + 62`) | `app.js:398–408`, `controls.js:12` | from `site.anchors` and the ZSSS thresholds |
| LiveATC KSFO mounts | `js/live/atc.js` | link-out only after Q4 |
| Mock relay: SFO snapshot, `KSFO` METAR, SFO routes | `livetest.mjs` | pack mock with the ZSSS latitude |
| `CLASS_MAX`, `HALL_H`, `STRUCT_H_BY_NAME`, `DEPARTURE_LEVELS` (SFO buildings and piers) | `live/airport.js:65, 192–194`, `live/gates.js:256` | from the sha data |

---

## 6. sfo3d tools that depend on US-only (or SFO-only) sources

[obs] means the tool headers name the source. The replacements are [inf] unless stated.

| US / SFO source | sfo3d tools that depend on it | Replacement for ZSSS |
|---|---|---|
| **USDA NAIP** (0.6 m, public domain) | `tools/imagery/*` (19 files: `naip_fetch`, `naip_world`, `paintline`, `als_naip`, `check_markings`, `shore_naip`, `naip_faa_check`, `paint_pave_naip`, `adsb_ground_cells`, `tower_lean` …); `tools/stands/naip_ac`, `naip_axis`, `naip_relief`, `redboxes_naip`; `tools/buildings/*` (most of 53); `tools/blender/*` (most of 66); `tools/env/lighting_naip_measure.py`, `check_als_placement.mjs`; `build_airfield_details.py`; `build_terminal_parts.py`; `tools/drawing/*` | **Sentinel-2 L2A** (10 m, Copernicus free and open; earth-search COGs reachable here) for layout and registration only. sha3d tools already exist: `tools/geo/s2_crop.py`, `s2_osm_align.py`, `tools/terrain/s2_crop.py`. Paint, hold bars, lead-ins, sign and fixture positions are **not measurable** at 10 m: they come from OSM, the AIP charts and the standards. |
| **Google Maps screenshots** (owner's, reference) | `tools/sat/*` (47 files: registration, the stand survey, `paint_export`, `pave_export`, `redboxes`, `check*`), `tools/drawing/*`, parts of `tools/buildings` | **none as geometry** (the sha3d rule). Use only for a visual sanity check, if the owner sends any. |
| **FAA NASR / AirNav / d-TPP / Chart Supplement / AL-375 diagram** | `geo_frame.py`, `imagery/common.py`, `build_sfo_airport.py`, `live/build_taxigraph.py` (runway ends), `env/build_lighting_spec.py`, `env/rwsl_graphic_fit.py`, `live/replay_datachar.py`, `xcheck/faa_al375_mask.py`, `buildings/build_spec_*.py`, `imagery/naip_faa_check.py`, `sat/faacheck.py`, `env/fetch_ephemeris_refs.py` (AirNav) | **CAAC eAIP** (https://www.eaipchina.cn/, a JavaScript single-page app; Playwright; the AIP needs a free login per geo.md) for AD 2 ZSSS (ARP, runways, thresholds, elevations, lighting, stands, charts); OurAirports and X-Plane only as secondary cross-checks |
| **FAA Releasable Aircraft Database / FAA ACD / US DOT BTS** | `models/build_brands.py`, `models/sfo_census.py`, `liveries/brands_meta.py`, `liveries/build_brands_js.py`, `models/faa_acd.py` (type dims; the ACD is a US database but lists foreign types [inf]) | Mictronics database (H, ODC-By) for registrations and types; COMAC / manufacturer documents for C919 and ARJ21 dims (fleet key); the airline brand map from the fleet key |
| **flysfo.com** (SFO AODB, no licence) | relay `Gates`, `live/gatecheck.py`, `replay_score.py`, `invariants.mjs`, `build_stream.py`, `stands/build_stands.py`, `stands/flysfo_provenance.py`, `stands/adsb_parked.py`, `buildings/*verify*`, `imagery/paint_pave_naip.py` | none known: shanghaiairport.com times out here and its terms are unknown (Q5) |
| **SFO Museum architecture data** (CDLA) | `build_sfo_airport.py`, `build_terminal_parts.py`, `blender/*`, `buildings/*`, `js/live/airport.js` / `terminals.js` data | OSM buildings (ODbL) + AIP; heights sourced or `inf` |
| **DataSF** gate numbers (PDDL) | `stands/build_stands.py` | AIP stand numbers / OSM `ref` |
| **USGS 3DEP** | `env/build_reservoirs.py` | Copernicus GLO-30 (terrain key) |
| **IEM ASOS archive / NOAA aviationweather.gov** | `env/ksfo_climatology.py`, `build_metar_golden.py`, `build_env_presets_js.py`, `env_spec_checks.py`, `live/replay_wx.py`, relay `Metar` | aviationweather.gov serves international stations [verify for ZSSS]; IEM's coverage of ZSSS [verify]; Ogimet as an alternative [verify terms] |
| **LiveATC** | `js/live/atc.js`, `docs/research/atc.md` | [verify] ZSSS feeds; probably none |
| Global (reusable) | `xcheck/fetch_xplane.py` + `parse_aptdat.py`, `convert_models.py` (FlightAirMap / FGMEMBERS), `liveries/*` painters, `live/record.py`, adsb.lol routeset / VRS standing data | as is, with ZSSS parameters |

---

## 7. Effort roll-up [inf]

| Package (hwd3d split, adapted) | Main modules | Effort |
|---|---|---|
| P0 frame and data foundation | `geo.js` + Python twin + test, `grid.js`, `site.js`; the eAIP extract; OSM pin via the API; Sentinel-2 registration; the `data/sha_airport` builder | L–XL (blocked by the eAIP login, Q2) |
| P1 relay, recording, pack, taxigraph | `sha_live_server.py`, record / stream / pack / shim, `build_taxigraph.py`, cache sync | L |
| P2 world and renderer (`live.html`) | `shaders/ground.js` ICAO markings, `world.js`, `terrain.js`, `airport.js`, `markings.js`, `signs.js`, env adaptations | XL |
| P2b three.js path (if Q1) | `js/three/ground.js` markings copy, `flood.js`, `objects.js`, `renderer3.js`, `buildings3d.js` | L–XL |
| P3 traffic, stands and bridges | `traffic.js` adaptation, the flow detector, `ground.js`, `gates.js` de-globalised + remote-stand GSE, `build_stands.py` fork, `lookup` / brands | XL |
| P4 app shell, UI, harness | `entry`, `app`, `ui`, `controls`, `about`, `atc`, `stats`, `livetest`, `jobs` | L |
| Fidelity phase | T1 / T2 / tower / hangars, lighting from AD 2.14, C919 / ARJ21 models, new liveries | XL each |

Compared with hwd3d, sha3d **keeps** about 4,700 lines of airliner systems (`gates.js` 2,091, `js/aircraft/*` 2,150,
`models.js` 442 [obs `wc -l`]) plus the stand and bridge logic inside `traffic.js`. Those lines save the work of rewriting the parking model, but de-SFO-ing
them costs more. Phase 2 of sha3d is therefore larger than hwd3d's, around 1.5–2.5 times its ~20 package-hours
[inf, rough].

---

## 8. Risks

1. **R1: no ADS-B coverage.** The sibling scan of adsb.lol globe_history found 0 traces within 150 km on 2026-11-10 and
   2026-11-12, and a few cruising traces on 2026-11-08.
   - The live, replay and snapshot path, stand learning (`adsb_parked`), the flow detector and every SFO-learned
     threshold all depend on data that may not exist.
   - Mitigations, which need the owner's decision (Q3):
     - other providers (OpenSky, with its terms checked);
     - a ZSSS recording kept running so that any data that exists accumulates;
     - showing an honest "no data" state rather than a look-alike.
2. **R2: no fine open imagery, and no geometry from Google, Baidu or Amap.**
   - What is lost:
     - stand nose and heading calibration;
     - jet-bridge positions (none in OSM);
     - paint positions and pavement edges;
     - sign and light-fixture positions.
   - The fallbacks are OSM and AIP charts, with `inf` labels. Fidelity in the markings will be standards-driven, not
     observed.
3. **R3: two copies of the FAA runway-marking geometry.** It exists in GLSL (`shaders/ground.js`) and in TSL
   (`js/three/ground.js`). If both paths are kept, they must share one ICAO/CAAC parameter table, or they will diverge.
4. **R4: module-scope SFO data in `gates.js`, `signs.js` and `traffic.js`.** `gates.js` imports `STANDS`,
   `BUILDINGS`, `AIRPORT` and `B3D_INTEGRATION`; `signs.js` imports `AIRPORT` and `DETAILS`; `traffic.js` imports
   `STANDS`. A fork that only swaps the imported file names hides coupling and breaks Node testing. Inject the data.
5. **R5: flysfo-dependent logic in `traffic.js` (92 lines).** With no plan source the code takes its fallback paths.
   Those paths were tuned with the plan available at SFO. The behaviour of silent docking and early bridge retraction
   without a plan needs its own tests.
6. **R6: degree / radian mixing** at the package boundaries (hwd R1). It is caught by a harness check: `disp.hdg`
   against the displacement bearing.
7. **R7: METAR trend groups** (§3.8) corrupting the current weather; plus ZSSS reporting habits (half-hourly, `MPS`)
   that are untested in the golden set.
8. **R8: the vertical datum.**
   - AIP elevation, Wusong height, the 1985 national datum, EGM2008 (DEM) and the WGS-84 ellipsoid (ADS-B `alt_geom`)
     differ by up to about 10 m around Shanghai [inf; terrain.md: Wusong = 1985 + 1.680 m].
   - A wrong `GEOID_M` makes landing aircraft float or sink.
9. **R9: the owner's privacy.** The sfo3d relay sends the owner's repository URL in its User-Agent to adsb.lol,
   adsb.fi, aviationweather.gov and flysfo. Do not copy it.
10. **R10: fonts and CDNs from mainland China.** `live.html` loads Google Fonts. Viewers in China may not reach it
    [inf]. This does not affect correctness, only typography.
11. **R11: licences.**
    - CAAC AIP reuse terms are unknown [verify].
    - X-Plane gateway data is GPL or unverified: cross-check only.
    - OurAirports' licence is unconfirmed (sibling SOURCES.json).
    - Livery trademarks for Chinese carriers are a fleet-key question.
12. **R12: renderer split.** Delaying live3 means losing GTAO, MSDF signs, floodlights and the Blender building path
    for a while. Doing live3 first doubles the de-SFO-ing work (Q1).

---

## 9. Questions for the owner

- **Q1 (renderer):** Should sha3d target the three.js page (`live3.html`, which sfo3d's relay opens by default) from
  the start, or the plain WebGL2 `live.html` first, as hwd3d did?
  - Does hwd3d's OD1 ("one quality level: full features, highest resolution") also apply to sha3d?
- **Q2 (eAIP access):** The CAAC eAIP needs a free registered login for the AIP itself (geo.md). May an agent use an
  account? If so, whose, and how are the credentials provided (not in chat)? Or will you download AD 2 ZSSS (text and
  charts) yourself?
  - Are the eAIP terms compatible with committing derived coordinates to this public repo?
- **Q3 (coverage):** If public ADS-B around ZSSS stays near zero, what should the app show?
  - (a) whatever few tracks exist, with an honest "no data" state;
  - (b) add OpenSky or other providers, subject to their terms;
  - (c) something else.
  - Do you know a ZSSS feed you would accept?
- **Q4 (ATC):** Is a LiveATC link-out wanted for ZSSS, if any feed exists? Otherwise drop the ATC toggle for sha3d.
- **Q5 (stand allocation):** sfo3d used SFO's own gate plan (flysfo). Is there an SHA source you want used, for
  example an official Hongqiao flight-information page, given its terms? Or should stands be matched by geometry only?
- **Q6 (language):** UI and labels in English only, or bilingual Chinese and English?
  - Should painted or sign text appear in Chinese where the real airfield uses it, once that is verified?
- **Q7 (imagery):** You set "Google, Baidu and Amap reference only, never geometry". So the jet bridges and paint at
  ZSSS cannot be surveyed as they were at SFO. Is standards-driven and inferred placement (clearly marked `inf`)
  acceptable? Or can you provide openly licensed high-resolution imagery or official apron charts?

---

## 10. Facts table

Every row was checked on 2026-11-13.

"Source" for code facts is the repository path at the stated commit; these are local, so no web URL.

Statuses:
- **verified**: the primary artefact was read.
- **secondary**: a sibling key's download or a secondary database.
- **unverified**: not checked.

| # | Topic | Value | Source | Date | Quote (verbatim, short) | Status |
|---|---|---|---|---|---|---|
| 1 | Fork base equals the current checkout | no sfo3d changes between e3218d6 and HEAD | `git diff --stat e3218d6 HEAD -- sfo3d` (empty) | 2026-11-13 | (empty output) | verified |
| 2 | sfo3d relay default page | `/` → `live3.html` | `git:e3218d6:sfo3d/sfo_live_server.py#L1714` | 2026-11-13 | `self.send_header('Location', 'live3.html' + ...` | verified |
| 3 | live3 = same app, four modules swapped | import map swaps `gl`, `renderer`, `scene`, `world/world` | `git:e3218d6:sfo3d/docs/research/engine_impl.md` §2 | 2026-11-13 | "`live3.html`'s import map swaps four renderer-facing modules" | verified |
| 4 | hwd3d forked the `live.html` path | `live.html` + custom WebGL2; `js/three/**` not forked | `git:origin/claude/hwd-live-3d:hwd3d/docs/phase2_fork_map.md` §0 | 2026-11-13 | "hwd3d forks the **`live.html` path**" | verified |
| 5 | hwd3d owner decision OD1 | one quality level, full features | `git:origin/claude/hwd-live-3d:hwd3d/CLAUDE.md` | 2026-11-13 | "One quality level: the full-feature, highest-resolution, complex-shading version" | verified (for hwd3d; whether it applies to sha3d is unverified) |
| 6 | SFO ARP in the frame | 37.6188056, −122.3754167 | `git:e3218d6:sfo3d/js/geo.js#L17` | 2026-11-13 | `export const ARP = { lat: 37.6188056, lon: -122.3754167 };` | verified |
| 7 | Constant ground height | `GROUND_Y = 3.0`; 111 uses in the live / world / env / anim path, 35 in `js/three` | `git:e3218d6:sfo3d/js/geo.js#L83`; grep counts | 2026-11-13 | `export const GROUND_Y = 3.0; // nominal airfield elevation (m) above bay datum` | verified |
| 8 | SFO geoid constant | `GEOID_M = 32.29` | `git:e3218d6:sfo3d/js/live/traffic.js#L31` | 2026-11-13 | `const GEOID_M = 32.29;          // EGM96 undulation at the ARP is -32.29 m` | verified |
| 9 | SFO airport box in the traffic engine | x −2,700 … 1,950, z −2,350 … 1,800 | `git:e3218d6:sfo3d/js/live/traffic.js#L276` | 2026-11-13 | `export const inAirport = (x, z) => x > -2700 && x < 1950 && z > -2350 && z < 1800;` | verified |
| 10 | SFO runway headings in env | 297.83 / 117.83 / 207.83 / 27.83 | `git:e3218d6:sfo3d/js/env/state.js#L47` | 2026-11-13 | `const RWY_HDG = { '28': 297.83, '10': 117.83, '19': 207.83, '1': 27.83 };` | verified |
| 11 | Time zone hard-coded | `America/Los_Angeles` | `git:e3218d6:sfo3d/js/env/clock.js#L18` (+ `ui.js`, `stats.js`) | 2026-11-13 | `export const TZ = 'America/Los_Angeles';` | verified |
| 12 | FAA threshold stripes in the shader | 16 stripes, 5.75 ft, for a 200 ft runway | `git:e3218d6:sfo3d/js/shaders/ground.js#L80-81` | 2026-11-13 | "threshold markings (AC 150/5340-1M 2.5.5): 16 stripes for a 200 ft runway" | verified |
| 13 | FAA aiming point in the shader | 1,020 ft from the threshold | `git:e3218d6:sfo3d/js/shaders/ground.js#L94` | 2026-11-13 | "aiming point (2.6): begins 1,020 ft from the threshold, 150 ft long, 30 ft wide" | verified |
| 14 | Marking logic duplicated in three.js | the same FAA stripes, aiming point and TDZ table | `git:e3218d6:sfo3d/js/three/ground.js#L350-364` | 2026-11-13 | "threshold stripes (AC 150/5340-1M 2.5.5): 16 x 5.75 ft, double centre gap" | verified |
| 15 | Decal markings built to FAA dims | header statement | `git:e3218d6:sfo3d/js/live/markings.js#L1` | 2026-11-13 | "built to FAA AC 150/5340-1 dimensions" | verified |
| 16 | `gates.js` loads SFO data at module scope | `STANDS`, `BUILDINGS`, `AIRPORT`, `B3D_INTEGRATION` | `git:e3218d6:sfo3d/js/live/gates.js#L88-91` | 2026-11-13 | `import { STANDS } from '../../data/sfo_stands.js';` | verified |
| 17 | sfo3d stand set | 108 stands, src obs 66 / inf 42 | `git:e3218d6:sfo3d/data/sfo_stands.json` | 2026-11-13 | (counted with `python3 -I`) | verified |
| 18 | Airliner models available | 23 keys (a319 … md11), no C919 / ARJ21 | `git:e3218d6:sfo3d/js/live/entry.js#L13`; `js/aircraft/types.js#L401-410` | 2026-11-13 | `const MODEL_KEYS = ['a319', 'a320', ... 'md11'];` | verified |
| 19 | Chinese carriers in the name table | CES, CSH, CQH, DKH, CCA, CSN … present | `git:e3218d6:sfo3d/data/lookup.js` | 2026-11-13 | `"CES":"China Eastern Airlines\|MU"`, `"CSH":"Shanghai Airlines\|FM"` | verified |
| 20 | Livery set | 57 brand folders incl. CES, CCA, CSN; no CSH / CQH / DKH | `git:e3218d6:sfo3d/data/liveries/` | 2026-11-13 | (directory listing) | verified |
| 21 | METAR decoder handles MPS / CAVOK / Q | yes | `git:e3218d6:sfo3d/js/env/wx/metar.js#L128-168` | 2026-11-13 | `(KT\|MPS\|KMH)$/` … `if (t === 'CAVOK')` … `/^Q(\d{4})$/` | verified |
| 22 | METAR decoder does not strip trend groups | `decodeMetar` passes all tokens before RMK to `parseBody` | `git:e3218d6:sfo3d/js/env/wx/metar.js#L360-381` | 2026-11-13 | `parseBody(toks.slice(i), out);` (no NOSIG / BECMG / TEMPO split) | verified (code); the effect on ZSSS reports is inferred |
| 23 | Routine minute default 56 | KSFO :56 | `git:e3218d6:sfo3d/js/env/wx/metar.js#L490` | 2026-11-13 | `export function renderParams(d, night = false, marineLayerDepthFt = null, routineMinute = 56)` | verified |
| 24 | Relay User-Agent includes the owner's repository URL | `CONTACT` → `UA` | `git:e3218d6:sfo3d/sfo_live_server.py#L56-57` | 2026-11-13 | `UA = f'sfo-live-3d-relay/{VERSION} (+{CONTACT}; personal non-commercial visualisation)'` | verified |
| 25 | hwd3d relay uses a generic UA | no names, no repository URL | `git:origin/claude/hwd-live-3d:hwd3d/hwd_live_server.py#L98-99` | 2026-11-13 | "a generic, honest User-Agent ... no names, no repository URL" | verified |
| 26 | Mock relay uses SFO latitude | `cos(37.6188)` | `git:e3218d6:sfo3d/livetest.mjs#L28` | 2026-11-13 | `a.lon += d * Math.sin(tr) / (111320 * Math.cos(37.6188 * Math.PI / 180));` | verified |
| 27 | sfo3d snapshot licence conflict | `data/snapshot.js` contains adsb.fi data (OD-11: kept) | `git:e3218d6:sfo3d/docs/ATTRIBUTION.md#L61` | 2026-11-13 | "LICENCE CONFLICT - owner's decision (2026-11-08, OD-11): keep the file as is." | verified |
| 28 | flysfo plan logic in the engine | 92 lines of `traffic.js` match the plan / flysfo / off-block / in-block / AODB terms | grep on `git:e3218d6:sfo3d/js/live/traffic.js` | 2026-11-13 | (count) | verified |
| 29 | Changes since the hwd3d base are airliner-side | `models.js` +148 (gear), `aircraft_real`, `three/aircraft`, `lookup`, `aircraft`, `terrain` | `git diff --stat a967f9b e3218d6 -- sfo3d` | 2026-11-13 | `sfo3d/js/live/models.js \| 148 ++++-` | verified |
| 30 | hwd3d Phase 2 build time (effort calibration) | 0b0a4bb 11:13Z → bd6cb30 16:28Z, 2026-11-13; 81 files, +8,910 lines in the last checkpoint | `git log origin/claude/hwd-live-3d` | 2026-11-13 | "hwd3d Phase 2: WIP checkpoint (relay, world, traffic engine, app shell, run renders; review in progress)" | verified (git); its use as an effort scale is inferred |
| 31 | Hypothesis: OurAirports ZSSS ARP | 31.198104 N, 121.33426 E, elevation 10 ft: **matches the hypothesis** | https://davidmegginson.github.io/ourairports-data/airports.csv (sibling cache `refs/cache/ourairports_runways/airports.csv`, fetched 2026-11-13T19:24Z) | 2026-11-13 | `"ZSSS","large_airport","Shanghai Hongqiao International Airport",31.198104,121.33426,10` | secondary |
| 32 | OurAirports ZSSS runways | 18L/36R 11,154 × 148 ft ASP, headings 176 / 356 °T; 18R/36L 10,826 × 197 ft CON, 176 / 356 °T, ends given only to 0.001° | https://davidmegginson.github.io/ourairports-data/runways.csv (sibling cache) | 2026-11-13 | `"18L",31.213199615478516,121.33499908447266,7,176,,"36R",...,356` | secondary |
| 33 | ADS-B near ZSSS (adsb.lol archive) | 0 traces within 150 km on 2026-11-10 and 2026-11-12 | sibling `refs/cache/adsb/zsss_2026.11.1{0,2}_prod.json.gz`, from https://github.com/adsblol/globe_history_2026/releases | 2026-11-13 | `"r_km": 150.0, "n_traces_scanned": 75360, "traces": []` | secondary (sibling key's measurement) |
| 34 | OSM at ZSSS has no jet bridges and no runway / taxiway surface polygons | as stated | sibling `docs/phase0/geo.md` (OSM API) | 2026-11-13 | "Missing: no jet bridges, no navaids, and no runway or taxiway surface polygons." | secondary |
| 35 | CAAC aerodrome standard designation | believed to be MH 5001-2021 | not read | 2026-11-13 | — | unverified |
| 36 | ICAO vs FAA marking differences in §4 | as listed | not read (from memory) | 2026-11-13 | — | unverified |

**Contradictions with the working hypothesis:** none found. OurAirports' ARP matches it exactly (row 31). That is
secondary agreement only; the ARP still needs the eAIP AD 2.2.

**Observed vs inferred in this note:**
- Observed: everything in §1, the code citations in §3–6 and the facts rows 1–30.
- Inferred: the recommended architecture (§2), the verdicts, the efforts and risks R10–R12.
- Unverified: §4 in full.
