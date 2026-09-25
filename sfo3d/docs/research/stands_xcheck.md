# Stand layout and runway ends cross-checked against OpenStreetMap, the X-Plane Scenery Gateway and the FAA

Research for the "Parking" and "Airport fidelity" objectives. It checks our 89 contact stands (`data/sfo_stands.json`:
43 `obs`, 46 `inf`, 117 bridges; provenance `tools/sat/stand_defs.py`) and the runway ends in `js/geo.js`
(`RWY_ENDS`) against independent sources, quotes what each source's coordinates mean and under which licence it can be
used, classifies every disagreement and recommends corrections. Nothing in `data/` or `js/` was changed.

Written 24 Sep 2026 (UTC) by a research agent. Tools: `tools/xcheck/*.py` (section 10). Third-party downloads are in
`refs/cache/osm/`, `refs/cache/xplane/` and `refs/cache/xcheck/` (gitignored).
**Observed** = read in a file or response I fetched (URL given). **Inferred** = my interpretation. **Not verified** =
could not be checked. Data versions: <!--STAMP-->OSM database 2026-09-24T09:07:42Z (Overpass https://maps.mail.ru/osm/tools/overpass/api/interpreter, fetched 20260924T091047Z); X-Plane Gateway scenery pack 112022; FAA NASR cycle 2026/09/03; AirNav 'FAA information effective 03 SEPTEMBER 2026'; ADS-B/SFO evidence: 191 stands (11 snapshots, newest flysfo_api_flight-status_20260925T020353Z.json.gz)<!--/STAMP-->

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
| OSM | all `obs` stands | 68 | -0.06 / -0.13 | 0.8 → 0.8 |
| OSM | 03dcd4ae | 8 | -0.1 / -0.2 | 0.7 → 0.7 |
| OSM | 151ec51d | 11 | +0.4 / -0.8 | 0.2 → 0.1 |
| OSM | 39176bb8 | 14 | -0.5 / -0.3 | 1.6 → 1.5 |
| OSM | ? | 21 | +0.0 / +0.0 | 0.0 → 0.0 |
| OSM | b1d51b0f | 22 | +0.0 / +0.0 | 0.0 → 0.0 |
| OSM | bf5c7afc | 13 | +0.3 / -0.3 | 0.9 → 0.8 |
| OSM | c235f3b8 | 10 | +0.0 / +0.0 | 0.0 → 0.0 |
| OSM | d82848c4 | 9 | +0.0 / +0.0 | 0.0 → 0.0 |
| X-Plane | all `obs` stands | 33 | +1.26 / +0.37 | 2.5 → 2.3 |
| X-Plane | 03dcd4ae | 7 | +4.8 / -2.4 | 4.5 → 2.6 |
| X-Plane | 151ec51d | 11 | +6.3 / -9.0 | 5.7 → 5.0 |
| X-Plane | 39176bb8 | 13 | +1.7 / -2.3 | 3.7 → 3.4 |
| X-Plane | ? | 12 | +4.7 / +0.5 | 5.1 → 4.2 |
| X-Plane | b1d51b0f | 13 | -10.8 / +2.0 | 10.5 → 8.4 |
| X-Plane | bf5c7afc | 12 | +1.3 / -1.7 | 2.6 → 2.1 |
| X-Plane | c235f3b8 | 9 | +10.0 / +0.2 | 11.7 → 9.8 |
| X-Plane | d82848c4 | 8 | -0.1 / +2.2 | 3.5 → 3.0 |
<!--END:registration-->

- **Frame accuracy.** The app's equirectangular frame is 0.12 % short in the east–west scale (111 320·cos φ = 88 175 m/deg against 88 285 m/deg on WGS-84 at the ARP latitude 37.6188° [corrected by verifier: was "88 157 against 88 266". Both figures were about 19 m/deg low. The 0.12 % ratio (0.124 %) and the 3.4 m runway shortfall are unchanged.]). This shortens 10L/28R by 3.4 m against its geodesic length (§6). It is irrelevant for distances between neighbouring stands, at most about 0.1 m.

## 4. Results — stands

### 4.1 Verdicts (our 89 stands)

<!--BEGIN:verdict_summary-->
| position verdict | obs | inf | total |
|---|---|---|---|
| agree (ADS-B + SFO confirm ours) | 53 | 18 | 71 |
| agree | 7 | 8 | 15 |
| agree with OSM; X-Plane differs | 4 | 9 | 13 |
| OURS OFF (ADS-B + SFO) | 2 | 5 | 7 |
| agree with X-Plane; OSM differs | 2 | 0 | 2 |
<!--END:verdict_summary-->

### 4.2 Independent evidence: parked aircraft on SFO-published stands (ADS-B)

The rows are aircraft stationary for 120 s or more in our recording, where SFO's AODB stand window names the stand ("SFO window"). Two rows (marked "occupancy") had no callsign; for them, the one allocation at the stand our matcher chose is used.
- **Distances and cross values.** "dist (x …)" is measured from the aircraft's antenna. The cross value is taken across the aircraft's axis, and only when a heading was reported.
- **For our stands**, the antenna position is given in our stand's frame instead. With the nose tip about 4–10 m ahead of the antenna, "along" should be about −4 to −10 and "cross" about 0.

<!--BEGIN:adsb_table-->
| SFO stand (evidence) | aircraft (reg, type, flight) | ADS-B hdg | ours, same name (in our stand frame; Δhdg = ours − ADS-B) | ours nearest: dist (cross from aircraft axis) | OSM same ref: dist (cross) | OSM nearest | X-Plane same name: dist (cross) | X-Plane nearest |
|---|---|---|---|---|---|---|---|---|
| 2-2A (SFO window) | C-GYLY, BCS3, ACA759 | — | — (no stand of ours) | A10 230.0 m | — (no such ref) | (no ref) 4.0 m | — (no such name) | Gate A15 220.1 m |
| A11 (occupancy) | TC-LGS, A359, THY73G | 298° | A11: ADS-B point -10.2 along / +0.0 cross of our stand, Δhdg -0° | A11 10.2 m (x -0.1) | A11: 6.9 m (x -0.1) | A11 6.9 m (x -0.1) | Gate A11: 79.2 m (x +79.2) | Gate A13 A14 1.4 m (x -0.4) |
| A11 (occupancy) | 9V-SGB, A359, SIA34 | 298° | A11: ADS-B point -6.6 along / +1.1 cross of our stand, Δhdg -0° | A11 6.7 m (x -1.1) | A11: 3.5 m (x -1.1) | A11 3.5 m (x -1.1) | Gate A11: 78.3 m (x +78.2) | Gate A13 A14 5.0 m (x -1.4) |
| A12 (SFO window) | JA826J, B788, TZP26 | 89° | A12: ADS-B point -13.3 along / -1.3 cross of our stand, Δhdg -1° | A12 13.3 m (x +1.1) | A12: 10.0 m (x +1.1) [2 ways] | A12 10.0 m (x +1.1) | Gate A12: 123.6 m (x -109.3) | Terminal A 4.5 m (x +2.8) |
| A13V (SFO window) | JA739J, B77W, JAL1 | 132° | A13: ADS-B point -65.5 along / -133.6 cross of our stand, Δhdg -122° | A12 100.5 m (x -100.4) | A13: 147.4 m (x -123.2) | A15 37.8 m (x -2.2) | Gate A13 A14: 171.3 m (x -161.1) | Terminal A 87.9 m (x -87.6) |
| A13V (occupancy) | B-18915, A359, CAL004 | 11° | A13: ADS-B point -12.5 along / -0.0 cross of our stand, Δhdg -1° | A13 12.5 m (x -0.2) | A13: 9.2 m (x -0.1) | (no ref) 4.2 m (x -2.2) | Gate A13 A14: 53.4 m (x -0.2) | Terminal A 6.1 m (x +4.3) |
| A15 (SFO window) | XA-CCN, B38M, AMX668 | 45° | A15: ADS-B point -12.0 along / -0.9 cross of our stand, Δhdg +0° | A15 12.0 m (x +1.0) | A15: 10.8 m (x +1.0) | A15 10.8 m (x +1.0) | Gate A15: 77.8 m (x -61.6) | Terminal A 7.9 m (x +2.5) |
| B11S (SFO window) | N384HA, A332, ASA811 | 118° | B11: ADS-B point +0.2 along / -11.6 cross of our stand, Δhdg -15° | B11S 11.0 m (x +0.3) | B11: 7.7 m (x +0.4) [2 ways] | B11 7.7 m (x +0.4) | Gate B10 B11: 38.2 m (x -38.1) | Gate B10 B11 38.2 m (x -38.1) |
| B12 (SFO window) | N218HA, A21N, ASA979 | 298° | B12: ADS-B point +0.7 along / +0.9 cross of our stand, Δhdg -0° | B12 1.1 m (x -0.9) | B12: 2.1 m (x -0.9) | B12 2.1 m (x -0.9) | Gate B12: 11.5 m (x -9.9) | Gate B12 11.5 m (x -9.9) |
| B12 (SFO window) | N430SY, E75L, SKW3420 | 298° | B12: ADS-B point -13.1 along / -0.5 cross of our stand, Δhdg -0° | B12 13.2 m (x +0.4) | B12: 11.9 m (x +0.4) | B12 11.9 m (x +0.4) | Gate B12: 11.7 m (x -8.6) | Gate B12 11.7 m (x -8.6) |
| B12 (SFO window) | N402AS, B739, ASA655 | 298° | B12: ADS-B point -21.6 along / +187.9 cross of our stand, Δhdg -0° | B7 73.0 m (x -67.0) | B12: 189.0 m (x -188.0) | C6 7.7 m (x -0.0) | Gate B12: 197.6 m (x -197.0) | Gate C6 81.9 m (x +81.8) |
| B13 (SFO window) | N175SY, E75L, SKW3055 | 298° | B13: ADS-B point -12.4 along / -0.2 cross of our stand, Δhdg -0° | B13 12.4 m (x +0.1) | B13: 11.2 m (x +0.1) | B13 11.2 m (x +0.1) | Gate B13: 9.6 m (x -6.1) | Gate B13 9.6 m (x -6.1) |
| B13 (occupancy) | N723AL, B39M, ASA1412 | 298° | B13: ADS-B point -7.4 along / +0.7 cross of our stand, Δhdg -0° | B13 7.4 m (x -0.7) | B13: 6.2 m (x -0.7) | B13 6.2 m (x -0.7) | Gate B13: 7.3 m (x -6.9) | Gate B13 7.3 m (x -6.9) |
| B13 (SFO window) | N287AK, B739, ASA525 | 298° | B13: ADS-B point -7.5 along / +0.8 cross of our stand, Δhdg -0° | B13 7.6 m (x -0.8) | B13: 6.4 m (x -0.8) | B13 6.4 m (x -0.8) | Gate B13: 7.4 m (x -7.0) | Gate B13 7.4 m (x -7.0) |
| B14 (SFO window) | N392FR, A20N, FFT1229 | 298° | B14: ADS-B point -3.3 along / -0.1 cross of our stand, Δhdg -0° | B14 3.3 m (x +0.1) | B14: 2.1 m (x +0.1) | B14 2.1 m (x +0.1) | Gate B14: 10.0 m (x -9.8) | Gate B14 10.0 m (x -9.8) |
| B14 (SFO window) | N413FR, A20N, FFT2486 | 298° | B14: ADS-B point -3.8 along / +0.1 cross of our stand, Δhdg -0° | B14 3.8 m (x -0.2) | B14: 2.6 m (x -0.1) | B14 2.6 m (x -0.1) | Gate B14: 10.2 m (x -10.1) | Gate B14 10.2 m (x -10.1) |
| B16 (SFO window) | N107NN, A321, AAL177 | 101° | B16: ADS-B point -2.1 along / -1.6 cross of our stand, Δhdg +2° | B16 2.6 m (x +1.6) | B16: 1.8 m (x +1.6) [2 ways] | B16 1.8 m (x +1.6) | Gate B15 B16: 41.9 m (x -39.0) | Gate B19 B20 18.2 m (x +18.1) |
| B16S (SFO window) | N177DN, B763, DAL531 | 118° | B16: ADS-B point -8.7 along / -13.3 cross of our stand, Δhdg -15° | B16 15.9 m (x +10.5) | B16: 15.3 m (x +10.8) [2 ways] | B16 15.3 m (x +10.8) | Gate B15 B16: 34.6 m (x -32.2) | Gate B19 B20 30.5 m (x +27.2) |
| B17 (SFO window) | N639FR, A21N, FFT3439 | — | B17: ADS-B point +1.6 along / +0.6 cross of our stand | B17 1.8 m | B17: 2.9 m | B17 2.9 m | Gate B17: 11.8 m | Gate B17 11.8 m |
| B17 (SFO window) | N235FR, A320, FFT3308 | 298° | B17: ADS-B point -4.4 along / +0.3 cross of our stand, Δhdg -1° | B17 4.4 m (x -0.3) | B17: 3.2 m (x -0.3) | B17 3.2 m (x -0.3) | Gate B17: 7.8 m (x -7.1) | Gate B17 7.8 m (x -7.1) |
| B17 (SFO window) | N613FR, A21N, FFT2857 | 298° | B17: ADS-B point +0.2 along / +0.8 cross of our stand, Δhdg -1° | B17 0.8 m (x -0.8) | B17: 1.6 m (x -0.7) | B17 1.6 m (x -0.7) | Gate B17: 10.8 m (x -7.5) | Gate B17 10.8 m (x -7.5) |
| B17 (SFO window) | N364FR, A20N, FFT1159 | 298° | B17: ADS-B point -4.8 along / -0.3 cross of our stand, Δhdg -1° | B17 4.8 m (x +0.2) | B17: 3.6 m (x +0.2) | B17 3.6 m (x +0.2) | Gate B17: 7.1 m (x -6.6) | Gate B17 7.1 m (x -6.6) |
| B17 (SFO window) | N414FR, A20N, FFT2638 | 31° | B17: ADS-B point +245.5 along / +187.5 cross of our stand, Δhdg -94° | B2 4.1 m (x -0.2) | B17: 309.9 m (x +257.6) | B2 2.9 m (x -0.2) | Gate B17: 319.0 m (x +264.3) | Gate A1 115.3 m (x -96.9) |
| B17 (SFO window) | N373FR, A20N, FFT1191 | 298° | B17: ADS-B point -4.5 along / +0.3 cross of our stand, Δhdg -1° | B17 4.5 m (x -0.4) | B17: 3.3 m (x -0.4) | B17 3.3 m (x -0.4) | Gate B17: 7.8 m (x -7.2) | Gate B17 7.8 m (x -7.2) |
| B17 (SFO window) | N366FR, A20N, FFT3581 | 298° | B17: ADS-B point -4.2 along / +0.8 cross of our stand, Δhdg -1° | B17 4.2 m (x -0.8) | B17: 3.1 m (x -0.8) | B17 3.1 m (x -0.8) | Gate B17: 8.3 m (x -7.6) | Gate B17 8.3 m (x -7.6) |
| B18 (occupancy) | N968JT, A321, .N968JT | 307° | B18: ADS-B point +0.5 along / -0.5 cross of our stand, Δhdg -1° | B18 0.7 m (x +0.5) | B18: 1.8 m (x +0.6) | B18 1.8 m (x +0.6) | Gate B18: 11.3 m (x -6.3) | Gate B18 11.3 m (x -6.3) |
| B18 (SFO window) | N935JB, A321, JBU577 | 307° | B18: ADS-B point +0.0 along / -0.4 cross of our stand, Δhdg -1° | B18 0.4 m (x +0.4) | B18: 1.3 m (x +0.4) | B18 1.3 m (x +0.4) | Gate B18: 11.0 m (x -6.5) | Gate B18 11.0 m (x -6.5) |
| B18 (SFO window) | N2157J, A21N, JBU633 | 307° | B18: ADS-B point +4.2 along / +3.2 cross of our stand, Δhdg -1° | B18 5.3 m (x -3.1) | B18: 6.3 m (x -3.1) | B18 6.3 m (x -3.1) | Gate B18: 16.5 m (x -10.0) | Gate B18 16.5 m (x -10.0) |
| B19 (SFO window) | N556UW, A321, AAL2885 | 118° | B19: ADS-B point -0.8 along / +0.0 cross of our stand, Δhdg -0° | B19 0.8 m (x -0.0) | B19: 0.4 m (x -0.0) | B19 0.4 m (x -0.0) | Gate B19 B20: 46.0 m (x -38.8) | Gate B26 B27 27.0 m (x +9.4) |
| B19 (SFO window) | N360FR, A20N, FFT1849 | 118° | B19: ADS-B point -5.2 along / +0.1 cross of our stand, Δhdg -0° | B19 5.2 m (x -0.1) | B19: 4.0 m (x -0.1) | B19 4.0 m (x -0.1) | Gate B19 B20: 48.7 m (x -38.9) | Gate B26 B27 31.1 m (x +9.3) |
| B19 (occupancy) | N151UW, A321, AAL2410 | 118° | B19: ADS-B point -0.8 along / +0.0 cross of our stand, Δhdg -0° | B19 0.8 m (x -0.0) | B19: 0.4 m (x -0.0) | B19 0.4 m (x -0.0) | Gate B19 B20: 46.0 m (x -38.8) | Gate B26 B27 27.0 m (x +9.4) |
| B2 (SFO window) | N17311, B38M, UAL2051 | 31° | B2: ADS-B point -9.4 along / -1.1 cross of our stand, Δhdg -0° | B2 9.5 m (x +1.1) | B2: 8.3 m (x +1.1) | B2 8.3 m (x +1.1) | — (no such name) | Gate A1 111.4 m (x -95.5) |
| B2 (SFO window) | N77538, B738, UAL2051 | 121° | B2: ADS-B point +575.2 along / +85.6 cross of our stand, Δhdg -90° | D15 14.1 m (x +1.0) | B2: 582.7 m (x +576.8) | D15 12.9 m (x +1.0) | — (no such name) | Gate D16 D17 15.5 m (x +0.5) |
| B20 (SFO window) | N929JB, A321, JBU15 | 104° | B20: ADS-B point -1.9 along / -0.4 cross of our stand, Δhdg -1° | B20 1.9 m (x +0.4) | B20: 0.8 m (x +0.4) [2 ways] | B20 0.8 m (x +0.4) | Gate B19 B20: 71.4 m (x -68.3) | Gate B26 B27 23.5 m (x -21.4) |
| B21 (SFO window) | N937JB, A321, JBU515 | — | B21: ADS-B point -0.4 along / +0.1 cross of our stand | B21 0.4 m | B21: 0.8 m | B21 0.8 m | Gate B21: 15.9 m | Gate B21 15.9 m |
| B21 (SFO window) | N988JT, A321, JBU115 | 307° | B21: ADS-B point -0.4 along / +0.1 cross of our stand, Δhdg -1° | B21 0.4 m (x -0.1) | B21: 0.8 m (x -0.1) | B21 0.8 m (x -0.1) | Gate B21: 15.9 m (x -5.2) | Gate B21 15.9 m (x -5.2) |
| B21 (SFO window) | N981JT, A321, JBU416 | 307° | B21: ADS-B point +0.1 along / +0.2 cross of our stand, Δhdg -1° | B21 0.3 m (x -0.2) | B21: 1.4 m (x -0.2) | B21 1.4 m (x -0.2) | Gate B21: 16.5 m (x -5.3) | Gate B21 16.5 m (x -5.3) |
| B21 (SFO window) | N962JT, A321, JBU415 | 307° | B21: ADS-B point +2.0 along / -1.7 cross of our stand, Δhdg -1° | B21 2.6 m (x +1.7) | B21: 3.6 m (x +1.7) | B21 3.6 m (x +1.7) | Gate B21: 17.8 m (x -3.4) | Gate B21 17.8 m (x -3.4) |
| B22 (SFO window) | N510SY, E75L, SKW6274 | 307° | B22: ADS-B point -16.6 along / -0.8 cross of our stand, Δhdg -0° | B22 16.6 m (x +0.7) | B22: 15.4 m (x +0.8) | B22 15.4 m (x +0.8) | Gate B22: 3.4 m (x -2.1) | Gate B22 3.4 m (x -2.1) |
| B22 (SFO window) | N515SY, E75L, SKW6277 | 307° | B22: ADS-B point -16.6 along / -0.7 cross of our stand, Δhdg -0° | B22 16.6 m (x +0.7) | B22: 15.4 m (x +0.7) | B22 15.4 m (x +0.7) | Gate B22: 3.4 m (x -2.2) | Gate B22 3.4 m (x -2.2) |
| B22 (SFO window) | N977NN, B738, AAL3247 | 304° | B22: ADS-B point -10.5 along / +1.0 cross of our stand, Δhdg +3° | B22 10.5 m (x -0.5) | B22: 9.3 m (x -0.6) | B22 9.3 m (x -0.6) | Gate B22: 5.2 m (x -4.0) | Gate B22 5.2 m (x -4.0) |
| B23 (SFO window) | N980UY, A321, AAL2856 | 338° | B23: ADS-B point -3.4 along / -0.2 cross of our stand, Δhdg +2° | B23 3.4 m (x +0.3) | B23: 2.2 m (x +0.3) [2 ways] | B23 2.2 m (x +0.3) | Gate B23: 16.0 m (x -15.9) | Gate B23 16.0 m (x -15.9) |
| B23 (SFO window) | N430AN, A21N, AAL1949 | 338° | B23: ADS-B point -3.8 along / +0.2 cross of our stand, Δhdg +2° | B23 3.8 m (x -0.1) | B23: 2.6 m (x -0.1) [2 ways] | B23 2.6 m (x -0.1) | Gate B23: 16.4 m (x -16.4) | Gate B23 16.4 m (x -16.4) |
| B23 (SFO window) | N959XV, PA27, AAL2758 | 338° | B23: ADS-B point -3.8 along / +0.2 cross of our stand, Δhdg +2° | B23 3.8 m (x -0.1) | B23: 2.6 m (x -0.1) [2 ways] | B23 2.6 m (x -0.1) | Gate B23: 16.4 m (x -16.4) | Gate B23 16.4 m (x -16.4) |
| B23 (SFO window) | N930AU, A321, AAL1851 | 338° | B23: ADS-B point -3.4 along / -0.2 cross of our stand, Δhdg +2° | B23 3.4 m (x +0.3) | B23: 2.2 m (x +0.3) [2 ways] | B23 2.2 m (x +0.3) | Gate B23: 16.0 m (x -15.9) | Gate B23 16.0 m (x -15.9) |
| B23 (SFO window) | N934AA, A321, AAL1489 | 338° | B23: ADS-B point +0.0 along / +4.4 cross of our stand, Δhdg +2° | B23 4.4 m (x -4.4) | B23: 4.6 m (x -4.5) [2 ways] | B23 4.6 m (x -4.5) | Gate B23: 20.8 m (x -20.7) | Gate B23 20.8 m (x -20.7) |
| B23 (SFO window) | N123UW, A320, AAL2421 | 340° | B23: ADS-B point -8.9 along / -0.3 cross of our stand, Δhdg -1° | B23 8.9 m (x +0.1) | B23: 7.7 m (x +0.1) [2 ways] | B23 7.7 m (x +0.1) | Gate B23: 16.8 m (x -16.0) | Gate B23 16.8 m (x -16.0) |
| B24 (SFO window) | N437AN, A21N, AAL2506 | — | B24: ADS-B point -0.9 along / -0.0 cross of our stand | B24 0.9 m | B24: 0.3 m | B24 0.3 m | Gate B24: 32.8 m | Gate B23 14.2 m |
| B24 (SFO window) | N466AN, A21N, AAL2814 | 14° | B24: ADS-B point +0.1 along / -0.1 cross of our stand, Δhdg -1° | B24 0.1 m (x +0.1) | B24: 1.3 m (x +0.1) | B24 1.3 m (x +0.1) | Gate B24: 32.5 m (x -32.1) | Gate B23 14.0 m (x +13.9) |
| B24 (SFO window) | N940AN, B738, AAL3115 | 295° | B24: ADS-B point -119.3 along / +63.5 cross of our stand, Δhdg +78° | B24 135.2 m (x +102.7) | B24: 69.4 m (x +2.0) | B23 29.1 m (x +0.2) | Gate B24: 157.6 m (x +101.6) | Gate B23 130.9 m (x +107.5) |
| B24 (SFO window) | N962NN, B738, AAL2642 | 11° | B24: ADS-B point -6.5 along / -0.1 cross of our stand, Δhdg +2° | B24 6.5 m (x +0.3) | B24: 5.3 m (x +0.2) | B24 5.3 m (x +0.2) | Gate B24: 34.3 m (x -31.6) | Gate B23 16.3 m (x +14.2) |
| B24 (SFO window) | N536UW, A321, AAL2333 | 11° | B24: ADS-B point -2.4 along / -0.9 cross of our stand, Δhdg +2° | B24 2.5 m (x +0.9) | B24: 1.4 m (x +0.9) | B24 1.4 m (x +0.9) | Gate B24: 32.3 m (x -31.0) | Gate B23 15.3 m (x +14.8) |
| B24 (occupancy) | N107NN, A321, AAL15 | 11° | B24: ADS-B point -2.4 along / +0.5 cross of our stand, Δhdg +2° | B24 2.4 m (x -0.4) | B24: 1.3 m (x -0.5) | B24 1.3 m (x -0.5) | Gate B24: 33.6 m (x -32.3) | Gate B23 14.0 m (x +13.5) |
| B25 (SFO window) | N123NN, A321, AAL1188 | 34° | B25: ADS-B point +0.7 along / -1.2 cross of our stand, Δhdg -1° | B25 1.4 m (x +1.2) | B25: 2.3 m (x +1.2) | B25 2.3 m (x +1.2) | Gate B25: 43.7 m (x -42.9) | Gate B24 5.4 m (x +4.0) |
| B25 (SFO window) | N104NN, A321, AAL76 | 34° | B25: ADS-B point +0.7 along / -1.2 cross of our stand, Δhdg -1° | B25 1.4 m (x +1.2) | B25: 2.3 m (x +1.2) | B25 2.3 m (x +1.2) | Gate B25: 43.7 m (x -42.9) | Gate B24 5.4 m (x +4.0) |
| B25 (SFO window) | N101NN, A321, AAL179 | 34° | B25: ADS-B point -0.6 along / -1.0 cross of our stand, Δhdg -1° | B25 1.1 m (x +1.0) | B25: 1.1 m (x +1.0) | B25 1.1 m (x +1.0) | Gate B25: 44.2 m (x -43.1) | Gate B24 4.4 m (x +3.7) |
| B25 (SFO window) | N305NY, A21N, AAL149 | 34° | B25: ADS-B point -0.3 along / -0.5 cross of our stand, Δhdg -1° | B25 0.6 m (x +0.5) | B25: 1.0 m (x +0.5) | B25 1.0 m (x +0.5) | Gate B25: 44.6 m (x -43.5) | Gate B24 4.2 m (x +3.3) |
| B25 (SFO window) | N895NN, B738, AAL1914 | 34° | B25: ADS-B point -9.7 along / -0.6 cross of our stand, Δhdg -1° | B25 9.7 m (x +0.4) | B25: 8.5 m (x +0.4) | B25 8.5 m (x +0.4) | Gate B25: 47.6 m (x -43.7) | Gate B24 7.4 m (x +3.2) |
| B25 (SFO window) | N426AN, A21N, AAL3166 | 31° | B25: ADS-B point -0.4 along / -0.5 cross of our stand, Δhdg +2° | B25 0.6 m (x +0.5) | B25: 0.9 m (x +0.4) | B25 0.9 m (x +0.4) | Gate B25: 44.7 m (x -43.1) | Gate B24 4.1 m (x +3.1) |
| B26 (occupancy) | N161AA, A321, — | — | B26: ADS-B point +0.5 along / +0.3 cross of our stand | B26 0.6 m | B26: 1.8 m [2 ways] | B26 1.8 m | Gate B26 B27: 85.6 m | Gate B25 20.9 m |
| B26 (SFO window) | N324VL, B38M, AAL2799 | 62° | B26: ADS-B point -8.1 along / +0.3 cross of our stand, Δhdg +2° | B26 8.2 m (x -0.0) | B26: 7.0 m (x -0.1) [2 ways] | B26 7.0 m (x -0.1) | Gate B26 B27: 92.7 m (x -49.7) | Gate B25 25.2 m (x -19.2) |
| B26 (SFO window) | N324SH, B38M, AAL773 | 65° | B26: ADS-B point -9.3 along / -0.4 cross of our stand, Δhdg -1° | B26 9.3 m (x +0.2) | B26: 8.1 m (x +0.3) [2 ways] | B26 8.1 m (x +0.3) | Gate B26 B27: 93.3 m (x -52.8) | Gate B25 25.4 m (x -19.3) |
| B26 (SFO window) | N474AN, A21N, AAL1022 | 62° | B26: ADS-B point +0.1 along / -1.6 cross of our stand, Δhdg +2° | B26 1.6 m (x +1.5) | B26: 2.1 m (x +1.5) [2 ways] | B26 2.1 m (x +1.5) | Gate B26 B27: 84.9 m (x -48.1) | Gate B25 19.3 m (x -17.7) |
| B26 (SFO window) | N163AA, A321, AAL2325 | 62° | B26: ADS-B point -0.1 along / -1.4 cross of our stand, Δhdg +2° | B26 1.4 m (x +1.4) | B26: 1.8 m (x +1.4) [2 ways] | B26 1.8 m (x +1.4) | Gate B26 B27: 85.1 m (x -48.2) | Gate B25 19.5 m (x -17.8) |
| B26 (SFO window) | N912UY, A321, AAL2069 | — | B26: ADS-B point +1.7 along / -4.7 cross of our stand | B26 5.0 m | B26: 2.7 m [2 ways] | B26 2.7 m | Gate B26 B27: 81.7 m | Gate B25 15.8 m |
| B27 (SFO window) | N139AN, A321, AAL2309 | 104° | B27: ADS-B point -5.5 along / -0.6 cross of our stand, Δhdg +0° | B27 5.6 m (x +0.7) | B27: 4.4 m (x +0.7) | B27 4.4 m (x +0.7) | Gate B26 B27: 77.9 m (x -64.1) | Gate B25 18.7 m (x +0.1) |
| B27 (SFO window) | N455AN, A21N, AAL1524 | 104° | B27: ADS-B point -5.2 along / +0.7 cross of our stand, Δhdg +0° | B27 5.2 m (x -0.6) | B27: 4.1 m (x -0.6) | B27 4.1 m (x -0.6) | Gate B26 B27: 78.8 m (x -65.4) | Gate B25 18.4 m (x -1.1) |
| B27 (SFO window) | N162UW, A321, AAL2387 | 104° | B27: ADS-B point -6.0 along / -2.4 cross of our stand, Δhdg +0° | B27 6.4 m (x +2.4) | B27: 5.3 m (x +2.4) | B27 5.3 m (x +2.4) | Gate B26 B27: 76.7 m (x -62.3) | Gate B25 19.2 m (x +1.9) |
| B27 (occupancy) | N157UW, A321, .N157UW | — | B27: ADS-B point -7.5 along / -2.0 cross of our stand | B27 7.8 m | B27: 6.6 m | B27 6.6 m | Gate B26 B27: 77.9 m | Gate B25 20.7 m |
| B3 (SFO window) | N264AK, B739, ASA1327 | 276° | B3: ADS-B point -8.7 along / +0.2 cross of our stand, Δhdg +0° | B3 8.7 m (x -0.2) | B3: 7.5 m (x -0.2) | B3 7.5 m (x -0.2) | Gate B3: 12.9 m (x -10.9) | Gate B3 12.9 m (x -10.9) |
| B3 (SFO window) | N639QX, E75L, QXE2138 | 276° | B3: ADS-B point -12.8 along / -0.0 cross of our stand, Δhdg +0° | B3 12.8 m (x +0.1) | B3: 11.6 m (x +0.1) | B3 11.6 m (x +0.1) | Gate B3: 15.4 m (x -10.6) | Gate B3 15.4 m (x -10.6) |
| B3 (SFO window) | N189SY, E75L, SKW3164 | 239° | B3: ADS-B point -30.2 along / -46.1 cross of our stand, Δhdg +37° | B6 12.3 m (x -1.7) | B3: 54.5 m (x +54.4) | B6 11.1 m (x -1.7) | Gate B3: 45.4 m (x +45.4) | Gate B6 5.8 m (x +4.3) |
| B4 (occupancy) | N533DT, A21N, — | — | B4: ADS-B point -0.1 along / -1.4 cross of our stand | B4 1.4 m | B4: 1.8 m | B4 1.8 m | — (no such name) | Gate B10 B11 105.7 m |
| B5 (SFO window) | N943JT, A321, JBU413 | 53° | B5: ADS-B point -0.8 along / -0.8 cross of our stand, Δhdg -3° | B5 1.1 m (x +0.8) | B5: 0.9 m (x +0.9) [2 ways] | B5 0.9 m (x +0.9) | — (no such name) | Gate B10 B11 76.7 m (x +64.6) |
| B6 (SFO window) | N563AS, B738, ASA8 | 239° | B6: ADS-B point -9.8 along / +0.4 cross of our stand, Δhdg +1° | B6 9.8 m (x -0.3) | B6: 8.6 m (x -0.3) | B6 8.6 m (x -0.3) | Gate B6: 8.5 m (x +5.7) | Gate B6 8.5 m (x +5.7) |
| B6 (SFO window) | N924AK, B39M, ASA1302 | 298° | B6: ADS-B point +28.5 along / -86.9 cross of our stand, Δhdg -58° | B9 7.0 m (x +0.0) | B6: 91.8 m (x +70.8) | B9 5.8 m (x +0.0) | Gate B6: 103.2 m (x +86.6) | Gate B9 13.1 m (x -12.7) |
| B6 (SFO window) | N402AS, B739, ASA630 | 239° | B6: ADS-B point -4.1 along / +0.3 cross of our stand, Δhdg +1° | B6 4.1 m (x -0.2) | B6: 2.9 m (x -0.2) | B6 2.9 m (x -0.2) | Gate B6: 13.3 m (x +5.8) | Gate B6 13.3 m (x +5.8) |
| B6 (SFO window) | N937AK, B39M, ASA591 | 239° | B6: ADS-B point -7.9 along / -0.4 cross of our stand, Δhdg +1° | B6 7.9 m (x +0.5) | B6: 6.7 m (x +0.5) | B6 6.7 m (x +0.5) | Gate B6: 10.4 m (x +6.5) | Gate B6 10.4 m (x +6.5) |
| B7 (SFO window) | N194SY, E75L, SKW3007 | 270° | B7: ADS-B point -12.0 along / +0.5 cross of our stand, Δhdg +1° | B7 12.0 m (x -0.4) | B7: 10.8 m (x -0.4) | B7 10.8 m (x -0.4) | Gate B7 B8: 33.8 m (x -15.9) | Gate B7 B8 33.8 m (x -15.9) |
| B8 (SFO window) | N953AK, B39M, ASA424 | 298° | B8: ADS-B point -7.6 along / +0.2 cross of our stand, Δhdg -0° | B8 7.6 m (x -0.2) | — (no such ref) | (no ref) 6.4 m (x -0.2) | Gate B7 B8: 25.3 m (x +8.9) | Gate B7 B8 25.3 m (x +8.9) |
| B8 (SFO window) | N839AK, B38M, ASA718 | 298° | B8: ADS-B point -7.9 along / +0.2 cross of our stand, Δhdg -0° | B8 7.9 m (x -0.2) | — (no such ref) | (no ref) 6.7 m (x -0.2) | Gate B7 B8: 25.5 m (x +8.8) | Gate B7 B8 25.5 m (x +8.8) |
| B9 (SFO window) | N549AS, B738, ASA1329 | 298° | B9: ADS-B point -5.8 along / +0.8 cross of our stand, Δhdg -0° | B9 5.8 m (x -0.8) | B9: 4.7 m (x -0.8) | B9 4.7 m (x -0.8) | Gate B9: 13.7 m (x -13.6) | Gate B9 13.7 m (x -13.6) |
| B9 (SFO window) | N537AS, B738, ASA656 | 298° | B9: ADS-B point -7.3 along / +0.8 cross of our stand, Δhdg -0° | B9 7.3 m (x -0.9) | B9: 6.1 m (x -0.9) | B9 6.1 m (x -0.9) | Gate B9: 14.0 m (x -13.6) | Gate B9 14.0 m (x -13.6) |
| B9 (SFO window) | N806AK, B38M, ASA1499 | 298° | B9: ADS-B point -6.1 along / +0.2 cross of our stand, Δhdg -0° | B9 6.1 m (x -0.3) | B9: 4.9 m (x -0.2) | B9 4.9 m (x -0.2) | Gate B9: 13.2 m (x -13.0) | Gate B9 13.2 m (x -13.0) |
| B9 (SFO window) | N405SY, E75L, SKW3313 | 298° | B9: ADS-B point -12.8 along / +0.1 cross of our stand, Δhdg -0° | B9 12.8 m (x -0.2) | B9: 11.6 m (x -0.2) | B9 11.6 m (x -0.2) | Gate B9: 15.8 m (x -12.9) | Gate B9 15.8 m (x -12.9) |
| C1 (occupancy) | N197SY, E75L, SKW939E | 309° | C1: ADS-B point -12.7 along / +0.6 cross of our stand, Δhdg -0° | C1 12.7 m (x -0.7) | C1: 11.5 m (x -0.7) | C1 11.5 m (x -0.7) | — (no such name) | Gate C2 61.3 m (x +59.8) |
| C10 (SFO window) | C-FDUW, BCS3, ACA738 | 321° | C10: ADS-B point -2.0 along / +0.9 cross of our stand, Δhdg -1° | C10 2.2 m (x -1.0) | C10: 1.2 m (x -0.9) | C10 1.2 m (x -0.9) | — (no such name) | Gate C11 9.3 m (x +9.0) |
| C10 (SFO window) | N262BZ, BCS3, MXY1066 | 321° | C10: ADS-B point -4.5 along / +1.8 cross of our stand, Δhdg -1° | C10 4.8 m (x -1.9) | C10: 3.7 m (x -1.9) | C10 3.7 m (x -1.9) | — (no such name) | Gate C11 9.4 m (x +8.1) |
| C11 (SFO window) | N316DU, BCS3, DAL2635 | 292° | C11: ADS-B point -6.1 along / +0.6 cross of our stand, Δhdg -3° | C11 6.2 m (x -0.9) | C11: 5.0 m (x -0.9) | C11 5.0 m (x -0.9) | Gate C11: 26.9 m (x -26.9) | Gate C9 7.3 m (x -0.5) |
| C11 (SFO window) | N342DU, A333, DAL1053 | 292° | C11: ADS-B point -9.1 along / +0.3 cross of our stand, Δhdg -3° | C11 9.1 m (x -0.7) | C11: 7.9 m (x -0.7) | C11 7.9 m (x -0.7) | Gate C11: 27.0 m (x -26.6) | Gate C9 10.3 m (x -0.3) |
| C3 (SFO window) | N619DN, A21N, DAL977 | 222° | C3: ADS-B point -4.7 along / +0.4 cross of our stand, Δhdg -0° | C3 4.7 m (x -0.4) | C3: 3.5 m (x -0.4) | C3 3.5 m (x -0.4) | Gate C3: 51.9 m (x -51.4) | Gate C3 51.9 m (x -51.4) |
| C3 (SFO window) | N891DN, B739, DAL750 | 25° | C3: ADS-B point +68.6 along / -130.6 cross of our stand, Δhdg -164° | C6 7.5 m (x +0.4) | C3: 148.1 m (x -105.4) | C6 6.3 m (x +0.4) | Gate C3: 113.1 m (x -53.5) | Gate C6 13.5 m (x +4.7) |
| C4 (SFO window) | C-FHYY, BCS3, ACA739 | 28° | C4: ADS-B point -5.9 along / -0.1 cross of our stand, Δhdg +2° | C4 5.9 m (x +0.2) | C4: 4.8 m (x +1.3) | C4 4.8 m (x +1.3) | Gate C4: 11.4 m (x +3.2) | Gate C4 11.4 m (x +3.2) |
| C5 (SFO window) | N929DZ, B739, DAL805 | 217° | C5: ADS-B point -12.0 along / +1.0 cross of our stand, Δhdg +0° | C5 12.0 m (x -0.9) | C5: 10.8 m (x -0.9) | (no ref) 8.5 m (x +0.9) | Gate C5: 48.2 m (x -47.4) | Gate C3 10.6 m (x -0.7) |
| C5 (SFO window) | N723TW, B752, DAL363 | 217° | C5: ADS-B point -7.2 along / +1.0 cross of our stand, Δhdg +0° | C5 7.3 m (x -1.0) | C5: 6.1 m (x -1.0) | (no ref) 3.8 m (x +0.8) | Gate C5: 47.7 m (x -47.5) | Gate C3 5.9 m (x -0.8) |
| C6 (SFO window) | N335NB, A319, DAL381 | 28° | C6: ADS-B point -4.7 along / -0.2 cross of our stand, Δhdg -1° | C6 4.7 m (x +0.1) | C6: 3.5 m (x +0.1) | C6 3.5 m (x +0.1) | Gate C6: 11.0 m (x +4.1) | Gate C6 11.0 m (x +4.1) |
| C6 (SFO window) | N371DA, B738, DAL1412 | 28° | C6: ADS-B point -11.6 along / +0.5 cross of our stand, Δhdg -1° | C6 11.6 m (x -0.7) | C6: 10.4 m (x -0.6) | C6 10.4 m (x -0.6) | Gate C6: 17.4 m (x +3.4) | Gate C6 17.4 m (x +3.4) |
| C6 (SFO window) | N838DN, B739, DAL1559 | 28° | C6: ADS-B point -7.7 along / -0.3 cross of our stand, Δhdg -1° | C6 7.7 m (x +0.2) | C6: 6.5 m (x +0.3) | C6 6.5 m (x +0.3) | Gate C6: 13.8 m (x +4.3) | Gate C6 13.8 m (x +4.3) |
| C7 (SFO window) | N3732J, B738, DAL1421 | 222° | C7: ADS-B point -13.9 along / +1.8 cross of our stand, Δhdg -0° | C7 14.0 m (x -1.9) | C7: 12.8 m (x -1.9) | C7 12.8 m (x -1.9) | Gate C7: 33.1 m (x -32.2) | Gate C5 18.1 m (x -4.9) |
| C7 (SFO window) | N818DA, B739, DAL2057 | 222° | C7: ADS-B point -11.0 along / +1.2 cross of our stand, Δhdg -0° | C7 11.1 m (x -1.3) | C7: 9.9 m (x -1.3) | C7 9.9 m (x -1.3) | Gate C7: 32.0 m (x -31.6) | Gate C5 15.2 m (x -4.3) |
| C7 (SFO window) | N334NW, A320, DAL902 | 222° | C7: ADS-B point -10.0 along / +0.3 cross of our stand, Δhdg -0° | C7 10.0 m (x -0.4) | C7: 8.8 m (x -0.4) | C7 8.8 m (x -0.4) | Gate C7: 31.0 m (x -30.7) | Gate C5 14.0 m (x -3.4) |
| C9 (SFO window) | N552DT, A21N, DAL693 | 253° | C9: ADS-B point -2.1 along / +0.2 cross of our stand, Δhdg +0° | C9 2.1 m (x -0.2) | C9: 0.9 m (x -0.2) | C9 0.9 m (x -0.2) | Gate C9: 29.6 m (x -29.6) | Gate C7 6.6 m (x -2.9) |
| D1 (SFO window) | N7749B, B737, SWA3722 | 357° | D1: ADS-B point -11.2 along / +0.4 cross of our stand, Δhdg +1° | D1 11.2 m (x -0.1) | D1: 10.0 m (x -0.2) | D1 10.0 m (x -0.2) | Gate D1 D2: 48.9 m (x +36.2) | Gate D1 D2 48.9 m (x +36.2) |
| D1 (SFO window) | N8722L, B38M, SWA974 | 298° | D1: ADS-B point -99.0 along / +39.8 cross of our stand, Δhdg +60° | C7 76.6 m (x -75.6) | D1: 53.0 m (x +0.2) | C5 22.6 m (x +21.3) | Gate D1 D2: 121.5 m (x +103.5) | Gate C5 81.1 m (x -79.8) |
| D1 (SFO window) | N217JC, B737, SWA4328 | 357° | D1: ADS-B point -11.2 along / +0.4 cross of our stand, Δhdg +1° | D1 11.2 m (x -0.1) | D1: 10.0 m (x -0.2) | D1 10.0 m (x -0.2) | Gate D1 D2: 48.9 m (x +36.2) | Gate D1 D2 48.9 m (x +36.2) |
| D1 (SFO window) | N229WN, B737, SWA4521 | 357° | D1: ADS-B point -11.2 along / +0.4 cross of our stand, Δhdg +1° | D1 11.2 m (x -0.1) | D1: 10.0 m (x -0.2) | D1 10.0 m (x -0.2) | Gate D1 D2: 48.9 m (x +36.2) | Gate D1 D2 48.9 m (x +36.2) |
| D1 (SFO window) | N8936Q, B38M, SWA4525 | 357° | D1: ADS-B point -7.8 along / +1.2 cross of our stand, Δhdg +1° | D1 7.8 m (x -1.0) | D1: 6.7 m (x -1.0) | D1 6.7 m (x -1.0) | Gate D1 D2: 46.0 m (x +35.3) | Gate D1 D2 46.0 m (x +35.3) |
| D10 (SFO window) | N220BZ, BCS3, MXY811 | 236° | D10: ADS-B point -17.9 along / +0.7 cross of our stand, Δhdg -1° | D10 17.9 m (x -1.0) | D10: 16.7 m (x -1.0) | D10 16.7 m (x -1.0) | Gate D9 D10: 46.0 m (x -41.5) | Gate D11 10.7 m (x +3.3) |
| D11 (SFO window) | C-FDUW, BCS3, ACA738 | 321° | D11: ADS-B point +414.5 along / -99.7 cross of our stand, Δhdg -118° | C10 2.8 m (x -0.3) | D11: 427.5 m (x +318.5) | C10 1.6 m (x -0.2) | Gate D11: 418.2 m (x +330.3) | Gate C11 10.2 m (x +9.7) |
| D11 (SFO window) | C-FHEI, BCS3, ACA562 | 202° | D11: ADS-B point -15.1 along / -0.2 cross of our stand, Δhdg -0° | D11 15.1 m (x +0.1) | D11: 13.9 m (x +0.1) | D11 13.9 m (x +0.1) | Gate D11: 35.1 m (x -30.8) | Gate D12 10.5 m (x -2.7) |
| D11 (occupancy) | C-FHFN, BCS3, ACA757 | 202° | D11: ADS-B point -14.8 along / +1.1 cross of our stand, Δhdg -0° | D11 14.8 m (x -1.2) | D11: 13.6 m (x -1.2) | D11 13.6 m (x -1.2) | Gate D11: 36.1 m (x -32.1) | Gate D12 10.6 m (x -4.0) |
| D11 (SFO window) | C-GJVT, A320, ACA743 | 202° | D11: ADS-B point -16.0 along / +1.0 cross of our stand, Δhdg -0° | D11 16.0 m (x -1.1) | D11: 14.8 m (x -1.1) | D11 14.8 m (x -1.1) | Gate D11: 36.7 m (x -32.0) | Gate D12 11.7 m (x -4.0) |
| D11 (occupancy) | C-FSIP, B38M, ROU1765 | 202° | D11: ADS-B point -16.5 along / -0.2 cross of our stand, Δhdg -0° | D11 16.5 m (x +0.1) | D11: 15.3 m (x +0.1) | D11 15.3 m (x +0.1) | Gate D11: 35.9 m (x -30.8) | Gate D12 11.9 m (x -2.8) |
| D12 (SFO window) | N14540, A21N, UAL1812 | 166° | D12: ADS-B point -87.1 along / +0.9 cross of our stand, Δhdg +0° | D12 87.1 m (x -0.2) | D12: 15.5 m (x -0.8) | D12 15.5 m (x -0.8) | Gate D12: 105.5 m (x -30.5) | Gate D14 85.8 m (x -0.3) |
| D15 (SFO window) | N77538, B738, UAL2051 | 121° | D15: ADS-B point -12.5 along / -1.0 cross of our stand, Δhdg -1° | D15 12.5 m (x +0.7) | D15: 11.3 m (x +0.7) | D15 11.3 m (x +0.7) | Gate D15: 39.7 m (x -38.1) | Gate D16 D17 13.9 m (x +0.2) |
| D16 (SFO window) | N17279, B38M, UAL2386 | 135° | D16: ADS-B point -13.3 along / +0.1 cross of our stand, Δhdg -1° | D16 13.3 m (x -0.3) | D16: 12.1 m (x -0.3) | D16 12.1 m (x -0.3) | Gate D16 D17: 70.0 m (x -63.3) | Gate D18 9.9 m (x +0.5) |
| D3 (SFO window) | N8786Q, B38M, SWA717 | 25° | D3: ADS-B point -3.9 along / -5.0 cross of our stand, Δhdg -12° | D3 6.3 m (x +4.1) | D3: 5.7 m (x +4.4) | D3 5.7 m (x +4.4) | Gate D3: 8.7 m (x +3.5) | Gate D3 8.7 m (x +3.5) |
| D3 (SFO window) | N8744B, B38M, SWA4519 | 25° | D3: ADS-B point -4.5 along / -4.9 cross of our stand, Δhdg -12° | D3 6.6 m (x +3.8) | D3: 5.9 m (x +4.1) | D3 5.9 m (x +4.1) | Gate D3: 9.1 m (x +3.2) | Gate D3 9.1 m (x +3.2) |
| D3 (SFO window) | N8688J, B738, SWA3422 | 25° | D3: ADS-B point -4.3 along / -4.0 cross of our stand, Δhdg -12° | D3 5.9 m (x +3.0) | D3: 5.1 m (x +3.3) | D3 5.1 m (x +3.3) | Gate D3: 8.5 m (x +2.4) | Gate D3 8.5 m (x +2.4) |
| D3 (SFO window) | N8641B, B738, SWA4496 | 28° | D3: ADS-B point -16.0 along / +36.6 cross of our stand, Δhdg -15° | D4 10.0 m (x -2.8) | D3: 39.5 m (x -39.2) | D4 8.8 m (x -2.3) | Gate D3: 41.3 m (x -40.3) | Gate D4 7.2 m (x +5.7) |
| D3 (SFO window) | N8743K, B38M, SWA4813 | 28° | D3: ADS-B point -4.3 along / -4.0 cross of our stand, Δhdg -15° | D3 5.9 m (x +2.8) | D3: 5.1 m (x +3.1) | D3 5.1 m (x +3.1) | Gate D3: 8.5 m (x +2.0) | Gate D3 8.5 m (x +2.0) |
| D3 (SFO window) | N8552Z, B738, SWA4532 | 25° | D3: ADS-B point -5.2 along / -5.2 cross of our stand, Δhdg -12° | D3 7.3 m (x +4.0) | D3: 6.5 m (x +4.2) | D3 6.5 m (x +4.2) | Gate D3: 9.8 m (x +3.4) | Gate D3 9.8 m (x +3.4) |
| D3 (SFO window) | N8629A, B738, SWA2697 | 25° | D3: ADS-B point -3.0 along / -4.3 cross of our stand, Δhdg -12° | D3 5.3 m (x +3.6) | D3: 4.7 m (x +3.8) | D3 4.7 m (x +3.8) | Gate D3: 7.6 m (x +3.0) | Gate D3 7.6 m (x +3.0) |
| D4 (SFO window) | N442WN, B737, SWA2978 | 25° | D4: ADS-B point -11.4 along / -2.3 cross of our stand, Δhdg -24° | D4 11.6 m (x -2.6) | D4: 10.4 m (x -2.1) | D4 10.4 m (x -2.1) | Gate D4: 8.1 m (x +5.7) | Gate D4 8.1 m (x +5.7) |
| D4 (SFO window) | N497WN, B737, SWA3714 | 28° | D4: ADS-B point -11.4 along / -1.8 cross of our stand, Δhdg -27° | D4 11.5 m (x -3.6) | D4: 10.4 m (x -3.0) | D4 10.4 m (x -3.0) | Gate D4: 7.6 m (x +5.0) | Gate D4 7.6 m (x +5.0) |
| D4 (SFO window) | N487WN, B737, SWA2288 | 298° | D4: ADS-B point -125.1 along / -15.6 cross of our stand, Δhdg +63° | C9 75.7 m (x -73.0) | D4: 44.3 m (x +43.1) | C7 36.5 m (x +0.1) | Gate D4: 118.4 m (x +113.3) | Gate C7 80.3 m (x -77.6) |
| D4 (SFO window) | N438WN, B737, SWA3975 | 25° | D4: ADS-B point -13.7 along / -2.2 cross of our stand, Δhdg -24° | D4 13.9 m (x -3.6) | D4: 12.7 m (x -3.1) | D4 12.7 m (x -3.1) | Gate D4: 9.1 m (x +4.7) | Gate D4 9.1 m (x +4.7) |
| D5 (SFO window) | N37422, B739, UAL1896 | 298° | D5: ADS-B point +278.2 along / -218.9 cross of our stand, Δhdg +46° | E5 10.2 m (x +0.1) | D5: 356.6 m (x -53.6) | E5 9.0 m (x +0.1) | Gate D5: 353.7 m (x -47.8) | Gate E5 19.9 m (x +15.3) |
| D5 (occupancy) | N77559, B39M, UAL8255 | 343° | D5: ADS-B point -7.0 along / -0.6 cross of our stand, Δhdg +2° | D5 7.0 m (x +0.8) | D5: 3.7 m (x +0.7) | D5 3.7 m (x +0.7) | Gate D5: 9.8 m (x +3.3) | Gate D5 9.8 m (x +3.3) |
| D6 (SFO window) | N17233, B738, UAL1329 | 163° | D6: ADS-B point +997.4 along / +68.6 cross of our stand, Δhdg +134° | F21 24.7 m (x +0.4) | D6: 1001.0 m (x -676.5) | F21 23.5 m (x +0.4) | Gate D6: 1000.7 m (x -678.3) | Gate F21 6.3 m (x +0.7) |
| D6 (SFO window) | N8936Q, B38M, SWA4108 | 298° | D6: ADS-B point -7.0 along / +0.7 cross of our stand, Δhdg -1° | D6 7.0 m (x -0.9) | D6: 5.8 m (x -0.8) | D6 5.8 m (x -0.8) | Gate D6: 6.3 m (x +1.9) | Gate D6 6.3 m (x +1.9) |
| D6 (SFO window) | N932WN, B737, SWA3546 | 298° | D6: ADS-B point -10.0 along / +0.7 cross of our stand, Δhdg -1° | D6 10.0 m (x -0.9) | D6: 8.8 m (x -0.9) | D6 8.8 m (x -0.9) | Gate D6: 9.1 m (x +1.8) | Gate D6 9.1 m (x +1.8) |
| D6 (occupancy) | N8540V, B738, SWA4760 | 298° | D6: ADS-B point -7.0 along / +0.7 cross of our stand, Δhdg -1° | D6 7.0 m (x -0.9) | D6: 5.8 m (x -0.8) | D6 5.8 m (x -0.8) | Gate D6: 6.3 m (x +1.9) | Gate D6 6.3 m (x +1.9) |
| D7 (SFO window) | N8329B, B738, SWA3557 | 278° | D7: ADS-B point -9.7 along / +0.2 cross of our stand, Δhdg -2° | D7 9.7 m (x -0.6) | D7: 8.5 m (x -0.5) | D7 8.5 m (x -0.5) | Gate D7: 9.9 m (x +1.7) | Gate D7 9.9 m (x +1.7) |
| D8 (SFO window) | N57868, B753, UAL1922 | 28° | D8: ADS-B point +821.4 along / +157.4 cross of our stand, Δhdg -108° | F16 2.0 m (x +1.3) | D8: 837.5 m (x +831.7) | F16 17.5 m (x +1.2) | Gate D8: 837.5 m (x +831.3) | Gate F16 2.5 m (x +2.5) |
| D9 (SFO window) | N47360, B38M, UAL1627 | 270° | D9: ADS-B point -13.2 along / +4.6 cross of our stand, Δhdg -12° | D9 14.0 m (x -7.4) | D9: 12.9 m (x -7.1) | D9 12.9 m (x -7.1) | Gate D9 D10: 5.6 m (x -4.2) | Gate D9 D10 5.6 m (x -4.2) |
| D9 (SFO window) | N37305, B38M, UAL1604 | 163° | D9: ADS-B point +270.8 along / +373.2 cross of our stand, Δhdg +94° | E12 103.6 m (x +0.4) | D9: 461.8 m (x -242.6) | (no ref) 18.3 m (x -0.5) | Gate D9 D10: 465.1 m (x -250.1) | Gate E12 95.1 m (x -3.7) |
| D9 (SFO window) | N4901U, A320, UAL626 | 343° | D9: ADS-B point +27.7 along / -138.5 cross of our stand, Δhdg -86° | D5 5.5 m (x +1.7) | D9: 141.5 m (x +39.5) | D5 2.5 m (x +1.6) | Gate D9 D10: 144.5 m (x +47.0) | Gate D5 8.7 m (x +4.2) |
| D9 (SFO window) | N806UA, A319, UAL1490 | 267° | D9: ADS-B point -9.2 along / +4.2 cross of our stand, Δhdg -10° | D9 10.1 m (x -5.7) | D9: 9.0 m (x -5.4) | D9 9.0 m (x -5.4) | Gate D9 D10: 2.9 m (x -2.9) | Gate D9 D10 2.9 m (x -2.9) |
| E10U (SFO window) | N17452, B39M, UAL2432 | 138° | E10: ADS-B point -11.0 along / +0.7 cross of our stand, Δhdg +0° | E10 11.0 m (x -0.7) | E10: 9.8 m (x -0.7) [2 ways] | E10 9.8 m (x -0.7) | Gate E8 E10: 11.9 m (x -2.4) | Gate E8 E10 11.9 m (x -2.4) |
| E10U (SFO window) | N37549, B39M, UAL1905 | 217° | E10: ADS-B point +20.5 along / -52.6 cross of our stand, Δhdg -79° | E13 10.0 m (x -0.4) | E10: 56.9 m (x +31.6) [2 ways] | (no ref) 8.2 m (x +8.1) | Gate E8 E10: 54.6 m (x +29.5) | Gate E13 15.5 m (x -15.5) |
| E10U (SFO window) | N85373, E75L, SKW5583 | 138° | E10: ADS-B point -20.5 along / +0.6 cross of our stand, Δhdg +0° | E10 20.5 m (x -0.6) | E10: 19.3 m (x -0.6) [2 ways] | (no ref) 14.8 m (x -0.6) | Gate E8 E10: 21.2 m (x -2.3) | Gate E8 E10 21.2 m (x -2.3) |
| E11U (SFO window) | N17321, B38M, UAL643 | 262° | E11: ADS-B point -12.0 along / +0.1 cross of our stand, Δhdg -0° | E11 12.0 m (x -0.1) | E11: 10.8 m (x -0.1) | (no ref) 10.0 m (x -1.3) | Gate E9 E11: 21.9 m (x -17.4) | Gate E9 E11 21.9 m (x -17.4) |
| E12 (SFO window) | N37305, B38M, UAL1604 | 163° | E12: ADS-B point -103.3 along / -0.0 cross of our stand, Δhdg +1° | E12 103.3 m (x +1.3) | E12: 43.7 m (x +0.6) | (no ref) 18.0 m (x +0.4) | Gate E12: 94.8 m (x -2.8) | Gate E12 94.8 m (x -2.8) |
| E12 (SFO window) | N14531, A21N, UAL1604 | 267° | E12: ADS-B point +280.0 along / -250.1 cross of our stand, Δhdg -103° | D9 7.9 m (x -7.2) | E12: 376.3 m (x +215.8) | D9 7.3 m (x -7.0) | Gate E12: 379.3 m (x +223.9) | Gate D9 D10 6.8 m (x -4.4) |
| E12 (SFO window) | N14235, B738, UAL433 | 163° | E12: ADS-B point -27.8 along / -0.3 cross of our stand, Δhdg +1° | E12 27.8 m (x +0.7) | E12: 26.6 m (x +0.7) | E12 26.6 m (x +0.7) | Gate E12: 19.5 m (x -3.4) | Gate E12 19.5 m (x -3.4) |
| E13T (SFO window) | N485UA, A320, UAL2818 | 205° | E13: ADS-B point -21.8 along / -127.5 cross of our stand, Δhdg +13° | E9 80.0 m (x +78.9) | E13: 129.1 m (x +120.1) | (no ref) 3.2 m (x -1.6) | Gate E13: 113.2 m (x +112.2) | Gate E9 E11 81.6 m (x +81.6) |
| E13T (SFO window) | N17335, B38M, UAL2818 | 217° | E13: ADS-B point -11.1 along / -0.1 cross of our stand, Δhdg +1° | E13 11.1 m (x +0.4) | E13: 9.9 m (x +0.3) | (no ref) 9.2 m (x +8.8) | Gate E13: 14.8 m (x -14.8) | Gate E13 14.8 m (x -14.8) |
| E2 (occupancy) | N605UX, E75L, SKW5733 | 225° | E2: ADS-B point -13.9 along / +1.0 cross of our stand, Δhdg -0° | E2 13.9 m (x -1.1) | E2: 12.7 m (x -1.1) | E2 12.7 m (x -1.1) | Gate E2: 53.6 m (x -53.1) | Gate E1 32.1 m (x -7.9) |
| E2 (SFO window) | N108SY, E75L, SKW5560 | 208° | E2: ADS-B point -101.0 along / +5.3 cross of our stand, Δhdg +16° | E10 81.3 m (x -77.3) | E2: 28.5 m (x -0.7) | E6 5.0 m (x -0.6) | Gate E2: 98.7 m (x -32.3) | Gate E8 E10 82.9 m (x -78.4) |
| E3 (SFO window) | N85370, E75L, SKW5636 | 188° | E3: ADS-B point -15.9 along / -0.0 cross of our stand, Δhdg +0° | E3 15.9 m (x +0.0) | E3: 14.7 m (x +0.0) | (no ref) 10.6 m (x +4.5) | Gate E3: 61.7 m (x -60.7) | Gate E2 11.2 m (x -1.6) |
| E4 (SFO window) | N67815, B739, UAL1151 | 284° | E4: ADS-B point -8.6 along / +1.6 cross of our stand, Δhdg +1° | E4 8.8 m (x -1.5) | E4: 7.6 m (x -1.5) | E4 7.6 m (x -1.5) | Gate E4: 28.4 m (x +16.3) | Gate E4 28.4 m (x +16.3) |
| E5 (SFO window) | N77552, B39M, UAL638 | 298° | E5: ADS-B point -9.9 along / -0.1 cross of our stand, Δhdg +0° | E5 9.9 m (x +0.1) | E5: 8.7 m (x +0.1) | E5 8.7 m (x +0.1) | Gate E5: 19.7 m (x +15.4) | Gate E5 19.7 m (x +15.4) |
| E6 (SFO window) | N37368, B38M, UAL369 | 166° | E6: ADS-B point -100.9 along / -0.8 cross of our stand, Δhdg -11° | E8 78.8 m (x -62.0) | E6: 11.7 m (x +0.2) [2 ways] | E6 11.7 m (x +0.2) | Gate E6: 81.0 m (x -63.2) | Gate E8 E10 80.5 m (x -78.7) |
| E6 (SFO window) | N14540, A21N, UAL1812 | 166° | E6: ADS-B point +69.0 along / -284.5 cross of our stand, Δhdg -11° | D12 87.2 m (x -0.1) | E6: 293.0 m (x +292.6) [2 ways] | D12 15.6 m (x -0.8) | Gate E6: 255.3 m (x +247.4) | Gate D14 85.9 m (x -0.3) |
| F10 (SFO window) | N933EV, CRJ2, SKW5796 | 183° | F10: ADS-B point -6.1 along / -0.4 cross of our stand, Δhdg -5° | F10 6.1 m (x -0.2) | F10: 4.9 m (x -0.1) | F10 4.9 m (x -0.1) | Gate F9 F10: 33.9 m (x +32.7) | Gate F8 9.0 m (x -8.6) |
| F12 (SFO window) | N18243, B738, UAL2177 | 28° | F12: ADS-B point -19.0 along / -1.3 cross of our stand, Δhdg -0° | F12 19.1 m (x +1.2) | F12: 17.9 m (x +1.2) | F12 17.9 m (x +1.2) | Gate F12: 12.4 m (x +2.1) | Gate F12 12.4 m (x +2.1) |
| F12 (SFO window) | N77537, B738, UAL1799 | 25° | F12: ADS-B point -16.2 along / -1.4 cross of our stand, Δhdg +2° | F12 16.2 m (x +2.1) | F12: 15.0 m (x +2.0) | F12 15.0 m (x +2.0) | Gate F12: 9.6 m (x +2.7) | Gate F12 9.6 m (x +2.7) |
| F13 (SFO window) | N33286, B738, UAL2262 | 208° | F13: ADS-B point -28.4 along / +1.8 cross of our stand, Δhdg -0° | F13 28.5 m (x -2.0) | F13: 25.2 m (x -2.0) | F13 25.2 m (x -2.0) | Gate F13: 18.7 m (x -1.9) | Gate F13 18.7 m (x -1.9) |
| F14 (SFO window) | N38268, B738, UAL1597 | 28° | F14: ADS-B point -18.2 along / -1.9 cross of our stand, Δhdg -0° | F14 18.3 m (x +1.7) | F14: 17.1 m (x +1.7) | F14 17.1 m (x +1.7) | Gate F14: 8.6 m (x +1.8) | Gate F14 8.6 m (x +1.8) |
| F15 (SFO window) | N771UA, B772, UAL1777 | — | F15: ADS-B point -10.1 along / +72.1 cross of our stand | F22 16.8 m | F15: 66.3 m | F22 13.5 m | Gate F15: 72.8 m | Gate F22 4.0 m |
| F16 (SFO window) | N37307, B38M, UAL1577 | 25° | F16: ADS-B point -9.5 along / -0.1 cross of our stand, Δhdg +2° | F16 9.5 m (x +0.5) | F16: 25.4 m (x +1.2) | F16 25.4 m (x +1.2) | Gate F16: 8.7 m (x +1.6) | Gate F16 8.7 m (x +1.6) |
| F18 (SFO window) | N933EV, CRJ2, SKW5566 | 56° | F18: ADS-B point -10.0 along / -0.9 cross of our stand, Δhdg -3° | F18 10.0 m (x +0.3) | F18: 8.8 m (x +0.4) | F18 8.8 m (x +0.4) | Gate F18 F17: 44.2 m (x +15.8) | Gate F19 29.7 m (x -26.7) |
| F20 (SFO window) | N37313, B38M, UAL1257 | 118° | F20: ADS-B point -10.8 along / -0.5 cross of our stand, Δhdg -0° | F20 10.8 m (x +0.4) | F20: 9.6 m (x +0.4) | F20 9.6 m (x +0.4) | Gate F20: 12.6 m (x +1.3) | Gate F20 12.6 m (x +1.3) |
| F21 (SFO window) | N17459, None, UAL2380 | 163° | F21: ADS-B point -23.5 along / -0.1 cross of our stand, Δhdg -0° | F21 23.5 m (x +0.0) | F21: 22.3 m (x +0.0) | F21 22.3 m (x +0.0) | Gate F21: 5.1 m (x +0.4) | Gate F21 5.1 m (x +0.4) |
| F22 (SFO window) | N17122, B752, UAL1343 | 208° | F22: ADS-B point -143.9 along / -74.1 cross of our stand, Δhdg -2° | F15 142.9 m (x -0.7) | F22: 86.3 m (x +72.9) | (no ref) 27.3 m (x -25.3) | Gate F22: 150.4 m (x +70.4) | Gate F15 135.3 m (x -1.7) |
| F22 (SFO window) | N57863, B753, UAL1723 | 205° | F22: ADS-B point -16.7 along / +0.7 cross of our stand, Δhdg +1° | F22 16.8 m (x -0.3) | F22: 13.5 m (x -0.4) | F22 13.5 m (x -0.4) | Gate F22: 4.0 m (x -0.9) | Gate F22 4.0 m (x -0.9) |
| F5 (SFO window) | N77537, B738, UAL2322 | 298° | F5: ADS-B point -11.9 along / +0.8 cross of our stand, Δhdg +2° | F5 12.0 m (x -0.4) | F5: 10.8 m (x -0.5) | F5 10.8 m (x -0.5) | Gate F5: 7.8 m (x +5.5) | Gate F5 7.8 m (x +5.5) |
| F5 (SFO window) | N73445, B739, UAL2322 | 28° | F5: ADS-B point +135.0 along / -82.6 cross of our stand, Δhdg -88° | F14 19.2 m (x +1.2) | F5: 159.3 m (x +139.0) | F14 18.0 m (x +1.2) | Gate F5: 166.8 m (x +144.2) | Gate F14 9.4 m (x +1.2) |
| F6 (SFO window) | N85373, E75L, SKW5433 | 290° | F6: ADS-B point -11.2 along / +0.6 cross of our stand, Δhdg -2° | F6 11.2 m (x -0.9) | F6: 10.0 m (x -0.9) | F6 10.0 m (x -0.9) | Gate F6: 17.7 m (x -1.6) | Gate F6 17.7 m (x -1.6) |
| F6 (occupancy) | N617UX, E75L, SKW430A | 290° | F6: ADS-B point -11.0 along / +1.2 cross of our stand, Δhdg -2° | F6 11.1 m (x -1.5) | F6: 9.9 m (x -1.5) | F6 9.9 m (x -1.5) | Gate F6: 17.6 m (x -2.3) | Gate F6 17.6 m (x -2.3) |
| F6 (SFO window) | N607UX, E75L, SKW5464 | 298° | F6: ADS-B point -15.2 along / +35.2 cross of our stand, Δhdg -10° | F7 9.9 m (x -0.2) | F6: 37.8 m (x -37.1) | F7 8.7 m (x -0.2) | Gate F6: 41.7 m (x -38.9) | Gate F7 10.2 m (x +5.5) |
| F6 (SFO window) | N612UX, E75L, SKW5841 | 290° | F6: ADS-B point -12.0 along / +0.2 cross of our stand, Δhdg -2° | F6 12.0 m (x -0.5) | F6: 10.8 m (x -0.5) | F6 10.8 m (x -0.5) | Gate F6: 18.5 m (x -1.2) | Gate F6 18.5 m (x -1.2) |
| F7 (SFO window) | N131SY, E75L, SKW5519 | 298° | F7: ADS-B point -11.1 along / +0.8 cross of our stand, Δhdg -0° | F7 11.1 m (x -0.8) | F7: 9.9 m (x -0.8) | F7 9.9 m (x -0.8) | Gate F7: 10.9 m (x +4.9) | Gate F7 10.9 m (x +4.9) |
| F7 (SFO window) | N616UX, E75L, SKW5452 | 298° | F7: ADS-B point -11.1 along / +0.8 cross of our stand, Δhdg -0° | F7 11.1 m (x -0.8) | F7: 9.9 m (x -0.8) | F7 9.9 m (x -0.8) | Gate F7: 10.9 m (x +4.9) | Gate F7 10.9 m (x +4.9) |
| F8 (SFO window) | N78361, E75L, SKW5693 | 267° | F8: ADS-B point -114.7 along / -4.1 cross of our stand, Δhdg +0° | F8 114.8 m (x +4.4) | F8: 40.6 m (x +4.2) | (no ref) 26.1 m (x +10.3) | Gate F8: 117.8 m (x +15.5) | Gate F8 117.8 m (x +15.5) |
| F8 (SFO window) | N641SY, E75L, SKW5453 | 267° | F8: ADS-B point -10.7 along / +0.7 cross of our stand, Δhdg +0° | F8 10.7 m (x -0.7) | F8: 9.5 m (x -0.7) | F8 9.5 m (x -0.7) | Gate F8: 16.4 m (x +10.4) | Gate F8 16.4 m (x +10.4) |
| G1 (SFO window) | N26967, B789, UAL893 | 198° | G1: ADS-B point -14.7 along / -2.6 cross of our stand, Δhdg +9° | G1 15.0 m (x +4.9) | G1: 11.8 m (x +4.4) | G1 11.8 m (x +4.4) | Gate G1 G2: 6.2 m (x +0.6) | Gate G1 G2 6.2 m (x +0.6) |
| G10 (SFO window) | N24993, B789, UAL115 | 207° | G10: ADS-B point -16.6 along / +0.8 cross of our stand, Δhdg +2° | G10 16.6 m (x -0.3) | G10: 13.3 m (x -0.4) | G10 13.3 m (x -0.4) | Gate G9 G10: 67.6 m (x -67.5) | Gate G13 G14 8.0 m (x +6.7) |
| G13S (SFO window) | N2135U, B77W, UAL1175 | 155° | G13: ADS-B point -14.7 along / +0.1 cross of our stand, Δhdg +3° | G13 14.7 m (x +0.5) | G13: 11.4 m (x +0.4) | G13 11.4 m (x +0.4) | Gate G13 G14: 50.4 m (x -48.6) | Terminal G 4.3 m (x +1.3) |
| G13S (SFO window) | JA791A, B77W, ANA8 | 155° | G13: ADS-B point -18.8 along / +1.2 cross of our stand, Δhdg +3° | G13 18.8 m (x -0.4) | G13: 15.5 m (x -0.5) | G13 15.5 m (x -0.5) | Gate G13 G14: 50.3 m (x -49.5) | Terminal G 8.2 m (x +0.4) |
| G2 (SFO window) | N2333U, B77W, UAL869 | 208° | G2: ADS-B point -12.6 along / +1.4 cross of our stand, Δhdg -1° | G2 12.6 m (x -1.6) | G2: 9.4 m (x -1.6) | G2 9.4 m (x -1.6) | Gate G1 G2: 77.3 m (x -77.3) | Terminal G 4.3 m (x -4.0) |
| G3 (SFO window) | N784UA, B772, UAL35 | 42° | G3: ADS-B point -14.2 along / +1.5 cross of our stand, Δhdg +1° | G3 14.3 m (x -1.3) | G3: 11.0 m (x -1.4) | G3 11.0 m (x -1.4) | Gate G3 G4: 79.3 m (x -78.1) | Terminal G 6.1 m (x +5.7) |
| G4 (SFO window) | N29989, B789, UAL1340 | 30° | G4: ADS-B point -11.7 along / -0.2 cross of our stand, Δhdg -2° | G4 11.7 m (x -0.1) | G4: 8.4 m (x -0.0) | G4 8.4 m (x -0.0) | Gate G3 G4: 7.8 m (x +5.8) | Gate G3 G4 7.8 m (x +5.8) |
| G5 (SFO window) | N2341U, B77W, UAL189 | 208° | G5: ADS-B point -9.0 along / +1.8 cross of our stand, Δhdg -1° | G5 9.2 m (x -1.9) | G5: 6.0 m (x -1.9) | G5 6.0 m (x -1.9) | Gate G5 G6: 3.7 m (x -3.3) | Gate G5 G6 3.7 m (x -3.3) |
| G5 (SFO window) | N434UA, A320, UAL1593 | 104° | G5: ADS-B point +349.1 along / -729.2 cross of our stand, Δhdg +103° | B11 3.9 m (x -3.8) | G5: 809.9 m (x -511.6) | B11 4.4 m (x -3.7) | Gate G5 G6: 811.7 m (x -518.3) | Gate B15 B16 41.1 m (x +39.7) |
| G6 (SFO window) | N796UA, B772, UAL194 | 208° | G6: ADS-B point -13.5 along / -0.4 cross of our stand, Δhdg -0° | G6 13.5 m (x +0.3) | G6: 10.2 m (x +0.4) | G6 10.2 m (x +0.4) | Gate G5 G6: 73.8 m (x -73.8) | Terminal G 3.0 m (x +1.7) |
| G6 (SFO window) | N68802, B739, UAL1227 | 28° | G6: ADS-B point -460.3 along / -716.9 cross of our stand, Δhdg +180° | D12 92.6 m (x +87.5) | G6: 797.7 m (x -716.8) | D16 21.6 m (x +0.4) | Gate G5 G6: 784.1 m (x -639.6) | Gate D14 91.5 m (x +86.7) |
| G6 (SFO window) | N22992, B789, UAL927 | 207° | G6: ADS-B point -12.9 along / +0.7 cross of our stand, Δhdg +1° | G6 12.9 m (x -0.5) | G6: 9.6 m (x -0.5) | G6 9.6 m (x -0.5) | Gate G5 G6: 74.9 m (x -74.9) | Terminal G 2.0 m (x +0.6) |
| G7 (SFO window) | N854UA, A319, UAL822 | 28° | G7: ADS-B point -30.1 along / +0.1 cross of our stand, Δhdg -0° | G7 30.1 m (x -0.2) | G7: 26.8 m (x -0.2) | G7 26.8 m (x -0.2) | Gate G7 G8: 22.9 m (x +6.8) | Gate G7 G8 22.9 m (x +6.8) |
| G7 (SFO window) | N61109, B789, UAL930 | 27° | G7: ADS-B point -11.3 along / +0.4 cross of our stand, Δhdg +1° | G7 11.3 m (x -0.2) | G7: 8.0 m (x -0.2) | G7 8.0 m (x -0.2) | Gate G7 G8: 7.3 m (x +6.6) | Gate G7 G8 7.3 m (x +6.6) |
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
| B/inf | 1, -1.3 (-1.3…-1.3) | 1, -1.2 (-1.2…-1.2) |
| B/obs | 1, +6.5 (+6.5…+6.5) | 5, -1.2 (-1.2…-1.2) |
| C/inf | 8, -2.6 (-8.7…+3.1) | 17, -1.2 (-1.2…-1.2) |
| C/obs | 17, -1.1 (-15.4…+9.3) | 43, -1.2 (-1.2…-1.2) |
| CL/inf | 1, -1.4 (-1.4…-1.4) | 1, -3.5 (-3.5…-3.5) |
| CL/obs | 7, -8.6 (-18.5…+3.8) | 8, -1.2 (-1.2…+15.9) |
| D/inf | 2, -3.9 (-10.2…+2.4) | 2, -3.3 (-3.3…-3.3) |
| E/inf | 3, -8.6 (-16.8…+2.4) | 4, -3.3 (-6.5…-3.3) |
| E/obs | 2, -8.0 (-9.3…-6.7) | 3, -3.3 (-3.3…-3.3) |
| EL/inf | 8, -9.9 (-15.0…-4.6) | 13, -3.3 (-3.3…-3.3) |
| EL/obs | 5, -10.6 (-12.9…-7.7) | 8, -3.3 (-8.3…-3.3) |
| F/inf | 1, -10.6 (-10.6…-10.6) | 2, -3.3 (-3.3…-3.3) |
| F/obs | 1, -11.4 (-11.4…-11.4) | 1, -3.3 (-3.3…-3.3) |
| all/inf | 24, -6.7 (-16.8…+3.1) | 40, -3.3 (-6.5…-1.2) |
| all/obs | 33, -4.4 (-18.5…+9.3) | 68, -1.2 (-8.3…+15.9) |
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
| A1 | EL · inf | A1: 3.3 m (-3.3 / -0.0, +0°) | — · own name at 48 m |  | agree | same as OSM | 2 / 0 / 1 |
| A2 | EL · inf | A2 ⟲: 3.3 m (-3.3 / -0.0, -0°) | Gate A1 A2: 6.5 m (-4.6 / -4.7, -1°) · C |  | agree with OSM; X-Plane differs | same as OSM | 2 / 1 / 2 |
| A4 | C · obs | A3: 1.2 m (-1.2 / -0.0, -0°) | Gate A3 A4 A5: 10.3 m (+9.3 / -4.4, +2°) · D |  | agree with OSM; X-Plane differs | DIFFERS from OSM (A3) · MISNAMED? position = OSM A3 · OSM has other positions here: A3 | 1 / 0 / 1 |
| A5 | EL · inf | A5: 3.3 m (-3.3 / +0.0, -0°) | Gate A9 A10: 6.9 m (-6.6 / -2.2, -0°) · own name at 68 m · E |  | agree | same as OSM · X-Plane name A9/A10 | 2 / 1 / 2 |
| A6 | F · inf | A6: 3.3 m (-3.3 / +0.0, -0°) | Gate A6 A7 A8: 13.0 m (-10.1 / -8.2, -2°) · F |  | agree with OSM; X-Plane differs | same as OSM | 2 / 0 / 2 |
| A8 | EL · inf | A8: 3.3 m (-3.3 / -0.0, +0°) | Gate A11: 9.2 m (-9.1 / -0.8, -2°) · own name at 72 m · E |  | agree | same as OSM · X-Plane name A11 | 2 / 1 / 2 |
| A9 | EL · inf | A9: 3.3 m (-3.3 / +0.0, +0°) | Gate A12: 10.1 m (-10.0 / +1.0, -0°) · own name at 74 m · E |  | agree | same as OSM · X-Plane name A12 | 2 / 1 / 2 |
| A10 | EL · inf | A10: 3.3 m (-3.3 / -0.0, +0°) | Gate A15: 9.9 m (-9.9 / +0.6, -0°) · own name at 147 m · E |  | agree | same as OSM · X-Plane name A15 | 2 / 1 / 1 |
| A11 | F · obs | A11: 3.3 m (-3.3 / -0.0, +0°) | Gate A13 A14: 11.5 m (-11.4 / -0.4, +1°) · own name at 80 m · D | A11: ours OK (aircraft +1.1 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · X-Plane name A13/A14 | 2 / 1 / 3 |
| A12 | E · inf | A12: 3.3 m (-3.3 / -0.0) | Terminal A: 16.9 m (-16.8 / +1.5, +2°) · own name at 119 m · C | A12: ours OK (aircraft -1.3 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| A13 | EL · obs | A13: 3.3 m (-3.3 / +0.0, -0°) | Terminal A: 9.3 m (-8.2 / +4.3, -31°) · own name at 41 m · C | A13V: ours OK (aircraft -0.0 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 2 / 1 / 1 |
| A15 | C · obs | A15: 1.2 m (-1.2 / -0.0, +0°) | Terminal A: 4.7 m (-4.4 / +1.6, -0°) · own name at 72 m · C | A15: ours OK (aircraft -0.9 m across our centreline, Δhdg +0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 2 / 1 |
| B2 | C · inf | B2: 1.2 m (-1.2 / -0.0, -0°) | — | B2: ours OK (aircraft -1.1 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 1 |
| B3 | C · obs | B3: 1.2 m (-1.2 / +0.0, -0°) | Gate B3: 10.9 m (-1.8 / -10.7, -21°) · C | B3: ours OK (aircraft -0.0 m across our centreline, Δhdg +0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| B4 | C · inf | B4: 1.2 m (-1.2 / +0.0, +0°) | — | B4: ours OK (aircraft -1.4 m across our centreline, no heading) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 1 |
| B5 | C · obs | B5: 1.2 m (-1.2 / +0.0, +0°) | — | B5: ours OK (aircraft -0.8 m across our centreline, Δhdg -3°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 0 |
| B5S | EL · inf | B5: 3.3 m (-3.3 / -0.0, +0°) | — |  | agree | DIFFERS from OSM (B5) · MISNAMED? position = OSM B5 · OSM has other positions here: B5 | 0 / 0 / 1 |
| B6 | C · obs | B6: 1.2 m (-1.2 / +0.0, +0°) | Gate B6: 17.1 m (-15.9 / +6.2, +15°) · C | B6: ours OK (aircraft -0.4 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 1 / 1 |
| B7 | C · obs | B7: 1.2 m (-1.2 / +0.0, -0°) | — · own name at 24 m | B7: ours OK (aircraft +0.5 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 0 |
| B8 | C · inf | (no ref): 1.2 m (-1.2 / -0.0, -0°) | Gate B7 B8: 18.4 m (+16.0 / +9.1, -43°) · C | B8: ours OK (aircraft +0.2 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | OSM position has no ref | 1 / 0 / 1 |
| B9 | C · obs | B9: 1.2 m (-1.2 / +0.0, +0°) | Gate B9: 13.2 m (-3.7 / -12.7, +2°) · C | B9: ours OK (aircraft +0.1 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| B10 | C · inf | B10: 1.2 m (-1.2 / +0.0, -0°) | Gate B10 B11: 16.5 m (+12.9 / -10.2, -16°) · D |  | agree with OSM; X-Plane differs | same as OSM | 1 / 0 / 0 |
| B11 | C · inf | B11: 1.2 m (-1.2 / +0.0, -0°) | — · own name at 49 m | B11S: ours OFF (aircraft -11.6 m across our centreline, Δhdg -15°) | OURS OFF (ADS-B + SFO) (vote: agree) | same as OSM | 1 / 0 / 1 |
| B11S | EL · obs | B11: 3.3 m (-3.3 / +0.0, -0°) | — |  | agree | DIFFERS from OSM (B11) · MISNAMED? position = OSM B11 · OSM has other positions here: B11 | 1 / 0 / 2 |
| B12 | C · obs | B12: 1.2 m (-1.2 / -0.0, -0°) | Gate B12: 10.4 m (-5.2 / -9.0, +2°) · C | B12: ours OK (aircraft -0.5 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| B13 | C · obs | B13: 1.2 m (-1.2 / +0.0, +0°) | Gate B13: 7.9 m (-4.9 / -6.2, +2°) · C | B13: ours OK (aircraft +0.8 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 1 / 1 |
| B14 | C · obs | B14: 1.2 m (-1.2 / +0.0, -0°) | Gate B14: 11.3 m (-5.4 / -9.9, +2°) · C | B14: ours OK (aircraft +0.1 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| B15 | C · inf | B15: 1.2 m (-1.2 / +0.0, +0°) | — · own name at 25 m |  | agree | same as OSM | 1 / 0 / 0 |
| B16 | C · obs | B16: 1.2 m (-1.2 / +0.0, +0°) | Gate B19 B20: 16.8 m (-2.7 / +16.6, +18°) · own name at 43 m · C | B16: ours OK (aircraft -1.6 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name B19/B20 | 1 / 1 / 2 |
| B16S | EL · obs | B16: 3.3 m (-3.3 / +0.0, +0°) | — |  | agree | DIFFERS from OSM (B16) · MISNAMED? position = OSM B16 · OSM has other positions here: B16 | 0 / 0 / 2 |
| B17 | C · obs | B17: 1.2 m (-1.2 / +0.0, -0°) | Gate B17: 10.1 m (-7.5 / -6.9, +2°) · C | B17: ours OK (aircraft +0.8 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 1 / 1 |
| B18 | C · obs | B18: 1.2 m (-1.2 / -0.0, -0°) | Gate B18: 11.2 m (-8.7 / -7.0, -6°) · C | B18: ours OFF (aircraft +3.2 m across our centreline, Δhdg -1°) | OURS OFF (ADS-B + SFO) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| B19 | C · obs | B19: 1.2 m (-1.2 / +0.0, -0°) | — · own name at 46 m | B19: ours OK (aircraft +0.0 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 0 |
| B20 | C · obs | B20: 1.2 m (-1.2 / +0.0, -0°) | — · own name at 71 m | B20: ours OK (aircraft -0.4 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 0 |
| B21 | C · obs | B21: 1.2 m (-1.2 / +0.0, +0°) | Gate B21: 16.3 m (-15.4 / -5.4, -6°) · C | B21: ours OK (aircraft -1.7 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| B22 | C · obs | B22: 1.2 m (-1.2 / +0.0, -0°) | Gate B22: 14.2 m (-14.0 / -2.8, -7°) · C | B22: ours OK (aircraft +1.0 m across our centreline, Δhdg +3°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| B23 | C · obs | B23: 1.2 m (-1.2 / +0.0, +0°) | Gate B23: 16.5 m (-3.1 / -16.2, +26°) · C | B23: ours OK (aircraft -0.3 m across our centreline, Δhdg -1°) | OURS OFF (ADS-B + SFO) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| B24 | C · obs | B24: 1.2 m (-1.2 / +0.0, -0°) | Gate B23: 14.0 m (+1.9 / +13.9, -8°) · own name at 33 m · C | B24: ours OK (aircraft +0.5 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name B23 · OSM has other positions here: B23 | 1 / 2 / 1 |
| B25 | C · obs | B25: 1.2 m (-1.2 / -0.0, +0°) | Gate B24: 4.1 m (-3.1 / +2.7, +1°) · own name at 45 m · C | B25: ours OK (aircraft -0.5 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · X-Plane name B24 | 1 / 1 / 1 |
| B26 | C · inf | B26: 1.2 m (-1.2 / +0.0, -0°) | Gate B25: 20.8 m (+7.4 / -19.5, +13°) · own name at 86 m · C | B26: ours OFF (aircraft -4.7 m across our centreline, no heading) | OURS OFF (ADS-B + SFO) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name B25 | 1 / 0 / 0 |
| B27 | C · obs | B27: 1.2 m (-1.2 / +0.0, +0°) | Gate B25: 13.2 m (+13.2 / -0.6, -27°) · own name at 75 m · C | B27: ours OK (aircraft -2.0 m across our centreline, no heading) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name B25 | 1 / 1 / 1 |
| C1 | C · obs | C1: 1.2 m (-1.2 / +0.0, -0°) | — | C1: ours OK (aircraft +0.6 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 1 |
| C3 | CL · obs | C3 ⟲: 1.2 m (-1.2 / -0.0, -0°) | — · own name at 52 m | C3: ours OK (aircraft +0.4 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 1 |
| C4 | C · obs | C4: 1.6 m (-1.2 / +1.1, +0°) | Gate C4: 5.9 m (+5.2 / +2.8, -4°) · C | C4: ours OK (aircraft -0.1 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| C5 | CL · inf | (no ref): 3.9 m (-3.5 / +1.8, +0°) · own name at 1 m | Gate C3: 1.4 m (-1.4 / +0.2, +8°) · own name at 47 m · C | C5: ours OK (aircraft +1.0 m across our centreline, Δhdg +0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · X-Plane name C3 | 1 / 0 / 1 |
| C6 | C · obs | C6: 1.2 m (-1.2 / +0.0, +0°) | Gate C6: 6.8 m (+5.4 / +4.1, -2°) · C | C6: ours OK (aircraft -0.3 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 1 / 1 |
| C7 | C · obs | C7: 1.2 m (-1.2 / -0.0, +0°) | Gate C5: 4.7 m (+3.6 / -3.0, +3°) · own name at 31 m · C | C7: ours OK (aircraft +0.3 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · X-Plane name C5 | 1 / 1 / 1 |
| C8 | D · inf | C8: 3.3 m (-3.3 / +0.0, -0°) | Gate C8: 10.7 m (-10.2 / +3.1, -0°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| C9 | CL · obs | C9: 1.2 m (-1.2 / +0.0, +0°) | Gate C7: 4.6 m (+3.8 / -2.7, +10°) · own name at 30 m · C | C9: ours OK (aircraft +0.2 m across our centreline, Δhdg +0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name C7 | 1 / 1 / 1 |
| C9V | D · inf | (no ref) ⟲: 3.3 m (-3.3 / -0.0, +0°) | Gate C7: 4.3 m (+2.4 / +3.6, -4°) · C |  | agree with OSM; X-Plane differs | OSM position has no ref · X-Plane name C7 · OSM has other positions here: C11/C9 | 0 / 1 / 1 |
| C10 | C · obs | C10: 1.2 m (-1.2 / +0.0, +0°) | Gate C11: 10.0 m (+0.2 / +10.0, +18°) · C | C10: ours OK (aircraft +1.8 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name C11 | 1 / 1 / 1 |
| C11 | C · obs | C11 ⟲: 1.2 m (-1.2 / -0.0, +0°) | Gate C9: 1.3 m (+1.2 / +0.5, +11°) · own name at 26 m · C | C11: ours OK (aircraft +0.3 m across our centreline, Δhdg -3°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name C9 | 1 / 1 / 1 |
| D1 | C · obs | D1 ⟲: 1.2 m (-1.2 / +0.0, +0°) | — · own name at 42 m | D1: ours OK (aircraft +1.2 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 1 |
| D3 | C · inf | D3 ⟲: 1.2 m (-1.2 / +0.0, -0°) | Gate D3: 3.1 m (+3.1 / +0.1, +3°) · C | D3: ours OFF (aircraft -4.3 m across our centreline, Δhdg -12°) | OURS OFF (ADS-B + SFO) (vote: agree) | same as OSM | 1 / 1 / 0 |
| D4 | C · inf | D4: 1.2 m (-1.2 / +0.0, -0°) | Gate D4: 10.0 m (-8.5 / +5.3, +15°) · C | D4: ours OFF (aircraft -2.2 m across our centreline, Δhdg -24°) | OURS OFF (ADS-B + SFO) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 1 / 1 |
| D5 | E · inf | D5: 3.3 m (-3.3 / -0.0, -0°) | Gate D5: 3.4 m (+2.4 / +2.4, -2°) · C | D5: ours OK (aircraft -0.6 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| D6 | C · obs | D6 ⟲: 1.2 m (-1.2 / +0.0, -0°) | Gate D6: 3.0 m (-1.1 / +2.8, +2°) · C | D6: ours OK (aircraft +0.7 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| D7 | C · obs | D7 ⟲: 1.2 m (-1.2 / -0.0, -0°) | Gate D7: 2.3 m (-0.1 / +2.3, -3°) · C | D7: ours OK (aircraft +0.2 m across our centreline, Δhdg -2°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| D8 | C · inf | D8 ⟲: 1.2 m (-1.2 / -0.0, +0°) | Gate D8: 3.7 m (-1.8 / +3.2, +2°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| D9 | C · inf | D9: 1.2 m (-1.2 / +0.0, +0°) | Gate D9 D10: 8.8 m (-8.7 / +1.4, -3°) · C | D9: ours OFF (aircraft +4.2 m across our centreline, Δhdg -10°) | OURS OFF (ADS-B + SFO) (vote: agree) | same as OSM | 1 / 1 / 1 |
| D10 | C · obs | D10 ⟲: 1.2 m (-1.2 / +0.0, +0°) | Gate D11: 8.8 m (-7.8 / +4.2, +3°) · own name at 40 m · C | D10: ours OK (aircraft +0.7 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name D11 | 1 / 1 / 1 |
| D11 | C · inf | D11 ⟲: 1.2 m (-1.2 / +0.0, -0°) | Gate D12: 5.7 m (-5.0 / -2.9, -1°) · own name at 31 m · C | D11: ours OK (aircraft -0.2 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · X-Plane name D12 | 1 / 1 / 1 |
| D12 | C · obs | D12 ⟲: 1.2 m (-1.2 / +0.0, +0°) | Gate D14: 1.3 m (-1.3 / -0.1, +1°) · own name at 33 m · C |  | agree | same as OSM · X-Plane name D14 | 1 / 1 / 1 |
| D14 | C · obs | D14 ⟲: 3.4 m (-1.2 / -3.2, -1°) | Gate D15: 2.6 m (+1.4 / -2.2, +1°) · own name at 37 m · C |  | agree with X-Plane; OSM differs | same as OSM · X-Plane name D15 | 1 / 1 / 1 |
| D15 | C · obs | D15: 1.2 m (-1.2 / -0.0, -0°) | Gate D16 D17: 1.5 m (+1.4 / -0.4, -1°) · own name at 39 m · C | D15: ours OK (aircraft -1.0 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · X-Plane name D16/D17 | 1 / 1 / 1 |
| D16 | C · inf | D16: 1.2 m (-1.2 / -0.0, -0°) | Gate D18: 3.5 m (-3.4 / +0.7, +1°) · own name at 65 m · C | D16: ours OK (aircraft +0.1 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · X-Plane name D18 | 1 / 1 / 1 |
| E2 | C · inf | E2 ⟲: 1.2 m (-1.2 / -0.0, -0°) | — · own name at 56 m | E2: ours OK (aircraft +1.0 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 1 |
| E3 | C · obs | E3 ⟲: 1.2 m (-1.2 / +0.0, +0°) | Gate E2: 5.2 m (-4.9 / -1.6, -1°) · own name at 61 m · C | E3: ours OK (aircraft -0.0 m across our centreline, Δhdg +0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · X-Plane name E2 | 1 / 1 / 1 |
| E4 | C · obs | E4 ⟲: 1.2 m (-1.2 / -0.0, +0°) | — · own name at 23 m | E4: ours OK (aircraft +1.6 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 0 |
| E5 | C · obs | E5 ⟲: 1.2 m (-1.2 / +0.0, -0°) | Gate E5: 15.5 m (+2.5 / +15.3, +0°) · C | E5: ours OK (aircraft -0.1 m across our centreline, Δhdg +0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 1 / 1 |
| E6 | C · obs | E6: 1.2 m (-1.2 / +0.0) | Gate E3: 1.7 m (-1.6 / -0.6, +3°) · own name at 66 m · C |  | agree | same as OSM · X-Plane name E3 | 1 / 1 / 1 |
| E7 | C · obs | E7 ⟲: 1.2 m (-1.2 / +0.0, -0°) | Gate E7: 18.2 m (-5.7 / +17.3, +1°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| E8 | C · inf | E8: 1.2 m (-1.2 / -0.0, -0°) | Gate E6: 2.3 m (+2.2 / +0.5, +1°) · own name at 36 m · C |  | agree | same as OSM · X-Plane name E6 · OSM has other positions here: E10A | 1 / 1 / 1 |
| E9 | C · obs | E9 ⟲: 1.2 m (-1.2 / -0.0, -0°) | Gate E9 E11: 13.6 m (+1.7 / +13.5, -19°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| E10 | C · inf | E10 ⟲: 1.2 m (-1.2 / -0.0, -0°) | Gate E8 E10: 1.9 m (+0.6 / -1.8, +3°) · C | E10U: ours OK (aircraft +0.6 m across our centreline, Δhdg +0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · OSM has other positions here: E10A | 1 / 1 / 1 |
| E11 | C · obs | E11: 1.2 m (-1.2 / +0.0, -0°) | Gate E9 E11: 17.3 m (+1.4 / -17.3, +11°) · C | E11U: ours OK (aircraft +0.1 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| E12 | CL · obs | E12 ⟲: 1.2 m (-1.2 / -0.0, -0°) | Gate E12: 9.5 m (-8.6 / -4.0, +12°) · C | E12: ours OK (aircraft -0.3 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 1 / 0 |
| E13 | C · obs | E13 ⟲: 1.2 m (-1.2 / +0.0, -0°) | Gate E13: 18.7 m (-11.3 / -14.8, -9°) · C | E13T: ours OK (aircraft -0.1 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 0 / 1 |
| F5 | C · obs | F5: 1.2 m (-1.2 / -0.0, +0°) | Gate F5: 8.7 m (-6.2 / +6.1, +10°) · B | F5: ours OK (aircraft +0.8 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 1 / 1 / 1 |
| F6 | B · obs | F6 ⟲: 1.2 m (-1.2 / +0.0, +0°) | Gate F6: 6.5 m (+6.5 / -0.5, +10°) · C | F6: ours OK (aircraft +0.2 m across our centreline, Δhdg -2°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 1 |
| F7 | B · inf | F7 ⟲: 1.2 m (-1.2 / +0.0, +0°) | Gate F7: 5.8 m (-1.3 / +5.7, -0°) · C | F7: ours OK (aircraft +0.8 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · OSM has other positions here: F8 | 1 / 1 / 1 |
| F8 | B · obs | F8 ⟲: 1.2 m (-1.2 / -0.0, -0°) | Gate F8: 11.3 m (+2.1 / +11.1, -12°) · C | F8: ours OK (aircraft +0.7 m across our centreline, Δhdg +0°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · OSM has other positions here: F7 | 1 / 1 / 1 |
| F9 | B · obs | F9 ⟲: 1.2 m (-1.2 / -0.0, -0°) | Gate F9 F10: 10.0 m (-9.2 / -4.0, +24°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| F10 | B · obs | F10 ⟲: 1.2 m (-1.2 / +0.0, -0°) | — · own name at 36 m | F10: ours OK (aircraft -0.4 m across our centreline, Δhdg -5°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 0 / 0 / 0 |
| F11 | E · obs | F11: 3.3 m (-3.3 / -0.0, -0°) | Gate F11: 9.3 m (-9.3 / -1.0, +0°) · D |  | agree | same as OSM | 2 / 2 / 1 |
| F12 | C · inf | F12 ⟲: 1.2 m (-1.2 / -0.0, +0°) | Gate F12: 6.9 m (-6.8 / +0.9, -1°) · C | F12: ours OK (aircraft -1.4 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| F13 | EL · inf | F13: 3.3 m (-3.3 / -0.0, -0°) | Gate F13: 9.8 m (-9.8 / +0.0, +1°) · D | F13: ours OK (aircraft +1.8 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 2 / 2 / 2 |
| F14 | CL · obs | F14: 1.2 m (-1.2 / +0.0, -0°) | Gate F14: 9.8 m (-9.8 / -0.0, -1°) · C | F14: ours OK (aircraft -1.9 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| F15 | EL · obs | F15 ⟲: 10.1 m (-8.3 / +5.8, +0°) | Gate F15: 7.7 m (-7.7 / -0.6, -6°) · C |  | agree with X-Plane; OSM differs | same as OSM | 2 / 2 / 2 |
| F16 | CL · obs | F16: 15.9 m (+15.9 / +0.0, +0°) | Gate F16: 1.4 m (-0.9 / +1.1, -1°) · C | F16: ours OK (aircraft -0.1 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| F17 | CL · obs | F17 ⟲: 1.2 m (-1.2 / -0.0, -0°) | Gate F18 F17: 15.0 m (-15.0 / -0.5, -0°) · C |  | agree | same as OSM | 1 / 1 / 1 |
| F18 | B · obs | F18: 1.2 m (-1.2 / -0.0, -0°) | — · own name at 35 m | F18: ours OK (aircraft -0.9 m across our centreline, Δhdg -3°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 0 / 0 / 0 |
| F19 | EL · inf | F19 ⟲: 3.3 m (-3.3 / +0.0, -0°) | Gate F19: 15.5 m (-15.0 / +4.0, -2°) · C |  | agree with OSM; X-Plane differs | same as OSM | 1 / 1 / 1 |
| F20 | CL · obs | F20 ⟲: 1.2 m (-1.2 / +0.0, +0°) | Gate F20: 1.9 m (+1.7 / +0.9, +2°) · C | F20: ours OK (aircraft -0.5 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 1 / 1 |
| F21 | CL · obs | F21 ⟲: 1.2 m (-1.2 / -0.0, +0°) | Gate F21: 18.5 m (-18.5 / +0.3, +1°) · C | F21: ours OK (aircraft -0.1 m across our centreline, Δhdg -0°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 1 / 0 / 1 |
| F22 | EL · obs | F22 ⟲: 3.3 m (-3.3 / -0.0, +0°) | Gate F22: 12.9 m (-12.9 / -0.3, +2°) · D | F22: ours OK (aircraft +0.7 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 2 / 1 / 1 |
| G1 | E · inf | G1 ⟲: 3.3 m (-3.3 / +0.0, +0°) | Gate G1 G2: 9.1 m (-8.6 / -3.0, +0°) · E | G1: ours OK (aircraft -2.6 m across our centreline, Δhdg +9°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 2 / 1 / 2 |
| G2 | EL · inf | G2 ⟲: 3.3 m (-3.3 / -0.0, -0°) | Terminal G: 11.3 m (-11.0 / -2.6, +1°) · own name at 76 m · E | G2: ours OK (aircraft +1.4 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 2 / 1 / 2 |
| G3 | E · obs | G3 ⟲: 3.3 m (-3.3 / -0.0, +0°) | Terminal G: 13.9 m (-11.9 / +7.2, -1°) · own name at 82 m · E | G3: ours OK (aircraft +1.5 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 2 / 2 / 2 |
| G4 | E · obs | G4: 3.3 m (-3.3 / -0.0, -0°) | Gate G3 G4: 8.8 m (-6.7 / +5.7, -1°) · E | G4: ours OK (aircraft -0.2 m across our centreline, Δhdg -2°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 2 / 2 / 2 |
| G5 | EL · obs | G5 ⟲: 3.3 m (-3.3 / +0.0, -0°) | Gate G5 G6: 10.7 m (-10.6 / -1.5, +0°) · E | G5: ours OK (aircraft +1.8 m across our centreline, Δhdg -1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 2 / 1 / 2 |
| G6 | EL · obs | G6 ⟲: 3.3 m (-3.3 / +0.0, +0°) | Terminal G: 11.1 m (-11.0 / +1.3, -0°) · own name at 75 m · E | G6: ours OK (aircraft +0.7 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM | 2 / 1 / 2 |
| G7 | EL · inf | G7 ⟲: 3.3 m (-3.3 / +0.0, -0°) | Gate G7 G8: 10.7 m (-8.2 / +7.0, -1°) · E | G7: ours OK (aircraft +0.4 m across our centreline, Δhdg +1°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM | 2 / 2 / 2 |
| G8 | EL · obs | G8 ⟲: 3.3 m (-3.3 / -0.0, -0°) | Gate G11 G12: 9.1 m (-9.0 / +1.2, +1°) · own name at 80 m · E |  | agree | same as OSM · X-Plane name G11/G12 | 2 / 1 / 2 |
| G9 | EL · inf | G9 ⟲: 3.3 m (-3.3 / +0.0, -0°) | Gate G9 G10: 16.7 m (-15.5 / +6.2, -0°) · E |  | agree with OSM; X-Plane differs | same as OSM | 2 / 2 / 2 |
| G10 | EL · inf | G10 ⟲: 3.3 m (-3.3 / +0.0, +0°) | Gate G13 G14: 14.0 m (-12.0 / +7.3, -1°) · own name at 69 m · E | G10: ours OK (aircraft +0.8 m across our centreline, Δhdg +2°) | agree (ADS-B + SFO confirm ours) (vote: agree with OSM; X-Plane differs) | same as OSM · X-Plane name G13/G14 | 2 / 2 / 2 |
| G12 (G11) | E · inf | (no ref): 6.5 m (-6.5 / -0.8, +5°) | Terminal G: 11.9 m (-5.1 / -10.8, -8°) · own name at 48 m · F |  | agree with OSM; X-Plane differs | OSM position has no ref · merged: SFO runs G12/G11 as separate stands (OSM has G11 here) | 2 / 0 / 1 |
| G13 (G14) | F · inf | G13 ⟲: 3.3 m (-3.3 / -0.0, +0°) | Terminal G: 10.7 m (-10.6 / +1.3, +5°) · own name at 57 m · F | G13S: ours OK (aircraft +1.2 m across our centreline, Δhdg +3°) | agree (ADS-B + SFO confirm ours) (vote: agree) | same as OSM · merged: SFO runs G13/G14 as separate stands | 2 / 2 / 2 |
<!--END:stands_table-->

### 4.5 Stand names by area

The SFO column is the union of stand names in SFO's AODB (flysfo `stands[]`) and gates with operations in DataSF, 18–31 Aug 2026. It is taken from `docs/research/gate_truth.md` §4 / `refs/cache/gate_truth/gates_report.json`, suffix letters removed.

<!--BEGIN:names_table-->
| Area | SFO stands in use (AODB ∪ DataSF, via gate_truth) | ours: own stands | ours: only as alias | OSM refs | X-Plane names | in SFO use but no own stand of ours | X-Plane names not in SFO's maps |
|---|---|---|---|---|---|---|---|
| A | A1 A2 A4 A5 A6 A8 A9 A10 A11 A12 A13 A15 | A1 A2 A4 A5 A6 A8 A9 A10 A11 A12 A13 A15 | — | A1 A2 A3 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14 A15 | A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14 A15 | — | — |
| B | B2 B3 B4 B5 B6 B7 B8 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | B2 B3 B4 B5 B5S B6 B7 B8 B9 B10 B11 B11S B12 B13 B14 B15 B16 B16S B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | — | B1 B2 B3 B4 B5 B6 B7 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | B3 B6 B7 B8 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | — | — |
| C | C1 C3 C4 C5 C6 C7 C8 C9 C10 C11 | C1 C3 C4 C5 C6 C7 C8 C9 C9V C10 C11 | — | C1 C3 C4 C5 C6 C7 C8 C9 C10 C11 | C2 C3 C4 C5 C6 C7 C8 C9 C11 | — | — |
| D | D1 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 | D1 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 | — | D1 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 | D1 D2 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 D17 D18 | — | — |
| E | E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 | E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 | — | E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 | E1 E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 | — | E1 |
| F | F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | — | F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | F1 F2 F3 F3A F4 F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | — | F1 F2 F3 F3A F4 |
| G | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G11 G12 G13 G14 G104 G105 | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G12 G13 | G11 G14 | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G11 G13 | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G11 G12 G13 G14 | G11 G14 G104 G105 | — |
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
| OSM | contact (at a terminal facade) | 25 | A7, A12 ⟨A12⟩, A14, B1, B20 ⟨B20⟩, B23 ⟨B23/B24⟩, B26 ⟨B26⟩, C5 ⟨C5⟩, E6 ⟨E6⟩, E10A ⟨E8/E10⟩, G11 ⟨G12⟩, (no ref) ×5, (no ref) ⟨A13⟩, (no ref) ⟨A1⟩, (no ref) ⟨A4⟩, (no ref) ⟨A6⟩, (no ref) ⟨C3⟩, (no ref) ⟨E11⟩, (no ref) ⟨E13⟩, (no ref) ⟨E3⟩, (no ref) ⟨G12⟩ |
| OSM | north field (maintenance / cargo / GA) | 95 | (no ref) ×92, 50-6, 50-7, 50-8 |
| OSM | terminal apron (remote / hardstand) | 54 | (no ref) ×53, (no ref) ⟨B19⟩ |
| OSM | west field (cargo, west of pier G) | 7 | (no ref) ×7 |
| X-Plane | contact (at a terminal facade) | 11 | Gate B15 B16 [D], Gate B26 B27 [C], Gate C2 [D], Gate D1 D2 [C], Gate E1 [C], Gate E4 [C], Gate F1 [C], Gate F2 [C], Gate F3 [C], Gate F4 [C], Terminal A [C] |
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
| 10L | 37-37-43.4594N 122-23-36.2107W | 5.5 | 0 | -0.0 / +0.0 | -0.0 / +0.0 | +0.0 | -3.3 / -0.7 | 0 (0) / 250 | +1.2 / -0.4 |
| 28R | 37-36-48.721N 122-21-25.708W | 13.0 | 300 | +0.0 / +0.0 | +0.0 / +0.0 | +0.0 | -0.3 / +0.1 | 90 (295) / 100 | -3.2 / +0.1 |
| 10R | 37-37-34.648N 122-23-35.1796W | 7.1 | 0 | -0.0 / -0.0 | -0.0 / -0.0 | +0.0 | +0.1 / -0.2 | 0 (0) / 250 | +2.9 / -0.1 |
| 28L | 37-36-42.163N 122-21-30.057W | 12.6 | 300 | +0.0 / +0.0 | +0.0 / +0.0 | +0.0 | +0.3 / +2.7 | 90 (295) / 100 | -0.4 / +0.0 |
| 1L | 37-36-28.4323N 122-22-58.5426W | 10.7 | 640 | +0.0 / -0.0 | +0.0 / -0.0 | +0.0 | +5.5 / +0.4 | 195 (640) / 0 | -9.7 / -0.7 |
| 19R | 37-37-35.3329N 122-22-14.1939W | 9.2 | 0 | -0.0 / +0.0 | -0.0 / +0.0 | +0.0 | -10.2 / -1.1 | 0 (0) / 0 | -2.2 / +0.3 |
| 1R | 37-36-22.7876N 122-22-51.7467W | 11.4 | 560 | +0.0 / -0.0 | +0.0 / -0.0 | +0.0 | +5.8 / -1.6 | 170 (558) / 0 | +0.7 / -1.5 |
| 19L | 37-37-38.4319N 122-22-1.599W | 10.5 | 0 | -0.0 / +0.0 | -0.0 / +0.0 | +0.0 | -9.6 / -0.8 | 0 (0) / 0 | +2.4 / -0.2 |
<!--END:runway_table-->

<!--BEGIN:threshold_table-->
| End | NASR displaced threshold: along / cross from runway end (m) | app threshold (end + disp along geo.js axis) − NASR DT (along / cross m) | NASR TORA / TODA / ASDA / LDA ft | position source, date |
|---|---|---|---|---|
| 28R | +91.5 / -0.0 | -0.1 / +0.0 | 11870 / 11870 / 11870 / 11236 | 3RD PARTY SURVEY, 2014/10/22 |
| 28L | +91.4 / +0.0 | +0.0 / -0.0 | 11381 / 11381 / 10981 / 10275 | 3RD PARTY SURVEY, 2014/10/22 |
| 1L | +195.1 / -0.0 | -0.0 / +0.0 | 7650 / 7650 / 7650 / 7010 | 3RD PARTY SURVEY, 2014/10/22 |
| 1R | +170.7 / -0.0 | -0.0 / +0.0 | 8650 / 8650 / 8650 / 8090 | 3RD PARTY SURVEY, 2014/10/22 |
<!--END:threshold_table-->

<!--BEGIN:length_table-->
| Runway | NASR published length | geodesic between NASR ends | app (geo.js planar frame) | app − geodesic |
|---|---|---|---|---|
| 10L/28R | 11870 ft = 3618.0 m | 3618.0 m | 3618.0 m | -0.00 m |
| 10R/28L | 11381 ft = 3468.9 m | 3469.0 m | 3469.0 m | +0.00 m |
| 1L/19R | 7650 ft = 2331.7 m | 2331.8 m | 2331.8 m | -0.00 m |
| 1R/19L | 8650 ft = 2636.5 m | 2636.5 m | 2636.5 m | +0.00 m |
<!--END:length_table-->

OSM `aeroway=stopway` ways (OSM uses them here for the paved areas beyond each end):

<!--BEGIN:stopway_table-->
| OSM way | nearest FAA end | length m | inner node along / cross from the end (m) | outer node along (m) | tags |
|---|---|---|---|---|---|
| way 510551650 | 10L | 269.8 | +1.2 / -0.4 | -268.6 | ref=10L/28R, surface=asphalt, width=61 |
| way 1065090263 | 10R | 231.4 | +2.9 / -0.0 | -228.4 | ref=10R/28L, surface=asphalt, width=61 |
| way 510551652 | 19L | 139.2 | +2.4 / -0.2 | -136.8 | ref=1R/19L, surface=asphalt, width=61 |
| way 23365562 | 19R | 134.6 | -2.2 / +0.3 | -136.8 | ref=1L/19R, surface=asphalt, width=61 |
| way 586154077 | 1L | 132.2 | -9.7 / -0.7 | -141.9 | length=2286, ref=1L/19R, surface=asphalt, width=61 |
| way 23365564 | 1R | 123.1 | +0.7 / -1.5 | -122.4 | length=2636, ref=1R/19L, surface=asphalt, width=61 |
| way 510551654 | 28L | 94.8 | -0.4 / +0.0 | -95.3 | ref=10R/28L, surface=asphalt, width=61 |
| way 510551656 | 28R | 91.4 | -3.2 / +0.1 | -94.6 | ref=10L/28R, width=61 |
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
