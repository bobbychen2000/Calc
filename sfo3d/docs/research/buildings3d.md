# Buildings in 3-D: Blender assets built from the verified 2-D sheets

The 3-D step of the owner's method (2-D drawings first, then 3-D). Each building group is a glTF 2.0 asset in
`data/buildings3d/`, built procedurally with Blender (bpy 5.0.1, Cycles CPU) from the same code and data as the 2-D sheets
(`docs/drawings/buildings/`), with one key per group in `data/buildings3d/manifest.json`. Each group writes its own section
below.

Common conventions (shared by the groups):
- Frame `ltp-nad83-2011`, the app's world frame: x east, y up, z south, metres from the ARP; the asset's root node sits at
  its world position with y = `GROUND_Y` = 3.0 (js/geo.js). Heights in the sheets are above local grade.
- Root children `LOD0` / `LOD1` / `LOD2` with `extras.lod` and `extras.switch_m`; show one LOD at a time.
- Every node carries `extras` with its source tag (`pub` / `obs` / `inf` / `unk`), the spec keys and per-dimension tags.
- PBR materials; tiling detail maps on `TEXCOORD_0`; sun-independent AO baked by Cycles on `TEXCOORD_1`
  (`occlusionTexture.texCoord = 1`). No imagery is used as a texture (NAIP 2024 only for sampling roof colours).
- Scripts that import `bpy` carry `SPDX-License-Identifier: GPL-3.0-or-later` (Blender licence, engine.md 7.3).
- KTX2 / meshopt compression is a later step (`tools/engine/glb_compress.mjs`).

---------------------------------------------------------------------------------------------------------------------

## International Terminal: main hall, Boarding Areas A and G (key `itb`, 4 Nov 2026)

```bash
python3 tools/blender/build_itb.py          # ~2.5 min: geometry, textures, AO bake (2048 + 512), export, verification, manifest
python3 tools/blender/verify_itb.py         # numbers only, reads the glb back (no bpy) -> out/buildings3d/itb_verify.json
python3 tools/blender/render_itb.py --views west,i4,i3,baa,bag,plan     # Cycles references, ~4 min at 48 spp
python3 tools/blender/ao_view_itb.py        # QA view of the baked AO (emission of the occlusion texture)
python3 tools/blender/ao_view_itb.py --backface --lod 0   # back faces red: the asset is single-sided
```

| File | Role |
|---|---|
| `tools/blender/itb_geom.py` | Geometry (numpy / shapely, no bpy). Imports `tools/buildings/draw_itb.py` / `draw_data.py`: the drawn functions are the reference, not copies. |
| `tools/blender/itb_tex.py` | Our procedural tiles: normal maps (membrane seams, panel joints, curtain-wall caps), frit and curtain-wall base colours |
| `tools/blender/build_itb.py` | bpy build, NAIP roof-colour sampling, AO bake, glTF export, manifest |
| `tools/blender/itb_manifest.py`, `build_itb_manifest_merge.py` | Manifest entry (tags, inferred / unknown / conflicts, budgets); render list |
| `tools/blender/verify_itb.py` | 92 checks against the sheets and the plausibility rules |
| `tools/blender/render_itb.py`, `ao_view_itb.py` | Reference renders of the exported glb; AO and back-face QA views |
| `data/buildings3d/itb.glb` (5.62 MB), `itb_lod2.glb` (0.48 MB) | The asset; the LOD2 subtree alone for the far / phone tier |

**Placement.** Root `itb` at world (−1244.555, 3.0, 365.405), the relief-corrected roof centre (`draw_itb.F`, frame-model
corners of `roof.corners_obs`). Roof frame: u along heading 162.85° (+ towards BA-A), v across (+ ENE).

### What is modelled, and from what

| Node | Source | Notes |
|---|---|---|
| `hall_roof` | obs | 252.87 × 65.40 m slab on the spec corners; top = `roof_line(u)` (BI-02: notches 35.7, humps 40.08, crown 40.1, tips 34.4 held non-increasing); flat across (camber unknown); 0.6 m deck + fascia [inf]; glazed tip bands 18.75 / 15.75 m set 1.6 / 3.6 m inside the fascia [obs]; 5 glazed truss-line strips 1.5 m [obs, rough]; 5 lens skylights from `lens_poly` (size obs, pointed-lens planform inf); dark soffit (photo i3) |
| `hall_trusses` | inf | 5 three-chord trusses on the truss lines (12.12 m [obs]); depth 29 ft over the supports [pub] with the BI-03 taper; webs on the 20-ft grid offset 10 ft (it carries the column lines and the canopy hangers) |
| `hall_columns` | inf | 20 columns (5 lines × ±190 / ±270 ft); the west line 2.5 m in front of the glass, branching into 5 members (count obs, i3 / i4) |
| `hall_outriggers` | inf | eave outriggers under the soffit at every truss node (photo i3) |
| `hall_west_wall`, `hall_mullions` | inf / obs | wall at v −25.8 (middle of the band −28.3..−23.3) over the 705-ft hall [pub]; L3 11.5, head 30.8 [obs photo], clear central bay ±40 m with its head 2 m higher [obs, tentative]; fritted side bays; mullions on the 20-ft grid, transoms 2.2 m [obs, low]; upper glazing behind the exposed west truss (photo i3) |
| `hall_lettering` | obs | "SAN FRANCISCO INTERNATIONAL", 66 × 2.8 m at 25.8–28.6 m (BI-02 box); font inf (Blender built-in) |
| `hall_canopy`, `hall_hangers`, `hall_curb` | inf / obs | canopy L3 + 5 m, 5 m deep [inf; exists pub]; hangers / posts at `HANGER_U` (40-ft grid + ±30 / ±90 ft) [obs photo i4]; 7-m curb at L3 [inf] |
| `hall_end_walls`, `hall_east_clerestory`, `hall_podium` | inf / unk | end curtain walls at ±107.4 m up to the roof (outline unk); east clerestory 1 m inside the east eave; levels 1–2 as faces only |
| `itb_core` | unk | SFO Museum ITB outline − piers − hall: east block and north / south bars, **17.9 m placeholder** (no source) |
| `ba_a_body`, `ba_g_body` | obs | SFO Museum outlines at 17.9 / 17.0 m [obs]; 1 m parapet [inf]; gate-room glazing 5.2–17.2 m (a2) centred on the bridge attach points, 24 m wide [inf] |
| `ba_a_pods`, `ba_g_pods`, `ba_g_box` | obs (low) | `itb_pods.json` rings (relief-corrected NAIP traces) to tops 23.6 / 23.6 / 23.3 and 22.4 / 22.2 / 23.2 m; the G3 end box to 32.0 m with a window band and antennas (schematic, photo d2; function inf) |

**Two deliberate choices where the sheets are inferred and disagree** (both in the manifest):
1. West truss bottom chord: BI-02 draws it level with the glass head (30.8) from the notch to the tip; BI-03 tapers the
   truss depth to 1.5 m at the notch. Photos i3 / i4 show the west chord sweeping up from the glass head towards the notch
   (~3.5–4 m above it at |u| 30 on i4), so the model takes the higher of the two lines: up to 2.6 m above BI-02's line
   between the notch and the inner column line, identical elsewhere.
2. Centre section: BI-03 draws the bowstring chord as an unknown placeholder; the photos show a lens-shaped truss, so the
   chord sags from the deck at the notches to the clear bay's head at u = 0.

### Budget, textures, AO

| LOD | switch | triangles | draw calls | content |
|---|---|---|---|---|
| 0 | < 450 m | 59,497 | 50 | everything; trusses 8-sided chords with webs (36k tris), mullions, lettering, antennas |
| 1 | 450–1600 m | 28,547 | 46 | shared shells (same meshes / atlas as LOD0); 4-sided trusses, lighter columns and hangers |
| 2 | > 1600 m | 3,728 | 19 | one joined node (8-m roof stations, simplified outlines), own 512-px atlas; also `itb_lod2.glb` |

