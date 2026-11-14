# Phase 1: adversarial re-verification of the data (fix round 2)

Date: 2026-11-14. I did not do the fix. My job was to try hard to **reconstruct the features the sensitive filter drops**
(military, armed police, police, prison, GNSS) from the committable files, using every route I could think of. I also
re-checked N2-N5 and the determinism of the builders.

How I worked:
- I used the local raw tiles and `tools/law/osm_sensitive.py` to know what was dropped. My scripts are in
  `tools/verify/reverify_data2/` (README there).
- Per-element logs went to `refs/cache/reverify_data2/` (git-ignored). This includes the search criteria of §6.
- I committed and pushed nothing, downloaded nothing and made no network calls. In the repository I wrote only under
  `sha3d/`: this report, the scripts folder and the local logs. Scratch copies stayed in the session scratchpad.
  Every script ran with `python3 -I`.
- This report gives **counts and descriptions only**. It contains no ids, names, positions, sizes or radial distances of
  dropped features. It also avoids naming which kept classes lie along which dropped feature, because §6 shows that
  such descriptions act as search keys.
- *[Fix round 3, `qa_data.md`: the passages about dropped features are cut further, to counts per class and per rule
  and "exempt / not exempt"; lengths, distances, percentages, test radii and kept classes next to a dropped feature
  are removed (details local only: refs/cache/reverify_data2/).]*

**Committable files tested:**
- 282 files: `git ls-files sha3d`, plus the untracked non-ignored files, plus the 5 files of
  `refs/cache/osm_pinned/`;
- of these, 229 text files, 34 JSON / JS data files and 50 images or rasters.

## 0. Summary

**Can a dropped feature be reconstructed from the committable files?**

| Dropped group | Verdict | Main evidence |
|---|---|---|
| Prison area | **No** | - 0 non-exempt kept features inside it, on it or along it.<br>- The kept features along it are exempt, and they trace it no more than they trace random placements of the same outline.<br>- No hole, no void, no data-file geometry on it. |
| Armed-police area | **Partly, when combined with the documents** (R1; *fixed in fix round 3*) | - The extract alone does not single it out.<br>- The phase-1 documents (before fix round 3) and the committed phase-0 radial distances narrowed it to **2 candidates**. One of them is right.<br>- Exempt kept features trace it above the base rate of random placements; non-exempt kept features do not trace it. |
| 3 military railway lines | **No** (weak residual signal, R2; *fixed in fix round 3*) | - 0 kept railway ways or railway nodes near them, and 0 dangling railway ends near them.<br>- 0 kept railway ways share a node with any dropped railway, including the second-order ones.<br>- Kept linework traces them at or below the base rate, and the corridor test is not significant.<br>- **Residual:** 10 crossing vertices stayed on kept ways. A Hough search ranked one bin on a line first at one window size, but the result depends on its parameters. |
| Police points (13 in the extent) | **No** | - 0 are vertices of kept ways.<br>- 0 kept tagged nodes at their positions.<br>- 0 data-file points near them. |
| GNSS | n/a | 0 in the raw tiles |

**N1-N5 and the builders:**

| Item | Status | Evidence (mine) |
|---|---|---|
| N1 | **fixed**, two low residuals (R2, R3; *fixed in fix round 3*) | My independent derivation finds 30 second-order drops (17 railway points, 13 ways). That equals `pin_summary.json`. All railway and point checks are 0 (§3). |
| N2 | **fixed** | Independent check (`rv2_n2.py`):<br>- 33 ways touched, largest added turn 10.5°, 0 spikes, 0 reversed segments, 0 new segments under 0.5 m;<br>- BN is not moved (0 vertices), and its Umbra residual is 0.25 m by the QA method;<br>- routing is unchanged: departures 150 / 164 at 100° (29 stands fail at 90°), arrivals 164 / 164;<br>- largest raw-segment turn 95.8° on departures and 91.0° on arrivals, 0 over 120°. |
| N3 | **fixed** | - `fix1/aip_check.py` holds no AIP value.<br>- The token scan lists no tool file.<br>- The one new "frequency-like" token, in `qa_data.md`, is a metre value in a runway-end table. |
| N4 | **fixed** (one cosmetic gap, R5) | - All 34 images are listed exactly once in `docs/phase1/SOURCES_*.json`, all with attribution and licence; 30 carry a matching sha256.<br>- 8 / 8 `data/meas/*.json` carry attribution and licence.<br>- The Umbra constant is used by `twy_refit`, `stand_sar`, `stands_plates` and `sar_registration`. B3 still uses +6.1 / −0.9, as the fixer documented. |
| N5 | **fixed** | - The fix-round-1 rows are corrected in place and marked.<br>- The owner README says "a spread sample, not a random one".<br>- The k-fold comment is fixed.<br>- The `observed_elsewhere.md` wording is fixed. |
| Determinism | **pass** | - Two chain runs (16 steps, 0 failures): 88 / 88 outputs md5-identical to each other and to the working tree.<br>- Clean checkout without `refs/cache/aip` and `aip_checks`: the 6 data files are byte-identical, and no `aip_checks` folder is created. |

