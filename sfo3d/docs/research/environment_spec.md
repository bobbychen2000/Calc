# Environment spec: lighting, day/night and weather for SFO Live 3D

Implementation spec for the owner's request "I also appreciate lighting, day/night support, weather support". It merges
three verified research reports into one buildable design for the new three.js r186 `WebGPURenderer` (`js/three/**`,
being built by another workflow; `docs/research/engine.md`) and, where cheap, the current WebGL2 renderer
(`js/renderer.js`, `js/shaders/*`, `js/anim/lights.js`):

| Report | What it contributes | Verification |
|---|---|---|
| `docs/research/airfield_lighting.md` + `tools/env/lighting_spec.json` + `tools/env/lighting_fixtures.json` | SFO light systems per runway end, FAA geometry, photometry, colours, JO 7110.65 operating rules, 2,269 fixtures | adversarial check §15 (36 claims; 5 corrected) |
| `docs/research/weather.md` + `tools/env/metar_decode.py` (+ 38 tests on 58 real KSFO reports) | METAR/TAF decoding, visibility → extinction, clouds, precipitation, wetness, wind, SFO climatology, live sources | adversarial check (38 claims; 6 corrected) |
| `docs/research/sun_night.md` + `tools/env/ephemeris.mjs` (+ 32 tests) | Sun/Moon ephemeris, twilight, natural illuminance (USNO Circular 171), sky options, exposure, aircraft lights | adversarial check (46 claims; 7 corrected) |

Written 24 Sep 2026. Research only: nothing in `js/`, `data/` or other docs was changed and nothing was committed. New
files: this document, `tools/env/env_spec_checks.py` (reproduces every number marked **M** below) and
`tools/env/fixtures/env_presets.json` (14 real-weather presets with expected environment and lighting states: the
acceptance test vectors). New downloads: `refs/cache/env_spec/` (gitignored).

**Tags** (one scheme for all three reports):

| Tag | Meaning | Same as |
|---|---|---|
| **V** | Verified: quoted from, or computed with, the primary source named next to it | weather `[V]`, sun_night `V`/`T` |
| **pub** / **std** / **obs** | Fixture provenance in `lighting_spec.json`: published SFO fact / FAA standard applied to SFO (**as-built not surveyed**) / measured on NAIP 2024 | airfield_lighting |
| **M** | Measured or computed by our tools from real data (reproducible command given) | weather `[M]`, sun_night `obs` |
| **I** | Inferred: our modelling or design choice. Open to correction; must be visible in QA overlays | `[I]`, `inf` |
| **2nd** | Secondary source (original not fetchable) | `[2nd]` |
| **NV** | Not verified / unknown. Needs the owner or a follow-up. Must not be presented as fact | `[NV]`, `NV` |

---------------------------------------------------------------------------------------------------------------------

## 1. Summary

1. **One renderer-agnostic environment core, two thin renderer adapters.** A pure-JS core computes one `EnvState`
   object per frame from (a) the **data clock**, (b) the current **METAR/SPECI** (relay `/api/metar` live and in replay;
   `SNAPSHOT_METAR` in snapshot and artifact mode), (c) the **runway configuration observed in traffic**. Both
   renderers read `EnvState`; neither computes weather or lighting logic itself (§3).
2. **Day/night is astronomy, not heuristics.** `tools/env/ephemeris.mjs` (matches JPL Horizons to < 0.01° over all of
   2026 and USNO rise/set/twilight to 1 min; **V/T**) replaces `solarPosition` and the hard-coded UTC−7 presets.
   Natural illuminance comes from USNO Circular 171 (**V**). Tower-operated lights switch at USNO sunset/sunrise, as
   JO 7110.65 says ("between sunset and sunrise"); photocell systems switch on illuminance (§4.1–4.2).
3. **Weather is the real KSFO METAR, decoded correctly.** Port `metar_decode.py` to JS (the current `parseMetar` reads
   `M1/4SM` as 4 SM; **M**). Visibility → extinction uses the ASOS day/night inversion (**V** constants via Rasmussen
   1999, **2nd** for the NWS spec itself), with the day/night switch driven by the same illuminance model (§4.3).
4. **New result: one visibility model for weather *and* lights.** With the ASOS extinction inversion, Allard's law with
   one threshold per period reproduces **every row of the FAA's own calibration table** (AC 70/7460-1N Table B-1 plus
   its B.3 night 1 SM case) within **3.2 %**: night E_T = 6.99×10⁻⁷ lx, day E_T = 4.12×10⁻⁴ lx; the twilight rows are
   exactly the day model at one end and the night model at the other (**M**, §4.10). The airfield report had found no
   single threshold with σ = 3/V (27 % error); that gap is closed.
5. **Airfield lighting is data, not code.** Render the 2,269 fixtures in `lighting_fixtures.json` (plus the REL arrays
   still to be expanded) through a lighting controller that implements the JO 7110.65BB §3-4 tables (**V**): steps,
   28R SSALR↔ALSF-2, flasher rule, edge lights by day below 2 SM, ALS by day below 1,000 ft / 5 SM, PAPI photocell,
   beacon, obstruction lights, RWSL (§5). A Python reference controller and 14 real-weather test vectors are provided
   (`tools/env/env_spec_checks.py`, `fixtures/env_presets.json`).
6. **What stays open (NV) and must not be faked:** ALS/flasher/apron-flood photometry (no FAA public source), apron
   floodlight colour, rotating-beacon and windsock positions, taxiway lighting per taxiway, which ALS stations are lit on
   the 28L/28R piers, MALSR control wiring (new, §5.3), SFO facility directives. These ship as clearly marked
   parameters or are not drawn, and are listed as owner questions (§12).
7. **Wide gamut is not available in r186 `WebGPURenderer`** (**M**, source read: `WebGPUBackend.js` configures the canvas
   without a `colorSpace`; only the classic `WebGLRenderer` sets `drawingBufferColorSpace`). Use the EB 67D colours
   clipped to linear sRGB (already in `lighting_spec.json`), keep the xy values for a later P3 path (§4.11).

---------------------------------------------------------------------------------------------------------------------

## 2. What was merged, and what this spec adds

### 2.1 Traceability of the 24 input recommendations

| # | Recommendation (source) | Where specified |
|---|---|---|
| L1 | Drive airfield lighting from `lighting_fixtures.json` / `lighting_spec.json`; show provenance in QA overlays (airfield §13.1) | §5.1, §11.4 |
| L2 | Lighting controller from JO 7110.65BB tables (airfield §9) | §5.3, test vectors §10 |
| L3 | Directional point sprites, beam limits, cd × step, EB 67D colours, Allard tuned to Table B-1 (airfield §10) | §4.10, §4.11, §5.4 |
| L4 | Fix the `js/anim/lights.js` defects (airfield §12) | §9.2 |
| L5 | Replace procedural masts with the 54 DOF poles (airfield §7.5) | §5.7 |
| L6 | ALS pier structures from NAIP, light plane at threshold elevation (airfield §6.3) | §5.6 |
| L7 | Ask for night photos (piers, beacon, RCL, taxiway lights) (airfield §13.6) | §12 |
| L8 | Adversarial visual QA at dusk / night-clear / night-fog on the 28 approach (airfield §13.7) | §11 |
| W1 | Port `decode_metar` to JS with the 58 fixtures (weather §6.1) | §3.3, §11.1 |
| W2 | Relay `/api/metar` + `/api/taf`, polling, UA, max-age/ETag; remove browser fallback (weather §5.1) | §3.3 |
| W3 | ASOS day/night extinction, blended; remove the 0.004 m⁻¹ / 97 % caps; 10SM is a bound (weather §3.1–3.2) | §4.3 |
| W4 | Three-slab vertical profile; BCFG/PRFG/MIFG, TWR/SFC VIS, sector remarks (weather §3.3) | §4.4, §7.3 |
| W5 | Every cloud layer, de-summed coverage, own shadow; exposure/ambient from sun-visible probability and K–C; drift from winds aloft (weather §3.4) | §4.5, §7.4 |
| W6 | GPU rain (Marshall–Palmer), drizzle mist, lightning; wetness/puddles (Lagarde) (weather §3.5–3.6) | §4.6, §4.7, §7.5–7.6 |
| W7 | Windsocks: true METAR wind, 0 at 3 kt → 1 at 15 kt, gusts, PK WND; survey positions (weather §3.7) | §4.8, §5.10 |
| W8 | Runway config: ADS-B flow → D-ATIS (if accepted) → METAR + 3-5-1; 2500/5 flag only for visual approaches (weather §4.5) | §3.5 |
| W9 | Store METAR + TAF with the snapshot; real archived presets; QA views per regime (weather §6.6–6.7) | §3.4, §10, §11 |
| S1 | `ephemeris.mjs` `skyState()`/`sunEvents()` replace `solarPosition` and `lightDate`; CI test (sun_night §8.1) | §4.1, §3.2 |
| S2 | Circular 171 illuminance + EV100 instead of `nightF`/`dark`; floods on < 32 lx; night at −6°; Brown's cloud divisors (sun_night §8.2) | §4.2, §8 |
| S3 | takram atmosphere (`/webgpu` entry) after a GPU test; self-host `stars.bin`; ephemeris-driven; `sky.js` fallback; attribution (sun_night §8.3) | §7.1 |
| S4 | Physical light units, pre-exposure, auto-exposure with EV clamp [2, 16] (sun_night §6.3) | §8 |
| S5 | Aircraft lights per 14 CFR 25 + AIM 4-3-24 (sun_night §5.4) | §6 |
| S6 | Floodlight CCT, terminal glow, bridge beacon stay parameters until owner photos (sun_night §8.7) | §5.7, §12 |
| S7 | Night-sky artificial luminance parameter, default 3 mcd/m², ×≤10 under low overcast (sun_night §8.6) | §4.9 |

### 2.2 Conflicts between the reports, and how this spec resolves them