Textures (PNG, embedded): AO atlas A 2048² (2.06 MB; LOD0 / LOD1 shells, 48 spp, 10-m rays, ground plane, white outside
the islands so mip levels do not bleed black), AO atlas B 512² (0.16 MB); tiling normal maps 512² (membrane, panels,
curtain caps; 2–28 kB); base colours 256–512² (frit, three curtain-wall glasses). Glass is coated (IOR 1.9 → F0 0.096:
`KHR_materials_ior`, which Blender's exporter writes only together with `KHR_materials_specular`, here specularFactor
0.998; the IOR is also in the material extras) and opaque; `glass_hall` carries the brightness of the lit hall behind the
clear bay. Materials are single-sided (`doubleSided` false): every face is wound outwards, checked by the back-face QA
render (0 red pixels in 5 views × 3 LODs, after capping the open truss-chord ends). No TANGENT attribute (saves 1.3 MB; the validator's
generated-tangent warning is accepted). Khronos glTF-Validator 2.0.0-dev.3.10: **0 errors** on both files.

### Verification (verify_itb.py: 92 checks, 0 failed; tolerance 0.5 m or 2 %)

- Placement exact; roof extent 252.872 × 65.397 m = the drawing; corners within 0.001 m of `roof.corners_obs`.
- Roof top vs `roof_line(u)` at all 4,380 top vertices: max 0.000 m (the mesh is sampled on the function). At the named
  stations: crown 40.10, notch 35.79 (station 0.5 m off the notch), hump 40.07, |u| 100 36.33 (36.40), tip 34.40.
- Rendered silhouette (orthographic west render, 0.28 m/px) vs `roof_line`: wings max 0.21 m, mean −0.02 m; centre 0.15 m.
- Tip bands 18.75 / 15.75 m at 1.6 / 3.6 m; strips on the truss lines (0.00 m); lenses: length, width, centre within
  0.06 m, planform within 0.02 m of `lens_poly`.
- Trusses: bottom chords over the supports within 0.001 m of BI-03 (west: of the chosen max line); 20 columns at
  ±57.9 / ±82.3 m (0.02 m); west column line v −28.26 (−28.27); 16 canopy posts / hangers within 0.17 m of `HANGER_U`.
- West wall v −25.768, foot 11.5, head 30.8, central head 32.8, ±40 m bay, 214.88 m long, glazed area 4,281.3 m² = the
  drawn outline (this check was added after the back-face QA found the entrance band built as triangles - fixed);
  canopy 16.5 / 5.0 m; lettering 66.0 × 25.8–28.6 m.
- Piers 17.9 / 17.0 m; footprints = the SFO Museum outlines (area difference 0.001 m², 0 m² outside); all six pod tops and
  the box top (32.0) exact; pod plans = the NAIP traces (none needed clipping).
- **Plausibility.** The airside footprint of every LOD lies inside the SFO Museum terminal / boarding-area outlines that
  `tools/stands/check_stands.py` tests all stands and bridges against (0 m² outside), so its results carry over: the nearest
  A / G stand envelope (app planforms, all accepted types) is 5.35 m away (G7; criterion ≥ 2.0 m); no SFO Museum taxiway
  polygon is touched; the roof trusses clear the core block under the tips by 12.65 m. **Pre-existing contact, not
  introduced by the asset:** 17 rotundas that stand directly at a pier facade (no fixed walkway) overlap that outline by
  0.33–1.84 m in `data/sfo_stands.json` (A9 1.84, G9 1.75, A10 1.68 ...); the outline accuracy is ±5 m
  (`sfo_buildings.json footprint_accuracy`). The list is in the manifest for the bridges work.

### Renders and self-review (out/buildings3d/, local; comparison sheets hold photo pixels and stay local)

| View | Compared with | Reading |
|---|---|---|
| `itb_west.png`, `itb_cmp_west.png` | BI-02 V1 lines drawn over the render | roof line, truss chord, glass head, canopy, L3, column and hanger stations fall on the drawing |
| `itb_i4.png`, `itb_cmp_i4.png` | photo i4 | two wings and the crown, exposed trusses, column fans, fritted side bays, clear central bay with the lettering, canopy line: reads as the building. The photo's crown reads darker (lens glass seen at grazing angle); the departures roadway in front is not part of this asset |
| `itb_i3.png`, `itb_cmp_i3.png` | photo i3 | column + fan, exposed truss over the head, dark soffit with outriggers, canopy with hangers, the centre arch at the notch. Photo columns look thicker (~2 m) than the drawn 1.5 m: kept to the drawing |
| `itb_baa.png` | photo a2, BI-04 V2 | flat-topped pods on the pier roof, glazed gate-room bays with a mullion grid, dark apron level |
| `itb_bag.png` | photo d2, BI-04 V1 | the pod-3 end box with its window band and antennas |
| `itb_plan.png` | BI-01 V2 / NAIP | north-up plan: tip bands, strips, lenses, core and bars as imaged |
| `itb_ao_*.png` | — | AO: soffit near the walls, under the canopy, curb and pod bases; no leaks seen |
| `itb_bf_*.png` | — | back-face QA (i4, i3, baa, east, top × LOD0-2): 0 red pixels |

### Open items (also in the manifest's `unknown` / `conflicts`)
- The ITB core block height (17.9 m placeholder) and its facades; the AirTrain stations at ITB level 4 inside the bars
  and the guideway are not modelled here (landside group / integration).
- The 2024–26 roof (new membrane, ~1.4 MW PV) is not imaged; the asset shows the NAIP 2024 roof.
- Conflicts carried from the sheets: 860 ft vs 252.9 m length; the 210-ft hall width; BA-A pod 1 NAIP 23.6 vs DOF 25.91 m.
- LOD1 has 46 draw calls (shared shells, one primitive per material per node): merge per material at load time on phones.
- Integration (js/three loader, replacing `terminals.js` greatHall / pier extrusions) is not part of this step.

<!-- tower:begin (written by tools/blender/build_tower.py) -->
## Control tower (ATCT 2016) and base building: `data/buildings3d/tower.glb`

```bash
python3 tools/blender/build_tower.py --render --audit   # both families, AO bake, export, manifest, verification, renders (~16 min, 4 CPUs)
python3 tools/blender/tower3d_verify.py data/buildings3d/tower.glb   # re-measure an exported file
```

**Source of the geometry.** Everything is generated from the approved sheets BT-01..03: `tools/blender/tower_geom.py` imports `tools/buildings/draw_tower.py` (and through it `spec_tower.json` and the SFO Museum footprint) and uses its functions and constants (`shaft_outline`, `cab_outline`, `plinth`, `SHOULDER`, slot / mast / pole bearings, `WING_TIP`, `RIB_BRG`, `IBF_AIR_BAND`, `IBF_CW`, rows / twist of the cladding). Nothing is typed in twice. The one new measurement is the roof-garden outline (NAIP 2024 vegetated pixels, lean-corrected). No imagery is used as a texture.

**Height family.** The sheets draw two self-consistent families and prefer neither (buildings_tower.md 12.3). Both are built: `tower.glb` = F1 (D 15.2, rim 67.36 = 221 ft), `tower_f2.glb` = F2 (D 14.5, rim 64.0, 221 ft at the masts). F1 is the default file only because CTBUH classifies 221 ft as a height without antennae (not a survey). `manifest.json#tower.family_decided = false`.

**Placement.** Root node `tower` at world (-740.5, GROUND_Y, 324.5) = the inferred shaft axis at grade (x east, y up, z south, js/geo.js). Cab-floor / eye heights and the other anchors are in the root extras and the manifest (F1: floor 60.6 m, eye 62.2 m, glass 61.45-64.533 m, rim 67.36 m, highest mast 72.06 m).

| LOD | Use (suggested camera distance) | Triangles F1 / F2 | AO atlas (TEXCOORD_1) | Content |
|---|---|---|---|---|
| LOD0 | < 350 m (close-up, tower view) | 33,631 / 32,564 | 2048 px | 272 helical columns, recessed slots with glazed panes, seams, 24 cab panes + joints, ribbon mullions, 15 whips + 9 poles + red light, base-building mullions, coping, rails, rooftop unit, sunken garden |
| LOD1 | 350-1200 m | 9,956 / 9,666 | 1024 px | 136 columns, flat slots, 24-facet cab, 15 whips, plain base building with parapet |
| LOD2 | > 1200 m; phone (`tower_lod2.glb`) | 2,382 / 2,248 | 512 px | 68 columns, flat slots, 12-facet cab, no masts, base building as a box |

