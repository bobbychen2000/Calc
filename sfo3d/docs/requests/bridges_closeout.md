# Bridges track close-out (review 2026-11-04): requests to the other tracks

## Round 2 API for realtime (js/live/gates.js, 2026-11-05)

For bridges-v1 (the 6 s hold cap of traffic.js vs a retraction at the datasheet's rates: bridge.orphan 313 -> 4,654
frames). The real bridge is retracted BEFORE the push-back; ADS-B shows a departure only once the push has begun. So the
retraction should start on an earlier signal, and the body needs to be held only until the cab is out of its push path -
not for the whole retraction. `gateSys` = app.js's `LiveGateSystem`; `G` = `bridgeGate(g)` (the stand whose bridges dock).

| Call | Returns | Meaning |
|---|---|---|
| `undockEarly(G, now)` | s until `extension(G)` is 0 | The engine's EARLIEST departure signal, while the aircraft is still parked (end of SFO's allocation window, the transponder / callsign appearing at the stand, ... - your choice). Starts the normal retraction at the sheet's rates (incl. the 3 s per-motion allowance). Afterwards `G.acType` is null, `G._early` holds the occupant (type, pose, icao) and the GSE has left. |
| `redock(G, now)` | s until docked | A false signal: every bridge reverses from where it is along the way it came (no jump); a hurried one along its tail (the rest of the path it was hurried on, kept through a second hurry). Second pass: it is `setOccupant(G, sameType, true, now, samePose, icao)`, which does the same after ANY undocking (early, normal or hurried) - see the note below the table. |
| `hurryUndock(G, s, now)` | s the retraction takes | The push is seen with the bridge still out: the retraction continues from where it is, along the same path, at the sheet's MAXIMUM rates - cab pivot <= 27 m/min at every instant (segPeak), cab 145 deg/min, lift 1.09 m/min, no per-motion allowance. From docked 16-91 s, p50 27 s. `s` is only a slower floor (never squeezed). Already called by app.js `applyGate` after `setOccupant(G, null)` with `opt.fast`. |
| `pushClearEta(G, now)` | s until every bridge is clear of the occupant's straight push-back | **The only hold the body needs.** Body = gates.js `acHit` (fuselage box section with the tapered nose, wings, engines, swept tailplane; `boxHitsSwept`) swept backward along its heading by L + 15 m, 0.3 m clearance, against every bridge part along its running retraction (or, with none running, the one `hurryUndock` would start now). From docked at the maximum rates over 2,883 stand x type dockings: p50 1.0 s, p90 1.6 s, p99 4.7 s, max 25.2 s (F13 L2 A333 / A339; F15 B779 24.4 s; B11S B736 11.3 s); 0 dockings clear only at rest. |
| `undockEta(G, now)` | s until `extension(G)` is 0 | The whole retraction (running, or the one `hurryUndock` would start now) - for display / releasing the gate, not for holding the body. |
| `dockEta(G, now)` | s until docked | 0 when no docking runs. |
| `extension(G)` | 0 .. 1 | Unchanged: 0 as soon as the tunnels are back at rest (the cab's height settle afterwards, `gateSys.settles`, needs no hold). |

**Second pass (2026-11-05, review round 2 v5): no docking ever jumps.** `setOccupant(G, type, true, now, pose, icao)` while
the bridges are not at rest - a retraction running (early, normal, hurried), a docking to another pose running, or docked
to another occupant (a replacement without a `null` in between) - goes on from where each bridge is (`dockFrom`): the
same occupant (type, designator, freighter flag, pose within 5 cm / 0.1 deg, angle wrapped) back along the way it came,
at once; another pose / aircraft after the usual 12 s, straight to its new stand-off point and in to the door when that
path is clear of the aircraft, else back to rest and along its normal docking path; a bridge that does not dock it goes
back to rest. Every new plan starts at rest (so an undocking / hurry during it retracts along the same path) and runs at
the sheet's rates, never faster. Contract (scratch `jump.mjs` of the verifier, every stand x accepted type at its stop,
2,875 dockings): early undock -> 40 % -> re-dock with the pose 10 cm off; normal undock -> 30 % -> same occupant; undock
-> hurry -> same occupant; early -> hurry(5) -> hurry(600) -> redock: 0 pose jumps > 5 cm in all four (HEAD code on the
same files: 2,874 / 2,086 / 2,875 jumps, max 8.26 / 2.56 / 9.63 m; the fourth had 0.25 s steps of up to 10.5 m in all
2,875), steps <= 0.11 m per 0.25 s; a replacement docked A -> B without a `null`, and A undocking -> B, at 103 stands:
0 jumps (HEAD 102 each, up to 27.3 / 15.4 m), all end at B's door;
`api.mjs` unchanged (0 jumps; pushClearEta p50 0.96 / p99 4.67 / max 25.19 s). No engine change is needed.

Integration (traffic.js / app.js / tools/live/invariants.mjs are yours):
1. Hold: replace `holdBridge = bridgeK(gate) > 0.01` + `HOLD_CAP_MS` with `pushClearEta(G, now) > 0` (expose it like
   `traffic.bridgeK`). Then the body is held at most 25 s (p99 4.7 s), never moves through a bridge, and the bridge's
   remaining retraction runs behind it at the sheet's rates (no squeeze). Drop the app.js fallback that squeezes
   `a.dur = s * 1000 * k` (gates.js has `hurryUndock`).
