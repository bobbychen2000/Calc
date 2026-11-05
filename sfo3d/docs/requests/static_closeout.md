# Static track close-out (review 2026-11-04): requests to the other tracks

From: owner of the static data (`data/sfo_*`, `tools/stands/**`, `tools/build_*.py`, `tools/sat/**`, `tools/imagery/**`,
`tools/xcheck/**`, `js/geo.js`, `js/live/airport.js` standGates / landside, `docs/ATTRIBUTION.md`). What changed and why:
`docs/research/stands_rebuild.md` §16. Nothing here is committed by me.

## 0. What every consumer should know

- **OSM inputs are restored and pinned.** `refs/cache/osm/` now holds the OSM database state the data were built on
  (airfield 2026-09-24T09:07:42Z, landside 2026-09-26T03:03:01Z), rebuilt from the OSM editing API
  (`tools/xcheck/fetch_osm.py --via api`, `tools/xcheck/osm_attic_api.py`; every Overpass instance failed today). HEAD's
  own generators reproduce `data/sfo_details.json` (all OSM-derived lines / holds / edges / masts identical) and
  `data/sfo_landside.json` (identical) from them. Later OSM edits enter only through `build_airfield_details.OSM_UPDATES`.
- **`data/sfo_stands.*` = the 26 Sep build + `tools/stands/patch_stands.py`** (build_stands.py's September inputs are
  lost; the patch stage is scripted and lists its evidence in `fixups`). Re-read the file; do not cache stand fields.

## 1. Real-time workflow (`js/live/traffic.js`, `tools/live/**`, `data/snapshot.js`)

1. **New stand field `exclTypes`** (data `excl_types`, passed by `standGates()`): `{neighbour: [ICAO types]}` - while this
   stand holds one of those types the neighbour must stay free, and an occupied neighbour keeps those types off this
   stand (entries `'@F19:B772'` on the neighbour name the type parked at the other stand). Now: F19 B772 -> F18, F20;
   C9 B763 -> C11; C8 B752 -> C10 (each type comes within the ICAO stand clearance of the neighbour's envelope, and SFO's
   4 Nov plan never overlaps them). Please honour it in `blocked()` / `standFits()` on every path, like `excl` but per type.