Files: `tower.glb` 3.47 MB, `tower_f2.glb` 3.37 MB, `tower_lod2.glb` 0.23 MB (PNG textures; KTX2 / meshopt later with `tools/engine/glb_compress.mjs`). Materials are PBR constants (our choices for the published "SFO Silver" ACM, glass, panels; `extras.src` on every material); detail normal tiles on TEXCOORD_0 (`tools/blender/tower_tex.py`: panel joints, louvres, base-building panels, mip-mapped: no moire); sun-independent AO baked by Cycles (48 samples, 8 m rays, ground plane as occluder). Glass of the cab is alpha-blended and double-sided; every other surface is single-sided and wound outwards (back-face audit renders: 0 back-face pixels in 6 views per LOD).

**Verification** (`out/buildings3d/tower_verify.json`, measured on the exported GLB against the sheet functions):
- F1: 109/109 checks within tolerance; tris {0: 33631, 1: 9956, 2: 2382}; plausibility clear of aircraft envelopes, bridges and taxilanes; the app's T2 hall / BA-D walkway parts overlap the base-building footprint (integration: cut them)
- F2: 109/109 checks within tolerance; tris {0: 32564, 1: 9666, 2: 2248}; plausibility clear of aircraft envelopes, bridges and taxilanes; the app's T2 hall / BA-D walkway parts overlap the base-building footprint (integration: cut them)
- largest deviation of a length: 0.047 m (tolerance 0.5 m / 2 %); 0 failures.
- Khronos glTF-Validator F1: 0 errors, 0 warnings, 32 infos (info:UNUSED_OBJECT); F2: 0 errors, 0 warnings, 32 infos (info:UNUSED_OBJECT)
- plausibility: clear of aircraft envelopes, bridges and taxilanes; the app's T2 hall / BA-D walkway parts overlap the base-building footprint (integration: cut them); nearest aircraft envelope 15.6 m (C3), bridge 37.2 m, taxiway centreline 85.3 m.

**Integration (for the app owner).** Parts of the app's `data/sfo_buildings.json` overlap the asset below 20 m: "Boarding Area D walkway" (walkway, 10.5 m) 66.3 m2; "Terminal 2" (hall, 19.0 m) 1123.3 m2. The base building would be swallowed by the T2 hall box. Cut the footprint (`manifest.json#tower.integration.exclusion_footprint_world`) out of those parts, replace `buildTower()`, and put the tower camera at `anchors.cab_eye_h` (the app uses GROUND_Y + 62).

**Renders** (Cycles CPU, 64 samples + OIDN, AgX; ours): `out/buildings3d/tower_A.png`, `tower_B.png` (the BT-02 elevations, orthographic; `tower_overlay_A/B.png` carry the sheet outlines in red), `tower_t2.png`, `tower_t3.png`, `tower_t4.png` (camera-matched to the reference photos t2 / t3 / t4, Famartin 2025, CC BY-SA 4.0; side-by-side comparisons `tower_compare_*.jpg` stay local).

**Observed vs inferred.** Per dimension in `manifest.json#tower.dimensions`; lists `inferred`, `unknown`, `not_modelled`, `conflicts` there. Node extras carry `src`, the spec keys and per-feature tags.

**Open (for the owner).**
- The height family (F1 / F2).
- NE blade tip: drawn at deck + 1.2 (61.7 m F1, obs low). In the t3 / t4 comparisons the model's tip stands ~2-3 m higher than the photographed tip (perspective-corrected estimate from t3: the prow top is near the flare corner, ~58-59 m). Not changed: the sheet is the reference.
- t2 camera match: with the rim registered, the base-building parapet renders ~90 px (~2.9 m) higher than in the photo; the camera height (11.5 m) and focal length are estimates (no EXIF here), so this is a camera-model check only, but the parapet / roof station (rim - 3.46 D - 0.7) comes from the same photo.
- Slot 345.5 deg: its top corner falls on the NE blade root; clipped 0.3 m clear of the crease (the sheet lets the blade cover it).
<!-- tower:end -->

<!-- landside:begin (tools/blender/build_landside.py; numbers from out/buildings3d/landside_verify.json) -->
## Landside: garages, AirTrain, Grand Hyatt, RCC, CAC, Superbay, United MOC (key `landside`, 5 Nov 2026)

```bash
flock out/.heavy.lock python3 tools/blender/build_landside.py     # ~2 min: geometry, textures, NAIP colours, 3 AO bakes, export, verify, manifest
python3 tools/blender/verify_landside.py                            # numbers only (no bpy) -> out/buildings3d/landside_verify.json
flock out/.heavy.lock python3 tools/blender/render_landside.py --views gar_a,hyatt,superbay,l4,l1,l5,overview
flock out/.heavy.lock python3 tools/blender/render_landside.py --views a2 --itb          # with itb.glb as context
flock out/.heavy.lock python3 tools/blender/render_landside.py --views gar_a,l1,l5 --backface   # red = inward faces
python3 tools/blender/landside_manifest.py                          # merge the render list into manifest.json#landside
```

| File | Role |
|---|---|
| `tools/blender/landside_geom.py` | Buildings (numpy / shapely). Imports `draw_landside.py` / `draw_data.py`: GAR / ggeom (Garages A / G), SB_* (Superbay), GH_* + the l4 fractions (Hyatt), RCC_N / RCC_S / RCC_TOWER_D, the BL-03 level placeholders |
| `tools/blender/landside_airtrain.py` | Guideway on the SFO Museum polygon, level field, piers, guide beams, stations, the RCC station tower |
| `tools/blender/landside_cars.py` | Parked cars on the deck stall grids (count / axis from NAIP), two low-poly shapes |
| `tools/blender/landside_mesh.py`, `landside_tex.py` | Mesh primitives (MB, facade / cap / tube, `face_dir`); procedural tiles (normal + base colour) |
| `tools/blender/build_landside.py`, `landside_manifest.py` | bpy build, NAIP colour sampling, AO bakes, export, manifest entry |
| `tools/blender/verify_landside.py`, `render_landside.py` | 140 checks on the exported glb; Cycles references with the sheet lines drawn over them; back-face QA |
| `data/buildings3d/landside.glb` (14.9 MB), `landside_lod2.glb` (1.26 MB) | The asset; the LOD2 subtrees alone (far / phone tier) |

**Layout.** Root `landside` at world (0, 3.0, 0); one child per building / AirTrain tile at its own origin (`origin_world_xz`
in the node extras), each with `LOD0_*` / `LOD1_*` / `LOD2_*` children: switch 0 / 450 / 1500 m **from that building node**
(the group spans 2.4 x 2.8 km, so one root LOD would not work). LOD0 / LOD1 share the shell meshes and their AO atlas
(A 2048 px: the six parking structures; B 2048 px: the other buildings and the AirTrain); LOD2 = one joined node per building
with atlas C (1024 px). Parked cars: 1,699 instances, one node per deck x shape x colour with `EXT_mesh_gpu_instancing`
(one material, paint / glass / skirt in COLOR_0), under LOD0 and LOD1.

| LOD | triangles (non-instanced) | instanced car triangles | draw calls (all buildings) |
|---|---|---|---|
| 0 | 116.8k | 91.6k | 286 (12 car groups per deck) |
| 1 | 63.0k | 64.5k | 258 |
| 2 | 8.8k | none | 74 (`landside_lod2.glb`: 1.26 MB) |

### What is modelled, and from what (per-dimension tags in the node extras and `manifest.json#landside.buildings`)