2. Early signal: call `undockEarly(G, now)` when it fires; the aircraft stays drawn on its stand. While `G._early` is set
   the app's occupancy sync must not re-dock the same aircraft (a `setOccupant` with the same type and pose = `redock`,
   i.e. the signal is cancelled). When the push is then seen, `setOccupant(G, null, ...)` starts nothing new (the stand is
   already empty for gates.js) and `hurryUndock(G, s, now)` speeds up the rest.
3. Contract test (scratch `api.mjs`, every stand x accepted type at its stop): early undock -> 40 % -> redock, and normal
   undock -> 20 % -> hurry -> 50 % -> redock (chained): 0 pose jumps > 5 cm, 0 steps > 0.3 m per 0.25 s; 44 s for all.
   `pushClearEta` is memoised per docking-in-progress for 0.5 s (it re-plans the hurried path); otherwise it reads cached
   plans and is cheap per frame.

From: owner of `js/live/gates.js` (bridge geometry / animation, VDGS, GSE), `js/world/gates.js`, `js/shaders/ground.js`
(threshold bars / runway paint). Numbers: the reviewer's numeric check `bcheck.mjs` (131 bridges, every accepted type at
its `type_stops` stop, incl. alternative positions), re-run before / after this round; GSE also with an independent check
that samples every vehicle MESH (`gse.mjs`). Scratch scripts are not committed; the numbers are quoted here.

