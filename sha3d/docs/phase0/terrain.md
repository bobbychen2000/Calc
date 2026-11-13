# Phase 0: terrain, land cover and open imagery for ZSSS (KEY = terrain)

Research note for SHA Live 3D. Checked on **2026-11-13**. The downloads are in `sha3d/refs/cache/{dem,landcover,imagery,licences}/`
and in three sub-folders of `sha3d/refs/cache/osm/`: `api_map_zsss/`, `api_map_north/` and `derived_zsss/`.
`osm/` is shared with another agent, so I did not touch its top-level files.
Each folder has a `SOURCES.json` giving the URL, date, quoted licence, redistribution status and sha256 of every file.
The scripts are in `sha3d/tools/terrain/`. Every script that reads a download runs with `python3 -I`.

**Legend.**
- **[obs]**: I measured it, or read it in the cited original, in this session.
- **[inf]**: I inferred or reasoned it from observations.
- **[unverified]**: I could not check it against an original source.

Fact status follows the owner's scale:
- **verified**: I read a primary or official source.
- **secondary**: only a secondary source.
- **unverified**: no source checked.
- **contradicted**: the sources disagree, and both are given.

Geometry is WGS-84 throughout. No GCJ-02 data was touched. No Google, Baidu or Amap imagery was used.

---

## 0. Summary

1. **DEM.** The ZSSS tile is Copernicus GLO-30 `Copernicus_DSM_COG_10_N31_00_E121_00_DEM`, covering 31–32 N and 121–122 E.
   - **Airfield heights [obs]** (EGM2008 heights; the DEM is a DSM):
     - OSM aerodrome polygon, 6.69 km²: median **1.50 m**, p05–p95 0.96–4.48 m.
     - Runway centrelines: 18L/36R median **1.0 m**; 18R/36L median **1.5 m**. Both range 1.0–2.0 m.
     - Probe at the OurAirports ARP: 1.51 m.
   - **The airfield heights are edited [obs].** 54 % of the aerodrome pixels carry Editing-Mask code **5 = "Airport editing"**. Two-thirds of those pixels sit exactly on 0.5 m steps (1.0 / 1.5 / 2.0 m).
     - These are WorldDEM's flattened airport planes, not measured runway profiles.
     - Do not derive runway slopes from them.
   - **Against the "~3 m" field elevation:** the DEM is about 1.5 m lower.
     - **[obs]** Shanghai's local Wusong height datum is **H_Wusong = H_1985 + 1.680 m**. Source: an official notice from the Shanghai Municipal Bureau of Planning and Natural Resources, 2022.
     - **[inf]** A 3 m figure in Wusong height would be about 1.3 m in the 1985 national datum. That is consistent with the DEM's 1.5 m on EGM2008 to a few decimetres.
     - **[unverified]** I did not check which datum the AIP elevation uses. That belongs to the AIP key.
   - **GLO-90** gives the same picture: aerodrome median 1.51 m.
2. **DEM licence.** GLO-30 and GLO-90 each have their own "Full, Free & Open" licence.
   - Both grant reproduction, distribution, communication to the public, and adaptation.
   - Both require a fixed © notice and a liability sentence.
   - The two licences are word-for-word the same apart from the product name and the higher-resolution products excluded from scope.
   - **Redistributing a crop is allowed.** It must carry the "produced using Copernicus WorldDEM-30 …" notice and the liability sentence. Both are embedded in our crop's GeoTIFF tags.
   - **Packaging bug [obs]:** the `eula_F.pdf` shipped in the AWS **GLO-90** tile is *not* the GLO-90 licence. It is the restricted ESA user licence for GLO-30-R / EEA-10-R.
3. **WorldCover 2021 v200** (tile N30E120). Class shares in the 20 km box (2518×2165 px at 8.33e-5°, about 7.9 m E–W × 9.2 m N–S):
   - built-up 64.2 %, tree cover 18.9 %, cropland 8.8 %, grassland 3.8 %, bare 2.7 %, permanent water **1.6 %**.
   - Inside the aerodrome: built-up 59.0 %, "cropland" 19.9 %, grassland 10.1 %, bare 9.5 %, water 1.35 %.
   - The airfield's mown grass infields come out mostly as *cropland*: a misclassification **[inf]**.
   - Licence: **CC BY 4.0**, with a required attribution text (§3).
4. **Open imagery sharper than 10 m over ZSSS:**
   - **Umbra SAR open data** has a **0.35 m X-band spotlight scene centred on the airport** (2024-06-02), licensed **CC BY 4.0**.
     - This is the only open, redistributable sub-10 m image of the airfield I found.
     - It is radar, not optical: use it as a geometry reference (runways, taxiways, aprons, canals), not as a texture.
     - The GEC (geocoded, ellipsoid-corrected) product's runway dark bands sit **3–4 m east of the OSM centrelines [obs]**. That fits a terrain-height projection effect **[inf]**.
   - **CNES SPOT World Heritage** has cloud-free SPOT 5 scenes over ZSSS from 2011-12-31, 2012-11-07 and 2012-12-24, at 5 m pan (2.5 m via THR).
     - **The licence is contradicted:** CNES REGARDS says Etalab Open 2.0; Theia says non-commercial only.
   - **No coverage of the airfield** from: SpaceNet AOI_4_Shanghai (WorldView-3, Pudong only), Satellogic EarthView 1 m (nearest tile 2.3 km east of the ARP), OpenAerialMap, Maxar Open Data (also CC BY-NC), Capella (nearest 10 km east) and INPE CBERS-4A.
   - JAXA AVNIR-2 ORI is 10 m, so it is no better.
   - Landsat is 15/30 m and public domain.
