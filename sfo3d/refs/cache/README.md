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

Agents saving a third-party file here record it in a `SOURCES.json` beside it:
`{"<file or glob>": {"url": "...", "licence": "..."}}` — only an open licence (public domain, CC0, CC-BY(-SA), ODbL,
GPL, ...) lets an image, document or fetched page be committed.
