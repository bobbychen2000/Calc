# SFO landside buildings: parking garages, AirTrain, Grand Hyatt, Rental Car Center, CAC / SFO Museum, maintenance hangars

Research note, 26 Sep 2026. It feeds the 2-D drawing stage (plans and elevations drawn to verified dimensions) and,
after the owner's review, the 3-D build. **This is a research draft.** No 2-D sheet or 3-D geometry has been built from
it yet, per the owner's method: drawings first.

- **Structured spec:** `tools/buildings/spec_landside.json`, written by `tools/buildings/build_spec_landside.py`. It
  holds 126 items (88 [pub], 33 [obs], 5 [inf]) with value, unit, metres, tag, confidence, source ids and a note. It
  also holds 49 sources, 13 reference photos, 10 conflicts and 12 open questions.
- **Measurements:** `tools/buildings/landside_naip_measure.py` writes `tools/buildings/landside_naip_measurements.json`.
  It covers footprint metrics, FAA DOF obstacles per building, NAIP roof-shift scans, roof-deck car counts, AirTrain
  polygon widths and the United MOC roofs. Helpers are in `tools/buildings/landside_common.py`, and
  `tools/buildings/landside_fetch.py` does the downloads and text extraction.
- **Local files:**
  - Source pages, PDFs and Commons thumbnails are in `refs/cache/buildings/landside/`, which is gitignored.
  - QA overlays with NAIP pixels are in `out/buildings/landside/`, which is local only: `overview_landside.jpg`,
    `crop_*.jpg`, `qa_cars_*.jpg` and `f_*.png`.
- **Not touched:** nothing in `js/` or `data/` was edited, and nothing was committed.
- **Fact-checked 4 Nov 2026:** see `## Verification` at the end. Every value in the spec now carries a verdict.
  The key changes:
  - The Garage A / G helix-drum tops are 38–40 m; the "25–30 m" reading is disputed.
  - The RCC parapet is 54–59 ft (DOF); the NAIP "19.5 m agrees" check is refuted.
  - The CAC parapet is 17.4–19.2 m and the LTP 1 parapet about 16.5 m, both by shadow.
  - The Central garage was built in phases from 1963 to 1981.
  - The Superbay roof has 8 × 17.3-m bays per side (Deep3DS says 50 ft) and a 32-m spine.
  - The NAIP frames differ in time and in lean.

**Legend.**

| Tag | Meaning |
|---|---|
| **[pub]** | Published by an original or primary source: SFO, SF Planning EIR documents, the FAA, the architect, engineer or contractor, or trade press quoting them. The value is transcribed, not measured. |
| **[obs]** | Measured by me, with the method stated. Sources are NAIP 2024, the SFO Museum footprints, the FAA DOF, and licensed photos used as reference. |
| **[inf]** | Derived from [pub] and [obs] values under a stated assumption. It must be confirmed before it is treated as fact. |
| **[unverified]** | Could not be checked against an original source. |

World frame: `ltp-nad83-2011`. x points east, z points south, in metres from the ARP. Headings are true, clockwise from
north. The airport grid axes are 27.83° and 117.83°.

---------------------------------------------------------------------------------------------------------------------

## 0. Summary

1. **The best primary source is the SFO RADP Draft EIR** (SF Planning, April 2025, Case 2017-007468ENV) and its
   appendices [pub].
   - They give SFO's own building numbers and several existing heights:
     - **Central (Domestic) Parking Garage, Building 195:** "five-level, 81-foot-tall", 3,680,000 sq ft, 6,460 spaces.
     - **Rental Car Center ready-return garage, Building 780:** "66-foot-tall", 1,488,000 sq ft, 2,485 stalls.
   - Appendix E.1 (a memo to SFO of 26 Jun 2018) tabulates the parking supply of every garage.
2. **Level counts are published for every garage and the hotel** [pub].

   | Building | Levels | Source |
   |---|---|---|
   | Central garage | 5 | EIR; Dreyfuss + Blackford 1981 |
   | Garages A and G | "nine-level" | Tutor Perini |
   | LTP Garage 2 | 6 levels, 12-ft floor-to-floor | DLR, ENR, Buehler |
   | Rental Car Center | 5 | Tutor Perini; Conrac Solutions |
   | Grand Hyatt | 12 stories | DBIA, Webcor, AGA, SF Chronicle |
   | CAC | 4 stories, 15-ft floor-to-floor | Cavagnero, MCK, Perkins&Will |

3. **Surveyed heights come from the FAA DOF** (accuracy 1A: ±3 ft vertical) [pub].

   | Building | DOF height (AGL) |
   |---|---|
   | Superbay hangar | **135 ft**, with a red obstruction light |
   | LTP Garage 1 | 86 and 91 ft |
   | RCC | roof points at 54 and 59 ft; a 60-ft "tank", probably the station stair tower |
   | United MOC large hangar | 132, 117 and 116 ft |
   | Central garage roof | light poles at 101 and 109 ft |

4. **No height is published for Garages A and G, the Grand Hyatt or LTP Garage 1**, nor for the CAC except by
   arithmetic.
   - My NAIP and photo estimates are low-confidence:
     - Garages A/G about 25–36 m;
     - Hyatt about 40–48 m (provisional 44 m);
     - CAC about 60–66 ft.
   - These need SFO drawings or FAA OE/AAA filings (§10).
5. **Roof decks at the NAIP moment** (Monday 20 May 2024, about 13:25 PDT) [obs]:
   - **RCC**, the densest: rental cars in nose-to-tail lanes, about 21 per 1,000 m²;
   - **LTP Garage 1:** about 18–19 per 1,000 m², 90° stalls, roughly half full;
   - **Garages A and G:** about 13–15 per 1,000 m²;
   - **Central garage:** about 300 cars;
   - **LTP Garage 2:** mostly under PV canopies.
   The counts are ±30 %.
6. **AirTrain** [pub]:
   - opened 2003, $430 M;
   - CX-100 cars 9'3" × 39'6";
   - 11 stations today;
   - "over 6 miles" of guideway;
   - the 2021 extension runs "50 feet above a public roadway".

   Station levels are published: Level 5 of the Domestic Garage, Level 7 of Garages A/G, ITB Level 4, the hotel's
   4th floor, and Level 5 of the LTP garage.
   - The EIR's "35 to 40 feet above ground at its highest point" conflicts with these figures.
   - The SFO Museum AirTrain polygon gives the guideway width [obs]: about 5 m single, 9.5–11.5 m twin.
7. **Superbay hangar (Building 1060)** [pub]:
   - built 1969–72 for American Airlines 747s;
   - four bays, six office levels and a central workshop;
   - "light-gauge steel beams that cantilever over 230 feet from the center";
   - inside height about 120 ft;
   - DOF 135 ft.

   The NAIP roof pattern shows a central spine on the 27.8° grid with cantilevered hangar roofs to the WNW and ESE
   [obs/inf].
8. **United MOC.** It has no SFO Museum outlines. The large stepped hangar block (about 241 × 85 m imaged roof,
   DOF 116–132 ft) and a pair of barrel-vault hangars are recorded from NAIP [obs, low]. Identities and door sizes are
   [unverified].
9. **SFO Museum data issue.** The newer duplicate AirTrain-station polygons "International Terminal (A)" and "(G)"
   (ids 1763588569 and 1763588567) have A and G swapped. The older records 1729791961 and 1729791965 are correct:
   A is south, G is north. `data/` was not edited.

---------------------------------------------------------------------------------------------------------------------

