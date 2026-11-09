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
held at 5.80 m [inf: 4.6 m over the at-grade building-passage roads + 1.2 m deck] [corrected in close-out r4: at the conflict it is at 6.27 m, not 5.80 m - floored by the at-grade roads 256787736 / 93671776 beside it, a three-level stack, R4.2], passes under its departures legs 38853121 /
38853045, which leave the L3 plate at 11.35 m (`spec_itb level3.floor` 11.5 [inf, +-1.5] - kerb). 5.55 m deck to deck < 5.8 m [corrected in close-out r4: 11.35 - 6.27 = 5.08 m over the conflict]:
`b3d_integrate` lists 88.6 m2 at 3.88-4.6 m (161 m2 by the verifier's own overhead script) [corrected in close-out r4: 160.3 m2 below 4.6 m - `b3d_integrate` sampled only half of each triangle's cells, R4.2] (round 3 had cut the lower road away under the leg - a road that stopped under the ramp).
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
  two profiles where the ribbons touch"): 140 pairs; columns use the same levels. [superseded in fix round 2, R4f2.1: side-by-side
  pairs only (50), end-to-end continuations not blended (90), phi fall-off to 1.2 m, the neighbour extrapolated beyond its ends (hp_ext)]
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
| deck area (117 pieces) / columns / max grade, ways > 8 % / LOD0 triangles | 92,349.7 m2 / 300 / 13.4 %, 20 / 48,780 | 92,808.2 m2 (+458.5 = the fills; no piece smaller than in r22) / 300 / 13.4 %, 20 [corrected in fix round 2: the way profiles' maximum (`stats.grade_max`), not the mesh - the round-4 mesh had 14.8 %, 971 m2 above 10 %, ITB 115 m2; R4f2.1] / 50,912 |

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

## Round 4, fix round 2 (8 Nov 2026; the round-4 verifier's findings, `SP/c4/integration_ver1`)

Rebuilt `roadways.glb` / `roadways_lod2.glb` (5,266,908 / 476,072 B; sha1 950d31fa / e3728c1d; round 4 4,685,984 / 450,412 B),
`integration.json` / `integration.js`, `manifest.json#roadways` / `#integration` (20:28-20:42Z, `SP/c4/integration/jobs/final.sh final3`;
building assets unchanged since round 4). Chain: build -> `verify_landside` 199 checks / 0 failed -> `b3d_integrate` 7 conflicts /
14 notes (= round 4; tier self-check 156,818 vertices, 0 outside, largest 0.124 m) -> `b3d_lod2_check` 47 units / 0 flagged ->
`tools/sat/check.py` ISSUES 0 / APP 0 / WARNINGS 41 (= round 4, the stands data). gltf-validator 0 / 0 errors on both files;
three.js GLTFLoader on the LOD2 file: 21 meshes, 7,338 triangles, all finite. Every number below is on the installed files
(byte-identical to dev build e3), measured with the verifier's own scripts (`SP/c4/integration_ver1/rv/`: grades, pfloat,
incarr, slits, rrclear, guard, dh) plus `SP/c4/integration/rv/stubs.py`, `ic22_step.py` and `f2/steps.py`. Work log, dev builds
e0-e3 and the offline blend lab: `SP/c4/integration/NOTES.md`, `f2/`.

### R4f2.1 Grade waves from the blend (major, regression of R4.1): fixed at the root

Confirmed as diagnosed: 90 of the 140 pairs that R4.1 blended were two ways continuing each other end to end; beyond the
neighbour's end `hp()` clamps to the node level, so every deck within 8 m of every joint was pulled towards the node level.
Two more defects of the same blend turned up while fixing it (dev builds e0 / e1, `f2/an_site.py`): (a) its fade on the step,
(1.0 - r) / 0.4 x r, has a slope down to -2.5, so a deck beside one at another grade rose or dipped by up to 1.25 x the grade
difference where the step grew through 0.6-1.0 m (the 10.0 % ITB triangle at (-1393.0, 482.7): 681667031 beside 38854581);
(b) a neighbour clamped beyond its own end pulled a deck towards a ramp's start level (14.4 % at (-1546.5, 471.5) in e0).
`build_roadways.py` now:

- blends only connected ways that touch SIDE BY SIDE: `continuation()` (centreline ends within JOINT_TOL, outward directions
  opposed) excludes end-to-end pairs, unless they also touch farther than their half width + 3 m from the joint (none): 50 pairs,
  90 continuations not blended;
- evaluates the neighbour extrapolated with its end slope beyond its ends (`hp_ext`, up to 8 m), not clamped;
- takes the step out in full up to 0.6 m and then falls off at the rate the step grows (phi(r) = 1.2 - r, none from 1.2 m), so the
  correction can never add more grade than half the two decks' grade difference;
- does not blend decks without a shared node (tried in e1 for R4f2.3: the mesh maximum rose to 13.7 % and no step left the
  0.05-0.30 m class; offline lab `f2/blendlab.py` on the same pieces: no blend 13.37 % / 784.3 m2 > 10 %, round-4 fade 821 m2 and
  ITB 26 m2, the chosen rule 13.37 % / 784.3 m2 / ITB 0);
