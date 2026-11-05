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

## International Terminal: main hall, Boarding Areas A and G (key `itb`, 4 Nov 2026; review round 1 5 Nov)

```bash
python3 tools/blender/build_itb.py          # ~2.5 min: geometry, textures, AO bake (2048 + 512), export, verification, manifest
python3 tools/blender/verify_itb.py         # numbers only, reads the glb back (no bpy) -> out/buildings3d/itb_verify.json
python3 tools/blender/render_itb.py --views west,i4,i3,a2g,baa,bag,plan # Cycles references, ~3 min at 48 spp
python3 tools/blender/itb_a2_solve.py       # camera of photo a2 (BA-G NNE face) from 10 picks -> out/buildings3d/itb_a2_camera.json
python3 tools/blender/itb_roofobs.py        # (r2) rooftop units on the BA-A / BA-G roofs measured on NAIP 2024 -> tools/blender/itb_roofobs.json
python3 tools/blender/ao_view_itb.py        # QA view of the baked AO (emission of the occlusion texture)
python3 tools/blender/ao_view_itb.py --backface --lod 0 --views i4,i3,a2g,bag,east,top,baa   # back faces red (single-sided)
```

| File | Role |
|---|---|
| `tools/blender/itb_geom.py` | Geometry (numpy / shapely, no bpy). Imports `tools/buildings/draw_itb.py` / `draw_data.py`: the drawn functions are the reference, not copies. |
| `tools/blender/itb_tex.py` | Our procedural tiles: normal maps (membrane seams, panel joints, curtain-wall caps, frit transoms), frit, curtain-wall and BA-G gate-room base colours |
| `tools/blender/build_itb.py` | bpy build, NAIP roof-colour sampling, AO bake, glTF export, manifest |
| `tools/blender/itb_manifest.py`, `build_itb_manifest_merge.py` | Manifest entry (tags, inferred / unknown / conflicts, budgets); render list |
| `tools/blender/verify_itb.py` | 110 checks against the sheets and the plausibility rules |
| `tools/blender/render_itb.py`, `ao_view_itb.py`, `itb_a2_solve.py` | Reference renders of the exported glb; AO and back-face QA views; the photo-a2 camera solve |
| `tools/blender/itb_roofobs.py`, `itb_roofobs.json` | (r2) rooftop units measured on NAIP 2024 (dark-object / shadow extents, the domestic `dom_roofobs.py` method; numbers only, committed) |
| `data/buildings3d/itb.glb` (6.47 MB, r2), `itb_lod2.glb` (0.58 MB) | The asset; the LOD2 subtree alone for the far / phone tier |

**Placement.** Root `itb` at world (−1244.555, 3.0, 365.405), the relief-corrected roof centre (`draw_itb.F`, frame-model
corners of `roof.corners_obs`). Roof frame: u along heading 162.85° (+ towards BA-A), v across (+ ENE).

### What is modelled, and from what

| Node | Source | Notes |
|---|---|---|
| `hall_roof` | obs | 252.87 × 65.40 m slab on the spec corners; silhouette = `roof_line(u)` (BI-02: notches 35.7, humps 40.08, crown 40.1, tips 34.4 held non-increasing); flat across (camber unknown); 0.6 m deck + fascia [inf]; glazed tip bands 18.75 / 15.75 m set 1.6 / 3.6 m inside the fascia [obs]; 5 glazed truss-line strips 1.5 m [obs, rough]; 5 lens skylights from `lens_poly` (size obs, pointed-lens planform inf) **raised as vaults** (crown_cap + 0.4 m along each lens centre line, 2.0 m at the crown), the centre deck / fascia `crown_cap(u)` below `roof_line` - review r2: flat-topped 1.6 (1 - abs(x)^3)^0.7 m over the lens row (i4 re-measured: 1.6 m at the crown, dark over ~80 % of the notch-to-notch span), so the dark lens glass forms the crown silhouette as in photos i4 / i2 (cap obs i4, rise / form inf); dark soffit 50 / 53 / 57 (photos i3 / i4, r2) |
| `hall_trusses` | inf | 5 three-chord trusses on the truss lines (12.12 m [obs]); depth 29 ft over the supports [pub] with the BI-03 taper; webs on the 20-ft grid offset 10 ft (it carries the column lines and the canopy hangers): V posts at every node and opposite diagonals in the two side planes, an X per panel seen from the west (review r2, photo i4) |
| `hall_columns` | inf | 20 columns (5 lines × ±190 / ±270 ft); the west line 2.5 m in front of the glass, branching into 5 members (count obs, i3 / i4): r2 - the post continues to the roof (r 0.30), slender struts to the bottom-chord nodes ±6.1 m (r 0.18) and to the eave soffit ±2 m (r 0.16) |
| `hall_brackets` | obs (low) / inf | review r2: 35 dark inverted-V wall-head brackets 1.7 × 1.4 m at mid-panel (u = k 20 ft) under the west truss (photo i4 rhythm / size; form inf) |
| `hall_outriggers` | inf | eave outriggers under the soffit at every truss node (photo i3); r2: white, 0.35 × 0.9 m (photos i3 / i4) |
| `hall_west_wall`, `hall_mullions` | inf / obs | wall at v −25.8 (middle of the band −28.3..−23.3) over the 705-ft hall [pub]; L3 11.5, head 30.8 [obs photo], clear central bay ±40 m with its head 2 m higher [obs, tentative]; fritted side bays (horizontal 0.9-m frit bands, own normal tile `itb_n_frit`); mullions on the 20-ft grid, transoms 2.2 m [obs, low]; upper glazing behind the exposed west truss (photo i3); LOD1 keeps the mullions (west + end walls joined) |
| `hall_lettering` | obs | "SAN FRANCISCO INTERNATIONAL", 66 × 2.8 m at 25.8–28.6 m (BI-02 box); font inf (Blender built-in); LOD1: flat, coarse curves (276 tris vs 3,812) |
| `hall_canopy`, `hall_hangers`, `hall_curb` | inf / obs | canopy L3 + 5 m, 5 m deep [inf; exists pub]; hangers / posts at `HANGER_U` (40-ft grid + ±30 / ±90 ft) [obs photo i4], posts 0.45 m behind the kerb (r2); curb sidewalk at L3 from the wall to the **kerb line v −30.1 [obs NAIP, r2]** (4.33 m), 0.15-m kerb, no upstand; `hall_bollards` (LOD0): 0.3 × 0.9-m bollards on the 10-ft pitch with gaps at the five NAIP crosswalks, a 1.07-m guard at the two end returns [inf] |
| `hall_end_walls`, `hall_east_clerestory`, `hall_podium` | inf / unk | end curtain walls at ±107.4 m up to the roof (outline unk); east clerestory 1 m inside the east eave; levels 1–2 as faces only |
| `itb_core` | unk | SFO Museum ITB outline − piers − hall: east block and north / south bars, **17.9 m placeholder** (no source). Review r2: the north bar that the roads cross is an elevated connector (underside 10.5 m = L3 − 1.0, ≥ 4.6 m over the 5.9-m viaduct; 7 round columns clear of the roads) [inf]; the east block is cut back where OSM road footprints graze it |
| `ba_a_body`, `ba_g_body` | obs | SFO Museum outlines at 17.9 / 17.0 m [obs]; 1 m parapet [inf]. **BA-G (review r1, photo a2 = its NNE face, camera solved):** the 10 bridge-head bump-outs of the outline are 6.5-m boxes [obs a2, low]; the two-storey gate-room curtain walls (4.6–14.7 m, 63.5 m wide, `glass_gate` with the a2 mullion rhythm) fill the main-face segments between the bump-outs that a roof pod overlaps by ≥ 35 m: 6 rooms = the "six double-gated gate rooms" [pub] (NNE face obs, SSW face and G3 inf); dark apron level 0–3.0 m and a light band to 4.6 m [obs a2]; r2: 7.32 × 3.048-m composite-panel module with faint halving lines (a2 joints) as base-colour + normal tiles on every `alu_panel` wall, the four imaged 2-lite windows of the NNE face, teal gate glass; `ba_roof_units`: rooftop units measured on NAIP 2024 (`tools/blender/itb_roofobs.py`) [obs extents, inf heights]. **BA-A:** no reference photo (a2 is BA-G): the round-0 bays (24 m centred on the bridge attach points) stay as placeholders [unk], with the BA-G band heights [inf] |
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
| 0 | < 450 m | 69,287 | 58 | everything; trusses 8-sided chords with webs (37k tris, X per panel since r2), mullions, lettering, antennas; lens vaults (+4k); r2: wall-head brackets (2.1k), kerb bollards / guards (1.8k), roof units (0.7k), the elevated core bar with columns |
| 1 | 450–1600 m | 36,927 | 54 | shared shells (same meshes / atlas as LOD0); 4-sided trusses, lighter columns (all 20) and hangers, mullions (one node), flat lettering; r2: brackets, roof units (plain) |
| 2 | > 1600 m | 5,336 | 20 | one joined node (8-m roof stations, coarse lens vaults, BA-G bump-outs, simplified outlines, the elevated core bar), own 512-px atlas; also `itb_lod2.glb` |

Textures (PNG, embedded): AO atlas A 2048² (2.06 MB; LOD0 / LOD1 shells, 48 spp, 10-m rays, ground plane, white outside
the islands so mip levels do not bleed black; the thin mullion fins and the lettering are left out of the occluders since
review r1 - below the texel they baked ~1-m dark bands beside every mullion), AO atlas B 512² (0.16 MB); tiling normal maps
512² (membrane, panels, curtain caps, frit transoms; 2–28 kB); base colours 256–512² (frit, two curtain-wall glasses, the
BA-G gate-room wall). Glass is coated (IOR 1.9 → F0 0.096:
`KHR_materials_ior`, which Blender's exporter writes only together with `KHR_materials_specular`, here specularFactor
0.998; the IOR is also in the material extras) and opaque; `glass_hall` carries the brightness of the lit hall behind the
clear bay. Materials are single-sided (`doubleSided` false): every face is wound outwards, checked by the back-face QA
render (0 red pixels in 7 views × 3 LODs, after capping the open truss-chord ends; r1: the new NNE view found the glass-head
closure wound inwards since round 0 - fixed - and the wall tops now end 0.1 m inside the deck, as the soffit is piecewise
linear between the roof stations; the AO view `under` stands inside the core block and is not a back-face view). No TANGENT attribute (saves 1.3 MB; the validator's
generated-tangent warning is accepted). Khronos glTF-Validator 2.0.0-dev.3.10: **0 errors** on both files.

### Verification (verify_itb.py: 125 checks, 0 failed since review r2; tolerance 0.5 m or 2 %)

Review r2 added: curb kerb line v −30.1, no upstand, kerb face 0.15 m, 44 bollards clear of the crosswalks, canopy posts on the
sidewalk; 35 wall-head brackets; the four BA-G windows; 40 NAIP roof units inside the outlines; the north-bar underside 10.5 m;
the core on grade over OSM road footprints 0.0 m² and roadway deck inside it 0.0 m² (round 1: 85.7 m², same mesh test); decks
under the bar cleared by ≥ 5.46 m (≥ 4.6 m required); a cross-asset table walkway top vs host roof (not counted as an asset
failure: 20 BA-G walkways, request to bridges). Crown deck now 38.50 (silhouette 40.1 − cap 1.60), lens rise 2.0 m, centre
silhouette within 0.47 m.

- Placement exact; roof extent 252.872 × 65.397 m = the drawing; corners within 0.001 m of `roof.corners_obs`.
- Roof deck vs `roof_line(u) − crown_cap(u)` at all 4,507 deck vertices: max 0.000 m (the mesh is sampled on the function).
  At the named stations: crown deck 38.60 (silhouette 40.1 − cap 1.5), notch 35.79 (station 0.5 m off the notch), hump
  40.07, |u| 100 36.33 (36.40), tip 34.40. Lens vault rise 1.90-1.91 m (5 lenses); centre silhouette (vault tops) vs
  `roof_line` within 0.46 m (|u| ≤ 20).
- Rendered silhouette (orthographic west render, 0.28 m/px) vs `roof_line`: wings max 0.21 m, mean −0.02 m; centre 0.43 m
  (the lens tops seen horizontally, up to 0.4 m above the line they form from the i4 camera 2.7° below).
- Tip bands 18.75 / 15.75 m at 1.6 / 3.6 m; strips on the truss lines (0.00 m); lenses: length, width, centre within
  0.06 m, planform within 0.02 m of `lens_poly`.
- Trusses: bottom chords over the supports within 0.001 m of BI-03 (west: of the chosen max line); 20 columns at
  ±57.9 / ±82.3 m (0.02 m); west column line v −28.26 (−28.27); 16 canopy posts / hangers within 0.17 m of `HANGER_U`.
- West wall v −25.768, foot 11.5, head 30.8, central head 32.8, ±40 m bay, 214.88 m long, glazed area 4,281.3 m² = the
  drawn outline (this check was added after the back-face QA found the entrance band built as triangles - fixed);
  canopy 16.5 / 5.0 m; lettering 66.0 × 25.8–28.6 m.
- Piers 17.9 / 17.0 m; footprints = the SFO Museum outlines (area difference 0.001 / 1.6 m², 0 m² outside); all six pod
  tops and the box top (32.0) exact; pod plans = the NAIP traces (none needed clipping). BA-G: 10 bump-outs at 6.5 m, 6 gate
  rooms, curtain walls 4.6–14.7 m filling their segments (max 0.02 m short); BA-A placeholder glazing 4.6–14.7 m.
- LOD1 holds `L1_hall_lettering` (66.0 m wide, 276 tris) and `L1_hall_mullions`.
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
| `itb_i4.png`, `itb_cmp_i4.png`, `itb_i4_lod1.png` | photo i4 | two wings and the crown capped by dark lens glass (r1), exposed trusses, column fans, fritted side bays with horizontal bands, clear central bay with the lettering (also at LOD1), canopy line; the departures roadway in front is not part of this asset |
| `itb_i3.png`, `itb_cmp_i3.png` | photo i3 | column + fan, exposed truss over the head, dark soffit with outriggers, canopy with hangers, the centre arch at the notch, horizontal frit bands |
| `itb_a2g.png`, `itb_cmp_a2g.png`, `itb_a2g_lod1.png` | photo a2 (solved camera, r1) | the BA-G NNE face: pods G1 / G2, the two gate-room curtain walls and the three low bump-outs land on the photo's (bays 528–798 / 0–195 px vs 527–797 / 0–187 at 960 px) |
| `itb_baa.png` | BI-04 V2 (no photo of BA-A) | flat-topped pods on the pier roof, placeholder glazed bays at the bridge heads, dark apron level |
| `itb_bag.png` | photo d2, BI-04 V1 | the pod-3 end box with its window band and antennas; the BA-G gate rooms and low bump-outs |
| `itb_plan.png` | BI-01 V2 / NAIP | north-up plan: tip bands, strips, lenses, core and bars as imaged |
| `itb_i4z.png`, `itb_cmp_i4z.png` (r2) | photo i4 centre at full size | the i4 camera with a 2x lens (~4.4 px/m): X lattice with the verticals, the wall-head brackets, the wider dark crown, the lettering tracking |
| `itb_curb.png` (r2) | photo i3 (furniture) | the curb from the roadway side: sidewalk to the NAIP kerb, 0.15-m kerb, bollards with crosswalk gaps, posts on the sidewalk, no upstand |
| `itb_bar.png` (r2) | roadways.glb (context) | the core north bar as an elevated connector (10.5-17.9 m) over the domestic departures viaduct, columns between the roads |
| `app/itb_r2/cmp_new_{i3like,i4like,a2g}.png` (r2) | the app (three.js, SOFTGL, `?b3donly=itb,roadways`) | i3like: no upstand, kerb bollards, dark brackets, dark soffit with white outriggers - and the 6.2-m gap to the roadway deck (request); i4like: lattice, crown, near-black letters (darkest 3 vs 11 in r1); a2g (LOD1): teal gate rooms, panel module, windows, roof units, the app walkways above the 6.5-m bump-outs (request) |
| `itb_ao_*.png` | — | AO: soffit near the walls, under the canopy, curb and pod bases; no leaks seen |
| `itb_bf_*.png` | — | back-face QA (i4, i3, a2g, bag, east, top, baa × LOD0-2): 0 red pixels |
| `itb_app_i4like.png`, `itb_app_i4far.png`, `itb_app_a2g.png` | the app (three.js, SOFTGL, `?b3donly=itb`) | i4-like at 330 m (LOD0): the fritted bays now read as horizontal bands - column-mean std of the bay 2.3 against 8.9 before r1 (row-mean 5.0 / 5.7); at 620 m (LOD1) the lettering and the dark crown cap stay; a2 camera at 800 m (LOD1): the BA-G gate rooms between the low bridge-head boxes, with the app's bridges docked at the boxes |

### Open items (also in the manifest's `unknown` / `conflicts`)
- The ITB core block height (17.9 m placeholder) and its facades; the AirTrain stations at ITB level 4 inside the bars
  and the guideway are not modelled here (landside group / integration).
