# Phase 2d: terminals, tower, hangars and surroundings

Date: 2026-11-20. Package P2d of Phase 2 (docs/PLAN.md §7). Fork base: sfo3d @ **e3218d6**, plain WebGL2 `live.html`
path (working default Q7). Nothing in `sfo3d/`, `pc12/` or `hwd3d/` was modified; nothing was committed. A previous
attempt (2026-11-14) left no P2d files behind (`git status` showed none), so everything here is new.

Tags as in docs/PLAN.md: **obs** = observed (OSM outline, AIP fact, measurement); **inf** = inferred (rule, modelling
parameter, reading of a photo).

Result. The core placeholders (436 extruded footprints and the round tower stand-in) are replaced by:
- T2 split into its main hall, central concourse, two finger piers and two linear arms;
- T1 split into a two-tier airside concourse, an airside core, a landside louvre block and the central hall;
- the east control tower, modelled from photo 02;
- the two untyped south-west towers;
- four hangars with door walls and roof forms;
- the business-aviation terminal (FBO), the VVIP annex and the other airport buildings;
- the Hongqiao transport hub (railway station, platform canopies, bus terminal, T2 metro station, car parks), at low
  detail;
- the 397 context buildings of the 23.5 km² extent, as LOD blocks;
- canal and river bank kerbs.

The flat grey ground beyond the extent (the "island" of `core_overview.png`) is replaced by a low-detail ground. It
shows ESA WorldCover 2021 class colours at 50 m, with no buildings, no roads and no imagery, and fades into haze.

---

## 1. File map

| File | Status | Content |
|---|---|---|
| `tools/buildings/build_buildings3d.py` | new | OSM outlines → building volumes: zones, heights, styles, roof overhangs, hangar door sides, checks → `data/sha_buildings3d.json` / `.js` (`window.SHA_BUILDINGS3D`) |
| `data/sha_buildings3d.json`, `.js` | new (generated, 34 KB) | 41 parts, 3 towers, 4 hangars, 40 claimed ids; ODbL (OSM-derived) |
| `tools/terrain/worldcover_far.py` | new | ESA WorldCover 2021 20 km crop → 50 m class fractions → colour (calibrated on Sentinel-2) + attributes → `data/sha_landcover_far.js` (`window.SHA_LANDCOVER_FAR`) |
| `data/sha_landcover_far.js` | new (generated, 371 KB) | colour JPEG + attribute PNG, 398 × 399 px over 19.9 × 19.95 km; CC BY 4.0 |
| `js/world/buildings3d.js` | new | geometry. The wall / cap / rooftop-plant / skylight helpers are **forked from sfo3d@e3218d6 js/live/terminals.js** (header says so) and rewritten for injected data. Facade layers by style, roof slabs and overhangs, hangars, control tower, block towers, context LOD blocks, bank kerbs |
| `js/live/terminals.js` | **replaces the stub** | the extension: `claimBuildings`, `shaderChunks.sha_ground_far`, `groundUniforms`, `buildWorld` (items, `anchors.tower`), `start` (credits); exports `buildingsCredits()`, `terminalsInfo()` |
| `js/shaders/ground.js` | **core file, edited** (hook only) | new chunk hook `sha_ground_far` (`shaGroundFar`, `shaGroundFarHaze`). Its default returns the neutral colour and no haze, so the output is **identical** to the core's when no extension redefines it (§5) |
| `live.html` | **core file, edited** (2 lines) | `<script src="data/sha_buildings3d.js">` and `<script src="data/sha_landcover_far.js">` |
| `jobs/buildings.mjs` | new | named building views, photo-match views (4:3 viewport), info print |
| `tools/buildings/compare_plates.py` | new | photo 02 vs render plates (`buildings_compare_*.png`), CC BY-SA 4.0 with credit strip |
| `tools/buildings/test_buildings3d.mjs` | new | node geometry checks without WebGL: no NaN, triangle winding vs normals, walls facing out of their footprints, tower top ≤ the AIP obstacle height, hangar door normal, bridge attach points (**all passed**) |

