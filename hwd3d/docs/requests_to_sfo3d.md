# Requests to sfo3d (from hwd3d)

Items found while forking sfo3d @ a967f9b that belong in sfo3d. hwd3d never edits sfo3d itself.

## R1 (2026-11-12, world frame fork): ARP rounding error is stated as "< 0.5 mm" but is 6.6 mm

`sfo3d/tools/geo_frame.py` (header) and `sfo3d/js/geo.js` say the ARP constants are the NASR decimals "rounded to
1e-7 deg (< 0.5 mm)". NASR LAT_DECIMAL 37.61880555 -> 37.6188056 (+5e-8 deg = 5.5 mm north) and LONG_DECIMAL
-122.37541666 -> -122.3754167 (-4e-8 deg = 3.5 mm west): the origin is 6.6 mm from the NASR point. Harmless (the origin
is only a reference and every feature has its own coordinates), but the stated figure is wrong. Suggested text:
"rounded to 1e-7 deg (origin 5.5 mm N, 3.5 mm W of the NASR decimal)". Also for information: pyproj 3.8.0 / PROJ 9.8.1
reproduces sfo3d's NAD83(2011) -> WGS 84 (G2296) value at the SFO ARP @ 2026.73 (-1.5679 E, +0.1589 N), measured by
`hwd3d/tools/common/test_hwd_frame.py` check 8.

## R2 (2026-11-12, OSM fetch fork): `osm_attic_api.py` writes relations without member geometry

`sfo3d/tools/xcheck/osm_attic_api.py` (the `--via api` fallback of `fetch_osm.py`) writes relations with their member
list only, while an Overpass `out meta geom` answer carries the geometry of every member. A parser that assembles
multipolygons (aprons, buildings, landuse mapped as relations) would therefore read different data depending on which
route fetched the extract. sfo3d's own `parse_osm.py` ignores relations, so nothing in sfo3d is wrong today; the
hwd3d fork (`hwd3d/tools/osm/osm_attic_api.py`) adds the member geometry where the member is known. Related, for
information: the hwd3d fork also queries lifecycle-prefixed keys (`nwr[~"^[a-z_]+:aeroway$"~"."]`, e.g.
`disused:aeroway`) because closed pavements are often tagged that way; at HWD there were none (closed taxiways there are
`aeroway=taxiway` + `abandoned=yes` / `disused=yes`). Whether the SFO extract misses such elements was not checked.

## R2 (2026-11-12, NAIP fork, task G2): `naip_fetch.py --source pc --year 2022` matches no item; PC now has CA NAIP 2024

1. `sfo3d/tools/imagery/naip_fetch.py` compares `f['properties']['naip:year'] == year`. On Planetary Computer the
   type of `naip:year` differs by year: an int for the 2022 (and older) CA items, a string (`'2024'`) for the new 2024
   items (STAC search over HWD, 2026-11-12). `--year 2022` is a string, so nothing matches; that is what
   `sfo3d/refs/cache/naip_fetch_pc.log` shows ("-> using 2022 []", 0.5 MB file, 76.7 M empty pixels). Fix: compare
   `str(...)` on both sides (done in `hwd3d/tools/imagery/naip_fetch.py`).
2. `sfo3d/docs/research/imagery.md` and the naip_fetch.py header say Planetary Computer stops at NAIP 2022. Its `naip`
   collection now lists CA 2024 items (e.g. `ca_m_3712223_se_10_060_20240520`, datetime 2024-05-20). For HWD the USDA
   image-service export (`--source usda`, LockRaster, nearest neighbour, 0.6 m) is pixel-identical to the PC 2024 COG
   in all 4 bands (two 512 x 512 windows, 0 DN difference, best offset 0,0: `hwd3d/tools/imagery/naip_grid_check.py`,
   `hwd3d/refs/cache/naip/naip_grid_check.json`). This confirms sfo3d's inference that the USDA path delivers the
   native grid; the SFO quads were not re-checked.

## R3 (2026-11-12, ADS-B ground analysis fork, task G4): rec_pack sampling and two comment fixes

