# SFO Live 3D — 2-D drawing set: deviations and physical conflicts

Generated 2026-09-25 20:07Z by `tools/drawing/run_all.sh` (report: `tools/drawing/report.py`).
Scene extracted from the running app (`jobs/extract2d.mjs`, live.html?mode=snapshot) at 2026-09-25T17:42:07Z, app served from a clean `git archive` of commit **`a8e0538`** (`a8e0538632d058bfa0c465ec8a27d11fd3d58c7d`, served from `out/draw_head/app_snapshot`, so edits made to the working tree during the run cannot enter the scene); HEAD at report time `a8e0538`. **World frame `ltp-nad83-2011`**; 86 input files hashed (inputs `1897ab1250dba186`, TYPES `0884580719571ac1`) - **all unchanged in the app source at report time**; quality tier `high`.

> **Not covered by this report: 37 of the 86 app files the scene loaded differ in the working tree now** (uncommitted work, or commits after `a8e0538`): data/brands.js, data/liveries/manifest.js, data/models/a319.sfom, data/models/a320.sfom, data/models/a321.sfom, data/models/a333.sfom, data/models/a359.sfom, data/models/a388.sfom, data/models/b738.sfom, data/models/b744.sfom, data/models/b748.sfom, data/models/b752.sfom, data/models/b763.sfom, data/models/b788.sfom, data/models/bcs1.sfom, data/models/bcs3.sfom .... The drawings and numbers describe commit `a8e0538`; re-run `tools/drawing/run_all.sh` once that work is committed.
Everything below is drawn/measured from the objects the 3-D app actually places (window.SFO world / gateSys / traffic / physics, and the app's own builder functions), not re-derived from the data files.

## Headline

- **Imagery `naip`** (NAIP (2 image(s)); public, primary): 1133 features sampled, **637 measured** (+72 jet-bridge rotundas found), **398 with median offset > 1.0 m**; 513 with p90 > 1.0 m.
- **Imagery `google`** (Google Maps screenshots (owner, reference only, re-registered to NAIP); reference only, not redistributable): 1133 features sampled, **487 measured** (+77 jet-bridge rotundas found), **390 with median offset > 1.0 m**; 479 with p90 > 1.0 m.
  - `naip` by class (flagged / measured): runway-edge-stripe 0/8; runway-end 0/4; runway-threshold 0/8; runway-threshold-bar 8/8; emas-bed 1/4; approach-light-station 0/2; approach-light-crossbar 0/2; approach-light-catwalk 0/2; taxiway-edge 84/162; extra-pavement 231/259; apron-edge 2/2; building 38/39; bridge-walkway 34/47; hold-line 0/90.
  - `google` by class (flagged / measured): runway-edge-stripe 1/4; runway-end 4/4; runway-threshold 0/2; runway-threshold-bar 5/6; emas-bed 3/4; approach-light-station 2/2; approach-light-crossbar 2/2; taxiway-edge 97/143; extra-pavement 200/238; apron-edge 2/2; building 32/33; bridge-walkway 42/47.
  - How far each class can be trusted is in the self-test section; building and pavement-edge classes recover a known shift less reliably than runway markings, so read their numbers with the overlay sheets.
- **Physical audit**: 445 distinct findings (one per pair of objects, merged across scenarios, worst severity kept): **59 COLLISION**, **4 OFF-PAVEMENT**, **27 OBSTRUCTION**, **42 CLEARANCE**, **313 WARNING**.

Per scenario (each scenario counted at its own severity - a pair that collides in DOCK-MAX but only warns in LIVE counts as a LIVE warning):

| scenario | COLLISION | OFF-PAVEMENT | OBSTRUCTION | CLEARANCE | WARNING |
|---|---|---|---|---|---|
| DOCK-MAX (every stand with its largest type, bridges docked) | 28 | 0 | 0 | 5 | 14 |
| DOCK-REF (every stand with its reference type, bridges docked) | 33 | 0 | 0 | 4 | 13 |
| ENVELOPE (class envelopes (all accepted types) vs neighbours / parked bridges / buildings) | 19 | 0 | 0 | 22 | 1 |
| KINEMATICS (bridge tunnel geometry rest vs docked) | 0 | 0 | 0 | 0 | 189 |
| LIVE (snapshot as displayed) | 32 | 4 | 0 | 0 | 16 |
| OVERSIZE (747 / A380 on EL-F stands vs blocking rule) | 3 | 0 | 0 | 11 | 0 |
| REST (all stands empty, bridges parked) | 31 | 0 | 0 | 0 | 13 |
| STATIC (buildings vs buildings; piers / signs vs movement surfaces) | 0 | 0 | 27 | 0 | 104 |

## Key findings (worst first)

- **19 COLLISION x envelope-rest-bridge** - parked (retracted) jet bridge inside the arrival envelope of a stand: an arriving aircraft of an accepted type would hit it (ENVELOPE 19).
- **17 COLLISION x bridge-bridge** - two bridges intersecting in 3-D (DOCK-MAX 16, DOCK-REF 16, LIVE 17, REST 17).
- **9 COLLISION x bridge-building** - bridge part inside a building / elevated walkway (DOCK-MAX 9, DOCK-REF 9, LIVE 9, REST 9).
- **6 COLLISION x bridge-aircraft** - docked bridge part (tunnel / rotunda / stair / drive column) intersecting an aircraft in 3-D (DOCK-REF 5, LIVE 1).
- **3 COLLISION x bridge-mast** - bridge intersecting a floodlight mast (DOCK-MAX 3, DOCK-REF 3, LIVE 3, REST 3).
- **2 COLLISION x oversize-rest-bridge** - oversize aircraft hits a neighbour's parked bridge (OVERSIZE 2).
- **2 COLLISION x bridge-vdgs** - VDGS / stand-sign box inside a bridge tunnel, cab or stair (LIVE 2, REST 2).
- **1 COLLISION x oversize-not-blocked** - oversize aircraft (747/A380) reaches a neighbour the blocking rule leaves available (OVERSIZE 1).
- **2 OFF-PAVEMENT x gear-off-pavement** - rendered gear on unpaved ground (visual view: rendered paved raster) (LIVE 2).
- **2 OFF-PAVEMENT x gear-off-physics-pavement** - GroundPhysics gear point neither on the paved raster nor on the OSM taxi net (physics view) (LIVE 2).
- **25 OBSTRUCTION x sign-on-movement-surface** - airfield sign standing on a runway / taxiway / blast pad / EMAS surface (STATIC 25).
- **2 OBSTRUCTION x pier-on-movement-surface** - approach-light pier or post standing on a runway / displaced-threshold area / blast pad / EMAS bed / taxiway (STATIC 2).
- LIVE aircraft involved in a collision / off-pavement finding (3): SKW5212 CRJ2 at F10 (gate) (phase gate, gs 0.0 m/s, stale, at F10); UAL643 B38M (parked) (phase parked, gs 0.0 m/s, stale); SKW6001 E75L (parked) (phase parked, gs 0.0 m/s, stale).
- **Bridge kinematics**: 122 bridges whose three tunnel sections change length between parked and docked (they scale instead of telescoping); 67 docked tunnels steeper than 1:12.
- **25 overlapping building footprints** that are both extruded (coplanar roofs that z-fight, or walls that cut through each other), among them 7 stations listed twice under two names: West Field Road AirTrain Station (Outbound) / Westfield Road AirTrain Station (Outbound)g; Terminal 1 Air Train Station / Terminal One AirTrain Station; Terminal 2 Air Train Station / Terminal Two AirTrain Station; Terminal 3 Air Train Station / Terminal Three AirTrain Station; International Terminal (G) AirTrain Station / International Terminal A Air Train Station; International Terminal (A) AirTrain Station / International Terminal G Air Train Station; West Field Road AirTrain Station (Inbound) / Westfield Road AirTrain Station (Inbound).
- 79 signs stand more than 1 m inside the paved raster that GroundPhysics treats as legal aircraft ground (deepest 20.4 m) - GroundPhysics does not know about signs, so a relocated aircraft can end up on one (WARNING).
- 1 aircraft on the ground drawn as a marker (no TYPES entry) - GroundPhysics treats it as no body at all.
- The OSM taxi-net pavement test the physics view uses is re-implemented from the exported net; it agrees with the page's own `TaxiNet.paved` at 100.00 % of 20000 random points.

## Runway markings and ends measured on `naip`

Along-axis numbers in metres from the threshold line (+ = landing side). `stripe start`: offset of the imaged start of the threshold-stripe block from the model's 6.1 m (stripe-start rule, module doc of measure.py). `threshold bar`: imaged centre of the 10 ft bar vs the model (`js/shaders/ground.js` endMarkings() draws a bar only at displaced thresholds, centred 1.525 m on the approach side).

| end | stripe start offset (n) | imaged bar centre | model bar centre | bar verdict | pavement end offset | EMAS bed median |
|---|---|---|---|---|---|---|
| 10L | 0.85 (16/16) | 0.90 (10/10) | none | **bar imaged, model draws none** | 0.90 | – |
| 28R | -0.10 (16/16) | 1.67 (10/10) | -1.52 | **wrong side of the threshold** | -0.40 | – |
| 10R | 0.50 (16/16) | 1.30 (10/10) | none | **bar imaged, model draws none** | 0.50 | – |
| 28L | -0.10 (16/16) | 1.87 (10/10) | -1.52 | **wrong side of the threshold** | -0.60 | – |
| 1L | -0.00 (16/16) | 1.72 (10/10) | -1.52 | **wrong side of the threshold** | (EMAS end) | 0.20 |
| 19R | -0.10 (16/16) | 1.50 (10/10) | none | **bar imaged, model draws none** | (EMAS end) | 1.20 |
| 1R | -0.10 (16/16) | 1.77 (10/10) | -1.52 | **wrong side of the threshold** | (EMAS end) | 0.10 |
| 19L | 0.20 (16/16) | 1.50 (10/10) | none | **bar imaged, model draws none** | (EMAS end) | 0.20 |

The EMAS "pavement end" at 1L/1R/19L/19R is not a visible edge (the 35 ft setback is paved); those ends are checked by the EMAS bed outline.

Approach-light structures over open water (`js/anim/lights.js`; at 28L/28R the structure is `js/geo.js` APPROACH_STRUCTURES, itself measured on NAIP 2024 by `tools/imagery/als_naip.py` - on NAIP these rows check the app's implementation of those measurements, on Google they are an independent image). `stations`: along-axis offset of each imaged station - the strongest bar of either polarity within 0.55 x the station spacing, i.e. the structure or its shadow on the bay (<= ~2.5 m apart); a station next to an equipment hut or platform can lock onto the hut (offsets of ~5-10 m there). `catwalk`: lateral offset of the imaged deck midway between stations from the modelled catwalk line. Crossbar ends are listed below the table.

| system | stations measured | station along-axis offset median / bias (m) | catwalk lateral offset median / bias (spans measured) | crossbar ends: median abs offset (measured) |
|---|---|---|---|---|
| RWY 28L MALSR approach-light stations over water (19, 213-762 m from the threshold) | 19/19 | 0.20 / -0.20 | 0.95 / -0.95 (10/18) | 0.35 (4/4) |
| RWY 28R ALSF2 approach-light stations over water (19, 211-760 m from the threshold) | 19/19 | 0.60 / 0.30 | 0.75 / -0.75 (8/18) | 0.80 (14/14) |

Crossbar ends (m along the runway frame's right from the axis; offset + = the imaged bar reaches further out than the model):

| end | crossbar | model end | imaged end | offset | note |
|---|---|---|---|---|---|
| 28L | 1000 ft -R | -12.90 | -12.40 | -0.50 |  |
| 28L | 1000 ft +R | +12.70 | 12.70 | 0.00 |  |
| 28L | 1300 ft -R | -16.30 | -16.00 | -0.30 |  |
| 28L | 1300 ft +R | +16.10 | 15.70 | -0.40 |  |
| 28R | 692 ft -R | -16.90 | -16.30 | -0.60 |  |
| 28R | 692 ft +R | +16.90 | 16.60 | -0.30 |  |
| 28R | 792 ft -R | -16.50 | -15.70 | -0.80 |  |
| 28R | 792 ft +R | +19.70 | 16.30 | -3.40 |  |
| 28R | 892 ft -R | -16.10 | -15.30 | -0.80 |  |
| 28R | 892 ft +R | +17.30 | 16.60 | -0.70 |  |
| 28R | 992 ft -R | -19.50 | -16.60 | -2.90 |  |
| 28R | 992 ft +R | +18.90 | 17.50 | -1.40 |  |
| 28R | 1092 ft -R (inferred) | -17.40 | -15.70 | -1.70 |  |
| 28R | 1092 ft +R (inferred) | +17.80 | 17.40 | -0.40 |  |
| 28R | 1192 ft -R | -17.70 | -16.30 | -1.40 |  |
| 28R | 1192 ft +R | +16.50 | 20.60 | 4.10 |  |
| 28R | 1292 ft -R | -18.30 | -17.70 | -0.60 |  |
| 28R | 1292 ft +R | +19.30 | 18.80 | -0.50 |  |

The app builds 58 approach-light structures (2 catwalk (water), 9 crossbar (water), 2 hut (water), 7 post (land), 38 station (water)); 2 of them stand on a runway, displaced-threshold area, blast pad, EMAS bed or taxiway (OBSTRUCTION rows below).

## Data vs published source (no imagery)

Runway ends of the RWY table the 3-D draws (`js/world/airfield.js`, s/t) against the FAA/AirNav end coordinates (`js/geo.js` RWY_ENDS), both in the scene's frame `ltp-nad83-2011`:

| end | along-axis diff (m) | lateral diff (m) | displacement model / FAA (m) |
|---|---|---|---|
| 10L | +0.00 | +0.00 | 0.0 / 0.0 |
| 28R | -0.00 | -0.00 | 91.4 / 91.4 |
| 10R | +0.00 | +0.03 | 0.0 / 0.0 |
| 28L | +0.00 | +0.03 | 91.4 / 91.4 |
| 1L | +0.00 | +0.01 | 195.1 / 195.1 |
| 19R | -0.00 | +0.00 | 0.0 / 0.0 |
| 1R | +0.00 | -0.00 | 170.7 / 170.7 |
| 19L | +0.00 | +0.01 | 0.0 / 0.0 |

Largest difference: 10R (+0.00 m along, +0.03 m across). All eight ends agree with the FAA coordinates to better than 1 m. Displacements match.

Rendered aircraft planform (the model after `fit.js` scaling, plugs, span and fin fits, as `models.js` applies them - re-implemented in `common.py _stretch` and checked below) against the TYPES span that GroundPhysics and standFits use: 42 model-rendered types, all within 0.5 m.

Check of the re-implemented model fit: model dims (L, span, H in model units) after `_stretch` equal the page's `model.dims` for 42 of 42 types (to 2 cm).

## Imagery and georeference

- `naip`: `refs/cache/naip/naip_2024_world_0.5m.png` (sha256 `2b202c3e670c0310`, 162,720,797 bytes, 0.50 m/px), transform ltp-nad83-2011, sidecar `refs/cache/naip/naip_2024_world_0.5m.json`.
- `naip`: `refs/cache/naip/naip_2022_sfo_utm10n.tif` (sha256 `7e8d4db9248aaf3c`, 228,753,426 bytes, 0.60 m/px), transform GeoTIFF NAD83 / UTM zone 10N: world -> NAD83(2011) lat/lon (geo_frame.world_to_ll) -> NAD83 / UTM zone 10N (datum NAD83, no datum shift).
- `google`: 19 screenshots, registrations `tools/sat/work/reg.json` (sha256 `18369b4f52c29d2f`, frame(s) equirect-v1 mapped exactly into `ltp-nad83-2011` by tools/sat/common.py sim_from_reg); NAIP residual correction: applied: per-screenshot translation to NAIP for 15 of 19 screenshots (imreg.py).

Residual translation of each Google screenshot against NAIP (`imreg.py`, 2026-09-25T18:21Z; ground-level colour gradients, buildings masked, +-15.0 m search). `shift` = where a ground feature shows in the screenshot as registered, relative to NAIP (x east, z south); applied when `use`.

| screenshot | m/px | patches ok / tested | shift x, z (m) | MAD (m) | NCC | used | note |
|---|---|---|---|---|---|---|---|
| b1d51b0f | 0.28 | 4 / 16 | +2.29, +4.71 | 1.59 | 0.51 | no | not applied: 4 patch(es), MAD 1.6 m - spread > 3 m: rotation/scale error beyond a translation |
| 1a26bbeb | 0.57 | 32 / 39 | -3.96, -0.64 | 0.40 | 0.72 | yes | ok |
| c235f3b8 | 0.24 | 6 / 10 | -1.22, +3.62 | 0.87 | 0.57 | yes | ok - spread > 3 m: rotation/scale error beyond a translation |
| c1064033 | 1.61 | 10 / 39 | -3.35, +0.46 | 0.73 | 0.58 | yes | ok |
| 2f0be03d | 1.08 | 24 / 39 | -2.33, +0.81 | 1.01 | 0.64 | yes | ok - spread > 3 m: rotation/scale error beyond a translation |
| 103723b0 | 1.15 | 20 / 35 | -1.35, +2.04 | 1.03 | 0.68 | yes | ok |
| e6f569c1 | 0.50 | 10 / 29 | -1.42, +1.72 | 0.39 | 0.64 | yes | ok |
| 59be8a98 | 0.93 | 22 / 37 | -1.86, +0.70 | 0.69 | 0.64 | yes | ok - spread > 3 m: rotation/scale error beyond a translation |
| 4637f855 | 0.42 | 13 / 22 | -1.11, +1.45 | 0.48 | 0.51 | yes | ok |
| c9ff55e8 | 1.27 | 11 / 36 | -1.53, +0.64 | 0.70 | 0.51 | yes | ok |
| 39176bb8 | 0.27 | 3 / 16 | -1.09, +1.14 | 0.40 | 0.53 | yes | ok |
| 35809e3e | 1.07 | 10 / 31 | -0.94, +0.93 | 0.93 | 0.62 | yes | ok |
| bc91df95 | 0.58 | 20 / 29 | -0.81, +0.94 | 0.68 | 0.60 | yes | ok |
| bf5c7afc | 0.24 | 6 / 11 | -0.59, +1.09 | 0.66 | 0.61 | yes | ok |
| d82848c4 | 0.25 | 7 / 13 | +0.30, +1.08 | 0.55 | 0.64 | yes | ok |
| 151ec51d | 0.27 | 5 / 15 | -0.81, +0.68 | 4.25 | 0.51 | no | not applied: 5 patch(es), MAD 4.2 m - spread > 3 m: rotation/scale error beyond a translation |
| 0af09b78 | 0.56 | 15 / 23 | +0.04, +1.05 | 0.71 | 0.63 | yes | ok |
| 8b334c52 | 3.17 | 0 / 34 | – | – | – | no | no reliable patch (NCC < 0.35 or flat peak) |
| 03dcd4ae | 0.17 | 0 / 4 | – | – | – | no | no reliable patch (NCC < 0.35 or flat peak) |

Cross-source check after the correction: median over features of (Google bias - NAIP bias) along the outward normal, per class (a residual georeference difference would show as a common non-zero value):

| class | features on both | median difference (m) | median absolute difference (m) |
|---|---|---|---|
| extra-pavement | 238 | +0.10 | 0.80 |
| taxiway-edge | 143 | -0.10 | 1.85 |
| bridge-walkway | 39 | +0.70 | 1.65 |
| building | 32 | -0.07 | 1.32 |
| runway-threshold-bar | 6 | +0.17 | 0.75 |
| runway-end | 4 | +1.80 | 1.80 |
| emas-bed | 4 | +0.10 | 0.45 |
| runway-edge-stripe | 4 | -0.15 | 0.15 |
| runway-threshold | 2 | -0.52 | 0.52 |
| approach-light-crossbar | 2 | -1.05 | 4.00 |
| apron-edge | 2 | -1.25 | 1.25 |
| approach-light-station | 2 | +1.50 | 1.50 |

## How far to trust the automatic picks (self-test)

`tools/drawing/selftest.py` (rules `2026-09-25a: stripe-start rule, building edge de-duplication, rotunda boundary = not found, approach-light stations / crossbar ends / catwalk`) resamples each source over 14 regions (terminal, airfield, and a box at every threshold) into synthetic tiles whose content is displaced by a known vector ((0.8, -0.5), (2.0, -1.0) m) and re-measures every feature there. `stable` = same pick on an undisplaced resampled tile (within 0.5 m); `recovered` = the measured offset changed by the known n . shift (within 0.5 m). Low recovery means the class's numbers are dominated by picking a neighbouring edge.

**`naip`**

| class | samples in test regions | measured | stable | recovered @ 0.9 m | recovered @ 2.2 m |
|---|---|---|---|---|---|
| approach-light-catwalk | 24 | 7 | 1.00 | 1.00 | 1.00 |
| approach-light-crossbar | 15 | 15 | 1.00 | 0.87 | 0.86 |
| approach-light-station | 26 | 26 | 1.00 | 0.85 | 0.88 |
| apron-edge | 18 | 12 | 0.92 | 0.82 | 0.75 |
| bridge-walkway | 11 | 11 | 1.00 | 0.91 | 0.18 |
| building | 1563 | 1509 | 0.98 | 0.81 | 0.58 |
| emas-bed | 237 | 237 | 0.99 | 0.87 | 0.75 |
| extra-pavement | 808 | 750 | 0.97 | 0.85 | 0.69 |
| hold-line | 293 | 271 | 1.00 | 0.97 | 0.92 |
| runway-edge-stripe | 359 | 359 | 1.00 | 1.00 | 0.90 |
| runway-end | 65 | 65 | 1.00 | 1.00 | 1.00 |
| runway-threshold | 176 | 176 | 1.00 | 0.99 | 0.98 |
| runway-threshold-bar | 110 | 110 | 1.00 | 0.95 | 0.91 |
| stand-leadin | 262 | 0 | – | – | – |
| taxiway-centreline | 877 | 0 | – | – | – |
| taxiway-edge | 496 | 483 | 0.98 | 0.89 | 0.80 |

**`google`**

| class | samples in test regions | measured | stable | recovered @ 0.9 m | recovered @ 2.2 m |
|---|---|---|---|---|---|
| approach-light-catwalk | 24 | 0 | – | – | – |
| approach-light-crossbar | 15 | 6 | 0.67 | 0.80 | 0.75 |
| approach-light-station | 26 | 3 | 0.67 | 0.67 | 0.67 |
| apron-edge | 18 | 13 | 0.85 | 0.67 | 0.67 |
| bridge-walkway | 11 | 11 | 0.91 | 0.64 | 0.36 |
| building | 1563 | 1468 | 0.82 | 0.65 | 0.51 |
| emas-bed | 237 | 199 | 0.87 | 0.78 | 0.70 |
| extra-pavement | 808 | 600 | 0.91 | 0.84 | 0.67 |
| hold-line | 293 | 0 | – | – | – |
| runway-edge-stripe | 359 | 85 | 1.00 | 1.00 | 0.94 |
| runway-end | 65 | 61 | 0.52 | 0.62 | 0.44 |
| runway-threshold | 176 | 64 | 1.00 | 0.82 | 0.66 |
| runway-threshold-bar | 110 | 66 | 1.00 | 1.00 | 1.00 |
| stand-leadin | 262 | 0 | – | – | – |
| taxiway-centreline | 877 | 0 | – | – | – |
| taxiway-edge | 496 | 208 | 0.92 | 0.85 | 0.58 |

## Deviations from imagery - `naip`

Source: NAIP (2 image(s)) (USDA NAIP: public domain (U.S. Government work); credit requested: "USDA Farm Production and Conservation - Business Center, Geospatial Enterprise Operations" (see docs/research/imagery.md)). Offsets are signed along the outward edge normal (+ = imaged edge outside / right of the model), in metres; `gsd` = ground resolution of the image the profile was read from; `alt` = the same samples read from the next-best image (NAIP: the other year; Google: another screenshot). Features flagged when the median |offset| > 1.0 m.

| class | features | measured | flagged (median > 1 m) | median of medians | median p90 | typical gsd | notes |
|---|---|---|---|---|---|---|---|
| approach-light-catwalk | 2 | 2 | 0 | 0.85 | 0.97 | 0.50 | lateral position of the imaged catwalk deck vs the modelled catwalk line |
| approach-light-crossbar | 2 | 2 | 0 | 0.57 | 1.86 | 0.50 | imaged crossbar end vs modelled end (+ = imaged longer) |
| approach-light-station | 2 | 2 | 0 | 0.40 | 1.76 | 0.50 | along-axis position of each imaged station over water |
| apron-edge | 2 | 2 | 2 | 5.45 | 8.12 | 0.50 |  |
| bridge-rotunda | 128 | 72 | 0 | 3.47 | 3.47 | 0.50 | automatic disc search (6 m radius; picks at the boundary count as not found), low confidence - read with the sheets |
| bridge-walkway | 47 | 47 | 34 | 3.00 | 4.80 | 0.50 |  |
| building | 39 | 39 | 38 | 4.20 | 7.90 | 0.50 | roof edge vs footprint: relief displacement (roofs lean away from nadir) + registration; see `shift`/`resid` columns. One feature per building; edges shared with the ramp-level complex belong to the part |
| emas-bed | 4 | 4 | 1 | 0.20 | 4.36 | 0.50 |  |
| extra-pavement | 259 | 259 | 231 | 2.20 | 5.00 | 0.50 | derived from the Google imagery (circular on `google`); checks the vectorisation |
| hold-line | 90 | 90 | 0 | 0.15 | 0.30 | 0.50 | needs <= 0.6 m/px |
| runway-edge-stripe | 8 | 8 | 0 | 0.40 | 0.70 | 0.50 | 0.91 m stripe |
| runway-end | 4 | 4 | 0 | 0.55 | 0.55 | 0.50 |  |
| runway-threshold | 8 | 8 | 0 | 0.10 | 0.22 | 0.50 | start of the stripe block (stripe-start rule) |
| runway-threshold-bar | 8 | 8 | 8 | 2.35 | 2.45 | 0.50 | imaged 10 ft bar vs the model bar (see the runway table above) |
| stand-leadin | 103 | 0 | 0 | – | – | – | lead-in paint: needs <= 0.35 m/px; often under parked aircraft |
| taxiway-centreline | 265 | 0 | 0 | – | – | – | 6 in paint: needs <= 0.35 m/px |
| taxiway-edge | 162 | 162 | 84 | 1.10 | 5.72 | 0.50 |  |

### runway-end (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 10L pavement end | 13/13 | 0.90 | 0.90 | 1.0 | +0.90 | 0.50 | naip_2024_world_0.5m.jso | +0.50 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 28L pavement end | 13/13 | 0.60 | 0.60 | 0.6 | -0.60 | 0.50 | naip_2024_world_0.5m.jso | +0.90 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 10R pavement end | 13/13 | 0.50 | 0.50 | 0.7 | +0.50 | 0.50 | naip_2024_world_0.5m.jso | +0.50 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 28R pavement end | 13/13 | 0.40 | 0.40 | 0.5 | -0.40 | 0.50 | naip_2024_world_0.5m.jso | +0.90 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-threshold (8 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 10L threshold stripes (start 6.1 m past threshold) | 16/16 | 0.85 | 0.90 | 0.9 | +0.85 | 0.50 | naip_2024_world_0.5m.jso | +0.40 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 10R threshold stripes (start 6.1 m past threshold) | 16/16 | 0.50 | 0.70 | 0.9 | +0.50 | 0.50 | naip_2024_world_0.5m.jso | +0.40 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 19L threshold stripes (start 6.1 m past threshold) | 16/16 | 0.20 | 0.25 | 13.1 | +0.20 | 0.50 | naip_2024_world_0.5m.jso | +0.20 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| RWY 28R threshold stripes (start 6.1 m past threshold) | 16/16 | 0.10 | 0.20 | 0.2 | -0.10 | 0.50 | naip_2024_world_0.5m.jso | -0.20 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28L threshold stripes (start 6.1 m past threshold) | 16/16 | 0.10 | 0.20 | 0.2 | -0.10 | 0.50 | naip_2024_world_0.5m.jso | -0.40 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 19R threshold stripes (start 6.1 m past threshold) | 16/16 | 0.10 | 0.10 | 0.2 | -0.10 | 0.50 | naip_2024_world_0.5m.jso | +0.60 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| RWY 1R threshold stripes (start 6.1 m past threshold) | 16/16 | 0.10 | 0.25 | 0.3 | -0.10 | 0.50 | naip_2024_world_0.5m.jso | +0.10 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| RWY 1L threshold stripes (start 6.1 m past threshold) | 16/16 | 0.00 | 0.20 | 0.2 | -0.00 | 0.50 | naip_2024_world_0.5m.jso | -0.00 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |

### runway-threshold-bar (8 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28L threshold bar (model: approach side, centre -1.52 m; displaced 91.4 m) **>1 m** | 10/10 | 3.40 | 3.50 | 3.5 | +3.40 | 0.50 | naip_2024_world_0.5m.jso | +3.60 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 1R threshold bar (model: approach side, centre -1.52 m; displaced 170.7 m) **>1 m** | 10/10 | 3.30 | 3.40 | 3.4 | +3.30 | 0.50 | naip_2024_world_0.5m.jso | +3.10 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| RWY 1L threshold bar (model: approach side, centre -1.52 m; displaced 195.1 m) **>1 m** | 10/10 | 3.25 | 3.31 | 3.4 | +3.25 | 0.50 | naip_2024_world_0.5m.jso | +3.20 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| RWY 28R threshold bar (model: approach side, centre -1.52 m; displaced 91.4 m) **>1 m** | 10/10 | 3.20 | 3.21 | 3.3 | +3.20 | 0.50 | naip_2024_world_0.5m.jso | +3.40 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 19R threshold bar (model: none drawn) **>1 m** | 10/10 | 1.50 | 1.70 | 1.7 | +1.50 | 0.50 | naip_2024_world_0.5m.jso | +1.10 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| RWY 19L threshold bar (model: none drawn) **>1 m** | 10/10 | 1.50 | 1.61 | 1.7 | +1.50 | 0.50 | naip_2024_world_0.5m.jso | +1.40 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| RWY 10R threshold bar (model: none drawn) **>1 m** | 10/10 | 1.30 | 1.41 | 1.5 | +1.30 | 0.50 | naip_2024_world_0.5m.jso | +1.30 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 10L threshold bar (model: none drawn) **>1 m** | 10/10 | 0.90 | 1.10 | 1.1 | +0.90 | 0.50 | naip_2024_world_0.5m.jso | +1.35 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |

### runway-edge-stripe (8 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 1L/19R edge stripe (north/west side) | 216/228 | 0.60 | 0.90 | 1.0 | +0.60 | 0.50 | naip_2024_world_0.5m.jso | +0.60 (0.60) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| RWY 10L/28R edge stripe (north/west side) | 355/356 | 0.50 | 0.70 | 0.8 | +0.50 | 0.50 | naip_2024_world_0.5m.jso | +0.50 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| RWY 10R/28L edge stripe (north/west side) | 340/341 | 0.50 | 0.70 | 0.8 | +0.50 | 0.50 | naip_2024_world_0.5m.jso | +0.50 (0.60) | [00-overview](00-overview.png) |
| RWY 1R/19L edge stripe (north/west side) | 246/258 | 0.50 | 0.80 | 1.0 | +0.50 | 0.50 | naip_2024_world_0.5m.jso | +0.70 (0.60) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| RWY 10L/28R edge stripe (south/east side) | 355/356 | 0.30 | 0.60 | 0.8 | +0.30 | 0.50 | naip_2024_world_0.5m.jso | +0.20 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| RWY 10R/28L edge stripe (south/east side) | 340/341 | 0.30 | 0.70 | 0.8 | +0.30 | 0.50 | naip_2024_world_0.5m.jso | +0.30 (0.60) | [00-overview](00-overview.png) |
| RWY 1L/19R edge stripe (south/east side) | 216/228 | 0.30 | 0.40 | 0.5 | +0.30 | 0.50 | naip_2024_world_0.5m.jso | -0.00 (0.60) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| RWY 1R/19L edge stripe (south/east side) | 245/258 | 0.20 | 0.40 | 0.5 | +0.20 | 0.50 | naip_2024_world_0.5m.jso | +0.10 (0.60) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |

### emas-bed (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| EMAS bed beyond RWY 19R **>1 m** | 126/126 | 1.20 | 6.60 | 9.6 | +0.20 | 0.50 | naip_2024_world_0.5m.jso | +0.30 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| EMAS bed beyond RWY 19L | 126/126 | 0.20 | 6.75 | 9.5 | -0.00 | 0.50 | naip_2024_world_0.5m.jso | +0.20 (0.60) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| EMAS bed beyond RWY 1L | 132/132 | 0.20 | 1.00 | 8.7 | -0.00 | 0.50 | naip_2024_world_0.5m.jso | +0.15 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| EMAS bed beyond RWY 1R | 118/118 | 0.10 | 2.13 | 8.9 | +0.10 | 0.50 | naip_2024_world_0.5m.jso | +0.40 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |

### approach-light-station (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28R ALSF2 approach-light stations over water (19, 211-760 m from the threshold) | 19/19 | 0.60 | 3.22 | 10.1 | +0.30 | 0.50 | naip_2024_world_0.5m.jso | +2.00 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28L MALSR approach-light stations over water (19, 213-762 m from the threshold) | 19/19 | 0.20 | 0.30 | 0.5 | -0.20 | 0.50 | naip_2024_world_0.5m.jso | +1.60 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### approach-light-crossbar (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28R approach-light crossbars over water (7), imaged ends vs modelled ends | 14/14 | 0.80 | 3.25 | 4.1 | -0.75 | 0.50 | naip_2024_world_0.5m.jso | -1.45 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28L approach-light crossbars over water (2), imaged ends vs modelled ends | 4/4 | 0.35 | 0.47 | 0.5 | -0.35 | 0.50 | naip_2024_world_0.5m.jso | -0.70 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### approach-light-catwalk (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28L approach-light catwalk over water (18 spans), lateral position vs the modelled catwalk | 10/18 | 0.95 | 1.11 | 1.2 | -0.95 | 0.50 | naip_2024_world_0.5m.jso | -0.55 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28R approach-light catwalk over water (18 spans), lateral position vs the modelled catwalk | 8/18 | 0.75 | 0.83 | 0.9 | -0.75 | 0.50 | naip_2024_world_0.5m.jso | -0.50 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### building (39 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | fit shift | resid median | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Air Traffic Control Tower **>1 m** | 25/25 | 8.90 | 9.18 | 9.7 | +6.50 | 0.50 | naip_2024_world_0.5m.jso | +9.10 (0.60) | 5.06 | 4.19 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| Garaga A AirTrain Station | 1/1 | 6.60 | 6.60 | 6.6 | +6.60 | 0.50 | naip_2024_world_0.5m.jso | – | – | – | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Harvey Milk Terminal 1 **>1 m** | 321/340 | 6.00 | 8.90 | 9.8 | -0.60 | 0.50 | naip_2024_world_0.5m.jso | -2.45 (0.60) | 1.92 | 5.55 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Grand Hyatt Hotel **>1 m** | 113/114 | 5.40 | 8.38 | 9.7 | -2.00 | 0.50 | naip_2024_world_0.5m.jso | -0.95 (0.60) | 1.91 | 4.64 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Garage G AirTrain Station **>1 m** | 109/119 | 5.30 | 7.20 | 9.6 | +3.00 | 0.50 | naip_2024_world_0.5m.jso | +4.10 (0.60) | 2.02 | 3.73 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Long Term Parking AirTrain Station **>1 m** | 107/108 | 5.20 | 7.80 | 9.6 | +2.30 | 0.50 | naip_2024_world_0.5m.jso | +5.00 (0.60) | 3.95 | 3.66 | [00-overview](00-overview.png) |
| Boarding Area D **>1 m** | 235/248 | 4.90 | 7.80 | 9.7 | +3.20 | 0.50 | naip_2024_world_0.5m.jso | +3.65 (0.60) | 5.67 | 1.67 | [10-ba-D](10-ba-D.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Terminal Three AirTrain Station **>1 m** | 32/32 | 4.85 | 6.90 | 7.7 | -3.10 | 0.50 | naip_2024_world_0.5m.jso | -3.05 (0.60) | – | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Grand Hyatt Hotel AirTrain Station **>1 m** | 70/73 | 4.80 | 9.22 | 9.7 | +4.45 | 0.50 | naip_2024_world_0.5m.jso | -1.00 (0.60) | 2.86 | 4.26 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Boarding Area E **>1 m** | 152/153 | 4.70 | 7.90 | 9.7 | +0.65 | 0.50 | naip_2024_world_0.5m.jso | -1.75 (0.60) | 4.26 | 3.76 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| International Terminal **>1 m** | 365/381 | 4.70 | 9.06 | 9.8 | +0.40 | 0.50 | naip_2024_world_0.5m.jso | +0.30 (0.60) | 2.64 | 3.75 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| Central Parking Garage **>1 m** | 425/427 | 4.70 | 8.90 | 9.7 | -0.30 | 0.50 | naip_2024_world_0.5m.jso | +2.10 (0.60) | 1.70 | 4.93 | [20-itb-tower](20-itb-tower.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Garage A **>1 m** | 9/9 | 4.70 | 6.88 | 7.2 | -4.30 | 0.50 | naip_2024_world_0.5m.jso | -2.90 (0.60) | 3.96 | 3.43 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| West Field Road AirTrain Station (Inbound) **>1 m** | 85/85 | 4.60 | 9.10 | 9.7 | -3.20 | 0.50 | naip_2024_world_0.5m.jso | +2.20 (0.60) | – | – | [00-overview](00-overview.png) |
| Boarding Area C **>1 m** | 160/162 | 4.60 | 7.75 | 9.7 | +1.45 | 0.50 | naip_2024_world_0.5m.jso | +3.40 (0.60) | 3.55 | 4.21 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Terminal complex ramp level **>1 m** | 128/137 | 4.60 | 8.23 | 9.5 | -0.15 | 0.50 | naip_2024_world_0.5m.jso | -1.10 (0.60) | 2.66 | 3.54 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Terminal complex ramp level **>1 m** | 75/80 | 4.30 | 9.40 | 9.7 | +2.10 | 0.50 | naip_2024_world_0.5m.jso | -0.90 (0.60) | 4.55 | 3.39 | [20-itb-tower](20-itb-tower.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Terminal 2 **>1 m** | 241/257 | 4.30 | 8.70 | 9.7 | +2.60 | 0.50 | naip_2024_world_0.5m.jso | +2.90 (0.60) | 2.39 | 4.18 | [10-ba-D](10-ba-D.png), [20-itb-tower](20-itb-tower.png) |
| Terminal One AirTrain Station **>1 m** | 30/30 | 4.25 | 7.41 | 8.8 | -3.85 | 0.50 | naip_2024_world_0.5m.jso | -3.65 (0.60) | – | – | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Boarding Area G **>1 m** | 367/372 | 4.20 | 7.34 | 9.4 | +2.60 | 0.50 | naip_2024_world_0.5m.jso | +4.40 (0.60) | 3.79 | 1.97 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| Boarding Area A **>1 m** | 278/307 | 4.15 | 8.73 | 9.7 | +2.15 | 0.50 | naip_2024_world_0.5m.jso | -0.40 (0.60) | 3.00 | 4.00 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Westfield Road AirTrain Station (Inbound) **>1 m** | 69/69 | 3.80 | 6.78 | 9.1 | -3.60 | 0.50 | naip_2024_world_0.5m.jso | +0.80 (0.60) | – | – | [00-overview](00-overview.png) |
| Terminal complex ramp level **>1 m** | 82/87 | 3.50 | 9.00 | 9.7 | +2.25 | 0.50 | naip_2024_world_0.5m.jso | +0.40 (0.60) | 3.61 | 3.28 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Super Bay Hangar Building **>1 m** | 292/292 | 3.45 | 9.40 | 9.8 | +3.40 | 0.50 | naip_2024_world_0.5m.jso | -0.70 (0.60) | 4.86 | 3.63 | [30-rwy-19R](30-rwy-19R.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Boarding Area B **>1 m** | 433/438 | 3.40 | 8.88 | 9.7 | -1.40 | 0.50 | naip_2024_world_0.5m.jso | -1.60 (0.60) | 1.01 | 3.34 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Garage A **>1 m** | 286/289 | 3.40 | 6.75 | 9.5 | +1.50 | 0.50 | naip_2024_world_0.5m.jso | +1.80 (0.60) | 3.77 | 2.76 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Garage G **>1 m** | 284/302 | 3.40 | 9.00 | 9.8 | +0.10 | 0.50 | naip_2024_world_0.5m.jso | +3.20 (0.60) | 1.06 | 3.83 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Long-Term Parking Garage 1 **>1 m** | 243/247 | 3.40 | 8.80 | 9.8 | -0.80 | 0.50 | naip_2024_world_0.5m.jso | +2.25 (0.60) | 1.73 | 2.72 | [00-overview](00-overview.png) |
| West Field Road AirTrain Station (Outbound) **>1 m** | 80/80 | 3.10 | 8.11 | 8.9 | -1.30 | 0.50 | naip_2024_world_0.5m.jso | +0.40 (0.60) | 1.70 | 3.12 | [00-overview](00-overview.png) |
| Westfield Road AirTrain Station (Outbound)g **>1 m** | 56/56 | 2.90 | 7.50 | 9.3 | -2.35 | 0.50 | naip_2024_world_0.5m.jso | -0.15 (0.60) | 1.35 | 2.82 | [00-overview](00-overview.png) |
| Terminal 3 **>1 m** | 290/297 | 2.85 | 8.90 | 9.7 | +2.00 | 0.50 | naip_2024_world_0.5m.jso | +1.80 (0.60) | 3.69 | 2.90 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Rental Car Center **>1 m** | 313/326 | 2.70 | 8.50 | 9.7 | +0.90 | 0.50 | naip_2024_world_0.5m.jso | -0.30 (0.60) | 3.85 | 1.86 | [40-apron-4-north-west](40-apron-4-north-west.png), [00-overview](00-overview.png) |
| International Terminal (G) AirTrain Station **>1 m** | 15/15 | 2.50 | 5.46 | 7.9 | +2.40 | 0.50 | naip_2024_world_0.5m.jso | -3.10 (0.60) | 7.14 | 2.18 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Long-Term Parking Garage 2 **>1 m** | 314/316 | 2.40 | 5.80 | 9.6 | -0.80 | 0.50 | naip_2024_world_0.5m.jso | -0.30 (0.60) | 2.23 | 1.68 | [00-overview](00-overview.png) |
| Rental Car Center AirTrain Station **>1 m** | 28/28 | 2.40 | 3.27 | 9.7 | +1.50 | 0.50 | naip_2024_world_0.5m.jso | +0.75 (0.60) | 0.20 | 2.43 | [40-apron-4-north-west](40-apron-4-north-west.png), [00-overview](00-overview.png) |
| Boarding Area F **>1 m** | 488/513 | 2.40 | 5.70 | 9.7 | +0.35 | 0.50 | naip_2024_world_0.5m.jso | -0.10 (0.60) | 3.31 | 1.20 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| Consolidated Administration Campus **>1 m** | 157/158 | 2.10 | 5.30 | 9.7 | +1.30 | 0.50 | naip_2024_world_0.5m.jso | +1.50 (0.60) | 2.73 | 0.71 | [40-apron-4-north-west](40-apron-4-north-west.png), [00-overview](00-overview.png) |
| Terminal 3 Air Train Station **>1 m** | 15/15 | 2.00 | 6.38 | 8.5 | -1.90 | 0.50 | naip_2024_world_0.5m.jso | -1.60 (0.60) | – | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Terminal Two AirTrain Station **>1 m** | 27/27 | 1.80 | 7.00 | 7.0 | -1.80 | 0.50 | naip_2024_world_0.5m.jso | -1.20 (0.60) | – | – | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |

### taxiway-edge (162 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| Taxiway A/G **>1 m** | 3/3 | 9.20 | 9.28 | 9.3 | +9.20 | 0.50 | naip_2024_world_0.5m.jso | +8.90 (0.60) | [10-ba-C](10-ba-C.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway C/APRON **>1 m** | 9/14 | 7.50 | 8.80 | 9.2 | +7.50 | 0.50 | naip_2024_world_0.5m.jso | +7.25 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway B **>1 m** | 16/16 | 7.45 | 8.00 | 8.2 | +7.45 | 0.50 | naip_2024_world_0.5m.jso | +7.40 (0.60) | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Taxiway S2/S3 **>1 m** | 12/12 | 7.45 | 9.00 | 9.1 | +7.15 | 0.50 | naip_2024_world_0.5m.jso | +7.45 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C/K **>1 m** | 9/14 | 7.20 | 7.84 | 8.0 | +7.20 | 0.50 | naip_2024_world_0.5m.jso | +6.85 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway C1 **>1 m** | 13/14 | 7.10 | 8.64 | 9.5 | +1.10 | 0.50 | naip_2024_world_0.5m.jso | +0.50 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway L **>1 m** | 23/23 | 7.00 | 9.58 | 9.8 | +6.60 | 0.50 | naip_2024_world_0.5m.jso | +6.15 (0.60) | [00-overview](00-overview.png) |
| Taxiway K **>1 m** | 11/11 | 6.80 | 7.60 | 8.8 | +6.60 | 0.50 | naip_2024_world_0.5m.jso | -0.20 (0.60) | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Taxiway R **>1 m** | 25/26 | 6.70 | 9.38 | 9.6 | +5.20 | 0.50 | naip_2024_world_0.5m.jso | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway A/D **>1 m** | 5/5 | 6.50 | 9.46 | 9.7 | +6.50 | 0.50 | naip_2024_world_0.5m.jso | +1.00 (0.60) | [10-ba-E](10-ba-E.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Taxiway L **>1 m** | 22/26 | 6.45 | 9.60 | 9.7 | +1.45 | 0.50 | naip_2024_world_0.5m.jso | -0.70 (0.60) | [00-overview](00-overview.png) |
| Taxiway S4/S **>1 m** | 11/11 | 6.40 | 7.70 | 7.9 | +6.40 | 0.50 | naip_2024_world_0.5m.jso | +4.40 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway B/H **>1 m** | 10/10 | 5.40 | 6.60 | 7.5 | +5.40 | 0.50 | naip_2024_world_0.5m.jso | +3.50 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway S2 **>1 m** | 15/15 | 5.20 | 7.76 | 8.4 | +4.70 | 0.50 | naip_2024_world_0.5m.jso | +5.40 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway D **>1 m** | 12/12 | 5.05 | 7.85 | 7.9 | +4.60 | 0.50 | naip_2024_world_0.5m.jso | +4.70 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway P **>1 m** | 14/14 | 5.05 | 8.32 | 9.1 | +5.05 | 0.50 | naip_2024_world_0.5m.jso | +5.55 (0.60) | [00-overview](00-overview.png) |
| Taxiway B/G **>1 m** | 9/9 | 5.00 | 6.32 | 6.8 | +5.00 | 0.50 | naip_2024_world_0.5m.jso | +1.25 (0.60) | [10-ba-C](10-ba-C.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway R **>1 m** | 3/3 | 5.00 | 5.16 | 5.2 | +5.00 | 0.50 | naip_2024_world_0.5m.jso | +4.10 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway Z/S2 **>1 m** | 3/3 | 4.70 | 7.02 | 7.6 | +0.90 | 0.50 | naip_2024_world_0.5m.jso | +7.40 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway R/U **>1 m** | 12/15 | 4.45 | 8.97 | 9.7 | -2.75 | 0.50 | naip_2024_world_0.5m.jso | -2.90 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway S3 **>1 m** | 7/7 | 4.40 | 6.46 | 6.7 | +4.40 | 0.50 | naip_2024_world_0.5m.jso | +5.50 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C | 2/3 | 4.30 | 7.26 | 8.0 | +4.30 | 0.50 | naip_2024_world_0.5m.jso | +3.65 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway C/R **>1 m** | 11/11 | 4.30 | 9.00 | 9.6 | +2.00 | 0.50 | naip_2024_world_0.5m.jso | +0.10 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway U **>1 m** | 35/40 | 4.20 | 7.70 | 9.0 | +1.00 | 0.50 | naip_2024_world_0.5m.jso | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C **>1 m** | 14/15 | 3.85 | 8.00 | 8.3 | +3.85 | 0.50 | naip_2024_world_0.5m.jso | +0.30 (0.60) | [30-rwy-19R](30-rwy-19R.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Taxiway R **>1 m** | 25/26 | 3.80 | 4.36 | 5.1 | -3.80 | 0.50 | naip_2024_world_0.5m.jso | -1.70 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway S2 **>1 m** | 3/3 | 3.70 | 8.34 | 9.5 | +3.70 | 0.50 | naip_2024_world_0.5m.jso | +0.10 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway H **>1 m** | 8/8 | 3.35 | 5.84 | 8.5 | +1.90 | 0.50 | naip_2024_world_0.5m.jso | -0.00 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway U **>1 m** | 69/80 | 3.20 | 8.38 | 9.7 | +0.50 | 0.50 | naip_2024_world_0.5m.jso | +7.75 (0.60) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway G **>1 m** | 21/26 | 3.10 | 8.80 | 9.7 | +1.00 | 0.50 | naip_2024_world_0.5m.jso | -1.10 (0.60) | [30-rwy-1L](30-rwy-1L.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Taxiway N **>1 m** | 32/34 | 3.10 | 9.69 | 9.7 | +0.45 | 0.50 | naip_2024_world_0.5m.jso | +0.65 (0.60) | [30-rwy-28L](30-rwy-28L.png), [00-overview](00-overview.png) |
| Taxiway B/D **>1 m** | 6/8 | 3.00 | 5.65 | 6.6 | +0.60 | 0.50 | naip_2024_world_0.5m.jso | +0.05 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway B **>1 m** | 47/48 | 2.90 | 7.40 | 8.7 | +0.30 | 0.50 | naip_2024_world_0.5m.jso | +0.10 (0.60) | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Taxiway G **>1 m** | 14/14 | 2.85 | 4.68 | 5.2 | +2.70 | 0.50 | naip_2024_world_0.5m.jso | – | [30-rwy-1L](30-rwy-1L.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Taxiway B **>1 m** | 44/44 | 2.75 | 8.70 | 9.3 | +0.20 | 0.50 | naip_2024_world_0.5m.jso | +0.20 (0.60) | [00-overview](00-overview.png) |
| Taxiway D **>1 m** | 8/11 | 2.55 | 9.33 | 9.4 | -2.40 | 0.50 | naip_2024_world_0.5m.jso | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway A **>1 m** | 15/15 | 2.40 | 7.06 | 8.3 | +2.40 | 0.50 | naip_2024_world_0.5m.jso | +0.80 (0.60) | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Taxiway C **>1 m** | 40/44 | 2.35 | 8.10 | 9.1 | +0.25 | 0.50 | naip_2024_world_0.5m.jso | +0.70 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway C1/U **>1 m** | 10/10 | 2.30 | 9.50 | 9.5 | +2.30 | 0.50 | naip_2024_world_0.5m.jso | +2.25 (0.60) | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| Taxiway C **>1 m** | 22/22 | 2.20 | 9.28 | 9.6 | -0.10 | 0.50 | naip_2024_world_0.5m.jso | -0.60 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### apron-edge (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| apron outline #0 **>1 m** | 10/10 | 5.70 | 7.24 | 8.5 | -4.70 | 0.50 | naip_2024_world_0.5m.jso | +3.50 (0.60) | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| apron outline #1 **>1 m** | 43/57 | 5.20 | 9.00 | 9.7 | +3.70 | 0.50 | naip_2024_world_0.5m.jso | +4.05 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |

### extra-pavement (259 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| extra pavement #10 **>1 m** | 11/11 | 9.60 | 9.70 | 9.7 | -9.60 | 0.50 | naip_2024_world_0.5m.jso | -9.50 (0.60) | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| extra pavement #248 **>1 m** | 29/38 | 9.60 | 9.72 | 9.8 | +9.60 | 0.50 | naip_2024_world_0.5m.jso | +0.75 (0.60) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| extra pavement #336 **>1 m** | 9/9 | 9.50 | 9.62 | 9.7 | +9.50 | 0.50 | naip_2024_world_0.5m.jso | +0.50 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #173 **>1 m** | 28/33 | 9.40 | 9.70 | 9.7 | +9.40 | 0.50 | naip_2024_world_0.5m.jso | +1.90 (0.60) | [10-ba-F](10-ba-F.png), [00-overview](00-overview.png) |
| extra pavement #223 **>1 m** | 11/15 | 8.90 | 9.20 | 9.5 | +8.90 | 0.50 | naip_2024_world_0.5m.jso | +9.00 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| extra pavement #152 **>1 m** | 10/10 | 8.80 | 9.60 | 9.6 | +4.10 | 0.50 | naip_2024_world_0.5m.jso | +7.10 (0.60) | [10-ba-F](10-ba-F.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #214 **>1 m** | 9/9 | 8.40 | 8.98 | 9.7 | +6.80 | 0.50 | naip_2024_world_0.5m.jso | +8.05 (0.60) | [00-overview](00-overview.png) |
| extra pavement #15 **>1 m** | 9/9 | 8.20 | 9.52 | 9.6 | +1.00 | 0.50 | naip_2024_world_0.5m.jso | -9.20 (0.60) | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| extra pavement #333 **>1 m** | 10/10 | 7.90 | 9.60 | 9.6 | +4.15 | 0.50 | naip_2024_world_0.5m.jso | -3.80 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #218 **>1 m** | 6/7 | 7.90 | 8.05 | 8.1 | +7.90 | 0.50 | naip_2024_world_0.5m.jso | +7.50 (0.60) | [00-overview](00-overview.png) |
| extra pavement #194 **>1 m** | 17/23 | 7.80 | 8.14 | 8.4 | +7.80 | 0.50 | naip_2024_world_0.5m.jso | -1.50 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| extra pavement #117 **>1 m** | 29/35 | 7.60 | 9.12 | 9.7 | +4.10 | 0.50 | naip_2024_world_0.5m.jso | +7.95 (0.60) | [30-rwy-10R](30-rwy-10R.png), [40-apron-4-north-west](40-apron-4-north-west.png) |
| extra pavement #63 **>1 m** | 12/18 | 7.55 | 7.90 | 8.6 | +7.55 | 0.50 | naip_2024_world_0.5m.jso | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #39 **>1 m** | 9/9 | 7.40 | 9.52 | 9.6 | +2.80 | 0.50 | naip_2024_world_0.5m.jso | +4.90 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #64 **>1 m** | 18/23 | 7.35 | 8.83 | 9.7 | +6.70 | 0.50 | naip_2024_world_0.5m.jso | +2.35 (0.60) | [30-rwy-19L](30-rwy-19L.png), [00-overview](00-overview.png) |
| extra pavement #91 **>1 m** | 17/19 | 7.30 | 9.38 | 9.5 | +2.40 | 0.50 | naip_2024_world_0.5m.jso | +8.00 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #13 **>1 m** | 11/15 | 7.20 | 8.00 | 8.2 | +7.20 | 0.50 | naip_2024_world_0.5m.jso | +5.55 (0.60) | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| extra pavement #5 **>1 m** | 10/14 | 7.10 | 8.45 | 8.9 | +6.80 | 0.50 | naip_2024_world_0.5m.jso | – | [40-apron-3-north-west](40-apron-3-north-west.png), [00-overview](00-overview.png) |
| extra pavement #205 **>1 m** | 4/5 | 6.75 | 7.43 | 7.7 | +6.75 | 0.50 | naip_2024_world_0.5m.jso | +3.60 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| extra pavement #96 **>1 m** | 7/9 | 6.70 | 7.52 | 7.7 | -6.70 | 0.50 | naip_2024_world_0.5m.jso | – | [30-rwy-19R](30-rwy-19R.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| extra pavement #51 **>1 m** | 7/8 | 6.50 | 9.34 | 9.4 | +1.70 | 0.50 | naip_2024_world_0.5m.jso | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #307 **>1 m** | 4/4 | 6.45 | 6.88 | 7.0 | +6.45 | 0.50 | naip_2024_world_0.5m.jso | +6.45 (0.60) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| extra pavement #322 **>1 m** | 9/9 | 6.40 | 7.28 | 9.6 | +6.40 | 0.50 | naip_2024_world_0.5m.jso | +6.40 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| extra pavement #332 **>1 m** | 4/4 | 6.40 | 9.33 | 9.6 | +6.40 | 0.50 | naip_2024_world_0.5m.jso | +2.05 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #1 **>1 m** | 50/113 | 6.20 | 8.81 | 9.5 | +4.35 | 0.50 | naip_2024_world_0.5m.jso | +1.15 (0.60) | [40-apron-3-north-west](40-apron-3-north-west.png), [00-overview](00-overview.png) |
| extra pavement #137 **>1 m** | 9/13 | 6.20 | 8.24 | 9.2 | +6.20 | 0.50 | naip_2024_world_0.5m.jso | +5.90 (0.60) | [30-rwy-10R](30-rwy-10R.png), [40-apron-4-north-west](40-apron-4-north-west.png) |
| extra pavement #262 **>1 m** | 5/5 | 5.90 | 6.94 | 7.1 | +5.90 | 0.50 | naip_2024_world_0.5m.jso | +6.80 (0.60) | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| extra pavement #331 **>1 m** | 14/14 | 5.75 | 8.40 | 9.5 | +5.25 | 0.50 | naip_2024_world_0.5m.jso | +6.10 (0.60) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #55 **>1 m** | 6/7 | 5.65 | 9.55 | 9.6 | +3.40 | 0.50 | naip_2024_world_0.5m.jso | +1.00 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #145 **>1 m** | 7/7 | 5.60 | 9.42 | 9.6 | +5.60 | 0.50 | naip_2024_world_0.5m.jso | +2.60 (0.60) | [30-rwy-10R](30-rwy-10R.png), [40-apron-4-north-west](40-apron-4-north-west.png) |
| extra pavement #227 **>1 m** | 6/8 | 5.60 | 8.70 | 9.2 | +4.55 | 0.50 | naip_2024_world_0.5m.jso | +2.40 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| extra pavement #72 **>1 m** | 13/24 | 5.40 | 7.80 | 7.8 | +5.40 | 0.50 | naip_2024_world_0.5m.jso | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #191 **>1 m** | 9/12 | 5.40 | 9.40 | 9.4 | +4.70 | 0.50 | naip_2024_world_0.5m.jso | +4.90 (0.60) | [00-overview](00-overview.png) |
| extra pavement #193 **>1 m** | 12/12 | 5.35 | 9.44 | 9.6 | -3.60 | 0.50 | naip_2024_world_0.5m.jso | +2.85 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| extra pavement #161 **>1 m** | 8/8 | 5.35 | 9.06 | 9.2 | +5.20 | 0.50 | naip_2024_world_0.5m.jso | +5.95 (0.60) | [10-ba-F](10-ba-F.png), [00-overview](00-overview.png) |
| extra pavement #190 **>1 m** | 8/9 | 5.10 | 8.65 | 9.0 | +3.50 | 0.50 | naip_2024_world_0.5m.jso | +3.30 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| extra pavement #174 **>1 m** | 13/14 | 5.00 | 8.80 | 9.0 | +4.80 | 0.50 | naip_2024_world_0.5m.jso | +5.30 (0.60) | [00-overview](00-overview.png) |
| extra pavement #104 **>1 m** | 20/27 | 4.70 | 7.89 | 9.6 | +1.15 | 0.50 | naip_2024_world_0.5m.jso | +1.10 (0.60) | [30-rwy-10R](30-rwy-10R.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| extra pavement #80 **>1 m** | 4/4 | 4.50 | 7.07 | 7.7 | +4.50 | 0.50 | naip_2024_world_0.5m.jso | -3.35 (0.60) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #108 **>1 m** | 5/5 | 4.50 | 8.32 | 9.0 | +4.50 | 0.50 | naip_2024_world_0.5m.jso | – | [40-apron-4-north-west](40-apron-4-north-west.png), [00-overview](00-overview.png) |

### bridge-walkway (47 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| B11S bridge B11 fixed walkway **>1 m** | 3/3 | 5.90 | 5.90 | 5.9 | -5.90 | 0.50 | naip_2024_world_0.5m.jso | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A13 bridge A13 fixed walkway **>1 m** | 5/5 | 5.20 | 5.82 | 5.9 | +5.20 | 0.50 | naip_2024_world_0.5m.jso | -0.80 (0.60) | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| C1 bridge C1 fixed walkway | 1/3 | 5.20 | 5.20 | 5.2 | +5.20 | 0.50 | naip_2024_world_0.5m.jso | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| G9 bridge G9 fixed walkway **>1 m** | 8/8 | 5.15 | 5.48 | 5.9 | -5.15 | 0.50 | naip_2024_world_0.5m.jso | -4.55 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A11 bridge A11 fixed walkway **>1 m** | 3/3 | 4.80 | 5.68 | 5.9 | -4.80 | 0.50 | naip_2024_world_0.5m.jso | +1.80 (0.60) | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| B23 bridge B23 fixed walkway **>1 m** | 7/7 | 4.80 | 5.90 | 5.9 | +4.80 | 0.50 | naip_2024_world_0.5m.jso | +5.00 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B20 bridge B20 fixed walkway **>1 m** | 11/11 | 4.70 | 5.40 | 5.7 | +4.70 | 0.50 | naip_2024_world_0.5m.jso | +2.10 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G13 bridge G13 fixed walkway **>1 m** | 7/7 | 4.60 | 5.40 | 5.4 | +3.90 | 0.50 | naip_2024_world_0.5m.jso | +1.90 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| B8 bridge B8 fixed walkway **>1 m** | 3/4 | 4.50 | 4.98 | 5.1 | -4.50 | 0.50 | naip_2024_world_0.5m.jso | -4.90 (0.60) | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| A1 bridge A1 fixed walkway **>1 m** | 21/26 | 4.40 | 5.90 | 5.9 | -3.10 | 0.50 | naip_2024_world_0.5m.jso | -3.20 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G10 bridge G10 fixed walkway **>1 m** | 8/8 | 4.25 | 5.69 | 5.9 | -3.25 | 0.50 | naip_2024_world_0.5m.jso | +4.35 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| G10 bridge G10 fixed walkway **>1 m** | 5/5 | 4.20 | 4.84 | 5.0 | -4.20 | 0.50 | naip_2024_world_0.5m.jso | -5.20 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| B19 bridge B19 fixed walkway **>1 m** | 12/12 | 4.15 | 5.90 | 5.9 | +2.90 | 0.50 | naip_2024_world_0.5m.jso | +3.10 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A6 bridge A6 fixed walkway **>1 m** | 6/6 | 4.15 | 5.50 | 5.8 | +4.15 | 0.50 | naip_2024_world_0.5m.jso | +4.50 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| F11 bridge F11 fixed walkway **>1 m** | 7/7 | 4.00 | 5.42 | 5.9 | -4.00 | 0.50 | naip_2024_world_0.5m.jso | -1.30 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A2 bridge A2 fixed walkway **>1 m** | 8/8 | 3.90 | 5.41 | 5.9 | -2.45 | 0.50 | naip_2024_world_0.5m.jso | -2.00 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| E4 bridge E4 fixed walkway **>1 m** | 6/6 | 3.75 | 5.20 | 5.6 | +3.75 | 0.50 | naip_2024_world_0.5m.jso | +3.20 (0.60) | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| B18 bridge B18 fixed walkway | 2/2 | 3.65 | 4.57 | 4.8 | -3.65 | 0.50 | naip_2024_world_0.5m.jso | -5.15 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B9 bridge B9 fixed walkway **>1 m** | 5/5 | 3.60 | 5.54 | 5.9 | +0.40 | 0.50 | naip_2024_world_0.5m.jso | -2.60 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| B11 bridge B11 fixed walkway **>1 m** | 12/12 | 3.50 | 3.99 | 4.1 | -3.20 | 0.50 | naip_2024_world_0.5m.jso | -3.85 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G9 bridge G9 fixed walkway **>1 m** | 3/3 | 3.50 | 3.82 | 3.9 | -3.50 | 0.50 | naip_2024_world_0.5m.jso | -2.10 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A1 bridge A1 fixed walkway **>1 m** | 22/24 | 3.40 | 5.85 | 5.9 | -2.95 | 0.50 | naip_2024_world_0.5m.jso | -0.50 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A6 bridge A6 fixed walkway **>1 m** | 11/11 | 3.30 | 4.50 | 5.4 | -0.20 | 0.50 | naip_2024_world_0.5m.jso | +0.10 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A4 bridge A4 fixed walkway **>1 m** | 5/5 | 3.00 | 3.10 | 3.1 | +3.00 | 0.50 | naip_2024_world_0.5m.jso | +2.70 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| D8 bridge D8 fixed walkway **>1 m** | 4/4 | 2.90 | 2.97 | 3.0 | -2.90 | 0.50 | naip_2024_world_0.5m.jso | -3.35 (0.60) | [10-ba-D](10-ba-D.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| F13 bridge F13 fixed walkway **>1 m** | 5/5 | 2.80 | 3.84 | 4.2 | -2.80 | 0.50 | naip_2024_world_0.5m.jso | +0.80 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G12 bridge G12 fixed walkway | 2/3 | 2.80 | 3.04 | 3.1 | +2.80 | 0.50 | naip_2024_world_0.5m.jso | – | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| G13 bridge G13 fixed walkway **>1 m** | 9/9 | 2.80 | 5.52 | 5.6 | +1.70 | 0.50 | naip_2024_world_0.5m.jso | +3.20 (0.60) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| A8 bridge A8 fixed walkway **>1 m** | 6/6 | 2.25 | 3.55 | 4.6 | -0.30 | 0.50 | naip_2024_world_0.5m.jso | +1.70 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B17 bridge B17 fixed walkway | 2/3 | 2.20 | 3.48 | 3.8 | -1.60 | 0.50 | naip_2024_world_0.5m.jso | -0.95 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| E2 bridge E2 fixed walkway **>1 m** | 5/5 | 2.20 | 4.58 | 5.5 | -1.40 | 0.50 | naip_2024_world_0.5m.jso | +1.20 (0.60) | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| B26 bridge B26 fixed walkway **>1 m** | 21/21 | 2.10 | 4.80 | 5.2 | +2.10 | 0.50 | naip_2024_world_0.5m.jso | +0.20 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B24 bridge B24 fixed walkway **>1 m** | 10/10 | 2.00 | 3.79 | 4.6 | -1.45 | 0.50 | naip_2024_world_0.5m.jso | -1.50 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B27 bridge B27 fixed walkway **>1 m** | 22/22 | 2.00 | 3.28 | 4.3 | +0.70 | 0.50 | naip_2024_world_0.5m.jso | +1.05 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B25 bridge B25 fixed walkway **>1 m** | 8/8 | 1.90 | 5.42 | 5.7 | +1.55 | 0.50 | naip_2024_world_0.5m.jso | -0.40 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| F11 bridge F11 fixed walkway | 2/2 | 1.80 | 2.92 | 3.2 | -1.80 | 0.50 | naip_2024_world_0.5m.jso | -2.35 (0.60) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A8 bridge A8 fixed walkway | 2/2 | 1.75 | 2.91 | 3.2 | -1.45 | 0.50 | naip_2024_world_0.5m.jso | -2.80 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B14 bridge B14 fixed walkway **>1 m** | 4/4 | 1.75 | 5.06 | 5.9 | -1.55 | 0.50 | naip_2024_world_0.5m.jso | -2.70 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B7 bridge B7 fixed walkway **>1 m** | 11/13 | 1.70 | 2.00 | 2.3 | -1.70 | 0.50 | naip_2024_world_0.5m.jso | -1.40 (0.60) | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| B2 bridge B2 fixed walkway | 2/3 | 1.40 | 2.52 | 2.8 | -1.40 | 0.50 | naip_2024_world_0.5m.jso | -3.30 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B16 bridge B16 fixed walkway **>1 m** | 8/8 | 1.00 | 1.66 | 1.8 | -0.85 | 0.50 | naip_2024_world_0.5m.jso | -1.70 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B13 bridge B13 fixed walkway | 3/4 | 0.90 | 4.90 | 5.9 | +0.50 | 0.50 | naip_2024_world_0.5m.jso | +0.80 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| A10 bridge A10 fixed walkway | 5/5 | 0.80 | 1.30 | 1.3 | +0.80 | 0.50 | naip_2024_world_0.5m.jso | -2.60 (0.60) | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| A9 bridge A9 fixed walkway | 4/4 | 0.70 | 1.01 | 1.1 | +0.45 | 0.50 | naip_2024_world_0.5m.jso | +0.30 (0.60) | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| A2 bridge A2 fixed walkway | 4/4 | 0.45 | 3.02 | 4.1 | -0.25 | 0.50 | naip_2024_world_0.5m.jso | -0.00 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B5 bridge B5 fixed walkway | 5/5 | 0.40 | 1.00 | 1.2 | +0.40 | 0.50 | naip_2024_world_0.5m.jso | -3.40 (0.60) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B12 bridge B12 fixed walkway | 4/4 | 0.20 | 4.19 | 5.9 | -0.05 | 0.50 | naip_2024_world_0.5m.jso | -0.15 (0.60) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |

### bridge-rotunda (72 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| E5 bridge E5 rotunda | 1/1 | 4.98 | 4.98 | 5.0 | +4.98 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| G8 bridge G8 rotunda | 1/1 | 4.97 | 4.97 | 5.0 | +4.97 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| E9 bridge E9 rotunda | 1/1 | 4.97 | 4.97 | 5.0 | +4.97 | 0.50 | raster | – | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| D15 bridge D15 rotunda | 1/1 | 4.95 | 4.95 | 4.9 | +4.95 | 0.50 | raster | – | [10-ba-D](10-ba-D.png), [00-overview](00-overview.png) |
| A5 bridge A5 rotunda | 1/1 | 4.88 | 4.88 | 4.9 | +4.88 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| F11 bridge F11 rotunda | 1/1 | 4.83 | 4.83 | 4.8 | +4.83 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G5 bridge G5 rotunda | 1/1 | 4.75 | 4.75 | 4.8 | +4.75 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F13 bridge F13 rotunda | 1/1 | 4.70 | 4.70 | 4.7 | +4.70 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| E8 bridge E8 rotunda | 1/1 | 4.70 | 4.70 | 4.7 | +4.70 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| G7 bridge G7 rotunda | 1/1 | 4.70 | 4.70 | 4.7 | +4.70 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F13 bridge F13 rotunda | 1/1 | 4.68 | 4.68 | 4.7 | +4.68 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G10 bridge G10 rotunda | 1/1 | 4.55 | 4.55 | 4.5 | +4.55 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| G12 bridge G12 rotunda | 1/1 | 4.51 | 4.51 | 4.5 | +4.51 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| D8 bridge D8 rotunda | 1/1 | 4.37 | 4.37 | 4.4 | +4.37 | 0.50 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| B27 bridge B27 rotunda | 1/1 | 4.36 | 4.36 | 4.4 | +4.36 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G1 bridge G1 rotunda | 1/1 | 4.25 | 4.25 | 4.3 | +4.25 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| F20 bridge F20 rotunda | 1/1 | 4.24 | 4.24 | 4.2 | +4.24 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| B21 bridge B21 rotunda | 1/1 | 4.16 | 4.16 | 4.2 | +4.16 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A9 bridge A9 rotunda | 1/1 | 4.16 | 4.16 | 4.2 | +4.16 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| D5 bridge D5 rotunda | 1/1 | 4.16 | 4.16 | 4.2 | +4.16 | 0.50 | raster | – | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| G2 bridge G2 rotunda | 1/1 | 4.11 | 4.11 | 4.1 | +4.11 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A11 bridge A11 rotunda | 1/1 | 4.05 | 4.05 | 4.1 | +4.05 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| B8 bridge B8 rotunda | 1/1 | 3.98 | 3.98 | 4.0 | +3.98 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| A6 bridge A6 rotunda | 1/1 | 3.92 | 3.92 | 3.9 | +3.92 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G3 bridge G3 rotunda | 1/1 | 3.91 | 3.91 | 3.9 | +3.91 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| A8 bridge A8 rotunda | 1/1 | 3.89 | 3.89 | 3.9 | +3.89 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| F12 bridge F12 rotunda | 1/1 | 3.83 | 3.83 | 3.8 | +3.83 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F14 bridge F14 rotunda | 1/1 | 3.82 | 3.82 | 3.8 | +3.82 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G12 bridge G12 rotunda | 1/1 | 3.81 | 3.81 | 3.8 | +3.81 | 0.50 | raster | – | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| C8 bridge C8 rotunda | 1/1 | 3.71 | 3.71 | 3.7 | +3.71 | 0.50 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| A15 bridge A15 rotunda | 1/1 | 3.64 | 3.64 | 3.6 | +3.64 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| C3 bridge C3 rotunda | 1/1 | 3.64 | 3.64 | 3.6 | +3.64 | 0.50 | raster | – | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| B25 bridge B25 rotunda | 1/1 | 3.61 | 3.61 | 3.6 | +3.61 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| E7 bridge E7 rotunda | 1/1 | 3.54 | 3.54 | 3.5 | +3.54 | 0.50 | raster | – | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| E3 bridge E3 rotunda | 1/1 | 3.54 | 3.54 | 3.5 | +3.54 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| D12 bridge D12 rotunda | 1/1 | 3.48 | 3.48 | 3.5 | +3.48 | 0.50 | raster | – | [10-ba-D](10-ba-D.png), [00-overview](00-overview.png) |
| B22 bridge B22 rotunda | 1/1 | 3.47 | 3.47 | 3.5 | +3.47 | 0.50 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| F6 bridge F6 rotunda | 1/1 | 3.44 | 3.44 | 3.4 | +3.44 | 0.50 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| G5 bridge G5 rotunda | 1/1 | 3.42 | 3.42 | 3.4 | +3.42 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F16 bridge F16 rotunda | 1/1 | 3.36 | 3.36 | 3.4 | +3.36 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |

## Deviations from imagery - `google`

Source: Google Maps screenshots (owner, reference only, re-registered to NAIP) (Google imagery - reference only, never redistributed). Offsets are signed along the outward edge normal (+ = imaged edge outside / right of the model), in metres; `gsd` = ground resolution of the image the profile was read from; `alt` = the same samples read from the next-best image (NAIP: the other year; Google: another screenshot). Features flagged when the median |offset| > 1.0 m.

| class | features | measured | flagged (median > 1 m) | median of medians | median p90 | typical gsd | notes |
|---|---|---|---|---|---|---|---|
| approach-light-catwalk | 2 | 0 | 0 | – | – | – | lateral position of the imaged catwalk deck vs the modelled catwalk line |
| approach-light-crossbar | 2 | 2 | 2 | 4.20 | 6.28 | 0.57 | imaged crossbar end vs modelled end (+ = imaged longer) |
| approach-light-station | 2 | 2 | 2 | 1.55 | 6.31 | 0.57 | along-axis position of each imaged station over water |
| apron-edge | 2 | 2 | 2 | 6.77 | 8.60 | 0.78 |  |
| bridge-rotunda | 128 | 77 | 0 | 3.42 | 3.42 | 0.27 | automatic disc search (6 m radius; picks at the boundary count as not found), low confidence - read with the sheets |
| bridge-walkway | 47 | 47 | 42 | 2.85 | 4.78 | 0.28 |  |
| building | 39 | 33 | 32 | 3.65 | 8.01 | 0.50 | roof edge vs footprint: relief displacement (roofs lean away from nadir) + registration; see `shift`/`resid` columns. One feature per building; edges shared with the ramp-level complex belong to the part |
| emas-bed | 4 | 4 | 3 | 1.55 | 3.08 | 1.38 |  |
| extra-pavement | 259 | 238 | 200 | 2.60 | 5.20 | 1.07 | derived from the Google imagery (circular on `google`); checks the vectorisation |
| hold-line | 90 | 0 | 0 | – | – | – | needs <= 0.6 m/px |
| runway-edge-stripe | 8 | 4 | 1 | 0.80 | 2.51 | 0.57 | 0.91 m stripe |
| runway-end | 4 | 4 | 4 | 2.00 | 2.92 | 0.92 |  |
| runway-threshold | 8 | 2 | 0 | 0.63 | 0.93 | 0.57 | start of the stripe block (stripe-start rule) |
| runway-threshold-bar | 8 | 6 | 5 | 2.32 | 2.62 | 1.08 | imaged 10 ft bar vs the model bar (see the runway table above) |
| stand-leadin | 103 | 0 | 0 | – | – | – | lead-in paint: needs <= 0.35 m/px; often under parked aircraft |
| taxiway-centreline | 265 | 0 | 0 | – | – | – | 6 in paint: needs <= 0.35 m/px |
| taxiway-edge | 162 | 143 | 97 | 2.70 | 6.72 | 1.08 |  |

### runway-end (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28R pavement end **>1 m** | 13/13 | 3.10 | 3.48 | 6.3 | +3.10 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 10L pavement end **>1 m** | 13/13 | 2.30 | 3.52 | 3.7 | +2.30 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 10R pavement end **>1 m** | 11/13 | 1.70 | 2.20 | 2.8 | +1.70 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 28L pavement end **>1 m** | 13/13 | 1.60 | 2.36 | 2.7 | +1.60 | 0.57 | 1a26bbeb | +4.45 (1.61) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-threshold (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28R threshold stripes (start 6.1 m past threshold) | 16/16 | 0.90 | 1.25 | 1.4 | -0.90 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28L threshold stripes (start 6.1 m past threshold) | 16/16 | 0.35 | 0.60 | 0.7 | -0.35 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### runway-threshold-bar (6 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28R threshold bar (model: approach side, centre -1.52 m; displaced 91.4 m) **>1 m** | 10/10 | 3.80 | 3.91 | 4.0 | +3.80 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28L threshold bar (model: approach side, centre -1.52 m; displaced 91.4 m) **>1 m** | 10/10 | 3.45 | 3.60 | 3.6 | +3.45 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 1R threshold bar (model: approach side, centre -1.52 m; displaced 170.7 m) **>1 m** | 9/10 | 2.40 | 2.64 | 2.8 | +2.40 | 1.08 | 2f0be03d | +2.95 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| RWY 1L threshold bar (model: approach side, centre -1.52 m; displaced 195.1 m) **>1 m** | 10/10 | 2.25 | 2.61 | 2.7 | +2.25 | 1.08 | 2f0be03d | +2.90 (1.15) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| RWY 10R threshold bar (model: none drawn) | 1/10 | 2.20 | 2.20 | 2.2 | +2.20 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| RWY 10L threshold bar (model: none drawn) **>1 m** | 5/10 | 1.20 | 1.36 | 1.4 | +1.20 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |

### runway-edge-stripe (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 10L/28R edge stripe (south/east side) **>1 m** | 32/356 | 1.10 | 2.69 | 6.5 | -1.10 | 0.58 | 1a26bbeb, bc91df95 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| RWY 10R/28L edge stripe (north/west side) | 42/341 | 1.00 | 2.49 | 2.6 | +0.40 | 0.57 | 1a26bbeb, bc91df95 | – | [00-overview](00-overview.png) |
| RWY 10L/28R edge stripe (north/west side) | 22/356 | 0.60 | 2.19 | 2.4 | +0.50 | 0.57 | 1a26bbeb | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| RWY 10R/28L edge stripe (south/east side) | 48/341 | 0.30 | 2.53 | 5.4 | +0.10 | 0.57 | 1a26bbeb, bc91df95 | – | [00-overview](00-overview.png) |

### emas-bed (4 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| EMAS bed beyond RWY 19L **>1 m** | 70/126 | 3.10 | 4.51 | 5.3 | -1.85 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| EMAS bed beyond RWY 1L **>1 m** | 132/132 | 1.90 | 2.60 | 9.1 | +0.30 | 1.08 | 103723b0, 2f0be03d | +0.15 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| EMAS bed beyond RWY 19R **>1 m** | 65/126 | 1.20 | 3.46 | 4.3 | +0.80 | 1.61 | c1064033 | +6.10 (3.18) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| EMAS bed beyond RWY 1R | 117/118 | 0.90 | 2.70 | 6.7 | -0.00 | 1.15 | 103723b0, 2f0be03d | -0.15 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |

### approach-light-station (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28L MALSR approach-light stations over water (19, 213-762 m from the threshold) **>1 m** | 3/19 | 1.70 | 7.78 | 9.3 | +1.70 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28R ALSF2 approach-light stations over water (19, 211-760 m from the threshold) **>1 m** | 3/19 | 1.40 | 4.84 | 5.7 | +1.40 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### approach-light-crossbar (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| RWY 28R approach-light crossbars over water (7), imaged ends vs modelled ends **>1 m** | 6/14 | 5.80 | 9.95 | 11.5 | -5.80 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| RWY 28L approach-light crossbars over water (2), imaged ends vs modelled ends **>1 m** | 1/4 | 2.60 | 2.60 | 2.6 | +2.60 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |

### building (33 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | fit shift | resid median | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Garage A | 2/9 | 9.35 | 9.39 | 9.4 | +0.05 | 0.55 | 0af09b78 | – | – | – | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Grand Hyatt Hotel AirTrain Station **>1 m** | 69/73 | 6.90 | 9.12 | 9.7 | +1.60 | 1.07 | 35809e3e | – | 1.42 | 6.54 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Super Bay Hangar Building **>1 m** | 187/292 | 6.60 | 8.00 | 9.1 | +6.60 | 1.61 | c1064033, c9ff55e8 | +2.50 (3.18) | 7.37 | 3.23 | [30-rwy-19R](30-rwy-19R.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Grand Hyatt Hotel **>1 m** | 103/114 | 6.20 | 9.04 | 9.5 | +0.70 | 1.07 | 35809e3e | -1.50 (3.18) | 1.97 | 5.76 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Central Parking Garage **>1 m** | 408/427 | 5.30 | 9.30 | 9.9 | -1.40 | 0.42 | 4637f855, e6f569c1 | +0.45 (0.55) | 0.70 | 5.36 | [20-itb-tower](20-itb-tower.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Westfield Road AirTrain Station (Outbound)g **>1 m** | 50/56 | 4.65 | 7.93 | 9.3 | -3.30 | 1.27 | c9ff55e8 | – | 2.84 | 3.07 | [00-overview](00-overview.png) |
| International Terminal (G) AirTrain Station **>1 m** | 14/15 | 4.60 | 8.21 | 9.7 | +3.25 | 0.25 | 0af09b78, d82848c4 | +3.20 (0.55) | 3.73 | 4.42 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Boarding Area E **>1 m** | 150/153 | 4.50 | 7.41 | 9.7 | -2.80 | 0.24 | 4637f855, c235f3b8 | -0.30 (0.42) | 2.75 | 4.43 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Terminal One AirTrain Station **>1 m** | 24/30 | 4.50 | 8.64 | 9.7 | -2.10 | 0.42 | 4637f855 | -0.75 (0.55) | – | – | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Terminal 2 **>1 m** | 253/257 | 4.40 | 8.78 | 9.8 | +2.90 | 0.24 | 03dcd4ae, 4637f855, bf5c7afc, c235f3b8 | +3.10 (0.42) | 2.23 | 3.63 | [10-ba-D](10-ba-D.png), [20-itb-tower](20-itb-tower.png) |
| Terminal 3 **>1 m** | 289/297 | 4.30 | 7.80 | 9.7 | +0.70 | 0.50 | 39176bb8, 4637f855, c235f3b8, e6f569c1 | +0.80 (0.55) | 3.34 | 2.27 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Garage G **>1 m** | 301/302 | 4.10 | 9.00 | 9.8 | +2.70 | 1.07 | 151ec51d, 35809e3e | +4.55 (1.07) | 3.59 | 3.97 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| West Field Road AirTrain Station (Outbound) **>1 m** | 73/80 | 4.10 | 7.78 | 9.3 | -3.70 | 1.27 | c9ff55e8 | – | 1.77 | 4.93 | [00-overview](00-overview.png) |
| Terminal complex ramp level **>1 m** | 86/87 | 4.00 | 8.15 | 9.7 | +1.35 | 0.27 | 39176bb8, 4637f855, c235f3b8, e6f569c1 | +1.45 (0.50) | 1.72 | 3.48 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Terminal complex ramp level **>1 m** | 80/80 | 3.85 | 8.01 | 9.8 | +2.10 | 0.27 | 0af09b78, 151ec51d, c9ff55e8, d82848c4, e6f569c1 | +1.60 (0.55) | 1.88 | 3.48 | [20-itb-tower](20-itb-tower.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Westfield Road AirTrain Station (Inbound) **>1 m** | 66/69 | 3.75 | 9.05 | 9.4 | -2.80 | 1.27 | c9ff55e8 | +2.00 (3.18) | – | – | [00-overview](00-overview.png) |
| International Terminal **>1 m** | 356/381 | 3.65 | 8.30 | 9.7 | +2.10 | 0.50 | 0af09b78, 151ec51d, 35809e3e, d82848c4, e6f569c1 | +2.40 (1.07) | 2.39 | 2.40 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| Terminal Three AirTrain Station **>1 m** | 10/32 | 3.55 | 8.05 | 9.4 | +0.45 | 0.50 | e6f569c1 | -2.30 (0.55) | – | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Terminal Two AirTrain Station **>1 m** | 11/27 | 3.50 | 4.00 | 4.3 | +3.50 | 0.42 | 4637f855 | +3.70 (0.55) | – | – | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| Harvey Milk Terminal 1 **>1 m** | 338/340 | 3.45 | 8.80 | 9.7 | -0.75 | 0.50 | 03dcd4ae, 0af09b78, 4637f855, b1d51b0f, e6f569c1 | -1.00 (1.07) | 2.60 | 4.00 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| West Field Road AirTrain Station (Inbound) **>1 m** | 82/85 | 3.05 | 6.10 | 8.2 | -1.95 | 1.27 | c9ff55e8 | +2.20 (3.18) | – | – | [00-overview](00-overview.png) |
| Garage A **>1 m** | 245/289 | 2.80 | 8.50 | 9.7 | +1.10 | 1.07 | 0af09b78, 35809e3e, 8b334c52, d82848c4 | +5.20 (1.07) | 2.97 | 2.71 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| Terminal 3 Air Train Station **>1 m** | 15/15 | 2.80 | 3.06 | 3.1 | +2.80 | 0.50 | e6f569c1 | +2.80 (0.55) | – | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| Boarding Area B **>1 m** | 435/438 | 2.60 | 7.20 | 9.8 | -1.60 | 0.28 | 0af09b78, 2f0be03d, b1d51b0f | -1.60 (0.55) | 3.25 | 2.83 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Garage G AirTrain Station **>1 m** | 107/119 | 2.60 | 7.54 | 9.3 | +1.90 | 1.07 | 35809e3e | +3.90 (3.18) | 3.19 | 1.56 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Boarding Area C **>1 m** | 162/162 | 2.40 | 8.89 | 9.7 | +0.95 | 0.16 | 03dcd4ae | +2.10 (0.42) | 0.69 | 2.27 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Boarding Area A **>1 m** | 306/307 | 2.30 | 8.75 | 9.8 | +0.80 | 0.25 | d82848c4 | +0.90 (0.55) | 1.94 | 2.22 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| Boarding Area F **>1 m** | 512/513 | 2.30 | 6.30 | 9.9 | +0.60 | 0.27 | 39176bb8, c235f3b8, e6f569c1 | +0.80 (0.50) | 1.12 | 1.39 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| Terminal complex ramp level **>1 m** | 134/137 | 2.10 | 8.01 | 9.8 | +0.80 | 0.28 | 03dcd4ae, 0af09b78, 2f0be03d, 4637f855, b1d51b0f | +1.70 (0.55) | 0.51 | 2.15 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| Boarding Area G **>1 m** | 362/372 | 1.50 | 6.89 | 9.7 | +0.80 | 0.27 | 151ec51d, c9ff55e8, e6f569c1 | +2.70 (0.50) | 2.36 | 1.31 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| Air Traffic Control Tower **>1 m** | 25/25 | 1.50 | 5.46 | 9.7 | +1.50 | 0.16 | 03dcd4ae | +2.20 (0.42) | 3.48 | 0.54 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| Boarding Area D **>1 m** | 247/248 | 1.40 | 6.70 | 9.6 | +1.40 | 0.24 | 4637f855, bf5c7afc | +1.90 (0.42) | 1.14 | 1.51 | [10-ba-D](10-ba-D.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Consolidated Administration Campus **>1 m** | 157/158 | 1.10 | 5.84 | 9.5 | +0.90 | 1.27 | c9ff55e8 | +2.85 (3.18) | 2.67 | 1.30 | [40-apron-4-north-west](40-apron-4-north-west.png), [00-overview](00-overview.png) |

### taxiway-edge (143 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| Taxiway Z | 1/8 | 9.30 | 9.30 | 9.3 | +9.30 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C/D **>1 m** | 10/24 | 9.00 | 9.20 | 9.2 | -9.00 | 0.93 | 59be8a98 | +1.00 (1.27) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway E | 1/7 | 9.00 | 9.00 | 9.0 | -9.00 | 0.93 | 59be8a98 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway C1 **>1 m** | 3/14 | 8.90 | 8.98 | 9.0 | +8.90 | 1.27 | c9ff55e8 | +5.55 (3.18) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C **>1 m** | 20/20 | 8.85 | 9.60 | 9.6 | +8.85 | 0.57 | 1a26bbeb | – | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| Taxiway R **>1 m** | 9/26 | 8.80 | 9.22 | 9.3 | +8.80 | 0.93 | 59be8a98 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway Z **>1 m** | 19/46 | 8.80 | 9.22 | 9.4 | +8.80 | 1.27 | 59be8a98, c9ff55e8 | +8.30 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway A/B/F **>1 m** | 5/5 | 8.70 | 9.20 | 9.4 | +8.70 | 0.93 | 59be8a98 | +1.20 (1.08) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Taxiway H **>1 m** | 60/131 | 8.70 | 9.20 | 9.4 | +8.70 | 1.08 | 2f0be03d | +8.90 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| Taxiway B **>1 m** | 16/19 | 8.55 | 9.05 | 9.2 | -8.55 | 1.07 | 35809e3e | -7.35 (1.08) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway Z/Z2 **>1 m** | 16/44 | 8.55 | 8.95 | 9.0 | +8.55 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway E | 1/21 | 8.40 | 8.40 | 8.4 | +8.40 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| Taxiway C/P **>1 m** | 3/41 | 8.20 | 8.44 | 8.5 | +8.20 | 1.61 | c1064033 | – | [00-overview](00-overview.png) |
| Taxiway E **>1 m** | 3/35 | 8.20 | 8.36 | 8.4 | +8.20 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| Taxiway F1 | 2/3 | 7.85 | 8.69 | 8.9 | +1.05 | 1.08 | 2f0be03d | +2.40 (1.15) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Taxiway B **>1 m** | 15/16 | 7.80 | 8.26 | 8.6 | +7.80 | 0.58 | bc91df95 | +7.40 (0.93) | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Taxiway L/C **>1 m** | 3/16 | 7.80 | 8.44 | 8.6 | +7.80 | 1.08 | 2f0be03d | +8.10 (1.61) | [00-overview](00-overview.png) |
| Taxiway E/C | 1/17 | 7.70 | 7.70 | 7.7 | -7.70 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| Taxiway P **>1 m** | 4/12 | 7.70 | 8.20 | 8.2 | +7.70 | 1.61 | c1064033 | +7.70 (3.18) | [00-overview](00-overview.png) |
| Taxiway Z/S2 | 2/6 | 7.60 | 7.76 | 7.8 | -7.60 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway V **>1 m** | 12/15 | 7.35 | 8.29 | 8.4 | +7.35 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| Taxiway C/N **>1 m** | 14/29 | 7.05 | 8.48 | 8.8 | -7.05 | 1.61 | c1064033 | – | [30-rwy-28R](30-rwy-28R.png), [00-overview](00-overview.png) |
| Taxiway C **>1 m** | 7/52 | 7.00 | 8.14 | 8.2 | -7.00 | 1.61 | c1064033 | – | [00-overview](00-overview.png) |
| Taxiway F1 **>1 m** | 13/30 | 7.00 | 7.66 | 7.9 | -3.30 | 1.08 | 2f0be03d | -2.55 (1.15) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Taxiway R/Z **>1 m** | 8/14 | 6.95 | 9.20 | 9.2 | +2.25 | 0.93 | 59be8a98 | +0.55 (1.27) | [30-rwy-10R](30-rwy-10R.png), [40-apron-4-north-west](40-apron-4-north-west.png) |
| Taxiway D **>1 m** | 3/11 | 6.90 | 7.94 | 8.2 | +6.40 | 0.58 | bc91df95 | +3.90 (0.93) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway P | 2/33 | 6.90 | 7.38 | 7.5 | +6.90 | 1.61 | c1064033 | – | [00-overview](00-overview.png) |
| Taxiway F/F1/L **>1 m** | 10/20 | 6.60 | 8.81 | 8.9 | +2.15 | 1.08 | 2f0be03d | -0.10 (1.15) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Taxiway B/E **>1 m** | 3/7 | 6.60 | 7.32 | 7.5 | +6.60 | 0.93 | 4637f855, 59be8a98 | +1.40 (1.08) | [00-overview](00-overview.png) |
| Taxiway H **>1 m** | 4/8 | 6.55 | 8.16 | 8.4 | +6.55 | 1.08 | 2f0be03d | +7.85 (1.15) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| Taxiway F **>1 m** | 9/26 | 6.50 | 8.42 | 8.9 | -6.50 | 1.08 | 2f0be03d | -6.10 (1.15) | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| Taxiway K **>1 m** | 11/11 | 6.50 | 8.00 | 9.4 | +6.50 | 0.58 | bc91df95 | +5.95 (0.93) | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| Taxiway G **>1 m** | 8/26 | 6.35 | 8.80 | 8.8 | -0.20 | 1.08 | 2f0be03d | +1.00 (1.15) | [30-rwy-1L](30-rwy-1L.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| Taxiway S4/S | 1/11 | 6.20 | 6.20 | 6.2 | +6.20 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway B/D **>1 m** | 7/8 | 6.10 | 6.82 | 7.3 | +1.70 | 0.58 | bc91df95 | +4.30 (0.93) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| Taxiway R **>1 m** | 25/26 | 6.00 | 9.06 | 9.1 | +1.60 | 0.93 | 59be8a98 | +6.40 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway C **>1 m** | 3/118 | 5.90 | 6.78 | 7.0 | -5.90 | 1.61 | c1064033 | – | [00-overview](00-overview.png) |
| Taxiway C/R **>1 m** | 10/11 | 5.75 | 6.36 | 7.8 | +1.55 | 0.93 | 59be8a98, c9ff55e8 | +5.90 (1.27) | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway S3 | 1/7 | 5.70 | 5.70 | 5.7 | +5.70 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| Taxiway B **>1 m** | 41/44 | 5.60 | 9.50 | 9.5 | +3.40 | 0.93 | 4637f855, 59be8a98 | -0.85 (1.07) | [00-overview](00-overview.png) |

### apron-edge (2 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| apron outline #0 **>1 m** | 8/10 | 7.15 | 8.09 | 8.3 | -4.70 | 1.07 | 151ec51d, 35809e3e | -3.50 (3.18) | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| apron outline #1 **>1 m** | 45/57 | 6.40 | 9.12 | 9.6 | +1.20 | 0.50 | 0af09b78, 151ec51d, 2f0be03d, 39176bb8, b1d51b0f | -0.05 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |

### extra-pavement (238 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| extra pavement #51 | 1/8 | 8.90 | 8.90 | 8.9 | +8.90 | 1.27 | c9ff55e8 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #15 **>1 m** | 7/9 | 8.80 | 8.94 | 9.0 | +8.80 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| extra pavement #102 **>1 m** | 6/77 | 8.65 | 8.85 | 8.9 | +8.65 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #333 **>1 m** | 10/10 | 8.55 | 8.93 | 9.2 | -4.05 | 1.08 | 2f0be03d | +7.20 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #55 | 2/7 | 8.45 | 8.57 | 8.6 | +0.15 | 1.27 | c9ff55e8 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #117 **>1 m** | 9/35 | 8.40 | 9.24 | 9.4 | +0.90 | 0.93 | 59be8a98, c9ff55e8 | +2.60 (1.27) | [30-rwy-10R](30-rwy-10R.png), [40-apron-4-north-west](40-apron-4-north-west.png) |
| extra pavement #287 | 1/9 | 8.40 | 8.40 | 8.4 | +8.40 | 1.08 | 2f0be03d | +3.95 (1.15) | [30-rwy-1L](30-rwy-1L.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| extra pavement #57 **>1 m** | 10/41 | 8.20 | 8.40 | 8.4 | +8.20 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #64 **>1 m** | 4/23 | 8.20 | 8.51 | 8.6 | +8.20 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [00-overview](00-overview.png) |
| extra pavement #144 | 2/6 | 8.10 | 8.18 | 8.2 | +0.10 | 0.93 | 59be8a98 | -1.05 (1.17) | [30-rwy-10R](30-rwy-10R.png), [40-apron-4-north-west](40-apron-4-north-west.png) |
| extra pavement #191 **>1 m** | 3/12 | 8.00 | 8.48 | 8.6 | +8.00 | 1.27 | c9ff55e8 | – | [00-overview](00-overview.png) |
| extra pavement #322 **>1 m** | 8/9 | 7.70 | 8.43 | 8.5 | +7.70 | 1.08 | 2f0be03d | +6.20 (1.15) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| extra pavement #36 **>1 m** | 9/18 | 7.60 | 8.26 | 8.9 | +7.60 | 1.61 | c1064033 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #63 **>1 m** | 7/18 | 7.40 | 8.38 | 9.1 | +7.40 | 0.93 | 59be8a98 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #194 **>1 m** | 19/23 | 7.40 | 9.40 | 9.5 | -4.20 | 0.27 | 39176bb8 | -6.80 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| extra pavement #161 **>1 m** | 8/8 | 7.25 | 9.50 | 9.5 | -2.65 | 0.50 | e6f569c1 | +3.65 (0.93) | [10-ba-F](10-ba-F.png), [00-overview](00-overview.png) |
| extra pavement #183 **>1 m** | 16/44 | 7.20 | 8.55 | 9.1 | +7.20 | 1.27 | c9ff55e8 | – | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| extra pavement #208 | 2/6 | 6.80 | 8.32 | 8.7 | -6.80 | 1.27 | c9ff55e8 | – | [00-overview](00-overview.png) |
| extra pavement #332 **>1 m** | 3/4 | 6.80 | 7.52 | 7.7 | +6.80 | 1.08 | 2f0be03d | +2.85 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #145 **>1 m** | 3/7 | 6.70 | 7.26 | 7.4 | +6.70 | 0.93 | 59be8a98 | +2.50 (1.27) | [30-rwy-10R](30-rwy-10R.png), [40-apron-4-north-west](40-apron-4-north-west.png) |
| extra pavement #6 **>1 m** | 9/102 | 6.60 | 6.92 | 7.0 | +6.60 | 3.18 | 8b334c52 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| extra pavement #58 **>1 m** | 3/11 | 6.60 | 7.40 | 7.6 | +6.60 | 1.27 | c9ff55e8 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #179 **>1 m** | 6/6 | 6.50 | 7.45 | 7.9 | -2.55 | 0.58 | bc91df95 | -2.60 (0.93) | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| extra pavement #307 **>1 m** | 4/4 | 6.50 | 7.12 | 7.3 | +6.50 | 0.57 | 1a26bbeb | +8.30 (1.61) | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| extra pavement #331 **>1 m** | 14/14 | 6.45 | 7.55 | 7.9 | +6.45 | 1.08 | 2f0be03d | +5.05 (1.15) | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| extra pavement #38 **>1 m** | 14/30 | 6.30 | 7.44 | 8.3 | +6.30 | 1.27 | c9ff55e8 | – | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| extra pavement #140 **>1 m** | 82/148 | 6.15 | 8.49 | 8.9 | +6.15 | 1.61 | c1064033 | -3.80 (3.18) | [00-overview](00-overview.png) |
| extra pavement #321 **>1 m** | 5/5 | 6.10 | 7.34 | 7.9 | -6.10 | 0.28 | 0af09b78, b1d51b0f | +2.10 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| extra pavement #218 | 1/7 | 5.90 | 5.90 | 5.9 | +5.90 | 3.18 | 8b334c52 | – | [00-overview](00-overview.png) |
| extra pavement #39 **>1 m** | 5/9 | 5.80 | 6.66 | 6.9 | +5.80 | 1.61 | c1064033 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #197 **>1 m** | 24/50 | 5.80 | 7.74 | 8.5 | +5.55 | 1.27 | c9ff55e8 | – | [00-overview](00-overview.png) |
| extra pavement #79 **>1 m** | 22/37 | 5.75 | 8.07 | 8.4 | +5.15 | 1.27 | c9ff55e8 | – | [40-apron-4-north-west](40-apron-4-north-west.png), [00-overview](00-overview.png) |
| extra pavement #91 **>1 m** | 15/19 | 5.70 | 9.26 | 9.3 | +2.40 | 0.93 | 59be8a98 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #178 **>1 m** | 11/18 | 5.60 | 6.00 | 6.3 | +5.60 | 0.58 | 59be8a98, bc91df95 | +5.40 (0.93) | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #52 | 2/7 | 5.55 | 7.75 | 8.3 | -5.55 | 1.61 | c1064033 | – | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #26 **>1 m** | 116/263 | 5.45 | 8.90 | 9.5 | +3.80 | 0.93 | 59be8a98, c9ff55e8 | – | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| extra pavement #73 **>1 m** | 18/22 | 5.35 | 5.96 | 6.6 | +5.35 | 1.61 | c1064033 | +0.70 (3.18) | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| extra pavement #11 **>1 m** | 15/39 | 5.30 | 6.86 | 7.0 | -4.00 | 3.18 | 8b334c52 | – | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| extra pavement #2 **>1 m** | 31/205 | 5.30 | 7.30 | 7.7 | +4.70 | 3.18 | 8b334c52 | – | [40-apron-3-north-west](40-apron-3-north-west.png), [00-overview](00-overview.png) |
| extra pavement #156 | 2/4 | 5.20 | 7.12 | 7.6 | +5.20 | 0.58 | bc91df95 | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |

### bridge-walkway (47 measured, worst first)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| G9 bridge G9 fixed walkway **>1 m** | 3/3 | 5.90 | 5.90 | 5.9 | -5.90 | 0.27 | 151ec51d | -4.00 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F11 bridge F11 fixed walkway **>1 m** | 7/7 | 5.40 | 5.90 | 5.9 | -4.80 | 0.27 | 39176bb8 | -5.00 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G13 bridge G13 fixed walkway **>1 m** | 7/7 | 5.20 | 5.90 | 5.9 | +5.20 | 0.50 | 151ec51d, e6f569c1 | +1.30 (1.07) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| B11S bridge B11 fixed walkway **>1 m** | 3/3 | 5.10 | 5.42 | 5.5 | -5.10 | 0.28 | b1d51b0f | -2.80 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B23 bridge B23 fixed walkway **>1 m** | 6/7 | 4.75 | 5.85 | 5.9 | -1.75 | 0.28 | b1d51b0f | +0.50 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B18 bridge B18 fixed walkway | 2/2 | 4.50 | 5.38 | 5.6 | +4.50 | 0.42 | 0af09b78, b1d51b0f | +4.45 (0.81) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| D8 bridge D8 fixed walkway **>1 m** | 4/4 | 4.40 | 4.78 | 4.9 | -4.40 | 0.24 | bf5c7afc | -4.85 (0.42) | [10-ba-D](10-ba-D.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| A1 bridge A1 fixed walkway **>1 m** | 21/26 | 4.30 | 5.20 | 5.9 | -3.50 | 0.25 | d82848c4 | -2.60 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A11 bridge A11 fixed walkway **>1 m** | 3/3 | 4.10 | 5.46 | 5.8 | -4.10 | 0.25 | d82848c4 | -0.30 (0.55) | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| A1 bridge A1 fixed walkway **>1 m** | 20/24 | 4.10 | 5.81 | 5.9 | -3.25 | 0.25 | 0af09b78, d82848c4 | -2.30 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G10 bridge G10 fixed walkway **>1 m** | 5/5 | 3.90 | 5.10 | 5.7 | -3.10 | 0.50 | e6f569c1 | +1.25 (1.07) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| G10 bridge G10 fixed walkway **>1 m** | 8/8 | 3.85 | 5.07 | 5.7 | +1.90 | 0.50 | e6f569c1 | +0.30 (1.07) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| F11 bridge F11 fixed walkway | 2/2 | 3.80 | 4.68 | 4.9 | -3.80 | 0.27 | 39176bb8 | -2.80 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| B19 bridge B19 fixed walkway **>1 m** | 12/12 | 3.75 | 5.90 | 5.9 | +2.20 | 0.28 | b1d51b0f | +1.90 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A6 bridge A6 fixed walkway **>1 m** | 11/11 | 3.60 | 5.80 | 5.9 | -3.60 | 0.25 | d82848c4 | -3.40 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B9 bridge B9 fixed walkway **>1 m** | 5/5 | 3.60 | 4.70 | 5.1 | +2.20 | 0.28 | b1d51b0f | +4.30 (0.55) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| A8 bridge A8 fixed walkway **>1 m** | 6/6 | 3.45 | 5.70 | 5.9 | +2.40 | 0.25 | d82848c4 | +0.85 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B20 bridge B20 fixed walkway **>1 m** | 11/11 | 3.30 | 4.80 | 5.2 | +3.30 | 0.28 | b1d51b0f | +4.30 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A2 bridge A2 fixed walkway **>1 m** | 4/4 | 3.20 | 3.44 | 3.5 | -3.20 | 0.25 | d82848c4 | -3.00 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A2 bridge A2 fixed walkway **>1 m** | 8/8 | 3.20 | 5.02 | 5.3 | +3.20 | 0.25 | d82848c4 | +3.15 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B25 bridge B25 fixed walkway **>1 m** | 8/8 | 3.20 | 4.45 | 4.8 | +3.20 | 0.28 | b1d51b0f | +4.05 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B14 bridge B14 fixed walkway **>1 m** | 4/4 | 3.10 | 4.85 | 5.3 | +3.10 | 0.55 | 0af09b78 | +4.70 (1.07) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A10 bridge A10 fixed walkway **>1 m** | 5/5 | 2.90 | 3.54 | 3.7 | +2.90 | 0.25 | d82848c4 | +2.90 (0.55) | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| E4 bridge E4 fixed walkway **>1 m** | 6/6 | 2.85 | 4.90 | 5.9 | +2.85 | 0.24 | c235f3b8 | +3.65 (0.42) | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| B27 bridge B27 fixed walkway **>1 m** | 22/22 | 2.80 | 5.20 | 5.9 | +2.35 | 0.28 | b1d51b0f | +3.10 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B26 bridge B26 fixed walkway **>1 m** | 21/21 | 2.60 | 5.00 | 5.9 | +2.20 | 0.28 | b1d51b0f | +3.10 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G13 bridge G13 fixed walkway **>1 m** | 9/9 | 2.50 | 4.46 | 5.9 | -2.50 | 0.27 | 151ec51d, e6f569c1 | +3.00 (0.50) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| B11 bridge B11 fixed walkway **>1 m** | 12/12 | 2.45 | 3.99 | 4.1 | -2.45 | 0.28 | b1d51b0f | +0.45 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B12 bridge B12 fixed walkway **>1 m** | 3/4 | 2.40 | 3.28 | 3.5 | +2.40 | 0.28 | b1d51b0f | +3.35 (0.55) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| B2 bridge B2 fixed walkway **>1 m** | 3/3 | 2.20 | 2.28 | 2.3 | -1.50 | 0.55 | 0af09b78 | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A8 bridge A8 fixed walkway | 2/2 | 2.15 | 2.83 | 3.0 | +2.15 | 0.25 | d82848c4 | +2.10 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| F13 bridge F13 fixed walkway **>1 m** | 5/5 | 2.10 | 4.32 | 5.0 | -2.10 | 0.27 | 39176bb8 | -2.70 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A9 bridge A9 fixed walkway **>1 m** | 4/4 | 2.05 | 3.54 | 3.6 | +1.65 | 0.25 | d82848c4 | +1.30 (0.55) | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| B24 bridge B24 fixed walkway **>1 m** | 10/10 | 2.00 | 5.72 | 5.9 | +1.25 | 0.28 | b1d51b0f | +2.90 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A4 bridge A4 fixed walkway **>1 m** | 5/5 | 2.00 | 2.30 | 2.3 | +2.00 | 0.25 | d82848c4 | +3.70 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A6 bridge A6 fixed walkway **>1 m** | 6/6 | 2.00 | 4.10 | 5.5 | +0.95 | 0.25 | d82848c4 | +1.10 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B7 bridge B7 fixed walkway **>1 m** | 13/13 | 2.00 | 2.94 | 4.9 | +1.60 | 0.28 | b1d51b0f | -4.10 (0.55) | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| B17 bridge B17 fixed walkway **>1 m** | 3/3 | 2.00 | 4.64 | 5.3 | +2.00 | 0.28 | b1d51b0f | +4.80 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| A13 bridge A13 fixed walkway **>1 m** | 5/5 | 1.90 | 4.78 | 5.1 | -1.90 | 0.25 | d82848c4 | -2.30 (0.55) | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| G12 bridge G12 fixed walkway **>1 m** | 3/3 | 1.90 | 5.10 | 5.9 | +1.90 | 0.27 | 151ec51d | +5.80 (0.50) | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| E2 bridge E2 fixed walkway **>1 m** | 5/5 | 1.50 | 2.60 | 3.0 | -0.60 | 0.24 | c235f3b8 | -2.10 (0.50) | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| G9 bridge G9 fixed walkway **>1 m** | 8/8 | 1.30 | 4.22 | 5.2 | -0.05 | 0.27 | 151ec51d | -1.85 (0.50) | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| C1 bridge C1 fixed walkway **>1 m** | 3/3 | 1.20 | 4.96 | 5.9 | +1.20 | 0.42 | 4637f855 | +3.60 (0.55) | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| B5 bridge B5 fixed walkway **>1 m** | 5/5 | 1.10 | 3.82 | 5.5 | +1.10 | 0.55 | 0af09b78 | +0.40 (1.07) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B8 bridge B8 fixed walkway **>1 m** | 4/4 | 1.05 | 3.18 | 3.9 | -0.20 | 0.28 | b1d51b0f | -2.80 (0.55) | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| B13 bridge B13 fixed walkway | 4/4 | 1.00 | 1.68 | 1.8 | +0.50 | 0.28 | b1d51b0f | +3.85 (0.55) | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| B16 bridge B16 fixed walkway | 8/8 | 0.50 | 1.53 | 2.3 | -0.40 | 0.28 | b1d51b0f | +2.25 (0.55) | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |

### bridge-rotunda (77 measured, worst first, top 40)

| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) | sheet |
|---|---|---|---|---|---|---|---|---|---|
| G10 bridge G10 rotunda | 1/1 | 4.98 | 4.98 | 5.0 | +4.98 | 0.27 | raster | – | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| E6 bridge E6 rotunda | 1/1 | 4.97 | 4.97 | 5.0 | +4.97 | 0.24 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| C5 bridge C5 rotunda | 1/1 | 4.90 | 4.90 | 4.9 | +4.90 | 0.16 | raster | – | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| A6 bridge A6 rotunda | 1/1 | 4.88 | 4.88 | 4.9 | +4.88 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G5 bridge G5 rotunda | 1/1 | 4.81 | 4.81 | 4.8 | +4.81 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| E10 bridge E10 rotunda | 1/1 | 4.74 | 4.74 | 4.7 | +4.74 | 0.24 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| A8 bridge A8 rotunda | 1/1 | 4.73 | 4.73 | 4.7 | +4.73 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| B18 bridge B18 rotunda | 1/1 | 4.70 | 4.70 | 4.7 | +4.70 | 0.28 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| C1 bridge C1 rotunda | 1/1 | 4.70 | 4.70 | 4.7 | +4.70 | 0.42 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| F13 bridge F13 rotunda | 1/1 | 4.61 | 4.61 | 4.6 | +4.61 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| D15 bridge D15 rotunda | 1/1 | 4.61 | 4.61 | 4.6 | +4.61 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [00-overview](00-overview.png) |
| D3 bridge D3 rotunda | 1/1 | 4.55 | 4.55 | 4.6 | +4.55 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| G13 bridge G13 rotunda | 1/1 | 4.44 | 4.44 | 4.4 | +4.44 | 0.27 | raster | – | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| C9 bridge C9 rotunda | 1/1 | 4.39 | 4.39 | 4.4 | +4.39 | 0.16 | raster | – | [10-ba-C](10-ba-C.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| E9 bridge E9 rotunda | 1/1 | 4.34 | 4.34 | 4.3 | +4.34 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| F11 bridge F11 rotunda | 1/1 | 4.34 | 4.34 | 4.3 | +4.34 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G7 bridge G7 rotunda | 1/1 | 4.34 | 4.34 | 4.3 | +4.34 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| A13 bridge A13 rotunda | 1/1 | 4.30 | 4.30 | 4.3 | +4.30 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| D14 bridge D14 rotunda | 1/1 | 4.14 | 4.14 | 4.1 | +4.14 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [00-overview](00-overview.png) |
| A9 bridge A9 rotunda | 1/1 | 4.11 | 4.11 | 4.1 | +4.11 | 0.25 | raster | – | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| F19 bridge F19 rotunda | 1/1 | 4.10 | 4.10 | 4.1 | +4.10 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| F8 bridge F8 rotunda | 1/1 | 4.00 | 4.00 | 4.0 | +4.00 | 0.27 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| E7 bridge E7 rotunda | 1/1 | 3.98 | 3.98 | 4.0 | +3.98 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| E13 bridge E13 rotunda | 1/1 | 3.98 | 3.98 | 4.0 | +3.98 | 0.24 | raster | – | [10-ba-E](10-ba-E.png), [00-overview](00-overview.png) |
| E8 bridge E8 rotunda | 1/1 | 3.96 | 3.96 | 4.0 | +3.96 | 0.24 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| B11 bridge B11 rotunda | 1/1 | 3.90 | 3.90 | 3.9 | +3.90 | 0.28 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G9 bridge G9 rotunda | 1/1 | 3.90 | 3.90 | 3.9 | +3.90 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| G2 bridge G2 rotunda | 1/1 | 3.81 | 3.81 | 3.8 | +3.81 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F15 bridge F15 rotunda | 1/1 | 3.81 | 3.81 | 3.8 | +3.81 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| C8 bridge C8 rotunda | 1/1 | 3.81 | 3.81 | 3.8 | +3.81 | 0.16 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| C10 bridge C10 rotunda | 1/1 | 3.81 | 3.81 | 3.8 | +3.81 | 0.16 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| B21 bridge B21 rotunda | 1/1 | 3.73 | 3.73 | 3.7 | +3.73 | 0.28 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| E12 bridge E12 rotunda | 1/1 | 3.57 | 3.57 | 3.6 | +3.57 | 0.42 | raster | – | [10-ba-E](10-ba-E.png), [00-overview](00-overview.png) |
| B24 bridge B24 rotunda | 1/1 | 3.55 | 3.55 | 3.5 | +3.55 | 0.28 | raster | – | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| G5 bridge G5 rotunda | 1/1 | 3.55 | 3.55 | 3.5 | +3.55 | 0.27 | raster | – | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| F21 bridge F21 rotunda | 1/1 | 3.50 | 3.50 | 3.5 | +3.50 | 0.50 | raster | – | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| B7 bridge B7 rotunda | 1/1 | 3.48 | 3.48 | 3.5 | +3.48 | 0.28 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| B8 bridge B8 rotunda | 1/1 | 3.42 | 3.42 | 3.4 | +3.42 | 0.28 | raster | – | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| D4 bridge D4 rotunda | 1/1 | 3.42 | 3.42 | 3.4 | +3.42 | 0.24 | raster | – | [10-ba-D](10-ba-D.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| F9 bridge F9 rotunda | 1/1 | 3.42 | 3.42 | 3.4 | +3.42 | 0.27 | raster | – | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |

## Physical conflicts (worst first)

One row per pair of objects (worst part pair shown; `parts` lists all intersecting part pairs), merged over scenarios; `scenarios` lists those at the row's severity, others with their own severity initial in brackets. `depth` = short side of the overlap region (m), `vgap` = smallest vertical gap over the overlap, evaluated point by point (negative = interpenetration). Crops: `crops/conflict_NNNN.png` (vector, committed for the first 60) and `out/draw/crops/` (over the imagery, local only).

### COLLISION (59)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [1](crops/conflict_0001.png) | OVERSIZE | oversize-rest-bridge | B11S:a388 | B11 bridge B11 (L1) | aircraft x beacon; aircraft x bellows; aircraft x cab; aircraft x cab-roof; airc | 3.55 / 13.8 | 0.00 | -3.14 | a388 at B11S hits the parked bridge of B11 | -902, 711 / -467, -1050 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [2](crops/conflict_0002.png) | ENVELOPE | envelope-rest-bridge | B11 bridge B11 (L1) (a19n, a20n, a21n, a319, a320, a321 ...) | B11S class envelope | beacon x envelope-type; bellows x envelope-type; cab x envelope-type; cab-roof x | 3.55 / 13.8 | 0.00 | -4.04 |  | -902, 711 / -467, -1050 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [3](crops/conflict_0003.png) | OVERSIZE | oversize-rest-bridge | B11S:b748 | B11 bridge B11 (L1) | aircraft x bellows; aircraft x cab; aircraft x cab-roof; aircraft x floodlight;  | 3.55 / 13.7 | 0.00 | -2.03 | b748 at B11S hits the parked bridge of B11 | -902, 711 / -467, -1050 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [4](crops/conflict_0004.png) | ENVELOPE | envelope-rest-bridge | G13 bridge G13 (L2) (a19n, a20n, a319, a320, b37m, b38m ...) | G13 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type; tunnel3 x e | 3.30 / 8.1 | 0.00 | -0.01 |  | -1616, -8 / -1433, -747 | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| [5](crops/conflict_0005.png) | LIVE, REST | bridge-bridge | B11 bridge B11 (L1) | B11S bridge B11 (L1) | pedestal x cab; rotunda x beacon; rotunda x bellows; rotunda x cab; rotunda x ca | 3.28 / 10.8 | 0.00 | -1.10 |  | -892, 701 / -462, -1036 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [6](crops/conflict_0006.png) | ENVELOPE | envelope-rest-bridge | A6 bridge A6 (L2) (a19n, a20n, a319, a320, b37m, b736 ...) | A6 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type; tunnel3 x e | 2.84 / 5.5 | 0.00 | -0.01 |  | -1177, 664 / -731, -1136 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [7](crops/conflict_0007.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | B2 bridge B2 (L1) | Harvey Milk Terminal 1 | walkway x building | 2.42 / 6.9 | 0.00 | -8.46 |  | -1001, 520 / -643, -927 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [8](crops/conflict_0008.png) | ENVELOPE | envelope-rest-bridge | A1 bridge A1 (L2) (a19n, a20n, a319, a320, b37m, b736 ...) | A1 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 2.20 / 3.8 | 0.00 | -0.64 |  | -1068, 529 / -698, -966 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [9](crops/conflict_0009.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | A15 bridge A15 (L1) | Boarding Area A | walkway x building | 1.96 / 7.8 | 0.00 | -8.46 |  | -1323, 793 / -800, -1319 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| [10](crops/conflict_0010.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | B15 bridge B15 (L1) | Boarding Area B walkway (elevated walkway) | walkway x building | 1.87 / 6.2 | 0.00 | -2.46 |  | -922, 763 / -459, -1105 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [11](crops/conflict_0011.png) | LIVE | bridge-aircraft | SKW5212 CRJ2 at F10 (gate) | F8 bridge F8 (L1) | aircraft x cab; aircraft x tunnel2; aircraft x tunnel3 | 1.59 / 3.9 | 0.00 | -1.91 |  | -987, -216 / -974, -269 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| [12](crops/conflict_0012.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | G5 bridge G5 (L1) | G5 bridge G5 (L2) | pedestal x rotunda; rotunda x pedestal; rotunda x rotunda; rotunda x tunnel1; wa | 1.56 / 3.8 | 0.00 | -3.60 |  | -1373, 91 / -1172, -721 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [13](crops/conflict_0013.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | B10 bridge B10 (L1) | Boarding Area B walkway (elevated walkway) | rotunda x building | 1.38 / 4.2 | 0.00 | -2.70 |  | -880, 674 / -464, -1007 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [14](crops/conflict_0014.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | G6 bridge G6 (L1) | G6 bridge G6 (L2) | pedestal x rotunda; rotunda x pedestal; rotunda x rotunda; rotunda x tunnel1; wa | 1.36 / 3.1 | 0.00 | -3.60 |  | -1437, 58 / -1244, -721 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [15](crops/conflict_0015.png) | ENVELOPE | envelope-rest-bridge | G3 bridge G3 (L2) (a19n, a319, b736, b737, e170) | G3 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.33 / 1.8 | 0.00 | -0.02 |  | -1374, 174 / -1134, -794 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| [16](crops/conflict_0016.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | G10 bridge G10 (L1) | G10 bridge G10 (L2) | rotunda x rotunda; walkway x walkway | 1.32 / 4.4 | 0.00 | -3.05 |  | -1551, -1 / -1372, -722 | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| [17](crops/conflict_0017.png) | ENVELOPE | envelope-rest-bridge | E7 bridge E7 (L1) (a19n, a20n, a21n, a319, a320, a321 ...) | E7 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 1.31 / 0.9 | 0.00 | -1.16 |  | -755, -11 / -673, -343 | [10-ba-D](10-ba-D.png), [10-ba-E](10-ba-E.png) |
| [18](crops/conflict_0018.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A10 bridge A10 (L1) | A10 bridge A10 (L2) | rotunda x rotunda; rotunda x walkway; tunnel1 x rotunda; walkway x walkway | 1.24 / 3.6 | 0.00 | -3.05 |  | -1299, 725 / -811, -1247 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| [19](crops/conflict_0019.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | G3 bridge G3 (L1) | G3 bridge G3 (L2) | rotunda x rotunda; rotunda x walkway; walkway x walkway | 1.06 / 2.2 | 0.00 | -3.60 |  | -1380, 157 / -1147, -783 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| [20](crops/conflict_0020.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A9 bridge A9 (L1) | A9 bridge A9 (L2) | rotunda x rotunda; rotunda x walkway; tunnel1 x rotunda; walkway x walkway | 1.04 / 2.4 | 0.00 | -3.05 |  | -1265, 661 / -811, -1175 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| [21](crops/conflict_0021.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F9 bridge F9 (L1) | Boarding Area F | rotunda x building | 1.03 / 2.8 | 0.00 | -8.70 |  | -1026, -218 / -1010, -286 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| [22](crops/conflict_0022.png) | ENVELOPE | envelope-rest-bridge | F12 bridge F12 (L1) (a19n, a20n, a21n, a319, a320, a321 ...) | F12 class envelope | bellows x envelope-type; cab x envelope-type | 0.96 / 0.6 | 0.00 | -0.85 |  | -1127, -121 / -1053, -418 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [23](crops/conflict_0023.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | G2 bridge G2 (L1) | G2 bridge G2 (L2) | rotunda x rotunda; rotunda x tunnel1; walkway x rotunda | 0.92 / 1.8 | 0.00 | -3.60 |  | -1310, 125 / -1101, -722 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [24](crops/conflict_0024.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A8 bridge A8 (L2) | A8 bridge A8 (L1) | stair x stair; walkway x walkway | 0.87 / 2.0 | 0.00 | -3.05 |  | -1242, 746 / -751, -1239 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [25](crops/conflict_0025.png) | LIVE, REST | bridge-vdgs | E4 bridge E4 (L1) | E4 VDGS / stand sign | stair x vdgs-post; stair x vdgs-post-base; tunnel2 x stand-sign-back; tunnel2 x  | 0.84 / 0.8 | 0.00 | -0.17 |  | -794, 76 / -667, -438 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| [26](crops/conflict_0026.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A2 bridge A2 (L1) | A2 bridge A2 (L2) | walkway x walkway | 0.75 / 1.6 | 0.00 | -3.05 |  | -1168, 606 / -751, -1081 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [27](crops/conflict_0027.png) | ENVELOPE | envelope-rest-bridge | F14 bridge F14 (L1) (a19n, a20n, a21n, a319, a320, a321 ...) | F14 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 0.75 / 0.4 | 0.00 | -0.60 |  | -1176, -148 / -1109, -417 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [28](crops/conflict_0028.png) | ENVELOPE | envelope-rest-bridge | F22 bridge F22 (L2) (a19n, a319, b736, b737) | F22 class envelope | bellows x envelope-type; cab x envelope-type | 0.74 / 0.3 | 0.00 | -0.01 |  | -1280, -287 / -1267, -343 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| [29](crops/conflict_0029.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A6 bridge A6 (L1) | A6 bridge A6 (L2) | walkway x walkway | 0.73 / 1.2 | 0.00 | -3.05 |  | -1209, 683 / -751, -1168 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [30](crops/conflict_0030.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A13 bridge A13 (L1) | A13 bridge A13 (L2) | cab-roof x stair; rotunda x walkway; tunnel1 x rotunda; tunnel2 x rotunda; walkw | 0.72 / 1.7 | 0.00 | -3.30 |  | -1282, 818 / -752, -1321 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| [31](crops/conflict_0031.png) | DOCK-REF | bridge-aircraft | F11 b789 | F11 bridge F11 (L2) | aircraft x stair | 0.70 / 2.1 | 0.00 | -1.13 |  | -1081, -207 / -1053, -321 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [32](crops/conflict_0032.png) | DOCK-REF | bridge-aircraft | G1 b789 | G1 bridge G1 (L2) | aircraft x stair | 0.70 / 2.1 | 0.00 | -1.13 |  | -1246, 132 / -1041, -698 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [33](crops/conflict_0033.png) | DOCK-REF | bridge-aircraft | G3 b789 | G3 bridge G3 (L2) | aircraft x stair | 0.70 / 2.1 | 0.00 | -1.06 |  | -1374, 180 / -1131, -800 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| [34](crops/conflict_0034.png) | DOCK-REF | bridge-aircraft | G4 b789 | G4 bridge G4 (L2) | aircraft x stair | 0.70 / 2.1 | 0.00 | -1.18 |  | -1448, 145 / -1213, -804 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [35](crops/conflict_0035.png) | DOCK-REF | bridge-aircraft | G12 b789 | G12 bridge G12 (L2) | aircraft x stair | 0.70 / 2.1 | 0.00 | -1.13 |  | -1628, 46 / -1418, -800 | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| [36](crops/conflict_0036.png) | ENVELOPE | envelope-rest-bridge | C10 bridge C10 (L1) (a19n, a20n, a21n, a319, a320, a321 ...) | C10 class envelope | bellows x envelope-type; cab x envelope-type; stair x envelope-type | 0.70 / 0.4 | 0.00 | -0.01 |  | -585, 471 / -298, -689 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| [37](crops/conflict_0037.png) | ENVELOPE | envelope-rest-bridge | G8 bridge G8 (L1) (a332, a333, a338, a339, a359, a35k ...) | G8 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.69 / 0.4 | 0.00 | -2.13 |  | -1563, 67 / -1352, -788 | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| [38](crops/conflict_0038.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F17 bridge F17 (L1) | Boarding Area F | rotunda x building | 0.67 / 1.5 | 0.00 | -8.70 |  | -1280, -216 / -1233, -406 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [39](crops/conflict_0039.png) | ENVELOPE | envelope-rest-bridge | A12 bridge A12 (L1) (a19n, a21n, a332, a333, b762, b763 ...) | A12 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.67 / 0.6 | 0.00 | -0.03 |  | -1336, 798 / -809, -1329 | [10-ba-A](10-ba-A.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| [40](crops/conflict_0040.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-mast | B12 bridge B12 (L1) | floodlight mast 61 | tunnel1 x pole; tunnel2 x base | 0.66 / 0.3 | 0.00 | -7.20 |  | -796, 716 / -370, -1005 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| [41](crops/conflict_0041.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-mast | B14 bridge B14 (L1) | floodlight mast 62 | rotunda x head-bar; rotunda x luminaire; tunnel1 x pole; tunnel2 x luminaire; tu | 0.66 / 0.3 | 0.00 | -7.23 |  | -837, 794 / -370, -1092 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [42](crops/conflict_0042.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-mast | B18 bridge B18 (L1) | floodlight mast 63 | pca-hose x base; pca-hose x luminaire; pca-unit x luminaire; pca-unit x pole; tu | 0.66 / 0.3 | 0.00 | -7.09 |  | -875, 866 / -370, -1174 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [43](crops/conflict_0043.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A5 bridge A5 (L1) | A5 bridge A5 (L2) | rotunda x rotunda; rotunda x tunnel1; walkway x rotunda | 0.61 / 0.5 | 0.00 | -3.35 |  | -1238, 610 / -810, -1117 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [44](crops/conflict_0044.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | G7 bridge G7 (L1) | G7 bridge G7 (L2) | rotunda x rotunda; rotunda x tunnel1; stair x stair; walkway x rotunda | 0.60 / 0.8 | 0.00 | -3.35 |  | -1508, 88 / -1293, -781 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [45](crops/conflict_0045.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | G4 bridge G4 (L1) | G4 bridge G4 (L2) | rotunda x rotunda; rotunda x tunnel1; walkway x rotunda | 0.58 / 0.6 | 0.00 | -3.35 |  | -1445, 121 / -1222, -781 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [46](crops/conflict_0046.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | C8 bridge C8 (L1) | Boarding Area C | rotunda x building | 0.57 / 1.2 | 0.00 | -8.70 |  | -623, 464 / -335, -700 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| [47](crops/conflict_0047.png) | ENVELOPE | envelope-rest-bridge | G4 bridge G4 (L1) (a332, a333, b762, b763, b764, b772 ...) | G4 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.56 / 0.4 | 0.00 | -0.03 |  | -1435, 135 / -1206, -788 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [48](crops/conflict_0048.png) | ENVELOPE | envelope-rest-bridge | F19 bridge F19 (L1) (a332, a333, a338, a339, a359, a35k ...) | F19 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.48 / 0.2 | 0.00 | -0.85 |  | -1318, -222 / -1269, -418 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [49](crops/conflict_0049.png) | ENVELOPE | envelope-rest-bridge | F21 bridge F21 (L1) (a19n, a20n, a21n, a319, a320, a321 ...) | F21 class envelope | bellows x envelope-type; cab x envelope-type | 0.45 / 0.2 | 0.00 | -0.60 |  | -1317, -268 / -1290, -377 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| [50](crops/conflict_0050.png) | LIVE, REST | bridge-vdgs | B23 bridge B23 (L1) | B23 VDGS / stand sign | stair x vdgs-post; stair x vdgs-post-base; tunnel2 x stand-sign-back; tunnel3 x  | 0.43 / 0.4 | 0.00 | -0.11 |  | -931, 944 / -384, -1269 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| [51](crops/conflict_0051.png) | ENVELOPE | envelope-rest-bridge | G7 bridge G7 (L1) (a332, a333, a338, a339, a359, a35k ...) | G7 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.43 / 0.2 | 0.00 | -0.85 |  | -1499, 101 / -1279, -788 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [52](crops/conflict_0052.png) | ENVELOPE | envelope-rest-bridge | F5 bridge F5 (L1) (a19n, a20n, a21n, a319, a320, a321 ...) | F5 class envelope | bellows x envelope-type; cab x envelope-type | 0.41 / 0.2 | 0.00 | -0.60 |  | -1023, -135 / -968, -358 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| [53](crops/conflict_0053.png) | ENVELOPE | envelope-rest-bridge | F17 bridge F17 (L1) (a19n, a20n, a21n, a319, a320, a321 ...) | F17 class envelope | bellows x envelope-type; cab x envelope-type | 0.37 / 0.1 | 0.00 | -0.60 |  | -1274, -204 / -1222, -414 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| [54](crops/conflict_0054.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F19 bridge F19 (L1) | Boarding Area F | rotunda x building | 0.25 / 0.4 | 0.00 | -8.70 |  | -1313, -235 / -1271, -405 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| [55](crops/conflict_0055.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A11 bridge A11 (L1) | A11 bridge A11 (L2) | rotunda x walkway | 0.19 / 0.2 | 0.00 | -3.30 |  | -1272, 807 / -749, -1307 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| [56](crops/conflict_0056.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | G8 bridge G8 (L1) | G8 bridge G8 (L2) | rotunda x rotunda; rotunda x tunnel1; walkway x rotunda | 0.16 / 0.1 | 0.00 | -3.35 |  | -1572, 54 / -1365, -781 | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| [57](crops/conflict_0057.png) | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F22 bridge F22 (L1) | Boarding Area F | rotunda x building | 0.14 / 0.1 | 0.00 | -8.70 |  | -1281, -259 / -1254, -369 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| [58](crops/conflict_0058.png) | ENVELOPE | envelope-rest-bridge | A5 bridge A5 (L1) (a332, a333, a338, a339, a359, a35k ...) | A5 class envelope | bellows x envelope-type; cab x envelope-type; cab-roof x envelope-type | 0.14 / 0.1 | 0.00 | -0.85 |  | -1252, 623 / -817, -1135 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| [59](crops/conflict_0059.png) | OVERSIZE | oversize-not-blocked | F15:a388 | F13 class envelope | aircraft x envelope | – / – | 0.00 | – | a388 (79.8 m span) at F15 reaches F13 (nose distance 74.7 m >= block radius 73.5 m): F13 stays available | -1173, -270 / -1163, -308 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |

### OFF-PAVEMENT (4)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [60](crops/conflict_0060.png) | LIVE | gear-off-pavement | UAL643 B38M (parked) | rendered paved raster (1.0 m): visual | aircraft x pavement | – / – | – | – | visual: rendered nose, main, main gear on unpaved ground | -139, 384 / 56, -404 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 61 | LIVE | gear-off-physics-pavement | UAL643 B38M (parked) | GroundPhysics pavement (raster OR OSM taxi net): physics | aircraft x pavement | – / – | – | – | physics: GroundPhysics nose, main, main gear point off raster and taxi net | -139, 384 / 56, -404 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 62 | LIVE | gear-off-pavement | SKW6001 E75L (parked) | rendered paved raster (1.0 m): visual | aircraft x pavement | – / – | – | – | visual: rendered nose, main, main gear on unpaved ground | -91, 409 / 110, -404 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 63 | LIVE | gear-off-physics-pavement | SKW6001 E75L (parked) | GroundPhysics pavement (raster OR OSM taxi net): physics | aircraft x pavement | – / – | – | – | physics: GroundPhysics nose, main, main gear point off raster and taxi net | -91, 409 / 110, -404 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |

### OBSTRUCTION (27)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 64 | STATIC | pier-on-movement-surface | RWY 19L MALSF approach-light post 61 m from the threshold | EMAS area 19L, EMAS bed 19L (3-D) | post x surface | 36.65 / 0.1 | – | – | RWY 19L MALSF approach-light post 61 m from the threshold (1.3 m high) stands 36.6 m inside EMAS area 19L, EMA | 762, -1001 / 207, 1241 | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| 65 | STATIC | sign-on-movement-surface | distance-remaining sign 391 | taxiway Taxiway M | sign x surface | 17.41 / 0.3 | – | – | distance-remaining sign 391 (1.5 m high) stands 17.4 m inside taxiway Taxiway M | -356, 1235 / 262, -1258 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 66 | STATIC | sign-on-movement-surface | distance-remaining sign 374 | taxiway Taxiway D | sign x surface | 16.94 / 0.3 | – | – | distance-remaining sign 374 (1.5 m high) stands 16.9 m inside taxiway Taxiway D | -676, -302 / -738, -48 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 67 | STATIC | sign-on-movement-surface | distance-remaining sign 363 | taxiway Taxiway D | sign x surface | 16.27 / 0.3 | – | – | distance-remaining sign 363 (1.5 m high) stands 16.3 m inside taxiway Taxiway D | -518, -601 / -738, 290 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 68 | STATIC | pier-on-movement-surface | RWY 19L MALSF approach-light post 122 m from the threshold | EMAS area 19L, EMAS bed 19L (3-D) | post x surface | 15.85 / 0.1 | – | – | RWY 19L MALSF approach-light post 122 m from the threshold (1.3 m high) stands 15.8 m inside EMAS area 19L, EM | 790, -1055 / 207, 1302 | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| 69 | STATIC | sign-on-movement-surface | hold/location sign 22 | taxiway Taxiway R/U | sign x surface | 12.40 / 0.7 | – | – | hold/location sign 22 (1.2 m high) stands 12.4 m inside taxiway Taxiway R/U | -1312, -871 / -1566, 159 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 70 | STATIC | sign-on-movement-surface | hold/location sign 23 | taxiway Taxiway R/U | sign x surface | 11.25 / 0.2 | – | – | hold/location sign 23 (1.2 m high) stands 11.3 m inside taxiway Taxiway R/U | -1310, -870 / -1564, 159 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 71 | STATIC | sign-on-movement-surface | hold/location sign 42 | taxiway Taxiway D | sign x surface | 7.88 / 0.7 | – | – | hold/location sign 42 (1.2 m high) stands 7.9 m inside taxiway Taxiway D | -573, -482 / -732, 159 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 72 | STATIC | sign-on-movement-surface | hold/location sign 43 | taxiway Taxiway D | sign x surface | 6.47 / 0.2 | – | – | hold/location sign 43 (1.2 m high) stands 6.5 m inside taxiway Taxiway D | -572, -481 / -730, 159 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 73 | STATIC | sign-on-movement-surface | hold/location sign 323 | taxiway Taxiway F | sign x surface | 6.42 / 0.3 | – | – | hold/location sign 323 (1.2 m high) stands 6.4 m inside taxiway Taxiway F | 182, 264 / 284, -148 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 74 | STATIC | sign-on-movement-surface | hold/location sign 322 | taxiway Taxiway F | sign x surface | 5.80 / 0.6 | – | – | hold/location sign 322 (1.2 m high) stands 5.8 m inside taxiway Taxiway F | 182, 266 / 285, -150 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 75 | STATIC | sign-on-movement-surface | distance-remaining sign 376 | taxiway Taxiway Q | sign x surface | 5.27 / 0.4 | – | – | distance-remaining sign 376 (1.5 m high) stands 5.3 m inside taxiway Taxiway Q | -1215, -586 / -1348, -48 | [30-rwy-10R](30-rwy-10R.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 76 | STATIC | sign-on-movement-surface | hold/location sign 15 | taxiway Taxiway C1 | sign x surface | 3.22 / 0.3 | – | – | hold/location sign 15 (1.2 m high) stands 3.2 m inside taxiway Taxiway C1 | -1569, -1190 / -1943, 321 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 77 | STATIC | sign-on-movement-surface | hold/location sign 68 | taxiway Taxiway P | sign x surface | 2.98 / 0.7 | – | – | hold/location sign 68 (1.2 m high) stands 3.0 m inside taxiway Taxiway P | 680, 179 / 685, 159 | [00-overview](00-overview.png) |
| 78 | STATIC | sign-on-movement-surface | hold/location sign 14 | taxiway Taxiway C1 | sign x surface | 1.64 / 0.7 | – | – | hold/location sign 14 (1.2 m high) stands 1.6 m inside taxiway Taxiway C1 | -1567, -1189 / -1941, 321 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 79 | STATIC | sign-on-movement-surface | hold/location sign 69 | taxiway Taxiway P | sign x surface | 1.53 / 0.2 | – | – | hold/location sign 69 (1.2 m high) stands 1.5 m inside taxiway Taxiway P | 679, 178 / 684, 159 | [00-overview](00-overview.png) |
| 80 | STATIC | sign-on-movement-surface | hold/location sign 324 | taxiway Taxiway F/F1/L | sign x surface | 1.00 / 0.6 | – | – | hold/location sign 324 (1.2 m high) stands 1.0 m inside taxiway Taxiway F/F1/L | 178, 288 / 292, -171 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 81 | STATIC | sign-on-movement-surface | hold/location sign 325 | taxiway Taxiway F/F1/L | sign x surface | 0.46 / 0.2 | – | – | hold/location sign 325 (1.2 m high) stands 0.5 m inside taxiway Taxiway F/F1/L | 178, 289 / 292, -173 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 82 | STATIC | sign-on-movement-surface | hold/location sign 126 | taxiway Taxiway T/K/A/B | sign x surface | 0.39 / 0.7 | – | – | hold/location sign 126 (1.2 m high) stands 0.4 m inside taxiway Taxiway T/K/A/B | -908, -400 / -990, -70 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 83 | STATIC | sign-on-movement-surface | hold/location sign 127 | taxiway Taxiway T/K/A/B | sign x surface | 0.35 / 0.2 | – | – | hold/location sign 127 (1.2 m high) stands 0.3 m inside taxiway Taxiway T/K/A/B | -906, -399 / -988, -70 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 84 | STATIC | sign-on-movement-surface | hold/location sign 36 | taxiway Taxiway K | sign x surface | 0.28 / 0.7 | – | – | hold/location sign 36 (1.2 m high) reaches 0.28 m onto taxiway Taxiway K | -708, -736 / -970, 321 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 85 | STATIC | sign-on-movement-surface | distance-remaining sign 379 | RWY 10R/28L | sign x surface | 0.13 / 0.3 | – | – | distance-remaining sign 379 (1.5 m high) reaches 0.13 m onto RWY 10R/28L | -51, -69 / -77, 37 | [00-overview](00-overview.png) |
| 86 | STATIC | sign-on-movement-surface | hold/location sign 134 | taxiway Taxiway B/D, taxiway Taxiway D | sign x surface | 0.11 / 0.7 | – | – | hold/location sign 134 (1.2 m high) stands 0.1 m inside taxiway Taxiway B/D, taxiway Taxiway D | -674, -276 / -725, -70 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 87 | STATIC | sign-on-movement-surface | distance-remaining sign 386 | RWY 10L/28R | sign x surface | 0.11 / 0.3 | – | – | distance-remaining sign 386 (1.5 m high) reaches 0.11 m onto RWY 10L/28R | 355, -113 / 262, 266 | [00-overview](00-overview.png) |
| 88 | STATIC | sign-on-movement-surface | hold/location sign 135 | taxiway Taxiway B/D, taxiway Taxiway D | sign x surface | 0.11 / 0.2 | – | – | hold/location sign 135 (1.2 m high) stands 0.1 m inside taxiway Taxiway B/D, taxiway Taxiway D | -672, -276 / -723, -70 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 89 | STATIC | sign-on-movement-surface | distance-remaining sign 360 | RWY 1R/19L | sign x surface | 0.04 / 0.3 | – | – | distance-remaining sign 360 (1.5 m high) stands 0.0 m inside RWY 1R/19L | 291, -174 / 176, 290 | [00-overview](00-overview.png) |
| 90 | STATIC | sign-on-movement-surface | distance-remaining sign 371 | RWY 1R/19L | sign x surface | 0.04 / 0.3 | – | – | distance-remaining sign 371 (1.5 m high) stands 0.0 m inside RWY 1R/19L | 133, 125 / 176, -48 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |

### CLEARANCE (42)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 91 | ENVELOPE | envelope-envelope | F19 class envelope | F20 class envelope | envelope x envelope | – / – | 0.21 | – | 0.2 m < ICAO 7.5 m | -1361, -241 / -1316, -422 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 92 | ENVELOPE | envelope-envelope | E10 class envelope | E12 class envelope | envelope x envelope | – / – | 0.35 | – | 0.4 m < ICAO 4.5 m | -820, -111 / -777, -285 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 93 | OVERSIZE | oversize-not-blocked | A2:a388 | A6 class envelope | aircraft x envelope | – / – | 0.59 | – | a388 (79.8 m span) at A2 reaches A6 (nose distance 82.4 m >= block radius 80.8 m): A6 stays available | -1122, 632 / -697, -1082 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 94 | OVERSIZE | oversize-not-blocked | G7:a388 | G4 class envelope | aircraft x envelope | – / – | 2.32 | – | a388 (79.8 m span) at G7 reaches G4 (nose distance 72.5 m >= block radius 71.2 m): G4 stays available | -1482, 162 / -1235, -835 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 95 | ENVELOPE | envelope-envelope | G7 class envelope | G8 class envelope | envelope x envelope | – / – | 2.33 | – | 2.3 m < ICAO 7.5 m | -1549, 125 / -1312, -834 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 96 | OVERSIZE | oversize-not-blocked | G2:a388 | G1 class envelope | aircraft x envelope | – / – | 2.40 | – | a388 (79.8 m span) at G2 reaches G1 (nose distance 72.7 m >= block radius 71.2 m): G1 stays available | -1273, 91 / -1084, -674 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 97 | OVERSIZE | oversize-not-blocked | F15:b748 | F13 class envelope | aircraft x envelope | – / – | 2.41 | – | b748 (68.4 m span) at F15 reaches F13 (nose distance 74.7 m >= block radius 73.5 m): F13 stays available | -1175, -276 / -1168, -304 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 98 | OVERSIZE | oversize-not-blocked | A1:a388 | A2 class envelope | aircraft x envelope | – / – | 2.57 | – | a388 (79.8 m span) at A1 reaches A2 (nose distance 105.9 m >= block radius 73.5 m): A2 stays available | -1083, 568 / -693, -1007 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 99 | ENVELOPE | envelope-envelope | A5 class envelope | A9 class envelope | envelope x envelope | – / – | 2.71 | – | 2.7 m < ICAO 7.5 m | -1308, 637 / -860, -1174 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 100 | ENVELOPE | envelope-envelope | G2 class envelope | G5 class envelope | envelope x envelope | – / – | 2.85 | – | 2.9 m < ICAO 7.5 m | -1338, 52 / -1160, -670 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 101 | OVERSIZE | oversize-not-blocked | A5:a388 | A4 class envelope | aircraft x envelope | – / – | 3.40 | – | a388 (79.8 m span) at A5 reaches A4 (nose distance 65.5 m >= block radius 59.0 m): A4 stays available | -1273, 568 / -861, -1096 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 102 | ENVELOPE | envelope-envelope | G5 class envelope | G6 class envelope | envelope x envelope | – / – | 3.53 | – | 3.5 m < ICAO 7.5 m | -1402, 18 / -1232, -670 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 103 | ENVELOPE | envelope-envelope | G6 class envelope | G9 class envelope | envelope x envelope | – / – | 3.54 | – | 3.5 m < ICAO 7.5 m | -1468, -12 / -1304, -674 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 104 | ENVELOPE | envelope-envelope | A10 class envelope | A9 class envelope | envelope x envelope | – / – | 3.66 | – | 3.7 m < ICAO 7.5 m | -1343, 701 / -861, -1246 | [10-ba-A](10-ba-A.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 105 | ENVELOPE | envelope-envelope | G10 class envelope | G9 class envelope | envelope x envelope | – / – | 3.71 | – | 3.7 m < ICAO 7.5 m | -1533, -46 / -1377, -675 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 106 | ENVELOPE | envelope-envelope | A10 class envelope | A12 class envelope | envelope x envelope | – / – | 3.89 | – | 3.9 m < ICAO 7.5 m | -1372, 768 / -856, -1319 | [10-ba-A](10-ba-A.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 107 | OVERSIZE | oversize-not-blocked | A2:a388 | A1 class envelope | aircraft x envelope | – / – | 3.93 | – | a388 (79.8 m span) at A2 reaches A1 (nose distance 105.9 m >= block radius 73.5 m): A1 stays available | -1079, 563 / -692, -1001 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 108 | ENVELOPE | envelope-envelope | F13 class envelope | F15 class envelope | envelope x envelope | – / – | 4.02 | – | 4.0 m < ICAO 7.5 m | -1175, -273 / -1167, -307 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 109 | ENVELOPE | envelope-envelope | F11 class envelope | F13 class envelope | envelope x envelope | – / – | 4.22 | – | 4.2 m < ICAO 7.5 m | -1109, -248 / -1096, -298 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 110 | ENVELOPE | envelope-envelope | F20 class envelope | F21 class envelope | envelope x envelope | – / – | 4.31 | – | 4.3 m < ICAO 4.5 m | -1341, -274 / -1315, -383 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 111 | ENVELOPE | envelope-envelope | F21 class envelope | F22 class envelope | envelope x envelope | – / – | 4.44 | – | 4.4 m < ICAO 7.5 m | -1307, -300 / -1296, -345 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 112 | ENVELOPE | envelope-envelope | C10 class envelope | C8 class envelope | envelope x envelope | – / – | 4.68 | – | 4.7 m < ICAO 7.5 m | -583, 503 / -281, -717 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| 113 | ENVELOPE | envelope-envelope | A11 class envelope | A8 class envelope | envelope x envelope | – / – | 5.41 | – | 5.4 m < ICAO 7.5 m | -1195, 772 / -697, -1240 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 114 | DOCK-REF | aircraft-aircraft | F19 b77w | F20 a21n | aircraft x aircraft | – / – | 5.79 | – | 5.8 m < ICAO 7.5 m | -1366, -241 / -1320, -424 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 115 | ENVELOPE | envelope-envelope | A6 class envelope | A8 class envelope | envelope x envelope | – / – | 5.79 | – | 5.8 m < ICAO 7.5 m | -1163, 704 / -700, -1166 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 116 | OVERSIZE | oversize-not-blocked | A2:b748 | A1 class envelope | aircraft x envelope | – / – | 5.79 | – | b748 (68.4 m span) at A2 reaches A1 (nose distance 105.9 m >= block radius 73.5 m): A1 stays available | -1078, 569 / -688, -1006 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 117 | OVERSIZE | oversize-not-blocked | F13:a388 | F15 class envelope | aircraft x envelope | – / – | 5.82 | – | a388 (79.8 m span) at F13 reaches F15 (nose distance 74.7 m >= block radius 73.5 m): F15 stays available | -1176, -277 / -1169, -303 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 118 | ENVELOPE | envelope-envelope | F15 class envelope | F22 class envelope | envelope x envelope | – / – | 5.88 | – | 5.9 m < ICAO 7.5 m | -1244, -302 / -1241, -313 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 119 | ENVELOPE | envelope-envelope | G4 class envelope | G7 class envelope | envelope x envelope | – / – | 5.88 | – | 5.9 m < ICAO 7.5 m | -1482, 155 / -1239, -828 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 120 | ENVELOPE | envelope-envelope | A2 class envelope | A6 class envelope | envelope x envelope | – / – | 6.03 | – | 6.0 m < ICAO 7.5 m | -1120, 630 / -697, -1080 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 121 | ENVELOPE | envelope-envelope | C6 class envelope | C8 class envelope | envelope x envelope | – / – | 6.09 | – | 6.1 m < ICAO 7.5 m | -634, 512 / -322, -748 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| 122 | DOCK-MAX | aircraft-aircraft | F19 b779 | F20 b752 | aircraft x aircraft | – / – | 6.29 | – | 6.3 m < ICAO 7.5 m | -1367, -241 / -1322, -425 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 123 | ENVELOPE | envelope-envelope | G1 class envelope | G2 class envelope | envelope x envelope | – / – | 6.42 | – | 6.4 m < ICAO 7.5 m | -1275, 90 / -1086, -674 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 124 | DOCK-MAX | aircraft-aircraft | G7 b779 | G8 b779 | aircraft x aircraft | – / – | 6.53 | – | 6.5 m < ICAO 7.5 m | -1548, 123 / -1312, -831 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 125 | DOCK-REF | aircraft-aircraft | G7 b77w | G8 b77w | aircraft x aircraft | – / – | 6.57 | – | 6.6 m < ICAO 7.5 m | -1548, 122 / -1312, -830 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 126 | OVERSIZE | oversize-not-blocked | A2:b748 | A6 class envelope | aircraft x envelope | – / – | 6.94 | – | b748 (68.4 m span) at A2 reaches A6 (nose distance 82.4 m >= block radius 80.8 m): A6 stays available | -1119, 630 / -696, -1080 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 127 | DOCK-MAX | aircraft-aircraft | G2 b779 | G5 b779 | aircraft x aircraft | – / – | 6.99 | – | 7.0 m < ICAO 7.5 m | -1339, 54 / -1160, -673 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 128 | DOCK-REF | aircraft-aircraft | G2 b77w | G5 b77w | aircraft x aircraft | – / – | 7.01 | – | 7.0 m < ICAO 7.5 m | -1340, 55 / -1160, -674 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 129 | OVERSIZE | oversize-not-blocked | B11S:a388 | B15 class envelope | aircraft x envelope | – / – | 7.20 | – | a388 (79.8 m span) at B11S reaches B15 (nose distance 72.0 m >= block radius 59.0 m): B15 stays available | -960, 732 / -508, -1095 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 130 | DOCK-MAX | aircraft-aircraft | A5 b779 | A9 b779 | aircraft x aircraft | – / – | 7.32 | – | 7.3 m < ICAO 7.5 m | -1308, 638 / -859, -1174 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 131 | DOCK-REF | aircraft-aircraft | A5 b77w | A9 b77w | aircraft x aircraft | – / – | 7.34 | – | 7.3 m < ICAO 7.5 m | -1306, 638 / -858, -1174 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 132 | DOCK-MAX | aircraft-aircraft | A11 a388 | A8 b779 | aircraft x aircraft | – / – | 7.47 | – | 7.5 m < ICAO 7.5 m | -1196, 770 / -699, -1239 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |

### WARNING (124)

| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 133 | STATIC | building-building | West Field Road AirTrain Station (Outbound) | Westfield Road AirTrain Station (Outbound)g | building x building | 30.77 / 399.7 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 400 m2: coplanar faces z-fight - probably one station listed twi | -2117, -321 / -2022, -703 | [00-overview](00-overview.png) |
| 134 | STATIC | building-building | Central Parking Garage | Terminal One AirTrain Station | building x building | 26.70 / 868.4 | 0.00 | – | walls interpenetrate: 76 % of Terminal One AirTrain Station lies inside Central Parking Garage (13.0 vs 22.0 m | -904, 399 / -613, -775 | [20-itb-tower](20-itb-tower.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 135 | STATIC | building-building | Terminal complex ramp level | Air Traffic Control Tower | building x building | 25.80 / 1125.5 | 0.00 | – | walls interpenetrate: 92 % of Air Traffic Control Tower lies inside Terminal complex ramp level (14.0 vs 5.0 m | -743, 334 / -501, -642 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| 136 | STATIC | building-building | Terminal 2 | Air Traffic Control Tower | building x building | 25.63 / 1119.3 | 0.00 | – | walls interpenetrate: 92 % of Air Traffic Control Tower lies inside Terminal 2 (14.0 vs 19.6 m high) | -743, 334 / -502, -642 | [10-ba-C](10-ba-C.png), [10-ba-D](10-ba-D.png) |
| 137 | STATIC | building-building | Garage G AirTrain Station | Garage G | building x building | 25.07 / 1054.1 | 0.00 | – | walls interpenetrate: 31 % of Garage G AirTrain Station lies inside Garage G (13.0 vs 21.0 m high) | -1499, 305 / -1183, -969 | [10-ba-G](10-ba-G.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 138 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 115 | pavement x sign | 20.40 / – | – | – | 20.4 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1411, -838 / -1639, 83 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 139 | STATIC | building-building | Central Parking Garage | Terminal Two AirTrain Station | building x building | 20.33 / 826.3 | 0.00 | – | walls interpenetrate: 64 % of Terminal Two AirTrain Station lies inside Central Parking Garage (13.0 vs 22.0 m | -807, 230 / -606, -580 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| 140 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | distance-remaining sign 369 | pavement x sign | 20.00 / – | – | – | 20.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 672, 409 / 786, -48 | [00-overview](00-overview.png) |
| 141 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 21 | pavement x sign | 19.24 / – | – | – | 19.2 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1376, -904 / -1639, 158 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 142 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 114 | pavement x sign | 18.44 / – | – | – | 18.4 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1410, -837 / -1637, 83 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 143 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 20 | pavement x sign | 17.26 / – | – | – | 17.3 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1375, -904 / -1637, 158 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 144 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | distance-remaining sign 372 | pavement x sign | 17.20 / – | – | – | 17.2 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -136, -17 / -129, -48 | [00-overview](00-overview.png) |
| 145 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 175 | pavement x sign | 16.12 / – | – | – | 16.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 815, 534 / 970, -92 | [00-overview](00-overview.png) |
| 146 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 167 | pavement x sign | 14.32 / – | – | – | 14.3 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 633, 412 / 752, -70 | [00-overview](00-overview.png) |
| 147 | STATIC | building-building | Central Parking Garage | Terminal Three AirTrain Station | building x building | 14.14 / 724.5 | 0.00 | – | walls interpenetrate: 62 % of Terminal Three AirTrain Station lies inside Central Parking Garage (13.0 vs 22.0 | -987, 141 / -807, -585 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 148 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 105 | pavement x sign | 14.14 / – | – | – | 14.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1478, -912 / -1733, 117 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 149 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 174 | pavement x sign | 13.89 / – | – | – | 13.9 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 814, 532 / 968, -91 | [00-overview](00-overview.png) |
| 150 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 307 | pavement x sign | 13.89 / – | – | – | 13.9 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -49, 756 / 310, -692 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 151 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 309 | pavement x sign | 13.45 / – | – | – | 13.5 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -45, 755 / 313, -689 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 152 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 1 | pavement x sign | 13.42 / – | – | – | 13.4 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1900, -1162 / -2223, 141 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 153 | STATIC | building-building | Terminal 1 Air Train Station | Terminal One AirTrain Station | building x building | 13.14 / 686.9 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 687 m2: coplanar faces z-fight - probably one station listed twi | -903, 399 / -613, -775 | [20-itb-tower](20-itb-tower.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 154 | STATIC | building-building | Terminal complex ramp level | International Terminal G Air Train Station | building x building | 13.09 / 895.9 | 0.00 | – | walls interpenetrate: 100 % of International Terminal G Air Train Station lies inside Terminal complex ramp le | -1242, 240 / -986, -791 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| 155 | STATIC | building-building | Terminal complex ramp level | International Terminal A Air Train Station | building x building | 13.09 / 894.8 | 0.00 | – | walls interpenetrate: 100 % of International Terminal A Air Train Station lies inside Terminal complex ramp le | -1173, 466 / -821, -959 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 156 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 0 | pavement x sign | 12.73 / – | – | – | 12.7 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1898, -1162 / -2221, 142 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 157 | STATIC | building-building | Terminal 2 Air Train Station | Terminal Two AirTrain Station | building x building | 12.48 / 704.4 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 704 m2: coplanar faces z-fight - probably one station listed twi | -809, 227 / -610, -578 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| 158 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 166 | pavement x sign | 12.37 / – | – | – | 12.4 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 631, 412 / 750, -70 | [00-overview](00-overview.png) |
| 159 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 104 | pavement x sign | 12.04 / – | – | – | 12.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1480, -911 / -1734, 116 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 160 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 215 | pavement x sign | 12.04 / – | – | – | 12.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -541, 1238 / 99, -1348 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 161 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 306 | pavement x sign | 12.04 / – | – | – | 12.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -50, 757 / 309, -693 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 162 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 308 | pavement x sign | 12.04 / – | – | – | 12.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -45, 754 / 312, -687 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 163 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 7 | pavement x sign | 11.66 / – | – | – | 11.7 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1758, -1340 / -2180, 365 | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| 164 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 17 | pavement x sign | 11.66 / – | – | – | 11.7 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1569, -1006 / -1857, 158 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 165 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 11 | pavement x sign | 11.40 / – | – | – | 11.4 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1569, -1006 / -1858, 158 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 166 | STATIC | building-building | Terminal 3 Air Train Station | Terminal Three AirTrain Station | building x building | 11.08 / 689.3 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 689 m2: coplanar faces z-fight - probably one station listed twi | -985, 140 / -806, -583 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 167 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 173 | pavement x sign | 11.05 / – | – | – | 11.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 796, 473 / 925, -47 | [00-overview](00-overview.png) |
| 168 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 16 | pavement x sign | 10.77 / – | – | – | 10.8 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1567, -1005 / -1855, 158 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 169 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 199 | pavement x sign | 10.77 / – | – | – | 10.8 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -881, 1276 / -184, -1540 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 170 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 10 | pavement x sign | 10.30 / – | – | – | 10.3 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1571, -1007 / -1860, 158 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 171 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 191 | pavement x sign | 10.05 / – | – | – | 10.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 1489, 864 / 1720, -70 | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| 172 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 214 | pavement x sign | 10.00 / – | – | – | 10.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -543, 1239 / 98, -1349 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 173 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 273 | pavement x sign | 10.00 / – | – | – | 10.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -537, 1297 / 130, -1397 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 174 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 198 | pavement x sign | 9.85 / – | – | – | 9.8 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -879, 1276 / -182, -1539 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 175 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 5 | pavement x sign | 9.43 / – | – | – | 9.4 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1754, -1273 / -2145, 308 | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| 176 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 6 | pavement x sign | 9.43 / – | – | – | 9.4 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1758, -1338 / -2179, 364 | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| 177 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 110 | pavement x sign | 9.00 / – | – | – | 9.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1411, -666 / -1559, -69 | [30-rwy-10R](30-rwy-10R.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 178 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 172 | pavement x sign | 9.00 / – | – | – | 9.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 796, 475 / 926, -48 | [00-overview](00-overview.png) |
| 179 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 111 | pavement x sign | 8.94 / – | – | – | 8.9 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1410, -665 / -1557, -69 | [30-rwy-10R](30-rwy-10R.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 180 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 281 | pavement x sign | 8.94 / – | – | – | 8.9 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -423, 1544 / 346, -1563 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 181 | STATIC | building-building | Terminal complex ramp level | Terminal Two AirTrain Station | building x building | 8.79 / 206.8 | 0.00 | – | walls interpenetrate: 16 % of Terminal Two AirTrain Station lies inside Terminal complex ramp level (13.0 vs 5 | -756, 212 / -570, -540 | [10-ba-D](10-ba-D.png), [20-itb-tower](20-itb-tower.png) |
| 182 | STATIC | building-building | Terminal 2 | Terminal Two AirTrain Station | building x building | 8.79 / 206.8 | 0.00 | – | walls interpenetrate: 16 % of Terminal Two AirTrain Station lies inside Terminal 2 (13.0 vs 19.6 m high) | -756, 212 / -570, -540 | [10-ba-D](10-ba-D.png), [20-itb-tower](20-itb-tower.png) |
| 183 | STATIC | building-building | Terminal complex ramp level | International Terminal (A) AirTrain Station | building x building | 8.76 / 1179.7 | 0.00 | – | walls interpenetrate: 100 % of International Terminal (A) AirTrain Station lies inside Terminal complex ramp l | -1253, 242 / -996, -798 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| 184 | STATIC | building-building | International Terminal | International Terminal (G) AirTrain Station | building x building | 8.73 / 1078.6 | 0.00 | – | walls interpenetrate: 90 % of International Terminal (G) AirTrain Station lies inside International Terminal ( | -1173, 466 / -821, -959 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 185 | STATIC | building-building | Terminal complex ramp level | International Terminal (G) AirTrain Station | building x building | 8.73 / 1078.5 | 0.00 | – | walls interpenetrate: 90 % of International Terminal (G) AirTrain Station lies inside Terminal complex ramp le | -1173, 466 / -821, -959 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 186 | STATIC | building-building | International Terminal (G) AirTrain Station | International Terminal A Air Train Station | building x building | 8.72 / 595.6 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 596 m2: coplanar faces z-fight - probably one station listed twi | -1173, 466 / -821, -959 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 187 | STATIC | building-building | International Terminal (A) AirTrain Station | International Terminal G Air Train Station | building x building | 8.69 / 593.5 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 594 m2: coplanar faces z-fight - probably one station listed twi | -1242, 238 / -988, -790 | [10-ba-G](10-ba-G.png), [20-itb-tower](20-itb-tower.png) |
| 188 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 103 | pavement x sign | 8.60 / – | – | – | 8.6 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1545, -735 / -1709, -70 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 189 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 272 | pavement x sign | 8.49 / – | – | – | 8.5 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -538, 1298 / 130, -1399 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 190 | STATIC | building-building | Terminal 3 | Terminal Three AirTrain Station | building x building | 8.19 / 124.0 | 0.00 | – | walls interpenetrate: 11 % of Terminal Three AirTrain Station lies inside Terminal 3 (13.0 vs 21.6 m high) | -1003, 96 / -842, -553 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 191 | STATIC | building-building | Terminal complex ramp level | Terminal Three AirTrain Station | building x building | 8.19 / 121.3 | 0.00 | – | walls interpenetrate: 10 % of Terminal Three AirTrain Station lies inside Terminal complex ramp level (13.0 vs | -1003, 96 / -842, -553 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 192 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 107 | pavement x sign | 8.06 / – | – | – | 8.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1558, -903 / -1799, 72 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 193 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 187 | pavement x sign | 8.06 / – | – | – | 8.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 1420, 945 / 1697, -174 | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| 194 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 190 | pavement x sign | 8.06 / – | – | – | 8.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 1487, 864 / 1718, -70 | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| 195 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 353 | pavement x sign | 8.06 / – | – | – | 8.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 785, -861 / 292, 1127 | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| 196 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 213 | pavement x sign | 8.00 / – | – | – | 8.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -622, 1265 / 40, -1409 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 197 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 261 | pavement x sign | 8.00 / – | – | – | 8.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 366, -905 / -98, 972 | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| 198 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 280 | pavement x sign | 7.62 / – | – | – | 7.6 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -424, 1542 / 345, -1562 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 199 | STATIC | building-building | West Field Road AirTrain Station (Inbound) | Westfield Road AirTrain Station (Inbound) | building x building | 7.38 / 459.5 | 0.00 | – | roofs at the same height (13.0 / 13.0 m) over 459 m2: coplanar faces z-fight - probably one station listed twi | -2132, -320 / -2035, -712 | [00-overview](00-overview.png) |
| 200 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 3 | pavement x sign | 7.21 / – | – | – | 7.2 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1831, -1160 / -2161, 172 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 201 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 4 | pavement x sign | 7.21 / – | – | – | 7.2 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1754, -1275 / -2146, 309 | [30-rwy-10L](30-rwy-10L.png), [40-apron-3-north-west](40-apron-3-north-west.png) |
| 202 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 186 | pavement x sign | 7.21 / – | – | – | 7.2 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 1419, 944 / 1696, -173 | [30-rwy-28L](30-rwy-28L.png), [30-rwy-28R](30-rwy-28R.png) |
| 203 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 102 | pavement x sign | 7.07 / – | – | – | 7.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1546, -736 / -1711, -70 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 204 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 197 | pavement x sign | 7.07 / – | – | – | 7.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -795, 1275 / -108, -1498 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 205 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 203 | pavement x sign | 7.07 / – | – | – | 7.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -744, 1199 / -99, -1408 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 206 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 106 | pavement x sign | 7.00 / – | – | – | 7.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1556, -903 / -1797, 73 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 207 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 352 | pavement x sign | 6.08 / – | – | – | 6.1 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 785, -862 / 292, 1129 | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| 208 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 196 | pavement x sign | 6.00 / – | – | – | 6.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -796, 1275 / -110, -1499 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 209 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 260 | pavement x sign | 6.00 / – | – | – | 6.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 365, -904 / -98, 970 | [30-rwy-19L](30-rwy-19L.png), [30-rwy-19R](30-rwy-19R.png) |
| 210 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 2 | pavement x sign | 5.83 / – | – | – | 5.8 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1833, -1160 / -2163, 172 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 211 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 212 | pavement x sign | 5.83 / – | – | – | 5.8 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -620, 1264 / 41, -1407 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 212 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 50 | pavement x sign | 5.66 / – | – | – | 5.7 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -413, -353 / -530, 120 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 213 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 202 | pavement x sign | 5.66 / – | – | – | 5.7 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -743, 1198 / -99, -1406 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 214 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 79 | pavement x sign | 5.00 / – | – | – | 5.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 961, 328 / 1003, 158 | [30-rwy-28L](30-rwy-28L.png), [00-overview](00-overview.png) |
| 215 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 289 | pavement x sign | 5.00 / – | – | – | 5.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -342, 1275 / 292, -1287 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 216 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 158 | pavement x sign | 4.47 / – | – | – | 4.5 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 308, 242 / 385, -71 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 217 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 78 | pavement x sign | 4.24 / – | – | – | 4.2 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 959, 327 / 1001, 158 | [30-rwy-28L](30-rwy-28L.png), [00-overview](00-overview.png) |
| 218 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 19 | pavement x sign | 4.00 / – | – | – | 4.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1493, -967 / -1772, 159 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 219 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 83 | pavement x sign | 4.00 / – | – | – | 4.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 966, 146 / 922, 321 | [00-overview](00-overview.png) |
| 220 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 217 | pavement x sign | 4.00 / – | – | – | 4.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -554, 1168 / 55, -1292 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 221 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 51 | pavement x sign | 3.61 / – | – | – | 3.6 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -412, -351 / -529, 118 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 222 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 156 | pavement x sign | 3.61 / – | – | – | 3.6 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 261, 219 / 333, -72 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 223 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 204 | pavement x sign | 3.61 / – | – | – | 3.6 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -667, 1052 / -99, -1242 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 224 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 288 | pavement x sign | 3.61 / – | – | – | 3.6 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -341, 1273 / 292, -1285 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 225 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 205 | pavement x sign | 3.00 / – | – | – | 3.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -666, 1051 / -99, -1240 | [10-ba-B](10-ba-B.png), [30-rwy-1L](30-rwy-1L.png) |
| 226 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 216 | pavement x sign | 3.00 / – | – | – | 3.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -553, 1167 / 55, -1290 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 227 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 157 | pavement x sign | 2.83 / – | – | – | 2.8 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 259, 218 / 331, -72 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 228 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 159 | pavement x sign | 2.83 / – | – | – | 2.8 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 309, 243 / 387, -71 | [40-apron-2-south-middle](40-apron-2-south-middle.png), [00-overview](00-overview.png) |
| 229 | STATIC | building-building | Harvey Milk Terminal 1 | Terminal One AirTrain Station | building x building | 2.77 / 12.5 | 0.00 | – | walls interpenetrate: 1 % of Terminal One AirTrain Station lies inside Harvey Milk Terminal 1 (13.0 vs 20.6 m  | -893, 453 / -578, -817 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 230 | STATIC | building-building | Terminal complex ramp level | Terminal One AirTrain Station | building x building | 2.44 / 8.9 | 0.00 | – | walls interpenetrate: 1 % of Terminal One AirTrain Station lies inside Terminal complex ramp level (13.0 vs 5. | -893, 453 / -578, -818 | [10-ba-A](10-ba-A.png), [20-itb-tower](20-itb-tower.png) |
| 231 | LIVE | gse-check-mismatch | fuel mesh | gates.js placeVehicles() check rectangle | fuel x code | 2.41 / 1.7 | – | – | 1.7 m2 of the fuel mesh lies outside the 8.2 x 2.5 m rectangle the collision check uses | -836, 859 / -339, -1150 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 232 | LIVE | gse-check-mismatch | fuel mesh | gates.js placeVehicles() check rectangle | fuel x code | 2.41 / 1.7 | – | – | 1.7 m2 of the fuel mesh lies outside the 8.2 x 2.5 m rectangle the collision check uses | -1025, 954 / -462, -1322 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 233 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 207 | pavement x sign | 2.24 / – | – | – | 2.2 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -712, 1139 / -98, -1339 | [30-rwy-1L](30-rwy-1L.png), [30-rwy-1R](30-rwy-1R.png) |
| 234 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 18 | pavement x sign | 2.00 / – | – | – | 2.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -1495, -968 / -1774, 159 | [30-rwy-10L](30-rwy-10L.png), [30-rwy-10R](30-rwy-10R.png) |
| 235 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 44 | pavement x sign | 2.00 / – | – | – | 2.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | -499, -626 / -733, 321 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 236 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 82 | pavement x sign | 2.00 / – | – | – | 2.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 968, 147 / 924, 321 | [00-overview](00-overview.png) |
| 237 | STATIC | sign-on-physics-pavement | paved raster (GroundPhysics-legal ground) | hold/location sign 252 | pavement x sign | 2.00 / – | – | – | 2.0 m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there) | 216, -291 / 55, 358 | [40-apron-1-north-middle](40-apron-1-north-middle.png), [00-overview](00-overview.png) |
| 238 | ENVELOPE | envelope-rest-bridge | A11 bridge A11 (L2) (a19n, a319, b736, b737) | A11 class envelope | bellows x envelope-type; cab x envelope-type | 1.75 / 4.3 | 0.00 | 0.14 | passes 0.14 m above/below (plan overlap 4.3 m2) | -1252, 802 / -733, -1294 | [10-ba-A](10-ba-A.png), [30-rwy-1L](30-rwy-1L.png) |
| 239 | STATIC | building-building | Long Term Parking AirTrain Station | Long-Term Parking Garage 2 | building x building | 1.22 / 6.0 | 0.00 | – | walls interpenetrate: 0 % of Long Term Parking AirTrain Station lies inside Long-Term Parking Garage 2 (13.0 v | -2238, -1834 / -2835, 578 | [00-overview](00-overview.png) |
| 240 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F9 bridge F9 (L1) | Terminal complex ramp level | rotunda x building | 0.92 / 2.4 | 0.00 | 0.10 | passes 0.10 m above/below (plan overlap 2.4 m2) | -1026, -218 / -1010, -286 | [10-ba-E](10-ba-E.png), [10-ba-F](10-ba-F.png) |
| 241 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F17 bridge F17 (L1) | Terminal complex ramp level | rotunda x building | 0.66 / 1.5 | 0.00 | 0.10 | passes 0.10 m above/below (plan overlap 1.5 m2) | -1280, -216 / -1233, -406 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 242 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F19 bridge F19 (L1) | Terminal complex ramp level | rotunda x building | 0.43 / 0.7 | 0.00 | 0.10 | passes 0.10 m above/below (plan overlap 0.7 m2) | -1313, -235 / -1271, -405 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 243 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | C8 bridge C8 (L1) | Terminal complex ramp level | rotunda x building | 0.37 / 0.6 | 0.00 | 0.10 | passes 0.10 m above/below (plan overlap 0.6 m2) | -623, 463 / -335, -700 | [10-ba-B](10-ba-B.png), [10-ba-C](10-ba-C.png) |
| 244 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F21 bridge F21 (L1) | Terminal complex ramp level | rotunda x building | 0.20 / 0.2 | 0.00 | 0.10 | passes 0.10 m above/below (plan overlap 0.2 m2) | -1304, -264 / -1276, -375 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 245 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F22 bridge F22 (L1) | Terminal complex ramp level | rotunda x building | 0.12 / 0.1 | 0.00 | 0.10 | passes 0.10 m above/below (plan overlap 0.1 m2) | -1281, -259 / -1254, -369 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 246 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-building | F21 bridge F21 (L1) | Boarding Area F | rotunda x building | 0.07 / 0.0 | 0.00 | -8.70 | touching (7 cm) | -1304, -264 / -1276, -375 | [10-ba-F](10-ba-F.png), [40-apron-1-north-middle](40-apron-1-north-middle.png) |
| 247 | LIVE, REST | bridge-vdgs | C5 bridge C5 (L1) | C5 VDGS / stand sign | stair x stand-sign-back; stair x vdgs-display; stair x vdgs-display-base; stair  | 0.01 / 0.0 | 0.00 | -0.75 | touching (1 cm) | -660, 386 / -404, -649 | [10-ba-C](10-ba-C.png), [20-itb-tower](20-itb-tower.png) |
| 248 | LIVE | marker-no-body | GroundPhysics | ACA758 type ? (gate) | physics x aircraft | – / – | – | – | drawn as a marker: no model/TYPES entry, so it is not a solid body (ground.js skips it) | -513, 37 / -436, -272 | [10-ba-D](10-ba-D.png), [00-overview](00-overview.png) |
| 438 | DOCK-MAX | bridge-bridge | F11 bridge F11 (L1) | F11 bridge F11 (L2) | stair x pca-hose; stair x pca-unit; stair x tunnel3 | – / – | 0.01 | – | only 0.01 m apart | -1085, -195 / -1051, -333 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 439 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-mast | B20 bridge B20 (L1) | floodlight mast 66 | walkway x head-bar; walkway x luminaire; walkway x platform | – / – | 0.02 | – | only 0.02 m apart | -965, 861 / -452, -1212 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 440 | DOCK-MAX, DOCK-REF | bridge-bridge | G12 bridge G12 (L1) | G12 bridge G12 (L2) | stair x pca-hose; stair x pca-unit; stair x tunnel2 | – / – | 0.02 | – | only 0.02 m apart | -1615, 43 / -1409, -791 | [10-ba-G](10-ba-G.png), [00-overview](00-overview.png) |
| 441 | DOCK-MAX, DOCK-REF | bridge-bridge | F13 bridge F13 (L1) | F13 bridge F13 (L2) | stair x pca-hose; stair x tunnel3 | – / – | 0.03 | – | only 0.03 m apart | -1150, -228 / -1124, -335 | [10-ba-F](10-ba-F.png), [10-ba-G](10-ba-G.png) |
| 442 | LIVE, REST | bridge-vdgs | B24 bridge B24 (L1) | B24 VDGS / stand sign | stair x vdgs-post-base | – / – | 0.06 | – | only 0.06 m apart | -953, 951 / -399, -1286 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 443 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-mast | D9 bridge D9 (L1) | floodlight mast 47 | rotunda x head-bar; rotunda x platform | – / – | 0.09 | – | only 0.09 m apart | -495, 131 / -376, -347 | [10-ba-D](10-ba-D.png), [40-apron-2-south-middle](40-apron-2-south-middle.png) |
| 444 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | A1 bridge A1 (L1) | A1 bridge A1 (L2) | walkway x walkway | – / – | 0.13 | – | only 0.13 m apart | -1137, 545 / -752, -1012 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |
| 445 | DOCK-MAX, DOCK-REF, LIVE, REST | bridge-bridge | B26 bridge B26 (L1) | B27 bridge B27 (L1) | walkway x walkway | – / – | 0.24 | – | only 0.24 m apart | -965, 884 / -441, -1232 | [10-ba-A](10-ba-A.png), [10-ba-B](10-ba-B.png) |

### Bridge kinematics (189)

| # | kind | bridge | note |
|---|---|---|---|
| 249 | tunnel-stretch | A1 bridge A1 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 8.9/8.1/6.8 m docked to b779: sections scale with the extension instead of telescoping |
| 250 | tunnel-stretch | A1 bridge A1 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 9.6/8.7/7.3 m docked to b779: sections scale with the extension instead of telescoping |
| 251 | tunnel-stretch | A2 bridge A2 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.0/8.2/6.9 m docked to b779: sections scale with the extension instead of telescoping |
| 252 | tunnel-stretch | A2 bridge A2 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 10.7/9.7/8.1 m docked to b779: sections scale with the extension instead of telescoping |
| 253 | tunnel-stretch | A4 bridge A4 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.7/8.8/7.5 m docked to b3xm: sections scale with the extension instead of telescoping |
| 254 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.6 m = 1:10.3 |
| 255 | tunnel-stretch | A5 bridge A5 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 11.1/10.1/8.5 m docked to b779: sections scale with the extension instead of telescoping |
| 256 | tunnel-stretch | A6 bridge A6 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 8.6/7.8/6.6 m docked to a388: sections scale with the extension instead of telescoping |
| 257 | tunnel-stretch | A6 bridge A6 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 7.9/7.2/6.1 m docked to a388: sections scale with the extension instead of telescoping |
| 258 | tunnel-stretch | A8 bridge A8 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.0/8.2/6.9 m docked to b779: sections scale with the extension instead of telescoping |
| 259 | tunnel-stretch | A8 bridge A8 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 10.9/9.9/8.3 m docked to b779: sections scale with the extension instead of telescoping |
| 260 | tunnel-stretch | A9 bridge A9 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.0/8.1/6.9 m docked to b779: sections scale with the extension instead of telescoping |
| 261 | tunnel-stretch | A9 bridge A9 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 10.6/9.6/8.1 m docked to b779: sections scale with the extension instead of telescoping |
| 262 | tunnel-stretch | A10 bridge A10 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.0/8.1/6.9 m docked to b779: sections scale with the extension instead of telescoping |
| 263 | tunnel-stretch | A10 bridge A10 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 10.6/9.6/8.1 m docked to b779: sections scale with the extension instead of telescoping |
| 264 | tunnel-stretch | A11 bridge A11 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 6.7/6.1/5.1 m docked to a388: sections scale with the extension instead of telescoping |
| 265 | tunnel-stretch | A11 bridge A11 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 7.5/6.8/5.7 m docked to a388: sections scale with the extension instead of telescoping |
| 266 | tunnel-stretch | A13 bridge A13 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.4/8.5/7.2 m docked to b779: sections scale with the extension instead of telescoping |
| 267 | tunnel-stretch | A13 bridge A13 (L2) | tunnel sections 4.9/4.5/3.8 m parked -> 11.8/10.7/9.0 m docked to b779: sections scale with the extension instead of telescoping |
| 268 | tunnel-stretch | A15 bridge A15 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.3/8.5/7.2 m docked to b3xm: sections scale with the extension instead of telescoping |
| 269 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.1 m = 1:10.1 |
| 270 | tunnel-stretch | B2 bridge B2 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.2/8.4/7.1 m docked to b3xm: sections scale with the extension instead of telescoping |
| 271 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.0 m = 1:10.1 |
| 272 | tunnel-stretch | B3 bridge B3 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 8.3/7.6/6.5 m docked to b3xm: sections scale with the extension instead of telescoping |
| 273 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 22.4 m = 1:9.0 |
| 274 | tunnel-stretch | B4 bridge B4 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.8/8.9/7.6 m docked to b3xm: sections scale with the extension instead of telescoping |
| 275 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.7 m = 1:10.4 |
| 276 | tunnel-stretch | B5 bridge B5 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.5/8.7/7.4 m docked to b3xm: sections scale with the extension instead of telescoping |
| 277 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.4 m = 1:10.2 |
| 278 | tunnel-stretch | B6 bridge B6 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.2/9.2/7.8 m docked to b3xm: sections scale with the extension instead of telescoping |
| 279 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.2 m = 1:10.6 |
| 280 | tunnel-stretch | B7 bridge B7 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.3/9.4/8.0 m docked to b3xm: sections scale with the extension instead of telescoping |
| 281 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.4 m = 1:10.6 |
| 282 | tunnel-stretch | B8 bridge B8 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.1/9.2/7.8 m docked to b3xm: sections scale with the extension instead of telescoping |
| 283 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.1 m = 1:10.5 |
| 284 | tunnel-stretch | B9 bridge B9 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.9/9.0/7.6 m docked to b3xm: sections scale with the extension instead of telescoping |
| 285 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.8 m = 1:10.4 |
| 286 | tunnel-stretch | B10 bridge B10 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 7.9/7.2/6.2 m docked to b3xm: sections scale with the extension instead of telescoping |
| 287 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 21.0 m = 1:8.5 |
| 288 | tunnel-stretch | B11 bridge B11 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.6/8.7/7.4 m docked to b3xm: sections scale with the extension instead of telescoping |
| 289 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.4 m = 1:10.3 |
| 290 | tunnel-stretch | B11S bridge B11 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.0/8.1/6.9 m docked to b779: sections scale with the extension instead of telescoping |
| 291 | tunnel-stretch | B12 bridge B12 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.9/9.0/7.7 m docked to b3xm: sections scale with the extension instead of telescoping |
| 292 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.9 m = 1:10.4 |
| 293 | tunnel-stretch | B13 bridge B13 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.9/9.0/7.6 m docked to b3xm: sections scale with the extension instead of telescoping |
| 294 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.8 m = 1:10.4 |
| 295 | tunnel-stretch | B14 bridge B14 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.9/9.0/7.7 m docked to b3xm: sections scale with the extension instead of telescoping |
| 296 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.9 m = 1:10.4 |
| 297 | tunnel-stretch | B15 bridge B15 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.4/9.5/8.1 m docked to b3xm: sections scale with the extension instead of telescoping |
| 298 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.5 m = 1:10.7 |
| 299 | tunnel-stretch | B16 bridge B16 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.6/8.8/7.5 m docked to b3xm: sections scale with the extension instead of telescoping |
| 300 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.5 m = 1:10.3 |
| 301 | tunnel-stretch | B17 bridge B17 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.0/9.1/7.7 m docked to b3xm: sections scale with the extension instead of telescoping |
| 302 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.0 m = 1:10.5 |
| 303 | tunnel-stretch | B18 bridge B18 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.8/8.9/7.6 m docked to b3xm: sections scale with the extension instead of telescoping |
| 304 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.8 m = 1:10.4 |
| 305 | tunnel-stretch | B19 bridge B19 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.4/9.5/8.0 m docked to b3xm: sections scale with the extension instead of telescoping |
| 306 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.5 m = 1:10.7 |
| 307 | tunnel-stretch | B20 bridge B20 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.8/8.9/7.6 m docked to b3xm: sections scale with the extension instead of telescoping |
| 308 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.8 m = 1:10.4 |
| 309 | tunnel-stretch | B21 bridge B21 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.7/8.8/7.5 m docked to b3xm: sections scale with the extension instead of telescoping |
| 310 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.6 m = 1:10.3 |
| 311 | tunnel-stretch | B22 bridge B22 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 8.2/7.4/6.4 m docked to b3xm: sections scale with the extension instead of telescoping |
| 312 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 20.9 m = 1:8.4 |
| 313 | tunnel-stretch | B23 bridge B23 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.8/9.8/8.3 m docked to b3xm: sections scale with the extension instead of telescoping |
| 314 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.9 m = 1:10.9 |
| 315 | tunnel-stretch | B24 bridge B24 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.7/9.7/8.3 m docked to b3xm: sections scale with the extension instead of telescoping |
| 316 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.9 m = 1:10.8 |
| 317 | tunnel-stretch | B25 bridge B25 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.7/9.7/8.3 m docked to b3xm: sections scale with the extension instead of telescoping |
| 318 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.9 m = 1:10.8 |
| 319 | tunnel-stretch | B26 bridge B26 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.4/9.5/8.1 m docked to b3xm: sections scale with the extension instead of telescoping |
| 320 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 26.5 m = 1:10.7 |
| 321 | tunnel-stretch | B27 bridge B27 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.0/9.1/7.7 m docked to b3xm: sections scale with the extension instead of telescoping |
| 322 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.9 m = 1:10.5 |
| 323 | tunnel-stretch | C1 bridge C1 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.5/8.6/7.4 m docked to b3xm: sections scale with the extension instead of telescoping |
| 324 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 25.4 m = 1:10.2 |
| 325 | tunnel-stretch | C3 bridge C3 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.3/9.4/7.9 m docked to b752: sections scale with the extension instead of telescoping |
| 326 | tunnel-stretch | C4 bridge C4 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 9.3/8.5/7.2 m docked to b3xm: sections scale with the extension instead of telescoping |
| 327 | tunnel-slope | PBB slope limit 1:12 (ADA / ABA 410.1) | docked to b3xm: floor 5.4 m at the rotunda -> 2.9 m at the cab over 24.1 m = 1:9.7 |
| 328 | tunnel-stretch | C5 bridge C5 (L1) | tunnel sections 4.9/4.5/3.8 m parked -> 10.0/9.1/7.7 m docked to b752: sections scale with the extension instead of telescoping |
| ... | | | 109 more in out/draw/audit.json |

## Moving traffic (live mode, harness mock relay)

`jobs/trace2d.mjs` ran the app in live mode for 690 s (40 samples, git `a8e0538`, 2026-09-25T18:09Z) with the harness's mock relay (recorded snapshot, aircraft moved in straight lines along their track, taxiing aircraft at 0.35 x speed); `trace_audit.py` checked every sampled frame. The mock's straight-line motion takes taxiing aircraft off the pavement and through buildings by construction, so only the aircraft-aircraft rows test GroundPhysics.

Pairs in conflict: **9 gear-off-pavement**, **9 gear-off-physics-pavement**.

| kind | object A | object B | frames in conflict | first - last (s) | worst depth (m) | state |
|---|---|---|---|---|---|---|
| gear-off-pavement | UAL643 B38M | rendered paved raster (visual) | 40 / 40 | 0 - 690 | 0.0 | parked (0.0 m/s) |
| gear-off-physics-pavement | UAL643 B38M | raster OR taxi net (physics) | 40 / 40 | 0 - 690 | 0.0 | parked (0.0 m/s) |
| gear-off-pavement | SKW6001 E75L | rendered paved raster (visual) | 40 / 40 | 0 - 690 | 0.0 | parked (0.0 m/s) |
| gear-off-physics-pavement | SKW6001 E75L | raster OR taxi net (physics) | 40 / 40 | 0 - 690 | 0.0 | parked (0.0 m/s) |
| gear-off-pavement | ASA528 B737 | rendered paved raster (visual) | 36 / 40 | 0 - 690 | 0.0 | taxi (0.4 m/s) |
| gear-off-physics-pavement | ASA528 B737 | raster OR taxi net (physics) | 36 / 40 | 0 - 690 | 0.0 | taxi (0.4 m/s) |
| gear-off-pavement | UAL852 B772 | rendered paved raster (visual) | 36 / 40 | 0 - 690 | 0.0 | taxi (1.4 m/s) |
| gear-off-physics-pavement | UAL852 B772 | raster OR taxi net (physics) | 36 / 40 | 0 - 690 | 0.0 | taxi (1.4 m/s) |
| gear-off-pavement | UAL2467 B39M | rendered paved raster (visual) | 35 / 40 | 0 - 690 | 0.0 | ground-other (1.9 m/s) |
| gear-off-physics-pavement | UAL2467 B39M | raster OR taxi net (physics) | 35 / 40 | 0 - 690 | 0.0 | ground-other (1.9 m/s) |
| gear-off-pavement | SKW3490 E75L | rendered paved raster (visual) | 35 / 40 | 0 - 690 | 0.0 | ground-other (3.1 m/s) |
| gear-off-physics-pavement | SKW3490 E75L | raster OR taxi net (physics) | 35 / 40 | 0 - 690 | 0.0 | ground-other (3.1 m/s) |
| gear-off-pavement | UAL2649 A319 | rendered paved raster (visual) | 35 / 40 | 0 - 690 | 0.0 | taxi (1.5 m/s) |
| gear-off-physics-pavement | UAL2649 A319 | raster OR taxi net (physics) | 35 / 40 | 0 - 690 | 0.0 | taxi (1.5 m/s) |
| gear-off-pavement | JBU578 A321 | rendered paved raster (visual) | 35 / 40 | 0 - 690 | 0.0 | ground-other (1.5 m/s) |
| gear-off-physics-pavement | JBU578 A321 | raster OR taxi net (physics) | 35 / 40 | 0 - 690 | 0.0 | ground-other (1.5 m/s) |
| gear-off-pavement | UAL1116 B753 | rendered paved raster (visual) | 33 / 40 | 0 - 690 | 0.0 | taxi (0.6 m/s) |
| gear-off-physics-pavement | UAL1116 B753 | raster OR taxi net (physics) | 33 / 40 | 0 - 690 | 0.0 | taxi (0.6 m/s) |

## Sheet index

Vector sheets (no imagery) are in this folder; the same sheets over the imagery (`*_overlay-naip.*`, `*_overlay-google.*`) are written to `out/draw/sheets/` only (Google pixels must not be committed). Deviation dots on the vector sheets are the NAIP measurements.

| sheet | scale | paper | features (flagged) | conflicts on sheet |
|---|---|---|---|---|
| [00-overview](00-overview.png) ([svg](00-overview.svg)) | 1:7500 | A1 | 963 (392) | CLEARANCE 42, COLLISION 59, OBSTRUCTION 27, OFF-PAVEMENT 4, WARNING 313 |
| [10-ba-A](10-ba-A.png) ([svg](10-ba-A.svg)) | 1:1500 | A2 | 68 (35) | CLEARANCE 16, COLLISION 23, WARNING 73 |
| [10-ba-B](10-ba-B.png) ([svg](10-ba-B.svg)) | 1:1500 | A2 | 113 (43) | CLEARANCE 12, COLLISION 19, WARNING 82 |
| [10-ba-C](10-ba-C.png) ([svg](10-ba-C.svg)) | 1:1500 | A3 | 54 (21) | CLEARANCE 2, COLLISION 2, WARNING 33 |
| [10-ba-D](10-ba-D.png) ([svg](10-ba-D.svg)) | 1:1500 | A3 | 60 (15) | COLLISION 1, WARNING 37 |
| [10-ba-E](10-ba-E.png) ([svg](10-ba-E.svg)) | 1:1500 | A3 | 54 (19) | CLEARANCE 1, COLLISION 5, WARNING 39 |
| [10-ba-F](10-ba-F.png) ([svg](10-ba-F.svg)) | 1:1500 | A2 | 101 (40) | CLEARANCE 19, COLLISION 24, OBSTRUCTION 2, WARNING 63 |
| [10-ba-G](10-ba-G.png) ([svg](10-ba-G.svg)) | 1:1500 | A2 | 63 (33) | CLEARANCE 13, COLLISION 23, WARNING 42 |
| [20-itb-tower](20-itb-tower.png) ([svg](20-itb-tower.svg)) | 1:1500 | A2 | 58 (35) | CLEARANCE 14, COLLISION 12, WARNING 60 |
| [30-rwy-10L](30-rwy-10L.png) ([svg](30-rwy-10L.svg)) | 1:2000 | A2 | 136 (62) | OBSTRUCTION 4, WARNING 24 |
| [30-rwy-10R](30-rwy-10R.png) ([svg](30-rwy-10R.svg)) | 1:2000 | A2 | 153 (67) | OBSTRUCTION 5, WARNING 22 |
| [30-rwy-19L](30-rwy-19L.png) ([svg](30-rwy-19L.svg)) | 1:2000 | A1 | 67 (25) | OBSTRUCTION 2, WARNING 4 |
| [30-rwy-19R](30-rwy-19R.png) ([svg](30-rwy-19R.svg)) | 1:2000 | A2 | 80 (31) | OBSTRUCTION 2, WARNING 4 |
| [30-rwy-1L](30-rwy-1L.png) ([svg](30-rwy-1L.svg)) | 1:2000 | A1 | 226 (77) | CLEARANCE 16, COLLISION 23, OBSTRUCTION 1, WARNING 108 |
| [30-rwy-1R](30-rwy-1R.png) ([svg](30-rwy-1R.svg)) | 1:2000 | A1 | 175 (54) | CLEARANCE 1, COLLISION 10, OBSTRUCTION 1, WARNING 69 |
| [30-rwy-28L](30-rwy-28L.png) ([svg](30-rwy-28L.svg)) | 1:2000 | A1 | 70 (26) | WARNING 6 |
| [30-rwy-28R](30-rwy-28R.png) ([svg](30-rwy-28R.svg)) | 1:2000 | A1 | 72 (27) | WARNING 4 |
| [40-apron-1-north-middle](40-apron-1-north-middle.png) ([svg](40-apron-1-north-middle.svg)) | 1:2500 | A1 | 301 (133) | CLEARANCE 10, COLLISION 11, OBSTRUCTION 12, WARNING 38 |
| [40-apron-2-south-middle](40-apron-2-south-middle.png) ([svg](40-apron-2-south-middle.svg)) | 1:3000 | A1 | 333 (114) | CLEARANCE 23, COLLISION 34, OBSTRUCTION 6, OFF-PAVEMENT 4, WARNING 173 |
| [40-apron-3-north-west](40-apron-3-north-west.png) ([svg](40-apron-3-north-west.svg)) | 1:2000 | A1 | 54 (23) | WARNING 4 |
| [40-apron-4-north-west](40-apron-4-north-west.png) ([svg](40-apron-4-north-west.svg)) | 1:2000 | A1 | 189 (80) | OBSTRUCTION 5, WARNING 26 |

## Method, sources and limits

- **Extraction** (`jobs/extract2d.mjs`): loads `live.html?mode=snapshot` in the harness, stops the page timers, lets traffic + GroundPhysics run until every track is displayable, freezes the render loop, then reads window.SFO and calls the app's own builders with a recording geometry sink (every jet-bridge box/cylinder/tube from `gates.js bridgeGeo()` in its current, parked and docked pose; VDGS from `standGeo()`; floodlight masts from `items.js buildMasts()`; approach-light structures (posts, stations, crossbars, catwalks, huts) from `js/anim/lights.js buildPierGeometry()`; light sprites and PAPIs from `buildLiveLights()`; markings from `markings.js`; signs from `signs.js`; EMAS from `world.js buildEMAS()`; buildings from `buildLiveBuildings()`; pavement from `paintAirportMapReal()`; the OSM taxi net from `traffic.net`). Boxes and tubes are recorded as exact parallelepipeds, so heights are evaluated point by point. Module-private values are read by re-importing the module source with an extra export. Replicated by hand (listed in scene2d.json meta.replicated): the runway paint layout (GLSL; meta.paintCheck confirms each constant is still in the shader), standFits(), the GSE check rectangles, the TaxiNet test and the GroundPhysics gear points. The world frame id, git state and a hash of every loaded file are recorded; all tools refuse a scene in another frame, and this report refuses a stale one.
- **Aircraft**: live aircraft use the rendered model (.sfom, with the `fit.js` plugs / span / fin fits applied exactly as `models.js` does) or the procedural TYPES body; per-cell min/max heights make the bridge/wing/engine checks 3-D. Class envelopes = union of every non-oversize type the stand accepts (both the procedural TYPES body and the rendered model). Gear on pavement is tested twice: rendered gear on the rendered raster (visual), GroundPhysics gear points on raster OR taxi net (physics).
- **Deviation measurement** (`measure.py`, rules `2026-09-25a: stripe-start rule, building edge de-duplication, rotunda boundary = not found, approach-light stations / crossbar ends / catwalk`): profiles along the edge normal (+-10 m; +-25 m along the runway axis for runway ends/thresholds), gradient peaks (steps) with feature-level polarity consensus against shadows, width-matched ridges for paint and bars, the stripe-start rule for thresholds. Automatic picks can lock onto the wrong edge (shadow, shoulder, paint): read a number together with its overlay sheet.
- **Imagery**: NAIP (USDA, public domain, independently georeferenced; primary) - the 2024 mosaic resampled into the world frame, plus the 2022 GeoTIFF mapped world -> NAD83(2011) lat/lon -> UTM 10N; the owner's Google Maps screenshots (reference only; frame-aware registrations, re-registered to NAIP per screenshot where `imreg.py` finds a reliable shift). Google building-edge numbers are not independent of the building data: the screenshots were first registered by chamfer matching against the SFO Museum outlines.
- **Heights**: SFO Museum footprints have no heights; building heights are the app's values (sfo_buildings parts, STRUCT_H tables), bridge / mast / pier heights come from the recorded geometry.
- **Not covered**: aircraft in the air; light fixtures other than the approach-light structures are sprites without bodies (runway / taxiway edge lights, PAPI boxes are drawn as points / boxes on the runway sheets but not audited as solids); buildings in the imagery that the app does not build are not detected automatically - compare the overlay sheets; taxiway centrelines and lead-ins need <= 0.35 m/px imagery.