| Building | Plan | Heights | Facade / detail |
|---|---|---|---|
| Central garage | SFO Museum outline with the 58.9-m void [obs]; the AirTrain ring and T1 / T2 / T3 station polygons cut out above Level 5, garage structure under them to the guideway deck | parapet 81 ft = 24.69 [pub, definition unk]; deck 23.62 [inf]; levels = equal fifths, Level 5 = 19.75 [unk, BL-03] | open levels (3-m dark recess, spandrels, piers 9 m [inf]); roof light poles at the two DOF points 30.8 / 33.2 [pub]; 300 cars [obs visual] |
| Garages A / G | outline up to the body end Lb 150.8 / 149.8 [obs]; drum = outline arc (R 16.2 / 15.2, fit residual < 0.6) [obs]; Garage A: the guideway strips inside the body, portals at both faces; Garage G: guideway cut out | parapet = drum ring 39.6 / 37.6 [unk: the deck is not measured]; core cylinder D 13 to +4 m [obs / unk]; Garage A rooftop box to +3.5 [obs / unk]; nine levels as equal ninths [unk] | precast spandrels + perforated screens on every face [obs spec, l1, a2]; banded drum with the top openings; Garage A station block: solid precast with dark slots (photo l1); 100 / 77 cars [obs NAIP] |
| LTP 1 / LTP 2 | outlines [obs] | LTP 1 parapet 16.5 [obs shadow], towers to the DOF tops 26.2 / 27.7 [pub, form inf]; LTP 2 deck 60 ft [inf], levels 12 ft [pub], PV canopies at deck + 3.5 [unk] | precast / exposed frame; PV rows over the stall modules [pub, layout inf]; 276 / 318 cars |
| Rental Car Center | outline [obs]; west wall = the outline between RCC_N and RCC_S | roof outline 54 ft [pub DOF]; 59-ft element at its DOF point [pub, form inf] | west wall per photo l5: board-formed concrete, ribbon windows at the platform, band, canted louvre screen (1.2 m lean [inf]); 626 cars in nose-to-tail lanes [obs NAIP] |
| Grand Hyatt | outline; the podium zone (17 m east of the slab along the south part, from the relief-corrected NAIP roof [obs, approx]) | 44 m [inf, 13.2 pitches]; podium 10.67, colonnade 14.0 [inf]; penthouse +1.4 / +0.65 pitches [obs l4] | l4 face fractions (podium 0.47, colonnade 0.02-0.10, end bay, framed bay 0.615-0.842, masts, sign pier) |
| CAC | outline | roof 60 ft, parapet 64 ft [inf] | window band per 15-ft floor [inf]; louvre fins on the S / W faces [pub] |
| Superbay | spine a -14..+18, roof a -80.5..+84.5, t +-69 [obs NAIP]; walls on the outline, 1 m inside the roof | spine 41.15 [pub DOF], root 39.65, tips 27.0 [inf], folds 1.5 [unk], door head 24.0 [unk] | 8 folded bays per side, hipped spine ends (plan BL-02), 2 x 67-m door bays per long face (8 leaves) [inf], red light at the DOF point |
| United MOC | imaged roof corners shifted west by 0.315 x 37.1 m (North-Field lean) [inf]; barrel hangars likewise | parts 35.7 / 40.2 / 35.4 at the DOF points [pub, extents inf]; barrel eave 14 / crown 24 [unk placeholders] | corrugated walls; no doors (not verified) |
| AirTrain | SFO Museum polygon (7.8 km of centreline), clipped inside the ITB outline and the Garage A body | deck top from station anchors (see below), harmonic interpolation, max grade 3.9 % | trough walls 1.1 m, guide beams, 99 single-column T-piers every 30 m (not inside buildings), 9 stations (glazed enclosures / curved canopies), RCC perforated tower D 6.5 to the DOF TANK 18.3 [pub, identity inf] |

**Station levels (deck top).** T1 / T2 / T3 19.75 (BL-03 Level 5 placeholder [unk]); ITB A / G 16.5 (ITB Level 4 [unk], keeps the
guideway inside the itb.glb core block); Garages A / G and the Hyatt station 19.75 [inf]; RCC 5.8 [inf, photo l5]; LTP 15.24
("50 ft above a public roadway" [pub]); West Field Road interpolated (11.3). **Two deliberate deviations from the BL-03
placeholders** (both [unk] on the sheets; listed in the manifest): the Garage A / G stations at 19.75 instead of 6/8 of the drum
ring (29.7 / 28.2 m) - the Grand Hyatt station is 40 m along the same track, so the sheet value would need a > 20 % grade - and
inside the sheet's own [inf] range 18.3-21.0 m; the RCC platform at 5.8 m (photo l5: ribbon windows at the platform, band and
louvres above to the 54-ft roof; the tower ~2 D above the platform) instead of 12.35 m. Also: the Superbay spine-end facets fall
to the cantilever-root level (BL-02 plan) rather than to the tip level (BL-03 V4 line, which would leave an 11-m step).

### Verification (verify_landside.py on the exported glb: 140 checks, 0 failed; tolerance 0.5 m or 2 %)
- Placement of all 23 nodes exact (0.01 m); root at GROUND_Y.
- Heights = the sheet values to < 0.01 m: CG 24.69 / deck 23.62 / poles 33.2, 30.8; Garages A / G ring 39.6 / 37.6, cores 43.6 /
  41.6, box 43.1; LTP 1 16.5, towers 27.7 / 26.2; LTP 2 18.29 / 19.36 / PV 21.79; RCC 16.46, 59-ft element 17.98; Hyatt 44.0,
  podium 10.67, penthouse 48.67; CAC 18.29 / 19.51; Superbay spine 41.15, root 39.65, tips 27.0 / 28.5, door head 24.0; MOC
  40.2 / 35.7 / 35.4; RCC tower 18.3, D 6.50.
- Plans: CG, LTP 1 / 2, RCC, CAC roof footprints = the outlines (0 m2 outside / missing; RCC: the canted louvres overhang the
  west wall by 1.1 m = 206 m2, by design); Hyatt 5.5 m2 outside (parapet buffering); drum fits R 16.21 / 15.17 (sheet 16.2 / 15.2),
  centres within 0.03 m; body ends 151.1 / 149.8 (150.8 / 149.8); rooftop box u 52.3-76.9 (exact); CG void 58.7 m (58.9);
  Superbay roof a -80.5 / +84.5, 138.0 m along the spine; Hyatt podium to f 0.470.
- AirTrain: deck inside the SFO Museum polygon (0 m2 outside); every anchored platform / track at its level within 0.02 m;
  99.9th-percentile grade between deck vertices 2-6 m apart 3.9 %.
- Cars: per deck = NAIP density x deck area (CG: the visual 300); minimum centre spacing 2.39 m (2.6-m stalls), all on the deck.
- Render silhouettes (orthographic, alpha pass) vs the sheet lines: Hyatt parapet max 0.04 m (0.135 m/px); Superbay spine
  max 0.07 m (0.177 m/px); Garage A ring max 0.73 m (0.333 m/px): SUVs on the deck stand 0.7 m above the 1.07-m guard, the ring
  itself is exact in the verification.
- Back-face QA (red = an inward face): gar_a, superbay, overview 0 px; a2 6 px; l5 537 px (0.08 %), Hyatt 610 px (0.12 %: the
  colonnade recess at the curved south end), l1 2,085 px (0.3 %: inside the Garage A portal openings) - small residuals, left
  open.
- **Plausibility**: nearest stand envelope (108 stands, app planforms) 28.9 m (A4, the guideway at the ITB); nearest bridge
  walkway / rotunda 56.0 m; no SFO Museum taxiway polygon inside any footprint (nearest 204 m, RCC; Superbay / MOC 212 m).
  Integration: the MOC has no SFO Museum outline, so the app's ground physics does not know it - add its footprint
  (`manifest.json#landside.buildings.united_moc`) to the obstacle list.
- Khronos glTF-Validator 2.0.0-dev.3.10: 0 errors (both files); warnings only MESH_PRIMITIVE_GENERATED_TANGENT_SPACE (no
  TANGENT attribute, accepted as for the ITB).
- Thin see-through plates (louvres, station roofs, coping) and the dark garage interiors are `doubleSided`; everything else is
  single-sided and wound outwards (`landside_mesh.MB.face_dir` where the winding is not implied by a ring).

### Renders (out/buildings3d/, local; comparison sheets with photo pixels stay local)
`landside_gar_a.png` / `landside_cmp_gar_a.png` (BL-03 row 1 lines over the orthographic SSE face), `landside_hyatt.png` /
`_cmp_hyatt` (BL-03 row 2, l4 fractions), `landside_superbay.png` / `_cmp_superbay` (BL-03 row 4 door face), `landside_l1`,
`landside_l4`, `landside_l5`, `landside_a2` (camera-matched to the photos; `_cmp_*` side by side), `landside_overview.png`.
Self-review: a2 reproduces the layout (Garage G with its station canopy along the NNW face, Garage A behind with the rooftop box
and core, the Hyatt beyond, the guideway curves); l1 the station block with its slots and portals, the curved NE corner with
screens; l5 the board-formed west wall, ribbon windows, canted louvres and the perforated tower; l4 the podium, colonnade,
penthouse steps, masts and framed bay.

### Open items (also in the manifest's `unknown` / `conflicts` / `deviations_from_sheets`)
- Garage A / G roof decks (drawn at the drum ring). Photo l1 shows the Garage A station block rising only ~9 m above the
  guideway, with the curved garage wall behind it higher: consistent with a lower block or a lower deck at the east end - not
  changed (BL-03 is the reference; the deck is [unk]).
