# Requests from the integration track (3-D building assets in the app)

From: owner of `js/three/buildings3d.js`, `tools/blender/{b3d_integrate,b3d_lod2_check,b3d_split,build_roadways,roadways_net,roadways_itb_plate}.py`,
`tools/blender/{b3d_views_job,b3d_glass_job}.mjs`, `data/buildings3d/{roadways,roadways_lod2}.glb`, `data/buildings3d/integration.{json,js}`,
`manifest.json#integration` / `#roadways`, `tools/build3/phone_artifact_page.py`. What changed on this side is in
`docs/research/buildings3d.md` (integration section, "Close-out round 3" and "Close-out round 4").

## Round 3 (close-out round 3, 7 Nov 2026; findings `docs/requests/closeout3_findings.json#groups.integration`)

Rebuilt in this round on the buildings track's 6-7 Nov assets (domestic 7 Nov 03:36Z, ITB 01:55Z, landside 02:11Z):
`roadways.glb` / `roadways_lod2.glb` (r18), `integration.json` / `integration.js`, the landside unit split, `manifest.json#integration` /
`#roadways`. Checks after it: `b3d_integrate` 2 conflicts / 11 notes (below), `b3d_lod2_check` 47 units 0 flagged,
`tools/sat/check.py` ISSUES 0 / APP ISSUES 0 / WARNINGS 17 (unchanged), `verify_landside` 195 / 0.

### R3.1 Bridges (bridges-6, R2b.3): the 3-D footprints are in `integration.js`

`B3D_INTEGRATION.footprints.units[group][unit]` (groups tower, ITB, domestic; 14 units; +138 kB of the bundled file) holds per
building the LOD0 / LOD1 max-extent `y` range and its `tiers`: `body` (what stands on the ground: grade to top) and `over`
(eaves, canopies, vestibules: from the lowest underside over that region to the top), each with `rings` ([x, z], simplified
0.1 m) and `y` (world y, `ground_y` 3.0). A rotunda drum under a roof overhang is clear when its top is below that `over`
tier's lower `y` (buildings R3.3: F7 / F8 L1 drum tops 8.55 m under the BA-F soffit 9.69 m). `gates.js` can now test drums and
tunnels against these instead of the SFO Museum proxy and the own-strip rule. The landside units stay in
`integration.json#footprints` only (bridges never reach them).

### R3.2 ITB group: the departures level against photo i1

Photo i1 (Kulikovsky 2007, CC BY 3.0, `refs/cache/buildings/review_likeness/i1.jpg`) settles that the light-concrete band in
front of the departures deck is a lower level, not the deck (integration-2). It also measures the step from the departures
deck's edge coping to the lower level's outer coping at ~6.7 m (6.1-7.3; horizontal scale 9.0 px/m from the deck-edge
planter, NAIP length 104 m = 935 px; insensitive to the camera height between 5 and 20 m). With the lower level at the lowest
plausible 5.8 m (4.6 m over the at-grade building-passage roads under it + 1.2 m deck [inf]) that puts the L3 deck ~1 m
above `spec_itb level3.floor` 11.5 m [inf, +-1.5]. Please review `level3.floor` against i1 (the deck and the lower level are
modelled at 11.35 / 5.80 m; the roadways follow the ITB asset's curb level, so a change there carries over on the next
`build_roadways.py` run).

### R3.3 Landside group: one AirTrain pier column 0.48 m beside a ramp edge (note, no action)

At (-1711.4, 555.5) a straddle-bent column stands 0.48 m outside a ramp deck's edge (no overlap; `verify_landside`: no column
foot on a carriageway or deck). `b3d_integrate` used to flag any column within 0.6 m of a deck as "in a road deck"; it now
lists overlaps as conflicts and near ones as notes. Nothing to rebuild. The roadways rebuild of this round did not move any
deck in plan near the guideway (R3.5 order respected: roadways -> `verify_landside` 195 / 0 -> integrate).

### R3.4 Environment / engine (vendor/**): WASM decoders for meshopt / KTX2

Not shipped: whether the artifact page may compile WebAssembly is still unverified (no primary source on the artifact CSP found;
the aircraft and building files ship as `.wasm` only as a file type, they are fetched as bytes, never compiled). The phone test
card now probes it: `tools/build3/phone_artifact_page.py` adds a "WebAssembly" row (`WebAssembly.compile` of the 8-byte empty
module: "compiles" or "blocked: <CSP message>") and a "JS heap" row, both included in "Copy results". If the owner's phone
reports "compiles", the meshopt decoder (and the Basis transcoder for KTX2) can be vendored under `vendor/**` (env track) and
`tools/engine/glb_compress.mjs` applied; measured on the 24 landside unit files in round 2: meshopt 18.87 -> 6.47 MB.

