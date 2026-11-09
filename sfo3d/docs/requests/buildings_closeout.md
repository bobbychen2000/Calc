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
