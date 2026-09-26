# Domestic terminals (Harvey Milk T1, T2, T3): research spec

Research note, 26 Sep 2026. **This is a research draft for the owner's review.** No 2-D sheet or 3-D geometry has been
built from it yet, per the owner's method (drawings first).

Where things are:

| What | Where | Committed? |
|---|---|---|
| Machine-readable spec: every value with unit, tag, sources and URLs, confidence and status | `tools/buildings/spec_domestic.json`, built by `tools/buildings/build_spec_domestic.py` | yes (no pixels) |
| Tools | `tools/buildings/dom_*.py` | yes |
| Source documents, photos, NAIP epoch rasters | `refs/cache/buildings/domestic/` | no (gitignored) |
| QA crops and overlays with imagery | `out/buildings/domestic/` | no (local only) |

Nothing in `js/` or `data/` was changed.

**Legend**

- **[pub]**: published by an original source. That means SFO, the SF Arts Commission Civic Design Review (CDR) submittals,
  the architects, engineers or builders, or the FAA. The value is transcribed, not measured.
- **[obs]**: measured by me with the stated method, on NAIP 2020/2024, the FAA DOF, the SFO Museum geometry, or licensed
  photos used as reference only.
- **[inf]**: derived from [pub] and [obs] values by stated arithmetic. It must be confirmed before it is treated as fact.
- **[unverified]**: no original source could be read.

Frame: `ltp-nad83-2011` (x east, z south, metres from the ARP). Airport grid axes: s = 117.83° (ESE), t = 27.83° (NNE).
Heights are above the local apron unless stated.

---------------------------------------------------------------------------------------------------------------------

## 0. Summary

1. **Primary drawings exist only for Terminal 3.**
   - The Terminal 3 West CDR set (Oct 2023, 95 % construction documents) gives the T3 floor and roof elevations [pub]:
     L1 arrivals 11'-0", L2 departures 27'-0", mezzanine 42'-6", FIS corridor 45'-0", roof high points **58'-6" (R2)**
     and **81'-0" (R3)**, and the new T3W parapet at 66'-0".
   - Measured from the arrivals floor, those are 14.5 m, 21.3 m and 17.0 m [inf].
   - The wall sections give the storey heights: 16'-0"/16'-9", 18'-0", and 56'-0"/59'-7" to the parapet.
   - The datum of these elevations is not stated.
2. **T1 and T2 have no published heights,** except one: the Harvey Milk T1 main-hall skylight trusses are **70 ft above
   the Level 3 floor** (SFO Museum) [pub]. That is a lower bound for the hall roof, not a roof height.
3. **Pier roof heights [obs] come from a new two-epoch NAIP method** (§2). It uses NAIP 2020 (late-afternoon sun, long
   ESE shadows) and NAIP 2024 (near noon, roofs leaning about 0.4 m per metre of height). It cancels the unknown relief
   lean of both epochs. It was checked against two controls:
   - the FAA DOF building point on the BA-F arm: measured 11.0 m vs 10.4 m published;
   - Boarding Area A, with the lean taken from the FAA DOF poles: 1 % agreement.

   | Roof | Height above apron | Confidence | Note |
   |---|---|---|---|
   | Boarding Area B, outer roof edge (south half) | **12.9 ± 0.7 m** (42 ft) | medium | the central clerestory rises above this; not measured |
   | Boarding Area E, tapered fascia (north part) | **13.5 ± 0.7 m** (44 ft) | medium | |
   | Boarding Area F, north-east arm | **11.0 ± 0.7 m** (36 ft) | medium | FAA DOF 06-035331: 34 ft (10.4 m ± 0.9) [pub] |
   | Boarding Area D, head | 8.9 ± 0.7 m | **low** | DOF (2013) 24–25 ft = 7.3–7.6 m at the head corners [pub] |
   | Boarding Area C, east half | 7.5 ± 1.6 m | **low** | single face, assumed lean |
   | *Control:* Boarding Area A (ITB) | 18.7 ± 0.8 m | medium | the ITB research has 17.0 m (low) |

   The current builder (`tools/build_terminal_parts.py`) uses **14.6 m for every pier**. That is 1–7 m too high for the
   domestic piers.
