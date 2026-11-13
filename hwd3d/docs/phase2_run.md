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

**D1 reference.** `docs/phase2/phase2_run_ref.py` builds, locally, the identity strings (ICAO address, registration,
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
| Air turn rate p99 / max (°/s) | 6.3 / 9.9 | 12.4 / 25.1 (EC30 helicopter) | 6.4 / 20 · 11.9 / 30 (EC30) |
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
- **a. Nose through a closed hangar (A, deterministic).** An M20P bridged a 51-s hole between two taxi fixes on a taxi
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
  80 kt" maximum of §2.4; the single-sample ground maxima of 258–370 m/s² (an M20P landing roll in A, a PTS1 drawn on
  the ground in phase "downwind" in B) are artefacts of the same kind at touchdown or at a stop.
- **d. Partly off pavement while slowing (B).** A C172 stopped with 1–3 wheels off pavement at (351, 22) north-east of
  the 28R end (25 / 46 still samples). Overall off-pavement rates stay at 0.007–0.28 % of ground samples.
- **e. A parked P180 with its fuselage in a building** for 1.5 s at its ramp spot (181.6, 396.7) before the placement
  moved it (15 samples, both B runs).
- Not seen in any run: airborne aircraft below the ground, ground aircraft off `site.groundY`, teleports of HWD traffic,
  fixed-wing aircraft on helipads, two aircraft on one spot.

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
| `docs/phase2/phase2_run_4_hangar_clipping_desktop.jpg` | F3a: M20P nose inside Hangar B |
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
