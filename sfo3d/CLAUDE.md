# SFO Live 3D — project instructions for Claude Code

A real-time, interactive 3D simulation of San Francisco International Airport (KSFO) driven by live ADS-B traffic.
Plain ES modules + a custom WebGL2 renderer (no framework, no bundler yet), plus offline Python data tools.
Detailed history, decisions, verification status and the task list are in `docs/HANDOFF.md`. Read it before working.

## Final-state objective (the user's definition of done)

In the user's words, this should be "a physical engine laid on top of real data with perfect real world simulations",
with quality that "surprises me and surpasses anything I could see on the market now". Concretely:

1. **Live traffic.** It runs continuously and reflects real traffic in real time, using live ADS-B data for flights into and out of SFO. Every arrival, departure, taxiing and parked aircraft is at its real position, and motion is smooth and physically plausible.
2. **Identity.** Each aircraft shows its tail number (registration), airline and aircraft type, and can be selected. The callsign and route are shown where known.
3. **Parking.** It shows where aircraft are parked: at the real gate or stand, with the gate number. Jet bridges dock to the aircraft door. Gate-number markers appear on the bridges and stands, as at the real SFO.
4. **Aircraft detail.** Real artist models, with convincing cockpit windows, liveries, lights, gear and shadows.
5. **Airport fidelity, with the same meticulous care as the aircraft.** This covers:
   - runways, taxiways and aprons, with FAA markings, signs and lighting;
   - terminals, the control tower, jet bridges and ramp equipment.

   The layout is confirmed against satellite imagery (the user's Google Maps screenshots). Add "significantly more detail to each component".
6. **Physical plausibility everywhere.** Objects never collide, clip or morph into each other. Aircraft stand only on pavement, never on grass or sand. Bridges and stands are spaced as in reality ("no way planes are parking that close"). Aircraft are solid bodies.
7. **ATC audio toggle** for SFO Ground, Tower and Approach frequencies (via LiveATC).
8. **QA and delivery.** Every component gets visual QA over several passes, using an adversarial-review pattern: an independent reviewer looks only at renders and reference images. The deliverables are:
   - (a) a standalone app the user can run, with a small local relay for live data;
   - (b) an in-Claude artifact version in snapshot mode (the artifact CSP blocks external fetches).

   Both must be mobile-friendly. The user mostly uses a phone.

## Working rules (from the user — non-negotiable)

- **Never make unverified key assumptions.** Verify critical content (coordinates, dimensions, frequencies, licences, API terms, stand positions) against the original source. If you can't get the original, ask the user for it. Don't ship a look-alike with a disclaimer.
- Keep a clear **observed vs inferred** distinction in data. For example, stands carry `src: 'obs' | 'inf'`.
- Treat the Google Maps screenshots as **reference only**: measure from them, but never use them as textures. The imagery is licensed. If the user wants satellite textures, discuss licensing first.
- Visual QA loop for every change:
  1. Render named views with the harness (below).
  2. Look at the PNGs yourself.
  3. For significant work, run an adversarial reviewer subagent on the renders and `docs/qa/ref/*`, then fix what it finds.

## Run

```bash
python3 -m http.server 8000     # from the repo root; ES modules need http://
# recorded snapshot (always works):  http://localhost:8000/live.html?mode=snapshot
# live mode: needs the local relay (/api/adsb, /api/routeset, /api/metar, /api/ping), not written yet (docs/HANDOFF.md, P2)
```

Test harness: `livetest.mjs` runs a static server, a mock ADS-B relay built from the snapshot, headless Chromium and screenshots.

```bash
npm i -D playwright && npx playwright install chromium
PREFIX=qa VIEWS="view:overview;tower;gate:B26,60,1,14;hold:12;look:1453,3,760,298,24,150" node livetest.mjs jobs/qa3.mjs
# -> out/live/qa_*.png ; also logs stand occupancy + ground-physics stats
# views: gate:<stand>,<dist>,<side>,<pitch> | hold:<i> | tower | ac:<hex>,<dist> | view:overview | look:x,y,z,yaw,pitch,dist
# GPU: default = Chromium's choice; SOFTGL=1 = Mesa llvmpipe (Linux, no GPU); SWS=1 = SwiftShader
```

In the page, `window.SFO` exposes these debug hooks:
- `R`, `scene`, `traffic`, `physics`, `world` and `gateSys`;
- `qa.look/gate/hold/tower/aircraft`.

## Architecture (key files)

**Coordinates.**
- World: x = east, z = south, y = up, in metres. The origin is the ARP; the ground is at `GROUND_Y = 3`.
- Airport grid (s, t): s runs along heading 117.83° (10→28) and t along 27.83° (1→19). Convert with `stToWorld` / `worldToST` in `js/geo.js`.
- Headings: `hdgVec(h) = [sin h, −cos h]`.

**Live app (`js/live/`).**

| File | Role |
|---|---|
| `entry.js` | Picks the mode, model sources and relay, then calls `startApp`. |
| `app.js` | Main loop: quality tiers, environment (sun/METAR/night), feeds, camera views, UI glue, QA hooks. |
| `traffic.js` | ADS-B tracks: Hermite interpolation plus dead reckoning, flight-phase classification, stand matching/snapping, heading inference, parked persistence. |
| `ground.js` | `GroundPhysics`: aircraft as solid planforms. Stationary off-stand aircraft move to the nearest pose that is on pavement, clear of buildings and not overlapping other aircraft. Taxiing overlaps are nudged apart. |
| `gates.js` | `LiveGateSystem`: apron-drive jet bridges (fixed walkway, rotunda, 3 tunnels, cab, bellows, stair, signs) docking to real door positions; stand sign and VDGS; collision-checked GSE. |
| `airport.js` | Stand model (`standGates`), pavement/concrete/wear/paint map, runway end zones (blast pads, EMAS), buildings. |
| `world.js` | Assembles terrain, water, ground bake inputs, markings, signs, masts, EMAS geometry and buildings. |
| `markings.js` | Anti-aliased decal ribbons: centerlines, hold bars, enhanced centerline, edges, stand lead-ins, stop bars, red boxes. |
| `signs.js` | Signs. |
| `terminals.js` | Terminals, tower and ITB hall. |
| `models.js` | `.sfom` model loader; light anchors come from the real geometry. |
| `aircraft.js` | Type→model mapping and LOD. |
| `ui.js` | User interface. |
| `feed.js` | adsb.lol / adsb.fi `jv2` feeds, routes, METAR. |

**Shaders (`js/shaders/`).**
- `ground.js`:
  - runway markings (SDF glyphs, thresholds, displaced-threshold arrows, blast-pad chevrons);
  - airfield bakes, including the green paint.
- `objects.js`: object materials.
- `aircraft_real.js`: imported models.
- `post.js`: ACES tone mapping.

**Data (`data/`, generated — don't hand-edit).**

| File | Contents | Made by |
|---|---|---|
| `sfo_airport.js` | SFO Museum geometry | `tools/build_sfo_airport.py` |
| `sfo_details.js` | Centerlines, holds, apron, masts | `tools/build_airfield_details.py` |
| `sfo_buildings.js` | Building parts | `tools/build_terminal_parts.py` |
| `sfo_stands.js` | 89 surveyed contact stands, 117 bridges, red boxes | `tools/sat/export_stands.py` |
| `sfo_paint.js` | Green no-taxi paint | `tools/sat/paint_export.py` |
| `sfo_pavement.js` | Extra paved areas | `tools/sat/pave_export.py` |
| `models/*.sfom` | Aircraft models | `tools/convert_models.py` |
| `snapshot.js` | Recorded ADS-B snapshot, 23 Sep 2026 10:51 PDT | — |

The satellite pipeline lives in `tools/sat/`. The screenshots go in `tools/sat/screens/` (shipped separately as `sfo3d-satellite-screens.zip`); registrations are in `tools/sat/work/reg.json`.

## Conventions

- Keep files self-describing: a header comment stating the purpose, plus the source of every constant (FAA AC paragraph, AirNav, imagery measurement, etc.).
- Items passed to the renderer look like `{mesh, prog, model, uniforms, bbox, castShadow, noCull, blend, bothPasses, sortKey, polyOffset, nearOnly, shadowMaxCascade}`.
- After changing geometry or data, re-run the QA harness and check the stand and bridge checks: `python3 tools/sat/check.py`, `python3 tools/sat/check_bridges.py`.
