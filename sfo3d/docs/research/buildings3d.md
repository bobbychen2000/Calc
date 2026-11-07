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

### Close-out round 3 (6-7 Nov 2026): dispositions (`manifest.json#itb.closeout_r3`)

Rebuilt 2026-11-07 01:55Z (`out/buildings3d/c3/itb_build_c3.log`): verify_itb **125 checks, 0 failed** in the build; the
standalone re-run with the corrected canopy check (below) **126 / 0** (`out/buildings3d/c3/verify_itb_c3.log`). 6.46 MB,
tris LOD0 69,287 / LOD1 36,927 / LOD2 5,336 (unchanged).

| id | Finding | Disposition | Evidence (before -> after) |
|---|---|---|---|
| buildings-7 | curb canopy 4.52 m over the departures plate (87 m2 below 4.6 m) | **fixed** | `CANOPY_THK` 0.6 -> 0.45 m [inf] under the unchanged observed / drawn top (16.5 m): soffit 15.9 -> 16.05 m. New verify check "curb canopy soffit over the roadway plate" (the roadways.glb LOD0 deck triangles under the 5-m canopy plan): **4.70 m** (>= 4.6; the integration's point sample of the same spot: 4.52 -> 4.67). The first version of this check built the canopy plan with `Buv` (the Blender-local frame) instead of `UVw` (world x, z): its polygon was degenerate and the check never ran (125 checks in the build log) - fixed, 126 checks. BI-02 / BI-03 draw the 0.45-m slab (`draw_itb.r3_hall`). Request R3.6: confirm in the integration's plausibility notes. |
| buildings-6 | clear centre bay (glass_hall) vs the frit; app ratio never measured after the final material | **partly** (fix 2, verifier v10: was 'fixed'): app = photo under the photo's light; Cycles 0.86 unchanged (renderer difference, recorded) | App render after the final material, high tier, look view = i4like, the west facade SUNLIT as in photo i4 (`?t=2026-09-23T23:15:00Z`: sun az 241.2 / el 31.5, `out/buildings3d/c3/appB1/c3_i4sun.png`, camera + sun logged by `tools/blender/c3_app_views_job.mjs`): centre / side bay **0.69** (mirror bays 0.688; centre 139 / side 202), photo i4 **~0.7**. The 0.418 of the snapshot-time render (06:21Z, `appA_high`) is the facade in shade - a different light, not comparable with the sunlit photo. Cycles at the estimated photo sun 0.86 (`itb_i4_c3.png`, 169 / 198; unchanged from r2); at the app's sun 0.84 (`itb_i4_c3sun.png`, sun az 241.2 / el 31.5 = the app's: 164 / 196) - at the same sun Cycles reads the clear bay ~0.15 lighter than the app (its path-traced sky / ground reflections on the opaque IOR-1.5 proxy; the app's IBL is filtered and has no SSR on this view). glass_hall is kept (IOR 1.5, base 100 / 110 / 116): the app is the deliverable and matches the photo; darkening it toward a Cycles 0.7 drives the app down (base 60 / 68 / 74: app 0.32 in r2). Matt letters: near-black in the sunlit app view (no specular lobe). |
| buildings-10 | BI-02 / BI-03 / BI-04 behind the 3-D state | **partly** (fix 2, verifier v5: was 'fixed'): BI-02 / BI-03 view 1 drawn; BI-03 / BI-04 still draw the old roof_line and the flat lens glazing (the 3-D state only in their 3-D STATE notes) | `draw_itb.r3_hall` draws the 3-D centre deck / fascia (roof_line - crown_cap: 38.50 m at the crown), the lens vaults and the 0.45-m canopy slab on BI-02 view 1 and BI-03 view 1; `r3_notes` states every `itb.deviations_from_sheets` item on its sheet (BI-01 items on BI-04) with size and tag. |
| buildings-12 (ITB) | core 17.9 m placeholder, L3 11.5 m, BA-A pod 23.6 vs DOF 25.91; BA-G mullion finish (engine R2.4) | **partly** | `spec_itb.json` `ba_g.mullion_finish`: light silver-white mullions / transoms [obs photo a2, Commons CC BY-SA 4.0, low, unverified] - BA-G only; the asset's `mullion` is light aluminium (178 / 182 / 186, metallic 0.6) already. No new source for the core height, L3 or the BA-A pod top (values stay tagged). |
| buildings-1 (ITB) | round-2 fixes never independently checked; app render after the final material missing | **done** | i4 Cycles comparison (`itb_cmp_i4.png`): lattice with the X per panel, dark soffit with white outriggers, near-black letters, dark crown over the notch-to-notch span - all as fixed in r2; the app render above closes the "app after the final material" doubt. |

### Close-out round 3, fix round 2 (7 Nov 2026; `manifest.json#itb.closeout_r3_fix2`)

Rebuilt 13:16Z (`out/buildings3d/c3f2/itb_build.log`): verify_itb **126 checks, 0 failed**. Geometry unchanged (tris 69,287 /
36,927 / 5,336); 6.46 MB.

| id | Finding | Disposition | Evidence (before -> after) |
|---|---|---|---|
| v8 | ITB glass carried the baked AO as glTF occlusion while domestic glass did not | **fixed** | ONE rule for all four assets: no glTF occlusion on a glass material (`build_itb.make_material`; the AO image stays only as the bake target). three.js applies `aoMap` to the indirect diffuse and, through its specular occlusion, to the IBL reflection that makes glass read; Cycles ignores the glTF occlusion. Glass materials with occlusion 18 -> **0** (itb_lod2 0 of 8). App i4, sunlit, high tier, same camera and sun as close-out r3 (`out/buildings3d/c3f2/appB1/c3_i4sun.png`): clear centre bay / frit side bay 0.690 -> **0.700** (mirror 0.688 -> 0.700); photo i4 ~0.7. |
| v6 | BA-G bump-out conflict still open; walkway table from the 5 Nov scene2d (tops 8.45 m) | **fixed** | `verify_itb` takes the walkways from `tools/blender/app_bridges.json` (gates.js run in Node; stale inputs = FAIL). Against DEPARTURE_LEVELS.G 2.7 [obs a2, low], 0 of 45 A / G walkways top above their host roof. The 20 BA-G walkways that dock into a bump-out top at 5.71-5.87 m, under the 6.5-m bump-out roofs (min margin 0.63 m). The 4 at G12 / G13 have no bump-out and top at 6.16-7.29 m under the 16.0-m pier roof. Conflict resolved; the record text now separates the two cases. |
| v9 | canopy clearance from the parameter | **fixed** | Measured on the exported canopy faces over the roadways.glb LOD0 deck faces (560 overlaps): **4.70 m** (>= 4.6); the parameter value is reported beside it. |
| v10 | buildings-6 recorded as fixed | **partly** | App 0.70 = photo i4 ~0.7 under the photo's light; Cycles 0.86 (photo sun) / 0.84 (app sun) unchanged - a renderer difference. glass_hall is not tuned toward Cycles, so that the app (the deliverable) stays at the photo. |
| v5 | BI-03 / BI-04 draw the old roof_line and flat lens glazing | **partly** (recorded) | The 3-D state is drawn on BI-02 / BI-03 view 1 (`draw_itb.r3_hall`). BI-03 / BI-04 keep roof_line(u) (crown 40.1) and the flat `lens_poly` glazing, and state every `itb.deviations_from_sheets` item in their 3-D STATE notes. |

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

**Close-out round 3 (7 Nov 2026; `manifest.json#tower.closeout_r3`).** No geometry change. buildings-13 (height family) stays
with the owner: F2 (rim 64.0, observation-anchored) is the default, F1 (rim 67.36 = 221 ft, CTBUH class) the hypothesis; both
files re-verified 2026-11-07, `tools/blender/tower3d_verify.py` 110 / 110 (F2) and 110 / 110 (F1)
(`out/buildings3d/c3/tower_verify_f{1,2}_c3.log`). buildings-1 (round-2 fixes): `tower_compare_t2.jpg` shows the slots as mid-grey
louvre recesses and the cab glass as one uniform dark tint, as fixed; the t3 (overcast) cab glass stays lighter than the photo
(render 15-16 vs photo 3-33; t2, the primary evidence, matches) - a light-condition deviation, recorded, not reopened.

**Close-out round 3, fix round 2 (7 Nov 2026; `manifest.json#tower.closeout_r3_fix2`).** v8: one glass AO rule for all four
assets - `build_tower.wire_ao` no longer links the baked AO as glTF occlusion on a glass material. Glass materials with
occlusion 3 -> **0** (ibf_glass_dark, ribbon_glass, slot_glass) in tower.glb, tower_f1.glb and tower_lod2.glb. Rebuilt 13:22Z
with `--no-manifest`, so this section and the close-out records are kept; `manifest.json#tower.bytes` / `verification` were
patched. tower3d_verify **110 / 110** (F2 and F1), glTF-Validator 0 errors, geometry unchanged (F2 tris 34,789 / 10,783 /
2,461); F2 3.46 -> 3.44 MB.
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
| `tools/blender/verify_landside.py`, `render_landside.py` | 192 checks on the exported glb; Cycles references with the sheet lines drawn over them; back-face QA |
| `data/buildings3d/landside.glb` (21.0 MB), `landside_lod2.glb` (2.85 MB) | The asset; the LOD2 subtrees alone (far / phone tier) |

**Layout.** Root `landside` at world (0, 3.0, 0); one child per building / AirTrain tile at its own origin (`origin_world_xz`
in the node extras), each with `LOD0_*` / `LOD1_*` / `LOD2_*` children: switch 0 / 450 / 1500 m **from that building node**
(the group spans 2.4 x 2.8 km, so one root LOD would not work). LOD0 / LOD1 share the shell meshes and their AO atlas
(A 2048 px: the six parking structures; B 2048 px: the other buildings and the AirTrain); LOD2 = one joined node per building
with atlas C (1024 px). Parked cars: 1,737 instances, one node per deck x shape x colour with `EXT_mesh_gpu_instancing`
(one material, paint / glass / skirt in COLOR_0), under LOD0 and LOD1.

| LOD | triangles (non-instanced) | instanced car triangles | draw calls (all buildings) |
|---|---|---|---|
| 0 | 159.7k | 93.6k | 363 (12 car groups per deck) |
| 1 | 85.0k | 65.9k | 323 |
| 2 | 21.7k (incl. the r2 car impostors, one quad per car) | none | 122 (`landside_lod2.glb`: 2.85 MB) |

### What is modelled, and from what (per-dimension tags in the node extras and `manifest.json#landside.buildings`)

| Building | Plan | Heights | Facade / detail |
|---|---|---|---|
| Central garage | SFO Museum outline with the 58.9-m void [obs]; the AirTrain ring and T1 / T2 / T3 station polygons cut out above Level 5, garage structure under them to the guideway deck | parapet 81 ft = 24.69 [pub, definition unk]; deck 23.62 [inf]; levels = equal fifths, Level 5 = 19.75 [unk, BL-03]; rooftop boxes deck + 4.5 / + 2.0 [inf] | open levels (3-m dark recess, spandrels, piers 9 m [inf]); the void's level lines rise one pitch per turn (helix); roof: NAIP-traced beige rims (0.15 m) and stall-free lobes, 11 stair / elevator / plant boxes [obs NAIP plan]; roof light poles at the two DOF points 30.8 / 33.2 [pub]; 344 cars: 217 at their NAIP positions [obs] (r2: 125 snapped to the nearest free stall within 3 m, the rest yawed onto the stall axis) + 127 white / silver beside them [inf] |
| Garages A / G | outline up to the body end Lb 150.8 / 149.8 [obs]; drum = outline arc (R 16.2 / 15.2, fit residual < 0.6) [obs]; stair / elevator towers 8 x 8 m at both drum ends [obs NAIP / i2, size inf]; Garage A: the guideway strips inside the body, portals at the west face and the station-block back wall; Garage G: guideway cut out | r2 (photo a2, solved camera): parapet 29.1 / 27.5, deck (Level 9) 26.7 / 25.3, 9 levels at 3.34 / 3.16 m, drum ring 31.0 / 29.4, towers parapet + 1.5 [obs a2 / i2, low; +-2.4 m with the Hyatt pick]; helix eye a guard ring (no core above the ring); Garage A penthouse to 36.0 (open storey to 29.6) and NE rotunda D 16.5 to 36.5 [obs a2 / NAIP, low]; Garage A station block to the parapet, its east faces at the outline's SE corner (u 134.8 / 139.8) [obs outline / a2; l1 reading 31.75 = conflict] (r1: drum ring 39.6 / 37.6) | full-bay perforated screen panels between thin mullions over the lower 62 % of each level [obs l1]; drum in smooth metal panels with five long slots + an open top band, recessed 0.8 m [obs i2]; white precast towers with small square windows [obs i2]; Garage A station block: two long slots, open hall over the tracks and to the south on round columns [obs l1]; 92 / 77 cars [obs NAIP density] |
| LTP 1 / LTP 2 | outlines [obs] | LTP 1 parapet 16.5 [obs shadow], towers to the DOF tops 26.2 / 27.7 [pub, form inf]; LTP 2 deck 60 ft [inf], levels 12 ft [pub], PV canopies at deck + 3.5 [unk] | precast / exposed frame; PV rows over the stall modules [pub, layout inf]; 276 / 318 cars |
| Rental Car Center | outline [obs]; west wall = the outline between RCC_N and RCC_S | roof outline 54 ft [pub DOF]; 59-ft element at its DOF point [pub, form inf]; platform 8.84 [obs l5 camera solve + r2 top-silhouette fit, low] (r1: 8.0) | west wall per photo l5: board-formed concrete, ribbon windows at the platform, band, canted louvre screen (1.2 m lean [inf]) with blades every 0.2 m [obs l5]; 626 cars in nose-to-tail lanes [obs NAIP] |
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
inside the sheet's own [inf] range 18.3-21.0 m; the RCC platform at 8.84 m (round 2: + 0.84 m from the raked-top fit; round 1: 8.0, the photo-l5 camera solved from the tower,
the guideway vanishing point and the horizon; the DOF TANK top 8.6 m above an eye 1.7 m above the platform; was 5.8 [inf] with the
BL-02 tower D 6.5, which puts the l5 camera inside the RCC) instead of 12.35 m. Also: the Superbay spine-end facets fall
to the cantilever-root level (BL-02 plan) rather than to the tip level (BL-03 V4 line, which would leave an 11-m step).