## 2. Inputs, and what is observed and what is inferred

| Input | Used for | Status |
|---|---|---|
| OSM building outlines (`data/sha_airport.json` `buildings[]`, `context.buildings[]`, pinned extract) | every footprint; the airside facades that the jet bridges attach to are **never moved** (check §3.5) | obs (T1 outline `source=estimation`) |
| B3 heights (`data/meas/b3_building_heights.json`, standards_refs.md §3) | T2 main hall 22, central concourse 21, T1 central hall 26, T1 concourse 9, China Eastern hangar 33.5, big east hangar 28.5, NE hangar 16 | inf (measured; uncertainty ±2–5 m) |
| AIP (mirror) obstacle "Control TWR" 47 m elevation | east tower 44.5 m above ground_y 2.5 | AIP (mirror) |
| Commons photos (photos_credits.md, contact sheet) | proportions, roof forms and facade rhythm only. Nothing is traced or textured | inf |
| ESA WorldCover 2021 v200, 20 km crop (`refs/cache/landcover/derived_zsss/`) | far-ground class fractions | obs (land cover), CC BY 4.0 |
| Sentinel-2 L2A `S2B_51RUQ_20261014_0_L2A` (committed crop, inside the extent) | per-class colour calibration of the far ground | obs |
| Rule heights of `data/sha_airport.js` (HEIGHT_RULES) | every other building | inf |

## 3. The parametric terminal model (`tools/buildings/build_buildings3d.py`)

Each terminal volume is the OSM polygon intersected with a modelling zone, so the union of the parts equals the OSM
outline. Check: T2 143,375.67 m² = 143,375.67 m². T1 54,355 of 54,362 m²; the 7 m² difference is slivers narrower
than 8 m, dropped from the core and landside parts. The split lines are world x / z values read from the outline plots
and the aerial photos 21 / 22 / 24 [inf].

### 3.1 T2 (osm:relation/21913345; photos 09–17, aerials 21 / 22 / 24)

| Part | Zone | Height (m) | Style | Basis |
|---|---|---|---|---|
| main hall | x ≤ −1238 | 22 | glazed walls, deep flat roof slab with a **6 m overhang** | B3 "T2 main hall" 22 ± 4 (Umbra 21.4 + DSM p90 22.2); deep roof edge from photos 07 / 08 / 11 |
| central concourse + core | −1238 < x ≤ −1098, −150 ≤ z ≤ 492 | 21 | 4.5 m apron-level service facade, curtain wall, light-grey fascia, skylight spine, rooftop plant | B3 Umbra layover on **its** west wall (x −1140, z 307–490): 21.4 ± 3.3 |
| north / south finger pier | x > −1098, z < 100 / > 300 | 15 | as the concourse, lower | rule: apron level + two glazed levels + roof (photos 09, 14, 15) |
| north / south linear arm | x ≤ −1098, z < −150 / > 492 | 15 | as the piers | rule |

### 3.2 T1 (osm:way/93184730, `source=estimation`; photos 01–05; photo 02 = airside from RWY 18L/36R)

The airside concourse is a band along the west facade (x_f(z) = 457 + 0.047 (z − 20)) and the north facade
(z_f(x) = 19.45 − 0.0513 (x − 467.5)), both fitted to the OSM points.

