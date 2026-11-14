# Phase 2 — P4 app shell, UI, harness, integration

Written 2026-11-13 by P4. Contract: `docs/phase2_fork_map.md` §2.10 (and §2.1–2.9 for what P4 consumes). P4 forked
sfo3d's live page, entry, app, UI, controls, about, ATC, stats and the test harness, and integrated P2's world and P3's
traffic through their contracts. P4 edits only its own files (FILE OWNERSHIP in the brief); where a contract was broken,
the problem is written up in §5 "Integration issues" and worked around in P4 files only. Nothing in `sfo3d/` or `pc12/`
was changed and nothing was committed.

Labels: **[obs]** measured/read here; **[inf]** a design choice.

## 1. Files (all P4-owned)

| File | What it is |
|---|---|
| `live.html` | Forked from sfo3d/live.html. The page: `#app`, `live.css`, the `js/live/entry.js` module. No Google Fonts (system font stack: works offline and in a sandboxed artifact, sends no third-party request). No three.js import map (hwd3d forks the `live.html` path only, fork map §0). |
| `live.css` | Forked from sfo3d/live.css. The dark glass HUD, the desktop side panel / phone bottom sheet, the card and popovers. Changed: the category colours of P3's `category()` (hwd_air blue, hwd_ground green, heli violet, overflight grey, vehicle amber), five list tabs, two panel status lines, the `inf` / `obs` / `type only` tags, the ATC pill tower state, the About sheet as a bottom sheet on phones. |
| `js/live/entry.js` | Mode select, relay detection (`api/ping` → `{hwdlive:1}`), the in-page replay shim (P1), the snapshot pack loader, the taxi graph, `startApp`. Sets `window.__hwdReady` / `__hwdError`. |
| `js/live/app.js` | Boot, render loop, the three feeds (live / replay / snapshot), the environment glue, the five named views, picking, the clocks, the UI glue, `window.HWD` + `HWD.qa`. |
| `js/live/controls.js` | `CameraRig`: touch orbit/pan/zoom/tilt, follow/chase, the tower eye, retuned near/split/far for a 2-km field (ground height from `site.groundY`). |
| `js/live/ui.js` | The DOM UI: top bar, view buttons, flight panel (tabs, phase line, runway line, search), the detail card (D1: names from `tr.ident` only; opaque ids, never a key), 3-D labels, the About / statistics / ATC sheets. |
| `js/live/about.js` | The About panel and the footer credit line; `NOTICES` is the ATTRIBUTION "Notices to show in the app" block verbatim, plus adsb.fi / weather / NAIP / LiveATC lines. |
| `js/live/atc.js` | The ATC link-out (D2): the LiveATC KHWD search link, the tower state at the scene time, tower hours, the NASR frequency table. No embedded audio, no synthetic voice. |
| `js/live/stats.js` | Airfield statistics from P3's `TrafficEvent`s at display time: movements per runway end, touch-and-goes and the circuit interval, helicopters, tower-closed operations; the phase-count status line. |
| `livetest.mjs` | The harness: a static server (never serving `refs/cache/local`), P1's relay spawned in replay mode on a free port 8700–8799 (or an external relay, or a pack-backed mock, or none → the app's shim fallback), headless Chromium, console-error capture, screenshots to `out/phase2/app_*.png`. |
| `jobs/views.mjs`, `smoke.mjs`, `relaycheck.mjs` | The QA jobs (named views + card + sheets; a quick smoke; the end-to-end relay check). |
| `package.json` | Playwright only (no three, no esbuild). |

## 2. Modes

- **live** — the relay's merged stream (`StreamFeed`, SSE deltas). The display delay starts from the relay's poll period
  (`ping.poll.adsblol_s`, ≥ 6.5 s, or 2 s with adsb.fi) and adapts to the report ages. METAR every 60 s.
- **replay** — the relay's own `--replay`, or P1's in-page shim (`out/replay/replay_shim.js installReplay`, imported
  before `detectRelay` so the app runs its live code path). The display runs `features.replay.lookahead_s` (60 s) behind
  with the delay fixed; the stream opens with `?history = lookahead_s + 5 s`.