4. **The SFO Museum polygons are level-2 floor outlines** (`sfo:level 2`), not roof outlines.
   - The lean-free roof edges overhang them by **1.8–3.3 m on the airfield (ESE) faces**.
   - They sit **1.3–2.0 m inside them on the WNW faces**.
   - BA-B roof width is 55.4 m, against an outline width of 53.7 m.
5. **Facades and roofs [pub]:**
   - **BA-B:** electrochromic (View) concourse glazing (112,000 sq ft); Low-E glazing at the clerestory; a 1–1.2 MW
     rooftop PV array (~3,000 panels); landside roof wells or courtyards. Two levels plus a mezzanine, concrete frame on
     100-ft piles.
   - **T1 Center:** a fritted "redwood" glass curb wall over a continuous glass canopy.
   - **T2:** clerestory windows and skylights over the lobby.
   - **BA-E:** a tapered roof edge overhanging clerestory glazing, over light and dark grey metal bands and glass with
     vertical fins.
   - **T3 East:** a large perforated, corrugated metal penthouse.
6. **T3 West is a construction site** (Aug 2024 to about 2029). A May 2026 design change adds one airside storey. The
   owner must choose which state to model (§6).

---------------------------------------------------------------------------------------------------------------------

## 1. Sources found and what each contributes

All sources are cached in `refs/cache/buildings/domestic/src/`. The full list with URLs is in the spec under `sources`.

| Source | Kind | Contributes |
|---|---|---|
| **T3W Civic Design Review, CD Phase 3, Oct 2023** (`231004_CDRC_CD_FINAL.pdf`) | primary: SFO / Turner / Gensler / TEF submittal | 95 % CD elevation sheets 5A-A5.01.01/.02 with the level markers (§5.1); "field" and "gatehouse" wall sections with storey heights and parapets; exterior material legend (ACM colours, electrochromic glass, perforated penthouse panel); existing and new massing; T3 East and BA-E reference photos with material keys |
| T3W CDR Concept (Feb 2024), SD Phase 1 (Mar 2024), C4C (Mar 2024), DD Phase 2 (Oct 2024), Post-Phase-3 update (18 May 2026) | primary | landside facade concept; "Existing Airside Architectural Languages" massing (BA-F octagon, arms, penthouses); kit of parts citing T1 fritted glass and continuous canopy and T2 "massing hierarchy"; the 2026 change: +1 storey airside, Level 4 club 22,450 SF, Level 5 penthouse 15,300 SF |
| SF Arts Commission CDR **minutes** of 21 Mar 2016 and 15 Aug 2016 | primary (minutes) | T1 Center (Gensler) and BA-B (HKS) teams; landside fritted glass on the top half, clear glass below the canopy; laminated-wood vestibules; airside glass plus painted metal panels, spandrels instead of louvres; "roof wells as intake zones". The 2016–17 presentations themselves are not online |
| SFO press releases: T1 final phase (17 Jun 2024), T3W start (20 Aug 2024) | primary | T1 phases, gates B3 and C1; T3W: 650,000 sq ft renovated, +200,000 sq ft, six-storey Courtyard 4 building, $2.6 B |
| **SFO Museum**, "Four Sculptural Light Reflectors" | primary | T1 Main Hall (Level 3, pre-security): four 180 × 30 ft reflectors in the skylight trusses, **70 ft above the floor** |
| SFO Museum architecture data (`refs/sfom-arch`) | open data (CDLA-Permissive) | the polygons are level-2 floor outlines; no heights |
| Arup, Woods Bagot, DBIA, RDH, Cupertino Electric, Webcor, Southland (BA-B) | primary (design team and builders) | 25 gates; "two levels and a mezzanine"; three-storey concrete frame on piles; electrochromic glass plus Low-E at the clerestory; 1 MW / 1.2 MWdc PV with ~3,000 panels; 619,150 sf; LEED Platinum |
| HKS BA-B page | **snippet only**: HTTP 403 | 1 MW rooftop solar |
| Kuth Ranieri, Hensel Phelps, AIA SF (T1 Center) | primary | Gensler / Kuth Ranieri JV, Hensel Phelps design-build, 1.1 M sf / 900,000 SF, completed June 2024 |
| Airport Improvement 2020 (T1) and 2011 (T2) | trade press quoting SFO and the architects | BA-B 617,700 sq ft on 3 levels, 4 swing gates, 100-ft piles, View glass 112,000 sq ft, "three large skylights" (2020, phase 1); T2 640,000 sq ft, two-level, clerestories and skylights, roof "floating angular planes" |
| Gensler (T2, BA-E), gb&d, Inhabitat (T2) | primary / press | T2: 14 gates, LEED Gold, clerestory windows and skylights, 456-kW PV on an adjacent building |
| **IDA award entry by Gensler (BA-E)**, Hensel Phelps news, BD+C (by Gensler) | primary | BA-E: "tapered edges overhanging clerestory glazing … lightweight, long-span trusses"; unveiled 25 Jan 2014; $138 M; 10 gates; 65,000 / 68,800 sf |
| MKA (T3E, T3W), Studio 151, Turner | engineers / consultants / builder | T3E three-storey, 320,000 ft² (MKA) or 400,000 SF + 53,000 SF with 3 gates (Studio 151); T3W: six-storey Courtyard 4, facade replacement |
| **FAA DOF** (DOF.CSV of 2026-09-18) | primary | domestic BLDG points surveyed 2013 (accuracy 1A): BA-F arm 34 ft, BA-D head 24–25 ft, old T1 50 ft (demolished). DOF 06-039216 "130 ft" is an antenna on the parking garage, not a terminal (FAA OE/AAA 2012-AWP-7455-OE) |
| USDA **NAIP 2020, 2022 and 2024** | public domain | all [obs] measurements (§2–3) |
| Wikipedia | **secondary** | only for the original 1954, 1963 and 1971–81 architects and dates |
| Wikimedia Commons (26 photos) and architect / builder photos | reference only | §7 |

