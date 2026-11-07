# Requests from the buildings track (Blender assets: tower, ITB, domestic, landside)

From: owner of `tools/blender/**` (except the integration files `b3d_integrate.py`, `b3d_lod2_check.py`, `b3d_split.py`,
`b3d_views_job.mjs`, `b3d_glass_job.mjs`, `build_roadways.py`, `roadways_net.py`), `tools/buildings/**`, the
`data/buildings3d/{tower,tower_f1,tower_lod2,itb,itb_lod2,domestic,domestic_lod2,landside,landside_lod2}.glb` assets and `lsu_*`
units, their `manifest.json` entries, `docs/drawings/buildings/**`. What changed on this side is in `docs/research/buildings3d.md`
(the "Close-out round 3" sections of the ITB, landside and domestic groups) and `manifest.json#<group>`.

## Round 3 (close-out round 3, 6 Nov 2026; findings `docs/requests/closeout3_findings.json#groups.buildings`)

Rebuilt in this round: `domestic.glb` / `domestic_lod2.glb` (05:39Z), `landside.glb` / `landside_lod2.glb` + `lsu_*` (05:43Z,
`b3d_split.py` re-run), `itb.glb` / `itb_lod2.glb` (see R3.6). `integration.json` (03:59Z) and `roadways.glb` predate all three.

### R3.1 Integration: rebuild `roadways.glb`, then re-run `b3d_integrate.py` / `b3d_lod2_check.py` (buildings-2, major)

The Terminal 2 landside face no longer follows the SFO Museum level-2 outline over the departures roadway. It now stands on
the NAIP 2024 relief-corrected roof edge, `x = -811.96 + 0.3063 z` for z 168-254 [obs]. Elsewhere it sits 5.85 m off the
departures deck edge (OSM ways 256787747 / 682008752). In front of it: the 5.85-m departures sidewalk at the curb level, a
5.4-m glass curb canopy, and the T2-garage connector (`T2_garage_link`, underside 9.43 m, top 14.38 m [inf]) carried to the new
face. In all, 2,355.9 m2 of shell was removed from over the roadway.
- `build_roadways.enclosure_cuts` cut 1,406.5 m2 of the domestic departures deck at the OLD T2 body as an interim. The
  rebuilt domestic asset no longer encloses that deck: `verify_domestic_r2.t2_curb` finds 0 m2 of T2 / connector solid
  between the deck and 4.6 m above it along the OSM Departures ways. A roadways rebuild should therefore return the deck
  along T2 (expect `deck_cut_inside_buildings_m2.domestic` near 0 and `deck_left_inside_buildings_m2` 0). Please check that
  the deck now meets the new sidewalk edge with no gap (the curb-gap check).
- Replacement table: the first-pass app part 23 "Terminal 2 walkway" (kept as a landside rest piece between x -797 and
  -766) now lies under the domestic `T2_garage_link`. The height-aware coverage should hand it to `domestic` on the re-run.
- New sha / sizes: domestic 11.50 MB, landside 21.23 MB (manifest entries updated by the builds).

### R3.2 Integration: list low decks over at-grade roads as plausibility conflicts (buildings-14)

`b3d_integrate` lists vertical clearance only for asset-over-deck cases. The anchored domestic departures loop
(`roadways.glb` deck top 4.73 m, `DECK_DEPTH` 1.2 m [inf]) has a 3.53-m soffit over 10 at-grade crossings: OSM 701476993,
701476994 (South Link Road), 701476988, 701476989, 701209939, 701476987 (Arrivals), 256787748 (Arrivals), 1274607795,
1274606309, 1274827440. Please add them to `plausibility.conflicts` (deck over an at-grade road < 4.6 m).

The curb level (4.877 m) is the published T3 L1 -> L2 16 ft [pub at T3], carried along the continuous loop [inf]. It was NOT
raised: a deck top >= 5.8 m would contradict the published T3 L2 at the T3 curb. With a 16-ft rise between the stacked
arrivals / departures levels, the real clearance is 16 ft minus the curb step and the slab. A 0.75-0.9 m slab gives
~3.8-4.0 m: the stacked arrivals roadway is lower than 4.6 m by design. Please review `DECK_DEPTH` at the anchored loop (1.2 m
is the generic viaduct depth [inf]). A posted-clearance photo of the domestic arrivals level would settle it (owner question).

