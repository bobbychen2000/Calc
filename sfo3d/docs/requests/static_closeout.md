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
