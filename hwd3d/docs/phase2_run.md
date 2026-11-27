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
| **B** | Wed 4 Nov 2026 23:00Z | 15:00 PST | 15 / 19 / 122 (weekday pattern work) | T&G 5, take-off 2, full-stop 3, low pass 1 (helicopter events not listed, D1) |

**Runs** (all through `node livetest.mjs <job>` with `RELAY=spawn`, i.e. `hwd_live_server.py --replay rec_pack --from <W>
--until <W+1h> --loop --no-adsbfi --quiet` on a free port 8760; the page was opened **on the relay's own port**, so static
files and `/api/*` came from the relay with its gzip — the real deployment path, not the harness's static server):

| Run | Window | Viewport | Relay identity mode | Scene span (display clock) | 10-Hz engine steps sampled |
|---|---|---|---|---|---|
| `satA_desktop` | A | 1280 × 720 | full (D1 masks LADD/PIA only) | 19:59:08 → 20:13:13Z | 6,604 (11.0 min) |
| `wedB_desktop` | B | 1280 × 720 | full | 22:59:16 → 23:13:12Z | 6,196 (10.3 min) |
| `satA_t_phone` | A | 390 × 844, DPR 1, touch, iPhone UA | `--ident type-only` | 19:59:07 → 20:13:13Z | 8,134 (13.6 min) |
| `wedB_t_phone` | B | 390 × 844 | type-only | 22:59:07 → 23:12:03Z | 7,477 (12.5 min) |
| `satA_t2_desktop` | A (a ~6-min part) | 1280 × 720 | type-only | not given (D1: it would date the cases it shows) | 2,949 (short type-only repeat for commit-safe HUD shots) |
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

`HWD.qa.counts().phases` and the runway line were read every 30 s (full series in the gitignored
`out/phase2/run_<w>_<dev>.json`). *(Round 5, R1: the table that stood here listed the phase counts, the scope counts and the
runway line at five scene times per window, about 2 min apart. With those times it placed individual movements within a few
minutes. It is replaced by window totals - D1, no committed time of an
individual aircraft's event.)* Ranges over those five readings per window, for the whole run (≈ 13-14 min of scene time):

| Window (whole run) | Drawn at a time | Tracks held at a time | Scope at a time: overflight / hwd / pending |
|---|---|---|---|
| A | 8–10 | 28–34 | 12–21 / 7–11 / 0–12 |
| B | 6–10 | 23–25 | 10–15 / 6–10 / 0–7 |

**Events vs the Phase 1 offline classifier** (window totals; live = whole run, ≈ 13 min; offline = first 12 min of the
window; helicopter events are not listed by window, D1):

| Event | A live / offline | B live / offline |
|---|---|---|
| touch_and_go | 5 / 5 | 6 / 5 |
| takeoff | 3 / 3 | 2 / 2 |
| full_stop_landing | 2 / 2 | 3 / 3 |
| low_pass_unresolved | 4 / 3 | 1 / 1 |
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
  third, type-only run.
- **b. Two taxiing aircraft pass through each other (B, both B runs; 'case B1').** In window B, for about
  6 s, an untyped high-wing single taxiing at ~2.3 m/s (4.5 kt) on a taxi route crossed a second high-wing single that was
  in phase "runup" but creeping at 0.7–2 m/s, north-east of the 28R end; centre distance down to 0.4 m; 56 / 60
  overlapping samples (1 pair). *(Round 4 iteration 3, F3: the clock times, the second aircraft's type and the position
  given here before were removed - D1, no committed time of an individual aircraft's event.)* GroundPhysics only
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

**F6 — One HWD departure tagged overflight (P3 classifier; 'case F6a').** In A, a single-engine piston was first seen
by the run just after lift-off (h ≈ 0 ft AGL, 83 kt), then 4 km away climbing. *(Round 4 iteration 3, F3, and round 5, R1:
its type, its clock times, when in the window it happened, its track and its position were removed - D1.)* The run never
saw its ground part and D6 tagged it overflight after 90 s; the "L corridor fix" rule did not fire on that first low fix
(cause not verified). The same can happen to any take-off whose ground part the app has not seen.

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

Committed (JPEG, ≤ 307 kB each; captions, sources and licences in `docs/phase2/SOURCES.json`; every HUD shot is from a
`--ident type-only` relay, the clean shot has no HUD, so none shows a registration or callsign). *Round 5 (R1, D1): the HUD
clock is pixelated in every shot that shows aircraft, the statistics sheet's event times, latest-events list and in-view line
are pixelated, and no caption gives the scene minute or the render's minute index.*

| File | What it shows |
|---|---|
| `docs/phase2/phase2_run_1_overview_desktop.jpg` | A, desktop Overview with the full HUD (type labels, phase line, runway line, list) |
| `docs/phase2/phase2_run_2_overview_phone.jpg` | A, phone portrait Overview, bottom sheet in peek state |
| `docs/phase2/phase2_run_3_card_stale_parking_phone.jpg` | F1 + F2 + F4 in one card: "Taxiing", Parking spot 41, "−50 ft · 40 ft AGL", 50 kt, +650 ft/min |
| `docs/phase2/phase2_run_4_hangar_clipping_desktop.jpg` | F3a: a single-engine piston's nose inside Hangar B (type label masked, D1 decision (d)) |
| `docs/phase2/phase2_run_5_type_only_bizjet_standin_desktop.jpg` | F5: parked bizjet as "Aircraft" with the airliner stand-in |
| `docs/phase2/phase2_run_6_runup_pad_clean_desktop.jpg` | B, three GA placeholders on/beside a paved pad, on pavement and apart (framebuffer, credit line added) |
| `docs/phase2/phase2_run_7_atc_sheet_phone.jpg` | ATC sheet: tower open at the scene time, LiveATC link, frequencies |
| `docs/phase2/phase2_run_8_stats_sheet_phone.jpg` | Statistics sheet: runway movements, circuit median (the clock, the in-view line, the per-runway last times and the latest-events list masked, D1) |

All run images (gitignored, 140 PNGs; the full-ident desktop runs show registrations and must not be published):
`out/phase2/run_{satA,wedB}_<view>_m<n>_desktop.png`, `run_{satA_t,wedB_t}_<view>_m<n>_phone.png` and
`run_satA_t2_*_desktop.png` (`m<n>`: the run minute of the shot set; not given here, D1), where `<view>` ∈ overview, tower, green, west, final28l, overview_clean, close_{parked,taxi,
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
  inf marker and "last signal N min ago" (the minutes pixelated, D1).
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
  (weekend TAYD beside Hangar Q, heli DA40 at a maintenance hangar door, weekday C182 at Hangar C).
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
| F4 | Bodies at rest over buildings / overlapping (REST LOCK); touch-and-go lift-off at 44-47 kt below the 47-48-kt stall estimate | `fw_in_building_frames` 6 / 0 / 0 / 25 / 84 / 0 / 6, `ground_overlap_frames` pat 13 | the lock froze the pose before `GroundPhysics` could push it clear; lift-off speed clamped to the reported speed only | once-per-lock push along the nose (0.5-6 m, `PUSH_M`); lift-off ≥ 1.05 x stall unless the climb-out fix was slower (`recon_substall_samples` 0 everywhere) | **partly**: buildings weekday 25 → 24, weekend 84 → 60, heli 6 and od3p 6 unchanged; overlaps pat 13 → 10; `air_substall_samples` unchanged at 0-2 (data low passes) |
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
  154 (fewer than before, 170 / 286; at 60 s pat 173, weekend 235, heli and od3p 58-59 - the 300-s gate window now
  catches overflight labels on traffic that flies a pattern minutes later; not analysed track by track);
  `label_flicker` 15 / 41 / 8 / 33 / 39 / 0 / 6; `ground_slow_fast_roll` heli 52; `pivot_in_place` 1-6 per window.
- On the last line-up rung the taxi may still speed up on the runway and slow to the 5.8-kt rolling start (od3s single:
  4 → 9 → 6 kt); case P's 3.6-s 'Final 28R' at 5 km; the pivot about the inner wheel starts at its full rate (11.5);
  night `label_lineup_rolling` 1 frame; weekday `label_takeoff_slow` 8 → 10 and pat `air_accel_samples` 4 → 8 (not
  analysed); `fw_in_building_frames` heli 6, od3p 6, weekday 24, weekend 60 and the other round-3 / round-4 residuals of
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

## 12. Fix round 4, iteration 3 - recheck findings F1-F10 (2026-11-14 / 2026-11-20)

The recheck of iteration 2 (section 11) raised ten findings: three major (F1 the PC-12 video's landing-roll stutter, F2 hidden
take-offs that make an aircraft vanish, F3 clock times of individual aircraft events in this file) and seven minor (F4-F10). This
iteration changed `js/live/{traffic,motion,ground,aircraft}.js`, `tools/traffic/{replay_engine,od3_trace}.mjs`, `tools/video/lib.mjs`,
`tools/check_airport.py` and the docs (`js/live/classifier.js`, `parking.js`, the app shell and every OD4-owned file were not changed).
It was interrupted once by the account usage limit (its partial work was checkpointed as WIP) and finished in a restart, which
re-measured everything below on the final files. Every change and constant is written up in `docs/phase2_traffic.md` §4 ("Fix round 4,
iteration 3"); the video part in `docs/phase3_video.md` section 15. Cases are named by window, class and an anonymous label, never by
time (D1): 'case P' / 'case S' (the OD3 heroes), weekend 'case H' (an aerobatic single) and 'case J' (a business jet), weekday 'case A'
(a single of iteration 2's F8), 'case T2' (a light single's touch-and-go; round 5, R8 (numbered R9 in round 5, corrected in round 5 iteration 3): it was called a light twin here before), weekend 'case W1' (iteration 2's F1 single).

### 12.1 Method

- **Before** = the engine at the end of section 11 (sha256 prefix of `traffic.js` 5fd978f57963), measured with the FINAL harness of
  this iteration; **after** = the final engine. Both at `--lookahead 120` (decision (c), the primary result) and at 60 s;
  `node tools/traffic/replay_engine.mjs <w> --strict --open app --lookahead 120|60`, 10-Hz frames, deterministic. Every harness run
  used a frozen copy of the engine (the working tree kept changing during the measurement); the final files are `traffic.js`
  56d24f9f7e91, `motion.js` b7a2c919ef7b, `ground.js` d793ac304a27, `classifier.js` f963f8f7cf95 (unchanged), `parking.js`
  24d5c0f2d885 (unchanged), harness `replay_engine.mjs` 3369690e691c (`aircraft.js` changed once more after the runs - one flap rule
  line, which the harness does not load; F4 below).
- **Reproduce first.** Each finding was reproduced in the before engine with a gate (new where none counted it, 12.2) or a 0.1-s probe
  of the case, its cause found in the code, fixed and re-measured. The probes are local scripts in the scratch directory (they print
  types and times and are not committed).
- **Looked at like a pilot**: cases P, S, H, J, A, T2 and W1 per 0.1 s (height, speed, heading, pitch, bank, flaps, label, target
  mode); the OD3 traces (`node tools/traffic/od3_trace.mjs S|P`); the two video scouts frame by frame (drawn speed against shown speed,
  yaw rate, flaps, pitch); spot stills of both videos and app snapshots of the SF50's flaps (all looked at; local only).

### 12.2 New and changed gates (harness `r4i3Frame` / `r4i3All`, all limit 0)

- `roll_yaw_rate_frames` (F1): on the ground on a runway (rectangle + 3 m), faster than 30 kt in both frames, the drawn heading turning
  faster than 3°/s over 0.3 s. `roll_speed_mismatch_frames` (F1): the same bodies, the drawn position's speed over 0.3 s differing from
  the shown speed (`disp.gs`) by more than 3 kt.
- `hard_stops_fade` (F2): a body drawn on the ground faster than 20 kt whose drawn speed falls below 2 kt within 2 s, WHATEVER its
  alpha (a fade-out does not excuse a stop). `hidden_rolling` (F2): a body drawn on the ground faster than 20 kt faded out by a hidden
  target (not a re-placement, a hangar or the edge of the view).
- `liftoff_pitch_dip` (F5): within 3 s after a drawn lift-off at HWD, the pitch more than 1.5° below its highest value since the
  lift-off. `label_landing_roll_rotating` (F6): 'Landing roll' on a ground body accelerating (> 0.3 m/s over 1 s) with the nose up
  (> 2°).
- `off_pavement_moving_frames` (F8): a moving fixed-wing ground body with a wheel off the physics' pavement in ANY target mode
  (`grass_route_frames` counts route mode only; the target mode is logged, `off_pave_moving_by_mode`).
- `low_bank_landing_frames` (F9): a planned landing / touch-and-go approach below 200 ft banked more than 15° (+ 0.5).
- Changed: `low_bank_frames` counts a FORCED take-off plan (F2: an aircraft already rolling on a runway, drawn with the least
  implausible climb-out instead of being hidden) as INFO `low_bank_forced_frames` - its excess over the limits is that plan's design
  and the owner question of 12.6; `ground_slow_fast_roll` counts only the PLANNED frames of a run above 0.75 VR (a run of 6 s of
  observed roll fixes between a planned re-acceleration and a planned lift-off was counted as 16 s of planned motion; the rest is INFO
  `ground_slow_fast_roll_reported`).

### 12.3 Findings: reproduction, cause, change, status

| # | Finding | Reproduced (before, 120 s) | Cause | Change | Status (after) |
|---|---|---|---|---|---|
| F1 (major) | Case P's landing roll stutters (52 → 43 → 37 → 50 kt drawn while 50 kt is shown) and yaws 4° at 50 kt; covered by a `heroAcc 3` plan-gate override | `roll_yaw_rate_frames` 131 / 650 / 65 / 470 / 546 / 0 / 47, `roll_speed_mismatch_frames` 81 / 231 / 39 / 111 / 185 / 0 / 34; video P plan gate 2.52 px/frame² | the fix-to-fix Hermite between roll fixes whose times jitter by 0.1-0.3 s (its speed is the reported one, its length the chord's); trail kinks where routes / plans / fixes join the axis; the release from 'behind' restarting the trail at a body beside the centreline; route roll-outs turning off at roll speed; a body held at its trail end still showing its speed | roll smoothing on observed fixes (reported speed integrated + kernel-mean residual corrections, smoothed speeds), nose held on the runway axis on a roll, lateral fade after 'behind', yaw-limited roll-out profile, shown speed = drawn speed at the trail end (`docs/phase2_traffic.md`) | **fixed**: both gates 0 in every window except `roll_yaw_rate_frames` night 3, weekday 6 (12.7); case P's roll-out in the video: drawn - shown ≤ 0.14 kt and yaw 0°/s over frames 1187-1930; the plan gate of `c-roll-dolly` 0.22 px/frame² with NO override (the job's `heroAcc 3` is removed) |
| F2 (major) | Hidden take-offs rose to 8; case H stops from 47 to 0 kt in 0.2 s mid-runway while it fades, case J vanishes at the hold and re-appears airborne | `m3_hidden_runway_consistent` 1 / 2 / 0 / 2 / 3, `hard_stops` weekend 1, `hard_stops_fade` 0 / 2 / 0 / 1 / 2, `hidden_rolling` 0 / 2 / 0 / 1 / 2 | the M3 fallback was a 'wait' at the last fix with a 0.4-s fade, also for aircraft already rolling | an aircraft already rolling on a runway is never hidden (forced least-implausible plan); any other M3 hide fades over 1.5 s while the body keeps its speed and direction | **fixed for rolling aircraft**: case H rolls on and climbs out (12.5); `hard_stops`, `hard_stops_fade`, `hidden_rolling` 0 everywhere; `m3_hidden_runway_consistent` 1 / 0 / 0 / 1 / 1 at 120 s (heli 2 at 60 s) - none rolling, **owner question** (12.6) |
| F3 (major, D1) | This file gave clock times of individual aircraft events in dated windows, one with a type; `check_airport.py` did not look for event times | lines of section 3 (findings b and F6 of the first run) | the D1(d) scan tested flagged-type / window pairs only | the two passages reworded by window and an anonymous label ('case B1', 'case F6a'; type, clock times, track and position removed); new hard check `d1_event_times` (12.8) | **fixed**: `python3 -I -B tools/check_airport.py` ALL HARD CHECKS PASSED, 0 clock times next to an aircraft event in 235 committed text files (13,254 units), 9 / 9 planted cases right |
| F4 | The SF50 retracts its take-off flaps on the taxi onto the runway and extends them again lined up (filmed) | video S trace: 0 → 15 at the hold, 15 → 0 taxiing, 0 → 15 lined up; app snapshot on that taxi: 0° | `flapRule` returned 0 for 'taxi'; no hold-to-runway state | take-off setting latched from the hold / run-up / line-up through 'taxi' / 'runway_taxi' (view latch + the engine's `tr._toFl`) | **fixed**: video S 0 → 15° at the hold (frames 959-999), held to 400 ft in the climb (frame 2867); the app snapshot on the taxi onto 28L draws 15° (was 0°) |
| F5 | The SF50's nose drops 2.8° just after lift-off at 0-1 ft | `liftoff_pitch_dip` 0 / 2 / 0 / 0 / 12 / 10 / 0 | the rotation hold needed vy > 0.3 m/s | lift-off attitude held 4 s while not descending, then blended; the attitude reached held within 1° for 3 s | **fixed**: 0 in every window; case S 8.3 → 8.5 → 9.0° and held (video and trace) |
| F6 | 'Low pass' at and after lift-offs (case A 2.2 s at 46-50 ft), 'Landing roll' flashes on take-off rolls | probe; `label_landing_roll_rotating` 0 / 0 / 0 / 0 / 7 / 0 / 0 (60 s: heli 3, od3p 3) | the lift-off latch was set only from roll labels, not from a fix-following lift-off | latch on the first airborne frame after a roll ≥ 0.6 VR; inside it 'Climbing out' when not descending; no 'Landing roll' on an accelerating, rotating body | **fixed**: case A reads Lined up → Take-off roll 28R → Climbing out 28R → Climbing out → Crosswind 28R; `label_landing_roll_rotating` 0; `label_flicker` 15 / 41 / 8 / 33 / 39 / 0 / 6 → 11 / 24 / 4 / 19 / 34 / 1 / 7 (no 'Take-off roll / Touch-and-go → Low pass → Climbing out' run left among the logged ones; one pat 'Climbing out → Low pass (~1 s) → Climbing out' on a fix-following climb remains) |
| F7 | Case T2 rolls ~20 s at a constant 41.4-41.7 kt | probe | the plateau of the 0.75-VR rule | no steady part > 3 s in the first pass (`vFit`); no approach floating > 6 s below 15 ft (the later touchdowns floated: weekday `air_float_runway_frames` 50 in a mid-iteration build) | **fixed**: T2 brakes 43 → 30 kt, 3 s at the bottom, accelerates to its lift-off; every touch-and-go of the weekday probe has a plateau ≤ 3 s; `ground_slow_fast_roll` 0 everywhere |
| F8 | Case W1's planned taxi out of the run-up area 'on grass' at 9.4 kt; 'Lined up' 18° off the axis | probe; `off_pavement_moving_frames` 9 / 6 / 1 / 0 / 71 / 0 / 11 | no pavement check on planned taxi connectors | paved connector search (`pavedEnds`), 'Taxiing on the runway' while > 10° off the axis, no second pivot dwell after a plan's pivot wait | **partly**: W1's connector crosses a NAIP-seen paved shoulder of the OSM taxiway (every wheel on the physics' pavement; `site.surface()`, OSM only, says 'grass'; looked at over NAIP), at ≤ 8.2 kt; no 'Lined up' while misaligned. `off_pavement_moving_frames` 9 / 0 / 1 / 0 / 92 / 0 / 11 - route-mode turns of large aircraft and rest poses (12.7) |
| F9 | Regressions against the round-3 final: wings over buildings while taxiing, low bank on reconstructed finals | `fw_in_building_frames` 6 / 0 / 0 / 24 / 60 / 0 / 6; `low_bank_landing_frames` 0 / 91 / 0 / 19 / 78 / 0 / 0 | the building push acted on bodies at rest only; landings used the climb-out bank rule; a resting body turned back toward a target starting behind it | sideways building push for taxiing bodies; rest wait for a target starting behind; 15° below 200 ft with longer finals for planned and fallback landings | **partly**: buildings weekday 24 → 16, weekend 60 → 61, heli 6 → 12 and od3p 6 → 12 (a hangar-door entry at 2-3 kt, 12.7); `low_bank_landing_frames` 0 / 12 / 0 / 16 / 42 / 0 / 0 (`landingBankOver` 3 / 1 / 4 plans: no final within 15° fits the hole) |
| F10 | Case S leaves the FBO at 12.5 kt, brakes at 3.1 m/s² into a 25°/s turn, turns at ~2 m/s² lateral (filmed at 8x) | OD3 trace | the taxi profile's corner limits were 2 m/s² / 25°/s, braking 2-3 m/s² | gentle taxi profile first (1 m/s² lateral, 20°/s, 1.5 m/s² braking, 10 kt on aprons), start pivot as a dwell, pivot onset ≤ 40°/s² | **partly**: 10-Hz trace ≤ 8.8 kt, braking ≤ 2.1 m/s², lateral ≤ 1.3 m/s², ≤ 21°/s; in the video's 30-fps grid the BODY still brakes at 3.0 m/s² for ~0.3 s and turns at 25°/s (1.7 m/s² lateral at 7.7 kt) - the follower's own corner rule (12.7) |

### 12.4 Results: strict harness, before → after, all seven windows

Cells: before → after at 120 s (after **bold** = still failing) (before → after at 60 s). `--open app`, 10-Hz frames unless the gate
says samples (1 Hz). "(new)" = gate added in this iteration (the before column is the before engine under the new gate).

| Gate (limit 0) | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|
| `hard_stops` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `grass_route_frames` | 0 → 0 (0 → 0) | 6 → 0 (8 → 2) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 32 → **54** (30 → 47) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_overlap_frames` | 0 → 0 (0 → 0) | 10 → **2** (12 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `fw_in_building_frames` | 6 → **12** (6 → 12) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 24 → **16** (24 → 16) | 60 → **61** (60 → 61) | 0 → 0 (0 → 0) | 6 → **12** (6 → 12) |
| `off_reports_samples` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 4 → 0 (4 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_overspeed_samples` | 0 → 0 (0 → 0) | 7 → **3** (7 → 3) | 1 → **1** (1 → 1) | 1 → **1** (1 → 1) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_climb_samples` | 59 → **59** (59 → 59) | 65 → **65** (65 → 65) | 3 → **3** (3 → 3) | 21 → **16** (21 → 16) | 103 → **101** (106 → 104) | 3 → **3** (3 → 3) | 23 → **23** (23 → 23) |
| `air_float_runway_frames` | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_substall_samples` | 2 → **2** (2 → 2) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 2 → **3** (2 → 3) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |
| `label_roll_flicker` | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 1 → **2** (2 → 2) | 0 → **1** (0 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `tg_no_contact` | 3 → **3** (3 → 3) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 5 → **5** (5 → 5) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |
| `m3_hidden_runway_consistent` | 1 → **1** (2 → 2) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 2 → **1** (2 → 1) | 3 → **1** (3 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_accel_samples` | 13 → **13** (13 → 13) | 8 → **8** (8 → 8) | 5 → **5** (5 → 5) | 9 → **9** (9 → 9) | 28 → **27** (28 → 27) | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) |
| `ground_fast_roll_frames` | 22 → **19** (22 → 19) | 20 → **5** (20 → 5) | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 33 → **25** (33 → 25) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `liftoff_plateau_frames` | 18 → **18** (18 → 18) | 21 → **21** (21 → 21) | 0 → 0 (0 → 0) | 9 → **9** (9 → 9) | 7 → **7** (7 → 7) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_takeoff_slow` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **2** (1 → 2) | 10 → **11** (10 → 11) | 13 → **10** (10 → 8) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_runway_end` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 2 → 0 (2 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_lineup_rolling` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `rest_pose_change_frames` | 0 → 0 (0 → 1) | 1 → 0 (0 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `pitch_phase_samples` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 1 → **1** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `roll_turn_samples` | 1 → **1** (1 → 1) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 3 → **3** (3 → 3) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_stall_frames` | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `roll_start_yaw_frames` | 18 → **16** (18 → 16) | 47 → **7** (47 → 7) | 56 → **52** (56 → 52) | 41 → **27** (41 → 27) | 56 → **45** (59 → 51) | 0 → 0 (0 → 0) | 19 → **16** (19 → 16) |
| `taxi_hole_stop_frames` | 0 → 0 (0 → 0) | 92 → **79** (92 → 79) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_overflight_hwd` | 0 → 0 (59 → 59) | 122 → **122** (173 → 173) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 154 → **154** (235 → 235) | 0 → 0 (0 → 0) | 0 → 0 (58 → 58) |
| `low_bank_frames` | 24 → **24** (0 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 13 → **13** (13 → 13) | 7 → **15** (7 → 15) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `pivot_in_place` | 3 → **5** (2 → 6) | 6 → **1** (3 → 2) | 2 → **2** (2 → 2) | 3 → **1** (3 → 1) | 3 → **1** (5 → 3) | 1 → 0 (1 → 0) | 0 → **3** (0 → 3) |
| `ground_slow_fast_roll` | 52 → 0 (52 → 0) | 9 → 0 (9 → 0) | 0 → 0 (0 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_flicker` | 15 → **11** (13 → 9) | 41 → **24** (45 → 27) | 8 → **4** (8 → 4) | 33 → **19** (33 → 19) | 39 → **34** (38 → 33) | 0 → **1** (0 → 1) | 6 → **7** (6 → 7) |
| `roll_yaw_rate_frames` (new) | 131 → 0 (131 → 0) | 650 → 0 (650 → 0) | 65 → **3** (65 → 3) | 470 → **6** (473 → 6) | 546 → 0 (547 → 0) | 0 → 0 (0 → 0) | 47 → 0 (47 → 0) |
| `roll_speed_mismatch_frames` (new) | 81 → 0 (81 → 0) | 231 → 0 (224 → 0) | 39 → 0 (39 → 0) | 111 → 0 (111 → 0) | 185 → 0 (184 → 0) | 0 → 0 (0 → 0) | 34 → 0 (34 → 0) |
| `hard_stops_fade` (new) | 0 → 0 (0 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `hidden_rolling` (new) | 0 → 0 (0 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `liftoff_pitch_dip` (new) | 0 → 0 (0 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 12 → 0 (12 → 0) | 10 → 0 (10 → 0) | 0 → 0 (0 → 0) |
| `label_landing_roll_rotating` (new) | 0 → 0 (3 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 7 → 0 (7 → 0) | 0 → 0 (0 → 0) | 0 → 0 (3 → 0) |
| `off_pavement_moving_frames` (new) | 9 → **9** (9 → 9) | 6 → 0 (8 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 71 → **92** (79 → 97) | 0 → 0 (0 → 0) | 11 → **11** (11 → 11) |
| `low_bank_landing_frames` (new) | 0 → 0 (0 → 0) | 91 → **12** (91 → 12) | 0 → 0 (0 → 0) | 19 → **16** (19 → 16) | 78 → **42** (78 → 42) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |

Zero before and after in every window at both lookaheads: `teleports_engine`, `teleports_signal_hwd`, `ghost_parked_frames`, `slow_liftoff`, `hops`, `air_hover_frames`, `heli_in_bldg_frames`, `label_contradictions`, `misaligned_transitions`, `stale_on_runway_frames`, `stale_overlap_frames`, `fast_off_runway_frames`, `landing_roll_speed_rise`, `liftoff_off_runway`, `touchdown_off_runway`, `ground_air_reappear`, `taxi_label_fast_frames`, `low_air_off_runway_frames`, `air_pair_close_frames`, `recon_substall_samples`, `label_vertical_sense`, `label_base_aligned`, `label_taxi_stopped`, `tg_label_frames`, `teleports_attitude`, `fast_ground_fixes`, `label_climbout_leg`, `label_lineup_misaligned`, `label_hold_on_runway`, `liftoff_pitch_low`, `touchdown_pitch_bad`, `pitch_rate_frames`, `label_taxi_still`, `snapshot_drift`, `label_final_arriving`, `planted_reappear`, `planted_low_air_box`, `planted_open_burst`, `d1_late_flag_forget`.

Failed gates (120 s): heli 18 → 15, pat 28 → 17, night 12 → 11, weekday 25 → 19, weekend 30 → 22, od3s 3 → 2, od3p 10 → 9 (60 s:
heli 19 → 16, pat 27 → 19, night 12 → 11, weekday 25 → 19, weekend 30 → 22, od3s 3 → 2, od3p 12 → 10); the before counts include the
eight new gates. **RESULT: FAIL in all seven windows, before and after** (residuals: 12.7). INFO at 120 s: `low_bank_forced_frames` 0 /
18 / 0 / 34 / 16 / 0 / 0 (forced take-offs, 12.6); `ground_slow_fast_roll_reported` 61 / 132 / 0 / 70 / 95 / 0 / 7. New engine counters
at 120 s (per window, heli / pat / night / weekday / weekend): `takeoffForced` 0 / 2 / 0 / 1 / 2, `touchGoFloatRefused` 0 / 0 / 0 / 240 /
0 (planning candidates), `restWaitBehind` 42-388 frames per window, `fallbackBankOver` weekday 1, `rollSmoothRuns` 7-30, `behindLatFade` 1-9, `landingBankOver`
0 / 3 / 1 / 0 / 4.

Against the round-3 final (section 9.3, the reviewer's F9 list), at 120 s: `tg_no_contact` 3 / 4 / 0 / 2 / 5 / 0 / 1 (unchanged by
this iteration), `m3_hidden_runway_consistent` 1 / 0 / 0 / 1 / 1 (round-3 final 2 / 0 / 0 / 0 / 1), `fw_in_building_frames` weekday
16 (2), weekend 61 (57), `ground_overlap_frames` pat 2 (6), `air_overspeed_samples` pat 3 (3), weekday 1 (0), `off_reports_samples`
weekday 0 (0), `air_substall_samples` heli / pat / weekday 2, weekend 3, od3p 1 (0 / 0 / 0 / 8 / 0), `air_float_runway_frames` pat 4 (0),
`hard_stops` 0 (0).

### 12.5 Cases, per 0.1 s, checked like a pilot (final engine, 120 s)

- **Case P (single-turboprop landing, 28L).** Touchdown unchanged: 411 m past the threshold on the centreline at 80.7 kt, 5.0° nose
  up, -223 ft/min, no height rise before it. The roll-out on observed fixes (`gg:roll` from +8.6 s) holds 299.9° to the turn-off and
  decelerates smoothly (61.9 → 39 kt over 12 s, ≤ ~2 m/s²; the largest ground deceleration of the trace, 3.1 m/s² at +21 s, is the
  planned route braking into the exit after the last roll fix). In the video scout: drawn - shown speed ≤ 0.14 kt and yaw 0°/s at
  every ground frame above 30 kt (frames 1187-1930; was 8.9-13 kt and up to 12.6°/s at frames 1601-1634). Labels unchanged (Arriving →
  Final 28R (provisional) 3.6 s → Final 28L → Landing roll 28L → Taxiing on the runway 28L → Taxiing → Holding short → Taxiing →
  Stopped → Stopped · no signal), no label run under 1 s.
- **Case S (light-jet take-off, 28L).** FBO exit ≤ 8.8 kt (10-Hz trace; video grid 8.4 kt, 12.7); take-off flaps from the hold
  through the taxi onto 28L and the line-up to 400 ft in the climb; constant 7.7-7.8-kt line-up, roll from 6 kt at ~1.75 m/s² to
  85 kt in 535 m on the centreline (≤ 0.1 m off); rotation 1.6° (-2 s) → 8.4° at the lift-off, then 8.5 → 9.0° held, 887 ft/min
  10 s after the lift-off, no height drop. The largest ground deceleration, 3.1 m/s² at -47.8 s, is a fix-to-fix Hermite between two
  taxi fixes near the hold (9.3 → 5.2 kt in 0.6 s; data-following, 12.7).
- **Case H (weekend aerobatic single, touch-and-go 28R; F2).** Touches down on observed fixes at 54 kt, rolls 6.9 s on the
  centreline to 46 kt, rotates 0 → 6.9° and lifts off at 46 kt (forced plan), climbs straight ahead at ~470 ft/min to ~190 ft, turns
  crosswind at 20-24° bank and joins its first fix on the downwind at ~380 ft. Labels: Final 28R → Touch-and-go 28R → Climbing out 28R
  (provisional) → Crosswind 28R (provisional) → Downwind 28R (provisional) → Downwind 28R. Before: 47 → 0 kt in 0.2 s while fading,
  absent 47 s, re-appearing 944 m away.
- **Case J (weekend business jet at the hold; F2, owner question).** Taxis to the hold at 7 kt, keeps taxiing at 7 kt while it fades
  out over 1.5 s (was 7 → 0 kt within 1 s), hidden ~45 s, re-appears airborne over 28L at ~20 ft and 148 kt (fades in over 0.5 s).
- **Case A (weekday single, take-off 28R; F6).** Lined up 28R → Take-off roll 28R (27.7 s) → Climbing out 28R (lift-off at 58 kt,
  7.6°) → Climbing out → Crosswind 28R; no 'Low pass', no 'Landing roll'.
- **Case T2 (weekday light single, touch-and-go 28L; F7).** 26 s on the ground: 43 → 30.3 kt at ~0.5 m/s², 3 s at 30.3 kt,
  accelerates at ~1.4 m/s² to its lift-off. The approach to it (fix-following, before the plan) dives at 1,100-1,300 ft/min with
  -3 to -5° pitch between 93 and 41 ft and then floats ~4 s at 0-5 ft (12.7).
- **Case W1 (weekend single, take-off 28R; F8).** Run-up pivot to the path heading in the plan's own wait, then taxi (no second
  8-s 'Stopped' dwell in the final engine), ≤ 8.2 kt over the NAIP-seen paved shoulder (all wheels on the physics' pavement), 'Taxiing
  on the runway 28R' while turning on, 'Lined up 28R' once aligned; the take-off itself as in section 11.5.

### 12.6 Owner question (F2): take-offs that are still hidden

The owner's M3 rule hides a take-off only when no runway is consistent. Three take-offs are still hidden at 120 s although a runway is
consistent (`m3_hidden_runway_consistent` 1 / 0 / 0 / 1 / 1): heli 'case C' (a single-engine piston, silent on a taxilane and heard
again at ~400 ft in the crosswind turn), a weekday single turboprop (heard again at ~200 ft) and weekend 'case J' (a business jet at the
hold, heard again at ~20 ft and 148 kt 885 m away 47 s later). None was rolling on a runway: each was taxiing or holding when it fell
silent, and no take-off within the plan limits reaches its next fix in the time left (`plan fail 11`). They fade out over 1.5 s while
they keep moving and fade in at their first airborne fix. Every aircraft that WAS rolling on a runway is now drawn with the least
implausible plan instead (forced: 5 take-offs in the five hour windows, `low_bank_forced_frames` 18 / 34 / 16 frames in pat / weekday /
weekend - e.g. a light single (case T2's aircraft) turning crosswind at 26-29° bank at 190-215 ft, 3-4° over the low-height rule). **Question:** should the
three non-rolling ones also be drawn with a forced plan (taxi, line-up and roll compressed, climb-out turn without the bank limit), or
stay hidden under M3? The engine supports both (`planTakeoffForced` is limited to rolling aircraft by `FORCE_V`).

### 12.7 Residuals (not fixed; all measured above)

- `roll_yaw_rate_frames` night 3, weekday 6: a planned landing roll-out turning onto an exit (night, 4°/s at 35 kt) and a fix-to-fix
  Hermite on 28L between two roll fixes, one of which fails the roll-run test (weekday, 6.7°/s at 40 kt, a 1.8-m S-curve beyond the
  15° axis hold).
- F10 in the video grid: the follower body turns at its 25°/s limit and brakes at 3.0 m/s² for ~0.3 s in case S's first FBO turn
  (frames 156-184, 7.7-8.4 kt): the follower's look-ahead uses the 2-m/s² body limits while the profile uses the gentle 1-m/s² ones.
  Case S also brakes 9.3 → 5.2 kt in 0.6 s near the hold on a fix-to-fix Hermite (data).
- F9: `fw_in_building_frames` heli 12, od3p 12 (a single entering a maintenance hangar door at 2-3 kt, its wing tips over the door
  jamb for ~1.2 s before the door rule fades it), weekday 16 (a high-wing single leaving its hangar, 'case C1'), weekend 61 (an
  observed single turning round in front of the west T-hangars at 0.5-3 kt, wings over the row for ~5 s); `low_bank_landing_frames`
  pat 12, weekday 16, weekend 42 (no final within 15° fits the hole; the least steep is drawn, 19-25° at 55-165 ft).
- F8: `off_pavement_moving_frames` weekend 92 (route mode 49: two business jets' route turns at taxi speed with one main wheel over
  a fillet edge - the same turns as before, more frames now that the gentle profile drives them slower, and `grass_route_frames`
  weekend 32 → 54 is the same; rest 36: a business jet settling onto its hold pose; landing plans 5, fix-following 2), heli 9 and
  od3p 11 (fix-following taxi past a grass corner), night 1.
- `pivot_in_place` 5 / 1 / 2 / 1 / 1 / 0 / 3: 30-32° turns with 0.29-0.5 m of movement in fix-following taxi (`gg:herm`, `extrap`) and
  routes, just under the gate's movement limit.
- `label_roll_flicker` pat 1, weekday 2, weekend 1 (a 'Landing roll' label held 0.3-1.8 s between two other labels: rolls that turn
  into a take-off roll or into runway taxi); `air_substall_samples` weekend 2 → 3 (a forced take-off's climb-out at 50 kt against a 54-kt estimate for 1 s);
  `low_bank_frames` weekend 7 → 15 (the one logged case: an aerobatic single's planned final at 27° at 214 ft, 0.1° over the
  rule; the weekend climb-outs of section 11.7 are forced plans now, INFO); heli 24 and weekday 13 as in section 11.7; case T2's dive and short float before its touchdown (data-following air hole before the plan).
- The other gates of section 11.7 (`air_climb_samples`, `air_accel_samples`, `liftoff_plateau_frames`, `roll_start_yaw_frames`,
  `taxi_hole_stop_frames`, `label_overflight_hwd`, `tg_no_contact`, ...) are unchanged or lower and were not worked on.
- Section 2.3's table (the first run's traffic counts every 2 min in windows A and B) gave the runway-movement counts of the moment,
  i.e. how many departures and landings happened in a 3-minute span. *Round 5 (R1): coarsened to window totals; `d1_event_times`
  now reads bare hh:mm:ss under a clock column header and flags such rows.*

### 12.8 Other checks, wanted, inferred, not verified

- `python3 -I -B tools/check_airport.py`: ALL HARD CHECKS PASSED, including D1(d) (types with dated windows) and the new
  `d1_event_times` hard check (F3): a clock time (hh:mm[:ss]Z / UTC / PST / PDT) in the same sentence or table row of committed text
  as an aircraft-event word (taxied, took off, landing roll, touchdown, lift-off, touch-and-go, crossed, first seen, signal ended,
  ...) is a hit; times on the hour, either end of a span of ≥ 5 min and a screenshot's 'scene hh:mm' are not; 9 planted cases
  (`--d1-windows` runs it alone in seconds). The window B caption in `docs/phase2/SOURCES.json` no longer gives the scene minute of
  case B1.
- **Round 5, D1 fixer (recheck R1 and R9, 2026-11-20).** R1: the planted cases of `d1_event_times` repeated two real event times
  of windows A and B word for word, and a comment tied them to those windows. Committed text and images also still pinned events:
  where in their windows cases F6a and B1 happened, section 2.3's per-slot table, the span of the short
  type-only repeat run, scene minutes and render minute indexes in screenshot captions, a snapshot minute in two captions, a
  traffic-render minute in `docs/phase2_traffic.md`, unmasked HUD clocks next to cards and lists, and the statistics sheet's
  latest-events list. All were reworded, coarsened to window totals or masked (sections 1, 2.3, 3 and 4,
  `docs/phase2/SOURCES.json`, 8 images, the run job's default shot minutes). `d1_event_times` now also reads:
  - string literals of .py / .js / .mjs files;
  - a bare hh:mm:ss under a clock column header;
  - a scene minute in a unit that names an aircraft's event or state;
  - offsets that pin an instant in a window or run.

  Markdown list items are read with their parent items. Its 23 planted cases use times built at run time from an instant in
  no recorded hour. Hits of this scanner on the pushed HEAD (7306714) **before**: 30 (`docs/phase2/SOURCES.json` 11,
  `docs/phase2_run.md` 13, `docs/phase2_traffic.md` 1, `tools/check_airport.py` 5); **after**: 0.
  `python3 -I -B tools/check_airport.py`: ALL HARD CHECKS PASSED (2 min). R8 (numbered R9 in round 5): case T2's aircraft is a light single, not a twin
  (12.0, 12.5, 12.6; `docs/phase2_traffic.md` §4). The pushed history (bd6cb30 onward) still holds the old text and images;
  rewriting it is the owner's decision.
- `node --check` on every edited JS file: OK. OD3 traces refreshed (`out/od3/trace_case_{S,P}.{json,csv}`, local). App snapshots of the
  SF50 at the hold, on the taxi onto 28L, lined up and climbing (`livetest.mjs` with the reviewer's job, local): flaps 15° at each,
  0 page errors.
- **Wanted** (packages this iteration does not own): none new; the round-4 wants (section 10.7: `modelDims`) stand.
- **Inferred, not sourced** [inf]: every new constant - `ROLLSM_V` 10 m/s, `ROLLSM_ALIGN` 15°, `ROLLSM_H` 5 s, `ROLLSM_VH` 2.5 s,
  `ROLLSM_RAMP` 2.5 s, the 15-m spike rule, the 8 / 15° axis hold, the max(30 m, 1.5 s) lateral fade, `ROLL_YAW_V` 15 m/s / `ROLL_YAW_W`
  3°/s, `HIDE_FADE_S` 1.5 s, `FORCE_V` 8 m/s, the forced-plan cost weights, `LO_HOLD_S` 4 s, `LO_PEAK_S` 3 s / 1°, `TG_PLATEAU_S` 3 s,
  `TG_FLOAT_S` 6 s, the 0.3-m/s² minimum braking of `vFit`, the 150-m paved-connector search, `BLD_PUSH_V` 8 m/s, the rest wait's
  REST_LOCK_M + 1 m and 60°, `LAND_BANK_FT` 200 / `LAND_BANK_DEG` 15, `TAXI_LAT_G` 1.0 m/s², `TAXI_W_G` 20°/s, `TAXI_DEC_G` 1.5 m/s²,
  `RAMP_V` 10 kt, `PIV_ACC` 40°/s², and the gate limits of 12.2.
- **Not run:** live mode; a real phone; the full videos (the orchestrator's).

## 13. Fix round 5 - engine and video (recheck R2-R9 of round 4 iteration 3; items V1-V7, 2026-11-20 / 2026-11-21)

The recheck of iteration 3 (section 12) left nine findings open (R1 D1 - the D1 fixer's, 12.8; R2-R9 here; *corrected in round 5 iteration 3,
15.3 G9: this section numbered the last two R9 / R10 - there are nine findings, R1-R9*). This round changed
`js/live/{traffic,motion,aircraft}.js`, `tools/traffic/replay_engine.mjs`, `js/video/camera.js`, `tools/video/render.mjs` and the docs
(`ground.js`, `classifier.js`, `parking.js` and the app shell unchanged; no OD4-owned file touched). It was stopped once by a container
restart; its partial work was checkpointed as WIP (9085b5d; the later checkpoints bab65be and 5f98e52 hold intermediate states of the restart) and the restart re-verified every item on frozen copies, corrected what did not
hold and re-measured everything below on the final files. The video part is in `docs/phase3_video.md` section 16. Cases are named by window,
class and an anonymous label, never by time (D1): 'case S' / 'case P' (the OD3 heroes), weekend 'case W1' (a single, R4), weekend 'case J' (a
business jet), heli 'case C' (a single), and from this round weekend 'case Q1' (a high-wing single) and 'case Q2' (a low-wing single), two forced take-offs, and
pat 'case Q3' (a light single's forced take-off).

### 13.1 Method

- **Before** = the final engine of section 12 (commit f4b9c59: `traffic.js` 56d24f9f7e91) measured with the FINAL harness of this round
  (`replay_engine.mjs` 80c282d7607b; for the import of the view flap rule the frozen copy carries the final `aircraft.js`, which without the
  engine's `tr._postLand` behaves as the iteration-3 rule). It reproduces every cell of table 12.4 (0 / 1,064 differ), so the before of the
  old gates is table 12.4 and the before of the new gates comes from the same runs. **After** = the final engine: `traffic.js` e200ec261122,
  `motion.js` c9b302d72d77, `aircraft.js` 2fbc4c333138, `ground.js` d793ac304a27, `classifier.js` f963f8f7cf95, `parking.js` 24d5c0f2d885
  (the last three unchanged). Harness `node tools/traffic/replay_engine.mjs <w> --strict --open app --lookahead 120|60 --log`, 10-Hz frames,
  deterministic, on frozen copies (the after runs used harness 788d4fd65f79, which differs from the final one only by the fallback of the
  hand-over gate for an engine without `target0`).
- **The interrupted attempt's WIP** (`traffic.js` 526842f98071) was measured first, the same way. It had fixed V1 and V4. It had NOT: the
  5-deg/s roll limit below 200 ft (V2) let the bank lag hard data turns there (`roll_turn_samples` weekend 3 → 16, heli 1 → 4, weekday 1 → 5)
  and hid their bank excess (`low_bank_landing_frames` weekend 42 → 17 only because the drawn bank lagged); forced take-offs still banked
  > 20 deg below 300 ft in 126 weekend frames and slowed in 21 / 25 / 88 pat / weekday / weekend frames; `taxi_speed_mismatch_frames`
  17-37 per window; `fw_in_building_frames` weekend 61 → 66; the hand-over gate compared against the target's vertical-speed field,
  which is not the derivative of its height (below). All of that is corrected in the final engine (13.3).
- **Reproduce first, then look like a pilot**: every item has a gate (13.2) and a 0.1-s probe of its case (local scripts in `out/`, not
  committed: they print types and window seconds); the OD3 traces per second (`node tools/traffic/od3_trace.mjs S|P`); the two video
  scouts frame by frame; spot stills and app snapshots (looked at; local only).

### 13.2 New and changed gates (harness `r5Frame`, all limit 0; plan gate in `tools/video/render.mjs`)

- `postland_toflaps_frames` (V1): on the ground after a drawn landing roll with no departure since (no line-up, take-off / touch-and-go /
  stop-and-go roll, run-up, take-off plan target, flight, parking or hangar), the engine's flap target at the take-off setting;
  `postland_toflaps_view_frames`: the same for the detailed models' rule (`js/live/aircraft.js` `flapRuleOf`, now exported pure and run per
  track with its own latch).
- `low_roll_rate_frames` (V2): airborne within 3 km below 200 ft AGL, the drawn bank changing faster than 5 deg/s over 0.3 s - an UNFORCED
  roll (wing rock); INFO `low_roll_rate_turn_frames`: the same while the engine's bank is catching up with the coordinated bank of the body's
  own turn (`disp.rollCatch`, 13.3 V2).
- `taxi_speed_mismatch_frames` (V3): on the ground within 3 km, shown speed 2-30 kt, the drawn position's speed over 0.3 s more than 1.5 kt off
  the shown speed.
- `label_lowpass_after_liftoff` (V4): 'Low pass' or 'Final' within 30 s after a drawn lift-off from a roll (>= 0.6 VR) while the body climbs
  or descends slower than 300 ft/min.
- `forced_low_bank_frames` (V6): a forced take-off plan airborne below 300 ft banked more than 20 deg (+ 0.5); `forced_speed_drop_frames`
  (V6): a forced plan's airborne speed falling by more than 0.5 kt over 1 s.
- `handover_rate_frames` (V2 / V6): in the first 6 s after a take-off plan hands over to fix-following in the air, the drawn speed changing
  faster than 1.2 m/s² or the vertical speed faster than 1.5 m/s² over 1 s AND more than 0.3 m/s² faster than the fix-following target
  does over the same second (INFO `handover_rate_raw_frames`: the drawn rate alone). The target's rates come from its POSITIONS (0.2-s
  differences): the vertical Hermite's `vy` field is the linear blend of its end slopes, not its derivative, and where the fixes' heights
  step it moved the target 100 ft in 1.4 s at a 'vy' of 4.9 m/s - the WIP gate blamed the hand-over for the data.
- Video plan gate `camAcc` <= 0.05 for chase shots (V3): the camera's judder - its per-frame step speeding up / slowing down / speeding up
  again by more than that fraction of the step (`js/video/camera.js`; the reviewer's stutter measures 0.37; `docs/phase3_video.md` 16).

### 13.3 Items: reproduction, cause, change, status

| # | Item (finding) | Reproduced (before, 120 s) | Cause | Change | Status (after) |
|---|---|---|---|---|---|
| V1 (R2) | Take-off flaps at a hold-short after a landing, kept through the taxi-in (video P on camera) | `postland_toflaps_view_frames` 11,705 / 6,240 / 2,015 / 10,130 / 20,244 / 0 / 3,598; video P 15° from the post-landing hold to the end | the iteration-3 latch was set by any hold-short and cleared only by a landing roll, parking, a hangar, no signal or the air | an ARRIVAL state (`tr._postLand`: set by a landing roll; cleared in the air, parked / in a hangar, by a departure - lined up, a take-off / touch-and-go / stop-and-go roll, a run-up, a take-off plan target - or after 5 min at rest): no take-off setting while arriving; the landing setting stays on the landing roll and runway taxi, the flaps go up once off the runway (after-landing check, timing [inf]) and stay up; the same rule in the views (`flapRuleOf`, exported) | **fixed**: both gates 0 in every window at both lookaheads; video P: flap target 0 from frame 2058 (off the runway), the flaps retracting through the hold-short (21° → 5°) and up (< 0.05°) from frame ~2166 *(round 5 iteration 3, 15.3 G9: this said ~2185)* to the stop (corrected in 14.6: this cell said 0° at the hold-short); app snapshot on the taxi-in 0° (was 15°) |
| V2 (R6) | SF50 wing rock at the plan → fix hand-over (-2.9 → +5.8° in 1.6 s at 45-70 ft) | `low_roll_rate_frames` 245 / 889 / 152 / 822 / 1,804 / 14 / 127; video S 15°/s at the hand-over | the climb-out's Dubins join turned at its full 25-deg radius for a 1-m / 1-deg offset (two short opposite arcs); the plan end and the fix-following target differ at the hand-over (a step in lateral position, heading, speed, vertical speed); the roll rate was 15°/s at any height | joins within 5 m / 4° fly straight to the fix's point abeam (`straightHermite`), others the longest straight with a natural Hermite join within 12° (`gentleJoin`, the climb-out kept straight >= 13 s); the hand-over is BLENDED (`target()`): from the body's own state, quintic weights over 5-12 s for the lateral, vertical and velocity differences and over up to 90 s (<= 0.6 m/s of extra speed) for an along-track gap; below 200 ft near the field the roll rate is <= 4.8°/s, except that the bank may not lag the coordinated bank of the body's own turn by more than 8° (then it follows at up to 15°/s, `disp.rollCatch`) | **fixed for wing rock**: `low_roll_rate_frames` 0 / 0 / 0 / 1 / 1 / 0 / 0; INFO turn-forced rolls 118 / 291 / 59 / 306 / 919 / 2 / 66 (data paths turning 7-13°/s below 200 ft); `roll_turn_samples` 1 / 1 / 0 / 1 / 3 / 0 / 0 → 0 / 0 / 0 / 1 / 3 / 0 / 0 (the WIP's hard limit had raised it to 4 / 1 / 0 / 5 / 16 / 0 / 1); case S: roll <= 1.8°/s and bank <= 2.4° through the hand-over (trace and video) |
| V3 (R7 + F10) | Fix-following taxi stutter (drawn 7.9 → 4.6 → 6.3 kt while 7.8 shown) and chase-camera judder in video S; P exit turn at 1.6-1.9 m/s²; S's first FBO turn braked at 3.0 m/s² | `taxi_speed_mismatch_frames` 44 / 172 / 61 / 194 / 205 / 6 / 17; video S scout 1.75 kt and a 3.99-m/s² hitch in `lineup-chase` | the Hermite through every observed taxi fix followed their GNSS scatter; route turn-offs used the 2-m/s² corner limits; the follower's look-ahead braked for corners at the body limits, not the gentle profile's | TAXI SMOOTHING on observed ground fixes (`taxiRunOf`: the fixes' polyline smoothed along its length, 6 m, ends pinned; the reported speeds integrated with kernel-mean residual corrections; no smoothing within 15 m of a hangar footprint; less where it would put a main or nose wheel on the grass); roll-outs that turn off take the turn at the gentle limits (1 m/s², 20°/s, braking <= 2 m/s² below taxi speed) when that does not keep them faster longer; the follower's corner look-ahead uses the gentle limits behind a gently profiled target; a corner's speed cap is its lowest within 8 m (no sawtooth); a body at its trail end shows the speed it moves at; video plan gate `camAcc` | **fixed in both videos**: video S drawn - shown <= 0.54 kt over every ground frame, judder 0-0.01 in its chase shots, FBO braking <= 1.95 m/s², lateral <= 0.9 m/s² (vertex frames to 1.57); video P exit and taxi-in lateral <= 1.22 m/s², yaw <= 12.7°/s. `taxi_speed_mismatch_frames` 18 / 19 / 4 / 2 / 27 / 1 / 13 (13.8) |
| V4 (R3) | 'Low pass' 2.4-4.5 s after touch-and-go lift-offs while climbing | `label_lowpass_after_liftoff` 27 / 129 / 0 / 12 / 29 / 0 / 0 | the lift-off latch mapped the label to the climb-out, but the runway-label branch preferred the plan phase ('low_pass' of a fix-to-fix low-pass curve) | inside the lift-off latch (not descending) the climb-out wins over a low-pass / final / base / arriving plan phase; a final descending at 150-300 ft/min within 30 s of a lift-off is a climb-out | **fixed**: 0 in every window at both lookaheads |
| V5 (R4) | Case W1: a 9.6-s stand ('Stopped' 7.7 s) between the run-up pivot and the taxi; three runway formats in the labels | probe of case W1 | the profile spent its spare time as a stop at the start of the taxi, after the plan's pivot wait; the runway end of a body turning onto the runway came from its heading | the profile's start stop is spent BEFORE the pivot wait (standing with the run-up label); the run-up / hold label stays until the body moves faster than 0.5 m/s; inside a take-off plan the runway end is the plan's while the body moves less than 90° from it, and a planned climb-out with no runway in its label reads the plan's | **fixed**: case W1 stands with 'Engine run-up' through the pivot and moves off 1.3 s after it (the rest-lock release) with no 'Stopped'; 'Taxiing on the runway 28R' → 'Lined up 28R'; case S reads 'Climbing out 28L' from the lift-off through the hand-over (was 'Climbing out' → 'Climbing out 28L'). Residual: W1 still creeps lined up at ~2 kt for ~10 s before its 14-s wait (13.8) |
| V6 (R5 + decision (e)) | Forced take-off plans banking 25-31° at 146-220 ft, their speed falling and rising, hand-over surges; three non-rolling take-offs hidden | `forced_low_bank_frames` 0 / 197 / 0 / 138 / 163 / 0 / 0, `forced_speed_drop_frames` 0 / 73 / 0 / 12 / 88 / 0 / 0, `handover_rate_frames` 65 / 13 / 26 / 13 / 61 / 3 / 40, `m3_hidden_runway_consistent` 1 / 0 / 0 / 1 / 1 | the forced climb-out took the first bank rung that flew the path at <= 1.3 x the reported speed, turned soon after the lift-off, slowed back to the fix's speed at its end; the body raced to close the gap it had left on the roll (2.4-11 kt faster than its plan, then slowed back); M3 hid every non-rolling take-off | every bank rung of 15 / 18 / 20 / 25 / 30° is tried with the straight climb long enough to reach the height where the forced rule (15° from the wheels, 20° at 300 ft, 30° above) allows it (>= 13 s), and the cheapest by the cost (bank above the rule x 5) is drawn; a forced climb-out's speed only rises until the join (or eases down at <= 0.2 m/s² from a fast lift-off); behind a planned climb-out the body flies <= 0.25 m/s faster than its target and the hand-over blend starts from the body; decision (e) (`docs/PLAN.md` 6b): in a recorded pack (display >= 90 s behind the recording) a take-off of an aircraft that was not yet rolling gets a forced plan - taxi, line-up (the fastest line-up rungs), roll at up to the class's roll limit, lift-off, join - when one within the physical limits exists (bank within the forced rule + 0.5°, 0.7-1.5 x the reported speed, climb within the class limit, roll acceleration within the class limit) | **partly**: `forced_speed_drop_frames` 0 everywhere; `forced_low_bank_frames` 0 / 5 / 0 / 0 / 137 / 0 / 0 (cases Q3, Q1, Q2: 13.8); `handover_rate_frames` 66 / 17 / 11 / 19 / 107 / 1 / 36 (13.8); decision (e): case J (weekend business jet at the hold) now taxis on, lines up, rolls and joins its first fix with a forced plan (`m3_hidden_runway_consistent` weekend 1 → 0 at 120 s; 60 s keeps M3: 1); heli case C and the weekday single turboprop stay hidden with the 1.5-s fade because no plan within the limits exists (13.6) |
| V7 (R9) | Regressions of iteration 3: `fw_in_building_frames` heli 6 → 12, od3p 6 → 12 (a hangar-door entry), `grass_route_frames` weekend 32 → 54 | table 12.4 | the door rule tested the TARGET's planform: the body runs ~1 m beside / behind it; the gentle profile drove two business jets' route turns slower over the same fillet edge | the door rule also tests the BODY's pose 0.6 s ahead while the target heads into a hangar (fades it before a wing tip crosses the jamb); the taxi smoothing is not used in front of hangar doors | **fw_in_building fixed**: heli 12 → 0, od3p 12 → 0, weekday 16 → 0, weekend 61 → 55; **grass_route partly**: weekend 54 → 49 (the nose wheel of a long-wheelbase jet swinging outside the fillet in route turns; a nose-wheel-on-the-centreline heading was tried and dropped - the trail does not reach a wheelbase ahead of the body in route mode) |

### 13.4 Results: strict harness, before → after, all seven windows

Cells: before → after at 120 s (after **bold** = still failing) (before → after at 60 s). `--open app`, 10-Hz frames unless the gate
says samples (1 Hz). Before of the old gates = table 12.4 (reproduced cell for cell); "(new)" = gate added in this round, before = the
iteration-3 engine under the final harness. Rows where every cell is 0 before and after are left out (list below the table).

| Gate (limit 0) | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|
| `grass_route_frames` | 0 → 0 (0 → 0) | 0 → 0 (2 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 54 → **49** (47 → 45) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `misaligned_transitions` | 0 → 0 (0 → 0) | 0 → **1** (0 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_overlap_frames` | 0 → 0 (0 → 0) | 2 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `fw_in_building_frames` | 12 → 0 (12 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 16 → 0 (16 → 0) | 61 → **55** (61 → 55) | 0 → 0 (0 → 0) | 12 → 0 (12 → 0) |
| `air_overspeed_samples` | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) | 1 → **1** (1 → 1) | 1 → **1** (1 → 1) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_climb_samples` | 59 → **57** (59 → 57) | 65 → **66** (65 → 66) | 3 → **3** (3 → 3) | 16 → **16** (16 → 16) | 101 → **100** (104 → 103) | 3 → **3** (3 → 3) | 23 → **21** (23 → 21) |
| `air_float_runway_frames` | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_substall_samples` | 2 → **2** (2 → 2) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 3 → **2** (3 → 2) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |
| `label_roll_flicker` | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 2 → **1** (2 → 1) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `tg_no_contact` | 3 → **3** (3 → 3) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 5 → **5** (5 → 5) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |
| `m3_hidden_runway_consistent` | 1 → **1** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 1 → 0 (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_accel_samples` | 13 → **13** (13 → 13) | 8 → **9** (8 → 9) | 5 → **6** (5 → 6) | 9 → **9** (9 → 9) | 27 → **32** (27 → 28) | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) |
| `ground_fast_roll_frames` | 19 → **19** (19 → 19) | 5 → **5** (5 → 5) | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 25 → **24** (25 → 24) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `liftoff_plateau_frames` | 18 → **18** (18 → 18) | 21 → **21** (21 → 21) | 0 → 0 (0 → 0) | 9 → **9** (9 → 9) | 7 → **9** (7 → 8) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_takeoff_slow` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 2 → **1** (2 → 1) | 11 → **5** (11 → 5) | 10 → **5** (8 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_lineup_rolling` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `rest_pose_change_frames` | 0 → 0 (1 → 1) | 0 → 0 (1 → 14) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `pitch_phase_samples` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 1 → 0 (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `roll_turn_samples` | 1 → 0 (1 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 3 → **3** (3 → 3) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_stall_frames` | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `roll_start_yaw_frames` | 16 → **10** (16 → 10) | 7 → **8** (7 → 8) | 52 → **5** (52 → 5) | 27 → **28** (27 → 28) | 45 → **25** (51 → 26) | 0 → 0 (0 → 0) | 16 → **10** (16 → 10) |
| `taxi_hole_stop_frames` | 0 → 0 (0 → 0) | 79 → **78** (79 → 78) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_overflight_hwd` | 0 → 0 (59 → 59) | 122 → **122** (173 → 173) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 154 → **154** (235 → 235) | 0 → 0 (0 → 0) | 0 → 0 (58 → 58) |
| `low_bank_frames` | 24 → **20** (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 13 → 0 (13 → 0) | 15 → **10** (15 → 10) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `pivot_in_place` | 5 → **5** (6 → 6) | 1 → 0 (2 → 2) | 2 → **3** (2 → 3) | 1 → **3** (1 → 3) | 1 → **4** (3 → 2) | 0 → 0 (0 → 0) | 3 → **5** (3 → 5) |
| `label_flicker` | 11 → **6** (9 → 5) | 24 → **20** (27 → 22) | 4 → **4** (4 → 4) | 19 → **19** (19 → 21) | 34 → **32** (33 → 37) | 1 → 0 (1 → 0) | 7 → **4** (7 → 4) |
| `roll_yaw_rate_frames` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) | 6 → **6** (6 → 6) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `off_pavement_moving_frames` | 9 → **15** (9 → 15) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 92 → **55** (97 → 62) | 0 → 0 (0 → 0) | 11 → **15** (11 → 15) |
| `low_bank_landing_frames` | 0 → 0 (0 → 0) | 12 → **10** (12 → 10) | 0 → 0 (0 → 0) | 16 → **15** (16 → 15) | 42 → **40** (42 → 40) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `postland_toflaps_view_frames` (new) | 11705 → 0 (11706 → 0) | 6240 → 0 (5741 → 0) | 2015 → 0 (2015 → 0) | 10130 → 0 (10130 → 0) | 20244 → 0 (17597 → 0) | 0 → 0 (0 → 0) | 3598 → 0 (3598 → 0) |
| `low_roll_rate_frames` (new) | 245 → 0 (212 → 0) | 889 → 0 (890 → 0) | 152 → 0 (152 → 0) | 822 → **1** (819 → 1) | 1804 → **1** (1805 → 1) | 14 → 0 (14 → 0) | 127 → 0 (117 → 0) |
| `taxi_speed_mismatch_frames` (new) | 44 → **18** (45 → 18) | 172 → **19** (173 → 20) | 61 → **4** (61 → 4) | 194 → **2** (194 → 2) | 205 → **27** (208 → 30) | 6 → **1** (5 → 0) | 17 → **13** (17 → 13) |
| `label_lowpass_after_liftoff` (new) | 27 → 0 (27 → 0) | 129 → 0 (129 → 0) | 0 → 0 (0 → 0) | 12 → 0 (12 → 0) | 29 → 0 (29 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `forced_low_bank_frames` (new) | 0 → 0 (0 → 0) | 197 → **5** (197 → 5) | 0 → 0 (0 → 0) | 138 → 0 (138 → 0) | 163 → **137** (164 → 137) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `forced_speed_drop_frames` (new) | 0 → 0 (0 → 0) | 73 → 0 (73 → 0) | 0 → 0 (0 → 0) | 12 → 0 (12 → 0) | 88 → 0 (88 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `handover_rate_frames` (new) | 65 → **66** (65 → 64) | 13 → **17** (13 → 19) | 26 → **11** (26 → 11) | 13 → **19** (13 → 19) | 61 → **107** (61 → 71) | 3 → **1** (3 → 1) | 40 → **36** (40 → 36) |

Zero before and after in every window at both lookaheads: `teleports_engine`, `teleports_signal_hwd`, `ghost_parked_frames`, `slow_liftoff`, `hard_stops`, `hops`, `air_hover_frames`, `heli_in_bldg_frames`, `label_contradictions`, `stale_on_runway_frames`, `stale_overlap_frames`, `fast_off_runway_frames`, `landing_roll_speed_rise`, `liftoff_off_runway`, `touchdown_off_runway`, `ground_air_reappear`, `taxi_label_fast_frames`, `off_reports_samples`, `low_air_off_runway_frames`, `air_pair_close_frames`, `recon_substall_samples`, `label_vertical_sense`, `label_base_aligned`, `label_taxi_stopped`, `tg_label_frames`, `teleports_attitude`, `fast_ground_fixes`, `label_climbout_leg`, `label_runway_end`, `label_lineup_misaligned`, `label_hold_on_runway`, `liftoff_pitch_low`, `touchdown_pitch_bad`, `pitch_rate_frames`, `label_taxi_still`, `snapshot_drift`, `ground_slow_fast_roll`, `label_final_arriving`, `roll_speed_mismatch_frames`, `hard_stops_fade`, `hidden_rolling`, `liftoff_pitch_dip`, `label_landing_roll_rotating`, `postland_toflaps_frames`, `planted_reappear`, `planted_low_air_box`, `planted_open_burst`, `d1_late_flag_forget`.

**Failed gates per window** (heli / pat / night / weekday / weekend / od3s / od3p): before (iteration-3 engine, final harness) 20 / 24 /
15 / 26 / 29 / 5 / 13 at 120 s and 21 / 26 / 15 / 26 / 29 / 5 / 14 at 60 s; **after 15 / 18 / 12 / 20 / 24 / 3 / 10 at 120 s and 16 /
20 / 12 / 20 / 26 / 2 / 11 at 60 s**. The strict harness still FAILS in all seven windows (residuals, 13.8). Exit code 1 in every run,
no crash; 10-Hz frames, deterministic.

INFO (120 s): `low_roll_rate_turn_frames` 118 / 291 / 59 / 306 / 919 / 2 / 66 (13.2), `handover_rate_raw_frames` 154 / 93 / 17 / 41 /
271 / 14 / 96. Engine counters (120 s): `handoverBlend` 6 / 11 / 5 / 9 / 17 / 2 / 4, `taxiSmoothRuns` 32 / 31 / 20 / 42 / 62 / 4 / 13,
`rollOutGentle` 15 / 63 / 4 / 11 / 72 / 0 / 10, `takeoffForced` (rolling) 0 / 2 / 0 / 1 / 3 / 0 / 0, `takeoffForcedAny` (decision (e))
weekend 1, `takeoffForcedNoFit` heli 1, weekday 1, `takeoffPreWait` weekend 1, `doorBody` heli 22, od3p 22.

### 13.5 Cases, per 0.1 s, checked like a pilot (final engine, 120 s)

- **Case S (light-jet take-off, 28L; V2, V3, V5).** From the FBO to the line-up (video scout, every frame): drawn - shown speed
  <= 0.54 kt, braking <= 1.95 m/s², lateral <= 0.9 m/s² (single route-vertex frames to 1.57), yaw <= 18.8°/s. Take-off flaps from the
  hold through the taxi onto 28L, the roll and the climb to 400 ft. Roll from 6 kt to 85 kt in 535 m on the centreline (<= 0.1 m
  off), lift-off 550 m past the threshold at 8.4° pitch, 802 ft/min 10 s after the lift-off, no height drop. The hand-over to the
  fixes 6-8 s after the lift-off at 45-70 ft is smooth: vertical speed 743 → 707 → 716 → 746 → 802 ft/min (1-s steps), 111.9 → 118 kt
  over 5 s, bank <= 2.4°, roll rate <= 1.8°/s (iteration 3: -2.9 → +5.8° in 1.6 s). Labels: Climbing out 28L (provisional) →
  Climbing out 28L. Not fixed: the crosswind turn at 900-1,570 ft rocks the wings (13.8).
- **Case P (single-turboprop landing, 28L; V1, V3).** Touchdown unchanged: 411 m past the threshold on the centreline at 80.7 kt,
  5.0° nose up, -223 ft/min. Roll-out on the centreline (<= 0.2 m), flaps 40° through the roll-out and the runway taxi; the flaps go
  up once the aircraft is off the runway - retracting through the post-landing hold-short (21° → 5°), up (< 0.05°) from frame ~2166 *(round 5 iteration 3, 15.3 G9: this said ~2185)* of video P
  (corrected in 14.6: this said 0° at the hold-short) - and stay up to the stop (iteration 3: 15° from that hold to the stop). Exit turn and taxi-in: lateral <= 1.22 m/s², yaw <= 12.7°/s (iteration 3: 1.6-1.9 m/s² at 20°/s in the exit
  turn). The largest ground deceleration, 3.6 m/s² at +21 s (12.5: 3.1), is still the planned route braking after the last roll
  fix, now into the gentler turn-off (13.8).
- **Case W1 (weekend single, take-off 28R; V5).** Stands with 'Engine run-up' through the run-up wait and the pivot, moves off 1.3 s
  after the pivot (the rest-lock release) with no 'Stopped' and no second stand; taxi <= 9.3 kt with every wheel on the physics'
  pavement; 'Taxiing on the runway 28R' while turning on, then 'Lined up 28R'. Residual: lined up, it creeps at ~2 kt for ~10 s before
  its 14-s wait (13.8).
- **Case J (weekend business jet at the hold; V6, decision (e)).** Before: faded out while taxiing at the hold, hidden ~45 s,
  re-appeared airborne at ~20 ft and 148 kt. Now drawn throughout: fix-following to the hold area (with a data stop-and-go, 8 → 0.7 →
  10 kt within ~5 s between two taxi fixes, before the plan starts), then the forced plan: taxi at 7 kt, 'Lined up 28L (provisional)'
  ~6 s before it stops on the centreline (it is still rolling at 7 kt when the label changes), an 8-s wait, the roll 0 → 118 kt in
  ~13.7 s over ~445 m at the jet class's roll limit (4.5 m/s², 13.8), rotation to 10°, lift-off at ~123 kt, a straight climb at 10°
  pitch, the hand-over at its first fix (~21 ft, 147 kt); there the data climb takes over: 480 → 2,650 ft/min within 5 s, pitch 10 →
  13.3° (counted by `handover_rate_frames`). Labels: Taxiing → Lined up 28L (provisional) → Take-off roll 28L (provisional) → Climbing
  out 28L (provisional) → Climbing out 28L.
- **Heli case C and the weekday single turboprop (V6, decision (e)): still hidden** with the 1.5-s fade (13.6).
- **Cases Q1, Q2 (weekend) and Q3 (pat), forced plans of aircraft that WERE rolling (V6).** No speed drop in any (`forced_speed_drop_frames`
  0; before 73 / 12 / 88 frames in pat / weekday / weekend). Q3: 21-22° at 283-291 ft for 0.5 s (5 frames; the forced rule allows ~19.7° there).
  Q1: 21-24° for ~10 s at 210-298 ft, up to 6.4° over the forced rule (the cheapest of the bank rungs by the cost). Q2: up to 31° for
  4 s at 136-198 ft (14.5° over the rule): its crosswind turn is flown at 99 kt and the drawn bank is the coordinated bank of the
  body's own turn at that speed.

### 13.6 Decision (e) and `m3_hidden_runway_consistent`

Decision (e) (`docs/PLAN.md` 6b, answering the owner question of 12.6): in a recorded pack (display >= 90 s behind the recording,
`REC_LOOK_S`) a take-off of an aircraft that was not yet rolling gets a forced plan when one within the physical limits exists:
bank within the forced rule (15° from the wheels, 20° at 300 ft, 30° above) + 0.5°, 0.7-1.5 x the reported speed, the climb within
the class limit, the roll acceleration within the class limit (`LIM.rollAcc`); live mode (no recording ahead) and plans outside the
limits keep M3. **`m3_hidden_runway_consistent` (120 s): 1 / 0 / 0 / 1 / 0 (before 1 / 0 / 0 / 1 / 1); 60 s: 2 / 0 / 0 / 1 / 1
(before 2 / 0 / 0 / 1 / 1).** Of the three take-offs of 12.6:
- weekend case J: forced plan drawn at 120 s (13.5); at the 60-s lookahead the next fix is not yet in the buffer when the plan is
  needed, so M3 keeps it hidden (1);
- heli case C (silent on a taxilane, heard again at ~400 ft in the crosswind turn): no plan within the limits - the best of the bank
  rungs needs 8.7° more bank than the forced rule allows, 1.27 x the reported speed, 4.5 m/s climb and 2.53 m/s² roll acceleration
  (class limit 2.5); hidden with the 1.5-s fade, as before;
- the weekday single turboprop (heard again at ~200 ft): the best rung needs 13.5° more bank than the rule allows (0.76 x the reported
  speed, roll 3.07 m/s² within its class limit 3.5); hidden, as before.
Heli at 60 s holds a second hidden take-off (2), unchanged from table 12.4.

### 13.7 Video

Both OD3 snapshots refreshed with this engine, re-scouted and re-planned (all gates pass, no override), determinism and spot stills
re-checked: `docs/phase3_video.md` section 16. The app's own snapshot cases: `docs/phase2_app.md` section 12.

### 13.8 Residuals (not fixed; all measured above)

- **NEW, open: wing rock above 200 ft in fix-following turns.** The drawn bank oscillates by 8-10° every ~0.7-1.4 s in steady turns
  on observed fixes (`aa:geo`): case S's crosswind turn at 900-1,570 ft swings between -14 and -24° (31 reversals of >= 4° in video
  S's `d-climb-chase`, frames 3256-3591), case J's at 500-770 ft between -12 and -23°. The traces show the body's turn rate jumping at each 1-s fix
  and decaying in between, and the bank (the coordinated bank of the body's own turn rate, 0.5-s lag, 15°/s above 250 ft) follows each pulse. Not introduced
  here: the Phase 3b / round-4 video S trace has 32 such reversals (the same 900-1,570-ft turn plus the low hand-over one fixed in
  V2), and the weekend window has 1,609 reversal episodes of >= 4° before and 1,591 after (local probe). No gate covers it above
  200 ft; a bank from a smoothed turn rate (~1.5-2 s) would remove it but changes every drawn bank and needs the video re-snapshot.
- `handover_rate_frames` 66 / 17 / 11 / 19 / 107 / 1 / 36 (before 65 / 13 / 26 / 13 / 61 / 3 / 40): at 1 Hz the drawn vertical speed
  changes at up to 2.5 m/s² (the follower's limit) or the speed at up to 2.9 m/s² in the first 6 s after a hand-over, mostly where
  the data climb steepens right after the plan's end (case J: 480 → 2,650 ft/min in 5 s) and the target's own rate is lower over the
  same second. Not traced to one cause in this round.
- `forced_low_bank_frames` pat 5 (case Q3), weekend 137 (cases Q1, Q2: ~10 s and 4 s; 13.5): forced plans of rolling aircraft are always drawn (the
  least implausible plan), unlike decision (e)'s, which must be within the limits.
- `taxi_speed_mismatch_frames` 18 / 19 / 4 / 2 / 27 / 1 / 13: data-following taxi between fixes that do not qualify for the smoothing
  (single fixes, stop-and-go fixes, runway-taxi plans, route mode into a stop) - e.g. case J's 8 → 0.7 → 10 kt; 0 in the two video
  heroes' ground frames.
- `low_roll_rate_frames` weekday 1, weekend 1: one frame each at 200 ft (5.1°/s, where the limit starts ramping up).
- Case J's forced roll at the jet class's roll limit (4.5 m/s², 0 → 118 kt in ~445 m): within the limits as they are, but the class
  limit [inf] is generous for a large-cabin jet (a real ground roll is well over 1 km); 'Lined up 28L (provisional)' while still rolling at
  7 kt for ~6 s.
- Case W1: ~2 kt creep while lined up for ~10 s before its 14-s wait.
- Case P: the planned braking after the last roll fix, 3.6 m/s² for ~3 s (12.5: 3.1), and the speed rise 62.54 → 63.26 kt at the plan →
  observed hand-over on the roll-out (unchanged).
- Regressions against table 12.4 (120 s unless noted): `misaligned_transitions` pat 0 → 1, `air_climb_samples` pat 65 → 66,
  `air_accel_samples` pat 8 → 9, night 5 → 6, weekend 27 → 32 (60 s: 28), `liftoff_plateau_frames` weekend 7 → 9,
  `rest_pose_change_frames` pat 60 s 1 → 14, `roll_start_yaw_frames` pat 7 → 8, weekday 27 → 28, `pivot_in_place` night 2 → 3, weekday
  1 → 3, weekend 1 → 4 (60 s: 3 → 2), od3p 3 → 5, `label_flicker` 60 s weekday 19 → 21, weekend 33 → 37, `off_pavement_moving_frames`
  heli 9 → 15, od3p 11 → 15 (in each window a smoothed taxi run crossing an OSM grass cell at 8-10 kt in `gg:taxi`: the
  smoothing's wheel guard did not catch it). The others were not traced to a cause in this round.
- Still failing as in 12.7: `grass_route_frames` weekend 49 (V7: the nose wheel of a long-wheelbase jet outside the fillet in route
  turns), `fw_in_building_frames` weekend 55, `air_climb_samples`, `air_accel_samples`, `tg_no_contact`, `liftoff_plateau_frames`,
  `ground_fast_roll_frames`, `label_overflight_hwd`, `taxi_hole_stop_frames` pat 78, `low_bank_landing_frames`, `air_substall_samples`,
  `air_overspeed_samples` (12.7).

### 13.9 Correction of section 12

12.3/12.5 corrected: section 12 (12.3 F8, 12.5 case W1) says the final engine had no second 8-s 'Stopped' dwell after the plan's pivot
wait. The recheck (R4) found that case W1 still stood 9.6 s between its run-up pivot and the taxi, 7.7 s of it labelled 'Stopped', and
that its labels used three runway formats: the dwell had moved before the taxi start, it had not gone. Fixed in this round (13.3 V5);
the other statements of 12.3 / 12.5 stand.

### 13.10 Other checks, wanted, inferred, not verified

- OD3 traces refreshed (`node tools/traffic/od3_trace.mjs S|P`, local), checked per second (13.5). App snapshot cases (`livetest.mjs`,
  local job, 14 instants on the two heroes, looked at every image): `docs/phase2_app.md` 12.
- `node --check` on every edited JS file: OK. `python3 -I -B tools/check_airport.py --d1-windows` with this section in place: passed
  (0 types named with a dated window, 0 event times; planted cases all classified right).
- **Wanted** (packages this round does not own): none new; the round-4 want (`modelDims`, 10.7) stands.
- **Inferred, not sourced** [inf]: every new constant - `GENTLE_BANK` 12°, `HO_MIN_S` / `HO_MAX_S` 5 / 12 s, `HO_AL_V` 0.6 m/s,
  `HO_AL_MAX_S` 90 s, `HO_LAT_M` 5 m / `HO_DH` 4° (the straight-join limits), `ROLL_RATE_LO` 4.8°/s below 200 ft within `LOWJ_R`
  3.5 km (rising to 15°/s by 250 ft; the code comments say 400 ft), `ROLL_LAG_MAX` 8°, `TSM_V` 1.5 m/s, `TSM_W` 6 m, `TSM_HC` 4 s,
  `TSM_VH` 2 s, `TSM_RAMP` 3.5 s, `TSM_HANGAR_M` 15 m, the forced bank rule (15° / 20° at 300 ft / 30°), `FORCE_BANKS`, `FORCE_KMAX`
  1.5, the 0.7 lower speed ratio, `FORCE_STRAIGHT_S` 13 s, `FORCE_DEC` 0.2 m/s², `TO_OVER_V` 0.25 m/s, `REC_LOOK_S` 90 s, the 5-min
  end of the arrival state, the 0.5-m/s run-up label hold, the 90° plan-end rule, the door rule's 0.6-s body look-ahead, the 8-m
  corner window, the gentle turn-off profile (1 m/s², 20°/s, braking <= 2 m/s² below taxi speed), the after-landing flap timing, and
  the gate limits of 13.2.
- **Not run:** live mode; a real phone; the full videos (the orchestrator's, after OD4's look fixes).

## 14. Fix round 5, iteration 2 - recheck findings G1-G10 (2026-11-21)

The recheck of section 13 left ten findings open (G1-G10: D1 / doc items, engine, video and QA). This iteration changed
`tools/check_airport.py`, `docs/phase2/` (seven images and `SOURCES.json`), `js/live/{traffic,motion}.js`,
`tools/traffic/replay_engine.mjs` and the docs (`js/live/aircraft.js`, `ground.js`, `classifier.js`, `parking.js`, the app shell,
`js/video/**`, `tools/video/**` and every OD4-owned file unchanged). Cases keep the names of section 13 (window, class, anonymous label).

### 14.1 Method

- **Before** = the final engine of section 13 (`traffic.js` e200ec261122, `motion.js` c9b302d72d77) under the final harness of this
  iteration (`replay_engine.mjs` 987e7e39fbca, with the gates of 14.2; an engine without `rollLimOf` is gated on its class limit). On every
  old gate it reproduces table 13.4 cell for cell. **After** = `traffic.js` 9437e3c5a1ea, `motion.js` ba446d169cb7 (the committed files).
  Harness `node tools/traffic/replay_engine.mjs <w> --strict --open app --lookahead 120|60 --log`, 10-Hz frames, frozen copies of the
  trees, deterministic.
- Every engine item was reproduced first on a 10-Hz probe of the case (local scripts in `out/`, not committed: they print types and window
  seconds), then fixed and re-probed. Three intermediate trees were measured in full and rejected (14.3 G5): the first held an engine cut, the
  second doubled `taxi_speed_mismatch_frames`, the third kept the reported landing-roll step. The OD3 traces (`node tools/traffic/od3_trace.mjs S|P`) and both video scouts were checked
  frame by frame on the final tree (14.5, `docs/phase3_video.md` section 17).

### 14.2 New gates (harness `r5i2Frame`, all limit 0)

- `bank_rock_episodes` (G3): airborne within 4.5 km of the ARP, at any height, the drawn bank swinging >= 4° one way and >= 4° back, each
  swing within 1.5 s (three consecutive extrema of the bank, 1° hysteresis) - wing rock. A roll into or out of a turn, however fast, is one
  swing and is not counted.
- `forced_roll_acc_frames` (G4): a forced take-off plan on the ground faster than 30 kt, the drawn speed rising faster over 1 s than the
  type's roll limit (`traffic.js` `rollLimOf`, 14.3 G4) + 0.1 m/s².
- `ground_decel_frames` (G5): on the ground within 4.5 km, the drawn speed - or the speed of the drawn position along the heading, where the
  shown speed is >= 1 m/s - falling by more than 3.6 m/s² (`LIM.rollDec` 3.5 + 0.1) over 0.3 s, unless the target itself brakes as hard
  and smoothly (<= 6 m/s²): INFO `ground_decel_plan_frames` (a planned roll-out's or the data's own braking, not a hand-over).

### 14.3 Findings: reproduction, cause, change, status

| # | Finding | Reproduced | Cause | Change | Status |
|---|---|---|---|---|---|
| G1 (major, D1) | Two planted cases of `d1_event_times` still carried real offsets (a snapshot minute and a traffic-render minute that the removed doc text gave), next to paraphrases of the real events | `tools/check_airport.py` built them as `'... %d min ...' % <number>` - the scan reads the literal with `%d`, not the number, so it could not see them | the plants were written from the removed doc text | every planted case rewritten with event wording unrelated to any case (east-flow runways 10L / 10R, which no recorded hour used; a twin, a gyroplane, a wash rack); the two offsets are synthetic (derived from the synthetic instant) and are stepped on while they equal an offset number that ever appeared in the docs' git history (the + / - lines of `docs/**` and `*.md`, read with the scanner's own offset pattern; 6 such numbers today, the two real ones among them) | **fixed** in the tree: 23 / 23 planted cases right, 0 hits; the pushed history still holds the old plants (corrected in round 5 iteration 3, 15.3 G5: the literal clock times in 9672e31, f4b9c59 and 7306714, the two real offsets as `% 16)` / `% 33)` plants in 9085b5d, bab65be and 5f98e52 - the pushed tip when this was rechecked; the checkpoint 974d219 pushed since holds none of them) - rewriting the history is the owner's decision (15.3 G5) |
| G2 (major, D1) | Committed screenshots kept the runway line's `(last N min)` - minutes since the page started watching, which with a committed run start gives the scene minute | looked at the 15 images: the runway line in `phase2_run_{1,2,4,5}` and `phase2_fix1_12` / `phase2_fix2_13`, and the card's `last signal N min ago` in `phase2_fix2_14` (whose snapshot minute is in the pushed history) | the image rule treated only the HUD clock as a clock | the runway-movements line pixelated in the six images, the minutes of `last signal N min ago` in the seventh (Pillow, re-saved from the committed JPEGs; checked by eye that nothing is readable); `SOURCES.json` MASKED notes; every app screenshot now carries a by-eye **clock review** `d1_clock` (`checked ...` / `masked ...`), a hard check of `check_airport.py`: the HUD clock and every HUD element derived from elapsed time (the runway line's `(last N min)`, `watching since`, `last signal N min ago`) count as a clock and are masked wherever an aircraft is in view | **fixed**: 15 / 15 screenshots reviewed (7 masked this iteration); the ATC-sheet screenshot keeps its clock (no aircraft in view) |
| G3 (major) | Wing rock above 200 ft in fix-following turns (video S's crosswind turn -14 <-> -24°; 2,091 swing frames weekend) | 10-Hz probes of every window (local) and the new gate: `bank_rock_episodes` 225 / 665 / 152 / 368 / 710 / 23 / 96 on the section-13 engine (120 s; heli / pat / night / weekday / weekend / od3s / od3p); the reviewer's swing count reproduced (weekend 1,928 swings above 200 ft) | (1) the drawn bank was the coordinated bank of the body's own heading rate, which follows the target's acceleration; (2) that acceleration pulses: the air curve of a hole drawn as a polyline (a Dubins arc in <= 5° steps, `retimePath`'s 96-point resampling, the pattern-departure arc) stepped its DIRECTION at every vertex - case S's crosswind turn every ~1.5 s -, and a Hermite between 1-s fixes interpolates the reported velocities linearly, its turn rate stepping at every fix with the scatter of the reported track angles | (a) `motion.js` `polyAtSmooth`: along a polyline air path the direction is interpolated between the vertex tangents, so the target turns smoothly (`turnFlight`, `straightHermite`, `retimePath`, the departure arc; the plan validators keep reading the old vertex directions, `atRaw`, so no plan choice changes with it); (b) `traffic.js` `turnRateS`: the bank target is the coordinated bank of the TARGET's mean turn rate from BANK_H = 1 s ago (its own history) to 1 s ahead (sampled ahead without side effects between two airborne fixes), kept within 8° of the coordinated bank of the body's own turn smoothed over 0.4 s, 0.3-s lag; on a reconstructed plan (smooth by design) the body's own smoothed turn, 0.5-s lag, as before; (c) gate `bank_rock_episodes` | **fixed for fix-following flight**: `bank_rock_episodes` 225 / 665 / 152 / 368 / 710 / 23 / 96 → 3 / 6 / 2 / 3 / 25 / 0 / 2 (120 s; 60 s in 14.4); video S: 0 swings in the crosswind turn (round 5: 33). Left: 14 of the weekend's 25 in one forced climb-out of a rolling aircraft (case Q2, both engines: its body's own turn rate pulses between < 1 and ~6.8°/s behind the plan), the rest single episodes in data turns (14.7) |
| G4 (major) | Decision (e)'s forced plan for weekend case J (a large-cabin business jet) rolled 0 -> 118 kt in 13 s at the jet class's 4.5 m/s² after an 8-s lined-up wait; 'Lined up 28L (provisional)' while still rolling at 7 kt | probe (local) and the round-5 strict run: `takeoffForcedAny` weekend 1, forced roll 4.5 m/s²; the section-13 engine gated on the type limit of this iteration (a local run of the before tree with `rollLimOf` in the gate): `forced_roll_acc_frames` weekend **102** (case J, 4.5 against 1.98 m/s²) | one roll limit per class (`LIM.rollAcc.jet` 4.5) in the decision-(e) fit test; the forced selection took the lowest cost with no regard for the roll; the line-up label at any speed inside a planned taxi | `rollLimOf(T)`: the class limit capped by the FAA ACD MTOW (jets <= 10 t 2.5, <= 20 t 2.1, heavier 1.8 m/s²; turboprops > 5.7 t 3.0), never below the type's own take-off table value; every forced rung above it is skipped (decision (e) and rolling forced plans); among the decision-(e) candidates within the limits the SLOWEST roll wins, then the cost (no lined-up wait bought with a faster roll); 'Lined up' only below 2.5 m/s (faster: Taxiing / Taxiing on the runway); gate `forced_roll_acc_frames`; `docs/PLAN.md` 6b (e) notes the type limit | **fixed**: `forced_roll_acc_frames` 0 in every window; case J has no plan within its 1.98 m/s² and is hidden with the 1.5-s fade, as M3 hides it at 60 s (`m3_hidden_runway_consistent` weekend 0 -> 1, by design, 14.5); case S no longer reads 'Lined up' while rolling |
| G5 (major) | Ground speed steps and dead stops at mode hand-overs (32.6 -> 6.4 kt in one frame, 12.4 -> 5.4 -> 0 kt, ...), not gated | 0.1-s probes and per-frame debug of the cases (local); the new gate: `ground_decel_frames` 30 / 68 / 15 / 52 / 85 / 0 / 15 on the section-13 engine (120 s) - 76 episodes: 22 target steps (the plan's or the data's speed itself jumps), 17 speed drops at hand-overs, 8 dead stops at taxi speed, 29 drops of the drawn position's speed alone | every step of the reported kind was the follower's trail-end clamp `c.v = (sEnd - c.s) / dt` firing where the target fell back to the body or stopped in front of it - a landing roll's 'behind' hold released with the target 0.3 m ahead after `BEHIND_S`; a smoothed taxi run at 13 kt handing over to a route whose profile starts with a turn-round stop | where the clamp would brake harder than G_DEC = 3 m/s² while the target still MOVES, and the body can reach its speed within max(3 m, 0.6 s of travel) past the trail end, the body runs on past the trail end along its last direction (`trailAt` extrapolates; the trail must give a direction - >= 0.5 m, or >= 0.1 m within 20° of the nose, as the fresh trail of a released 'behind' hold; the target's points are laid again once it is ahead; the trail restarts at the body if the overrun outgrows its allowance by 1 m or the target is > max(10 m, 3 s of travel) away and not ahead), letting the target catch up at <= 0.3 m/s per m (>= 0.8 x its speed); the box filter shrinks gradually past the end; gate `ground_decel_frames`. Measured in full and dropped: (1) the overrun on a one-point trail (a body created moving) held a trainer still while its target taxied off and cut it at 151 m - the only engine cut of the iteration; (2) a run-out past a STANDING target along a trail extension of its braking distance doubled `taxi_speed_mismatch_frames` (27 -> 54 weekend, 19 -> 36 pat) and added 6 wing-in-building frames for ~5 fewer decel frames; (3) a flat 0.5-m trail rule kept the reported 32.6 -> 6.4 kt step (that trail is 0.3 m long). Tried on two windows and dropped: never clamping a body that has overrun (off-pavement frames weekend 56 -> 92) | **partly fixed**: the reported steps are gone (the weekend landing roll released from its 'behind' hold 0.3 m behind its target, 32.6 -> 6.4 kt, and a similar release in the heli window, 31.8 -> 6.3 kt; one later 0.3-s sample of the weekend one still reads 11 m/s², 31.9 -> 25.6 kt; the 12.4 -> 5.4 -> 0 kt route start is a standing target and remains), hand-over speed drops 17 -> 6 episodes, but `ground_decel_frames` 30 / 68 / 15 / 52 / 85 / 0 / 15 → 24 / 65 / 12 / 52 / 77 / 0 / 15 (120 s) still fails in six windows (per episode: 22 target steps as before, dead stops at taxi speed 8 -> 15 - a body that has overrun its trail end stops dead when its target then stops -, 29 position-speed drops; 14.7) |
| G6 (minor, D1) | Section 13.4 / 13.8 reported two windows' counters as one (wording corrected in round 5 iteration 3, 15.3 G4) | text | the counters of two windows were reported together | 13.3 / 13.4 / 13.8 and the round-4 cells of 11.3 / 11.7 / 12.3 / 12.7 (and `docs/phase2_traffic.md` §4) give each window's numbers separately | **fixed** in the tree (9.4 too since round 5 iteration 3); the pushed history is left to the owner |
| G7 (minor, docs) | 'Flaps 0° at the post-landing hold-short' (video P) is wrong: they are retracting through it; `CLAUDE.md` said every committed app screenshot has its clock pixelated | the round-5 scout: 20.9° at frame 2109 (hold), 5.2° at 2152, up (< 0.05°) from 2166 *(round 5 iteration 3, 15.3 G9: this said ~2185)* | the flap TARGET is 0 from frame 2058; the statements read the target | `docs/phase3_video.md` 16, 13.3 / 13.5 corrected in place (marked), `docs/phase2_app.md` 12 notes that a snapshot draws the target at once; `CLAUDE.md` reworded (screenshots that show aircraft; the ATC sheet keeps its clock) | **fixed**; this iteration's video P: 17 |
| G8 (minor) | (a) R5 residual of the forced climb-outs; (b) the engine's flap target went back to the landing setting when a landed aircraft crossed a runway after leaving the landing runway, while the views kept 0 | (b) `D.flapsF` 1.0 on post-landing runway crossings: heli 97 frames, weekday 83, weekend 160, od3p 32, pat 31, night 414 (recheck) | (b) `(post && ph === 'runway_taxi') ? 1` | (b) on the runway while arriving the engine now KEEPS its previous target (the views' rule): the landing setting from the landing roll through the runway taxi, 0 once the flaps went up | (b) **fixed**: the engine and the views agree (OD3 P trace: 1 through the runway taxi, 0 once off it; video P: 17); (a) **open**, not changed: `forced_low_bank_frames` pat 5 -> 15, weekend 137 -> 151 (the same plans; the body follows their smoothed direction and banks 1-2° more in the same turns, 14.7) |
| G9 (minor) | Strict harness regressions against table 12.4 (reproduced exactly) | the recheck's table equals 13.4 | listed in 13.8 | not addressed; kept in the residual list (14.7) with this iteration's own regressions | **open** (14.7) |
| G10 (minor, QA) | The local livetest job read the wheel contacts 11.4 m below the ground in four ground cases on the current tree | the recheck's job (a local copy) on the final tree: its first case of the session read -1,142 to -1,146 cm, the same case after the 90-frame freeze +0.3 / -0.3 / -1.1 cm, its later cases correctly | the job read `view.worldPt` right after the model loaded and the clock was paused - before a drawn frame had updated the view's model matrix (OD4's runtime) | the local job (out/, not committed) draws two frames at the frozen clock before it reads the contacts | **fixed** (a probe artefact; nothing drawn was affected): 7 ground cases within -2.3 / +2.1 cm at once and after the freeze, 21 images looked at (`docs/phase2_app.md` 13) |

### 14.4 Results: strict harness, before → after, all seven windows

Cells: 120-s lookahead before → after (60 s: before → after); bold = still above its limit. Gates that are 0 before and after in every
window are not listed. Before = section 13's final engine under this iteration's harness (14.1); after = the committed engine.

| Gate (limit 0) | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|
| `air_accel_samples` | 13 → **13** (13 → 13) | 9 → **8** (9 → 8) | 6 → **6** (6 → 6) | 9 → **9** (9 → 9) | 32 → **27** (28 → 27) | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) |
| `air_climb_samples` | 57 → **58** (57 → 58) | 66 → **66** (66 → 66) | 3 → **3** (3 → 3) | 16 → **16** (16 → 16) | 100 → **100** (103 → 103) | 3 → **3** (3 → 3) | 21 → **21** (21 → 21) |
| `air_float_runway_frames` | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_overspeed_samples` | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) | 1 → **1** (1 → 1) | 1 → **1** (1 → 1) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_substall_samples` | 2 → **2** (2 → 2) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |
| `bank_rock_episodes` | 225 → **3** (226 → 3) | 665 → **6** (664 → 6) | 152 → **2** (152 → 2) | 368 → **3** (368 → 3) | 710 → **25** (717 → 25) | 23 → 0 (23 → 0) | 96 → **2** (98 → 2) |
| `forced_low_bank_frames` | 0 → 0 (0 → 0) | 5 → **15** (5 → 15) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 137 → **151** (137 → 151) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `forced_speed_drop_frames` | 0 → 0 (0 → 0) | 0 → **2** (0 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `fw_in_building_frames` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 55 → **55** (55 → 55) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `grass_route_frames` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 49 → **49** (45 → 45) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_decel_frames` | 30 → **24** (29 → 22) | 68 → **65** (61 → 58) | 15 → **12** (15 → 12) | 52 → **52** (52 → 52) | 85 → **77** (85 → 77) | 0 → 0 (0 → 0) | 15 → **15** (15 → 15) |
| `ground_fast_roll_frames` | 19 → **19** (19 → 19) | 5 → **5** (5 → 5) | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 24 → **24** (24 → 24) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_overlap_frames` | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_stall_frames` | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `handover_rate_frames` | 66 → **63** (64 → 63) | 17 → **15** (19 → 17) | 11 → **11** (11 → 11) | 19 → **21** (19 → 21) | 107 → **55** (71 → 55) | 1 → **1** (1 → 1) | 36 → **35** (36 → 35) |
| `label_flicker` | 6 → **7** (5 → 6) | 20 → **19** (22 → 21) | 4 → **4** (4 → 4) | 19 → **18** (21 → 20) | 32 → **28** (37 → 32) | 0 → 0 (0 → 0) | 4 → **5** (4 → 5) |
| `label_overflight_hwd` | 0 → 0 (59 → 59) | 122 → **122** (173 → 173) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 154 → **154** (235 → 235) | 0 → 0 (0 → 0) | 0 → 0 (58 → 58) |
| `label_roll_flicker` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_takeoff_slow` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 5 → **5** (5 → 5) | 5 → **5** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `liftoff_plateau_frames` | 18 → **18** (18 → 18) | 21 → **21** (21 → 21) | 0 → 0 (0 → 0) | 9 → **9** (9 → 9) | 9 → **8** (8 → 8) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `low_bank_frames` | 20 → **18** (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 10 → **2** (10 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `low_bank_landing_frames` | 0 → 0 (0 → 0) | 10 → **12** (10 → 12) | 0 → 0 (0 → 0) | 15 → **16** (15 → 16) | 40 → **45** (40 → 45) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `low_roll_rate_frames` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `m3_hidden_runway_consistent` | 1 → **1** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `misaligned_transitions` | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `off_pavement_moving_frames` | 15 → **15** (15 → 15) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 55 → **56** (62 → 63) | 0 → 0 (0 → 0) | 15 → **15** (15 → 15) |
| `pitch_phase_samples` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → **1** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `pivot_in_place` | 5 → **5** (6 → 6) | 0 → 0 (2 → 2) | 3 → **3** (3 → 3) | 3 → **3** (3 → 3) | 4 → **3** (2 → 1) | 0 → 0 (0 → 0) | 5 → **5** (5 → 5) |
| `rest_pose_change_frames` | 0 → 0 (1 → 1) | 0 → 0 (14 → 14) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `roll_start_yaw_frames` | 10 → **10** (10 → 10) | 8 → **8** (8 → 8) | 5 → **5** (5 → 5) | 28 → **28** (28 → 28) | 25 → **25** (26 → 26) | 0 → 0 (0 → 0) | 10 → **10** (10 → 10) |
| `roll_turn_samples` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 3 → **6** (3 → 6) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `roll_yaw_rate_frames` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) | 6 → **6** (6 → 6) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `taxi_hole_stop_frames` | 0 → 0 (0 → 0) | 78 → **78** (78 → 78) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `taxi_speed_mismatch_frames` | 18 → **13** (18 → 13) | 19 → **19** (20 → 20) | 4 → **4** (4 → 4) | 2 → **1** (2 → 1) | 27 → **23** (30 → 26) | 1 → **1** (0 → 0) | 13 → **9** (13 → 9) |
| `tg_no_contact` | 3 → **3** (3 → 3) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 5 → **5** (5 → 5) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |

Failed gates per window (heli / pat / night / weekday / weekend / od3s / od3p), 120 s: 17 / 20 / 14 / 22 / 26 / 4 / 12 → 16 / 21 / 14 / 21 / 26 / 3 / 12; 60 s: 18 / 22 / 14 / 22 / 28 / 3 / 13 → 17 / 23 / 14 / 21 / 26 / 2 / 13.

### 14.5 Cases, checked like a pilot (final engine)

- **Case S (light-jet take-off, 28L; G3, G4 label).** Video S scout, every frame: the crosswind turn at 900-1,590 ft rolls in and out
  once - 0 swings of >= 4° within 1.5 s above 200 ft (round 5: 33 in `d-climb-chase`), roll rate <= 15°/s; below 200 ft <= 2.3° of bank at
  <= 2.5°/s. The OD3 trace (`od3_trace.mjs S`, per second) differs from the round-5 one in the bank (G3: up to 11.0° in the climbing turn; 80 rows differ by > 0.05° or 0.05 m) and slightly in the crosswind-turn path (up to 8.8 m), and in the labels *(corrected in round 5 iteration 3, 15.3 G9: this said 'the round-5 one except the labels'; case P's trace differs from round 5 in the bank too, up to 5.8° in 61 rows)*: the SF50 rolls onto 28L at 6-8 kt without
  stopping and now reads Taxiing (provisional) → Taxiing on the runway 28L (provisional) → Take-off roll 28L (provisional) (round 5: 'Lined
  up 28L (provisional)' for 5.8 s while rolling at 7 kt). Ground: drawn speed within 0.54 kt of the shown speed (2-30 kt), braking <= 1.96
  m/s² over 0.3 s; flaps 15° from the hold to 400 ft as before.
- **Case P (single-turboprop landing, 28L; G7, G8).** Touchdown, roll-out and exit unchanged (13.5). Flaps (video P scout, every frame):
  40° through the roll-out and the runway taxi, retracting from the exit (39.6° → 21.3° while taxiing to the hold-short), 20.9° → 5.5°
  through the post-landing hold-short, 5.2° → 0 on the taxi-in, 0 at the stop; the engine's own flap state (OD3 trace) is now the views':
  1 through the runway taxi, retracting from the exit. Largest ground deceleration over 0.3 s: 3.5 m/s² (the planned braking after the last
  roll fix, 13.8).
- **Case J (weekend large-cabin business jet at the hold; G4).** Its type's roll limit is 1.98 m/s² (the MTOW cap of 1.8 m/s², raised to
  the type's own take-off table value); no decision-(e) plan within the limits exists at any rung, so it is hidden with the 1.5-s fade, as
  M3 hides it at 60 s. Round 5 drew a 13-s roll at 4.5 m/s².
- **Cases Q1-Q3 (forced plans of rolling aircraft; G8 (a)).** Not changed: Q3 21-22° at 281-289 ft for ~1.5 s (round 5: 0.5 s), Q1 / Q2 as in
  13.5 with 14 more frames. Q2's forced crosswind turn at 99 kt also rocks 13 ↔ 21° about once a second from 240 to 450 ft (14 of the
  weekend's 25 `bank_rock_episodes`; the section-13 engine 9 ↔ 19°): on a plan the drawn bank is the body's own turn rate smoothed over
  0.4 s, and that rate pulses between < 1 and ~6.8°/s behind the plan's target (the air follower's heading limit cycle).
- **G5 cases.** The weekend trainer of the first final tree (14.3 G5): with the direction rule it follows its target as the section-13
  engine does (0.1-s probe, local). The landing roll released from its 'behind' hold no longer drops 32.6 → 6.4 kt in a frame; it runs
  on past its trail end; a later 0.3-s sample of the same roll still reads 11 m/s² (31.9 → 25.6 kt). The route that starts with a
  turn-round stop still stops the body (12.4 → 5.4 → 0 kt, a standing target).

### 14.6 Corrections of section 13

- 13.3 V1 / 13.5 case P (G7): 'flaps 0° at the post-landing hold-short' read the flap target; the drawn flaps retract through it
  (corrected in place, marked).
- 13.4 / 13.8 (G6): each window's counters are given separately (corrected in place).
- The wing-rock counts of 13.8 (1,609 / 1,591 reversal episodes in the weekend window, 31-33 in video S) were counted with a different,
  local measure; `bank_rock_episodes` (14.2) is the gate now. Values of that gate printed while this iteration's harness was being written
  were invalid (an extremum test that never confirmed the first extremum); every value in 14.3 / 14.4 is of the final harness.

### 14.7 Residuals (not fixed; all measured above)

- **G5:** `ground_decel_frames` 30 / 68 / 15 / 52 / 85 / 0 / 15 → 24 / 65 / 12 / 52 / 77 / 0 / 15 (120 s): 22 target steps (a plan → fix-following or roll → taxi hand-over whose target speed itself jumps,
  e.g. a landing roll handing over from its roll target to fix-following: 38.9 → 20.1 kt in 0.3 s, pat), 15 dead stops at taxi
  speed (8 before: fix-following targets that stop between two fixes, and now also a body that has overrun its trail end and stops dead
  when its target then stops - braking it at G_DEC past the end would remove those), 29 drops of the drawn position's speed alone (corner cuts of the box filter
  at hand-overs), 6 speed drops. `groundJoltKept` counts the clamp's firings that are left (5-35 per window).
- **G3:** `bank_rock_episodes` 225 / 665 / 152 / 368 / 710 / 23 / 96 → 3 / 6 / 2 / 3 / 25 / 0 / 2 (120 s; 60 s in 14.4) - case Q2's forced turn (14.5), the rest single episodes in data turns (fix-following Hermites at
  50-740 ft). `roll_turn_samples` weekend 3 → 6: three data turns where the windowed bank lags the body's turn by more than 8°.
- **G8 (a):** `forced_low_bank_frames` pat 5 → 15, weekend 137 → 151; `forced_speed_drop_frames` pat 0 → 2 (case Q3).
- **Other regressions of this iteration** (120 s): `low_bank_landing_frames` pat 10 → 12, weekday 15 → 16, weekend 40 → 45 (planned
  finals: the same plans and turns, 1-2° more bank behind the smoothed direction); `handover_rate_frames` weekday 19 → 21;
  `label_flicker` heli 6 → 7, od3p 4 → 5; `air_climb_samples` heli 57 → 58; `pitch_phase_samples` weekend 0 → 1;
  `off_pavement_moving_frames` weekend 55 → 56; Not traced further.
- **G9 (regressions against table 12.4, listed in 13.8):** unchanged where this iteration did not touch them (table 14.4 has the current
  values). Still failing as in 12.7 / 13.8: `grass_route_frames`, `fw_in_building_frames`, `air_climb_samples`, `air_accel_samples`,
  `tg_no_contact`, `liftoff_plateau_frames`, `ground_fast_roll_frames`, `label_overflight_hwd`, `taxi_hole_stop_frames`,
  `low_bank_landing_frames`, `air_substall_samples`, `air_overspeed_samples`, `handover_rate_frames`, `roll_start_yaw_frames`,
  `pivot_in_place`, `label_flicker`, `off_pavement_moving_frames`, `taxi_speed_mismatch_frames`.

### 14.8 Other checks, wanted, inferred, not verified

- `python3 -I -B tools/check_airport.py` (all hard checks, with this section in place): ALL HARD CHECKS PASSED; `--d1-windows`: 23 / 23
  planted event-time cases and 29 / 29 type cases right, 0 hits, 15 / 15 app screenshots with `d1_labels` and `d1_clock`.
- `node --check` on every edited JS file: OK. OD3 traces refreshed (local), checked per second (14.5). Video: `docs/phase3_video.md`
  section 17. App: `docs/phase2_app.md` section 13.
- **Wanted:** none new.
- **Inferred, not sourced** [inf]: `BANK_H` 1 s, `BANK_LAG_S` 0.3 s, `BANK_BAND` 8°, the 0.4-s smoothing of the body's own turn and the
  0.6-s shortest window; `G_DEC` 3 m/s², the overrun allowance max(3 m, 0.6 s of travel), the trail-direction rule (0.5 m, or 0.1 m within 20° of the nose), the catch-up rate 0.3 m/s per m
  (>= 0.8 x), the restart distance max(10 m, 3 s of travel); the type roll caps (2.5 / 2.1 / 1.8 m/s² for jets <= 10 t / <= 20 t /
  heavier, 3.0 m/s² for turboprops > 5.7 t: design values, not AFM figures; the MTOW is the FAA ACD's [obs]); the 2.5-m/s 'Lined up' limit;
  the gate limits of 14.2.
- **Not run:** live mode; a real phone; the full videos (the orchestrator's, after OD4's look fixes).

## 15. Fix round 5, iteration 3 - recheck findings G1-G10 (2026-11-27)

The recheck of section 14 left ten findings open (G1-G10: D1 screenshots, ground jolts, wing rock, doc items, world paint, a route stop,
roll labels, harness residuals). This iteration was stopped once (paused for the account usage limit) after the D1 part (G1) and the hold
marking (G6) had been written; its WIP was checkpointed (974d219) and the restart re-verified both, then did the rest. It changed
`js/live/{traffic,motion,markings}.js`, `tools/traffic/replay_engine.mjs`, `tools/check_airport.py`, `docs/phase2/` (two images and
`SOURCES.json`) and the docs (`js/live/aircraft.js`, `ground.js`, `classifier.js`, `parking.js`, the app shell, `js/video/**`,
`tools/video/**` and every OD4-owned file unchanged). Cases keep the names of sections 13 / 14 (window, class, anonymous label).

### 15.1 Method

- **Before** = the final engine of section 14 (`traffic.js` 9437e3c5a1ea, `motion.js` ba446d169cb7) under the final harness of this
  iteration (`replay_engine.mjs` 49cac0e2f9fd, with the gates of 15.2). On every gate that 15.2 does not change it reproduces table 14.4
  cell for cell, in all seven windows at both lookaheads. **After** = `traffic.js` cf1d7dce5631, `motion.js` 255fa1fb9cf6 (the committed
  files). Harness `node tools/traffic/replay_engine.mjs <w> --strict --open app --lookahead 120|60 --log`, 10-Hz frames, frozen copies of the
  trees, deterministic. The machine was shared with another workflow's renders the whole time (load 15-27 on 4 CPUs); every run is nice'd.
- Every engine item was reproduced first on a 10-Hz probe of the case (local scripts in `out/`, not committed: they print types and window
  seconds), then fixed and re-probed. Intermediate trees measured in full and changed or dropped (15.3): a Dubins arc in 1-deg steps (G3:
  it changed which plans fit - `low_bank_frames` pat 0 -> 61); the lateral-first acceleration limit for every target (G3: `air_overspeed_samples`
  weekend 2 -> 10, `off_reports_samples` night 0 -> 2, weekend 0 -> 6, pat `bank_rock_episodes` 6 -> 10); a tangent shared by both intervals at
  an airborne fix (G3: pat `bank_rock_episodes` 6 -> 59, `air_accel_samples` 8 -> 34, `air_overspeed_samples` 3 -> 23); a 'Take-off roll' label
  from the first acceleration of a reconstructed touch-and-go (G8: `label_takeoff_slow` pat 0 -> 34, weekday 5 -> 121); the anticipation
  without the physics offset and without the lift-off rule, and the trail without its re-anchoring (G2: video S's plan gate failed, a pat
  touch-and-go lifted off 15 kt slow - 15.3); the braking behind a touchdown capped at `LIM.rollDec` (G2: `teleports_engine` weekend 0 -> 1).
  The OD3 traces (`node tools/traffic/od3_trace.mjs S|P`) and both video scouts were checked frame by frame on the final tree (15.5,
  `docs/phase3_video.md` section 18).

### 15.2 New and changed gates (harness `r5i3Frame`, all limit 0)

- `ground_decel_frames` (G2, changed): the target's own braking excuses a frame only up to the engine's roll braking limit, `LIM.rollDec`
  3.5 + 0.1 m/s² (it was 6 m/s²: bodies that copied a target braking harder than the engine allows were not counted - INFO
  `ground_decel_plan_frames` weekend 120, weekday 10, od3p 4, heli 2 frames on the section-14 engine).
- `label_roll_backward` (G8): a ground roll from a drawn touchdown (airborne the frame before) until the body is airborne again or slower
  than 7.7 m/s; once 'Take-off roll' has been shown, 'Landing roll' or 'Touch-and-go' again - episodes.
- `route_runway_stop_frames` (G7): on the ground within 4.5 km, the target a taxi route, the drawn speed below 0.5 m/s with the body's centre
  inside a runway's protected zone (nearer its centreline than its runway holding position - the taxigraph hold bars' median, `TaxiNet.holdDist`
  - along it +-30 m past its ends).

### 15.3 Findings: reproduction, cause, change, status

| # | Finding | Reproduced | Cause | Change | Status |
|---|---|---|---|---|---|
| G1 (major, D1) | `phase2_fix1_12` / `phase2_fix2_13`: the HUD clock and runway line were pixelated, but the committed job defaults (`jobs/views.mjs` / `jobs/phone_ui.mjs`: the default replay pack, a committed wait after ready) and the shim's timing still fix both shots' instant in the dated weekend window, with individual aircraft's states in view | the two jobs read: both load `?mode=replay` (the default pack, the weekend window) and wait a committed `WAIT` after ready; the images (looked at) show a card's state rows and labelled aircraft | the clock rule covered only HUD elements derived from elapsed time, not a shot whose instant a committed job fixes | (restart: verified, unchanged) both JPEGs re-masked with Pillow from the committed JPEGs: the 3-D view (aircraft positions and every label), the card's state rows (phase, parking, traffic, altitude, speed, data age) and the list / tab counts and phase / runway lines are blanked; what they document stays (the card header and type-only rows, the wrapped view row, the pills, the credit line, the sheet's tabs). Looked at again on the restart, the strip of the 3-D view left behind the top bar enlarged 3x: ground and pavement only, no aircraft or label. `tools/check_airport.py` `_d1_job_clocked`: a SOURCES entry whose committed livetest job loads a recorded pack (`mode=replay` / `snapshot`) and waits a committed default before its shots counts as clocked; its `d1_clock` must say `job-clocked` and that every aircraft state is masked (or that none is shown) - hard, with 5 planted entries | **fixed**: 2 job-clocked screenshots, both reviewed; planted entries 5 / 5 right |
| G2 (major) | Ground speed steps of 10-23 kt in 0.1-0.3 s at landing-roll hand-overs and dead stops from taxi speed in every window but od3s; the gate excused bodies copying a target braking up to 6 m/s² | the recheck's 10-Hz probe reproduced exactly on the frozen section-14 tree (weekend 18 episodes, pat 9, heli 6, weekday 8, night 1, od3p 4, od3s 0; worst 35.9 -> 18.0 kt, 38.9 -> 20.1 kt); per-frame debug of the cases (local) | the body followed its target's CURRENT speed and position only: where the target stopped or slowed abruptly ahead (a fix-following run handing over to a route that starts by turning round, a planned landing roll handing over to the fixes at half its speed, a Hermite stopping between two fixes) the body reached the trail end at its old speed and was clamped to it; a fix-to-fix Hermite's speed FIELD (the reported speed at its first fix) also disagreed with its positions (31 kt against 40-45 kt), and the body braked to the field; behind a landing roll the body copied its target's braking + 0.2 m/s² | (a) **anticipation** (`traffic.js` `groundAhead`): a moving ground body samples its target 0.3-8 s ahead (up to its braking time + 1.5 s) along the target's own path and limits its speed so it can brake - at `G_DEC` 3 m/s² on a roll, `LIM.taxiDec` 2 m/s² taxiing - to every speed the target will have, by the point where the target has it (the speed there is the target's path speed, the secant between samples; a target that turns back stops first); without side effects (no instant past the newest fix, no take-off / landing transition or airborne interval, the rest pose / raw position / reconstruction restored, a late-join plan built by the samples dropped with its cache entries; the samples carry the body's current physics offset, `tr.physOff`, as its target does; a target that lifts off within the horizon is not braked for); (b) the body takes the target's PATH speed over the next 0.3 s where the speed field disagrees by > 0.5 m/s; (c) a body still faster than the creep when its target stops brakes along its own braking curve; (d) behind a touchdown a body ahead of or faster than its target brakes as hard as the target and no harder (the target's braking + 0.1 m/s², was + 0.2; up to 5 m/s²) - capping it at `LIM.rollDec` was tried and dropped: a large business jet rolled 17 m ahead of its planned landing roll braking at 3.7 m/s², into the plan's back-taxi turn, stopped there and pivoted while its target ran on, and was cut 155 m away (`teleports_engine` weekend 0 -> 1), the round-4 case this rule was made for; (e) the run past the trail end (round 5 iteration 2) also from 0.3 m/s while the target moves; (f) a body that has run past its trail end is anchored where it is before the target's next point is laid (the trail used to bend from its old end and the body's place on it jumped sideways); (g) gate exemption narrowed to <= 3.6 m/s². Two intermediate trees of this iteration were corrected after the video S plan's hero-motion gate failed on the first (the hero leaving the FBO: 7.9 kt behind a 5.2-kt route target - a 0.4-m physics offset read as 1.2 m/s of extra path speed - ran past its trail end at a corner and jumped 0.27 m sideways in one frame) and a pat probe showed a light single's touch-and-go braked in advance to the 33-kt hand-over speed and lifted off 15 kt slow: (a)'s offset and lift-off rules and (f) | **partly fixed**: `ground_decel_frames` 25 / 65 / 12 / 62 / 196 / 0 / 18 -> 6 / 41 / 11 / 39 / 98 / 0 / 5 (120 s; heli / pat / night / weekday / weekend / od3s / od3p); the recheck's probe (speed drops > 3.6 m/s² over 0.3 s, 120 s) 6 / 9 / 1 / 8 / 18 / 0 / 4 -> 1 / 2 / 0 / 3 / 5 / 0 / 1 episodes, the worst left a 13.8-kt stop at the start of a planned back-taxi turn (15.7 (e)); the left-overs: 15.7 |
| G3 (major) | Wing rock left in one forced climb-out (14 of the weekend's 25 `bank_rock_episodes`) and in fix-following data turns | 10-Hz air probes (local) of the forced climb-out and of a pat data turn: the forced plan's TARGET turned 1.3 -> 4.3 -> 5.5 -> 1.3 deg/s about once a second; the body 55-100 m behind it turned 0.6 <-> 6.0 deg/s frame by frame; in the data turn the target's direction jumped 25° in one frame at a fix | (1) `retimePath` resampled a Dubins arc drawn in 5-deg chords (66 m at 760 m radius) at 96 instants: resampled segments that straddled a chord vertex turned and the others did not; (2) the air follower scaled its acceleration as one vector: a large along-track error (a forced climb-out may not close its gap, `TO_OVER_V`) starved the turn, then the 'turning at its limit' rule gave the full turn for a frame - a limit cycle; (3) a fix-following Hermite chose its tangent per interval (the reported velocity where it agreed with THAT interval's chord, else the chord): a fix whose report agreed with one chord but not the other got two tangents and the target's direction jumped there | (1) `retimePath` re-times a path that can be evaluated along its own arc length (`motion.js` `turnFlight` / `straightHermite` `atS`) along it, not along the resampled polyline - the plan validators keep reading `atRaw`, so no plan choice changes (tried first and dropped: the Dubins arc in 1-deg steps - it changed which plans fit, `low_bank_frames` pat 0 -> 61); (2) behind a reconstructed plan (x/plan modes) the limit keeps the lateral part first and gives the along-track part the rest (tried for every target and dropped: `air_overspeed_samples` weekend 2 -> 10, `off_reports_samples` night 0 -> 2, weekend 0 -> 6, pat `bank_rock_episodes` 6 -> 10); (3) not changed: a tangent shared by both intervals at a fix (the report where it agrees with every chord around the fix, else the mean of the chords) was tried and dropped - it moved every fix-following air path (pat `bank_rock_episodes` 6 -> 59, `air_accel_samples` 8 -> 34, `air_overspeed_samples` 3 -> 23) | **partly fixed**: the forced climb-out turns evenly (15.5: bank 17.9-19.1°, was 13.3-25.5°); `bank_rock_episodes` weekend 25 -> 11, weekday 3 -> 2, the other windows unchanged (heli 3, pat 6, night 2, od3s 0, od3p 2); the data-turn rock is left (15.7) |
| G4 (minor, D1) | 14.3's G6 row repeated the window join it was meant to remove and said why it dates a case | text | the row described the effect instead of the change | the row now says only that two windows' counters were reported as one; no window is named with another and nothing dates a case (corrected in round 5 iteration 3 before the pause; re-read on the restart) | **fixed** in the tree; the pushed history is the owner's (G5) |
| G5 (minor, D1) | 14.3 G1 / G2 named the history only partly: the pushed tip of the recheck (5f98e52) also held the two real offsets as plants and the unmasked '(last N min)' screenshots | `git show <c>:hwd3d/tools/check_airport.py`: 3 `% 16)` / `% 33)` plants each in 9085b5d, bab65be and 5f98e52; the G2 / G1 images there are the unmasked ones (89,642 / 99,933 bytes for the two job-clocked JPEGs) | the statement was written while 5f98e52 was the tip | 14.3 G1 names 9085b5d, bab65be and 5f98e52; the owner question (15.9) lists every pushed commit with D1 material. The WIP checkpoint 974d219 (pushed after the recheck) holds none of it: 0 plants, the masked JPEGs (62,768 / 41,877 bytes) | **fixed** (statement); rewriting the pushed history is the owner's decision |
| G6 (minor, world paint) | Hold A1 (and Z1) near the 28L end drawn reversed: an aircraft holding there faced the dashed lines (video S's hold) | abs(`n . toRw`) computed from `data/hwd_airport.json`: 0.02 (A1) and 0.00 (Z1), every other hold 0.81-1.00; a local check of every hold bar (solid -> dashed vector) on the old and new `markings.js` | `markings.js` chose the holding side by the direction to the runway CENTRELINE, which is degenerate for a hold on a taxiway parallel to the runway | below 0.3 the runway side is the way's own direction toward the runway rectangle: walked along the way from the bar both ways in 1-m steps (<= 250 m), the direction that enters a runway rectangle first, else the one that comes closest (`holdWayToRunway`); the inventory notes it (2 holds) | **fixed**: A1 and Z1 flipped (solid lines now on the side away from the 28L entry, dashed toward it), the other 21 unchanged; app still: 15.5 |
| G7 (minor) | Video P / case P: after the post-landing hold the PC-12 crossed 28R and slowed from 8.9 to 0.6 kt at the far runway edge on an inferred route, then accelerated again | OD3 P trace (local, iteration-2 tree), per second at the 28R edge: 8.9 -> 5.4 -> 2.3 -> 0.8 -> 2.2 -> 4.1 kt; a debug print of the route profile: hole 49.1 s, route 196 m, start 0.57 m/s, end 6.3 m/s, at the 4.5-m/s typical cruise 46.9 s | `motion.js` `profilePath` put a route's spare time into ONE stop at the slowest point of the path (here the corner where the straight crossing rejoins the taxiway, on the runway's edge) whenever the cruise at the typical speed was still too fast; 'start at rest' meant < 0.5 m/s, so a start at 0.57 m/s got an interior stop (with no dwell left: a slow-down to ~0) | the spare time is spread over the whole path first: unless the path starts or ends at rest (< 0.5 m/s - a wait there, as before), the cruise goes on down to `TAXI_SLOW` 2.0 m/s (3.9 kt) before a stop is put in (bisection between that and the typical speed); a stop that is still needed is never put on a runway or between a runway and its holding position + half the aircraft's length (`stopOk`, `traffic.js` `rwyZone`: the taxigraph hold bars' median distance per runway) - else at the slowest allowed point | **fixed**: case P crosses 28R and taxis on at 8.2 kt (6.0-6.9 kt through the two corners after the crossing; OD3 P trace; video P: 15.5); gate `route_runway_stop_frames` (15.2) 9 / 122 / 0 / 6 / 5 / 0 / 8 -> 2 / 0 / 0 / 0 / 0 / 0 / 2 - the 2 left (heli 2, od3p 2) are routes that run along a runway their whole length (15.7) |
| G8 (minor) | Reconstructed touch-and-go rolls flipped their label: 'Take-off roll' at the touchdown, 'Landing roll', 'Take-off roll' | probe label sequences on `xplan:landing:roll` touchdowns (local): weekend 4, pat 4, weekday 1 such rolls with a label going back | the fix labels around the hole (the classifier's take-off roll / touch-and-go) and the plan phase (landing roll) were used by turns: `drawnPhase0` applies the plan phase only where the fix label is not a runway event | `traffic.js` `displayPhase`: the roll of a reconstructed landing (an x/plan landing roll) whose following fixes take off again (an airborne fix, or one labelled take-off roll / touch-and-go, before the roll slows to taxi speed) is labelled 'Touch-and-go' from the touchdown to the lift-off - the classifier's own label for the episode; a reconstructed roll that does not take off again is a landing roll, and once 'Take-off roll' has been shown it stays. (A first version labelled 'Take-off roll' from the first acceleration on; a take-off plan that joins the roll slowed down again on the runway, and 'Take-off roll' was shown at 22 kt while braking: `label_takeoff_slow` pat 0 -> 34, weekday 5 -> 121 - dropped.) Gate `label_roll_backward` (15.2) | **fixed** for reconstructed rolls: `label_roll_backward` 3 / 7 / 0 / 4 / 7 / 0 / 3 -> 2 / 0 / 0 / 0 / 1 / 0 / 2; the five left are not reconstructed touch-and-gos (15.7) |
| G9 (minor, docs) | 14.5 said case S's OD3 trace was the round-5 one except the labels; 13.3 V1, 13.5, 14.3 G7, `docs/phase2_app.md` 12 and `docs/phase3_video.md` 16 put video P's flaps up from frame ~2185; section 13 numbered the recheck's findings R1-R10 | the recheck's traces and the iteration-2 scout (local) | written from memory of an earlier trace / scout | corrected in place, each correction marked; 15.6 lists them | **fixed** |
| G10 (minor, QA) | The strict harness still fails in every window; rises of `off_pavement_moving_frames` (13.4: heli 9 -> 15, od3p 11 -> 15) and `pivot_in_place` (13.4: night 2 -> 3, weekday 1 -> 3, weekend 1 -> 4, od3p 3 -> 5) not traced | the harness's per-frame log lines of the section-12 and section-14 engines (local), 10-Hz probes | (traced) `off_pavement_moving_frames`: in heli one episode, in od3p one episode - a fix-following taxi past a corner with one main wheel over the pavement edge, 0.6-1 s longer than before round 5 (the round-5 smoothed fix-following taxi takes the corner on a slightly wider line); `pivot_in_place`: the new entries are 30-32° turns with 0.3-0.5 m of movement (the gate's limits: 30° within < 0.5 m) at walking speed - taxi starts in smoothed fix-following taxi (`gg:taxi`), on routes and at holds (rest, `gg:lin` hold-short) | not changed (no engine fault: both are at the gates' thresholds); the residuals per gate are in 15.7 | **traced**, open |

### 15.4 Results: strict harness, before → after, all seven windows

Cells: 120-s lookahead before → after (60 s: before → after); bold = still above its limit. Gates that are 0 before and after in every
window are not listed. Before = section 14's final engine under this iteration's harness (15.1); after = the committed engine.

| Gate (limit 0) | heli | pat | night | weekday | weekend | od3s | od3p |
|---|---|---|---|---|---|---|---|
| `air_accel_samples` | 13 → **13** (13 → 13) | 8 → **8** (8 → 8) | 6 → **6** (6 → 6) | 9 → **9** (9 → 9) | 27 → **27** (27 → 27) | 0 → 0 (0 → 0) | 3 → **4** (3 → 4) |
| `air_climb_samples` | 58 → **57** (58 → 57) | 66 → **66** (66 → 66) | 3 → **3** (3 → 3) | 16 → **16** (16 → 16) | 100 → **101** (103 → 104) | 3 → **3** (3 → 3) | 21 → **20** (21 → 20) |
| `air_float_runway_frames` | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_overspeed_samples` | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) | 1 → **1** (1 → 1) | 1 → **1** (1 → 1) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `air_substall_samples` | 2 → **2** (2 → 2) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 2 → **2** (2 → 2) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |
| `bank_rock_episodes` | 3 → **3** (3 → 3) | 6 → **6** (6 → 6) | 2 → **2** (2 → 2) | 3 → **2** (3 → 2) | 25 → **11** (25 → 11) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) |
| `forced_low_bank_frames` | 0 → 0 (0 → 0) | 15 → **13** (15 → 13) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 151 → **120** (151 → 120) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `forced_speed_drop_frames` | 0 → 0 (0 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `fw_in_building_frames` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 55 → **53** (55 → 53) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `grass_route_frames` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 49 → **47** (45 → 43) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_decel_frames` (changed, 15.2) | 25 → **6** (23 → 6) | 65 → **41** (58 → 36) | 12 → **11** (12 → 11) | 62 → **39** (62 → 39) | 196 → **98** (196 → 98) | 0 → 0 (0 → 0) | 18 → **5** (18 → 5) |
| `ground_fast_roll_frames` | 19 → **19** (19 → 19) | 5 → **5** (5 → 5) | 0 → 0 (0 → 0) | 4 → **4** (4 → 4) | 24 → **24** (24 → 24) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `ground_overlap_frames` | 0 → 0 (0 → 0) | 1 → 0 (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `handover_rate_frames` | 63 → **64** (63 → 64) | 15 → **15** (17 → 17) | 11 → **11** (11 → 11) | 21 → **20** (21 → 20) | 55 → **59** (55 → 59) | 1 → 0 (1 → 0) | 35 → **35** (35 → 35) |
| `label_flicker` | 7 → **7** (6 → 7) | 19 → **18** (21 → 20) | 4 → **3** (4 → 3) | 18 → **9** (20 → 12) | 28 → **26** (32 → 25) | 0 → 0 (0 → 0) | 5 → **4** (5 → 4) |
| `label_overflight_hwd` | 0 → 0 (59 → 59) | 122 → **122** (173 → 173) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 154 → **154** (235 → 235) | 0 → 0 (0 → 0) | 0 → 0 (58 → 58) |
| `label_roll_backward` (new) | 3 → **2** (2 → 2) | 7 → 0 (8 → 1) | 0 → 0 (0 → 0) | 4 → 0 (3 → 2) | 7 → **1** (7 → 2) | 0 → 0 (0 → 0) | 3 → **2** (2 → 2) |
| `label_roll_flicker` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → 0 (1 → 0) | 1 → 0 (1 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `label_takeoff_slow` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 5 → 0 (5 → 2) | 5 → **5** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `liftoff_plateau_frames` | 18 → **18** (18 → 18) | 21 → **21** (21 → 21) | 0 → 0 (0 → 0) | 9 → **9** (9 → 9) | 8 → **8** (8 → 8) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `low_bank_frames` | 18 → **18** (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 2 → 0 (2 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `low_bank_landing_frames` | 0 → 0 (0 → 0) | 12 → **12** (12 → 12) | 0 → 0 (0 → 0) | 16 → **16** (16 → 16) | 45 → **45** (45 → 45) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `m3_hidden_runway_consistent` | 1 → **1** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `misaligned_transitions` | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `off_pavement_moving_frames` | 15 → **15** (15 → 15) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 0 → 0 (0 → 0) | 56 → **85** (63 → 86) | 0 → 0 (0 → 0) | 15 → **15** (15 → 15) |
| `pitch_phase_samples` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 1 → **1** (2 → 2) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `pivot_in_place` | 5 → **4** (6 → 5) | 0 → **1** (2 → 3) | 3 → **2** (3 → 2) | 3 → **2** (3 → 2) | 3 → **3** (1 → 3) | 0 → 0 (0 → 0) | 5 → **2** (5 → 2) |
| `rest_pose_change_frames` | 0 → 0 (1 → 1) | 0 → 0 (14 → 16) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → **1** (0 → 1) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `roll_start_yaw_frames` | 10 → **10** (10 → 10) | 8 → **8** (8 → 8) | 5 → **5** (5 → 5) | 28 → **28** (28 → 28) | 25 → **25** (26 → 26) | 0 → 0 (0 → 0) | 10 → **10** (10 → 10) |
| `roll_turn_samples` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) | 6 → **7** (6 → 7) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `roll_yaw_rate_frames` | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 3 → **3** (3 → 3) | 6 → **6** (6 → 6) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `route_runway_stop_frames` (new) | 9 → **2** (9 → 2) | 122 → 0 (122 → 0) | 0 → 0 (0 → 0) | 6 → 0 (6 → 0) | 5 → 0 (5 → 0) | 0 → 0 (0 → 0) | 8 → **2** (8 → 2) |
| `taxi_hole_stop_frames` | 0 → 0 (0 → 0) | 78 → 0 (78 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) | 0 → 0 (0 → 0) |
| `taxi_speed_mismatch_frames` | 13 → **9** (13 → 9) | 19 → **32** (20 → 33) | 4 → **8** (4 → 8) | 1 → 0 (1 → 0) | 23 → **11** (26 → 14) | 1 → **1** (0 → 0) | 9 → **9** (9 → 9) |
| `tg_no_contact` | 3 → **3** (3 → 3) | 4 → **4** (4 → 4) | 0 → 0 (0 → 0) | 2 → **2** (2 → 2) | 5 → **5** (5 → 5) | 0 → 0 (0 → 0) | 1 → **1** (1 → 1) |

Failed gates per window (heli / pat / night / weekday / weekend / od3s / od3p), 120 s: 18 / 23 / 14 / 23 / 28 / 3 / 14 → 18 / 19 / 14 / 18
/ 26 / 2 / 14; 60 s: 19 / 25 / 14 / 23 / 28 / 2 / 15 → 19 / 22 / 14 / 20 / 26 / 1 / 15. (The before counts include the two new gates; on
the section-14 engine they fail in five windows each. `teleports_engine` and every other gate not listed: 0 before and after.)

### 15.5 Cases, checked like a pilot (final engine)

- **Case S (light-jet take-off, 28L).** The OD3 trace (`od3_trace.mjs S`, per second) is the iteration-2 one: 0 rows differ by > 0.05° of
  bank or 0.05 m (largest 0.03 m), the same labels, the same checks (lift-off 550 m along 28L at 85 kt, 8.4° pitch). Video S's scout (every
  frame, final snapshot): the plan's shot reports equal section 17's, 0 wing-rock swings, roll rate <= 15°/s above 200 ft and <= 2.4°/s
  below, no ground position step off the drawn speed but the timeline's two cuts, the shown speed's largest drop 2.1 m/s² over 0.3 s (the
  slow-down on 28L before the roll - the same on the section-14 engine, local probe of the video pack).
- **Case P (turboprop landing, 28L; G7).** The OD3 trace: the landing, the roll-out, the exit and the post-landing hold-short as in
  iteration 2 (the same labels: Final 28L -> Landing roll 28L -> Taxiing on the runway 28L -> Taxiing -> Holding short -> Taxiing -> Stopped);
  then the crossing of 28R on the inferred route no longer stops at the far edge: from the hold it accelerates to 8.0-8.3 kt, slows to
  6.8-6.9 kt through the corner onto the crossing and 6.0-6.1 kt through the corner after it, and taxis on at 8.2 kt (iteration 2: 8.9 ->
  5.4 -> 2.3 -> 0.8 -> 2.2 -> 4.1 kt at the far edge). Only the taxi after the hold differs from iteration 2 (and the landing roll by
  <= 0.4 kt / 6 cm); no bank differs. Video P's scout: from the post-landing hold-short the PC-12 taxis across 28R and on at 5.9-12.4 kt
  (5.9 kt at frame 2222, the corner after the crossing; iteration 2: 0.6 kt at the far edge), the drawn flaps up (< 0.05°) from frame 2166 as
  in iteration 2, 0 wing-rock swings, the roll-out's largest drop 3.2 m/s² over 0.3 s.
- **Weekend, forced climb-out of a light single (G3).** 10-Hz probe (local): the forced plan's target turns at a constant 3.70 °/s
  through the climbing turn (section-14 engine: 1.2-5.5 °/s, changing about once a second), the body at 3.4-3.9 °/s (0.2-6.8), the bank
  steady at 17.9-19.1° (13.3-25.5°).
- **Pat window, a data turn (G3 residual).** The fix-following target's direction still jumps 25° in one frame at a fix whose reported
  velocity agrees with one chord and not the other; the body rocks once there (15.7).
- **Reconstructed touch-and-goes (G8).** Weekend, pat and weekday rolls that went 'Take-off roll' -> 'Landing roll' -> 'Take-off roll' read
  'Touch-and-go' from the touchdown to the lift-off (`label_roll_backward` pat 7 -> 0, weekday 4 -> 0; the five left in heli, od3p and
  weekend are not touch-and-gos, 15.7).
- **Hold A1 (G6).** The app (`livetest.mjs`, snapshot mode, video S's pack at its hold; local, not committed): the SF50 holding short faces
  the two solid lines, the dashed lines are beyond them on the runway side; looked at from ahead of the aircraft and from its quarter.

### 15.6 Corrections of sections 13 and 14 (G9)

- 14.5 case S: 'the OD3 trace is the round-5 one except the labels' was wrong - it differed from the round-5 trace in the bank (G3: up to
  11.0° in the climbing turn; 80 rows differ by > 0.05° or 0.05 m), slightly in the crosswind-turn path (up to 8.8 m) and in the labels;
  case P's trace differed in the bank too (up to 5.8°, 61 rows). Measured on the two traces of the recheck (local); corrected in place.
- 13.3 V1, 13.5, 14.3 G7, `docs/phase2_app.md` 12 and `docs/phase3_video.md` 16: video P's drawn flaps were up (< 0.05°) from frame 2166
  of the iteration-2 scout, not ~2185 (read on that scout's trace: 20.9° at 2109, 5.2° at 2152, 0.4° at 2165, 0.03° at 2166; the same on
  this iteration's scout); corrected in place.
- Section 13 numbered the recheck's last two findings R9 / R10; that recheck had nine (R1-R9): the light-single correction is R8 and the
  strict residuals R9 (13 heading and intro, 13.3 V7, 12 intro / 12.8 R8). Corrected in place.

### 15.7 Residuals (not fixed; all measured above)

- **G2, `ground_decel_frames`** 6 / 41 / 11 / 39 / 98 / 0 / 5 (120 s). By kind (the harness's log lines, local): (a) a planned landing roll
  that brakes harder than `LIM.rollDec` and the body that follows it as hard (weekend, a large business jet's roll-out at 3.8 m/s², ~70
  frames; the body copying a touchdown hand-over's target braking at 3.7-4.0 m/s² in heli / od3p and weekend) - the plan's roll-out rate is
  the plan's (not changed here); (b) the gate's position term alone at taxi speeds (the drawn position's speed along the heading falling
  3.6-10 m/s² over 0.3 s while the shown speed falls < 3 m/s²: heli, pat, night, weekday, weekend); (c) targets that step by themselves
  (weekday: reconstructed touch-and-go / landing rolls whose target brakes at 5-9 m/s²; weekend: a reconstructed touch-and-go whose target
  steps at 29.5 m/s² and a fix-following one braking at 5.1 m/s²; pat: a touch-and-go whose roll hands over to the fixes 22 kt slower just
  before they climb away - the anticipation does not brake for a target that lifts off within its horizon); (d) a fix-following touchdown
  1.7 m behind its target and 6 kt faster, clamped to its trail end (pat, 57.5 -> 54.8 kt in 0.1 s; unchanged from section 14); (e)
  **new**: the large business jet of (a), now 1-3 m behind its planned landing roll (6-7 m on the section-14 engine), is released from the
  touchdown hold when the plan turns for its back-taxi with the target beside it, and the trail-follower holds its speed down for the
  misalignment: 13.8 -> 0.2 kt in 0.4 s, a pivot, then 36 m behind its target, caught up within ~35 s (no cut). The recheck's probe finds
  12 episodes left (46 on the section-14 engine): 4 of kind (a), 6 of (c), 1 of (d), 1 of (e).
- **G3, the data-turn rock** (`bank_rock_episodes` 3 / 6 / 2 / 2 / 11 / 0 / 2): a fix-following Hermite still takes its tangent per
  interval, and where a fix's reported velocity agrees with one chord and not the other the target's direction jumps at the fix (pat: 25°
  in one frame); the body rolls in and back once. The shared tangent that removes it moved every fix-following air path and was dropped
  (15.3 G3). The weekend's 11 are all fix-following air paths (`aa:herm` 10, `aa:geo` 1; 8 of them light singles in pattern work); the
  forced climb-out's 14 are gone.
- **G7, a route along a runway** (`route_runway_stop_frames` heli 2, od3p 2): a route that runs along 10R/28L its
  whole length has no point where a stop is allowed; it crawls at 0.7-1.6 kt with its spare time (2 frames below 1 kt). **G8**: the five
  `label_roll_backward` left (heli 2, weekend 1, od3p 2) are a fix-following roll at 82 kt (the
  classifier's take-off roll then landing roll) and the exit profiles of three reconstructed landings at 48-56 kt (heli, od3p, weekend) -
  not touch-and-goes; the G8 rule covers the reconstructed roll itself.
- **Rises in this iteration** (120 s): `taxi_speed_mismatch_frames` pat 19 -> 32, night 4 -> 8 - four new short episodes, each a slow, tight
  turn (a route corner at 2-3 kt where the section-14 engine stopped and pivoted - G7 spreads the time; a body that now arrives at its
  target's turn-round point at 5 kt instead of stopping dead there - G2) where the box-filtered place on the trail cuts the corner and the
  drawn motion falls 1.4-2.2 kt below the shown speed for 0.5-1 s (weekend 23 -> 11); `off_pavement_moving_frames` weekend 56 -> 85 - one
  episode, a business jet holding short that pivots at its rest pose with one main wheel over the taxiway edge, the same aircraft and place
  as on the section-14 engine and 3 s longer (timing: it arrives at its hold at a different instant); `pivot_in_place` pat 0 -> 1 (30°,
  0.17 m - at the gate's threshold); `rest_pose_change_frames` weekend 0 -> 1 (4 cm); `roll_turn_samples` weekend 6 -> 7;
  `handover_rate_frames` heli 63 -> 64, weekend 55 -> 59; `air_accel_samples` od3p 3 -> 4; `air_climb_samples` weekend 100 -> 101. The
  60-s lookahead has the same rises and `rest_pose_change_frames` pat 14 -> 16, `pivot_in_place` pat 2 -> 3, weekend 1 -> 3, `label_flicker`
  heli 6 -> 7 (not traced one by one).
- **G10 and the rest of the strict harness**: every window still fails (15.4); the traced rises of 13.4 are in 15.3 G10.

### 15.8 Other checks, wanted, inferred, not verified

- **Inferred constants added** (all [inf], chosen on the probes of 15.3, not from a source): the anticipation horizon `GA_TAUS` 0.3, 0.6, 1,
  1.5, 2, 2.5, 3, 4, 5, 6, 8 s up to `GA_H_MAX` 8 s and the body's braking time + 1.5 s, the stop margin `GA_M` 0.3 m, the braking used to plan
  it (`G_DEC` 3 m/s² on a roll, `LIM.taxiDec` 2 m/s² taxiing - the engine's own limits), a target that 'turns back' (the next sample's
  direction < -0.5 against the previous one), the 0.5-m/s disagreement between the speed field and the path speed, the run past the trail end
  from 0.3 m/s while the target moves, the braking behind a touchdown at the target's + 0.1 m/s² (<= 5 m/s²); `TAXI_SLOW` 2.0 m/s (3.9 kt) as
  the slowest spread cruise of an inferred route; the runway zone of a route stop (the hold bars' median distance per runway + half the
  aircraft's length, +-60 m past the runway ends); the touch-and-go label's 90-s look at the following fixes and its 7.7-m/s (15-kt) end of
  the episode; the lateral-first acceleration limit only behind an x/plan target.
- **Checked:** `python3 -I -B tools/check_airport.py` (full, after these docs were written) passes every hard check; `--d1-windows` alone,
  the same; `node --check` on every changed module; the committed tree names no type of 15.3's local probes next to a dated window
  (decision (d); the check's own D1(d) scan); a local probe of ground position steps (a drawn step in 0.1 s more than 0.15 m off the drawn
  speed, both frames on the ground): 43 frames on the section-14 engine, 37 on the final one, the largest 1.49 m in both (od3s, the same
  frames) - not traced one by one.
- **Video** (`docs/phase3_video.md` section 18): both snapshots refreshed to the final engine, re-scouted and re-planned - all gates pass, no
  override; determinism (6 / 6 frames identical per case) and spot stills looked at. **App** (`livetest.mjs`, 4 cases on the final tree,
  local): `docs/phase2_app.md` 14.
- **Not run:** live mode; a real phone; the full videos (the orchestrator's, after OD4's look fixes).
- **Wanted:** a fix-following tangent that does not jump at a fix and does not move every air path (G3 residual); a release from a
  touchdown hold that follows a target turning away beside the body (15.7 (e)); a strict-harness gate for a body's position step on the
  ground (the video plan's hero-motion gate caught 15.3 G2's first intermediate tree; the strict harness has none for every body).

### 15.9 Owner question (G5): the pushed history

The working tree holds no D1 material (`tools/check_airport.py` hard checks, 15.8), but commits already pushed on `claude/hwd-live-3d` do:
- **Clock times of individual aircraft's events** in the docs of 9672e31, f4b9c59 and 7306714 (removed in round 5, section 13; 8
  clock-time-like strings in each against 2 benign ones);
- **two real offsets as planted cases** of the D1 event-time check in `tools/check_airport.py` of 9085b5d, bab65be and 5f98e52 (3 plants
  each; replaced by synthetic ones in round 5 iteration 2, 14.3 G1);
- **unmasked app screenshots** (`docs/phase2/`) in the commits up to 5f98e52: the elapsed-time HUD elements ('(last N min)', 14.3 G2) and
  the two job-clocked shots whose committed job fixes their instant in a dated window (15.3 G1: 89,642 / 99,933 bytes there, the masked
  ones 62,768 / 41,877).

The WIP checkpoint 974d219 holds none of it. Removing it from the pushed history needs a rewrite of the branch (and a force-push), which
changes every later commit's hash and is the owner's decision; nothing was rewritten.