## 1. Sources and what each contributes

| Source | Type | Contributes |
|---|---|---|
| **RADP Draft EIR, Apr 2025** (`radp_deir`, ceqanet 2019050013/3) | primary (SF Planning / SFO) | building numbers; Central garage 5 levels, 81 ft, 3.68 M sq ft, 6,460 spaces; RCC 66 ft, 1.488 M sq ft, 2,485 stalls; LTP Garage 2 completed 2020 (fn. 48); CAC Phase II addendum (fn. 45); Superbay = Building 1060; future projects |
| **RADP Appendices A–G** (`radp_appx`) | primary | App. E.1 parking-supply table (2018); App. B Initial Study: AirTrain "35 to 40 feet" (fn. 19), visual simulations of the LTP garages and the Superbay; NOP heights of other West Field buildings |
| RADP NOP 2019, RTC Nov 2025 | primary | 81 ft garage repeated; Final EIR certified 20 Nov 2025 |
| **FAA DOF** (DOF.CSV 2026-09-18) | primary (FAA) | surveyed obstacle heights (see §2) |
| FAA OE/AAA 2012-AWP-7455-OE | primary (FAA) | the 130-ft DOF "BLDG" on the Central garage is a filed antenna, 4D |
| SFO Museum architecture data | primary (SFO Museum) | ids, addresses, inception dates, geometry source (flysfo / sfomuseum / sfo / sfogis) |
| flysfo.com parking, getting-around and long-term pages; AirTrain Fact Sheet 7/03; releases SF-03-10 (2003) and 5 May 2021 | primary (SFO) | height limits, station levels, AirTrain system data, the extension |
| Dreyfuss + Blackford | architect | Central garage 1981, JV with John Carl Warnecke; 7,000 cars on five levels; 200-ft central open space; bridges with moving walkways |
| Tutor Perini (ITB, RCC); Willis (LTP 1); Conrac Solutions | contractors / operator | Garages A/G: nine-level post-tensioned concrete, architectural precast, metal/composite panels, 3,200 spaces. RCC: five-story, $67 M, service areas on floors 1 and 4. LTP 1: Joseph Chow & Associates / Tutor Saliba |
| DLR, Buehler, ENR, DBIA, Langan, CHS | design-build team / press | LTP Garage 2 facts (§4.2) |
| Hyatt releases 2016/2019, DBIA, Webcor, AGA, Hornberger + Worstell, SF Chronicle 2018 | owner / team | Grand Hyatt facts (§5) |
| Cavagnero, Perkins&Will, Webcor, MCK; SF Planning NOD 2023 | architect / team | CAC facts (§6) |
| Weitz (2 pages), Deep Design Studio, SFO Museum negative 2011.032.2456 | contractors / archive | Superbay facts (§7) |
| PCAD, AirlineReporter | secondary | United base history (§8) |
| Wikipedia AirTrain | secondary | used only to find primary references; a few secondary facts are flagged |

**Searched but not found (or blocked).**
- A published height of the Grand Hyatt, Garages A/G or LTP Garage 1.
- The 1986.638E Master Plan EIR addenda for the hotel, LTP Garage 2 / AirTrain extension and CAC (2015–2019).
- The FAA OE/AAA filings for these buildings. The public OE/AAA area search returns only about the last 12 months;
  a circle search within 3 NM returned 130 cases, all from Sep 2025 to Sep 2026.
- SubwayNut's station pages (403). The "9 story" snippet agrees with Tutor Perini.
- The Arup Grand Hyatt page (404; snippet only).
- An SOM/Goldsmith hangar present-day status.

---------------------------------------------------------------------------------------------------------------------

## 2. FAA DOF obstacles on the landside buildings [pub]

Positions use `geo_frame.wgs84_to_world`, because the DOF datum is WGS 84. Accuracy codes: 1A = ±20 ft horizontal and
±3 ft vertical; 4D = ±250 ft and ±50 ft.

| Building | OAS | Type | AGL ft (m) | Acc. | World (x, z) | What it probably is |
|---|---|---|---|---|---|---|
| Central garage | 06-034812 | POLE | 109 (33.2) | 1A | (−877.9, 305.0) | roof-deck light pole |
| Central garage | 06-034813 | POLE | 101 (30.8) | 1A | (−908.1, 203.8) | roof-deck light pole |
| Central garage | 06-039216 | BLDG | 130 (39.6) | 4D | (−896.3, 178.9) | antenna, OE 2012-AWP-7455-OE ("Short Perm Parking Garage") |
| LTP Garage 1 | 06-035207 | BLDG | 86 (26.2) | 1A | (−2264.4, −2015.0) | inside the footprint (SW part) |
| LTP Garage 1 | 06-035206 | BLDG | 91 (27.7) | 1A | (−2176.4, −1903.6) | 0.7 m outside the NE corner (tower or helix?) |
| RCC | 06-035204 | BLDG | 59 (18.0) | 1A | (−2260.2, −1042.3) | roof outline |
| RCC | 06-035203/-35205/-35329 | BLDG | 54 (16.5) | 1A | NE, W and SW corners | roof outline |
| RCC | 06-034240 | TANK | 60 (18.3) | 1A | (−2278.7, −1074.0) | cylindrical perforated-metal stair/elevator tower at the RCC AirTrain station (photo) [inf] |
| Superbay | 06-001451 | BLDG | **135 (41.1)** | 1A, lit R | (−105.6, −799.7) | south end of the central spine |
| United MOC | 06-035289 / -35290 / -35288 | BLDG | 132 / 117 / 116 | 1A | NE part / NW corner / S end | large hangar block |
| United MOC | 06-035303, -35245, -35292, -35284, -35327, -35291 | BLDG | 107, 92, 79, 75, 74, 70 | 1A | west and north MOC buildings | not matched to names |

The Grand Hyatt (2019), LTP Garage 2 (2019), the CAC (2018) and Garages A/G have **no DOF entry**.

The DOF 1A batch is from the 2013 survey (JDATE 2013289). The tall "POLE" 153–157 ft entries in the US-101 interchange
between the ITB garages and the hotel are highway high-mast lights, not buildings.

---------------------------------------------------------------------------------------------------------------------

## 3. How the NAIP measurements were made, and their limits

**Footprints [obs].**
- The SFO Museum polygons (`data/sfo_airport.json`) give area, perimeter and minimum rectangle.
- Geometry source per record:
  - `flysfo`: Garages A and G, LTP 1 and 2, the RCC. These are probably SFO CAD footprints.
  - `sfomuseum`: the Central garage and the hotel. These are possibly traced from imagery.
  - `unknown`: the Superbay and the CAC.
- imagery.md §6 shows the outlines agree with NAIP roofs within the roof lean (±5–10 m) and with Google roofs to about
  1.5 m.

**Roof shift ("lean") scan [obs, low].**
- NAIP images a roof at height h displaced by k·h. The ITB study fitted, from five DOF 1A poles,
  k(x) = 0.7553 + 0.0002753·x, directed due east, for x = −1622 … −1346.
- The tool slides each footprint east over the NAIP gradient image and reports the strongest peaks.
- Where the footprint is a true ground outline, h = dx / k.
- Limitations:
  - The polygons may be roof traces.
  - Several peaks occur: facade base, parapet, towers and canopies.
  - k is extrapolated outside the calibrated x range and is not valid in other NAIP frames. The North Field (LTP)
    results contradict the DOF, and the Superbay frame leans roofs north-west.

