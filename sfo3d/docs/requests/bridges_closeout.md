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
back to rest. (**Corrected in Round 3, bridges-4:** until then the way back to rest and the leg of a bridge that does
not dock the new aircraft were NOT tested against it. Now every leg is - back the way it came, straight back, both also
lifted 1.5 / 2.5 m; to the door direct, via rest or lifted - the first clear one is taken, else the one with the fewest
poses in the body, and a bridge with a part already in the new body starts at once instead of after 12 s. A replacement
without `null` can still leave no clear way out: 2 input-induced cases, R3.3.) Every new plan starts at rest (so an undocking / hurry during it retracts along the same path) and runs at
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
| VDGS posts / facade units / blocked | 92 / 11 / 0; 4 of the 11 units inside an asset footprint | 83 / 20 / 0 (373de34: 82 / 21); 0 units in an asset footprint, gap to the asset face 0.20-1.14 m bridged by a 0.35-1.07 m bracket into the drawn wall (**corrected in Round 3:** not at B2 / C8 - their brackets ended 0.74 / 0.09 m short of the asset face; now they reach it); F5 stays a post (its facade spot lies in the Museum / asset bump around F5 L1's walkway start) |
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

---------------------------------------------------------------------------------------------------------------------

# Round 3 (close-out round 3, fix round 1: findings bridges-1 .. bridges-11 of docs/requests/closeout3_findings.json; 7 Nov 2026)

Before = the committed `js/live/gates.js`, `js/world/gates.js` and `tools/drawing/*` on today's data (frozen copy, scratchpad
`c3/bridges/root_before`); after = the working tree. Scripts: the round-2 verifier's (`vb3/*`, `verify/bcheck2.mjs`, run
with `ROOT=`), the aircraft track's `census.mjs` / `belt_api.mjs`, and new ones in scratchpad `c3/bridges/scripts/`:
`beltend.mjs` (conveyor end vs the placed mesh), `beltmesh.mjs` (every belt-loader mesh sample vs the rendered fuselage
mesh), `fuelmesh.mjs` (fuel-truck hull vs the rendered aircraft mesh, every zone), `signs.mjs` (readability of every sign
quad), `walktop.mjs` (walkway tops per pier), `legacy.mjs` (old-scene closures), `e12b.mjs` (dockFrom cases). No renders
(no Chromium: the heavy lock was busy with the env track; the visual QA loop is on hold).

