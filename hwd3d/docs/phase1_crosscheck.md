# Phase 1 cross-check: `data/hwd_airport.json` against NAIP 2024 and AL-5015

Written 2026-11-12. **Updated the same day by the Phase 1 review fixes** (`docs/phase1_data_report.md` §6). The images
and the numbers marked *(review)* come from the current build, `hwd_airport.json` sha256 b1262637…; that build includes
the review fixes. The plots and numbers come from `tools/plot_overlays.py`; run it with
`python3 hwd3d/tools/plot_overlays.py --docs` (about 4 min; needs poppler). Every number below is in
`out/phase1/crosscheck_metrics.json`, unless it is marked "by eye". Since the review that file is also committed, as
`docs/phase1/crosscheck_metrics.json`. The NAIP numbers use the lossless local GeoTIFF
`refs/cache/local/naip/naip_2024_hwd_utm10n.tif` when it exists (`naip_source` in the metrics); a fresh clone falls back
to the committed JPEG, whose pixels differ by mean 2.1 DN.

Frame: the world frame of `tools/common/hwd_frame.py`. x is east and z is south, in metres from the NASR ARP.
Positions are given as (x, z).

## 1. Result in brief

- **I found and fixed a bug in our tools: the AL-5015 registration.**
  - The HS 4 hot-spot ring runs along the 10L/28R runway bar for about 90 px near 28R and cuts it into narrow strips.
  - G1's bar detection (`tools/osm/xcheck_osm_faa.py`) opens the black mask with a 9 × 9 px square, which removes those strips. Its 28R end therefore stopped 92.6 px (76 m) short of the true end.
  - The 4-point affine absorbed this as a shear: scales 0.956 / 0.724 m/px, residuals 15–31 m.
  - Everything placed from the diagram inherited the error: the hot-spot ellipses, the label anchors, two apron-name matches and the terminal building.
  - With the true bar end, the diagram fits the four NASR runway ends to 0.3–0.8 m with a 4-parameter similarity, and to 0.4–0.7 m with the affine. I fixed the detection, rebuilt the data set and re-plotted (section 5).
- **AL-5015 is drawn to scale at HWD**, much better than its stated ±600 ft:
  - Scale: 0.8254 m per px at 400 dpi, about 1:13,000.
  - Runway bars: 1,735.8 m and 946.7 m long, against NASR 1,735.5 m and 947.3 m. Drawn widths are 43.7 m and 22.4 m, against 45.7 m and 22.9 m.
  - Hangars: every one of the 34 OSM hangar footprints is 89–99 % covered by a black block of the diagram.
  - Taxiways: 95–100 % of the OSM taxiway samples (every 5 m) fall on diagram pavement, per ref; the worst sample is 5.0 m off.
- **The data mostly agree with NAIP 2024 within about 1–2 m where I could measure:**
  - Displaced-threshold bars: 0.1–0.7 m.
  - Taxiway centreline vs pavement centre: up to 1.35 m on the ways with a tight profile.
  - Hangar outlines vs roof edges: median 0.9 m.
  - Hold bars: 0–0.6 m (G5).
