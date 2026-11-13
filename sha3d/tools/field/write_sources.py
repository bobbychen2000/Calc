"""Write SOURCES.json into every refs/cache/field/<source>/ directory (KEY = field, checked 2026-11-13).

usage (from sha3d/):  python3 -I tools/field/write_sources.py
Hashes every file present; directories whose copy was deliberately not kept list the hash of what was fetched.
"""
import hashlib
import json
import os

ROOT = "refs/cache/field"
DATE = "2026-11-13"

CAAC_LIC = ("www.caac.gov.cn footer: \"版权所有：中国民用航空局\" (copyright CAAC); no reuse licence published. "
            "PRC Copyright Law art. 5 excludes official documents of state organs and pure factual information, "
            "but we have not confirmed that it covers these files.")
SIAC_LIC = ("Statutory disclosure by Shanghai International Airport Co., Ltd. (600009.SH) filed on the Shanghai Stock "
            "Exchange; copy fetched from the Eastmoney mirror pdf.dfcfw.com. Neither the document nor the mirror states "
            "a reuse licence.")
SAA_LIC = ("Shanghai Airport Authority site (www.avinex.com, formerly www.shairport.com). Footer: \"上海机场(集团)有限公司 "
           "... 沪ICP备05007027号\". No licence or terms of reuse found on the pages fetched.")
CAACNEWS_LIC = ("caacnews.com.cn footer: \"'中国民航网'各种新闻、信息和各种专题专栏资料, 均为中国民航报社有限公司版权所有，"
                "未经协议授权，禁止下载使用。\" (all content copyright China Civil Aviation News; download and use prohibited "
                "without an agreement).")

