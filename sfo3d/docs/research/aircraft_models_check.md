# Aircraft models: dimension, gear, door and type-mapping check

Status: research note, 24 Sep 2026. Tool: `tools/models/check_dims.py` (re-run it after any change to `data/models/*.sfom`,
`js/aircraft/types.js` or `js/live/aircraft.js`). Nothing in `data/` or `js/` was modified.

**Scope.** For every converted model (`data/models/*.sfom`, 21 models) and every ICAO designator in
`TYPE_MODELS` (`js/live/aircraft.js`), I compared what the app renders and uses with the manufacturers'
airport-planning documents:

- overall length, wingspan and height;
- nose- and main-gear positions, and track;
- the doors that the jet bridges dock to (L1, and L2 on wide-bodies);
- the ICAO type → model mapping, including the plug-stretch rule for derived variants.

Threshold: I flag anything more than 1 % off. For positions (gear, doors), that means more than 1 % of the aircraft's length.

Legend for provenance:

- **obs**: read directly from the manufacturer document, with the page or figure given.
- **inf**: derived from one. Examples: a door centre computed from a dimensioned door edge plus the door width, or a value scaled off a drawing.
- **unverified**: not checked against a primary source.

## 1. Summary: what is wrong, most important first

1. **The jet bridges dock at the wrong fuselage station on every type.** `TYPES.doors[0]` (L1) is 0.9–3.2 m too far forward on all types. [corrected by verifier: this is true for most types, not all. On the A330 family (A332/A333/A339) `doors[0]` is 5.80 m against 5.85 m (−0.05 m), so the bridge docks 0.45 m *aft* of the door centre. On the A380 `doors[0]` is −0.72 m and the dock −0.22 m, neither flagged. The A320 family is −0.92 to −0.94 m and the A350 −1.02 m. The A220 has no reference. Source: `check_dims.py --json`, re-run by the verifier.] `gates.js` docks at `doors[x] + 0.5`, but the procedural shader treats `doors[x]` as the door *centre* (`js/shaders/aircraft.js` line 105: box centred on `uDoors[i]`, half-width 0.5). So the two conventions disagree by 0.5 m.

   | Type | Where the bridge docks | L1 centre (ACAP) | Error | Source |
   |---|---|---|---|---|
   | 737 NG / MAX | 3.8 m | 5.03 m | 1.23 m | Boeing D6-38A004 §2.7.1 p.2-26 |
   | 757 | 4.1 m | 5.05 m | 0.95 m | D6-58327 p.2-21, "longitudinal distance from nose to center of door" |
   | 787 | 5.7 m | 6.30 m | 0.6 m | |
   | 747-8 | 6.8 m | 9.5 m | 2.7 m | |
   | E175 | 3.4 m | ≈5.1 m | ≈1.7 m | inf |
   | CRJ700 / CRJ900 | 3.3 m | 4.68 m | 1.4 m | |

   For the wide-bodies the second bridge docks at `doors[1] + 0.5`. It is also off:

   | Type | L2 error |
   |---|---|
   | A350-1000 | −5.2 m |
   | 747-8 | −5.6 m |
   | 787-10 | −3.3 m |
   | A330-200 | +3.5 m |
   | 787-8 | +2.8 m |
   | 767-400 | −4.6 m |

   The imported models themselves have the doors in the right place where the source mesh has door objects:

   | Mesh | Position | ACAP |
   |---|---|---|
   | A320 `DoorL1` | 4.99 m | 5.04 m |
   | CRJ700/900 `LeftDoor` | 4.71 m | 4.68 m |
   | A220-100 `doorFL` | 4.96 m | not dimensioned |
   | E190 `door.l1` | 5.48 m | ≈5.14 m (inf) |

   So on the screen, the bridge cab stops beside a blank piece of fuselage ahead of the painted door.

2. **Main and nose gear positions in `TYPES` are shifted fore or aft by 0.5–2.7 m.** The procedural gear is drawn at these positions under gear-less models:

   | Type | Main gear | Nose gear |
   |---|---|---|
   | E175 | +2.67 m aft (wheelbase 14.8 m vs 11.40 m, +30 %) | |
   | E190 | +2.64 m | |
   | 747-400 / -8 | −2.2 m | |
   | 787 family | +1.76 m | +1.89 m |
   | A350 | +1.7 m | +1.67 m |
   | 757 | −1.2 m | −1.3 m |
   | 777 | +1.1 m | |
   | A220-300 | +1.0 m | |
   | 737 | +0.6 m | +0.6 m |

   Because `LiveAircraft.placement()` translates the model by `T.xMain`, the same errors also move every model relative to its main gear.