| Part | Zone | Height (m) | Style | Basis |
|---|---|---|---|---|
| concourse, front tier | 0–12 m (west) / 0–14 m (north) from the facade | 9 | dark apron-level recess, white band, glass band, white fascia | B3 photo ratio 8.9 (7.3–10.8) |
| concourse, rear tier | 12–32 / 14–34 m | 13 | white, upper glass band | photo 02 at the B3 scale: the set-back tier is 40 px → 13 m [inf] |
| airside core | rest of the outline, x ≤ 553 | 15 | white with window rows | rule |
| landside block | rest, x > 553, z < 140 | 24 | stacked silver louvre bands, glazed clerestory, 3 m roof overhang | rule; facade from photos 01 / 03 / 05 |
| tower yard | a 30 m square around the tower node | – | open: the tower rises from the ground behind the concourse (photo 02). A round cut showed as a curved wall, so it is square | resolves core open issue 5 |
| central hall | osm:way/590426959 (claimed) | 26 | west face: fritted glass from 13 m up (photo 02); other faces: louvres + clerestory | B3 photo ratio 26.4 (23.0–30.1). This OSM way is taken as the hall because its west face is where B3 placed the hall front (x ≈ 560, z ≈ 240) [inf] |
| VVIP annex | osm:way/1443258835 | 10 | white, dark apron level, window row | photo 02, right edge |

### 3.3 Towers

- **East control tower** (osm:node/3342630333): 44.5 m (AIP (mirror) 47 m elevation − ground 2.5 m). Its form is
  measured on photo 02 (1920 px) at 0.356 m/px (the B3 scale: 125 px = 44.5 m at about 500 m), ±1 px = ±0.36 m:
  - square shaft 7.7 m wide, with a dark vertical slot on the face towards the runways;
  - inverted frustum head from 29.5 m to 39.8 m (7.7 → 15.8 m), with small windows in rows at 32.6 m and 37.9 m;
  - octagonal (chamfered-square) cab glazing from 39.8 m to 43.0 m, leaning outward (10.5 → 12.1 m);
  - roof slab from 43.0 m to 43.9 m (12.6 m wide) and a set-back roof block to 44.5 m. Nothing goes above 44.5 m,
    because the AIP obstacle elevation is the highest point; an earlier version had a 5.5 m mast, which was removed.
    `test_buildings3d.mjs` checks the top.

  The plan orientation is unknown, so it is aligned with the runway grid 177.33° [inf]. The app's tower-cab eye is now
  `anchors.tower.eyeY` = ground + 41.4 m (cab floor + 1.6 m), replacing the stand-in's.

  From that eye the in-app Tower view looks out through the cab glass (back faces are culled), with the roof-slab
  underside as the ceiling and a 0.6 m floor / console band below. The band is matte charcoal with a faint fill
  [inf]. The object shader has no occlusion under the cab roof, so a light or glossy floor is lit by the sky alone and
  turned a sky-blue that read as water; the first phone render showed this.
- **South-west towers** (osm:way/1576039982, 1576039987; untyped `man_made=tower`, added 2026-11-06, role unknown):
  the OSM footprint (≈ 17.8 m square) is extruded to the 35 m rule, with a dark band near the top and a rooftop mast
  [inf]. They stand inside the two fan-shaped office complexes. The orange-and-white tower of photos 17 / 25 is
  **not** placed: its location is not established (standards_refs.md §2.3).

### 3.4 Hangars, FBO, other buildings, hub

| Building | Height (m) | Door side (computed) | Roof | Basis |
|---|---|---|---|---|
| China Eastern hangar (osm:way/327613444) | 33.5 (eaves) | east (pavement share 0.67) | one shallow barrel, ridge parallel to the door, rise 4.5 m | B3 SAR (clean box profile); form: aerial 22 [inf] |
| big east hangar (327473856) | 28.5 | south (0.88) | 4 vaults front-to-back (one per bay), rise 3.9 m | B3 SAR (moderate); 4 bays: aerial 21 [inf] |
| small east hangar (327473860) | 22 | south (0.95) | flat | rule |
| north-east hangar (328013621) | 16 | west: no pavement polygon in front of any side, so the side nearest to pavement (118 m) | flat | B3 SAR (moderate) |

- **Door rule:** the door wall is the side of the minimum rectangle with the most airside pavement 15–70 m in front.
  Door leaves reach min(26, 0.72 h) m, under a darker header and between jambs [inf].
