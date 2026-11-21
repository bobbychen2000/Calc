# SHA Live 3D (Shanghai Hongqiao, ZSSS) - project notes for Claude Code

A 3-D simulation of Shanghai Hongqiao International Airport (ZSSS / SHA), forked from `sfo3d/` (SFO Live 3D) at commit
**e3218d6**. Plain ES modules and a custom WebGL2 renderer (the `live.html` path; no framework, no bundler), offline
Python data tools, a stdlib Python relay, and a Playwright test harness.

Read first: `docs/PLAN.md` (§4 architecture, **§6a owner decisions OD0-OD4, binding**, §6b working defaults, §7 phases),
`docs/phase0/arch.md` (reuse map, what must not leak from sfo3d), and the phase reports in `docs/phase1/` and
`docs/phase2/` (`core.md`, `markings.md`, `gates.md`, `buildings.md`, `relay_ui.md`, `integration.md`).

**Status (2026-11-20): Phase 2 done** - a static, sun-lit, weather-aware ZSSS scene: airfield pavement with CAAC
MH 5001-2021 markings and signs, 164 stands with 56 jet bridges, VDGS and stand signs, parametric T1 / T2 / tower /
hangars, the surroundings of the 23.5 km² extent plus a low-detail far ground, the relay (ZSSS METAR / TAF), snapshot and
live modes, the phone / laptop UI with the Observed / Inferred legend and the About panel. **There is no traffic yet**
(Phase 3: a schedule-driven simulator, every aircraft labelled inferred - open ADS-B sees nothing at Hongqiao, PLAN §3).

**Phase 2 fix round 1 (2026-11-21)** answered `docs/phase2/review_visual.md` (each package report has a "Fix round 1"
section; `integration.md` the integration). Conventions that changed are listed under "Conventions" below.

## Rules (owner decisions and working defaults; non-negotiable unless the owner says otherwise)

- **Do not modify `sfo3d/`, `pc12/` or `hwd3d/`.** Copy what you need into `sha3d/`; every copied file starts with
  `forked from sfo3d@e3218d6 <path>`. Things sfo3d should change go to `docs/requests_to_sfo3d.md`.
- **Sub-agents do not `git commit` / `push`**; the lead does. Commit only redistributable content (see "Committing").
- **Observed vs inferred stays visible**: data `src` fields (`obs` / `inf`, plus "AIP (mirror)"), item tags, the legend,
  labels, cards, About. Never unlabelled synthetic traffic; only `adsb_icao` records count as observed.
- **No FAA marking / sign / lighting constants in sha3d code paths.** Use CAAC MH 5001-2021 values with their clause
  numbers (`docs/phase1/standards_refs.md`, `js/live/caac_markings.js` is the ONE parameter table) or a clearly marked
  `inf` placeholder. Remaining US-origin values (photocell thresholds in `js/env/state.js`, bridge slope limits in
  `js/live/gate_system.js`) are labelled `inf placeholder`; aircraft-side rules (lights, METAR coding) are not airfield.
- **No SFO values may leak**: SFO ARP, headings 117.83 / 27.83, `GROUND_Y 3`, `GEOID_M 32.29`, flysfo plan logic, SFO
  data imported at module scope (inject `window.SHA_*` instead), degree / radian mixing.
- **Feeds**: never call OpenSky. adsb.lol at most one request per 180 s (keyless quota 500/day; the local recorder may
  share the IP) - the relay's `--adsb` is OFF by default, its floor cannot be lowered, and it keeps a persisted 24 h cap.
  aviationweather.gov at most one METAR and one TAF request per 10 min (relay cache). Relay and tool User-Agents are
  generic (`sha-live-3d-relay/0.1 (personal non-commercial visualisation; python-stdlib)`): no names, e-mail or URLs.
  The browser never talks to a provider; the relay is OFF unless `?relay=1` (its `/` redirect adds it).
- **Personal use only (OD4)**, but the repo is public: real flight identities "observed elsewhere" are read at run time
  from the gitignored `refs/cache/observed_elsewhere/` and are **never committed**. No history rewrite.
- **Legal posture (PLAN §6b Q3)**: detail only inside the 23.5 km² extent (convex hull of the aerodrome + 1 km); beyond
  it only 50 m land-cover fractions. Sensitive OSM features (military, armed police, police, prison, GNSS stations) are
  filtered and never drawn or labelled. No Google / Baidu / Amap imagery. AIP values come from an unofficial mirror
  (OD3): short cited facts labelled "AIP (mirror)" only, never whole lists. No ATC audio (Q4). English UI (Q8).
- **Aircraft models** are sfo3d's `.sfom` files loaded **by URL** from `../sfo3d/data/models/` (`window.SHA_MODEL_BASE`
  overrides); do not copy them yet. C919 / C909 come in Phase 4.
