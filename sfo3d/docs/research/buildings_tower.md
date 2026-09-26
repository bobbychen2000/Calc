# SFO Airport Traffic Control Tower (2016): research spec

Research note, 26 Sep 2026. Machine-readable spec: `tools/buildings/spec_tower.json`, which holds every value with its
unit, sources, tag and confidence. Tools: `tools/buildings/tower_*.py`. Downloads and photos are in
`refs/cache/buildings/tower/`, which is gitignored. Imagery overlays are in `out/buildings/tower/`, which is local only.
Nothing in `js/` or `data/` was changed. **This is a research draft for the owner's review.** No 2-D sheet or 3-D geometry
has been built from it yet, per the owner's method: drawings first.

**Legend.**
- **[pub]**: published by an original source (FAA, SFO, the architects, engineers or contractors, or trade press
  quoting them). The value is transcribed, not measured.
- **[obs]**: measured by me, with the method stated. Sources are NAIP, SFO Museum geometry, and licensed photos with a
  scale reference.
- **[inf]**: derived by me from [pub] and [obs] values under a stated assumption. It must be confirmed before it is
  treated as fact.
- **[unverified]**: could not be checked against an original source.

World frame: `ltp-nad83-2011`. x points east, z points south, in metres from the ARP. Heights are in metres above local
grade.

---------------------------------------------------------------------------------------------------------------------

## 0. Summary

1. **The FAA Digital Obstacle File's 245 ft is not the as-built height.**
   - DOF obstacle 06-323169 copies FAA airspace case **2008-AWP-286-NRA** [pub]. I retrieved it from the FAA OE/AAA
     system: the case data and the 20 Aug 2008 Final Determination letter.
   - The case describes "a proposed Airport Traffic Control Tower (ATCT) location for SFO … site 13 in the site survey
     report … We will not build above 245'".
   - 245 ft AGL / 258 ft AMSL (site elevation 13 ft) is therefore the **approved envelope**, filed four years before
     the design.
   - The DOF accuracy code is **4D**: ±250 ft horizontal, ±50 ft vertical.
   - Use 245 ft only as an upper bound.
2. **The published height is 221 ft (67.36 m)** [pub]. Sources: the FAA dedication release (Oct 2016), KQED, HNTB,
   ENR, Airport Improvement and Metal Construction News.
   - Other published figures: 220 ft (Fentress, and the engineers in STRUCTURE 2017), 228 ft (early design,
     Archinect) and 231 ft (AviationPros, Dec 2015).
   - **What 221 ft measures is not stated** [unverified]. My photo stations are consistent with *grade to the top of the
     cab-roof cap*, with antenna tips about 3.3 m higher, at about 232 ft. That may explain the "231-foot" figure.
3. **Vertical stations** [inf], all anchored on 221 ft at the roof rim:

   | Station | Height |
   |---|---|
   | Base-building roof | 14.2 m (measured from NAIP) |
   | Glass ribbon | 14.2 → about 59 m (147 ft, [pub]) |
   | Flared top, widest point | 59.4 m |
   | Cab floor / sill | about 61.0 m |
   | Cab glass | 61.8 → 64.7 m |
   | Roof rim | 67.36 m |
   | Mast tips | about 70.7 m |

   These are mutually consistent:
   - 147 ft of glass from the base-building roof ends at the flare.
   - A "200-foot high concrete core" (snippet only, [unverified]) ends at the cab floor.
4. **Diameters** [obs]. The scale comes from the published 11-ft cab glass panel and is cross-checked on top-view
   imagery.

   | Element | Diameter |
   |---|---|
   | Cab-roof cap | 14.3 ± 1.0 m |
   | Cab glass head | 12.3 m |
   | Cab glass sill | 10.0 m (glass leans out 20 ± 4°) |
   | Flared top | 22.6 ± 1.5 m |
   | Waist, at about 26 m | 9.8 m |
   | At the base-building roof | 10.3 m |

   A full radius-versus-height profile is in the spec.