- reports the as-built grades: `roadways_build.json#stats.mesh_grades` (LOD0 deck-top triangles, deck_* materials, area-weighted,
  max / area above 6-13.5 % / per unit / folds; identical to the verifier's `grades.py` on the e0 and e3 files) and
  `manifest.json#roadways.closeout_r4.fix_round_2`. `stats.grade_max` stays the way profiles' maximum.

| Measure (LOD0 mesh) | r22 | Round 4 | Fix round 2 |
|---|---|---|---|
| max grade | 13.4 % | 14.8 % | 13.4 % (13.37, (-1549.5, 468.8), the r22 site: 41015033's profile) |
| area > 10 / > 12 / > 13.5 % | 772 / 36 / 0 m2 | 971 / 171 / 19 m2 | 784 / 36.5 / 0 m2 (the 12 m2 over r22 are round-4 fills; the same pieces without any blend: 784.3) |
| ITB / interchange_1_2 area > 10 % | 0 / 0 m2 | 115 / 71 m2 | 0 / 0 m2 (ITB max 9.7 %, as r22) |
| folds > 1 / > 2 / > 4 deg | 107 / 56 / 5 | 299 / 102 / 8 | 226 / 84 / 10 (the same pieces without a blend: 150 / 76 / 9 - the flat joint wedges; the side-by-side blend adds ~75 folds of 1-2 deg) |
| deck tops moved vs r22, area with abs(dh) > 0.1 m (`dh.py`) | - | 3,895 m2 (max +-0.30) | 3,983 m2 (max +-0.29; now only along the 50 side-by-side pairs - the R4.4 interchange_2_2 step and junctions) |
| interchange_2_2 deck-to-deck jumps 0.3-0.8 m (`ic22_step.py`) | 20.2 m | 0 | 0 (largest 0.25 m) |

### R4f2.2 Barrier feet off the deck (minor): fixed

Each deck ring is now segmentized at the deck triangulation's own spacing (6 / 16 / 30 m per LOD: `tri_polys` segmentizes the
same polygon, so they share the boundary vertices) and the fascia / parapet heights are linear between `hb()` at those vertices,
exactly as the deck's boundary edges (`edge_runs` returns each run's ring segment and its end fractions). Self-check
`stats.edges_lod0.parapet_foot` (every parapet's base vs the deck's own top triangles every 0.5 m): 46,920 samples, 0 m beyond
0.02 m (largest 0.002 m). `pfloat.py`: floating > 0.02 / > 0.05 m 50 / 18 m (r22) -> 230 / 37 m (round 4) -> 2 / 0 m; buried
> 0.02 m 27.1 -> 82.3 -> 1.6 m2. `guard.py`: open edge 1,257 -> 929 -> 882 m, drop 0.5-1.5 m 315.6 -> 100.0 -> 100.0 m, drop > 4 m
137.4 -> 109.8 -> 95.2 m (the 2-m tool artefact at (-1544.1, 481.7) is gone; the rest are the ITB plate's h 12.30 edges, as r22).
Cost: LOD0 50,912 -> 57,753 triangles, the full file 4.69 -> 5.27 MB (more edge quads, the abutments and soffits of R4f2.6).

### R4f2.3 Low step faces inside carriageways (minor): partly - reported by height; both suggested remedies tried and rejected

`stats.edges_lod0.step_face_by_height_m` (build, LOD0, by the step at the run ends): 0.02-0.05 m 105.3, 0.05-0.10 m 65.8, 0.10-0.20 m
99.7, 0.20-0.30 m 88.0 m, plus 95.5 m that is the ITB lower sidewalk's 0.15-m kerb over its roadway (by design, now its own class);
`stats.edges_lod0.step_face_top` lists the sites. Round 4 had 498.5 m in one figure (kerb included). On the mesh (`f2/steps.py`:
vertical concrete 0.02-0.31 m tall above grade, kerb included): 0.02-0.10 / 0.10-0.20 / 0.20-0.31 m: round 4 92.6 / 152.8 / 65.2 m,
now 103.3 / 163.7 / 58.7 m - not resolved. Tried:
- the verifier's first option, blending decks that share no node as well (e1, full below 0.30 m): it moves the step to the deck's
  other neighbours at junctions where three or more pieces meet (the 0.05-0.30 m contact stayed 172 m in the lab) and raised the
  mesh maximum to 13.7 %;
- the second, two levels with a median barrier from a 0.05-m step (e2, STEP_LIP): the in-carriageway parapet self-check went
  52 -> 427 m (80 clusters, 18.7 m at (-1472.9, 471.5)): at junction pieces with 0.07-0.23 m between them every side became a
  barrier, a lattice across the junction (`f2/an_edges.py`).
What is left (`f2/an_contacts.py`, contact with a 0.05-0.30 m step): 72 m between connected decks where their profiles part through
0.6-0.75 m (the blend's fall-off), 86 m between decks that share no node at junctions and parallel carriageways (41015033 /
41015044), 14 m at continuations. A clean fix needs one warped surface per junction (a joint level solve over the touching
pieces) rather than per-way ribbons - deferred, recorded here.

### R4f2.4 Records (minor): fixed

Inline "[corrected in close-out r4: ...]" notes added to R3f2.2 (lower roadway at 6.27 m, not 5.80 m, floored by the at-grade roads
256787736 / 93671776, a three-level stack; deck to deck 5.08 m; 160.3 m2 below 4.6 m) and to the `docs/research/buildings3d.md`
fix-2 v1 row; the R4.1 table's grade row now says it is the profiles' maximum, with the round-4 mesh figures.

### R4f2.5 Conflicts left with their owners (minor): unchanged

`b3d_integrate` 7 conflicts / 14 notes as round 4: roads over roads 3.88 m at (-1307.8, 483.4), deck 6.27 m, 160.3 m2 (ITB L3 level:
ITB group / owner, +0.8 m on `level3.floor`; not guessed); the domestic departures loop 3.53 m over 26 at-grade roads, 758 m (owner:
posted clearance); interchange_2_2 4.60 m over 1.0 m (numerical); the four narrowed stacked cuts, including 370279626 cut to 0.00 m
under 35157100 over 51 m. Holding diverge branches at the main deck's level over their overlap (`roadways_net` solve) is deferred:
it changes grades and clearances network-wide, and the mesh-grade self-check above is now in place for when it is done.
`rrclear.py` on the mesh: min 3.88 m, 444.9 m2 below 4.6 m (with the 4.20-m ITB lower sidewalk under the plate) - unchanged.

### R4f2.6 Columns under decks just above the fill level (minor): fixed

The soffit is now built on every triangle with a vertex at or above FILL_H (round 4: all three), at the deck depth below the top
(not below grade), and where such a triangle meets an all-fill one an abutment face from grade to the soffit closes the fill (142.5 m
at LOD0); columns run 0.15 m (COL_TOP) up into the 1.2-m deck box. Self-check `stats.columns_vs_soffit`: 300 of 300 columns reach a
soffit triangle at the centre and 0.3 m round it (largest soffit offset 0.063 m; round 4: 298 of 300 by the verifier's test,
35157016 at (-1796.4, 753.6) and 186398851 at (-1592.6, 500.0) without one). `b3d_integrate` finds no new clearance conflict from
the added soffits.

## Round 5 (residuals) - close-out round 5, fix round 1 (9 Nov 2026; the round-4 fix-2 verifier's residuals, scratchpad `c4_r4verify2_integration.json`)

Rebuilt after the round-5 building rebuilds (R5 of `buildings_closeout.md`; the landside asset changed, and the roadway trims read
its triangles): `roadways.glb` 5,266,908 -> 5,296,016 B (sha1 950d31fa -> d33aa2a0; LOD0 / LOD1 / LOD2 tris 57,753 / 16,243 /
7,338 -> 57,987 / 16,421 / 7,340), `roadways_lod2.glb` 476,072 -> 476,212 B, `integration.json` / `integration.js`,
`manifest.json#roadways` / `#integration` (final run 05:12-05:22Z, scratchpad `c5/buildings/final2/chain2.sh`). Dev builds g1 / g2
(`c5/buildings/rw/`, outputs redirected) and the round-4 verifier's own scripts (`grades`, `soffit_close`, `ledges`, `pfloat`,
`incarr`, byte-identical copies in `c5/buildings/rw/rv/`, run on the installed files: "r4" = sha1 950d31fa, "now" = d33aa2a0) give
the numbers below. No replays were run.

