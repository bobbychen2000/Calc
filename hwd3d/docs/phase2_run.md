# Phase 2 — independent run of the integrated app

Written 2026-11-13 by an independent QA agent. **No app, relay or data file was changed and nothing was committed.** The
app was run as built by P1–P4 (`docs/phase2_app.md`), against P1's relay in replay mode, on two replay windows that the
builders had not used, at 1280 × 720 and at the 390 × 844 phone viewport. Every number below was measured in these runs;
every image listed was looked at (Read tool) before it was described. Aircraft are named by ICAO type only; the run
artefacts with identities (`out/phase2/run_*`, full-ident runs) are gitignored and never quoted here.

## 1. What was run

**Windows** (chosen from `out/replay/hours_rank.json`; the builders tested Sun 8 Nov 20Z and Mon 9 Nov 21Z):

| Window | Recording hour | Local | Rank data (ground / transitions / area) | Offline Phase 1 events in the first 12 min |
|---|---|---|---|---|
| **A** | Sat 7 Nov 2026 20:00Z | 12:00 PST | 22 / 19 / 125 (2nd busiest hour) | T&G 5, take-off 3, full-stop 2, low pass 3 |
| **B** | Wed 4 Nov 2026 23:00Z | 15:00 PST | 15 / 19 / 122 (weekday pattern work) | T&G 5, take-off 2, full-stop 3, lift-off 1, low pass 1 |

**Runs** (all through `node livetest.mjs <job>` with `RELAY=spawn`, i.e. `hwd_live_server.py --replay rec_pack --from <W>
--until <W+1h> --loop --no-adsbfi --quiet` on a free port 8760; the page was opened **on the relay's own port**, so static
files and `/api/*` came from the relay with its gzip — the real deployment path, not the harness's static server):

| Run | Window | Viewport | Relay identity mode | Scene span (display clock) | 10-Hz engine steps sampled |
|---|---|---|---|---|---|
| `satA_desktop` | A | 1280 × 720 | full (D1 masks LADD/PIA only) | 19:59:08 → 20:13:13Z | 6,604 (11.0 min) |
| `wedB_desktop` | B | 1280 × 720 | full | 22:59:16 → 23:13:12Z | 6,196 (10.3 min) |
| `satA_t_phone` | A | 390 × 844, DPR 1, touch, iPhone UA | `--ident type-only` | 19:59:07 → 20:13:13Z | 8,134 (13.6 min) |
| `wedB_t_phone` | B | 390 × 844 | type-only | 22:59:07 → 23:12:03Z | 7,477 (12.5 min) |
| `satA_t2_desktop` | A from 20:09Z | 1280 × 720 | type-only | 20:08:07 → 20:13:46Z | 2,949 (short repro of F3a + commit-safe HUD shots) |
| `perf` ×4 | pack (shim) | desktop high / low / dynamic res, phone | — | 30 s each after 20 s warm-up | frame-rate probe only |

The first ~60 s of every relay run show no aircraft: a freshly spawned replay relay has no backlog (P4's issue I2, confirmed).

**Method.** The job (`docs/phase2/phase2_run_job.mjs`) runs inside the integrated page and uses only the app's own objects
(`window.HWD`). Headless Chromium renders this app with SwiftShader at **0.6–2 frames per second** (§2.2), which is far too
slow to sample motion, so the job pauses the app's render loop (`HWD.qa.pause`) and steps the app's own engine in the
app's frame order — `traffic.update(now)` → `physics.resolve(traffic, dt)` — at 10 Hz (step interval p50 100 ms, p99
≤ 103.5 ms in every run), as a device rendering ≥ 10 fps would. Every 30 s it un-pauses the app for 3.5 s so the app's own
UI (list, phase line, runway line, status, clock, labels) refreshes, then reads the UI and scans the DOM. Frames for
screenshots are rendered on demand (`HWD.frameNow`, `HWD.qa.shot`). Pauses for screenshot sets (13–21 per run, ≤ 32 s)
are excluded from the kinematics (pairs with dt > 0.4 s). Measures are taken on **drawn** bodies (valid, alpha > 0.5,
inside the D6 window, not hidden) with the same definitions as P3's `tools/traffic/replay_engine.mjs`; keys never leave
the page (opaque per-run ids, ICAO types only in the output).

**D1 reference.** `tools/qa/phase2_run_ref.py` (in `docs/phase2/` until fix round 1) builds, locally, the identity strings (ICAO address, registration,
callsign, `ownOp`, Mictronics registration) of every LADD/PIA-flagged aircraft (readsb `dbFlags & 12`) within 8 NM in the
window's hour — A: 5 flagged aircraft, 12 strings; B: 11 flagged, 28 strings — and, as a positive control, the
registrations/callsigns of unflagged aircraft (206 / 192 strings). The lists stayed in a scratch directory (never in
the repository). The bit meanings were re-read from the source: `wiedehopf/readsb` `README-json.md` (dev branch,
fetched 2026-11-13, sha256 `abb581d9…2b30`, identical to the copy P1 quoted): "PIA = dbFlags & 4; LADD = dbFlags & 8".

## 2. Results

### 2.1 At a glance

| Check | A desktop | B desktop | A phone (type-only) | B phone (type-only) |
|---|---|---|---|---|
| Console errors / warnings / page errors / failed requests | 0 | 0 | 0 | 0 |
| Ready (`__hwdReady`) | 2.6 s | 2.1 s | 2.1 s | 2.1 s |
| Bytes on the wire at ready (63 requests) | 6.53 MB | 6.53 MB | 2.20 MB | 2.20 MB |
| Bytes after the run (incl. SSE stream) | 7.88 MB | 7.74 MB | 3.34 MB | 3.15 MB |
| Hosts contacted by the page | relay only | relay only | relay only | relay only |
| Tracks held / drawn at some time | 55 / 18 | 49 / 16 | 55 / 18 | 47 / 16 |
| Fixed-wing ground aircraft-samples | 26,774 | 30,000 | 32,568 | 36,996 |
| … off pavement (any wheel; site + NAIP mask) | **2** (0.007 %) | **68** (0.23 %) | **5** (0.015 %) | **105** (0.28 %) |
| … fuselage inside a building footprint | **66** | **15** | **149** | **15** |
| Ground overlaps (planforms, margin 0) | 0 | **56** (1 pair, both moving) | 0 | **60** (same pair) |
| Teleports (> 1.5 × speed × dt + 2 m) | 0 | 0 | 2 (a B738 overflight, 16.7 m) | 0 |
| ↳ *correction (fix round 2)* | *this row counted only jumps between consecutive drawn samples; fade cuts and absences of any length were not counted, so "0" was not true. Re-measured with the any-absence definition in section 7* ||||
| Airborne below the ground / ground y ≠ `site.groundY` (> 0.3 m) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| D1: masked tracks; label = type; no reg/callsign/operator | 2; 2; 2 | 1; 1; 1 | 55; 55; 55 | 47; 47; 47 |
| D1: LADD/PIA identity strings found in the DOM (text + attributes) | 0 of 12 (23 scans) | 0 of 28 (20 scans) | 0 of 12 (27 scans) | 0 of 28 (24 scans) |
| Positive control: unflagged identity strings visible | 8–13 of 206 | 5–10 of 192 | 0 (type-only, expected) | 0 (expected) |
| Cards opened (every drawn aircraft, twice per run): masked cards "Identity withheld" / leaks | 2 / 0 | 1 / 0 | 21 / 0 | 16 / 0 |
| Track keys in the DOM / in console lines / `/api/ident` calls | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| `<audio>/<video>/<iframe>/<embed>/<object>` anywhere, any scan | 0 | 0 | 0 | 0 |
| ATC link | exactly one, `https://www.liveatc.net/search/?icao=KHWD`, `target=_blank rel=noopener` (all runs) ||||
| ATC sheet / pill / every card's Tower row at the scene time | "Tower open … (recorded)" / TWR / Open — correct for 12:00 and 15:00 PST, while the run itself took place at 06–07 PST (real tower closed): P4's I3 workaround works ||||
| About panel | all 6 notice blocks of `docs/ATTRIBUTION.md` found verbatim (whitespace-normalised); 7 links; LiveATC link-out; NAIP and weather credits (all runs) ||||

The two phone runs repeat their window's desktop run with a different identity mode: window A produced the **same 82
events with the same breakdown** in both runs (deterministic engine on the same input); B's phone run ended its scene
70 s earlier (73 vs 79 events).

### 2.2 Frame time and load size

Frame rate on this machine (4 CPUs, **SwiftShader software GL**; P4's in-page shim, 30 s after a 20 s warm-up, 8–9
aircraft drawn; `perf` probe):

| Configuration | Render size | rAF fps | rAF interval p50 / p90 / max | app `frameMs` (main-thread EMA) |
|---|---|---|---|---|
| desktop, high tier, `?fixedres=1` | 1280 × 720 | 0.63 | 1.60 / 3.12 / 3.12 s | 1,366 ms |
| desktop, `?quality=low`, fixed res | 1088 × 612 | 1.19 | 1.05 / 1.37 / 2.00 s | 1,056 ms |
| desktop, high tier, dynamic resolution on | 991 × 558 (scale 0.77) | 0.20 | 1.55 / 25.8 / 25.8 s | 1,230 ms |
| phone, low tier (auto), fixed res | 332 × 717 | 2.03 | 0.47 / 0.87 / 8.57 s | 61 ms |

These are software-rendering numbers and say nothing about a real phone GPU. Two observations still hold: the frame time
is dominated by the GL work (the `frameMs` EMA is the JS time of `frame()`, which blocks on the GPU process), and turning
on the dynamic-resolution controller made it worse here (one 25.8-s stall after a resize). P4's earlier "frameMs ~5.7 on
the phone" was not reproduced (61 ms here with the loop running).

Load size (relay serving, gzip, cold cache): the desktop high tier transfers **6.53 MB** before `ready`, of which the two
NAIP JPEGs are 6.04 MB (`naip2024_1m2.jpg` 3.55 MB, `naip2024_region_8m.jpg` 2.49 MB); 54 JS modules 0.48 MB gzip
(2.02 MB raw); `data/hwd_airport.js` 77 kB gzip (841 kB raw); `data/hwd_taxigraph.js` 82 kB gzip (348 kB raw); CSS 6 kB.
The phone (low tier) transfers **2.20 MB** (NAIP 1.71 MB: `naip2024_2m4.jpg` + `region_16m`). The SSE stream adds
0.94–1.33 MB per 13–14 min of replay (≈ 70–95 kB/min), METAR polls ≈ 0.7 kB/min.

### 2.3 Traffic counts by phase over time

`HWD.qa.counts().phases` and the runway line, read every 30 s (excerpt; runway lines shortened, zero counts dropped;
full series in `out/phase2/run_<w>_<dev>.json`):

| Scene (Z) | Drawn | Tracks | Phases | Scope (all tracks) | Runway line |
|---|---|---|---|---|---|
| **A** 20:00:16 | 8 | 31 | pattern 4 · parked 5 · arr/dep 2 | pending 12, overflight 12, hwd 7 | No runway movements seen yet |
| 20:02:13 | 10 | 34 | pattern 2 · taxi 3 · parked 3 · arr/dep 1 · over 2 | overflight 21, hwd 8, pending 5 | 28L ↑0 ↓0 (last 3 min) |
| 20:04:13 | 10 | 28 | pattern 4 · taxi 2 · parked 3 · arr/dep 1 · over 1 | overflight 16, hwd 9, pending 3 | 28L ↑0 ↓0 · 28R ↑1 ↓0 |
| 20:08:15 | 9 | 30 | pattern 4 · runway 1 · taxi 3 · parked 2 | overflight 15, hwd 11, pending 4 | 28L T&G 2 · 28R ↑1 ↓1 |
| 20:10:10 | 9 | 29 | pattern 2 · runway 1 · taxi 5 · parked 2 | overflight 19, hwd 10 | 28L T&G 3 · 28R ↑1 ↓2 |
| **B** 23:00:17 | 6 | 23 | pattern 1 · taxi 1 · parked 4 · arr/dep 3 | overflight 10, pending 7, hwd 6 | No runway movements seen yet |
| 23:02:16 | 9 | 24 | pattern 1 · taxi 2 · parked 3 · arr/dep 1 · over 2 | overflight 15, pending 3, hwd 6 | 28L T&G 1 |
| 23:04:10 | 9 | 24 | pattern 1 · runway 2 · taxi 4 · parked 1 · over 1 | overflight 15, hwd 7, pending 2 | 28L T&G 2 · 28R ↓1 |
| 23:06:51 | 7 | 23 | pattern 1 · runway 1 · taxi 4 · parked 2 · heli 1 | overflight 13, hwd 9, pending 1 | 28L T&G 3 · 28R ↓1 |
| 23:10:13 | 10 | 25 | pattern 2 · taxi 2 · parked 4 · heli 1 · arr/dep 1 · over 1 | overflight 15, hwd 10 | 28L T&G 4 · 28R ↓2 · heli 1 |

**Events vs the Phase 1 offline classifier** (live = whole run, ≈ 13 min; offline = first 12 min of the window):

| Event | A live / offline | B live / offline |
|---|---|---|
| touch_and_go | 5 / 5 | 6 / 5 |
| takeoff | 3 / 3 | 2 / 2 |
| full_stop_landing | 2 / 2 | 3 / 3 |
| low_pass_unresolved | 4 / 3 | 1 / 1 |
| lift_off (helicopter) | 0 / 0 | 1 / 1 |
| runup · hold_short · park · unpark · hangar_in · hangar_out | 3 · 2 · 6 · 2 · 2 · 0 | 4 · 1 · 6 · 2 · 2 · 1 |

### 2.4 Speeds, accelerations, turn rates of the drawn bodies (10 Hz)

| Measure | A desktop | B desktop | Phone runs (A / B) |
|---|---|---|---|
| Ground speed on the ground: p99 / max | 48.8 / **71.7 kt** (C172 touch-and-go roll) | 33.0 / **80.0 kt** (PA46, phase still "final") | 49.7 / 71.8 · 35.5 / 80.0 |
| Taxi-type phases > 35 kt | 4 samples (RV12, 35.6 kt) | 0 | 0 · 0 |
| Air speed p99 / max | 173 / 209 kt (B738 overflight) | 140 / 190 kt (PA46) | 167 / 177 · 135 / 183 |
| GA singles > 200 kt; anything > 250 kt below 3,000 ft | 0; 0 | 0; 0 | 0; 0 |
| Ground longitudinal accel p50 / p99 / max (m/s²) | 0.43 / 5.25 / **258** | 0.77 / 3.41 / **370** | max 316 · 311 |
| Ground path-lateral accel p99 / max | 5.06 / 142 | 5.76 / 215 | 6.36 / 210 · 7.56 / 263 |
| Ground turn rate p99 / max (°/s) | 25 / 25 (the engine cap) | 25 / 25 | 25 / 50 · 25 / 25 |
| Crab (nose vs motion) p99 / max | 18° / 163° | 33° / 180° | 21° / 166° · 31° / 180° |
| Air longitudinal p99 / max · path-lateral p99 / max | 4.49 / 5.35 · 4.38 / 7.67 | 4.50 / 4.50 · 4.73 / 9.17 | — |
| Air turn rate p99 / max (°/s) | 6.3 / 9.9 | 12.4 / 25.1 (a helicopter) | 6.4 / 20 · 11.9 / 30 (the same helicopter) |
| Vertical speed p99 / max (ft/min) | 1,274 / 1,806 | 1,523 / 2,362 (PTS1 low pass) | 1,347 / 1,996 · 1,597 / 2,362 |
| Exceedances vs P3's [inf] limits: ground accel > 3 (taxi) / > 6 (roll); path-lateral > 3; crab > 10° | 69 / 4; 173; 113 | 103 / 9; 217; 135 | — |
| … air: path-lateral > 6; turn > 25 °/s; vs > 2,500 (jets 6,000) | 8; 0; 0 | 4; 1; 0 | — |

Denominators: ground pairs moving > 0.5 m/s 10,087 (A) / 9,911 (B); path pairs > 1 m/s 8,787 / 7,739; air pairs 30,808 /
17,773. The p99 values match P3's offline harness on other windows (`docs/phase2_traffic.md` §7); the single-sample maxima
of 258–370 m/s² are single-sample artefacts at touchdown or at a stop-and-pivot (F3c).

### 2.5 Parking

| | A | B |
|---|---|---|
| `park` events / matched to a Phase 1 spot / unspotted | 6 / 4 / 2 | 6 / 6 / 0 |
| Spot kinds matched | hangar apron 1, ramp 2, tie-down 1 | ramp 5, tie-down 1 |
| Fixed-wing on a helipad; two aircraft on one spot | 0; 0 | 0; 0 |
| Oversize matches (span > spot capacity, "neighbours free" rule) | bizjet 28.7 m on 14.9 m | P180 14.0 m on 9.3 m; DA42 13.6 m on 6.7 m |
| Parked pose vs spot point (aircraft at their spot) | 0.8–4.3 m | 0.6–2.9 m |
| **Stale park records** (spot still held by an aircraft that left) | 1: a C172, 2.9 km away and airborne | 1: an untyped single, 517–535 m away, taxiing |
| `hangar_in` / `hangar_out` | 2 / 0 | 2 / 1 |

### 2.6 D6 — HWD traffic vs overflights

| | A | B |
|---|---|---|
| Scope at the end of each track: overflight / hwd / pending | 40 / 11 / 4 | 34 / 11 / 4 (phone 31 / 11 / 5) |
| Overflights by emitter category | A3 23, A1 10, A5 4, A2 2, none 1 | A3 21, A1 5, A4 4, A2 3, A5 1 |
| GA types tagged overflight | C72R, C152, PA24, AA5, P28R, C182, RV7, SF50, C172, E55P, CC11 (1 each) | C150, C172, P28A, C208 ×2, GLF4, CL60, C68A |
| Overflight tracks with a runway, ground or park event | 0 | 0 |
| A3–A5 tracks classified hwd | 1 (a bizjet that parked on the field — correct) | 0 |
| Aircraft with Phase 1 offline HWD events in the window → live scope hwd | 7 of 7 | 6 of 6 |
| Overflights that came within 1.5 km of the ARP below 500 ft AGL | **1** (PA24, F6) | 0 |
| hwd tracks never on the ground and never within 4 km | 0 | 0 |
| overflight → hwd upgrades / hwd → overflight | 0 / 0 | 2 / 0 |

## 3. Findings (most severe first)

**F1 — A departing aircraft keeps its parking spot (P3, `traffic.js`).** `tr.park` is released only when a track is
re-acquired after silence ("moved while silent", l. 237), removed (l. 383) or parks elsewhere (l. 427) — not when it
taxis out and takes off while transmitting. Seen in both windows: a C172 still held "FBO Ramp (north-east) ramp spot 41"
while airborne 2.9 km away (`parking.occ` still mapped the spot to it, so no other aircraft could be matched to that spot),
and an untyped single held a Green Ramp tie-down while taxiing 517–535 m away. Its card shows the **Parking row during
the take-off** (image 3). Only 2 of 6 `park` events got an `unpark` in each window.

**F2 — The altitude in the list, the 3-D labels and the card is the newest report, up to 60 s ahead of the drawn
aircraft (P4, `ui.js altText` l. 252, `app.js` labels l. 338).** In replay the display runs `lookahead_s` = 60 s behind
the stream head, but both read `tr.last.altB`. Measured on drawn airborne aircraft, once per second: the printed report
is p50 35–42 s, p90 58–59 s ahead of the display time; it differs from the reported altitude at the display time by p50
199–230 ft, p90 500–548 ft, max 793–912 ft; **> 200 ft in 49–56 % of samples** (B desktop, both phone runs; the A desktop
run predates this measure). Image 3: "−50 ft · 40 ft AGL" on a climbing aircraft. The value is also the raw readsb
`alt_baro` (pressure altitude, not QNH-corrected; A3007 on 7 Nov), so finals read "−75 ft", "−100 ft". In live mode the
lead equals the adaptive delay (up to 65 s).

**F3 — Physical plausibility violations** (all rare, all with the evidence in `out/phase2/run_*_*.json`):
- **a. Nose through a closed hangar (A, deterministic).** A single-engine piston bridged a 51-s hole between two taxi fixes on a taxi
  route and stopped between the Hangar B and C rows with its nose inside the Hangar B footprint (1–6 of 18 fuselage sample
  points, depending on the heading, which was not logged; Hangar B is drawn 4.5 m tall, height [inf]); its reported GNSS fixes are outside every footprint. It stayed so until its signal
  ended (`hangar_in`, "In hangar · Hangar B"): 66 / 149 samples. It is real behaviour (entering its T-hangar), but no door
  is modelled and no door spot exists there, so the render shows the nose through the wall (image 4). Reproduced in a
  third, type-only run at the same scene time.
- **b. Two taxiing aircraft pass through each other (B, both B runs).** At 23:05:16–23:05:22Z an untyped high-wing single
  taxiing at ~2.3 m/s (4.5 kt) on a taxi route crossed a C172 that was in phase "runup" but creeping at 0.7–2 m/s, at
  about (394, 24), north-east of the 28R end; centre distance down to 0.4 m; 56 / 60 overlapping samples (1 pair). GroundPhysics only
  nudges moving bodies with a fading offset, which did not separate them.
- **c. Touchdown drawn short of the runway, then stop-and-pivot (B).** A PA46 was drawn on the ground at 79 kt
  (40.8 m/s), 37 m before the 28R threshold on the extended centreline (all 3 wheels off pavement), while its recorded
  fix there was still airborne (−50 ft baro, 74 kt); a C150 was drawn on the ground 9 m before the 28R end decelerating
  from 45 kt to under 1 kt within 1–2 s, then crawling (0.4–8 kt) with its heading swinging 306°→330°, while the
  recording had it crossing the threshold airborne at 44 kt and reporting ground only about 140 m past it. The PA46 is the "ground, phase final,
  80 kt" maximum of §2.4; the single-sample ground maxima of 258–370 m/s² (a single-engine piston's landing roll in A, a PTS1 drawn on
  the ground in phase "downwind" in B) are artefacts of the same kind at touchdown or at a stop.
- **d. Partly off pavement while slowing (B).** A C172 stopped with 1–3 wheels off pavement at (351, 22) north-east of
  the 28R end (25 / 46 still samples). Overall off-pavement rates stay at 0.007–0.28 % of ground samples.
- **e. A parked P180 with its fuselage in a building** for 1.5 s at its ramp spot (181.6, 396.7) before the placement
  moved it (15 samples, both B runs).
- Not seen in any run: airborne aircraft below the ground, ground aircraft off `site.groundY`, fixed-wing aircraft on
  helipads, two aircraft on one spot. (*Correction, fix round 2:* this list also said "teleports of HWD traffic"; the
  measure behind it missed fade cuts and absences longer than one sample, so that claim was withdrawn - see section 7.)

