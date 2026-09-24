# KSFO airfield lighting: verified facts, FAA geometry, photometry and day/night/weather logic

Research deliverable for the lighting, day/night and weather work. It is research only: it changes no code or data.
It adds two machine-readable files, both written by `tools/env/build_lighting_spec.py` (the NAIP measurements it uses are reproduced by `tools/env/lighting_naip_measure.py`):

- `tools/env/lighting_spec.json`: the rules, photometry, colours, operating logic, per-runway-end facts and anchors, obstructions, conflicts and open questions.
- `tools/env/lighting_fixtures.json`: the rules expanded into 2,269 individual fixtures, each with world x/z, height, fixture type and a colour per face.

Written 24 Sep 2026. Every source below was downloaded that day into `refs/cache/lighting/` (gitignored), except the
NASR zip, which was already in `refs/cache/xcheck/faa/`.

**Provenance codes, used in this report and the JSON:**
- **pub**: a published SFO fact. The sources are FAA NASR, the Chart Supplement, the d-TPP plates and airport diagram, the FAA RWSL graphic and the FAA DOF.
- **std**: an FAA standard applied to SFO. The standard itself is verified. **Its as-built application at SFO is not surveyed.**
- **obs**: measured by us on USDA NAIP 2024 orthoimagery (public domain, 0.6 m).
- **inf**: inferred. Either a choice inside a standard tolerance, or a value no source gives.

---------------------------------------------------------------------------------------------------------------------

## 1. Summary

1. **Runway lights (pub).**
   - All four runways have HIRL and centreline lights: the Chart Supplement says "HIRL CL" on each runway, and NASR has `CNTRLN_LGTS_AVBL_FLAG=Y` at all 8 ends.
   - TDZ lights only at 28R and 19L.
   - REIL only at 10L, 1L and 1R. NASR `RWY_END_LGTS_FLAG` is the REIL flag, per the NASR layout PDF.
   - Approach lights only at three ends: **28R ALSF-2, 28L MALSR, 19L MALSF**.
   - 4-light PAPI on the left at 10L, 10R, 19L, 19R, 28L and 28R, with published angle and TCH as follows. There is no VGSI at 1L or 1R.

     | End | Angle | TCH |
     |---|---|---|
     | 10L | 3.0° | 80 ft |
     | 10R | 3.0° | 68 ft |
     | 19L | 3.0° | 71 ft |
     | 19R | 3.15° | 58 ft |
     | 28L | 2.85° | 67 ft |
     | 28R | 3.0° | 68 ft |

   - RVR at touchdown, midfield and rollout (TMR) on every end.
   - Rotating beacon white-green, operating sunset to sunrise (SS-SR).
   - Lighted wind indicator.
   - **Runway Status Lights (RWSL) in operation.** The FAA site graphic shows Takeoff Hold Lights at 10L, 10R, 28L, 28R, 1L and 1R, and REL arrays at ~~27~~ **28** labelled taxiway entrances *[corrected by verifier: the graphic has 28 taxiway labels; taxiway N on 10R/28L, between P and the 28L THL, was omitted; see §15]*.
2. **New observations (obs), measured on NAIP 2024 in the app's world frame.**
   - **All six PAPIs** are clearly resolved: four lamp housings on a concrete pad, 30 ft apart.
     - Their distances from the threshold match the NASR TCH/angle geometry within ±31 ft at five ends.
     - **28R is the exception: its PAPI sits 71 ft further out than its published 68-ft TCH implies.** The measured 1,369 ft equals the ILS glide-slope source (1,049 ft) plus the 300-ft "height group 4" rule in JO 6850.2C. *[corrected by verifier: "equals" should read "falls inside": the HG4 window is source + 300 ft +50/−0, i.e. 1,349–1,399 ft. The same window also contains 28L (ILS source 1,065 ft → 1,365–1,415 ft; observed 1,369 ft), and 19L is 5 ft short of its window (1,349 ft vs observed 1,344 ft). So HG4 siting explains all three ILS ends. What is unique to 28R is that its published TCH of 68 ft does not match the observed siting, which implies 71.7 ft.]*
   - **The approach-light piers over the Bay are resolved.**
     - The 28R pier has crossmembers every 100 ft from 700 to 1,300 ft.
     - The 28L pier has crossmembers at 1,000 and 1,300 ft and runs on past 3,000 ft.
     - The 19L pier ends at about 1,400 ft, which is the MALSF length, with crossmembers at 1,000 and 1,200 ft.
     - 19R has no pier.
3. **Standards (std).** The full FAA geometry is transcribed with paragraph references and verbatim quotes:
   - edge, threshold and displaced-threshold lights, centreline and TDZ lights;
   - ALSF-2 and its SSALR mode, MALS/MALSF/MALSR, PAPI and REIL;
   - RWSL, taxiway centreline and edge lights, runway guard lights, stop and clearance bars;
   - the beacon, obstruction lights and apron floodlighting.

   The sources are AC 150/5340-30J, JO 6850.2C and AC 70/7460-1N. Photometry (candela and beam extents per colour) comes from AC 150/5345-46F, -28H, -51B, -12F and -43J. The aviation colours are the chromaticity boxes in FAA EB 67D, also converted to linear sRGB.
4. **Day, night and weather.** FAA JO 7110.65BB §3-4 gives the tower's rules: which systems are on, and at which intensity step, by day or night and by visibility or RVR.
   - This includes the rule that the **28R system runs as SSALR, not full ALSF-2, unless visibility is at or below ¾ SM or RVR is at or below 4,000 ft**.
   - It also includes the rule that the **sequenced flashers only run below 3 SM**.

   This is the verified logic for the renderer's day/night/weather states.
5. **What the current renderer gets wrong** (`js/anim/lights.js`, see §12). It has no yellow caution zone. The centreline colour code is wrong. It draws a 19-light threshold bar at every end. It has no displaced-threshold lighting. The MALS crossbar is drawn as the ALSF-2 bar. There is no 500-ft bar, no SSALR mode, no REIL, no RWSL, no beacon and no obstruction lights. The PAPI distance comes from TCH/tan, which puts the 28R PAPI 22 m off. The intensities are arbitrary.

---------------------------------------------------------------------------------------------------------------------

## 2. Sources, currency, cache

| id | Source | Currency | URL | Cache |
|---|---|---|---|---|
| nasr | FAA NASR 28-day APT CSV (APT_BASE, APT_RWY, APT_RWY_END, APT_RMK + "APT DATA LAYOUT.pdf") | cycle eff. **2026-09-03** | https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/ | `refs/cache/xcheck/faa/03_Sep_2026_APT_CSV.zip` |
| cs | Chart Supplement SW, SAN FRANCISCO INTL p. 275–276 | **3 SEP–29 OCT 2026** | https://aeronav.faa.gov/afd/03sep2026/sw_275_03SEP2026.pdf | `refs/cache/lighting/sw_275_03SEP2026.pdf` |
| ad | Airport Diagram AL-375 | SW-2 **03 SEP–01 OCT 2026** | https://aeronav.faa.gov/d-tpp/2609/00375ad.pdf | `refs/cache/xcheck/faa/00375ad_2609.pdf` |
| tpp | 22 SFO approach plates, d-TPP 2609 (e.g. ILS 28R Amdt 15B, ILS 28L Amdt 27C, ILS 19L Amdt 23A, RNAV 10L Amdt 3, RNAV Y 19R Amdt 4, RNAV Y 10R Amdt 2A) | 2609 | https://aeronav.faa.gov/d-tpp/2609/00375IL28R.PDF (pattern `00375<proc>.PDF`) | `refs/cache/lighting/tpp/` |
| ac30j | AC 150/5340-30J *Design and Installation Details for Airport Visual Aids* (current; errata 2020-11-17) | 2018-02-12 | https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5340-30J.pdf | `refs/cache/lighting/` |
| jo6850 | FAA Order JO 6850.2C *Visual Guidance Lighting Systems* (status "Active"; cancels 6850.2B) | eff. 2022-08-30 | https://www.faa.gov/documentLibrary/media/Order/FAA_Order_6850.2C.pdf | ″ |
| ac46f | AC 150/5345-46F *Specification for Runway, Taxiway, Heliport, and Vertiport Light Fixtures* | 2024-09-30 | https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC-150-5345-46F-Fixtures.pdf | ″ |
| ac28h | AC 150/5345-28H *PAPI Systems* | 2019-07-29 | https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-28H.pdf | ″ |
| ac51b | AC 150/5345-51B *Discharge-Type Flashing Light Equipment* (REIL/ODALS) | 2010-09-08 | https://www.faa.gov/documentLibrary/media/Advisory_Circular/150_5345_51b.pdf | ″ |
| ac12f | AC 150/5345-12F *Airport and Heliport Beacons* | 2010-09-24 | https://www.faa.gov/documentLibrary/media/Advisory_Circular/150_5345_12f.pdf | ″ |
| ac43j | AC 150/5345-43J *Obstruction Lighting Equipment* | 2019-03-11 | https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-43J.pdf | ″ |
| ac7460 | AC 70/7460-1N *Obstruction Marking and Lighting* (cancels -1M) | 2026-08-11 | https://www.faa.gov/documentLibrary/media/Advisory_Circular/2026-07-13_AC_70_7460-1N_Obstruction_Marking_and_Lighting_FINAL_CLEAN.pdf | ″ |
| eb67d | FAA Engineering Brief 67D (LED chromaticity) | 2012 (rev. file 2024-07) | https://www.faa.gov/sites/faa.gov/files/2024-07/eb_67d_rev.pdf | ″ |
| jo7110 | JO 7110.65BB *Air Traffic Control* §3-4 Airport Lighting | online, fetched 2026-09-24 | https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_4.html | ″ |
| aim | AIM Ch. 2 §1 Airport Lighting Aids | online, fetched 2026-09-24 | https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap2_section_1.html | ″ |
| rwsl | FAA "Runway Status Lights at San Francisco (SFO)" graphic (PDF created 2017-11-13) | — | https://www.faa.gov/air_traffic/technology/rwsl/media/SFO.pdf | ″ |
| dof | FAA Digital Obstacle File, `DAILY_DOF_CSV.ZIP` (WGS 84) | DOF.CSV 2026-09-18 | https://aeronav.faa.gov/Obst_Data/DAILY_DOF_CSV.ZIP | ″ |
| sfo2013 | SFO Airport Commission memo "Runway Safety Area Project Update", 2013-06-20 (NTSB docket copy) | 2013 | https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=ATC+3-SFO+RSA+Construction+Update-Rel.pdf&ID=398528 | ″ |
| ac5360 | AC 150/5360-13A *Airport Terminal Planning* §7.5; cancelled AC 150/5360-13 (1988) Table 4-1 | 2018-07-13 | https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC-150-5360-13A-Airport-Terminal-Planning.pdf | ″ |
| naip | USDA NAIP 2024 (flown 2024-05-20), public domain, world-grid resample | 2024 | docs/research/imagery.md | `refs/cache/naip/` |
| xplane / osm | X-Plane Gateway KSFO 112022; OSM Overpass 2026-09-24 (**cross-checks only**) | — | — | `refs/cache/xplane/`, `refs/cache/osm/` |