### R5.1 Joints open underneath (f3 residual 1 + f6 residual 2): closed

`build_piece` now builds, on every inner run (a joint with a neighbouring piece, LOD0 / LOD1), an UNDER-JOINT face where this
deck's underside at the joint is higher than the neighbour's: from the neighbour's underside (its soffit after a 0.02-0.30 m step,
or grade under an all-fill neighbour - the cross-piece fill case) up to this deck's soffit, facing into this deck's under-space.
The undersides come from `_bottoms()` (each piece's own plan triangulation and per-corner soffit / grade, cached per LOD), probed
5 % in from the run ends, 0.06 m into this deck and 0.06 / INNER_GAP + 0.06 m into the neighbour (a neighbour may stand off by up
to INNER_GAP: the first dev build closed only 9.2 of the 16.5 m of cross-piece joints). A probe that still finds no underside takes
the first OTHER neighbour's at that point [superseded in fix round 2, R5f2.1: without an abutment test this fallback took decks
passing underneath and at-grade roads under flyovers - 6-14 m walls through the carriageways; now only pieces that abut at deck level] (edge_runs gives one neighbour per run; deck 35157100's 4.4-m run at (-1607.7, 459.1)
starts on ramp 735035451 and ends on ramp 735035452, 0.92 m from the first: the last cross-piece fill joint the 04:47 build left
open). New build self-check `soffit_check()` (the verifier's soffit_close rule: every LOD0 soffit boundary edge every 0.5 m,
closed by a vertical face spanning it or a continuing soffit) -> `roadways_build.json#stats.soffit_closure` and
`manifest.json#roadways.closeout_r4.closeout_r5`.

| LOD0 soffit boundary 22,244 m (verifier's `soffit_close.py`) | r4 | now |
|---|---|---|
| closed by a face | 18,773.2 m | 19,612.6 m |
| soffit continues | 3,083.3 m | 2,573.6 m |
| open into a hollow (see-through) | 330.4 m | 2.8 m (largest 1.0 m at (-1545.6, 469.7)) |
| open, nothing above | 56.9 m | 54.5 m |
| the verifier's cross-piece fill joints (-1607.7, 459.1) / (-2024.4, 444.4) / (-1493.7, 470.7) / (-1609.4, 453.0) | 6.4 / 4.1 / 3.5 / 2.5 m | 0 / 0 / 0 / 0 |
| the ITB lower-sidewalk kerb (-1316.2, 353.4), walk soffit 4.75 m over roadway soffit 4.60 m | ~190 m open | closed |

Under-joint faces 448.1 m at LOD0 (18.5 m of them down to grade under an all-fill neighbour); probes left unresolved 269.9 m
(04:47 build 366.0 m; the soffit check leaves at most 2.8 m of see-through edge, so all but that are closed by another face or a
continuing soffit).
LOD1 (same script, `soffit_close.py 1`): open into a hollow 544.8 -> 174.6 m, open other 284.8 -> 269.5 m (the LOD1 soffits are
simplified by 0.35 m, so more of their joints stand off beyond the probes); LOD2 builds no under-joint faces (`roadways_lod2.glb`
LOD2 subtree unchanged by R5.1).
The 0.02-0.30 m LEDGES on the deck tops themselves are unchanged (`ledges.py` deck-to-deck 239.2 m, 87.5 m of them 0.10-0.31 m;
r4 239.2 / 87.5 m): two decks that meet with a small step are still one carriageway with a drivable ledge and no barrier. Both
quick remedies were rejected in R4f2.3; the fix is one warped junction surface (a joint level solve over the touching pieces) - an
open item for the integration track, with the ledge length by height kept in `stats.edges_lod0.step_face_by_height_m`
(0.02-0.05 105.3 / 0.05-0.10 65.8 / 0.10-0.20 99.7 / 0.20-0.30 88.0 m, walk kerbs 95.5 m).

Unchanged by these faces (same scripts, r4 -> now): max grade 13.37 % -> 13.37 %, area > 10 / 12 / 13.5 % 784.3 / 36.5 / 0 m2 ->
the same; barrier feet floating > 0.02 m 0.8 m2 -> 0.8 m2, buried > 0.02 m 1.6 -> 1.6 m2; in-carriageway parapet 36.9 m -> 36.9 m;
columns 300 / 300 on a soffit (largest offset 0.063 m).

### R5.2 Creases at the joint wedges (residual 3): analysed, trial reverted, deferred; a fold regression gate added

The wedge's level IS the exact C0 fill: `hp()` depends on the station only, so the caps of both decks a wedge closes are at the
node level over their whole width, and a flat wedge at that level meets both without a step. The fold where it meets a graded deck
(6.4 deg beside the 11.2 % ramp at (-1610.4, 449.1)) is that deck's own grade. Dev build g1 tried the verifier's option (each
deck's end-slope extrapolation `hp_ext`, distance-weighted across the wedge): mesh max grade 13.4 -> 79.4 % (0.0015-m2 slivers at
the ITB L3 joint (-1370.3, 301.2) and the domestic joint (-806.2, 333.3)), folds > 3 / 4 / 6 deg 31 / 10 / 6 -> 50 / 26 / 17 - the
caps still pin both edges at the node level, so the extrapolation only adds a bulge. Reverted (the `hb()` docstring records the
trial). Removing the fold needs the same warped junction surface as R5.1's ledges. Folds now (= r4 fix 2): > 1 / 2 / 4 / 6 deg 226
(1,430 m) / 84 (518 m) / 10 (28.9 m) / 6 (23.3 m) (r22: 107 / 56 / 5 / 2). New `stats.mesh_grades.fold_gate` (also in
`closeout_r5.fold_gate`): the fold edge over 4 / 6 deg may not exceed the r4 fix-2 build's 28.9 / 23.3 m + 5 % (`FOLD_GATE_M`
30.4 / 24.5 m; a WARNING line otherwise): ok.