5. **Water and transport hub context:**
   - **[obs, OSM]** A perimeter canal system runs close round the field: 机场河 about 4 m from the aerodrome boundary, 北横泾 about 19 m, plus unnamed canals and ditches. 新泾港 (Xinjing Gang) is about 1.2 km away. Suzhou Creek (吴淞江) is about 2.6 km north of the north runway end.
   - **[obs]** Shanghai Hongqiao Station (OSM way 70364443) is 1.72 km west-south-west (bearing 262° from the ARP). It sits 1.55 km west of the 18R/36L midpoint, past Terminal 2. In WorldCover, the 1.5 km box around the station is 75 % built-up.
6. **Sentinel-2.** I recorded the Copernicus legal notice verbatim (§6). Credit line: "Contains modified Copernicus Sentinel data [Year]".
   - I saved a cloud-free 20 km TCI crop at 10 m: tile **51RUQ**, 2026-10-14. Clouds cover 0.22 % of the crop (SCL classes 8–10).

---

## 1. Facts table

All rows checked 2026-11-13.

| # | Fact | Value | Source URL | Quote (verbatim, short) | Status |
|---|---|---|---|---|---|
| 1 | GLO-30 tile covering ZSSS | `Copernicus_DSM_COG_10_N31_00_E121_00_DEM` (41 MB COG, 3600×3600, 1″) | https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N31_00_E121_00_DEM/ | bucket listing; GeoTIFF bounds 120.99986–121.99986 E, 31.00014–32.00014 N | verified [obs] |
| 2 | Bucket processing | "removed these shared rows and columns on east and south edges"; "[resolution] … 10 for GLO-30, and 30 for GLO-90" | https://copernicus-dem-30m.s3.amazonaws.com/readme.html | as quoted | verified |
| 3 | Vertical datum | EGM2008 (EPSG:3855); horizontal WGS84-G1150 | tile XML `Copernicus_DSM_10_N31_00_E121_00.xml`; Product Handbook i5.0 | XML: `vertical: "WGS 84 Geoid EGM08"`, `horizontal: "WGS84-G1150"`; PH: "The vertical reference datum is the Earth Gravitational Model 2008 (EGM2008; EPSG 3855)." | verified |
| 4 | Data type | DSM, not bare earth | https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf | "The Copernicus DEM is a Digital Surface Model (DSM) which represents the surface of the Earth including buildings, infrastructure and vegetation." | verified |
| 5 | Airport editing exists | yes | same PH | "Editing of shore- and coastlines, special features such as airports and implausible terrain structures has also been applied." | verified |
| 6 | EDM code 5 | "Airport editing" (Table 6) | same PH | "5 Airport editing" | verified |
| 7 | TanDEM-X acquisitions over ZSSS | 2011-09-07, 2011-09-18 (first), 2012-10-18 (second) | tile `PREVIEW/…_SRC.kml` | "Acquisition Date: 2011-09-07T09:53" … "2012-10-18T09:53" | verified [obs] |
| 8 | Tile absolute vertical accuracy | LE90 1.920 m, LE68 1.346 m (3654 ICESat points) | tile `AUXFILES/…_ACM.kml` | `Absolute Vertical Accuracy LE_90 [m] 1.920` | verified [obs] |
| 9 | GLO-30 heights, aerodrome polygon (OSM rel 21913346) | n=8210; median 1.50, mean 2.06, p05 0.96, p95 4.48, max 30.78 m | computed, `dem/derived_zsss/dem_stats_zsss.json` | — | verified [obs] |
| 10 | GLO-30 runway centrelines (30 m step) | 18L/36R: median 1.0, mean 1.28, 1.0–2.0; 18R/36L: median 1.5, mean 1.43, 1.0–2.0 m | same | — | verified [obs] |
| 11 | Airport-edited pixels | 4419 of 8210 aerodrome px (53.8 %); median 1.5; 66.8 % exact 0.5 m multiples | computed from EDM + DEM | — | verified [obs] |
| 12 | Unedited DEM inside aerodrome | median 1.74 m (p25 1.37, p75 2.28); HEM median 0.83, p95 1.5 m | computed | — | verified [obs] |
| 13 | GLO-90 at ZSSS | aerodrome median 1.51 m; ARP 1.58 m; runways median 1.38 / 1.51 m | `Copernicus_DSM_COG_30_N31_00_E121_00_DEM` | — | verified [obs] |
| 14 | 20 km box DEM | median 4.70, p05 1.44, p95 10.27, max 41.94 m (DSM: roofs/trees) | computed | — | verified [obs] |
| 15 | Field elevation "~3 m" | 3 (OSM tag `ele=3`, `source=wikipedia`); AIP value not checked here | https://api.openstreetmap.org/api/0.6/relation/21913346/full | `ele=3` | secondary (AIP: unverified) |
| 16 | Shanghai Wusong vs 1985 national height | H_Wusong = H_1985 + 1.680 m | https://ghzyj.sh.gov.cn/cmsres/e6/e6d80f66205b45c8adb7a61dbca37905/636d66c646db3f56caa61dc4f1c87301.pdf | "H 吴淞=H1985+1.680(m)" | verified |
| 17 | EGM2008 undulation at ARP | N = +11.24 m (nearest node, 2.5′ grid) | https://cdn.proj.org/us_nga_egm08_25.tif | grid tag: "WGS 84 (EPSG:4979) to EGM2008 height (EPSG:3855)" | verified [obs] |
| 18 | GLO-30 licence: rights | reproduction, distribution, communication to public, adaptation | `INFO/eula_F.pdf` in tile = https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf (identical text) | "(a) reproduction; (b) distribution; (c) communication to the General Public; (d) adaptation, modification and combination with other data and information." | verified |
| 19 | GLO-30 notice (modified) | "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved" | same | as quoted, Art. 6(b) | verified |
| 20 | GLO-30 liability sentence | "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30" | same | Art. 6(c) | verified |
| 21 | GLO-90 licence | "Licence for COP-DEM-GLO-90-F Global 90m Full, Free & Open", same Art. 4/6 with "WorldDEM™-90" | https://dataspace.copernicus.eu/sites/default/files/media/files/2025-06/copernicus_contributing_mission_data_access_v2_cop_dem_licenses.pdf | "The higher resolutions, Copernicus WorldDEM™-30 and WorldDEM™-10 are subject of a separate licence" | verified |
| 22 | AWS GLO-90 shipped EULA | wrong document: ESA user licence for GLO-30-R / EEA-10-R | https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_N31_00_E121_00_DEM/INFO/eula_F.pdf | "Licence for the use of Copernicus DEM instances COP-DEM-GLO-30-R and COP-DEM-EEA-10-R" | contradicted (AWS file vs CDSE licence) |
| 23 | Free licence for both | yes | https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM | "The GLO-30 and GLO-90 datasets are available worldwide with a free license." | verified |
| 24 | WorldCover tile | `ESA_WorldCover_10m_2021_v200_N30E120_Map.tif`, 120–123 E, 30–33 N, uint8, nodata 0 | https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N30E120_Map.tif | — | verified [obs] |
| 25 | WorldCover licence | CC BY 4.0 | https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/docs/WorldCover_PUM_V2.0.pdf §5.1 | "The WorldCover product is provided free of charge, without restriction of use. For the full license information see the Creative Commons Attribution 4.0 International License" | verified |
| 26 | WorldCover attribution | "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium" | same §5.2 | "With year either 2020 or 2021 for the WorldCover 2020 and 2021 map, respectively" | verified |
| 27 | WorldCover citation | Zanaga et al. 2022, ESA WorldCover 10 m 2021 v200, doi:10.5281/zenodo.7254221 | same §5.2 | as quoted | verified |
| 28 | WorldCover v200 accuracy | global OA 76.7 %; Asia 82.1 % | same PUM | "highest accuracy of 82.1% for Asia" | verified |
| 29 | Sentinel-2 legal notice | free use for (a)–(e); credit "Copernicus Sentinel data [Year]" or "Contains modified Copernicus Sentinel data [Year]" | https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice | see §6 | verified |
| 30 | S2 tile over ZSSS | MGRS 51RUQ (UTM 51N); best recent: S2B_T51RUQ_20261014T024532_L2A, 1.98 % tile cloud | https://earth-search.aws.element84.com/v1/search | — | verified [obs] |
| 31 | Umbra scene over ZSSS | 2024-06-02T01:46:48Z, UMBRA_05, spotlight, X-band VV, incidence 38.1°, GEC 0.35 m, footprint 121.3078–121.3650 E, 31.1701–31.2193 N, centre 121.33640 E 31.19470 N | https://umbra-open-data-catalog.s3.amazonaws.com/sar-data/tasks/ad%20hoc/Shanghai_CHN/96b8bdc7-96bf-415e-b43b-20adc327995f/2024-06-02-01-46-47_UMBRA-05/2024-06-02-01-46-47_UMBRA-05_METADATA.json | `"sceneCenterPointLla": … [121.33640219170886, 31.194698496358967 …]` | verified [obs] |
| 32 | Umbra licence | CC BY 4.0 | https://registry.opendata.aws/umbra-open-data/ | "All data is provided with a Creative Commons License ( CC by 4.0 ), which gives you the right to do just about anything you want with it." | verified (provider's registry entry) |
| 33 | Umbra GEC vs OSM runways | dark band centred 4 m (18L/36R) and 3 m (18R/36L) **east** of OSM centrelines; band width 72–74 m | computed, `tools/terrain/gec_runway_check.py` | — | verified [obs]; cause [inf] |
| 34 | SpaceNet AOI_4_Shanghai footprint | 121.590–121.748 E, 30.828–31.427 N (WorldView-3 2015-06-06): no ZSSS | https://spacenet-dataset.s3.amazonaws.com/AOIs/AOI_4_Shanghai/PS-MS/15JUN06023537-S2AS-056155973070_01_P001.IMD | `ULLon = 121.59017055;` … | verified [obs] |
| 35 | SpaceNet licence | CC BY-SA 4.0 (bucket) vs DigitalGlobe "dissemination … prohibited" (README in product) | https://spacenet-dataset.s3.amazonaws.com/LICENSE.md | "licensed under a Creative Commons Attribution-ShareAlike 4.0 International License" | contradicted (moot: no coverage) |
| 36 | Satellogic EarthView near ZSSS | 1 m, Jul–Dec 2022, CC-BY-4.0; nearest 384 m tile UL (343390 E, 3451744 N, UTM 51N) = 2.3 km E of ARP; none over airfield | https://satellogic-earthview.s3.us-west-2.amazonaws.com/index.html | `"license": "CC-BY-4.0"` | verified [obs] |
| 37 | SPOT World Heritage over ZSSS | 845 SPOT 5 scenes 2002–2014; cloud ≤10 % after 2010-03: 2011-12-31, 2012-10-02, 2012-11-07, 2012-12-24, 2013-07-08 (pan A/B, THR pairs) | https://geodes-portal.cnes.fr/api/stac/search (collection SWH_SPOT5_L1) | — | verified [obs] |
| 38 | SPOT SWH licence | Etalab Open 2.0 **vs** non-commercial only | https://regards.cnes.fr/html/swh/Home-swh3.html ; https://www.theia-land.fr/blog/produits/spot-world-heritage | "Spot 1-5 archives images are subject to Open 2.0 ETALAB Licence." vs "Non-Exclusive Licence to Use Spot Archive Product for Non-Commercial Purpose Only." | contradicted |
| 39 | Maxar Open Data | no China event; CC BY-NC 4.0 | https://maxar-opendata.s3.amazonaws.com/events/catalog.json | `"license": "CC-BY-NC-4.0"` | verified [obs] |
| 40 | OpenAerialMap | 4 items in 120.5–122.2 E × 30.5–31.9 N: one 5 cm UAV 150×180 m patch at 121.211 E 31.283 N (13 km NW), three 1 km/px regional mosaics; nothing over ZSSS | https://api.openaerialmap.org/meta?bbox=120.5,30.5,122.2,31.9&limit=50 | `"license":"CC-BY 4.0"` | verified [obs] |
| 41 | Capella open data | nearest GEO scene 121.436–121.499 E (about 10 km E): no ZSSS; licence CC BY 4.0 | https://capella-open-data.s3.amazonaws.com/stac/catalog.json ; https://registry.opendata.aws/capella_opendata/ | "License CC BY 4.0" | verified [obs] |
| 42 | CBERS-4A (INPE) | 0 WPM / MUX L2 items over Shanghai; collections CC BY 4.0 | https://data.inpe.br/bdc/stac/v1/search | `"matched": 0` | verified [obs] |
| 43 | JAXA AVNIR-2 ORI | about 10 m, 2006–2011, free | https://www.eorc.jaxa.jp/ALOS/en/dataset/ori_e.htm | "approx.10-meter mesh in horizontal resolution" | verified |
| 44 | Landsat / USGS EROS | public domain; credit "… courtesy of the U.S. Geological Survey" | https://www.usgs.gov/centers/eros/data-citation | "may be used, transferred, or reproduced without copyright restriction" | verified |
| 45 | OSM aerodrome relation | rel 21913346, version 1, created 2026-11-06T12:00:40Z; area 6.69 km²; `iata=SHA icao=ZSSS ele=3` | https://api.openstreetmap.org/api/0.6/relation/21913346/full | — | verified [obs] (OSM = secondary for the airport itself) |
| 46 | OSM runways | 18L/36R way 16714125: 3388.5 m, az 177.34°, width tag 57.6; 18R/36L way 1477848219: 3282.1 m, az 357.31°, width tag 60; midpoints 369 m apart | same map extract | — | secondary |
| 47 | OurAirports ARP vs OSM | ARP 31.198104 N 121.33426 E lies 14 m from the mean of the two OSM runway midpoints and 52 m from the Nominatim aerodrome centroid | computed (not an AIP check) | — | secondary (no contradiction found) |
| 48 | Hongqiao railway station | OSM way 70364443 "上海虹桥站"; centroid 121.3164 E 31.1961 N; 1.72 km W of ARP | https://api.openstreetmap.org/api/0.6/map?bbox=121.300,31.168,121.362,31.226 | `name:en=Shanghai Hongqiao Station` | secondary (OSM) |
| 49 | Suzhou Creek | OSM way 49206417 `吴淞江` / `Suzhou Creek`; nearest vertex about 2.6 km N of the 18L/36R north end | https://api.openstreetmap.org/api/0.6/map?bbox=121.335,31.226,121.350,31.245 | `name:en=Suzhou Creek` | secondary (OSM) |

