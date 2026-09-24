# Orthoimagery, projection and screenshot-registration audit (KSFO)

Research note, 24 Sep 2026. Tools: `tools/imagery/*.py`. Downloads and derived rasters: `refs/cache/naip/` (gitignored).
Nothing in `data/`, `js/` or `tools/sat/work/` was modified.

**Legend.** **[obs]** = measured or read by me from the cited original source in this session.
**[inf]** = inferred or reasoned from observations. **[unverified]** = could not be checked against an original source.

---------------------------------------------------------------------------------------------------------------------

## 0. Summary

1. **Best open imagery: USDA NAIP 2024.** It was flown 2024-05-20 at 0.6 m, RGB + NIR. It is public domain, and USDA
   asks for credit. I downloaded it from USDA's own image service, because Planetary Computer stops at NAIP 2022. I also
   downloaded NAIP 2022 (flown 2022-05-18).
   - I found **no public-domain or openly licensed imagery sharper than 0.5–0.6 m over SFO**.
   - San Mateo County publishes 0.5 ft (15 cm) orthos for 2018 and 2022, but under a disclaimer with no licence grant.
     They are **not** open.
   - NOAA NGS has 0.5 m mosaics from 2013–2018, all older than NAIP 2024.
   - USGS The National Map returns no HRO over the airport. OpenAerialMap's API was down.
2. **NAIP is very accurate on the ground at SFO**, far better than its ±6 m specification.
   - The runway side stripes in NAIP 2024 lie **0.20–0.23 m** from the FAA centrelines. The 2-D offset is 0.32 m; for
     NAIP 2022 it is 0.43 m.
   - The threshold-bar edges lie **−0.9 to 0.0 m** from the FAA ends.
   - Measured markings confirm FAA/AC dimensions: stripe blocks of 45.7–46.1 m (150 ft), EMAS 10.5–10.7 m (35 ft)
     beyond the 19L/19R ends, and side stripes 60.0–60.2 m apart.
   - NAIP 2022 and 2024 agree on the ground to 0.32 m (median) over 289 tiles.
   - **Roofs are the exception.** NAIP is not a true orthophoto. Roofs lean east by metres, and the ATC tower cab by about
     40 m.
3. **The projection in `js/geo.js` scales longitude 0.124 % short.** 110 990 m/deg latitude is correct to 7 ppm. But
   111 320·cos φ gives 88 175.4 m/deg longitude, while GRS80 gives 88 285.2.
   - Error against an exact local tangent plane: **3.7 m at 3 km, 4.1 m at the AOI corner, 0.6 m within 500 m** of the
     ARP.
   - Runways 10/28 come out 3.4 m short, and their headings are off by 0.04°.
   - Everything in the app goes through the same function, so it is *internally* consistent. The error shows up only in
     metric lengths and against external rasters. The fix is cheap, and so is the migration (§4).
4. **Datum shift at SFO: NAD83(2011) → WGS 84 is about 1.58 m toward azimuth 276°** (1.57 m west, 0.16 m north) at
   epoch 2026.7. This is a time-dependent EPSG Helmert transformation. PROJ's *default* NAD83→WGS84 is a null transform.
   - FAA and NAIP are NAD83. ADS-B is WGS 84.
   - Older NAD83 realisations differ by a further 0.1–0.9 m (NGS NCAT).
   - Bay Area intraplate motion is **not** modelled [unverified].
5. **The Google screenshot registrations are good to about 2 m, with exceptions.**
   - 11 of the 19 images share an offset of about (−1.5 m east, +1.2 m south) against NAIP.
   - **Three close-up screenshots have a scale error of 1.5–2.5 %**, giving 5–10 m at the image edges: 151ec51d
     (G pier), b1d51b0f (B pier) and c235f3b8 (E pier). A fourth, 03dcd4ae, is about −0.7 % with low confidence.
     - Two of the three have a partner screenshot at the same zoom. After correction, their px/m match the partner's to
       0.06 %. This strongly suggests a misread scale bar.
     - Stands measured on these images are off by a median of 2.6–3.7 m, up to 9 m. Their pitch is about 2.5 % short.
   - The east-side images 1a26bbeb and c1064033 are about 3.7 m west.
   - The overview 8b334c52 (3.2 m/px) is off by up to 13 m at the east runway ends.
   - Corrected similarity transforms are in `refs/cache/naip/reg_naip.json`. They are a proposal only; `reg.json` is
     unchanged.
6. **SFO Museum outlines vs NAIP.** The roof edges in NAIP sit about 5 m east of the outlines, the same in 2022 and
   2024. This matches NAIP's roof lean, not an outline error.
   - NAIP therefore **cannot** verify the outlines better than about ±5 m.
   - No public lidar covers SFO in the USGS 3DEP cloud bucket.
   - Indirect evidence says the outlines agree with Google's roofs to about 1.5 m.
7. **Can NAIP be used as a texture? Yes, licence-wise.** It is U.S. public domain, and USDA requests a credit line
   (§1.1).
   - **Practical caveats:**
     - 0.6 m resolution;
     - dozens of parked aircraft and many vehicles are baked in (not counted exactly);
     - roofs lean by metres.
   - Use it for ground and landside, and mask or inpaint aircraft. Get the owner's sign-off first, per the CLAUDE.md
     rule.

---------------------------------------------------------------------------------------------------------------------

## 1. Imagery sources and licences (task a)

### 1.1 USDA NAIP — chosen

| Item | Value | Source |
|---|---|---|
| Latest CA year over SFO | **2024**, tiles `m_3712229_ne_10_060_20240520`, `m_3712230_nw_…`, `m_3712222_sw_…`, `m_3712221_se_…`; flown 2024-05-20 (`QQDATE`) | [obs] catalog query of the USDA image service `https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer/query` (saved `refs/cache/naip/usda_2024_catalog.json`) |
| Planetary Computer | STAC `naip` has CA 2012, 2014, 2016, 2018, 2020, 2022 over the AOI; **no 2024** (collection temporal extent ends 2023-12-31) | [obs] `https://planetarycomputer.microsoft.com/api/stac/v1/search` (saved `stac_search.json`, `collection_naip.json`) |
| 2022 tiles | `ca_m_3712230_nw_10_060_20220518` + `…29_ne`, `…22_sw`, `…21_se`; also on Azure `ca_030cm_2022` exists but only for northern CA cells 41120–42123 (no 30 cm at SFO) | [obs] STAC + blob listing `naipeuwest.blob.core.windows.net/naip/v002/ca/2022/` |
| GSD / bands / CRS | 0.6 m, R G B NIR, uint8, EPSG:26910 (NAD83 / UTM 10N); 2022 and 2024 on the same 0.6 m grid (pixel edges at multiples of 0.6 m) | [obs] GeoTIFF headers; 2024 grid phase tested by exporting at 0.1 m (all pixel boundaries at phase 0 of 6) |
| Tile buffer | 300 m (2022); "In 2024 the buffer was changed to 12-meters on all four sides." | [obs] 2022 ISO metadata; USDA hub text quoted in the CA Geoportal item `061537e1c20744cb95506c12a028bff4` |
| Ortho process (2022) | Leica ContentMapper, ~4470 m AGL, 67.1° across-track FOV; bundle adjustment "with … photo-identifiable GPS-surveyed ground control points"; "orthorectified image frames were created … with … the 2018 or newer HxIP DEM" | [obs] tile ISO 19115 metadata `…/ca_fgdc_2022/37122/m_3712230_nw_10_060_20220518.xml` (saved `src/fgdc_m_3712230_nw_10_060_20220518.xml`) |
| Accuracy spec | "all well-defined points tested shall fall within 6 meters of true ground at a 95% confidence level" | [obs] NAIP Information Sheet, Feb 2015, https://www.fsa.usda.gov/Internet/FSA_File/naip_info_sheet_2015.pdf. The often-quoted "±4 m from 2016" appears only on secondary pages (e.g. Utah UGRC) — [unverified] against a USDA original |

**Licence — quoted from the originals:**

- **data.gov catalog record** (https://catalog.data.gov/dataset/national-agriculture-imagery-program-naip-imagery,
  "Dataset Last Updated July 09, 2025"; saved as `src/datagov_naip.html`) [obs]:
  - "License: https://www.usa.gov/publicdomain/label/1.0/";
  - "Access Level: public";
  - Publisher: "Farm Production and Conservation Business Center".
