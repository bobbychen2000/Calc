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
| position source (pos_src) | osm 105, osm+paint 2, naip 1 |
| name source (name_src) | sfo 108 |
| verified_by | OSM only 33, naip 28, adsb 23, paint 10, paint+adsb 7, naip+adsb 7 |
| src (legacy field) | obs 75, inf 33 |
| classes | B 6, C 60, CL 5, D 7, E 9, EL 18, F 3 |
| jet bridges | 131 OSM bridges: 128 main-deck bridges on 103 stands (1: 78, 2: 25), 3 upper-deck (`bridges_upper`: A6, A11, G13); no bridge of its own: B5S (uses B5), B16S (uses B16), C9V (uses C9), F10, F18 |
| mutually exclusive pairs | 8 |
| remote stands (SFO names, ADS-B) | 1: 2-2A |
| unnamed OSM parking positions (`positions`) | north 95, apron 50, contact-unused 27, west 7 |
| red boxes (NAIP) | 309 |
| painted lead-in vs model axis (NAIP yellow-line fit, 3-22 m behind the nose, clean fits), 18 stands | lateral at the nose: median |r| 0.23 m, max 4.73 m; heading: median |dh| 0.42 deg, max 17.97 deg; corrected: C4 (-1.1 m, -0.2 deg), D14 (+3.2 m, +0.6 deg) |
| NAIP parked-aircraft reading (by eye, +-1.5 m along / +-0.7 m lateral; lateral 0.0 = within the reading resolution, not a measured zero), 44 stands | lateral: median |r| 0.0 m, max |r| 5.2 m; along: median 0.0 m, median |r| 1.4 m |
| ADS-B residual (antenna median in the stand frame), 41 stands / 45 aircraft | lateral: median |r| 0.4 m, max |r| 5.0 m; along (antenna behind the nose): median -9.5 m, range -30.8..0.5 m; heading: median |dh| 0.7 deg |
<!--END:summary-->

- The Google-screenshot survey (`tools/sat/stand_defs.py`, 89 stands) is no longer used for any committed coordinate. It
  stays in the repository as provenance; `tools/sat/export_stands_google_legacy.py` writes it to `tools/sat/work/` only.
- Every stand carries SFO's own name (AODB stand name from flysfo, or the official gate number); positions come from
  OpenStreetMap lead-in lines, calibrated along the axis and verified on NAIP 2024 and against ADS-B positions of
  aircraft that SFO's stand plan put on that stand.
- `check_stands.py` (rewritten after review round 1, §11): aircraft are the envelope of **every** type the app accepts
  on a stand, bridges are buffered footprints in docked and rest poses with the manufacturer's extension range. Result:
  3 issues, all F5 (its OSM bridge is 6.4-6.9 m from the door, shorter than any apron-drive bridge; §10). Pairs below
  the ICAO stand clearance are listed in §5 (they exist at SFO: ICAO allows reduced clearance with VDGS guidance).

## 2. Sources and roles