---

## 2. Copernicus DEM (GLO-30, with GLO-90 for comparison)

### 2.1 What was downloaded [obs]

Everything below is in `refs/cache/dem/glo30_N31_E121/`. The bucket objects are dated 2022-05-09.
- The DEM COG.
- The auxiliary masks: EDM (editing), FLM (filling), HEM (height error), WBM (water body).
- The ISO XML.
- `ACM.kml` (accuracy) and `SRC.kml` (source scenes).
- The shipped `eula_F.pdf` and the bucket `readme.html`.

GLO-90 for the same cell (DEM, XML, EULA) is in `glo90_N31_E121/`.

**Grid.** The COG is 3600 × 3600 px, EPSG:4326, `AREA_OR_POINT=Point`.
- Transform origin: 120.999861 E, 32.000139 N, at 1/3600°.
- At 31.2° N one pixel is about 23.8 m E–W × 30.8 m N–S.
- The bucket removed the original 3601st row and column. Use the GeoTIFF transform as given and do not re-derive it from the tile name.

### 2.2 Elevations on the airfield [obs]

Script: `tools/terrain/dem_stats.py`. Output: `dem/derived_zsss/dem_stats_zsss.json`.

Masks used: the OSM aerodrome multipolygon (relation 21913346, 6.69 km²) and the OSM runway centrelines, sampled every 30 m.