**F4 — Phase label lags the drawn motion on departure (P3).** The card of image 3 says "Taxiing" for an aircraft drawn
40 ft above the runway at 50 kt and +650 ft/min (the take-off happened inside a recorder hole; the back-dated label
arrives later). The same class of lag shows as "final" for an aircraft already rolling (F3c). Labels marked
"provisional" are designed to change, but these were not marked provisional.

**F5 — Type-only mode loses Mictronics-derived types (P1 relay `_finish` + `D1.apply`).** Masking removes `_mx`, and
with it the type of aircraft whose adsb.lol record has no `t` (checked in the recording: the parked A3 bizjet of window A
and an A1 aircraft report no `t`). In the type-only runs that bizjet is labelled "Aircraft" and drawn with the A3
stand-in (airliner shape, 34.3 m span; image 5) instead of its 28.7 m bizjet placeholder, 11.2 m from its spot point.
Since published packs default to type-only (D1), the artifact will show this. The type is not identity under D1, so
keeping `_mx.t` / `_mx.d` as `t` / `desc` before masking would fix it (owner/P1 decision).

**F6 — One HWD departure tagged overflight (window edge, P3 classifier).** In A, a PA24 that had been taxiing on the
field at 19:56Z was first seen by the run at 20:00:01Z just after lift-off (alt_geom −100 ft → h ≈ 0 ft AGL, 83 kt, track
305°, 537 m north-west of the ARP), then 4 km away climbing. The run never saw its ground part and D6 tagged it
overflight after 90 s; the "L corridor fix" rule did not fire on that first low fix (cause not verified). The same will
happen whenever the live relay starts, or coverage begins, during a take-off.

**F7 — Start-up transient on the tower suffix (P4, minor).** In one scan (B, 5 s after `ready`) a list row carried
"tower closed (CTAF)" although the scene tower was open: the first list render uses `ui.towerOpen` computed before the
first data-clock update (wall clock ≈ 06:56 PST). Gone from the next refresh on.

**F8 — Runway line lists a runway with nothing on it (P4 `stats.js`, cosmetic).** "28L ↑0 ↓0 (last 3 min)" appears
when the only 28L event is a hold-short or low pass.

**F9 — Display limits of this machine, not app defects.** Under SwiftShader the app renders at 0.6 fps (desktop high) to
2 fps (phone low tier); with the render loop running, aircraft move in visible jumps and the follow camera does not
converge (a follow shot of A showed the runway without the aircraft). The fly-in close-ups of fast aircraft missed
them for the same reason. These shots were not used to judge the app.

What worked as designed and was checked: D1 everywhere in the UI (0 leaks, positive control positive, 0 keys in DOM or
console), the ATC link-out (one link, no media element), tower state from the data clock (I3), the About notices, the
phone bottom sheet (the fifth view button sits in a horizontally scrollable row, CSS `overflow-x: auto`; scrolling was
not exercised), D6 for every aircraft with offline HWD events (13 of 13), no overflight
with a runway event, deterministic event counts across two runs of the same window, ground heights on `site.groundY`.

## 4. Screenshots

Committed (JPEG, ≤ 285 kB each; captions, sources and licences in `docs/phase2/SOURCES.json`; every HUD shot is from a
`--ident type-only` relay, the clean shot has no HUD, so none shows a registration or callsign):

| File | What it shows |
|---|---|
| `docs/phase2/phase2_run_1_overview_desktop.jpg` | A, desktop Overview with the full HUD (type labels, phase line, runway line, list) |
| `docs/phase2/phase2_run_2_overview_phone.jpg` | A, phone portrait Overview, bottom sheet in peek state |
| `docs/phase2/phase2_run_3_card_stale_parking_phone.jpg` | F1 + F2 + F4 in one card: "Taxiing", Parking spot 41, "−50 ft · 40 ft AGL", 50 kt, +650 ft/min |
| `docs/phase2/phase2_run_4_hangar_clipping_desktop.jpg` | F3a: a single-engine piston's nose inside Hangar B (type label masked, D1 decision (d)) |
| `docs/phase2/phase2_run_5_type_only_bizjet_standin_desktop.jpg` | F5: parked bizjet as "Aircraft" with the airliner stand-in |
| `docs/phase2/phase2_run_6_runup_pad_clean_desktop.jpg` | B, three GA placeholders on/beside a paved pad, on pavement and apart (framebuffer, credit line added) |
| `docs/phase2/phase2_run_7_atc_sheet_phone.jpg` | ATC sheet: tower open at the scene time, LiveATC link, frequencies |
| `docs/phase2/phase2_run_8_stats_sheet_phone.jpg` | Statistics sheet: phases in view, runway movements, circuit median, latest events by type |

All run images (gitignored, 140 PNGs; the full-ident desktop runs show registrations and must not be published):
`out/phase2/run_{satA,wedB}_<view>_m{6,11}_desktop.png`, `run_{satA_t,wedB_t}_<view>_m{6,11}_phone.png` and
`run_satA_t2_*_desktop.png`, where `<view>` ∈ overview, tower, green, west, final28l, overview_clean, close_{parked,taxi,
air}[_clean], card_masked, follow, plus `about`, `atc`, `stats`, `card_stalepark`, `clip_*`. Per-run data:
`out/phase2/run_<w>_<dev>.json`; console files `out/phase2/app_console_run_<w>_<dev>.json`.

## 5. Not verified / limits

- **Real devices.** Only SwiftShader was exercised; frame times, GPU memory and touch feel on a real phone are unknown.
  The 10-Hz engine stepping emulates a device rendering ≥ 10 fps; the app's own pacing (variable dt, dynamic resolution)
  was measured only in the frame-rate probe.
- **Live mode** (adsb.lol / adsb.fi polling, adaptive delay) was not run; only the relay's replay path.
- **East flow** (10L/10R) is untested: every recorded hour is west flow.
- The cause of F6 (why the corridor rule did not fire) and of F3c (which code path set ground before the threshold) was
  not traced in the code; the observations are from the drawn state and the recording.
- Hangar heights (4.5 m T-hangar) are [inf] (P2); F3a's visual depth depends on them, the footprint test does not.
- The A desktop run predates the F2 measure and the violation context logs (added to the job between runs); B desktop
  predates the context logs. The phone runs carry both.
- Positive-control and leak lists cover the window's whole hour within 8 NM; a leak string not displayed during the run
  cannot be excluded by this test beyond what the scans saw (19–27 DOM scans and 16–21 cards per run).