**Sun.** The sun was at about azimuth 187° and elevation 72.4° (from a DOF pole shadow in the ITB study), which is local
early afternoon. Shadows are short: 0.32·h, pointing north.

**Cars [obs, low].**
- Detection uses the CIE-Lab distance from a 9-m median background, over 16 units, on the roof region: the footprint
  shifted by the roof dx and eroded by 3 m.
- Blobs of 2–250 m² are counted as area/9 m².
- White and silver cars on a pale deck are partly missed; merged rows are counted by area.
- A manual check on LTP Garage 1 (1,600 m²) counted 28 cars by eye against 34 by the detector.
- Treat counts as ±30 %.
- The Central garage detector count (1,000) is not usable: the ramp kerbs and helix ring are detected. I estimated
  about 300 by eye.

**Photos** are Wikimedia Commons reference photos; the table is in the spec's `photos`. EXIF GPS is not trusted. For
example, the 243 mm telephoto shot of the Hyatt carries a position 125 m from the hotel.

---------------------------------------------------------------------------------------------------------------------

## 4. Parking garages

### 4.1 Central Parking Garage ("Domestic Garage"), Building 195

| Item | Value | Tag / source |
|---|---|---|
| Opened | 1981, by Dreyfuss + Blackford with John Carl Warnecke & Associates (JV). An earlier garage stood 1963–1981 (SFO Museum). | [pub] db_1981, sfom |
| Levels | **5**: "parking for 7,000 automobiles on five levels … direct ramps to each of the five parking levels" | [pub] db_1981, radp_deir |
| Height | **81 ft (24.7 m)**, "five-level, 81-foot-tall". What it measures (deck, parapet or towers) is not stated. | [pub] radp_deir p. 2-34, radp_nop; definition [unverified] |
| Floor area | 3,680,000 sq ft. Divided by 5, this is 68,400 m² per level, close to the footprint. | [pub] radp_deir |
| Spaces | 6,460 (2025). In 2018 there were 6,459: 5,443 public domestic, 105 ParkFAST, 126 valet and **785 employee on Level 4**. At opening in 1981: 7,000. | [pub] radp_deir, radp_appx E.1, db_1981 |
| Height limit | 6'6" (78 in) | [pub] flysfo |
| Plan | Grid-aligned, about 275 × 275 m (minimum rectangle), 64,392 m² (SFO Museum). **Central circular open space "200 feet in diameter"** with up and down ramps around it; the SFO Museum hole measures **58.9 m (193 ft)**, centred at (−930.8, 275.5). | [pub] db_1981; [obs] sfom |
| Connections | AirTrain T1/T2/T3 stations on **Level 5**. Mezzanine (Level 3) skybridges to the terminals near checkpoints B, D and F. The 1981 design also had tunnels at the first level. | [pub] flysfo_around, db_1981 |
| Ground floor | Taxi staging and the Central Utility Plant | [pub] radp_deir |
| Roof deck | Light poles 101 and 109 ft AGL (DOF). Four curved ramp/island "petals" and the helix ring. Straight stall rows in each quadrant, some angled stalls along the ramps. **About 300 (±100) cars** at the NAIP moment. | [pub] faa_dof; [obs] NAIP |
| Future | RADP "Central Hub" (9 levels, up to 175 ft) would replace it. EIR certified Nov 2025; not built. | [pub] |

- **Roof-deck height** (as opposed to the 81-ft overall figure) is not published.
- 101–109 ft light-pole tops are consistent with 20–28-ft roof poles on a deck in the high 70s to 81 ft [inf, low]. Keep
  it as an open question.

### 4.2 International Garages A (Building 95) and G (Building 495)

| Item | Garage A | Garage G | Tag / source |
|---|---|---|---|
| Address | 95 South Link Road, north of South Link Rd | 495 North Link Road, south of North Link Rd | [pub] sfom, radp_deir |
| Opened | 2000 (with the ITB) | 2000 | [pub] sfom |
| Construction | "$60 million, **nine-level** concrete parking garage with post-tensioned beams and deck slabs, architectural precast concrete, and prefabricated metal/composite panels", with an integral AirTrain station and a steel-truss bridge to the ITB. 3,200 spaces at opening; the text says "garage" for both structures. | same | [pub] tutor_itb |
| Spaces (2018) | 1,585 (1,008 public + 577 employee) | 1,405 (1,151 + 254) | [pub] radp_appx E.1 |
| AirTrain | Garage A station, Building 97, from **Level 7** | Garage G BART and AirTrain station, Building 497, from **Level 7**; the BART station is one level below the AirTrain platform (Wikipedia, secondary) | [pub] flysfo_around, radp_deir |
| Height limit | 8'2" (98 in) | 8'2" | [pub] flysfo |
| Footprint (SFO Museum, src flysfo) | 9,202 m² in 2 polygons, 281.8 × 54.7 m, long side 72.8° | 7,676 m², 282.3 × 71.6 m, long side 63.6° | [obs] |
| Height | **not published.** NAIP shift 13.0 m, which gives **35.7 m** with k = 0.364 | **not published.** NAIP shift 12.0 m, which gives **34.7 m** with k = 0.346 | [obs, low] |
| Roof cars | 91 (12.7 per 1,000 m²); rows along the long axis | 77 (15.0 per 1,000 m²) | [obs, low] |

**Facade [obs, photos].**
- Light architectural precast panels in a square grid.
- The parking levels are screened by perforated metal panels with horizontal slots.
- A cylindrical **helix drum** at the west end has continuous horizontal bands and arched openings at the top.
- Square stair/elevator towers rise one level above the parapet.
- The AirTrain runs through the garage at the station.

**Height conflict.**
- The scan values of 34–36 m would need about 4.3 m per level for 9 levels.
- The photo of the Garage G helix taken from the AirTrain (Aug 2018) shows about three levels plus the parapet above
  the AirTrain line of sight. That suggests a roof deck nearer **25–30 m**, with the 34–36 m peak being towers or
  canopies.
- **Range 25–36 m, unresolved.** "Level 7" for the AirTrain may point to half-levels.

### 4.3 Long-Term Parking Garage 1 (Building 795)

| Item | Value | Tag / source |
|---|---|---|
| Address, date | 795 South Airport Blvd; 1997 | [pub] sfom |
| Team | Architect Joseph Chow & Associates, contractor Tutor Saliba, architectural precast by Willis | [pub] willis_ltp1 |
| Spaces | 3,109 | [pub] radp_appx |
| Height limit | 6'10" (82 in) | [pub] flysfo_ltp |
| DOF | **86 ft** (inside, SW) and **91 ft** (NE corner) AGL, 1A. Probably tower or helix tops rather than the deck. | [pub] faa_dof; interpretation [inf] |
| Levels | **Not published.** At least 5: Garage 2's vehicular connector lands at "level 5", and the AirTrain bridge at "Level 5 of the Long-Term Parking Garage". | [pub] dlr_ltp2, flysfo_ltp → [inf] |
| Footprint | 14,429 m², 177.0 × 93.7 m, long side 154.6°. **Three circular helix ramps** at the corners (N, SE, S). | [obs] |
| Roof cars | 240 by the detector (19.4 per 1,000 m²); manual 17.5 per 1,000 m². 90° stalls: cars at about 70°, aisles along the 155° long axis. Roughly half full. | [obs, low] |

### 4.4 Long-Term Parking Garage 2 (Building 794)

