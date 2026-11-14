# Phase 1: re-verification of the data fixes (QA C1, fix round 1)

Date: 2026-11-14. I re-verified the 16 QA C1 findings in `qa_data.md` against the fixer's "Fix round 1" table. I did not
build the data and did not fix anything. I used my own scripts (`tools/verify/reverify_data/`, README there) and
scratch copies of the QA scripts in `tools/verify/qa_c1/`. The QA plate outputs went to the scratchpad, not to
`docs/phase1/qa/`.

How I worked:
- I committed and pushed nothing, and I changed nothing in `sfo3d/`, `pc12/` or `hwd3d/`. The only files written are
  this report and the scripts folder.
- I downloaded nothing and called neither api.adsb.lol nor OpenSky. Every script that reads cached downloads ran with
  `python3 -I`.
- The report gives counts only. It contains no dropped-element ids, names or positions, no AIP values and no
  per-flight data.

**Committable files:**
- 250 files: `git ls-files sha3d` plus the untracked, non-ignored files;
- plus the 5 files of the pinned extract (`refs/cache/osm_pinned/`).

**Status values used below:**
- **fixed**: the finding no longer holds on my checks.
- **partly**: the main defect is gone, but a stated part remains or a new side effect appeared.
- **not fixed**: the finding still holds.
- **regressed**: a check that passed in QA C1 §9 now fails.

## 0. Summary

| # | Status | Evidence (mine) |
|---|---|---|
| H1 | **fixed** | **The non-exempt feature on the outline:** dropped. Kept features inside or along the dropped area outlines: exempt only.<br>**Ids and orphan nodes:** 0 dropped ids listed; 0 orphan outline nodes kept. |
| H2 | **partly** | **Runway use, turns, crossings:** with my own geometric turn rule, 0 routes use a runway link and 0 cross off the AIP list. The largest turn is 93.2° (0 over 100°).<br>**Reachability:** 164 / 164 stands are reached from all 4 landing directions.<br>**Not fixed:** 14 stands cannot depart to any runway end. QA §9 passed this check without rules (§3). |
| M1 | **partly** | **Fixed:** A1, H2 and H4 now sit on the Umbra pavement centre (residual 0.5 to 1.25 m).<br>**Still off on Umbra:** A2's second run (3.0 m) and B (3.1 to 3.5 m, the same sign in both methods). BN moved away from the Umbra centre: 3.25 m after the move, against about 0.6 m before.<br>**New:** the moves left a 0.3 m backward spike (169.7°) on H1. |
| M2 | **partly** | **Fixed:** the runway values sit in two `aip_facts` blocks. No removed value remains in the data or the generators.<br>**Still outside the blocks** (labelled "AIP (mirror)" and covered by the new licence sentence): aerodrome facts, obstacle rows, a quote, the `profile_y` elevations and the 12 unplaced names.<br>**Stand list:** PLAN.md §1 plus `sha_stands.json` still rebuild the AIP stand list.<br>**New:** `fix1/aip_check.py` contains 8 of the removed values as literals. |
| M3 | **fixed** | **Bridges:** 56 bridges, 0 stands with two, 0 shared rotundas. Every T1 reach is ≤ 40.0 m. One bridge is over 50 m (240, flagged).<br>**112:** `unclear`, with an inferred bridge.<br>**Null:** terminal-adjacent, n = 314, p95 1.887. Layover and shadow are recorded per face. |
| M4 | **partly** | **Fixed:** with `span_max`, 0 class-max overlaps, and every stand has a `span_max`. The west remote apron has 0 stands above the AIP class (local count).<br>**Still open:** 101 is still 2+ classes above the AIP class. 14 stands are narrow where the AIP allows wide-bodies (was 5). For 12 stands, `span_max` is below their class's reference span. |
| M5 | **fixed** | 164 / 164 pushes are the reversed own lead-in. Median 81.3 m, 3 over 150 m. 401-413 and 601-608 push 78-108 m to an apron lane. The cap is a flag, not a cut; the fixer documented this deviation. |
| M6 | **fixed** | 165 own lead-in links (164 stands, `obs`). 732 apron lanes are `taxilane` / `inf`. The turn table has 0 push-end transitions into a stand lead-in. |
| M7 | **fixed** | Every `src` is `obs` or `inf`, and every record with a `src` has evidence, refs or a rule. Exceptions: the 10 `not_yet_sourced` placeholders, and `aprons` (bare rings described by `aprons_src`). |
| M8 | **fixed** | 12 rasters, 23.54 km² of valid pixels, 0 valid pixels outside the polygon. Bounds are within 1 pixel of the extent bbox. |
| L1 | **fixed** | 15 data plates are listed with matching sha256. New: the 8 QA plates in `docs/phase1/qa/` are in no SOURCES file. |
| L2 | **partly** | **Fixed:** the data files, the JS headers and `stand_sar.json` carry the full licence and attribution.<br>**Missing:** `data/meas/rwy_ends.json` and `twy_refit.json` have no attribution block (`twy_refit.json` names Umbra without the licence URL). |
| L3 | **fixed** | `frame.py` and `airport.md` say 11.16-11.35 m. `geoid_qa.py` measures 11.163-11.350 m. |
| L4 | **fixed** | The non-circular metric is reported. 608: 11.5 % in the data, 11.9 % on my own union. |
| L5 | **fixed** | Repeated chain runs: md5-identical. A clean checkout without the AIP mirror: the 6 data files are byte-identical (§1). |
| L6 | **fixed** | `nose_note` is present (`inf`). |