5. **Position.**
   - Four independent NAIP flights (2016, 2018, 2022, 2024) put the cab roof at **z = 323.5 ± 2** [obs]. The four
     disc centres agree in z to ±1.2 m, while x swings by 54 m with each flight's east-west lean.
   - x is only bounded: **−739 ± 5** [inf].
   - The shaft axis is inferred at about (−740.5, 324.5).
   - The current 3-D model puts the shaft at the SFO Museum footprint centroid (−740.9, 331.7), which is **about 7 m
     too far south** [inf].
6. **Base building** [pub, obs]:
   - 3 storeys [pub], about 44,000 sq ft (published figures range from 42,000 to 55,000) [pub].
   - The SFO Museum footprint is a 45.0 × 27.2 m rectangle on the runway 1/19 grid [obs].
   - Roof at about 14.2 m, and a 2,000-sq-ft roof garden on the SW side at about 12.5 m [inf].
   - It includes the T1–T2 connectors, one with a 35-ft glass ceiling [pub].
7. **Materials** [pub]:
   - about 1,500 curved, trapezoidal ACM panels (4-mm Alucobond Plus in "SFO Silver"), with spiralling joints;
   - a 147-ft LED-backlit glass ribbon on the west (landside) face;
   - a frameless, laminated, outward-leaning cab glass band;
   - red obstruction lights, required by the FAA in 2008 and coded R in the DOF.
8. **Main open items:**
   - a lean-free absolute position;
   - what the 221 ft measures;
   - the cab glazing arc and pane count: sources give 220°, 235° or 270°, and "24 × 6 ft panes" does not fit;
   - the landside fin plan;
   - the obstruction-light fixtures.

   See §10.

---------------------------------------------------------------------------------------------------------------------

## 1. Sources found and what each one contributes