| Item | Value | Tag / source |
|---|---|---|
| Address, dates | 794 South Airport Blvd, at the NW corner of former Lot DD, SW of Garage 1. SFO Museum 2018; ENR best project 2019; "completed in 2020" (RADP fn. 48). | [pub] |
| Team | Progressive design-build, $154.6 M: Nibbi Brothers; DLR Group \| Kwan Henmi with FMG Architects; Watry/Buehler (structural); Langan (geotechnical); CHS (traffic) | [pub] |
| Levels | **6**. The Bay Trail photo shows 5 open floors plus the roof deck. | [pub] DLR/ENR/Buehler/Langan/DBIA; [obs] photo |
| Floor-to-floor | **12 ft** | [pub] enr_ltp2 |
| Roof-deck height | **60 ft (18.3 m)** = 5 × 12 ft, plus parapet and PV canopies | [inf] |
| Area, stalls | 1,190,300 sq ft (1.2 M; 1.25 M); **3,600 stalls** (3,500; 3,000 net in 2018) | [pub], conflict |
| Structure | Four seismically isolated structures, a central lightwell, open cast-in-place frame, a 5,000-sq-ft ground-floor customer area, and an elevator tower with Morse-code mirrored glass | [pub] |
| Roof | Largely covered by **PV canopies**, with cars beneath and between. SFO: 2,700 panels on "the LTP garage" roof (garage not named). | [pub] |
| Links | Vehicular and pedestrian connector to Garage 1 at level 5; AirTrain bridge at level 5 | [pub] |
| Height limit | 8'2" | [pub] |
| Footprint | 18,819 m², 175.1 × 170.8 m, long side 64.6°, stepped west edge. 1,190,300 sq ft divided by 6 levels is 18,430 m², which matches. | [obs] |
| Facade | Exposed concrete frame, columns and deep spandrel beams, open bays with no screens | [obs] photo |
| Roof cars | 289 (17.1 per 1,000 m²); PV edges add false hits and the canopies hide cars | [obs, low] |

### 4.5 Rental Car Center (Building 780; QTA Building 782; AirTrain station Building 779)

| Item | Value | Tag / source |
|---|---|---|
| Address, date | 780 North McDonnell Road; 2000 (AirTrain Blue Line from 2003) | [pub] sfom |
| Levels | **5**: "five-story" (Tutor Perini, $67 M); "five levels of garage and customer service areas on first and fourth floors" (Conrac Solutions) | [pub] |
| Height | **66 ft (20.1 m)** for the ready-return garage | [pub] radp_deir, radp_appx |
| Height check | NAIP shift 3.0 m ÷ k 0.154 = **19.5 m**, which agrees | [obs, low] |
| DOF | 54 ft ×3 and 59 ft on the roof outline; 60-ft "tank" at the station | [pub] |
| Area, stalls | 1,488,000 sq ft; 2,485 ready-return stalls. Divided by 5 levels, this is 27,650 m² per level. | [pub] |
| Footprint | 30,443 m², 203.5 × 197.2 m, including a triangular SE part | [obs] |
| West facade (AirTrain side) | Board-formed concrete, horizontal ribbon windows at the customer level, and a canted green-grey corrugated-metal upper wall. Station: island platform, platform-door cabins, curved metal canopy, cylindrical perforated-metal tower. | [obs] photo |
| Roof cars | **Densest roof: 588** (20.7 per 1,000 m²). Rental cars in long nose-to-tail lanes at about 115–125°, mostly white/silver and black; tan deck with white lane lines. | [obs, low] |
| Future | RADP #12 would convert it into LTP Garage #4 (about 3,700 spaces) | [pub] |

---------------------------------------------------------------------------------------------------------------------

## 5. Grand Hyatt at SFO (Building 55) and its AirTrain station

| Item | Value | Tag / source |
|---|---|---|
| Address | 55 South McDonnell Road, west of Garage A, south of South Link Road. The station is at 59 S McDonnell Rd (Oct 2019). | [pub] radp_deir, sfom |
| Opened | 7 Oct 2019; $237 M | [pub] hyatt_pr_2019 |
| Team | Owner SFO; operator Hyatt. Architect **Hornberger + Worstell** with ED2 International ("ED21"); design-builder **Webcor**; curtain wall **AGA**. | [pub] |
| Stories | **12**: "12-story high rise, Type 1 construction"; "12 levels above grade" | [pub] dbia, webcor, aga, sfchron |
| Structure | Type I concrete. Post-tensioned flat slabs with columns and shear walls (Arup snippet only). | [pub] / [unverified] |
| Lobby / AirTrain | Guests arriving by road take elevators to the **4th-floor lobby**; the AirTrain station connects there by an enclosed bridge | [pub] sfchron, webcor, hyatt_pr_2019 |
| Program | 351 rooms incl. 22 suites (21 per Webcor); 14,435 sq ft meeting space; 215 surface stalls; roof PV (133,000 kWh/yr); no rooftop deck | [pub] |
| Site | 4.2 acres (2019) / 4.7 acres (2016) | [pub], conflict |
| Plan | **Crescent**: convex facade to the west (US 101), concave all-glass facade to the east (airfield). A taller straight block sits at the north end by the station. A 2–3-storey podium clad in dark metal panels, with large glazed openings and a porte-cochère ("55"), is on the east/south. SFO Museum polygon: 3,311 m², 107.4 × 57.6 m, axis 25.7°, including podium and connector. | [obs] sfom, NAIP, photos |
| Facade | Unitised glass curtain wall, vertical mullion grid, one spandrel band per floor, recessed colonnade level above the podium, 4 corner masts on the parapet, and a dark stepped mechanical penthouse near mid-length | [obs] photos 7391/7433 |
| Height | **Not published.** Provisional **44 m (40–48 m)**. | [inf, low] |

**How the provisional height was derived.**
- The near-orthographic photo 7391 (243 mm equivalent, Gregory Varnum, CC BY-SA 4.0) gives grade-to-parapet = 13.2
  typical upper-floor pitches: podium 3.2, colonnade level 1, tower about 9.
- With 3.2–3.5 m per floor (an assumption), that is 42–46 m.
- The NAIP scan has weak peaks at dx 11–12 m, which gives 36–40 m. The strongest peak, 5.5 m, is probably the podium.

---------------------------------------------------------------------------------------------------------------------

## 6. Consolidated Administration Campus (CAC) and SFO Museum facilities

| Item | Value | Tag / source |
|---|---|---|
| Address, date | 674 West Field Road; opened summer 2018 | [pub] sfom, mck |
| Use | Airport departments (administration, landside, terminal and airside operations). The ground floor holds the **SFO Museum's** collection storage, conservation and preparation shops. The public Aviation Library and Louis A. Turpen Aviation Museum is in the International Terminal Main Hall, level 3 (SFO Museum record 1947304235). | [pub] cavagnero, pw, mck, sfom |
| Team | Mark Cavagnero Associates with Perkins&Will; Webcor (progressive design-build); MCK (CM); $84 M; LEED Gold | [pub] |
| Stories | **4** (steel). Floor-to-floor **15 ft**, "increased from 13 feet to 15 feet". | [pub] |
| Height | **About 64 ft (60–66 ft)**: 4 × 15 ft plus parapet. The NAIP scan (extrapolated k) is low confidence. | [inf] |
| Area | 135,000 sq ft (136,000 per P+W) | [pub] |
| Form | A bend in the main bar encloses a protected court. Reduced window-to-wall ratio; exterior louvers on the south and west; interior stair tower with a light well. | [pub] |
| Footprint | 4,752 m², 141.3 × 51.4 m, long side 64.0° | [obs] |
| Phase II | CAC Addendum, Case 2019-006583ETM (issued 17 May 2021, RADP fn. 45; NOD as 1986.638E Addendum 6, final approval 18 Apr 2023, 6.6 acres): a new administration building, a garage replacing Building 676, West Field Road station platform expansion, and two pedestrian bridges. Build status is unverified. | [pub] radp_deir fn. 45, NOD |