**Searched but not found or not readable:**
- flysfo.com "Harvey Milk Terminal 1 Redevelopment" (HTTP 403);
- the HKS, Architect Magazine and Architizer pages (403; the Wayback Machine refused);
- the CDR presentations for T1 Center and BA-B, 2016–2017 (only minutes are online);
- a T2 / BA-D CDR set;
- the SFO RADP EIR text on existing heights. The Draft EIR (Case 2017-007468ENV) was not retrieved; only the NOP is in
  the ITB cache.
- FAA OE/AAA cases for the new T1 buildings: the public circle search only returns about one year of cases.

---------------------------------------------------------------------------------------------------------------------

## 2. Method: roof heights from two NAIP epochs

**Problem.** NAIP is orthorectified to a terrain DEM, not a surface model. A roof point at height h is imaged displaced
by **k·h**. k is an unknown 2-D "lean" vector that changes with the flight line, and even inside one mosaic (frame and
strip seams).
- In 2024 the domestic roofs lean about 0.3–0.55 m per metre of height, toward the east.
- In 2020 they lean between −0.35 and +0.25 m per metre, depending on the spot.
- No public lidar or true ortho exists (docs/research/imagery.md §6).

**The two epochs.**

| Epoch | Flown | Sun | Shadows | Where the sun values come from |
|---|---|---|---|---|
| NAIP 2020 | 2020-05-24, about 16:45 PDT | azimuth ≈ 267°, elevation ≈ 40° | long, toward the ESE | the ATCT shadow azimuth plus the NOAA sun path (`dom_sun.py`) |
| NAIP 2024 | 2024-05-20, 13:15 PDT | azimuth 186.6°, elevation 72.5° | short, toward the NNE | the DOF pole 06-034826 shadow, from the ITB research |

**Measurement.** On a grid-aligned pier I measure three quantities, each as the median cross-profile over 60–90 m of
edge at 0.1 m sampling (`dom_profile.py`):

| Quantity | What it is | Equals |
|---|---|---|
| band20 | on the face turned away from the 2020 sun (ESE), the width of the dark band from the roof edge to the end of the cast shadow on the apron | h (s20 − k20)·n |
| band24 | on the opposite face (WNW) in 2024, the dark band of the shaded, obliquely seen facade plus its shadow | h (k24 − s24)·n |
| p | the shift of the same roof edge, or roof texture, between 2020 and 2024 | h (k24 − k20)·n |

