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

Plausibility: every closing box against every bridge solid of the bridges track's bc_after2 geometry [note, close-out r5: that dump
was of 7 Nov 06:21Z, before the gates.js commit fe78e17 of 07:16Z; the round-4 verifier's fresh bcheck2 run gave the same result] in
the rest AND all docked poses: own walkway only (nubs G4 / G8 / G9 L1, D14 / F5 L1, the A11 shared head); ITB vestibules reach <= 0.97 m beyond the
outline; A / G stand envelopes >= 5.35 m from the 3-D footprint [corrected in close-out r5: 5.31 m (G7) to the ITB BA-G LOD0
triangles in integration.json, whose old_outline_dist is 5.35 m; verify_itb's own plan-footprint check reads 5.354 m]; verify_domestic_r2 drums 0 contacts of 415 hulls, drum_overhead
min 0.92 m. The verifier's `brsolids.py`: ITB 23 -> 40, domestic 73 -> 74 contacts - all at the bridge's own building end (door
leaf 0.064 m2, the rest walkway solid's 0.12 m past `walk[0]`, nubs F5 1.13 / D14 0.46 m2, D15 0.27 m2 where the shrunk drum notch
puts the facade back at the walkway crossing). Budget: itb L0 69,287 -> 71,939 tris, 6.46 -> 6.93 MB; domestic L0 79,913 -> 79,070
tris, 11.37 -> 11.17 MB. Checks: verify_itb 126 / 0 -> 135 / 0, verify_domestic 61 / 0 -> 67 / 0, verify_domestic_r2 n_fail 0.

App check (low tier, llvmpipe, `tools/blender/c3_app_views_job.mjs`, itb + roadways only): views of G6 L1 (short walkway into the
bump-out vestibule) and A1 L1 / L2 (vestibules with door surrounds at the BA-A facade) show the walkways entering the boxes with no
daylight between bridge and terminal (scratchpad `c4/buildings/app/c3_g6.png`, `c3_a1.png`; local, not committed).

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
| station block opening vs AirTrain deck | fixed [corrected in close-out r5: partly - the east-face jambs were fixed, the deck-1 opening on the stepped face 5.3 m out (a spandrel through the girder) and the far wall across both decks' parapets were not; closed in R5.1] | R4.2: 0.41 / 0.31 m -> 0.09-0.10 m clear |
| v9 back-face coverage + CG spandrels | fixed (CG) / partly (gates) | R4.2 / R4.3: cg_body 2,164 -> 20; near mode in verify_itb / verify_domestic; domestic residuals open |
| v8 glazing AO by name | fixed | R4.2: 5 -> 0 |
| v9 swalk / walkend in verify scripts | partly | walkend gate added; the slope-exact swalk stays a QA tool (domestic r2 box probe kept) |
| v6 scene2d / records | confirmed fixed | - |
| v7 T2 curb slot | integration | 0.045-0.10 m with an edge face (their side) |
| v5 / v10 drawings | owner | redraw BL-02 / BL-03 / BI-03 / BI-04 or keep the NOT DRAWN notes (open question) |

## Round 5 (residuals) - close-out round 5, fix round 1 (9 Nov 2026; the round-4 verifier's findings, scratchpad `c4_r4verify1_buildings.json`)

Rebuilt one at a time under `out/.heavy.lock`: `itb.glb` / `itb_lod2.glb` 02:39Z, `domestic.glb` / `domestic_lod2.glb` 02:54Z,
`landside.glb` / `landside_lod2.glb` 05:08Z (b_ls5; four earlier landside builds b_ls .. b_ls4 were test builds of the keep-out
rule, each superseded) with the `lsu_*` units re-split (`b3d_split.py`, run, not edited); then the roadways and the integration
re-run (R5.6). `tools/blender/app_bridges.json` was re-dumped three times (the runtime track keeps editing `js/live/gates.js`): every
dump had the same 131 bridges, max difference 0 m; only the input hash moved (verify_domestic: dump current). Records:
`manifest.json#<group>.closeout_r5` (`tools/blender/c5_manifest.py`); work log, every before / after file and the emulation
scripts: scratchpad `c5/buildings/` (NOTES.md). Before = the round-4 files (commit a5ecf67, copies in `c5/buildings/before/`);
every before / after pair below was measured with the same script on both files (the verifier's `xtri.py` md5 d44f6b44, re-run on
the round-4 file: identical to its round-4 log). No replays were run by this track (no tools/live harness numbers).

| file | round 4 | round 5 |
|---|---|---|
| itb.glb (LOD0 / LOD1 / LOD2 tris) | 6,934,336 B (71,939 / 38,683 / 7,092) | 6,807,008 B (71,929 / 38,683 / 5,884) |
| itb_lod2.glb (phone) | 772,664 B | 645,984 B (-16 %) |
| domestic.glb | 11,174,120 B (79,070 / 23,334 / 23,174) | 11,196,072 B (79,040 / 23,368 / 23,208) |
| domestic_lod2.glb (phone) | 2,848,024 B | 2,849,948 B |
| landside.glb | 21,966,188 B (168,815 / 94,789 / 22,258) | 22,339,248 B (171,079 / 97,025 / 22,937) |
| landside_lod2.glb (phone) | 2,892,136 B | 2,984,552 B (+3.2 %: the keep-out re-triangulation, R5.1) |

### R5.1 Buildings vs the AirTrain: one keep-out rule at every LOD (Garage A station block, Garage G, LTP garage 2, Grand Hyatt, RCC, BART, CG plinth)

Root cause. Every facade style (precast spandrels, slab-edge bands, screens, glazing, louvres) was built from its own outline with
no knowledge of where the guideway passes; round 4 fixed one face of the station block by hand (the east-face jambs). New module
`tools/blender/keepout.py`: the AirTrain's COLUMN HULL (at a plan point, the merged height intervals of the guideway triangles
over it; a non-vertical triangle contributes its plane height there, a vertical one its band) and `clip_mb`, which clears every
planar face of a building mesh out of it in the face's own frame (vertical faces: exact height intervals on equal steps <= 0.05 m
over the whole face; other faces: cells <= 0.10 m with a 5-point test, the cut intersected with the hull outline itself;
constrained-Delaunay re-triangulation, UVs by an affine fit). `landside_geom.airtrain_keepout` runs it on every building part:
LOD0 shells + details and LOD1 details against the LOD0 guideway, and the LOD2 parts against the LOD2 guideway (the coarse deck
is the outline simplified by 0.6 m: cut against the LOD0 hull, the LOD2 station-block jambs still crossed it by <= 0.14 m, 13
points, found on the b_ls4 file and fixed in b_ls5). KEEP_CLEAR 0.08 m in plan, 0.05 m above / below. Exempt by design: the portal
tunnels (the guideway's own lining). CONTACT rule for the Central Garage plinth (the garage structure built up to the guideway; its
walls stand on the deck outline): no clearance, cut only beyond 0.03 m inside the footprint - its walls stood up to 2.6 m deep
inside the deck box where the deck runs below h5 (82.8 m2 of faces inside the solid) -> 0.03 m2, all within 0.05 m of the
outline [corrected in fix round 2, R5f2.2: both figures were measured with the merged-interval hull that missed the deck box under
each parapet; by the closed-solid rule (the round-5 verifier's cgdepth2) the fix-1 plinth kept 43.4 m2 more than 0.05 m inside, up
to 1.22 m deep]. Also: the station block's hall back wall is holed over each block portal (deck +- PORTAL_CLEAR, the far-face lintel),
and the Garage G station vault is pulled in off its host's spandrels (`VAULT_REACH` 0.65 m, `VAULT_HOST_CLEAR` 0.33 m).

| AirTrain x building, edge-triangle crossing points (the verifier's `xtri.py` rule) | round 4 | round 5 |
|---|---|---|
| LOD0 garage_a_station_block x deck / track; _det x deck | 75 / 10; 32 | 0 / 0; 0 |
| LOD0 garage_g_body x station steel; _piers x deck / station steel | 83; 39 / 34 | 0; 0 / 0 |
| LOD0 ltp2_body x deck | 41 | 0 |
| LOD0 gh_body x track / deck | 41 / 38 | 0 / 0 |
| LOD0 rcc_louvres x deck; rcc_body x deck / piers | 44; 12 / 7 | 0; 0 / 0 |
| LOD0 garage_a_portal x deck (exempt lining) | 3 | 4 |
| LOD0 cg_plinth x decks / track (contact part) | 657 / 2 | 1,427 / 0, all within the contact band; beyond it 0 (verify_landside) |
| LOD1 (same rule, L1_ nodes) | 938 in 13 pairs | 1,431 in 4 pairs = the CG contact band + the exempt portal |
| LOD2 phone file `landside_lod2.glb`: garage_a / grand_hyatt / ltp_garage_2 / garage_g | 101 / 40 / 32 / 24 | 0 / 0 / 0 / 0 |
| LOD2: L2_central_garage (unclipped contact shell) | 149 | 149 (residual, below) |

The CG plinth's raw crossing count rose because its walls now END on the guideway's faces (coincident contact edges) instead of
running through them; the contact gate counts only crossings > 0.05 m inside the footprint and > 0.03 m inside the height
interval: 0. Cut by the keep-out (m2): LOD0 536.2 (cg_plinth 429.8 contact - walls and the plinth top cap where the deck soffit
runs below it, inside the closed deck box; station block 21.2 + det 2.0, garage_a_body 2.3, ltp2_body 26.3, rcc_body 25.8 +
louvres 5.5, gh_body 22.3, bart_body 0.95); LOD2 111.1 (garage_a_L2 66.4, gh_L2 21.3, ltp2_L2 17.5, bart_L2 6.0). The record is
`manifest.json#landside.airtrain.building_keepout` (from the next build; `out/buildings3d/landside_build.json#airtrain.keepout` now).

New gates in `verify_landside` (199 -> 202 checks, 0 failed): every LOD0 AirTrain triangle edge against every LOD0 building
triangle and back, 0 crossings outside the exempt portal linings and the CG contact band; the same at LOD2 (L2_ nodes), 0 for every
building but the Central Garage, whose LOD2 shell is reported with a ceiling (`KEEP_CONTACT_L2_MAX` 160).

Residual (documented, not fixed): `L2_central_garage` keeps 149 crossings with the coarse guideway, 28 of them where its parapet wall
(top 20.65 m) rises <= 0.16 m above the simplified deck top (20.49-20.62 m) over two short runs at (-946.7, 416.9) - (-938.6, 414.2).
Clipping that shell with the contact rule against the LOD2 hull was tried (module emulation, `t/emu_ls_l2b.py`): 2,095 -> 3,641
triangles on the phone file (+1,546) - rejected. The remedy is a less-simplified LOD2 guideway deck along the CG (landside_airtrain
coarse `simplify(0.6)`), an open item.

### R5.2 Domestic fins through the app walkways (regression of R4.1) and door heads on roof planes (z-fight)

- **Fins.** `dom_geom` builds `APP_SOLIDS` (the app's fixed walkways and drums from `app_bridges.json`, each with its height band)
  and `set_door_keepouts` (every door surround's frame); a fin is emitted only in the spans of its height that stay FIN_CLEAR
  0.05 m off them (`fin_spans`, capped top and bottom). Fin contacts with app walkway / drum solids (the verifier's SAT test):
  27 sets -> 0 (B10, D4, D5, D11, D14, D15, D16, E6, E11 all clear). New verify_domestic gate (0 allowed).
- **Coplanar door heads.** The door surround's member top steps 0.04 m below any roof top / deck / soffit plane it would meet
  within 0.03 m (`tops_near`: host roof, the deck under a parapet, the slab soffit). Same-facing coplanar detail faces BA_C 5 /
  BA_B 2 -> 0 / 0 (C4 / C9 at 6.6 m, B10 / B16); new verify_domestic gate (0 allowed).

### R5.3 The ITB door surrounds clip the walkways / drums; LOD2 bridge heads lighter (phone path)

- `bridge_head.clip_member`: every door member (jambs, head, leaf) is tested against the other walkways and drums of its head
  (`fixed_solids_near`, the own seg-1 walkway excluded, the upper-deck walkway included), on its real footprint. A member whose
  top meets an obstacle starting > 0.1 m above its foot is capped VEST_CLEAR below it; otherwise the obstacle's stretch is cut out
  along the member (1-cm bisection); a member keeping less than half its length is dropped. 100 members: 85 kept, 3 capped, 2
  trimmed, 15 dropped (the dropped ones lay inside another walkway). Door surrounds vs app solids: A11 U 16 / A6 U 6 / A6 L1 seg 2 4
  triangles -> 0; A2 door to its drum 0.0026 -> 0.0535 m. New verify_itb gate (0 allowed).
- LOD2: the drum and other-bridge cuts use an 8-segment circumscribed polygon (`drum_disc`): LOD2 head triangles 1,756 -> 548;
  `itb_lod2.glb` 7,092 -> 5,884 triangles, 772,664 -> 645,984 B (below the round-3 size plus the 25 boxes). Gates: LOD2 heads <= 600,
  itb_lod2.glb <= 6,500.
- Walkway ends 0 / 46 open at every LOD (max gap 0.058 / 0.067 m LOD2); near-context back-face rays 55 / 0 (unchanged).
- verify_itb 135 -> 138 checks, 0 failed.

### R5.4 Domestic near-context back-face rays (T1 / T3W / T3E): traced and closed

Traced with `bf_rays` ray dumps: every T1 / T3W / T3E first hit came from a ray entering through the ITB core block (context) into
the halls' open junction - the walls there were hidden by the ITB occupancy (`exposed_pieces`), so the halls had no wall at the
ITB. `World.finish` tags that occupancy; `exposed_pieces(closure=)` returns the stretches hidden ONLY by the ITB and `emit_walls`
closes them with plain `panel_light` walls (no fins): 507.9 m2 [corrected in fix round 2, R5f2.3: ~30 % of them faced open air -
the 2-D occupancy is larger than the itb.glb core; now plain only where the ITB 3-D core covers them]. Near-context hits LOD0 1,155 -> 87 (worst T1 37), LOD2 1,162 ->
86. The per-node residuals are dropped; one merged-node residual stays (`L2_domestic` 88 = 83 x 1.05), per-node limit 60.
verify_domestic 67 -> 69 checks, 0 failed; verify_domestic_r2 n_fail 0.

### R5.5 Records (round 4)

Corrected in place with markers: the G7 envelope figure (5.31 m to the BA-G LOD0 triangles, integration.json; 5.35 m is the old
outline), the station-block disposition (fixed -> partly; closed in R5.1), and a note that the docked-pose plausibility used the
7 Nov 06:21Z bridge dump (before gates.js fe78e17; the round-4 verifier's fresh run gave the same result). verify_itb's overlap
NOTE now separates the data contacts (8.679 m2) from the asset's own head boxes (`plausibility.walkway_overlap_m2`). Future pose
tests re-dump the bridges first (`node tools/blender/app_bridges.mjs <out>`).

### R5.6 Integration: re-run after the round-5 rebuilds

Order as R4.4, final run after b_ls5 (`c5/buildings/final2/chain2.sh`). Plan changes for the integration: landside faces cut back
from the guideway (no footprint change beyond 0.1 m); domestic junction walls inside the ITB core outline [2-D outline: see R5f2.3]; ITB door members fewer
(no footprint change). Results (final run 05:12-05:22Z; before = the round-4
chain): `b3d_integrate` 7 conflicts / 15 notes - the conflict and note lines identical to round 4's report plus one informational
note (the old scene2d.json is stale; the walkway / drum tests now read the tracked `tools/blender/app_bridges.json`, see
integration_closeout R5.3); walkway / drum vs host: no conflict (as r4); nearest stand envelopes F12 2.91 m, F17 3.15 m, G7 5.31 m
(unchanged); footprint tiers 156,636 vertices, 0 outside; `b3d_lod2_check` 47 units / 0 flagged (r4 47 / 0); `tools/sat/check.py`
0 issues / 0 app issues / 41 warnings (r4 the same); verify_itb 138 / 0, verify_domestic 69 / 0, verify_domestic_r2 n_fail 0,
verify_landside 202 / 0 (all re-run after the last build, with the 03:31Z bridge dump, current). Lite (phone) path, the five
`*_lod2.glb` files: 62,323 -> 61,830 triangles (itb -1,208, domestic +34, landside +679, roadways +2), 7,317,568 -> 7,285,368 B.

### R5.7 Bridges data and drawings (owner; unchanged)

F22 L2 (R4.5) stays exempt in verify_domestic, one key only; the fix belongs to the stand / bridge data (feed L2 from L1's rotunda
with walkFrom, or correct its attach point to BA-F). Drawings BL-02 / BL-03 / BI-03 / BI-04: the tagged NOT DRAWN notes stand;
the round-4/5 bridge-head vestibules and door surrounds and the round-5 keep-out cuts are not on the sheets either. Both need the
owner (redraw, or keep the notes).

### Round 5 dispositions (verifier findings in scratchpad `c4_r4verify1_buildings.json`)

| finding | status | evidence |
|---|---|---|
| Garage A station block (deck-1 opening, far wall) + Garage G / LTP2 family vs AirTrain; no LOD0 test | fixed | R5.1: every non-exempt LOD0 / LOD1 / LOD2 pair 0 crossings (r4 1,118 points in 17 LOD0 pairs); CG plinth contact band only; gates at LOD0 + LOD2 |
| domestic fins through short walkways (drum-notch regression) | fixed | R5.2: 27 -> 0 contact sets; gate |
| ITB door surrounds vs other walkways / drums (A6, A11, A2) | fixed | R5.3: 26 -> 0 triangles, A2 0.0026 -> 0.0535 m; gate |
| ITB LOD2 head bloat (phone path) | fixed | R5.3: 1,756 -> 548 head tris; itb_lod2.glb 772,664 -> 645,984 B; budget gates |
| new coplanar z-fight pairs (BA_C / BA_B) | fixed | R5.2: 5 / 2 -> 0 / 0; gate |
| 1,155 near-context back-face hits T1 / T3 | fixed | R5.4: traced (open ITB junction), closed: 1,155 -> 87 LOD0, 1,162 -> 86 LOD2 |
| F22 L2 | needs owner | R5.7 (stand / bridge data) |
| record accuracy | fixed | R5.5 |
| drawings BL / BI | needs owner | R5.7 |
| (found this round) LOD2 jambs vs the coarse guideway | fixed | R5.1: 13 -> 0 (LOD2 hull) |
| (found this round) CG LOD2 shell vs the coarse guideway | deferred | R5.1 residual: 149 points (28 above the deck top, <= 0.16 m); the clip costs +1,546 phone tris |

## Round 5 (residuals) - close-out round 5, fix round 2 (9 Nov 2026; the round-5 verifier's findings, scratchpad `c5/buildings_ver1`)

Rebuilt one at a time under `out/.heavy.lock`: `domestic.glb` / `domestic_lod2.glb` 08:32Z (the ITB-coverage rule, R5f2.3; a first
build at 08:18Z used a rule that was then refined and is superseded), `landside.glb` / `landside_lod2.glb` 08:28Z and again 09:00Z
(R5f2.5: the Grand Hyatt mast fix found after the first build; `landside_lod2.glb` came out byte-identical) with the `lsu_*` units
re-split, then the roadways and the integration (integration_closeout "Round 5, fix round 2"); `itb.glb` unchanged.
`tools/blender/app_bridges.json` re-dumped with the rotunda pedestals (integration R5f2.3). Before = the fix-1 files (commit d1883bb /
HEAD 710babe, copies in scratchpad `c5/buildings/f2/before/`). Every before / after pair below ran on the same script on both files:
the round-5 verifier's `trainenv2` / `cgdepth2` rules (`f2/ls/lsck.py` md5 e92daa68, whose fix-1 arm reproduces the verifier's
numbers exactly: envelope LOD0 gh_body 9,039 samples, LOD2 GH 8,667 / Garage A 1,010; CG plinth 71,063 samples > 0.05 m deep, 1,012
> 0.30 m, max 1.218 m), its `xtri.py` (md5 d44f6b44) and `xtri_lod.py`, its `closure2.py` rule split by material
(`f2/eval/closure3.py`, md5 ceabcc87; fix-1 arm 152.2 m2 = the verifier's), and two own scripts (`f2/an/gate_mast.py`,
`f2/an/ghdist.py`). Work log: scratchpad `c5/buildings/NOTES.md`. No replays were run (harness for the record: invariants.mjs
e52f3dfd, build_stream.py 93da6fe0).

| file (LOD0 / LOD1 / LOD2 tris) | fix 1 | fix 2 |
|---|---|---|
| itb.glb / itb_lod2.glb | 6,807,008 B (71,929 / 38,683 / 5,884) / 645,984 B | unchanged |
| domestic.glb | 11,196,072 B (79,040 / 23,368 / 23,208) | 11,198,584 B (79,120 / 23,406 / 23,246) |
| domestic_lod2.glb (phone) | 2,849,948 B | 2,854,668 B |
| landside.glb | 22,339,248 B (171,079 / 97,025 / 22,937) | 22,245,560 B (170,430 / 96,386 / 22,700) |
| landside_lod2.glb (phone) | 2,984,552 B | 2,951,776 B (-1.1 %) |
| the five `*_lod2.glb` (phone path) | 61,830 tris, 7,285,368 B | 61,631 tris, 7,257,312 B |

| check (same script both arms) | fix 1 | fix 2 |
|---|---|---|
| buildings inside the AirTrain vehicle envelope, LOD0 (trainenv2 rule) | gh_body 9,039 samples | 0 |
| the same, LOD2 (phone file) | L2_grand_hyatt 8,667, L2_garage_a 1,010 | 0 |
| Grand Hyatt body: plan distance to the guideway deck (`ghdist`) | 0 m (323 vertices over the deck, 0-44 m) | 5.11 m (0 over it) |
| CG plinth > 0.05 m inside the CLOSED deck box (cgdepth2 rule) | 71,063 samples, 43.4 m2 (area-weighted), max 1.218 m | 496 samples, 0.85 m2, max 0.232 m |
| the same, > 0.30 m deep | 1,012 samples | 0 |
| other buildings > 0.05 m inside the deck box | station block 0.47, gh_body 0.46, rcc louvres 0.56 m2 | 0 |
| AirTrain x building crossings LOD0 (`xtri`) | 4 pairs / 1,431 points (CG contact + exempt portal) | 4 pairs / 1,329 points (the same two kinds; verify_landside: 0 beyond the contact band) |
| the same, LOD2 (`xtri_lod`) | 3 pairs / 149 (Central Garage, deferred) | 3 / 149 (unchanged, R5f2.4) |
| domestic plain junction walls facing open air (`closure3`) | 152.2 m2 (T1 27.1, T3W 125.1) | 6.0 m2 (T1, coverage-cell edges); the exposed stretches carry the hall's bands (158.0 m2) |
| Grand Hyatt roof steel outside the roof (`gate_mast`) | 0.85 m | 0.00 m (the first fix-2 build: 12.04 m, R5f2.5) |
| verify_itb / verify_domestic / verify_domestic_r2 / verify_landside | 138 / 0, 69 / 0, n_fail 0, 202 / 0 | 138 / 0, 69 / 0, n_fail 0, 206 / 0 (+ envelope LOD0 / LOD2, deck box, mast gates) |

### R5f2.1 Buildings vs the AirTrain VEHICLE (bldg-1 'partly'): the envelope is part of the keep-out; the Grand Hyatt connector; Garage A LOD2 portals

- **Envelope.** R5.1 cleared faces out of the guideway STRUCTURE only. `landside_airtrain.vehicle_envelope` builds the car envelope
  as a closed prism: over each track (the deck offset BEAM_IN = 2.4 m inwards, the track centre lines guide_beams uses) +-ENV_HW
  1.5 m [inf: the running pads' outer edge 1.25 m + 0.25 m body overhang / clearance; the CX-100 car width is not sourced here], from
  the running surface (deck + PAD_H) to deck + PORTAL_H (4.2 m); the deck's clipped ends (portals into a body / the ITB) stay 0.9 m
  short, so the designed portal openings are untouched. `airtrain_keepout` clears every non-exempt part at every LOD out of it as well
  (keepout.clip_mb, the same face-frame clip; cut 0.04-0.06 m2 per part once the two items below were fixed). New verify_landside
  gates (0 allowed, LOD0 and LOD2): building triangles inside the envelope by the verifier's trainenv2 rule (track footprints +0.35 /
  -0.10 m, running surface + 0.15 .. + 3.5 m).
- **Grand Hyatt.** Checked against the source outline (SFO Museum 'Grand Hyatt Hotel', `sfom_union`): its only part narrower than
  3.2 m that touches the guideway is a 3.1 x 9 m FINGER at the NE corner, (-1614.6 .. -1609.0, 606.1 .. 615.5), 27.8 m2, reaching
  4.5 m onto the south track (11.9 m2 over the deck polygon) and touching the HYATT station polygon. We read it as the enclosed
  AirTrain bridge to the Grand Hyatt station that the Museum outline includes ('incl. podium / connector') [inf], not the 44-m slab.
  `hyatt()` takes it out of the slab / podium / LOD2 plan (opening of radius GH_CONN_W / 2 = 1.6 m, components touching the deck);
  the body now stands 5.11 m off the deck, so no tunnel and no keep-out cut is left in the hotel. The bridge itself is NOT modelled
  (span, level, enclosure: owner; manifest `unknown`). *(Round 6, R6.1: the bridge is now modelled from the [pub] level / enclosure and
  the [obs] finger, hotel face to the guideway edge; the 'south track' here is the guideway south of the hotel, i.e. the hotel-side one
  of the two single-track guideways at the station.)*
- **Garage A LOD2 station shell.** The LOD2 portal holes were the deck - 0.4 m with a 6-m dark recess whose back panel stood across
  both tracks at (-1397, 541) / (-1396, 527) inside the station block. Now as LOD0: the deck + PORTAL_CLEAR, and where the track runs
  on through the block (the east face of a garage with a station block) the recess reaches through it to the LOD0 tunnel's end
  (STATION_BLOCK_D + 10 m).

### R5f2.2 The keep-out hull is read as a CLOSED solid (CG plinth inside the deck box; the R5.1 record)

Root cause (as the verifier found): `keepout.Columns` merged plan-point intervals closer than GAP 2.0 m, and a non-vertical triangle
contributes a point (its plane height). Under a parapet the soffit and the parapet top are DECK_T + WALL_H = 2.5 m apart, so they
never merged and only the +-clear bands of the vertical faces were solid there: the plinth's top cap / slab soffit (18.13 / 18.15 m)
survived inside the deck edge, and so did facade remnants ~0.1 m wide inside the parapets of other buildings. Now each column is also
read as a closed solid - walking up the sorted plane heights, a DOWN-facing face (soffit) opens it and the next UP-facing face
(deck / parapet / walkway top) closes it (PAIR_MAX 3.0 m guards against an unclosed mesh) - united with the old reading; `near()`
tests the candidates' joint band. New verify_landside gate: LOD0 building surface more than 0.05 m inside the closed deck box (the
cgdepth2 rule), ceiling `KEEP_INSIDE_MAX_M2` 2.0 m2 (now 0.85; *corrected in Round 6, R6.2: not all on vertical faces - 259 of the 496
deep samples, incl. the 0.232-m maximum, were on the plinth TOP cap at 18.13 m where the deck runs below h5, (-956, 408) 177 samples /
0.232 m and (-1022, 154) 82 / 0.050 m; the vertical faces <= 0.053 m*). Record corrected: R5.1's
"82.8 m2 -> 0.03 m2 inside the solid" was measured with the same merged-interval hull that had the hole; by the closed-solid rule the
fix-1 plinth kept 43.4 m2 (area-weighted; the verifier's 71,063 samples / ~711 m2 count the slender triangles' samples) more than
0.05 m inside, max 1.22 m. The optional lowering of the plinth top to the local deck soffit was not needed (the contact clip now
removes the cap inside the box). *(Round 6, R6.2: wrong - the contact clip left the cap where it lay inside the box above a lower deck;
the plinth top now follows the local deck soffit.)*

### R5f2.3 Domestic ITB-junction walls: plain only where the ITB 3-D core covers them (bldg-6; R5.4 record)

R5.4's junction walls were hidden by the 2-D ITB occupancy, which is larger than the itb.glb core at those heights: ~30 % faced open
air as plain panel walls (152.2 m2). `emit_walls` now closes a junction stretch with a plain `panel_light` wall only where the ITB's
own LOD0 geometry stands in front of it: on 0.5-m cells (JUNCTION_DS) a horizontal ray along the outward normal meets a FRONT-facing
itb.glb LOD0 triangle (normal against the ray) within ITB_COVER_D 120 m (the verifier's ray length). The rest is EXPOSED and gets the
hall's facade bands (its band materials, the glazing among them) like any other stretch of that wall; a mullion fin only where no
ITB triangle of either facing stands within ITB_FIN_CLEAR 0.3 m in front (no fin through a back-to-back ITB wall). A first build of
this fix used 'any ITB triangle within 1 m' and left T1's 27.1 m2: a back-to-back ITB wall within 1 m faces into the ITB hall and is
culled from outside, so it hides nothing - hence front-facing only. Of the 507.9 m2 of junction walls 187.0 m2 are exposed (the
build's rule); by the verifier's rule 6.0 m2 of plain wall still faces open air (T1: the edges of the 0.5-m cells), 158.0 m2 of the
new faces now carry the bands. itb.glb is an input of the domestic build (built before it, the R4.4 order; this build read itb.glb
sha1 671d1ba4). The 87 m2 back-to-back coplanar with L0_itb_core stay (opposite-facing, single-sided: no z-fight).

### R5f2.4 Central Garage LOD2 shell vs the coarse guideway (deferred, unchanged)

As R5.1's residual: 149 crossings, ceiling 160 (verify_landside). The verifier's remedy (a less-simplified LOD2 deck along the CG,
then the contact clip) was not done this round: the R5.1 trial of the clip alone cost +1,546 phone triangles, and the
less-simplified deck adds its own. The clash is inside the closed deck box at LOD2 (the shell's parapet up to 0.16 m above the
coarse deck top at (-946.7, 416.9)); open item.

### R5f2.5 Grand Hyatt roof masts (found this round: a regression of R5f2.1, plus an r1 one)

After the connector finger left the slab plan, the f = 0.961 roof mast (photo l4 fractions of the outline's min-rect length) no
longer met the slab: `hyatt().east_pt` fell back to the outline axis and the mast (tube + 1.8-m crossbar, `gh_detail` steel, LOD0
and LOD1) stood at (-1620.6, 606.3), 44.0-46.7 m, 11.4 m off the hotel over the AirTrain (first fix-2 build, 08:28Z). The f = -0.008
mast stood 0.8 m beyond the curved south end since round 1 (the fix-1 file: 0.85 m). A mast is now kept 0.8 m inside the roof edge
with both crossbar ends 0.1 m inside it, else it goes to the nearest point 1.0 m inside [inf: positions; the masts are obs l4].
New verify_landside gate 'Hyatt: roof masts on the roof' (steel above the parapet outside the body plan, tol 0.05 m): first fix-2
build 12.04 m, fix 1 0.85 m, now 0.00 m. Rebuilt 09:00Z; `landside_lod2.glb` unchanged (the masts are LOD0 / LOD1 details).

### R5f2.6 Owner items (unchanged, not guessed)

F22 L2 (walkLen 1.641 < rotR 1.74; one-key exemption in verify_domestic), the BL-02 / BL-03 / BI-03 / BI-04 drawings, the ITB L3 level,
the domestic loop's posted clearance, interchange_2_2 / narrowed cuts - as R5.7 / integration R5.5. New: the Grand Hyatt's enclosed
AirTrain bridge (the outline's connector finger, not modelled) - its span, level and enclosure need a source. *(Round 6, R6.1 / R6.4:
level and enclosure were already [pub] in the spec; the bridge is modelled; the question is narrowed to the cross-section / roof form
and the crossing of the hotel-side track.)*

### R5f2.7 Integration re-run

Final run after the 09:00Z landside build (`c5/buildings/f2/fin3/chain.sh`, 09:06-09:23Z): `b3d_integrate` 7 conflicts / 15 notes - the
conflict and note lines identical to fix 1's report and to the first fix-2 run's (md5 of the lines f9f333a5); the bridge dump current
(stale inputs: none); walkway / drum / pedestal vs host: no contact above 0.05 m2 (131 pedestals now tested); nearest stand envelopes
F12 2.91 m, F17 3.15 m, G7 5.31 m (unchanged); footprint tiers 156,717 vertices, 0 outside; `b3d_lod2_check` 47 units / 0 flagged;
`tools/sat/check.py` 0 issues / 0 app issues / 41 warnings (= fix 1); verify_itb 138 / 0, verify_domestic 69 / 0, verify_domestic_r2
n_fail 0, verify_landside 206 / 0. The first fix-2 landside build's in-build verify_landside crashed in the new envelope gate (a local
import shadowed `MultiPoint`; fixed) and wrote 204 / 1 to `manifest.json#landside.verification`; the standalone re-run gave 205 / 0 and
the final build 206 / 0, which `c5_manifest.py` recorded. Roadways: two redirected dev builds after the last landside build (`f2/rw/gfin`,
`gfin3`) reproduce the installed `roadways.glb` / `roadways_lod2.glb` byte for byte (sha1 e2869621 / 3b031edf), so the roadway trims
do not depend on the mast fix or on the domestic rebuild order. Records: `manifest.json#<group>.closeout_r5` gained the `r5f2-*`
records (`out/buildings3d/c5/c5_manifest.json` -> `tools/blender/c5_manifest.py`, under the manifest flock).

### Round 5 fix round 2 dispositions (`c5/buildings_ver1` findings)

| finding | status | evidence |
|---|---|---|
| (major) roadways under-joint fallback walls | fixed | integration_closeout R5f2.1: through-deck walls LOD0 / LOD1 12.5 / 143.6 m2 -> 0 / 0; gates stop the build |
| bldg-1 'partly': AirTrain vehicle envelope (Grand Hyatt, Garage A LOD2) | fixed | R5f2.1: envelope LOD0 9,039 -> 0, LOD2 9,677 -> 0 samples; GH 5.11 m off the deck; gates LOD0 + LOD2; the GH bridge not modelled (owner) |
| keepout.Columns GAP: CG plinth inside the deck box; R5.1 record | fixed | R5f2.2: 43.4 -> 0.85 m2 (> 0.30 m: 1,012 -> 0); other buildings 1.49 -> 0 m2; gate (ceiling 2.0); R5.1 annotated |
| integ-1 / integ-2 LOD0-only (LOD1 soffits) | fixed | integration_closeout R5f2.2: LOD1 open into a hollow 174.6 -> 7.8 m; gate |
| integ-4 stale bridge dump + pedestal | fixed | integration_closeout R5f2.3: stale dump -> CONFLICT + exit 2; pedestals tested (0 contacts) |
| domestic closure walls facing open air; R5.4 record | fixed | R5f2.3: plain walls facing open air 152.2 -> 6.0 m2; R5.4 annotated |
| CG LOD2 shell vs the coarse guideway | deferred | R5f2.4: 149 (= fix 1), ceiling 160 |
| owner items (F22 L2, drawings, ITB L3, clearance, ic_2_2 / narrowed cuts) | needs owner | R5f2.6 (+ the GH AirTrain bridge) |
| (found this round) Grand Hyatt roof masts off the roof | fixed | R5f2.5: 12.04 / 0.85 -> 0.00 m; gate |

## Round 6 (follow-up on close-out round 5 verifier 2) - 9 Nov 2026

Input: SP/c5_r5verify2_buildings.json (5 minors; (a), (b), (e) are this doc's, (c) / (d) in integration_closeout Round 6). Work log
SP/c6/buildings/NOTES.md. Before / after on the same scripts: the new verify_landside (md5 5a791814) ran on the r5 files (landside.glb
md5 9bb0389f / landside_lod2 c2ad24a3, SP/c6/buildings/vbefore) and in-build on the round-6 files (aca13820 / 642b0760). No tools/live
replays; no renders.

### R6.1 Grand Hyatt: the enclosed AirTrain bridge is modelled (r5 verifier 2, (a)): fixed, cross-section / crossing to the owner

R5f2.1 took the outline's connector finger out of the slab and left nothing: the hotel stood 5.11 m from its own station. The repo
already sources the bridge's level and enclosure: spec_landside `gh_lobby_level` [pub, CONFIRMED] "AirTrain station connects at the
fourth floor"; the station entry and landside_airtrain `STATIONS['HYATT']` "hotel 4th floor via an enclosed bridge [pub]"; its plan is
the SFO Museum finger [obs]. Measured first (SP/c6/buildings/t/gh_geo.py, gh_sec.py; along the finger, s = 0 at its station end, 8.87
at the slab): the HYATT station polygon is an ISLAND platform between the two single-track guideways (s -10.2 .. 0); the hotel-side
guideway (R5's "south track") spans s -1.26 .. 3.79 and its vehicle envelope s -0.36 .. 2.89; the level field there is 19.751 m
(= the network level). So at the [pub] level the finger's station half lies in the train path.

`hyatt()` now builds `gh_bridge` (LOD0 / LOD1 shell; the same box inside `L2_grand_hyatt`): plan = the finger (+0.03 m, into the slab
face) minus the guideway polygon + `GH_BR_GAP` 0.15 m (LOD2: 0.40 m, the coarse LOD2 guideway), i.e. from the hotel face to the guideway
edge (15.8 m2, ~5 m); floor at the platform level 19.751 m [inf: network level; 4th-floor connection pub]; section [inf]: floor structure
0.4 m (dark metal edge, soffit), glazed sides and end 3.5 m clear, 0.5 m dark roof fascia, membrane roof (`GH_BR_*`). Triangles +54 at
LOD0 and LOD1, +10 at LOD2 (LOD0 / LOD1 / LOD2 170,430 / 96,386 / 22,700 -> 170,484 / 96,440 / 22,710). The keep-out cuts nothing on
it. Measured on the installed glb (t/gh_glb.py): bridge to every AirTrain triangle (deck, track, station steel) 0.146 m in plan at LOD0
/ LOD1, 0.396 m at LOD2, overlap 0; bridge to the hotel body 0.000 m; verify_landside: AirTrain x building crossings LOD0 / LOD2 0,
vehicle envelope LOD0 / LOD1 / LOD2 0 / 0 / 0, Hyatt masts on the roof 0.00 m, all Hyatt rows unchanged.

The record (manifest `landside.buildings.grand_hyatt`): `unknown` is narrowed to the bridge's cross-section (width beyond the 3.1-m
finger, clear height, glazing) and roof form, and to HOW it crosses the hotel-side track (over the vehicle envelope, under the deck, or
a hotel-side platform our island-platform reading misses); a new `conflicts` line states the [pub]-level vs [obs]-plan clash; the
crossing is in `not_modelled`. Not guessed: a bridge across the running track at the platform level would stand in the train path, and
a level over the envelope (>= 23.95 m) or under the deck (<= 18.15 m) contradicts the fourth-floor [pub] connection. **[Corrected in
round 7 (r6 verifier (a)-(b)):** the last clause was wrong. By the model's own storeys the hotel 4th floor is ~14 m (colonnade top),
UNDER the deck, and the platform level put the round-6 bridge mid-storey, 5.75 m above it. The 19.75-m level was the [inf] network
level, not a [pub] fact. Round 7 moves the bridge under the deck (R7.1).**]**

### R6.2 CG plinth record corrected; the plinth top follows the local deck soffit (r5 verifier 2, (b)): fixed

The R5f2.2 record and the `KEEP_INSIDE_MAX_M2` comment said the 0.85-m2 residual was all on vertical plinth faces; the verifier showed
259 of its 496 deep samples, incl. the 0.232-m maximum, on the plinth TOP cap (zt - 0.02 = 18.13 m) where the deck runs below h5:
(-956, 408) 177 samples / 0.232 m, (-1022, 154) 82 / 0.050 m. Both records are corrected (R5f2.2 above, landside_geom comment). Root
cause: the cap was at h5 - DECK_T everywhere. It now follows the local soffit: the cap polygon is segmentized to 2 m and each vertex
at min(h5, deck level) - DECK_T - 0.02 (`_at_levels()`: the AirTrain level field, built from the same region as
`landside_airtrain.build`). Emulation (t/cg_test.py): every cap vertex 0.020 m under the soffit, triangle centroids <= -0.011 m (at
(-956, 408) the soffit is 17.80-17.97 m; the cap was at 18.13). verify_landside deck box, LOD0: 0.85 m2 / max 0.232 m at (-954.6,
408.7) -> 0.85 m2 / max 0.053 m at (-837.2, 373.2) (> 0.30 m: 0 / 0). The area is unchanged at two decimals: the cap's area share
was < 0.005 m2 (large triangles, few deep samples); the 0.85 m2 are the vertical faces at <= 0.053 m. Ceiling 2.0 -> 1.0 m2.

### R6.3 Deck-box and envelope gates at every LOD; the Central Garage LOD2 depth is reported (r5 verifier 2, (e)): partly (reported + ceiling; clip deferred)

verify_landside runs the cgdepth2 deck-box rule per LOD against the guideway of the SAME LOD (LOD1 vs the L1_*_deck nodes, LOD2 vs the
coarse L2_airtrain_* nodes) and adds the area deeper than 0.30 m; the vehicle-envelope gate also runs on LOD1. Before (r5 files) ->
after (round 6): envelope LOD0 / LOD1 / LOD2 0 / 0 / 0 -> 0 / 0 / 0; deck box LOD1 0.85 m2 (max 0.232) -> 0.85 (max 0.053), ceiling
1.0; LOD2 311.18 m2 -> 311.18 m2, only `L2_central_garage` (> 0.30 m: 76.11 m2; max 0.686 m at (-796.6, 261.4) = the verifier's
0.686 m), ceiling `KEEP_INSIDE_L2_MAX_M2` 327.0 (+5 %) - a regression bound next to the 149 crossings (ceiling 160). The fix (a
less-simplified LOD2 deck along the CG, simplify ~0.2 m on its tiles, then the contact clip on cg_L2) was not cheap enough this round:
it changes the coarse guideway of three LOD2 tiles and re-triangulates the CG shell (+1,546 phone triangles in the R5.1 trial); the
clash stays inside the closed coarse deck box (hidden). Deferred. **[Corrected in round 7 (r6 verifier (e)):** the deferral reason was
wrong. 94 % of the residual (72,679 of 77,356 samples) was the LOD2 plinth top at the constant 18.15 m, at the two sites R6.2 fixed at
LOD0. The same soffit-following top at LOD2 needs no change to the coarse deck (R7.2).**]**

### R6.4 Owner items

As R5f2.6, with the Grand Hyatt item narrowed (R6.1): the bridge's cross-section and roof form, and how it crosses the hotel-side
AirTrain track (the [pub] fourth-floor connection vs the [obs] finger over the running track from the island platform). F22 L2, the
drawings, ITB L3, the posted clearance, interchange_2_2 / narrowed cuts unchanged.

### R6.5 Re-run (heavy lock, one job at a time; SP/c6/buildings/fin)

landside rebuild + b3d_split 0 (11:57Z; landside.glb 22,291,188 B), in-build verify_landside 209 checks / 0 failed (the before arm:
209 / 1 = only the new LOD2 deck-box gate at its provisional ceiling); roadways rebuild 0 (byte-identical glbs); b3d_integrate 7 conflicts
/ 15 notes (lines identical to round 5); b3d_lod2_check 47 / 0; check.py 0 / 0 / 41 warnings; verify_itb 138 / 0; verify_domestic
69 / 0. Manifest `landside` and `roadways` entries rewritten by their builds (under the manifest flock).

### Round 6 dispositions (`c5_r5verify2_buildings.json`)

| Finding | Status | Evidence |
|---|---|---|
| (a) Grand Hyatt: no connection to its AirTrain station | partly (corrected round 7: the round-6 stub ended at the guideway edge, mid-storey; see R7.1) | R6.1: gh_bridge LOD0/1/2 from the [pub] level + [obs] finger, hotel face to the guideway edge; 0 crossings / envelope; owner question narrowed |
| (b) R5f2.2 record + KEEP_INSIDE comment wrong (plinth top cap) | fixed | R6.2: records corrected; plinth top on the local soffit: max depth 0.232 -> 0.053 m; ceiling 2.0 -> 1.0 m2 |
| (c) LOD1 creases | partly | integration_closeout R6.2: LOD1 fold report + ceiling (17 / 8 folds over 4 / 6 deg); creases deferred |
| (d) dump currency misses the generator | fixed | integration_closeout R6.1: generator hash + schema + per-bridge parts -> CONFLICT |
| (e) CG LOD2 depth not reported; LOD1 gates | partly | R6.3: deck box + envelope at LOD0/1/2; LOD2 311.18 m2 / 0.686 m with ceiling 327; the clip deferred |


## Round 7 (follow-up on the round-6 verifier, `SP/c6_r6verify_buildings.json`) - 9 Nov 2026

Work log: `SP/c7/buildings/NOTES.md`. Rebuilt: landside only (one heavy-lock job, 17:29-17:41Z, build exit 0, split exit 0), then
b3d_integrate, b3d_lod2_check, tools/sat/check.py, verify_itb and verify_domestic. verify_landside is unchanged (md5 5a791814),
so its before numbers are the round-6 run on the installed r6 files (landside `aca13820`, lod2 `642b0760`). No replays, no renders.

### R7.1 Grand Hyatt: the bridge runs under the deck at the hotel's 4th floor, to the station footprint (r6 verifier (a), (b))

**What the sources say**
- [pub] hyatt_pr_2019: "Guests step out of the hotel's new AirTrain station, which features a dramatic kaleidoscopic stained-glass art
  installation, and after crossing an enclosed bridge, they enter the hotel's ... lobby".
- [pub] gh_lobby_level: guests arriving by road take elevators "up to the fourth floor lobby"; Webcor: "a fourth-floor light rail station".
- [obs, reference photo only] Commons "Grand Hyatt at SFO station from the northwest, December 2019" (already listed in the spec's
  photos; fetched this round to `SP/c7/buildings/dl/`, not used as a texture). It shows the station's glazed level with the stained
  glass directly UNDER the guideway deck, and the train on the deck above it.

**What changes in the model**
- The bridge level is the hotel's 4th-floor line, not the platform. The 19.75-m platform level is the [inf] network level, not a
  [pub] fact.
- 4th-floor line = the colonnade top hc = 14.0 m. It comes from the photo-l4 bands read as storeys: 2 podium + 1 recessed colonnade
  level + 9 tower pitches = 12 [pub gh_stories]. The pitch stays 3.33 m [inf].
- The bridge runs under the deck along the whole outline finger (28.5 m2) to the station footprint. Before, it was a 15.7-m2 stub
  that stopped 0.15 m short of the guideway parapet.
- Section: floor 14.0 m, roof `min(floor + 4.0, deck soffit - GH_BR_GAP)` = 18.0 m. The deck soffit over the bridge is 18.151 m (the
  AirTrain level field minus DECK_T). The LOD2 roof is `soffit - 0.40` = 17.75 m.
- Hotel storey heights: unchanged. No source moves them, and they now agree with the [pub] 4th-floor connection. The record gains
  `storeys` and `fourth_floor` dims. `conflicts` replaces the old platform-level clash with the resolved level note and adds
  "NAIP roof-shift 36-40 m vs the 44-m parapet". `unknown` now holds the bridge section, the station's lower concourse (extent,
  stairs / lifts to the island platform) and the absolute storey heights (an SFO drawing or the FAA OE/AAA filing would settle them).
  The concourse is in `not_modelled`.

**Measured** with `SP/c7/buildings/t/ghbr7.py` (`a3047316`), the same script on both arms:

| | before (r6 `aca13820` / `642b0760`) | after (`845ea564` / `f47a0e3f`) |
|---|---|---|
| L0 / L1 bridge, local y | 19.351..23.751 (mid-storey on the hotel) | 13.600..18.000 (floor on the 4th-floor line) |
| plan | 15.71 m2, ends at the guideway edge | 28.31 m2, to the station footprint |
| AirTrain triangles over the plan / penetrating | 0 / 0 | 565 / 0 (deck soffit 0.151 m above the roof) |
| LOD2 | inside L2_grand_hyatt, 0.40 m off the deck in plan | 10 triangles, y 13.60..17.75, 0 penetrating, 0.400 m under the coarse deck |
| roadways / other landside parts over the plan | 0 | 0 |

- verify_landside: 209 checks, 0 failed. Envelope LOD0 / 1 / 2: 0 / 0 / 0. AirTrain crossings L0 / L2: 0 / 0. Hyatt masts: 0.
- The keep-out cut no bridge face: 22 triangles at LOD0, as built.

### R7.2 Central Garage LOD2 plinth top on the local soffit (r6 verifier (e))

The round-6 LOD0 fix now also applies at LOD2. The `cg_L2` under-guideway stack's walls and top follow
`min(zt, AirTrain level - DECK_T) - CG_L2_SOFFIT` (0.25 m), with vertices every 2 m. The coarse deck tiles are unchanged.

**Before -> after**
- verify_landside LOD2 deck box: 311.18 m2 -> 9.78 m2. Deeper than 0.30 m: 76.11 -> 1.74 m2. Max 0.686 m at (-796.6, 261.4), on
  vertical faces, unchanged.
- The verifier's site split (cgdepth2 `b2eb1ca6` via `SP/c7/buildings/t/cgl2_sites_g.py` `ae31bd86`, a crash guard for empty sites):
  - deep samples: 77,356 -> 2,393;
  - non-vertical: 72,679 -> 0;
  - at (-955, 408): 53,460 -> 0; at (-1025, 155): 19,219 -> 0;
  - deeper than 0.30 m: 18,400 -> 506.
- `KEEP_INSIDE_L2_MAX_M2` 327.0 -> 10.3 (measured + 5 %).

**Wording corrected in place:** R6.3 "not cheap" and R6.1 "Not guessed". The Round 6 table row (a) now reads 'partly'.

### Round 7 dispositions (`c6_r6verify_buildings.json`)

| finding | status | evidence |
|---|---|---|
| (a)+(b) GH bridge stub, 9 m above the 4th floor | fixed (section and concourse: owner) | R7.1 |
| (e) CG LOD2 deck-box residual | fixed | R7.2: 311.18 -> 9.78 m2, non-vertical deep samples 72,679 -> 0 |
| (c) LOD1 fold gate not enforced | fixed | integration_closeout R7.1 |
| (d) zero-bridge dump passes | fixed | integration_closeout R7.2 |
| wording / records | fixed | R6.1, R6.3 and the Round 6 table corrected in place; integration R6.2 likewise |
| request C5.1 (realtime) | answered + height bands | integration_closeout R7.3 |
