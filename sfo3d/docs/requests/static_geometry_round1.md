# Requests after review round 1 (static geometry), 24 Sep 2026

From: static-geometry workflow (owner of `js/geo.js`, `js/live/airport.js`, `js/live/markings.js`, `data/sfo_*`,
`tools/stands/`, `tools/imagery/`, `tools/build_*.py`). These changes are needed in files I do not own. Evidence and
numbers: `docs/research/stands_rebuild.md` (§4, §5, §11) and `python3 tools/stands/check_stands.py`.

## js/live/gates.js (bridge geometry)

`standGates()` (js/live/airport.js) now passes, per bridge: `rotundaW`, `walkW`, `cabW`, `cabPose`, `stowW`,
`rotundaMaxR` (see stands_rebuild.md §8). The review found the app's derived bridge geometry is what fails the imagery
and clearance checks; the data now carries geometry that passes `check_stands.py` (0 issues except F5 and A11, §11).

| # | Change | Why (review round 1 finding) |
|---|---|---|
| 1 | Place the rotunda at `b.rotundaW` (when not null) and draw the fixed walkway along `b.walkW` (building -> rotunda), instead of `attach + u * clamp(D - 27)` (gates.js:83-89). | Every rendered rotunda is 1.5-20.8 m (median 8 m) off the OSM/NAIP rotunda; L1/L2 walkways of the same stand collide. |
| 2 | Draw the rotunda with radius `min(2.45, b.rotundaMaxR)`. | OSM rotundas on the G pier are 4.6-4.9 m apart; with a 4.9 m diameter they intersect. |
| 3 | Rest pose: put the tunnel end at `b.stowW` (not at the reference type's door, gates.js:103). Never use `b.cabW` as a rest pose when `b.cabPose === 'docked'`. | Alternative positions (B5S, B11S, B16S) park inside the base stand's resting bridge; narrow bodies on two-bridge stands sit under the non-docking L2 bridge; 40 OSM cabs are mapped docked. `stowW` clears the envelope (+1 m) of every type the stand and its neighbours (including `excl` / alternative stands) accept. |
| 4 | Dock L2 only to a door ahead of the wing root. For the 767 that is its 2L door at 15.96 m (Boeing D6-58328 767 ACAP; `tools/models/check_dims.py` REF B763 doors {1: 5.70, 2: 15.96, 3: 42.55}); `js/aircraft/types.js` SPEC b763/b762 lists [5.70, 42.55] and docks L2 at the aft door (tunnel over the wing, 42.8-50 m extension). If a type has no such door, dock L1 only and leave L2 at `stowW`. | 24 stand-bridges docked over the 767's own wing. |
| 5 | Clamp the docked extension (rotunda centre -> cab) to 9.846-41.381 m (Oshkosh AeroTech Jetway sell sheet 2025) and do not dock beyond it; limit the cab turn to 92.5 deg (standard cab). | F5 / F16 / F17 docked at 6-10 m; F10 cab turned 150 deg. |
| 6 | Display `g.gate` (e.g. `B5` for stand `B5S`) on the stand sign / VDGS; `b.gate` is now always the stand's gate number. `g.name` is the gate number again for every stand except the four alternative positions. | Signs showed AODB suffixes (A1V, E10U, G13S). |
| 7 | F10 no longer has a bridge (the OSM "F10" bridge is right-front of the nose; NAIP shows it parked ahead of the regional jet). `g.bridge` is false for F10, so it renders as a stand without bridge. | cab turn 150 deg, tunnel over its own CRJ. |
| 8 | `REF_TYPE.F`: use `'a388'` (door 1 at 6.32 m), not `'b748'` (9.5 m); better, drop the reference-type rest pose and use `stowW`. | 3.2 m along-track mismatch on A6, A11, G13. |

## js/live/traffic.js (stand matching)

| # | Change | Why |
|---|---|---|
| 1 | Oversize rule (traffic.js:60, `g.maxSpan >= 64 && span <= 80`): allow A388 / B748 / B779 only on stands with `g.a380` (data: `a380_stands` = A6, A11, G13). | With an A380 on an EL stand the wings overlap the neighbour: A9/A5 0.0 m, G2/G5 0.0 m, G8/G7 0.0 m, A8/A11 0.1 m, G9/G6 0.2 m, A8/A6 0.5 m, G6/G5 0.3 m, F19/F20 1.0 m (envelopes, `tools/stands/geom.py`). |
| 2 | `standFits`: respect `g.maxLen` (now limited by the data's `len_max`, e.g. E10 42.2 m, E12 54.5 m, F19/F20). It already uses `maxSpan` (with `span_max`). | E10/E12 and F19/F20 are tight pairs (0.4 m / 1.9 m with the largest types SFO parks there); larger accepted types would overlap. |
| 3 | `g.tightWith` lists neighbours that are only clear with the stand's span/len limits (SFO plans both at once). Optionally prefer the other free stand when a type near the limit arrives. | as above |
| 4 | Stand ids: `name` changed back to the gate number (A1, A4, A13, E10, E11, E13, G13; AODB names in `aodb`, which `prepGates` already merges into `g.names`). Bump the persistence key again. | stale parked records |
| 5 | A per-type stop point: the app parks every type's nose at one point per stand; SFO's stop marks differ per type (ADS-B: narrow bodies stop 20-30 m short on wide-body stands, E12 B753 ~18 m short). | the remaining tight pairs and the per-type envelopes |

## js/shaders/ground.js (blast-pad chevrons)

Change the chevron apex spacing to **30.48 m (100 ft)** and the first apex to **16.8 m** beyond the runway end
(shader: 29.7 m / 15.0 m, ground.js:116). Measured on NAIP 2024 along the NASR axes (review round 1, re-checked in
stands_rebuild.md §6): 10L apexes 16.9, 47.4, 77.9, 108.3, 138.8, 169.3, 199.6, 230.3 m; 10R 16.4 ... 168.9 m; 28R
17.2, 47.6, 78.1 m; 28L 16.9, 47.4, 77.9 m. The shader's error reaches 7.4 m at the 8th chevron.

## js/live/entry.js / ui / about (credits)

`data/sfo_details.*` now contains OSM taxiway centrelines (ODbL, like `sfo_stands.*`), and `data/sfo_paint.*` /
`data/sfo_pavement.*` are classified from USDA NAIP 2024. Show: "Taxiway, stand and jet-bridge data © OpenStreetMap
contributors (ODbL). Imagery-derived paint and pavement: USDA NAIP 2024." (docs/ATTRIBUTION.md).

## CLAUDE.md / docs/HANDOFF.md (data table)

| File | Contents | Made by |
|---|---|---|
| `sfo_details.js` | OSM taxiway centrelines checked on NAIP, holding positions measured on NAIP, apron (inferred), masts, roads | `tools/build_airfield_details.py` |
| `sfo_stands.js` | 108 contact stands (4 alternative positions), 131 OSM bridges with rest poses, lead-ins, 309 NAIP red boxes (ODbL) | `tools/stands/build_stands.py` |
| `sfo_paint.js`, `sfo_pavement.js` | green no-taxi paint and extra pavement from NAIP 2024 | `tools/imagery/paint_pave_naip.py` |

Checks: `python3 tools/stands/check_stands.py` (bridges and aircraft), `python3 tools/imagery/check_markings.py`
(centrelines and hold bars against the paint on NAIP).