### R5.3 `b3d_integrate` silently depended on gitignored out/ files (residual 4): fails loudly; the bridge solids moved to a tracked input

- `_input()` records each required input with its sha1 and mtime in `integration.json#plausibility.stats.inputs`; a missing or
  unreadable one is a CONFLICT 'input missing: ...' and the checks that need it are not run (the `tools/stands/geom.py`
  whole-file fallback for the bridge solids is gone; the at-grade clearance and stacked-cut checks no longer return behind a log
  line). `--check` exits 2 when an input is missing; a full run REFUSES to write integration.json / .js / the manifest (exit 2).
- The bridge solids now come from `tools/blender/app_bridges.json` (TRACKED; the dump of the current `js/live/gates.js` + stands by
  `node tools/blender/app_bridges.mjs`, whose currency verify_domestic gates): the fixed walkway segments and rotunda drums of the
  rest pose (the fixed parts are the same in every pose). The gitignored `out/draw/scene2d.json` the round-4 check read was not only
  missable but stale: generated 7 Nov 10:35Z (git e87c2d2), before later `data/sfo_stands.js` changes - 10 walkway attach points
  0.02-1.18 m off the current ones (B2 1.18, A15 0.54, E8 0.52 m; `_scene_currency`, now an informational note). The pedestal
  column under a drum is not in the dump, so it is not tested here (scene2d.json carried it).
- Tests (`c5/buildings/integ2/t_check.py`, --check, OUTD redirected): real inputs -> 7 conflicts (line-for-line round 4's) / 15
  notes (round 4's 14 + the stale-scene2d note), exit 1 as round 4; both required inputs pointed at missing paths -> 3 'input
  missing' conflicts (bridge solids; at-grade clearance inputs; roadways build record), exit 2.
- The full run of the chain: 7 conflicts / 15 notes, the conflict and note lines identical to round 4's report apart from that one
  note; integration.json 992 kB / integration.js 237 kB; `b3d_lod2_check` 47 units / 0 flagged (r4 47 / 0); `tools/sat/check.py`
  0 issues / 0 app issues / 41 warnings (r4 the same).

### R5.4 Records (residual 5): fixed

The R4.1 "Connected decks meet halfway" bullet carries "[superseded in fix round 2, R4f2.1: ...]".

### R5.5 Conflicts left with their owners (residual 6): unchanged

As R4f2.5: roads over roads 3.88 m at (-1307.8, 483.4), 160.3 m2 (ITB L3 level: ITB group / owner, +0.8 m on `level3.floor`), the
domestic departures loop 3.53 m over 26 at-grade roads, 758 m (owner: posted clearance photo or sign), interchange_2_2 4.60 m over
1.0 m (numerical), the four narrowed stacked cuts (370279626 cut to 0.00 m under 35157100). Not guessed; holding diverge branches at
the main deck's level (`roadways_net`) stays deferred, now with the mesh-grade and fold gates in place for when it is done.

### Round 5 dispositions (`c4_r4verify2_integration.json`)

| residual | status | evidence |
|---|---|---|
| 1 f3 ledges + their soffits open underneath | partly | R5.1: underneath closed (see-through soffit edge 330.4 -> 2.8 m); the deck-top ledges (239.2 m) deferred to a junction surface |
| 2 cross-piece fill joints without an abutment | fixed | R5.1: 16.5 -> 0 m at the verifier's sites; self-check `soffit_closure` [LOD0 only - LOD1 174.6 m stayed open; closed in fix round 2, R5f2.2] |
| 3 creases at the wedges | deferred | R5.2: trial reverted with evidence (79 % slivers); fold gate added |
| 4 b3d_integrate silent on missing out/ files | fixed | R5.3: input-missing CONFLICT + exit 2 + refuse to write; bridge solids from the tracked dump |
| 5 R4.1 bullet pointer | fixed | R5.4 |
| 6 deferred conflicts | needs owner | R5.5 |

## Round 5 (residuals) - close-out round 5, fix round 2 (9 Nov 2026; the round-5 verifier's findings, scratchpad `c5/buildings_ver1`)

Rebuilt after the fix-2 building rebuilds (buildings_closeout "Round 5, fix round 2"): `roadways.glb` 5,296,016 -> 5,603,480 B (sha1
d33aa2a0 -> e2869621; LOD0 / LOD1 / LOD2 tris 57,987 / 16,421 / 7,340 -> 57,971 / 22,151 / 7,340: LOD1 keeps the LOD0 outlines,
R5f2.2), `roadways_lod2.glb` 476,212 B (same size and triangles; 193 vertices of `L2_domestic_departures` moved <= 0.014 m with the
domestic rebuild the trims read), `integration.json` / `integration.js`, `manifest.json#roadways` / `#integration`; roadways build
08:32-08:36Z (`c5/buildings/f2/final/chain.sh`), integration final run after the last landside build (`f2/fin3/chain.sh`).
Every before / after number below ran on the SAME script on both files: the round-5 verifier's own `thrudeck.py` (input paths from
the environment, rule unchanged), `soffit_close.py` (md5 6f4d60ee), `grades.py` (92b06d39), `ledges.py` (a4ad7156), `pfloat.py`
(69fdbe99) on the fix-1 file (`rw_fix1.pkl`, sha1 d33aa2a0) and the installed one (`rw_f2.pkl`, e2869621); the same rules are now
build self-checks. An offline harness (`c5/buildings/f2/rw/uj.py`: `build_piece` from the fix-1 copy vs the current module on the
same trimmed pieces) reproduced the verifier's fix-1 figures exactly before the build (LOD0 / LOD1 open into a hollow 2.8 / 174.6 m,
through-deck faces 1,850 / 51, wall area 12.5 / 143.6 m2). No replays were run (harness for the record: invariants.mjs e52f3dfd,
build_stream.py 93da6fe0).