- **USDA FSA, Policies and Links** (https://www.fsa.usda.gov/help/policies-and-links; saved as `src/fsa_policies_and_links.html`)
  [obs]:
  > "Most information presented on the FSA Web site is considered public domain information. Public domain information
  > may be freely distributed or copied, but use of appropriate byline/photo/image credits is requested. Attribution may
  > be cited as follows: "U. S. Department of Agriculture, Farm Service Agency.""
- **USDA image service item** (CA State Geoportal / ArcGIS item `061537e1c20744cb95506c12a028bff4`, "NAIP 2024 60cm
  California", service URL above), `licenseInfo` [obs]:
  > "Use Constraints: These services are for illustrative purposes only. It is not suitable for surveying or engineering
  > purposes, The Farm Production and Conservation Business Center (FPAC-BC) Geospatial Enterprise Operations (GEO)
  > Branch asks to be credited for derived products."
- **Planetary Computer collection `naip`** [obs]:
  - `"license": "proprietary"`, with the licence link titled **"Public Domain"**, pointing to the FSA policies page above;
  - USDA FSA listed as "producer, licensor".
  - PC's own service terms were not reviewed [unverified]. They govern the API, not the data.

**Can NAIP be used as a texture?**
- **Yes.** It is U.S. public domain.
- Credit it, for example: *"Imagery: USDA NAIP 2024 (USDA Farm Production and Conservation Business Center, Geospatial
  Enterprise Operations)"*.
- Do not imply USDA endorsement.
- One nuance [inf]: NAIP is flown by contractors. Its public-domain status rests on USDA's own designation (data.gov
  label, FSA policy), not on 17 U.S.C. §105 alone. That designation is explicit, which is sufficient.
- **Practical caveats** before using it as the airport ground texture (observed in the rasters):
  - 0.6 m GSD. Painted lines 15–30 cm wide are blurred.
  - Dozens of parked aircraft (not counted), GSE and cars are baked in, and would appear as "ghost" aircraft under the
    live ones.
  - Roofs, jet bridges and the tower lean (§6), so they do not sit on the 3-D buildings.
- Recommendation:
  - use NAIP for landside, terrain and water edges, and optionally airfield pavement *after* masking or inpainting
    aircraft and vehicles;
  - keep the procedural airfield for markings;
  - the owner signs off before shipping (CLAUDE.md working rule).

### 1.2 Higher-resolution candidates searched

| Source | Over SFO? | GSD / date | Licence (quoted) | Verdict |
|---|---|---|---|---|
| **San Mateo County image services** `https://gis.smcgov.org/image/rest/services/SanMateoCounty_Imagery2022/ImageServer` and `…2018…` | yes (county covers SFO) | 2022: 0.5 ft (service `pixelSizeX` 0.5 in EPSG:2227 ftUS), 3-band. 2018: 0.5 ft, 4-band, "collected between 6/13/2018 and 6/23/2018 for the Golden Gate National Parks Conservancy", NAD83(2011) | County items (e.g. ArcGIS item `385b774fb9db476c97153a4cab358c2e`): "The GIS data (the "Data") is made available by San Mateo County (the "County") as a public service. The Data is for reference purposes only, and the County makes no representations, warranties, or guarantees…". The 2018 service `copyrightText`: "Golden Gate National Parks Conservancy and San Mateo County". The 2017 item says "The raw geotiff or sid files are not readily available for download. If you need access to the source files please contact the San Mateo County GIS Team at countygis@smcgov.org" [obs] | **Not open.** No licence grant; "reference purposes only". Do not use as a texture without written permission. It is the best candidate to *request* (15 cm): ask countygis@smcgov.org |
| **NOAA NGS DSS mosaics** (Digital Coast, `coastalimagery.blob.core.windows.net/digitalcoast/…`) | 2018 Redwood City (5 tiles intersect the AOI; bbox 37.447–37.631 N, "coverage may not include full geographic extent"), 2015 Redwood City, SF Bay South 2013/2014 (tide-coordinated). The 2022 and 2025 "San Francisco" and 2022 "Redwood City" sets do **not** reach SFO | 0.5 m; 2018-10-20; NAD83(2011) UTM 10N (EPSG:6339); "The accuracy of the data is plus or minus 1.5 m at at the 95% circular error confidence level" (InPort 54930) | InPort 54930 ISO metadata: "Access Constraints: None"; "Use Constraints: Users should be aware that temporal changes may have occurred…"; "Cite As: National Geodetic Survey, [Date of Access]: 2018 NOAA Ortho-rectified Color Mosaic of Redwood City, CA…". A U.S. Government work: "Copyright protection under this title is not available for any work of the United States Government" (17 U.S.C. §105(a), law.cornell.edu) [obs] | Open (public domain), but not sharper than NAIP and 6 years older. Useful as an **independent accuracy check** (±1.5 m CE95 spec). Not downloaded |
| USGS HRO (The National Map) | TNM API `products?datasets=High Resolution Orthoimagery&bbox=…` → 0 results (also 0 for the NAIP dataset) [obs] | — | public domain if found | Not available via TNM. EarthExplorer's HRO collection needs a login, not checked [unverified] |
| OpenAerialMap | API `api.openaerialmap.org/meta?bbox=…` twice returned `"Operation metas.count() buffering timed out after 10000ms"` [obs] | — | API meta states "CC-BY 4.0" | **Could not be queried** [unverified] |
| USGS 3DEP lidar (EPT, `s3-us-west-2.amazonaws.com/usgs-lidar-public`) | `CA_SanFrancisco_1_B23` covers 37.697–37.837 N only; no other CA_* project in the listing covers SFO [obs] | — | public domain | No lidar over SFO in the bucket, which rules out a lean-free building check (§6) |
| Google Maps screenshots | yes | ~0.16–3.2 m/px | licensed | **Reference only**, per the project rule |

---------------------------------------------------------------------------------------------------------------------

## 2. Delivered rasters (refs/cache/naip/)

| File | What |
|---|---|
| `naip_2024_sfo_utm10n.tif` (276 MB) | NAIP 2024 mosaic of the 4 DOQQs, RGB+NIR, EPSG:26910, native 0.6 m grid, E 552 343.8–557 531.4, N 4 160 896.8–4 166 222.4 (AOI + 150 m). Each pixel is taken from the DOQQ whose centre is nearest. Made by `tools/imagery/naip_fetch.py --source usda --year 2024` (exportImage per tile, LockRaster, nearest neighbour, 2000 px chunks) |
| `naip_2022_sfo_utm10n.tif` (229 MB) | Same for 2022, from Planetary Computer COGs (`naip_fetch.py`, windowed HTTP range reads) |
| **`naip_2024_world_0.5m.png`** (163 MB, 9701 × 9990) | NAIP 2024 resampled onto the **world grid**: x = east, z = south, metres from the ARP, via `js/geo.js` `llToWorld` exactly. Mapping is per pixel: world → lat/lon (inverse geo.js) → UTM (pyproj) → bilinear. World lat/lon is treated as NAD83, the same as the FAA ends |
| `naip_2024_world_0.5m.json` | Transform: `x0 = -2609.0, z0 = -2352.5, res = 0.5, width 9701, height 9990`; **`col = (x − x0)/res − 0.5`, `row = (z − z0)/res − 0.5`** (pixel centres); texture UV `u = (x − x0)/(W·res)`, `v = (z − z0)/(H·res)`. Includes provenance and the credit line |
| `naip_2024_world_0.5m_tiles/t_{row}_{col}.jpg` | The same raster as 25 JPEG tiles of 2048 px (1024 m) each, 26 MB total, for WebGL |
| `naip_2024_world_preview.jpg` | 4 m/px preview |

Notes:
- 0.5 m was chosen because NAIP's native GSD is 0.6 m. 0.3 m would only interpolate.
- `naip_world.py --proj ltp` re-renders the raster in the recommended exact projection (§4); `--wgs84` treats world
  lat/lon as WGS 84.
- For the in-Claude artifact (16 MB cap), use an airport-only 1 m JPEG or KTX2. I did not produce one.

---------------------------------------------------------------------------------------------------------------------

## 3. How good is NAIP at SFO? (absolute and inter-year)

`tools/imagery/naip_faa_check.py`: NAIP is sampled through the exact mapping and compared with the FAA runway ends in
`js/geo.js` (AirNav/FAA, NAD83).

**Lateral check.**
- Method: the 75th-percentile cross-profile of each runway, in 300 m segments.
- The continuous white side stripes (3 ft, outer edge on the 200 ft edge → centres at ±30.02 m) give the measured
  centreline.

**Along-track check.**
- At the four non-displaced ends, a ~3.5 m white threshold bar starts at the end.
- Then comes a ~2 m gap, then the 150 ft threshold stripes.

