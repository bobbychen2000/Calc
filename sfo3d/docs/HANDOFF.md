# SFO Live 3D — session handoff (from Claude in Cowork, 24 Sep 2026)

This document records what exists, why it was built this way, what was verified, and what is left.
`CLAUDE.md` holds the objective, the working rules and the architecture. Read that first.

---------------------------------------------------------------------------------------------------------------------

## 1. History (phases)

1. **Cinematic video (done).** A custom offline WebGL2 renderer (`js/main.js`, `js/shots.js`, `render.mjs`) produced a 68 s 4K MP4 of SFO. The shots are aircraft landing, taking off and taxiing to gates.
   - This work also covered procedural airliners, the cockpit window rebuild and imported real aircraft models.
   - The video files are not in this package; they are large.
   - `render.mjs` needed a Playwright patch: add `{ maxPostDataSize: 65536 }` to `Network.enable` in playwright-core `lib/server/chromium/crNetworkManager.js`. This is only needed for streaming frames.
2. **Pivot to live.** The user asked for more than an MP4. Their words: "I want a running 3D modeling that reflect real world traffic and aircraft's data into and out sfo and where those aircraft's parked. Their tail numb[ers, airlines, types] …"
   - This produced the live app in `js/live/`.
   - Real airport geometry comes from SFO Museum data; ADS-B comes from adsb.lol / adsb.fi.
   - Also built: a traffic engine, the UI, and the 21 converted aircraft models.
3. **Airport fidelity.** The user asked for:
   - the "same meticulous care" for runways, taxiways, buildings, bridges and items;
   - "significantly more details";
   - "physical objects can't collide or morph", with aircraft on pavement;
   - an ATC toggle, and to "surpass anything on the market";
   - gate-number markers on bridges;
   - adversarial visual QA passes, with the layout confirmed against satellite images.

   Built so far: FAA markings and signs, terminal parts, tower, ITB hall, detailed jet bridges, VDGS, GSE, masts.
   - QA pass 1 found about 70 defects (`docs/qa/review_pass1.md`).
4. **Satellite survey (last segment).** The user sent 16 Google Maps screenshots; 2 were duplicates, which left 14 unique images. They then sent 5 more of the airfield. The user's feedback was: "some bridges are soo close together … a plane is a physical object, and they will collide if you don't space up well".
   - Root cause: the SFO Museum "gate" points are **hold-room/lounge points inside the building**, not aircraft stands. Several are 3–10 m apart, for example B6/B7/B8, C7/C9, G11/G12 and D17/D18.
   - Fix: all 19 screenshots were georeferenced and a real stand layout was surveyed from them. The details are below.

## 2. Satellite georeferencing (tools/sat) — how and how well

- Each screenshot is 1290×2796, taken on an iPhone in Google Maps.
  - Rotation comes from the map compass (`scalebar.py` / `orient.py`).
  - Scale comes from the scale bar.
  - Registration uses coarse FFT correlation plus chamfer refinement against the SFO Museum outlines (`register.py`), or SIFT matches pooled across already-registered images (`featreg2.py`).
- Results live in `tools/sat/work/reg.json`, as a similarity transform: world (x, z) → image pixels.
- **Verification:**
  - FAA runway-end coordinates (`js/geo.js` `RWY_ENDS`, AirNav) and centerline intersections project exactly onto the imaged runway ends and intersections. See `faacheck.py`: the crops show the cross on the end line.
  - Cross-image consistency (`crosscheck.py`, `offset.py`): median discrepancy 0.5–1.7 m.
  - Two images were wrong and were corrected:
    - `151ec51d` (G pier) had slid 17.5 m along the pier axis;
    - `c235f3b8` (E pier) was off by about 2.3 m.
  - The stands measured on those two images were shifted by the same amounts in `stand_defs.py`.
- The EMAS beds measured on the imagery agree with published data (Runway Safe, SFO reference):
  - published: beds start 35 ft (10.7 m) beyond the runway end and are 372–437 ft (113–133 m) long;
  - measured: starts at 11–15 m, lengths 111–136 m.