- **FBO** (osm:way/469610770): a glazed two- to three-storey pavilion, 12 m (rule). Its 10,527 m² neighbour
  (469610771) may hold the business-aviation hangars (field.md: FBO hangar 4,500 m²). This is unverified, so it is
  drawn as a metal-clad service block.
- **Other airport buildings:** metal-clad service blocks, offices (China Eastern office), the hotel and the car parks
  (facade with open decks, cars on the roof), all at the data's rule heights.
- **Hub** (context, low detail): the railway station main building and the bus terminal are glazed halls with a 6 m
  roof overhang (rule heights 25 / 20 m). The two platform-canopy outlines (53,000 / 52,000 m²) are roof slabs at
  8 m on a 24 × 18 m column grid [inf].

### 3.5 Checks at build (`checks` in `data/sha_buildings3d.json`)

- **Bridge attach points:** all 56 lie on a part boundary, max 0.01 m. The airside facades are the OSM outline, so the
  gates package's fixed links meet the walls.
- **Tower yard:** the tower node lies inside the T1 yard.
- **Area split:** as above.
- **Determinism:** both generators were run twice; the outputs are byte-identical (md5).

## 4. Context LOD blocks and banks

- **Context blocks.** The 397 context buildings of the extent, minus the hub parts, are drawn as one low-detail block
  each:
  - walls to the data height (rule heights, inf; 6 are OSM `height`);
  - a parapet and a flat roof;
  - the facade by kind: punched windows for housing, hotels and small offices; glass for offices of 28 m or more;
    corrugated metal for industrial buildings; concrete panels otherwise;
  - a tint from a 6-colour palette chosen by id hash [inf].

  They are grouped into 4 quadrant items, for culling.
- **Banks.** The water surface stays the core ground shader's. Low embankment kerbs (0.5 m high, 0.35 m wide) run
  along the OSM water areas, and along the river, canal and stream lines outside them, at the core's drawn half-width
  [inf]. That is 67 km of kerb, about 10,600 triangles.
- **Totals:** 11 items, 57,267 triangles. `buildWorld` takes 70–120 ms here.

## 5. The far ground beyond the extent

**Data** (`tools/terrain/worldcover_far.py`):
1. Each pixel of the local 20 km WorldCover crop (10 m, EPSG:4326) is mapped to the world frame. The exact frame is
   evaluated on a 41 × 41 grid and interpolated in between; the interpolation error is 0.002 m.
2. Pixels are binned into 50 m cells, giving class fractions per cell. Shares over the crop: built-up 64 %, tree 19 %,
   cropland 9 %, grassland 4 %, bare 3 %, water 2 %.
3. Class colours are the median Sentinel-2 L2A reflectance on pure pixels (the same class in the 3 × 3 neighbourhood)
   **inside** the extent, so the far ground continues the extent's Sentinel-2 colour:
   - built-up 0.107 / 0.099 / 0.087;
   - tree 0.029 / 0.045 / 0.027;
   - cropland 0.104 / 0.091 / 0.063;
   - water 0.044 / 0.055 / 0.047;
   - grassland and bare are also calibrated; shrubland, wetland and the other absent classes keep fallback values
     [inf].
4. Output:
   - colour = Σ fraction × class colour, stored as a JPEG;
   - attributes = water fraction, built-up fraction, and the distance outside the extent (0–6 km), stored as a PNG.

**Legal default kept** (PLAN §6b Q3 and this brief): detail stays inside the 23.5 km² extent. Beyond it there are no
buildings, no roads and no imagery: only land-cover class fractions on 50 m cells. That is five times coarser than the
source, and coarser than the 10 m / 0.5 m imagery thresholds of PLAN R3. ⚠ PLAN R3 also says the WorldCover and DEM
crops "will be cut to that extent" under the 25 km² default. This package follows the lead's brief (low detail
beyond the extent); the owner should confirm (§8).