| | 10L–28R | 10R–28L | 1L–19R | 1R–19L |
|---|---|---|---|---|
| NAIP 2024 centreline − FAA centreline (+ = right of the 10/1 → 28/19 direction) | −0.23 m | −0.23 m | −0.20 m | −0.23 m |
| azimuth difference | −0.001° | −0.003° | +0.007° | +0.007° |
| scatter of 300 m segments | 0.15 m | 0.14 m | 0.08 m | 0.11 m |
| side-stripe spacing (nominal 60.05 m) | 60.18 | 60.12 | 60.09 | 60.00 |
| NAIP 2022 centreline offset | −0.32 m | −0.24 m | −0.33 m | −0.32 m |

- **2-D shift NAIP − FAA** (least squares from the two perpendicular runway pairs):
  - 2024: **(−0.08 m east, −0.31 m south) = 0.32 m**;
  - 2022: (−0.16, −0.40) = 0.43 m.
- **Along-track**: the threshold-bar outer edge lies −0.88 (10L), −0.51 (10R), −0.33 (19L) and +0.01 m (19R) from the
  FAA end, with 2024 imagery. The 2022 values are −0.47, −0.46, −0.28 and −0.66 m.
  - This agrees with the along-track component of the 2-D shift (−0.2 to −0.3 m) to better than 0.7 m. [obs]
- By-products that check the method [obs]:
  - stripe blocks measure 45.66–46.09 m (150 ft = 45.72 m);
  - the EMAS edge is 10.50 m (19R) and 10.70 m (19L) beyond the end, matching the 35 ft (10.67 m) setback quoted in
    `docs/HANDOFF.md`.
  - The measured bar width, 3.4–3.7 m, is wider than 10 ft; the cause is not resolved: blur, or the paint really is
    wider [unverified].
- **Inter-year** (`naip_interyear.py`): 289 ground-only 200 m tiles, buildings excluded.
  - 2024 − 2022: median (+0.10, +0.24) m, std (0.17, 0.19) m;
  - |d| median 0.32 m, p90 0.54 m, max 0.82 m. [obs]

**Conclusion** [inf]:
- On ground-level features, NAIP 2024 is registered to the FAA NAD83 runway coordinates to about 0.3–0.5 m at SFO.
- It can serve as ground truth at the ≈0.5 m level for everything that is on the ground.
- It **cannot** do so for anything elevated (§6).

---------------------------------------------------------------------------------------------------------------------

## 4. Projection and datum audit (task b) — `tools/imagery/projection_audit.py`

### 4.1 `js/geo.js` equirectangular vs exact local tangent plane (GRS80 ENU at the ARP)

| | geo.js | GRS80 at φ = 37.6188° | error |
|---|---|---|---|
| m / deg latitude | 110 990.0 | 110 989.3 (meridian radius M) | +7 ppm |
| m / deg longitude | 111 320·cos φ = 88 175.4 | N·cos φ·π/180 = 88 285.2 | **−1243 ppm (−0.124 %)** |

Over the AOI (lat 37.595–37.640, lon −122.405 to −122.350), geo.js − LTP:
- **max 4.10 m** (SW corner), RMS 1.82 m;
- by radius from the ARP, maximum error: 0.62 m (< 0.5 km), 1.24 m (< 1 km), 1.88 m (< 1.5 km), 2.53 m (< 2 km),
  3.20 m (< 2.5 km), **3.72 m (< 3 km)**, 4.10 m (< 4 km);
- almost all of it is the x scale. After the best affine fit, the non-linear part is ≤ 0.77 m (meridian convergence and
  the change of the parallel radius with latitude).

FAA runway ends, geo.js − LTP, x component:
- 10L +1.76, 28R −2.12, 10R +1.79, 28L −2.02;
- 1L +0.92, 19R −0.48, 1R +0.70, 19L −0.83 m;
- z components ≤ 0.16 m.

| Runway | geodesic length (GRS80) | geo.js world length | Δ | azimuth geodesic → geo.js |
|---|---|---|---|---|
| 10L–28R | 3618.00 m (= 11 870 ft) | 3614.58 m | −3.43 m | 117.793° → 117.833° |
| 10R–28L | 3468.97 m | 3465.61 m | −3.36 m | 117.794° → 117.834° |
| 1L–19R | 2331.76 m | 2331.13 m | −0.63 m | 27.799° → 27.773° |
| 1R–19L | 2636.55 m | 2635.83 m | −0.71 m | 27.800° → 27.774° |

**Impact** [inf]:
- All app data (FAA ends, SFO Museum geometry, ADS-B, and the screenshot registrations fitted to them) goes through the
  same `llToWorld`. The scene is therefore internally consistent.
- The distortion appears as:
  - metric lengths (runways 3.4 m short; gate pitch off by ≤ 7 cm);
  - headings (≤ 0.04°);
  - misfit to any externally georeferenced raster, unless it is resampled through geo.js as done in §2.
- Aircraft models are true-scale, so the airport is 0.12 % narrower E-W than the aircraft on it. That is harmless but
  unnecessary.

### 4.2 UTM 10N (the NAIP grid) at the ARP

- Point scale factor k = 0.999637 (−363 ppm).
- **Grid convergence +0.381°**: UTM grid north is east of true north.
- Using UTM E/N directly as world x/−z after a translation would be wrong by up to **24.7 m** over the AOI.
- NAIP must therefore always be resampled per pixel, as `naip_world.py` does. It must never just be shifted onto the
  world grid.

### 4.3 Datums at SFO

| Transformation (at the ARP, h = 0) | ΔE | ΔN | horizontal | Source |
|---|---|---|---|---|
| NAD83(2011) → ITRF2014 (≈ WGS 84 G2139) @ 2026.73 | −1.568 m | +0.160 m | **1.576 m, az 276°** (ΔH −0.504 m) | [obs] pyproj/PROJ 9.5.1, EPSG "ITRF2014 to NAD83(2011) (1)" time-dependent Helmert |
| NAD83(2011) → ITRF2020 (≈ WGS 84 G2296) @ 2026.73 | −1.568 | +0.159 | 1.576 m | [obs] EPSG "ITRF2020 to NAD83(2011) (1)" |
| same @ 2010.0 | −1.340 | +0.379 | 1.392 m | [obs] |
| NAD83(2011) → NAD83(NSRS2007) | +0.043 | −0.101 | 0.11 m | [obs] NGS NCAT API (NADCON 5), `geodesy.noaa.gov/api/ncat/llh` (saved `src/ncat_*.json`) |
| NAD83(2011) → NAD83(HARN) | +0.406 | −0.593 | 0.72 m | [obs] NCAT |
| NAD83(2011) → NAD83(1986) | +0.437 | −0.799 | 0.91 m | [obs] NCAT |
| `EPSG:4269 → EPSG:4326`, PROJ default | 0 | 0 | 0 | [obs] "NAD83 to WGS 84 (1)" is a null transformation (accuracy 4 m). This is what most GIS tools silently do |

- **Who is in which datum.**
  - FAA runway ends (AirNav/NASR): "NAD83". The realisation is not stated on AirNav [unverified]. That NAIP matches FAA to
    0.3 m suggests the same realisation [inf].
  - NAIP: EPSG:26910, NAD83. Planetary Computer's GeoTIFFs carry the plain NAD83 CRS; NOAA's use NAD83(2011) explicitly.
  - ADS-B: GNSS positions in WGS 84 at the current epoch [inf; standard avionics practice].
  - SFO Museum GeoJSON: RFC 7946 says WGS 84, but the source CAD datum and the transform used are unknown [unverified].
  - Google imagery: Web Mercator on WGS 84.
- **Intraplate motion (not modelled).**
  - NAD83(2011) is fixed to stable North America at epoch 2010.00.
  - SFO sits in the Pacific–North America boundary zone. The EPSG Helmert includes only the stable-plate rotation.
  - The local NW drift since 2010 (NGS HTDP would give it) is **not** included. Order of magnitude 0.2–0.4 m [inf;
    unverified — HTDP could not be run here].
  - Practical meaning: WGS 84 positions of fixed airport features are about 1.6 m (±0.4 m) west of their NAD83(2011)
    coordinates.
- **Relevance.** 1.6 m is below ADS-B position noise, but not negligible next to a surveyed 0.3 m frame. It should be
  handled once, explicitly, rather than silently.

### 4.4 Recommended fix and migration

