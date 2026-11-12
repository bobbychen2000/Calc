# Phase 1: the HWD airport data set (`data/hwd_airport.json` / `.js`)

Task G5, 2026-11-12. Built by `tools/build_airport.py` and checked by `tools/check_airport.py`. The build reads only
committed inputs and makes no network calls.

**Updated twice on the same day:**
- **By the Phase 1 cross-check** (`docs/phase1_crosscheck.md`). The AL-5015 registration had a bug: the 28R end of the
  diagram's runway bar was found 76 m short. It was fixed in `tools/osm/xcheck_osm_faa.py`, which moved the hot spots,
  the label anchors, two apron-name matches and the terminal.
- **By the Phase 1 review fixes** (section 6). The review's findings changed:
  - the parking model, and the taxiways E and F;
  - several fields: ref, width, on_runway, the lighting schedule, `not_yet_sourced`;
  - the provenance of the committed inputs.

  Section 6 lists every finding with its outcome.

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

The JSON is 642 kB. The `.js` twin is `export const HWD_AIRPORT = …` with a licence header.

| Section | Count | src | Content and origin |
|---|---|---|---|
| `runways` | 2 | obs | See below this table. |
| `taxiways` | 65 | obs | OSM centrelines with ref, status and OSM tags: 61 open, 2 `abandoned`, 2 `disused`; 10.3 km in total, 9.5 km open. Fields on each way:<br>• `naip_paint`: its NAIP paint measurement, including faint-ridge sections.<br>• `ref_src` / `ref_note`: 3 OSM refs that AL-5015 does not support along the way are `inf` (section 2).<br>• `on_runway`: present on every way that enters a NASR runway rectangle; 13 ways overlap it by more than 50 m.<br>• `width`: the NAIP grey-test width on 14 ways, and an AC default marked inf on all.<br>A1 carries the NASR wingspan limit of 100 ft, Z1 of 94 ft. A carries the remark "not visible from ATCT between B and C". |
| `taxilanes` | 78 | obs | OSM centrelines, 6.3 km in total. Two are moved locally onto NAIP paint (section 2). |
| `aprons` | 9 | obs | OSM polygons. Names are only where OSM tags them or AL-5015 labels them (see after this table). |
| `holds` | 18 | obs | OSM holding-position nodes. 16 are moved onto the yellow bar measured on NAIP 2024. Each records the runway, its distance from the centreline in ft, and the bar direction and skew. |
| `hotspots` | 6 | **inf** | HS 1–HS 5. HS 5 is two ellipses, one on A1 and one on Z1. Each is an AL-5015 ellipse mapped to the world, with the CS hot-spot text and the OSM taxiway refs inside it. |
| `helipads` | 9 | obs | OSM polygons: 6 on the "Helicopter Ramp" and 3 on the north-east FBO ramp. They carry the NASR remark about transient helicopters. |
| `hangars` | 34 | obs (footprint) | OSM footprint, name and letter (A–Q, EX1, EX2; "Hanagar K" read as Hangar K, inf).<br>• **kind** is inf: 18 `t_hangar_row` and 16 `box_hangar`, from the footprint shape (minimum rectangle ratio ≥ 3, width ≤ 22 m, fill ≥ 0.85).<br>• The FBO **role** is inf: APP Jet Center and Signature Aviation, by name.<br>• `adsb_signal_edges_8m` counts adsb.lol signal starts and ends within 8 m. |
| `buildings` | 17 | obs | **Control tower:** OSM way 204803620 (man_made=tower, service=aircraft_control, height 15.85 m), matched to the AL-5015 TWR label and the NASR ATCT. Its beacon is inf.<br>**Fire station:** OSM node 368168603, a point only. It now carries the cross-check `deviation` [inf]: the AL-5015 block, with a building on NAIP, is 45 m east.<br>**Terminal / Airport Administration:** OSM way 1372203791, name inf, placed by the AL-5015 label leader.<br>**Other:** 14 OSM buildings inside the aerodrome, role unknown. |
| `markers` | 2 | obs | The windsock (OSM node; NASR: lighted) and the segmented circle around it. The circle is obs (NASR flag, NAIP). Its diameter of about 31.5 m was read by eye, so `diameter_src` is inf; its centring on the windsock gives `position_src` inf. |
| `parking` | 178 | 115 obs / 63 inf | Tie-downs, ramp spots, hangar aprons and helipad spots (section 3). |
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