### R3.3 Integration: carry height bands in the footprint tiers (buildings-4, integration-5)

The F7 / F8 L1 rotunda drums lie ~1.05 m inside the BA-F footprint ring only under the ESE roof overhang. In 3-D they are
clear (`verify_domestic_r2.drum_overhead`, the gates.js solids dumped this round):
- soffit 9.69 m, drum top 8.55 m: 1.14 m clear;
- the facades are >= 0.1 m outside the largest drum;
- F8 L1 tunnel 1 stays >= 1.58 m below the soffit in all poses;
- the D3 L1 facade is 0.19 m clear of its drum.

The other drums under a roof (E6 / E9 / E11, soffit 9.05) clear by 0.5 m, B10 by 1.25 m. The integration footprint rings are
plan-only. Please carry the overhang's height band (soffit above the apron) so plan tests stop reading it as a wall.

### R3.4 Integration: BART station vs taxilane 302 (buildings-8, rejected)

No geometry change. The modelled north face (OSM way 221663595) is 36.75 m from lane 302. The observed NAIP 2024 north wall
line is 35.8 m from it (+-2 m), so the real building stands inside the inferred ADG-5 OFA (42.1 m). Please record the
conflict as an existing condition of the observed building (`verify_landside`: body >= NAIP line - 0.5 m), or source the ADG
of lane 302 (the 5 is inferred from the largest stand served).

### R3.5 Integration: order of rebuilds (buildings-3)

The AirTrain pier sites now avoid `data/sfo_landside.json` carriageways (+0.5 m) and keep caps >= 4.6 m over the
`roadways.glb` LOD0 deck tops, with straddle bents where no single column fits. Results: piers 91 -> 86 (19 bents), column
feet on a road 3 -> 0, no pier vertex over a deck. If `roadways.glb` changes in plan (R3.1), please re-run
`python3 tools/blender/verify_landside.py`; its checks read the current `roadways.glb`. If it reports a column on a deck,
tell this track and the landside asset will be rebuilt. The roadway trim reads landside triangles, so the order is
roadways -> verify_landside -> (landside rebuild if needed) -> b3d_integrate.

### R3.6 Integration: ITB curb canopy over the departures plate (buildings-7)

The ITB curb canopy slab is now 0.45 m (was 0.6) under an unchanged top: soffit 16.05 m. `verify_itb` checks it against the
`roadways.glb` plate at >= 4.6 m (4.52 -> 4.67 m at (-1278.4, 359.9), deck 11.38 m). Please confirm it in
`plausibility.notes` on the re-run.

### R3.7 Engine (env-7, engine_closeout R2.4): BA-G mullion finish recorded

`tools/buildings/spec_itb.json` now has `ba_g.mullion_finish`: light silver-white mullions / transoms, `obs`, low confidence,
status unverified. The source is one openly licensed photo, `photo_a2` (Wikimedia Commons, Pi.1415926535, CC BY-SA 4.0, cached
`refs/cache/buildings/review_likeness/a2.jpg`). It applies to Boarding Area G only; piers B-F have no openly licensed close
photo (not verified). The app material may follow for BA-G. The ITB asset's `mullion` material is already light aluminium
(178 / 182 / 186, metallic 0.6).

### R3.8 Owner (open questions; defaults kept and tagged)

- Grand Hyatt at SFO height: default 44 m [inf] (40-48; 12 storeys [pub]); the a2-scaled garage heights move -/+2.4 m with
  it. The FAA OE/AAA determination for the hotel would be the primary source.
- Courtyard 3 Connector height: default 33.0 m [inf] (32-36; penthouse 38.0 obs low).
- Control-tower height family: F2 (rim 64.0, observation-anchored) stays the default; F1 (rim 67.36 = 221 ft) is the
  published-height hypothesis.
- T2-garage connector level: modelled 9.43-14.38 m from the roadway clearance [inf]; the NAIP shadow suggests a top near
  24 m. A photo of the T2 curb would settle it.
- Posted vertical clearance on the domestic arrivals level (R3.2).
