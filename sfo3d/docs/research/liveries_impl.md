# Brand liveries: implementation, verification and status (24 Sep 2026; cabin windows 25 Sep 2026, §8; photo checks and
# window verification 25 Sep 2026, §3.5, §5, §8.6)

Implements the owner's decisions on `docs/research/liveries.md` §7: real airline liveries, re-drawn as vector art for a
non-commercial depiction (About notice: trademarks belong to their owners); FlightGear GPL textures only where the
livery is current and the UV layout fits; everything else baked by our own painter. Colours come from official brand
documents where we could fetch them, otherwise measured on official press images (URL recorded), otherwise marked
`approx`. Every design records its references (`tools/liveries/liveries.py`, copied into
`data/liveries/manifest.json` `brands.<CODE>` and `data/brands.js` `BRAND_INFO`).

Pipeline (all offline, Python + numpy; no reference image or font file is committed):

```bash
FAM_DIR=refs/cache/src/fam3d python3 tools/convert_models.py [keys]   # only when a model changes (keeps UVs sane, see §3.4)
python3 tools/liveries/windows_ref.py [types] [--plot DIR]            # cabin-window rows off the manufacturers' drawings (§8)
python3 tools/liveries/windows.py [keys]                             # artist rows vs references, keep / paint per model (§8)
python3 tools/liveries/atlas.py [keys]                               # livery atlas per model -> data/models/*.sfom
python3 tools/liveries/build.py [BRANDS] [--models k,..]             # bake -> data/liveries/**, manifest.json/.js
python3 tools/liveries/build_brands_js.py                            # registration -> brand table -> data/brands.js
python3 tools/liveries/render_blender.py [BRANDS]                    # render check -> out/liveries/<CODE>.png
python3 tools/liveries/build.py --list-snapshot                      # lo files the recorded snapshot needs
python3 tools/liveries/ref_photos.py [BRANDS]                        # reference photos (Wikimedia Commons) -> refs/cache/livref (not committed)
python3 tools/liveries/compare.py BRAND.. [--mini out.png]           # photo vs software render of our bake -> out/liveries/compare/
python3 tools/liveries/window_sheet.py [--models k,..]               # window rows vs manufacturer stations, every type -> out/liveries/windows/
python3 tools/liveries/doc_tables.py --brands|--windows|--atlas      # the tables of this document, from the data
```

## 1. Which brand an aircraft wears (`data/brands.js`, `js/live/lookup.js`)

The livery follows the airframe, not the callsign: a SkyWest (`SKW`) E175 may be United Express, Alaska, Delta
Connection or American Eagle. `brandFor({airline, reg, hex, icaoType})` resolves, in order:

1. **Per-registration override** (`REG_OVERRIDE`, observed in the cited source): N645SY United Express "Mountain
   Ascent" (source: worldairlinenews.com, 4 Sep 2026; third-party), N735AT American centennial "Flagship" retro
   (news.aa.com). Both are rendered in the brand's standard livery for now (the entry says so: `rendered`).
2. **Registration → brand, observed** (`REG_BRAND`, 586 tails): US DOT BTS Marketing Carrier On-Time Performance,
   months 2026-05..07 (public domain), marketing network of each tail flown by the regional operators with SFO
   flights (SkyWest OO: United 253, Delta 142, American 99, Alaska 43; Horizon QX: Alaska 49). `brandSrc = 'obs'`.
3. **Registration series, inferred** (`REG_SERIES`, 14 rules with at least 5 tails each, E-Jets / CRJ200), then
   **operator majority, inferred** (`OP_MAJORITY`: SkyWest at SFO = United Express for every type, from the SFO landings
   by published airline; Horizon = Alaska). `brandSrc = 'inf'`.
4. **Callsign airline** (`CALLSIGN_BRAND`, mainline flights: `UAL` → United, `JZA` → Air Canada Express,
   `TAI`/`LRC` → Avianca, `QXE` → Alaska via rule 3, ...). `brandSrc = 'obs'`.
5. **Unknown operator**: no brand → the generic `NEUTRAL` scheme (white body, light grey tail, no titles) on the
   neutral atlas (the model's own skin detail, all brand paint removed).

The registration comes from the feed when present, else from the ICAO 24-bit address: US addresses decode to the
N-number with the FAA algorithm (`nNumberFromHex`). Verified against tar1090-db (commit d9459d7): 392,062 of 392,213 US
entries decode to the database's registration; the 151 mismatches are database entries whose registration and address
disagree. In the recorded snapshot, 46 of 46 N-registered aircraft decode to the feed's
registration.

Snapshot check (`data/snapshot.js`, 48 aircraft; node, the app's own modules): every airline resolves; the five SkyWest
E175s of `docs/research/liveries.md` §1.2 get their observed brands (N510SY American Eagle, N171SY and N408SY Alaska,
N125SY and N148SY United Express; all `obs`); one aircraft of an unknown operator gets `NEUTRAL`; the 777s (6 United,
1 Air Canada, 1 Delta, 1 Cathay) now wear their brand bakes on the 777 artist models (§9.4).

## 2. The livery atlas (`tools/liveries/atlas.py`)

The source models' UV layouts are unusable for painting (overlapping, mirrored, tiled; the 747 fuselage at
1024 × 256 px for 70 m). Each model therefore gets a second, uniform layout, the **livery atlas**, as texture 0:

- **Parts** (per triangle): fuselage (inside the measured section envelope incl. nose, tail cone, wing-root fillets; every body-zone triangle in the first 10 % of the length),
  fin (+ dorsal), tailplane, engine nacelle skins (outermost surface per station and angle; inlet cowls modelled in
  the body zone are captured; E175 / MD-11 nacelles merged into the wing mesh are found as connected components at
  the type's engine stations; the radome, APU exhaust cones and long strips are rejected), pylons, wing tips / winglets,
  gear doors. Wings, glass, lights, gear and interior keep their source textures.
- **Charts**: box projection by dominant normal (fuselage sides up to 55°), occlusion layer peeling, long charts
  split, shelf-packed at one texel density per model (`kpm`, px per m at 2048 px), 6 px padding.
- **Detail layer**: the source texture's panel lines, door outlines and window frames (black top-hat, lines at least
  0.8 m long, masked where the source livery differed from its neutralised version so no ghost titles survive) are
  kept as a multiply layer; small dark areas (≤ 1.5 m²: walkway marks, vents) are kept as they are.
- **Alpha**: 1 paint, 0.75 unchanged dark skin, **< 0.5 cabin-window glass** (0.1; not 0, so no WebP encoder or viewer
  drops the glass colour).
- **Cabin windows** (§8): exactly one row per deck. 11 models get their artist windows removed (glass objects deleted,
  openings in the skin closed with a fan of skin triangles that has its own vertices and the skin's outward normal,
  painted source windows and window frames dropped from the kept skin detail in the window band) and the
  manufacturer's row painted; 10 keep their artist glass. No body-skin triangle is deleted (the openings are closed,
  not cut wider), and nothing is removed away from the fuselage side (§8.1).
- **Plug bands** (§8.4): the mesh is split at the fuselage-plug stations of `js/aircraft/fit.js`; the 2 cm band gets its
  own charts, as long as the longest plug of any type on the model, so stretched types have texels for the plug.

| Model | px/m at 2048 | Fuselage cm/px (2048 / 1024) | Charts | Engines found | Cabin windows | Plug bands (m, model; longest plug) |
|---|---|---|---|---|---|---|
| a319 (Airbus A319) | 35.4 | 2.8 / 5.7 | 100 | 2 | paint: 32 painted, 66 glass / 66 openings removed | - |
| a320 (Airbus A320) | 35.3 | 2.8 / 5.7 | 99 | 2 | paint: 40 painted, 80 glass / 80 openings removed | - |
| a321 (Airbus A321) | 32.6 | 3.1 / 6.1 | 97 | 2 | paint: 48 painted, 96 glass / 96 openings removed | - |
| a333 (Airbus A330-300) | 20.0 | 5.0 / 10.0 | 108 | 2 | paint: 69 painted | - |
| a359 (Airbus A350-900) | 19.2 | 5.2 / 10.4 | 110 | 2 | paint: 60 painted, 112 glass / 112 openings removed | 12.84 (4.45), 45.35 (2.56) |
| a388 (Airbus A380-800) | 15.3 | 6.5 / 13.1 | 102 | 4 | paint: 109 painted | - |
| b738 (Boeing 737-800) | 35.6 | 2.8 / 5.6 | 84 | 2 | paint: 45 painted, 0 glass / 83 openings removed | 9.99 (2.74), 25.97 (1.58) |
| b744 (Boeing 747-400) | 20.1 | 5.0 / 10.0 | 104 | 4 | paint: 106 painted | - |
| b748 (Boeing 747-8) | 14.0 | 7.2 / 14.3 | 89 | 4 | keep: 0 painted | - |
| b752 (Boeing 757-200) | 31.7 | 3.2 / 6.3 | 93 | 2 | keep: 2 painted | 14.93 (3.98), 30.32 (2.99) |
| b763 (Boeing 767-300) | 25.9 | 3.9 / 7.7 | 73 | 2 | paint: 53 painted, 92 glass / 92 openings removed | 10.85 (3.47), 37.18 (2.99) |
| b788 (Boeing 787-8) | 22.7 | 4.4 / 8.8 | 122 | 2 | paint: 45 painted, 82 glass / 0 openings removed | 10.79 (6.09), 37.98 (5.49) |
| bcs1 (Airbus A220-100) | 39.0 | 2.6 / 5.1 | 83 | 2 | keep: 0 painted | - |
| bcs3 (Airbus A220-300) | 39.1 | 2.6 / 5.1 | 60 | 2 | keep: 0 painted | - |
| crj2 (Bombardier CRJ200) | 54.1 | 1.8 / 3.7 | 71 | 2 | paint: 12 painted | - |
| crj7 (Bombardier CRJ700) | 56.9 | 1.8 / 3.5 | 66 | 2 | keep: 0 painted | - |
| crj9 (Bombardier CRJ900) | 56.2 | 1.8 / 3.6 | 66 | 2 | keep: 0 painted | - |
| e170 (Embraer E170) | 43.7 | 2.3 / 4.6 | 99 | 2 | keep: 0 painted | - |
| e190 (Embraer E190) | 38.0 | 2.6 / 5.3 | 106 | 2 | keep: 0 painted | 9.11 (0.80), 23.27 (1.58) |
| e75l (Embraer E175) | 41.4 | 2.4 / 4.8 | 74 | 2 | keep: 0 painted | - |
| md11 (McDonnell Douglas MD-11) | 17.2 | 5.8 / 11.6 | 97 | 2 | keep: 0 painted | - |