1. **World frame = NAD83(2011), exact local tangent plane at the ARP.** Replace `llToEN` / `enToLL` in `js/geo.js`. I did
   not edit `js/`; this is for the owner or the geo.js maintainer.

   ```js
   // GRS80 local tangent plane (ENU) at the ARP; exact. Replaces the spherical equirectangular formula.
   const A = 6378137.0, F = 1 / 298.257222101, E2 = F * (2 - F), D2R = Math.PI / 180;
   function ecef(lat, lon) { const sl = Math.sin(lat * D2R), cl = Math.cos(lat * D2R);
     const N = A / Math.sqrt(1 - E2 * sl * sl);
     return [N * cl * Math.cos(lon * D2R), N * cl * Math.sin(lon * D2R), N * (1 - E2) * sl]; }
   const O = ecef(ARP.lat, ARP.lon), s0 = Math.sin(ARP.lat * D2R), c0 = Math.cos(ARP.lat * D2R),
         sL = Math.sin(ARP.lon * D2R), cL = Math.cos(ARP.lon * D2R);
   const MLAT = 110989.3, MLON = 88285.2;            // exact local m/deg (projection_audit.json), used for inversion
   export function llToEN(lat, lon) { const p = ecef(lat, lon), dx = p[0] - O[0], dy = p[1] - O[1], dz = p[2] - O[2];
     return [-sL * dx + cL * dy, -s0 * cL * dx - s0 * sL * dy + c0 * dz]; }
   export function enToLL(e, n) { let lat = ARP.lat + n / MLAT, lon = ARP.lon + e / MLON;
     for (let i = 0; i < 3; i++) { const [e1, n1] = llToEN(lat, lon); lat += (n - n1) / MLAT; lon += (e - e1) / MLON; }
     return [lat, lon]; }
   ```

   The Python equivalents are `tools/imagery/common.py` `world_ltp` / `ll_ltp`; their round trip was checked to < 1e-9 m.
2. **ADS-B → NAD83(2011).** Add a constant world offset of **x += +1.57 m, z += +0.16 m**. This is the inverse of the
   ITRF shift at epoch 2026.7; it drifts by about 1 cm/yr, and the Bay Area drift is excluded. It is optional: it is
   below ADS-B noise, but it makes the parked-aircraft alignment exact in principle.
3. **Migration of existing world-metre data** (`tools/imagery/migrate_world.py`):
   - *Rebuild from source* everything derived from lat/lon: `build_sfo_airport.py`, `build_airfield_details.py`,
     `RWY_ENDS`, the snapshot.
   - *Convert pointwise* everything measured in world metres: `tools/sat/stand_defs.py` stands, bridges, red boxes,
     paint, pavement, EMAS/blast-pad measurements. The exact mapping is `new = world_ltp(ll_geojs(old))`.
     - Displacement: 1.18 m at the B pier (−900, 500), 1.89 m at the G pier tip, ≤ 2.1 m anywhere on the terminal
       complex.
     - Relative change: 0.13 m per 100 m E-W.
     - Heading change ≤ 0.011°.
   - A dry run on `data/sfo_stands.json` (written to `refs/cache/naip/sfo_stands_ltp_DEMO.json`, not into `data/`)
     moved 206 points by a median of 1.27 m, max 2.02 m.
   - Registrations in `reg.json` stay valid if they are composed with the same mapping. Refitting each similarity to the
     mapped points leaves ≤ 0.1 m residual inside one screenshot [inf from the ≤ 0.13 m/100 m field gradient].
   - Order of work: switch geo.js and all builders in one commit. Otherwise stands and buildings disagree by 1–2 m.

---------------------------------------------------------------------------------------------------------------------

## 5. Audit of the Google-screenshot registrations against NAIP (task c) — `tools/imagery/reg_audit.py`

**Reference and control points.**
- NAIP 2024 is the reference: 0.3 m from FAA on the ground (§3).
- 115 control points were defined:
  - **16 FAA-derived named points**: the 8 runway ends, the 4 displaced thresholds (FAA end + `RWY_ENDS.disp`) and the 4
    runway-centreline intersections. Each is placed at FAA + the measured 0.32 m NAIP−FAA shift.
  - **99 automatic points**, one per 250 m cell of the *paved* airside. This is the SFO Museum runway/taxiway polygons,
    the inferred apron in `sfo_details.json` and `sfo_pavement.json`, with ≥ 75 % of the 48 m template paved and buildings
    +10 m excluded. The point chosen in each cell has the strongest 2-D gradient structure in NAIP (min. eigenvalue of
    the structure tensor, aircraft-sized bright blobs removed first). In practice these are taxiway-centreline
    junctions, hold bars, runway designations, pad edges and lead-in lines.
- 82 of the 115 points (15 of the 16 FAA points) were measured in at least one screenshot (table below).
- Screenshots were also measured on a **dense grid** of such patches, because the close-ups contain few named points:
  2394 accepted dense matches, plus 169 accepted control-point matches.

**Measurement.**
- A world-aligned template of the screenshot (48 m; 32 m for close-ups ≥ 3 px/m) is sampled *through its `reg.json`
  similarity*.
- It is compared with NAIP ±15 m (±30 m for the 3.2 m/px overview) by masked NCC on gradient images.
  - Masked: SFO Museum buildings +10 m, and bright blobs ≥ 4 m (aircraft, vehicles, white roofs).
  - Accepted when NCC ≥ 0.40, uniqueness ≥ 0.08, the peak is not on the search border, and grey-level NCC agrees within
    max(2 m, 1.5 px).
- **Residual r = where the registration puts a feature − where NAIP has it** (x east, z south).
- Per image, a robust similarity fit r(w) = a + B·(w − w_c) gives a translation at the view centre, a scale and a
  rotation.
- The fit's inverse is written as a corrected registration to `refs/cache/naip/reg_naip.json`.
- QA sheets: `refs/cache/naip/reg_audit_qa_<img>.jpg`, with columns NAIP | screenshot as registered | screenshot
  shifted by r. I inspected those for 151ec51d, 1a26bbeb, 103723b0 and c235f3b8. The corrected column lines up with
  NAIP on threshold bars, EMAS edges, pads and taxiway edges.

### Per-image residuals (registered - NAIP 2024; x east, z south, metres)

| image | m/px | view | ctrl pts ok/in view | dense ok | median r (x, z) | median abs r | p90 abs r | max | fit: translation at view centre | scale (ppm) | rotation (deg) | rms after fit | s in reg.json -> NAIP-corrected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 151ec51d | 0.27 | 345 x 497 m | 0/0 | 47 | (+0.32, +2.34) | 5.37 | 6.50 | 8.08 | (+0.30, +2.16) | -24390 | +0.110 | 0.27 | 3.7394 -> 3.6503 |
| 39176bb8 | 0.27 | 353 x 509 m | 0/1 | 30 | (-0.95, +1.15) | 1.48 | 2.77 | 14.82 | (-0.77, +1.35) | -80 | +0.189 | 0.22 | 3.6529 -> 3.6526 |
| 8b334c52 | 3.18 | 4096 x 5906 m | 60/98 | 221 | (-2.54, +2.20) | 6.98 | 13.09 | 17.17 | (-0.02, +3.64) | +1249 | +0.266 | 2.43 | 0.3149 -> 0.3153 |
| 35809e3e | 1.07 | 1376 x 1984 m | 10/24 | 183 | (-1.31, +1.21) | 2.28 | 3.08 | 4.38 | (-1.23, +1.45) | +663 | -0.051 | 1.09 | 0.9373 -> 0.9379 |
| 0af09b78 | 0.55 | 715 x 1032 m | 4/6 | 95 | (-0.12, +1.05) | 1.23 | 2.32 | 7.33 | (-0.02, +1.71) | -2739 | +0.063 | 0.42 | 1.8030 -> 1.7981 |
| 4637f855 | 0.42 | 539 x 777 m | 0/4 | 29 | (-1.33, +1.63) | 2.19 | 3.04 | 3.52 | (-1.46, +1.69) | +637 | -0.082 | 0.74 | 2.3927 -> 2.3942 |
| bf5c7afc | 0.24 | 308 x 444 m | 0/0 | 51 | (-1.22, +1.47) | 1.97 | 2.62 | 13.63 | (-1.07, +1.42) | -4410 | +0.040 | 0.44 | 4.1923 -> 4.1739 |
| e6f569c1 | 0.50 | 644 x 929 m | 1/2 | 49 | (-1.56, +1.57) | 2.25 | 2.98 | 5.93 | (-1.30, +1.88) | +1664 | +0.027 | 0.26 | 2.0019 -> 2.0053 |
| bc91df95 | 0.58 | 749 x 1081 m | 0/5 | 145 | (-0.99, +0.35) | 1.26 | 2.21 | 6.40 | (-0.98, +0.81) | +2139 | -0.025 | 0.56 | 1.7212 -> 1.7249 |
| 03dcd4ae | 0.16 | 212 x 306 m | 0/0 | 10 | (-1.29, +0.86) | 1.55 | 4.22 | 4.24 | (-1.81, +1.11) | -7020 | -0.584 | 1.39 | 6.0755 -> 6.0329 |
| c235f3b8 | 0.24 | 305 x 439 m | 0/1 | 36 | (-1.62, +3.83) | 4.67 | 6.19 | 6.74 | (-1.86, +3.54) | -15145 | +0.400 | 0.25 | 4.2347 -> 4.1715 |
| d82848c4 | 0.25 | 319 x 460 m | 0/0 | 30 | (+0.52, +1.26) | 1.42 | 1.76 | 2.53 | (+0.51, +1.22) | +739 | -0.122 | 0.17 | 4.0434 -> 4.0464 |
| b1d51b0f | 0.28 | 364 x 525 m | 1/2 | 83 | (+1.05, +3.21) | 4.75 | 7.49 | 9.77 | (-0.53, +3.11) | -24965 | +0.167 | 0.39 | 3.5398 -> 3.4536 |
| 59be8a98 | 0.93 | 1194 x 1722 m | 10/18 | 281 | (-2.04, +0.62) | 2.19 | 2.91 | 6.66 | (-2.02, +0.49) | +170 | +0.002 | 0.94 | 1.0803 -> 1.0805 |
| c9ff55e8 | 1.27 | 1635 x 2357 m | 4/36 | 76 | (-1.38, +0.66) | 2.00 | 3.75 | 7.68 | (-1.61, +0.77) | +723 | -0.002 | 1.58 | 0.7890 -> 0.7896 |
| 1a26bbeb | 0.57 | 742 x 1069 m | 12/17 | 256 | (-3.64, -0.37) | 3.68 | 4.37 | 4.73 | (-3.68, -0.43) | -339 | -0.045 | 0.45 | 1.7392 -> 1.7387 |
| c1064033 | 1.61 | 2078 x 2997 m | 29/55 | 185 | (-3.80, -0.07) | 3.88 | 5.35 | 7.69 | (-3.76, -0.15) | -76 | -0.043 | 1.44 | 0.6207 -> 0.6206 |
| 2f0be03d | 1.08 | 1388 x 2001 m | 19/37 | 318 | (-2.14, +0.95) | 2.74 | 3.35 | 14.80 | (-2.00, +1.14) | +488 | -0.103 | 0.96 | 0.9294 -> 0.9298 |
| 103723b0 | 1.15 | 1479 x 2133 m | 19/37 | 269 | (-1.90, +1.64) | 2.70 | 3.42 | 5.16 | (-1.97, +1.58) | +640 | -0.063 | 1.08 | 0.8721 -> 0.8726 |