2. **Classes / whitelists from SFO's 4 Nov plan**: A15 C -> E (span_max 60.3 / len_max 58.8 = the A332 SFO plans there),
   D5 and C9 CL -> D (B763), C11 `types_ok` + B738 / E195, F19 `types_ok` + B752 / B772. With the current standFits these
   allocations are accepted again (A15 / D5 / C9 were refused by class on SFO's own path). `types_ok_all_paths` stays on
   F19 / F20 (APP ISSUE F19|F20 1.9 m, unchanged request of static_geometry_round4 §2; traffic.js does not read it yet).
3. **src obs -> inf** (B9, B18, B22, D3, D4, D6, D9, F10) and **ADS-B stops beyond the nose** (`conflict_along` with
   `beyond: true`: B9 B737 +2.4 m, B18 A320 +1.8 m, D6 B737 +2.7 m, F10 CRJ +3.4 m; `adsb_beyond` evidence only: B26 A320
   +4.9 m, C4 A320 +2.6 m - one airframe each). If the matcher scores the along offset, these stands see aircraft stop
   1.8-3.4 m past the model nose.
4. **`data/snapshot.js` - licence conflict (owner's decision).** It is published with adsb.fi records although adsb.fi's
   terms forbid licensing them (docs/ATTRIBUTION.md). Please rebuild it from adsb.lol (ODbL) records only, with the
   provider per record, or keep it out of the public repo until the owner decides.
5. **`data/sfo_taxigraph.js`**: `tools/live/build_taxigraph.py` reads `refs/cache/osm/ksfo_osm_parsed.json`, which is the
   pinned 24 Sep state again - it has the OLD taxiway W and no lead-on arcs. The relocated W (OSM way 1562117372) is in
   `refs/cache/osm/overpass_ksfo_aeroway_at_20261104T180000Z.json` and in `data/sfo_details.json` (centerlineMeta src
   `osm_update`). Please add it to the graph (and drop the old W ways 155476502 / 155476504 and the old F1 crossing) so
   departures across 1L / 1R route on the paved W (realtime_round1 §3 / round2 §2a are answered by this).
6. `tools/stands/adsb_parked.py` was re-run on the 4 Nov recording (17:43-21Z, 177 stays, 140 with an SFO window):
   `refs/cache/stands/adsb_parked.json` (adsb.lol only). The September stays are gone.

## 2. Bridges workflow (`js/live/gates.js`)

1. **`standGates()` now passes `bridgesUpper`** (A6 / A11 / G13, same fields as `bridges`, `door: 3`, `upper: true`) -
   bridges_static #5 done here; please use `g.bridgesUpper` and drop `attachUpper()`'s own read of `STANDS`.
2. **Rotundas vs the terminal outline** (bridges_static #1 / #1b): `rotunda_max_r` now also stays 0.2 m inside the
   distance to the outline you draw (`sfo_buildings` complex + non-walkway parts): D7 2.16, E2 1.99, E3 2.11, E8 2.26,
   F7 2.10, F8 2.31 m. B2 L1 and F9 L1 (outline 0.25 / 1.23 m away) moved straight out by 2.40 / 1.45 m so the full
   2.45 m drum clears by 0.2 m (`rotunda_src` inferred; walk end and `stow_len` follow). check_stands: no new issue.
3. **Rest poses vs types SFO newly plans** (the build cannot re-run its stow search): WARN G3 L2 at rest 1.8 m from a
   B738 wing, G8 L2 2.8 m from an E75L, F19 L1 2.5 m from a B752, G13 L3 6.9 m from a B772 - narrow bodies on wide-body
   stands. If gates.js re-chooses the rest pose per occupant it should keep these clear; otherwise they stay WARNs.
4. Still open (no source in hand): A6 upper bridge cannot reach U1L (47.2 m), A11 upper rest pose / model
   (bridges_static #3 / #4), A10 L1 graze 0.9 m2 (check_stands ISSUE, unchanged), heights (#7).

## 3. Owner of `js/live/markings.js`

1. `details.roads` is now **empty** (the inferred terminal-offset "ramp road lines" were not imaged paint): the road
   loops draw nothing; drop them or keep them as no-ops. Real service-road paint is not traced yet.
2. Centrelines are split where NAIP shows no paint over >= 28 m (`centerlineMeta[i].drawn` false + `drawn_why`, `part`)
   and at reversals - `drawn` per entry already works. 17 runway-crossing lead-on / lead-off arcs (OSM 1571228365-381)
   lie ON the runway (edge -> centreline); 14 have NAIP paint and are `drawn`.
3. 4 holds have `src: 'inf'` (the relocated W at 1L / 1R, FAA AL-375 cycle 2611; position = SFO's median NAIP hold
   distance on that runway, `note`). Draw them like the others (or dimmer, if inferred paint should be marked).

## 4. Lead (`CLAUDE.md`, commits)

1. CLAUDE.md data table is stale: `sfo_stands.*` = 108 contact stands (+ remote / positions) from
   `tools/stands/build_stands.py` + `tools/stands/patch_stands.py` (not `tools/sat/export_stands.py`, not 89);
   `sfo_paint.*` / `sfo_pavement.*` from `tools/imagery/paint_pave_naip.py` (not tools/sat); add `sfo_landside.*`
   (`tools/build_landside.py`) and the OSM method (`tools/xcheck/fetch_osm.py` date-pinned, `--via api` fallback ->
   `parse_osm.py`). "Check the stand and bridge checks: `python3 tools/stands/check_stands.py`".
2. Please commit (via `tools/cache/sync.py`): `refs/cache/osm/*.json` (ODbL, `SOURCES.json`; not `.parts/`),
   `refs/cache/faa/00375ad_2611.pdf` + `SOURCES.json` (FAA, public domain), `refs/cache/stands/sfo_stands_built_20260926.json`
   and `adsb_parked.json` (own outputs; the patch stage needs the first). The 4 Nov flysfo snapshot stays local (listed
   in the MANIFEST) - patch_stands.py needs it to reproduce P1 / P2.
3. Owner decisions recorded as open in `docs/ATTRIBUTION.md`: `data/snapshot.js` (adsb.fi), flysfo-derived stand fields.

## 5. From bridges (round 2, 2026-11-05; js/live/gates.js owner) - exact data change for check.py's A10 ISSUE (orch-1)

**Root cause** (stand data, not the docking path and not gates.js): A10 L1's `rotunda` [-1297.71, 722.28] (OSM node
1096422734, "start of the tunnel"; `geom_src`: traced roofs as imaged, "likely ~1.3-2.1 m east of the true structure")
lies 0.77 m from the SFO Museum "Boarding Area A" outline (the outline check_stands tests and the 3-D ITB asset is built
from). check_stands' docked tunnel (2.9 m wide, from that centre) then grazes the outline 2.6-6.5 m out from the
rotunda: 0.85 m2 for B39M / B38M / B738 / B739 / A321 / A21N, beyond the "graze next to the rotunda" tolerance
(hausdorff > rot_r + 4 m); the door-facing cab is clear (0.00 m2). The same lean puts 30 more data rotundas closer to
the Museum outlines than a 1.5 m drum + 0.2 m (41 drums overlapped them, A9 L1 by 4.9 m2). gates.js now moves these
rotundas straight off the nearest outline by the deficit and keeps every moving part out of the outlines (0 of 3,286
dockings / paths / rest poses inside); the data should say the same.

**Requested change** (`data/sfo_stands.json` via patch_stands.py, `rotunda_src` "inferred: moved off the SFO Museum
outline for a 1.5 m drum + 0.2 m (gates.js prepGeom); OSM roof lean"): set `rotunda` - and the walk's last vertex where it
is the rotunda - to the positions below (x, z world m; shift in m):

| Bridge | data rotunda | new rotunda | shift |
|---|---|---|---|
| A4 L1 | -1204.34, 544.11 | -1204.55, 544.01 | 0.23 |
| A5 L1 | -1239.22, 610.17 | -1239.49, 610.02 | 0.31 |
| A9 L1 | -1264.32, 659.37 | -1265.31, 658.85 | 1.11 |
| **A10 L1** | **-1297.71, 722.28** | **-1298.55, 721.84** | **0.95** |
| A13 L1 | -1283.25, 814.78 | -1283.58, 815.46 | 0.76 |
| B6 L1 | -774.40, 602.57 | -774.64, 601.76 | 0.85 |
| B8 L1 | -760.60, 634.14 | -760.58, 634.22 | 0.08 |
| B10 L1 | -881.38, 671.14 | -881.86, 670.89 | 0.54 |
| B11 L1 | -876.45, 696.08 | -876.78, 696.73 | 0.73 |
| B11S's bridge (gate B11) | -877.96, 682.53 | -879.28, 682.90 | 1.37 |
| B15 L1 | -922.83, 765.44 | -923.53, 766.38 | 1.17 |
| B16 L1 | -916.06, 774.62 | -916.46, 775.33 | 0.82 |
| B19 L1 | -961.34, 835.53 | -962.58, 834.95 | 1.37 |
| B20 L1 | -958.16, 851.19 | -959.23, 851.40 | 1.09 |
| B24 L1 | -963.16, 940.36 | -963.12, 941.22 | 0.86 |
| B25 L1 | -980.24, 920.53 | -981.13, 921.40 | 1.25 |
| B26 L1 | -991.66, 911.69 | -992.19, 912.55 | 1.01 |
| B27 L1 | -1008.15, 903.83 | -1009.07, 904.46 | 1.11 |
| D4 L1 | -526.16, 206.54 | -526.41, 206.99 | 0.51 |
| D5 L1 | -495.79, 222.28 | -496.16, 222.98 | 0.80 |
| D16 L1 | -615.82, 138.16 | -616.06, 137.40 | 0.80 |
| E6 L1 | -836.14, 0.75 | -836.94, 0.33 | 0.90 |
| E8 L1 | -805.71, -46.91 | -806.28, -47.21 | 0.65 |
| E11 L1 | -745.83, -66.83 | -745.82, -67.75 | 0.92 |
| G1 L1 | -1244.34, 157.85 | -1244.22, 157.63 | 0.25 |
| G3 L1 | -1381.83, 154.66 | -1382.10, 155.18 | 0.59 |
| G4 L1 | -1445.19, 121.09 | -1445.51, 121.70 | 0.69 |
| G7 L1 | -1507.92, 87.90 | -1508.29, 88.61 | 0.80 |
| G8 L1 | -1571.38, 54.55 | -1571.70, 55.15 | 0.68 |
| G9 L1 | -1488.96, 34.93 | -1489.87, 34.46 | 1.02 |
| G10 L1 | -1547.77, 0.38 | -1547.97, 0.45 | 0.21 |

and, because the shift shortens their rest tunnel below the model's retraction, `stow` (and `stow_len`) of: B11 L1
[-890.91, 710.05], B15 L1 [-936.21, 776.50], B16 L1 [-932.76, 785.89], B20 L1 [-977.35, 858.41], G4 L1 [-1440.15,
130.46], G7 L1 [-1510.64, 98.61] (the same rest line, pivot at the retraction - what gates.js draws).

**Checked:** check_stands.py on a copy of the data with exactly these changes: ISSUES 1 -> 0 (the A10 ISSUE and all 29
A10 L1 notes gone), WARNINGS 18 -> 17 (B26 L1 / E75L extension warning gone), notes 73 -> 44, nothing new. Better than my
minimal shift, if you have it: correct the OSM bridge geometry by the measured relief lean at bridge-roof height
(tools/buildings/draw_data.py `dom_lean()`; the ITB spec's frame model, nadir [-2767.8, 443.6]) and re-run the stow
search.

**Also (bridges round 2, unchanged data questions with today's numbers):**
1. bridges-v3, known clip: the data's rest / docked poses of A12, F5, F14, F17, F19, F21 L1 fold the tunnel back to
   41-45 deg from the bridge's own walkway, so the 2.4 m rotunda corridor overlaps the 2.6 m walkway outside the drum:
   A12 L1 0.32 m2 at rest / 0.47 m2 worst (37 of 37 poses), F5 L1 0.18 (1 of 25), F14 L1 0.40 (6/27), F17 L1 0.45 / 0.46
   (6/27), F19 L1 0.45 / 0.52 (6/14), F21 L1 0.56 (5/26) (gates.js `b.ownClip`, exact). Please check their last walkway
   segment / rotunda position against NAIP (the walkway probably enters the rotunda from another side).
2. bridges-v2: the same 12 observed (bridge, type) pairs stay undocked (A1 L2 B78X; A2 L2 B78X, A35K; A6 / A11 upper
   A388; F5 L1 B738 / B38M / E75L; F11 L2 B772; F15 L1 B39M; G7 L1 E75L; G8 L1 E75L) - bridges_closeout §1.1, 1.5, 1.6, 1.9.
3. bridges-v4: docked slopes > 1:12 / > 1:8: 969 / 386 of 3,286 (observed 125 / 39 of 605); HrPinned on 108 bridges -
   the departure level 5.4 m is inferred (§1.5).
4. bridges-v5: stow vs the imaged parked pose (§1.7) - not re-measured (Overpass down for the reviewer).
5. bridges-v9: 158 dockings beyond the operational extension (max +1.02 m, was 189 / +1.19 m); 19 need the inferred
   optional 185 deg cab (F14, F17, F19, F21 L1; 38.8-48.2 deg ccw) - please pick models / source the cab split (§1.3, 1.4).

---------------------------------------------------------------------------------------------------------------------

# Round 2 (fix round of wf_41410c83, 2026-11-05): static changes, numbers, requests

Nothing hand-edited; every data file regenerated by its generator (byte-identical on a second run). Numbers: the
verifier's own scripts (`vst/chk/paths2.py`, `newpave.py`, `pos.py`, `pave_chk.py`, `rev/chk_lines.py`, `vst/chk/edges.py`,
`arcs.py`) plus `tools/imagery/check_markings.py`, `tools/stands/check_stands.py`, `tools/sat/check.py`.

| Finding | Change | Before | After |
|---|---|---|---|
| static-v1 (airside paths shifted the wrong way) | `tools/build_landside.py` measure_path: offset along measure_band's OWN normal (no shapely side convention), running-median offset per 2.5 m station (+-12.5 m), outliers > 1 m off the local median dropped, one entry per imaged stretch (`part`; gaps < 15 m bridged, `drawn` false where NAIP shows no band), w = stretch median; a band < 1.75 m wide or with a paved flank (sat < 22) is a paint line in wider pavement, not a path | drawn-vs-imaged centre median 2.88 m, p90 4.00, 62 % > 2 m; share of the drawn width on the imaged band 4 % (47 % zero); under the drawn bands: vegetation 4.8 %, soil 30.0 % | median 0.12 m, p90 0.25, 2 % > 2 m; 96 % (1 % zero); vegetation 0.1 %, soil 1.2 %. 103 stretches / 10.5 km drawn (was 19 ways / 19.4 km) |
| static-v2 (pavement discs at vehicle stays) | `tools/imagery/paint_pave_naip.py`: only AIRCRAFT stays (ICAO type that is no readsb vehicle pseudo-type SERV / GRND / EMER / TWR ..., or an SFO flight / stand match): 159 of 177; bare soil / dry grass (R - B > 38, R > 110, opened) rejected in the footprints | added area since 8d13a5f: 16.6 ha, soil / dry grass 3.5 %; FM8 (144,-74) 62 %, OPS40 76 %, OPS38 68 %, OPS12 44 %, OPS31 22 % | 15.1 ha, 1.4 %; all six vehicle discs gone; position footprints > 50 % / > 25 % unpaved: 0 / 0 (unchanged); all pavement polygons soil 0.8 -> 0.6 % |
| static-v3 (old W / F1 crossing half-retired; companion edits) | `tools/build_airfield_details.py`: PAVEMENT_RETIRE - the 3 SFO Museum 'Taxiway F1' polygons (8,838 m2) get no edges and are listed in `pavementRetired`; `js/live/airport.js` does not pave them. Evidence: FAA AL-375 2611 rendered at 1200 dpi, registered on the runway ends / intersections (residual 6-17 px = 7-20 m): ONE paved band between 1L and 1R near W, crossing at 86 deg (relocated W 89.9 deg, old F1 65-69 deg), no pavement between F and it. OSM_UPDATES: J 1562117374 added (= the eastern 97 m of the deleted J, same nodes; NAIP paint 21/24); J 155476380, 671167438, 1511792223 retired (deleted in changeset 189525528); B 1562117373 is a split of base B 363803227 (100 % within 3 m): not added | 539 m of edges and 74 % pavement along the retired trace; 3 deleted ways drawn | 0 m edges along F1 (610 m removed), F1 not paved; holds unchanged (90; the hold rule now keeps holds on the re-mapped part of a retired way) |
| static-v4 (edge defects) | hygiene: a turn > 120 deg with a leg < 2 m loses that vertex (ends and interior); edges split where >= 16 m have no paint / sit > 1.5 m off it (3.1 km cut, crops: the cut runs lay inside pavement or on concrete/asphalt seams); on-runway arcs count paint only with b* >= 11 (painted arcs 12-40, ambiguous 9-11) | hooks 46 (35 at ends); edge runs >= 15 m > 1.5 m off paint 13 / 250 m; edge samples > 1.5 m 3.1 %; arc 1571228374 drawn with 4/21 yellow peaks | hooks 0; 3 / 45 m; 1.7 % (check_markings b*: 2.5 -> 1.6 %, > 3 m 1.3 -> 0.8 %); arcs 374 and 377 not drawn (12 of 17 drawn), arcs median 0.20 m, 1.9 % > 1.5 m; check_markings OK; side-stripe 0 m, reversals 0, self-intersections 0 |
| static-v5 (stand data reproducible only here) | `tools/stands/patch_stands.py`: P1 / P2 results recorded in `refs/cache/stands/patch_p1p2_replay.json` (per stand only the fields they set + log, snapshot SHA-256; no windows) and replayed when the snapshot is missing (`--replay` forces it, `--check` compares live vs replay) | fresh clone cannot regenerate | live and replay outputs byte-identical; `--check`: MATCH (56 stands) |
| static-v6 (exclTypes unused) | realtime track (request 1 below); standGates passes exclTypes (F19 {F18, F20: B772}) | - | unchanged: realtime |

check_stands / check.py: ISSUES 1 -> 0 (A10), WARNINGS 18 -> 17 (B26 L1 / E75L gone), APP 1 (F19|F20, unchanged).

## R2.1 Bridges (js/live/gates.js owner)

1. **Your §5 / R2.1 data change is in** (patch_stands P6, computed - not copied: gates.js prepGeom's rule with the same
   outlines, drum / walkway clearances and 2.0 m cap, from the other bridges' data positions): the same 31 rotundas
   (max difference to your table 0.00 m), the 6 stows at the retraction (B11, B15, B16, B20, G4, G7 L1; <= 0.01 m), walk
   end = rotunda, `rotunda_src` inferred, and `rotunda_max_r` capped at (d - 0.2) / 2 where two moved drums came closer
   (G3 2.11, G4 2.16, G7 2.13, G8 2.18 m). Node check: prepGeom now shifts 0 of 131 rotundas; prepBridge + finishPrep
   787 ms, ownClip 6 (the known A12 / F5 / F14 / F17 / F19 / F21 L1). Keep the shift in gates.js as a guard or drop it.
2. **Rest poses vs the imaged pose (§1.7, bridges-v5)** - patch_stands P7 tests the OSM parked cab of the 20 bridges whose
   `stow` is > 3 m from it with the build's own rest criteria (envelope of every stand within 150 m + 1 m, ICAO clearance
   to the observed types' wings, SFO Museum outline, model range, not crossed by another bridge docked to an accepted
   type; the build's 30 m length cap dropped). None passes; each records why in `stow_osm` {dist_m, osm_len_m, why_not}:
   16 overlap the envelope of their own stand's accepted types (G13 L3, F15 L2, F22 L2, F11 L2, B15 L1 ...: the imaged
   pose is where the bridge parked next to a smaller aircraft), A4 L1 / G10 L1 are 0.92 / 0.96 m from it (< 1 m), D9 /
   D11 L1 lie 4.0 / 3.4 m inside the ICAO clearance of the observed A319 / A320, G13 L2 is crossed by G13 L1 docked to a
   B736 (12.7 m2). (Check: each OSM pose alone in check_stands - only A4 L1, G10 L1, G13 L2 add no issue / warning; G13
   L2's crossing is a check_stands note because B736 is not observed at G13.)
3. Still open, no source in hand: heights / departure levels (§1.5 - the observed-type rotunda heights change nothing,
   your own numbers), F15 / G12 one or two drums (§1.1), the six folded walkway junctions (§1.2: NAIP at roof height with
   the 1.3-2.1 m lean cannot place the walkway end to the needed < 1 m), models for the over-extension (§1.3) and the
   optional-cab split (§1.4), F11 L2 (§1.6: its OSM pose overlaps F11's envelope by 20.9 m2 - P7), A15 L1 re-trace (§1.8),
   the upper-deck A6 / A11 (§1.9).

## R2.2 Realtime (js/live/traffic.js, tools/live/**)

1. **static-v6, unchanged request (§1.1 above):** honour `g.exclTypes` in `blocked()` / `standFits()` on every path
   (entries `'@F19:B772'` on the neighbour mean the type parked at the other stand). Today F19 B772 / C9 B763 / C8 B752
   are accepted beside an occupied F20 / C11 / C10 at 4.7 / 5.3 / 5.7 m (below the ICAO 7.5 m, no overlap).
2. Taxigraph (§1.5 above, extended): drop the retired ways listed in `DETAILS.centerlineRetired` (now also J 155476380,
   671167438, 1511792223) and add J 1562117374 (centerlineMeta src `osm` with `osm_changeset` 189525528).
3. **`DETAILS.pavementRetired`** (the old F1 crossing, 3 SFO Museum polygons, 8,838 m2) is no longer pavement:
   `inPolys(this.taxiways, ...)` and every "on pavement" test built from `AIRPORT.taxiways` should skip these
   (`name` + `poly` index), or an aircraft could hold / park on grass between 1L and 1R.

## R2.3 Owners of js/live/lights.js, js/live/signs.js, js/three ground / engine, jobs/extract2d.mjs

`DETAILS.pavementRetired` lists SFO Museum taxiway polygons that no longer exist (layer `taxiways`, `name`, `poly`):
skip them wherever `AIRPORT.taxiways` rings are drawn or used (taxiway edge lights along the rings, sign placement,
three.js pavement bake, 2-D extracts). js/live/airport.js already skips them in the WebGL2 bake.

## R2.4 Markings (js/live/markings.js)

Edges: 400 runs (36.9 km; were 380 / 40.6 km - split runs, F1 removed); arcs 1571228374 / 377 now `drawn` false;
centrelines 341 (J re-mapped, old J and connectors retired). Format unchanged.

## R2.5 Lead

1. Commit (via tools/cache/sync.py) `refs/cache/stands/patch_p1p2_replay.json` (own output; flysfo-derived values that
   data/sfo_stands.json already publishes - docs/ATTRIBUTION.md flysfo row). The flysfo snapshot itself stays local.
2. CLAUDE.md data table still stale (§4.1 above).
3. Open, flagged: the asphalt perimeter road (OSM 112508632, surface=asphalt, ~6-8 m) is wider than measure_band's
   window; where NAIP shows only its edge / lane paint (1.5 km, 1.15 km of it not paved by any other source) it is now
   not drawn (round 1: a 1.75 m concrete strip 2.5 m off it). Needs an asphalt-road width measurement (not done).

---------------------------------------------------------------------------------------------------------------------

# Round 2 of the close-out-2 fix / verify (static, 2026-11-05; "round 3" in the code comments)

Answers the round-1 verifier's five findings (v1-v5 of `closeout2_findings.json` groups.static) and the lead's static-v5
request. Nothing hand-edited; every data file regenerated by its generator, a second run byte-identical (landside,
details: twice; stands: `--check` MATCH; paint / pavement: scratch run + repo run, see below). Before / after with the
verifier's own scripts (`ver2/holdfrag.py`, `shortedges2.py`-style b* check, `vst/chk/edges.py`, `paths2.py` logic) and
mine in scratch `st3/` (`pavecov.py`, `pathcls.py`, `overlap.py`, `pavediff.py`, `faareg.py`).

| Finding | Change | Before | After |
|---|---|---|---|
| v1 (major) perimeter road 112508632 | `tools/build_landside.py` `measure_road`: a wide paved run across +-14 m (samples with channel spread < 34, grey > 150, along-line texture < 3.5 - excludes dry grass / soil, Bay water, dark and mottled rip-rap, light infield soil), edges at the half maximum; per station it replaces the narrow band when >= 1.5 m wider (the 1.75 m strip lay ON the road) or when there is none; one width per near-constant-width piece; road gaps where the run reaches the window (inside wider pavement / light ground) or a light line, <= 250 m, and any gap < 30 m between two road pieces bridged along the OSM line (`bridged`, offset interpolated, narrower neighbour width: inferred); drawn parts clipped at SFO Museum runway / taxiway pavement; `material` = OSM surface (asphalt / concrete, obs) else concrete (inferred); `naip_grey` per drawn entry. `js/live/airport.js`: only `material` concrete goes into the concrete layer | 112508632: drawn 0.83 of 4.89 km, 3,570 m on no paved source, 804 m of 1.75 m edge strips; all paths: 10.5 km drawn, 14.0 km undrawn on no paved source; 4.8 km of OSM-asphalt paths in the concrete layer | 112508632: drawn 4.88 km (31 pieces, 5.5-16.3 m wide, 9 of them bridged), 2 m on no paved source, 0 m strips <= 1.75 m; all paths: 27.8 km drawn (12.5 asphalt / 15.3 concrete; 5.9 km bridged, 2.3 km of it off other pavement), 3.4 km undrawn on no paved source; NAIP under the drawn paths: vegetation 0.0 %, soil / dry grass 1.0 -> 0.9 %, water / dark rip-rap 0.1 %; bands drawn vs imaged median 0.12 m, p90 0.25, 2 % > 2 m (unchanged); roads 0.25 m / p90 2.4 m, drawn width on the imaged run 0.94; on runways 0 m2, taxiways 187 -> 46 m2, buildings 0 -> 1 m2 |
| v2 edge dashes at hold bars | `tools/build_airfield_details.py`: after the cut, a piece with > 50 % of its length in a hold-bar zone, or < 15 m with no painted sample of its own (b* ridge within 1.5 m), or mostly inside a retired part, is dropped (`edgeStats.fragments_dropped`) | 13 pieces / 123 m > 50 % in hold zones; 9 pieces < 15 m without paint (verifier's b* rule) | 0 / 0; 13 pieces (123 m) dropped; edges 400 -> 387; check_markings OK, edges b* > 1.5 m 1.6 -> 1.5 %, > 3 m 0.8 %; side stripe 0 m, reversals 0, self-intersections 0 |
| v3 old-J remainder pavement | new `tools/xcheck/faa_al375_mask.py` -> `refs/cache/faa/al375_2611_oldJ.json` (own output): AL-375 2611 at 600 dpi registered on the four runway-centreline crossings (the fitted black bands; world runway centre points 0.1 / 0.3 m median / max off them), chart classes, the chart's white island touching the old-J remainder (OSM 155476380 minus 1562117374). Builder: the part of the SFO Museum polygons inside the +-12 m corridor AND the island -> `pavementRetiredParts` (rings, why); airport.js cuts the rings out of the taxiway pavement | old J west 150 m paved, no decision recorded | chart under the trace's middle 60 %: 61 % white / 27 % grey (controls: retired F1 #0 / #1 89 / 91 % white, relocated W 2 % white); retired 'Taxiway A/F1' #0 882 m2 + 'Taxiway A/B/F' #1 492 m2 = 1,374 m2; no edge lies in them (0 dropped). INFERRED: the island's surface (grass or green paint like the two painted islands it joins on the chart) - drawn unpaved like F1 |
| v4 lost grey pavement at vehicle stays | `tools/imagery/paint_pave_naip.py`: the 18 vehicle stays seed the 60 m candidate region again (NAIP grey + smooth decides; S < 32 excludes soil), never footprints, never the 12,000 m2 hole limit | round-1 pavement lost in round 2 and on no other source 1.48 ha (24 % soil, 43 % light grey) | +0.27 ha (soil 0.1 %, vegetation 0 %, light grey 88 %); 0.26 ha of the 1.48 back (89 % grey); still missing 1.22 ha (29 % soil, 33 % grey: mostly the ARFF apron (-1569, -600) with fire trucks / parking stripes, which fails grey + smooth); FM8 0 m2 (unchanged), R41 576 -> 820 m2. PARTLY: the cluttered ARFF apron needs a footprint-like rule, which the verifier ruled out for vehicles (FM8's disc is 62 % soil + dry grass) |
| v5 text | `_J_WHY` single %, edge-cut comment "(2 m apart, i.e. >= 16 m)" | '100 %% within 3 m' x2 | no '%%' in sfo_details.json |
| static-v5 (lead) flysfo local-only | new `tools/stands/flysfo_provenance.py` -> `refs/cache/stands/flysfo_provenance.json`: exactly which committed values derive from flysfo (per stand / field of data/sfo_stands.json; the replay; the SFO match fields of adsb_parked.json) and which P1 types ADS-B geometry alone corroborates. `patch_stands.py` P5 now selects stays by geometry + ADS-B type (no flysfo match); `paint_pave_naip.py` identifies aircraft by ADS-B type or airline callsign (same 159 of 177 stays) | P5 and the pavement read flysfo-derived match fields | no generator reads a flysfo-derived field except P1 / P2 (replayed) and the base build; P5: D6 B737 +2.7 (n 1) -> +2.6 m (n 2), F10 CRJ +3.4 (n 1) -> +3.7 m (n 2), nothing else; 108 of 108 stands carry flysfo-derived fields (base names / classes / types); 3 of 66 P1 types corroborated by ADS-B geometry |

check_stands / check.py before -> after: ISSUES 0 -> 0, WARNINGS 17 -> 17 (identical lines), APP ISSUES 0 -> 0. patch_stands
`--check`: MATCH (56 stands).

## R3.1 Bridges (js/live/gates.js) - the open static items of bridges_closeout.md

1. A10 (orch-1): done in the previous fix (P6); check.py ISSUES 0, nothing changed here.
2. Heights / departure levels (§1.5; the observed-type rotunda heights change nothing, your own numbers): still no source -
   the 133 OSM jet bridges carry no height / min_height / ele (layer=1 on 79, level on 2), NAIP is 2-D, and no SFO
   drawing with departure-level elevations is in hand. Deferred, unchanged.
3. Rest poses vs the imaged pose (§1.7): P7 (previous fix) tested the OSM parked cab of the 20 bridges > 3 m from `stow`
   with the build's rest criteria (`stow_osm.why_not`). A NAIP re-measurement was not done: NAIP 2024 is one epoch
   (many bridges docked), the roof lean is 1.3-2.1 m, and OSM's cab is itself the imaged parked pose. Deferred.

## R3.2 Realtime (traffic.js, ground.js, tools/live/**)

1. `pavementRetiredParts` (new, sfo_details): PARTS of SFO Museum taxiway polygons that no longer exist (`ring`, `name`,
   `poly`, `why`) - the old-J remainder, 1,374 m2. Any "on pavement" test built from `AIRPORT.taxiways` (inPolys,
   GroundPhysics, the taxi graph) should subtract the rings (0 ADS-B fixes there, so nothing should change).
2. realtime_closeout R2.3.1 done: tools/stands/geom.py / check_stands.py docstrings now say types_ok applies on SFO's path
   where `types_ok_all_paths` (F19 / F20); your one-line change is kept.
3. realtime_closeout R2.3.2 (cells off the mask and the OSM net): NOT changed this round. Measured (25 m cells from the
   corner given; paved = any source the bake draws except stand envelopes / end zones; NAIP classes): (-550,-350) paved
   70 %, NAIP grey 71 % / soil 27 %; (-550,-375) 24 % / 56 % / 37 %; (-525,-375) 53 % / 64 % / 29 %; (-650,-175) 69 % /
   82 % / 13 %; (-350,300) W 97 %; (-1450,-175) 76 % / 88 % / 1 %; (-1050,1025) 68 % / 94 % / 3 %; (-1400,-50) 48 % /
   95 % / 0 %; (-600,-250) 33 % / 71 % / 7 %; (-800,-925) FBO 64 % / 91 % / 0 %. The ones with NAIP grey >= 88 % and
   soil <= 3 % are pavement the classifier misses (cluttered aprons near the G / A piers and the FBO) - next static round;
   the (-550,-350) group is the infield edge (27-37 % soil). Scratch: st3/cells.py.

## R3.3 Owner of js/shaders/ground.js / the three.js bake (engine)

1. Airside paths now carry `material` 'asphalt' (OSM surface=asphalt; 12.5 km incl. the Bay perimeter road, 6-16 m wide)
   and go into the bake as pavement WITHOUT the concrete flag. On NAIP they are as light as the concrete paths
   (`naip_grey` medians 198 vs 204; runways 173-189), but the bake's asphalt is the dark 0.13 albedo: they will render
   much darker than imaged. Please use `naip_grey` (or an aged-asphalt tone) for these, or tell me to flag them concrete
   for the albedo only.
2. `pavementRetiredParts` (see R3.2.1): js/live/airport.js cuts them out of the WebGL2 bake; the three.js bake / lights
   along `AIRPORT.taxiways` rings / signs / 2-D extracts should do the same.

## R3.4 Lead

1. Commit (via tools/cache/sync.py): `refs/cache/faa/al375_2611_oldJ.json` (own output from the public-domain FAA chart;
   SOURCES.json entry added), `refs/cache/stands/flysfo_provenance.json` (own output; it repeats only stand / type pairs
   data/sfo_stands.json already publishes), and the new tools `tools/xcheck/faa_al375_mask.py`,
   `tools/stands/flysfo_provenance.py`. `out/faa/al600-1.png` is a local render (regenerated by the tool).
2. Owner decision still open (docs/ATTRIBUTION.md flysfo row, updated): the flysfo-derived stand fields - the exact list is
   now in flysfo_provenance.json; option (c) "ADS-B only" would keep 3 of the 66 types P1 adds.

---------------------------------------------------------------------------------------------------------------------

# From bridges, round 2 second pass (2026-11-05; js/live/gates.js owner) - revert 9 B-pier rotunda moves of P6 (bridges-v6)

**Why:** the round-1 verifier showed that P6's rule (= gates.js prepGeom's, which you replicated) treated the SFO Museum
"Boarding Area B" strips that trace the bridges' OWN fixed walkways as building and pushed nine B-pier rotundas about 1 m
outward along their own walkway. The 3-D domestic asset does not draw those strips (docs/research/buildings3d.md:
"the fixed-walkway strips at the BA-B tip are left to the app's bridges"; data/buildings3d/integration.json footprints
cover 3-31 % of their edges, all within 0.5 m of the pier face), so "moved off the SFO Museum outline" does not hold for
them. gates.js now exempts a bridge's own walkway strip (`ownStrip`: a piece of a Museum ring at most 6.8 m = walkway
2.6 m + 2 x 2.1 m lean across the walkway, every point of it within 6.8 m of the mapped walkway, along a run of at
least 5 m of it - the BA-B strips run 6.3-50.8 m, the pier-face bumps around the other walkways' starts, which the
assets DO draw, at most 3.3 m). With that rule and the OSM positions these nine need no shift (the other 22 P6 moves
still do, by the same amounts).

**Requested change** (`data/sfo_stands.json` via patch_stands.py; either skip these nine in P6, or give P6 the own-strip
exemption above): restore the 373de34 values (OSM) of `rotunda`, the walk's last vertex, `rotunda_src`, and drop the P6
`fixup` entry; for B11 / B16 / B20 also `stow`, and `stow_len` where P6 changed it:

| Bridge | rotunda now (P6) | restore (OSM) | stow restore | stow_len restore |
|---|---|---|---|---|
| B6 L1 | -774.64, 601.76 | -774.40, 602.57 | - | 14.8 |
| B11 L1 | -876.78, 696.73 | -876.45, 696.08 | -890.41, 709.58 | - |
| B16 L1 | -916.46, 775.33 | -916.06, 774.62 | -932.15, 785.50 | - |
| B19 L1 | -962.58, 834.95 | -961.34, 835.53 | - | 19.3 |
| B20 L1 | -959.23, 851.40 | -958.16, 851.19 | -977.27, 858.38 | 20.4 |
| B24 L1 | -963.12, 941.22 | -963.16, 940.36 | - | 22.2 |
| B25 L1 | -981.13, 921.40 | -980.24, 920.53 | - | 25.2 |
| B26 L1 | -992.19, 912.55 | -991.66, 911.69 | - | 20.3 |
| B27 L1 | -1009.07, 904.46 | -1008.15, 903.83 | - | 14.3 |

**Checked** (scratch tree with exactly these nine reverted, today's other data, the new gates.js): prepGeom shifts 0 of
131 rotundas; 3,278 dockings made / 109 refused, the same refusal list as without the revert; drums vs the 3-D asset
footprints: the same 7 pre-existing overlaps (none at B), drums vs the drawn outline 0. B15 L1 (1.17 m) and B11S (1.37 m)
keep their moves: their Museum pieces run only 1.5 / 3.0 m along the walkway and the asset draws 45-63 % of them.
