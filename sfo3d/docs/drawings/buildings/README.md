# SFO building drawings: 2-D sheets to the verified dimensions

These are the owner's "drawings first" step. Plans, elevations and sections of the control tower, the International
Terminal (ITB), the domestic terminals and the landside buildings are drawn here from the verified specs. Each is
overlaid on NAIP 2024 with measured deviations, and compared with what the 3-D app builds today. The 3-D rebuild is a
later workflow.

```bash
python3 tools/buildings/draw.py              # all 13 sheets + 4 NAIP overlays + deviations.json (~60 s)
python3 tools/buildings/draw.py BT BI        # only the sheets whose id starts with BT / BI
python3 tools/buildings/draw.py --no-naip    # vector sheets only (reuses deviations.json)
```

| Input | Contents |
|---|---|
| `tools/buildings/spec_{tower,itb,domestic,landside}.json` | Every value with its tag, sources and verification record |
| `itb_naip_measurements.json`, `dom_heights.json`, `landside_naip_measurements.json` | The measurement records |
| `data/sfo_airport.json` | SFO Museum footprints |
| `js/live/terminals.js`, `js/live/airport.js`, `data/sfo_buildings.json` | The app, read only |

Code lives in `tools/buildings/`:

| File | Role |
|---|---|
| `draw.py` | Runner |
| `draw_lib.py` | Sheet engine and NAIP helpers |
| `draw_data.py` | Inputs and relief models |
| `draw_measure.py` | Deviations |
| `draw_tower.py`, `draw_itb.py`, `draw_domestic.py`, `draw_landside.py` | The sheets of each group |
| `draw_compare.py` | The app-vs-spec sheet |
| `dom_bab_roof.py` → `dom_bab_roof.json` | BA-B roof features read on NAIP 2024 (wells, bridges, skylight grids, PV fields) |

Nothing in `js/` or `data/` is changed.

## Conventions

- **Format.** ISO A3 / A2 / A1 sheets with a title block, a tag legend and notes. Each view carries a true scale
  (1:200 to 1:5000) and a scale bar. SVG files keep their text as text; the PNGs are 150 dpi with a 160-colour palette.
- **Plans** are north-up, plotted as (x, −z) in the world frame `ltp-nad83-2011` (x east, z south, metres from the
  ARP). They also show the airport s / t grid (dashed blue) and a north arrow.
- **Elevations and sections** are plotted as (u, h), in metres along the view axis and above local grade.
- **Every value is labelled `[tag source]`.** The line and text style also shows the tag:

  | Tag | Meaning | Style |
  |---|---|---|
  | `pub` | published by an original source | black, solid |
  | `obs` | measured by us | blue, solid |
  | `inf` | inferred / derived, not confirmed | orange, dashed, *italic* |
  | unknown | placeholder geometry with no source value | grey, dotted, *italic* |
  | `app` | what the 3-D app builds today | magenta, dash-dot |

- **Ranges** are given in parentheses after the value, and appear as shaded bands in the elevations.
- **The vector sheets in this folder contain no imagery pixels.** The NAIP overlays are written to
  `out/buildings/drawings/*_naip.jpg`, which is local and gitignored. NAIP is public domain (USDA FPAC-BC GEO), but
  imagery overlays stay out of the repo. No Google imagery was used.

## Sheets