- Station enclosure / canopy heights, the stair / elevator towers of the terminal-area stations, the Hyatt bridge, the LTP links.
- The RCC "66 ft", the DOF 10.4-m point inside the RCC outline (conflict), the MOC section extents and barrel-vault heights,
  the Superbay fold amplitude and door leaves, the CAC cladding: placeholders / inferred, as tagged.
- Guideway over the T1 / T2 / T3 terminal outlines (skybridge parts at Level 3 below it): check against the domestic asset.
- KTX2 / meshopt (tools/engine/glb_compress.mjs) and the js/three loader are later steps.
<!-- landside:end -->

<!-- domestic:begin (tools/blender/build_domestic.py; numbers from out/buildings3d/domestic_verify.json, 2026-11-05) -->
## Domestic terminals: T1 Center, T2, T3 West / East and Boarding Areas B-F (key `domestic`, 5 Nov 2026)

```bash
flock out/.heavy.lock python3 tools/blender/build_domestic.py --final   # ~70 s: geometry, textures, AO bake (2 x 2048 + 1024), export, verification, manifest
python3 tools/blender/build_domestic.py --no-bake                       # quick WIP build -> out/buildings3d/wip/ (white occlusion)
python3 tools/blender/verify_domestic.py [glb]                          # 59 checks, reads the glb back (no bpy) -> out/buildings3d/domestic_verify.json
flock out/.heavy.lock python3 tools/blender/render_domestic.py --views a1,d1,bab,plan,bclose,eclose     # Cycles references, ~2 min at 48 spp
flock out/.heavy.lock python3 tools/blender/render_domestic.py --qa backface --views a1,bclose,eclose,d1,plan [--lod 1|2]   # back faces red
python3 tools/blender/dom_pv.py                                         # (re)measure the PV rack blocks on NAIP 2024 -> tools/blender/dom_pv.json
```

| File | Role |
|---|---|
| `tools/blender/dom_geom.py` | Geometry (numpy / shapely, no bpy). Imports `tools/buildings/draw_domestic.py` / `draw_data.py` (the sheets' functions and constants, not copies): footprints from the SFO Museum level-2 outlines, measured roof edges, BA-B band, BA-E section, BA-F hub / lantern / monitor, BA-D drums, T1 / T3 landside, bridge doors |
| `tools/blender/dom_mesh.py` | Mesh builder + extrusion / cap / box / tube primitives (faces wound outwards) |
| `tools/blender/dom_tex.py` | Our procedural tiles: normal maps (membrane laps, panel joints, curtain caps, corrugation, PV frames), curtain / frit / PV base colours |
| `tools/blender/dom_pv.py`, `dom_pv.json` | PV rack blocks measured on NAIP 2024 (extents only; numbers, never a texture) |
| `tools/blender/build_domestic.py` | bpy build, NAIP roof-colour sampling, the T1 sign, AO bake, glTF export (WIP to `out/buildings3d/wip/`, `--final` copies to `data/`), manifest |
| `tools/blender/dom_manifest.py` | Manifest entry (per-dimension tags, inferred / unknown / not modelled / conflicts, budgets, renders) |
| `tools/blender/verify_domestic.py` | 59 checks against the sheets and the plausibility rules, measured on the exported mesh (top-surface probe) |
| `tools/blender/render_domestic.py` | Cycles references of the exported glb (+ tower / ITB assets for context), AO and back-face QA modes |
| `data/buildings3d/domestic.glb` (9.27 MB), `domestic_lod2.glb` (1.63 MB) | The asset; the LOD2 subtree alone for the far / phone tier |

**Placement.** Root `domestic` at world (−896.5, 3.0, 336.5) (centre of the complex bbox, GROUND_Y). LOD0 / LOD1 hold one node
per building and kind (`L<k>_<bld>_shell / _detail / _pv`, `extras.building` in T1, BA_B, BA_C, T2, BA_D, T3W, T3E, BA_E, BA_F),
each recentred on its own plan bbox: the complex spans ~1.3 km, so **choose the LOD per building** from the camera distance to
that node (switch 380 / 1300 m). LOD2 is one joined node.

### What is modelled, and from what (tags per dimension in `manifest.json#domestic.dimensions`)

| Part | Source | Notes |
|---|---|---|
| Pier / hall footprints | obs | SFO Museum level-2 outlines; bridge-head fingers and the fixed-walkway strips at the BA-B tip are left to the app's bridges; the tower base building and the ITB are excluded (0 m²) |
| Roof edges | obs | measured lean-free lines (`dom_true_edges`): BA-B ESE +2.27 / WNW −1.66 m, BA-D +2.40 / −1.36, BA-F +1.83 / −1.15 (see conflicts), BA-E WNW −2.0; continuous along each side (gaps at the finger roots closed, limited to the offset band) |
| Heights (roof edge = coping top) | obs / inf / unk | BA-B 13.14 / band 19.04, BA-C 7.20, BA-D 8.49, BA-E 12.85 / flanks 9.85, BA-F 10.49, T3W parapet 16.76, T3E 14.48, penthouse 21.34; **T1 17.88 and T2 16.88 are placeholders [unk]** (curb 4.88 [unk] + the BD-03 heights) |
| BA-B | obs / inf / unk | raised clerestory band s −391.0 / −423.4, t −1236..−946 (glazed both sides, low-E); 3 planted roof wells (depth 3 m [unk]), 2 bridges, 2 skylight grids, PV fields (NAIP); electrochromic gate glazing [pub] |
| BA-E | obs / inf | raised PV plate 12.85 with its edge 1.5 m over the recessed clerestory, flanks 4.4 m at 9.85; NEW: the tip end bay (8 m) with the full-height glazed end wall recessed 1.5 m under the plate (photo a1) [inf] |
| BA-F | obs / inf / unk | arms + octagonal hub on the outline; eccentric lantern 19.4 m at its 4.6-m rise bound [unk]; NW-arm monitor +2.5 m [unk] |
| BA-D | obs / inf | head with two drums D 19.2 m to 13.19 m [inf top]; linear skylights; ESE overhang notched at the doors (roof soffit 7.69 m < walkway head 8.4 m) |
| T1 Center | pub / obs / inf / unk | landside face on the measured roof edge (trimmed curb line − 4.0 m); clear glass under a 4.0-m glass canopy (brackets), two-tier green fritted wall with dark irregular mullions and the tier transom (photo d1), sign "Harvey Milk Terminal / Terminal 1" with the circled 1 [obs text, size / font inf]; PV fan (NAIP); 3 skylights |
| T3 | pub / inf | T3W airside window stack 10 + 2 + 10 ft above L3 [pub]; T3W landside ACM / fritted window wall / spandrel [pub materials, proportions inf]; T3E grey-frit glass / platinum panels; T3E penthouse (corrugated, accent bands) |
| Facades elsewhere | inf / unk | service band 0–4.6 m, dark spandrel, concourse glazing from 5.4–5.6 m (the bridge floor), panel above; mullion fins every 1.5 m (LOD0) |
| Bridge attachment | inf | at all 75 attach points of `data/sfo_stands.json` (B–F): a door surround (jambs + head around the 2.6 × 3.0 m walkway section) and a dark leaf; 63 vestibules (max 2.6 m) from the facade to the app's walkway start; 23 bulkheads where the roof edge is below the walkway head (BA-C / BA-D) |
| Elevated sky-bridge / connector parts | unk | the app's convention 6.0–10.5 m (kept so the app's walkways and bridges stay consistent) |

### Budget, textures, AO

| LOD | switch | triangles | draw calls | content |
|---|---|---|---|---|
| 0 | < 380 m | 69,757 | 115 | everything: mullion fins (~48k tris), door surrounds, PV rack boxes, canopy brackets, sign |
| 1 | 380–1300 m | 21,501 | 91 | the LOD0 shell meshes and atlases; PV tops only; no fins / frames |
| 2 | > 1300 m | 11,725 | 16 | one joined node, simplified outlines (1 m), reduced palette, own 1024 atlas; also `domestic_lod2.glb` |

