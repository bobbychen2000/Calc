# Phase 2f: integration and named-view renders

Date: 2026-11-21. Package P2f of Phase 2 (docs/PLAN.md §7), on the module checkpoint commit 798dcc1 plus the P2e
leftovers in the working tree. Fork base: sfo3d @ **e3218d6**, plain WebGL2 `live.html` path (working default Q7).
Nothing in `sfo3d/`, `pc12/` or `hwd3d/` was modified (`git status` clean there; `hwd3d/` is not checked out in this
tree); nothing was committed.

Tags as in docs/PLAN.md: **obs** = observed, **inf** = inferred.

## 1. Result

| Item | State |
|---|---|
| The four packages together in `live.html` | markings (P2b), gates (P2c), terminals (P2d) and the UI shell / relay (P2e) load and build together on the core (P2a). Every extension's `buildWorld` returns ok; 161 world items; 164 stands, 56 bridges, 56 VDGS; the class reference docks at 54 of 56 bridges (111 and 235 do not, as gates.md §2.6). |
| Modes | snapshot (default), live through the relay, live with the page served by the relay itself (standalone), relay requested but offline (snapshot + red "Relay offline"), and snapshot with `?park=`: **all five scenes have a clean console** (0 errors, 0 warnings, 0 page errors, 0 HTTP ≥ 400, 0 failed requests). §3 |
| Integration bugs | 4 found and fixed (§2): the DEBUG park note was overwritten every second; the gates legend line appeared only with `?legend=1`; the Tower view was 41 % console band; the snapshot status pill repeated the date. |
| Frame time per tier | llvmpipe (no GPU), reference only: low 0.98-1.18 s, medium 1.20-1.33 s, high 1.55-1.68 s, ultra 1.33-1.58 s per frame at 1024-1280 px wide. JS main-thread time is only 2-4 ms per frame; 108-201 draw calls and 0.60-0.77 M triangles per frame (all passes). §4 |
| Debug parking | 10 class-correct static aircraft (A333, B77W, 4 × B738, 2 × A320 ...) at T2 north pier, T1 and the west remote apron: **all 8 bridge stands docked**, the 2 remote stands got stairs, buses and GSE. §5 |
| Named views | 25 renders `docs/phase2/view_*.png` at deviceScaleFactor 1: overview, 4 runway ends, T1, T2, tower (orbit and cab), T2 pier stand 233, bridge 230, T1 stands 113 and 102, remote stand 404, hold H1, the T2 pier tip, 3 night views, 4 phone UI and 2 laptop UI (live mode). I looked at every one. §6 |
| Tests (no browser) | `test_geo_js.mjs`, `test_relay.py` (7/7), `test_metar_zsss_js.mjs` (0 differences on 69,104 reports), `test_buildings3d.mjs`, `test_frame.py`: **all pass**. |
| `sha3d/CLAUDE.md` | new: run commands, harness views, architecture, data files, rules, committing. |
| Safe-to-commit list | §8. |

## 2. Integration bugs found and fixed