| Sheet | Contents | Paper, scale |
|---|---|---|
| [BT-01](BT-01.svg) | **Tower: site and roof plan.**<br>- Base-building footprint, with its dimensions.<br>- Cab-roof caps of both height families (D 15.2 / 14.5) at the inferred centre, with the tolerance box.<br>- The x bounds of each family at its own rim (F1 67.36, F2 64.0), tagged inf.<br>- Flare and base circles of both families on the inferred axis.<br>- The landside ribbon channel (bearing 310) and its two blades; the SW wing tip at 254° / 14.0 m reproduces both oblique photos (schematic: plan not measured).<br>- FAA DOF 06-323169 (WGS 84, as the other sheets) and the OE/AAA NAD83 readings of sites 13 / 13A.<br>- The cab as imaged by NAIP 2016 / 18 / 22 / 24.<br>- The app's shaft and cab.<br>Overlay: `BT-01_naip.jpg` | A3, 1:400 |
| [BT-02](BT-02.svg) | **Tower: elevations from the ESE (airside) and the WNW (landside).**<br>- Both height families: F1 (D 15.2, rim 67.36) filled, F2 (D 14.5, rim 64.0) dash-dot; levels of F1 right, F2 left; the diameters of both at each station.<br>- The cab on its inferred centre (1.8 m off the axis, 1.6 m in these views), on its dark plinth ring (D 10.8 m).<br>- Airside: the discrete upper slots (each ~1.4 m wide, sweeping ~20°) and the long helical slot (~44°), projected from plan bearings.<br>- Landside: the glass ribbon (2 columns × ~25 rows), drawn at its plan bearing 310 (up to 2.3 m left of the axis), between the narrow NE blade and the louvred SW wing; the NE-flank slots.<br>- The DOF 245 ft envelope; the CTBUH classification of 221 ft. | A1, 1:200 |
| [BT-03](BT-03.svg) | **Tower: section through the shaft axis.**<br>- Mat, base building, cladding outline of both families.<br>- Core (published as text only; diameter unknown).<br>- Cab floor, plinth ring, glass, roof (offset cab) and the snippet-only centre column. | A3, 1:400 |
| [BI-01](BI-01.svg) | **ITB: roof plans.**<br>- Key plan, 1:2500.<br>- Main-hall wing roof, 1:750: relief-corrected outline, 5 truss lines, 5 skylights (row 1.7 m north of the fascia midpoint, all full length; planform inf, D-shaped alternative dotted), glazed tip bands (1.6 m / 3.6 m inside the fascia); the west glass wall as the band of its two canopy readings [inf]; inferred column lines and 20 columns (west line in front of the glass); DOF roof tops; eave heights (hump = DOF-anchored fit, inf); the obs and published lengths; the published rhythm; the app's roof.<br>- BA-A, 1:2000 and BA-G, 1:2500: outlines, heights, the DOF pod point.<br>- Key-value table.<br>Overlay: `BI-01_naip.jpg` | A1, 1:750 / 2000 / 2500 |
| [BI-02](BI-02.svg) | **ITB hall: elevations.**<br>- West (landside), 1:400: wing eave profile with V notches and the glazed centre arch (±2 m band), the exposed truss band above a level glass-wall head, the white columns with their struts (inf), the 705-ft glass wall on the departures curb (clear ~80 m central bay with the "SAN FRANCISCO INTERNATIONAL" lettering, fritted side bays, clear glass under the canopy) and the open cantilever tips; DOF tops, level 3, the curb canopy, 252.9 m vs 860 ft, structural rhythm.<br>- North end, 1:250: width, tip fascia, hump silhouette, the west wall band and its eave overhang, the hall-width conflict, placeholder end wall. | A1, 1:400 / 1:250 |
| [BI-03](BI-03.svg) | **ITB hall: sections.**<br>- Long section on the centre truss line: football trusses 29 ft max over the supports with an inferred taper, the centre arch, columns from level 3, the 705-ft hall, the 83-ft interior.<br>- Cross section at the inner column line: 5 truss lines at 12.12 m, 65.4 m width; the DOF tops at their stations; the west glass wall band (canopy edge / wall above the canopy) behind the column, the sight line to the camera, the entrance canopy [pub SEAONC]; the 210-ft hall measured from the wall, 5.5 m beyond the east eave (conflict).<br>- Structure table. | A1, 1:400 / 1:250 |
| [BD-01](BD-01.svg) | **Domestic T1 / T2 / T3: plan.**<br>- SFO Museum level-2 outlines.<br>- Measured lean-free roof edges for BA-B, BA-D and BA-F.<br>- BA-B raised centre band (approximate), and along the whole pier its three planted roof wells, two bridges, two skylight grids and the PV fields (NAIP, lean-corrected).<br>- BA-D head: the two round drums and the linear skylight / roof-plane edges (NAIP).<br>- BA-F: the octagonal hub, its lantern rings and the NW arm's central roof monitor (NAIP).<br>- Pier heights with their ranges.<br>- T1 Center skylights.<br>- FAA DOF points, with the refuted ones marked.<br>- Height table.<br>Overlay: `BD-01_naip.jpg` | A1, 1:2500 |
| [BD-02](BD-02.svg) | **Domestic: elevations.**<br>- Pier cross-sections on a common datum, 1:500: BA-B stepped, BA-E stepped (raised centre with the tapered edge over the clerestory, lower side roofs), BA-F, BA-D head (with its drums), BA-C, BA-A control, and the app's 14.6 m.<br>- BA-F hub cut through the lantern and the NW arm with its monitor (heights unknown, placeholders).<br>- Terminal 3 West airside field / gatehouse wall sections (field-wall window stack per the printed 10 + 2 + 10 ft chain) and the T3 level datum, 1:200, from the published CDR 95 % CD. | A1, 1:500 / 1:200 |
| [BD-03](BD-03.svg) | **Domestic: landside (curb) elevations.**<br>- Harvey Milk T1 Center, developed along its curved face towards the central garage, 1:400: clear glass under the curb canopy, the two-tier fritted curtain wall with its irregular mullions (schematic), the signage zone, PV at the roof edge; heights above the curb [inf, photo d1].<br>- Terminal 2 entry face, 1:200: the published description only (heights unknown). | A1, 1:400 / 1:200 |
| [BL-01](BL-01.svg) | **Landside: key plan.**<br>- Every landside building with its height summary.<br>- FAA DOF points.<br>- AirTrain guideway and stations.<br>- United MOC, from the imaged roof. | A1, 1:5000 |
| [BL-02](BL-02.svg) | **Landside: roof plans.**<br>- Central garage (with its void), Garages A / G and the Grand Hyatt, LTP 1 / 2, MOC, RCC, CAC.<br>- Superbay, with its spine and 8 × 17.3 m roof bays (138 m against the 134.5 m outline).<br>- Minimum-rectangle dimensions, DOF points, height table.<br>Overlay: `BL-02_naip.jpg` | A1, 1:2000 |
| [BL-03](BL-03.svg) | **Landside: principal elevations (long faces).**<br>- Massing elevations of the 10 buildings, with levels, published / DOF / inferred heights and ranges; DOF points at their projected positions.<br>- Superbay across the spine (roofs falling from the spine to ~27 m tips [inf]) and its WNW door face (8 folded bays, two ~67 m door bays); Grand Hyatt east face (podium, colonnade level, curtain wall, penthouse, masts); MOC stepped by its DOF points. | A1, 1:1000 |
| [BX-01](BX-01.svg) | **Current 3-D app vs spec.**<br>- Table of 28 items (tower rows give both families).<br>- Heights dot plot: app ×, spec ● with range bars.<br>- Tower profile overlay at 1:500 (app, family 1, family 2).<br>- ITB roof profile along its axis. | A2 |

