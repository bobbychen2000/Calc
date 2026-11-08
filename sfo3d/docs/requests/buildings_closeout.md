# Requests from the buildings track (Blender assets: tower, ITB, domestic, landside)

From: owner of `tools/blender/**` (except the integration files `b3d_integrate.py`, `b3d_lod2_check.py`, `b3d_split.py`,
`b3d_views_job.mjs`, `b3d_glass_job.mjs`, `build_roadways.py`, `roadways_net.py`), `tools/buildings/**`, the
`data/buildings3d/{tower,tower_f1,tower_lod2,itb,itb_lod2,domestic,domestic_lod2,landside,landside_lod2}.glb` assets and `lsu_*`
units, their `manifest.json` entries, `docs/drawings/buildings/**`. What changed on this side is in `docs/research/buildings3d.md`
(the "Close-out round 3" sections of the ITB, landside and domestic groups) and `manifest.json#<group>`.

## Round 3 (close-out round 3, 6 Nov 2026; findings `docs/requests/closeout3_findings.json#groups.buildings`)

Rebuilt in this round: `domestic.glb` / `domestic_lod2.glb` (6 Nov 05:39Z, again 7 Nov 03:36Z after the back-face QA), `landside.glb` / `landside_lod2.glb` + `lsu_*` (6 Nov
05:43Z, again 7 Nov 02:11Z after the back-face QA - R3.9; `b3d_split.py` re-run each time), `itb.glb` / `itb_lod2.glb` (7 Nov
01:55Z, R3.6). `integration.json` (03:59Z on 6 Nov) and `roadways.glb` predate all three.

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
- New sizes: domestic 11.58 MB (7 Nov 03:36Z), landside 21.13 MB (7 Nov 02:11Z), itb 6.46 MB (manifest entries updated by the builds).
- The 7 Nov domestic rebuild also closes a 5-m hole in the T2 face beside the connector (back-face QA; `dom_geom.World.splits`) - the
  connector stretch of the face is now the only opening, as `t2_curb` assumes.

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

The ITB curb canopy slab is now 0.45 m (was 0.6) under an unchanged top: soffit 16.05 m. `itb.glb` rebuilt 7 Nov 01:55Z.
`verify_itb` checks it against the `roadways.glb` LOD0 deck triangles under the canopy plan: **4.70 m** (126 checks, 0 failed;
the point sample at (-1278.4, 359.9), deck 11.38 m, gives 4.52 -> 4.67 m). Please confirm it in `plausibility.notes` on the
re-run; `integration.json` pins the old itb.glb sha1.

### R3.7 Engine (env-7, engine_closeout R2.4): BA-G mullion finish recorded

`tools/buildings/spec_itb.json` now has `ba_g.mullion_finish`: light silver-white mullions / transoms, `obs`, low confidence,
status unverified. The source is one openly licensed photo, `photo_a2` (Wikimedia Commons, Pi.1415926535, CC BY-SA 4.0, cached
`refs/cache/buildings/review_likeness/a2.jpg`). It applies to Boarding Area G only; piers B-F have no openly licensed close
photo (not verified). The app material may follow for BA-G. The ITB asset's `mullion` material is already light aluminium
(178 / 182 / 186, metallic 0.6).

### R3.9 Integration: landside rebuilt again after the back-face QA (buildings-1)

