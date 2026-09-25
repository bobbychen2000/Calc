# Data sources and required attributions

Which third-party data the shipped app and the committed data files contain, under which terms, and the notice each
one requires. Quotes were read on 24 Sep 2026 from the pages named (local copies under `refs/cache/`, gitignored).
Not legal advice; the owner decides.

## Notices to show in the app (About / credits panel) and in any distribution

> Taxiway centreline, holding-position, stand, jet-bridge and parking-position data © OpenStreetMap contributors,
> available under the Open Database License (ODbL 1.0) - https://www.openstreetmap.org/copyright
>
> Airport geometry: SFO Museum, sfomuseum-data-architecture (CDLA-Permissive-1.0)
>
> Measurements on imagery, green paint and extra pavement: USDA NAIP 2024 (USDA Farm Production and Conservation
> Business Center, Geospatial Enterprise Operations) - public domain
>
> Runway, lighting and airport data: FAA National Airspace System Resources (NASR), cycle 2026-09-03; FAA Airport
> Diagram AL-375 - U.S. Government works
>
> Stand names: San Francisco International Airport (DataSF dataset chfu-j7tc, PDDL; flysfo.com)

## Per source

| Source | Where it is used | Terms (quoted) | Obligation |
|---|---|---|---|
| **OpenStreetMap** (Overpass download 24 Sep 2026, `refs/cache/osm/`) | `data/sfo_stands.json` / `.js`: stand positions and headings (OSM `aeroway=parking_position`), lead-in polylines, jet-bridge geometry (`aeroway=jet_bridge`), unnamed parking positions; built by `tools/stands/build_stands.py`. `data/sfo_details.json` / `.js`: taxiway centrelines (`aeroway=taxiway` ways, 264 lines, locally moved onto the NAIP paint) and the direction / position of 1 holding position (`aeroway=holding_position`); OSM holding positions also serve as locators for 10 holds whose bars are measured on NAIP (review round 2); one centreline (E-W crossing of 1L/1R) is traced on NAIP where OSM has no way; the 70 apron / landside floodlight masts (`man_made=mast` + `tower:type=lighting` nodes; review round 3, before: inferred positions); built by `tools/build_airfield_details.py`. `data/sfo_taxigraph.js` (realtime workflow, `tools/live/build_taxigraph.py`) is also OSM-derived. | "You are free to copy, distribute, transmit and adapt our data, as long as you credit OpenStreetMap and its contributors. If you alter or build upon our data, you may distribute the result only under the same license." / "Where you use OpenStreetMap data, you are required to do the following two things: Provide credit to OpenStreetMap by displaying our attribution notice. Make clear that the data is available under the Open Database License." (https://www.openstreetmap.org/copyright) | Each of these files is a Derivative Database (more than 100 features; OSMF Substantial guideline) and is offered under **ODbL 1.0** (notice in the file headers; `licence` / `attribution` fields in the JSON). Show the credit in the app (Produced Work, ODbL §4.3). Offer the database or the method of making it (§4.6): the files themselves plus `tools/stands/`, `tools/build_airfield_details.py` and `tools/xcheck/fetch_osm.py`. They contain no Google-derived content, which keeps share-alike possible. |
| **USDA NAIP 2024** (`refs/cache/naip/`, docs/research/imagery.md) | `data/sfo_paint.*` (green no-taxi paint) and `data/sfo_pavement.*` (extra pavement) classified from NAIP colour by `tools/imagery/paint_pave_naip.py`; holding-position bars, taxiway-centreline corrections and (review round 3) the taxiway edge lines snapped onto the painted double yellow line in `data/sfo_details.*` (`tools/build_airfield_details.py`, `tools/imagery/paintline.py`); stand nose calibration, painted lead-in corrections (C4, D14), red equipment boxes (`redBoxes`, colour detection + oriented-square template fit, `tools/stands/redboxes_naip.py`), EMAS and blast-pad dimensions in `js/live/airport.js`; approach-light structures of 28L / 28R (`APPROACH_STRUCTURES` in `js/geo.js`, `tools/imagery/als_naip.py`). No NAIP pixels are committed. | data.gov: "License: https://www.usa.gov/publicdomain/label/1.0/"; USDA FSA: "Public domain information may be freely distributed or copied, but use of appropriate byline/photo/image credits is requested"; USDA image service: "The Farm Production and Conservation Business Center (FPAC-BC) Geospatial Enterprise Operations (GEO) Branch asks to be credited for derived products." | credit requested (notice above); do not imply USDA endorsement |
| **FAA** NASR APT CSV (cycle effective 2026-09-03), Airport Diagram AL-375 (2609) | `js/geo.js` RWY_ENDS, APPROACH_LIGHTS, PAPI, TDZ_LIGHTS; `js/world/airfield.js` runway axes | U.S. Government works (17 U.S.C. §105) | none required; credit given as courtesy |
| **SFO Museum** sfomuseum-data-architecture | `data/sfo_airport.*`, `sfo_buildings.*`, building outlines used in the stand checks | CDLA-Permissive-1.0 | attribution (already in `data/sfo_airport.json`) |
| **SFO / DataSF** chfu-j7tc | official gate numbers | PDDL (dataset metadata) | none |
| **flysfo.com** flight-status feed | AODB stand names in `data/sfo_stands.json`; offline verification only | no published terms (docs/research/gate_truth.md §7) | names only; no live dependency without SFO's permission |
| **ADS-B**, own recording | `data/sfo_stands.*`: verification residuals (`resid.adsb`, `verified_by: adsb`), `conflict`, per-family stop offsets (`type_stops`), the SFO-named remote stand positions - derived from **adsb.lol only** (`tools/stands/adsb_parked.py` reads only `refs/cache/rec/adsblol_*`; every stay records `prov`). adsb.fi data is NOT used in any published data file (review round 2: before, stays mixed both providers without provenance). | adsb.lol: "The license for the API as well as all data ADSB.lol makes public is ODbL" (docs/research/realtime_feeds.md §3.1). adsb.fi: "You may not license, sell, rent, or lease any part of the data or the service" (realtime_feeds.md §3.2) - incompatible with the ODbL stand file. | adsb.lol: ODbL attribution ("Contains information from adsb.lol, made available under the ODbL"); the stand file is ODbL anyway. adsb.fi: credit in the app for the live feed only; ask adsb.fi before any adsb.fi-derived record is published. |
| **ICAO** Doc 9157 Part 2 | clearance values quoted in tools/docs only | ICAO copyright | quote only |
| Google Maps screenshots | **not used** for any shipped data file (checked 24 Sep 2026, review round 1: `data/sfo_paint.*` and `data/sfo_pavement.*`, which until then were frame-migrated screenshot classifications, are now classified from NAIP). The screenshot-derived feature coordinates (`stand_defs.py`, `work/redboxes.json`, `pave_add.json`, `faces.json`, the frozen paint/pavement polygons) were moved out of the repository into the gitignored `refs/cache/sat_legacy/`; the legacy scripts in `tools/sat/` write only there. Still in the repository: `tools/sat/work/reg.json` (screenshot-to-world registrations, no feature coordinates) and the git history of the removed files. | licensed imagery | outputs containing their pixels or coordinates stay in `out/` / `refs/` |
| X-Plane Scenery Gateway | cross-check only (`tools/xcheck/`), nothing copied into `data/` | GPL v2 or later | none while unused |

## Every shipped data file

| File | Content | Sources (licence) | Generator |
|---|---|---|---|
| `data/sfo_airport.*` | runways, taxiways, terminals, structures (outlines) | SFO Museum (CDLA-Permissive-1.0) | `tools/build_sfo_airport.py` |
| `data/sfo_buildings.*` | terminal building parts | SFO Museum (CDLA-Permissive-1.0) | `tools/build_terminal_parts.py` |
| `data/sfo_details.*` | taxiway centrelines, holding positions, inferred apron, edges (SFO Museum outline snapped to NAIP paint), masts (OSM), road lines | OSM (ODbL 1.0), USDA NAIP 2024 (public domain), SFO Museum (CDLA-Permissive-1.0). No ADS-B data: the 45 m `patches` that paved wherever an aircraft of `data/snapshot.js` (adsb.fi + adsb.lol) stood were removed in review round 3; the snapshot is read only for a debug image in `out/` | `tools/build_airfield_details.py` |
| `data/sfo_stands.*` | contact stands, lead-ins, jet bridges, remote stands, parking positions, red boxes | OSM (ODbL 1.0), NAIP (public domain), SFO / DataSF names (PDDL), own ADS-B recording of adsb.lol (ODbL 1.0) only | `tools/stands/build_stands.py` |
| `data/sfo_paint.*` | green no-taxi paint polygons | USDA NAIP 2024 (public domain) | `tools/imagery/paint_pave_naip.py` |
| `data/sfo_pavement.*` | paved areas not in SFO Museum (shoulders, aprons, service roads) | USDA NAIP 2024 (public domain) | `tools/imagery/paint_pave_naip.py` |
| `data/sfo_shore.*` | airport shoreline (land / Bay water; review round 3) used by `js/world/terrain.js` | USDA NAIP 2024 near-infrared (public domain) | `tools/imagery/shore_naip.py` |
| `data/sfo_taxigraph.js` | taxi routing graph (realtime workflow) | OSM (ODbL 1.0) | `tools/live/build_taxigraph.py` |
| `data/lookup.js` | airline / type names (realtime workflow) | Virtual Radar Server standing data (see its header) | - |
| `data/snapshot.js` | recorded ADS-B snapshot + METAR | adsb.fi / adsb.lol, NOAA (see docs/research/realtime_feeds.md) | - |
| `data/models/*` | aircraft models (aircraft workflow) | see `data/models/manifest.json` | `tools/convert_models.py` |
