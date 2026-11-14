# Fix round 1 checks (QA C1)

Scripts used to show the fixes of fix round 1 (`docs/phase1/qa_data.md`, section "Fix round 1"). Run them like the QA
scripts: copy `tools/verify/qa_c1/` to a scratch directory and run with `python3 -I`. They print counts only.

- `route_edge.py` (H2, M6): the QA route sets of `graph_qa2/3.py` and `rwy_use.py` routed edge-based on the committed
  turn table (`turns`), with the use / dir rules; runway links once excluded and once allowed (explicit backtrack).
- `aip_check.py` (M2): per-stand AIP fields, the per-runway `aip_facts` blocks, and whether removed AIP values remain.
  Since fix round 2 (re-verify N3) the script holds no AIP value: it reads its search patterns from the local,
  git-ignored `refs/cache/aip_checks/patterns/fix1_removed.json` (labels -> strings; numeric patterns match whole
  tokens only, so coordinates such as -3420.18 are no longer hits). Usage: `python3 -I aip_check.py [SHA3D_DIR]`.

Schema adaptations applied to the scratch copies of the original QA scripts (the originals are unchanged):
- `graph_qa.py`, `graph_qa5.py`: `adj()` also accepts `use: 'stand'` (own lead-ins) in both modes;
- `umb_reg.py`: the runway width and shoulder are read from `runways[].aip_facts`;
- `aip_leak.py` reads the removed `aip_status` field and is replaced by `aip_check.py`.