---------------------------------------------------------------------------------------------------------------------

## 7. Superbay hangar (Building 1060)

| Item | Value | Tag / source |
|---|---|---|
| Address, users | 1060 North Access Road, East Field near the Seaplane Harbor, about 520 m west of the 19R end. American Airlines and United Airlines. | [pub] radp_deir, sfom, weitz |
| Built | 1969–72 for American Airlines 747s. Weitz: "originally built in 1969". SFO Museum construction negative dated 12 Jun 1970. SFO Museum inception 1972. | [pub], conflict on the year |
| Programme | **Four maintenance bays** ("one of four hangars in the United States that can fully house four 747-sized airplanes"), **six levels of office space**, a central workshop | [pub] weitz_superbay_story |
| Height | **DOF 135 ft (41.1 m)** AGL / 144 ft AMSL, 1A, red light, at the south end of the spine. "140-foot tall roof" (Deep3DS, rounded). Inside height about **120 ft** (sprinklers). | [pub] |
| Structure | "light-gage steel beams that cantilever over **230 feet** from the center of the hangar in each direction"; "open volume of about 12,000,000 cubic feet" (per side or total, ambiguous) | [pub] deep3ds |
| Area | Footprint "250,000 sq ft" (Deep3DS). 420,550 sq ft total (Weitz). SFO Museum polygon **22,201 m² = 238,970 sq ft**. | [pub] / [obs] |
| Plan | Minimum rectangle **165.9 × 134.5 m (544 × 441 ft)**, long side on the 117.8° grid, centre (−93.9, −860.1) | [obs] sfom |
| Layout | Bright raised **spine** along the 27.8° grid (NNE–SSW), about 25–30 m wide. Cantilevered roofs to the WNW and ESE, about 70 m each (165.9 m = 2 × 70 + spine, consistent with 230 ft). Each side is probably split into two bays of about 67 m. Doors are probably on the WNW and ESE faces. The Bay Trail photo (identification unverified) shows roofs falling from a central ridge to both sides. | [obs] NAIP + [inf] |
| NAIP frame | The roof is imaged about (−7, −7.5) m, north-west of the polygon. This frame leans north-west. | [obs] |
| Future | RADP #18: a new 95-ft, 181,000 sq ft hangar on the Superbay employee lot | [pub] |

---------------------------------------------------------------------------------------------------------------------

## 8. United Airlines Maintenance and Operation Center (MOC), North Field

Only partly researched. Every item below is [obs, low] or [unverified] unless marked.

- **History** (secondary):
  - United's base at SFO dates from 1948 (AirlineReporter).
  - A 325,000-sq-ft facility of about 1947 was built by the Austin Co. (PCAD).
  - A 1956–58 SOM (Myron Goldsmith) cantilever hangar existed. One blog says it was demolished [unverified].
- **Large hangar block.**
  - Imaged-roof corners: (−1683, −2025), (−1606, −2048), (−1528, −1837), (−1604, −1797), ±3 m.
  - That gives **about 241 × 85 m**, 19,264 m², long side 160.9°.
  - The relief shift is not removed.
  - The roof steps at about z −1945 and −1885.
  - Aprons lie on the west and south.
  - DOF 1A: **132 ft** (NE part), **117 ft** (NW corner), **116 ft** (S end) [pub].
- **Two barrel-vault hangars** south of it: about 156 × 90 m imaged, doors facing the west apron. No DOF.
- **Other MOC buildings** with DOF tops of 107, 92, 79, 75, 74 and 70 ft stand on the west and north blocks. They are
  not identified.
- **What is needed:** SFO or United building data (numbers, footprints, heights, door sizes), and a lean calibration
  in this NAIP frame.

---------------------------------------------------------------------------------------------------------------------

## 9. AirTrain guideway and stations

| Item | Value | Tag / source |
|---|---|---|
| Opened | 24 Feb / 3 Mar 2003; $430 M | [pub] SF-03-10, fact sheet |
| Team | Guideways: Parsons Brinckerhoff / MGE Eng. / Manna Consultants (engineer), Tutor-Saliba (contractor). Operating system: Lea+Elliott; Bombardier CX-100. | [pub] fact sheet |
| Vehicle | **9'3" × 39'6" (2.82 × 12.04 m)**, 32,000 lb, teal blue metallic. 38 cars (2003), 41 (2021). Trains of up to 3 cars. Rubber tyres, **centre guide beam**, guideway-mounted power rail (600 V AC rectified to 300 V DC; 5 substations). | [pub] fact sheet, 2021 release |
| Length | "Five miles of two independent loops" (2003); "over 6 miles of … concrete guideways" (2021) | [pub], conflict |
| Extension (May 2021) | **1,900 ft** beyond the RCC, "running **50 feet** above a public roadway". Skanska + WSP design-build ($172 M contract, $259 M programme). | [pub] |
| General height | "elevated 35 to 40 feet above ground at its highest point" (RADP IS fn. 19). Conflicts with the extension and with the station levels. | [pub, low] |
| Stations (11) | T1, T2, T3 (Buildings 279/379/479) on Domestic Garage Level 5; International Terminal A and G (197/179) at ITB Level 4; Garage A (97) and Garage G/BART (497) at garage Level 7; Grand Hyatt (Oct 2019; hotel 4th floor); West Field Road (677); Rental Car Center (779); Long-Term Parking (797; bridge to LTP Garage Level 5) | [pub] |
| Lines | Red: clockwise terminal loop, about 9 min. Blue: counter-clockwise, adding West Field Road, RCC and LTP, about 25 min. The T3 station is closed from 4 Nov 2025 to 2027 (secondary). | [pub] |
| Guideway polygon | SFO Museum "AirTrain Rail" (src sfo), 57,727 m². About 7.8 km of polygon centreline. Widths: **single about 4.8–5.1 m, twin about 9.5–11.5 m** (p25–p50 / p75–p90). | [obs] |
| Section | Concrete deck with two running surfaces and a centre guide beam per track, and a side walkway with galvanised railing. Single-column T-piers on the extension. Stations have platform-edge door cabins and curved metal canopies. | [obs] photos |
| Domestic-garage stations | T1/T2/T3: long glazed platform enclosures with platform-door cabins under a single-pitch metal roof on X-braced steel struts, and a dark ribbed-metal stair/elevator tower. The ring guideway is a concrete trough with a side walkway and lamp posts; the roadway viaducts below stand on large cylindrical columns with drum capitals. | [obs] Famartin 2025-08-12 photo |
| Maintenance facility | 24-hour control room, five service bays, a test track, and a two-level employee parking structure | [pub] fact sheet |

---------------------------------------------------------------------------------------------------------------------

## 10. Deviations of the current 3-D model (`js/live/airport.js`, not edited)