## 3. Stand layout (data/sfo_stands.js)

- **89 contact stands and 117 bridges.**
  - 43 stands are `src: obs`: an aircraft was parked there in the imagery, and its nose, heading and class were measured.
  - 46 are `src: inf`: inferred from parked bridge heads and the pier pitch.
- The pipeline:
  - `tools/sat/stand_defs.py` holds the hand-measured stands with comments;
  - `export_stands.py` → JSON/JS;
  - `check.py` checks aircraft vs building and aircraft vs aircraft clearance for each stand's largest class;
  - `check_bridges.py` checks bridge length and crossings.
- **Classes:** B (CRJ/E175), C (A320/737), CL (A321/737-9), D (767), E (787/A330), EL (777-300ER), F (747-8).
  - A stand's class caps the aircraft it accepts: `traffic.js` `standFits`.
  - An oversize aircraft blocks its neighbours.
- **Names:** each stand takes its hold-room name, with the other hold rooms it serves listed as `alias`. Names at pier tips are the nearest hold room, which is not necessarily SFO's official stand number. *Unverified.*
- **Bridges:**
  - One bridge per stand; wide-body stands (D/E/EL/F) get two, at doors L1 and L2.
  - A bridge attaches at the hold-room edge point. If a straight bridge from there would cross the building, it attaches at the building point nearest the door instead, for example the walkway fingers at the B-pier tip.
- **Check results:**
  - 0 physical conflicts (less than 3 m).
  - 13 pairs have wingtip clearance 0.5–1.5 m below the ICAO 7.5 m / 4.5 m design value. These are measured real spacings.
  - Long bridges:
    - B11 and B16 (about 62 m) are **real**: the imagery shows long diagonal bridges from the pods;
    - A1 (60 m), D10 (54 m) and F11 (50 m) need checking.
- **Red equipment boxes:** 221 detected by colour on the imagery (`redboxes.py`) and drawn by `markings.js`. False positives were not audited one by one.

## 4. Other imagery-derived data

- **`data/sfo_paint.js`:** 83 polygons of green no-taxi island paint (FAA AC 150/5340-1M §1.5.2), about 9 ha. It is baked into the airfield albedo through the `uPaint` texture.
- **`data/sfo_pavement.js`:** 75 polygons (about 196 ha) of paved areas that the SFO Museum geometry lacks: cargo and maintenance aprons, island shoulders, service areas and landside.
  - They come from a grey-pixel classification of the mosaic, with water excluded and holes up to 8000 m² filled.
  - `conc[]` flags the concrete ones.
  - The west field looks patchy; this needs work.
- **Runway ends (`airport.js` `END_ZONES`, shader `ground.js`):**
  - 28L/28R blast pads, measured on the imagery:
    - 108 m long and as wide as the runway;
    - yellow chevrons at 45°, about 3 ft wide, with apex spacing 29.7 m starting 15 m from the end;
    - a yellow demarcation bar.
  - EMAS beds at 1L/1R/19L/19R as 3D geometry: 66 m wide, height 0.25→0.6 m, yellow chevrons.
  - The 10L/10R ends have no pad; nothing is visible in the imagery.
- **Displaced threshold (28L/28R), measured on the imagery:**
  - a 10 ft bar;
  - a row of 4 arrowheads at ±25 ft and ±75 ft from the centreline, with tips about 2 m before the bar and about 12 m long;
  - centreline arrows with the first tip 25 m before the bar, a 12 m head and a 15 m shaft, repeated every 55 m.

  The repeat spacing for 1L/1R, whose displacements are longer, is **an assumption**. The FAA figure dimensions could not be extracted from the AC PDF, so check them against AC 150/5340-1M Fig. A-7.
- **Threshold stripes:** 16 stripes for a 200 ft runway, 5.75 ft wide with 5.75 ft gaps, and a double gap at the centre (AC 150/5340-1M §2.5.5).
- **Aiming point:** starts 1,020 ft from the threshold (§2.6).

## 5. Traffic, physics and rendering changes this segment (all in the repo)