| Sample | GLO-30 (m, EGM2008) | GLO-90 (m) |
|---|---|---|
| ARP probe (31.198104 N, 121.33426 E) | 1.51 | 1.58 |
| Aerodrome polygon median (p05–p95) | 1.50 (0.96–4.48), n=8210 | 1.51 (1.00–3.92), n=908 |
| Runway 18L/36R centreline | median 1.0, mean 1.28, min 1.0, max 2.0 | median 1.38 |
| Runway 18R/36L centreline | median 1.5, mean 1.43, min 1.0, max 2.0 | median 1.51 |
| 18L/36R profile N→S, every 10 % | 1.0 1.0 1.0 1.0 1.0 1.0 1.5 1.5 2.0 1.77 1.5 | — |
| 18R/36L profile S→N, every 10 % | 1.0 1.5 2.0 2.0 2.0 1.5 1.0 1.0 1.5 1.0 1.5 | — |
| Unedited pixels inside aerodrome (EDM=1, n=3253) | median 1.74, p25 1.37, p75 2.28, p95 5.86 | — |
| 20 km box (ARP ±10 km) | median 4.70, p05 1.44, p95 10.27, max 41.94 | — |

**Editing masks inside the aerodrome** (counts in pixels):
- **EDM:**
  - 5 "Airport editing": 4419 (53.8 %)
  - 1 "Not edited": 3253
  - 2 "Infill of external elevation data": 301
  - 9 "Lake pixels": 139
  - 6 "Raised negative elevation pixels": 50
  - 4 "Smoothed": 30
  - 11 "Shoreline": 9
  - 3 "Interpolated": 8
  - 10 "River": 1
