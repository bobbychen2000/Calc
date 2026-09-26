# International Terminal (ITB), Boarding Areas A and G: dimensions and evidence

Research note, 26 Sep 2026. It feeds the 2-D drawing stage (plans and elevations drawn to verified dimensions) and,
after the owner's review, the 3-D build.

- **Structured spec:** `tools/buildings/spec_itb.json`, written by `tools/buildings/build_spec_itb.py`. It holds 65
  items. Each item carries a value, a unit, a tag, source ids, a confidence and a status.
- **Measurements:** `tools/buildings/itb_naip_measure.py` writes `itb_naip_measurements.json`, and
  `tools/buildings/itb_photo_skyline.py` writes `itb_photo_skyline.json`.
- **Local files:**
  - Source pages, drawings and photos are cached in `refs/cache/buildings/itb/`, which is gitignored.
  - QA overlays that contain imagery are in `out/buildings/itb/`, which is local only.
- **Not touched:** nothing in `js/` or `data/` was edited, and nothing was committed.

**Legend.**

| Tag | Meaning |
|---|---|
| **[pub]** | Published by an original source: the architect, engineer, contractor, FAA, SF Planning or contemporary press. |
| **[obs]** | Measured by me on public data: NAIP 2024, FAA DOF geometry, a public-domain photo or the SFO Museum footprints. The method is stated. |
| **[inf]** | Derived by stated arithmetic from [pub] or [obs] values. |
| **[unverified]** | The original could not be read, or no source exists. |

"First-hand" means I read the document itself. "Snippet" means the site blocked automated access, so only
search-engine extracts of it were read.

**Spec status values.**

| Status | Meaning |
|---|---|
| `verified` | Read first-hand in at least one source, or measured by me. |
| `snippet-only` | Every source was read only as extracts. Applies to the 160 ft cantilever, the truss length (320 ft), the centre section (180 ft), the truss depth (29 ft), the 20 columns and the steel fabricator. Independent extracts agree. |
| `secondary-only` | Known only through Wikipedia. |
| `conflict` | Sources disagree. |
| `unverified` | No readable source. |

---------------------------------------------------------------------------------------------------------------------

## 0. Summary

1. **The hall roof is about 40 m above ground, not 25 m.**
   - The FAA Digital Obstacle File (DOF) surveys two roof tops of the hall:
     - 06-035315: 131 ft AGL / 139 ft AMSL;
     - 06-035316: 132 ft AGL / 140 ft AMSL.

     Both are accuracy class 1A (±20 ft horizontal, ±3 ft vertical) and verified [pub].
   - The two points lie on the west eave over the column pairs, 115.5 m apart.
   - The current model (`js/live/terminals.js` `greatHall()`) tops the roof at "83 ft". Where that number was traced, it
     belongs to the *interior* great-hall height ("705 × 210 ft, up to 83 ft high"), and I could not verify it
     first-hand.
   - SOM and Enclos publish "Building Height: 144 feet", but neither states the datum [pub, conflict].
2. **The published roof structure** comes from four sources: SEAONC and AISC Modern Steel Construction (Feb 2000),
   both read only as snippets, plus Smith-Emery and SOM, read first-hand. They state:
   - five sets of balanced double-cantilever steel trusses (three-chord "football" trusses), linked by bowstring trusses
     into one wing-shaped roof;
   - a 380 ft centre span and 160 ft end cantilevers, 860 ft overall;
   - trusses up to 29 ft deep and up to 320 ft long, with a 180 ft central section;
   - 20 columns rising from the level-3 departures floor;
   - a roof "soaring 60 to 90 ft above the floor" [pub].

   Only one split of the length satisfies all of these at once [inf]:

   ```
   20 | 140 | col | 80 | col | 100 | 180 | 100 | col | 80 | col | 140 | 20 ft
   ```

   The column lines therefore sit at ±190 ft and ±270 ft from the centre (±57.9 m and ±82.3 m).
