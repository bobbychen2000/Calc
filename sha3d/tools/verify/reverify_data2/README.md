# Re-verify (data), fix round 2: adversarial scripts, 2026-11-14

Report: `docs/phase1/reverify_data2.md`. These scripts try to reconstruct the features that the sensitive filter drops
(military, armed police, police, prison, GNSS) from the committable files. They read the raw tiles
(`refs/cache/osm_pinned_raw/`, local only) to know what was dropped.

Rules:
- Run with `python3 -I` from any directory. `SHA3D_DIR` may point at another copy of `sha3d/`.
- Console output is counts, lengths, percentages and feature classes only. Nothing names or places a dropped feature.
  The lengths, percentages and kept classes stay on the console: committed documents quote counts per class and per
  rule and "exempt / not exempt" only (fix round 3, `docs/phase1/qa_data.md`).
- Per-element details (ids, classes, sizes) go to `refs/cache/reverify_data2/*_local.json`, which is git-ignored.
- `rv2_fingerprint.py` reads its search criteria from the git-ignored `refs/cache/reverify_data2/fingerprint_local.json`,
  so the committed script does not restate what the documents say about a dropped feature's surroundings.

`LIST` is the committable file list: `git ls-files sha3d`, plus `git ls-files --others --exclude-standard sha3d`, plus
the 5 files of `refs/cache/osm_pinned/`.

| Script | What it tests |
|---|---|
| `rv2_common.py` | Shared loader. Applies the tag rule to the raw tiles, builds the dropped geometry in world metres, loads the pinned extract. |
| `rv2_inventory.py` | Tag-rule drops by class and kind. Second-order drops derived independently of `pin_extract.py` (raw tagged elements in the extent that are missing from the extract), compared with `pin_summary.json`. |
| `rv2_names.py LIST` | Text search:<br>- sensitive regexes and dropped-name parts in every kept tag value;<br>- dropped names, dropped ids and the ids of vertex-only nodes in every committable text file;<br>- kept relations with dropped members;<br>- camera and enforcement tags;<br>- a broad keyword scan. |
| `rv2_geom.py` | Per dropped group:<br>- kept features touching, inside or near it;<br>- how much of the outline or line kept linework traces, against 40 random placements of the same shape;<br>- parallel features within 30 m;<br>- shared nodes;<br>- bridges and railway remnants;<br>- holes in kept polygons;<br>- crossing vertices left on kept roads. |
| `rv2_geom2.py` | - Dangling network ends near dropped groups, against the base rate.<br>- Bridges or tunnels over nothing.<br>- Unexplained corridors between kept polygons, against 60 random placements.<br>- Holes left by the second-order drops.<br>- Voids inside dropped areas.<br>- A Hough search over the unexplained kept road vertices. |
| `rv2_data.py LIST` | Every committable JSON / JS file outside the pinned extract: points and polylines near each dropped group, and how much of each group they trace. Also checks that each `.js` equals its `.json`. |
| `rv2_fingerprint.py` | Search-key test: the committed phase-0 radial distances, the phase-1 descriptions and the pinned extract. How many candidate places remain? |
| `rv2_n2.py` | N2. Taxiway re-fit side effects measured against the OSM ways: added turns, spikes, reversed or short segments, BN not moved. |

**Fix round 3 adaptation** (`docs/phase1/qa_data.md`, Fix round 3): `pin_extract.py` rule (g) removes crossing vertices
from the kept geometry, so the raw node list of a kept way no longer equals what the committable files show.
`rv2_common.committed_nodes()` returns each kept way's raw node list without the in-extent nodes that are not vertices
of its committed geometry. `rv2_geom.py` (T6, T7, T9), `rv2_geom2.py` (U1, U6), `rv2_fingerprint.py` (vertex density)
and `rv2_names.py` (vertex-only node ids) use it. On the pre-fix extract it reproduces the original T6, T7, T9, U1, U6 and
fingerprint output exactly.

Other checks used, unchanged:
- `tools/verify/reverify_data/chain.sh` and `md5set.sh`: two chain runs.
- `rv_route.py`: routing.
- `rv_aip_tokens.py`: AIP tokens.
- `tools/verify/qa_c1/twy_offset.py`: Umbra residuals. Run it from a scratch copy that also holds `qa_img.py`.
