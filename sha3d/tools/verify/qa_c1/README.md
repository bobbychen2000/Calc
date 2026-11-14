# QA C1 scripts (adversarial data QA of sha_airport / sha_stands / sha_taxigraph)

Report: `docs/phase1/qa_data.md`. These are the scripts as run on 2026-11-14. They read the committed data, the pinned
OSM, the local imagery caches and (for the sensitive and AIP checks) local-only caches; they print counts only and never
write OSM ids of dropped (sensitive) elements or AIP values. Several write small intermediate JSON files into the current
directory, so copy this folder to a scratch directory and run there, e.g. `python3 -I rwy_qa.py`. Absolute paths point at
`/home/user/Calc/sha3d`. Plates go to `docs/phase1/qa/`.