**New problems**, ranked (details in the sections named):
1. **N1 (high, §2).** The dropped military railway lines can still be traced in the pinned extract and in
   `sha_airport.json`:
   - 14 kept railway point features lie on them;
   - 1 kept non-passenger railway way runs along one line (the railway exemption kept it).
   This dates from before the fix. QA H1 and the fix covered dropped areas only.
2. **H2 (regressed reachability, §3).** 14 T2 stands cannot depart at all under the new rules. The fixer reported this
   as open. With a strict 90° rule (no 10° tolerance), 29 stands cannot depart.
3. **N2 (low-medium, §4).** Re-fit side effects:
   - a 0.3 m out-and-back spike (169.7°) on H1, link 706;
   - 20-39° added kinks on 13 ways next to moved junctions, most of them short fillet ways;
   - BN moved by S2 alone, against Umbra.
4. **N3 (low, §5).** `tools/verify/qa_c1/fix1/aip_check.py` (committable) contains 8 removed AIP AD 2.12 / 2.14
   values as literal search patterns: strip, RESA, SWY and CWY dimensions, MEHT, TDZ and the slope lengths.
5. **N4 (low).**
   - The 8 QA plates have no SOURCES entry.
   - `rwy_ends.json` and `twy_refit.json` have no attribution block.
   - The Umbra registration differs between tools: `stand_sar` +3.4 E, `twy_refit` +3.07 E, `b3_umbra_layover`
     +6.1 / −0.9 (the last one is already noted by the fixer).
6. **N5 (low).** Three statements in the fixer's table do not match my checks:
   - "B opposite sign between methods": the sign is the same in both methods, about 3.1-3.5 m east (§4).
   - "0 kept features along the outline" (H1): this holds only for features that intersect the polygon. 1 exempt kept
     feature runs along it outside (details local only: refs/cache/reverify_data2/).
   - "Each [of the 14 stands] needs one short lane": 227 and 238A need two.

## 1. Determinism and clean checkout (obs)

| Test | Result |
|---|---|
| Whole chain re-run on a scratch copy (16 steps, as in "Fix round 1", `chain.sh`) | 52 outputs regenerated. Compared with the committed versions, all **85** chain outputs are md5-identical: `data/*`, `data/meas/*`, pinned extract, S2 rasters, `s2_precut`, `aip_checks`, plates and SOURCES files. |
| Second run on the same copy | 85 / 85 md5-identical to the first run |
| Clean checkout (`refs/cache/aip` and `aip_checks` removed), then `build_airport`, `build_stands`, `build_taxigraph` | 6 / 6 `.json` / `.js` files byte-identical to the committed ones; no `aip_checks` folder created |