Notes on the table:
- "max" includes the occasional false match. The fit is robust (3σ-MAD trimming). Use p90 and the post-fit rms.
- The fitted scale, rotation and translation are what the registration is off by; the right-hand column gives the
  NAIP-consistent px/m.
- 03dcd4ae has only 10 matches, mostly roofs and aircraft, so its fit is **low confidence**.

### Named FAA control points (registered - NAIP, and registered - FAA)

| image | point | r vs NAIP (x, z) | abs | r vs FAA (x, z) | abs | NCC |
|---|---|---|---|---|---|---|
| 8b334c52 | RWY 10L end | (+5.47, -5.11) | 7.48 | (+5.39, -5.41) | 7.63 | 0.59 |
| 8b334c52 | RWY 28R end | (-4.66, +13.97) | 14.73 | (-4.75, +13.67) | 14.47 | 0.51 |
| 8b334c52 | RWY 10R end | (+3.38, -4.28) | 5.45 | (+3.29, -4.58) | 5.65 | 0.56 |
| 8b334c52 | RWY 28L end | (-4.08, +12.19) | 12.85 | (-4.16, +11.88) | 12.59 | 0.44 |
| 8b334c52 | RWY 19R end | (+3.50, +3.50) | 4.95 | (+3.42, +3.19) | 4.68 | 0.53 |
| 8b334c52 | RWY 28R displaced thr | (-4.27, +13.90) | 14.54 | (-4.35, +13.60) | 14.28 | 0.60 |
| 8b334c52 | RWY 1L displaced thr | (-5.13, +4.29) | 6.69 | (-5.21, +3.98) | 6.56 | 0.55 |
| 8b334c52 | X 1L/10L | (-0.10, +4.39) | 4.39 | (-0.18, +4.08) | 4.08 | 0.55 |
| 8b334c52 | X 1L/10R | (-0.70, +4.82) | 4.87 | (-0.79, +4.52) | 4.58 | 0.57 |
| 8b334c52 | X 1R/10L | (-0.99, +5.32) | 5.41 | (-1.07, +5.01) | 5.13 | 0.60 |
| 8b334c52 | X 1R/10R | (-1.57, +6.06) | 6.26 | (-1.65, +5.75) | 5.98 | 0.62 |
| 1a26bbeb | RWY 28R end | (-4.32, -0.72) | 4.39 | (-4.41, -1.03) | 4.52 | 0.77 |
| 1a26bbeb | RWY 28L end | (-3.65, -0.60) | 3.70 | (-3.73, -0.91) | 3.84 | 0.69 |
| 1a26bbeb | RWY 28R displaced thr | (-4.45, -0.69) | 4.50 | (-4.53, -0.99) | 4.64 | 0.82 |
| c1064033 | RWY 28L end | (-3.28, -0.71) | 3.35 | (-3.36, -1.02) | 3.51 | 0.52 |
| c1064033 | RWY 19R end | (-4.55, -2.06) | 4.99 | (-4.63, -2.36) | 5.20 | 0.56 |
| c1064033 | RWY 19L end | (-5.16, -2.63) | 5.79 | (-5.24, -2.93) | 6.00 | 0.63 |
| c1064033 | RWY 28R displaced thr | (-3.15, +0.53) | 3.20 | (-3.23, +0.22) | 3.24 | 0.50 |
| c1064033 | X 1L/10L | (-4.34, -0.41) | 4.36 | (-4.43, -0.72) | 4.48 | 0.63 |
| c1064033 | X 1R/10L | (-4.06, -0.40) | 4.08 | (-4.14, -0.70) | 4.20 | 0.65 |
| 2f0be03d | RWY 1L displaced thr | (-1.12, +2.44) | 2.68 | (-1.20, +2.13) | 2.45 | 0.74 |
| 2f0be03d | RWY 1R displaced thr | (-1.03, +2.68) | 2.87 | (-1.11, +2.38) | 2.62 | 0.64 |
| 103723b0 | RWY 1L end | (-0.96, +2.50) | 2.67 | (-1.04, +2.19) | 2.42 | 0.49 |
| 103723b0 | RWY 1R end | (-1.37, +2.39) | 2.75 | (-1.45, +2.08) | 2.54 | 0.55 |
| 103723b0 | RWY 1L displaced thr | (-1.27, +2.30) | 2.63 | (-1.36, +1.99) | 2.41 | 0.74 |
| 103723b0 | RWY 1R displaced thr | (-1.28, +2.37) | 2.70 | (-1.36, +2.06) | 2.47 | 0.69 |

- "r vs FAA" = r vs NAIP + (NAIP − FAA). It is the error of the screenshot registration against the FAA coordinates
  themselves.
- **The HANDOFF statement that FAA runway ends "project exactly onto the imaged runway ends" (`faacheck.py`) holds only
  at the pixel scale of those crops.**
- Measured, the registrations put the runway ends **2.4–2.6 m** (103723b0, 2f0be03d), **3.2–6.0 m** (c1064033,
  1a26bbeb) and **4.1–14.5 m** (8b334c52) away from the FAA positions. [obs]

**Findings** [obs unless marked]:
1. **Common bias.** 11 of the 19 images have a fitted translation at the view centre of **x −0.8 to −2.0 m, z +0.5 to
   +1.9 m**, mean (−1.46, +1.24) m: 39176bb8, 35809e3e, 4637f855, bf5c7afc, e6f569c1, bc91df95, 03dcd4ae, 59be8a98,
   c9ff55e8, 2f0be03d and 103723b0.
   - [inf] The registrations were chained (pooled SIFT) and anchored on SFO Museum outlines and FAA ends, so they
     share this offset.
   - It cannot be attributed to Google's own georeferencing versus the chain.
2. **East-side images 1a26bbeb and c1064033 are about 3.7 m west** (r ≈ (−3.7, −0.4)). Their scale and rotation are
   fine (< 0.04 %, < 0.05°).
3. **Four close-ups have scale errors**:

   | Image | Area | Scale error |
   |---|---|---|
   | 151ec51d | G pier | **−2.44 %** |
   | b1d51b0f | B pier | **−2.50 %** |
   | c235f3b8 | E pier | **−1.51 %** (+0.40° rotation) |
   | 03dcd4ae | | about −0.7 % (low confidence) |

   Features are 5–10 m off at the image edges. The fitted scale error means reg.json's px/m is too large, so distances
   measured on these images are **1.5–2.5 % too short**.
   - [obs] **Independent corroboration.** The corrected px/m of 151ec51d (3.6503) equals that of 39176bb8 (3.6526,
     itself corrected by only −80 ppm) to 0.06 %. The corrected c235f3b8 (4.1715) equals the corrected bf5c7afc
     (4.1739) to 0.06 %.
   - [inf] Each pair was evidently captured at the same map zoom, so the original per-image scale-bar readings were off
     by 1.5–2.5 %.
   - The earlier manual fixes corrected translation only: 151ec51d "slid 17.5 m" and c235f3b8 "2.3 m" (`stand_defs.py`).