META = {
    "caac_bulletin_2025": {
        "what": "CAAC 2025年全国民用运输机场生产统计公报 (national airport production statistics bulletin) + attachment 1 "
                "(airport ranking xlsx) + attachment 2 (hub airports by route xlsx)",
        "urls": {"page.html": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/t20260226_230119.html",
                 "bulletin_2025.pdf": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/P020260226360830234339.pdf",
                 "ranking_2025.xlsx": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/P020260226360830390937.xlsx",
                 "hubs_by_route_2025.xlsx": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/P020260226360830545167.xlsx"},
        "publisher": "Civil Aviation Administration of China (CAAC)", "published": "2026-02-26", "status": "verified",
        "licence": CAAC_LIC, "redistributable": False,
        "use": "SHA annual movements, passengers and cargo for 2025, and the 2025 split by route class"},
    "caac_bulletin_2024": {
        "what": "CAAC 2024年全国民用运输机场生产统计公报 + attachment 1 (airport ranking xlsx)",
        "urls": {"page.html": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202503/t20250314_226932.html",
                 "bulletin_2024.pdf": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202503/P020250314353469776556.pdf",
                 "ranking_2024.xlsx": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202503/P020250314353470214193.xlsx"},
        "publisher": "CAAC", "published": "2025-03-14", "status": "verified", "licence": CAAC_LIC,
        "redistributable": False, "use": "SHA 2024 annual figures"},
    "caac_bulletin_2023": {
        "what": "CAAC 2023年全国民用运输机场生产统计公报 + attachment 1 (airport ranking xlsx)",
        "urls": {"page.html": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202403/t20240320_223261.html",
                 "bulletin_2023.pdf": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202403/P020240320504230898437.pdf",
                 "ranking_2023.xlsx": "https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202403/P020241227527614591507.xlsx"},
        "publisher": "CAAC", "published": "2024-03-20 (xlsx file id dated 2024-12-27)", "status": "verified",
        "licence": CAAC_LIC, "redistributable": False, "use": "SHA 2023 annual figures"},
    "caac_news_t2_opening_2010": {
        "what": "CAAC news item 上海虹桥机场2号航站楼今日启用 (T2 opening, second runway, 365 m spacing, 43 bridges, T1/T2 split)",
        "urls": {"page.html": "https://www.caac.gov.cn/PHONE/XWZX/MHYW/201003/t20100316_12580.html"},
        "publisher": "CAAC", "published": "2010-03-16", "status": "verified", "licence": CAAC_LIC,
        "redistributable": False, "use": "T2/runway history"},
    "caac_slot_capacity_2016": {
        "what": "CAAC notice 关于公布航班时刻协调机场容量标准的通知 (局发明电〔2011〕3401号): hourly capacity of 21 coordinated airports",
        "urls": {"page.html": "https://www.caac.gov.cn/XXGK/XXGK/ZFGW/201602/t20160224_29138.html"},
        "publisher": "CAAC 空管行业管理办公室", "published": "dated 2011-11-01, page posted 2016-02-24", "status": "verified",
        "licence": CAAC_LIC, "redistributable": False,
        "use": "historic hourly capacity standard (43/h) and coordination window 06:00-02:00"},
    "caacnews_bridge_rate_2023": {
        "what": "China Civil Aviation News / caacnews.com.cn: 深挖保障潜能、加速机位周转……精耕靠桥率提升的“上海攻略” (contact stands, bridge rate)",
        "urls": {"(not kept)": "http://www.caacnews.com.cn/special/2023nzt/7624/2020mhcy1/2020cybzmhj/202308/t20230818_1369755.html"},
        "fetched": {"bytes": 30574, "sha256": "a18b3f60b2c2afe309ab31fcef94071e0c0d93126ceee65b748f919d219799c6"},
        "note": "Copy deleted after reading because the site's terms forbid downloading without an agreement; quotes are in docs/phase0/field.md.",
        "publisher": "中国民航报社 (CAAC's newspaper)", "published": "2023-08-18", "status": "secondary (official-sector press)",
        "licence": CAACNEWS_LIC, "redistributable": False, "use": "54 contact stands, ~34 % of stands, ~535 bridge flights/day, no night schedule"},
    "caacnews_end_around_2021": {
        "what": "caacnews.com.cn: 全国首例：华东空管在虹桥机场实施近距跑道绕滑运行 (end-around taxiways, runway mode, hourly peak 59)",
        "urls": {"(not kept)": "http://www.caacnews.com.cn/1/3/202110/t20211009_1331872.html"},
        "fetched": {"bytes": 74387, "sha256": "68500ceab73baebfc9a3c7bd1507dba5f8d345cdb85d728996b30650694e8375"},
        "note": "Copy deleted after reading because the site's terms forbid downloading without an agreement; quotes are in docs/phase0/field.md.",
        "publisher": "中国民航报社", "published": "2021-10-09", "status": "secondary (official-sector press)",
        "licence": CAACNEWS_LIC, "redistributable": False, "use": "runway use 东落西起, end-around taxiway lengths, peak hour"},
    "siac_annual_2025": {
        "what": "上海国际机场股份有限公司 2025年年度报告 (SIAC annual report 2025)",
        "urls": {"siac_2025_annual_report.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202604291821768752_1.pdf"},
        "publisher": "Shanghai International Airport Co., Ltd. (operator of PVG and, since the 2022-24 restructuring, SHA)",
        "published": "2026-04-30", "status": "verified", "licence": SIAC_LIC, "redistributable": False,
        "use": "2025 SHA traffic by route class incl. GA residual; 2 runways, 2 terminals, 40 M design capacity"},
    "siac_annual_2024": {"what": "SIAC 2024年年度报告", "urls": {"siac_2024_annual_report.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202504281664029312_1.pdf"},
                         "publisher": "SIAC", "published": "2025-04-29", "status": "verified", "licence": SIAC_LIC,
                         "redistributable": False, "use": "2024 SHA traffic by route class"},
    "siac_annual_2023": {"what": "SIAC 2023年年度报告", "urls": {"siac_2023_annual_report.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202403291629039661_1.pdf"},
                         "publisher": "SIAC", "published": "2024-03-30", "status": "verified", "licence": SIAC_LIC,
                         "redistributable": False, "use": "2023 SHA traffic by route class"},
    "siac_interim_2023": {"what": "SIAC 2023年半年度报告", "urls": {"siac_2023_interim_report.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202308301596821341_1.pdf"},
                          "publisher": "SIAC", "published": "2023-08-31", "status": "verified", "licence": SIAC_LIC,
                          "redistributable": False, "use": "checked for capacity statements (none found)"},
    "siac_esg_2025": {"what": "SIAC 2025年度ESG报告", "urls": {"siac_2025_esg_report.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202604291821768720_1.pdf"},
                      "publisher": "SIAC", "published": "2026-04-30", "status": "verified", "licence": SIAC_LIC,
                      "redistributable": False, "use": "checked for stand/terminal facts (little found)"},
    "siac_monthly_briefs": {
        "what": "SIAC 运输生产情况简报 (monthly traffic briefs) 2025-12 .. 2026-09; Hongqiao block parsed by tools/field/siac_briefs.py",
        "urls": {"brief_2025-12.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202601141817011237_1.pdf",
                 "brief_2026-01.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202602131819920049_1.pdf",
                 "brief_2026-02.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202603131820542416_1.pdf",
                 "brief_2026-03.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202604141821177451_1.pdf",
                 "brief_2026-04.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202605141822312961_1.pdf",
                 "brief_2026-05.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202606141823550607_1.pdf",
                 "brief_2026-06.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202607141826955279_1.pdf",
                 "brief_2026-07.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202608141827984081_1.pdf",
                 "brief_2026-08.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202609141829368745_1.pdf",
                 "brief_2026-09.pdf": "https://pdf.dfcfw.com/pdf/H2_AN202610141830452855_1.pdf"},
        "index": "https://np-anotice-stock.eastmoney.com/api/security/ann?stock_list=600009 (announcement list)",
        "publisher": "SIAC", "published": "2026-01-15 .. 2026-10-15", "status": "verified",
        "note": "Each brief says: 上述运输生产数据源自公司内部统计，仅供投资者参考 (company internal statistics, for investors' reference).",
        "licence": SIAC_LIC, "redistributable": False, "use": "current daily movement rate (ADS-B denominator)"},
    "saa_airline_directory": {
        "what": "Shanghai Airport Authority airline directory with per-terminal lists (PVG T1/T2, SHA T1/T2)",
        "urls": {"airlines_index.html": "https://www.avinex.com/airlines/index.html"},
        "publisher": "上海机场(集团)有限公司 (Shanghai Airport Authority)", "published": "undated live page", "status": "verified",
        "licence": SAA_LIC, "redistributable": False, "use": "which airlines use SHA T1 vs T2"},
    "saa_terminal_flow_maps": {
        "what": "SAA terminal flow diagrams for Hongqiao T1/T2 (gate numbers, remote-stand gates); schematic images",
        "urls": {"sha_t1_arr_1f.jpg": "https://www.avinex.com/uploadfiles/2023/10/20231016170402550.jpg",
                 "sha_t1_dep_2f.jpg": "https://www.avinex.com/uploadfiles/2023/10/20231016170418478.jpg",
                 "sha_t2_arr_1f.jpg": "https://www.avinex.com/uploadfiles/2023/10/20231016170440786.jpg",
                 "sha_t2_arr_2f.jpg": "https://www.avinex.com/uploadfiles/2023/10/20231016170457899.jpg",
                 "sha_t2_dep_m2.jpg": "https://www.avinex.com/uploadfiles/2023/10/20231016170510286.jpg",
                 "sha_t2_dep_3f.jpg": "https://www.avinex.com/uploadfiles/2023/12/20231225083756766.jpg"},
        "linked_from": "https://www.avinex.com/jcznt/index.html",
        "publisher": "SAA", "published": "2023-10-16 / 2023-12-25 (upload paths)", "status": "verified",
        "licence": SAA_LIC + " The images carry the 上海机场 AVINEX logo.", "redistributable": False,
        "use": "reference only for gate numbering; never geometry or texture (schematic, not to scale)"},
    "saa_news_bizav_2010": {"what": "SAA news 上海虹桥国际机场公务机基地3月26日启用", "urls": {"page.html": "https://www.avinex.com/xwg/info_itemid_19492.html"},
                            "publisher": "SAA", "published": "2010-03-26", "status": "verified", "licence": SAA_LIC,
                            "redistributable": False, "use": "business-aviation base facts"},
    "saa_news_t2_opening_2010": {"what": "SAA news 虹桥机场2号航站楼3月16日启用", "urls": {"page.html": "https://www.avinex.com/xwg/info_itemid_19498.html"},
                                 "publisher": "SAA", "published": "2010-03-16", "status": "verified", "licence": SAA_LIC,
                                 "redistributable": False, "use": "T2 opening, runway 2 opening 2010-03-11, 365 m spacing"},
    "saa_news_t1_renovation_2014": {"what": "SAA news on the T1 renovation (19196: 启动 2014-10-30; 19191: 全面开工 2014-12-20)",
                                    "urls": {"page_19196.html": "https://www.avinex.com/xwg/info_itemid_19196.html",
                                             "page_19191.html": "https://www.avinex.com/xwg/info_itemid_19191.html"},
                                    "publisher": "SAA", "published": "2014-10-30 / 2014-12-20", "status": "verified",
                                    "licence": SAA_LIC, "redistributable": False, "use": "T1 history, role, 10 M design capacity"},
    "saa_news_t1_reopen_2018": {"what": "SAA news 虹桥机场1号航站楼正式全面启用", "urls": {"page.html": "https://www.avinex.com/xwg/info_itemid_18946.html"},
                                "publisher": "SAA", "published": "2018-10-15", "status": "verified", "licence": SAA_LIC,
                                "redistributable": False, "use": "T1 full reopening; Spring Airlines at D island"},
    "shgov_press_t2_2010": {
        "what": "Shanghai Municipal Government press conference 2010-03-11: 市政府新闻发布会介绍虹桥机场2号航站楼落成相关情况",
        "urls": {"page.html": "https://www.shanghai.gov.cn/nw9822/20200906/0001-9822_395090.html"},
        "publisher": "上海市人民政府", "published": "2010-03-11 (archived page, path dated 2020-09-06)", "status": "verified",
        "licence": "No licence or copyright notice in the page text.", "redistributable": False,
        "use": "design capacity 40 M pax / 1 Mt / 300k movements; 45 bridges; 8 MARS stands"},
    "shgov_en_sha_record_2025": {"what": "english.shanghai.gov.cn: Hongqiao airport sets new monthly passenger record",
                                 "urls": {"page.html": "https://english.shanghai.gov.cn/en-Latest-WhatsNew/20250815/73f45a7e0984407cb61fd3a66f2773dc.html"},
                                 "publisher": "Shanghai Municipal Government (English portal)", "published": "2025-08-15",
                                 "status": "verified", "licence": "No licence in page text.", "redistributable": False,
                                 "use": "context only (international pax in July 2025)"},
    "shhqcbd_noise_2012": {"what": "Hongqiao CBD management committee site reposting 东方早报 2012-05: 虹桥机场为降噪或限制大型飞机飞行",
                           "urls": {"page.html": "https://www.shhqcbd.gov.cn/yshj/csyx/sndt/3803.html"},
                           "publisher": "上海虹桥国际中央商务区管理委员会 (government) reposting a newspaper article",
                           "published": "2012-05 (article)", "status": "secondary (newspaper on a government site)",
                           "licence": "Footer: \"Copyright 2021 by Shanghai Hongqiao International Central Business District. All rights Reserved\" / \"版权所有：上海虹桥国际中央商务区管理委员会\"",
                           "redistributable": False, "use": "no scheduled flights 00-06; west runway for take-off"},
    "sina_2010_night_slots": {"what": "Sina mobile news 2010-06-26: 减少扰民，虹桥机场拟不再安排夜间航班",
                              "urls": {"page.html": "https://news.sina.cn/sa/2010-06-26/detail-ikmxzfmk0135400.d.html"},
                              "publisher": "Sina (news portal)", "published": "2010-06-26", "status": "secondary",
                              "licence": "Sina: all rights reserved (no reuse licence).", "redistributable": False,
                              "use": "origin of the 00:00-06:00 no-scheduled-flights rule"},
    "sina_saa_w2026_season": {"what": "上观新闻 via Sina 2026-10-24: 2026年冬春航季明起执行 (SAA winter 2026/27 schedule, daily planned flights)",
                              "urls": {"page.html": "http://news.sina.com.cn/minsheng/2026-10-24/doc-iniwhxpu1437622.shtml"},
                              "publisher": "上观新闻 (Jiefang Daily group) relaying Shanghai Airport Authority", "published": "2026-10-24",
                              "status": "secondary", "licence": "Footer: \"Copyright © 1996-2026 SINA Corporation All Rights Reserved 新浪公司 版权所有\"",
                              "redistributable": False, "use": "SHA 802 planned movements/day in winter 2026/27"},
    "zhwiki_sha": {"what": "Chinese Wikipedia 上海虹桥国际机场 wikitext (action=raw)",
                   "urls": {"SHA_zh_wikitext.txt": "https://zh.wikipedia.org/w/index.php?title=%E4%B8%8A%E6%B5%B7%E8%99%B9%E6%A1%A5%E5%9B%BD%E9%99%85%E6%9C%BA%E5%9C%BA&action=raw"},
                   "publisher": "Wikipedia contributors", "published": "live; retrieved 2026-11-13 ~20:20Z (revision API rate-limited, revid not recorded)",
                   "status": "secondary",
                   "licence": "Wikipedia text: 'Text is available under the Creative Commons Attribution-ShareAlike 4.0 License; additional terms may apply'",
                   "redistributable": "yes, CC BY-SA 4.0 with attribution; ShareAlike for adaptations", "use": "history, terminal roles, runway use"},
    "derived_field": {"what": "Our derived tables: saa_airlines_by_terminal.json (tools/field/saa_airlines.py), "
                              "siac_hongqiao_monthly.jsonl (tools/field/siac_briefs.py), traffic_summary.json (tools/field/summarise_traffic.py)",
                      "urls": {}, "publisher": "derived locally", "published": DATE, "status": "derived",
                      "licence": "inherits the sources (SAA, SIAC, CAAC); facts only", "redistributable": "numbers yes as cited facts; files no",
                      "use": "inputs to docs/phase0/field.md"},
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        meta = META.get(d)
        if meta is None:
            raise SystemExit("no metadata for " + d)
        files = {}
        for fn in sorted(os.listdir(p)):
            if fn == "SOURCES.json":
                continue
            fp = os.path.join(p, fn)
            files[fn] = {"bytes": os.path.getsize(fp), "sha256": sha(fp)}
        rec = {"key": "field", "date_checked": DATE, **meta, "files": files}
        with open(os.path.join(p, "SOURCES.json"), "w", encoding="utf-8") as f:
            json.dump({d: rec}, f, ensure_ascii=False, indent=1)
        print(d, len(files))


if __name__ == "__main__":
    main()