| Item | Current model | Evidence |
|---|---|---|
| Central garage | flat block 22 m | 81 ft (24.7 m) overall, 5 levels, a 61-m central void with helix, 3 AirTrain stations at Level 5 |
| Garages A / G | 21 m | 9 levels, AirTrain at Level 7; height unresolved, 25–36 m |
| LTP Garage 1 | 16 m | DOF 86–91 ft tops; at least 5 levels; 3 corner helixes |
| LTP Garage 2 | 16 m | 6 levels × 12 ft, giving a 60-ft (18.3 m) roof deck plus PV canopies |
| Rental Car Center | 26 m | 66 ft (20.1 m), 5 levels |
| Grand Hyatt | 38 m block extruded from the whole polygon | 12 stories, about 44 m provisional; crescent tower plus podium, not one block |
| CAC | 20 m | 4 × 15 ft, about 64 ft (19.5 m); bent bar |
| Superbay | 34 m flat block | 135 ft (41.1 m) at the spine; cantilevered roofs falling to the doors; 4 bays |
| AirTrain guideway | deck at 9.0–10.6 m, columns every 45 m on the polygon outline | 50 ft at the extension; stations at garage Level 5/7. Pier spacing and heights not yet measured. |
| AirTrain stations | glass box 7.5–13 m | station levels as above; canopies |
| United MOC | missing | large hangar block, 116–132 ft; barrel-vault hangars |

---------------------------------------------------------------------------------------------------------------------

## 11. Conflicts (also in the spec)

1. **AirTrain height:** "35 to 40 ft at its highest point" (RADP IS), against the extension "50 ft above a public
   roadway" and the station levels.
2. **AirTrain length:** 5 mi (2003), against over 6 mi (2021), against "three miles" (Wikipedia, route).
3. **Central garage capacity:** 7,000 (1981), 6,459 (2018) and 6,460 (2025). The capacity changed over time.
4. **LTP Garage 2:**
   - floor area 1.19, 1.2 or 1.25 M sq ft;
   - 3,600, 3,500 or 3,000 net stalls;
   - completed 2019 (ENR) or 2020 (EIR).
5. **Grand Hyatt:**
   - site 4.2 or 4.7 acres;
   - 22 or 21 suites;
   - associate architect "ED21" or "ED2 International".
6. **Superbay:**
   - built 1969, 1970 or 1972;
   - height 140 ft or DOF 135 ft;
   - footprint 250,000 sq ft, against 420,550 sq ft total and 238,970 sq ft for the polygon.
7. **CAC floor area:** 135,000 or 136,000 sq ft.
8. **Garages A/G height:** NAIP 34–36 m, against about 25–30 m from the level view.
9. **LTP Garage 1:** the NAIP scan gives 37 m, against the DOF 86–91 ft. The North Field lean is not calibrated.
10. **SFO Museum A/G station names** are swapped in the newer duplicate polygons.

## 12. Open questions and what would close them

1. **Heights** for Garages A/G, the Grand Hyatt, LTP Garage 1 and the CAC: roof deck, parapet and tower tops. Also what
   "81 ft" (Central) and "66 ft" (RCC) measure.
   - Ask SFO Planning & Environmental Affairs or SFO GIS for building data. SFO Museum already imports "sfogis"
     geometry.
   - Or use the as-built drawings.
2. **FAA OE/AAA NRA filings** for the hotel (about 2016–17), LTP Garage 2 (about 2017), the CAC (about 2016) and the
   AirTrain extension (about 2017–19). They give surveyed AGL/AMSL. The ASNs are needed because public search covers
   only about the last 12 months.
3. **Case 1986.638E Master Plan EIR addenda** (2015–2019) for the hotel, LTP 2 / AirTrain extension and CAC. SF
   Planning can supply them.
4. **Garage A/G level numbering:** are they split levels?
5. **LTP Garage 1:** levels and roof-deck height.
6. **Grand Hyatt:** floor-to-floor heights, parapet and penthouse heights, and the tower-versus-podium outline.
7. **Superbay:** roof section (spine against edge heights), door widths and heights, and which faces carry doors.
8. **United MOC:** building identities, footprints and heights, and door sizes.
9. **AirTrain:** deck width, parapet height, pier spacing and height profile. Sources: the Parsons Brinckerhoff 2003
   drawings, or photogrammetry.
10. **NAIP lean calibration** in the North Field and East Field frames, using DOF poles as in the ITB study. This would
    make the roof-shift scans usable there.
11. **Central garage exterior facade.** The outer walls are hidden behind the roadways and the AirTrain ring in the
    photos found. Interior photos show waffle/joist slabs, board-formed walls and lettered areas ("Area C, Level 3").
12. **Roof-deck occupancy rule** for the procedural cars. The counts are one Monday lunchtime (±30 %); the owner should
    choose the rule.

## 13. Reproduce

```bash
python3 tools/buildings/landside_naip_measure.py   # ~1 min: footprints, DOF, roof-shift scans, roof cars, MOC, AirTrain
python3 tools/buildings/build_spec_landside.py     # -> tools/buildings/spec_landside.json (asserts all source ids exist)
python3 tools/buildings/landside_fetch.py URL NAME # re-download a source into refs/cache/buildings/landside/src/
```

---------------------------------------------------------------------------------------------------------------------

## Verification

Adversarial fact-check, 4 Nov 2026 (section 14 of this note). I re-fetched every cited source I could reach and tried
to refute each key height, dimension, date, level count, roof form and footprint. Where I could, I used a *different*
method from the one above.

- **Tools.**
  - `tools/buildings/landside_verify.py` writes `out/buildings/landside/verify/verify.json` plus QA crops with NAIP
    pixels (local only), offline from the caches:
    - `dof`: FAA DOF on a newer edition, DOF.CSV of 2026-11-03;
    - `fp`: footprints re-computed with shapely;
    - `shift2d`: a 2-D roof-shift scan;
    - `drums`: helix-drum facade bands;
    - `shadow`: north shadows on grade, with a NOAA solar ephemeris;
    - `superbay`: roof rhythm;
    - `text`: the quotes re-read.
  - `tools/buildings/landside_verify_apply.py` writes the verdicts and corrections into the spec. Since
    `build_spec_landside.py` now calls it, a rebuilt spec keeps them; I checked that rebuild + apply is byte-identical
    and idempotent.
- **Sources.** 43 re-fetched to `refs/cache/buildings/landside/src/verify_*`, recorded in `SOURCES.json` there. The 13
  SFO Museum Who's On First records are in `refs/cache/buildings/landside/verify/wof/`.
- **Not touched.** Nothing in `js/` or `data/`. Nothing committed.
- **Not reachable.** The Commons API returned HTTP 429, so the 13 photo licences were **not re-checked**. The Buehler
  page now returns a script shell, and the scanned CAC NOD PDF has no text layer.
- **Fix to `landside_fetch.py`.** It now falls back to `pdftotext` when PyMuPDF is missing.

**Verdicts.**

| Verdict | Meaning |
|---|---|
| CONFIRMED | An independent check agrees. |
| PLAUSIBLE | Consistent, but not pinned tighter. |
| DISPUTED | An independent check conflicts with it. |
| CORRECTED / REFUTED | Shown wrong. |
| STILL UNKNOWN | No source or measurement settles it. |
| NOT RE-CHECKED | The source was unreachable. |

**Tally in the spec** (130 values):
- 84 CONFIRMED, 18 of them with a qualifier (number only, as published, conflict stands, or the definition disputed);
- 2 PLAUSIBLE;
- 4 DISPUTED, 6 CORRECTED and 1 REFUTED;
- 1 STILL UNKNOWN and 28 NOT RE-CHECKED (roof-car counts, photo-based facades, identities);
- 4 new.