| Source (cache in `refs/cache/buildings/tower/src/`) | Kind | Contributes |
|---|---|---|
| **FAA OE/AAA 2008-AWP-286-NRA**: case JSON and the Final Determination PDF of 20 Aug 2008 (`oe_case_*.json`, `oe_letter_*.pdf`) | primary | NAD83 37-36-56.81N 122-23-01.78W; 245 ft AGL, 258 AMSL, site elevation 13; "will not build above 245'"; "Requires red obstruction lights"; line-of-sight and approach-minimum notes |
| **FAA DOF** (DOF.CSV dated 2026-09-18, `refs/cache/lighting/`) | primary | 06-323169, CTRL TWR, 245/258 ft, accuracy 4D, lighting R, marking N, study 2008AWP00286NR, JDATE 2025084 |
| **FAA release** of 11 Oct 2016, verbatim on AviationPros (`faa_pr_aviationpros.txt`) | primary text | 221 ft; 650-sq-ft controller work area; 235° unobstructed views; 147-ft glass ribbon; 3-storey, 44,000-sq-ft base building; costs; in use from 15 Oct 2016 |
| KQED and Patch (Oct 2016) | press | repeat the FAA and SFO figures (221 ft, 650 sq ft, 235°, 147 ft, 44,000 sq ft) |
| **STRUCTURE**, Jan 2017, written by the structural engineers (`structuremag.txt`) | primary | "220-foot"; brushed-aluminium cladding over a vertically post-tensioned cast-in-place core; steel flare and cab cantilevered off the core; three-storey 50,000-sq-ft base; non-secure corridor with a 35-ft glass ceiling; column-free for 220°; 7-ft mat on piles to 125 ft; slip-formed |
| **Walter P Moore** project and award pages | primary | 55,000-sf integrated base facility; circular offset cab; "first observation cab with a 270-degree unobstructed view"; tuned mass dampers |
| **ENR** Best Project, Sep 2016 | trade press (award data) | 221 ft; 26 PT cables; 650-sq-ft cab; **24 glass panels, 6 ft × 11 ft**; 1,100 cu yd; 42,000-sq-ft base; 213 piles, 140 ft |
| **Metal Construction News**, "Torch Tower", Jan 2017 (`mcn_torch.txt`) | trade press quoting HNTB, Fentress and suppliers | 221 ft; 5,652 sq ft; 147-ft glass band **on the west façade**; about 1,500 panels; 10,000 sq ft of 4-mm Alucobond Plus in "SFO Silver" on the KPS System A rainscreen; spiralling joints; Wausau curtainwall and Guardian SNX 62/27 IGUs (over 4,000 sq ft); 270° view; skylights, open core |
| **Airport Improvement**, Jan 2017, and **AviationPros**, Dec 2015 | trade press quoting SFO, HNTB and the FAA | HNTB design (45 %), Fentress architect of record; "nearly 150 ft" of glass; LED array; 650 sq ft and 235°; 44,000 sq ft; panels trapezoidal, curved, with rotated joints; lightning discharge in the seams; tuned mass dampers; "231-foot" (2015) |
| Fentress, HNTB and Hensel Phelps pages | primary (designers, builder) | "220-foot" (Fentress) and "221-foot" (HNTB); laminated seamless cab glass; courtyard and green roof; design-build; 60,000 SF total (Hensel Phelps) |
| Mead & Hunt | consultant | "2,000-square-foot roof garden on the third level" |
| Archinect (an HNTB designer's portfolio) | early design | "228 ft tall"; 270°; 44,000 sq ft; parametric façade panels |
| Architect Magazine project page | **[unverified]**: HTTP 403 to curl, WebFetch and the Wayback Machine | search snippets only: core 30 in at the base and 18 in at the top; 26 bundles × 19 cables × 7 strands; "200-foot high concrete core"; 13 controller stations; cab roof cantilevered from a 2'-2" × 3'-4" centre column of 1½" plate (14 tons) with three 2'-0" × 1'-4" landside tension columns; 215 piles averaging 140 ft |
| **SFO Museum** architecture data, record 1477855995 | open data (CDLA-Permissive) | base-building footprint ("atc", `src:geom flysfo`), 1,221 m²; inception 2016-10-15; address 250 Upper Domestic Loop |
| OpenStreetMap way 554547693 | community data (ODbL), **cross-check only** | cab polygon with r ≈ 7.9 m, centre (−739.0, 322.6); height 67.36 m; min_height 60 m |
| USDA NAIP 2016, 2018, 2020, 2022 and 2024 | public domain | top-view measurements (§4) |
| Wikimedia Commons, category *San Francisco Airport Control Tower* | photos, CC BY / BY-SA / CC0, **reference only** | profile ratios (§5). Authors, licences and camera positions are in the spec under `photos`. Pixels are in `refs/cache/buildings/tower/photos/` with `manifest.json` |
| Owner's Google screenshot 03dcd4ae | licensed, **reference only** | top-view cross-check of the cab disc (§4.3). Crops are in `refs/cache/buildings/tower/google/` and are never shipped |

**Searched but not found:**
- a flysfo.com fact sheet or design-and-construction page for the 2016 tower. The site search returned nothing, and
  the FAA newsroom URL gave 404.
- San Francisco Arts Commission Civic Design Review submittals for the new ATCT (2011–2012). Only the 2017–2018
  reviews of the *old* T2 tower's demolition are online.
- SF Planning CEQA documents for the ATCT.
- An AIA page with drawings.

The architects' pages give no elevations or plans with dimensions.

---------------------------------------------------------------------------------------------------------------------

## 2. Height: 221 ft vs the DOF's 245 ft

**The OE/AAA case** [pub], retrieved in this session:
- Method: `POST /oeaaa/oe3a/external/portal-api/caseFiling/dynamicCaseDataByAsn.do` with
  `{asnYear:2008, asnRegion:'AWP', asnSequence:'286', asnCaseType:'NRA'}`. The letter came from `letterDataByLetterId.do`,
  letterId 103217287.
- Case fields:
  - `heightAglFoot` 245, `elevationFoot` 13, `structureHeightAmslFoot` 258;
  - point 37.6157806, −122.3838278;
  - created 2008-05-06, determined 2008-08-20 as "Determined - No Hazard";
  - durationCode PERM; work 2012-01 to 2014-01.
- The letter's table gives NAD83 37-36-56.81N 122-23-01.78W, 245 AGL, 258 AMSL. It adds:
  - "…with sites 13 and 13A, there is a line of site issue that exists with the existing tower…";
  - "The proposed height of this new Air Traffic Control Tower, at this site, will cause the RNAV GPS RWY 19L and the
    RNAV GPS RWY 19R, LNAV MDA approach minimums to be increased by 40 feet";
  - "Tower pentrates a part 77 surface. Requires red obstruction lights."
- The determination expired on 20 Feb 2010 unless extended.

**The DOF** repeats exactly these values and the study number, with accuracy 4D. So the DOF records the *proposal*,
not a survey of the building. Its JDATE of 2025-084 is a later record update. The record is still 4D, so there has been
no survey.

**As-built published heights** [pub]:

| Height | Sources |
|---|---|
| 221 ft | FAA 2016, HNTB, ENR, AIC, MCN, KQED, Patch |
| 220 ft | Fentress; Sabelli et al. in STRUCTURE 2017 |
| 228 ft | pre-construction design text (Archinect) |
| 231 ft | AviationPros, Dec 2015 |

The core is "200-foot high" per the Architect Magazine snippet [unverified]. Hensel Phelps calls it a "13-story tower".

**Adopted.**
- 221 ft = 67.36 m at the **top of the cab-roof cap** [inf].
- Antenna tips at about 70.7 m [inf], which is about 232 ft.
- The DOF 245 ft / 74.7 m is an upper bound only.
- *Needs confirmation:* SFO Design & Construction or the FAA could state the reference points of "221 ft" and give the
  cab floor elevation.

---------------------------------------------------------------------------------------------------------------------

## 3. Position

| Candidate (world x, z) | What it is | Tag / quality |
|---|---|---|
| (−742.6, 335.7) | OE/AAA and DOF point, taken as NAD83 per the letter. Read as WGS 84, as the DOF labels it, it is (−741.0, 335.9) | [pub]; ±76 m (code 4); a 2008 *proposal* site |
| (−740.9, 331.7) | centroid of the SFO Museum "atc" footprint, which is the **base building**, not the tower | [obs]; used by the current `buildTower` |
| (−739.0, 322.6) | OSM cab polygon centre | community data; cross-check only |
| (−737.2, 314.3) | circle fit on the Google screenshot 03dcd4ae top view | reference only. Its registration is flagged low-confidence (imagery.md §8), and Google's imagery may have its own lean |
| NAIP cab-roof disc, per epoch: 2016 (−752.75, 323.35), 2018 (−749.70, 323.20), 2022 (−698.75, 325.30), 2024 (−700.85, 322.40) | tower top seen from above, displaced by that flight's lean | [obs]; §4 |

**Adopted cab-roof centre: (−739 ± 5, 323.5 ± 2)** [inf].
- **z.** NAIP is flown on north–south lines ("flight lines have been designed with a north/south orientation", NAIP
  2022 metadata). The lean is therefore across-track, that is east–west. The four epochs' disc centres agree in z to
  ±1.2 m while x swings by 54 m. A common north–south displacement in four independent flights is unlikely, so z is
  taken as measured.
- **x** needs an absolute zero-height reference, which NAIP lacks.
  - The SFO Museum SE (airside) wall line combined with the measured roof-to-cab lean ratio gives x in
    **−747…−734**. The spread comes from where the wall base really is (±1.5 m in the outline, ×4.8).
  - OSM (−739.0), Google (−737.2) and the OE/AAA point (−742.6) all lie inside that range.
- **Shaft axis:** the cab is offset from the core "closer to the airfield" by an unpublished amount. Photos suggest
  1–3 m towards the NE. That gives **(−740.5 ± 5.5, 324.5 ± 3)** [inf].
- **To close this**, one of the following is needed:
  - an SFO or FAA site plan;
  - the San Mateo County 2022 15 cm orthophoto, which needs a licence request (docs/research/imagery.md §7);
  - a photogrammetric solve from two ground photos with surveyed camera stations.

---------------------------------------------------------------------------------------------------------------------

## 4. NAIP measurements (top view): `tower_naip_epochs.py`, `tower_roof_disc.py`, `tower_lean_ratio.py`

**Data.** Each epoch was resampled onto the world grid at 0.1 m/px, for x −800…−640 and z 250…410.
- 2016-06-25, 2018-09-11, 2020-05-24 and 2022-05-18 come from DOQQ `m_3712229_ne` on Planetary Computer, read as
  windowed COG reads.
- 2024-05-20 comes from the local USDA mosaic.
- Output: `out/buildings/tower/naip_<year>_tower*.png|jpg`, and the evidence montage `evidence_naip_epochs.jpg`.
- 2012 predates construction. 2014 (tower under construction) was not used.
- **2020 is unusable for the top.** The tower appears as a thin sliver with no roof disc, probably a mosaic seamline
  through the tower. It does show a long ENE ground shadow.

### 4.1 Cab-roof disc

The fit is a radial-gradient circle fit around a hand seed, using the best 60 % of the rim.

| Epoch | Centre (x, z) | Radius of the strongest rim |
|---|---|---|
| 2016 | (−752.75, 323.35) | 6.10 m |
| 2018 | (−749.70, 323.20) | 6.00 m |
| 2022 | (−698.75, 325.30) | 7.60 m |
| 2024 | (−700.85, 322.40) | 6.50 m |

- The lean flips between the 2016/2018 flights (tower tops displaced **west**) and the 2022/2024 flights (displaced
  **east**, about 40–54 m). That is why the 2024-only analysis in imagery.md §6 saw "38–40 m east".
- The radius profiles show two or three concentric rims: about 4.5–5 m, 6–7.6 m, and about 9–11.5 m. At 0.6 m GSD on
  a white-on-white roof these cannot be assigned to physical edges with certainty.
- The 03dcd4ae screenshot at 0.165 m/px, reference only, shows rims at r 4.9, 7.1–7.7 and about 11.5 m.
- I read these as the roof inner curb, the **roof cap edge (r ≈ 7.1–7.7)** and the **flare rim (r ≈ 11.5)**. This
  agrees with the photo diameters in §5: 14.3 m and 22.6 m.

### 4.2 Relative heights from the lean change

This uses the principle in `tower_lean_ratio.py`. Between two epochs, a feature at height h moves by (k_b − k_a)·h.
The ratio of a feature's shift to the cab-roof shift is therefore h / H_cab, without knowing either k. The shifts were
measured by NCC template matching on gradient images.

| Feature | 2016→2024 | 2018→2024 | 2016→2022 | 2018→2022 | Adopted h (H = 67.36 m) |
|---|---|---|---|---|---|
| cab-roof disc shift (m) | 51.9 | 48.9 | 54.0 | 51.0 | (anchor) |
| base-building roof, hatch area (ratio; NCC 0.70–0.85) | 0.213 | 0.209 | 0.206 | 0.201 | **14.2 ± 1.5 m** [inf] |
| roof-garden planter, SW edge (NCC 0.55–0.67) | 0.180 | 0.181 | 0.187 | 0.83 (mismatch) | **12.5 m** [inf] |
| Terminal 1 roof south of the base building | 0.263 | (mismatch) | 0.239 | 0.243 | 16.1–17.7 m [inf] |

**Ground control.** Painted red equipment boxes on the apron move ≤ 1.2 m between epochs:

| Epoch | Box 1 (x, z) | Box 2 (x, z) |
|---|---|---|
| 2016 | (−667.03, 352.57) | (−647.96, 354.05) |
| 2018 | (−666.66, 352.21) | — |
| 2022 | (−666.82, 352.46) | (−648.07, 353.57) |
| 2024 | (−667.61, 351.39) | (−648.06, 353.12) |

Registration error therefore adds under ±0.02 to the ratios. The "roadway" patch I first used as ground control
actually moves 2–5 m: the departures deck and the AirTrain guideway are elevated.

**Base-building airside wall.** The SFO Museum SE edge compared with the imaged roof edge, along the outward normal:

| Epoch | Offset |
|---|---|
| 2016 | −0.5 m |
| 2018 | +1.5 m |
| 2020 | +1.3 m |
| 2022 | +10.5 m |
| 2024 | +9.0 m |

The cab shift divided by the edge shift is 5.5, matching the predicted 1 / (0.21 · 0.886) = 5.4. The outline and the
lean model are therefore consistent.

### 4.3 What the top views show about the shape [obs]

Visible best in 2016 and 2018, where the lean is small:
- a round flared top, with a pointed prow (the landside fin) towards the NW;
- the cab-roof disc set towards the east part of the flare;
- the base-building roof with a rectangular roof outline;
- a hatch or skylight;
- the planted strip along the SW edge;
- a teal/green glazed strip along the NW (roadway) edge, probably the non-secure corridor's glass roof [inf].

---------------------------------------------------------------------------------------------------------------------

## 5. Photo measurements: `tower_photo_profile.py`

**Photos** (reference only; licences are in the spec):
- **Basil D Soufi, "SFO – New Control Tower & A380"**, CC BY-SA 4.0, 2015-05-08, taken from 1.75 km at bearing 142°.
  - It is near-orthographic: vertical angles are under 2.5°.
  - The landside fin faces away from the camera, so the silhouette widths belong to the round airside body.
- **Famartin, 2025-08-12 11:57:15**, CC BY-SA 4.0, taken from 263 m at bearing 126°.
- Landside views, used for the ribbon and fin: Famartin 09:10:05 and 09:12:13, Varnum 2018 (0463 and 0465),
  Pi.1415926535's T2 AirTrain photo (2018), Sarah Stierch (2025, CC0).

**Scale.** Three independent measurements of the cab-roof cap agree on **d_cab_roof = 14.3 ± 1.0 m** [obs]:
- **Famartin photo.** The published panel height is 11 ft (ENR). The glass is measured to lean out 20.4°. So the
  vertical glass extent of 105 px equals 11 ft × cos 20.4° = 3.14 m, giving 0.0299 m/px. The cap is then
  480 px = **14.37 m**.
- **Google top view:** r 7.1–7.7 m.
- **OSM:** r 7.9 m.

The A380 photo is then scaled with the cap = 405 px (0.0353 m/px) and anchored at the roof rim = 221 ft.

**Vertical stations** [inf], measured on the A380 photo and cross-checked on the Famartin photo:

| Feature | Height |
|---|---|
| Mast tips | 70.7 m (Famartin: +2.96 m above the rim) |
| Roof rim | 67.36 m |
| Cab glass head | 64.7 m |
| Cab glass sill | 61.8 m |
| Sill band bottom / cab floor | ~61.0 m |
| Flare, widest | 59.4 m |
| Upper slot band | 49.2–56.8 m |
| Light seams | 44.3 and 29.5 m |
| Waist | 24.5–28.0 m |
| Base-building roof | 14.2 m (from §4.2) |

The seam spacing ratio agrees between the two photos: 0.609 against 0.614.

**Radius profile** [obs] of the round body. The A380 width ratios are in the spec as `shaft_profile_ratio_A380`, and the
radius per height is in `model_proposal_provisional.profile_r_of_h_m`.

| h (m) | 14.2 | 21.6 | 25.9 | 30.1 | 32.9 | 36.5 | 40.0 | 43.5 | 47.1 | 50.6 | 54.1 | 57.7 | 59.4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r (m) | 5.1 | 5.0 | 4.82 | 4.91 | 5.10 | 5.46 | 5.98 | 6.60 | 7.45 | 8.44 | 9.55 | 10.82 | 11.48 |

**Cab** [obs]:

| Element | Diameter |
|---|---|
| Cap rim | 14.3 m |
| Fascia, 2.7 m tall inverted cone, down to the glass head | 12.3 m |
| Glass sill (glass slopes out 20 ± 4°) | 10.0 m |

**Glass ribbon** [obs, low confidence]:
- a trapezoid about 3.2 m wide at the bottom and about 6.8 m at the top, taken from the T2 AirTrain photo, which is
  near-frontal;
- about 2 to 3 mullion columns;
- a row pitch of about 1.8 m.

**Cross-checks and inconsistencies:**
- 147 ft of glass, starting on the 14.2 m roof, ends at 59 m, right at the flare. **Consistent.**
- A 650-sq-ft "controller work area" against about 79 m² (850 sq ft) inside the glass sill. **Plausible** once the
  core and stair are deducted.
- **Inconsistent:** ENR's "24 6-ft by 11-ft panels" give 43.9 m of glass length. The glass-head circumference is about
  38.6 m. They fit only if the glass runs all the way round (about 360°) with panes of about 5.3 ft. A 270° arc of 6-ft
  panes would need an 18.7 m cab, which the photos and imagery rule out.
- **Inconsistent:** the published ACM area is 10,000 sq ft. The photo-derived clad envelope is about 20,000 sq ft. The
  figure may be partial, or the scale may be off. The scale is supported three ways, so the figure is more likely
  partial [inf].

---------------------------------------------------------------------------------------------------------------------

## 6. Cab

**Published** [pub]:
- 650-sq-ft controller work area (FAA).
- Views and glazing: "unobstructed 235-degree views" (FAA); "270-degree column-free" or "unobstructed" (WPM, ENR,
  MCN); "column-free for 220 degrees of its perimeter" (the engineers, STRUCTURE).
- Offset from the core towards the airfield. Vertical circulation moved out of the cab. The flare holds FAA electronics.
- Clear, laminated, seamless glass (Fentress).
- Two exit stairs (AIC).
- Tuned mass dampers "near the cab" (STRUCTURE).
- Snippet only, [unverified]:
  - 13 controller positions;
  - the roof cantilevered from a 2'-2" × 3'-4" plate column, with three landside tension columns, so the glass has no
    intermediate support.

**Observed:**
- a continuous dark glass band;
- vertical joints only;
- an outward lean of about 20°;
- a light sill band below the glass;
- an inverted-cone cap with a thin top rim;
- a flat roof carrying whip antennas around the edge and camera or sensor poles. There were about 8 masts in 2015 and
  about 12 in 2025.

**Open:**
- the glazed arc versus the solid sector;
- the pane count;
- where the tension columns sit;
- the exact offset of the cab from the core.

---------------------------------------------------------------------------------------------------------------------

## 7. Shaft, cladding and the glass ribbon

**Form** [pub, obs]:
- A "torch" of flared, hyperboloid-like section. The waist is at about 26 m. It flares to about 22.6 m at about 59 m.
- It is opened on the **west (landside) façade** to show the core behind a 147-ft glass ribbon (MCN, FAA). The ribbon
  faces the upper-level roadway and AirTrain.
- The ribbon is flanked by two curved blades. One ends in a sharp prow above the flare.
- Photos give a facing bearing of about 300–320° [inf].
- The ribbon is LED-backlit and programmable, and is lit in event colours at night.

**Cladding** [pub]:
- about 1,500 curved, trapezoidal ACM panels;
- 4-mm Alucobond Plus in custom "SFO Silver";
- the KPS System A pressure-equalized rainscreen;
- joints rotated so that they spiral up the tower;
- a lightning-discharge system woven into the seams.

**Observed on the cladding:**
- 6 visible inclined dark slots, probably louvres, in the band from 49 to 57 m on the airside;
- one long inclined slot from 25 to 42 m on the SE face;
- two light circumferential joints at 29.5 and 44.3 m;
- panel rows about 1.5 m tall.

**Structure** [pub], not visible:
- a slip-formed concrete cylinder with unbonded vertical post-tensioning;
- the flare and cab in steel;
- a 7-ft mat on auger pressure-grouted piles;
- four buckling-restrained braces from the base-building roof acting as a backstay.

---------------------------------------------------------------------------------------------------------------------

## 8. Base building (Integrated Facilities)

- **Storeys and area** [pub]: 3 storeys. Published floor areas are 42,000 (ENR), **44,000** (FAA, SFO and most
  others), 50,000 (STRUCTURE) and 55,000 sf (WPM). The whole project is 60,000 sf (Hensel Phelps).
- **Footprint** [obs]: the SFO Museum polygon, a 45.0 × 27.2 m rectangle with its long axis at 27.7°, parallel to the
  1/19 grid. It covers 1,221 m², and × 3 that is about 39,400 sf.
- **Roof** [inf]: about 14.2 m, with the roof garden at about 12.5 m on the SW side ("2,000-square-foot roof garden on
  the third level", Mead & Hunt).
- **Façades** [pub, obs]:
  - concrete walls, blast-resistant towards the roadway;
  - airside, a horizontal band of dark glazing between light metal panels;
  - landside, grey metal-panel volumes with a curtainwall section.
- **Connectors** [pub]:
  - a pre-security T1–T2 corridor with a 35-ft-tall glass ceiling that looks up at the tower;
  - a post-security connector bridge.
- **Open:** the connector roofs and parapet heights. Is the footprint the roof outline or the wall line?

---------------------------------------------------------------------------------------------------------------------

## 9. Deviations of the current 3-D model (`js/live/terminals.js` `buildTower`)

For the later 3-D workflow. **Not edited here.**

| Item | Current model | This research | Tag |
|---|---|---|---|
| Shaft position | footprint centroid (−740.9, 331.7) | (−740.5 ± 5.5, 324.5 ± 3) | inf |
| Base-building roof | 14 m | 14.2 ± 1.5 m | inf (NAIP) |
| Waist | r 4.2 m at 36–44 m | r 4.8–4.9 m at 24–30 m | obs |
| Flare | r 7.2 m at 57.2 m | r 11.5 m at 59.4 m | obs |
| Cab glass | r 7.4 → about 8.4 m, 58.4 → 60.9 m, 9-ft panes leaning 25°, 24 of 32 segments glazed | r 5.0 → 6.15 m, 61.8 → 64.7 m, 11-ft panes leaning about 20°; glazed arc open | obs / pub |
| Roof | cap to about 62.4 m, plus a 7 m mast | cap rim r 7.15 m at 67.36 m; masts to about 70.7 m | inf |
| Ribbon | on −x (west) from 14 m to 58.8 m, 2.2 m wide | west to NW face, 3.2 → 6.8 m wide, recessed between blades, 14.2 → 59 m | obs (low) |
| Cab offset | +1.6 m east | 1–3 m towards the airfield (NE), unpublished | inf |

---------------------------------------------------------------------------------------------------------------------

## 10. Open questions and what would close them

1. **Absolute position** (x ± 5 m; the shaft axis relative to the base footprint). Any one of these would close it:
   - an SFO or FAA site plan;
   - SFO GIS;
   - the San Mateo County 15 cm ortho, after a licence request;
   - two to three ground photos with surveyed or RTK camera positions.
2. **Reference points of "221 ft", and the cab floor elevation.** Ask SFO Design & Construction or the FAA Western
   Service Area. The Civic Design Review Phase 1–3 submittals (SF Arts Commission, 2011–2012) would likely have
   elevations but were not found online.
3. **Cab glazing.** The arc (220°, 235°, 270° or 360°), the pane count and width, and the solid sector towards the
   core. ENR's "24 × 6 ft" is inconsistent with 270°.
4. **Landside plan.** The fin and blade geometry, the ribbon's facing bearing, and the prow.
5. **Obstruction lights.** The FAA required red lights in 2008 and the DOF codes them R. No fixture is identifiable in
   the photos found. The type (L-864 and L-810(F), per AC 70/7460-1N for over 150 ft) is inferred in
   `tools/env/lighting_spec.json`.
6. **Architect Magazine details** (core walls, 13 positions, roof column). The page is blocked here. Another copy, or
   the owner's browser, could confirm them.
7. **Cladding area:** 10,000 sq ft published against about 20,000 sq ft derived.
8. **Base building.** The roof outline versus the wall line, the parapets, the rooftop units, and the connector roofs.

**Next step (owner's method):** draw the 2-D sheet. Plan at the base, at 26 m, at 59 m and at the roof, plus an
elevation from the SE and from the NW. Draw it from `spec_tower.json`, overlay it on NAIP 2016/2024 with the lean
applied, and put it up for owner review before any 3-D.

## 11. Reproduce

```bash
python3 tools/buildings/tower_naip_epochs.py      # NAIP 2016-2024 crops (needs network for Planetary Computer)
python3 tools/buildings/tower_roof_disc.py        # cab-roof disc fits      -> out/buildings/tower/roof_disc_fits.json
python3 tools/buildings/tower_lean_ratio.py       # relative heights        -> out/buildings/tower/lean_ratio.json
python3 tools/buildings/tower_photo_profile.py    # photo ratios (needs refs/cache/buildings/tower/photos/)
```

Credit NAIP as: "USDA NAIP (USDA FPAC Business Center, Geospatial Enterprise Operations), public domain". The photos
are reference only; their authors and licences are listed in the spec.