**New findings**, ranked:
1. **R1 (medium, §6). The documents are a search key.** *[Fixed in fix round 3, `qa_data.md`.]* Three uncommitted
   phase-1 documents described what lies next to each dropped feature: which kept classes run along it, with lengths,
   distances, percentages, a perimeter and node counts. The documents are `airport.md`, `qa_data.md` and
   `reverify_data.md`.
   - Combined with the radial distances from the ARP in the pushed phase-0 documents (`law.md`,
     `verify_licences_law.md` item 5), these descriptions locate the armed-police area to one of 2 places (§6).
   - Once it is located, exempt kept features give part of its outline. The outline was drawn on exempt features, so
     dropping the area cannot hide that part.
   - **Fix, before commit:** in those three files, reduce every passage about the surroundings of a dropped feature to
     counts per rule and per "exempt / not exempt", and drop all lengths, distances, percentages, perimeters and node
     counts. Do not repeat the radial distances in new documents.
   - The phase-0 radial distances are already pushed (commit `bc21d7e`; PLAN §6b: no history rewrite). That is the
     owner's call. Without the phase-1 descriptions, the radial band alone leaves 4 candidate places. *[Fix round 3:
     the working copies of `law.md` and `verify_licences_law.md` no longer carry them; git history still does.]*
2. **R2 (low, §7). Crossing vertices.** *[Fixed in fix round 3: rule (g) of `pin_extract.py`.]*
   - The 10 kept ways that crossed a dropped line keep their crossing vertex. All 10 are "unexplained" vertices: in
     one way only, no turn, not an end. 5 of them are exactly collinear with their neighbours.
   - Among the 1,252 unexplained vertices of the test population they do not stand out one by one. But a Hough
     search at one window size puts a bin through 4 of them **first, alone** (6 distinct ways, 4 of them on a line).
   - The signal is fragile: at a smaller window that bin ties with 8 chance bins, and with other vertex filters no
     line bin ranks at all.
   - **Fix option:** drop those 10 vertices from the kept geometry and leave them out of `osm_elements.json`. The ways
     would barely move (5 of them not at all). Otherwise accept the risk and note it.
3. **R3 (low).** *[Fixed in fix round 3.]* `osm_elements.json` lists 13 node ids that are second-order dropped railway
   points. They are kept because they are vertices of kept ways. Nothing in our files marks them, so only an OSM
   lookup identifies them, and OSM shows the line anyway. Fixing R2 removes them.
4. **R4 (info).** Existence and class are disclosed by design. `pin_summary.json`,
   `sha_airport.json` `checks_at_build.sensitive_filter`, the pinned `SOURCES.json` and the documents give counts per
   class and per rule. These show that the extent holds a prison area, an armed-police area, three military railway
   lines and police cameras. With the phase-0 radial distances, this gives an annulus, not a place.
