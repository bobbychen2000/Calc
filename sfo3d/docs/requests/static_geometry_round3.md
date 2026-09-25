# Requests after review round 3 (static geometry), 25 Sep 2026

From: static-geometry workflow (owner of `js/geo.js`, `js/live/airport.js`, `js/live/markings.js`, `js/live/world.js`,
`js/live/terminals.js`, `js/live/signs.js`, `js/live/items.js`, `js/anim/lights.js`, `js/world/*`, `data/sfo_*`,
`tools/build_*.py`, `tools/stands/`, `tools/imagery/`, `tools/sat/`, `tools/xcheck/`). The data changes of this round
are in `docs/research/stands_rebuild.md` §13. Everything below is in files I do not own. Items of
`static_geometry_round2.md` that are still open are restated here, because round 3 found them still open and critical.

## 1. js/live/gates.js (critical, still open since round 2): draw the DATA bridges

Review round 3 measured the app (out/draw/scene2d.json, 24 Sep 22:01Z) against the data and NAIP 2024:
- app rotunda (`rc = attach + u * fixedLen`, gates.js:99) vs data `rotunda`: median 8.6 m, 107 of 108 more than 1.5 m
  apart, up to 31 m (F11 L2), 30.1 (F13 L2), 20.7 (A1 L2);
- 41 app walkways are drawn straight where the data walk has 3 or more vertices (A1 L1 / L2 become 53-57 m straight
  corridors across the apron); NAIP walkway band vs app walkways median |residual| 2.75 m, vs data walks 1.16 m;
- overlaps that exist only in the app: rotunda drums 3.3-4.8 m apart at G2-G7 / A9, B11 L1's rotunda inside B11S's
  resting tunnel, B11S L1 docked through B11 L1, resting bridges inside parked aircraft (F22 L2 20.6 m2, B16 L1 17.5,
  B11 L1 16.4, B5 L1 13.8, G13 L2 13.8, A6 L2 10.2 + 17 more), 38 drums partly inside the building.

`standGates()` (js/live/airport.js) passes per bridge:

| field | meaning (data field) |
|---|---|
| `walkW` | fixed walkway polyline building -> rotunda, world [x, z]; **since round 3 it always ends at the rotunda** (`walk`) |
| `rotundaW` | rotunda centre (never null any more: 128 of 128; `rotundaSrc` says how it was found, "inferred: ..." where it is) |
| `rotundaMaxR` | drum radius that touches nothing else (use `min(2.45, rotundaMaxR)`) |
| `tunnelEndW` | OSM ways that end with a short cab stub: the parked tunnel ends here (the cab follows); null otherwise |
| `cabW`, `cabPose` | OSM cab end and whether it was mapped docked or parked - never use a 'docked' cab as the rest pose |
| `stowW`, `stowLen` | the rest pose of the tunnel end (cab pivot); `stowLen` >= the model's retraction; clear (+1 m) of every aircraft the stand, its alternatives and its neighbours accept, of every other bridge at rest and of **every other bridge docked** (round 3: F15 / G7 / G13 L1 docked a narrow body straight through L2 at rest) |
| `extRange` [min, max] | operational range rotunda centre -> cab pivot of the bridge's datasheet model (`model`, Oshkosh AeroTech sell sheet; one model per bridge, inferred) - **not** 9.846-41.381 m, which is the whole product line |
| `dockTypesOut` | accepted types this bridge cannot reach at their stop: it stays at `stowW` |
| `cabTurnDeg`, `cabOption` | signed cab turn of the observed dockings (sense: data `cab_convention`); 'optional 185 deg cab needed' where the standard 92.5 cw / 32.5 ccw cab is not enough |

| # | Change |
|---|---|
| 1 | Fixed walkway along `walkW`, rotunda at `rotundaW` with radius `min(2.45, rotundaMaxR)`. Drop `fixedLen = clamp(D - 27, 3.5, 70)` and "second bridge = attach + 7 m" (gates.js:54-104). |
| 2 | Rest pose: tunnel from the rotunda to `stowW` (cab beyond it), never `cabW` when `cabPose === 'docked'`, never the reference type's door. |
| 3 | Docked: cab pivot 2.4 m out from the door along the fuselage normal; dock only when the rotunda -> pivot distance lies in `extRange` (+-1 m) and the type is not in `dockTypesOut`; otherwise the bridge stays at `stowW`. L2 docks only types with `T.dock2`; a narrow body docks L1 while L2 stays at `stowW` (the data guarantees L1 docked clears L2 at rest). |
| 4 | Alternative positions (`g.altOf` with `g.sharesBridgesOf`): dock the base stand's bridges; when the alternative is occupied, the base stand's bridges dock it or stay at `stowW`. |
| 5 | Upper-deck bridges (`bridges_upper`, A6 / A11 / G13) stay parked until an A388 U1 door can be docked. |

Check after the change: `python3 tools/stands/check_stands.py` (data) and the 2-D audit (`tools/drawing/run_all.sh`,
bridge rows of docs/drawings/report.md) - the rendered rotundas should then match the data to < 0.5 m.

## 2. js/shaders/ground.js and js/three/ground.js (major): threshold bar on the landing side, at all 8 ends