- **FLM:**
  - 1 "Edited": 4656
  - 2 "Not edited / not filled": 3253
  - 5 "SRTM30": 264
  - 3 "ASTER": 37
- **Code meanings** come from Product Handbook i5.0, Tables 6–8.
- In the whole crop window, EDM code 5 occupies 4420 px, and 4419 of them lie inside the aerodrome. Their extent is 121.3238–121.3468 E, 31.1776–31.2193 N.
- **[obs]** In the airport-edited region the values are mostly 1.5 m (2155 px), 1.0 m (621 px) and 2.0 m (254 px). 66.8 % of them are exact multiples of 0.5 m.
- **[inf]** These are manually set planes from WorldDEM airport editing. They are not interferometric measurements, so runway longitudinal slopes and threshold elevations cannot be taken from the DEM.
- HEM is −32767 on edited pixels, as the handbook states. On unedited aerodrome pixels HEM is median 0.83 m, p95 1.5 m.

### 2.3 DEM against the "~3 m" field elevation

- **[obs]** The DEM gives about **1.5 m** on EGM2008. OSM's `ele=3` comes with `source=wikipedia`. I did not read the AIP elevation in this key, so the AIP value is **unverified** here.
- **[obs]** Shanghai's official local height datum is **Wusong**: "H 吴淞=H1985+1.680(m)" (沪规划资源调〔2022〕434号, 2022-11-16).
- **[inf]** If the 3 m (≈10 ft) figure is a Wusong height, it equals about 1.3 m in the 1985 national datum. That agrees with the DEM's 1.5 m (EGM2008) to within the unknown EGM2008–1985-datum offset (decimetres) and the DEM's LE90 of 1.9 m.
- **[inf]** If instead it is a 1985-datum height, the DEM is about 1.5 m low. That is still within the tile's LE90, but systematic over the whole field.
- **Recommendation [inf]:**
  - Use the AIP elevation as the authoritative aerodrome height for aircraft and the ground plane.
  - Use the DEM only for the surrounding terrain shape, offset so that it matches the AIP elevation at the runway.
  - In Shanghai the terrain is flat anyway: the 20 km box has p05–p95 of 1.4–10.3 m, and most of that range is roofs and trees in a DSM.
- **[obs]** The EGM2008 geoid undulation at the ARP is N = +11.24 m. Ellipsoidal (WGS-84) height = EGM2008 height + 11.2 m, so the field is at about 12.7 m above the ellipsoid. This matters for ADS-B: GNSS altitude is ellipsoidal (HAE), while barometric altitude is referenced to MSL.

### 2.4 Licence (verbatim), GLO-30 against GLO-90, restrictions, redistribution

**GLO-30.** The file is `INFO/eula_F.pdf`, titled "Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full, Free & Open". It is identical, apart from whitespace, to the CDSE copy `License-COPDEM-30.pdf`; I checked this by hashing both texts with whitespace removed.
- Art. 3: "The rights granted under this Licence are worldwide and without limitation in time."
- Art. 4: "The Licensor grants to the User the following non-exclusive rights of use regarding the Copernicus WorldDEM-30: (a) reproduction; (b) distribution; (c) communication to the General Public; (d) adaptation, modification and combination with other data and information."
- Art. 5: "The use rights granted under this licence are free of charge to the User."
- Art. 6(a): unmodified data must carry "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved."
- Art. 6(b): adapted or modified data must carry "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved".
- Art. 6(c): add "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30".
- Art. 6(d): do not suggest official endorsement.
- Art. 6(e): bind subsequent users to the same obligations.
- Art. 9: no IPR transfer, and Airbus keeps its rights. The WorldDEM trademark may be used only "in the context of these terms and conditions".
- Termination: the Licensor "may terminate it with the immediate result of the User losing all the rights" on breach.

**GLO-90.** The licence is "Licence for COP-DEM-GLO-90-F Global 90m Full, Free & Open". It sits in the CCM licences PDF on CDSE; I quoted it in full from `licences/copdem_cdse/ccm_data_access_v2_cop_dem_licenses.pdf`, pp. after the ESA licence.
- **Differences from GLO-30 [obs]:**
  - Every "WorldDEM-30" reads "WorldDEM™-90".
  - The preamble excludes **both** WorldDEM™-30 and WorldDEM™-10 from scope. The GLO-30 licence excludes only WorldDEM-10.
- Otherwise the rights (Art. 4), obligations (Art. 6) and liability terms are the same.
- The CDSE page states: "The GLO-30 and GLO-90 datasets are available worldwide with a free license."
- CDSE release history: "2023_1 (Dec-2023): GLO-30: Free & Open release of the restricted countries: Armenia, Azerbaijan and Moldova".
- **[inf]** China was never restricted.
- **[obs]** The AWS tile is dated 2022-05; China tiles were not touched by later releases.