**Shader** (the `sha_ground_far` hook, defined in `js/live/terminals.js`):
- **Colour:** the class colours. Built-up cells are darkened to 0.9× for the streets and shadows a 50 m cell cannot
  resolve, and get a per-cell roof tone: 60 m cells with a bounded warp, 6 % lighter roofs and 3 % blue steel roofs
  (aerials 21 / 24). The variation fades out beyond 15 km. An earlier unbounded warp drew swirl patterns; it was
  replaced.
- **Water:** water fractions above 0.35 get the core's sky-reflecting water.
- **Night:** a warm urban glow on built-up cells, 4× the core's in-extent glow factor so the plain reads as a lit city
  [inf]. The first night render, with the core factor, showed almost no glow.
- **Beyond the crop** (±10 km): the crop's mean colour.
- **Haze** [inf]: a = 1 − exp(−max(d − 2.5 km, 0) / 14 km), ramped in over the first 4 km **outside the extent** (the
  distance outside is a channel of the attribute map). So the extent edge shows no step, and the buildings (all inside)
  need no extra haze.
- **Haze colour:** the renderer's sky base (`R.skyBase`, the texture the sky pass draws), sampled at the horizon in
  the view direction. Towards the 80 km mesh edge the direction tends to the actual view ray, so the ground meets the
  sky drawn beyond the mesh without a step. The texture is bound in `start()`, once the environment exists; before
  that the env map is used. An earlier version hazed to the env map (`uSkyTex`), whose colour differs from the drawn
  sky, and left a tan band at the horizon.
- **Switches:** `?far=0` keeps the core's neutral ground, and `?bld=0` keeps the core placeholders (QA).

## 6. Renders and comparison with the photos

All renders are at deviceScaleFactor 1, `?fixedres=1&quality=high`, 2026-11-14 03:00Z (11:00 local), SOFTGL=1
(llvmpipe). I looked at every one.

**How the last views were rendered.** While this package finished, the parallel UI package (P2e) was editing
`entry.js`, `app.js`, `ui.js` and `about.js` in the working tree. `entry.js` imports a `./shell.js` that did not exist
yet, so the working tree could not boot. The tower views (re-rendered after the tower top was capped at the AIP
height), the night views and the phone views were therefore rendered from a scratch copy of `sha3d/`: this package's
files, with the seven P2e-edited files restored to HEAD 81be988. Every other view was rendered from the working tree
before P2e's edit landed. Once P2e's `shell.js` had landed, the overview was rendered once more from the working tree,
as an integration check: the extension loaded (41 parts, 397 context blocks, 57,267 triangles, tower anchor eye
43.9 m) and the image matched `buildings_overview.png`.

```
SOFTGL=1 OUT=docs/phase2 PREFIX=buildings node livetest.mjs jobs/buildings.mjs
SOFTGL=1 OUT=docs/phase2 PREFIX=buildings_night T=2026-11-14T13:30:00Z VIEWS='overview;t2_close;t1_close' node livetest.mjs jobs/buildings.mjs
SOFTGL=1 OUT=docs/phase2 PREFIX=buildings_phone MOBILE=1 W=390 H=844 QUALITY=low SHOWUI=1 VIEWS='view:overview;view:tower' node livetest.mjs jobs/buildings.mjs
python3 -I tools/buildings/compare_plates.py docs/phase2 docs/phase2
node tools/buildings/test_buildings3d.mjs        # geometry checks (no WebGL): all passed
```