Therefore **h = (band20 + band24 − p) / ((s20 − s24)·n)**. Both leans drop out. The denominator is about 1.14 for ESE/WNW
faces, so each 0.35 m edge-pick error costs only about 0.3 m of height. The leans come out as a by-product, and they are
plausible everywhere: k24·n = 0.28–0.48, k20·n from −0.31 to 0.19.

**Scale.** The only scale-setting constant is |s20|, the 2020 shadow length per metre.
- The ATCT shadow gives the direction (87.4 ± 1.5°). On the sun path that allows |s20| = 1.15–1.29.
- Two independent controls fix it at **1.19 ± 0.03** (sun elevation 40.0°):
  - **FAA DOF 06-035331,** the BA-F north-east arm roof, 34 ft ± 3 ft [pub] → measured 11.03 m vs 10.36 m.
  - **Boarding Area A**: the solved 2024 lean k24.x = 0.418 matches 0.413 from the FAA DOF poles (ITB research,
    `tools/buildings/itb_naip_measurements.json`). The height is 18.7 m.
- The uncertainty of each height combines four edge picks (±0.35 m each) and ±0.03 in |s20|. It is ±0.65–0.75 m.

**What the method cannot do.** It needs a straight roof edge with clean apron on both sides. It cannot do curved halls
(T1 Center, T2, T3 landside) or faces over roadways. Faces along s (NNE/SSW) give a small denominator of 0.31, so those
are single-face estimates with an assumed lean (BA-C) [low].

**Checks.**
- Parallax consistency: for BA-B, the dark ESE perimeter strip and the PV rows shift by the same 3.3–3.4 m between
  epochs. They are therefore at the same height, and the strip is not a lower eave.
- The same holds for BA-E: the fascia edge moves 2.2 m and the roof texture 2.5 m.
- Overlays: `out/buildings/domestic/h_<roof>_<year>.jpg` show the measured faces (red and blue) and the lean-free roof
  edges (green) on both epochs.

**Cross-workflow note** [obs]. With |s20| = 1.19, the ATCT cab-roof shadow on NAIP 2020 puts the tower axis at
**x ≈ −733.5 ± 3** (z ≈ 324). The tower research value is −740.5 (bounded ±5). With −733.5 the 2024 cab lean becomes
0.50, which fits the k24 trend measured here. This is worth re-checking in `buildings_tower.md`.

---------------------------------------------------------------------------------------------------------------------

## 3. Harvey Milk Terminal 1

### 3.1 General [pub]

- **Composition:** Boarding Area B (B2–B27), the T1 Center (check-in, security, baggage claim) and Boarding Area C
  (C1–C11).
- **Openings:**
  - first 9 BA-B gates: 23 Jul 2019;
  - 9 more gates plus the south lobby: May 2020;
  - BA-B complete: 2021;
  - final phase: 17 Jun 2024 (north lobby, mezzanine checkpoint, B3, C1, and the all-terminal connector).
- **Teams:**
  - BA-B: Austin Commercial / Webcor JV with the HKS / Woods Bagot / ED2 / KYA JV (plus Tsao), and Arup;
  - T1 Center: Hensel Phelps with Gensler / Kuth Ranieri.
- **Floor areas conflict:**
  - BA-B: 619,150 sf (DBIA), 617,700 sf "on 3 levels" (Airport Improvement), 500,000 sf (Woods Bagot);
  - T1 Center: 1.1 M sf (Kuth Ranieri), 900,000 SF (Hensel Phelps).

### 3.2 Boarding Area B

**Section [pub].**
- Arup: "two levels and a mezzanine". RDH: a three-storey concrete frame. The mezzanine holds the airline clubs and the
  international corridor (DBIA).
- The concourse centre rises to a **clerestory**: "Low-E high performance glazing at the clerestory level" (Arup),
  visible in the interior photos.
- The gates have floor-to-ceiling electrochromic glass (View, 112,000 sq ft in total).

**Roof [pub and obs].**
- A 1 MW (1.2 MWdc, ~3,000 panels) PV array [pub]. [obs] on NAIP and the Google screenshot b1d51b0f:
  - PV rows run parallel to the pier axis, ~5.5 m wide at ~9 m pitch;
  - a narrow PV row runs along the ESE roof edge;
  - a central light strip carries skylight grids;
  - on the landside (WNW) half of the north part, long sunken **roof wells / courtyards** with planting are crossed by
    two bridges. The CDR (Aug 2016) discussed "roof wells as intake zones".