3. **The wingspan in `TYPES` is wrong for derived airframes.** Ground physics uses this value (planform collision), and far-LOD aircraft draw with it.

   | Type | TYPES span | Real span | Error |
   |---|---|---|---|
   | CRJ200 | 24.85 m | 21.23 m | +17 % |
   | CRJ700 | 24.85 m | 23.25 m | +6.9 % |
   | A330-200 / -300 | 64.75 m (the A350's) | 60.30 m | +7.4 % |
   | 767-300 | 50.9 m | 47.57 m | +7.0 % |
   | 747-400 | 68.4 m | 64.44 m | +6.1 % |
   | 777-200/-200ER, procedural | 64.8 m | 60.93 m | +6.4 % |
   | A319 / A320 / A321 (ceo, wing-tip fence) | | 34.10 m | +5 % |
   | E75S | | 26.00 m | +10 % |

   The E175 main-gear track is 5.94 m against a real 5.20 m (+14 %). The CRJ200 track is 4.00 m against about 3.14 m (inf).

4. **Rendered spans are wrong where one model stands in for a different wing.** These are mapping issues:

   | ICAO | Rendered with | Rendered span | Real span | Error |
   |---|---|---|---|---|
   | E75L | short-wing FAM E175 | 26.3 m | 28.65 m | −8.3 % |
   | A20N / A19N / A21N | fence-tip A320-family models | | 35.80 m (sharklet) | −5 to −7 % |
   | A339 (A330-900) | A330-300 model | 60.5 m | 64.00 m | −5.5 % |
   | B764 | 767-300 model | 46.1 m | 51.92 m | −11 % |
   | B752 / B753 | | | | +2.6 to +2.9 % |
   | B763 | | | | −3.1 % |

5. **Mis-mapped designators.**

   | ICAO | Mapped to | Length used | Real length | Error | Other |
   |---|---|---|---|---|---|
   | B3XM (737-10) | b39m | 42.16 m | 43.79 m | −3.7 % | wheelbase 17.1 vs 18.34 m |
   | B779 (777-9) | b77w | 73.86 m | 76.73 m | −3.7 % | |
   | E195 | e190 | 36.24 m | 38.65 m | −6.2 % | |
   | E290 / E295 | e190 (E1 airframe) | | | | E2 wing and fuselage not modelled; no primary numbers downloaded |
   | A338 | A330-200 airframe | | | | A330neo span 64.00 m vs 60.3 m |
   | A318, B736, CRJX | | | | | no reference extracted; A318 and B736 are shorter than the airframe they map to (Boeing and Airbus numbers not checked here) |

   B74F is not an ICAO Doc 8643 designator (747-400F files under B744); that mapping is harmless.

6. **Several aircraft are seated too high or too low.**
   - **CRJ700/900.** The bridge cab floor comes out 1.1 m above the door sill: 2.8–2.9 m against a sill of 1.73 m (CSP B-020 / C-020 00-02-04 Table 1).
   - **A330-300.** The fuselage top renders 0.93 m too high: 8.67 m against 7.58–7.74 m. Seating the model at the published height (16.79 m) leaves its fuselage floating, because the FAM A330 fin is about 1 m too short relative to the fuselage.
   - **A320neo.** The bridge floor is 0.40 m below the D1 sill.
   - **737 family.** The FlightGear 737-800 with gear is 0.3–0.5 m too tall: 12.94 m against 12.37–12.62 m (NG) and 11.86–12.45 m (MAX). The fuselage top is right: 5.58 m against 5.41–5.56 m.

7. **The plug-stretch rule inserts the forward plug in the wrong place for most wide-bodies.** `stretchFor` cuts 1 m ahead of the wing root. But the ACAP door tables show that the forward plug lies **ahead of door 2** on these types:

   | Pair | Door 2 moves by |
   |---|---|
   | 787-8 → -9 | +3.04 m |
   | 787-8 → -10 | +6.09 m |
   | 747-400 → 747-8 | +4.1 m |
   | 767-300 → 767-400 | +3.38 m |
   | A330-300 → A330-200 | −3.18 m |
   | A350-900 → A350-1000 | +4.44 m |

   So a stretched model's painted door 2 stays at the base type's station, and `derive()` does not move `doors[1]` either. The 737 and 757 plugs are consistent with the rule: 757-300 door 2 is unchanged at 13.99 m, and the 737 wheelbase deltas match within 0.2 m.

8. **Licence of the A220 models: resolved.** This was open in `docs/HANDOFF.md` §7 item 12.
   - FAM `bcs1/` has no licence file, but its source is the pinned submodule `bcs1/CSeries`, which points to FGMEMBERS/CSeries @8a8223f3. That repository carries `COPYING`, GPL-2.0.
   - The proof of derivation is twofold:
     - the embedded `cs300.png` in `BCS3.glb` is pixel-identical (mean abs. difference 0.000) to `Models/cs300.png` at that commit;
     - the node names in `BCS1.glb` (`doorFL`, `doorRR`, `cargodoor`, `cockpitdoor`, `geardoorF1`, `gearLdoor`) are the object names in `Models/CS100.ac` at that commit.

   All the other sources are GPL-2.0 or "GPL v2 or later". The details are in `docs/research/liveries.md` §4.

   [corrected by verifier] There are two refinements.
   - **A380 exception.** A380-omega @ffb200c2 also contains `License/README`. It records that the textures by Toryx, Tapaninen and Muraleedharan were CC-BY-NC 3.0 until 31 May 2015, and the relicensing note covers only Muraleedharan's work. The A380 textures' GPL status is therefore unverified; see liveries.md §4.1.
   - **BCS1 texture.** The derivation is stronger than stated. `livery_sources.py` reports BCS1's embedded `cs100.png` as mad 0.41 against `Models/cs100.png`, but that is a different file. The verifier compared it with the other CSeries textures at @8a8223f3: `cs100.png` is `Models/bombardier.png` (= `Liveries/CS100/Bombardier.png`, 4000×4000, resampled to 4000×2000) at mad 0.0008, and `engines`, `interior` and `chrome` are identical (mad 0.000).

What is right:

- Length is right on every modelled type, because `TYPES.L` is used as the scale: all within 0.1 %, except the mapping errors above.
- The rendered spans of the A319/A321 ceo, A330-300, A350, A380, 747-8, 787 and CRJ200/700 are within 0.8 %.
- The heights of the seated gear-less models reproduce the `HEIGHT` table, which matches the ACAP within 1 % for the A320neo, A330-300, A350, A380, 747, 757, 767 and 787.

## 2. How the app uses the numbers (what was checked)

- **Scale.** `LiveAircraft.placement()` in `js/live/aircraft.js` scales each model uniformly by
  `s = T.L / (model L + plugs)`.
  - Rendered length = `TYPES.L`.
  - Rendered span = model span × s.
  - Rendered height:
    - gear-less models: `T.Hc + finTop·s`, where `seatType` sets `T.Hc = HEIGHT[t] − finTop·s` from the `HEIGHT` table;
    - the only model with gear (`b738`): (finTop − lowest wheel) · s.
- **Stretch** (`stretchFor`): vertices aft of `cut1 = −(B.rootLE − 1)` move by `d1 = T.rootLE − B.rootLE`, and those aft of `cut2`
  (wing trailing edge + 1 m) move by `d1 + d2`.
- **Door docking** (`gates.js doorOf`): the bridge cab docks at x = `T.doors[which−1] + 0.5` from the nose,
  y = `T.Hc − 0.3·T.R`. `which` = 1 for every bridge, and 2 for the second bridge on class E/F stands (`docks()`).
- **Gear.** The procedural gear is built at `T.gear.main[].x` and `T.gear.nose.x` (nose-based, `js/aircraft/model.js` l.100).
  `placement()` translates the model by `T.xMain` (the mean of the main units).
- **What the tool measures.** It decodes every `.sfom` exactly like `js/live/models.js`. It re-derives the same normalised frame from the FAM
  source `.glb` (copying `convert()`), so it can measure the model's **own door and gear-door meshes**. It loads `TYPES` with
  node, and `TYPE_MODELS`, `HEIGHT` and `MODEL_BASE` by parsing `js/live/aircraft.js`.

Run: `python3 tools/models/check_dims.py [--md out.md] [--json out.json]`. It needs `node`, and optionally `refs/cache/src/fam3d`
(`git clone https://github.com/Ysurac/FlightAirMap-3dmodels`) for the door-mesh pass. It prints 182 flagged items at the time of writing.

## 3. Reference documents (all downloaded to `refs/cache/acap/`, gitignored)

| Types | Document | Where |
|---|---|---|
| 737-700/800/900ER | Boeing D6-58325-7 Rev C (Oct 2025), 737NG Airplane Characteristics for Airport Planning | boeing.com/content/dam/boeing/v2/airports/acaps/737NG_REV_C.pdf — §2.2.4/2.2.6/2.2.8, §2.3.1–2.3.3, §2.7.1 |
| 737-8/-9/-10 | Boeing D6-38A004 Rev K (Jul 2025) | …/acaps/737MAX_RevK.pdf — §2.2.2–2.2.4 p.2-10..12, §2.3.2–2.3.4, §2.7.1 p.2-26 (door table) |
| 757-200/-300 | D6-58327 Rev H (Dec 2024) | …/acaps/757_Rev_H.pdf — §2.2.1–2.2.2, §2.3.1–2.3.2, §2.7.1 p.2-21 |
| 767 | D6-58328 Rev K (Dec 2024) | …/acaps/767_REV_K.pdf — §2.2.2, §2.2.4, §2.3.2, §2.3.4, §2.7.1 p.2-30 |
| 777-200/-200ER | D6-58329 Rev E (Dec 2024) | …/acaps/777-200-200ER-300_Rev_E.pdf — §2.2.1 p.2-8, §2.3.1, §2.7.1 p.2-23 |
| 777-200LR/-300ER | D6-58329-2 Rev G (Dec 2024) | …/acaps/777-200LR-300ER-F_Rev_G.pdf — §2.2.1–2.2.2, §2.3.1–2.3.2, §2.7.1 p.2-19 |
| 777-9 | D6-86073 Rev G (Sep 2025, preliminary) | …/acaps/777X_Rev_G.pdf — Fig 2-1, §2.3.1 |
| 787-8/-9/-10 | D6-58333 Rev Q (Oct 2025) | …/acaps/787_ACAP_Rev_Q.pdf — §2.2.1–2.2.3 p.2-5..7, §2.3.1–2.3.3, §2.7.1 p.2-16 |
| 747-400 | D6-58326-1 Rev F (Dec 2024) | …/acaps/747-400_Rev_F.pdf — §2.2.1 p.2-14, §2.3.1, §2.7.1 p.2-35 |
| 747-8 | D6-58326-3 Rev E (Jan 2026) | …/acaps/747-8_Rev_E.pdf — §2.2.2 p.2-5, §2.3.2, §2.7.1 p.2-14 |
| A319 | Airbus AC A319 (Rev Jul 15/25) | aircraft.airbus.com/sites/g/files/jlcbta126/files/2025-07/AC_A319_20250715.pdf — FIG-2-2-0-991-002/-008, FIG-2-7-0-991-002 |
| A320/A320neo | AC A320 (Rev Jun 01/24) | …/2025-01/AC_A320_0624.pdf — FIG-2-2-0-991-004/-009, FIG-2-3-0-991-032 (p.2-3-0 6), FIG-2-7-0-991-003 |
| A321/A321neo | AC A321 (Rev Jul 15/25) | …/2025-07/AC_A321_20250715.pdf — FIG-2-2-0-991-005/-010, FIG-2-7-0-991-004/-047 |
| A330 (-200/-300/-800/-900) | AC A330 (Rev Dec 01/25) | …/2025-12/AC_A330_20251201.pdf — FIG-2-2-0-991-001/-002/-011/-012, FIG-2-3-0-991-001, FIG-2-7-0-991-006 |
| A350-900/-1000 | AC A350 (Rev Jul 15/25) | …/2025-07/AC_A350_20250715.pdf — FIG-2-2-0-991-001/-002, FIG-2-3-0-991-001, FIG-2-7-0-991-001 |
| A380 | AC A380 (Rev Dec 01/25) | …/2025-12/AC_A380_20251201.pdf — FIG-2-2-0-991-001, FIG-2-3-0-991-001, FIG-2-7-0-991-002 |
| A220-100 / -300 | A220-100 APP BD500-3AB48-22000-00 (2023-09-08); A220-300 APP BD500-3AB48-32000-00 (2022-05-12) — both marked "superseded by the ACP" | …/2023-11/A220-100APP-Issue032-00-19Oct2023.pdf, …/A220-300APP-Issue031-00-19Oct2023.pdf. The ACP itself (A220-ACP-Issue001) could not be downloaded (Incapsula block). |
| E175 | Embraer APM-2259 (Rev May 25/18), attached to NTSB docket DCA20IA014 | data.ntsb.gov/Docket/Document/docBLOB?ID=13691419 — §2.2.1–2.2.2 p.2-3, Fig 2.1/2.2 |
| E190 / E195 | Embraer APM-1901 (May 21/21) and APM-1997 (Oct 07/08) | web.archive.org copies of embraercommercialaviation.com/wp-content/uploads/2017/06/APM_190.pdf and /2017/02/APM_E195.pdf (the originals now return 404) |
| CRJ200 / 700 / 900 | Bombardier CSP A-020 Rev 8, CSP B-020 Rev 15, CSP C-020 Rev 11 | customer.aero.bombardier.com/…/CRJ200APMR8.pdf, CRJ700APMR15.pdf, CRJ900APMR11.pdf |
| ICAO designators | ICAO Doc 8643 dump (OpenSky mirror, s3.opensky-network.org/data-samples/metadata/doc8643AircraftTypes.csv) | no B3XM / E290 / E295 in that 2024 dump; E75L = "175 (long wing)", E75S = "175 (short wing)" |

**Conventions checked in the documents.**

- **Boeing door dimensions** run to the door **centre**. The 757 table says so explicitly ("longitudinal distance from nose to center of door"). The 737/767/777/787/747 figures draw the dimension to the door centre line.
- **Airbus AC door figures** dimension the door centre line.
- **Boeing "wheelbase"** is nose-gear axle → main-gear axle. For the 747 it is measured to the wing gear, and the body gear is 3.07 m further aft.
- **Airbus.** The nose → nose-gear distance is shown separately. The A330 main-gear dimension runs from the **nose tip** (32.05 m); the A350/A320 figures dimension the wheelbase from the nose gear. I checked each against the drawing scale.
- **Embraer plan views** (nose left, seen from above) put the right side at the top. So the lower door arrow (4.71 m) is door 1L.

## 4. Per-type result (from `check_dims.py`, rendered or used value minus reference)

Percentages are for sizes; metres are for positions. **Bold** means flagged (more than 1 %, or a position error more than 1 % of L).

- `L1 (shader)`: `TYPES.doors[0]`.
- `L1 dock`: `doors[0] + 0.5`.
- `L2`: `doors[1]`, used for the second bridge on wide-bodies.
- `crown`: rendered fuselage top above the ground.
- `model's own L1 mesh`: the door object in the source model, when it has one.

| ICAO | TYPES / model | L | span (render) | span (proc) | span (TYPES) | H | crown | nose gear x | main gear x | wheelbase | track | L1 (shader) | L1 dock | L2 | bridge floor | model's own L1 mesh |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A19N | a319 / a319 | +0.0% | **-5.4%** | — | +0.0% | — | — | +0.13 | +0.14 | — | +0.1% | **-0.94** | **-0.44** | — | — | +0.03 |
| A20N | a20n / a320 | +0.0% | **-7.0%** | — | +0.0% | -0.6% | -0.26 | +0.13 | +0.14 | — | +0.1% | **-0.94** | **-0.44** | — | **-0.40** | -0.05 |
| A21N | a21n / a321 | +0.0% | **-5.3%** | — | +0.0% | — | — | +0.13 | +0.13 | — | +0.1% | **-0.92** | -0.42 | — | — | +0.06 |
| A319 | a319 / a319 | +0.0% | -0.7% | — | **+5.0%** | **-1.1%** | — | +0.13 | +0.14 | — | +0.1% | **-0.94** | **-0.44** | — | — | +0.03 |
| A320 | a320 / a320 | +0.0% | **-2.4%** | — | **+5.0%** | — | — | +0.13 | +0.14 | — | +0.1% | **-0.94** | **-0.44** | — | — | -0.05 |
| A321 | a321 / a321 | +0.0% | -0.6% | — | **+5.0%** | — | — | +0.13 | +0.13 | — | +0.1% | **-0.92** | -0.42 | — | — | +0.06 |
| A332 | a332 / a333 | +0.0% | +0.4% | — | **+7.4%** | — | — | -0.37 | +0.45 | — | -0.7% | -0.05 | +0.45 | **+3.04** | — | — |
| A333 | a333 / a333 | -0.0% | +0.3% | — | **+7.4%** | +0.0% | **+0.93** | -0.37 | -0.35 | — | -0.7% | -0.05 | +0.45 | -0.14 | +0.15 | — |
| A339 | a333 / a333 | +0.0% | **-5.5%** | — | **+1.2%** | — | — | -0.37 | -0.35 | — | -0.7% | -0.05 | +0.45 | -0.14 | — | — |
| A359 | a359 / a359 | +0.0% | -0.3% | — | +0.0% | -0.5% | +0.22 | **+1.67** | **+1.71** | — | +0.0% | **-1.02** | -0.52 | **-1.26** | -0.49 | — |
| A35K | a35k / a359 | +0.0% | -0.3% | — | +0.0% | — | — | **+1.67** | **+1.69** | — | **-1.2%** | **-1.02** | -0.52 | **-5.70** | — | — |
| A388 | a388 / a388 | -0.0% | +0.1% | — | +0.0% | -0.1% | +0.23 | +0.43 | +0.22 | — | — | -0.72 | -0.22 | +0.70 | +0.13 | — |
| B38M | b38m / b738 | +0.1% | -0.4% | — | -0.1% | **+4.1%** | +0.07 | **+0.61** | **+0.61** | — | +0.0% | **-1.73** | **-1.23** | — | +0.00 | — |
| B39M | b39m / b738 | +0.1% | -0.5% | — | -0.1% | **+4.4%** | +0.07 | **+0.61** | **+0.54** | — | +0.0% | **-1.73** | **-1.23** | — | +0.00 | — |
| B3XM | b39m / b738 | **-3.7%** | -0.5% | — | -0.1% | **+4.0%** | +0.04 | **+0.61** | **-0.63** | — | +0.0% | **-1.73** | **-1.23** | — | +0.00 | — |
| B737 | b737 / b738 | +0.0% | -0.1% | — | +0.0% | **+2.2%** | +0.02 | **+0.61** | **+0.41** | — | +0.0% | **-1.73** | **-1.23** | — | +0.00 | — |
| B738 | b738 / b738 | +0.0% | -0.2% | — | +0.0% | **+2.6%** | +0.02 | **+0.61** | **+0.61** | — | +0.0% | **-1.73** | **-1.23** | — | +0.00 | — |
| B739 | b739 / b738 | +0.0% | -0.2% | — | +0.0% | **+2.6%** | +0.00 | **+0.61** | **+0.54** | — | +0.0% | **-1.73** | **-1.23** | — | +0.00 | — |
| B744 | b744 / b744 | -0.0% | **+1.1%** | — | **+6.1%** | +0.0% | — | **-0.95** | **-2.25** | — | +0.0% | **-3.20** | **-2.70** | **-2.00** | — | — |
| B748 | b748 / b748 | +0.0% | -0.4% | — | +0.0% | +0.0% | — | **-0.94** | **-2.20** | — | +0.1% | **-3.20** | **-2.70** | **-6.10** | — | — |
| B752 | b752 / b752 | +0.0% | **+2.9%** | — | +0.0% | +0.0% | — | **-1.29** | **-1.18** | — | +0.0% | **-1.45** | **-0.95** | — | — | — |
| B753 | b753 / b752 | -0.1% | **+2.6%** | — | -0.0% | +0.0% | — | **-1.29** | **-1.34** | — | +0.0% | **-1.45** | **-0.95** | — | — | — |
| B763 | b763 / b763 | +0.0% | **-3.1%** | — | **+7.0%** | +0.0% | — | **+0.55** | **+0.59** | — | +0.0% | **-1.40** | **-0.90** | **-1.76** | — | — |
| B764 | b764 / b763 | +0.0% | **-11.2%** | — | **-2.0%** | +0.0% | — | +0.54 | +0.54 | — | +0.0% | **-1.40** | **-0.90** | **-5.14** | — | — |
| B772 | b772 / procedural | +0.0% | — | **+6.4%** | — | — | — | **+1.11** | **+1.13** | — | +0.3% | **-1.15** | **-0.65** | **+0.73** | — | — |
| B779 | b77w / procedural | **-3.7%** | — | -0.1% | — | — | — | **+1.11** | -0.02 | — | — | — | — | — | — | — |
| B77L | b772 / procedural | +0.0% | — | +0.0% | — | — | — | **+1.11** | **+1.12** | — | +0.3% | **-1.14** | **-0.64** | **+0.73** | — | — |
| B77W | b77w / procedural | +0.0% | — | +0.0% | — | — | — | **+1.11** | **+1.09** | — | +0.3% | **-1.14** | -0.64 | +0.73 | — | — |
| B788 | b788 / b788 | +0.0% | -0.8% | — | -0.0% | +0.0% | — | **+1.89** | **+1.76** | — | +0.0% | **-1.10** | **-0.60** | **+2.28** | — | — |
| B789 | b789 / b788 | +0.0% | -0.8% | — | -0.0% | +0.0% | — | **+1.89** | **+1.76** | — | +0.0% | **-1.10** | -0.60 | **-0.76** | — | — |
| B78X | b78x / b788 | -0.0% | -0.8% | — | -0.0% | +0.0% | — | **+1.89** | **+1.76** | — | +0.0% | **-1.10** | -0.60 | **-3.81** | — | — |
| BCS1 | bcs1 / bcs1 | +0.3% | **-1.5%** | — | +0.0% | — | — | — | — | — | +0.0% | — | — | — | — | — |
| BCS3 | bcs3 / bcs3 | +0.0% | **+1.9%** | — | +0.3% | **-2.0%** | — | **+1.01** | **+1.00** | — | -0.4% | — | — | — | — | — |
| CRJ2 | crj2 / crj2 | +0.0% | -0.3% | — | **+17.1%** | +0.0% | -0.04 | — | — | **+1.50** | **+27.4%** (inf ref) | **-1.92** (inf ref) | **-1.42** | — | +0.05 | — |
| CRJ7 | crj7 / crj7 | -0.1% | -0.3% | — | **+6.9%** | +0.8% | — | — | — | +0.19 | **-2.9%** | **-1.88** | **-1.38** | — | **+1.15** | +0.04 |
| CRJ9 | crj9 / crj9 | -0.1% | **-4.2%** (vs 24.85 m; +2.4 % vs early-build 23.24 m) | — | +0.0% | **+2.1%** | — | — | — | +0.00 | **-1.7%** | **-1.88** | **-1.38** | — | **+1.08** | +0.04 |
| E190 | e190 / e190 | +0.0% | -0.7% | — | -0.2% | -0.0% | — | **-0.73** | **+2.64** | — | +0.0% | **-2.24** (inf ref) | **-1.74** | — | — | +0.34 (inf ref) |
| E195 | e190 / e190 | **-6.2%** | -0.7% | — | -0.2% | -0.0% | — | — | — | — | +0.0% | **-2.24** | **-1.74** | — | — | +0.34 |
| E75L | e75l / e75l | +0.0% | **-8.3%** | — | +0.0% | +0.0% | — | **-0.73** | **+2.67** | — | **+14.2%** | **-2.24** (inf ref) | **-1.74** | — | — | — |
| E75S | e75l / e75l | +0.0% | **+1.1%** | — | **+10.2%** | +0.0% | — | **-0.73** | **+2.67** | — | **+14.2%** | **-2.24** | **-1.74** | — | — | — |

Notes on the table:

- **B77L span.** The 777-200LR's 64.80 m is right. For the B772 (777-200/-200ER) the procedural span of 64.8 m is +6.4 %.
- **B779.** The reference span is the ground (folded) span of 64.85 m. Extended, the 777-9 spans 71.76 m.
- **B744.** The ACAP gives 64.44 m (jig) and 64.92 m (at MGW). The model is +1.1 % against the jig value and +0.4 % against the MGW value.
- **CRJ9.** Airframes 15001–15035 have a 23.24 m span; 15036 and later have 24.85 m (CSP C-020 00-02-02 p.1 and p.8). US CRJ900s are late-build.
- **The `H` column** compares with the ACAP's vertical-tail height range. For the gear-less models it reproduces the app's `HEIGHT` table. The `HEIGHT` values are within range, except:

  | Type | HEIGHT | ACAP |
  |---|---|---|
  | A319 | 11.76 m | 11.89–12.05 m |
  | A220-300 | 11.5 m | 11.73 m |
  | CRJ900 | 7.51 m | 7.35 m |

  The CRJ700/900 values look swapped: `HEIGHT.crj7 = 7.57` against an APM value of 7.51 m, and `crj9 = 7.51` against 7.35 m.

- **The door references for the E-Jets and the CRJ200 are inf.** The E-Jet centre is 4.71 m (door 1L forward edge, APM Fig 2.x plan view) plus half of the 0.85 m door (Fig 2.3). The CRJ200 door is scaled off Fig 2. The CRJ700/900 door centre is 4.22 m ("Passenger Door (FWD side) to Radome", 00-02-04 Table 1) plus half of 0.91 m.

## 5. The models' own geometry (source-mesh pass)

Door and gear-door objects found in the FAM sources. Positions are in rendered metres from the nose. Of the ACAP values, only the CRJ700/900 door is inferred (edge + half width); the other values are read directly.

| Model | Passenger door meshes (centre) | ACAP | Gear-door meshes | ACAP gear |
|---|---|---|---|---|
| a319 | DoorL1 5.07, overwing 13.66, aft 25.87 | 5.04 / 12.83–13.68 / 25.81 | nose-gear doors 3.9–5.4, main 15.86 | nose 5.07, main 16.11 |
| a320 | DoorL1 4.99, overwing 14.17 / 15.00, aft 29.09 | 5.04 / 14.43 / 15.28 / 29.53 | nose 3.9–5.3, main 17.16 | nose 5.07, main 17.71 |
| a321 | DoorL1 5.08, L2 13.99, L3 25.02, L4 36.57 | 5.02 / 13.84 / 24.79 / 36.58 | main 21.75 | main 21.97 |
| bcs1 | doorFL 4.96, doorRL 26.34 | not dimensioned in the APP (ACP not obtained) | main 16.2–16.3 | — |
| crj7 / crj9 | LeftDoor 4.71 (forward edge 4.28) | 4.68 (forward edge 4.22) | main 17.16 / 19.46 | wheelbase 15.01 / 17.30 |
| e170 / e190 | door.l1 5.41 / 5.48 (forward edge 4.9) | forward edge 4.71 | — | — |
| a333, a359, a388, b744, b748, b788 | no passenger-door objects (doors are only painted) | | nose / main gear doors at the ACAP stations ± 0.5 m (e.g. b788 lh/rh main-gear doors 26.6–27.8 m against main gear 28.19 m) | |

So the source models are good references in their own right. The error is in `TYPES`, not in the meshes.

## 6. ICAO type → model mapping (`TYPE_MODELS`, `js/live/aircraft.js`)

| ICAO | Maps to (TYPES / model) | Verdict |
|---|---|---|
| B736 → b737 / b738 | 737-600 is shorter than the -700 airframe it uses | Wrong length (737-600 not extracted; rare at SFO) |
| B737, B738, B739 | b737/b738/b739 / b738 (FlightGear 737-800 with gear) | OK in size. Gear, doors and height need correcting (§1) |
| B37M, B38M, B39M | b38m / b39m / b738 | OK in size |
| B3XM (737-10) | b39m | **Mis-mapped**: 42.16 m against 43.79 m. Needs its own derive: +1.67 m, of which the wheelbase grows +1.17 m (fwd plug) |
| A318 | a319 | A318 is shorter (not extracted; not seen at SFO) |
| A319, A320, A321 | a319/a320/a321 (FAM, wing-tip fences) | OK for ceo with fences. US ceo fleets fly both fences and sharklets: that is per airframe and **unverified** |
| A19N, A20N, A21N | same models | **Span −5 to −7 %**: sharklets missing. Needs a sharklet variant or a wingtip swap |
| A332 → a332 / a333 | length OK after the stretch | Door 2 is 3.0 m off (the shrink is ahead of door 2) |
| A333 | a333 | OK. Seated 0.9 m high (fin too short) |
| A338, A339 | a332/a333 | **Span −5.5 %** (neo wing 64.00 m); tips missing |
| A359 | a359 | OK |
| A35K | a35k / a359 stretched | Length OK. Door 2 is −5.7 m off. The 6-wheel bogie is only procedural |
| A388 | a388 | OK |
| B752, B753 | b752 (+ plug) | Span +2.6–2.9 %. Door and gear offsets |
| B762, B763, B764 | b763 (+ plug) | B764 span **−11 %** (the 767-400 has raked tips). B763 −3.1 % |
| B772, B77L, B773, B77W, B778, B779 | procedural b772/b77w (no model) | B772 span +6.4 %. B779 **−3.7 % length**. B778 unverified. "B773" in SFO landings data is SFO's own code (§ liveries.md) |
| B788, B789, B78X | b788 (+ plug) | Sizes OK. Door 2 wrong on -8 and -10. Nose and main gear +1.8 m |
| B744, B74F, B748 | b744/b748 | B74F is not in Doc 8643 (harmless). Gear −2.2 m, L1 −3.2 m |
| BCS1, BCS3 | bcs1/bcs3 | OK within 2 %. Gear +1.0 m (A220-300) |
| E170 | e170 | No APM obtained (APM_170.pdf is 404 and not archived) |
| E75L | e75l (short-wing model) | **Span −8.3 %** against the long wing |
| E75S | e75l | OK |
| E190 | e190 | OK in size. Gear +2.6 m |
| E195 | e190 | **Length −6.2 %** |
| E290, E295 (E2) | e190 | Mis-mapped (E2 wing and gear). The E2 APM (techcare.embraer.com APM_E-JetsE2.PDF) could not be downloaded (502) — **unverified** |
| CRJ2 | crj2 | Model OK. `TYPES` span/wheelbase/track taken from the CRJ900 are wrong |
| CRJ7 (includes CRJ550 CL-600-2C11, which ADS-B databases also code as CRJ7) | crj7 | Model OK. `TYPES` span +6.9 % |
| CRJ9, CRJX | crj9 | CRJ9 OK. CRJX (CRJ1000, CSP D-020 not extracted) is longer |
| MD11 | md11 | Not checked (no ACAP values transcribed). Not in the SFO landings of Aug 2025 – Jul 2026 |

## 7. Stretch rule (`stretchFor` / `derive()`) against the ACAP

| Pair | Forward plug (ACAP) | Where it is (ACAP) | App |
|---|---|---|---|
| 737-8 → 737-9 | wheelbase +1.57 m | between door 1 and the wing | d1 1.5 ✓, cut ahead of the wing ✓ |
| 737-800 → 737-700 | −3.00 m | same | d1 −3.2 (0.2 m) |
| 757-200 → -300 | +4.06 m | aft of door 2 (door 2 unchanged at 13.99 m) | 3.9 ✓ |
| 787-8 → -9 → -10 | +3.05 m, +3.05 m | **ahead of door 2** (door 2 moves 15.32 → 18.36 → 21.41 m) | cut at the wing LE − 1 m ✗; `doors[1]` kept at 17.6 m ✗ |
| 747-400 → -8 | +4.06 m | ahead of door 2 (18.80 → 22.9 m) | ✗ |
| 767-300 → -400 | +3.44 m | ahead of door 2 (15.96 → 19.34 m) | ✗ |
| A330-300 → -200 | −3.20 m | ahead of door 2 (17.74 → 14.56 m) | ✗ |
| A350-900 → -1000 | wheelbase +3.82 m, door 2 +4.44 m | ahead of door 2 | ✗ |

The fix: make the plug station a per-pair parameter taken from these door deltas. For the six pairs marked ✗, the plug goes between door 1 and door 2. For the painted texture that is still an approximation, because the window pattern gets stretched.

## 8. Proposed reference values for `TYPES` (for whoever edits `js/aircraft/types.js`)

All values are metres from the nose tip, door **centres**.

- Where a main-gear value is given as "nose+", it is the wheelbase added to a nose-gear position that is not dimensioned.
- For the A319 and A320 the door list is [1L, 4L]. Their overwing exits are A319 12.83 / 13.68 and A320 14.43 / 15.28.
- For the A321 the list is 1L, 2L, 3L, 4L on the four-door cabin. The A321neo ACF/XLR is 1L 5.04, overwing 18.70 / 19.54, 3L 26.82, 4L 36.47.

| ICAO → TYPES | L | span | fin height (min–max) | nose-gear x | main-gear x | track | door centres from nose (1, 2, …) | L1 sill | source |
|---|---|---|---|---|---|---|---|---|---|
| B737 → b737 | 33.63 | 35.79 | 12.45–12.67 | 4.09 | 16.69 | 5.72 | 5.03 | 2.59–2.74 | Boeing D6-58325-7 Rev C |
| B738 → b738 | 39.47 | 35.79 | 12.37–12.62 | 4.09 | 19.69 | 5.72 | 5.03 | 2.59–2.74 | Boeing D6-58325-7 Rev C |
| B739 → b739 | 42.11 | 35.79 | 12.37–12.62 | 4.09 | 21.26 | 5.72 | 5.03 | 2.59–2.74 | Boeing D6-58325-7 Rev C |
| B38M → b38m | 39.47 | 35.92 | 11.86–12.45 | 4.09 | 19.69 | 5.72 | 5.03, aft 31.88 | 2.77–3.07 | Boeing D6-38A004 Rev K |
| B39M → b39m | 42.11 | 35.92 | 11.89–12.40 | 4.09 | 21.26 | 5.72 | 5.03, aft 34.52 | 2.79–3.07 | Boeing D6-38A004 Rev K |
| B3XM → (new) | 43.79 | 35.92 | 11.91–12.45 | 4.09 | 22.43 | 5.72 | 5.03, aft 36.20 | 2.77–3.07 | Boeing D6-38A004 Rev K |
| B752 → b752 | 47.32 | 38.05 | 13.49–13.74 | 5.89 | 24.18 | 7.32 | 5.05, 13.99, 38.23 | — | Boeing D6-58327 Rev H |
| B753 → b753 | 54.43 | 38.06 | 13.56–13.64 | 5.89 | 28.24 | 7.32 | 5.05, 13.99, 35.99, 45.34 | — | Boeing D6-58327 Rev H |
| B763 → b763 | 54.94 | 47.57 | 15.39–16.03 | 4.55 | 27.31 | 9.30 | 5.70, 15.96 (optional mid door), 42.55 | — | Boeing D6-58328 Rev K |
| B764 → b764 | 61.37 | 51.92 | 16.68–17.01 | 4.56 | 30.76 | 9.30 | 5.70, 19.34, 48.95 | — | Boeing D6-58328 Rev K |
| B772 → b772 | 63.73 | 60.93 | 18.42–18.76 | 5.89 | 31.77 | 10.97 | 6.75, 17.07, 36.33, 49.54 | — | Boeing D6-58329 Rev E |
| B77L → (b772 with 64.80 span) | 63.73 | 64.80 | 18.48–18.75 | 5.89 | 31.78 | 10.97 | 6.74, 17.07, 36.32, 49.53 | — | Boeing D6-58329-2 Rev G |
| B77W → b77w | 73.86 | 64.80 | 18.24–18.85 | 5.89 | 37.11 | 10.97 | 6.74, 17.07, 32.92, 46.46, 59.67 | — | Boeing D6-58329-2 Rev G |
| B779 → (new) | 76.73 | 64.85 folded / 71.76 | 19.28–19.74 | 5.89 | 38.22 (inf) | — | — | — | Boeing D6-86073 Rev G |
| B788 → b788 | 56.72 | 60.12 | 16.59–17.09 | 5.41 | 28.19 | 9.80 | 6.30, 15.32, 32.39, 43.56 | — | Boeing D6-58333 Rev Q |
| B789 → b789 | 62.81 | 60.12 | 16.81–17.09 | 5.41 | 31.24 | 9.80 | 6.30, 18.36, 35.43, 49.66 | — | Boeing D6-58333 Rev Q |
| B78X → b78x | 68.30 | 60.12 | 16.89–17.02 | 5.41 | 34.29 | 9.80 | 6.30, 21.41, 38.48, 55.14 | — | Boeing D6-58333 Rev Q |
| B744 → b744 | 70.67 | 64.44 | 18.80–19.51 | 7.75 | 33.35 (wing gear; body +3.07) | 11.00 | 9.50, 18.80, 30.61, 40.74, 55.14 | — | Boeing D6-58326-1 Rev F |
| B748 → b748 | 76.25 | 68.40 | 18.97–19.51 | 7.74 | 37.40 (wing gear; body +3.07) | 10.99 | 9.50, 22.90, 34.70, 46.30, 60.80 | — | Boeing D6-58326-3 Rev E |
| A319 → a319 | 33.84 | 34.10 (fence) / 35.80 (sharklet) | 11.89–12.05 (inf) | 5.07 | 16.11 | 7.59 | 5.04, aft 25.81 | — | Airbus AC A319 |
| A20N/A320 → a20n/a320 | 37.57 | 35.80 / 34.10 | 11.83–12.08 | 5.07 | 17.71 | 7.59 | 5.04, aft 29.53 | 3.38–3.48 | Airbus AC A320 |
| A21N/A321 → a21n/a321 | 44.51 | 35.80 / 34.10 | — | 5.07 | 21.97 | 7.59 | 5.02, 13.84, 24.79, 36.58 | — | Airbus AC A321 |
| A332 → a332 | 58.82 | 60.30 | — | 6.67 | 28.85 | 10.68 | 5.85, 14.56, 32.77, 45.63 | — | Airbus AC A330 |
| A333 → a333 | 63.67 | 60.30 | 16.72–17.18 | 6.67 | 32.05 | 10.68 | 5.85, 17.74, 35.96, 50.96 | 4.41–4.55 | Airbus AC A330 |
| A339 → (new) | 63.66 | 64.00 | — | 6.67 | 32.05 | 10.68 | 5.85, 17.74, 35.96, 50.96 | — | Airbus AC A330 |
| A359 → a359 | 66.80 | 64.75 | 17.14–17.47 | 4.63 | 33.29 | 10.60 | 6.82, 18.86, 37.93, 52.55 | 5.04–5.36 | Airbus AC A350 |
| A35K → a35k | 73.79 | 64.75 | — | 4.63 | 37.11 (inf) | 10.73 | 6.82, 23.30, 42.38, 59.53 | — | Airbus AC A350 |
| A388 → a388 | 72.73 | 79.75 | 24.12–24.27 | 4.97 | 33.58 (WLG), 36.85 (BLG) | — | M1 6.32, M2 16.50 (U1 20.94) | 5.10–5.36 (U1 7.87–8.08) | Airbus AC A380 |
| BCS1 → bcs1 | 34.90 | 35.10 | — | — | — | 6.70 | — | — | Airbus A220-100 APP (labels lost; inf) |
| BCS3 → bcs3 | 38.69 | 34.98 | 11.73 | 3.39 | 18.70 | 6.73 | — | — | Airbus A220-300 APP Table 5 |
| E75L → e75l | 31.68 | 28.65 | 9.86 | 4.13 | 15.53 | 5.20 | ≈5.14 (inf) | — | Embraer APM-2259 |
| E75S → e75l | 31.68 | 26.00 | 9.86 | 4.13 | 15.53 | 5.20 | ≈5.14 (inf) | — | Embraer APM-2259 |
| E190 → e190 | 36.24 | 28.72 | 10.57 | 4.13 | 17.96 | 5.94 | ≈5.14 (inf) | — | Embraer APM-1901 |
| E195 → (new) | 38.65 | 28.72 | 10.57 (inf) | — | — | 5.94 | ≈5.14 (inf) | — | Embraer APM-1997 |
| CRJ2 → crj2 | 26.77 | 21.23 | 6.18–6.32 | — | nose+11.40 | ≈3.14 (inf) | ≈4.72 (inf) | 1.50–1.73 | Bombardier CSP A-020 Rev 8 |
| CRJ7 → crj7 | 32.34 | 23.25 | 7.51 | — | nose+15.01 | 4.12 | 4.68 (inf) | 1.73 | Bombardier CSP B-020 Rev 15 |
| CRJ9 → crj9 | 36.24 | 24.85 | 7.35 | — | nose+17.30 | 4.07 | 4.68 (inf) | 1.73 | Bombardier CSP C-020 Rev 11 |

The machine-readable version of this table is `REF` in `tools/models/check_dims.py`, with the page or figure of every value.

## 9. Recommendations

1. **Doors.**
   - Replace `TYPES.doors` with ACAP door centres. Keep door 1 and door 2 explicit (for example `doorL1`, `doorL2`), because the arrays currently mix in overwing exits.
   - Remove the `+ 0.5` in `gates.js doorOf`, or define every door value as the forward edge in both places.
   - Where the source model has a door mesh (A320 family, E-Jets, A220-100, CRJ700/900), measure the door from the model itself at conversion time and store it in the `.sfom` header. This guarantees that the bridge meets the painted door.
2. **Bridge cab height.**
   - Use the ACAP sill heights (table above) instead of `Hc − 0.3 R`.
   - For gear-less models, seat on the ACAP fuselage-top or sill height rather than on the fin height (`HEIGHT`). This fixes the A330 and CRJ floating.
3. **Gear.** Take the nose-gear x, main-gear x and track from §8. For the 747 and A380, add the body-gear offset.
4. **Spans in `TYPES`.** Correct the derived airframes (crj2, crj7, a332, a333, b763, b744, b772). Ground physics collides with these planforms.
5. **Mapping.**
   - Add B3XM (43.79 m), E195 (38.65 m) and B779 (76.73 m).
   - Keep the E75L/E75S distinction by span. Needs a long-wing E175 model or a procedural tip extension.
   - Neo variants (A19N/A20N/A21N/A338/A339) need sharklets or neo tips.
   - B764 needs raked tips.
6. **Stretch.** Take per-pair plug stations from §7. `derive()` must move door 2 when the plug is ahead of it.
7. **Pipeline guard.** Run `tools/models/check_dims.py` in CI or before every model conversion. It exits normally but prints the flag count.

## 10. Not verified / open

- E170 and E175-E2 / E190-E2 / E195-E2 dimensions: no primary document could be downloaded.
- The A220 ACP (the successor of the APP) is not downloaded. A220 door stations are not dimensioned in the APP.
- MD-11 and 737-600: not transcribed.
- **E175 long-wing / short-wing per airframe.**
  - The ADS-B databases code every US E175 as E75L. For example, `wiedehopf/tar1090-db` codes N125SY (FAA model "ERJ 170-200 LR") as E75L "(long wing)".
  - The FAA registry distinguishes "ERJ 170-200 LR" from "ERJ 170-200 LL". "LL" is probably the enhanced (long) wingtip, but I did not find a primary definition of the suffix; the UK CAA TCDS link returned 404.
  - Until this is settled, the 26.00 m and 28.65 m spans cannot be assigned per airframe.
  - [corrected by verifier] Settled (inf):
    - "LL" is the 70-passenger model, not the wingtip. ANAC TCDS EA-2003T05-24: "ERJ 170-200 LL, approved on 05 February 2018"; "70 Passengers (170-200 LL)".
    - The long wing is "extended wingtip or Post-Mod SB 0170-57-0058" (APM-2259 §2.2.2). The TCDS applies the later certification basis to S/N 17000376–378, 17000381–388, 17000390 and 17000392 onward, or post-mod SB 170-57-0058.
    - By FAA MASTER serials, all SkyWest (265) and Horizon (49) E175s in BTS 2026-05..07 are in that range. The exceptions are the 6 Delta-owned N603–614CZ (S/N 17000181–198), which are short-wing unless retrofitted.
    - So E75L → 28.65 m is right for almost all SFO E175s.
- **CRJ fuselage-top reference.** The CRJ700 Fig 1 value of 4.18 m is ambiguous, so I did not use it.
- **ACAP letter codes.** Several ground-clearance tables use letter codes whose figure I did not view. The vertical-tail rows (757 K, 767 J, 777 K, 787 N, 747 K) were identified by magnitude; each is consistent with the published overall height.

## Verification (adversarial check)

Independent re-check, 24 Sep 2026.
- `tools/models/check_dims.py` was re-run, and reference values were re-read from the cached manufacturer PDFs (PyMuPDF text extraction, or a rendered figure where the dimensions are drawn).
- Inline fixes are marked **[corrected by verifier]**.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | `check_dims.py` flags 182 items | confirmed | Re-run prints "182 flagged items" (2.7 s). |
| 2 | Bridge docks at `doors[x] + 0.5` and the shader treats `doors[x]` as the door centre | confirmed | `js/live/gates.js` `doorOf`: `v3.mul(f, x + 0.5)`. `js/shaders/aircraft.js`: `box(vec2(dx, …), …, vec2(0.5, 0.95), …)` with `dx = xn - uDoors[i]`. |
| 3 | L1 is 0.9–3.2 m too far forward "on all types"; bridges wrong "on every type" | **refuted (overgeneralised)** | Re-run JSON: A330 family `doors[0]` 5.80 against 5.85 (−0.05 m), dock +0.45 m. A380 −0.72 / dock −0.22. It is true for the 737, 757, 767, 777, 787, 747, E-Jets and CRJs, and −0.92 to −1.02 m for the A320 family and A350. |
| 4 | 737 MAX L1 5.03 m (D6-38A004 Rev K §2.7.1 p.2-26) | confirmed | PDF p.42 (printed 2-26): "FWD MAIN ENTRY DOOR NO. 1 LEFT 16-6 (5.03)" for every MAX model. |
| 5 | 757 L1 5.05 m; note "longitudinal distance from nose to center of door" | confirmed | D6-58327 Rev H PDF p.31: "NO. 1 PASSENGER DOOR (LH) 16 FT 7 IN (5.05 M)"; note 1 verbatim. |
| 6 | 787 L1 6.30; door 2 15.32 / 18.36 / 21.41 | confirmed | D6-58333 Rev Q PDF p.32 door table. |
| 7 | 747-8 doors 9.5 / 22.9 / 34.7 / 46.3 / 60.8 | confirmed | D6-58326-3 Rev E p.2-14 figure (rendered): 31 ft 2 in (9.5 m), 75 ft 0 in (22.9 m), 113 ft 9 in (34.7 m), 152 ft 0 in (46.3 m), 199 ft 4 in (60.8 m). |
| 8 | 767-300 span 47.57, L 54.94, nose gear 4.55, main 27.31, track 9.30 | confirmed | D6-58328 Rev K p.2-9 figure: 156 ft 1 in (47.57 m), 180 ft 3 in (54.94 m), 14 ft 11 in (4.55 m), wheelbase 74 ft 8 in (22.76 m), 30 ft 6 in (9.3 m). |
| 9 | A330-300 span 60.30, L 63.67, nose gear 6.67, main 32.05, track 10.68; A330-900 span 64.00; A330-200 L 58.82, main 28.85 | confirmed | AC A330 Dec 01/25, FIGURE-2-2-0-991-001 (60.3 m, 63.67 m, 32.05 m, 6.67 m, 10.68 m) and the A330-900 / -200 / -800 sheets. |
| 10 | A320 span 34.10 (fence) / 35.80 (sharklet) | confirmed | AC A320 FIGURE-2-2-0-991-004 (34.10 m) and the A320neo sheet (35.80 m). |
| 11 | E175: span 26.00 (winglet, pre-SB 0170-57-0058) and 28.65 (extended tip), L 31.68, H 9.86, nose gear 4.13, wheelbase 11.40, track 5.20 | confirmed | APM-2259 §2.2.1/2.2.2 p.30 verbatim; Fig 2.1/2.2 and footprint p.111. |
| 12 | E190: span 28.72, L 36.24, wheelbase 13.83, track 5.94 | confirmed | APM-1901 §2.2.1 p.28; Fig p.30; footprint p.114. |
| 13 | E195 L 38.65 | confirmed (minor note) | APM-1997 §2.2.3 "Fuselage Total Length 38.65 m". §2.2.1 gives the overall length as 38.67 m, a 0.05 % difference that changes no flag. |
| 14 | CRJ200 span 21.23, L 26.77, wheelbase 11.4 | confirmed | CSP A-020 00-02-01 Fig 2 p.5 (rendered). The track of 3.14 m is 2 × 1.57 m; it is marked inf and plausible. |
| 15 | CRJ700 span 23.25, H 7.51, sill 1.73, "Passenger Door (FWD Side) to Radome" 4.22 | confirmed | CSP B-020 Table 1 p.29 and 00-02-04 Table 1 p.72, verbatim. |
| 16 | CRJ900 span 23.24 (15001–15035) / 24.85 (15036+), H 7.35 | confirmed | CSP C-020 Table 1, PDF p.29 / p.36; MRW table "A/C 15036 − 15990". |
| 17 | 777-9 L 76.73, span 71.76 extended / 64.85 folded | confirmed | D6-86073 Rev G Fig 2-1 text. |
| 18 | Other Boeing values (737NG, 747-400, 777, 757 spans; 737-10 43.79) | unverifiable here | Drawn as vector figures; not re-rendered. They match publicly known Boeing figures. |
| 19 | Doc 8643 dump lacks B3XM, E290, E295; B74F not a designator; E75L/E75S "(long/short wing)" | confirmed | `doc8643AircraftTypes.csv` (Last-Modified 4 Nov 2024, 10,021 lines). B3XM, E290 and E295 are real, newer ICAO designators that are missing from this older dump. |
| 20 | A220 licence resolved (FGMEMBERS/CSeries @8a8223f3, GPL-2.0) | confirmed, strengthened | See liveries.md verification #44. BCS1 `cs100.png` = FG `Models/bombardier.png` (mad 0.0008). |
| 21 | "All the other sources are GPL-2.0 or GPL v2 or later" | **refuted for A380 textures** | A380-omega `License/README`: textures CC-BY-NC 3.0 until 31 May 2015. The relicensing covers only Muraleedharan's consent. |
| 22 | CRJ7 includes CRJ550 = CL-600-2C11 | confirmed | Federal Register 2023-00130: "Model CL-600-2C11 (Regional Jet Series 550)". |
| 23 | E175 "LL" is probably the enhanced wingtip | **refuted** | ANAC TCDS EA-2003T05-24: LL = 70-passenger model. The long wing depends on S/N or SB 170-57-0058 (inf). All SkyWest and Horizon E175s in BTS 2026-05..07 are in the long-wing S/N range, except N603–614CZ (S/N 17000181–198). |
| 24 | E175 TYPES: nose gear 3.4, main 18.2 (wheelbase 14.8), track 5.94, doors [2.9, …] | confirmed | `js/aircraft/types.js` `e75l`: `gear.main x 18.2 z 2.97`, `nose x 3.4`, `doors: [2.9, 27.9]`. |

**Net effect.**
- The main conclusions stand: bridge stations are wrong on most types, `TYPES` gear, spans and door-2 stretches are wrong, and B3XM, E195, B779 and B764 are mis-mapped.
- Bridge docking on the A330 family is already within 0.5 m. The A380 texture licence needs owner attention.
- The long-wing E175 geometry is the right default for SFO traffic.