The numbers in the files:
- `deviations.json`: every measured edge and the per-building summary (numbers only).
- `index.json`: the files of the last run.

## What is verified, inferred and still unknown

### Control tower (BT-01..03; spec verification 2026-09-26)

**Verified.**
- Published height: 221 ft. What it measures is open.
- DOF 06-323169: the 245 ft figure is the 2008 proposal envelope (4D accuracy) and is drawn as an upper bound only.
- Base-building footprint: 44.95 × 27.20 m, long axis 27.7° (SFO Museum).
- Cab-roof z: 323.5 ± 2, from four NAIP epochs.
- Photo station ratios (seams, waist, slots: "ratios confirmed; absolute inherits the rim").
- Published as text: 147-ft glass ribbon, 3 storeys, 7-ft mat, slip-formed post-tensioned core.

**Plausible / not re-checked** (spec verdicts):
- Cab-roof D 14.3 ± 1.0 m: PLAUSIBLE, stated derivation flawed; the independent EXIF check gives 14.75 ± 0.5 m.
- Flare D 22.6 m (1.58 D): PLAUSIBLE.
- Waist 9.8 m, 10.3 m at the base-building roof, cab glass head 12.3 m / sill 10.0 m: no verification record.
- A380 width ratios: ~1.5 % high (drawn divided by 1.015).

**Two height families** (buildings_tower.md 12.3). Every station is rim − k × D. The spec trio {rim 67.36 m,
D 14.3 m, base-building roof 14.2 m} fails the photo-span / NAIP-ratio test by about 3 m, so it is not a family and is
not drawn. Both self-consistent families are drawn, and neither is preferred:

| Family | D | Rim | 221 ft is at | Base-building roof | Flare | Line style |
|---|---|---|---|---|---|---|
| F1 | 15.2 m | 67.36 m | the rim | 14.1 m | 24.0 m | orange dashed, filled |
| F2 | 14.5 m | 64.0 m | the mast tips (67.4 m) | 13.1 m | 22.9 m | orange dash-dot |

**Inferred.**
- Every vertical station, in each family.
- Cab x −739 ± 5 (axis −740.5 ± 5.5). The x bounds belong to the cab-roof centre and come from the NAIP 2022 sensor field
  of view **and an assumed rim height**, so there is one pair per family: F1 (rim 67.36) ≥ −744.1 hard, ≥ −739.6 likely;
  F2 (rim 64.0, interpolated from the spec's 63.3 m pair at −0.69 / −0.62 m per m of rim) ≥ −741.8 hard, ≥ −737.5
  likely. Under F2 the tolerance box west of −741.8 is excluded and −739 lies below the likely bound.
- Cab centre offset 1.8 m (1.5 E, 1.0 N) from the axis; 1.6 m in the BT-02 / BT-03 view plane.
- Cab-roof z spread over the four epochs: 322.4–325.3 (±1.45 m about 323.85; the spec's "±1.2" was corrected).
- Landside blades: the glass ribbon (facing bearing 310, the middle of the 300–320 photo range) sits in a flat-faced
  channel between a narrow, sharp NE blade (pointed tip at about the flare rim; photos read 0–2.4 m above it) and a broad
  SW wing with a horizontally louvred face, a flat top and a rounded corner; both run full height with creases (photos
  t3 / t4, Famartin 2025, CC BY-SA 4.0). The SW wing tip at 254° / 14.0 m from the axis (2 m outside the flare) is the one
  plan point that reproduces both oblique photos (t3: 14.5 m right of the cab centre and 7.0 m beyond the ribbon; t4:
  15.7 / 6.6 m; model 14.5 / 7.6 and 15.7 / 5.8). From the BT-02 B bearing (297.7°) it projects at u +9.7, inside the
  round flare (12.0); only a wing wrapping south to ~208° (not excluded by the photos) would reach u +13.6.
- Slots (photos t1 / t2): the upper band is ~13 discrete slots (27.7° apart, ~1.4 m wide, each sweeping ~20° between
  the band seams, tops towards the NNE; none drawn in the landside sector 230–335°); the long slot is a helix from
  bearing 137 (foot) to 93 (head), ~44°.
- Plinth: a dark ring D 10.8 m, ~0.7 m high, under the cab glass on the flare shoulder [obs photo t1].
- CTBUH lists 221 ft as a height excluding antennae [pub, database classification]: it favours F1 but is not a survey.
- Overlay check: the frame model predicts the NAIP 2024 cab disc within (1.1, 1.1) m for F1 and (2.9, 1.0) m for F2,
  both at cab x −739; with F2's cab at its own likely bound (−737.5) F2 gives (1.4, 1.0) m, about as good as F1.
  **Inconclusive**: the two predictions differ by 1.9 m, less than the input uncertainty (cab x ± 5 m [inf]; the
  flying-height sd gives ± 2.7 m on the ~36 m lean). The k(x) model gives the same pair.

**Unknown.**
- What the 221 ft measures.
- The blade plan geometry (depth, width, the channel depth) beyond the wing-tip point.
- The cab glazing arc (220 / 235 / 270°) and pane layout.
- The core diameter and floor levels.
- A lean-free absolute position.

### ITB (BI-01..03; spec verification 2026-11-04)

**Verified.**
- DOF roof tops: 131 / 132 ft = 39.93 / 40.23 m (1A), at u +57.2 / −58.4, 0.8–1.1 m inside the west eave. They mark the
  inner column lines 115.5 m (379 ft) apart, which fits the published 380 ft centre span.
- Roof [obs, relief-corrected]: 252.9 × 65.4 m, axis 162.85°, 5 truss lines at 12.12 m (the 40 ft grid), 5 lens
  skylights (all full length; the row 1.5–2.2 m north of the fascia midpoint), glazed tip bands of 18.75 m (N) and
  15.75 m (S) ending 1.6 m / 3.6 m inside the fascia.
- Wing eave profile: 34.9 m at the tips → 40.08 m humps → 35.7 m notches (NAIP re-run byte-identical). The hump value
  is the fit's anchor (the DOF mean at the fitted peak |u| 67) [inf]; at the DOF stations the curve reads 0.23 / 0.45 m
  below the DOF values (inside the 1A ± 3 ft); anchored there, every eave height would rise ~0.34 m.
- SEAONC, read in full: 5 double-cantilever truss sets, 29 ft deep, 380 / 160 / 860 ft, 20 columns from level 3,
  705 × 210 × 83 ft interior.
- Piers: BA-A 17.9 m (16.9–18.8). BA-G 17.0 m (13–20, low; k(x) relief).

**Plausible / not re-checked.**
- The glazed centre arch's crown, 40.1 m ± 2: one photo; its silhouette was not re-run by the verification.
- BA-A pods: pod 1 ~55–60 m long (the note's 70 m revised), pods 2 / 3 ~52–55 m; pod 1 rises 4.9–6.9 m above the main
  roof, so its top is 22.3–25.2 m — a **conflict** with the DOF 25.9 m except at the upper end.

**Observed in photos** (i3, i4; reference only).
- The west glass wall stands on the elevated departures curb and is level-topped ~9.3 m below the wing crest (30.8 m).
- The football trusses are exposed above it along the whole facade and taper to the tips.
- Single white columns stand clear in front of the glass (each casts a shadow on it) at u −83.4 / −59.4 m, and branch
  into struts into the trusses.
- The hall stops ~21 m short of each roof tip: the tips are open cantilevers.

**Inferred.**
- Column lines at ±190 / ±270 ft (±57.9 / ±82.3 m), and the 20 columns as 5 truss lines × 4.
- The truss taper away from the supports.
- Level 3 at 11.5 m (9.6–14.8).
- The west wall's position: the band v −28.3 to −23.3 m (4.4–9.4 m inside the eave), drawn at −25.8. The NAIP
  straight facade-base line [obs] reads −21.8 at grade; the curb canopy ("entrance canopy" [pub SEAONC], ~5 m deep
  [inf]) hides the wall's foot from the camera whenever it is deeper than ~2 m (lean 0.39 m/m × 5 m), so the line is the
  canopy edge (→ −23.3) or the wall just above the canopy (→ −28.3). The earlier −26.3 (foot on L3) holds only for a
  canopy ≤ 2 m deep.
- Skylight planform: drawn as pointed lenses [inf]; NAIP shows D shapes (vaulted lens leaning east, or a D in plan:
  not settled); the D alternative is dotted on BI-01.
- The west facade (photos i1 / i4): a clear central bay ~80 m wide on a mullion grid, carrying the lettering (~65–74 m);
  white horizontally banded fritted side bays with a dark clear strip above the canopy; the central glazing head 1–3.5 m
  above the side bays' head (tentative).
- The end-wall set-back: ~19 m (the 705-ft hall centred in the roof; photo ~21 m).

**Conflicts.**
- Length: 860 ft = 262.1 m [pub] against 252.6–255.1 m [obs]. Both are drawn.
- Hall width: 210 ft = 64.0 m [pub] against at most 61.0 m under the roof east of the west wall (55.9–61.0 over the wall
  band). Resolutions: the wall nearer the eave; the hall continuing east under a lower roof (the measured east edge is a
  "fascia → lower roof fall"); a wider roof (SOM concept sketch 260 ft). BI-02 / BI-03 draw the published width from the
  wall, 5.5 m beyond the east eave.
- "Building height 144 ft" [pub]: datum unknown.
- BA-A pod 1 top: NAIP 22.3–25.2 m against DOF 25.9 m.

**Unknown.**
- Cross camber.
- Fascia depth.
- Facade mullion module, canopy depth, the end-wall outline.
- The 2024–26 rooftop PV layout.
- The BA-G pod heights.
- The pod positions.

### Domestic (BD-01..02; spec verification 2026-11-04)

**Verified.**
- The SFO Museum polygons are departure-level (level 2) floor outlines, not roofs. The lean-free roof edges lie, from the
  outline (shapely, ESE / WNW): BA-B +2.3 / −1.7 m, BA-D +2.4 / −1.4 m, BA-F 0.0 / −1.0 to −1.3 m (spec range 0–5 m outside,
  0–2 m inside). The spec's BA-F note ("1.8 m outside") was the shift from the imaged face and is corrected.
- T3 project levels and the T3W wall sections, published in the CDR 95 % CD (Oct 2023). The field-wall window stack
  (10 ft + 2 ft band + 10 ft) is the 22 ft from the international level (34 ft) to the top of the parapet (56 ft).

**Pier roof heights [obs]** (two-epoch NAIP at |s20| 1.25; every value carries ×0.95–1.05):

| Pier | Height |
|---|---|
| BA-B outer edges | 13.1 m |
| BA-B raised centre | 19.0 m (low) |
| BA-E | 12.85 m |
| BA-F | 10.49 m (DOF 10.36 m) |
| BA-D head | 8.5 m (low) |
| BA-C | 7.2 m (low) |

**Observed on NAIP for the drawings** (2026-11-04; imaged, lean not removed unless stated).
- BA-D head: two round drums, D ~19 m, each with a ~2.5–3 m oblique west-wall band, i.e. ~4–5 m above the adjacent
  roof at the D lean 0.58 m/m [obs, low]; drawn moved back by the relief of a ~13 m top [inf]. Linear skylights /
  angular roof-plane edges, drawn less the 8.5 m roof relief. (The T2 "floating angular planes" are interior ceiling
  planes per the research, not the roof.)
- BA-F hub: a regular octagon 74.2 m across the flats fits the SFO Museum outline to 0.01 m; an octagonal lantern /
  skylight pair of rings 19.4 / 13.4 m across (drawn concentric [inf]; heights unknown). The imaged ring centre lies
  8.1 m east of the hub centre: if concentric, a top of ~24 m at the 0.33 m/m lean [inf, unverified].
- BA-F NW arm: a central roof monitor / light strip ~8 m wide (low contrast), height unknown.
- BA-B, whole pier (by eye, ±3 m, `dom_bab_roof.json`; drawn less the 13.1 m outer-roof relief, 5.1 m W [inf]): three
  planted sunken roof wells on the WNW side ("roof wells" [pub CDR 2016]), two bridges across them, two skylight grids,
  three PV row fields. Their heights are not measured.
- BA-E (photo a1, Sept 2025, CC BY-SA 4.0, pier identified by position / airline): a raised PV-covered centre roof whose
  thin tapered edge overhangs a recessed glass clerestory / end wall, between lower side roofs; step ~3 m, flanks ~4.4 m,
  overhang ~1.5 m [inf, low]. Which level the measured 12.85 m fascia belongs to is not settled.
- T1 Center landside face (BD-03; photo d1, Famartin 2025, CC BY-SA 4.0): canopy soffit ~3.5–4.5 m and wall head ~12–14 m
  above the departures curb [inf, low]; face lengths along the SFO Museum outline 94.1 + 43.6 (set-back) + 93.8 m [obs].

**Inferred.**
- The BA-B step widths (7.5 / 33 / 14 m): approximate, measured on the south half only.
- The BA-E width, 42.9 m.
- T3 heights above L1.

**Refuted** (marked on BD-01):
- The T1 "70 ft trusses / reflectors" belong to the ITB.
- The BA-D DOF points and 06-035332 are not on the piers.

**Unknown.**
- T1 Center and T2 hall heights: nothing is published or measured.
- The T3 datum.
- Bay modules.
- The heights of the BA-B north half and of its roof wells / skylights.
- The departures-curb heights of T1 / T2, the T2 landside box height.
- Which state of T3W to model: under construction 2024–29; a May 2026 change adds a storey.

### Landside (BL-01..03; spec verification 2026-11-04)

**Published / DOF.**

| Building | Value |
|---|---|
| Central garage | 5 levels, 81 ft; roof poles 101 / 109 ft; void 200 ft (58.9 m [obs]) |
| Garages A / G | 9 levels; AirTrain at L7 |
| Grand Hyatt | 12 stories; lobby at the 4th floor |
| CAC | 4 × 15 ft |
| LTP 2 | 6 levels × 12 ft |
| RCC | 5 levels; "66 ft"; DOF roof outline 54 / 59 ft; DOF TANK 60 ft (06-034240: the station stair / elevator tower by inference only [inf]) |
| LTP 1 | DOF 86 / 91 ft (stair towers / helix by inference only [inf]) |
| Superbay | DOF 135 ft with a red light; "140 ft"; interior 120 ft; cantilever "over 230 ft from the centre" |
| MOC | DOF 132 / 117 / 116 ft |

**Observed.**
- LTP 1 parapet 16.5 m, by shadow.
- CAC shadow 17.4–19.2 m.
- Garage A / G helix drum tops 39.6 / 37.6 m (low).
- Superbay spine 32 m and 8 × 17.3 m roof bays. This conflicts with the published 50-ft bays. The roof runs 138 m along
  the spine against the 134.5 m outline: 1.75 m per end of overhang [inf] or outline error [unk].
- Grand Hyatt east face (photo l4 = 7391, Gregory Varnum 2019, CC BY-SA 4.0): dark metal podium under the south ~47 %,
  a recessed colonnade level, the glass slab with one spandrel per floor, a dark stepped penthouse at 0.52–0.74 of the
  face, four corner masts. The spec's "taller straight block at the north end" is not visible there [conflict].
- MOC imaged roofs (relief not removed).

**Inferred.**
- Grand Hyatt ~44 m (40–48). Not published. Its levels drawn as 13.2 pitches of 3.33 m (podium 3.2, colonnade 1, slab 9).
- Superbay cantilever tips ~27 m (22–32): photo l3 ratio, identification unverified [inf, low]; door bays ~67 m [inf].
- LTP 2 deck 60 ft.
- CAC 64 ft.

**Unknown.**
- The Garage A / G roof decks. The drawn 25 m lower end of their band is what remains of the disputed "25–30 m"
  AirTrain-photo reading; the upper end is the drum top.
- The Hyatt height.
- What the published 81 ft / 66 ft measure.
- The MOC section heights and identities.
- Facade modules.

## Overlays and measured deviations (method)

NAIP is orthorectified to a bare-earth DEM, so every roof is imaged displaced away from the camera nadir (relief
displacement): 16 m at the ITB roof and 38–40 m at the tower cab. Comparing a drawn roof with the image directly would
measure the lean, not the drawing. `draw_measure.py` therefore compares:

| Kind | Edge | Where it is checked |
|---|---|---|
| `roof` | A roof edge of known height | At its **predicted imaged position**, drawn edge + h × lean |
| `base` | A footprint (ground-contact) edge | Only on faces towards the nadir, where the facade base is visible. The window is narrow (±1.5–4 m), so the inward-displaced roof edge stays out. |
| `line` | The research's lean-free roof-edge lines | A consistency check only: derived from the same imagery |

Edge finding is the same as in `tools/imagery/outline_audit.py`:
- luminance is sampled across the edge every 0.25 m, ±6 m;
- the gradient is taken as the median along the edge, so only parallel edges count;
- the peak is refined with a parabola;
- the edge is "weak" when the peak is less than 1.25 × the next peak more than 2 m away.

Long edges are cut into ≤ 40 m pieces. Offsets are signed along the outward normal.

**Lean per building:**

| Model | Where it is used | Basis |
|---|---|---|
| `frame` | ITB hall and west facade, BA-A, tower | Frame camera fitted to five FAA DOF high-mast poles (nadir (−2768, 444), flying height 3752 m; rms 0.21 m) |
| `dom` | Domestic piers | Each pier's two-epoch 2024 lean. The along-face part is assumed east. |
| `north` | North Field | 0.30–0.33 m/m east, from shadows at the CAC and LTP 1 |
| `kmodel` | BA-G (as its spec height), Garages A / G (central garage, Hyatt extrapolated) | The ITB k(x) east model |
| `fitted` | Superbay | Its own roof shift, so the result is circular |

**Results** (median offset, median |offset|, share of edge length within 1 m / 2.5 m; good edges only):

| Building | Kind | Median | Median \|o\| | ≤ 1 m | ≤ 2.5 m | Reading |
|---|---|---|---|---|---|---|
| ITB main hall roof | roof | −0.16 | 0.27 | 74 % | 100 % | Relief-corrected outline + frame model reproduce the imaged roof (same imagery: consistency) |
| ITB west facade (wall base on L3) | base | +0.03 | 0.07 | 100 % | 100 % | 6 of 6 pieces; the L3-foot reading placed from the same NAIP line: consistency only (with a canopy > 2 m deep the drawn wall is the band −28.3 to −23.3, not this reading) |
| BA-A / BA-G | base | +0.57 / −0.57 | 0.67 / 0.81 | 68 / 75 % | 100 % | SFO Museum outline ≈ facade base within ~1 m on the west faces |
| BA-A / BA-G | roof | +0.24 / +0.13 | 2.09 / 1.05 | 46 / 40 % | 56 / 88 % | Outline vs roof at 17–18 m: overhang / outline mismatch of 1–3 m. BA-G uses k(x), as its spec height; with the frame model (which fails at G) it reads −0.60 / 1.46 / 72 % |
| Domestic piers B / C / D / E / F | base | −0.6 … −0.8 | 0.7–1.2 | 45–100 % | 100 % | Level-2 outlines sit ~0.7 m outside the visible facade base |
| Domestic piers B / C / D / E / F | roof | −0.6 … +1.9 | 0.85–2.5 | 0–68 % | 55–77 % | Mixed signs: the level-2 outline is not the roof outline (overhangs / recesses of 1–3 m, as the spec says) |
| T1 / T2 / T3 halls | base | −0.43 / −0.41 / +0.11 | 0.69–0.94 | 49–67 % | 100 % | |
| Lean-free roof-edge lines B / D / F | line | ≤ 0.2 | | | | 5 of 6 lines; the BA-F WNW line is a weak edge (not measured). Consistency only |
| Garage A / G, Hyatt, LTP 2 | base | −0.7 … +0.3 | 0.3–0.9 | 100 % | 100 % | |
| CAC / LTP 1 / RCC | roof | −0.56 / −0.98 / −1.13 | 0.56–1.62 | | 74–100 % | North-Field lean |
| Central garage | base / roof | +1.5 / +3.0 | 1.6 / 4.4 | | | Extrapolated lean and an undefined 81 ft: not a usable check |
| Superbay | base | −2.78 | 2.78 | | 29 % | Fitted lean; the outline's SE faces are 2.8 m off |
| Tower base building | base / roof | −0.75 / +1.8 | | | | Roof at the F1 14.1 m; only 1–2 good edges of 3; weak |

## The app today vs the spec (BX-01)

The biggest gaps:
- **ITB hall roof.** The app tops it at the 83-ft *interior* height plus a 0.6 m cross crown (21.4–27.1 m) instead of
  34.9–40.1 m. Its roof is 237 × 82 m (spec 252.9 × 65.4 m), centred 35 m east of the measured roof and turned 2.9°.
  Its 20 columns stand in 2 rows of 10 across the width at s = ±57.9 m, not on 5 truss lines × 4.
- **Tower.** The app puts the shaft 7.2 m south of the inferred axis. Its cab roof is D 20.3 m (F1 15.2 / F2 14.5 m)
  and its rim is 2.1–5.5 m too low (61.9 m against F2 64.0 / F1 67.36 m).
- **Piers.** Every pier is 14.6 m; the measured roofs range from 7.2 m (BA-C) to 19.0 m (the BA-B raised centre).
  The app also uses the level-2 outlines as roof outlines.
- **Landside.**
  - The Superbay is a 34 m flat box (spine DOF 41.15 m, cantilever roofs falling to ~27 m tips).
  - The RCC is 26 m (roof outline 16.5–18.0 m; "66 ft").
  - The Grand Hyatt is 38 m (~44 m, inferred).
  - The central garage is 22 m (81 ft = 24.7 m).
  - The United MOC hangars are not built at all.

## Limits

- **Planimetric accuracy.**
  - Footprints are SFO Museum polygons, of unknown survey accuracy (±1.5–5 m).
  - Relief-corrected NAIP roofs are ±1.5 m.
  - Every NAIP height inherits its lean model.
- **Schematic geometry.** Elevations draw the published or measured heights over schematic massing. Where a facade
  module, floor level or cross camber is not published, it is drawn as a dotted placeholder.
- **Two height sets.** The tower and ITB heights carry their spec ranges. The tower carries two families (F1, F2) and
  is not to be built from one value until the owner or a new source decides between them.
- **Photo-derived form.** The tower blades, slots and plinth, the ITB facade (wall head, central bay, columns, open
  tips), BA-E's step, the T1 landside face, the Superbay roof fall, the Hyatt east face and the BA-B / BA-D / BA-F roof
  features are drawn from reference photos and NAIP; their dimensions are tagged with the method and are not published.
  Reference photos are in `refs/cache/buildings/review_likeness/` (licences in its `SOURCES.json`; not committed).