- **This first version of the summary was too kind** *(review)*. It said that "the remaining deviations are missing features, not misplaced ones", but the review found misplaced and wrong features:
  - Taxiway E (OSM way 490634605) lay 3.3 m from its worn centreline paint, and part of F lay 1.5 m from its paint. Both are now fixed by the faint-paint rule.
  - 11 of the 40 NAIP ramp spots sat on road vehicles or bare paint. They were dropped after a by-eye review.
  - Three building outlines are 2–6 m off their roofs, by the same shift in both NAIP years (#15). They are flagged.
  - The missing features remain: 5 wind cones, a painted H circle, a fire-station footprint, unmapped pavement, and parked aircraft without spots. They are listed in section 4, and in `not_yet_sourced` / `not_placed` of the data.

## 2. Images (`docs/phase1/`, JPEG ≤ 2 MB, credit line in each; `docs/phase1/SOURCES.json`)

All 13 were re-rendered from the current build *(review)*. In this pass I looked at `overlay_naip_fbo_ne.jpg`,
`overlay_naip_west_hangars.jpg` and `overlay_naip_green_ramp_tower.jpg` in full, including the credit line. The first
pass looked at `overlay_al5015.jpg`, `overlay_al5015_west.jpg`, `overlay_naip_fbo_south_heli.jpg` and
`overlay_naip_green_ramp_tower.jpg` for the credit line, and at more images for content. The earlier count of "6 of the
13" did not match the list of 9, and is withdrawn.

The legend and the credit sit in a band under each map, so they never cover data. The AL-5015 crops carry the credit and
point to the legend of `overlay_al5015.jpg`. Sizes run from 120 kB to 1.32 MB.

| File | What it shows |
|---|---|
| `overlay_naip.jpg` | The whole data set over NAIP 2024, 0.6 m/px, north up. Taxiways are coloured by ref and labelled; other layers are runways (NASR rectangle, ends, displaced thresholds), taxilanes, aprons, holds, hot spots, hangars (named), buildings, helipads and the windsock. Parking spots are filled when `src` is obs and hollow when it is inf. Dashed white rings mark features that the data set lacks (section 4). |
| `overlay_naip_west_hangars.jpg` | West Hangars (T-rows F–Q, EX1, EX2), the west tie-down apron where AL-5015 prints "FBO RAMP", the 10L run-up and HS 3. 0.3 m/px. |
| `overlay_naip_green_ramp_tower.jpg` | Green Ramp tie-downs (80; heading triangles; span segments), the tower and the terminal building. |
| `overlay_naip_tower_helipads.jpg` | The Helicopter Ramp helipads, the tower and the north edge of the Green Ramp (painted H circle). |
| `overlay_naip_fbo_ne.jpg` | FBO Ramp (north-east): FBO hangars, 56 ramp spots, 3 helipads, the 28R run-up and HS 4. |
| `overlay_naip_east_hangars_runup.jpg` | East Hangars A–E, the 28L run-up and HS 2. |
| `overlay_naip_fbo_south_heli.jpg` | FBO Ramp (south), Signature Aviation, and the unmapped helicopter pads (not placed). |
| `overlay_naip_rwy_10R_10L.jpg`, `overlay_naip_rwy_28L.jpg`, `overlay_naip_rwy_28R.jpg` | The four runway ends, including the 826 ft and 676 ft displaced thresholds, and the HS 5 holds. |
| `overlay_al5015.jpg` (+ `_west`, `_east` crops) | Our data drawn in the frame of AL-5015. The diagram is rasterised at 400 dpi and the overlay goes through the inverse of the similarity fit. Cyan crosses mark the four registration points; the residual table is in the image. |

## 3. Registration of AL-5015

| | 28L | 10R | 28R | 10L |
|---|---|---|---|---|
| Bar end found (px, 400 dpi) | 1840.6, 548.8 | 793.7, 2372.7 | 1307.7, 1107.3 | 734.8, 2101.1 |
| G1's bar end (before the fix) | 1840.9, 548.4 | 793.5, 2373.0 | **1261.4, 1187.6** | 734.5, 2101.6 |
| Similarity residual along / across the runway (m) | −0.21 / +0.27 | +0.10 / −0.47 | +0.39 / −0.54 | −0.29 / +0.74 |
| Affine residual (m), after / before the fix | 0.40 / 15.7 | 0.39 / 15.3 | 0.73 / 31.2 | 0.72 / 30.9 |

How the bar ends are found: walk along each bar's axis. A cross-section counts as bar when at least 90 % of 21 samples
across it are black or hot-spot brown, so the overprinted rings do not end the bar. Gaps of up to 16 px are bridged,
which spans the white dot near the 28L end. The similarity rotation is 89.98°. The fixed affine has singular values of
0.8255 / 0.8242 m/px, i.e. no shear. Two bar-end finders now exist: the plotting tool's, and the fixed one in
`xcheck_osm_faa.py`. They agree to 0.1–0.5 px.

Checks of the registered diagram against our data:
- The diagram's hot-spot ring centres land 0.3–0.4 m from the rebuilt `hotspots`; before the fix they were 12–64 m off. **This is not independent** *(review)*: the data's hot spots are the same ring centres (`al5015.hotspots`) mapped by the affine, so the number only compares the affine with the similarity fit.
- The TWR beacon symbol (star) lies inside the OSM tower footprint, 4.9 m from its centroid.
- The HS 5 holding-position symbols lie 296 ft (Z1) and 304 ft (A1) from the 10R/28L centreline. The NAIP-measured holds are at 299 and 300 ft, a difference of −1.0 / +1.2 m. Along the runway the symbols are 18 m and 6 m from the holds, because the symbol spans the whole taxiway width.
- G1's two "Closed Surface" x rows now lie 0.4 m and 0.2 m (mean) from the OSM abandoned taxiways 1366756208 and 289829582. Before the fix they were 14 m and 57 m away.

## 4. Deviations

Sizes are in metres. "Data" means `data/hwd_airport.json` after the rebuild.

| # | Where (world x, z) | What and size | Seen on | Probable cause | Action |
|---|---|---|---|---|---|
| 1 | AL-5015 bar end 28R | The bar end was found 92.6 px = 76 m short, so the diagram affine was sheared (residuals 15–31 m) | AL-5015 raster | **Bug in our tool**: the 9 px opening in `xcheck_osm_faa.runway_bars` removes the strips that the HS 4 ring leaves | **Fixed** (section 5) |
| 2 | All 6 hot-spot ellipses | They moved 49.3 m (HS 1), 51.3 (HS 2), 55.8 (HS 3), 63.3 (HS 4), 12.2 / 39.7 (HS 5 Z1 / A1). Areas changed −1.6 to −1.7 %. The same taxiways are inside each one (HS 1 A, E; HS 2 A; HS 3 A, F; HS 4 A, B, C; HS 5 A1, Z1) | AL-5015 | Consequence of #1 | **Fixed**; check 7 (CS texts) still passes |
| 3 | Apron 1372203784, beside the tower (3, −484) | Named "FBO Ramp (west)", but no AL-5015 label lies on it. The west "FBO RAMP" text lies 100 % inside apron 1366756195 (West Hangars, OSM name=air), at about (−174, −563) between the west box hangars. That is the tie-down apron with about 15 parked aircraft (G2) | AL-5015 + OSM | Consequence of #1 (the old label point fell inside 1372203784) | **Fixed**: 1372203784 is now unnamed. 1366756195 carries both labels (`al5015_labels_more`). Its ramp spot R082 (one adsb.lol GLEX stay) is now "near hangar 204797798 ramp spot 1" |
| 4 | Green Ramp / Helicopter Ramp boundary (−139, −406) | The GA TRANSIENT RAMP text straddles the Helicopter Ramp (38 % of its text area) and the Green Ramp (36 %) | AL-5015 + OSM | The label is placed in the gap between two aprons (diagram generalisation) | Still matched to the Green Ramp [inf]. The evidence now says it is ambiguous and why |
| 5 | Terminal / Airport Administration | Not placed before. With the fixed registration, the label's leader ends at (26.6, −430.8): 7.3 m from OSM building 1372203791; next nearest are the tower at 16.6 m and building 204802919 at 30.0 m | AL-5015 + OSM | The sheared affine had made this undecidable | **Fixed**: way 1372203791 is now `kind: terminal_admin` with a name [inf]; removed from `not_placed` |
| 6 | Label anchors | They moved 37–169 m. The TWR text now lies 36 m from the tower (was 136 m) | AL-5015 | Consequence of #1 | Fixed. The evidence text now says an anchor is where the text is printed, not the feature |
| 7 | (−410.5, −399.0) near 10L; (−412.0, −253.7) near 10R; (268.5, 95.2) near 28R; (537.5, 440.0) near 28L; (258.5, 280.5) south of 10R/28L | **Five unlit wind cones** (TPP legend symbol "Wind Cone, unlit") on AL-5015. NAIP 2024 shows a small object 1–2 m across, 2.3–6.1 m from each symbol (by eye, 0.1 m resampling). The lit wind cone at the segmented circle is in the data (OSM windsock, 2.5 m from the NAIP object) | AL-5015 + NAIP | OSM omission (OSM maps one windsock) | Not added. Candidates for the data as `obs`. The identity as wind cones rests on the AL-5015 symbol |
| 8 | (−79.0, −412.0), north edge of the Green Ramp, about 115 m west of the tower | A **painted H circle**, about 13.8 m outer diameter (by eye), with a row of painted arcs east of it | NAIP | OSM omission | Not added. It bears on the NASR remark "helipads … at base of ATCT" (G5's open point). Not verified |
| 9 | (298, 584), south-east of the airfield | **Fire station footprint**: AL-5015 draws a FIRE STATION block (about 1,270 m²); NAIP shows a building with solar panels there. The OSM fire-station node (GNIS import) lies 45 m west, at (253, 591), and OSM has no building at the block | AL-5015 + NAIP | OSM: an imported point that is off, and the building is not mapped | Not changed; the data keep the OSM point (`src` obs, point only) |
| 10 | (−2, 472), south-west of Signature Aviation | 25,400 m² of AL-5015 pavement that is not in the data. NAIP shows a weathered paved area with a few dashes and a domed building | AL-5015 + NAIP | OSM omission (no apron mapped); its use is unknown, possibly disused | Not added |
| 11 | (−67, 206) | 3,100 m² of diagram pavement: the unmapped helicopter pads already listed in `not_placed` | AL-5015 + NAIP | OSM omission | Already in `not_placed` |
| 12 | (175, 458) and (−258, 101) | 1,700 m² and 450 m² of diagram pavement: old pavement next to buildings, and a concrete stub off Z | AL-5015 + NAIP | OSM omission | Not added |
| 13 | 13 unnamed OSM taxiway ways | They lie 51–370 m inside the NASR runway rectangles. Twelve are lead-on/lead-off loops that run from a connector onto the centreline and back. Way **58169722** runs along the 10R/28L centreline from the 28L displaced threshold to 12.5 m beyond the 28L end (215 m) | OSM | OSM tagging: the OSM runway way 10R/28L stops at the 28L displaced threshold, and the rest is tagged taxiway | Not changed. **Phase 2 taxi graph:** treat taxiway ways inside a runway polygon as runway |
| 14 | Taxiways vs NAIP pavement | Measurable at 12 ways (pavement cross-profiles every 6 m); 8 have an IQR ≤ 1 m. Offset of the pavement centre from the OSM line: Z 58170277 +0.3 m; A 490634608, E 204801027 +0.15 m; E 204801035, A1 0.0 m; C 204801024 −0.9 m; 204801025 −1.27 m; **D 58170248 −1.35 m**. By eye at (−87, −89), D lies 0.5–1.2 m from the middle of its yellow edge stripes | NAIP | OSM tracing; the grey test also includes shoulders | None: within the tolerance G5 found. **But see #21** *(review)*: one way was 3.3 m off its paint, which a median of medians hid |
| 15 | Hangar / building outlines | *(review: search widened from ±3.9 m to ±8.1 m and done in both NAIP years.)* Shift to the best fit with the NAIP 2024 roof edges, over the 49 outlines not at the search edge (the tower is at the edge): median 0.9 m, p90 4.9 m, max 10.4 m; 8 shift more than 2 m. **3 outlines shift by the same amount in 2022 (within 1 m): Absolute Aero 204800994 (+4.2, −3.6 m; 2022 +5.1, −3.9), Bud Field Aviation 204800996 (+3.0, −0.9; 2022 +3.0, −0.6) and Savage Aviation 204798813 (+1.8, −0.9; 2022 +2.7, −1.2).** The other large shifts (small buildings, the tower) change between the years. The first version's p90 of 1.7 m left out the five outlines that hit its ±3.9 m search edge | NAIP 2024 and 2022 | Stable shifts point to outline offsets in OSM; shifts that change between flights point to roof lean (relief displacement), which is not excluded | Flagged in `crosscheck_metrics.json` (`stable_offset`) as candidates for a manual correction or an OSM note. The data keep the OSM outlines (obs) |
| 16 | Displaced thresholds | The painted threshold bar was measured on NAIP. Its outboard edge lies −0.70 m (10R) and +0.10 m (28L) from the NASR surveyed displaced threshold; bar widths are 3.30 / 3.20 m. AC 150/5340-1M Chg 1 para 2.9.1.3 / 2.9.1.5: the outboard edge is on the threshold, and the bar is 10 ft (3.1 m) wide. That page (PDF p. 54) is now in the committed extract `ac150_5340_1m_chg1_p52-54_63.pdf` *(review)* | NAIP | Agreement | None. AL-5015 does **not** draw either displaced threshold (diagram generalisation) |
| 17 | 28L end of the AL-5015 bar | A white dot 20 px (17 m) inside the bar end, not in the part of the legend I read | AL-5015 | Unknown symbol | None; noted |
| 18 | Parked aircraft without spots | West tie-down apron: about 15 aircraft, 6 spots. North-east strip along the road (x 370–445, z −285 to −200): about 10 aircraft, 2 spots. A jet-sized aircraft at about (−175, −498), 42 m from the nearest spot. A business jet at about (255, 356) on the east edge of FBO Ramp (south), partly outside the OSM apron polygon. All counts and positions by eye | NAIP | Known G5 gap: aircraft parked wing to wing merge into one rejected blob, and blobs larger than 24 m are rejected | Not changed |
| 19 | 28R run-up (982 m²), 28L run-up | NAIP shows a paved pad with a yellow dashed outline, but only 7 % (28R) and 37 % (28L) of the polygon passes the grey test (concrete reads tan) | NAIP | Limitation of the grey test (saturation < 0.16) | Note: this test, used by G5 for spots and here for item 14, under-reports concrete |
| 20 | Green Ramp tie-downs | The spot is the painted tee. Parked aircraft have their wing over the tee or up to about 4 m from it (by eye, 0.1 m resampling of 10 spots) | NAIP | Parking variation | None; app placement uses the spot as the wing / main-gear point (`ref_point: tee_junction`) |
| 21 | Taxiway E, OSM way 490634605 (168 m, north of A) *(review)* | The way lay 3.3 m west of its worn yellow centreline over its whole length (25 faint ridges, median −3.31 m, IQR 0.31 m; the review measured the same in 2022). F 490634609 lay +1.5 m off over its first 145 m. The per-way median of medians hid both | NAIP 2024 (+ 2022, review) | OSM tracing; worn paint below the strong snap thresholds | **Fixed**: faint-paint rule; E moved by up to 3.36 m, F by up to 1.68 m. A per-50 m-section paint check is now hard in `check_airport.py`, with 0 offsets left |
| 22 | NAIP ramp spots *(review)* | 8 of the 40 NAIP-blob ramp spots sat on cars, box trucks, vans or a bus in landside lots inside OSM apron 289829587; 3 sat on bare paint; 1 was a second blob of one aircraft; 4 were centred between two aircraft. They were visible in `overlay_naip_fbo_ne.jpg` (the truck and car lots north of the FBO hangars), which the first pass looked at without seeing them | NAIP 2024 | No vehicle test; one blob was enough for `obs` | **Fixed**: by-eye verdicts recorded in `refs/cache/naip/naip_blob_review.json`; NAIP-only spots are inf until corroborated (`docs/phase1_data_report.md` §2) |

## 5. What I changed (bug fix) and rebuilt

1. `tools/osm/xcheck_osm_faa.py`:
   - New `refine_bar_ends`, the axis walk of section 3.
   - The header documents the fix.
   - The output JSON gains `bar_end_method` and `affine_singular_values_m_per_px`.
   - Re-run: only the `al5015` section of `refs/cache/osm/khwd_osm_xcheck.json` changed. That is the bar ends, the affine and the residuals, and the world positions of the closed-surface rows (their nearest OSM ways are unchanged). The `runways`, `inventory`, `counts` and other sections are identical.
2. `tools/airport/al5015.py`:
   - Every label now carries `boxes_xz`, the world rings of its text.
   - The docstring is updated.
3. `tools/build_airport.py`:
   - The label-to-apron table now identifies each label by its PDF point.
   - Labels without a leader are matched by measured text overlap (asserted at build time).
   - "FBO Ramp (west)" is dropped.
   - The terminal is placed by the leader end (`TERMINAL_TIP_PX`, asserted unambiguous by a factor of 1.5).
   - The residual text comes from the fit instead of the hard-coded "15-31 m".
4. Rebuilt `data/hwd_airport.json` / `.js`:
   - New sha256: json 4f20a5cc…, js 44079032….
   - Counts are unchanged except `not_placed` (4 → 3). Elements: 403 obs / 33 inf.
   - Parking positions and sizes are unchanged. Zone names changed for 16 ramp spots, which renumbered R067–R082. The ids are build-generated and not stable.
5. `tools/check_airport.py`: all hard checks pass. Check 7 (hot spots vs CS texts) is consistent for HS 1–HS 5. 449 elements now (was 450).
6. Reproducibility:
   - A second run from scratch (`__pycache__` deleted; xcheck → build → check) gave byte-identical `khwd_osm_xcheck.json`, json, js and QA plot, and an identical check report.
   - Run in this environment only.
7. `docs/phase1_data_report.md`: the stale passages are updated and marked *(cross-check)*.
8. `docs/ATTRIBUTION.md`: a row for `docs/phase1/*.jpg`.

### Phase 1 review fixes (2026-11-12)

`docs/phase1_data_report.md` §6 lists all 33 findings with their outcome. For this report:
- `plot_overlays.py`:
  - widens the roof-edge search and measures 2022 too (#15);
  - describes the hot-spot comparison as a transform check;
  - commits its metrics, with the ODbL URI, as `docs/phase1/crosscheck_metrics.json`;
  - keeps one world→pixel polynomial per NAIP year (the cache was shared between years).
- Rows #21 and #22 are new.

## 6. Not verified / open

- The wind cones (#7) are identified by the AL-5015 symbol only. NAIP shows small objects but cannot show a cone, and their positions were read by eye.
- The H circle (#8), the unmapped pavement (#10–12) and the parked aircraft (#18) were read by eye. Whether the paved areas are movement areas is unknown.
- GA TRANSIENT RAMP → Green Ramp stays an inference (#4). The city layout map, which PLAN §1 cites as reference only, names "Transient Parking" separately; I did not see it.
- The leaders of the north-east and south FBO RAMP, 28L RUN-UP and TERMINAL labels:
  - The first three were read by eye on the corrected overlay.
  - The terminal leader's end pixel was found as the lowest pixel of its line component. That is a measurement, but the window it was searched in was chosen by eye.
- The taxiway-pavement offsets (#14) cover only 12 of 61 open taxiways. Concrete, junctions and aprons defeat the grey-test profile.
- The roof-edge shifts (#15) were not corrected for relief displacement. I did not have the flight's camera geometry.
- AC 150/5340-1M para 2.9.1.3 / 2.9.1.5 (#16) is on PDF p. 54, which is now in the committed extract *(review)*.
- The overlays use the lossless local NAIP GeoTIFF, `refs/cache/local/naip/naip_2024_hwd_utm10n.tif`, and the 2022 one for #15. Without them the script falls back to the committed JPEGs, so a fresh clone gets numbers that differ slightly. The NAIP licence wording was not re-read (as G5).
- The overlay images were looked at in full and in crops. The credit line was checked on six of the 13 JPEGs. The first pass checked `overlay_al5015.jpg`, `overlay_al5015_west.jpg`, `overlay_naip_fbo_south_heli.jpg` and `overlay_naip_green_ramp_tower.jpg`. The review re-render checked `overlay_naip_fbo_ne.jpg`, `overlay_naip_west_hangars.jpg` and `overlay_naip_green_ramp_tower.jpg` again.
- GA TRANSIENT RAMP → Green Ramp, and therefore "Green Ramp (= AL-5015's GA Transient Ramp)", is an **inference** wherever it appears (#4).
- I made no change to `sfo3d/` or `pc12/`, and nothing for `requests_to_sfo3d.md`: the bar bug is in hwd3d's own G1 tool.