| # | Symptom (how found) | Cause | Fix (files) |
|---|---|---|---|
| 1 | With `?park=` the panel note "DEBUG ?park=: n static aircraft (not traffic)" vanished within a second (integration scene `park`: the note read only the weather and runway lines). The DEBUG label is what keeps parked models from passing as traffic. | The gates package wrote it with `ui.setNote()`; the UI shell (P2e) rewrites the note with `setNote()` from its once-a-second status hook. The gates package also restored a `baseNote` captured before the shell existed (the core's "Static scene" note). | `ui.js`: keyed extra note lines `ui.setNoteLine(key, text, {first})` rendered with the main note; `gates.js`: the DEBUG line is a keyed line shown **first** (a phone's bottom-sheet peek shows the top lines), the `baseNote` restore is gone. Checked: note = "DEBUG ?park=: 4 static aircraft (not traffic) / METAR ... / Runway in use ..." (`view_laptop_live_stand_233.png`). |
| 2 | The legend had no jet-bridge line unless the URL carried `?legend=1`; with it, the line arrived as raw html with its own "Observed / inferred" header, re-wrapped by the shell. | gates.js appended to the legend body only under `?legend=1` (the core's old slot), before the shell's legend API existed. | `gates.js`: always `ui.addLegendLine('gates', ...)` with obs / inf chips; `shell.js`: lines other packages added earlier are kept and placed after the stand-label line. `view_phone_t2_legend.png`, `view_laptop_live_t2.png`. |
| 3 | The in-app Tower view (`view_towercab` first pass, laptop): the lower 41 % of the frame was the dark console band and the top 15 % the cab ceiling (buildings.md open issue 13 reported it for phones). | The eye sat at the cab centre, 5.65 m from the glass, so the 0.6 m console band subtended −10° to −34° and the roof +15°. | `terminals.js`: `anchors.tower.cabHalf` (cab half-width at eye height from the tower dims); `app.js`: the eye stands 2 m inside the glass on the runway side (yaw 262°), pitch −7° (−5° when no cab is modelled). Now the horizon sits at 40 %, the runways and T2 fill the middle, and the lower quarter is the tower head's ledge outside the glass (photo 02 shows that ledge). `view_towercab.png`, `view_phone_towercab.png`. |
| 4 | Status pill "Snapshot · 20 Nov · 20 Nov, 12:15" on screens ≥ 1720 px (where the sub-line shows). | The shell put the date in both the text and the sub-line. | `shell.js`: the sub-line is the time ("12:15 CST"). |

No console error or warning existed before the fixes either. The only browser-logged error in any scene is Chromium's own
"Failed to load resource: 503" line for `/api/ping` in the offline scene, where the harness answers 503 on purpose; the job
classifies exactly that line as expected.

Harness additions (no app impact): `jobs/integration.mjs` (new: scenes, console audit, perf) and `jobs/views.mjs` (new kinds
`hold:`, `bridge:`, `park:` / `unpark`, `ui:`, `<view>@<name>`, `stand:` with camera numbers, `T=snapshot`, the P2f set
`VIEWS=@full`).

## 3. Console and modes

`SOFTGL=1 RELAY=http://127.0.0.1:8792 SCENES=snapshot,live,standalone,offline,park node livetest.mjs jobs/integration.mjs`
(each scene: load, then a tour through Overview, T2, T1, Runways, Tower, Top and stand 233 so every extension's frame,
lights and label hooks run; quality high, fixed resolution). The relay was a real `sha_live_server.py --port 8792`
(METAR / TAF on, ADS-B off).

| Scene | Mode / status pill | Weather and runway line | Console |
|---|---|---|---|
| snapshot (default page) | snapshot · "Snapshot · 20 Nov" | METAR 0400Z 330° 6 m/s CAVOK Q1027 13/-5 °C, trend NOSIG not applied · north flow, arr 36R, dep 36L | 4 log lines (the extensions' build summaries), 0 errors, 0 warnings |
| live (harness serves the page, `/api/*` proxied) | live · "Live weather · METAR 0000Z" | METAR 0000Z 280° 2 m/s CAVOK Q1029 10/0 °C · north flow | clean |
| standalone (page and all static files from the relay's allow-list) | live · same | same | clean: the allow-list serves every file the page loads, including `../sfo3d/data/models/` |
| offline (`?relay=1`, API answers 503) | snapshot · red "Relay offline · snapshot 20 Nov, 12:15" | snapshot weather | clean (one expected 503 line) |
| park (`?park=233,230,113,404`) | snapshot | DEBUG line + weather + runway | clean; 4 aircraft parked, bridges docked |

After the last two fixes (DEBUG line first, pill sub-line) the scenes snapshot, standalone, offline and park were run once
more: all clean; pill "Snapshot · 20 Nov · 12:15 CST"; park note "DEBUG ?park=: 4 static aircraft (not traffic)" above
the METAR and runway lines; standalone live on the relay's then-current METAR 0030Z.

Upstream requests during this package: aviationweather.gov 4 METAR + 4 TAF requests in about 1 h 35 min of relay uptime (the relay's
10-min cache; some TAF requests answered 304). **adsb.lol: none** (relay ADS-B off). **OpenSky: never.** The harness
mock was not used.

Start-up on this sandbox (llvmpipe): `__shaReady` after 8.7-11.8 s (ground 1.2 s, markings 0.45 s, gates 0.7-0.8 s,
terminals 0.08 s; the rest is shader compilation and first frames). With `?park=` each model takes 22-32 s more,
although its fetch takes 10 ms: the async decode steps interleave with 1-1.5 s software-rendered frames. A real GPU does
not have this cost (sfo3d loads the same `.sfom` files on phones).

## 4. Frame time per quality tier (llvmpipe; reference only)

`SOFTGL=1 SCENES=perf TIERS=low,medium,high,ultra node livetest.mjs jobs/integration.mjs`: snapshot mode, fixed
resolution, viewport 1280 × 720 at deviceScaleFactor 1, 10 warm-up frames, then 40 frames per view; ms between
requestAnimationFrame callbacks (median / p90). "js" = main-thread time in `scene.frame` + `R.render` + `R.present`;
draws and triangles are counted on the WebGL context (all passes: shadow cascades, MSAA scene, post).

| Tier | Render size | Overview | T2 | Stand 233 |
|---|---|---|---|---|
| low (phone default) | 1024 × 576 | 1183 / 1283 ms (js 2.9, 201 draws, 767 k tris) | 1050 / 1133 (js 2.3, 127, 600 k) | 983 / 1050 (js 2.2, 108, 706 k) |
| medium | 1152 × 648 | 1333 / 1400 (js 3.1) | 1267 / 1350 (js 2.5) | 1200 / 1267 (js 2.0) |
| high (laptop default) | 1280 × 720 | 1683 / 1867 (js 4.0) | 1550 / 1617 (js 2.2) | 1567 / 1783 (js 2.1) |
| ultra | 1280 × 720 | 1583 / 1767 (js 3.3) | 1467 / 1550 (js 1.9) | 1333 / 1433 (js 2.3) |

Reading: on llvmpipe the frame is rasteriser-bound (4 CPU threads); resolution, the shadow map (2048 / 3072 / 4096) and
MSAA explain the spread, and ultra ≈ high here because the viewport caps both at 1280 × 720 (run-to-run noise ±10 %; an
earlier run gave 917-1517 ms). The JS cost is small (2-4 ms) and the geometry modest (≤ 201 draw calls, ≤ 0.77 M
triangles including shadow passes), which is in the range sfo3d runs on phones. A real phone has not been measured.

## 5. Debug parking: bridges docking

`park:229+230+231+233+234+113+115+102+403+404` (gates `SHA.qa.park`, class reference type; static models by URL from
`../sfo3d/data/models/`, neutral livery; flagged DEBUG, not traffic):

| Stand | Area, class | Type | Bridge (model, inf) | Docked |
|---|---|---|---|---|
| 229 | T2 north pier, E | A333 | gate 29, AT3 52/100 | yes |
| 230 | T2 north pier, EL | B77W | gate 30, AT3 58/116 | yes |
| 231 | T2 north pier, C | B738 | gate 31, AT3 61/127 | yes |
| 233 | T2 north pier, C | B738 | gate 33, AT3 52/100 | yes |
| 234 | T2 north pier, C | A320 | gate 34, AT3 52/100 | yes |
| 113 | T1 west face, C | B738 | gate 9, AT3 58/116 (rotunda on the facade) | yes |
| 115 | T1 west face, C | B738 | gate 11, AT3 58/116 | yes |
| 102 | T1 north face, EL | B77W | gate 3, AT3 68/144 | yes |
| 403 | west remote apron, C | B738 | none: stairs at 1L and the last left door, bus, GSE | - |
| 404 | west remote apron, C | A320 | none: stairs, bus, fuel and catering trucks | - |

The class-reference test over all 56 bridges (`SHA.qa.gates().refDock`) stays at 54 / 56 (111 and 235: cab turn beyond
the inferred sell sheet, gates.md §2.6).

## 6. Named-view renders (deviceScaleFactor 1; all looked at)

```
SOFTGL=1 OUT=docs/phase2 PREFIX=view T=snapshot VIEWS=@full node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=docs/phase2 PREFIX=view T=snapshot VIEWS='park:229+230+231+233+234;t2pier' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=docs/phase2 PREFIX=view T=2026-11-20T13:30:00Z VIEWS='park:229+230+231+233+234;t2pier@night_t2pier;stand:233,-,70,1,24@night_stand_233;hold:H1@night_hold_H1' node livetest.mjs jobs/views.mjs
SOFTGL=1 DEVICE='iPhone 15' SHOWUI=1 QUALITY=low OUT=docs/phase2 PREFIX=view_phone T=snapshot VIEWS='overview;ui:legend;t2@t2_legend;ui:close;park:233+234+230;ui:fly:233;stand:233,-,95,1,28@stand_233;ui:nocard;towercab' node livetest.mjs jobs/views.mjs
SOFTGL=1 W=1440 H=900 SHOWUI=1 RELAY=http://127.0.0.1:8792 OUT=docs/phase2 PREFIX=view_laptop T=snapshot VIEWS='ui:legend;t2@live_t2;ui:close;park:233+234+230+229;ui:fly:233;stand:233,-,90,1,26@live_stand_233' node livetest.mjs jobs/views.mjs
```
Day views are at the snapshot instant (2026-11-20 12:15 CST, recorded CAVOK); the laptop UI views are live (wall clock,
08:31 CST on 21 Nov, the relay's current METAR). Orientation checks printed by the job: T2 x −1222 < runway x min −445
(west), T1 x 581 > runway x max 79 (east), headings 177.34 / 177.31 (N-S): all ok. The phone views were rendered with the
`ui:card` state replaced by `ui:fly` after the first pass showed the full card covering the stand (the app's own
"label tap" state).

| Render | What it shows / what I checked |
|---|---|
| `view_overview.png` | the extent in the WorldCover plain with haze; T2 west, T1 east; runways N-S. Canals inside the extent read near-black (buildings.md open issue 7) |
| `view_rwy_18L.png`, `view_rwy_36R.png` | 45 m asphalt runway, concrete ends, blast pads with yellow chevrons, centreline, threshold stripes; red painted mandatory markings and hold signs at the crossing taxiways |
| `view_rwy_18R.png`, `view_rwy_36L.png` | 60 m concrete runway over the 300 / 150 m displaced portions: white DTHR arrows, the threshold bar, pattern-A holds both sides |
| `view_t1.png` | T1 two-tier concourse, tower behind it, bridges on the west and north faces; the east apron |
| `view_t2.png` | T2 hall, concourse, both finger piers and arms with their bridges; south-west office fans |
| `view_tower.png` | the tower from the apron: shaft, flared head, cab, the T1 concourse in front; stand signs, red stand safety lines and white equipment boxes on the apron |
| `view_towercab.png`, `view_phone_towercab.png` | after fix 3: through the cab glass towards T2 over both runways; the head's ledge in the lower quarter. Phone: stand labels along the horizon |
| `view_stand_233.png` | T2 north pier: B738 docked at 233 (tunnel to door 1L), GSE, prism signs "232" / "233" on the rotundas, VDGS posts, red bridge activity hatch, "设备区" box |
| `view_bridge_230.png` | B77W at 230 and A333 at 229 docked through their long glazed fixed links and tunnels; B738 at 231 below |
| `view_stand_113.png` | T1 west face: B738 docked from the facade rotunda "113", next rotunda "112" |
| `view_stand_102.png` | T1 north face: B77W docked through the inferred fixed link; idle stair units on the east remote apron behind |
| `view_stand_404.png` | west remote apron: A320 at 404 and B738 at 403 with passenger stairs, buses, fuel and catering trucks; post signs on the grass |
| `view_hold_H1.png` | pattern-A holding position on H1 with the "18L-36R" painted mandatory markings and the "H1 / 18L-36R" sign assemblies |
| `view_t2pier.png` | the T2 north pier tip with the five parked aircraft and their bridges |
| `view_night_t2pier.png`, `view_night_stand_233.png` | 21:30 CST: lit curtain walls and tunnels, internally lit stand signs, cab lights; the apron is dark (no floodlights: airfield lighting is not modelled yet) |
| `view_night_hold_H1.png` | the internally lit hold signs; no stop bar or taxiway lights (not modelled yet) |
| `view_phone_overview.png` | iPhone 15 (393 × 659), low tier: pill "Snapshot · 20 Nov", clock, view bar, credit line, legend chip, sheet peek with the weather and runway lines |
| `view_phone_t2_legend.png` | legend open: airfield, stand labels, **jet bridges** (fix 2), markings, buildings, ... with obs / inf chips |
| `view_phone_stand_233.png` | after "Fly to stand": compact card, the docked B738 and the "233" label above it |
| `view_laptop_live_t2.png` | 1440 × 900, **live**: green "Live weather", 08:31 CST, METAR 0000Z line, legend open with the jet-bridge line, 30-odd stand labels |
| `view_laptop_live_stand_233.png` | live, parked aircraft: the note starts with the DEBUG line (fix 1), stand card bottom-right |

## 7. Rules checked

- **No FAA marking / sign / lighting constant in a sha3d code path.** `grep -rni "faa|AC 150|5340|7110|8400" js` finds:
  provenance comments; the inf-labelled photocell placeholders in `js/env/state.js` (nothing draws a PAPI or obstruction
  light); the METAR / TAF decoder's coding references; aircraft-side light rules (AIM 4-3-24). Markings and signs use
  `js/live/caac_markings.js` (MH 5001-2021 clauses or inf).
- **No SFO leak:** `grep -rn "117\.83|27\.83|32\.29|37\.6188|KSFO|sfolive|Los_Angeles|window\.SFO|SFO_|flysfo"` over
  `js`, `live.html`, `live.css`, `sha_live_server.py` finds comments only.
- **Fork headers:** every file copied from sfo3d starts with `forked from sfo3d@e3218d6 <path>`; the files without it are
  new (generated data, new modules, jobs) and say so in their first line.
- **Relay:** generic User-Agent (asserted by `test_relay.py`); ADS-B off by default, 180 s floor, persisted daily cap; the
  browser talks only to the relay. No OpenSky anywhere.
- **Models** by URL from `../sfo3d/data/models/` (not copied). `sfo3d/`, `pc12/` untouched; nothing committed.
- **Observed vs inferred:** legend lines now include the bridges; stand labels, card, About unchanged; DEBUG-parked
  aircraft are labelled in the note.

## 8. Files safe to commit

Everything below was checked: no secrets, no per-flight observed-elsewhere data, no AIP lists, no third-party imagery
other than our renders; the copied files carry fork headers.

Changed or new in this package (P2f):
- `sha3d/CLAUDE.md` (new)
- `sha3d/docs/phase2/integration.md` (new, this report)
- `sha3d/jobs/integration.mjs` (new), `sha3d/jobs/views.mjs`
- `sha3d/js/live/app.js`, `sha3d/js/live/gates.js`, `sha3d/js/live/shell.js`, `sha3d/js/live/terminals.js`,
  `sha3d/js/live/ui.js`
- `sha3d/docs/phase2/view_*.png` (25 renders, 19 MB in all; the lead may keep a subset):
  `view_overview`, `view_rwy_18L`, `view_rwy_36R`, `view_rwy_18R`, `view_rwy_36L`, `view_t1`, `view_t2`, `view_tower`,
  `view_towercab`, `view_stand_233`, `view_bridge_230`, `view_stand_113`, `view_stand_102`, `view_stand_404`,
  `view_hold_H1`, `view_t2pier`, `view_night_t2pier`, `view_night_stand_233`, `view_night_hold_H1`,
  `view_phone_overview`, `view_phone_t2_legend`, `view_phone_stand_233`, `view_phone_towercab`,
  `view_laptop_live_t2`, `view_laptop_live_stand_233`

Left uncommitted by P2e (after the checkpoint 798dcc1), reviewed here and safe:
- `sha3d/docs/phase2/relay_ui.md` (64 added lines: report text)
- `sha3d/live.css` (one rule: the remote stand label's dashed border)
- `sha3d/docs/phase2/ui_laptop_stand_card_fly.png`, `ui_laptop_stand_card_label.png`, `ui_laptop_t2_labels.png`,
  `ui_phone_stand_card_fly.png` (re-rendered)
- `sha3d/docs/phase2/ui_laptop_about.png`, `ui_laptop_about_end.png`, `ui_laptop_about_licences.png`,
  `ui_laptop_live.png`, `ui_laptop_live_about.png`, `ui_laptop_relay_offline.png`, `ui_laptop_settings.png` (new renders)

Do **not** commit: `sha3d/out/` (harness output and the relay's `out/relay/.state/` quota log; gitignored),
`sha3d/refs/cache/**` except files a `SOURCES.json` marks redistributable (gitignored by default), `tools/geo/gcj02.py`
(gitignored, owner decision pending), any `__pycache__/`.

## 9. Open issues

1. **Airfield lighting is not modelled** (night views): no apron floodlights, runway / taxiway lights, stop bars, PAPI or
   PALS. AD 2.14 facts and CAAC photometry are needed (a later lighting package); the env still carries US photocell
   thresholds as labelled inf placeholders.
2. **Model loading under llvmpipe** takes 22-32 s per type (§3); harness runs with many parked types are slow. Not a
   product issue on a GPU, but phone load time is unmeasured.
3. **Frame time on a real phone is unmeasured**; llvmpipe numbers are reference only (§4).
4. **Phone peek and the note**: the peek shows about three note lines; with the DEBUG line first, the runway line can
   fall below the fold while debug parking is on (QA only).
5. **Tower view** (fix 3) faces 262° from 2 m inside the west glass; turning round in the cab looks across the cab
   interior. The cab plan and orientation stay inf (buildings.md open issue 4).
6. Carried from the packages: bridges 111 / 235 cannot dock and three rotundas were moved (gates.md §10); markings
   placement inferred (markings.md); T1 outline south end and heights inferred (buildings.md §8); Google Fonts still
   linked (relay_ui.md open issue 9); traffic is Phase 3.
7. `js/live/gates.js` `WALL_H` still uses the 25 m T2 rule for the VDGS facade test while the modelled T2 walls are 15 /
   21 m (buildings.md open issue 11). No unit is facade-mounted (all stops are 20-40 m from the walls), so nothing
   changes on screen today.

## Fix round 1 (2026-11-21)

Integration of the three package fixers' answers to `review_visual.md` (markings, buildings, gates), plus the
hand-offs between them. Nothing was committed. `sfo3d/`, `pc12/` and `hwd3d/` are untouched (`git status` is clean
there). Tags as above: **obs** = observed, **inf** = inferred.

### F1. Review findings: where each one stands

| # | Owner | Status after integration | Seen in |
|---|---|---|---|
| H1 threshold paint blurred | markings | **fixed**: directional footprints. The final set shows 6 + 6 = 12 stripes at 18L / 36R and 8 + 8 = 16 at 18R / 36L | `view_rwy_*.png`, `fix1_integration_thresholds.png` |
| H2 brown strip at the facades | buildings | **fixed** (airside fill, asphalt, src inf). See F4.1 for a similar gap at the edge stands | `view_stand_233`, `view_bridge_230`, `view_stand_102` |
| M1 night airfield black | markings (a), gates (label) | **partly**: apron flood 0.42 × albedo, warm; legend and About say airfield lighting is not modelled (Phase 5). Aircraft and GSE are not flood-lit (deferred hand-off) | `view_night_*` |
| M2 no floodlight masts | gates | **fixed**: 73 masts (inf); the clearances now come from table 4.9.5 in the one parameter table | `view_tower`, `view_bridge_230`, `view_stand_102` |
| M3 night glazing clipped | buildings | **fixed**: warm, per-bay variation, dark mullions | `view_night_t2pier` |
| M4 lead-ons over DTHR arrows | markings | **fixed**: yellow runs beside the shafts, never through the heads or the bar | `view_rwy_18R`, `view_rwy_36L` |
| M5 nose tip vs nose wheel | gates + integration | **fixed**: the stop node is the nose-wheel stop for every package. The painted envelopes now follow it (F2.1). Side effect at the edge stands: F4.1 | `view_stand_*`, `fix1_integration_envelope_233.png` |
| M6 water black, dotted kerbs | markings (water), buildings (kerbs) | **fixed** | `view_overview`, `view_t2` |
| L1 36L chevrons 75 m | markings + integration | **fixed**: chevrons over the full 120 m pad. The "AIP 75 m conflict" was a misreading of [length, width] (F2.2) | `view_rwy_*` |
| L2 T1 hall box | buildings | **fixed**: arched roof (inf) | `view_t1`, `view_tower` |
| L3 tower cab view | buildings | **fixed**: faces the 18L/36R midpoint; no console band | `view_towercab`, `view_phone_towercab` |
| L4 idle airstairs everywhere | gates | **fixed**: staged in the equipment areas, now **20 of 26** groups (F2.1) | `view_stand_102` (background), `view_stand_404` |
| L5 snow-white city | buildings | **fixed**: hashed wall palette, grey roofs | `view_overview`, `view_t1`, `view_t2` |
| L6 "T2 APRONS NR. 2" | gates | **fixed**: "T2 APRON 2" | `view_phone_stand_233`, `view_laptop_live_stand_233` |
| L7 attribution hidden | gates | **fixed**: dark credit strip; the card stays above it | `view_laptop_live_*`, `view_phone_*` |
| L8 "CST" | gates | **fixed**: "UTC+8" | all UI views |
| L9 haze ignores the weather | buildings | **fixed**: L = clamp(0.8 / σ, 1.2, 20 km) | `view_overview` |
| L10 first pad chevron | markings | **verified** (fig. 6.2.25: the cut legs are right); no chevrons on taxiway pavement | `view_rwy_18L` |
| Extent ring (lead) | buildings + integration | **fixed**: S2 cross-fade and haze ramp (buildings); context lines fade inside the ramp (F2.3) | `fix1_integration_extent_edge.png` |

### F2. Hand-offs applied

1. **Stand envelopes on the nose-wheel convention** (gates → markings, `js/live/caac_decals.js` `buildStands`). The
   class planform is shifted forward by `class_ref.<cls>.nose_gear_m`: `toW([u, v]) = nose + h·(u + ng) + rn·v`. The
   stop line, lead-in and alignment line stay at the node, and the stop-line comment now cites the convention.
   - Effect: the red nose-clearance line runs ahead of the B738's nose tip at 233. Before, it crossed the fuselage about
     2.5 m behind the tip (`fix1_integration_envelope_233.png`, the same camera as the gates fixer's
     `g_fix1_nose233_top`).
   - Counts from the page: equipment areas 265 → 261, hatched overlaps 91 → 94; masts unchanged (73, identical
     rejection counts).
   - **Staged idle stairs 26 → 20 groups** (all 20 in equipment areas). The six groups that lost their unit are the
     whole west remote apron (401-413) and T2 remote 286-290. See F4.1.
2. **Table 4.9.5 in the one parameter table** (gates → `js/live/caac_markings.js`). `CAAC.separation.twyCLToObject` =
   col. (11) {A 15.5, B 20.0, C 26.0, D 37.0, E 43.5, F 51.0} and `taxilaneCLToObject` = col. (13) {A 12.0, B 16.5,
   C 22.5, D 33.5, E 40.0, F 47.5}. I checked the values against the local MH 5001-2021 copy; 9.2.7 applies col. (13)
   to apron floodlight supports. `gate_system.js` `placeMasts` imports them and has no local copy now (same values, so
   no mast moved).
3. **Context lines fade inside the extent ramp** (buildings → core, `js/shaders/ground.js`):
   `extF = smoothstep(0.55, 0.95, ext)` for ditches, roads, rail and water. The soft extent mask is 0.5 at the polygon
   where the OSM context ends, so these lines used to stop at half weight. The change is small at overview range: a mean
   0.02 grey-level difference, concentrated along the extent outline (`fix1_integration_extent_edge.png`).
4. **Docs.**
   - `docs/phase1/standards_refs.md` §1.3: the fig. 6.2.25 reading. §1.4: the blast-pad row, plus a change note.
   - `docs/phase1/airport.md`: the blast-pad note (F2.2).
   - `docs/phase1/stands.md`: the reference point is now the nose-wheel stop, with `nose_gear_m` and the moved cab
     points.
   - `docs/phase2/markings.md`: §5 stop lines and safety lines; open issue 2 closed; the §3 table row; integration
     notes.
   - `docs/phase2/gates.md`: integration notes.
   - `sha3d/CLAUDE.md`: the `thr:` job view, the gates `SET='fix1;fix1night'` and buildings `FILLCHECK=1` options, the
     QA hooks `masts()` / `idleStairs()` / `SHA.markings.apron()` / `plan()`, and a new "Conventions" section (stop node
     = nose-wheel stop, paint hook signature `shaGroundPaint(wp, fw, dxy, apt, paved, rough)`, `sha_apron_flood`,
     `blast_pad_m` = [length, width], table 4.9.5, airside fill, UTC+8, tower view, haze).

**F2.2 Conflict found and resolved: the 36L "75 m" blast pad.** `aip_facts.blast_pad_m` is the pad's
**[length, width] at both ends**. The AIP (mirror) AD 2.12 remark reads "Blast pad: 120×75m on the both ends" for
18R/36L and "60×60m" for 18L/36R, and `build_airport.py` already builds the rings as `bl, bw = blast_pad_m`.
- `js/live/markings.js` read the pair as one length per end (`[j]`) in Phase 2 and in the L1 fix, which gave 75 m at
  36L. Review L1 and the markings hand-offs then treated this as an AIP-vs-measurement conflict to record.
- There is no conflict. The measured 120 m at both 18R and 36L agrees with the AIP.
- Changed in `markings.js`: it now reads `[0]` at both ends. The chevrons are unchanged (the length is the surface
  ring, 120 m); `padSrc` for 36L now reads "= AIP (mirror) 120 m". The `geo.js` comment now says `blastPad`
  [length, width].
- I did **not** record the requested conflict in `airport.md` or `standards_refs.md`, and I did not change the
  `build_airport.py` evidence string: its current text is correct, and the requested one ("AIP 75 m") came from the
  misreading. Both docs now state the length × width reading.

**Not applied (not small, or optional), for round 2:**
- Aircraft and GSE lit by the apron flood. Every object / model program would need the airfield map texture and
  `sha_apron_flood`; this is not a one-line change.
- Per-mast flood pools from `SHA.qa.masts()` instead of the even flood.
- A `uAirsideFill` mask so the asphalt fill gets the flood.
- Feathering the S2 hint's alpha in `tools/terrain/s2_ground_hint.py`. This regenerates data; `featherS2` covers it
  for now.
- Matching the bank-kerb colour to the new water colour (cosmetic).

### F3. Scenes, tests, frame time

**Scenes**, with a real relay (`sha_live_server.py --port 8792`, METAR / TAF on, ADS-B off):
`SOFTGL=1 RELAY=http://127.0.0.1:8792 SCENES=snapshot,live,offline,park,standalone node livetest.mjs jobs/integration.mjs`.
All five are **clean**: 0 errors, 0 warnings, 0 page errors, 0 HTTP ≥ 400, 0 failed requests. The offline scene has
only its expected 503 line.

| Scene | Pill / note |
|---|---|
| snapshot | "Snapshot · 20 Nov · 12:15 UTC+8"; METAR 0400Z CAVOK Q1027 13/-5; north flow, arr 36R, dep 36L |
| live | "Live weather · METAR 0300Z" (320° 4 m/s CAVOK Q1030 14/-2) |
| offline | "Relay offline · snapshot 20 Nov, 12:15" |
| park (`233,230,113,404`) | "DEBUG ?park=: 4 static aircraft (not traffic)" first, then METAR and runway lines |
| standalone | live, with every file served from the relay's allow-list |

Every scene logs the same world: 164 stands, 56 bridges, 56 VDGS (52 posts, 4 facade), class reference docks 54 / 56,
73 masts, airside fill 2 rings, 41 building parts. Build times: ground 1.18-1.38 s, runway paint set-up 0.44-0.50 s,
gates 0.81-0.89 s plus masts 0.17-0.20 s, terminals 0.18-0.23 s.

Upstream during this step (about 41 min of relay uptime): aviationweather.gov 2 METAR and 2 TAF requests (one TAF
answered 304). adsb.lol: none. OpenSky: never.

**No-browser tests: all pass.**
- `test_geo_js.mjs`: 1681 grid + 50 data points; data 6.6 mm.
- `test_relay.py`: 7 / 7.
- `test_metar_zsss_js.mjs`: 0 decode differences on 69,104 IEM reports.
- `test_buildings3d.mjs`: arch crest 27.30 / eaves 20.30 m, palette, airside fill, 0 / 539 fixed-link points off
  pavement.
- `test_frame.py`: OK.
- The edited modules pass `node --check`.

**Frame time on llvmpipe** (reference only; `SCENES=perf TIERS=low,high`, 1280 × 720 viewport, fixed resolution, 40
frames after 10 warm-up), median / p90 ms:

| Tier | Overview | T2 | Stand 233 | Phase 2 (same views) |
|---|---|---|---|---|
| low (1024 × 576) | 1150 / 1217 (js 2.8, 201 draws, 738 k tris) | 1017 / 1067 (127, 583 k) | 933 / 967 (108, 677 k) | 1183 / 1050 / 983 |
| high (1280 × 720) | 1517 / 1617 (js 3.0, 201, 737 k) | 1567 / 1633 (127, 582 k) | 1533 / 1600 (108, 676 k) | 1683 / 1550 / 1567 |

The fixes add no draw calls (the masts are merged) and no measurable frame cost on llvmpipe; the differences are
within run-to-run noise (±10 %).

### F4. Named views (re-rendered, all 25 looked at)

The commands are the ones in §6 above (the separate `t2pier` re-render is not needed: `@full` includes it). Day views
are at the snapshot instant; night at 21:30 local; laptop views are live (relay METAR 0330Z, 11:42-11:47 UTC+8).
- **Parking.** All 8 bridge stands dock (229 A333, 230 B77W, 231 / 233 / 113 / 115 B738, 234 A320, 102 B77W). 403
  and 404 get stairs and buses. The bridge models picked for some stands changed because the cab points moved (gates
  M5), e.g. 230 AT3 47/85.
- **Orientation checks:** T2 west, T1 east, runways N-S (ok).
- What I saw, per render:
  - **overview**: varied context blocks, grey roofs, dark green-grey water, no ring at the extent edge, CAVOK haze.
  - **rwy_18L / 36R**: 12 stripes, pad chevrons (the cut first one), small "L 18" / "R 36" glyphs.
  - **rwy_18R / 36L**: 16 stripes, five DTHR arrows clear of yellow.
  - **t1 / t2 / tower**: grey metal roofs, T1 hall arch, masts on the aprons.
  - **towercab**: across the T1 apron and both runways to T2; head terrace in the lower right.
  - **stand_233 / bridge_230 / stand_102 / stand_113**: docked aircraft, asphalt under the fixed links and rotundas
    (no brown strip). In `stand_233` a mast stands in the near foreground and splits the frame.
  - **stand_404**: see F4.1.
  - **hold_H1**: unchanged and correct.
  - **t2pier**: five docked aircraft, asphalt at the pier tip.
  - **night_t2pier / night_stand_233**: lit apron, warm glazing with dark mullions, glowing mast heads. Aircraft and
    GSE are dark silhouettes. In `night_stand_233` the near mast's lamp glow is a ~220 px disk.
  - **night_hold_H1**: black except the signs (no airfield lighting, as labelled).
  - **phone views**: "UTC+8", credit strip readable, "T2 APRON 2" card, legend lists the masts and "Idle airstairs:
    20".
  - **laptop views**: "Live weather · UTC+8", the card clear of the credit strip, DEBUG line first.

Evidence images from this step (deviceScaleFactor 1 renders, composited):
- `fix1_integration_envelope_233.png`: envelope shift at 233.
- `fix1_integration_edge_stands_404.png`: Phase 2 / now / top view at the west remote apron.
- `fix1_integration_extent_edge.png`: the context-line fade at the extent edge.
- `fix1_integration_thresholds.png`: stripe crops from the final `view_rwy_*`.

Check renders are in `out/fix1/integ/` (gitignored).

**F4.1 New integration finding: an OSM apron gap ahead of the edge stands.** At 286-290 (T2 remote) and 401-413 (west
remote apron) the paved surface ends 0-1.5 m ahead of the stop node (`pavedAt` along the heading).
- Under the nose-wheel convention the class C noses there reach about 4-5 m over the unpaved band.
- The shifted red envelope fronts and the 设备区 boxes are painted on the band (the decal shader has no pavement mask),
  and the six idle-stair groups there find no spot.
- The three west-remote masts also stand on it (`pavedAt` 0).
- The Sentinel-2 hint reads the band as neutral grey: 134-171 in the 8-bit hint, against 170-206 on the apron and
  about (93, 98, 89) on real grass further out. It is probably paved, a gap in the OSM apron like H2.
- Phase 2 already showed the boxes and the nose at this edge; the convention moves them about 5 m further
  (`fix1_integration_edge_stands_404.png`).
- Proposed for round 2: extend the airside fill (`build_buildings3d.py`) or add an inferred `apron_fill` in
  `build_airport.py` over the S2-paved strips ahead of these stand heads.

### F5. Files changed in this step and safe to commit

- Code:
  - `js/live/caac_decals.js`: envelope shift.
  - `js/live/caac_markings.js`: `separation`.
  - `js/live/gate_system.js`: imports table 4.9.5.
  - `js/live/markings.js`: `padAip` [0].
  - `js/geo.js`: comment only.
  - `js/shaders/ground.js`: `extF`.
- Docs: `CLAUDE.md`, `docs/phase1/airport.md`, `docs/phase1/standards_refs.md`, `docs/phase1/stands.md`,
  `docs/phase2/markings.md`, `docs/phase2/gates.md`, `docs/phase2/integration.md`.
- Renders: the 25 `docs/phase2/view_*.png` (re-rendered) and the 4 `docs/phase2/fix1_integration_*.png`.

Together with the fixers' files (their reports list them), everything in `git status` under `sha3d/` is safe to
commit:
- `js/**`, `data/**`, `jobs/**`, `tools/**`, `live.css`, `docs/**`;
- the 18 `fix1_markings_*` / `fix1_buildings_*` / `fix1_gates_*` images (13 MB).

None of it holds secrets, per-flight data, AIP lists or third-party imagery. The AIP remark quoted in `airport.md` and
`markings.md` is one short cited fact, labelled AIP (mirror). Do **not** commit `out/` (it holds the check renders and
the relay state).

### F6. Open issues after this round

1. **Edge stands 286-290 / 401-413** (F4.1): the OSM apron gap ahead of the stand heads. Noses, envelope fronts,
   equipment areas and three masts sit on an unpaved band; 6 of 26 idle-stair groups have no unit.
2. **Aircraft and GSE are not flood-lit** at night, so they show as dark silhouettes on the lit apron (deferred
   hand-off). Airfield lights (centreline, edge, stop bars, RGL) are Phase 5; `view_night_hold_H1` stays dark, and the
   legend and About say so.
3. **Masts close to the camera.**
   - A mast on the rotunda line stands in the near foreground of the stand-233 cameras (`view_stand_233`, phone,
     laptop).
   - At night its lamp sprite draws a ~220 px glow disk (`view_night_stand_233`).
   - Proposal for the gates package: cap the sprite's screen size or fade the glow within ~40 m of the camera, or move
     the named camera.
4. The designation numerals are 3-4 px tall in the threshold views. The ZSSS size is not observed; 6.2.2-4 allows 2×
   (markings).
5. Carried from the package reports:
   - buildings: the T2 north strip, the T1 hall offset against photo 02, the tower terrace covering about 15 % of the
     cab view, and `featherS2` costing about 150-200 ms of start-up;
   - gates: the Phase 1 bridge rules still on the old cab, no masts at 333-337, 4 facade VDGS units and 2 turned rest
     poses not re-reviewed close up;
   - markings: whether the lead-on parallels beside the DTHR arrows are painted is unobserved; the decal build takes
     0.58 s;
   - the open issues of §9 above (model loading under llvmpipe, phone frame time unmeasured).
