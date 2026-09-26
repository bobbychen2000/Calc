# Stand and jet-bridge rebuild from licence-clean sources (24 Sep 2026)

What `data/sfo_stands.json` / `.js` now contain, where every number comes from, how it was verified, and the fields the
realtime workflow can use. Generator: `tools/stands/build_stands.py` (also run by `tools/sat/export_stands.py`).
Checks: `tools/stands/check_stands.py` (also `tools/sat/check.py`, `tools/sat/check_bridges.py`). Generated tables below
are refreshed by `tools/stands/report.py`.

**Observed** = read in a source file or measured on imagery / recorded data; **inferred** = my interpretation, marked.

## 1. Result in brief

<!--BEGIN:summary-->
| quantity | value |
|---|---|
| contact stands | 108 (104 stands + 4 alternative positions: B5S, B11S, B16S, C9V) |
| position source (pos_src) | osm 102, osm+paint 2, naip 1, osm+adsb 1, osm+naip_axis+adsb 1, osm+naip+adsb 1 |
| name source (name_src) | sfo 108 |
| verified_by | adsb 52, OSM only 24, paint+adsb 14, paint 7, naip+adsb 7, naip 4 |
| src (legacy field) | obs 71, inf 37 |
| classes | B 6, C 60, CL 9, D 2, E 7, EL 21, F 3 |
| jet bridges | 131 OSM bridges: 128 main-deck bridges on 103 stands (1: 78, 2: 25), 3 upper-deck (`bridges_upper`: A6, A11, G13); no bridge of its own: B5S (uses B5), B16S (uses B16), C9V (uses C9), F10, F18 |
| mutually exclusive pairs | 8 |
| remote stands (SFO names, ADS-B) | 2: 2-2A, 41-22 |
| unnamed OSM parking positions (`positions`) | north 95, apron 50, contact-unused 27, west 7 |
| red boxes (NAIP) | 255 |
| painted lead-in vs model axis (NAIP yellow-line fit, 3-22 m behind the nose, clean fits), 22 stands | lateral at the nose: median |r| 0.28 m, max 4.70 m; heading: median |dh| 0.38 deg, max 17.74 deg; corrected: C4 (-1.1 m, -0.3 deg), D14 (+3.2 m, +0.6 deg) |
| NAIP parked aircraft, relief-corrected (lean k = 0.54 +- 0.04 m/m, residual 0.70 m rms; `naip_relief.py`): along = by-eye nose reading (+-1.5 m) corrected at nose height, 44 stands; lateral = measured fuselage centre, 26 stands | lateral: median |r| 0.3 m, max |r| 1.8 m; along: median 0.1 m, median |r| 1.1 m |
| ADS-B residual (antenna median in the stand frame), 83 stands / 254 aircraft | lateral: median |r| 0.4 m, max |r| 8.5 m; along (antenna behind the nose): median -10.4 m, range -27.2..0.4 m; heading: median |dh| 0.6 deg |
<!--END:summary-->

- The Google-screenshot survey (`tools/sat/stand_defs.py`, 89 stands) is no longer used for any committed coordinate. It
  stays in the repository as provenance; `tools/sat/export_stands_google_legacy.py` writes it to `tools/sat/work/` only.
- Every stand carries SFO's own name (AODB stand name from flysfo, or the official gate number); positions come from
  OpenStreetMap lead-in lines, calibrated along the axis and verified on NAIP 2024 and against ADS-B positions of
  aircraft that SFO's stand plan put on that stand.
- `check_stands.py` (rewritten in review rounds 1-3, §11-§13): aircraft are the app's own planforms, engine nacelles and
  door tables (`js/aircraft/types.js`, all 48 designators it knows; 757 / 767-300ER with the Boeing winglet spans), the
  envelope of every type a stand accepts, each at its per-family stop point; bridges are buffered footprints in docked
  and rest poses, each bridge with the range of ONE datasheet model (Oshkosh AeroTech sell sheet); floodlight masts
  against aircraft, bridges and buildings. Result (25 Sep 2026): **7 DATA ISSUES**, all evidence conflicts listed in §13
  (F5 L1 7.1-7.5 m, shorter than any apron-drive bridge; A1 / A2 L2 42.4-43.7 m for the 787-10; G7 L1 36.3 m for the A319
  that one ADS-B stay put 27.5 m short; A10 L1 0.9 m2 graze of the building outline) and **33 APP ISSUES** that come from
  how `js/live/traffic.js` uses the data today (oversize clause, one stop point per stand, stop-short parking;
  `docs/requests/static_geometry_round3.md`). Pairs below the ICAO stand clearance are listed in §5.
- **The rendered bridges are NOT the data bridges** (review rounds 2-4, critical, escalated): `js/live/gates.js`
  derives its own rotundas, walkways and rest poses and ignores `rotundaW` / `walkW` / `stowW`; round 4 measured 116 of
  128 rendered rotundas > 1.5 m (43 > 10 m) from the data and the imaged drums, with bridge-bridge, bridge-mast and
  bridge-aircraft collisions that exist only in the app. Everything checked in this file is the DATA geometry; nothing
  here verifies what the owner sees until `docs/requests/static_geometry_round4.md` §1 is implemented. The data bridges
  are OSM-traced roofs (lean included, likely ~1.3-2.1 m east of true) and **not verified on NAIP** (`geom_src`,
  `bridge_geom_note`).
  Review round 3 measured it: data walkways vs the imaged walkway band median |residual| 1.16 m (app: 2.75 m), rest poses
  on the imaged parked tunnels at the D, E and G piers (§13).

## 2. Sources and roles