Crops and figures made for this report are in `refs/cache/lighting/fig/` and `refs/cache/lighting/naip/`. Key files:
- `rwsl_SFO.png` and its zooms;
- `ac30j_p191.png` and `ac30j_p195.png` (Fig A-5 and A-9);
- `papi28h_p12.png`;
- `naip/als_28_top.png`, `naip/als_28_bot.png`, `naip/zoom_28.png`, `naip/end_28.png`, `naip/als_19.png` and `naip/papi_sites.png`.

---------------------------------------------------------------------------------------------------------------------

## 3. SFO facts per runway and per end (pub, with obs where stated)

### 3.1 Runways

| Runway | Length × width ft | Edge | CL | Source |
|---|---|---|---|---|
| 10L/28R | 11,870 × 200, ASPH-GRVD | HIRL | yes | NASR `RWY_LGT_CODE=HIGH`; CS "HIRL CL" |
| 10R/28L | 11,381 × 200 | HIRL | yes | ″ |
| 1R/19L | 8,650 × 200 | HIRL | yes | ″ |
| 1L/19R | 7,650 × 200 | HIRL | yes | ″ |

The Chart Supplement entries, verbatim (cs p. 275):

> "RWY 10L–28R: H11870X200 (ASPH–GRVD) … HIRL CL
> RWY 10L: REIL. PAPI(P4L)—GA 3.0º TCH 80´. RVR–TMR Tower.
> RWY 28R: ALSF2. TDZL. PAPI(P4L)—GA 3.0º TCH 68´. RVR–TMR Thld dsplcd 300´. Rgt tfc.
> RWY 10R–28L: … HIRL CL  RWY 10R: PAPI(P4L)—GA 3.0º TCH 68´. RVR–TMR Tower. Rgt tfc.
> RWY 28L: MALSR. PAPI(P4L)—GA 2.85º TCH 67´. RVR–TMR Thld dsplcd 300´.
> RWY 01R–19L: … HIRL CL  RWY 01R: REIL. RVR–TMR Thld dsplcd 560´. Tree.  RWY 19L: MALSF. TDZL. PAPI(P4L)—GA 3.0º TCH 71´. RVR–TMR
> RWY 01L–19R: … HIRL CL  RWY 01L: REIL. RVR–TMR Thld dsplcd 640´.  RWY 19R: PAPI(P4L)—GA 3.15º TCH 58´. RVR–TMR"

The airport remarks also say "Rwy status lgts in operation", and NASR APT_RMK has "RWY STATUS LGTS IN OPN.".

### 3.2 Runway ends

All values are from NASR APT_RWY_END (cycle 2026-09-03) and agree with the CS, except the PAPI "obs" columns. "Instr." means the end has a published instrument approach procedure in d-TPP 2609. The world positions of every threshold and runway end are in `lighting_spec.json` under `runways[].ends[]`.

| End | True hdg | Displaced thr ft | ALS | REIL | TDZ | PAPI angle / TCH (pub) | PAPI dist. from TCH/tan ft | **PAPI LHAs obs (NAIP)**: along ft / lateral ft left | Plate electronic GP / TCH | Instr. | Caution zone | THL (RWSL) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10L | 117.8 | 0 | — | **yes** | — | 3.00 / 80 | 1,526 | **1,556** / 177-207-237-268 | RNAV GP 3.00 / 55 | yes | 2,000 ft | yes |
| 28R | 297.8 | **300** | **ALSF2** | — | **yes** | 3.00 / 68 | 1,298 | **1,369** / 173-204-234-264 | ILS GS 3.00 / 55 (CAT II/III) | yes | 2,000 ft | yes |
| 10R | 117.8 | 0 | — | — | — | 3.00 / 68 | 1,298 | **1,298** / 157-188-218-248 | RNAV 3.00 / 60 | yes | 2,000 ft | yes |
| 28L | 297.8 | **300** | **MALSR** | — | — | **2.85** / 67 | 1,346 | **1,369** / 173-203-233-263 | ILS GS 2.85 / 53 (SA CAT II) | yes | 2,000 ft | yes |
| 1L | 27.8 | **640** | — | **yes** | — | none | — | — | none | **no** | none | yes |
| 19R | 207.8 | 0 | — | — | — | **3.15** / 58 | 1,054 | **1,023** / 176-206-236-266 | RNAV GP 3.15 / 55 | yes | 2,000 ft | no |
| 1R | 27.8 | **560** | — | **yes** | — | none | — | — | none | **no** | none | yes |
| 19L | 207.8 | 0 | **MALSF** | — | **yes** | 3.00 / 71 | 1,355 | **1,344** / 161-191-221-251 | ILS GS 3.00 / 55 | yes | 2,000 ft | no |

- **Glide paths on the plates.** The plates carry the notes "(VGSI Angle 3.00/TCH 68). VGSI and ILS glidepath not coincident" (28R), "(VGSI Angle 2.85/TCH 67)" (28L), "(VGSI Angle 3.00/TCH 71)" (19L), "(VGSI Angle 3.00/TCH 80)" (10L) and "(VGSI Angle 3.00/TCH 68). VGSI and descent angles not coincident" (10R). There is no note at 19R, where the VGSI and the GP are within the non-coincidence thresholds. The VGSI and the electronic glide paths are deliberately different. *[verifier: the 28L, 19L and 10L plates also say "VGSI and ILS/RNAV glidepath not coincident"; only the angle/TCH part was quoted above.]*
- **Caution zone.** The caution zone is the yellow edge-light zone seen by traffic using that end: the last min(2,000 ft, half the runway length). It applies only to instrument ends (ac30j 2.3.1.1.2 items 1–4). No IAP exists to 1L or 1R, so traffic landing on 1L or 1R sees white edge lights to the end *[std rule applied; as-built unverified]*.
- **RVR.** RVR is TMR at all ends.
- **Declared distances.** Declared distances are in the JSON. The 10L and 10R ASDA/LDA end 677 ft before the east pavement end. Lights are still measured from the pavement end, per Fig A-9 notes 5 and 6 (§5.1).

### 3.3 Airport-level facts

- **Beacon.** NASR APT_BASE `BCN_LENS_COLOR=WG` ("WHITE-GREEN (LIGHTED LAND AIRPORT)", layout PDF) and `BCN_LGT_SKED=SS-SR`. **The beacon's position is published nowhere**: not in NASR, the CS, the airport diagram, X-Plane or the cached OSM (see §14).
- **Airport lighting schedule.** `LGT_SKED` is blank. The CS says "Attended continuously", so lighting is operated by ATC.
- **Wind indicator.** `WIND_INDCR_FLAG=Y-L`, a lighted wind indicator.
- **Airport diagram lighting note, verbatim:** "TDZL/RCLS Rwys 19L and 28R REIL Rwys 1R, 1L and 10L HIRL Rwys 1R-19L, 1L-19R, 10L-28R and 10R-28L". The plates carry the same lines. See conflict C1.

### 3.4 History that matters for the 28-end lighting (pub)

SFO memo of 20 Jun 2013 (sfo2013):
- The 28L and 28R thresholds were relocated on 27 and 29 Jun 2013.
- It also says "Other improvements include … replacement of the Runway 28L approach lighting system, needed changes to the Runway 28R approach lighting system".
- It says "The new Precision Approach Path Indicators (PAPI) for Runways 28L and 28R arc [sic OCR] scheduled to become operational by July 2, 2013".

So both 28-end ALS were reworked for the 300-ft displacement. This supports referencing the ALS stations to the displaced (landing) threshold, as the FAA standard requires.

---------------------------------------------------------------------------------------------------------------------

## 4. Conflicts between sources

| # | Conflict | Resolution in the spec |
|---|---|---|
| C1 | **Centreline lights.**<br>• The CS "HIRL CL" on all 4 runways and NASR `CNTRLN_LGTS_AVBL_FLAG=Y` at all 8 ends say every runway has them.<br>• The AD and plate note "TDZL/RCLS Rwys 19L and 28R" implies centreline lights only on 10L/28R and 1R/19L. | Follow **CS + NASR** (two FAA datasets agree).<br>Open question Q3. |
| C2 | **28R PAPI.**<br>• The published TCH (68 ft at 3.00°) implies 1,298 ft from the threshold.<br>• NAIP shows the LHAs at 1,369 ft ±5 ft.<br>• X-Plane's community position is also 1,365 ft. | Render the **observed LHA positions** with the published angle. Keep TCH 68 as the label.<br>The 71-ft gap equals JO 6850.2C para 502's height-group-4 rule: "distance to the GPA/VDA source, plus an additional 300 feet +50, -0". |
| C3 | **Beacon flash rate.** AC 150/5345-12F §3.3.1 gives 22–26 fpm for the L-802A equipment. AC 150/5340-30J §6.1.3 and the AIM give 24–30 fpm. | Use 24 fpm. |
| C4 | **ALSF-2 green threshold count.** The FAA ALSF-2 page and JO 6850.2C §15d say "49". The 6850.2C §200a geometry ("5 foot centers … extends … approximately 45 feet from the runway edge") gives **59** on a 200-ft runway. | 59 (inf).<br>Our counts reproduce the FAA totals elsewhere: 144 white steady lights and 54 red side-row lamps. |
| C5 | **`js/geo.js` comment.** It attributes "TDZL/RCLS Rwys 19L and 28R" to the CS; that text is on the AD and plates. | Comment only; the data there is correct: only 3 ALS, 6 PAPIs and TDZ at 28R and 19L. |