**Restricted instances** (GLO-30-R, EEA-10, EEA-10-R) fall under a separate ESA user licence for eligible user categories. We do not use them.

**Packaging inconsistency [obs].**
- The `INFO/eula_F.pdf` inside the AWS **GLO-90** tile N31 E121 is the restricted "ESA - User licence … Copernicus DEM instances COP-DEM-GLO-30-R and COP-DEM-EEA-10-R".
- So the file name and its content disagree. Treat the CDSE GLO-90-F text as authoritative.
- We use GLO-30, which is unaffected.

**Can we redistribute a crop? Yes [obs + inf].** Articles 4(b), 4(c) and 4(d) allow it.
- **[inf]** A crop is "adapted" data, so it carries the 6(b) "produced using …" notice and the 6(c) liability sentence.
- Pass the obligations on (6(e)), for example in `ATTRIBUTION.md` and in the app's credits.
- Our crop `dem/derived_zsss/cop_dem_glo30_zsss_20km.tif` (755×650 px, values unmodified) has both texts embedded as GeoTIFF tags.

---

## 3. ESA WorldCover 10 m 2021 v200

**Download [obs].** `landcover/worldcover_v200_N30E120/ESA_WorldCover_10m_2021_v200_N30E120_Map.tif`: 93.4 MB, 3×3° (120–123 E, 30–33 N), 1/12000° grid, uint8, nodata 0. Also saved: the bucket readme and PUM v2.0.

**Crop [obs].** `landcover/derived_zsss/esa_worldcover_2021_v200_zsss_20km.tif`, made by `tools/terrain/worldcover_crop.py`.
- Bounds: 121.22933–121.43918 E, 31.10789–31.28831 N, a 20 × 20 km box centred on the ARP hypothesis.
- Size: 2518 × 2165 px, values unmodified.
- Attribution and citation are embedded as tags.
- Preview PNG uses the official PUM palette.

| Class | 20 km box | Aerodrome polygon | 1.5 km box at Hongqiao Station |
|---|---|---|---|
| 10 Tree cover | 18.86 % | 0.09 % | 13.74 % |
| 20 Shrubland | 0.00 % | — | — |
| 30 Grassland | 3.84 % | 10.13 % | 3.97 % |
| 40 Cropland | 8.79 % | 19.94 % | 5.33 % |
| 50 Built-up | **64.22 %** | 59.03 % | **75.33 %** |
| 60 Bare / sparse vegetation | 2.67 % | 9.46 % | 1.51 % |
| 80 Permanent water bodies | **1.62 %** | 1.35 % | 0.12 % |
| 90 Herbaceous wetland | 0.00 % | — | — |

**How to read the classes [inf]:**
- The airfield infields between runways and taxiways are mown grass. WorldCover calls most of them "Cropland" (pink) and some "Grassland".
- Parts of the aprons and paved areas come out "Bare".
- So WorldCover is fine for the city and green-space context around the airport.
- For the airfield itself, the OSM aeroway polygons and the Umbra radar scene should drive surface materials.

**Licence (verbatim, PUM v2.0 §5.1).** "The WorldCover product is provided free of charge, without restriction of use. For the full license information see the Creative Commons Attribution 4.0 International License."
- The AWS registry also says "License CC-BY 4.0".
- **Required attribution (§5.2):** "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium".
- **Citation:** Zanaga et al. 2022, *ESA WorldCover 10 m 2021 v200*, doi:10.5281/zenodo.7254221.
- **Redistributable:** yes, under CC BY 4.0, with the changes indicated (cropped).

---

## 4. Open imagery sharper than 10 m over Shanghai and ZSSS

| Source | GSD / type | Covers ZSSS? | Date | Licence (quoted) | Use for SHA3D |
|---|---|---|---|---|---|
| **Umbra SAR Open Data**, task "Shanghai_CHN" | **0.35 m** GEC, X-band VV spotlight, 5×5 km | **yes**: centre 121.3364 E 31.1947 N; footprint covers both runways, T1/T2, the station and canals [obs] | 2024-06-02 | "All data is provided with a Creative Commons License ( CC by 4.0 )" | **Best open geometry reference.** Radar: layover and sidelobes on buildings, no colour. Not a texture. |
| CNES **SPOT World Heritage** (GEODES `SWH_SPOT5_L1`) | SPOT 5 HRG pan 5 m (A/B) → 2.5 m THR; MS 10 m | yes, 845 scenes; cloud-free 2011-12-31, 2012-11-07, 2012-12-24 (THR pairs) [obs] | 2002–2014 | **contradicted:** "Spot 1-5 archives images are subject to Open 2.0 ETALAB Licence." (CNES REGARDS) vs "Non-Exclusive Licence to Use Spot Archive Product for Non-Commercial Purpose Only." (Theia SWH) | Possible historical optical reference. L1A needs orthorectification. Needs a licence decision and a GEODES account [inf]. Pre-dates later terminal work. |
| SpaceNet AOI_4_Shanghai | WorldView-3 0.3 m pan-sharpened | **no**: 121.590–121.748 E (Pudong) [obs] | 2015-06-06 | bucket: "licensed under a Creative Commons Attribution-ShareAlike 4.0" vs product README: "Unauthorized use and/or dissemination is prohibited." | none |
| Satellogic EarthView | 1 m RGBN | **no**: nearest 384 m tile 2.3 km E of the ARP; 893 tiles in a 35 × 35 km UTM window around ZSSS, all at E ≥ 341086 [obs] | Jul–Dec 2022 | item `"license": "CC-BY-4.0"` | Optional context east of the airport. |
| OpenAerialMap | various | **no** (one 5 cm UAV patch 13 km NW) [obs] | — | "CC-BY 4.0" | none |
| Maxar Open Data | 0.3–0.5 m | **no** China event [obs] | — | "CC-BY-NC-4.0" (non-commercial) | none |
| Capella Open Data | SAR 0.5–1 m | **no**: nearest 121.436 E (about 10 km E) [obs] | 2022, 2024 | "CC BY 4.0" (registry) | none |
| INPE CBERS-4A WPM | 2 m pan / 8 m MS | **no**: 0 items [obs] | — | "Creative-Commons-Attribution-4.0-International" | none |
| JAXA ALOS AVNIR-2 ORI | about 10 m | not checked (no gain over 10 m) | 2006–2011 | "free of charge and open to the public" (JAXA Terms for Use) | none |
| Landsat 8/9 | 15 m pan, 30 m MS | yes | ongoing | USGS: "may be used, transferred, or reproduced without copyright restriction" | coarser than S2 |
| Sentinel-2 L2A | 10 m | yes (51RUQ) | ongoing | Copernicus legal notice (§6) | baseline optical, cropped |
| NAIP / USGS HRO | 0.6 m / ≤1 m | US only (by programme definition) [unverified, not queried] | — | public domain | n/a |
| Google / Baidu / Amap / Tianditu | sub-metre | yes | — | proprietary; Baidu/Amap use offset datums | **reference only**, never geometry or texture (owner rule) |