| Role | Source | Licence / terms | How used |
|---|---|---|---|
| Position, heading | OSM `aeroway=parking_position` ways (Overpass download 24 Sep 2026, `refs/cache/osm/`) | ODbL 1.0 | stop = last node of the oriented way, heading = last segment. 66 of 287 ways are drawn backwards; `tools/stands/osm_src.py` orients each way by two independent cues (the end on an OSM taxiway/taxilane is the start; the end within 60 m of and > 5 m closer to the terminal outline is the stop). The cues never conflict; 21 unreferenced ways with neither cue are not used for contact stands. |
| Bridges | OSM `aeroway=jet_bridge` ways (133) | ODbL 1.0 | building attach point, fixed walkway, rotunda (start of the final segment), parked cab; assignment to stands §4 |
| Names | flysfo.com flight-status `stands[]` (AODB stand names, 8 snapshots 07:32-16:32 UTC 24 Sep), DataSF `chfu-j7tc` gates with operations 18-31 Aug 2026, flysfo terminal maps | DataSF PDDL; flysfo no published terms (used for names/checks only, docs/research/gate_truth.md §7) | stand name = AODB name; stands without an AODB name in the snapshots = DataSF gate number. OSM refs only link the two. |
| Along-axis calibration, verification | NAIP 2024 (USDA, 0.6 m, flown 2024-05-20; `refs/cache/naip/`) | public domain (USDA credit requested) | parked aircraft read by eye on oriented patches (§3.2), red boxes by colour, pavement check |
| Verification, names of ambiguous lines | own ADS-B recording, **adsb.lol files only** (`refs/cache/rec/adsblol_*`, 07:28-10:28 and 15:13-19:12 UTC 24 Sep, read 19:15 UTC) + flysfo stand windows (`tools/stands/adsb_parked.py`) | adsb.lol: ODbL 1.0 (realtime_feeds.md §3.1). adsb.fi is not used: its terms forbid licensing the data (§3.2), and the stand file is ODbL (review round 2) | parked stays (on ground, < 1 kt, >= 180 s), median antenna position with NACp >= 8, tied to SFO's stand window of the aircraft's callsign; each stay records its provider |
| Aircraft dimensions and planforms | `js/aircraft/types.js` after applySpec (its SPEC values are the manufacturers' airport-planning numbers, checked by `tools/models/check_dims.py`; dumped by `tools/stands/dump_types.mjs`) | - | class of each type, collision planforms (as js/live/ground.js), door tables and dock2 - the geometry the app renders (review round 2; before: a class-shaped planform from REF) |
| Clearances | ICAO Doc 9157 Part 2 (Aerodrome Design Manual, 4th ed. 2005) §3.4.4, p. 3-10 (skybrary copy `refs/cache/icao/sky3090.pdf`, read 24 Sep 2026): code A, B 3.0 m; C 4.5 m; D, E, F 7.5 m; "can be reduced ... between the terminal (including passenger loading bridges) and the nose of an aircraft; and ... over a portion of the stand provided with azimuth guidance by a visual docking guidance system" | - | notes; the physical limit used for exclusivity is 3.0 m |
| Not used | Google screenshots (reference only, owner 24 Sep 2026); X-Plane Gateway (GPL, names shifted, stands_xcheck.md §5.3) | | |

## 3. Method

### 3.1 Which lead-in is which SFO stand

Default: the OSM lead-in whose `ref` equals the stand's gate number. Every exception is written out with its evidence
in `tools/stands/stand_table.py` (`OVERRIDES`, `DROPPED`), in the table in §7, and summarised here:

- **Suffixed stands (AODB).** `B5S`, `B11S`, `B16S` are the straight, long OSM lead-ins at the B-west pods; `B5`,
  `B11`, `B16` the curved ones (ADS-B: JBU413 A321 on curved B5, AAL177 A321 on curved B16, ASA811 A332 with SFO stand
  window B11S on the straight B11 line). `A1V`, `A13V`, `E10U` (ADS-B UAL2647 B39M), `E11U`, `E13T` are the only
  variants of their gates in the feed and take the OSM line of that gate. `C9V` (767s) takes the only other lead-in at
  the C9 bridge (unreferenced OSM way 1096422761) - **inferred, no ADS-B yet**. `G13S` (A388/B748/B77W) is the OSM G13
  line at the three-bridge G13-G14 hold room. `G13R` and `G14T` (narrow bodies SFO plans at the G13 and G14 hold rooms at the same time - a MARS split of G13S) have no identifiable line and are not modelled.
- **A4T** = the OSM line tagged `A3` (A3 is a hold-room label without operations; A4T takes narrow bodies; NAIP shows
  a narrow body with its nose 1.7 m past that line's stop). `B8` = the unreferenced OSM line between B7 and B9 (ADS-B
  ASA424 B39M at AODB B8, NAIP narrow body on it). `G11` = the OSM G11 line at the G11-G12 hold room (alias G12);
  `G13S` has alias G14 (OSM gate nodes "G11-G12", "G13-G14").
- **Split** (previously merged under one stand): B6/B7/B8, B19/B20, B22/B23, B24/B25, C7/C9, D5/D6, E2/E3, F7/F8,
  F17/F18, F21/F22, A11/A13V, A12/A15, E12/E13T, G10/G14 (G14 is now a gate of G13S). **Renamed / added:** our old
  "C11" is C9; the real C11 is at the C-pier tip (ADS-B DAL2635); F9, F10 added; D11-D15 on their OSM lines (6-14 m
  closer to the rotunda than before); B5 and B16 take A321s (class C); C10 heading 319.5° and E6 155.1° from OSM
  (ADS-B: ACA738 320.6°, gate_truth.md UAL367 154.7°).
- **Dropped:** B1, C2, D17, D18 (no operations), A3/A7/A14 (no AODB stand, no operations), G13R, G14T, and duplicate OSM
  lines without an SFO name (straight B20 1096422706, B23 1096422699, straight B26 1096422703, the unreferenced line
  12.8 m behind A4T, E11 1096433104).

### 3.2 Nose position along the line

> **Review round 2 - NAIP relief.** NAIP is orthorectified to the terrain, so parked aircraft lean EAST in the image
> by k x height. `tools/stands/naip_relief.py` measures the imaged fuselage centre numerically on 26 stands (bright
> band midpoint, rows 4-22 m behind the nose) and fits **k = 0.54 +- 0.04 m/m** (residual 0.70 m rms, 25 stands; model
> lat_img = lat_true + k h cos(hdg), h = 3.4 m narrow / 5.3 m wide fuselage band). The imaged fuselages sit 1.2-2.6 m
> east of the lines - the by-eye "lateral 0.0" readings below did not see this, and the "relief up to ~1 m" statement
> was wrong by a factor 2-3. Now: along readings are corrected at nose height (h 2.5 / 4.5 m), the lateral check uses
> only the measured, corrected fuselage centre, and the calibration below is recomputed from corrected readings:
> **narrow bodies +1.2 m, wide bodies +3.3 m** (was +1.0 / +4.0). F15 is placed on the corrected reading (lateral
> -5.9 m instead of -8.0 m, nose +8.3 m instead of +7.0 m); ADS-B (UAL1189 B39M) now lies 0.9 m from its axis (was 3.1 m).

OSM mappers end the lead-in near the painted stop marks, not at a type's nose wheel (stands_xcheck.md §4.3). The app's
`nose` is the nose tip of the stopped aircraft. I read 45 parked aircraft on NAIP 2024 (oriented patches, 0.1-0.2 m
per pixel, 1 m ticks, `tools/stands/montage.py`; readings in `stand_table.NAIP_OBS`): nose tip relative to the OSM
stop node, and the fuselage axis offset. Medians (excluding 3 uncertain readings and 3 with |lateral| >= 3 m):
**narrow bodies +1.0 m, wide bodies +4.0 m** ahead of the OSM stop. `nose` = OSM stop + that offset for the stand's
class group. Reading accuracy is about +/- 1.5 m along (bridge cabs and shadows hide some noses; fuselage relief
displacement in the orthophoto up to ~1 m).

Cross-check with ADS-B: the antenna medians lie a median 9.5 m behind the model nose, lateral median |0.3| m. The
along value depends on the airframe, not on the pier (observed, §7): A320-family aircraft of JetBlue, American,
Frontier and Alaska report -1.1..+0.4 m from the model nose at B5, B12, B16, B17, B18, B21, B24, B25 (B23, mixed
A321/A21N, -3.6 m); Boeing 737/757, Embraer and A220 -2.6..-16 m; wide bodies -10..-18 m; narrow bodies on wide-body
stands stop far short of the wide-body stop point (A319 at G7 -31 m, B39M at F15 -21 m, B738 at F21 -23 m). *Inferred:* the Airbus A32x positions are
referenced near the nose (antenna offset compensated), the others at the GNSS antenna. The app's `ANT = 0.2 L` fits the
Boeing family; matching A32x reports needs the realtime workflow's attention (request in docs/requests/stands_rebuild.md).

One stand is positioned on NAIP instead of OSM (`pos_src: naip`): **F15**, whose OSM way is a 24.5 m two-node stub;
NAIP shows a wide body parallel to it 8 m to its left with the nose 7 m ahead (SFO parks B772 at F15).

### 3.3 Class

`cls` = the class of the largest aircraft type SFO allocates to the stand (flysfo AODB types, all snapshots) or that
ADS-B saw parked there - since review round 1 only ADS-B stays that were accepted on the stand's line (§3.4) and whose
type agrees with the type SFO planned for that flight (C11 had been raised to class E by an A333 746 m away, D14 to
class D by a B753 flying another flight number; both are class C now); dimensions from REF (ACAP documents). DataSF chfu-j7tc carries **no aircraft types** (columns
time, airline, flight_number, transaction, terminal, gate, remark; observed in the dataset metadata), so it only
supplies names. App classes as in `js/live/airport.js` CLASS_MAX (span / length limits + the traffic.js 0.6 m / 2 m
tolerances). Designators not in REF: E175 -> E75L, B787 -> B789, B76W -> B763 (767-300ER winglet span about 51 m, not
in REF, inside class D's 52 m either way), E295 (only at B2, whose class B738/B39M set). Physical limits: §5.

### 3.3a Painted lead-in lines (review round 1)

The lead-in paint is measured numerically on NAIP (`tools/imagery/paintline.py`, index (R + G)/2 - B for these pale
lines): 19 stands have a clean fit. Two disagreed and were moved onto the paint (`pos_src: osm+paint`, the OSM lead-in
polyline is moved with them): **D14** +3.21 m lateral, +0.64 deg (review: +3.07 m; ADS-B +2.5 m) and **C4** -1.12 m,
-0.25 deg (review: -1.7 m, +2.5 deg with a wider window). A correction is refused when it would move the line away from
a parked NAIP aircraft (G10 would have been). F16's clean fit (-4.7 m, -18 deg) follows its curving lead-in and is not
used. The NAIP parked-aircraft readings (`NAIP_OBS`) stay what they were: readings by eye with +-0.7 m lateral
resolution; a lateral 0.0 there means "within the reading resolution", not a measured zero (the summary table says so).

### 3.4 Evidence per stand

`verified_by` lists `naip` when the relief-corrected, numerically measured NAIP fuselage centre lies within 1.5 m of
the axis (review round 2; about 2 sigma of the relief fit - a NAIP check cannot resolve better than ~+-1.5 m; never
for the stand positioned on that same reading, F15), `paint` when the painted lead-in line on NAIP (yellow-ridge fit
3-22 m behind the nose, `build_stands.paint_fit`, >= 7 samples, rms <= 0.3 m) lies within 0.8 m / 1.5 deg of the
model axis, and `adsb` when the ADS-B (adsb.lol) antenna median of the aircraft SFO had on that stand lies within
**1.5 m** of the line (was 3 m; review round 2, G5) and its heading within 10 deg (ADS-B surface headings come in
2.8125 deg steps: 426 of 439 stay headings are multiples of 360/128). ADS-B stays far from the line (push-back /
waiting / plan changes) are listed in `refs/cache/stands/stands_built.json` (`adsb_rejected`) and not used.
ADS-B medians more than 3 m or 10 deg off the axis are recorded as `conflict` (D3, D4 three aircraft each, D8, D9) and
empty `verified_by` (the evidence that would otherwise verify is kept in `verified_unconfirmed`).
`src` = `obs` only when an aircraft was seen on the line (`naip` or `adsb`); a painted lead-in alone confirms the axis,
not the stop point, so paint-only stands are `inf` (review round 2: the data file's note and this section had
disagreed).

## 4. Jet bridges

- Geometry from OSM jet-bridge ways, oriented building -> cab (base = the end nearer the terminal outline; for the 5
  ways with ends at equal building distance, the end farther from the nearest stand stop). Per bridge:
  `attach` = building end (for a bridge branching off another bridge's fixed walkway: that bridge's building end),
  `walk` = polyline from the building to the rotunda, `rotunda` = first node of the final segment when the way has a
  fixed part before it (else null - the app derives it), `cab` = the parked cab end as mapped, `osm_id`, `assoc`.
- **Forced** (review round 2, `stand_table.BRIDGE_FORCE`): at the B10 / B11 hold room 1096422714 (OSM ref B11; NAIP
  shows its cab at the L1 door of the aircraft on the curved B11 line) -> B11; 1096422712 (ref "B11S"; the only bridge on
  B10's door side, cab 20.7 m left of the nose) -> B10; 1096422713 (ref "B10"; 13.7 m to the RIGHT of the B10 axis, so it
  cannot serve B10's left doors) -> B11S. The review asked to follow the OSM refs for B10; rejected on that geometry.
- Assignment: optimal assignment (Hungarian) of bridges to door slots (narrow body 1, wide body 2, class F 3). A bridge
  can serve a stand only if its pivot (rotunda, else attach) or its parked cab is not on the stand's right side and the
  pivot is 8-48 m from the door; cost = pivot-door distance, +10 m when the OSM ref/name gate differs from the stand's
  gate (OSM bridge refs are shifted at the B-west pods, so geometry leads). Alternative positions are assigned in a
  second pass and may only take bridges no base stand uses (a bridge must exist once in the app); B11S has its own
  (OSM ref B11S), B5S / B16S / C9V get none and carry `shares_bridges_of` (their base stand). One override: OSM
  "A7 Jetway" = A6's third bridge (A6 takes A388s; inferred). One OSM bridge is ignored: "F18 Jetway" (a 7.8 m stub).
- Rotunda (review round 1): the first node of the final segment when that segment is >= 4 m (was 8 m: B10's fully
  retracted tunnel is 7.2 m), or the branch point for a bridge that branches off another's walkway (G11 L1, F15 L1). An
  OSM rotunda closer to the door than the shortest bridge can retract (9.846 m + 3 m cab) or inside the wing sweep of
  the types SFO parks there is moved back along the OSM walkway (`rotunda_osm` keeps the mapped point, `rotunda_src`
  says by how much): A4 2.5 m, C6 3.5 m, C8 11.5 m, E5 5.5 m, E12 21.5 m (the OSM node is part-way along the imaged
  tunnel), F16 2.5 m, F17 1.5 m, F19 2.0 m. F5 has no feasible point (§10).
- `cab_pose`: `docked` when the OSM cab lies within 6 m of a door of an accepted type (OSM mapped the bridge docked),
  else `parked` - a docked cab must not be used as a rest pose.
- `stow`: a rest pose for the tunnel end, 9.85-30 m from the rotunda, clear (+1 m) of the envelope of every stand within
  150 m (own, alternative and exclusive stands included), of the building and (+0.5 m) of the other bridges' fixed
  parts and rest poses; the pose nearest the OSM direction is kept. Every main-deck and upper-deck bridge has one.
- `rotunda_max_r`: half the distance to the nearest other rotunda and the clearance to other fixed walkways, capped at
  2.45 m (G pier pairs 4.6-4.9 m apart need r ~2.3 m). F15 and G11 have two rotundas 3.4 m apart at the end of one fixed
  walkway; NAIP shows both tunnels leaving one elevated junction there (`refs/cache/stands/view/F15rot.png`,
  `G11rot.png`): a twin head (inferred), modelled as two drums of r 1.64 m (`rotunda_twin_of`).
- `geom_src`: every bridge is `osm (traced; not NAIP-verified)`. The imaged bridge roofs lean ~0.54 m per m of height
  (~3-4 m east for a bridge; review round 2 saw the C3 walkway roof 4 m east of the OSM line) and the parked cab pose
  changes between images, so NAIP cannot confirm the walkways to 1.5 m.
- F10's OSM bridge is no longer used (`stand_table.BRIDGE_IGNORE`): it lies right-front of the F10 nose, NAIP shows it
  parked ahead of the regional jet, and docking needs a ~150 deg cab turn. F10 is modelled without a bridge (inferred).
- Door numbers: ordered by the parked cab's position along the aircraft (nearest the nose = 1). A third bridge
  (A380 upper deck at A6, A11, G13S) is written to `bridges_upper` with `door: 3`, not to `bridges`: the app's bridge
  model docks main-deck doors only and docked it into the fuselage (2-D audit, §4 last point). See the request.
- Result: counts in §1. F18 (CRJ2) has none: the only bridge near it is OSM's 7.8 m "F18 Jetway" stub 32-39 m ahead of
  its nose, which cannot reach; the F17/F18 bridge serves F17 (inferred: F18 boards by stairs or via the F17 bridge -
  not verified).
- Visual check: `python3 tools/stands/view.py <name> x0 z0 x1 z1 2 --stands data/sfo_stands.json --plan --noosm`
  renders the class reference aircraft and the docked bridge lines on NAIP (outputs stay in `refs/cache/stands/view/`).
  All seven boarding areas were inspected on 24 Sep 2026: the planforms sit on the imaged aircraft and markings.
- 2-D clearance audit of the running app (`tools/drawing/audit.py` on a fresh `jobs/extract2d.mjs` extraction, output
  kept in a scratch directory; `docs/drawings/` belongs to the drawing workflow and was not rewritten): see §4a.

### 4a. 2-D clearance audit of the running app

`jobs/extract2d.mjs` + `tools/drawing/audit.py` (the drawing workflow's tools, run on 24 Sep 2026 ~16:25 UTC with
`DRAW_OUT` in a scratch directory; the app loaded the new data: 108 stands + 1 remote, 129 bridges). Distinct findings:
**75 COLLISION, 1 OFF-PAVEMENT, 44 CLEARANCE, 254 WARNING**, against 114 / 4 / 50 / 209 for the previous
(Google-survey) data in `docs/drawings/report.md`. What remains:

- B11 / B11S aircraft-aircraft: an `excl` pair (the audit does not know `excl` yet).
- Bridge models: L1/L2 walkways and rotundas of the same stand touching each other or the building (21 + 10), docked L2
  tunnels touching B789/B772/B748 fuselages at G1, G3, G4, G11, F11, F15, F22, A6, A11, G13S, and the F10 bridge
  (whose OSM pivot lies right-front of the nose) crossing a docked CRJ: `js/live/gates.js` derives rotundas and door
  positions itself (request: use `rotundaW` / `walk`).
- `envelope-rest-bridge` (19): parked bridge cabs inside the envelope of some accepted type - the parked pose is
  gates.js's.
- App class envelopes E10U/E12 (1.0 m) and F19/F20 (2.4 m) overlap; with the manufacturers' reference types
  (check_stands.py) they clear by 7.3 m and 5.8 m (§5). The app's envelopes use its own `TYPES` table.

## 5. Mutually exclusive positions (MARS / suffixed stands) and clearances

Since review round 1 every clearance uses the envelope of all types the app accepts on each stand (`tools/stands/geom.py`:
the traffic.js standFits rule, planforms from the ACAP dimensions; shorter types carry their wings further forward).
`excl` lists stands that cannot be occupied at the same time: (a) an alternative position and its base
(B5/B5S, B11/B11S, B16/B16S, C9/C9V), (b) any pair whose envelopes come within 3.0 m, unless SFO's plan occupies both
at once; then both stands are limited to the largest span / length SFO (or accepted ADS-B) put there (`span_max`,
`len_max`). If that clears 3 m, done; if the limited envelopes still come within 3 m but no longer overlap, the pair is
kept (`tight_with`: E10/E12 0.4 m, F19/F20 1.9 m - SFO plans them together 26 and 29 times, so making them exclusive
would push really parked aircraft off their stands; our single stop point per stand is the likely error, real stop
marks are per type).

Review round 2: clearances are computed on the app's planforms (types.js) with every designator the app knows, at the
per-family stop points (`type_stops`: ADS-B shows 737s stopping 15-18 m short at E12, F15, F21, an A319 29 m short at
G7, ...). E10/E12 and F19/F20 still came within 1.1 / 1.9 m with the class limits - only through types never seen
there (an A319neo at E12's nose, a 777-200LR at F19). Both stands of such a pair now carry **`types_ok`**, the types
SFO / ADS-B actually put there; with them they clear 4.2 m and 5.1 m (> 3 m, below ICAO C 4.5 / D-F 7.5 m; SFO plans
them simultaneously 42 and 26 times). The app honours `types_ok` / `type_stops` only after the traffic.js request.
Pairs below the ICAO clearance:

Review round 3 (25 Sep 2026): the 757-200/-300 and 767-300ER now carry the Boeing winglet spans (41.1 / 50.9 m, geom.py
WINGLET_SPAN), which narrows F21/F22, F19/F20, F18/F19 and C9/C11 below. The clearances are worst-case type pairs
(every type the stand accepts, at its stop), so the aircraft SFO actually parks side by side usually clear by more.
ICAO Annex 14 3.13.6 / Doc 9157 Part 2 §3.4.4 (table verified by review round 4 in `refs/cache/icao/doc9157p2_p70.png`):
A/B 3.0, C 4.5, D-F 7.5 m; for code D-F only, the clearance may be reduced (a) between the terminal incl. a fixed
passenger bridge and the nose and (b) over any portion of the stand provided with azimuth guidance by a VDGS - so a
D-F wingtip reduction IS possible where a VDGS guides the stand (round 3 wrongly said "not at the wingtips"); there
is no relief for code C, and SFO's VDGS coverage is not verified. The evidence that SFO nevertheless operates
these pairs at the same time is SFO's own plan (column 4: overlapping AODB stand windows in 11 flysfo snapshots,
24-25 Sep 2026). How SFO keeps its wingtip clearance there (wing walkers, marshalling, type restrictions in its gate
assignment rules) is not published and is **not verified**; where SFO's plan confirms type restrictions they are
recorded as `types_ok` (E10/E12, F19/F20, F18/F19 via `span_max`). Everything else is kept as observed.

<!--BEGIN:pairs-->
| pair | clearance m: SFO path (class limits, per-family stops) / with types_ok | ICAO | SFO plans both at once (overlaps) | handled |
|---|---|---|---|---|
| B4 / B5S | 0.0 / 0.0 | 7.5 | 0 | excl |
| B5 / B5S | 0.0 / 0.0 | 7.5 | 0 | alternative positions (excl) |
| B10 / B11S | 0.0 / 0.0 | 7.5 | 0 | excl |
| B11 / B11S | 0.0 / 0.0 | 7.5 | 0 | alternative positions (excl) |
| B15 / B16S | 0.0 / 0.0 | 7.5 | 0 | excl |
| B16 / B16S | 0.0 / 0.0 | 7.5 | 0 | alternative positions (excl) |
| C9 / C9V | 0.0 / 0.0 | 7.5 | 0 | alternative positions (excl) |
| C9V / C11 | 0.0 / 0.0 | 7.5 | 4 | excl (SFO plans both at once 4 times, but even its largest types overlap) |
| F19 / F20 | 1.9 / 4.3 | 7.5 | 40 | kept: SFO plans both at once 40 times; types_ok (strict path); clearance 1.9 m on SFO's path (class limits), 4.3 m with types_ok - TIGHT (< 3 m) |
| F21 / F22 | 3.3 / 3.3 | 7.5 | 30 | kept: SFO plans both at once 30 times; no limit helps; clearance 3.3 m on SFO's path (class limits), 3.3 m with types_ok (below ICAO) |
| F18 / F19 | 3.7 / 5.4 | 7.5 | 25 | kept: SFO plans both at once 25 times; span_max / len_max = largest types SFO parks there; clearance 3.7 m on SFO's path (class limits), 3.7 m with types_ok (below ICAO) |
| E10 / E12 | 4.5 / 4.5 | 7.5 | 66 | kept: SFO plans both at once 66 times; inferred A320 stop at E12 (analog of B737); inferred A220 stop at E12 (analog of B737); inferred EJET stop at E12 (analog of B737); clearance 4.5 m on SFO's path (class limits), 4.5 m with types_ok (below ICAO) |
| C8 / C10 | 5.7 / 5.7 | 7.5 | 10 | kept: SFO plans both at once 10 times; no limit helps; clearance 5.7 m on SFO's path (class limits), 5.7 m with types_ok (below ICAO) |
| F20 / F21 | 6.4 / 6.4 | 7.5 | 43 | kept: SFO plans both at once 43 times; no limit helps; clearance 6.4 m on SFO's path (class limits), 6.4 m with types_ok (below ICAO) |
| G7 / G8 | 6.5 / 6.5 | 7.5 | 51 | kept: SFO plans both at once 51 times; no limit helps; clearance 6.5 m on SFO's path (class limits), 6.5 m with types_ok (below ICAO) |
| F13 / F15 | 6.6 / 6.6 | 7.5 | 43 | kept: SFO plans both at once 43 times; no limit helps; clearance 6.6 m on SFO's path (class limits), 6.6 m with types_ok (below ICAO) |
| C9 / C11 | 6.8 / 8.0 | 7.5 | 23 | kept: SFO plans both at once 23 times; no limit helps; clearance 6.8 m on SFO's path (class limits), 6.8 m with types_ok (below ICAO) |
| A5 / A9 | 6.9 / 6.9 | 7.5 | 29 | kept: SFO plans both at once 29 times; no limit helps; clearance 6.9 m on SFO's path (class limits), 6.9 m with types_ok (below ICAO) |
| C5 / C7 | 7.1 / 7.1 | 7.5 | 57 | kept: SFO plans both at once 57 times; no limit helps; clearance 7.1 m on SFO's path (class limits), 7.1 m with types_ok (below ICAO) |
| G2 / G5 | 7.1 / 7.1 | 7.5 | 42 | kept: SFO plans both at once 42 times; span_max / len_max = largest types SFO parks there; clearance 7.1 m on SFO's path (class limits), 7.1 m with types_ok (below ICAO) |
| C6 / C8 | 7.3 / 7.3 | 7.5 | 15 | kept: SFO plans both at once 15 times; no limit helps; clearance 7.3 m on SFO's path (class limits), 7.3 m with types_ok (below ICAO) |
<!--END:pairs-->

## 6. Runway ends and lighting (same session)

- **Blast pads** (`js/live/airport.js` END_ZONES), measured on NAIP 2024 strips along the NASR runway axes (3 px/m):
  10L 269 m (dark pad edge; OSM 270, FAA diagram ~260), 10R 231 m (chevrons end ~230 m, the pad merges into taxiway
  pavement; OSM 231, diagram ~240), 28R 98 m and 28L 98 m (pad edge at the seawall road; OSM 91/95, diagram ~90,
  replacing 108 m). Chevron apexes (`tools/imagery/check_markings.py`, yellow peaks on the axis): 10L 17.1, 47.5, 78.1,
  108.5, 139.0, 169.5, 199.8, 230.5 m; 10R 16.6 ... 199.7 m; 28R 17.3, 47.8, 78.3 m; 28L 17.1, 47.6, 78.1 m - spacing
  30.5 m (100 ft), first apex ~17 m. The shaders keep 29.7 m / 15 m (`js/shaders/ground.js`, `js/three/ground.js` are
  not mine; request in docs/requests/static_geometry_round2.md).
- **EMAS chevrons** (review round 2, `js/live/world.js`, which I own): first apex beyond the runway end 1L 17.2, 19R 16.3,
  1R 17.2, 19L 16.6 m (0.05 m samples) = 5.4-6.4 m after the bed entry (`END_ZONES[].chev0`), spacing 30.4-30.8 m ->
  30.48 m. Was 12 m / 30 m (4.4-5.9 m off).
- **EMAS beds** (review round 1, re-checked on NAIP oriented patches): 19R 124.8 m (was 122.0), 19L 124.1 m (was 117.0),
  1L 133.2 and 1R 113.4 m unchanged, width 69.3 m at all four (was 66 m); 10.67 m setback confirmed.
- **Runway axes** (`js/world/airfield.js` RWY) now derive from the NASR ends through the exact frame (were legacy
  constants, up to 1.9 m off at the ends).
- **Lighting** (`js/geo.js`, `js/anim/lights.js`) from FAA NASR APT_RWY_END.csv, cycle 2026-09-03 (re-read today):
  approach lights only 28R ALSF2, 28L MALSR, 19L MALSF (FAA standard layouts: ALSF-2 bars every 100 ft to 2400 ft with
  flashers from 1000 ft; MALS bars every 200 ft to 1400 ft; MALSF flashers on the outer three bars; MALSR RAIL flashers
  1600-2400 ft). PAPI-4L at 10L 3.00° (TCH 80 ft), 10R 3.00° (68), 19L 3.00° (71), 19R 3.15° (58), 28R 3.00° (68), 28L
  2.85° (67); none at 1L/1R. PAPI distance from the threshold = TCH / tan(angle) (inferred, NASR has no PAPI position),
  box settings angle ±30' / ±10'. TDZ lights only at 28R and 19L (NASR TDZ_LGT_AVBL_FLAG).

## 7. Every stand

<!--BEGIN:stands-->
| stand | gate | AODB | cls (largest type) | pos_src | verified_by | NAIP resid along/lat m (relief-corrected; n/m = lateral not measured) | ADS-B (adsb.lol) n, along/lat m, dhdg | paint lat m / dh deg | bridges | excl / alt_of / tight / types_ok / per-family stops | name / position evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | A1 | A1V | EL (B77W) | osm | - | - | - | - | 2 | - | AODB stand A1V (only A1 variant in the feed) on the OSM A1 lead-in |
| A2 | A2 | A2 | EL (B77W) | osm | paint+adsb | - | 1, -7.9 / -0.3, +1 | -0.30 / +0.31 | 2 | - | OSM ref = SFO name |
| A4 | A4 | A4T | C (B39M) | osm | - | -0.7 / +0.8 | - | - | 1 | - | OSM ref A3 = SFO stand A4T (A3 hold-room label only; AODB narrow-body types; NAIP narrow-body at this stop) |
| A5 | A5 | A5 | EL (B77W) | osm | paint | - | - | +0.03 / -0.02 | 2 | - | OSM ref = SFO name |
| A6 | A6 | A6 | F (A388) | osm | paint | - | - | -0.42 / -0.09 | 3 | - | OSM ref = SFO name |
| A8 | A8 | A8 | EL (B77W) | osm | paint | - | - | -0.18 / -0.17 | 2 | - | OSM ref = SFO name |
| A9 | A9 | A9 | EL (B77W) | osm | - | -0.9 / +1.7 | - | - | 2 | - | OSM ref = SFO name |
| A10 | A10 | A10 | EL (B77W) | osm | - | -6.4 / n/m | - | - | 2 | - | OSM ref = SFO name |
| A11 | A11 | A11 | F (A388) | osm | naip | +0.2 / -0.4 | - | - | 3 | - | OSM ref = SFO name |
| A12 | A12 | A12 | E (A332) | osm | - | +7.3 / n/m (u) | - | - | 1 | - | OSM ref = SFO name |
| A13 | A13 | A13V | EL (B77W) | osm | paint+adsb | - | 1, -12.1 / -0.1, +1 | -0.61 / -0.54 | 2 | - | AODB stand A13V (only A13 variant in the feed) on the OSM A13 lead-in |
| A15 | A15 | A15 | C (B38M) | osm | naip | +0.1 / -0.1 | - | -4.09 / -1.56 (noisy) | 1 | - | OSM ref = SFO name |
| B2 | B2 | B2 | C (B39M) | osm | - | -1.9 / n/m | - | - | 1 | - | OSM ref = SFO name |
| B3 | B3 | B3 | C (B39M) | osm | adsb | - | 2, -11.3 / +0.1, -0 | - | 1 | - | OSM ref = SFO name |
| B4 | B4 | B4 | C (A21N) | osm | - | +0.6 / n/m | - | - | 1 | B5S | OSM ref = SFO name |
| B5 | B5 | B5 | C (B739) | osm | paint+adsb | - | 1, -0.6 / -0.7, +3 | -0.38 / -0.76 | 1 | B5S | curved OSM B5 lead-in; ADS-B A321 JBU413 at AODB B5 |
| B5S | B5 | B5S | EL (B77W) | osm | paint | - | 1, -13.4 / -1.6, +0 | -0.15 / -0.38 | 0 | B4 B5 alt of B5 | straight OSM B5 lead-in = wide-body alternative (AODB B5S takes A359/B77W/A333) |
| B6 | B6 | B6 | C (B39M) | osm | paint+adsb | - | 3, -7.9 / +0.8, -1 | -0.10 / -0.38 | 1 | - | OSM ref = SFO name |
| B7 | B7 | B7 | C (B39M) | osm | adsb | - | 2, -10.3 / +0.3, -1 | - | 1 | - | OSM ref = SFO name |
| B8 | B8 | B8 | C (B39M) | osm | adsb | -2.5 / n/m | 5, -7.9 / +0.3, +0 | - | 1 | - | unreferenced OSM lead-in between B7 and B9 at the OSM B8 jet bridge; ADS-B ASA424 B39M at AODB B8 and NAIP narrow-body on it |
| B9 | B9 | B9 | C (B39M) | osm | adsb | - | 2, -6.2 / -0.1, +0 | - | 1 | - | OSM ref = SFO name |
| B10 | B10 | B10 | C (B739) | osm | - | - | - | - | 1 | B11S | OSM ref = SFO name |
| B11 | B11 | B11 | C (A319) | osm | - | +0.5 / n/m | - | - | 1 | B11S | curved OSM B11 lead-in (NAIP narrow-body on it) |
| B11S | B11 | B11S | EL (A339) | osm | adsb | - | 1, -11.0 / -0.4, +0 | - | 1 | B10 B11 alt of B11 | straight OSM B11 lead-in; ADS-B ASA811 A332 at AODB B11S |
| B12 | B12 | B12 | C (B38M) | osm | paint+adsb | - | 5, -7.9 / -0.0, +0 | -0.13 / +0.10 | 1 | - | OSM ref = SFO name |
| B13 | B13 | B13 | C (B39M) | osm | adsb | - | 3, -7.8 / +0.2, +0 | - | 1 | - | OSM ref = SFO name |
| B14 | B14 | B14 | C (B38M) | osm | adsb | - | 6, -3.6 / +0.1, +0 | - | 1 | - | OSM ref = SFO name |
| B15 | B15 | B15 | C (B39M) | osm | - | +1.1 / n/m | - | +4.05 / +0.38 (noisy) | 1 | B16S | OSM ref = SFO name |
| B16 | B16 | B16 | C (B739) | osm | adsb | - | 1, -0.5 / -0.6, - | - | 1 | B16S | curved OSM B16 lead-in; ADS-B AAL177 A321 at AODB B16 |
| B16S | B16 | B16S | EL (B77W) | osm | adsb | - | 1, -20.1 / +0.1, +0 | - | 0 | B15 B16 alt of B16 | straight OSM B16 lead-in = wide-body alternative (AODB B16S takes B763/B76W/A339) |
| B17 | B17 | B17 | C (A21N) | osm | adsb | - | 8, -4.2 / +0.8, +1 | - | 1 | - | OSM ref = SFO name |
| B18 | B18 | B18 | C (A321) | osm | adsb | - | 4, +0.4 / -0.4, +1 | - | 1 | - | OSM ref = SFO name |
| B19 | B19 | B19 | C (A21N) | osm | adsb | - | 4, -1.9 / +0.1, -0 | - | 1 | - | OSM ref = SFO name |
| B20 | B20 | B20 | C (B38M) | osm | adsb | +1.5 / n/m | 2, -1.5 / -0.4, +1 | - | 1 | - | curved OSM B20 lead-in (NAIP narrow-body on it); straight 1096422706 has no SFO name |
| B21 | B21 | B21 | C (A321) | osm | adsb | - | 5, -0.1 / -0.1, +1 | - | 1 | - | OSM ref = SFO name |
| B22 | B22 | B22 | C (B38M) | osm | adsb | -4.1 / n/m | 5, -16.5 / -0.7, +0 | - | 1 | stops EJET -4 | OSM ref = SFO name |
| B23 | B23 | B23 | C (B38M) | osm | adsb | -0.2 / n/m | 7, -3.8 / -0.0, -2 | - | 1 | - | OSM B23 lead-in hdg 339 (NAIP + ADS-B AAL2856 A321 on it); the second OSM B23 way 1096422699 has no SFO name |
| B24 | B24 | B24 | C (B38M) | osm | adsb | - | 7, -2.4 / -1.0, -2 | - | 1 | - | OSM ref = SFO name |
| B25 | B25 | B25 | C (A21N) | osm | adsb | - | 8, -0.5 / -0.5, +1 | - | 1 | - | OSM ref = SFO name |
| B26 | B26 | B26 | C (B38M) | osm | - | - | 7, -0.4 / -1.6, -2 | - | 1 | - | OSM B26 lead-in hdg 64 (ADS-B AAL2799 B38M on it); straight 1096422703 has no SFO name |
| B27 | B27 | B27 | C (A21N) | osm | adsb | - | 4, -5.4 / -0.9, -0 | - | 1 | - | OSM ref = SFO name |
| C1 | C1 | C1 | C (B738) | osm | paint+adsb | - | 1, -12.2 / +0.2, +0 | -0.33 / +0.10 | 1 | - | OSM ref = SFO name |
| C3 | C3 | C3 | CL (B752) | osm | - | +0.7 / -0.2 | - | - | 1 | - | OSM ref = SFO name |
| C4 | C4 | C4 | C (B38M) | osm+paint | paint+adsb | - | 2, -5.9 / -0.0, -2 | +0.00 / +0.03 | 1 | - | OSM ref = SFO name |
| C5 | C5 | C5 | CL (B753) | osm | adsb | +4.6 / -0.3 | 3, -12.0 / +1.0, -0 | - | 1 | - | OSM ref = SFO name |
| C6 | C6 | C6 | C (A21N) | osm | adsb | - | 3, -7.6 / -0.4, +1 | +0.42 / +10.02 (noisy) | 1 | - | OSM ref = SFO name |
| C7 | C7 | C7 | C (A21N) | osm | naip+adsb | -0.3 / -0.1 | 4, -11.9 / +0.4, +0 | - | 1 | - | OSM ref = SFO name |
| C8 | C8 | C8 | D (B763) | osm | paint | - | - | -0.63 / +0.00 | 1 | - | OSM ref = SFO name |
| C9 | C9 | C9 | CL (B752) | osm | naip+adsb | +1.1 / -0.3 | 2, -5.4 / +0.5, -0 | - | 1 | C9V | OSM ref = SFO name |
| C9V | C9 | C9V | D (B76W) | osm | - | - | - | +0.14 / -0.08 (noisy) | 0 | C9 C11 alt of C9 types_ok B763 | INFERRED: unreferenced OSM lead-in at the C9 bridge, the only other line there; AODB C9V = 767 alternative of C9 |
| C10 | C10 | C10 | C (B737) | osm | paint+adsb | - | 2, -2.9 / +0.1, +1 | -0.09 / -1.21 | 1 | - | OSM ref = SFO name |
| C11 | C11 | C11 | C (BCS3) | osm | paint+adsb | -2.9 / n/m (u) | 1, -5.5 / +0.4, +3 | +0.53 / +1.41 | 1 | C9V types_ok A319 A320 BCS3 E190 E195 E75L E75S | OSM ref = SFO name |
| D1 | D1 | D1 | C (B38M) | osm | adsb | - | 8, -10.7 / -0.2, -1 | - | 1 | - | OSM ref = SFO name |
| D3 | D3 | D3 | C (B38M) | osm | - | -2.0 / +0.5 | 9, -4.5 / -4.9, +12 | - | 1 | - | OSM ref = SFO name **CONFLICT: ADS-B (9 aircraft) -4.9 m / +12 deg off the axis** |
| D4 | D4 | D4 | C (B38M) | osm | - | -0.2 / +0.2 | 7, -11.4 / -1.8, +24 | -4.63 / -6.30 (noisy) | 1 | - | OSM ref = SFO name **CONFLICT: ADS-B (7 aircraft) -1.8 m / +24 deg off the axis** |
| D5 | D5 | D5 | E (B772) | osm | - | -4.4 / -0.1 | 2, -3.8 / -2.2, -2 | - | 1 | - | OSM ref = SFO name |
| D6 | D6 | D6 | C (B38M) | osm | adsb | +1.0 / n/m | 5, -7.0 / +0.6, +1 | - | 1 | - | OSM ref = SFO name |
| D7 | D7 | D7 | C (B38M) | osm | naip+adsb | +0.1 / -0.4 | 3, -4.6 / +1.2, +2 | - | 1 | - | OSM ref = SFO name |
| D8 | D8 | D8 | C (B38M) | osm | - | - | 1, +0.2 / -8.5, +1 | - | 1 | - | OSM ref = SFO name **CONFLICT: ADS-B (1 aircraft) -8.5 m / +1 deg off the axis** |
| D9 | D9 | D9 | C (B38M) | osm | - | - | 3, -13.3 / +4.6, +12 | - | 1 | - | OSM ref = SFO name **CONFLICT: ADS-B (3 aircraft) +4.6 m / +12 deg off the axis** |
| D10 | D10 | D10 | C (B38M) | osm | adsb | - | 5, -17.5 / +0.2, +1 | - | 1 | - | OSM ref = SFO name |
| D11 | D11 | D11 | C (B38M) | osm | adsb | -6.7 / n/m | 3, -15.1 / -0.1, +0 | +4.12 / +5.12 (noisy) | 1 | - | OSM ref = SFO name |
| D12 | D12 | D12 | C (B39M) | osm | adsb | - | 3, -15.0 / -0.2, -0 | - | 1 | stops A320 -12 | OSM ref = SFO name |
| D14 | D14 | D14 | C (B39M) | osm+paint | adsb | - | 3, -7.4 / -0.6, -1 | -1.99 / -15.76 (noisy) | 1 | - | OSM ref = SFO name |
| D15 | D15 | D15 | C (B38M) | osm | adsb | - | 4, -11.1 / -0.6, -0 | - | 1 | stops A320 -10 | OSM ref = SFO name |
| D16 | D16 | D16 | C (B39M) | osm | - | -4.2 / +0.1 | - | - | 1 | - | OSM ref = SFO name |
| E2 | E2 | E2 | C (B39M) | osm | adsb | - | 1, -14.0 / +0.8, +6 | +0.28 / +0.49 (noisy) | 1 | - | OSM ref = SFO name |
| E3 | E3 | E3 | C (B39M) | osm | adsb | - | 1, -14.7 / +0.1, -0 | +0.86 / +1.67 (noisy) | 1 | - | OSM ref = SFO name |
| E4 | E4 | E4 | C (B39M) | osm | adsb | -1.4 / n/m | 2, -9.6 / +0.3, +1 | +4.00 / +0.00 (noisy) | 1 | - | OSM ref = SFO name |
| E5 | E5 | E5 | C (B39M) | osm | adsb | - | 4, -8.9 / +0.2, -0 | -0.33 / -0.45 (noisy) | 1 | - | OSM ref = SFO name |
| E6 | E6 | E6 | C (B39M) | osm | adsb | - | 5, -8.5 / +0.0, -0 | - | 1 | - | OSM ref = SFO name |
| E7 | E7 | E7 | C (B38M) | osm | adsb | - | 4, -11.7 / +0.6, +0 | -1.95 / -5.71 (noisy) | 1 | - | OSM ref = SFO name |
| E8 | E8 | E8 | C (B38M) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| E9 | E9 | E9 | C (B39M) | osm | adsb | - | 3, -8.3 / -0.9, +7 | +1.73 / +27.95 (noisy) | 1 | - | OSM ref = SFO name |
| E10 | E10 | E10U | C (B39M) | osm | adsb | - | 1, -20.5 / +0.6, -0 | +2.30 / +14.44 (noisy) | 1 | - | OSM E10 lead-in; ADS-B UAL2647 B39M (AODB E10U) antenna 8.4 m behind its stop, hdg 137.8 |
| E11 | E11 | E11U | C (B38M) | osm | paint+adsb | - | 2, -10.4 / +0.3, +0 | -0.09 / -0.31 | 1 | - | OSM E11 lead-in (hdg 261); the unreferenced 1096433104 (hdg 297) is not used |
| E12 | E12 | E12 | CL (B753) | osm | paint+adsb | - | 4, -27.2 / -0.2, -1 | +0.19 / -0.15 | 1 | stops B737 -18, A320 -18, A220 -18, EJET -18 | OSM ref = SFO name |
| E13 | E13 | E13T | C (B39M) | osm | paint+adsb | - | 1, -7.7 / +0.2, -1 | -0.48 / -0.97 | 1 | - | OSM E13 lead-in |
| F5 | F5 | F5 | C (B38M) | osm | adsb | - | 2, -10.8 / +0.3, -1 | - | 1 | stops B737 -1 | OSM ref = SFO name |
| F6 | F6 | F6 | B (E75L) | osm | adsb | - | 2, -10.8 / +0.8, +2 | - | 1 | - | OSM ref = SFO name |
| F7 | F7 | F7 | B (E75L) | osm | - | +2.0 / n/m | - | - | 1 | - | OSM ref = SFO name |
| F8 | F8 | F8 | B (E75L) | osm | adsb | +0.2 / n/m (u) | 2, -10.8 / +0.2, -0 | +6.12 / +22.77 (noisy) | 1 | - | OSM ref = SFO name |
| F9 | F9 | F9 | B (E75L) len_max 31.7 | osm | adsb | -0.3 / n/m | 3, -11.8 / +0.9, -0 | - | 1 | - | OSM ref = SFO name |
| F10 | F10 | F10 | B (CRJ2) span_max 21.2 len_max 26.8 | osm | naip+adsb | +0.7 / +0.6 | 3, -6.0 / -0.3, -0 | - | 0 | - | OSM ref = SFO name |
| F11 | F11 | F11 | E (B772) | osm | paint | - | 2, -21.1 / +1.6, -0 | +0.25 / -0.62 | 2 | stops B737 -2 | OSM ref = SFO name |
| F12 | F12 | F12 | C (B39M) | osm | - | - | - | -4.48 / -18.69 (noisy) | 1 | stops A220 -1, A320 -2, B737 -4, EJET -3 | OSM ref = SFO name |
| F13 | F13 | F13 | EL (B77W) | osm | - | -7.2 / -0.2 | - | - | 2 | stops B737 -1 | OSM ref = SFO name |
| F14 | F14 | F14 | CL (B753) | osm | naip | +1.2 / +0.4 | 1, -13.8 / -2.2, +0 | -4.01 / -1.77 (noisy) | 1 | stops A220 -2, A320 -3, B737 -5, EJET -4 | OSM ref = SFO name |
| F15 | F15 | F15 | EL (B77W) | naip | adsb | +0.0 / -0.0 | 3, -21.9 / +0.9, -3 | +4.00 / -0.00 (noisy) | 2 | stops B737 -12 | OSM ref = SFO name |
| F16 | F16 | F16 | CL (B753) | osm+adsb | adsb | - | 3, -26.3 / -0.4, +0 | -4.70 / -17.74 | 1 | - | OSM ref = SFO name |
| F17 | F17 | F17 | CL (B753) | osm | adsb | - | 2, -19.5 / -1.2, +0 | - | 1 | stops B737 -13, A220 -6, A320 -7, CRJ -4, EJET -8 | OSM ref = SFO name |
| F18 | F18 | F18 | B (CRJ2) span_max 21.2 len_max 26.8 | osm | adsb | - | 2, -9.4 / -0.6, -2 | -1.54 / -4.55 (noisy) | 0 | - | OSM ref = SFO name |
| F19 | F19 | F19 | EL (B77W) span_max 64.8 len_max 73.9 | osm | adsb | - | 1, -18.6 / -1.5, +0 | -4.25 / -16.37 (noisy) | 1 | tight F20 types_ok A21N A319 A320 A321 B38M B39M B738 B739 B752 B753 B773 B77W CRJ9 E190 E195 stops A220 -4, A320 -6, B737 -7, CRJ -2, EJET -6 | OSM ref = SFO name |
| F20 | F20 | F20 | CL (B752) | osm | adsb | - | 2, -9.6 / -0.0, +0 | - | 1 | tight F19 types_ok A21N A320 A321 B38M B39M B3XM B738 B739 B752 B753 BCS3 E190 E195 | OSM ref = SFO name |
| F21 | F21 | F21 | CL (B752) | osm | adsb | - | 5, -22.7 / +0.2, +0 | - | 1 | stops B737 -13, A220 -4, A320 -5, CRJ -0, EJET -6 | OSM ref = SFO name |
| F22 | F22 | F22 | EL (B77W) | osm | paint+adsb | - | 4, -16.6 / +0.3, -1 | -0.50 / -0.65 | 2 | - | OSM ref = SFO name |
| G1 | G1 | G1 | E (B772) | osm+naip_axis+adsb | adsb | -0.4 / +1.8 | 4, -13.2 / +0.9, -1 | - | 2 | - | OSM ref = SFO name |
| G2 | G2 | G2 | EL (B77W) span_max 64.8 len_max 73.9 | osm | paint | - | - | +0.05 / +0.56 | 2 | - | OSM ref = SFO name |
| G3 | G3 | G3 | E (B772) | osm | naip+adsb | -1.0 / +0.3 | 1, -15.1 / +0.5, -1 | -2.69 / +5.48 (noisy) | 2 | - | OSM ref = SFO name |
| G4 | G4 | G4 | E (B772) | osm | naip+adsb | -0.4 / +0.2 | 1, -12.3 / +0.1, +2 | - | 2 | - | OSM ref = SFO name |
| G5 | G5 | G5 | EL (B77W) span_max 64.8 len_max 73.9 | osm | paint+adsb | - | 1, -14.9 / +0.4, - | +0.57 / +0.70 | 2 | - | OSM ref = SFO name |
| G6 | G6 | G6 | EL (B77W) | osm | naip+adsb | +0.8 / +0.1 | 1, -13.4 / -0.3, +0 | - | 2 | - | OSM ref = SFO name |
| G7 | G7 | G7 | EL (B77W) | osm | adsb | +2.6 / -0.3 | 4, -10.4 / -0.9, -1 | - | 2 | stops A320 -28 | OSM ref = SFO name |
| G8 | G8 | G8 | EL (B77W) | osm | naip | +0.1 / -0.3 | 1, -9.6 / -1.9, +2 | - | 2 | - | OSM ref = SFO name |
| G9 | G9 | G9 | EL (B77W) | osm | adsb | +3.6 / -0.1 | 2, -15.3 / +0.7, -0 | - | 2 | - | OSM ref = SFO name |
| G10 | G10 | G10 | EL (B77W) | osm+naip+adsb | adsb | -0.1 / n/m | 2, -12.9 / +0.8, -2 | -2.23 / -21.04 (noisy) | 2 | - | OSM ref = SFO name |
| G12 | G12 | G12S | E (B789) | osm | - | +2.1 / -0.9 | - | +5.02 / +6.90 (noisy) | 2 | - | AODB G12S (UA900 B789 plan, 24 Sep) = SFO Museum gate point G12S on the OSM "G11" lead-in (4.5 m behind the nose); gates G11 / G12 (DataSF) share this hold room |
| G13 | G13 | G13S | F (A388) | osm | adsb | +1.6 / +1.0 | 2, -17.6 / +1.0, -2 | - | 3 | - | OSM G13 lead-in at the three-bridge G13-G14 hold room (AODB G13S takes A388/B748/B77W) |
<!--END:stands-->

Remote stands with SFO names (ADS-B parked stays with an SFO remote-stand window, snapped to the nearest OSM parking
position within 25 m):

<!--BEGIN:remote-->
| remote stand | position | pos_src | ADS-B aircraft | OSM residual |
|---|---|---|---|---|
| 2-2A | (-1522.0, 650.4) hdg 334.64 | osm | C-GYLY BCS3 ACA759 | 3.8 m |
| 41-22 | (-1347.3, -392.6) hdg 70.3 | adsb | N78002 B772 UAL3932 | no OSM parking position within 25 m (nearest 157 m) |
<!--END:remote-->

## 8. Fields added to data/sfo_stands.json (backward compatible)

Existing fields keep their meaning: `name` (unique stand id = the gate number as signed, e.g. `A1`, `E10`, `G13`; only
the four alternative positions keep their AODB name `B5S`, `B11S`, `B16S`, `C9V` because they share the gate of their
base stand - review round 1 restored this; before it `name` had become the AODB name), `alias`,
`letter`, `nose` (world x, z of the nose tip of the class reference aircraft), `hdg` (true), `cls`, `src`
(obs/inf), `bridges[]` {`gate`, `attach`, `door`}, `redBoxes`, `remote[]` {`name`, `x`, `z`}.

| Field | Where | Meaning |
|---|---|---|
| `licence`, `sources` | top | ODbL notice; source versions |
| `gate` | stand | the gate number to display (base of a suffixed AODB name: `B5S` -> `B5`, `E10U` -> `E10`) |
| `aodb` | stand | SFO AODB stand names seen for this position (empty when only DataSF/maps name it) |
| `excl` | stand | stands that must not be occupied at the same time as this one (alternative positions and physically overlapping pairs). A matcher should skip a stand while any stand in its `excl` is occupied. |
| `alt_of` | stand | this position is an alternative (usually wide-body) stop of stand `alt_of`; both share bridges |
| `span_max`, `len_max` | stand | per-stand wingspan / length limits (m) where the class envelope is too coarse (largest types SFO parks there); `js/live/airport.js` standGates applies them to `maxSpan` / `maxLen` |
| `obs_types` | stand | the types SFO planned / ADS-B saw on the stand (the basis of the class and the limits) |
| `tight_with` | stand | neighbours only clear with the limits (< 3 m, no overlap; SFO plans both at once) |
| `a380`, `a380_stands` (top) | stand | the stands that may take an A380 / 747-8 (class F) |
| `leadin` | stand | the painted lead-in polyline (oriented OSM way, moved with the stand when the paint corrected it) |
| `resid.paint` | stand | painted lead-in fit (`n`, `lat_nose`, `lat_m20`, `dh`, `rms`) |
| `cab_pose`, `cab_door_dist`, `stow`, `stow_turn_deg`, `stow_len`, `rotunda_max_r`, `rotunda_osm`, `rotunda_src` | bridge | §4 (review round 1) |
| `pos_src` | stand | `osm` / `naip` / `adsb` (where the position comes from) |
| `name_src` | stand | `sfo` for all contact stands |
| `verified_by` | stand | `naip`, `adsb` (§3.4) |
| `cls_src`, `largest_type` | stand | how the class was set; the largest type seen |
| `osm_id` | stand | the OSM way used |
| `resid` | stand | `{naip: {resid_along, resid_lat}, adsb: {n_aircraft, along_med, lat_med, dhdg_med}, osm}` residuals in the stand frame (m, deg) |
| `rotunda`, `cab`, `walk`, `osm_id`, `assoc` | bridge | §4 |
| `bridges_upper` | stand | third (A380 upper-deck) bridges, `door: 3`; not in `bridges` because the app cannot dock them yet |
| `types_ok` | stand | review round 2: whitelist of ICAO designators where the class limits alone let a simultaneously planned neighbour come within 3 m (E10, E12, F19, F20): the types SFO / ADS-B put there |
| `type_stops` | stand | review round 2: `{FAMILY: {along, n, src}}` - ADS-B shows that family stopping `along` m (negative) short of the stand nose (geom.py FAMILY) |
| `conflict` | stand | review round 2: ADS-B aircraft with SFO's stand window more than 3 m / 10 deg off the axis (`n_aircraft`, `lat_med`, `dhdg_med`, aircraft); `verified_by` is then empty and `verified_unconfirmed` keeps what would have verified it |
| `resid.naip` | stand | relief-corrected (review round 2); `resid_lat` null where the fuselage centre was not measured |
| `geom_src`, `rotunda_twin_of` | bridge | review round 2: provenance of the bridge geometry (OSM, not NAIP-verified); the other rotunda of a twin head (F15, G11) |
| `shares_bridges_of` | stand | an alternative position without bridges of its own uses the bridges of this stand |
| `hdg`, `pos_src`, `name_src`, `verified_by`, `osm_id` | remote | parked heading and provenance of SFO-named remote stands |
| `positions` | top | unnamed OSM parking positions (remote apron, cargo, maintenance, GA; `zone`: apron / north / west / contact-unused) with stop point and heading - candidates for parking aircraft that match no named stand (no SFO name, positions from OSM only, not verified) |
| `conflict_along` | stand | review round 3: the relief-corrected NAIP nose is > 1.5 m from the model nose (`resid_along`, `note`, `imaged`, `explained_by` when an ADS-B + NAIP family stop explains it); the stop point is then not verified |
| `resid.naip.imaged` / `naip.imaged` | stand | review round 3: what NAIP shows on a wide-body stand with an along conflict (engines, length, candidate types; not identified) |
| `name_note` | stand | review round 3: provenance of a name that rests on DataSF gate numbers only |
| `model`, `model_src`, `ext_range`, `dock_types_out`, `cab_turn_deg`, `cab_option`, `tunnel_end` | bridge | review round 3: the bridge's datasheet model and its operational range rotunda -> cab pivot (inferred); accepted types it cannot reach; signed cab turn of the observed dockings; end of the parked tunnel where the OSM way ends with a cab stub |
| `walk` | bridge | since review round 3 always ends at the rotunda |
| `cab_convention`, `bridge_models` | top | review round 3: the cab-rotation sense used for `cab_turn_deg` (inferred) and the model table (Oshkosh sell sheet) |
| `cls`, `obs_types`, `pave`, `pave_outside_apron` | remote | review round 3: class and types of a remote stand, its paved area (class envelope + 3 m clipped to the OSM apron) |
| `unplaced` | top | review round 3: SFO stand names (AODB / SFO Museum) without a position in this file, with their evidence |
| `redBoxes` [x, z, side, angle] | top | review round 3: side = the painted line's centre square and angle (deg, x east / z south) from an oriented-square template fit (was the colour component's outer rectangle; the angle was unused) |

`js/live/airport.js` `standGates` passes `gate`, `excl`, `altOf`, `aodb`, `a380`, `tightWith`, `leadinW`, bridge
`rotundaW` / `walkW` / `cabW` / `cabPose` / `stowW` / `rotundaMaxR` through and applies `span_max` / `len_max`;
`js/live/markings.js` paints the lead-in polyline. The bridge fields need gates.js changes
(docs/requests/static_geometry_round1.md, round2.md, round3.md). Since review round 3 `standGates` also passes
`tunnelEndW`, `extRange`, `model`, `dockTypesOut`, `cabTurnDeg`, `cabOption`, `stowLen`, `rotundaSrc`, and remote stands
carry `cls` / `paveW`.

## 9. Licences

`data/sfo_stands.json` now contains OSM-derived positions of more than 100 features (stands, bridges, positions), so
it is a Derivative Database under ODbL 1.0 and is offered under ODbL (notice in the file and `docs/ATTRIBUTION.md`).
It no longer contains anything measured on the Google screenshots (which could not be relicensed; stands_xcheck.md
§7), so the share-alike condition can be met. NAIP measurements (public domain), SFO names and our ADS-B observations
can be combined with it. The app must show the OSM attribution (request for the UI owner).

## 10. Remaining doubts

- Review round 3 (§13): the app still draws its own bridges (request round 3 §1), so the renders do not show the data
  bridges; 7 DATA ISSUES remain as evidence conflicts (F5, A1 / A2 L2 787-10, G7 A319 stop, A10 graze); 16 stands have a
  NAIP stop-point conflict (`conflict_along`); bridge models, the cab-rotation sense and the facade rotundas are inferred.
- The AirTrain guideway polygon overlaps several elevated walkway parts and the T1 / ITB halls in plan (the ITB station
  is inside the building; the others are crossings whose real levels are not known); heights are approximate.

- Review round 2 (see §12): the app does not yet use the data bridges, `types_ok`, `type_stops` or the `a380` flag, so
  what the owner sees still differs from what is checked here (30 APP ISSUES). The drawing workflow's audit could not
  be re-run this round: `jobs/extract2d.mjs` fails on the current `js/live/gates.js` ("Duplicate export of 'doorOf'";
  both files belong to other workflows).
- A2 L2: the 787-10 door 2 is 1.0 m beyond the longest apron-drive bridge (42.4 m vs 41.381 m); either the stop for that
  type is further forward or the bridge is a longer unit - not resolved.
- The relief fit assumes the OSM / paint lines are unbiased on average; k varies across NAIP frames (the Super Bay
  Hangar leans the other way), so the per-stand correction is good to ~0.7 m rms near the terminals only.
- `type_stops` rest on one or two ADS-B stays per stand; the along reference per family (antenna behind the nose) is
  itself a median over stands.

- C9V's lead-in and A4T's identity are inferred (no ADS-B on them yet); G13R and G14T are not modelled.
- F18 and F10 have no bridge (see §4); F15 is placed on one imaged wide body.
- **F5** (open issue in `check_stands.py`): its OSM rotunda is 6.4-6.9 m from the L1 door of the types SFO parks there,
  shorter than the smallest apron-drive bridge retracts (9.846 m), and its walkway gives no feasible point further back.
  Either the stop (OSM lead-in end, no NAIP / ADS-B evidence) is ~3.5 m too close to the building or the bridge is a
  special short unit - not resolved; needs an aircraft on F5 in imagery or ADS-B.
- The G pier: no painted lead-in is visible in NAIP 2024 at any G stand (covered by aircraft or faded), and the NAIP
  aircraft at G1 (-5.2 m), G9 (-2.4 m) sit off their OSM lines, so G1, G3, G4, G9 are `src: inf`. The 2022 NAIP frame
  (`refs/cache/naip/items_2022`) was not read this round.
- E10/E12 and F19/F20 are tight pairs (0.4 m / 1.9 m, §5); E12's only ADS-B aircraft (B753) stopped ~18 m short of the
  model nose, which supports per-type stop points (request to traffic.js).
- The drawing workflow's audit of the running app (fresh extraction 24 Sep ~18:15 UTC, scratch output) still reports,
  with the app's own `TYPES` table, E10/E12 overlapping 2.3 m2 and F19/F20 1.6 m2 (the envelopes here use the ACAP
  dimensions and clear by 0.4 / 1.9 m), and rest-pose bridge collisions that come from gates.js deriving its own
  rest poses (it does not read `stow` yet).
- NAIP (May 2024) predates some OSM edits; three NAIP aircraft sit 3.7-8 m off their OSM lines laterally (G1, G13S,
  F15) and ADS-B shows heading offsets of 12-24° at D3, D4, D9 (one Southwest/United aircraft each; the NAIP aircraft at
  D3/D4 sit on the lines) - not resolved.
- Remote stands: only those SFO allocated while the recorder ran (daytime coverage from 15:13 UTC) have positions.
- Classes follow one day of AODB data; rarer larger types will raise some classes.

## 14. Review round 4 (26 Sep 2026): what changed here

Resumed after the usage-limit interruption; the WIP of 767b56d was superseded by the committed state (HEAD 5e09706), which
was re-checked. Pipeline re-run: `adsb_parked.py` (recording now to 25 Sep 23:57 UTC, 14 flysfo snapshots: 997 stays
with an SFO stand window, was 730) -> `build_stands.py` -> `check_stands.py` -> `report.py`; `build_airfield_details.py`;
`build_terminal_parts.py`; `tools/sat/check.py` / `check_bridges.py` (5 ISSUES: F5 x3, G7 A319, A10 graze); the
offline xcheck steps (Overpass unreachable: 504 / reset, cached OSM used); the 2-D drawing audit (`tools/drawing/audit.py`)
on a scratch copy of the working tree with HEAD's `js/live/gates.js` - the bridges workflow's uncommitted gates.js
breaks `jobs/extract2d.mjs` ("reading 'toFixed'", its request `docs/requests/bridges_tools.md`). With HEAD's gates.js the
audit still shows that renderer's own bridges (20 envelope-rest-bridge collisions, 17 bridge-bridge, 3 bridge-mast:
request §1); its only envelope-envelope COLLISION is F19 B77L x F20 B736 = the SFO-path case of request §2.