### 14.1 Claim by claim (the key ones; every value carries its record in the spec)

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Central garage "five-level, 81-foot-tall", 3,680,000 sq ft, 6,460 spaces (DEIR p. 2-34) | **CONFIRMED** (number); definition still unknown | Re-read in the DEIR, its table ("Building 195 3,680,000") and the NOP. NAIP cannot test it: elevated roadways ring the garage, so no shadow falls on grade, and the 2-D scan is weak (best 5 m toward 143°). |
| 2 | Central garage opened 1981; "an earlier garage stood 1963–1981" | **CORRECTED** | RADP Historic Resources Evaluation (in the appendices): Building 195 "Years constructed: 1963–1981". The first section (Edward B. Page / Gould & Degenkolb, 1963–65, four floors over about the eastern third) "was partially demolished and absorbed by the later phases". "Following the completion of the central parking garage in 1980". App. A Build Year 1974. SFO Museum "1981~" is approximate. **It is one phased building, not a replacement.** |
| 3 | Central void "200 feet in diameter"; outline hole 58.9 m | **CONFIRMED** | D+B re-read. shapely: area-equivalent 58.74 m, minimum enclosing 58.96 m, centre (−930.8, 275.5). |
| 4 | Garages A/G "nine-level", AirTrain from Level 7, 8'2" | **CONFIRMED** | Tutor Perini ("the $60 million, nine-level concrete parking garage"; singular, for the 3,200 spaces of both) and flysfo re-read. App. A: Buildings 95 / 495, 2000. |
| 5 | Garages A/G height 25–36 m; "about three levels above the AirTrain → roof ~25–30 m" | **DISPUTED** (the 25–30 m reading); deck still unknown | New, independent measure. NAIP leans these roofs due east (2-D scan: Garage A best (13.0, 0) m). The ribbed **west facade of each helix drum** is therefore imaged as a band from the outline (a flysfo ground trace; the drum base lies on it, `drums.jpg`) to the drum's top ring. Bands: **13.25 m** (A, 45 rows) and **12.0 m** (G, 57 rows). k = 0.334 / 0.319 from the ITB high-mast-pole model, used **inside** its calibrated x range (−1622…−1346; drums at x −1530 / −1585). **Drum tops 39.6 m (A, IQR 38.9–40.2) and 37.6 m (G, IQR 37.6–39.9), ± about 2 m.** The roof deck can be lower than the drum crown ("arched openings at the top"), but not the drum. For G, the 2-D scan does not reproduce the 12.0 m east peak as a 2-D maximum. |
| 6 | LTP Garage 1: DOF 86 / 91 ft; levels ≥ 5; the NAIP scan "not usable" (37 m) | DOF **CONFIRMED**; scan **CORRECTED**; levels **PLAUSIBLE** | DOF 1A unchanged; grade 9–12 ft AMSL. **North-end parapet by shadow: 15.9–16.8 m.** The shadow runs 5.25 m from the outline along the shadow direction. The outline is a ground trace there: the roof edge is imaged −2.75 m along u, against −2.79 m predicted from the 5.5-m east lean. So the DOF points are about 10 m higher elements. Lean = 5.5 / 16.5 = **0.33 per m**, against 0.14 from the extrapolated ITB model. The model, not the garage, made the 37 m. A roof at Level 5 fits (4 storeys of about 3.8 m plus a parapet). |
| 7 | LTP Garage 2: 6 levels, 12-ft floor height, 3,600 stalls, completed 2020, "four seismically isolated structures" | levels / height / stalls / date **CONFIRMED**; structures **CORRECTED** | DLR, ENR, DBIA, Langan and the DEIR footnote re-read. DBIA says "**seismically separated** structures", with no count; "isolated" is in no source. "Four" rests on the Buehler page alone, now unreadable: [unverified]. New: DLR "Louvered towers at three corners". The 60-ft roof deck is not settled by NAIP: the outline's north edges lie 1.75–3.25 m outside the imaged roof, where the 1.8-m lean predicts 0.5 m. |
| 8 | RCC "66-foot-tall", 1,488,000 sq ft, 2,485 stalls, Building 780 | number **CONFIRMED**; as a roof height **DISPUTED** | DEIR p. 2-36 re-read. The FAA DOF 1A survey (±3 ft) puts the roof outline at **54 ft (three points) and 59 ft (one)**, so 66 ft is 7–12 ft above the surveyed edge. Read it as the tallest element. |
| 9 | RCC "NAIP 19.5 m agrees with 66 ft" | **REFUTED** | The 3.0-m peak was the third strongest; the 2-D scan ranks (8.5, 2.5) m and (5.5, 1.0) m first. k = 0.154 is the ITB model extrapolated 600 m west, where it fails (item 6, item 12). |
| 10 | RCC DOF points "NE, W and SW corners" | **CORRECTED** | All four lie on the **west (AirTrain) side**: −35203 near the SW corner, −35204 mid-west, −35205 west, −35329 NW. None is at the NE corner. Missed: 06-035328 BLDG **34 ft** 1A, 1.5 m outside the SE part. |
| 11 | Build years: LTP 1 1997, RCC 2000 | **DISPUTED** | RADP App. A Build Year (= completion): Building 795 **1994**; 779 / 780 / 782 **1998**. SFO Museum: "1997~" and "2000~", approximate. |
| 12 | CAC height "about 64 ft (60–66)"; NAIP scan 28.6 m | 64 ft **CONFIRMED within ±1.5 m**; 28.6 m **REFUTED** | North shadows on grade (edges 1, 2, 5) run 5.75–6.0 m. With cot e = 0.313–0.33 (the sun cannot pass 72.59° that day), **h = 17.4–19.2 m**. The outline is a ground trace there: the roof edge is imaged −2.25 to −2.75 m along u, against −1.7 to −2.6 m predicted from the 5.5-m east lean (`ov_cac.jpg`). That fits 4 × 15 ft = 18.3 m plus a parapet. The lean is 0.30 per m here, not the model's 0.19. |
| 13 | CAC: 4 stories, 15-ft floor-to-floor, 135,000 (136,000) sq ft, Phase II addendum | **CONFIRMED**; area conflict gone | Cavagnero, P&W, Webcor and MCK re-read. P&W now also shows 135,000. DEIR fn. 45 re-read (Case 2019-006583ETM, 17 May 2021). New: Phase 1 = **Building 674**. Phase 2 (demolition of Building 676, the former Design & Construction building) was "anticipated to begin in 2025". |
| 14 | Grand Hyatt: 12 stories, 4th-floor lobby, opened 7 Oct 2019, 351 rooms, Building 55 | **CONFIRMED** | DBIA, Webcor, AGA, SF Chronicle, the 2019 release and the DEIR re-read. The site conflict 4.2 / 4.7 acres stands (Webcor also says 4.7). |
| 15 | Grand Hyatt provisional 44 m (40–48) | **STILL UNKNOWN** | The SFO Museum outline (src sfomuseum) is **not a ground trace of the slab**. It covers the west crescent and podium; the slab's white PV roof lies largely east of its concave edge (`z_hyatt.jpg`). The slab's north shadow falls on the station and the elevated roadways. |
| 16 | Superbay: Building 1060, 1969–72, four bays, six office levels, 120 ft inside, DOF 135 ft | **CONFIRMED** | Weitz, Deep3DS, the SFO Museum negative (12 Jun 1970) and the DEIR re-read; App. A Build Year 1969. DOF: action **C**, JDATE **2011356**, not the 2013 batch. The point sits on the ESE edge of the spine near its SSW end (a = +17.9, b = −58.9 m). |
| 17 | "cantilever over 230 feet from the center" → "≈70 m each, 165.9 = 2 × 70 + spine" | quote **CONFIRMED**; decomposition **REFUTED** | 230 ft is measured **from the centre**, so tip to tip is ≥ 140.2 m. NAIP (rectified roof, `sb_rect.jpg`): roof 165 m along a (±82.5 m = 271 ft from the centre line); **spine 32 m** (not 25–30); about 66.5 m (218 ft) beyond the spine on each side. |
| 18 | Superbay layout "each side split into two bays of ~67 m" [inf] | **CORRECTED** (roof form) | NAIP shows each cantilever side **folded into 8 bays of 17.3 m** along the spine: autocorrelation 17.0 m on both sides (r 0.73 / 0.69), fold spacing 17.4 / 17.5 m. Each bay is a light / shaded pair with darker grey tip panels over about 138 m. **New conflict:** Deep3DS "a cantilever system having **50 foot** wide structural bays" (15.24 m, i.e. 9 bays). Relief displacement cannot stretch the period by 13 %. The two aircraft positions per side do not show on the roof and stay [inf]. |
| 19 | NAIP moment "about 13:25 PDT" for all landside buildings | **CORRECTED** | Frames differ in time. The terminal and North Field frames cast north shadows; the Superbay frame has the sun in the **ESE**: the ESE door facade is imaged as a sunlit 10-m band, and a 5–6 m shadow lies beyond the WNW roof edge (about 10:45–11:35 PDT). NOAA ephemeris for 2024-05-20: maximum 72.59° at 13:06 PDT. Roof-car counts are therefore not one moment. |
| 20 | One NAIP lean model k(x) for the landside scans | **REFUTED** outside its range | The 2-D scan confirms an **east** lean (bearing 90–106°) for Garage A, LTP 1, RCC, Hyatt and CAC, and 317° for the Superbay. The magnitude is not k(x): CAC 0.30 and LTP 1 0.33 per m (items 6, 12) against 0.19 / 0.14 modelled. Each frame has its own nadir. |
| 21 | AirTrain: CX-100 9'3" × 39'6", $430 M, 1,900-ft extension "50 feet above a public roadway", "35 to 40 feet", over 6 miles, 41 cars | **CONFIRMED as published** | Fact sheet, SF-03-10, the 2021 release, PTT ($172 M), Airport World ($259 M), PGH Wong and RADP App. B re-read. Opened 24 Feb 2003 (Wikipedia; SFO Museum station inception 2003-02-24); official opening 3 Mar (release). The rail polygon re-run gives 57,727 m², widths 4.5 / 4.8 / 5.1 / 9.5 / 11.5 m and a 7.8-km (4.9-mi) route, so "over 6 miles" probably counts track miles. |
| 22 | SFO Museum newer A/G station polygons swapped | **CONFIRMED** | WOF geometries: 1729791961 "A" centroid z = +466 (south), 1729791965 "G" z = +240; the newer 1763588569 "(A)" z = +242 and 1763588567 "(G)" z = +469. |
| 23 | Footprints (all nine) | **CONFIRMED** | shapely minimum rectangles and areas equal the research's cv2 values to 0.1 m / 0.1 m². |
| 24 | Parking supply 2018 (A 1,008 + 577, G 1,151 + 254, Central 6,459, LTP 1 3,109) | **CONFIRMED** | App. E.1 re-read. The June 2017 sheet splits A 902 / 683 and G 1,130 / 275, with the same totals. |
| 25 | United MOC DOF 132 / 117 / 116 ft and others; history 1947 / 1948 | **CONFIRMED** (DOF, secondary history) | DOF.CSV 2026-11-03 positions listed in the spec; PCAD and AirlineReporter re-read. |
| 26 | 13 reference-photo licences | **NOT RE-CHECKED** | Commons API HTTP 429 on 2026-11-04. |

