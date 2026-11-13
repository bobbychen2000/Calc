# Phase 1: the HWD airport data set (`data/hwd_airport.json` / `.js`)

Task G5, 2026-11-12. Built by `tools/build_airport.py` and checked by `tools/check_airport.py`. The build reads only
committed inputs and makes no network calls.

**Updated three times on the same day, and once on 2026-11-13:**
- **By the Phase 1 cross-check** (`docs/phase1_crosscheck.md`). The AL-5015 registration had a bug: the 28R end of the
  diagram's runway bar was found 76 m short. It was fixed in `tools/osm/xcheck_osm_faa.py`, which moved the hot spots,
  the label anchors, two apron-name matches and the terminal.
- **By the Phase 1 review fixes** (section 6). The review's findings changed:
  - the parking model, and the taxiways E and F;
  - several fields: ref, width, on_runway, the lighting schedule, `not_yet_sourced`;
  - the provenance of the committed inputs.

  Section 6 lists every finding with its outcome.
- **By the round-1 re-check fixes** (section 7). An independent re-check found that the review fix had turned taxiway E
  into a zig-zag, that `obs` counted one aircraft session two or three times, and several smaller defects. Section 7 lists
  each finding with its outcome.
- **By the round-2 re-check fixes** (section 8, 2026-11-13). A second independent re-check found that the round-1 taxiway
  moves had broken the taxi network at 22 joins, that a power-cycled parked aircraft still counted as two sessions, that
  the back row of a nested double row was missing from the unspotted list, and that the heading-less sizing disc left
  the tail out. Section 8 lists each finding with its outcome; sections 1-5 below describe the current build.

The numbers below are those of the current build. Sources, terms and notices are in `docs/ATTRIBUTION.md`. The file
itself is offered under **ODbL 1.0**.

## 1. What the file contains

The world frame is `ltp-nad83-2011-hwd` from `tools/common/hwd_frame.py`, the same as `js/geo.js`. x is east and z is
south, in metres, with the origin at the NASR ARP. y is the NAVD 88 height (that datum is inferred).

Every element has three fields:
- `src`: `obs` if a source saw it (FAA survey, OSM mapping, NAIP measurement, ADS-B observation), and `inf` if it was derived by a stated rule, from a schematic chart, by eye, or as a default.
- `refs`: keys of the top-level `sources` map.
- `evidence`: the reasoning, with the numbers.

Attribute-level `*_src` fields mark inferred parts of observed elements.

The JSON is 826 kB (826,197 bytes). The `.js` twin is `export const HWD_AIRPORT = …` with a licence header.

| Section | Count | src | Content and origin |
|---|---|---|---|
| `runways` | 2 | obs | See below this table. |
| `taxiways` | 65 | obs | OSM centrelines with ref, status and OSM tags: 61 open, 2 `abandoned`, 2 `disused`; 10.3 km in total, 9.5 km open. Fields on each way:<br>• `naip_paint`: its NAIP paint measurement, including faint-ridge sections.<br>• `ref_src` / `ref_note`: 3 OSM refs that AL-5015 does not support along the way are `inf` (section 2).<br>• `on_runway`: present on every way that enters a NASR runway rectangle; 13 ways overlap it by more than 50 m.<br>• `width`: an AC default marked inf on all; a NAIP grey-test width marked obs on 6 ways (≥ 5 stations, IQR ≤ 1.5 m), inf with a reason on 8 (IQR 3.6-21.9 m), no value on 125 (< 5 stations).<br>• `paint_offset_unsnapped`: 30 unmoved ways whose measured paint offsets are recorded (section 2).<br>• `naip_paint.junctions`: since round 2, every junction with another way is one shared vertex with one displacement (section 2); 22 unmoved ways have an end attached to a moved junction.<br>A1 carries the NASR wingspan limit of 100 ft, Z1 of 94 ft. A carries the remark "not visible from ATCT between B and C". |
| `taxilanes` | 78 | obs | OSM centrelines, 6.3 km in total. Two are moved as a whole onto a fit of their NAIP paint (section 2); one of them, 204801549, now starts at a shallow fork on taxiway E. |
| `aprons` | 9 | obs | OSM polygons. Names are only where OSM tags them or AL-5015 labels them (see after this table). |
| `holds` | 18 | obs | OSM holding-position nodes. 16 are moved onto the yellow bar measured on NAIP 2024. Each records the runway, its distance from the centreline in ft, and the bar direction and skew. |
| `hotspots` | 6 | **inf** | HS 1–HS 5. HS 5 is two ellipses, one on A1 and one on Z1. Each is an AL-5015 ellipse mapped to the world, with the CS hot-spot text and the OSM taxiway refs inside it. |
| `helipads` | 9 | obs | OSM polygons: 6 on the "Helicopter Ramp" and 3 on the north-east FBO ramp. They carry the NASR remark about transient helicopters. |
| `hangars` | 34 | obs (footprint) | OSM footprint, name and letter (A–Q, EX1, EX2; "Hanagar K" read as Hangar K, inf).<br>• **kind** is inf: 18 `t_hangar_row` and 16 `box_hangar`, from the footprint shape (minimum rectangle ratio ≥ 3, width ≤ 22 m, fill ≥ 0.85).<br>• The FBO **role** is inf: APP Jet Center and Signature Aviation, by name.<br>• `adsb_signal_edges_8m` counts adsb.lol signal starts and ends within 8 m. |
| `buildings` | 17 | obs | **Control tower:** OSM way 204803620 (man_made=tower, service=aircraft_control, height 15.85 m), matched to the AL-5015 TWR label and the NASR ATCT. Its beacon is inf.<br>**Fire station:** OSM node 368168603, a point only. It now carries the cross-check `deviation` [inf]: the AL-5015 block, with a building on NAIP, is 45 m east.<br>**Terminal / Airport Administration:** OSM way 1372203791, name inf, placed by the AL-5015 label leader.<br>**Other:** 14 OSM buildings inside the aerodrome, role unknown. |
| `markers` | 2 | obs | The windsock (OSM node; NASR: lighted) and the segmented circle around it. The circle is obs (NASR flag, NAIP). Its diameter of about 31.5 m was read by eye, so `diameter_src` is inf; its centring on the windsock gives `position_src` inf. |
| `parking` | 177 | 113 obs / 64 inf | Tie-downs, ramp spots, hangar aprons and helipad spots (section 3). |
| `unspotted_aircraft` | 48 | inf | Parked aircraft on NAIP 2024 that no spot stands for, found by eye; since round 2 the check's omission sweep (machine candidates, by-eye verdicts) looks for more (positions ±2 m; section 5). A known gap, not spots. |
| `al5015_labels` | 10 | inf | AL-5015 area labels placed by the diagram affine. |
| `not_placed` | 3 | obs / inf | Known features without a location: the UL94 self-serve fuel island; an unmapped paved helicopter area with four square pads south of 10R/28L (its spot ids are generated at build time); the official tie-down numbering. |
| `not_yet_sourced` | 4 | inf | What the data set still lacks, with candidate sources: signs, lighting fixtures, marking geometry beyond hold bars and thresholds, and five unlit wind cones (section 5). |

**Runways** (2, obs). These come from FAA NASR:
- end coordinates and elevations, and the surveyed displaced thresholds (826 / 676 ft);
- length, width, surface, treatment and condition;
- marking type PIR / NPI, MIRL and REIL;
- VASI / PAPI code, glide angle and TCH;
- traffic-pattern side: NASR flag plus the CS, so 28L is left;
- TPA 652 / 852 ft MSL, strength, gradient, the distance-remaining-sign remarks, and the NASR obstacle fields;
- the pavement outline, which is the NASR rectangle checked against NAIP and OSM.

New since the review: **lighting when the tower is closed**, from NASR remark LGT_SKED and the CS SERVICE line:
- `vgsi.when_tower_closed`: the VASI of 10R / 28L operates SS–SR; the PAPI of 10L / 28R is unavailable.
- `reil.when_tower_closed`: unavailable.
- `edge_lights.when_tower_closed`: MIRL 10R/28L preset low and pilot-controlled on CTAF.
- `closed_when_tower_closed`: true for 10L/28R.

Fixture positions are not sourced (`vgsi.position` null).