**Umbra details [obs].** The metadata JSON and STAC item are saved in `imagery/umbra_opendata/`.
- The 4×-decimated GEC overview (5714 × 5714 px, about 1.4 m) was read by HTTP range from the 461 MB COG with `tools/terrain/umbra_overview.py`, and saved as `umbra_gec_ovr4.tif` with the original rotated geotransform.
- **Orientation:** image rows run roughly east and columns roughly north. The columns are rotated about 5.5° east of north. The array-order PNG is *not* north-up.
- **Acquisition geometry:** incidence 38.1°, `angleAzimuthDegrees` 275.5, descending, left-looking.
- The footprint vertices carry an ellipsoid height of **17.76 m HAE**.
- The ground is at about 12.7 m HAE (§2.3), so the scene's projection surface is about 5 m above the ground **[inf]**.
- **[inf]** For points below the projection surface the range offset is about Δh / tan θ ≈ 5 / tan 38.1° ≈ 6 m, away from the sensor (eastward).
- **[obs]** The measured runway dark-band centres are 3–4 m east of OSM. That matches the sign and order of magnitude, given OSM's own metre-level uncertainty.
- Full-resolution GEC (0.35 m) and SICD (12 GB) are available if needed.
- A second Umbra scene of the Shanghai_CHN task, 2025-04-18, is over Pudong/Waigaoqiao (121.65–121.82 E) and does not cover ZSSS.

**SPOT SWH [obs]** (`imagery/cnes_swh_spot5/search_p*.json`).
- Scene counts per year: 2002: 31, 2003: 178, 2004: 173, 2005: 197, 2006: 50, 2007: 29, 2008: 31, 2009: 13, 2010: 10, 2011: 58, 2012: 32, 2013: 20, 2014: 1.
- Low-cloud scenes after the March 2010 runway opening: 2011-12-31 (A+B, DT), 2012-10-02 (7 %), 2012-11-07 (MX), 2012-12-24, 2013-07-08 (4 %), 2013-08-29 (J, 10 m MS).
- The STAC `license` field reads "Apache-2.0" on every GEODES collection. **[inf]** That is a metadata placeholder, not the imagery licence.

---

## 5. Water bodies, canals and the Hongqiao transport hub

Sources: OSM API 0.6 extracts (ODbL); script `tools/terrain/osm_extract.py`; output `osm/derived_zsss/zsss_osm_context.geojson`.
- The extract holds 149 waterway ways, 18 water-area polygons (closed ways, 1.03 km²), 4 stations, 3 terminals and 2 runways.
- WorldCover class 80 adds 1.62 % water in the 20 km box.

**Waterways near the airfield [obs]:**

| Name | OSM type | Length of touching ways | Closest to the aerodrome boundary |
|---|---|---|---|
| 北横泾 | river | 13.7 km | ~19 m |
| 新泾港 (Xinjing Gang) | canal | 11.4 km | ~1.2 km |
| unnamed ditches | ditch | 11.2 km | ~25 m |
| unnamed canals | canal | 7.5 km | ~53 m |
| 外环西河 | river | 4.7 km | ~0.3 km |
| 张正浦 | canal | 3.3 km | ~53 m |
| 机场河 ("Airport River") | river | 2.5 km | **~4 m** (perimeter) |
| 午潮港 | canal | 1.2 km | ~78 m |
| 许浦港 | river | 0.8 km | ~43 m |
| 蟠龙塘, 小涞港, 徐泾江, 华新港 | rivers | 4.5–8.8 km | 0.9–2.6 km |

- **[obs]** In both Sentinel-2 and WorldCover, a continuous blue canal ring runs along the north and east perimeter and SW of the field. There is also a pond south of the 36R/36L ends.
- **[obs]** Suzhou Creek (吴淞江, OSM way 49206417) is about 2.6 km north of the 18L/36R north end and about 4.0 km from the ARP.