**Heights [obs].**
- **Outer roof edge 12.9 ± 0.7 m** (south half).
- The clerestory height is **not measured** (open).
- Lean-free roof edges:
  - ESE edge 3.3 m outside the level-2 outline, which reads as a roof overhang;
  - WNW edge 1.6 m inside it;
  - width 55.4 m.

**Facade materials [pub].** Glass and painted metal panels airside, with metal spandrels at the air intakes (CDR 2016).
Colours are not published.

### 3.3 T1 Center (main hall)

- **70 ft** from the Main Hall (Level 3) floor to the skylight trusses [pub]. There are **four** 180 × 30 ft light
  reflectors, so four skylights at least 55 × 9 m [pub]. Airport Improvement 2020 mentions "three large skylights", but
  only half the hall existed then [conflict].
- NAIP 2024 shows the roof almost fully covered by radial (fan-shaped) PV rows, and three light-blue glazed openings of
  about 9 × 11 m [obs, low].
  - The four long skylights could not be identified: the roof is saturated white in the 2024 image.
  - **The hall roof height is not measured** [unverified]. The Level 3 floor elevation is needed.
- **Landside facade [pub]:** two tiers of fritted glass with vertical mullions, in the "redwood" pattern, above a
  continuous glass canopy. Clear glass below the canopy, and warm wood-lined entries. Sources: the CDR minutes (2016),
  Airport Improvement, and the T3W "kit of parts". A reference photo is Commons p00 (Famartin, 2025).
- The FAA DOF points on the *old* T1 (50 ft, 2013) are superseded [pub, obsolete].

### 3.4 Boarding Area C

- This is the 1963 South Terminal pier, "refreshed" with the T1 Center [secondary / pub].
- **Roof about 7.5 ± 1.6 m** [obs, low: single NNE face, assumed lean].
- On the roof [obs]: two long dark bands on both sides of a lighter spine. These may be glazed monitors or dark roofing;
  that is unresolved. Also a light-blue glazed patch (2024) and a rounded ESE end.

---------------------------------------------------------------------------------------------------------------------

## 4. Terminal 2 and Boarding Area D

**History [pub].**
- Opened 1954 as the Central Terminal.
- Rebuilt by Gensler as the International Terminal (1983).
- Closed 2000.
- Reopened 14 Apr 2011 after a $383 M Gensler / Turner design-build renovation.

**Size and daylight [pub].**
- 640,000 sq ft over two levels, with 14 gates (D1–D12, D14–D16).
- Clerestory windows and skylights over the ticketing lobby and the recompose areas.
- Interior "floating angular planes" hang below the roof.
- The 456-kW PV array is on an *adjacent* building.
- The old ATCT stood on top of T2 (photos from 2009 and 2013).
- The landside is a light metal-panel box with a glass entry wall.

**T2 hall height:** not measured [unverified].

**BA-D [obs, low].**
- The head is **8.9 ± 0.7 m**.
- Its two measured faces are about 90 m apart and may belong to different roof levels.
- The FAA DOF (2013) gives 25 ft and 24 ft (7.6 and 7.3 m) near the head corners [pub]. It also gives 06-035320, which
  is 30 m east of the head and is probably an apron object.
- On the roof: a large trapezoidal head with two semicircular features and linear skylights.

---------------------------------------------------------------------------------------------------------------------

## 5. Terminal 3 and Boarding Areas E and F

### 5.1 Terminal 3 levels [pub], from the 95 % CD elevations (Oct 2023)

| Level marker | Elevation | Above T3 L1 [inf] |
|---|---|---|
| T3W L1 arrivals TOC | 10'-3" | −0.75 ft |
| T3 L1 arrivals TOC | 11'-0" | 0 |
| T3 L2 departures TOC | 27'-0" | 16.0 ft = 4.88 m |
| T3 L2M mezzanine TOC | 42'-6" | 31.5 ft = 9.60 m |
| T3 L3 FIS corridor TOC | 45'-0" | 34.0 ft = 10.36 m |
| **T3 R2 top of roof at the high point** | **58'-6"** | **47.5 ft = 14.48 m** |
| T3W top of parapet (new) | 66'-0" | 55.75 ft above T3W L1 = 16.99 m |
| **T3 R3 top of roof at the high point** | **81'-0"** | **70.0 ft = 21.34 m** |