1. **The committed rec_pack sees about 14 s of every minute.** Measured over all 111 adsb.lol files of
   `sfo3d/refs/cache/rec_pack` (`hwd3d/tools/adsb/extract.py`, 'poll_pattern'): 54,537 HTTP 200 polls, 5,806 HTTP 429,
   324 without a code. The recorder polls every ~1.3 s until adsb.lol answers 429 (4,782 of 5,541 bursts have exactly
   10 polls), then waits for the next minute: poll-gap percentiles p50 1.5 s, p90 43.5 s, p95 48 s. Anything shorter
   than ~45 s (a touch-and-go roll, a short stop, a push-back start) can fall entirely into a hole; durations are known
   to +-~50 s. Worth stating in `sfo3d/refs/cache/README.md` / the replay docs, and worth checking whether the replay
   interpolation assumes a denser stream.
2. `sfo3d/tools/imagery/adsb_ground_cells.py` header: "NACp >= 8 (EPU < 30 m; ...)". In the DO-260B NACp table (from
   memory, not re-read) NACp 8 is EPU < 0.05 NM (92.6 m) and NACp 9 is < 30 m. The selection itself is fine; only the
   stated bound is off by one category.
3. For information: on the ground, readsb's `track` can be stale (an HWD BE20 take-off roll at 46-91 kt reported track
   55.0 while `true_heading` and the position displacement gave 300.9). If sfo3d derives ground headings from `track`,
   prefer the displacement or `true_heading` on the surface.

## R4 (2026-11-12, airport data set, task G5): hold-bar depth source; window_corr reused unchanged

1. `sfo3d/tools/imagery/paintline.py` BAR_DEPTH carries the comment "4 lines 12 in wide with 12 in gaps = 7 ft deep
   (FAA AC 150/5340-1M fig. A-5? see build_airfield_details.py)". The value is right; the source is FAA AC 150/5340-1M
   Change 1, para 3.3.4.1 (Pattern A: "two continuous lines, two dashed lines, and three spaces ... measure 12 inches
   (30 cm) in width"; 6 in is allowed only at airports without an operating ATCT that are not certificated under
   Part 139). The page is committed in hwd3d as `refs/cache/faa/ac150_5340_1m_chg1_p52-54_63.pdf` (PDF page 63).
   Suggested comment: "AC 150/5340-1M Chg 1 para 3.3.4.1".
2. For information: `hwd3d/tools/build_airport.py` reuses `window_corr()` of `sfo3d/tools/build_airfield_details.py`
   unchanged. At HWD the taxiway centrelines are so worn on NAIP 2024 that only 45 of 1,962 unmasked stations gave a
   ridge >= 10 DN with b* >= 9 (sfo3d's thresholds); faint ridges (>= 4 DN) put the OSM lines 0.1-0.4 m from the
   paint. No change requested.

## R5 (2026-11-12, Phase 1 review of hwd3d): OSM contributor metadata in the committed Overpass extracts; fetch provenance on a re-merge

1. **Contributor names and ids.** The sfo3d Overpass extracts keep the `out meta` fields `user` (display name) and `uid`
   (account id) of every element, for example `sfo3d/refs/cache/osm/overpass_ksfo_latest.json`. The hwd3d review counted
   1,118 to 4,752 uid entries per file. No sfo3d parser needs them. The OSMF Privacy Policy lists user id and login name
   as data stored with every change, and says that the metadata in its data dumps goes to logged-in users. The reviewer
   read this through a summariser, and hwd3d did not re-read it. The harm is low because OSM serves the fields publicly
   through its API, so the owner decides. hwd3d now strips both fields from its committed extract
   (`hwd3d/tools/osm/fetch_osm.py` STRIP_FIELDS). It records `sha256_unstripped` in the meta and keeps an unstripped
   local copy for the `--via api` cross-check. Suggestion: do the same in `sfo3d/tools/xcheck/fetch_osm.py`, or record
   the owner's acceptance.
2. **Re-merge from the cache.** In hwd3d, a re-run of `fetch_osm.py` that took every part from the `.parts` cache, with no
   network, rewrote the meta's `fetched_utc` and dropped the original FAIL log lines. The new `fetched_utc` then
   propagated into the parsed file. hwd3d now keeps the existing meta's `fetched_utc` and log when no part was fetched.
   sfo3d's `fetch_osm.py`, which hwd3d forked, probably behaves the same; this was not checked in sfo3d.