`landside.glb` / `landside_lod2.glb` and the `lsu_*` units were rebuilt 7 Nov 02:11Z (`b3d_split.py` re-run; verify_landside
195 / 0). The back-face QA of the 6 Nov file found back faces the round-2 changes had introduced (details:
`docs/research/buildings3d.md`, landside "Close-out round 3"): the Garage A body's screened bands ran across the station block's
south stretch (one 131.7-m outline edge), the NE rotunda band had an open 0.12-m underside, and the single-sided perforated
screens showed their backs through the open levels of the curved ends. Plan footprint unchanged; LOD0 160,713 -> 159,459 tris,
21.13 MB. The roadway trim reads landside triangles: rebuild order as R3.5. The a2 view also shows the BART station's east end
open against the ITB outline: by design (internal edge), and covered by `itb.glb` in the app (ray test with itb / roadways / domestic
loaded: every a2 ray through the BART end's red pixels ends on an `itb.glb` front face, the ITB core) - no action needed unless the ITB core outline changes.

### R3.10 Environment / engine (and integration): BA-B glass vs Cycles at the same camera and sun (buildings-5)

The domestic glass no longer carries the baked AO as glTF occlusion (three.js applied it to the IBL reflection through its
specular occlusion; low tier pierB wall median (20, 24, 25) -> (27, 35, 36)). Measured like-for-like this round: the app camera and
sun were logged (`tools/blender/c3_app_views_job.mjs`, `out/buildings3d/c3/appB2/c3_info.json`: view `gate:B20,110,1,12`, eye
(-1018.5, 28.3, 768.7), fov 50, sun az 133.9 / el 41.6, snapshot time) and the same camera / sun rendered in Cycles
(`out/buildings3d/domestic_app_pierB_c3.png`, `render_domestic.py --views appcam --appcam <c3_info.json>:pierB`). BA-B wall median:
Cycles (58, 64, 71), app low (27, 35, 36), app high (29, 36, 37) - so it is not the low tier's missing SSR. Normalised to the white
fascia in the same frames, glass / fascia is 0.15-0.17 in the app against 0.33 in Cycles, while the sky in the same frames is (126,
146, 161) in the app against (166, 182, 194) in Cycles; the panes are sky-reflection dominated (IOR 1.9 coated glass). Please
compare the app's IBL / sky radiance near the horizon with Cycles' sky at this sun (the same pair of images), and the glass
material's environment response (`js/three/buildings3d.js` kind `hall`). The asset's glass values stay (no openly licensed BA-B
photo to aim a material-only lift at).

### R3.8 Owner (open questions; defaults kept and tagged)

- Grand Hyatt at SFO height: default 44 m [inf] (40-48; 12 storeys [pub]); the a2-scaled garage heights move -/+2.4 m with
  it. The FAA OE/AAA determination for the hotel would be the primary source.
  Searched again 7 Nov (web): SFO / Hyatt / contractor pages give 12 storeys and 351 rooms, no height; the 355-ft figures online
  belong to the Grand Hyatt at Union Square. The Courtyard 3 Connector: "six-story" office building [pub HOK / Hensel Phelps],
  no height; its 2019 SF Arts Commission civic-design deck (sfgov.org/arts) did not download (HTTP 504).
- Courtyard 3 Connector height: default 33.0 m [inf] (32-36; penthouse 38.0 obs low).
- Control-tower height family: F2 (rim 64.0, observation-anchored) stays the default; F1 (rim 67.36 = 221 ft) is the
  published-height hypothesis.
- T2-garage connector level: modelled 9.43-14.38 m from the roadway clearance [inf]; the NAIP shadow suggests a top near
  24 m. A photo of the T2 curb would settle it.
- Posted vertical clearance on the domestic arrivals level (R3.2).

## Round 3 - fix round 2 (7 Nov 2026; verifier round-1 findings v1-v10 for buildings)

Rebuilt in this round (one heavy-lock hold, `out/buildings3d/c3f2/chainH.sh`): `domestic.glb` / `domestic_lod2.glb` (v1),
`landside.glb` / `landside_lod2.glb` + `lsu_*` (v2-v4, `b3d_split.py` re-run), `itb.glb` / `itb_lod2.glb` and `tower.glb` /
`tower_f1.glb` / `tower_lod2.glb` (one glass AO rule, v8). Numbers: `docs/research/buildings3d.md` ("Close-out round 3, fix round 2"
in each group) and `manifest.json#<group>.closeout_r3_fix2`.

### R3.11 Integration: re-run after the fix-2 rebuilds (all four buildings assets changed)

`integration.json` pins the asset sha1s; all four groups were rebuilt. Order as R3.5: `roadways` (unchanged unless R3.12) ->
`python3 tools/blender/verify_landside.py` -> `b3d_integrate.py` / `b3d_lod2_check.py`. What changed in plan / height:
- domestic: no footprint change. Bridge-attachment parts follow the per-pier walkway levels (below); the 23 BA-C / BA-D
  bulkheads above the roofs and the BA-D overhang notches at the doors are gone; the BA-C / BA-D facade bands moved to the photo
  a1 ratios. Drum notches are now taken per drum from its rotunda floor `Hr` (the BA-D roofs are no longer notched round the
  D4 / D5 / D14 / D15 / D16 drums: drum tops 6.70-6.75 m under the 7.69-m slab underside).
- landside: Superbay LOD2 closed (walls up to a soffit, fascia, spine walls); Superbay LOD0 / LOD1 spine soffit + end fascias +
  hip-end walls; garage LOD2 drum-ring inner faces and portal recess sides; Garage A station-block east-face lining; central-garage
  sliver linings; car instances de-overlapped (oriented footprints; some dropped or shortened) and the LOD1 cars on the deck.
- itb / tower: glass materials no longer carry the glTF occlusion texture (geometry unchanged).

### R3.12 Integration: T2 departures curb - close the 0.13-0.26 m slot at the deck edge (verifier v7)

The verifier's sections every 7.5 m along z 165-255 find the `roadways.glb` `L0_domestic_departures` deck east edge 0.13-0.26 m
short of the domestic T2 sidewalk's west (kerb) edge, and the deck end has no edge face, so a slot runs along the whole T2 curb
(section z 210: deck 3.53-4.73 m ends at x -754.16; sidewalk 4.27-4.88 m with its kerb face at -754.02). The sidewalk stands on the
NAIP-derived curb line (`tools/blender/dom_geom.py` `T2_SIDEWALK_POLY`, the deck-side edge 5.85 m off the T2 face line [obs NAIP
2024 roof edge + inf offset]) and is not moved by this track. Please extend the deck to the sidewalk edge (or add a kerb return /
edge face) and add T2 to the `curb_gap` check (it covers only the ITB plate today).

### R3.10 (rewritten) Environment / engine: BA-B glass vs Cycles - the reflected apron, not the sky (verifier v8)

The round-3 R3.10 compared the sky pixels of the app and Cycles frames. That does not test what the panes reflect: the logged
pierB camera (`out/buildings3d/c3/appB2/c3_info.json`: eye (-1018.5, 28.3, 768.7), target y 5.435, pitch 12 deg down, fov 50)
looks at vertical BA-B panes, so the mirror direction is ~12 deg BELOW the horizon - the apron / the IBL lower hemisphere. Please
compare the app's environment lower hemisphere / ground reflection (or SSR, where the tier has it) with Cycles' reflected sunlit
apron at this camera and sun (az 133.9 / el 41.6): Cycles BA-B wall median (58, 64, 71) vs app (27, 35, 36) low / (29, 36, 37)
high. Glass AO is no longer a factor in any building asset: ONE rule for all four assets since fix 2 - no glTF occlusion texture on
a glass material (`build_domestic.py`, `build_itb.py`, `build_landside.py`, `build_tower.py`; the bake image stays in the
material only as the bake target). three.js applies `aoMap` to the indirect diffuse and, via its specular occlusion, to the IBL
reflection, while Cycles ignores the glTF occlusion - so AO on glass made the two renderers disagree by construction.

### R3.13 Bridges: the domestic asset now reads `js/live/gates.js` through a dump (verifier v1)

`tools/blender/app_bridges.mjs` (Node, no browser, ~1 min) runs gates.js and writes `tools/blender/app_bridges.json`: per bridge
the pier level `Hb` (DEPARTURE_LEVELS), the rotunda floor `Hr`, the fixed-walkway polyline with its floor heights and the rest
solids, plus the SHA-256 of its inputs. `dom_geom.py` sizes every door frame, vestibule, overhang notch, drum notch and
bridge-entered pod from it; `verify_domestic.py`, `verify_domestic_r2.py` and `verify_itb.py` test the walkways in their own
height bands from it and FAIL when the dump is stale. Cross-checked against the browser extraction `out/draw/scene2d.json`
(7 Nov 10:35Z): 131 / 131 bridges, Hb / Hr / rotR within 0.0005 m. After any change to DEPARTURE_LEVELS, the walk polylines or
the rotunda heights, please re-run `node tools/blender/app_bridges.mjs` and tell this track (domestic rebuild). Your R3.2.1
(bulkheads, door surrounds, vestibules, concourse glazing at the photo ratios) is done.

### Fix round 2 results (rebuilt 7 Nov 13:11-13:22Z; checks 13:48-14:10Z)

The rebuilds R3.11 announces are done: `domestic.glb` / `domestic_lod2.glb` 13:11Z, `landside.glb` / `landside_lod2.glb`
13:15Z with the lsu units split 13:48Z, `itb.glb` / `itb_lod2.glb` 13:16Z, `tower.glb` / `tower_f1.glb` / `tower_lod2.glb`
13:22Z. Every build check passes: verify_domestic 61 / 0, verify_domestic_r2 n_fail 0, verify_landside 198 / 0, verify_itb
126 / 0, tower3d_verify 110 / 110 (F2 and F1). The numbers that matter to other tracks:
- **Bridges (R3.13).** The verifier's `brsolids.py` with your bc_after2 geometry gives domestic walkway contact
  20.68 -> 10.71 m2. Every C / D bridge is <= 0.31 m2, with 0 rotunda / tunnel / cab contacts. The remaining B16 1.45 / B11
  0.85 m2 come from the box representation of a sloped walkway (one height band for the whole segment); they are not an
  overlap, so nothing is needed from you. ITB: 0 of 45 A / G walkways above their host roof.
- **Integration (R3.11).** No footprint change in any group. Landside LOD2 is closed: back-face hits with the LOD2 neighbours
  15,718 -> 138. The car instances changed (1,737 -> 1,724), so the instanced car tris changed too: LOD0 168,718 -> 167,304.
  Glass materials carry no glTF occlusion in any of the nine files. R3.12 (the T2 curb slot) is still open on your side.
- **Environment / engine (R3.10).** Removing AO from the ITB glass moved the app's i4 clear-bay / frit ratio only from
  0.690 to 0.700 (photo ~0.7). The BA-B glass has carried no AO since close-out r3, and the app vs Cycles gap at pierB
  remained (app (27, 35, 36) low / (29, 36, 37) high vs Cycles (58, 64, 71)). So glass AO is not the cause of that gap, and
  the reflected-apron comparison asked for in R3.10 stands.

## Round 4 (residuals) - close-out round 4, fix round 1 (8 Nov 2026; the round-3 verifier's round-2 residuals)

Rebuilt (one asset at a time under `out/.heavy2.lock`): `itb.glb` / `itb_lod2.glb` 17:18Z, `domestic.glb` / `domestic_lod2.glb`
17:21Z, `tower.glb` / `tower_f1.glb` / `tower_lod2.glb` 17:31Z (`--no-manifest`; bytes / verification patched by
`tools/blender/c4_manifest.py`), `landside.glb` / `landside_lod2.glb` 17:36Z with the `lsu_*` units re-split 17:36Z
(`b3d_split.py`, run, not edited). `tools/blender/app_bridges.json` re-dumped 17:13Z: its content was identical (131 bridges, max
difference 0 m); only the input hashes of `data/sfo_stands.js` / `js/live/airport.js` had moved (comment edits). Records:
`manifest.json#<group>.closeout_r4`; work log and every before / after file: scratchpad `c4/buildings/NOTES.md`.

### R4.1 The app's walkway ends are closed by the 3-D assets (major; ITB + domestic)

Root cause. `js/live/gates.js` starts the fixed walkway at the data's attach point (`walk[0]`, trimmed only where it lies inside
a drawn outline). At the ITB the attach points lie up to 0.96 m OUTSIDE the SFO Museum outline the piers are extruded from (and up
to 1.0 m inside it); at the BA-G bump-outs some walkway edges pass the bump-out's corner. The ITB had nothing between facade and
walkway end. The domestic doors had three faults: the walkway direction was taken towards the first stands-polyline point
> 0.5 m from the trimmed start - for E8 / B2 that is the attach point BEHIND the start, inside the building, so no facade was found
and the door was dropped; the vestibule ran from the centreline facade point only (oblique facades stayed open on one side: B2,
and B11S / C4 / D11 / E2 at LOD1 / LOD2); and drum notches / vestibule clips used the radius UPPER BOUND (2.2-2.45 m) instead
of the drum the app draws (1.5-2.1 m), leaving 0.4-0.6 m between the asset and the drum that closes a short walkway (E3 / E9 / F7
/ F8).