`endMarkings()` draws the 10 ft bar at `band(xt, -3.05, 0.0)` (approach side) and only when `disp > 1`. NAIP 2024 shows
a 10 ft bar on the LANDING side at all eight ends. Two independent measurements (centre of the bright 3 m band,
+ = landing side): review round 3 10L +0.90, 28R +1.80, 10R +1.40, 28L +1.90, 1L +1.80, 19R +1.90, 1R +1.80, 19L +1.50 m;
docs/drawings/report.md "runway-threshold-bar" 8/8 flagged, displaced ends +3.3..3.4 m from the model's -1.52 m.
**Draw `band(xt, 0.0, 3.05)` at every end** (displaced or not). The consistent +1.5 m also confirms the NAIP-to-FAA
registration of the thresholds to ~0.4 m.

## 3. js/aircraft/types.js (major): winglet spans

Boeing Commercial Airplanes, "Wingspan Increases Due to the Addition of Winglets" (airport FAQ, cached
`refs/cache/boeing3v/wingletspans.pdf`): 757-200/-300 124 ft 10 in (38.05 m) -> 134 ft 9 in (41.1 m); 767-300ER 156 ft
1 in (47.57 m) -> 167 ft 0 in (50.9 m). SFO's 757s and 767-300ERs (UAL, DAL; ADS-B stays B752 / B753 / B763 at C3, C5,
C9, D5, F11, F14-F17, F19-F22) fly with winglets; types.js has the baseline spans. The stand data now uses the winglet
spans for B752 / B753 / B763 (tools/stands/geom.py WINGLET_SPAN; class CL = 41.1 m / 54.5 m), as a verified upper
bound - the fit per airframe is not verified (ADS-B designators do not say; SFO's AODB writes B75W / B76W for some).
Request: add the winglet spans (e.g. `wingletSpan` on b752 / b753 / b763, or the AODB designators B75W / B76W as
variants) so that ground.js clearances and gates.js use them.

## 4. js/live/traffic.js (still open from round 2 #1-#6, plus)

- honour `g.typesOk` (now the observed types PLUS every type whose planform fits inside their envelope - round 3: the
  exact-designator whitelists had refused smaller types SFO parks) and `g.typeStops` (new: B22 E-Jets stop 4.3 m short,
  ADS-B n = 3 and NAIP agree);
- the oversize clause only on `g.a380` stands; per-family stops instead of stop-short parking (APP ISSUES: 33 pairs
  in `python3 tools/stands/check_stands.py`);
- class CL is now 41.1 m span / 54.5 m length (airport.js `CLASS_MAX`, exported);
- remote stands carry their class (`cls`, was a fixed 'E') and `paveW` (the paved envelope clipped to the OSM apron);
- stand `G11` is now `G12` (AODB G12S; alias G11): bump the persisted-parking key (`sfolive.parked.v2`);
- `conflict_along` (NAIP aircraft stopped > 1.5 m from the model nose): the stop point is not verified - do not snap
  aircraft harder than the stand's evidence allows.
- js/live/ground.js (GroundPhysics): the 45 m `patches` that paved grass wherever a snapshot aircraft stood are gone
  (review round 3, critical: circular and on the infield). Two snapshot aircraft, UAL643 B38M at (-135.7, 385.5) and
  SKW6001 E75L at (-89.3, 409.7) (gs 0), are 38 / 49 m from any pavement and 136 / 155 m from any taxiway centreline -
  on the grass between 1L/19R and 1R/19L. A stationary aircraft that far from pavement cannot be placed plausibly within
  the 6 m correction; it should be moved to the nearest centreline / stand it can reach, or not drawn on the ground.

## 5. js/three/* (three.js port)

The same data now feeds js/live: red boxes carry their measured angle and a line-centre side (js/live/markings.js
draws them at `[x, z, side, ang]`, no grid alignment); floodlight masts are OSM-mapped and all drawn (js/live/world.js
no longer drops masts inside the class rectangle); approach-light structures come from `APPROACH_STRUCTURES` in
js/geo.js (js/anim/lights.js pier kinds 'catwalk', 'station', 'crossbar', 'hut', 'post'); remote stands pave only
`paveW`; `data/sfo_details.json` has no `patches` any more; `buildSigns` (shared) keeps signs off taxiway / runway
polygons. js/three/{markings,lights,ground,bridges}.js should follow.

## 6. CLAUDE.md / docs/HANDOFF.md (owner)

- `sfo_details.js`: masts = 70 OSM-mapped (man_made=mast, tower:type=lighting; 8 moved <= 1.6 m off the building
  outline), taxiway edges snapped to NAIP paint (edgeStats), no `patches`.
- `sfo_stands.js`: 255 red boxes (NAIP, oriented-square template fit), `unplaced` (SFO stand names without a position),
  `bridge_models`, `cab_convention`.
- New `data/sfo_shore.js` (`tools/imagery/shore_naip.py`, NAIP 2024 NIR): the shoreline over the NAIP coverage used by
  js/world/terrain.js for land / water. The 16-vertex `AIRPORT_LAND_ST` stays the shaders' airport-area mask; as a
  coastline it was 44 m out in the Bay at the 28 ends and made the north basin land (100 ha of water inside it).
  js/three/* terrain code (if it has its own) should use the same file. `AIRPORT_LAND_ST` itself is now a 16-vertex fit
  to that shoreline (IoU 0.98; Bay-side median 11 m, max 143 m). **js/shaders/ground.js BAKE_AUX_FS / js/shaders/env.js
  (seawall foam)**: the foam distance comes from that 16-vertex polygon, so foam lies up to ~100 m off the real seawall
  in places; please bake the aux distance from `data/sfo_shore.js` (a full-resolution ring, or a distance texture)
  instead of `uAptPoly[16]`.
- Checks: `python3 tools/stands/check_stands.py` now also checks the masts.
