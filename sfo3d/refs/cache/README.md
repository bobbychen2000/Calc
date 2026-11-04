# refs/cache — downloads and recordings

Gitignored as a directory; `tools/cache/sync.py` commits (`git add -f`) the files we may redistribute in this PUBLIC
repository and lists every other file, with its SHA-256, in `refs/MANIFEST.json`. `tools/cache/restore.sh` rebuilds
what can be rebuilt after a container loss (NAIP, the ADS-B hours, workflow journals).

Committed third-party data and its attribution:
- `rec_pack/` — ADS-B positions trimmed to 25 nm / 18,000 ft of SFO. Contains information from ADSB.lol
  (https://adsb.lol), which is made available here under the Open Database License (ODbL 1.0,
  https://opendatacommons.org/licenses/odbl/1-0/). adsb.fi recordings are NOT committed (adsb.fi terms: personal,
  non-commercial use).
- `osm/` — © OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright).
- `naip/` provenance and previews — USDA Farm Service Agency NAIP (public domain).
- `lighting/`, `faa/`, `weather/`, `bts/` — US government works (FAA, NOAA, US DOT BTS).
- `xplane/` — X-Plane Scenery Gateway data (GPL, as published by the Gateway).
- `buildings/**/verify/wof/*.geojson` — SFO Museum Who's On First architecture data
  (https://github.com/sfomuseum-data/sfomuseum-data-architecture), Community Data License Agreement – Permissive 1.0.
- `buildings/**/src/*wiki*` — Wikipedia article text as fetched (URLs in the `SOURCES.json` beside each file), by
  Wikipedia contributors, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/); these copies stay under
  CC BY-SA 4.0.
- `commons_photos.json`, `review_likeness/manifest.json` — Wikimedia Commons metadata (structured data CC0) listing
  each photo's author and licence; the photos themselves are kept local (reference only, never textures).

Agents saving a third-party file here record it in a `SOURCES.json` beside it:
`{"<file or glob>": {"url": "...", "licence": "..."}}` — only an open licence (public domain, CC0, CC-BY(-SA), ODbL,
GPL, ...) lets an image, document or fetched page be committed.
