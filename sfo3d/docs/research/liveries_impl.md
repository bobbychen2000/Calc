# Brand liveries: implementation, verification and status (24 Sep 2026; cabin windows 25 Sep 2026, §8)

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
1 Air Canada, 1 Delta, 1 Cathay) use the procedural airframe with the brand's runtime colours.

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
  openings in the skin closed with skin triangles, window reveals inside the openings deleted, painted source windows
  and window frames dropped from the kept skin detail in the window band) and the manufacturer's row painted; 10 keep
  their artist glass.
- **Plug bands** (§8.4): the mesh is split at the fuselage-plug stations of `js/aircraft/fit.js`; the 2 cm band gets its
  own charts, as long as the longest plug of any type on the model, so stretched types have texels for the plug.

| Model | px/m at 2048 | Fuselage cm/px (2048 / 1024) | Charts | Engines found | Cabin windows (§8) | Plug bands (m, model; longest plug) |
|---|---|---|---|---|---|---|
| a319 (Airbus A319) | 35.4 | 2.8 / 5.7 | 100 | 2 | painted (33 glass + openings removed) | - |
| a320 (Airbus A320) | 35.3 | 2.8 / 5.7 | 99 | 2 | painted (40 glass + openings removed) | - |
| a321 (Airbus A321) | 32.6 | 3.1 / 6.1 | 97 | 2 | artist glass (matches; 2 extra removed) | - |
| a333 (Airbus A330-300) | 20.0 | 5.0 / 10.0 | 108 | 2 | painted (source has none) | - (only negative plugs) |
| a359 (Airbus A350-900) | 19.2 | 5.2 / 10.4 | 110 | 2 | painted (56 glass + openings + reveals removed) | 12.84 (4.45), 45.35 (2.56) |
| a388 (Airbus A380-800) | 15.3 | 6.5 / 13.1 | 102 | 4 | painted, two decks (source has none) | - |
| b738 (Boeing 737-800) | 35.6 | 2.8 / 5.6 | 84 | 2 | painted (41 openings closed, dark strip removed) | 9.99 (2.74), 25.97 (1.58) |
| b744 (Boeing 747-400) | 20.1 | 5.0 / 10.0 | 104 | 4 | painted, two decks (source windows in the texture dropped) | - |
| b748 (Boeing 747-8) | 14.0 | 7.2 / 14.3 | 89 | 4 | artist glass (no usable drawing) | - |
| b752 (Boeing 757-200) | 31.7 | 3.2 / 6.3 | 93 | 2 | artist glass (matches) + missing windows painted | 14.93 (3.98), 30.32 (2.99) |
| b763 (Boeing 767-300) | 25.9 | 3.9 / 7.7 | 73 | 2 | painted (46 glass + openings removed) | 10.85 (3.47), 37.18 (2.99) |
| b788 (Boeing 787-8) | 22.7 | 4.4 / 8.8 | 122 | 2 | painted (41 glass removed) | 10.79 (6.09), 37.98 (5.49) |
| bcs1 (Airbus A220-100) | 39.0 | 2.6 / 5.1 | 83 | 2 | artist glass (no usable drawing) | - |
| bcs3 (Airbus A220-300) | 39.1 | 2.6 / 5.1 | 60 | 2 | artist glass (no usable drawing) | - |
| crj2 (Bombardier CRJ200) | 54.1 | 1.8 / 3.7 | 71 | 2 | painted (source windows and ghost titles in the texture dropped) | - |
| crj7 (Bombardier CRJ700) | 56.9 | 1.8 / 3.5 | 66 | 2 | artist glass (no usable drawing) | - |
| crj9 (Bombardier CRJ900) | 56.2 | 1.8 / 3.6 | 66 | 2 | artist glass (no usable drawing) | - |
| e170 (Embraer E170) | 43.7 | 2.3 / 4.6 | 99 | 2 | artist glass (no usable drawing) | - |
| e190 (Embraer E190) | 38.0 | 2.6 / 5.3 | 106 | 2 | artist glass (no usable drawing) | 9.11 (0.80), 23.27 (1.58) |
| e75l (Embraer E175) | 41.4 | 2.4 / 4.8 | 74 | 2 (components) | artist glass (no usable drawing) | - |
| md11 (McDonnell Douglas MD-11) | 17.2 | 5.8 / 11.6 | 97 | 2 (components) | artist glass (matches: 71 / 71) | - |

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