3. **NAIP 2024, measured with relief displacement calibrated on FAA DOF poles [obs]:**

   | Quantity | Value |
   |---|---|
   | Roof axis heading | **162.85°**, rotated 2.9° from the SFO Museum hall axis the model uses |
   | Relief-corrected roof centre | **(−1245.0, 364.7)** |
   | Roof size | **252.7 m × 65.4 m** (829 × 215 ft) |
   | Truss / skylight lines | **5**, spaced **12.12 m** (39.8 ft, the published 40 ft grid) |
   | Centre-section skylights | 5 lens-shaped, **48.4 m** long and up to 9.6 m wide |
   | Glazed canopy bands at the tips | **18.8 m** (N) and **15.8 m** (S) deep |

   - The NAIP length is **9 m shorter than the published 860 ft**. This is unresolved and flagged as a conflict.
4. **Wing-roof height profile [obs]**, from two independent measurements: the NAIP eave relief and a public-domain
   frontal photo. Heights are anchored to the DOF tops.

   | Location | Height AGL |
   |---|---|
   | Humps, \|u\| 60–75 m over the column pairs | **40.1 m** |
   | Notches where the wings meet the centre section, \|u\| ≈ 27 m | **35.7 m** |
   | Glazed centre crown | **≈ 40 m** |
   | Tips | **≈ 34.9 m** |

   Each value is ±1.5–2 m. The shape is the "two wings and a crown" silhouette seen in every landside photo.
5. **Piers [obs, low confidence]:**
   - Boarding Area A's main roof is **about 17 m** above the apron (±2.5 m, from NAIP relief and shadow). Its first
     raised pod reaches **85 ft (25.9 m) AGL**, which is DOF 06-035352 [pub].
   - Boarding Area G's roof is about 17 m (±3 m).

   No published pier height was found. The model uses 14.6 m.
6. **The 2026 roof is not the roof in the imagery.** An envelope upgrade ran from the ceremony on 27 Jun 2024 to early
   or mid 2026 [pub]. It added:
   - a new membrane;
   - about 1,400 kW of rooftop PV;
   - a new facade access system;
   - repairs to the expansion joints and mullion caps.

   NAIP was flown on 2024-05-20, before the works. The layout of the PV is **unverified**.

---------------------------------------------------------------------------------------------------------------------

## 1. Sources