Elements with `src` obs or inf: 418 elements, with `parking` counted per spot. **349 obs / 69 inf** at element level: the 6 hot spots and 63 parking spots are inf. With the labels and not-placed items there are 431 elements.

Many obs elements still carry inferred sub-fields:
- all 34 hangar kinds;
- 2 FBO roles;
- 6 apron label matches;
- all 80 tie-down headings and the headings of the 10 rule-made hangar-apron spots;
- every spot's size;
- the beacon position;
- the segmented-circle diameter and position;
- 3 taxiway refs;
- every taxiway default width.

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

**Taxiway and taxilane paint** (`tools/imagery/paintline.py`, a fork of sfo3d's; `window_corr` from sfo3d is reused
unchanged):
- The yellow index min(R, G) − B is profiled across each OSM way every 4 m on NAIP 2024.
- *Strong rule:* a ridge counts when it reaches ≥ 10 DN, is unambiguous, and has b* ≥ 9 (white-paint rejection). A line moves only where a 7-sample window agrees.
- *Faint rule* (new since the review): faint ridges (≥ 4 DN) with b* ≥ 8 (yellow) are grouped per 50 m section.
  - A section with ≥ 8 such ridges whose median offset is ≥ 1.0 m and whose IQR is ≤ 0.6 m is an offset. So is a whole way with ≥ 20 such ridges and an offset ≥ 1.5 m.
  - Such a way is moved onto the faint ridges, using `window_corr` without the strict rule for shifts above 1.5 m.
  - Every way records its sections before and after the move (`naip_paint.faint`).