| Check | Before | After |
|---|---|---|
| dockings made / refused (3,413 bridge x type candidates, slopes.mjs) | 3,304 / 109 | **3,335 / 78** |
| observed (bridge, type) pairs refused | 14 (+ G7 L1 B738, G8 L1 B738 since the 737 stance change) | **10**: A1 L2 B78X; A2 L2 B78X / A35K; A6 / A11 upper A388; F5 L1 B738 / B38M / E75L; F11 L2 B772; F15 L1 B39M |
| docked slopes > 1:12 / > 1:8 / > 1:4 (all) | 1,031 / 406 / 0 | **638 / 194 / 0** |
| observed types > 1:12 | 144 of 610 | **88 of 614** |
| steepest docked slope; HrPinned | 0.2457 (1:4.07); 109 | 0.2499 (1:4.0, G8 L1 A35K / MD11 now refused at 1:4.0 / 1:3.9 - not observed there); 98 |
| 737 / A320 / regional census (planFor, every stand x type) | B738 95 docked, max 0.219, 39 > 1:12; MAX 96, 0.238, 31; A320 96, 0.203, 23; E75L 97; CRJ9 90 | **B738 97, 0.185, 17** (G7 / G8 b0 dock the 737 at the unchanged ACAP sill); **MAX 96, 0.160, 11; A320 96, 0.134, 5; E75L 99; CRJ9 95** |
| fixed-walkway top at the attach point (walktop.mjs) | every pier 8.40 m (BA-G 7.41-8.40) | **BA-G G1-G10 5.71-5.87 m** (bump-out roofs 6.5-7.1; G12 / G13 long tip walkways 6.16-7.29); **BA-C 6.20-6.26, BA-D 6.65** (roofs 7.20 / 8.49); BA-E / BA-F 7.88; BA-A / BA-B 8.40 |
| rotunda corridor through its own walkway (ownclip / ownneck) | 6 bridges (A12, F5, F14, F17, F19, F21 L1), 0.18-0.65 m2 | **0 / 0** |
| conveyor end vs the rendered skin (beltend.mjs, 14 types x 2 doors; belt_api.mjs before) | lateral -0.16 .. +0.88 m (737 NG fwd inside, aft off; MAX fwd 0.28-0.42 off) | **-0.038 .. +0.034 m**; skin directly above the end -0.006 .. +0.002 m |
| belt-loader mesh inside the rendered fuselage (beltmesh.mjs, 79 + 138 loaders) | - (with the new door positions and full-length rails: rails 0.62 m back, 0.29 m deep) | **rails 0; the conveyor's end face <= 0.054 m, only in its last 0.1 m** (it meets the sill: the cargo door is open in reality, drawn closed) |
| GSE (gse.mjs; conveyors tested against the rendered skin, `GSE_SKIN=1`) A / B | 0 / 0 | **0 / 0**, belts 79 / 138, catering 26 / 28, fuel 37 / 36 (with the old unpitched-ellipse test: 61 belt "conflicts" - the very ellipse bridges-3 is about) |
| dockFrom, samples in the NEW body (dockcol.mjs, 206 pairs): E / F / H / Hh / J | 7,718 / 566 / 13,848 / 11,369 / 1,033 | **2,158 / 155 / 6,097 / 5,144 / 473** |
| ... of which a bridge that started clear entered it later (cases) | E 4, F 1, H 4, Hh 4, J 1 | **E 2, F 0, H 2, Hh 2, J 0** (A8 L2 B779 -> E170, E12 L1 A321 -> CRJ2: replacement while docked, no null - below) |
| jump / swap / api (re-dock continuity, departure API) | 0 / 0 / 0; pushClearEta p50 0.96, p99 4.67, max 25.19 s | identical |
| hurry_peak (3,335 plans) | pivot / column <= 0.45 m/s, 16-91 s | identical (15.4-91.3 s) |
| tunnel gate-number signs that read mirrored (signs.mjs) | **524 of 524** (both sides) | **0 of 524** (VDGS / stand signs 0 of 206 before and after) |
| VDGS posts / facade / blocked; arms short of the 3-D asset face | 83 / 20 / 0; 2 (B2 0.74 m, C8 0.09 m) | 83 / 20 / 0; **0** (B2 bracket 0.60 -> 1.37 m, C8 0.35 -> 0.61 m); 0 units / posts hit an aircraft |
| fuel trucks vs the rendered aircraft mesh (fuelmesh.mjs) | - | A 37 / B 36 trucks: 0 inside, min clearance 1.44 / 1.67 m; **D10 B39M 1.76 m** |
| drums vs asset footprints (drums2); moving parts in an asset footprint (assetpose) | 3 (F7 L1 -1.06, F8 L1 -1.05, D3 L1 -0.03 m); F8 L1 tunnel 1 0.58 / 0.51 m2 | the same (plan-only footprints of the BA-F overhang: buildings resolved them in 3-D, see bridges-6) |
| bldpose / restsweep / stair | 0 / 0 / 1 (G7 L1 stair in G7 L2's drum) | 0 / 0 / **0** |
| tools/sat/check.py | ISSUES 0, APP 0, WARNINGS 17 | identical |
| old offline scene (js/world/gates.js GateSystem) closures | flat block 0.4 m past the cab stop (0.25 m into the skin at door 1) | fitted closure (js/aircraft/dock.js) for all 50 fitted types |
| tools/drawing model fit (report.py check: dims after `_stretch` vs the page) | port without tipShear / tipCut / noseExt / engScale / squash / gearUp / fairing | **47 of 47 types within 2 cm** (scene of 5 Nov) |
| bcheck2 (verifier's full check, 131 bridges; before = the committed gates.js on today's data, scratchpad `c3/bridges/bc_before/`; the round-2 verifier's run on the data of 6 Nov had 0 issues) | **32 issues**: 16 critical `dock-restbridge` + 15 critical `sibling-path` + 1 major `rest-bridge`, all the G7 L1 stair through the G7 L2 drum (with the data of 7 Nov); 3,304 made / 109 refused, 14 observed pairs refused; slopes > 1:12 / > 1:8 / > 1:4 1,031 / 406 / 0, observed 144 of 610, max 0.2457; hurry / undock paths > 1:8 509, > 1:4 0; 171 beyond the operational extension; telescope overlap >= 1.64 m; cab turn -84.2 / +48.2 deg | **0 issues** (after-run 1 had 8 major `rest-bridge` - the G13 upper walkway through the G13 L1 / L2 walkways - and `pathGt4` 2; both fixed, R3.0); 3,335 made / 78 refused, **10** observed pairs refused (list above); slopes 638 / 194 / 0, observed 88 of 614, max 0.2499; hurry / undock paths > 1:8 **262**, > 1:4 0 (max 0.24999999991); 171 beyond the operational extension (max +1.02 m, 1 > 1 m; all within the mechanical stroke; unchanged - the round-2 158 differs by the data); telescope overlap >= 1.64 m; cab turn -84.2 / +48.2 deg (20 need the optional 185-deg cab, inferred); VDGS 83 / 20 / 0; path-vs-docked 0; rotShift / swingWide / drumOverWing 0 (scratchpad `c3/bridges/bc_after2/`, 215 s) |

## R3.0 What changed (js/live/gates.js, js/world/gates.js, tools/drawing/*)

| Finding | Change |
|---|---|
| bridges-1 (heights) | `DEPARTURE_LEVELS` (exported): the floor of the fixed walkway where it leaves the building, **per boarding area** instead of one inferred 5.4 m: **G 2.7 [obs, low]** - photo a2 (Commons "Aerial view of San Francisco International Airport station, September 2025", CC BY-SA 4.0) with the ITB group's solved camera: at the G2 / G5 / G6 bridge heads the walkway / drum roofs read 5.5-6.6 m and the tunnels leave the drums at 1.9-2.9 m (1 m ticks projected at the attach points, +0.3-0.7 m for the camera's ground offset at B1; scratchpad `c3/bridges/photo/a2_G_walk2.png`), consistent with the ITB group's "walkway roofs 1-1.4 m under the 6.5-7.1 m bump-out roofs"; **E / F 4.88 [pub]** - Terminal 3 L2 departures 27'-0" vs L1 11'-0" = 16.0 ft (T3W Civic Design Review, 95 % CD, Oct 2023, sheets 5A-A5.01.01/.02, cached; docs/research/buildings_domestic.md §5.1), L1 at the apron [inf]; **D 3.65 [obs, low]** - photo a1 ratios at the BA-D near end (domestic group: concourse glazing 0.44-0.79 of the 8.49 m roof edge, walkways at that band); **C 3.2 [inf]** - the BA-D layout on a1 applied to the measured 7.2 m roof (BA-C is too small on a1); **A / B 5.4 [inf]** - no photo or published level. `b.Hb`, `b.HbTag`, `b.HbSrc` per bridge; the upper-deck walkway level follows (level + WALK_H + 0.6, inf). The 737 sill is not raised (ACAP OEW rows). Upper-deck walkways (A380 U1L): level over the main-deck walkway / drum roofs they cross in plan + 0.6 m (inf) - the old `level + WALK_H + 0.6` assumed level main-deck walkways, and with the low BA-G level the G13 upper walkway ran through the rising G13 L1 / L2 walkways (bcheck2 after-run 1: 8 major `rest-bridge`); G13 upper 9.0 -> 8.44 m, A6 / A11 9.0 m unchanged. |
| bridges-2 (own-walkway clip) | `neckStart` / `neckParts`: the rotunda corridor starts where it leaves the bridge's own fixed walkway (separating axes, 0.06 m), the half away from the walkway from where that half leaves it (it closes the drum / walkway / corridor junction); the `fixedHit` exemption of the corridor is gone (it is tested like every moving part). F5 L1's rest turn 3 deg (unchanged). |
| bridges-3 (belt loaders) | js/world/gates.js `beltDoor` / `beltEndY` read the aircraft track's stance-aware API from `T.fit` (cargo-door object or published station, the drawn door's rendered sill or the type's own published range - MAX ACAP rows D / L - never under the rendered keel; end at the rendered starboard skin + 0.03 m); `BELT_PUB` remains only for the A319 / A320 families (no cargo entry: 0.22 / 0.66 L, inf). Mesh settings to 0.01 m. Side rails stop 0.7 m short of the conveyor's end (`BELT_RAIL_GAP`, inferred). `acHit(..., 'skin')`: the conveyor is tested against the rendered, pitched skin (`T.fit.keelAt` / `skinHW`), every other vehicle against the skin or the ellipse (`'both'`). |
| bridges-4 (dockFrom) | every leg is tested against the NEW occupant (`pathHits(..., toDoor, count)`): back to rest the way it came, straight back (retract - swing - extend) and both lifted by 1.5 / 2.5 m first; to the door direct, via rest, or lifted; the first clear one, else the fewest poses in the body. The way back that was chosen becomes the plan's first part (an undocking during it retraces it). A bridge with a part already in the new body moves at once (no 12 s DOCK_DELAY). `b._dockFromHit` for checkers. |
| bridges-5 (VDGS bracket) | the bracket reaches max(drawn wall + 0.1, 3-D asset face + 0.15 m) - the asset face from `B3D_INTEGRATION.physics.rings` (data/buildings3d/integration.js, rounded to 0.1 m: hence +0.15). F5 stays a post (inferred; header says every VDGS position is inferred). |
| bridges-7 (tools/drawing) | `common._stretch` = `tools/liveries/common.apply_stretch` (loaded by path; no second pitch - it is in the scene's placement matrix); `type_family()` / `type_stops()` / `stop_nose()` from the app's own sources; audit.py: ENVELOPE / OVERSIZE place each type at its family's stop, a bridge whose pose does not dock (`docks` false, else k < 1) is at rest - its cab is no longer exempt against its own aircraft, slope records "above 1:12: exceeds unassisted access" (WARNING; AC 150/5220-21C §2.2.d(3)(b), Figure 6) and "beyond 1:4" (CLEARANCE; §3.4.b(6)) with the pier level and its tag (parsed from gates.js DEPARTURE_LEVELS); measure / report / sheets: the threshold bar at every end on the landing side, [0, 3.05] m (`common.THR_BAR`, checked against js/shaders/ground.js; the scene's stale `dispBar` is not used); `measure.RULES_VERSION` 2026-11-07a. |
| bridges-8 (mirrored sign) | the tunnel gate-number signs ran their text towards the viewer's left on BOTH sides (`along = -sg * hdir`); now `+sg * hdir`. The three.js renderer rebuilds the same quads from their uvs (js/three/signs.js addQuad), so it follows. |
| bridges-9 (old scene) | js/world/gates.js `GateSystem`: one bridge per gate at door 1 (there is no second-bridge door in that scene); its closure is js/aircraft/dock.js `bellowsShape` / `bellowsGeo` (fitted to the drawn skin, deployed over the last 15 % of the docking; static and per-gate cached meshes), the cab docked 1.95 m off the cab stop so the flat front lies on the skin at the door station; flat only for a type without a measured footprint. |
| bridges-10 (D10 fuel truck) | no change: verified clear (table) - in plan the truck's rear is 1.1 m ahead of the B39M's wing leading edge and its outer side 4.3 m inboard of the split tip (span 35.92 m); the render's perspective puts the winglet above it. |
| bridges-11 (upper-deck bridges) | `attachUpper()` takes `g.bridgesUpper` from `standGates()` (js/live/airport.js) and no longer reads STANDS itself. |
| header / comments | the inferred list, the own-walkway rule, the GSE description, the VDGS note. |
| verifier path slope | `bandH` keeps heights 1e-9 m inside the 1:4 band: on its edge two hurry paths read 0.25000000000000006 (bcheck2 `pathGt4` 2 -> 0). |

## R3.1 Static (data/sfo_stands.*; static_closeout.md)

1. **F5 L1 (`short_unit`)** still refuses every narrow body: at the published T3 level (4.88 m) and its 5.7 m walkway the
   rotunda floor is at 4.41 m, and the 4.4 m tunnel run to a 737 / E175 door is 1:2.5-3.2. The real bridge docks them
   (observed B38M / B738 / E75L): either its walkway is a steeper ramp / stair than 1:12, or it leaves the building lower
   than L2 - a photo of F5 (or the T3W CD sections at F5) decides; until then it stays at rest for them (inferred).
2. Unchanged from round 2 (numbers above): A1 / A2 L2 (B78X, A35K reach), A6 / A11 upper (A388), F11 L2 B772, F15 L1 B39M
   (twin drums), over-extension / optional-cab inferences, rest poses vs OSM.

## R3.2 Buildings workflow (3-D assets) / integration

1. **[Done by buildings, close-out r3 fix 2 - Round 5 R5.1; the interim-mismatch paragraph below no longer applies.]**
   **Bridge levels per pier** (js/live/gates.js `DEPARTURE_LEVELS`, exported): BA-C 3.2 [inf], BA-D 3.65 [obs, low],
   BA-E / BA-F 4.88 [pub], BA-G 2.7 [obs, low], BA-A / BA-B 5.4 [inf]. Domestic: the 23 BA-C / BA-D bulkheads can go
   (walkway tops now 6.20-6.26 / 6.65 m under the 7.20 / 8.49 m roof edges), the BA-C / BA-D concourse glazing / door
   surrounds can follow the photo ratios, `tools/blender/dom_geom.py` (concourse floor 5.4), `b3d_integrate.py` (walkway
   floor 5.4) and `verify_domestic.py` should read the per-pier value; ITB: the BA-G walkways now top 5.71-5.87 m at G1-G10
   (bump-out roofs 6.5-7.1) and the G13 upper-deck walkway floor is 8.44 m (was 9.0; inferred) - please re-extract the scene and re-run `verify_itb.py` walkway_vs_host_roof, then close the
   manifest conflict "BA-G bridge-head bump-outs vs the app walkways".
   **Interim mismatch until the domestic asset is rebuilt:** every bridge-attachment element of `dom_geom.py` derives from
   the one `FLOOR2 = 5.4` - `DOOR` (frame 5.2-8.6 m), `VEST` (vestibule 4.9-8.7 m), `FINGER_Z`, `WALK_Y0_BRIDGE`, the
   `WALK_TOP` overhang notches. The walkway section at the facade is now level - 0.25 .. level + 3.05 m: BA-C 2.95-6.25,
   BA-D 3.40-6.70, BA-E / BA-F 4.63-7.93 m (BA-B unchanged). So at BA-C / BA-D / BA-E / BA-F the door frames and the
   vestibules sit 0.3-2.3 m above the walkway ends, and where a vestibule bridges a gap to the walkway start the walkway's
   lower part meets open air under the vestibule floor. Nothing intersects (no bridge part in an asset, below), but it is
   visibly wrong: please take these from `DEPARTURE_LEVELS[pier]` (per pier, not one constant) in the rebuild.
2. **[Withdrawn in Round 5: delivered (r18 / r22) and read by gates.js `solidInAsset`; walkway starts / drums: R5.1 item 3.]**
   **integration-5 is needed for bridges-6**: `B3D_INTEGRATION.physics.rings` are plan-only; testing drums / walkway starts
   / moving parts against them would read the BA-F overhang (soffit 9.69 m over the F7 / F8 drums, which now top at about
   7-8 m) as a wall and move those drums 1.05 m. Please export the per-building footprints WITH height bands (wall vs roof
   overhang); gates.js then takes walkway starts, drum limits and `bldHit` from them and drops the own-strip heuristic, and
   I will list the vestibules that can go. (Used now only for the VDGS bracket, where the plan face is what matters.)
   Evidence that the height bands are what is missing (scratchpad `c3/bridges/scripts/tiers3d.py`: every bridge solid of
   the final tree at rest and in every docked pose - bcheck2 `bgeom.json`, 131 bridges - against
   `integration.json` footprints, plan-only vs with the `tiers[].y` bands): plan-only 2 drums (F7 / F8 L1, 2.54 / 2.67 m2)
   and F8 L1 tunnel 1 / corridor docked to CRJ2 / CRJ9 / E75L (0.46-0.52 m2) read as inside BA-F; with the bands **0 moving
   parts in any asset in any tested pose**, and the F7 / F8 drums (tops 8.03 / 8.04 m) clear the 9.69-m overhang tier by
   1.65 m (0.01 m2 against the 4.6-m tier = its 0.1-m ring rounding). The only other contacts are the 107 fixed-walkway
   building-end segments (segment 1 of 95 bridges: the walkway joins the facade), none on any other walkway segment.

## R3.3 Realtime (traffic.js / app.js / tools/live/invariants.mjs)

1. `dockFrom` now checks every leg against the new occupant and starts at once when a bridge is already in the new body.
   Two input-induced cases remain (dockcol E / H: a different aircraft set while the bridge is docked, no `null` in
   between): A8 L2 B779 -> E170 (the drive column must pass under the E170's wing on every way back) and E12 L1 A321 ->
   CRJ2 (the CRJ2 is set where the docked bridge's stair already stands). The realistic case - a new aircraft during the
   previous retraction (F / J) - is now 0. Please send `setOccupant(G, null)` before a different occupant (the real bridge
   retracts before the next aircraft arrives) and re-run the all-hours replay A/B with this gates.js (heights changed:
   slopes / dock counts above; pushClearEta unchanged).

## R3.4 Tools (jobs/extract2d.mjs)

- `paint.dispBar` is stale: the shader draws the bar at every end, `band(xt, 0.0, 3.05` (the meta.paintCheck string
  `band(xt, -3.05, 0.0` fails); tools/drawing no longer reads it (common.THR_BAR). Please export per bridge `Hb`,
  `HbTag`, `HrPinned`, `ownClip`, `rotR`, and per stand the data's `type_stops`, and re-extract (gates.js changed).

## R3.5 Aircraft

- The belt loaders now use the stance-aware API (`T.fit.cargo` / `keelAt` / `skinHW`) as requested in your Round 3 §2;
  tools/drawing uses `tools/liveries/common.apply_stretch` with no second pitch. Note for `skinHW`: it under-reads the
  A319 / A320 lower lobe by up to 0.04 m at 0.66 L (beltend.mjs: a319 aft end 0.038 m inside the mesh's side; inferred
  station, no cargo-door object) - harmless here, listed in case the table is used elsewhere.

# Round 5 (close-out round 5, residuals: c3 verify-1 bridges findings 1-5 + aircraft c4 F3; 9 Nov 2026)

Before = the files at the start of round 5, frozen (scratchpad `c5/runtime/root_before`: `js/live/gates.js` a93cce58,
`js/world/gates.js` da0cb32a; data, models and assets shared with the repo); after = the working tree (`js/live/gates.js`
11af0f1d, `js/world/gates.js` 51fc0924). Both arms ran the SAME copy of the scripts (scratchpad `c5/runtime/bscripts`: the
round-3 set + the verifier's `neckgap*.mjs` / `legacy_dyn.mjs` + new `neckcheck.mjs` bbd40737, `legacy_dyn2.mjs` 478c3f8c,
`assetpose2.mjs` 224daf66, `fixedtiers.mjs` 7be04f9e, `vestgap.mjs` 81d7ff64, `preptime.mjs` 89b100d8; bcheck2 7f845f5b).
No renders of the bridges (the two Chromium slots of this track went to the env items).

| Check | Before | After |
|---|---|---|
| rotunda / walkway / corridor junction, DRAWN mesh (neckcheck.mjs: plan coverage of the full 2.4 m corridor from the drum edge by the drum disc + the drawn walkway and corridor roofs; rest, every docked pose, every path sample k/5; 10,772 poses) | worst open notch **0.92 m2** (432 trimmed poses; narrowest covered width at the drum edge 1.2 m) | **0** (444 trimmed poses; 2.4 m); drawn corridor inside the own walkway <= 0.018 m2 (G12, tilted box); tested parts clip 0; `fixedHit` corridor x own walkway 0 |
| the verifier's neckgap.mjs / neckgap_path.mjs (coverage by the TESTED `neckParts` boxes) | 0.76-0.93 / 0.96 m2 | 0.28 / 0.34 m2 (the tested bands are inner boxes 0.06 m clear of the walkway; the drawn outline closes the rest: row above) |
| ownclip / ownneck | 0 / 0 | 0 / 0 |
| old scene, animated bridges (legacy_dyn2.mjs: GateSystem.items, consecutive frames k 0.84-1.0, b738 then a320 at one gate) | **7 of 11 frames flat block + fitted closure**; the a320 frames drew the cached b738 closure | **0 of 11**; one closure per (gate, type, 0.05 k step), drawn at the cab (offset 0.000 m); flat only before deployment (k < 0.85, by design) |
| old scene, static (legacy.mjs) | 50 fitted / 0 flat | 50 / 0 |
| conveyor end face vs the rendered skin (beltmesh.mjs, SKIP=0: every mesh sample) A / B | **64 of 79 / 138 of 138** belts with the end face inside the skin (max 0.054 m) | **0 / 0** |
| aircraft verifier `belt_w2.mjs` (c4: end inside the skin by) | NG aft 0.055-0.058, MAX 0.041, A319 0.119 m | all clear (<= -0.008 m) |
| beltend.mjs: lateral gap end face - skin (28 type x door rows) | -0.005 .. +0.033 m (the centre clear, the corners inside) | 0 .. +0.132 m (the whole top edge clear; the binding point is the outer corner) |
| gse.mjs (GSE_SKIN=1) A / B | 0 / 0 issues, belts 79 / 138, catering 26 / 28, fuel 37 / 36 | identical |
| moving parts in a 3-D asset footprint tier (assetpose2.mjs, height bands, 44,776 docked / path poses) | 0 (not tested by gates.js) | 0, and now tested (`bldHit`) |
| docking plans (slopes.mjs; preptime.mjs staticPlans) | 3,331 made / 78 refused | identical (same plan set); prep + plans 0.88 + 1.24 + 6.23 s -> 0.74 + 0.97 + 5.90 s |
| slopes, hurry_peak, stair, restsweep, bldpose, vdgs, vdgsarm, vdgsac, signs, upper, walktop, census, dockcol, jump, swap, api, fuelmesh | (suite s0) | output identical except wall time (suite s2) |
| bcheck2 (131 bridges) | 0 issues | 0 issues; bcheck.json / bcheck_extra.json / log identical (bgeom.json differs: the drawn corridor) |

## R5.0 What changed

| Finding | Change |
|---|---|
| bridges-2 residual (neck notch) | `neckShape(b, a)` (js/live/gates.js): the corridor's plan outline per lateral (every 0.05 m + the walkway corners +-1e-4 m): near part from the drum to the own walkway's near edge, far part from the walkway to the full-width start (ray vs the drawn walkway boxes, inclusive). `bridgeGeo` draws it as extruded prisms over the full-width slab, so drum + walkway + corridor is one closed union, 2.4 m wide everywhere (sell-sheet minimum 1.32 m). `neckParts` tests it as 0.3-m lateral bands, each bisected to 0.06 m clear of the own walkway (`obbOverlap`), adjacent equal bands merged. Cached per bridge and angle (reset when the own walkway changes). |
| bridges-9 regression (old scene cache) | js/world/gates.js `bridgeInstances(g, k, out, fit, opt)` -> `{M, fitted}`; `items()` caches per `gate:type:kq`, builds the closure in the cab frame (`opt.local`) and draws it with the cab's matrix (`prevModel` = last M); on a cache hit (`opt.cached`) neither the closure nor the flat block is rebuilt. Static path unchanged. |
| bridges-6 (asset footprints) | **partly**: `solidInAsset(bx)` (exported) tests a solid against `B3D_INTEGRATION.footprints.units[*][*].tiers` with their height bands (`TIER_TOL` 0.15 m for the r22 ring growth, indexed by 40-m cells + 8-m edge cells + 4-m height bands so the start-up time stays as before); `bldHit` = museum strip OR asset tier. Walkway starts, drum limits and the own-strip heuristic still come from the SFO Museum outline: R5.1 item 3 says why, and what a coordinated switch needs. The gates.js comment at the ASSET block no longer says "no height bands yet". |
| aircraft c4 F3 (`beltEndY`) | js/world/gates.js `beltEndY(T, X, S, face)`: the conveyor's end face is kept 0.03 m off `T.fit.skinHW` along its whole top edge (5 samples over the face's lateral / fore-aft extent, `BELT_W` 0.9 m) instead of at its centre line; js/live/gates.js passes the per-yaw corner offsets and rejects a pose whose end face (3 heights x 5 laterals) is in the skin (`no('own fus (conveyor end)')`). |
| R3.2.1 stale paragraph | marked done below (R5.1 item 1). |
| DEPARTURE_LEVELS A / B / C | unchanged (A / B 5.4, C 3.2 [inf]); owner question in R5.2. |

## R5.1 Buildings workflow (3-D assets) / integration

1. **R3.2.1 is done by buildings** (close-out r3 fix 2, domestic.glb 2026-11-07 13:10Z from `tools/blender/app_bridges.json`,
   `dom_geom.py PIER_LEVEL`; manifest: domestic conflict "BA-C / BA-D roofs vs the app concourse floor" resolved, ITB
   `walkway_vs_host_roof` 0 of 24 BA-G / 0 of 21 BA-A). The interim-mismatch paragraph of R3.2.1 no longer applies.
2. **R3.2.2 (integration-5) is withdrawn**: `B3D_INTEGRATION.footprints` with `tiers[].y` bands was delivered (r18 / r22)
   and gates.js now reads it (`solidInAsset`, `bldHit`).
3. **Request R5.3 (coordinated, buildings + bridges in one round): walkway starts and drum limits from the asset tiers.**
   gates.js still starts each fixed walkway at the SFO Museum outline (`prepGeom`, own-strip heuristic) and limits the
   drums against it; `app_bridges.json` (`walk[0]`) carries those starts into the assets, whose vestibules and door
   surrounds close the gap to the facade (buildings' walkway-end check: LOD0 0 of 46 open). Moving the starts to the tier
   faces changes the walkway lengths, hence `Hr` over the 1:12 band, the docked slopes and every vestibule at once, in
   both renderers - so it needs one round where buildings re-extracts `app_bridges.json` right after the gates.js change.
   Data for that round (scratchpad `c5/runtime/a2x/`): fixed parts at rest vs the tiers (`fixedtiers.mjs`): walkway
   segment 1 joins the facade at 162 bridges (by design); A6 L1 walkway segment 2 0.13 m2 into `itb/hall` 'over'
   (underside 4.9-6.0 m vs walkway top 8.26 m: the BA-A 5.4 m level, R5.2); 18 drums 0.008-0.39 m2 into a tier
   (`itb/hall` body G1 0.23, G2 0.26, G5 0.39, G6 0.36, G10 0.12; `itb/hall` over A2 0.38, A11 0.18; BA_D over D3 / D4 / D5 /
   D7 / D10 / D15 / D16 0.008-0.13; T3E over E3 0.14; BA_E over E9 0.34; BA_F over F7 0.16, F8 0.37) - the drums abut
   the facade (walkway 1.3-2.2 m), they are fixed (no moving part in a tier in any pose, table). Walkway start vs the tier
   face at walkway height (`vestgap.mjs`, 126 first segments): 97 start inside the asset by 0.15-2.0 m, 9 short of it
   (A2 L1 0.40, G1 0.15, G2 0.20, G5 0.25, G6 0.35, E9 0.30, F8 0.25, **E6 L1 4.25, E11 L1 4.05 m**), 15 with no tier
   within 8 m behind them (B5, C8, D3-D5, D15, D16, F12, F14, F16, F17, F19-F21 L1, F22 L2). The tiers are the plan
   prisms of the shells, not the vestibules, so a "short" start may be closed by a vestibule in the mesh (buildings'
   check is the authority); please confirm E6 / E11, then list the vestibules that can go once the starts move.

## R5.2 Owner

- **DEPARTURE_LEVELS A / B / C stay inferred** (5.4 / 5.4 / 3.2 m). BA-A's sister pier BA-G is 2.7 m [obs, low]; if the
  two ITB piers share a section, BA-A's walkways are ~2.7 m high (tops 8.26-8.40 m; no conflict with the BA-A asset). A BA-A
  walkway / facade photo, the ITB sections, or an instruction to apply the BA-G level to BA-A by analogy (tag inf, as
  `itb_geom.py` treats the BA-A facade) decides it. F5 L1 (B738 / B38M / E75L refused at the published T3 level) as in R3.1.

## R5.3 Lead

- Files changed by this track for bridges this round: `js/live/gates.js`, `js/world/gates.js`, this file.
- The neck coverage check the verifier asked for "next to ownclip" lives in the scratchpad (`c5/runtime/bscripts/
  neckcheck.mjs`); `tools/bridges/` does not exist and is not this track's to create. If a committed gate is wanted,
  please say where (e.g. `tools/bridges/check_neck.mjs`, run with `PATHS=1`: pass = worst notch 0, tested clip 0).