**Hongqiao hub [obs, OSM]:**
- Shanghai Hongqiao Station (way 70364443, `building=train_station`): centroid 121.3164 E 31.1961 N. That is **1.72 km WSW** of the ARP (bearing 262° from the ARP) and 1.55 km west of the 18R/36L midpoint.
- Hongqiao Long-Distance Bus Terminal (way 392964430): 121.3134 E 31.1960 N.
- "Hongqiao Airport Terminal 2 Station (Suburban Railway)" (way 449054625): 121.3195 E 31.1962 N.
- Terminal 1 (`aeroway=terminal`, way 93184730): 121.3424 E 31.1962 N, on the east side.
- In the S2 crop the rail-station throat and track fan lie between T2 and the National Exhibition and Convention Center (国家会展中心, Nominatim way 1437146321, about 121.297 E 31.192 N) **[obs]**.
- WorldCover in a 1.5 km box at the station: 75 % built-up, 14 % trees, 0.1 % water.

---

## 6. Sentinel-2 licence

The Copernicus Sentinel data legal notice is saved as `licences/sentinel_legal_notice/Sentinel_Data_Legal_Notice.pdf`. Source: https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice. The earth-search collection `sentinel-2-c1-l2a` links to it as its `license`, labelled "proprietary".

> "The access and use of Copernicus Sentinel Data and Service Information is regulated under EU law. In particular, the law provides that users shall have a free, full and open access to Copernicus Sentinel Data and Service Information without any express or implied warranty, including as regards quality and suitability for any purpose."
>
> "EU law grants free access to Copernicus Sentinel Data and Service Information for the purpose of the following use in so far as it is lawful: (a) reproduction; (b) distribution; (c) communication to the public; (d) adaptation, modification and combination with other data and information; (e) any combination of points (a) to (d)."
>
> "Where the user communicates to the public or distributes Copernicus Sentinel Data and Service Information, he/she shall inform the recipients of the source of that Data and Information by using the following notice: (1) 'Copernicus Sentinel data [Year]' for Sentinel data … Where the Copernicus Sentinel Data and Service Information have been adapted or modified, the user shall provide the following notice: (1) 'Contains modified Copernicus Sentinel data [Year]' for Sentinel data"
>
> "By using Sentinel Data or Service Information the user acknowledges that these conditions are applicable to him/her and that the user renounces to any claims for damages against the European Union and the providers of the said Data and Information."

**Saved crop:** `imagery/sentinel2_earthsearch/crop_20261014/`.
- 10 m TCI: 2030 × 2030 px, EPSG:32651. 20 m SCL: 1015 × 1015 px.
- Made by `s2_crop.py`, with the credit "Contains modified Copernicus Sentinel data 2026" embedded.
- SCL shares: vegetation 32.8 %, not-vegetated 64.2 %, cloud classes 8–10 0.22 %.

---

## 7. Risks and caveats

- **The DEM over the airfield is synthetic.** Airport editing gives 0.5 m stepped planes, and the DSM represents 2011–2012 roofs and trees.
  - Do not use it for runway profiles or building heights.
  - Use the AIP elevation and THR elevations for the airfield, and treat the DEM as near-flat context.
- **The height datum is ambiguous.** The AIP-like "3 m" may be in Wusong height, which is 1.68 m above the 1985 national datum. ADS-B GNSS altitude is ellipsoidal, and N = +11.24 m here.
- **The AWS GLO-90 tile ships a mismatched EULA.** Cite the CDSE GLO-90-F text if GLO-90 is ever shipped.
- **Umbra is radar.** It shows layover on tall buildings (the station roof and terminals), bright sidelobe streaks, a projection-height offset of about 3–6 m, and no visible markings colour.
  - Good for outlines; not usable as a texture.
  - CC BY 4.0 requires attribution.
- **SPOT SWH's licence is contradicted, and the imagery is 2011–2013.** Changes since then (terminal works) make it stale.
- **WorldCover misclassifies the airfield grass** as cropland, and it is 2021 data.
- **The OSM aerodrome relation 21913346 is new** (version 1, 2026-11-06). The OSM runway geometry and `ele=3` are secondary. Runway lengths from OSM (3388.5 / 3282.1 m) must be checked against the AIP.
- **The downloads are not gitignored yet.** `sha3d/refs/cache/` is about 290 MB, and there is no `.gitignore` for `sha3d/` (the repo root only ignores `pc12/refs/cache/`). Add one before any commit.
- **Fresh dependency versions.** I installed `rasterio 1.5.2`, `tifffile 2026.11.12` and `imagecodecs 2026.11.11` with pip. The last two were published 1–2 days before use.

---

## 8. Files

**Scripts** (`sha3d/tools/terrain/`):
- `dem_stats.py`
- `worldcover_crop.py`
- `osm_extract.py`
- `umbra_overview.py`
- `s2_crop.py`
- `gec_runway_check.py`
- `write_sources.py`

**Data** (`sha3d/refs/cache/`), each with a `SOURCES.json`:
- `dem/`: `glo30_N31_E121/`, `glo90_N31_E121/`, `copdem_product_handbook/`, `sh_height_datum/`, `derived_zsss/` (crop + stats)
- `landcover/`: `worldcover_v200_N30E120/`, `worldcover_v200_docs/`, `derived_zsss/` (crop, preview, shares)
- `imagery/`: `umbra_opendata/`, `sentinel2_earthsearch/`, `cnes_swh_spot5/`, `spacenet_aoi4_shanghai/`, `satellogic_earthview/`, `oam/`, `maxar_opendata/`, `inpe_cbers4a/`
- `licences/`: `sentinel_legal_notice/`, `copdem_cdse/`, `aws_registry/`
- `osm/api_map_zsss/`, `osm/api_map_north/`, `osm/derived_zsss/`: ODbL, each with its own `SOURCES.json`