- **The UI must work on a phone (portrait, touch) and a laptop.** Check both with the harness.
- **Look at your renders yourself** (deviceScaleFactor 1 for checks).

## Run

```bash
python3 sha_live_server.py [--port 8000]          # from sha3d/: relay + static files -> http://localhost:8000/ (live mode)
python3 sha_live_server.py --no-metar             # offline (never contacts aviationweather.gov)
python3 sha_live_server.py --adsb                 # also relay adsb.lol (>= 180 s between requests, daily cap 200)
python3 -m http.server 8000                       # from the REPOSITORY ROOT (so ../sfo3d/data/models/ resolves):
                                                  #   http://localhost:8000/sha3d/live.html  -> snapshot mode
```

URL options (`live.html?...`): `mode=auto|live|snapshot` (auto = live when a relay answers, else snapshot),
`relay=1`, `t=<ISO>` (environment time), `quality=low|medium|high|ultra`, `fixedres=1` (no dynamic resolution),
`metar=<raw>` / `wx=<id>`, `legend=1|0`, `park=<stand>[:<ICAO>],...|contact|remote|all` (**DEBUG** static aircraft,
bridges dock; the panel says "DEBUG ?park=: n static aircraft (not traffic)"), `debug=push` (lead-in / push-back overlay),
`bld=0` (core placeholder buildings), `far=0` (neutral ground beyond the extent), `qa=env` (environment HUD).

## Harness and checks

`livetest.mjs` serves the repository root, opens `/sha3d/live.html` in headless Chromium (`require('playwright')`) and
runs a job script `export default async ({page, shot, base, W, H, OUT}) => {}`. This sandbox has no GPU: always
`SOFTGL=1` (Mesa llvmpipe via ANGLE/EGL; about 1-1.5 s per frame at 1280 × 720, so allow minutes per run).

```bash
# env: SOFTGL=1 | SWS=1; W, H, DPR (default 1); MOBILE=1 (iPhone UA + touch) or DEVICE='iPhone 15'; OUT, PREFIX;
#      MOCK_RELAY=1 [MOCK_ADSB=1] (ping / METAR / TAF mock) or RELAY=http://127.0.0.1:8792 (proxy /api/* to a real relay)
SOFTGL=1 OUT=docs/phase2 PREFIX=view T=snapshot VIEWS=@full node livetest.mjs jobs/views.mjs     # the named view set
SOFTGL=1 VIEWS='overview;rwy:18L;t2;stand:233,A320;hold:H1' node livetest.mjs jobs/views.mjs
SOFTGL=1 RELAY=http://127.0.0.1:8792 SCENES=snapshot,live,offline,park,standalone node livetest.mjs jobs/integration.mjs
SOFTGL=1 SCENES=perf TIERS=low,high node livetest.mjs jobs/integration.mjs                       # frame time per tier
SOFTGL=1 DEVICE='iPhone 15' OUT=docs/phase2 PREFIX=ui_phone node livetest.mjs jobs/ui.mjs        # UI shell
```