| # | Conflict | Resolution |
|---|---|---|
| X1 | Day→night blend of the visibility inversion: weather.md suggests sun elevation −1° to −5° (**I, NV**); sun_night.md maps the ASOS photocell (0.5–3 fc) to −3.7° to −5.5° with Circular 171 (**I** on **V** physics) | Blend on **illuminance**, not elevation: 32.3 lx → 5.38 lx (3 → 0.5 fc), log-linear, using Circular 171 with the cloud divisor (§4.3). Clouds then shift the switch earlier, as a real photocell would. |
| X2 | Allard threshold: airfield §10.3 found no single E_T with σ = 3/V (night rows 1.6–3.6 ×10⁻⁶ lx) | Use the ASOS σ inversion: one E_T per period fits all rows within 3.2 % (**M**, §4.10). |
| X3 | Brown's ÷10 is for "dark stratus clouds preceding a heavy thunder storm … (RARE)" (sun_night verifier), but SFO's usual cloud is ordinary marine stratus | Divisor D = 1 / (Kasten–Czeplak ratio) (OVC → 4, close to Brown's "average cloud" 3); ÷10 only with TS or CB (**I**, §4.2). |
| X4 | Circular 171 divides the night-sky floor by the cloud divisor (darker under cloud); Kyba 2011 shows city glow is **amplified** by cloud (×10.1 in Berlin) | Two separate terms: natural floor ÷ D; artificial city glow × amplification (§4.9). |
| X5 | Night HIRL step at 3–5 SM: airfield §9 said step 1; verifier: step 2 | Step 2 (TBL 3-4-8 "3 to 5 miles inclusive"; re-read here, **V**). |
| X6 | REL arrays: the FAA graphic has **28** labels (taxiway N added by the verifier); `lighting_spec.json` `rwsl.rel` has 27 and `lighting_fixtures.json` has no REL fixtures | Regenerate before implementation (§5.1 D1). |
| X7 | 28R pier far end: JSON says "> ~2350 ft"; verifier: NAIP grid ends ~2,650 ft, pile caps to ~2,600 ft | Regenerate the JSON note (§5.1 D2). |
| X8 | Tower obstruction lights: JSON `fixture_inferred` cites AC 70/7460-1N §5.5 (one L-864 + L-810(F)); verifier: §5.6 (≥ 3 L-864 at top + steady L-810 mid level) | Use §5.6 (§5.8); regenerate the JSON text (§5.1 D3). |
| X9 | Rain rate: weather.md "use Prrrr when present"; but Prrrr is an **average since the last METAR** while the intensity (+RA) is the rate **at observation**. The 25 Dec 2025 squall has `+RA` (> 7.6 mm/h) and P0016 → 4.1 mm/h (**M**) | Clamp the Prrrr rate into the reported intensity class (§4.6, **I**). |
| X10 | Nav lights on parked aircraft: sun_night rule 3 vs its verifier (91.209(a)(2) covers parking; "clearly illuminated" suffices) | Default off at floodlit gates when the beacon is off; owner decides (§6, §12). |

### 2.3 New checks made for this spec (all reproducible)

1. **Table B-1 fit** (§4.10): `python3 tools/env/env_spec_checks.py` (**M**).
2. **JO 7110.65BB §3-4 re-read** from the cached online edition (`refs/cache/lighting/jo7110_65_chap3_section_4.html`,
   fetched 2026-09-24 by the lighting work): paragraph numbers corrected (REIL is 3-4-2 with TBL 3-4-1; ALS intensity is
   3-4-6/TBL 3-4-5; MALSR is 3-4-8 with TBLs 3-4-6/3-4-7; HIRL is 3-4-11/TBL 3-4-8; taxiway lights 3-4-16/TBL 3-4-12),
   the TBL 3-4-5 NOTE ("Daylight steps 2 and 3 provide recommended settings …; At night, use step 4 or 5 only when
   requested by a pilot") and a **third MALSR rule, 3-4-12 "HIRL associated with MALSR" (TBL 3-4-9)**, which the lighting
   report did not list (**V**, §5.3).
3. **14 CFR 91.155** fetched from eCFR (point in time 2026-09-01; `refs/cache/env_spec/ecfr_91_155.xml`) for the
   "basic VFR minima" that switch the beacon by day: ceiling ≥ 1,000 ft (91.155(c)) and ground visibility ≥ 3 SM
   (91.155(d)(1)) (**V**; https://www.ecfr.gov/current/title-14/part-91/section-91.155).
4. **AIM 2-1-2 / 2-1-6 cross-checks** from the cached AIM chapter 2 (**V**): PAPI "visible from about 5 miles during the
   day and up to 20 miles at night"; THLs "starting at a point 375 feet from the departure threshold"; REL departure
   threshold ≈ 30 kt, arrival ≈ 1 mile, 80 kt and 34 kt states.
5. **three.js r186 colour output** read in `node_modules/three` 0.186.0 (§4.11, **M**).
6. **Relay replay clock**: `sfo_live_server.py` `/api/ping` exposes `replay: {dir, speed, from, loop}` but not the
   current data time, so the app cannot place the Sun correctly in replay (§3.2, **M**, code read).
7. **Sun/Moon state of every preset** with `ephemeris.mjs` (§10, **T** via the module's tests).

---------------------------------------------------------------------------------------------------------------------

## 3. Architecture and data flow

### 3.1 Modules (proposed paths; renderer-agnostic, plain ES modules, no DOM)

```
  data clock ───────────────┐      relay /api/metar,/api/taf (live, replay)      traffic.js events/phases
  (live / replay / snapshot │      SNAPSHOT_METAR (+TAF) (snapshot, artifact)    runwayConfig() (stats.js)
   / QA override)           │      preset (QA, "weather presets" menu)                  │
                            ▼                        ▼                                   ▼
   js/env/clock.js ──► js/env/sky.js ◄── tools/env/ephemeris.mjs (copied or imported; tests in CI)
                            │     js/env/wx/metar.js (port of metar_decode.py) ──► js/env/wx/params.js (render_params)
                            ▼                        ▼                                   ▼
                     js/env/state.js  ── EnvState (one object, units + provenance per field) ──┐
                            │                                                                   │
            js/env/lighting/controller.js (JO 7110.65 tables) ◄── tools/env/lighting_spec.json   │
            js/env/lighting/fixtures.js (lighting_fixtures.json → sprite records per frame)      │
            js/env/aircraft_lights.js (14 CFR 25 / AIM 4-3-24)                                  │
                            │                                                                   │
              ┌─────────────┴───────────────┐                                                   │
              ▼                             ▼                                                   ▼
   js/three/* adapter (new renderer)   js/live/app.js applyEnv → js/renderer.js + js/shaders/* (old renderer, §9)
   sky/atmosphere, fog slabs, clouds, rain, wetness, exposure, Sprites (js/three/lights.js)
```

- `lighting_spec.json` and `lighting_fixtures.json` are build inputs. Ship them as a generated `data/sfo_lighting.js`
  (same pattern as the other `data/*.js`, made by `tools/env/build_lighting_spec.py`), not hand-edited.
- Everything in `js/env/` must run in Node (unit tests in CI, no GPU) and in the browser.

### 3.2 The data clock (what "now" means for the environment)

| Mode | Environment time `t_env` | Source |
|---|---|---|
| Live (relay or direct) | `traffic.displayTime(Date.now())`: wall clock minus the display delay and the ATC-audio delay, i.e. the time of the traffic actually on screen (the provider clock skew `traffic.offset` is seconds and irrelevant for the Sun) | `js/live/traffic.js:230,268` (**M**, code read) |
| Relay replay | The recording's clock. **Gap:** `/api/ping` does not expose it. Add `dataNow` (ms) = `Clock.to_src(time.time())` to `/api/ping` and to every ADS-B payload | `sfo_live_server.py` `Clock`, `Metar.get` (**M**) |
| Snapshot / artifact | `cfg.snapshot.now` = 23 Sep 2026 17:51:00Z (10:51 PDT) | `data/snapshot.js` |
| QA / "time machine" override | `?t=<ISO-8601 UTC>` or a preset id; overrides the environment only, traffic keeps its own time. The UI must show "environment time ≠ traffic time" | new (**I**) |
| Light-mode menu (Real / Dawn / Day / Dusk / Night) | Times on the **same local date** from `sunEvents()`: Dawn = midpoint of civil dawn and sunrise; Day = solar transit; Dusk = civil dusk − 10 min; Night = nautical dusk + 60 min (**I**; replaces `app.js:114`, which is 1 h off in PST and seasonally wrong, sun_night §2.4 as corrected) | `ephemeris.mjs` |

Local time and the UTC offset for `sunEvents()` come from `Intl.DateTimeFormat` with `timeZone:
'America/Los_Angeles'` (DST-correct), never from a constant.

### 3.3 METAR/SPECI and TAF transport

**Relay (standalone app, live and replay).** `/api/metar` already exists (aviationweather.gov, 60 s cache, `hours=2`,
custom UA `sfo-live-3d-relay/<ver> (+repo URL)`; replay returns the latest cached report observed ≤ 90 min before the
replay time, never today's weather; **M**, code read). Changes (weather.md §5.1, **V** limits, **I** schedule):

- Fetch `metar?ids=KSFO&format=json&hours=3` (JSON gives `obsTime` and `receiptTime`; always decode `rawOb`, weather
  §2.7) plus `/api/taf` from `taf?ids=KSFO&format=raw`.
- Poll upstream every 60 s from hh:59 to hh:03 and every 5 min otherwise (KSFO routine METARs are at hh:56 and reach the
  API 4.1–4.4 min later, p10–p90; about 8 % arrive 6.6–28.6 min late and one SPECI took 89 min, **M**). This stays far
  under "100 requests per minute" (**V**).
- Honour `cache-control: max-age=60` and send `If-None-Match` with the ETag (**M** headers).
- Keep the last good report with its age; tolerate a missing routine METAR for up to ~30 min before flagging "stale".
- `js/live/app.js` polls `/api/metar` every 60 s (it is 10 min today, which delays SPECIs); the relay cache makes this
  free. **Remove the browser fallback in `js/live/feed.js:144`**: aviationweather.gov sends no CORS header ("Cross-origin
  resource sharing is not permitted at this time", **V**), so that call can never succeed in a browser.
- Terms: NWS content is public domain with the three conditions of https://www.weather.gov/disclaimer (**V**); credit
  "Weather: NOAA/NWS Aviation Weather Center" (already in the relay's attribution list).

**Selection by data clock.** The current report is the latest with `obsTime ≤ t_env` (live: the latest received).
Older than 90 min → `wx.stale = true`, keep it, show the age. Example: at the snapshot time 17:51Z the current report is
`SPECI KSFO 231722Z 09004KT 10SM FEW004 SCT008 …`, not the 1656Z METAR (**M**).

**Transitions.** Numeric weather fields interpolate over 60 s of data time after a new report (weather §3); lighting
steps change instantly (tower switch) with a 0.3 s lamp ramp (**I**); PAPI day/night mode switches after the photocell
delay of 45–75 s (AC 150/5345-28H §3.3.6, **V**; use 60 s).

**Beyond the latest METAR** (time machine forward): use the TAF period in force (`decode_taf`, FM/TEMPO/BECMG/PROB) and
label the scene "forecast" (**I**).

### 3.4 Snapshot and artifact

- `data/snapshot.js` has 3 METARs and no TAF. Add the TAF valid at 17:51Z on 23 Sep 2026 (AWC keeps 30 days, so fetch it
  before 23 Oct 2026; **V** limit).
- The artifact (no network) uses `SNAPSHOT_METAR` and the **weather presets** of §10 (all real archived KSFO reports,
  ~45 KB JSON). Showing archived weather in the artifact is an owner decision (weather Q6, §12).

### 3.5 Runway configuration (input to the lighting controller)

Priority (weather §4.5, **I** built on **V** facts):

1. **Observed ADS-B flow**: `runwayConfig(events, t_env)` in `js/live/stats.js` (landings/take-offs per runway in the last
   20 min). Arrival ends = ends with touchdowns or aircraft in `final`/`flare`; departure ends = ends with take-off rolls
   or `lineup`.
2. D-ATIS text (atis.info) only if the owner accepts a source with no published terms (weather Q3).
3. Fallback (snapshot start, empty history): METAR **true** wind with JO 7110.65 3-5-1 ("most nearly aligned with the
   wind when 5 knots or more", **V**); below 5 kt, SFO's West Plan (arrive 28L/R, depart 1L/R; "95-98% of the time",
   flysfo.com, **V**). SFO's formal "calm wind runway" is **NV**.
4. Approach type per arrival end: instrument whenever the METAR is below the charted visual-approach minima "SFO
   2500'/5" (Quiet Bridge / Tipp Toe charts, d-TPP 2609, **V**); otherwise unknown (visual or ILS; the D-ATIS showed ILS
   at night in VFR, **M**). The controller only needs "instrument approaches are being made" for the flasher rule, and
   that rule applies below 3 SM, where visual approaches are impossible anyway.
5. Closed runways (e.g. "RY 1L, 1R CLSD" on the 24 Sep D-ATIS, **M**, third party): lights off ("Do not turn on the
   runway edge lights when a NOTAM closing the runway is in effect", 3-4-10, **V**). Without NOTAM access the app can
   only infer closure from absent traffic (**I**).

### 3.6 `EnvState` (the contract both renderers consume)

| Field | Unit | Source / rule | Tag |
|---|---|---|---|
| `tEnv`, `mode`, `overridden` | ms, enum | §3.2 | — |
| `sun {az, el, elTrue, dir, semidiameter}` | deg, unit vec (x east, y up, z south) | `ephemeris.mjs` `sunPosition` (Bennett refraction, 1010 hPa, 10 °C) | V/T |
| `moon {az, el, dir, lit, brightLimbZenithAngle, angularDiameter}` | deg, 0–1 | `moonPosition` | V/T |
| `phase`, `towerNight` | enum, bool | `skyState().phase`; `towerNight = elTrue ≤ −50′` (USNO sunset/sunrise) | V |
| `natural {E_clear, D, E}` | lx | Circular 171 `naturalIlluminanceAt`; D = cloud divisor §4.2 | V + I |
| `photocell {asosNightW, papiNight, obstructionOn, floodsOn}` | 0–1, bool | §4.2, §4.3 | V + I |
| `wx {raw, obsTime, ageMin, stale, decoded, taf}` | | §3.3 | V |
| `atm {sigmaSurface, sigmaDay, sigmaNight, visLowerBound, slabs[], fog, sectors[], aerosol}` | m⁻¹, m | §4.3–4.4 | V + I |
| `clouds[] {base, thickness, total, own, kind, drift}` | m, 0–1, m/s | §4.5 | V + I |
| `sunVisibleP`, `kcRatio` | 0–1 | §4.5 | I / 2nd |
| `precip {kind, rateMmH, rateBasis, dropsPerM3, D0mm, vFall, showery, thunder}`, `lightning {perMin, where[]}` | | §4.6–4.7 | V + I |
| `surface {wet, puddle}` | 0–1 | §4.7 state machine | I (constants NV) |
| `wind {fromTrue, speed, gust, peak, variable, range, sockExt}` | deg true, m/s | §4.8 | V + I |
| `nightSky {naturalCdM2, artificialCdM2, colour, stars}` | cd/m² | §4.9 | V + I |
| `lightVis {ET, sigmaEye}` | lx, m⁻¹ | §4.10 | M |
| `exposure {ev100Target, min, max, ec}` | EV100 | §8 | V + I |
| `lighting` | per system: on, step, pct, mode | §5.3 | V + I |
| `runway {arr: {end: type}, dep: [], source}` | | §3.5 | M / I |
| `prov` | per field tag | this table | — |

---------------------------------------------------------------------------------------------------------------------

## 4. Parameter mappings (physics → renderer inputs)

### 4.1 Time, Sun and Moon

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| Sun/Moon direction | `skyState(date).sunDir/moonDir` (`directionWorld(az, el)`, same convention as `sunVector`) | `tools/env/ephemeris.mjs`; accuracy vs Horizons ≤ 0.0094° (Sun) / 0.0023° (Moon) over 2026 | T |
| Apparent Sun at the horizon | Bennett refraction (29′ at the true horizon) | Meeus 16.4; app today sets the Sun 2.9 min early (sun_night §2.4) | T |
| Sunrise/sunset/twilight | `sunEvents(y, m, d, utcOffsetH)`: −50′, −6°, −12°, −18° | USNO RST definitions https://aa.usno.navy.mil/faq/RST_defs | V/T |
| Moon phase and lit side | `moon.illuminatedFraction`, `brightLimbZenithAngle`; with takram, the phase comes from the geometry (`MoonNode` shades from the Sun direction) | Meeus 48; WEBGPU.md | T / V |
| Ground bake refresh | Keep the current thresholds (> 2° el or > 4° az) | `app.js` | I |
| CI | `node tools/env/test_ephemeris.mjs` (32 checks) | — | T |

### 4.2 Natural light, cloud divisor, photocell switches

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| Horizontal illuminance, clear | `naturalIlluminanceAt(date)`: 984 lx at 0°, 24.4 lx at −4°, 2.99 lx at −6°, 0.0049 lx at −12°; full Moon at zenith 0.40 lx; night floor 0.0005 lx | USNO Circular 171 (1987), https://archive.org/details/DTIC_ADA182110; authors: "formally accurate to one or two digits" | V |
| Cloud divisor D | D = 1 / KC(N) with KC(N) = 1 − 0.75 (N/8)^3.4 and N = total oktas from the de-summed layers (OVC → D = 4); D = 10 only if TS or CB in the report | Brown's divisors 2/3/10 quoted in C171 App. B (**V**); Kasten & Czeplak 1980 (**2nd**); the mapping is **I** | I |
| `E` (drives exposure, switching) | E = E_clear / D (sun and moon terms); the night floor is handled in §4.9 | — | I |
| ASOS night weight `asosNightW` | 0 at E ≥ 32.3 lx (3 fc), 1 at E ≤ 5.38 lx (0.5 fc), log-linear between | ASOS User's Guide §4.2: photocell "between 0.5 and 3 foot candles (deep twilight)" https://www.weather.gov/media/asos/aum-toc.pdf (**V**); using horizontal C171 illuminance is **I** | V + I |
| Apron floodlights on | E < 32.3 lx (Sun ≈ −3.7° clear) | sun_night §8.2 (**I**); no SFO or FAA switching rule found (**NV**) | I |
| Tower-operated lights "night" | `towerNight` (USNO sunset → sunrise) | JO 7110.65BB 3-4-5, 3-4-10, 3-4-17, 3-4-18 "between sunset and sunrise" | V |
| PAPI day/night mode | Day mode when the north-facing vertical illuminance rises to 50–60 fc; night mode below 25–35 fc; 45–75 s delay; photocell failure → night | AC 150/5345-28H §3.3.6 https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-28H.pdf (**V**). Estimate the north-sky vertical illuminance as half the C171 horizontal sky term, isotropic sky (**I**); thresholds 55 fc up / 30 fc down (midpoints, **I**) | V + I |
| Obstruction lights | On when north-sky illuminance falls below 60 fc, before it reaches 35 fc | AC 70/7460-1N §5.3 (**V**); same vertical-illuminance estimate (**I**) | V + I |

### 4.3 Visibility → extinction (surface value)

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| σ_day | −ln(0.055) / V = 2.900 / V | ASOS day equation, Koschmieder ε = 0.055 (Rasmussen et al. 1999 §6c, https://opensky.ucar.edu/system/files/2024-08/articles_15245.pdf) | V (constants **2nd**: NWS spec not located) |
| σ_night | ln(I₀ / (CDB·V_mi)) / V_mi, I₀ = 25 cd, CDB = 0.084 mi⁻¹ | ASOS night equation, simplified Allard (Rasmussen eq. 24) | V (**2nd** as above) |
| σ_surface | (1 − w)·σ_day + w·σ_night with w = `asosNightW` | resolves X1 | I |
| Table (V → σ day / night) | 10 SM ≤ 1.80e-4 / ≤ 2.11e-4; 5 SM 3.60e-4 / 5.08e-4; 3 SM 6.01e-4 / 9.52e-4; 1 SM 1.80e-3 / 3.54e-3; ½ SM 3.60e-3 / 7.94e-3; ¼ SM 7.21e-3 / 1.76e-2 m⁻¹ | weather §3.1 (recomputed by the verifier) | M |
| `M1/4SM` etc. | M prefix = "less than": σ is a lower bound; use the value (fog is at least that thick) | JO 7900.5E 13.11 | V |
| 10SM / P6SM | "10 miles or greater": σ is an **upper bound**. Use the clear-air aerosol of the sky model (Mie 21e-6 m⁻¹ + Rayleigh), clamped to ≤ 1.8e-4 m⁻¹ | ASOS guide (**V**); weather §3.1 (**I**) | V + I |
| Remove | the `Math.min(3.912/vis, 0.004)*0.9` density cap and the `fog.w = 0.97` opacity cap (`app.js:125,129`, `common.js:64`) | weather verifier row 2 | M |
| 7–10 SM without HZ/BR | "hazy but unspecified": σ from V, neutral tint | JO 7900.5E only requires HZ/BR below 7 SM | V + I |
| RVR | KSFO reports RVR for 28R only (1,079 reports 2016–2025, **M**). Use it for the lighting controller (§5.3) and as a sanity check of the visual range, never to override σ | JO 7900.5E 13.12, 8.2j | V |

### 4.4 Vertical and horizontal structure (fog, mist, marine layer)

| Case (decoded) | Structure | Source | Tag |
|---|---|---|---|
| Default | Three slabs: sub-cloud σ_surface from ground to the ceiling (or VV); cloud slab σ_c from base to base + depth; clear air above | weather §3.3 | I |
| Stratus depth | Oakland 12Z/00Z sounding inversion base when available (relay, twice daily; IEM raob mirror), else 1,000 ft | MIT LL ATC-319: "usually less than 1000 feet"; "base of the inversion height … estimate of the cloud top height" (**V**) | V + I |
| In-cloud σ_c | 0.04 m⁻¹ default, allowed range 0.025–0.075 (visual range 40–120 m); independent extremes 0.015–0.125 | σ_c ≈ 3·LWC/(2·ρ_w·r_eff) (**I**, textbook); r_eff 4–17 µm (MODIS–MISR, **V**) | I |
| `FG` + `VVhhh` | Surface fog at least VV deep (VV = 100–200 ft in every KSFO FG case seen) | JO 7900.5E 9.3; weather §3.3 | V meaning, I depth |
| `FG` without VV (e.g. `FG BKN000`, partial obscuration, not a ceiling) | Fog top default 200 ft (**I**) | same | I |
| `MIFG` | Fog below 6 ft only: "visibility at 6 feet above the ground is 5/8 SM or more" | JO 7900.5E 13.13e | V |
| `BCFG` / `PRFG` | Noise-masked fog volume (patch scale ~200–500 m, **I**); clear parts keep prevailing σ | JO 7900.5E 13.13e | V + I |
| `BR` | σ_surface through the whole sub-cloud layer | weather §3.3 | I |
| `TWR VIS` ≠ `SFC VIS` | The lower value is prevailing; if tower > surface, fog top below the tower cab (cab eye height **NV**) | JO 7900.5E 8.3, 13.24 | V + I |
| `VIS [DIR] v`, `VIS LWR W` | Directional σ(azimuth) around the station (cosine lobe ±45°, **I**) | 13.26; 29 KSFO `VIS LWR` reports (**M**) | V + I |
| `VIS vnVvx` | Animate σ between the two values over minutes (**I**) | 13.25 | V + I |
| `FG IN GAP W` | Westward fog bank on the horizon (terrain gap; the name "San Bruno Gap" is **I**) | 96 KSFO reports (**M**) | M + I |
| `CIG hnVhx`, `CIG hhh RWY L10` | Ragged base between the two heights; lower base over the 10L area (sensor location **I**) | 13.34, 13.38 | V + I |

### 4.5 Clouds

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| Coverage per layer | Reported amounts are cumulative ("summation amount"). C = okta-range midpoint (FEW 1.25/8, SCT 3.5/8, BKN 6/8, OVC 8/8); own_i = 1 − (1 − C_i)/(1 − C_{i−1}) | JO 7900.5E 10.4o/10.7 (**V**); midpoints and random overlap (**I**); `render_params` | V + I |
| Base height | y = `GROUND_Y` + h_ft × 0.3048 (heights are above field elevation, 13.1 ft) | JO 7900.5E 10.8; AirNav | V |
| Height resolution | ±50 ft below 5,000 ft; ±250 ft to 10,000; ±500 ft above | Table 13-6 | V |
| High layers | `CLR` = nothing detected ≤ 12,000 ft; `SCT200`-type layers come from the observer | 13.14b | V |
| Thickness | Low stratus (< 3,000 ft, SCT–OVC): stratus depth (§4.4); others: renderer default, flagged | weather §3.4 | I |
| Type | CB/TCU only when coded; else by height (< 6,500 ft stratiform; 6,500–20,000 mid; > 20,000 cirriform) | weather §3.4 | I |
| Sun occlusion / shadows | Every layer has a coverage map; the sun ray's transmittance is the product over layers; each layer casts its own shadow | weather §3.4 | I |
| `sunVisibleP` | Π(1 − own_i) | `render_params` | I |
| Ambient / exposure scale by day | KC(N) = 1 − 0.75 (N/8)^3.4 (OVC → 0.25, all diffuse) | Kasten & Czeplak 1980 (**2nd**); NASA S'COOL "P = 990 (1-0.75F³)" (**V**, related form) | 2nd |
| Drift | Wind at the cloud base from the Oakland sounding; fallback: METAR surface wind vector, not amplified (the current `2.5 × surface + 1 m/s` is unsourced) | weather §3.4 | I |
| Variable sky `BKN V OVC`, `BINOVC` | Coverage flicker / breaks (13 KSFO `BINOVC`, **M**) | 13.36 | V + I |

### 4.6 Precipitation

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| Kind | RA / DZ (diameter < 0.5 mm) / GR, GS (rare: 3 KSFO reports in 2016–2025) / SN (not seen) | JO 7900.5E 9.2; weather §3.5 | V / M |
| Rain rate | Prrrr / minutes since the last routine report (KSFO routine at :56), **clamped into the coded intensity class**: light ≤ 2.5, moderate 2.8–7.6, heavy > 7.6 mm/h. Without Prrrr: geometric middle of the class | Table 9-4 (**V**); Prrrr (13.46, **V**); clamp resolves X9 (**I**) | V + I |
| Drop size distribution | Marshall–Palmer: Λ = 4.1 R^−0.21 mm⁻¹, N₀ = 8,000 m⁻³ mm⁻¹; D₀ = 3.67/Λ | Garg & Nayar 2007 quote (**V** for Λ, v); N₀ **2nd/NV** (verifier: the quoted formula gives half) | V + 2nd |
| Fall speed | v = 200 √a (a = radius in m): 4.2 m/s at 1 mm/h, 5.4 m/s at 10 mm/h | Gunn & Kinzer via Garg & Nayar | V |
| Streaks | length = v × exposure time (use 1/60 s) | Garg & Nayar | V + I |
| Particle count | density × volume of a camera-attached box, scaled to the tier budget, class ratios kept | weather §3.5 | I |
| Drizzle | Dense fine mist, no streaks, 1–2 m/s; the visual weight is in σ | weather §3.5 | I |
| Showers `SH` | Cellular: modulate rate in space (cells ~2–5 km, **I**) and time | weather §3.5 | I |
| Lightning | Rate OCNL 0.5/min, FRQ 3.5/min, CONS 8/min (midpoints of "< 1", "about 1 to 6", "> 6"); at the station for TS, 5–10 NM for VCTS, 10–30 NM on the horizon for `LTG DSNT`, direction from the remark; IC/CC as cloud flashes, CG as bolts | Table 13-7, ALDARS 13.28b (**V**); midpoints and rendering (**I**) | V + I |
| Brightness during flash | Not sourced; tune in QA (**NV**) | — | NV |

### 4.7 Wet surfaces

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| Inputs | precipitation now, `RAB/RAE` times, Prrrr, 6RRRR (`60000` = trace), `P0000` = < 0.01 in | JO 7900.5E 13.29, 13.46–13.49 | V |
| State | `wet` rises toward 1 at a rate ∝ rain rate; `puddle` from accumulated mm minus drainage; drying starts at the `…E mm` time, faster with sun, wind and a large T–Td spread | weather §3.6 | I (constants **NV**: calibrate on owner-approved photo/video sequences) |
| Snapshot/preset start | wet = 1 if precipitation now; 0.5 if it ended in the last hour; else 0 (**I**) | — | I |
| Diffuse darkening | `albedo *= lerp(1, lerp(1, 0.2, porosity), wet)`; asphalt porosity medium (**I**) | Lagarde 2013 (**V**); Nakamae 0.1–0.3 for asphalt (quoted there) | V + I |
| Specular | Wet: slightly smoother normal, higher specular; puddles: flat normal, water F0 = 0.02; drying: specular disappears first, diffuse stays darker | Lagarde 2013 | V |
| Puddle mask | Noise mask on paint-free pavement (no slope data) | weather §3.6 | I |
| Implementation | Dynamic uniforms in the ground and object materials, never a re-bake | weather §3.6 | I |

### 4.8 Wind

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| Direction | METAR wind is **true**; the D-ATIS wind is magnetic (22 of 22 pairs = METAR − 10°, **M**). Never drive visuals from the ATIS | JO 7900.5E 13.10 (**V**) | V + M |
| Windsock extension | 0 at ≤ 3 kt, 1 at ≥ 15 kt, linear between (the shape in between is unspecified) | AC 150/5345-27F §3.2.2 ("fully extend … 15 knots"), §3.5 (moves at 3 kt, ±5°) https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-27F-Wind-Cone.pdf (**V**); linear (**I**) | V + I |
| Gusts | Noise process between ff and G; PK WND as the maximum since the last report; `dddVddd` sector wander; `VRB` slow random; `00000KT` hangs | JO 7900.5E 13.10, 13.22 (**V** bounds); process (**I**) | V + I |
| Water | Existing `world.waterU.uWind` from the METAR wind | code | — |
| Windsock geometry | Size 1: 8 ft × 18 in throat; Size 2: 12 ft × 36 in; fabric white/yellow/orange (SFO colour **NV**); lighted (NASR `WIND_INDCR_FLAG=Y-L`, **V**) | AC 150/5345-27F | V |

### 4.9 Night sky, stars and Moon

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| Natural background | 174 µcd/m² (22.0 mag/arcsec²), ÷ D under cloud (C171 behaviour) | Falchi et al. 2016 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4928945/ | V |
| Artificial zenith luminance | Parameter, default **3 mcd/m²** (Bay Area atlas classes red–pink = 1.07–7.30 mcd/m² total, read coarsely from the published figure); replace with the atlas pixel value once obtained (data CC BY-NC 4.0, attribution) | Falchi Table 1 (**V**), per-pixel value **NV** | I |
| Overcast amplification | × up to 10 for a low deck (BKN/OVC ≤ 5,000 ft) at night; tint = city-light colour (**NV** → parameter) | Kyba et al. 2011 (Berlin ×10.1, ×2.8 at 32 km; **V**); applying it to SFO is **I** | I |
| Stars | takram `stars.bin` (self-hosted), `intensity = 1` physical, optional user "star boost" off by default; hidden under BKN/OVC | WEBGPU.md (**V**); BSC5 terms **NV** | V + NV |
| Moon | Position/phase/limb from ephemeris; NASA CGI Moon Kit texture optional ("NASA's Scientific Visualization Studio" credit) | sun_night §4.1 | V |
| Twilight in fog | Below ~1 SM the civil-twilight sky gradient collapses toward grey, driven by σ | sun_night §7 | I |

### 4.10 Light visibility (Allard's law) — calibrated to the FAA table

Physics: the illuminance at the eye from a point light is E = I·T/d², with T = exp(−∫σ ds) along the path (Allard's
law; Rasmussen 1999 eqs. 22–24, **V**). A light is seen when E ≥ E_T.

**Calibration (M, `tools/env/env_spec_checks.py`).** Using the ASOS σ inversion of §4.3 and one threshold per period,
fitted to AC 70/7460-1N (2026-08-11) Appendix B Table B-1 and the B.3 sentence "When the visibility at night deteriorates
to 1SM, the pilot's ability to see the lights of a structure using 2,000 candela is reduced to 1.2 SM" (**V**,
https://www.faa.gov/documentLibrary/media/Advisory_Circular/2026-07-13_AC_70_7460-1N_Obstruction_Marking_and_Lighting_FINAL_CLEAN.pdf):

| Period | V (SM) | Intensity (cd) | FAA distance (SM) | Model (SM) | Error |
|---|---|---|---|---|---|
| Night, E_T = **6.99×10⁻⁷ lx** | 3 | 1,500 | 2.9 | 2.97 | +2.3 % |
| | 3 | 2,000 | 3.1 | 3.10 | −0.1 % |
| | 3 | 32 | 1.4 | 1.42 | +1.3 % |
| | 1 | 2,000 | 1.2 (B.3) | 1.17 | −2.2 % |
| Day, E_T = **4.12×10⁻⁴ lx** | 1 | 200,000 | 1.5 | 1.52 | +1.1 % |
| | 1 | 100,000 | 1.4 | 1.36 | −3.2 % |
| | 1 | 20,000 | 1.0 | 1.01 | +0.6 % |
| | 3 | 200,000 | 3.0 | 3.08 | +2.8 % |
| | 3 | 100,000 | 2.7 | 2.67 | −1.2 % |
| | 3 | 20,000 | 1.8 | 1.81 | +0.4 % |
| Twilight | 1 | 20,000 | 1.0 to 1.5 | day model 1.01, night model 1.49 | — |
| | 3 | 20,000 | 1.8 to 4.2 | day model 1.81, night model 4.20 | — |

For comparison, σ = 3.0/V gives up to 27 % error (night) and σ = 3.912/V (the app today) 15 % (night) / 12 % (day).

**Rule.** E_T(w) = exp((1 − w)·ln 4.12e-4 + w·ln 6.99e-7) with w = `asosNightW` (the twilight rows span exactly the two
models, so a log blend is the natural reading; **I** on **M**). The same σ field (all slabs of §4.4) is used for the
scene fog and for the lights.

**Cross-check against AIM 2-1-2 (V):** PAPI "visible from about 5 miles during the day and up to 20 miles at night".
Model, clear air (σ ≈ 3.3×10⁻⁵ m⁻¹, the app's own Rayleigh + Mie): 30,000 cd by day → 4.7 SM; night at the 5 % setting
(1,500 cd) → 17.9 SM, at 20 % → 27.6 SM (**M**). Consistent with the coarse AIM statement.

**Examples (M)** — visual range of lights at the controller's steps (§10 presets):

| Preset | σ (m⁻¹) | Light | cd | Range |
|---|---|---|---|---|
| predawn_fog (M1/4SM, night) | 0.0176 | HIRL white, step 4 (25 %) | 2,500 | 536 m |
| | | RCL / TDZ, step 4 | 1,250 | 503 m |
| | | stop bar / REL L-852S | 300 | 438 m |
| | | taxiway edge L-861T (2 cd minimum) | 2 | 228 m |
| ifr_mist_day (¾ SM, day) | 0.0024 | HIRL white, step 5 | 10,000 | 1,186 m |
| night_clear (10SM bound) | ≤ 2.1e-4 | HIRL white, step 1 (0.15 %) | 15 | ≥ 3.3 km |
| | | aircraft nav light (40 cd minimum) | 40 | ≥ 4.6 km |

RVR sanity check: predawn_fog reports R28R/1000V1400FT (305–427 m) while the model sees step-4 edge lights to 536 m. RVR
uses step 5, the pilot's eye geometry and an FAA threshold model not verified here, so only order-of-magnitude
agreement is expected (**NV** for a tighter test).

**Rendering the threshold on a display (I).** A 1–2 px sprite cannot reproduce eye sensitivity through exposure alone.
Per sprite: compute E_eye = I_view·T/d²; draw the HDR sprite pre-exposed as usual (for bloom/halo), and multiply its core
by a visibility factor v = smoothstep(0, 1, log₁₀(E_eye/E_T)/0.3) (fade band = factor 2). Constants are tuned until the
acceptance test A-VIS in §11.2 passes. Fog adds a forward-scatter aureole ∝ I·(1 − T) with angular radius growing with
optical depth (**I**, QA-tuned).

### 4.11 Colours

| Parameter | Rule | Source | Tag |
|---|---|---|---|
| Aviation colours | EB 67D chromaticity boxes; render the area centroid converted to linear sRGB and gamut-clipped (`lighting_spec.json` `colours.*.lin_srgb`: white 1.000/0.614/0.411; green 0/1/0.036; blue 0/0.159/1; yellow 1/0.189/0; red 1/0/0) | FAA EB 67D https://www.faa.gov/sites/faa.gov/files/2024-07/eb_67d_rev.pdf | V (conversion M) |
| Aircraft colours | Same boxes via 14 CFR 25.1397 (aviation red "y is not greater than 0.335; and z is not greater than 0.002") | eCFR | V |
| RWSL red, RGL yellow | ITE traffic-signal colours (46F notes) → use the red/yellow above | AC 150/5345-46F | V + I |
| Obstruction red | "purple boundary y = 0.980 − x, yellow boundary y = 0.335" | AC 150/5345-43J 3.3.3 | V |
| Wide gamut | **Not available in r186 `WebGPURenderer`**: `WebGPUBackend.js` calls `context.configure({device, format, usage, alphaMode, toneMapping})` with no `colorSpace`, and the WebGL fallback backend has no `drawingBufferColorSpace`; only the classic `WebGLRenderer` sets it (`WebGLRenderer.js:3675`). Keep xy in the data for a later Display-P3 path | three 0.186.0 source | M |
| Tone mapping | AgX (engine.md) pushes bright saturated lights toward white. QA must confirm green, red, blue and yellow lights keep their hue in the halo (A-COL, §11.2) | — | I |

---------------------------------------------------------------------------------------------------------------------

## 5. Airfield lighting

### 5.1 Data contract and fixes needed before use

`lighting_fixtures.json` (schema `sfo3d.airfield_lighting_fixtures.v1`): `groups[]` with `system`, `end`, `type`,
`prov`, `emit` (faces: `seen_by` end, `emit_dir` world unit vector [x, z], optional `aim_up_deg`, `toe_in_deg`,
`toe_out_deg`), `n`, `pts`. Edge/centreline points are `[x, z, h, colour_face0, colour_face1]` (W/Y/G/R/B, `-` =
blanked); ALS points carry the station (and the firing order for flashers); PAPI points carry the aiming angle. World
frame: x east, z south, metres from the ARP; `h` above local ground; the ALS light plane is the threshold elevation.

The loader converts each fixture face into one sprite record per frame (the existing `{p, c, i, s, dir, k}` format
consumed by both `js/three/lights.js` `Sprites` and the old sprite shader) with `i` from §5.4.

**Data defects to fix first (regenerate with `tools/env/build_lighting_spec.py`):**

| # | Defect | Fix |
|---|---|---|
| D1 | `rwsl.rel` has 27 entries; the FAA graphic has 28 (taxiway N on 10R/28L between P and the 28L THL); no REL fixtures are expanded | Add N; expand every REL array per AC 150/5340-30J App. G (first light 2 ft before the hold marking, next-to-last 2 ft before the runway edge stripe, last 2 ft beside the RCL, ≥ 6 lights, 12.5–50 ft spacing, 2 ft off the taxiway CL). The runway assignment of the second F1/G/H labels is ambiguous (**NV**): flag them |
| D2 | 28R `piers_observed.far_end_ft` says "> ~2350 ft" | NAIP grid ends ~2,650 ft; pile caps visible to ~2,600 ft (verifier) |
| D3 | Tower `fixture_inferred` cites AC 70/7460-1N §5.5 | §5.6: at least three L-864 at the top; 150–350 ft AGL → a second, steady red level at mid-height (**std**; as-built **NV**) |
| D4 | No taxiway centreline/edge fixtures, no stop bars, no RGLs (SFO lighting per taxiway unpublished) | Keep the current blue edge lights labelled `inf` until the owner answers Q4 (§5.9) |

### 5.2 Per-runway-end light lists for SFO

Counts are fixtures in `lighting_fixtures.json` (**M**, regenerated by the verifier); facts per end are in
`lighting_spec.json` `runways[].ends[<end>]`. Runway-wide systems (edge, centreline) are listed once per runway.

| Runway (length × 200 ft, HIRL, CL) | Edge lights | Centreline lights |
|---|---|---|
| 10L/28R, 11,870 ft | 118 L-862 (L-850C on crossing pavement), 197.83 ft spacing; faces: 10L W 98 / Y 20; 28R W 96 / Y 20 / **R 2** (displaced area) | 235 L-850A; 10L W 196 / R 39; 28R W 191 / R 39 / blanked 5 |
| 10R/28L, 11,381 ft | 112, 199.67 ft; 10R W 92 / Y 20; 28L W 90 / Y 20 / R 2 | 226; 10R W 187 / R 39; 28L W 182 / R 39 / blanked 5 |
| 1L/19R, 7,650 ft | 76, 196.15 ft; 1L W 70 / **R 6**; 19R W 56 / Y 20 (no caution zone toward 1L: no IAP) | 151; 1L W 100 / R 39 / blanked 12; 19R W 112 / R 39 |
| 1R/19L, 8,650 ft | 86, 196.59 ft; 1R W 82 / R 4; 19L W 66 / Y 20 | 171; 1R W 122 / R 39 / blanked 10; 19L W 132 / R 39 |

Edge lateral 110 ft from the CL (10 ft outside the pavement, **std/inf**); RCL on all four runways follows CS + NASR
(conflict C1 with the AD note "TDZL/RCLS Rwys 19L and 28R": owner Q3).

| End | Displaced thr | Approach lights (pub) | Other systems (fixtures) | PAPI (pub angle / TCH; **obs** distance from thr, lateral) | Plate GP / TCH | Caution zone seen from this end | THL |
|---|---|---|---|---|---|---|---|
| **28R** | 300 ft | **ALSF-2** (SSALR mode): 120 CL-bar + 54 red side-row + 8 (500-ft bar) + 16 (1000-ft bar) + 59 green thr + 15 SFL = 272 | red end bar 8 at pavement end; green wing bars 8; **TDZ 180** | 3.00° / 68 ft; **1,369 ft** (TCH/tan gives 1,298: +71 ft), 173–264 ft left | ILS 3.00 / 55 (CAT II/III) | 2,000 ft (instrument) | 32 |
| **28L** | 300 ft | **MALSR**: 35 CL-bar + 10 (1000-ft crossbar) + 23 green thr + 5 RAIL = 73 | red end 8; wing bars 8 | **2.85°** / 67 ft; **1,369 ft** (+23), 173–263 ft | ILS 2.85 / 53 (SA CAT II) | 2,000 ft | 32 |
| **19L** | 0 | **MALSF**: 35 + 10 + 23 + 3 SFL = 71 | threshold/end 8 (G to 19L, R to 1R); **TDZ 180** | 3.00° / 71 ft; **1,344 ft** (−11), 161–251 ft | ILS 3.00 / 55 | 2,000 ft | — |
| **19R** | 0 | none | threshold/end 8 | **3.15°** / 58 ft; **1,023 ft** (−31), 176–266 ft | RNAV GP 3.15 / 55 | 2,000 ft | — |
| **10L** | 0 | none | threshold/end 8; **REIL 2** | 3.00° / 80 ft; **1,556 ft** (+30), 177–268 ft | RNAV GP 3.00 / 55 | 2,000 ft | 32 |
| **10R** | 0 | none | threshold/end 8 | 3.00° / 68 ft; **1,298 ft** (0), 157–248 ft | RNAV 3.00 / 60 | 2,000 ft | 32 |
| **1L** | 640 ft | none | red end 8; wing bars 8; **REIL 2** | none | no IAP | none (visual) | 32 |
| **1R** | 560 ft | none | red end 8; wing bars 8; **REIL 2** | none | no IAP | none | 32 |

Totals: edge 392, RCL 783, TDZ 360, threshold/end/wing 96, ALS 416, PAPI 24, REIL 6, THL 192 = **2,269**. Not yet in the
fixtures: REL arrays (28 entrances, D1), obstruction lights (43 DOF obstacles in `obstructions[]`), apron masts (54 in
`apron_masts[]`), beacon (position unknown), windsocks (positions unknown), taxiway lights (D4).

PAPI aiming (JO 6850.2C Table 5-2, **V**): standard +30′/+10′/−10′/−30′ or height-group 4 +35′/+15′/−15′/−35′ about the
published angle, LHA 1 nearest the runway. SFO's set is **NV**; default HG4 (all six ends have a published GPA and HG4
traffic, **I**). Both sets are in the JSON (`aiming_deg_std`, `aiming_deg_hg4`).

### 5.3 Lighting controller (JO 7110.65BB §3-4; https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_4.html)

Inputs: `towerNight`, prevailing visibility V (SM; `M` values reduced by 1 %), RVR 28R (lowest reported, ft), ceiling
(ft), runway configuration (§3.5), traffic phases (RWSL). Step → % tables: HIRL/RCL/TDZ/taxiway 5-step
100/25/5/1.2/0.15 % (AC 150/5340-30J 2.6.4.1); ALSF-2 steady 100/20/4/0.8/0.16 %, ALSF-2 flashers 100/20/2.3 %
(steady steps 4–5 → high, 3 → medium, 1–2 → low); MALS steady 100/20/4 %, MALS flashers 100/10/2.3 % (JO 6850.2C
Table 2-3; the 1:1 MALS step → flasher step mapping is **I**). SFO facility directives may override all of this (**NV**).

| System | On | Step by day (visibility SM) | Step at night | Source |
|---|---|---|---|---|
| HIRL + RCL + TDZL (runways in use) | Night: departures before taxi onto the runway; arrivals from final approach (IFR) or entering the surface area (VFR) until off the runway. Day: when surface visibility < 2 SM | 5: < 1; 4: 1–< 2 (3: 2–< 3, only if lit for other reasons) | 4: < 1; 3: 1–< 3; **2: 3–5 inclusive**; 1: > 5 | 3-4-10, 3-4-11, TBL 3-4-8 ("*and/or appropriate RVR equivalent": RVR conversion not given → visibility only, **I**) |
| ALS (28R, 28L, 19L) | Night: serves the landing runway (or an approach to it). Day: ceiling < 1,000 ft or visibility ≤ 5 SM and approaches are being made | ALSF-2 (TBL 3-4-5): 5: < 1 or RVR ≤ 6,000; 4: 1–< 3; 3: 3–< 5; 2: 5–< 7; **≥ 7 with a low ceiling: 2** (TBL NOTE, **I**) | ALSF-2: 3: < 1 or RVR ≤ 6,000; 2: 1–3; 1: > 3 ("use step 4 or 5 only when requested") | 3-4-5, 3-4-6 |
| 28R mode | **ALSF-2** when visibility ≤ ¾ SM or RVR ≤ 4,000 ft; otherwise **SSALR** (no red side rows, no 500-ft bar, bars every 200 ft to 1,400 ft, 70-ft crossbar, RAIL 1,600–2,400 ft) | | | 3-4-9; JO 6850.2C 200c |
| MALSR 28L, MALSF 19L | as ALS | 3-step TBL 3-4-7: 3: < 2; 2: 2–5; **> 5 with a low ceiling: 2** (**I**) | 3: < 1; 2: 1–< 3; 1: ≥ 3 | 3-4-8. **New open point:** if SFO's MALSR is controlled through the HIRL, 3-4-12 / TBL 3-4-9 applies instead (same breakpoints as TBL 3-4-8). Wiring **NV** (Q10) |
| Sequenced flashers (all three ALS) | Only when visibility < 3 SM **and** instrument approaches to that runway; never with the ALS off | follow the steady step (mapping above) | same | 3-4-7 |
| REIL (10L, 1L, 1R) | "When the associated runway lights are lighted"; off after the arrival has landed / the departure has left the pattern (end in use, **I**) | TBL 3-4-1: 3: < 2; 2: 2–5 | 3: < 1; 2: 1–< 3; 1: ≥ 3 | 3-4-2 |
| PAPI (all six) | Continuous (the FAA standard photo-electric type; SFO's control type **NV**) | day mode 100 % | night mode: 20 % default of the selectable 5 %/20 % (**I**; Q6) | 3-4-4; AC 150/5345-28H 3.3.6–3.3.8 |
| Taxiway lights | Night; day when visibility < 1 SM | 5-step TBL 3-4-12: 5: < 1 | 4: < 1; 3: ≥ 1 | 3-4-16 |
| Rotating beacon | Night; day when ceiling < 1,000 ft or visibility < 3 SM | — | — | 3-4-18 + 14 CFR 91.155(c),(d)(1). **Not drawn** until located (Q1) |
| Obstruction lights | Photocell (§4.2); tower rule "between sunset and sunrise" if controls exist | — | — | 3-4-17; AC 70/7460-1N 5.3 |
| RWSL (REL, THL) | Continuous, automatic intensity; activation from traffic (below) | — | — | 3-4-19 |
| Lighted wind cone | Night, constant | — | — | AC 150/5340-30J 6.6 |
| Stop bars, RGLs, clearance bars | Not drawn: SFO use unpublished (Q4); stop bars are "required for operations below 600 ft (183 m) RVR" | — | — | 4.1.3.3 |

**RWSL activation (AIM 2-1-6, V).** RELs on a runway light when a departure on it passes ~30 kt, or an arrival is ~1 mile
from the threshold; each intersection's REL goes out ~3–4 s before the aircraft reaches it; for arrivals, below ~80 kt
all arrays not within 30 s of the forward path go out, and at ~34 kt ("taxi state") all go out; after the departure is
"airborne", all go out. THLs light only when an aircraft is in position or rolling **and** another aircraft or vehicle is
on or about to enter the runway ahead; they start 375 ft "from the departure threshold" (this supports the spec's
runway-end reference at displaced ends, **I**) and run 1,500 ft (32 lights). Inputs: `traffic` phases (`lineup`,
`takeoff`, `final`, `flare`, `rollout`, `taxi`), ground speed and runway-relative position.

**Reference implementation and test vectors.** `tools/env/env_spec_checks.py` `controller()` implements the table
above; `tools/env/fixtures/env_presets.json` holds its output for the 14 presets of §10. The JS controller must
reproduce those outputs exactly (test A-CTL).

### 5.4 Photometry → sprite intensity

I_view = cd(type, colour) × pct(step)/100 × B(θ_h, θ_v) × k_cd, then the attenuation and threshold of §4.10.

| Term | Rule | Source | Tag |
|---|---|---|---|
| cd(type, colour) | Minimum average main-beam intensity per fixture type and colour, e.g. L-862 W 10,000 / Y 5,000 / G 2,500 / R 2,000; L-850A W 5,000 / R 750; L-850B 5,000; L-850T R 1,500; L-852S R 300; L-852G Y 1,000; L-861T B ≥ 2; L-804 Y 3,000 (`lighting_spec.json` `fixtures`) | AC 150/5345-46F Tables 3-1/3-2/3-3 | V |
| k_cd | 1.0 default; the spec allows the average up to 3× the minimum ("at most 3×", §3.3). Calibrate within [1, 3] against owner night photos | 46F §3.3 (**V** bound), value (**I**) | I |
| B (beam) | 1 inside the main-beam ellipse (H × V limits); log-linear fall to 0.1 at the 10 % curve; 0 outside (L-862: plus ≥ 50 cd white omnidirectional to 15° elevation). Toe-in/out and aim-up from the fixture face | 46F tables (**V** limits); interpolation (**I**) | V + I |
| PAPI | White above / red below each LHA's aiming angle; transition 3′ wide at beam centre, 5′ at the edges; isocandela stadiums 30,000 cd (W) / 15,000 (R) within ±2°, 20,000/10,000 to ±4°×±2.5°, 14,000/7,000 to ±6°×±3°, 8,000/4,000 to ±8°×±3.5°, 5,000/2,500 to ±10°×±4°; LED units emit only within ±10.5° azimuth | AC 150/5345-28H Fig 3-1, §3.2.1 (**V**, contours read ±0.25°); JO 6850.2C 504b | V |
| ALS steady lamps | Intensity **NV** (FAA-E-2408 Q20A/PAR-56 300 W; 12° vertical spread, JO 6850.2C 206a). Provisional: I = L-862 white × pct (**I**, flagged "photometry NV" in QA); do not use the unverified vendor figure (~38,000 cd) as data | JO 6850.2C 204–206 | NV |
| ALS aiming | JO 6850.2C Table 2-1 (ALSF-2, 6.1° at the threshold → 7.6° at 2,400 ft for 3°; shift by GS − 3°; 6–9° limits) and Table 2-2 (MALS 3.1° → 3.7°; 28L −0.15°); flashers 6° (per-station values in `als_detail.elevation_setting_deg`) | JO 6850.2C 206, Fig 2-10 | V |
| Sequenced flashers | Bluish-white, each flasher twice per second, sequence from the outermost toward the threshold. Effective intensity **NV** (FAA-E-2998/2689 not obtained); timing within the 0.5 s cycle: equal spacing (**I**) | JO 6850.2C 200b, 200e–f | V + NV |
| REIL | Two units flash in sync (≤ 20 ms), 120 fpm (unidirectional styles) or 60 fpm (omni); style E effective 15,000 / 1,500 / 300 cd in 30° × 10°, aimed 10° up and toed out 15°; SFO style **NV** (Q5) | AC 150/5345-51B §3.4, Table 1; JO 6850.2C 402a | V + NV |
| L-864 (tower top) | 2,000 cd effective ±25 %, 30 ± 3 fpm red; L-810 32.5 cd steady red | AC 150/5345-43J 3.4.1.2, 3.4.1.5 | V |
| Flash rendering | Blondel–Rey: a flash drawn for n frames of t_f is perceived as I_f·n·t_f/(0.2 + n·t_f). Solve I_f for the target effective intensity at the **actual** frame time (400 cd eff → 5,200 cd for 1 frame at 60 Hz, 2,800 cd for 2 frames) | 14 CFR 25.1401(e) | V |
| Beacon (L-802A) | 24 fpm alternating white/green, white ≥ 75,000 cd effective at 3–7°, green ≥ 0.15 × white | AC 150/5345-12F; conflict C3 resolved at 24 fpm | V (position **NV**) |

### 5.5 Threshold, displaced threshold and runway end (std, geometry in the fixtures)

Standard threshold: two groups of 4 split green/red fixtures on 10-ft centres, outermost in line with the edge lights
(±80…±110 ft). Displaced thresholds (28L, 28R, 1L, 1R): green wing bars outboard (±110…±140 ft), red-only end lights at
the pavement end, edge lights red toward the approach and yellow toward rollout in the displaced area, centreline
blanked toward the approach (displacements ≤ 700 ft) (AC 150/5340-30J 2.3.2, 3.3.1.3.1, Fig A-5/A-9; **std**).
ALS threshold bars exist only at 28R (59 green), 28L and 19L (23 each).

### 5.6 Approach-light structures (obs) and light plane

- Light plane: one horizontal plane at the threshold centreline elevation (JO 6850.2C 201a, **V**): y = `GROUND_Y` +
  (threshold elevation − field elevation) × 0.3048 (28R/28L thresholds 12.9 ft NAVD88 vs field 13.1 ft; < 0.1 m).
- Piers as geometry (NAIP 2024, **obs**, verified): 28R from the shoreline (~650 ft out) with 7 crossmembers ~110 ft wide
  at 700–1,300 ft, pile caps every 100 ft to ~2,600 ft, platforms at ~1,150 and ~1,390 ft; 28L crossmembers at 1,000 ft
  (~82 ft) and 1,300 ft (~103 ft), pile caps to > 3,000 ft; 19L pier ~500–1,400 ft with crossmembers at ~1,000 and
  ~1,200 ft; 19R none. Semiflush lights on paved areas before the shoreline (JO 6850.2C 203a).
- Which stations are lit on the piers is **NV** (Q2): lights at FAA stations from the landing threshold (FAA rule + the
  2013 SFO memo that both 28-end ALS were reworked for the relocated thresholds).
- Replaces `buildPierGeometry` (a generic post + crossbar per station at `GROUND_Y + 0.8`).

### 5.7 Apron floodlights

- Poles: the 54 DOF poles 60–157 ft AGL within 3 km (`apron_masts[]`, accuracy 1A ±20 ft H / ±3 ft V, public domain);
  28 coincide with OSM lighting masts (only a boolean is stored, ODbL-safe). They replace the procedural masts in
  `data/sfo_details.js` (roughly 120 m spacing, inferred).
- Photometry, aiming and lamp type: **NV** (no SFO or FAA public source; current guidance AC 150/5360-13A §7.5 gives no
  numbers). Model: per pole, a downward asymmetric flood toward the nearest apron, luminous output calibrated so that the
  mean apron illuminance is ~54 lx (cancelled 1988 AC table: "historical, order of magnitude only") (**I**).
- Ground lighting: bake the floodlight illuminance field from the real pole positions into a night light map (replaces
  the hash-grid "pools" every 90 m in `js/three/ground.js` `nightLight`), exposure anchor EV100 ≈ 4.6–5.6 (54 lx on 18 %
  grey / concrete 0.35).
- Colour temperature: parameter per pole, value **unknown**. Do not choose sodium-orange or LED-white; night apron views
  are a release gate until the owner supplies photos (Q7).
- Terminal glazing glow: L ≈ E_int × ρ_int/π × τ_glass (e.g. 300 lx × 0.5/π × 0.5 ≈ 24 cd/m², **I**); jet-bridge
  floodlights per the Oshkosh sell sheet ("Three floodlights … A sealed dual fluorescent tube 4'0" fixture", **V** for the
  product, SFO fleet **NV**); **remove the amber bridge beacon** unless a photo or SFO spec shows one (**NV**).

### 5.8 Obstruction lights

43 lighted DOF obstacles within 4.5 km (`obstructions[]`). ≤ 150 ft AGL: steady red L-810 (double at the top). The
control tower (245 ft AGL, DOF lighting "R"): AC 70/7460-1N §5.6 (≥ 3 L-864 flashing red at the top, steady red second
level at mid-height), placed on the tower model's top (the DOF 4D accuracy ±250 ft is too coarse; **std**, as-built
**NV**). Apron poles: DOF lighting "U" (49) / "N" (5): no red lights asserted.

### 5.9 Taxiway lighting

SFO per-taxiway lighting is not published (Q4). Until answered: keep the current blue edge lights of
`js/live/lights.js` (outline-derived, labelled `inf` in the QA overlay); add no green centreline lights, stop bars or RGLs.
X-Plane community data (837 green CL segments, 732 blue edge, 108 amber hold, 81 alternating) is a cross-check only,
not a data source (licence and accuracy not established).

### 5.10 Windsocks and beacon

Positions are unpublished (OSM has one windsock; X-Plane lists 8). Survey them on NAIP 2024 (cone 8–12 ft, lit) with
X-Plane/OSM only as locators, as done for the PAPIs; draw only surveyed ones (**obs**). The beacon is not drawn until
located (Q1).

---------------------------------------------------------------------------------------------------------------------

## 6. Aircraft lights (14 CFR 25.1385–25.1401, 91.209; AIM 4-3-24 "Effective 7/9/2026, Change 3")

| Light | Geometry and photometry | When on (traffic phase) | Tag |
|---|---|---|---|
| Position (nav) | Red left / green right, each visible 0–110° from dead ahead; white aft ±70° about the tail axis. Minimum horizontal intensity 40 cd (0–10°), 30 cd (10–20°), 5 cd (20–110°); rear white 20 cd; vertical factors 1.00/0.90/0.80/0.70/0.50/0.30/0.10/0.05 at 0/0–5/5–10/10–15/15–20/20–30/30–40/40–90°; overlap maxima per 25.1395. Default = 2 × minima (**I**) | Sunset–sunrise when operated (91.209(a)(1)); before taxi (AIM). Parked at a floodlit gate with the beacon off: off by default (91.209(a)(2) "clearly illuminated" suffices; owner decides, Q11) | V + I |
| Anti-collision (red beacons, white strobes) | 40–100 flashes/min; ≥ 400 cd effective at 0–5°, 240 / 80 / 40 / 20 cd at 5–10 / 10–20 / 20–30 / 30–75°; ±75° vertical coverage; flash drawn via Blondel–Rey at the real frame time (§5.4). Current rates (strobe 66/min double, beacon 60/min) comply | Beacon: engines running (from pushback/start); strobes: entering the departure runway (line up) until vacating, and on runway crossings (AIM "all exterior lights … when taxiing on or across any runway", **I** for strobes) | V |
| Logo | Not regulated photometrically: parameter (**NV**) | Before taxi until parked (AIM) | V + NV |
| Taxi | Not regulated: parameter (**NV**) | Moving on the ground; **off when stopped or holding** (AIM) | V |
| Landing | Example Honeywell LED 770,000 cd, 15° × 16° (737NG/757/767/777; other types **NV**) | Take-off roll (proxy for "takeoff clearance"), and below 10,000 ft (3,048 m; the app uses 3,000 m) in flight | V |
| Wing / runway turn-off | **NV** (airline SOPs not public) | — | NV |
| Colours | 25.1397 boxes = EB 67D (§4.11); replace `[1,0.06,0.04]` / `[0.1,1,0.3]` | | V |
| Rendering | Directional sprites with the sector function (not omni); landing/taxi lights also as a few real `SpotLight`s (cd) for the nearest/selected aircraft only (budget per tier, **I**) | | I |

---------------------------------------------------------------------------------------------------------------------

## 7. Rendering in the new three.js r186 renderer (`js/three/**`)

### 7.1 Sky and atmosphere

- **Primary: @takram/three-atmosphere 0.19.1, `/webgpu` entry only** (MIT; BSD-3 Bruneton/INRIA, MIT Epic Games and
  Apache-2.0 Intel notices; 84.4 KB minified / 25.3 KB gzip tree-shaken). Use `skyBackground`, `aerialPerspective`,
  `AtmosphereLight`, `SkyEnvironmentNode`. Drive `sunDirectionECEF`/`moonDirectionECEF` from `ephemeris.mjs` via ENU at
  the ARP (x_east → E, y → U, z_south → −N); stars with Rz(GAST). Self-host `assets/stars.bin` (90,960 B; the default URL
  is media.githubusercontent.com, blocked by the artifact CSP). Ship the repository LICENSE (the npm tarball has none)
  and the notices in `docs/ATTRIBUTION.md`.
- **Gate:** a GPU render test on desktop and on the owner's iPhone (the package deep-imports
  `three/src/nodes/core/NodeUtils.js`; never run on a GPU here). Owner approval of the dependency (Q12).
- **Fallback:** keep `js/three/sky.js` (single-scattering precompute) and add the Moon disc, stars and the night-sky
  floor of §4.9.
- Clear-air haze = takram aerial perspective; METAR fog is a separate extinction term (§7.3).

### 7.2 Sun, lights and units

- Sun: `DirectionalLight` intensity = direct-beam illuminance normal to the beam (lux; three's lux unit is inferred from
  the code, sun_night §6.1). With takram, `AtmosphereLight` supplies sun + sky irradiance. With the fallback sky,
  calibrate the relative `sunI` so that the global horizontal illuminance equals Circular 171 (**I**; test A-EXP).
- Cloud transmittance multiplies the sun (product over layers along the sun ray) and shadows come from each layer's
  coverage map (extend `cloudShadow` to N layers).
- Point lights: sprites via `js/three/lights.js` `Sprites` (instanced additive billboards, max 24,000). Extend the
  instance data with the beam ellipse, toe/aim and a flash phase so B(θ) is evaluated on the GPU (**I**); CPU evaluation
  of ~2,500 fixtures per frame is the fallback.
- Pre-exposure: multiply every emitter (sun, sky luminance scale, sprites, emissive glazing, floodlight map) by the
  current exposure before shading, so RGBA16F never overflows (Filament; the Sun is ~1.6×10⁹ cd/m² vs the half-float max
  65,504).

### 7.3 Fog and cloud slabs

Replace `Sky.fogNode()` (single exponential `a·exp(−b·h)`, `uFog.y = 1/700`, capped) with the piecewise-constant σ(y)
of §4.4: the optical depth along a view ray is Σ σ_i × (path length inside slab i), exact and cheap. In-scatter colour =
ambient sky irradiance (+ Mie sun glow) × (1 − T). Horizontal modulation: BCFG/PRFG noise mask, sector lobes, `FG IN
GAP` horizon bank. Lights use the same optical depth (§4.10). Inside a cloud slab (camera on approach through the deck)
the visual range falls to 40–120 m.

### 7.4 Clouds

N layers (all reported, up to 6; `CLR` above 12,000 ft ignored) as TSL slab materials (the existing `cloudSlabMaterial`
takes one layer). Per layer: base, thickness, own coverage (noise threshold), drift. r186 `SkyMesh`'s built-in 2-D
clouds (`cloudCoverage/Density/Elevation/Scale/Speed`) are an option for high thin layers only. Night: underside lit by
the artificial sky term (§4.9).

### 7.5 Precipitation and lightning

GPU particles (compute on WebGPU; instanced quads with a time-driven vertex shader on WebGL2) in a camera-attached box
(~40 m radius, **I**). Counts from §4.6 scaled to a tier budget (**I**: high 60k, medium 30k, low 12k), streaks
v × 1/60 s, wind slant from the METAR wind, splash sprites on pavement; drizzle as fine non-streaking points. Lightning:
cloud-illumination bursts (and bolts for CG) at the §4.6 rate and direction, brief global sky/ambient boost.

### 7.6 Wet surfaces

`uWet`, `uPuddle` in the ground and object node materials (Lagarde, §4.7); puddles reflect via SSR (high tier) or the
PMREM environment (others).

### 7.7 Performance gates (engine.md phase gates, unchanged)

≥ 30 fps at the mobile tier (snapshot traffic, all airfield lights, rain on) and ≥ 60 fps on a desktop GPU; no context
loss over 10 minutes.

---------------------------------------------------------------------------------------------------------------------

## 8. Exposure and tone mapping

| Step | Rule | Source | Tag |
|---|---|---|---|
| Units | Physical throughout: lux (sun/sky), cd (all lamps: airfield from `lighting_spec.json`, aircraft from §6), cd/m² (sky, glazing) | sun_night §6.3 | V (units) |
| EV100 | EV100 = log₂(L_avg·100/12.5); exposure = 1/(1.2·2^EV100) | Frostbite §4.3/§5.1 (K = 12.5) | V |
| Targets (18 % grey, clear) | noon 15.3; snapshot 15.0; marine layer 12.0; sunset 8.8; −4° 3.5; civil dusk 0.5; floodlit apron (54 lx) 4.6; full Moon −3.5 | Circular 171 + EV formula (**M**, `env_presets.json`) | M |
| Metering | Log-luminance mip chain (WebGL2) or 64-bin histogram (WebGPU); centre-weighted; exclude top 2 % and bottom 50 % | Filament "Automatic exposure" | V method, I params |
| Clamp | EV100 ∈ [2, 16] plus a compensation curve darkening below Sun −4°, so night stays night and lights bloom | sun_night §6.3 | I (QA-tuned) |
| Adaptation | L_avg += (L − L_avg)(1 − e^(−Δt·τ)), τ ≈ 1–2 s brightening, 3–4 s darkening; snap on camera cuts and view presets | Filament / Pattanaik 2000 | V form, I τ |
| Tone map | AgX + the existing grade (saturation 1.1, contrast 1.35 at pivot 0.45; `js/three/engine.js`) | engine.md | — |
| Night look | "Photographic" default; optional "eye-like" (Thompson et al. 2002 blue shift, desaturation) below EV 0, off by default (Q13) | sun_night §6.3 | I |
| Replaces | `app.js:146–148` (`nightF`, `dark`, exposure 0.45 → 2.4) and `renderer3.js` `post.exposure ?? 0.45` | code | M |

---------------------------------------------------------------------------------------------------------------------

## 9. Current renderer: the cheap subset

### 9.1 Do in the current renderer (shared core, small adapters)

1. `js/env/*` core (§3) replaces `parseMetar`, `lightDate`, `solarPosition`, `nightF`/`dark`/exposure in `app.js`
   `applyEnv`.
2. Fog: feed σ_surface and the fog top into the existing `uFog` (a = σ, b = 1/top) and **remove both caps**. The
   three-slab profile, sectors and patches are new-renderer only.
3. Clouds: use the de-summed coverage and the real base of the lowest BKN/OVC layer ≤ 5,000 ft (today the coverage map
   `COVER` treats amounts as independent); more layers only in the new renderer.
4. Airfield lights: replace `buildAirfieldLights` with the fixture loader + controller; the sprite records are the same
   format, so both renderers benefit. The old sprite shader gets the visibility factor of §4.10 (CPU-side is fine).
5. Aircraft light logic (§6) in `app.js` `syncViews` and `fleet.js` colours.
6. Exposure from the EV100 target (CPU; no histogram).
7. A wetness darkening uniform in the ground shader (diffuse only) is optional.

Not in the current renderer: takram sky, stars/Moon, N-layer clouds with shadows, GPU rain, puddle reflections,
histogram auto-exposure.

### 9.2 `js/anim/lights.js` defects fixed by moving to the fixture data (airfield §12)

| # | Today | Becomes |
|---|---|---|
| 1 | Edge lights all white, 60.96 m from the runway start, 1 m outside the pavement | Per-face W/Y/R with the caution zone and displaced areas, 110 ft from the CL, spacings of §5.2 |
| 2 | RCL red/white within 300 m of either end, reverse face white, first light at 15 m | Per-direction coding (white; alternating 3,000–1,000 ft remaining; red last 1,000 ft), blanked toward the approach in displaced areas |
| 3 | 19 green + 19 red lights at 3.2 m at every end | 8 split G/R (4 per side, 10 ft), wing bars and red end bars at displaced ends, ALS threshold bars only at 28R/28L/19L |
| 4 | TDZ 30–900 m | 100–3,000 ft, 36 ft from the CL, 4° toe-in |
| 5 | PAPI at TCH/tan (28R 22 m off), 15 m + j·9 m, ±30′/±10′ | Observed LHA positions; HG4 aiming (default); 3′ transition |
| 6 | Same 8-per-side 1000-ft bar for MALSR/MALSF; no 500-ft bar, no threshold bars, no SSALR; all at `GROUND_Y + 1.4 m` | MALS 66-ft crossbar; ALSF-2 500-ft bar; green threshold bars; SSALR ↔ ALSF-2 switch; light plane at threshold elevation |
| 7 | Rabbit always on at night | Only when visibility < 3 SM with instrument approaches and the ALS on |
| 8 | Arbitrary intensities (`i: 30`, `60`, `900` …) | cd × step % × beam (§5.4) |
| 9 | Sparse blue edge lights every 45 m on every taxiway | Outline-derived blue edges kept as `inf` (§5.9) |
| 10 | No REIL, RWSL, beacon, obstruction lights; procedural masts | REIL (10L/1L/1R), RWSL THL + REL, obstruction lights (DOF), DOF masts; beacon when located |

---------------------------------------------------------------------------------------------------------------------

## 10. Real-weather presets (QA views, artifact menu, test vectors)

All presets are real KSFO reports: IEM ASOS archive (public domain, attribution appreciated;
`tools/env/fixtures/ksfo_archive_wx.txt`) or the aviationweather.gov API (US Government work;
`refs/cache/weather/metar_json_120h.json`). Sun/Moon from `ephemeris.mjs` (**T**); weather from `render_params` (**M**);
lights from the reference controller (**M**). Full records, including cloud layers, precipitation, wind and every
controller output: `tools/env/fixtures/env_presets.json`. The runway configuration is an **input** (stated in the JSON),
not an observation, except where noted.

| Preset | t_env (UTC) | Report | Sun el / phase | Moon | E (lx), D | EV100 | σ (m⁻¹) | Key light states (controller) |
|---|---|---|---|---|---|---|---|---|
| dawn | 2026-09-24 13:40 | `241256Z 23003KT 10SM FEW200` | −3.98° civil | below | 12.8, 1.0 | 2.6 | 1.96e-4 (w 0.52) | tower night: HIRL step 1, SSALR 28R step 1, MALSR 28L step 1, no SFL, PAPI night, floods on |
| noon | 2026-09-24 20:02 | `241956Z 35008KT 10SM SCT200` | +51.68° day | below | 8.7e4, 1.05 | 15.3 | ≤ 1.8e-4 | all runway lights off; PAPI day 100 %; beacon off |
| dusk | 2026-09-24 02:30 | `240156Z 29013KT 10SM FEW200` | −5.23° civil (civil dusk 02:30:39) | 18.9°, 93 % | 3.46, 1.0 | 0.7 | ≤ 2.1e-4 | as dawn; windsock 0.83 |
| night_clear | 2026-09-24 06:56 | `240656Z 29005KT 10SM CLR` | −49.3° night | 40.0°, 93 % | 0.070, 1.0 | −5.0 | ≤ 2.1e-4 | HIRL step 1 (0.15 %), SSALR step 1 |
| snapshot | 2026-09-23 17:51 | `SPECI 231722Z 09004KT 10SM FEW004 SCT008` | +41.59° day | below | 7.1e4, 1.05 | 15.0 | ≤ 1.8e-4 | all off except PAPI/RWSL |
| marine_layer (low ceiling, day) | 2026-09-23 15:56 | `231556Z 14005KT 10SM FEW003 OVC005` | +22.1° day | below | 8.7e3, 4.0 | 12.0 | ≤ 1.8e-4 | ceiling 500 ft → ALS on by day: SSALR step 2 (0.8 %), MALSR step 2; HIRL off (vis ≥ 2); beacon on (below basic VFR) |
| low_ceiling_night | 2026-09-23 04:56 | `230456Z 30008KT 10SM FEW006 BKN010` | −32.5° night | 34.9°, 87 % | 0.032, 1.39 | −6.1 | ≤ 2.1e-4 | HIRL step 1; overcast sky-glow amplification |
| predawn_fog | 2025-11-08 13:56 | `081356Z 20003KT M1/4SM R28R/1000V1400FT FG VV002` | −8.96° nautical | 50.6°, 87 % (hidden) | 0.031, 4.0 | −6.1 | 1.76e-2 | HIRL/TDZ step 4 (25 %); **28R ALSF-2** step 3 + SFL 20 %; MALSR step 3 + RAIL; REIL 1L/1R high |
| night_fog | 2025-01-07 09:39 | `070939Z 00000KT M1/4SM R28R/1600V3000FT FG BKN000` | −65.8° night | below | 3.6e-4, 1.39 | −12.6 | 1.76e-2 | as predawn_fog (RVR 1,600 ≤ 4,000 → ALSF-2) |
| ifr_mist_day | 2025-11-08 17:03 | `081703Z 03005KT 3/4SM R28R/3500VP6000FT BR BKN002 OVC004` | +22.5° day | 15.8° | 8.9e3, 4.0 | 12.0 | 2.4e-3 | day < 1 SM: HIRL step 5; ALSF-2 (RVR 3,500) step 5 + SFL high; taxiway step 5 |
| rain_day | 2026-04-10 19:15 | `101915Z 18005KT 3/4SM R28R/2200VP6000FT +RA BR FEW006 BKN015 OVC048 … P0010` | +58.0° day | 2.7° | 2.5e4, 4.0 | 13.5 | 2.4e-3 | +RA 8.0 mm/h (Prrrr, 19 min); input config: arrive 19L (ILS) → MALSF step 3 + SFL; HIRL step 5 |
| squall_night | 2025-12-25 10:56 | `251056Z 22036G63KT 2SM … +RA BR SQ … PK WND 23063/1053 … P0016` | −51.2° night | below | 1.3e-4, 4.0 | −14.1 | 1.55e-3 | Prrrr 4.06 mm/h clamped to the heavy class (`rate_mm_h_spec` 7.62); windsock full; input config 19L: MALSF step 2 + SFL 10 %; HIRL step 3 |
| ts_evening | 2026-02-18 03:20 | `SPECI 180320Z COR 28012G23KT 8SM -TSRA SCT029 BKN044CB OVC080 … FRQ LTGICCCCG SE VCTS` | −17.6° night | below | 5.1e-5, 10 | −15.4 | 2.8e-4 | lightning FRQ (3.5/min) to the SE; HIRL step 1, SSALR |
| drizzle_night | 2026-05-26 10:21 | `261021Z 25008KT 2 1/2SM -DZ BR FEW005 BKN016 OVC027` | −22.6° night | below | 1.3e-4, 4.0 | −14.1 | 1.19e-3 | drizzle mist; HIRL step 3; SSALR step 2 + SFL low (vis < 3) |

EV100 here is the natural-light target before the clamp of §8; at night the clamp (≥ 2) and artificial light set the
actual exposure.

---------------------------------------------------------------------------------------------------------------------

## 11. QA views and acceptance criteria

### 11.1 Harness additions (proposed)

- Query parameters: `?t=<ISO UTC>` (environment time), `?wx=<preset id>` or `?metar=<url-encoded raw>`,
  `?rwy=arr:28L,28R;dep:1L,1R` (runway-config override), `?qa=prov` (provenance overlay), `?qa=env` (EnvState HUD).
  Passed through `QS=` of `jobs/qa3.mjs`.
- View kinds in `jobs/qa3.mjs` (today: gate, look, view, tower, hold, ac): add `thr:<end>,<dist>,<pitch>` (maps to the
  existing `SFO.qa.threshold`), `papi:<end>,<pitch>,<dist>` (target = LHA row centre, yaw = approach bearing) and
  `lighttest:<cd>,<visSM>,<day|night>,<distSM>` (a synthetic scene with one light and one black target, §11.2 A-VIS).
- Every environment view is rendered on the WebGL2 backend in headless Chromium (engine.md: WebGPU in headless is
  unverified) and spot-checked on the owner's iPhone (WebGPU).

`look:` arguments are target x, y, z, yaw (compass bearing from target to camera), pitch, distance, fov. Anchors
(**M** from `lighting_spec.json`): landing thresholds 28R (1532.6, 542.3), 28L (1426.1, 744.5), 19L (733.2, −947.5);
PAPI row centres 28R (1132.4, 406.7), 28L (1026.0, 608.6), 19L (597.7, −555.9), 19R (338.5, −544.7), 10L (−1135.6,
−941.3), 10R (−1182.7, −701.1); approach bearings 117.8° (28L/28R), 27.8° (19L/19R), 297.8° (10L/10R).

### 11.2 Views

| ID | Env (`?wx=`) | Camera | What must be seen | Acceptance |
|---|---|---|---|---|
| E1 dawn | dawn | `view:overview`; `tower` | Warm glow at az 87°, no Moon, lights at night steps, floods on | A-SUN, A-EXP, A-CTL |
| E2 noon | noon | `view:overview`; `tower`; `gate:B26,60,1,14` | Shadows toward az 0° (Sun az 180.2°, el 51.7°); runway lights off; PAPIs lit; SCT200 high cloud | A-SUN, A-EXP |
| E3 dusk | dusk | 28R approach at 2 NM: `look:1532.6,19.8,542.3,117.8,3.0,3704,40`; `view:overview` | Civil-twilight sky, Moon at 18.9° 93 % lit with the correct lit limb, SSALR (no red side rows, no 500-ft bar), no rabbit, yellow caution zone at the far end, PAPI 2 white / 2 red | A-SUN, A-MOON, A-CTL, A-PAPI, A-COL |
| E4 night | night_clear | same approach view; `tower`; `gate:B26,60,1,14` | Moon 40° 93 %, faint bright stars only, sky floor, lit apron (colour parameter), terminal glow, aircraft nav/beacon | A-EXP, A-VIS, A-NAV |
| E5 marine layer | marine_layer | `tower`; approach 1 NM below the deck: `look:1532.6,19.8,542.3,117.8,3.0,1852,40`; approach 2 NM (inside the deck) | Flat grey OVC005 base at 152 m, no sun disc, no shadows; ALS on but dim by day (SSALR step 2 = 0.8 %: with the provisional ALS intensity of §5.4, 80 cd, it fades out beyond ~0.42 km, **M**) | A-FOG, A-CLD, A-CTL |
| E6 low ceiling night | low_ceiling_night | `view:overview`; `tower` | BKN010 underside lit by city glow; stars hidden in the cloud-covered part | A-CLD, A-EXP |
| E7 night fog | predawn_fog, night_fog | 28R approach at 0.6 NM (~255 ft, just above the 200-ft VV top): `look:1532.6,19.8,542.3,117.8,3.0,1111,40`; at 0.3 NM (~160 ft, inside the fog): `look:1532.6,19.8,542.3,117.8,3.0,556,40`; `tower`; `hold:14,40` | Full ALSF-2 (red side rows, 500-ft bar, rabbit twice per second), HIRL/TDZ step 4, lights fading at ~0.5 km, flood domes on the apron | A-FOG, A-VIS, A-CTL, A-FLASH |
| E8 IFR mist day | ifr_mist_day | same approach view; `tower` | Day ALSF-2 at step 5 visible through ¾ SM mist; BKN002 | A-FOG, A-VIS |
| E9 rain | rain_day, squall_night, drizzle_night | `gate:B26,60,1,14`; `hold:14,40`; `tower` | Streaks (heavy) vs mist (drizzle), wet darkened pavement, puddles, windsock full in the squall, waves | A-RAIN, A-WET, A-WIND |
| E10 thunderstorm | ts_evening | `view:overview` yaw toward SE | Flashes to the SE at ~3.5/min, CB base 4,400 ft | A-LTG |
| C1 ALS close-ups | night_clear and predawn_fog | 28R, 28L, 19L at 1,000 ft before the threshold, 100 ft up (`thr:28R,305,5`) and plan view from 300 m | Station layout vs JO 6850.2C Fig 2-1 (ALSF-2), 2-2 (SSALR), 2-3/2-4 (MALS/MALSR); piers vs NAIP crops | A-GEO |
| C2 PAPI | dusk | `papi:<end>,<angle>,1852` for all six ends at five angles | 28R/10L/10R/19L (3.00°): 2.3° 4R, 2.6° 1W3R, 3.0° 2W2R, 3.4° 3W1R, 3.7° 4W; 28L (2.85°): 2.15/2.45/2.85/3.25/3.55; 19R (3.15°): 2.45/2.75/3.15/3.55/3.85 | A-PAPI |
| C3 TDZ/RCL/edge | night_clear, predawn_fog | On the 28R centreline at the landing threshold, eye 5 m, looking west (`look:1178.8,3,355.7,117.8,0.7,400,50`) | TDZ bars 100–3,000 ft, 36 ft from the CL; RCL coding toward the far end; caution-zone yellow edges; red end bar; displaced-threshold wing bars behind | A-GEO, A-COL |
| C4 taxiway / RWSL | night_clear (+ a departure on 28R) | `hold:14,40` (REL at taxiway E, 10L/28R) and `hold:38,40` (E, 10R/28L) | REL on when a departure passes 30 kt, off 3–4 s before it reaches the intersection; blue edge lights labelled `inf` | A-RWSL |
| C5 aircraft lights | night_clear | `ac:<hex>,60` for a parked, a pushing-back, a taxiing, a lining-up and a landing aircraft; each from ahead, 90° left, 90° right, behind | Nav sectors, strobes/beacon rate, taxi light off when stopped, landing lights on the roll and < 10,000 ft | A-NAV, A-FLASH |
| C6 obstruction | night_clear | `tower` at 400 m | Tower-top L-864 flashing 30/min; no red lights on apron poles | A-FLASH |
| T1 light test | synthetic | `lighttest:` all Table B-1 rows | see A-VIS | A-VIS |

### 11.3 Acceptance criteria

**Unit tests (Node, no GPU; run in CI):**

| ID | Criterion |
|---|---|
| A-WX | The JS METAR decoder reproduces `metar_decode.py` on all 58 fixtures (deep-equal output) and the 38 test cases; `parseMetar` is deleted. |
| A-SUN | `node tools/env/test_ephemeris.mjs` passes (32 checks). |
| A-CTL | The JS controller reproduces `lights` in `tools/env/fixtures/env_presets.json` for all 14 presets. |
| A-VIS1 | The light-visibility function reproduces AC 70/7460-1N Table B-1 (+ B.3) within ±5 % and both twilight ranges within ±5 % at their ends. |
| A-PAPI1 | The PAPI colour function gives the C2 patterns for all six ends with both the standard and the HG4 aiming sets. |
| A-FIX | The fixture loader yields the §5.2 counts and face colours (e.g. 28R edge faces W 96 / Y 20 / R 2) and every sprite carries `prov`. |
| A-NAV1 | The nav-light sector function matches 25.1387 (red only 0–110° left, green only 0–110° right, white only ±70° aft) and the 25.1393 vertical factors. |
| A-FLASH1 | Effective intensity (Blondel–Rey) of every rendered flash ≥ the target at 30, 60 and 120 fps; rates: SFL 2/s, REIL 120/min (or 60), aircraft 40–100/min, L-864 30 ± 3/min. |
| A-CLK | METAR selection by data clock: at 2026-09-23 17:51Z the current report is `SPECI … 231722Z`; replay never returns a report observed after the replay time. |

**Render tests (harness PNGs; thresholds are ours, **I**):**

| ID | Criterion |
|---|---|
| A-SUN | A vertical pole's shadow azimuth within 1° of the ephemeris value; the Sun's disc centre on the horizon within 1 min of apparent sunset (19:04:33 PDT on 23 Sep 2026, USNO 19:05). |
| A-MOON | Moon position within 0.5° and lit fraction/limb visually correct (compare with a JPL Horizons table for the same instant). |
| A-EXP | Metered EV100 within ±1 EV of the §10 target by day; at night the clamp holds (EV100 ≥ 2) and the airfield lights bloom. With the fallback sky, the rendered global horizontal illuminance within ±20 % of Circular 171 at noon. |
| A-FOG | Day (ifr_mist_day): a black target at the reported visibility (1,207 m) has 5.5 % ± 2 % contrast against the horizon sky (the ASOS day definition). Marine layer: nothing above 152 m is visible from below the deck. No residual 3 % see-through anywhere (caps removed). |
| A-VIS | In `lighttest` scenes, each Table B-1 light is visible (core ≥ 3 code values above the local background) at 0.9 × the tabled distance and invisible (< 1 code value) at 1.1 ×; at night (night_clear) HIRL at step 1 is visible from the 2 NM approach view only if its modelled E ≥ E_T. |
| A-CTL | Every system on/off state and relative brightness in E1–E10 matches the controller output (e.g. SSALR vs ALSF-2 station count in C1: 28R SSALR shows no red side rows and no 500-ft bar; ALSF-2 shows 54 red lights). |
| A-PAPI | The five-angle patterns of C2 in the rendered images for all six ends. |
| A-COL | At night, the halo hue of threshold/wing-bar lights lies in 90–170° (HSV), red 345–15°, yellow caution 40–65°, blue taxiway 200–250°; the core may saturate to white. |
| A-GEO | Light positions project within 1 px (at 1 m/px plan views) of the fixture coordinates; ALS stations and pier crossmembers match the NAIP crops; the 28R PAPI is at 1,369 ft, not 1,298 ft. |
| A-CLD | Cloud bases at the METAR height ± the Table 13-6 resolution; the number of layers equals the report's; coverage within ±0.1 of `own_fraction` over a large area. |
| A-RAIN | Streak length within ±25 % of v × 1/60 s at the D₀ fall speed; the drop count ratio between light (1 mm/h) and heavy (10 mm/h) within ±25 % of the Marshall–Palmer ratio; drizzle shows no streaks. |
| A-WET | Wet asphalt diffuse albedo between 0.2 and 0.9 of dry (Lagarde range for porosity), puddles mirror the sky; drying shows the specular fading before the diffuse. |
| A-WIND | Windsock extension 0 at ≤ 3 kt, full at ≥ 15 kt; it points downwind of the METAR **true** direction (never ATIS). |
| A-LTG | Flash count per minute within the Table 13-7 class over a 5-min capture; flashes in the reported sector. |
| A-RWSL | REL/THL activations follow AIM 2-1-6 in a replayed departure and arrival (frame timestamps). |
| A-NAV | In C5 renders, only the permitted colours are visible from each azimuth; taxi light off when the aircraft is stopped. |
| A-PERF | engine.md gates: ≥ 30 fps mobile tier, ≥ 60 fps desktop, with lights and rain on. |

**Adversarial review (CLAUDE.md QA loop).** An independent reviewer sees only the E/C renders and the reference set, and
checks: ALS/PAPI/TDZ/threshold geometry against the FAA figures (AC 150/5340-30J Fig A-5, A-9, A-34, A-35; JO 6850.2C Fig
2-1 to 2-4; AC 150/5345-28H Fig 3-1, cached in `refs/cache/lighting/fig/`); pier layout against the NAIP crops
(`refs/cache/lighting/naip/`); night and weather appearance against **real SFO photos supplied by the owner** (none are in
`docs/qa/ref/` today; each needs a licence note). Pass = no "critical" finding; every "major" fixed or listed as an
owner question. Minimum three passes: dusk, clear night and night fog on the 28L/28R approach (airfield rec L8), then
the weather set.

### 11.4 QA overlays

`?qa=prov` tints every fixture sprite by provenance (pub/obs green, std blue, inf orange, NV red) and shows counts;
`?qa=env` shows the EnvState HUD with the tag of each value, the METAR in use, its age and the controller's steps.

---------------------------------------------------------------------------------------------------------------------

## 12. Open questions for the owner (merged, in priority order)

| # | Question | Blocks | From |
|---|---|---|---|
| Q7 | **Night photos of SFO**: apron floodlight colour per terminal, jet-bridge lights (amber beacon or not), terminal glazing glow, the tower at night. | Night apron look (release gate), bridge beacon | sun_night Q1, S6 |
| Q2 | Night photos or imagery of the **28L/28R approach piers**: which stations are lit? | ALS geometry beyond the FAA default | airfield Q2 |
| Q1 | Where is the **rotating beacon**? (Not in NASR, CS, AD, X-Plane, cached OSM.) | Beacon | airfield Q1 |
| Q3 | **Centreline lights on 10R/28L and 1L/19R**: CS/NASR say yes, the AD note implies no. A close photo would settle it. | RCL on two runways | airfield Q3 |
| Q4 | **Taxiway lighting** at a few holds (green centreline vs blue edge, lead-on/off coding, stop bars, RGLs). | Taxiway lights | airfield Q4 |
| Q10 | *New:* is the **28L MALSR** controlled separately (JO 7110.65 3-4-8, TBL 3-4-7) or through the HIRL (3-4-12, TBL 3-4-9)? Only SFO/FAA facility data can say; otherwise we keep TBL 3-4-7. | MALSR steps (minor) | this spec |
| Q5 / Q6 | REIL style (uni/omni) and PAPI aiming set / night setting (5 % or 20 %). | Minor photometry | airfield Q5, Q6 |
| Q8 | Accept archived real SFO weather as **presets in the artifact** (dated), or only the snapshot's own weather? | Artifact weather menu | weather Q6 |
| Q9 | D-ATIS via atis.info (no published terms) for runway configuration, or ADS-B flow only? | Runway config source | weather Q3 |
| Q12 | Add **@takram/three-atmosphere** (MIT, ~25 KB gzip + 91 KB star file) and ship takram's `stars.bin` (BSC5 terms unstated)? | Sky | sun_night Q5, Q6 |
| Q13 | Default night look: "photographic" (auto-exposed) or "eye-like" (darker, blue shift)? | Exposure tuning | sun_night Q3 |
| Q11 | Parked, powered aircraft at gates: nav and logo lights on or off? | Aircraft lights | sun_night Q4 |
| Q14 | Light-pollution data: request the Falchi raster (CC BY-NC 4.0; is the app strictly non-commercial?) | Night-sky floor value | sun_night Q2 |
| Q15 | Windsock positions: may we survey them on NAIP (public domain), with X-Plane/OSM only as locators? | Windsocks | weather Q4 |
| Q16 | A licensable photo/video source to calibrate pavement **drying** and puddle look? | Wetness constants | weather Q5 |
| Q17 | FMH-1 (2019) PDF and Kasten & Czeplak (1980), if you can download them (both only cross-checks). | Nothing blocking | weather Q1, Q2 |

Not answerable by the owner, tracked as **NV**: ALS steady-lamp and flasher photometry (FAA-E-2408/2998/2689 not public),
apron-flood photometry, SFO tower facility directives, NWS ASOS algorithm constants (primary spec not located).

---------------------------------------------------------------------------------------------------------------------

## 13. Implementation order

| Step | Content | Gate |
|---|---|---|
| 0 | Regenerate `lighting_spec.json`/`lighting_fixtures.json` (D1–D3); generate `data/sfo_lighting.js`; relay `dataNow`, `/api/taf`, ETag, polling; remove the browser METAR fallback | A-FIX, relay smoke test |
| 1 | `js/env/` core: clock, METAR port, ephemeris, EnvState, presets, `?t=`/`?wx=` hooks, QA overlays | A-WX, A-SUN, A-CLK |
| 2 | Lighting controller + fixture sprites + visibility factor + aircraft light logic, in **both** renderers | A-CTL, A-VIS1, A-PAPI1, A-NAV1, A-FLASH1, then C1–C6 renders |
| 3 | New renderer: atmosphere (takram GPU test → adopt or fallback), fog slabs, N cloud layers + shadows, physical units, pre-exposure, auto-exposure | A-SUN, A-MOON, A-EXP, A-FOG, A-CLD, A-PERF |
| 4 | Rain/drizzle, lightning, wetness, windsocks (after the survey), DOF masts + floodlight map, obstruction lights | A-RAIN, A-WET, A-WIND, A-LTG |
| 5 | Adversarial QA passes (dusk, clear night, night fog on the 28 approach; then E1–E10) with owner photos | §11.3 review |

---------------------------------------------------------------------------------------------------------------------

## 14. Sources

The three merged reports list and quote every source; the verifiers re-fetched them. Primary URLs used in this spec:

- FAA JO 7110.65BB §3-4 Airport Lighting: https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_4.html; §3-5 (3-5-1): https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_5.html
- FAA AC 150/5340-30J: https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5340-30J.pdf
- FAA Order JO 6850.2C: https://www.faa.gov/documentLibrary/media/Order/FAA_Order_6850.2C.pdf
- FAA AC 150/5345-46F: https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC-150-5345-46F-Fixtures.pdf
- FAA AC 150/5345-28H: https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-28H.pdf
- FAA AC 150/5345-51B: https://www.faa.gov/documentLibrary/media/Advisory_Circular/150_5345_51b.pdf
- FAA AC 150/5345-12F: https://www.faa.gov/documentLibrary/media/Advisory_Circular/150_5345_12f.pdf
- FAA AC 150/5345-43J: https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-43J.pdf
- FAA AC 70/7460-1N: https://www.faa.gov/documentLibrary/media/Advisory_Circular/2026-07-13_AC_70_7460-1N_Obstruction_Marking_and_Lighting_FINAL_CLEAN.pdf
- FAA EB 67D: https://www.faa.gov/sites/faa.gov/files/2024-07/eb_67d_rev.pdf
- FAA AC 150/5360-13A: https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC-150-5360-13A-Airport-Terminal-Planning.pdf
- FAA AC 150/5345-27F: https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-27F-Wind-Cone.pdf
- AIM ch. 2 §1: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap2_section_1.html; ch. 4 §3: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_3.html; ch. 7 §1: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html
- FAA NASR: https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/; Chart Supplement: https://aeronav.faa.gov/afd/03sep2026/sw_275_03SEP2026.pdf; Airport Diagram: https://aeronav.faa.gov/d-tpp/2609/00375ad.pdf; RWSL graphic: https://www.faa.gov/air_traffic/technology/rwsl/media/SFO.pdf; DOF: https://aeronav.faa.gov/Obst_Data/DAILY_DOF_CSV.ZIP
- 14 CFR 25.1385–25.1401: https://www.ecfr.gov/current/title-14/part-25/section-25.1385 (…/section-25.1401); 91.209: https://www.ecfr.gov/current/title-14/part-91/section-91.209; 91.155: https://www.ecfr.gov/current/title-14/part-91/section-91.155
- FAA Order JO 7900.5E w/ Chg 1: https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf
- ASOS User's Guide: https://www.weather.gov/media/asos/aum-toc.pdf; Rasmussen et al. 1999: https://opensky.ucar.edu/system/files/2024-08/articles_15245.pdf
- aviationweather.gov Data API: https://aviationweather.gov/data/api/; NWS disclaimer: https://www.weather.gov/disclaimer; IEM: https://mesonet.agron.iastate.edu/disclaimer.php
- MIT LL ATC-252: https://archive.ll.mit.edu/mission/aviation/publications/publication-files/atc-reports/atc-252.pdf; ATC-319: https://archive.ll.mit.edu/mission/aviation/publications/publication-files/atc-reports/Clark_2006_ATC-319_WW-15318.pdf
- flysfo.com runway constraints: https://www.flysfo.com/about/airport-operations/policies-regulations/runway-constraints; d-TPP visual charts: https://aeronav.faa.gov/d-tpp/2609/00375quietbridge_vis28r.pdf, https://aeronav.faa.gov/d-tpp/2609/00375tipptoe_vis28lr.pdf
- Garg & Nayar 2007: https://www.cs.columbia.edu/CAVE/publications/pdfs/Garg_IJCV07.pdf; Lagarde 2013: https://seblagarde.wordpress.com/2013/04/14/water-drop-3b-physically-based-wet-surfaces/
- USNO Circular 171: https://archive.org/details/DTIC_ADA182110; USNO definitions: https://aa.usno.navy.mil/faq/RST_defs; NOAA: https://gml.noaa.gov/grad/solcalc/calcdetails.html; JPL Horizons: https://ssd.jpl.nasa.gov/api/horizons.api
- takram three-atmosphere WEBGPU.md: https://github.com/takram-design-engineering/three-geospatial/blob/main/packages/atmosphere/WEBGPU.md
- Falchi et al. 2016: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4928945/; Kyba et al. 2011: https://doi.org/10.1371/journal.pone.0017307
- Frostbite PBR v3.2: https://seblagarde.files.wordpress.com/2015/07/course_notes_moving_frostbite_to_pbr_v32.pdf; Filament: https://google.github.io/filament/Filament.md.html
- Honeywell LED landing light: https://www.honeywellaerospace.com/us/en/products-and-services/products/control-systems/lighting/led-landing-and-taxi-lights/high-output-led-landing-light; Oshkosh Jetway sell sheet: https://oshkoshaerotech.com/hubfs/images/Jetway%20SteelGlass_Truss_Sell-Sheet_2025.pdf; NASA SVS CGI Moon Kit: https://svs.gsfc.nasa.gov/4720/
- three.js r186 source: npm `three` 0.186.0 (`node_modules/three`), MIT

Reproduce this spec's numbers: `python3 tools/env/env_spec_checks.py [--json]` (needs `node` for the ephemeris),
`python3 tools/env/test_metar_decode.py`, `node tools/env/test_ephemeris.mjs`, `python3 tools/env/build_lighting_spec.py`.