4. **The overview 8b334c52** (3.2 m/px) has a +0.13 % scale and a +0.27° rotation error. Features are 4–7 m off in the
   west and 12–16 m off at the east runway ends. Do not measure anything on it.
5. **Effect on the surveyed stands** (`data/sfo_stands.json`). Error of each stand nose = the fitted residual field of
   the image it was measured on (`tools/sat/stand_defs.py` `img`), plus the manual shifts applied there.

### Estimated stand-position error by source image (from the fitted residual field)

Stands whose nose projects outside the audited map area of their image (rows 340-2200, cols 10-1280) are extrapolations and counted separately.

| image | stands inside view | median abs err (m) | max (m) | outside view (extrapolated) |
|---|---|---|---|---|
| 151ec51d | 11 | 3.68 | 5.39 | - |
| b1d51b0f | 20 | 3.60 | 9.10 | B3 (inf) 9.8 m, B1 (inf) 9.4 m, C1 (inf) 11.2 m |
| c235f3b8 | 10 | 2.63 | 3.88 | - |
| 03dcd4ae | 8 | 2.21 | 2.86 | - |
| bf5c7afc | 13 | 2.01 | 2.35 | - |
| 39176bb8 | 14 | 1.63 | 2.20 | - |
| d82848c4 | 9 | 1.32 | 1.63 | A1 (inf) 0.8 m |

All 85 stands inside their image: median 2.16 m, p90 5.04 m, max 9.10 m; > 3 m: 21, > 5 m: 9.

   - [inf] The B- and G-pier stands also have **pitch and bridge lengths about 2.5 % too short**. That is 1.7 m on a
     70 m wide-body pitch. It matters for the wingtip-clearance checks in `check.py` and for the "planes too close"
     complaint.
   - The relative errors *between* neighbouring stands on the other images are small (scale errors < 0.45 %).

### Control points: where each was measured (accepted matches only)

| id | kind / label | NAIP world (x, z) | images (residual abs, m) |
|---|---|---|---|
| RWY 10L end | runway end (threshold bar / EMAS edge) | (-1585.0, -1102.8) | 8b334c52 7.5 |
| RWY 28R end | runway end (threshold bar / EMAS edge) | (1611.4, 584.8) | 8b334c52 14.7, 1a26bbeb 4.4 |
| RWY 10R end | runway end (threshold bar / EMAS edge) | (-1559.8, -831.1) | 8b334c52 5.4 |
| RWY 28L end | runway end (threshold bar / EMAS edge) | (1504.9, 787.0) | 8b334c52 12.9, 1a26bbeb 3.7, c1064033 3.4 |
| RWY 1L end | runway end (threshold bar / EMAS edge) | (-662.4, 1210.3) | 103723b0 2.7 |
| RWY 19R end | runway end (threshold bar / EMAS edge) | (423.8, -852.2) | 8b334c52 5.0, c1064033 5.0 |
| RWY 1R end | runway end (threshold bar / EMAS edge) | (-496.0, 1384.4) | 103723b0 2.8 |
| RWY 19L end | runway end (threshold bar / EMAS edge) | (732.3, -947.8) | c1064033 5.8 |
| RWY 28R displaced thr | displaced threshold bar (300 ft) | (1530.5, 542.1) | 8b334c52 14.5, 1a26bbeb 4.5, c1064033 3.2 |
| RWY 1L displaced thr | displaced threshold bar (640 ft) | (-571.5, 1037.7) | 8b334c52 6.7, 2f0be03d 2.7, 103723b0 2.6 |
| RWY 1R displaced thr | displaced threshold bar (560 ft) | (-416.4, 1233.4) | 2f0be03d 2.9, 103723b0 2.7 |
| X 1L/10L | runway centreline intersection | (90.0, -218.4) | 8b334c52 4.4, c1064033 4.4 |
| X 1L/10R | runway centreline intersection | (-16.5, -16.2) | 8b334c52 4.9 |
| X 1R/10L | runway centreline intersection | (292.0, -111.8) | 8b334c52 5.4, c1064033 4.1 |
| X 1R/10R | runway centreline intersection | (185.5, 90.4) | 8b334c52 6.3 |
| A03 | Taxiway C1/U | (-1614.5, -1271.5) | 8b334c52 8.7 |
| A04 | RUNWAY 10L/28R | (-1572.5, -1103.5) | 8b334c52 7.3 |
| A05 | paved area (apron/service, not an SFO Museum taxiway) | (-1289.5, -1100.5) | 8b334c52 5.8, 59be8a98 1.9, c9ff55e8 1.8 |
| A08 | paved area (apron/service, not an SFO Museum taxiway) | (721.5, -1109.5) | c1064033 7.5 |
| A10 | Taxiway S2/S3 | (-1622.5, -1013.5) | 8b334c52 6.3 |
| A11 | RUNWAY 10L/28R | (-1574.5, -1099.5) | 8b334c52 7.4 |
| A12 | Taxiway R | (-1331.5, -876.5) | 8b334c52 7.1 |
| A15 | paved area (apron/service, not an SFO Museum taxiway) | (-126.5, -1052.5) | 8b334c52 3.1 |
| A17 | paved area (apron/service, not an SFO Museum taxiway) | (190.5, -898.5) | 8b334c52 5.1 |
| A18 | paved area (apron/service, not an SFO Museum taxiway) | (722.5, -1099.5) | c1064033 7.7 |
| A19 | Taxiway Z/Z2 | (-1733.5, -793.5) | 8b334c52 5.9 |
| A20 | paved area (apron/service, not an SFO Museum taxiway) | (-1564.5, -829.5) | 8b334c52 6.0 |
| A21 | paved area (apron/service, not an SFO Museum taxiway) | (-766.5, -753.5) | 8b334c52 3.1, 59be8a98 2.1 |
| A22 | Taxiway D | (-556.5, -617.5) | 8b334c52 1.4, 59be8a98 1.7 |
| A23 | paved area (apron/service, not an SFO Museum taxiway) | (-0.5, -714.5) | 8b334c52 5.0 |
| A24 | RUNWAY 01L/19R | (399.5, -794.5) | c1064033 5.5 |
| A25 | RUNWAY 01L/19R | (400.5, -793.5) | c1064033 5.4 |
| A28 | paved area (apron/service, not an SFO Museum taxiway) | (-1540.5, -507.5) | 59be8a98 6.7 |
| A29 | Taxiway Z/B1/B2 | (-1334.5, -484.5) | 35809e3e 1.8, 59be8a98 1.9 |
| A30 | paved area (apron/service, not an SFO Museum taxiway) | (-619.5, -515.5) | 59be8a98 2.2 |
| A31 | Taxiway T | (-420.5, -382.5) | 35809e3e 2.6, 2f0be03d 2.8 |
| A32 | Taxiway T | (-302.5, -377.5) | 59be8a98 2.8, 2f0be03d 3.1 |
| A33 | Taxiway C | (115.5, -354.5) | 8b334c52 5.4, c1064033 3.8 |
| A36 | paved area (apron/service, not an SFO Museum taxiway) | (-1843.5, -201.5) | 8b334c52 2.1, c9ff55e8 2.9 |
| A37 | apron near Boarding Area G | (-1544.5, -165.5) | 8b334c52 1.4, 35809e3e 1.7, e6f569c1 2.2, c9ff55e8 2.1 |
| A42 | Taxiway E | (-166.5, -267.5) | 59be8a98 3.0, 2f0be03d 3.5, 103723b0 3.8 |
| A43 | RUNWAY 01L/19R | (74.5, -166.5) | 8b334c52 5.1, 2f0be03d 3.5 |
| A44 | RUNWAY 01R/19L | (331.5, -144.5) | 8b334c52 5.2, c1064033 3.3, 2f0be03d 3.2 |
| A45 | paved area (apron/service, not an SFO Museum taxiway) | (-1881.5, -12.5) | 8b334c52 3.2, c9ff55e8 3.6 |
| A46 | paved area (apron/service, not an SFO Museum taxiway) | (-1844.5, 19.5) | 8b334c52 3.4 |
| A47 | apron near Boarding Area E | (-610.5, -88.5) | 2f0be03d 2.8 |
| A48 | Taxiway A | (-599.5, -96.5) | 2f0be03d 2.7 |
| A49 | Taxiway A | (-340.5, 142.5) | 8b334c52 4.2, 35809e3e 2.7, 59be8a98 2.9, c1064033 2.7, 103723b0 2.7 |
| A50 | RUNWAY 01R/19L | (149.5, 118.5) | 8b334c52 6.5, c1064033 3.1, 2f0be03d 3.2, 103723b0 3.3 |
| A51 | RUNWAY 01R/19L | (177.5, 128.5) | 8b334c52 6.6, c1064033 2.2, 2f0be03d 3.1, 103723b0 3.4 |
| A53 | paved area (apron/service, not an SFO Museum taxiway) | (650.5, 149.5) | 8b334c52 9.4, c1064033 4.1 |
| A54 | Taxiway C/N | (997.5, 148.5) | 8b334c52 10.4, c1064033 4.3 |
| A56 | apron near Boarding Area G | (-1381.5, 337.5) | 8b334c52 7.6 |
| A57 | apron near Boarding Area G | (-1336.5, 390.5) | 8b334c52 7.9 |
| A58 | Taxiway A | (-386.5, 290.5) | 8b334c52 3.2 |
| A59 | Taxiway A/F1 | (-339.5, 154.5) | 8b334c52 3.8, 35809e3e 2.7, 59be8a98 2.8, c1064033 2.7, 103723b0 2.8 |
| A60 | RUNWAY 01R/19L | (119.5, 231.5) | 8b334c52 7.0, c1064033 3.1, 2f0be03d 2.9, 103723b0 3.3 |
| A61 | Taxiway F | (186.5, 267.5) | 8b334c52 8.1, c1064033 3.7, 2f0be03d 2.5 |
| A62 | Taxiway P | (649.5, 292.5) | 8b334c52 8.2, c1064033 2.7 |
| A63 | paved area (apron/service, not an SFO Museum taxiway) | (670.5, 206.5) | 8b334c52 7.9, c1064033 3.9 |
| A64 | Taxiway N | (909.5, 320.5) | 8b334c52 11.4, 1a26bbeb 3.4, c1064033 3.7 |
| A67 | apron near Boarding Area A | (-1316.5, 431.5) | 8b334c52 7.5 |
| A69 | Taxiway B/G | (-426.5, 549.5) | 8b334c52 8.0, 2f0be03d 2.6, 103723b0 2.6 |
| A71 | Taxiway N | (889.5, 407.5) | 8b334c52 10.6, 1a26bbeb 3.3, c1064033 3.4 |
| A72 | paved area (apron/service, not an SFO Museum taxiway) | (900.5, 429.5) | 8b334c52 10.9, 1a26bbeb 3.3, c1064033 3.1 |
| A73 | RUNWAY 10L/28R | (1376.5, 463.5) | 1a26bbeb 4.2 |
| A75 | paved area (apron/service, not an SFO Museum taxiway) | (1677.5, 618.5) | 8b334c52 16.1, 1a26bbeb 4.4 |
| A76 | apron near Boarding Area A | (-1469.5, 808.5) | 8b334c52 4.8, 35809e3e 2.7, 0af09b78 1.2 |
| A77 | apron near Boarding Area A | (-1149.5, 883.5) | 8b334c52 4.7, 35809e3e 3.0, 0af09b78 0.8, 2f0be03d 3.3, 103723b0 3.0 |
| A78 | apron near Boarding Area B | (-1094.5, 896.5) | 8b334c52 4.7, 35809e3e 2.3, 0af09b78 0.7, b1d51b0f 3.9, 2f0be03d 2.4, 103723b0 2.4 |
| A79 | Taxiway B/H | (-600.5, 894.5) | 8b334c52 7.0, 103723b0 2.8 |
| A80 | Taxiway B/H | (-598.5, 894.5) | 8b334c52 6.9, 2f0be03d 3.1, 103723b0 2.9 |
| A81 | Taxiway F | (1119.5, 804.5) | 1a26bbeb 3.2 |
| A82 | RUNWAY 10R/28L | (1399.5, 746.5) | c1064033 3.6 |
| A84 | paved area (apron/service, not an SFO Museum taxiway) | (1650.5, 732.5) | 1a26bbeb 4.1, c1064033 5.7 |
| A85 | paved area (apron/service, not an SFO Museum taxiway) | (-1702.5, 927.5) | 8b334c52 5.8, 35809e3e 3.1 |
| A86 | apron near Boarding Area A | (-1149.5, 900.5) | 8b334c52 4.6, 35809e3e 2.0, 0af09b78 0.7, 2f0be03d 2.3, 103723b0 2.2 |
| A89 | RUNWAY 01L/19R | (-569.5, 1043.5) | 8b334c52 6.8, 2f0be03d 2.7, 103723b0 2.6 |
| A90 | Taxiway F | (1345.5, 919.5) | 8b334c52 14.5, 1a26bbeb 3.3, c1064033 3.8 |
| A91 | Taxiway F | (1402.5, 921.5) | 8b334c52 14.6, 1a26bbeb 3.5, c1064033 3.4 |
| A96 | Taxiway L | (-630.5, 1503.5) | 103723b0 3.2 |
| A98 | paved area (apron/service, not an SFO Museum taxiway) | (-319.5, 1473.5) | 103723b0 4.3 |