HWD's centrelines are badly worn on NAIP. **4 of 143 ways moved, over 562 m in total:**
- **Taxiway E, way 490634605** (faint rule): it lay 3.3 m west of its worn yellow centreline over its whole length (the review's finding; 25 faint ridges, median −3.31 m, IQR 0.31 m). It moved by up to 3.36 m over 136 m. Afterwards its 50 m section reads median 0.0 m. Its end points are not moved, because the corrections taper to zero there.
- **Taxiway F, way 490634609** (faint rule): it moved by up to 1.68 m over its first 145 m, which had read +1.47 to +1.54 m. Afterwards the sections read 0.02–0.10 m.
- Taxilane 204801549 (strong rule): moved by up to 1.45 m over 190 m. The residual is 0.06 m; it was checked on a 0.08 m view.
- Taxilane 1366760486 (strong rule): moved by up to 0.64 m over 91 m; residual 0.14 m.

`tools/check_airport.py` now measures the faint ridges again on every way's final geometry. No 50 m section shows an
offset (32 sections are measurable). The review also found D 204801016 1.2–1.65 m off over 130 m north of A, with its own
method. Our ridge test finds fewer than 8 yellow ridges per section there, so it cannot confirm that offset, and D is
unchanged.

**Taxiway refs against AL-5015** (new). Three OSM refs run where AL-5015 draws apron, with no label. We checked this by
eye on the 400 dpi raster with the ways drawn through the diagram affine. These ways keep their OSM ref with
`ref_src: inf` and a `ref_note`:
- E 490634605 lies inside the GA TRANSIENT RAMP area.
- D 204801016 lies north of A.
- F 490634609 runs through the WEST HANGARS / FBO RAMP area.

**On the runway** (new). `on_runway` records the length of each way inside a NASR runway rectangle. 13 unnamed taxiway
ways overlap a runway by more than 50 m (`runway_overlap: true`), for example 58169722 (202 m) and 204801038 (382 m).
The Phase 2 taxi graph should treat those parts as runway.

**Widths** (new):
- The NAIP grey-test pavement width is measured where possible, on cross profiles every 6 m. This was possible on 14 of 139 open ways (median 15.0 m). The width includes shoulders of the same grey; concrete that reads tan is missed.
- Every way also carries an AC 150/5300-13B Table 4-2 default width, `default_src: inf`, because the TDG of each way is not known: 35 ft (10.7 m, TDG 2) for taxiways and 25 ft (7.6 m, TDG 1) for taxilanes.
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
- **Aircraft on a tie-down** (new since the review): the aircraft mask is measured inside the outline of a GA single parked on the tee (wing box ±5.5 × ±1.5 m, fuselage ±0.8 m from 2.5 m ahead to 6.5 m behind the bar). ≥ 2.5 m² counts as an aircraft. Calibration: empty tees seen in both years carry 0–0.9 m²; the 14 positions the review saw occupied carry 2.8–7.6 m². I checked this by eye on the whole Green Ramp.

Only the Green Ramp (the GA Transient Ramp, inferred) has tee rows: 69 seeds, 7 rows, pitch **12.15 m** (median seed
residual 0.16 m). That gives 80 tie-downs:
- 66 obs: tee seen in 2024 and 2022 (33), 2024 only (17) or 2022 only (16);
- 14 inf. On every one of them NAIP 2022 and / or 2024 shows an aircraft.

`aircraft_seen` now holds 39 of the 80 tie-downs: 25 in 2024 only, 8 in 2022 only and 6 in both. Most tees seen only in
2022 have an aircraft over them in 2024.

The other aprons gave 0–21 isolated seeds and no rows.

**Heading** = the stem direction + 180°. On the Green Ramp, parked aircraft sit with the horizontal tail over the stem end
(NAIP 2024, by eye).

**Other spots** (`build_airport.parking`), in build order:

| Step | Source | Rule |
|---|---|---|
| helipad | OSM helipad centres (9) | made first, so that ADS-B evidence on a pad attaches to its spot. Fixed-wing ADS-B on a pad is kept as evidence of that pad, not as a ramp spot: the review's GLEX spot R073. |
| ramp / hangar_apron | adsb.lol parking spots (stays of 5 min or more) | a spot within 5 m of a hangar outline is that hangar's apron spot: an aircraft at its door, like the review's R056 at a T-hangar wall |
| ramp / hangar_apron | clusters of ≥ 3 adsb.lol signal starts / ends (≥ 2 within 10 m of a hangar) | single linkage 4 m |
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

**Inferred hangar aprons** (rule spots). One spot per box hangar without an observed spot. It is 8 m out from the *real*
wall, on the normal through the middle of the longest side, and it needs all of these:
- the 2–14 m strip in front of that wall is OSM **apron** (taxiway buffers no longer count) and free of buildings;
- the outline of an ADG I aircraft parked nose-in keeps the AC 150/5300-13B Table 4-1 object distances: 13.6 m from open taxiway centrelines and 12.0 m from open taxilane centrelines;
- no NAIP 2024 objects lie in that outline, and the point is not on a white roof (median grey > 235);
- the hangar is not on the recorded by-eye rejection list: an unmapped annex roof at APP Jet Center, and a walled yard at hangar 204800998.

The review's H006, which sat 5.0 m from the taxiway F centreline with its tail across F, is gone; so is H001. H010 now
sits on the real wall of its L-shaped hangar.

**Duplicates.** Ramp and hangar-apron spots closer than 9.5 m are one parking position. That is below the span of the
smallest common type, C150 / C152 (10.17 m, FAA ACD), minus position noise. Such spots are merged into the one with the
strongest evidence before sizing; H017 / H018 became one spot.

**src of a spot** (new). For ramp and hangar-apron spots, `src` is about the *role* "parking position". It is obs only
with **≥ 2 independent observations**: NAIP years with an aircraft, adsb.lol stays, and signal-edge events (max of starts
and ends). One sighting gives inf. `strength` lists the observations. The other kinds keep their rules:
- a tie-down is obs when its tee is seen;
- a helipad is obs when it is mapped in OSM;
- a rule spot is inf.

**Sizes** (`size`, always inf). They are solved in tiers: painted tie-down rows first, then obs spots, then inf spots, so
that a weak spot cannot shrink a strong one. Buildings and helipad discs (rotor size, or the smallest OSM pad, 10.1 m,
when unknown) are fixed obstacles; a hangar-apron spot may enter its own hangar. Within a tier, each pair of spots within
40 m shares the space equally.
- **`max_span_m`**: the AC design value, which keeps the wing shapes 10 ft (3.05 m) apart. Sources: AC 150/5300-13B Chg 1 Table 5-1 ("I and II: 10 ft (3 m)") and Figure E-2 ("Wingspan plus 10 ft (3 m) for critical aircraft"). The upper bound is ADG I, 49 ft (14.94 m, Table 4-1), or the ADG of a wider type seen there. The wing shape is a segment across the heading, or a disc when the heading is unknown.
- **`capacity_span_m`** (new): the same with a 1.0 m gap, the practical size for placing aircraft. HWD's own use: C172s on the 12.15 m pitch leave 1.15 m.
- **`observed_max_span_m`** (obs): the widest adsb.lol type seen at the spot (FAA ACD wingspan), now counted from *every* stay, signal start / end and merged duplicate in the evidence. `observed_type_spans_m` lists them.
- **`flags`**:
  - `observed_type_wider_than_design`: 30 spots;
  - `observed_type_wider_than_capacity`: 17;
  - `capacity_below_smallest_common_type`: 10;
  - `no_design_size`: 1, an inf BE20 stay 14.3 m from an obs jet stand.

Green Ramp rows: design 9.1 m (pitch − 10 ft) and capacity 11.15 m (pitch − 1.0 m). Overall: 154 spots ADG I, 5 ADG II,
3 ADG III; 120 of 162 design sizes are limited by a neighbour, a building or a helipad. Helipad spots carry `max_rotor_m`:
the OSM pad size, or null.

**ref_point** (new) says what point each position stands for:
- the tee junction (wing line), 80 spots;
- the GNSS antenna median, 52;
- the NAIP blob centroid, 24, or the centroid of one half of a split blob, 3;
- the helipad centroid, 9;
- the rule point, 10.

**ids** (new) come from the rounded position, so a rebuild keeps them: `RE187N279` is a ramp spot 187 m east and 279 m
north of the ARP. The prefixes are T (tie-down), R (ramp), H (hangar apron) and P (helipad). Zone labels follow D3 and
are never official numbers.

## 3. Parking spots

| Kind | Total | obs | inf | Where |
|---|---|---|---|---|
| tiedown | 80 | 66 | 14 | Green Ramp, rows 1–7 |
| ramp | 67 | 33 | 34 | FBO Ramp (north-east) 44, FBO Ramp (south) 10, Green Ramp 6, West Hangars 6, near hangar 204797798 1 |
| hangar_apron | 15 | 3 | 12 | 15 hangars. The 3 obs are adsb.lol spots at Hangar C, Hangar G and hangar 971132675. Of the 12 inf, 10 are rule spots at box hangars and 2 are single adsb.lol sightings (Hangar B, Signature Aviation). Four of these hangars are T-hangar rows: B, C, G and 971132675 |
| helipad | 16 | 13 | 3 | Helicopter Ramp 6, FBO Ramp (north-east) 5, FBO Ramp (south) 2, unmapped helicopter area south of 10R/28L 2, West Hangars 1 |

What the ramp spots rest on:
- 26 rest on one NAIP 2024 aircraft only (inf), and 1 on aircraft in both NAIP years (obs);
- 14 rest on adsb.lol stays alone: 8 have one stay (inf) and 6 have two or more (obs);
- 26 rest on adsb.lol signal edges, with or without stays. All 26 have at least 2 signal events, so all are obs.

Headings are known for all 80 tie-downs (inf, from the tee) and for the 10 rule-made hangar aprons (nose toward the
hangar). No ramp spot has one: no adsb.lol spot had ≥ 3 consistent taxi-in headings (G4: the taxi-in heading matches the
reported heading only 29 % of the time).

## 4. Check results (`tools/check_airport.py`, run 2026-11-12 on the current build)

All hard checks passed. Several of them are *consistency* checks: the build derives the data from the same rule or source
that the check uses. The report says so.

1. **Runways vs NASR**, recomputed from the NASR rows rather than from `hwd_frame`'s constants:
   - 69 fields compared, 0 mismatches;
   - worst position difference 3.8 mm (the data is rounded to 0.01 m);
   - plane lengths +0.06 m and −0.07 m against the NASR ft values;
   - traffic sides and TPA agree with the CS.
2. **Pavement vs NAIP:**
   - the outline equals the NASR rectangle to 5.3 mm;
   - the edge residuals are in the table in section 2, all within the 0.6 m tolerance (the largest is 0.12 m).
3. **Taxiway designations, read from the AL-5015 PDF itself** (new):
   - 23 taxiway label glyphs of the text layer lie 0.1–11.6 m from an OSM way with the same ref; the tolerance is 15 m;
   - the label set {A, A1, B, C, D, E, F, Z, Z1} equals the OSM refs;
   - every other single-letter glyph (closed-surface X marks, runway-side letters, symbol letters, the WEST HANGARS letters) lies ≥ 14 m from every taxiway centreline;
   - the three `ref_src: inf` ways are listed;
   - the A1 / Z1 wingspan limits are present.

   **NAIP paint per section** (new, hard): no 50 m section of any way shows a consistent faint-paint offset.
4. **Spot centres on pavement:** 176 inside OSM aprons. 2 helicopter spots pass only the NAIP grey test: they sit on the unmapped paved helicopter area.
5. **Spot centres in buildings:** 0. **Wing shapes vs building outlines** (new, consistency): 0 inside 10 ft at design size and 0 inside 1.0 m at capacity size.
6. **Spacing.** The 8 AC 150/5300-13B quotes were found in the committed extract.
   - Helipad spots now take part as discs (consistency check): 940 pairs within 40 m. The design minimum is 3.046 m, which is 10 ft minus the floor rounding of the sizes; the capacity minimum is 0.995 m; 0 violations.
   - **Duplicates** (new, independent): 0 ramp / hangar-apron pairs closer than 9.5 m.
   - **Observed types** recounted from all the evidence (new): 30 spots saw a type wider than the design size and 17 one wider than the capacity size, for example FBO-ramp spots where E55P, PC12 or C680 parked. The spots' own flags agree with the recount.
   - **Spot vs taxiways** (new). Against AC Table 4-1 ADG I object distances (13.6 m from a taxiway centreline, 12.0 m from a taxilane centreline), every Green Ramp tie-down's wing line is only 7.2–7.7 m from an OSM taxilane centreline (the real layout: tails toward the taxilanes). 34 ramp spots, 2 obs hangar-apron spots and 1 inf hangar-apron spot (an adsb.lol sighting) are also inside that distance. The 10 rule-made spots all keep it (hard).
7. **Hot spots:** HS 1 and HS 5 agree with the taxiways their CS texts name. HS 2–4 are *not checkable against the CS*, because their texts name no taxiway (earlier versions called them "consistent").
8. **Holds:** 16 of 18 have a NAIP bar; the offset from the OSM node is at most 0.60 m (median 0.30 m).
9. **Hygiene:**
   - all 431 elements have a valid `src` and `refs`;
   - the `.js` twin parses to the same object.
   - **D1** (new, extended): all 17 committed ADS-B-derived files were scanned against the hex, registration and callsign of the 1,098 aircraft that the recording saw within 5 km. The scan also looks for identity keys, per-row time keys, epoch numbers and N-number-like tokens. 0 findings.
   - **SOURCES coverage** (new): all 58 committed data files under `data/`, `refs/cache/` and `docs/phase1/` have an entry.

**Reproducibility.**
- Every input of the build is committed. The build reads the committed NAIP JPEGs, never the local GeoTIFF.
- The ADS-B pipeline (`tools/adsb/*`, about 20 s) and the OSM merge and parse were re-run. Before the review changes the ADS-B outputs came out byte-identical. After the changes, the OSM files came out byte-identical when `fetch_osm.py` re-merged from its cache: it now keeps the original `fetched_utc` and fetch log.
- Two dependencies stay local. The NDVI fields of `hwd_parked_stays.json` need the local NAIP GeoTIFF, but the build does not use them. `tools/plot_overlays.py` uses the GeoTIFF when present; its numbers are now committed as `docs/phase1/crosscheck_metrics.json`.
- A fresh clone cannot re-merge the OSM extract without the network, because `.parts/` is gitignored. The merged extract itself is committed.
- Build: `hwd_airport.json` sha256 b1262637…, `.js` c46fa6f6…; about 175 s. A second build from scratch, with every `__pycache__` deleted first, gave byte-identical files.
- Environment: `build_env` in the file records Python 3.13.18, numpy 2.5.3, scipy 1.18.1, shapely 2.2.0, Pillow 12.3.0 and poppler 24.02.

## 5. Gaps and things not verified

- **FAA aircraft registry: not obtained (open).** PLAN §7 Phase 1 asks for it. registry.faa.gov answered HTTP 403 to the one automated attempt (`refs/cache/local/registry/fetch_log.json`). `tools/registry/build_lookup.py` and `registry_mix.py` have not run on real data; `registry_mix.py --onfield-only` gives the same 243 on-field aircraft as Phase 0. Next step for the owner:
  1. Download `https://registry.faa.gov/database/ReleasableAircraft.zip` by hand.
  2. Run `tools/registry/fetch_registry.py --record-manual`.
  3. Run `build_lookup.py` and then `registry_mix.py`.

  Nothing per aircraft is committed (D1).
- **Signs, lighting fixtures and marking geometry are not sourced** (`not_yet_sourced`). Signs: only the two NASR distance-remaining remarks; no position, text or direction. Lighting: types, codes and the tower-closed schedule only; no VASI / PAPI box or REIL unit positions, and no taxiway edge lights or reflectors. Markings: only hold bars, the displaced-threshold bars and the runway edge stripes are measured. Also missing: the five unlit wind cones and the painted H circle (cross-check #7, #8). Candidate sources: NAIP, FAA siting standards applied as rules (inf), owner photos.
- **Taxiways.**
  - Most centrelines are still OSM as mapped, because the paint is too worn to measure; only 4 ways moved.
  - Widths: measured on 14 ways only; the rest carry an AC default (inf); edges are not measured.
  - The D 204801016 offset the review found north of A is not confirmed by our ridge test.
- **NAIP-only ramp spots** (27): every blob is reviewed by eye, but 26 of them rest on one image and are inf.
  - The OSM apron 289829587 still takes in the landside lots. It is not clipped to airside; the review and the occupancy and roof tests handle the spots there.
  - Rows of aircraft parked wing to wing are covered only partly: the north-east strip along the road, the West Hangars tie-down area (about 15 aircraft, 6 spots).
  - Three aircraft on the Green Ramp lie 7–8 m from a tee, between rows, and have no spot: no tee was found under them and no nested row was searched for.
- **Size classes.** `max_span_m` follows the AC design rule and is tighter than the real use (Green Ramp 9.1 m against a C172 of 11.0 m). Use `capacity_span_m` for placement and `flags` for the spots where even that is smaller than the type seen there.
- **T-hangar bays and doors.** NAIP shows no door rhythm (G2). Four of the 18 T-hangar rows have a spot, all from adsb.lol: obs at Hangar C, Hangar G and hangar 971132675; inf at Hangar B. The other 14 have none. (The earlier "T-hangar rows get no spots" was wrong.)
- **Rule-made hangar aprons** (10) sit on the side that faces mapped apron, not on a known door.
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
| 4 | ODbL URI / notice missing in derived files (minor) | **fixed** | URI and attribution are now in `ga_types.json._meta`, `khwd_features.json`, `khwd_osm_xcheck.json`, `refs/cache/adsb/*.json`, the OSM meta, `osm/SOURCES.json` and `docs/phase1/crosscheck_metrics.json`. The two plain-text Phase 0 summaries rely on `adsb/SOURCES.json` (ODbL 4.2(d)), which now says so. |
| 5 | `naip/MANIFEST.json` without a SOURCES entry (minor) | **fixed** | Entry added. check_airport now checks SOURCES coverage: 58 files, 0 missing. |
| 6 | `src` reused for the ADS-B transport class; null src in ga_types (minor) | **fixed** | The field is now `feed` in stays, signal edges, holds and spot `feeds`, so 0 non-obs/inf `src` remain in any committed JSON. ga_types: `src: 'none'` plus a `src_legend`. |
| 7 | Segmented-circle diameter read by eye but obs (minor) | **fixed** | `diameter_src: inf` and `position_src: inf` with evidence. |
| 8 | Per-event ADS-B rows, rare LADD types (minor) | **partly fixed; rest deferred: owner (Q1)** | Exact `dur_s` removed from the committed stays (bucket only); run-up durations rounded to 10 s. Rare types are not coarsened, because that changes observed sizes; the options are listed for the owner. |
| 9 | Constants without a stated basis (minor) | **fixed** | A basis line was added to: `WEST_HANGARS_BOX`, `PITCH_RANGE` and the tee thresholds, `HGR_D`, `TERMINAL_TIP_PX` (window by eye), `AC_EXT_MIN` (its wrong "vans are shorter" rationale is corrected), every constant of `runup_holds.py` and `parked_stays.py`, the `events.py` thresholds, and `rwy_edges.py`. Most read "chosen; sensitivity not tested". |
| 10 | `__pycache__` written in sfo3d (minor) | **fixed** | `sfo3d/tools/models/__pycache__/` deleted (ignored; no tracked file was touched); `git status --ignored sfo3d pc12` is now empty. No hwd3d tool imports sfo3d code, and the fix runs wrote nothing under sfo3d. Note: `python3 -I` ignores `PYTHONDONTWRITEBYTECODE`, so hwd3d's own runs leave ignored `__pycache__` folders under `hwd3d/tools/`; I deleted them at the end. Use `python3 -I -B` to avoid them. |
| 11 | Cited pages and terms not committed or not re-read (minor) | **partly fixed** | (1) AC 5340-1M PDF p. 54 (para 2.9.1.3 / 2.9.1.5) added: the extract is now `ac150_5340_1m_chg1_p52-54_63.pdf`. (2) STAC items labelled "Planetary Computer service terms not reviewed". (3) NAIP / USDA quotes and (4) the adsb.fi quote are **deferred**: to be re-read before Phase 2 publishes credits. |
| 12 | Taxiway E 3.3 m from its paint (major) | **fixed** | Faint-paint rule (section 2): E moved by up to 3.36 m and F by up to 1.68 m. New hard per-section check: 0 offset sections. D 204801016 is not confirmed by our test (too few ridges). |
| 13 | NAIP ramp spots on vehicles / paint (major) | **fixed** | By-eye review of all 40 blob spots, recorded in `naip_blob_review.json`. 8 vehicles (R007, R009–R012, R016, R022, R042), 3 empty (R014, R017, R033) and 1 duplicate (R039) dropped. R041 and R080 split, R077 and R079 dropped. The other 24 are kept as aircraft; 26 of the 27 NAIP-only spots are now inf. |
| 14 | Overlaps and duplicates invisible to the check (major) | **fixed** | Helipads are sized and checked. Duplicates are merged before sizing (H017 / H018 → HE248N195); R039 dropped; R038 [RE405N217] is 14.93 m instead of 5.88 m. R073 (GLEX on a helipad) is now evidence on helipad PW138N468, not a spot. The duplicate check is hard; the spacing check is labelled a consistency check. R020 [RE286N076] now clears P002 / P003 [PE286N088 / PE296N083] (design 7.14 m, flagged against the observed E55P). |
| 15 | Size vs observed types under-counted (minor) | **fixed** | Observed spans now come from every adsb.lol type in the evidence: 30 spots wider than design, 17 than capacity. The check's recount agrees with the flags. T003, T047, R048 and the others carry the flag. |
| 16 | OSM refs E, D, F where AL-5015 shows apron (minor) | **fixed** | `ref_src: inf` + `ref_note` on 490634605, 204801016 and 490634609, confirmed by eye on the registered raster. check_airport reads the labels from the PDF (check 3). |
| 17 | Hangar aprons: lane rule, MRR walls, footprints vs buildings (minor) | **fixed** | Real-wall ray, apron-only strip, AC object distances, occupancy and roof tests, by-eye rejects. Wing shapes vs buildings are now part of the sizing and the check. H006, H001 gone; H010 on the real wall [HW100N602]. R056 is now the Hangar C apron spot [HE623S150]. |
| 18 | Building outlines 3–6 m off; statistics hid them (minor) | **fixed in the cross-check** | Roof-edge search widened to ±8.1 m, in both NAIP years; outlines with the same shift in both years are flagged (`docs/phase1_crosscheck.md` #15). The outlines are not corrected in the data (OSM obs); they are candidates for an OSM note. |
| 19 | Tie-down `aircraft_seen` misses aircraft; 3 aircraft without spot (minor) | **fixed / deferred** | Planform test: 39 of 80 tie-downs now record an aircraft, and all 14 listed by the review are among them. The three aircraft between rows still have no spot: no tee under them, no nested row searched (section 5). |
| 20 | Hot-spot check vacuous for HS 2–4 (minor) | **fixed** | Reported as "not checkable against the CS". |
| 21 | Vehicles as obs ramp spots; reports understated it (major) | **fixed** | As #13. Reports corrected. Clipping the OSM apron to airside is **not done**; the review and the new tests cover the spots. |
| 22 | H006 blocks taxiway F; no spot-vs-taxiway check (major) | **fixed** | Inferred spots keep the AC object distances (rule and hard check). Spot-vs-taxiway distances are reported per src (check 6). H006 is gone. |
| 23 | FAA registry not done, not reported (major) | **deferred: owner** | Listed as open in section 5 and in ATTRIBUTION, with the owner's steps. HTTP 403, not worked around. |
| 24 | No signs, lighting fixtures, markings; not listed (major) | **partly fixed** | `not_yet_sourced` section; the tower-closed lighting schedule is in the runway elements. Fixture and sign positions are **deferred** to sourcing (Phase 4). |
| 25 | Taxiway snapping nominal; no widths; runway overlaps unflagged (major) | **partly fixed** | 4 ways moved (E, F added); `on_runway` on 13 overlapping ways; widths measured on 14 ways plus an inf AC default on all. Edge geometry is **deferred**. |
| 26 | Size class unfit for placement (major) | **fixed** | `capacity_span_m` beside the AC `max_span_m`; tiered sizing; duplicates merged and vehicles removed first; flags. |
| 27 | obs = one sighting; unstable ids; spots missing where aircraft park (major) | **mostly fixed** | `strength` + the ≥ 2-observation rule (ramp 33 obs / 34 inf); position-derived ids; ref_point; the T-hangar statement corrected. Real designations for the West tie-down apron, the NE road strip and most T-hangar rows remain **open**: PLAN Q3 and section 5. |
| 28 | Hard-coded P016 / P017 in not_placed (minor) | **fixed** | Generated from the spots: PW072S220 / PW049S181. |
| 29 | Reproducibility (minor) | **fixed** | `fetch_osm.py` keeps `fetched_utc` and the log on a cache-only re-merge; checked byte-identical. Cross-check metrics committed. The GeoTIFF dependency is documented (section 4). |
| 30 | Report statements wrong (minor) | **fixed** | Hold list (section 2); apron labels 5 / 6; T-hangar statement; image count in the cross-check; GA TRANSIENT RAMP as an inference everywhere. |
| 31 | Weak or circular checks presented as validation (minor) | **fixed** | Consistency checks are labelled; check 3 reads the PDF; the cross-check hot-spot comparison is described as a transform comparison. |
| 32 | obs/inf inconsistencies; missing ref point (minor) | **fixed** | Segmented circle; fire-station deviation; `adsb/SOURCES.json` duration wording; `ref_point` on every spot. |
| 33 | PLAN §1 facts wrong (minor) | **fixed** | PLAN §1: "FBO ramps (×3)"; Tower 118.9 is in NASR *and* the CS. Both are marked as corrected. |