- **snapshot** — one instant `S` of P1's pack, for the future artifact. The app runs the engine over the `PRE_S` (600 s)
  before `S` on the pack's own field-delta events (the live code path: `parsePayload → ingest → update → physics`), then
  freezes the engine clock at `S + lookahead_s`, so `S` is drawn between real fixes. Only rotors and lights then move.

The app auto-detects: `?mode=live` with no relay falls back to the shim and shows the recorded replay.

## 3. What the UI shows (brief requirements → where)

- **Phone-first touch** — `controls.js`: one finger pans, two pinch-zoom/twist/tilt, tap selects; inertia; follow/chase.
  Verified at 390 × 844 (`app_*_phone.png`).
- **Aircraft picking + info card** — `app.js tap()` projects each track with the near-range view-projection; the card
  (`ui.renderCard`) shows registration / type / model / operator / phase / parking spot / runway / tower / altitude MSL
  and height above the field (§9) / speed / data age. **LADD/PIA → type only** (the card says "Identity withheld", the rows say "withheld").
- **Follow-aircraft camera** — `rig.setFollow`; the card's Follow / Chase buttons.
- **Named views** — Overview, Tower (the cab eye from `site.anchors.tower`), Green Ramp, West Hangars, 28L Final (behind
  an aircraft on the NASR 4.0° VASI path). `HWD.qa.view(name)`.
- **Compact status line (traffic by phase)** — `stats.js phaseCounts` / `statusLine`, always visible in the panel
  (`#phaseline`), e.g. "3 pattern · 1 runway · 1 taxi · 3 parked · 2 heli". A second line is the runway movements.
- **About / credits** — `about.js`: every notice from `docs/ATTRIBUTION.md`, plus adsb.fi (only while used), weather and
  NAIP credits.
- **ATC link-out (D2) with tower hours** — `atc.js`: the tower state now/at the scene time, hours 07:00–21:00 local,
  CTAF 120.2 when closed, the NASR frequency table, and a single link to `https://www.liveatc.net/search/?icao=KHWD`.

## 4. Harness and what was run (2026-11-13, SwiftShader, this machine)

Every image below was looked at (Read tool) before this was written.

- **`jobs/views.mjs`**, desktop 1280 × 720 and phone 390 × 844 @ DPR 1, through P1's shim (`?mode=replay`, the
  artifact's cold start, which draws aircraft within ~5 s): ready in ~2.4 s; **0 console errors / warnings** both
  devices; world `terrain 166,044 tris / map 3994×2427 @ 0.5 m / NAIP 1m2 fit residual 0.007 m`. Shots:
  `overview, tower, green, west, final28l` (clean 3-D, fast framebuffer read), `card`, `follow`, `about`, `atc`,
  `stats` (full HUD).
  - **D1 in the UI**: a locally-built **full-ident** pack (gitignored, then deleted; the committed default is
    type-only) with 27 tracks in view: **2 masked** (business jets; their types are not named here, fix round 1: a type plus a named hour of a flagged aircraft is not repeated in committed docs) leaked nothing (reg/callsign/operator null, label = the
    type designator); **23 of 25 unmasked carried real identity** (positive control: registration, callsign and operator shown for
    unflagged airline and GA tracks; the identities are not repeated here, default D1); **no hex key reached the DOM** (`keyInDom: false`). On the committed type-only
    pack all 25 tracks are masked and type-only.
- **`jobs/smoke.mjs`**, snapshot mode: 14 aircraft drawn, 63 events over the 10-min pre-roll, runway line
  "28L ↑1 ↓3 T&G 2 · 28R ↑1 ↓1 T&G 1", 0 errors.
- **`jobs/relaycheck.mjs`**, end-to-end against `hwd_live_server.py --replay` (spawned): the app detects the relay
  (`hwdlive:1`), and after the fresh relay's cold start (I2 below) draws 9 aircraft, classifies them, and advances the
  relay seq; 0 console errors.

What the renders show: the NAIP ground and the airfield read correctly; tie-down tees and taxiway centrelines on the
Green Ramp; the tower eye over the hangars; placeholders taxiing and in the pattern on pavement; 3-D labels (type +
phase/altitude); the card, About, statistics and ATC sheets legible on both desktop and phone; the phone portrait view
framed along the runways.

