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
131 rotundas; bcheck2: 0 issues, 3,278 dockings made / 109 refused, the same refusal list, slopes and observed pairs as
without the revert; drums vs the 3-D asset footprints: the same 7 pre-existing overlaps (none at B), drums vs the drawn
outline 0. One cost: B26 L1 (OSM rotunda 1.0 m nearer the pier) then reaches 13 types beyond its model's
operational extension by 0.13-0.52 m (158 -> 171 such dockings, still >= 1.48 m short of the allowance) - the model question of
bridges_closeout §1.3. B15 L1 (1.17 m) and B11S (1.37 m)
keep their moves: their Museum pieces run only 1.5 / 3.0 m along the walkway and the asset draws 45-63 % of them.


---------------------------------------------------------------------------------------------------------------------

# Round 3 (close-out 3, fix round 1, static, 2026-11-06 / 07): static-1 ... static-13

Answers the 13 findings of `docs/requests/closeout3_findings.json` groups.static. Nothing hand-edited: every data file
comes from its generator; second runs are byte-identical (details and landside run twice; stands: `--replay` output
md5-identical to the live run, `--check` MATCH (55 stands); paint / pavement: a second run md5-identical, twice - before and after rule (e)). Restarted 2026-11-07 after a
usage-limit stop and a reboot: the unfinished pavement step was completed (rule (e) below) and the replay re-run. Before = the data at the start of
the round (scratch copies), after = now. Checks: `tools/stands/check_stands.py` ISSUES 0 -> 0, WARNINGS 17 -> 17 (lines
below), APP ISSUES 0 -> 0; `tools/imagery/check_markings.py` OK (edge samples 3,682 -> 3,680, the two dropped dashes; b*
> 1.5 m 1.5 % -> 1.5 %); bridges summ (verify-3 `summ.mjs`, gates.js of the tree): prepGeom shifts 0, dockings 3,304 /
3,413 planned, 109 refused (unchanged). check_stands / check.py re-run on the final data (2026-11-07): the same 17 lines.