### Verification (verify_landside.py on the exported glb: 192 checks, 0 failed; tolerance 0.5 m or 2 %)
- Placement of all 24 nodes exact (0.01 m; round 1 adds `bart_station`); root at GROUND_Y.
- Heights = the sheet values to < 0.01 m: CG 24.69 / deck 23.62 / poles 33.2, 30.8; Garages A / G (r2, a2 solved camera - deviations
  from BL-03): parapet 29.1 / 27.5, ring 31.0 / 29.4, deck 26.7 / 25.3, penthouse 36.0, rotunda 36.5; LTP 1 16.5, towers 27.7 / 26.2; LTP 2 18.29 / 19.36 / PV 21.79; RCC 16.46, 59-ft element 17.98; Hyatt 44.0,
  podium 10.67, penthouse 48.67; CAC 18.29 / 19.51; Superbay spine 41.15, root 39.65, tips 27.0 / 28.5, door head 24.0; MOC
  40.2 / 35.7 / 35.4; RCC tower 18.3, D 4.70 (round 1: SFO Museum polygon lobe; BL-02 E draws 6.5 [inf]), platform 8.84 (r2), top raked 2.55 m, high side toward 353 deg.
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
| 1 | Inter-track deck east of the Garage A station (656 m2) | fixed | Deck removed. A 1.6-m emergency walkway cantilevered from each single-track trough at the walkway level (0.25-m slab), a galvanised cable rail on its open edge (posts 1.5 m, top rail + 4 cables) [obs l1 for the camera's track; the other by symmetry, inf]; the strip between (300 m2 left open in the tail polygon, verify: > 200 m2) is open to grade. The SFO Museum "tail" polygon is a footprint at grade: its structure is listed [unk] |
| 2 | Garages A / G about 6 m too tall in a2 | fixed, re-measured (lower than the reviewer's estimate) | Near parapet edge found column by column on a2 and solved with the camera for the height of the outline's near top edge: **Garage A 29.1 m** (9 columns, 28.85-29.5), **Garage G 27.5 m** (4 columns). The a2 level rows (deep dark strips at 25.3 / 22.0 / 18.6 / 15.3 m, the same at every column over 270 px) give a **3.34-m pitch**: 9 levels [pub] with L1 at grade put the roof deck (Level 9) at 26.7 m - the penthouse base and the roof cars sit on that line in a2 - and Level 7 (AirTrain [pub]) at 20.0 m (network level 19.75). Drum ring 31.0 m (A; a2: the ring wall ~1.9 m over the parapet), towers parapet + 1.5. Garage G: Garage A's section scaled to its parapet [inf]. The a2 camera rests on the Grand Hyatt top 44 m [inf]: 40 / 48 m move these by -2.4 / +2.4 m. The reviewer's ~33 / 30-31 came from other columns (far parapet / rotunda); at x 415 the photo edge is y 398 against 338 for the 39.6-m render (-10.5 m). i2 agrees once its scale comes from the level pitch (tower windows and drum slots both 32 px per level; the tower 85 px = 8.9 m) instead of the drum width (5.7 px/m made the levels 5.6 m and the towers 15 m); drum slots now one per level below the ring. Conflict listed: the NAIP drum band (13.25 m east lean, BL-03 39.6 with the ITB pole k 0.334) implies k 0.43 here. Garage A station block top = the parapet (a2: nothing above the roof at the SE corner; NAIP: stalls over it); l1's door-cabin reading (31.75 m) is listed as a conflict. `landside_cmp_a2` now uses the solved camera (`render_landside.py --views a2 --itb --roadways`) |
| 3 | Garage A roof massing | fixed, location corrected | Rotunda D 16.5 m, top 36.5 m (a2: 94 px at 5.8 px/m, top rim against 32 / 34 / 36-m overlays; NAIP 2024 disc, lean-corrected) on the curved NE end: a2 looks SSW, so the photo's LEFT end of Garage A is its EAST end - the west end is the helix drum. The r1 4-m core cylinder over the ring is gone (a2 / i2: nothing rises above the ring; the NAIP dark disc is the helix eye -> a guard ring round a dark opening). Penthouse from a2: base on the deck, open braced storey to 29.6, solid to 36.0 m; plan = the NAIP box lean-corrected with the measured lean (west face at the deck height, east face at the top: 18 x 12 m; r1 shifted the whole imaged box, 24.6 m long) |
| 4 | Central-garage roof cars at random angles; soft lobes; flat station boxes | fixed | Each observed car snapped to the nearest free stall of the 117.8-deg layout within 3 m (stall position + orientation, ~15 % backed in [inf]); the rest keep their NAIP position with the yaw on the stall axis; NAIP colour kept (125 of 217 snapped). Rims / lobes re-contoured from the same NAIP masks blurred 1.2 / 3 px on a 4x grid (smooth curved edges); rim colour = median of the beige pixels. The T1 / T2 / T3 AirTrain stations get white barrel roofs (NAIP) like the Garage G vault |
| 5 | RCC tower rake / skin | fixed | Cut plane fitted to the l5 top silhouette (sky boundary per column, r1 l5 camera): rake 2.55 m, highest toward bearing 353 (toward the camera), rms 2.3 px (r1's 2.5 m toward 236: 74 px; a flat top: 89 px); the high point at the DOF top lifts the platform 0.84 m (RCC_PLATFORM 8.84). Skin alpha-blended (`perf_tower`: expanded-metal diamonds 0.19 x 0.09 m [inf] - strands opaque, openings alpha 0.5, mean ~0.75 -, frame opaque, doubleSided, metallic 0.25 / roughness 0.80; a uniform alpha 0.45 with roughness 0.55 read as glass in the first r2 render) with a dark core, switch-back flights and landings inside, posts every 1/8 turn |
| 6 | BART band too high / thin | fixed (a2 solved camera) | Four columns (x 1100-1700): colonnade top 5.9, white spandrel to 9.2, green band 9.2-13.5, white to the 17.6-m top -> band 4.1 m below the top, 4.3 m tall; colonnade 5.9 (OSM min_height 4 listed) |
| 7 | Hyatt glass too light / flat | fixed | 4-pane x 3-floor tile with per-pane brightness / hue and a reflection gradient, deep cyan-blue (28, ~104, ~150), IOR 1.5 (the 1.9 coat mirrored the grey sky: red channel 3x the photo) |
| 8 | Curved NE end faceted | fixed | `landside_geom.smooth_arcs`: outline vertex runs that follow a circle (< 0.6 m) replaced by the fitted arc at 1.2-m chords (Garage A: drum + NE end; Garage G: 3 arcs); walls and screens on the arcs share vertices (smooth normals), the panels run on across the vertices (no inset, no end faces), mullions every 4.05 m of arc. The arcs may run up to the 0.6-m fit tolerance outside the outline's chords (the real wall is the curve; verify allows 0.6 m) |
| r2-self | Garage A station block over open track (seen in the r2 a2 render) | fixed | r1 had united the track strips with the body up to the NE end (u = Lb 150.8): a 16-m block over open track, east of the curved NE end where a2 shows the apron. The SFO Museum outline ends the body there at u 134.8 (south track) / 139.8 (north-track face): the strips stop there, the block's east faces are those outline faces and the tracks run in the open beside the NE end (l1: the curved NE wall stands east of the block face, nearer the camera); the l1 render camera moved with the face |
| 9 | LOD2 drops the void floor / Level-5 parts / cars; roofs jump | fixed | Central garage LOD2 keeps the void floor, the Level-5 garage edges beside the guideway (to the trough-wall top), the two DOF roof poles and the roof lobes / rims (cut out of the deck); every deck has a LOD2 car impostor (one roof quad per car in its paint colour, COLOR_0); LTP 1 / 2, RCC, Hyatt, CAC and MOC LOD2 roofs at the LOD0 roof level inside a coping ring |

**Requests to the drawings group (r2):** the Garage A / G heights (BL-03 draws the NAIP drum ring 39.6 / 37.6; a2 gives parapet 29.1 / 27.5,
deck 26.7 / 25.3, 9 levels at 3.34 m, Garage A drum ring 31.0) and the NAIP-lean conflict behind them; the Garage A NE rotunda and
penthouse; the trough walkways east of the Garage A station and the open gap; the RCC tower rake and platform 8.84 m; the BART band /
colonnade.
### Close-out round 3 (6 Nov 2026): what changed, and why (`manifest.json#landside.closeout_r3`)

Rebuilt 05:43Z (`out/buildings3d/c3/landside_build_c3.log`): **195 checks, 0 failed** (192 / 0 before; the three new checks are
the last rows below). landside.glb 20.97 -> 21.23 MB; LOD0 159,741 -> 160,713 tris, instanced car tris 93,582 -> 168,718 (1,737
cars, ~97 tris each within 450 m; LOD1 65,854 -> 71,894; LOD2 has no wheels). Rebuilt again 7 Nov 02:11Z after the back-face QA below (`out/buildings3d/c3/landside_build_c3r.log`): 195 / 0, LOD0 160,713 -> 159,459 tris (the duplicate body bands over the station block's south stretch are gone), 21.13 MB; `b3d_split.py` re-run.

| id | Finding | Disposition | What the model does now (evidence, before -> after) |
|---|---|---|---|
| buildings-3 | AirTrain piers in road decks, caps 3.25 m over interchange_2_2 | fixed | `landside_airtrain.py` tests every pier site against the `data/sfo_landside.json` carriageways (OSM centrelines buffered by their half widths, at grade and elevated) and the `roadways.glb` LOD0 deck tops (6,147 triangles): a column (+0.5 m) on a road, or a cap less than 4.6 m (Caltrans HDM 309.2, the roadway solve's clearance) over a deck, rejects the site, and a rejected site no longer reserves its 30-m slot. Where no single column fits, a straddle bent: two columns off the road within 18 m of the centre line, a cap beam >= 4.6 m over any deck [inf]. Piers 91 -> 86 (19 straddle bents; 39 column sites rejected). Column feet on a road / deck: 3 (integration 03:59Z) -> 0; pier vertices over a deck: none (the 3.25-m cap is gone). The largest guideway distance to the nearest pier stays 46.7 m (a road test without bents left 120 m). |
| buildings-8 | BART 36.7 m from taxilane 302 (ADG-5 OFA 42.1 m [inf]) | rejected with evidence, no geometry change | The modelled north face is the OSM way 221663595 edge, 36.75 m from lane 302. The observed NAIP 2024 north wall line (`landside_r1_measure.BART_NORTH`, +-2 m) is 35.8 m from it, so the real building stands inside the inferred OFA: an existing condition, not a modelling error. Pulling the body back would contradict both the OSM outline and the imagery. The SFO Museum geometry has no BART outline; its 37.3 m is the nearest other structure. New check: body to lane 302 >= the NAIP line - 0.5 m (36.73 >= 35.78). The ADG of lane 302 (5, from the largest stand served) is the integration's inference; request in `docs/requests/buildings_closeout.md`. |
| buildings-9 | parked cars: boxes without wheels, two shapes | fixed | `landside_cars.py`: at LOD0 two 6-sided axle prisms per car through the full track width. The tyres show outside the 3-% skirt inset and below the body. A third shape, the pickup (5.50 x 1.95 x 1.85 m), has an open bed with a dark liner 0.45 m below the rails. The mix is sedan / SUV / pickup 45 / 40 / 15 % [inf]. LOD1 / LOD2 are unchanged. Spacing and on-deck checks: min centre spacing 2.39-2.81 m (>= 2.1), median height over the deck 0.01 m. |
| buildings-1 (landside) | back-face QA not re-run after round 2 | done | `render_landside.py --backface` (8 spp, red = inward faces) on the rebuilt glb: see the table below. |
| buildings-10 (BL-03) | BL-03 drew the drum rings 39.6 / 37.6 m against the a2 parapets 29.1 / 27.5 m | **partly** (fix 2, verifier v5): BL-03 fixed on the sheet; the other review r1 / r2 landside drawing requests and the AirTrain wye are not drawn - recorded as deviations (`manifest.json#landside.closeout_r3_fix2` v5) | `draw_landside.garage_r3` overlays the 3-D state on the Garage A / G elevations: a2 parapets 29.1 / 27.5, decks 26.7 / 25.3, 9 levels at 3.34 m, Garage A ring 31.0. The old NAIP drum-ring reading (39.6 / 37.6) stays dotted and is marked SUPERSEDED. Lean-model conflict, resolved on the sheet [inf]: the NAIP frame model (spec `naip.k_model`, fitted on the ITB poles) would turn the whole 13.25 / 12.0-m drum-band offset into relief only with a Hyatt far outside 40-48 m. The sheet therefore splits the band into relief at the a2 height plus the gap between the SFO Museum outline arc and the ring's outer edge. The Hyatt height (owner item) decides. |
| buildings-11 | Hyatt 44 m [inf] (40-48), a2 scale | deferred: needs the owner | Unchanged default 44 m [inf]: 12 storeys [pub] at the photo-l4 13.2 pitches. The FAA DOF has no Hyatt entry (searched 2026-09-18 DOF.CSV). The FAA OE/AAA filing is the likely primary source, but its search portal is a session web app (not reachable as a document here). |
| buildings-12 (landside) | single-photo / placeholder values | partly: no new primary source | Unchanged and tagged: AirTrain levels (the solved d1 camera implies a T1 station deck below the 19.75-m placeholder - information only, the level field stays), the l1 station-block top (31.75 m) vs a2 (29.1 m, adopted; conflict listed), Garage G from 4 parapet columns, the rotunda centre ~2 m residual [low], the far-track walkway by symmetry [inf]. Searched 2026-11-07: no published height or FAA determination for the Grand Hyatt at SFO (contractor / SFO press pages give 12 storeys and 351 rooms only). |
| buildings-1 (LOD2 void floor) | 'LOD2 void floor slightly brighter (pop at 1,500 m)' (r2 doubt) | checked, no change | Cycles cg_top (r2 renders): void-floor mean inside r 18 m of the void centre LOD0 (217, 214, 209) vs LOD2 (218, 215, 210): +1 grey level, below visibility at the 1,500-m switch. |

**Back-face QA, close-out round 3** (`render_landside.py --backface`, 8 spp, red = the back of a single-sided face; red pixels per
960-px view). "Last recorded" = the r0 / r1 renders (no back-face run was made after round 2); "c3 first" = the 6 Nov 05:43Z file;
"after" = the 7 Nov 02:11Z rebuild. Causes found by casting the red pixels back into the glb (numpy ray test,
`scratchpad c3/buildings/bf/bfhit.py`, `occl.py`):

| view | last recorded | c3 first | after | what the red pixels were / are |
|---|---|---|---|---|
| gar_a | 0 | 1 | 0 | - |
| hyatt | 610 | 162 | 162 | the colonnade recess at the curved south end (r1 residual, left open) |
| l1 | 56 | 1,076 | **26** | (fixed) the Garage A body's screened bands ran across the station block's south stretch: `roof_w` had one 131.7-m outline edge past the block, so `style()` could not tell the block stretch apart and the hall showed the bands' backs through the south track opening -> the ring is split at the block corners (`_split_ring_at`); (fixed) the NE rotunda's proud top band (+0.12 m) had an open underside -> annulus added; 26 px remain deep inside the station hall, at the edge of the track deck (the rays end on its front face: sub-pixel slivers) |
| l5 | 2,380 | 2,213 | 2,213 | thin lines along the RCC guideway trough-wall tops / walkway edges: a down-facing deck soffit seen through a narrow gap beside the deck top (r1 residual, left open - `airtrain_-6_-3`, round-1 track furniture) |
| bart | 569 | 100 | **7** | (fixed) the perforated screens were single-sided: from outside, through the open strips of the curved ends, their inner faces showed -> `screen` doubleSided (a thin panel: both sides valid); in a2 the screen hits went from ~115 px to 0 (ray test) |
| cg_top | 0 | 0 | 0 | - |
| a2 | 6 | 1,704 | 1,621 | screens (fixed as above, ~115 px); the rest is the BART station's east end against the ITB outline, left open by design (internal edge, `inside_other`): with itb.glb loaded every one of these rays ends on the ITB core (a front face) - the landside-only render shows it, the app does not |
| overview | 0 | 3 | 3 | sub-pixel slivers at the guideway ends |

### Close-out round 3, fix round 2 (7 Nov 2026): what changed, and why (`manifest.json#landside.closeout_r3_fix2`)

Rebuilt 13:15Z (`out/buildings3d/c3f2/landside_build.log`), split into the lsu units (`b3d_split.py`, 13:48Z).
verify_landside **198 checks, 0 failed**; the same script on the 11:14Z file gave 198 / 3: the three new gates failed there.
landside.glb 21.13 -> 21.16 MB; LOD0 159,459 -> 159,599 tris, LOD1 85,433 -> 85,573, LOD2 22,060 -> 22,284 (125 draw calls).

The back-face counts below come from `tools/blender/bf_rays.py`, the verifier's numeric ray test (16 azimuths x 1-m slices
plus vertical rays at 0.5 m) adopted into the repo, with each LOD's neighbours loaded. "Tie-break" is the same test with one
change made in this round: where a ray meets two faces at the same point to 1e-6 m (a ray of the grid passing exactly
through a convex corner vertex), the front face wins. Before this change, those zero-measure hits were counted as back
faces.

| LOD (context) | before | after | after, tie-break | main changes |
|---|---|---|---|---|
| LOD0 (itb, domestic, roadways, tower) | 2,582 | **837** | 787 | sb_roof 878 -> 0, cg_plinth 830 -> 62, garage_a_station_block 81 -> 12 |
| LOD1 (itb, domestic, roadways) | 2,460 | **663** | - | sb_roof 878 -> 0, cg_plinth 883 -> 63 |
| LOD2 (itb_lod2, domestic_lod2, roadways_lod2) | 15,718 | **138** | 61 | L2_superbay 15,084 -> 2, L2_garage_a 433 -> 14, L2_garage_g 82 -> 3 |

| id | Finding | Disposition | What the model does now (evidence) |
|---|---|---|---|
| v2 (major) | Superbay LOD2 an open shell since round 1. The walls stopped at 25.8 m under a 27.0-39.6 m roof, and the 41.1-m spine roof floated. | fixed | `landside_geom` builds the Superbay LOD2 as a closed coarse solid: the two cantilever roof planes with a 1.2-m fascia and soffit, the flat spine roof with its side and end walls, and outline walls up to the soffit (top sampled along every edge, split at the spine lines). LOD0 / LOD1 (878 pre-existing hits): the spine stretch of the roof sandwich got its soffit and end fascias, and the spine walls their triangular ends under the hips. Garage LOD2 got portal-recess jambs / head / sill and drum-ring inner faces above the parapet; the CG slot got sliver linings. `verify_landside` gained a LOD2 see-through gate (bf_rays with the LOD2 neighbours; > 60 hits per node fails; worst now L2_bart_station 25). |
| v3 | parked cars overlapping (16 pairs, worst 2.44 m2); LOD1 cars 0.30 m above the deck | fixed | `landside_cars.resolve_overlaps`: every car's oriented footprint (its shape's length x width, + 0.025 m) is tested against the cars already placed on the deck and on the building's other decks (+-1.5 m). A car that overlaps takes the next shorter shape (pickup -> SUV -> sedan), else it is dropped [inf: which car gives way; the NAIP-observed cars are placed first]. The LOD1 body starts at the deck. verify_landside, on the oriented plan hulls of every LOD0 instance: **16 pairs -> 0** (1,729 -> 1,716 instances; manifest 1,737 -> 1,724 cars); LOD1 bottom **0.30 -> 0.00 m**; NAIP-detected central-garage cars reproduced 0.858 -> 0.839. |
| v4 | Garage A station block: the open south side showed the back of the single-sided east wall (+72 hits) | fixed (3-ray residual) | An inner lining of the east (portal) face over the hall / track band, 0.05 m inside, with the same track openings, faces into the hall (dark interior). garage_a_station_block **81 -> 12**: 9 of these are the same cells as in the round-2 file (unchanged). The other 3 are rays at az 315 deg that pass through the 0.05-m joint where the lining ends at the wall vertex (-1392.21, 537.34), 21.5-24.5 m up - a hairline, recorded. |
| v5 | landside drawing requests and the AirTrain wye not on BL-01..03 | partly (recorded, not drawn) | BL-03 states each not-drawn item as a NOT DRAWN note, with its 3-D source and tag (`draw_landside.fix2_notes`, 9 notes), and labels the old drum-ring line SUPERSEDED. The items: station block, BART station plan / levels, RCC rake / platform 8.84, drum towers, CG rims / lobes, NE rotunda / penthouse, walkways east of the station, BART band / colonnade, the AirTrain wye west of x -1592. The records are in `closeout_r3_fix2.v5.sheet_requests`. buildings-10 stays **partly**. |
| v8 | landside glass carried the baked AO as glTF occlusion (7 of 8) | fixed | One glass AO rule for all four assets: `build_landside` links no glTF occlusion on a glass material. station_glass@B/C, glass_bart@B/C, glass_hyatt@B/C and glass_band@B: 7 -> **0** (landside_lod2 0 of 3). |
| v9 | pier-cap test on every third vertex | fixed | verify_landside measures pier caps / bents on the pier FACES over the roadways.glb deck faces (35 overlaps): min **12.40 m**; column feet on carriageways / decks 0. The independent ray test is now a verify gate (above). |

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

### Close-out round 3 (6 Nov 2026): dispositions (`verify_domestic_r2.py` t2_curb / drum_overhead; `manifest.json#domestic` conflicts, dimensions)

Rebuilt `--final` 05:39Z: `verify_domestic.py` **60 checks, 0 failed**; LOD0 78,143 -> 80,494 tris, 150 -> 156 draw calls,
11.14 -> 11.50 MB. Rebuilt again 7 Nov 03:36Z after the back-face QA (row buildings-1 below): 60 / 0, LOD0 80,720 tris, 156 draw calls, 11.58 MB. `verify_domestic_r2.py`: n_fail 0 with the two new probes below (re-run 2026-11-07 01:43Z, `out/buildings3d/c3/verify_domestic_r2_final2.log`, after the t2_curb probe was changed to cut the triangles with z planes along the measured line and to clip the deck to the T2 stretch; the 06:26Z run with the vertex-based probe had reported 2 false fails, median -3.5 m, because the fascia triangles run 10-25 m along the slanted line).

| id | Finding | Disposition | Evidence (before -> after) |
|---|---|---|---|
| buildings-2 (major) | T2 shell over the departures curb roadway | **fixed** | `dom_geom._t2_curb`: the T2 landside face stands on the NAIP 2024 relief-corrected roof edge, x = -811.96 + 0.3063 z for z 168-254. That line is the lean-free coping, 59 rows, rms 0.06 m; NAIP 2020 is within 1.5 m, and the SFO Museum AirTrain T2 station polygon ends at x -743.8, on the line [obs]. Elsewhere the face sits 5.85 m off the departures deck edge (NAIP edge minus OSM 256787747, median 5.85, p10 5.76, p90 6.63 m). 2,355.9 m2 of hall removed. In front of the face: the departures sidewalk at the curb level (905 m2); a glass lobby band 0-7 m above the curb under light panels (style `T2_land`); a 5.4-m glass curb canopy (NAIP 2024 / 2022 teal band, soffit 8.88 = curb + 4.0 as T1 [inf], 668 m2, 17 brackets). The T2-garage connector (`T2_garage_link`, 847.5 m2: the SFO Museum courtyard connector carried along its axis to the new face and cut at the Central Garage outline) runs over the deck with soffit 9.43 / top 14.38 [inf]. New probe `t2_curb` (LOD0 / LOD2, the OSM Departures ways along T2): solid between the deck and 4.6 m above it 1.41 m2 on the round-2 asset (its west walls standing on the roadway; the integration had to cut 1,406.5 m2 of deck enclosed by that shell) -> **0.00 m2**; connector soffit over the deck 4.70 m; roof edge minus the measured line median 0.01, max 0.11 m (14 sections). The neighbour check found the connector's fins 0.64 m2 into the Central Garage plinth; the connector now has fin-less glass, so landside contact is 0 again. Roadways must be rebuilt to lift the interim deck cut (request R3.1). |
| buildings-4 (major) | F7 / F8 / D3 drums inside the asset footprints | **fixed (3-D shown clear, recorded); plan test routed** | The F7 / F8 L1 drums lie ~1.05 m inside the BA-F footprint ring only under the ESE roof overhang: soffit 9.69, drum top 8.55, **1.14 m clear**; facades >= 0.1 m outside the largest drum. F8 L1 tunnel 1 stays >= 1.58 m below the soffit in every pose (the gates.js solids dumped this round, `SP/c3/buildings/drum`). The D3 L1 facade is 0.19 m clear of its drum. New probe `drum_overhead`: 6 drums under a roof, min clear 0.5 m (E6 / E9 / E11 under the 9.05-m soffit), F7 / F8 1.14, B10 1.25. Conflict record "app rotunda drums under the BA-F overhang" (status resolved, 3-D). Request R3.3: height bands in the integration footprint tiers. |
| buildings-5 | BA-B glass in the low tier darker than Cycles | **partly**: the domestic-side cause fixed; the rest measured and routed | Cause on this side: the baked AO was linked as the glTF occlusion of the GLASS materials; three.js applies a material's aoMap to the indirect diffuse and, through its specular occlusion, to the IBL reflection that makes a curtain wall read, so the BA-B panes under the 2.3-m overhang (AO 0.59-0.65) came out ~0.6x darker in the app (Cycles ignores the glTF occlusion). `build_domestic.make_material` no longer links it for `glass*` (the bake node stays). App low tier, pierB (B20, 110 m): wall median (20, 24, 25) -> **(27, 35, 36)**. Like-for-like comparison this round (the r2 Cycles reference `domestic_bclose` was a sunlit view of the other side): the app camera and sun logged by `tools/blender/c3_app_views_job.mjs` (`out/buildings3d/c3/appB2/c3_info.json`: eye (-1018.5, 28.3, 768.7), fov 50, sun az 133.9 / el 41.6) and rendered in Cycles with `render_domestic.py --views appcam` (`domestic_app_pierB_c3.png`): Cycles (58, 64, 71) vs app low (27, 35, 36) and app HIGH tier (29, 36, 37) (`appB3`) - the same in both tiers, so not the low tier's missing SSR. Normalised to the white fascia band in the same frames: glass / fascia 0.15 (low) / 0.17 (high) vs 0.33 (Cycles); the sky in the same frames reads (126, 146, 161) in the app vs (166, 182, 194) in Cycles, and the panes are sky-reflection dominated. The remaining gap is the app's sky / IBL radiance relative to Cycles' sky (request R3.10); a material-only lift would brighten Cycles too and has no photo to aim at (no openly licensed BA-B photo). |
| buildings-14 | 3.53-m soffit of the departures loop over at-grade roads | **partly**: provenance recorded, value not changed, routed | The curb (4.877 m) is now tagged inf with its provenance: the published T3 L1 -> L2 16 ft (CDR 95 % CD p.28-29) carried along the connected loop. The 17 OSM Departures ways that roadways.glb anchors form ONE component by shared nodes. NAIP relief / shadow of the deck edge cannot resolve it at 0.6 m GSD. Raising the deck to clear 4.6 m (top >= 5.8 m) would contradict the published T3 L2 at the T3 curb. A 16-ft stacked rise with a 0.75-0.9 m slab gives ~3.8-4.0 m: the stacked arrivals level is low-clearance by design. Conflict "departures loop soffit over at-grade roads" (status open; the 10 OSM crossing ids). Request R3.2: list them in b3d_integrate and review DECK_DEPTH 1.2 m [inf]. Owner question: posted clearance on the arrivals level. |
| buildings-10 (BD-01 / BD-03) | sheets behind the 3-D state | **fixed on the domestic sheets**; finding overall **partly** (fix 2, verifier v5: landside requests / wye not drawn, BI-03 / BI-04 roof notes) | BD-01 plan: `draw_domestic.r3_plan` overlays the moved T2 face, sidewalk, canopy, connector and the NAIP rooftop units (`dom_roofobs.json`). BD-03 view 2 is redrawn from the 3-D state: the 77.4-m curb stretch, glass 0-7 m, canopy, connector, leaders to the sources. The spec note on the BA-F ESE roof edge (`spec_domestic.json` baf.roof_edges, "on the level-2 outline") is corrected: sampled at 10 / 25 / 50 / 75 / 90 % of its 52.4-m length the drawn line is 1.83 m outside the outline (it touches the outline only at its end points, on the corner jogs) - the overhang the sheets and the 3-D carry; manifest conflict "BA-F ESE roof edge" resolved. |
| buildings-1 (domestic) | round-2 fixes never independently checked | **done; one defect found and fixed** | Back-face QA (`render_domestic.py --qa backface`, red = the back of a single-sided face) on the 6 Nov file: t2curb **209 px** - a 5-m hole in the moved T2 face beside the connector: the face edge z 199.2-220.7 was opened 9.43-14.38 m over its whole length for the 16.9-m connector end, because `World.splits` only split an edge where a neighbour's outline CROSSES it, and the connector's end runs along the face 0-9 cm off it (never crossing), so the one mid-edge sample clipped the whole edge. Root-cause fix in `dom_geom.World.splits`: neighbour vertices within 0.15 m of an edge split it too. Exposed wall area over the whole asset -27.6 m2 (T2 +72.6, BA_C +68.4, T3E +53.9 m2: holes of the same kind closed; BA_F -162.2, T1 -40.8, T3W -31.8 m2: internal walls against abutting solids now clipped). After (03:36Z file): t2curb **0**, a1 127 -> 106, c3c 258 -> 197, eclose 204 -> 164, d1 0, ibf 0 px; verify_domestic 60 / 0, verify_domestic_r2 n_fail 0 (t2_curb, drum_overhead unchanged). Round-2 items re-checked: `domestic_cmp_a1.png` shows the dark C3C storey glass and the BA-E end glazing / PV as fixed (the a1 camera is estimated, so only qualitatively); the drum notches hold in the probes; the T1 sign (d1) was not re-rendered. |
| buildings-12 (domestic) | T1 / T2 hall heights and curb placeholders | **partly** | No new primary source. The FAA DOF (DOF.CSV 2026-09-18, 1,332 rows around the airport, re-searched this round) has no entry on T1 or T2 (nearest: apron poles and the 2016 tower, 245 ft). One BLDG entry, 06-039216, lies inside the T3 footprint, 80 m WNW of the C3C outline: 130 ft AGL / 136 ft AMSL, accuracy 4D (+-250 ft horizontal, +-50 ft vertical), status unverified, study 2012-AWP-7455-OE. It is too coarse and too far to identify as the C3C (the model's C3C penthouse top 38.0 m would sit inside its +-15 m), so it is recorded, not used. The values stay tagged (`dimensions`, `unknown`). |

### Close-out round 3, fix round 2 (7 Nov 2026): dispositions (`manifest.json#domestic.closeout_r3_fix2`)

Rebuilt `--final` 13:11Z (`out/buildings3d/c3f2/domestic_build.log`): `verify_domestic.py` **61 checks, 0 failed** (the new
row: the app bridge dump matches the current gates.js / stands). LOD0 80,720 -> 79,913 tris, 156 -> 154 draw calls, 11.58 ->
11.37 MB. `verify_domestic_r2.py` n_fail 0. The heights now come from `tools/blender/app_bridges.json`: `node
tools/blender/app_bridges.mjs` runs `js/live/gates.js` in Node and records the SHA-256 of its inputs. The scripts fail when
the dump is stale. Cross-checked against the browser extraction `out/draw/scene2d.json` of 10:35Z: 131 / 131 bridges.

| id | Finding | Disposition | Evidence (before -> after) |
|---|---|---|---|
| v1 (major) | bridge attachments sized for one 5.4-m floor; gates.js now has per-pier levels (C 3.2, D 3.65, E / F 4.88) | **fixed** | Every bridge-attachment height is taken per door from the app walkway floor at the facade / walkway start (DEPARTURE_LEVELS + the 1:12 slope): door frames floor -0.2 .. +3.2, vestibules -0.5 .. +3.3, overhang notches, drum notches per drum from its rotunda floor `Hr`, and the undersides of pods a walkway enters (lowest floor in the part - 0.5). BA-C / BA-D facade bands at the photo a1 ratios: glazing 0.443-0.794 of the roof edge [obs low BA-D; inf BA-C]. Bulkheads 23 -> **0**; BA-D overhang notches 2 -> 0; 80 doors / 54 vestibules. Walkway floors at the doors: B 5.30-5.40, C 3.18-3.20, D 3.59-3.65, E 4.87-4.88, F 4.82-4.88 m. `verify_domestic_r2` walk (app walkway solids in their own height band, same probe on the old and new files): LOD0 conflicts **8 -> 0** (C4 C8 D3 D4 D5 D14 D15 D16), horizontal overlap **8.72 -> 0.00 m2**, walkway-end contact 41.26 -> 31.45 m2 (vertical only: the walkway ends against the door leaf). LOD2: 8 -> 0, 8.72 -> 0.00. The verifier's `brsolids.py` with the same bridge geometry (bridges bc_after2, rest + docked poses): **20.68 -> 10.71 m2**, every C / D bridge <= 0.31 m2 (was D15 1.99, D14 1.95, D3 1.66, C4 1.49, D5 1.21); 0 rotunda / tunnel / cab contacts. Residuals B16 1.45 / B11 0.85 m2 are unchanged since round 2. They are an artifact of the box test: brsolids gives the whole sloped walkway one height band (4.60-8.40 / 3.94-8.40), and the pod soffit (4.73 / 4.63 m) falls inside it. At the pod itself the walkway floor is >= soffit + 0.5 by construction (`walk_y0`), so its slab underside is 0.2 m above the soffit. BA-C walkway top 6.20 m sits under the 6.40-m slab underside, BA-D 6.65 under 7.69. Cycles a1 (`out/buildings3d/domestic_a1_c3f2.png`): no boxes above the BA-C / BA-D roof lines. Manifest conflict "BA-C / BA-D roofs vs the app concourse floor" resolved. |
| v6 | stale cross-asset records | **fixed** | scene2d.json replaced by the 7 Nov extraction (the 5 Nov copy is in `out/buildings3d/integ/draw/stale_20261105/`); the probes read `app_bridges.json` (gates_js_current true). The buildings-14 conflict now quotes `integration.json`: 26 roads, 753 m, min 3.53 m at (-940.9, 429.6), with the 26 OSM ways. It stays open: the posted clearance is an owner question. |
| v9 | drum_overhead ignored faces dipping below the drum top | **fixed** | Every face that covers the drum disc and reaches above its top counts, with its height evaluated over the disc. Drums use their own `Hr` band. Result: 13 drums under a roof, min clearance **0.92 m** (D7: drum top 6.77 under the 7.69-m overhang underside), 0 contacts with the 415 drum hulls, at LOD0 and LOD2. |
| v8 | one glass AO rule | **fixed** (all groups) | Domestic glass has had no glTF occlusion since close-out r3 (20 materials, LOD2 5). The same rule is now in the ITB, landside and tower builds: 0 glass materials with occlusion in all nine files. |

Back-face rays (bf_rays, LOD0 with itb / tower / landside loaded): 87 -> 89 by the verifier's method. The +2 are three rays
on the grid line x = -552.50 through the west corner of a BA-D rooftop unit. That unit is a closed box (four walls + top). It
is no longer clipped by the dropped overhang notch, so its corner moved from x -552.14 onto the grid line. With the
front-face tie-break, the count is **74 before and 74 after**, and BA-D has 0 (its 13 earlier hits were all such corner
ties). The residuals are the pre-existing BA-E 29, T1 22 and BA-B 21. LOD2 with context: 90 -> 92 by the same method.

### Open items (also in the manifest's `unknown` / `conflicts`)
- T1 Center and T2 hall heights and the departures-curb height (placeholders); the T3 datum; the BA-B well depth; the BA-F lantern
  (1.0 m modelled, bound 4.6) and monitor rises; the C3C height (33.0, range 32-36) and its roof penthouse (photo a1, not in NAIP);
  rooftop unit heights / types and the units NAIP 2024 does not resolve; the T3W state (95 % CD massing, without the May 2026 storey).
  (The C3C penthouse is modelled since review r2.)
- BA-B facade: no openly licensed reference photo found (Commons, 5 Nov 2026): the EC tint states are [inf].
- **Conflict for the drawings group:** BA-F ESE roof edge — the drawn line is 1.83 m outside the outline along the face (BD-02
  draws 27.0 m between the lines); the spec / README note "on the outline" was measured at the line ends only. The asset follows
  the drawn line.
- ~~Open plausibility conflict (review r2 #5): BA-C / BA-D roofs below the app's 5.4-m concourse~~ - **resolved in close-out r3
  fix 2**: gates.js `DEPARTURE_LEVELS` (C 3.2 [inf], D 3.65 [obs, low]) and the domestic asset sized per door from them (no
  bulkheads, no BA-D overhang notches; see "Close-out round 3, fix round 2"). The pod parts that bridges enter come down to the
  entering walkway's floor - 0.5 m [inf] (BA-B 4.63 / 4.73 m; the app's convention 6.0 m elsewhere); F22's second door attaches
  to door 1's bridge (app side).
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
| `data/buildings3d/integration.js` | What the app imports (js/live/world.js, js/three/buildings3d.js, js/live/gates.js): replacement table, tower camera anchor, landside unit index, ground-physics rings and (close-out round 3) the per-building footprints with body / over height tiers of the tower, ITB and domestic units (182 kB) |
| `data/buildings3d/integration.json` | Footprints per asset unit (LOD0 / LOD1) with height ranges and body / overhang tiers, the table with coverages, the plausibility results (every LOD), the physics set |
| `tools/blender/b3d_views_job.mjs` | livetest job: the same views with `?b3d=0` (first-pass) and the assets -> `out/buildings3d/cmp_*.png`; in `near` mode each view waits until the full files near the camera are on screen (`Buildings3D.settled`) |
| `tools/blender/build_roadways.py`, `roadways_net.py` | the elevated landside roadways asset (`roadways.glb`, `roadways_lod2.glb`, check sheet `out/buildings3d/roadways_plan.png`, `manifest.json#roadways`; review round 1) |
| `tools/blender/b3d_lod2_check.py` | every building's LOD2 against its own LOD0 on the exported GLBs (plan, height, roof) -> `out/buildings3d/integ/lod2_check.json` |
| `tools/blender/roadways_itb_plate.py` | the ITB departures deck measured on NAIP 2024 as one plate (review round 2), sheet BR-02 `out/buildings3d/roadways_itb_plate.png` |
| `tools/blender/b3d_split.py` | landside.glb split per building into `data/buildings3d/lsu_<unit>.glb` + shared `lsu_img_*` images (review round 2; run by b3d_integrate) |
| `tools/blender/b3d_glass_job.mjs` | livetest job: A/B variants of the loaded glass materials at one view (review round 2, finding 2) |
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
listed groups (QA). Review round 2: the landside group loads per building (`lsu_<unit>.glb`, triggers per unit) and
near mode releases what it loaded when the camera is far again (details in "Review round 2", finding 4).

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
binary file - landside.glb was 14.87 MB then -, 255 files and 64 MB per publish), the app bundle 4.58 MB with GLTFLoader and the
loader in it. `integration.js` is bundled (6 kB then; 182 kB since close-out round 3 with the footprints); `integration.json` is not shipped.
**Sizes as of close-out round 3 (7 Nov 2026)**, counted on the working tree's files the artifact ships (B3D=all): 271 supporting
files, 73.1 MB (+ the page: the inlined app bundle, ~4.7 MB) - models 23 files 13.5 MB, low-resolution liveries 185 files
3.8 MB, building files 62 / 55.8 MB. `landside.glb` (21.13 MB) is NOT shipped: since review round 2 the landside goes as 24
unit files (`lsu_*.glb`, 19.8 MB, 0.05-2.5 MB each) + 29 shared images (3.0 MB); the largest file is `domestic.glb` 11.58 MB,
so no file needs the 12-MB split any more (it stays for any file >= 14 MB). Over both single-publish limits (255 files / 64 MB):
the artifact goes up in two publishes to the same URL (a version holds up to 511 files / 256 MB).

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

### Review round 2 (6 Nov 2026): dispositions

```bash
python3 tools/blender/build_roadways.py          # ~2.5 min, ~0.5 GB (no bpy): + the ITB plate (roadways_itb_plate.py, sheet BR-02), stacked crossings
python3 tools/blender/b3d_lod2_check.py          # ~3 min
python3 tools/blender/b3d_integrate.py           # ~4 min: + solid tests, deck clearance / curb checks, the landside split (b3d_split.py), units index
```

Final state: roadways r14 (`out/buildings3d/roadways_build.json`, built 03:55Z), integration of 03:59Z
(`data/buildings3d/integration.json`), LOD2 check after it (`out/buildings3d/integ/lod2_check.json`). r14 differs from r12, which the
phone and high-tier runs loaded, only by the T1 / T2 / T3 cuts of finding 3; the ITB plate and the guideway clearances are identical. The container rebooted at ~01:00Z during the first pass of this
work; the runs below are the ones made after it.

| # | Finding | Disposition | Evidence |
|---|---|---|---|
| 1 | ITB departures deck not continuous (critical) | **fixed**: the deck in front of the ITB is one plate (`tools/blender/roadways_itb_plate.py`, sheet BR-02 `out/buildings3d/roadways_itb_plate.png`), measured on NAIP 2024 resampled in the ITB roof frame with the frame-model relief of the deck edge (12.20 m: deck top + parapet). Kerb at v -30.10 (from the ITB asset's curb triangles), inner roadway 3 lanes (v -43.7..-30.1), island A (v -47.2..-43.7), bus roadway 4 lanes (v -61.8..-47.2), island B with its red kerb (to v -64.3), straight section u -51..44; 8 imaged structural gaps at the outer curves and the far end (6-40 m long, v -73..-90 and u 107) kept open; level L3 11.35 m **[inf]** (spec_itb level3.floor 11.5 - 0.15 kerb); lane tiles, islands raised 0.15 m with kerb faces, island B's red kerb, crosswalk bars at the ITB crossings, 13 plate columns [inf]. Plate 8,066 m2 after trimming (measured outline 9,889 m2). The OSM layer-2 ribbons are anchored on it. Curb to deck: **426 stations, largest void 0.143 m, 0 over 0.3 m** (b3d_integrate, its own test: 428 stations, 0.134 m) - was 3.5 m; no void between the ribbons (was 7.4 m). **Not done as asked**: the outer ~10 m (the light-concrete band v -75.6..-64.3) is **not** put on the L3 deck. OSM maps it as ways 41015123 / 739695588, layer 1, which run under the anchored departures leg 20-30 m past the straight, so on L3 it would have to drop >= 5.8 m there (19-25 % grade; tried: a 14.5 % kink at the plate end). NAIP shows a different surface (sRGB 218, 217, 208 against the asphalt's 213, 210, 202) and, between island B and it, a 2.8-m dark / bright / dark band that reads as the step's barrier and fascia at the 2024 lean. It is built as the **lower deck** (solved 6.87 / 7.20 m on the straight), widened to the imaged band (+245 / +258 m2) toward the plate edge. Independent cross-sections of the exported files (r12 and r14 alike; `r4/t2/xsec_r12.py`; deck-top triangles of roadways.glb and the ITB curb, every 0.1 m along v at u = -40 / 0 / +40) read the same at all three: curb v -30.1..-25.8 at 11.5 m, void <= 0.2 m, plate v -30.3..-64.3 at 11.4-11.5 m (parapet 12.2 m), a 0.4-0.6 m plan slit at the 4.2-m level step, lower deck v -64.9..-74.5 at 6.3-8.0 m. The slit is deliberate: the lower deck stops 0.6 m (STACK_GAP) short of the plate, so no road runs under the plate with less than 4.6 m (it would have 2.95 m). Listed as `unknown` in manifest.json#roadways (the NAIP 2020 / 2024 parallax is inconclusive) | BR-02; `roadways_build.json#stats.itb_plate`, `curb_gap`; `integration.json#plausibility.stats.itb_curb_gap`; cross-sections (`r4/t2/xsec_r12.py`); renders `r4/high/cmp_new_i3like.png`, `r4/low/cmp_new_itbwest.png` |
| 2 | BA-B facade black at B20 on the low tier (minor) | **fixed (pane structure), partly (pane level)**: the loader scaled the fins' `max_dist_m` (160 m) by the tier's LOD range, so the phone tier dropped the fin nodes at 89 m and the B20 view (110 m) saw BA-B without them. The limit is the fins' size in pixels, which the tier does not change, so it is no longer scaled. A/B on the loaded materials (`tools/blender/b3d_glass_job.mjs`, low tier, domestic only, one view; median sRGB of the BA-B wall): r3 12, 16, 16; base 43, 54, 60; fins forced on 42, 53, 60; glass AO off 43, 54, 61; normal map off 42, 54, 61; envMapIntensity x 2 31, 45, 49 (the frame-metered exposure moves with it). Env / specular / AO are not the cause. With the fin nodes hidden (what every tier shows beyond 160 m) the glass tiles keep the pane / frame rhythm (`r4/glass2/`: median 26, 32, 36 against 34, 45, 51 with fins; pixel spread 66.6 vs 67.1). In the phone run at the reviewer's B20 view (`r4/low/cmp_new_pierB.png`, wall region x 20-200, y 185-255): median 12, 15, 15 (r3) -> 19, 25, 25, frames to luminance ~125, mullion grid visible. The panes stay dark on this shaded side: darker than Cycles' 61, 67, 74 (`domestic_bclose.png`, a different view and light). The glass material is the domestic group's; the low tier has no screen-space reflections | `r4/glass/glass_*.png`, `glass_info.json`; `r4/glass2/`; scratchpad crop r3 vs r4 |
| 3 | domestic departures roadway inside the T2 shell; T1 / T3 1-3 m (major) | **decided against NAIP: the roadway is right, the T2 shell is not**. NAIP 2024 shows the departures roadway open to the sky, with traffic, between the modelled T2 west wall (x -768 / -756) and the glass curb canopy. The T2 roof edge measures at x -750.5 (z 200), -745 (z 220), -739 (z 240), 17-18 m east of the asset's wall: the asset follows the SFO Museum outline over the curb roadway, as T1 Center did before the domestic group moved that face. Request to the domestic group in manifest.json#integration.requests. Until that face moves, the deck is cut where it runs inside a building: T2 1,406.5, T1 390.6, T3E 312.6, T3W 309.4 m2; **0.00 m2 left enclosed after the cut**. The cut lifts by itself on the next build after the face moves. **Solid tests** replace the surface-band pair test for these cases. A deck point is inside a building when a ray up hits that building's roof, and rays in 8 plan directions (every 45 deg) hit near-vertical walls (>= 1 m2 triangles) within 150 m, with no open sector > 45 deg. The walls are taken from the whole group's LOD0, because a unit's shell is open where it joins the next one. With the unit's own walls, the plan check (`r4/t2/t2_plan.png`, on r12) found 102 m2 of deck under the T2 roof, east of its west wall at the BA-D junction, still standing. The 150-m bound stops a far pier from closing an open sector: with unbounded group walls, BA-A ~600 m away 'enclosed' the ITB plate's end and the cut reopened a 1.66 m curb void (r13). b3d_integrate runs the same test on the exported decks (CONFLICT > 1 m2): **none inside** (r14). It also runs it on building pairs (1-m cells x 1 m of the shared height, inside both buildings): tower / T2, tower / BA_D and ITB / T1 share 0 m3. Re-check in the reviewer's sections (exported files, `out/buildings3d/integ/r4/t2/t2_vsec.py`) and in plan (`t2_plan.py`): at z 200 the deck tops end at x -768.5, on the T2 wall (x -769..-767.7, to 16.1 m), with no deck under the T2 roof (16.28 m) at x -765..-745 (was: deck x -769..-756 inside). At z 240 they end at x -756.0, on the wall at -756 (was: x -756..-744 inside). Seen from outside, the departures roadway meets the T2 wall at both ends of the ~115-m stretch until the face moves. That is the same view as before (the deck was inside the shell), without a road inside the hall | `roadways_build.log`; `integration.json#plausibility.stats.deck_inside_buildings`, `asset_pairs[].solid_m3`; `r4/t2/t2_plan.png` (plan: T2 walls / roof, r14 deck tops); renders `r4/t2/cmp_new_t2along.png`, `r4/high/cmp_new_t2curb.png` |
| 4 | near mode loads landside.glb (20.3 MB) from every core camera (major) | **fixed**: `tools/blender/b3d_split.py` splits landside.glb (21.0 MB) byte for byte into 24 unit files (`lsu_<unit>.glb`, 18.9 MB together, 0.05-2.3 MB each) + 29 shared images (3.0 MB, referenced by URI; textures named `lsu:<image>`, one GPU texture per image, refcounted). Near mode loads a unit when the camera is within its own LOD1 switch (low tier; LOD2 on the medium tier) x the tier's range + 10 % + 60 m (low: 335 m). It **releases** units, and full group files, when every trigger is farther than 1.3 x + 100 m for 8 s; the lod2 file comes back. All due units are dropped in one pass; groups reload one at a time. On the low tier the groups are no longer compiled with `compileAsync` over every LOD with culling off: only the LOD shown is compiled (`_setLod`), others on first use. The phone artifact ships the unit files instead of landside.glb (`tools/build3/phone_artifact_page.py`). **Phone run** (low tier, llvmpipe, `r4/low/cmp_info.json`, table below). **Not done**: meshopt / KTX2. Measured on the 24 unit files (geometry only, gltf-transform 4.1.1): meshopt medium 18.87 -> 6.47 MB (34 %); quantisation alone (`KHR_mesh_quantization`, 16-bit positions, 10-bit normals, 12-bit UVs, no decoder) 18.87 -> 12.79 MB (68 %). meshopt needs the WASM decoder (`WebAssembly.instantiate`), KTX2 the Basis transcoder; the artifact CSP for WASM is unverified (engine.md section 5). Quantised positions would also need the loader's per-material merge (`mergeInto`) to de-quantise, which gives up the GPU saving for merged meshes. Left to the engine owner with these numbers | `r4/low/run.log`, `cmp_info.json`; `r4/mo/meshopt_test.json`, `r4/mo/quantize_test.json` (script `quantize_test.mjs` beside it) |
| 5 | road decks under the AirTrain guideway < 4.6 m (4.22 m worst) (minor) | **fixed**: a hard upper bound in the level solve. Every 2 m along each way under the guideway, at 5 positions across the deck (half width + 0.6 m barrier + 0.4 m), deck top <= the lowest guideway-deck soffit over that section - 1.2 - 4.6 m; the bounds are constraints of the same screened solve, not a clamp. Result: **4,942 deck points under the guideway deck, min 4.61 m, 0 below 4.6** (was 4.22); b3d_integrate's own vertical check (`deck_points` every 1 m on the deck tops, the lowest triangle above each, guideway deck and piers separately): 3,872 points, min 4.62 m. **Routed**: the guideway **pier caps** of the landside asset hang 1.4 m below its deck. Over the decks west of the ITB (-1730..-1719, 428-430) they leave 3.25 m (8.6 m2 below 4.6 m), and 3 pier columns stand in road decks. Pier positions are the landside group's [inf] spacing, and a pier over a carriageway is the pier's error, not the road's (bounding the road under the caps gave a 70 % dip). Request: move those piers off the roadways (manifest.json#integration.requests) | `roadways_build.json#stats.guideway_clearance`, `guideway_pier_caps_over_decks`; `integration.json#plausibility.stats.deck_clearance`, `guideway_piers_in_road_decks`; render `r4/high/cmp_new_gwx.png` |
| 6 | LOD2 checker artefacts (BA_C top +9.08, RCC roof median 4.58) (minor) | **fixed in the checker, requests withdrawn**: a joined LOD2 mesh is split per building by containment in the LOD0 footprint (+1.0 m) per triangle, and both LODs use the same roof cells (1-m cells inside the LOD0 footprint - 0.5 m, the highest triangle over each by barycentric rasterisation). **47 units, 0 flagged**: BA_C top +9.08 -> 0.0 m (the C3C triangles had been assigned to BA_C); RCC roof median 4.58 -> 0.00 m (the old cells sampled the open deck below the roof edge); Central Garage top -5.1 (round-1 check) -> 0.0 m. The BA_C (domestic) and RCC (landside) requests are withdrawn (manifest.json#integration.requests_withdrawn) | `out/buildings3d/integ/lod2_check.json` |
| - | deck over deck (new check, this round) | **fixed, with a residual**: b3d_integrate's vertical check over the roadways themselves (LOD0, the undersides only: what a vehicle meets) found, on r7, 90.5 m2 of deck at 3.92-4.6 m under another deck. 89 m2 of it was one stacked pair: the lower outer roadway OSM 739695588 (layer 1) under the layer-3 ramp 681667027 west of the ITB, 466 m2 of full-width overlap over ~50 m at 8-25 deg, 5.11-5.95 m deck to deck against 5.8 needed. The other 1.6 m2 was a parapet top of a lane diverging 0.26-0.5 m higher at five gores, counted as overhead; it is no longer counted (undersides only). Fix in the level solve: crossings under 20 deg (stacked) now take part in the per-crossing deficit raise, when their deficit before any raise is within XS_CAP (1.5 m) and neither way is anchored. The rest stay with the trim's stacked cut: the ITB loop's lower outer roadway under its anchored departures leg, 38853121 / 41015123, and 681667054 / 701476987. Without the anchor rule it gave a 33 % step on 41015123. Tried and dropped: a per-cell cut of the lower deck, which removed 447 m2 of 739695588 and made a gap in a road; a 0.1-m target margin, which raised 72 crossings instead of 36, gave a 14.6 % grade and 31.6 m2 at 2.59 m elsewhere; XS_CAP 2.0, no change. **Result r12: 3.7 m2 at 4.55-4.59 m** (1-5 cm short, at (-1447, 365) and (-1399, 312), the deck top linear between solve nodes) - listed as a CONFLICT, not hidden. Max grade 13.5 % (681667027; r7 13.4 %), 15 decks > 8 %, 0 unresolved | `roadways_build.log` (skewed / stacked line); `integration.json#plausibility.stats.deck_clearance.roadways` |

**Phone run, review round 2** (`out/buildings3d/integ/r4/low/`, live3.html `tier=low` near mode, headless Chromium on
llvmpipe 960 x 540, all five groups incl. the landside units; one page, views in this order). Draw calls and triangles are
the whole frame (aircraft, ground, bridges); "b3d" = the buildings' own visible triangles and their geometry bytes on the
GPU (every loaded LOD); textures = renderer `info.memory.texturesSize` for the whole app. JS heap: Chromium reports
`performance.memory` in coarse buckets without `--enable-precise-memory-info` (527 MB at every near view, 631 MB after),
so it is not a per-view measure here.

| View | Draw calls | Frame triangles | b3d triangles | b3d geometry | Textures | Landside units loaded (unit files) |
|---|---|---|---|---|---|---|
| `pierB` gate B20, 110 m | 560 | 1.65 M | 135 k (LOD0 / 1 units 6 / 40) | 24.7 MB | 568 MB | 2 (1.47 MB) |
| `towercam` tower cab | 1,583 | 3.66 M | 214 k (12 / 36) | 28.8 MB | 607 MB | 4 (4.27 MB: central_garage, 3 guideway sections) |
| `gateA1` gate A1, 60 m | 1,308 | 2.94 M | 244 k (28 / 24) | 33.6 MB | 631 MB | 8 (8.20 MB: + garage_a, bart_station) |
| `itbwest` 520 m west of the ITB | 2,176 | 4.18 M | 228 k (14 / 40, 2 at LOD2) | 38.2 MB | 639 MB | 12 (12.07 MB: + garage_g, grand_hyatt) |
| `far` east of the airport | 233 | 0.97 M | 60 k (4 sets at LOD2) | 22.6 MB | 606 MB | 0 (12 released in one pass) |
| `release` 150 s later | 224 | - | - | - | **537 MB** | 0; tower / ITB / domestic / roadways back to their lod2 files |

Before this round the low tier never loaded the landside (r3 `low2`: 346-535 draw calls, 573-590 MB, landside left out),
and the reviewer's budget put the landside at 88-131 k of 168-256 k building triangles at these probes. Now the near
units come per building (1.5-12.1 MB of unit files instead of the 21-MB landside.glb, which nothing loads any more), and
they go again. The full group files load once the camera is within that group's LOD2 switch (tower 3.5, ITB 6.5,
domestic 11.1, roadways 4.3 MB). Unit load + prepare on llvmpipe: 36-76 s; compile ~1 ms where the programs exist already, 3.3-60 s where a unit brings
new ones (airtrain_-2_0 3.3 s, airtrain_-5_1 9.6 s, garage_g 60 s). These are llvmpipe times on a shared CPU; not measured on a phone.

**Plausibility re-run** (r14 roadways, every LOD of every file, `integration.json` of 03:59Z): 4 conflicts, 10 notes.
- Conflicts:
  - landside/bart_station 36.7 m from taxilane 302 (ADG V needs 42.1 m; the SFO Museum outline is 37.3 m; routed);
  - the guideway pier caps 3.25 m over interchange_2_2 (8.6 m2; routed);
  - deck over deck 3.7 m2 at 4.55 m (above);
  - 3 guideway pier columns in road decks (routed).
- Notes: envelopes F12 / F17 2.9-3.3 m from BA-F (the Museum outline is as close); taxilane OFA for ITB BA-G, BA-F and airtrain_-4_0 (existing condition); the ITB's `L0_hall_canopy` 4.52 m over its departures plate (87 m2, the ITB group's call). No deck inside any building; building pairs share 0 m3.

`tools/sat/check.py`: 0 issues, 17 warnings (bridge extensions / rest poses, unchanged). LOD2 check: 47 units, 0 flagged.

**Renders, review round 2** (`out/buildings3d/integ/r4/`, live3.html headless on llvmpipe, 960 x 540):

| View | Tier / files | Draw calls / triangles / textures | What it shows |
|---|---|---|---|
| `high/cmp_new_i3like.png` | high, all five groups (24 landside units) | 1,787 / 4.01 M / 1,197 MB | finding 1: from the ITB curb at the i3 camera, the plate runs straight and continuous along the face to the far end, curb, bollards and canopy columns at the kerb, no hole to the podium. The lane dashes show only in the distance: the sunlit plate clips (sRGB p95 228) at this exposure (open: lane-mark contrast against the photo, with the photo-match pass) |
| `high/cmp_new_itbwest.png`, `low/cmp_new_itbwest.png` | high; low (phone) | 2,869 / 5.32 M / 1,202 MB; 2,176 / 4.18 M / 639 MB | the plate in front of the ITB as one band between Garages A and G, the viaducts and ramps; the same on the phone tier with 12 landside units near |
| `high/cmp_new_gwx.png` | high | 1,747 / 3.73 M / 1,202 MB | finding 5: the interchange decks and ramps under the AirTrain guideway west of the ITB (deck clearance >= 4.61 m) |
| `high/cmp_new_t2curb.png` | high | 1,891 / 4.65 M / 1,202 MB | the camera of the previous round, over the Central Garage roof: T2 and its curb canopy beyond the garage edge (the T2 face itself is hidden; see `t2/`) |
| `t2/cmp_new_t2along.png`, `t2/t2_plan.png` | high, domestic + roadways only (`b3donly`; the others first-pass) | 1,168 / 4.39 M / 1,134 MB | finding 3 on r14: looking south along the T2 west wall from the departures deck to the north. The outer departures ramp runs on the right, and the deck that ran inside the shell is gone. No road shows inside the hall; the plan shows the deck tops stopping at the T2 wall line. `t2/cmp_new_t2above.png` (over the first-pass garage) does not show the gap between garage and T2 and is kept for the record only; `t2_r12/` holds the same views on r12 |
| `low/cmp_new_pierB.png` (vs `r3/low2/cmp_new_pierB.png`) | low | 560 / 1.65 M / 568 MB | finding 2: BA-B at the B20 view with the pane / frame grid (r3: a black slab) |
| `low/cmp_new_towercam.png`, `low/cmp_new_gateA1.png` | low | 1,583 / 3.66 M / 607 MB; 1,308 / 2.94 M / 631 MB | finding 4 probes with the landside units near the camera (table above) |

### Close-out round 3 (7 Nov 2026): dispositions

Findings `docs/requests/closeout3_findings.json#groups.integration` (integration-1..6); cross-track requests in
`docs/requests/integration_closeout.md` (Round 3). Inputs: the buildings track's rebuilt assets (domestic 7 Nov 03:36Z with
the T2 face moved, ITB 01:55Z, landside 02:11Z). Runs (scratch `c3/integration/`): `base_r15` = the round-2 code on these
assets, `r16`-`r18` = this round's code; final state r18 (roadways built 07:3xZ, integration, LOD2 check, check.py after it).

```bash
python3 tools/blender/build_roadways.py      # ~2.3 min: + the ITB lower level (LOWER_H), its sidewalk, the deck-edge planter, the partial stacked cut
python3 tools/blender/verify_landside.py     # the landside group's checks read roadways.glb (buildings R3.5 order)
python3 tools/blender/b3d_integrate.py       # ~3.5 min: + at-grade clearance, BART observed wall, pier overlap / near, footprints in integration.js, glow table
python3 tools/blender/b3d_lod2_check.py; python3 tools/sat/check.py
```

| # | Finding | Disposition | Evidence |
|---|---|---|---|
| integration-1 | round-2 fixes never reviewed (major) | **verified on the current assets, with the reviewers' own scripts** (copied from the review, run on r18): ITB curb cross-sections (`curb_gap.py`, deck tops 9.5-13.5 m AGL) u -80..80: deck v -64.3..-30.2 continuous, curb v -30.1..-25.8 (0.1 m kerb face; b3d_integrate curb void max 0.134 m, 0 over 0.3); T2 vertical sections z 200 / 240 (`vsec.py`): the departures deck (4.73 m) ends at x -757.3 / -745.2 on the new T2 sidewalk, nothing under the T2 roof, T2 wall at x -750.7 / -738.4; guideway clearance (`clear3.py`): 1,312 m2 of deck under the guideway, min 4.65 m, 0 m2 below 4.6 (review: 4.22 m, 150 m2). No deck inside any building (the T2 interim cut is gone by itself: cut T1 390.6, T3E 312.6, T3W 309.4 m2 at the parapets straddling those facades, none at T2). Low-tier phone run on r18: table below | `c3/integration/rv/` (vsec_t2_z200/240.png, clear3.log, curb_gap.log), `integration.json#plausibility` |
| integration-2 | outer band of the ITB plate a lower deck with an open slit (major) | **settled from evidence: it is a lower level; the slit is closed**. Photo i1 (Kulikovsky 2007, CC BY 3.0, the ITB frontage from the west) shows the departures deck ending in a planter of pink-flowering shrubs on a ~0.9 m fascia, and in front of / below it a lower level - trees in planters on its outer edge (the NAIP hedge line), shelters, pedestrians - which continues under the deck and is level along the facade. The NAIP "red kerb" (R - G peak, v -62) is that planter: its NAIP length (u -53..51, 104 m) = 935 px in i1 gives 9.0 px/m at the deck edge, and the step from the deck-edge coping (y 286.5) to the lower level's outer coping (y 349.5) is ~6.7 m (6.1-7.3; 6.4-7.0 for camera heights 5-20 m). OSM agrees: the at-grade roads 256787738 / 370279550 / 370279603 / 370279607 pass under the band as `tunnel=building_passage`, and the layer-1 footway 1164416297 runs along the frontage at v ~ -48, i.e. under island A ~16 m inside the plate edge [corrected in fix round 2, verifier v4: round 3 said "the plate's length" as if along the edge; it argues for a lower level that runs much further under the deck than the modelled 3.0 m] (OSM layers here are not physical: the crosswalk footways on the deck carry layer 1 too, so the reviewer's "layer 1 is lower" is not evidence either way). Built: the lower roadway held LEVEL at `LOWER_H` 5.80 m on the straight (was solved 6.3-8.0, sloping) = 4.6 m clearance + 1.2 m deck over the building-passage roads [inf: the lowest plausible level; i1 reads ~1 m lower relative to the plate, which would put L3 ~1 m above spec_itb 11.5 - request to the ITB group]; its sidewalk (`sidewalk`, 5.95 m) from the lower roadway to 3.0 m under the plate edge [inf width] closes the 0.4-0.6 m slit; island B is now the deck-edge planter (0.95 m, NAIP colour, concrete walls) instead of a red-painted kerb. Plan coverage across the frontage (`slit_c3.py`, every up-facing roadways / ITB triangle 4-14 m AGL) u -45..40: kerb -> plate (11.3) -> planter (12.3) -> sidewalk (6.0) -> lower roadway (5.8) v -30.2..-74.6 with no gap; the only plan gap is the 0.13 m kerb face | `c3/integration/ev/` (i1_left/right.png, i1prof.png, naip_plate_h12.png, osm_h12.png), `rv/slit_c3.json`, BR-02 `out/buildings3d/roadways_itb_plate.png`, `manifest.json#roadways` observed / inferred / unknown |
| integration-3 | deck over deck 3.7 m2 at 4.55-4.59 m (minor) | **fixed by a local trim**: `trim()` cut stacked overlaps only when the MEDIAN separation was short, so a stacked pair whose median cleared kept the short part (739695588 under 681667027: 1-5 cm short over 3.7 m2; with the lower level held at 5.80 m, 739695588 beside the layer-3 ramp 1205493778 north of the ITB: 23.6 m2 at 3.29 m in r16). New `partial_stacked_cut`: the lower deck gives up the 1-m cells of the overlap with less than deck + clearance (+ STACK_GAP + half a cell diagonal), only where that trims its edge (a cut that would split the deck or open a hole is refused and left to the check). Result: roadways over roadways min **4.61 m, 0 m2 below 4.6** (r14 4.55 m / 3.7 m2). Tried and dropped: a raise-only 8 % grade envelope in the level solve (moved the 681667027 kink to 220862132: 27.8 %, ramps 20 %; with a guard 15.6 %) and a 0.12-m separation margin for stacked pairs (15.6 %); `roadways_net.py` is unchanged. Side effect left open: max grade 14.1 % on 681667027 (r14 13.5 %), a kink at a node the deck-over-deck constraint fixes 0.9 m above its neighbour, moved by the lower level | `c3/integration/an/` (v_*.log, prof_*.log), `roadways_build.json` |
| integration-4 | phone delivery unmeasured / uncompressed, doc sizes stale (minor) | **partly fixed**: per-view JS heap now measured (exact V8 heap through the DevTools protocol after a forced GC, `b3d_views_job.mjs`; `performance.memory` was bucketed); doc sizes corrected (Bundle and delivery above: 271 files / 73.1 MB, landside.glb not shipped, largest file 11.58 MB, two publishes); the WASM question is put to the owner's phone: the test card now reports "WebAssembly: compiles / blocked" and the JS heap (`phone_artifact_page.py`). **Not done**: meshopt / KTX2 (needs that answer, then WASM decoders under vendor/** - env), a run on a real phone (owner) | phone table below; `integration_closeout.md` R3.4 |
| integration-5 | per-building footprints not in integration.js (minor) | **fixed**: `B3D_INTEGRATION.footprints.units[group][unit]` (tower, ITB, domestic: 14 units, +138 kB) with `body` / `over` height tiers; the landside units stay in integration.json (bridges never reach them). Bridges can now drop the Museum proxy / own-strip rule (bridges-6) | `integration.js` |
| integration-6 | tower cab glass glows teal at night (minor) | **fixed**: `GLOW_DEF.cab` k 0.25 -> 0 (off) by default: the only dusk / night photo (t5) shows the cab dark under the lit LED ribbon. The whole glow table is listed as inferred and configurable (`SFO.R.b3d.setGlow`) in `manifest.json#integration.glow` | `js/three/buildings3d.js`, manifest |

**Plausibility, before / after** (`b3d_integrate`, every LOD of every file):

| Check | r14 (6 Nov, round-2 assets) | base r15 (7 Nov assets, round-2 code) | r18 (this round) |
|---|---|---|---|
| conflicts / notes | 4 / 10 | 3 / 9 | 2 / 11 |
| road deck inside a building | 0 (after a 1,406.5 m2 cut at T2) | 0 (no T2 cut needed) | 0 |
| roadways over roadways < 4.6 m | 3.7 m2, min 4.55 m | 3.7 m2, 4.55 m | **0 m2, min 4.61 m** |
| guideway deck over a road deck | min 4.62 m | 4.62 m | 4.62 m |
| guideway pier caps / columns in decks | 3.25 m (8.6 m2) / 3 | 13.85 m / 1 (0.48 m beside a deck) | 13.85 m / 0 (1 note: beside, 0.48 m) |
| ITB curb void / canopy over the plate | 0.134 m / 4.52 m (87 m2) | 0.134 / 4.67 m | 0.134 / 4.67 m |
| ITB plate -> outer band | 0.4-0.6 m open slit, lower deck 6.3-8.0 m sloping | slit, 6.87-7.20 m | closed; lower level 5.80 m level, sidewalk under the edge |
| at-grade roads under a deck < 4.6 m (new) | - | - | domestic loop 26 roads 3.53 m (by design, owner); interchange_2_2 1 road 4.597 m over 2 m |
| BART station vs taxilane 302 | conflict | conflict | note: observed NAIP wall 35.8 m from the lane (existing condition) |
| max deck grade | 13.5 % | 13.5 % | 14.1 % (681667027, open) |
| LOD2 check / check.py | 47 / 0; 0 / 0 / 17 | - | 47 / 0; 0 / 0 / 17 |

**Phone run, close-out round 3** (`out/buildings3d/integ/c3/low/`, live3.html `tier=low` near mode, headless Chromium on llvmpipe
960 x 540, all five groups incl. the landside units, r18 roadways, the 7 Nov assets; served from a frozen copy of the working
tree; one page, views in this order, 41 min under the heavy lock). JS heap = the exact V8 heap after a forced GC (DevTools
`Runtime.getHeapUsage`; `performance.memory` read 561 / 631 MB in its buckets). Round-2 values in brackets.

| View | Draw calls | Frame triangles | b3d triangles (LOD0 / 1 / 2 units) | b3d geometry | Textures | JS heap used / total | Landside units |
|---|---|---|---|---|---|---|---|
| page ready (lod2 files, 420 s) | - | - | - | - | - | 99.0 / 106.7 MB | 0 |
| `pierB` gate B20, 110 m | 576 (560) | 1.62 M | 137 k (6 / 40 / 0) | 25.2 MB | 573 MB (568) | 98.5 / 101.9 MB | 2 |
| `towercam` | 1,617 (1,583) | 3.72 M | 235 k (12 / 37 / 0) | 31.0 MB | 621 MB (607) | 122.5 / 127.9 MB | 5 |
| `gateA1` gate A1, 60 m | 1,341 (1,308) | 2.90 M | 262 k (28 / 24 / 0) | 34.4 MB | 634 MB (631) | 140.6 / 145.7 MB | 8 |
| `itbwest` 520 m west | 2,279 (2,176) | 4.14 M | 238 k (14 / 40 / 2) | 39.2 MB | 637 MB (639) | 174.6 / 179.8 MB | 12 |
| `i1like` photo-i1 direction, 300 m | 1,500 | 3.19 M | 208 k (15 / 37 / 1) | 33.4 MB | 642 MB | 165.2 / 172.1 MB | 9 |
| `plateedge` the plate edge from the WSW, 45 m, 35 deg | 1,260 | 2.44 M | 298 k (35 / 20 / 0) | 38.6 MB | 638 MB | 175.7 / 181.8 MB | 11 |
| `far` east of the airport | 240 (233) | 0.89 M | 62 k (4 sets at LOD2) | 23.2 MB | 605 MB (606) | 145.3 / 149.8 MB | 0 (12 released) |
| `release` 150 s later | 240 (224) | - | - | - | **536 MB** (537) | 125.3 / 130.2 MB | 0; the four group files back to lod2 |

The round-2 near mode holds on the current assets: units load near the camera and all go again, the group files fall back to
their lod2 files, textures return to 536 MB; the JS heap stays at 99-176 MB through the near views and drops to 125 MB after the
release. The cost of the round's assets is +2-10 % draw calls and +1-21 k building triangles against round 2. `plateedge`
(`cmp_new_plateedge.png`): kerb, inner and bus roadways, planter, the step face down to the lower level, the lower roadway and
its fascia - no ground showing between the plate and the lower level. Not measured: a real phone (owner; the test card now
reports WebAssembly and the JS heap), GPU memory beyond `texturesSize`.

### Close-out round 3, fix round 2 (7 Nov 2026): dispositions of the independent verifier's findings v1-v8

Inputs: the verifier's findings on round 3 (`closeout3_findings.json#groups.integration`, verifier round 1, v1-v8) and the
buildings track's fix-2 rebuilds (domestic 13:11Z, landside 13:15Z / units 13:48Z, ITB 13:16Z, tower 13:22Z; buildings R3.11,
R3.12). Runs (scratch `c3/integration/`): r19 (first build of this round), r20-r22 (r20: STK at 6 %, the T2 curb margin; r21: + the against-asset edge faces, at-grade floor margin; r22: + a flat floor 4 m either side of an at-grade crossing - final, 15:30Z; `roadways.glb` 4.58 MB, `integration.js` 229 kB). Verification used the
verifier's own scripts (`f2/rv`: width2, slopes, overhead, near, planplot2) plus `f2/creases.py` (fold angle between adjacent
deck-top triangles), `f2/t2slot2.py` (T2 curb seam) and `f2/an_tiers.py` (the verifier's fpval4 rule for the tiers).

```bash
python3 tools/blender/build_roadways.py      # ~2.5 min, ~0.5 GB: + stacked pairs held in the level solve (roadways_net STK_*), stacked cut along the upper deck's edge, against-asset edge faces, T2 curb check
python3 tools/blender/verify_landside.py; python3 tools/blender/b3d_integrate.py   # ~3.6 min, ~0.5 GB: + footprint tiers buffered + self-check
python3 tools/blender/b3d_lod2_check.py; python3 tools/sat/check.py
```

| # | Finding | Disposition | Evidence |
|---|---|---|---|
| v1 | the round-3 `partial_stacked_cut` bit 1-m cells + round buffers out of the lower deck: scalloped edge, wavy parapet, 739695588 down to 3.5 m (major, regression) | **fixed at the root**: the cell cut is gone. (1) The level solve now holds stacked pairs itself (`roadways_net.py` STK_*): every 2 m along the overlap of two elevated ways of different layers without a shared node, the lower way's node is a constraint (deck top to deck top >= 1.2 + 4.6 + 0.05 m), met by LOWERING the lower way under the upper deck (the upper keeps its profile), spread as a 6 % grade cone, never below its clearance over the at-grade roads it crosses (+0.10 m, flat 4 m either side), never moving an anchored / plate node. 15 pairs sampled, 8 held this way (167 nodes, max 1.64 m: 739695588 under 681667027 / 1205493778 / 1483716495, 41015123 under 681667031 ...). (2) What the solve cannot hold goes to `stacked_cut()`: the lower deck gives up the overlap grown by STACK_GAP (0.6 m) along the upper deck's edge (mitre buffer, simplified 0.05 m: a straight line, the parapet on it); the cut is REFUSED - the deck kept whole and the pair reported - where it would split the lower deck or leave less than lanes x 3.0 m (+ shoulders), as long as the clearance kept is >= 3.5 m (below that the decks would clash and the cut stands, reported as narrowed). Result: 739695588 north of the ITB keeps its full ribbon, 8.2-8.8 m measured across x -1396..-1376 (r18 3.5-4.0 m over x -1392..-1386); no notch under 681667027; straight parapets (plan plots). Refused, reported as a conflict: the ITB loop's lower roadway 41015123 under its anchored departures legs 38853121 / 38853045 (deficit 0.74 m: 11.35 m plate vs the 5.80 m lower level, see v4 / R3.2) - min 3.88 m over 88.6 m2 (`b3d_integrate`; 161 m2 by the verifier's `overhead.py`), which round 3 had hidden by cutting the lower road away under the leg (a road that stopped under the ramp, r18 plot); and 394222196 under 35157016 (4.58 m by the trim's centreline estimate, 4.61 m on the mesh) | `f2/plots/scallop_r19.png`, `notch_r19.png`, `refused_r18/r19.png`; `roadways_build.json#stats.stacked` (solve + cuts); manifest#roadways deviations |
| v2 | steepest deck grade 13.5 -> 14.1 % on 681667027 (a 0.8 m hump) (minor) | **fixed**: the hump came from the per-crossing deficit raise at one node of a stacked pair; stacked pairs no longer take that raise (they are held by lowering the lower way, v1). 681667027 max 4.3 % (was 14.1); overall max 13.4 % (41015033 in interchange_2_2, unchanged since r14); ways > 8 %: 20 -> 20 (decks 13, ramps 12). The lowered 739695588 first ran at the 8 % cone over ~150 m (mesh triangles 8.0-9.7 % on its curves, r19); the cone is now 6 % (same 8 pairs held, same deficits left): its node grade <= 6.0 %, the ITB lower roadways' deck triangles max 8.1 % (r18 49.5 / 10.7 %), deck triangle area over 8 % in the ITB unit 573 -> 468 m2 | `slopes.py`, `f2/solve_g*.log`, `roadways_build.json#stats.grades_over_8pct` |
| v3 | exported footprint tiers miss 0.5-3.9 m of vestibules, junction walls, outrigger tips (minor) | **fixed**: each tier region is grown by the ring tolerance (0.1 m, mitre) before it is simplified, so the simplified ring stays outside every vertex; pieces down to 0.02 m2 are kept (were dropped below 1.0 / 0.25 m2: the T1 / BA_C junction wall, door bins); a self-check in `b3d_integrate` tests every LOD0 / LOD1 vertex above the ground plate against the admissible tiers of its own unit (body always, over when its underside <= vertex y + 0.15): **155,560 vertices, 0 outside** (max 0.00 m). The verifier's rule (any unit's tiers) on the same assets: 0 of 14 units with a vertex outside (`an_tiers.log`). `integration.js` 182 -> 229 kB | integration.json#footprints_js.self_check, `f2/an_tiers.log` |
| v4 | integration-2 residuals: OSM 1164416297 mis-cited, south-end parapet opening, stale unknown, the level question (minor) | **fixed / kept with the owner**: (1) 1164416297 cited correctly everywhere (code comment, `sidewalk` material note, manifest#roadways.unknown, the round-3 row above): it runs at v ~ -48 under island A, ~16 m inside the plate edge, i.e. it argues for a lower level that runs much further under the deck than the modelled 3.0 m - recorded as unknown. (2) The opening: deck-edge segments took the class of their MIDPOINT, so a segment spanning the corner where the sidewalk meets the lower roadway was "inner" over its whole length; `edge_runs()` now classifies every 0.5 m - the parapet is continuous round the corner (left: a 0.08 m joint between the 6.65-m and 6.80-m parapet tops of the two levels). (3) manifest#roadways.unknown rewritten (the straight is held at 5.80 m; beyond it solved and lowered under the stacked ramps). (4) The ~6.7 m photo step vs the modelled 5.55 m stays with the owner / ITB group (R3.2); it is also the cause of the v1 refused pair | `f2/plots/walkend_r18/r19.png`, manifest#roadways |
| v5 | phone probe: V8 heap only, `performance.memory` bucketed / Chromium-only, two clipboard writes (minor) | **fixed** (the real-phone run stays the owner's): the test card's memory row now adds what any browser can count - the bytes of the scene's geometry ArrayBuffers (unique BufferAttribute arrays + indices under `SFO.R.engine.scene`) and three.js' texture estimate - plus `performance.measureUserAgentSpecificMemory()` where the page is cross-origin isolated; "JS heap" is labelled "V8 only". "Copy results" is built by the probe alone: one capture-phase handler composes the whole text from the card's rows and writes the clipboard once, stopping the template's handler. `b3d_views_job.mjs` records `arrayBufferMB` (CDP `Runtime.getHeapUsage` backingStorageSize) and `embedderHeapMB` next to the V8 heap. Tested on the stub-assembled page (`f2/pagetest`): in headless Chromium (`f2/probe_test.mjs`, under the heavy lock) one `writeText` per click, identical to the text shown, holding the template's rows (frame rate, frame time, GPU) and the probe's (WebAssembly: compiles; JS heap (V8 only); Geometry / textures - shared ArrayBuffers counted once); the same in a node-VM run of both scripts (`f2/probe_vm.mjs`). The high-tier run below shows why it matters: ArrayBuffers 587-598 MB against a V8 heap of 402-428 MB | `tools/build3/phone_artifact_page.py`, `out/buildings3d/integ/c3f2/high/probe_test.log` |
| v6 | a 0.27 m crease (49.5 % sliver) in the lower roadway at (-1312.3, 476.6) (minor, pre-existing) | **fixed**: it sat where the round-2 / round-3 cut ended 41015123 under the departures leg 38853121; with that cut refused (v1) the deck runs through on a smooth lowered profile. Fold angle between adjacent deck-top triangles: max 6.5 deg (interchange_2_2, unchanged), none on the ITB lower roadways above 4.6 deg (r18: 28.4 deg there) | `f2/creases.py` |
| v7 | two plausibility conflicts open: domestic loop 3.53 m over 26 at-grade roads, interchange_2_2 4.597 m; building-passage roads not drawn (minor) | **kept open, honestly listed**: the domestic loop is the published 16-ft T3 L1 -> L2 step with the generic 1.2-m deck (owner: a posted-clearance photo or sign); interchange_2_2 is 3 mm short over 1 m, between the solve's nodes (numerical). The building-passage roads are the static track's (R3.6a, re-sent) | `b3d_integrate` |
| v8 | the high tier not re-run in round 3 (minor) | **done**: one high-tier page (`tier=high`, headless Chromium on llvmpipe 960 x 540, served from a frozen copy of the final tree - r22 roadways, the 229-kB integration.js, the fix-2 building assets - 16:20-17:59Z under the heavy lock): every asset loaded (tower / ITB / domestic / roadways full files, all 24 landside units, `failed` empty), ready after 86 min (llvmpipe compile 200-330 s per large file). Views (round 2 r4/high in brackets): `itbwest` 3,120 draw calls (2,869), 6.24 M frame tris (5.32 M), b3d LOD0 / 1 / 2 sets 36 / 24 / 8, b3d geometry 45.9 MB (44.5), textures 1,197 MB (1,202), V8 heap 402 / 528 MB, ArrayBuffers 587 MB; `plateedge` 1,850 / 3.59 M / 591 MB ArrayBuffers - kerb, departures lanes, planter, step face, lower level and its roadway continuous, no ground between them; `t2curb` 1,996 / 4.73 M (the round-2 camera; it frames T2 from the garage roof, not the seam) | `out/buildings3d/integ/c3f2/high/` |

**Also done (buildings R3.12, the T2 curb slot).** The deck stopped 0.10 m short of every asset's occupancy and had no edge
face where it met one, so a 0.10-0.20 m seam open to grade ran along the T2 curb. Against the domestic group the margin is now
0.02 m (`ASSET_BUF_DOM`), and a deck edge against an asset gets its fascia (the edge face, no parapet): T2 curb seam median
0.145 -> 0.065 m (plan, 544 sidewalk-edge points; the rest is the deck outline's simplification), with ~122 m of edge face along
it (r20: none). `build_roadways` now checks it (`stats.curb_gap_t2`, measured on the deck polygons before meshing: median 0.065 m, its 0.05-m
target not met - residual, the outline's simplification; closing it fully would need the deck under the sidewalk slab, which the
solid tests would flag as an overlap).

**Phone artifact sizes after this round.** Building files the artifact ships (B3D=all: every `*.glb` but `landside.glb` and the tower's
alternative family, plus the 29 shared landside images): 33 + 29 files, 55.9 MB; largest `domestic.glb` 11.37 MB (< the 15-MB
per-file limit, no split needed); `roadways.glb` 4.29 -> 4.58 MB (the against-asset edge faces); `integration.js` 182 -> 229 kB.

**Plausibility, before (r18, the verifier's state) / after (r22)** (`b3d_integrate`, every LOD of every file):

| Check | r18 | after |
|---|---|---|
| conflicts / notes | 2 / 11 | 3 / 11 |
| roadways over roadways < 4.6 m | 0 m2 (min 4.61), with the scalloped cuts | 88.6 m2, min 3.88 m (the verifier's `overhead.py`: 161 m2, min 3.88 m): the refused ITB pair 41015123 under 38853121 / 38853045 (owner / ITB R3.2); the other refused pair, 394222196 under 35157016, is 4.58 m by the trim's centreline estimate and 4.61 m on the mesh |
| at-grade roads under a deck < 4.6 m | domestic loop 26 roads 3.53 m; interchange_2_2 4.597 m over 2 m | domestic loop 26 roads 3.53 m (owner); interchange_2_2 4.597 m over 1 m (r21 had a third, 4.59 m over 93671776 next to the lowered 41015123: fixed in r22 by the flat floor) |
| road deck inside a building / ITB curb void | 0 / 0.134 m | 0 / 0.134 m |
| guideway deck / pier caps over decks | 4.62 / 13.85 m | 4.62 / 13.85 m |
| max deck grade (ways > 8 %) | 14.1 % (20) | 13.4 % (20) |
| footprint tiers: vertices outside | not checked (verifier: up to 3.9 m) | 0 of 155,560 |
| LOD2 check / check.py / verify_landside | 47 / 0; 0 / 0 / 17; 195 / 0 | 47 / 0; 0 / 0 / 17; 198 / 0 (the landside group added 3 checks) |

<!-- integration:end -->