| Check (131 bridges, 3,373 bridge x type dockings) | Before (HEAD 90a1f0c) | After |
|---|---|---|
| bcheck issues (critical / major / minor) | 8 / 0 / 1 (F15 L1 path through L2's connector; A15 walkway in the pier) | 0 / 0 / 0 |
| dockings made / refused | 3,282 / 91 | 3,273 / 100 (+9: F15 L1 737 family + B744, static §1) |
| drums narrower than 1.5 m | 6 (min 1.11 m) | 0 |
| docking path steeper than 1:4 at any point | 28 (max 1:2.9) | 0 (max 1:4.0) |
| rest after an undocking steeper than 1:4 / 1:12 | 208 / 1,679, for hours | 0 / 1,671 for p50 33 s, max 133 s, then 0 |
| fast undocking (5 s request) pivot speed / cab rate p50 | 1.97 m/s / 456 deg/min | 0.45 m/s / 92 deg/min (sheet: 0.45 m/s, 145 deg/min); 16-93 s, p50 26 s |
| VDGS facade units without a wall behind | 3 (A13, G10, G13) | 0 (82 posts, 21 facade, 0 blocked) |
| GSE, all 106 stands occupied (largest type) | belt loaders 0, catering 20, fuel 21 | belt loaders 79, catering 11, fuel 37; 0 conflicts (mesh-sampled) |
| docked slopes > 1:12 / > 1:8 (all; observed) | 953 / 380; 102 / 29 of 535 | unchanged (heights: static §5) |

Snapshot render (llvmpipe, 800x500, B-pier tip as in the review): no page errors. The snapshot's 7 parked aircraft got 10
belt loaders, 2 catering trucks and 2 fuel trucks, with no part visibly clipping.

## What changed in gates.js (for everybody who reads it)

| Item | Now |
|---|---|
| Rotunda drum | never below `DRUM_MIN` = 1.5 m (the corridor it carries is 2.4 m wide). A rotunda closer than that to the outline, another bridge's fixed walkway (+0.1 m) or drum is moved by the deficit (G10 L1 0.21 m off G10 L2's walkway). Before: G10 L1 1.11 m, F15 / G12 1.39 m, F22 L1 1.38 m. |
| Fixed obstacles | `jointOk()` / `pathHits()` reject any pose whose rotunda corridor, tunnels, drive column or cab pass through another bridge's fixed walkway, drum or pedestal, or whose tunnels / column / cab pass through the bridge's own fixed walkway. F15 L1 no longer docks the 737 family / 744 (its corridor swept through F15 L2's twin connector); those 9 dockings stay at rest (`docks()` false, `why` names the parts). |
| Twin heads (F15, G12) | both drums on one floor level; the connector between them is level and closed against the first drum (before: 0.7 m floor step, 0.25 m gap). |
| Undocking | the cab keeps the door height only within 1:4 along the way back, then settles to the rest height `h0` (rest tunnel <= 1:12) at the sheet's 1.09 m/min (`gateSys.settles`; `extension()` is 0 as soon as the tunnels are back - the engine does not wait for the settle). |
| `hurryUndock(g, s, now)` | NEW (realtime_round2.md §1a): restarts the current undocking from where the bridges are, along the same path, at the sheet's maximum rates (27 m/min, cab 145 deg/min, lift 1.09 m/min, no 3 s allowance per motion) - in `s` seconds when that is slower, never faster. Returns the seconds it takes. app.js / invariants.mjs already call it when it exists. |
| Docking paths | the retract-swing-extend path keeps the rest height until the final extension (it put the door height on the fully retracted tunnel: 1:2.9); the stand-off point is clamped to 1:4. |
| Reach | strictly >= the operational retraction (sections() cannot telescope shorter); the 0.3 m-short-of-mechanical allowance beyond the operational extension is kept and documented as an inference (see static §3). |
| `solids()` | adds `drive_ctrl`, `pca`, `pca_basket`; the `column` box is 1.6 m half-wide (cross beam). |
| VDGS | facade units only where a pier / hall wall behind them (0.6-3 m) reaches above the unit; else posts (A13, G10, G13 now on posts at 12 / 9 / 12 m). |
| GSE | belt loaders on the sourced lower-deck sills (737: 1.55 m conveyor, A320 family: 2.05 m; js/world/gates.js `BELT_SILL`, new mesh key `beltLoaderA`), conveyor end on the sill at the fuselage side; every vehicle's mesh hull is sampled with heights (elliptical fuselage) and checked against the other vehicles too. |
| Bridge fields for tools | `b.rotShift`, `b.walkNudge` (A15 L1 1.6 m), `b.restTurn` (F5 L1 3 deg), `b.restBlocked`, `b.twinOf`, `b.HrPinned` (rotunda floor on the edge of the 1:12 walkway band from the inferred departure level), `b._obs` (obstacles). |

## 1. Static geometry (`data/sfo_stands.*`, `tools/stands/*`, `js/live/airport.js`)

1. **F15 / G12 twin rotundas** (OSM nodes 3.38 / 3.39 m apart; `rotunda_twin_of`): is this ONE physical rotunda (one
   drum, two tunnels) or two? With two drums of 1.5 m and the connector between them, F15 L1's corridor cannot turn to
   the 737-family docking direction (59 deg from the connector; it clears only beyond ~64 deg), so F15 no longer docks
   B736/B737/B738/B739/B37M/B38M/B39M/B3XM/B744 with L1 (B39M observed at F15). A sourced answer (imagery, a photo, an SFO
   drawing) decides; if one rotunda, give it one `rotunda` point and gates.js docks both from it.
2. **Rest / docked poses folded back onto the bridge's own walkway**: the data's poses of A12, F5, F14, F17, F19, F21
   L1 turn the tunnel to 41-45 deg from the bridge's own mapped walkway (`stow_from_walkway_deg` 135-139). A 2.4 m
   corridor meeting a 2.6 m walkway at 45 deg overlaps it out to ~3.3 m from the rotunda centre, so gates.js tolerates
   the overlap of the rotunda corridor (the junction) but not of the tunnels; F5 L1's rest pose was turned 3 deg for
   that. Please check the last walkway segment / rotunda position of these six against NAIP (the walkway probably bends
   into the rotunda, or the rotunda sits elsewhere).
3. **Reach beyond the operational extension**: 199 of 3,282 dockings use 0-1.05 m of the over-travel between the
   sheet's operational extension and its mechanical stop (worst A1 L2 B789 42.21 vs 41.381 m). gates.js allows up to
   0.3 m short of the mechanical stop (inferred). The data's `model` is the inference ("smallest-retracting model
   covering the observed dockings"): please pick a model whose operational range covers the stops, or record why not.
4. **Optional 185 deg cab** (`cab_option: 'optional 185 deg cab needed (inferred)'`): 17 dockings turn 38.7-48.2 deg
   ccw (standard 32.5). The sell sheet gives no cw/ccw split for the option; `tools/stands/check_stands.py` models it as
   150 deg, gates.js as +-92.5 deg - please make them agree and cite the split if one is found.
5. **Heights (bridges_static.md #7, still open)**: all 107 observed dockings steeper than 1:12 (worst F5 L1 B738 1:2.4
   not docked, G8 L1 B38M/B39M 1:4.4, D11 L1 CRJ9 1:5.0, G4 L1 B738 1:5.4, E6 L1 E75L 1:5.5) are on bridges whose
   rotunda floor sits on the lower edge of the 1:12 band of a 1.3-3.0 m walkway from the INFERRED 5.4 m departure level
   (`b.HrPinned`). Taking the rotunda height from the observed types only (review suggestion) changes nothing for them
   (102 -> 105 of 534 steeper than 1:12, steepest 1:4.4 both ways). Only sourced departure levels / rotunda heights at
   the D, E, F, G piers can fix this; F5 L1 (`short_unit`) and G7 L1 E75L (1:3.9) stay undocked until then.
6. **F11 L2 to a 777 / 787-8 / A330-200**: from the data rest pose (`stow`, -16.6 deg) every swing to the docking
   direction (-133 deg) passes over the parked aircraft's wing / engine - tried direct, retracted, at rest length, half
   and fully extended. The OSM parked cab (-68.6 deg, 11.6 m from `stow`) would leave a 65 deg swing; please re-check
   `stow` there (it is also review finding "rest poses far from OSM").
7. **Rest poses vs the imaged parked pose** (review): stow vs OSM parked cab median 0.38 m but G13 30.9 m, F15 L2
   23.3 m, B15 22.2 m, F22 19.0 m, F11 11.6 m, G8 8.4 m, A11 7.8 m, G5 7.3 m, G6 6.8 m, G9 / G10 6.3 m (overlays
   out/rev_bridges/ov_*.png). Where the OSM parked pose clears every type the stand accepts at its stop, please use it as
   `stow`, or record why it was moved. gates.js draws `stow` as given.
8. **A15 L1 walkway** (bridges_static.md #2): its second segment ran along Boarding Area A with half its width inside the
   pier for 4 m; gates.js now moves the interior vertex 1.6 m out (within the 1.3-2.1 m OSM roof lean of
   `bridge_geom_note`). Please re-trace it so that the nudge is no longer needed.
9. **Still open from bridges_static.md**: #1 / #1b (B2 L1 rotunda 1.47 m, F9 L1 0.49 m moved off the outline), #3 / #4
   (A6 upper-deck bridge 47.2 m from U1L, beyond AT3 72/150's mechanical 43.7 m; A11 upper rests as AT2 41/55 and
   cannot reach U1L at 27.3 m - so 2 of the 3 upper-deck bridges never dock the A380), #5 (pass `bridges_upper` from
   `standGates()`), #6 (rotunda centreline), and the rotunda / walkway NAIP offsets of the drawing pipeline
   (out/draw_bridges/deviations.json: rotundas median 2.9 m off, walkways 2.5 m, low confidence).

## 2. Real-time (`js/live/app.js`, `traffic.js`, `tools/live/invariants.mjs`)

1. **Trigger the undock earlier instead of compressing it.** `hurryUndock(g, 5)` now takes 16-93 s (p50 26 s) at the
   sheet's maximum rates (it used to be squeezed into 5 s: pivot p50 2.0 m/s vs the sheet's 0.45 m/s, cab p50 456
   deg/min vs 145). The real bridge retracts before the push-back; please start the undock on an earlier signal (end of
   the stand's SFO allocation window, beacon / engine start, ground-frequency push clearance where available) and keep
   the 5 s request only as the late fallback. The squeeze fallback in app.js / invariants.mjs (`a.dur = s * 1000 * k`)
   can go.
2. `extension(g)` is unchanged (0 when every tunnel is back); the cab's height settle after it runs on its own
   (`gateSys.settles`) and needs no hold.
3. **UAL1180 B77W (a21dc4) drawn inside the terminal at G8 while being towed / pushed** (replay 17:48-18:25Z): it meets
   G8 L1's tunnel at rest (1,097 frames) and the building (1,018 frames). It is the aircraft pose, not the bridge: please
   keep a towed / pushed aircraft on pavement and out of the building outline.
4. invariants.mjs: use `gsys.solids(g, b, k)` and `gsys.bridgesOf(g)` (incl. the 3 upper-deck bridges) and `doorOf()`
   (bridges_realtime.md §3, still open).

## 3. Tools (`jobs/extract2d.mjs`, `tools/drawing/*`)

bridges_tools.md #1-#6 are still open (the review found `dispBar [-3.05, 0]` and the string check `band(xt, -3.05, 0.0`
stale, the 3 upper-deck bridges never audited, ENVELOPE at the stand nose instead of `type_stops`). The review's NAIP
profile confirms the bars: imaged centres +1.0..+2.0 m on the landing side at all 8 ends vs the model's +1.52 m. New
for the audit: `solids()` now also returns `drive_ctrl`, `pca`, `pca_basket`; belt loaders come in two mesh keys
(`beltLoader`, `beltLoaderA`); `b.HrPinned` marks slopes that come from the inferred departure level; `docks()` false
now also means "the path would pass through a fixed walkway / drum".