Textures (PNG, embedded): AO atlases S (T1 / BA-B / BA-C / T2) and N (BA-D / T3 / BA-E / BA-F) 2048² (1.33 / 1.30 MB, 8-bit
greyscale), L2 1024² (0.42 MB); 48 spp, 10-m rays, ground plane, neighbours as occluders, white outside the islands; tiling
normal maps 512² (membrane, panels, curtain, T3W window wall, corrugation, PV) and base colours 512² (4 curtain glasses, grey
frit, green frit, T3W, PV), 1.5–24 kB each. Roofs: NAIP 2024 median per building; the white membranes saturate, so the base colour
is capped at sRGB 215 (aged single-ply reflectance ~0.65–0.70) [inf]. Glass coated (IOR 1.9 → F0 0.096, as the ITB / tower), the
T1 frit uncoated (F0 0.04, rougher: the ceramic frit dominates). Single-sided; no TANGENT. KTX2 / meshopt: later
(`tools/engine/glb_compress.mjs`).

### Verification (verify_domestic.py: 59 checks, 0 failed; tolerance 0.5 m or 2 %)

- Placement exact. Every roof edge (median of 16–302 probes on the top surface 0.12 m inside the roof outline): deviation 0.000 m.
- BA-B (28 stations every 10 m): band edges max 0.05 / 0.10 m; outer roof edges (t < −1150, the stretch of the measured lines and
  the BD-02 typical section) 0.10 / 0.11 m; widths 7.35 / 32.2 / 14.69 / 54.24 m vs 7.3 / 32.4 / 14.7 / 54.3.
- Measured roof-edge lines: BA-B, BA-D, BA-F within 0.15 m at every station; BA-F NE arm 27.15 m vs 27.0 (BD-02).
- BA-E (13 sections): plate 12.85, flanks 9.85, widths 42.8 / 37.0 vs 42.9 / 37.1. BA-F lantern 20.90 vs 21.00 m across the
  corners; BA-D drums r 9.57 vs 9.6.
- T3W window stack L3 10.36 / 13.41 / 14.02 m (0.003 m); T1 fritted tiers 8.88–17.08, canopy soffit 8.88, canopy depth 4.0.
- **Plausibility.** Nearest B–F stand envelope (app planforms, all accepted types) 2.93 m from the 3-D footprint (F12; criterion
  ≥ 2.0); bridge walkways beyond the attachment (app-drawn part, 4.8–8.7 m band) 0.0 m² of contact with the asset (83 bridges);
  SFO Museum taxiways 0 m²; tower base building 0 m²; ITB 0.02 m²; AirTrain guideway 0 m². INFO: the first 1.5 m beyond the
  facade touch the door surrounds / the facade where the stand data meets the outline at an angle (79 bridges, 28 m² total,
  e.g. C9, D14), as in the ITB rotunda contacts.
- Khronos glTF-Validator 2.0.0-dev.3.10: **0 errors** on both files (domestic.glb: 77 warnings MESH_PRIMITIVE_GENERATED_TANGENT_SPACE,
  accepted as for the ITB: no TANGENT attribute by choice; 39 infos UNUSED_OBJECT).
- Neighbouring assets (`verify_domestic.py --neighbours`, LOD0 triangles whose height ranges overlap): landside 0 m², tower
  0 m², ITB 0.77 m² (slivers along the shared T1 / T3W – ITB core boundary, ~1 cm; no shared volume).
- Back-face QA (Cycles, single-sided): 0 red pixels in bclose / d1 / plan (LOD0, LOD1, LOD2); a1 49 px and eclose 85 px: the T1 –
  BA-A connector's walls on the ITB boundary are left to the ITB asset (seen open only when the ITB is not loaded).
- Render check (orthographic BA-B section, `domestic_render_check.json`, 0.1 m/px): band edges −0.13 / +0.17 m, heights +0.13 m
  (pixel); the outer WNW silhouette −1.6 m comes from the tip's end walls (t < −1236), not the typical stretch.

### Renders and self-review (out/buildings3d/, local; comparison sheets hold photo pixels and stay local)

| View | Compared with | Reading |
|---|---|---|
| `domestic_a1.png`, `_cmp_a1` | photo a1 (camera solved from 3 points, 60 m, 36.5 mm) | tower, BA-D head with the drums, T2 behind, BA-E with its PV plate and glazed tip fall where the photo has them; missing: aircraft, bridges, apron, the C3C office building and landside (other assets / not in the sheets) |
| `domestic_d1.png`, `_cmp_d1` | photo d1, BD-03 view 1 | green fritted two-tier wall with dark irregular mullions and the transom, sign with the circled 1, glass canopy, clear glass below: reads as the T1 Center landside; the curb roadway in front is not part of this asset |
| `domestic_bab.png`, `_cmp_bab` | BD-02 view 1 | stepped section: clerestory band 19.04 over the 13.14 outer roof, ESE overhang, door surrounds at the concourse level |
| `domestic_plan.png` | BD-01 / NAIP | PV fan on T1, BA-B wells / PV / skylights, BA-F hub and lantern, T3E penthouse |
| `domestic_bclose.png`, `domestic_eclose.png` | photo a1 detail | BA-B band, PV, skylight grid, electrochromic gate glazing; BA-E plate overhanging the clerestory, the recessed glazed end |

### Open items (also in the manifest's `unknown` / `conflicts`)
- T1 Center and T2 hall heights and the departures-curb height (placeholders); the T3 datum; the BA-B well depth; the BA-F lantern
  and monitor rises; the T3W state (95 % CD massing, without the May 2026 storey).
- **Conflict for the drawings group:** BA-F ESE roof edge — the drawn line is 1.83 m outside the outline along the face (BD-02
  draws 27.0 m between the lines); the spec / README note "on the outline" was measured at the line ends only. The asset follows
  the drawn line.
- BA-D / BA-C roofs below the bridge walkway head (notches / bulkheads); 6 bridges that attach into elevated pod parts (B10, B11,
  B11S, B15, B16, F22) have no door surround.
- Not modelled: courtyard links over the roadways / across the guideway, the curb roadways, the Courtyard 3 Connector building,
  T3W penthouses, roof equipment other than PV / penthouse, interiors.
- Integration (js/three loader replacing the `terminals.js` extrusions of these parts, per-building LOD) is not part of this step.
<!-- domestic:end -->

<!-- integration:begin (tools/blender/b3d_integrate.py, js/three/buildings3d.js; 5 Nov 2026) -->
---------------------------------------------------------------------------------------------------------------------

## Integration into the three.js app (key `integration`, 5 Nov 2026)

```bash
python3 tools/buildings/draw.py                 # 2-D sheets first (38 s, clean: only dates / clip ids changed, BD-01 profile, BX-01)
python3 tools/blender/b3d_integrate.py          # ~1 min: footprints from the GLBs, replacement table, plausibility, manifest key
python3 tools/sat/check.py                      # stands / bridges, now with the 3-D footprints (B3D_FOOTPRINTS=0: outlines only)
node tools/build3/build.mjs                     # vendored three.js bundle, now with GLTFLoader (tools/build3/three-entry.js)
flock out/.heavy.lock env SOFTGL=1 W=960 H=540 OUT=out/buildings3d VIEWS="..." node livetest.mjs tools/blender/b3d_views_job.mjs
```

| File | Role |
|---|---|
| `js/three/buildings3d.js` | Loader: GLTFLoader, per-building LOD switching, node materials with the night hooks, shadows, the swap of the first-pass items, the tower camera |
| `tools/blender/b3d_integrate.py` | Footprints measured on the exported GLBs (every LOD and file), the replacement table, the combined plausibility check, `manifest.json#integration` |
| `data/buildings3d/integration.js` | What the app imports (js/live/world.js): replacement table + tower camera anchor (6 kB) |
| `data/buildings3d/integration.json` | Footprints per asset unit (LOD0 / LOD1) with height ranges and body / overhang tiers, the table with coverages, the plausibility results (every LOD), the physics set |
| `tools/blender/b3d_views_job.mjs` | livetest job: the same views with `?b3d=0` (first-pass) and the assets -> `out/buildings3d/cmp_*.png` |
| hooks | `js/three/renderer3.js` (+5 lines), `js/live/world.js` (+import, +2 items loops), `js/live/airport.js` / `js/live/terminals.js` (optional routing parameter; same geometry, same order), `tools/build3/three-entry.js` (+GLTFLoader), `tools/build3/phone_artifact*` (ships the GLBs), `tools/stands/check_stands.py` and `tools/drawing/common.py` / `audit.py` (use the 3-D footprints) |