| Render | View | What I checked / compared |
|---|---|---|
| `buildings_overview.png` | the core overview (south-east, 5.6 km) | No more "island". The extent sits in an urban plain of WorldCover colours, and rivers continue as land-cover water. The haze ramps in outside the extent, so there is no step at the extent edge; the finer Sentinel-2 detail inside still shows the extent softly (open issue 7). T2 west, T1 east, buildings at rule heights |
| `buildings_overview_far.png` | 11 km, pitch 18° | Far ground beyond the 20 km crop (mean colour) fades into a brownish haze that meets the drawn sky at the horizon without a band. Compare photos 22 / 23 (hazy plain around the airport) |
| `buildings_p02.png` + `buildings_compare_t1.png` | **photo match, photo 02** (camera on RWY 18L/36R abeam the tower, 4:3, vfov 55°) | The tower top lands within 1–5 px of the photo (render rows 381–385 vs photo 386 at 1280 × 960). The north end of the concourse lines up, and the central hall is about twice the concourse height in both. Differences: the real concourse and its white annex reach ≈ 6° (≈ 70 m) further south (open issue 3); the photo shows more context (grey office blocks, a dark-glass block and a radome building behind T1) that OSM / the rules do not give |
| `buildings_p02_tower.png` + `buildings_compare_tower.png` | photo match, zoomed on the tower (vfov 6°; photo enlarged about 4.6×) | Shaft width, slot, flare start, head width, window rows, cab and roof slab agree in proportion. The photo's head is slightly more angular and its cab a little smaller; the base is hidden behind the concourse in both |
| `buildings_t1.png` | T1 from the runway side (yaw 270, 620 m) | two-tier white concourse with the dark apron level, bridges at the OSM gate nodes, tower behind, hall and landside block above the concourse |
| `buildings_t1_close.png` | T1 north-west, close | concourse bands, VVIP annex (white), fritted-glass west face of the central hall (photo 02), louvre landside block |
| `buildings_tower.png`, `buildings_tower_far.png` | east tower, close (140 m) and from the apron (520 m) | the tower rises from its square yard behind the concourse; the head flare and cab read as in photo 02 |
| `buildings_t2.png` | T2 from the airside (1.25 km) | form as aerials 21 / 22 / 24: two finger piers east, central concourse N–S, linear arms, main hall behind with its overhanging roof, car parks P6 / P7, hotel |
| `buildings_t2_close.png` | T2 central concourse and north finger (360 m) | 21 m curtain wall vs 15 m pier, apron-level band, light-grey fascia, skylight spines, rooftop plant; compare photos 09 / 15 (grey-framed glass, light fascia) |
| `buildings_hangars.png` | China Eastern hangar from the apron (east) | 33.5 m box with door leaves and header on the east side (the computed door side), shallow barrel; the neighbouring service blocks are light metal-clad |
| `buildings_hangars_east.png` | big and small east hangars from the south | 4 vaults front-to-back over the 4 bays (aerial 21) and door walls on the south side (pavement share 0.88 / 0.95) |
| `buildings_fbo.png` | FBO from its apron | glazed pavilion (12 m rule) and its metal-clad neighbour |
| `buildings_hub.png` | the Hongqiao hub behind T2 | railway station hall and roof overhang, platform canopies on columns, bus terminal, T2 metro station; low detail as briefed |
| `buildings_sw.png` | south-west: China Eastern base | the two untyped towers (35 m rule) inside the fan-shaped office complexes, hangar, canal with bank kerbs |
| `buildings_night_overview.png`, `buildings_night_t2_close.png`, `buildings_night_t1_close.png` | 21:30 local | Lit window bands on T1 / T2 and on the context blocks, dark roofs and aprons. The far ground shows a faint warm, mottled glow on the built-up plain (4× factor), fading into the dark haze. It is much dimmer than real Shanghai at night (open issue 12) |
| `buildings_phone_view_overview.png` | 390 × 844, iPhone UA, touch, low tier, HUD on, app view "Overview" | The scene builds and renders on the low tier. The extent sits in the WorldCover plain, the HUD and the bottom sheet do not cover the airport core, and the credit line shows the WorldCover credit |
| `buildings_phone_view_tower.png` | the same, app view "Tower" (eye at the modelled cab) | Looks out through the cab glass towards T2 over the runways. The ceiling and the charcoal console band take ≈ 45 % of the portrait frame (open issue 13) |

## 7. Rules carried

- **No SFO geometry or data.** sfo3d's terminal parts, ITB hall, 221 ft tower and SFO Museum footprints are not used;
  only the generic wall / cap / plant / skylight helpers were forked (header). Audit:
  `grep -n "SFO\|sfo\|FT\b\|0.3048" js/world/buildings3d.js js/live/terminals.js` finds only provenance comments
  (the fork note and "as sfo3d" remarks).
