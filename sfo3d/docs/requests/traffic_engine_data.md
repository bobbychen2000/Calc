# Requests from the real-time traffic workflow (traffic engine, step 2) — 24 Sep 2026

From: real-time workflow (owner of `js/live/traffic.js`, `ground.js`, `feed.js`, `app.js`, `ui.js`, `stats.js`,
`sfo_live_server.py`, `tools/live/**`). All evidence below is from the replay of the real recording
(`refs/cache/rec`, 24 Sep 15:13–16:45Z) through the app's engine (`sh tools/live/replay_engine_all.sh`); positions are in
the world frame `ltp-nad83-2011` (ADS-B through `wgs84ToWorld`).

## 1. New file in `data/`: `data/sfo_taxigraph.js` (for the static workflow — please take it over or tell me where)

I created one new generated file, `data/sfo_taxigraph.js`, because the engine needs the OSM taxi network at run time
and the relay does not serve `tools/`. Nothing else in `data/` was touched.

- Generator: `python3 tools/live/build_taxigraph.py` (reads `refs/cache/osm/ksfo_osm_parsed.json`, osm_base
  2026-09-24T09:07:42Z). Contents: 244 OSM `aeroway=taxiway/taxilane` ways as 3,876 centreline segments, the four runway
  centrelines from the FAA ends, 18 `aeroway=apron` rings, 287 `aeroway=parking_position` lead-in lines (stop point and
  parked heading). WGS 84 → `geo_frame.wgs84_to_world`.
- Licence: ODbL 1.0, © OpenStreetMap contributors; the file header says so and `js/live/about.js` credits it.
- The app loads it with a guarded dynamic import (`js/live/entry.js`), so the file can move or be regenerated; if you
  rebuild the OSM extract, please re-run the generator. If you would rather own it under a different name, tell me.

## 2. Pavement gap: the north cargo apron (for the static workflow: `data/sfo_pavement.*` / `airport.js` mask)

Three aircraft parked for the whole window on an apron that is neither in the rendered pavement mask nor in any OSM
`aeroway=apron` polygon, so their gear is "off pavement" in every frame (and GroundPhysics refuses to push them further
than their report scatter, as the audit asks):

| Aircraft | Type | Median antenna position (x, z) m | Reported heading |
|---|---|---|---|
| KAL214 | B748 | (−1243, −2169) | see `refs/cache/replay_day3/events.txt` |
| CSB805 | B762 | (−1131, −2038) | idem |
| EVA629 | (see events.txt) | (−1028, −1870) | idem |

This is ~2 km north of the ARP (the cargo area north of the 10/28 runways). Please add the paved area there (from the
imagery pipeline) — the engine will then count them as on pavement without any change on my side. It is the single
largest source of off-pavement frames in the metrics (≈ 85 % of them).

## 3. Stand survey: evidence from reported true headings and SFO's allocation (for the stands rebuild)

The engine parks an aircraft on the surveyed lead-in line when its reported heading agrees within 8° and it is within
6 m laterally; otherwise it uses the aircraft's own median pose (and falls back to the stand pose if that would hit a
building). Cases where the data and the survey disagree (observed 24 Sep):

| Stand | Evidence | Detail |
|---|---|---|
| E4 | UAL488 (B38M, SFO plan E4) stopped with true heading ~312–329° | survey 284.9° (pos_src osm): 30–45° off; the reported pose puts the nose in the building mask, so the engine falls back to the stand pose |
| F17 | UAL1845 (B39M, SFO plan F17) | the stand's stop point (nose) lies inside the building mask for a 42 m aircraft on the lead-in; the aircraft really stopped ~17 m short of it (type-specific stop mark) |
| C10 | ACA738 (BCS3) reports 320.6° | survey 298° (audit F7, confirmed again 15:13–15:38Z) |
| B13/B14 | FFT3435 (A21N, SFO B14) and ASA526 (B39M, SFO B13) | no conflict found in the survey itself; listed because they were adjacent in the overlap metrics (the cause was on my side and is fixed) |

The rebuilt stand records' `aodb`, `gate`, `excl` and `alt_of` fields are already used by the engine
(`traffic.js prepGates`): AODB names for matching SFO's allocation, `excl` to block mutually exclusive stands (MARS).

## 4. Relay aircraft database fields (my own file, FYI)

adsb.fi and adsb.lol can hold different types for one airframe (C-FDUW: BCS3 vs BCS1); the relay now takes
database fields from adsb.fi when it has them, and the engine only changes a type after 5 consistent reports.