- The 2024–26 roof (new membrane, ~1.4 MW PV) is not imaged; the asset shows the NAIP 2024 roof.
- Conflicts carried from the sheets: 860 ft vs 252.9 m length; the 210-ft hall width; BA-A pod 1 NAIP 23.6 vs DOF 25.91 m.
- LOD1 has 48 draw calls (shared shells, one primitive per material per node): merge per material at load time on phones.
- **BA-A facades have no reference photo** (round 0 compared BA-A with a2, which shows BA-G): its glazing is a placeholder.
  A Commons search (2026-11-05, rate-limited) found no exterior photo identifiable as BA-A; an owner photo of the BA-A apron
  faces (WNW / ESE) would settle it. BA-A's pods sit over its bump-outs, so the BA-G rule does not transfer.
- (r2) The four imaged 2-lite windows of the BA-G NNE face are modelled; windows on its SSW face and on BA-A are not imaged.
- (r2) **Requests:** integration - extend the `itb_departures` deck of roadways.glb to the measured kerb line (v −30.1; it
  starts at v −36.3 with a parapet: a 6.2-m gap) and re-run the roadway trim against the new itb.glb; bridges - lower the
  BA-G fixed walkways (top ≤ 6.0 m at the attach point; G1-G10, 20 walkways at 8.45-8.46 m dock into 6.5-m bump-outs).
  Both in `manifest.json#itb.requests`.
- `data/buildings3d/integration.json` records the itb.glb sha1 of the integration run; re-run `tools/blender/b3d_integrate.py`
  (integration owner) to refresh it - the plan footprint is unchanged, so its physics / plausibility tables stay valid.

### Review round 1 (2026-11-05): dispositions

| # | Finding | Disposition | Evidence / change |
|---|---|---|---|
| 1 | frit bays show ~1-m vertical stripes; "UVs turned 90°" | **fixed; the cause was not the UVs** | glb TEXCOORD_0 of `glass_frit`: u = along / 3.6 m (0.212 over 0.762 m), v = height / 3.6 m (3.556 over 12.8 m), the base tile has horizontal bands (row-mean std 46 vs column 12) - so the mapping was right. The stripes came from (a) the `itb_n_curtain` normal tile reused on the frit's 3.6-m tile: its 1.524-m verticals land every 0.9 m (near Nyquist at 330 m in the app: moiré), (b) the AO bake: the 0.4-m mullion fins darkened ~1-m bands beside every mullion (and on LOD1, which shares the atlas, even without mullions), (c) 35 % pane-joint lines in the base tile. Now: own `itb_n_frit` (horizontal transom caps, 4-mm verticals), mullions / lettering out of the AO occluders, joints 15 % |
| 2 | piers read as blank boxes with small square glazed bays | **fixed (BA-G, obs); BA-A placeholder** | a2 re-measured with the solved camera (8.6 px/m at the facade): BA-G curtain walls fill the segments between the bump-outs under the pods, 63.6 × 10.1 m (4.6–14.7 m), bump-outs 6.5 m; 6 gate rooms. **Not done: the "continuous concourse window band"** - a2 shows none on BA-G (only two 2-lite windows per panel segment); the long green band in a2 is the building beyond the south apron (Garage G / BART station, landside asset) |
| 3 | the BA-A check used a photo of BA-G | **valid; fixed** | `itb_a2_solve.py`: bearings of 5 features put the camera NNE of BA-G looking 203° (residuals ≤ 16 px), the 3-D fit (10 picks) gives x −1059.7, z −614.2, h 163.4 m, f 6,780 px (127 mm eq.), picks within 16.7 px mean; new view `a2g` (+ LOD1); `baa` is now render-only (no BA-A photo found) |
| 4 | crown reads white from the curb; columns thinner than i3 | **crown fixed; columns kept** | i4: dark cap 10 px at 6.72 px/m = 1.5 m above the white fascia → lens vaults (1.9 m rise) and the cap; the crown now reads dark blue-grey in `itb_i4.png`. Columns: on i4 (frontal, 6.72 px/m at the wall), the two columns crossing the dark entrance glazing measure 9.3 / 10.3 px at half maximum and 12-13 px to the dark limb = 1.4-1.9 m, i.e. 1.6 ± 0.2 m: the drawn 1.5 m holds (inside the 0.5-m tolerance). i3's "~2 m" is perspective: its column stands 2.5 m in front of the wall, much nearer the camera than the wall it is compared with |
| 5 | LOD1 drops lettering, mullions, eastern columns | **fixed** | LOD1 now has the flat lettering (276 tris), the mullions (west + end walls, one node, 858 tris) and all 20 columns (720 tris): +1.6k tris and +2 draw calls at LOD1 (LOD1 total 34,976 with the +4k lens vaults of the shared roof). The inner columns stand inside the opaque envelope (not visible from outside) but the LOD sets now match |

### Review round 2 (2026-11-05): dispositions