---------------------------------------------------------------------------------------------------------------------

## 5. Runway lighting geometry and colours (std, AC 150/5340-30J)

### 5.1 Edge lights (HIRL, L-862 elevated / L-850C in pavement)

- **Colour.** ac30j 2.3.1.1.2:
  > "The runway edge lights emit white light except in the caution zone (not applicable to visual runways) which is the last 2,000 ft (610 m) of runway or one-half the runway length, whichever is less."
  >
  > "In the caution zone, yellow lights are substituted for white lights; they emit yellow light in the direction facing the instrument approach threshold and white light in the opposite direction."
- **Lateral position.** ac30j 2.3.1.2.1: "at least 2 ft (0.6 m), but not more than 10 ft (3 m), from the edge of the full-strength pavement … On runways used by jet aircraft, we recommend 10 ft (3 m)". The spec uses 10 ft, so the lights are **110 ft from the centreline** *[inf]*. This is consistent with the MALS threshold row of 23 lights on 10-ft centres "coincident with the runway edge lights" (JO 6850.2C 200d).
- **Spacing.** "Longitudinal spacing between light units must not exceed 200 ft (61 m)", uniform and symmetric, referenced to the threshold/runway-end lights. The spec uses the largest uniform spacing of 200 ft or less:

  | Runway | Spacing | Spaces |
  |---|---|---|
  | 10L/28R | 197.83 ft | 60 |
  | 10R/28L | 199.67 ft | 57 |
  | 1L/19R | 196.15 ft | 39 |
  | 1R/19L | 196.59 ft | 44 |

  *[inf: SFO as-built spacing unknown]*
- **Intersections.** 2.3.1.2.2 item 3: "For runways approved for instrument landing system (ILS) CAT III operations with HIRL installed at runway intersections, install L-850C, flush in-pavement light fixtures … to maintain uniform spacing." This applies to 10L/28R (CAT III). On the other runways, a gap over 400 ft gets an in-pavement fixture.
- **Height.** JSON h = 0.36 m *[inf]*. The 14-in limit in ac30j 2.5.2 is written for taxiway fixtures, and the runway elevated-fixture height in AC 150/5345-46 was not transcribed.
- **Displaced thresholds.** ac30j 2.3.2.1.2: "When the runway threshold is displaced, the edge lights located in the area before the threshold emit red light toward the approach." 2.3.2.2.2 item 2: "When the displaced runway area is usable for takeoff, red/yellow runway edge lights are installed". This gives red toward the approach and yellow toward rollout traffic, because the area lies inside the other direction's caution zone (Fig A-5, A-7, A-9).
- **Measurement start.** Fig A-7 and A-9 notes: "Start measurement of 2000 ft … of yellow caution lights from end of runway pavement." and "Start measurement of runway centerline lights from end of runway pavement." Fig A-9 is the case of a displaced threshold not coinciding with the opposite runway end, which is exactly 10L/28R and 10R/28L.
- **Brightness steps (5).** 100 / 25 / 5 / 1.2 / 0.15 % (6.6 / 5.2 / 4.1 / 3.4 / 2.8 A) (ac30j 2.6.4.1).

### 5.2 Threshold and runway-end lights (L-862E / L-850D)

- **Colour.** ac30j 2.3.2.1.1: "Threshold lights emit green light outward from the runway and emit red light toward the runway to mark the ends of the runway."
- **Layout.** 2.3.2.2.1:
  - the lights are 2–10 ft before the threshold (the spec uses 5 ft, *inf*);
  - they are in two groups, "The outermost light in each group is located in line with the runway edge lights", and "the other lights … on 10 ft (3 m) centers";
  - item 6: "precision instrument runways with HIRLs must have four lights in each light group".

  This gives ±80, ±90, ±100 and ±110 ft.
- **Displaced threshold (28L, 28R, 1L, 1R).** 2.3.2.2.2: "The innermost light of each group is located in-line with the line of runway edge lights, and the remaining lights are located outward, away from the runway, on 10 ft (3 m) centers". This gives green unidirectional wing bars at ±110, ±120, ±130 and ±140 ft. Fig A-5 note 6: "Threshold lights are aligned with the approach side edge of the runway threshold marking." The pavement end then carries red-only end lights (Fig A-5 and A-9).
- **ALS threshold bars.** Where an ALS exists, its own threshold bar is added (JO 6850.2C 200; §6).

### 5.3 Runway centreline lights (L-850A, all four runways; C1)

- ac30j 3.3.1.1: "located along the runway centerline at 50 ft (15 m) equally spaced longitudinal intervals", with a tolerance of ±2 ft.
- The line may be offset up to 2.5 ft to one side. SFO's offset is unknown, so the spec uses 0.
- Fig A-34: the first and last lights are "75 FT +12.5 FT -25 FT" from the runway end. The spec centres the array:

  | Runway | End gap | Lights |
  |---|---|---|
  | 10L/28R | 85 ft | 235 |
  | 10R/28L | 65.5 ft | 226 |
  | 1L/19R | 75 ft | 151 |
  | 1R/19L | 75 ft | 171 |
- **Colour coding.** 3.3.1.2: "Alternating red and white lights are installed, starting with red, as seen from 3,000 ft (900 m) to 1,000 ft (300 m) from the runway end, and red lights are installed in the last 1,000 ft (300 m) portion." The coding is per travel direction; the fixtures are bidirectional.
- **Displaced areas.** 3.3.1.3.1: "If the displaced area is equal to or less than 700 feet (110 m) in length, the centerline lights are blanked out in the approach direction." All four SFO displacements (300, 300, 560 and 640 ft) are 700 ft or less. 3.3.1.3.4: with a high-intensity ALS in the displaced area, separate circuiting is not required.

### 5.4 Touchdown zone lights (L-850B; 28R and 19L)

- ac30j 3.3.2.1: "Each light bar consists of three unidirectional lights facing the landing threshold."
- 3.3.2.2: "The rows of light bars extend to 3,000 ft (900 m) … with the first light bars located 100 ft (30 m) from the threshold."
- 3.3.2.3: "toed four degrees toward the runway centerline".
- Fig A-35: "30 LIGHT BARS EQUALLY SPACED @ 100' ±2'". The lights are 5 ft apart, the inner light is 36 ft ±6 in from the centreline, and the inner lights of the two rows are 72 ft apart.
- The bars are referenced to the **landing (displaced) threshold** at 28R.

---------------------------------------------------------------------------------------------------------------------

## 6. Approach lighting systems (std JO 6850.2C Ch. 2; pub type per end)

**Common rules.**
- All lights are aimed away from the threshold, with beams parallel to the runway centreline (207).
- The light plane is the runway threshold centreline elevation (201a).
- Semiflush lights are used "only in displaced threshold, overrun, and other paved operational surfaces" (203a). At SFO that covers:
  - 28R stations 100–300 (the displaced area) plus the blast pad out to the shoreline, about 650 ft (obs);
  - the same at 28L;
  - 19L stations 200 and 400, over the EMAS bed and pad, out to about 500 ft.
- Pier installations (209c): "a minimum of 20 feet must be provided between the light plane and the rigid structure … When the 20-foot separation … cannot be maintained, a NAS Change Proposal (NCP) is required."

### 6.1 28R ALSF-2 (with SSALR mode)

JO 6850.2C 200a:

> "The ALSF-2 consists of light bars, with five equally spaced lights at 100-foot intervals starting 100 feet from the runway threshold and continuing out to 2,400 feet … The centerline light bar at 1,000 feet from the threshold is supplemented with eight additional lights on either side forming a 100 foot wide light bar containing 21 lights … There is also a light bar (four white lights each) on each side of the centerline bar 500 feet from the threshold … In addition, there are light bars (three red filtered lights each) on each side of the centerline bars at each light station in the inner 900 feet. … A row of green filtered lights on 5 foot centers is located within 10 feet of the threshold and extends across the runway threshold and outwards a distance of approximately 45 feet from the runway edge on each side of the runway."

From 200b and Fig 2-1:
- The centreline bars have 40.5-in spacing and there are 24 of them.
- The side rows are "LOCATE SIDE ROW BARS IN LINE WITH TDZ LIGHTS", at 36, 41 and 46 ft.
- The 500-ft barrettes are "EQUIDISTANT BETWEEN SIDE ROW BARS AND CENTERLINE BARS", at 13.9–28.9 ft *[offsets derived, inf]*.
- The 1000-ft bar runs from 15 to 50 ft each side at 5 ft spacing.
- There are 15 sequenced flashers at stations 1000–2400: "These flashing lights emit a bluish-white light and flash in sequence toward the threshold at a rate of twice per second."

Our expansion has 144 white steady lights, 54 red and 15 flashers, which matches the FAA's "144 … 54 … 15" (FAA VGLS ALSF-2 page).

**SSALR mode** (200c: "This configuration is a mode of operation for the ALSF-2/SSALR"):
- a threshold row on 10-ft centres;
- bars at 200, 400 … 1,400 ft;
- "a crossbar 70 feet wide" at 1,000 ft (15–35 ft each side);
- RAIL flashers at 1,600–2,400 ft.

**When each mode runs**: see §9. Brightness is 5 steps, 100 / 20 / 4 / 0.8 / 0.16 %, and the flashers have 3 steps, 100 / 20 / 2.3 % (T2-3). Vertical aiming follows Table 2-1: from 6.1° at the threshold to 7.6° at 2,400 ft, for a 3° glide slope. It is corrected by the angle b = a ± arctan(h/1246 ft) when lights sit off the plane, and limited to 6–9° (206, Fig 2-10). The sequenced flashers are aimed at 6° (206).

### 6.2 28L MALSR, 19L MALSF (MALS core)

JO 6850.2C 200d:

> "The MALS consists of a threshold light bar and seven light bars, with five-lamps each located on the extended runway centerline. The first of the seven light bars is located 200 feet from the runway threshold, and the remaining bars at each 200-foot interval out to 1,400 feet … Two additional light bars are located, one on each side of the centerline bar, 1,000 feet from the runway threshold forming a crossbar 66 feet wide. The spacing between individual lights in all bars is approximately 2½ feet. … for 200 foot wide runways, 23 threshold lights are used. The threshold lights consist of a row of lights on 10-foot centers located coincident with the runway edge lights".

The other two systems add flashers to the MALS:
- **MALSR** (200f): the RAIL is "five sequenced flashers … The first flasher is located 200 feet beyond the approach end of the MALS with successive units located at each 200-foot interval out to 2,400 feet from the runway threshold."
- **MALSF** (200e): "sequenced flashers located on three light bar stations", i.e. the outermost bars at 1,000, 1,200 and 1,400 ft, flashing "at the rate of twice per second".

The steady lights have 3 steps (100 / 20 / 4 %) and the flashers 3 steps (100 / 10 / 2.3 %). Aiming follows Table 2-2, from 3.1° at the threshold to 3.7° at 1,400 ft, shifted by the glide slope minus 3°. For 28L that is −0.15°.

### 6.3 What NAIP 2024 shows on the piers (obs)

The imagery was resampled along each runway at 0.25 m; ±10 ft; positions in ft from the NASR landing threshold.
- **28R.** The pier starts at the shoreline, about 650 ft out. It has **7 equal crossmembers, about 110 ft wide, at 700, 800, 900, 1,000, 1,100, 1,200 and 1,300 ft**, pile caps every 100 ft, and platforms at about 1,150 and 1,390 ft. It continues past the NAIP edge, ~~at about 2,350 ft~~ *[corrected by verifier: the NAIP world grid ends at about 2,650 ft on the 28R centreline. Pile caps are visible every 100 ft out to about 2,600 ft.]*
- **28L.** There are crossmembers at **1,000 ft (about 82 ft wide) and 1,300 ft (about 103 ft)**, and pile caps every 100 ft. The pier continues **past 3,000 ft**, beyond the 2,400-ft MALSR.
- **19L.** The pier runs from the shoreline, at about 500 ft, to about **1,400 ft**, which matches the MALSF length. It has crossmembers at **about 1,000 and about 1,200 ft**.
- **19R.** There is no structure in the water, which is consistent with "no ALS".

The structure alone cannot say which stations are lit. On 28R, a 100-ft crossmember spacing that runs out to 1,300 ft fits the pre-2013 ALSF-2 geometry (referenced to the old threshold) as well as it fits a re-referenced system with spare members. **The spec places lights at the FAA stations from the landing threshold**, which is the FAA rule plus the 2013 memo. The pier geometry goes to the renderer as **structure**. See Q2.

The overlay check on NAIP (`refs/cache/lighting/naip/qa_east.png` and `qa_19.png`, from `tools/env/lighting_naip_measure.py --qa`) confirmed three things:
- the MALSF crossbar and flashers fall on the 19L crossmembers;
- the pier lies on the extended centreline;
- the threshold bars fall on the imaged thresholds.

---------------------------------------------------------------------------------------------------------------------

## 7. PAPI, REIL, beacon, obstruction lights, apron floodlighting

### 7.1 PAPI (std JO 6850.2C Ch. 5, AC 150/5345-28H; pub per end; **obs positions**)

- **Siting.** 502: "The PAPI TCH is selected by siting the PAPI the same distance from the threshold as the virtual source of the instrument approach procedure GPA/VDA, within a tolerance of ±30 feet … For these locations [height group 4], the distance of the PAPI from the threshold must equal the distance to the GPA/VDA source, plus an additional 300 feet +50, -0".
- **Layout.** 506a: "Locate the inboard LHA 50 feet, +25,-0 from the runway edge". 506b: "a lateral separation of 30 feet (9 m)". 500b: LHAs "on the left side of the runway".
- **Observed.** The observed inboard LHAs are 57–77 ft from the edge (the 157–177 ft lateral values in §3.2). The pitch is 30 ft. All units are on the left.
- **Aiming.** Table 5-2 gives, from the unit nearest the runway outward, **+30′ / +10′ / −10′ / −30′** about the glide path. For "Height Group 4 Aircraft on Runway with a Published Glide Path" it is **+35′ / +15′ / −15′ / −35′**. SFO's choice is unpublished, but the HG4 set is likely *[inf]*. Both sets are in the JSON.
- **Photometry.** From AC 150/5345-28H Fig 3-1 (isocandela, white/red):

  | Contour extent | White | Red |
  |---|---|---|
  | ±2° circle | 30,000 cd | 15,000 cd |
  | ±4° H × ±2.5° V | 20,000 | 10,000 |
  | ±6° × ±3° | 14,000 | 7,000 |
  | ±8° × ±3.5° | 8,000 | 4,000 |
  | ±10° × ±4° | 5,000 | 2,500 |

  The contour extents were read from the figure (±0.25°). The red/white transition must be "within 3 minutes of arc at the beam center and within 5 minutes of arc at the beam edges" (§3.2.1). Night modes are about 5 % and 20 % of day intensity (§3.3.8). An LED PAPI emits only within ±10.5° of azimuth; an incandescent one is visible to about ±14° (6850.2C 504b).
- **Day/night switching.** Photo-electric: day mode when the north-sky vertical illuminance reaches 50–60 fc, night mode below 25–35 fc, with a 45–75 s delay (28H §3.3.6).
- **Observation method.** On runway-aligned NAIP crops (0.125 m resample), the orange lamp housings were detected by colour and fitted to a 4-unit row at 30-ft pitch. 4 of 4 units were found at 19L, 19R, 28L and 28R; 10L and 10R were confirmed visually. The accuracy is about ±5 ft (0.6 m source pixels plus NAIP registration of 0.3–1 m, docs/research/imagery.md). OSM nodes at 19L and 10R (1,344 and 1,299 ft) and X-Plane rows agree with the NAIP positions except at 19L, where X-Plane has 1,244 ft. *[verifier: the OSM part is unverifiable. `refs/cache/osm/overpass_ksfo_latest.json` has no PAPI- or VASI-tagged element, `refs/cache/lighting/osm_lighting_query.json` is an Overpass "406 Not Acceptable" error page, and a live Overpass re-query failed (504 on overpass.kumi.systems). The X-Plane rows re-projected here give 10L 1,557, 10R 1,298 (typed "VASI" there), 19L 1,246, 19R 1,043, 28L 1,369 and 28R 1,370 ft.]*

### 7.2 REIL (10L, 1L, 1R; std JO 6850.2C Ch. 4, AC 150/5345-51B)

- 401: "The optimum location is 40 feet from the runway edge and in line with the existing runway threshold lights." It may be up to 75 ft laterally, "30 feet downwind and 100 feet upwind".
- 402a (unidirectional units): "aimed at an angle of 10 degrees vertically and toed out … 15 degrees".
- 51B §3.4.2: the two units flash in sync, within 20 ms. Unidirectional styles flash at 120 fpm and omnidirectional styles at 60 fpm.
- Style E effective intensity is 15,000 / 1,500 / 300 cd in a 30° × 10° beam, ±50 % (Table 1).
- The REIL follows the HIRL step (405a): HIRL steps 1–2 give low, 3 gives medium, and 4–5 give high.
- **The SFO REIL style is unpublished.** NAIP shows candidate pads about 33 ft before the 1L threshold line on both sides (unconfirmed).

### 7.3 Rotating beacon (pub type/schedule; position unknown)

- **Type.** ac30j 6.1.2–6.1.4: "For civil land fields only, the optical system consists of one green lens and one clear lens." The flash rate is "24-30 flashes per minute". L-802A is used "where high intensity lighting systems are used".
- **Photometry.** ac12f Table 1 gives the L-802A minimum effective intensity in white light: 37,500 cd at 1–2°, **75,000 cd at 3–7°** and 37,500 cd at 8–10°. The beam centre is at 5°. Green is at least 0.15 × white. Each flash lasts 75–300 ms.
- **Operation** (jo7110 3-4-18): sunset to sunrise, and in the daytime when conditions are below basic VFR.

### 7.4 Obstruction lights (FAA DOF, pub; fixture type inferred from AC 70/7460-1N)

**Lighted obstacles within 4.5 km.** There are 43 lighted DOF obstacles within 4.5 km (all in `obstructions[]`, world x/z via the WGS 84→frame shift). Key ones:

| DOF OAS | Type | AGL / AMSL ft | Lighting | Accuracy | World x, z (m) | Note |
|---|---|---|---|---|---|---|
| 06-323169 | **CTRL TWR** | **245 / 258** | R (red) | **4D** (±250 ft H, ±50 ft V), verified | −741, 336 | FAA study 2008AWP00286NR. Over 150 ft AGL, so AC 70/7460-1N 5.5.1.2 applies: "At least one red flashing (L-864) light" at the top, and L-810(F) flashing at intermediate levels ("configured to flash simultaneously with the L-864 … at a rate of 30 flashes per minute"). *[corrected by verifier: §5.5 covers "Poles, Towers, and Similar Skeletal Structures" (radio/TV towers, power-line supports). A control tower is a solid building, so §5.6 applies. §5.6.2.2: "At least three L-864 lights should be installed" at the top. §5.6.3: structures of 150–350 ft AGL "should have a second level of steady-burning red-light units installed approximately at the midpoint". §5.6.1 gives 3 units per level (4 if the top is 20–100 ft across). As-built lighting is still unverified.]* The position accuracy is too coarse for placement: use the tower model's top. |
| 06-001451 | BLDG | 135 / 144 | R | 1A | −106, −800 | north field building. 150 ft or less, so steady red L-810, double at the top (5.2.2.1) |
| 06-001425 | BLDG | 126 / 137 | L (type unknown) | 1A | 447, 1852 | |
| 06-001440, 06-028374 … 06-034631 | T-L TWR (power line) | 68–102 | R | 1A–5E | around (−1,000, 1,600) | SW of the 1L/1R ends |
| NAVAID ×~~6~~ **5** *[corrected by verifier: the DOF of 2026-09-18 and `lighting_spec.json` both have 5]* | localizer/GS structures | 8–20 | R | 1A | around 10L/10R and 1L | |