| Role | Source | Licence / terms | How used |
|---|---|---|---|
| Position, heading | OSM `aeroway=parking_position` ways (Overpass download 24 Sep 2026, `refs/cache/osm/`) | ODbL 1.0 | stop = last node of the oriented way, heading = last segment. 66 of 287 ways are drawn backwards; `tools/stands/osm_src.py` orients each way by two independent cues (the end on an OSM taxiway/taxilane is the start; the end within 60 m of and > 5 m closer to the terminal outline is the stop). The cues never conflict; 21 unreferenced ways with neither cue are not used for contact stands. |
| Bridges | OSM `aeroway=jet_bridge` ways (133) | ODbL 1.0 | building attach point, fixed walkway, rotunda (start of the final segment), parked cab; assignment to stands §4 |
| Names | flysfo.com flight-status `stands[]` (AODB stand names, 8 snapshots 07:32-16:32 UTC 24 Sep), DataSF `chfu-j7tc` gates with operations 18-31 Aug 2026, flysfo terminal maps | DataSF PDDL; flysfo no published terms (used for names/checks only, docs/research/gate_truth.md §7) | stand name = AODB name; stands without an AODB name in the snapshots = DataSF gate number. OSM refs only link the two. |
| Along-axis calibration, verification | NAIP 2024 (USDA, 0.6 m, flown 2024-05-20; `refs/cache/naip/`) | public domain (USDA credit requested) | parked aircraft read by eye on oriented patches (§3.2), red boxes by colour, pavement check |
| Verification, names of ambiguous lines | own ADS-B recording (`refs/cache/rec/`, 07:27-10:28 and 15:13-16:33 UTC 24 Sep) + flysfo stand windows (`tools/stands/adsb_parked.py`) | adsb.fi / adsb.lol terms (gate_truth.md, realtime_feeds.md) | parked stays (on ground, < 1 kt, >= 180 s), median antenna position with NACp >= 8, tied to SFO's stand window of the aircraft's callsign |
| Aircraft dimensions | manufacturers' airport-planning documents (`tools/models/check_dims.py` REF, docs/research/aircraft_models_check.md) | - | class of each SFO type, reference planforms |
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

`verified_by` lists `naip` when a NAIP aircraft sits on the line within 1.5 m laterally (reading not flagged uncertain;
2.5 m before review round 1, so G1, G3, G4, G9 lost it), `paint` when the painted lead-in line on NAIP (yellow-ridge
fit 3-22 m behind the nose, `build_stands.paint_fit`, >= 8 samples, rms <= 0.3 m) lies within 0.8 m / 1.5 deg of the
model axis, and `adsb` when the ADS-B antenna median of the aircraft SFO had on that stand lies within 3 m of the line and its
heading within 10°. ADS-B stays far from the line (push-back / waiting / plan changes) are listed in
`refs/cache/stands/stands_built.json` (`adsb_rejected`) and not used. `src` (legacy meaning) = `obs` if anything
verified the stand, else `inf`.

## 4. Jet bridges

- Geometry from OSM jet-bridge ways, oriented building -> cab (base = the end nearer the terminal outline; for the 5
  ways with ends at equal building distance, the end farther from the nearest stand stop). Per bridge:
  `attach` = building end (for a bridge branching off another bridge's fixed walkway: that bridge's building end),
  `walk` = polyline from the building to the rotunda, `rotunda` = first node of the final segment when the way has a
  fixed part before it (else null - the app derives it), `cab` = the parked cab end as mapped, `osm_id`, `assoc`.
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
  2.45 m (G pier pairs 4.6-4.9 m apart need r ~2.3 m).
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
marks are per type). Pairs below the ICAO clearance:

<!--BEGIN:pairs-->
| pair | clearance m (envelope of all accepted types, final limits) | ICAO | SFO plans both at once (overlaps) | handled |
|---|---|---|---|---|
| B4 / B5S | 0.0 | 7.5 | 0 | excl |
| B5 / B5S | 0.0 | 7.5 | 0 | alternative positions (excl) |
| B10 / B11S | 0.0 | 7.5 | 0 | excl |
| B11 / B11S | 0.0 | 7.5 | 0 | alternative positions (excl) |
| B15 / B16S | 0.0 | 7.5 | 0 | excl |
| B16 / B16S | 0.0 | 7.5 | 0 | alternative positions (excl) |
| C9 / C9V | 0.0 | 7.5 | 0 | alternative positions (excl) |
| C9V / C11 | 0.0 | 7.5 | 0 | excl |
| E10 / E12 | 0.4 | 7.5 | 26 | kept: SFO plans both at once 26 times; span/len limits; model clearance 0.4 m < 3 m (tight, no overlap) |
| F19 / F20 | 1.9 | 7.5 | 29 | kept: SFO plans both at once 29 times; span/len limits; model clearance 1.9 m < 3 m (tight, no overlap) |
| F17 / F18 | 3.2 | 7.5 | 7 | kept (below ICAO, above 3 m) |
| F18 / F19 | 4.6 | 7.5 | 12 | span_max / len_max = largest types SFO parks there (clear 4.6 m) |
| F20 / F21 | 5.7 | 7.5 | 30 | kept (below ICAO, above 3 m) |
| C8 / C10 | 6.1 | 7.5 | 4 | kept (below ICAO, above 3 m) |
| A10 / A12 | 6.3 | 7.5 | 16 | kept (below ICAO, above 3 m) |
| G7 / G8 | 6.6 | 7.5 | 21 | kept (below ICAO, above 3 m) |
| A5 / A9 | 6.9 | 7.5 | 10 | kept (below ICAO, above 3 m) |
| G2 / G5 | 7.0 | 7.5 | 12 | kept (below ICAO, above 3 m) |
| F21 / F22 | 7.3 | 7.5 | 18 | kept (below ICAO, above 3 m) |
<!--END:pairs-->

