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

## Fix round 1 (2026-11-21)

Findings from `docs/phase2/review_visual.md` (H2, M3, M6 part, L2, L3, L5, L9) and the lead's extent-ring finding.
Files changed (this package only): `tools/buildings/build_buildings3d.py`, `data/sha_buildings3d.js/.json` (rebuilt),
`tools/terrain/worldcover_far.py`, `data/sha_landcover_far.js` (rebuilt), `js/live/terminals.js`, `js/world/buildings3d.js`,
`js/shaders/objects.js`, `js/live/app.js`, `jobs/buildings.mjs`, `tools/buildings/test_buildings3d.mjs`, this report.
Nothing was committed; `sfo3d/`, `pc12/` and `hwd3d/` were not touched. Every new value below is tagged in the code and
data: **inf** unless a source is named. Check renders are in `out/fix1/buildings/` (gitignored); the six evidence plates
are `docs/phase2/fix1_buildings_*.png` (our renders, deviceScaleFactor 1, SOFTGL llvmpipe). I looked at every render.

| Id | Status | What changed | Evidence |
|---|---|---|---|
| H2 | **fixed** | New data block `airside_fill` (`build_buildings3d.py` `airside_fill()`, `src: inf`, `kind: paved`), drawn by a new `pavement(api)` hook in `terminals.js` (the core hook, `js/live/ext.js`) as asphalt. Rule: every T1 / T2 / VVIP-annex facade segment (≤ 8 m) whose outward normal meets airside pavement (aprons, taxiway / runway surfaces) within 60 m gets a quad facade → pavement + 3 m, pier-tip corners get a disc; cut to the aerodrome polygon (never landside) and to outside every building; **minus the Sentinel-2 pixels that read as grass** (L < 0.115 and g > 0.02, or g > 0.12, clusters ≥ 3 px; thresholds from the medians of 12,516 apron and 11,589 airside-grass pixels of `data/sha_ground_s2.js`): 2,162 m² of real grass kept at the T1 south end and pier edges. Plus 24 m corridors along every fixed link, 14 m rotunda discs and 10 m contact-stand centreline strips nose → facade (VDGS posts). Total 99,931 m², 2 rings. Evidence string in the data: OSM apron ways stop 15-40 m short of the facades; paved in the S2 hint; dark asphalt service road in photo 09. Checked on S2 plates before rendering (`out/fix1/buildings/fill_t2.png`, `fill_t1.png`, `fill_233.png`). | `fix1_buildings_h2_stand_233.png` (stand 233: links, rotundas, VDGS on asphalt, the bridge hatching now on pavement), `fix1_buildings_h2_stand_102.png` (T1 north face); `out/fix1/buildings/h2a_bridge_230.png`, `h2a_t1_north_face.png`, `h2a_under233.png`. `FILLCHECK=1` (jobs/buildings.mjs, `SHA.world.pavedAt`): fixed-link points 392 / 392, VDGS posts 56 / 56, rotundas 53 / 56 paved; the 3 others (115, 121, 126, T1 west) have no fixed link: the rotunda sits on the facade line, so the 2 m pavedAt sample falls inside the outline; not visible. `test_buildings3d.mjs`: 0 / 539 fixed-link points off pavement |
| M3 | **fixed** | `objects.js` mat 1 night term: ~0.25 of the old level (mean 0.72 → ~0.17), warm tint (1.0, 0.74, 0.46), per-bay hash (6 % of bays near dark, 22 % at 0.35), mullions and spandrels dark with a distance-stable line coverage (`gridAA`: a plain `gridLine` tends to full coverage once a pixel spans a period and would have blacked out distant facades). Bridge tunnel strip 0.7 → 0.09 (0.4-0.5 of the new mean curtain-wall glow, as `gates.md` intends). Punched windows (mat 6) 0.9 → 0.4. | `fix1_buildings_night_t2pier.png` (T2 north pier at 21:30, before / after: no clipped white bands, warm panes, dark frames); `out/fix1/buildings/r2_night_stand_233.png` (fixed link at 233: warm panes, dark mullions) |
| M6 (part) | **fixed** (kerbs) | Bank kerbs get their own material (mat 17, `buildings3d.js` `BANK`, albedo 0.46): a dithered fade-out from 650 to 850 m (`objects.js`), so the 67 km of 0.35 m kerb no longer alias into dotted beige outlines from overview distances; still drawn near the camera. The water colour is the markings fixer's. | `fix1_buildings_overview_edge.png`: no dotted outlines along the canals (before: beige dots along every canal) |
| Extent ring (lead) | **fixed** | Two causes, two fixes. (1) The Sentinel-2 hint's alpha is binary at the extent polygon while the core's extent mask fades over ~±250 m, so 10 m detail stopped dead at half weight. `terminals.js` `featherS2()` builds a replacement for the ground program's `uS2` texture: inside the polygon the hint is cross-faded (linear reflectance) to the far land-cover colour over the inner 60-480 m (chamfer distance to the nodata edge); outside the polygon, within the hint's rectangle, it carries only the 50 m WorldCover colour (fading out over the rectangle's last 150 m, which removed a faint seam in the first try, `out/fix1/buildings/cmp_edge_r1r2.png`). No detail is added beyond the extent. (2) The far attribute map's B channel is now the **signed** distance to the edge (-1 km … +6 km, `worldcover_far.py`, `attr_b_range_m`), and the far haze ramps from 300 m inside the edge to 4 km outside (was: from the edge; `(1 - ext)` factor dropped). `?far=0` keeps the core's texture and ground. Cost: `buildWorld` 296 ms here (was 70-120 ms; the cross-fade loop over 457 × 703 px). | `fix1_buildings_overview_edge.png` (before: hard ring; after: the detail fades into the far ground); crops `out/fix1/buildings/cmp_edge_east.png` |
| L9 | **fixed** | The far-haze e-folding distance follows the environment's surface extinction: L = clamp(0.8 / σ, 1.2 km, 20 km), σ = `uFog.x` (from the METAR visibility via `js/env/state.js`). 20 km is the Shanghai haze floor [inf]: a dry CAVOK day (the 13/M05 snapshot, σ = 3.3e-5 /m) gets 20 km (was a fixed 14 km); 10 km visibility gets 2 km, 5 km 1.2 km. The 80 km mesh edge is forced to the sky colour (`max(a, smoothstep(45, 78 km))`) so the longer L leaves no step at the horizon. | `out/fix1/buildings/r2_overview_far.png` vs `buildings_overview_far.png` (mid-distance ground clearer, horizon band unchanged); `fix1_buildings_overview_edge.png` |
| L2 | **fixed** | T1 central hall: data `roof_form {kind 'arch', rise 7, exp 4, dir N-S, src inf}`; `buildings3d.js` `buildArchPart()`: walls to the eaves (h − 7 m), a 1.3 m roof slab following y(s) = 7 (1 − \|s\|⁴) across the 145 m N-S length (flat crest, ends sloping down, as photo 02), gables under it (fritted glass on the airside face, continuing the wall below; white elsewhere), white slab edge, grey metal top. The crest stays at the B3 height + slab (27.3 m, as the flat roof before), because B3's 26.4 m photo ratio was measured to the top of the hall front; `test_buildings3d.mjs` checks crest and eaves. | `fix1_buildings_t1_hall.png` (photo-match camera of photo 02, before / after); `out/fix1/buildings/cmp/buildings_compare_t1.png` (photo 02 above the new render, credit strip; not committed); `out/fix1/buildings/r1_tower.png` |
| L5 | **fixed** | Context blocks: wall colour from a Shanghai-like palette by id hash (grey concrete, beige / buff tile, brick, warm white tile, blue-grey; luminance 0.18-0.58) with ±8 % per-building variation; roofs 0.16-0.30 grey, always ≤ 0.8 × the wall luminance, with blue / grey steel on a share of industrial / commercial roofs (`contextColours()`, `CONTEXT_PALETTE`, src inf: aerials 21 / 24). Terminal / hangar roofs `roofMetal` / `roofLight` 0.52-0.58 → 0.45 grey; `clad` 0.74 → 0.64, `panelLight` 0.78 → 0.66, `officeLight` 0.74 → 0.60; roof-patch shader term made relative (a fixed 0.62 made white spots on darker roofs). | `fix1_buildings_overview_edge.png`, `out/fix1/buildings/r1_t1.png` vs `view_t1.png` (brick / beige / grey blocks instead of white), `out/fix1/buildings/cmp_t1_hall.png` |
| L3 | **fixed** | `app.js` Tower view: aims at the RWY 18L/36R midpoint from the runway data (yaw ≈ 285° instead of 262°), eye 0.5 m from the glass of the nearest cab face (`anchors.tower.cabYaw` added by `terminals.js`), pitch −11°; on a portrait screen the vertical field widens to keep ≥ ~40° horizontal (58-72°). The console band is no longer in view. The cab's own head terrace (2.65 m ring at the head top, photo 02 dims) still hides the ground within ~75 m of the tower: it is real geometry, now a grey roof membrane (`M.terrace` 0.26) instead of glaring white concrete; it takes the lower-right ~15 % of the laptop frame. | `fix1_buildings_towercab.png` (laptop before / after, phone after: T1 apron stands, taxiways, runway 18L/36R and its crossings in view; phone 393 × 659 with the UI) |

**Tests and console.** `node tools/buildings/test_buildings3d.mjs`: all checks passed, with new checks for the arch
(crest 27.30 m, eaves roof 20.30 m), the context palette (0 walls out of range, 0 roofs brighter than their walls) and the
airside fill (tagged inf / paved; 0 of 539 fixed-link points off pavement). `node tools/common/test_geo_js.mjs`: passed.
Both generators re-run twice: byte-identical outputs. Console in every check run (snapshot mode overview / T1 / tower /
cab, night, phone, photo match): 0 errors, 0 warnings, 0 page errors.

```
SOFTGL=1 OUT=out/fix1/buildings PREFIX=h2a T=snapshot VIEWS='park:229+230+231+233+234+102;stand:233,-,70,1,24;look:-860,2.5,-180,60,22,140@bridge_230;stand:102,-,110,1,20;look:600,2.5,-40,345,22,330@t1_north_face;look:-786,2.5,-118,160,35,70@under233' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=out/fix1/buildings PREFIX=r2 T=snapshot VIEWS='towercab;overview' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=out/fix1/buildings PREFIX=r2 DEVICE='iPhone 15' QUALITY=low SHOWUI=1 T=snapshot VIEWS='towercab@phone_towercab' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=out/fix1/buildings PREFIX=r3 T=2026-11-20T13:30:00Z VIEWS='park:229+230+231+233+234;t2pier@night_t2pier' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=out/fix1/buildings PREFIX=r3 FILLCHECK=1 VIEWS='p02;look:-1195,2.5,-398,100,35,120' node livetest.mjs jobs/buildings.mjs
```

**Open after this round.**
1. Roads, rail and canals (OSM, clipped at the extent polygon) still end at the edge, at half weight and fading with the
   core's extent mask; they are drawn by the core ground shader (handoff below).
2. The airside asphalt fill gets no night flood: the markings fixer's `shaApronFlood` keys on the apron channel (G = 255)
   and the fill is plain 'paved' (G = 0, like runway asphalt). Under the piers it lies in the buildings' shadow anyway.
3. North of the T2 north arm (z < −406) a ~33 m strip between the apron and the aerodrome boundary reads paved in S2 but
   stays unpaved: it is outside this fill (no terminal facade faces it).
4. The S2 override of `uS2` is a package-side workaround; a feathered alpha in the hint itself (core / data tool) would
   make it unnecessary.
5. The T1 hall's photo-02 offset (open issue 2, ~40 m south) and its white end wedges (the arch gables here are glass on the
   airside face) remain.