| # | Finding | Disposition | Evidence / change |
|---|---|---|---|
| 1 | curb upstand walls the departures curb off (major) | **fixed** | NAIP 2024 resampled in the roof frame at the 11.35-m relief: the yellow detectable-warning strips of the five crosswalk ramps (u -52.8, -15.8, -4.7 / 2.5, 14.0, 49.5) centre at v -29.8, lane-1 car roofs at v -31.0..-32.3 -> **kerb line v -30.1 +- 0.4 [obs]**: the sidewalk is 4.33 m wide (was 7.0 m [inf], i.e. 2.7 m into lane 1). No upstand; a 0.15-m kerb face (`kerb`, the roadway deck at L3 - 0.15); 0.3 x 0.9-m bollards (photo i3) 0.6 m behind the kerb on the 10-ft pitch with gaps at the crosswalks (44 bollards); a 1.07-m guard only at the two curb end returns (open edge). The canopy posts moved 0.65 m in (they stood 0.2 m out on the roadway). **Request (integration):** the `itb_departures` deck of roadways.glb starts at v -36.3 with a parapet on its inner edge - a 6.2-m gap to the measured kerb over abs(u) < 55 m (manifest `itb.requests`) |
| 2 | truss lattice coarse, thick column Y-branches, no wall-head brackets (major) | **fixed** | i4 (4x zoom of one column bay): verticals on the 20-ft grid and an X in every panel. The two side planes of each three-chord truss now carry opposite diagonals (round 1: both planes alike, so the front view showed one N-web per panel); the V posts are the verticals. Column fans: the post continues to the roof (r 0.30) with struts to the bottom-chord nodes one panel either side (r 0.18) and short eave struts (+-2 m, r 0.16) - the +-10-m arms are gone. 35 dark inverted-V wall-head brackets (1.7 x 1.4 m, i4 ~12 x 10 px) at mid-panel (u = k 20 ft) under the chord. `itb_i4z.png` / `itb_cmp_i4z.png` (the i4 camera with a 2x lens, ~4.4 px/m, next to the full-size photo centre) shows the X per panel between the verticals, the brackets and the slender fans; a peak count along a mid-depth row of one column bay in the 960-px `itb_i4.png` is resolution-limited (12-16 by local maxima; round 1 5-8 by the reviewer's count, photo 16-17) |
| 3 | wing-tip soffit light and smooth; no outrigger rhythm (minor) | **fixed** | `soffit` 84 / 87 / 91 -> 44 / 47 / 51 (metallic 0, rough 0.9: at the ~2-deg i4 view a smoother panel mirrors the lit ground), `glass_roof_under` (the glazed tip bands seen from below) 150 / 172 / 178 -> 96 / 108 / 114; outriggers white (`steel_white`) 0.35 x 0.9 m (were dark-grey 0.3 x 0.6 m, lost against the soffit). Soffit / sky at the left tip (same column, `measure_r2.py`): the tip now reads dark with the white outrigger ends in rhythm under the eave (`itb_i4.png`); the glazed tip band seen from below stays mid-grey |
| 4 | frit reads as white siding, clear bay too light, letters mid-grey (minor) | **fixed** | frit tile 214 -> 184 (white band) / 92 -> 62 (clear band), roughness 0.22 -> 0.12 (coated glass reflects the sky); `glass_hall` (the clear centre bay) now uncoated clear glass, IOR 1.5 (F0 0.04, was the coated 0.096), base 100 / 110 / 116 (was 118 / 130 / 136): in Cycles the coated sky reflection made the bay light, while the app renders it mostly by its base colour - a darker base alone (60 / 68 / 74, tried) gave 0.77 in Cycles but 0.32 in the app (`app/itb_r2/cmp_new_i4like.png`; r1 base: 0.64); `lettering` 38 / 42 / 46 metallic 0.3 -> 16 / 18 / 20 rough 0.6 with bolder strokes (curve offset 0.03; the built-in font is light). i4 render: Cycles centre / side bay 169 / 198 = 0.86 (round 1: 182 / 207 = 0.88; photo ~0.7) - a compromise with the app (above); letters darkest 28 (1st percentile 32; round 1 ~90-102, photo 53) after making them matt (rough 0.95, specular level 0.1: the frontal i4 sun lit a 4 % specular lobe) with wider tracking; the app showed them near-black already (darkest 3); i3 (now lit as the photo: facade in shade) shows the side bays as banded glass, not siding |
| 5 | dark lens crown narrower and lower than i4 (minor) | **fixed (span), rise kept** | i4 re-measured at full resolution (column scan between the notches x 797..1230): the dark band is 11-12 px (~1.6 m) at the crown and >= 3 px over 83 % of the notch-to-notch span. `crown_cap(u)` is now flat-topped over the lens row, 1.6 (1 - abs(x)^3)^0.7 (round 1: a 1.5 m parabola), and each lens vault rises crown_cap + 0.4 m; the dark crown now spans 74 % of the notch-to-notch width at >= 2 px in `itb_i4.png` (round 1: 63 % by the same scan, the reviewer 59 %; photo 73-83 %). The notch-to-crown rise is kept at the BI-02 silhouette (4.4 m): the photo reading (33 px of the skyline file, 4.5-4.9 m at 6.7-7.4 px/m) lies inside the +-2 m that `itb_photo_skyline.json` gives single readings (perspective / yaw not modelled) |
| 6 | BA-G / BA-A walls blank, no windows / roof units, gate glass grey (major) | **fixed** | a2 (solved camera, ~9 px/m on the NNE face, solid segment B1-B2 zoomed 3x): strong joints every 67 px along the face (7.3 m) and every ~26 px up it (2.9 m: the four rows below the roof edge), faint ones halfway (3.7 m / 1.45 m) -> a 7.32 x 3.048-m panel module with faint halving lines as a base-colour tile (`itb_c_panel`: 8-cm dark reveals, +-3 % panel tone) + normal tile on every `alu_panel` wall [obs a2 for BA-G; BA-A / core by analogy]. The four imaged 2-lite windows of the NNE face (s -19.5..-10.6 at 4.6-7.2 m, s -3.6..5.3 at 9.8-12.1 m above bump-out B2, s 76.2..84.9 at 6.9-9.2 m, s 92.1..101.4 at 4.6-7.2 m; +-2 m / +-1.5 m) [obs a2, low]. Rooftop units from NAIP 2024 (`tools/blender/itb_roofobs.py`, the domestic method): 40 units (BA-G main roof 20, bump-out roofs 2, BA-A 18; 608 m2). Gate glass teal: base 16 / 92 / 96, caps 110 / 122 / 124 (a first try at 22 / 66 / 68 rendered 54 / 61 / 62); a2g render glass 54 / 70 / 74 (round 1: 56 / 57 / 57 by the same measure; photo 52-66 / 69-85 / 68-86) |
| 7 | ITB core north bar a solid from grade across the roads (major) | **fixed** | the bar (924 m2, mean width 5.9 m) that the OSM roads cross is now an elevated connector: underside 10.5 m (L3 - 1.0; 4.62 m over the 5.88-m deck under it, >= the 15-ft = 4.57-m minimum clearance [pub]), top the 17.9-m placeholder [unk], 7 round columns (0.6 m) where clear of every road footprint (+1.5 m; >= 1.38 m from the roadways.glb decks). The east block is cut back where OSM road footprints graze its outline (-144 m2, <= 5 m deep). verify (mesh-based): roadway deck inside the core on grade 0.0 m2 (round 1: 85.7 m2 by the same mesh test), core on grade over OSM road footprints 0.0 m2, decks under the bar cleared by >= 5.46 m |
| 8 | BA-G bump-outs (6.5 m) vs the app walkways (top 8.46 m) (major) | **rejected for the asset (bump-outs kept at a2), conflict reported to bridges; verify check added** | Projected with the solved a2 camera, the 6.5-m outline of bump-out B1 lies on the observed bump-out roof (with its rooftop unit and a yellow box), a 9-m outline falls on the gate-room glazing behind it (`itb3/a2_bump_proj_z.png`, local); re-reading the back roof edges per column gives 6.5-7.2 m; a 2-lite window of an upper storey sits ~3 m above bump-out B2 (9.8-12.1 m) where a 9-m box would cover it; and the walkway roofs meet the bump-outs ~1-1.4 m BELOW their roof edge. So the inferred value is the walkway head: gates.js `DEPARTURE_LEVEL` 5.4 m [inf] + `WALK_H` 3.0. **Request (bridges):** BA-G walkway top <= 6.0 m at the attach point. verify_itb.py now lists walkway top vs host roof for every A / G walkway (cross-asset table, `itb.verification.plausibility.walkway_vs_host_roof`): the 20 BA-G walkways of G1-G10 (top 8.45-8.46 m against bump-out roofs 6.5 m) fail, every BA-A walkway clears its host roof (16.9 / 17.9 m) |
| 9 | 3-D changes not drawn back into BI-01..04 (minor) | **fixed as a record** | the sheets were not redrawn (owned by the 2-D step; the BI sheets stay the reference of round 0); `manifest.json#itb.deviations_from_sheets` lists the 11 deviations with sizes and tags (crown cap 1.60 m / deck 38.50 at the crown, lens vaults to +2.0 m, west chord up to +3.4 m, centre chord form, column fans, truss webs / brackets / outriggers, curb / kerb, bump-outs 6.5 m, pier glazing 4.6-14.7 m, BA-G wall detail, core north bar) |

<!-- tower:begin (written by tools/blender/build_tower.py) -->
## Control tower (ATCT 2016) and base building: `data/buildings3d/tower.glb`

```bash
python3 tools/blender/build_tower.py --render --audit   # both families, AO bake, export, manifest, verification, renders (~16 min, 4 CPUs)
python3 tools/blender/tower3d_verify.py data/buildings3d/tower.glb 2   # re-measure an exported file (tower.glb = F2, tower_f1.glb = F1)
```

**Source of the geometry.** Everything is generated from the approved sheets BT-01..03: `tools/blender/tower_geom.py` imports `tools/buildings/draw_tower.py` (and through it `spec_tower.json` and the SFO Museum footprint) and uses its functions and constants (`shaft_outline`, `cab_outline`, `plinth`, `SHOULDER`, slot / mast / pole bearings, `WING_TIP`, `NE_TIP`, `RIB_BRG`, `IBF_AIR_BAND`, `IBF_CW`, rows / twist of the cladding). Nothing is typed in twice. The one new measurement is the roof-garden outline (NAIP 2024 vegetated pixels, lean-corrected). No imagery is used as a texture.

**Height family.** The sheets draw two self-consistent families (buildings_tower.md 12.3). Default (3-D review round 1, 2026-11-05): `tower.glb` = F2 (D 14.5, rim 64.0; 221 ft at the 2015 mast station), the family that lies within the observations (cab-roof D 14.3 +-1.0 measured, 14.75 +-0.5 EXIF; rim 63.3-64.1 m for D 14.3 and 65 +-2 m for D 14.75 in the `h_roof_top` test). `tower_f1.glb` = F1 (D 15.2, rim 67.36 = 221 ft at the rim) is the published-height hypothesis: it needs D >= ~15.1 and rests on the CTBUH classification of 221 ft (a database class, not a survey); `?b3dtower=f1` loads it. `manifest.json#tower.family_decided = false`: the owner decides.

**Placement.** Root node `tower` at world (-740.5, GROUND_Y, 324.5) = the inferred shaft axis at grade (x east, y up, z south, js/geo.js). Cab-floor / eye heights and the other anchors are in the root extras of each file and the manifest (F2: floor 57.551 m, eye 59.151 m, glass 58.362-61.303 m, rim 64.0 m, highest whip 68.484 m; F1: floor 60.6, eye 62.2, glass 61.45-64.533, rim 67.36, whip 72.06 m).

| LOD | Use (suggested camera distance) | Triangles F2 / F1 | AO atlas (TEXCOORD_1) | Content |
|---|---|---|---|---|
| LOD0 | < 350 m (close-up, tower view) | 34,789 / 35,848 | 2048 px | 272 helical columns, recessed slots with perforated screens and glazed lowest panes, dark seam joints, 24 tinted cab panes + slim dark joints, cab interior (floor, console ring, shade band, ceiling), ribbon mullions, 15 whips + 9 poles + red light, base-building mullions, coping, rails, rooftop unit, sunken garden |
| LOD1 | 350-1200 m | 10,783 / 11,087 | 1024 px | 136 columns, flat slots (screen tone), dark seam joints, 24-facet cab, 15 whips + red light, plain base building with parapet |
| LOD2 | > 1200 m; phone (`tower_lod2.glb`, F2) | 2,461 / 2,595 | 512 px | 68 columns, flat slots, 12-facet cab, 15 whips (3-sided) + red light, base building as a box |

Files: `tower.glb` (F2) 3.46 MB, `tower_f1.glb` 3.56 MB, `tower_lod2.glb` (F2) 0.33 MB (PNG textures; KTX2 / meshopt later with `tools/engine/glb_compress.mjs`). Materials are PBR (our choices for the published "SFO Silver" ACM, glass, panels; `extras.src` on every material). The cladding carries a procedural base-colour + normal tile on TEXCOORD_0 (`tools/blender/tower_tex.py`, 4 joints x 2 panel rows per tile): dark helical and row joint lines (6.5 cm, 0.35 x the panel tone at the centre) and a +-5 % tone per panel, mip-mapped (no moire); the two circumferential seams are dark 0.10-m joint bands flush in the shell. The slots are recessed pockets with a perforated screen 0.06 m behind the face (base-colour tile: a staggered hole grid on a mid-grey sheet) and a light reveal. The cab glass is tinted and see-through (alpha 0.6, double-sided: the far-side panes and the sky show through in a level view) with slim dark 3-cm butt joints; behind it a neutral placeholder interior (floor, console ring, a dark shade band inside the glass head, mid-dark ceiling). Sun-independent AO baked by Cycles (48 samples, 8 m rays, ground plane as occluder). Every other surface is single-sided and wound outwards (back-face audit renders).

**Verification** (`out/buildings3d/tower_verify.json`, measured on the exported GLB against the sheet functions):
- F2 (default): 110/110 checks within tolerance; tris {0: 34789, 1: 10783, 2: 2461}; plausibility clear of aircraft envelopes, bridges and taxilanes; the app's T2 hall / BA-D walkway parts overlap the base-building footprint (integration: cut them)
- F1: 110/110 checks within tolerance; tris {0: 35848, 1: 11087, 2: 2595}; plausibility clear of aircraft envelopes, bridges and taxilanes; the app's T2 hall / BA-D walkway parts overlap the base-building footprint (integration: cut them)
- largest deviation of a length: 0.047 m (tolerance 0.5 m / 2 %); 0 failures.
- Khronos glTF-Validator F1: 0 errors, 0 warnings, 33 infos (info:UNUSED_OBJECT); F2: 0 errors, 0 warnings, 33 infos (info:UNUSED_OBJECT)
- plausibility (F2): clear of aircraft envelopes, bridges and taxilanes; the app's T2 hall / BA-D walkway parts overlap the base-building footprint (integration: cut them); nearest aircraft envelope 15.6 m (C3), bridge 37.2 m, taxiway centreline 85.3 m.

**Integration.** The loader (`js/three/buildings3d.js`) reads the anchors from the loaded file's root extras: the app's tower view takes `world.towerPos.eyeY` = GROUND_Y + `cab_eye_h` of that family (js/live/app.js hook; GROUND_Y + 62 before a tower file is shown), and the alpha-blended cab glass is hidden while the camera is inside that family's glass ring (radius `glass_head_r` + 0.3, `cab_floor_h` - 0.5 .. `glass_head_h` + 0.5). The first-pass T2 hall / BA-D walkway parts over the base-building footprint are cut by `tools/blender/b3d_integrate.py`.

**Renders** (Cycles CPU, 64 samples + OIDN, AgX; ours; of the default family F2): `out/buildings3d/tower_A.png`, `tower_B.png` (the BT-02 elevations, orthographic; `tower_overlay_A/B.png` carry the sheet outlines in red), `tower_t2.png`, `tower_t3.png`, `tower_t4.png` (camera-matched to the reference photos t2 / t3 / t4, Famartin 2025, CC BY-SA 4.0; per family the focal length follows the rim width in pixels and the camera height the angle below the rim, the sun is computed for the photo time; side-by-side comparisons `tower_compare_*.jpg` stay local). App views (three.js, llvmpipe, `?b3donly=tower`, photo-matched camera and sun; `tools/blender/tower_app_job.mjs`): `out/buildings3d/app/tapp_t2.png`, `tapp_t4.png`, `tapp_t4close.png`, `tapp_t2like.png`, `tapp_towercam.png` (+ `tapp_t2_metal0.png` / `tapp_t2_col085.png`, material experiments), `tower_app_info.json` (round 1). Round 2: `out/buildings3d/app/r2/tapp_t2.png`, `tapp_t4.png`, `tapp_towercam.png`, `tapp_t4night.png` (21:30 PDT: the LED ribbon), `r2/low/tapp_lowcam.png` (low tier, tower view); the floor-moire experiments (old file, low tier) in `out/buildings3d/app/r2exp/`.

**Observed vs inferred.** Per dimension in `manifest.json#tower.dimensions`; lists `inferred`, `unknown`, `not_modelled`, `conflicts` there. Node extras carry `src`, the spec keys and per-feature tags.

**Review round 1 (2026-11-05).**
- 1 (major) cladding read as flat grey plastic, seams as light raised bands - FIXED: procedural base-colour + normal tile (4 joints x 2 rows per tile) with dark helical and row joint lines; the two seams are dark 0.10-m joint bands flush in the shell (the light 0.03-m-proud band is withdrawn); material seam 98 / clad 150 sRGB (was 196 / 149).
- 2 (major) NE blade spike above the flare rim - FIXED in the sheet first (draw_tower.NE_TIP = 0, BT-02 redrawn: flush with the flare corner and the ribbon head, photos t3 / t4 / t5 re-read), then in 3-D: prow top = flare corner, F2 55.93 m (F1 58.90; was 61.7 F1), verify check "NE blade top". The deck over the landside sector (wing, ribbon head, NE blade) is now flat, then rises ~14 deg to the plinth (photos t3 / t4: flat blade tops; from t4, ~30 deg below, no deck shows above the blade or the ribbon head): a first rebuild with the round-body shoulder there showed a sunlit facet above the NE blade.
- 3 (major) cab an opaque black band - FIXED: tinted see-through glass (alpha 0.5, teal-grey; far-side panes and sky show through) with light 6-cm joints; glass / sky: Cycles t2 0.25 (photo 0.28), t3 0.16 (photo 0.10).
- 4 (major) shaft as bright as the sky in the app - CHECKED at the photo's sun, albedo kept: the review compared the app at the snapshot time (sun az 134 / el 42 behind the camera: cos 0.74 on the face) with photo t2 (11:57 PDT, sun az 137 / el 62: cos 0.47). Same camera and sun as t2 (tools/blender/tower_app_job.mjs, out/buildings3d/app/tapp_t2.png): lit shaft / sky 0.82 in the app, 0.77 in Cycles (tower_t2.png), photo 0.82 against the blue sky / 0.70 against the fog; metalness 0 instead of 0.15: 0.83, base colour x 0.85: 0.62 (too dark). At the snapshot time (t2like) 1.08. The clad albedo (~0.31 linear) also reproduces the photo's shaft / bridge-roof ratio, so it is kept. The Cycles photo suns were typed in by hand in round 1 (t2 az 165, t3 110): now computed (NOAA; 137.4 / 95.5); the cab glass reads 0.12 of the sky in the app from 12 deg below (the unlit ceiling behind the upper half, the sky through the lower half; Cycles 0.25 with interior bounce light; photos 0.28 / 0.10).
- 5 (minor) upper slots too wide / long slot right of centre - FIXED width and phase in the sheet (SLOT_W 1.4 -> 0.95 m, SLOT_PHASE 124 -> 127, t1 + t2 together); the long-slot offset is REJECTED: at the same three rows the t2 photo reads u/R +0.37 / +0.12 / -0.07, the render +0.34 / +0.07 / -0.11 (within 0.05 = ~3 deg); the review compared different rows.
- 6 (major) red obstruction light only in LOD0, no masts in LOD2 - FIXED: the red-light fixture (material red_light, the app's beacon glow) is in LOD0 / LOD1 / LOD2 and in tower_lod2.glb, LOD2 carries the 15 whips (3-sided): the top is 68.48 m (F2) at every LOD.
- 7 (major) F1 default - FIXED: tower.glb = F2 (default, within the observations), tower_f1.glb = F1 (the published-height hypothesis, ?b3dtower=f1); family_decided stays false.
- 8 (minor) mast tips vs spec - FIXED: spec h_antenna_tips = 71.8 spec m (2025-08-12 obs ratio 0.30-0.31 D; 2015 station 70.7 kept as station_2015); F2 restated as "221 ft at the 2015 mast station"; mesh vs spec 2025 value: F2 68.48 vs 68.50, F1 72.06 vs 72.08.
- 9 (minor) tower camera / in-cab test on F1 values - FIXED: the loader takes eye and bounds from the loaded file's anchors (root extras); app.js reads towerPos.eyeY (one-line hook); app check: tower view eye at y 62.15 = GROUND_Y + 59.151 (F2), glass hidden inside the ring (tapp_towercam.png); F1 file anchors: eye 62.2 above grade, glass head r 6.537.

**Review round 2 (2026-11-05).**
- 1 (major) slots read as black gashes - FIXED: every slot cell above its glazed lowest pane carries a perforated screen 0.06 m behind the cladding face (obs photo t4: a dot grid; base-colour tile tower_tex.slot_color, a staggered hole grid ~0.05 m pitch on a sheet sRGB 122-131: tile linear albedo 0.56 x the cladding tile), a light reveal (the panel return) and the dark pocket behind; LOD1 / LOD2 flat slots take the screen tone (material slot_screen). Cycles t2, display ratio slot / neighbouring panels: upper band 0.64-0.74 (photo 0.69-0.76; round 1 0.10-0.20), long slot 0.73 (photo 0.62-0.72; round 1 0.30); a first pass with the sheet at sRGB 112-121 gave 0.56-0.65 / 0.66. App (out/buildings3d/app/r2/tapp_t2.png, photo-t2 camera and sun): 0.63-0.68 across the middle of the upper band (0.44-0.56 at the grazing flanks), long slot 0.70; round 1 0.02-0.08 / 0.10. At night the screens stay dark (photo t5); only the glazed lowest panes keep the office glow.
- 2 (major) cab glass an empty jar from below, two-tone - FIXED: a dark shade band inside the glass head (obs photo t1: the top ~0.35-0.4 of the glass dark all round; from 0.62 of the slant, 0.12 m inside the glass) hides the far side's sky that showed through the lower third; the ceiling is mid-dark (sRGB 62), the glass a lighter teal-grey tint (80, 98, 106) at alpha 0.6 (two panes pass 16 % of the sky). Cycles t2, vertical profile through the cab centre (grey levels): 24-34 over the whole glass height, mean 32 (photo 26-41, mean 34; round 1 11-20 over the upper three quarters, then 47-96); glass / sky 0.21 (photo 0.26). Variants in one Blender session: tint (48, 60, 64) mean 26 with the upper part 18 (0.5x the photo), (80, 98, 106) at alpha 0.7 mean 38, (100, 122, 130) at 0.7 mean 50. t3 (overcast photo): uniform 15-16 against the photo's 3-33. App t2: 23-42 over the glass height (mean 33; round 1: 1-4 over the upper two thirds, then 22-64); glass / fascia 0.34 (photo 0.38, Cycles 0.38).
- 3 (minor) light joints, black in-cab void, floor moire - FIXED: pane butt joints 0.03 m and dark (sRGB 38-43; the published frameless butt glazing, the thin dark joints of t2; were light 0.06 m); a neutral console ring (0.9 m high, 0.8 m deep, sRGB 96) and floor (sRGB 74) as unknown placeholders, in their own node cab_interior without baked AO (the Cycles AO of the enclosed cab was noisy and read as blotches in the tower view). Floor moire: root cause measured on the low tier (tools/blender/tower_app_job.mjs experiments, old file, out/buildings3d/app/r2exp/): high-pass of the floor 50.5 grey levels per pixel, 50.0 with GTAO off (aoAmount 0), 0.65 with the floor's receiveShadow off: the sun shadow test, not AO or a texture. The alpha-blended glass casts no shadow, so the sun reached the whole floor through the glass ring and the floor sat in the PCF penumbra of the 1024-px low-tier cascade, whose per-pixel rotated taps TRAA did not average. The interior placeholders (floor, consoles, shade band, ceiling) are now lit by the sky only (material extras.ambient_only: the loader gives them an empty lights node, no sun, no shadow lookup; IBL x baked AO stays). After (low tier, rebuilt file, out/buildings3d/app/r2/low/tapp_lowcam.png): floor high-pass 0.65 (was 50.5), console 1.8 (was 15.2); floor 112 / console 90 grey levels, 3 % of the window area clipped. Tower view (high tier, out/buildings3d/app/r2/tapp_towercam.png): console ring mean 109 and floor 113 grey levels (round 1: 0 / 1, the black void), slim dark joints, no blotches. A first pass with the interior in the baked-AO atlas (r2/pass1/) showed the Cycles AO noise as blotches on floor and consoles, and with the frame-metered auto-exposure that the environment work added at ~18:43Z (js/three/renderer3.js meter: centre-weighted 50-98th percentile of the geometry, the sky left out) the darker interior pushed 83 % of the window area to clipping; now 6 % (window mean 234). That an interior view meters on the interior is the environment work's to settle (noted for it).
- 4 (minor) LED ribbon glows white at night - FIXED: the ribbon material carries extras.led_color = the observed photo-t5 blue (median sRGB 82 / 137 / 209 of the lit ribbon, Varnum 2018-04 dusk; linear (0.084, 0.250, 0.638)), scaled to the loader's previous mean level and compensated for the app's AgX desaturation (a first night render with the photo-linear colour showed hue 209 / saturation 0.35 against the photo's 214 / 0.58; display ratios fit out = in^0.56, so the input is (0.077, 0.536, 2.848)); the loader glows in that colour (the wave modulates the level only; GLOW_DEF.led / setGlow('led') tint and scale it at run time) and the manifest lists it under night_glow as the observed default of a programmable array, inferred for any other night. App night render (21:30 PDT, out/buildings3d/app/r2/tapp_t4night.png): ribbon median sRGB (93, 146, 211), hue 213 / saturation 0.57 (photo t5 (82, 137, 209), 214 / 0.58; the first pass with the photo-linear colour, r2/pass1/: (104, 144, 182), 209 / 0.35).

**Open (for the owner).**
- The height family (F2 default / F1 hypothesis).
- t2 camera match: the camera height and focal length are estimates (no EXIF here); a camera-model check only.
- For the domestic group: `tools/blender/dom_geom.py` leaves out the T2 walls that face the base building up to 14.07 m (the F1 roof). With F2 as the default, the base-building parapet tops at 13.83 m, so a 0.24-m slit opens in the T2 wall above it. Take `anchors.ibf_parapet_h` of the loaded tower file, or the family minimum.
- NE channel wall: louvred like the SW wing (photos t3 / t4). In the sunny t4-matched render its upper part, which faces bearing 40, catches the 09:10 sun (az 95) and reads bright against the shaded NW faces. The photo was overcast, so the brightness cannot be compared.
- Obstruction light: one red fixture (t5) is modelled in every LOD; at a few km it is sub-pixel, so a LOD-independent point sprite belongs to the environment's lighting layer (data/sfo_lighting.js lists the tower as obstruction 06-323169, fixtures inferred from AC 70/7460-1N).
<!-- tower:end -->

<!-- landside:begin (tools/blender/build_landside.py; numbers from out/buildings3d/landside_verify.json) -->
## Landside: garages, AirTrain, Grand Hyatt, RCC, CAC, Superbay, United MOC (key `landside`, 5 Nov 2026)

```bash
flock out/.heavy.lock python3 tools/blender/build_landside.py     # ~2 min: geometry, textures, NAIP colours, 3 AO bakes, export, verify, manifest
python3 tools/blender/verify_landside.py                            # numbers only (no bpy) -> out/buildings3d/landside_verify.json
flock out/.heavy.lock python3 tools/blender/render_landside.py --views gar_a,hyatt,superbay,l4,l1,l5,overview
flock out/.heavy.lock python3 tools/blender/render_landside.py --views i2,bart,a2 --itb   # with itb.glb as context
flock out/.heavy.lock python3 tools/blender/render_landside.py --views cg_top             # + the NAIP crop beside it (local)
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
| `tools/blender/verify_landside.py`, `render_landside.py` | 182 checks on the exported glb; Cycles references with the sheet lines drawn over them; back-face QA |
| `data/buildings3d/landside.glb` (20.3 MB), `landside_lod2.glb` (2.10 MB) | The asset; the LOD2 subtrees alone (far / phone tier) |

**Layout.** Root `landside` at world (0, 3.0, 0); one child per building / AirTrain tile at its own origin (`origin_world_xz`
in the node extras), each with `LOD0_*` / `LOD1_*` / `LOD2_*` children: switch 0 / 450 / 1500 m **from that building node**
(the group spans 2.4 x 2.8 km, so one root LOD would not work). LOD0 / LOD1 share the shell meshes and their AO atlas
(A 2048 px: the six parking structures; B 2048 px: the other buildings and the AirTrain); LOD2 = one joined node per building
with atlas C (1024 px). Parked cars: 1,732 instances, one node per deck x shape x colour with `EXT_mesh_gpu_instancing`
(one material, paint / glass / skirt in COLOR_0), under LOD0 and LOD1.

| LOD | triangles (non-instanced) | instanced car triangles | draw calls (all buildings) |
|---|---|---|---|
| 0 | 162.0k | 93.4k | 350 (12 car groups per deck) |
| 1 | 81.5k | 65.7k | 310 |
| 2 | 15.6k | none | 107 (`landside_lod2.glb`: 2.10 MB) |

### What is modelled, and from what (per-dimension tags in the node extras and `manifest.json#landside.buildings`)

| Building | Plan | Heights | Facade / detail |
|---|---|---|---|
| Central garage | SFO Museum outline with the 58.9-m void [obs]; the AirTrain ring and T1 / T2 / T3 station polygons cut out above Level 5, garage structure under them to the guideway deck | parapet 81 ft = 24.69 [pub, definition unk]; deck 23.62 [inf]; levels = equal fifths, Level 5 = 19.75 [unk, BL-03]; rooftop boxes deck + 4.5 / + 2.0 [inf] | open levels (3-m dark recess, spandrels, piers 9 m [inf]); the void's level lines rise one pitch per turn (helix); roof: NAIP-traced beige rims (0.15 m) and stall-free lobes, 11 stair / elevator / plant boxes [obs NAIP plan]; roof light poles at the two DOF points 30.8 / 33.2 [pub]; 343 cars: 216 at their NAIP positions [obs] + 127 white / silver beside them [inf] |
| Garages A / G | outline up to the body end Lb 150.8 / 149.8 [obs]; drum = outline arc (R 16.2 / 15.2, fit residual < 0.6) [obs]; stair / elevator towers 8 x 8 m at both drum ends [obs NAIP / i2, size inf]; Garage A: the guideway strips inside the body, portals at the west face and the station-block back wall; Garage G: guideway cut out | r2 (photo a2, solved camera): parapet 29.1 / 27.5, deck (Level 9) 26.7 / 25.3, 9 levels at 3.34 / 3.16 m, drum ring 31.0 / 29.4, towers parapet + 1.5 [obs a2 / i2, low; +-2.4 m with the Hyatt pick]; helix eye a guard ring (no core above the ring); Garage A penthouse to 36.0 (open storey to 29.6) and NE rotunda D 16.5 to 36.5 [obs a2 / NAIP, low]; Garage A station block to the parapet, its east faces at the outline's SE corner (u 134.8 / 139.8) [obs outline / a2; l1 reading 31.75 = conflict] (r1: drum ring 39.6 / 37.6) | full-bay perforated screen panels between thin mullions over the lower 62 % of each level [obs l1]; drum in smooth metal panels with five long slots + an open top band, recessed 0.8 m [obs i2]; white precast towers with small square windows [obs i2]; Garage A station block: two long slots, open hall over the tracks and to the south on round columns [obs l1]; 92 / 77 cars [obs NAIP density] |
| LTP 1 / LTP 2 | outlines [obs] | LTP 1 parapet 16.5 [obs shadow], towers to the DOF tops 26.2 / 27.7 [pub, form inf]; LTP 2 deck 60 ft [inf], levels 12 ft [pub], PV canopies at deck + 3.5 [unk] | precast / exposed frame; PV rows over the stall modules [pub, layout inf]; 276 / 318 cars |
| Rental Car Center | outline [obs]; west wall = the outline between RCC_N and RCC_S | roof outline 54 ft [pub DOF]; 59-ft element at its DOF point [pub, form inf]; platform 8.0 [obs l5 camera solve, low] | west wall per photo l5: board-formed concrete, ribbon windows at the platform, band, canted louvre screen (1.2 m lean [inf]) with blades every 0.2 m [obs l5]; 626 cars in nose-to-tail lanes [obs NAIP] |
| Grand Hyatt | outline; the podium zone east of the slab face, which continues the outline's east face along the relief-corrected NAIP slab-roof edge (r1: no re-entrant notch) [obs, approx] | 44 m [inf, 13.2 pitches]; podium 10.67, colonnade 14.0 [inf]; penthouse +1.4 / +0.65 pitches [obs l4] | l4 face fractions (podium 0.47, colonnade 0.02-0.10, end bay, framed bay 0.615-0.842, masts, sign pier); saturated blue glass [obs l4] |
| CAC | outline | roof 60 ft, parapet 64 ft [inf] | window band per 15-ft floor [inf]; louvre fins on the S / W faces [pub] |
| Superbay | spine a -14..+18, roof a -80.5..+84.5, t +-69 [obs NAIP]; walls on the outline, 1 m inside the roof | spine 41.15 [pub DOF], root 39.65, tips 27.0 [inf], folds 1.5 [unk], door head 24.0 [unk] | 8 folded bays per side, hipped spine ends (plan BL-02), 2 x 67-m door bays per long face (8 leaves) [inf], one roof colour (NAIP 2024); red light (`red_light`, extras.obstruction_light) at the DOF point in every LOD |
| United MOC | imaged roof corners shifted west by 0.315 x 37.1 m (North-Field lean) [inf]; barrel hangars likewise | parts 35.7 / 40.2 / 35.4 at the DOF points [pub, extents inf]; barrel eave 14 / crown 24 [unk placeholders] | corrugated walls; no doors (not verified) |
| AirTrain | SFO Museum polygon (7.8 km of centreline), clipped inside the ITB outline and the Garage A body (not in its station hall) | deck top from station anchors (see below), harmonic interpolation, max grade 4.2 % | weathered concrete trough walls 0.9 m, running pads, a low 0.3-m guide rail, the twin-section walkway (+0.9 m) with galvanised handrails [obs l1 / l5]; east of the Garage A station a 1.6-m cantilevered walkway beside each single-track trough with a cable rail, the gap between open (r2) [obs l1]; single-column T-piers every 30 m (not inside buildings); 9 stations (glazed enclosures / curved canopies; Garage G: white barrel vault over platform and tracks [obs NAIP / a2]); RCC perforated tower D 4.7 at the SFO Museum polygon lobe, raked open hood, to the DOF TANK 18.3 [pub, identity inf] |
| SFO BART station (Bldg 497) | OSM way 221663595 (ODbL), its north edge within ~1.5 m of the NAIP 2024 shadow line; minus the Garage G body and the ITB | open ground storey 0-4 m (OSM min_height), top 1.6 m below the AirTrain deck (follows the level field) [inf] | columns every 9 m, white panels, green glazed band from 15.2 m (photo a2 ratios) [obs a2, heights inf]; the 3-track approach not modelled (shares the AirTrain corridor x -1920..-1592, then 2+ km west) |

**Station levels (deck top).** T1 / T2 / T3 19.75 (BL-03 Level 5 placeholder [unk]); ITB A / G 16.5 (ITB Level 4 [unk], keeps the
guideway inside the itb.glb core block); Garages A / G and the Hyatt station 19.75 [inf] (r2: a2 puts their Level 7 at 20.0 / 19.0); RCC 8.84 [obs, photo l5 camera solve + r2 top-silhouette fit]; LTP 15.24
("50 ft above a public roadway" [pub]); West Field Road interpolated (11.3). **Two deliberate deviations from the BL-03
placeholders** (both [unk] on the sheets; listed in the manifest): the Garage A / G stations at 19.75 instead of 6/8 of the drum
ring (29.7 / 28.2 m) - the Grand Hyatt station is 40 m along the same track, so the sheet value would need a > 20 % grade - and
inside the sheet's own [inf] range 18.3-21.0 m; the RCC platform at 8.0 m (round 1: the photo-l5 camera solved from the tower,
the guideway vanishing point and the horizon; the DOF TANK top 8.6 m above an eye 1.7 m above the platform; was 5.8 [inf] with the
BL-02 tower D 6.5, which puts the l5 camera inside the RCC) instead of 12.35 m. Also: the Superbay spine-end facets fall
to the cantilever-root level (BL-02 plan) rather than to the tip level (BL-03 V4 line, which would leave an 11-m step).

### Verification (verify_landside.py on the exported glb: 182 checks, 0 failed; tolerance 0.5 m or 2 %)
- Placement of all 24 nodes exact (0.01 m; round 1 adds `bart_station`); root at GROUND_Y.
- Heights = the sheet values to < 0.01 m: CG 24.69 / deck 23.62 / poles 33.2, 30.8; Garages A / G (r2, a2 solved camera - deviations
  from BL-03): parapet 29.1 / 27.5, ring 31.0 / 29.4, deck 26.7 / 25.3, penthouse 36.0, rotunda 36.5; LTP 1 16.5, towers 27.7 / 26.2; LTP 2 18.29 / 19.36 / PV 21.79; RCC 16.46, 59-ft element 17.98; Hyatt 44.0,
  podium 10.67, penthouse 48.67; CAC 18.29 / 19.51; Superbay spine 41.15, root 39.65, tips 27.0 / 28.5, door head 24.0; MOC
  40.2 / 35.7 / 35.4; RCC tower 18.3, D 4.70 (round 1: SFO Museum polygon lobe; BL-02 E draws 6.5 [inf]), platform 8.01.
- Plans: CG, LTP 1 / 2, RCC, CAC roof footprints = the outlines (0 m2 outside / missing; RCC: the canted louvres overhang the
  west wall by 1.1 m = 206 m2, by design); Hyatt 5.5 m2 outside (parapet buffering); drum fits R 16.21 / 15.17 (sheet 16.2 / 15.2),
  centres within 0.03 m; body ends 151.1 / 149.8 (150.8 / 149.8); rooftop box u 52.3-76.9 (exact); CG void 58.7 m (58.9);
  Superbay roof a -80.5 / +84.5, 138.0 m along the spine; Hyatt podium to f 0.470.
- AirTrain: deck inside the SFO Museum polygon (0 m2 outside); every anchored platform / track at its level within 0.02 m;
  99.9th-percentile grade between deck vertices 2-6 m apart 3.9 %.
- Cars: per deck = NAIP density x deck area (CG: the visual 300); minimum centre spacing 2.39 m (2.6-m stalls), all on the deck.
- Render silhouettes (orthographic, alpha pass) vs the sheet lines: Hyatt parapet max 0.04 m (0.135 m/px); Superbay spine
  max 0.07 m (0.177 m/px); Garage A ring: max 3.07 m / p95 2.98 m (0.333 m/px) since round 1 - the white stair towers rise 3.0 m
  above the ring [obs i2] and stand in the silhouette; the ring itself is exact in the verification.
- Back-face QA (red = an inward face): gar_a, superbay, overview, cg_top 0 px; a2 6 px; l1 56 px (was 2,085: the station block
  was open to the east); Hyatt 610 px (0.12 %: the colonnade recess at the curved south end); bart 569 px (0.09 %: inside a Garage G
  facade notch); l5 2,380 px (0.34 %: thin lines along the trough-wall tops / walkway edges of the round-1 track furniture) - small
  residuals, left open.
- **Plausibility**: nearest stand envelope (108 stands, app planforms) 26.3 m (G3; was 28.9 m at A4 before
  round 1); nearest bridge walkway / rotunda 55.8 m (A4); no SFO Museum taxiway polygon inside any footprint (nearest 204 m, RCC; Superbay / MOC 212 m).
  Integration: the MOC has no SFO Museum outline, so the app's ground physics does not know it - add its footprint
  (`manifest.json#landside.buildings.united_moc`) to the obstacle list.
- Khronos glTF-Validator 2.0.0-dev.3.10: 0 errors (both files); warnings only MESH_PRIMITIVE_GENERATED_TANGENT_SPACE (no
  TANGENT attribute, accepted as for the ITB).
- Thin see-through plates (louvres, station roofs, coping) and the dark garage interiors are `doubleSided`; everything else is
  single-sided and wound outwards (`landside_mesh.MB.face_dir` where the winding is not implied by a ring).

### Renders (out/buildings3d/, local; comparison sheets with photo pixels stay local)
`landside_gar_a.png` / `landside_cmp_gar_a.png` (BL-03 row 1 lines over the orthographic SSE face), `landside_hyatt.png` /
`_cmp_hyatt` (BL-03 row 2, l4 fractions), `landside_superbay.png` / `_cmp_superbay` (BL-03 row 4 door face), `landside_l1`,
`landside_l4`, `landside_l5`, `landside_a2` (camera-matched to the photos; `_cmp_*` side by side), `landside_overview.png`;
round 1: `landside_i2` (+ itb.glb; camera solved from four bearings), `landside_bart` (BART station / Garage G vault from the NNE,
a2 beside it), `landside_cg_top` / `_cmp_cg_top` (orthographic central-garage roof beside the NAIP 2024 crop, local only),
`landside_overview_lod2.png` (LOD2 only), `_bf` back-face variants.
Self-review: a2 reproduces the layout (Garage G with its station canopy along the NNW face, Garage A behind with the rooftop box
and core, the Hyatt beyond, the guideway curves); l1 (round 1, camera 28 m east of the face) the low station block with two slots,
the track portal, the open hall on columns to the south, the walkway between the tracks with handrails and the curved NE end with
full-bay screens - block width within 0.2 % of the photo's, the camera ~4.6 deg off in yaw; l5 the board-formed west wall, ribbon
windows, louvres, the perforated tower with its raked hood and the canopy only east of / behind the tower (as in the photo; the
glazed platform cabins and the steel stair are not modelled); i2 both garages with drums, towers and screens either side of the
ITB, the photo camera looks down from higher (the road is below it); cg_top the cars at their NAIP places in dark / coloured
paint, the ring road, lobes, rims and boxes, the void floor; bart the glazed band under the AirTrain deck; l4 the podium,
colonnade, penthouse steps, masts and framed bay (lens 176 mm, round 1).

### Open items (also in the manifest's `unknown` / `conflicts` / `deviations_from_sheets`)
- Garage A / G heights (review r2): measured on photo a2 with the solved camera (parapet 29.1 / 27.5); its absolute scale rests on
  the Grand Hyatt top 44 m [inf] (40 / 48 m -> -2.4 / +2.4 m). Conflict with the NAIP drum band (BL-03 39.6 / 37.6 via the ITB pole
  lean k 0.334; a2 implies k 0.43 here) and with l1's block-top reading (31.75 m, door-cabin scale): both listed, raised with the
  drawings group. (r1 text: the l1 "conflict withdrawn" rested on the 39.6-m ring reaching the frame top - not a height check.)
- Round 1 inferred items: drum towers 8 x 8 m (top ring + 3.0 m, i2), rooftop box heights (deck + 4.5 / 2.0), the void floor at
  grade, car blob colour un-mixing (0.5 car share, blue cast removed), the BART band (a2 proportions, low), the RCC platform
  8.0 m and canopy extent (l5, low).
- Not modelled (round 1): the BART three-track approach west of x -1592 (shares the SFO Museum AirTrain corridor), the RCC
  platform cabins / steel stairs (l5), 26 large airport buildings outside every asset (`manifest.json#landside.scene_not_modelled`).
- Station enclosure / canopy heights, the stair / elevator towers of the terminal-area stations, the Hyatt bridge, the LTP links.
- The RCC "66 ft", the DOF 10.4-m point inside the RCC outline (conflict), the MOC section extents and barrel-vault heights,
  the Superbay fold amplitude and door leaves, the CAC cladding: placeholders / inferred, as tagged.
- Guideway over the T1 / T2 / T3 terminal outlines (skybridge parts at Level 3 below it): check against the domestic asset.
- KTX2 / meshopt (tools/engine/glb_compress.mjs) and the js/three loader are later steps.
### Review round 1 (5 Nov 2026): what changed, and why

Measurements the sheets do not carry yet are in `tools/blender/landside_r1_obs.json` (written by
`tools/blender/landside_r1_measure.py`; NAIP 2024 plan positions / colours, OSM (ODbL) for the BART station, numbers read off
photos l1 / i2 / l5 / a2, each with its tag). They are listed per finding in `manifest.json#landside.review_r1` and raised with
the drawings group (end of this section).

| # | Finding | Disposition | What the model does now (evidence) |
|---|---|---|---|
| 1 | Garage A station block was the full-height face with three stacked slots | fixed (block); deck conflict withdrawn | A separate block over both tracks: top 12.0 m above the deck (l1: 11.1 m above the walkway, scaled from the 2.2-m platform-door cabin, +-15 %), two long slots at +7.4 m (none over the central pier), open hall under its soffit over the tracks and to the south on round columns, 30 m deep (l1 sightline: the sky above the block needs >= 27 m); its east face one precast wall from grade to the top with the two track portals, and the walkway deck between the tracks east of it (the SFO Museum Garage A outline tail lies exactly between the two track polygons [obs]; l1's camera stands on it). The curved NE garage end beside it stays at the 39.6-m ring [unk, BL-03]. A first reading of l1 put its parapet ~12.9 m above the deck (~32.7 m) and raised a conflict; it is withdrawn: in the camera-matched comparison (28 m from the face, block width within 0.2 %) the rendered curved end at 39.6 reaches the frame top as in the photo, so the 12.0-m reading had taken the receding left edge of the curved wall for its top |
| 2 | Drums / screens read as square punched panels; no stair towers | fixed | Drums: `drum_metal` (smooth light panels) with five long horizontal slots and an open top band, recessed 0.8 m (heights from i2, scaled from the drum width). Screens: full-bay perforated panels between thin mullions (4.05 m), covering the lower 62 % of each level with a dark strip above (l1). White precast stair / elevator towers (8 x 8 m [inf]) with a column of small square windows at both ends of each drum (NAIP bright boxes at the outline notches), top = ring + 3.0 m [obs i2, low]. Screen panels also on edges <= 4 m (the curved ends). The i2 comparison uses a solved camera (ITB roof, old tower cab, Garage A drum and NE corner bearings; held on the guideway east edge, residuals <= 1.3 deg) |
| 3 | No SFO BART station; Garage G station roof flat | fixed (station); approach not modelled | New node `bart_station`: plan = OSM way 221663595 `train_station` (ODbL; its north edge within ~1.5 m of the NAIP 2024 shadow line), open ground storey on columns (OSM `min_height` 4, a2), white panels, green glazed band 3.9 m tall, 1.6 m below the top, following the level field (a2 proportions; first cut: 15.2 m to the top, a sliver where the AirTrain descends west), the top carrying the AirTrain deck (follows the level field). The Garage G AirTrain station roof is a white barrel vault over platform and tracks (NAIP white roof, a2). The three-track approach shares the corridor the SFO Museum AirTrain polygon covers (x -1920..-1592) and continues 2+ km west to the wye: not separable from NAIP, listed as not modelled |
| 4 | Central-garage roof: uniform stall field, 300 random cars, waffle void | fixed | NAIP-traced beige rims (0.15 m raised; nature unk) and stall-free lobes (own NAIP colour), 11 rooftop stair / elevator / plant boxes (NAIP plan +-2 m and roof colour; heights inf), the stall-free helix ring road round the void (r 43.5 m [obs NAIP]), the void floor at grade with stall marks [obs NAIP: stalls and cars in the void], the void's level lines rise one pitch per turn (helix), 216 cars at their NAIP 2024 blob positions (blob colours un-mixed against the deck at a 0.5 car share and the common blue sky cast removed: the raw blob means had mapped dark cars to beige / silver) + 127 white / silver cars next to them (fleet share 37 %, not separable from the light deck) |
| 5 | l5 camera 75 m off; claims not supported | fixed: camera solved, comparison redone | The tower subtends 350 px; with the BL-02 D 6.5 [inf] the solution falls inside the RCC; the SFO Museum station polygon has the tower as a 4.7-m round lobe 1.8 m west of the DOF point -> camera on the east walkway 19.4 m from the tower (yaw 185.5, pitch +4, 26-mm equivalent); the DOF top 8.6 m above the eye gives the platform 8.0 m [obs, low] (was 5.8 [inf]). Louvres every 0.2 m (were 0.6), raked perforated hood (2.5 m rake, open top, doubleSided skin), twin tracks with pads / guide rail / walkway; the station canopy starts behind the tower and ends at its centre line on the west, 5.5 m wide (l5: open sky and the exit cabin beside the tower; the SFO Museum station polygon, 10.9 m across, includes the tower lobe) |
| 6 | Guideway: tall white trough, guide beam as a wall | fixed | Trough walls 0.9 m (were 1.1), guide rail 0.30 m (was 0.80), concrete running pads, the twin-section walkway (+0.9 m) with galvanised handrails (LOD0), weathered darker concrete (`ls_c_weather`) |
| 7 | Hyatt re-entrant notch; grey-mint glass | fixed | The slab face behind the podium continues the outline's east face from its notch corner along the relief-corrected NAIP slab-roof edge (no return face); glass retinted (texture glass (30, 92, 140), photo mean (38, 113, 150)) |
| 8 | Superbay two-tone roof, doors over the whole face | partly rejected, with evidence | l3 is the Superbay seen from the NW: the NNE end face (165 m, plain walls, the darker spine end under the hipped spine roof) on the left, the WNW door face (138 m, sawtooth fold eave, door leaves over its whole length) on the right - what the model has. NAIP 2024 at noon: one light colour on both cantilevers, medians (238, 238, 229) / (242, 242, 234): the grey-green / tan of l3 (~2008, low sun from the W) is the lighting of the two 11-deg roof planes. Doors stay [inf] |
| 9 | Other hangars / cargo missing | listed | `manifest.json#landside.scene_not_modelled`: 26 large airport buildings outside every asset (OSM ODbL ways, centres, areas: United Buildings 84 / 15 / 68, United Cargo, the West Field cargo row, ...) for a later spec round |
| 10 | Superbay red light not lit | fixed | Own material `red_light` with `extras.obstruction_light` (glowKind -> beacon), in LOD0 / 1 / 2 |
| 11 | LOD2 differs from LOD0, guideway into blank walls | fixed | Garage LOD2: parapet recess, core, rooftop box, towers, drum slot bands, station block, portals with dark backs; Hyatt penthouse; MOC barrels to the crown; AirTrain LOD2 trough walls; LOD2 checks in `verify_landside.py`. LOD2 has no parked cars by design (>= 1500 m: sub-pixel; `deck_far` carries the NAIP deck + car mean) |

**Requests to the drawings group** (the 3-D now carries these as `obs` / `osm` / `inf` round-1 items): the Garage A / G deck (still
[unk]; the l1 conflict is withdrawn), the Garage A station block on BL-03, the SFO BART station as a spec item and sheet, the RCC tower D 4.7 /
platform 8.0 (l5 solve), the drum towers, the central-garage roof rims / lobes / boxes.
### Review round 2 (5 Nov 2026): what changed, and why

New measurements are in `tools/blender/landside_r2_obs.json` (written by `tools/blender/landside_r2_measure.py`: photo a2 with its
SOLVED camera `out/buildings3d/itb_a2_camera.json`, i2 in level pitches, the l5 top-silhouette fit, NAIP 2024 rims / lobes); per finding
in `manifest.json#landside.review_r2`, with requests to the drawings group.

| # | Finding | Disposition | What the model does now (evidence) |
|---|---|---|---|
| 1 | Inter-track deck east of the Garage A station (656 m2) | fixed | Deck removed. A 1.6-m emergency walkway cantilevered from each single-track trough at the walkway level (0.25-m slab), a galvanised cable rail on its open edge (posts 1.5 m, top rail + 4 cables) [obs l1 for the camera's track; the other by symmetry, inf]; the strip between (227 m2) is open to grade. The SFO Museum "tail" polygon is a footprint at grade: its structure is listed [unk] |
| 2 | Garages A / G about 6 m too tall in a2 | fixed, re-measured (lower than the reviewer's estimate) | Near parapet edge found column by column on a2 and solved with the camera for the height of the outline's near top edge: **Garage A 29.1 m** (9 columns, 28.85-29.5), **Garage G 27.5 m** (4 columns). The a2 level rows (deep dark strips at 25.3 / 22.0 / 18.6 / 15.3 m, the same at every column over 270 px) give a **3.34-m pitch**: 9 levels [pub] with L1 at grade put the roof deck (Level 9) at 26.7 m - the penthouse base and the roof cars sit on that line in a2 - and Level 7 (AirTrain [pub]) at 20.0 m (network level 19.75). Drum ring 31.0 m (A; a2: the ring wall ~1.9 m over the parapet), towers parapet + 1.5. Garage G: Garage A's section scaled to its parapet [inf]. The a2 camera rests on the Grand Hyatt top 44 m [inf]: 40 / 48 m move these by -2.4 / +2.4 m. The reviewer's ~33 / 30-31 came from other columns (far parapet / rotunda); at x 415 the photo edge is y 398 against 338 for the 39.6-m render (-10.5 m). i2 agrees once its scale comes from the level pitch (tower windows and drum slots both 32 px per level; the tower 85 px = 8.9 m) instead of the drum width (5.7 px/m made the levels 5.6 m and the towers 15 m); drum slots now one per level below the ring. Conflict listed: the NAIP drum band (13.25 m east lean, BL-03 39.6 with the ITB pole k 0.334) implies k 0.43 here. Garage A station block top = the parapet (a2: nothing above the roof at the SE corner; NAIP: stalls over it); l1's door-cabin reading (31.75 m) is listed as a conflict. `landside_cmp_a2` now uses the solved camera (`render_landside.py --views a2 --itb --roadways`) |
| 3 | Garage A roof massing | fixed, location corrected | Rotunda D 16.5 m, top 36.5 m (a2: 94 px at 5.8 px/m, top rim against 32 / 34 / 36-m overlays; NAIP 2024 disc, lean-corrected) on the curved NE end: a2 looks SSW, so the photo's LEFT end of Garage A is its EAST end - the west end is the helix drum. The r1 4-m core cylinder over the ring is gone (a2 / i2: nothing rises above the ring; the NAIP dark disc is the helix eye -> a guard ring round a dark opening). Penthouse from a2: base on the deck, open braced storey to 29.6, solid to 36.0 m; plan = the NAIP box lean-corrected with the measured lean (west face at the deck height, east face at the top: 18 x 12 m; r1 shifted the whole imaged box, 24.6 m long) |
| 4 | Central-garage roof cars at random angles; soft lobes; flat station boxes | fixed | Each observed car snapped to the nearest free stall of the 117.8-deg layout within 3 m (stall position + orientation, ~15 % backed in [inf]); the rest keep their NAIP position with the yaw on the stall axis; NAIP colour kept (125 of 217 snapped). Rims / lobes re-contoured from the same NAIP masks blurred 1.2 / 3 px on a 4x grid (smooth curved edges); rim colour = median of the beige pixels. The T1 / T2 / T3 AirTrain stations get white barrel roofs (NAIP) like the Garage G vault |
| 5 | RCC tower rake / skin | fixed | Cut plane fitted to the l5 top silhouette (sky boundary per column, r1 l5 camera): rake 2.55 m, highest toward bearing 353 (toward the camera), rms 2.3 px (r1's 2.5 m toward 236: 74 px; a flat top: 89 px); the high point at the DOF top lifts the platform 0.84 m (RCC_PLATFORM 8.84). Skin alpha-blended (`perf_tower`: texture alpha 0.45, frame opaque, doubleSided) with a dark core, switch-back flights and landings inside, posts every 1/8 turn |
| 6 | BART band too high / thin | fixed (a2 solved camera) | Four columns (x 1100-1700): colonnade top 5.9, white spandrel to 9.2, green band 9.2-13.5, white to the 17.6-m top -> band 4.1 m below the top, 4.3 m tall; colonnade 5.9 (OSM min_height 4 listed) |
| 7 | Hyatt glass too light / flat | fixed | 4-pane x 3-floor tile with per-pane brightness / hue and a reflection gradient, deep cyan-blue (28, ~104, ~150), IOR 1.5 (the 1.9 coat mirrored the grey sky: red channel 3x the photo) |
| 8 | Curved NE end faceted | fixed | `landside_geom.smooth_arcs`: outline vertex runs that follow a circle (< 0.6 m) replaced by the fitted arc at 1.2-m chords (Garage A: drum + NE end; Garage G: 3 arcs); walls and screens on the arcs share vertices (smooth normals), the panels run on across the vertices (no inset, no end faces), mullions every 4.05 m of arc. The arcs may run up to the 0.6-m fit tolerance outside the outline's chords (the real wall is the curve; verify allows 0.6 m) |
| r2-self | Garage A station block over open track (seen in the r2 a2 render) | fixed | r1 had united the track strips with the body up to the NE end (u = Lb 150.8): a 16-m block over open track, east of the curved NE end where a2 shows the apron. The SFO Museum outline ends the body there at u 134.8 (south track) / 139.8 (north-track face): the strips stop there, the block's east faces are those outline faces and the tracks run in the open beside the NE end (l1: the curved NE wall stands east of the block face, nearer the camera); the l1 render camera moved with the face |
| 9 | LOD2 drops the void floor / Level-5 parts / cars; roofs jump | fixed | Central garage LOD2 keeps the void floor, the Level-5 garage edges beside the guideway (to the trough-wall top) and the two DOF roof poles; every deck has a LOD2 car impostor (one roof quad per car in its paint colour, COLOR_0); LTP 1 / 2, RCC, Hyatt, CAC and MOC LOD2 roofs at the LOD0 roof level inside a coping ring |

**Requests to the drawings group (r2):** the Garage A / G heights (BL-03 draws the NAIP drum ring 39.6 / 37.6; a2 gives parapet 29.1 / 27.5,
deck 26.7 / 25.3, 9 levels at 3.34 m, Garage A drum ring 31.0) and the NAIP-lean conflict behind them; the Garage A NE rotunda and
penthouse; the trough walkways east of the Garage A station and the open gap; the RCC tower rake and platform 8.84 m; the BART band /
colonnade.
<!-- landside:end -->

<!-- domestic:begin (tools/blender/build_domestic.py; numbers from out/buildings3d/domestic_verify.json / _verify_r1.json, 2026-11-05, review round 1) -->
## Domestic terminals: T1 Center, T2, T3 West / East and Boarding Areas B-F (key `domestic`, 5 Nov 2026)

```bash
flock out/.heavy.lock python3 tools/blender/build_domestic.py --final   # ~165 s: geometry, textures, AO bake (2 x 2048 + 1024), export, verification, manifest
python3 tools/blender/build_domestic.py --no-bake                       # quick WIP build -> out/buildings3d/wip/ (white occlusion)
python3 tools/blender/verify_domestic.py [glb] [--neighbours]           # 60 checks, reads the glb back (no bpy) -> out/buildings3d/domestic_verify.json
flock out/.heavy.lock python3 tools/blender/render_domestic.py --views a1,d1,bab,plan,bclose,eclose     # Cycles references, ~2 min at 48 spp
flock out/.heavy.lock python3 tools/blender/render_domestic.py --qa backface --views a1,bclose,eclose,d1,plan [--lod 1|2]   # back faces red
python3 tools/blender/dom_pv.py                                         # (re)measure the PV rack blocks on NAIP 2024 -> tools/blender/dom_pv.json
python3 tools/blender/dom_roofobs.py                                    # PV rack tables + rooftop units on NAIP 2024 -> tools/blender/dom_roofobs.json (review r1)
python3 tools/blender/dom_roofobs_qa.py [x0 z0 x1 z1 scale out.png]     # QA overlay of the units / tables on NAIP (local)
python3 tools/blender/verify_domestic_r1.py                             # the review-r1 probes (walkway gaps / clashes per LOD, LOD2 vs LOD0) -> out/buildings3d/domestic_verify_r1.json
flock out/.heavy.lock python3 tools/blender/render_domestic.py --views roof,c3c [--lod 2 --suffix _lod2]   # review-r1 close-ups
python3 tools/blender/dom_pv_r2.py                                      # review r2: the BA-E plate PV arrays dom_pv.py missed -> tools/blender/dom_pv_r2.json
python3 tools/blender/verify_domestic_r2.py [glb lod2_glb]              # review-r2 probes (IBF junction, app rotunda drums, C3C, BA-E, sign, BA-C / BA-D clearances) -> out/buildings3d/domestic_verify_r2.json
flock out/.heavy.lock python3 tools/blender/render_domestic.py --views a1,d1,c3c,eclose,ibf,bab,plan   # review-r2 set (d1 = solved camera, ibf = the T2 / IBF junction)
```

| File | Role |
|---|---|
| `tools/blender/dom_geom.py` | Geometry (numpy / shapely, no bpy). Imports `tools/buildings/draw_domestic.py` / `draw_data.py` (the sheets' functions and constants, not copies): footprints from the SFO Museum level-2 outlines, measured roof edges, BA-B band, BA-E section, BA-F hub / lantern / monitor, BA-D drums, T1 / T3 landside, bridge doors |
| `tools/blender/dom_mesh.py` | Mesh builder + extrusion / cap / box / tube primitives (faces wound outwards) |
| `tools/blender/dom_tex.py` | Our procedural tiles: normal maps (membrane laps, panel joints, curtain caps, corrugation, PV frames), curtain / frit / PV base colours |
| `tools/blender/dom_pv.py`, `dom_pv.json` | PV rack blocks measured on NAIP 2024 (extents only; numbers, never a texture) |
| `tools/blender/dom_roofobs.py`, `dom_roofobs.json` | review r1: the rack TABLES inside each PV block (rows with their aisles, local axis per sub-cell) and the rooftop units (compact dark objects with a shadow on their NNE side) on every deck, NAIP 2024 (numbers only); `dom_roofobs_qa.py` draws them on NAIP |
| `tools/blender/dom_pv_r2.py`, `dom_pv_r2.json` | review r2: the 8 PV arrays on the BA-E raised plate (484 m2) that `dom_pv.py` merged with the plate's edge shadow (NAIP 2024, numbers only); merged by `dom_geom.pv_blocks` |
| `tools/blender/verify_domestic_r2.py` | review r2: the T2 / tower base building (IBF) junction (wall bottoms, rays into the gap), the app's rotunda drums (scene2d.json cyl solids at four poses + the largest drum the app can draw) vs every domestic triangle in their band, C3C materials / penthouse, BA-E end-wall glazing share and plate PV, sign extents, BA-C / BA-D clearance numbers |
| `tools/blender/verify_domestic_r1.py` | review r1: the reviewer's physics probes re-implemented on the exported files (walkway gaps / clashes at 6.0 / 7.5 m per LOD from the app's `scene2d.json` hulls; LOD2 vs LOD0 top-height rasters and plan Hausdorff) |
| `tools/blender/build_domestic.py` | bpy build, NAIP roof-colour sampling, the T1 sign, AO bake, glTF export (WIP to `out/buildings3d/wip/`, `--final` copies to `data/`), manifest |
| `tools/blender/dom_manifest.py` | Manifest entry (per-dimension tags, inferred / unknown / not modelled / conflicts, budgets, renders) |
| `tools/blender/verify_domestic.py` | 60 checks against the sheets and the plausibility rules, measured on the exported mesh (top-surface probe) |
| `tools/blender/render_domestic.py` | Cycles references of the exported glb (+ tower / ITB assets for context), AO and back-face QA modes |
| `data/buildings3d/domestic.glb` (11.1 MB), `domestic_lod2.glb` | The asset; the LOD2 subtree alone for the far / phone tier |

**Placement.** Root `domestic` at world (−896.5, 3.0, 336.5) (centre of the complex bbox, GROUND_Y). LOD0 / LOD1 hold one node
per building and kind (`L<k>_<bld>_shell / _detail / _fins / _pv`, `extras.building` in T1, BA_B, BA_C, T2, C3C, BA_D, T3W, T3E,
BA_E, BA_F; the `_fins` nodes carry `extras.max_dist_m` 160: `js/three/buildings3d.js` hides them beyond, review r1),
each recentred on its own plan bbox: the complex spans ~1.3 km, so **choose the LOD per building** from the camera distance to
that node (switch 380 / 1300 m). LOD2 is one joined node.

### What is modelled, and from what (tags per dimension in `manifest.json#domestic.dimensions`)

| Part | Source | Notes |
|---|---|---|
| Pier / hall footprints | obs | SFO Museum level-2 outlines; bridge-head fingers and the fixed-walkway strips at the BA-B tip are left to the app's bridges; the tower base building and the ITB are excluded (0 m²) |
| Roof edges | obs | measured lean-free lines (`dom_true_edges`): BA-B ESE +2.27 / WNW −1.66 m, BA-D +2.40 / −1.36, BA-F +1.83 / −1.15 (see conflicts), BA-E WNW −2.0; continuous along each side (gaps at the finger roots closed, limited to the offset band) |
| Heights (roof edge = coping top) | obs / inf / unk | BA-B 13.14 / band 19.04, BA-C 7.20, BA-D 8.49, BA-E 12.85 / flanks 9.85, BA-F 10.49, T3W parapet 16.76, T3E 14.48, penthouse 21.34; **T1 17.88 and T2 16.88 are placeholders [unk]** (curb 4.88 [unk] + the BD-03 heights) |
| BA-B | obs / inf / unk | raised clerestory band s −391.0 / −423.4, t −1236..−946 (glazed both sides, low-E); 3 planted roof wells (depth 3 m [unk]), 2 bridges, 2 skylight grids, PV fields (NAIP); electrochromic gate glazing [pub] |
| BA-E | obs / inf | raised PV plate 12.85 with its edge 1.5 m over the recessed clerestory, flanks 4.4 m at 9.85; the tip end bay (8 m) with the glazed end wall recessed 1.5 m under the plate (photo a1) [inf]; review r2: the end wall glazed from 2.0 m (dark base below; photo a1 profile, 83 % of the wall) [obs low] and the plate PV completed from NAIP (`dom_pv_r2.json`: tops 269 -> 753 m2) |
| BA-F | obs / inf / unk | arms + octagonal hub on the outline; eccentric lantern 19.4 m as a minimal 1.0-m glazed upstand [unk] (the NAIP 2020 shadow only bounds the rise, <= 4.6 m: kept in the manifest; review r1); NW-arm monitor +2.5 m [unk] |
| Courtyard 3 Connector office block (review r1 / r2) | pub / obs / inf | the glazed block between the tower and BA-E in photo a1: the T2 outline's NW end west of the line through its two outline jogs (1,971 m2) [obs]; "Above the connector, a six-story office building", "Dynamic glazing", 124,000 sq ft (HOK) [pub]; 33.0 m [inf, range 32-36: >= 6 x 3.8 m + the ~10.5-m connector head; NAIP 2024 relief 12.9 m / lean 0.379 = 34.0 m; photo a1 ~35 m]; review r2: six 3.8-m office storeys from 10.2 m of storey-height panes with STAGGERED mullions (pane widths 1.2-4.5 m, a new sequence per storey), very dark green glass, light frames (`glass_c3c`, 24 x 22.8 m tile, no fins) [rhythm / colour obs photo a1, widths inf]; rooftop penthouse 22.5 x 26 m to 38.0 m with a dark louvre band on its NNE wall [obs low: photo a1 23-77 % of the face, NAIP 2024 imaged wall band 5.7 m]; the 8 C3C PV tables stand on it; node building `C3C` |
| Rooftop units (review r1) | obs / inf | 31 boxes on 9 decks at their NAIP 2024 extents (`dom_roofobs.json`: compact dark objects 4-150 m2 with a shadow on the NNE side), heights 1.5 / 2.2 / 3.0 m by plan size [inf]; LOD2 keeps those >= 15 m2 |
| PV (review r1) | obs / inf | discrete rack tables (rows / tables with their aisles) inside every NAIP block, 0.35-0.75 m above the deck, modules in the PV tiles; LOD2 the clipped table tops (the old LOD2 minimum rectangles overhung the curved T3 edges) |
| BA-D | obs / inf | head with two drums D 19.2 m to 13.19 m [inf top]; linear skylights; ESE overhang notched at the doors (roof soffit 7.69 m < walkway head 8.4 m) |
| T1 Center | pub / obs / inf / unk | landside face on the measured roof edge (trimmed curb line − 4.0 m); clear glass under a 4.0-m glass canopy (brackets), two-tier green fritted wall with dark irregular mullions and the tier transom (photo d1), sign "Harvey Milk Terminal / Terminal 1" with the circled flagged 1 [obs text; review r2: sizes / heights measured on photo d1 with its solved camera - line 1 1.41 x 14.0 m at 14.03 m, line 2 cap 0.79 m, disc 1.10 m at 12.10 m; near-black; Liberation Sans Bold x 0.93 (OFL; the real typeface inf)]; PV fan (NAIP); 3 skylights |
| T3 | pub / inf | T3W airside window stack 10 + 2 + 10 ft above L3 [pub]; T3W landside ACM / fritted window wall / spandrel [pub materials, proportions inf]; T3E grey-frit glass / platinum panels; T3E penthouse (corrugated, accent bands) |
| Facades elsewhere | inf / unk | service band 0–4.6 m, dark spandrel, concourse glazing from 5.4–5.6 m (the bridge floor), panel above; mullion fins every 1.5 m (LOD0) |
| Tower base building junction (review r2) | inf | T2 / BA-D / T1 cut 0.3 m off the IBF outline; their walls facing it full height (blank panel, no fins); a coping flashing over the gap at min(top, 13.03 m = the lowest family's IBF roof 13.13 - 0.10, manifest.json#tower anchors) with a 0.15-m joint at the IBF wall (clear of its 0.12-m mullions) |
| App rotunda drums (review r2) | inf | every facade within the largest drum the app can draw (gates.js: max(1.5, min(2.45, rotunda_max_r - 0.25)) around the data rotunda) + 0.1 m is notched (B10, D4, D5, D14-D16, E6, E9, E11; roofs notched where their underside is below the drum top); door surrounds / vestibules / bulkheads near a drum clipped or left out |
| Bridge attachment | inf | at all 80 attach points of `data/sfo_stands.json` (B–F, incl. the 5 BA-B pod bridges since review r1): a door surround (jambs + head around the 2.6 × 3.0 m walkway section, LOD0) and a dark leaf; 63 vestibules (max 2.6 m) from the facade to the app's walkway start; 23 bulkheads where the roof edge is below the walkway head (BA-C / BA-D), reaching 0.5 m past the walkway start inside the facade with the deck cut under them; **vestibules, notches and bulkheads at every LOD** (review r1) |
| Elevated sky-bridge / connector parts | unk / inf | the app's convention 6.0–10.5 m; the two BA-B parts that the B10 / B11 / B11S / B15 / B16 walkways enter come down to 4.9 m (the vestibule floor: the walkway runs 5.15-8.45 m) [inf, review r1] |

### Budget, textures, AO

| LOD | switch | triangles | draw calls | content |
|---|---|---|---|---|
| 0 | < 380 m | 78,143 (r2) | 150 | everything: mullion fins (~48k tris, own `_fins` nodes, `max_dist_m` 160), door surrounds, PV table boxes, units, canopy brackets, sign |
| 1 | 380–1300 m | 23,715 (r2) | 117 | the LOD0 shell meshes and atlases; PV table tops only; no fins / frames |
| 2 | > 1300 m | 23,535 (r2) | 21 | one joined node: the LOD0 outlines, wells, skylights, coping recess, units >= 15 m2, PV table tops, vestibules / notches / bulkheads (review r1: the phone tier sees it up close); reduced palette, own 1024 atlas; also `domestic_lod2.glb` |

Textures (PNG, embedded): AO atlases S (T1 / BA-B / BA-C / T2 / C3C) and N (BA-D / T3 / BA-E / BA-F) 2048² (1.35 / 1.31 MB, 8-bit
greyscale), L2 1024² (0.47 MB); 48 spp, 10-m rays, ground plane, neighbours as occluders, white outside the islands; tiling
normal maps 512² (membrane, panels, curtain, T3W window wall, corrugation, PV) and base colours 512² (4 curtain glasses, grey
frit, green frit, T3W, PV, lobby glass) and the BA-B electrochromic tile 1024 x 256 (24 x 6 m, per-pane tint states, review r1) with its caps normal map, 1.5–24 kB each. Roofs: NAIP 2024 median per building; the white membranes saturate, so the base colour
is capped at sRGB 215 (aged single-ply reflectance ~0.65–0.70) [inf]. Glass coated (IOR 1.9 → F0 0.096, as the ITB / tower), the
T1 frit uncoated (F0 0.04, rougher: the ceramic frit dominates). Single-sided; no TANGENT. KTX2 / meshopt: later
(`tools/engine/glb_compress.mjs`).

### Verification (verify_domestic.py: 60 checks, 0 failed; tolerance 0.5 m or 2 %)

- Placement exact. Every roof edge (median of 16–302 probes on the top surface 0.12 m inside the roof outline): deviation 0.000 m
  (incl. the C3C 33.00 m over 44 probes and the BA-F lantern 11.49 m).
- BA-B (28 stations every 10 m): band edges max 0.05 / 0.10 m; outer roof edges (t < −1150, the stretch of the measured lines and
  the BD-02 typical section) 0.10 / 0.11 m; widths 7.35 / 32.2 / 14.69 / 54.24 m vs 7.3 / 32.4 / 14.7 / 54.3.
- Measured roof-edge lines: BA-B, BA-D, BA-F within 0.15 m at every station; BA-F NE arm 27.15 m vs 27.0 (BD-02).
- BA-E (13 sections): plate 12.85, flanks 9.85, widths 42.8 / 37.0 vs 42.9 / 37.1. BA-F lantern 20.90 vs 21.00 m across the
  corners; BA-D drums r 9.57 vs 9.6.
- T3W window stack L3 10.36 / 13.41 / 14.02 m (0.003 m); T1 fritted tiers 8.88–17.08, canopy soffit 8.88, canopy depth 4.0.
- **Plausibility.** Nearest B–F stand envelope (app planforms, all accepted types) 2.93 m from the 3-D footprint (F12; criterion
  ≥ 2.0); bridge walkways beyond the attachment (app-drawn part, 4.8–8.7 m band) 0.0 m² of contact with the asset (83 bridges);
  SFO Museum taxiways 0 m²; tower base building 0 m²; ITB 0.02 m²; AirTrain guideway 0 m². INFO: the first 1.5 m beyond the
  facade touch the door surrounds / the facade where the stand data meets the outline at an angle (81 bridges, 29.6 m² total,
  e.g. C9, D14), as in the ITB rotunda contacts. 80 doors (54 vestibules > 0.12 m, max 2.6 m; 23 bulkheads).
- Khronos glTF-Validator 2.0.0-dev.3.10: **0 errors** on both files (domestic.glb: 92 warnings MESH_PRIMITIVE_GENERATED_TANGENT_SPACE,
  accepted as for the ITB: no TANGENT attribute by choice; 53 infos UNUSED_OBJECT; domestic_lod2.glb 0 warnings).
- Neighbouring assets (`verify_domestic.py --neighbours`, LOD0 triangles whose height ranges overlap): landside 0 m², tower
  0 m², ITB 0.77 m² (slivers along the shared T1 / T3W – ITB core boundary, ~1 cm; no shared volume); the C3C is 41.9 m from the
  nearest landside triangle.
- **Review-r1 probes** (`verify_domestic_r1.py`, the app's walkway hulls from `out/buildings3d/integ/draw/scene2d.json`, 83 B–F
  bridges; the four second doors F11 / F13 / F15 / F22 whose walkway branches off door 1's bridge are not facade attachments):
  walkways ending > 0.5 m from the building at 6.0 / 7.5 m: LOD0 5 -> **0**, LOD2 30 -> **0** (max 0.02 m; B19 1.42, E4 1.25, E13
  1.16, B18 1.06, B21 1.06, E6 0.98, B17 0.83 m -> 0.00, the reviewer's values reproduced). Walkway / rotunda hulls vs triangles in
  their height band: B10 5.57 -> 0.14 m², D6 / D7 at LOD2 7.73 / 8.33 -> 0.14 / 0.17 m², C4 1.96 -> 1.01, D15 3.76 -> < 0.98; the
  rest (<= 2.32 m², B16 / B11) is the 4.9-m pod / vestibule floor inside the box the probe draws for a SLOPED walkway (hull y
  4.1-8.45 m: its floor is 5.15 m at the building end) and the facade crossing (~0.27 m² per bridge). LOD2 vs LOD0 (1-m top
  rasters): |dz| > 0.5 m over 11,866 -> **161 m²** (the units < 15 m² LOD2 leaves out), > 2.5 m 1,477 -> 0, the T3E / T3W strips
  roofed at PV height 92 / 110 cells -> 0; plan Hausdorff 8.19 -> **0.05 m**, symmetric difference 1,596 -> 0 m².
- Back-face QA (Cycles, single-sided, without the neighbouring assets): 0 red pixels in bclose / d1 (LOD0) and plan (LOD2), roof
  1 px; a1 127 px (LOD0 and LOD2) and eclose 201 px: the T1 – BA-A connector (`T1_walk23`) whose walls along the ITB core
  boundary are left to the ITB asset (seen open only when the ITB is not loaded; the pre-r1 QA counted 49 / 85 px there - the
  connector's exposed walls are unchanged, 324.6 m² before and after the r1 occupancy change); c3c 259 px (LOD0, LOD2 258;
  the pre-r1 asset 432 px in the same view): slits along the BA-E stepped section and the T3E penthouse base, pre-existing.
- Render check (orthographic BA-B section, `domestic_render_check.json`, 0.1 m/px): band edges −0.13 / +0.17 m, heights +0.13 m
  (pixel); the outer WNW silhouette −1.6 m comes from the tip's end walls (t < −1236), not the typical stretch.

### Renders and self-review (out/buildings3d/, local; comparison sheets hold photo pixels and stay local)

| View | Compared with | Reading |
|---|---|---|
| `domestic_a1.png`, `_cmp_a1` | photo a1 (camera solved from 3 points, 60 m, 36.5 mm) | tower, BA-D head with the drums, T2 behind, BA-E with its PV plate and glazed tip fall where the photo has them; missing: aircraft, bridges, apron, the C3C office building and landside (other assets / not in the sheets) |
| `domestic_d1.png`, `_cmp_d1` | photo d1 (camera solved in review r2), BD-03 view 1 | green fritted two-tier wall with dark irregular mullions and the transom, sign with the circled 1, glass canopy, clear glass below: reads as the T1 Center landside; the curb roadway in front is not part of this asset |
| `domestic_bab.png`, `_cmp_bab` | BD-02 view 1 | stepped section: clerestory band 19.04 over the 13.14 outer roof, ESE overhang, door surrounds at the concourse level |
| `domestic_plan.png` | BD-01 / NAIP | PV fan on T1, BA-B wells / PV / skylights, BA-F hub and lantern, T3E penthouse |
| `domestic_bclose.png`, `domestic_eclose.png` | photo a1 detail | BA-B band, PV tables, skylight grid, electrochromic gate glazing in mixed tint states; BA-E plate overhanging the clerestory, the recessed glazed end |
| `domestic_roof.png` (+ `_lod2`) | NAIP 2024 (`dom_roofobs_qa.png`) | review r1: T1 Center east roof: PV rack tables in rows with aisles, two rooftop units, skylights; LOD2 the same tops |
| `domestic_ibf.png` | review r2 | the T2 / tower base building junction from above the IBF roof (tower asset in context): T2 wall full height behind the IBF parapet, flashing with its joint |
| `domestic_c3c.png` (+ `_lod2`) | photo a1 | review r1: the C3C glazed block standing ~16 m above the T2 roof, PV / units on its roof, T2 units; in `_cmp_a1` it falls at x 545-620 px (photo 527-601) with its top at the photo's |

### Review round 1 (5 Nov 2026): dispositions (numbers from `domestic_verify_r1.json`, before -> after)

| # | Finding | Disposition | Evidence after the fix |
|---|---|---|---|
| 1 major | roofs flat and empty apart from PV; the Courtyard 3 Connector missing | **fixed**: C3C office block (33.0 m, footprint and height sources in the table above); 31 NAIP-measured rooftop units (541 m2) on 9 decks (`dom_roofobs.py`: compact dark objects 4-150 m2 with a measurable shadow; the strict shadow test was needed because most dark objects on these roofs are PV fields that `dom_pv.py` did not catch); the t1 photo's units at the tower foot (2015) are not resolved in NAIP 2024 and are not modelled | `domestic_c3c.png`, `domestic_roof.png`, `domestic_cmp_a1.png`; QA overlay `out/buildings3d/dom_roofobs_qa.png` |
| 2 minor | PV blobs with one texture | **fixed**: 303 discrete rack tables (19,547 m² inside the 29,212 m² of NAIP blocks: rows / tables with their aisles, local axis per sub-cell so the T1 / T3 fans keep their radial rows; the block area between tables is membrane) | `domestic_roof.png`; tables on NAIP: `dom_roofobs_qa.png` |
| 3 minor | BA-B facade a uniform near-black band; fins alias | **fixed (unverified)**: electrochromic panes in four tint states on a 24 x 6 m tile (no 6-m repeat); fins in their own `_fins` nodes with `extras.max_dist_m` 160, hidden beyond by `js/three/buildings3d.js` (4 added lines); no openly licensed BA-B photo found (Commons API search / categories, 5 Nov 2026), so the look stays [inf] | `domestic_bclose.png` |
| 4 minor | T1 clear glass black under the canopy; canopy a dark line | **fixed**: `glass_lobby` (the lit hall seen through, sRGB 112 / 120 / 122, as the ITB `glass_hall`); the canopy light uncoated laminated glass (188 / 200 / 200, rough 0.3) | `domestic_cmp_d1.png` |
| 5 major | LOD2 without vestibules / notches / bulkheads: walkways float, C walkways above the roof, D walkways / drums through the eave | **fixed**: the bridge attachment is emitted at every LOD; bulkheads reach 0.5 m past the walkway start inside the facade with the deck cut under them | LOD2 walkways > 0.5 m from the building 30 -> 0 (max 0.02 m); D6 / D7 eave + drum overlaps 7.73 / 8.33 -> 0.14 / 0.17 m² (the facade crossing); C walkways: bulkheads at LOD2 (C4 1.96 -> 1.01 m², the coping inside its closed bulkhead) |
| 6 major | the app walkways (5.15-8.45 m) run into the 6.0-m floor of the BA-B elevated parts (B10 5.65 m2 ...) | **fixed**: the two parts these walkways enter come down to 4.9 m (and their walls with them: the walk style's first band starts at the part's underside), door surrounds added there (80 doors) | B10 5.57 -> 0.14 m², B15 2.35 -> 0.14, B11S 1.51 -> 0.14; B16 / B11 2.32 / 1.72: the probe's box of the sloped walkway, see Verification; walkway-to-building gaps 9-24 m -> 0 |
| 7 minor | BA-F lantern at its 4.6-m upper bound | **fixed**: 1.0-m glazed upstand [unk], the bound kept in the manifest (`dimensions`, range 0-4.6); top 11.49 m | `verify_domestic.py` heights |
| 8 minor | LOD2 outlines / roofs differ from LOD0 by > tolerance | **fixed**: LOD2 keeps the LOD0 outlines (no 1-m simplification), wells, skylights, coping recess; PV table tops clipped to the deck | plan Hausdorff 8.19 -> 0.05 m; |dz| > 0.5 m 11,866 -> 161 m² (small units); T3 strips 0 |

Self-review of the new renders: the back-face QA of the c3c view showed a 0.6-m slot where a lower deck meets a taller neighbour
(the lower solid's coping ring is cut there, but the neighbour's wall only started at the lower ROOF EDGE, not its deck): the
occupancy used for the wall clipping now ends at the deck, so the taller wall comes down to it at every such junction (T2 / C3C,
T1 / piers, bands, links).

### Review round 2 (5 Nov 2026): dispositions (`verify_domestic_r2.py`, before -> after; `manifest.json#domestic.review_r2`)

| # | Finding | Disposition | Evidence after the fix |
|---|---|---|---|
| 1 major | C3C a tiled cube of 3-m mottled blue panes; penthouse missing | **fixed**: six 3.8-m storeys of storey-height panes, staggered mullions, very dark green glass (sRGB 26/40/35 from the photo median), light frames, subtle per-pane variation (±4 %), own tile + normal map, no fins; connector levels below (tinted concourse band, dark band at the office floor); penthouse to 38.0 m with the louvre band [obs low: photo a1 + the NAIP 2024 wall band FWHM 2.5 m / lean 0.438 = 5.7 m above the deck]; the C3C PV tables (all 8 inside it) moved onto it | `domestic_c3c.png`, `domestic_a1.png`; probe: glass_c3c 10.2-32.2 m, coping top 38.0, louvre present |
| 2 minor | BA-E end wall glazed in its upper 55 % only; plate PV 4-5 rectangles | **fixed**: end wall glazed from 2.0 m (photo a1 profile at the end wall: glass 746-790 px of a 736-~802-px wall); 8 NAIP arrays added (`dom_pv_r2.py`: the WNW row `dom_pv.py` had merged with the plate edge shadow) | glass share 0.535 -> **0.834**; plate PV tops 269 -> **753 m2**; `domestic_eclose.png`, QA overlay `dom_pv_r2_E_centre.png` |
| 3 / 6 minor | walls at the IBF clipped up to 14.07 m (the F1 roof): 0.24-m slot above the F2 parapet + a 0.35-m crack into T2 | **fixed**: the walls facing the IBF are emitted full height (blank panel, 0.3 m off it); a coping flashing over the gap at min(top, 13.03 m) - the LOWEST family's IBF roof (manifest.json#tower) less 0.10 - with a 0.15-m joint at the IBF wall; T1 / BA-D walk part treated alike | lowest wall bottom near the IBF 14.07 -> **0.0 m**; rays into the gap 272 of 272 open -> **0 open** (LOD0 / LOD2); neighbours vs tower.glb **0 m2**; `domestic_ibf.png` (tower in context) |
| 4 minor | circled "1" a bar, thin grey letters; d1 camera above the roof edge | **fixed**: Liberation Sans Bold (flagged 1), near-black, sizes / heights from the photo; the d1 camera **solved** (`render_domestic.D1_SOLVE`): the glass-head, transom and canopy lines meet at x 9031 / 9379 / 8683, y 520-533 -> horizon 525 px; the camera is 5.83 m above the canopy line, 2.8 m below the roof edge (15.06 m in the model frame; f 2657 px from the AirTrain guideway distance [inf]) | `domestic_cmp_d1.png` (local): facade top, canopy and sign fall where the photo has them; no roof strip. Note: the photo shows PV rows ABOVE the coping although its camera is below it - the T1 roof rises behind the landside edge (unknown, listed) |
| 5 major | BA-C / BA-D roofs below the app's 5.4-m concourse; bulkheads 1.0-1.5 m proud | **open, tagged** (manifest conflict "BA-C / BA-D roofs vs the app concourse floor", status open, with the numbers): BA-C deck 6.6 (0.4 m clear under a 0.8-m roof structure), BA-D 7.89 (1.69 m); 9 / 14 bulkheads to 8.70 / 9.49 m. Photo a1 (ratios, camera-independent) at the BA-D near end: the concourse glazing spans 0.44-0.79 of the roof-edge height and the walkways enter at that band with ~one walkway height of facade above them: with the measured 8.49 m the BA-D concourse sits near 3.5-3.8 m, ~1.5-2 m below the app floor (the roof would have to be 10.7-11.7 m to keep 5.4) | **request to the bridges / realtime owners**: a per-pier departure level for BA-C / BA-D (~3.5-4.0 m, verified against photos); domestic then drops the bulkheads and moves the glazing to the photo ratios |
| 7 minor | C3C / roof equipment only in 3-D | **fixed (recorded)**: `manifest.json#domestic.deviations_from_sheets` (10 items: C3C + penthouse, units, PV tables, BA-E end wall, lantern, pod parts, bridge attachment, IBF junction, T1 face, sign); the BD sheets belong to the drawings group | manifest |
| 8 minor | E9 drum 0.32 m inside BA_E (F8 / F7 / E3 contacts) | **fixed**: facades notched around the largest drum the app can draw (+0.1 m) at 9 stands, door parts near drums clipped / left out | scene2d drums (4 poses): 20 contacts / 4 conflicts (F8 0.40 m2, **E9 0.39 m2 at 0.32 m**, F7 0.24, E3 0.21) -> **0 / 0**; max-radius drums 13 / 10 -> **0 / 0**; LOD2 12 / 0 -> 0 / 0 |

Round status: `data/buildings3d/integration.json` (b3d_integrate.py, 16:35Z) lists **2** open conflicts, not 0: the E9 drum vs
BA_E (fixed here; it clears when the integration owner re-runs `tools/blender/b3d_integrate.py`) and the BART-station taxilane
OFA (landside asset). Re-verified after the r2 build: `verify_domestic.py` 60 checks, 0 failed; `verify_domestic_r2.py` 0 failed;
r1 probes unchanged (walkway gaps max 0.02 m; LOD2 vs LOD0 Hausdorff 0.03 m after closing zero-area seam rings in the probe);
neighbours landside 0 / tower 0 / ITB 0.82 m2 (the ~1-cm core slivers); glTF-Validator 0 errors (96 tangent warnings by
choice); back faces unchanged (a1 127, c3c 258, eclose 204, d1 0, ibf 0 px).

### Open items (also in the manifest's `unknown` / `conflicts`)
- T1 Center and T2 hall heights and the departures-curb height (placeholders); the T3 datum; the BA-B well depth; the BA-F lantern
  (1.0 m modelled, bound 4.6) and monitor rises; the C3C height (33.0, range 32-36) and its roof penthouse (photo a1, not in NAIP);
  rooftop unit heights / types and the units NAIP 2024 does not resolve; the T3W state (95 % CD massing, without the May 2026 storey).
  (The C3C penthouse is modelled since review r2.)
- BA-B facade: no openly licensed reference photo found (Commons, 5 Nov 2026): the EC tint states are [inf].
- **Conflict for the drawings group:** BA-F ESE roof edge — the drawn line is 1.83 m outside the outline along the face (BD-02
  draws 27.0 m between the lines); the spec / README note "on the outline" was measured at the line ends only. The asset follows
  the drawn line.
- **Open plausibility conflict (review r2 #5):** BA-C / BA-D roofs below the app's 5.4-m concourse (bulkheads every LOD, BA-D
  overhang notches) - request to the bridges / realtime owners for a per-pier departure level (photo a1: ~3.5-4.0 m at BA-D). The
  BA-B pod parts that bridges enter come down to 4.9 m [inf] (the app's convention 6.0 m elsewhere); F22's second door attaches to
  door 1's bridge (app side).
- The drum notches follow the data rotunda centres (gates.js `rotShift` is 0 today): a future rotunda shift needs a rebuild.
- The T1 Center roof profile (photo d1 sees PV above the coping from below it) and the C3C penthouse height (38.0 m, +-1 m).
- Not modelled: courtyard links over the roadways / across the guideway, the curb roadways, T3W penthouses, rooftop equipment that
  NAIP 2024 does not resolve, interiors.
- Integration: `js/three/buildings3d.js` (per-building LOD; since review r1 it also hides nodes beyond `extras.max_dist_m`).
<!-- domestic:end -->

<!-- integration:begin (tools/blender/b3d_integrate.py, js/three/buildings3d.js; 5 Nov 2026) -->
---------------------------------------------------------------------------------------------------------------------

## Integration into the three.js app (key `integration`, 5 Nov 2026)

```bash
python3 tools/buildings/draw.py                 # 2-D sheets first (38 s, clean: only dates / clip ids changed, BD-01 profile, BX-01)
python3 tools/blender/build_roadways.py          # ~2 min: the elevated roadways asset (review round 1; reads the other GLBs)
python3 tools/blender/b3d_integrate.py          # ~4 min: footprints from the GLBs, replacement table, plausibility, manifest key
python3 tools/blender/b3d_lod2_check.py         # ~3 min: LOD2 vs LOD0 per building
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
| `tools/blender/b3d_views_job.mjs` | livetest job: the same views with `?b3d=0` (first-pass) and the assets -> `out/buildings3d/cmp_*.png`; in `near` mode each view waits until the full files near the camera are on screen (`Buildings3D.settled`) |
| `tools/blender/build_roadways.py`, `roadways_net.py` | the elevated landside roadways asset (`roadways.glb`, `roadways_lod2.glb`, check sheet `out/buildings3d/roadways_plan.png`, `manifest.json#roadways`; review round 1) |
| `tools/blender/b3d_lod2_check.py` | every building's LOD2 against its own LOD0 on the exported GLBs (plan, height, roof) -> `out/buildings3d/integ/lod2_check.json` |
| hooks | `js/three/renderer3.js` (+5 lines), `js/live/world.js` (+import, +2 items loops), `js/live/airport.js` / `js/live/terminals.js` (optional routing parameter; same geometry, same order), `tools/build3/three-entry.js` (+GLTFLoader), `tools/build3/phone_artifact*` (ships the GLBs), `tools/stands/check_stands.py` and `tools/drawing/common.py` / `audit.py` (use the 3-D footprints) |

**Loading.** `Renderer3._buildStatic` starts `Buildings3D` once the static scene exists; the five groups load one after
another (tower, ITB, domestic, roadways, landside: one decode / upload / program compile at a time, `compileAsync` over every
LOD before the group is shown, so a LOD switch later does not stall). Until a group is on screen, or if its file fails, the
first-pass extrusions stay: the scene never has a hole. Tiers (review round 1, finding 5): high / ultra load the full files
(LOD0-2); the low tier (phones) and the medium tier use `near` mode: the `*_lod2.glb` files first (5.9 MB together, the
whole airport at once), then a group's full file as soon as the camera comes within that group's LOD2 switch distance
(x the tier's range, + 10 % + 60 m) of one of its LOD2 subtrees, one file at a time; the full file replaces the lod2 one
(its GPU data released), so the units near the camera show LOD0 / LOD1 as on the desktop. `?b3d=0` shows the first-pass
buildings only, `?b3d=lod2|full|near` forces a mode, `?b3dtower=f1` the tower's alternative height family F1 (`tower_f1.glb`; manifest `family_decided: false`;
F2 `tower.glb` is the default since the tower review round 1, see the tower section), `?b3donly=tower,...` loads only the
listed groups (QA).

**LOD.** As each group's manifest says: a "LOD set" is a node whose children are LOD0 / LOD1 / LOD2 (tower, ITB, domestic:
the root; landside: every building node). LOD2 (one joined mesh with its own small atlas) is shown when the camera is beyond
the LOD2 switch distance from the set's bounding box; nearer, LOD0 or LOD1 per unit: domestic per building
(`extras.building`), ITB per part (the group spans 650 m), tower and each landside building as a whole. Distances are to the
unit's bounding box (the nearest point; a 400-m pier seen from its tip is near), 5 % hysteresis, and the switch distances
(extras `switch_m`) are scaled by the tier's `lod` range relative to the high tier (ultra 2.2x, medium 0.72x, low 0.56x:
phones show LOD0 within ~195-250 m and LOD2 beyond ~670-890 m). Within a unit and LOD, the static meshes of one material are
merged at load (`_mergeUnit`; instanced cars, fading fins, the LED / obstruction-light nodes, the cab glass and transparent
materials stay apart): landside LOD0 286 -> 189 primitives, LOD1 258 -> 161, tower 30 -> 23 / 23 -> 18; the ITB and domestic
units already hold one mesh per material (no change).

**Materials, AO, shadows.** The glTF PBR materials are used as exported (MeshStandard / MeshPhysical with
`KHR_materials_ior` / `_specular`), converted to node materials the way three does it internally, so an emission term can be
added. The baked AO (`occlusionTexture`, TEXCOORD_1) is the material's `aoMap` (ambient / IBL term only); GTAO adds the
screen-space contact term on top as for every object. The AO atlases are single-channel data: they are repacked at load into
R8 textures (`RedFormat`, mipmapped), capped at the tier's `maxTex` (low 1024, medium 2048), and the decoded RGBA bitmaps are
released (review round 1, finding 10): decoded texture memory of the full set 200 -> 90 MB (66 MB with the 1024 cap; lod2
set 36 -> 26 MB). Every opaque mesh casts and receives shadows (CSM); the alpha-blended
cab glass does not cast. Tiling normal / base-colour tiles get the tier's anisotropy.

**Night hooks (for the environment work).** Emission = the material's own + `nightE` (renderer3: night factor x LAMP_M) x
`glow[kind].color` x a soft-capped level `cap x (1 - exp(-k x lvl / cap))` (cap 0.42 lamp units, about 0.9 exposed at the
keyed night exposure, every kind but the beacon), with `lvl` an interior pattern standing for the lit hall behind the glass
(review round 1, finding 2): per 3 m x 4 m cell a level 0.6-1.25, a gradient up each 4-m storey (0.72 at the floor ..
1.08 under the ceiling lamps), masked to the panes where the glass has a base-colour tile (frames and frit stay dark). Kinds from the assets' own material names and extras: `hall` (terminal glazing, the
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

The app's tower view (`js/live/app.js`: `world.towerPos`, height `towerPos.eyeY`, GROUND_Y + 62 before a tower file is
shown) moves to the loaded tower file's cab eye: the loader reads the anchors from the file's root extras (`userData.anchors`),
so F2 (`tower.glb`, `tower_lod2.glb`) puts the eye at GROUND_Y + 59.15 = 62.15 and F1 (`tower_f1.glb`) at 65.2 (tower review
round 1: the fixed GROUND_Y + 62 sat in the F2 roof fascia). Inside that family's glass ring (`glass_head_r` + 0.3, cab floor
- 0.5 .. glass head + 0.5) the alpha-blended glass is hidden (it would darken the whole view); from outside it is drawn.

**Physical plausibility of the integrated set** (`integration.json#plausibility`; every LOD of every file, unsimplified
footprints; the bullets below are the first run of 5 Nov 03:00-04:45Z - the review round 1 checks and their results are in
"Review round 1" at the end of this section):
- Aircraft envelopes (every accepted type at every one of the 108 stands, `tools/stands/geom.py stand_env`, the envelope
  `check_stands.py` tests): **0 conflicts** (overlap > 0.5 m2 or < 2.0 m). Notes (< 3.5 m): F12 2.91 m (SFO Museum outline
  2.81 m), F17 3.15 m (outline 3.38 m: BA-F's measured roof edge, 0.23 m nearer). Next: G7 5.2, F5 5.5, E4 / F9 6.6 m.
- Jet bridges (128, incl. 3 upper deck): docked and stowed tunnel + cab beyond 3 m of the rotunda vs every footprint, fixed
  walkway + rotunda vs other buildings: **0 conflicts**. (Review round 1, finding 6: this never tested the walkway and drum
  against their own building, and skipped the LOD2 joined units: added, see the round-1 section.)
- Taxiways: no footprint inside an SFO Museum taxiway polygon; nearest taxiway centreline 27.0 m (BA-F), then 38 m. (The
  12.3-m note threshold was half of 81 ft twice over - finding 7; replaced by the per-lane ADG distance, round-1 section.)
- Assets against each other, per 2-m height band on the triangles: largest core overlap 0.6 m2 (ITB hall / guideway tile
  at the ITB, band 16-18 m; below the 2 m2 note threshold); tower / T2, ITB / T1 / T3W: coplanar shared walls only.
- What stays of the first-pass buildings (walkway rests, the kept walkway, kept ramp-level edges) against the assets in
  its own height band: 0 m2.
- `tools/sat/check.py` / `check_bridges.py` (one run; `check_stands.py` now unions the 3-D footprints into the aircraft-
  envelope test, `B3D_FOOTPRINTS=0` for the outlines only): ISSUES 0 before and after, WARNINGS 17 both, APP ISSUES 0; the
  only change is the F17 note (3.4 -> 3.2 m).
- Re-run after the 04:31Z container restart (04:45Z, inputs and GLBs unchanged: `integration.json` file hashes match):
  `b3d_integrate.py --check` 0 conflicts / 6 notes and `check.py` / `check_bridges.py` ISSUES 0 / WARNINGS 17, identical
  to the reports above.
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
without the tower's alternative family file `tower_f1.glb`; `B3D=all+alt` adds it). A test build from the working tree: 218 files, 59.0 MB (the GLBs 36.8 MB; limits: 15 MB per
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
- **Draw calls x 1.8-3.2** (shadow cascades and the depth / normal pre-pass multiply the meshes): 949-2,512 per frame at
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
- The tower camera follows the loaded family's `cab_eye_h` (tower review round 1; one-line hook in app.js:
  `tower.eyeY || GROUND_Y + 62`).
- Ground physics: the 3-D footprints are not in `ground.js buildingGrid` yet (above); the realtime owner's call.
- KTX2 / meshopt compression (`tools/engine/glb_compress.mjs`) is still a later step: it needs the KTX2 transcoder and the
  meshopt decoder in the vendored bundle and the artifact (WASM policy unverified, engine.md 5).

### Elevated landside roadways (key `roadways`, integration review round 1, 5 Nov 2026)

```bash
python3 tools/blender/build_roadways.py     # ~2 min: network + levels (roadways_net.py), clash trimming against the other
                                            # assets' triangles, columns, GLB (LOD0-2 + roadways_lod2.glb), check sheet,
                                            # manifest.json#roadways; then b3d_integrate.py (the roadways are a group there)
```

Finding 1 ("none of the elevated roadways exist in 3-D ... nobody owns this"): the integration step owns them. The 2-D check
sheet comes first (`out/buildings3d/roadways_plan.png`, BR-01: plan on dimmed NAIP 2024 with the deck levels and columns,
and the deck / soffit profiles of the two anchored structures), drawn from the same pieces the 3-D export uses.

| What | From what | Tag |
|---|---|---|
| network | OSM ways (pinned extract of 2026-09-26, ODbL) with their node topology; the selection of `tools/build_landside.py` (bridge / layer >= 1), only ids the app keeps as elevated in `data/sfo_landside.json`, without the 6 ways that run inside a landside building (garage ramps: that asset's) | obs |
| widths | OSM lanes x 3.6 m or the class default (`w_src`), + 0.6 m shoulders | osm / inf |
| ITB departures deck | the layer-2 loop along the ITB west wall at `spec_itb.json level3.floor` 11.5 m (+-1.5 m) less a 0.15 m kerb = 11.35 m | inf |
| domestic departures loop | OSM `Departures` layer-1 ways within 60 m of the domestic asset at its curb, `manifest.json#domestic` "departures curb above the apron (T1 / T2)" 4.877 m less the kerb = 4.73 m | unk (the domestic placeholder) |
| other levels | one screened solve over the elevated ways and the at-grade roads touching them (`roadways_net.solve_levels`): layer prior 6.5 / 12.5 / 18.5 m (Caltrans HDM 309.2 15-ft clearance + ~1.5-1.9 m structure, recalled), ELL 100 m; the at-grade way leaving a bridge end pulled to grade with ELL_G 45 m (it becomes the approach ramp on fill), all other at-grade roads held at grade; crossings (no shared node) get clearance constraints: deck over deck / deck over road >= 1.2 + 4.6 m (the upper deck is raised; anchored levels kept), deck under the AirTrain guideway <= guideway soffit - 4.6 m (soffit measured on the landside asset's triangles) | inf |
| structure | deck 1.2 m deep, concrete barriers 0.40 x 0.85 m on the outer edges, solid fill where the deck top is below 3.2 m, round columns D 1.4 m at ~30 m, each placed only where it stands clear of at-grade carriageways (+0.3 m), lower decks and every asset (tried on the centreline, across the deck and +-6 m along; else omitted) | inf |
| clash trimming | every ribbon minus the other assets' occupancy in its own height band (12-m chunks): the ITB L3 curb sidewalk, the domestic curb decks, garage walls, AirTrain columns; same-level overlaps (merges) go to the higher-priority ribbon | - |
| surface | asphalt: NAIP 2024 median over the deck tops (sRGB 213, 210, 202) x 0.57 linear (the NAIP-to-albedo factor of the integration note) -> 166, 163, 157; own lane-marking tiles (MUTCD 3A.06 10-ft dashes on 40-ft cycles, yellow left edge on one-way roads); concrete 172, 170, 163 | obs colour / inf |

Results (`out/buildings3d/roadways_build.json`, `roadways_build.log`): 147 elevated OSM ways, 109 kept (32 outside the app's
landside / airside clip, 6 inside landside buildings); 6,447 level nodes, 224 anchored, 152 crossing nodes, 38 under the
guideway, 65 clearance constraints, **0 unresolved, 0 crossings below 4.6 m**; 43 at-grade roads lifted into approach ramps;
built inside the terminal-core box x -2150..-550, z -50..1050 (115 pieces in 9 units: `itb_departures`,
`domestic_departures`, 7 `interchange_*`; 38 pieces / 5.8 km beyond it - the US 101 / I-380 ramps 1-2 km away - keep their
ground footprint as before); 481 m2 trimmed against assets (ITB 6, domestic 85, landside 300 - the landside buildings count
as solids: a ramp that runs into a garage ends at its facade); 295 of 332 column positions placed; LOD0 / 1 / 2 46.7k /
14.4k / 6.9k triangles, `roadways.glb` 4.34 MB, `roadways_lod2.glb` 0.44 MB (built against the landside round-1 GLB of
16:18Z). Steep: 12 decks
above 8 % (in the core box at most 12.1 %, the short motorway links west of the ITB that must clear the at-grade roads under
them; the US 101 side 13.2 %) and 7 ramps - reported, not hidden. Below the domestic loop the soffit is 3.53 m over the
arrivals roads: the domestic curb placeholder [unk], kept as the domestic asset has it (manifest `deviations`).
Plausibility in `b3d_integrate.py` (the roadways are a group: elevated, so tested by their triangles in each height band;
not in the ground physics, aircraft never reach them): no aircraft envelope, bridge or taxiway conflict; against the other
assets no core overlap in any 2-m band (the first build had 4.3 m2 where an ITB approach ramp ran into the rebuilt Garage G
between two of its floors: fixed by the solid trimming above).

### Review round 1 (5 Nov 2026): dispositions

| # | Finding | Disposition | Evidence |
|---|---|---|---|
| 1 | elevated roadways missing (major) | **fixed**: new asset `roadways.glb` owned by the integration step (above), loaded as a fifth group | BR-01 sheet; renders `out/buildings3d/integ/r3/high/cmp_new_itbwest.png` (the viaducts between Garages A and G, the ITB L3 loop) and `cmp_new_i3like.png` (from the ITB departures deck at the i3 camera: curb sidewalk, upstand, canopy hangers, the loop curving away); `cmp_new_domcurb.png` missed its target (a camera inside the T1 canopy zone) and is not evidence |
| 2 | night glow: white cards on the piers (major) | **fixed** (levels and pattern): every glow kind but the beacon soft-capped at 0.42 lamp units, hall 0.8 -> 0.30, office 0.9 -> 0.34, station 0.9 -> 0.32, roof glass 0.35 -> 0.14, soffit 0.35 -> 0.22, LED 1.0 -> 0.30; per 3 x 4 m cell levels 0.6-1.25 and a storey gradient 0.72 -> 1.08. **Not done**: a glow along a concourse band on BA-A / BA-G - the ITB asset has no glazing there ("no continuous concourse window band on BA-G: a2 shows none on the pier", manifest.json#itb), and lighting metal panels would invent windows | `out/buildings3d/integ/r3/night/cmp_new_itbnight.png`, `cmp_new_pierAnight.png` (b3donly without the landside, whose garages stay first-pass there): pixels above L 235 10,732 -> 727 and components >= 60 px 29 -> 2 in the itbnight view (r2 vs r3); on BA-A at A9 no component above 235, the gate-room panes L 155-199 (p10-p90), max 231 |
| 3 | white slab at the ITB west wall (minor) | **fixed**: it was the first-pass ramp-level wall (terminal complex ring 2, edges 46-50, 64 m, G..G+5) 4.1-5.6 m in front of the ITB asset, just beyond the 3-m edge buffer; new gap rule: an uncovered edge next to a group's edges and within 8 m of that group goes to it (10 edges in all: ITB 5, domestic 5) | `integration.js replace.gap_edges`; `cmp_new_itbwest.png` |
| 4 | parked cars: 2 shapes, no wheels (minor) | **routed to the landside group** (not fixed here): the cars are made by `tools/blender/landside_cars.py` and exported by `build_landside.py`, both the landside group's, whose round-1 rebuild was queued on the heavy lock during this work; the request (wheels / skirt at LOD0, a third shape, the black / grey paint with metallic 0.4 -> a clear-coat dielectric) is in manifest.json#integration.requests | - |
| 5 | phones show LOD2 everywhere (critical) | **fixed**: low and medium tiers use `near` mode (Loading, above); LOD2 now appears on a phone only beyond ~670-890 m. LOD2 checked against LOD0 per building: `tools/blender/b3d_lod2_check.py` -> `out/buildings3d/integ/lod2_check.json` (47 units; against the landside round-1 GLB of 14:52Z 4 flagged: domestic BA_C (LOD2 1.5 m beyond LOD0, top +9 m: a C3C triangle split to BA_C - to check), ITB BA-G top -5.0 m (the pod-3 box not in LOD2), landside Central Garage top -5.1 m and RCC roof median 4.6 m; the first run, on the landside GLB of 02:10Z, had flagged 9 incl. every garage roof); `b3d_integrate.py` now tests the LOD2 meshes split per building (below) | `out/buildings3d/integ/r3/low2/cmp_new_*.png` (near) vs `cmp_lod2_*.png` (the old phone behaviour) at gate B20, the tower cab and the tower look (low tier, landside left out: see the renders note) |
| 6 | plausibility never tested walkway / drum vs host; LOD2 joined units skipped (major) | **fixed**: (b') walkway and drum against their own building at every LOD and pose, on the app's own bridge solids (`scene2d.json` of 03:56Z; the facade crossing allowed within 2.5 m of the attach point; CONFLICT > 0.3 m2 and > 0.10 m deep), (d) with the joined LOD2 meshes split per building (domestic's `building: 'all'` included). Result: 393 tests, **1 conflict** - drum E9: 0.39 m2 of BA_E surfaces 0.32 m inside the drum (current pose, LOD0) - and 1 note (F8 drum 0.40 m2 touching, depth 0.00); B10 walkways and the D6 / D7 drums in the LOD2 eave the reviewer found are clear after the domestic round-1 rebuild (domestic.glb 10:54Z); asset pairs with LOD2 included: no core overlap in any band (the domestic-ITB 8 m2 is gone with that rebuild) | `integration.json#plausibility.stats.walkway_drum_vs_host`, `asset_pairs`; requests: domestic (E9) |
| 7 | taxilane threshold halved twice (minor) | **fixed**: distance per lane design group (AC 150/5300-13A Table 4-1 taxilane centreline to object: ADG III 24.7 / IV 34.3 / V 42.1 m), a lane's ADG = the largest wingspan among the stands whose envelope is within 45 m of it (inferred: no SFO taxilane design-group source here). Notes: BA-F 27.1 m to lane 9 (ADG V, needs 42.1 m), BA-G 38.6 m and the guideway 38.1 m to lane 302 (ADG V): in each case the SFO Museum geometry is as close (27.3 / 37.3 m) - existing condition, not the assets; the real lanes are likely restricted (not verified). **1 conflict**: the BART station of the landside round-1 rebuild is 36.7 m from lane 302, 0.6 m nearer than the SFO Museum structure (within that outline's +-5 m accuracy; reported to the landside group) | `integration.json#plausibility.stats.taxilane_clearance` |
| 8 | app collision data from first-pass outlines (minor) | **partly fixed**: `integration.js` now carries `physics.rings` (26 asset footprints, hangars / guideway / roadways out) and `js/live/app.js` passes them to `ground.js buildingGrid` (additive third parameter): off-stand aircraft now avoid the measured roof edges. **Not done**: `gates.js prepGeom` from the asset facades (walkway start / drum limits) - that changes every bridge and the bridges group's verification while it closes out; requested, with the vestibule removal (domestic) after it. The F10 CRJ2 1.40 m from BA-F (SFO Museum outline 1.43 m) is a stand-pose item (stands) | requests in manifest.json#integration |
| 9 | phone artifact ships full GLBs near the 15-MB limit (minor) | **changed premise / fixed limit**: phones now load the full files near the camera, so the artifact keeps them (B3D=all); any file >= 14 MB is split into 12-MB pieces (`<name>.part<i>.wasm`, `window.SFO_B3D_PARTS`) and joined by the loader. Needed at once: the landside round-1 rebuilds (12:52Z, 14:52Z) made `landside.glb` 19.6 / 20.3 MB, which the old per-file assert would have refused (2 pieces now). Full set 43.7 MB + lod2 5.9 MB (without tower_f1): with the rest of the artifact over the 64-MB single-publish limit, so it goes up in two publishes (as phone_artifact.sh already says) | `tools/build3/phone_artifact_page.py` |
| 10 | desktop budget: RGBA AO, draw calls, medium tier (minor) | **fixed**: AO repacked as R8 (200 -> 90 MB decoded, 66 MB at the 1024 cap); per-unit per-material merge (landside 286 -> 189 / 258 -> 161, tower 30 -> 23 / 23 -> 18 primitives; ITB / domestic already one mesh per material); medium tier in `near` mode | `integ/r3/*/cmp_info.json` |


**Renders, review round 1** (`out/buildings3d/integ/r3/`, live3.html headless on llvmpipe, 960 x 540; the machine was shared
by three other workflows, so program compiles took 2-18 min per group and two runs hit their time limit: the views below are
the ones that completed; the comparison sheets with photo pixels stay local):

| View | Tier / files | Draw calls / triangles / textures | What it shows |
|---|---|---|---|
| `high/cmp_new_itbwest.png` | high, all five groups | 2,848 / 6.19 M / 1,171 MB (r1: 2,512 / 5.82 M / 1,273 MB) | the viaducts and ramps between Garages A and G and the ITB L3 loop; the 64-m white slab at the ITB west wall is gone |
| `high/cmp_new_i3like.png` | high | 1,679 / 3.98 M / 1,176 MB | from the ITB departures deck at the i3 camera: curb sidewalk and upstand, canopy hangers, the loop curving away |
| `night/cmp_new_itbnight.png`, `cmp_new_pierAnight.png` | high, landside first-pass | 976 / 3.57 M; 450 / 2.33 M | the capped glow (numbers in the table above) |
| `night/cmp_new_pierA.png` | high | 858 / 3.39 M | BA-A by day at A9 (reference for the night view) |
| `low2/cmp_new_{pierB,towercam,tower}.png` vs `cmp_lod2_*` | low (phone), landside left out | near: 346-535 / 1.6-2.3 M / 573-590 MB, units at LOD0 / 1: 5 / 36 (B20), 8 / 33 (tower); lod2: 330-537 / 548-559 MB, every unit at LOD2 | near mode puts LOD0 / LOD1 on screen at the gate and tower views for +25-31 MB of textures; the domestic and tower LOD2 meshes are close to LOD0 at these distances after their round-1 rebuilds, the ITB and landside ones are not (b3d_lod2_check) |

Textures fell by ~100 MB at the high tier (1,273 -> 1,171 MB with a fifth group added: the R8 AO atlases); draw calls rose
with the roadways (+9 units, ~31 primitives at LOD0 x the shadow / pre-pass multiplier) where they are in view. Not
re-rendered here: the garage / t4-like car view (finding 4 routed to the landside group).

<!-- integration:end -->