- LiveATC terms (Q2) and whether `www.adsb.lol` is the normal docs host remain owner questions; nothing here re-read them.
- Network use of these runs: no adsb.lol or adsb.fi request (replay from the committed recording, `--no-adsbfi`; the
  relay's adsb.lol quota log is unchanged since 11:35Z); the relay fetched the KHWD METARs of the two new hour slots
  from aviationweather.gov once each (cached in the gitignored `out/replay/wx/`); the readsb README was fetched once
  from raw.githubusercontent.com.

## 6. Review fix round 1 (2026-11-13)

The Phase 2 review raised 40 findings (traffic behaviour 12, visual / world 10, provenance 18). Fix round 1 changed the
app, relay, data tools and docs (nothing committed). Every number below was measured after the fixes, on this machine;
every image named here was looked at.

### 6.1 Re-run of the review's traffic harness (three 1-h windows, 10 Hz, the app's replay path)

The reviewer's packs (heli = 5 Nov 19Z, pat = 8 Nov 22Z, night = 5 Nov 05Z; full-ident, gitignored, `out/review_traffic/`)
through a harness that follows the app (ingest at send time, display 60 s behind, `update` + `physics.resolve` at 10 Hz).
Before = the review's numbers.

| Measure | heli before → after | pat before → after | night before → after |
|---|---|---|---|
| Visible re-placements (invisible < 5 s, reappearing > 1.5 v·gap + 5 m and > 10 m away) | 28 → 5 | 27 → 2 | 6 → 1 |
| Lift-offs of fixed-wing aircraft below 40 kt | 3 of 12 → 0 of 11 | 12 of 34 → 0 of 33 | 1 of 5 → 0 of 6 |
| On-ground stops from > 40 kt to < 8 kt within 3 s | 14 in the three windows → 0 | | |
| Ghost-parked aircraft (drawn parked > 50 m from their newest fix) | 3 → 0 | 2 → 0 | 1 → 0 |
| Airborne label on a rolling aircraft / ground label > 50 ft up / "parked" while moving (10-Hz samples) | 1,052 / 20 / 203 → 0 / 0 / 0 | 3,002 / 114 / 530 → 0 / 0 / 0 | 978 / 162 / 29 → 0 / 0 / 0 |
| Air speed above 1.15 × the reported speed + 3 m/s (samples) | 5 → 6 | 178 → 0 | 0 → 0 |
| Helicopter drawn inside a building (samples) | 12,628 → 0 | 0 → 0 | 0 → 0 |
| Fixed-wing ground samples with a wheel off the site + NAIP pavement | 801 → 786 | 197 → 265 | 2 → 1 |

The remaining re-placements (by class only: these are named hours of full-ident packs, and a type plus an hour of a
LADD / PIA-flagged aircraft is not repeated in committed docs): heli two single-engine pistons (one twice, 205-256 m),
two helicopters (145 m, 16 m) and an airliner overflight (734 m); pat a single-engine piston (39 m) and a helicopter
(184 m); night a helicopter (321 m). The pat off-pavement count rose by 68 samples: aircraft now
follow taxi routes through two places where the site pavement has holes that NAIP shows paved (around (-220, -288) and
(-516, -484)); the heli count is mostly a C172 standing at the 28R end on grass by its GNSS fixes (15-20 m off the
pavement) [*correction, fix round 2: that attribution was wrong - the body was driving on a planned route (577 of its
773 off-pavement samples had route = 1) and only one of its fixes lay on grass; it shuttled ~12 m to and fro between a
GroundPhysics seek offset and its decay. Root cause and fix in section 7*]. 289 fixed-wing samples in the heli window still have the planform inside a building footprint (aircraft
entering hangars; review residual (d)).

### 6.2 P3's harness, now strict (`node tools/traffic/replay_engine.mjs <w> --strict`)

The harness now counts fade re-placements as teleports and fails on > 6 re-placements per hour, any ghost-parked frame,
lift-off below 0.7 × the approach speed, on-ground hard stop, hop, airborne hover, helicopter inside a building, and label
contradiction.

- **Weekday (Mon 9 Nov 21Z; *correction, fix round 2:* this line said "Wed 11 Nov 19Z", but the P3 weekday pack `out/replay/pack_weekday.json.gz` covers 2026-11-09T21:00-21:59Z): RESULT ALL PLAUSIBILITY CHECKS PASSED.** 2 re-placements (an R44 on the ground 25 m, an
  untyped aircraft on downwind 339 m), 0 ghost frames, 0 slow lift-offs, 0 hard stops, 0 hops, 0 hover frames, 0 label
  contradictions. Event counts unchanged from section 2.
- **Weekend (Sun 8 Nov 20Z): RESULT FAILED** on three checks: 7 re-placements in the hour (7.1 / h, limit 6), 1 ghost-parked
  frame and 1 hop. Before fix round 1 the harness did not count re-placements; the old fade counter gave 46 cuts in the
  review's pat window. The 7 (by phase only, see 6.1): an arrival (248 m), a downwind (316 m), two take-off rolls / climb-outs of
  two aircraft (432 and 971 m; 66 and 891 m) and a landing roll (294 m). One take-off case was traced: the last taxi fix
  lies 70 m from the runway end at 13 kt and the next fix, 48 s later, 455 m down the runway at 117 kt; a taxi route plus
  a 3.9 m/s2 roll needs 62 s, so no plan within the [inf] limits fits and the body is re-placed (`planRollTo`, new in
  this round, handles the feasible cases: 1 to 2 per window). The event counts are unchanged.

### 6.3 Other checks run after the fixes

| Check | Result |
|---|---|
| `python3 -I tools/live/test_relay.py` | 20 tests OK (new: late-flag purge + forget event, case-variant / allow-list serving, two processes sharing the quota file) |
| `node tools/live/test_shim.mjs` | PASS |
| `python3 -I tools/live/test_taxigraph.py` | 9 tests OK (graph rebuilt with 23 holds: 747 nodes, 1 component, 0 unreachable holds / spots / helipads) |
| `python3 -I tools/check_airport.py` | see the bullet below |
| Planted D1 token in an untracked `docs/phase2/*.md` | found by the extended scan (then deleted) |
| Headless renders (desktop + phone, day and night) | 0 console errors / warnings in every run |

`tools/check_airport.py` after the fixes: section 8 lists the 5 NAIP-only holds (contrast 22.4-32.0, 128-203 ft from the
centreline; 0 failing). The D1 scan reads 27 ADS-B-derived files plus 190 more committed text files (taxigraph,
docs/phase2, CLAUDE.md, code, generated modules), 0 findings. The SOURCES coverage now includes `docs/phase2/` and
`js/` data files and generated modules. The RESULT line still reports FAILED, on two items, and both come from files of
the concurrent Phase 3a work (`js/aircraft/models/`, untracked, not touched by this round): its `SOURCES.json` has an
entry without `made_by` / `note` (`sf50_meta.json`), and its `pc12_meta.json` / `sf50_meta.json` carry `src` texts other
than obs / inf. The same two items failed before this round's edits.

### 6.4 Renders looked at

- Night, 20:00 PST (tower open): the MIRL rows of both runways, the PAPI / VASI and the beacon (`phase2_fix1_9`); at
  23:30 PST (tower closed) only 10R/28L is lit, dimmer (preset low), 10L/28R dark.
- Tower: the shaft on its single-storey base (`phase2_fix1_10`); the Tower view's eye now stands over the shaft.
- Ground: before / after / NAIP on one camera (`phase2_fix1_11`). Over five off-airport tiles the render / NAIP mean RGB
  went from 0.80-0.82 / 0.77-0.79 / 0.72-0.74 to 0.87-0.91 on every channel, and the mean saturation from 0.22-0.32
  (NAIP 0.14-0.25) to within 0.01-0.015 of NAIP. On the runway and taxiway points of three airfield tiles the pavement
  luminance went from 0.68-0.73 to 0.84-0.93 of NAIP.
- The business jet that was cut in half at the FBO Ramp (south) edge is in-painted away. One aircraft-like object on the
  grass near the 28R end is not in the catalogue (not on pavement) and still shows as a flat image.
- The helicopter pad complex south of 10R/28L is paved (the helicopter that the review saw "on grass" there now stands
  on a pad).
- Phone card (`phase2_fix1_12`): "Identity not shown · type-only feed", icons on screen, opaque footer.

### 6.5 Per-finding status

| # | Finding (short) | Status | What changed / evidence |
|---|---|---|---|
| 1 | Re-placement cuts are visual teleports | fixed (residual) | `motion.js` profiles and plans the body can follow; re-placements counted as teleports in both harnesses; real alpha cross-fade (`uAlpha`). 28 / 27 / 6 → 5 / 2 / 1 per h; weekend P3 still 7.1 / h (6.2). *Fix round 2: both counts covered only absences < 5 s; with any-absence counting and the fixes of section 7: 0 in all five windows* |
| 2 | Stale park record → ghost + teleport back | fixed | park released on moving > 15 m or airborne; no "parked" from first-heard on a taxiway. Ghost-parked 6 → 0 aircraft in the review windows. *Correction (fix round 2): this row said "ground loss rests at the last fix pose" - true only on aprons / helipads / hangar-door taxilanes with gs < 1 kt; elsewhere the aircraft faded out and reappeared minutes later. Fixed in fix round 2 (section 7)* |
| 3 | Take-off / T&G in a hole: brake, pivot, slow lift-off | fixed | rolling start at the fix's own speed and position, line-up at the route's runway join, VLOF from the ACD approach speed; lift-offs < 40 kt 16 → 0, hard stops 14 → 0 |
| 4 | Chord across grass and runways | fixed | route → fast route → chord only if on pavement → forced route ≤ 1.5 × → hold; roll-out + exit split. The P46T grass chord is gone |
| 5 | Ground state from unsmoothed per-fix height | fixed | debounced ground (slow fixes < 0.45 Vapp on the ground, one airborne-by-altitude fix < 250 ft held, lift-off needs ≥ 0.8 VR) |
| 6 | Live: fixed-wing hovering after reports stop | fixed | air tracks dead-reckoned straight and level, faded after 20 s; synthetic live test: hovering 0 s at a 156-s poll period |
| 7 | Helicopters: no rest pose; inside a hangar | fixed | helicopter still runs and rest poses; hidden while the rest pose is in a hangar. Helicopter-in-building samples 12,628 → 0 |
| 8 | D6 'L corridor fix' rule not implemented | fixed | an L corridor fix within R_FIELD and ≤ H_PASS sets K.hwd; synthetic corridor test: scope hwd at t = 0 |
| 9 | Phase labels lag / contradict | fixed | `drawnPhase`: the plan's phase, then the drawn ground / air state; contradictions 0 in all windows |
| 10 | Runway end from the line-up turn | fixed (app); deferred (Phase 1 `events.py`) | end from the decisive airborne fix if aligned, else ground-speed-weighted ≥ 15 kt; the pat '10L ↑1' is gone. `events.py` not changed: regenerating the frozen Phase 1 `hwd_events.json` cascades into Phase 1 docs and counts |
| 11 | Six residuals | (a) fixed, (b) fixed, (c) fixed, (d) partly, (e) not a defect, (f) fixed | (a) speed cap 1.15 × target + 3 m/s, feed-forward (pat 178 → 0); (b) TIS-B echo de-duplication (150 m / 300 ft / 10 s); (c) one stop event per still run; (d) fillets keep wingtips clear, 289 heli-window samples remain near hangar doors; (e) the tie-down row pitch is 12.15 m, so matching 8-13 m would assign the neighbour's spot; (f) ground bodies > 3 km from the ARP are not drawn |
| 12 | Relay budget consequences | fixed (docs + record mode) | the real budget behaviour is in About, the status pill (poll period from `/api/ping`) and `phase2_relay.md`; adsb.fi polls only while a client is connected, also with `--record` |
| 13 | 5 hold bars missing | fixed | `NAIP_HOLDS` measured (contrast 22-32), data + taxigraph rebuilt (23 holds), check section 8 |
| 14 | TDZ bars not drawn | fixed | `END_PAINT_OBS` tdz groups (src obs); docs corrected |
| 15 | Night: airfield invisible | fixed | MIRL on both runways (type obs, positions inf), NASR schedule (`phase2_fix1_9`) |
| 16 | Tower massing | fixed | tall part ~8 × 9 m [inf, NAIP 2022 + 2024], base 4 m; eye over the shaft (`phase2_fix1_10`) |
| 17 | Unmapped helicopter pad area | fixed | `site.js HELI_APRON_NAIP` (NAIP-segmented outline, 4 pads); not added to the Phase 1 data set |
| 18 | NAIP aircraft as flat images | fixed (residual) | catalogued aircraft in-painted in the texture; one uncatalogued object on grass remains |
| 19 | PAPI / VASI without a vertical cut-off | fixed | PAPI 4°, VASI 6° above the aim, 4° below, with a fade |
| 20 | Surface-painted holding position signs | fixed (as a documented gap) | listed under "Not drawn" in `phase2_world.md` §4 |
| 21 | Phone UI defects | fixed | sticky icons, 44-px targets, opaque footer, label clamp, no "-0 ft", "unspotted" reworded, closer phone overview (`phase2_fix1_12`) |
| 22 | Ground tone and pavement patchwork | fixed | `uNaipSat` / `uNaipBal` and NAIP-calibrated asphalt (6.4; `phase2_fix1_11`) |
| 23 | D1: identity kept after a late flag | fixed | purge from `/api/ident` and history, `forget` SSE event, test; adsb.fi v3 verified to carry `dbFlags` |
| 24 | Type-only cards claim LADD / PIA | fixed | `_masked` 'd1' / 'type-only' → `maskWhy`; card text per reason |
| 25 | Persistence vs salted masked keys | fixed | masked tracks not stored / restored; reconcile restored stale tracks |
| 26 | Static deny rules case-sensitive | fixed | allow-list + lower-cased parts + case-insensitive realpath check; tests for `/Refs/…`, `/OUT/…`, `/JS/geo.js` |
| 27 | "Broadcast" for database fields | fixed | `adsb_db` source "aggregator database"; About reworded |
| 28 | `--record` guard too loose | fixed | inside hwd3d only `refs/cache/local/` or `out/` (not `out/replay/`) |
| 29 | ATTRIBUTION not updated | fixed | rows for the taxigraph, NAIP textures, regional mosaic, fixtures, pave mask, ACD module, docs/phase2 images, AWC, IEM METARs, earcut; adsb.fi row updated; NAIP terms still not re-read (marked unverified) |
| 30 | SOURCES.json / ODbL URI | fixed | `js/world/SOURCES.json`, `js/world/tex/SOURCES.json`, `js/aircraft/SOURCES.json`; URI in `pave_naip.js`; coverage check extended |
| 31 | D1 guard scope | fixed | every committed text file scanned (taxigraph node ids, synthetic test values, numeric tokens and FAA coordinates whitelisted); planted-token test |
| 32 | Flagged types + hour in docs | fixed | `phase2_app.md` and `phase2_traffic.md` now give counts / "business jets" only |
| 33 | Unescaped pack text in About | fixed | `esc()` on desc / src; `?pack=` same-origin relative only |
| 34 | About poll claim vs real budget | fixed | About text + status pill; the quota file is merged under a lock before each request |
| 35 | Regional backdrop provenance | fixed | described as a mosaic incl. undated overviews; raw kept in `refs/cache/local/naip/` (sha256 4b6b46a9…) |
| 36 | earcut ISC notice | fixed | licence text in `js/world/earcut.js`, ATTRIBUTION software row, `requests_to_sfo3d.md` R6 |
| 37 | Plain static server binds all interfaces | fixed | `--bind 127.0.0.1` in CLAUDE.md and `package.json` |
| 38 | QA script hygiene | fixed | moved to `tools/qa/phase2_run_ref.py` (not served), output refused outside `out/` / temp |
| 39 | Docs vs code (OD1, Phase 2 status, persistence comment) | fixed | `QUALITY` high only; CLAUDE.md "in review"; comment reworded |
| 40 | Derived N-number for unregistered addresses | fixed | shown only with a known type and marked [inf] (the FAA PIA program page was not re-read) |

## 7. Review fix round 2 (2026-11-13)

The second review raised 9 findings:

| Area | Findings |
|---|---|
| Traffic | F1-F5 |
| Relay | F6, F7 |
| Phone UI | F8 |
| Docs | F9 |

Fix round 2 changed these files (nothing committed):

- the app: `js/live/{traffic,motion,ground,feed,classifier,ui}.js` and `live.css`;
- the relay: `hwd_live_server.py`;
- the checks: both teleport harnesses, a new phone-UI job (`jobs/phone_ui.mjs`), and `tools/live/test_relay.py`;
- these docs.

Every number below was measured after the fixes, on this machine (4 CPUs, SwiftShader), and every image named here was
looked at.

**Windows.** All five run at 10 Hz through the app's replay path: ingest at send time, display 60 s behind,
`update` + `physics.resolve`.

| Window | Pack | Hour (UTC) |
|---|---|---|
| heli | review | 5 Nov 19Z |
| pat | review | 8 Nov 22Z |
| night | review | 5 Nov 05Z |
| weekday | P3 | Mon 9 Nov 21Z |
| weekend | P3 | Sun 8 Nov 20Z |

The review packs are full-ident and gitignored (`out/review_traffic/`); the P3 packs are in `out/replay/`.

**Before and after.** "Before" is the fix-round-1 code measured with the *new* counting, so the two columns compare like
with like.

### 7.1 How a teleport is counted now (F1)

Fix round 1 counted a re-placement only when the drawn body was invisible for less than 5 s. A fade-out, removal and
re-creation of the same aircraft somewhere else was never counted, and neither was a hidden segment. The gate also
allowed 6 re-placements per hour.

Both harnesses now follow each aircraft by its key across *any* absence: a fade cut, a fade-out and removal, `hideSeg`,
an air hide or the hangar. The harnesses are `tools/traffic/replay_engine.mjs` and the in-app `phase2_run_job.mjs`.

- **Counted as a teleport:** the aircraft reappears more than 1.5 × speed × absence + 10 m (and more than 10 m) from
  where it vanished.
- **Not counted:** absences only outside the D6 window or simulation range. These are reported as window re-entries.
- **Engine or signal:** each teleport is attributed to one of two causes.
  - *Engine:* the fixes on either side of the absence are no more than `SIGNAL_LOSS_S` = 90 s apart [inf]. That is
    longer than any recorder hole (≤ 52.4 s) plus `seen_pos` latency.
  - *Signal:* the aircraft was not heard for longer than that and moved unseen.
- **Gates:** `teleports_engine` = 0, and `teleports_signal_hwd` (signal teleports of HWD traffic) = 0. The 6 / h
  allowance is gone.
- **Independent check:** the reviewer's scratch harness measures the same quantity (`reappJump`).

With this count, the fix-round-1 code had these teleports:

| heli | pat | night | weekday | weekend |
|---|---|---|---|---|
| 7 (5 engine + 2 signal) | 3 | 1 | 5 | 12 |

Section 6.2's "weekday: ALL PASSED" was therefore true only under the old count.

### 7.2 Root causes and what changed

**F1 / F2 — silent ground aircraft.** A ground track whose reports stopped was faded out off an apron. It then came back
wherever it was next heard. This was the main source of the long-absence teleports, and of aircraft vanishing while
moving.

- `groundLost` now keeps such an aircraft drawn (`tr.stale`, phase `no_signal`, "No signal · last position", src inf).
  - It stays at the stop point of its own braking extrapolation (`groundStop`: taxi / roll deceleration, clipped to the
    pavement).
  - It is kept for up to 30 min (`LOST_KEEP_MS`); park records keep their own rule.
  - Only aircraft more than 3 km from the ARP (not drawn anyway) are removed.
- When the aircraft is heard again, the motion continues from the drawn pose. A continuation anchor at the current target
  pose is inserted before the new fix (`anchorAt`).
- **Race with `seen_pos` latency.** Ground loss now needs `MOVING_LOST_MS` (45 s) + `LATENCY_ALLOW_MS` (30 s) [inf], so
  a report that arrives late no longer races the loss.
- A heard, moving aircraft that drives into a silent, unparked one fades the silent one. That one is evidently gone
  (`staleOverrun`, 0-1 per window).
- (*Correction, fix round 3, M1:* this was wrong on runways.
  - A silent aircraft stayed standing on the runway while other traffic landed or rolled through it, and
    `staleOverrun` faded it only after the two bodies had overlapped (margin 0).
  - Measured on the 68b7c07 engine with the final harness: `stale_on_runway_frames` pat 56, weekend 550, od3p 54;
    `stale_overlap_frames` heli 3, pat 18, weekend 78.
  - Since round 3, a silent fixed-wing aircraft on a runway continues its take-off, or brakes to the first exit it can
    make and is kept clear of the runway (`runwayCont`). A mover fades a silent aircraft before the bodies would touch
    (`staleAhead`).
  - Both gates are 0 in all seven windows; see section 8.2.)

| Window | Silent aircraft kept (`groundLostKept`) |
|---|---|
| heli | 9 |
| pat | 13 |
| night | 1 |
| weekday | 6 |
| weekend | 16 |

**F3 — OAK arrivals faded high.** An arrival whose next fix is a ground fix more than 3 km away (OAK; its runways are not
modelled) fell into the generic hole rule. That rule hid the body at 55-2,063 ft.

- A *far* transition (`farTransition`) now flies a curve to a touchdown short of the roll fix, then rolls hidden.
- A far departure waits hidden at lift-off, then flies along the next fix's track.
- Air dead-reckoning hides a fixed-wing below 5 m/s.

**F4 — ground physics shuttling on grass.**

- **Root cause.** `GroundPhysics.resolve` decided "stationary" by the body's speed, so a body driving to its seek offset
  counted as *moving*. Its offset decayed, its target swung back, and it shuttled ~12 m to and fro for a minute. In the
  heli window this was 577 of 773 off-pavement samples, with `route = 1`.
- **The fix.** A body is now stationary when its *target* rests (`restPose`), whatever its own speed. The offset is kept
  while the target rests and decays from where it is once the target moves.
- **Other changes:**
  - Off-pavement ground fixes snap to the nearest paved point within 25 m, unless that point is inside a building
    [inf].
  - Roll fixes snap to the runway axis.
  - A route reversal over its first or last 15 m is penalised, and out-and-back spurs are removed (`despur`).
  - The rest-jitter threshold is 0.3 m.
  - `grass_route_frames` was reported but not gated; it is gated now.
  - Section 6.1's attribution was corrected.

**F5 — straight air-ground chord ('ag:lin').** When no take-off or landing plan fitted, the engine drew a straight chord
between an air fix and a ground fix. Finals and lift-offs could then be misaligned with the runway. The chord is gone:

- **Near failures** (`fallbackTransition`) roll along the runway axis: touchdown at threshold + 30 m or later, then the
  exit route.
  - A take-off with no feasible plan whose ground fix is more than 30 m of taxi route from the runway is not drawn
    rolling along taxilanes at take-off speed. It fades out where it stood and fades in on its climb-out (`replaceSignal`;
    1 case, heli window). This is a re-placement after a signal loss. The teleport count does not flag it, because the
    distance fits within 1.5 × speed × absence.
    (*Correction, fix round 3, M3* - first written in iteration 2 (m8 / F8), updated after the final recheck:
    - The fade-in was not harmless. Measured on the 68b7c07 engine with the final harness: the heli case faded in 743 m
      away over grass after a 33.5-s absence, and a weekend take-off faded in 2,025 m away (`ground_air_reappear`
      heli 1, weekend 1; `teleports_signal_hwd` heli 1; section 8.4).
    - The round-2 count let both pass because it allowed the larger of the two speeds.
    - Since round 3, a take-off across a hole is reconstructed on the runway (section 8.3). When no plan fits, it is
      hidden from its last ground position until its first airborne fix and appears THERE, at its reported height (the
      owner's M3 rule; `transitionFor`, `tr.m3Log`).
    - `fallbackTransition` / `replaceSignal` is no longer reached for take-offs at HWD (`replaceSignal` heli 1 → 0).
    - The harness counts such a case as `m3_hidden_takeoffs` only when the body appears at that fix within 8 s. Any
      other ground → air re-appearance fails `ground_air_reappear`.
    - Open (final recheck F3, section 8.6): 3 take-offs are hidden although a runway is consistent with their first
      airborne fix. The owner's rule does not allow that.)
- **Air curves** (`flightCurve`) are Hermite curves unless the curvature needs more than 30° of bank at the flown speed
  [inf].
  - Then `motion.js turnFlight` builds a turn-limited Dubins CSC path at 25 / 30 / 35° of bank.
  - It has a straight final of 300 m (600 m for jets) and a straight initial climb-out of 500 m (1,500 m for jets, and at
    most 0.4 × the distance) [inf].
- **Contacts before the threshold** that report only an altitude stay airborne.
- **Slow runway contacts** (< 0.7 × Vapp on the runway) are on the ground.
- **Implausible air fixes** are rejected. These are fixes whose implied acceleration exceeds 2 g over 2-20 s; three
  agreeing fixes override the rejection, and repeated copies of a rejected report are ignored.
- **New measures in the harness:**
  - `transition_linear` (INFO).
  - The gate `misaligned_transitions`: a lift-off or touchdown more than 15° off the runway heading, measured 2-12 s
    around it, within 2.5 km of the field.

**F6 — `--record` guard.** The guard lower-cased the path, so `Refs/Cache/Local/rec` passed on a case-sensitive file
system, and that directory is not gitignored. `record_dir_check` now checks the real path case-sensitively:

- Inside hwd3d it allows only `refs/cache/local/…` or `out/…`, not `out/replay/…`.
- It then requires `git check-ignore -q --no-index` to report a would-be recording file as ignored.
- Outside a work tree the directory is allowed. Without git, only the path rule applies.

**F7 — late-flag forget reached only open SSE streams, and only the last event.**

- The Hub keeps every forget event for 10 min, with the seq at which each key was first published.
- `/api/adsb?since=<seq>` adds `"forget": [keys]` for the events after `since` whose key the client had already seen.
- The SSE loop sends every pending event.
- `feed.js` polls with `?since=`.
- `traffic.forget` marks the track `maskWhy: 'd1'`.

**F8 — phone.** Several controls were smaller than 44 px (the sheet grab was 34 px). The view row also ran off the right
edge under the icons.

- The view buttons now wrap onto two rows.
- Icons, grab, stats line (one `#statsbtn` button), search and card actions are at least 44 px.
- The credit line and the pop-up sheets sit below the second view row.

**F9 — stale docs and image caption.**

- Image 3's caption now marks the pre-fix false "IDENTITY WITHHELD - LADD / PIA" header (`docs/phase2/SOURCES.json`).
- These places were corrected in place, marked *correction, fix round 2*:
  - the teleport row of 2.1 (after line 67);
  - the "not seen" list of section 3 (e);
  - the attribution in 6.1;
  - rows 1 and 2 of 6.5;
  - the weekday window in 6.2.
- `phase2_traffic.md`, `phase2_relay.md`, `phase2_app.md`, `phase2_fork_map.md` and `CLAUDE.md` describe the new
  behaviour.

### 7.3 P3's harness, strict (`node tools/traffic/replay_engine.mjs <w> --strict`)

(*Note, fix round 3:* these are the round-2 numbers of the round-2 harness.
- The same engine (68b7c07) measured with the final harness, next to the final engine, is in section 8.4.
- The per-iteration tables of round 3 are in 8.8.3, 9.3 and `phase2_traffic.md` §7.)

| Check (10-Hz samples unless stated) | heli | pat | night | weekday | weekend |
|---|---|---|---|---|---|
| Teleports, engine + signal | 7 → **0** | 3 → **0** | 1 → **0** | 5 → **0** | 12 → **0** |
| Window re-entries | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| Ghost-parked frames | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 1 → **0** |
| Slow lift-offs / hard stops / air hover / heli in building / label contradictions | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| Hops | 0 → 0 | 1 → **1** | 0 → 0 | 0 → 0 | 1 → **0** |
| Route samples with a wheel on grass (`grass_route_frames`) | 579 → **9** | 141 → **58** | 1 → **1** | 1 → **5** | 110 → **74** |
| Misaligned lift-offs / touchdowns (> 15°) | 3 → **0** | 0 → 0 | 0 → 0 | 1 → **2** | 4 → **1** |
| Straight air-ground chords (`transition_linear`, INFO) | 23 → 0 | 20 → 0 | 10 → 0 | 16 → 0 | 26 → 0 |
| Fixed-wing ground samples off pavement (site + NAIP) | 786 → 42 | 376 → 99 | 1 → 1 | 57 → 37 | 845 → 143 |
| Fixed-wing in a building footprint | 19 → 0 | 0 → 0 | 0 → 0 | 2 → 2 | 29 → 29 |
| Ground planform overlaps, one body stopped (frames / pairs) | 0 → 3 / 1 | 8 / 1 → 24 / 2 | 0 → 0 | 0 → 0 | 75 / 1 → 78 / 2 |
| **RESULT** | FAIL → **FAIL** (grass 9) | FAIL → **FAIL** (hop 1, grass 58) | FAIL → **FAIL** (grass 1) | FAIL → **FAIL** (grass 5, misaligned 2) | FAIL → **FAIL** (grass 74, misaligned 1) |

The fixed-wing ground-sample denominator grew: heli 173,126 → 237,456 and weekend 227,715 → 310,934. Silent aircraft are
now drawn, so they are sampled.

**Event counts against the offline classifier.** Weekend take-offs were 7 live against 9 offline, the same as before.
There is one new difference, not traced in this round (*traced in round 3 iteration 2: one C172 take-off emitted twice,
15 min apart - fixed, section 8.8.2 F10*):

| Window | Event | Live before → after | Offline |
|---|---|---|---|
| Weekday | Touch-and-go | 13 → 13 | 14 |
| Weekday | Take-off | 6 → **7** | 6 |
| Weekend | Touch-and-go | 24 → 24 | 25 |
| Weekend | Full-stop landing | 9 → 10 | 10 |
| Weekend | Low pass | 18 → 18 | 15 |

Scope-HWD events fell: weekday 22 → 18, weekend 36 → 30. Unpark events fell too (weekday 9 → 7). This is consistent with
fewer remove-and-re-create cycles [inf].

### 7.4 The reviewer's scratch harness, re-run on its three windows

The script is `recheck/harness2.mjs`, a scratch file of the review that is not in the repo. Its "before" is the review's
own measurement of the fix-round-1 code.

| Measure | heli | pat | night |
|---|---|---|---|
| Re-appearance jumps after any absence (`reappJump`) | 7 → **0** | 3 → **0** | 1 → **0** |
| Cuts started / jumps | 5 / 5 → **0 / 0** | 2 / 2 → **0 / 0** | 1 / 1 → **0 / 0** |
| Vanished while moving, not fading (`vanishMoving`) | 8 → 2 | 9 → 1 | 9 → 1 |
| Height of those vanishes | 76-2,063 ft → 7-8 ft | 55-408 ft (+ 1 on the ground) → 5 ft | 1-775 ft → 5 ft |
| Fixed-wing samples off pavement (`fw_off`) | 786 → 42 | 265 → 99 | 1 → 1 |
| Fixed-wing in a building footprint (`g_in_bld`) | 289 → 179 | 0 → 0 | 0 → 0 |
| Air speed > 1.25 × reported + 10 kt (`a_overspeed`) | 6 → 0 | 0 → 0 | 0 → 0 |
| Air crab > 15° (`a_crab15`) | 478 → 0 | 103 → 0 | 0 → 0 |
| Ground body moving backwards (`g_back`) | 56 → 47 | 37 → 12 | 42 → 23 |
| Ground planform overlaps (`ovl_g`) | 0 → 3 | 8 → 24 | 0 → 0 |
| Phase-label contradictions / stale park poses | 0 / 0 → 0 / 0 | 0 / 0 → 0 / 0 | 0 / 0 → 0 / 0 |

The remaining `vanishMoving` cases are all jet arrivals to OAK. They now go out of sight at touchdown at 5-8 ft, where the
hidden far roll begins. Before, 19 of 26 vanished above 100 ft.

`g_in_bld` counts fixed-wing aircraft taxiing into hangar footprints (residual (d) of fix round 1). P3's own measure, which
excludes hangar-door spots, gives 0 in this window.

### 7.5 Other checks

| Check | Result |
|---|---|
| `python3 tools/live/test_relay.py` | 22 tests OK. New: `test_forget_reaches_pollers_and_every_pending_event`, `test_record_dir_case_sensitive_and_git_ignored` |
| `node tools/live/test_shim.mjs` | PASS |
| `hwd_live_server.py --replay rec_pack --record Refs/Cache/Local/rec` | refused, exit 1, no `Refs/` directory created |
| `feed.js` poll with a mocked `fetch` | requests `api/adsb`, then `api/adsb?since=5`; the forget list applied; seq 7 |
| Spawned replay relay (scratch job), `api/adsb?since=<seq>` and `?since=abc` | both answer the snapshot (200), 0 console errors |
| `MOBILE=1 RELAY=none node livetest.mjs jobs/phone_ui.mjs` | 53 controls in the default, sheet-open and card-open states: 0 smaller than 44 px, 0 off-screen, 0 covered; page scroll width = viewport; 0 console errors |
| Synthetic late flag in the strict harness (`d1_late_flag_forget`) | masked, `maskWhy` 'd1', no registration: 0 failures in all five windows |
| `node --check` on every edited JS file | OK |
| In-app run `phase2_run_job.mjs`, desktop, 8 min of the weekend hour (20:00Z), spawned relay with `--ident type-only` | **Teleports:** none counted.<br>**D1:** 53 tracks, all type-only; 0 leak or key hits.<br>**Pavement:** 42 of 19,680 fixed-wing ground samples off pavement, 34 of them on a route; 0 in buildings; 0 planform overlaps.<br>**Console:** 0 errors.<br>**Images:** overview and West Hangars looked at. |

### 7.6 Images (looked at)

- `phase2_fix2_13_phone_view_row.jpg`: the phone top bar. The five view buttons wrap onto two rows, clear of the 44-px
  icons; the credit line sits below them.
- `phase2_fix2_14_card_no_signal_phone.jpg`: a silent aircraft's card. It reads "No signal · last position", with the
  inf marker and "last signal 2 min ago".
- `phase2_fix2_15_no_signal_taxiway_phone.jpg`: a silent single-engine aircraft drawn on the taxiway by a hold bar,
  where its signal stopped. With the fix-round-1 code such an aircraft faded out there. A helicopter is in the
  foreground.
- All three are type-only (D1); their notices are in `docs/phase2/SOURCES.json`.
- `phase2_run_3_card_stale_parking_phone.jpg` is kept as a record of the pre-fix state, and is captioned as such.

### 7.7 Per-finding status

| # | Finding | Status | Evidence |
|---|---|---|---|
| F1 | Teleports: re-placements after absences > 5 s uncounted; 6 / h gate; docs :67 / :223 | fixed | any-absence count in both harnesses; teleports 7 / 3 / 1 / 5 / 12 → 0 / 0 / 0 / 0 / 0; reviewer `reappJump` 7 / 3 / 1 → 0; gate 0; docs corrected |
| F2 | Silent aircraft vanish off aprons; race with `seen_pos` latency; doc :392 | fixed | kept as `no_signal` [inf] for 30 min; latency allowance 30 s; continuation anchors; images 14 / 15; 6.5 row 2 corrected. *Correction (fix round 3): not on runways. A silent aircraft was kept standing on the runway while others landed through it (M1); fixed in round 3, section 8.2* |
| F3 | OAK arrivals fade at 125-459 ft | fixed | far transitions; remaining vanishes at 5-8 ft (touchdown), before 76-2,063 ft |
| F4 | GroundPhysics seek / decay oscillation; `grass_route_frames` not gated; §6 attribution | fixed (root cause); residual open | stationary by target rest state; pavement snap; gated; route-on-grass 579 / 141 / 1 / 1 / 110 → 9 / 58 / 1 / 5 / 74 (the gate still fails); attribution corrected |
| F5 | 'ag:lin' straight chord; misaligned finals; transitions not counted | fixed (root cause); residual open | no chord (`transition_linear` 0 in all windows); turn-limited aligned finals; misaligned 3 / 0 / 0 / 1 / 4 → 0 / 0 / 0 / 2 / 1 (gated, still fails). *Correction (fix round 3): the take-off fallback of 7.2 F5 faded in over grass (M3); replaced in round 3, section 8.2. Misaligned transitions are 0 in all seven windows since round 3 (8.4)* |
| F6 | `--record` guard lower-cases paths | fixed | case-sensitive real-path rule + `git check-ignore`; test; CLI probe refused |
| F7 | Forget only via SSE, only the last event, no `maskWhy` | fixed | `?since` forget for pollers, pending event list, `maskWhy` 'd1'; relay test + harness check |
| F8 | Phone targets < 44 px; view row off-screen / covered | fixed | wrapped view row, 44-px controls; `jobs/phone_ui.mjs` 53 / 0 |
| F9 | Stale docs / image caption | fixed | run_3 re-captioned; 2.1, 3 (e), 6.1, 6.2, 6.5 corrected |

### 7.8 Residuals and limits (not verified)

**Strict harness still fails.** `--strict` fails in all five windows:

- route samples on grass: 1-74 per hour (≤ 7.4 s of drawn time);
- 1 hop in pat (a single-engine piston at 68 s, 54 m, 0 ft: a ground / air flip at lift-off);
- 3 misaligned transitions: two lift-offs in the weekday window (25° and 67°) and a touchdown in the weekend window
  (18°).

**Where the grass samples cluster**, as 50-m cells (x, z):

| Window | Cells |
|---|---|
| pat | (-500, -500), (-200, -300) |
| weekday | (-250, -300) to (-350, -350) |
| weekend | (650, 550), (200, 300), (100, 250) |
| heli | (-50, -200) |

None of these residuals was traced to a root cause in this round. (*Round 3 traced them to gaps of the NAIP-derived
pavement mask - corners without their fillet, 1-2-m notches at pavement edges - see `phase2_traffic.md` §7; the counts
are unchanged in round 3 iteration 2, section 8.8.4.*)

**Ground planform overlaps rose.** With one body stopped they rose in pat (8 → 24 frames, 2 pairs; one pair is a
run-up aircraft and a hold-short aircraft 9.7 m apart at 28R) and heli (0 → 3). They are reported but not gated.

(*Correction, fix round 3, M1 / m4:*
- Since round 3 these overlaps are gated at 0: `ground_overlap_frames` (a moving body against a parked, resting or
  silent one) and `stale_overlap_frames`.
- Much of the weekend's 78 frames, and the heli 3, were moving aircraft driving through silent ones (M1).
- Measured with the final harness: 68b7c07 heli 3, pat 24, weekend 78 frames; final engine pat 6 (a pair whose reported
  positions are about 9 m apart), 0 elsewhere (section 8.4).
- One moving-vs-stationary overlap outside the gates remains (final recheck F9, section 8.6).)

**The new event difference is not traced:** weekday take-offs, 7 live against 6 offline. (*Traced and fixed in round 3
iteration 2, section 8.8.2 F10: the live classifier emitted one C172 take-off twice; now 6 against 6.*)

**Not run:**

- Live mode (adsb.lol / adsb.fi) was not run in this round. The `?since` path was exercised against the replay relay and
  a mocked `fetch`, not against a real late flag in live traffic.
- No real phone was used. The phone check is Chromium at 390 × 844, DPR 1, with touch emulation.

**Inferred, not sourced** [inf]:

- the 90-s signal-loss split;
- the 30-s latency allowance;
- the 30-min silent keep;
- the 25-m pavement snap;
- the bank limits and the final / climb-out lengths;
- the 2-g fix rejection.

**In-app teleport counter.** The run's JSON has no `teleports` key, because the counter keys were created only on the
first count; they are now initialised to 0. The counter was not shown to fire on a planted case.

**In-app re-placement cuts.** The in-app engine logged 59 re-placement cuts in 8 min (68 air-error triggers). The offline
harness logs 5-9 per hour, and round-1 in-app runs logged 98-118 in 12.5 min.

- The relay replays the whole Bay Area recording (53 tracks) where the P3 pack holds fewer.
- Neither harness counted a teleport, so these are probably tracks outside the drawn window [inf]. This was not
  traced.

**OAK.** OAK's runways are not modelled. Far arrivals and departures are drawn up to touchdown and from lift-off only.

**Teleport definition.** A disappearance followed by a reappearance within 1.5 × speed × absence + 10 m is not counted.
This is the same rule as the reviewer's `reappJump`, and the hidden take-off of 7.2 F5 passes under it.
(*Correction, fix round 3:* the rule has changed since.
- A ground → air re-appearance is allowed only the distance at the speed the body had *before* it vanished.
- A re-placement fade counts as an absence (iteration 3).
- A declared M3 appearance must be at its fix.
- Under the final count, the 68b7c07 hidden take-off of 7.2 F5 is a signal teleport (heli 1, section 8.4).)

## 8. Review fix round 3 (2026-11-13 to 2026-11-14)

The third review (the recheck of fix round 2) raised three major findings (M1-M3) and five minor ones (m4-m8). Round 3
fixed them and was then rechecked three times:

| Pass | Findings | Record |
|---|---|---|
| Round 3, first fixes | M1-M3, m4-m8 | `phase2_traffic.md` §4 / §7 "Fix round 3", `phase2_relay.md` (m6), `phase2_app.md` §9 (m7) |
| Recheck → iteration 2 | F1-F3 major, F4-F10 minor | 8.8 below; `phase2_traffic.md` §7 "Iteration 2 results" |
| Second recheck → iteration 3 | F1 major, F2-F8 minor | section 9; `phase2_traffic.md` §7 "Iteration 3 results" |
| Final recheck | F1 major, F2-F9 minor | **open**, 8.6 |

Round 3 is not accepted. Its code is in the WIP checkpoints b0d55c1, 47271d1 and 62fc2f8; the last one holds the final
engine measured here. Round 3 changed mainly `js/live/traffic.js` (the motion engine), `classifier.js`, `feed.js`, `ui.js`, `app.js` and `live.css`; the relay
(`hwd_live_server.py`, m6) and its tests; the strict harness `tools/traffic/replay_engine.mjs`; the pavement mask
(`tools/traffic/build_pave_mask.py` → `js/aircraft/pave_naip.js`); the new job `jobs/horizon.mjs`; and these docs.

This section is the summary of the whole round. Every count and measurement in 8.2-8.5 comes from runs made for this
section on this machine (4 CPUs, Node 22); the constants are read from the code. The findings of the final recheck in
8.6 are quoted from its report, and marked where I re-measured them.

### 8.1 Method

**Windows.** Seven windows, all 10 Hz, deterministic:

| Window | Pack |
|---|---|
| heli, pat, night | the reviewer's packs (full identity, gitignored, `out/review_traffic/`); hours as in section 7 |
| weekday, weekend | P3's packs (`out/replay/`); hours as in section 7 |
| od3s, od3p | two local type-only packs around OD3 case S (SF50 take-off) and OD3 case P (PC-12 landing), built by `tools/live/build_replay.py` into `out/od3/packs/` (gitignored). Their times are not given here (D1) |

**Harness.** `node tools/traffic/replay_engine.mjs <w> --strict --pack <pack>`.

- Since iteration 3 it reads the opening burst as `app.js` does (`--open app`, the default). Before that, every gate was
  blind to what the app draws in its first minute.
- It now has 39 gates, all with limit 0 [inf]. Round 3 added 28 of them:
  - *iteration 1 (M1-M3, m4, m5):* `stale_on_runway_frames`, `stale_overlap_frames`, `fast_off_runway_frames`,
    `landing_roll_speed_rise`, `liftoff_off_runway`, `touchdown_off_runway`, `ground_air_reappear`,
    `ground_overlap_frames`, `fw_in_building_frames`, `taxi_label_fast_frames`;
  - *iteration 2:* `off_reports_samples`, `air_overspeed_samples`, `air_climb_samples`, `low_air_off_runway_frames`,
    `air_pair_close_frames`, the planted cases `planted_reappear` / `planted_low_air_box`, and five label gates inside
    `label_contradictions`;
  - *iteration 3:* `air_float_runway_frames`, `recon_substall_samples`, `air_substall_samples`, `label_vertical_sense`,
    `label_base_aligned`, `label_taxi_stopped`, `label_roll_flicker`, `tg_no_contact`, `m3_hidden_runway_consistent`,
    `planted_open_burst`.
- Each gate is defined in the harness header and in 8.8.1 / 9.1.

**Before and after** (8.4):

- *Before* is the committed fix-round-2 engine. I took `js/`, `data/` and `tools/` of 68b7c07 with `git archive`, into
  a scratch directory, and ran it through the **final** harness.
- *After* is a snapshot of the working tree. Its engine and harness files are identical to commit 62fc2f8
  (`js/live/traffic.js` sha256 `8becc281…`).
- 68b7c07 has no `traffic.spd(tr)`, which two gates read for their reference speeds and climb rates. The scratch copy of
  the harness therefore got a shim: the current speed tables (`speedsOf`), with the current per-aircraft scaling to the
  slowest airborne fix ≥ 150 ft and > 20 kt. The current engine also requires `alt_baro` and `alt_geom` to agree within
  200 ft for that fix; the shim cannot check this, because 68b7c07 does not store `alt_geom`.
- Two gates read engine fields that 68b7c07 does not have: the reconstruction target and `tr.m3Log`. Their before
  column reads n/a.
- The per-iteration before → after tables of the fixers (each measured with that iteration's harness) stay in 8.8.3,
  9.3 and `phase2_traffic.md` §7. I did not re-run them.

**D1.**

- Cases are named by window, ICAO type and an anonymous label ("case A"). No time of an aircraft's event is given.
- An aircraft flagged LADD / PIA is named by class only. I checked locally, against the full-identity packs (types and
  counts only), that every type named here next to one of the five dated windows (heli, pat, night, weekday, weekend)
  belongs to unflagged aircraft. The OD3 windows are not dated here. The one exception is a flagged business jet in the
  weekend window, named here only as "the weekend business jet". Sections 8.8 and 9 were changed to match;
  `phase2_traffic.md` still names its type (8.7).

### 8.2 The third review's findings and their status

Gate counts are 68b7c07 → final (8.4).

**M1 - silent aircraft left standing on a runway.** Others landed through it. *Fixed.*

- What changed (`runwayCont` / `planRunwayCont`): a silent fixed-wing aircraft on a runway continues its take-off, or
  brakes on the centreline (≤ 2 m/s² for GA, 2.5 for others) to the first exit it can make and rolls clear of the
  runway.
- Since iteration 3, a silent aircraft last heard low on final continues its landing to an exit (`airLandCont`).
- A moving aircraft fades a silent one *before* their bodies would touch (`staleAhead`).
- Evidence: `stale_on_runway_frames` pat 56, weekend 550, od3p 54 → 0; `stale_overlap_frames` heli 3, pat 18,
  weekend 78 → 0.

**M2 - landing roll re-routed through the taxi graph onto the other runway.** *Fixed.*

- What changed (`rollExitRoute`): the roll stays on its own runway's centreline to an exit. Taxi routes avoid runway
  links (× 8 cost). `rollParts` holds and brakes so that the roll fits the hole.
- The body no longer speeds up on a roll to close a gap.
- Evidence: `fast_off_runway_frames` pat 58, weekday 39 → 0; `landing_roll_speed_rise` 946 / 2,292 / 513 / 1,121 /
  1,305 / 0 / 112 → 0.

**M3 - take-off / landing across recorder holes; a hidden take-off faded in over grass.** *Fixed, with residuals.*

- What changed: take-offs and landings are reconstructed on the runway from type performance (8.3). A take-off that
  cannot be timed is hidden until its first airborne fix (the owner's rule).
- Evidence: `ground_air_reappear` heli 1, weekend 1 → 0; `teleports_signal_hwd` heli 1 → 0; `misaligned_transitions`
  weekday 2, weekend 1 → 0.
- Residuals: the touch-and-go reconstruction (final recheck F1). Three hidden take-offs whose runway is consistent
  (F3: `m3_hidden_runway_consistent` heli 2, weekend 1).

**m4 - ground overlaps; wings in buildings.** *Partly fixed.*

- What changed:
  - `routeBlock` routes around parked, resting and silent aircraft; `staleAhead` (M1).
  - Iteration 2: the building test also samples the wing / tail outline.
  - Iteration 3: each taxi link carries its building clearance, and a too-narrow link is penalised 400 m. A slow body
    with a wing over a hangar footprint is faded as being in its door.
- Evidence: `ground_overlap_frames` heli 3, pat 24, weekend 78 → 0 / **6** / 0; `fw_in_building_frames` heli 179,
  weekday 2, weekend 225, od3p 30 → **11 / 2 / 57 / 11**.

**m5 - fast fixes flagged on the ground.** *Fixed, with a residual.*

- What changed:
  - Such a fix is drawn on the centreline of the runway it follows (within 60 m), or flying low at ≥ 0.8 VR.
  - A taxi label is never shown above 35 kt.
  - Iteration 3: a ground fix at ≥ 0.9 VR beside the runway is airborne. The counter `fastOffAir` reads weekday 8,
    weekend 4.
- Evidence: `taxi_label_fast_frames` 0 / 4 / 8 / 52 / 12 / 7 / 1 → 0.
- Residual: weekday C152 case A (final recheck F4).

**m6 - late flag lost on reconnects, pauses and old publications (relay).** *Fixed.*

- What changed:
  - SSE ids, with `Last-Event-ID` / `?since=` answered by the forget events since then.
  - `forget_horizon` when they have expired.
  - A seq base per relay process, and first publications kept for 24 h (`phase2_relay.md`).
  - `app.js` passes `onHorizon` (iteration 2).
- Evidence: `python3 -I -B tools/live/test_relay.py` 26 tests OK (re-run). `jobs/horizon.mjs` PASS in iteration 2 (not
  re-run here).

**m7 - altitude display.** The list, labels and card showed the raw `alt_baro` from a fix up to 60 s ahead.
*Fixed, with a residual.*

- What changed:
  - One value per aircraft (`phase2_app.md` §9).
  - Iteration 2: the drawn height, a single source.
  - Iteration 3: the height above the ground or runway below 300 ft.
- Evidence: the reviewer's probe in iterations 2-3 (`phase2_app.md` §10; not re-run here).
- Residual: final recheck F7 (the method tooltip).

**m8 - docs that overstated or no longer matched the code.** *Fixed in this section.*

- What changed: corrected in place in iteration 2 (7.2 F5, 7.3, 7.8, `phase2_traffic.md` §4 / §7). Corrected again
  here, for what was still wrong: 7.2 F1 / F2 and F5, 7.7, 7.8, 9.2 F3, 9.4.

### 8.3 Take-off and landing reconstruction across recorder holes (OD3)

The recorder heard ~14 s of every minute. A take-off or landing usually falls in a ~46-s hole between a ground fix and
an airborne fix. The engine draws it from the fixes on both sides (`traffic.js transitionFor`).

**Take-off** (`planTakeoff`, `departureRunway`, `takeoffAir`):

1. **Runway.** An aircraft already on a runway and aligned takes that one. Otherwise the engine takes the runway end
   most consistent with the first airborne fix: its track within 150° of the runway heading, its offset from the
   extended centreline for the distance flown, near the aircraft, in the current flow [inf weights].
2. **Ground part.**
   - Taxi to a line-up point that leaves the table roll × 1.1 + 40 m of runway ahead. This is the runway end or an
     intersection.
   - Pivot onto the centreline and wait lined up for ≤ 30 s.
   - Roll from rest on the centreline at one constant acceleration VR² / (2 × ground roll).
3. **Lift-off.** At VR, ≥ 30 m before the runway end. When the first airborne fix lies on the climb-out, the lift-off is
   also far enough before it to climb to its height at twice the type's climb rate, plus 30 m.
4. **Climb-out.**
   - A straight on the runway heading of 400 m (jets 800 m), then a bank-limited join to the fix (`flightCurve`).
   - The climb starts level at the wheels and rises monotonically.
   - The aircraft accelerates after lift-off no harder than it rolled (≤ 2.5 m/s²).
   - Its mean climb is ≤ 2 × the type's take-off climb, or 1.25 × the reported one.
   - Its speed is 0.75-1.2 × the reported speed.
5. **Timing.**
   - The plan is timed backwards from the first airborne fix.
   - It tries an option ladder in this order: the table acceleration, 1.15 ×, 1.3 ×; climb-out straights of 250 m, then
     150 m; 1.6 ×; a 25-kt taxi with a climb-out at ≤ 1.3 × the reported speed; 2.0 ×.
   - Spare time goes to the ground: a longer wait, or a slower taxi.
   - A rolling start (seen mid-roll, or a touch-and-go) lifts off at its own speed. An aircraft at ≥ 0.9 VR is never
     stopped and launched again.
6. **No option fits** (the owner's M3 rule). The aircraft is hidden from its last ground position until its first
   airborne fix, and appears there at its reported height. `tr.m3Log` records where; the harness checks that the body
   appears within 60 m (plus what it flew) within 8 s, or counts a teleport.

**Landing** (`planLanding`):

1. **Runway.** The runway aligned with the approach fix (≤ 150 m off its axis), else the runway beside the ground fix in
   the current flow.
2. **Touchdown.**
   - In the touchdown zone, never before the landing threshold (displaced thresholds from `data/hwd_airport.js`).
   - At least 60 m before a ground fix that is still on the runway.
   - From an approach fix below 100 ft, where a 3.5° path plus a 2.5-s flare ends, with 4.5 % of the speed bled off in
     the flare.
3. **Time split** (iteration 3).
   - Candidate touchdown points: the touchdown zone, then 25-m steps to 10 m past the threshold and on to twice the zone
     distance.
   - The approach takes between L / (1.1 × the faster speed) and L / `airFloor`.
   - `airFloor` = max(vmin, min(VR, 0.97 × the reported speed)): never slower than about 1.1 × the stall speed, unless
     the aircraft was observed slower.
   - The sampled air curve stays ≥ 0.93 × that floor. The ground part takes the rest of the hole, within its drivable
     time.
4. **Roll-out.**
   - One constant deceleration when it fits; otherwise braking parts of ≤ 2.5 m/s². Firm braking only when nothing
     else fits.
   - The roll follows its own runway to an exit (M2).
   - When the next fix back-taxis: roll-out, a U-turn on the runway, back-taxi.
   - A straight final of 400 m (jets 800 m) is kept.
5. **Far landings** (OAK / SFO, no pavement model) touch down earlier instead of flying slower. Their roll is hidden.

**Unseen touch-and-go across an air hole** (`touchGoFor` / `planTouchGo`, iteration 3).

- Two airborne fixes lined up with one runway, whose air curve would be flown below the floor, or that the classifier
  calls a touch-and-go: approach, touchdown, roll, lift-off, climb-out.
- 10 such plans in the seven windows (counter `touchGoPlans`: pat 1, weekday 4, weekend 5).
- **The final recheck found all 10 physically implausible** (8.6 F1).

**Constants and their basis:**

| Quantity | Value | Basis |
|---|---|---|
| VR | 0.85 × the FAA ACD approach speed (≈ 1.1 × the landing stall speed) | the ACD approach speed is 1.3 × Vso [recalled, not re-read: inf]; factor [inf] |
| VR, SF50 | 85 KIAS | Cirrus SF50 AFM P/N 31452-001 Rev 4, "VR 80-90 KIAS" (`tools/models/sf50/SF50_FACTS.md` S5) [obs range; the mid value is inf] |
| Ground roll, SF50 | 621 m (2,036 ft) | same AFM, SL ISA, 6,000 lb [obs; the weight is inf]; 1,483-2,231 ft over 5,000-6,000 lb and -20 to +20 °C [obs] |
| Ground roll, classes | single high-wing 290 m; low-wing 300; twin 340; turboprop 450; turboprop twin 600; light jet 750; business jet 1,000; airliner 1,700; other 250 | C172S POH 960 ft [recalled, not re-read: inf]; all others [inf] (`PERF_CLS`) |
| Take-off climb | SF50 1,892 ft/min; classes 3.0-12 m/s | SF50 AFM [obs]; classes [inf] |
| Roll acceleration ladder | 1, 1.15, 1.3, 1.6, 2.0 × the table | [inf]: a lighter aircraft rolls shorter (SF50 1,483 vs 2,036 ft = 1.37 × [obs]); wind, weight and density altitude are not modelled |
| Line-up | runway ahead ≥ roll × 1.1 + 40 m; wait ≤ 30 s | [inf] |
| Lift-off margin | ≥ 30 m before the runway end | [inf] |
| Climb-out | straight 400 / 250 / 150 m (jets 800 m); acceleration ≤ 2.5 m/s²; speed 0.75-1.2 (1.3) × reported; mean climb ≤ 2 × type | [inf] |
| Touchdown zone | 150 m past the landing threshold (pistons), 200 m (turboprops), 300 m (jets) | the aiming-point marking is 1,020 ft past the threshold (FAA AC 150/5340-1M) [obs]; light aircraft touch down before it [inf] |
| Approach floor | `airFloor` as above; curve ≥ 0.93 × floor; ≥ L / (1.1 × faster speed) | [inf] |
| Low approach fix (< 100 ft) | 3.5° path + 2.5-s flare, 4.5 % speed bleed | [inf] |
| Roll-out braking | ≤ 2.5 m/s²; firm 3.6 (jets, turboprops) / 3.0 (pistons) | [inf] |
| U-turn | half circle as wide as the runway allows, wheels ≥ 1.5 m inside the edge, ≥ 30 m straight back | [inf] |
| Pattern side / TPA (silent touch-and-go continuation) | 28L / 10L left, 28R / 10R right; 600 ft AGL (800 ft for 10L/28R) | FAA NASR + Chart Supplement, `data/hwd_airport.json` [obs]; jets 1,500 ft [inf] |

**Inferred marking.** Every reconstructed sample is drawn state, not data:

- the target carries `recon`;
- the phase shown is a drawn-state phase with `src: 'inf'` and `provisional`, so the list and card show the inf marker;
- the altitude method reads `drawn` [inf].

In the OD3 traces (`pos_src`), 4,538 of 5,700 samples of case S and 2,932 of 3,900 of case P are inferred: farther than
2 s from a fix, or reconstructed.

**The OD3 cases, re-traced on the final engine.** These are my runs of the fixer's trace script, on the snapshot, with
the output in a scratch directory; 1-Hz rows, local only. In the script's final form a comment had swallowed the
ingest call, so it did not parse; I repaired that first. The `out/od3/trace_case_{S,P}` files predate the final
engine, and I did not overwrite them.

- **Case S (SF50 take-off).**
  - It lines up at the 28L end, waits ~9 s, rolls from rest on the centreline (offset 0 m) and lifts off 477 m down 28L
    at 85.5 kt, with 1,258 m left. The mean roll acceleration is 2.0 m/s²: the 1.3 × rung of the ladder on the
    AFM-derived 1.54 m/s², and inside the AFM's 452-680-m range.
  - It climbs from level with no height drop (0 → 63 ft in 8 s) to its first airborne fix at ~112 kt.
  - 0 samples off pavement or on grass.
  - The trace's own "roll start" (by phase label) now reads 8.4 kt at 4.5 m, where the fixer's trace read "from rest".
    The motion is unchanged. The phase line shows 'Lined up' for the first 2 s of the roll (3.5-7.6 kt): this is the
    2-s hold on a change into a roll label of iteration 3.
- **Case P (PC-12 landing).**
  - It touches down 411 m down 28L at ~80 kt on the centreline (roll offset ≤ 0.4 m). It brakes at ~1.2 m/s² to its
    first ground fix at 63 kt and exits.
  - Its height never rises in the 40 s before touchdown.
  - 0 samples off pavement or on grass.
  - The largest 0.1-s speed change is -3.6 m/s², at the touchdown sample.

### 8.4 Results: strict harness, 68b7c07 → final, all seven windows

10-Hz frames unless the gate says samples (1 Hz). "From" names the finding that added the gate (i2 / i3 = iteration
2 / 3). **Bold** = still failing.

| Gate (limit 0) | From | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|---|
| `stale_on_runway_frames` | M1 | 0 → 0 | 56 → 0 | 0 → 0 | 0 → 0 | 550 → 0 | 0 → 0 | 54 → 0 |
| `stale_overlap_frames` | M1 | 3 → 0 | 18 → 0 | 0 → 0 | 0 → 0 | 78 → 0 | 0 → 0 | 0 → 0 |
| `fast_off_runway_frames` | M2 | 0 → 0 | 58 → 0 | 0 → 0 | 39 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| `landing_roll_speed_rise` | M2 | 946 → 0 | 2,292 → 0 | 513 → 0 | 1,121 → 0 | 1,305 → 0 | 0 → 0 | 112 → 0 |
| `ground_air_reappear` | M3 | 1 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 0 | 0 → 0 | 0 → 0 |
| `teleports_signal_hwd` | M3 | 1 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| `misaligned_transitions` | M3 | 0 → 0 | 0 → 0 | 0 → 0 | 2 → 0 | 1 → 0 | 0 → 0 | 0 → 0 |
| `ground_overlap_frames` | m4 | 3 → 0 | 24 → **6** | 0 → 0 | 0 → 0 | 78 → 0 | 0 → 0 | 0 → 0 |
| `fw_in_building_frames` | m4 | 179 → **11** | 0 → 0 | 0 → 0 | 2 → **2** | 225 → **57** | 0 → 0 | 30 → **11** |
| `grass_route_frames` | round 2 | 9 → **9** | 58 → **7** | 1 → **1** | 5 → **1** | 84 → **33** | 0 → 0 | 6 → **6** |
| `taxi_label_fast_frames` | m5 | 0 → 0 | 4 → 0 | 8 → 0 | 52 → 0 | 12 → 0 | 7 → 0 | 1 → 0 |
| `off_reports_samples` | i2 F1 | 5 → 0 | 0 → 0 | 0 → 0 | 11 → 0 | 0 → 0 | 0 → 0 | 5 → 0 |
| `air_overspeed_samples` | i2 F1 | 21 → **1** | 5 → **3** | 4 → **1** | 6 → 0 | 12 → **5** | 0 → 0 | 1 → 0 |
| `air_climb_samples` | i2 F1 | 81 → **61** | 80 → **80** | 5 → **5** | 42 → **31** | 166 → **124** | 8 → **3** | 22 → **24** |
| `low_air_off_runway_frames` | i2 F2 | 60 → 0 | 34 → 0 | 0 → 0 | 5 → 0 | 353 → 0 | 0 → 0 | 0 → 0 |
| `air_pair_close_frames` | i2 F3 | 0 → 0 | 0 → 0 | 0 → 0 | 17 → 0 | 44 → 0 | 0 → 0 | 0 → 0 |
| `label_contradictions` | round 1, i2 F6 | 201 → 0 | 106 → 0 | 68 → 0 | 207 → 0 | 338 → 0 | 23 → 0 | 45 → 0 |
| `recon_substall_samples` | i3 F1 | n/a → 0 | n/a → 0 | n/a → 0 | n/a → 0 | n/a → 0 | n/a → 0 | n/a → 0 |
| `air_substall_samples` | i3 F1 | 61 → 0 | 127 → 0 | 52 → 0 | 219 → 0 | 136 → **8** | 2 → 0 | 29 → 0 |
| `air_float_runway_frames` | i3 F1 | 0 → 0 | 85 → 0 | 0 → 0 | 542 → 0 | 40 → **9** | 0 → 0 | 0 → 0 |
| `label_vertical_sense` | i3 F4 | 5 → 0 | 41 → 0 | 1 → 0 | 55 → 0 | 101 → 0 | 0 → 0 | 3 → 0 |
| `label_base_aligned` | i3 F4 | 193 → 0 | 474 → 0 | 21 → 0 | 139 → 0 | 514 → 0 | 0 → 0 | 163 → 0 |
| `label_taxi_stopped` | i3 F4 | 442 → 0 | 206 → 0 | 54 → 0 | 674 → 0 | 822 → 0 | 78 → 0 | 137 → 0 |
| `label_roll_flicker` | i3 F4 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → **1** | 2 → 0 | 0 → 0 | 0 → 0 |
| `tg_no_contact` | i3 F4 | 2 → **1** | 3 → **1** | 0 → 0 | 3 → **1** | 4 → **2** | 0 → 0 | 1 → 0 |
| `m3_hidden_runway_consistent` | i3 F6 | n/a → **2** | n/a → 0 | n/a → 0 | n/a → 0 | n/a → **1** | n/a → 0 | n/a → 0 |
| `ghost_parked_frames` | round 1 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 3 → **3** | 0 → 0 |
| the other 12 gates (see below) | | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| **gates failing / RESULT** | | 17 → **6** FAIL | 17 → **5** FAIL | 10 → **3** FAIL | 18 → **5** FAIL | 21 → **8** FAIL | 6 → **2** FAIL | 14 → **3** FAIL |

The other 12 gates: `teleports_engine`, `slow_liftoff`, `hard_stops`, `hops`, `air_hover_frames`, `heli_in_bldg_frames`,
`liftoff_off_runway`, `touchdown_off_runway`, `planted_reappear`, `planted_low_air_box`, `planted_open_burst`,
`d1_late_flag_forget`.

How to read the table:

- **The final column equals the fixer's iteration-3 "after" (9.3) in every cell.** The final recheck said the same.
- **What the 68b7c07 column shows:**
  - heli: a hidden take-off faded in 743 m away over grass after a 33.5-s absence (M3; the signal teleport and the
    ground → air re-appearance);
  - weekend: one more such re-appearance, 2,025 m away over grass;
  - the silent aircraft on runways (M1) and the roll-outs that sped up (M2);
  - pat / weekday: the floats and sub-stall approaches that iteration 3 removed.
- **Not improved:** `label_roll_flicker` weekday 0 → 1, and `air_climb_samples` od3p 22 → 24 (pat 80 → 80).
- **INFO counters, final engine:**
  - `m3_hidden_takeoffs` heli 2, weekend 1. The harness found each body at its fix.
  - `transition_linear` 0 everywhere. `transition_fallback` 0 / 4 / 0 / 3 / 3 / 0 / 0. `replaceSignal` heli 1 → 0.
- **Events against the offline classifier:**

  | Window | Event | Live, 68b7c07 → final | Offline |
  |---|---|---|---|
  | weekday | take-offs | 7 → 6 | 6 |
  | weekend | take-offs | 7 → 7 | 9 |
  | weekend | touch-and-goes | 25 → 26 | 25 |
  | weekend | low passes | 17 → 16 | 15 |

  The weekend take-off difference was traced in iteration 2 (8.8.4).

### 8.5 Other checks (run for this section)

| Check | Result |
|---|---|
| `python3 -I -B tools/live/test_relay.py` | 26 tests OK |
| `node --check` on `js/live/{traffic,ui,app,classifier,feed}.js`, `tools/traffic/replay_engine.mjs`, `jobs/horizon.mjs` | OK |
| M3 cases with a longer display lookahead (`replay_engine.mjs heli --lookahead 120`, scratch copy) | Heli C172 'case B' is then planned. Heli C172 'case C' is still hidden. Both are unflagged (checked locally). With the default 60 s both are hidden; each is heard again ~1.2-1.3 km away |
| OD3 traces of case S / case P | 8.3 |
| `python3 -I -B tools/check_airport.py` (after these edits) | `RESULT: ALL HARD CHECKS PASSED`. D1: 29 committed ADS-B-derived files and 203-204 more committed text files scanned (the count moves with other workflows' files), 0 with a finding |

### 8.6 Open findings (final recheck, not fixed)

The strict harness FAILS in all seven windows (8.4). The final recheck's report lists:

| # | Severity | Finding | Status |
|---|---|---|---|
| F1 | major | **Unseen touch-and-go reconstruction (`planTouchGo`) moves in ways the aircraft cannot.** All 10 plans (pat 1, weekday 4, weekend 5; my counter agrees) hold a long ground roll near lift-off speed: 20-34 s at 44-59 kt. Then they accelerate at 3.1-4.5 m/s² right after lift-off, where the engine's own take-off table implies ~1.2 m/s² for the class. Speed peaks overshoot the next report. The labels never say touch-and-go. No gate catches it: there is no airborne-acceleration gate, and the 1-Hz `air_overspeed_samples` missed the peaks | open |
| F2 | minor | **Silent touch-and-go continuation.** A weekend single-engine piston vanishes over its crosswind leg, then pops in elsewhere, at another height, heading and speed. It is then labelled 'Climbing out 28L' for ~58 s on downwind. 9.2 F3 gave only the 82-m distance | open (9.2 F3 corrected) |
| F3 | minor | **M3 hidden take-off although a runway fits.** The owner's rule allows hiding only when no runway is consistent. Heli C172 'case B' and 'case C' and the weekend business jet are hidden (`m3_hidden_runway_consistent` heli 2, weekend 1). A 120-s lookahead plans case B only (8.5). Iteration 3 left this as a question to the owner instead of changing the behaviour | open: the behaviour still violates the rule |
| F4 | minor | **Weekday C152 'case A'.** The lift-off position is fixed (~390-400 m of 28R left; was 96-116 m). The roll is still implausible: 'ground' fixes at 59.5-61.5 kt on the runway stay on the ground. The 15-m cap of the iteration-3 rule then draws a level segment at ~47 ft just after lift-off, labelled 'Low pass' | open |
| F5 | minor | **Label contradictions the gates do not see.** (a) 'Base 28L' on aircraft lined up on short final directly over the runway at 58-7 ft: `onFinal` and `label_base_aligned` only look before the threshold. (b) 'Take-off roll 10R (provisional)' for 3 s on the weekend business jet back-taxiing at 20-21 kt. (c) 'Climbing out <rwy>' kept through crosswind and downwind, up to 165° off the runway heading and > 1 km off the axis (pre-existing). Also seen in iteration 3: a BL8 landing 28R labelled 'Landing roll 10L'. Also seen here: 'Lined up' during the first 2 s of a roll (8.3, case S) | open |
| F6 | minor | **Snapshot mode (the published iPhone artifact path).** A 'Recorded instant' is not frozen: the selected aircraft drifts on, and the card's speed and height change. Not checked against 68b7c07 | open, not re-checked here |
| F7 | minor | **Card method tooltip.** For drawn or reconstructed heights it gives the altimeter-equivalent value of the last fix as if it applied now, without saying it comes from an earlier fix | open |
| F8 | minor | **Ground pivots in place.** Bodies at ~0 kt rotate about their centre by up to 176° in a few seconds: parked aircraft swinging on position jitter, a body 'Lined up' 143° off the runway, 'Holding short' drawn on runway pavement. Both OD3 windows show it, including the SF50 leaving its FBO spot in case S (pre-existing since 68b7c07) | open |
| F9 | minor | **Strict residuals.** `grass_route_frames` 1-33, `fw_in_building_frames` 2-57, `air_overspeed_samples` 1-5, `air_climb_samples` 3-124, `ground_overlap_frames` pat 6, `ghost_parked_frames` od3s 3, `tg_no_contact` 1-2, `air_substall_samples` / `air_float_runway_frames` weekend 8 / 9, `label_roll_flicker` weekday 1, `m3_hidden_runway_consistent` 3. Outside the gates: an inferred touchdown before a displaced threshold, and one moving-vs-stationary overlap | open (numbers re-measured, 8.4) |

Causes of the residuals, where traced: 8.8.4, 9.4 and `phase2_traffic.md` §7.

### 8.7 Not verified / limits

- **Not run here:**
  - live mode (adsb.lol / adsb.fi);
  - a real phone;
  - the in-app sampler (`docs/phase2/phase2_run_job.mjs`) and the reviewer's extended harness on the final engine;
  - `jobs/horizon.mjs` and the card-altitude probes (iteration 2 / 3 results only);
  - the snapshot-mode finding F6.
- **Before column:** measured through a scratch shim for `traffic.spd` (8.1); two gates are n/a.
- **D1 in other docs.** `phase2_traffic.md` §4 / §7 (not edited here) still names the weekend business jet by its ICAO
  type in a named hour, and another flagged weekend jet type in its `grass_route_frames` residuals. This is against the
  round-1 rule ("a type plus an hour of a LADD / PIA-flagged aircraft is not repeated in committed docs", 6.1). That
  file's owner should reword both.
- **Assumptions:** every constant of 8.3 not marked [obs] is a design value [inf]. Wind, weight and density altitude
  are not modelled. Only west-flow windows were run.

### 8.8 Record of iteration 2 (as written by its fixer, 2026-11-14)

(*Note:* the numbers in 8.8 were measured by the iteration-2 fixer, with the iteration-2 harness, which ingested the
opening burst at the start time. The final numbers are in 8.4.)

Round 3 (the third review's findings M1-M3, m4-m8, recorded in `phase2_traffic.md` §4 and §7 "Fix round 3") was
rechecked; the recheck raised 10 findings (F1-F3 major, F4-F10 minor). This iteration changed
`js/live/{traffic,classifier,ui,app}.js`, `tools/traffic/replay_engine.mjs`, a new job `jobs/horizon.mjs` and these docs
(nothing committed). Windows: heli, pat, night, weekday, weekend (as in section 7) and two local OD3 windows `od3s` /
`od3p` around OD3 case S (SF50 take-off) and OD3 case P (PC-12 landing); their definitions and packs are in
`out/od3/` (gitignored). Cases are named by window, type and an anonymous label. Every number was measured on this
machine after the fixes; "before" is the round-3 engine at the start of the iteration under the same (new) harness.

#### 8.8.1 New and fixed gates (`tools/traffic/replay_engine.mjs`)

- `off_reports_samples` (1 Hz): the drawn body more than 150 m from the position interpolated between its two reports
  when they are at most 5 s apart - the late join drew aircraft kilometres and minutes behind them (F1).
- `air_overspeed_samples` (> 1.15 × the faster bracketing airborne report), `air_climb_samples` (> 1.25 × the type's
  take-off climb and > 1 m/s more than the reports and their chord support) (F1).
- `low_air_off_runway_frames`: a fixed-wing aircraft below 35 ft AGL within 2.5 km, more than 30 m beside or 300 m
  beyond every runway (F2).
- `air_pair_close_frames`: two airborne aircraft drawn within 30 m while their reports are ≥ 60 m apart; pairs whose
  reports are that close are INFO (`air_pair_close_reported`) (F3).
- Label gates inside `label_contradictions`: hold short / run-up / in hangar moving > 5 kt, lined up > 15 kt, runway
  taxi off the runway, 'No signal' moving > 2 kt, a runway label > 50 ft up (F6).
- F4: the state before a vanish now stores `ground` and `cls` (the `ground_air_reappear` gate read a field that was never
  stored and could not fire); `fw_in_building_frames` tests the planform outline (wings, tail) as well as the fuselage,
  hangar-door spots excepted; planted cases `planted_reappear` (a ground → air re-appearance must fire, a declared M3
  appearance at its fix must not, an air → air re-placement within range must not) and `planted_low_air_box` must
  evaluate to 0.
- M3 hidden take-offs (`tr.m3Log`) are counted as `m3_hidden_takeoffs` (INFO) only when the body appears within
  60 m (+ what it flew) of the declared fix within 8 s; otherwise they are teleports.

#### 8.8.2 Root causes and what changed

| # | Finding | Root cause | Change | Status |
|---|---|---|---|---|
| F1 | Late join kilometres / minutes behind; m5 roll aborted, back-taxi, second take-off | `planTakeoff` timed forwards from the last ground fix and, when the climb-out could not reach the first airborne fix, pursued the track (`xplanAir`); a rolling start needed `roll / 2 + 40 m` of runway, so a C152 at 64 kt 112 m before the end was sent to the line-up point | Timing searched backwards from the first airborne fix over a ladder of ground options (1-2 × table acceleration, shorter climb-out straights, faster taxi), spare time spent on the ground; lift-off before an on-centreline first fix; ≥ 0.9 VR never aborted; no fit → the owner's M3 hidden fallback; `xplanAir` removed; helicopter holes on the geometric curve; airborne fixes that disagree with both velocities alpha-filtered | fixed: `off_reports_samples` 91 / 63 / 13 / 5 → 0 (heli / weekday / weekend / od3p); harness2 weekday `a_overspeed` 119 → 0 |
| F2 | Runway passes drawn as S-curves over the infield grass at 0-50 ft | Air holes used Hermite / Dubins curves with the fix's own direction from a low fix beside the axis; low fixes kept their GNSS offset | Low fixes (< 100 ft over a runway / extended centreline) drawn on the axis; the hole from / into them keeps a straight along the runway; the climb from a low fix levels off instead of sinking; approaches on a glide-path profile | fixed: `low_air_off_runway_frames` 35 / 109 → 0 (pat / weekend) |
| F3 | Mid-air convergence to 9 m; TIS-B echoes drawn beside their aircraft | The echo test ran only for '~' keys (a published pack masks every key), once per report at arrival time (60 s ahead of the drawing), against a 10-s-old ADS-B fix without extrapolation | Echo test per fix at display time for every TIS-B source, extrapolated, speed / track / altitude matched, sticky through the primary's holes; air separation offset (`airSeparate`) | fixed: `air_pair_close_frames` 17 / 44 → 0; harness2 closest pair weekday 29 → 79 m, weekend 9 → 48 m |
| F4 | `ground_air_reappear` dead code; wings in hangars not tested | `V.last` had no `ground`; the building test sampled the fuselage only | `ground`, `cls` stored; outline tested; planted cases | fixed (harness); the outline test raises `fw_in_building_frames` to 179 / 2 / 225 / 30 - residual, 8.8.4 |
| F5 | 'below field elevation' on a climbing aircraft; label and picture > 100 ft apart | The label used alt_baro with the KHWD altimeter setting, anchored to the drawn path; the picture uses the calibrated GNSS height | One source: the label is the drawn height (at a fix the report as the engine reads it, between fixes the drawn path, inf); the card's second value is the height above the ground for a body drawn lower than the field elevation; the altimeter-equivalent value only in the method note | fixed: reviewer's probe 0 'below field' and 0 > 100-ft differences of 10,397 (weekend) / 10,518 (pat) / 281 (od3s) / 1,320 (od3p) samples |
| F6 | Labels contradicting the motion | Phase from the fix label / plan without a motion check; 'No signal' set for any stale track | Labels derived from the drawn motion (3 kt / 15 kt, the runway rectangle); continued motion of a silent aircraft labelled by its plan | fixed: `label_contradictions` 220 / 107 / 54 / 269 / 329 / 23 / 37 → 0 |
| F7 | `app.js` did not pass `onHorizon` | — | `onHorizon: (h) => traffic.forgetHorizon(h)`; `HWD.feed()`; `jobs/horizon.mjs` | fixed: job PASS (8.8.3) |
| F8 | Docs stale / overstated | — | 7.2 F5, 7.3, 7.8 corrected in place; this section; `phase2_traffic.md` §4 / §7 corrected and extended; `phase2_fork_map.md` 2.1; `CLAUDE.md`; `phase2_app.md` | fixed |
| F9 | OD3 blemishes | Case P: taxi-graph nodes on the 28R centreline; case S: post-lift-off blend of a fixed min(0.25 D, 6) s and a climb started at up to 3 × the mean rate | Straight runway crossings; climb-out acceleration ≤ the roll's, ramps limited; climb starts level; trapezoid vertical profiles; quantised heights smoothed | fixed (8.8.3) |
| F10 | Strict residuals; weekday take-off count | One C172 take-off emitted twice by the classifier (its episode key changed when older fixes left the buffer) | Events also de-duplicated by type, runway and time | weekday 7 / 6 → 6 / 6 fixed; weekend 7 / 9 traced (8.8.4); grass / overlap / ghost residuals unchanged |

#### 8.8.3 Results

Strict harness, all seven windows (10-Hz frames unless stated; full table in `phase2_traffic.md` §7 "Iteration 2
results"):

| Gate | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|
| off_reports_samples (1 Hz) | 91 → 0 | 0 → 0 | 0 → 0 | 63 → 0 | 13 → 0 | 0 → 0 | 5 → 0 |
| low_air_off_runway_frames | 0 → 0 | 35 → 0 | 0 → 0 | 0 → 0 | 109 → 0 | 0 → 0 | 0 → 0 |
| air_pair_close_frames | 0 → 0 | 0 → 0 | 0 → 0 | 17 → 0 | 44 → 0 | 0 → 0 | 0 → 0 |
| label_contradictions | 220 → 0 | 107 → 0 | 54 → 0 | 269 → 0 | 329 → 0 | 23 → 0 | 37 → 0 |
| air_overspeed_samples (1 Hz) | 169 → 1 | 2 → 3 | 3 → 1 | 64 → 0 | 9 → 3 | 2 → 0 | 0 → 0 |
| air_climb_samples (1 Hz) | 74 → 61 | 77 → 76 | 5 → 5 | 48 → 30 | 167 → 121 | 8 → 3 | 25 → 24 |
| grass_route / fw_in_building / ground_overlap / ghost_parked | 9 / 179 / 0 / 0 | 7 / 0 / 6 / 0 | 1 / 0 / 0 / 0 | 1 / 2 / 0 / 0 | 33 / 225 / 0 / 0 | 0 / 0 / 0 / 3 | 6 / 30 / 0 / 0 |
| every other gate (teleports, hops, misaligned, off-runway lift-offs / touchdowns, ...) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **RESULT** | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |

Every window still fails on the residuals of 8.8.4 (the gates stay failing until those are fixed).

Other checks:

| Check | Result |
|---|---|
| `python3 tools/live/test_relay.py` | 26 tests OK |
| `python3 -I -B tools/check_airport.py` | ALL HARD CHECKS PASSED (D1: 29 + 203 committed files scanned, 0 findings) |
| `jobs/horizon.mjs` (full-ident replay relay on a local 89xx port, 8 Nov 20Z; the page reconnected with `?since=12345`) | PASS: 5 parked / silent bodies before → 5 kept and drawn; the silent one with an identity shows its type only (`withheld: 'horizon'`); 2 tracks withheld in all; `traffic.forget` not called (d1Forget 0 → 0); 0 console errors. A first run with a stricter check flagged two aircraft the relay had masked 'd1' before the horizon - a fault of the check, corrected |
| OD3 traces `out/od3/trace_case_{S,P}.{json,csv}` (refreshed; local) | Case S: line-up at the 28L end, roll from rest 477 m at a mean 2.0 m/s², lift-off at 85.5 kt with 1,258 m left, ≤ 2 m/s² to the first airborne fix, monotone climb from level, 0 samples off pavement. Case P: touchdown 412 m down 28L at 80.7 kt on the centreline, straight 8.8-kt crossing of 28R (no stop on the runway), 0 samples off pavement |
| `node --check` on every edited JS file | OK |

#### 8.8.4 Residuals and limits (not verified)

- **Hidden take-offs (M3 fallback, by design):** heli C172 'case B' and 'case C', the weekend business jet - no runway
  plan within the option ladder reaches their first airborne fix (8.8.2 F1; `phase2_traffic.md` §7). They fade out at
  their last ground position and appear at the fix. (*Correction, final recheck F3:* "by design" does not hold: the
  owner's rule allows hiding only when no runway is consistent, and for these three one is - open, 8.6 F3.)
- **Case S roll**: 477 m at 2.0 m/s² (1.3 × the AFM-derived table value; inside the AFM's 452-680 m range for 5,000-
  6,000 lb and -20 to +20 °C). With its first airborne fix at 112 kt 900 m down the runway, a 1.55-m/s² (621-m) roll
  cannot be followed by a climb-out that accelerates more gently than the roll; weight and temperature of the day are
  not known, and wind is not modelled.
- **air_climb / air_overspeed**: residual 1-121 / 0-3 samples per window, mostly 1-3-s excursions in short holes with
  25-ft altitude steps (`phase2_traffic.md` §7).
- **fw_in_building_frames** with the outline test: wings over building footprints at T-hangar rows and hangar doors
  (heli 179, weekday 2, weekend 225, od3p 30 frames). Not fixed: a sideways physics push was tried and reverted (it
  made the counts worse).
- **grass_route_frames, ground_overlap_frames (pat 6), ghost_parked_frames (od3s 3)**: unchanged from round 3.
- **Weekend take-offs 7 live vs 9 offline (traced, not changed)**: an RV4 first heard rolling on 28L (live: touch-and-go,
  offline: take-off with the taxi-out unobserved) and a C152 heard again on 28R after a silence at its tie-down (live:
  unresolved low pass, offline: take-off).
- **A two-fix TIS-B target** at 166-212 kt, 80-145 m from a weekday TF19 for ~3 s, is still drawn: it matches neither
  the TF19's speed nor its track.
- **Inferred, not sourced** [inf]: every new constant of 8.8.2 (the option ladder 1-2 ×, 400 / 250 / 150-m straights,
  kMax 1.2 / 1.3, the 0.9-VR rule, 1.5-m/s² touch-and-go braking, the 100 / 35-ft and 60 / 300-m low-pass band, the
  glide-profile ramp times, 15-m separation clearance and its rates, the echo tolerances, the 3 / 15-kt label limits,
  the 5-s event buckets, the 1-m/s² vertical ramps, the alpha filters).
- **Not run**: live mode against adsb.lol / adsb.fi; a real phone; the in-app sampler job (`phase2_run_job.mjs`) on this
  iteration's engine. The horizon job ran against the replay relay only.

## 9. Record of review fix round 3, iteration 3 (as written by its fixer, 2026-11-14)

(*Note, after the final recheck:* the summary of round 3 is in section 8, including the final numbers (re-measured,
identical to 9.3) and the open findings of the final recheck. Corrected in place below: 9.2 F3 and 9.4 (F6). The
weekend business jet, which is flagged LADD / PIA, is named by class: 8.1 D1.)

The second recheck of round 3 raised F1 (major) and F2-F8 (minor). This iteration changed `js/live/{traffic,ui,app}.js`,
`tools/traffic/replay_engine.mjs` and these docs (nothing committed). Windows: heli, pat, night, weekday, weekend and the
local OD3 windows `od3s` / `od3p` (OD3 case S (SF50 take-off), OD3 case P (PC-12 landing); definitions and packs in
`out/od3/`, gitignored; the packs are the type-only ones `tools/live/build_replay.py` built in iteration 2, reused
unchanged). Cases are named by window, type and an anonymous label, never by time. "Before" is the iteration-2 engine
(the working tree at the start of this iteration) measured with the iteration-3 harness; "after" the iteration-3 engine.

### 9.1 The harness now sees what the app draws in the first minute (F2) - and the new gates

- **Opening burst (F2).** `replay_engine.mjs` ingested the first batch at the start time, so `traffic.js` dropped every
  fix older than 45 s of a track first heard in it, and every gate was blind to the opening minute. `--open app` (the
  default now) ingests it as `app.js onData` does: a payload older than 3 s at its arrival at its own send time, the rest
  at the arrival. `--open tstart` keeps the old mode for comparison; `--lookahead S` replays a pack with another display
  delay. Planted case `planted_open_burst`: a track heard 58 s, 50 s and 0 s before the start keeps all three fixes with
  `--open app` and only the newest with `--open tstart` (it must, or the gate fails).
- **Cuts are absences.** A re-placement fade (`tr.cutting`) counts as an absence for the teleport rule - the 411-m
  re-placement of the floating business jet faded only to alpha ~0.25 and was never tested.
- **New gates (all limit 0; definitions in the harness, `iter3Frame` / `iter3End`):** `air_float_runway_frames` (fixed-wing
  airborne below 15 ft over a runway > 6 s at a speed varying < 2 kt; data-supported frames INFO),
  `recon_substall_samples` (a reconstructed airborne target below the type's stall speed `vapp / 1.3` and below 0.95 x
  the slower airborne report), `air_substall_samples` (the drawn body ditto), `label_vertical_sense` ('final' / 'base'
  climbing > 300 ft/min, 'climbing out' descending > 300 ft/min, above 50 ft; upwind / crosswind / departing legs flown
  descending are INFO `label_vertical_info`), `label_base_aligned` ('base' lined up on a final), `label_taxi_stopped`
  ('Taxiing' on a body still for > 30 s), `label_roll_flicker` (a roll label shown < 2 s between two spells of another),
  `tg_no_contact` (a touch-and-go event drawn without ground contact within 30 s), `m3_hidden_runway_consistent` (an M3
  hidden take-off although a runway was consistent). `label_runway_in_air` now fires above 15 ft (was 50 ft) and
  includes 'lined up'.

### 9.2 Root causes and what changed

| # | Finding | Root cause | Change | Status |
|---|---|---|---|---|
| F1 | Landing reconstruction flown at sub-stall speed (the weekend business jet 'floating' at 100.8 kt 2-12 ft over 28L for ~20 s, re-placed 411 m, touchdown ~780 m past the threshold, a 153-m ground cut) | `planLanding` gave the roll-out its natural time and ALL the rest of the hole to the approach, with no upper bound on the approach time: with the next fix back-taxiing at 9 kt the approach was planned at 23 kt. The fallback transitions (OAK / SFO arrivals, `landingF`) and air holes between a low fix and a climbing fix had the same flaw | `planLanding` rewritten: for each touchdown point (the touchdown zone, then 25-m steps toward the threshold and to twice the TDZ distance) the approach takes [L / 1.1 x the faster speed, L / `airFloor`] (`airFloor` = VR, i.e. ~1.1 x stall, or 0.97 x the reported speed if observed slower, never below `vmin`), the ground part the rest, within its shortest / longest drivable time; the air curve must stay ≥ 0.93 x the floor all along. A back-taxiing next fix (direction from the fixes after it) gets a roll-out, a U-turn on the runway (as wide as the runway allows) and the back-taxi; firm braking (3.6 m/s² jets / turboprops, 3.0 pistons) only when the normal braking cannot fit. A low approach fix (< 100 ft) touches down where a 3.5° path plus a 2.5-s flare ends, bleeding 4.5 % in the flare. Far / fallback landings touch down earlier instead of flying slower. New: an unseen touch-and-go across an air → air hole lined up with a runway when the air curve would be flown below the floor or the classifier decided a touch-and-go (`planTouchGo`); a silent aircraft last heard low on final continues its landing to an exit (`airLandCont`); the flare floor of the body follows the target's touchdown speed | fixed: teleports weekend 2 → 0; `recon_substall_samples` 58 / 213 / 56 / 277 / 174 / 0 / 26 → 0 everywhere; `air_float_runway_frames` pat 48 → 0, weekday 16 → 0, weekend 138 → 9; `air_substall_samples` 57 / 220 / 54 / 258 / 181 / 0 / 25 → 0 / 0 / 0 / 0 / 8 / 0 / 0. The business jet now touches down ~315 m past the displaced threshold at 122 kt, brakes, turns round at the west end at 11 kt and joins its back-taxi fix - no cut |
| F2 | Strict harness blind to the opening burst | `recv = tStart` for the first batch | `--open app` default (9.1), planted case | fixed |
| F3 | Silent touch-and-go continuation labelled 'Final', vanishing mid-air over the runway | the continuation's air segment fell back to the plan label 'final' (`P.kind` 'depart' is not 'takeoff'); the continuation ended after 20 s and nothing joined a fix heard later | continuation segments carry their phase (climbing out, crosswind); a pattern aircraft turns crosswind on its runway's NASR pattern side and climbs toward the TPA for up to 40 s more; a new fix heard during the continuation is joined by an airborne anchor from where the body is (did not occur in the seven windows: counter 0) | fixed: `label_vertical_sense` → 0 in all windows (weekend 96 → 0). The weekend C172 now climbs out, turns crosswind to the south (28L left traffic) and is hidden ~50 s after its last fix at the end of that leg (not over the runway); its next fix comes 137 s after the last, and it reappears 82 m from where it was hidden, on the take-off reconstruction to that fix. (*Correction, final recheck F2:* "82 m from where it was hidden" leaves out that it reappears at another height, heading and speed, and is then labelled 'Climbing out 28L' for ~58 s while it flies the downwind leg - open, 8.6 F2) |
| F4 | Visible label contradictions | runway labels kept on airborne bodies, no vertical-sense, base/final, stopped or debounce rules | `labelPost`: a runway or ground label on an airborne body becomes its flight phase (plan, else vertical sense); final climbing → go-around, base climbing → crosswind, climbing out descending → final / arriving, base lined up → final; a slow non-accelerating 'take-off roll' → runway taxi; 'Stopped' / 'Stopped on the runway' after 10 s at rest; changes into a roll label held 2 s, a roll label kept ≥ 2 s (a landing roll that speeds up is released at once) | fixed except `label_roll_flicker` weekday 4 → 1 and `tg_no_contact` 11 → 5 (residuals, 9.4); `label_base_aligned` 1,490 → 0, `label_taxi_stopped` 2,382 → 0 samples, `label_contradictions` 62 → 0 |
| F5 | Wings through hangar footprints | routes along apron connectors 3 m from T-hangar rows; slow manoeuvres at hangar doors | every taxi link carries its building clearance (`TaxiNet(G, site)`); routes for an aircraft whose half span + 1 m exceeds it are penalised 400 m; a slow (< 2.5 m/s) body with any planform point in a hangar footprint is in its door and faded like one inside | partly: `fw_in_building_frames` heli 179 → 11, weekend 225 → 57, od3p 30 → 11, weekday 2 → 2 |
| F6 | M3 hidden take-off although a runway is consistent | the 60-s display lookahead leaves too little time after a long silence | measured, not changed (owner decision, 9.4): with `--lookahead 90` or `120` heli 'case B' is planned (no hide); heli 'case C' and the weekend business jet remain hidden | open: gate `m3_hidden_runway_consistent` heli 2, weekend 1 (kept failing) |
| F7 | Weekday C152 'case A' rolled 838 m, lifting off 96 m before the 28R end | fast off-centreline ground fixes kept on the ground and snapped to the axis | a fixed-wing ground fix ≥ 0.9 VR more than the runway half-width beside the runway it moves along is airborne, low over the runway (3 m + 2 m per m/s over 0.9 VR, ≤ 15 m) | fixed: case A lifts off with ~400 m of 28R left (was 96-116 m) |
| F8 | Card '... above field' understated the height over the low west part of 10R/28L by up to 27 ft | the second value was referenced to the 52-ft field elevation | below 300 ft the card gives the height above the ground / runway under the aircraft ('30 ft above the runway'), higher 'N ft above airport elevation (52 ft)' | fixed: probe 0 card heights > 15 ft off the drawn height above the ground (pat 3,236, weekend 3,147, od3s 39, od3p 424 AGL samples) and 0 samples below 290 ft showing the airport-elevation form |

### 9.3 Results

Strict harness, `--open app`, all seven windows (10-Hz frames unless stated; **bold** = still failing):

| Gate (limit 0) | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|
| teleports_engine | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 2 → 0 | 0 → 0 | 0 → 0 |
| label_contradictions | 5 → 0 | 18 → 0 | 8 → 0 | 8 → 0 | 14 → 0 | 0 → 0 | 9 → 0 |
| recon_substall_samples (1 Hz) | 58 → 0 | 213 → 0 | 56 → 0 | 277 → 0 | 174 → 0 | 0 → 0 | 26 → 0 |
| air_substall_samples (1 Hz) | 57 → 0 | 220 → 0 | 54 → 0 | 258 → 0 | 181 → **8** | 0 → 0 | 25 → 0 |
| air_float_runway_frames | 0 → 0 | 48 → 0 | 0 → 0 | 16 → 0 | 138 → **9** | 0 → 0 | 0 → 0 |
| label_vertical_sense (1 Hz) | 7 → 0 | 41 → 0 | 0 → 0 | 43 → 0 | 96 → 0 | 0 → 0 | 7 → 0 |
| label_base_aligned (1 Hz) | 192 → 0 | 474 → 0 | 22 → 0 | 140 → 0 | 502 → 0 | 0 → 0 | 160 → 0 |
| label_taxi_stopped (1 Hz) | 434 → 0 | 199 → 0 | 54 → 0 | 674 → 0 | 812 → 0 | 79 → 0 | 130 → 0 |
| label_roll_flicker | 0 → 0 | 2 → 0 | 2 → 0 | 4 → **1** | 2 → 0 | 0 → 0 | 0 → 0 |
| tg_no_contact | 1 → **1** | 2 → **1** | 0 → 0 | 3 → **1** | 5 → **2** | 0 → 0 | 0 → 0 |
| m3_hidden_runway_consistent | 2 → **2** | 0 → 0 | 0 → 0 | 0 → 0 | 1 → **1** | 0 → 0 | 0 → 0 |
| fw_in_building_frames | 179 → **11** | 0 → 0 | 0 → 0 | 2 → **2** | 225 → **57** | 0 → 0 | 30 → **11** |
| grass_route_frames | 9 → **9** | 7 → **7** | 1 → **1** | 1 → **1** | 33 → **33** | 0 → 0 | 6 → **6** |
| ground_overlap_frames / ghost_parked_frames | 0 / 0 | **6** / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / **3** | 0 / 0 |
| air_overspeed_samples (1 Hz) | 1 → **1** | 3 → **3** | 1 → **1** | 0 → 0 | 4 → **5** | 0 → 0 | 0 → 0 |
| air_climb_samples (1 Hz) | 61 → **61** | 76 → **80** | 5 → **5** | 24 → **31** | 122 → **124** | 3 → **3** | 24 → **24** |
| every other gate (signal teleports, slow lift-offs, hard stops, hops, hovering, misaligned / off-runway lift-offs and touchdowns, stale / fast-off-runway / roll-rise / taxi-label gates, off_reports, low_air_off_runway, air pairs, the three planted cases, D1 late-flag) | 0 → 0 |
| **RESULT** | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |

With `--open tstart` (the round-3 ingestion) the iteration-3 engine fails the same gates, with the same or lower counts
except weekday `air_climb_samples` 37.

Other checks:

| Check | Result |
|---|---|
| `python3 tools/live/test_relay.py` | 26 tests OK |
| `python3 -I -B tools/check_airport.py` | ALL HARD CHECKS PASSED (D1 scan clean) |
| `node --check` on every edited JS file | OK |
| OD3 traces `out/od3/trace_case_{S,P}.{json,csv}` (refreshed, app ingestion; local) | identical to iteration 2: case S lines up at the 28L end, rolls from rest 477 m at a mean 2.0 m/s², lifts off at 85.5 kt with 1,258 m left, climbs from level with no height drop; case P touches down 412 m down 28L at 80.7 kt on the centreline, never rises before the touchdown; 0 samples off pavement in both |
| App snapshot of OD3 case S just after lift-off (desktop 1280 × 720, snapshot mode, looked at) | the SF50 drawn just above 28L; card 'Climbing out (provisional) [inf] · 70 ft MSL · 30 ft above the runway'; 0 console errors |
| Card-altitude probe (1 Hz, airborne fixed-wing within 3 km; pat / weekend / od3s / od3p) | 0 'below field elevation', 0 label-vs-drawn differences > 100 ft, 0 card heights above the ground / runway > 15 ft off the drawn height |

### 9.4 Residuals and limits (not verified)

- **Owner decision (F6).** The M3 hidden fallback is still used for three take-offs whose runway IS consistent but that
  cannot be timed: heli C172 'case B' and 'case C' (silent on a taxilane, heard again in the crosswind turn) and the
  weekend business jet (148 kt 834 m down 28L - physically inconsistent with any roll). The 60-s display lookahead
  leaves too little time after a long silence. Measured with `replay_engine.mjs heli --lookahead 90` and `120`: case B
  is then planned (taxi, roll, climb-out on 28R), case C still not; a pack built with `build_replay.py --lookahead 120`
  would do the same in the app (not built; the default stays 60 because the relay's replay mode then shows nothing for
  2 min after it starts, and Phase 3b's video packs use 60). Either the owner allows the hidden fallback for
  time-infeasible take-offs, or packs move to a 120-s lookahead; the gate stays failing until then.
  (*Correction, round 4:* owner decision (c) moved packs to a 120-s lookahead; `build_replay.py` now defaults to 120 s and
  live mode keeps 60 s - section 10.)
  (*Correction, final recheck F3:* the owner's rule already covers this case. It allows hiding a take-off only when no
  runway is consistent, so these three take-offs violate it. This is an open finding (8.6 F3), not a question for the
  owner. The 120-s probe was re-run for section 8.5: case B is planned, case C is still hidden.)
- **tg_no_contact (5):** touch-and-go events of the classifier (runway contact by altitude) whose drawn body passes
  low without touching because no touch-and-go fits the two fixes' timing; the label no longer says 'Touch-and-go' on
  the airborne body (it shows the flight phase), but the event list counts the touch-and-go.
- **air_substall_samples weekend 8 / air_float_runway_frames weekend 9:** a TAYD and a P28A at the follower's speed
  floor inside air holes (`aa:herm` / `aa:geo`), a GLAS climb-out for 1 s; a C172 fallback landing in its flare.
- **label_roll_flicker weekday 1:** a TF19 'Landing roll' for 0.1 s inside a take-off roll after a 2-s pending hold.
- **fw_in_building_frames:** aircraft taxiing at 2.5-5 m/s with a wing tip over a T-hangar row or a hangar door
  (weekend TAYD beside Hangar Q, od3p / heli DA40 at a maintenance hangar door, weekday C182 at Hangar C).
- **air_climb_samples** rose slightly (pat 76 → 80, weekday 24 → 31, weekend 122 → 124): the touch-and-go climb-outs
  reach up to ~1.3 x the C172 table climb for a few seconds. **grass_route, ground_overlap (pat), ghost_parked (od3s),
  air_overspeed:** unchanged (8.8.4).
- **Seen, not in the findings, not fixed:** a BL8 landing 28R westbound labelled 'Landing roll 10L' (the runway end in
  the classifier's label).
- **Inferred, not sourced** [inf]: every new constant (the 1.1 / 0.97 / 0.93 speed factors, the 1.12 path factor,
  25-m touchdown steps, 3.5° / 2.5-s flare and the 4.5 % bleed, the 3.6 / 3.0 m/s² firm braking, the U-turn margins,
  the 400-m link penalty and 25-m clearance search, 2.5 m/s door rule, 10-s 'Stopped', 2-s label holds, 15° / 100 m /
  4 km final test, 300 ft card threshold, the touch-and-go glide angles and acceleration factors, the 40-s crosswind
  continuation). The pattern sides and TPAs used are FAA NASR [obs].
- **Not run:** live mode; a real phone; the reviewer's extended harness (harness2) on this engine.

## 10. Fix round 4 - motion engine (items E1-E8, 2026-11-14)

The fourth review raised eight motion items (E1-E8). This round changed `js/live/{traffic,motion,ground,classifier}.js`,
the lookahead default of `tools/live/build_replay.py`, `tools/traffic/replay_engine.mjs` (new gates), the new
`tools/traffic/od3_trace.mjs` and these docs (nothing committed; `js/live/parking.js` was not changed). Windows: heli, pat,
night, weekday, weekend and the local OD3 windows `od3s` / `od3p` (definitions and packs in `out/od3/`, gitignored). Cases
are named by window, class and an anonymous label, never by time; the OD3 cases are 'case S' (a light-jet take-off) and
'case P' (a single-turboprop landing). The detailed write-up of every change and constant is in `docs/phase2_traffic.md` §4
("Fix round 4").

### 10.1 Method

- **Before** = the engine at the start of this round (a copy of `js/live/` kept in the scratch directory), measured with
  the FINAL round-4 harness, at the packs' own 60-s lookahead. **After** = the final engine, measured twice: with
  `--lookahead 120` (owner decision (c): packs are now built with a 120-s lookahead; this is the primary result) and at the
  packs' 60 s (what live mode and the existing 60-s packs show). `node tools/traffic/replay_engine.mjs <w> --strict --open
  app`, 10-Hz frames, deterministic.
- **Reproduce first.** Every item was reproduced in the before engine (a gate that counts it, or a 10-Hz probe of the
  case), the root cause found in the code, then fixed; the gate is limit 0 where the item is measurable.
- **Looked at like a pilot.** OD3 cases S and P are traced per second (`node tools/traffic/od3_trace.mjs S|P`, lookahead
  120): position, height, speed, heading, pitch, bank, label, phase, obs / inf, plus 10-Hz checks (accelerations, stalls,
  pitch steps, rest moves, roll / rotation / flare numbers) - `out/od3/trace_case_{S,P}.{json,csv}` (local only).

### 10.2 New gates (harness `r4Frame` / `r4End`, all limit 0)

`air_accel_samples` (E1: airborne dV/dt over 1 s above 1.25 x the type's take-off acceleration (≥ 1.0 m/s²) or a loss
above max(1.6, that), on reconstructed motion; fix-to-fix data INFO), `ground_fast_roll_frames` (E1: ≥ 0.9 VR on the
ground > 8 s), `tg_label_frames` (E1: a reconstructed touch-and-go roll not labelled so), `teleports_attitude` (E2: air →
air re-appearance jumping > 100 ft or > 45°, counted as a teleport), `fast_ground_fixes` (E4: ground fixes kept on the
ground at ≥ 1.1 VR that accelerate, or ≥ 1.3 VR), `liftoff_plateau_frames` (E4: < 100 ft/min for > 3 s within 25 s of a
lift-off below 200 ft), `label_takeoff_slow`, `label_climbout_leg`, `label_runway_end`, `label_lineup_rolling` (E5),
`rest_pose_change_frames`, `label_lineup_misaligned`, `label_hold_on_runway` (E6), `liftoff_pitch_low`,
`touchdown_pitch_bad`, `pitch_rate_frames`, `pitch_phase_samples`, `roll_turn_samples`, `ground_stall_frames`,
`roll_start_yaw_frames`, `taxi_hole_stop_frames`, `label_overflight_hwd`, `label_taxi_still` (E7) and `snapshot_drift`
(E8: a fresh engine pre-rolled to 25 / 50 / 75 % of the window, one catch-up update, then 30 updates at the same clock:
any drawn change). Definitions are in the harness header; `label_base_aligned` now includes the runway itself. A pivot toward the heading
of a PLANNED wait (the turn a take-off plan schedules before it taxis off at an angle, or at its line-up) is the plan's own
manoeuvre and counts as INFO `rest_turn_planned`, like a pivot toward an observed true heading (`rest_turn_observed`).

### 10.3 Items: reproduction, root cause, change

| # | Item | Reproduced (before) | Root cause | Change |
|---|---|---|---|---|
| E1 | Unseen touch-and-go rolled 20-34 s near lift-off speed, then accelerated at 3-4.5 m/s² in the air | `ground_fast_roll_frames`, `air_accel_samples`, `tg_label_frames` (table 10.4) | `planTouchGo` gave the roll the whole spare time at its touchdown speed (no braking), lifted off late and joined the climb-out fix with an unbounded speed change; the air follower accepted any target acceleration | roll = brake (2.0 / 1.5 / 2.5 m/s²) → slow roll (≤ 0.75 VR, ≤ 0.88 VR if needed) → take-off acceleration to VR; spare time to a slower approach, a later touchdown, the slow roll, or a stop-and-go; ≤ 8 s at ≥ 0.9 VR (also for every landing roll); no fit → a re-timed low pass (speed change ≤ 1.15 x accTO); climb-out acceleration ≤ 1.15 x accTO; air follower limits per class; label 'Touch-and-go (provisional)' |
| E2 | A silent climb-out heard again popped in at another height / heading | `teleports_attitude` | the next plan started from the last FIX, not from where the hidden continuation had drawn the body | the anchor of the next plan is the hidden continuation's state at its end (`anchorAt`); reappearances > 100 ft / 45° are teleports; the leg label follows the drawn leg |
| E3 | 120-s lookahead for packs | - | - | `build_replay.py` `LOOKAHEAD_S = 120` (decision c); live keeps 60 s + M3; the harness replays any pack with `--lookahead` |
| E4 | 'Ground' fixes at ≥ 1.1 VR kept on the ground, a level plateau after lift-off | `fast_ground_fixes`, `liftoff_plateau_frames` | the F7 rule (round 3) only lifted fast fixes BESIDE the runway; those on the centreline stayed on the ground; heights of lifted fixes were a fixed 3-15 m | fixes ≥ 1.1 VR not decelerating (or ≥ 1.3 VR) are airborne; height from a lift-off at VR after the last slower ground fix and 70 % of the table climb |
| E5 | Labels: 'Base' over the runway on short final, 'Take-off roll' on a slow back-taxi, 'Climbing out' through crosswind / downwind | `label_base_aligned`, `label_takeoff_slow`, `label_climbout_leg`, `label_runway_end` | label rules keyed to the classifier's fix phase, not to the drawn body; 'upwind' had no lateral limit | `labelPost` rewritten (runway label → plan phase / leg / departing-arriving on airborne bodies; slow non-accelerating roll → runway taxi; runway end by the body's motion); classifier `leg()` upwind ≤ 800 m off the axis; HWD scope from final-approach evidence (`onFinalFix`) |
| E6 | Ground bodies pivoting at ~0 kt; 'Lined up' 143° off; 'Holding short' on the runway | `rest_pose_change_frames`, `label_lineup_misaligned`, `label_hold_on_runway` | a resting body kept following its target's centimetre jitter (trail, rest heading, physics re-placement); the box filter grew at once when a trail was extended ahead of a still body | REST LOCK (3 m, 0.5 m/s; pivot only to an observed heading > 30° off or on a planned wait); heading at rest = arrival heading; box filter grows with the body's motion; constant 0.6 m/s² stop; line-up nose blend (12 m) and a taxi into a line-up-and-wait that ends at rest; 'Lined up' only within 30°; no 'Holding short' on runway pavement |
| E7 | Video motion: pitch at rotation / flare / climb / approach, bank, touchdown stall, roll-start yaw, a 16-s stop inside a 48-s moving taxi hole, parked pivots / hops, hold twitch; labels 'Overflight' on base / early final, 'Taxiing' while standing / at 0 kt parked | `liftoff_pitch_low`, `touchdown_pitch_bad`, `pitch_rate_frames`, `pitch_phase_samples`, `roll_turn_samples`, `ground_stall_frames`, `roll_start_yaw_frames`, `taxi_hole_stop_frames`, `label_overflight_hwd`, `label_taxi_still` | pitch was the flight-path angle only (no attitude model); the ground follower lost a frame at the air → ground switch (`behind` mode stood still when the target was level with it); stretched roll parts ran out early; the old trail behind a lined-up body; a long hole's chord direction pointed back; scope 'overflight' until a runway fix; 'Taxiing' had a 10-s grace | `attitude()` (class attitudes, rotation over 2.5 s, flare, rate limits, coordinated bank) and `disp.flapsF`; `c.td` touchdown flag and a bounded behind mode; smoothstep-warped roll clock; catch-up counted after the frame's own advance; `trkH` true track for holes; scope from final evidence; 'Stopped' / 'Parked' after 3 s |
| E8 | Snapshot not frozen | `snapshot_drift` | `update()` integrated the follower with dt > 0 even when the clock did not move | `update(now)` at the same `now` as the last frame returns at once (`counters.frozenFrames`) |

### 10.4 Results: strict harness, before → after, all seven windows

Cells: **before** (round-3 engine, final round-4 harness, 60-s lookahead) → **after at 120 s** (decision (c); **bold** =
still failing) (after at 60 s in brackets). `--open app`, 10-Hz frames unless the gate says samples (1 Hz). Gates that are 0
before and after in every window at both lookaheads are listed below the table.

| Gate (limit 0) | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|
| teleports_signal_hwd | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 1 → 0 (1) | 0 → 0 (0) | 0 → 0 (0) |
| ghost_parked_frames | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 3 → **1** (1) | 0 → 0 (0) |
| grass_route_frames | 9 → 0 (0) | 7 → **5** (5) | 1 → **1** (1) | 1 → 0 (0) | 33 → **35** (34) | 0 → 0 (0) | 6 → 0 (0) |
| ground_overlap_frames | 0 → 0 (0) | 6 → **13** (12) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) |
| fw_in_building_frames | 11 → **6** (6) | 0 → 0 (0) | 0 → 0 (0) | 2 → **25** (25) | 57 → **84** (84) | 0 → 0 (0) | 11 → **6** (6) |
| off_reports_samples | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → **4** (4) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) |
| air_overspeed_samples | 1 → 0 (0) | 3 → **7** (7) | 1 → **1** (1) | 0 → **1** (1) | 5 → **4** (3) | 0 → 0 (0) | 0 → 0 (0) |
| air_climb_samples | 61 → **58** (58) | 80 → **65** (65) | 5 → **3** (3) | 31 → **24** (24) | 124 → **101** (104) | 3 → **3** (3) | 24 → **23** (23) |
| low_air_off_runway_frames | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → **21** (0) | 0 → 0 (0) | 0 → 0 (0) |
| air_float_runway_frames | 0 → 0 (0) | 0 → **4** (4) | 0 → 0 (0) | 0 → 0 (0) | 9 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) |
| air_substall_samples | 0 → **2** (2) | 0 → **2** (2) | 0 → 0 (0) | 0 → **2** (2) | 8 → **2** (2) | 0 → 0 (0) | 0 → **1** (1) |
| label_roll_flicker | 0 → 0 (0) | 0 → **1** (1) | 0 → 0 (0) | 1 → **1** (2) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) |
| tg_no_contact | 1 → **3** (3) | 1 → **4** (4) | 0 → 0 (0) | 1 → **2** (2) | 2 → **5** (5) | 0 → 0 (0) | 0 → **1** (1) |
| m3_hidden_runway_consistent | 2 → **1** (2) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 1 → **1** (1) | 0 → 0 (0) | 0 → 0 (0) |
| air_accel_samples | 40 → **13** (13) | 38 → **4** (4) | 17 → **5** (5) | 21 → **9** (9) | 92 → **28** (28) | 4 → 0 (0) | 15 → **3** (3) |
| ground_fast_roll_frames | 336 → **22** (22) | 161 → **20** (20) | 0 → 0 (0) | 56 → **4** (4) | 1319 → **33** (33) | 0 → 0 (0) | 115 → 0 (0) |
| tg_label_frames | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 557 → 0 (0) | 441 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) |
| teleports_attitude | 1 → **1** (1) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 2 → 0 (2) | 0 → 0 (0) | 0 → 0 (0) |
| fast_ground_fixes | 9 → 0 (0) | 51 → 0 (0) | 6 → 0 (0) | 8 → 0 (0) | 27 → 0 (0) | 0 → 0 (0) | 6 → 0 (0) |
| liftoff_plateau_frames | 59 → **18** (18) | 0 → **21** (21) | 0 → 0 (0) | 5 → **9** (9) | 23 → **229** (7) | 0 → 0 (0) | 0 → 0 (0) |
| label_takeoff_slow | 16 → 0 (0) | 8 → **7** (6) | 22 → **3** (3) | 3 → **8** (8) | 54 → **16** (10) | 0 → 0 (0) | 16 → 0 (0) |
| label_climbout_leg | 114 → 0 (0) | 796 → 0 (0) | 99 → 0 (0) | 319 → 0 (0) | 779 → 0 (0) | 176 → 0 (0) | 25 → 0 (0) |
| label_runway_end | 6 → 0 (0) | 3 → 0 (0) | 0 → 0 (0) | 2 → **2** (2) | 31 → **1** (1) | 0 → 0 (0) | 3 → 0 (0) |
| label_lineup_rolling | 25 → **1** (0) | 31 → 0 (0) | 37 → 0 (0) | 111 → **2** (2) | 72 → **1** (0) | 25 → 0 (0) | 18 → 0 (0) |
| rest_pose_change_frames | 1078 → 0 (0) | 1162 → 0 (0) | 15 → 0 (0) | 1045 → 0 (0) | 2297 → **1** (1) | 300 → 0 (0) | 289 → 0 (0) |
| label_lineup_misaligned | 13 → **1** (1) | 5 → 0 (0) | 0 → 0 (0) | 2 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 6 → 0 (0) |
| label_hold_on_runway | 5 → 0 (0) | 1 → 0 (0) | 1 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 4 → 0 (0) |
| liftoff_pitch_low | 10 → 0 (0) | 35 → 0 (0) | 6 → 0 (0) | 21 → 0 (0) | 36 → 0 (0) | 2 → 0 (0) | 7 → 0 (0) |
| touchdown_pitch_bad | 14 → 0 (0) | 40 → 0 (0) | 6 → 0 (0) | 19 → 0 (0) | 40 → 0 (0) | 0 → 0 (0) | 8 → 0 (0) |
| pitch_rate_frames | 1 → 0 (0) | 13 → 0 (0) | 0 → 0 (0) | 0 → 0 (0) | 4 → 0 (0) | 0 → 0 (0) | 1 → 0 (0) |
| pitch_phase_samples | 29 → 0 (0) | 49 → 0 (0) | 24 → 0 (0) | 23 → 0 (0) | 144 → **1** (1) | 1 → 0 (0) | 12 → 0 (0) |
| roll_turn_samples | 0 → 0 (0) | 0 → **1** (1) | 0 → 0 (0) | 0 → **1** (1) | 0 → **8** (5) | 0 → 0 (0) | 0 → 0 (0) |
| ground_stall_frames | 11 → **1** (1) | 33 → 0 (0) | 6 → 0 (0) | 19 → 0 (0) | 31 → **1** (1) | 0 → 0 (0) | 7 → 0 (0) |
| roll_start_yaw_frames | 32 → **33** (25) | 65 → **73** (73) | 130 → **54** (54) | 31 → **57** (57) | 68 → **82** (83) | 5 → **8** (8) | 33 → **26** (26) |
| taxi_hole_stop_frames | 152 → 0 (0) | 157 → **92** (92) | 93 → 0 (0) | 280 → 0 (0) | 283 → 0 (0) | 131 → 0 (0) | 112 → 0 (0) |
| label_overflight_hwd | 60 → 0 (3) | 168 → 0 (48) | 0 → 0 (0) | 0 → 0 (0) | 246 → **3** (61) | 0 → 0 (0) | 61 → 0 (3) |
| label_taxi_still | 198 → 0 (0) | 209 → 0 (0) | 42 → 0 (0) | 167 → 0 (0) | 318 → 0 (0) | 21 → 0 (0) | 90 → 0 (0) |
| snapshot_drift | 3 → 0 (0) | 3 → 0 (0) | 3 → 0 (0) | 3 → 0 (0) | 3 → 0 (0) | 2 → 0 (0) | 3 → 0 (0) |

Zero before and after in every window at both lookaheads: `teleports_engine`, `slow_liftoff`, `hard_stops`, `hops`, `air_hover_frames`, `heli_in_bldg_frames`, `label_contradictions`, `misaligned_transitions`, `stale_on_runway_frames`, `stale_overlap_frames`, `fast_off_runway_frames`, `landing_roll_speed_rise`, `liftoff_off_runway`, `touchdown_off_runway`, `ground_air_reappear`, `taxi_label_fast_frames`, `air_pair_close_frames`, `recon_substall_samples`, `label_vertical_sense`, `label_base_aligned`, `label_taxi_stopped`, `planted_reappear`, `planted_low_air_box`, `planted_open_burst`, `d1_late_flag_forget`.

**RESULT: FAIL in all seven windows, before and after** (residuals: 10.6).

### 10.5 OD3 cases S and P, per second, checked like a pilot

`node tools/traffic/od3_trace.mjs S` / `P` (final engine, lookahead 120, app ingestion; `out/od3/trace_case_{S,P}.{json,csv}`,
local only). "inf" = reconstructed / interpolated, "obs" = within 2 s of a fix.

**Case S (light-jet take-off, 28L).** Taxi to the 28L end at 10-13 kt, holding short (no pivot or hop at
the hold: 0 rest-pose changes in 570 s), on to the runway at 2.6 kt with the nose blending onto the runway heading (296.3 →
299.4 → 299.9°, the line-up taxi now ends at rest), lined up 8 s with flaps at the take-off setting (0.4), roll from rest
at the threshold (2 kt at -21.4 s), a constant ~2.0 m/s² to 85.1 kt in 477 m (the plan's 1.3 x table acceleration: the
type's AFM roll is 2,036 ft at maximum weight, sea level ISA; 1,258 m of 28L left), heading 299.8-299.9° on the
centreline (spread 0.1°, 0 m off it), rotation 1.7° (-2 s) → 5.1° (-1 s) → 7.9° at lift-off, 8-9° in the reconstructed
initial climb at ~500 ft/min accelerating to 112 kt, joining the first observed samples (+10 s: 84 ft, 115.6 kt) without a step;
0 ft height drop after lift-off; then the observed climb (670-1,690 ft/min) at 9-10°. Labels: Stopped → Taxiing → Holding
short → Taxiing → Lined up 28L → Take-off roll 28L → Climbing out → Crosswind → Departing (all provisional while
reconstructed). Pilot's notes: the roll is ~23 % shorter than the AFM maximum-weight figure (plausible lighter or colder,
but it is the plan's compression, [inf]); 9° nose-up while climbing only ~500 ft/min is the rotation floor (≤ 400 ft, 30 s)
and reads slightly high for that climb; the largest frame-to-frame airborne speed change is 2.06 m/s² in the first 0.1 s
after lift-off (one frame; the 1-s gate `air_accel_samples` is 0 here).

**Case P (single-turboprop landing, 28L).** Final 28L at ~596 ft/min (3.8° path), 89 → 82 kt, flaps at the landing
setting, attitude -0.1 to 0.1° (flat, as the class approach attitude gives), lined up within 3 m; the flare from ~20 ft
(-4 s): 1.7 → 3.3 → 4.6 → 5.0°, sink 549 → 287 ft/min; touchdown 411 m past the 28L threshold on the centreline at
80.7 kt, 5.0° nose up, no height rise before it; the nose lowers in ~2 s (4.6 → 0.7 → 0°). Landing roll: 80.7 → 72.7 kt in
2 s (2 m/s²), then 1-2 kt/s to the first fix at +10 s (61.4 kt), observed braking to 12 kt at +26 s, runway taxi at 12 kt
along 28L to the exit, flaps retracting after the landing roll; no speed rise, no frame without motion (`ground_stall_frames`
0; the rise 80.4 → 71.7 → 73.6 kt that the first round-4 trace still showed is gone), the largest braking 3.1 m/s² (observed
part, +21 s). Labels: Arriving → Final 28L → Landing roll 28L → Taxiing on the runway → Taxiing → Holding short → Taxiing →
Stopped (no 'Overflight' on the approach). 0 samples with a wheel off pavement in either case.

### 10.6 Residuals (not fixed, all measured above)

Every window still FAILS strict (failed gates before → after-120 (after-60): heli 28 → 13 (13), pat 25 → 15 (16), night
18 → 6 (6), weekday 24 → 15 (15), weekend 30 → 20 (20), od3s 12 → 3 (3), od3p 23 → 6 (7)). What is left, by cause:

- **Made worse by this round, open.** `fw_in_building_frames` weekday 2 → 25, weekend 57 → 84 and `ground_overlap_frames`
  pat 6 → 13: the REST LOCK keeps a body's pose and `GroundPhysics` places a locked body where it is drawn, so a rest pose
  with a wing tip over a T-hangar row or another aircraft is no longer pushed clear (E6 traded rest pivots / hops, 1,078-2,297
  frames per window → 0-1, for these). `tg_no_contact` 1/1/0/1/2/0/0 → 3/4/0/2/5/0/1 and `air_substall_samples` 0 → 1-2 in
  heli / pat / weekday / od3p: when no touch-and-go fits the type's braking and acceleration within 8 s at ≥ 0.9 VR, the hole
  is now a low pass (E1 rule), which never touches the runway the classifier saw it touch, and some of those passes sit
  below the type's stall-speed estimate for 1-2 s. `liftoff_plateau_frames` pat 0 → 21, weekday 5 → 9 and, at 120 s
  only, weekend 23 → 229 with `low_air_off_runway_frames` 0 → 21: a weekend single-engine piston whose next airborne fix is
  low and back toward the field is reconstructed with a climb-out at ~90 ft/min and a tight turn back (the 120-s lookahead
  plans this take-off; at 60 s it is not planned). `roll_start_yaw_frames` 31-130 → 8-82 (better in night / od3p, worse in
  weekday / pat / weekend): mostly observed ground fixes (`gg:herm`) whose track wanders > 2° off the axis at the roll start,
  plus planned rolls joined from a taxi at an angle. `label_takeoff_slow` weekday 3 → 8, `off_reports_samples` weekday 0 →
  4 (a touch-and-go roll 150 m from its reports), `air_overspeed_samples` pat 3 → 7, `roll_turn_samples` 0 → 1-8 (bank off
  the coordinated value in data turns), `label_roll_flicker` pat / weekday 1 (these four not analysed further).
- **Reduced, not to 0.** `air_accel_samples` 40/38/17/21/92/4/15 → 13/4/5/9/28/0/3 (fix-to-fix data with fast speed changes
  inside approach / departure curves of non-HWD traffic, plan joins); `ground_fast_roll_frames` 336/161/0/56/1319/0/115 →
  22/20/0/4/33/0/0 (not broken down per case); `ground_stall_frames`
  heli / weekend 1 (a planned landing roll advancing 0.3 m against 1.6 m in one frame; not analysed further); `label_lineup_rolling` /
  `label_lineup_misaligned` 1-2; `taxi_hole_stop_frames` pat 92 (a 48-s hole whose reports move but whose chord is a stop);
  `label_overflight_hwd` at 60 s pat 48 / weekend 61 / heli, od3p 3 (at 120 s: 0 / 3 / 0 / 0) - probably the final-approach
  evidence arrives with a fix the 60-s display has not reached yet [not verified]; `teleports_attitude` heli 1 (and weekend 2 at 60 s); `m3_hidden_runway_consistent`
  heli 1 (2 at 60 s), weekend 1; `rest_pose_change_frames` weekend 1.
- **Unchanged from round 3.** `grass_route_frames`, `air_climb_samples` (lower), `ghost_parked_frames` od3s 1 (was 3),
  `air_overspeed_samples` night / weekend.
- **Not attempted:** the round-3 residuals outside E1-E8 (grass routes, wings over hangars, over-climb samples) beyond what
  the changes above touched.

### 10.7 Other checks, wanted, not verified

- `node --check` on every edited JS file: OK. `python3 -I -B tools/check_airport.py`: ALL HARD CHECKS PASSED (D1 scan clean;
  it found one class name next to an OD3 case in a code comment during this round, which was removed).
- The engine files measured in 10.4 are the final ones except a comment-only edit made after the runs (no code change).
- **Wanted** (packages this round does not own): `js/live/aircraft.js` / the OD4 runtime could read the engine's flap
  fraction `disp.flapsF` (it derives its own flap setting; pitch / roll are read already, radians); the Phase 3b video packs
  should be rebuilt with `build_replay.py` at the new 120-s default; `app.js` needs nothing for E8.
- **Inferred, not sourced** [inf]: every new constant (`ATT_CLS` attitudes, `REST_LOCK_M` 3 m, `TG_BRAKE`, `TG_VM_MAX` /
  `TG_VM_HI`, `TG_HOLD_S`, `FAST_ROLL_S` 8 s, `AIR_ACC_K` 1.15, `AIR_DEC_MIN` 1.5, `FAST_AIR_K` 1.1, `STOP_LABEL_S` 3 s,
  `ROT_S` 2.5 s, `PITCH_RATE` / `ROLL_RATE` / `PITCH_DN`, `FLAPS_TO` 0.4, `LINEUP_M` 12 m, `BEHIND_S` 20 s, the 0.6 m/s²
  stop, `UPW_M` 800 m, `FIN_ALIGN` 20°). Attitudes are recalled from flight-training material, not read from a POH / AFM.
- **Not run:** live mode; the app in a browser (no screenshot was taken in this round: the change is in the engine, measured
  by the harness and the traces); a real phone.

## 11. Fix round 4, iteration 2 - recheck findings F1-F12 (2026-11-14)

The recheck of round 4 (section 10) raised twelve findings: two major (F1 a weekend single's implausible reconstructed
climb-out, F2 case S's line-up) and ten minor (F3-F12). This iteration changed `js/live/{traffic,motion,ground,classifier}.js`,
`tools/traffic/{replay_engine,od3_trace}.mjs`, `tools/video/{lib,render}.mjs` and these docs (nothing committed;
`js/live/parking.js`, the app files and every OD4-owned file were not changed). Every change and constant is written up in
`docs/phase2_traffic.md` §4 ("Fix round 4, iteration 2"); the video part (F9) in `docs/phase3_video.md` section 14. Cases
are named by window, class and an anonymous label: 'case W1' (the weekend single of F1), 'case S' / 'case P' (the OD3
cases), weekday 'case A' (the single of F8), never by time.

### 11.1 Method

- **Before** = the engine at the end of section 10 (a copy kept in the scratch directory), measured with the FINAL harness
  of this iteration; **after** = the final engine. Both at `--lookahead 120` (decision (c), the primary result) and at the
  packs' 60 s. `node tools/traffic/replay_engine.mjs <w> --strict --open app [--lookahead 120]`, 10-Hz frames,
  deterministic. The before run reproduces the round-4 numbers of section 10.4 exactly on every gate that existed then.
- **Reproduce first.** Each finding was reproduced in the before engine with a gate (new where none counted it) or a
  10-Hz probe of the case, its cause found in the code, fixed, and re-measured; probes are local scripts in the scratch
  directory (they print types and times and are not committed).
- **Looked at like a pilot**: cases W1, S and P per 0.1 s (height, speed, heading, pitch, bank, flaps, label); the OD3
  traces (`node tools/traffic/od3_trace.mjs S|P`, `out/od3/trace_case_{S,P}.{json,csv}`, local).
- The engine files measured below are the final ones (sha256 prefixes: `traffic.js` 5fd978f57963, `motion.js`
  d2d0e690282a, `ground.js` ec030d03a2c2, `classifier.js` f963f8f7cf95; harness `replay_engine.mjs` d667643f37c9); the
  video snapshots of `docs/phase3_video.md` section 14 hold the same engine files.

### 11.2 New and changed gates (harness `r4i2Frame`, all limit 0)

- `low_bank_frames` (F1): a PLANNED airborne body (plan / xplan / continuation) below 300 ft banking more than max(25°, 15°
  at 100 ft rising to 35° at 300 ft) + 0.5°. INFO: the same on fix-to-fix data (`low_bank_data_frames`) and with a 400-ft
  ceiling (`low_bank_400_frames`).
- `pivot_in_place` (F3): a fixed-wing ground body turning > 30° while its reference point moves less than min(0.5 m,
  0.2 x the main-gear track).
- `ground_slow_fast_roll` (F5): planned ground motion at ≥ 0.75 VR for more than 12 s (INFO: on data).
- `label_flicker` (F7): a label run shorter than 1 s that is not an event label (touchdown / lift-off inside it); flips
  of the '(provisional)' suffix only are INFO (`label_provisional_flips`); 'Parked' → 'Stopped' without movement counts.
- `label_final_arriving` (F6): 'Arriving' on a body lined up with a final (≤ 15°, ≤ 100 m beside the extended centreline,
  ≤ 5 km out), descending, below 2,000 ft.
- Changed: `label_overflight_hwd` looks 300 s back for HWD final-approach evidence (was 120 s; F6); `label_lineup_misaligned`
  counts at any speed (was < 5 kt; F1); the rest gates allow the reference-point displacement of a pivot about the inner
  main wheel (≤ 0.02 m + track / 2 x the heading change; F3); `teleports_attitude` excludes re-appearances after a
  'removed' / 'far' absence (F12); `hard_stops` now logs its cases (`hardLog`).

### 11.3 Findings: reproduction, cause, change, status

| # | Finding | Reproduced (before) | Cause | Change | Status (after, 120 s) |
|---|---|---|---|---|---|
| F1 (major) | Weekend single 'case W1': 120-s reconstructed take-off with a 35° turn at 29-49 ft, 70 ft/min for 20 s, a pivot at the hold, a grass taxi, 'Lined up' / 'Take-off roll' labels while misaligned | 10-Hz probe; `low_bank_frames` 26 / 108 / 0 / 215 / 284 / 0 / 0; `label_lineup_misaligned` 1-6 per window | `takeoffAir` accepted any climb-out that reached the first airborne fix (no low-height bank, minimum-climb or stall check); the line-up label had a 5-kt limit; 'Take-off roll' was promoted from any acceleration | `climbOutOk` (bank ≤ max(25°, 15° → 35° over 100-300 ft), climb ≥ 0.35 x the table over > 15 s, speed ≥ 1.05 x stall), refined W grid, a second plan pass with 6° bank tolerance (`BANK_TOL`), a 14° early-turn rule; longer finals for landings; line-up labels (section 11.2) | **W1 fixed**: waits lined up on 28R with take-off flaps, rolls from rest, lifts off at 47 kt (7.3° pitch) and climbs STRAIGHT (0° bank) at ~330 ft/min to its first fix (52 ft); `label_lineup_misaligned` 0 everywhere. `low_bank_frames` 24 / 1 / 0 / 13 / 7 / 0 / 0 remain - all from the tolerance pass (12 plans in four windows, ≤ 6° over the rule), traded for hidden take-offs; **m3 hides 1 / 2 / 0 / 2 / 3** (open, 11.7) |
| F2 (major) | Case S: line-up yaw 299.6 → 294.4° at 1 kt and an 18°/s snap-back; a 10-14-kt sawtooth line-up with 23°/s turns; a pivot at the FBO exit | OD3 trace + probe | the wait after the line-up lost the nose blend; the line-up speed was the taxi profile's (corner speeds from 3 m/s² lateral); the line-up straight joined the axis from 1.5 m beside it | `profilePath` line-up section (monotone, 0.6 m/s² / 12°/s / 5.8 kt, rungs to 25 kt and none), on-axis line-up straight, nose blend kept in the wait / rolling start; inner-wheel pivots (F3) | **Fixed**: constant 7.7-7.8 kt line-up, nose 290.8 → 299.9° monotone over ~2 s while joining the centreline, no snap-back, rolling start at 6.8-7.8 kt (11.5); `pivot_in_place` od3s 10 → 1 (a single's fix-following taxi turn, not case S) |
| F3 | Ground bodies pivoting about the reference point | `pivot_in_place` 59 / 30 / 13 / 43 / 84 / 10 / 27 | turn rate limited, position not: a turn at 0 kt spun the main-gear midpoint in place | pivot about the inner main wheel (`c.po` offset, `PIVOT_V`, `PO_FADE_M`), in place only where a wheel would leave the pavement | 3 / 6 / 2 / 3 / 3 / 1 / 0 (fix-following taxi turns at pavement edges, `counters.pivotInPlace`, and 0.4-0.5-m moves just under the gate) |
| F4 | Bodies at rest over buildings / overlapping (REST LOCK); touch-and-go lift-off at 44-47 kt below the 47-48-kt stall estimate | `fw_in_building_frames` 6 / 0 / 0 / 25 / 84 / 0 / 6, `ground_overlap_frames` pat 13 | the lock froze the pose before `GroundPhysics` could push it clear; lift-off speed clamped to the reported speed only | once-per-lock push along the nose (0.5-6 m, `PUSH_M`); lift-off ≥ 1.05 x stall unless the climb-out fix was slower (`recon_substall_samples` 0 everywhere) | **partly**: buildings weekday 25 → 24, weekend 84 → 60, heli / od3p 6 unchanged; overlaps pat 13 → 10; `air_substall_samples` unchanged at 0-2 (data low passes) |
| F5 | Long constant-speed touch-and-go / landing rolls just under 0.9 VR | `ground_slow_fast_roll` 138 / 168 / 0 / 91 / 92 / 0 / 103 | the 0.9-VR / 8-s rule let a roll sit at 0.85 VR | ≤ 12 s at ≥ 0.75 VR on rolling starts, touch-and-goes and landing roll-outs | 52 / 9 / 0 / 2 / 0 / 0 / 0 (heli: landing roll-outs whose observed exit fix is fast; not broken down further) |
| F6 | Case P labelled 'Overflight' for 120 s while descending 8 km SE; 'Arriving' on an aligned final | `label_final_arriving` 103 / 37 / 0 / 24 / 78 / 0 / 43; `label_overflight_hwd` (300-s window) pat 170, weekend 286 | the classifier decided 'overflight' before any pattern / final evidence; 'Arriving' had no final rule | `arrivingField` (descending toward the field, < 10 km, < 6,000 ft → 'pending'), the overflight decision waits 60 s after such a fix or a pattern-leg fix; 'Arriving' aligned with a final < 2,000 ft → 'Final'; nearest-centreline end | `label_final_arriving` 0 everywhere; case P: 'Arriving' → 'Final' (no 'Overflight'); `label_overflight_hwd` **pat 122, weekend 154** (open) |
| F7 | Label flicker (0.1-0.7-s runs) | `label_flicker` 34 / 62 / 11 / 59 / 78 / 16 / 19 | no hysteresis between calm ground labels, the lined-up roll start, pattern-leg steps back, a still body's end of signal | targeted holds (11.2 / phase2_traffic.md F7), 'Stopped · no signal' | 15 / 41 / 8 / 33 / 39 / 0 / 6 (remaining: provisional / leg changes of fix-following traffic, not analysed one by one) |
| F8 | Weekday single 'case A': 'Low pass' and full flaps right after a take-off roll | probe | the fix label ('low pass' / 'final') was shown on a climbing body; flaps followed the label | 90-s after-take-off rule in `labelPost`; flaps ≤ the take-off setting (`TO_KEEP_S`) | fixed in this iteration's probe ('Climbing out' with the take-off flaps, then 0); not re-probed on the final engine, whose later changes do not touch this rule |
| F9 | Video snapshots from mid-round engines | snapshot manifests | the Phase 3b snapshots froze the engine of the moment | `render.mjs snapshot --refresh=engine`; re-scout, re-plan, determinism, spot stills on the final engine | done (`docs/phase3_video.md` section 14) |
| F10 | `od3_trace` used the wrong speed table | trace | `speedsOf(null)` after the hero's track ended | speeds cached while the track lives | fixed |
| F11 | A planned fallback final gained 11 kt at 5 m/s² and lost 48 kt at 3-4.5 m/s² | `air_accel_samples` | `airSeg` curves took the speed profile of their end speeds | re-timed to ramps ≤ 1.15 x accTO (`retimePath`) | `air_accel_samples` 13 / 8 / 5 / 9 / 28 / 0 / 3 (pat 4 → 8: fix-to-fix data and plan joins of non-HWD traffic, open) |
| F12 | Live mode: a silent low-pass continuation re-appeared with a 284-ft / 42° jump | `teleports_attitude` (60 s) weekend 1 | the late anchor was the continuation's END state, already passed by the display | anchor dead-reckoned to the display time (`anchorAt`) | `teleports_attitude` 0 at 60 and 120 s in every window |

### 11.4 Results: strict harness, before → after, all seven windows

Cells: **before → after at 120 s** (**bold** = still failing) (before → after at 60 s). `--open app`, 10-Hz frames unless
the gate says samples (1 Hz). Gates that are 0 before and after in every window at both lookaheads are listed below the
table.

| Gate (limit 0) | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|
| teleports_signal_hwd | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| ghost_parked_frames | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) |
| hard_stops | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → **1** (0 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| grass_route_frames | 0 → 0 (0 → 0) | 5 → **6** (5 → 8) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 35 → **32** (34 → 30) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| ground_overlap_frames | 0 → 0 (0 → 0) | 13 → **10** (12 → 12) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| fw_in_building_frames | 6 → **6** (6 → 6) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 25 → **24** (25 → 24) | 84 → **60** (84 → 60) | 0 → 0 (0 → 0) | 6 → **6** (6 → 6) |
| off_reports_samples | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| air_overspeed_samples | 0 → 0 (0 → 0) | 7 → **7** (7 → 7) | 1 → **1** (1 → 1) | 1 → **1** (1 → 1) | 4 → **2** (3 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| air_climb_samples | 58 → **59** (58 → 59) | 65 → **65** (65 → 65) | 3 → **3** (3 → 3) | 24 → **21** (24 → 21) | 101 → **103** (104 → 106) | 3 → **3** (3 → 3) | 23 → **23** (23 → 23) |
| low_air_off_runway_frames | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 21 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| air_float_runway_frames | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| air_substall_samples | 2 → **2** (2 → 2) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |
| label_roll_flicker | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 1 → **1** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| tg_no_contact | 3 → **3** (3 → 3) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 5 → **5** (5 → 5) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |
| m3_hidden_runway_consistent | 1 → **1** (2 → 2) | 0 → **2** (0 → 2) | 0 → 0 (0 → 0) | 0 → **2** (0 → 2) | 1 → **3** (1 → 3) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| air_accel_samples | 13 → **13** (13 → 13) | 4 → **8** (4 → 8) | 5 → **5** (5 → 5) | 9 → **9** (9 → 9) | 28 → **28** (28 → 28) | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) |
| ground_fast_roll_frames | 22 → **22** (22 → 22) | 20 → **20** (20 → 20) | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 33 → **33** (33 → 33) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| teleports_attitude | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| liftoff_plateau_frames | 18 → **18** (18 → 18) | 21 → **21** (21 → 21) | 0 → 0 (0 → 0) | 9 → **9** (9 → 9) | 229 → **7** (7 → 7) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| label_takeoff_slow | 0 → 0 (0 → 0) | 7 → 0 (6 → 0) | 3 → **1** (3 → 1) | 8 → **10** (8 → 10) | 16 → **13** (10 → 10) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| label_runway_end | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| label_lineup_rolling | 1 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → **1** (0 → 1) | 2 → 0 (2 → 0) | 1 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| rest_pose_change_frames | 0 → 0 (0 → 0) | 0 → **1** (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **2** (1 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| label_lineup_misaligned | 6 → 0 (3 → 0) | 6 → 0 (6 → 0) | 0 → 0 (0 → 0) | 3 → 0 (3 → 0) | 5 → 0 (3 → 0) | 1 → 0 (1 → 0) | 2 → 0 (2 → 0) |
| pitch_phase_samples | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → **1** (0 → 1) | 1 → **1** (1 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| roll_turn_samples | 0 → **1** (0 → 1) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 8 → **3** (5 → 3) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| ground_stall_frames | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| roll_start_yaw_frames | 33 → **18** (25 → 18) | 73 → **47** (73 → 47) | 54 → **56** (54 → 56) | 57 → **41** (57 → 41) | 82 → **56** (83 → 59) | 8 → 0 (8 → 0) | 26 → **19** (26 → 19) |
| taxi_hole_stop_frames | 0 → 0 (0 → 0) | 92 → **92** (92 → 92) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| label_overflight_hwd | 0 → 0 (59 → 59) | 170 → **122** (221 → 173) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 286 → **154** (462 → 235) | 0 → 0 (0 → 0) | 0 → 0 (58 → 58) |
| low_bank_frames | 26 → **24** (0 → 0) | 108 → **1** (108 → 1) | 0 → 0 (0 → 0) | 215 → **13** (215 → 13) | 284 → **7** (140 → 7) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| pivot_in_place | 59 → **3** (57 → 2) | 30 → **6** (31 → 3) | 13 → **2** (13 → 2) | 43 → **3** (44 → 3) | 84 → **3** (84 → 5) | 10 → **1** (12 → 1) | 27 → 0 (27 → 0) |
| ground_slow_fast_roll | 138 → **52** (138 → 52) | 168 → **9** (168 → 9) | 0 → 0 (0 → 0) | 91 → **2** (91 → 2) | 92 → 0 (92 → 0) | 0 → 0 (0 → 0) | 103 → 0 (103 → 0) |
| label_flicker | 34 → **15** (34 → 13) | 62 → **41** (66 → 45) | 11 → **8** (11 → 8) | 59 → **33** (59 → 33) | 78 → **39** (76 → 38) | 16 → 0 (16 → 0) | 19 → **6** (19 → 6) |
| label_final_arriving | 103 → 0 (102 → 0) | 37 → 0 (37 → 0) | 0 → 0 (0 → 0) | 24 → 0 (24 → 0) | 78 → 0 (78 → 0) | 0 → 0 (0 → 0) | 43 → 0 (43 → 0) |

Zero before and after in every window at both lookaheads: `teleports_engine`, `slow_liftoff`, `hops`, `air_hover_frames`, `heli_in_bldg_frames`, `label_contradictions`, `misaligned_transitions`, `stale_on_runway_frames`, `stale_overlap_frames`, `fast_off_runway_frames`, `landing_roll_speed_rise`, `liftoff_off_runway`, `touchdown_off_runway`, `ground_air_reappear`, `taxi_label_fast_frames`, `air_pair_close_frames`, `recon_substall_samples`, `label_vertical_sense`, `label_base_aligned`, `label_taxi_stopped`, `tg_label_frames`, `fast_ground_fixes`, `label_climbout_leg`, `label_hold_on_runway`, `liftoff_pitch_low`, `touchdown_pitch_bad`, `pitch_rate_frames`, `label_taxi_still`, `snapshot_drift`, `planted_reappear`, `planted_low_air_box`, `planted_open_burst`, `d1_late_flag_forget`.

Failed gates (120 s): heli 17 → 15, pat 22 → 21, night 8 → 9, weekday 21 → 20, weekend 26 → 22, od3s 6 → 2, od3p 11 → 7
(60 s: heli 16 → 15, pat 22 → 20, night 8 → 9, weekday 21 → 20, weekend 26 → 22, od3s 6 → 2, od3p 12 → 8). The one new
failing gate is night `label_lineup_rolling` 1 (one 0.1-s frame between two log seconds, not traced). **RESULT: FAIL in all
seven windows, before and after** (residuals: 11.7). New engine counters at 120 s: `climbOutBankTol` (plans needing the
bank tolerance) heli 1, pat 3, weekday 3, weekend 5; `landingLongFinal` night 1, pat 3, weekday 4, weekend 5;
`lineupFaster` (a quicker line-up rung) 1-2 in five windows; `airSegRetimed` pat / od3p 1; `pivotInPlace` heli 4, weekend 2.

### 11.5 Cases W1, S and P, per 0.1 s, checked like a pilot

**Case W1 (weekend single, take-off, 28R; final engine, 120 s).** Taxis onto 28R at ~2 kt with the nose blending
272 → 299.9° over ~3.5 s, stops lined up and waits ~8 s with the take-off flaps (0.40), rolls from rest at ~1 m/s² for
23 s, rotates over the last ~2.5 s (0 → 7.3°) and lifts off at 47 kt; climbs straight ahead on 299.9° at 0° bank, 8° nose
up, ~330 ft/min, accelerating 49 → 64 kt, to its first airborne fix (52 ft, ~10 s after the lift-off), then follows the
data. Labels: Lined up 28R → Take-off roll 28R → Climbing out → Climbing out 28R (all provisional while reconstructed).
Pilot's note: the climb to the first fix is shallow because the fix itself is low (52 ft) - the data, not the plan.

**Case S (light-jet take-off, 28L; `node tools/traffic/od3_trace.mjs S`).** Holding short with no rest move (0
rest-pose changes, 0 planned pivots); the taxi onto the runway at a constant 7.7-7.8 kt (line-up rung C: its 50-s hole
leaves no time for the 5.8-kt rung with a roll inside the AFM range), joining the centreline from 3.3 m left at ~8° and
turning the nose 290.8 → 299.9° monotonically in ~2 s; 'Lined up 28L' for 5.7 s, the speed 7.8 → 6.0 kt at the roll start
(the line-up's monotone section ends at the rolling-start speed), then the roll at ~1.75 m/s² (f = 1.15 x the table) to
85 kt in 535 m (1,185 m of 28L left), heading 299.9° and ≤ 0.1 m off the centreline from the roll start (the trace's
`heading_spread_on_centreline_deg` 6.4 includes the last 5 s of the line-up on runway pavement); rotation 1.6° (-2 s) →
7.7° at lift-off, max 11° in the first 30 s, 887 ft/min 10 s after the lift-off, no height drop. Largest airborne speed
change 2.06 m/s² in the first 0.1 s (one frame, as in round 4). Labels: Parked → Taxiing → Holding short → Taxiing →
Lined up 28L → Take-off roll 28L → Climbing out → Climbing out 28L → Crosswind 28L → Departing; no label run under 1 s.

**Case P (single-turboprop landing, 28L; `od3_trace.mjs P`).** Arriving → Final 28R (provisional) for 3.6 s at ~5 km
(the track was then nearer the 28R extended centreline) → Final 28L; flare 0.1 → 5.0° over the last ~4 s, touchdown 411 m
past the 28L threshold on the centreline at 80.7 kt, 5.0° nose up, -223 ft/min, no height rise before it; landing roll
on the centreline (≤ 0.4 m off), runway taxi, turn-off labelled 'Taxiing on the runway 28L' → 'Taxiing' (the 0.5-s
'10R/28L' of an intermediate build is gone), holding short, taxi, 'Stopped' → 'Stopped · no signal'. No label run under
1 s; 0 ground stall frames, 0 rest moves, 0 samples off pavement. The trace's largest ground acceleration, 3.6 m/s² at
+79.7 s, is the inner-wheel pivot starting at its full rate at the hold (reference point 0 → 0.7 kt in one frame);
the lowest final pitch, -5° 60 s before touchdown, is a 1,446-ft/min interpolated descent between fixes (data).

### 11.6 Video (F9)

The two video snapshots were refreshed with the final engine files (`render.mjs snapshot --refresh=engine`; renderer,
shaders, models and data kept frozen), both cases re-scouted and re-planned, all plan gates pass (job overrides: two
removed as no longer needed, one added for the case P roll-out, with its reason), determinism 15 / 15 frames identical
in two fresh runs and 15 / 15 after rendering earlier frames, and ten spot stills were rendered and looked at. Details:
`docs/phase3_video.md` section 14.

### 11.7 Residuals (not fixed; all measured above)

- **Hidden take-offs although a runway is consistent** (`m3_hidden_runway_consistent` heli 1, pat 2, weekday 2, weekend
  3; before 1 / 0 / 0 / 1): rolling starts or touch-and-goes whose next airborne fix can only be reached with a 35-45°
  turn below 300 ft or a climb-out acceleration of 1.5-3.4 m/s², even with the 6° tolerance. This is the conflict F1
  leaves between the owner's M3 rule (hide only when no runway is consistent) and a plausible climb-out; one of them (a
  weekend rolling touch-and-go at 47-52 kt) is the `hard_stops` 1: the hidden fallback 'wait' stops the body at once
  while it fades out. Owner question: hide such a take-off, or draw the least implausible turn without a limit?
- `low_bank_frames` 24 / 1 / 0 / 13 / 7 (tolerance plans, ≤ 6° over the rule); `label_overflight_hwd` pat 122, weekend
  154 (fewer than before, 170 / 286; at 60 s pat 173, weekend 235, heli / od3p 58-59 - the 300-s gate window now
  catches overflight labels on traffic that flies a pattern minutes later; not analysed track by track);
  `label_flicker` 15 / 41 / 8 / 33 / 39 / 0 / 6; `ground_slow_fast_roll` heli 52; `pivot_in_place` 1-6 per window.
- On the last line-up rung the taxi may still speed up on the runway and slow to the 5.8-kt rolling start (od3s single:
  4 → 9 → 6 kt); case P's 3.6-s 'Final 28R' at 5 km; the pivot about the inner wheel starts at its full rate (11.5);
  night `label_lineup_rolling` 1 frame; weekday `label_takeoff_slow` 8 → 10 and pat `air_accel_samples` 4 → 8 (not
  analysed); `fw_in_building_frames` heli / od3p 6, weekday 24, weekend 60 and the other round-3 / round-4 residuals of
  section 10.6 that this iteration did not touch.

### 11.8 Other checks, wanted, inferred, not verified

- `node --check` on every edited JS file: OK. `python3 -I -B tools/check_airport.py`: ALL HARD CHECKS PASSED (run after
  these docs were written).
- **Wanted** (packages this iteration does not own): none new; the round-4 wants (section 10.7: `disp.flapsF` in the OD4
  runtime, `modelDims`) stand.
- **Inferred, not sourced** [inf]: every new constant - `LU_LEN` 60 m and `LU_RUNGS` (5.8 / 8 / 10 / 25 kt, 0.6-2.0 m/s²,
  12-25°/s), `LOW_BANK_*` / `BANK_HI_*` (15° at 100 ft → 35° at 300 ft), `CLIMB_BANK_MIN` / `TG_BANK_MIN` 25°, `BANK_TOL`
  6°, the 14° early-turn chord, `CLIMB_MIN_K` 0.35 over `CLIMB_MIN_S` 15 s to `CLIMB_TOP_FT` 400 ft, `LO_STALL_K` 1.05
  (stall = ACD approach speed / 1.3), `PIVOT_V` 0.5 m/s, `PO_FADE_M` 6 m, `PUSH_M` 6 m, `SLOW_FAST_K` 0.75 / `SLOW_FAST_S`
  12 s, `LABEL_HOLD_S` 1.5 s, `LEG_BACK_S` 5 s, `CALM_HOLD_S` 1 s, `TO_KEEP_S` 90 s, the classifier's `ARR_*` (10 km,
  6,000 ft, 30°, 60 s, -300 ft/min, 300 m closing). The bank limits are recalled training practice (no turns below
  ~400 ft, ≤ 30° in the pattern), not read from a handbook.
- **Not run:** live mode; the app in a browser beyond the video pipeline's frames; a real phone; the reviewer's probes
  for F8 (case A) and F12 on the final engine (F12 is measured by `teleports_attitude` at 60 s).