| Finding | Change | Before | After |
|---|---|---|---|
| static-1 (major) aircraft on unpaved cells | NEW `tools/imagery/adsb_ground_cells.py` -> `refs/cache/stands/adsb_ground_cells.json` (own output, ODbL: the 35 committed adsb.lol hours 4 Nov 17Z - 6 Nov 03Z, 115,166 aircraft ground fixes (alt_baro ground, NACp >= 8, position age <= 2 s, no vehicle pseudo-types) in 16,317 cells of 5 m). `tools/imagery/paint_pave_naip.py`, five rules, each counted in the polygon `src` share (inferred); NAIP still decides; OSM building footprints (not `building=roof`) and (2026-11-07) the app's runway end zones (`END_ZONES` of js/live/airport.js: blast pads / EMAS beds, parsed from the file) take no addition: (a) candidate region + 60 m round cells with >= 2 aircraft fixes and the grey apron connected to them up to 150 m (where the 25 m window has <= 3 % soil / vegetation); (b) cluttered aprons: inside a 25 m window >= 88 % grey (reviewer class), <= 3 % soil and vegetation, >= 50 % smooth, every pixel that is not soil / vegetation / building; (c) vehicle-stay pads (ARFF): within 25 m of a vehicle stay, smooth unsaturated pixels or a >= 60 % grey / <= 5 % soil window, connected to the pavement; (d) bright concrete: within 10 m of a cell where >= 2 aircraft were on the ground the window of (b) counts V >= 245 grey pixels too (the fresh slab south of Boarding Area B); (e) (2026-11-07) any-window envelope: a pixel inside ANY qualifying window of (b), not only the one centred on it, when it is near-neutral (spread < 30, V < 245, R - B <= 25, lum > 70) and its 5 m window >= 50 % smooth - the light island borders / shoulders beside soil (the replay cell (-550,-375): NAIP 92 % grey / 1 % soil but 73 % paved). No footprints. A first version of (e) also let V >= 245 pixels in and paved the EMAS beds beyond 1L / 1R; caught on the review montage, fixed (V < 245 + end zones) before the replay | pavement 367 polygons, 173.6 ha; cells (25 m from the corner, NAIP mask p or SFO Museum / apron): (-1450,-175) 69 %, (-1400,-50) 40 %, (-1050,1025) 61 %, FBO (-800,-925) 49 %, (-1300,-150) 59 %, (-1400,700) 43 %, (-1625,-150) 32 %, UAL2480 (-1385,-1930) 1 %; ARFF R41 25 m disc 217 m2 paved / 680 m2 unpaved (+ the 1,064 m2 station building), OPS44 pad 474 / 1,486; the before-replay's 25 worst offpave cells (25 m, centred): 0 >= 98 % paved; airfield 25 m cells with NAIP grey >= 88 %, soil / vegetation <= 3 %, no building and ADS-B aircraft fixes: 176 < 90 % paved, 35 < 50 %; round-1 pavement still missing 2.75 ha; all-hours replay offpave.mask 1,375,584 frames / 377 aircraft, offpave.union 471,479 / 237 | pavement 284 polygons, 209.1 ha (+35.5 ha, 0 removed; the added pixels: NAIP soil 1.1 %, vegetation 0.2 %, channel spread > 34 5.2 % = cars / GSE inside the envelopes; 166 polygons carry a round-3 share in `src`); cells: (-1450,-175) 99 %, (-1400,-50) 100 %, (-1050,1025) 90 %, FBO 79 % (the rest: rough concrete round a painted island), (-1300,-150) 100 %, (-1400,700) 77 %, (-1625,-150) 90 %, UAL2480 100 %; ARFF disc 510 / 386 m2 (the rest: 58 % reviewer-grey but striped / textured below the window shares, 33 % soil / tan; not footprinted, as the round-2 verifier ruled for vehicles), OPS44 1,370 / 591 (85 % of the rest dark, lum < 90); worst-25 cells: 14 >= 98 %, (-550,-375) 90 %, (-525,-375) 95 %, (-1450,-175) 92 %, (-1625,-150) 90 %; left: (-550,-350) 57 % (NAIP 29 % soil, the island interior), (-600,-250 / -275) 46 / 54 % (12 % soil, a ditch at the old F1 crossing), W (-350..-375, 275..300) 39-87 % in the NAIP mask (W is paved by its osm_update buffer: NAIP predates it); criterion cells with fixes 176 -> 45 < 90 %, 35 -> 7 < 50 % (the rest: shoulders beside aircraft imaged by NAIP, striped shoulders); round-1 pavement still missing 2.00 ha (40 % soil; 1,085 m2 of it is the ARFF station building); all-hours replay (round-2 harness and stream, frozen r3v code, this round's data): offpave.mask 1,375,584 -> 412,453 frames (377 -> 328 aircraft), offpave.union 471,479 -> 5,678 frames (237 -> 153); UAL2480's 369,812 frames are gone; 335,068 of the mask frames left are one parked GLF5 (N199TH, (-1138,-1171)) whose gear point lies 0.15 m beyond the apron edge on the fence line beside the service road (NAIP: fence / barrier, not pavement - pose, realtime); the worst union cells left: (-550,-350) 501 frames, (-550,-375) 202, (-600,-275 / -250) 138 / 121 (gear 1-3 m into the soil strip beside the runway exit at (-607,-269): corner cut), W (-350..-375, 275..300) 59-160 (the relocated W, unchanged) |
| static-2 refused observed pairs (data) | F15 / G12: NAIP 2024 shows two tunnels leaving each walkway end, roots ~3 m apart (OSM drums 3.38 / 3.39 m apart) - two drums (twin heads, r 1.64 m) stay; the F15 L1 B39M refusal is the twin-drum neck geometry (bridges). F11 L2: its OSM parked cab overlaps F11's envelope by 20.9 m2 (P7) and P10 finds no rest pose that keeps the ICAO clearance to the observed B752, so the rest pose stays; the B772 refusal (path from rest over the wing) needs gates.js to re-choose the rest per occupant (request below). Models / upper-deck bridges A6 / A11 / reach A1 / A2: no open source names SFO's bridge makers or the upper-deck units (owner decision OD-14, default unchanged: Oshkosh AeroTech ranges, inferred). | 12 observed pairs refused (bcheck2) | data unchanged for these; check.py extension WARNs: +A2 L2 / B789 (41.6 m, a type SFO newly planned there) and +B26 L1 / E75L (36.3 m after the B-pier revert of static-8), both within 1 m. PARTLY - the bridge makers are the owner's question (OD-14). |
| static-3 old-J island | `tools/xcheck/faa_al375_mask.py`: chart crop 60 -> 120 m, so the white island is measured whole (5,575 m2, `white_touches_crop` false). `tools/build_airfield_details.py`: the old-J retirement is removed (AL-375 draws painted islands white too; 36 vehicle fixes cross the band), its `why` text with it. `paint_pave_naip.py`: the chart island on the former SFO Museum taxiway pavement gets green no-taxi paint like the two painted islands it joins (one polygon, 2,219 m2, `src` inferred) | 1,374 m2 retired (an unpaved +-12 m band through a paved island); why "no ground traffic" | 0 m2 retired in the island; the island is paved (SFO Museum + NAIP) with the inferred paint; no edge in it |
| static-4 F1 #2 chart-grey fillet | `faa_al375_mask.py` `f1_parts`: per F1 polygon the chart-grey parts (grey 180-230, closed, >= 30 m2); builder retires a polygon whole only when < 50 m2 of it is grey, else all but the grey parts (`pavementRetiredParts`), `why` cites the kept area | F1 #2 retired whole (1,439 m2, 575 m2 grey); controls #0 / #1 only quoted | #0: 4,837 m2 retired, its 182 m2 grey corner kept; #1: 2,378 m2 retired whole (grey 0); #2: 810 m2 retired, the 625 m2 taxiway-F fillet kept. ADS-B all hours: 0 aircraft cells in any retired part |
| static-7 isolated edge dashes | builder post-pass: a piece < 15 m with no other edge within 10 m and a painted share <= 50 % is dropped (`edgeStats.isolated_dropped`) | edges 387 (243 (537,-274) 9.0 m, 327 (-570,-350) 4.7 m) | 386 (2 dropped, 14 m; +1 run on the kept F1 #2 fillet) |
| static-5 paths too wide on pale soil | `tools/build_landside.py`: `_profile` also returns the per-pixel channel spread; on non-asphalt ways the wide-road test needs spread < 22 per pixel (light soil is spread 25-40) and every station counts | 1182574236/5 5.75 m, 1182574227/4 6.0 m, 1182574229/3 8.5 m, 1182574227/40 4.25 x 18 m box; 11 pieces / 676 m2 with >= 15 % of the footprint at spread > 34 | 3.25 / 3.0 / 3.0 (bridged, inferred) m / not drawn; 7 pieces / 335 m2; flank-soil road pieces on non-asphalt ways 3 -> 0 |
| static-6 gap in the asphalt perimeter road | bridging: an undrawn inner stretch <= 400 m between two drawn pieces of one way is drawn along the OSM line when NAIP shows <= 5 % soil / vegetation / water on it (`w_src` inferred, narrower neighbour width) | 1182574242/14 92 m undrawn, 155476060/4 76 m | 1182574242/14 drawn 8.25 m (inferred); all OSM-asphalt undrawn stretches off other pavement 78 m, each <= 10 m |
| static-8 B-pier rotunda revert | `tools/stands/patch_stands.py` P6: Python port of gates.js `ownStrip` (the bridge's own walkway strip of a Museum ring is not building for that bridge); nearest-building search per ring | 31 P6 moves incl. the nine B-pier ones | 22 moves; the nine are exactly the revert table (373de34 values, P6 `fixup` gone); prepGeom shifts 0; summ 3,304 / 109 refused (unchanged) |
| static-9 rest poses / cab split | P10 (new): where the observed type at the stop is closer than its ICAO clearance, the rest pose is re-chosen among the build's candidates (`stow_src`), else kept with `stow_icao`: B11 L1 (at B11S) 4.6 -> 12.3 m from the B752, G8 L2 2.8 -> 4.5 m from the E75L; F14 / F17 / F19 / F21 L1 no compliant pose (kept, `stow_icao`). G3 L2's warning ends because SFO's 5 Nov plan moved UA1931 / UA581 (B738) to G7 / E13. `check_stands` / `geom.py`: optional cab split = gates.js (+-92.5 deg; was 150) | check.py rest WARNs 11; check_stands optional cab 150 deg vs gates.js 92.5 | rest WARNs 9 (F14 / F17 / F19 / F21 L1 B752, G13 L3 B772 remain: no pose found); one cab split in both; the 185 deg optional cab is still unsourced (open question). PARTLY |
| static-10 stand rules vs SFO / ADS-B | `FLYSFO_WINDOW2` = both local snapshots (4 Nov 18:01Z + 5 Nov 02:49Z, SFO's newer allocation wins); P2: a pair seen together by ADS-B inside a plan window is never excluded (`adsb_cooccupied`); P8 (new): `types_ok` widened by family dominance only where the planform clears the neighbours by 3 m (`types_ok_dominated_unsafe` lists the rest); D5 class from SFO's 02:49Z plan | F19 / F20 excl B772; C8 / C10 excl B752; F19 types_ok no B38M; D5 cls D (UAL649 B772 refused 06:55Z) | excl dropped (UAL2467 at F20 20:47-20:50Z inside F19's B772 window; C8 B752 + C10 BCS3 planned together 4 times); F19 types_ok + B38M / B752 / B772 (+ A19N ... E75S by P8); F20 unsafe list A19N / A20N / A319 / B37M / B736 / B737 (1.9-2.9 m from F19); D5 class E (B763, B772; UAL649 at D5's stop 0.4 m / -0.6 m off, 06:55-06:57Z 5 Nov) |
| static-11 stops vs antenna | P9 (new): per-family ADS-B antenna reference behind the nose (`antenna_ref.families`: median of parked stays at their stops, n, IQR) - E-Jet 13.6 m (19 stays / 11 stands), B737 9.2, A320 1.2, A220 5.4, CRJ 8.3, B757 17.1, B777 15.0 (12 / 7), B787 18.3 (3 / 3), A350 10.5 (2 / 2), B767 13.6 (1). `js/live/airport.js antennaRef(STANDS, minN)` exports them. The E-Jet ~7 m is the antenna offset (traffic.js 0.2 L = 6.3 m for an E75L vs 13.6 m measured), not the type stops: at their stops F7 / F8 E75L clear by 4.66 m (>= 4.5). D8: NAIP's painted lead-in lies 0.1 m from the data line; the ADS-B reports scatter -2.4 / -3.4 / -8.5 m - not moved | E-Jets 6.7-12 m short; no B777 / B787 / A350 reference; F7 / F8 4.38 m in the replay | per-family references in the data; the replay effect needs traffic.js to use them (request) |
| static-12 bridge-geometry residuals | P11 (new): A15 L1 walkway vertex moved 1.61 m out of the drawn outline (= the gates.js nudge, `walk_src` inferred). B2 / F9 L1 re-checked on NAIP 2024 0.5 m (the best open imagery; the Google screens are not in this container): the tunnels at rest are imaged parallel to the data stow lines but 2.6 m (B2) / ~4 m (F9) to the east and their roots merge with the facade shadow - the 1.3-2.1 m roof lean plus registration exceed the 1.45-2.40 m moves, so the drum position cannot be read; the P3 positions (minimal move clearing the outline) stay inferred | gates.js A15 nudge 1.6 m | gates.js A15 nudge 0 (data); B2 / F9 unchanged (recorded). PARTLY |
| static-13 flysfo-derived fields | owner decision OD-10; default kept (keep, snapshots local, replay committed); `flysfo_provenance.json` regenerated (108 / 108 stands; 72 P1 types, 3 also seen by ADS-B geometry); ATTRIBUTION row updated (second snapshot, P8) | - | DEFERRED (owner) |

check_stands WARN lines before -> after: - G3 L2 rest (B738), - G8 L2 rest (E75L); + A2 L2 / B789 extension 41.6 m
(within 1.0 m of 41.4), + B26 L1 / E75L extension 36.3 m (within 1.0 m of 36.2).

## R4.1 Realtime (traffic.js, ground.js, tools/live/**)

1. **Antenna references per family**: use `antennaRef(STANDS)` (js/live/airport.js; `{family: {m, n}}`, metres from the
   nose to the ADS-B position, families with n >= 5) instead of 0.2 L when placing a parked aircraft at its stop. E-Jet
   13.6 m vs 0.2 L = 6.3 m explains the "6.7-12 m short" E-Jets and the F7 / F8 4.38 m (their stops clear by 4.66 m).
2. **typesOkHas**: P8 now lists family-dominated members in `types_ok` only where they clear the neighbours by 3 m;
   `standGates` passes `typesOkUnsafe` ({ICAO: why}, F20) - typesOkHas should not admit those (or use exact membership).
3. `excl_types` F19 / F20 and C8 / C10 removed (ADS-B / SFO co-occupancy); F19 -> F18 blocks for B752 / B772 added (P2);
   D5 class E. The `exclTypeConflict` / `sfoStandRefused` events of R3.1 should go to 0.
4. `pavementRetiredParts` changed: F1 #0 / #2 minus their chart-grey parts; the old-J parts are gone (that island is
   paved, with green paint). `pavementRetired`: F1 #1 whole.
5. Off-pavement replay (your harness `tools/live/invariants.mjs`, stream SP/r3/all, frozen r3v code + this round's data,
   all hours; it still builds the OLD building grid): offpave.mask 1,375,584 -> 412,453 frames (377 -> 328 aircraft), offpave.union 471,479 -> 5,678 frames (237 -> 153); UAL2480's 369,812 frames are gone; 335,068 of the mask frames left are one parked GLF5 (N199TH, (-1138,-1171)) whose gear point lies 0.15 m beyond the apron edge on the fence line beside the service road (NAIP: fence / barrier, not pavement - pose, realtime); the worst union cells left: (-550,-350) 501 frames, (-550,-375) 202, (-600,-275 / -250) 138 / 121 (gear 1-3 m into the soil strip beside the runway exit at (-607,-269): corner cut), W (-350..-375, 275..300) 59-160 (the relocated W, unchanged). Classes that changed besides: excl-type-conflict 2 -> 0, sfo-stand-refused 1 -> 0
   (UAL649 B772 now in-block at D5), bridge.refused 19 -> 20 keys (+18,760 frames) / early-undock +1 with that new in-block; clear.stand unchanged
   (F7 / F8 E75L: needs item 1). The infield cells (25 m, centred as your offpaveCells): (-550,-350) NAIP 29 % soil (the island
   interior), (-600,-250 / -275) 12 % soil + a soil strip between the runway exit's shoulder and the taxiway - the gear points
   cluster 1-3 m into it at (-607,-269) for 10+ aircraft: the interpolated track cuts the corner (no pavement to add). N199TH
   (GLF5, parked 21:07Z on): its planform puts a gear point on the fence line north of the apron - please let GroundPhysics move
   stationary aircraft fully onto the mask (or check its heading); the apron is paved up to the fence.

## R4.2 Bridges (js/live/gates.js)

1. static-8 applied: the nine B-pier rotundas are back at the 373de34 (OSM) values; P6 = your ownStrip rule.
2. P10 rest re-choice: B11 L1 (at B11S) +0 deg turn to a pose 12.3 m from the B752; G8 L2 +10 deg (4.5 m from the
   E75L). F14 / F17 / F19 / F21 L1 keep their poses (`stow_icao`: no candidate clears the observed B752); F11 L2's B772
   refusal (rest over the wing) - please re-choose the rest per occupant (findings static-2 / static-9).
3. A15 L1: the walkway vertex is now in the data (P11, 1.61 m); your nudge should find nothing to move.
4. Optional cab: check_stands now uses your +-92.5 deg split; still no source for a 185 deg cab (open question).
5. F15 / G12 twin drums stay (NAIP: two tunnels per walkway end); the F15 L1 B39M neck geometry is yours.
6. Bridge makers / upper-deck units (A1 / A2 reach, A6 / A11 upper): owner decision OD-14.

## R4.3 Buildings / engine / lights / markings

1. Buildings: re-run `tools/blender/verify_domestic_r2.py` (B-pier drums back at the OSM positions, 0.4-1.2 m inward).
2. Owners of lights / signs / three.js bake: skip the `pavementRetiredParts` rings (F1 #0 / #2 minus grey) and
   `pavementRetired` (F1 #1); the old-J island is paved again and carries an inferred green-paint polygon (paint `src`).
3. Engine / 2-D extracts (js/three bake, jobs/extract2d.mjs): data/sfo_pavement grew 173.6 -> 209.1 ha (367 -> 284 polygons,
   merged); polygons carry `src` with the share from the round-3 rules (inferred). Re-bake / re-extract. The runway end zones
   (blast pads / EMAS) take no round-3 addition (the app draws them from END_ZONES).

## R4.4 Lead

1. Commit (tools/cache/sync.py): NEW `tools/imagery/adsb_ground_cells.py` and `refs/cache/stands/adsb_ground_cells.json`
   (own output from the committed adsb.lol hours, ODbL), the updated `refs/cache/faa/al375_2611_oldJ.json` (SOURCES.json
   note updated), `refs/cache/stands/patch_p1p2_replay.json`, `refs/cache/stands/flysfo_provenance.json`.
2. Owner decisions unchanged: OD-10 (flysfo-derived fields; now also the 5 Nov 02:49Z snapshot), OD-14 (bridge makers).

# Round 3, fix round 2 (static, 2026-11-08): verifier findings v1 ... v9

Answers the round-1 verifier's nine findings (task text of close-out round 3, fix round 2). Nothing hand-edited; every data
file comes from its generator and a second run is byte-identical (stands `--replay` twice: md5 f590e3d6..., `--check`
MATCH (55 stands; final md5 336c590a...); landside twice: 1216ca2d...; paint / pavement: a second run md5-identical, pavement.json 78705958...,
paint.json 68471e21...). Before = the data
committed at the start of this round (= fix round 1). Checks: `tools/stands/check_stands.py` (= `tools/sat/check.py` /
`check_bridges.py` output) ISSUES 0 -> 0, APP 0 -> 0, WARNINGS 17 -> 20 with the WIDER rest test of v7 (the same test on
the old data: 41); bridges summary (vb3 `summ.mjs` on the current gates.js): 3,335 / 3,413 planned -> 3,333 / 3,411 (the two
removed P8 types), refusals identical (78), rotShifted 0, walkNudge [].

| Finding | Change | Before | After |
|---|---|---|---|
| v1 (major) P9 / P2 not reproducible | `tools/stands/patch_stands.py`: `REC_HOURS` pins the adsb.lol hours P2's co-occupancy and P9's antenna reference read = the 36 complete hours when P2 / P9 were first run (4 Nov 17Z - 6 Nov 04Z; a missing hour is an error, a new hour changes nothing until added); `antenna_ref.hours` lists them; airport.js comment says so | every `rec_pack` file read (36 h then, 65 h now): reruns gave EJET 13.0 m n 37, B787 16.6 m n 8 (would cross traffic.js's n >= 5 gate) ... | the pinned list reproduces the committed `antenna_ref` exactly (md5 d89d5e85 = committed, before the v6 / v7 changes); values unchanged (EJET 13.6 n 19, B737 9.2, A320 1.2, A220 5.4, B757 17.1, CRJ 8.3, B777 15.0; B787 18.3 n 3 stays below the gate). Kept at 36 h on purpose: the 65 h values above change parked-aircraft placement in traffic.js (B787) - a re-pin is the realtime track's call (request R5.1.3) |
| v2 OSM buildings / end zones paved by hole fill / smoothing | `tools/imagery/paint_pave_naip.py`: the shaping steps run on the pre-round-3 pixels too (`p_old`); OSM building footprints (not `building=roof`) and `END_ZONES` are never filled as holes or grown into by the gaussian step, and at the end they keep exactly `p_old` (`p = (p & ~excl) \| (p_old & excl)`), so the round-3 / fix-2 rules add nothing there | vs the round-start pavement (verifier's pv1.py): added on OSM buildings 1,353 m2 (way 1473685129 paved whole, 1,314 m2; a 28 m2 one at (-1028,1191)); added in end zones 907 m2 (323 m2 in the 1L EMAS zone) | added on OSM buildings 6 m2 (polygon simplification), pavement on OSM buildings 12,724 m2 (round start 12,722); added in end zones 51 m2 (simplification; zone total 24,927 vs 24,917). FIXED |
| v3 unpaved holes where aircraft taxi | rule (f): holes ENCLOSED by the paved union (pavement, SFO Museum pavement / apron, buildings, OSM buildings, end zones) that hold an adsb.lol aircraft ground cell (>= 2 fixes) or a vehicle stay, NAIP <= 5 % soil + vegetation, <= 20 % water-blue, >= 60 % grey, < 12000 m2 (the parking-point hole limit) are pavement (inferred, `src` share) | verifier holes.py: enclosed holes with aircraft fixes 37 (round start, 1,723 fixes) -> 9 (117) after fix 1, worst (-405,-967) 4,285 m2 / 35 fixes, (-1426,-252) 456 / 36, (-723,-316) 378 / 9; criterion cells < 90 % paved 168 -> 28, < 50 % 26 -> 0 | 6 holes / 37 fixes left: (-1345,693) 1,978 m2 / 17 and (-932,-257) 876 / 12 are not holes of the generator's union (no hole within 58-61 m in its masks: they are closed only by layers it does not read - landside paths / roads), (-1435,-1) / (-1495,-31) hold 3 single fixes each (no cell with >= 2) and are 4 % grey + smooth, (-2114,-748) is a 6.5 ha infield (1 fix), (-369,350) 4 % grey (the relocated W area, paved by its osm_update buffer); 6 holes filled, +0.50 ha; criterion cells < 90 % paved 21 (< 50 %: 0). ARFF R41 disc: unchanged (511 m2 paved; the unpaved remainder is the station roofs plus ~60 m2 of stripe gaps in the tan, striped bays - tan concrete reads as soil by colour (R - B > 38) and the stripes fail the texture test; a closing of the stripes adds ~60 m2 only; a vehicle footprint stays ruled out). PARTLY |
| v4 landside pieces on soil | `tools/build_landside.py`: (1) a light band on a non-asphalt way whose CORE is soil-coloured (median per-pixel channel spread >= 22 over its central 1 m) is not a path (light segments broken by soil / grass: 1157838876 core medians 28-33, b* 12-14); (2) the asphalt wide-run test also needs per-pixel spread < 34 (soil verge 37-65); (3) `footprint_fix`: a drawn piece with > 15 % of its footprint at per-pixel spread > 34 (the verifier's measure) is narrowed in 0.25 m steps (>= 1.75 m) or not drawn | pathfoot: 7 pieces / 335 m2 with >= 15 % footprint at spread > 34 (1157838876 /1 /3 /8 /11, 1182574227 /28 /48, 1182574212 /1); drawn 344 pieces, 28.58 km | 0 pieces (drawn footprint 1.0 % at spread > 34, was 1.2 %); drawn 337 pieces, 28.13 km: not drawn 1157838876 /3 /4 /6, 1182574211 /1, 1182574227 /23 /50 (soil-coloured band / footprint); narrowed 1182574212 /1 2.50 -> 2.00 m, 1182574227 /30 (the old /28 box) 6.62 -> 4.37 m. Perimeter road 112508632 widths unchanged. The flank criterion "flank b* > 12" is NOT met and is rejected as a test for this road: on the same NAIP profiles the dusty asphalt itself (o -5..0 m, parts 20 / 21 / 23 / 26) has per-pixel spread 23-32 and b* 10-14, so a flank test outside the 1.5-2 m light strip flags the asphalt lanes (crops f2/land/c_p23s.png, c_p26.png). What is left: on parts 21 / 23 the run extends 3-4 m beyond the light edge strip on the water side over a grey-brown fringe (spread 13-27, b* 8-11, grey 160-185 - not separable from the dusty asphalt by colour or 3 m texture at 0.6 m) - open (residual, inferred widths). PARTLY |
| v5 old-J island interior | rule (g): the part of the FAA AL-375 2611 chart island (`white_polys`) that is neither SFO Museum taxiway pavement, paint nor pavement is paved (concrete, inferred; NAIP 2024 predates the rebuild: the pale interiors inside the painted rings, median RGB 199/207/183, unpainted - so paved, not painted) | chart island 5,575 m2: 4,653 paved / 922 unpaved (17 %), largest 361 m2 at (-328,102) | 5,449 paved / 126 unpaved (2 %: polygon simplification; the raster covers it), +1,526 m2 of raster. FIXED (inferred) |
| v6 F19 / F20, C9 / C11 clearances | P8 threshold: an added (family-dominated) type must clear every stand within 120 m by the ICAO stand clearance of ITS code, or - where a listed type of the same family that dominates it already sits closer to that neighbour - by that listed type's clearance (never < 3 m); tested against the neighbours' FINAL envelopes until nothing more drops (order-free). ADS-B / NAIP re-check of the poses below | P8 at 3 m: F19 + B77L (3.02 m from F20's A320), C11 + B737 (4.44 m from C9's B762, < code C 4.5); pair notes F19\|F20 3.0 m, C9\|C11 4.4 m | F19 B77L (6.1 m from F18, ICAO 7.5) and C11 B737 (4.4 < 4.5) now `types_ok_dominated_unsafe`; F19\|F20 4.3 m (B77W / B752, both observed), C9\|C11 5.1 m (B762 / B736). Re-check (adsb.lol, pinned hours, f2/copark.py): the axes hold - F19 stays lateral -0.2..-0.7 m, heading +0.3 deg (UAL1020 / UAL626 / UAL589); F20 lateral -0.1..+0.5 m, +0.4 deg (UAL2467 / UAL1372 B752, UAL216 A320); C9 / C11 lateral <= 1.1 m, heading <= 2.6 deg. The co-parked pair (UAL2358 B772 at F19 20:16Z + UAL2467 B752 at F20 20:48Z, 4 Nov) is 7.28 m apart in the model at the stops; the B772's last fix sits 27.1 m behind F19's model nose (B777 reference 15.0 m, IQR 11.9-21.1) and the B737-family stays 6.6 m behind their (inferred) type stop - both further from the terminal, which INCREASES the separation from F20 (B772 / B752 7.28 -> 8.35 m, B77W / B752 4.31 -> 12.18 m with a 12 m shift): the poses are not drawn too close; the stops are not moved (n 1-3 stays, per-airframe antenna offsets of the same order). NAIP 2024 does not resolve the F19 / F20 lead-ins from the stained concrete (b* crop f2/yel_f19.png); the 26 Sep build's F19 paint residual (lateral -4.25 m, -16.4 deg) matches F18's line (20 deg off F19's axis), not F19's (inferred). FIXED (P8) / re-check recorded |
| v7 rest poses vs observed types only | P10 and check_stands test the rest pose against every type a stand within 150 m ACCEPTS that stays parked while the bridge rests (neighbours; own-stand types the bridge does not dock, e.g. an L2 beside a narrow-body), besides the observed ones; P10 also keeps a re-chosen pose clear of the other bridges' rest poses / fixed parts (> 0.5 m2, check_stands' tests) and never further AFT along the own stand's axis than the present rest (the all-hours replay showed why: a first version turned G4 L2 +43 deg aft into UAL917 B772's pushback tail swing, 5 Nov 06:54Z - 378 hit points on the cab vs 47 before) | same test on the old data: 41 WARN (24 bridges, e.g. G3 L2 2.8 m from a B752 / 1.8 m from a B738, G12 L2 1.0 m from a B736) | rest poses turned to keep the ICAO clearance (inferred, `stow_src`): A2 L2 +0 (shorter), A6 L2 -1, A8 L2 -2, A9 L2 -21, A10 L2 -4, B4 L1 +2, F12 L1 -20, F15 L2 +2, F22 L2 +3, G1 L2 +0, G2 L2 +95, G3 L2 +104, G4 L2 +75 (G2-G4 L2 now lie along the facade, 21-35 m off the axis), G5 L2 -16, G6 L2 -6, G7 L2 +4, G8 L2 +20 (round 1 +10), G9 L2 +0, G10 L2 +0, G12 L2 +11, G13 L2 -3 deg; WARN 20: F14 / F17 / F19 / F21 L1 (observed B752 at the own stand while it taxis in), G13 L3 (upper deck, observed only), A5 L2 / A11 L2 (B752 accepted) and B15 L1 (B762 at B16S accepted) - no compliant pose that is not further aft (`stow_icao`). The +-92.5 deg optional-cab source stays an open question. FIXED (data) / per-occupant rest = request R5.2 |
| v8 refused (bridge, type) pairs | no static change: F15 L1 neck x walkway (9 types), F11 L2 rest per occupant (B772 / B788 / A332), A6U / A11U A388 extension, dock_types_out are the bridges track's and the owner's (OD-14); B2 / F9 drum positions need the owner's screenshots. NAIP shows two tunnels per walkway end at F15 / G12 (twin drums kept) | 78 refusals | 78 refusals, identical list (P10's 24 new rests refuse nothing). DEFERRED (bridges / owner) |
| v9 pavement provenance | `note`, `provenance`, new `licence` and the `.js` header of `data/sfo_pavement.*` name rules (a)-(g), the OSM-building / END_ZONES exclusion and the ODbL inputs (OSM, adsb.lol: "Contains information from OpenStreetMap and adsb.lol, made available under the ODbL"); paint gets its own provenance and a header naming FAA AL-375 / SFO Museum (CDLA, change notice); ATTRIBUTION rows (ADS-B hours, landside, pavement) updated | provenance ended at "static close-out 2026-11-04"; .js header "from USDA NAIP 2024 (public domain)" | FIXED |

## R5.1 Realtime (traffic.js, ground.js, tools/live/**)

1. `types_ok_dominated_unsafe` grew (P8's ICAO rule): F19 B77L (6.1 m from F18's envelope), C11 B737 (4.4 m from C9's,
   code C 4.5 m); F20's list unchanged. `typesOkHas` already honours `typesOkUnsafe`. Please refresh the comment above
   `typesOkHas` (it names F20's list only) - data only, no code change needed.
2. `antenna_ref` is now reproducible: P9 reads the 36 hours pinned in `patch_stands.py` `REC_HOURS` (listed in
   `antenna_ref.hours`); the values are unchanged, so `ANT_REF` behaves as before. The `ANT_REF` comment ("36 committed
   adsb.lol hours") is right; please add "pinned (REC_HOURS)".
3. Re-pin decision is yours: all 65 complete hours (to 8 Nov 03Z) would give EJET 13.0 m (n 37), B737 9.0, B777 14.5,
   CRJ 6.7 (n 7), B757 17.2, A350 8.7 (n 3), and B787 16.6 m with n 8 (it would pass your n >= 5 gate and move parked
   B787s from 0.2 L to 16.6 m). Say so and the static track adds the hours to `REC_HOURS` (one line) and re-runs.
4. F19 evidence (not moved, n too small): the B737-family stays stop ~6.6 m and UAL2358 B772 ~12 m further from the
   terminal than F19's drawn stops (antenna references 9.2 / 15.0 m); `antPark()` places parked aircraft from their own
   reports, so this affects the static checks only.
5. Pavement changed slightly vs fix 1 (+0.65 / -0.28 ha; the north cargo taxilane hole at (-405,-967) is paved; OSM
   buildings / end zones are back at their pre-round-3 pavement). All-hours replay on the frozen r3v code: see R5.4.

## R5.2 Bridges (js/live/gates.js)

1. P10 re-chose 21 more rest poses (v7: every accepted type parked while the bridge rests, not only observed ones; never
   further aft than before): A2 / A6 / A8 / A9 / A10 / F15 / F22 / G1-G10 / G12 / G13 L2, B4 / F12 L1 (angles in the table).
   The vb3 summary on the current gates.js shows no new refusal (3,333 / 3,411 planned); please re-run your own checks
   (bcheck2, slopes, ownclip) on the new `stow` values.
2. No compliant STATIC rest exists for F14 / F17 / F19 / F21 L1 (observed B752 at the own stand, arrival transient),
   A5 / A11 L2 (B752 accepted) and B15 L1 (B762 at B16S): please choose the rest per occupant (e.g. retract an L2 fully when the occupant does not use it)
   - also F11 L2 for B772 / B788 / A332 (every docking path from its rest passes through the aircraft) and the F15 L1 neck
   (verifier v8).
3. The +-92.5 deg optional-cab split still has no source (open question to the owner, unchanged).

## R5.3 Engine / extracts

1. `data/sfo_pavement.*` 284 -> 285 polygons, 209.1 -> 209.5 ha (classified area; fix-2 additions tagged in `src`);
   `data/sfo_landside.*` airside paths 344 -> 337 drawn pieces. Re-bake / re-extract.

## R5.4 Lead

1. Commit: `tools/stands/patch_stands.py`, `tools/stands/check_stands.py`, `tools/imagery/paint_pave_naip.py`,
   `tools/build_landside.py`, `js/live/airport.js` (comments), the regenerated `data/sfo_stands|pavement|paint|landside.*`,
   `docs/ATTRIBUTION.md`, this file. No `refs/cache` file changed (`patch_p1p2_replay.json`, `adsb_ground_cells.json`
   md5-identical).
2. Owner questions unchanged: OD-14 (bridge makers / upper-deck units), the B2 / F9 screenshots, the 185 deg optional cab.