- **`traffic.js`:**
  - Stand matching compares the report with the stand's expected ADS-B antenna point (the nose minus 0.2 L), plus the class check.
  - At a contact stand, an aircraft snaps exactly onto the lead-in line, nose-in.
  - Heading inference for aircraft first seen stationary with no heading:
    - on a runway → lined up on the departure direction;
    - on a taxiway → along the centreline, facing the nearest runway;
    - on a ramp → nose toward the nearest building, else toward the terminal core.
  - The storage key changed to `sfolive.parked.v2` because the stand names changed.
- **`ground.js` (new):** `GroundPhysics.resolve()` runs after `traffic.update()`. It is only tested on the snapshot, where 16 moving and 11 free aircraft needed 0 corrections.
- **`gates.js`:**
  - multiple bridges per stand, with walkway columns;
  - L2 docks only for wide-bodies;
  - VDGS on a post when the facade is far from the stop point;
  - baggage trains alongside the aft fuselage, behind the wing;
  - new cart and tug colours.
- **Rendering:**
  - an SDF runway glyph atlas (fixes the missing "2");
  - anisotropic filtering per quality tier;
  - livery colours converted sRGB → linear;
  - nav, strobe, tail and beacon lights anchored on the real model geometry (the tail light sits on the tail cone, not the fin tip);
  - realistic car colours on the garage roof;
  - saturation 1.1.
- **Enhanced taxiway centreline:** it now follows the real centreline polyline, at a 12 in offset. In the `hold:12` renders the dashes still *look solid*. Verify this; it may be the far-dash fade in `markings.js`.

## 6. Status of the QA pass-1 findings (`docs/qa/review_pass1.md`)

| Finding | Status |
|---|---|
| Impossible poses / off-gate / overlaps / aircraft on sand | fixed: surveyed stands, snapping, heading inference, GroundPhysics, extra pavement — needs QA pass 2 |
| Blank aprons (no lead-ins / red boxes) | fixed (lead-ins, stop bars, 221 red boxes) |
| ANISO = 1 | fixed |
| Runway "2" missing, arrowheads missing, stripe spacing | fixed (SDF, imagery-measured arrows, 16 stripes) |
| Enhanced centerline wrong | reworked; dashes may render solid — check |
| Livery sRGB used as linear | fixed |
| Nav lights floating | fixed (model anchors) |
| Pink carts, cart train under wingtip | fixed (colours, placement) |
| Garage roof confetti | fixed (car colour mix) |
| Tone mapping washed out | partly (sat 1.1); reassess |
| Gray-box materials, bridge detail, facade moiré | open |
| Tower cab/roof shape | open — needs reference photos of the 2016 SFO tower |
| ITB roof looks like a tarp | open |
| Gate signs illegible | open (make larger / higher contrast) |
| Terrain streaks, coastline stair-steps, city tiling | open |
| Shadow/aliasing artifacts | open |

## 7. Task list (priority order)

**P0 — the objective's core, and plausibility**
1. **Adversarial QA pass 2.** Render a full view set (see `CLAUDE.md`; `out/live/qa8_*` are the current state). Run an independent reviewer subagent against `docs/qa/ref/*`, fix, and repeat. The user explicitly wants several passes.
2. Test `GroundPhysics` and the stand matching under **moving** traffic (the mock relay moves aircraft), and in live mode once the relay exists. Check taxiing overlaps, pushback, and aircraft at remote and cargo stands.
3. **Cross-check the 46 inferred stands and the stand numbers against authoritative data.** The Cowork sandbox could not reach Overpass: robots.txt blocked one mirror and another returned 429. Possible sources:
   - OpenStreetMap Overpass: `aeroway=parking_position` and `aeroway=jet_bridge` around 37.6188, −122.3754;
   - the X-Plane Scenery Gateway KSFO `apt.dat` (1300 ramp-start rows);
   - SFO terminal maps.
4. Remote and cargo stands: only G103–G105 exist. Add the cargo, maintenance and remote stands seen in the imagery, which is now paved.
5. Check the long bridges (A1, D10, F11) and the B26/B27 rotundas that share one walkway finger.