**Photometry.**
- L-810: 32.5 cd red, at least 10° vertical spread centred at +4° to +20° (ac43j 3.4.1.2).
- L-864: 2,000 cd effective ±25 %, 30 fpm ±3, at least 750 cd over 3° vertical (ac43j 3.4.1.5 and Table 3-5).

**Switching.** Lights come on when the north-sky vertical illuminance falls below 60 fc, and before it reaches 35 fc (AC 70/7460-1N 5.3).

### 7.5 Apron floodlighting

- **Current FAA guidance.** AC 150/5360-13A §7.5.2:
  > "Mounted floodlights are the preferred method of lighting the apron area. Floodlights should be sited, aimed, and shielded to avoid glint and glare to pilots and air traffic controllers without reducing the level of illumination in critical areas. To enhance visibility, install uniform illumination across lighted areas using multiple overlapping light sources from different directions to minimize strong ground shadowing."

  It gives no illuminance numbers; it refers to IES RP-37-15, which is not freely available.
- **Cancelled guidance.** The cancelled AC 150/5360-13 (1988), §52 and Table 4-1, gave 5.0 fc (54 lx) for "apron areas" and 0.15 fc (1.6 lx) for the "General aircraft operations area". Floodlights were "typically mounted at a height of 25 to 50 feet (8 to 15 m) with a maximum spacing of 200 feet (60 m)". This is **historical guidance, useful only as an order of magnitude.**
- **SFO masts (pub + obs).** The DOF has **54 poles 60–157 ft AGL within 3 km**: 30 in the 100–109 ft band, 13 at 60–69 ft and 5 at 150–159 ft. Most are surveyed in 2013 at accuracy 1A (±20 ft H, ±3 ft V). **28 of them coincide within 15 m (median 1.9 m) with OSM `man_made=mast` + `tower:type=lighting` nodes.** These are SFO's high-mast apron lights. DOF lighting for them is "U" (unknown), so red obstruction lights are not asserted. *[verifier: that is 49 "U" and 5 "N" (none).]*

  The app's masts in `data/sfo_details.js` are procedural (roughly 120 m spacing, "inferred"). Replace them with the DOF poles (`apron_masts[]`, public domain) and use OSM only as a cross-check. Only a boolean flag is stored from OSM, which respects the ODbL guidance in stands_xcheck.md.

---------------------------------------------------------------------------------------------------------------------

## 8. Taxiway lighting, RWSL, guard lights, stop and clearance bars

### 8.1 RWSL (pub presence; std geometry)

**Presence.**
- The NASR, CS and AD remarks say it is in operation.
- The FAA graphic (`rwsl_SFO.pdf`) shows **THL at 10L, 10R, 28L, 28R, 1L and 1R** (none at 19L or 19R). It shows **REL labels** at these taxiway entrances:

  | Runway | Taxiway entrances with REL |
  |---|---|
  | 10L/28R | R, E ×2, L, C |
  | 10R/28L | Q, K, D, T, E, L, P, **N** *[added by verifier]*, F2, C, F |
  | 1L/19R | M, H ×2, G ×2, F1 ×2, F, C |
  | 1R/19L | F, C, E |

  *[corrected by verifier: the graphic has 28 REL labels, not 27. Taxiway N (PDF word box at x 478, y 382 pt) sits south of 10R/28L between P and the 28L THL. `lighting_spec.json` `rwsl.rel` also has only 27 entries, with no N, and needs regenerating. The runway assignment of the second F1, G and H labels, which sit between 1L/19R and 1R/19L, is ambiguous. Their orange tabs point east, toward 1R/19L, so assigning them to 1L/19R is unverified.]*

- The graphic sits on a satellite image. An 8-point affine fit of its runway polygons to the NASR ends leaves residuals of 40–80 m, so it is schematic.
- Each label is snapped to the nearest same-name, same-runway hold in `data/sfo_details.js` (`rwsl.rel[]`; offsets 28–113 m).

**REL** (ac30j G.2.1–G.2.3, Fig G-1): L-852S red, at least 6 lights.
- "The first light in the taxiway segment is installed 2 ft (0.6 m) prior to the runway holding position marking. The next to last light is installed 2 ft (0.6 m) prior to the runway edge stripe."
- The last light is 2 ft beside the runway centreline lights.
- The lights are 2 ft off the taxiway centreline, on the opposite side from the centreline lights.
- Spacing is at most 50 ft and at least 12.5 ft.

**THL** (ac30j G.2.4, Fig G-3): L-850T red, 1,500 cd.
- "THLs begin at a point that is 375 ft (±25 ft) … from the runway threshold and are displaced 6 ft (2 m) on either side of the runway centerline lights."
- They sit every 100 ft: "There will be 1500 ft (457.2 m) of lights (32 lights) in the array."
- *[inf]* The spec references the **runway end** (start of the takeoff roll) because TORA is full length at every THL end. At 28R, 28L, 1L and 1R the landing-threshold reading would shift the array by 300–640 ft.

**Behaviour** (AIM 2-1-6, quoted in `operation.rwsl`):
- RELs light for departures above about 30 kt and for arrivals within about 1 mile. They go out 3–4 s before the aircraft reaches the intersection, and after the system declares it airborne.
- THLs light when a departure is in position and the runway ahead is occupied.
- Intensity is automatic, operated continuously (jo7110 3-4-19).

### 8.2 Taxiway centreline (green; L-852 family)

**Colour coding** (ac30j 4.3.2.1.1):
> "Alternate green and yellow lights are installed from the runway centerline (beginning with a green light) to one centerline light position beyond the runway hold or ILS critical area hold position ending with a yellow light."

Lead-on lights (4.3.2.2) and crossings (4.3.2.3) use the same pattern.

**Spacing** (Table 4-1), for ≥1,200 RVR and <1,200 RVR:

| Segment | ≥1,200 RVR | <1,200 RVR |
|---|---|---|
| Straight | 100 ft | 50 ft |
| Curve radius ≥1,200 ft | 100 ft | 50 ft |
| Curve radius 400–1,199 ft | 50 ft | 25 ft |
| Curve radius 75–399 ft | 25 ft | 12.5 ft |
| Acute-angled exits | 50 ft | 50 ft |

On acute-angled exits, the lead-off lights begin 200 ft before the point of curvature (4.3.4).

**Beams** (4.3.9). On straight sections the beam is parallel to the path. Bidirectional fixtures on curves follow the tangent. Unidirectional fixtures on curves are toed in to meet the centreline about 4 spacings ahead.

**Fixtures** (4.8.5.1): L-852A/B/E on routes at or above 1,200 RVR; L-852C/D/F on low-visibility routes.

**SFO specifics are NOT published per taxiway (Q4).** X-Plane KSFO (community data) has line types 101 (green CL) ×837, 102 (blue edge) ×732, 103 (amber hold lines) ×108 and 105 (alternating green/amber) ×81. That is indicative only.

### 8.3 Taxiway edge (blue)

- L-861T elevated, 2 cd minimum at 0–6°, visible from 15° to 90°; or L-852T inset.
- 2–10 ft outside the full-strength pavement.
- Spacing follows Table 2-1: straight sections over 200 ft at 200 ft or less; 100–200 ft sections at 100 ft or less.
- Curves follow Fig A-16 by radius, with "at least three edge lights" on arcs over 30° (2.5.3.2.1).
- Taxiway curve indicators are placed 50 ft before the point of tangency (2.5.3.2.9).

### 8.4 Runway guard lights, stop bars, clearance bars (std; SFO use unverified)

- **Elevated RGL, L-804.** A pair of alternately lit yellow lamps each side of the taxiway, 10–17 ft outside the edge.
  - Aim: at the cockpit 150–200 ft before the hold, 5–10° up (ac30j 4.4.5–4.4.6).
  - Photometry: 3,000 cd within ±8°, at least 1,000 cd within ±15°.
  - Flashing: "alternately illuminated at the rate of 45-50 flashes per minute" with a 50 % duty cycle. The off-state falls to 17 % or less (ac46f 3.4.3).
- **In-pavement RGL, L-852G.** A row across the whole taxiway, 2 ft on the holding side of the hold marking, at 9 ft 10 in centres.
  - Photometry: 1,000 cd within ±24° H and 1–10° V.
  - Flashing: "even-numbered lights in the row pulse simultaneously and, as they extinguish, the odd-numbered lights pulse", with "a pulse at a rate of 30-32 flashes per minute" (ac30j 4.8.6.2.5).
- **Stop bar.** Red in-pavement L-852S (300 cd), 2 ft on the holding side at 9 ft 10 in centres, plus an elevated red L-862S each side (2,000 cd).
  - Stop bars are "required for operations below 600 ft (183 m) RVR" (4.1.3.3).
  - AIM: "Pilots should never cross a red illuminated stop bar".
- **Clearance bar.** "a row of three in-pavement yellow lights" on 5-ft centres (4.7.1, 4.7.3.1).

---------------------------------------------------------------------------------------------------------------------

## 9. Day, night and weather operating logic (verified: JO 7110.65BB §3-4)

This is the FAA's rule set for the tower. SFO facility directives may override it; those directives are not public. Visibility is prevailing surface visibility in SM, or the RVR equivalent where noted. The full tables are in `lighting_spec.json` under `operation`.

