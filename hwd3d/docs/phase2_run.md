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
There is one new difference, not traced:

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
| F2 | Silent aircraft vanish off aprons; race with `seen_pos` latency; doc :392 | fixed | kept as `no_signal` [inf] for 30 min; latency allowance 30 s; continuation anchors; images 14 / 15; 6.5 row 2 corrected |
| F3 | OAK arrivals fade at 125-459 ft | fixed | far transitions; remaining vanishes at 5-8 ft (touchdown), before 76-2,063 ft |
| F4 | GroundPhysics seek / decay oscillation; `grass_route_frames` not gated; §6 attribution | fixed (root cause); residual open | stationary by target rest state; pavement snap; gated; route-on-grass 579 / 141 / 1 / 1 / 110 → 9 / 58 / 1 / 5 / 74 (the gate still fails); attribution corrected |
| F5 | 'ag:lin' straight chord; misaligned finals; transitions not counted | fixed (root cause); residual open | no chord (`transition_linear` 0 in all windows); turn-limited aligned finals; misaligned 3 / 0 / 0 / 1 / 4 → 0 / 0 / 0 / 2 / 1 (gated, still fails) |
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

None of these residuals was traced to a root cause in this round.

**Ground planform overlaps rose.** With one body stopped they rose in pat (8 → 24 frames, 2 pairs; one pair is a
run-up aircraft and a hold-short aircraft 9.7 m apart at 28R) and heli (0 → 3). They are reported but not gated.

**The new event difference is not traced:** weekday take-offs, 7 live against 6 offline.

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