**Loading.** `Renderer3._buildStatic` starts `Buildings3D` once the static scene exists; the four groups load one after
another (tower, ITB, domestic, landside: one decode / upload / program compile at a time, `compileAsync` over every LOD
before the group is shown, so a LOD switch later does not stall). Until a group is on screen, or if its file fails, the
first-pass extrusions stay: the scene never has a hole. Tiers: high / medium / ultra load the full files (LOD0-2), the low
tier (phones) the `*_lod2.glb` files (3.6 MB together); `?b3d=0` shows the first-pass buildings only, `?b3d=lod2|full`
forces a set, `?b3dtower=f2` the tower's second height family (manifest `family_decided: false`; F1 stays the default).

**LOD.** As each group's manifest says: a "LOD set" is a node whose children are LOD0 / LOD1 / LOD2 (tower, ITB, domestic:
the root; landside: every building node). LOD2 (one joined mesh with its own small atlas) is shown when the camera is beyond
the LOD2 switch distance from the set's bounding box; nearer, LOD0 or LOD1 per unit: domestic per building
(`extras.building`), ITB per part (the group spans 650 m), tower and each landside building as a whole. Distances are to the
unit's bounding box (the nearest point; a 400-m pier seen from its tip is near), 5 % hysteresis, and the switch distances
(extras `switch_m`) are scaled by the tier's `lod` range relative to the high tier (ultra 2.2x, medium 0.72x).

**Materials, AO, shadows.** The glTF PBR materials are used as exported (MeshStandard / MeshPhysical with
`KHR_materials_ior` / `_specular`), converted to node materials the way three does it internally, so an emission term can be
added. The baked AO (`occlusionTexture`, TEXCOORD_1) is the material's `aoMap` (ambient / IBL term only); GTAO adds the
screen-space contact term on top as for every object. Every opaque mesh casts and receives shadows (CSM); the alpha-blended
cab glass does not cast. Tiling normal / base-colour tiles get the tier's anisotropy.

**Night hooks (for the environment work).** Emission = the material's own + `nightE` (renderer3: night factor x LAMP_M) x
`glow[kind].color` x `glow[kind].k` x a +-15 % variation per 3-m cell, masked to the panes where the glass has a base-colour
tile (frames and frit stay dark). Kinds from the assets' own material names and extras: `hall` (terminal glazing, the
concourse level of objects.js), `office` (hotel, CAC, station-block windows: 55 % of the cells lit), `station` (AirTrain
station glass), `roofglass` (skylights, glazed roof lines: weaker), `cab` (tower cab: dim), `led` (the tower ribbon,
`extras.led`: the objects.js LED wave), `beacon` (red obstruction light, `extras.obstruction_light`). The `glow` entries are
uniforms (`SFO.R.b3d.glow.hall.k.value = ...`): levels inferred, no measured SFO night luminances.

**What the assets replace.** `b3d_integrate.py` measures every asset unit's footprint on the exported meshes (every LOD and
file, plan union of the triangles, vertical faces as 5-cm strips, +0.02 m) and assigns each first-pass app building to the
group that covers it (+2 m: the SFO Museum outlines are +-5 m). Piers, halls and structures go wholly to the group covering
>= 50 % of them; elevated walkways are tested in their own height band (the guideway deck is elevated: a skybridge passing
under or over it is not covered) and are clipped instead: the part is hidden with the asset and the open span outside the
asset's occupancy (- 0.3 m, slivers < 3 m wide dropped) stays as a "rest" item. `js/live/world.js` routes the replaced
geometry into one item per group (`b3d`) and the rests into `b3dRest` items (three.js renderer only); `buildLiveBuildings` /
`buildTerminals` build exactly the same geometry in the same order (the rooftop-plant random sequence is unchanged), only into
different `Geo`s. live.html is unaffected (it draws every item, the rests are not created for it).

| First-pass element (app) | Replaced by | Kept |
|---|---|---|
| `sfo_buildings.json` parts (29) | domestic 15 (T1, T2, T3 halls, BA-B..F, their walkways), ITB 6 (hall + great-hall roof, BA-A, BA-G, 3 walkways), landside 7 (garage / station walkways) | Terminal 3 walkway #26 (outside every asset); 7 walkway spans as rests (T1 / T2 / T3 skybridges to the Central Garage and the AirTrain stations: 35-528 m2 each) |
| terminal-complex ramp-level walls (G..G+5) | per edge where an asset occupies the band within 3 m: 15 runs (domestic, ITB, tower) | the edges along the courtyard links and connectors |
| `sfo_airport.json` structures (36) | landside 30 (garages, RCC, CAC, Hyatt, Superbay, AirTrain stations, guideway slab + columns), ITB 4 (ITB AirTrain stations: inside the ITB core block), tower 1 (`buildTower`) | none |

The app's tower view (`js/live/app.js`: GROUND_Y + 62 over `world.towerPos`) moves to the asset's cab eye (x, z) once
tower.glb is shown (manifest `tower.integration.tower_camera`: eye (-739.0, 65.2, 323.5); GROUND_Y + 62 = 65.0 is 0.2 m
from the F1 eye height, so the height is kept). Inside the cab the alpha-blended glass is hidden (it would darken the whole
view); from outside it is drawn.

