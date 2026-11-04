# Bridges track close-out (review 2026-11-04): requests to the other tracks

From: owner of `js/live/gates.js` (bridge geometry / animation, VDGS, GSE), `js/world/gates.js`, `js/shaders/ground.js`
(threshold bars / runway paint). Numbers: the reviewer's numeric check `bcheck.mjs` (131 bridges, every accepted type at
its `type_stops` stop, incl. alternative positions), re-run before / after this round; GSE also with an independent check
that samples every vehicle MESH (`gse.mjs`). Scratch scripts are not committed; the numbers are quoted here.

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