**P1 — fidelity**
6. **Airfield lighting to FAA/AirNav.** `js/geo.js` `APPROACH_LIGHTS` and `js/anim/lights.js` are unverified. Earlier notes from AirNav, still to be re-verified:
   - 28L MALSR 1400 ft + RAIL;
   - no ALS on 1L/19R;
   - TDZ lights only on 28R/19L;
   - PAPIs with the published angles;
   - REIL on 10L/1R/1L;
   - green taxiway centreline lights.
7. Tower model (Fentress, 2016), ITB roof, terminal materials, gate-sign legibility, GSE models, night lighting, lead-in visibility at distance.
8. Displaced-threshold arrow spacing for long displacements (1L 640 ft, 1R 560 ft): verify against AC 150/5340-1M Fig. A-7.

**P2 — features and delivery**
9. **ATC audio toggle.** Link out to LiveATC's own player: `https://www.liveatc.net/hlisten.php?mount=<mount>&icao=ksfo`.
   - Mounts noted earlier (**unverified — confirm on liveatc.net**): Tower `ksfo_twr` (120.5), Ground `ksfo_gnd` (121.8), NorCal Approach `ksfo_app2_l`, Departure `koak_dep`, combined `ksfo_gnd_twr`.
   - Frequencies must match the FAA Chart Supplement / AirNav.
   - LiveATC's embedding terms are unverified, so don't embed the audio stream.
10. **Local relay `sfo_live_server.py`** (Python, stdlib only). It serves the app plus four endpoints:

    | Endpoint | Behaviour |
    |---|---|
    | `/api/ping` | returns `{"sfolive":1}` |
    | `/api/adsb?lat&lon&dist` | adsb.fi first, adsb.lol as fallback |
    | `/api/routeset` | POST passthrough to the adsb.lol routeset |
    | `/api/metar?ids=KSFO` | aviationweather.gov |

    Provider terms:
    - adsb.fi: 1 request per second, personal non-commercial use, attribution with a link;
    - adsb.lol: verify its terms and licence.

    `entry.js` auto-detects the relay through `/api/ping`.
11. **Packaging.**
    - (a) A standalone single-file HTML: bundle the ES modules, embed the models as base64 in `window.SFO_EMBED`, and ship it with the relay.
    - (b) A Claude artifact of at most 16 MB in snapshot mode: models as `.bin` supporting files via `window.SFO_MODEL_BASE` / `SFO_MODEL_EXT`.
    - Check performance on mobile.
12. **Licences before any public sharing.**
    - The FlightAirMap models are GPL-2.0 per each model's COPYING/LICENSE file.
    - **The A220 models (bcs1/bcs3) have no licence file** in `Ysurac/FlightAirMap-3dmodels`. Confirm the licence, or fall back to the procedural airframe.
    - SFO Museum data: CDLA-Permissive-1.0.
    - Google imagery: reference only.

## 8. Source repositories (clone into `../refs/` or set the env vars)

| Env var | Repository | Commit |
|---|---|---|
| `SFOM_DATA` | `sfomuseum-data/sfomuseum-data-architecture` | 5f64ee8 |
| `FAM_DIR` | `Ysurac/FlightAirMap-3dmodels` | 0906d9b |
| `FG738_DIR` | `FGMEMBERS/737-800` | 9126249 |

Reference repositories: `adsblol/api` (3c969c8), `adsbfi/opendata` (9fe1c9a), `wiedehopf/readsb` (843d8e3), `vradarserver/standing-data` (4e0cb94).

## 9. Environment notes

- The Cowork sandbox had no general internet: only `git clone` from github.com, plus WebSearch/WebFetch. On your machine you can reach the data sources directly.
- The Linux sandbox rendered with Mesa llvmpipe, so use `SOFTGL=1` there. A laptop with a GPU renders far faster.
- `tools/sat` reads the screenshots from `tools/sat/screens/` or `$SFO_SCREENS`, and writes to `tools/sat/work/` or `$SFO_SATWORK`. The re-encoded JPEG screenshots reproduce `data/sfo_stands.json` byte for byte (verified).