6. Tower view: the head terrace still covers the near field (~15 % laptop); hiding the head while the eye is in the cab is
   the alternative the review mentions, not done (it would show ground that the controllers cannot see).

**Handoffs (files this package does not own).**
- `js/shaders/ground.js` (core): fade OSM context features out before the extent polygon instead of stopping them at half
  weight: add `float extF = smoothstep(0.55, 0.95, ext);` after `ext` is computed, and use `extF` instead of `ext` in the
  ditch line (`alb *= 1.0 - 0.3 * … * ext;`), `sharp(ctx.g, 0.0, 1.0) * ext` (road), `sharp(ctx.b, 0.0, 1.0) * ext` (rail)
  and `float water = sharp(ctx.r, 0.0, 1.0) * ext;`.
- `js/shaders/ground.js` `shaApronFlood` (markings fixer): the airfield map cannot tell the fill from runway asphalt (both
  R 255, G 0; G 0.5-0.85 already reads as concrete). If the band should be flood-lit, `terminals.js` can supply a 1 m R8
  mask of the same rings as a ground uniform (`uAirsideFill`, through `groundUniforms`) and the flood chunk adds
  `0.6 * level * mask`; say so and the terminals side follows.
- `tools/terrain/s2_ground_hint.py` / `js/world/ground.js` (core): optionally write the hint's alpha as a 300-500 m
  feather inside the extent polygon; `terminals.js` `featherS2()` can then be dropped.