### 14.2 New facts found

| Fact | Value | Source |
|---|---|---|
| Central garage construction history | first section 1963–65 (Edward B. Page / Gould & Degenkolb), enlarged 1969–81 by the San Francisco Airport Architects; completed 1980–81; App. A Build Year 1974 | RADP HRE (appendices) |
| Garage A / G helix-drum tops | 39.6 m / 37.6 m (± about 2 m) | NAIP west-facade band ÷ ITB pole k [obs] |
| LTP Garage 1 north-end parapet | 15.9–16.8 m | NAIP shadow [obs] |
| CAC parapet | 17.4–19.2 m | NAIP shadow [obs] |
| CAC building numbers | Phase 1 = 674; Building 676 = former Design & Construction building, to be demolished for Phase 2 (start anticipated 2025) | DEIR |
| CAC floor plate vs outline | 135,000 sq ft / 4 = 3,135 m² per floor, against a 4,752 m² outline | arithmetic |
| Superbay spine | 32 m wide | NAIP [obs] |
| Superbay roof rhythm | 8 bays of 17.3 m per side, against "50 foot wide structural bays" (Deep3DS) | NAIP [obs] / [pub] |
| RCC DOF 34-ft building | 06-035328, 1.5 m outside the SE part | DOF |
| LTP Garage 2 | louvered towers at three corners | DLR |
| NAIP 2024 frames | not one time: the Superbay frame is a morning frame | NAIP |

### 14.3 Changes made to `spec_landside.json`

- **Verification records.** Every value now carries one: `{verdict, evidence, date}`.
- **Corrections.** Each keeps the previous fields in `corrected.old`, with the reason:
  - `naip_epoch`: not one moment.
  - `cg_built`: now 1963–1981, phased.
  - `ltp1_built`: range 1994–1997.
  - `rcc_built`: range 1998–2000.
  - `rcc_height_check`: withdrawn; it now carries `parapet_dof_m` 16.46–17.98.
  - `rcc_dof`: positions corrected and the 34-ft point added.
  - `garage_a_height` / `garage_g_height`:
    - `drum_top_m` 39.6 / 37.6;
    - range 25–41.5 / 25–40.
  - `ltp1_scan`: lean 0.33 per m; model invalid here.
  - `ltp2_structure`: "separated", count [unverified], louvered towers.
  - `cac_height`: range 17.4–19.5 and `shadow_obs_m`.
  - `sb_layout`: spine 32 m, 8 × 17.3 m roof bays, 66.5 m beyond the spine; tag inf → obs.
- **New values:** `sb_roof_bays_obs`, `sb_structural_bays_pub`, `ltp1_parapet_obs`, `cg_first_section`.
- **New source:** `verify`.
- **New conflicts:** 5.
- **New open questions:** 3.

### 14.4 What would settle the open points

1. **Garages A / G roof deck.** An SFO drawing, or the station platform elevation at Level 7. On NAIP, a free deck edge
   on the west, or a north shadow on grade, would do; the north sides border elevated ramps.
2. **The RCC's 66 ft.** What the DEIR measures: the station tower or canopies. The DOF settles the parapet.
3. **Grand Hyatt.** A ground outline of the slab (SFO GIS), or the FAA OE/AAA filing.
4. **Superbay bays.** A drawing or a scaled photo: are the 17.3-m roof folds the structural bays?
5. **Photo licences.** Re-run the Commons check when the API is not rate-limited.
6. **Lean per frame.** The frame nadirs (NAIP 2024 frame metadata) would turn every east shift into a height.

Reproduce:
```bash
python3 tools/buildings/landside_fetch.py URL verify_<source id>.(pdf|html)   # for each source in the spec
python3 tools/buildings/landside_verify.py all   # ~15 s: dof fp shift2d drums shadow text superbay qa apply
```