Outer shape, `MODEL_DIMS` and `MODEL_FEATURES` are unchanged (vertices are duplicated along chart seams and plug
bands; the removed window glass and the closed openings change the triangle lists). The unatlased conversions are kept in
`refs/cache/models_orig/` (the atlas source).

## 3. The painter (`tools/liveries/paint.py`, `liveries.py`, `art.py`)

### 3.1 Design coordinates
A livery is a Python function painting on a `Canvas` built for one **aircraft type** (the type's fuselage plugs,
span and fin fit of `js/aircraft/fit.js` applied first), so titles and cheatlines sit where they belong on stretched
airframes: 737-900 / 737 MAX 8 / MAX 9, 787-9 / 787-10, 757-300, 767-400, A330-200, A350-1000 get their own bakes
(`<model>@<type>`). Coordinates: side view `(sn, eta)` (station / length, height / cabin half height), window line,
absolute metres, and the fin frame `(fu, fv)` (chordwise, spanwise). The side of each texel is taken from its position
(port / starboard), so text reads correctly on both sides (mirrored art only where the airline mirrors it).

### 3.2 Primitives
`paint`, `below` (region under a smooth curve), `band`, `gradient`, `poly` (anti-aliased by signed distance), `decal`
(titles from OFL fonts, `text` mode never mirrored), `fin_decal`, `engines` (nacelle colour + inlet lip), `tips`,
`hstab`, `pylons`, `gear_doors`, `from_texture` (a GPL FlightGear livery sampled through the model's original UVs:
used only for the Alaska 737-800 tail, N563AS). `finish()` multiplies the detail layer, keeps the dark areas and writes
the window alpha. Colours are sRGB hex, composited in linear light.

### 3.3 Art
Emblems are drawn by code (`art.py`: the United globe as a lat/long grid on a sphere with the pole where the official
graphic has it, the Air Canada rondelle and maple leaf, SVG paths for the others). No airline raster logo is copied.
Proprietary wordmark typefaces are replaced by OFL look-alikes (`docs/ATTRIBUTION_models.md` §3).

### 3.4 Converter fix found on the way
The 747-400, 767-300 and A220-100 sources contain triangles with garbage UVs (up to ±2,100 texture repeats), which
stretched the u16 UV quantisation to a 0.05 step, collapsing the atlas UVs (garbled titles on the 767). 
`tools/convert_models.py normalize_uvs` now shifts each triangle's UVs by the integer part of their centroid and gives
the garbage triangles (> 4 repeats; 219 / 34 / 285 / 19 triangles on b763 / b744 / bcs1 / b748) the texel of the
texture's mean colour. Re-converted b744, b748, b763, bcs1, a333: geometry identical to the previous conversion
(sorted triangle positions equal to 1 cm), dims identical, UV step now 1.5–7.5 × 10⁻⁵.

### 3.5 Photo checks (25 Sep 2026)
The render check of §5 needs the real aircraft to compare with. The airlines' media hosts block this sandbox, so
`tools/liveries/ref_photos.py` fetches recent photographs of the rendered type in the current livery from Wikimedia
Commons (1-2 per brand, 2019-2026, mostly 2025-2026; file page, author and licence recorded in the gitignored
`refs/cache/livref/index.json`; reference only, `docs/ATTRIBUTION_models.md` §5), and `tools/liveries/compare.py` sets
each photo beside a software render of our bake. The comparison found designs that did not look like the aircraft; they
were re-drawn with positions measured on the photos (station as a fraction of the length from the nose, height as the
cabin eta, sizes as fractions of the cabin height H; the measured values are in the comments of `liveries.py`):

| Brand | What the photo showed | Change |
|---|---|---|
| WestJet | large WESTJET title over the windows; teal aft body behind a diagonal from sn 0.54 (keel) to 0.77 (crown); navy wedge at the fin root; faceted leaf of white / teal on the fin | re-drawn (the earlier design had a small title, a teal tail with a dark maple leaf and no navy) |
| Aeroméxico | small-caps serif AEROMEXICO, a thin red swoosh across the windows, the navy only as a sweep at the tail, the eagle-knight head facing forward | re-drawn (the earlier design had a large navy aft body and an unrecognisable eagle) |
| Cathay Pacific | title larger and further forward, grey lower body from just below the windows, brushwing on the nose | re-drawn, brushwing re-drawn |
| Singapore Airlines | windows in a navy band with an orange line and a gold band below, from just aft of door 1 to the tail; orange trailing-edge stripe on the fin | re-drawn, Kris bird re-drawn (the earlier cheatlines were at the belly) |
| British Airways (A380) | title between the decks; speedwing at the upper-deck windows; tail ribbons red / blue / red | re-drawn (the earlier tail was mostly blue and the title sat in the upper-deck window row) |
| Emirates (A380) | flag tail with the red band descending along the fin onto the body to the wing root; black band; title between the decks | re-drawn; the 2025 photo shows the pre-2023 tail on A6-EUH, rendered as photographed |
| KLM | the fin is white with the blue crown logo; blue body down to just below the windows | corrected (the earlier fin was blue) |
| Flair | cream body, very large black "flair", black fin with a green disc | corrected (the earlier design was the old purple livery) |
| Volaris | black "volaris", black fin with the pixel cross, magenta nacelles | corrected |
| Avianca | red aft body from under the wing to the fin, red nacelles | red aft body added, invented tail symbol removed |
| Virgin Atlantic | light silver body, large thin title across the windows, "Virgin" signature large on the fin, red onto the lower tail cone | re-drawn |
| Starlux, ZIPAIR, Asiana, Copa, Philippine Airlines, Japan Airlines, Turkish Airlines, Qantas, EVA Air, China Airlines | titles too small / wrong text or face; tail art or body colours missing | titles re-sized and placed as measured; Starlux bronze belly and white tail, ZIPAIR teal window line and serif title, Asiana tail bands, Copa globe lines and "CopaAirlines", "Philippines" title |
| Delta Connection | CONNECTION is below the window row, not in it; on the starboard side the widget stays ahead of DELTA in reading order | moved; widget + DELTA + CONNECTION drawn as one lock-up (`liveries.lockup`, `Canvas.decal(block=...)`) |
| United Express | UNITED (blue) and EXPRESS (grey) same size on one line; one E175 (N206SY) still wears the 2010 Globe livery | lock-up re-drawn; Globe regional aircraft not modelled per tail |
| American Eagle | symbol and title below the window row (mainline: across the windows); on the starboard side the symbol stays forward of the title | moved (mainline unchanged; AA elements keep their stations on both sides, as photographed) |
| Air Canada Express | AIR CANADA over the windows, rondelle + EXPRESS on a second line below them | re-drawn as a lock-up |
| Sun Country | orange forward body with the white title, white centre section, navy aft body and tail with the orange sun | re-drawn (the earlier design, from a text description, was navy all over) |
| FedEx | white body, purple tail and aft body behind a slash at sn 0.71-0.80, FedEx title half the body height with Express below | re-drawn (the earlier design showed a purple crown) |
| Breeze | white title | title colour |
| Qatar, SAS, ITA | burgundy fin with a grey oryx; SAS dark blue down the aft body; ITA medium blue | corrected |
| JetBlue | the tail tiles of the refreshed livery are about half the cabin height | tiles enlarged |
| Lettering on fins (SAS, ANA, Sun Country S) | fin lettering read mirrored on the starboard side (fin decals default to a mirrored symbol) | drawn in text mode |

United, Alaska, American, Delta, Southwest, JetBlue, Air Canada, Frontier and Hawaiian matched their photos in layout
(United and Alaska closely; Hawaiian and Frontier with simplified art); their designs are unchanged apart from the
table above.

## 4. Output, sizes and runtime

- `data/liveries/<BRAND>/<model>[@<type>]-{hi,mid,lo}.webp`: 2048 / 1024 / 512 px (area-averaged downscale), WebP
  RGBA (quality 88 / 84 / 80).