## 4. Engine (three.js, `js/three/ground.js`)

bridges_engine.md #2 is still open: `js/three/ground.js` draws the blast-pad chevrons at 15.0 m / 29.7 m, the WebGL2
shader (`js/shaders/ground.js`) at the NAIP-measured 17.0 m / 30.48 m (AC 150/5340-1M Fig. A-9: 100 ft). New vehicle
mesh key `beltLoaderA` comes through `items()` like the others (js/three/bridges.js handles any key).

## 5. Aircraft (`js/aircraft/fit.js`)

The 737-800 family cab docks at the rendered door's 3.12 m floor, Boeing publishes 2.59-2.74 m (NG) / 2.77-3.07 m (MAX)
(types.js `NG_CL.sill`; fit.js documents it as a model-door deviation). Please re-seat or fix the model door so that the
cab height is the published sill (bridges_aircraft.md: `T.dockX3` / `dockSill3` / `dockHW3` for the A380 also open).

---------------------------------------------------------------------------------------------------------------------

# Round 2 (fix round of wf_41410c83, 2026-11-05): what changed, numbers, requests

(The numbers below are as of that fix. Since then the static track moved the 31 rotundas in the data (P6) and the
aircraft track re-cut the 737 door-1 sill / MAX stance; on today's files they are superseded by "Round 2, second pass"
at the end of this file - review round 2 bridges-v11.)

Numbers: the verifier's `bcheck2.mjs` (131 bridges, every accepted type at its `type_stops` stop), `hurry_peak.mjs`,
`ownneck.mjs`, the mesh-sampled `gse.mjs` (scenario A: every stand with its largest type; B: a 737 / A320-family type),
the departure-API contract test `api.mjs` and `tools/sat/check.py`. Before = gates.js of 373de34 (the round-1 result)
on today's data; after = the working tree. Scratch scripts are not committed.

