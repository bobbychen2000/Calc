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
  (`ui.renderCard`) shows registration / type / model / operator / phase / parking spot / runway / tower / altitude /
  speed / data age. **LADD/PIA → type only** (the card says "Identity withheld", the rows say "withheld").
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
    type-only) with 27 tracks in view: **2 masked** (C680, GLF4) leaked nothing (reg/callsign/operator null, label = the
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
- The quality tiers are just `high` / `low` (P2's world tiers), with sfo3d's dynamic-resolution controller and canvas
  caps; `?quality=` and the Settings menu switch them.
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
- The card header reads "Identity withheld · LADD / PIA" for every masked track. On a **type-only pack** (where the
  relay masks *all* aircraft for a published artifact, not only the flagged ones) this names a specific reason that may
  not apply to a given aircraft; the About panel states "This recording shows every aircraft by type only". Softening
  the header per-pack is an open nicety, not a correctness issue.
