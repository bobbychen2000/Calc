# Stand layout and runway ends cross-checked against OpenStreetMap, the X-Plane Scenery Gateway and the FAA

Research for the "Parking" and "Airport fidelity" objectives. It checks our 89 contact stands (`data/sfo_stands.json`:
43 `obs`, 46 `inf`, 117 bridges; provenance `tools/sat/stand_defs.py`) and the runway ends in `js/geo.js`
(`RWY_ENDS`) against independent sources, quotes what each source's coordinates mean and under which licence it can be
used, classifies every disagreement and recommends corrections. Nothing in `data/` or `js/` was changed.

Written 24 Sep 2026 (UTC) by a research agent. Tools: `tools/xcheck/*.py` (section 10). Third-party downloads are in
`refs/cache/osm/`, `refs/cache/xplane/` and `refs/cache/xcheck/` (gitignored).
**Observed** = read in a file or response I fetched (URL given). **Inferred** = my interpretation. **Not verified** =
could not be checked. Data versions: <!--STAMP-->OSM database 2026-09-24T09:07:42Z (Overpass https://maps.mail.ru/osm/tools/overpass/api/interpreter, fetched 20260924T091047Z); X-Plane Gateway scenery pack 112022; FAA NASR cycle 2026/09/03; AirNav 'FAA information effective 03 SEPTEMBER 2026'; ADS-B/SFO evidence: 10 stands (3 snapshots, newest flysfo_api_flight-status_20260924T085301Z.json.gz)<!--/STAMP-->

## 1. Answer in brief

- **OpenStreetMap is the best independent reference for SFO stands, and it is good.** Observed: 289
  `aeroway=parking_position` features (287 lead-in ways + 2 nodes), 118 with a `ref`. Where SFO's own stand
  allocation and ADS-B put a parked aircraft on a named stand (10 stands, §4.2), OSM has a position with that ref within
  0.4–2.2 m of the aircraft in 8 cases. The other 2 are within 5–6 m, and both are ways drawn backwards. X-Plane is right in 1 case of 10.
  Our stands are right in 1 case of 10, and 1 more is marginal (3.7 m).
- **Our observed stands are good. Our inferred stands have a systematic lateral error.** Compared with OSM, our 43
  `obs` stands have a median lateral offset of +0.3 m (median |offset| 1.5 m). Our 40 matched `inf` stands have a median of
  **+5.7 m** (|offset| 6.3 m). In 25 of those 40 the real lead-in line is more than 3 m to the right of ours. [corrected by verifier: 42 `inf` stands have an OSM best match. The "40" applies an undocumented filter, |cross| ≤ 20 m and |Δhdg| ≤ 25°. Without the filter the values are: median +5.6 m, median |offset| 6.45 m, 25 of 42 more than 3 m to the right. The conclusion is unchanged.] Inferred cause: the
  inference put the centreline too close to the jet bridge (the aircraft's left, L1-door side). ADS-B confirms this at
  B18 (+5.0 m) and B21 (+6.0 m).
- **Stands to fix** (§5): 24 stands where OSM and X-Plane agree against us, or where ADS-B at the SFO-published stand
  shows ours off. There are 10 more where the sources disagree with each other and the imagery must decide. Worst cases:
  - B16 and B24/B25: 16–26 m off.
  - C11: misnamed. Our "C11" is SFO's **C9**. The real C11 is at the pier tip, where we have no stand.
  - C10: 23° heading error.
  - The D-rotunda stands D11–D15: stop points 6–14 m too far from the building, which also explains the long D10 bridge flagged in the handoff.
  - F19/F20: 13–17 m lateral.
  - E6, D3, D15, G3: 10–16 m lateral.
- **Names.** An OSM lead-in carrying our stand's own name lies within the match radius at 79 of 89 stands. OSM refs equal SFO's published stand on all 10 ADS-B checks.
  X-Plane names are unreliable:
  - they are shifted by one or more stands on piers A, B-west and D, and at C;
  - it still carries F1, F2, F3, F3A, F4 and E1, which are not on SFO's current maps (§4.5).
- **Stands we lack** (§4.6):
  - Contact stands in SFO use that have no own stand of ours: A4, A12, A13, B7, B8, B20, B22, B24, C9 (see C11), D6, E2, E12, F7, F9, F18, F21, G11, G13, G14. OSM maps most of them separately.
  - 156 remote, cargo and maintenance lead-ins in OSM, all but 3 without refs. X-Plane has 33 north-field positions (maintenance, GA, corporate ramps) and 3 west-field positions.
- **Runway ends.** `js/geo.js` `RWY_ENDS` reproduces the FAA NASR end coordinates (cycle effective 2026-09-03) and AirNav to
  0.0 m, the elevations exactly, and the displaced thresholds to ≤ 0.1 m. The ends were surveyed by a "3RD PARTY SURVEY" dated 2014-10-22.
  - X-Plane ends are 1–10 m off along the runway. OSM ends are ≤ 3 m off, except 1L (10 m).
  - Two errors found next to the runway ends:
    - (a) The FAA airport diagram, OSM and X-Plane all show a **230–270 m chevron-marked pavement beyond 10L and 10R**. `END_ZONES` has none.
    - (b) `APPROACH_LIGHTS` in `js/geo.js` gives approach lights to 8 runway ends. NASR lists only 28R ALSF2, 28L MALSR and 19L MALSF.
- **Licences.**
  - X-Plane Gateway packs are **GPL v2 or later**. Observed in the pack README/COPYING and in the WorldEditor source that writes them.
  - OSM is **ODbL 1.0**. Copying OSM stand positions into `data/` makes that file a Derivative Database: it must be offered under ODbL, with
    attribution. [corrected by verifier: only if the copy is Substantial. Under the OSMF guideline, a one-off copy of fewer than 100 Features is not Substantial. A copy of 100 or more Features, or repeated copies, is. See §7.] The OSMF "horizontal layers" guideline says mixing OSM and non-OSM features of the same type triggers
    share-alike for that type.
  - Our current stands are measured on Google imagery, so mixing them with OSM needs a decision by the owner (§7).

## 2. Sources and what their coordinates mean

| Source | Version fetched | Reference point of a stand (quoted) | Licence (quoted, §7) |
|---|---|---|---|
| **Ours**: `data/sfo_stands.json` | as in repo (file dated 24 Sep 07:01, written by `tools/sat/export_stands.py`) | `nose` = nose tip of the stopped aircraft, `hdg` = true heading ("stand inferred from jet-bridge positions / stand pitch", note in the file) | Imagery-derived (Google Maps screenshots, reference only) |
| **OSM** `aeroway=parking_position` | Overpass `maps.mail.ru` instance, database timestamp as in the stamp above (first run 08:41Z, rerun 09:07Z; same results); bbox 37.595,-122.405,37.640,-122.350; `out meta geom` | "As a node: Put a node where the nose wheel stops." "As a way: Draw a way from the relevant taxiway and to the nose wheel position. The direction of the way indicates the direction a plane should park. This usually means that the last node of the way should be where the nose wheel is parked." (https://wiki.openstreetmap.org/wiki/Tag:aeroway=parking_position, rev. 2785188, 2024-12-05) | ODbL 1.0 |
| **X-Plane** apt.dat row 1300 | Gateway recommended pack **112022** (uploaded 2026-09-07 by "Julian", "XSG-17643 / Gates renamed.", WorldEditor 2.7.2-r1) | Spec: "Latitude of location in decimal degrees", "Heading (true) of airplane positioned at this location" (https://developer.x-plane.com/article/airport-data-apt-dat-12-00-file-format-specification/, last updated 22 Dec 2023). The spec does **not** say which point of the aircraft. WorldEditor's own code does: `WED_RampPosition::GetTips()` reads the location into `Point2 nosewheel_loc` and draws the nose tip `nose_offset` ahead of it: A 1.0, B 2.7, C 4.7, D 9.5, E 8.2, F 8.8 m. For type `misc` it is the aircraft centre ("tip of nose" = `fuse_len / 2` ahead). Source: https://github.com/X-Plane/xptools/blob/a3725c8f5ed6d9681573496ab0153e550d54cd09/src/WEDEntities/WED_RampPosition.cpp (lines 154–184). **So a 1300 point is the nose wheel.** | GPL v2 or later |
| **ADS-B + SFO AODB** | our 1 Hz recording (adsb.fi/adsb.lol, since 07:27 UTC) + flysfo.com stand windows, via `tools/live/gatecheck.py` (see `docs/research/gate_truth.md`) | ADS-B position = the aircraft's GNSS antenna (on the centreline, some metres aft of the nose). The stand name = SFO's allocation covering that time | flysfo: no terms published (see gate_truth.md §7). Used here only as a check. Nothing is copied into data. |
| **FAA NASR** APT CSV | cycle effective **2026-09-03**: https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip (`APT_RWY_END.csv`, `APT_RWY.csv`) | Runway end (`LAT_DECIMAL`/`LONG_DECIMAL`), displaced threshold (`LAT_DISPLACED_THR_DECIMAL`…), `DISPLACED_THR_LEN` (ft); position source "3RD PARTY SURVEY" 2014/10/22 | US Government work |
| **AirNav** | https://www.airnav.com/airport/KSFO, "FAA INFORMATION EFFECTIVE 03 SEPTEMBER 2026" (the page `geo.js` cites) | runway end lat/lon in degrees-decimal-minutes | page terms not reviewed. Only compared, never copied |
| **FAA Airport Diagram** | https://aeronav.faa.gov/d-tpp/2609/00375ad.pdf (AL-375, valid 03 SEP–01 OCT 2026) | chart symbols (blast pads / EMAS / approach lights); not to survey accuracy | US Government work |

**Quality of the OSM parking positions (observed):**
- The current versions were last edited between 2019-10-16 and 2026-04-08 (each way's `timestamp`). Most were last edited by `Necessarycoot72`, including 166 of the 171 unreferenced lead-ins (most on 2022-09-20), and by `lasagna`, `sharksfan166269` and `iamthemap2121`.
- **64 of the 287 ways are drawn backwards**: the first node is at the stand and the way runs out to the taxilane.
  - `compare_stands.py` detects these and flips them. A way is treated as backwards when its first node is within 60 m of the terminal outline and more than 5 m closer to it than the last node.
- 8 refs occur twice: A12, B5, B11, B16, B20, B23, B26 and E6.
  - Inferred: these are the alternative lead-ins that SFO's AODB names with a suffix (`B5S`, `B11S`, `B16S`; gate_truth.md §3).
- The only refs that are not gate numbers are `50-6`, `50-7` and `50-8`, in the north field. None of them is in SFO's AODB list of remote stands (2-x, 6-x, 9-x, 12-x, 41-xx).

**X-Plane rows parsed (observed, `ksfo_apt_parsed.json`):**

| Row codes | Content |
|---|---|
| 1300/1301 | 136 ramp starts: 117 `gate`, 19 `tie_down`. ICAO category A 11, B 15, C 76, D 14, E 17, F 3. All are operation type `airline`. |
| 1500 | 126 jetways. The pack's `Earth nav data/apt.dat` has these rows; the Gateway's bare `KSFO.dat` lacks them. |
| 1201 / 1202 / 1204 | Taxi network: 534 nodes, 437 edges (383 `taxiway_E`, 6 `taxiway_D`, 48 `runway`), 408 active-zone rows. |
| 100 | 4 runways. |
| 110–116 | 46 pavement polygons and 2,392 linear features. Line types by segment count: 60 → 1,390, 24 → 1,370, 20 → 3,030, 53 → 732, 57 → 173, 54 → 50. Lighting: 101 → 837, 102 → 732, 103 → 108, 105 → 81. |
| 20 | 326 signs. |
| 21 | 6 PAPIs. |
| 19 | 8 windsocks. |
| 1050–1056 | 15 frequencies. |

Undocumented codes (not verified):
- Line types 10, 12, 24, 30, 60, 62 and 63 are not in the 12.00 spec table. They are also not in WorldEditor's `AptDefs.h` / `WED_Enums.h`, so their meaning is not verified.
- Jetway size codes 10, 11 and 12 occur 27 times. The spec defines only 0–3.

## 3. Method

- **Frame.** Every coordinate is converted to the app's world frame with `js/geo.js` `llToEN`, reimplemented exactly in `xcommon.py`.
- **Offsets.** They are expressed in *our* stand's frame:
  - **along**: + means their point is ahead of our nose tip, toward the building;
  - **cross**: + means to the right of our centreline, seen from the cockpit;
  - **Δhdg**: theirs − ours.
- **Robust comparisons.** Cross and Δhdg are robust. Along also contains the difference in reference points: nose tip vs nose wheel vs GNSS antenna.
- **Matching.** A counterpart is a candidate if it is within 25 m of our estimated nose-wheel point (nose − WED `nose_offset`) and within 45° of our heading. The best candidate minimises distance + 0.1·|Δhdg|. The same-name counterpart is also looked up anywhere on the field.
- **Tolerances for "agree".** |cross| ≤ 3 m and |Δhdg| ≤ 10°.
- **Voting.**
  - Both references off, on the same side (within 6 m of each other) or with the same heading error (within 12°): **OURS OFF**.
  - Both references off, but in different directions: **unresolved**.
  - ADS-B at an SFO-published stand overrides the vote. On all 10 stands with ADS-B evidence, OSM agreed with the aircraft.
- **Registration check.** A rigid translation fitted to the cross residuals, by source image, removes at most 1.2 m of RMS against OSM (table below). So the disagreements are **per stand, not per image**: there is no sign of another image-registration slip like the 17.5 m G-pier one found earlier.
  - The one image where a shift explains X-Plane much better (03dcd4ae, C pier: 5.9 → 3.5 m) shows no shift against OSM. That is an X-Plane offset.

<!--BEGIN:registration-->
| source | image (tools/sat/stand_defs.py) | n | rigid shift E / S (m) | RMS cross before → after (m) |
|---|---|---|---|---|
| OSM | all `obs` stands | 36 | +0.20 / -0.35 | 2.0 → 1.9 |
| OSM | 03dcd4ae | 8 | +0.4 / +2.3 | 4.0 → 3.7 |
| OSM | 151ec51d | 11 | -0.1 / +0.5 | 5.0 → 5.0 |
| OSM | 39176bb8 | 13 | -1.6 / +4.8 | 6.0 → 5.2 |
| OSM | b1d51b0f | 21 | +2.1 / -4.4 | 8.3 → 7.1 |
| OSM | bf5c7afc | 12 | +2.4 / +2.1 | 7.8 → 7.5 |
| OSM | c235f3b8 | 9 | -4.5 / +1.2 | 6.6 → 5.7 |
| OSM | d82848c4 | 9 | -1.9 / -0.1 | 4.0 → 3.9 |
| X-Plane | all `obs` stands | 22 | +0.77 / +0.23 | 2.6 → 2.5 |
| X-Plane | 03dcd4ae | 6 | +6.5 / -2.3 | 5.9 → 3.5 |
| X-Plane | 151ec51d | 11 | +2.9 / -4.4 | 9.1 → 8.9 |
| X-Plane | 39176bb8 | 13 | +0.8 / +3.2 | 6.9 → 6.4 |
| X-Plane | b1d51b0f | 15 | -6.9 / -6.3 | 9.1 → 7.8 |
| X-Plane | bf5c7afc | 12 | +0.4 / +6.1 | 9.8 → 8.7 |
| X-Plane | c235f3b8 | 7 | +0.8 / -9.2 | 12.1 → 9.6 |
| X-Plane | d82848c4 | 9 | -1.3 / +1.5 | 3.8 → 3.3 |
<!--END:registration-->

- **Frame accuracy.** The app's equirectangular frame is 0.12 % short in the east–west scale (111 320·cos φ = 88 175 m/deg against 88 285 m/deg on WGS-84 at the ARP latitude 37.6188° [corrected by verifier: was "88 157 against 88 266". Both figures were about 19 m/deg low. The 0.12 % ratio (0.124 %) and the 3.4 m runway shortfall are unchanged.]). This shortens 10L/28R by 3.4 m against its geodesic length (§6). It is irrelevant for distances between neighbouring stands, at most about 0.1 m.

## 4. Results — stands

### 4.1 Verdicts (our 89 stands)

<!--BEGIN:verdict_summary-->
| position verdict | obs | inf | total |
|---|---|---|---|
| agree | 16 | 4 | 20 |
| agree with OSM; X-Plane differs | 14 | 4 | 18 |
| OURS OFF (OSM and X-Plane agree) | 4 | 11 | 15 |
| unresolved (sources disagree) | 4 | 6 | 10 |
| OURS OFF (ADS-B + SFO) | 3 | 6 | 9 |
| agree with X-Plane; OSM differs | 0 | 7 | 7 |
| differs from the only counterpart (OSM) | 1 | 4 | 5 |
| differs from the only counterpart (X-Plane) | 0 | 3 | 3 |
| NO COUNTERPART | 0 | 1 | 1 |
| agree (ADS-B + SFO confirm ours) | 1 | 0 | 1 |
<!--END:verdict_summary-->

### 4.2 Independent evidence: parked aircraft on SFO-published stands (ADS-B)

The rows are aircraft stationary for 120 s or more in our recording, where SFO's AODB stand window names the stand ("SFO window"). Two rows (marked "occupancy") had no callsign; for them, the one allocation at the stand our matcher chose is used.
- **Distances and cross values.** "dist (x …)" is measured from the aircraft's antenna. The cross value is taken across the aircraft's axis, and only when a heading was reported.
- **For our stands**, the antenna position is given in our stand's frame instead. With the nose tip about 4–10 m ahead of the antenna, "along" should be about −4 to −10 and "cross" about 0.

<!--BEGIN:adsb_table-->
| SFO stand (evidence) | aircraft (reg, type, flight) | ADS-B hdg | ours, same name (in our stand frame; Δhdg = ours − ADS-B) | ours nearest: dist (cross from aircraft axis) | OSM same ref: dist (cross) | OSM nearest | X-Plane same name: dist (cross) | X-Plane nearest |
|---|---|---|---|---|---|---|---|---|
| B16 (SFO window) | N107NN, A321, AAL177 | 101° | B16: ADS-B point +2.2 along / -15.7 cross of our stand, Δhdg +17° | B16 15.9 m (x +14.5) | B16: 1.8 m (x +1.6) [2 ways] | B16 1.8 m (x +1.6) | Gate B15 B16: 41.9 m (x -39.1) | Gate B19 B20 18.1 m (x +18.1) |
| B18 (occupancy) | N968JT, A321, .N968JT | 307° | B18: ADS-B point -4.2 along / +5.0 cross of our stand, Δhdg -9° | B18 6.5 m (x -5.6) | B18: 1.7 m (x +0.6) | B18 1.7 m (x +0.6) | Gate B18: 11.2 m (x -6.3) | Gate B18 11.2 m (x -6.3) |
| B21 (SFO window) | N937JB, A321, JBU515 | — | B21: ADS-B point +1.7 along / +6.0 cross of our stand | B21 6.2 m | B21: 0.8 m | B21 0.8 m | Gate B21: 15.9 m | Gate B21 15.9 m |
| B23 (SFO window) | N980UY, A321, AAL2856 | 338° | B23: ADS-B point -4.9 along / +5.2 cross of our stand, Δhdg -9° | B23 7.1 m (x -5.9) | B23: 2.2 m (x +0.2) [2 ways] | B23 2.2 m (x +0.2) | Gate B23: 16.0 m (x -16.0) | Gate B23 16.0 m (x -16.0) |
| B24 (SFO window) | N437AN, A21N, AAL2506 | — | B25 (as alias): ADS-B point -5.8 along / +26.1 cross of our stand | B23 23.1 m | B24: 0.4 m | B24 0.4 m | Gate B24: 32.8 m | Gate B23 14.1 m |
| B26 (occupancy) | N161AA, A321, — | — | B26: ADS-B point -1.8 along / +3.7 cross of our stand | B26 4.1 m | B26: 1.8 m [2 ways] | B26 1.8 m | Gate B26 B27: 85.6 m | Gate B25 20.8 m |
| B5 (SFO window) | N943JT, A321, JBU413 | 53° | B5: ADS-B point -6.7 along / -0.5 cross of our stand, Δhdg -26° | B5 6.7 m (x -2.4) | B5: 0.9 m (x +0.9) [2 ways] | B5 0.9 m (x +0.9) | — (no such name) | Gate B10 B11 76.6 m (x +64.6) |
| C10 (SFO window) | C-FDUW, BCS3, ACA738 | 321° | C10: ADS-B point -3.4 along / -5.6 cross of our stand, Δhdg -23° | C10 6.5 m (x +3.8) | C10: 1.2 m (x -1.0) | C10 1.2 m (x -1.0) | — (no such name) | Gate C11 9.2 m (x +8.9) |
| C11 (SFO window) | N316DU, BCS3, DAL2635 | 292° | C11: ADS-B point -3.2 along / -34.1 cross of our stand, Δhdg -48° | C10 30.7 m (x -30.0) | C11: 5.0 m (x -0.9) | C11 5.0 m (x -0.9) | Gate C11: 26.9 m (x -26.9) | Gate C9 7.3 m (x -0.5) |
| G5 (SFO window) | N2341U, B77W, UAL189 | 208° | G5: ADS-B point -9.8 along / +2.1 cross of our stand, Δhdg -0° | G5 10.0 m (x -2.2) | G5: 6.0 m (x -1.9) | G5 6.0 m (x -1.9) | Gate G5 G6: 3.6 m (x -3.2) | Gate G5 G6 3.6 m (x -3.2) |
<!--END:adsb_table-->

What this establishes (observed unless stated):
- **OSM.** Positions with the SFO name are within 0.4–2.2 m of the aircraft at B5, B16, B18, B21, B23, B24, B26 and C10. At C11 and G5 the distance is 5.0 and 6.0 m; both ways are drawn backwards, so their first node is the stand end.
  - Across the aircraft axis, OSM is within 1.9 m on all 7 rows that report a heading. The other 3 rows (B21, B24, B26) have no heading; there OSM is 0.4–1.8 m from the antenna in total distance.
- **Ours.**
  - G5 is right: cross +2.1 m, Δhdg 0°.
  - B26 is marginal: +3.7 m.
  - B18, B21 and B23 are 5–6 m off laterally (+5.0, +6.0, +5.2).
  - B5 is 26° off in heading, and its class B refuses the A321 that SFO put there. gatecheck reports "class-rejected; geometry matches B5".
  - C10 is 23° off in heading and 5.6 m off laterally.
  - B16 is 15.7 m off.
  - B24 (our alias on B25) is 26 m away from the real B24.
  - SFO's C11 is 34 m from our "C11". Our "C11" sits on OSM's C9 (1.4 m).
- **X-Plane.** Only G5 is within 4 m. At the others the X-Plane position with that name is 11–86 m away, or the name does not exist.
  X-Plane's positions nearest to the aircraft carry other names: "C9" for C11, "C11" for C10, "B19 B20" for B16, "B23" for B24, "B25" for B26.
- The sample is small, because the recording is at night (00:30–02:00 PDT). Re-running `run_all.sh` later in the day adds rows.

### 4.3 Reference-point offsets along the stand axis

Their point − our nose tip, for matches with |cross| ≤ 6 m and |Δhdg| ≤ 15°:

<!--BEGIN:along_stats-->
| class / our src | X-Plane: n, median along (min…max) m | OSM: n, median along (min…max) m |
|---|---|---|
| B/inf | 2, +6.5 (+6.4…+6.6) | 1, +3.9 (+3.9…+3.9) |
| B/obs | 1, +6.5 (+6.5…+6.5) | 3, -1.3 (-1.7…-0.0) |
| C/inf | 9, -9.8 (-12.4…+10.4) | 8, +4.9 (-6.0…+14.2) |
| C/obs | 4, -2.1 (-3.3…+1.0) | 11, +0.3 (-2.7…+6.3) |
| CL/obs | 2, +2.1 (+0.9…+3.4) | 4, -2.6 (-6.7…-1.4) |
| D/inf | 2, -8.6 (-9.0…-8.1) | 2, +4.2 (+0.6…+7.8) |
| D/obs | 2, -8.3 (-9.2…-7.5) | 2, +1.4 (-1.9…+4.7) |
| E/inf | 1, +1.9 (+1.9…+1.9) | 1, +0.9 (+0.9…+0.9) |
| E/obs | 3, -7.7 (-10.9…-1.0) | 4, -1.4 (-5.6…+4.9) |
| EL/inf | 3, -8.8 (-11.2…-4.2) | 2, -1.1 (-3.0…+0.9) |
| EL/obs | 10, -9.6 (-12.6…-6.1) | 12, -2.9 (-4.9…-0.6) |
| all/inf | 17, -9.0 (-12.4…+10.4) | 14, +2.2 (-6.0…+14.2) |
| all/obs | 22, -7.6 (-12.6…+6.5) | 36, -1.6 (-6.7…+6.3) |
<!--END:along_stats-->

- **X-Plane.** On our observed wide-body stands (class EL), X-Plane points are a median 9.6 m behind our nose tip. That fits the nose-wheel convention: WED draws the nose 8.2 m ahead for category E.
- **OSM.** Its "stop" nodes are only 1.6–2.9 m behind our nose tips. [corrected by verifier: the range is imprecise. Those two numbers are the all/obs median (−1.6) and the EL/obs median (−2.9). The per-class obs medians run from +1.4 m (ahead, D) to −2.9 m (behind, EL); C/obs is +0.3; single values run −6.7…+6.3 m. At the 8 ADS-B stands with a forward-drawn way, the OSM end is within 0.3–2.2 m of the aircraft's GNSS antenna.] *Inferred:* mappers end the lead-in line where the painted line ends, near the most forward stop mark, not at a given type's nose wheel. OSM along values are therefore not a precise stop position.
- **Consistency of our observed noses.** On our observed stands (B23, B26, G5), the ADS-B antennas are 1.8–9.8 m behind our nose tips (§4.2), as expected for a nose tip. [corrected by verifier: this holds only for the sign. All three are 4.0–7.1 m shorter than the app's antenna offset `ANT`·L (A321: 8.9 m; B77W: 14.8 m). See S3.]
- **Inferred stands** do not follow this pattern (OSM +2.2 m, range −6…+14). The D rotunda is the outlier (§5).

### 4.4 Every stand

- Columns: best OSM match and best X-Plane match, as "dist (along / cross, Δhdg)". "own name at N m" means the counterpart with our name is elsewhere. ⟲ = an OSM way drawn backwards and flipped; cat = X-Plane ICAO size category.
- Bridge counts: OSM `jet_bridge` ways and X-Plane 1500 jetways whose aircraft end is within 14 m of our L1/L2 door estimate. They are indicative only, because they depend on our stand being in the right place.

<!--BEGIN:stands_table-->
| Ours (aliases) | cls · src | OSM best match: ref: dist (along / cross, Δhdg) | X-Plane best match: name: dist (along / cross, Δhdg) · cat | ADS-B + SFO | position verdict | name verdict · flags | bridges ours / XP / OSM |
|---|---|---|---|---|---|---|---|
| G10 (G14) | EL · obs | G10 ⟲: 6.4 m (+1.4 / +6.2, +1°) | Gate G13 G14: 15.4 m (-7.4 / +13.5, -0°) · own name at 62 m · E |  | unresolved (sources disagree) | same as OSM · merged: SFO runs G10/G14 as separate stands | 2 / 2 / 2 |
| G9 | EL · inf | G9 ⟲: 3.9 m (+0.9 / +3.8, +0°) | Gate G9 G10: 15.1 m (-11.3 / +10.0, -0°) · E |  | unresolved (sources disagree) | same as OSM | 2 / 2 / 2 |
| G6 | EL · obs | G6 ⟲: 4.4 m (-4.0 / +1.8, -0°) | Terminal G: 12.2 m (-11.8 / +3.1, -0°) · own name at 73 m · E |  | agree with OSM; X-Plane differs | same as OSM | 2 / 1 / 2 |
| G5 | EL · obs | G5 ⟲: 4.0 m (-4.0 / +0.3, -0°) | Gate G5 G6: 11.4 m (-11.3 / -1.1, -0°) · E | G5: ours OK (aircraft +2.1 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 2 / 1 / 2 |
| G2 | EL · obs | G2 ⟲: 5.1 m (-4.9 / -1.5, -1°) | Terminal G: 13.2 m (-12.6 / -4.0, -0°) · own name at 78 m · E |  | agree with OSM; X-Plane differs | same as OSM | 2 / 1 / 2 |
| G1 | E · obs | G1 ⟲: 5.6 m (-5.6 / +0.1, -0°) | Gate G1 G2: 11.3 m (-10.9 / -2.9, -0°) · E |  | agree | same as OSM | 2 / 1 / 2 |
| G7 | EL · obs | G7 ⟲: 2.3 m (-2.3 / -0.2, +0°) | Gate G7 G8: 9.9 m (-7.2 / +6.8, -1°) · E |  | agree with OSM; X-Plane differs | same as OSM | 2 / 2 / 2 |
| G4 | EL · obs | G4: 2.7 m (-2.7 / +0.3, +0°) | Gate G3 G4: 8.5 m (-6.1 / +6.0, -1°) · E |  | agree with OSM; X-Plane differs | same as OSM | 2 / 2 / 2 |
| G3 | EL · inf | G3 ⟲: 14.5 m (-1.2 / +14.4, +15°) | Terminal G: 22.3 m (-11.4 / +19.1, +14°) · own name at 66 m · E |  | OURS OFF (OSM and X-Plane agree) | same as OSM | 2 / 2 / 2 |
| G12 (G11/G13) | EL · obs | G13 ⟲: 4.3 m (-3.4 / +2.6, +1°) | Terminal G: 11.4 m (-10.7 / +3.7, +6°) · own name at 82 m · F |  | agree with OSM; X-Plane differs | OSM = our alias G13 · merged: SFO runs G12/G11/G13 as separate stands (OSM has G13 here) | 2 / 2 / 3 |
| G8 | E · obs | (no ref): 5.0 m (-4.8 / -1.5, -3°) · own name at 48 m | Terminal G: 12.5 m (-4.8 / -11.6, -16°) · own name at 127 m · F |  | agree with OSM; X-Plane differs | OSM position has no ref · OSM has other positions here: G11 | 2 / 0 / 1 |
| A3 (A4) | EL · inf | A3: 23.9 m (-21.6 / +10.1, -1°) | Gate A3 A4 A5: 12.5 m (-11.2 / +5.6, +1°) · D |  | OURS OFF (OSM and X-Plane agree) | same as OSM · merged: SFO runs A3/A4 as separate stands | 2 / 1 / 1 |
| A5 | EL · obs | A5: 4.9 m (-4.9 / +0.0, +0°) | Gate A9 A10: 8.4 m (-8.1 / -2.2, -0°) · own name at 68 m · E |  | agree | same as OSM · X-Plane name A9/A10 | 2 / 1 / 2 |
| A9 | EL · obs | A9: 1.7 m (-1.7 / -0.5, -0°) | Gate A12: 8.4 m (-8.4 / +0.5, -0°) · own name at 75 m · E |  | agree | same as OSM · X-Plane name A12 | 2 / 1 / 2 |
| A10 | EL · obs | A10: 2.0 m (-2.0 / +0.3, +0°) | Gate A15: 8.6 m (-8.6 / +0.9, -0°) · own name at 146 m · E |  | agree | same as OSM · X-Plane name A15 | 2 / 1 / 1 |
| A1 | C · inf | — · own name at 19 m | — · own name at 27 m |  | NO COUNTERPART | no OSM counterpart | 1 / 0 / 2 |
| A2 | EL · inf | A2 ⟲: 7.1 m (-3.1 / +6.3, +2°) | Gate A1 A2: 4.5 m (-4.2 / +1.6, +2°) · C |  | agree with X-Plane; OSM differs | same as OSM | 2 / 1 / 2 |
| A6 (A7) | EL · obs | A6: 1.3 m (-0.9 / -0.9, +0°) | Gate A6 A7 A8: 11.9 m (-7.6 / -9.1, -1°) · F |  | agree with OSM; X-Plane differs | same as OSM · merged: SFO runs A6/A7 as separate stands | 2 / 0 / 2 |
| A8 | EL · inf | A8: 3.2 m (-3.0 / -1.2, +0°) | Gate A11: 9.1 m (-8.8 / -2.0, -2°) · own name at 71 m · E |  | agree | same as OSM · X-Plane name A11 | 2 / 1 / 2 |
| A11 (A13) | EL · obs | A11: 3.2 m (-3.1 / -0.8, -0°) | Gate A13 A14: 11.3 m (-11.3 / -1.1, +1°) · own name at 79 m · D |  | agree | same as OSM · merged: SFO runs A11/A13 as separate stands | 2 / 1 / 3 |
| A15 (A12/A14) | C · obs | A15: 2.2 m (+1.6 / -1.4, +0°) | Terminal A: 1.7 m (-1.7 / +0.1, +0°) · own name at 75 m · C |  | agree | same as OSM · merged: SFO runs A15/A12/A14 as separate stands | 1 / 2 / 1 |
| C3 | C · obs | C3 ⟲: 0.8 m (+0.4 / +0.7, +4°) | — · own name at 51 m |  | agree | same as OSM | 1 / 0 / 1 |
| C5 | CL · obs | (no ref): 3.5 m (-1.4 / +3.3, +7°) · own name at 2 m | Gate C3: 2.2 m (+0.9 / +2.0, +15°) · own name at 45 m · C |  | unresolved (sources disagree) | same as OSM · X-Plane name C3 | 1 / 0 / 1 |
| C7 (C9) | CL · obs | C7: 1.7 m (-1.6 / -0.4, +5°) | Gate C5: 4.5 m (+3.4 / -3.0, +8°) · own name at 31 m · C |  | agree | same as OSM · X-Plane name C5 · merged: SFO runs C7/C9 as separate stands | 1 / 1 / 1 |
| C11 | C · obs | C9: 1.4 m (-1.4 / +0.2, +10°) · own name at 31 m | Gate C7: 4.3 m (+3.9 / -1.6, +20°) · own name at 54 m · C | C11: ours OFF (aircraft -34.1 m across our centreline, Δhdg -48°) | OURS OFF (ADS-B + SFO) (vote: agree with OSM; X-Plane differs) | DIFFERS from OSM (C9) · MISNAMED? position = OSM C9 · X-Plane name C7 · OSM has other positions here: C9 | 1 / 1 / 1 |
| C4 | C · inf | C4: 10.4 m (-6.9 / +7.8, +4°) | Gate C4: 10.0 m (-0.6 / +10.0, -0°) · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM | 1 / 1 / 1 |
| C6 | C · inf | C6: 6.5 m (-6.0 / +2.5, +8°) | Gate C6: 7.5 m (-0.1 / +7.5, +7°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| C8 | C · inf | C8: 7.7 m (+7.1 / +3.0, -0°) | Gate C8: 6.1 m (+0.2 / +6.1, -0°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| C10 | C · inf | C10: 6.6 m (-2.3 / -6.2, +22°) | Gate C11: 5.9 m (-4.7 / +3.6, +40°) · C | C10: ours OFF (aircraft -5.6 m across our centreline, Δhdg -23°) | OURS OFF (ADS-B + SFO) (vote: unresolved (sources disagree)) | same as OSM · X-Plane name C11 | 1 / 1 / 1 |
| B9 | C · inf | B9: 12.0 m (-7.0 / +9.8, +0°) | Gate B9: 9.9 m (-9.4 / -2.9, +2°) · C |  | agree with X-Plane; OSM differs | same as OSM | 1 / 1 / 1 |
| B12 | C · inf | B12: 9.3 m (-5.9 / +7.2, +0°) | Gate B12: 10.0 m (-9.8 / -1.8, +2°) · C |  | agree with X-Plane; OSM differs | same as OSM | 1 / 1 / 1 |
| B13 | C · inf | B13: 11.1 m (-6.1 / +9.3, -0°) | Gate B13: 10.3 m (-9.8 / +3.1, +2°) · C |  | unresolved (sources disagree) | same as OSM | 1 / 1 / 1 |
| B14 | C · inf | B14: 9.0 m (-6.2 / +6.6, +0°) | Gate B14: 10.9 m (-10.4 / -3.3, +2°) · C |  | unresolved (sources disagree) | same as OSM | 1 / 1 / 1 |
| B17 | C · inf | B17: 8.8 m (-6.1 / +6.3, -0°) | Gate B17: 12.4 m (-12.4 / -0.5, +2°) · C |  | agree with X-Plane; OSM differs | same as OSM | 1 / 1 / 1 |
| B18 | C · inf | B18: 7.9 m (-5.8 / +5.3, +8°) | Gate B18: 12.6 m (-12.4 / -2.6, +2°) · C | B18: ours OFF (aircraft +5.0 m across our centreline, Δhdg -9°) | OURS OFF (ADS-B + SFO) (vote: agree with X-Plane; OSM differs) | same as OSM | 1 / 1 / 1 |
| B21 | C · inf | B21: 5.9 m (+0.9 / +5.8, +8°) | Gate B21: 12.5 m (-12.4 / -1.4, +2°) · C | B21: ours OFF (aircraft +6.0 m across our centreline, no heading) | OURS OFF (ADS-B + SFO) (vote: agree with X-Plane; OSM differs) | same as OSM | 1 / 1 / 1 |
| B10 | B · obs | B10: 5.7 m (-0.0 / -5.7, -6°) | Gate B10 B11: 21.6 m (+12.9 / -17.2, -21°) · D |  | unresolved (sources disagree) | same as OSM | 1 / 0 / 0 |
| B11 | B · obs | B11: 5.7 m (-0.8 / -5.6, -15°) | — · own name at 55 m |  | differs from the only counterpart (OSM) | same as OSM | 1 / 0 / 1 |
| B15 | B · inf | B16: 15.8 m (+9.5 / +12.7, -0°) · own name at 21 m | Gate B15 B16: 20.3 m (+5.5 / -19.5, -21°) · D |  | unresolved (sources disagree) | same as OSM · stop point 6-10 m ahead of our nose in both · OSM has other positions here: B16 | 1 / 0 / 0 |
| B16 | B · inf | B16: 14.9 m (+3.5 / -14.5, -15°) | Gate B19 B20: 6.6 m (+6.4 / +1.9, +3°) · own name at 58 m · C | B16: ours OFF (aircraft -15.7 m across our centreline, Δhdg +17°) | OURS OFF (ADS-B + SFO) (vote: agree with X-Plane; OSM differs) | same as OSM · X-Plane name B19/B20 | 1 / 0 / 0 |
| B19 (B20) | B · inf | B20 ⟲: 12.0 m (+7.5 / +9.4, +0°) · own name at 23 m | Gate B26 B27: 7.2 m (+6.6 / -3.0, +3°) · own name at 52 m · C |  | agree with X-Plane; OSM differs | same as OSM · stop point 7-8 m ahead of our nose in both · X-Plane name B26/B27 · merged: SFO runs B19/B20 as separate stands (OSM has B20 here) | 1 / 0 / 1 |
| B27 | CL · obs | B27: 7.1 m (-6.7 / +2.3, -2°) | Gate B25: 7.7 m (+7.7 / +1.1, -30°) · own name at 71 m · C |  | agree with OSM; X-Plane differs | same as OSM · X-Plane name B25 · OSM has other positions here: B26 | 1 / 2 / 1 |
| B26 | CL · obs | B26: 4.9 m (-3.6 / +3.4, +2°) | Gate B25: 16.8 m (+5.7 / -15.8, +15°) · own name at 82 m · C | B26: ours OFF (aircraft +3.7 m across our centreline, no heading) | OURS OFF (ADS-B + SFO) (vote: unresolved (sources disagree)) | same as OSM · X-Plane name B25 | 1 / 0 / 0 |
| B23 (B22) | C · obs | B23: 6.3 m (-2.7 / +5.7, +11°) | Gate B23: 10.6 m (-1.6 / -10.5, +37°) · C | B23: ours OFF (aircraft +5.2 m across our centreline, Δhdg -9°) | OURS OFF (ADS-B + SFO) (vote: unresolved (sources disagree)) | same as OSM · merged: SFO runs B23/B22 as separate stands (OSM has B24 here) | 1 / 0 / 1 |
| B25 (B24) | C · inf | B25: 10.6 m (-5.4 / -9.1, +5°) | Gate B24: 10.0 m (-7.5 / -6.6, +6°) · own name at 53 m · C | B24: ours OFF (aircraft +26.1 m across our centreline, no heading) [SFO stand is our alias] | OURS OFF (ADS-B + SFO) (vote: OURS OFF (OSM and X-Plane agree)) | same as OSM · merged: SFO runs B25/B24 as separate stands | 1 / 1 / 0 |
| B6 (B7/B8) | C · obs | B7: 10.1 m (-7.2 / +7.1, +7°) · own name at 42 m | Gate B7 B8: 14.8 m (+13.4 / -6.4, -9°) · own name at 43 m · C |  | unresolved (sources disagree) | OSM = our alias B7 · merged: SFO runs B6/B7/B8 as separate stands (OSM has B7 here) | 1 / 0 / 1 |
| B3 | C · inf | — · own name at 25 m | Gate B3: 17.9 m (+11.5 / +13.7, +2°) · C |  | differs from the only counterpart (X-Plane) | no OSM counterpart | 1 / 0 / 0 |
| B1 | B · inf | B1: 10.7 m (-9.6 / -4.7, -22°) | — |  | differs from the only counterpart (OSM) | same as OSM | 1 / 0 / 0 |
| B2 | B · inf | B2: 7.7 m (+2.5 / +7.2, +3°) | — |  | differs from the only counterpart (OSM) | same as OSM | 1 / 0 / 1 |
| B4 | B · inf | B4: 8.6 m (-3.6 / -7.9, +39°) | — |  | differs from the only counterpart (OSM) | same as OSM | 1 / 0 / 0 |
| B5 | B · inf | B5: 7.3 m (-7.3 / +0.1, +23°) | — | B5: ours OFF (aircraft -0.5 m across our centreline, Δhdg -26°) | OURS OFF (ADS-B + SFO) (vote: differs from the only counterpart (OSM)) | same as OSM | 1 / 0 / 0 |
| C1 | C · inf | C1: 16.6 m (-0.7 / +16.6, +11°) | — |  | differs from the only counterpart (OSM) | same as OSM | 1 / 0 / 1 |
| D9 | C · obs | D9: 4.5 m (+4.3 / +1.3, +8°) | Gate D9 D10: 3.6 m (-3.3 / +1.6, +5°) · C |  | agree | same as OSM | 1 / 1 / 1 |
| D8 | C · obs | D8 ⟲: 2.2 m (-1.5 / +1.6, +9°) | Gate D8: 5.3 m (-2.6 / +4.7, +11°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| D16 | C · obs | D16: 7.8 m (+2.0 / +7.5, +14°) | Gate D18: 7.7 m (-0.3 / +7.7, +15°) · own name at 60 m · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM · X-Plane name D18 | 1 / 1 / 1 |
| D5 (D6) | C · obs | D5: 12.5 m (-10.3 / +7.2, +9°) | Gate D5: 11.6 m (-5.1 / +10.4, +7°) · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM · merged: SFO runs D5/D6 as separate stands | 1 / 1 / 1 |
| D1 (D2) | C · obs | D1 ⟲: 6.3 m (+6.3 / +0.3, +0°) | — · own name at 47 m |  | agree | same as OSM · merged: SFO runs D1/D2 as separate stands | 1 / 0 / 1 |
| D10 | C · inf | — · own name at 23 m | Gate D11: 16.3 m (+15.1 / +6.3, +21°) · own name at 51 m · C |  | differs from the only counterpart (X-Plane) | no OSM counterpart · X-Plane name D11 | 1 / 0 / 0 |
| D11 | C · inf | D11 ⟲: 14.8 m (+14.2 / +4.1, -1°) | Gate D12: 10.5 m (+10.4 / +1.2, -1°) · own name at 32 m · C |  | agree with X-Plane; OSM differs | same as OSM · stop point 10-14 m ahead of our nose in both · X-Plane name D12 | 1 / 1 / 1 |
| D12 | C · inf | D12 ⟲: 9.8 m (+9.7 / +1.3, -21°) | Gate D14: 9.6 m (+9.5 / +1.2, -20°) · own name at 35 m · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM · stop point 10-10 m ahead of our nose in both · X-Plane name D14 | 1 / 1 / 1 |
| D14 | C · inf | D14 ⟲: 12.7 m (+11.4 / +5.6, +6°) | Gate D15: 15.5 m (+13.9 / +6.9, +7°) · own name at 32 m · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM · stop point 11-14 m ahead of our nose in both · X-Plane name D15 | 1 / 0 / 0 |
| D15 | C · inf | D15: 14.6 m (+6.5 / +13.1, +17°) | Gate D16 D17: 16.3 m (+9.1 / +13.5, +16°) · own name at 30 m · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM · stop point 6-9 m ahead of our nose in both · X-Plane name D16/D17 | 1 / 0 / 1 |
| D3 | C · inf | D3 ⟲: 10.6 m (+2.7 / +10.2, -22°) | Gate D3: 11.0 m (+6.8 / +8.7, -18°) · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM | 1 / 1 / 1 |
| D4 | C · inf | D4: 10.1 m (+6.0 / +8.2, -20°) | Gate D4: 15.6 m (+0.8 / +15.6, -4°) · C |  | unresolved (sources disagree) | same as OSM | 1 / 1 / 1 |
| D7 | C · inf | D7 ⟲: 16.1 m (+5.2 / +15.3, -22°) | Gate D6: 18.9 m (+0.3 / -18.9, +0°) · own name at 18 m · C |  | unresolved (sources disagree) | same as OSM · X-Plane name D6 · OSM has other positions here: D6 | 1 / 1 / 1 |
| E9 | C · obs | E9 ⟲: 4.0 m (+3.4 / +2.0, +0°) | Gate E9 E11: 16.7 m (+6.4 / +15.5, -19°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| E5 | C · obs | E5 ⟲: 1.7 m (+0.3 / +1.7, +8°) | Gate E5: 17.4 m (+1.9 / +17.3, +8°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| E4 | C · obs | E4 ⟲: 2.1 m (-0.9 / -1.9, +4°) | — · own name at 22 m |  | agree | same as OSM | 1 / 0 / 0 |
| E7 | C · inf | E7 ⟲: 6.6 m (+6.2 / +2.1, +0°) | Gate E7: 19.5 m (+1.7 / +19.4, +1°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| E11 | C · inf | — · own name at 2 m | Gate E13: 22.7 m (+4.2 / +22.3, +1°) · own name at 20 m · C |  | differs from the only counterpart (X-Plane) | no OSM counterpart · X-Plane name E13 | 1 / 0 / 0 |
| E10 | C · obs | E10 ⟲: 2.7 m (-0.8 / +2.6, -2°) | Gate E8 E10: 1.3 m (+1.0 / +0.8, +1°) · C |  | agree | same as OSM · OSM has other positions here: E10A/E12 | 1 / 1 / 1 |
| E13 (E12) | C · obs | E12 ⟲: 18.6 m (+14.7 / +11.4, +9°) · own name at 33 m | Gate E12: 10.1 m (+8.0 / +6.3, +21°) · own name at 48 m · C |  | OURS OFF (OSM and X-Plane agree) | OSM = our alias E12 · stop point 8-15 m ahead of our nose in both · merged: SFO runs E13/E12 as separate stands (OSM has E12 here) | 1 / 0 / 1 |
| E8 | C · inf | E8: 3.9 m (+3.6 / +1.4, +2°) | Gate E6: 7.3 m (+7.0 / +2.0, +3°) · own name at 34 m · C |  | agree | same as OSM · X-Plane name E6 · OSM has other positions here: E10A | 1 / 1 / 1 |
| E6 | C · inf | E6: 16.4 m (+5.1 / +15.5) | Gate E3: 15.7 m (+5.2 / +14.8, +40°) · own name at 50 m · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM · stop point 5-5 m ahead of our nose in both · X-Plane name E3 | 1 / 1 / 0 |
| E3 (E2) | C · inf | (no ref): 1.3 m (+0.1 / -1.3, -20°) · own name at 8 m | Gate E2: 7.5 m (-0.5 / -7.5, -20°) · own name at 66 m · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM · merged: SFO runs E3/E2 as separate stands | 1 / 1 / 1 |
| F22 (F21) | E · obs | F22 ⟲: 1.9 m (+1.9 / -0.3, -1°) | Gate F22: 7.7 m (-7.7 / -0.3, +1°) · D |  | agree | same as OSM · merged: SFO runs F22/F21 as separate stands | 2 / 1 / 1 |
| F15 | E · inf | F15 ⟲: 5.6 m (+0.9 / +5.6, +3°) | Gate F15: 2.1 m (+1.9 / -0.8, -2°) · C |  | agree with X-Plane; OSM differs | same as OSM | 2 / 1 / 2 |
| F13 | EL · obs | F13: 0.6 m (-0.6 / +0.1, -0°) | Gate F13: 7.1 m (-7.1 / +0.2, +1°) · D |  | agree | same as OSM | 2 / 2 / 2 |
| F11 | E · obs | F11: 4.9 m (+4.9 / -0.3, +0°) | Gate F11: 1.7 m (-1.0 / -1.3, +1°) · D |  | agree | same as OSM | 2 / 2 / 1 |
| F17 (F18) | D · obs | F17 ⟲: 4.7 m (+4.7 / +0.5, -0°) | Gate F18 F17: 9.2 m (-9.2 / +0.1, -1°) · C |  | agree | same as OSM · merged: SFO runs F17/F18 as separate stands | 2 / 1 / 1 |
| F16 | D · inf | F16: 7.8 m (+7.8 / +0.6, -0°) | Gate F16: 9.2 m (-9.0 / +1.8, -1°) · C |  | agree | same as OSM | 2 / 1 / 1 |
| F14 | D · inf | F14: 1.4 m (+0.6 / +1.3, -0°) | Gate F14: 8.2 m (-8.1 / +1.3, -1°) · C |  | agree | same as OSM | 2 / 1 / 1 |
| F12 | D · obs | F12 ⟲: 3.1 m (-1.9 / +2.4, -0°) | Gate F12: 8.2 m (-7.5 / +3.4, -1°) · C |  | agree with OSM; X-Plane differs | same as OSM | 2 / 1 / 1 |
| F19 | E · obs | F19 ⟲: 13.3 m (+1.1 / +13.3, +11°) | Gate F19: 18.7 m (-11.1 / +15.0, +9°) · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM | 2 / 1 / 1 |
| F20 | C · inf | F20 ⟲: 17.1 m (-6.5 / +15.8, -0°) | Gate F20: 17.1 m (-3.6 / +16.7, +2°) · C |  | OURS OFF (OSM and X-Plane agree) | same as OSM | 1 / 1 / 1 |
| F8 (F7) | B · obs | F7 ⟲: 1.7 m (-1.7 / +0.4, +3°) · own name at 23 m | Gate F7: 6.4 m (-2.0 / +6.1, +2°) · own name at 33 m · C |  | agree with OSM; X-Plane differs | same as OSM · merged: SFO runs F8/F7 as separate stands (OSM has F7 here) | 1 / 1 / 1 |
| F6 | B · obs | F6 ⟲: 1.3 m (-1.3 / -0.5, +5°) | Gate F6: 6.5 m (+6.5 / -0.3, +14°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 0 / 1 |
| F10 | B · inf | F8 ⟲: 13.3 m (+2.1 / -13.1, -30°) · own name at 20 m | Gate F8: 11.8 m (+10.5 / -5.2, -42°) · own name at 54 m · C |  | OURS OFF (OSM and X-Plane agree) | DIFFERS from OSM (F8) · X-Plane name F8 · OSM has other positions here: F8 | 1 / 1 / 0 |
| F5 | B · inf | F5: 4.1 m (+3.9 / +1.5, +2°) | Gate F5: 7.5 m (-1.4 / +7.4, +12°) · B |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
<!--END:stands_table-->

### 4.5 Stand names by area

The SFO column is the union of stand names in SFO's AODB (flysfo `stands[]`) and gates with operations in DataSF, 18–31 Aug 2026. It is taken from `docs/research/gate_truth.md` §4 / `refs/cache/gate_truth/gates_report.json`, suffix letters removed.

<!--BEGIN:names_table-->
| Area | SFO stands in use (AODB ∪ DataSF, via gate_truth) | ours: own stands | ours: only as alias | OSM refs | X-Plane names | in SFO use but no own stand of ours | X-Plane names not in SFO's maps |
|---|---|---|---|---|---|---|---|
| A | A1 A2 A4 A5 A6 A8 A9 A10 A11 A12 A13 A15 | A1 A2 A3 A5 A6 A8 A9 A10 A11 A15 | A4 A7 A12 A13 A14 | A1 A2 A3 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14 A15 | A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14 A15 | A4 A12 A13 | — |
| B | B2 B3 B4 B5 B6 B7 B8 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | B1 B2 B3 B4 B5 B6 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B21 B23 B25 B26 B27 | B7 B8 B20 B22 B24 | B1 B2 B3 B4 B5 B6 B7 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | B3 B6 B7 B8 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | B7 B8 B20 B22 B24 | — |
| C | C1 C3 C4 C5 C6 C7 C8 C9 C10 C11 | C1 C3 C4 C5 C6 C7 C8 C10 C11 | C9 | C1 C3 C4 C5 C6 C7 C8 C9 C10 C11 | C2 C3 C4 C5 C6 C7 C8 C9 C11 | C9 | — |
| D | D1 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 | D1 D3 D4 D5 D7 D8 D9 D10 D11 D12 D14 D15 D16 | D2 D6 | D1 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 | D1 D2 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 D17 D18 | D6 | — |
| E | E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 | E3 E4 E5 E6 E7 E8 E9 E10 E11 E13 | E2 E12 | E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 | E1 E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 | E2 E12 | E1 |
| F | F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | F5 F6 F8 F10 F11 F12 F13 F14 F15 F16 F17 F19 F20 F22 | F7 F18 F21 | F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | F1 F2 F3 F3A F4 F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | F7 F9 F18 F21 | F1 F2 F3 F3A F4 |
| G | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G11 G12 G13 G14 G104 G105 | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G12 | G11 G13 G14 | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G11 G13 | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G11 G12 G13 G14 | G11 G13 G14 G104 G105 | — |
<!--END:names_table-->

Findings (observed in the tables above; interpretation marked):
- **OSM refs agree with SFO's list and with ours.**
  - Exceptions:
    - our C11, which OSM calls C9, confirmed by ADS-B;
    - our F10, which OSM and X-Plane both call F8; [corrected by verifier: overstated. For both sources the nearest position to our F10 is named F8, but it is 12–14 m away with a 30–42° heading difference. OSM's own F10 is 20–23 m away. X-Plane's "Gate F8" lies 8.8 m from OSM's F10 stop point and 11.6 m from OSM's F8, so X-Plane does not independently confirm the name.]
    - our E13, B6, B19, G12 and F8, which sit where OSM has our aliases E12, B7, B20, G13 and F7;
    - our B15 (inf): its nearest OSM lead-in is a B16 one (+9.5 / +12.7), and OSM B15 is 20 m away (−18.4 / −9.2).
  - Of the contact gates SFO uses, OSM lacks only A4, B8, G12 and G14.
- **X-Plane names are shifted on whole faces** (positions compared in §4.4):
  - A west: our A5, A9, A10 are X-Plane "A9 A10", "A12", "A15".
  - A east: our A8, A11 are X-Plane "A11", "A13 A14".
  - D rotunda: our D10, D11, D12, D14, D15, D16 are X-Plane "D11", "D12", "D14", "D15", "D16 D17", "D18".
  - C: our C5, C7, C11 are X-Plane "C3", "C5", "C7".
  - B west: our B16, B19 are X-Plane "B19 B20", "B26 B27".
  - X-Plane also keeps F1, F2, F3, F3A, F4 and E1, which are on none of SFO's current maps.
  - It names D17, D18 and C2, which are on the maps but have no operations and no AODB stand.
  - *Inferred:* the Gateway pack's names ("Gates renamed", 2026-09-07) come from an older numbering and **must not be used for names**.
- **Our merged stands.** OSM maps separate lead-ins for most of the gates we merged: G11/G13, B7, B20, B22, B24, E2, E12, F7, F18, F21, D6, A7, A12, A13, A14. This agrees with gate_truth.md's finding that SFO allocates them at the same time.

### 4.6 Theirs without ours

These are counterparts that are nobody's best match. Zones:
- **contact**: within 45 m of the terminal outline;
- **north field**: north of the 10/28 runways, i.e. z < −550 m;
- **west field**: west of pier G;
- **terminal apron**: everything else.

<!--BEGIN:orphans-->
| source | zone | n | names (⟨…⟩ = also a secondary candidate of our stand …; cat = X-Plane ICAO size) |
|---|---|---|---|
| OSM | contact (at a terminal facade) | 48 | A1, A7, A12 ×2, A13, A14, B3, B5 ⟨B5⟩, B6, B11 ⟨B11⟩, B15 ⟨B15⟩, B19 ⟨B19⟩, B20 ⟨B19⟩, B22, B23 ⟨B23⟩, B24 ⟨B23⟩, B26 ⟨B27/B26⟩, C5 ⟨C5⟩, C11, D6 ⟨D7⟩, D10, E2, E3 ⟨E3⟩, E6 ⟨E6⟩, E10A ⟨E10/E8⟩, E11, E13, F9, F10, F18, F21, G8, G11 ⟨G8⟩, (no ref) ×10, (no ref) ⟨A6⟩, (no ref) ⟨C11⟩, (no ref) ⟨C3⟩, (no ref) ⟨D1⟩, (no ref) ⟨G8⟩ |
| OSM | north field (maintenance / cargo / GA) | 95 | (no ref) ×92, 50-6, 50-7, 50-8 |
| OSM | terminal apron (remote / hardstand) | 54 | (no ref) ×52, (no ref) ⟨F15⟩ ×2 |
| OSM | west field (cargo, west of pier G) | 7 | (no ref) ×7 |
| X-Plane | contact (at a terminal facade) | 18 | Gate B22 [C], Gate B6 [C] ⟨B3⟩, Gate C2 [D], Gate C9 [C], Gate D1 D2 [C], Gate D7 [C] ⟨D7⟩, Gate E1 [C], Gate E4 [C], Gate F1 [C], Gate F2 [C], Gate F21 [C], Gate F3 [C], Gate F4 [C], Gate F9 F10 [C], Gate G11 G12 [E], Terminal A [C] ×3 |
| X-Plane | north field (maintenance / cargo / GA) | 33 | Corporate Ramp [B], East Maintenance Ramp [D] ×3, GA Ramp [A] ×11, GA Ramp [B] ×11, North Maintenance Ramp [C] ×4, North Maintenance Ramp [D] ×3 |
| X-Plane | terminal apron (remote / hardstand) | 4 | Gate A1 [C], Gate F3A [C], Terminal G South [E] ×2 |
| X-Plane | west field (cargo, west of pier G) | 3 | Terminal G South [E], West Cargo Ramp [B] ×2 |
<!--END:orphans-->

Classification:
1. **Contact stands we lack or place wrongly.** OSM has 48 of these, 14 without a ref; X-Plane has 18.
   - With refs that SFO uses: A12 (twice), A13, A14, A7, B6, B22, B24, B20, C11, D6, D10, E2, E11, E13, F9, F10, F18, F21, G8, G11. See §5 per area.
   - Several (D10, E11, G8) exist in ours but sit 25 m or more from OSM's position with that name. The same-name distance is in §4.4.
2. **Remote and hardstand positions on the terminal apron.** OSM has 54, all without refs; X-Plane has "Gate A1", "Gate F3A" and "Terminal G South" (×2).
   - SFO's AODB remote stands (2-1, 2-2A/B, 6-1/2/4, 9-5/6, 12-1…12-5, 41-08…41-21, G104, G105) cannot be matched to these by name.
   - *Not verified* which OSM lead-in is which SFO remote stand. The way to find out is to log ADS-B at SFO-published remote stands (gate_truth.md §6.1).
3. **North field (maintenance, cargo, GA).**
   - OSM has 95 positions: 92 without a ref, plus `50-6`, `50-7`, `50-8`.
   - X-Plane has 33: "North Maintenance Ramp" ×7 (categories C/D, airlines fdx, dal, ual), "East Maintenance Ramp" ×3 (D), "GA Ramp" ×22 (A/B), "Corporate Ramp" ×1.
   - We have none. HANDOFF P4 already lists them.
4. **West field (cargo, west of pier G).** OSM has 7 without refs; X-Plane has "West Cargo Ramp" ×2 (B) and "Terminal G South" ×1 (E).
   - Our remote stands G103, G104 and G105 are in `remote` (points only). OSM has no ref G10x.

### 4.7 Jet bridges

Observed counts: ours 117 (61 stands with 1 bridge, 28 with 2), X-Plane 126 jetways (1500), OSM 133 `jet_bridge` ways (83 with a ref).

Door-based association (§4.4 last column):
- All three agree on 37 stands.
- OSM and X-Plane agree with each other but not with us on 20:
  - A3, A10, F12, F14, F16, F17, F19, F22: both show **one** bridge where we build **two**. Our second (L2) bridge comes from a rule, "wide-body stands (D/E/EL/F) get two", not from observation.
  - B1, B4, B5, B10, B15, B16, B26, B3, D10, D14, E4, E11: both show none near our door. Mostly this is because our stand is misplaced there.
- X-Plane jetway bases are a median 9.4 m from our bridge attach points. Only 18 of 117 are within 5 m.
- *Not verified*: which F-pier and A-pier stands really have two bridges. Check on the imagery before keeping the L2 rule.

## 5. Classification of the disagreements and recommended corrections

Classes, most important first:
- **(P) position**: our stand is off, established by ADS-B or by OSM and X-Plane agreeing.
- **(U) unresolved**: the sources disagree; re-measure on the imagery.
- **(N) name**.
- **(M) merged**: SFO runs these as separate stands.
- **(A) along-track** stop point.
- **(C) class**.
- **(R) reference-only**: a difference that is not a defect, e.g. nose tip vs nose wheel.

Offsets are OSM's best match in our frame, as along / cross / Δhdg.

Two caveats apply to every item below:
- **These are targets for re-measurement, not values to paste.** See §7 before copying OSM or X-Plane coordinates.
- After any change, re-run `tools/sat/check.py` and `check_bridges.py` (CLAUDE.md).

### 5.1 Systematic

**S1.** Inferred stands sit about 6 m toward the bridge side (their centreline is left of the real one).
- Evidence: OSM median cross +5.7 m on 40 `inf` stands against +0.3 m on `obs`; ADS-B at B18 and B21.
- Recommendation: re-derive every `inf` stand from the painted lead-in line in the imagery rather than from bridge heads. Do the B-east face first (B9–B21). Until then, a stopgap is to shift each `inf` stand +5.7 m to its right, but only after checking its neighbour spacing. [corrected by verifier: a blanket shift is a poor stopgap. Of the 42 matched `inf` stands it would make 16 worse against OSM: A8, C6, C10, B16, B25, B1, B4, B5, D12, E7, E8, E3, F16, F14, F10 and F5. Only 11 → 14 stands would come within 3 m. Shift only stands whose own OSM, X-Plane or ADS-B offset is to the right.]

**S2.** L2 bridges on wide-body stands follow a rule. The references show one bridge at F12, F14, F16, F17, F19, F22, A3 and A10 (§4.7). Verify each on the imagery.

**S3.** On our three observed stands with ADS-B evidence, the antennas are 1.8–9.8 m behind our nose tips (§4.3). This small sample gives no reason to change `ANT = 0.2·L`. [corrected by verifier: the sample points the other way. `js/live/traffic.js` puts the antenna `ANT`·L = 8.9 m (A321) and 14.8 m (B77W) behind the nose. The observed offsets are 4.9 m (B23, A321), 1.8 m (B26, A321) and 9.8 m (G5, B77W): all 4.0–7.1 m shorter. The ADS-B stands whose along value is measured against inferred stands (B18 −4.1, B5 −6.6, C10 −3.3; B16 and B21 are even ahead of our nose) point the same way. So either `ANT` = 0.2 is too large, or our along positions are several metres too far from the building. More samples are needed, but "no reason to change" is not supported.]

### 5.2 By area

**A (international, 10 stands).**
- **A5, A6, A8, A9, A10, A11 and A15**: agree with OSM (cross within 1.4 m).
- **A3** (inf) (P, M, N): OSM A3 −21.6 / +10.1; X-Plane "A3 A4 A5" −11 / +5.6. SFO uses A4 (or A4T), not A3. Re-measure; rename to A4 as gate_truth.md recommends; model A3 and A4 separately.
- **A2** (inf): OSM +6.3 lateral (S1), X-Plane +1.6. Re-measure.
- **A1** (inf): no counterpart within 25 m. OSM A1 is elsewhere, and SFO uses A1 and A1V. Re-measure.
- **A6/A7, A11/A13, A15/A12/A14** (M): OSM has separate A7, A12 (×2), A13 and A14. Add them.

**B (T1).**
- **B-east, B9–B21, all inferred** (P, S1): OSM cross +5.3 to +9.8 m on all 7. ADS-B: B18 +5.0, B21 +6.0. Move each onto its lead-in.
- **B16** (inf) (P, C): ADS-B −15.7 m, +17°; OSM B16 at −14.5 / −15°. An A321 is parked there, but our class is B. Move it, and set the class to at least C/CL. OSM has two B16 lead-ins (B16/B16S).
- **B15** (inf) (U): its nearest OSM lead-in is a B16 one (+9.5 / +12.7), and OSM B15 is 20 m away (−18.4 / −9.2). Re-measure.
- **B19/B20** (M, A): OSM separate B19 and B20; stop point 7–8 m ahead. Split.
- **B23/B22** (P, M): ADS-B +5.2 m, OSM +5.7 / +11°. Split B22 off.
- **B24/B25** (P, M): the real B24 is 26 m from our B25 (ADS-B, OSM 0.4 m). OSM B25 lies at −9.1 lateral. Split into two stands.
- **B26, B27** (obs): B26 ADS-B +3.7 m (marginal); B27 agrees with OSM.
- **B10, B11** (obs, class B) (U): OSM −5.7 / −5.6 lateral, −6° / −15°, and OSM has two B11 lead-ins. Check which lead-in the imaged aircraft used.
- **B6/B7/B8** (M, U): our B6 sits on OSM "B7"; OSM B6 is separate, and OSM has no B8. SFO uses all three. Split.
- **B1, B2, B4, B5, B3** (inf, T1 north face):
  - OSM gives B1 −4.7 / −22°, B2 +7.2, B4 −7.9 / +39°, B5 +0.1 / +23°.
  - ADS-B at B5: 26° heading error; an A321 is parked there but our class is B (C).
  - B3: no OSM within 25 m; X-Plane +13.7.
  - SFO does not use B1 (gate_truth.md).
  - Re-measure all five, and fix the B5 class.

**C (T1).**
- **C11** (N, P): our "C11" (obs) is SFO/OSM **C9**. Rename it C9, which also dissolves our C7/C9 merge. Add a new **C11** at the pier tip: the ADS-B aircraft was there on heading 292°, and OSM C11's first node (way drawn backwards) and X-Plane "Gate C9" are within 7 m.
- **C10** (inf) (P): ADS-B −5.6 m, −23°; OSM −6.2 / +22°. Rotate and move it.
- **C4** (inf) (P): OSM +7.8, X-Plane +10.0.
- **C1** (inf) (U): OSM +16.6 / +11°, and no X-Plane counterpart.
- **C5** (obs): OSM (no ref) +3.3; X-Plane +2.0 / +15°. Borderline; check.
- **C3, C6, C7, C8**: agree with OSM (C6 +2.5, C8 +3.0).
- **C2**: on the T1 map, but has no operations and no AODB stand. Leave it out.

**D (T2).**
- **D11, D12, D14, D15** (inf) (A, P): OSM and X-Plane both put the stop point **6–14 m closer to the rotunda** than our nose. D12 is also rotated −21°, and D15 is +13 m lateral / +17°.
  - Move these stands in. This also shortens the long D10 bridge (54 m) that HANDOFF §3 flags.
- **D10** (inf): no OSM within 25 m. OSM D10 is elsewhere (§4.6). Re-measure.
- **D3** (P): +10.2 / −22°.
- **D4** (U): OSM +8.2 / −20°, X-Plane +15.6.
- **D7** (U): OSM +15.3 / −22°; X-Plane matches its "D6".
- **D5/D6** (obs) (P, M): OSM +7.2 / +9°, X-Plane +10.4. Split D6 off; OSM has a separate D6.
- **D16** (obs) (P): OSM +7.5 / +14°, X-Plane +7.7 / +15°. Re-check the imaged aircraft: it may have been off the line, or on another lead-in.
- **D1, D8, D9**: agree.

**E (T3).**
- **E3/E2** (inf) (P, M): heading −20° in both references. Split E2 off; OSM has a separate E2.
- **E6** (inf) (P): +15.5 lateral in both references.
- **E13/E12** (obs) (M, U): OSM and X-Plane both show E12 near our stand, with the stop point 8–15 m ahead. Split and re-measure.
- **E11** (inf): no OSM within 25 m; OSM E11 is elsewhere. Re-measure.
- **E4, E5, E7, E8, E9, E10**: agree with OSM.
  - X-Plane's E5, E7, E9 and E11 positions are 15–22 m off laterally: an X-Plane defect, not ours.

**F (T3).**
- **F19** (obs) and **F20** (inf) (P): both references put them 13–17 m to the right (F19 +11°). Re-measure the F-pier tip on the imagery.
- **F10** (inf) (N, P): sits on OSM/X-Plane **F8**, with −13 m / −30° against it. [corrected by verifier: it is nearest to OSM F8, at 13–14 m and −30°, not on it. X-Plane "Gate F8" sits closer to OSM F10 (8.8 m) than to OSM F8 (11.6 m). The rename F10 → F8 rests on OSM alone and on an inferred, misplaced stand, so re-measure on the imagery first. "Our F8 = OSM F7" is solid: 1.1 m apart.]
  - Rename our F8(F7) → F7 and our F10 → F8.
  - Add **F9** and **F10**. F9 had 185 operations in two weeks (gate_truth.md).
- **F17/F18, F21/F22** (M): OSM has separate F18 and F21. Split.
- **F15** (inf): OSM +5.6 (S1).
- **F5, F6, F11, F12, F13, F14, F16**: agree.

**G (international).**
- **G3** (inf) (P): OSM +14.4 / +15°, X-Plane +19.1 / +14°.
- **G9** (inf) and **G10** (obs) (U): OSM +3.8 and +6.2 (ways drawn backwards); X-Plane +10…+13.5.
- **G1, G2, G4, G5, G6, G7, G8, G12**: agree with OSM. G5 is also confirmed by ADS-B.
- **G10/G14, G12/G11/G13** (M): OSM has separate G11 and G13. Split per SFO.

### 5.3 What not to take from X-Plane

- Its names (§4.5).
- Its E-pier and B-west positions.
- Its runway end positions (§6).

Use it only as a secondary geometric vote. It is still useful for:
- the north-field ramps' existence and size categories;
- the taxi routing graph;
- sign texts, as a check against our signs (GPL: see §7).

## 6. Runway ends and thresholds (`js/geo.js` `RWY_ENDS`)

Offsets are geodesic (WGS-84), measured along / across the FAA runway axis from the NASR end. + along points into the runway; + cross is to the right looking down the runway.

<!--BEGIN:runway_table-->
| End | FAA NASR end (DMS) | elev ft | disp ft | geo.js − NASR (along / cross m) | AirNav − NASR | geo.js elev − NASR ft | X-Plane end − NASR | X-Plane disp m (ft) / blast pad m | OSM runway way end − NASR |
|---|---|---|---|---|---|---|---|---|---|
| 10L | 37-37-43.4594N 122-23-36.2107W | 5.5 | 0 | -0.0 / +0.0 | -0.0 / +0.0 | +0.0 | -4.8 / -0.1 | 0 (0) / 250 | -0.3 / +0.2 |
| 28R | 37-36-48.721N 122-21-25.708W | 13.0 | 300 | +0.0 / +0.0 | +0.0 / +0.0 | +0.0 | +1.1 / -0.5 | 90 (295) / 100 | -1.7 / -0.5 |
| 10R | 37-37-34.648N 122-23-35.1796W | 7.1 | 0 | -0.0 / -0.0 | -0.0 / -0.0 | +0.0 | -1.3 / +0.4 | 0 (0) / 250 | +1.5 / +0.5 |
| 28L | 37-36-42.163N 122-21-30.057W | 12.6 | 300 | +0.0 / +0.0 | +0.0 / +0.0 | +0.0 | +1.8 / +2.1 | 90 (295) / 100 | +1.0 / -0.6 |
| 1L | 37-36-28.4323N 122-22-58.5426W | 10.7 | 640 | +0.0 / -0.0 | +0.0 / -0.0 | +0.0 | +5.0 / -1.1 | 195 (640) / 0 | -10.3 / -2.1 |
| 19R | 37-37-35.3329N 122-22-14.1939W | 9.2 | 0 | -0.0 / +0.0 | -0.0 / +0.0 | +0.0 | -9.6 / +0.4 | 0 (0) / 0 | -1.6 / +1.8 |
| 1R | 37-36-22.7876N 122-22-51.7467W | 11.4 | 560 | +0.0 / -0.0 | +0.0 / -0.0 | +0.0 | +5.2 / -3.1 | 170 (558) / 0 | +0.1 / -2.9 |
| 19L | 37-37-38.4319N 122-22-1.599W | 10.5 | 0 | -0.0 / +0.0 | -0.0 / +0.0 | +0.0 | -9.0 / +0.7 | 0 (0) / 0 | +3.0 / +1.3 |
<!--END:runway_table-->

<!--BEGIN:threshold_table-->
| End | NASR displaced threshold: along / cross from runway end (m) | app threshold (end + disp along geo.js axis) − NASR DT (along / cross m) | NASR TORA / TODA / ASDA / LDA ft | position source, date |
|---|---|---|---|---|
| 28R | +91.5 / -0.0 | +0.0 / -0.0 | 11870 / 11870 / 11870 / 11236 | 3RD PARTY SURVEY, 2014/10/22 |
| 28L | +91.4 / +0.0 | +0.1 / -0.1 | 11381 / 11381 / 10981 / 10275 | 3RD PARTY SURVEY, 2014/10/22 |
| 1L | +195.1 / -0.0 | +0.0 / +0.0 | 7650 / 7650 / 7650 / 7010 | 3RD PARTY SURVEY, 2014/10/22 |
| 1R | +170.7 / -0.0 | +0.0 / +0.0 | 8650 / 8650 / 8650 / 8090 | 3RD PARTY SURVEY, 2014/10/22 |
<!--END:threshold_table-->

<!--BEGIN:length_table-->
| Runway | NASR published length | geodesic between NASR ends | app (geo.js planar frame) | app − geodesic |
|---|---|---|---|---|
| 10L/28R | 11870 ft = 3618.0 m | 3618.0 m | 3614.6 m | -3.43 m |
| 10R/28L | 11381 ft = 3468.9 m | 3469.0 m | 3465.6 m | -3.36 m |
| 1L/19R | 7650 ft = 2331.7 m | 2331.8 m | 2331.1 m | -0.63 m |
| 1R/19L | 8650 ft = 2636.5 m | 2636.5 m | 2635.8 m | -0.71 m |
<!--END:length_table-->

OSM `aeroway=stopway` ways (OSM uses them here for the paved areas beyond each end):

<!--BEGIN:stopway_table-->
| OSM way | nearest FAA end | length m | inner node along / cross from the end (m) | outer node along (m) | tags |
|---|---|---|---|---|---|
| way 510551650 | 10L | 269.8 | -0.3 / +0.2 | -270.1 | ref=10L/28R, surface=asphalt, width=61 |
| way 1065090263 | 10R | 231.4 | +1.5 / +0.5 | -229.9 | ref=10R/28L, surface=asphalt, width=61 |
| way 510551652 | 19L | 139.2 | +3.0 / +1.3 | -136.2 | ref=1R/19L, surface=asphalt, width=61 |
| way 23365562 | 19R | 134.6 | -1.6 / +1.8 | -136.2 | ref=1L/19R, surface=asphalt, width=61 |
| way 586154077 | 1L | 132.2 | -10.3 / -2.1 | -142.5 | length=2286, ref=1L/19R, surface=asphalt, width=61 |
| way 23365564 | 1R | 123.1 | +0.1 / -2.9 | -123.0 | length=2636, ref=1R/19L, surface=asphalt, width=61 |
| way 510551654 | 28L | 94.8 | +1.0 / -0.6 | -93.8 | ref=10R/28L, surface=asphalt, width=61 |
| way 510551656 | 28R | 91.4 | -1.7 / -0.5 | -93.2 | ref=10L/28R, width=61 |
<!--END:stopway_table-->

Findings:
1. **`RWY_ENDS` is correct.** Observed: all 8 ends equal NASR (cycle 2026-09-03) and AirNav ("FAA information effective 03 September 2026") to 0.0 m. The elevations are identical. The displaced lengths 300/300/640/560 ft equal `DISPLACED_THR_LEN`. The app's threshold (end + displacement along its axis) lands within 0.1 m of NASR's surveyed displaced-threshold point. NASR's position source for every end is "3RD PARTY SURVEY", 2014/10/22.
2. **X-Plane runway ends are 1–10 m off along the axis.**
   - Values: 10L −4.8, 19R −9.6, 19L −9.0 (beyond the end); 1L +5.0, 1R +5.2 (inside the runway). Cross offsets are up to 3.1 m.
   - X-Plane displacements: 28L/28R 90 m, which is 295 ft against FAA 300 ft; 1L 195 m and 1R 170 m match.
   - Do not use X-Plane runway geometry.
3. **OSM runway ends are within 3 m, except 1L**, where the OSM runway way extends 10.3 m beyond the NASR end.
   - Its length tags are stale: 10R/28L `length=3231` against NASR 11,381 ft = 3,469 m; 1L/19R `2286` against 2,332 m.
4. **Blast pads.** The FAA Airport Diagram (AL-375, 2609) draws chevron-hatched pavement beyond **10L and 10R**, and shorter ones beyond 28R and 28L. It draws EMAS at all four 1/19 ends. Observed on the chart; crops are in `refs/cache/xcheck/faa/ad_crop_*.png`.
   - Lengths:
     - measured by hand on a 300-dpi render of the chart, at about 2.67 m/px from the 10L–28R length (approximate): 10L ≈ 260 m, 10R ≈ 240 m, 28R ≈ 90 m;
     - OSM: 270 / 231 / 91 / 95 m;
     - X-Plane blast pads: 250 / 250 / 100 / 100 m.
   - The app's `END_ZONES` (`js/live/airport.js`) has 108 m pads at 28L/28R and nothing at 10L/10R. HANDOFF §4 says "nothing is visible in the imagery".
   - Recommendation: check the 10L/10R ends on the imagery again, and add blast pads (type 1) with measured lengths. The references agree on 230–270 m.
   - The 28L/28R pads: ours 108 m against OSM 91–95 and X-Plane 100. Re-measure.
   - At the 1/19 ends, OSM's 123–139 m "stopways" cover the EMAS areas. Ours are the 10.7 m setback plus 111–136 m beds (HANDOFF §2), which is consistent. X-Plane has no pad there.
5. **Approach lights, PAPI and TDZ** (next to the runway ends, from NASR `APT_RWY_END.csv`):
   - **Approach lights.** NASR lists 28R ALSF2, 28L MALSR and 19L MALSF, and no approach light system at 10L, 10R, 1L, 1R or 19R. The FAA diagram shows light bars only at 28R/28L, and X-Plane codes 2, 8 and 9 at exactly those three ends.
     - `js/geo.js` `APPROACH_LIGHTS` has 8 entries: 10L ALSF2, 10R MALSR, and MALSF at 1L, 1R and 19R, in addition to the three real ones.
     - `js/anim/lights.js` draws all 8, so **5 approach-light systems are drawn that do not exist**.
   - **VGSI.** NASR shows a 4-light PAPI on the left at 10L, 10R, 19L (3.00°), 19R (**3.15°**), 28R (3.00°) and 28L (**2.85°**), and no VGSI at 1L or 1R.
     - The app builds PAPIs only at 28L/28R, with the same bands for both.
     - X-Plane has all six at 3.00°. It labels 10R "VASI", although the type code is 2 = PAPI-4L.
   - **TDZ lights.** NASR shows them only at 28R and 19L. The AD says "TDZL/RCLS Rwys 19L and 28R". The app builds TDZ bars at both 28 ends.
   - These are for the owner of `js/`. I changed nothing.
6. **Frame scale.** The app's planar length is 3.4 m shorter than the geodesic length for 10/28, and 0.6–0.7 m shorter for 1/19. The cause is the east–west scale in `js/geo.js` (§3).
   - The frame is used consistently: the SFO Museum geometry, the imagery survey and `RWY_ENDS` all use the same formula. So nothing is misaligned; the whole scene is 0.12 % narrow east–west.
   - Optional fix: use the WGS-84 metres-per-degree values at the ARP (lat 110 989 m, lon 88 285 m [corrected by verifier: was 88 266]), and re-export every world-coordinate file through lat/lon in one step.

## 7. Licences and what they mean for us

**X-Plane Scenery Gateway.** Observed:
- The downloaded pack's `README.txt`, written by WorldEditor's Gateway export (xptools `src/WEDImportExport/WED_GatewayExport.cpp`, lines 570–574 at a3725c8), says:
  > "The scenery packs shared via the X-Plane Scenery Gateway are free software; you can redistribute it and/or modify it
  > under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of
  > the License, or (at your option) any later version. See the included COPYING file for complete terms."
- The pack includes the GPL v2 text as `COPYING`.
- The Gateway API page (https://gateway.x-plane.com/api) sets no licence but asks:
  > "Please note: There is currently no metering on the Gateway API, but we ask that you be considerate of our server load
  > and avoid making unnecessary requests."
- *Not found:* a Gateway terms-of-service page. `/terms` and `/about` return 404, and the "About the Airport Scenery Gateway" article (https://developer.x-plane.com/article/airport-scenery-gateway/) has no licence text.

  *Inferred:* if X-Plane positions or names were copied into our shipped data, that data would become a work based on
  GPL material. Distributing it would require GPL terms and source availability. X-Plane is the less accurate
  source anyway (§4–6), so **use it only for checking**. That creates no obligation.

**OpenStreetMap.** Observed on https://www.openstreetmap.org/copyright:
> "OpenStreetMap is open data, licensed under the Open Data Commons Open Database License (ODbL) by the OpenStreetMap
> Foundation (OSMF). … You are free to copy, distribute, transmit and adapt our data, as long as you credit OpenStreetMap
> and its contributors. If you alter or build upon our data, you may distribute the result only under the same license."

> "Where you use OpenStreetMap data, you are required to do the following two things: Provide credit to OpenStreetMap by
> displaying our attribution notice. Make clear that the data is available under the Open Database License."

The Overpass response itself states: "The data included in this document is from www.openstreetmap.org. The data is made available under ODbL."

ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/):
- "Derivative Database" includes "Extracting or Re-utilising the whole or a Substantial part of the Contents in a new Database".
- §4.3 (Produced Work notice):
  > "if you Publicly Use a Produced Work, You must include a notice associated with the Produced Work reasonably calculated to make any Person that uses, views, accesses, interacts with, or is otherwise exposed to the Produced Work aware that Content was obtained from the Database … and that it is available under this License."
- §4.4 (Share alike):
  > "a. Any Derivative Database that You Publicly Use must be only under the terms of: i. This License; …"
  > "c. … A Derivative Database is Publicly Used and so must comply with Section 4.4. if a Produced Work created from the Derivative Database is Publicly Used."
  > "d. … You must not add Contents to Derivative Databases under Section 4.4 a that are incompatible with the rights granted under this License."
- §4.6: if you publicly use a Derivative Database or a Produced Work from one, you must offer the recipients "the entire Derivative Database" or "a file containing all of the alterations … or the method of making the alterations".

OSMF guidelines (https://osmfoundation.org/wiki/Licence/Community_Guidelines/):
- Substantial:
  > "Less than 100 Features" is regarded as not Substantial "provided that the extraction is one-off and not repeated over time".
  > Also: "The systematic extraction of all eating places within an area … would be considered to be systematic."
- Horizontal Map Layers (endorsed 2014-06-06):
  > "If you use OpenStreetMap data along with non-OpenStreetMap data for a given Feature Type, then the share-alike condition would apply regardless of whether some data for that Feature Type is in a different layer."
  > It also lists "You add restaurants in one area from non-OpenStreetMap data based on comparison with OpenStreetMap data in other layers" among the cases where you DO need to share.

What this means (*inferred; not legal advice, the owner decides*):
- **Checking only** (what this report and `tools/xcheck` do): the report quotes a few OSM refs and offsets. It is a
  Produced Work and should carry "© OpenStreetMap contributors, ODbL" (below). No data is copied into `data/`.
- **Copying OSM stand positions or refs into `data/sfo_stands.json`.** All 89 or more stands of one systematic kind count as a Substantial extract,
  so the file becomes a Derivative Database. [corrected by verifier: the guideline does not say this for fewer than 100 Features. It says "The OpenStreetMap community regards the following as being not Substantial … provided that the extraction is one-off and not repeated over time for the same or a similar project. Less than 100 Features." The "systematic" sentence qualifies only the ">100 Features" exception ("More that [sic] 100 Features only if the extraction is non-systematic …"). A one-off copy of 89 stand positions (89 Features) would therefore be *insubstantial* by the guideline. It becomes Substantial when the copy reaches 100 or more Features: for example the stands plus the 133 jet bridges, or the 118 referenced lead-ins, or the stands we lack added in. It also becomes Substantial when the copy is repeated or refreshed over time ("we regard repeated small extractions as one big extraction"). Source: https://osmfoundation.org/wiki/Licence/Community_Guidelines/Substantial_-_Guideline (endorsed 2014-06-06), re-fetched 24 Sep 2026. Not legal advice; the owner decides.] Because the app shows it (a public Produced Work), the file must be offered under
  ODbL, with attribution in the app.
  - Mixing in our stands measured on **Google** imagery would put content derived from that imagery into the same Derivative Database. Google's terms were not reviewed here; CLAUDE.md already treats the imagery as licensed and reference only, and those terms may not allow relicensing under ODbL. That would conflict with ODbL §4.4 d. The horizontal-layers guideline makes the mix count as one Feature Type.
  - So the clean options are:
    - (a) stands entirely from OSM (plus our own ADS-B evidence), published under ODbL with attribution;
    - (b) stands entirely from our own measurements, using OSM only to flag errors and re-measuring on the imagery. The guideline's "based on comparison" example makes this a grey zone; ask the owner.
- **Our own ADS-B + SFO evidence** is independent of both and can be used freely for positions. Stand names come from SFO: DataSF is PDDL, and flysfo has no terms (gate_truth.md). Such positions are observations of
  our own recording.

**Attribution notice for this document:** Contains information from OpenStreetMap
(https://www.openstreetmap.org/copyright), made available under the ODbL
(https://opendatacommons.org/licenses/odbl/1-0/). Contains information derived from the X-Plane Scenery Gateway KSFO
scenery pack 112022 (https://gateway.x-plane.com/), GPL v2 or later. The overlay figures `refs/cache/xcheck/fig/*.png`
embed OSM and X-Plane geometry and are kept out of the repository.

## 8. Other X-Plane and OSM content (parsed, not yet compared)

All of this is saved in `refs/cache/xplane/ksfo_apt_parsed.json` and `refs/cache/osm/ksfo_osm_parsed.json`:

- **X-Plane** (GPL):
  - the taxi routing graph (1201/1202), with taxiway names and 408 runway active-zone flags (1204);
  - 326 sign texts (row 20, in X-Plane sign syntax, e.g. `{@L}S3{@R}10L{@@,@L}S3`);
  - 2,392 painted and lit linear features with line-type codes (110–120);
  - 8 windsocks, a tower viewpoint (row 14, 220 ft), 52 ground-truck parking spots (1400) and frequencies.
    - Frequencies: CLNC DEL 118.2, GND 121.8 and 128.65, TWR 120.5, ATIS 113.7, 115.8, 118.85.
    - The FAA diagram's box shows the same values, except that the diagram lists only 121.8 for ground.
- **OSM** (ODbL):
  - 177 `holding_position` features (90 nodes, 87 ways), 244 taxiways and taxilanes, 18 aprons, 10 terminal outlines, 1 control tower;
    - the tower is tagged `height=67.36`, `min_height=60`;
  - 4 navaids and 1 windsock.

Obvious next checks, not done here:
- our hold bars (`sfo_details`) against OSM holding positions and X-Plane 1204 zones;
- our sign texts against X-Plane row 20. Original sources (the FAA airport diagram, SFO's own documents) are to be preferred over X-Plane.

## 9. Open questions and what is not verified

1. **The meaning of OSM's end node.** It is closer to the nose tip (1.6–2.9 m behind) than a nose wheel would be (§4.3). Along-track positions therefore need imagery or ADS-B, not OSM.
2. **Which lead-in is which suffixed SFO stand.** B5S, B11S, B16S, C9V, A1V, A4T, A13V, E10U, E11U, E13T and G13S. OSM has duplicate refs at B5, B11 and B16. Not verified.
3. **Remote, cargo and maintenance stands.** SFO names (2-x, 6-x, 9-x, 12-x, 41-xx) cannot be tied to positions without ADS-B at the published stand. OSM has only `50-6`, `50-7` and `50-8` named.
4. **Two-bridge stands.** Only the imagery can settle this (§4.7).
5. **The 10L/10R pavement.** It is in all three references, but HANDOFF says it is not visible in our imagery. Check which screenshots cover the 10L/10R ends.
6. **ADS-B sample.** It is 10 stands overnight. Re-run later for daytime coverage. Each row is a single aircraft; the NACp was 9–10. [corrected by verifier: the samples are mostly NACp 9–10, but not all. At B16, 4 of 201 reports have NACp 0, which explains the 34.9 m spread. At B5, the 13 reports include NACp 8 and reports without NACp. The medians are robust: B16 recomputed from NACp ≥ 8 reports only is still 1.83 m from OSM B16.]
7. **X-Plane codes.** Line types 10, 12, 24, 30, 60, 62 and 63 and jetway sizes 10, 11 and 12 are undocumented.
8. **The OSM-derived-data decision (§7).** For the owner: option (a), all OSM under ODbL, or (b), own measurements only.
9. **Nose-to-nose-gear distances per type** were not extracted from the manufacturers' airport-planning documents. The WED values in §2 are X-Plane's schematic ones.

## 10. Reproduce

```bash
sh tools/xcheck/run_all.sh          # everything below, in order
python3 tools/xcheck/fetch_osm.py   # Overpass -> refs/cache/osm/overpass_ksfo_latest.json (+ .meta.json); rejects mirrors > 7 days stale
python3 tools/xcheck/fetch_xplane.py   # Gateway airport -> recommended pack -> refs/cache/xplane/apt_<id>.dat (+ README/COPYING)
python3 tools/xcheck/parse_osm.py      # -> refs/cache/osm/ksfo_osm_parsed.json
python3 tools/xcheck/parse_aptdat.py   # -> refs/cache/xplane/ksfo_apt_parsed.json (1300/1301, 1500, 1201-1206, 100, 110-120, 20, 21, 19, 14, 1050-1056)
python3 tools/live/gatecheck.py check --every 120 --json refs/cache/xcheck/gatecheck_every120.json   # ADS-B vs SFO (read-only use)
python3 tools/xcheck/adsb_evidence.py  # -> refs/cache/xcheck/adsb_evidence.json, tables_adsb.md
python3 tools/xcheck/compare_stands.py # -> refs/cache/xcheck/stands_result.json, tables_stands.md
python3 tools/xcheck/compare_runways.py   # needs refs/cache/xcheck/faa/03_Sep_2026_APT_CSV.zip + airnav_KSFO.txt (run_all.sh fetches)
python3 tools/xcheck/figs.py           # overlays -> refs/cache/xcheck/fig/stands_<area>.png (not for redistribution)
python3 tools/xcheck/make_report.py    # refresh the generated tables in this file
```

Parameters to adjust for a new NASR cycle:
- the file name in `compare_runways.py` / `run_all.sh`;
- `MATCH_R`, `MATCH_H`, `TOL_CROSS`, `TOL_HDG` at the top of `compare_stands.py`.

## Verification (adversarial check)

This check was done on 24 Sep 2026, 09:40–10:10 UTC, by an independent verifier agent. Every cited source was fetched again where possible and the scripts were re-run in a scratch copy, so nothing in `refs/cache/xcheck` was overwritten. Nothing in `data/`, `js/` or `tools/` was changed.

**Results in brief.**
- The core data claims hold. These are:
  - OSM counts and refs;
  - the ADS-B vs OSM distances;
  - the X-Plane pack, its counts and its GPL notice;
  - the WED nose-wheel convention;
  - the NASR runway ends, lights and PAPIs;
  - the licence quotes;
  - every generated table (bit-identical on re-run).
- 7 statements were corrected inline, marked [corrected by verifier], and one note was added (the 40 vs 42 `inf` count). The most important is a licence inference: 89 stands are below the OSMF 100-Feature threshold. The others:
  - the m/deg numbers;
  - the ANT = 0.2·L conclusion;
  - F10 "sits on" F8;
  - the blanket +5.7 m stopgap;
  - the OSM along-offset range;
  - the NACp range.

**How the checks were done.**
- Scripts were re-run in a scratch copy:
  - `compare_stands.py`: all 10 result keys and the stands table are identical;
  - `compare_runways.py`: the result is identical.
- These were computed independently, without the agent's code:
  - OSM ways from the main OSM API (api.openstreetmap.org/api/0.6/way/{id}/full, 25 ways);
  - ADS-B medians from the raw recording (`tools/live/recio.py`);
  - a fresh flysfo snapshot;
  - the Gateway API;
  - the NASR zip (sha256 identical to the cache);
  - the FAA diagram (sha256 identical to the cache);
  - AirNav;
  - the OSM wiki API;
  - the licence pages.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Two Overpass responses: 289 `parking_position` (287 ways + 2 nodes), 118 with `ref`, 133 `jet_bridge` (83 with ref). Database 08:41:02Z and 09:07:42Z, "same results" | **Confirmed** | Both cached responses parsed: identical element sets, 4,594 elements each. The OSM API returns the same version and identical geometry for every way checked (B5, B16, B18, B21, B23, B24, B25, B26, C9, C10, C11, G5, the 8 stopways and the tower). A fresh Overpass run failed: maps.mail.ru and overpass-api.de returned 504, and kumi.systems is stale (2026-05-06, 295 positions, i.e. 6 deleted since). |
| 2 | (Agent summary only) "4,565 airfield and building features" | **Refuted** (not in report body) | The saved responses hold 4,594 elements (357 nodes, 4,198 ways, 39 relations); `overpass_ksfo_latest.meta.json` says `"elements": 4594`. |
| 3 | OSM provenance: last edits 2019-10-16…2026-04-08. Necessarycoot72 edited 166 of the 171 unreferenced lead-ins, on 2022-09-20. 8 duplicate refs. Only non-gate refs are 50-6/7/8, none in the AODB remote list | **Confirmed** | Recount of `ksfo_osm_parsed.json`. Remote list in `gates_report.json`: 2-x, 6-x, 9-x, 12-x, 41-xx, G104, G105. |
| 4 | OSM wiki quote ("Put a node where the nose wheel stops." … "the last node of the way should be where the nose wheel is parked."), rev. 2785188, 2024-12-05 | **Confirmed** | https://wiki.openstreetmap.org/w/api.php (Tag:aeroway=parking_position). Current revision is 2785188, 2024-12-05T00:12:06Z (Maro21); quoted text is verbatim. |
| 5 | Gateway recommended pack 112022: uploaded 2026-09-07 by "Julian", "XSG-17643 / Gates renamed.", WorldEditor 2.7.2-r1 | **Confirmed** | https://gateway.x-plane.com/apiv1/airport/KSFO returns `recommendedSceneryId` 112022. https://gateway.x-plane.com/apiv1/scenery/112022 returns dateUploaded 2026-09-07T03:41:40Z, userName Julian, and that comment. The zip sha256 is identical to the cache. `apt.dat` line 2: "1200 Generated by WorldEditor 2.7.2-r1". |
| 6 | apt.dat content: 136 ramp starts (117 gate, 19 tie_down; A11 B15 C76 D14 E17 F3; all airline); 126 jetways, absent from the bare KSFO.dat; 534/437 taxi nodes/edges (383 E, 6 D, 48 runway); 408 active-zone rows; 46 pavements; 2,392 line features; 326 signs; 6 PAPIs; 8 windsocks; 15 frequencies; 52 truck spots; tower at 220 ft | **Confirmed** | Counted independently with my own parser on the freshly downloaded pack. Line-segment codes are 20→3,030, 60→1,390, 24→1,370, 53→732, 57→173, 54→50, plus 30/12/63/10/62. Jetway size codes 10/11/12 occur 1+25+1 = 27 times. |
| 7 | apt.dat 12.00 spec says only "Latitude of location in decimal degrees" and "Heading (true) of airplane positioned at this location". Last updated 22 Dec 2023. Jetway sizes 0–3 only. Line types 10, 12, 24, 30, 60, 62, 63 not in the table | **Confirmed** | https://developer.x-plane.com/article/airport-data-apt-dat-12-00-file-format-specification/ was re-fetched: "Last updated December 22, 2023", with `dateModified` 2023-12-22. The line table lists 0–9, 51–59, 20–22 and 101–108. The jetway size code is "0 = tunnel length 11–23m … 3 = 20–47m". |
| 8 | WED `WED_RampPosition::GetTips` reads the location into `nosewheel_loc`, with nose_offset A 1.0, B 2.7, C 4.7, D 9.5, E 8.2, F 8.8. For `misc` the offset is fuse_len/2. Lines 154–184 at a3725c8 | **Confirmed** | https://raw.githubusercontent.com/X-Plane/xptools/a3725c8f5ed6d9681573496ab0153e550d54cd09/src/WEDEntities/WED_RampPosition.cpp, lines 154–184 verbatim. |
| 9 | Gateway packs are GPL v2 or later. The README text is written by `WED_GatewayExport.cpp` lines 570–574, and COPYING is GPL v2 | **Confirmed** | The pack README text matches the quote verbatim, and COPYING is "GNU GENERAL PUBLIC LICENSE Version 2, June 1991". Same commit, `src/WEDImportExport/WED_GatewayExport.cpp` lines 570–574. |
| 10 | Gateway API "no metering … be considerate" quote. There is no Gateway ToS: /terms and /about return 404, and the About article has no licence text | **Confirmed** | https://gateway.x-plane.com/api quote is verbatim. It continues: "(For instance, if you start making frequent requests to get all 34,000 airports in the database, we'll have to cut you off!)". /terms and /about return 404. The sitemap has no terms link. https://developer.x-plane.com/article/airport-scenery-gateway/ and /register contain no GPL or licence text. The cached "x-plane-scenery-gateway-terms-of-service" page is a 404 too. |
| 11 | NASR (APT CSV, effective 2026/09/03) end coordinates, elevations, displacements, "3RD PARTY SURVEY" 2014/10/22. `RWY_ENDS` = NASR to 0.0 m | **Confirmed** | Re-downloaded https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip (sha256 d5e4c999…, identical). Geodesic geo.js − NASR is ≤ 0.001 m at all 8 ends. Elevations and `DISPLACED_THR_LEN` are identical, and TORA/TODA/ASDA/LDA match the threshold table. |
| 12 | NASR lighting: approach lights only 28R ALSF2, 28L MALSR, 19L MALSF. PAPI-4L at 10L, 10R, 19L (3.00), 19R (3.15), 28R (3.00), 28L (2.85); none at 1L/1R. TDZ only at 28R and 19L | **Confirmed** | `APT_RWY_END.csv` fields APCH_LGT_SYSTEM_CODE, VGSI_CODE, VISUAL_GLIDE_PATH_ANGLE and TDZ_LGT_AVBL_FLAG. |
| 13 | The app draws 8 approach-light systems (5 nonexistent), PAPIs only at 28L/28R with identical bands, and TDZ bars at both 28 ends | **Confirmed** | `js/geo.js` `APPROACH_LIGHTS` has 8 entries. `js/anim/lights.js` `buildAirfieldLights` loops over all of them and is used by the live app through `js/live/lights.js` → `app.js`. PAPI and TDZ are built only for `name.startsWith('28')`. |
| 14 | FAA diagram AL-375, valid 03 SEP–01 OCT 2026: chevron pads beyond 10L/10R and short ones beyond 28L/28R; EMAS at the 1/19 ends; "TDZL/RCLS Rwys 19L and 28R"; frequency box | **Confirmed** | https://aeronav.faa.gov/d-tpp/2609/00375ad.pdf is byte-identical to the cache. Text: "AL-375 (FAA)", "SW-2, 03 SEP 2026 to 01 OCT 2026", "TDZL/RCLS Rwys 19L and 28R", "118.2 CLNC DEL 121.8 GND CON 120.5 269.1 SAN FRANCISCO TOWER 113.7 115.8 118.85 D-ATIS". Crops inspected. Pad lengths (≈260/240/90 m) were not re-measured. |
| 15 | X-Plane runway ends 1–10 m off (10L −4.8, 19R −9.6, 19L −9.0, 1L +5.0, 1R +5.2 …). Disp 28L/28R 90 m, 1L 195 m, 1R 170 m. Blast pads 10L/10R 250 m, 28L/28R 100 m. Approach codes 2/8/9 at 28R/28L/19L. All PAPIs 3.00°; 10R named "VASI" with code 2 | **Confirmed** | Computed independently from the pack's row 100/21 with pyproj; all offsets match to 0.1 m. Spec: 2 = ALSF-II, 8 = MALSR, 9 = MALSF; row 21 code 2 = PAPI-4L. |
| 16 | OSM stopway ways (ids, lengths 269.8/231.4/139.2/134.6/132.2/123.1/94.8/91.4 m, tags). Stale runway `length` tags 3231 and 2286 | **Confirmed** | OSM API geodesic lengths agree to ≤ 0.2 m. Runway ways 23365560 and 1333615088 carry `length=3231`; 586154078 and 1333615087 carry `length=2286`. |
| 17 | `END_ZONES`: 108 m pads at 28L/28R, nothing at 10L/10R; HANDOFF says "nothing is visible in the imagery" | **Confirmed** | `js/live/airport.js` lines 183–187 (RWY order from `js/world/airfield.js`); `docs/HANDOFF.md` line 88. |
| 18 | Frame: 111 320·cos φ = 88 157 against WGS-84 88 266 m/deg, 0.12 % short | **Refuted (numbers); ratio confirmed** — corrected in §3 and §6 | At φ = 37.6188056°, 111 320·cos φ = 88 175.4 m/deg and WGS-84 (π/180)·N·cos φ = 88 285.2 m/deg. The ratio is −0.124 %. The 3.4 m 10/28 shortfall (length table) is unaffected. |
| 19 | ADS-B evidence on 10 SFO-published stands: OSM same-ref position 0.4–2.2 m from the aircraft at 8, and 5.0/6.0 m at C11/G5 (first node of backwards ways). Cross ≤ 1.9 m on the 7 rows with heading. X-Plane right only at G5. Ours: G5 OK, B26 3.7 m, the others off | **Confirmed** | Independent medians from the raw adsb.fi/adsb.lol files, gs < 1 kt, on ground, T−300…T. Geodesic distances to OSM-API geometry: B16 1.83, B18 1.76, B21 0.79, B23 2.23, B24 0.30, B26 1.76, B5 0.94, C10 1.20, C11 4.96 (first node), G5 6.01 (first node). In our stand frames: B16 −15.8 / +16.6°, B18 +5.0, B21 +6.0, B23 +5.1, B24→B25 +26.1, B26 +3.7, B5 −0.5 / −25.6°, C10 −5.6 / −22.8°, C11 −34.1 / −48.5°, G5 +2.2 / −0.3° (all within 0.1 m of the report). |
| 20 | SFO stand windows: AAL177 B16, JBU515 B21, AAL2856 B23, AAL2506 B24, JBU413 B5, ACA738 C10, DAL2635 C11, UAL189 G5. B18 and B26 are "occupancy" rows | **Confirmed** (6 re-fetched, 2 from cache) | A fresh https://www.flysfo.com/flysfo/api/flight-status fetch (09:58Z) confirms the B16, B21, B5, C10, C11 and G5 windows covering each T. It also confirms the B18 (JBU277/JBU116) and B26 (AAL2522/AAL2116) allocations. AAL2856/B23 and AAL2506/B24 have aged out of the live feed and were confirmed only in the cached 07:32Z/08:53Z snapshots. Caveat: B18 and B26 rest on our own matcher's stand choice (the transponder sent no callsign), so they are weaker evidence. |
| 21 | NACp 9–10 on all ADS-B rows | **Refuted (minor)** — corrected in §9 | B16: 4 of 201 reports have NACp 0 (hence the 34.9 m spread). B5 includes NACp 8 and missing values. The medians are unaffected (B16 with NACp ≥ 8 only: 1.83 m). |
| 22 | Our 43 `obs` stands: median cross +0.3 m, median abs 1.5 m. 40 `inf`: +5.7, abs 6.3, 25 > 3 m right | **Confirmed with a note** — note added in §1 | `obs` values reproduce exactly. For `inf`, 42 stands have an OSM best match (median +5.6, abs 6.45, 25 > 3 m). The quoted 40 / +5.7 / 6.3 reproduce only with an undocumented filter, \|cross\| ≤ 20 and \|Δhdg\| ≤ 25°. |
| 23 | S1 stopgap: shift each `inf` stand +5.7 m right | **Partly refuted** — caveat added | It would make 16 of the 42 matched `inf` stands worse. Within 3 m of OSM goes only from 11 to 14; median abs cross 6.45 → 4.35 m. |
| 24 | S3: "no reason to change ANT = 0.2·L" | **Refuted** — corrected in §5.1 and §4.3 | The observed antenna offsets are 4.9 / 1.8 / 9.8 m (B23 A321, B26 A321, G5 B77W). `ANT`·L is 8.9 / 8.9 / 14.8 m (`js/live/traffic.js` line 19; `js/aircraft/types.js` L). All three are shorter by 4.0–7.1 m, so either ANT is too large or our along positions are off. |
| 25 | OSM stop nodes "only 1.6–2.9 m behind our nose tips" | **Imprecise** — corrected in §4.3 | Per-class obs medians run +1.4 … −2.9 m; the range quoted is two medians (all/obs, EL/obs). |
| 26 | Verdict counts (20 / 18 / 15 / 10 / 9 / 7 / 5 / 3 / 1 / 1). 79 of 89 stands have a same-name OSM lead-in in radius. Bridges: 37 all-agree, 20 OSM+XP-vs-us; XP jetway base median 9.4 m, 18 of 117 ≤ 5 m. 64 backwards ways | **Confirmed** | Re-run is identical. Recounted from `stands_result.json`: name verdict "same as OSM" = 79, and any in-radius candidate with our own name = 79. Backwards ways follow the script's heuristic; the C11 and G5 cases are consistent with the ADS-B positions. |
| 27 | Stand classes: B5 and B16 are class B and refuse the A321 SFO parks there | **Confirmed** | `data/sfo_stands.json`: B5 and B16 are `cls: B`. `CLASS_MAX.B.span` is 28.5 m, against A321 ≈ 35.8 m. gatecheck: "class-rejected; geometry matches B5". |
| 28 | C11 misnamed: our "C11" sits on OSM C9 (1.4 m); SFO's C11 is at the pier tip | **Confirmed** (the SFO C9 part is inferred) | ADS-B at SFO C11: 34.1 m across our C11 and 4.96 m from OSM C11's first node. OSM C9 is 1.4 m from our C11. That SFO calls that spot "C9" is inferred from OSM, which matched SFO on 10 of 10 checks; no aircraft at SFO C9 was observed. |
| 29 | F10 "sits on OSM and X-Plane's F8" | **Overstated** — corrected in §4.5 and §5.2 | Distances were computed from the nose-wheel estimate. OSM F8 is 14.0 m from our F10 and OSM F10 is 22.8 m. X-Plane "Gate F8" is 8.8 m from OSM F10 and 11.6 m from OSM F8. Our F8 ↔ OSM F7 is 1.1 m (solid). |
| 30 | X-Plane names shifted on whole faces (A-west, A-east, D rotunda, C, B-west) | **Confirmed**, independently of our stands | X-Plane names compared directly with the nearest OSM ref (≤ 15 m): 25 of 68 disagree. Examples: A9 A10→A5, A12→A9, A15→A10, A11→A8, A13 A14→A11; C3→C5, C5→C7, C7→C9, C9→C11, C11→C10; D11→D10 … D18→D16; B24→B25, B25→B26, B26 B27→B20; X-Plane "B19 B20" is nearest OSM B16 (16.6 m). Not in the report: E2→E3, E3→E6, E6→E8, and G11 G12→G8, G13 G14→G10. The G and E faces are shifted as well. |
| 31 | X-Plane keeps F1, F2, F3, F3A, F4, E1 (not on SFO maps) and C2, D17, D18 (on the maps, no ops) | **Confirmed** | X-Plane has ramp starts named these. The SFO map list (A1–A15, B1–B27, C1–C11, D1–D12, D14–D18, E2–E13, F5–F22, G1–G14) and the per-area DataSF counts are from `refs/cache/gate_truth/gates_report.json`, already verified in gate_truth.md. |
| 32 | Of the contact gates SFO uses, OSM lacks only A4, B8, G12, G14 | **Confirmed** | Set difference of DataSF ∪ AODB (suffix removed) against the OSM refs gives A4, B8, G12, G14, plus the remote G104/G105. |
| 33 | "Gates renamed" pack names come from an older numbering | **Unverifiable** (inference) | Nothing in the pack or the API says so. The shift itself is confirmed (#30). |
| 34 | D11–D15 fix "also explains/shortens the 54 m D10 bridge" | **Unverifiable** (inference) | HANDOFF §3 does flag D10 at 54 m. D10 has no OSM counterpart within 25 m, and X-Plane "D11" is +15.1 m along. Plausible, but not tested. |
| 35 | OSM © page, ODbL §§ definitions, 4.3, 4.4 a/c/d and 4.6, Overpass notice | **Confirmed** | https://www.openstreetmap.org/copyright and https://opendatacommons.org/licenses/odbl/1-0/ re-fetched; all quoted sentences found verbatim (4.6 starts with capitals "The entire…"/"A file…"). The Overpass `osm3s.copyright` string is verbatim. |
| 36 | OSMF Substantial guideline quotes; Horizontal Map Layers guideline quotes, endorsed 2014-06-06 | **Quotes confirmed** | https://osmfoundation.org/wiki/License/Community_Guidelines/Substantial_-_Guideline and https://osmfoundation.org/wiki/License/Community_Guidelines/Horizontal_Map_Layers_-_Guideline re-fetched; both say "Endorsed by the OSMF board 2014-06-06". |
| 37 | Inference: "All 89 or more stands of one systematic kind count as a Substantial extract" → the file becomes a Derivative Database | **Refuted** — corrected in §1 and §7 | The guideline regards "Less than 100 Features" as not Substantial when extracted one-off. The "systematic" sentence applies only to the >100-Feature exception. 89 stands, copied once, fall under that threshold. Copying ≥ 100 Features (stands + bridges, all 118 refs, …) or refreshing repeatedly would be Substantial. |
| 38 | DataSF is PDDL | **Confirmed** | https://data.sf.gov/api/views/chfu-j7tc.json gives `licenseId` PDDL ("Open Data Commons Public Domain Dedication and License"). |
| 39 | Frequencies (X-Plane): CLNC 118.2, GND 121.8 and 128.65, TWR 120.5, ATIS 113.7/115.8/118.85. The diagram lists only 121.8 for ground | **Confirmed as stated; verifier note** | Verified in the pack and on the diagram. However, AirNav ("FAA information effective 03 September 2026", https://www.airnav.com/airport/KSFO) lists "SAN FRANCISCO GROUND: 121.8 124.25". X-Plane's 128.65 GND is corroborated by neither FAA-derived source, so do not use X-Plane frequencies for the ATC toggle. |
| 40 | OSM tower `height=67.36`, `min_height=60` | **Confirmed** | OSM API way 554547693 v3. |
| 41 | The overpass-api.de instance timed out; another instance was 2 months stale | **Unverifiable** (consistent) | It could not be reproduced at the agent's time. In this check overpass-api.de and maps.mail.ru gave 504/reset, private.coffee gave 504, and kumi.systems returned data dated 2026-05-06. |

Verifier's scratch outputs are in the session scratchpad and are not part of the repo.