| Check | Before | After |
|---|---|---|
| bcheck issues | 0 | 0 |
| dockings made / refused | 3,287 / 100 | 3,286 / 101 (+ E6 L1 CRJ2, slope 1:3.9 after the rotunda shift; not an observed type) |
| observed (bridge, type) pairs refused | 12 | 12 (same list; bridges-v2 below) |
| dockings beyond the operational extension | 189 (max +1.19 m) | 158 (max +1.02 m) |
| docked slopes > 1:12 / > 1:8 (all; observed) | 975 / 388; 125 / 39 of 605 | 969 / 386; 125 / 39 of 605 |
| hurry retraction: peak drive column / cab pivot | 0.486 / 0.536 m/s (172 plans > 0.455) | 0.450 / 0.450 m/s (0 > 0.455); 16-91 s, p50 27 s |
| bridge poses with a moving part inside the SFO Museum outlines / a sky bridge (rest; docked; path) | 1; 88; 88 (A9 L1, E11 L1 corridors, 3 bridges) | 0; 0; 0 |
| check.py ISSUE A10 L1 / B39M 0.9 m2 (check_stands' 2.9 m tunnel from the data rotunda) | 1 | 1 until the data change of §R2.1 (with it: 0) |
| drums overlapping the SFO Museum outlines (exact discs) | 41 (max A9 L1 4.94 m2) | 0 (31 rotundas moved 0.08-1.37 m; 0 drums < 1.5 m; drawn outlines 0 -> 0) |
| VDGS posts / facade units / blocked | 82 / 21 / 0 | 92 / 11 / 0 (facade units only where they also clear the Museum outline in front of the drawn wall) |
| GSE A: belt loaders / catering / fuel; conflicts | 79 / 11 / 37; 0 | 79 / 26 / 37; 0 |
| GSE B: belt loaders / catering; conflicts | 138 / 0; 0 | 138 / 28; 0 |
| belt conveyor top below the rendered skin at its end | up to 0.38 m (737) | <= 0.024 m |
| start-up `prepBridge` + `finishPrep` (node) / 3,387 plans | 0.8 s / 4 s (13.9 s / 147 s with the sampled Museum test of the killed fixer's WIP) | 0.66 s / 5 s |
| pushClearEta from docked (p50 / p90 / p99 / max) | - | 1.0 / 1.6 / 4.7 / 25.2 s |

## What changed in gates.js / world/gates.js (round 2)

| Item | Now |
|---|---|
| Departure API | `undockEarly`, `redock`, `pushClearEta`, `undockEta`, `dockEta` (top of this file); `hurryUndock` keeps its contract. |
| Path timing (bridges-v6) | `segPeak`: every segment is timed by the cab pivot's PEAK speed (exact for the linear angle / extension interpolation), so pivot and drive column stay <= 27 m/min at every instant. |
| Building clearance (orch-1) | The SFO Museum terminal-complex and boarding-area outlines (data/sfo_airport.js; what the 3-D ITB / domestic assets are built from) are clearance outlines for every moving part (`bldHit`, in `jointOk`, `pathHits`, the rest-pose check) and for the drums (`drumLimits`): 31 rotundas move off them by the deficit for a 1.5 m drum + 0.2 m (<= 2 m, list in static_closeout.md; since P6 the data carries the moves and gates.js shifts 0 - a guard; second pass: a bridge's own walkway strip in those outlines is not building, `ownStrip`); their rest cab stays at the data's stow (moving it with the rotunda put B15 L1's cab in B16 L1's B744 path). Exact tests (edge grid + Liang-Barsky, no sampling): start-up 0.66 s. `inBuilding(x, z, all, drawn)`, `solidInBuilding(box)` are exported for tools. |
| Known clip (bridges-v3) | `b.ownClip = {rest, docked, poses}` (exact plan overlap of the rotunda corridor with the bridge's own walkway outside the drum): A12 L1 0.32 / 0.47 m2 (37/37 poses), F5 L1 0.18 (1/25), F14 L1 0.40 (6/27), F17 L1 0.45 / 0.46 (6/27), F19 L1 0.45 / 0.52 (6/14), F21 L1 0.56 (5/26). Listed as a data clip, not an accepted junction (static_closeout.md). |
| Stair side | penalties weighted by how long a pose lasts (rest x10, docked x4, path sample x1): G7 L1 (rotunda moved 0.8 m) no longer rests its stair in G7 L2's drum. |
| Tailplane solid | `acHit` 'tail' beside the fuselage is the swept, tapered planform (was the whole rectangle from the root LE station aft): catering trucks at narrow-body door 2 are possible (0 -> 28 in scenario B), 0 mesh conflicts. |
| Belt loaders (bridges-v7) | per family AND door (published sills, `BELT_PUB`: 737 fwd 1.30-1.45 / aft 1.63-1.80; A320 family fwd 1.81-1.93 / aft 1.91-2.08), raised to at least 0.3 m above the rendered model's lowest skin (`beltSill`), one mesh per 0.05 m setting (`belt190`, `belt195`, `belt205`, `belt210` today: the fitted models' skin decides, see §R2.4). Keys `beltLoader` / `beltLoaderA` are gone (the old offline `GateSystem` keeps `beltLoader` / `catering`). |
| Catering trucks (bridges-v7) | box lifted to the door-2 floor (`cateringFloor`: T.dockSill2, else door 1's rendered sill + the model's nose-down pitch over the door spacing; 0.2 m steps, >= 2.8 m), hull = chassis, cab, column, box (`cateringBoxes`); 10 mesh keys `catering300` ... `catering520`. Before: one box at 3.6-6.2 m - 1.4 m under a 777's door 2. |
| VDGS | the facade is the drawn outline (`inBuilding(.., drawn)`); a unit / post must also clear the Museum outlines and sky bridges (`solidInBuilding`). (Second pass: the unit goes on the OUTER face - the Museum ring where it lies in front of the drawn wall - with a bracket back into the drawn wall.) |
| Comments (bridges-v9) | header, `extension()`, `setOccupant` (undocking: door height only within 1:4, then the settle), `hurryUndock` (measured 16-91 s; the hold is `pushClearEta`). |

## R2.1 Static (also written to docs/requests/static_closeout.md "From bridges, round 2")

orch-1 root cause = stand data, not the path or gates.js: A10 L1's `rotunda` (OSM node 1096422734, a roof trace with
relief lean: `geom_src` "likely ~1.3-2.1 m east of the true structure") is 0.77 m from the SFO Museum Boarding Area A
outline; check_stands' 2.9 m tunnel from that centre grazes the outline 2.6-6.5 m out (0.85 m2 for B39M / B38M / B738 /
B739 / A321 / A21N - beyond the "graze next to the rotunda" tolerance), the cab is clear (0.00 m2). Exact change and its
check: static_closeout.md. bridges-v2 / v4 / v5 / v9 (observed types refused, heights, stow vs OSM, over-extension and
the optional-cab split) are unchanged data questions - same requests as §1.1-§1.9 above, numbers updated there.

## R2.2 Realtime

- bridges-v1: the API above. The replay A/B (orphan frames) has to be re-run once traffic.js uses `pushClearEta` /
  `undockEarly` - gates.js alone cannot change the hold; `hurryUndock` (datasheet rates) stays as it is.
- bridges-v8 (arrival touches at G5, F20, A2, B19 / B20): not bridges. Each bridge involved, at rest and (B19 L1)
  docked to every type it serves, is clear of the arriving stand's accepted types swept straight along the lead-in from
  80 m back to the stop with 0 m margin (gates.js `boxHitsSwept`; scratch `b19.mjs`). The reported positions were 4.4 m
  (B20), 4.9 m (G5) and 12.3 m (A2) off the lead-in at 15-21 m before the stop: the drawn body is off its lead-in or past
  its stop. Please trace those four (`--trace hex`) and keep an arriving body on the lead-in up to its stop; tools:
  invariants.mjs should take `acHit` / `boxHitsAc` (tapered nose) instead of its rectangle.

## R2.3 Buildings workflow (3-D assets; FYI)

gates.js now keeps every bridge part clear of the SFO Museum outlines (the ITB `rotunda_contacts` of the manifest: 0 now
for the drums). Where the domestic asset trims narrow strips that carry fixed walkways (dom_geom.py CORE_OPEN), the
Museum outline is stricter than what you draw - no conflict. If an asset draws a facade OUTSIDE the Museum outline, the
bridges do not know it: give gates.js that footprint (or tell us) before it is drawn.

## R2.4 Aircraft

The belt loaders and catering boxes now follow the RENDERED fuselage (lowest skin, door-1 sill, pitch): the 737 conveyors
sit at 1.90-1.95 m (published sills 1.30-1.45 fwd / 1.63-1.80 aft) because the fitted 737 skin is 1.62 m above the apron.
When the 737 is re-seated at the published sills (§5 above), the conveyors drop to the published values by themselves.

---------------------------------------------------------------------------------------------------------------------

# Round 2, second pass (fix of the round-1 verify findings v1-v11, wf_14fa97a9; 2026-11-05)

Before = gates.js / world/gates.js of HEAD (the round-1 fix, as verified) on TODAY's files (data with static P6, the
aircraft track's 737 sill re-cut and MAX stance); after = the working tree. Same scripts as the verifier (scratch
`vb2/*.mjs`, `verify/bcheck2.mjs`), plus four new independent ones in scratch `br4/`: `colpts.mjs` (walkway columns vs
the 3-D asset footprints of data/buildings3d/integration.json), `drums2.mjs` (drums vs drawn / asset / Museum),
`assetpose.mjs` (every moving solid at rest, docked and along the exact paths - 11,805 poses - vs the asset footprints,
the drawn outline and the Museum rings, plan area sampled at 0.2 m), `vdgsasset.mjs` (facade units vs the asset
footprints) and `tailcmp.mjs` (acHit's tailplane vs model.js's loft). No renders (no visual change beyond the columns,
drums, brackets; a render is left to the visual QA loop).

