# SFO building drawings: 2-D sheets to the verified dimensions

These are the owner's "drawings first" step. Plans, elevations and sections of the control tower, the International
Terminal (ITB), the domestic terminals and the landside buildings are drawn here from the verified specs. Each is
overlaid on NAIP 2024 with measured deviations, and compared with what the 3-D app builds today. The 3-D rebuild is a
later workflow.

```bash
python3 tools/buildings/draw.py              # all 12 sheets + 4 NAIP overlays + deviations.json (~45 s)
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
| [BT-01](BT-01.svg) | **Tower: site and roof plan.**<br>- Base-building footprint, with its dimensions.<br>- Cab-roof cap D 14.3 at the inferred centre, with the tolerance box and the x ≥ −744.1 bound.<br>- Flare, waist and base circles on the inferred axis.<br>- Ribbon bearing, and the FAA OE/AAA sites 13 / 13A.<br>- The cab as imaged by NAIP 2016 / 18 / 22 / 24.<br>- The app's shaft and cab.<br>Overlay: `BT-01_naip.jpg` | A3, 1:400 |
| [BT-02](BT-02.svg) | **Tower: elevations from the ESE (airside) and the WNW (landside, glass ribbon).**<br>- Diameters and every station as level marks.<br>- Both height families: the spec values solid, family 2 dotted.<br>- The DOF 245 ft envelope. | A1, 1:200 |
| [BT-03](BT-03.svg) | **Tower: section through the shaft axis.**<br>- Mat, base building, cladding outline.<br>- Core (published as text only; diameter unknown).<br>- Cab floor, glass, roof and the snippet-only centre column. | A3, 1:400 |
| [BI-01](BI-01.svg) | **ITB: roof plans.**<br>- Key plan, 1:2500.<br>- Main-hall wing roof, 1:750: relief-corrected outline, 5 truss lines, 5 lens skylights, glazed tip bands; inferred column lines and 20 columns; DOF roof tops; eave heights; the obs and published lengths; the published rhythm; the app's roof.<br>- BA-A, 1:2000 and BA-G, 1:2500: outlines, heights, the DOF pod point.<br>- Key-value table.<br>Overlay: `BI-01_naip.jpg` | A1, 1:750 / 2000 / 2500 |
| [BI-02](BI-02.svg) | **ITB hall: elevations.**<br>- West (landside), 1:400: eave profile, crown, DOF tops, level 3, column lines, 252.9 m vs 860 ft, structural rhythm.<br>- North end, 1:250: width, tip fascia, hump silhouette, placeholder end wall. | A1, 1:400 / 1:250 |
| [BI-03](BI-03.svg) | **ITB hall: sections.**<br>- Long section on the centre truss line: football trusses 29 ft max over the supports with an inferred taper, columns from level 3, the 705-ft hall, the 83-ft interior.<br>- Cross section at the inner column line: 5 truss lines at 12.12 m, 65.4 m width.<br>- Structure table. | A1, 1:400 / 1:250 |
| [BD-01](BD-01.svg) | **Domestic T1 / T2 / T3: plan.**<br>- SFO Museum level-2 outlines.<br>- Measured lean-free roof edges for BA-B, BA-D and BA-F.<br>- BA-B raised centre band (approximate).<br>- Pier heights with their ranges.<br>- T1 Center skylights.<br>- FAA DOF points, with the refuted ones marked.<br>- Height table.<br>Overlay: `BD-01_naip.jpg` | A1, 1:2500 |
| [BD-02](BD-02.svg) | **Domestic: elevations.**<br>- Pier cross-sections on a common datum, 1:500: BA-B stepped, BA-E, BA-F, BA-D head, BA-C, BA-A control, and the app's 14.6 m.<br>- Terminal 3 West airside field / gatehouse wall sections and the T3 level datum, 1:200, from the published CDR 95 % CD. | A1, 1:500 / 1:200 |
| [BL-01](BL-01.svg) | **Landside: key plan.**<br>- Every landside building with its height summary.<br>- FAA DOF points.<br>- AirTrain guideway and stations.<br>- United MOC, from the imaged roof. | A1, 1:5000 |
| [BL-02](BL-02.svg) | **Landside: roof plans.**<br>- Central garage (with its void), Garages A / G and the Grand Hyatt, LTP 1 / 2, MOC, RCC, CAC.<br>- Superbay, with its spine and 8 × 17.3 m roof bays.<br>- Minimum-rectangle dimensions, DOF points, height table.<br>Overlay: `BL-02_naip.jpg` | A1, 1:2000 |
| [BL-03](BL-03.svg) | **Landside: principal elevations (long faces).**<br>- Massing elevations of the 10 buildings, with levels, published / DOF / inferred heights and ranges.<br>- Superbay across the spine; MOC stepped by its DOF points. | A1, 1:1000 |
| [BX-01](BX-01.svg) | **Current 3-D app vs spec.**<br>- Table of 28 items.<br>- Heights dot plot: app ×, spec ● with range bars.<br>- Tower profile overlay at 1:500 (app, spec, family 2).<br>- ITB roof profile along its axis. | A2 |

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
- Diameters, from photos [obs]:
  - cab roof 14.3 ± 1.0 m; an independent EXIF check gives 14.75 ± 0.5 m;
  - flare 22.6 m;
  - waist 9.8 m;
  - 10.3 m at the base-building roof.
- Published as text: 147-ft glass ribbon, 3 storeys, 7-ft mat, slip-formed post-tensioned core.

**Inferred.**
- Every vertical station: the photo ratios are anchored at the rim, and the rim height is disputed. The verification
  found two self-consistent families, and both are drawn:
  - the spec values, solid: rim 67.36 m, D 14.3;
  - family 2, dotted: rim 64.0 m, D 14.5, with 221 ft at the mast tips.
- Axis x: −739 ± 5 (hard bound ≥ −744.1).
- Base-building roof: 14.2 m (12.7–16.5).
- Roof garden: +12.5 m.
- Overlay check: the frame model predicts the NAIP 2024 cab disc within (1.1, 1.1) m for a 67.36 m rim, and
  (2.9, 1.0) m for 64.0 m. This leans towards the 221-ft rim but does not decide it, because the cab x is itself
  ± 5 m.

**Unknown.**
- What the 221 ft measures.
- The landside fin / prow plan.
- The cab glazing arc (220 / 235 / 270°) and pane layout.
- The core diameter and floor levels.
- A lean-free absolute position.

### ITB (BI-01..03; spec verification 2026-11-04)

**Verified.**
- DOF roof tops: 131 / 132 ft = 40.08 m (1A). They mark the inner column lines 115.5 m (379 ft) apart, which fits the
  published 380 ft centre span.
- Roof [obs, relief-corrected]: 252.9 × 65.4 m, axis 162.85°, 5 truss lines at 12.12 m (the 40 ft grid), 5 lens
  skylights, glazed tip bands of 18.75 m (N) and 15.75 m (S).
- Eave profile: 34.9 m at the tips → 40.08 m humps → 35.7 m notches. The 40.1 m crown rests on one photo.
- SEAONC, read in full: 5 double-cantilever truss sets, 29 ft deep, 380 / 160 / 860 ft, 20 columns from level 3,
  705 × 210 × 83 ft interior.
- Piers: BA-A 17.9 m (16.9–18.8). BA-G 17.0 m (13–20, low).

**Inferred.**
- Column lines at ±190 / ±270 ft (±57.9 / ±82.3 m), and the 20 columns as 5 truss lines × 4.
- The truss taper away from the supports.
- Level 3 at 11.5 m (9.6–14.8).
- The end-wall set-back.

**Conflicts.**
- Length: 860 ft = 262.1 m [pub] against 252.6–255.1 m [obs]. Both are drawn.
- "Building height 144 ft" [pub]: datum unknown.

**Unknown.**
- Cross camber.
- Fascia depth.
- Facade mullion module.
- The 2024–26 rooftop PV layout.
- The BA-G pod heights.
- The pod positions.

### Domestic (BD-01..02; spec verification 2026-11-04)

**Verified.**
- The SFO Museum polygons are departure-level (level 2) floor outlines, not roofs. The lean-free roof edges lie
  ~1.8–2.3 m outside them on the ESE faces and 1.3–1.7 m inside them on the WNW faces.
- T3 project levels and the T3W wall sections, published in the CDR 95 % CD (Oct 2023).

**Pier roof heights [obs]** (two-epoch NAIP at |s20| 1.25; every value carries ×0.95–1.05):

| Pier | Height |
|---|---|
| BA-B outer edges | 13.1 m |
| BA-B raised centre | 19.0 m (low) |
| BA-E | 12.85 m |
| BA-F | 10.49 m (DOF 10.36 m) |
| BA-D head | 8.5 m (low) |
| BA-C | 7.2 m (low) |

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
- The north half of BA-B.
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
| RCC | 5 levels; "66 ft"; DOF roof outline 54 / 59 ft; station tower 60 ft |
| Superbay | DOF 135 ft with a red light; "140 ft"; interior 120 ft; cantilever "over 230 ft from the centre" |
| MOC | DOF 132 / 117 / 116 ft |

**Observed.**
- LTP 1 parapet 16.5 m, by shadow.
- CAC shadow 17.4–19.2 m.
- Garage A / G helix drum tops 39.6 / 37.6 m (low).
- Superbay spine 32 m and 8 × 17.3 m roof bays. This conflicts with the published 50-ft bays.
- MOC imaged roofs (relief not removed).

**Inferred.**
- Grand Hyatt ~44 m (40–48). Not published.
- LTP 2 deck 60 ft.
- CAC 64 ft.

**Unknown.**
- The Garage A / G roof decks.
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
| `frame` | ITB, BA-A, BA-G, tower | Frame camera fitted to five FAA DOF high-mast poles (nadir (−2768, 444), flying height 3752 m; rms 0.21 m) |
| `dom` | Domestic piers | Each pier's two-epoch 2024 lean. The along-face part is assumed east. |
| `north` | North Field | 0.30–0.33 m/m east, from shadows at the CAC and LTP 1 |
| `kmodel` | Garages A / G (central garage, Hyatt extrapolated) | The ITB k(x) east model |
| `fitted` | Superbay | Its own roof shift, so the result is circular |

**Results** (median offset, median |offset|, share of edge length within 1 m / 2.5 m; good edges only):

| Building | Kind | Median | Median \|o\| | ≤ 1 m | ≤ 2.5 m | Reading |
|---|---|---|---|---|---|---|
| ITB main hall roof | roof | −0.16 | 0.27 | 74 % | 100 % | Relief-corrected outline + frame model reproduce the imaged roof (same imagery: consistency) |
| BA-A / BA-G | base | +0.57 / −0.64 | 0.67 / 0.80 | 68 / 75 % | 100 % | SFO Museum outline ≈ facade base within ~1 m on the west faces |
| BA-A / BA-G | roof | +0.24 / −0.60 | 2.09 / 1.46 | 46 / 43 % | 56 / 72 % | Outline vs roof at 17–18 m: overhang / outline mismatch of 1–3 m |
| Domestic piers B / C / D / E / F | base | −0.6 … −0.8 | 0.7–1.2 | 45–100 % | 100 % | Level-2 outlines sit ~0.7 m outside the visible facade base |
| Domestic piers B / C / D / E / F | roof | −0.6 … +1.9 | 0.85–2.5 | 0–68 % | 55–77 % | Mixed signs: the level-2 outline is not the roof outline (overhangs / recesses of 1–3 m, as the spec says) |
| T1 / T2 / T3 halls | base | −0.43 / −0.41 / +0.11 | 0.69–0.94 | 49–67 % | 100 % | |
| Lean-free roof-edge lines B / D / F | line | ≤ 0.2 | | | | Consistency only |
| Garage A / G, Hyatt, LTP 2 | base | −0.7 … +0.3 | 0.3–0.9 | 100 % | 100 % | |
| CAC / LTP 1 / RCC | roof | −0.56 / −0.98 / −1.13 | 0.56–1.62 | | 74–100 % | North-Field lean |
| Central garage | base / roof | +1.5 / +3.0 | 1.6 / 4.4 | | | Extrapolated lean and an undefined 81 ft: not a usable check |
| Superbay | base | −2.78 | 2.78 | | 29 % | Fitted lean; the outline's SE faces are 2.8 m off |
| Tower base building | base / roof | −1.7 / +1.7 | | | | Only 2–3 edges; weak |

## The app today vs the spec (BX-01)

The biggest gaps:
- **ITB hall roof.** The app tops it at the 83-ft *interior* height (21.4–26.5 m) instead of 34.9–40.1 m. Its roof is
  237 × 82 m (spec 252.9 × 65.4 m), centred 35 m east of the measured roof and turned 2.9°.
- **Tower.** The app puts the shaft 7.2 m south of the inferred axis. Its cab roof is D 20.3 m (spec 14.3–14.75 m)
  and its rim is 1–5.5 m too low (61.9 m against 63.0–67.6 m).
- **Piers.** Every pier is 14.6 m; the measured roofs range from 7.2 m (BA-C) to 19.0 m (the BA-B raised centre).
  The app also uses the level-2 outlines as roof outlines.
- **Landside.**
  - The Superbay is 34 m (DOF 41.15 m).
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
- **Two height sets.** The tower and ITB heights carry their spec ranges. The tower carries two families and is not to
  be built from one value until the owner or a new source decides between them.