- `data/liveries/manifest.json` and `manifest.js` (`LIVERY_MANIFEST`): entries `{brand, model, pxm, types, files, file,
  painted_as, bytes, variants[]}` (`pxm`: the model's atlas px per metre at 2048) and `brands{name, livery, since, refs, colors, status, types}`.
- Totals: 61 designs (57 with bakes; Air India, Swiss, China Eastern, Air China fly only 777s at SFO), 117 brand × model entries (incl. the neutral `_N` variants), 163 textures (incl. plug and window-row variants); hi 12.7 MB, mid 6.4 MB, lo 3.3 MB (WebP, 20-150 KB per hi texture).
- **Runtime (legacy renderer, this workflow's files):** `js/aircraft/liveries.js liveryTextureFor(brand, model, type,
  res)` picks the entry / variant; resolution `window.SFO_LIVERY_RES`, else `hi` for `?quality=ultra`, else `auto`
  (`mid`, or `hi` where the atlas is coarse at mid, `pxm / 2 < 11` px/m: A330, A350, A380, 747, MD-11);
  base URL `window.SFO_LIVERY_BASE` (default `data/liveries/`). `js/live/models.js getLiveryTexture` loads on demand
  and caches per URL (only the brands in view are fetched). `js/live/aircraft.js` resolves `ac.liv` per aircraft
  (brand from the ICAO address when the track has no registration) and binds the texture to the atlas draw
  (`uLivTex = 1`). `js/shaders/aircraft_real.js`: atlas alpha < 0.5 = window glass (dark, reflective, warm cabin light
  at night), clear coat on paint only. Without a brand texture the neutral atlas is recoloured by the brand's runtime
  colour family (777 family: procedural airframe, runtime colours only). While the texture of a type whose airframe or
  window row differs from its model's own type is loading (737-700 on the 737-800 model, 787-9, A321neo, ...), the
  aircraft is drawn as the procedural airframe (one row of windows), not with the model's own atlas, whose window row
  would be squeezed or stretched by the fuselage plugs (seen in an app screenshot of the snapshot's Southwest 737-700,
  25 Sep 2026); if the texture fails to load, the model's own atlas is used. The texture request starts when the
  aircraft comes within the model LOD distance (1-4 km), so the switch happens far from the camera.
- **Artifact (16 MB):** ship only the `lo` files the snapshot needs (`build.py --list-snapshot`, as the app picks them incl. neutral variants) with
  `window.SFO_LIVERY_RES = 'lo'`. Requests to the owners of `traffic.js`, `js/three/aircraft.js`, `about.js`, `ui.js`
  and packaging: `docs/requests/liveries_brand.md`.

## 5. Render check

One Blender Cycles close-up per brand (`tools/liveries/render_blender.py`: the brand's most frequent SFO type with a
bake, `hi` texture, three-quarter front view from port, sun + sky, 12-16 samples, denoised; freighters with their cabin
glass painted over) in `out/liveries/<CODE>.png` (not committed; `--view port|stbd|stbd34|rear34`, `--type`, `--zoom` for
other views), compared by eye with the reference photographs of §3.5 (`tools/liveries/compare.py`, photo beside a
software render of the same type).

Result (25 Sep 2026, all 57 brands with bakes rendered after the last bake):

- **Cabin windows: one row on every render** (UAL 737-800 and SWA 737-700, the renders the owner flagged, included;
  two decks on the A380 and 747). No painted row beside a modelled one, no doubled windows at the plugs.
- **Match with the photos**: United, United Express, Delta, Delta Connection, American, American Eagle, Alaska,
  Southwest, JetBlue, Air Canada, WestJet, Aeroméxico, Sun Country, Breeze, Cathay Pacific, Singapore, Japan Airlines,
  EVA, Korean, Qantas, British Airways, Emirates, Turkish, Virgin Atlantic, KLM, Avianca, Volaris, Copa, Flair, ZIPAIR,
  Starlux, FedEx: layout (title position and size, colour regions, tail) as on the photos, emblems simplified.
- **Photo differs in details only** (simplified art, colours approx): Hawaiian (lei and flower pattern of the body
  simplified), Frontier (one generic animal; per-aircraft animals), Air New Zealand (fern), Philippine Airlines,
  China Airlines, Asiana, Qatar (oryx), SAS, ITA, Lufthansa (the photographed 747-8s still wear the pre-2018 scheme; the
  2018 design is rendered), Air France, Aer Lingus, Vietnam, Fiji, TAP, China Southern, Air Premia, French bee, Iberia,
  LOT, Condor, UPS (checked against the descriptions; photos for part of them).
- **In the app** (headless Chromium, SwiftShader / llvmpipe, snapshot mode; `out/live/livapp_*.png`): the Southwest
  737-700, the United Express E175 and the Alaska 737-800 of the snapshot wear their brand bakes (resolved by
  callsign and registration, `brandSrc` obs) with one window row. On the software renderer a 1024 px WebP took up to
  47 s to arrive; the first screenshot (taken after 4 s) showed the model's own atlas instead, which on the 737-700
  had the 737-800 row squeezed at the fuselage plugs: fixed in `js/live/aircraft.js` (§4).

## 6. Per-brand status

`colours`: count of design colours by provenance: `official` (brand guide / official swatch on the airline's own
host), `measured` (sampled on an official press image, URL in the refs), `photo` (sampled on the reference photographs
of §3.5: real paint under real light, not an official value), `third-party` (profile chart or copied brand guide on a
third-party host: unverified), `approx` (from the reference description / general knowledge / a photo under strongly
coloured light: unverified).
`refs`: hosts of the references (full URLs in `data/liveries/manifest.json`).

| Code | Brand | Livery | Baked textures | Colours | Refs | Status / known simplifications |
|---|---|---|---|---|---|---|
| UAL | United Airlines | 2019 "blue" livery (Rhapsody Blue swoop, Runway Gray belly, globe tail) | a319, a320, a321@a21n, b738, b738@b38m, b738@b39m, b752, b752@b753, b763, b763@b764, b788, b788@b789, b788@b78x | official 4, approx 1 | mma.prnewswire.com; united.mediaroom.com | layout measured on the official United livery graphic (737-800); other types scaled by fuselage length |
| UAL-X | United Express | 2019 livery with UNITED EXPRESS titles | crj2, crj7, e170, e75l | official 4, approx 2 | Wikimedia Commons photos; mma.prnewswire.com; united.mediaroom.com | 2019 design on regional jets (United release: applied to regional aircraft); title lock-up measured on a photo of an E175; fleet mid-transition (some SkyWest E175s still wear the 2010 Globe livery: not modelled per tail) |
| UAL-G | United Airlines (2010-2019 "Globe" livery) | post-merger livery: white top, grey belly, gold/blue cheatline, gold globe on a blue tail | a319, a320, b738, b738@b39m | approx 3 | FlightGear texture (GPL-2.0); norebbo.com | legacy variant (still on part of the fleet; no per-tail list, liveries.md §3.1): used only by per-registration override |
| DAL | Delta Air Lines | 2007 "Onward and Upward" livery (white DELTA on the belly since 2015) | a319, a320, a321, a321@a21n, a333, a333@a332, a333@a339, b738, b738@b39m, b752, b752@b753, b763, b763@b764, bcs1, bcs3 | official 2, third-party 2, approx 1 | deltamuseum.org; news.delta.com; norebbo.com; waatbp.oneclub.org | layout from official photos + profile reference; belly title not drawn |
| DAL-C | Delta Connection | Delta livery with DELTA CONNECTION titles | e75l | official 2, approx 3 | Wikimedia Commons photos; deltamuseum.org; news.delta.com; norebbo.com; waatbp.oneclub.org | layout from the ERJ-175 profile reference |
| AAL | American Airlines | 2013 livery, 2021 Silver Eagle paint | a319, a320, a321, a321@a21n, b738, b738@b38m, b788, b788@b789 | measured 2, approx 2, third-party 1 | news.aa.com; norebbo.com; simpleflying.com | layout from the official 2013 photo + profile reference; flight symbol simplified |
| AAL-E | American Eagle | American 2013 livery with American Eagle titles | e75l | measured 1 | Wikimedia Commons photos; news.aa.com; norebbo.com; simpleflying.com | layout from the ERJ-175 profile reference |
| ASA | Alaska Airlines | 2016 brand refresh (tail portrait, aurora sweep), also on Horizon / SkyWest E175s | a321@a21n, b738, b738@b38m, b738@b39m, b738@b737, e75l | measured 4, approx 1 | FlightGear texture (GPL-2.0); news.alaskaair.com | layout from the official render; portrait strongly simplified (re-drawn) |
| SWA | Southwest Airlines | 2014 "Heart" livery | b738, b738@b38m, b738@b737 | third-party 2, approx 2 | dallasnews.com; investors.southwest.com; norebbo.com | layout from the profile reference; heart on the belly not drawn |
| JBU | JetBlue | 2023 livery refresh (blue allover, tail pattern extended onto the body) | a320, a321, a321@a21n, bcs3 | measured 4, approx 1 | news.jetblue.com; s202.q4cdn.com | the Mint tile pattern of the official photo on every airframe (patterns vary by aircraft: inf); fleet mid-transition from the white livery (inf: new livery rendered) |
| FFT | Frontier Airlines | 2014-15 livery: green FRONTIER title, animal on a green tail | a320, a320@a20n, a321, a321@a21n | measured 3, approx 1 | news.flyfrontier.com; simpleflying.com | per-aircraft animal not modelled (a generic stylised animal on every tail) |
| ACA | Air Canada | 2017 livery (black tail, belly and engines; red maple-leaf rondelle) | a320, a321, b738@b38m, b788@b789, bcs3 | official 2, approx 1 | aircanada.com; cbc.ca; norebbo.com | layout from the CBC description and the profile reference |
| ACA-X | Air Canada Express | 2017 livery with AIR CANADA EXPRESS titles | crj9 | official 2 | Wikimedia Commons photos; aircanada.com; cbc.ca; norebbo.com | title placement approx |
| WJA | WestJet | 2018 livery (white body, WESTJET title, teal aft body with a navy wedge, faceted leaf tail) | b738, b738@b38m, b738@b737, b788@b789 | photo 7 | Wikimedia Commons photos; travelweek.ca; westjet.mediaroom.com | layout measured on a photo of a 737-8 (starboard); the halftone texture of the tail facets is drawn flat; colours from photos (approx) |
| AMX | Aeroméxico | Caballero Águila livery (white body, red swoosh, navy tail sweeping onto the aft body; the 2024 updated eagle is being applied gradually) | b738, b738@b38m, b738@b39m, b788@b789 | approx 5 | Wikimedia Commons photos; breitflyte.com; norebbo.com | layout measured on a photo of a 737-8 (starboard); eagle re-drawn from the photo; colours approx |
| HAL | Hawaiian Airlines | 2017 livery (Pualani on a purple sunrise tail, lei flowers on the aft body) | a321@a21n, a333@a332 | approx 6 | news.alaskaair.com; norebbo.com | Pualani and the lei strongly simplified |
| SCX | Sun Country Airlines | 2018 livery (orange forward body with the white title, white centre section, navy aft body and tail with the orange sun) | b738 | approx 3 | Wikimedia Commons photos; startribune.com | layout measured on a photo of a 737-800 (orange sn 0-0.41 at the crown / 0.48 at the keel, navy aft of a diagonal from the keel at sn 0.69 to the fin root, orange line on the diagonal); contour pattern of the navy not drawn |
| MXY | Breeze Airways | 2021 livery (blue fuselage, navy tail with the light-blue check) | bcs3 | third-party 4 | Wikimedia Commons photos; airbus.com; norebbo.com | layout from the profile reference |
| CPA | Cathay Pacific | 2015 livery (all-green tail with the white brushwing, grey lower body, name above the windows, brushwing on the nose) | a359 | approx 3 | Wikimedia Commons photos; news.cathaypacific.com; norebbo.com | layout measured on photos of A350-900s; brushwing re-drawn from a photo; colours approx |
| EVA | EVA Air | 2015 update (green tail with the orange globe, darker green belly) | b788@b789 | approx 2 | airlinereporter.com | from the description; globe simplified |
| CAL | China Airlines | plum-blossom tail (1995 identity), white fuselage | a359 | approx 3 | china-airlines.com | from knowledge only: approx |
| SIA | Singapore Airlines | midnight-blue tail with the gold Kris bird; navy window band with orange and gold lines | a359 | photo 6 | Wikimedia Commons photos; airlinegeeks.com | layout measured on photos of A350-900s; Kris bird re-drawn (simplified); title face a look-alike |
| KAL | Korean Air | new identity 11 Mar 2025: metallic sky blue, KOREAN logotype, dark-blue taegeuk | b788@b789, b788@b78x | third-party 2 | norebbo.com; samchui.com | fleet mid-transition from the 1984 livery (new livery rendered: inf) |
| ANA | ANA | "Triton Blue" livery (1982) | b788, b788@b789 | third-party 2 | ana.co.jp; norebbo.com | at SFO ANA flies the 777-300ER (procedural airframe; runtime colours) |
| JAL | Japan Airlines | 2011 "Tsurumaru" crane livery | b788, b788@b789 | approx 1 | japantimes.co.jp; norebbo.com | crane circle simplified |
| QFA | Qantas | 2016 livery (red tail with the streamlined kangaroo, red wrapping onto the aft body) | b788@b789 | approx 1 | norebbo.com | kangaroo simplified |
| PAL | Philippine Airlines | flag-motif tail (blue and red triangles, yellow sun) | a359 | approx 3 | philippineairlines.com | approx; at SFO mostly the 777-300ER (procedural) |
| AFR | Air France | Eurowhite livery with the tricolour tail stripes | a359 | approx 2 | corporate.airfrance.com | approx |
| BAW | British Airways | Chatham Dockyard Union-flag tail, midnight-blue belly, red / blue speedwing | a388 | approx 4 | Wikimedia Commons photos; key.aero; norebbo.com; simpleflying.com | layout measured on a photo of the A380 (port side); tail ribbons and speedwing simplified; colours approx |
| DLH | Lufthansa | 2018 brand design (dark-blue tail wrapping onto the aft fuselage, white crane in a ring) | a359, a388, b744, b748 | third-party 1 | dezeen.com; lufthansagroup.com | fleet mid-transition (some 747-400 keep the old colours; new design rendered: inf) |
| UAE | Emirates | livery with the UAE-flag tail and gold titles (as photographed on the A380 in 2025; the 2023 update is being applied gradually) | a388 | approx 5 | Wikimedia Commons photos; norebbo.com | layout measured on a 2025 photo of the A380 (starboard); Arabic title not drawn; flag simplified |
| THY | Turkish Airlines | red tail with the goose in a white circle, grey tulip stripe | a359, b788@b789 | approx 1 | turkishairlines.com | goose simplified |
| VIR | Virgin Atlantic | 2019 "Flying Icons" livery (light silver fuselage, red tail with the Virgin signature, purple-grey titles) | a359@a35k, b788@b789 | approx 4 | Wikimedia Commons photos; virgin.com | layout from photos of 787-9s (one at SFO); flying-icon figures and the flag are not drawn; signature in a script look-alike |
| AIC | Air India | 2023 livery (deep red, aubergine and gold; window-frame motif) | - (procedural airframe only) | approx 3 | airindia.com | SFO fleet is 777 only (procedural airframe: runtime colours); fleet mid-transition |
| ANZ | Air New Zealand | black tail with the white koru, black fern on the aft fuselage | b788@b789 | approx 1 | norebbo.com | fern simplified to a black aft sweep |
| AVA | Avianca | 2023 brand (lowercase avianca, brighter red; red tail, red aft body and nacelles) | a320, a320@a20n | approx 4 | Wikimedia Commons photos; airlinegeeks.com; avianca.com | layout from 2025 photos of A320neos; the tail symbol is not drawn; fleet mid-transition (2023 brand rendered: inf) |
| VOI | Volaris | white fuselage, black lowercase title, black tail with the pixel cross, magenta nacelles | a320, a320@a20n, a321@a21n | approx 7 | Wikimedia Commons photos; volaris.com | layout from a photo of an A320neo; pixel cross simplified; colours approx |
| CMP | Copa Airlines | white fuselage, CopaAirlines title, navy tail with the Copa globe | b738@b39m | approx 2 | Wikimedia Commons photos; copaair.com | layout from photos of 737 MAX 9s; globe lines simplified; colours approx |
| KLM | KLM | blue upper fuselage, white lower body, white tail with the blue KLM crown logo | b788@b789, b788@b78x | approx 3 | Wikimedia Commons photos; news.klm.com | layout from photos of a 787-10 and a 787-9; crown simplified |
| SWR | Swiss | red tail with the white Swiss cross | - (procedural airframe only) | approx 1 | swiss.com | 777-300ER only at SFO (procedural) |
| AAR | Asiana Airlines | champagne fuselage, tail in the Asiana colour bands | a359 | approx 8 | Wikimedia Commons photos; flyasiana.com | layout from photos of A350-900s; tail bands simplified; colours approx |
| SJX | Starlux Airlines | champagne-silver body, bronze belly with a gold line, white tail with the emblem | a359 | approx 4 | Wikimedia Commons photos; starlux-airlines.com | layout from photos of A350-900s; emblem simplified; colours approx |
| TZP | ZIPAIR | white body, teal window line, large black ZIPAIR, pale tail with dashes | b788 | approx 4 | Wikimedia Commons photos; zipair.net | layout from photos of 787-8s; tail dashes simplified; colours approx |
| EIN | Aer Lingus | 2019 livery (teal tail with the white shamrock) | a333, a333@a332 | approx 2 | aerlingus.com | approx |
| QTR | Qatar Airways | grey fuselage, burgundy tail with the grey oryx | a359 | third-party 2 | Wikimedia Commons photos; norebbo.com | burgundy fin with the grey oryx (photo check); oryx simplified; Arabic script not drawn |
| FBU | French bee | white / blue gradient fuselage, blue tail | a359 | approx 1 | frenchbee.com | from knowledge only: approx |
| SAS | SAS | 2019 livery (silver-grey fuselage, dark-blue tail with SAS sweeping down the aft body) | a333, a359 | approx 2 | Wikimedia Commons photos; sasgroup.net | approx |
| TAP | TAP Air Portugal | 2017 livery (white; green and red on the tail) | a333@a339 | approx 2 | flytap.com | approx |
| APZ | Air Premia | white fuselage, dark navy tail | b788@b789 | approx 1 | airpremia.com | from knowledge only: approx |
| FLE | Flair Airlines | cream body, black flair title, black tail with the green disc | b738@b38m | approx 3 | Wikimedia Commons photos; flyflair.com | layout from 2023 and 2026 photos of 737 MAX 8s (the 2026 photo adds a black aft body on one aircraft: not drawn); colours approx |
| ITY | ITA Airways | 2021 livery (blue Savoia fuselage, white titles, tricolour tail) | a333@a339, a359 | approx 1 | Wikimedia Commons photos; ita-airways.com | approx |
| CSN | China Southern | blue tail with the red kapok flower | b788@b789 | approx 2 | csair.com | approx |
| CES | China Eastern | swallow logo on the tail (red / blue) | - (procedural airframe only) | approx 1 | ceair.com | 777 only at SFO (procedural) |
| CCA | Air China | red phoenix on a white tail | - (procedural airframe only) | approx 1 | airchina.com | 777 only at SFO (procedural) |
| HVN | Vietnam Airlines | teal tail with the golden lotus | a359 | approx 2 | vietnamairlines.com | approx |
| FJI | Fiji Airways | masi (tapa) pattern tail | a333, a333@a332, a359 | approx 2 | fijiairways.com | pattern simplified |
| CFG | Condor | 2022 striped livery (each aircraft one colour; red "Passion" rendered) | a333@a339 | approx 1 | condor.com | colour varies per aircraft (inf: red) |
| IBE | Iberia | 2013 livery (red and yellow IB symbol on the tail) | a333@a332 | approx 2 | iberia.com | approx |
| LOT | LOT Polish Airlines | dark-blue tail with the crane in a circle | b788, b788@b789 | approx 1 | lot.com | approx |
| FDX | FedEx | FedEx Express livery (white body, purple tail and aft body, FedEx title with Express) | b752, b763, md11 | approx 4 | Wikimedia Commons photos; newsroom.fedex.com | layout measured on a photo of the MD-11F (port side); the earlier design showed the purple crown of the 1994 scheme, which the photo does not |
| UPS | UPS | brown tail and belly, gold shield, white upper fuselage | b744, b748, b752, b763, md11 | approx 2 | norebbo.com | approx |

## 7. Known deviations and open items

- **Colours of most international brands are `approx`** (no official paint values fetched; airline image hosts and
  Airbus media are behind bot protection from this sandbox). Official values exist only for United (livery graphic
  swatches), Delta (Blue / Red, official palette image) and Air Canada (logo guideline). Measured on official images:
  American, Alaska, JetBlue, Frontier. Measured on the Commons photographs of §3.5 (real paint under real light, not
  official values): WestJet, Singapore, KLM (blue), United Express (EXPRESS grey), Sun Country, and the colour checks of
  the redesigned brands. Owner: supply brand guides where exact values matter.
- **Layouts** measured on an official side-view graphic for United (737-800), on official photos for American,
  Alaska, JetBlue, and on the Commons photographs (§3.5) for WestJet, Aeroméxico, Cathay, Singapore, British Airways,
  Emirates, Sun Country, FedEx, Delta Connection, United Express, American Eagle, Air Canada Express, KLM, Volaris,
  Avianca, Flair, Copa, Starlux, ZIPAIR, Virgin, Japan Airlines, Turkish, Qantas, EVA, China Airlines. The others
  (Air Premia, French bee, TAP, Vietnam, Fiji, China Southern, Iberia, LOT, Condor, Aer Lingus, UPS) follow the
  reference descriptions and are simplified; some of their photos failed to download (Wikimedia rate limit) and can be
  fetched later with `tools/liveries/ref_photos.py`.
- **Fleet mixes seen on the photos, not modelled per tail**: SkyWest United Express E175s still in the 2010 Globe
  livery (N206SY, Jan 2026), Lufthansa 747-8s in the pre-2018 scheme, Emirates A380s with the pre-2023 tail. The
  per-registration override table (`brands_meta.REG_OVERRIDE`) can assign `UAL-G` to known Globe tails when a verified
  list exists.
- **Per-aircraft art is not modelled**: Frontier animals (one generic stylised animal), JetBlue tail patterns (the
  official Mint photo's pattern on all), Condor colours (red rendered), special liveries (overrides rendered standard).
- **Fleet transitions rendered as the new livery** (`inf`): United 2019 vs Globe (no per-tail list; `UAL-G` exists
  for overrides only), Korean 2025, Lufthansa 2018, Avianca 2023, Air India 2023 (777 only at SFO), Aeroméxico 2024
  eagle, JetBlue 2023.
- **No model**: Porter E195-E2 (the 777 family has artist models since 26 Sep, §9.4). **MD-11 tail engine** is painted with the fin (the type table has no centre engine).
- **Texel density** of the large models is 5–7 cm/px at 2048 (A330, A350, A380, 747-8): titles are sharp enough at
  gate distance, not in extreme close-ups.
- **A380 textures**: licence caveat (CC-BY-NC 3.0 possible), `docs/ATTRIBUTION_models.md` §1.
- Requests pending with other owners (`docs/requests/liveries_brand.md`): `traffic.js` should pass reg / hex / type
  so the track (UI, three.js) sees the resolved brand; `js/three/aircraft.js` LiveryLibrary to use the published
  manifest; About notice; UI brand display; artifact packaging of the `lo` set.

## 8. Cabin windows: exactly one row (owner feedback, 25 Sep 2026)

Owner: "I see two sets of windows on these livery planes" (`out/liveries/UAL.png`, `SWA.png`, 737-800 model).

### 8.1 Diagnosis (verified on the models and renders)

- `tools/liveries/atlas.py` painted a window row from the procedural type table (`js/aircraft/types.js` `win`, estimates)
  on the five models it believed had no windows (`PAINT_WINDOWS`: 737-800, 747-400, A330-300, A380, CRJ200).
- The 737-800 does have the artist's windows: 41 openings per side in the skin with a dark glass strip behind them (no
  glass objects, so the check missed them). Painted row + openings = the two rows of the UAL / SWA / DAL / ASA renders.
- The 747-400 (`BOE.png`) and the CRJ200 (`UAX.png`) have their windows painted in the source texture; the atlas kept
  them as "small dark areas" (the CRJ200 also kept the source's black UNITED EXPRESS letters on every brand).
- Found while fixing: the A350's texture draws window frames around its artist windows: removing the glass alone left a
  grey second row (fixed by dropping the source skin detail in the window band on painted models).
- Negative fuselage plugs (737-700 on the 737-800 model, 767-200, A330-200 / -800) slid the aft body over the forward
  body (`js/live/models.js` applyStretch): 3 m of doubled skin and doubled windows on the 737-700 (the SWA render).
- The renderer adds no windows to the imported models (`js/shaders/aircraft_real.js` draws the kind-1 glass and the
  atlas-alpha glass only); procedural windows exist only on the procedural airframe (777 family, and every aircraft
  beyond the model LOD distance), one row from `TYPES.win`. `js/live/aircraft.js` never draws the procedural body and
  the imported model of one aircraft together (only the procedural gear under gear-less models).

**Second pass: verification of the first fix (25 Sep 2026).** The window sheets of §8.6 and close-up renders found:

- *Ghost rims.* The neutral atlas carries the model's own row as painted glass (alpha 0.1) with anti-aliased rims
  (alpha 0.5-0.99). The painter reset the skin detail only where alpha < 0.5, so on every other type of the model
  (737-700 / -900 / MAX on the 737-800 model, 787-9 / -10, A321neo, A330-200 / -900, ...) the rims of the model's own
  windows stayed as faint window outlines next to the type's painted row: a faint second row. Fixed:
  `paint.py _base_window_rims` treats the rims in the base row's band as plain skin.
- *Doubled windows at negative plugs.* The inferred 737-700 / -600 rows had two windows 0.3 m apart at each plug cut
  (the plug lengths are not multiples of the window pitch). Fixed: `windows._plug_transform` keeps the row regular at
  each cut (a window closer than 0.75 pitch to the one ahead of the cut is dropped; gaps of 1.5 pitches get windows).
- *Holes.* The removal deleted every triangle inside a removed window's rectangle, which also caught wing-tip and
  winglet triangles at the same station and height (A320, A319, 737-800, 767-300 and A350 wing tips were opened) and,
  on the A350 and E175, small skin triangles beside the windows. Fixed: only non-skin triangles within 0.3 m of the
  window's lateral position are removed; the fans that close the openings get their own vertices with the skin's
  outward normal (A350: loop vertices carried the normals of the reveal walls and shaded dark triangles); new open skin
  edges are checked: none on any model (`atlas.py` records `reclosed` / `open` in `head.atlas.windows.removed`).
- *The E175 flight deck.* The "stray window" the first pass removed from the E175 at 3.06 m is the pane of the aft
  flight-deck side window: its removal left a see-through hole in the flight-deck glazing. Restored; without a
  reference row nothing is removed.
- *A321 and A321neo share the glass.* The artist glass matches the A321 drawing (48 / 48) but the A321neo drawing has
  no windows at 25.6 / 26.1 m; the glass is geometry shared by both types, so the A321 model now paints both rows
  (`windows.decision` checks every type with a drawing that is rendered on the model).
- The bakes of the first pass predated the last atlas run (textures and atlas layout out of step); every model was
  re-atlased and every livery re-baked from the same atlas.

### 8.2 The real rows: manufacturers' drawings (`tools/liveries/windows_ref.py` -> `tools/liveries/windows_ref.json`)

No airport-planning document tabulates cabin windows, but the manufacturers' drawings draw them: Boeing's CAD 3-views
for airport planning (DXF/DWG, "accurate to within 6 inches"; MD-11 "~ +/- 3 inches";
https://www.boeing.com/commercial/airports/3-view), the Airbus AC side views (2-2-0, 2-7-0 door location), the
Bombardier CRJ200 APM Figure 2. Every drawing is rendered to ink (DXF at 80 px/m; PDF pages at up to 2400 dpi), window
outlines are the enclosed holes of window size along a straight line at a regular pitch, windows partly hidden behind
the wing root are found by template matching of the upper outline, windows crossed by a wing or a dimension line are
filled at the pitch, and windows entirely inside the wing's projection were filled by hand where the plot shows them
(747-400 main deck 38.1-43.7 m, 767-300 32.0-34.8 m, A380 main deck 27.8-47.0 m). Scale and origin: the Boeing drawing
unit (inch; MD-11 foot) and the nose tip; Airbus: the published door stations of `SPEC` matched to the door outlines
(least squares, max residual 0.00-0.08 m; the fitted nose falls at -0.12 to +0.04 m); CRJ200: the overall length
(door 1 at 4.53 m vs 4.74 m published). Heights: the window centre relative to the fuselage centre line of the barrel
section (eta, -1 keel .. +1 crown). Checks on the results: fuselage heights of the drawings 4.01 m (737, 757), 5.41 m (767),
6.18 m (777), 6.04 m (MD-11); window pitch 20 in (737 / 757 / MD-11: 0.506-0.512 m), 22 in (767, 777: 0.562 m), 24 in
(787: 0.613 m), 21 in (A320 family, A330: 0.526-0.537 m), 25 in (A350, A380: 0.637-0.639 m); the 777-200 row ends at
48.18 m, the 777-300 row with the published 10.13 m shorter fuselage predicts 48.19 m. Not usable (window rows not drawn
or not at a verifiable scale): 737-600 / -700 / -900 (their CAD 3-views draw no cabin windows), 747-8 (the DWG converts
to an incomplete DXF), E-Jets, CRJ700 / 900, A220 (door stations for a calibration not published in our documents).
Plots of every measurement: `python3 tools/liveries/windows_ref.py --plot DIR` (red: windows found, orange: partly
hidden, green: filled; magenta: nose / doors).

Each type's row (`tools/liveries/windows.py type_rows`; stations in m aft of the nose tip; `inferred` = not on that type's
own drawing):

| Type | Model | Row source | Windows (main deck) | First / last (m) | Pitch (m) | Height (eta) | Further decks | Notes |
|---|---|---|---|---|---|---|---|---|
| a19n | a319 | Airbus AC A319 (15 Jul 2025) FIGURE-2-2-0-991-008-A01 sheet 1 (A319neo) (height: a20n drawing) | 31 | 6.03 / 23.96 | 0.527 | 0.327 |  |  |
| a20n | a320 | Airbus AC A320 (1 Jun 2024) FIGURE-2-2-0-991-009-A01 sheet 1 (A320neo) | 39 | 6.16 / 27.57 | 0.536 | 0.327 |  |  |
| a21n | a321 | Airbus AC A321 (15 Jul 2025) FIGURE-2-2-0-991-010-A01 sheet 1 (A321neo) | 46 | 6.17 / 34.64 | 0.534 | 0.288 |  |  |
| a319 | a319 | Airbus AC A319 (15 Jul 2025) FIGURE-2-2-0-991-002-A01 sheet 1 (height: a320 drawing) | 32 | 6.03 / 23.45 | 0.526 | 0.326 |  |  |
| a320 | a320 | Airbus AC A320 (1 Jun 2024) FIGURE-2-2-0-991-004-A01 sheet 1 | 40 | 6.16 / 27.57 | 0.531 | 0.326 |  |  |
| a321 | a321 | Airbus AC A321 (15 Jul 2025) FIGURE-2-2-0-991-005-A01 sheet 1 | 48 | 6.17 / 34.65 | 0.534 | 0.287 |  |  |
| a332 | a333 | Airbus AC A330 (1 Dec 2025) FIGURE-2-7-0-991-006-A01 Door Location sheet 2 (A330-200/-800) | 57 | 7.24 / 42.87 | 0.537 | 0.278 |  |  |
| a333 | a333 | Airbus AC A330 (1 Dec 2025) FIGURE-2-7-0-991-006-B01 Door Location sheet 2 (A330-300/-900) | 69 | 8.33 / 48.73 | 0.529 | 0.29 |  |  |
| a338 | a333 | Airbus AC A330 (1 Dec 2025) FIGURE-2-2-0-991-012-A01 sheet 1 (A330-800) | 56 | 7.30 / 42.62 | 0.536 | 0.303 |  |  |
| a339 | a333 | Airbus AC A330 (1 Dec 2025) FIGURE-2-2-0-991-011-A01 sheet 1 (A330-900) | 67 | 8.80 / 48.63 | 0.530 | 0.305 |  |  |
| a359 | a359 | Airbus AC A350 (15 Jul 2025) FIGURE-2-2-0-991-001-A01 sheet 1 (A350-900; raster drawing) | 60 | 8.37 / 50.98 | 0.638 | 0.218 |  |  |
| a35k | a359 | Airbus AC A350 (15 Jul 2025) 2-2-0 page 4 (A350-1000; raster drawing) | 72 | 8.32 / 57.97 | 0.637 | 0.212 |  |  |
| a388 | a388 | Airbus AC A380 (1 Dec 2025) FIGURE-2-7-0-991-002-A01 Door Location sheet 2 (scale: upper-deck doors U1-U3 at 20.94 / 40.30 / 49.19 m; main deck M1-M5 6.32 / 16.50 / 32.68 / 44.74 / 53.63 m) | 47 | 13.00 / 52.68 | 0.639 | 0.565 | deck 1: 62 |  |
| b37m | b738 | Boeing CAD 3-view 737-7 (737_max7.zip, DWG -> DXF) | 35 | 6.11 / 26.23 | 0.522 | 0.243 |  |  |
| b38m | b738 | Boeing CAD 3-view 737-8 (737_max8.zip, DWG -> DXF) | 42 | 6.11 / 29.89 | 0.512 | 0.245 |  |  |
| b39m | b738 | Boeing CAD 3-view 737-9 (737_max9.zip, DWG -> DXF) | 45 | 6.11 / 32.52 | 0.512 | 0.234 |  |  |
| b3xm | b738 | Boeing CAD 3-view 737-10 (737_max10.zip, DWG -> DXF) | 48 | 6.11 / 34.71 | 0.512 | 0.234 |  |  |
| b736 | b738 | Boeing CAD 3-view 737-800 (7378.zip) | 31 | 5.64 / 22.18 | 0.512 | 0.231 |  | inferred: the b738 row with the b736 fuselage plugs of js/aircraft/fit.js |
| b737 | b738 | Boeing CAD 3-view 737-800 (7378.zip) | 35 | 5.64 / 24.57 | 0.512 | 0.231 |  | inferred: the b738 row with the b737 fuselage plugs of js/aircraft/fit.js |
| b738 | b738 | Boeing CAD 3-view 737-800 (7378.zip) | 45 | 5.64 / 30.41 | 0.512 | 0.231 |  |  |
| b739 | b738 | Boeing CAD 3-view 737-9 (737_max9.zip, DWG -> DXF) | 45 | 6.11 / 32.52 | 0.512 | 0.234 |  | inferred: 737-900 CAD 3-view (2001) draws no cabin windows; 737-9 fuselage: same length (42.11 m) and plug stations |
| b744 | b744 | Boeing CAD 3-view 747-400 (7474.zip) | 85 | 1.34 / 53.84 | 0.519 | -0.038 | deck 1: 21 |  |
| b748 | b748 | artist glass (no usable drawing) | - | - | - | - | - |  |
| b752 | b752 | Boeing CAD 3-view 757-200 (7572.zip) | 54 | 6.29 / 36.87 | 0.506 | 0.231 |  |  |
| b753 | b752 | Boeing CAD 3-view 757-300 (7573.zip) | 64 | 6.29 / 43.98 | 0.506 | 0.231 |  |  |
| b762 | b763 | Boeing CAD 3-view 767-200 (7672.zip) | 45 | 7.27 / 33.92 | 0.562 | 0.251 |  |  |
| b763 | b763 | Boeing CAD 3-view 767-300 (7673.zip) | 53 | 7.27 / 40.34 | 0.562 | 0.252 |  |  |
| b764 | b763 | Boeing CAD 3-view 767-400 (7674.zip) | 64 | 7.27 / 46.77 | 0.562 | 0.252 |  |  |
| b788 | b788 | Boeing CAD 3-view 787-8 (7878.zip, DWG -> DXF) | 45 | 8.26 / 41.94 | 0.613 | 0.254 |  |  |
| b789 | b788 | Boeing CAD 3-view 787-9 (7879.zip, DWG -> DXF) | 56 | 8.26 / 48.02 | 0.613 | 0.254 |  |  |
| b78x | b788 | Boeing CAD 3-view 787-10 (78710.zip, DWG -> DXF) | 64 | 8.26 / 53.52 | 0.613 | 0.254 |  |  |
| bcs1 | bcs1 | artist glass (no usable drawing) | - | - | - | - | - |  |
| bcs3 | bcs3 | artist glass (no usable drawing) | - | - | - | - | - |  |
| crj2 | crj2 | Bombardier CRJ200 APM rev. 8, 00-02-01 Figure 2 (raster drawing) | 12 | 6.31 / 14.13 | 0.744 | 0.227 |  |  |
| crj7 | crj7 | artist glass (no usable drawing) | - | - | - | - | - |  |
| crj9 | crj9 | artist glass (no usable drawing) | - | - | - | - | - |  |
| e170 | e170 | artist glass (no usable drawing) | - | - | - | - | - |  |
| e190 | e190 | artist glass (no usable drawing) | - | - | - | - | - |  |
| e195 | e190 | artist glass (no usable drawing) | - | - | - | - | - | plug windows from the artist pitch (inf) |
| e75l | e75l | artist glass (no usable drawing) | - | - | - | - | - |  |
| e75s | e75l | artist glass (no usable drawing) | - | - | - | - | - |  |
| md11 | md11 | Boeing CAD 3-view MD-11 (md11.zip) | 71 | 6.26 / 46.11 | 0.506 | 0.172 |  |  |

### 8.3 Per model: keep the artist's glass or paint the reference row

Keep when the artist glass matches the drawing (count within 2, 90 % of the reference windows within 0.35 pitch of an
artist window) or there is no usable drawing; otherwise remove the artist windows and paint (`tools/liveries/windows.py
decision`). Artist windows that the reference does not have are removed also on kept models (A321: 2); reference
windows the kept glass lacks are painted at the glass row's height (757-200: 2).

| Model | Artist windows | Decision | Reason | Removed by the atlas (per model, both sides) |
|---|---|---|---|---|
| a319 | 33 glass objects per side over 33 openings | paint | artist glass differs from the drawing (33 vs 32 windows, 53% within 0.35 pitch, pitch 0.533 vs 0.526 m) | glass 66, holes 66 |
| a320 | 40 glass objects per side over 40 openings | paint | artist glass differs from the drawing (40 vs 40 windows, 57% within 0.35 pitch, pitch 0.524 vs 0.531 m) | glass 80, holes 80 |
| a321 | 48 glass objects per side over 48 openings | paint | artist glass matches the a321 drawing (48 vs 48 windows, 98%) but has 1 window(s) the a21n drawing does not (at 26.03 m); the glass is shared by both types, so the drawings' rows are painted | glass 96, holes 96 |
| a333 | none | paint | artist windows are none | - |
| a359 | 56 glass objects per side over 56 openings | paint | artist glass differs from the drawing (56 vs 62 windows, 73% within 0.35 pitch, pitch 0.654 vs 0.638 m) | glass 112, holes 112 |
| a388 | none | paint | artist windows are none | - |
| b738 | 41 openings in the skin | paint | artist windows are holes | holes 83, strip 20 |
| b744 | none | paint | artist windows are none | - |
| b748 | 109 glass objects per side | keep | no usable manufacturer drawing: artist glass windows kept (unverified) | - |
| b752 | 52 glass objects per side over 42 openings | keep | artist glass matches the drawing (52 vs 54 windows, 96% within 0.35 pitch) | - |
| b763 | 46 glass objects per side over 46 openings | paint | artist glass differs from the drawing (46 vs 55 windows, 44% within 0.35 pitch, pitch 0.550 vs 0.562 m) | glass 92, holes 92 |
| b788 | 41 glass objects per side | paint | artist glass differs from the drawing (41 vs 47 windows, 47% within 0.35 pitch, pitch 0.750 vs 0.613 m) | glass 82 |
| bcs1 | 33 glass objects per side over 31 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) | - |
| bcs3 | 40 glass objects per side | keep | no usable manufacturer drawing: artist glass windows kept (unverified) | - |
| crj2 | 12 painted in the source texture | paint | artist windows are texture | painted texture windows dropped from the kept skin |
| crj7 | 20 glass objects per side over 20 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) | - |
| crj9 | 24 glass objects per side over 24 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) | - |
| e170 | 18 glass objects per side over 18 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) | - |
| e190 | 27 glass objects per side over 23 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) | - |
| e75l | 20 glass objects per side over 19 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) | - |
| md11 | 71 glass objects per side | keep | artist glass matches the drawing (71 vs 71 windows, 100% within 0.35 pitch) | - |

### 8.4 Fuselage plugs

- `tools/liveries/atlas.py` splits the mesh at each plug station (`js/aircraft/fit.js PLUG_AT`) so a 2 cm band straddles
  it; the band has its own charts as long as the longest plug of any type on the model: a 737-900 / 787-10 plug gets
  texels (and windows) instead of one stretched texel column. On models that keep their glass, the stations were moved
  into a window pier (757: 15.40 -> 15.24 m, 31.00 -> 30.96 m; E190: 9.00 -> 9.22 m, 23.50 -> 23.54 m) so no window is
  stretched; doors and the documented plug lengths are unchanged (`fit.js`).
- A negative plug now removes its section (`js/live/models.js plugShift`, Python `common.apply_stretch`,
  `fit.js rx`): vertices in the section collapse onto the station, the rest moves forward; no doubled skin.
- Every type is baked with its own window row: `tools/liveries/build.py` groups the types of a model by fuselage plugs
  AND window row (737-800 vs 737 MAX 8, A321 vs A321neo, A330-300 vs -900 differ on the drawings), and bakes the neutral
  skin of every type that differs from its model's own type as pseudo-brand `_N` (`data/liveries/_N/<model>@<type>`),
  worn by aircraft without a brand bake (`js/aircraft/liveries.js neutralTextureFor`, brand colours by zone).

### 8.5 Freighters

`FDX` and `UPS` are flagged `cargo` (`tools/liveries/liveries.py`, manifest `brands.<CODE>.cargo`): no painted windows,
and the kept artist glass of their models (MD-11, 757-200, 747-8) is shaded as painted-over window plugs in the top
colour (`js/shaders/aircraft_real.js uNoCabin`; the three.js owner is asked in `docs/requests/liveries_windows.md`).
Their 747F upper-deck crew windows are not modelled.

### 8.6 Verification

- **Every type with an imported model** (42 types on 21 models): `tools/liveries/window_sheet.py` renders the model
  stretched as the app renders the type, wearing the texture the app gives it (the brand bake or the neutral `_N` skin
  of the type), orthographic from port, with the manufacturer's window stations of the type drawn as ticks above and
  below the body (`out/liveries/windows/<model>@<type>.png`, not committed). Checked by eye on all 42 sheets: one row
  per deck, every painted window between its pair of ticks, door and over-wing-exit gaps where the drawings have them
  (737-800: 45; 737-700 inferred: 35; 737 MAX 8 / 9 / 10: 42 / 45 / 48; A319 / A320 / A321 (neo): 32 (31) / 40 (39) / 48
  (46); A330-200 / -300 / -800 / -900: 57 / 69 / 56 / 67; A350-900 / -1000: 60 / 72; A380: 47 upper, 62 main; 747-400:
  85 main, 21 upper; 757-200 / -300: 54 / 64; 767-200 / -300 / -400: 45 / 53 / 64; 787-8 / -9 / -10: 45 / 56 / 64; CRJ200:
  12; MD-11: 71). Models that keep their artist glass (E-Jets, CRJ700 / 900, A220, 747-8) show one row (two decks on the
  747-8).
- **Close-up renders** (Blender Cycles, §5): `out/liveries/UAL.png` (737-800) and `out/liveries/SWA.png` (737-700 on the
  737-800 model with negative plugs) are the renders the owner flagged; both show one row. The other brand renders of
  §5 were checked for the same.
- **Geometry checks** (Python, on the atlased models): no open skin edges created by the window removal on any model;
  the flight-deck glazing of every model unchanged (the E175 hole of the first pass restored).

### 8.7 Open items

- Artist glass kept unverified on the E-Jets, CRJ700 / 900, A220-100 / -300 and 747-8 (no usable drawing: their APM /
  APP drawings lack published door stations for a calibration, the 747-8 DWG converts to an incomplete DXF). The E175
  glass pane at 3.06 m that the first pass took for a stray cabin window is the aft flight-deck side window and is kept
  (the artist count of 20 per side includes it).
- 737-600 / -700 rows are the 737-800 row with the plugs of `fit.js` (inferred: the fitted forward plug is the published
  wheelbase difference, 3.00 m; real 737 plugs are not documented here); 737-900 uses the 737-9 drawing (same fuselage).
- The A319 heights are taken from the A320 drawings (the A319 sheets are drawn smaller; same fuselage section).
- The 747-400 drawing (1998) draws main-deck windows from 1.34 m aft of the nose tip; kept as drawn.
- Window sizes come from the drawings (outline at mid-stroke); the small-scale Airbus sheets (A330) draw the windows
  as tall ovals (0.25 x 0.45 m).


## 9. Review round 1 (26 Sep 2026): findings, fixes, rejections

Adversarial reviewers checked the bakes, the renders and the fitted models (30 findings). What changed:

### 9.1 Cabin windows (the owner's double-row feedback)

Re-verified after the fixes of §8: one row per deck on every bake (the reviewer found no duplicate row on 12 variants and
the 747). Blender renders of `UAL` (737-800) and `SWA` (737-700) after the full re-bake: one row (`out/liveries/UAL.png`,
`SWA.png`). The renderer adds no procedural windows to imported models (§8.1). Two remaining items:
- **737-600 / -700 exits**: D6-58325-7 Rev C §2.4.2 (interior arrangements, p.2-22) draws one overwing exit per side on
  the 737-700 (§2.4.4: two on the -800). The 737-800 skin detail kept both hatch outlines in the plug-shortened gap; the
  aft one is now removed on the b736 / b737 bakes (`paint.py _one_overwing_exit`).
- **E195** row: still the E190 artist glass stretched (no calibrated drawing: the APMs in `refs/cache/acap` lack door
  stations for a scale; open).

### 9.2 Liveries re-drawn (positions measured on the reference photos, `refs/cache/livref`, stations as fractions of L)

| Brand | Finding | Change |
|---|---|---|
| United Express | title too big, centred on the windows | lock-up 0.21-0.55 L, cap 0.25 H, feet on the window tops (photo N86371) |
| Japan Airlines | tail symbol not the Tsurumaru; "stray red dot" | Tsurumaru re-drawn as vector (red disc, crane ring with feather slits, head and beak, white JAL); the "dot" is the Hinomaru flag after the title on the photo (JA864J), now drawn as a flag with its keyline — **finding partly rejected** |
| Qatar | tail inverted, no Arabic title, no nacelle oryx | grey fin with the burgundy oryx (polygons measured on A7-AMI's fin), القطرية in Noto Kufi Arabic (shaped with libraqm) sn 0.38-0.47 above the windows, oryx on the nacelles; QATAR sn 0.12-0.33, 0.40 H |
| UPS | empty shield, wrong body | white forward/lower body, brown aft body behind a gold sweep (crown sn 0.48 → keel sn 0.78), shield with gold border, gold bow and gold "ups" on the brown fin. The reviewer's "filled gold shield" is **not** what the photo (N627UP) shows: the shield face is brown |
| Air France | tail stripes missing | stripes parallel to the leading edge over the whole fin (navy 0.12-0.40, 0.47-0.55, 0.60-0.64, 0.67-0.69, red 0.76-0.97 to 0.72 height), red slash after AIRFRANCE in reading order, title sn 0.135-0.385 |
| Fiji | wrong title and tail | outline FIJI 0.6 H across the windows from door 1 with AIRWAYS below; brown fin, masi medallion, black masi bands at the tip and forward root |
| Virgin | signature small, titles grey, no nose icon | signature 0.25 fin height rising aft with its underline; titles #2E2A48 (dark purple, measured); flying icon (figure + Union flag, strongly simplified) and type name on the nose |
| Volaris | title on the door, black, small cross | title from the door-1 aft edge + 0.55 m to 0.462 L in navy #1A1438; volaris.com sn 0.645; the pixel cross 5 × 5 cells of 0.135 fin height low and forward (13 cells, colours sampled on the photo) |
| China Southern, Emirates, Qatar | non-Latin titles missing | 中国南方航空 (Noto Sans SC) forward of CHINA SOUTHERN, reading from the nose on both sides as photographed (right-to-left on the starboard side); الإمارات (Aref Ruqaa) aft of Emirates; Qatar above. **China Airlines: rejected** — both photos (B-18906, B-18918, port side) show only CHINA AIRLINES; its title was moved to sn 0.305-0.46 as photographed, with the small red mark |
| Lufthansa 747 | blotches on the nose | not texture (the atlas texels there are uniform white): the FAM 747-8 source has 1,897 exact duplicate triangles (double-sided copies) whose opposite normals shade as blotches in Cycles. The nose vertex normals are smoothed (`common.NORMAL_SMOOTH`, b744 / b748), degenerate normals repaired at load (`js/live/models.js repairNormals`). Dropping one twin (tried in the atlas, at load and in the check render) exposed unpainted twins on body panels, so the twins stay (the app's shader turns every normal to the camera; no Cycles artefact). **Open**: the Blender check render still shows faint nose smudges; the app view of a 747-8 was not captured (none in the snapshot) |
| Avianca | orange stripe | removed; the photo's coral-orange is a small wedge at the fin root (#FD653C, sampled) |
| EVA | title too dark, green tips | title #249243 (sampled), 787 raked tips unpainted |

### 9.3 Registration on every aircraft

The registration is painted per aircraft at run time (`js/live/models.js registrationTexture` → `js/shaders/aircraft_real.js
uReg*`, placed by `js/live/aircraft.js regUniforms`): two layouts in one texture (the flag stays at its end of the aircraft
on both sides, mirrored so its canton leads), letters inked dark or white by the paint under them. Placement per brand
(`tools/liveries/liveries.py REG`, manifest `brands.<code>.reg`) measured on the photos for United (US flag aft), United
Express, American (flag ahead, below the windows), Delta, Southwest, Volaris (Mexican flag), JAL, Qatar, Virgin, Air France
and UPS; every other brand (and unknown operators) uses the default (inf): 0.74 L, 0.18 H above the window line. The design
frame of each bake (length, cabin height, window line in model units) is recorded by `build.py` (`manifest.frames`).
Registration source: the feed's `r`, else the US N-number decoded from the ICAO address; non-US aircraft need
`js/live/traffic.js` to pass `tr.info.reg` (`docs/requests/aircraft_models_777.md`; read through the debug hook meanwhile).

### 9.4 777 family: artist models

FlightGear 777-200ER and 777-300ER (FGMEMBERS/777 @371a354; GPL-2.0 per the FGAddon `LICENSE`, `docs/ATTRIBUTION_models.md`)
converted as `b772` / `b77w` (the old JAL / BA paint of their default textures erased before neutralising), atlased
(windows painted from the Boeing 3-view rows), oleos compressed to the published fuselage top. B772 / B773 on `b772`
(plain tip; the TYPES table wrongly gave the -200 a raked tip: fixed), B77L / B77W / B779 on `b77w`; 777-300 / -200LR plugs
from the main-gear change (5.34 m ahead of the wing). Bakes: United (B772, B77W), Cathay, EVA, JAL, ANA, BA, Air India,
Air France, Korean, Air Canada, Swiss (cross added), China Eastern, Air China, Philippine. Limitation: the -200LR / 777F on
the -300ER model keep the -300's overwing door outline in the skin detail.

### 9.5 Geometry and docking (js/aircraft/fit.js, tools/models/check_dims.py)

- A330 family: engines 0.12 m → 0.74 m (N1 0.69-0.79), belly 1.68 (BF1 1.85), wing tip 7.65 (W1 7.61-7.70), tailplane
  7.98 (HT 7.88-8.09; AC A330 FIGURE-2-3-0-991-001-A01, read in the PDF): vertical compression below the centre line and a
  wing / tailplane dihedral shear. Same mechanism for 787-9 (0.44 → 0.70), 747-8 (0.31 → 0.84), A220-300 (engine 0.55 after
  the crown fix: the 5 m median filter ignores the dorsal hump).
- Procedural struts of gear-less models reach 0.15 m into the model's skin (`features.under`).
- 737: the FG model's door objects are read (doorLF 5.25 m); the bridge meets the drawn door (cab floor 3.12 m; the artist
  drew the sill 0.38 m above the published 2.59-2.74 m: recorded, not hidden).
- 757: plain wing fitted to the ACAP span up to the winglet root; the winglets add their own extent (39.17 m overall).
- A320neo family: procedural sharklets (2.4 m) at the model's tip; 737 MAX: the NG winglet folded away, AT split tip,
  nacelles scaled to the LEAP-1B fan (69.4 / 61 in). MAX tail cone and nacelle chevrons are not modelled (open).
- Freighters by operator / type / database description (`lookup.js isFreighter`): no cabin windows; one bridge only
  (`gates.js` `opts.freighter`, request filed). 747-400F short upper deck: not modelled (open).
- Business jets: HondaJet unmapped (over-wing engines); generic airframe without a cabin row. E295: still a marker (no
  primary dimensions).
- 777 procedural glazing compressed to end 0.8 m ahead of door 1; raked-tip nav lights on the tip loft.
- `check_dims`: engine / belly / wing-tip / tailplane clearances, rendered door sill vs cab floor, self-check marking,
  the renderer's stretch (common.apply_stretch). Result: 24 flagged, all explained, 0 unexplained.

### 9.6 Verification

- Full re-bake: 135 entries, 183 textures (hi 14.1 MB, mid 7.2 MB, lo 3.7 MB); snapshot `lo` set 22 files, 0.52 MB.
- Blender renders (`out/liveries/*.png`) of UAL, SWA (one window row each), UAL-X, JAL, QTR, UPS, AFR, FJI, VIR, VOI, CSN, UAE,
  DLH, AVA, EVA, CAL and UAL on the 777-200ER (`UAL_b772.png`); software previews of each new design.
- App (headless, SOFTGL, snapshot): United 777-200ER N796UA with its brand bake and registration; United 737 MAX 8 N37371
  starboard with the US flag aft of the registration (as photographed), NG winglet folded, split tip drawn; JetBlue
  A321neo with sharklets (`out/live/idr_*.png`, `idr2_*.png`).