**Apron names:**
- From OSM: Green Ramp, 28L Run-up, 28R Runup, 10L Runup, Helicopter Ramp.
- From AL-5015, inferred: 5 aprons carry 6 AL-5015 labels; the West Hangars apron carries two.
  - The **GA TRANSIENT RAMP** text straddles the OSM Helicopter Ramp (38 % of its text area) and the Green Ramp (36 %). It is taken for the Green Ramp, and the evidence says this is ambiguous. **This is an inference** (PLAN §1's city map lists "Green Ramp" and "Transient Parking" separately; nobody has looked at that map).
  - AL-5015 prints "FBO RAMP" three times. Two leaders end in aprons, which are named "FBO Ramp (north-east)" and "FBO Ramp (south)"; the qualifiers are ours.
  - The third "FBO RAMP" is printed inside the West Hangars apron (OSM name=air) and gives no polygon name.
- OSM `name=air` is reported as a data-quality issue and not used.

Elements with `src` obs or inf: 417 elements, with `parking` counted per spot. **347 obs / 70 inf** at element level: the 6 hot spots and 64 parking spots are inf. With the labels, the not-placed items and the 48 unspotted aircraft there are 478 elements.

Many obs elements still carry inferred sub-fields:
- all 34 hangar kinds;
- 2 FBO roles;
- 6 apron label matches;
- all 80 tie-down headings, the headings of the 9 rule-made hangar-apron spots and of the one door spot;
- every spot's size and sizing planform (`size.planform`);
- the beacon position;
- the segmented-circle diameter and position;
- 3 taxiway refs;
- every taxiway default width, and the 8 NAIP widths whose IQR is too large (`width.naip_src` inf with `naip_reason`).

## 2. How it was built and what was measured

**Runways.** These come straight from NASR through `hwd_frame` (`RWY_ENDS` / `RWY_DATA`).

`tools/airport/rwy_edges.py` measured the outline on NAIP. It measures the white runway edge stripes every 15 m. Per AC
150/5340-1M para 2.8, the outer edge of these stripes is on the edge of the usable runway; the stripe width used is the AC
minimum. The NAIP painted edges lie within 0.12 m of the NASR rectangle on every side in both years:

| Runway | NAIP | Edge residual (median per side) | Painted width | NASR width |
|---|---|---|---|---|
| 10L/28R | 2024 | +0.01 / −0.09 m | 22.78 m | 22.86 m |
| 10R/28L | 2024 | +0.04 / −0.12 m | 45.64 m | 45.72 m |
| 10L/28R | 2022 | −0.04 / −0.08 m | 22.75 m | |
| 10R/28L | 2022 | −0.02 / −0.05 m | 45.65 m | |

Against OSM: the runway centrelines lie 0.14–0.17 m from the NASR axis (G1). The OSM 10R/28L way stops 202 m short of
the NASR 28L end, at the displaced threshold. The OSM geometry is reported but not used.

**Taxiway and taxilane paint** (`tools/imagery/paintline.py`, a fork of sfo3d's; rewritten in round 1, section 7 R1-1):
- *Ridges:* the yellow index min(R, G) − B is profiled across each OSM way every 2 m, ±5 m wide. A ridge counts when it is
  ≥ 2.5 DN over the profile median, a second ridge ≥ 1.5 m away is < 0.6 × it, it is not at the window edge, and its
  CIE b* is ≥ 8 (yellow). E's worn centreline reads 2.2-9 DN, below the 4 DN of the review build.
- *Trigger:* the sfo3d strong rule (`window_corr` on ≥ 10 DN ridges) moves something, or a 50 m section has ridges at
  ≥ 60 % of its stations with |median| ≥ 1.0 m and IQR ≤ 0.6 m, or the whole way has ≥ 40 ridges with |median| ≥ 1.5 m
  and IQR ≤ 0.6 m.
- *Move:* a piecewise-linear offset curve (knots every 25 m, second-difference smoothing) is fitted by IRLS (Tukey) to
  every ridge of the way. The whole way moves only if ≥ 70 % of the ridges lie within 0.5 m of the curve, their MAD is
  ≤ 0.25 m, and every stretch of > 40 m without such a ridge either lies between inliers with a change of ≤ 2 % of its
  length, or runs to an end where the curve is held at ≤ 1.0 m. Otherwise the way is **not moved**, and its off-paint
  20 m windows (≥ 5 ridges, |median| > 0.9 m, IQR ≤ 0.9 m; stations at both 0 and 1 m phase) are recorded as
  `naip_paint.faint.off_paint_windows_after` with `paint_offset_unsnapped: true`.
- *Junctions* (round 2, section 8 R2-1; `build_airport.network_fields`). Round 1 moved each way on its own and held only
  the moved way's own end vertices, which broke the network at 22 joins on the moved ways. Now every OSM vertex shared by
  two or more taxiway / taxilane / runway ways is **one node with one displacement**:
  - a node on the interior of a way follows that way's final line (on two or more through ways: the least-squares point
    on their lines; on a runway: it does not move), so a way that ends on a moved way follows it;
  - a node where only way ends meet follows the moved way(s) whose paint holds up to it (≥ 3 ridges within 12 m of the
    end, median within 1.0 m of the fit there), else it stays where OSM has it.

  Each way then takes its own move plus, at each end on a node, the difference to the node's displacement, tapered to 0
  over max(15 m, 5 × the difference). One exception, a **shallow fork**: a moved way that ends on another way at < 30°
  and whose own moved line meets that way's final line within 20 m of the node starts at that meeting point instead
  (tapering it back to the node would cross the other way). The displacements are iterated to a fixed point, and the
  junction vertices are kept when the lines are simplified (round 1 and earlier builds also dropped some of them there).
  Each way records its junctions in `naip_paint.junctions` (node shift, correction, taper, rule).

**4 of 143 ways moved (1,024 m):**
- **Taxiway E, way 490634605:** the curve is −3.27 to −3.51 m over the whole way (73 ridges, 89 % inliers, MAD 0.12 m,
  longest gap 22 m). Its paint holds up to the south end (s = 0), so that node follows E by 3.51 m and the last 17.5 m of
  taxilane 58169733, which ends there, taper to it (58169733's own last ~45 m is still recorded as off the paint,
  unmoved). At the north end (s = 168 m) the paint curves back to the junction (ridges there median +0.45 m against the
  fit's −3.34 m), so that node stays and E tapers to it over 16.7 m; on NAIP 2024 the built line follows the curving
  paint there (looked at on a NAIP 2024 crop with both lines drawn, round 2). Interior nodes: 204801012 joins at s = 165.7 m and
  follows E (0.47 m); 204801549 forks off at s = 53.2 m (below).
- **Taxiway F, way 490634609:** +1.66 m at the start, drifting to +0.2 m by s ≈ 225 m (82 ridges, 93 % inliers, MAD
  0.16 m). It has one interpolated stretch (s 280-380 m, change 0.05 m) and one held end stretch (s 384-445 m at
  +0.2 m). Wide profiles (±12 m) show the centreline continuously along that drift. Its start node follows F (1.65 m;
  58173579 attached); its far end stays (correction 0.2 m over 15 m); the 17 ways that end on F's interior follow F's
  line (0.13-1.53 m).
- Taxilane 204801549 (strong rule + section offset): −2.84 m at s = 0 to about −1.3 m from s 125 m on (113 ridges, MAD
  0.09 m); its free end moves by 1.29 m. It leaves E at 9.0° in OSM; since round 2 it starts at the **shallow fork**
  16.2 m along it, where its moved line meets E's (a vertex of both, 15.8 m from the OSM node). Before, it started at the
  old OSM node, 3.26 m off the moved E line. On NAIP 2024 its faint paint leaves E's within a few metres of that point (looked at on a crop with both lines drawn, round 2).
- Taxilane 1366760486 (strong rule): −0.38 to −0.61 m (50 ridges, MAD 0.06 m); its free end moves by 0.45 m, and its
  other end follows the node on 204801549 (1.30 m; correction 1.79 m over 15 m).

**22 unmoved ways are attached to a moved junction** (`naip_paint.junction_adjusted_len_m`, 13.5-21.7 m each): the ways
that end on E, F, 204801549 or at a node that follows them. Their end moves by 0.13-3.51 m and tapers to the OSM line.
The check (section 4, check 3) verifies that no attachment takes a way farther off its paint than OSM had it.

Ribbons of all four on the round-1 geometry were looked at (`out/phase1/r1/rib_*.png`); in round 2 the junction ends of E, F and 204801549 were looked at on NAIP 2024 crops with the OSM and built lines drawn.

**30 unmoved ways record off-paint windows.** Most are short windows (5-10 ridges) near junctions, where lead-in curves
cross the centreline. 8 of them also meet the check's stricter test (section 4, check 3). **Taxiway D 204801016** north of
A has a line about 1.1-1.8 m east of OSM from s ≈ 70 m on (the review's D finding). Its colour reads b* 5.4-8.0, between
white (< 5) and the worn yellow measured elsewhere (≥ 8.6), so the yellow test does not accept it. D is not moved; its
windows are recorded, and the offset stays open.

**Taxiway refs against AL-5015** (new). Three OSM refs run where AL-5015 draws apron, with no label. We checked this by
eye on the 400 dpi raster with the ways drawn through the diagram affine. These ways keep their OSM ref with
`ref_src: inf` and a `ref_note`:
- E 490634605 lies inside the GA TRANSIENT RAMP area.
- D 204801016 lies north of A.
- F 490634609 runs through the WEST HANGARS / FBO RAMP area.

**On the runway** (new). `on_runway` records the length of each way inside a NASR runway rectangle. 13 unnamed taxiway
ways overlap a runway by more than 50 m (`runway_overlap: true`), for example 58169722 (202 m) and 204801038 (382 m).
The Phase 2 taxi graph should treat those parts as runway.

**Widths** (round 1, section 7 R1-6):
- The NAIP grey-test pavement width is measured on cross profiles every 6 m. It includes shoulders of the same grey and
  misses concrete that reads tan.
- The value is obs only with ≥ 5 stations and an IQR ≤ 1.5 m: 6 ways (Z 58170277 15.0 m, A 490634608 21.2 m, C 204801024
  12.6 m, E 204801027 15.0 m, E 204801035 17.6 m, 204801025 11.3 m).
- With ≥ 5 stations and a larger IQR the value is inf with `naip_reason`: 8 ways, IQR 3.6-21.9 m, for example Z1
  58170922 at 9.0 m with an IQR of 21.9 m.
- Below 5 stations there is no value: 125 ways. Before round 1, 38 of these carried a number from 1-4 stations, contrary
  to the note.
- Every way also carries an AC 150/5300-13B Table 4-2 default width, `default_src: inf`, because the TDG of each way is
  not known: 35 ft (10.7 m, TDG 2) for taxiways and 25 ft (7.6 m, TDG 1) for taxilanes.
- Edges are not measured.

**Holds.** `find_ladder` searches ±12 m along the taxiway for the 7 ft yellow band (Pattern A, 12-in lines, AC
150/5340-1M para 3.3.4.1). It found 16 of 18 bars at a contrast of 21–36 DN. They lie 0.0–0.6 m (median 0.3 m) along
the taxiway from the OSM nodes.

Distances from the runway centreline:
- 10L/28R holds: 126, 129, 129, 130, 130 and 165 ft.
- 10R/28L holds: 199, 200, 201, 201, 202, 204, 216, 223, 237, 299, 300 and 352 ft. The review looked at the 223 ft and 352 ft holds on NAIP: both are real Pattern A bars.
- The 299 / 300 ft holds are the A1 and Z1 holds of 28L. This fits CS hot spot HS 5: "Rwy 28L hold bars on Twy A1 and Twy Z1 are at non-typical lctn".

**Hot spots** (`tools/airport/al5015.py`). AL-5015 is rasterised at 400 dpi:
- the brown hot-spot rings are segmented;
- the label boxes, taken from the PDF text layer, are cut away;
- each ring is closed and filled, and an opening removes the leader line;
- the ellipse with the same second moments is mapped to the world by the diagram affine (residuals 0.4–0.7 m at the four NASR runway ends).

The taxiways inside each ellipse match the CS texts where a text names taxiways: HS 1 has A and E, and HS 5 has A1 and Z1.
The CS texts of HS 2, HS 3 and HS 4 name no taxiway, so they cannot be checked this way. The geometry stays inf: the
legend states ±600 ft.

**Tie-downs** (`tools/airport/tiedowns.py`):
- Painted tees (AC 150/5300-13B E.2.3.2) are matched with a tee template (cross-bar 6.0 m, stem 4.8 m) by normalised cross-correlation every 7.5°, on both NAIP years, inside each OSM apron with buildings cut out.
- A seed needs NCC ≥ 0.45 and both arms confirmed on the image.
- Rows need ≥ 4 seeds with the same stem heading and the same across-row position; one pitch is fitted per apron.
- Every pitch position of a row is then scored in both years. A tee seen gives obs; no tee gives inf.
- **Aircraft on a tie-down:** the aircraft mask is measured inside the outline of a GA single parked on the tee (wing box ±5.5 × ±1.5 m, fuselage ±0.8 m from 2.5 m ahead to 6.5 m behind the bar). ≥ 2.5 m² counts as an aircraft. Since round 1 the outline is also tried shifted by up to ±3 m along the aircraft axis and turned by ±10°, and the largest area counts (TW054N324 had a high wing 2.3 m off the junction and read 0.9 m²). With the tolerance, the 160 position-years split into ≤ 2.1 m² and ≥ 5.6 m². The 18 positions it adds (TW054N324 in 2024; 17 in 2022, all 2-3 m toward the stem) each show an aircraft over the tee by eye (`out/phase1/r1/green_td_2022.png`, `_2024.png`).

Only the Green Ramp (the GA Transient Ramp, inferred) has tee rows: 69 seeds, 7 rows, pitch **12.15 m** (median seed
residual 0.16 m). That gives 80 tie-downs:
- 66 obs: tee seen in 2024 and 2022 (33), 2024 only (17) or 2022 only (16);
- 14 inf. On every one of them NAIP 2022 and / or 2024 shows an aircraft.

`aircraft_seen` holds 48 of the 80 tie-downs: 16 in 2024 only, 16 in 2022 only and 16 in both (39 before round 1).

The other aprons gave 0–21 isolated seeds and no rows. The north-east strip (x 255-290, z −300 to −235) has painted
lead-in lines ending in a tee-like mark at each parking place (seen in the re-check's view and on
`out/phase1/r1/tne_01.png`); they are not detected as tee rows, so its aircraft rest on ADS-B / NAIP spots, and two of them have none
(section 5). The nested double row east of x 445 on the same apron shows tee-like marks at empty back-row places on NAIP
2022 (round 2); no tee row was detected there either.

**Heading** = the stem direction + 180°. On the Green Ramp, parked aircraft sit with the horizontal tail over the stem end
(NAIP 2024, by eye).

**Other spots** (`build_airport.parking`), in build order:

| Step | Source | Rule |
|---|---|---|
| helipad | OSM helipad centres (9) | made first, so that ADS-B evidence on a pad attaches to its spot. Fixed-wing ADS-B on a pad is kept as evidence of that pad, not as a ramp spot: the review's GLEX spot R073. |
| ramp / hangar_apron | adsb.lol parking spots (stays of 5 min or more) | a spot within 5 m of a hangar outline is that hangar's apron spot; since round 1 it is a **door spot** (`door_spot: true`, heading nose in toward the nearest wall point [inf]), like the review's R056 at a T-hangar wall |
| ramp / hangar_apron | clusters of ≥ 3 adsb.lol signal starts / ends (≥ 2 within 10 m of a hangar) | single linkage 4 m; within 5 m of the wall also a door spot |
| ramp | NAIP 2024 aircraft blobs, extent 8–24 m | each blob takes the **by-eye verdict** of `refs/cache/naip/naip_blob_review.json` (below) |
| hangar_apron (inf) | box hangars with no observed spot | see below |

The **NAIP blob review**. I looked at every NAIP blob that had become a ramp spot (40) at 0.12 m and 0.08 m. Verdicts:
- 24 aircraft;
- 8 vehicles: cars, box trucks, vans and a bus in landside lots that the OSM apron polygon 289829587 takes in;
- 3 with no object at the spot (paint);
- 1 the same aircraft as a neighbouring blob;
- 4 centred between two aircraft parked wing to wing.

The build drops the vehicles, the empty ones and the duplicate. It splits the two-aircraft blobs of 16 m or more into two
spots (2) and drops the others (2). I tested the blob shape (extent, minor extent, fill) as an automatic filter, and it
does not separate the classes. Wing-only aircraft blobs (minor 1.8–2.1 m, fill 0.70–0.81) look like trucks. Blobs not
in the review are marked "not reviewed by eye".

**Inferred hangar aprons** (rule spots, 9). One spot per box hangar without an observed spot. It is 8 m out from the *real*
wall, on the normal through the middle of the longest side, and it needs all of these:
- the 2–14 m strip in front of that wall is OSM **apron** (taxiway buffers no longer count) and free of buildings;
- the outline of an ADG I aircraft parked nose-in keeps the AC 150/5300-13B Table 4-1 object distances: 13.6 m from open taxiway centrelines and 12.0 m from open taxilane centrelines;
- no NAIP 2024 objects lie in that outline, and the point is not on a white roof (median grey > 235);
- the hangar is not on the recorded by-eye rejection list: an unmapped annex roof at APP Jet Center, and a walled yard at hangar 204800998;
- (round 1) the point is reachable from an open OSM taxiway / taxilane centreline over OSM pavement (aprons and taxi-line buffers) around buildings within 75 m (`CONNECT_M`, chosen: the plausible rule spots lie 20-69 m away; HE221N301 in the landside truck yard was 119 m away and is now dropped by this rule);
- (round 1) every rule spot that passes carries a recorded by-eye verdict (`HGR_REVIEW`, NAIP 2024 and 2022 at 0.1 m with the planform, `out/phase1/r1/hgr_rule_sheet_*.png`): all 9 are "ok".

The review's H006, which sat 5.0 m from the taxiway F centreline with its tail across F, is gone; so is H001. H010 now
sits on the real wall of its L-shaped hangar.

**Duplicates.** Ramp and hangar-apron spots closer than 9.5 m are one parking position. That is below the span of the
smallest common type, C150 / C152 (10.17 m, FAA ACD), minus position noise. Such spots are merged into the one with the
strongest evidence before sizing; H017 / H018 became one spot.

**src of a spot.** For ramp and hangar-apron spots, `src` is about the *role* "parking position". It is obs only
with **≥ 2 independent observations**: NAIP years with an aircraft plus adsb.lol **sessions** (round 1). A session is one
aircraft's continuous presence at one place: its consecutive stays and signal starts / ends linked when ≤ 15 m apart and
the aircraft has no fix farther than 30 m away, and none off the ground, in between, **however long the gap** (round 2;
`tools/adsb/parked_stays.py sessions()`). So a stay and its own signal start and end are one session, and so is a parked
aircraft's power cycle: its signal end and its next signal start at the same place with no fix elsewhere in between, even
two days later. The same aircraft after taxiing away or flying is another session. Round 1 linked events only when ≤ 20
min apart, which split such presences (section 8 R2-2). The rule errs towards fewer sessions: an aircraft that left and
came back while the recorder had an outage (17 outages > 600 s, PLAN §3) counts once. One sighting gives inf. `strength` lists
`adsb_sessions` and, for information, stays and signal events. The other kinds keep their rules:
- a tie-down is obs when its tee is seen;
- a helipad is obs when it is mapped in OSM;
- a rule spot is inf.

**Sizes** (`size`, always inf). They are solved in tiers: painted tie-down rows first, then obs spots, then inf spots, so
that a weak spot cannot shrink a strong one. Buildings (each spot's own hangar included since round 1) and helipad discs
(rotor size, or the smallest OSM pad, 10.1 m, when unknown) are fixed obstacles. Only a door spot may enter its own
hangar, and only with its nose; its wing keeps 1.0 m from that hangar at both sizes. Within a tier, each pair of spots
within 40 m shares the space equally. The sizing **planform** (round 1, `size.planform`) is the wing (a segment of the
span across the heading) plus the fuselage (span × length / span of the widest observed type with both values in the FAA
ACD, else the C172's 0.754; 24 % ahead of the reference point). Without a heading (71 spots) it is a disc that holds
that planform in every heading (round 2): radius = span × max(1/2, 0.765 × length / span), the wingtip or the tail,
whichever lies farther from the reference point (`size.planform.disc_radius_per_span`; 0.577 × span for the C172 default).
- **`max_span_m`**: the AC design value, which keeps the wing shapes 10 ft (3.05 m) apart. Sources: AC 150/5300-13B Chg 1 Table 5-1 ("I and II: 10 ft (3 m)") and Figure E-2 ("Wingspan plus 10 ft (3 m) for critical aircraft"). The upper bound is ADG I, 49 ft (14.94 m, Table 4-1), or the ADG of a wider type seen there. The wing shape is a segment across the heading, or a disc when the heading is unknown.
- **`capacity_span_m`** (new): the same with a 1.0 m gap, the practical size for placing aircraft. HWD's own use: C172s on the 12.15 m pitch leave 1.15 m.
- **`observed_max_span_m`** (obs): the widest adsb.lol type seen at the spot (FAA ACD wingspan), now counted from *every* stay, signal start / end and merged duplicate in the evidence. `observed_type_spans_m` lists them.
- **`flags`**:
  - `observed_type_wider_than_design`: 39 spots (32 before round 2);
  - `observed_type_wider_than_capacity`: 29 (18);
  - `capacity_below_smallest_common_type`: 27 (10). The rise comes from the round-2 heading-less disc: two such spots
    12.04 m apart (RE127N262 / RE131N273, C172 default) now get a capacity span of 9.58 m each, below a C150. Aircraft
    parked parallel fit there in reality; the disc must hold the aircraft in any heading because the heading is not known;
  - `no_design_size`: 1, RE154S340, an inf BE20 stay 14.4 m from the obs jet stand RE155S326.

Green Ramp rows: design 9.1 m (pitch − 10 ft) and capacity 11.15 m (pitch − 1.0 m). Overall: 155 spots ADG I, 4 ADG II,
1 ADG III, 1 none; 130 of 161 design sizes are limited by a neighbour, a building or a helipad. Helipad spots carry `max_rotor_m`:
the OSM pad size, or null.

**ref_point** (new) says what point each position stands for:
- the tee junction (wing line), 80 spots;
- the GNSS antenna median, 52;
- the NAIP blob centroid, 24, or the centroid of one half of a split blob, 3;
- the helipad centroid, 9;
- the rule point, 9.

**ids** (new) come from the rounded position, so a rebuild keeps them: `RE187N279` is a ramp spot 187 m east and 279 m
north of the ARP. The prefixes are T (tie-down), R (ramp), H (hangar apron) and P (helipad). Zone labels follow D3 and
are never official numbers.

## 3. Parking spots

| Kind | Total | obs | inf | Where |
|---|---|---|---|---|
| tiedown | 80 | 66 | 14 | Green Ramp, rows 1–7 |
| ramp | 67 | 31 | 36 | FBO Ramp (north-east) 44, FBO Ramp (south) 10, Green Ramp 6, West Hangars 6, near hangar 204797798 1 |
| hangar_apron | 14 | 3 | 11 | 14 hangars. The 3 obs are adsb.lol signal-edge spots at Hangar B, Hangar G and hangar 971132675 (2, 2 and 11 sessions). Of the 11 inf, 9 are rule spots at box hangars, 1 is the Hangar C door spot HE623S150 (one session) and 1 is HE154S380 at Signature Aviation (one session since round 2). Four of these hangars are T-hangar rows: B, C, G and 971132675 |
| helipad | 16 | 13 | 3 | Helicopter Ramp 6, FBO Ramp (north-east) 5, FBO Ramp (south) 2, unmapped helicopter area south of 10R/28L 2, West Hangars 1 |

What the ramp spots rest on (counted in sessions, round-2 rule):
- 26 rest on one NAIP 2024 aircraft only (inf), and 1 on aircraft in both NAIP years (obs);
- 40 rest on adsb.lol sessions: 10 on one session (inf) and 30 on two or more (obs).

History: round 1 replaced stays and signal events by sessions (ramp split unchanged at 33 / 34; HE623S150 became inf;
HE625S176 and HE154S380 became obs). Round 2 joined a parked aircraft's power cycles into one session: RE181S395,
RW166N607 and HE154S380 each rested on one aircraft's single presence and are now inf; HE625S176 stays obs (that
aircraft flew away between its two sessions). 25 other spots (3 helipads and 1 tie-down among them) lost sessions but stay obs.

Headings are known for all 80 tie-downs (inf, from the tee), for the 9 rule-made hangar aprons and for the door spot
HE623S150 (nose toward the hangar, inf). No ramp spot has one: no adsb.lol spot had ≥ 3 consistent taxi-in headings (G4: the taxi-in heading matches the
reported heading only 29 % of the time).

## 4. Check results (`tools/check_airport.py`, run 2026-11-13 on the current build)

All hard checks passed on the current build. Several of them are *consistency* checks: the build derives the data from
the same rule or source that the check uses. The report says so. Since round 1 the check takes `--data FILE`; run on the
build that the re-check examined, it fails on every round-1 finding it covers (section 7). Run on the round-1 build
(the one the round-2 re-check examined), it fails on each of the four round-2 findings (section 8).

1. **Runways vs NASR**, recomputed from the NASR rows rather than from `hwd_frame`'s constants:
   - 69 fields compared, 0 mismatches;
   - worst position difference 3.8 mm (the data is rounded to 0.01 m);
   - plane lengths +0.06 m and −0.07 m against the NASR ft values;
   - traffic sides and TPA agree with the CS.
2. **Pavement vs NAIP:**
   - the outline equals the NASR rectangle to 5.3 mm;
   - the edge residuals are in the table in section 2, all within the 0.6 m tolerance (the largest is 0.12 m).
3. **Taxiway designations, read from the AL-5015 PDF itself:**
   - 23 taxiway label glyphs of the text layer lie 0.1–11.6 m from an OSM way with the same ref; the tolerance is 15 m;
   - the label set {A, A1, B, C, D, E, F, Z, Z1} equals the OSM refs;
   - every other single-letter glyph (closed-surface X marks, runway-side letters, symbol letters, the WEST HANGARS letters) lies ≥ 14 m from every taxiway centreline;
   - the three `ref_src: inf` ways are listed;
   - the A1 / Z1 wingspan limits are present.

   **NAIP paint per way** (rewritten in round 1, extended in round 2, hard). The ridges are measured again on every open
   way's final geometry, at stations 1 m shifted from the build's. A 20 m window (step 10 m) with ≥ 6 ridges, |median|
   > 1.0 m and IQR ≤ 0.8 m is off the paint.
   - Moved ways off the paint anywhere, junction tapers included (round 2: round 1 exempted the tapers): 0.
   - Ways changed only by a junction attachment (22): an off-paint window that the OSM line does not have at least as far
     off: 0.
   - Zig-zag (round 2), on every changed way with no exemption: the displacement from the OSM line must not be a local
     extremum more than 0.5 m deeper than both points 10 m away. Largest 0.03 m (58169733).
   - Lateral kinks of the moves (second difference over ±10 m of the displacement, outside the recorded junction
     tapers): 0 above 0.5 m. The largest is 0.15 m (taxilane 204801549); E 0.03 m, F 0.04 m.
   - Unchanged / attached ways with an off-paint window: 8, all recorded as `paint_offset_unsnapped`.
   - Run on older builds (`--data`), these tests fail:
     - the build the round-1 re-check examined (commit 7afa0ac): off the paint E in the windows from s 0, 10 and 70 m (−2.9 to
       −3.3 m) and 204801549 in those from s 30 and 40 m; zig-zag E 0.95 m at s 84 m; kinks E 1.96 m, F 0.82 m, 204801549 0.58 m; unrecorded
       offsets;
     - the round-1 build: off the paint E at s 150 m (+1.02 m, inside its old junction taper); kinks E 2.08 m, F 0.98 m,
       204801549 1.37 m (measured over the whole way now that the taper exemption follows the recorded tapers).

   **Taxi network topology** (round 2, hard; `check_airport.topology_check`, own code):
   - every OSM vertex shared by two or more taxiway / taxilane ways must be one vertex in the data, identical (to
     0.015 m) on every member way and within 8 m of the OSM node; a shallow fork passes when the ending way's built end
     is a vertex of the other way within 20 m of the node and the OSM angle is < 30°;
   - built ways may touch or cross only at a shared vertex, unless their OSM ways already cross without a node.
   - Current build: 167 junction vertices, 166 shared (largest shift 3.51 m, 22 moved by > 0.05 m), 1 shallow fork
     (204801549 on E, 15.8 m from the node, 9.0°), 0 crossings away from a vertex (OSM's own crossing 204797826 /
     204801043 is kept).
   - The round-1 build fails: 78 junctions without a shared vertex (11 of them with a gap > 0.05 m) and 43 crossings
     away from a vertex. The 7afa0ac build fails too: 73 and 42. Most of these are junction vertices that the line simplification
     dropped on ways that did not move (a pre-existing defect, now fixed by keeping junction vertices); the moved-way
     joins of finding R2-1 are among them.

   **Widths** (round 1, hard): obs only with ≥ 5 stations and IQR ≤ 1.5 m (6 ways); inf with a reason (8); no value
   below 5 stations (125); 0 violations. The reviewed build had 46 violations.
4. **Spot centres on pavement:** 175 inside OSM aprons. 2 helicopter spots pass only the NAIP grey test: they sit on the unmapped paved helicopter area.
5. **Spot centres in buildings:** 0.
6. **Spacing.** The 8 AC 150/5300-13B quotes were found in the committed extract.
   - **Planforms** (round 1): wing plus fuselage. The check recounts each spot's length / span from the observed types in
     its evidence (FAA ACD via `data/ga_types.json`, else the C172's) and compares it with the spot's `size.planform`
     (hard; agrees on every spot).
   - **Heading-less discs** (round 2, hard): for each of the 71 spots without a heading, the recorded disc must contain
     the wing + fuselage planform at every heading (5° steps) at both sizes: yes. The round-1 build fails (its discs of
     diameter span × max(1, length / span) leave the tail out, for example RE127N262 / RE131N273).
   - Pairs within 45 m, helipad spots as discs (consistency check):
     - design size: 1,083 pairs, minimum 3.046 m (10 ft minus the floor rounding of the sizes), 0 violations. RE154S340
       has no design size (flag `no_design_size`): not even a point keeps 10 ft from the higher-tier jet stand
       RE155S326. It is listed and left out of this pair test only; the capacity test keeps it.
     - capacity size: 1,088 pairs, minimum 0.995 m, 0 violations.
   - **Planform vs every building, the spot's own hangar included** (round 1; consistency, hard): 0 violations at both
     sizes. The only exception is a door spot, whose nose may enter its own hangar while its wing keeps 1.0 m. There is
     one door spot, HE623S150; the check verifies from the geometry that it lies ≤ 5 m from its hangar wall and heads to
     the nearest wall point.
   - Run on the reviewed build, these tests fail: RE459N093 / HE461N103 1.77 m apart at design size; 12 capacity
     violations; HE623S150, HE625S176 and HW272N632 overlapping their own hangars and HE154S380 / HE248N195 within 1.0 m
     of theirs.
   - **Duplicates** (independent): 0 ramp / hangar-apron pairs closer than 9.5 m.
   - **Observed types** recounted from all the evidence: 39 spots saw a type wider than the design size and 29 one wider than the capacity size, for example FBO-ramp spots where E55P, PC12 or C680 parked. The spots' own flags agree with the recount.
   - **Independent observations** (round 1, hard):
     - `n_observations` equals NAIP years plus `adsb_sessions`, and `src` follows the ≥ 2 rule on every ramp /
       hangar-apron spot;
     - an independent recount (distinct sessions of the committed stays and signal edges within 8 m of each obs spot or
       its merged duplicates, half the span + 2 m for types wider than 15 m, plus NAIP years) finds 0 obs spots below 2.
       On the reviewed build it finds HE623S150 (one session). This recount reuses the session numbers, so it cannot see
       a wrong session rule;
     - (round 2) a **presence recount from the local per-aircraft files**, without the session numbers: one aircraft's
       events at an obs spot are one presence unless it has a fix > 30 m away in between or the events are > 15 m apart,
       however long the gap. 34 obs spots, 106 same-aircraft event pairs joined, 0 obs spots below 2. On the round-1
       build it finds RE181S395, RW166N607 and HE154S380. It needs the gitignored `refs/cache/local/adsb/` files and
       says SKIPPED without them (a fresh clone cannot run it); it prints no identity.
   - **Spot vs taxiways.** The capacity planform is compared with the AC Table 4-1 ADG I object distances (13.6 m from a
     taxiway centreline, 12.0 m from a taxilane centreline). Inside that distance: all 80 Green Ramp tie-downs (the real
     layout, tails toward the taxilanes), 34 ramp spots and 3 hangar-apron spots (2 obs, 1 inf). The 9 rule-made spots
     all keep it with their ADG I planform (hard).
   - **Rule spots** (round 1, hard):
     - each is reachable over OSM pavement around buildings from an open taxiway / taxilane within the build's 75 m. The
       check uses its own 8-neighbour Dijkstra, +6 % for the two grid metrics; it gives 22-74 m;
     - each has an "ok" by-eye entry in `HGR_REVIEW`.
     - On the reviewed build these fail: HE221N301 is not reachable within 100 m, and no rule spot was reviewed.
   - **Unspotted aircraft:** 48 listed; 0 now have a spot within 5 m (hard, so that the list cannot go stale silently).
   - **Omission sweep** (round 2, hard; `check_airport.omission_sweep`, own code): the NAIP 2024 aircraft mask (as
     `tiedowns.py`: ≥ 30 DN over the 4 m median, closed by a 0.75 m disc) on every OSM apron with buildings (+1 m) cut
     out; mask parts joined within 1 m; the pixels of a part farther than 7.5 m (`SWEEP_R`) from every spot, listed
     unspotted aircraft and reviewed NAIP blob form a candidate when they cover ≥ 6 m². Every candidate needs a by-eye
     verdict in `build_airport.SWEEP_REVIEW` within 3 m. Current build: 49 candidates, all with a verdict (28 vehicle,
     13 paint, 1 structure, 5 the far part of the aircraft at a spot, 2 part of a listed aircraft). The round-1 build
     fails: one candidate without a verdict at (486.3, −0.9), 53.8 m², the merged back row of the nested double row.
     Limits: the mask needs a bright object, so dark aircraft and aircraft in shadow are not found, and only OSM aprons
     are swept.
7. **Hot spots:** HS 1 and HS 5 agree with the taxiways their CS texts name. HS 2–4 are *not checkable against the CS*, because their texts name no taxiway (earlier versions called them "consistent").
8. **Holds:** 16 of 18 have a NAIP bar; the offset from the OSM node is at most 0.60 m (median 0.30 m).
9. **Hygiene:**
   - all 478 elements have a valid `src` and `refs`;
   - the `.js` twin parses to the same object.
   - **D1:** all 17 committed ADS-B-derived files were scanned against the hex, registration and callsign of the 1,098
     aircraft that the recording saw within 5 km. The scan also looks for identity keys, per-row time keys, epoch
     numbers and N-number-like tokens. 0 findings.
   - **Session numbers** (round 1, revised in round 2): the 522 sessions in `hwd_parked_stays.json` (630 under the round-1
     rule) each lie within 30 m, and in each the signal starts and ends differ by at most 1: 14 sessions hold a power
     cycle (end, start, ...) at one place. A number still never links an aircraft's visits to different places or
     across a departure.
   - **SOURCES** (round 1 extended, hard):
     - all 58 committed data files have an entry;
     - all entries in the 6 SOURCES.json files have `made_by` or `note`;
     - all 14 text / JSON files whose SOURCES licence names the ODbL carry the ODbL URI in the file itself.
   - **src values** (round 1): every `src` / `*_src` value in every committed JSON is obs, inf or null, field-documentation
     maps aside. The one listed exception is `data/ga_types.json` `src: 'none'` (23 types without an FAA ACD row; its
     `src_legend` says so).

**Reproducibility.**
- Every input of the build is committed. The build reads the committed NAIP JPEGs, never the local GeoTIFF.
- Round 1 re-ran these, and each came out byte-identical on a second run:
  - `tools/adsb/parked_stays.py` (now with sessions; round 2 changed the session rule, and a re-run on 2026-11-13 gave a
    byte-identical `hwd_parked_stays.json`);
  - `tools/phase0/hwd_mix.py` and `hwd_cov.py`. Before the notice line was added they reproduced the committed
    summaries exactly; after it, the summaries differ from the committed ones only by that first line.
- OSM:
  - `fetch_osm.py` re-merged the extract from its cache (new: the `licence` key), and `parse_osm.py` and
    `xcheck_osm_faa.py` were re-run. Only the extract's sha256 changed downstream.
  - `fetch_osm.py --via api` needed one live OSM API request.
- Two dependencies stay local. The NDVI fields of `hwd_parked_stays.json` need the local NAIP GeoTIFF, but the build does not use them. `tools/plot_overlays.py` uses the GeoTIFF when present; its numbers are committed as `docs/phase1/crosscheck_metrics.json`.
- A fresh clone cannot re-merge the OSM extract without the network, because `.parts/` is gitignored. The merged extract itself is committed.
- Build: `hwd_airport.json` sha256 df5a8828…, `.js` 7781349a… (round 2, 2026-11-13); about 3 min. A second build from scratch, with every `__pycache__` deleted first, gave byte-identical files.
- Environment: `build_env` in the file records Python 3.13.18, numpy 2.5.3, scipy 1.18.1, shapely 2.2.0, Pillow 12.3.0 and poppler 24.02.

## 5. Gaps and things not verified

- **FAA aircraft registry: not obtained (open).** PLAN §7 Phase 1 asks for it. registry.faa.gov answered HTTP 403 to the one automated attempt (`refs/cache/local/registry/fetch_log.json`). `tools/registry/build_lookup.py` and `registry_mix.py` have not run on real data; `registry_mix.py --onfield-only` gives the same 243 on-field aircraft as Phase 0. Next step for the owner:
  1. Download `https://registry.faa.gov/database/ReleasableAircraft.zip` by hand.
  2. Run `tools/registry/fetch_registry.py --record-manual`.
  3. Run `build_lookup.py` and then `registry_mix.py`.

  Nothing per aircraft is committed (D1).
- **Signs, lighting fixtures and marking geometry are not sourced** (`not_yet_sourced`). Signs: only the two NASR distance-remaining remarks; no position, text or direction. Lighting: types, codes and the tower-closed schedule only; no VASI / PAPI box or REIL unit positions, and no taxiway edge lights or reflectors. Markings: only hold bars, the displaced-threshold bars and the runway edge stripes are measured. Also missing: the five unlit wind cones and the painted H circle (cross-check #7, #8). Candidate sources: NAIP, FAA siting standards applied as rules (inf), owner photos.
- **Taxiways.**
  - Most centrelines are still OSM as mapped; only 4 ways moved.
  - 30 unmoved ways carry recorded off-paint windows (`paint_offset_unsnapped`). Most are short windows near junctions;
    whether they are centreline offsets or lead-in curves was not looked at way by way.
  - Taxilane 58169733, which ends at E's south end: its end now follows E's moved node (17.5 m taper), but the 40 m
    before that still read −1.9 to −3.2 m off its paint (recorded windows); it is not moved as a whole.
  - 22 unmoved ways are attached to moved junctions; the check verifies that this takes none of them farther off the
    paint than OSM was, not that they are on it.
  - D 204801016: a line about 1.1-1.8 m east of OSM north of A has an ambiguous colour (b* 5.4-8.0). Not moved; open.
  - Widths: obs on 6 ways only; inf on 8; the rest carry only the AC default (inf); edges are not measured.
- **NAIP-only ramp spots** (27): every blob is reviewed by eye, but 26 of them rest on one image and are inf.
  - The OSM apron 289829587 still takes in the landside lots. It is not clipped to airside; the review and the occupancy and roof tests handle the spots there.
- **Parked aircraft without a spot: 48 (known gap; `unspotted_aircraft` in the data).** The parking spots are not
  complete, and this list is not proven complete either. A by-eye pass over every apron on NAIP 2024 (flown 2024-05-20)
  with the spots drawn found 42 parked aircraft that no spot stands for (round 1; 0.25 m tiles and 0.06-0.15 m crops in
  `out/phase1/r1/`, plus every NAIP aircraft-mask blob more than 6 m from a spot). The round-2 re-check found the back
  row of the nested double row on the FBO Ramp (north-east) missing; 6 aircraft were added after looking at 0.05-0.07 m
  crops of NAIP 2024 (NAIP 2022 shows the same layout with 3 of them occupied). They lie 7.8-10.6 m from the front-row spots, so distance from a spot alone does not show a
  missing aircraft in a nested row. Since round 2 the check's **omission sweep** (section 4, check 6) shows every
  bright aircraft-mask part on an OSM apron more than 7.5 m from every spot and listed aircraft for a by-eye verdict; all
  49 such parts now have one, and none is an unlisted aircraft. Dark aircraft, aircraft in shadow and aircraft off the
  OSM aprons are outside the sweep. Each listed position has an aircraft-bright patch within 2.5 m and lies 5.6-57 m
  from the nearest spot. Positions are ±2 m (world x east / z south, m). Some may be taxiing: one image.

  | Where | Positions (x, z) | Note |
  |---|---|---|
  | Green Ramp | (−4.9, −275.8) | SE end of a tie-down row, no tee under it |
  | Green Ramp | (−22.0, −308.6), (−10.8, −302.6), (−0.6, −296.6) | between two tee rows (no nested row searched) |
  | West Hangars apron | (−200.0, −595.2), (−210.8, −589.2), (−222.2, −583.8), (−213.2, −580.2) | cluster of 5 wing to wing; RW203N587 is the 5th |
  | West Hangars apron | (−195.8, −563.4), (−206.0, −556.2) | pair north of RW208N551 (which is on the next aircraft) |
  | West Hangars apron | (−155.0, −577.8), (−144.2, −584.4) | pair wing to wing |
  | West Hangars apron | (−140.6, −552.6), (−150.8, −546.0), (−161.0, −540.0) | row of 4; RW130N558 is the first |
  | West Hangars apron | (−376.6, −463.0), (−367.0, −462.4), (−370.9, −452.8), (−360.7, −452.2) | 4 in a painted rectangle; RW374N473 lies 9-10 m north |
  | West Hangars apron | (−158.6, −507.6), (−114.8, −532.8), (−173.6, −496.8) | beside / on taxi lines: parked or taxiing (the last a larger twin or jet) |
  | FBO Ramp (north-east) | (162.5, −361.3), (156.3, −267.5), (150.5, −255.0) | north end; east of the RE127N262 / RE131N273 / RE139N285 row |
  | FBO Ramp (north-east) | (266.3, −282.5), (281.3, −253.8) | north-east strip, on painted lead-in / tie-down marks |
  | FBO Ramp (north-east) | (325.2, −244.8), (382.2, −266.4) | open apron |
  | FBO Ramp (north-east) | (397.8, −274.2), (406.2, −264.6), (413.4, −255.0), (419.4, −244.8), (424.8, −231.6), (430.2, −222.0), (433.8, −211.2) | row of 7 along the road, wing to wing |
  | FBO Ramp (north-east) | (343.2, −212.4), (411.0, −204.0), (400.8, −202.2), (491.3, −27.5) | beside RE331N209; beside RE405N217; on a taxi line; south of the FBO building |
  | FBO Ramp (north-east) | (455.7, 14.9), (465.7, 8.5), (476.9, 4.2), (486.5, −2.1), (497.1, −6.7), (507.8, −11.3) | back (south-east) row of the nested double row east of x 445, behind the front-row spots RE447S012 … RE498N016 (round 2) |
  | FBO Ramp (south) | (126.3, 285.0), (255.1, 357.6) | west edge between two spots; business jet on the east edge, partly outside the OSM apron |

  Why they were missed: aircraft parked wing to wing merge into blobs above the 24 m extent limit; the West Hangars and
  NE-strip markings are not detected as tee rows; and blobs within 4 m of a taxi line count as taxiing. They are listed,
  not made into spots. Whether to add them as inf spots is open. Aircraft that sit about 6 m from a spot were counted as
  standing at it by eye (inferred): (304, −70) at RE308N064 and (272, −268) at RE277N271 are sweep verdicts; (365, −35),
  6.4 m from RE361N040, has no part beyond 7.5 m that the sweep shows.
- **Size classes.** `max_span_m` follows the AC design rule and is tighter than the real use (Green Ramp 9.1 m against a C172 of 11.0 m). Use `capacity_span_m` for placement and `flags` for the spots where even that is smaller than the type seen there.
- **T-hangar bays and doors.** NAIP shows no door rhythm (G2). Four of the 18 T-hangar rows have a spot, all from adsb.lol: obs at Hangar B, Hangar G and hangar 971132675; inf at Hangar C (the door spot HE623S150, one session). The other 14 have none.
- **Door spot heading.** HE623S150's axis is taken perpendicular to the wall, nose in [inf]; whether aircraft enter that T-hangar nose or tail first is not known.
- **Rule-made hangar aprons** (9) sit on the side that faces mapped apron, not on a known door. `CONNECT_M` (75 m) was chosen from the distances of the plausible spots; it is a filter for unobserved spots only.
- **OSM apron 289829587** still takes in landside lots (truck yard, car parks). It is not clipped to airside: OSM maps only five fence fragments, too few to define airside. Rule spots are kept out by `CONNECT_M` and the by-eye review; NAIP blobs there were reviewed as vehicles.
- **AL-5015-derived items are inferred** (±600 ft):
  - the hot-spot ellipses;
  - the label matches. GA TRANSIENT RAMP → Green Ramp is an inference;
  - the terminal building, placed by its leader end;
  - the three apron-route refs (E, D, F).
- **Not placed:** the UL94 fuel island (no location in any source), and the unmapped helicopter area south of 10R/28L (4 pads on NAIP 2024).
- **Hangar classification** (T-hangar row / box) is a shape rule and has not been checked against photos. The FBO names are not verified as current.
- **Building outlines.** Some are 3–6 m off the roof edges in both NAIP years (cross-check #15). They are flagged, not corrected.
- **Helicopters:** the NASR remark puts the transient helipads "west of green ramp located at base of twr". This reading is inferred. G4 found that helicopters mostly use the south FBO apron and the unmapped area.
- **Inherited from earlier tasks:**
  - NAD83(2011) and NAVD 88 as the realisations / datum (frame);
  - the NAIP E/N treated as NAD83(2011);
  - the decoding of the NASR VGSI code letters, which is from memory;
  - ADS-B positions are GNSS antenna positions;
  - one west-flow November week of ADS-B only.
- **Not re-read:** the NAIP / USDA licence wording (taken from sfo3d) and the adsb.fi quote. Planetary Computer's terms were not reviewed. The adsb.lol quotes were read via the `www.` host after a 403 on the bare host; the owner decides (`docs/ATTRIBUTION.md`).

## 6. Phase 1 review (2026-11-12): findings and outcomes

Ids in the findings are those of the reviewed build. The current ids are in brackets.

| # | Finding (severity) | Outcome | What was done / why |
|---|---|---|---|
| 1 | OSM contributor names / uids in the committed extract (minor) | **fixed** | `fetch_osm.py` strips `user` and `uid` from the committed extract (2,878 elements, 0 left). The meta records `sha256_unstripped` 975f7ab7…, equal to the first fetch, and an unstripped copy stays in gitignored `.parts/` for the `--via api` cross-check. The sfo3d precedent goes to `requests_to_sfo3d.md` R5. |
| 2 | adsb.lol docs read via `www.` after a 403 (minor) | **deferred: owner** | Both quotes are marked "read via www. host after a 403 on the bare host; owner to confirm" in ATTRIBUTION, and listed as an open owner decision. |
| 3 | ATTRIBUTION overstated the D1 check (minor) | **fixed** | check_airport check 9 scans all 17 ADS-B-derived files against hex, registration and callsign from the recording, plus keys, per-row times, epochs and N-numbers. A positive control matched 200 of 200 local hexes. ATTRIBUTION describes the real check. |
| 4 | ODbL URI / notice missing in derived files (minor) | **partly fixed; completed in round 1** | URI and attribution are now in `ga_types.json._meta`, `khwd_features.json`, `khwd_osm_xcheck.json`, `refs/cache/adsb/*.json`, the OSM meta, `osm/SOURCES.json` and `docs/phase1/crosscheck_metrics.json`. The two plain-text Phase 0 summaries rely on `adsb/SOURCES.json` (ODbL 4.2(d)), which now says so. *Round 1 (R1-7): the OSM extract itself, the OSM API meta and the two Phase 0 summaries still lacked the URI; they now carry it, and check 9 enforces it.* |
| 5 | `naip/MANIFEST.json` without a SOURCES entry (minor) | **fixed** | Entry added. check_airport now checks SOURCES coverage: 58 files, 0 missing. |
| 6 | `src` reused for the ADS-B transport class; null src in ga_types (minor) | **fixed; claim corrected in round 1** | The field is now `feed` in stays, signal edges, holds and spot `feeds`, so 0 non-obs/inf `src` remain in any committed JSON. ga_types: `src: 'none'` plus a `src_legend`. *Round 1 (R1-7): "0 non-obs/inf `src` remain in any committed JSON" was not literally true (ga_types `src: 'none'`, apron `name_src: 'osm'`, `observed_src` text). The apron and observed fields now hold obs / inf; ga_types `none` stays, documented and listed by check 9.* |
| 7 | Segmented-circle diameter read by eye but obs (minor) | **fixed** | `diameter_src: inf` and `position_src: inf` with evidence. |
| 8 | Per-event ADS-B rows, rare LADD types (minor) | **partly fixed; rest deferred: owner (Q1)** | Exact `dur_s` removed from the committed stays (bucket only); run-up durations rounded to 10 s. Rare types are not coarsened, because that changes observed sizes; the options are listed for the owner. |
| 9 | Constants without a stated basis (minor) | **fixed** | A basis line was added to: `WEST_HANGARS_BOX`, `PITCH_RANGE` and the tee thresholds, `HGR_D`, `TERMINAL_TIP_PX` (window by eye), `AC_EXT_MIN` (its wrong "vans are shorter" rationale is corrected), every constant of `runup_holds.py` and `parked_stays.py`, the `events.py` thresholds, and `rwy_edges.py`. Most read "chosen; sensitivity not tested". |
| 10 | `__pycache__` written in sfo3d (minor) | **fixed** | `sfo3d/tools/models/__pycache__/` deleted (ignored; no tracked file was touched); `git status --ignored sfo3d pc12` is now empty. No hwd3d tool imports sfo3d code, and the fix runs wrote nothing under sfo3d. Note: `python3 -I` ignores `PYTHONDONTWRITEBYTECODE`, so hwd3d's own runs leave ignored `__pycache__` folders under `hwd3d/tools/`; I deleted them at the end. Use `python3 -I -B` to avoid them. |
| 11 | Cited pages and terms not committed or not re-read (minor) | **partly fixed** | (1) AC 5340-1M PDF p. 54 (para 2.9.1.3 / 2.9.1.5) added: the extract is now `ac150_5340_1m_chg1_p52-54_63.pdf`. (2) STAC items labelled "Planetary Computer service terms not reviewed". (3) NAIP / USDA quotes and (4) the adsb.fi quote are **deferred**: to be re-read before Phase 2 publishes credits. |
| 12 | Taxiway E 3.3 m from its paint (major) | **not fixed by this step; fixed in round 1** | Faint-paint rule (section 2): E moved by up to 3.36 m and F by up to 1.68 m. New hard per-section check: 0 offset sections. D 204801016 is not confirmed by our test (too few ridges). *Round 1 (R1-1): this fix produced a zig-zag (E back at its old position over s 0-22 / 78-92 m), which the 50 m section check passed. Replaced by the whole-way fit (section 2).* |
| 13 | NAIP ramp spots on vehicles / paint (major) | **fixed** | By-eye review of all 40 blob spots, recorded in `naip_blob_review.json`. 8 vehicles (R007, R009–R012, R016, R022, R042), 3 empty (R014, R017, R033) and 1 duplicate (R039) dropped. R041 and R080 split, R077 and R079 dropped. The other 24 are kept as aircraft; 26 of the 27 NAIP-only spots are now inf. |
| 14 | Overlaps and duplicates invisible to the check (major) | **fixed; extended in round 1** | Helipads are sized and checked. Duplicates are merged before sizing (H017 / H018 → HE248N195); R039 dropped; R038 [RE405N217] is 14.93 m instead of 5.88 m. R073 (GLEX on a helipad) is now evidence on helipad PW138N468, not a spot. The duplicate check is hard; the spacing check is labelled a consistency check. R020 [RE286N076] now clears P002 / P003 [PE286N088 / PE296N083] (design 7.14 m, flagged against the observed E55P). *Round 1 (R1-5): the spacing check modelled the wing only; it now uses wing + fuselage, and RE459N093 / HE461N103 no longer touch.* |
| 15 | Size vs observed types under-counted (minor) | **fixed** | Observed spans now come from every adsb.lol type in the evidence: 30 spots wider than design, 17 than capacity. The check's recount agrees with the flags. T003, T047, R048 and the others carry the flag. *With the round-1 planform: 32 and 18.* |
| 16 | OSM refs E, D, F where AL-5015 shows apron (minor) | **fixed** | `ref_src: inf` + `ref_note` on 490634605, 204801016 and 490634609, confirmed by eye on the registered raster. check_airport reads the labels from the PDF (check 3). |
| 17 | Hangar aprons: lane rule, MRR walls, footprints vs buildings (minor) | **fixed; extended in round 1** | Real-wall ray, apron-only strip, AC object distances, occupancy and roof tests, by-eye rejects. Wing shapes vs buildings are now part of the sizing and the check. H006, H001 gone; H010 on the real wall [HW100N602]. R056 is now the Hangar C apron spot [HE623S150]. *Round 1 (R1-2, R1-3): HE623S150 is now an inf door spot (one session); own hangars are obstacles; rule spots need a connection to the taxi network and a by-eye review (HE221N301 dropped).* |
| 18 | Building outlines 3–6 m off; statistics hid them (minor) | **fixed in the cross-check** | Roof-edge search widened to ±8.1 m, in both NAIP years; outlines with the same shift in both years are flagged (`docs/phase1_crosscheck.md` #15). The outlines are not corrected in the data (OSM obs); they are candidates for an OSM note. |
| 19 | Tie-down `aircraft_seen` misses aircraft; 3 aircraft without spot (minor) | **partly fixed; extended in round 1** | Planform test: 39 of 80 tie-downs now record an aircraft, and all 14 listed by the review are among them. The three aircraft between rows still have no spot: no tee under them, no nested row searched (section 5). *Round 1 (R1-4): the planform test missed TW054N324; with a ±3 m / ±10° tolerance 48 tie-downs record an aircraft. 42 parked aircraft without a spot are listed (section 5), not 3.* |
| 20 | Hot-spot check vacuous for HS 2–4 (minor) | **fixed** | Reported as "not checkable against the CS". |
| 21 | Vehicles as obs ramp spots; reports understated it (major) | **fixed** | As #13. Reports corrected. Clipping the OSM apron to airside is **not done**; the review and the new tests cover the spots. |
| 22 | H006 blocks taxiway F; no spot-vs-taxiway check (major) | **fixed** | Inferred spots keep the AC object distances (rule and hard check). Spot-vs-taxiway distances are reported per src (check 6). H006 is gone. |
| 23 | FAA registry not done, not reported (major) | **deferred: owner** | Listed as open in section 5 and in ATTRIBUTION, with the owner's steps. HTTP 403, not worked around. |
| 24 | No signs, lighting fixtures, markings; not listed (major) | **partly fixed** | `not_yet_sourced` section; the tower-closed lighting schedule is in the runway elements. Fixture and sign positions are **deferred** to sourcing (Phase 4). |
| 25 | Taxiway snapping nominal; no widths; runway overlaps unflagged (major) | **partly fixed** | 4 ways moved (E, F added); `on_runway` on 13 overlapping ways; widths measured on 14 ways plus an inf AC default on all. Edge geometry is **deferred**. *Round 1 (R1-1, R1-6): the moves and the widths were revised; see section 7.* |
| 26 | Size class unfit for placement (major) | **fixed** | `capacity_span_m` beside the AC `max_span_m`; tiered sizing; duplicates merged and vehicles removed first; flags. |
| 27 | obs = one sighting; unstable ids; spots missing where aircraft park (major) | **mostly fixed** | `strength` + the ≥ 2-observation rule (ramp 33 obs / 34 inf); position-derived ids; ref_point; the T-hangar statement corrected. Real designations for the West tie-down apron, the NE road strip and most T-hangar rows remain **open**: PLAN Q3 and section 5. *Round 1 (R1-2): the "≥ 2 independent observations" rule counted one session up to three times; it now counts sessions.* |
| 28 | Hard-coded P016 / P017 in not_placed (minor) | **fixed** | Generated from the spots: PW072S220 / PW049S181. |
| 29 | Reproducibility (minor) | **fixed** | `fetch_osm.py` keeps `fetched_utc` and the log on a cache-only re-merge; checked byte-identical. Cross-check metrics committed. The GeoTIFF dependency is documented (section 4). |
| 30 | Report statements wrong (minor) | **fixed** | Hold list (section 2); apron labels 5 / 6; T-hangar statement; image count in the cross-check; GA TRANSIENT RAMP as an inference everywhere. |
| 31 | Weak or circular checks presented as validation (minor) | **fixed** | Consistency checks are labelled; check 3 reads the PDF; the cross-check hot-spot comparison is described as a transform comparison. |
| 32 | obs/inf inconsistencies; missing ref point (minor) | **fixed** | Segmented circle; fire-station deviation; `adsb/SOURCES.json` duration wording; `ref_point` on every spot. |
| 33 | PLAN §1 facts wrong (minor) | **fixed** | PLAN §1: "FBO ramps (×3)"; Tower 118.9 is in NASR *and* the CS. Both are marked as corrected. |

## 7. Round-1 re-check (2026-11-12): findings and outcomes

An independent re-check of the Phase 1 data raised seven findings. Each was fixed in the tools, not by editing outputs.
The build was then run twice from scratch (byte-identical: `hwd_airport.json` 6864aef4…, `.js` 112caacf…).
`check_airport.py` passed every hard check, and `plot_overlays.py --docs` was re-run. I looked at every regenerated image
before writing this. "Fails on the reviewed build" means `check_airport.py --data <build at commit 7afa0ac>` fails that test.

| # | Finding (severity) | Outcome | What was done; evidence |
|---|---|---|---|
| R1-1 | Taxiway E 490634605 a zig-zag: on the paint over s 45-60 / 110-145 m, back at the OSM position 3.3 m off over s 0-22 / 78-92 m; the hard check passed it; the report called it fixed (major) | **fixed; the fix broke the taxi network, repaired in round 2 (R2-1)** | *Cause:* `window_corr` over sparse faint ridges tapers to 0 wherever a window lacks ridges. *Fix:* each way is moved as a whole onto a robust smooth fit of all its yellow ridges, or not at all (section 2). E's paint reads 2.2-9 DN, so the ridge test now samples every 2 m, ±5 m, from 2.5 DN with the yellow test. E: curve −3.27 to −3.51 m, 89 % inliers, MAD 0.12 m; only the 15 m junction tapers are off the paint. F: +1.66 m drifting to +0.2 m, no taper-back to the old position. The 2 taxilanes were refitted the same way. 30 unmoved ways record their off-paint windows. D 204801016 stays open: colour ambiguous (b* 5.4-8.0). *Check:* 20 m off-paint windows (hard for moved ways), lateral kinks > 0.5 m (hard), unrecorded offsets (hard). Current build: 0 / 0 / 0; largest kink 0.15 m. The reviewed build fails all three (E: −3.21 m at s 70 m, kink 1.96 m). Ribbons looked at: `out/phase1/r1/rib_*.png`. *Round 2 (R2-1): moving whole ways one by one left 22 joins on the moved ways without a shared vertex, and the 15 m taper exemption hid E's far-end taper; junctions are now solved over the network and the exemption is gone.* |
| R1-2 | "≥ 2 independent observations" counted one session two or three times; HE623S150 obs from one 47-min session; its disc overlapped its own T-hangar by 54.9 m², exempted by the check (minor) | **fixed; session rule corrected in round 2 (R2-2)** | `parked_stays.py` gives every stay and signal edge an opaque `session` number. A session is one aircraft's continuous presence at one place; the number is assigned by position and carries no identity. Check 9 verifies that a session never holds two starts or two ends or spans more than 30 m. The build counts NAIP years + sessions. HE623S150 is now inf; HE625S176 and HE154S380 became obs (start and end from two different sessions). *Round 2 (R2-2): for HE154S380 those two sessions were one aircraft's single presence (a power cycle); it is inf again, and so are RE181S395 and RW166N607.* The ramp split stayed 33 obs / 34 inf. HE623S150 is an explicit **door spot**: heading nose in to the nearest wall point [inf]; only its nose may enter its hangar; its wing keeps 1.0 m. Every other spot treats its own hangar as an obstacle. *Check:* sessions consistency plus an independent radius recount (hard; 0 below 2); planform vs every building including the own hangar (hard; 0). The reviewed build fails both (recount finds HE623S150 at 1 session; 3 spots overlap their own hangar). |
| R1-3 | Rule spot HE221N301 in the landside truck / bus yard, 114 m from any taxiway (minor) | **fixed** | Rule spots must be reachable from an open taxiway / taxilane over OSM pavement around buildings within 75 m (`CONNECT_M`, chosen: the plausible ones lie 20-69 m away). HE221N301 (119 m) is dropped by that rule. All 9 remaining rule spots were looked at in both NAIP years and recorded as "ok" in `HGR_REVIEW` (`out/phase1/r1/hgr_rule_sheet_*.png`). *Check:* independent Dijkstra path (22-74 m, hard) and a required "ok" review (hard). The reviewed build fails both. Apron 289829587 is still not clipped (section 5). |
| R1-4 | Planform test misses aircraft (TW054N324); more aircraft lack a spot than the 3 deferred (minor) | **partly fixed; rest listed (known gap); list extended in round 2 (R2-3)** | The tie-down planform is tried at ±3 m along the axis and ±10°. Values split cleanly (≤ 2.1 vs ≥ 5.6 m²), and the 18 new hits were each confirmed by eye. `aircraft_seen`: 48 of 80 (was 39); TW054N324 now records 2024. Unspotted parked aircraft: a by-eye pass over every apron found **42** (table in section 5; `unspotted_aircraft` in the data). They are listed, not spotted; the check fails if a listed one gains a spot within 5 m. The NE-strip painted markings are noted (section 2). *Round 2 (R2-3): the list missed the 6-aircraft back row of the nested double row on the FBO Ramp (north-east); added, and an omission sweep in the check now catches such gaps (48 listed).* |
| R1-5 | Spacing check modelled a spot with a heading as a wing segment only; RE459N093 and HE461N103 touched (minor) | **fixed for spots with a heading; completed in round 2 (R2-4)** | Build and check use a wing + fuselage planform. The fuselage is span × length / span of the widest observed type (FAA ACD), else C172 0.754; 24 % lies ahead of the reference point. Without a heading the disc is scaled by max(1, ratio). Rule-spot placement uses the same planform. The check recounts the ratio from the evidence (hard). Design minimum 3.046 m, capacity minimum 0.995 m; 0 violations. RE154S340 already had no design size and is listed. The reviewed build fails: RE459N093 / HE461N103 1.77 m at design size, 12 capacity violations. *Round 2 (R2-4): the heading-less disc of diameter span × max(1, ratio) did not contain the tail; it now has radius span × max(1/2, 0.765 × ratio).* |
| R1-6 | Some 'obs' widths unreliable (IQR ≥ value); 38 ways carried a value from 1-4 stations under a note saying null (minor) | **fixed** | No value below 5 stations; obs only with IQR ≤ 1.5 m (6 ways); otherwise inf with `naip_reason` (8 ways). The note now states the rule. *Check:* hard rule test; 0 violations now, 46 on the reviewed build. |
| R1-7 | Provenance residuals: the "0 non-obs/inf src" claim not literally true; no ODbL URI in some files; two SOURCES entries without made_by / note (minor) | **fixed** | The ODbL URI is now inside the files, written by the tools: the OSM extract (`fetch_osm.py` adds a `licence` key after `sha256_unstripped` is taken; re-merged from cache; downstream only the sha changed); the OSM API meta (re-run, one live request, same reconstruction); and the two Phase 0 summaries (the scripts print the notice as their first line; otherwise byte-identical). made_by was added to the two meta entries and the OSM API note updated (the SOURCES files are hand-kept records). Apron `name_src` and `size.observed_src` now hold obs / inf, with `name_from` / `observed_basis`. The claim is corrected in section 6 #6. *Check 9:* every SOURCES entry has made_by / note (hard); every text / JSON file whose SOURCES licence names the ODbL carries the URI (hard, 14 files); `src` values listed (ga_types `none` documented). `naip_blob_review.json` and `naip_visual_notes.json` are own NAIP work that name OSM ids only in prose; they are not treated as ODbL-derived. |

Not changed and still open after round 1: the FAA registry (403), the adsb.lol `www.` quotes, signs / lighting / markings,
the D offset, and whether the 42 unspotted aircraft become spots.

## 8. Round-2 re-check (2026-11-13): findings and outcomes

A second independent re-check of the round-1 build raised four findings. Each was fixed in the tools, not by editing
outputs. `tools/adsb/parked_stays.py` was re-run (and once more: byte-identical); the build was then run twice from
scratch with every `__pycache__` deleted (byte-identical: `hwd_airport.json` df5a8828…, `.js` 7781349a…).
`check_airport.py` passed every hard check on that build, and `plot_overlays.py --docs` was re-run (I looked at the
regenerated FBO Ramp (north-east) and West Hangars images; the overlays do not draw `unspotted_aircraft`). "Fails on the
round-1 build" means `check_airport.py --data <round-1 build>` fails that test; the round-1 build is the one the
re-check examined (`hwd_airport.json` 6864aef4…, kept as a scratch copy; the checkpoint commit 44ab3fd holds a later,
partial round-2 build). "The 7afa0ac build" is the one the round-1 re-check examined.

| # | Finding (severity) | Outcome | What was done; evidence |
|---|---|---|---|
| R2-1 | Moving whole ways broke the taxi network: of the interior joins on the 4 moved ways, 22 no longer shared a vertex (12 gaps up to 2.74 m, 10 crossings with an overhanging stub); no connectivity test; section 2 claimed the junctions stayed where OSM has them (major) | **fixed** | *Cause:* each way was moved on its own; only its own end vertices were held, so a way ending on a moved way's interior stayed at the old node. *Fix* (`build_airport.network_fields`, section 2 "Junctions"): every shared OSM vertex is one node with one displacement; a node on a way's interior follows that way's final line; an end-only node follows the moved way(s) whose paint holds up to it, else stays; ends are tapered to their node; a shallow fork (204801549 leaving E at 9°) starts where the moved lines meet (16.2 m along it); junction vertices survive simplification. 22 unmoved ways now have an end attached to a moved junction (0.13-3.51 m). The reviewer's script (scratch `topo2.py`), run on the new build: all 31 junction pairs that touch a moved way share a vertex; 30 meet at the node, and the fork pair (204801549 / E) meets 15.8 m from it, so the script's 8 m local gap is undefined there. On the round-1 build the same script gives 22 pairs without a shared vertex, 12 of them with a gap. Looked at on NAIP 2024 crops with OSM and built lines: E's two ends, the fork, and F's junctions with 204797831 and 289829586. *Check* (new, hard): topology test (section 4, check 3): 166 of 167 junction vertices shared, 1 fork, 0 crossings away from a vertex. The round-1 build fails (78 junctions without a shared vertex, 11 with a gap > 0.05 m; 43 crossings); the 7afa0ac build fails too (73 / 42), mostly through junction vertices dropped by the simplification on unmoved ways. The paint test lost its 15 m taper exemption, and a zig-zag test now covers every changed way: the round-1 build fails the first (E's far-end taper, +1.02 m), the 7afa0ac build fails the second (E, 0.95 m at s 84 m). The section 2 text is rewritten. |
| R2-2 | The session rule split one aircraft's uninterrupted presence: events linked only when ≤ 20 min apart, and a signal end followed by the same aircraft's next start at the same place always made two sessions. HE154S380 obs from one presence; RE181S395 and RW166N607 obs on one parked aircraft; the check's recount reused the session numbers (minor) | **fixed** | *Fix* (`parked_stays.py sessions()`): no time limit; consecutive events of one aircraft ≤ 15 m apart are one session unless it has a fix > 30 m away or airborne in between. 522 sessions (630 before); 14 hold a power cycle. HE154S380, RE181S395 and RW166N607 are now inf; HE625S176 stays obs (that aircraft flew between its two events); 25 other spots lost sessions but stay obs. Ramp 31 obs / 36 inf, hangar aprons 3 / 11. The rule errs towards fewer sessions when an outage hides a departure (section 2). *Check* (new, hard): a presence recount from the gitignored per-aircraft files with own code, not the session numbers: 0 obs spots below 2 (106 same-aircraft pairs joined); on the round-1 build it finds the three spots. It is SKIPPED in a clone without `refs/cache/local/adsb/`. The D1 session test now allows power cycles (starts / ends differ by ≤ 1; ≤ 30 m). Report sections 2, 3, 4 and 7, ATTRIBUTION and `adsb/SOURCES.json` updated; the R1-2 row's HE154S380 statement is annotated. |
| R2-3 | The unspotted list (42) missed the back row of the nested double row on the FBO Ramp (north-east), about 4 aircraft 9.5-10.5 m from the nearest spot; the check could not detect omissions (minor) | **fixed for the found row; list still not proven complete** | Crops of NAIP 2024 (0.05-0.07 m, spots drawn) show a back row of **6** aircraft behind the 6 front-row spots (NAIP 2022, 0.07 m: the same nested layout, with aircraft on 3 of these back-row places and painted tee marks on two empty ones): (455.7, 14.9), (465.7, 8.5), (476.9, 4.2), (486.5, −2.1), (497.1, −6.7), (507.8, −11.3), ±2 m; added to `UNSPOTTED_NAIP2024` (48 listed). They lie 7.8-10.6 m from the front-row spots. *Check* (new, hard): the omission sweep (section 4, check 6) shows every bright NAIP 2024 aircraft-mask part on an OSM apron more than 7.5 m from every spot, listed aircraft and reviewed blob; each needs a by-eye verdict in `build_airport.SWEEP_REVIEW`. I looked at all 49 parts on 0.12 m tiles (and closer where unclear): 28 vehicles, 13 paint, 1 kerb, 5 the far part of an aircraft at a spot (RE048N669, RE142S348, RE171S300; RE277N271 and RE308N064 at about 6 m, taken as the same position [inf]), 2 parts of listed aircraft; no unlisted aircraft. On the round-1 build the sweep fails with one part without a verdict, the back row (486.3, −0.9; 53.8 m²). Not covered: dark aircraft, aircraft in shadow, aircraft off the OSM aprons. Whether the listed aircraft become spots is still open. |
| R2-4 | Spots without a heading (71) were sized as a disc of diameter span × max(1, length / span), which does not contain the build's own fuselage (tail 0.577 × span from the reference point for the C172 default); 38 heading-less pairs fall below 1.0 m with a containing disc (minor) | **fixed** | *Fix* (`build_airport._shape`, `disc_k`): the disc radius is span × max(1/2, (1 − 0.235) × length / span), the farther of wingtip and tail, recorded in `size.planform.disc_radius_per_span`. The sizes shrink where heading-less spots are close: `capacity_below_smallest_common_type` 27 spots (10 before), e.g. RE127N262 / RE131N273 9.58 m each; `observed_type_wider_than_capacity` 29 (18). That is the cost of not knowing the heading, not a statement that those positions are too small in reality. *Check* (new, hard): each heading-less disc must contain the wing + fuselage planform at every heading (5° steps) at both sizes; capacity pairs 0 below 1.0 m (minimum 0.995 m, the 0.01 m floor rounding), design pairs 0 below 10 ft. The round-1 build fails the containment test (for example RE068N260, RE127N262, RE131N273, RE139N285). |

Still open after round 2: the FAA registry (403), the adsb.lol `www.` quotes, signs / lighting / markings, the D offset,
whether the 48 unspotted aircraft become spots, and the sweep's blind spots (dark or shadowed aircraft, aircraft off the
OSM aprons).
