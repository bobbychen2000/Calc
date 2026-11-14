# Re-verify (data) scripts, 2026-11-14

Report: `docs/phase1/reverify_data.md`. Independent checks of the QA C1 fix round 1 (`docs/phase1/qa_data.md`). The
scripts print counts, stand names and graph link numbers only. They never print dropped (sensitive) element ids,
names or positions, and never print AIP values: the AIP comparisons read the local mirror at run time.

Run from a scratch directory with `python3 -I`. Some scripts write small JSON files into the current directory.

| Script | Checks |
|---|---|
| `chain.sh ROOT LOG`, `md5set.sh ROOT` | Re-run the whole builder chain on a scratch copy of `sha3d/`, then md5 every output |
| `rv_route.py TAXIGRAPH AIRPORT STANDS` | H2 / M5 / M6. Edge-based router whose turn rule comes from the link geometry, not from `turns`. Checks one-way, use, runway crossings off the AIP list and own lead-ins. Compares with the committed turn table and gives reachability at 90 deg and 100 deg |
| `rv_route_dbg.py`, `rv_dep14*.py` | Pairs that only the table allows; short spikes at link ends; why 14 stands cannot depart |
| `rv_sens.py SHA3D`, `rv_sens2-4.py SHA3D` | H1 and the new N1. Areas, lines and points that the tag rule drops, compared with every kept feature of the pinned extract and the data files |
| `rv_kw.py REPO LIST` | Sensitive keywords and per-flight patterns in every committable file |
| `rv_aip_struct.py SHA3D`, `rv_aip_tokens.py SHA3D LIST` | M2. AIP-labelled fields outside the notice blocks, and distinctive mirror tokens in committable files |
| `rv_stands.py SHA3D`, `rv_stands2.py SHA3D` | M3 / M4 / M5 / L4 / L6. Nose and heading against the OSM data, own planforms at reference size, class max and `span_max`, buildings, bridges, push, pavement, local AIP class counts |
| `rv_s2.py SHA3D` | M8. Committed Sentinel-2 rasters against the extent polygon |

`LIST` is the committable file list: `git ls-files sha3d` plus `git ls-files --others --exclude-standard sha3d`. The
pinned extract is added by the scripts.