## 5. Integration issues (contracts found imperfect; worked around in P4 files only)

- **I1 — opening-burst fixes dropped as stale (P3 `traffic.js ingest`).** `ingest()` drops a **new** track's fix when
  `recvNow − fix.t > MOVING_LOST_MS` (45 s). The 60-s start-up history (`?history`) has a ~46-s polling hole, so its
  older cluster of fixes is 50–63 s old and was all dropped; the display (60 s behind) then had no fix until it caught
  up, and aircraft appeared only ~58 s after load. **Workaround** (`app.js onData`): a payload whose `now` is more than
  ~3 s old (an opening-burst / catch-up payload) is ingested at **its own send time** (`p.now`) rather than
  `Date.now()`, so those historical fixes are kept, as they would have been had they arrived live. Aircraft now draw
  within ~5 s via the shim. **Request to P3**: accept a new track's fix up to `lookahead_s` old during a history burst
  (e.g. a `ingest(payload, recvNow, {history})` flag, or widen the new-track acceptance window for payloads whose `now`
  is well behind `recvNow`).
- **I2 — a freshly spawned replay relay has no backlog.** `hwd_live_server.py --replay` advances its replay head with
  wall time from spawn, and a new client's display (`lookahead_s` behind) reaches real data only after ~`lookahead_s`
  (~60 s). This is a P1 relay trait, not a P4 bug: the in-page **shim** starts `lookahead_s` into the window and draws
  immediately, so the phone artifact and `?mode=replay` have no cold start; only a fresh `--replay` relay does. The
  harness's `views` job therefore drives through the shim; `relaycheck` waits out the cold start. **Request to P1**:
  start a `--replay` relay's head `lookahead_s` into the window (as the shim does), or pre-fill the history buffer, so a
  first client sees data at once.
- **I3 — tower status / local hour keyed off the engine wall clock (P3 `classifier.js` / `traffic.js`).** The
  classifier stamps each event's `tower` and the phase's tower suffix from `towerStatus(fix.t)`, where `fix.t` is the
  engine (wall) clock. In **replay / snapshot** the depicted scene is at the recording's time of day, which differs, so
  a noon scene was labelled "tower closed (CTAF)" and after-hours counts reflected the real-world run time, not the
  recording. **Workaround** (P4 files): the UI computes the tower state from the **data clock** — the card's Tower row
  and the ATC sheet already use `atc.towerAt(sceneTime)`; `ui.ph()` strips a false "tower closed (CTAF)" suffix when the
  scene tower is open, and `app.js` passes `towerOf(e) = towerStatus(toData(e.t))` into `stats.js` so the
  movement-sheet after-hours count and the per-event tags use the recording's local time. In **live** mode the two
  clocks coincide, so nothing changes. **Request to P3**: pass the data clock (or the per-fix data time) to the
  classifier for tower/local-hour decisions, so the offline `tower` field matches the depicted scene in replay.

None of these required editing P1/P2/P3 files.

## 6. Deviations from the fork map

- The five named views are Overview, Tower, Green Ramp, West Hangars and 28L Final (the fork map listed a longer menu,
  §2.10 `qa.view`; the rest are reachable through `HWD.qa.view`, `spot`, `hold`, `thr`, `aircraft`).
- `HWD.qa.shot()` renders from the renderer's final framebuffer (as P2's dev page does) so the harness avoids
  recompositing the heavy SwiftShader scene with `page.screenshot`; a `qa.pause(on)` stops the rAF loop during QA stills
  so the harness drives frames. The DOM-overlay shots (card, follow, About, ATC, statistics) still use `page.screenshot`.
- One quality level (owner decision OD1): the full-feature, highest-resolution tier only. The `low` tier, `?quality=`
  and the Settings switch were removed in review fix round 1 (`app.js QUALITY` has `high` only); sfo3d's
  dynamic-resolution controller and canvas caps remain.
- The settings "lighting" menu is the data clock's light-mode machine (Scene time / Dawn / Day / Dusk / Night, P2's
  `clock.js`), not sfo3d's fixed UTC presets.

## 7. What was not verified / limits