- The wall sections agree:
  - the "field" wall is 16'-0" + 18'-0" + 22'-0" = **56'-0"** from arrivals to parapet, with a 42" parapet above a
    single-ply roof;
  - the "gatehouse" wall is 16'-9" + 18'-0" + … = **59'-7"**, with an 8'-0" penthouse screen.
- Datum [inf, unverified]: the sheets do not state the datum. The DOF ground next to T3 is 9–10 ft AMSL. If the project
  datum is close to NAVD88, L1 sits 1–2 ft above the apron.

### 5.2 T3 West (under construction) and T3 East [pub]

- **T3W scope:**
  - 650,000 sq ft renovated and +200,000 sq ft new;
  - a seismic retrofit and a complete facade replacement;
  - new F1–F4 gatehouses, an FIS sterile connector to the ITB, the six-storey Courtyard 4 building, and new mechanical
    penthouses.
- **T3W materials:** ACM rainscreen in Whetstone Gray Metallic, Norfolk Gray Mica and Focus Black; electrochromic and
  fritted glazing; perforated panels matching the T3E penthouse.
- **2026 change:** one more airside storey (Level 4 club; Level 5 mechanical penthouse, 15,300 SF).
- **T3 East, existing:**
  - clear glass with grey frit, platinum and dark-grey metallic panels, vertical mullion fins and a metal brow;
  - a large rooftop penthouse clad in light-grey perforated corrugated metal with wide-profile accent stripes (CDR
    photos).
  - T3E size conflicts: 320,000 ft², three-storey (MKA) vs 400,000 SF + 53,000 SF (Studio 151).

### 5.3 Boarding Area E

- **Renovation [pub]:** Hensel Phelps with Gensler and KPA, unveiled 25 Jan 2014, $138 M, 10 gates, LEED Gold.
- **Roof [pub]:** "tapered edges overhanging clerestory glazing … lightweight, long-span trusses". The middle two column
  rows were removed.
- **Facade [pub, CDR photo keys]:** clear glass with frit, light-grey and dark-grey metallic metal-panel bands, and
  aluminium vertical fins.
- **Height [obs]: 13.5 ± 0.7 m** to the fascia (north part). The fascia and the roof texture shift alike, so there is one
  level at the edge.
- Lean-free WNW roof edge [obs]: about 2 m inside the outline. The roof width is about 42.7 m vs an outline width of
  45.0 m.

### 5.4 Boarding Area F

- 18 gates today (F5–F22; F1–F4 are being rebuilt) [secondary / pub].
- An octagonal rotunda hub with arms [pub, CDR massing; obs].
- **North-east arm: 11.0 ± 0.7 m** [obs], against **34 ft = 10.4 m** in the DOF [pub].
- DOF 06-035332 records 16 ft at the arm tip. What it is (a lower end structure or a rotunda) is an open question.
- The other arms, the F connector and the hub were not measured: the outline edges there show no clean profile.

---------------------------------------------------------------------------------------------------------------------

## 6. Deviations of the current 3-D model (information only; `js/` and `data/` are untouched)

- `tools/build_terminal_parts.py` gives every pier `PIER_H = 14.6 m`. Measured values: B 12.9, E 13.5, F 11.0, D about
  8.9 (low), C about 7.5 (low).
- The halls T1 20 / T2 19 / T3 21 m are "approximate". The published T3 roof high points are 14.5 m (R2) and 21.3 m (R3)
  above L1.
- `js/live/terminals.js` uses generic piers: glass to 13.4 m and a skylight spine. The real piers differ:
  - BA-B has a PV roof, a central clerestory and landside roof wells;
  - BA-E has an overhanging tapered fascia over clerestory glass;
  - T3 has big mechanical penthouses.
- Roof overhangs of up to about 3 m beyond the SFO Museum outlines on the airfield faces are not modelled.

---------------------------------------------------------------------------------------------------------------------

## 7. Photos (reference only; never shipped)