`jobs/views.mjs` view kinds: `overview | top | runways | t1 | t2` (app views), `rwy:<end>` (behind the landing
threshold), `tower` (orbit), `towercab` (the app's cab view), `stand:<name>[,<ICAO>|-][,dist,side,pitch]`,
`bridge:<stand>`, `hold:<taxiway ref>`, `look:x,y,z,yaw,pitch,dist[,fov]`, `park:<stand>[:<ICAO>]+...` / `unpark`,
`ui:legend|card:<stand>|fly:<stand>|nocard|about|close` (with `SHOWUI=1`), `<view>@<name>` (file name). `T=snapshot` keeps the app's
snapshot instant; otherwise `T` defaults to 2026-11-14T03:00Z (11:00 local, clear default sky).
Package jobs: `jobs/markings.mjs` (`end: endtop: hold: sign: plate: thr:`; `thr:<end>` = the app's threshold view, as
`views.mjs rwy:<end>`), `jobs/gates.mjs` (`SET='fix1;fix1night'`: stop convention, masts, idle stairs), `jobs/buildings.mjs`
(photo-match views; `FILLCHECK=1` counts fixed-link points, rotundas and VDGS posts on pavement), `jobs/ui.mjs`
(`SCENES=snapshot,offline,live`; also checks that the card leaves the credit strip free and the strip's contrast).

Tests (no browser):
```bash
node tools/common/test_geo_js.mjs           # js/geo.js vs tools/common/frame.py and the data (mm)
python3 -I tools/live/test_relay.py         # relay against a local mock: limits, allow-list, UA (7 tests)
node tools/wx/test_metar_zsss_js.mjs        # ZSSS METAR decoder vs the Python reference (archive part needs refs/cache)
node tools/buildings/test_buildings3d.mjs   # building geometry checks
python3 -I tools/common/test_frame.py       # the frame (Python)
```

In the page, `window.SHA` = `{R, scene, rig, ui, world, view, applyEnv, qa, env(), envCore, geo, data, extensions,
cfg, mode, hooks, quality, runwayMode(), setRunwayRule(), observed, markings}`; readiness `window.__shaReady` /
`__shaError`; storage prefix `shalive.`. `SHA.qa`: `hideUI, look, view, threshold, stand, tower, placeModel` (QA only),
`clearModels, info`; gates: `park, unpark, unparkAll, parked, gates, gate, bridgeView`; shell: `selectStand, closeCard,
openAbout, openSettings, openLegend, sheet, search, standLabels, runway, mode`; gates (fix round 1): `masts()` (73 inferred
apron floodlight masts), `idleStairs()` (staged idle stair cues); `SHA.markings.holds() / signs() / info() / apron() / plan()`
(`apron()`: equipment areas, stand envelopes, bridge areas as world rings, src inf).

## Architecture

**Frame** (`js/geo.js` = `tools/common/frame.py`, frame id `ltp-wgs84-zsss`): x = east, z = south, y = up, metres;
origin = centre of RWY 18L/36R from the OSM runway ends, 31.19784885 N 121.3362899 E (OD0); WGS 84 local tangent plane.
`GROUND_Y` 2.5 m nominal (flat ground, inf); AD ELEV 3.0 m; EGM2008 plane fit for heights. Headings are **degrees true**
everywhere: `hdgVec(h) = [sin h, -cos h]`. Runways 18L/36R 177.34°, 18R/36L 177.33° (close parallels 365 m apart).

**Boot**: `live.html` loads the data scripts (window globals) -> `js/live/entry.js` (mode, relay detection, snapshot,
model URLs) -> `js/live/app.js` `startApp` (quality tier, renderer, `buildLiveWorld`, environment, camera, UI, loop,
`window.SHA`) -> each extension's `start(app)`.

**Extensions** (`js/live/ext.js`): each package owns one file and calls `registerExtension({name, order, shaderChunks,
groundUniforms, pavement, claimBuildings, buildWorld, start, frame, lights})`; `entry.js` imports them.

| File | Package | Role |
|---|---|---|
| `js/live/markings.js` (+ `caac_markings.js` table, `caac_decals.js`, `caac_signs.js`) | P2b | CAAC runway paint in the ground shader (`sha_ground_paint` chunk), taxiway / hold / stand decals, sign assemblies |
| `js/live/gates.js` (+ `gate_system.js` engine, `gate_signs.js`, `js/world/gates.js` GSE) | P2c | stands -> gate objects, apron-drive jet bridges, VDGS, CAAC stand-number signs, remote-stand stairs / buses, DEBUG park, push overlay |
| `js/live/terminals.js` (+ `js/world/buildings3d.js`) | P2d | T1 / T2 parts, east tower (`anchors.tower` with `eyeY`, `cabHalf`), hangars, hub, context LOD blocks, far ground (`sha_ground_far` chunk) |
| `js/live/shell.js` (order 90) | P2e | status pill / clock by mode, METAR + inferred runway lines, legend, stand labels / card / search, TAF and ADS-B polls, About tail |

Core: `js/live/world.js` (ground + placeholders + extensions), `js/world/ground.js` (1 m airfield map, 4 m context map,
Sentinel-2 hint, `pavedAt`), `js/shaders/ground.js` (paint and far-ground hooks), `js/world/placeholders.js`,
`js/live/ui.js` (phone bottom sheet / laptop side panel; `setNote` + keyed `setNoteLine`, legend lines, stand labels),
`js/live/about.js`, `js/live/relay.js` (client), `js/env/*` (sun / moon, METAR / TAF, `wx/metar_zsss.js` decoder in report
units + runway rule), `js/aircraft/*` + `js/live/models.js` (sfo3d's model pipeline), `js/live/traffic_api.js` (Phase 3
stub; the traffic engine removes `body.no-traffic`). Relay: `sha_live_server.py` (`/api/ping`, `/api/metar`, `/api/taf`,
`/api/adsb`, `/api/status`; static allow-list: `sha3d/live.html`, `live.css`, `js/**`, `data/**`, sfo3d models and
liveries; never `refs/`, `tools/`, `docs/`, `out/`, `jobs/`).

## Conventions (since Phase 2 fix round 1)

- **Stand stop node = nose-wheel stop** (MH 5001-2021 6.2.16-7; OSM `aeroway=parking_position`). A type parks with its
  nose-gear contact on `stands[].nose` and its nose tip `noseGearX(T)` ahead (`js/live/gate_system.js` `noseGearX(T)`,
  `standTip(stand, T)`; Phase 3 traffic: `setOccupant(g, key, ..., {nose: standTip(g, T), dir})`). `sha_stands.json`
  `class_ref.<cls>.nose_gear_m` (+ `nose_gear_src`) per reference type; the bridges' `cab` points are door 1 of the class
  reference parked that way. The painted envelopes, safety lines, hatching and equipment areas (`caac_decals.js`) are
  shifted forward by `nose_gear_m`; the stop line, lead-in and alignment line stay at the node.
- **Ground shader hooks** (`js/shaders/ground.js`): the paint hook is `shaGroundPaint(wp, fw, dxy, apt, paved, rough)`
  (`dxy` = dFdx / dFdy of `wp.xz`, for directional footprints); chunk `sha_apron_flood` (`shaApronFlood`, level
  `APRON_FLOOD` 0.42 × albedo, warm, inf) lights the apron and the decals at night. Airfield lighting (runway / taxiway
  lights, stop bars) is **not modelled** (Phase 5); the legend and About say so.
- **`aip_facts.blast_pad_m`** = [length, width] of the pad at both ends (AD 2.12), not one value per end.
- `caac_markings.js` also carries table 4.9.5 (`separation.twyCLToObject` / `taxilaneCLToObject`, used for the masts).
- Pavement added by packages through the `pavement(api)` hook is in the airfield map: the T1 / T2 **airside fill**
  (`sha_buildings3d.json` `airside_fill`, src inf: OSM apron gap, paved in S2 / photo 09) draws as asphalt.
- The UI clock and pill say **UTC+8** (Beijing time), not "CST". The tower view (`app.js`) faces the 18L/36R midpoint
  (`anchors.tower.cabYaw`). The far haze follows the METAR surface extinction (L = clamp(0.8 / σ, 1.2, 20 km)), and the
  Sentinel-2 hint is cross-faded into the far ground over the inner 60-480 m of the extent (`terminals.js featherS2`).

## Data (`data/`, generated - do not hand-edit)

| File | Global | Contents | Made by |
|---|---|---|---|
| `sha_airport.js/.json` | `SHA_AIRPORT` | frame block, runways (+ `aip_facts`), taxiways, taxilanes, aprons, holds, surfaces, buildings, context (OSM, ODbL) | `tools/airport/build_airport.py` |
| `sha_stands.js/.json` | `SHA_STANDS` | 164 stands (sfo3d schema: name, nose, hdg, cls, src, bridges[], remote[], span_max, push) | `tools/airport/build_stands.py` |
| `sha_taxigraph.js/.json` | `SHA_TAXIGRAPH` | taxi graph | `tools/airport/build_taxigraph.py` |
| `sha_ground_s2.js` | `SHA_GROUND_S2` | Sentinel-2 L2A ground-colour hint, 10 m, inside the extent | `tools/terrain/s2_ground_hint.py` |
| `sha_buildings3d.js/.json` | `SHA_BUILDINGS3D` | building parts, towers, hangars, claims | `tools/buildings/build_buildings3d.py` |
| `sha_landcover_far.js` | `SHA_LANDCOVER_FAR` | ESA WorldCover 2021 at 50 m beyond the extent (CC BY 4.0) | `tools/terrain/worldcover_far.py` |
| `sha_snapshot.js/.json` | `SHA_SNAPSHOT` | snapshot instant 2026-11-20 04:15Z, 11 METARs + TAF, empty traffic set | `tools/live/build_snapshot.py` |
| `meas/*.json` | - | measurements (runway ends, taxiway refit, SAR / S2 stand evidence, building heights) | `tools/airport/*`, B3 |
| `models/manifest.js`, `dock_foot.js`, `liveries/manifest.js`, `lookup.js`, `brands.js` | - | copied sfo3d metadata (`.sfom` and textures stay in sfo3d) | sfo3d |

Sources and licences: `data/SOURCES_*.json`, `docs/phase1/SOURCES_*.json`. Third-party downloads live in the gitignored
`refs/cache/` (local only unless redistributable and staged with `git add -f` next to a `SOURCES.json`).

## Committing

Safe to commit: `live.html`, `live.css`, `js/**`, `data/**` (generated, licensed as their headers say), `jobs/**`,
`livetest.mjs`, `sha_live_server.py`, `tools/**` except `tools/geo/gcj02.py` (gitignored, local until the owner
decides), `docs/**` (reports and renders), `CLAUDE.md`, `.gitignore`. Never: `out/` (harness output, relay state),
`refs/cache/**` unless its `SOURCES.json` marks it redistributable, anything with per-flight observed-elsewhere data,
AIP lists, COMAC ACAP figures, Google / Baidu imagery. The latest list with reasons is in `docs/phase2/integration.md`.