| id | Source | What it gave | Read |
|---|---|---|---|
| som | SOM project page, https://www.som.com/projects/san-francisco-international-airport-international-terminal/ | completed 2000; design finished 1995; site 1,000,000 sq ft; **height 144 ft**; 5 stories; 1,800,000 sq ft; collaborators (Del Campo & Maru and Michael Willis Architects as JV design partners; Tutor-Saliba, Perini, Buckley; OLMM); "double-cantilevered trusses linked by bowstring trusses"; "elongated skylights and clerestories"; base isolation | first-hand (`som_project.html`) |
| som_sketch | SOM image `sfairport_1400x800_plan_01jpg.jpg` (Hartman concept sketches, © SOM) | "Main roof: 866' × 260'"; "columns spaced on 40' E/W grid by 80' N/S column bays"; roof elevation with two humps and a small crown; "roof plane is opened with glass along major truss lines"; west-wall frit bands | first-hand, reference only |
| som_section | SOM images `sfia_1575x900_som_02/03` (© SOM) | section at the ticket counter; perspective section showing 5 inverted-triangle (three-chord) trusses, each with a column and a ridge skylight | first-hand; perspective, not to scale |
| sfom_sketch | SFO Museum 2000.086.009, Hartman roof-plan sketch, 1995 | column grid letters B–J, skylights, "3-D trusses" (developmental) | first-hand |
| msc2000 | Ferch & Hassett, "S.F. Airport Roof Truss Erection", *Modern Steel Construction*, Feb 2000, https://www.aisc.org/globalassets/modern-steel/archives/2000/02/2000v02_sf_airport.pdf | 860 ft wing-like roof "soaring 60 to 90' above the floor"; five sets of double-cantilever trusses up to 320 ft on spherical bearings; 180 ft centre section jacked up to 60 ft; assembled at Mare Island and shipped in ~35 pieces; Herrick Corp. | **snippet**: Cloudflare 403, and the Scribd copy was blocked |
| seaonc | Hensolt SEAONC Legacy Project, https://legacy.seaonc.org/structure/sfo-international-terminal/ | 5 sets of balanced double-cantilever trusses with a central trussed span; up to 29 ft deep; 380 ft centre span; 160 ft end cantilevers; 860 ft overall; **20 cantilevered columns from the 3rd-floor departures level**; 26 new gates; (attributed) "great hall 705 ft × 210 ft, up to 83 ft high" | **snippet**: sgcaptcha |
| smith_emery | https://www.smithemery.com/staging/4272/projects/san-francisco-international-airport-roof-truss-system-san-francisco-california/ | 860 ft wing-like roof, 60–90 ft above the floor; "three-chord 'football' shaped trusses"; double-cantilever trusses carry the centre span | first-hand |
| sfgate2000 | D. Armstrong, SF Examiner, 30 Jan 2000, https://www.sfgate.com/business/article/SFO-terminal-ready-to-take-wing-3077658.php | "100-foot-high terminal roof"; roof span 380 ft; ticket lobby 700 ft; 5 stories; **L1 services/baggage, L2 arrivals, L3 departures, L4–5 offices and lounges**; front glass with three layers of ceramic frit; cherry-wood back wall; bamboo 55 ft; 2.5 M sq ft with concourses | first-hand (`sfgate_3077658.html`) |
| enclos | https://enclos.com/project/san-francisco-international-airport-international-terminal/ | "unitized curtainwalls spanning over 60´ for the vertical exterior end walls of the roof structure"; 267 friction pendulum isolators; height 144 ft | first-hand |
| tutor_itb / tutor_bag | Tutor Perini project pages (ITB; Boarding Area G) | ITB: 1.8 M sq ft, 5 levels, 382,000 sq ft of metal and glass cladding. BA G: 380,000 sq ft, three stories, six double-gated two-level gate rooms, composite aluminium panels plus tinted curtain wall, architect Robin Chiang & Co., completed 1999 | first-hand |
| ags_baa | https://www.agsinc.com/projects/sfo-gate-enhancement | BA A: 23 boarding bridges at A1–A15 replaced; A6 set up for a 3-bridge A380; completed 2020 | first-hand |
| airportworld25 | https://airport-world.com/sfos-international-terminal-celebrates-25th-anniversary/ | ribbon cutting 10 Dec 2000; ground broken Oct 1995; renamed for Sen. Feinstein 16 Jan 2024; roof and exterior project due mid-2026 | first-hand |
| webcor_roof, webcor_ceremony, ftf_roof, ai_roof | Webcor, FTF Engineering, Airports International | roof upgrade: membrane, ~1,400 kW PV, facade access, mullion caps, expansion joints; ceremony 27 Jun 2024; $75 M; 4 phases of west-facade scaffolding; "scaffolding reached 90 feet high" | first-hand (ai_roof: snippet) |
| radp_nop | SF Planning Case 2017-007468ENV, RADP NOP (May 2019), https://sfmea.sfplanning.org/2017-007468ENV_SFO_RADP_NOP.pdf | "levels two (arrivals) and three (departures) of the ITB"; planned western expansion of the Main Hall (~140,000 sq ft); bump-outs on A and G; curbside expansion | first-hand (`radp_nop_*.pdf`) |
| wiki_sfo | Wikipedia, SFO article | A1–A15 and G1–G14; BA G by HOK with Robin Chiang & Co. and Robert B. Wong (built by Tutor Perini); BA A by Gerson/Overstreet (built by Hensel Phelps). It cites the flySFO "Fact Sheet – International Terminal" (2007) | secondary; the fact sheet could not be fetched because web.archive.org was refused |
| dof | FAA DOF, DAILY_DOF_CSV.ZIP (DOF.CSV 2026-09-18), already in `refs/cache/lighting/` | roof tops 06-035315/-316; A-pier pod 06-035352 (85 ft); high-mast poles 06-035353…57 (153–157 ft) and apron pole 06-034826 (108 ft) used for calibration | first-hand; extract in `refs/cache/buildings/itb/dof_itb_area.json` |
| naip | USDA NAIP 2024 world raster (public domain), `refs/cache/naip/` | every [obs] plan measurement | first-hand |
| photos | Wikimedia Commons "Category:International Terminal (San Francisco International Airport)" | 24 files listed in `spec_itb.json` `photos[]` with author, licence and use; 13 were reviewed | see §6 |