## 6. Runway ends and lighting (same session)

- **Blast pads** (`js/live/airport.js` END_ZONES), measured on NAIP 2024 strips along the NASR runway axes (3 px/m):
  10L 269 m (dark pad edge; OSM 270, FAA diagram ~260), 10R 231 m (chevrons end ~230 m, the pad merges into taxiway
  pavement; OSM 231, diagram ~240), 28R 98 m and 28L 98 m (pad edge at the seawall road; OSM 91/95, diagram ~90,
  replacing 108 m). Chevron apexes (`tools/imagery/check_markings.py`, yellow peaks on the axis): 10L 17.1, 47.5, 78.1,
  108.5, 139.0, 169.5, 199.8, 230.5 m; 10R 16.6 ... 199.7 m; 28R 17.3, 47.8, 78.3 m; 28L 17.1, 47.6, 78.1 m - spacing
  30.5 m (100 ft), first apex ~17 m. The shader keeps 29.7 m / 15 m (`js/shaders/ground.js` is not mine; request in
  docs/requests/static_geometry_round1.md).
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
| stand | gate | AODB | cls (largest type) | pos_src | verified_by | NAIP resid along/lat m | ADS-B n, along/lat m, dhdg | paint lat m / dh deg | bridges | excl / alt_of / tight | name / position evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | A1 | A1V | EL (B77W) | osm | - | - | - | - | 2 | - | AODB stand A1V (only A1 variant in the feed) on the OSM A1 lead-in |
| A2 | A2 | A2 | EL (B77W) | osm | paint | - | - | -0.29 / +0.35 | 2 | - | OSM ref = SFO name |
| A4 | A4 | A4T | C (B39M) | osm | naip | +0.7 / -0.0 | - | - | 1 | - | OSM ref A3 = SFO stand A4T (A3 hold-room label only; AODB narrow-body types; NAIP narrow-body at this stop) |
| A5 | A5 | A5 | EL (B77W) | osm | paint | - | - | +0.03 / -0.01 | 2 | - | OSM ref = SFO name |
| A6 | A6 | A6 | F (A388) | osm | - | - | - | -0.42 / -0.14 (noisy) | 3 | - | OSM ref = SFO name |
| A8 | A8 | A8 | EL (B77W) | osm | paint | - | - | -0.17 / -0.13 | 2 | - | OSM ref = SFO name |
| A9 | A9 | A9 | EL (B77W) | osm | naip | +0.5 / -0.0 | - | - | 2 | - | OSM ref = SFO name |
| A10 | A10 | A10 | EL (A359) | osm | naip | -5.0 / -0.0 | - | - | 2 | - | OSM ref = SFO name |
| A11 | A11 | A11 | F (A388) | osm | naip | -2.7 / +1.0 | - | - | 3 | - | OSM ref = SFO name |
| A12 | A12 | A12 | E (A332) | osm | - | +9.0 / -0.0 (u) | - | - | 1 | - | OSM ref = SFO name |
| A13 | A13 | A13V | EL (B77W) | osm | paint | - | - | -0.66 / -0.70 | 2 | - | AODB stand A13V (only A13 variant in the feed) on the OSM A13 lead-in |
| A15 | A15 | A15 | C (B38M) | osm | naip | +1.3 / +0.3 | - | -4.03 / -1.39 (noisy) | 1 | - | OSM ref = SFO name |
| B2 | B2 | B2 | C (B39M) | osm | naip | -1.0 / +0.0 | - | - | 1 | - | OSM ref = SFO name |
| B3 | B3 | B3 | C (B39M) | osm | adsb | - | 1, -8.5 / +0.2, -0 | - | 1 | - | OSM ref = SFO name |
| B4 | B4 | B4 | C (A21N) | osm | naip | +2.0 / -0.0 | - | - | 1 | B5S | OSM ref = SFO name |
| B5 | B5 | B5 | C (A321) | osm | paint+adsb | - | 1, -0.6 / -0.8, +3 | -0.38 / -0.75 | 1 | B5S | curved OSM B5 lead-in; ADS-B A321 JBU413 at AODB B5 |
| B5S | B5 | B5S | EL (B77W) | osm | paint | - | - | -0.13 / -0.26 | 0 | B4 B5 alt of B5 | straight OSM B5 lead-in = wide-body alternative (AODB B5S takes A359/B77W/A333) |
| B6 | B6 | B6 | C (B39M) | osm | paint | - | - | -0.10 / -0.36 | 1 | - | OSM ref = SFO name |
| B7 | B7 | B7 | C (B39M) | osm | adsb | - | 1, -11.8 / +0.5, -1 | - | 1 | - | OSM ref = SFO name |
| B8 | B8 | B8 | C (B39M) | osm | naip+adsb | -3.5 / +0.0 | 1, -7.7 / +0.2, +0 | - | 1 | - | unreferenced OSM lead-in between B7 and B9 at the OSM B8 jet bridge; ADS-B ASA424 B39M at AODB B8 and NAIP narrow-body on it |
| B9 | B9 | B9 | C (B38M) | osm | adsb | - | 1, -6.2 / -0.4, +0 | - | 1 | - | OSM ref = SFO name |
| B10 | B10 | B10 | C (A321) | osm | - | - | - | - | 1 | B11S | OSM ref = SFO name |
| B11 | B11 | B11 | C (A320) | osm | naip | +2.0 / -0.0 | - | - | 1 | B11S | curved OSM B11 lead-in (NAIP narrow-body on it) |
| B11S | B11 | B11S | E (B772) | osm | adsb | - | 1, -11.7 / -0.4, +0 | - | 1 | B10 B11 alt of B11 | straight OSM B11 lead-in; ADS-B ASA811 A332 at AODB B11S |
| B12 | B12 | B12 | C (B38M) | osm | adsb | - | 1, +0.3 / -0.2, +0 | -0.11 / +0.10 (noisy) | 1 | - | OSM ref = SFO name |
| B13 | B13 | B13 | C (B39M) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| B14 | B14 | B14 | C (A20N) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| B15 | B15 | B15 | C (B39M) | osm | naip | +2.5 / +0.0 | - | - | 1 | B16S | OSM ref = SFO name |
| B16 | B16 | B16 | C (B739) | osm | adsb | - | 1, -0.3 / -0.6, - | - | 1 | B16S | curved OSM B16 lead-in; ADS-B AAL177 A321 at AODB B16 |
| B16S | B16 | B16S | EL (A339) | osm | - | - | - | - | 0 | B15 B16 alt of B16 | straight OSM B16 lead-in = wide-body alternative (AODB B16S takes B763/B76W/A339) |
| B17 | B17 | B17 | C (A21N) | osm | adsb | - | 2, -1.1 / +0.7, +1 | - | 1 | - | OSM ref = SFO name |
| B18 | B18 | B18 | C (A321) | osm | adsb | - | 1, +0.5 / -0.4, +1 | - | 1 | - | OSM ref = SFO name |
| B19 | B19 | B19 | C (A321) | osm | adsb | - | 1, +0.1 / +1.4, -0 | - | 1 | - | OSM ref = SFO name |
| B20 | B20 | B20 | C (B38M) | osm | naip | +3.0 / -0.0 | - | - | 1 | - | curved OSM B20 lead-in (NAIP narrow-body on it); straight 1096422706 has no SFO name |
| B21 | B21 | B21 | C (A321) | osm | adsb | - | 2, +0.5 / -0.4, +1 | - | 1 | - | OSM ref = SFO name |
| B22 | B22 | B22 | C (B738) | osm | naip+adsb | -5.0 / +0.0 | 1, -16.3 / -0.8, +0 | - | 1 | - | OSM ref = SFO name |
| B23 | B23 | B23 | C (B38M) | osm | naip+adsb | -0.5 / +0.9 | 2, -3.6 / +0.2, -2 | - | 1 | - | OSM B23 lead-in hdg 339 (NAIP + ADS-B AAL2856 A321 on it); the second OSM B23 way 1096422699 has no SFO name |
| B24 | B24 | B24 | C (A21N) | osm | adsb | - | 1, -0.7 / +0.2, -2 | - | 1 | - | OSM ref = SFO name |
| B25 | B25 | B25 | C (A21N) | osm | adsb | - | 1, +0.4 / -0.9, +1 | - | 1 | - | OSM ref = SFO name |
| B26 | B26 | B26 | C (B38M) | osm | adsb | - | 1, -9.1 / -0.2, -2 | - | 1 | - | OSM B26 lead-in hdg 64 (ADS-B AAL2799 B38M on it); straight 1096422703 has no SFO name |
| B27 | B27 | B27 | C (A21N) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| C1 | C1 | C1 | C (B738) | osm | - | - | - | -0.33 / +0.08 (noisy) | 1 | - | OSM ref = SFO name |
| C3 | C3 | C3 | CL (B752) | osm | naip | +0.0 / -0.0 | - | - | 1 | - | OSM ref = SFO name |
| C4 | C4 | C4 | C (B38M) | osm+paint | paint | - | - | +0.01 / +0.02 | 1 | - | OSM ref = SFO name |
| C5 | C5 | C5 | D (B753) span_max 38.1 len_max 54.4 | osm | naip | +1.0 / -0.0 | - | - | 1 | - | OSM ref = SFO name |
| C6 | C6 | C6 | C (A21N) | osm | - | - | - | +0.43 / +10.12 (noisy) | 1 | - | OSM ref = SFO name |
| C7 | C7 | C7 | C (B739) span_max 35.8 | osm | naip+adsb | -1.0 / -0.0 | 1, -12.8 / +1.3, +0 | - | 1 | - | OSM ref = SFO name |
| C8 | C8 | C8 | D (B763) | osm | paint | - | - | -0.63 / -0.03 | 1 | - | OSM ref = SFO name |
| C9 | C9 | C9 | CL (B752) | osm | naip+adsb | +0.0 / -0.0 | 1, -8.5 / +0.9, -0 | - | 1 | C9V | OSM ref = SFO name |
| C9V | C9 | C9V | D (B763) | osm | - | - | - | +0.09 / -0.35 (noisy) | 0 | C9 C11 alt of C9 | INFERRED: unreferenced OSM lead-in at the C9 bridge, the only other line there; AODB C9V = 767 alternative of C9 |
| C10 | C10 | C10 | C (BCS3) | osm | paint+adsb | - | 1, -2.6 / +0.2, +1 | -0.08 / -1.24 | 1 | - | OSM ref = SFO name |
| C11 | C11 | C11 | C (BCS3) | osm | adsb | -15.0 / -0.0 (u) | 1, -5.3 / +0.4, +3 | +0.50 / +1.20 (noisy) | 1 | C9V | OSM ref = SFO name |
| D1 | D1 | D1 | C (B38M) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| D3 | D3 | D3 | C (B38M) | osm | naip | -1.5 / +0.3 | 1, -3.7 / -5.0, +12 | - | 1 | - | OSM ref = SFO name |
| D4 | D4 | D4 | C (B38M) | osm | naip | +0.0 / +0.0 | 1, -11.2 / -2.3, +24 | -4.66 / -6.44 (noisy) | 1 | - | OSM ref = SFO name |
| D5 | D5 | D5 | CL (B752) | osm | naip | -2.5 / -0.5 | - | - | 1 | - | OSM ref = SFO name |
| D6 | D6 | D6 | C (B38M) | osm | naip | -0.0 / +0.0 | - | - | 1 | - | OSM ref = SFO name |
| D7 | D7 | D7 | C (B38M) | osm | naip | -1.0 / -0.0 | - | - | 1 | - | OSM ref = SFO name |
| D8 | D8 | D8 | C (B38M) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| D9 | D9 | D9 | C (B38M) | osm | - | - | 1, -13.2 / +4.6, +12 | - | 1 | - | OSM ref = SFO name |
| D10 | D10 | D10 | C (B38M) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| D11 | D11 | D11 | C (BCS3) | osm | naip | -7.0 / +0.0 | - | - | 1 | - | OSM ref = SFO name |
| D12 | D12 | D12 | C (A21N) | osm | adsb | - | 1, -16.2 / -0.3, -0 | - | 1 | - | OSM ref = SFO name |
| D14 | D14 | D14 | C (B39M) | osm+paint | adsb | - | 1, -6.9 / -0.6, -1 | -1.80 / -15.55 (noisy) | 1 | - | OSM ref = SFO name |
| D15 | D15 | D15 | C (A21N) | osm | adsb | - | 1, -14.1 / -1.5, -1 | - | 1 | - | OSM ref = SFO name |
| D16 | D16 | D16 | C (B738) | osm | naip | -3.0 / +0.0 | - | - | 1 | - | OSM ref = SFO name |
| E2 | E2 | E2 | C (B39M) | osm | - | - | - | +0.27 / +0.45 (noisy) | 1 | - | OSM ref = SFO name |
| E3 | E3 | E3 | C (B39M) | osm | - | - | - | +0.87 / +1.79 (noisy) | 1 | - | OSM ref = SFO name |
| E4 | E4 | E4 | C (B39M) | osm | naip | -2.5 / +0.0 | - | +4.00 / +0.00 (noisy) | 1 | - | OSM ref = SFO name |
| E5 | E5 | E5 | C (B39M) | osm | adsb | - | 1, -8.2 / +0.5, -0 | -0.30 / -0.36 (noisy) | 1 | - | OSM ref = SFO name |
| E6 | E6 | E6 | C (B39M) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| E7 | E7 | E7 | C (B38M) | osm | adsb | - | 1, -10.6 / +0.1, +0 | -1.92 / -5.64 (noisy) | 1 | - | OSM ref = SFO name |
| E8 | E8 | E8 | C (B38M) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| E9 | E9 | E9 | C (B39M) | osm | - | - | - | -3.13 / -11.07 (noisy) | 1 | - | OSM ref = SFO name |
| E10 | E10 | E10U | C (B39M) len_max 42.1 | osm | adsb | - | 1, -9.5 / +0.1, -0 | +2.30 / +14.44 (noisy) | 1 | tight E12 | OSM E10 lead-in; ADS-B UAL2647 B39M (AODB E10U) antenna 8.4 m behind its stop, hdg 137.8 |
| E11 | E11 | E11U | C (B38M) | osm | paint+adsb | - | 1, -10.5 / +0.3, +0 | -0.09 / -0.32 | 1 | - | OSM E11 lead-in (hdg 261); the unreferenced 1096433104 (hdg 297) is not used |
| E12 | E12 | E12 | D (B753) span_max 38.1 len_max 54.4 | osm | paint+adsb | - | 1, -29.4 / -0.0, -1 | +0.21 / -0.02 | 1 | tight E10 | OSM ref = SFO name |
| E13 | E13 | E13T | C (B38M) | osm | paint | - | - | -0.48 / -0.98 | 1 | - | OSM E13 lead-in |
| F5 | F5 | F5 | C (B38M) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| F6 | F6 | F6 | B (E75L) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| F7 | F7 | F7 | B (E75L) | osm | naip+adsb | +1.0 / +0.0 | 2, -10.3 / +0.4, -1 | - | 1 | - | OSM ref = SFO name |
| F8 | F8 | F8 | B (E75L) | osm | - | -1.0 / -0.0 (u) | - | +6.12 / +22.80 (noisy) | 1 | - | OSM ref = SFO name |
| F9 | F9 | F9 | B (E75L) len_max 31.7 | osm | naip+adsb | -1.0 / +0.0 | 1, -11.0 / +0.9, -0 | - | 1 | - | OSM ref = SFO name |
| F10 | F10 | F10 | B (CRJ2) span_max 21.2 len_max 26.8 | osm | naip | +1.0 / -0.0 | - | - | 0 | - | OSM ref = SFO name |
| F11 | F11 | F11 | E (B789) | osm | paint+adsb | - | 1, -21.8 / +0.2, -0 | +0.25 / -0.56 | 2 | - | OSM ref = SFO name |
| F12 | F12 | F12 | C (B39M) | osm | - | - | - | -4.43 / -18.54 (noisy) | 1 | - | OSM ref = SFO name |
| F13 | F13 | F13 | EL (B77W) | osm | naip | -9.0 / -1.0 | - | - | 2 | - | OSM ref = SFO name |
| F14 | F14 | F14 | D (B753) | osm | naip | -1.0 / +0.0 | - | -4.11 / -1.84 (noisy) | 1 | - | OSM ref = SFO name |
| F15 | F15 | F15 | E (B772) | naip | naip | +0.0 / -0.0 | 1, -20.7 / +3.1, -3 | -4.00 / -0.00 (noisy) | 2 | - | OSM ref = SFO name |
| F16 | F16 | F16 | CL (B752) | osm | - | - | - | -4.73 / -17.97 | 1 | - | OSM ref = SFO name |
| F17 | F17 | F17 | D (B753) | osm | - | - | - | - | 1 | - | OSM ref = SFO name |
| F18 | F18 | F18 | B (CRJ2) span_max 21.2 len_max 26.8 | osm | - | - | - | -1.63 / -4.88 (noisy) | 0 | - | OSM ref = SFO name |
| F19 | F19 | F19 | EL (B77W) span_max 64.8 len_max 73.9 | osm | - | - | - | -4.87 / -17.35 (noisy) | 1 | tight F20 | OSM ref = SFO name |
| F20 | F20 | F20 | D (B753) span_max 38.1 len_max 54.4 | osm | - | - | - | - | 1 | tight F19 | OSM ref = SFO name |
| F21 | F21 | F21 | CL (B752) | osm | adsb | - | 1, -23.3 / -0.1, +0 | +0.78 / +0.42 (noisy) | 1 | - | OSM ref = SFO name |
| F22 | F22 | F22 | E (B772) | osm | paint+adsb | - | 1, -17.5 / +0.0, -1 | -0.51 / -0.67 | 2 | - | OSM ref = SFO name |
| G1 | G1 | G1 | E (B772) | osm | - | -2.0 / -5.2 | - | - | 2 | - | OSM ref = SFO name |
| G2 | G2 | G2 | EL (B77W) | osm | paint | - | - | +0.05 / +0.49 | 2 | - | OSM ref = SFO name |
| G3 | G3 | G3 | E (B772) | osm | - | +0.0 / +1.5 | - | -2.82 / +4.58 (noisy) | 2 | - | OSM ref = SFO name |
| G4 | G4 | G4 | E (B772) | osm | - | +0.0 / +1.6 | - | - | 2 | - | OSM ref = SFO name |
| G5 | G5 | G5 | EL (B77W) | osm | paint+adsb | - | 1, -9.7 / +1.8, +1 | +0.56 / +0.59 | 2 | - | OSM ref = SFO name |
| G6 | G6 | G6 | EL (B77W) | osm | naip | -1.0 / -0.7 | - | - | 2 | - | OSM ref = SFO name |
| G7 | G7 | G7 | EL (B77W) | osm | adsb | +3.0 / +2.0 | 1, -30.8 / +0.1, +0 | - | 2 | - | OSM ref = SFO name |
| G8 | G8 | G8 | EL (B77W) | osm | naip | +0.5 / +0.7 | - | - | 2 | - | OSM ref = SFO name |
| G9 | G9 | G9 | EL (B77W) | osm | - | +1.8 / -2.4 | - | - | 2 | - | OSM ref = SFO name |
| G10 | G10 | G10 | EL (B77W) | osm | naip | -4.7 / -1.1 | - | -2.46 / -21.67 (noisy) | 2 | - | OSM ref = SFO name |
| G11 | G11 | - | E (-) | osm | naip | +3.8 / -0.7 | - | +4.95 / +5.73 (noisy) | 2 | - | OSM G11 lead-in at the G11-G12 hold room bridges (DataSF gates G11, G12) |
| G13 | G13 | G13S | F (A388) | osm | adsb | +1.8 / -3.7 | 1, -15.0 / +0.3, -3 | - | 3 | - | OSM G13 lead-in at the three-bridge G13-G14 hold room (AODB G13S takes A388/B748/B77W) |
<!--END:stands-->