---------------------------------------------------------------------------------------------------------------------

## 6. SFO Museum building outlines vs NAIP (task d) — `tools/imagery/outline_audit.py`

**Method.**
- The outlines are `terminalComplex`, `terminals`, `boardingAreas` and the garage/hotel/hangar/ATC `structures` in
  `data/sfo_airport.json`.
- Each outline edge ≥ 15 m is compared with NAIP. The strongest parallel edge within ±14 m of the edge line, taken as the
  median along the edge, gives a signed outward offset.
- Summary per building: the length-weighted median offset of the edges facing ±s (ESE/WNW) and ±t (NNE/SSW). A pure
  translation shows as opposite signs (the "shift"); a size difference shows as equal signs (the "growth").

| Building | NAIP 2024: shift along s (ESE) / t (NNE), m | growth s / t | NAIP 2022: shift s / t | ⇒ world (x, z) 2024 |
|---|---|---|---|---|
| Terminal complex (161 edges) | **+4.1 / +3.1** | +2.6 / +0.1 | +4.6 / +3.5 | (+5.0, −0.8) |
| Harvey Milk Terminal 1 | +4.1 / +2.9 | +2.6 / +0.1 | +3.4 / +2.5 | (+5.0, −0.7) |
| International Terminal | +3.4 / +3.8 | +4.2 / +0.3 | +4.2 / +4.1 | (+4.8, −1.7) |
| Terminal 2 | +9.4 / +2.2 | −3.6 / +0.2 | +5.4 / +2.7 | (+9.3, +2.5) |
| Terminal 3 | +2.1 / +2.8 | −0.7 / −0.5 | +4.8 / +2.9 | (+3.2, −1.5) |
| Boarding Area A | +3.3 / n/a | +3.9 / n/a | +3.8 / n/a | |
| Boarding Area B | +1.2 / +2.4 | −0.4 / +0.6 | −0.6 / +2.6 | (+2.2, −1.5) |
| Boarding Area C | +7.7 / +7.2 (6 edges) | −0.3 / −4.2 | +8.0 / +7.5 | (+10.2, −2.8) |
| Boarding Area D | +7.9 / +2.3 | −2.4 / +0.1 | +5.4 / +1.9 | (+8.0, +1.6) |
| Boarding Area E | n/a / +6.3 (5 edges) | | +5.8 / +6.6 | |
| Boarding Area F | +3.6 / +1.9 | −0.9 / 0.0 | +2.9 / +2.6 | (+4.1, 0.0) |
| Boarding Area G | n/a / +4.0 | n/a / −0.2 | n/a / +4.2 | |
| Super Bay Hangar | −6.0 / −1.2 | +3.4 / +4.2 | too few edges | (−5.8, −1.8) |
| All 501 accepted edges | \|offset\| median 4.3 m, p90 11.6 m; within 1 m 10 %, 2 m 25 %, 5 m 57 % | | 465 edges: 4.4 / 11.1 m | |

**Interpretation.**
- The offsets are dominated by **NAIP relief displacement**, not by outline errors:
  - [obs] NAIP is orthorectified to a terrain DEM (metadata: "the 2018 or newer HxIP DEM"), not to a surface model.
  - [obs] In both 2022 and 2024 the **ATC tower cab appears about 38–40 m east of the tower base**, with the shaft
    visible in between. This is a visual estimate on a 10 m grid (±3 m); the image is
    `refs/cache/naip/tower_lean.jpg` (`tools/imagery/tower_lean.py`). The edge overlay for the terminal area is
    `outline_audit_2024.jpg`.
  - The tower is about 67 m (221 ft) tall [unverified here]. That implies a lean of about 0.57 m per metre of height,
    to the east, around the terminal core.
  - [inf] Roof edges 8–15 m high would then shift 4.5–8.5 m east, which is the size of the measured terminal-complex
    shift (+5 m east).