5. **R5 (low).** *[Fixed in fix round 3.]* The 4 `sources_sim_*.png` entries in `SOURCES_sim.json` (task B2's format)
   have no sha256. Every other image entry matches.

## 1. What is dropped (`rv2_inventory.py`)

| | Count | Notes |
|---|---|---|
| Tag rule, raw tiles | 27 | 22 police nodes (13 inside the extent, nearly all surveillance cameras), 3 military-usage railway lines, 1 armed-police area, 1 prison area. 0 relations, 0 GNSS. |
| Second order, derived by me | 30 | 17 railway points and 13 ways; per rule as in `pin_summary.json`: inside a dropped area 1, along one 4, on a dropped line 1, along one 3, railway points 14 + 3, non-passenger railway 2 + 2. **This equals `pin_summary.json`.** |

## 2. Text: names, ids, tags (`rv2_names.py`)

| Test | Result |
|---|---|
| Dropped ids (tag rule) in any committable file | 0 |
| Ids of the nodes that belong only to dropped ways | 0 |
| Second-order ids | 13 node ids in `osm_elements.json`, listed as plain vertices of kept ways (R3; *0 since fix round 3*). 0 way ids. |
| Names and distinctive name parts of dropped features, in kept tag values and in all committable text files | - **Tag-rule drops:** 1 hit in a kept tag value, judged **not a leak** (details local only: refs/cache/reverify_data2/names_local.json).<br>- **Second-order drops:** 0. |
| Sensitive regexes of the tag rule on every kept tag value (all keys, linear features and relations included) | 0 |
| Broad keyword scan (border, immigration, radar, security and so on) | Only an inspection and quarantine office (civil) and 6 `type=road_border` relations. No missed sensitive feature. |
| Kept relations whose raw member list holds a dropped element | 0. Members of kept relations that are dropped: 0. |
| Speed cameras, enforcement relations, `surveillance:*` / `camera:*` keys without `man_made=surveillance` | 0 |

## 3. Geometry of the pinned extract (`rv2_geom.py`, `rv2_geom2.py`)

"Exempt" means the classes the filter keeps on purpose:
- for areas: public roads, railways, waterways and the aerodrome boundary;
- for lines: waterways, passenger railways and the aerodrome boundary.

**Trace** is the share of the dropped outline or line that has kept linework within D m running within 30° of its
direction. It is compared with 40 random placements of the same shape inside the extent. Exact values are printed by
the scripts and kept off this page.

| Test | Prison area | Armed-police area | Military railway lines | Police points |
|---|---|---|---|---|
| Kept features close to it | All exempt | All exempt | The non-exempt ones cross the lines; none runs along them | n/a (points cannot be traced by passing features) |
| Kept features with a part inside | 0 | Exempt ones only | n/a | n/a |
| Parallel kept features in a band wider than the filter's (rules c, d) | All exempt | The non-exempt ones lie outside the filter band | None of the non-exempt ones meets rule (d) | n/a |
| Trace against the random placements | Within the base-rate range; non-exempt linework: negligible | **Above the base rate**, by exempt features only; non-exempt: none | At or below the base rate | n/a |
| Shared nodes | None | With exempt features only | 10 crossing vertices on kept ways (R2; *0 since fix round 3*) | 0 vertices of kept ways; 0 kept tagged nodes at their positions |
| Holes and voids | No gap has the area's shape; no kept interior ring meets it; the filter makes no void | Same: no ring, no shaped gap, no filter-made void | Corridor between kept polygons, against 60 random placements: **not significant** | n/a |
| Dangling ends near it | 1, which does not run along the outline | 0 | 0 | 0 |
| Railway remnants | n/a | n/a | - 0 kept railway ways or nodes near them.<br>- 0 dangling railway ends near them.<br>- 0 kept railway ways share a node with a dropped railway (tag rule or second order).<br>- 0 `landuse=railway` near them. | n/a |
| Bridges / tunnels over the line | n/a | n/a | **No kept bridge or tunnel over "nothing".** | n/a |

**Holes left by the second-order drops.** For each of the 5 dropped second-order polygons, kept polygons trace only part
of its outline, and no hole of its shape remains.

## 4. Data files (`rv2_data.py`)

I walked 34 JSON / JS files outside the pinned extract: `data/`, `data/meas/`, `docs/` and the tracked cache JSON. That
gave 5,714 points and 12,136 polylines. The taxi-graph turn table holds link-id pairs, not coordinates, so I skipped
it. The 3 `.js` files carry the same object as their `.json` twins.

| Group | Data points on it (rule b / d distance) | Polylines along it (rule c / d test) |
|---|---|---|
| Prison area | 0 | 0 |
| Armed-police area | 0 | 2, exempt |
| Military railway lines | 0 | 1, exempt |
| Police points | 0 | n/a |

`context.rail` has 0 polylines along a dropped line (details local only: refs/cache/reverify_data2/).

## 5. Images

**What the generators read:**
- The plate generators read the data files only. `overlay.py` also reads the pinned taxiways.
- Phase 0's `geo_overlay.py` drew aeroway features only.
- So no plate can draw a dropped feature unless the data files hold it, and §3-§4 show they do not.

**What I looked at:**
- `airport_overlay.jpg` at full resolution, around all four groups. It draws canals, roads, buildings, the aerodrome
  boundary and the extent, and no outline, line or label of a dropped feature.
- `stands_overlay.jpg`, `taxigraph.png`, the QA plates, the bridge sheets, the height plates and the contact sheet.
  These are airport crops or charts.

**Imagery** shows the ground without labels, as PLAN §6b Q6 allows: the Sentinel-2 rasters (tracked), the Umbra
crops and the Commons aerial photos.

## 6. Search-key test: documents plus extract (`rv2_fingerprint.py`)

An adversary who reads only committable files has three inputs:
- the ARP text in `sha_airport.json`;
- the radial distances in the pushed phase-0 document;
- what the phase-1 documents say about the kept features next to a dropped feature.

The search walks a kept reference line in fixed steps. The criteria and the line live in a git-ignored local file,
so the script does not restate them.

| Search | Candidate clusters | One of them is right |
|---|---|---|
| Areas: radial band only | 4 | yes |
| Areas: radial band + the documented neighbours | **2** | **yes** |
| Lines: radial band only | 3 | yes |
| Lines: radial band + crossing-vertex density | 3 | yes (no narrowing) |

Status: R1. The descriptions in the uncommitted documents turn a weak annulus into 2 candidates for the armed-police
area. For the lines and the prison, the documents give no useful key; the prison has no radial distance in any
document. *[Fix round 3: re-run on the cut documents, see `qa_data.md`.]*

## 7. Crossing vertices (`rv2_geom.py` T9, `rv2_geom2.py` U6)

| Test | Result |
|---|---|
| Kept way mid-vertices on a dropped line | 10, all unexplained: one way, no turn (*0 since fix round 3*) |
| Unexplained vertices in the extent (the test population of T9 / U6) | 1,252. Of the 172 that are exactly collinear, 5 are on a line (*0 since fix round 3*). |
| Hough bins (voted by distinct ways crossing at ≥ 30°), whole extent | The line bin is not distinguished. |
| Same, the largest window tested | **The best bin is unique (6 ways) and 4 of its votes are on a line** |
| Same, the two smaller windows | The line bin ties with 8 chance bins / 3 bins score higher |
| Same, other vertex filters (scratch probe) | No line bin with ≥ 3 votes / no line bin with ≥ 3 votes / more than 100 bins rank above the line bin |
| Moving the way if the vertex is dropped | barely (5 of 10: not at all) |

Status: R2, low. Only a dedicated statistical search with tuned parameters finds the signal. The fix option is cheap.
*[Fixed in fix round 3.]*

## 8. N2-N5 details

**N2:**
- `twy_refit.json` lists 144 vertex moves: 35 run vertices and 109 taper vertices. The data matches: 33 ways touched.
- The QA method finds 25 runs, |offset| median 1.25 m, p90 3.75 m. 4 runs are ≥ 3.5 m: T1, T6, B and the A1 tail, as
  the fixer reported.
- H2: 0.5 m. A2's second run, A3 and H1 sit at 3.0 m.

**N3 and N4:** see §0.

**N5:** all three statements are corrected. The research items match `reverify_research.md` §6.

**Note for B3:** the remaining Umbra offset in `umbra_layover.py` and `umbra_crops.py` (+6.1 / −0.9) is documented in
`b3_umbra_layover.json` and in `standards_refs.md`.

## 9. Determinism and clean checkout

| Test | Result |
|---|---|
| Chain run (`tools/verify/reverify_data/chain.sh`) on two scratch copies | 16 steps each, 0 failures |
| Outputs (`md5set.sh`) | 88 / 88 md5-identical between the runs, and identical to the working tree |
| Clean checkout (`refs/cache/aip` and `aip_checks` removed), then `build_airport`, `build_stands`, `build_taxigraph` | 6 / 6 data files byte-identical; no `aip_checks` folder created |

## 10. Files

- **Scripts:** `tools/verify/reverify_data2/`: 9 Python scripts and a README. They print counts only.
- **Local logs (git-ignored):** `refs/cache/reverify_data2/`. They hold the per-element details and the search
  criteria of §6.
- **Scratch:** the chain copies and the QA script copies stayed in the session scratchpad.