- **No FAA marking, sign or lighting constant** in these files (none are needed).
- **Observed vs inferred.**
  - Every item carries `src: 'inf'`. Every part in the data has `h_src`, `h_note` and `geom_src`; every tower and
    hangar has `form_src` / `roof_src`.
  - The About panel gets a "Buildings and surroundings" section (observed outlines, inferred forms and heights).
  - `buildingsCredits()` is exported for the UI package.
- **Credits:** the credit line adds "ESA WorldCover 2021 (CC BY 4.0)", and the About panel carries the full
  WorldCover attribution. The comparison plates carry the photo credit (CC BY-SA 4.0).
- **Phone:** about 57,270 triangles instead of the core placeholders' ~12,000, and 405 KB of data scripts
  (`sha_buildings3d.js` 34 KB, `sha_landcover_far.js` 371 KB, after moving the colour map to JPEG; it was 711 KB as
  two PNGs). The ground program now uses 14 of the 16 texture units: 6 frame samplers, the core's 3, the markings'
  2 and these 3.

## 8. Open issues

1. **Heights are inf.**
   - The T2 piers and arms (15 m), the T1 core (15 m) and landside block (24 m), the FBO, the hub and every context
     block are rules.
   - The T2 main-hall and central-concourse values rest on one SAR wall and the DSM p90.
   - B3 notes that its layover heights are registration-sensitive (standards_refs.md §3.3).
2. **T1 identification.**
   - The T1 outline is an OSM estimation. The split into concourse tiers, core and landside block is a modelling
     choice.
   - The central hall is assumed to be osm:way/590426959. Photo 02 puts its glazed front at z ≈ 226–315 m, about
     40 m south of that outline (z 141–287), and shows a white block with a sloping roof south of it (z ≈ 312–354; part
     of osm:way/1443259951?), which is drawn as a 12 m block.
3. **T1 south end.** In the photo match (`buildings_compare_t1.png`) the north end and the tower line up, but the
   real airside concourse and its white annex reach about 6° (≈ 70 m) further south than the OSM T1 outline plus the
   VVIP way (z 426–478). The OSM outline is an estimation. The geometry is not moved, since nothing here may
   override OSM without a source; for the data package, a re-trace on the Umbra full-resolution windows.
4. **Tower form** comes from one 2023 photo at 0.36 m/px. The plan orientation, the cab plan (octagon assumed) and the
   base are unknown. The orange-and-white tower of photos 17 / 25 is not placed (location unknown), and the role of the
   two south-west towers is unknown.
5. **Roof forms.** The T2 roof is drawn flat with skylight spines. The aerials suggest a long roof with angled ends on
   the main hall; not modelled. The T1 hall's sloping south end is not modelled.
6. **Landside canopies** (the T2 "tree" canopies, photo 11; the T1 deep kerb canopy with struts, photos 01 / 03) are not
   drawn. Only the roof overhangs are.
7. **Far ground.** It ends at the 20 km crop (±10 km), with the crop's mean colour beyond and haze. The haze is a
   fixed rendering law, not driven by the METAR visibility. The core's clear-sky extinction (σ = 3.3e-5 /m, ~90 km
   visibility) makes no visible haze. ⚠ Whether the WorldCover crop may be shown beyond the extent at 50 m is the
   owner's call (PLAN R3 / Q3: "crops cut to that extent"). In the oblique overview, the canals and rivers inside the
   extent (the core's water, at full fraction) read near-black. The same rivers in the far land cover (50 m
   fractions, mostly below 1) read grey-blue, so a river changes tone where it crosses the extent edge.