| finding (severity) | change | evidence now |
|---|---|---|
| rendered bridges are not the data bridges (critical x2) | not my file: `docs/requests/static_geometry_round4.md` §1 (escalated); §1 of this file no longer calls the rendered bridges "OSM-traced" | data: 0 bridge overlap issues |
| F17 / F19 / F21 L1 rest pose on its own walkway, swing 137-163 deg (critical) | stow search (build_stands.py): own fixed walkway is an obstacle; **neutral-axis-free swing test** - rest + every docked direction within one 175 deg arc (Oshkosh: 87.5 cw / 87.5 ccw of the centreline) and never through the walkway direction (+-25 deg); docked-sibling spacing 1.0 m (F15 had 0.40) | every bridge: arc of all poses <= 54 deg; F17 L1 rest 125 deg from the walkway, 48 deg arc; check_stands: 0 rest-on-walkway, 0 swing issues |
| rotunda in the wing sweep of accepted types (F17 / F19 / F21) (critical) | **inferred per-family stops** where wings / engines / tailplane of a family (class-limited, i.e. SFO's path) came within `geom.fixed_clear` of a fixed walkway / rotunda (code A-C: ICAO 3.0 / 4.5 m; D-F: 3.0 m, see §5 relief): the smallest shift short (0.5 m steps), never more than 2 m beyond an ADS-B stay of that family; src "inferred: clearance ..." | F17 A320 -7.0 / EJET -8.0 / A220 -6.0 / CRJ -3.5 (B737 -13.2 ADS-B); F19 B737 -7.0, A320 -5.5, EJET -6.5 ...; F21 A320 -5.0, EJET -6.5 (B737 -13.4 ADS-B); F12 / F14 / F11 / F13 / F5 1-5 m. check (g): no fixed part within ICAO of a code-C wing; D-F 3.5-5.7 m (757 at F14 / F17 / F21, 767 at F19) are WARNs (VDGS relief unverified) |
| swing limit dismissed as "neutral axis unknown" (major) | the arc test above is the ISSUE criterion; the walkway-relative figure is one NOTE per bridge | 17 bridges > 87.5 deg from the walkway (F12-F22 112-138 deg): both the imaged parked tunnels (79-95 deg) and SFO's dockings lie beyond 87.5 deg there, so the walkway is not the centreline (a side-entry rotunda - inferred, not sourced) |
| rest poses 1-4.5 m from observed wings (major) | stow keeps the ICAO clearance to the wings / engines / tailplane of every OBSERVED type within 150 m, relaxed to 3.0 / 1.0 m only where no pose exists; then listed (`stow_clear_m`, `stow_note`, check WARN) | 124 of 128 main-deck rest poses clear by ICAO; F14 L1 3.2, F17 L1 1.0, F19 L1 3.3, F21 L1 3.0 m (757 wings; evidence conflicts - the imaged parked tunnels lie inside our accepted envelopes there) |
| G1 axis offset / rotated (major) | **NAIP fuselage-axis fit** (`tools/stands/naip_axis.py`, relief-corrected line fit of the fuselage band 4-45 m behind the nose) applied when ADS-B heading agrees (>= 2 aircraft, within 2.5 deg): G1 NAIP -4.12 m at the nose / -7.6 deg (rms 0.21 m, 94 rows), ADS-B 4 aircraft -9.0 deg -> nose moved -4.1 m lateral, heading 207.44 -> 199.13 | after: NAIP axis +0.25 m / +0.9 deg; the review's own fit was -3.6 m / -7.8 deg |
| G12 axis (major) | one image only (NAIP -0.1 m at the nose, -2.1 m 30 m aft, +3.8 deg; no ADS-B, no paint): `conflict_axis`, src inf, not moved - at G5 the NAIP aircraft stands 7.8 deg off an axis that paint AND ADS-B confirm, so a lone NAIP aircraft is no proof | flagged |
| stop points (A10, D11, F13, G10) (major) | stop moved where NAIP and ADS-B (>= 2 aircraft, family-corrected, within 1.5 m of each other) agree within 2 m: **G10 -2.7 m** (NAIP -2.8, two B789 -2.7 / -1.4); ADS-B types now fall back to SFO's planned type when the feed's type is not an aircraft type (Air Canada A220s were 'AS50' / 'GLID' / 'AS55'), which also re-bases the A220 antenna reference (-5.9 m from 7 stays -> -15.0 m with them) | A10, F13: NAIP only (no ADS-B stay near them in two days), kept `conflict_along`; D11: three A220s stop at the model nose (0 m vs the family reference) while the NAIP aircraft (type unknown) reads -6.7 m: kept `conflict_along`, not moved |
| pairs below ICAO, 3.4.4(b) wording (major) | §5 wording corrected (D-F relief with VDGS exists; none for C). Pair logic targets the ICAO clearance on SFO's path (class limits): span/len limits kept only if they help; **analog stops** (a family without a stop takes the ADS-B stop of a same-code family on that stand) - E12: A320 / A220 / E-Jet at the B737 stop -17.5 m | E10/E12 4.2 -> 4.5 m (code C met; 7.5 only through the 757 at E12); F21/F22 3.3 m, F19/F20 4.3 m (types_ok) remain listed (§5) |
| types_ok bypass on SFO's path; stale APP model in the checker (major) | checker APP view = current standFits (no types_ok on SFO's path, a380 flag, per-family stops; stop-short is resolved at runtime by `shortBlocked`); data flag `types_ok_all_paths` (F19, F20) + request §2 | APP ISSUES 33 -> 1 (F19/F20 1.9 m) |
| bridge reach (major) | `bridge_models.note`: per-bridge models are an Oshkosh-only inference; beyond 41.4 m but within TK's 14-50 m -> WARN "manufacturer-dependent" (A1 / A2 L2) | ISSUES: F5 (7.2-7.5 m, below every published unit; E-Jets stop at the nose per ADS-B - unresolved), G7 L1 (A319 ADS-B stop -27.7 m, n = 1), A10 graze |
| masts vs rendered bridges (major) | covered by request §1; data stow: no mast within 0.8 m of any bridge (check_stands masts: 0 issues) | - |
| alternative positions without bridges in the app (critical) | `standGates()` (airport.js): `sharedBridges` / `sharedFrom` on B5S / B16S / C9V, `altGates` on the base; request §1 | data rest poses clear the alternative positions' aircraft |
| taxiway T end across the shoulder (major) | `build_airfield_details.py` PAINT_REROUTES: OSM 23718429 cut at x -470, traced on the paint straight to the runway (84/84 samples with paint), the way beyond the runway kept (its hold stays) | independent Lab b* check: longest run > 1.5 m 44 m -> 0 |
| taxiway D curve 1.4-2.3 m off (minor) | window correction fits a local line (the paint curving away from the OSM way), plus a second pass on the corrected line | centreline 23: run > 1.5 m 22 m -> 0 m |
| edge runs 1.5-2.8 m off (minor) | edges: local-line windows, passes 2-4 on the snapped run, no measurement within 7 m of a hold bar (the ladder pulled runs 143 / 242 / 302) with the run drawn straight across, runs with < 30 % paint and > 1 m off dropped (6) | generator: > 1.5 m 2.2 % -> 1.0 %; independent b* check (noisier than the review's): runs >= 6 m over 1.5 m 43 -> 20 lines |
| centrelines drawn without paint (minor) | `centerlineMeta[i].drawn = false` when paint is in < 25 % of the samples or naip_unverified; markings.js skips them (they stay for routing) | 19 lines not drawn |
| stop bars without a source (minor) | markings.js no longer draws nose-gear stop bars | - |
| B5 lead-in corner (minor) | NOT fixed: an automatic lead-in snap was tried and rejected (it pulled G10's end onto the aircraft and B26's start onto the taxiway edge); B5's corner lies on faint paint on white concrete (contrast < 10) | open |
| bridge lean (minor) | stated in `geom_src` / `bridge_geom_note` (not corrected) | - |
| terminal footprints T1 / T3 / BA D (major) | NOT trimmed: listed in `footprint_accuracy.known_misfits` with the review's figures (T1 north x -1000..-840, T3 landside, BA D corner, unconfirmed IT / T3 S / BA E medians); an automated facade detector was tried and is unreliable next to the AirTrain / teal roofs | open |
| threshold bar (minor) | shader not mine: request §3 | - |

## 13. Review round 3 (25 Sep 2026): what changed here

Resumed from the partial work of the interrupted run (git a8e0538); every item below was re-checked, the data were
regenerated (`adsb_parked.py` -> `build_stands.py` -> `redboxes_naip.py` -> `build_stands.py` -> `check_stands.py` ->
`report.py`; `build_airfield_details.py`; `build_terminal_parts.py`) and the builder is deterministic (two runs, same
file).

| finding (severity) | change | evidence now |
|---|---|---|
| app draws its own bridges (critical x2) | not my file: `docs/requests/static_geometry_round3.md` §1 restates round-2 #1-#5 with the new fields; `standGates()` passes `tunnelEndW`, `extRange`, `model`, `dockTypesOut`, `cabTurnDeg`, `cabOption`, `stowLen`, `rotundaSrc` | data side: 0 DATA ISSUES about bridge overlaps (below) |
| sibling L1 docked through L2 at rest: F15, G7, G13 (critical) | stow search avoids every other bridge's DOCKED footprints (a sibling for the types this bridge does not dock, other stands' bridges for all their types); rest poses >= 1 m apart; check_stands tests docked-vs-rest for siblings and neighbours, and L1/L2 docked to the same type | 0 issues |
| 20 bridges with rotunda = null; cab-stub ways (major x2) | rotunda rule: a final segment < 7.5 m after one >= 8 m is the cab stub -> rotunda = the node before the tunnel, `tunnel_end` = the stub's start (13 bridges: C4, C5, C7, C9, C11, D16, E4 ...); two-node ways starting on the facade (NAIP: tube from the facade, no corridor) -> drum 3.0 m out (13, inferred); F22 L1 (way starts 15.4 m off the building) -> rotunda there, walkway from the facade (inferred). `walk` now always ends at the rotunda; the extension is checked for every bridge | rotunda null 0 of 128; `rotunda_src` on every bridge; D-pier rest poses lie on the imaged parked tunnels (`refs/cache/stands/view/dpier.png`) |
| one range 9.846-41.381 m for every bridge (major) | one datasheet model per bridge (`model`, `ext_range`, inferred: the smallest-retracting model covering the observed dockings); rest length >= its retraction; `dock_types_out`; stands whose dockings fit no model are listed | ISSUES: A1 / A2 L2 (787-10, 42.4-43.7 m > 41.4), F5 L1 (7.1 m < 9.8), G7 L1 (A319 at the ADS-B stop 27.5 m short, 36.3 m > 17.0) |
| cab turn |angle| only (minor) | signed test 92.5 cw / 32.5 ccw; sense inferred from the fit (`cab_convention`: 504 of 531 observed dockings fit counter-clockwise-as-cw); `cab_option` | F12, F14, F17, F19, F21 L1 need the optional 185 deg cab (inferred) |
| no engines in the planform (minor) | `dump_types.mjs` exports `eng` / `rear`; `geom.planform` adds the nacelles | rest / fixed checks include engines |
| stop points along the axis (major) | `conflict_along` when the relief-corrected NAIP nose is > 1.5 m from the model nose; such a stand is never `verified_by naip` and never `src obs`; a per-family stop that ADS-B (n >= 2, within 1.5 m of each other) and NAIP agree on explains it (B22: three E-Jets 4.3-5.4 m short, NAIP -4.1 m -> `type_stops.EJET = -4.3`); wide stands record what NAIP shows (`naip.imaged`: engine count, length, candidate types - not identified) | 16 stands with `conflict_along`, 1 explained; C11's reading re-read: the -14 m had taken the white aft fuselage for the nose (grey forward fuselage; engines ~-11 m, tail ~-37.5 m -> nose ~-3..0 m, flagged `u`, not used) |
| winglets (major) | `geom.WINGLET_SPAN` (Boeing airport FAQ, read in `refs/cache/boeing3v/wingletspans.pdf`: 757-200/-300 41.1 m, 767-300ER 50.9 m) for B752 / B753 / B763 (B75W / B76W aliases); class CL = 41.1 m / 54.5 m (also `js/live/airport.js` CLASS_MAX) | 9 CL stands; F21/F22 3.3 m, F19/F20 4.3 m (§5). Per-airframe fit not verified: request types.js (§3 of the request) |
| B11S / F15 classes, `types_ok` too narrow (major) | classes from every version of every flight in all 11 snapshots (a re-plan had removed types); `types_ok` = observed types + every type whose planform (engines incl.) lies inside their envelope | B11S EL (TAP A339), F15 EL (B77W); E12 / F19 / F20 whitelists include the smaller types |
| G11 / G12 identity (major) | the wide-body stand at the G11-G12 hold room is SFO's G12S (AODB UA900 B789 24 Sep; SFO Museum gate point G12S on the OSM "G11" line, 4.5 m behind the nose) -> stand `G12` (aodb G12S, alias G11); SFO Museum G11R / G12T / G12V and AODB G13R / G14T are listed in `unplaced` with their evidence (no lead-in, heading or stop known) | name `G12`; class from the B789 |
| G103-G105 and 26 remote codes dropped silently (major) | `unplaced`: every AODB stand name without a position here (turns, types, first / last window, SFO Museum reference point where one exists, reason) | 38 entries (G102-G105, 2-1 ... 41-22, G11R, G12T, G12V, G13R, G14T) |
| 2-2A 40 m disc across the perimeter wall (major) | remote stands carry `cls` (largest SFO / ADS-B type) and `pave` = the class envelope + 3 m clipped to the OSM airside apron; airport.js paves only that | 2-2A: class C (BCS3), 0 m2 of the envelope outside the apron |
| red boxes off-centre (minor) | every box re-fitted with an oriented hollow-square template (full 0-90 deg, side 2.5-7.5 m, centre +-1.5 m; the component rectangle's angle had been 45 deg off on several boxes); boxes whose best template score < 8 are rejected; js/live/markings.js now draws each box at its angle (it had drawn all grid-aligned) and the side as the paint line's centre | 255 boxes; the review's centroid test: median 0.35 -> 0.33 m, > 1.5 m 14 -> 6 (the rest are double boxes / vehicles in the window); `refs/cache/stands/redboxes_naip.json` keeps `boxes_component` |
| pairs below ICAO (minor) | kept, with SFO's own simultaneous planning as the evidence (§5) | §5 |
| small building overlaps (minor) | docked tunnel inside the building is checked for every docking; a graze < 1.5 m2 within 4 m of the rotunda is a NOTE (outline accuracy +-5 m) | A10 L1 (0.9 m2, 3-6 m from the rotunda along the facade) stays an ISSUE |

Static geometry in the same round:
- **Masts** (critical): `data/sfo_details.json` masts = the 70 OSM floodlight masts (`man_made=mast`, `tower:type=lighting`,
  ODbL; all 70 viewed on NAIP contact sheets: bases with shadows on the airfield and landside, leaning poles over the
  roofs at the terminal). 8 that lay on / inside the rendered building outline were moved 0.2-1.6 m out to 1.5 m clearance
  (`mastMeta.moved`, inferred). None is within 51 m of a taxiway centreline or inside any stand's accepted-type envelope
  (check_stands: 0 issues, 0 warnings); js/live/world.js draws all of them (it had dropped 11). Height not in OSM
  (`MAST_H` in js/live/items.js inferred).
- **Snapshot patches** (critical): removed; the NAIP pavement covers patch sites 0-2 (100 / 100 / 92 %), sites 3-4 on the
  infield stay grass. The two snapshot aircraft there (UAL643, SKW6001) are 38 / 49 m from any pavement - an ADS-B /
  engine matter (request §4).
- **Taxiway edges** (major): the SFO Museum outline runs are snapped onto the painted double line (NAIP yellow ridge
  every 2 m, consistent windows only); 27 runs without paint dropped. Independent check (Lab b* peak, the review's
  method): median 0.05 m, 12 of 360 lines > 1.5 m (0.7 km of 40.4 km, all with 3-15 paint samples); before: 0.95 m,
  20.6 km over 1.5 m.
- **Centrelines** (minor): OSM 1096199967 corrected with a smooth fit (2.06 -> 0.06 m); OSM 155702566 and 7 other lines with
  paint in < 25 % of the samples are `naip_unverified`. Independent check: median 0.15 m, 6 lines > 1.5 m (all flagged or
  weak paint).
- **Approach-light structures** (major): 28L / 28R piers from NAIP (`js/geo.js` APPROACH_STRUCTURES, `tools/imagery/
  als_naip.py`): continuous catwalk from the seawall, a station every 100 ft (28L 700-2500 ft; 28R 692-2492 ft), the
  imaged crossbars (28L 1000 / 1300 ft +-13 / +-16 m; 28R 692-1292 ft +-16.5..19.7 m) and huts; checked on the strip
  panels `refs/cache/als/28?_panels.jpg`. The light pattern stays the FAA standard (inferred), snapped onto the imaged
  stations; the 1000-ft crossbar lights stop at the FAA 50 ft. Lights on the displaced runway / blast pad / EMAS are
  inset (at the surface, no post; they had floated 1.4 m up), lights on open ground stand on posts.
- **Buildings** (minor): not verifiable to better than ~5 m on NAIP; NAIP 2022 has the same east lean (imagery.md §6), so
  it is no second view. `data/sfo_buildings.json` `footprint_accuracy` = inferred +-5 m with the known misfits (BA D SSE
  face, BA A east face, the T1 hall's bulge over the departures roadway / AirTrain guideway).
- **Shoreline** (found in this round's own render check): the terrain's airport landfill was the 16-vertex
  `AIRPORT_LAND_ST` polygon, 44 m out in the Bay at the 28 ends (the NAIP catwalks started on rendered land) and with the
  north basin as land (100 ha of water inside it). `tools/imagery/shore_naip.py` classifies NAIP 2024 NIR / NDWI on a 2 m
  grid (water: NDWI > 0.25 and NIR < 90 or NIR < 0.65 R on 10 m box-filtered bands - sun glint; Bay 0.31-0.89, pavement
  0.07-0.20; thin catwalk connections cut) -> `data/sfo_shore.js` (one 1687-vertex land ring over the NAIP coverage, airport
  + mainland; checked by eye on NAIP along the whole Bay side and by sampling the app's terrain against NAIP);
  `js/world/terrain.js` takes land / water from it inside the NAIP coverage (4.8 x 5 km; the regional Bay polygon had also
  put part of the Burlingame shore under water); `AIRPORT_LAND_ST` (the shaders'
  16-vertex area / foam mask) is refitted to it (IoU 0.83 -> 0.98; Bay side median 11 m, max 143 m: 16 vertices cannot
  follow the curved shores - request for a shoreline texture in the foam bake).
- **Signs on movement surfaces** (this round's 2-D audit of the app, `out/draw/audit.json`: 25 hold / distance-remaining
  signs stood 0.1-17 m inside SFO Museum taxiway or runway polygons): `js/live/signs.js` now places every sign where its
  footprint + 1 m is off those polygons - hold signs at the usual 11 m beyond the painted bar end or the nearest clear
  distance 5-30 m (8 moved, 3 with no clear spot not drawn), distance-remaining signs shifted along the runway / to the other
  side (8 moved). Sign positions stay inferred (FAA layout), not surveyed.
- **Threshold bar** (major): `js/shaders/ground.js` is not mine - request §2 (bar on the landing side at all 8 ends).

Rejected / not done, with the evidence:
- **G13 walkways "not on any imaged structure"**: rejected. NAIP (`refs/cache/stands/view/g13raw.png`, 0.06 m/px,
  relief in mind) shows the fixed walkway from the G13-G14 hold room running NW, three parallel tunnels to the WSW and a
  short corridor down to the southern tunnel; the data walk follows the corridor and the three rest poses lie on the
  imaged tubes, ~2-3 m west of the leaning roofs. Doubt: the L1 rotunda may sit up to ~6 m further along its tube.
- **Moving narrow-body stop points onto NAIP** (D11 -6.7, D16 -4.2, B8 -2.5, D3 -2.0, B2 -1.9, C5 +4.6, F7 +2.0 m): not
  done - one image of one aircraft against the OSM stop; where ADS-B exists it disagrees (B8 +1.7, C5 -2.4, D5 +0.3 m
  relative to the family norm). Recorded as `conflict_along`, not verified.
- **Wide-body parked types**: dimensions and candidates recorded (`naip.imaged`), no registration visible, so no type
  stop is derived from them.
- **Second-epoch building check**: NAIP 2022 leans the same way; a true orthophoto (San Mateo County 2022, licence
  unclear) would be needed.

## 12. Review round 2 (24 Sep 2026): what changed here

| finding (severity) | change | evidence now |
|---|---|---|
| NAIP relief: F15 placed on a leaning image; NAIP_OBS lateral 0.0 wrong; 'relief ~1 m' (major x2) | `naip_relief.py`: fuselage centres measured numerically, lean fitted (k = 0.54 +- 0.04 m/m, 0.70 m rms, 25 stands); along readings corrected; calibration +1.2 / +3.3 m; F15 on the corrected reading; `naip` verification only from measured, corrected centres (accuracy ~+-1.5 m), never circular | F15 ADS-B lateral 0.9 m (was 3.1 m); verified_by naip 21 stands |
| red boxes: ~20 % false positives (major) | `redboxes_naip.py` filter: painted outline on the perimeter, grey concrete ring, not coloured inside, hollow (not vehicles), not next to hold markings / within 15 m of a hold, within 200 m of a stand or OSM parking position | 257 boxes (was 309); rejected list with reasons in `refs/cache/stands/redboxes_naip.json`; montages `out/review/r2/redbox_rejected.jpg`, `redbox_kept_sample.jpg` (1-2 doubtful in 60) |
| bridges not NAIP-verifiable (minor) | `geom_src` on every bridge; stated in §1 / §4 | - |
| G5 ADS-B 1.8 m accepted at 3 m (minor) | `adsb` threshold 1.5 m | G5 now 0.4 m with more stays |
| gates.js ignores the data bridges; 767 L2 over the wing; bridges at rest in aircraft (critical x3) | not my files: `docs/requests/static_geometry_round2.md` (gates.js #1-#5); §1 says the rendered bridges are unverified | - |
| E10/E12, F19/F20 overlap with the app planforms (critical) | checker and builder on types.js planforms; `type_stops` (ADS-B per family); `types_ok` for pairs SFO plans together | E10/E12 4.2 m, F19/F20 5.1 m (DATA); 1.1 m in the APP view until traffic.js honours `typesOk` |
| A380 clause on EL stands / F19 (critical) | request traffic.js #1; the checker models the clause as APP ISSUES | 15 APP ISSUES from the clause (+ E10/E12 from the single stop point) |
| F16 / F17 noses at the facade (critical) | stands whose envelope comes within 2 m of the building move back to the ADS-B family stop when one exists (F16 16.9 m, F17 15.6 m; `pos_src osm+adsb`); nose-to-building < 2 m is an ISSUE, < 3.5 m a NOTE | F16 / F17 clear; closest now F12 2.4 m (NOTE) |
| checker used REF / class planforms, missed 7 app types (major) | `geom.py` reads `js/aircraft/types.js` (`dump_types.mjs`, re-dumped when types.js changes); all 48 designators; doors and dock2 from types.js; cab pivot on the door normal | - |
| rotunda swing (major) | check added: tunnel crossing its own walkway = ISSUE; > 87.5 deg from the walkway direction = NOTE only, because NAIP shows F-pier walkways running along the facade with the parked tunnels pointing away from it (the rotunda's neutral axis is not the walkway direction; `refs/cache/stands/view/F16F17osm.png`). Partly rejected: the "fold-back" reading assumed the neutral axis | no tunnel crosses its own walkway |
| pairs below 3 m / ICAO with app planforms (major) | pair logic on types.js geometry | §5 table: nothing below 3 m in the data; F7/F8 4.7 m (> 4.5 m) |
| app parks up to 25 m short (major) | checker: stop-short combinations as APP ISSUES; request traffic.js #4 | 14 APP ISSUES |
| F5 / F16 short retraction (major) | F16 moved back (above); F5 stays open (DATA ISSUE) | F5 L1 7.1-7.5 m |
| F15 / G11 twin rotundas (minor) | NAIP: one junction, two tunnels; `rotunda_twin_of` | - |
| cab pivot 3.0 vs 2.5 m (minor) | one constant `geom.PIVOT_TO_DOOR = 2.4 m` (12.224 - 9.846 m, sheet footnote), builder and checker | - |
| licence: adsb.fi in the ODbL file (major) | `adsb_parked.py` reads adsb.lol only, records `prov`; ATTRIBUTION.md updated | 624 stays, all `prov: adsblol` |
| src='obs' overstated for paint-only (major) | paint-only stands are `inf`; note in the data file rewritten | src obs 71 / inf 37 |
| D3 / D4 / D9 conflict (major) | `conflict` field, `verified_by` empty; NAIP 2024 (relief-corrected) puts the imaged aircraft on the D3 / D4 axes (0.5 / 0.2 m), so the 2026 ADS-B offset (three Southwest aircraft each, -5.0 m / +12 deg at D3, -2.3 m / +24 deg at D4) is unresolved: re-striping after May 2024 or a feed bias - not decided | D3, D4, D8, D9 flagged |
| B10 / B11 bridge assignment (major) | `BRIDGE_FORCE`: 1096422714 -> B11 (OSM ref + NAIP); 1096422712 -> B10, 1096422713 -> B11S by geometry (following the OSM refs would put B10's bridge on its right side: rejected) | - |
| F15 circular verification (major) | not `naip`-verified; ADS-B is the independent check | verified_by adsb |

Static geometry in the same round (`tools/build_airfield_details.py`, `tools/imagery/`, `js/live/world.js`; checked by
`python3 tools/imagery/check_markings.py`: centrelines median 0.15 m from the paint, 90 holds median 0.10 m / max 0.70 m):
12 holds added from the paint with OSM holding positions as locators (incl. ladders 100-125 m out, the T ladder pair,
the 2 ILS holds with their own marking pattern; the OSM node at (306, 189) has no paint and was rejected), the painted
E-W taxiway across 1L/1R that OSM lacks (traced on NAIP, named F1 by the SFO Museum polygon) with its 4 holds, hold
bars clipped to the painted length (holds 23 / 24 / 26 / 41 of the reviewed file: 3.5 / 8.5 / 4.0 / 2.0 m shorter; review measured 4.0 / 9.5 / 3.0 / 1.7 m), NAIP centreline corrections
above 1.5 m only when consistent over 24 m and smoothed (centreline 24's zig-zag gone; centreline 191 checked by eye and
left: it lies on the western of three painted curves, the 2.8 m offset was to the middle one -
`out/review/r2/cl191_check.png`), EMAS chevrons from the measured first apex with a 30.48 m pitch, and a 3 m pavement
band under every hold bar (`data/sfo_pavement.*`; 1.5 ha; the ladders' outer ends had lain on unpaved ground in the model).

Reproduce (order matters): `python3 tools/stands/adsb_parked.py; python3 tools/stands/naip_relief.py;
python3 tools/stands/build_stands.py; python3 tools/stands/redboxes_naip.py; python3 tools/stands/build_stands.py;
python3 tools/stands/check_stands.py; python3 tools/stands/report.py` (the red-box filter reads the stand positions, the
builder reads the boxes). `geom.py` re-dumps `js/aircraft/types.js` with node when it is newer than the cache.

Not changed (with evidence): the SFO Museum hangar offset (building outlines are not generated from NAIP; a lean-free
check needs a true orthophoto or wall-base measurement, see imagery.md §6 - open).

## 11. Review round 1 (24 Sep 2026): what changed here

| finding | change | evidence now |
|---|---|---|
| C11 / D14 classes raised by far-away ADS-B stays | ADS-B types only from accepted stays whose type agrees with SFO's planned type | C11 C (BCS3), D14 C (B39M); the C9V/C11 pair stays exclusive (C9V is the 767 alternative) |
| D14 3.1 m, C4 1.7 m off the painted lead-in | numeric paint fit, applied when clean (§3.3a) | after correction both within 0.01 m of the paint |
| NAIP lateral residuals mostly 0.0 | stated as reading resolution; numeric paint fits reported | summary table |
| `name` meaning changed | `name` = gate number again (alternative positions keep AODB names); bridge `gate` = the stand's gate number | §8 |
| checker used one reference type per class, zero-width bridge lines, skipped same-stand / excl pairs, 8-48 m reach | `check_stands.py` rewritten (envelopes of accepted types; buffered bridges; docked + rest poses; same-stand, excl and alternative stands included; 9.846-41.381 m; cab turn; own-aircraft tunnel) | 3 issues (F5) |
| E10U/E12, F18/F19, F19/F20, C5/C7, F17/F18 below 3 m with accepted types | limits from the observed types; tight pairs recorded | §5: C5/C7, F17/F18, F18/F19 >= 3.2 m; E10/E12 0.4, F19/F20 1.9 (tight, SFO plans both) |
| alternative positions inside the base stand's resting bridge; narrow bodies under the non-docking L2 | `stow` rest pose per bridge, clear of every accepted type of all stands within 150 m | check 4d: 0 overlaps |
| 767 L2 docked to the aft door | L2 docks only a door ahead of the wing (REF B763 2L 15.96 m); request to gates.js / types.js | check 4a-c: 0 issues |
| F10 bridge right-front of the nose | not used | F10 without bridge |
| short bridges F5 / F16 / F17 | rotundas moved back along the OSM walkway where needed | F16 / F17 fine; F5 open |
| rotundas 3.3-6.2 m apart (app) | `rotunda_max_r`; request to use the data rotundas | data rotundas: fixed parts do not overlap (A11 L2 / upper-deck walkways are side by side: note) |
| A380 on EL stands | `a380` / `a380_stands`; request to traffic.js | envelopes: A380 on an EL stand overlaps 9 neighbours |
| curved lead-ins painted straight | `leadin` polyline; markings.js paints it | - |
