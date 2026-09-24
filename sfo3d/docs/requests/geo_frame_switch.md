# Request: switch WGS 84 inputs to `wgs84ToWorld` (world frame `ltp-nad83-2011`)

From: projection & datum workflow (owner of `js/geo.js`, `tools/geo_frame.py`), 24 Sep 2026.

`js/geo.js` now uses the exact GRS80 local tangent plane at the ARP and declares the world datum **NAD83(2011)**
(FAA NASR, USDA NAIP, SFO Museum). `llToWorld` / `worldToLL` are for NAD83 lat/lon only. Positions in **WGS 84**
(ADS-B, OSM, X-Plane, GNSS) must go through the new `wgs84ToWorld(lat, lon, h)` / `worldToWgs84(x, z)`. These apply
the NAD83(2011) -> WGS 84 (G2296) displacement at SFO, epoch 2026.73: a fixed ground point's WGS 84 coordinates are
dE -1.568 m, dN +0.159 m from its NAD83 coordinates. This was checked with pyproj 3.7.2 / PROJ 9.5.1 (EPSG
"ITRF2020 to NAD83(2011) (1)"). Python twin: `tools/geo_frame.py` (`wgs84_to_world`, `world_to_wgs84`). Test:
`python3 tools/test_geo_frame.py`.

Evidence that the shift is right: OSM runway centrelines against the FAA NASR axes move from about 0.54 m lateral
to about 0.05 m once the datum shift is applied (`tools/xcheck/compare_runways.py`, ends 28R, 10R, 28L).

Files that are not mine and still use the old path:

| File | Line (24 Sep) | Now | Change to |
|---|---|---|---|
| `js/live/traffic.js` | 184 | `llToWorld(a.lat, a.lon, 0)` on ADS-B | `wgs84ToWorld(a.lat, a.lon, 0)` |
| `js/livedata.js` | 49, 64 | `llToWorld` on ADS-B | `wgs84ToWorld` |
| `js/shots.js` | 44 | `llToWorld` on ADS-B | `wgs84ToWorld` |
| `js/live/app.js` | 289 | inline equirectangular inverse (110990 / 111320 cos) to lat/lon for the route lookup | `worldToWgs84(t.last.x, t.last.z)` (the 3-decimal rounding makes this cosmetic) |
| `tools/drawing/background.py` | 185 | inline **legacy** equirectangular inverse to lat/lon to sample NAIP | `geo_frame.world_to_ll(X, Z)` (NAIP is NAD83, so no datum shift). With the legacy formula the imagery is misregistered by up to ~2 m against the regenerated data. |
| `tools/live/gatecheck.py` | 13, 47-49, 269 | legacy equirectangular `ll_to_en` on ADS-B | `geo_frame.wgs84_to_world` / `world_to_wgs84` |
| `tools/live/replay_common.py` | 5, 27-28 | legacy equirectangular on ADS-B | `geo_frame.wgs84_to_world` |
| `livetest.mjs` | 28 | legacy m/deg in the mock random walk | Harmless: it only jitters mock positions. Optional change. |

`data/sfo_stands.json` is backward compatible: same fields with the same meaning, plus a top-level `frame`. Stand
noses and bridge attach points are the legacy survey mapped exactly into the new frame (shift 1.0-2.0 m, heading change
< 0.03 deg). There is one deliberate label change: stand B25's bridge is now labelled `B25` instead of `B24`. The two
hold rooms are equidistant from the door to 3 mm, and the tie now goes to the stand's own name.
