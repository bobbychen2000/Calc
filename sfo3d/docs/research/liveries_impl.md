# Brand liveries: implementation, verification and status (24 Sep 2026)

Implements the owner's decisions on `docs/research/liveries.md` §7: real airline liveries, re-drawn as vector art for a
non-commercial depiction (About notice: trademarks belong to their owners); FlightGear GPL textures only where the
livery is current and the UV layout fits; everything else baked by our own painter. Colours come from official brand
documents where we could fetch them, otherwise measured on official press images (URL recorded), otherwise marked
`approx`. Every design records its references (`tools/liveries/liveries.py`, copied into
`data/liveries/manifest.json` `brands.<CODE>` and `data/brands.js` `BRAND_INFO`).

Pipeline (all offline, Python + numpy; no reference image or font file is committed):

```bash
FAM_DIR=refs/cache/src/fam3d python3 tools/convert_models.py [keys]   # only when a model changes (keeps UVs sane, see §3.4)
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
- **Alpha**: 1 paint, 0.75 unchanged dark skin, **< 0.5 cabin-window glass**. The 737-800, 747-400, A330-300, A380 and
  CRJ200 sources have no window geometry: their window rows are painted into the atlas from the type's window table
  (`js/aircraft/types.js` `win`).

| Model | px/m at 2048 | Fuselage cm/px (2048 / 1024) | Charts | Engines found | Windows painted |
|---|---|---|---|---|---|
| a319 (Airbus A319) | 35.4 | 2.8 / 5.7 | 100 | 2 | no (window geometry) |
| a320 (Airbus A320) | 35.3 | 2.8 / 5.7 | 99 | 2 | no (window geometry) |
| a321 (Airbus A321) | 32.6 | 3.1 / 6.1 | 97 | 2 | no (window geometry) |
| a333 (Airbus A330-300) | 20.0 | 5.0 / 10.0 | 108 | 2 | yes |
| a359 (Airbus A350-900) | 19.6 | 5.1 / 10.2 | 86 | 2 | no (window geometry) |
| a388 (Airbus A380-800) | 15.3 | 6.5 / 13.1 | 102 | 4 | yes |
| b738 (Boeing 737-800) | 36.0 | 2.8 / 5.6 | 76 | 2 | yes |
| b744 (Boeing 747-400) | 20.1 | 5.0 / 10.0 | 104 | 4 | yes |
| b748 (Boeing 747-8) | 14.0 | 7.2 / 14.3 | 89 | 4 | no (window geometry) |
| b752 (Boeing 757-200) | 30.6 | 3.3 / 6.5 | 83 | 2 | no (window geometry) |
| b763 (Boeing 767-300) | 26.3 | 3.8 / 7.6 | 65 | 2 | no (window geometry) |
| b788 (Boeing 787-8) | 24.2 | 4.1 / 8.3 | 110 | 2 | no (window geometry) |
| bcs1 (Airbus A220-100) | 39.0 | 2.6 / 5.1 | 83 | 2 | no (window geometry) |
| bcs3 (Airbus A220-300) | 39.1 | 2.6 / 5.1 | 60 | 2 | no (window geometry) |
| crj2 (Bombardier CRJ200) | 54.1 | 1.8 / 3.7 | 71 | 2 | yes |
| crj7 (Bombardier CRJ700) | 56.9 | 1.8 / 3.5 | 66 | 2 | no (window geometry) |
| crj9 (Bombardier CRJ900) | 56.2 | 1.8 / 3.6 | 66 | 2 | no (window geometry) |
| e170 (Embraer E170) | 43.7 | 2.3 / 4.6 | 99 | 2 | no (window geometry) |
| e190 (Embraer E190) | 38.2 | 2.6 / 5.2 | 98 | 2 | no (window geometry) |
| e75l (Embraer E175) | 41.4 | 2.4 / 4.8 | 74 | 2 (components) | no (window geometry) |
| md11 (McDonnell Douglas MD-11) | 17.2 | 5.8 / 11.6 | 97 | 2 (components) | no (window geometry) |

Geometry, `MODEL_DIMS` and `MODEL_FEATURES` are unchanged (vertices are duplicated along chart seams). The unatlased
conversions are kept in `refs/cache/models_orig/` (the atlas source).

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