## 2. Sensitive scan (H1 and the new N1)

**Tag rule:** I applied `tools/law/osm_sensitive.py` to the raw tiles: nodes, ways and relations (`rv_sens.py`).
- 32 elements are dropped: 22 police nodes, 3 military-usage railway lines, 1 armed-police area and 1 prison area. No
  relation is dropped.
- None of their ids is in `osm_elements.json`.
- 0 listed nodes belong only to dropped features.
- 0 kept features match the tag rule or have a sensitive name.

**Kept features near dropped geometry** (pinned extract, world metres; I counted any feature with ≥ 10 m within 5 m,
≥ 25 m within 10 m, or > 50 % inside):

| Dropped geometry | Kept features near it | Assessment |
|---|---|---|
| 2 dropped areas (prison, armed police) | All exempt; 0 non-exempt | Exempt. **H1 is fixed:** the non-exempt feature is gone. |
| 3 military railway lines | **14 railway point features on the lines.**<br>**1 kept non-passenger railway way** along one line.<br>**Some vertices of the lines are kept** as vertices of other kept ways (details local only: refs/cache/reverify_data2/). | **N1: not caught.** `pin_extract.py` builds its inside / along rules only from dropped areas, and the railway exemption keeps the railway way. |

**N1 in the data files:**
- `sha_airport.json` `context.rail` carries the same railway way (`rv_sens3.py`).
- No stand or taxi-graph geometry runs along any dropped geometry.

**Proposed fix for N1** in `pin_extract.py`:
- treat dropped lines as sensitive geometry too;
- drop the point features within 2 m of a dropped line, or strip their `railway=*` tags and keep the vertex;
- drop railway features (spur, siding, yard) with ≥ 25 m within 10 m of a dropped line, with no public-railway
  exemption for `service=*` tracks;
- then re-run the chain.

**Keyword and per-flight scan** (`rv_kw.py`, all committable files):
- In the data files and the pinned extract, the only hits are the counts-only filter notes.
- 0 registrations, callsigns or ICAO hex codes appear in any data file or in the pinned extract.

## 3. Taxi graph (H2, M5, M6)

**My router** (`rv_route.py`) is edge-based. Its transitions are computed from the link geometry and do **not** use the
committed `turns` table:
- turn ≤ θ, measured on a 15 m chord;
- one-way respected;
- `use` respected, and `runway` links never used;
- own lead-ins only for their own stand;
- push only as the first leg;
- a pass through a runway node is allowed only on that runway's AIP crossing taxiways.