**Searched without result:**
- an SFO Airport Layout Plan building table;
- an ITB EIR with heights (the 1992 SFO Master Plan FEIR is not online);
- flySFO pages (they returned the site's error page);
- the RADP Draft EIR (CEQAnet lists only the NOP);
- OpenAerialMap and lidar (none, per `imagery.md`).

The Google screenshots cover the ITB only at about 1 m/px, and map overlays hide the roof. I did not use them.

---------------------------------------------------------------------------------------------------------------------

## 2. Main hall roof

### 2.1 Published structure [pub]

- **Form:** "A series of double-cantilevered trusses linked by bowstring trusses support the roof" (som).
  - "five sets of steel balanced double cantilever trusses with a central trussed span linked together creating a
    continuous wing-like form" (seaonc, snippet);
  - "three-chord 'football' shaped trusses" (smith_emery).
  - The perspective section (som_section) shows each truss line as an inverted triangle with a pitched skylight ridge
    and a column beneath it.
- **Numbers:**

  | Quantity | Value | Sources |
  |---|---|---|
  | Overall length | 860 ft | msc2000, seaonc, smith_emery |
  | Centre span | 380 ft | seaonc, msc2000, sfgate2000 |
  | End cantilevers | 160 ft | seaonc, msc2000 |
  | Truss length | up to 320 ft | msc2000 |
  | Centre section | 180 ft | msc2000 |
  | Truss depth | up to 29 ft | seaonc, msc2000 |
  | Columns | 20, "cantilevered", rising from the level-3 departures floor | seaonc |
  | Concept dimensions | "Main roof: 866' × 260'"; "40' E/W grid by 80' N/S column bays" | som_sketch |

- **Heights:**
  - "soaring 60 to 90' above the floor of a cavernous ticketing hall" (msc2000, smith_emery). The surface meant, top
    or underside, is not stated.
  - "100-foot-high terminal roof" (sfgate2000).
  - DOF roof tops at 131 and 132 ft AGL (§2.4).
- **Rhythm [inf].** Only one split satisfies all the numbers:
  - 160 + 80 + 380 + 80 + 160 = 860;
  - a truss of 140 + 80 + 100 = 320;
  - a centre section of 380 − 2 × 100 = 180.

  This implies a 20 ft roof overhang beyond each truss end, with column lines at ±190 and ±270 ft from the centre. The
  20 columns are 5 truss lines × 2 trusses × 2 columns.

### 2.2 NAIP relief calibration [obs]

NAIP is orthorectified to terrain, so roofs lean away from the frame nadir. See `imagery.md` §6.

**Calibration poles.** I calibrated the lean on five FAA-surveyed high-mast poles west of the ITB, 153–157 ft AGL. Each
pole's luminaire ring is imaged 14.7–18.3 m east of its surveyed foot:

| Pole | Height | Ring shift | k (m per m of height) | Ring pick |
|---|---|---|---|---|
| 06-035353 | 157 ft | 18.30 m | 0.382 | automatic |
| 06-035354 | 157 ft | 18.03 m | 0.377 | automatic |
| 06-035355 | 153 ft | 16.88 m | 0.362 | by eye |
| 06-035356 | 154 ft | 16.00 m | 0.341 | automatic |
| 06-035357 | 156 ft | 14.65 m | 0.308 | by eye |

- The fitted model is **k(x) = 0.7553 + 0.0002753·x**, with a scatter of 0.002. The shift direction is 87–95°, due
  east.
- At the ITB, k = **0.418**. At Boarding Area A it is 0.415, and at Boarding Area G it is 0.364.
- **Independent check.** The model predicts k = 0.551 at the tower. The tower cab lean in `imagery.md`, 38–40 m, then
  implies a height of 69–73 m, against a DOF top of 74.7 m that includes appurtenances.
- **Frame geometry.** The slope implies H − h ≈ 3,630 m and a nadir about 2.7 km west of the ARP. An elevated plane is
  magnified by about 1 % at 35–40 m, and I remove that from every length.
- **Sun.** The shadow of apron pole 06-034826 (108 ft) points to azimuth 6.6° and is 10.4 m long. The sun was therefore
  at azimuth ~187° and elevation ~72.4°: local noon on 2024-05-20.
- **Error budget.** The DOF 1A horizontal tolerance (±6 m per foot) is the largest single-pole error. The consistency
  of the five poles and the tower suggests the real error is well below that.

### 2.3 Plan measurements [obs]

The tool works in a frame rotated to the roof: u runs along the axis (+ toward Boarding Area A), v across (+ toward
ENE). It samples at 0.25 m. QA images: `out/buildings/itb/qa_roof_frame.png` and `qa_planform_world.png`.

- **Axis.** The glazed tip edges and the lens row are perpendicular to the axis.
  - Heading: **162.85°**.
  - The straight west facade-base line confirms it: standard deviation 0.61 m over 182 rows, tilt 0.002.
- **Length.**
  - Fascia to fascia, as imaged: 255.25 m.
  - Relief-corrected: **252.7 m (829 ft) ± 1.5 m**.
  - Published: 860 ft = 262.1 m. The **conflict** is open: perhaps the chord is measured along the curve, or steel
    extends beyond the visible fascia.
- **Width.** Eave to eave: **65.4 ± 1 m** (215 ft). The concept sketch gives 260 ft; the unverified hall width is
  210 ft.
- **Truss lines.**
  - Five straight glazed lines, spaced **12.12 m (39.8 ft)**. The comb fit (north half) and the lens centres agree at
    12.25 m as imaged.
  - The outer lines are 48.5 m apart; the roof extends about 8.4 m beyond them on each side.
  - The south half shows *doubled* dark lines about 2.5 m apart. Their origin is unknown; they are not re-roofing,
    because the works started after the flight.
- **Centre section.**
  - 5 lens-shaped glazed skylights, one centred on each truss line.
  - Length **48.4 m**, maximum width **9.6 m**. The published centre section is 180 ft = 54.9 m.
  - Interior photos show them as glazed "basket" trusses.
- **Tip canopies.** Bluish glazed grids across the full width: **18.75 m** at the north tip and **15.75 m** at the
  south. The 3 m difference is not explained.
- **Relief-corrected outline (world x/z, ±1.5 m):**

  | Corner | x | z |
  |---|---|---|
  | NW | −1313.9 | 252.5 |
  | NE | −1251.4 | 233.2 |
  | SE | −1176.2 | 476.9 |
  | SW | −1238.7 | 496.2 |

  - Centre: (−1245.0, 364.7).
  - **Check:** the two DOF roof-top points fall 1.1 m and 0.8 m inside the corrected west eave line. Along the axis
    they sit at u = +54.7 and −60.9 m, on the flanks of the hump plateau (peak at |u| = 67 m, 0.2–0.9 m higher).
  - The SFO Museum hall part is 0.7–5 m wider on the west. It follows the curb structures, not the eave.

### 2.4 Heights and the wing profile

- **DOF [pub]** (ground ≈ 8 ft AMSL at the ITB, from AMSL − AGL):

  | Obstacle | Height AGL | Height AMSL | Position (37° N, 122° W) | u (from roof centre) |
  |---|---|---|---|---|
  | 06-035315 | 131 ft | 139 ft | 37 36 53.77 N, 122 23 22.86 W | +54.7 m |
  | 06-035316 | 132 ft | 140 ft | 37 36 57.35 N, 122 23 24.26 W | −60.9 m |

- **NAIP eave relief [obs].** Along the west side, the oblique west wall appears as a dark band.
  - Its west boundary is straight (v = −43.5 ± 0.6 m), a constant-height line.
  - Its east boundary is the imaged west eave, which wanders east by 0.955·k·h.
  - I fitted an even polynomial in u with a tilt term (RMS 0.20 m in plan) and anchored its peak to the DOF mean,
    40.1 m.

  | \|u\| (m) | 23 | 27 | 31 | 40 | 50 | 60 | **67** | 75 | 85 | 95 | 105 | 115–119 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|
  | eave AGL (m) | 35.8 | 36.3 | 36.8 | 37.9 | 39.1 | 39.9 | **40.1** | 39.9 | 38.9 | 37.3 | 35.5 | 34.4 |

  - The peak at |u| = 67 m lies between the inferred inner (57.9 m) and outer (82.3 m) column lines.
  - A second, noisier method tracks the five skylight lines. It gives a peak at |u| ≈ 76–78 m and the same fall to the
    centre and the tips, with ±2–4 m north/south scatter.
- **Photo silhouette [obs].** Wikimedia Commons `San_Francisco_International.jpg` (DimiCalifornia, 2005, public
  domain) is a near-frontal long-lens view of the west elevation.
  - I read the sky/roof boundary, excluded lamp posts, and scaled it by the NAIP roof length.
  - Perspective is visible: the crown is off-centre and the two tips differ. I therefore use north/south pair means.

  | Feature | Drop below the humps |
  |---|---|
  | Notches | 4.9 m |
  | Tips | 4.6 m |
  | Crown | 0.0 m (the crown is as high as the humps) |

- **Adopted profile [obs + pub anchor]:**

  | Location | Height AGL | Basis |
  |---|---|---|
  | Humps | 40.1 m | DOF |
  | Notches (\|u\| ≈ 27 m) | 35.7 m | NAIP 3.8 m and photo 4.9 m drops |
  | Crown | ≈ 40 m ± 2 m | photo |
  | \|u\| = 100 m | 36.4 m | NAIP |
  | Tips | ≈ 34.9 m | NAIP 5.7 m at \|u\| = 119, photo 4.6 m |

  - **Caveat:** the DOF top may be a skylight ridge rather than the eave. In that case every eave value would drop by
    up to about 1–2 m [unverified].
- **Departures floor (level 3) [inf, unverified]:** 40.1 m − 90 ft = 12.7 m, and 40.1 m − 100 ft = 9.6 m. The
  estimate is **11.5 ± 1.5 m**. No section drawing was found.

### 2.5 Facades [pub]

- **West (front) wall:** full-height glass carrying three layers of ceramic frit (sfgate2000). The concept sketch
  shows bands of translucent patterned frit, clear glass and brise-soleil.
- **Photos** show:
  - clear glazing at curb level, with revolving-door vestibules under a canopy;
  - light fritted panels above;
  - white paired columns at the column lines;
  - the trusses exposed above the wall, with the roof eave overhanging the curb.
- **End walls:** unitized curtain walls spanning over 60 ft (enclos).
- **Back wall:** cherry wood (sfgate2000).
- **Cladding:** 382,000 sq ft of metal and glass in total (tutor_itb).

### 2.6 Roof upgrade 2024–26 [pub]

- The ceremony was on 27 Jun 2024 (webcor_ceremony).
- Scope:
  - a new roof membrane and waterproofing;
  - about 1,400 kW of PV;
  - expansion joints;
  - the window-washing (facade access) system;
  - curtain-wall mullion caps;
  - repairs to exposed-steel corrosion.
- The west facade was scaffolded in four phases (webcor_roof, ftf_roof, ai_roof). Completion was due early or mid 2026
  (airportworld25).
- No open imagery after the works was found, so the PV layout is an open question.

---------------------------------------------------------------------------------------------------------------------

## 3. Boarding Area A

| Item | Value | Tag / source |
|---|---|---|
| Architect / builder | Gerson/Overstreet Architects; Hensel Phelps | [pub] wiki_sfo (secondary) |
| Gates | A1–A15. 23 bridges replaced by 2020; A6 set up for a 3-bridge A380 (AGS). Wikipedia names A11 instead. | [pub] ags_baa, wiki_sfo |
| Footprint | SFO Museum polygon: 339 m along the axis including the connector; body 38.7–38.8 m wide. NAIP imaged roof 36.5 m (by eye, ±1 m). | [obs] |
| Main roof height | **≈ 17 m ± 2.5 m** above the apron | [obs, low] |
| Raised pods | 3 D-shaped pods about 70, 55 and 55 m long (by eye, ±3 m). Pod 1 top **85 ft (25.9 m) AGL / 94 ft AMSL** (DOF 06-035352, 37 36 49.70 N 122 23 20.30 W). Its oblique rim band (2.5–3 m) gives about 7.5 m above the main roof, which is consistent. | [pub] dof, [obs] |

**How the main-roof height was measured.** Two estimates agree:
- The west-side dark band (the oblique WNW facade plus its shadow) is 8.5–9 m wide. It equals (0.873·k + 0.122)·h, which
  gives 17.4–18.4 m, less any roof overhang.
- The imaged roof centre sits 5.85 m from the SFO Museum footprint centre. That offset equals 0.873·k·h, which gives
  15.9 m.

A three-level pier, with an apron level and two passenger levels, supports this height [inf]. OpenStreetMap's 25 m is
unsourced.

## 4. Boarding Area G

| Item | Value | Tag / source |
|---|---|---|
| Architect / builder | Robin Chiang & Co. (tutor_bag); Wikipedia adds HOK and Robert B. Wong. Tutor Perini; completed 1999; $95 M. | [pub] |
| Size and levels | 380,000 sq ft, three stories. Apron: operations, storage and MEP. Level 2: international arrivals, sterile corridor, clubs and in-transit lounge. Level 3: departures concourse and retail. | [pub] tutor_bag |
| Gate rooms | Six double-gated, two-level common-use gate rooms for twelve 747-400s; gates G1–G14 | [pub] tutor_bag, wiki_sfo |
| Exterior | Metallic-finish composite aluminium panels and a tinted energy-efficient curtain wall | [pub] tutor_bag |
| Footprint | SFO Museum body 38.3–38.4 m wide (47 m at the middle pod). NAIP imaged roof about 33.5 m (edges ambiguous). The SFO Museum outline is offset 3–6 m NNE of the NAIP roof, as in `imagery.md` §6 (+4 m). | [obs] |
| Main roof height | **≈ 17 m ± 3 m**. The NNE shadow band plus the SSW facade band measure 4.5–5.5 m, which equals 0.297·h. | [obs, low] |
| Raised pods | 3 lens-shaped pods about 60, 55 and 62 m long. No DOF entry, so their height is unmeasured. | [obs] |

---------------------------------------------------------------------------------------------------------------------

## 5. What the current model gets wrong (for the drawing/3-D stages, not edited here)

| # | Current model | Evidence |
|---|---|---|
| 1 | Roof top at 83 ft (25.3 m) AGL in `terminals.js` `greatHall()`, and `data/sfo_buildings.json` hall h = 25.3 m | DOF 131/132 ft AGL (40 m) |
| 2 | Roof length about 237 m (380 + 2 × 160 + 2 × 12 ft), width about 82 m | NAIP 252.7 × 65.4 m; 860 ft published |
| 3 | Roof on the SFO Museum hall part's axis and centre | axis +2.9°, heading 162.85°, centre (−1245.0, 364.7) |
| 4 | 20 columns as 2 × 10 along the long edges | 5 truss lines × 4 columns at ±190 / ±270 ft |
| 5 | Smooth profile | two wing humps, notches about 5 m lower at \|u\| ≈ 27 m, a glazed crown back at hump height, tips about 5 m lower |
| 6 | No skylights | 5 glazed lines along the trusses, 5 lens skylights in the centre section, glazed canopies about 16–19 m deep at both tips |
| 7 | Piers at 14.6 m | about 17 m, with pods to about 26 m on A |

---------------------------------------------------------------------------------------------------------------------

## 6. Reference photos (reference only; files in `refs/cache/buildings/itb/photos/`, gitignored)

| File (Commons) | Author, date | Licence | Used for |
|---|---|---|---|
| San_Francisco_International.jpg | DimiCalifornia, 2005 | Public domain | west elevation silhouette (measured) |
| San Francisco International Airport, California LCCN2013632177 / …178 (.tif) | Carol M. Highsmith (Library of Congress) | Public domain | west elevation, column pairs, decks, high-mast pole |
| International Terminal of San Francisco International Airport.jpg | Constantine Kulikovsky, 2007 | CC BY 3.0 | frontal west-elevation panorama |
| SFO IT (35656942334).jpg | Elizabeth K. Joseph, 2017 | CC BY 2.0 | curb-level eave, trusses, columns |
| SFO international terminal.jpg | Håkan Dahlström, 2009 | CC BY 2.0 | night view of eave and notch |
| KSFO10.jpg | Vmzp85, 2014 | CC BY-SA 4.0 | approach view with garages |
| 2025-08-12 … View of the G gate side of the International Terminal … | Famartin, 2025 | CC BY-SA 4.0 | interior: column pairs, three-chord trusses, lens baskets |
| SFO INTERNATIONAL TERMINAL 8-9 - panoramio.jpg | Masrur Odinaev, 2010 | CC BY-SA 3.0 | interior panorama |
| SFO view 2008-3 (5299520824).jpg | Bill Larkins, 2008 | CC BY-SA 2.0 | Boarding Area G apron facade |

- **SOM images** (© SOM, the Hartman sketches and sections) and the **SFO Museum sketch** are reference only.
- **Not yet reviewed:** the other files in `spec_itb.json` `photos[]`. Several thumbnails were refused by Wikimedia's
  rate limiter.

---------------------------------------------------------------------------------------------------------------------

## 7. Open questions and unverified items

1. **Original drawings.** Can the owner obtain ITB sections and elevations? Candidates are SFO Bureau of Design and
   Construction record drawings, the 1992 SFO Master Plan FEIR, or SOM. They would fix the level-3 floor, the tip and
   crown heights, and the roof length.
2. **Roof length.** NAIP gives 252.7 m; the sources give 860 ft (262.1 m). The proposal is to draw the NAIP planform with
   the published rhythm scaled to it, and flag the conflict on the sheet.
3. **The 2026 roof.** It has a new membrane and about 1.4 MW of PV, but no open post-2024 imagery exists. Options: wait
   for NAIP 2026, or use owner photos.
4. **Pier heights.** Accept about 17 m (pods to about 26 m) from NAIP, or find an elevation source.
5. **Boarding Area G outline.** The SFO Museum polygon is offset from NAIP by several metres. Should it be re-traced
   from ground-level edges?
6. **Unverified inputs:**
   - The flySFO 2007 ITB fact sheet could not be fetched.
   - The SEAONC and AISC texts were read only as snippets.
   - The "705 × 210 × 83 ft" attribution is unconfirmed.
   - The datum of the "144 ft" height is unknown.
   - The DOF tops may be the eave or the skylight ridges.
   - The gate for the three-bridge A380 operation is A6 per AGS, A11 per Wikipedia.
   - It is unknown whether any RADP ITB project (hall expansion, A/G bump-outs) was built by 2026.
7. **Side note for the AirTrain work.** The SFO Museum data names the two ITB AirTrain stations inconsistently: a "(G)"
   polygon sits on the A side and vice versa (`docs/drawings/report.md`).

## 8. Reproduce

```bash
python3 tools/buildings/itb_naip_measure.py      # ~25 s -> tools/buildings/itb_naip_measurements.json, out/buildings/itb/qa_*.png
python3 tools/buildings/itb_photo_skyline.py     # -> tools/buildings/itb_photo_skyline.json
python3 tools/buildings/build_spec_itb.py        # -> tools/buildings/spec_itb.json
```

- **Measurement inputs:**
  - `refs/cache/naip/naip_2024_world_0.5m_bgr.npy` and its `.json`;
  - `refs/cache/lighting/DAILY_DOF_CSV.ZIP`;
  - `refs/cache/buildings/itb/photos/1975704.jpg`.
- **Other files:**
  - Cached source pages: `refs/cache/buildings/itb/`.
  - Pole, pier and roof crops used for the by-eye picks: `out/buildings/itb/`.