## 4. Output, sizes and runtime

- `data/liveries/<BRAND>/<model>[@<type>]-{hi,mid,lo}.webp`: 2048 / 1024 / 512 px (area-averaged downscale), WebP
  RGBA (quality 88 / 84 / 80).
- `data/liveries/manifest.json` and `manifest.js` (`LIVERY_MANIFEST`): entries `{brand, model, pxm, types, files, file,
  painted_as, bytes, variants[]}` (`pxm`: the model's atlas px per metre at 2048) and `brands{name, livery, since, refs, colors, status, types}`.
- Totals: 61 designs (57 with bakes; Air India, Swiss, China Eastern, Air China fly only 777s at SFO), 107 brand × model entries, 130 textures (incl. plug variants); hi 9.8 MB, mid 5.0 MB, lo 2.6 MB (WebP, 20-110 KB per hi texture).
- **Runtime (legacy renderer, this workflow's files):** `js/aircraft/liveries.js liveryTextureFor(brand, model, type,
  res)` picks the entry / variant; resolution `window.SFO_LIVERY_RES`, else `hi` for `?quality=ultra`, else `auto`
  (`mid`, or `hi` where the atlas is coarse at mid, `pxm / 2 < 11` px/m: A330, A350, A380, 747, MD-11);
  base URL `window.SFO_LIVERY_BASE` (default `data/liveries/`). `js/live/models.js getLiveryTexture` loads on demand
  and caches per URL (only the brands in view are fetched). `js/live/aircraft.js` resolves `ac.liv` per aircraft
  (brand from the ICAO address when the track has no registration) and binds the texture to the atlas draw
  (`uLivTex = 1`). `js/shaders/aircraft_real.js`: atlas alpha < 0.5 = window glass (dark, reflective, warm cabin light
  at night), clear coat on paint only. Without a brand texture the neutral atlas is recoloured by the brand's runtime
  colour family (777 family: procedural airframe, runtime colours only).
- **Artifact (16 MB):** ship only the `lo` files the snapshot needs (`build.py --list-snapshot`: 18 files, 0.42 MB) with
  `window.SFO_LIVERY_RES = 'lo'`. Requests to the owners of `traffic.js`, `js/three/aircraft.js`, `about.js`, `ui.js`
  and packaging: `docs/requests/liveries_brand.md`.

## 5. Render check

One Blender Cycles close-up per brand (`tools/liveries/render_blender.py`: the brand's most frequent SFO type with a
bake, `hi` texture, three-quarter front view from port, sun + sky, 24 samples, denoised) in `out/liveries/<CODE>.png`
(not committed), compared by eye with the official references listed per brand.

{{RENDERS}}

## 6. Per-brand status

`colours`: count of design colours by provenance: `official` (brand guide / official swatch on the airline's own
host), `measured` (sampled on an official press image, URL in the refs), `third-party` (profile chart or copied brand
guide on a third-party host: unverified), `approx` (from the reference description / general knowledge: unverified).
`refs`: hosts of the references (full URLs in `data/liveries/manifest.json`).

| Code | Brand | Livery | Baked textures | Colours | Refs | Status / known simplifications |
|---|---|---|---|---|---|---|
| UAL | United Airlines | 2019 "blue" livery (Rhapsody Blue swoop, Runway Gray belly, globe tail) | a319, a320, a321, b738, b738@b39m, b752, b752@b753, b763, b763@b764, b788, b788@b789, b788@b78x | official 4, approx 1 | mma.prnewswire.com; united.mediaroom.com | layout measured on the official United livery graphic (737-800); other types scaled by fuselage length |
| UAL-X | United Express | 2019 livery with UNITED EXPRESS titles | crj2, crj7, e170, e75l | official 4, approx 1 | mma.prnewswire.com; note: layout of the EXPRESS title: approx; united.mediaroom.com | 2019 design on regional jets (United release: applied to regional aircraft); EXPRESS title placement approx |
| UAL-G | United Airlines (2010-2019 "Globe" livery) | post-merger livery: white top, grey belly, gold/blue cheatline, gold globe on a blue tail | a319, a320, b738, b738@b39m | approx 3 | FlightGear texture (GPL-2.0); norebbo.com | legacy variant (still on part of the fleet; no per-tail list, liveries.md §3.1): used only by per-registration override |
| DAL | Delta Air Lines | 2007 "Onward and Upward" livery (white DELTA on the belly since 2015) | a319, a320, a321, a333, a333@a332, b738, b738@b39m, b752, b752@b753, b763, b763@b764, bcs1, bcs3 | official 2, third-party 2, approx 1 | deltamuseum.org; news.delta.com; norebbo.com; waatbp.oneclub.org | layout from official photos + profile reference; belly title not drawn |
| DAL-C | Delta Connection | Delta livery with DELTA CONNECTION titles | e75l | official 2, approx 3 | deltamuseum.org; news.delta.com; norebbo.com; waatbp.oneclub.org | layout from the ERJ-175 profile reference |
| AAL | American Airlines | 2013 livery, 2021 Silver Eagle paint | a319, a320, a321, b738, b788, b788@b789 | measured 2, approx 2, third-party 1 | news.aa.com; norebbo.com; simpleflying.com | layout from the official 2013 photo + profile reference; flight symbol simplified |
| AAL-E | American Eagle | American 2013 livery with American Eagle titles | e75l | measured 1 | news.aa.com; norebbo.com; simpleflying.com | layout from the ERJ-175 profile reference |
| ASA | Alaska Airlines | 2016 brand refresh (tail portrait, aurora sweep), also on Horizon / SkyWest E175s | a321, b738, b738@b39m, b738@b737, e75l | measured 4, approx 1 | FlightGear texture (GPL-2.0); news.alaskaair.com | layout from the official render; portrait strongly simplified (re-drawn) |
| SWA | Southwest Airlines | 2014 "Heart" livery | b738, b738@b737 | third-party 2, approx 2 | dallasnews.com; investors.southwest.com; norebbo.com | layout from the profile reference; heart on the belly not drawn |
| JBU | JetBlue | 2023 livery refresh (blue allover, tail pattern extended onto the body) | a320, a321, bcs3 | measured 4, approx 1 | news.jetblue.com; s202.q4cdn.com | the Mint tile pattern of the official photo on every airframe (patterns vary by aircraft: inf); fleet mid-transition from the white livery (inf: new livery rendered) |
| FFT | Frontier Airlines | 2014-15 livery: green FRONTIER title, animal on a green tail | a320, a321 | measured 3, approx 1 | news.flyfrontier.com; simpleflying.com | per-aircraft animal not modelled (a generic stylised animal on every tail) |
| ACA | Air Canada | 2017 livery (black tail, belly and engines; red maple-leaf rondelle) | a320, a321, b738, b788@b789, bcs3 | official 2, approx 1 | aircanada.com; cbc.ca; norebbo.com | layout from the CBC description and the profile reference |
| ACA-X | Air Canada Express | 2017 livery with AIR CANADA EXPRESS titles | crj9 | official 2 | aircanada.com; cbc.ca; norebbo.com | title placement approx |
| WJA | WestJet | 2018 livery (teal tail with the stylised maple leaf, teal down onto the rear fuselage) | b738, b738@b737, b788@b789 | approx 5 | thedesignair.net; travelweek.ca; westjet.mediaroom.com | layout from the descriptions and the official logo; colours approx (no official values found) |
| AMX | Aeroméxico | Caballero Águila livery (navy tail; the 2024 updated eagle is being applied gradually) | b738, b738@b39m, b788@b789 | approx 4 | breitflyte.com; norebbo.com | eagle-knight head strongly simplified; colours approx |
| HAL | Hawaiian Airlines | 2017 livery (Pualani on a purple sunrise tail, lei flowers on the aft body) | a321, a333@a332 | approx 6 | news.alaskaair.com; norebbo.com | Pualani and the lei strongly simplified |
| SCX | Sun Country Airlines | 2018 livery (blue base, orange stripes, retained sun logo) | b738 | approx 4 | startribune.com | from the text description only (no reference image fetched): approx |
| MXY | Breeze Airways | 2021 livery (blue fuselage, navy tail with the light-blue check) | bcs3 | third-party 4 | airbus.com; norebbo.com | layout from the profile reference |
| CPA | Cathay Pacific | 2015 livery (all-green tail with white brushwing, light grey band, name above the windows) | a359 | approx 2 | news.cathaypacific.com; norebbo.com | brushwing simplified |
| EVA | EVA Air | 2015 update (green tail with the orange globe, darker green belly) | b788@b789 | approx 2 | airlinereporter.com | from the description; globe simplified |
| CAL | China Airlines | plum-blossom tail (1995 identity), white fuselage | a359 | approx 3 | china-airlines.com | from knowledge only: approx |
| SIA | Singapore Airlines | midnight-blue tail with the gold Kris bird, blue and gold cheatline | a359 | approx 2 | airlinegeeks.com | Kris bird simplified |
| KAL | Korean Air | new identity 11 Mar 2025: metallic sky blue, KOREAN logotype, dark-blue taegeuk | b788@b789, b788@b78x | third-party 2 | norebbo.com; samchui.com | fleet mid-transition from the 1984 livery (new livery rendered: inf) |
| ANA | ANA | "Triton Blue" livery (1982) | b788, b788@b789 | third-party 2 | ana.co.jp; norebbo.com | at SFO ANA flies the 777-300ER (procedural airframe; runtime colours) |
| JAL | Japan Airlines | 2011 "Tsurumaru" crane livery | b788, b788@b789 | approx 1 | japantimes.co.jp; norebbo.com | crane circle simplified |
| QFA | Qantas | 2016 livery (red tail with the streamlined kangaroo, red wrapping onto the aft body) | b788@b789 | approx 1 | norebbo.com | kangaroo simplified |
| PAL | Philippine Airlines | flag-motif tail (blue and red triangles, yellow sun) | a359 | approx 3 | philippineairlines.com | approx; at SFO mostly the 777-300ER (procedural) |
| AFR | Air France | Eurowhite livery with the tricolour tail stripes | a359 | approx 2 | corporate.airfrance.com | approx |
| BAW | British Airways | Chatham Dockyard Union-flag tail, midnight-blue belly, red speedwing | a388 | approx 2 | key.aero; norebbo.com; simpleflying.com | flag simplified |
| DLH | Lufthansa | 2018 brand design (dark-blue tail wrapping onto the aft fuselage, white crane in a ring) | a359, a388, b744, b748 | third-party 1 | dezeen.com; lufthansagroup.com | fleet mid-transition (some 747-400 keep the old colours; new design rendered: inf) |
| UAE | Emirates | 2023 livery (waving UAE-flag tail, gold titles) | a388 | third-party 2, approx 1 | norebbo.com | Arabic title not drawn |
| THY | Turkish Airlines | red tail with the goose in a white circle, grey tulip stripe | a359, b788@b789 | approx 1 | turkishairlines.com | goose simplified |
| VIR | Virgin Atlantic | 2019 "Flying Icons" livery (metallic silver fuselage, red tail, purple titles) | a359@a35k, b788@b789 | approx 3 | virgin.com | flying icon figures not drawn |
| AIC | Air India | 2023 livery (deep red, aubergine and gold; window-frame motif) | - (procedural airframe only) | approx 3 | airindia.com | SFO fleet is 777 only (procedural airframe: runtime colours); fleet mid-transition |
| ANZ | Air New Zealand | black tail with the white koru, black fern on the aft fuselage | b788@b789 | approx 1 | norebbo.com | fern simplified to a black aft sweep |
| AVA | Avianca | 2023 brand (lowercase avianca, brighter red; red tail and nacelles) | a320 | approx 1 | airlinegeeks.com; avianca.com | fleet mid-transition (2023 brand rendered: inf) |
| VOI | Volaris | white fuselage with purple / teal tail and titles | a320, a321 | approx 2 | volaris.com | approx |
| CMP | Copa Airlines | dark-blue tail with the gold Copa symbol | b738@b39m | approx 2 | copaair.com | approx |
| KLM | KLM | sky-blue upper fuselage, white belly, KLM crown on the tail | b788@b789, b788@b78x | approx 2 | news.klm.com | approx |
| SWR | Swiss | red tail with the white Swiss cross | - (procedural airframe only) | approx 1 | swiss.com | 777-300ER only at SFO (procedural) |
| AAR | Asiana Airlines | grey / white fuselage, striped tail (yellow, red, blue, grey) | a359 | approx 4 | flyasiana.com | approx |
| SJX | Starlux Airlines | white fuselage, gold / dark titles and tail | a359 | approx 2 | starlux-airlines.com | from knowledge only: approx |
| TZP | ZIPAIR | white fuselage with grey / green ZIPAIR titles and tail | b788 | approx 2 | zipair.net | from knowledge only: approx |
| EIN | Aer Lingus | 2019 livery (teal tail with the white shamrock) | a333, a333@a332 | approx 2 | aerlingus.com | approx |
| QTR | Qatar Airways | grey fuselage, burgundy oryx on the tail | a359 | third-party 2 | norebbo.com | oryx simplified; Arabic script not drawn |
| FBU | French bee | white / blue gradient fuselage, blue tail | a359 | approx 1 | frenchbee.com | from knowledge only: approx |
| SAS | SAS | 2019 livery (silver-blue fuselage, dark-blue tail with SAS) | a333, a359 | approx 2 | sasgroup.net | approx |
| TAP | TAP Air Portugal | 2017 livery (white; green and red on the tail) | a333 | approx 2 | flytap.com | approx |
| APZ | Air Premia | white fuselage, dark navy tail | b788@b789 | approx 1 | airpremia.com | from knowledge only: approx |
| FLE | Flair Airlines | white fuselage, purple tail and titles | b738 | approx 2 | flyflair.com | from knowledge only: approx |
| ITY | ITA Airways | 2021 livery (blue Savoia fuselage, white titles, tricolour tail) | a333, a359 | approx 1 | ita-airways.com | approx |
| CSN | China Southern | blue tail with the red kapok flower | b788@b789 | approx 2 | csair.com | approx |
| CES | China Eastern | swallow logo on the tail (red / blue) | - (procedural airframe only) | approx 1 | ceair.com | 777 only at SFO (procedural) |
| CCA | Air China | red phoenix on a white tail | - (procedural airframe only) | approx 1 | airchina.com | 777 only at SFO (procedural) |
| HVN | Vietnam Airlines | teal tail with the golden lotus | a359 | approx 2 | vietnamairlines.com | approx |
| FJI | Fiji Airways | masi (tapa) pattern tail | a333, a333@a332, a359 | approx 2 | fijiairways.com | pattern simplified |
| CFG | Condor | 2022 striped livery (each aircraft one colour; red "Passion" rendered) | a333 | approx 1 | condor.com | colour varies per aircraft (inf: red) |
| IBE | Iberia | 2013 livery (red and yellow IB symbol on the tail) | a333@a332 | approx 2 | iberia.com | approx |
| LOT | LOT Polish Airlines | dark-blue tail with the crane in a circle | b788, b788@b789 | approx 1 | lot.com | approx |
| FDX | FedEx | FedEx Express livery (purple crown and tail, white lower fuselage, grey belly) | b752, b763, md11 | approx 2 | newsroom.fedex.com | approx |
| UPS | UPS | brown tail and belly, gold shield, white upper fuselage | b744, b748, b752, b763, md11 | approx 2 | norebbo.com | approx |

## 7. Known deviations and open items

- **Colours of most international brands are `approx`** (no official paint values fetched; airline image hosts and
  Airbus media are behind bot protection from this sandbox). Official values exist only for United (livery graphic
  swatches), Delta (Blue / Red, official palette image) and Air Canada (logo guideline). Measured on official images:
  American, Alaska, JetBlue, Frontier. Owner: supply brand guides or allow measuring on photos we can fetch.
- **Layouts** measured on an official side-view graphic only for United (737-800) and on official photos for American,
  Alaska, JetBlue; the rest follow the reference descriptions / profile drawings (reference only) and are simplified.
  Sun Country, China Airlines, Starlux, ZIPAIR, French bee, Air Premia, Flair are from descriptions only.
- **Per-aircraft art is not modelled**: Frontier animals (one generic stylised animal), JetBlue tail patterns (the
  official Mint photo's pattern on all), Condor colours (red rendered), special liveries (overrides rendered standard).
- **Fleet transitions rendered as the new livery** (`inf`): United 2019 vs Globe (no per-tail list; `UAL-G` exists
  for overrides only), Korean 2025, Lufthansa 2018, Avianca 2023, Air India 2023 (777 only at SFO), Aeroméxico 2024
  eagle, JetBlue 2023.
- **No model**: 777 family (procedural airframe, runtime colours), Porter E195-E2. **MD-11 tail engine** is painted with the fin (the type table has no centre engine).
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
- Found while fixing: the A350's artist windows are glass objects over openings plus window reveals (1,861 small
  textured triangles) and frames drawn in its texture: removing the glass alone left a grey second row.
- Negative fuselage plugs (737-700 on the 737-800 model, 767-200, A330-200 / -800) slid the aft body over the forward
  body (`js/live/models.js` applyStretch): 3 m of doubled skin and doubled windows on the 737-700 (the SWA render).
- The renderer adds no windows to the imported models (`js/shaders/aircraft_real.js` draws the kind-1 glass and the
  atlas-alpha glass only); procedural windows exist only on the procedural airframe (777 family, and every aircraft
  beyond the model LOD distance), one row from `TYPES.win`.

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

| Model | Artist windows | Decision | Reason |
|---|---|---|---|
| a319 | 33 glass objects per side over 33 openings | paint | artist glass differs from the drawing (33 vs 32 windows, 53% within 0.35 pitch, pitch 0.533 vs 0.526 m) |
| a320 | 40 glass objects per side over 40 openings | paint | artist glass differs from the drawing (40 vs 40 windows, 57% within 0.35 pitch, pitch 0.524 vs 0.531 m) |
| a321 | 48 glass objects per side over 48 openings | keep | artist glass matches the drawing (48 vs 48 windows, 98% within 0.35 pitch) |
| a333 | none | paint | artist windows are none |
| a359 | 56 glass objects per side over 56 openings | paint | artist glass differs from the drawing (56 vs 62 windows, 73% within 0.35 pitch, pitch 0.654 vs 0.638 m) |
| a388 | none | paint | artist windows are none |
| b738 | 41 openings in the skin + dark strip | paint | artist windows are holes |
| b744 | none | paint | artist windows are none |
| b748 | 109 glass objects per side | keep | no usable manufacturer drawing: artist glass windows kept (unverified) |
| b752 | 52 glass objects per side over 42 openings | keep | artist glass matches the drawing (52 vs 54 windows, 96% within 0.35 pitch) |
| b763 | 46 glass objects per side over 46 openings | paint | artist glass differs from the drawing (46 vs 55 windows, 44% within 0.35 pitch, pitch 0.550 vs 0.562 m) |
| b788 | 41 glass objects per side | paint | artist glass differs from the drawing (41 vs 47 windows, 47% within 0.35 pitch, pitch 0.750 vs 0.613 m) |
| bcs1 | 33 glass objects per side over 31 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) |
| bcs3 | 40 glass objects per side | keep | no usable manufacturer drawing: artist glass windows kept (unverified) |
| crj2 | 12 painted in the source texture | paint | artist windows are texture |
| crj7 | 20 glass objects per side over 20 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) |
| crj9 | 24 glass objects per side over 24 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) |
| e170 | 18 glass objects per side over 18 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) |
| e190 | 27 glass objects per side over 23 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) |
| e75l | 20 glass objects per side over 19 openings | keep | no usable manufacturer drawing: artist glass windows kept (unverified) |
| md11 | 71 glass objects per side | keep | artist glass matches the drawing (71 vs 71 windows, 100% within 0.35 pitch) |

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

{{WINDOW_RENDERS}}

### 8.7 Open items

- Artist glass kept unverified on the E-Jets, CRJ700 / 900, A220-100 / -300 and 747-8 (no usable drawing: their APM /
  APP drawings lack published door stations for a calibration, the 747-8 DWG converts to an incomplete DXF). The E175
  model's stray glass window at 3.1 m (3.7 m ahead of the row, in front of door 1 at 5.14 m; the E170 model with the
  same nose has none) was removed.
- 737-600 / -700 rows are the 737-800 row with the plugs of `fit.js` (inferred: the fitted forward plug is the published
  wheelbase difference, 3.00 m; real 737 plugs are not documented here); 737-900 uses the 737-9 drawing (same fuselage).
- The A319 heights are taken from the A320 drawings (the A319 sheets are drawn smaller; same fuselage section).
- The 747-400 drawing (1998) draws main-deck windows from 1.34 m aft of the nose tip; kept as drawn.
- Window sizes come from the drawings (outline at mid-stroke); the small-scale Airbus sheets (A330) draw the windows
  as tall ovals (0.25 x 0.45 m).