| System | On | Intensity step: day | Intensity step: night |
|---|---|---|---|
| HIRL / RCL / TDZL (TBL 3-4-8) | edge lights: sunset–sunrise for runways in use; by day when visibility < 2 SM (3-4-10) | 5: <1; 4: 1–<2; 3: 2–<3; 1–2: on request | 4: <1; 3: 1–<3; 2: 3–5; 1: >5 |
| ALS (TBL 3-4-5) | night when serving the landing runway; by day when ceiling < 1,000 ft or visibility ≤ 5 SM (3-4-5) | 5: <1 (or RVR ≤ 6,000); 4: 1–<3; 3: 3–<5; 2: 5–<7 | 3: <1 (or RVR ≤ 6,000); 2: 1–3; 1: >3 |
| **ALSF-2 vs SSALR** (3-4-9) | "When the prevailing visibility is 3/4 mile or less or the RVR is 4,000 feet or less, operate the ALSF-2 … Operate the SSALR system when the conditions … are not a factor." | | |
| Sequenced flashers (3-4-7) | "When the visibility is less than 3 miles and instrument approaches are being made"; "SFL … cannot be operated when the ALS is off" | follows ALS step (JO 6850.2C T2-3: steady steps 4–5 → high, 3 → medium, 1–2 → low) | ″ |
| MALSR 3-step (TBL 3-4-7) | | 3: <2; 2: 2–5 | 3: <1; 2: 1–<3; 1: ≥3 |
| REIL (TBL 3-4-1) | "When the associated runway lights are lighted" | 3: <2; 2: 2–5 | 3: <1; 2: 1–<3; 1: ≥3 |
| PAPI (TBL 3-4-4) | continuous (photo-electric) | step 4 | step 3 |
| Taxiway lights, 5-step (TBL 3-4-12) | | 5: <1 | 4: <1; 3: ≥1 |
| Obstruction lights (3-4-17) | sunset–sunrise (photocell 60→35 fc per AC 70/7460-1N) | | |
| Beacon (3-4-18) | sunset–sunrise, and by day below basic VFR | | |
| RWSL (3-4-19) | continuous, automatic intensity | | |

Twilight, where needed, is "from sunset to 30 minutes after sunset and from 30 minutes before sunrise to sunrise" (TBL 3-4-3).

**Renderer consequences:**

1. On a clear night with visibility over 3 SM, SFO shows:
   - HIRL, RCL and TDZ at step 1: 0.15 % of peak; *[corrected by verifier: TBL 3-4-8 gives night step 1 only for "More than 5 miles". From 3 to 5 miles inclusive the setting is step 2, 1.2 % (ac30j 2.6.4.1). The ALS and SSALR items below are right for anything over 3 SM.]*
   - the 28R system as **SSALR without the red side rows or the 500-ft bar**, at step 1 (0.16 %);
   - **no rabbits** unless visibility is under 3 SM or a pilot asks;
   - the PAPIs at night mode, about 5–20 %.
2. In fog, with RVR ≤ 4,000 ft, the full ALSF-2 appears, with the rabbits and steps 3–5.
3. By day with visibility over 5 SM and a ceiling at or above 1,000 ft, the ALS and runway edge lights are off. The PAPIs are on in day mode, and the RWSL keeps operating.

---------------------------------------------------------------------------------------------------------------------

## 10. Photometry, colours, visibility model

### 10.1 Fixture photometry (AC 150/5345-46F Tables 3-1/3-2/3-3)

Values are the minimum average intensity in the main beam. Every point in the beam must be at least 50 % of it, and the average may be at most 3× the specification (§3.3). H is horizontal (for toed fixtures, + is toward the centreline) and V is elevation.

| Type | Use | Main beam H × V (deg) | 10 % curve | cd by colour |
|---|---|---|---|---|
| L-850A | runway CL | ±5 × 0.2–9 | ±7 × −4–13 | W 5,000, R 750 |
| L-850B | TDZ | −1–9 × 2–9 | −3–11 × −0.5–11.5 | W 5,000 |
| L-850C | edge, in pavement | −2–9 × 0.2–7 | −4–11 × −2.5–9.5 | W 10,000, Y 5,000, G 3,300, R 1,500 |
| L-850D | threshold/end, in pavement | G −2–9 × 1–10; R ±6 × 0.2–4.7 | R ±7.5 × −2.5–7.5 | G 3,300, R 2,500 |
| L-850E | MALS/threshold green | ±6 × 1–9 | — | G 5,000 (min) |
| L-850T | THL | ±5 × 0.2–9 | ±7 × −4–13 | R 1,500 (traffic-signal red) |
| L-852A/B | taxiway CL ≥1,200 RVR | ±10 × 1–4 / ±30 × 1–4 | ±16 / ±30 × 0.5–10 | G, Y 20 |
| L-852C/D | taxiway CL <1,200 RVR | ±3.5 × 1–8 / ±30 × 1–10 | | G, Y 200 / 100 (W 150) |
| L-852G | in-pavement RGL | ±24 × 1–10 | ±30 × 0.5–13 | Y 1,000 |
| L-852S | stop bar / REL | ±24 × 1–10 | ±30 × 0.5–13 | R 300 |
| L-852T / L-861T | taxiway edge | omni, 1–6 / 0–6 | visible 15–90 | B 2 (min) |
| L-862 | HIRL edge, elevated | −2–9 × 0–7 | −4–11 × −2.5–9.5 | W 10,000, Y 5,000, G 2,500, R 2,000; plus ≥50 cd W omni to 15° |
| L-862E | threshold/end, elevated | R ±6 × 0.2–4.7; G −2–9 × 1–10 | R ±7.5 × −2.5–7.5 | R 2,500, G 3,200 |
| L-862S | elevated stop bar | ±7 × ±4 | ±14 × ±8 | R 2,000 |
| L-804 | elevated RGL | circle ±8 | circle ±25 | Y 3,000 (≥1,000 within ±15) |

**Not obtainable from FAA public documents:**
- the ALS steady-burning lamp intensity. JO 6850.2C 204 names FAA-E-2408 Q20A/PAR-56 300 W lamps with a "12 degree vertical beam spread" (206a) for the ALSF-2, and PAR-38 spots for the MALS;
- the sequenced-flasher effective intensity (FAA-E-2998 / FAA-E-2689).

A vendor listing gives about 38,000 cd at centre for Q20A/PAR56/C. **That figure is unverified; do not treat it as FAA data.**

### 10.2 Aviation colours (EB 67D §2.1.1–2.1.2, CIE 1931 xy)

| Colour | Boundary intersection points | Area centroid | Linear sRGB (derived, max = 1) |
|---|---|---|---|
| white | (0.320, 0.356) (0.440, 0.433) (0.440, 0.383) (0.320, 0.292) | 0.378, 0.364 | 1.000, 0.614, 0.411 |
| green ("ICAO Modified") | (0.014, 0.750) (0.129, 0.600) (0.312, 0.600) (0.302, 0.692) | 0.180, 0.665 | 0, 1, 0.036 *(outside sRGB)* |
| blue ("ICAO") | (0.090, 0.137) (0.186, 0.214) (0.233, 0.167) (0.148, 0.025) | 0.161, 0.129 | 0, 0.159, 1 *(outside)* |
| yellow ("CIE S 004/E-2001") | (0.547, 0.452) (0.536, 0.444) (0.593, 0.387) (0.613, 0.387) | 0.573, 0.417 | 1, 0.189, 0 *(outside)* |
| red ("Restricted Red") | (0.680, 0.320) (0.660, 0.320) (0.690, 0.290) (0.710, 0.290) | 0.685, 0.305 | 1, 0, 0 *(outside)* |

The red-obstruction light chromaticity is "purple boundary y = 0.980 - x, yellow boundary y = 0.335" (ac43j 3.3.3). White obstruction lights are 4,000–8,000 K. RWSL red (L-852S, L-850T) and RGL yellow (L-852G, L-804) are ITE traffic-signal colours (46F notes g).

### 10.3 Visibility vs distance (for the weather renderer)

The FAA calibration points are in AC 70/7460-1N App. B, Table B-1. That table "indicates at what distance the various candela intensities are visible":

| Period | Meteorological visibility | Intensity → distance |
|---|---|---|
| Night | 3 SM | 2,000 cd → 3.1 SM; 1,500 cd → 2.9 SM; 32 cd → 1.4 SM |
| Day | 1 SM | 200,000 cd → 1.5 SM; 100,000 cd → 1.4 SM; 20,000 cd → 1.0 SM |
| Day | 3 SM | 200,000 cd → 3.0 SM; 100,000 cd → 2.7 SM; 20,000 cd → 1.8 SM |

Recommendation *[inf]*: model point lights with Allard's law, E = I·e^(−σd)/d², with σ from the visibility (Koschmieder, σ ≈ 3.0/V). Tune the day and night threshold illuminance E_T until Table B-1 is reproduced within about 10 %.

A quick fit shows these rows do not follow a single E_T. With σ = 3/V, the night rows imply E_T ≈ 3.6e-6 lx for 1,500–2,000 cd but ≈ 1.6e-6 lx for 32 cd. So use the table as acceptance points rather than as a formula. The ICAO/RVR threshold formulas were not verified here, so defer to the weather research.

---------------------------------------------------------------------------------------------------------------------

## 11. Method notes (reproducible)

- **NASR.** The per-end values come from `APT_RWY_END.csv` and the per-runway values from `APT_RWY.csv`, with `ARPT_ID == 'SFO'`. The code meanings come from "APT DATA LAYOUT.pdf" in the same zip, e.g. "RWY_END_LGTS_FLAG - Runway End Identifier Lights (REIL) Availability" and "RWY_LGT_CODE - Runway Lights Edge Intensity … HIGH".
- **Frame.** World coordinates come from `tools/geo_frame.py`, identical to `js/geo.js`. DOF and OSM coordinates are WGS 84 and go through `wgs84_to_world`. NASR and NAIP are NAD83.
- **NAIP measurements.** `tools/env/lighting_naip_measure.py [--qa]` reproduces them. It makes runway-aligned resamples of `naip_2024_world_0.5m_bgr.npy` and writes `refs/cache/lighting/naip/papi_fit.json` plus the crops. Axis: along from the NASR landing threshold, lateral positive to the left.
  - PAPI: the orange lamp housings (R−G > 15, R−B > 30) were fitted to 4 units at 30-ft pitch.
  - Pier crossmembers: read visually on 0.25 m resamples.
- **RWSL graphic.** The vector runway polygons and label boxes were read with PyMuPDF. The 8-point affine fit to the NASR ends has residuals of 41–80 m.
- **Regenerate** with `python3 tools/env/build_lighting_spec.py`. It needs the NASR CSVs, the DOF zip and, optionally, the OSM cache and `data/sfo_details.js`.

### `lighting_fixtures.json` format

It holds `groups[]`, one per system and end. Each group has `system`, `end`, `type`, `prov`, `emit` (the face definitions: `seen_by` end, and `emit_dir` as a world unit vector [x, z]), `n` and `pts`.