### R3.5 Environment / engine (buildings R3.10): BA-B glass vs Cycles

Forwarded, not changed here: the app's BA-B glass / fascia ratio is 0.15-0.17 against 0.33 in Cycles at the same camera and
sun (buildings R3.10), with the app sky near the horizon darker than Cycles' (126, 146, 161 vs 166, 182, 194). That is the IBL /
sky radiance (engine / env); the loader passes the asset's glass material through unchanged (kind `hall`, no override).

### R3.6a Static track (landside roads): the at-grade roads under the ITB frontage are not drawn

The OSM ways that pass under the ITB departures deck and its lower level at grade - 256787738 "Airport Access Road" (primary),
370279603 / 370279607 (secondary), 370279550 (service), 256787743, 1079463010, 370279532 - are tagged
`tunnel=building_passage`, and `tools/build_landside.py` drops every way with `tunnel != no`, so `data/sfo_landside.json` has
none of them. Under the decks the app shows bare ground (`out/buildings3d/integ/c3/low/cmp_new_i1like.png`: tan ground between
the ramps in front of the ITB). Please consider keeping `building_passage` ways as at-grade roads (they are open roads under a
structure, not tunnels); the roadways' clearance over them is 4.6 m by construction of the lower level (LOWER_H).

### R3.6 Owner

- Domestic arrivals level clearance (buildings R3.2): the anchored domestic departures loop (deck 4.73 m at the curb
  placeholder [unk], soffit 3.53 m with the generic 1.2-m deck) is now listed as a conflict over 26 at-grade roads (3.53 m;
  the T3 L1 -> L2 16 ft [pub] makes the real stacked level < 4.6 m by design). A posted-clearance photo or sign of the
  domestic arrivals roadway would settle it.
- The phone: open the phone test artifact on the owner's phone and send "Copy results" - it now includes WebAssembly
  (the CSP question above) and the JS heap.

### Responses to the buildings track's Round 3 requests

