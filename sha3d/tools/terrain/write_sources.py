"""Write SOURCES.json files for the terrain / land-cover / imagery Phase-0 downloads (sha3d/refs/cache/...).

Usage: python3 -I write_sources.py <sha3d/refs/cache>
Every entry: url, retrieved (2026-11-13), licence (quoted), redistributable, attribution, sha256 per file.
"""
import sys, os, json, hashlib

ROOT = sys.argv[1]
DAY = "2026-11-13"
COPDEM_NOTICE = ("produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
                 "provided under COPERNICUS by the European Union and ESA; all rights reserved")
COPDEM_LIAB = "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30"
WC_ATTR = "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def files(d):
    out = {}
    for dp, _, fs in os.walk(d):
        for f in sorted(fs):
            if f == "SOURCES.json":
                continue
            p = os.path.join(dp, f)
            out[os.path.relpath(p, d)] = dict(bytes=os.path.getsize(p), sha256=sha(p))
    return out


def write(d, entries):
    with open(os.path.join(d, "SOURCES.json"), "w") as f:
        json.dump(entries, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.join(d, "SOURCES.json"))


def main():
    # ---------------- dem ----------------
    d = os.path.join(ROOT, "dem")
    write(d, {
        "glo30_N31_E121": dict(
            what="Copernicus DEM GLO-30 (COP-DEM_GLO-30-DGED, 1 arc-second DSM, EGM2008 heights) tile N31 E121 + aux masks (EDM/FLM/HEM/WBM), ISO XML, ACM/SRC KML, shipped EULA, bucket readme",
            url="https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N31_00_E121_00_DEM/ (readme: https://copernicus-dem-30m.s3.amazonaws.com/readme.html)",
            s3_last_modified="2022-05-09T14:15:21Z", retrieved=DAY,
            licence="Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full, Free & Open (INFO/eula_F.pdf). Art. 4: 'The Licensor grants to the User the following non-exclusive rights of use regarding the Copernicus WorldDEM-30: (a) reproduction; (b) distribution; (c) communication to the General Public; (d) adaptation, modification and combination with other data and information.'",
            redistributable="yes, with the Art. 6 notices (source notice or 'produced using' notice for modified data, the liability sentence, no implied endorsement, and the same obligations passed on to subsequent users)",
            attribution=COPDEM_NOTICE, liability_sentence=COPDEM_LIAB, files=files(os.path.join(d, "glo30_N31_E121"))),
        "glo90_N31_E121": dict(
            what="Copernicus DEM GLO-90 (3 arc-second) tile N31 E121 for comparison, ISO XML, shipped EULA",
            url="https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_N31_00_E121_00_DEM/", retrieved=DAY,
            licence="Licence for COP-DEM-GLO-90-F Global 90m Full, Free & Open (text quoted from https://dataspace.copernicus.eu/sites/default/files/media/files/2025-06/copernicus_contributing_mission_data_access_v2_cop_dem_licenses.pdf). NOTE: the INFO/eula_F.pdf shipped in this AWS GLO-90 tile is NOT that licence; it is the restricted 'ESA - User licence ... COP-DEM-GLO-30-R and COP-DEM-EEA-10-R' (packaging inconsistency observed 2026-11-13).",
            redistributable="yes under GLO-90-F (same Art. 4/6 terms as GLO-30-F); not needed for the app (GLO-30 is better)",
            attribution="produced using Copernicus WorldDEM-90 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved",
            files=files(os.path.join(d, "glo90_N31_E121"))),
        "copdem_product_handbook": dict(
            what="Copernicus DEM Product Handbook GEO1988-CopernicusDEM-SPE-002 issue 5.0 (29.11.2022): EDM/FLM/WBM/HEM code tables, EGM2008, acquisition 2011-2015",
            url="https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf", retrieved=DAY,
            licence="'Copyright reserved. Refer to protection notice ISO 16016.' / 'Public Document'", redistributable="no (reference only; link to it)",
            files=files(os.path.join(d, "copdem_product_handbook"))),
        "sh_height_datum": dict(
            what="Shanghai Municipal Bureau of Planning and Natural Resources notice 沪规划资源调〔2022〕434号 (2022-11-16): 'H吴淞=H1985+1.680(m)'",
            url="https://ghzyj.sh.gov.cn/cmsres/e6/e6d80f66205b45c8adb7a61dbca37905/636d66c646db3f56caa61dc4f1c87301.pdf", retrieved=DAY,
            licence="government notice, marked '公开属性：主动公开信息' (proactively disclosed); no licence grant", redistributable="no (reference only; quote + link)",
            files=files(os.path.join(d, "sh_height_datum"))),
        "derived_zsss": dict(
            what="20 km crop of GLO-30 around ZSSS (values unmodified, EPSG:4326, EGM2008 m) + statistics JSON; made by sha3d/tools/terrain/dem_stats.py",
            derived_from="glo30_N31_E121 + glo90_N31_E121 + ../osm/derived_zsss/zsss_osm_context.geojson", made=DAY,
            licence="GLO-30-F (crop = adapted data) -> must carry the 'produced using' notice and the liability sentence (embedded as GeoTIFF tags)",
            redistributable="yes, with notices", attribution=COPDEM_NOTICE, liability_sentence=COPDEM_LIAB,
            files=files(os.path.join(d, "derived_zsss"))),
    })
    # ---------------- landcover ----------------
    d = os.path.join(ROOT, "landcover")
    write(d, {
        "worldcover_v200_N30E120": dict(
            what="ESA WorldCover 10 m 2021 v200 Map tile N30E120 (3x3 deg, EPSG:4326) + bucket readme",
            url="https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N30E120_Map.tif",
            s3_last_modified="2022-10-26T12:44:33Z", retrieved=DAY,
            licence="CC BY 4.0. PUM v2.0 s5.1: 'The WorldCover product is provided free of charge, without restriction of use. For the full license information see the Creative Commons Attribution 4.0 International License'",
            redistributable="yes (CC BY 4.0) with attribution + citation", attribution=WC_ATTR,
            citation="Zanaga, D., Van De Kerchove, R., Daems, D., De Keersmaecker, W., Brockmann, C., Kirches, G., Wevers, J., Cartus, O., Santoro, M., Fritz, S., Lesiv, M., Herold, M., Tsendbazar, N.E., Xu, P., Ramoino, F., Arino, O., 2022. ESA WorldCover 10 m 2021 v200. doi:10.5281/zenodo.7254221",
            files=files(os.path.join(d, "worldcover_v200_N30E120"))),
        "worldcover_v200_docs": dict(
            what="WorldCover Product User Manual v2.0", url="https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/docs/WorldCover_PUM_V2.0.pdf",
            retrieved=DAY, licence="not stated separately (project document)", redistributable="unclear - link, do not ship",
            files=files(os.path.join(d, "worldcover_v200_docs"))),
        "derived_zsss": dict(
            what="20 km crop around ZSSS (values unmodified) + class-colour preview PNG + class shares JSON; sha3d/tools/terrain/worldcover_crop.py",
            derived_from="worldcover_v200_N30E120 + ../osm/derived_zsss/zsss_osm_context.geojson", made=DAY,
            licence="CC BY 4.0 (adapted: cropped)", redistributable="yes with attribution", attribution=WC_ATTR,
            files=files(os.path.join(d, "derived_zsss"))),
    })
    # ---------------- imagery ----------------
    d = os.path.join(ROOT, "imagery")
    write(d, {
        "umbra_opendata": dict(
            what="Umbra SAR open data over ZSSS: task 'ad hoc/Shanghai_CHN' collect 2024-06-02T01:46:48Z UMBRA-05 spotlight, X-band VV, GEC 0.35 m (5x5 km, centre 121.3364E 31.1947N); 4x-decimated GEC overview (1.4 m, rotated geotransform, EPSG:4326) made by tools/terrain/umbra_overview.py; also metadata of a 2025-04-18 collect (Pudong/Waigaoqiao, does not cover ZSSS)",
            url="https://umbra-open-data-catalog.s3.amazonaws.com/sar-data/tasks/ad%20hoc/Shanghai_CHN/96b8bdc7-96bf-415e-b43b-20adc327995f/2024-06-02-01-46-47_UMBRA-05/",
            retrieved=DAY,
            licence="AWS Registry entry (managed by Umbra): 'All data is provided with a Creative Commons License ( CC by 4.0 ), which gives you the right to do just about anything you want with it.' https://registry.opendata.aws/umbra-open-data/",
            redistributable="yes (CC BY 4.0) with attribution", attribution="Umbra Lab Inc, Umbra SAR Open Data (CC BY 4.0)",
            files=files(os.path.join(d, "umbra_opendata"))),
        "sentinel2_earthsearch": dict(
            what="Sentinel-2 L2A (Collection 1) tile 51RUQ: STAC collection + low-cloud search 2025-10..2026-11 + 20 km crop of the 10 m TCI 'visual' COG and 20 m SCL for S2B_T51RUQ_20261014T024532_L2A (s2_crop.py)",
            url="https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a/items/S2B_T51RUQ_20261014T024532_L2A", retrieved=DAY,
            licence="Legal notice on the use of Copernicus Sentinel Data and Service Information (https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice; copy in ../licences/sentinel_legal_notice/): free access for '(a) reproduction; (b) distribution; (c) communication to the public; (d) adaptation, modification and combination with other data and information'",
            redistributable="yes with notice", attribution="Contains modified Copernicus Sentinel data 2026",
            files=files(os.path.join(d, "sentinel2_earthsearch"))),
        "spacenet_aoi4_shanghai": dict(
            what="SpaceNet AOI_4_Shanghai WorldView-3 2015-06-06 metadata (IMD/TIL/XML/README/browse) - footprint 121.590-121.748E, 30.828-31.427N: does NOT cover ZSSS",
            url="https://spacenet-dataset.s3.amazonaws.com/AOIs/AOI_4_Shanghai/PS-MS/", retrieved=DAY,
            licence="bucket LICENSE.md: 'The \"SpaceNet Dataset\" is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License.' (the DigitalGlobe README inside says 'Unauthorized use and/or dissemination is prohibited.' - conflicting notices)",
            redistributable="n/a for ZSSS (no coverage)", files=files(os.path.join(d, "spacenet_aoi4_shanghai"))),
        "oam": dict(what="OpenAerialMap catalogue query bbox 120.5,30.5,122.2,31.9", url="https://api.openaerialmap.org/meta?bbox=120.5,30.5,122.2,31.9&limit=50",
                    retrieved=DAY, licence="catalogue response; imagery items CC-BY 4.0", redistributable="n/a (no ZSSS imagery found)", files=files(os.path.join(d, "oam"))),
        "maxar_opendata": dict(what="Maxar Open Data events catalogue (no China event)", url="https://maxar-opendata.s3.amazonaws.com/events/catalog.json",
                               retrieved=DAY, licence="catalog 'license': 'CC-BY-NC-4.0'", redistributable="n/a (no ZSSS coverage; NC licence)", files=files(os.path.join(d, "maxar_opendata"))),
        "cnes_swh_spot5": dict(what="CNES GEODES STAC search, collection SWH_SPOT5_L1, bbox 121.32,31.18,121.35,31.21 (845 SPOT 5 scenes 2002-2014)",
                               url="https://geodes-portal.cnes.fr/api/stac/search", retrieved=DAY,
                               licence="CONTRADICTED: regards.cnes.fr SWH page 'Spot 1-5 archives images are subject to Open 2.0 ETALAB Licence.' vs Theia SWH page 'Non-Exclusive Licence to Use Spot Archive Product for Non-Commercial Purpose Only.'",
                               redistributable="unknown until the owner/legal check resolves which licence applies", files=files(os.path.join(d, "cnes_swh_spot5"))),
        "inpe_cbers4a": dict(what="INPE BDC STAC: CBERS-4A WPM/MUX L2 searches over Shanghai (0 matches) + collection doc", url="https://data.inpe.br/bdc/stac/v1/search",
                             retrieved=DAY, licence="collection 'license': 'Creative-Commons-Attribution-4.0-International'", redistributable="n/a (no coverage)", files=files(os.path.join(d, "inpe_cbers4a"))),
        "satellogic_earthview": dict(what="Satellogic EarthView (1 m, Jul-Dec 2022) zone 51N region list near ZSSS + one metadata JSON + index.html; nearest region 2.3 km E of the ARP, none over the airfield",
                                     url="https://satellogic-earthview.s3.us-west-2.amazonaws.com/index.html", retrieved=DAY,
                                     licence="item metadata 'license': 'CC-BY-4.0'", redistributable="n/a for the airfield (no coverage)", files=files(os.path.join(d, "satellogic_earthview"))),
    })
    # ---------------- licences ----------------
    d = os.path.join(ROOT, "licences")
    write(d, {
        "sentinel_legal_notice": dict(url="https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice", retrieved=DAY,
                                      what="European Commission, 'Legal notice on the use of Copernicus Sentinel Data and Service Information' (2 pp.)",
                                      licence="public legal notice", redistributable="yes (public notice); link preferred", files=files(os.path.join(d, "sentinel_legal_notice"))),
        "copdem_cdse": dict(url="https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM ; https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf ; https://dataspace.copernicus.eu/sites/default/files/media/files/2025-06/copernicus_contributing_mission_data_access_v2_cop_dem_licenses.pdf",
                            retrieved=DAY, what="CDSE COP-DEM page, GLO-30-F licence PDF (identical text to the AWS eula_F.pdf, whitespace aside), CCM data access v2 licences (contains GLO-90-F and GLO-30-F and the -R ESA licence)",
                            licence="licence documents", redistributable="link, do not ship", files=files(os.path.join(d, "copdem_cdse"))),
        "aws_registry": dict(url="https://registry.opendata.aws/<name>/", retrieved=DAY, what="AWS Open Data registry pages (licence fields) for umbra-open-data, copernicus-dem, esa-worldcover-vito, sentinel-2-l2a-cogs, spacenet, maxar-open-data",
                             licence="web pages", redistributable="no (reference)", files=files(os.path.join(d, "aws_registry"))),
    })
    # ---------------- osm (my subdirectories only; osm/ is shared with another agent) ----------------
    for sub, url, what in [
        ("api_map_zsss", "https://api.openstreetmap.org/api/0.6/relation/21913346/full ; https://api.openstreetmap.org/api/0.6/map?bbox=121.300,31.168,121.362,31.226", "OSM API 0.6 aerodrome relation + map extract around ZSSS"),
        ("api_map_north", "https://api.openstreetmap.org/api/0.6/map?bbox=121.335,31.226,121.350,31.245", "OSM API 0.6 map extract north of ZSSS (Suzhou Creek)"),
        ("derived_zsss", "derived by sha3d/tools/terrain/osm_extract.py from ../api_map_zsss", "GeoJSON: aerodrome polygon, runways, stations, terminals, waterways, water areas")]:
        dd = os.path.join(ROOT, "osm", sub)
        write(dd, {sub: dict(url=url, what=what, retrieved=DAY,
                             licence="ODbL 1.0 - API response header: copyright='OpenStreetMap and contributors' license='http://opendatacommons.org/licenses/odbl/1-0/'",
                             redistributable="yes under ODbL (attribution '© OpenStreetMap contributors'; share-alike for derived databases)",
                             attribution="© OpenStreetMap contributors", files=files(dd))})


if __name__ == "__main__":
    main()