- For edge and centreline lights, a point is `[x, z, h, colour seen by face0, colour seen by face1]`. Colour codes are W / Y / G / R / B, and `-` means blanked.
- ALS points carry the station, and flashers also carry the firing order.
- PAPI points carry the aiming angle.

Counts: edge 392; RCL 783; TDZ 360; threshold/end/wing bars 96; ALS 416 (28R 272, 28L 73, 19L 71); PAPI 24; REIL 6; THL 192.

---------------------------------------------------------------------------------------------------------------------

## 12. Gap analysis: current renderer (`js/anim/lights.js`) vs this spec

| # | Current | Should be |
|---|---|---|
| 1 | Edge lights all white, every 60.96 m from the runway start, 1 m outside the pavement | Yellow toward instrument-approach traffic in the last 2,000 ft. Red toward the approach in the 28L/28R/1L/1R displaced areas. About 110 ft (33.5 m) from the centreline, at the spacings in §5.1. |
| 2 | Centreline: red/white alternation within 300 m of *either* end and alternation in the last 1,000 ft; the reverse face always white; first light at 15 m | Per direction: white; alternating red/white from 3,000 to 1,000 ft remaining; red in the last 1,000 ft. Blanked toward the approach in displaced areas. First light 50–87.5 ft from the pavement end. |
| 3 | 19 green lights at 3.2 m across the runway at every threshold, and 19 red at every runway start | 8 split G/R fixtures (4 per side at 10 ft, outermost in line with the edge lights). Displaced ends: green wing bars outboard at the threshold and red-only end lights at the pavement end. Plus the ALS threshold bars at 28R, 28L and 19L only. |
| 4 | TDZ bars from 30 m to 900 m | 100 to 3,000 ft, which is right to within 1 bar; add the 4° toe-in. |
| 5 | PAPI at TCH/tan (geo.js), 15 m + j × 9 m from the edge, ±30′/±10′ | Use the observed LHA positions (the 28R error is 22 m). Aim at HG4 ±35′/±15′ (inf) and give the transition a 3′ width. |
| 6 | ALS: the same 8-light-per-side 1000-ft bar for MALSR/MALSF; no 500-ft bar; no threshold bar; no SSALR mode; all lights at GROUND_Y + 1.4 m | MALS crossbar of 5 + 5 lights at 23–33 ft; the ALSF-2 500-ft bar; green threshold bars; SSALR/ALSF-2 switching by weather (§9); light plane = threshold elevation on the observed pier structure. |
| 7 | Rabbit always on at night | On only when visibility < 3 SM (or on request) and the ALS is on. |
| 8 | Intensities are arbitrary numbers | cd per fixture type and colour (§10.1) × step percentage (§9) × a beam-pattern falloff. |
| 9 | Taxiway: sparse blue edge lights at 45 m, ±13.5 m from the centreline, on every taxiway | SFO taxiway lighting is unverified (Q4). At minimum: green centreline lights with lead-on/off colour coding at the runway exits; blue edges spaced per Table 2-1 and Fig A-16. |
| 10 | Missing systems | REIL (10L, 1L, 1R), RWSL THL/REL, the beacon (position open), obstruction lights (the tower top red L-864 flashing at 30 fpm), and the apron masts replaced with the 54 DOF poles. |

---------------------------------------------------------------------------------------------------------------------

## 13. Recommendations

1. **Drive the lighting from `tools/env/lighting_fixtures.json`**, not from hard-coded rules in JS. Honour `prov`: it is fine to render `std` and `inf`, but label them in the QA overlay.
2. **Implement the §9 state machine as the lighting controller**, with day/night from the sun, visibility, RVR and ceiling from the METAR, and the runway configuration from traffic. Include the SSALR/ALSF-2 switch and the SFL rule. This one piece of logic gives believable day, night and fog.
3. **Render lights as directional point sprites.** Use the fixture's main-beam and 10 % ellipses, the colour's linear sRGB (or its wide-gamut xy if the three.js r186 pipeline supports it), the cd × step value, and Allard attenuation tuned to AC 70/7460-1N Table B-1. Model the PAPI as a white/red split at the aiming angle, and the flashers with an effective-intensity pulse.
4. **Use the observed geometry:** the PAPI LHAs from NAIP, the ALS pier structures (28R, 28L, 19L), and the DOF apron masts and obstruction lights. Drop the procedural masts.
5. **Snap the RWSL RELs to the matched holds** (`rwsl.rel[].hold`) and build each array per ac30j App. G. The THLs use the runway-end reference until Q-THL is resolved.
6. **Ask the owner** for photos or night imagery of four things: the 28L/28R piers at night (which stations are lit), the rotating beacon, runway centreline fixtures on 10R/28L and 1L/19R, and the taxiway lighting at a few holds.
7. Run a visual QA pass: render dusk, night-clear and night-fog views of the 28 approach and compare against real night photos from the owner. Include `docs/qa/ref` if such photos exist.

## 14. Open questions

1. **Beacon position.** No FAA or community source has it; ask the owner or find a photo. Until then, do not draw it.
2. **Which ALS stations are lit on the 28L/28R piers?** The structure (crossmembers at 700–1,300 ft on 28R, and at 1,000/1,300 ft on 28L with the pier running past 3,000 ft) does not settle it. The spec uses the FAA stations from the landing threshold.
3. **Centreline lights on 10R/28L and 1L/19R.** The CS and NASR say yes; the AD and plate note implies only 19L/28R.
4. **SFO taxiway lighting per taxiway:** the centreline/edge mix, lead-on/off colour coding, clearance and stop bars, the SMGCS low-visibility routes, and elevated vs in-pavement RGLs. No FAA publication was found.
5. **REIL style**, unidirectional or omnidirectional. The 1L pads are candidates.
6. **PAPI aiming set**, standard or HG4.
7. **Photometry of the ALS lamps, flashers and apron floodlights.** No public FAA source was found.
8. **THL reference point**: runway end or landing threshold, at the displaced-threshold ends.
9. **SFO tower facility directives** that override the JO 7110.65 steps.

---------------------------------------------------------------------------------------------------------------------

## 15. Verification (adversarial check)

Independent fact-check, 24 Sep 2026. Every cited primary source was downloaded again into `refs/cache/lighting_verify/` (gitignored). The re-downloaded CS, AD, RWSL PDF, 6850.2C, ac30j, 46F, 28H, 51B, 12F, 43J, EB 67D, AC 70/7460-1N, JO 7110.65BB §3-4 and AIM §2-1 are byte-identical to the author's cache where the author cached them.

Also re-downloaded:
- the NASR `03_Sep_2026_APT_CSV.zip` from nfdc.faa.gov;
- the d-TPP 2609 metafile, and the IL28R, IL28L, IL19L, R10L, RY10R, RY19R and RZ19R plates;
- the FAA DOF (DOF.CSV 2026-09-18);
- the FAA ALS page and the NTSB-hosted 2013 SFO memo.