| Check | Result |
|---|---|
| Turn table against my rule (θ = 100°) | Identical. The 6 pairs that only the table has lie on `construction` links, which routing filters out. |
| Turn table content | 5,785 pairs:<br>- 0 with a turn over 100°, 331 between 90° and 100°;<br>- 206 involve `runway` links (allowed only for a backtrack, kept off taxi routing by `use`);<br>- 20 crossings, all on the AIP list;<br>- 0 push-end transitions into a stand lead-in;<br>- 0 one-way violations. |
| Rapid exits | All 18 runway-side `for_landing` links (and 34 chain links) open towards their landing direction (< 45°). They are one-way `arrival`. |
| Routes, θ = 100° (builder tolerance) | Departures 600 / 656, arrivals 656 / 656:<br>- 0 use a runway link, 0 cross off the AIP list, 0 use another stand's lead-in;<br>- largest turn 93.2° (15 m chord): 70 departure and 42 arrival routes have a turn between 90° and 93.2°;<br>- largest contiguous length inside a runway outline, first and last link excluded: 30 m (departures) and 55 m (arrivals), i.e. crossings only. **No taxiing along runways.** |
| Committed table used for routing | Same counts as my rule |
| Reachability, θ = 100° | Arrivals: 164 / 164 from all 4 landing ends.<br>Departures: **150 / 164** to all 4 take-off ends.<br>The other **14 reach no end**: 218, 219, 225, 226, 227, 238A, 239, 240, 240A, 271, 272, 278, 279, 280. |
| Reachability, θ = 90° (strict AIP) | **29 stands cannot depart.** |
| Cause of the 14 | All 57 one-way apron lanes are OSM `oneway=yes` (`obs`). Ignoring their direction gives all 14 four take-off ends.<br>- 12 of the 14 are each freed by one lane of 5.9-10.8 m.<br>- 227 and 238A need two lanes (5.9 + 24.4 m and 8.1 + 39.1 m), or a turn of 113° / 101.6°. |
| Raw-segment turns | QA metric with 0.5 m segments ignored: 0 reversals. On raw segments, 46-48 routes show 169.7° from one 0.3 m spike on H1 (link 706, §4). |
| M5 push | 164 / 164 push links equal the reversed own lead-in link and end at the graph junction where it ends. `graph_qa4.py`: chord-to-lead-in deviation 0 m, axis deviation 0°. `push_conf.py`: 0 pushes cross another stand's reference planform. On class-max planforms, only the alternative pairs cross (238/238A, 240/240A, 259/259A, 604/604B). |
| M6 | 165 own lead-in links (164 stands, `obs`, tagged with their stand); 732 apron lanes `taxilane` / `inf` with their OSM way as evidence |
| Graph integrity (`graph_qa.py`, patched for `use: stand`) | Unique ids; 0 point / length mismatches; 0 links < 0.5 m; 0 node pairs < 0.5 m; 10 dead ends (as in QA); node-based 164 / 164 depart and arrive |

**Status of H2: partly.**
- The runway, reversal and lead-in defects are fixed, and the rule is now in the data.
- The rule leaves 14 stands without any departure, which is a regression of the QA §9 reachability check. The fixer
  reported it and Phase 3 has to decide. The two options are a push that continues along the lane, or a soft one-way
  rule on apron lanes.
- The 10° tolerance is a documented deviation from the AIP's 90°.

## 4. Taxiway re-fit (M1)

- **Registration:** my re-run of the QA method (`umb_reg.py`) gives **+2.99 m E**; the tool uses +3.07 m E. They agree.
- **Pavement** (`twy_pave.py`): 0 of 305 centrelines run ≥ 20 m on grass or ≥ 30 m on S2 vegetation, and 0 cross a
  building.
- **Runway nodes:** all 40 lie within 0.09 m of their centreline.
- **Overall offsets** (`twy_offset.py`, QA method, Umbra +3.0 E): 24 runs measured; |offset| median 1.25 m, p90 3.42 m.
  Three runs are ≥ 3.5 m: T1 (82 m long), T6 (flagged `single_source`) and B.

