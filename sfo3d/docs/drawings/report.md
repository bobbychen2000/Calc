# SFO Live 3D — 2-D drawing set: deviations and physical conflicts

Generated 2026-09-24 09:52Z by `tools/drawing/run_all.sh` (report: `tools/drawing/report.py`).
Scene extracted from the running app (`jobs/extract2d.mjs`, live.html?mode=snapshot, git `dbdaf2b`, 2026-09-24T09:06:15Z, quality tier `high`).
Everything below is drawn/measured from the objects the 3-D app actually places (window.SFO world / gateSys / traffic / physics, and the app's own builder functions), not re-derived from the data files.

## Headline

- **Imagery `google`** (Google Maps screenshots (owner, reference only); reference only, not redistributable): 914 features sampled, **329 measured** (+116 jet-bridge rotunda candidates), **270 with median offset > 1.0 m**; 324 with p90 > 1.0 m.
- **Imagery `naip`** (NAIP (2 image(s)); public): 914 features sampled, **434 measured** (+115 jet-bridge rotunda candidates), **323 with median offset > 1.0 m**; 403 with p90 > 1.0 m.
- **Physical audit**: 377 distinct findings (one per pair of objects, merged across scenarios): **114 COLLISION**, **4 OFF-PAVEMENT**, **50 CLEARANCE**, **209 WARNING**.

| scenario | COLLISION | OFF-PAVEMENT | CLEARANCE | WARNING |
|---|---|---|---|---|
| DOCK-MAX (every stand with its largest type, bridges docked) | 46 | 0 | 16 | 5 |
| DOCK-REF (every stand with its reference type, bridges docked) | 46 | 0 | 11 | 5 |
| ENVELOPE (class envelopes (all accepted types) vs neighbours / parked bridges / buildings) | 47 | 0 | 20 | 5 |
| KINEMATICS (bridge tunnel geometry rest vs docked) | 0 | 0 | 0 | 168 |
| LIVE (snapshot as displayed) | 42 | 4 | 0 | 8 |
| OVERSIZE (747 / A380 on EL-F stands vs blocking rule) | 1 | 0 | 12 | 0 |
| REST (all stands empty, bridges parked) | 33 | 0 | 0 | 2 |
| STATIC (buildings vs buildings) | 0 | 0 | 0 | 25 |

## Key findings (worst first)

- **46 x envelope-rest-bridge** - parked (retracted) jet bridge inside the arrival envelope of its own stand: the cab parks min(15 m, reach - 2 m) from the rotunda towards the door, i.e. within ~2 m of the fuselage line on short-reach stands.
- **21 x bridge-vdgs** - VDGS / stand-sign box inside a bridge tunnel or stair (the VDGS is placed on the stand centreline at the attach-point depth, where tunnels also pass).
- **20 x bridge-aircraft** - docked bridge (tunnel / rotunda / stair / drive column) intersecting its own or a neighbouring aircraft (wing, engine or fuselage) in 3-D.
- **18 x bridge-bridge** - two bridges intersecting in 3-D (mostly the L1 and L2 bridges of one wide-body stand at rest).
- **5 x aircraft-building** - parked aircraft overlapping a terminal building in the LIVE snapshot - GroundPhysics never tested them (see the classification finding below); note also that its tests use 13 outline points of the TYPES planform, not the rendered model.
- **1 x aircraft-vdgs** - aircraft intersecting a VDGS unit.
- **1 x bridge-building** - bridge part inside a building / elevated walkway.
- **1 x envelope-envelope** - two neighbouring class envelopes overlap.
- **1 x oversize-not-blocked** - oversize aircraft (747/A380) reaches a neighbour the blocking rule leaves available.
- **GroundPhysics never checks 9 parked aircraft**: tracks with phase `parked` and a stale transponder that still carry their last reported ground speed (UAL875 0.8 m/s, UAL34 6.1 m/s, ASA528 3.5 m/s, UAL1116 4.2 m/s, UAL852 6.1 m/s, UAL2467 6.8 m/s, SKW3490 9.5 m/s, UAL2649 6.3 m/s, JBU578 6.3 m/s) fall into the *moving* branch of `ground.js resolve()` (`(D.gs || 0) < 0.8` fails), which only nudges aircraft apart and never tests buildings or pavement. 7 of them account for the LIVE building / VDGS / off-pavement conflicts below.
- **4 aircraft with a gear leg off the paved raster** the app uses (ground.js physics / ground shader): UAL2467 B39M (parked), SKW3490 E75L (parked), UAL2649 A319 (parked), JBU578 A321 (parked).
- **Bridge kinematics**: 109 bridges whose three tunnel sections change length between parked and docked (they scale instead of telescoping - visible "morphing"); 59 docked tunnels steeper than 1:12.
- **25 overlapping building footprints** that are both extruded (coplanar roofs that z-fight, or walls that cut through each other), among them AirTrain stations listed twice under two names: West Field Road AirTrain Station (Outbound) / Westfield Road AirTrain Station (Outbound)g; Terminal 1 Air Train Station / Terminal One AirTrain Station; Terminal 2 Air Train Station / Terminal Two AirTrain Station; Terminal 3 Air Train Station / Terminal Three AirTrain Station; International Terminal (A) AirTrain Station / International Terminal G Air Train Station; International Terminal (G) AirTrain Station / International Terminal A Air Train Station; West Field Road AirTrain Station (Inbound) / Westfield Road AirTrain Station (Inbound).
- 1 aircraft on the ground drawn as a marker (no TYPES entry) - GroundPhysics treats it as no body at all.

## Visually verified on the overlay sheets

- **28R / 28L displaced-threshold bar is on the wrong side of the threshold line (3.05 m)** - verified on NAIP 2024 (0.5 m, independently georeferenced) and on the Google screenshot 1a26bbeb: the modelled threshold stripes coincide with the imaged ones to about half a metre at both ends, but the imaged 10 ft bar lies on the landing side of the threshold (x = 0 .. +3.05 m, then a ~3 m gap to the stripes starting at +6.1 m), while `js/shaders/ground.js` endMarkings() draws it at x = -3.05 .. 0 (approach side, where the imagery shows the arrowheads). Candidate fix: `band(xt, 0.0, 3.05, fw)` instead of `band(xt, -3.05, 0.0, fw)`; re-check the arrowhead tips against the bar afterwards (AC 150/5340-1M Fig. A-7). The automatic bar number in the tables over-states the shift because the ridge detector locks onto the stripe block.
- **Threshold bar missing at the non-displaced ends (10L, 10R, 19L, 19R)** - the NAIP along-axis profiles in `refs/cache/naip/naip_faa_check_2022.json` / `_2024.json` (produced by the imagery research task) show a 3.4-3.7 m bright band from x = -0.9..0 to +2.7..3.5 m at all four ends, presumably the 10 ft bar blurred by the imagery; `endMarkings()` draws a bar only when the threshold is displaced. The same profiles confirm the rest of the model at those ends: stripes start at 5.3-6.3 m (model 6.1 m) and end at 51.3-52.2 m (model 51.8 m); EMAS beds start 10.5-11.1 m beyond the end (model setback 10.67 m).
- The EMAS "pavement end" at 1L/1R/19L/19R is not a visible edge (the 35 ft setback is paved); these ends are measured by the EMAS bed outline instead.

## Data vs published source (no imagery)

Runway ends of the RWY table the 3-D draws (`js/world/airfield.js`, s/t) against the FAA/AirNav end coordinates (`js/geo.js` RWY_ENDS):

| end | along-axis diff (m) | lateral diff (m) | displacement model / FAA (m) |
|---|---|---|---|
| 10L | +0.25 | -0.07 | 0.0 / 0.0 |
| 28R | +0.03 | +0.07 | 91.4 / 91.4 |
| 10R | +0.18 | +0.09 | 0.0 / 0.0 |
| 28L | +0.03 | +0.00 | 91.4 / 91.4 |
| 1L | -0.16 | **-1.11** | 195.1 / 195.1 |
| 19R | -0.02 | **-1.31** | 0.0 / 0.0 |
| 1R | -0.17 | **-1.36** | 170.7 / 170.7 |
| 19L | +0.11 | **-1.32** | 0.0 / 0.0 |

The RWY table stores every runway axis-aligned in the s/t grid (a single c per runway). The FAA ends of 1L/19R (s = -20.49 / -22.91) and 1R/19L (s = 207.96 / 205.28) show those runways are not exactly perpendicular to 10/28 (about 0.06 deg), so the modelled 1/19 centrelines are 1.1-1.4 m off at both ends (bold, opposite sides) and close to 0 at mid-length - a rotation, not a shift. NAIP agrees: along their whole length the 1/19 edge stripes measure within ~0.8 m of the model, and the NAIP-derived runway centrelines lie within 0.2-0.4 m of the FAA lines (refs/cache/naip/naip_faa_check_*.json). Fix: give 1L/19R and 1R/19L their own direction instead of the t axis.

Rendered aircraft planform (real model scaled to TYPES length) against the TYPES published span - the audit uses the rendered geometry; GroundPhysics and standFits use TYPES:

| type | model | TYPES span (m) | rendered span (m) | diff |
|---|---|---|---|---|
| a20n | a320 | 35.8 | 33.3 | -2.5 |
| a21n | a321 | 35.8 | 34.0 | -1.8 |
| a319 | a319 | 35.8 | 33.9 | -1.9 |
| a320 | a320 | 35.8 | 33.3 | -2.5 |
| a321 | a321 | 35.8 | 34.0 | -1.8 |
| a332 | a333 | 64.8 | 60.6 | -4.1 |
| a333 | a333 | 64.8 | 60.5 | -4.2 |
| b744 | b744 | 68.4 | 65.2 | -3.2 |
| b752 | b752 | 38.0 | 39.2 | +1.2 |
| b753 | b752 | 38.0 | 39.1 | +1.1 |
| b762 | b763 | 50.9 | 46.1 | -4.8 |
| b763 | b763 | 50.9 | 46.1 | -4.8 |
| b764 | b763 | 50.9 | 46.2 | -4.7 |
| bcs3 | bcs3 | 35.1 | 35.7 | +0.6 |
| crj2 | crj2 | 24.9 | 21.2 | -3.6 |
| crj7 | crj7 | 24.9 | 23.2 | -1.6 |
| crj9 | crj9 | 24.9 | 23.9 | -0.9 |
| e170 | e170 | 28.6 | 25.7 | -2.9 |
| e75l | e75l | 28.6 | 26.3 | -2.3 |
| md11 | md11 | 50.9 | 51.9 | +1.0 |

Several TYPES spans are not the published value of the type they name, and standFits() / GroundPhysics use TYPES: e.g. a332/a333 64.8 m is the A350 wing (A330-200/-300: 60.3 m), crj2 24.9 m is the CRJ900 value (CRJ200: 21.2 m). Rendered models are scaled by length only, so their spans differ from TYPES by up to ~5 m. Verify against the manufacturers' airport-planning documents before changing js/aircraft/types.js.

## How far to trust the automatic picks (self-test)

`tools/drawing/selftest.py` resamples the Google imagery of 5 regions into synthetic georeferenced tiles whose content is displaced by a known vector ((0.8, -0.5), (2.0, -1.0) m) and re-measures every feature there. `stable` = same pick on an undisplaced resampled tile (within 0.5 m); `recovered` = the measured offset changed by the known n . shift (within 0.5 m). Low recovery means the class's numbers are dominated by picking a neighbouring edge (parapet, shadow, shoulder, paint): use its overlay sheets, not its numbers.

| class | samples in test regions | measured | stable | recovered @ 0.9 m | recovered @ 2.2 m |
|---|---|---|---|---|---|
| bridge-walkway | 19 | 19 | 1.00 | 0.53 | 0.16 |
| building | 2520 | 2398 | 0.87 | 0.76 | 0.60 |
| emas-bed | 140 | 140 | 0.98 | 0.90 | 0.80 |
| extra-pavement | 566 | 436 | 0.96 | 0.88 | 0.73 |
| hold-line | 187 | 0 | – | – | – |
| runway-displaced-threshold | 28 | 28 | 1.00 | 1.00 | 1.00 |
| runway-edge-stripe | 187 | 52 | 1.00 | 0.98 | 0.95 |
| runway-end | 39 | 37 | 0.78 | 0.59 | 0.51 |
| runway-threshold | 48 | 32 | 1.00 | 0.91 | 0.94 |
| stand-leadin | 293 | 0 | – | – | – |
| taxiway-centreline | 467 | 0 | – | – | – |
| taxiway-edge | 234 | 112 | 0.95 | 0.80 | 0.64 |

## Deviations from imagery - `google`

Source: Google Maps screenshots (owner, reference only) (Google imagery - reference only, never redistributed). Offsets are signed along the outward edge normal (+ = imaged edge outside / right of the model), in metres; `gsd` = ground resolution of the image the profile was read from; `alt` = the same samples read from the next-best image (registration check). Features flagged when the median |offset| > 1.0 m.

| class | features | measured | flagged (median > 1 m) | median of medians | median p90 | typical gsd | notes |
|---|---|---|---|---|---|---|---|
| apron-edge | 1 | 1 | 1 | 8.70 | 9.67 | 0.28 |  |
| bridge-rotunda | 117 | 116 | 0 | 5.09 | 5.09 | 0.27 | automatic disc search, low confidence - use the per-bridge crops |
| bridge-walkway | 28 | 28 | 16 | 2.33 | 3.65 | 0.27 |  |
| building | 130 | 117 | 101 | 2.90 | 8.07 | 0.28 | roof edge vs footprint: relief displacement (roofs lean away from nadir) + registration; see `shift`/`resid` columns |
| emas-bed | 4 | 4 | 4 | 2.35 | 4.92 | 1.38 |  |
| extra-pavement | 60 | 57 | 54 | 2.90 | 7.52 | 1.07 | derived from the same imagery (circular); checks the vectorisation |
| hold-line | 81 | 0 | 0 | – | – | – | needs <= 0.6 m/px; most holds are on 0.9-1.6 m/px shots |
| runway-displaced-threshold | 2 | 2 | 2 | 7.30 | 7.44 | 0.57 |  |
| runway-edge-stripe | 8 | 4 | 1 | 0.80 | 2.52 | 0.57 | 0.91 m stripe; 1L/19R, 1R/19L only on coarse shots |
| runway-end | 4 | 4 | 3 | 2.20 | 2.79 | 0.92 |  |
| runway-threshold | 8 | 2 | 2 | 1.80 | 2.00 | 0.57 | stripe start; needs <= 0.8 m/px |
| stand-leadin | 89 | 0 | 0 | – | – | – | lead-in paint not visible (worn / under the parked aircraft on obs stands) |
| taxiway-centreline | 254 | 0 | 0 | – | – | – | 6 in paint: needs <= 0.35 m/px; the airfield screenshots are 0.5-1.6 m/px and JPEG chroma hides thin yellow lines |
| taxiway-edge | 128 | 110 | 86 | 3.67 | 6.98 | 1.08 |  |

### runway-end (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 10L pavement end **>1 m** | 13/13 | 3.90 | 4.52 | 4.8 | +3.90 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 10R pavement end **>1 m** | 11/13 | 2.80 | 3.30 | 4.1 | +2.80 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 28L pavement end **>1 m** | 13/13 | 1.60 | 2.28 | 2.4 | -0.90 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28R pavement end | 13/13 | 0.70 | 2.00 | 3.8 | -0.60 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-threshold (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28L threshold stripes (start 6.1 m past threshold) **>1 m** | 16/16 | 2.10 | 2.20 | 2.4 | +2.10 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28R threshold stripes (start 6.1 m past threshold) **>1 m** | 16/16 | 1.50 | 1.80 | 1.8 | +1.50 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-displaced-threshold (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28R displaced threshold bar (91.4 m) **>1 m** | 14/14 | 7.50 | 7.60 | 7.7 | +7.50 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28L displaced threshold bar (91.4 m) **>1 m** | 14/14 | 7.10 | 7.27 | 7.3 | +7.10 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-edge-stripe (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 10R/28L edge stripe (south/east side) **>1 m** | 44/341 | 1.30 | 1.60 | 1.8 | +1.25 | 0.57 | 1a26bbeb, bc91df95 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| RWY 10L/28R edge stripe (north/west side) | 26/356 | 0.80 | 3.55 | 3.6 | -0.80 | 0.57 | 1a26bbeb | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| RWY 10L/28R edge stripe (south/east side) | 28/356 | 0.80 | 1.53 | 1.6 | +0.20 | 0.57 | 1a26bbeb, bc91df95 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| RWY 10R/28L edge stripe (north/west side) | 42/341 | 0.75 | 3.45 | 3.9 | -0.75 | 0.57 | 1a26bbeb, bc91df95 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |

### emas-bed (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| EMAS bed beyond RWY 19L **>1 m** | 62/118 | 6.10 | 7.60 | 8.0 | -3.25 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| EMAS bed beyond RWY 1L **>1 m** | 130/130 | 2.40 | 3.50 | 7.7 | +0.65 | 1.08 | 103723b0, 2f0be03d | +0.10 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| EMAS bed beyond RWY 1R **>1 m** | 116/116 | 2.30 | 3.30 | 3.8 | +0.05 | 1.15 | 103723b0, 2f0be03d | -1.60 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| EMAS bed beyond RWY 19R **>1 m** | 55/122 | 2.00 | 6.34 | 8.5 | -1.50 | 1.61 | c1064033 | +6.35 (3.18) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |

### building (117 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | fit shift | resid median | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Central Parking Garage near Harvey Milk Terminal 1 (part 2/5) **>1 m** | 85/85 | 8.70 | 9.66 | 9.9 | -3.60 | 0.42 | 4637f855 | -4.60 (0.55) | 4.41 | 7.54 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Central Parking Garage near Terminal 2 (part 3/5) **>1 m** | 85/85 | 8.20 | 9.36 | 9.9 | +7.90 | 0.42 | 4637f855 | +6.90 (0.55) | 9.17 | 2.75 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Terminal complex ramp level near Harvey Milk Terminal 1 (part 5/19) **>1 m** | 70/76 | 8.00 | 9.40 | 9.7 | -8.00 | 0.55 | 03dcd4ae, 0af09b78, 4637f855 | -5.00 (0.55) | 9.90 | 2.16 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Boarding Area F near Boarding Area F (part 1/6) **>1 m** | 86/86 | 7.35 | 8.35 | 9.4 | -4.60 | 0.27 | 39176bb8, e6f569c1 | -1.00 (0.50) | 4.26 | 3.98 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| Super Bay Hangar Building near Boarding Area E (part 2/3) **>1 m** | 97/97 | 7.30 | 8.70 | 9.1 | +7.10 | 1.61 | c1064033 | +1.70 (3.18) | 8.78 | 1.00 | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Boarding Area B near Boarding Area B (part 4/5) **>1 m** | 87/87 | 7.10 | 9.10 | 9.7 | -7.10 | 0.28 | 0af09b78, b1d51b0f | -7.00 (0.55) | – | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Terminal complex ramp level near Boarding Area B (part 11/19) **>1 m** | 75/75 | 6.90 | 6.90 | 9.4 | -6.90 | 0.28 | 0af09b78, b1d51b0f | -4.30 (0.55) | – | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Terminal complex ramp level near Boarding Area B (part 12/19) **>1 m** | 75/75 | 6.80 | 8.90 | 9.4 | -6.70 | 0.28 | 0af09b78, b1d51b0f | -6.80 (0.55) | – | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Terminal complex ramp level near Harvey Milk Terminal 1 (part 14/19) **>1 m** | 75/75 | 6.30 | 9.10 | 9.7 | -1.10 | 0.16 | 03dcd4ae, 4637f855 | -0.70 (0.42) | 3.85 | 3.85 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Boarding Area B near Boarding Area B (part 5/5) **>1 m** | 87/87 | 6.30 | 8.44 | 9.7 | -3.80 | 0.28 | 0af09b78, b1d51b0f | -0.40 (0.55) | 2.81 | 5.49 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| Terminal complex ramp level near Terminal 2 (part 3/19) **>1 m** | 74/76 | 6.00 | 8.80 | 9.8 | +2.90 | 0.24 | 4637f855, bf5c7afc, c235f3b8 | +1.15 (0.42) | 6.04 | 4.15 | [10-ba-E](10-ba-E.png), [20-itb-tower](20-itb-tower.png) |
| Grand Hyatt Hotel **>1 m** | 102/116 | 5.90 | 8.60 | 9.5 | -0.50 | 1.07 | 35809e3e | -1.50 (3.18) | 1.45 | 5.48 | [40-apron-3-south-middle](40-apron-3-south-middle.png), [00-overview](00-overview.png) |
| Grand Hyatt Hotel AirTrain Station **>1 m** | 70/73 | 5.75 | 9.11 | 9.6 | +1.40 | 1.07 | 35809e3e | – | 1.19 | 5.83 | [40-apron-3-south-middle](40-apron-3-south-middle.png), [00-overview](00-overview.png) |
| West Field Road AirTrain Station (Outbound) **>1 m** | 72/80 | 5.35 | 8.67 | 9.4 | -2.15 | 1.27 | c9ff55e8 | – | 3.10 | 4.97 | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| Super Bay Hangar Building near Boarding Area D (part 1/3) **>1 m** | 34/98 | 5.35 | 6.70 | 7.2 | +5.35 | 1.61 | c1064033 | +3.75 (3.18) | 6.71 | 0.75 | [30-rwy-19R](30-rwy-19R.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Boarding Area E near Boarding Area E (part 1/2) **>1 m** | 76/76 | 5.30 | 6.05 | 9.8 | -5.20 | 0.24 | 4637f855, c235f3b8 | +0.15 (0.42) | 2.71 | 3.17 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Terminal complex ramp level near Terminal 2 (part 17/19) **>1 m** | 70/75 | 5.30 | 8.57 | 9.7 | +5.20 | 0.24 | 03dcd4ae, 4637f855, bf5c7afc | +4.75 (0.42) | 4.34 | 2.50 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| Terminal complex ramp level near Boarding Area E (part 6/12) **>1 m** | 79/80 | 5.20 | 8.56 | 9.6 | -4.20 | 0.24 | 4637f855, c235f3b8 | +1.80 (0.42) | 2.82 | 3.10 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Terminal complex ramp level near Boarding Area E (part 7/12) **>1 m** | 80/80 | 5.20 | 5.70 | 8.5 | -2.30 | 0.24 | 4637f855, c235f3b8 | -0.95 (0.42) | 3.32 | 3.80 | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| Boarding Area B near Boarding Area B (part 3/5) **>1 m** | 87/87 | 5.10 | 7.30 | 8.6 | -5.10 | 0.28 | 0af09b78, b1d51b0f | -0.30 (0.55) | 6.73 | 2.06 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Garage A near International Terminal (part 1/3) **>1 m** | 78/97 | 5.10 | 8.73 | 9.7 | +3.85 | 0.55 | 0af09b78, 35809e3e, 8b334c52 | +5.00 (1.07) | 3.02 | 3.79 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Central Parking Garage near Harvey Milk Terminal 1 (part 1/5) **>1 m** | 75/85 | 5.00 | 8.76 | 9.5 | +3.40 | 0.42 | 4637f855, e6f569c1 | +0.90 (0.55) | 5.38 | 4.37 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Garage G near International Terminal (part 3/4) **>1 m** | 78/79 | 4.90 | 8.93 | 9.4 | +3.60 | 0.27 | 151ec51d, 35809e3e | +2.80 (1.07) | – | – | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| Central Parking Garage near Terminal 3 (part 5/5) **>1 m** | 78/84 | 4.80 | 9.16 | 9.6 | -3.30 | 0.50 | 103723b0, 4637f855, e6f569c1 | -3.90 (0.55) | 1.60 | 4.39 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Garage G near International Terminal (part 4/4) **>1 m** | 79/79 | 4.70 | 9.10 | 9.9 | +3.60 | 1.07 | 151ec51d, 35809e3e | +5.30 (3.18) | – | – | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Super Bay Hangar Building near Boarding Area D (part 3/3) **>1 m** | 70/97 | 4.70 | 8.41 | 8.8 | +2.10 | 1.27 | c1064033, c9ff55e8 | +3.90 (1.61) | 8.06 | 2.90 | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Garage A near International Terminal (part 3/3) **>1 m** | 75/96 | 4.70 | 8.90 | 9.7 | +1.70 | 0.55 | 0af09b78, 35809e3e, d82848c4 | -0.75 (1.07) | – | – | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Harvey Milk Terminal 1 near Harvey Milk Terminal 1 (part 2/4) **>1 m** | 78/86 | 4.65 | 9.30 | 9.8 | -3.40 | 0.55 | 0af09b78, e6f569c1 | +0.70 (1.07) | 5.61 | 3.41 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Terminal 2 near Terminal 2 (part 1/3) **>1 m** | 82/86 | 4.60 | 8.39 | 9.6 | +1.50 | 0.24 | 4637f855, bf5c7afc, c235f3b8 | -0.60 (0.42) | 2.74 | 4.47 | [10-ba-D](10-ba-D.png), [20-itb-tower](20-itb-tower.png) |
| Westfield Road AirTrain Station (Inbound) **>1 m** | 75/78 | 4.60 | 6.92 | 9.1 | -1.30 | 1.27 | c9ff55e8 | +1.75 (3.18) | – | – | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| Boarding Area C near Boarding Area C (part 1/2) **>1 m** | 81/81 | 4.60 | 8.80 | 9.8 | +0.20 | 0.16 | 03dcd4ae | +1.70 (0.42) | 2.21 | 4.16 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Harvey Milk Terminal 1 near Harvey Milk Terminal 1 (part 1/4) **>1 m** | 85/86 | 4.60 | 9.52 | 9.8 | +1.20 | 0.16 | 03dcd4ae, 0af09b78, 4637f855 | -5.05 (0.42) | 3.97 | 4.60 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Terminal One AirTrain Station **>1 m** | 26/30 | 4.55 | 8.95 | 9.5 | -1.40 | 0.42 | 4637f855 | -0.70 (0.55) | – | – | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Terminal complex ramp level near Boarding Area F (part 1/12) **>1 m** | 81/81 | 4.50 | 8.40 | 9.4 | -0.80 | 0.27 | 39176bb8, e6f569c1 | -0.00 (0.50) | 3.62 | 4.07 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| Westfield Road AirTrain Station (Outbound)g **>1 m** | 55/62 | 4.30 | 7.70 | 8.9 | -3.10 | 1.27 | c9ff55e8 | – | 1.82 | 3.77 | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| Terminal 2 near Terminal 2 (part 2/3) **>1 m** | 86/86 | 4.20 | 7.60 | 9.4 | +3.05 | 0.20 | 03dcd4ae, 4637f855, bf5c7afc | +3.50 (0.42) | 6.07 | 2.90 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| Central Parking Garage near Terminal 3 (part 4/5) **>1 m** | 85/85 | 4.20 | 8.40 | 9.6 | -0.50 | 0.50 | 4637f855, e6f569c1 | +1.90 (0.55) | 5.10 | 4.58 | [10-ba-E](10-ba-E.png), [20-itb-tower](20-itb-tower.png) |
| Terminal 3 near Terminal 3 (part 3/4) **>1 m** | 74/77 | 4.15 | 9.40 | 9.7 | -0.95 | 0.50 | e6f569c1 | -0.80 (0.55) | 0.21 | 4.36 | [10-ba-F](10-ba-F.png), [20-itb-tower](20-itb-tower.png) |
| International Terminal (G) AirTrain Station **>1 m** | 16/16 | 4.05 | 8.60 | 9.6 | +2.20 | 0.25 | 0af09b78, d82848c4 | +3.45 (0.55) | 3.43 | 3.54 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Terminal complex ramp level near Terminal 3 (part 4/12) **>1 m** | 80/80 | 4.00 | 8.20 | 9.6 | +0.80 | 0.50 | e6f569c1 | -0.10 (0.55) | 2.99 | 4.85 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |

### taxiway-edge (110 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| Taxiway L2 **>1 m** | 6/19 | 9.15 | 9.25 | 9.3 | +9.15 | 1.08 | 2f0be03d | +9.00 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway B **>1 m** | 10/15 | 9.00 | 9.11 | 9.2 | -9.00 | 1.07 | 35809e3e | -8.80 (1.08) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway M **>1 m** | 12/53 | 8.85 | 9.10 | 9.2 | +8.85 | 1.08 | 2f0be03d | +9.00 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway H **>1 m** | 67/146 | 8.80 | 9.14 | 9.3 | +8.80 | 1.08 | 2f0be03d | +8.80 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway H **>1 m** | 7/11 | 8.70 | 9.24 | 9.3 | +8.70 | 1.08 | 2f0be03d | +8.80 (1.15) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway V | 1/16 | 8.70 | 8.70 | 8.7 | +8.70 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| Taxiway Z/S2 **>1 m** | 8/9 | 8.35 | 9.00 | 9.0 | +2.95 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C/N **>1 m** | 10/29 | 8.20 | 8.52 | 8.7 | -8.20 | 1.61 | c1064033 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| Taxiway P **>1 m** | 5/48 | 8.20 | 8.78 | 8.9 | +8.20 | 1.61 | c1064033 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| Taxiway S2 | 1/3 | 8.10 | 8.10 | 8.1 | -8.10 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway R **>1 m** | 9/23 | 8.00 | 8.30 | 8.3 | +8.00 | 0.93 | 59be8a98 | +8.00 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway F **>1 m** | 6/10 | 7.80 | 8.40 | 8.4 | -7.80 | 1.08 | 2f0be03d | -7.80 (1.15) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| Taxiway F **>1 m** | 25/72 | 7.70 | 8.66 | 8.9 | -7.50 | 1.08 | 2f0be03d | -6.35 (1.15) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| Taxiway B/E **>1 m** | 6/13 | 7.65 | 9.00 | 9.0 | -0.85 | 0.93 | 59be8a98 | +4.40 (1.08) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway N **>1 m** | 5/14 | 7.60 | 8.16 | 8.4 | +6.00 | 0.57 | 1a26bbeb | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| Taxiway Z | 2/6 | 7.35 | 8.51 | 8.8 | +1.45 | 1.27 | c9ff55e8 | +6.80 (3.18) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C/R **>1 m** | 4/5 | 7.30 | 7.91 | 8.0 | -5.35 | 0.93 | 59be8a98 | +0.35 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway F1 **>1 m** | 9/13 | 7.30 | 8.12 | 8.2 | +7.30 | 1.08 | 2f0be03d | +7.35 (1.15) | [40-apron-3-south-middle](40-apron-3-south-middle.png), [00-overview](00-overview.png) |
| Taxiway K **>1 m** | 13/16 | 7.30 | 9.10 | 9.6 | +7.30 | 0.58 | bc91df95 | +7.05 (0.93) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Taxiway C/P | 1/43 | 7.00 | 7.00 | 7.0 | -7.00 | 1.61 | c1064033 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Taxiway Z **>1 m** | 4/9 | 6.80 | 7.11 | 7.2 | -6.80 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway L **>1 m** | 3/56 | 6.80 | 8.00 | 8.3 | +6.80 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| Taxiway T/K/A/B **>1 m** | 5/6 | 6.80 | 7.56 | 8.0 | +6.80 | 0.58 | bc91df95 | +5.30 (0.93) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Taxiway B **>1 m** | 12/12 | 6.75 | 7.20 | 7.3 | +6.75 | 0.58 | bc91df95 | +6.30 (0.93) | [10-ba-F](10-ba-F.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway F **>1 m** | 8/16 | 6.70 | 9.12 | 9.4 | -0.80 | 1.08 | 2f0be03d, 59be8a98 | -4.60 (1.08) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway D | 1/6 | 6.70 | 6.70 | 6.7 | +6.70 | 0.58 | bc91df95 | – | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway U **>1 m** | 13/34 | 6.70 | 7.26 | 7.4 | +6.70 | 3.18 | 8b334c52 | – | [30-rwy-10L](30-rwy-10L.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Taxiway Z/Z2 **>1 m** | 16/43 | 6.65 | 9.00 | 9.2 | +5.60 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway M **>1 m** | 4/18 | 6.50 | 8.97 | 9.0 | +2.75 | 1.08 | 2f0be03d | +8.20 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway L/C **>1 m** | 10/33 | 6.45 | 8.45 | 8.9 | +4.00 | 1.08 | 2f0be03d, c1064033 | +7.90 (1.61) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Taxiway E | 1/53 | 6.40 | 6.40 | 6.4 | +6.40 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| Taxiway L **>1 m** | 3/41 | 6.30 | 6.78 | 6.9 | -6.30 | 1.08 | 2f0be03d | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Taxiway Z | 2/26 | 6.30 | 8.62 | 9.2 | +2.90 | 1.27 | c9ff55e8 | -8.20 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway G **>1 m** | 10/59 | 6.30 | 8.33 | 8.6 | +2.05 | 1.08 | 2f0be03d | +2.00 (1.15) | [30-rwy-1L](30-rwy-1L.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| Taxiway C **>1 m** | 36/43 | 6.10 | 8.75 | 9.3 | -5.90 | 0.93 | 59be8a98, c9ff55e8 | +2.90 (1.27) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway L **>1 m** | 19/19 | 6.10 | 9.02 | 9.3 | -0.60 | 1.15 | 103723b0, 2f0be03d | +2.30 (3.18) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway F1 **>1 m** | 26/73 | 5.90 | 6.95 | 7.4 | -5.90 | 1.08 | 2f0be03d | -5.65 (1.15) | [40-apron-3-south-middle](40-apron-3-south-middle.png), [00-overview](00-overview.png) |
| Taxiway R **>1 m** | 21/22 | 5.10 | 8.80 | 9.1 | +3.80 | 0.93 | 59be8a98 | +5.70 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C **>1 m** | 4/124 | 4.80 | 7.31 | 8.3 | -4.80 | 1.61 | c1064033 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Taxiway C **>1 m** | 10/67 | 4.80 | 5.82 | 6.0 | -4.80 | 1.61 | c1064033 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |

### apron-edge (1 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| apron outline #1 **>1 m** | 14/33 | 8.70 | 9.67 | 9.8 | +8.70 | 0.28 | 0af09b78, 35809e3e, b1d51b0f, d82848c4 | +8.80 (0.55) | [10-ba-A](10-ba-A.png), [40-apron-1-north-west](40-apron-1-north-west.png) |

### extra-pavement (57 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| extra pavement #7 **>1 m** | 35/43 | 7.90 | 8.10 | 8.8 | +7.70 | 1.07 | 35809e3e | -1.20 (3.18) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| extra pavement #13 **>1 m** | 11/11 | 7.90 | 8.10 | 8.2 | +7.90 | 1.07 | 35809e3e | – | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| extra pavement #12 **>1 m** | 27/31 | 7.70 | 8.18 | 8.5 | +7.70 | 1.07 | 35809e3e | – | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #67 **>1 m** | 12/30 | 7.10 | 8.47 | 9.0 | +7.10 | 1.61 | c1064033 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #66 **>1 m** | 130/461 | 6.90 | 8.50 | 9.2 | +6.90 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #45 **>1 m** | 14/143 | 6.80 | 8.38 | 8.9 | -6.80 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #10 **>1 m** | 473/632 | 6.40 | 8.26 | 9.7 | +6.10 | 1.07 | 0af09b78, 103723b0, 2f0be03d, 35809e3e,  | +1.80 (3.18) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #70 **>1 m** | 56/226 | 6.30 | 8.20 | 9.1 | +6.15 | 1.61 | c1064033 | +2.10 (3.18) | [30-rwy-19R](30-rwy-19R.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #40 **>1 m** | 57/81 | 5.80 | 9.00 | 9.2 | +5.80 | 0.93 | 2f0be03d, 59be8a98 | +4.05 (1.08) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #68 **>1 m** | 205/315 | 5.60 | 8.90 | 9.6 | +0.80 | 1.27 | 59be8a98, c9ff55e8 | +2.65 (3.18) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #49 **>1 m** | 27/32 | 5.20 | 7.82 | 8.3 | -4.90 | 1.61 | c1064033 | – | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| extra pavement #54 **>1 m** | 16/91 | 5.05 | 6.45 | 9.3 | +4.00 | 0.93 | 59be8a98 | -1.10 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #71 **>1 m** | 401/1056 | 5.00 | 8.60 | 9.5 | -1.90 | 1.61 | 59be8a98, 8b334c52, c1064033, c9ff55e8 | -0.60 (1.61) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #50 **>1 m** | 34/34 | 4.55 | 7.61 | 9.2 | +4.45 | 1.08 | 2f0be03d | +4.80 (1.61) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #41 **>1 m** | 33/36 | 4.50 | 7.62 | 8.9 | -0.80 | 0.93 | 59be8a98, bc91df95 | +1.60 (1.07) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #72 **>1 m** | 89/126 | 4.50 | 8.20 | 8.9 | +4.20 | 1.61 | c1064033 | +2.80 (3.18) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #34 **>1 m** | 9/9 | 4.50 | 7.22 | 8.9 | -0.20 | 0.58 | bc91df95 | -2.70 (0.93) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #28 **>1 m** | 92/101 | 4.45 | 7.78 | 9.3 | +4.05 | 1.08 | 2f0be03d, 59be8a98 | +2.85 (1.15) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| extra pavement #37 **>1 m** | 473/914 | 4.40 | 8.40 | 9.6 | -0.30 | 1.27 | 35809e3e, 59be8a98, c9ff55e8 | – | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| extra pavement #43 **>1 m** | 40/49 | 4.20 | 8.90 | 9.2 | -0.15 | 0.93 | 59be8a98, bc91df95 | -0.30 (1.07) | [30-rwy-10R](30-rwy-10R.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #63 **>1 m** | 21/39 | 4.10 | 6.50 | 7.9 | -0.10 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #14 **>1 m** | 45/45 | 4.10 | 6.46 | 8.8 | +4.10 | 1.08 | 2f0be03d | +3.90 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #62 **>1 m** | 31/45 | 4.00 | 7.00 | 8.8 | +2.50 | 0.93 | 59be8a98, c9ff55e8 | +2.35 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #74 **>1 m** | 119/192 | 4.00 | 7.52 | 8.8 | +2.60 | 1.61 | c1064033 | +4.10 (3.18) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #51 **>1 m** | 36/57 | 3.90 | 9.20 | 9.4 | +1.60 | 0.93 | 59be8a98 | +2.20 (1.08) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #23 **>1 m** | 79/81 | 3.60 | 9.30 | 9.5 | +3.60 | 1.27 | c9ff55e8 | +5.60 (3.18) | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| extra pavement #11 **>1 m** | 18/19 | 3.55 | 7.53 | 7.7 | +1.00 | 0.55 | 0af09b78, 35809e3e, 8b334c52 | -1.50 (1.07) | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #48 **>1 m** | 28/31 | 2.95 | 5.80 | 6.7 | +0.85 | 0.57 | 1a26bbeb, c1064033 | +3.70 (3.18) | [40-apron-4-central-east](40-apron-4-central-east.png), [00-overview](00-overview.png) |
| extra pavement #57 **>1 m** | 55/56 | 2.90 | 6.68 | 8.7 | -2.80 | 0.57 | 1a26bbeb | -2.85 (1.61) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| extra pavement #42 **>1 m** | 71/80 | 2.90 | 6.20 | 9.2 | +2.70 | 0.58 | bc91df95 | +2.30 (0.93) | [30-rwy-10R](30-rwy-10R.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #21 **>1 m** | 194/197 | 2.80 | 3.20 | 9.4 | +2.80 | 1.27 | c9ff55e8 | – | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| extra pavement #8 **>1 m** | 22/27 | 2.70 | 7.66 | 7.9 | +2.70 | 1.08 | 2f0be03d | +2.85 (1.15) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| extra pavement #69 **>1 m** | 70/79 | 2.60 | 7.91 | 9.6 | -1.00 | 1.27 | 59be8a98, c9ff55e8 | -0.05 (3.18) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #3 **>1 m** | 310/310 | 2.60 | 3.10 | 4.0 | +2.60 | 1.07 | 35809e3e | – | [40-apron-3-south-middle](40-apron-3-south-middle.png), [00-overview](00-overview.png) |
| extra pavement #5 **>1 m** | 45/58 | 2.50 | 7.54 | 8.8 | +0.50 | 1.08 | 2f0be03d | +0.30 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #58 **>1 m** | 178/194 | 2.45 | 5.50 | 8.9 | +2.15 | 0.93 | 103723b0, 59be8a98, c1064033 | +3.10 (1.08) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #32 **>1 m** | 36/42 | 2.35 | 8.00 | 9.1 | -1.35 | 1.08 | 2f0be03d | -0.60 (1.61) | [00-overview](00-overview.png) |
| extra pavement #26 **>1 m** | 4/4 | 2.35 | 4.18 | 4.6 | +2.35 | 0.93 | 59be8a98 | -2.95 (1.08) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| extra pavement #2 **>1 m** | 24/24 | 2.30 | 5.65 | 6.5 | -0.35 | 1.15 | 103723b0, 2f0be03d | -3.40 (3.18) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #0 **>1 m** | 115/115 | 2.20 | 2.72 | 8.0 | +2.20 | 1.15 | 103723b0 | – | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |

### bridge-walkway (28 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| G9 bridge G9 fixed walkway | 2/2 | 5.90 | 5.90 | 5.9 | -5.90 | 0.27 | 151ec51d | -5.25 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| E4 bridge E4 fixed walkway **>1 m** | 6/6 | 5.75 | 5.90 | 5.9 | +5.75 | 0.24 | c235f3b8 | +5.25 (0.42) | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| G8 bridge G8 fixed walkway **>1 m** | 3/3 | 4.90 | 5.70 | 5.9 | +4.90 | 0.27 | 151ec51d | -2.45 (0.50) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G12 bridge G12 fixed walkway **>1 m** | 3/3 | 4.80 | 5.12 | 5.2 | +4.80 | 0.27 | 151ec51d | +3.10 (0.50) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| B5 bridge B5 fixed walkway | 2/2 | 4.50 | 4.74 | 4.8 | +4.50 | 0.55 | 0af09b78 | +4.65 (1.07) | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| A1 bridge A1 fixed walkway **>1 m** | 14/14 | 4.30 | 5.87 | 5.9 | +0.10 | 0.25 | d82848c4 | +1.30 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| C3 bridge C3 fixed walkway | 2/2 | 3.60 | 5.44 | 5.9 | -3.60 | 0.16 | 03dcd4ae | -4.50 (0.42) | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| F11 bridge F11 fixed walkway **>1 m** | 7/7 | 3.30 | 3.48 | 3.6 | -3.30 | 0.27 | 39176bb8 | -3.60 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A8 bridge A8 fixed walkway | 2/2 | 3.30 | 3.62 | 3.7 | +3.30 | 0.25 | d82848c4 | +4.50 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| F22 bridge F22 fixed walkway **>1 m** | 4/4 | 3.15 | 5.36 | 5.9 | +3.15 | 0.50 | e6f569c1 | +3.65 (0.58) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| B11 bridge B11 fixed walkway **>1 m** | 14/14 | 3.10 | 4.07 | 4.2 | -3.00 | 0.28 | b1d51b0f | -0.35 (0.55) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| F13 bridge F13 fixed walkway | 2/2 | 3.05 | 3.65 | 3.8 | +3.05 | 0.27 | 39176bb8 | +2.40 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| D8 bridge D8 fixed walkway **>1 m** | 3/3 | 2.90 | 3.30 | 3.4 | -2.90 | 0.24 | bf5c7afc | -3.20 (0.42) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| F13 bridge F13 fixed walkway **>1 m** | 4/4 | 2.35 | 2.60 | 2.6 | -2.05 | 0.27 | 39176bb8 | -2.75 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G9 bridge G9 fixed walkway **>1 m** | 3/3 | 2.30 | 4.94 | 5.6 | -2.30 | 0.27 | 151ec51d | -2.70 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G10 bridge G10 fixed walkway **>1 m** | 4/4 | 2.20 | 2.64 | 2.7 | +2.20 | 0.50 | e6f569c1 | -3.10 (1.07) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| D14 bridge D14 fixed walkway | 2/2 | 2.05 | 3.29 | 3.6 | -2.05 | 0.24 | bf5c7afc | -2.25 (0.42) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| D1 bridge D1 fixed walkway | 2/2 | 2.00 | 2.56 | 2.7 | -2.00 | 0.24 | bf5c7afc | -2.05 (0.42) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| F11 bridge F11 fixed walkway **>1 m** | 5/5 | 2.00 | 4.18 | 4.3 | -2.00 | 0.27 | 39176bb8 | -2.60 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| B16 bridge B16 fixed walkway **>1 m** | 15/15 | 1.90 | 4.32 | 4.7 | +0.60 | 0.28 | b1d51b0f | +3.05 (0.55) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| D9 bridge D9 fixed walkway | 2/2 | 1.65 | 1.69 | 1.7 | -0.05 | 0.24 | bf5c7afc | -2.15 (0.42) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| D11 bridge D11 fixed walkway | 2/2 | 1.50 | 1.98 | 2.1 | -0.60 | 0.24 | bf5c7afc | -0.90 (0.42) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G8 bridge G8 fixed walkway **>1 m** | 5/5 | 1.20 | 4.22 | 4.5 | -0.10 | 0.27 | 151ec51d | -3.00 (0.50) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| D10 bridge D10 fixed walkway **>1 m** | 10/10 | 1.10 | 1.38 | 2.1 | -1.05 | 0.24 | bf5c7afc | -1.50 (0.42) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| F15 bridge F15 fixed walkway **>1 m** | 3/3 | 1.10 | 2.14 | 2.4 | -1.10 | 0.27 | 39176bb8 | -2.00 (0.50) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| A8 bridge A8 fixed walkway | 3/3 | 0.40 | 2.40 | 2.9 | +0.40 | 0.25 | d82848c4 | +2.70 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G12 bridge G12 fixed walkway | 3/5 | 0.30 | 3.66 | 4.5 | -0.30 | 0.27 | 151ec51d | -2.50 (0.50) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| D16 bridge D16 fixed walkway | 2/2 | 0.30 | 0.30 | 0.3 | +0.30 | 0.24 | bf5c7afc | -4.15 (0.42) | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |

### bridge-rotunda (116 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| A9 bridge A9 rotunda | 1/1 | 5.98 | 5.98 | 6.0 | +5.98 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| D16 bridge D16 rotunda | 1/1 | 5.98 | 5.98 | 6.0 | +5.98 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| B4 bridge B4 rotunda | 1/1 | 5.97 | 5.97 | 6.0 | +5.97 | 0.28 | raster | – | [10-ba-B](10-ba-B.png), [20-itb-tower](20-itb-tower.png) |
| F15 bridge F15 rotunda | 1/1 | 5.97 | 5.97 | 6.0 | +5.97 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| B27 bridge B27 rotunda | 1/1 | 5.97 | 5.97 | 6.0 | +5.97 | 0.28 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| F14 bridge F14 rotunda | 1/1 | 5.97 | 5.97 | 6.0 | +5.97 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| C6 bridge C6 rotunda | 1/1 | 5.96 | 5.96 | 6.0 | +5.96 | 0.16 | raster | – | [10-ba-C](10-ba-C.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| C7 bridge C7 rotunda | 1/1 | 5.96 | 5.96 | 6.0 | +5.96 | 0.16 | raster | – | [10-ba-C](10-ba-C.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| F17 bridge F17 rotunda | 1/1 | 5.95 | 5.95 | 6.0 | +5.95 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| D14 bridge D14 rotunda | 1/1 | 5.95 | 5.95 | 5.9 | +5.95 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| E7 bridge E7 rotunda | 1/1 | 5.95 | 5.95 | 5.9 | +5.95 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| F22 bridge F22 rotunda | 1/1 | 5.95 | 5.95 | 5.9 | +5.95 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| C3 bridge C3 rotunda | 1/1 | 5.95 | 5.95 | 5.9 | +5.95 | 0.16 | raster | – | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| B1 bridge B1 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.55 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| D15 bridge D15 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| F15 bridge F15 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G3 bridge G3 rotunda | 1/1 | 5.92 | 5.92 | 5.9 | +5.92 | 0.27 | raster | – | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| G4 bridge G4 rotunda | 1/1 | 5.92 | 5.92 | 5.9 | +5.92 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A2 bridge A2 rotunda | 1/1 | 5.92 | 5.92 | 5.9 | +5.92 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A8 bridge A8 rotunda | 1/1 | 5.92 | 5.92 | 5.9 | +5.92 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B14 bridge B14 rotunda | 1/1 | 5.91 | 5.91 | 5.9 | +5.91 | 0.28 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| E4 bridge E4 rotunda | 1/1 | 5.91 | 5.91 | 5.9 | +5.91 | 0.24 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| A6 bridge A7 rotunda | 1/1 | 5.91 | 5.91 | 5.9 | +5.91 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| D9 bridge D9 rotunda | 1/1 | 5.91 | 5.91 | 5.9 | +5.91 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G9 bridge G9 rotunda | 1/1 | 5.91 | 5.91 | 5.9 | +5.91 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| E8 bridge E8 rotunda | 1/1 | 5.90 | 5.90 | 5.9 | +5.90 | 0.24 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| D11 bridge D11 rotunda | 1/1 | 5.89 | 5.89 | 5.9 | +5.89 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| A6 bridge A7 rotunda | 1/1 | 5.86 | 5.86 | 5.9 | +5.86 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| D8 bridge D8 rotunda | 1/1 | 5.85 | 5.85 | 5.8 | +5.85 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G7 bridge G7 rotunda | 1/1 | 5.77 | 5.77 | 5.8 | +5.77 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G8 bridge G8 rotunda | 1/1 | 5.74 | 5.74 | 5.7 | +5.74 | 0.27 | raster | – | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| A2 bridge A2 rotunda | 1/1 | 5.74 | 5.74 | 5.7 | +5.74 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| F16 bridge F16 rotunda | 1/1 | 5.72 | 5.72 | 5.7 | +5.72 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F19 bridge F19 rotunda | 1/1 | 5.70 | 5.70 | 5.7 | +5.70 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G5 bridge G5 rotunda | 1/1 | 5.68 | 5.68 | 5.7 | +5.68 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G9 bridge G9 rotunda | 1/1 | 5.67 | 5.67 | 5.7 | +5.67 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| B13 bridge B13 rotunda | 1/1 | 5.61 | 5.61 | 5.6 | +5.61 | 0.28 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| F14 bridge F14 rotunda | 1/1 | 5.59 | 5.59 | 5.6 | +5.59 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A10 bridge A10 rotunda | 1/1 | 5.58 | 5.58 | 5.6 | +5.58 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| G10 bridge G10 rotunda | 1/1 | 5.54 | 5.54 | 5.5 | +5.54 | 0.27 | raster | – | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |

## Deviations from imagery - `naip`

Source: NAIP (2 image(s)) (USDA NAIP: public domain (U.S. Government work); credit requested: "USDA Farm Production and Conservation - Business Center, Geospatial Enterprise Operations" (see docs/research/imagery.md)). Offsets are signed along the outward edge normal (+ = imaged edge outside / right of the model), in metres; `gsd` = ground resolution of the image the profile was read from; `alt` = the same samples read from the next-best image (registration check). Features flagged when the median |offset| > 1.0 m.

| class | features | measured | flagged (median > 1 m) | median of medians | median p90 | typical gsd | notes |
|---|---|---|---|---|---|---|---|
| apron-edge | 1 | 1 | 1 | 8.50 | 9.00 | 0.50 |  |
| bridge-rotunda | 117 | 115 | 0 | 4.93 | 4.93 | 0.50 | automatic disc search, low confidence - use the per-bridge crops |
| bridge-walkway | 28 | 28 | 16 | 3.33 | 4.35 | 0.50 |  |
| building | 130 | 130 | 129 | 4.00 | 7.82 | 0.50 | roof edge vs footprint: relief displacement (roofs lean away from nadir) + registration; see `shift`/`resid` columns |
| emas-bed | 4 | 4 | 2 | 2.07 | 5.90 | 0.50 |  |
| extra-pavement | 60 | 59 | 59 | 4.20 | 8.46 | 0.50 | derived from the same imagery (circular); checks the vectorisation |
| hold-line | 81 | 62 | 28 | 5.05 | 6.17 | 0.50 | needs <= 0.6 m/px; most holds are on 0.9-1.6 m/px shots |
| runway-displaced-threshold | 2 | 2 | 2 | 3.20 | 3.29 | 0.50 |  |
| runway-edge-stripe | 8 | 8 | 0 | 0.58 | 1.00 | 0.50 | 0.91 m stripe; 1L/19R, 1R/19L only on coarse shots |
| runway-end | 4 | 4 | 1 | 0.60 | 0.65 | 0.50 |  |
| runway-threshold | 8 | 8 | 6 | 6.03 | 6.15 | 0.50 | stripe start; needs <= 0.8 m/px |
| stand-leadin | 89 | 0 | 0 | – | – | – | lead-in paint not visible (worn / under the parked aircraft on obs stands) |
| taxiway-centreline | 254 | 0 | 0 | – | – | – | 6 in paint: needs <= 0.35 m/px; the airfield screenshots are 0.5-1.6 m/px and JPEG chroma hides thin yellow lines |
| taxiway-edge | 128 | 128 | 79 | 1.20 | 4.65 | 0.50 |  |

### runway-end (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 10L pavement end **>1 m** | 13/13 | 1.10 | 1.20 | 1.2 | +1.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.70 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 10R pavement end | 13/13 | 0.70 | 0.70 | 0.8 | +0.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.60 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 28L pavement end | 13/13 | 0.50 | 0.60 | 0.6 | -0.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.00 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28R pavement end | 13/13 | 0.40 | 0.40 | 0.4 | -0.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.90 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-threshold (8 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 10L threshold stripes (start 6.1 m past threshold) **>1 m** | 16/16 | 7.20 | 7.30 | 10.1 | +7.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.80 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 19L threshold stripes (start 6.1 m past threshold) **>1 m** | 16/16 | 6.50 | 12.80 | 14.7 | +6.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.50 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| RWY 28L threshold stripes (start 6.1 m past threshold) **>1 m** | 16/16 | 6.05 | 6.10 | 6.1 | +6.05 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +5.80 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 19R threshold stripes (start 6.1 m past threshold) **>1 m** | 16/16 | 6.05 | 12.35 | 14.5 | +6.05 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.70 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| RWY 1L threshold stripes (start 6.1 m past threshold) **>1 m** | 16/16 | 6.00 | 6.10 | 6.1 | +6.00 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.10 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| RWY 1R threshold stripes (start 6.1 m past threshold) **>1 m** | 16/16 | 5.90 | 6.00 | 6.1 | +5.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.10 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| RWY 10R threshold stripes (start 6.1 m past threshold) | 16/16 | 0.65 | 3.85 | 6.9 | +0.65 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.70 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 28R threshold stripes (start 6.1 m past threshold) | 16/16 | 0.10 | 6.20 | 6.2 | +0.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.10 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-displaced-threshold (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28L displaced threshold bar (91.4 m) **>1 m** | 14/14 | 3.30 | 3.37 | 3.4 | +3.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.50 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28R displaced threshold bar (91.4 m) **>1 m** | 14/14 | 3.10 | 3.20 | 3.2 | +3.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.20 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-edge-stripe (8 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 1L/19R edge stripe (north/west side) | 216/228 | 0.80 | 1.50 | 1.8 | +0.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.70 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| RWY 1R/19L edge stripe (north/west side) | 246/258 | 0.80 | 1.30 | 1.8 | +0.65 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.60 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| RWY 10R/28L edge stripe (north/west side) | 340/341 | 0.70 | 0.90 | 1.0 | +0.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.60 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| RWY 1R/19L edge stripe (south/east side) | 244/258 | 0.60 | 1.20 | 1.4 | +0.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.20 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| RWY 1L/19R edge stripe (south/east side) | 216/228 | 0.55 | 1.10 | 1.3 | +0.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.10 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| RWY 10L/28R edge stripe (north/west side) | 354/356 | 0.50 | 0.70 | 0.9 | +0.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.60 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| RWY 10L/28R edge stripe (south/east side) | 354/356 | 0.20 | 0.50 | 0.7 | +0.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.10 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| RWY 10R/28L edge stripe (south/east side) | 340/341 | 0.10 | 0.50 | 0.7 | +0.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.10 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |

### emas-bed (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| EMAS bed beyond RWY 19R **>1 m** | 122/122 | 4.00 | 6.50 | 9.5 | +3.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.40 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| EMAS bed beyond RWY 19L **>1 m** | 118/118 | 3.20 | 7.90 | 9.5 | -0.00 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.20 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| EMAS bed beyond RWY 1L | 130/130 | 0.95 | 2.80 | 8.2 | +0.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.00 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| EMAS bed beyond RWY 1R | 116/116 | 0.55 | 5.30 | 9.5 | +0.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.70 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |

### building (130 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | fit shift | resid median | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Air Traffic Control Tower **>1 m** | 25/25 | 8.90 | 9.18 | 9.7 | +6.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +8.20 (0.60) | 5.09 | 4.17 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| Garage G near International Terminal (part 3/4) **>1 m** | 78/79 | 8.80 | 9.03 | 9.1 | -7.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -9.30 (0.60) | – | – | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| Terminal 3 near Terminal 3 (part 4/4) **>1 m** | 75/76 | 7.30 | 9.46 | 9.7 | +6.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +7.00 (0.60) | 5.83 | 3.98 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Terminal complex ramp level near Terminal 3 (part 5/12) **>1 m** | 78/80 | 7.25 | 9.13 | 9.7 | +7.05 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +7.10 (0.60) | 5.59 | 3.05 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Harvey Milk Terminal 1 near Harvey Milk Terminal 1 (part 2/4) **>1 m** | 86/86 | 7.10 | 9.00 | 9.5 | -7.00 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -7.00 (0.60) | 6.54 | 2.52 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Terminal complex ramp level near Boarding Area A (part 7/13) **>1 m** | 56/79 | 6.90 | 9.05 | 9.7 | +6.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +8.20 (0.60) | 7.05 | 1.06 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Terminal complex ramp level near International Terminal (part 4/13) **>1 m** | 79/79 | 6.80 | 9.22 | 9.7 | -2.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.30 (0.60) | 8.77 | 6.23 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Boarding Area A near Boarding Area A (part 3/4) **>1 m** | 60/76 | 6.80 | 8.81 | 9.6 | +6.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +8.00 (0.60) | 6.75 | 1.05 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Harvey Milk Terminal 1 near Harvey Milk Terminal 1 (part 4/4) **>1 m** | 66/85 | 6.80 | 9.15 | 9.7 | +6.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +4.40 (0.60) | 4.36 | 2.74 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| International Terminal near International Terminal (part 2/4) **>1 m** | 94/94 | 6.80 | 9.27 | 9.7 | -1.85 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.05 (0.60) | 2.10 | 6.36 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Terminal 3 near Terminal 3 (part 3/4) **>1 m** | 76/77 | 6.75 | 8.70 | 9.4 | +6.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.40 (0.60) | 4.27 | 4.39 | [10-ba-F](10-ba-F.png), [20-itb-tower](20-itb-tower.png) |
| Terminal complex ramp level near Boarding Area D (part 19/19) **>1 m** | 69/75 | 6.70 | 8.44 | 9.7 | +6.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.40 (0.60) | 7.37 | 0.52 | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| Boarding Area D near Boarding Area D (part 3/3) **>1 m** | 74/83 | 6.70 | 7.91 | 9.6 | +6.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.40 (0.60) | 7.60 | 0.77 | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Terminal complex ramp level near Boarding Area B (part 13/19) **>1 m** | 75/75 | 6.30 | 7.66 | 9.4 | +2.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.90 (0.60) | 3.74 | 5.89 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| Central Parking Garage near Terminal 3 (part 5/5) **>1 m** | 80/84 | 6.30 | 8.50 | 9.7 | -0.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.20 (0.60) | 2.79 | 5.14 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Boarding Area B near Boarding Area B (part 5/5) **>1 m** | 87/87 | 6.10 | 7.60 | 9.3 | +1.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -5.70 (0.60) | 3.35 | 5.72 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| Terminal complex ramp level near Boarding Area A (part 8/13) **>1 m** | 58/79 | 6.10 | 8.89 | 9.6 | +6.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.35 (0.60) | 7.51 | 2.35 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Terminal 2 near Terminal 2 (part 3/3) **>1 m** | 77/86 | 6.10 | 9.04 | 9.7 | +5.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.00 (0.60) | 6.26 | 2.59 | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| Boarding Area A near Boarding Area A (part 4/4) **>1 m** | 56/76 | 6.05 | 7.85 | 9.7 | +6.00 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +5.50 (0.60) | 7.40 | 2.36 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Terminal complex ramp level near Terminal 2 (part 17/19) **>1 m** | 70/75 | 6.00 | 7.80 | 9.7 | +5.85 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.10 (0.60) | 5.69 | 2.09 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| Super Bay Hangar Building near Boarding Area E (part 2/3) **>1 m** | 97/97 | 5.90 | 9.50 | 9.7 | +5.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.70 (0.60) | 9.27 | 0.50 | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Boarding Area B near Boarding Area B (part 3/5) **>1 m** | 87/87 | 5.80 | 9.20 | 9.3 | -4.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -5.90 (0.60) | 1.77 | 7.17 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Terminal complex ramp level near Harvey Milk Terminal 1 (part 5/19) **>1 m** | 76/76 | 5.75 | 9.60 | 9.9 | -5.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -5.80 (0.60) | 9.00 | 3.03 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Rental Car Center near Boarding Area F (part 3/4) **>1 m** | 80/81 | 5.65 | 8.50 | 9.5 | -1.35 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.70 (0.60) | 4.45 | 2.92 | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| Garage A **>1 m** | 9/9 | 5.60 | 6.72 | 6.8 | -5.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -2.90 (0.60) | 4.83 | 1.40 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Terminal complex ramp level near Boarding Area D (part 18/19) **>1 m** | 72/75 | 5.60 | 9.07 | 9.5 | +5.55 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +4.65 (0.60) | 6.77 | 2.37 | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Terminal complex ramp level near Harvey Milk Terminal 1 (part 6/19) **>1 m** | 75/76 | 5.60 | 7.46 | 9.2 | -2.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -6.60 (0.60) | 2.88 | 4.73 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Terminal complex ramp level near Boarding Area C (part 15/19) **>1 m** | 75/75 | 5.50 | 9.00 | 9.4 | -2.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.00 (0.60) | 4.54 | 4.43 | [10-ba-C](10-ba-C.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Central Parking Garage near Terminal 3 (part 4/5) **>1 m** | 85/85 | 5.50 | 9.00 | 9.7 | -1.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.80 (0.60) | 1.43 | 5.15 | [10-ba-E](10-ba-E.png), [20-itb-tower](20-itb-tower.png) |
| Garage G AirTrain Station **>1 m** | 125/135 | 5.50 | 7.10 | 9.6 | +5.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +4.10 (0.60) | 2.37 | 3.39 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Grand Hyatt Hotel **>1 m** | 114/116 | 5.40 | 8.37 | 9.7 | -1.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.50 (0.60) | 2.18 | 4.66 | [40-apron-3-south-middle](40-apron-3-south-middle.png), [00-overview](00-overview.png) |
| Terminal complex ramp level near Boarding Area B (part 10/19) **>1 m** | 74/75 | 5.30 | 6.56 | 8.7 | -4.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -3.20 (0.60) | 5.06 | 0.83 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Terminal complex ramp level near International Terminal (part 9/13) **>1 m** | 71/79 | 5.30 | 8.70 | 9.6 | +3.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.00 (0.60) | 3.13 | 3.73 | [10-ba-B](10-ba-B.png), [20-itb-tower](20-itb-tower.png) |
| Long Term Parking AirTrain Station **>1 m** | 107/108 | 5.30 | 7.84 | 9.6 | +2.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +5.10 (0.60) | 3.97 | 3.64 | [00-overview](00-overview.png) |
| Boarding Area F near Boarding Area F (part 3/6) **>1 m** | 83/86 | 5.10 | 5.68 | 9.2 | +5.00 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +5.10 (0.60) | 3.74 | 2.69 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Central Parking Garage near Harvey Milk Terminal 1 (part 2/5) **>1 m** | 85/85 | 5.10 | 6.10 | 8.9 | -1.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.40 (0.60) | 8.69 | 0.97 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Terminal complex ramp level near Boarding Area B (part 11/19) **>1 m** | 75/75 | 5.00 | 8.90 | 9.4 | -3.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.50 (0.60) | – | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Terminal complex ramp level near Boarding Area C (part 16/19) **>1 m** | 66/75 | 5.00 | 8.00 | 9.4 | +2.85 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.10 (0.60) | 2.04 | 4.25 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Boarding Area D near Boarding Area D (part 2/3) **>1 m** | 79/83 | 5.00 | 8.42 | 9.5 | +4.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.05 (0.60) | 5.27 | 2.45 | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| International Terminal near International Terminal (part 3/4) **>1 m** | 83/93 | 5.00 | 8.70 | 9.6 | +3.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +8.40 (0.60) | 3.97 | 3.71 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |

### taxiway-edge (128 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| Taxiway E **>1 m** | 7/11 | 9.80 | 9.80 | 9.8 | -9.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.60 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Taxiway L/G **>1 m** | 22/38 | 9.70 | 9.80 | 9.8 | -9.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway N **>1 m** | 28/29 | 9.60 | 9.70 | 9.7 | -9.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -9.50 (0.60) | [30-rwy-28L](30-rwy-28L.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| Taxiway C/R **>1 m** | 5/5 | 8.80 | 9.24 | 9.4 | -7.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -7.75 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway B **>1 m** | 48/70 | 8.70 | 8.80 | 9.5 | -8.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.10 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway S2/S3 **>1 m** | 8/8 | 7.95 | 9.00 | 9.0 | +7.95 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +7.95 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway B **>1 m** | 12/12 | 7.75 | 8.00 | 8.2 | +7.75 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +7.40 (0.60) | [10-ba-F](10-ba-F.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway P **>1 m** | 45/48 | 7.40 | 9.60 | 9.7 | -1.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.60 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| Taxiway C1 **>1 m** | 8/16 | 7.30 | 8.87 | 9.5 | +4.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.95 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway L **>1 m** | 26/26 | 6.90 | 9.55 | 9.7 | +6.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.20 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Taxiway C/U **>1 m** | 13/13 | 6.80 | 9.36 | 9.5 | +1.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -2.10 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway K **>1 m** | 15/16 | 6.80 | 8.64 | 8.9 | +6.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.40 (0.60) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Taxiway A/D **>1 m** | 9/9 | 6.40 | 9.22 | 9.7 | -5.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.50 (0.60) | [10-ba-E](10-ba-E.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Taxiway T/K/A/B **>1 m** | 6/6 | 6.25 | 7.55 | 7.7 | +6.25 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.15 (0.60) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| Taxiway P **>1 m** | 24/26 | 5.75 | 9.07 | 9.7 | +5.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.20 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| Taxiway R **>1 m** | 21/22 | 5.40 | 9.40 | 9.7 | +1.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -3.30 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway B/H **>1 m** | 9/10 | 5.20 | 6.00 | 7.6 | +5.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway B/G **>1 m** | 11/11 | 4.90 | 6.20 | 6.7 | +4.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [10-ba-C](10-ba-C.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway L **>1 m** | 60/118 | 4.70 | 9.70 | 9.8 | -4.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.60 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway A **>1 m** | 11/11 | 4.50 | 7.90 | 9.6 | -0.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.70 (0.60) | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Taxiway B/D **>1 m** | 19/23 | 4.50 | 9.02 | 9.5 | -0.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.70 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway U **>1 m** | 35/40 | 4.40 | 7.66 | 9.1 | +2.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway S3 **>1 m** | 4/4 | 4.10 | 6.58 | 6.7 | +4.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +4.40 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway R **>1 m** | 23/23 | 3.90 | 4.40 | 5.1 | -3.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.80 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway F **>1 m** | 197/234 | 3.70 | 4.30 | 9.4 | -3.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.10 (0.60) | [30-rwy-28L](30-rwy-28L.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| Taxiway S2 **>1 m** | 22/22 | 3.40 | 8.41 | 9.3 | +3.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.60 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway U **>1 m** | 68/80 | 3.35 | 8.54 | 9.6 | +0.45 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +7.80 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway G **>1 m** | 34/59 | 3.15 | 9.15 | 9.7 | -0.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.35 (0.60) | [30-rwy-1L](30-rwy-1L.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| Taxiway G **>1 m** | 13/15 | 2.80 | 4.32 | 4.8 | +2.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.60 (0.60) | [30-rwy-1L](30-rwy-1L.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| Taxiway N **>1 m** | 14/14 | 2.80 | 7.61 | 9.4 | +0.55 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.20 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| Taxiway D **>1 m** | 5/6 | 2.40 | 3.12 | 3.6 | -1.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway R/U **>1 m** | 6/9 | 2.15 | 3.50 | 4.6 | -1.85 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway K **>1 m** | 15/15 | 1.90 | 3.16 | 3.6 | +1.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.35 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway L **>1 m** | 40/41 | 1.80 | 9.41 | 9.6 | +0.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -8.55 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| Taxiway E **>1 m** | 108/108 | 1.80 | 2.20 | 2.3 | -0.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -2.10 (0.60) | [30-rwy-19R](30-rwy-19R.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| Taxiway H **>1 m** | 10/11 | 1.80 | 8.75 | 9.2 | +1.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.70 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway INTERSECTION L/L2 **>1 m** | 4/4 | 1.65 | 1.80 | 1.8 | -1.65 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.55 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway H **>1 m** | 121/146 | 1.60 | 9.20 | 9.7 | +0.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +9.15 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway INTERSECTION L/E **>1 m** | 23/23 | 1.60 | 6.40 | 9.2 | +1.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.20 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| Taxiway L **>1 m** | 56/56 | 1.60 | 8.90 | 9.3 | +1.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.40 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |

### apron-edge (1 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| apron outline #1 **>1 m** | 13/33 | 8.50 | 9.00 | 9.6 | +5.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +8.10 (0.60) | [10-ba-A](10-ba-A.png), [40-apron-1-north-west](40-apron-1-north-west.png) |

### extra-pavement (59 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| extra pavement #26 **>1 m** | 3/4 | 9.40 | 9.64 | 9.7 | +9.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +4.70 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| extra pavement #23 **>1 m** | 81/81 | 9.00 | 9.70 | 9.8 | +9.00 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -3.80 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| extra pavement #73 **>1 m** | 3/3 | 8.70 | 9.26 | 9.4 | +8.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.10 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #7 **>1 m** | 41/43 | 7.90 | 9.20 | 9.6 | +7.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +7.95 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| extra pavement #45 **>1 m** | 46/143 | 7.30 | 9.45 | 9.7 | -7.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -7.20 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #12 **>1 m** | 25/31 | 6.90 | 9.36 | 9.5 | +5.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +6.20 (0.60) | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #13 **>1 m** | 11/11 | 6.10 | 8.70 | 8.8 | -2.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.10 (0.60) | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| extra pavement #67 **>1 m** | 20/30 | 5.80 | 9.41 | 9.7 | +5.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +5.00 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #49 **>1 m** | 30/32 | 5.75 | 9.50 | 9.6 | -4.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.00 (0.60) | [40-apron-2-north-middle](40-apron-2-north-middle.png), [40-apron-4-central-east](40-apron-4-central-east.png) |
| extra pavement #71 **>1 m** | 731/1056 | 5.70 | 9.00 | 9.8 | -1.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.05 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #10 **>1 m** | 592/632 | 5.60 | 9.10 | 9.7 | +1.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.30 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #43 **>1 m** | 46/49 | 5.55 | 9.35 | 9.6 | -0.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -2.70 (0.60) | [30-rwy-10R](30-rwy-10R.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #11 **>1 m** | 19/19 | 5.50 | 9.50 | 9.5 | -2.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -3.90 (0.60) | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #57 **>1 m** | 55/56 | 5.20 | 7.36 | 9.6 | -3.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.90 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| extra pavement #68 **>1 m** | 238/315 | 5.20 | 8.90 | 9.8 | +2.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.70 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #54 **>1 m** | 71/91 | 5.10 | 9.20 | 9.7 | -2.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.10 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #21 **>1 m** | 197/197 | 5.00 | 9.30 | 9.7 | -4.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -5.00 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| extra pavement #66 **>1 m** | 364/461 | 5.00 | 8.80 | 9.7 | +1.35 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.40 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #14 **>1 m** | 45/45 | 4.90 | 7.40 | 9.6 | +4.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +4.80 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #74 **>1 m** | 169/192 | 4.80 | 8.70 | 9.7 | +1.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.20 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #48 **>1 m** | 28/31 | 4.75 | 7.29 | 8.9 | -4.00 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.15 (0.60) | [40-apron-4-central-east](40-apron-4-central-east.png), [00-overview](00-overview.png) |
| extra pavement #40 **>1 m** | 52/81 | 4.70 | 8.89 | 9.7 | +3.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.50 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #72 **>1 m** | 100/126 | 4.65 | 8.12 | 9.8 | +3.95 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.30 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #37 **>1 m** | 758/914 | 4.60 | 9.10 | 9.8 | -0.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.50 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| extra pavement #3 **>1 m** | 310/310 | 4.55 | 9.10 | 9.7 | -2.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.15 (0.60) | [40-apron-3-south-middle](40-apron-3-south-middle.png), [00-overview](00-overview.png) |
| extra pavement #70 **>1 m** | 109/226 | 4.50 | 8.92 | 9.7 | +3.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.40 (0.60) | [30-rwy-19R](30-rwy-19R.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #15 **>1 m** | 115/130 | 4.40 | 8.86 | 9.7 | +1.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.85 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| extra pavement #32 **>1 m** | 40/42 | 4.25 | 6.95 | 9.6 | -2.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -3.40 (0.60) | [00-overview](00-overview.png) |
| extra pavement #20 **>1 m** | 104/105 | 4.20 | 8.41 | 9.6 | -3.55 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -3.70 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| extra pavement #62 **>1 m** | 43/45 | 4.20 | 8.84 | 9.4 | +1.00 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.35 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #28 **>1 m** | 91/101 | 3.90 | 8.20 | 9.4 | +1.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.60 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| extra pavement #69 **>1 m** | 77/79 | 3.60 | 8.44 | 9.5 | -1.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.05 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #64 **>1 m** | 433/515 | 3.60 | 7.30 | 9.7 | +0.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.10 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| extra pavement #0 **>1 m** | 115/115 | 3.50 | 8.70 | 9.7 | +0.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -3.50 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #1 **>1 m** | 111/113 | 3.50 | 8.90 | 9.7 | +1.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.10 (0.60) | [40-apron-3-south-middle](40-apron-3-south-middle.png), [00-overview](00-overview.png) |
| extra pavement #42 **>1 m** | 73/80 | 3.30 | 5.98 | 9.6 | +3.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.20 (0.60) | [30-rwy-10R](30-rwy-10R.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| extra pavement #41 **>1 m** | 36/36 | 3.25 | 8.55 | 9.4 | +0.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.00 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |
| extra pavement #61 **>1 m** | 39/40 | 3.10 | 6.42 | 8.7 | -2.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -2.60 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #5 **>1 m** | 42/58 | 3.00 | 8.46 | 9.1 | -2.25 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.75 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #58 **>1 m** | 182/194 | 2.95 | 6.29 | 9.6 | +2.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.25 (0.60) | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-2-north-middle](40-apron-2-north-middle.png) |

### bridge-walkway (28 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| G9 bridge G9 fixed walkway **>1 m** | 3/3 | 5.40 | 5.40 | 5.4 | -5.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.40 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| D1 bridge D1 fixed walkway | 2/2 | 5.35 | 5.71 | 5.8 | -5.35 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G10 bridge G10 fixed walkway **>1 m** | 4/4 | 4.75 | 5.75 | 5.9 | -3.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +5.25 (0.60) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| C3 bridge C3 fixed walkway | 1/2 | 4.50 | 4.50 | 4.5 | +4.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| A8 bridge A8 fixed walkway **>1 m** | 3/3 | 4.40 | 5.60 | 5.9 | +4.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.80 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| D9 bridge D9 fixed walkway | 2/2 | 4.35 | 5.35 | 5.6 | +4.35 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G8 bridge G8 fixed walkway **>1 m** | 4/5 | 4.25 | 5.63 | 5.9 | +3.45 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | – | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| G12 bridge G12 fixed walkway **>1 m** | 3/3 | 4.10 | 5.54 | 5.9 | +4.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +4.30 (0.60) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| D16 bridge D16 fixed walkway | 2/2 | 4.05 | 4.97 | 5.2 | +4.05 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.10 (0.60) | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| E4 bridge E4 fixed walkway **>1 m** | 6/6 | 3.85 | 5.25 | 5.8 | +3.85 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.65 (0.60) | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| F22 bridge F22 fixed walkway **>1 m** | 4/4 | 3.85 | 5.81 | 5.9 | +3.85 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.80 (0.60) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| B5 bridge B5 fixed walkway | 2/2 | 3.75 | 4.11 | 4.2 | +3.75 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -2.45 (0.60) | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| D11 bridge D11 fixed walkway | 2/2 | 3.60 | 5.20 | 5.6 | +3.60 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.70 (0.60) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| A1 bridge A1 fixed walkway **>1 m** | 14/14 | 3.55 | 5.90 | 5.9 | -1.55 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +1.75 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G9 bridge G9 fixed walkway | 2/2 | 3.10 | 3.42 | 3.5 | -3.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.70 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G12 bridge G12 fixed walkway **>1 m** | 4/5 | 3.10 | 3.87 | 3.9 | -3.10 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.25 (0.60) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| F11 bridge F11 fixed walkway **>1 m** | 5/5 | 3.10 | 4.76 | 5.8 | +0.50 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.30 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G8 bridge G8 fixed walkway **>1 m** | 3/3 | 3.00 | 4.20 | 4.5 | -0.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -4.40 (0.60) | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| B11 bridge B11 fixed walkway **>1 m** | 14/14 | 2.65 | 4.04 | 4.6 | -2.65 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -3.35 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| A8 bridge A8 fixed walkway | 2/2 | 2.55 | 3.95 | 4.3 | +2.55 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.15 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| D14 bridge D14 fixed walkway | 2/2 | 2.40 | 2.56 | 2.6 | +2.40 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +2.20 (0.60) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| F13 bridge F13 fixed walkway **>1 m** | 4/4 | 2.30 | 3.60 | 3.9 | +2.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +0.70 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| D8 bridge D8 fixed walkway **>1 m** | 3/3 | 2.20 | 2.20 | 2.2 | -2.20 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -2.70 (0.60) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| B16 bridge B16 fixed walkway **>1 m** | 15/15 | 1.90 | 3.56 | 4.4 | +1.70 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.80 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| F13 bridge F13 fixed walkway | 2/2 | 1.45 | 1.49 | 1.5 | -0.05 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -0.50 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F15 bridge F15 fixed walkway **>1 m** | 3/3 | 1.20 | 1.84 | 2.0 | +0.90 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | -1.80 (0.60) | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| D10 bridge D10 fixed walkway | 10/10 | 0.80 | 1.00 | 1.0 | +0.80 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +4.20 (0.60) | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| F11 bridge F11 fixed walkway | 7/7 | 0.30 | 0.76 | 1.0 | +0.30 | 0.50 | (0, '/home/user/Calc/sfo3d/refs/cache/na | +3.00 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |

### bridge-rotunda (115 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| E4 bridge E4 rotunda | 1/1 | 5.98 | 5.98 | 6.0 | +5.98 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| A9 bridge A9 rotunda | 1/1 | 5.97 | 5.97 | 6.0 | +5.97 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| F8 bridge F8 rotunda | 1/1 | 5.97 | 5.97 | 6.0 | +5.97 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| C8 bridge C8 rotunda | 1/1 | 5.97 | 5.97 | 6.0 | +5.97 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| F12 bridge F12 rotunda | 1/1 | 5.97 | 5.97 | 6.0 | +5.97 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A2 bridge A2 rotunda | 1/1 | 5.96 | 5.96 | 6.0 | +5.96 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| C6 bridge C6 rotunda | 1/1 | 5.95 | 5.95 | 6.0 | +5.95 | 0.50 | raster | – | [10-ba-C](10-ba-C.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| A10 bridge A10 rotunda | 1/1 | 5.95 | 5.95 | 5.9 | +5.95 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| B27 bridge B27 rotunda | 1/1 | 5.95 | 5.95 | 5.9 | +5.95 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| B16 bridge B16 rotunda | 1/1 | 5.95 | 5.95 | 5.9 | +5.95 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| G6 bridge G6 rotunda | 1/1 | 5.95 | 5.95 | 5.9 | +5.95 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A8 bridge A8 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| D11 bridge D11 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.50 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| E5 bridge E5 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| E8 bridge E8 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| G12 bridge G12 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| F17 bridge F17 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F10 bridge F10 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| G12 bridge G12 rotunda | 1/1 | 5.94 | 5.94 | 5.9 | +5.94 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| C1 bridge C1 rotunda | 1/1 | 5.91 | 5.91 | 5.9 | +5.91 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| E3 bridge E2 rotunda | 1/1 | 5.90 | 5.90 | 5.9 | +5.90 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| G6 bridge G6 rotunda | 1/1 | 5.89 | 5.89 | 5.9 | +5.89 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| B4 bridge B4 rotunda | 1/1 | 5.89 | 5.89 | 5.9 | +5.89 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [20-itb-tower](20-itb-tower.png) |
| E9 bridge E9 rotunda | 1/1 | 5.89 | 5.89 | 5.9 | +5.89 | 0.50 | raster | – | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| C4 bridge C4 rotunda | 1/1 | 5.85 | 5.85 | 5.8 | +5.85 | 0.50 | raster | – | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| B5 bridge B5 rotunda | 1/1 | 5.83 | 5.83 | 5.8 | +5.83 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| D14 bridge D14 rotunda | 1/1 | 5.82 | 5.82 | 5.8 | +5.82 | 0.50 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| A6 bridge A7 rotunda | 1/1 | 5.81 | 5.81 | 5.8 | +5.81 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B25 bridge B24 rotunda | 1/1 | 5.78 | 5.78 | 5.8 | +5.78 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| B14 bridge B14 rotunda | 1/1 | 5.77 | 5.77 | 5.8 | +5.77 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| B23 bridge B22 rotunda | 1/1 | 5.77 | 5.77 | 5.8 | +5.77 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| G10 bridge G14 rotunda | 1/1 | 5.76 | 5.76 | 5.8 | +5.76 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| C10 bridge C10 rotunda | 1/1 | 5.68 | 5.68 | 5.7 | +5.68 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| B13 bridge B13 rotunda | 1/1 | 5.58 | 5.58 | 5.6 | +5.58 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| C7 bridge C7 rotunda | 1/1 | 5.54 | 5.54 | 5.5 | +5.54 | 0.50 | raster | – | [10-ba-C](10-ba-C.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| A11 bridge A13 rotunda | 1/1 | 5.52 | 5.52 | 5.5 | +5.52 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| B18 bridge B18 rotunda | 1/1 | 5.51 | 5.51 | 5.5 | +5.51 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| B12 bridge B12 rotunda | 1/1 | 5.50 | 5.50 | 5.5 | +5.50 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| F11 bridge F11 rotunda | 1/1 | 5.46 | 5.46 | 5.5 | +5.46 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A11 bridge A11 rotunda | 1/1 | 5.38 | 5.38 | 5.4 | +5.38 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |

## Physical conflicts (worst first)

One row per pair of objects (worst part pair shown; `parts` lists all intersecting part pairs), merged over the scenarios in which it occurs. `depth` = short side of the overlap region (m), `vgap` = smallest vertical gap over the overlap (negative = interpenetration). Crops: `crops/conflict_NNNN.png` (vector, committed for the first 60 collisions) and `out/draw/crops/` (over the imagery, local only).

### COLLISION (114)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [1](crops/conflict_0001.png) | LIVE | aircraft-building | UAL1116 B753 (parked) | Boarding Area E | aircraft x building | 3.80 / 18.9 | 0.00 | -6.52 |  | -768, -73 / -714, -294 | [10-ba-E](10-ba-E.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [2](crops/conflict_0002.png) | LIVE | aircraft-building | UAL1116 B753 (parked) | Terminal complex ramp level | aircraft x building | 3.80 / 18.9 | 0.00 | -2.50 |  | -768, -73 / -714, -294 | [10-ba-E](10-ba-E.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [3](crops/conflict_0003.png) | ENVELOPE | envelope-rest-bridge | G7 bridge G7 (L2) (a20n, a21n, a319, a320, a321, a332 ...) | G7 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.55 / 4.3 | 0.00 | -0.15 |  | -1503, 110 / -1278, -799 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [4](crops/conflict_0004.png) | ENVELOPE | envelope-rest-bridge | G3 bridge G3 (L2) (a20n, a21n, a319, a320, a321, a332 ...) | G3 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 11.9 | 0.00 | -0.43 |  | -1378, 178 / -1135, -801 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| [5](crops/conflict_0005.png) | ENVELOPE | envelope-rest-bridge | A10 bridge A10 (L2) (a20n, a21n, a319, a320, a321, a332 ...) | A10 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 11.9 | 0.00 | -0.73 |  | -1327, 746 / -825, -1279 | [10-ba-A](10-ba-A.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| [6](crops/conflict_0006.png) | ENVELOPE | envelope-rest-bridge | F19 bridge F19 (L2) (a20n, a21n, a319, a320, a321, b38m ...) | F19 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 11.9 | 0.00 | -1.28 |  | -1337, -226 / -1288, -424 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [7](crops/conflict_0007.png) | ENVELOPE | envelope-rest-bridge | F12 bridge F12 (L2) (a20n, a21n, a319, a320, a321, b38m ...) | F12 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 10.7 | 0.00 | -0.59 |  | -1135, -115 / -1058, -428 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [8](crops/conflict_0008.png) | ENVELOPE | envelope-rest-bridge | F14 bridge F14 (L2) (a20n, a21n, a319, a320, a321, b38m ...) | F14 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 10.5 | 0.00 | -0.59 |  | -1184, -140 / -1113, -429 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [9](crops/conflict_0009.png) | ENVELOPE | envelope-rest-bridge | F16 bridge F16 (L2) (a20n, a21n, a319, a320, a321, b38m ...) | F16 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 10.4 | 0.00 | -0.06 |  | -1233, -166 / -1168, -429 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [10](crops/conflict_0010.png) | ENVELOPE | envelope-rest-bridge | A6 bridge A7 (L2) (a20n, a21n, a319, a320, a321, a332 ...) | A6 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-le | 3.30 / 10.2 | 0.00 | -0.59 |  | -1174, 652 / -733, -1125 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [11](crops/conflict_0011.png) | ENVELOPE | envelope-rest-bridge | G2 bridge G2 (L2) (a20n, a21n, a319, a320, a321, a332 ...) | G2 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 2.9 | 0.00 | -2.32 |  | -1319, 100 / -1119, -704 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [12](crops/conflict_0012.png) | ENVELOPE | envelope-rest-bridge | G6 bridge G6 (L2) (a20n, a21n, a319, a320, a321, a332 ...) | G6 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 2.7 | 0.00 | -2.32 |  | -1444, 34 / -1261, -704 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [13](crops/conflict_0013.png) | ENVELOPE | envelope-rest-bridge | A5 bridge A5 (L2) (a20n, a21n, a319, a320, a321, a332 ...) | A5 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.30 / 2.2 | 0.00 | -3.01 |  | -1262, 617 / -828, -1135 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| [14](crops/conflict_0014.png) | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | G7 bridge G7 (L1) | G7 bridge G7 (L2) | beacon x rotunda; bellows x rotunda; cab x pedestal; cab x rotunda; cab x walkwa | 3.26 / 10.5 | 0.00 | -0.48 |  | -1502, 101 / -1281, -791 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [15](crops/conflict_0015.png) | ENVELOPE | envelope-rest-bridge | G4 bridge G4 (L2) (a20n, a21n, a319, a320, a321, a332 ...) | G4 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 3.26 / 1.3 | 0.00 | -2.32 |  | -1442, 145 / -1207, -802 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [16](crops/conflict_0016.png) | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | G8 bridge G8 (L1) | G8 bridge G8 (L2) | beacon x pca-hose; bellows x tunnel1; bellows x tunnel2; cab x pca-unit; cab x t | 3.01 / 9.9 | 0.00 | -3.13 |  | -1612, 49 / -1403, -796 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [17](crops/conflict_0017.png) | DOCK-MAX | bridge-aircraft | F19 b78x | F19 bridge F19 (L2) | aircraft x pedestal; aircraft x rotunda; aircraft x stair; aircraft x tunnel1; a | 2.94 / 6.7 | 0.00 | -2.88 |  | -1324, -230 / -1278, -414 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [18](crops/conflict_0018.png) | DOCK-REF | bridge-aircraft | F19 b789 | F19 bridge F19 (L2) | aircraft x pedestal; aircraft x rotunda; aircraft x stair; aircraft x tunnel1; a | 2.94 / 6.7 | 0.00 | -2.87 |  | -1324, -230 / -1278, -414 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [19](crops/conflict_0019.png) | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | A10 bridge A10 (L1) | A10 bridge A10 (L2) | beacon x rotunda; beacon x tunnel1; bellows x tunnel1; cab x rotunda; cab x tunn | 2.84 / 8.2 | 0.00 | -2.72 |  | -1315, 752 / -811, -1279 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| [20](crops/conflict_0020.png) | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | A6 bridge A7 (L1) | A6 bridge A7 (L2) | beacon x tunnel1; bellows x pca-unit; bellows x stair; bellows x tunnel2; cab x  | 2.80 / 11.9 | 0.00 | -2.86 |  | -1188, 646 / -749, -1125 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [21](crops/conflict_0021.png) | LIVE | aircraft-building | UAL852 B772 (parked) | Boarding Area D | aircraft x building | 2.53 / 8.4 | 0.00 | -7.70 |  | -501, 210 / -345, -420 | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [22](crops/conflict_0022.png) | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | G3 bridge G3 (L1) | G3 bridge G3 (L2) | beacon x pedestal; beacon x rotunda; cab x pedestal; cab x rotunda; cab x walkwa | 2.49 / 7.1 | 0.00 | -0.48 |  | -1375, 168 / -1138, -790 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| [23](crops/conflict_0023.png) | LIVE | aircraft-building | ASA528 B737 (parked) | Boarding Area B | aircraft x building | 2.44 / 6.3 | 0.00 | -5.31 |  | -818, 724 / -386, -1023 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [24](crops/conflict_0024.png) | ENVELOPE | envelope-rest-bridge | B25 bridge B24 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B25 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type; tunnel3 x e | 2.39 / 7.4 | 0.00 | -1.05 |  | -977, 948 / -421, -1294 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [25](crops/conflict_0025.png) | ENVELOPE | envelope-rest-bridge | B23 bridge B22 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B23 class envelope | bellows x envelope-type; cab x envelope-type | 2.39 / 6.8 | 0.00 | -1.37 |  | -932, 958 / -377, -1282 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [26](crops/conflict_0026.png) | LIVE | aircraft-building | ASA528 B737 (parked) | Terminal complex ramp level | aircraft x building | 2.36 / 5.9 | 0.00 | -3.26 |  | -819, 724 / -386, -1023 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [27](crops/conflict_0027.png) | LIVE | bridge-aircraft | UAL852 B772 (parked) | D7 bridge D7 (L1) | aircraft x cab; aircraft x cab-roof; aircraft x stair; aircraft x tunnel2; aircr | 2.10 / 4.7 | 0.00 | -1.99 |  | -467, 200 / -320, -394 | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [28](crops/conflict_0028.png) | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | F19 bridge F19 (L1) | F19 bridge F19 (L2) | bellows x tunnel1; bellows x tunnel2; cab x rotunda; cab x tunnel1; cab-roof x r | 1.99 / 4.5 | 0.00 | -2.71 |  | -1324, -232 / -1279, -413 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [29](crops/conflict_0029.png) | ENVELOPE | envelope-rest-bridge | F19 bridge F19 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | F19 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-be | 1.90 / 6.3 | 0.00 | -0.64 |  | -1326, -231 / -1281, -415 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [30](crops/conflict_0030.png) | ENVELOPE | envelope-rest-bridge | E3 bridge E2 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | E3 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type; tunnel3 x e | 1.78 / 5.2 | 0.00 | -0.89 |  | -919, -2 / -814, -427 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| [31](crops/conflict_0031.png) | ENVELOPE | envelope-rest-bridge | F20 bridge F20 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | F20 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type; tunnel3 x e | 1.68 / 4.2 | 0.00 | -0.89 |  | -1323, -261 / -1292, -387 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [32](crops/conflict_0032.png) | ENVELOPE | envelope-rest-bridge | B3 bridge B3 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B3 class envelope | bellows x envelope-type; cab x envelope-type | 1.63 / 3.4 | 0.00 | -1.01 |  | -768, 548 / -423, -844 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| [33](crops/conflict_0033.png) | ENVELOPE | envelope-rest-bridge | B2 bridge B2 (L1) (crj7, crj9, e170, e190, e75l) | B2 class envelope | bellows x envelope-type; cab x envelope-type | 1.63 / 3.0 | 0.00 | -0.06 |  | -978, 543 / -612, -937 | [10-ba-B](10-ba-B.png), [20-itb-tower](20-itb-tower.png) |
| [34](crops/conflict_0034.png) | ENVELOPE | envelope-rest-bridge | G8 bridge G8 (L2) (a20n, a21n, a319, a320, a321, b38m ...) | G8 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; drive-le | 1.61 / 5.1 | 0.00 | -0.64 |  | -1613, 52 / -1402, -799 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [35](crops/conflict_0035.png) | ENVELOPE | envelope-rest-bridge | B1 bridge B1 (L1) (crj7, crj9, e170, e190, e75l) | B1 class envelope | bellows x envelope-type; cab x envelope-type | 1.61 / 2.8 | 0.00 | -0.06 |  | -1012, 530 / -648, -942 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [36](crops/conflict_0036.png) | ENVELOPE | envelope-rest-bridge | A10 bridge A10 (L1) (a20n, a21n, a319, a320, a321, a332 ...) | A10 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; stair x  | 1.60 / 4.3 | 0.00 | -0.64 |  | -1318, 752 / -814, -1281 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| [37](crops/conflict_0037.png) | ENVELOPE | envelope-rest-bridge | A6 bridge A7 (L1) (a20n, a21n, a319, a320, a321, a332 ...) | A6 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; tunnel3  | 1.60 / 4.3 | 0.00 | -0.64 |  | -1181, 647 / -742, -1124 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [38](crops/conflict_0038.png) | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | F11 bridge F11 (L1) | F11 bridge F11 (L2) | drive-beam x tunnel2; drive-control x tunnel1; drive-control x tunnel2; drive-le | 1.57 / 4.3 | 0.00 | -3.34 |  | -1089, -189 / -1051, -341 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [39](crops/conflict_0039.png) | ENVELOPE | envelope-rest-bridge | C4 bridge C4 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | C4 class envelope | bellows x envelope-type; cab x envelope-type | 1.56 / 2.4 | 0.00 | -0.94 |  | -686, 450 / -396, -718 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| [40](crops/conflict_0040.png) | DOCK-REF | bridge-aircraft | G1 b789 | G1 bridge G1 (L2) | aircraft x drive-control; aircraft x drive-leg; aircraft x stair; aircraft x tun | 1.55 / 3.3 | 0.00 | -0.50 |  | -1248, 137 / -1039, -704 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [41](crops/conflict_0041.png) | DOCK-MAX | bridge-aircraft | G1 b78x | G1 bridge G1 (L2) | aircraft x drive-control; aircraft x drive-leg; aircraft x stair; aircraft x tun | 1.49 / 3.0 | 0.00 | -1.25 |  | -1248, 137 / -1040, -704 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [42](crops/conflict_0042.png) | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | G12 bridge G12 (L1) | G12 bridge G12 (L2) | drive-beam x tunnel2; drive-control x tunnel1; drive-control x tunnel2; drive-le | 1.48 / 3.7 | 0.00 | -3.18 |  | -1606, 15 / -1413, -763 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [43](crops/conflict_0043.png) | ENVELOPE | envelope-rest-bridge | G7 bridge G7 (L1) (a20n, a21n, a319, a320, a321, a332 ...) | G7 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 1.45 / 1.8 | 0.00 | -0.31 |  | -1498, 101 / -1278, -789 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [44](crops/conflict_0044.png) | ENVELOPE | envelope-rest-bridge | B9 bridge B9 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B9 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.38 / 1.2 | 0.00 | -0.48 |  | -765, 680 / -359, -958 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [45](crops/conflict_0045.png) | ENVELOPE | envelope-rest-bridge | B12 bridge B12 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B12 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.38 / 1.2 | 0.00 | -0.48 |  | -784, 716 / -359, -999 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [46](crops/conflict_0046.png) | ENVELOPE | envelope-rest-bridge | B13 bridge B13 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B13 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.36 / 1.1 | 0.00 | -0.48 |  | -806, 756 / -359, -1045 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [47](crops/conflict_0047.png) | ENVELOPE | envelope-rest-bridge | B18 bridge B18 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B18 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.35 / 1.0 | 0.00 | -0.48 |  | -863, 865 / -360, -1168 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [48](crops/conflict_0048.png) | ENVELOPE | envelope-rest-bridge | B14 bridge B14 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B14 class envelope | bellows x envelope-type; cab x envelope-type | 1.35 / 1.0 | 0.00 | -0.48 |  | -825, 792 / -359, -1086 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [49](crops/conflict_0049.png) | ENVELOPE | envelope-rest-bridge | B21 bridge B21 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B21 class envelope | bellows x envelope-type; cab x envelope-type | 1.33 / 1.0 | 0.00 | -0.48 |  | -884, 904 / -359, -1212 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [50](crops/conflict_0050.png) | ENVELOPE | envelope-rest-bridge | G3 bridge G3 (L1) (a20n, a21n, a319, a320, a321, a332 ...) | G3 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 1.28 / 1.2 | 0.00 | -0.31 |  | -1371, 168 / -1134, -789 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| [51](crops/conflict_0051.png) | DOCK-REF | bridge-aircraft | B23 b38m | B23 bridge B22 (L1) | aircraft x tunnel2; aircraft x tunnel3 | 1.24 / 1.8 | 0.00 | -1.03 |  | -933, 958 / -378, -1283 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [52](crops/conflict_0052.png) | DOCK-MAX | bridge-aircraft | B23 b39m | B23 bridge B22 (L1) | aircraft x tunnel2; aircraft x tunnel3 | 1.22 / 1.8 | 0.00 | -1.03 |  | -933, 958 / -377, -1283 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [53](crops/conflict_0053.png) | ENVELOPE | envelope-rest-bridge | A3 bridge A4 (L2) (a20n, a21n, a319, a320, a321, b38m ...) | A3 class envelope | cab x envelope-type; drive-beam x envelope-type; drive-control x envelope-type;  | 1.20 / 1.7 | 0.00 | -0.12 |  | -1229, 549 / -830, -1059 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [54](crops/conflict_0054.png) | ENVELOPE | envelope-rest-bridge | B17 bridge B17 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B17 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.18 / 0.8 | 0.00 | -0.48 |  | -845, 831 / -359, -1129 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [55](crops/conflict_0055.png) | DOCK-REF | bridge-aircraft | G8 b789 | G8 bridge G8 (L2) | aircraft x stair; aircraft x tunnel3 | 1.10 / 4.2 | 0.00 | -3.29 |  | -1627, 44 / -1418, -799 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [56](crops/conflict_0056.png) | DOCK-REF | bridge-aircraft | F22 b789 | F22 bridge F22 (L2) | aircraft x stair; aircraft x tunnel3 | 1.10 / 4.2 | 0.00 | -3.29 |  | -1277, -296 / -1268, -334 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [57](crops/conflict_0057.png) | DOCK-REF | bridge-aircraft | F15 b789 | F15 bridge F15 (L2) | aircraft x stair; aircraft x tunnel3 | 1.10 / 4.2 | 0.00 | -3.29 |  | -1211, -269 / -1196, -328 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [58](crops/conflict_0058.png) | DOCK-REF | bridge-aircraft | F11 b789 | F11 bridge F11 (L2) | aircraft x stair; aircraft x tunnel3 | 1.10 / 4.2 | 0.00 | -3.29 |  | -1077, -214 / -1053, -314 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [59](crops/conflict_0059.png) | DOCK-MAX | bridge-aircraft | F22 b78x | F22 bridge F22 (L2) | aircraft x stair; aircraft x tunnel3 | 1.10 / 3.6 | 0.00 | -2.54 |  | -1278, -296 / -1268, -334 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| [60](crops/conflict_0060.png) | DOCK-MAX | bridge-aircraft | G8 b78x | G8 bridge G8 (L2) | aircraft x stair; aircraft x tunnel3 | 1.10 / 3.6 | 0.00 | -2.54 |  | -1627, 45 / -1418, -799 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 61 | DOCK-MAX | bridge-aircraft | F15 b78x | F15 bridge F15 (L2) | aircraft x stair; aircraft x tunnel3 | 1.10 / 3.6 | 0.00 | -2.54 |  | -1211, -269 / -1197, -328 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 62 | DOCK-MAX | bridge-aircraft | F11 b78x | F11 bridge F11 (L2) | aircraft x stair; aircraft x tunnel3 | 1.10 / 3.6 | 0.00 | -2.54 |  | -1078, -214 / -1053, -314 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 63 | LIVE | bridge-aircraft | SKW5212 CRJ2 (parked) | F10 bridge F10 (L1) | aircraft x drive-beam; aircraft x drive-control; aircraft x drive-leg; aircraft  | 1.10 / 3.5 | 0.00 | -3.36 |  | -983, -224 / -973, -261 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 64 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | F13 bridge F13 (L1) | F13 bridge F13 (L2) | drive-control x tunnel1; drive-control x tunnel2; rotunda x walkway; stair x pca | 1.10 / 1.4 | 0.00 | -1.30 |  | -1148, -229 / -1122, -334 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 65 | ENVELOPE | envelope-rest-bridge | G5 bridge G5 (L2) (a20n, a319, a320, b737, b762, bcs1 ...) | G5 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.10 / 1.4 | 0.00 | -1.77 |  | -1376, 72 / -1183, -706 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 66 | ENVELOPE | envelope-rest-bridge | G1 bridge G1 (L2) (a20n, a319, a320, b737, bcs1, e170 ...) | G1 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.10 / 1.1 | 0.00 | -1.30 |  | -1246, 139 / -1036, -705 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 67 | DOCK-MAX,DOCK-REF | bridge-bridge | F15 bridge F15 (L1) | F15 bridge F15 (L2) | stair x pca-hose; stair x pca-unit; stair x tunnel2 | 1.02 / 0.8 | 0.00 | -0.02 |  | -1215, -257 / -1194, -340 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 68 | ENVELOPE | envelope-rest-bridge | C10 bridge C10 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | C10 class envelope | bellows x envelope-type; cab x envelope-type | 0.99 / 0.6 | 0.00 | -0.48 |  | -583, 466 / -298, -684 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| 69 | ENVELOPE | envelope-rest-bridge | B27 bridge B27 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | B27 class envelope | bellows x envelope-type; cab x envelope-type | 0.91 / 0.4 | 0.00 | -0.27 |  | -1026, 908 / -484, -1282 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 70 | ENVELOPE | envelope-rest-bridge | F12 bridge F12 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | F12 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; stair x  | 0.87 / 0.6 | 0.00 | -3.13 |  | -1129, -123 / -1056, -418 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 71 | DOCK-MAX,DOCK-REF | bridge-bridge | F12 bridge F12 (L1) | F12 bridge F12 (L2) | drive-beam x rotunda; drive-beam x tunnel1; drive-control x rotunda; drive-leg x | 0.83 / 2.1 | 0.00 | -2.83 |  | -1135, -128 / -1063, -416 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 72 | ENVELOPE | envelope-rest-bridge | F14 bridge F14 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | F14 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.80 / 0.6 | 0.00 | -3.13 |  | -1178, -148 / -1111, -419 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 73 | DOCK-REF | bridge-aircraft | B19 crj9 | B19 bridge B20 (L1) | aircraft x drive-leg; aircraft x tunnel3 | 0.76 / 0.9 | 0.00 | -1.44 |  | -984, 856 / -471, -1217 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 74 | ENVELOPE | envelope-rest-bridge | F16 bridge F16 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | F16 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; stair x  | 0.76 / 0.5 | 0.00 | -2.52 |  | -1227, -174 / -1166, -419 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 75 | DOCK-MAX | bridge-aircraft | B19 e190 | B19 bridge B20 (L1) | aircraft x drive-leg; aircraft x tunnel3 | 0.75 / 1.2 | 0.00 | -0.57 |  | -984, 856 / -471, -1217 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 76 | ENVELOPE | envelope-rest-bridge | F17 bridge F17 (L1) (a20n, a21n, a319, a320, a321, b38m ...) | F17 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; stair x  | 0.74 / 0.5 | 0.00 | -2.52 |  | -1277, -200 / -1222, -420 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 77 | LIVE | bridge-aircraft | UAL852 B772 (parked) | D5 bridge D5 (L1) | aircraft x rotunda; aircraft x walkway | 0.72 / 0.6 | 0.00 | -1.24 |  | -495, 220 / -335, -426 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| 78 | ENVELOPE | envelope-rest-bridge | G10 bridge G14 (L1) (a332, a333, a359, a35k, b762, b763 ...) | G10 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.71 / 0.3 | 0.00 | -3.13 |  | -1577, -22 / -1404, -717 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 79 | DOCK-MAX,DOCK-REF | bridge-bridge | A5 bridge A5 (L1) | A5 bridge A5 (L2) | cab x rotunda; cab-roof x rotunda; drive-beam x rotunda; drive-control x rotunda | 0.70 / 0.7 | 0.00 | -4.97 |  | -1251, 616 / -819, -1129 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 80 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | D1 bridge D1 (L1) | D1 VDGS / stand sign | tunnel1 x stand-sign-back; tunnel1 x vdgs-display; tunnel1 x vdgs-display-base;  | 0.65 / 0.3 | 0.00 | -2.18 |  | -632, 222 / -455, -492 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| 81 | DOCK-MAX,DOCK-REF | bridge-bridge | F22 bridge F21 (L1) | F22 bridge F22 (L2) | stair x pca-hose; stair x pca-unit; stair x tunnel2 | 0.63 / 0.3 | 0.00 | -0.02 |  | -1281, -284 / -1266, -347 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 82 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | C5 bridge C5 (L1) | C5 VDGS / stand sign | drive-beam x stand-sign-back; drive-beam x vdgs-display; drive-beam x vdgs-displ | 0.60 / 0.9 | 0.00 | -2.64 |  | -656, 386 / -400, -647 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| 83 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | C6 bridge C6 (L1) | C6 VDGS / stand sign | tunnel1 x stand-sign-back; tunnel1 x vdgs-display; tunnel1 x vdgs-display-base;  | 0.60 / 0.9 | 0.00 | -2.86 |  | -641, 465 / -349, -710 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| 84 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | B26 bridge B26 (L1) | B27 VDGS / stand sign | tunnel1 x vdgs-display; tunnel1 x vdgs-display-base; tunnel2 x vdgs-display; tun | 0.60 / 0.9 | 0.00 | -0.77 |  | -1011, 914 / -467, -1280 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 85 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | D5 bridge D5 (L1) | D5 VDGS / stand sign | tunnel1 x stand-sign-back; tunnel1 x vdgs-display; tunnel1 x vdgs-display-base;  | 0.60 / 0.9 | 0.00 | -2.86 |  | -494, 231 / -329, -435 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| 86 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | D15 bridge D15 (L1) | D15 VDGS / stand sign | tunnel1 x stand-sign-back; tunnel1 x vdgs-display; tunnel1 x vdgs-display-base;  | 0.60 / 0.9 | 0.00 | -2.90 |  | -584, 86 / -476, -349 | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| 87 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | E11 bridge E11 (L1) | E11 VDGS / stand sign | pca-hose x vdgs-post; pca-unit x vdgs-display-base; pca-unit x vdgs-post; tunnel | 0.60 / 0.9 | 0.00 | -2.77 |  | -736, -75 / -686, -277 | [10-ba-E](10-ba-E.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 88 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | E13 bridge E12 (L1) | E13 VDGS / stand sign | drive-beam x vdgs-post; drive-leg x stand-sign-back; drive-leg x vdgs-display; d | 0.60 / 0.9 | 0.00 | -2.64 |  | -789, -106 / -747, -275 | [10-ba-E](10-ba-E.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 89 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | F20 bridge F20 (L1) | F20 VDGS / stand sign | walkway x vdgs-display; walkway x vdgs-display-base | 0.60 / 0.9 | 0.00 | -1.26 |  | -1310, -253 / -1277, -388 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 90 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | F8 bridge F8 (L1) | F8 VDGS / stand sign | tunnel1 x stand-sign-back; tunnel1 x vdgs-display; tunnel1 x vdgs-display-base;  | 0.60 / 0.9 | 0.00 | -2.80 |  | -999, -203 / -978, -287 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 91 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | F19 bridge F19 (L1) | F19 VDGS / stand sign | walkway x vdgs-display; walkway x vdgs-display-base | 0.60 / 0.9 | 0.00 | -1.26 |  | -1313, -236 / -1271, -404 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 92 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | E3 bridge E2 (L1) | E3 VDGS / stand sign | rotunda x stand-sign-back; rotunda x vdgs-display; rotunda x vdgs-display-base;  | 0.60 / 0.9 | 0.00 | -2.50 |  | -926, 10 / -814, -441 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 93 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | B16 bridge B16 (L1) | B15 VDGS / stand sign | walkway x vdgs-display; walkway x vdgs-display-base | 0.60 / 0.8 | 0.00 | -1.26 |  | -931, 782 / -459, -1126 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 94 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | B3 bridge B3 (L1) | B3 VDGS / stand sign | rotunda x stand-sign-back; rotunda x vdgs-display; rotunda x vdgs-display-base;  | 0.60 / 0.7 | 0.00 | -2.50 |  | -782, 552 / -433, -853 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| 95 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | D16 bridge D16 (L1) | D16 VDGS / stand sign | drive-beam x vdgs-post; drive-leg x vdgs-post; tunnel2 x vdgs-post-base; tunnel3 | 0.60 / 0.6 | 0.00 | -2.64 |  | -634, 129 / -500, -410 | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| 96 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | D14 bridge D14 (L1) | D14 VDGS / stand sign | drive-beam x vdgs-post; drive-leg x vdgs-post; stair x stand-sign-back; stair x  | 0.60 / 0.5 | 0.00 | -2.64 |  | -568, 58 / -476, -317 | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| 97 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | A15 bridge A14 (L1) | A15 VDGS / stand sign | tunnel1 x stand-sign-back; tunnel1 x vdgs-display; tunnel1 x vdgs-display-base;  | 0.60 / 0.4 | 0.00 | -2.90 |  | -1296, 817 / -765, -1328 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| 98 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | B27 bridge B27 (L1) | B26 bridge B26 (L1) | rotunda x rotunda; walkway x walkway | 0.58 / 0.3 | 0.00 | -3.11 |  | -1007, 903 / -469, -1269 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 99 | LIVE,REST | bridge-vdgs | E4 bridge E4 (L1) | E4 VDGS / stand sign | drive-beam x vdgs-post; drive-leg x vdgs-post; stair x stand-sign-back; stair x  | 0.57 / 0.3 | 0.00 | -2.64 |  | -794, 76 / -667, -438 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 100 | LIVE | aircraft-vdgs | UAL2177 B39M (parked) | D10 VDGS / stand sign | aircraft x vdgs-display; aircraft x vdgs-display-base | 0.49 / 0.2 | 0.00 | -0.18 |  | -485, 64 / -399, -283 | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 101 | ENVELOPE | envelope-rest-bridge | A5 bridge A5 (L1) (a332, a333, a359, a35k, b762, b763 ...) | A5 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type; stair x  | 0.49 / 0.2 | 0.00 | -0.14 |  | -1251, 624 / -815, -1136 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 102 | ENVELOPE | envelope-rest-bridge | G4 bridge G4 (L1) (a332, a333, a359, a35k, b762, b763 ...) | G4 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.45 / 0.1 | 0.00 | -0.14 |  | -1435, 134 / -1206, -789 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 103 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-building | A3 bridge A3 (L1) | International Terminal walkway (elevated walkway) | rotunda x building | 0.42 / 0.8 | 0.00 | -2.70 |  | -1204, 552 / -807, -1050 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 104 | LIVE,REST | bridge-vdgs | E6 bridge E6 (L1) | E6 VDGS / stand sign | tunnel1 x stand-sign-back; tunnel1 x vdgs-display; tunnel1 x vdgs-display-base;  | 0.41 / 0.2 | 0.00 | -0.37 |  | -843, 1 / -745, -394 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 105 | ENVELOPE | envelope-rest-bridge | F22 bridge F21 (L1) (b752, b753, b762, b763, b764, b788 ...) | F22 class envelope | bellows x envelope-type; cab x envelope-type | 0.37 / 0.2 | 0.00 | -1.94 |  | -1293, -283 / -1276, -353 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 106 | LIVE,REST | bridge-vdgs | F6 bridge F6 (L1) | F6 VDGS / stand sign | drive-beam x vdgs-post; drive-leg x vdgs-post-base; tunnel2 x vdgs-post-base; tu | 0.33 / 0.2 | 0.00 | -0.85 |  | -1016, -167 / -976, -326 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 107 | DOCK-MAX,DOCK-REF | bridge-aircraft | A10 b77w | A10 bridge A10 (L2) | aircraft x rotunda | 0.31 / 0.5 | 0.00 | -1.55 |  | -1316, 754 / -812, -1281 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| 108 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-bridge | F14 bridge F14 (L1) | F14 bridge F14 (L2) | drive-control x tunnel1; stair x pca-unit; stair x tunnel1; stair x tunnel2; tun | 0.30 / 0.4 | 0.00 | -2.85 |  | -1184, -155 / -1120, -416 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 109 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-vdgs | A6 bridge A7 (L1) | A6 VDGS / stand sign | rotunda x stand-sign-back; rotunda x vdgs-display; rotunda x vdgs-display-base | 0.14 / 0.0 | 0.00 | -1.20 |  | -1194, 639 / -758, -1123 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 110 | DOCK-MAX,DOCK-REF | bridge-bridge | F16 bridge F16 (L1) | F16 bridge F16 (L2) | stair x pca-unit; stair x tunnel1; stair x tunnel2; tunnel1 x rotunda; tunnel2 x | 0.13 / 0.1 | 0.00 | -2.85 |  | -1233, -180 / -1175, -416 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 111 | ENVELOPE | envelope-envelope | E3 class envelope | E6 class envelope | envelope x envelope | 0.12 / 0.0 | 0.00 | – | E6: b39m,b739 x E3: b39m,b739 | -892, -16 / -797, -402 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 112 | DOCK-MAX,DOCK-REF | bridge-bridge | G4 bridge G4 (L1) | G4 bridge G4 (L2) | stair x tunnel1 | 0.05 / 0.1 | 0.00 | -0.56 |  | -1444, 134 / -1215, -793 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 113 | DOCK-MAX,DOCK-REF | bridge-bridge | G6 bridge G6 (L1) | G6 bridge G6 (L2) | stair x pedestal; stair x rotunda | 0.05 / 0.1 | 0.00 | -0.62 |  | -1442, 45 / -1254, -713 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 114 | OVERSIZE | oversize-not-blocked | A2:a388 | A1 class envelope | aircraft x envelope | – / – | 0.00 | – | a388 (79.8 m span) at A2 reaches A1 (nose distance 94.8 m >= block radius 59.0 m): A1 stays available | -1086, 567 / -696, -1009 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |

### OFF-PAVEMENT (4)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 115 | LIVE | gear-off-pavement | UAL2467 B39M (parked) | app paved raster (ground.js physics, 1.0 m) | aircraft x pavement | – / – | – | – | unpaved under nose, main, main gear | -357, 471 / -96, -583 | [40-apron-1-north-west](40-apron-1-north-west.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| 116 | LIVE | gear-off-pavement | SKW3490 E75L (parked) | app paved raster (ground.js physics, 1.0 m) | aircraft x pavement | – / – | – | – | unpaved under nose, main, main gear | 508, 97 / 495, 152 | [40-apron-2-north-middle](40-apron-2-north-middle.png), [00-overview](00-overview.png) |
| 117 | LIVE | gear-off-pavement | UAL2649 A319 (parked) | app paved raster (ground.js physics, 1.0 m) | aircraft x pavement | – / – | – | – | unpaved under nose, main gear | 769, 643 / 980, -209 | [40-apron-4-central-east](40-apron-4-central-east.png), [00-overview](00-overview.png) |
| 118 | LIVE | gear-off-pavement | JBU578 A321 (parked) | app paved raster (ground.js physics, 1.0 m) | aircraft x pavement | – / – | – | – | unpaved under nose, main, main gear | 851, 737 / 1097, -255 | [40-apron-4-central-east](40-apron-4-central-east.png), [00-overview](00-overview.png) |

### CLEARANCE (50)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 119 | OVERSIZE | oversize-not-blocked | A6:a388 | A2 class envelope | aircraft x envelope | – / – | 0.53 | – | a388 (79.8 m span) at A6 reaches A2 (nose distance 75.0 m >= block radius 73.5 m): A2 stays available | -1121, 632 / -696, -1082 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 120 | OVERSIZE | oversize-not-blocked | A2:a388 | A6 class envelope | aircraft x envelope | – / – | 0.56 | – | a388 (79.8 m span) at A2 reaches A6 (nose distance 75.0 m >= block radius 73.5 m): A6 stays available | -1122, 637 / -695, -1087 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 121 | DOCK-MAX | aircraft-aircraft | E3 b39m | E6 b39m | aircraft x aircraft | – / – | 1.27 | – | 1.3 m < ICAO 4.5 m | -892, -17 / -797, -401 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 122 | ENVELOPE | envelope-envelope | G2 class envelope | G5 class envelope | envelope x envelope | – / – | 1.50 | – | 1.5 m < ICAO 7.5 m | -1343, 61 / -1159, -681 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 123 | ENVELOPE | envelope-envelope | G10 class envelope | G9 class envelope | envelope x envelope | – / – | 1.60 | – | 1.6 m < ICAO 7.5 m | -1526, -47 / -1372, -671 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 124 | ENVELOPE | envelope-envelope | G6 class envelope | G9 class envelope | envelope x envelope | – / – | 1.70 | – | 1.7 m < ICAO 7.5 m | -1466, -10 / -1301, -676 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 125 | ENVELOPE | envelope-envelope | A1 class envelope | A2 class envelope | envelope x envelope | – / – | 2.04 | – | 2.0 m < ICAO 7.5 m | -1088, 569 / -696, -1011 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 126 | ENVELOPE | envelope-envelope | G5 class envelope | G6 class envelope | envelope x envelope | – / – | 2.20 | – | 2.2 m < ICAO 7.5 m | -1401, 20 / -1230, -672 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 127 | ENVELOPE | envelope-envelope | B17 class envelope | B18 class envelope | envelope x envelope | – / – | 2.39 | – | 2.4 m < ICAO 4.5 m | -838, 855 / -341, -1147 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 128 | OVERSIZE | oversize-not-blocked | A2:b748 | A1 class envelope | aircraft x envelope | – / – | 2.78 | – | b748 (68.4 m span) at A2 reaches A1 (nose distance 94.8 m >= block radius 59.0 m): A1 stays available | -1083, 572 / -691, -1011 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 129 | ENVELOPE | envelope-envelope | B3 class envelope | C1 class envelope | envelope x envelope | – / – | 2.90 | – | 2.9 m < ICAO 4.5 m | -752, 522 / -421, -813 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| 130 | ENVELOPE | envelope-envelope | G4 class envelope | G7 class envelope | envelope x envelope | – / – | 3.00 | – | 3.0 m < ICAO 7.5 m | -1486, 160 / -1240, -835 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 131 | ENVELOPE | envelope-envelope | A3 class envelope | A5 class envelope | envelope x envelope | – / – | 3.00 | – | 3.0 m < ICAO 7.5 m | -1272, 575 / -856, -1102 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 132 | ENVELOPE | envelope-envelope | A5 class envelope | A9 class envelope | envelope x envelope | – / – | 3.00 | – | 3.0 m < ICAO 7.5 m | -1310, 637 / -861, -1175 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 133 | ENVELOPE | envelope-envelope | A10 class envelope | A9 class envelope | envelope x envelope | – / – | 3.00 | – | 3.0 m < ICAO 7.5 m | -1335, 705 / -852, -1247 | [10-ba-A](10-ba-A.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| 134 | ENVELOPE | envelope-envelope | G3 class envelope | G4 class envelope | envelope x envelope | – / – | 3.01 | – | 3.0 m < ICAO 7.5 m | -1420, 190 / -1167, -831 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 135 | DOCK-MAX | aircraft-aircraft | F14 md11 | F16 md11 | aircraft x aircraft | – / – | 3.09 | – | 3.1 m < ICAO 7.5 m | -1221, -122 / -1136, -462 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 136 | ENVELOPE | envelope-envelope | F14 class envelope | F16 class envelope | envelope x envelope | – / – | 3.09 | – | 3.1 m < ICAO 7.5 m | -1218, -127 / -1136, -457 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 137 | DOCK-MAX | aircraft-aircraft | F12 md11 | F14 md11 | aircraft x aircraft | – / – | 3.10 | – | 3.1 m < ICAO 7.5 m | -1171, -98 / -1081, -461 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 138 | ENVELOPE | envelope-envelope | F12 class envelope | F14 class envelope | envelope x envelope | – / – | 3.10 | – | 3.1 m < ICAO 7.5 m | -1169, -102 / -1081, -455 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 139 | DOCK-REF | aircraft-aircraft | B17 b38m | B18 b38m | aircraft x aircraft | – / – | 3.39 | – | 3.4 m < ICAO 4.5 m | -834, 857 / -337, -1147 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 140 | DOCK-MAX | aircraft-aircraft | B17 b39m | B18 b39m | aircraft x aircraft | – / – | 3.39 | – | 3.4 m < ICAO 4.5 m | -831, 859 / -334, -1147 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 141 | ENVELOPE | envelope-envelope | B26 class envelope | B27 class envelope | envelope x envelope | – / – | 3.46 | – | 3.5 m < ICAO 4.5 m | -1047, 923 / -495, -1305 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 142 | DOCK-REF | aircraft-aircraft | E3 b38m | E6 b38m | aircraft x aircraft | – / – | 3.78 | – | 3.8 m < ICAO 4.5 m | -892, -16 / -796, -403 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 143 | DOCK-MAX | aircraft-aircraft | B3 b39m | C1 b39m | aircraft x aircraft | – / – | 3.80 | – | 3.8 m < ICAO 4.5 m | -751, 522 / -420, -813 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| 144 | OVERSIZE | oversize-not-blocked | A2:b744 | A1 class envelope | aircraft x envelope | – / – | 3.87 | – | b744 (68.4 m span) at A2 reaches A1 (nose distance 94.8 m >= block radius 59.0 m): A1 stays available | -1089, 570 / -697, -1012 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 145 | ENVELOPE | envelope-envelope | B13 class envelope | B14 class envelope | envelope x envelope | – / – | 4.10 | – | 4.1 m < ICAO 4.5 m | -798, 781 / -341, -1064 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 146 | ENVELOPE | envelope-envelope | B12 class envelope | B9 class envelope | envelope x envelope | – / – | 4.20 | – | 4.2 m < ICAO 4.5 m | -758, 705 / -341, -977 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 147 | DOCK-MAX | aircraft-aircraft | F16 md11 | F17 md11 | aircraft x aircraft | – / – | 4.40 | – | 4.4 m < ICAO 7.5 m | -1270, -148 / -1192, -462 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 148 | ENVELOPE | envelope-envelope | F16 class envelope | F17 class envelope | envelope x envelope | – / – | 4.40 | – | 4.4 m < ICAO 7.5 m | -1267, -153 / -1192, -456 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 149 | OVERSIZE | oversize-not-blocked | G2:a388 | G1 class envelope | aircraft x envelope | – / – | 4.54 | – | a388 (79.8 m span) at G2 reaches G1 (nose distance 74.3 m >= block radius 71.2 m): G1 stays available | -1270, 88 / -1082, -671 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 150 | OVERSIZE | oversize-not-blocked | F13:a388 | F15 class envelope | aircraft x envelope | – / – | 4.63 | – | a388 (79.8 m span) at F13 reaches F15 (nose distance 73.6 m >= block radius 71.2 m): F15 stays available | -1176, -287 / -1174, -296 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 151 | OVERSIZE | oversize-not-blocked | A8:a388 | A6 class envelope | aircraft x envelope | – / – | 5.54 | – | a388 (79.8 m span) at A8 reaches A6 (nose distance 80.0 m >= block radius 73.5 m): A6 stays available | -1157, 700 / -696, -1159 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 152 | ENVELOPE | envelope-envelope | F11 class envelope | F13 class envelope | envelope x envelope | – / – | 5.57 | – | 5.6 m < ICAO 7.5 m | -1105, -254 / -1095, -291 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 153 | OVERSIZE | oversize-not-blocked | A6:a388 | A8 class envelope | aircraft x envelope | – / – | 5.57 | – | a388 (79.8 m span) at A6 reaches A8 (nose distance 80.0 m >= block radius 73.5 m): A8 stays available | -1159, 705 / -695, -1165 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 154 | DOCK-MAX,DOCK-REF | aircraft-aircraft | G2 b77w | G5 b77w | aircraft x aircraft | – / – | 5.63 | – | 5.6 m < ICAO 7.5 m | -1340, 56 / -1159, -675 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 155 | DOCK-MAX,DOCK-REF | aircraft-aircraft | G10 b77w | G9 b77w | aircraft x aircraft | – / – | 5.70 | – | 5.7 m < ICAO 7.5 m | -1528, -44 / -1372, -675 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 156 | DOCK-MAX,DOCK-REF | aircraft-aircraft | G6 b77w | G9 b77w | aircraft x aircraft | – / – | 5.80 | – | 5.8 m < ICAO 7.5 m | -1466, -10 / -1301, -675 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 157 | ENVELOPE | envelope-envelope | A2 class envelope | A6 class envelope | envelope x envelope | – / – | 6.00 | – | 6.0 m < ICAO 7.5 m | -1121, 634 / -695, -1084 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 158 | OVERSIZE | oversize-not-blocked | A11:a388 | A8 class envelope | aircraft x envelope | – / – | 6.03 | – | a388 (79.8 m span) at A11 reaches A8 (nose distance 80.5 m >= block radius 73.5 m): A8 stays available | -1194, 771 / -696, -1239 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 159 | OVERSIZE | oversize-not-blocked | A8:a388 | A11 class envelope | aircraft x envelope | – / – | 6.07 | – | a388 (79.8 m span) at A8 reaches A11 (nose distance 80.5 m >= block radius 73.5 m): A11 stays available | -1197, 776 / -696, -1245 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 160 | DOCK-MAX,DOCK-REF | aircraft-aircraft | G5 b77w | G6 b77w | aircraft x aircraft | – / – | 6.31 | – | 6.3 m < ICAO 7.5 m | -1403, 23 / -1230, -675 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 161 | DOCK-MAX | aircraft-aircraft | A1 b39m | A2 b77w | aircraft x aircraft | – / – | 6.81 | – | 6.8 m < ICAO 7.5 m | -1089, 568 / -698, -1011 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 162 | OVERSIZE | oversize-not-blocked | A2:b748 | A6 class envelope | aircraft x envelope | – / – | 7.01 | – | b748 (68.4 m span) at A2 reaches A6 (nose distance 75.0 m >= block radius 73.5 m): A6 stays available | -1120, 635 / -694, -1084 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 163 | OVERSIZE | oversize-not-blocked | A6:b748 | A2 class envelope | aircraft x envelope | – / – | 7.02 | – | b748 (68.4 m span) at A6 reaches A2 (nose distance 75.0 m >= block radius 73.5 m): A2 stays available | -1120, 635 / -694, -1085 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 164 | DOCK-MAX,DOCK-REF | aircraft-aircraft | G4 b77w | G7 b77w | aircraft x aircraft | – / – | 7.10 | – | 7.1 m < ICAO 7.5 m | -1484, 156 / -1239, -831 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 165 | DOCK-MAX,DOCK-REF | aircraft-aircraft | A5 b77w | A9 b77w | aircraft x aircraft | – / – | 7.10 | – | 7.1 m < ICAO 7.5 m | -1307, 638 / -858, -1175 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 166 | DOCK-MAX,DOCK-REF | aircraft-aircraft | A10 b77w | A9 b77w | aircraft x aircraft | – / – | 7.10 | – | 7.1 m < ICAO 7.5 m | -1340, 702 / -857, -1247 | [10-ba-A](10-ba-A.png), [40-apron-3-south-middle](40-apron-3-south-middle.png) |
| 167 | DOCK-MAX,DOCK-REF | aircraft-aircraft | G3 b77w | G4 b77w | aircraft x aircraft | – / – | 7.11 | – | 7.1 m < ICAO 7.5 m | -1420, 190 / -1167, -831 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 168 | DOCK-MAX,DOCK-REF | aircraft-aircraft | A3 b77w | A5 b77w | aircraft x aircraft | – / – | 7.38 | – | 7.4 m < ICAO 7.5 m | -1274, 574 / -858, -1103 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |

### WARNING (41)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 169 | STATIC | building-building | West Field Road AirTrain Station (Outbound) | Westfield Road AirTrain Station (Outbound)g | building x building | 30.79 / 399.7 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 400 m2: coplanar faces z-fight - probably one station listed twi | -2115, -321 / -2020, -704 | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| 170 | STATIC | building-building | Central Parking Garage | Terminal One AirTrain Station | building x building | 26.71 / 869.6 | 0.00 | – | walls interpenetrate: 76 % of Terminal One AirTrain Station lies inside Central Parking Garage (13.0 vs 22.0 m | -903, 400 / -612, -775 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 171 | STATIC | building-building | Terminal complex ramp level | Air Traffic Control Tower | building x building | 25.96 / 1125.3 | 0.00 | – | walls interpenetrate: 92 % of Air Traffic Control Tower lies inside Terminal complex ramp level (14.0 vs 5.0 m | -742, 334 / -500, -642 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| 172 | STATIC | building-building | Terminal 2 | Air Traffic Control Tower | building x building | 25.68 / 1119.9 | 0.00 | – | walls interpenetrate: 92 % of Air Traffic Control Tower lies inside Terminal 2 (14.0 vs 19.6 m high) | -742, 335 / -500, -643 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| 173 | STATIC | building-building | Garage G AirTrain Station | Garage G | building x building | 24.95 / 1049.2 | 0.00 | – | walls interpenetrate: 31 % of Garage G AirTrain Station lies inside Garage G (13.0 vs 21.0 m high) | -1497, 306 / -1181, -969 | [10-ba-G](10-ba-G.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 174 | STATIC | building-building | Central Parking Garage | Terminal Two AirTrain Station | building x building | 20.27 / 824.0 | 0.00 | – | walls interpenetrate: 64 % of Terminal Two AirTrain Station lies inside Central Parking Garage (13.0 vs 22.0 m | -806, 230 / -605, -580 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| 175 | STATIC | building-building | Central Parking Garage | Terminal Three AirTrain Station | building x building | 14.05 / 722.0 | 0.00 | – | walls interpenetrate: 62 % of Terminal Three AirTrain Station lies inside Central Parking Garage (13.0 vs 22.0 | -986, 141 / -806, -585 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 176 | STATIC | building-building | Terminal 1 Air Train Station | Terminal One AirTrain Station | building x building | 13.14 / 684.4 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 684 m2: coplanar faces z-fight - probably one station listed twi | -902, 400 / -611, -775 | [20-itb-tower](20-itb-tower.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 177 | STATIC | building-building | Terminal complex ramp level | International Terminal A Air Train Station | building x building | 13.09 / 895.1 | 0.00 | – | walls interpenetrate: 100 % of International Terminal A Air Train Station lies inside Terminal complex ramp le | -1172, 466 / -819, -959 | [10-ba-B](10-ba-B.png), [20-itb-tower](20-itb-tower.png) |
| 178 | STATIC | building-building | Terminal complex ramp level | International Terminal G Air Train Station | building x building | 13.09 / 895.1 | 0.00 | – | walls interpenetrate: 100 % of International Terminal G Air Train Station lies inside Terminal complex ramp le | -1240, 240 / -985, -791 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| 179 | STATIC | building-building | Terminal 2 Air Train Station | Terminal Two AirTrain Station | building x building | 12.46 / 702.9 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 703 m2: coplanar faces z-fight - probably one station listed twi | -808, 227 / -609, -578 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| 180 | STATIC | building-building | Terminal 3 Air Train Station | Terminal Three AirTrain Station | building x building | 11.02 / 688.1 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 688 m2: coplanar faces z-fight - probably one station listed twi | -984, 140 / -804, -583 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 181 | STATIC | building-building | Terminal complex ramp level | Terminal Two AirTrain Station | building x building | 8.82 / 206.6 | 0.00 | – | walls interpenetrate: 16 % of Terminal Two AirTrain Station lies inside Terminal complex ramp level (13.0 vs 5 | -755, 212 / -569, -540 | [10-ba-D](10-ba-D.png), [20-itb-tower](20-itb-tower.png) |
| 182 | STATIC | building-building | Terminal 2 | Terminal Two AirTrain Station | building x building | 8.82 / 206.6 | 0.00 | – | walls interpenetrate: 16 % of Terminal Two AirTrain Station lies inside Terminal 2 (13.0 vs 19.6 m high) | -755, 212 / -569, -540 | [10-ba-D](10-ba-D.png), [20-itb-tower](20-itb-tower.png) |
| 183 | STATIC | building-building | Terminal complex ramp level | International Terminal (A) AirTrain Station | building x building | 8.79 / 1185.1 | 0.00 | – | walls interpenetrate: 100 % of International Terminal (A) AirTrain Station lies inside Terminal complex ramp l | -1252, 242 / -994, -798 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| 184 | STATIC | building-building | International Terminal (A) AirTrain Station | International Terminal G Air Train Station | building x building | 8.78 / 598.3 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 598 m2: coplanar faces z-fight - probably one station listed twi | -1241, 238 / -986, -790 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| 185 | STATIC | building-building | International Terminal | International Terminal (G) AirTrain Station | building x building | 8.72 / 1076.0 | 0.00 | – | walls interpenetrate: 90 % of International Terminal (G) AirTrain Station lies inside International Terminal ( | -1172, 466 / -819, -959 | [10-ba-B](10-ba-B.png), [20-itb-tower](20-itb-tower.png) |
| 186 | STATIC | building-building | Terminal complex ramp level | International Terminal (G) AirTrain Station | building x building | 8.72 / 1075.9 | 0.00 | – | walls interpenetrate: 90 % of International Terminal (G) AirTrain Station lies inside Terminal complex ramp le | -1172, 466 / -819, -959 | [10-ba-B](10-ba-B.png), [20-itb-tower](20-itb-tower.png) |
| 187 | STATIC | building-building | International Terminal (G) AirTrain Station | International Terminal A Air Train Station | building x building | 8.71 / 594.0 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 594 m2: coplanar faces z-fight - probably one station listed twi | -1172, 466 / -819, -959 | [10-ba-B](10-ba-B.png), [20-itb-tower](20-itb-tower.png) |
| 188 | STATIC | building-building | Terminal 3 | Terminal Three AirTrain Station | building x building | 8.19 / 136.8 | 0.00 | – | walls interpenetrate: 12 % of Terminal Three AirTrain Station lies inside Terminal 3 (13.0 vs 21.6 m high) | -1001, 97 / -840, -553 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 189 | STATIC | building-building | Terminal complex ramp level | Terminal Three AirTrain Station | building x building | 8.19 / 134.2 | 0.00 | – | walls interpenetrate: 12 % of Terminal Three AirTrain Station lies inside Terminal complex ramp level (13.0 vs | -1001, 97 / -840, -553 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 190 | STATIC | building-building | West Field Road AirTrain Station (Inbound) | Westfield Road AirTrain Station (Inbound) | building x building | 7.36 / 462.1 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 462 m2: coplanar faces z-fight - probably one station listed twi | -2130, -319 / -2032, -712 | [40-apron-1-north-west](40-apron-1-north-west.png), [00-overview](00-overview.png) |
| 191 | STATIC | building-building | Harvey Milk Terminal 1 | Terminal One AirTrain Station | building x building | 2.67 / 11.5 | 0.00 | – | walls interpenetrate: 1 % of Terminal One AirTrain Station lies inside Harvey Milk Terminal 1 (13.0 vs 20.6 m  | -891, 453 / -577, -817 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| 192 | LIVE | gse-check-mismatch | catering mesh | gates.js placeVehicles() check rectangle | catering x code | 2.43 / 1.2 | – | – | 1.2 m2 of the catering mesh lies outside the 8.2 x 2.4 m rectangle the collision check uses | -976, 961 / -414, -1306 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 193 | LIVE | gse-check-mismatch | fuel mesh | gates.js placeVehicles() check rectangle | fuel x code | 2.41 / 1.7 | – | – | 1.7 m2 of the fuel mesh lies outside the 8.2 x 2.5 m rectangle the collision check uses | -844, 859 / -345, -1154 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 194 | LIVE | gse-check-mismatch | fuel mesh | gates.js placeVehicles() check rectangle | fuel x code | 2.41 / 1.7 | – | – | 1.7 m2 of the fuel mesh lies outside the 8.2 x 2.5 m rectangle the collision check uses | -1023, 950 / -462, -1318 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 195 | STATIC | building-building | Terminal complex ramp level | Terminal One AirTrain Station | building x building | 2.33 / 8.0 | 0.00 | – | walls interpenetrate: 1 % of Terminal One AirTrain Station lies inside Terminal complex ramp level (13.0 vs 5. | -892, 454 / -577, -817 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| 196 | STATIC | building-building | Long Term Parking AirTrain Station | Long-Term Parking Garage 2 | building x building | 1.17 / 5.7 | 0.00 | – | walls interpenetrate: 0 % of Long Term Parking AirTrain Station lies inside Long-Term Parking Garage 2 (13.0 v | -2236, -1834 / -2833, 577 | [00-overview](00-overview.png) |
| 197 | DOCK-MAX,DOCK-REF | bridge-bridge | G2 bridge G2 (L1) | G2 bridge G2 (L2) | stair x pedestal; stair x rotunda | 0.74 / 0.7 | 0.00 | 0.13 | passes 0.13 m above/below (plan overlap 0.7 m2) | -1317, 113 / -1112, -715 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 198 | DOCK-MAX,DOCK-REF | bridge-bridge | F17 bridge F17 (L1) | F17 bridge F18 (L2) | stair x pca-unit; stair x tunnel1; stair x tunnel2 | 0.52 / 0.2 | 0.00 | 0.23 | passes 0.23 m above/below (plan overlap 0.2 m2) | -1287, -200 / -1231, -424 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 199 | ENVELOPE | envelope-rest-bridge | A3 bridge A3 (L1) (a332, a333, a359, a35k, b772, b77w ...) | A3 class envelope | bellows x envelope-type | 0.09 / 0.1 | 0.00 | -2.23 | touching (9 cm) | -1220, 559 / -818, -1064 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 200 | ENVELOPE | envelope-rest-bridge | G6 bridge G6 (L1) (a332, a333, a359, a35k, b772, b77w ...) | G6 class envelope | bellows x envelope-type | 0.09 / 0.1 | 0.00 | -2.23 | touching (9 cm) | -1452, 45 / -1263, -717 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 201 | ENVELOPE | envelope-rest-bridge | G2 bridge G2 (L1) (a332, a333, a359, a35k, md11) | G2 class envelope | bellows x envelope-type | 0.09 / 0.0 | 0.00 | -2.23 | touching (9 cm) | -1327, 112 / -1121, -718 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 202 | LIVE | bridge-aircraft | AAL2722 A21N at B25 (gate) | B25 bridge B24 (L1) | aircraft x tunnel2 | 0.07 / 0.0 | 0.00 | 0.16 | passes 0.16 m above/below (plan overlap 0.0 m2) | -976, 946 / -422, -1292 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 203 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-building | F17 bridge F17 (L1) | Boarding Area F | rotunda x building | 0.06 / 0.0 | 0.00 | -8.70 | touching (6 cm) | -1281, -217 / -1234, -407 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 204 | DOCK-MAX,DOCK-REF | bridge-bridge | A3 bridge A3 (L1) | A3 bridge A4 (L2) | stair x tunnel1 | 0.05 / 0.0 | 0.00 | -0.56 | touching (5 cm) | -1219, 549 / -822, -1054 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 205 | DOCK-MAX,DOCK-REF,LIVE,REST | bridge-building | F17 bridge F17 (L1) | Terminal complex ramp level | rotunda x building | 0.04 / 0.0 | 0.00 | 0.10 | passes 0.10 m above/below (plan overlap 0.0 m2) | -1281, -217 / -1234, -406 | [10-ba-F](10-ba-F.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 206 | LIVE | marker-no-body | GroundPhysics | ACA758 type ? (gate) | physics x aircraft | – / – | – | – | drawn as a marker: no model/TYPES entry, so it is not a solid body (ground.js skips it) | -506, 30 / -434, -263 | [10-ba-D](10-ba-D.png), [40-apron-1-north-west](40-apron-1-north-west.png) |
| 375 | LIVE | gse-aircraft | AAL2722 A21N at B25 (gate) | catering (B25) | aircraft x catering | – / – | 0.22 | – | only 0.22 m apart | -980, 958 / -419, -1305 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 376 | ENVELOPE | envelope-building | A3 class envelope (b762) | International Terminal | envelope-type x building | – / – | 2.92 | – | only 2.92 m apart | -1228, 531 / -838, -1043 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 377 | ENVELOPE | envelope-building | Terminal complex ramp level (b762) | A3 class envelope | building x envelope-type | – / – | 2.93 | – | only 2.93 m apart | -1228, 531 / -838, -1043 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |

### Bridge kinematics (168)

| # | kind | bridge | note |
|---|---|---|---|
| 207 | tunnel-stretch | G10 bridge G14 (L1) | tunnel sections 3.5/3.2/2.9 m parked -> 4.0/3.7/3.1 m docked to b77w: sections scale with the extension instead of telescoping |
| 208 | tunnel-stretch | G10 bridge G10 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 9.2/8.3/7.0 m docked to b77w: sections scale with the extension instead of telescoping |
| 209 | tunnel-stretch | G9 bridge G9 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.0/8.2/6.9 m docked to b77w: sections scale with the extension instead of telescoping |
| 210 | tunnel-stretch | G9 bridge G9 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 9.1/8.2/6.9 m docked to b77w: sections scale with the extension instead of telescoping |
| 211 | tunnel-stretch | G6 bridge G6 (L2) | tunnel sections 3.5/3.2/2.9 m parked -> 3.9/3.6/3.0 m docked to b77w: sections scale with the extension instead of telescoping |
| 212 | tunnel-stretch | G5 bridge G5 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 5.9/5.4/4.6 m docked to b77w: sections scale with the extension instead of telescoping |
| 213 | tunnel-stretch | G5 bridge G5 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 7.0/6.4/5.4 m docked to b77w: sections scale with the extension instead of telescoping |
| 214 | tunnel-stretch | G1 bridge G1 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 7.3/6.6/5.6 m docked to b78x: sections scale with the extension instead of telescoping |
| 215 | tunnel-stretch | G1 bridge G1 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 7.9/7.1/6.0 m docked to b78x: sections scale with the extension instead of telescoping |
| 216 | tunnel-stretch | G7 bridge G7 (L2) | tunnel sections 2.7/2.8/2.9 m parked -> 3.9/3.6/3.0 m docked to b77w: sections scale with the extension instead of telescoping |
| 217 | tunnel-stretch | G4 bridge G4 (L1) | tunnel sections 3.8/3.4/3.0 m parked -> 4.2/3.8/3.2 m docked to b77w: sections scale with the extension instead of telescoping |
| 218 | tunnel-stretch | G4 bridge G4 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 5.7/5.1/4.3 m docked to b77w: sections scale with the extension instead of telescoping |
| 219 | tunnel-stretch | G3 bridge G3 (L2) | tunnel sections 2.9/2.8/2.9 m parked -> 3.9/3.6/3.1 m docked to b77w: sections scale with the extension instead of telescoping |
| 220 | tunnel-stretch | G12 bridge G12 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.0/9.0/7.6 m docked to b77w: sections scale with the extension instead of telescoping |
| 221 | tunnel-stretch | G12 bridge G12 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 10.0/9.1/7.7 m docked to b77w: sections scale with the extension instead of telescoping |
| 222 | tunnel-stretch | G8 bridge G8 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.6/9.6/8.1 m docked to b78x: sections scale with the extension instead of telescoping |
| 223 | tunnel-stretch | G8 bridge G8 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 10.6/9.6/8.1 m docked to b78x: sections scale with the extension instead of telescoping |
| 224 | tunnel-stretch | A3 bridge A4 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 5.9/5.3/4.5 m docked to b77w: sections scale with the extension instead of telescoping |
| 225 | tunnel-stretch | A5 bridge A5 (L2) | tunnel sections 2.7/2.8/2.9 m parked -> 3.3/3.0/2.9 m docked to b77w: sections scale with the extension instead of telescoping |
| 226 | tunnel-stretch | A9 bridge A9 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.0/8.2/6.9 m docked to b77w: sections scale with the extension instead of telescoping |
| 227 | tunnel-stretch | A9 bridge A9 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 9.1/8.2/7.0 m docked to b77w: sections scale with the extension instead of telescoping |
| 228 | tunnel-stretch | A10 bridge A10 (L1) | tunnel sections 3.6/3.3/2.9 m parked -> 5.2/4.7/4.0 m docked to b77w: sections scale with the extension instead of telescoping |
| 229 | tunnel-stretch | A10 bridge A10 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 6.9/6.2/5.3 m docked to b77w: sections scale with the extension instead of telescoping |
| 230 | tunnel-stretch | A1 bridge A1 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.4/8.6/7.3 m docked to b39m: sections scale with the extension instead of telescoping |
| 231 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 25.3 m = 1:9.9 |
| 232 | tunnel-stretch | A2 bridge A2 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.1/8.2/7.0 m docked to b77w: sections scale with the extension instead of telescoping |
| 233 | tunnel-stretch | A2 bridge A2 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 9.2/8.3/7.0 m docked to b77w: sections scale with the extension instead of telescoping |
| 234 | tunnel-stretch | A6 bridge A7 (L1) | tunnel sections 4.8/4.3/3.7 m parked -> 6.4/5.8/4.9 m docked to b77w: sections scale with the extension instead of telescoping |
| 235 | tunnel-stretch | A6 bridge A7 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 8.1/7.3/6.2 m docked to b77w: sections scale with the extension instead of telescoping |
| 236 | tunnel-stretch | A8 bridge A8 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.1/8.2/6.9 m docked to b77w: sections scale with the extension instead of telescoping |
| 237 | tunnel-stretch | A8 bridge A8 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 9.1/8.3/7.0 m docked to b77w: sections scale with the extension instead of telescoping |
| 238 | tunnel-stretch | A11 bridge A11 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 5.6/5.1/4.3 m docked to b77w: sections scale with the extension instead of telescoping |
| 239 | tunnel-stretch | A11 bridge A13 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 9.4/8.5/7.2 m docked to b77w: sections scale with the extension instead of telescoping |
| 240 | tunnel-stretch | A15 bridge A14 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 11.0/10.0/8.5 m docked to b39m: sections scale with the extension instead of telescoping |
| 241 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 26.9 m = 1:10.5 |
| 242 | tunnel-stretch | C3 bridge C3 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.1/9.2/7.8 m docked to b39m: sections scale with the extension instead of telescoping |
| 243 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 26.1 m = 1:10.2 |
| 244 | tunnel-stretch | C5 bridge C5 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.7/9.7/8.2 m docked to b752: sections scale with the extension instead of telescoping |
| 245 | tunnel-stretch | C7 bridge C7 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.6/8.8/7.4 m docked to b752: sections scale with the extension instead of telescoping |
| 246 | tunnel-stretch | C11 bridge C11 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.6/8.8/7.5 m docked to b39m: sections scale with the extension instead of telescoping |
| 247 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 24.8 m = 1:9.7 |
| 248 | tunnel-stretch | C4 bridge C4 (L1) | tunnel sections 4.6/4.2/3.6 m parked -> 6.4/5.9/5.1 m docked to b39m: sections scale with the extension instead of telescoping |
| 249 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 16.2 m = 1:6.3 |
| 250 | tunnel-stretch | C6 bridge C6 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.6/8.7/7.4 m docked to b39m: sections scale with the extension instead of telescoping |
| 251 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 23.6 m = 1:9.2 |
| 252 | tunnel-stretch | C8 bridge C8 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.6/9.7/8.2 m docked to b39m: sections scale with the extension instead of telescoping |
| 253 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 26.8 m = 1:10.4 |
| 254 | tunnel-stretch | C10 bridge C10 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 6.9/6.3/5.4 m docked to b39m: sections scale with the extension instead of telescoping |
| 255 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 17.5 m = 1:6.8 |
| 256 | tunnel-stretch | B9 bridge B9 (L1) | tunnel sections 3.0/2.8/2.9 m parked -> 4.5/4.2/3.7 m docked to b39m: sections scale with the extension instead of telescoping |
| 257 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 11.4 m = 1:4.5 |
| 258 | tunnel-stretch | B12 bridge B12 (L1) | tunnel sections 3.0/2.8/2.9 m parked -> 4.5/4.2/3.6 m docked to b39m: sections scale with the extension instead of telescoping |
| 259 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 11.4 m = 1:4.4 |
| 260 | tunnel-stretch | B13 bridge B13 (L1) | tunnel sections 3.0/2.8/2.9 m parked -> 4.5/4.2/3.7 m docked to b39m: sections scale with the extension instead of telescoping |
| 261 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 11.5 m = 1:4.5 |
| 262 | tunnel-stretch | B14 bridge B14 (L1) | tunnel sections 3.0/2.8/2.9 m parked -> 4.5/4.1/3.6 m docked to b39m: sections scale with the extension instead of telescoping |
| 263 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 11.4 m = 1:4.5 |
| 264 | tunnel-stretch | B17 bridge B17 (L1) | tunnel sections 3.2/2.9/2.9 m parked -> 4.6/4.2/3.7 m docked to b39m: sections scale with the extension instead of telescoping |
| 265 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 11.8 m = 1:4.6 |
| 266 | tunnel-stretch | B18 bridge B18 (L1) | tunnel sections 3.0/2.8/2.9 m parked -> 4.5/4.1/3.6 m docked to b39m: sections scale with the extension instead of telescoping |
| 267 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 11.4 m = 1:4.4 |
| 268 | tunnel-stretch | B21 bridge B21 (L1) | tunnel sections 3.0/2.8/2.9 m parked -> 4.4/4.1/3.6 m docked to b39m: sections scale with the extension instead of telescoping |
| 269 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 11.4 m = 1:4.4 |
| 270 | tunnel-stretch | B10 bridge B10 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.9/9.0/7.7 m docked to e190: sections scale with the extension instead of telescoping |
| 271 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to e190: floor 5.4 m at the rotunda -> 2.5 m at the cab over 25.8 m = 1:8.9 |
| 272 | tunnel-stretch | B11 bridge B11 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.3/8.5/7.2 m docked to e190: sections scale with the extension instead of telescoping |
| 273 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to e190: floor 5.4 m at the rotunda -> 2.5 m at the cab over 25.0 m = 1:8.6 |
| 274 | tunnel-stretch | B15 bridge B15 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 7.3/6.7/5.7 m docked to e190: sections scale with the extension instead of telescoping |
| 275 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to e190: floor 5.4 m at the rotunda -> 2.5 m at the cab over 19.7 m = 1:6.8 |
| 276 | tunnel-stretch | B16 bridge B16 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.4/8.5/7.3 m docked to e190: sections scale with the extension instead of telescoping |
| 277 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to e190: floor 5.4 m at the rotunda -> 2.5 m at the cab over 25.1 m = 1:8.6 |
| 278 | tunnel-stretch | B19 bridge B20 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 11.8/10.7/9.1 m docked to e190: sections scale with the extension instead of telescoping |
| 279 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to e190: floor 5.4 m at the rotunda -> 2.5 m at the cab over 28.1 m = 1:9.7 |
| 280 | tunnel-stretch | B27 bridge B27 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 6.0/5.5/4.7 m docked to b752: sections scale with the extension instead of telescoping |
| 281 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b752: floor 5.4 m at the rotunda -> 3.7 m at the cab over 16.2 m = 1:9.5 |
| 282 | tunnel-stretch | B26 bridge B26 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.3/8.5/7.2 m docked to b752: sections scale with the extension instead of telescoping |
| 283 | tunnel-stretch | B23 bridge B22 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 8.5/7.7/6.6 m docked to b39m: sections scale with the extension instead of telescoping |
| 284 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 20.0 m = 1:7.8 |
| 285 | tunnel-stretch | B25 bridge B24 (L1) | tunnel sections 4.0/3.6/3.1 m parked -> 6.7/6.1/5.2 m docked to b39m: sections scale with the extension instead of telescoping |
| 286 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b39m: floor 5.4 m at the rotunda -> 2.8 m at the cab over 15.7 m = 1:6.1 |
| ... | | | 88 more in out/draw/audit.json |

## Moving traffic (live mode, harness mock relay)

`jobs/trace2d.mjs` ran the app in live mode for 215 s (40 samples) with the harness's mock relay (recorded snapshot, aircraft moved in straight lines along their track, taxiing aircraft at 0.35 x speed); `trace_audit.py` checked every sampled frame. The mock's straight-line motion takes taxiing aircraft off the pavement and through buildings by construction, so only the aircraft-aircraft rows test GroundPhysics.

Pairs in conflict: **4 aircraft-building**, **3 gear-off-pavement**.

| kind | object A | object B | frames in conflict | first - last (s) | worst depth (m) | state |
|---|---|---|---|---|---|---|
| aircraft-building | UAL1116 B753 | Boarding Area E | 40 / 40 | 0 - 215 | 24.4 | parked (4.2 m/s) |
| aircraft-building | UAL1116 B753 | Terminal complex ramp level | 40 / 40 | 0 - 215 | 24.1 | parked (4.2 m/s) |
| aircraft-building | ASA528 B737 | Terminal complex ramp level | 40 / 40 | 0 - 215 | 4.2 | parked (3.5 m/s) |
| aircraft-building | ASA528 B737 | Boarding Area B | 40 / 40 | 0 - 215 | 4.2 | parked (3.5 m/s) |
| gear-off-pavement | SKW3490 E75L | paved raster | 40 / 40 | 0 - 215 | 0.0 | parked (9.5 m/s) |
| gear-off-pavement | UAL2649 A319 | paved raster | 40 / 40 | 0 - 215 | 0.0 | parked (6.3 m/s) |
| gear-off-pavement | JBU578 A321 | paved raster | 40 / 40 | 0 - 215 | 0.0 | parked (6.3 m/s) |

## Sheet index

Vector sheets (no imagery) are in this folder; the same sheets over the imagery (`*_overlay-google.*`, and `*_overlay-naip.*` when NAIP is present) are written to `out/draw/sheets/` only (Google pixels must not be committed).

| sheet | scale | paper | features (flagged) | conflicts on sheet |
|---|---|---|---|---|
| [00-overview](00-overview.png) ([svg](00-overview.svg)) | 1:7500 | A1 | 791 (267) | CLEARANCE 50, COLLISION 114, OFF-PAVEMENT 4, WARNING 209 |
| [10-ba-A](10-ba-A.png) ([svg](10-ba-A.svg)) | 1:1500 | A3 | 43 (23) | CLEARANCE 19, COLLISION 18, WARNING 24 |
| [10-ba-B](10-ba-B.png) ([svg](10-ba-B.svg)) | 1:1500 | A2 | 90 (38) | CLEARANCE 21, COLLISION 34, WARNING 72 |
| [10-ba-C](10-ba-C.png) ([svg](10-ba-C.svg)) | 1:1500 | A3 | 55 (29) | CLEARANCE 2, COLLISION 9, WARNING 30 |
| [10-ba-D](10-ba-D.png) ([svg](10-ba-D.svg)) | 1:1500 | A3 | 66 (23) | COLLISION 9, WARNING 37 |
| [10-ba-E](10-ba-E.png) ([svg](10-ba-E.svg)) | 1:1500 | A3 | 57 (30) | CLEARANCE 2, COLLISION 15, WARNING 35 |
| [10-ba-F](10-ba-F.png) ([svg](10-ba-F.svg)) | 1:1500 | A2 | 107 (49) | CLEARANCE 19, COLLISION 50, WARNING 58 |
| [10-ba-G](10-ba-G.png) ([svg](10-ba-G.svg)) | 1:1500 | A2 | 68 (41) | CLEARANCE 19, COLLISION 33, WARNING 38 |
| [20-itb-tower](20-itb-tower.png) ([svg](20-itb-tower.svg)) | 1:1500 | A2 | 102 (71) | CLEARANCE 18, COLLISION 25, WARNING 61 |
| [30-rwy-10L](30-rwy-10L.png) ([svg](30-rwy-10L.svg)) | 1:2000 | A2 | 108 (31) | – |
| [30-rwy-10R](30-rwy-10R.png) ([svg](30-rwy-10R.svg)) | 1:2000 | A2 | 117 (32) | – |
| [30-rwy-19L](30-rwy-19L.png) ([svg](30-rwy-19L.svg)) | 1:2000 | A2 | 47 (10) | – |
| [30-rwy-19R](30-rwy-19R.png) ([svg](30-rwy-19R.svg)) | 1:2000 | A2 | 61 (18) | – |
| [30-rwy-1L](30-rwy-1L.png) ([svg](30-rwy-1L.svg)) | 1:2000 | A1 | 188 (68) | CLEARANCE 25, COLLISION 37, WARNING 72 |
| [30-rwy-1R](30-rwy-1R.png) ([svg](30-rwy-1R.svg)) | 1:2000 | A1 | 129 (41) | CLEARANCE 8, COLLISION 19, WARNING 36 |
| [30-rwy-28L](30-rwy-28L.png) ([svg](30-rwy-28L.svg)) | 1:2000 | A2 | 41 (14) | – |
| [30-rwy-28R](30-rwy-28R.png) ([svg](30-rwy-28R.svg)) | 1:2000 | A2 | 42 (15) | – |
| [40-apron-1-north-west](40-apron-1-north-west.png) ([svg](40-apron-1-north-west.svg)) | 1:4000 | A1 | 460 (173) | CLEARANCE 25, COLLISION 78, OFF-PAVEMENT 1, WARNING 147 |
| [40-apron-2-north-middle](40-apron-2-north-middle.png) ([svg](40-apron-2-north-middle.svg)) | 1:4000 | A1 | 485 (146) | CLEARANCE 23, COLLISION 72, OFF-PAVEMENT 1, WARNING 109 |
| [40-apron-3-south-middle](40-apron-3-south-middle.png) ([svg](40-apron-3-south-middle.svg)) | 1:3000 | A1 | 352 (147) | CLEARANCE 36, COLLISION 76, OFF-PAVEMENT 1, WARNING 161 |
| [40-apron-4-central-east](40-apron-4-central-east.png) ([svg](40-apron-4-central-east.svg)) | 1:2000 | A1 | 70 (22) | OFF-PAVEMENT 2 |

## Method, sources and limits

- **Extraction** (`jobs/extract2d.mjs`): loads `live.html?mode=snapshot` in the harness, stops the page timers, lets traffic + GroundPhysics run until every track is displayable, freezes the render loop, then reads window.SFO and calls the app's own builders with a recording geometry sink (every jet-bridge box/cylinder/tube from `gates.js bridgeGeo()` in its current, parked and docked pose; VDGS from `standGeo()`; markings from `markings.js`; signs from `signs.js`; EMAS from `world.js buildEMAS()`; buildings from `buildLiveBuildings()`; pavement from `paintAirportMapReal()` - the raster the physics uses). Module-private values (REF_TYPE, CLASS_MAX, STRUCT_H, ...) are read by re-importing the module source with an extra export. Replicated by hand (listed in scene2d.json meta.replicated): the runway paint layout (GLSL), standFits(), and the GSE check rectangles.
- **Aircraft**: live aircraft use the rendered model (.sfom, stretched and placed exactly as `aircraft.js` does) or the procedural TYPES body; per-cell min/max heights make the bridge/wing/engine checks 3-D. Class envelopes = union of every non-oversize type the stand accepts (both the procedural TYPES body and the rendered model). Gear contact points: TYPES nose/main gear (the gear the app draws).
- **Deviation measurement** (`measure.py`): profiles along the edge normal (+-10 m; +-25 m along the runway axis for runway ends/thresholds), gradient peaks (steps) with feature-level polarity consensus against shadows, width-matched ridges for paint; nearest strong candidate to the model. Automatic picks can lock onto the wrong edge (shadow, shoulder, paint): always read a number together with its overlay sheet.
- **Imagery**: the owner's Google Maps screenshots (19, 0.17-3.2 m/px, similarity registrations in tools/sat/work/reg.json). Building-edge numbers are not independent of the building data: the screenshots were registered by chamfer matching against the SFO Museum outlines. Runway ends were checked independently against FAA coordinates (tools/sat/faacheck.py). NAIP (independent georeference) is supported but was not available for this run.
- **Heights**: SFO Museum footprints have no heights; building heights are the app's values (sfo_buildings parts, STRUCT_H tables), bridge heights come from the geometry.
- **Not covered**: aircraft in the air; buildings in the imagery that the app does not build (cargo sheds, hangars other than the Super Bay) are not detected automatically - compare the overlay sheets; taxiway centrelines, lead-ins and most hold lines are not measurable on the available resolution.