**Physical plausibility of the integrated set** (`integration.json#plausibility`; every LOD of every file, unsimplified
footprints):
- Aircraft envelopes (every accepted type at every one of the 108 stands, `tools/stands/geom.py stand_env`, the envelope
  `check_stands.py` tests): **0 conflicts** (overlap > 0.5 m2 or < 2.0 m). Notes (< 3.5 m): F12 2.91 m (SFO Museum outline
  2.81 m), F17 3.15 m (outline 3.38 m: BA-F's measured roof edge, 0.23 m nearer). Next: G7 5.2, F5 5.5, E4 / F9 6.6 m.
- Jet bridges (128, incl. 3 upper deck): docked and stowed tunnel + cab beyond 3 m of the rotunda vs every footprint, fixed
  walkway + rotunda vs other buildings: **0 conflicts**.
- Taxiways: no footprint inside an SFO Museum taxiway polygon; nearest taxiway centreline 27.0 m (BA-F), then 38 m.
- Assets against each other, per 2-m height band on the triangles: largest core overlap 0.6 m2 (ITB hall / guideway tile
  at the ITB, band 16-18 m; below the 2 m2 note threshold); tower / T2, ITB / T1 / T3W: coplanar shared walls only.
- What stays of the first-pass buildings (walkway rests, the kept walkway, kept ramp-level edges) against the assets in
  its own height band: 0 m2.
- `tools/sat/check.py` / `check_bridges.py` (one run; `check_stands.py` now unions the 3-D footprints into the aircraft-
  envelope test, `B3D_FOOTPRINTS=0` for the outlines only): ISSUES 0 before and after, WARNINGS 17 both, APP ISSUES 0; the
  only change is the F17 note (3.4 -> 3.2 m).
- 2-D audit (`tools/drawing/run_all.sh`): `common.py buildings()` now marks the replaced first-pass parts / structures
  `notBuilt`, adds the walkway rests and every asset unit as prisms from `integration.json` (`tiers`: the body standing on
  the ground, grade to top; the overhangs - eaves, canopies, the tower flare, bridge vestibules - binned by the height of
  their undersides; `B3D_FOOTPRINTS=0` reverts); `audit.py` drops the old ITB wing-roof overhang object when the ITB hall is
  replaced. Run on a fresh extraction (`jobs/extract2d.mjs`, 213 s) of the working tree with the other workflows'
  half-done files at HEAD, `audit.py` before / after (through a wrapper that aliases the renamed GSE kinds `belt210` /
  `belt195` / `belt190` / `catering340`: `audit.py` stops on them since the bridges round renamed them - pre-existing,
  for the drawing-system owner): COLLISION 18 -> 21, CLEARANCE 45 -> 45, WARNING 161 -> 142. The 25 building-building
  warnings that go are the first-pass duplicates (stations listed twice, stations inside garages, the tower inside T2). New:
  3 COLLISION (rotunda drums E9 / F8 / F7 against the BA-E / BA-F vestibule prisms, 0.11-0.63 m2): measured on the
  triangles no asset surface lies inside any rotunda drum (deepest < 1 mm; the domestic door surrounds and vestibules meet
  the drums by design), so these are prism-model artefacts; 2 WARNING touching (E3, D10: 5-8 cm); and the CRJ2 the
  snapshot parks at F10 is 1.40 m from the BA-F body: the SFO Museum outline is 1.43 m from it too (the first-pass pier part
  was drawn 3.77 m away, so the old audit missed it): a stands / realtime item, not a change of the building.
- Ground physics (`js/live/ground.js buildingGrid`): not changed. The asset footprints (hangars and the elevated guideway
  excluded, as the app excludes its hangars and rail) add 1,783 m2 to the building mask, all in strips 2-4 m wide along
  the measured roof edges (largest 365 m2); the MOC (no SFO Museum outline) is a hangar block and stays out as the
  Superbay does. `integration.json#physics.rings` holds the set for the realtime owner (tools/live/*.mjs import ground.js
  from repository copies, so the hook belongs to that workflow).

**Bundle and delivery.** The vendored three.js bundle had no glTF loader: `tools/build3/three-entry.js` now also exports
`GLTFLoader` (three r186 addon; it imports `three`, which shares `build/three.core.js` with `three/webgpu`, so its classes
are the renderer's; WebGLRenderer is tree-shaken out). `vendor/three/three.module.js` 1,338,635 -> 1,383,650 B (+45 kB);
a rebuild without the change reproduced the old file byte for byte first. Phone-test artifact (`tools/build3/phone_artifact.sh`):
artifacts serve standard web types only, and the aircraft models already ship as `.wasm` (application/wasm) fetched as bytes,
so the GLBs ship the same way (`data/buildings3d/*.wasm`, `window.SFO_B3D_EXT = '.wasm'`; `B3D=all|lod2|none`, default all
without the tower's F2 file). A test build from the working tree: 218 files, 59.0 MB (the GLBs 36.8 MB; limits: 15 MB per
binary file - landside.glb is 14.87 MB -, 255 files and 64 MB per publish), the app bundle 4.58 MB with GLTFLoader and the
loader in it. `integration.js` is bundled (6 kB); `integration.json` is not shipped.

**GPU memory (found in the first headless run).** GLTFLoader clones a texture for every material that reads it on
TEXCOORD_1 (`assignTexture`: `texCoord > 0 -> texture.clone()`), and the WebGPU / WebGL 2 backends upload every clone as
its own GPU texture: the AO atlases were uploaded once per material, **4,054 MB** of textures in the tower view. The loader
now keeps one Texture per image and sampling (source, channel, colour space, wrap, transform); the unique images of the
four full files decode to ~185 MB with mips (tower 29, ITB 31, domestic 67, landside 58 MB).

**Renders, old vs new** (`tools/blender/b3d_views_job.mjs`, live3.html headless on llvmpipe, 960 x 540, high tier, 8 TRAA
frames per view; `out/buildings3d/cmp_old_*.png` = `?b3d=0`, `cmp_new_*.png` = the assets; served from a snapshot of the working
tree with the other workflows' half-done files at HEAD, `ROOT=`):

| View (camera) | First-pass (`cmp_old_*`) | Assets (`cmp_new_*`) | Draw calls / triangles / textures (old -> new) |
|---|---|---|---|
| `tower` look (-740.5, 35, 324.5) yaw 235 pitch 11 170 m | lathe tower on the old footprint centroid, terminal boxes with plant | Fentress shaft with flare, slots and cab at the asset axis; T2 / BA-D with PV and the BA-B band; Central Garage deck with the guideway | 765 / 4.93 M / 1,088 MB -> 1,855 / 4.79 M / 1,273 MB |
| `itb` look (-1244.6, 15, 365.4) yaw 72.85 pitch 9 620 m (from the ENE: the Central Garage in front) | ring garage with a dense car field, flat ITB roof | the garage's void and Level-5 ring, the ITB wing roof behind, T1 / T3 PV | 791 / 4.81 M -> 2,497 / 4.77 M |
| `pierB` gate B20 110 m | white fascia + glass extrusion, rooftop plant | BA-B dark curtain band and service base; bridges dock as before (unchanged geometry) | 519 / 3.62 M -> 949 / 2.89 M |
| `pierG` gate G7 120 m | glass extrusion; Garage G box behind | BA-G panels with gate-room glazing at the bridge heads, pods, ITB trusses and the guideway | 823 / 5.51 M -> 1,895 / 5.10 M |
| `garage` look (-938, 25, 274) yaw 200 pitch 32 230 m | old deck with ~60 % of the stalls taken | Central Garage deck, NAIP car density, void | 662 / 4.68 M -> 2,004 / 4.85 M |
| `towercam` (app tower view) | inside the old lathe cab | inside the asset cab at its eye: glass hidden, joints and rim visible, dark interior (the asset's placeholder) | 813 / 5.24 M -> 1,831 / 4.97 M |
| `itbwest` look (-1244.6, 18, 365.4) yaw 252.85 pitch 8 520 m (landside, second run) | Garages A / G as boxes with dense cars, flat ITB | Garages A / G with their helix drums and station blocks, the ITB west facade, wing-roof trusses and curb canopy, the guideway | 924 / 5.87 M -> 2,512 / 5.82 M |
| `itbnight` look from the WSW, `light:night` | garages lit through every open bay | ITB west glazing lit (central bay brightest), canopy band, tower LED ribbon; garages dark (below) | 531 / 3.83 M -> 1,165 / 2.94 M |

What the renders show, and what was done about it:
- **No interpenetration** between the assets, the kept first-pass parts, the bridges and the aircraft in any view; the old
  tower, garage cars and AirTrain slab are gone where the assets stand (`b3dLod` per view: 15-36 units at LOD0).
- **Textures +185 MB** (1,088 -> 1,273 MB in every day view, as estimated from the images) after the texture dedupe; the
  first run without it had 4,054 MB.
- **Draw calls x 1.8-3.2** (shadow cascades and the depth / normal pre-pass multiply the meshes): 949-2,497 per frame at
  the high tier. Triangles are flat or lower (the first-pass buildings were one mesh, never culled). Merging the LOD0 /
  LOD1 meshes per material at load time (the ITB manifest suggests it for phones) is the next step if a device is
  draw-call bound.
- **Garages dark at night**: the first-pass garages glowed through painted openings (objects.js id 3); the assets have
  real openings and no night term. Added the `soffit` glow kind (slab undersides, canopy and station ceilings) at the
  first-pass level (0.35 x nightE, colour (0.9, 0.95, 1.0)); the second run (`out/buildings3d/integ/r2/`, `cmp_new_itbnight`
  replaced) shows it does not reach an elevated camera, which sees the decks from above, not the ceilings. Still open for
  the environment work: lighting the inner decks needs the landside asset to split the inner-deck material from the roof
  deck (same material today), then a `setGlow` kind for it.
- **Garage decks read near-white** (display ~214 against ~181 for the first-pass deck): the landside deck base colour is
  the NAIP 2024 DN taken as sRGB albedo (229, 232, 227 -> linear 0.78). On the same scale NAIP gives the apron concrete
  (196, 200, 196) -> linear 0.56, where the app's own airfield bake has 0.32 (renderer3 `concrete mean albedo`), i.e. NAIP
  DN-as-albedo is ~1.75x too bright against the app's ground; the white roof membranes (TPO, real solar reflectance
  ~0.7-0.8) are plausible, the concrete decks (~0.45 after the same factor) are not. Left as built (the colours are the
  landside / domestic / ITB groups' tagged `obs` values) and reported to them: the NAIP-to-albedo factor should be applied
  where NAIP sets a base colour.

**Inferred / open (integration only; each asset's own lists are in its manifest key).**
- Night glow levels and colours (`GLOW_DEF`): inferred from the objects.js concourse / window terms; for the environment work.
- LOD switch distances: the groups' suggestions scaled by the tier; not tuned on a device. Program compile on llvmpipe took
  22 / 46 / 41 / 327 s (tower / ITB / domestic / landside; WebGL 2 without parallel compile blocks the main thread, the
  landside has 97 materials and 160 instanced car nodes); on GPUs with `KHR_parallel_shader_compile` / WebGPU async
  pipelines it is not blocking, but merging the landside materials would cut it (not done here: the assets are the groups').
- The tower camera keeps the app's eye height (GROUND_Y + 62 = 65.0 m world) 0.2 m under the F1 anchor (`cab_eye_h` 62.2 m
  above grade); app.js is another workflow's file. F2 (`?b3dtower=f2`) has a different cab floor: the eye is then
  not re-anchored (open while `family_decided` is false).
- Ground physics: the 3-D footprints are not in `ground.js buildingGrid` yet (above); the realtime owner's call.
- KTX2 / meshopt compression (`tools/engine/glb_compress.mjs`) is still a later step: it needs the KTX2 transcoder and the
  meshopt decoder in the vendored bundle and the artifact (WASM policy unverified, engine.md 5).
<!-- integration:end -->
