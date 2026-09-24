# Requests after review round 2 (static geometry), 24 Sep 2026

From: static-geometry workflow (owner of `js/geo.js`, `js/live/airport.js`, `js/live/markings.js`, `js/live/world.js`,
`js/live/signs.js`, `data/sfo_*`, `tools/stands/`, `tools/imagery/`, `tools/build_*.py`). The data now carries geometry
and evidence that pass `python3 tools/stands/check_stands.py` except the items listed in
`docs/research/stands_rebuild.md` §12. The checker now uses the app's own aircraft geometry (`js/aircraft/types.js`,
dumped by `tools/stands/dump_types.mjs`) and prints a separate **APP ISSUES** list: conflicts that exist only because of
how the files below use the data today. Each row names the review finding it answers. Earlier requests
(`static_geometry_round1.md`, `stands_rebuild.md`) still apply; this file restates the ones the review found critical.

## js/live/gates.js (critical: the rendered bridges are not the data bridges)

`standGates()` passes per bridge `rotundaW`, `walkW`, `cabW`, `cabPose`, `stowW`, `rotundaMaxR`, `rotundaTwinOf`.
gates.js reads none of them (review round 2: app rotunda vs data rotunda median 8.2 m, 43 of 108 more than 10 m off;
13 stands with their own fixed parts overlapping; D1 rotunda on the wrong side of the nose).

