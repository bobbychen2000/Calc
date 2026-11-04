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

---------------------------------------------------------------------------------------------------------------------

## Verification

Adversarial fact-check, 4 Nov 2026. I re-fetched every cited source I could reach and tried to refute each key height,
dimension, date and licence, where possible with a method different from the one above.
- Tool: `tools/buildings/itb_verify.py` writes `tools/buildings/itb_verify.json` (numbers only) and the QA crops
  `out/buildings/itb/verify/qa_*.jpg` (NAIP pixels, local). With `--apply` it writes the verdicts into
  `tools/buildings/spec_itb.json`. It runs offline from the caches in about 5 s.
- Re-fetched on 4 Nov 2026, in `refs/cache/buildings/itb/verify/` (provenance in `SOURCES.json`):
  - the FAA DOF (`DAILY_DOF_CSV.ZIP`, `DOF.CSV` dated 2026-11-02; now in `refs/cache/lighting/`);
  - 15 source pages (`src/*.html`); **SEAONC now opens first-hand**;
  - the Commons licence records of all 24 photos (`commons_photos.json`).
- `itb_naip_measure.py` re-run on the restored NAIP 2024 raster and the new DOF file: **byte-identical output**.
- `js/` and `data/` are untouched. Corrected values in `spec_itb.json` keep the old value under `corrected`, and every
  item now carries a `verification` record.

**Verdicts.** CONFIRMED: an independent check agrees. PLAUSIBLE: consistent, but not pinned tighter. CONFLICT: sources
disagree. CORRECTED: the stated value or derivation is wrong; replaced. REFUTED: shown wrong. NOT RE-CHECKED: no new
evidence this round.

### V.1 Claim by claim

**Heights**

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | DOF roof tops 06-035315 / -316: 131 / 132 ft AGL, 139 / 140 ft AMSL, 1A | **CONFIRMED** | Unchanged in the 2026-11-02 file: same height, same accuracy (1A), position identical. New detail: VERIFIED STATUS O, ACTION A, JDATE 2013289, so the obstacles were **added on 16 Oct 2013**. The survey predates NAIP 2024 and the 2024–26 re-roofing. |
| 2 | The DOF points sit "at u = +54.7 and −60.9 m, on the flanks of the hump plateau" | **CORRECTED** | Those u values are measured from the *imaged* roof centre. From the relief-corrected centre they are at **u = +57.2 and −58.4 m**, 0.6–0.9 m inside the west eave. They are symmetric about the centre and **115.5 m apart along the axis = 379 ft**, which matches the published 380-ft centre span. The two surveyed tops therefore mark the roof over the **inner column lines** (±190 ft = ±57.9 m), which supports §2.1's inferred rhythm. |
| 3 | Ground ≈ 8 ft AMSL | **CONFIRMED** | AMSL − AGL = 8, 8 and 9 ft. |
| 4 | "144 ft" (SOM, Enclos), datum unknown | **CONFIRMED as published; conflict kept** | SOM: "Building Height: 144 feet". Enclos's spec block also names the owner as "San Francisco Department of Public Health", a data-entry error, so **Enclos is not an independent source** for the height. |
| 5 | Interior hall "705 × 210 × up to 83 ft" | **CONFIRMED (now first-hand)** | SEAONC: "glass-enclosed 'great hall' – 705 ft long, 210 ft wide, and up to 83 ft high". **83 ft is the interior height**, confirming §5 row 1. |
| 6 | Wing profile: humps 40.1, notches 35.7, crown ≈ 40, tips ≈ 34.9 m | **PLAUSIBLE**; one new independent check | (a) Reproduced exactly. (b) **New:** the *east* eave wanders together with the west eave. From the north tip to the hump the west eave moves +2.25 m and the east eave +2.20 m, while the imaged width stays at 66.0–66.6 m. A curved plan would move the two eaves in opposite directions, so the wander is height, as assumed. (c) The photo silhouette (crown, tips) **could not be re-run**: the Commons API and upload host returned HTTP 429 (rate limit) and the photo is not cached. (d) The two relief models in V.2 differ by 1–4 % along the hall, which is ≤ 0.5 m on the drops. |
| 7 | Level-3 floor 11.5 ± 1.5 m [inf] | **PLAUSIBLE / still unverified** | Three published heights now bracket it: 40.1 m − 90 ft = 12.7 m; − 100 ft = 9.6 m; − the first-hand 83-ft hall height = 14.8 m (less the roof build-up at the crown). No section drawing found. |
| 8 | Boarding Area A main roof ≈ 17 m ± 2.5 | **CORRECTED (refined) → 17.9 m, range 16.9–18.8** | The west band was re-measured with automatic half-level edges: **8.79 m** (IQR 8.71–8.86, 11 clean stations). The band equals (relief + shadow) × h. The note subtracts "any roof overhang", but **an overhang moves both band edges equally and cancels**. Method (b) relies on the SFO Museum footprint, which at G sits 3–6 m off. Result: h = 18.3 m with k(x), 17.4 m with the frame model. |
| 9 | Boarding Area A pod 1 top 85 ft (DOF 06-035352); rim band 2.5–3 m ⇒ about 7.5 m above the main roof | **DOF value CONFIRMED; derivation weaker than stated** | The rim bands at the three pod apexes measure 2.49–2.52 m. The dark band includes the pod's own shadow (0.116 m per m of rise), so the rise is **4.9–5.2 m** (6.8–6.9 m if the shadow is ignored, as in the note). Pod top = **22.3–25.2 m** against the DOF's 25.9 m: consistent only at its upper end. The DOF point (±6.1 m) lies at pod 1's NNE end near the west eave. |
| 10 | Boarding Area G main roof ≈ 17 m ± 3 | **PLAUSIBLE** | The NNE shadow band was re-measured: **2.14 m** (IQR 1.75–2.36, 41 stations). With k(x), h = **16.9 m** (IQR 15.5–18.0). The sunlit SSW facade cannot be separated from the apron, so the note's k-free sum (0.297·h) was **not** reproduced. |