Fix (`tools/blender/bridge_head.py`, shared): the closing box of a walkway end is measured in the walkway frame over the whole
3.2-m vestibule width (depth samples every 0.1 m): a VESTIBULE from 0.15 m inside the deepest facade point to the walkway's end
face where any part of the end lies > 0.02 m in front of the facade; a NUB (0.03 m behind the facade plane) where the end lies
inside the facade but its edge passes a corner; nothing where the end is inside across its width. Boxes are clipped 0.05 m clear of
every OTHER bridge's fixed walkway solid and drum and of the bridge's own drum (app_bridges.json); stacked walkways at one head
(A6 / A11 upper deck) share one box. `itb_geom.bridge_heads` adds parts `ba_bridge_heads` (shell, LOD0 / LOD1 / LOD2 against
each LOD's own outline) and `ba_bridge_doors` (LOD0 door surrounds, as dom_geom). `dom_geom.bridge_doors` takes the start and
direction from app_bridges.json, uses the same box, the drawn drum radius (`rotunda_drums`: `r` = app `rotR`, `r_max` kept),
and skips walkways drawn from a sibling's (walkFrom > 0: F11 / F13 / F15 L2 had duplicate coplanar doors).

| check (`tools/blender/walkend_check.py`: gap <= 0.10 m at 7 offsets x floor + 0.3 / 1.5 / 2.7 m) | before | after |
|---|---|---|
| ITB A / G walkway ends open, LOD0 / LOD1 / LOD2 / itb_lod2.glb | 27 / 27 / 27 / 27 of 46 (max 10.08 m) | 0 / 0 / 0 / 0 (max <= 0.0 m) |
| domestic B-F walkway ends open, LOD0 / LOD1 / LOD2 / domestic_lod2.glb | 6 / 10 / 10 / 10 of 80 | 0 / 0 / 0 / 0 |

Plausibility: every closing box against every bridge solid of the bridges track's bc_after2 geometry in the rest AND all docked
poses: own walkway only (nubs G4 / G8 / G9 L1, D14 / F5 L1, the A11 shared head); ITB vestibules reach <= 0.97 m beyond the
outline; A / G stand envelopes >= 5.35 m from the 3-D footprint; verify_domestic_r2 drums 0 contacts of 415 hulls, drum_overhead
min 0.92 m. The verifier's `brsolids.py`: ITB 23 -> 40, domestic 73 -> 74 contacts - all at the bridge's own building end (door
leaf 0.064 m2, the rest walkway solid's 0.12 m past `walk[0]`, nubs F5 1.13 / D14 0.46 m2, D15 0.27 m2 where the shrunk drum notch
puts the facade back at the walkway crossing). Budget: itb L0 69,287 -> 71,939 tris, 6.46 -> 6.93 MB; domestic L0 79,913 -> 79,070
tris, 11.37 -> 11.17 MB. Checks: verify_itb 126 / 0 -> 135 / 0, verify_domestic 61 / 0 -> 67 / 0, verify_domestic_r2 n_fail 0.

New checks: `verify_itb.py` / `verify_domestic.py` run walkend_check at every LOD of both files (FAIL on any open end; domestic
F22 L2 exempt, R4.5), verify_itb checks the vestibules' reach beyond the outline (<= 1.2 m), and both run `bf_rays` in a new NEAR
mode (R4.3).

### R4.2 Landside minors (cars, portal opening, spandrels) and one glazing rule

- **Cars vs static geometry.** `landside_cars.StaticIndex` + `resolve_overlaps(static=)`: a car whose footprint meets the
  building's LOD0 triangles in its own band (bottom + 0.10 .. top - 0.05) gives way (shorter shape, else dropped). Cars touching
  static geometry 13 -> 0 (verify_landside now checks it); 1,724 -> 1,711 cars (CG 331 -> 318); NAIP-detected CG cars reproduced
  0.839 -> 0.799 (gate 0.75).
- **Garage A station block east face.** Portal holes keep `PORTAL_CLEAR` 0.10 m to the AirTrain deck (they were inset 0.6 m into
  the deck + 0.2 interval); the lining follows. Face plane, y 18.3-20.4 m: wall to s 7.94 / from 12.17 against the deck 7.53-12.48
  (0.41 / 0.31 m into the jambs) -> wall to 7.44 / from 12.57 (0.09-0.10 m clear).
- **Spandrels.** `garage_facade` makes every spandrel / slab-edge band below the parapet a 0.2-m solid (inner face + caps).
  Central Garage unit with roadways only: `L0_cg_body` back-face hits 2,164 -> 20; landside LOD0 with full context 787 -> 770
  (cg_body 37 -> 3, station block 12 -> 9); LOD2 gate worst 25. LOD0 159,599 -> 168,815 tris, 21.13 -> 21.97 MB.
- **Glazing AO.** One rule in all four builders, keyed on a material flag: no glTF occlusion when `MATS[key]['glazing']` (else
  'glass' in the key). `ibf_curtain` (tower) and `ribbon` (landside) carry `glazing=True`: glazing materials with occlusion 5 -> 0
  across all asset files. Tower geometry unchanged, tower3d_verify 110 / 110 (F1 and F2), glTF-Validator 0 errors.

verify_landside 198 / 0 -> 199 / 0 (the new car check; before the rebuild it failed with 13).

### R4.3 Back-face rays: near mode (verifier v9)

`bf_rays.py` gains `near` (m): context faces occlude only within `near` m in front of a ray's first own face - a camera that close
(round 3 let a building 190-250 m away hide the Central Garage's open storeys). verify_itb and verify_domestic run it at LOD0 and
LOD2 (10 m; per-node limit 60, the landside gate). ITB: 55 (hall hangers, identical before) / 0. Domestic: LOD0 1,155 (T3W 574,
T1 453, T3E 74), LOD2 1,162 - IDENTICAL on the round-3 fix-2 file, so not from the bridge heads; the far context had hidden them
(they are not at the ITB abutment). Recorded as residuals (a regression above 1.05 x fails) and left for the next round to trace
(OPEN). verify_landside keeps its LOD2 gate; its LOD0 numbers are above.

### R4.4 Integration: re-run after the round-4 rebuilds (all four buildings assets changed)

Order as R3.5: `roadways` -> `python3 tools/blender/verify_landside.py` -> `b3d_integrate.py` / `b3d_lod2_check.py`. Plan changes:
- itb: 25 closing boxes per LOD outside the SFO Museum A / G outlines (<= 0.97 m, between the facade and the app walkway end; the
  outline itself unchanged). They enter the asset footprints that gates.js reads for the VDGS brackets (`B3D_INTEGRATION`).
- domestic: vestibules now span the walkway width (B2, E8 new; oblique ends deeper), drum notches follow the drawn drum radius
  (smaller notches: facades 0.1 m from the drums at E3 / E9 / F7 / F8 / D-pier), 3 duplicate twin doors gone.
- landside: car instances 1,724 -> 1,711; station-block openings wider; spandrel linings (no footprint change).
- tower: materials only.

### R4.5 Bridges data (bridges track closed; owner / next bridges round)

F22 L2's fixed walkway starts at (-1267.58, -272.13), 17.6 m from Boarding Area F and 1.48 m from F22 L1's drum (centre
(-1270.55, -271.87), r 1.50), at floor 4.88 m against L1's rotunda floor 3.55 m: the walkway end floats with no building or
drum to close it. It is listed as exempt in verify_domestic; the fix belongs to the stand / bridge data (`data/sfo_stands.*`), not
to the buildings track. `js/live/gates.js` was not edited.

### Round 4 dispositions (verifier findings in scratchpad `c3_verify2_buildings.json`)

| finding | status | evidence |
|---|---|---|
| v1 domestic per-pier levels | confirmed fixed (r3) | no change needed; walkway ends now gated (R4.1) |
| ITB walkway ends 0.3-0.9 m short + domestic E8 / E9 / F8 (major) | fixed | R4.1: 27 -> 0 / 6-10 -> 0 open, every LOD |
| v2 Superbay LOD2 | confirmed fixed | LOD2 gate worst 25 |
| v3 cars | confirmed fixed | 0 overlapping pairs (1,703 instances) |
| CG roof cars vs coping / rim | fixed | R4.2: 13 -> 0 |
| v4 station block lining | confirmed fixed | 12 -> 9 hits with context |
| station block opening vs AirTrain deck | fixed | R4.2: 0.41 / 0.31 m -> 0.09-0.10 m clear |
| v9 back-face coverage + CG spandrels | fixed (CG) / partly (gates) | R4.2 / R4.3: cg_body 2,164 -> 20; near mode in verify_itb / verify_domestic; domestic residuals open |
| v8 glazing AO by name | fixed | R4.2: 5 -> 0 |
| v9 swalk / walkend in verify scripts | partly | walkend gate added; the slope-exact swalk stays a QA tool (domestic r2 box probe kept) |
| v6 scene2d / records | confirmed fixed | - |
| v7 T2 curb slot | integration | 0.045-0.10 m with an edge face (their side) |
| v5 / v10 drawings | owner | redraw BL-02 / BL-03 / BI-03 / BI-04 or keep the NOT DRAWN notes (open question) |