| check (same script both arms) | fix 1 (d33aa2a0) | fix 2 (e2869621) |
|---|---|---|
| vertical concrete faces a deck / walk top passes through, LOD0 (`thrudeck`) | 1,850, of them walls 12.5 m2 at 3 new sites (5.0-13.8 m tall) | 1,839 - none new vs fix 1; tallest 1.53 m, <= 1.38 m above the top (the r4 ledge family); walls 0 |
| the same, LOD1 | 51, walls 143.6 m2 at 7 sites (up to 0-14.3 m) | 3 (<= 1.43 m tall, <= 1.01 m above the top); walls 0 |
| soffit edge open into a hollow / open other, LOD0 (`soffit_close`) | 2.8 / 54.5 m (face 19,612.6 m) | 2.8 / 56.9 m (face 19,606.8 m) |
| the same, LOD1 | 174.6 / 269.5 m (face 19,547.2 m) | 7.8 / 55.2 m (face 19,784.3 m) |
| mesh grades (`grades`) | max 13.4 %; folds > 1 / 2 / 3 / 4 / 6 deg 226 / 84 / 31 / 10 / 6 | identical |
| deck-top ledges deck > deck (`ledges`) | 239.2 m | 239.2 m (deferred, R5.1) |
| parapet floats / buried > 0.02 m (`pfloat`) | 0.8 / 1.6 m2 | 0.8 / 1.6 m2 |
| `b3d_integrate --check` with a stale dump (the verifier's test: gates.js hash zeroed, A2 / B2 / E8 moved 1.2 m) | 7 conflicts / 14 notes, exit 1 - identical to the current dump | CONFLICT 'input stale: app_bridges.json predates js/live/gates.js' + the 7, exit 2 (full run refuses to write) |

### R5f2.1 Under-joint 'closures' standing in the carriageways (major, regression of R5.1): fixed at the root, gated

Root cause: R5.1's fallback took, for an under-joint probe the run's neighbour left unresolved, the underside of ANY other piece near
the deck at the probe point - a deck passing underneath (interchange_2_2 at (-1618.9, 544.3): 5.01 .. 13.57 m through deck_1o at
6.21 m) or an at-grade road under a flyover (LOD1 (-1688.1, 540.4): 0 .. 14.19 m) - and built a wall from it up to this soffit.
`build_piece` now accepts a piece (the run's neighbour first, then the others) only where it REALLY abuts at deck level: at the probe
point its top is within `UJ_TOP_TOL` (STEP_TOL + 0.1 = 0.40 m: the probes sit 5 % in from the run ends, where a step that edge_runs
found below STEP_TOL may have grown a little) of this deck's top, and its underside is within DECK_DEPTH + STEP_TOL below this
soffit, or it is grade under an all-fill deck (top below FILL_H). A probe nothing qualifies for stays unresolved (counted: LOD0
273.2 m, LOD1 216.5 m); a hard cap stops any closure taller than DECK_DEPTH + STEP_TOL unless it goes to grade under a fill deck
(capped this build: 0 m). New build self-check `thru_check()` (the verifier's thrudeck rule, LOD0 and LOD1): a vertical concrete face
that a deck / walk top passes through AND that rises more than `THRU_RISE` (DECK_DEPTH + PARAPET_H = 2.05 m: the most a fascia +
parapet can rise above a neighbouring deck) above that top is a WALL - gate 0 at both LODs; the rest (fascias / parapets a
neighbouring deck's top cuts near their foot at a joint) is the deferred ledge family with a regression ceiling (`THRU_LEDGE_MAX`
1,950 / 10). The gates stop the build BEFORE anything is written (exit 3; `RW_GATE_WRITE=1` writes anyway, dev builds only).
Build self-check: LOD0 1,839 faces / 0 walls, LOD1 3 / 0. (The manifest record string of this rule said 'top within 0.30 m' - the
code uses 0.40 m; corrected in the code and in `manifest.json#roadways` by `c5_manifest.py`.)

### R5f2.2 LOD1 soffits open into a hollow (integ-1 / integ-2 at LOD1): fixed at the root, gated

The verifier's LOD-aware probes were tried first (UJ_PROBE to INNER_GAP + 0.35 m at LOD1, abutters only): 174.6 -> 172.1 m - the LOD1
residual is not a height step. Diagnosis (`f2/rw/dbg_site.py` at (-1527.8, 472.6), (-1790.9, 441.5), (-1519.2, 513.0)): equal soffit
levels on both sides of the joint, the neighbour's underside found only 0.46 m into it - LOD1 simplified every piece's outline by
0.35 m ON ITS OWN, so neighbouring decks no longer met: see-through slits up to ~0.4 m at the LOD1 joints, in the tops as in the
soffits (no vertical face closes a plan gap). LOD1 now keeps the LOD0 outline (`LOD_SIMPLIFY[1]` 0.35 -> 0.05, `INNER_GAP[1]` 0.40 ->
0.08); it still saves on the 16-m triangulation, the single-quad parapets and the 6-sided columns. Cost: LOD1 16,421 -> 22,151 tris
(+5,730; LOD1 is the desktop 400-1,400 m band and the phone near mode once the full file loads; the phone far file
`roadways_lod2.glb` is unchanged). New gate: soffit open into a hollow <= `SOFFIT_GATE_M` 5 m (LOD0) / 12 m (LOD1); this build 2.8 /
7.8 m. *(Round 6, R6.2: the trade-off's other side - LOD1 inherits the LOD0 wedge creases and gains long LOD1-only creases where the
LOD0 outline vertices fan into the 16-m interior triangles: LOD1 folds > 2 / 4 / 6 deg 34 / 9 / 6 -> 86 / 17 / 8 (LOD0 84 / 10 / 6).
Now reported with a regression ceiling.)*

### R5f2.3 `b3d_integrate`: a stale bridge dump fails loudly; the pedestal is tested again (integ-4): fixed

`_dump_current()` recomputes the SHA-256 of every file `tools/blender/app_bridges.json` records in `inputs` (js/live/gates.js,
data/sfo_stands.js, data/sfo_buildings.js, js/live/airport.js, js/geo.js); a mismatch is a CONFLICT 'input stale: app_bridges.json
predates <file>', the walkway / drum / pedestal tests are not run on it, `--check` exits 2 and the full run refuses to write (as for
a missing input). `app_bridges.mjs` now dumps the rotunda PEDESTAL with the walkway segments and drums (gates.js solidsQ part
'pedestal'); `b3d_integrate` tests host surfaces inside it ('rotunda pedestal: host building surfaces inside it'): 131 pedestals,
0 contacts above 0.05 m2. The dump was regenerated 08:13Z (131 bridges + 131 pedestals; every other value identical to the 03:31Z
dump, inputs unchanged); the other consumers filter on `part` (dom_geom, bridge_head door-member obstacles, app_bridges.py,
verify_domestic / verify_itb).

### R5f2.4 Re-run and records

Final run after the last landside build (`c5/buildings/f2/fin3/chain.sh`): `b3d_integrate` 7 conflicts / 15 notes, the conflict and
note lines identical to fix 1's (md5 of the lines f9f333a5; exit 1 = conflicts present, as before); bridge dump current; 131
pedestals tested, 0 contacts; footprint tiers 156,717 vertices, 0 outside; `b3d_lod2_check` 47 units / 0 flagged; `tools/sat/check.py`
0 / 0 / 41 warnings. Two redirected roadways dev builds after it (`f2/rw/gfin`, `gfin3`) give the installed `roadways.glb` /
`roadways_lod2.glb` byte for byte (e2869621 / 3b031edf). `manifest.json#roadways` / `#integration`: `closeout_r5` restored after their
rebuilds dropped it, plus `r5f2-under-joint-walls`, `r5f2-lod1-soffit`, `r5f2-stale-dump` (`tools/blender/c5_manifest.py`).

R5.1's integ-2 'fixed' was LOD0-only (the verifier: LOD1 174.6 m still open) - R5f2.2 closes it at LOD1. The R5.1 sentence "A probe
that still finds no underside takes the first OTHER neighbour's" is the cause of the major (R5f2.1) and carries a "[superseded in
fix round 2]" note.

### R5f2.5 Owner items and deferred (unchanged, not guessed)

As R5.5: roads over roads 3.88 m (ITB L3 level), the domestic departures loop 3.53 m over 26 at-grade roads (posted clearance),
interchange_2_2 4.60 m over 1.0 m, the four narrowed stacked cuts. Deferred: the deck-top ledges (239.2 m; 87.5 m of 0.10-0.31 m)
and the wedge creases (folds 226 / 84 / 31 / 10 / 6) need a warped junction surface, gated by `fold_gate`, `mesh_grades` and now the
through-deck ceiling.

### Round 5 fix round 2 dispositions (`c5/buildings_ver1` findings)

| finding | status | evidence |
|---|---|---|
| (major) under-joint fallback walls through lower carriageways | fixed | R5f2.1: walls LOD0 / LOD1 12.5 / 143.6 m2 -> 0 / 0 (verifier's thrudeck, same script); build gates 0 |
| integ-1 / integ-2 at LOD1 (soffit open into a hollow) | fixed | R5f2.2: 174.6 -> 7.8 m (open other 269.5 -> 55.2 m); LOD1 gate |
| integ-4 stale bridge dump; pedestal dropped | fixed | R5f2.3: stale -> CONFLICT + exit 2; pedestal test restored (0 contacts) |
| deferred ledges / creases, owner conflicts | deferred / needs owner | R5f2.5 (unchanged: 239.2 m, folds as r4, 7 conflicts) |

## Round 6 (follow-up on close-out round 5 verifier 2) - 9 Nov 2026

Input: SP/c5_r5verify2_buildings.json (5 minors; (c) and (d) are this doc's). Work log SP/c6/buildings/NOTES.md. Same script on both
arms for every before / after pair; no tools/live replays (harness md5s for the record: invariants.mjs e52f3dfd, build_stream.py
93da6fe0 - not run).

### R6.1 `app_bridges.json`: the generator and the schema are part of the currency check (r5 verifier 2, (d)): fixed

`app_bridges.mjs` decides with its part filter which solids the dump carries, but it was not among the hashed inputs: a dump from an
older generator (e.g. one from before the r5 pedestal) passed `_dump_current()` silently. Now:
- `app_bridges.mjs` hashes ITSELF with the five data inputs and writes `schema: {version: 2, parts: ['walkway', 'rotunda', 'pedestal']}`
  (one list, `REST_PARTS`, is both the part filter and the schema); it warns when a bridge lacks a part.
- `b3d_integrate._dump_current()` (`DUMP_GENERATOR`, `DUMP_SCHEMA`) emits CONFLICT 'input stale' (exit 2 under `--check`, the full run
  refuses to write) when the generator's hash is not recorded or differs, when the schema differs, or when any bridge lacks any schema
  part ('3 of 131 bridges have no pedestal part (e.g. A1/A1/1, ...)').
- Unit test (SP/c6/buildings/integ/t_dump.py, `_dump_current` on variants of the new dump): current 0 conflicts; the r5 dump 3 (gates.js
  stale - the runtime track has edited it since -, generator unrecorded, schema {}); pedestals removed on 3 bridges 1; schema v1 1;
  generator hash changed 1; generator unrecorded 1.
- The dump was regenerated (11:31Z): bridges and departure levels identical to the r5 dump (131 bridges, 131 x walkway / rotunda /
  pedestal); only the gates.js hash moved and the generator hash / schema are new. The check stays hash-based: a dump edited by hand
  with current hashes still passes (acceptable for a generated file; recorded).

### R6.2 LOD1 deck folds: reported with a regression ceiling (r5 verifier 2, (c)): partly (gated, creases deferred)

`grade_check(mb, log, lod)` now also runs on LOD1 (`gchk1`; manifest `roadways.closeout_r5.closeout_r6`: `lod1_mesh_folds`,
`lod1_fold_gate`, `lod1_fold_top`). Ceiling `FOLD1_GATE`: folds over 4 / 6 deg at most 17 / 8 and 95.2 / 53.0 m of edge (the r5
fix-2 build as measured + 5 % on the length; WARNING + `ok` false in the record, like the LOD0 fold gate). **[Corrected in round 7
(r6 verifier (c)):** in round 6 neither ceiling was enforced: no gfail entry, exit 0, and no tool read the flag. Round 7 enforces both
(R7.1).**]** Measured with the same
function on a dev build of this code (SP/c6/buildings/rw/d1, glb byte-identical to the installed e2869621 / 3b031edf): LOD1 folds
> 1 / 2 / 4 / 6 deg 209 (1,405 m) / 86 (541 m) / 17 (90.7 m) / 8 (50.5 m) = the verifier's 86 / 17 / 8; LOD0 226 / 84 / 10 / 6
unchanged; worst LOD1 folds 8.0 deg (8.4-m edge) at (-1558.6, 478.8), 7.1 deg along 15.6 m at (-1579.8, 447.0) - all in
interchange_2_2. The trade-off (R5f2.2: +5,730 LOD1 triangles for the slit / soffit fix; the creases its cost) is recorded there.
Not done: Steiner points from the LOD0 height field or a shorter LOD1 SEG on warped pieces (more LOD1 triangles; deferred with the
LOD0 crease item). The installed roadways rebuild (12:01Z, build 0, no gate fail) is byte-identical (sha1 e2869621 / 3b031edf).

### R6.3 Re-run (12:05-12:13Z, after the landside rebuild; buildings_closeout R6)

- `b3d_integrate` (full): exit 1 = 7 conflicts / 15 notes, the conflict and note lines identical to round 5's final run (md5 of the
  lines be8a0d44 both); bridge solids inputs: 6 checked (incl. the generator), stale [], schema v2, schema problems [].
- `b3d_lod2_check`: 47 units, 0 flagged. `tools/sat/check.py`: 0 issues, 0 app issues, 41 warnings (as round 5).
- verify_itb 138 / 0, verify_domestic 69 / 0 (writes redirected; they read the regenerated dump: current).

### Round 6 dispositions (`c5_r5verify2_buildings.json`, this doc's items)

| Finding | Status | Evidence |
|---|---|---|
| (d) dump currency misses generator changes | fixed | R6.1: generator hashed + schema; CONFLICT on generator / schema / missing part (6 variants tested) |
| (c) LOD1 creases (side effect of the LOD1 soffit fix) | partly | R6.2: LOD1 fold report + ceiling 17 / 8 folds (95.2 / 53.0 m) over 4 / 6 deg; trade-off recorded; creases deferred |


## Round 7 (follow-up on the round-6 verifier + realtime request C5.1) - 9 Nov 2026

Work log: `SP/c7/buildings/NOTES.md`.

### R7.1 Fold gates are enforced (r6 verifier (c))

**What changed**
- `build_roadways.py`: `gfail` now includes the LOD0 fold gate (`FOLD_GATE_M`) and the LOD1 fold gate (`FOLD1_GATE`). A ceiling
  breach stops the build before anything is written (exit 3), like the through-deck and soffit gates. `RW_GATE_WRITE` still forces a
  write.
- `b3d_integrate._roadway_gates`: every `*fold_gate` record under `manifest.json#roadways` must say `ok`. If one does not (e.g. a
  forced build), that is a CONFLICT; the checked paths are listed in `inputs`.

**Tests**
- `SP/c7/buildings/rw/t_gfail.py` (`808947c3`) evaluates the gfail expression, extracted with ast, on synthetic gate records:

  | case | before | after |
  |---|---|---|
  | as installed (17 / 8 and 10 / 6) | 0 | 0 |
  | LOD1 over the ceiling | 0 | 1 |
  | LOD0 over the ceiling | 0 | 1 |
  | no fold record | 0 | 0 |

- `SP/c7/buildings/integ/t_gate.py` (`ebb1de20`): installed manifest 0 conflicts (3 gate paths checked); LOD1 gate flipped to false:
  1 CONFLICT.
- The roadways glb is not rebuilt: its geometry is unchanged, and the installed record (17 / 8 and 10 / 6) passes the new gate.

### R7.2 An empty or short bridge dump is stale (r6 verifier (d))

`_dump_current` now gives CONFLICT 'input stale' (exit 2 under `--check`) in two cases:
- an empty `bridges` list;
- fewer bridges than `out/draw/scene2d.json` has, when that file exists (it has 131).

Test: the verifier's `t.py` (`11651e64`) plus a "short by 10" variant, with ROOT patched so the backup module reads the repo inputs
(`SP/c7/buildings/integ/t7.py`, `1ad7f2b1`). Before -> after:
- zero bridges: 0 -> 1;
- short by 10: 0 -> 1;
- the other 8 variants unchanged (current 0, generator changed 1, generator unrecorded 1, no schema 1, schema reordered 1, one
  bridge without a pedestal 1, extra part 0, geometry-only edit 0).

### R7.3 Request C5.1: provenance and height band of the footprints under the reported wings

**`physics.rings[82]` (old index) is the landside unit `bart_station`.** That is the SFO BART station complex, Building 497.
- Plan: OpenStreetMap way 221663595 'train_station' (ODbL), cross-checked within ~1.5 m against the NAIP 2024 north wall line
  [obs]. The Garage G body and the ITB outline are subtracted. Code: `landside_geom.bart_footprint`.
- Heights: [inf], from photo-a2 proportions. The ground storey is open on columns.
- Its tiers (world y, grade 3.0):
  - `body`, from grade to 21.13: 200 m2. These are the columns and walls that stand on the ground.
  - `over`, from 8.9 (5.9 m above grade) to the top: 1,526 m2.
  - `over`, from 18.48 (15.5 m above grade): 4,868 m2. This is the deck under the AirTrain.
  - smaller pieces higher up.
- Within half-span + 6 m of the reported points:
  - UAL1757: body 10 m2, over 5.9 m 94 m2, over 15.5 m 27 m2;
  - CFJNX: body 4.6 m2, over 5.9 m 45 m2.

**The SFO Museum 'Garage A' outline** (`data/sfo_airport.js` structure, kind garage):
- It reaches to 16.2 m of the AMX664 point. Its east part extends to x -1252.
- The 3-D asset `garage_a` (x -1533..-1383) is 58.5 m away. It replaces the outline (replace table cover 0.849).
- The grid should use the asset footprints (`physics`) and not this outline.

**The real problem is the positions, not the footprints.** All three reference points lie on the LANDSIDE. In the same frame
(`data/sfo_airport.js`: x east, z south, origin ARP; the outline and the asset rings coincide):

| aircraft | point | outside the International Terminal outline | nearest taxiway polygon |
|---|---|---|---|
| UAL1757 | (-1421.5, 239.2) | 90.6 m west | 390 m (B5) |
| AMX664 | (-1328, 535) | 86.2 m west | 692 m (A/H) |
| CFJNX | (-1611.6, 324.2) | 258.8 m west | 485 m (B5) |

They sit beside the BART station, Garage G, the ITB departures roadway and the AirTrain. No airliner can be there. Neither footprint
is wrong. See the realtime request below.

**Height bands (done in `b3d_integrate`).** Each physics ring now carries:
- `y[i]`: its world-y band [underside, top];
- `unit[i]`: an index into `units` (group/unit/band).

How the rings are built:
- A unit's tiers are grouped into underside bands `PHYS_BANDS` = 0 / 3 / 6 / 10 / 15 m above grade. Each group sits at its lowest
  underside.
- An `over` tier below 3 m joins the body.
- Each plan point goes to its lowest band only.
- Any footprint no tier covers blocks from grade.

The BART station now reads as:
- body [3.0, 21.13]: 55 + 88 m2;
- over >= 3 m [8.9, 21.13]: 504 + 851 m2;
- over >= 15 m [18.48, 21.13]: 6,465 m2.

A consumer that ignores `y` blocks the same area as before. The union is 385,918 -> 385,781 m2. The differences (387 m2 lost,
251 m2 gained) come from the 0.1-m simplification of the tier rings.

**Cost**
- Rings 91 -> 741, vertices 2,284 -> 9,055.
- `integration.js` 235,864 -> 362,528 B (+127 kB); `integration.json` 1,007,167 -> 1,146,105 B.
- `PHYS_BANDS = [0.0]` restores one ring set per unit if the lead prefers the smaller file.

**Request to the realtime track** (their files; not edited here):
1. `js/live/ground.js` buildingGrid (and the harness `building` rule): read `physics.y`. A body part whose top is below a ring's
   underside (`y[i][0] - GROUND_Y` above grade) does not collide with that ring. Use a wing at 4-6 m, and the fin / tail for the
   tall types.
2. Find out why bodies sit on the landside:
   - UAL1757 "taxiing", 5 Nov 04:10:56Z;
   - CFJNX "kept parked by repos", 5 Nov 09:44:26Z;
   - AMX664, 7 Nov 03:48:51Z.

   Each is 390-692 m from any taxiway and 86-259 m west of the ITB, on roads that the rendered pavement mask may include. Either
   the ADS-B surface positions there are spurious (multipath near the ITB / garages) and should be rejected, or the harness frame /
   repos placement is off. A parking repos must stay on airside pavement (owner rule).

### R7.4 Re-run after the landside rebuild

All results are on the files built this round (landside `845ea564` / lod2 `f47a0e3f`; roadways unchanged, `5d742b38` / `9e6f5802`).

- **b3d_integrate** (run twice; the second run after the band grouping): exit 1, 7 conflicts / 15 notes.
  - The conflict and note lines, keys stripped, md5 `55e2b851`, equal round 6's.
  - Bridge inputs current. Fold gates: 3 paths checked, 0 failed.
  - Footprint tiers self-check: 156,717 vertices, 0 outside.
- **b3d_lod2_check:** 47 units, 0 flagged.
- **tools/sat/check.py:** 0 app issues / 0 issues.
- **verify_itb and verify_domestic:** exit 0 (writes redirected).
- **Output md5s:** `integration.js` `1be9d0fb`, `integration.json` `e8e95c8e`.

### Round 7 dispositions

| finding | status | evidence |
|---|---|---|
| r6 (c) fold ceiling only warns | fixed | R7.1 |
| r6 (d) zero-bridge dump passes | fixed | R7.2 |
| R6.2 wording | fixed | corrected in place |
| C5.1 ring 82 / Garage A provenance + height band | fixed (provenance + bands); positions -> realtime | R7.3 |