| Run | Fixer's move | Umbra residual after the move (QA method) | Assessment |
|---|---|---|---|
| A1 (295 m) | +7.65 | −0.75 (was +6.75) | fixed |
| H2 | +3.54 | 0.5 | fixed |
| H4 (144 m) | +4.67 | 1.25 | fixed |
| A2 run 1 / run 2 | +6.66 / +3.82 | 1.0 / **3.0** | Run 2 is still 3 m off on Umbra (flagged `dissent`) |
| BN (366 m) | −3.72 (S2B + S2C) | **3.25 m** from the band centre (about 0.6 m before) | Moved away from Umbra. On the plate the green line sits left of the dark band. Flagged `dissent`. |
| B (3,199 m) | not moved: fixer +3.12 E (3 sources) | 3.5 m east of the line | **Same sign in both methods** (the fixer's note says the opposite). At the threshold; left as OSM. |
| N (last run) | +7.01 (S2B + S2C, no Umbra coverage) | — | S2 only. On the plate there is a jog where the moved run meets the unmoved one. |

- **N2 (re-fit side effects)** (`rv_route_dbg.py`, vertex turns compared with the OSM ways):
  - H1 (way 467403670) now has a **0.3 m out-and-back spike, a 169.7° reversal, at vertex 18**. The vertex was dragged
    3.72 m by the BN move through the shared B / BN junction. OSM has 0.1° there. In the graph, link 706 starts with
    it. Routing is not affected (15 m chord), but a renderer or taxi physics that follows `pts` would be.
  - 13 ways gain 20-39° kinks at moved junction vertices. Most are short fillet / connector ways with 5-14 m
    segments; H2 and H4 are among them.
  - Suggested fix:
    - do not move a shared vertex past its neighbour (or drop the vertex);
    - limit moves of junction vertices to the moved run's normal;
    - smooth the 2-3 neighbouring vertices.
- **Status of M1: partly.**
  - The registration is fixed, and A1, H2 and H4 are fixed.
  - A2's second run and B stay about 3 m off.
  - BN's S2-only move goes against the sharper Umbra. I recommend leaving BN at OSM until a better image settles it.

## 5. AIP content (M2, OD3)

**Runway blocks.** Each runway has one `aip_facts` block with the notice: 2 blocks in `sha_airport.json`, 1 in
`sha_stands.json`, plus `rules` in `sha_taxigraph.json`.

**Token scan** of the committable files, outside these blocks, against the mirror's distinctive tokens (`rv_aip_tokens.py`):

| Where | Hits |
|---|---|
| The 6 data files | 0 dimensions, PCR codes, coordinates, slopes, bearings, TDZ or TL/TA values. The "frequency-like" hits are metre coordinates: 0 inside strings. |
| `build_airport.py` and `airport.md` | Only the kept runway dimensions |
| `fix1/aip_check.py` | **8 removed AD 2.12 / 2.14 values written as search patterns: N3.** Fix: read the patterns from the local mirror at run time, or compare hashes. |
| Phase-0 docs (`aip.md`, `verify_official.md`, `PLAN.md`) | Pre-existing short facts, already in history; outside this data re-verify |

**Still outside the blocks.** Each item below is labelled "AIP (mirror)". The new licence sentence covers it ("the
aip_facts blocks and the other values labelled AIP (mirror) ... are not covered by the ODbL"):
- `aerodrome`: elevation, ARP text, magnetic variation;
- the control tower: AIP elevation, bearing and distance;
- 4 glide-path antennas: AIP obstacle bearing, distance and elevation in `evidence`;
- 5 obstacle rows in `checks_at_build` and 4 in `context.buildings[].aip_obstacle_match`: type and elevation;
- the runway-separation quote in `checks_at_build.runways`;
- `runways[].profile_y`, which repeats the THR / DTHR elevations of `aip_facts`;
- the 12 `unplaced` stand designators.

QA C1 rated the obstacle use acceptable. Strictly, though, the AIP content is **not** confined to the `aip_facts` blocks.

**Stand list:**
- No stand record carries an AIP field, and `sha_stands.json` alone does not show which 15 OSM names are missing from
  the AIP.
- `PLAN.md` §1, already committed, names those 15 as ranges, and with `sha_stands.json` that rebuilds the 161-name AIP
  list. The fixer flagged this as the lead's or the owner's call.

## 6. Stands (M3, M4, L4, L6) and the QA §9 stand checks

| Check (`rv_stands.py`, `rv_stands2.py`, `stand_qa.py`, `stand_pave.py`) | Result |
|---|---|
| Nose vs OSM ref node / heading vs OSM final lead-in segment | Max 7 mm / 0.005° (164 / 164). No regression from the re-fit. |
| Planform overlaps, reference size (outside the excluded and alternative pairs) | 0. There are 10 pairs closer than 2.5 m, among them 301-312. |
| Class-max planforms with `span_max` | 0 overlaps; 1 pair at 2.49 m (220/221) |
| Class-max planforms without `span_max` | 5 overlaps, at the business stands 301-312. **The app must honour `span_max`.** |
| `span_max` | Present on 164 / 164. None is below the next lower class's maximum, but 12 are below the stand's class reference span (that class's reference type does not fit). |
| Planforms within 3 m of an OSM building | 0 |
| Classes | C 101, B 27, EL 23, E 11, D 2; 25 `obs` |
| Against the AIP (mirror), local counts, reference-span mapping | - Wide / narrow agreement 134 / 149.<br>- 14 stands narrow where the AIP allows wide-bodies.<br>- 1 stand 2+ classes above the AIP (101).<br>- West remote apron: 0 above the AIP (11 same, 2 below).<br>- Exact class: 104 by my mapping, 107 by the builder's; the difference comes from how a limit is mapped to a class. |
| Bridges (M3) | 56 bridges (42 `inf`, 14 `obs`); 0 stands with two; 0 rotundas shared or < 8 m apart. Reach median 33.4 m; T1 max 40.0 m; > 45 m: 240 (52.5) and 266 (48.4), both flagged. The 240 bridge crosses 240A's planform, an alternative pair. |
| Bridge status (local counts) | 54 / 54 VDGS stands are contact stands (40 unclear, 13 present, 1 retracted). 112: `unclear`, contact, `inf` bridge. |
| SAR null | n 314 terminal-adjacent pseudo-stands (only 4 and 9 on the two T1 faces), p95 1.887. The former remote null is kept as `null_remote`. Layover and shadow are recorded in `faces`. |
| Pavement without lead-in buffers (L4) | 608 at 11.5 % (data) / 11.9 % (my union); every other stand ≤ 3.5 % |

**Status of M4: partly.** The overlaps and the west-apron over-classing are fixed. Three points remain:
- 101 is still 2+ classes above the AIP class;
- the classes now err on the narrow side at 14 stands;
- the S2 evidence is still blind at T1 (a limit of the method).

## 7. QA §9 checks that passed before: regression scan

| Check | Now |
|---|---|
| Frame, origin, PROJ, geoid (`frame_qa.py`, `geoid_qa.py`) | Pass. Same numbers; the geoid ring range is now 11.163-11.350 m. |
| Every data coordinate inside the extent (`extent_qa.py`) | Pass. The 1,120 "outside" points are `turns` link-id pairs that the generic scanner reads as coordinates (the fixer noted this). |
| Sensitive filter (`sens_qa.py`) | Pass on the tag rule. **N1** (lines) is new. |
| Runway ends | Unchanged (`rwy_ends.json` is byte-identical on re-run) |
| Taxiways on pavement | Pass (§4) |
| Stand position, heading, planforms, buildings | Pass (§6) |
| Graph integrity and geometry (`graph_qa.py`, `graph_geo.py`, `push_conf.py`) | Pass |
| Graph reachability | Node-based: pass. **Under the new rules: 150 / 164 departures** (§3). |
| Reproducibility | Pass (§1) |

## 8. Plates I looked at

| Plate | What I saw |
|---|---|
| `airport_overlay.jpg` | The imagery is masked outside the extent, and the legend says so |
| `taxigraph.png` | Runways in red (not for taxiing), one-way rapid exits with arrows, the ROUTE-N/S and M/Y one-way taxiways. The title shows "150 / 164 depart". |
| `airport_twy_checks.jpg` (all panels) | **A1, A2 and H2:** the green re-fitted lines sit on the band centre on Umbra (A2 has a bend at the runway end).<br>**BN:** the line sits left of the Umbra band.<br>**N:** outside Umbra coverage, with a jog at the run boundary.<br>**H7 and the unnamed taxiway:** plausible. |
| `stands_overlay.jpg` | Classes, bridges and pushes as in the data |
| `bridges_sar_t1_north.jpg` | The T1 north face: structures reach out from the facade, consistent with the fixed-link rotundas |

## 9. Files

- **Scripts:** `tools/verify/reverify_data/`: 15 Python scripts, `chain.sh`, `md5set.sh` and a README. Run them from a
  scratch directory with `python3 -I`. They print counts only.
- **Scratch:** the chain re-runs, the QA script copies and their plates stayed in the session scratchpad.