- [obs] The shift is the same in 2022 and 2024. [inf] Both flights apparently used a similar flight-line geometry,
  consistent with the NAIP metadata ("flight lines have been designed with a north/south orientation"). The nadir was
  about 2.5 km west of the terminals.
- [obs] The Super Bay Hangar shifts *west*, and the garages vary. [inf] Those areas come from other source frames or
  strips.
- Independent indirect evidence [inf]:
  - the Google screenshots were registered by chamfer-matching their roofs to the SFO Museum outlines (`register.py`);
  - on *ground* features they still agree with NAIP to about 1–2 m (§5);
  - so the outlines match Google's roofs to about 1.5 m;
  - NAIP's roofs, by contrast, are displaced.

**Verdict.**
- The outlines are **consistent with NAIP within the uncertainty of NAIP roof lean**, about ±5–10 m.
- **NAIP cannot verify them better than that**.
- A lean-free check needs one of:
  - lidar: none public over SFO in the 3DEP bucket;
  - a true orthophoto: possibly the 15 cm San Mateo County 2022 ortho, if the County grants access;
  - a check on wall bases and ground-level features. With NAIP this is only possible on facades facing the nadir (the
    west side); I did not do it.

---------------------------------------------------------------------------------------------------------------------

## 7. Recommendations

**Imagery.**
1. **Adopt NAIP 2024 as the project's georeferenced ground truth and as the only redistributable imagery.**
   - Credit line: *"Imagery: USDA NAIP 2024, USDA FPAC Business Center – Geospatial Enterprise Operations (public
     domain)"*.
   - If it is used as a texture, the owner decides first (CLAUDE.md rule). Also mask or inpaint the parked aircraft and
     vehicles, and do not use it for roofs.
2. Keep NAIP 2022 as a second epoch. The recorder's ADS-B and the 2024 imagery are 2+ years apart, so stands and paint
   may have changed. Check against the Google screenshots [unverified: their capture date is unknown]. Their tiles
   carry a faint "© 20.. Google" watermark. The year is not legible in my crops, and it would be a copyright year in any
   case, not a capture date.
3. **Ask San Mateo County GIS (countygis@smcgov.org) for licence terms** for the 2022 0.5 ft (15 cm) ortho. It is the
   only public-sector source sharp enough for markings and GSE. Until then, it is not usable as a texture and not open.
4. Optional independent check: the NOAA NGS 2018 mosaic (0.5 m, ±1.5 m CE95, public domain).

**Projection.**
5. **Replace the equirectangular formula in `js/geo.js`** with the exact GRS80 local tangent plane (§4.4), in one change
   together with all builders.
   - Convert measured world-metre data with `tools/imagery/migrate_world.py`: shifts of 1–2 m on the terminal complex,
     negligible relative change.
   - Rebuild everything that comes from lat/lon.
   - Re-render the NAIP world PNG with `--proj ltp`.
6. **Declare the world datum as NAD83(2011)**, matching FAA and NAIP.
   - Apply ADS-B → NAD83(2011) as a constant (x +1.57 m, z +0.16 m), with a comment giving the epoch.
   - Never let a GIS tool apply its default null NAD83↔WGS84 transformation silently.

**Screenshot registrations and stands.**
7. **Replace the screenshot registrations with the NAIP-corrected ones** (`refs/cache/naip/reg_naip.json`), after
   owner/maintainer review.
   - Priority: 151ec51d, b1d51b0f, c235f3b8, then 1a26bbeb, c1064033 and 8b334c52.
   - Then correct what was measured on them:
     - **Stands** are hand-entered world coordinates in `tools/sat/stand_defs.py`, so they do not follow a new
       registration automatically. Correct each nose by subtracting its estimated error
       (`reg_audit.json` → `stand_error_estimates[].err`, which already includes the manual 151ec51d / c235f3b8
       shifts): new = current − err. Better still, re-measure on the corrected registrations. In either case the manual
       shifts in `stand_defs.py` are then superseded.
     - **Red boxes, paint and pavement** come from pipelines that read `reg.json`, so re-run them with the corrected
       similarities.
   - Afterwards, re-run `check.py` and `check_bridges.py`. The G- and B-pier pitch grows by about 2.5 %.
8. Stop using the SFO Museum outlines as the *registration target*. Roof outlines carry an unknown datum and relief. Use
   NAIP ground features, as `reg_audit.py` does. `match.py` can be reused for new screenshots.
9. **SFO Museum outlines: no correction from NAIP.** The measured 5 m is NAIP roof lean. If metre-level building
   footprints are needed, obtain lidar or a true ortho, for example the San Mateo County request above.

---------------------------------------------------------------------------------------------------------------------

## 8. Open questions / not verified

- **NAD83 realisation of the FAA/AirNav runway-end coordinates** [unverified]. AirNav gives no realisation. That NAIP
  agrees with FAA to 0.3 m suggests NAD83(2011), or a close one. NAD83(1986) would differ by 0.9 m (NCAT).
- **Bay Area intraplate velocity** since 2010.0 is not included in the 1.58 m datum shift. HTDP could not be run here.
  Estimated 0.2–0.4 m NW [inf].
- **The "±4 m from 2016" NAIP accuracy figure** is seen only on secondary pages. The USDA original found is the 2015 info
  sheet (6 m at 95 %). This does not matter for SFO, where NAIP was measured at 0.3–0.9 m.
- **OpenAerialMap** could not be queried (API errors). **USGS EarthExplorer HRO** was not checked (login required).
- **San Mateo County imagery licence**: only the disclaimer text was found. Written terms are needed before any use
  beyond reference.
- **Height of the ATC tower** (≈ 67 m / 221 ft) was not verified here. The tower lean of about 38–40 m is a visual
  estimate (±3 m).
- **Roof heights of the terminals** are unknown, so the lean-per-height argument in §6 is qualitative.
- **Datum and provenance of the SFO Museum geometry** are unknown: source CAD, and whether a NAD83→WGS84 transform was
  applied.
- **Google imagery date(s)** are unknown. The acquisition epoch of each screenshot is not recorded.
- **03dcd4ae** has only 10 usable matches. Its fitted correction (−0.7 %, −0.58°) is low confidence. Re-measure the stands
  on it from an overlapping, better-constrained image.
- **Stands measured outside the valid map area of their image** (B1, B3, C1 on b1d51b0f; A1 on d82848c4, all `inf`):
  their error estimates are extrapolations.
- **Automatic control points on vegetation or soil** were excluded (pavement only). Points A04/A11, A24/A25 and A79/A80
  are near-duplicates at cell borders; this is harmless.
- **The ADS-B datum offset could be verified empirically** from the recorder (`refs/cache/rec`): the mean lateral offset
  of take-off rolls from the FAA centrelines should be about 1.5 m on 1/19 and 0.6 m on 10/28. Not done.

---------------------------------------------------------------------------------------------------------------------

## 9. Reproduce

```bash
# (a) imagery
python3 tools/imagery/naip_fetch.py --source usda --year 2024      # USDA image service -> refs/cache/naip/naip_2024_sfo_utm10n.tif
python3 tools/imagery/naip_fetch.py --year 2022                     # Planetary Computer (SAS token) -> naip_2022_sfo_utm10n.tif
python3 tools/imagery/naip_world.py --year 2024 --res 0.5 --tiles 2048   # world-grid PNG + JSON (+ --proj ltp / --wgs84)
# accuracy of NAIP
python3 tools/imagery/naip_faa_check.py --year 2024                 # vs FAA runway ends
python3 tools/imagery/naip_interyear.py                             # 2022 vs 2024 on the ground
# (b) projection / datum
python3 tools/imagery/projection_audit.py
python3 tools/imagery/migrate_world.py data/sfo_stands.json refs/cache/naip/sfo_stands_ltp_DEMO.json   # dry run
# (c) screenshots (needs tools/sat/screens/)
python3 tools/imagery/reg_audit.py && python3 tools/imagery/report_tables.py
# (d) outlines
python3 tools/imagery/outline_audit.py --year 2024 ; python3 tools/imagery/outline_audit.py --year 2022
```

Shared helpers:
- `common.py`: geo.js and exact projections, the NAIP sampler, the AOI and FAA ends;
- `screens.py`: loading screenshots and `reg.json`, with the UI mask from `tools/sat/featreg.py`;
- `match.py`: masked NCC matching.

All saved source pages, quoted metadata and API responses are in `refs/cache/naip/src/`.