| Request | Done |
|---|---|
| R3.1 rebuild roadways, re-run integrate / LOD2 check | done (r18): deck inside a building 0 m2 (the T2 cut is gone: `deck_cut_inside_buildings_m2` T1 390.6 / T3E 312.6 / T3W 309.4, no T2), curb void 0.134 m; T2 sections z 200 / 240: the deck ends on the new sidewalk edge (x -757.3 at z 200) with no gap; replacement table re-run |
| R3.2 low decks over at-grade roads as conflicts | done: new check `at_grade_clearance` (every 1 m along each app at-grade road, centre and 0.3 m inside the edges, the lowest roadways underside above it); 1 conflict per deck unit: domestic_departures 26 roads 3.53 m (owner question above), interchange_2_2 1 road 4.597 m over 2 m (numerical: the deck is linear between the solve's nodes) |
| R3.3 height bands in the footprint tiers | done: `integration.js` footprints with `body` / `over` tiers (R3.1 above) |
| R3.4 BART station vs taxilane 302 | done: recorded as an existing condition (note): the observed NAIP north wall (`landside_r1_measure.BART_NORTH`) is 35.8 m from the lane, the asset 36.7 m; the lane's ADG 5 stays inferred |
| R3.5 order of rebuilds | followed (roadways -> verify_landside -> integrate) |
| R3.6 ITB canopy over the plate | confirmed: ITB over road deck min 4.67 m, 0 m2 below 4.6 (no note any more) |
| R3.9 landside rebuilt again | split re-run: 24 unit files 19.8 MB + 29 images 3.0 MB |
| R3.10 BA-B glass | forwarded (R3.5 above) |

## Round 3, fix round 2 (7 Nov 2026; the independent verifier's findings v1-v8 on round 3)

Rebuilt on the buildings track's fix-2 assets (domestic 13:11Z, landside 13:15Z / units 13:48Z, ITB 13:16Z, tower 13:22Z):
`roadways.glb` / `roadways_lod2.glb` (r22, 4.58 / 0.47 MB), `integration.json` / `integration.js` (229 kB), the landside unit split,
`manifest.json#integration` / `#roadways`. Order as R3.5: roadways -> `verify_landside` 198 / 0 -> `b3d_integrate` 3 conflicts / 11
notes -> `b3d_lod2_check` 47 units 0 flagged -> `tools/sat/check.py` ISSUES 0 / APP ISSUES 0 / WARNINGS 17. Dispositions:
`docs/research/buildings3d.md` (integration, "Close-out round 3, fix round 2").

### R3f2.1 Buildings track: R3.11 and R3.12 done

- **R3.11** (re-run after the fix-2 rebuilds): done in that order; no footprint change seen (deck inside a building: none; ITB curb
  void 0.134 m; ITB canopy over the plate 4.67 m; domestic over the deck 4.70 m).
- **R3.12** (the T2 curb slot): the deck stops 0.02 m (was 0.10 m) short of the domestic group's occupancy (`ASSET_BUF_DOM`), and a
  deck edge against any asset now gets its fascia (the edge face, no parapet), so the seam is no longer open to grade. Seam along the
  T2 sidewalk edge (plan, every 0.25 m, 544 points): median 0.145 -> 0.065 m: 516 points at 0.02-0.10 m, 14 at 0.10-0.20 m (r19: all 0.10-0.20 m; the 14 points beyond
  0.3 m are the sidewalk's end edges; what is left is the deck outline's 0.05-m simplification); ~122 m of edge face along it. `build_roadways` reports it (`roadways_build.json#stats.curb_gap_t2`).

### R3f2.2 ITB group / owner: the L3 level now shows as a stacked-road conflict (R3.2 restated)

The round-3 cut that removed 1-m cells from lower decks is gone (verifier v1). Stacked pairs are now held by the level solve
(the lower way lowered under the upper deck) and, where it cannot, the lower deck is cut along the upper deck's edge - or the cut is
refused and reported when it would split the lower road. One pair cannot be held: the ITB loop's lower (arrivals) roadway 41015123,
held at 5.80 m [inf: 4.6 m over the at-grade building-passage roads + 1.2 m deck], passes under its departures legs 38853121 /
38853045, which leave the L3 plate at 11.35 m (`spec_itb level3.floor` 11.5 [inf, +-1.5] - kerb). 5.55 m deck to deck < 5.8 m:
`b3d_integrate` lists 88.6 m2 at 3.88-4.6 m (161 m2 by the verifier's own overhead script) (round 3 had cut the lower road away under the leg - a road that stopped under the ramp).
Photo i1 reads the step ~6.7 m, i.e. L3 ~1 m higher than modelled. Please review `level3.floor` against i1; the roadways follow the
ITB curb level on the next `build_roadways.py` run, and the conflict lifts by itself if L3 rises by >= 0.8 m.

### R3f2.3 Bridges (R3.1): the footprint tiers are complete

`B3D_INTEGRATION.footprints` tiers are now grown by the ring tolerance before simplification and keep pieces down to 0.02 m2
(verifier v3: vestibules 0.5-1.3 m, the T1 / BA_C junction wall 3.9 m and the ITB outrigger tips 1.6 m lay outside every tier).
`b3d_integrate` self-checks every LOD0 / LOD1 vertex against its unit's admissible tiers: 155,560 vertices, 0 outside. Same format.

### R3f2.4 Static track: R3.6a re-sent

The building-passage roads under the ITB frontage are still not in `data/sfo_landside.json` (unchanged since round 3).

### R3f2.5 Owner

- The ITB L3 level (R3f2.2) and the domestic arrivals clearance (R3.6, unchanged: 26 at-grade roads at 3.53 m).
- The phone test card (rebuild the artifact with `tools/build3/phone_artifact.sh`) now reports "Geometry / textures" (the scene's
  geometry ArrayBuffers and three.js' texture estimate, on every browser) next to "JS heap (V8 only)" and "WebAssembly"; "Copy
  results" writes the whole card once.

## Round 4 (residuals) (close-out round 4, 8 Nov 2026; the round-3 fix-2 verifier's findings `SP/c3_verify2_integration.json`)

Rebuilt on the buildings track's round-4 assets (ITB 17:18Z, domestic 17:21Z, tower 17:31Z, landside 17:35Z): `roadways.glb` /
`roadways_lod2.glb` (4,685,984 / 450,412 B; r22 4,580,524 / 466,124 B), `integration.json` / `integration.js` (990,751 / 236,218 B), the landside unit split, `manifest.json#integration` /
`#roadways`. Order as R3.5: roadways -> `verify_landside` 199 checks / 0 failed -> `b3d_integrate` 7 conflicts / 14 notes (r22 3 / 11; the 4 + 3 new entries are the narrowed and refused stacked cuts, R4.3, now reported) -> `b3d_lod2_check` 47 units / 0 flagged ->
`tools/sat/check.py` ISSUES 0 / APP ISSUES 0 / WARNINGS 41 (r22 17; all 41 are bridge rest / extension / walkway warnings of the stands data, whose bridge tests use the SFO Museum outlines, not `integration.json` - `tools/stands/check_stands.py` l. 93-99; none comes from the roadways). Work log, scripts and plots: `SP/c4/integration/` (NOTES.md; `rv/stubs.py` = the verifier's
stubs4 rule vectorised, `rv/guard.py`, `rv/rr_clear.py`, `plot_mesh.py`; `dev_build.py` / `dev_check.py` run the build and the
integration check into a scratch root without touching the repo).

### R4.1 The parapet "fingers" (major, regression of fix 2): fixed at the root

Root cause (`an_joints.py` on the r22 pieces): every road ribbon ends in a flat cap square to its own centreline, so where two
OSM ways continue each other at a shared node with a bend, the two caps leave a wedge open to grade on the outside of the bend
(100 of 105 such joints, up to 4.9 m2). Fix 2 sampled deck edges every 0.5 m and called a sample inner only within 0.08 m of a
same-level neighbour, so the wedge's sides - the caps, i.e. ACROSS the lanes - became outer edges with parapets. Behind it two
more defects of the edge rule: (a) "same level" was decided per pair of pieces by the median step over their whole contact
(< 1 m), so ~885 m of edge with a local step of 0.3-15 m was left open (no fascia, no parapet) and ~22 m of barrier stood
between decks within 0.3 m of each other; (b) pieces that meet at a shared node disagree in level along their common edge
(each piece's level is its own centreline profile projected sideways) - the verifier's unguarded 0.44-0.63 m step in
interchange_2_2 is one of these. Changes (`tools/blender/build_roadways.py`):

- **Joint wedges** (`joint_wedges`): the convex hull of the two caps less both decks, less any other piece in the stacking band,
  the stacked cuts and the assets' occupancy, joins the higher-priority piece at the node's level: 105 joints, 86 wedges filled, 40.4 m2 (largest 4.59 m2 at (-915.8, 450.3), 1059482643 / 512320224, bend 11.4 deg). Where a wider way
  continues into a narrower one, the wider cap stood across the narrower deck's outer lane: a taper alongside the narrower deck
  (8:1, max 15 m [inf: of the order of the MUTCD low-speed lane-reduction taper, recalled, not re-checked]) on plain two-way
  continuations only: 18 tapers, 284.8 m2 (largest 27.9 m2 over 15 m at (-1578.8, 536.1)).
- **Slits and gores** (`slit_fill`): the points between two decks (nearest points on opposite sides) whose gap across is < 1.0 m
  are deck, where the raw levels differ by < 1.0 m (connected decks, which the blend below equalises) or < 0.3 m (decks that share
  no node, the ITB plate): 103 pairs, 130.7 m2 (largest 15.3 m2, the gore at (-1649.9, 468.6)); small voids enclosed by decks at one level (a junction's leftover triangle at the T2 curb):
  12 voids, 2.1 m2. Gore noses now start where the two decks are 1 m apart (room for the two 0.4-m barriers).
- **Edge rule** (`edge_runs`): per 0.5-m sample, inner only if a neighbour within 0.08 m (LOD1 0.40, LOD2 1.05: the LOD's
  simplification) has its deck top within STEP_TOL 0.30 m there; a larger step is an edge of both (fascia + parapet, a median
  barrier); an inner joint with a 0.02-0.30 m step gets the higher deck's step face (498.5 m); an outer chain < 2 m with a deck
  within 1 m of its level 0.6 m beyond its middle and both ends is a slit side: edge face, no parapet (5.8 m); a deck's
  own other parts count as a neighbour; parapet chains get end caps.
- **Connected decks meet halfway** (`blend_neighbours` / `hb`): pieces that share an OSM node and touch move towards each other
  over 8 m (in full below a 0.6-m step, none above 1.0 m), so their tops agree on the common edge (the verifier's "equalise the
  two profiles where the ribbons touch"): 140 pairs; columns use the same levels.
- **Merges** (`merge_into`): a fill joins its owner with a 2-cm round close, validated (dev build d9: GEOS' mitre negative
  buffer returned an empty polygon and two whole decks, 41015044 and 905752945, vanished - caught before the final build by the
  piece-area comparison; `merge_into` now raises if a piece would lose area, and `stats.pieces_without_deck` lists any piece with
  a ribbon but no deck: one, ramp 370279562, which lies wholly inside the landside asset's occupancy (cut by `landside` 31.3 m2; area 0 in r22 too)).
- **Self-check** `roadways_build.json#stats.in_carriageway_parapet` (the verifier's stubs4 rule on the LOD0 mesh: parapet-top
  samples with the same deck level +-0.3 m 0.6 m away in >= 7 of 8 directions), plus `stats.joint_wedges` and `stats.edges_lod0`.

| Measure (LOD0 mesh) | r22 | Round 4 |
|---|---|---|
| in-carriageway parapet (stubs4 rule; build self-check / independent `rv/stubs.py`) | 236.7 m (2,367 samples), largest cluster 7.0 m | 52.3 m (523 samples) / 52.1 m (521), 34 clusters, largest 1.4 m |
| the verifier's 7 new finger sites (samples within 4 m) | 27 / 25 / 17 / 16 / 13 / 11 / 10 | 0 / 0 / 0 / 0 / 0 / 0 / 0 |
| the verifier's grown sites | (-780.4, 329.9) 27, (-861.0, 138.1) 17, (-831.4, 396.5) 13, (-790.7, 330.8) 18, (-794.3, 327.3) 16, (-773.3, 299.5) 18, (-1072.3, 184.6) 28, (-1417.9, 323.2) 22, (-1696.3, 575.1) 21, (-1334, 498.5) 47 | 0 / 6 / 11 / 4 / 3 / 6 / 5 / 12 / 8 / 0 (gore-nose tips, below) |
| interchange_2_2 step between the two decks (`rv/ic22_step.py`, x -1645..-1619, z 422-432): x-stations (0.1 m) with a deck-to-deck jump of 0.3-0.8 m between cells 0.1 m apart | 202 (20.2 m; 0.32-0.69 m) | 0 (largest deck-to-deck jump 0.23 m) |
| open deck edges, the verifier's `guard.py` (same asset pickle): open / drop 0.5-1.5 m / drop > 4 m | 1,257 / 315.6 / 137.4 m | 929 / 100.0 / 109.8 m (the > 4 m rest: the ITB plate's h 12.30 edges, as in r22) |
| glTF validator errors roadways.glb / roadways_lod2.glb | 0 / 29 (non-unit normals) | 0 / 0 |
| deck area (117 pieces) / columns / max grade, ways > 8 % / LOD0 triangles | 92,349.7 m2 / 300 / 13.4 %, 20 / 48,780 | 92,808.2 m2 (+458.5 = the fills; no piece smaller than in r22) / 300 / 13.4 %, 20 / 50,912 |

What is left of the in-carriageway count is gore noses - the last 0.5-1.4 m of the two barriers where they converge to the V tip and the
filled slit (< 1 m) continues the deck between them (`SP/c4/integration/plots/m8_831.png`: (-831.4, 396.5), 1.1 m;
the verifier measured 0.1 m there in r18) - and junction corners where an outer parapet meets a neighbour's edge; the largest cluster is 1.4 m at (-1540.2, 467.4) (deck 3.89 m). The 29 non-unit normals were zero
normals on soffit vertices no triangle uses (`vnormals` now gives them (0, 1, 0)).

### R4.2 The refused stacked pair's record (minor): fixed; the L3 level stays with the owner / ITB group

- Area: `b3d_integrate.deck_points` sampled only the upright cells of each triangle's k x k subdivision (k(k+1)/2 of k^2), so
  areas summed from it covered ~half of every large triangle; both cell kinds now: roads over roads below 4.6 m 160.3 m2
  (r22 88.6 m2; the verifier's mesh measure 161 m2; `rv/rr_clear.py` on the mesh 159.9 m2 in r22, 159.7 m2 now).
- Minimum: 3.88 m at (-1307.8, 483.4), deck 6.27 m - unchanged (r22 3.88 m at (-1306.7, 482.4)); `rv/rr_clear.py` on the
  meshes: 3.88 m in both, 159.9 -> 159.7 m2 below 4.6 m. The lower roadway's profile is unchanged (hp 6.27-6.32 m over the conflict).
- `roadways_net` stacked report: `held` is now `true` only when the separation is met everywhere, `'partial'` when the solve took
  the pair but `left_m` > 0 (`in_solve` true): 6 held in full, 2 partly (41015123 under 38853045 / 38853121, 0.74 m left).
- Three-level stack (R3f2.2 corrected): at the conflict point the lower roadway 41015123 is not at LOWER_H 5.80 m but at
  6.27-6.33 m, floored by the at-grade roads beside it (data/sfo_landside.json: 256787736, tertiary 10.8 m, 3.2 m away; 93671776,
  service, 3.8 m away) - at-grade roads, the lower roadway, then the departures legs at the L3 plate's 11.35 m. The request text in
  `b3d_integrate` now says so with the record's deck level. L3 + 0.8 m still lifts the conflict (needs 12.07 m over 6.27 m).

### R4.3 Narrowed stacked cuts (minor): reported

`b3d_integrate` (`stacked_cut_checks`) lists every stacked cut made although it narrows the lower carriageway below lanes x 3.0 m
as a CONFLICT with its way ids (4: 38853121 / 1185654144 under 38854581, 370279626 under 35157100 and under 41015036), and the
refused ones as notes (3). The geometry is unchanged: three of the four are diverges / merges at a shared OSM node (the branch
leaves the main deck's level while their ribbons still overlap); resolving them in the level solve (the branch held at the main
deck's level over the overlap) is a change to `roadways_net`'s solve with effects on grades and clearances everywhere - deferred,
recorded as such.

### R4.4 interchange_2_2 unguarded step (minor, pre-existing): fixed (R4.1, the blend)

The two decks now meet: no deck-to-deck jump of 0.3-0.8 m is left in the window (r22: 20.2 m of stations, 0.32-0.69 m); the largest remaining jump is 0.23 m, under STEP_TOL 0.30 (an inner joint by the round-4 rule, which gives such joints the higher deck's step face).

### R4.5 v7 residuals (minor): unchanged, with their owners

Domestic departures loop 3.53 m over 26 at-grade roads (758 m; r22 753 m; owner: a posted-clearance photo or sign of the domestic
arrivals level); interchange_2_2 4.60 m at (-1590.7, 416.8), 2.0 m long (r22 1.0 m: the both-cell sampling finds more points) over the at-grade way 397162138 (numerical: the deck is linear between the solve's nodes;
the blend does not touch this point - hb = hp = 5.798 m); the building-passage roads under the ITB frontage (static track,
R3.6a).

### R4.6 Low tier / LOD2 file (minor): done in a browser

One low-tier near-mode page (`tier=low`, headless Chromium on llvmpipe 960 x 540, `SP/c4/integration/jobs/low.sh`, under `out/.heavy2.lock` 18:25-19:10Z, served from a frozen copy of the final tree whose md5s match the installed `roadways.glb` / `roadways_lod2.glb` / `integration.js` / `buildings3d.js`): `roadways_lod2.glb` loaded and shown at start (6,971 tris in 21 meshes, 5 materials, 22 s + 6 s compile), ready in 721 s with `failed` empty and every group loaded; near the T2 curb the full `roadways.glb` replaced it (72,978 tris, 92 meshes). View `t2curb` rendered (`out/buildings3d/integ/c4/low/cmp_near_t2curb.png`; 1,135 draw calls, 2.58 M tris, JS heap 133 MB used). The second view (the interchange joint at (-1623.7, 505.1)) did not finish inside the run's 45-min budget: the landside unit files near it were still streaming on llvmpipe (exit 124). Offline on the same files: gltf-validator 0 errors on both (r22 LOD2: 29); three.js GLTFLoader in node: 21 meshes, 6,971 tris, all positions finite.

### R4.7 Records (minor): corrected

`manifest.json#integration.footprints_js.self_check` now records the largest distance (`max_m` 0.124 m, per unit in
`max_by_unit`) next to the count beyond the 0.3-m tolerance (`max_beyond_tol_m` 0.00); `docs/research/buildings3d.md` fix-2 rows:
"167 lowered nodes" -> 163, "max 0.00 m" -> max beyond the tolerance, 0.124 m largest.

### R4.8 Owner / ITB group (unchanged requests)

- The ITB L3 level (R3.2 / R3f2.2): the conflict is 3.88 m on the mesh over 160.3 m2 (the area now counted in full); +0.8 m on
  `level3.floor` lifts it.
- The domestic arrivals clearance (R3.6) and the phone test card (R3f2.5).