Remote stands with SFO names (ADS-B parked stays with an SFO remote-stand window, snapped to the nearest OSM parking
position within 25 m):

<!--BEGIN:remote-->
| remote stand | position | pos_src | ADS-B aircraft | OSM residual |
|---|---|---|---|---|
| 2-2A | (-1522.0, 650.4) hdg 334.64 | osm | C-GYLY BCS3 ACA759 | 3.8 m |
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
| `shares_bridges_of` | stand | an alternative position without bridges of its own uses the bridges of this stand |
| `hdg`, `pos_src`, `name_src`, `verified_by`, `osm_id` | remote | parked heading and provenance of SFO-named remote stands |
| `positions` | top | unnamed OSM parking positions (remote apron, cargo, maintenance, GA; `zone`: apron / north / west / contact-unused) with stop point and heading - candidates for parking aircraft that match no named stand (no SFO name, positions from OSM only, not verified) |

`js/live/airport.js` `standGates` passes `gate`, `excl`, `altOf`, `aodb`, `a380`, `tightWith`, `leadinW`, bridge
`rotundaW` / `walkW` / `cabW` / `cabPose` / `stowW` / `rotundaMaxR` through and applies `span_max` / `len_max`;
`js/live/markings.js` paints the lead-in polyline. The bridge fields need gates.js changes
(docs/requests/static_geometry_round1.md).

## 9. Licences

`data/sfo_stands.json` now contains OSM-derived positions of more than 100 features (stands, bridges, positions), so
it is a Derivative Database under ODbL 1.0 and is offered under ODbL (notice in the file and `docs/ATTRIBUTION.md`).
It no longer contains anything measured on the Google screenshots (which could not be relicensed; stands_xcheck.md
§7), so the share-alike condition can be met. NAIP measurements (public domain), SFO names and our ADS-B observations
can be combined with it. The app must show the OSM attribution (request for the UI owner).

## 10. Remaining doubts

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