8. **Horizon colour** (core). The sky pass draws a brownish band at and below the horizon (the renderer's sky base).
   The far haze takes that colour so the horizon is seamless; the result reads as smog (plausible for Shanghai, cf.
   photo 22) but its colour is the core sky model's.
9. **Core edits.** `js/shaders/ground.js` (the `sha_ground_far` hook; default output unchanged) and `live.html` (two
   script tags) are core files. The lead may want to fold these into the core commit.
10. **Context blocks.** OSM maps only some of the buildings in the extent (large residential areas are empty), so the
   urban fabric inside the extent comes from Sentinel-2 colour alone. The palette and facade kinds are inf.
11. **Gates package interface.**
    - `js/live/gates.js` `WALL_H` uses T1 9 m (matches the front tier here) and the 25 m rule for T2.
    - The modelled T2 airside walls are 15 m (piers, arms) and 21 m (central concourse). The VDGS facade-mount test
      could read the part heights from `window.SHA_BUILDINGS3D.parts` (id `t2_*`, field `h`).

12. **Night far glow.** Even at 4× the core factor, the built-up plain reads as a faint warm mottle. There are no
    point lights, road lights or sky glow beyond the extent; a brighter law, or a light-pollution sky term, is a
    rendering choice for the core.
13. **In-app Tower view on a portrait phone** (core view: pitch −5°, vfov 58°). The ceiling and the cab floor take
    about 45 % of the frame, and the ground near the tower is hidden below the console band. A tower view could
    lower the pitch (≈ −10°) or narrow the vertical field in portrait (`js/live/app.js`, core / UI package).
    Alternatively it could hide the cab's floor and roof boxes while the camera is in the cab: they are drawn in the
    tower item, and only the eye anchor is shared.

## 9. Interfaces for the other packages

- **Ground shader hook** `sha_ground_far` in `js/shaders/ground.js`:
  - `vec3 shaGroundFar(vec3 wp, float dist, vec3 neutral, inout float water, inout float glow)` is the albedo beyond
    the extent;
  - `vec3 shaGroundFarHaze(vec3 col, vec3 wp, float dist, vec3 V, float ext, float night)` runs after `applyFog`.

  The defaults reproduce the core. Only `js/live/terminals.js` redefines the hook (through `shaderChunks`).
  Uniforms: `uFarCol`, `uFarAttr`, `uFarSky` (3 samplers), `uFarRect`, `uHasFar`, `uHasFarSky`, `uFarMean`,
  `uFarHaze`. The ground program now uses 14 of the 16 texture units.
- **Data:**
  - `window.SHA_BUILDINGS3D`:
    - `parts[]`: `{id, of, name, style, h, h_src, h_note, polys, roof_polys?, axis, center, len, wid, area, src}`;
    - `towers[]`: `{id, of, form: 'control' | 'block', x, z, h, dims, yaw_deg, ...}`;
    - `hangars[]`: `{id, polys, h, roof, bays, door: {edge, normal, pavement_share}}`;
    - `claims[]`.
  - `window.SHA_LANDCOVER_FAR`: `{rect, res_m, w, h, png_col, png_attr, classes, attribution, licence}`.
  - Rebuild with `tools/buildings/build_buildings3d.py` and `tools/terrain/worldcover_far.py`; both are
    deterministic.
- **Claims:** every airport building, every context building and `'tower'`. The core draws no placeholders unless
  `?bld=0`.
- **Anchors:** `anchors.tower = {pos, eyeY, top}`. The eye is at the modelled cab, ground + 41.4 m; the top is the AIP
  obstacle height. From the eye the Tower view sees the cab ceiling and the console band (open issue 13).
- **Exports:** `buildingsCredits()` → `{attrib, about}` for `js/live/about.js` (the UI package may take them over;
  `start()` only appends when the texts are missing), and `terminalsInfo()`.
- **Gates:** the T1 / T2 airside facades are the OSM outlines; all 56 bridge attach points are on them (0.01 m). The
  T2 wall heights are in the parts (open issue 11).
- **QA:** `jobs/buildings.mjs` (named views, photo-match views with a 4:3 viewport), `tools/buildings/
  compare_plates.py`, `tools/buildings/test_buildings3d.mjs`.