**Plan and structure**

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 11 | Roof axis heading 162.85° | **CONFIRMED** | An independent straight-line fit to the west facade base (ground level, so no relief) gives **162.81°**: 312 of 339 rows, sd 0.15 m. 162.83° = the airport grid t-axis (27.83°) + 135°. The piers sit on the grid axes too: A at 208.0° and G at 297.75°, by NAIP edge alignment. |
| 12 | Roof length 252.7 m ± 1.5 | **PLAUSIBLE; range widened to 252.6–255.1 m** | See V.2. The 252.7 m depends on removing a 2.4 m along-axis magnification, which a frame camera produces and an across-track-only relief model does not. Either way the roof is **7–9 m shorter than 860 ft**. |
| 13 | Corner outline NW/NE/SE/SW (±1.5 m) | **CORRECTED** | The stated corners span **255.06 m** along the axis: they were relief-corrected east-only. That contradicts the stated length of 252.68 m, which removes the magnification. Replaced by frame-model corners (V.2): NW (−1313.08, 254.23), NE (−1250.59, 234.95), SE (−1176.03, 476.58), SW (−1238.52, 495.86), outline 252.87 × 65.39 m. The east-only alternative is kept in the spec as `alt_x_only_model`. |
| 14 | Centre (−1245.0, 364.7) | **PLAUSIBLE** | The frame model gives (−1244.56, 365.40), 0.85 m away, inside the stated ±1.5 m. |
| 15 | Width 65.4 m | **CONFIRMED** | East eave re-measured: imaged width 66.15 m, constant along the length; true 65.39 m. |
| 16 | 5 truss lines, 12.12 m (39.8 ft) apart | **CONFIRMED** | Autocorrelation of 207 cross profiles: imaged 12.28 m (IQR 12.24–12.32), giving **12.16 m = 39.9 ft** against the published 40 ft (12.19 m). |
| 17 | 5 lens skylights, 48.4 m × 9.6 m | **PLAUSIBLE (minor)** | 48.4 m is the *imaged* detection-box length; with the magnification removed it is ≈ 47.9 m. The pointed ends fade, so tip to tip may be 1–2 m more. The westmost lens is full length too; it was detected at 34 m only because it is darker. Each skylight reads as a **D** in NAIP: straight east edge, convex west edge. Whether that is a vaulted lens leaning east or a D-shaped plan is not settled. |
| 18 | Glazed tip bands 18.75 m (N) / 15.75 m (S) | **CONFIRMED**, plus a new asymmetry | The bands are visible at the stated rows (`qa_tip_N.jpg`, `qa_tip_S.jpg`). **New:** the centre-section lens row sits **2.2 m north** of the fascia midpoint. Beyond the glass, the south tip carries a **3.6 m white segmented strip** and the north tip 1.6 m. The dark band beyond the north fascia is not roof: it continues outside the roof width, and is 0.4 m wider inside it, where the hall's shadow falls. |
| 19 | Rhythm 20 \| 140 \| col \| 80 \| col \| 100 \| 180 … ft [inf] | **PLAUSIBLE; the end segment conflicts** | The inner column lines are supported by the DOF pair (#2). With the 80-ft bay, the outer columns sit at ±82.3 m, and NAIP puts the fascia **44.1 m = 145 ft** beyond them, not 160 ft. Either the 860-ft total or the bay does not describe the visible roof. |
| 20 | 860 ft, 380 ft, 160 ft, 29 ft deep, 20 columns from level 3, five double-cantilever sets | **CONFIRMED first-hand** (were snippet-only) | SEAONC page text: "five sets of steel balanced double cantilever trusses with a central trussed span"; "supported on 20 cantilevered columns rising from the third floor departures level"; "up to 29 ft deep, spans 380 ft at its center and 160 ft at each end cantilever with an overall length of 860 ft". Also new: "172,000 sq. ft. of exposed trussed steel roof (4,040 tons including main roof cantilevered box columns)" = 15,980 m², against the NAIP outline of 16,535 m². |
| 21 | Truss length 320 ft, centre section 180 ft | **STILL SNIPPET-ONLY** | AISC PDF: curl 403 (Cloudflare) and WebFetch 403; web.archive.org has a 2024-09-04 snapshot, but the connection was reset. |
| 22 | Herrick; Mare Island; ~35 pieces by barge | **CONFIRMED (now first-hand)** | SEAONC lists The Herrick Corporation. Quote: "fully assembled at the Mare Island fabrication shop and then disassembled into some 35 major pieces … shipped directly to the site on barges … jacked into position and pinned in place". Smith-Emery: "middle sections were erected first, followed by the outside cantilever and the inside cantilever trusses". |
| 23 | Boarding Area A imaged roof 36.5 m | **PLAUSIBLE** | Re-measured at **37.85 m** (58 stations; the upper quartile is gate rooms). |
| 24 | Boarding Area G imaged roof "~33.5 m" | **REFUTED** | Between its two parapet lines the roof measures **38.4 m** (IQR 38.2–38.7, 38 stations). This matches the SFO Museum body width of 38.3–38.4 m. |
| 25 | Pod lengths A 70 / 55 / 55 m, G 60 / 55 / 62 m (by eye) | **PLAUSIBLE** | Read by eye again on the grid-aligned crops: A pod 1 ≈ 55–60 m (not 70); pods 2 and 3 ≈ 52–55 m. G ≈ 62 / 58 / 66 m. All ±4 m. |

**Method, dates and licences**

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 26 | Relief k(x) = 0.7553 + 0.0002753·x, east-only | **PLAUSIBLE; north–south component unresolved** | See V.2. |
| 27 | Sun azimuth ~187°, elevation ~72.4° (local noon) | **CONFIRMED** | NOAA solar position for 2024-05-20 at the shadow azimuth of 186.6°: **13:14 PDT, elevation 72.39°** (71.9–72.4° for ±4° of azimuth), declination 20.09°. The shadow-length value, 72.5°, agrees. |
| 28 | Dates: ground broken Oct 1995; opened 10 Dec 2000; renamed 16 Jan 2024; re-roof ceremony 27 Jun 2024; completion mid-2026 | **CONFIRMED** | Airport World: "On Sunday, December 10, 2000, SFO held a ribbon-cutting ceremony"; "Breaking ground in October 1995"; "On January 16, 2024, the San Francisco Airport Commission approved a resolution to rename"; "expected to be completed in mid-2026". Webcor: "June 27, 2024". Other dates: SEAONC "Designed and constructed from 1994 to 2000"; Tutor Perini lists "COMPLETION 2001", the contract close-out. |
| 29 | Upgrade scope: 1,400 kW PV, 90-ft scaffolds, $75 M | **CONFIRMED except the cost** | Webcor: "installing 1,400 kW solar". FTF, now read first-hand: "Scaffolds reached 90 feet high over active roadways and AirTran tracks". The **"$75 M" is not in the re-fetched Webcor pages**, and Airports International is still 403: unverified. |
| 30 | Gates at opening: 26 | **CONFLICT** | SEAONC, first-hand: "26 new gates". Tutor Perini ITB page: "24 international gates". |
| 31 | Other published figures | **CONFIRMED** | **Size:** 1.8 M sq ft; 1,000,000 sq ft site. **Levels:** 5 stories / five levels, L1 services and baggage, L2 arrivals, L3 departures, L4–5 offices. **Roof:** 380-ft span; ticket lobby 700 ft; bamboo 55 ft; 60–90 ft above the floor; three-chord "football" trusses. **Envelope:** 267 isolators (SEAONC adds "up to 20 inches" of displacement); curtain walls spanning over 60 ft; 382,000 sq ft of cladding. **Boarding Area G:** 380,000 sq ft, three-story, six double-gated gate rooms for twelve 747-400s, Robin Chiang & Company, completed 1999, composite aluminium panels. **Boarding Area A:** 23 bridges at A1–A15, A6 retrofitted for three bridges. Each quote was found verbatim in the cached pages; `itb_verify.json` `sources.quotes` lists them. |
| 32 | A6 (AGS) vs A11 (Wikipedia) for the three-bridge A380 gate | **Not a contradiction in time** | Wikipedia "Gate A11 has three jetways" cites an older SFGate A380 article. AGS: A6 was retrofitted in the 2020 project. |
| 33 | Photo licences, authors and dates (24 files) | **CONFIRMED** | Commons API re-query: all 24 licences and authors match `spec_itb.json` `photos[]`. |
| 34 | 40-ft E/W grid by 80-ft N/S bays (SOM sketch) | **NOT RE-CHECKED** (image not re-fetched) | The E/W grid agrees with #16; the N/S bay is not observable in NAIP. |

### V.2 The relief model, and what it does to length, corners and pier heights

The measurement fits only the **east** component of the five pole-ring shifts. Fitting their full 2-D shifts with one
central projection, shift = h·(P − N)/(H − h), works better:

| Model | Parameters | RMS |
|---|---|---|
| Frame | nadir **N = (−2768, 444)** ± (98, 9); H − h = 3705 ± 277 m | **0.21 m** |
| x-only | k(x), as in the measurement | 0.54 m |

The shift direction rotates with z, as a frame camera's does:

| Pole z | 338 | 421 | 447 | 467 | 520 |
|---|---|---|---|---|---|
| Shift direction | 86.8° | 88.0° | 90.0° | 90.0° | 94.9° |

The correlation is 0.91. NAIP 2022 over SFO was a Leica ContentMapper frame sensor (`imagery.md`); no open metadata names
the 2024 sensor. But two of the five picks are manual (±1 m), so the north–south signal (|dz| ≤ 1.25 m) is close to the
pick noise. At Boarding Area G (z ≈ 100) the single-frame model **fails**: the roof would lean over its own north shadow
(visible shadow 0.04 m per metre of height), yet 2.1 m of shadow is seen. G is therefore in another frame of the mosaic,
or the relief there has little north–south component.

**Consequences.**

| Quantity | Frame model | x-only model | Adopted |
|---|---|---|---|
| Length | 252.87 m | 255.04 m (no magnification) | 252.68 m stated; range **252.6–255.1 m** |
| Corners | consistent with the 252.87 m length | 255.06 m outline (the stated corners) | frame model (the stated corners contradicted the stated length) |
| Hall heading | 162.85° | 163.03° | 162.85° |
| Boarding Area A height | 17.4 m | 18.3 m | 17.9 m |
| Boarding Area G height | fails (see above) | 16.9 m | 17 m kept, range 13–20 m |

The 860-ft conflict survives both models.

### V.3 Changes made to `spec_itb.json` (by `itb_verify.py --apply`)

- **Corrected values** (the old value kept under `corrected`):
  - `roof.corners_obs`: frame-model corners; the old ones are also kept as `alt_x_only_model`.
  - `ba_a.height_roof`: 17.0 → **17.9 m**, range 16.9–18.8, confidence low → medium.
- **Status changes:**
  - **snippet-only → verified (SEAONC first-hand):** `roof.cantilever_end`, `roof.truss_depth`, `roof.columns` and
    `itb.steel`.
  - **unverified → verified:** `hall.size_snippet`.
  - **unverified → conflict:** `itb.gates_2000`, now 24 vs 26.
- **Additions:**
  - `range_m` on `roof.length_obs` (252.6–255.1), `ba_a.height_roof` and `ba_g.height_roof` (13–20);
  - `alt_frame_model` on `roof.centre_obs` and `naip.k_model`;
  - `naip_roof_width_m` on both pier footprints (A 37.85 m, G 38.4 m; G's "~33.5 m" refuted);
  - a `verification` record on all 65 items, and `photos_verification`.
- **Sources and lists:**
  - The `seaonc` source is now `read: full`.
  - The `unverified` list drops the SEAONC / "705 × 210 × 83" entries and gains three: the AISC PDF, the NAIP 2024
    sensor, and the $75 M cost.
  - One open question added (below).

### V.4 Still unknown, and what would settle it

1. **Roof length**: 252.6–255.1 m (NAIP) against 860 ft = 262.1 m (SEAONC, Smith-Emery). The 380-ft centre span is now
   confirmed independently by the DOF pair, so the discrepancy sits in the end cantilevers: 145 ft visible against 160 ft
   published. Any one of these would settle it: an SFO record roof plan, a ground survey of the tip fascias, or the NAIP
   2024 FGDC metadata with the frame centres.
2. **Truss length (320 ft) and centre section (180 ft)**: only the AISC article states them, and it is still unreadable.
3. **Crown and tip heights**: these rest on the 2005 photo, which could not be re-checked this round (rate limit); the
   tips also rest on extrapolation of the eave fit.
4. **Pier pods**: their heights are unmeasured (A pod 22–25 m by relief; DOF 25.9 m), and G has no DOF entry.
5. **Level-3 floor**: still only bracketed (9.6–14.8 m) by published heights.
6. **The 2026 roof** (PV layout) and **the $75 M cost**: as before.
7. **The lens skylight plan** (lens or D shape): one interior photo, e.g. Famartin 2025, would settle it.

Reproduce:
```bash
python3 tools/buildings/itb_naip_measure.py          # unchanged; output identical
python3 tools/buildings/build_spec_itb.py            # regenerates spec_itb.json without the verdicts ...
python3 tools/buildings/itb_verify.py --apply        # ... so re-apply them (writes itb_verify.json and the spec)
```

## Drawing round (2026-11-04): facade and roof details used by BI-01..03

**West glass wall position** [obs + inf]. `eave_profile.base_line_v_median` = −43.5 m (imaged frame, centre
(−1223.11, 361.42), sd 0.6) lies at v = −21.8 m in the relief-corrected roof frame of the sheets (centre
(−1244.56, 365.41)). The line fixes the wall only together with the height of the base it images. Photos put the wall's
foot on the elevated departures curb (level 3), so the wall is the line moved back by the frame-model relief of L3:
**v = −26.3 m (−27.6 to −25.6 for L3 14.8–9.6 m), 6.4 m (5.1–7.1) inside the west eave** (`draw_data.itb_west_wall`).
At grade it would read −21.8; if the imaged line were the curb-canopy edge (~16.5 m) the wall would sit 2–4 m further
east. The deviation check of the drawn wall base at its predicted imaged position: 6/6 pieces, median +0.03 m
(consistency, same imagery).

**Photos** (i4 DimiCalifornia 2005, public domain, near-frontal long lens: 0.1335 m/px from the 126.4 m tip-to-crown
span; i3 Elizabeth K. Joseph 2017, CC BY 2.0; i1 Kulikovsky 2007, CC BY 3.0; reference only):
- Glass-wall head level at ~30.8 m: 70 px = 9.3 m below the wing crest (cf. the 29-ft truss depth) [obs, ± 1.5].
- The football trusses are exposed above the wall along the whole facade and taper to the tips [obs].
- Columns: single white columns at u −83.4 / −59.4 m (± 1.5; inferred lines −82.3 / −57.9). Each "pair" in i4 is a
  column and its shadow on the glass, so the columns stand clear in front of the wall; in i3 they rise from the curb
  sidewalk and branch into struts into the trusses [obs]. Their v is not measured.
- The hall's west wall ends ~157 px = ~21 m short of the north tip (705-ft hall centred: 19.0 m): open cantilevers.
- V notches at |u| 27–29 m; the centre arch reads level with, or ~1 m above, the humps (40.1 m ± 2 kept).
- Curb canopy ~4.5–6 m above the curb [inf].

**Roof plan.** Relative to the fascia midpoint (imaged u +1.0), the glass tip bands end 1.6 m (N) / 3.6 m (S) inside
the fascia, and the lens row's area centroids lie 1.5–2.2 m north; the westmost lens is drawn full length (mean of the
other four), per the verification.

**BA-G overlay** uses the k(x) relief (as the verified height): roof median +0.13 m, |median| 1.05, 88 % within 2.5 m;
with the frame model (which fails at G) −0.60 / 1.46 / 72 %. Base unchanged (−0.57 / −0.64).

## Drawing round 2 (2026-11-04)

**West wall and the curb canopy** [inf]. SEAONC (re-fetched): "760 tons of exposed steel at the ITB departures level
window walls and entrance canopy" — the canopy exists [pub]; ~5 m above L3 and ~5 m deep in photos i3 / i4 [inf]. The
frame-model lean across the facade is (−21.83 + 26.31) / 11.5 = 0.39 m/m, so the sight line from the wall's foot (L3)
leaves the wall by only 1.95 m at canopy height: a canopy deeper than ~2 m hides the foot. The imaged straight line is
then the canopy's outer edge (wall at v −23.3) or the wall just above the canopy (v −28.3). The sheets draw the band
−28.3 to −23.3 (4.4–9.4 m inside the eave) at its middle −25.8, tagged inf; −26.3 is valid only for a canopy ≤ 2 m deep.

**Hall width conflict** [pub vs obs]. SEAONC: "705 ft long, 210 ft wide, and up to 83 ft high" = 64.0 m wide. East of
the wall there are at most 61.0 m (55.9–61.0 over the band) under the 65.4 m roof. Resolutions: the wall nearer the
eave; the hall running east under a lower roof (the measured east edge is "fascia → lower roof fall"); a wider roof (SOM
concept sketch 866' × 260'). BI-02 / BI-03 draw the published width from the wall, ending 5.5 m beyond the east eave.

**Hump anchor** [inf]. The eave fit is anchored on the DOF mean (40.08) at its fitted peak |u| 67, where no DOF point
exists. At the DOF stations (u +57.16, 39.93; u −58.35, 40.23; 0.8–1.1 m inside the west eave) the curve reads 39.70 /
39.78, 0.23 / 0.45 m low (inside the 1A ± 3 ft). Anchored there every eave height would rise ~0.34 m (peak ~40.4).
The sheets tag 40.08 as a DOF-anchored fit [inf] and show the DOF values at their stations [pub].

**West facade** (photos i1 Kulikovsky 2007, CC BY 3.0; i4 DimiCalifornia 2005, public domain; reference only), measured
on i4 at 0.1331 m/px about the centre column 1025: a clear central bay x 727–1323 (±39 m; i1 ±42 m) on a mullion grid
(verticals ~6.1 m, horizontals ~2.2 m, low); the lettering "SAN FRANCISCO INTERNATIONAL" x 780–1267 (±32.5 m; i1 ±37 m),
~2.7–2.8 m tall; fritted side bays white with horizontal frit bands and a dark clear strip just above the canopy; the
central glazing's head follows the centre section's bottom chord, 1–3.5 m above the side bays' head (tentative).

**Skylight planform** [inf]: drawn as pointed lenses with the D-shaped alternative dotted (spec verification: not settled).

**Tags corrected**: the west-line columns (u at the inferred column lines) and the hump are inf; the BA-A pod-1 top is
"DOF 25.9 [pub] vs NAIP 22.3–25.2 [obs] (conflict)"; 252.87 m = 830 ft (rounded, was 829).