| Check | Before (HEAD code, today's files) | After |
|---|---|---|
| fixed-walkway columns drawn (posts2.mjs) | 45 (B-pier: 27 dropped on 20 bridges; B26 / B27 L1 spans 42 / 53 m) | 72 = the round-1 set, per bridge identical; 0 inside or within 0.6 m of a 3-D asset footprint (min 2.0 m), 0 within 2.6 m of the drawn outline; 18 stand in the Museum walkway strips (1.8-5.0 m wide) |
| rotunda shifts in prepGeom (data P6) | 0 | 0; with the 9 B-pier P6 moves reverted (static_closeout "From bridges, round 2 second pass"): 0 needed, the other 22 still needed by the same amounts |
| drums vs the drawn outline / the 3-D asset footprints | 0 / 7 (F7 L1 1.06 m, F8 L1 1.05, E9 0.55, E3 0.23, D10 0.17, D14 0.02 m + 1; pre-existing, R2b.3) | 0 / the same 7; 13 B-pier drums grow - B6, B11, B16, B19, B20, B24, B25, B26, B27 L1 from 1.52 to 2.20 m, 0.48 m into their own walkway's strip end (the walkway enters the drum), B13 / B14 / B17 / B18 / B22 L1 by 0.01-0.15 m |
| moving solids in a 3-D asset footprint (assetpose, 11,805 poses) | F8 L1 tunnel1 docked 0.58 m2, path 0.51 m2 (pre-existing, R2b.3) | the same; drawn outline 0; Museum rings 0 (even the own strips) |
| bldpose (gates.js's own outline test, no exemption) | 0 / 0 / 0 (3,278 dockings) | 0 / 0 / 0 |
| VDGS posts / facade units / blocked | 92 / 11 / 0; 4 of the 11 units inside an asset footprint | 83 / 20 / 0 (373de34: 82 / 21); 0 units in an asset footprint, gap to the asset face 0.20-1.14 m bridged by a 0.35-1.07 m bracket into the drawn wall; F5 stays a post (its facade spot lies in the Museum / asset bump around F5 L1's walkway start) |
| re-dock pose jumps > 5 cm (jump.mjs, 2,875 dockings): A 10 cm off / B same after undock / C after hurry / D double hurry | 2,874 (8.26 m) / 2,086 (2.56 m) / 2,875 (9.63 m) / 0 but 2,875 with 0.25 s steps up to 10.5 m | 0 / 0 / 0 / 0; max step 0.11 m per 0.25 s |
| occupant changes without a rest in between (new `swap.mjs`, 103 stands, first / last dockable type): E docked A -> B directly / F A undocking 50 % -> B / G A docking -> undock -> A | E 102 jumps (max 27.3 m), F 102 (15.4 m), G 0 | 0 / 0 / 0, max step 0.11 m per 0.25 s, all end docked at the new door |
| departure API (api.mjs) | 0 jumps; pushClearEta p50 0.96 / p99 4.67 / max 25.19 s | identical |
| hurry rates (hurry_peak.mjs, 3,278 plans) | - | pivot / drive column <= 0.450 m/s (0 > 0.455), cab <= 145 deg/min, lift <= 1.09 m/min, 16.0-91.3 s |
| acHit tailplane LE / TE vs model.js loft (all non-T-tail types) | 0.34-0.90 m behind | <= 0.01 m |
| GSE (gse.mjs, mesh-sampled): A belts / catering / fuel; B belts / catering; conflicts | 79 / 26 / 37; 138 / 28; 0 | 79 / 26 / 37; 138 / 28; 0 |
| belt conveyor below the rendered skin (beltgap) | 0.024 m | 0.024 m |
| rest bridges vs every stand's lead-in (restsweep, 0 / 1 m margin) | 0 / 0 pairs | 0 / 0 |
| ownClip (data, bridges-v3) | A12 0.32 / 0.47, F5 0.18, F14 0.40, F17 0.45 / 0.46, F19 0.45 / 0.52, F21 0.56 m2 | unchanged |
| tools/sat/check.py | ISSUES 0, WARNINGS 17, APP 0 | unchanged |
| start-up prepBridge + finishPrep (node, under load) | 0.64 s | 0.76 s (the own-strip sections) |
| bcheck2 (verifier's, 131 bridges, 3,387 candidates): issues; dockings made / refused | 0 (verifier); 3,278 / 109 (summ.mjs, same list) | 0; 3,278 / 109, the same refusal list |
| observed (bridge, type) pairs refused (bridges-v2) | 12 (slopes.mjs; the verifier's 14 incl. G8 L1 B38M / B39M were before the aircraft track's MAX stance change) | the same 12: A1 L2 B78X; A2 L2 B78X / A35K; A6 / A11 upper A388; F5 L1 B738 / B38M / E75L; F11 L2 B772; F15 L1 B39M; G7 L1 E75L; G8 L1 E75L |
| docked slopes > 1:12 / > 1:8 / > 1:4 (all; observed > 1:12) (bridges-v4) | 1,004 / 406 / 0; 145 of 605; max 1:4.07; HrPinned 108 | identical (the code change moves no rotunda floor) |
| beyond the operational extension; optional-cab ccw max; min telescope overlap (bridges-v9) | 158 (max +1.02 m); 48.2 deg; 1.64 m | identical |

## What changed (second pass)

| Item | Now |
|---|---|
| Own walkway strip (v1, v6) | `ownStrip(W)` per bridge from its mapped walkway + rotunda: a piece of an SFO Museum ring is the bridge's own walkway (not building) when, on the line across the walkway (or one up to the 2.1 m lean along it), every point of it lies within 6.8 m (walkway 2.6 + 2 x 2.1 m lean) of the walkway polyline and some within 3.4 m of its centreline, and the walkway carries such pieces for >= 5 m (BA-B tip strips 6.3-50.8 m; the pier-face bumps around the other walkways' starts, which the assets draw, <= 3.3 m). Exempt: its edges in `drumLimits` (the drum may meet its own walkway), `bldHit` / `solidInBuilding(box, own)` (the moving parts are tested against the walkway slab itself, fixedHit) and the rest-pose test. Found on the 21 B-pier tip bridges only; the asset footprints cover 3-31 % of their strip edges (within 0.5 m of the pier face), 75-100 % of every other candidate (which is why the run length is required). |
| Walkway columns (v1) | `columnOk(b, p)`: not inside an outline (own strip excepted) and 0.6 m clear of the drawn outline and the sky bridges - the round-1 rule plus the Museum rings' insides. |
| Docking from a non-rest state (v5) | `setOccupant` -> `legsNow` / `dockFrom` (API section at the top); `samePose` wraps the angle; `hurryUndock` keeps a `tail` (the rest of the path to the door) through repeated hurries. |
| VDGS (v7) | facade unit on the outer face (the Museum ring where it lies <= 2.1 m in front of the drawn wall), 0.25-1.0 m off it, with a 4-arm bracket back 0.1 m into the drawn wall (`vdgsSpot().bracket`, drawn by `standGeo`); wall height still from the drawn wall; posts as before (search limit ~2.5 m off the drawn wall). `gateSys.vdgsWhy` (array) collects every tried spot and why it failed, for tools. |
| Tailplane solid (v8) | `acHit` 'tail': root at 0.35 R (T-tail 0.2 m) as model.js lofts it; LE x + (|y| - z0) tan(sweep), chord tapering from z0. |
| Belt floor (v8) | world/gates.js `BELT_THICK` (0.3 m, the conveyor's depth): the conveyor's underside stays at or above the rendered lowest skin - the "+0.3 m" is that depth, derived from the drawn geometry, not a source. |
| Tools (v4) | tools/drawing/audit.py: a docked tunnel steeper than 1:12 whose rotunda floor sits on the 1:12 band of the inferred 5.4 m departure level is noted "[inferred heights ...]" (uses `HrPinned` when the scene carries it, else the same test from floorY / fixedLen). |
| Comments (v11) | header (rotunda moves are in the data; the shift is a guard), prepGeom (0 shifts today), the Round 2 table above marked superseded. |

## R2b.1 Static (data/sfo_stands.*; also in docs/requests/static_closeout.md "From bridges, round 2 second pass")

1. **Revert the nine B-pier P6 moves** (B6, B11, B16, B19, B20, B24, B25, B26, B27 L1: rotunda, walk end, `rotunda_src`,
   P6 fixup, B11 / B16 / B20 stow, stow_len): exact table and check in static_closeout.md. Or give P6 the own-strip rule.
2. Unchanged data questions (numbers on today's files in the table above): bridges-v2 observed pairs refused, bridges-v4
   departure levels / rotunda heights (G8 L1 B38M / B39M, refused at 1:3.7 after the 737 sill re-cut, dock again since the
   aircraft track's MAX stance change - the heights decide this, not gates.js), bridges-v3 the six
   folded walkway junctions (A12, F5, F14, F17, F19, F21 L1), bridges-v9 / v5 models for the over-extension, the
   optional-cab split and the rest poses (P7 rejected the 20 OSM poses with reasons) - §1.1-§1.9.

## R2b.2 Realtime (traffic.js, tools/live/invariants.mjs)

- The API is unchanged; re-docking is now continuous in every case (top). Please re-run the all-hours replay A/B
  (`r2/run_inv.sh`) with this gates.js: the 43 early cancellations and every stale replacement now go through `dockFrom`.
- bridges-v8 (bodies touching rest / retracting bridges in the replay: D5 / UAL626 149 frames, A2 / KLM373 38, E9 /
  UAL2262 33, G5 / DLH454 46, F20 L1 vs UAL574): the bridges side is clear (restsweep 0 pairs at 0 / 1 m; b19.mjs clear);
  please trace them (`--trace hex`) and give invariants.mjs `acHit` / `boxHitsAc` (tapered nose, swept tailplane - now
  the model.js planform) instead of its rectangle.

## R2b.3 Buildings workflow (3-D assets) / integration

- gates.js keeps the bridges out of the SFO Museum rings as the proxy of what the assets draw. Where the assets reach
  beyond those rings (the lean-corrected roof edges), the bridges do not know it: drums F7 L1 / F8 L1 overlap the asset
  footprint by 1.06 / 1.05 m, E9 L1 0.55, E3 0.23, D10 0.17, D14 0.02 m; F8 L1's tunnel 1 enters it when docked (0.58 m2).
  Please export the per-building LOD0/1 footprints (integration.json `footprints`) in `data/buildings3d/integration.js`
  (`B3D_INTEGRATION.footprints`), so gates.js can use the real asset outlines instead of the Museum proxy (and drop the
  own-strip heuristic), or trim the asset at those drums.

## R2b.4 Aircraft

- Belt loaders (bridges-v7 / v8): the per-door published sills still do not apply - the conveyors sit on the rendered
  skin (737NG 1.90-1.95 m, MAX 1.75-1.80 m after your stance change, A320 family 2.05-2.10 m vs Boeing fwd 1.30-1.45 /
  aft 1.63-1.80, Airbus 1.81-1.93 / 1.91-2.08): re-seat the 737 / A320 models at the published sills (§5 / §R2.4) and
  they drop to BELT_PUB by themselves.

## R2b.5 Tools (jobs/extract2d.mjs)

- Please export `b.HrPinned` (and `b.ownClip`, `b.rotR`) per bridge in the scene; tools/drawing/audit.py then labels the
  inferred-height slopes from it directly (today it recomputes it from floorY / fixedLen).