Tools re-run (outputs written to the session scratchpad; the author's files were not overwritten):
- `build_lighting_spec.py` reproduces `lighting_fixtures.json` exactly (only `generated` differs) and gives the same counts.
- `lighting_naip_measure.py` `papi_fit` was run with the shipped seeds, with seeds at the TCH/tan distances and with ±40-ft offsets. It converges to the same positions every time.

Verdicts: **confirmed**, **refuted** (corrected inline above, marked *[corrected by verifier]*) or **unverifiable**.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| V1 | CS: HIRL CL on all 4 runways; REIL 10L/1L/1R; ALSF2+TDZL 28R; MALSR 28L; MALSF+TDZL 19L; PAPI P4L angles/TCH as tabled; RVR-TMR everywhere; displaced thresholds 300/300/560/640; "Rwy status lgts in operation"; "Attended continuously" | confirmed | sw_275_03SEP2026.pdf re-fetched, text identical to §3.1 |
| V2 | NASR: CL flag Y at all 8 ends; `RWY_END_LGTS_FLAG` = REIL (Y at 1L, 1R, 10L); TDZ Y at 28R/19L; ALS ALSF2/MALSR/MALSF; VGSI P4L ×6 with the tabled angle/TCH; RWY_LGT_CODE HIGH ×4; BCN WG, SS-SR; WIND Y-L; LGT_SKED blank; remark "RWY STATUS LGTS IN OPN." | confirmed | re-downloaded NASR 2026-09-03 zip; "APT DATA LAYOUT.pdf" defines RWY_END_LGTS_FLAG as "Runway End Identifier Lights (REIL) Availability" |
| V3 | AD AL-375 note "TDZL/RCLS Rwys 19L and 28R / REIL Rwys 1R, 1L and 10L / HIRL …"; RWSL note; conflict C1 | confirmed | 00375ad.pdf (SW-2 03 SEP–01 OCT 2026) re-fetched. The plates carry the same line (the RZ19R text extraction reads "TDZE/RCLS", not checked visually) |
| V4 | Plate VGSI notes and GP/TCH (28R 3.00/55, 28L 2.85/53, 19L 3.00/55, 10L 3.00/55, 10R TCH 60, 19R 3.15/55); amendment numbers | confirmed (nuance) | d-TPP 2609 plates. 28L, 19L and 10L also say "not coincident"; annotated in §3.2 |
| V5 | No IAP to 1L/1R; 22 SFO IAPs | confirmed | d-TPP 2609 metafile lists 22 IAP entries, none for 1L or 1R |
| V6 | JO 6850.2C quotes (200a–f, 203a, 209c, 401, 402a, 502, 504b, 506a/b), Table 2-1/2-2 aiming, Fig 2-10 (d = 1,246 ft), Table 2-3 steps and flasher mapping, Table 5-2 HG4 ±35′/±15′, §15d "49 … 54 … 144 … 15" | confirmed | text search of the re-fetched order: every quoted phrase present verbatim |
| V7 | ALSF-2 expansion = 144 white + 54 red + 15 flashers; 59 green on a 200-ft runway (C4) | confirmed | recount 24×5 + 2×8 + 2×4 = 144; 9×2×3 = 54. 290 ft / 5 + 1 = 59 (the FAA's 49 fits a 150-ft runway: 240/5 + 1). The regenerated fixtures give 28R 272 = 144 + 54 + 15 + 59 |
| V8 | ac30j quotes (2.3.1.1.2, 2.3.1.2.1/2, 2.3.2.1/2, 3.3.1.x, 3.3.2.x, Fig A-7/A-9/A-34/A-35 notes, 2.6.4.1 steps, 4.1.3.3, 4.3.2.1.1, Table 4-1, 4.7.1, 4.8.6.2.5, 6.1.2–6.1.4, G.2.3, G.2.4) | confirmed | re-fetched 150-5340-30J.pdf. The ">400 ft gap" rule for non-CAT III HIRL is item 5 of 2.3.1.2.2 |
| V9 | AC 150/5345-46F Tables 3-1/3-2 candela and beam values; L-804 45–50 fpm, off-state ≤17 %; ITE traffic-signal colour notes | confirmed | re-fetched PDF pp. 3-2 to 3-5 and 3-16/3-17 |
| V10 | AC 150/5345-28H Fig 3-1 contours (30k/15k ±2°, 20k/10k ±4×±2.5, 14k/7k ±6×±3, 8k/4k ±8×±3.5, 5k/2.5k ±10×±4); 3′/5′ transition; night 5 %/20 %; photocell 50–60 / 25–35 fc, 45–75 s | confirmed | figure rendered from the re-fetched PDF (p. 12) and read directly |
| V11 | AC 150/5345-51B: Styles A/C/E 120 fpm, B/D/F 60 fpm, sync ≤20 ms, Style E 15,000/1,500/300 cd in 10°×30°, ±50 % | confirmed | §3.4.1–3.4.2, Table 1 |
| V12 | AC 150/5345-12F: L-802A 37,500/75,000/37,500 cd, green ≥0.15×, 22–26 fpm, 75–300 ms; ac30j/AIM 24–30 fpm (C3) | confirmed | §3.3.1–3.3.3, Table 1; AIM 2-1-9 |
| V13 | AC 150/5345-43J: L-810 32.5 cd; L-864 2,000 cd ±25 %, ≥750 cd over 3°, 30 ±3 fpm; red boundaries y = 0.980 − x, y = 0.335; white 4,000–8,000 K | confirmed | §3.3.3, 3.4.1.2, 3.4.1.5, Table 3-5 |
| V14 | AC 70/7460-1N (2026-08-11, cancels -1M): 5.3 photocell 60/35 fc; 5.2.2.1; Table B-1 values | confirmed | re-fetched PDF; cancellation is on the FAA AC page (`acpage_70_7460-1.html`) |
| V15 | Tower lighting per AC 70/7460-1N **5.5.1.2** (one L-864 + L-810(F) intermediates) | **refuted** | §5.5 is for skeletal structures; a building/solid structure falls under §5.6 (≥3 L-864, steady L-810 midpoint level). Corrected in §7.4 |
| V16 | DOF: CTRL TWR 06-323169 245/258 ft, R, 4D, study 2008AWP00286NR; 43 lighted obstacles within 4.5 km; 54 poles 60–157 ft within 3 km (30 / 13 / 5 by band; 49 at 1A, 2013); 28 within 15 m of OSM lighting masts | confirmed | re-downloaded DOF.CSV (2026-09-18) and the cached Overpass extract (70 `tower:type=lighting` masts) |
| V17 | "NAVAID ×6" lighted | **refuted** (minor) | 5 in the DOF and in `lighting_spec.json`. Also, one T-L TWR (06-001450, 138 ft AGL, west of the field) lies outside the "68–102 ft" SW cluster in the table |
| V18 | EB 67D intersection points; centroids and linear sRGB | confirmed | re-fetched PDF §2.1.1–2.1.2; centroids and sRGB recomputed independently (same values to 3 dp) |
| V19 | JO 7110.65BB §3-4 tables (TBL 3-4-1, -4, -5, -7, -8, -12), 3-4-5, 3-4-7, 3-4-9, 3-4-10, 3-4-17/18/19, twilight definition | confirmed | re-fetched `chap3_section_4.html` (7110.65BB). Nuance: under 3-4-9, ALSF-2 at ≤¾ SM or RVR ≤4,000 is run "as requested by the pilot / as you deem necessary"; SSALR otherwise |
| V20 | §9 renderer consequence: night, visibility >3 SM → HIRL/RCL/TDZ step 1 | **refuted** | TBL 3-4-8 night step 1 is ">5 miles"; 3–5 miles inclusive is step 2 (1.2 %). Corrected in §9 |
| V21 | AIM 2-1-6 RWSL behaviour (~30 kt, ~1 mile, 3–4 s, "airborne"); stop-bar note | confirmed | re-fetched `chap2_section_1.html` |
| V22 | RWSL graphic: THL at 10L, 10R, 28L, 28R, 1L, 1R (none at 19s); PDF created 2017-11-13 | confirmed | re-fetched SFO.pdf, rendered and inspected |
| V23 | RWSL graphic: **27** REL labels, per-runway list in §8.1 | **refuted** | 28 taxiway labels; N (10R/28L) was missing. Runway assignment of the between-runway F1/G/H labels is unverified. `rwsl.rel` in the spec also lacks N |
| V24 | NAIP PAPI positions (10L 1,556; 10R 1,298; 19L 1,344; 19R 1,023; 28L 1,369; 28R 1,369 ft), lateral 157–177 ft inboard, 30-ft pitch; 4/4 hits at 19L, 19R, 28L, 28R | confirmed | fit re-run with independent seeds (TCH/tan, ±40 ft) returns identical values. The 28R crop shows four orange LHAs on a pad at 1,369 ft and nothing at 1,298 ft; the 10L/10R crops show four faint units at the fitted distances |
| V25 | 28R PAPI 71 ft beyond TCH/tan; five ends within ±31 ft; app 22 m off | confirmed | arithmetic: +30, 0, −11, −31, +23, +71 ft; 71 ft = 21.6 m |
| V26 | 1,369 ft "equals" GS source 1,049 + 300 (HG4) | confirmed with correction | inside the 1,349–1,399 ft window rather than equal to it. HG4 also fits 28L, and 19L is 5 ft short, so HG4 does not single out 28R. Annotated in §1 |
| V27 | X-Plane PAPI 28R 1,365 ft, 19L 1,244 ft | confirmed | re-projected apt.dat row-21 points: 28R 1,370, 19L 1,246 ft (difference within the WGS 84/NAD83 shift) |
| V28 | OSM PAPI nodes at 19L/10R (1,344 / 1,299 ft) | **unverifiable** | no PAPI-tagged element in the cached Overpass extract; the author's `osm_lighting_query.json` is a 406 error page; live Overpass re-query failed (504) |
| V29 | Piers: 28R crossmembers 700–1,300 ft every 100 ft (~110 ft wide), shoreline ~650 ft, platforms ~1,150/~1,390 ft; 28L crossmembers 1,000 (~82 ft) and 1,300 (~103 ft), pier to ≥3,000 ft; 19L pier ~500–1,400 ft, crossmembers ~1,000/~1,200 ft; 19R none | confirmed | own runway-aligned NAIP strips: 28R members at 695–1,295 ft; 28L at 1,001/1,300 ft (widths 80/104 ft) with pile caps to the grid edge (~3,050 ft); 19L 519–1,420 ft, members at 1,012/1,214 ft; 19R open water |
| V30 | 28R pier "continues past the NAIP edge, at about 2,350 ft" | **refuted** (minor) | the world-grid edge on the 28R centreline is at about 2,650 ft; pile caps are visible to about 2,600 ft. Corrected in §6.3 |
| V31 | 2013 SFO memo: thresholds relocated 27/29 Jun 2013; "replacement of the Runway 28L approach lighting system, needed changes to the Runway 28R approach lighting system"; new PAPIs by 2 Jul 2013 | confirmed | re-fetched NTSB docket PDF (identical) |
| V32 | FAA ALS page "247 … 49 … 54 … 144 … 15" | confirmed | re-fetched https://www.faa.gov/about/office_org/headquarters_offices/ato/service_units/techops/navservices/lsg/als |
| V33 | AC 150/5360-13A §7.5.2 quote; cancelled AC 150/5360-13 Table 4-1 (5.0 fc apron, 0.15 fc general AOA; 25–50 ft masts, ≤200 ft spacing) | confirmed | re-fetched 13A (identical); 1988 text from the author's OCR cache, where the OCR table layout is garbled but the values match |
| V34 | Fixture counts (edge 392, RCL 783, TDZ 360, thr/end/wing 96, ALS 416 = 272/73/71, PAPI 24, REIL 6, THL 192; total 2,269); edge spacings and RCL end gaps | confirmed | regenerated; hand recount of the RCL (235/226/151/171), MALSR 73 = 23 + 35 + 10 + 5 and MALSF 71 |
| V35 | §12 gap analysis of `js/anim/lights.js` (60.96 m white edge 1 m out, RCL from 15 m with a white reverse face, 19-light bars at 3.2 m, TDZ 30–900 m, PAPI TCH/tan at 15 + 9j m ±30′/±10′, same 8/side 1000-ft bar for all ALS, lights at GROUND_Y + 1.4 m, 45 m blue edges at ±13.5 m); C5 geo.js comment | confirmed | read `js/anim/lights.js` and `js/geo.js` at HEAD |
| V36 | RWSL graphic affine-fit residuals 40–80 m; REL snap offsets 28–113 m | partly verified | the snap offsets (`dist_m`) are in the regenerated spec (28–113 m); the affine residuals were not re-derived |

**Net result.** The FAA-sourced facts, quotes, photometry, colour limits and tower operating rules are accurate. The NAIP PAPI and pier observations reproduce. Five statements were wrong:
- the REL count (28, not 27; taxiway N was missing, and the spec needs regenerating);
- the tower obstruction-light section (§5.6, not §5.5);
- the night HIRL step at 3–5 SM (step 2, not step 1);
- the NAIP edge on the 28R pier (about 2,650 ft, not 2,350 ft);
- the lighted-NAVAID count (5, not 6).

One cross-check (OSM PAPI nodes) is unverifiable.
