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