## Fix round 2 (2026-11-21)

Findings from `docs/phase2/review_visual_fix1.md`: **R1** (high, regression: edge stands on unpaved ground) and **N3**
(medium: aircraft and GSE unlit at night; owner "other", the object program is this package's). Files changed (this package
only): `tools/buildings/build_buildings3d.py`, `data/sha_buildings3d.js/.json` (rebuilt), `js/live/terminals.js`,
`js/shaders/objects.js`, `js/live/app.js`, `jobs/buildings.mjs`, `tools/buildings/test_buildings3d.mjs`, this report.
Nothing was committed; `sfo3d/`, `pc12/` and `hwd3d/` were not touched. Check renders: `out/fix1/buildings2/` (gitignored);
evidence plates `docs/phase2/fix1_buildings_r2_*.png` (our renders, deviceScaleFactor 1, SOFTGL llvmpipe). I looked at every
render listed below. The markings fixer worked on `js/shaders/ground.js` / `js/live/markings.js` at the same time (apron light
map); the night renders below include its state at the time.

| Id | Status | What changed | Evidence |
|---|---|---|---|
| R1 | **fixed** (pavement under nodes, nose tips, equipment areas, envelopes); masts and remote stand signs: **handoff** (gates) | New data block `stand_head_fill` (`build_buildings3d.py` `stand_head_fill()`, `src: inf`, `kind: apron`, evidence and rule strings in the data), drawn by the `pavement(api)` hook in `terminals.js` as `paved` (R, `pavedAt`) + `apron` (G 255: the same concrete and night flood as the apron it continues; the core map is additive, `apron` alone sets no R). Rule [inf]: per stand, the head rectangle in the decals' stand frame shifted by `class_ref.nose_gear_m` (nose-wheel stop, MH 5001-2021 6.2.16-7): u from −0.5 × length (contact stands; remote stands from the envelope back, −length − 3 m) to the envelope front (`stand.noseE` 3.75 m, table 4.13.5 note a) + 3 m, v = ±(span / 2 + B + 2 m), B = table 4.13.5 by code letter. `clearB`, `noseE` and `classLetter` are **read from `js/live/caac_markings.js`** (the ONE table; not duplicated). The part outside the pavement (aprons, taxiway / runway surfaces and shoulders, the H2 fill) is the stand's need (69 stands ≥ 5 m²); needs joined by a 6 m closing (one band per row, no teeth), cut to the aerodrome, outside buildings and OSM water, minus the Sentinel-2 grass pixels (the H2 test, clusters ≥ 3 px: 0 m² cut, the bands read neutral grey: e.g. 286-290 L 0.14-0.20 up to the aerodrome boundary, 401-413 L 0.13-0.18 in the first 10 m pixel past the apron edge, grass beyond, which the band does not reach), 2 m overlap with the apron, never over taxiway / runway pavement or the H2 asphalt band. Result: 21 rings, 28,181 m² (T2 apron 2 212-219 / 278-290, east apron 318-322 / 338-342, business apron 306 / 313, west remote 401-413, east remote 501-525, apron 6 601-608). Generator check (polygon test, in `checks`): stop nodes off pavement 14 → 0, class nose tips 32 → 0, envelope fronts 49 → 0. Page probe (`jobs/buildings.mjs HEADCHECK=1`, the review's `pavedAt` probe, snapshot, high tier) vs the review's `rv_probe.json`: stop nodes **18 → 0**, class nose tips **32 → 0**, equipment areas > 5 % unpaved **87 → 0** of 261 (≥ 25 %: 65 → 0), envelopes > 5 % **29 → 1** of 164 (101, T1 north face, 7 %: the rear of a contact stand, outside this rule), idle stair groups with a unit 20 → **26 / 26**; mast feet off pavement 33 → 30 of 73 (gates: placement, see handoffs). Checked on S2 plates before rendering (`fix1_buildings_r2_s2_plates.png`). | `fix1_buildings_r2_stand_404.png` (named view `stand:404,-,75,1,22`, before / after: the A320 at 404 and the B738 at 403 now have noses, stairs, buses and both equipment areas on concrete; the stand signs and the mast foot stand just past the band, on grass), `fix1_buildings_r2_edge290.png` (the review's two cameras at 286-290, before / after: equipment boxes and envelope fronts on concrete; masts and signs beyond the band), `fix1_buildings_r2_s2_plates.png`; `out/fix1/buildings2/r1_edge607.png` (apron 6: 607 / 608 and the corner piece south of 608 on concrete), `f2c_headcheck.json` |
| N3 | **partly**: GSE, jet bridges, stairs and buses lit; aircraft wired but need a two-line shader include (**handoff**); legend line (**handoff**) | `objects.js`: new self-contained chunk `sha_obj_flood` (`shaObjFlood(wp, N, alb, hAbove)`, `OBJ_FLOOD`, src inf): an object surface over the lit apron gets the ground's flood, `alb × APRON_FLOOD.tint × level × lit × k × (0.5 + 0.5 max(N.y, 0)) × uFloodNight`, faded out between 14 and 24 m above the ground (masts 30 m); `lit` = apron in the airfield map (R paved, G 255) sampled 4 m in front of the surface (4 m mip footprint), and — when the markings package's apron light map is in the ground uniforms (`uApLight`, R = lit area incl. the airside fill + spill, G = mast pools) — `lit = max(apron, R)`, `k = gScale × G`, exactly as the ground; else k = 1. Level / tint / gScale come from `ground.js APRON_FLOOD` by namespace import (fallback copy if the export changes). OBJ_FS calls it after the emissive terms. `app.js`: `R.extraCommon.uFloodNight` (= the night factor; the bridges' `objG` program dims `uNight`, not this) and `floodUniforms(fr.items)` after `scene.frame`: every item of the object programs (`obj`, `objI`, `objG`) and of the aircraft programs (`aircraft`, `acr`, inert until their shaders include the chunk) gets `uAptMap / uAptRect / uObjLight / uObjLightRect / uObjLightOn / uObjFlood` per draw (samplers are rebound per draw in `gl.js`; with no light map the airfield map is bound in its place, so no sampler is ever unbound). The wrapper inherits the item's uniforms (`Object.create`: the aircraft items keep prototype-chained per-frame uniforms) and is re-made when an item's uniforms are replaced. Items may opt out (`noFlood: true`): the terminals' building items do (`terminals.js item()` and the tower): with the light map's spill under the piers, the 15 m T2 pier roofs glowed (`out/fix1/buildings2/n4_night_t2pier.png`, rejected). Day renders are byte-identical before / after the wiring (`r1_stand_404` vs `r2_stand_404`: 0 differing pixels). | `fix1_buildings_r2_night_t2pier.png` (named view `t2pier` at 21:30 UTC+8, before / after: belt loaders, tugs, carts, bridge tunnels, cabs and drive units lit like the apron under them; the pier roof stays dark; the aircraft stay navy silhouettes), `fix1_buildings_r2_night_stand_233.png` (before / after: fuel truck, catering, baggage train, belt loader and the 233 / 232 bridges lit; B738 unlit); `out/fix1/buildings2/n5_night_stand_404.png` (remote stand: stairs and buses lit on the lit apron fill) |

**Tests and console.** `node tools/buildings/test_buildings3d.mjs`: all checks passed, with a new check that the stand-head
fill exists (tagged inf / apron) and that every stop node, class nose tip and envelope front lies on pavement (0 / 0 / 0 of
164). `node tools/common/test_geo_js.mjs`: passed. The generator run twice: byte-identical outputs (note: `caac_markings.js`
is now an input, so an edit there changes `inputs_sha256_16`). `jobs/buildings.mjs` now prints a console tally (errors /
warnings / page errors, driver noise excluded as in `livetest.mjs`): snapshot run with HEADCHECK + FILLCHECK + overview
0 / 0 / 0; night run (21:30) 0 / 0 / 0; the `jobs/views.mjs` day and night runs above logged no console warnings, errors or
page errors. FILLCHECK unchanged: fixed-link points 392 / 392, VDGS posts 52 / 52 paved, rotundas 53 / 56 (115, 121, 126:
rotunda on the facade line, as in round 1).

```
python3 -I tools/buildings/build_buildings3d.py && node tools/buildings/test_buildings3d.mjs
SOFTGL=1 OUT=out/fix1/buildings2 PREFIX=f2c HEADCHECK=1 FILLCHECK=1 VIEWS='overview' T=snapshot node livetest.mjs jobs/buildings.mjs
SOFTGL=1 OUT=out/fix1/buildings2 PREFIX=r1 T=snapshot VIEWS='park:403+404+288+290+607+608;stand:404,-,75,1,22@stand_404;look:-723,2.5,1050,60,30,140@edge290;look:-726,2.5,1050,268,86,140,50@edge290_top;look:-735,2.5,1590,300,40,120@edge607' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=out/fix1/buildings2 PREFIX=n5 T=2026-11-20T13:30:00Z VIEWS='park:229+230+231+233+234+403+404;t2pier@night_t2pier;stand:233,-,70,1,24@night_stand_233;stand:404,-,75,1,22@night_stand_404' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=out/fix1/buildings2 PREFIX=f2n VIEWS='t2_close' T=2026-11-20T13:30:00Z node livetest.mjs jobs/buildings.mjs
```

**Open after this round.**
1. Masts (30 of 73 feet off pavement, all 7 west-remote ones) and the remote stand-number signs stand just past the new
   band: `remoteSpot` puts the post 10 m ahead of `frontOf` (≈ node + 15 m for class C) and the band ends at node +
   nose_gear_m + 3.75 + 3 m (≈ 11.8 m). Placement is the gates package's (handoff); the band is not widened for them because
   the S2 hint turns to grass 10-15 m past the apron edge at 401-413.
2. Envelope of 101 (T1 north face, EL) 7 % unpaved at its rear (contact stands use the front half of the head rectangle).
3. Aircraft stay unlit at night until the aircraft shaders include `sha_obj_flood` (handoff; `app.js` already passes the
   uniforms). Vertical faces over the dark asphalt band (N6, plain asphalt albedo) are lit by the light map although the
   ground there stays darker (albedo, not light).
4. The stand-head band is plain apron concrete; the photo-09-style service-road lines (N6, low) are not drawn.

**Handoffs (files this package does not own).**
- **Aircraft programs** (`js/shaders/aircraft_real.js` ACR_FS, `js/shaders/aircraft.js` AC_FS; core / aircraft): add
  `import './objects.js';` at the top of each module (defines the chunk); in each FS add `#include <sha_obj_flood>` after
  `#include <fout>` and `uniform float uGroundY;` (already in `R.extraCommon`); after `vec3 col = shadePBR(albedo, N, V,
  rough, metal, sh, ao, 1.0);` (aircraft_real.js line ~139, aircraft.js line ~184) add
  `col += shaObjFlood(wp, N, albedo, wp.y - uGroundY) * ao;`. Nothing else: `app.js floodUniforms` already binds the
  uniforms for `aircraft` / `acr` items. Then the legend clause below can be dropped.
- **Legend** (`js/live/shell.js`, lighting line, relay_ui): until the aircraft include lands, append "; aircraft are not lit
  at night yet (vehicles and jet bridges are)".
- **Gates** (`js/live/gate_system.js`): `placeMasts`: require `pavedAt(x, z) >= 0.5` at the mast foot for remote stands too
  and drop the 12 m remote tolerance (the stand-head fill now paves the stand heads); `remoteSpot`: add
  `&& pavedAt(p[0], p[2]) >= 0.5` to `okAt` and try the lateral candidates before `t >= 10` when the centreline candidates
  are unpaved (the band ends ≈ nose_gear_m + 6.75 m ahead of the node; `lat` 8-10 m at `t` 3-6 is on the band and clear of
  the class footprint).
- **Markings** (`js/live/caac_decals.js`, optional safety net): multiply decal alpha by `paved` (the probe now finds 0
  equipment areas and 1 envelope (101, 7 %) over unpaved ground).
- **Lead / CLAUDE.md** ("Conventions"): add "the **stand-head fill** (`sha_buildings3d.json` `stand_head_fill`, src inf: OSM
  apron gap ahead of the edge stands, S2-tested) draws as apron; chunk `sha_obj_flood` (`js/shaders/objects.js`) lights
  objects over the lit apron at night, `app.js floodUniforms` binds it per draw (`noFlood: true` opts an item out)", and
  under package jobs "`jobs/buildings.mjs HEADCHECK=1` (the review's pavement probe: stop nodes, nose tips, equipment areas,
  envelopes, mast feet) and a console tally".

## Fix round 3 (2026-11-27)

Findings from `docs/phase2/review_visual_fix2.md`: **V3** (low: terminal / pier roofs pure black at night), **V5** (low: the
surroundings black at night), **L9** (low, open since round 1: the CAVOK overview reads as 5-6 km visibility), and the optional
**N6** (the pier-tip fill reads as a round dark disc) and **L3** (the cab terrace covers ~20 % of the laptop tower view). Files
changed (this package only): `js/shaders/objects.js`, `js/live/app.js`, `js/live/terminals.js`,
`tools/buildings/build_buildings3d.py`, `data/sha_buildings3d.js/.json` (rebuilt), `tools/buildings/test_buildings3d.mjs`,
`jobs/buildings.mjs`, new `tools/buildings/band_contrast.py`, this report. Nothing was committed; `sfo3d/`, `pc12/` and `hwd3d/`
were not touched. Check renders: `out/fix3/buildings/` (gitignored; SOFTGL llvmpipe, 1280 × 720, deviceScaleFactor 1, high
tier). Evidence plates (our renders, labelled with the measured values): `fix3_buildings_v3_night_t2pier.png`,
`fix3_buildings_v5_night_overview.png`, `fix3_buildings_l9_overview.png`, `fix3_buildings_n6_l3_day.png`. Before / after pairs
were rendered **in one page** (`out/fix3/buildings/fix3.mjs`, the same switch as `jobs/buildings.mjs FIX3=off`): "before"
switches this round's shader terms off through the page, so the other packages' concurrent changes (masts, light map) are the
same in both images. I looked at every render named below. Night instant: 2026-11-20T13:30Z (21:30 UTC+8, the named night
views; that instant's weather has 8 km visibility, sigma 5.1e-4 /m). Day: `T=snapshot` (CAVOK, sigma 3.3e-5 /m).

| Id | Status | What changed | Evidence |
|---|---|---|---|
| V3 | **fixed** | `objects.js` `sha_obj_flood`: an item that opts out of the flood (`noFlood`) gets a night ambient instead, `alb × APRON_FLOOD.tint × APRON_FLOOD.level × mix(vert, up, max(N.y, 0)) × uFloodNight`, with `(up, vert)` = `uObjNightAmb` per item (`OBJ_NIGHT`, src inf): terminal / pier / hangar / hub / tower items `[0.12, 0.04]` (0.12 of the apron flood level × albedo on roofs, 0.04 on walls). `app.js floodUniforms` passes `item.nightAmb` (every other item gets `[0, 0]`, so the program uniform never carries over); `terminals.js` sets it on its items (bank kerbs: none). Below the facade glow (curtain wall 0.10-0.32 × uNight) and the apron flood. | `fix3_buildings_v3_night_t2pier.png` (view `t2pier`, 21:30, same page): T2 north pier roof median **(4, 4, 5) → (37, 32, 27)** sRGB next to an apron of (104, 91, 71); the main-hall and concourse roofs read as dark grey shapes, the curtain walls stay the brightest building surfaces. `out/fix3/buildings/n1_night_t2pier_b/_a.png` (V3 alone, before N6). |
| V5 | **fixed** (far ground, context blocks, terminal / hub roofs); **handoff** for the landside ground and roads inside the extent (core `ground.js`) and the legend wording (`shell.js`) | Far ground (`terminals.js` `sha_ground_far`): the built-up glow level is a uniform, `uFarNight` = (16, ramp 0-2000 m, edge 0.12) (was a fixed 4: radiance ~0.005, black from the overview). It ramps from 0.12 × level at the extent edge to full 2 km outside it, so the landside inside the extent (core ground, ~0.1 × albedo urban glow) does not end in a ring; the ramp is dropped automatically when the core exports `URBAN_NIGHT` (handoff below). Night airlight `uFarNightAir` (0.020, 0.015, 0.010): the far haze colour at night is at least this warm radiance (city light scattered by the haze), faded out towards the 80 km mesh edge; without it the haze (and the core fog: 8 km visibility at the night instant) took the lit plain to black within a few km. Context LOD blocks: `nightAmb` `OBJ_NIGHT.context` [0.20, 0.14] (dim warm emissive on roofs and walls, on top of their lit windows). All src inf. | `fix3_buildings_v5_night_overview.png`: night overview, far ground median by row **0-4 → 7-29** sRGB (y 60: 29, y 300: 22, y 600: 13), apron p90 (75, 65, 49) unchanged, landside inside the extent (1, 1, 0) (core); with the core hand-off applied in a scratch copy (`hoff3`): landside median (27, 21, 11), roads p90 ~47, no ring at the extent edge; hub view (T2 landside): roofs and blocks read, the ground is the core's. Clear-night check (CAVOK sigma forced in the page, airlight 0.010 at the time, `hzn2_clear1`): far city 19-42 sRGB median by row, so it stays below the apron without the haze too. |
| L9 | **fixed** (the far haze was the dominant term; now a boundary-layer haze); ground-level haze unchanged | **Diagnosis** (overview camera 3,052 m above the ground; page probe `out/fix3/buildings/haze_probe.mjs`, each term switched off through the uniforms): at the review's bands y = 60 / 120 / 180 / 240 / 300 (slant 15.0 / 11.2 / 9.0 / 7.5 / 6.4 km) the far-ground haze (`shaGroundFarHaze`) was a = 0.46 / 0.35 / 0.28 / 0.22 / 0.18, the core aerial perspective (`applyFog`, sigma 3.3e-5 with its 914 m scale height) only 1 − T = 0.13 / 0.10 / 0.08 / 0.07 / 0.06. Renders: switching the far haze off lowers the y = 120 band mean from 120 to 86 and lifts its detail contrast from 0.025 to 0.076; switching the core fog off changes little (120 → 116, 0.025 → 0.030); both off: 76, 0.105. The far haze's law used the 3-D camera distance as if the whole slant path from 3 km ran through ground-level air (ground-level e-folding 20 km, the Shanghai haze floor; with the core's clear-air sigma that is ~47 km visibility at the ground, computed). **Change** (`terminals.js`): the hazed part of the path (beyond 2.5 km) is weighted by exp(−h / H) along the ray: factor H / h1 × (1 − exp(−h1 / H)), h1 = the ray's height where the hazed part starts, H = the core's surface-slab depth (`1 / uFog.y`: 914 m on this CAVOK day, the cloud base under a low deck) clamped to 0.3-2 km (`FAR_HAZE_H`, inf). New a = 0.19 / 0.14 / 0.12 / 0.10 / 0.08. A camera near the ground keeps the old law (factor > 0.95 below ~90 m): `towercab` before / after **0 pixels** differ by more than 2 levels. The mesh-edge sky ramp now starts at 25 km (was 45 km): with the weaker haze a 45 km start left a 6 px step at the horizon of `overview_far` (`d1_overview_far_a.png`, rows 174-186: 152 → 142 → 134); now a soft 20 px haze-layer top (`d2_overview_far_a.png`). | `fix3_buildings_l9_overview.png`; `python3 -I tools/buildings/band_contrast.py` on `d1_overview_b.png` / `d2_overview_a.png` (same page): **review std** y 60-300: 3.8 / 5.6 / 12.7 / 17.5 / 22.6 → 3.4 / 6.9 / 9.1 / 17.3 / 22.7; **detail contrast** (high-pass std / mean, see below): 0.008 / 0.025 / 0.048 / 0.135 / 0.132 → **0.018 / 0.047 / 0.063 / 0.146 / 0.137**; band mean 129 / 120 / 105 → 107 / 102 / 95. The review's std at y = 180 *drops* although the ground there is clearer: that band crosses the extent edge, where the old haze ramp (with the distance outside the extent) made a bright-dark-bright profile; with no haze at all the band's std is 10.5, lower than the hazed 12.7 (`hz0_none.png`). The ceiling with the far haze off is 0.032 / 0.076 / 0.080 (`hz0_nofar.png`). What still reads as haze at the top of the frame: the remaining boundary-layer haze (a 0.14-0.19), the core fog (0.10-0.13) and, above y ≈ 64, ground beyond the 20 km land-cover crop (one mean colour, no detail). |
| N6 | **fixed** (optional) | The "disc" is the OSM apron's rounded inner ring around the pier tip (obs), 30-40 m deep, filled by the airside fill as asphalt. `build_buildings3d.py airside_fill()`: only a `FILL_SERVICE_W` 12 m band along the facades (the terminal outline buffered with mitre joins: square corners) stays asphalt (`polys`, kind paved: the service road of photo 09); the rest of the gap is `apron_polys` (`apron_kind` apron), drawn by `terminals.js` as paved + apron (the apron concrete and its night flood). Corner wedges of the fill are now mitre parallelograms instead of discs. All inf; evidence / rule strings in the data updated. 36,215 m² service band + 63,638 m² apron part (was 99,931 m² asphalt). | `fix3_buildings_n6_l3_day.png` (day `t2pier`, the old data in a scratch copy vs the new, same code): the round dark cap at the tip is gone, a narrow dark band follows the pier. Night: pier-tip median (70, 60, 49) → (151, 135, 109) (`fix3_buildings_v3_night_t2pier.png`); under the 233 bridges (32, 28, 22) in the review's named view, (70, 61, 51) with this round's light map still on asphalt (`n1_night_stand_233_a.png`), (157, 141, 116) on concrete (`f3n_night_stand_233_a.png`, apron there (89, 77, 60)): the markings light map holds the fill under contact bridges at `standFillLevel` 1.25 × the stand mean, set against asphalt; on concrete that band is now the brightest ground, as photos 13 / 19 show, but ~1.7 × the apron (see handoffs). FILLCHECK unchanged: fixed-link points 392 / 392, VDGS posts 52 / 52, rotundas 53 / 56 (115, 121, 126, as before). |
| L3 | **fixed** on the laptop (optional); phone unchanged by design | `terminals.js` adds `anchors.tower.terraceHalf / terraceY` (head_w / 2, head_y1). `app.js` Tower view, landscape: vertical field 46° (was 58°; horizontal ~74° on 16:9, was 88°) and the pitch that puts the frame's lower edge 1° below the terrace edge seen from the eye (clamped −11° … −4°; here −8.2°). Portrait keeps −11° and 58-72°: tried first, the higher pitch put the horizon mid-screen and the apron under the bottom sheet, which already hides the terrace (`out/fix3/buildings/cmp_l3_phone.png`); the final phone render differs from the round-2 named view in 3 % of pixels (masts / labels). | `fix3_buildings_n6_l3_day.png`; `band_contrast.py --terrace`: terrace share of the laptop frame **20.5 % → 5.5 %** (column median 20.6 % → 3.3 %; the right-hand columns, where the cab face comes closer, 14 % at p90). |

**Tests and console.** `node tools/buildings/test_buildings3d.mjs`: all checks passed (the fixed-link and stand-head checks now
also accept the fill's apron part; a new check that the apron part is tagged apron). `node tools/common/test_geo_js.mjs`: passed.
The generator re-run twice: byte-identical (`sha_buildings3d.json` md5 e17fa564…, `.js` 6e59eca9…). Note: the generator reads
`js/live/caac_markings.js`, which the markings fixer changed this round (`inputs_sha256_16` changed; `stand_head_fill` came out
identical); the integrator re-runs the build after all fixers. `jobs/buildings.mjs` snapshot run with `HEADCHECK=1 FILLCHECK=1`
(views overview, t2pier): stop nodes 0, nose tips 0, equipment areas > 5 % 0 / 261, envelopes 1 / 164 (101, as before), mast feet
0 / 58, idle stairs 26 / 26; console **0 errors · 0 warnings · 0 page errors**. Every other run of this round (day and night, the
phone tower view, the `FIX3=off` run, the scratch-copy hand-off runs) logged 0 / 0 / 0. `FIX3=off` reproduces the "before"
overview (0.08 % of pixels differ by more than 2 levels, the masts placed by the concurrently changing gates package).

```
python3 -I tools/buildings/build_buildings3d.py && node tools/buildings/test_buildings3d.mjs && node tools/common/test_geo_js.mjs
SOFTGL=1 OUT=out/fix3/buildings PREFIX=f3c HEADCHECK=1 FILLCHECK=1 T=snapshot VIEWS='overview;t2pier' node livetest.mjs jobs/buildings.mjs
SOFTGL=1 OUT=out/fix3/buildings PREFIX=f3off FIX3=off T=snapshot VIEWS='overview' node livetest.mjs jobs/buildings.mjs   # "before" (shader terms)
SOFTGL=1 OUT=out/fix3/buildings PREFIX=f3n T=2026-11-20T13:30:00Z VIEWS='park:229+230+231+233+234;t2pier@night_t2pier;stand:233,-,70,1,24@night_stand_233;overview@night_overview' node livetest.mjs out/fix3/buildings/fix3.mjs
SOFTGL=1 OUT=out/fix3/buildings PREFIX=d1 T=snapshot VIEWS='overview;look:-300,2.5,150,150,18,11000,55@overview_far;towercab' node livetest.mjs out/fix3/buildings/fix3.mjs
SOFTGL=1 OUT=out/fix3/buildings PREFIX=l3b DEVICE='iPhone 15' QUALITY=low SHOWUI=1 T=snapshot VIEWS='towercab@phone_towercab' node livetest.mjs jobs/views.mjs
python3 -I tools/buildings/band_contrast.py out/fix3/buildings/d1_overview_b.png out/fix3/buildings/d2_overview_a.png
python3 -I tools/buildings/band_contrast.py --terrace docs/phase2/view_towercab.png out/fix3/buildings/l3_towercab_a.png
```

**Open after this round.**
1. Inside the extent the landside ground and roads stay black at night until the core hand-off below lands (the far ground's
   2 km ramp keeps the edge from reading as a ring meanwhile; the airport then sits in a dark disc ~2 km wide in the night
   overview).
2. At the named night instant (8 km visibility) the core fog's in-scatter is the night sky (no city light), so the far ground
   within ~2.5 km of the camera, where this package's airlight does not act, is darkened by the core fog (T 0.48 at 5 km).
   Optional core change: an urban night floor in `applyFog`'s in-scatter (`js/shaders/common.js`).
3. The top of the CAVOK overview (above y ≈ 64) is ground beyond the 20 km WorldCover crop: one mean colour, so it still reads
   as haze; a larger crop needs a new download (refs/cache) and the owner's extent decision (§8).
4. The light map's `standFillLevel` (markings) was tuned for an asphalt band under the bridges; with N6 most of that band is
   concrete and ~1.7 × the surrounding apron at night (handoff 3).
5. L2 (T1 hall profile) and N7 (canal tone) are not in this round.

**Handoffs (files this package does not own).**
1. **Legend** (`js/live/shell.js` `legendLines`, relay_ui), the `buildings` line when the terminals extension is present, append:
   `' At night, the dim glow on the roofs, the city blocks and the built-up land beyond the detailed area is <span class="srcchip inf">inf</span>.'`
   so the line reads: "**Buildings:** outlines from OpenStreetMap [obs]; heights, forms, facades, the tower form [inf]. At night,
   the dim glow on the roofs, the city blocks and the built-up land beyond the detailed area is [inf]."
2. **Core ground** (`js/shaders/ground.js`, core / integration), the landside of the extent at the far ground's level (tested in
   a scratch copy, `out/fix3/buildings/hoff3_night_overview_a.png` / `hoff3_night_hub_a.png`: landside median (27, 21, 11),
   roads p90 ~47 against an apron p90 of 77, no ring at the extent edge, console 0 / 0 / 0). (a) Above `export const APRON_FLOOD`
   add
   `export const URBAN_NIGHT = { k: 0.8, road: 0.3, tint: [1.0, 0.75, 0.5], src: 'inf: rendering levels (lit city at night), review_visual_fix2.md V5' };`
   (b) in `GROUND_FS`, replace
   `col += alb * vec3(1.0, 0.75, 0.5) * urbanN * (0.3 + 0.7 * nzB.g * nzC.b) * 0.10 * uNight;` with
   `col += alb * vec3(1.0, 0.75, 0.5) * urbanN * (0.3 + 0.7 * nzB.g * nzC.b) * ${URBAN_NIGHT.k.toFixed(3)} * uNight;   // V5: was 0.10`
   `col += alb * vec3(1.0, 0.75, 0.5) * road * ext * (1.0 - aero) * ${URBAN_NIGHT.road.toFixed(3)} * uNight;   // V5: landside street lighting`
   No change is needed here afterwards: `terminals.js` reads `URBAN_NIGHT` by namespace import and then drops the far ground's
   edge ramp (`uFarNight.w` = 1). `python3 -I out/fix3/buildings/handoff_ground.py js/shaders/ground.js` (local, gitignored)
   applies exactly these two edits and nothing else.
3. **Markings** (`js/live/caac_markings.js` `CAAC.apronFlood.standFillLevel`, optional): since N6 the fill under the contact
   bridges beyond 12 m from the facade is apron concrete (albedo ~0.30, was asphalt ~0.085). At 1.25 × the stand mean it renders
   (151-157, 135-141, 109-116) sRGB at the T2 north pier tip against (89, 77, 60) / (104, 91, 71) on the apron beside it: the
   brightest ground, as photos 13 / 19 show, but by ~1.7 ×. If that is too strong, ~1.0 for apron-kind texels (or 1.25 only for
   the asphalt service band, `SHA_BUILDINGS3D.airside_fill.polys`) keeps the band at the stand level.
4. **Lead / CLAUDE.md** ("Conventions"): "the far haze is a boundary-layer haze (`terminals.js` `FAR_HAZE_H`: the hazed path is
   weighted by exp(−h / H), H = the core's surface-slab depth, 0.3-2 km; ground-level views unchanged); `noFlood` items get a night
   ambient (`objects.js` `OBJ_NIGHT`, `item.nightAmb`); the far ground's night glow / airlight are `uFarNight` / `uFarNightAir`;
   the airside fill is a 12 m asphalt service band (`airside_fill.polys`) plus apron concrete (`apron_polys`); the laptop Tower
   view frames to 1° below the cab terrace (`anchors.tower.terraceHalf / terraceY`, vertical field 46°)"; under package jobs:
   "`jobs/buildings.mjs FIX3=off` (round-3 shader terms off) and `tools/buildings/band_contrast.py` (band / detail contrast,
   `--terrace`)".