- Only SwiftShader (software) rendering was exercised; real phone GPUs were not. The low tier keeps the canvas ≤ 1.1 Mpx
  and uses P2's 1 m pavement map / 2.4 m NAIP, but texture memory on a real phone GPU is untested (a P2 note).
- A busy **live** period was not observed (the relay was exercised against the recording and, by P1, for ~22 s at night
  with 4 aircraft). The live adaptive delay (up to 65 s with 6.5–60 s polls) is exercised only through the replay path.
- Every recorded hour is **west flow** (PLAN §3). East-flow views (10L/10R finals, the `28L Final` view's opposite) are
  untested because no east-flow window exists.
- The P4 D1 UI test is strong (masked tracks leak nothing; unmasked carry identity; no key in the DOM) but was run on
  one window; P3's own leak harness covers the engine across both windows.
- (Fixed in review fix round 1.) The card header said "Identity withheld · LADD / PIA" for every masked track, also
  on type-only packs where no aircraft need be enrolled. The record now carries the reason (`_masked` 'd1' /
  'type-only' -> `ident.maskWhy`): 'd1' reads "Identity withheld · LADD / PIA", 'type-only' "Identity not shown in this
  recording".

## 8. Review fix round 1 (2026-11-13), app shell

- **Provenance on the card.** Registration, type and model come from the aggregator's database (readsb / tar1090-db), not
  from the broadcast: the card's source reads "aggregator database (adsb.lol / adsb.fi)" (`adsb_db`); "broadcast" stays
  for callsign, position, altitude, speed, squawk and category. A registration derived from the ICAO address
  (`nNumberFromHex`) is shown only when the type is known, with an "inf" marker. The About bullet says the same.
- **About.** Pack text (`desc`, `src`) is HTML-escaped (`about.js esc`); `?pack=` accepts only same-origin relative paths
  (`entry.js safePack`). The live-data line states the real adsb.lol budget behaviour (fast for the first hour, then
  minutes, then about hourly until the rolling 24 h frees up) and the status pill shows the current poll period from
  `/api/ping` (refreshed every 60 s in live mode). The regional backdrop is credited as a USDA NAIP image-service mosaic
  with undated overviews.
- **Phone.** The icon buttons stay on screen (sticky on the right of the top bar), touch targets are 44 px (the sheet
  grab 34 px tall), the tabs 44 px, the ODbL footer has an opaque backing at 11 px; 3-D labels are clamped to the
  viewport, altitudes cannot print "-0 ft", "unspotted" reads "Parked here … no mapped spot", and the phone overview
  starts closer (1,250 m).
  - *Fix round 2.* The fix-round-1 statement was not true everywhere: the grab was 34 px and other controls were small.
    The view row also ran off the right edge, under the icons. Now:
    - The view buttons wrap onto two rows.
    - The icons, the sheet grab, the stats line (one `#statsbtn` button holding the phase line and the runway line),
      the search field and the card actions are each at least 44 px tall.
    - The credit line and the pop-up sheets moved below the second view row.
  - `jobs/phone_ui.mjs` (new, `MOBILE=1 RELAY=none node livetest.mjs jobs/phone_ui.mjs`) checks every visible button,
    link, input and list row in three states: default, sheet open and card open. Each must be at least 44 × 44 px, in
    the viewport and not covered at its centre (`elementFromPoint`). It exits 1 on any violation.
    - Exempt: the inline credit links (WCAG 2.2 SC 2.5.8 inline exception), controls below the bottom edge (the sheet
      in peek) and the sheet under an open card.
    - Result: 53 controls, 0 violations, 0 console errors (`docs/phase2/phase2_fix2_13_phone_view_row.jpg`).
- **Persistence (D1).** Masked tracks are neither stored nor restored (`hwdlive.parked.v1`); a restored stale track is
  reconciled with a new same-type stationary track within 15 m.
- **Docs / commands.** `CLAUDE.md` and `package.json` bind the plain static server to 127.0.0.1; Phase 2 is "in review".

## 9. Altitude display (round-2 recheck m7, 2026-11-13)

**Problem.** The list, the 3-D labels and the card printed `alt_baro` raw as "N ft". `alt_baro` is the transponder's
*pressure* altitude, referenced to 29.92 inHg (14 CFR 91.217(a)(2), LII copy read 2026-11-13). In the five review windows the KHWD
altimeter setting was 30.06-30.17 inHg, so `alt_baro` read 128-229 ft below the altitude MSL (computed with H below), so aircraft on final showed "Final 28L -150 ft" and helicopters "-100 ft".
The card set this value beside a drawn height from another datum ("Altitude 400 ft · 560 ft AGL"). The value also came
from the newest fix, which in replay is up to 60 s ahead of the drawn position. Over the five review windows, 1,095 of
8,279 airborne fixes within 5 km had a negative raw `alt_baro` [obs, aggregate].

**What is shown now** (`js/live/ui.js altitudeOf / altFor / altCard / altMethod`, `js/live/app.js altCtx / qnhAt`):

- **One value per aircraft.** List row, 3-D label and card read the same number: altitude MSL at the display time,
  rounded to 10 ft. It is refreshed on the list's 1-s tick, before the labels are drawn. On the ground the card says
  "On the ground" and the list and label show no altitude.
- **List and labels:** "1,450 ft". A legend line above the rows says "Altitudes in ft MSL · <method> [inf]".
- **Card:** "Altitude 1,450 ft MSL · 1,400 ft above field". The height above the field is the rounded MSL value minus
  the NASR field elevation (52.1 ft, `data/hwd_airport.json frame.field_elev_ft`), so a reader's own subtraction
  agrees. Within ±10 ft of the field elevation it reads "at field elevation"; lower values read "N ft below field
  elevation". The data line names the method, marked inf, for example "altitude: pressure altitude corrected with the
  KHWD altimeter 30.13 inHg (METAR <local time>), between fixes [inf]". Its tooltip gives the formula and the sources.

**Method** (in order; the first plausible value is used):

1. **baro** (default). The aircraft's altitude is what an altimeter set to the current KHWD altimeter setting A would
   read: `MSL = alt_baro - H(A)`, where `H(p) = (1 - (p / 1013.25 hPa)^0.190284) x 145,366.45 ft`.
   - `H` is the NWS pressure-altitude equation (weather.gov/media/epz/wxcalc/pressureAltitude.pdf, read 2026-11-13) [V].
   - The NWS altimeter-setting equation (weather.gov/media/epz/wxcalc/altimeterSetting.pdf, read 2026-11-13) is the same
     relation solved for A at the station elevation. Rearranged, station elevation = H(P_station) - H(A) [V].
   - There is no temperature correction: this is indicated altitude, not true altitude [inf].
   - The cockpit rule of thumb (1 inHg ≈ 1,000 ft) would add about 8 % (dH/dA at 29.92 is 924 ft per inHg, computed).
   - **Which setting.** A comes from the KHWD report at or before the *scene* time (the data clock: the recording's
     time in replay and snapshot). It must be at most 90 min old (`state.js STALE_MIN`, spec §3.3). The reports are the
     ones the environment already holds: the relay's `/api/metar`, the shim's pack reports, or the snapshot pack's.
   - A QA weather override (`?metar=`, `?wx=`) is not the traffic's weather and is never used for altitudes.
2. **geom** applies when there is no usable report or no `alt_baro`. `MSL = alt_geom + 108.09 ft`, the Phase 1
   calibration of the GNSS height against the NASR runway surfaces (`GEOM_OFF`, n 797, `classifier.js RULES`) [obs
   calibration, inf use]. The legend gives the reason, for example "no KHWD METAR at or before this time" or "the QA
   weather override is not used for altitudes".
3. **drawn** applies when neither fix has a usable value, for example a take-off or landing reconstructed across a
   recorder hole. The engine's drawn height (NAVD 88 ≈ MSL) is shown [inf].

**Between fixes** [inf]:
- At a fix, the value is that fix's report.
- Between two fixes, it is the drawn height plus the report-minus-drawn offset (`report MSL - f.y`). The offset is taken
  at the two fixes around the display time and interpolated in time. The number therefore follows the 3-D picture
  through a hole (flare, reconstructed climb-out) and still equals the reports at the fixes.
- A straight interpolation of the reports printed "110 ft MSL" over an aircraft the engine drew touching down (case C
  below); the anchored value reads "50 ft MSL".

**Plausibility** [inf]: an airborne aircraft is not below the ground under it.
- A value more than 25 ft below that ground (the 25-ft report quantum) falls through to the next method. Causes: an
  encoder outside the 125-ft tolerance, or a fix flagged airborne on the runway.
- A value up to 25 ft below the ground is shown at the ground height.
- Measured over the five windows: 156 of 8,279 airborne fixes within 5 km gave a QNH-corrected value below 0 ft MSL
  [obs, aggregate].

**Agreement of the two methods** (QNH-corrected `alt_baro` minus `alt_geom + 108.09 ft`, fixes with both values within
9 km and below 4,000 ft, METAR ≤ 90 min old; aggregate only, script in the fixer's scratch directory):

| window | n | median | IQR |
|---|---|---|---|
| weekend | 3,199 | +9 ft | −16 to +34 |
| weekday | 2,005 | −2 ft | −52 to +23 |
| heli | 2,127 | −6 ft | −31 to +19 |
| pat | 3,226 | −21 ft | −71 to +4 |
| night | 632 | −37 ft | −37 to −12 |

Single aircraft can differ by more. In the weekend window, case D (a C152) reads about 100 ft below its GNSS height.

**Checked in the app** (`livetest.mjs`, shim, type-only weekend pack, snapshot mode). Desktop 1280×720 and phone
390×844, 0 console errors; every image looked at.

| case | what | before | now (list = label = card) |
|---|---|---|---|
| A | C172 on final 28L | 200 ft (newest fix, 60 s ahead) | 490 ft; card "490 ft MSL · 440 ft above field" |
| B | R22 in flight | 600 ft | 650-660 ft MSL · 600-610 ft above field (it climbs while the snapshot runs) |
| C | BL8 on short final 28R | −150 ft | 50 ft MSL · at field elevation |

- **Replay mode.** The setting is picked up the same way, from the shim's `/api/metar` (A3013, 6 min old).
- **QA override.** With `?metar=…A2992…` all values switch to the geom method. For the same aircraft they are 10-90 ft
  from the baro values (case D: 760 vs 670 ft).
- **Phone UI.** `jobs/phone_ui.mjs`: 52 controls, 0 violations. One fix was needed. With the 44-px grab of fix round 2,
  the card-open peek (56 px) left 9 px of the tab row on screen, which gave five half-visible targets. The card-open
  peek is now 47 px, so only the grab shows.
  - The job samples 0.8 s after selecting. Under SwiftShader the sheet transition had not started 1.8 s after
    selecting and had finished by 4.8 s, so the job may see either end state. The settled state was measured separately: grab 798-842 px, tabs at 844 px (below the edge).

**Not done / limits.**
- No temperature correction (cold-day true altitude is lower).
- No per-aircraft encoder calibration for the baro value: the classifier's per-aircraft geom offset is not applied
  to it.
- A one-second refresh: a 2,000 ft/min climb moves in about 30-ft steps.
- `about.js` (not a file of this task) still says altitudes "are what the aircraft broadcast". It should say that the
  shown altitude is the broadcast pressure altitude corrected with the KHWD altimeter setting.
- Observed in passing, not changed: in snapshot mode, airborne aircraft keep moving and slowing after the engine
  clock is frozen (about 1 kt and 5 m per 10 frames). §2 says only rotors and lights move.


## 10. Review round 3, iteration 2 (2026-11-14): one altitude source, forget horizon

**Altitude (F5).** The baro method of section 9 printed a number that contradicted the 3-D picture: the engine draws the
calibrated GNSS height (alt_geom - GEOM_OFF), the label showed alt_baro with the KHWD altimeter setting, shifted on to the
drawn path between fixes. The recheck measured the two more than 100 ft apart in 11-19 % of the airborne samples within
3 km and an SF50 drawn 23 ft above the runway just after lift-off labelled "40 ft MSL · 10 ft below field elevation".
Now (`js/live/ui.js altitudeOf / altCard / altMethod`):

- **One source.** List, 3-D labels and card show the DRAWN height (D.y, NAVD 88 ~ MSL [inf]). At a fix (within 1.5 s)
  that is the fix's report as the engine reads it (`method` 'geom', or 'baro' = the pressure altitude mapped on to the
  GNSS calibration by the unit's own offset, classifier.js prep); between fixes or in a reconstructed take-off / landing
  it is the drawn path (`method` 'drawn', inf). The data line says which.
- **Never 'below field elevation' for a body drawn airborne.** When the rounded value is at or below the field elevation
  (the 10R end lies 24 ft below it), the card gives the height above the ground under the aircraft ("20 ft above the
  ground", or "just above the ground").
- **The altimeter-equivalent value** (alt_baro - H(A), NWS equations as in section 9, no temperature correction) is kept
  only in the method note's tooltip, with the METAR it used; it is never the headline number.
- **Measured** (the reviewer's scratch probe, 1 Hz, airborne fixed-wing within 3 km): 0 samples labelled below the field
  elevation and 0 whose label differs from the drawn height by > 100 ft, of 10,397 (weekend), 10,518 (pat), 281 (od3s)
  and 1,320 (od3p) samples. In the app (desktop 1280 × 720, snapshot mode on the local od3s pack, RELAY=none): OD3 case S
  1 s after lift-off reads "Altitude 50 ft MSL · just above the ground" (drawn 5 ft above the runway; round 3 read
  "10 ft below field elevation" there) and 3 s later "60 ft MSL · 10 ft above field" (drawn 22 ft up, over a part of 28L
  that lies below the field elevation); the list row and the 3-D label show the same 50 / 60 ft; 0 console errors.
  Both images were looked at (scratch, not committed: the pack is local).
- `about.js` still describes the section-9 method (not changed here; noted for P4).

**Forget horizon (F7).** `js/live/app.js` now passes `onHorizon: (h) => traffic.forgetHorizon(h)` to `StreamFeed` (the
feed fell back to `onForget(absent)`, which marked every silent and parked aircraft LADD / PIA and faded it out on each
relay restart) and exposes the feed as `HWD.feed()`. `jobs/horizon.mjs` (RELAY = a full-ident replay relay; WAIT ms)
reconnects the page's feed with a seq from another relay process and checks: every parked / silent body is kept and
drawn, the silent ones show their type only (`ident.withheld = 'horizon'`), nothing is marked LADD / PIA by the horizon
(`counters.d1Forget` unchanged). Run on this machine against `hwd_live_server.py --replay rec_pack --from 2026-11-08T20:00Z`
on a local 89xx port: PASS (5 bodies kept, 1 silent aircraft with an identity → type only, 2 tracks withheld,
0 console errors). The job prints counts only; its JSON goes to `out/phase2/` (or `OUT`).

**Card height (review round 3, iteration 3, F8).** The card's second value was the height above the NASR field elevation
(52.1 ft); over the west half of 10R/28L, which lies up to ~24 ft lower, it understated the drawn height above the
runway by up to 27 ft ('60 ft MSL · 10 ft above field' on a body drawn 20 ft above the runway). `ui.js altCard` now
gives, below 300 ft drawn above the ground (`AGL_CARD_FT` [inf]), the height above the ground or runway under the
aircraft - "30 ft above the runway" / "30 ft above the ground" / "just above the runway" - from the drawn height and
`site.groundY` (`app.js altCtx().surface` = `site.surface`, so the card knows a runway is beneath); higher up it says
"1,110 ft above airport elevation (52 ft)", so it is not read as a height above the ground. MSL, the list rows and the
3-D labels are unchanged. Checked: a scratch probe (1 Hz, airborne fixed-wing within 3 km; pat / weekend / od3s /
od3p) found 0 card heights above the ground / runway more than 15 ft from the drawn height and 0 samples below 290 ft
showing the airport-elevation form; a desktop snapshot of OD3 case S (SF50 take-off) just after lift-off reads
"70 ft MSL · 30 ft above the runway" (looked at; scratch, not committed). The phase line can now read "Stopped" /
"Stopped on the runway" (`phaseInfo.label` of a `taxi` / `runway_taxi` body at rest for 10 s; `docs/phase2_traffic.md`
§4 "Fix round 3, iteration 3").
