# Requests from the integration track (3-D building assets in the app)

From: owner of `js/three/buildings3d.js`, `tools/blender/{b3d_integrate,b3d_lod2_check,b3d_split,build_roadways,roadways_net,roadways_itb_plate}.py`,
`tools/blender/{b3d_views_job,b3d_glass_job}.mjs`, `data/buildings3d/{roadways,roadways_lod2}.glb`, `data/buildings3d/integration.{json,js}`,
`manifest.json#integration` / `#roadways`, `tools/build3/phone_artifact_page.py`. What changed on this side is in
`docs/research/buildings3d.md` (integration section, "Close-out round 3").

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
