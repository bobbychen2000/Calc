# Fix round 2 checks (re-verify N1-N5)

Scripts used to show the fixes of fix round 2 (`docs/phase1/qa_data.md`, section "Fix round 2"). Run them with
`python3 -I` from any directory. They print counts, stand names and graph link numbers only: no dropped (sensitive)
element ids, names or positions, and no AIP values.

- `sens_n1.py SHA3D_DIR` (N1): applies the tag rule (`tools/law/osm_sensitive.py`) to the raw tiles (local only) and
  checks the committable pinned extract and `data/sha_airport.json` `context.rail` against the dropped lines, areas and
  points: railway points within 30 m, other tagged points within 2 m of a line, non-passenger railway within 100 m,
  railway ways sharing a node with a dropped railway, features running >= 25 m along a line (within 10 m and 30 deg),
  kept ways sharing vertices with a line (0 expected since fix round 3, rule g of `pin_extract.py`; and the longest
  stretch ON a line), and `osm_elements.json` nodes that belong to no kept feature or only to dropped ones.
- `dep14_options.py` (H2 side effect): the two Phase-3 options for the 14 T2 stands without a departure under the OSM
  one-way tags (push on along the lane; soft one-way rule with 15 / 30 / 50 m), on the independent router of
  `tools/verify/reverify_data/rv_route.py`.

Other checks used in fix round 2 (unchanged scripts): `tools/verify/reverify_data/rv_sens.py`, `rv_sens3.py`,
`rv_route.py`, `rv_route_dbg.py` (the 0.3 m spike on H1), `rv_dep14*.py`, `rv_aip_tokens.py`, `rv_kw.py`, `chain.sh`,
`md5set.sh`; `tools/verify/qa_c1/twy_offset.py` (Umbra residuals by the QA method) and `fix1/aip_check.py`.