All are in `refs/cache/buildings/domestic/photos/` with `manifest.json` (author, licence, date, camera location). The
spec's `photos` list has every file. The most useful:

| File | Commons page | Licence, author, date | Use |
|---|---|---|---|
| p22 | *Aerial view of SFO from departing flight, September 2025* | CC BY-SA 4.0 / GFDL, Pi.1415926535, 2025-09-09 | oblique of T2/BA-D, the ATCT, T3, BA-E and BA-F from the NE: the best exterior reference |
| p00 | *2025-08-12 … The front of Harvey Milk Terminal 1 viewed from AirTrain …* | CC BY-SA 4.0, Famartin | T1 landside fritted glass and canopy |
| p02 | *SFO - San Francisco International Airport 2024* | CC BY-SA 4.0, Elbeaux, 2024-11-21 | BA-B concourse clerestory |
| p06, p07 | *SFO Terminal 2 from AirTrain* / *2009-0722-SFO-Terminal2* | CC BY-SA 3.0 Grendelkhan (2013) / CC BY 3.0 Bobak Ha'Eri (2009) | T2 with the old tower (superseded) |
| p21 | *Aerial view of SFO, September 2022* | CC BY-SA 4.0 / GFDL, Pi.1415926535 | overview |
| p17–p20 | *Aerial photographs of SFO (July 2022) 1–4* | CC0 | distant obliques |

**Architect and builder photos,** reference only and copyrighted, are in `refs/cache/buildings/domestic/photos_arch/`:
Woods Bagot / Joe Fletcher, DBIA, RDH and CEI. They show the BA-B interior clerestory and holdroom glazing, and the T1
landside facade. The CDR PDFs also contain SFO / Gensler photos of the BA-E and T3E facades.

---------------------------------------------------------------------------------------------------------------------

## 8. Open questions and unverified items

1. **Datum of the T3 CDR elevations.** Ask SFO Design & Construction for the SFO project datum vs NAVD88, and the apron
   elevation at T3.
2. **T1 Center, T2 and T3 landside hall roof heights and skylight/clerestory geometry.** For T1: the Level 3 floor
   elevation plus the 70 ft, or a licensed photo with a scale reference. None are published.
3. **BA-B clerestory** height and width above the 12.9 m roof. The BA-B north half and the roof wells were not measured.
4. **BA-C and BA-D** are low confidence. The D DOF points (24–25 ft) are 1.3–1.6 m below our 8.9 m.
5. What the DOF points 06-035320, 322, 323 and 332 are.
6. **T3W state to model:** before construction (NAIP 2024), during construction (today), or the approved design with the
   2026 extra storey? This is the owner's decision.
7. NAIP 2020 leans vary irregularly across the site because of frame and strip seams. The San Mateo County 15 cm ortho
   (licence request, `imagery.md`) or lidar would remove the ambiguity.
8. **Unverified sources:**
   - HKS BA-B (snippet only);
   - Architect Magazine and Architizer (403);
   - flysfo.com T1 redevelopment page (403);
   - T1/BA-B CDR presentations (not online);
   - Wikipedia-only dates and architects of the original terminals.
9. Tower axis (§2): x ≈ −733.5 from the 2020 shadow, vs −740.5 in the tower research.

---------------------------------------------------------------------------------------------------------------------

## 9. Reproduce

```bash
python3 tools/buildings/dom_naip_epochs.py                          # NAIP 2018/2020/2022/2024 on the world grid (~6 min) -> refs/cache/buildings/domestic/naip/
python3 tools/buildings/dom_sun.py                                  # sun-path table for both dates
python3 tools/buildings/dom_shiftfield.py --a 2020 --b 2024         # dense 2020->2024 parallax field (QA map)
python3 tools/buildings/dom_heights.py                              # roof heights -> tools/buildings/dom_heights.json + QA overlays
python3 tools/buildings/dom_photos.py                               # Commons reference photos + manifest (3 s per request)
python3 tools/buildings/build_spec_domestic.py                      # -> tools/buildings/spec_domestic.json
```

Helpers:
- `dom_common.py`: epoch rasters, (s, t) crops, DOF reader, QA grids;
- `dom_profile.py`: median cross-profiles and sub-pixel steps;
- `dom_edges.py`: per-row edge picker, used in exploration.