| # | Change | Finding / evidence |
|---|---|---|
| 1 | Fixed walkway along `b.walkW` (building -> rotunda), rotunda at `b.rotundaW` (when not null), drum radius `min(2.45, b.rotundaMaxR)`. Drop `fixedLen = clamp(D - 27, 3.5, 70)` / "second bridge = attach + 7 m" (gates.js:54-90). | app rotundas 3.3-4.9 m apart at G2-G7, A9, A10; fixed parts overlapping at G5, G10, A10, G6, A9, G2, G3, A13, A8, A2, G7, A6, G4 |
| 2 | Rest pose: tunnel end at `b.stowW`, never `cabW` when `cabPose === 'docked'`, never the reference type's door (gates.js:95-104 `cabPark`). `stowW` is 9.85-30 m from the rotunda and clear (+1 m) of every type the stand, its alternative position and its neighbours accept. | bridges at rest inside parked aircraft: B11/B11S 23.8 m2, B16/B16S 18.9, B5/B5S 15.9, L2 inside narrow bodies at F22 26.2 m2, G13 17.3, A6 15.3, A11, A1, G3, G7, G8, G9, G10 |
| 3 | L2 docks `T.doors[T.dock2 - 1]` only when `T.dock2` is set (types.js now sets it; b762 / b763 have none, their 2L is optional) - otherwise L2 stays at `stowW`. L1 docks door 1. | L2 over the 767's wing (aft door) at 25 two-bridge stands, 46-50 m extensions |
| 4 | Docked cab: pivot 2.4 m out from the door along the fuselage normal (Oshkosh AeroTech sell sheet: full retraction 12.224 m - operational 9.846 m = 2.378 m pivot -> cab spacer); extension rotunda -> pivot limited to 9.846-41.381 m; a stand whose docking would fall outside keeps the bridge at `stowW`. | app rest tunnels of 5.8 m (F5) / 9.6 m (F16), shorter than any apron-drive bridge can retract |
| 5 | Alternative positions (`g.altOf` with `g.sharesBridgesOf`): dock the base stand's bridges; when the alternative position is occupied the base stand's bridges must dock or stay at their `stowW` (clear of the alternative's aircraft by construction). B11 / B11S now each have their own bridge (1096422714 / 1096422713, stand_table.BRIDGE_FORCE). | B5S / B11S / B16S aircraft inside the base stand's resting bridge |

## js/live/traffic.js (stand fit and parking)

| # | Change | Finding / evidence |
|---|---|---|
| 1 | `standFits`: the oversize clause `g.maxSpan >= 64 && span <= 80` only when `g.a380` (data: A6, A11, G13). | A380 / 747-8 on every EL stand and on F19 (F19's span_max 64.8 = the B77W SFO parks there opens the clause): APP ISSUES A5/A9, A9/A10, G2/G5, G5/G6, G6/G9, G7/G8, G9/G10 overlap, A8/A11 0.1 m, A6/A8 0.5 m, F19/F20 1.1 m, F11/F13 1.1 m |
| 2 | `standFits`: when `g.typesOk` (array of ICAO designators) is set, accept only those types (+ the unknown-type fallback). Set on E10 / E12 and F19 / F20: the types SFO parks there. | With every type inside the class limits the pairs come within 1.1 m (E10 A19N-sized wing at E12's nose) / 1.9 m (B77L at F19); with the observed types at their stops they clear 4.2 m / 5.1 m (ICAO C 4.5 m / D-F 7.5 m reducible with VDGS, listed in stands_rebuild.md §5) |
| 3 | Per-family stop points: `g.typeStops = {FAMILY: {along, n, src}}` (FAMILY: B737, A320, B757, B767, EJET, A220, CRJ, B777, B787, A330, A350, B747, A380, MD11 - `tools/stands/geom.py` FAMILY). Park the nose `along` metres along the stand axis from `g.world` (negative = short of the nose). Evidence: ADS-B (adsb.lol) stays with SFO stand windows, relative to the family's usual offset on other stands. | 737s stop 15-18 m short of the stand nose at E12, F15, F21; an A319 29 m short at G7; A220 12 m at D10; A320 family 14.5 m at D12 |
| 4 | Stop-short parking (`updatePark`, noseAlong clamped to -25..0 m, traffic.js:693-698): limit the offset to the family stop (#3) or re-check clearance to occupied neighbours before accepting a pose short of the stop. | APP ISSUES (stop-short): A1/B2, B2/B4, B3/B6, B3/C1, B5/B10, B5S/B10, C1/C4, E2/E3, E3/E6, F9/F10 touch or overlap at 10-25 m short; E4/E5, E6/E8, F6/F7, F18/F19 below 3 m |
| 5 | The SFO-plan path (traffic.js:656) should also skip stands in `g.excl` while one is occupied and respect #1-#2. | it bypasses `blocked()` and `excl` |
| 6 | `g.conflict` (D3, D4, D8, D9): ADS-B aircraft with SFO's stand window sit 2-8.5 m / up to 24 deg off the stand axis while NAIP 2024 shows aircraft on it (D3, D4). Matching should tolerate the offset (do not snap such an aircraft to a different stand); do not treat the stand position as verified. | review round 2 (gatecheck 15:15-18:46 UTC) |

## js/shaders/ground.js and js/three/ground.js (blast-pad chevrons)

Both shaders draw the chevrons with the first apex 15.0 m beyond the runway end and a 29.7 m pitch
(`q = xb - |dv| - 15.0; k = floor(q / 29.7 + 0.5)`; js/shaders/ground.js:116, js/three/ground.js:311). Measured again
on NAIP 2024 (`python3 tools/imagery/check_markings.py`, yellow peaks on the axis, 0.1 m samples): first apex 10L 17.1,
10R 16.6, 28R 17.3, 28L 17.1 m; spacing 30.4-30.6 m (100 ft). Use **first apex 17.0 m, pitch 30.48 m**
(`q = xb - |dv| - 17.0; k = floor(q / 30.48 + 0.5); f = q - k * 30.48`). The error of the present shader grows to
7.6 m at the 8th chevron. (The EMAS chevrons are geometry in js/live/world.js and were fixed there: first apex
5.4-6.4 m after the bed entry per end, pitch 30.48 m.)

## js/three/signs.js (holds)

`data/sfo_details.json` holds now carry `kind` ('runway' | 'ils'), `signs` (false for the second, angled ladder at T,
which shares the sign pair of the main ladder) and `secondary`. js/live/signs.js skips the sign pair when
`h.signs === false` and the painted surface sign for ILS holds (FAA: the ILS critical-area hold has an "ILS"
mandatory sign, no surface-painted holding sign). js/three/signs.js places signs through buildSigns and keeps the same
atlas face list, so it follows automatically; `worldSignAtlasMap` needs no change.

## CLAUDE.md / docs/HANDOFF.md (owner)

- Data table: `sfo_details.js` = 267 centrelines (OSM + 1 NAIP-traced E-W crossing of 1L/1R that OSM lacks), 90 holds
  (88 runway, 2 ILS; 10 located by OSM holding-position features and measured on the paint); `sfo_stands.js` = 108
  contact stands, 128 OSM bridges, 257 NAIP red boxes (plausibility-filtered), ADS-B evidence from adsb.lol only.
- Checks: `python3 tools/stands/check_stands.py` (DATA ISSUES + APP ISSUES), `python3 tools/stands/naip_relief.py`
  (NAIP lean fit), `python3 tools/imagery/check_markings.py`.
