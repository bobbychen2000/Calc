"""Write refs/cache/law/SOURCES.json (KEY = law, checked 2026-11-13).

usage (from sha3d/):  python3 -I tools/law/write_sources.py
Hashes every file present in each refs/cache/law/<source>/ directory. Fetches that failed or were deliberately not
kept are listed under "not_kept" with the reason. Downloads are untrusted data; this script only reads and hashes them.
Sources already cached by phase0 key adsb under refs/cache/china_law/ are referenced, not copied.
"""
import hashlib
import json
import os

ROOT = "refs/cache/law"
DATE = "2026-11-13"

STATE_TEXT = ("Text of a law, regulation or state-organ normative document. PRC Copyright Law (2020) Art. 5(1): "
              "\"本法不适用于：（一）法律、法规，国家机关的决议、决定、命令和其他具有立法、行政、司法性质的文件，及其官方正式译文\" "
              "(read at refs/cache/china_law/law_copyright_mofcom/). The page furniture (HTML, layout) belongs to the host site.")
GOVCN = STATE_TEXT + " Host footer: \"版权所有：中国政府网\"."
NEWS = "Publisher copyright (no reuse licence found); quote only."
WIKI = ("Wikipedia text: CC BY-SA 4.0 (en.wikipedia.org footer: \"Text is available under the Creative Commons "
        "Attribution-ShareAlike 4.0 License\"); redistribution needs attribution and share-alike.")
OSMWIKI = ("OSM wiki footer (read 2026-11-13): \"Content is available under Creative Commons Attribution-ShareAlike 2.0 "
           "license unless otherwise noted.\"")

META = {
    "law_surveying_npc": dict(
        url="http://www.npc.gov.cn/zgrdw/npc/xinwen/2017-04/27/content_2020927.htm",
        what="中华人民共和国测绘法 (Surveying and Mapping Law), 2nd revision adopted 2017-04-27, in force 2017-07-01 (NPC site)",
        publisher="全国人大常委会 / 中国人大网", status="verified", licence=STATE_TEXT,
        redistributable="law text: yes; page HTML: no", use="Arts. 2, 5, 8, 10, 34, 38, 47, 51, 52, 62"),
    "reg_map_mgmt_govcn": dict(
        url="https://www.gov.cn/zhengce/content/2015-12/14/content_10403.htm",
        what="地图管理条例 (Map Management Regulations), State Council Order No. 664, signed 2015-11-26, in force 2016-01-01",
        publisher="国务院 / 中国政府网", status="verified", licence=GOVCN,
        redistributable="text: yes; page HTML: no", use="Arts. 2, 8, 15, 16, 21, 22, 34, 36, 54, 55"),
    "rule_public_map_2023_govcn": dict(
        url="https://www.gov.cn/zhengce/zhengceku/2023-02/17/content_5741977.htm",
        what="自然资源部关于印发《公开地图内容表示规范》的通知 (自然资规〔2023〕2号), notice page with docx attachment link",
        publisher="自然资源部 via 中国政府网 policy library", status="verified", licence=GOVCN,
        redistributable="text: yes; page HTML: no", use="document number and date 2023-02-06"),
    "rule_public_map_2023_docx": dict(
        url="https://www.gov.cn/zhengce/zhengceku/2023-02/17/5741977/files/bf77ffdd8b3e4b73aa3e301d1e77406b.docx",
        what="《公开地图内容表示规范》 attachment (.docx in a non-standard WPS container: no word/document.xml; not parsed)",
        publisher="自然资源部", status="verified (downloaded; text read from the Gazette copy instead)", licence=STATE_TEXT,
        redistributable="text: yes", use="kept as the original attachment"),
    "rule_public_map_2023_gongbao": dict(
        url="https://www.gov.cn/gongbao/content/2023/content_5752310.htm",
        what="《公开地图内容表示规范》 full text, State Council Gazette 2023 No. 11",
        publisher="国务院公报 / 中国政府网", status="verified", licence=GOVCN,
        redistributable="text: yes; page HTML: no", use="items 2, 16-23 (10 m accuracy, prohibited content, 0.5 m imagery)"),
    "rule_foreign_survey_2019_govcn": dict(
        url="https://www.gov.cn/zhengce/2019-08/13/content_5711393.htm",
        what="外国的组织或者个人来华测绘管理暂行办法 (Interim Measures on foreign surveying in China), MLR Order 38 of 2007, amended 2011 and 2019",
        publisher="自然资源部 via 中国政府网", status="verified", licence=GOVCN,
        redistributable="text: yes; page HTML: no", use="Arts. 2, 3, 6, 7, 19"),
    "rule_secret_scope_2020_mfa": dict(
        url="https://www.mfa.gov.cn/wjb_673085/zzjg_673183/bjhysws_674671/bhflfg/ldbjchxgfl/202303/P020230313534680395614.pdf",
        what="测绘地理信息管理工作国家秘密范围的规定 (自然资发〔2020〕95号) with the catalogue of state secrets, MFA copy",
        publisher="自然资源部, 国家保密局 (copy hosted by the Ministry of Foreign Affairs)", status="verified",
        licence=STATE_TEXT, redistributable="text: yes (state document); keep local anyway",
        use="catalogue items 2, 3, 8-10, 22-25 and note 1; Art. 5 says the rule is managed as a work secret ('按照工作秘密管理')"),
    "law_state_secrets2024_govcn": dict(
        url="http://big5.www.gov.cn/gate/big5/www.gov.cn/yaowen/liebiao/202402/content_6934648.htm",
        what="中华人民共和国保守国家秘密法 (State Secrets Law), 2nd revision 2024-02-27, in force 2024-05-01 (gov.cn, traditional-character gateway)",
        publisher="中国政府网", status="verified", licence=GOVCN,
        redistributable="text: yes; page HTML: no", use="Arts. 2, 13, 36, 40"),
    "law_criminal_chinatax": dict(
        url="https://fgk.chinatax.gov.cn/zcfgk/c100009/c5212248/content.html",
        what="中华人民共和国刑法 consolidated text (成文日期 2023-12-29, through Amendment XII), State Taxation Administration law database",
        publisher="国家税务总局政策法规库 (footer: 版权所有：国家税务总局)", status="verified (official government mirror)",
        licence=STATE_TEXT, redistributable="text: yes; page HTML: no", use="Arts. 6, 8, 111, 282, 288"),
    "law_criminal_art8_npc_qa": dict(
        url="http://www.npc.gov.cn/zgrdw/npc/flsyywd/flwd/2002-04/17/content_292709.htm",
        what="NPC legal Q&A: 外国人在中国领域外对我国或者我国公民犯罪的，是否适用我国刑法？ (2002)",
        publisher="中国人大网 法律问答", status="verified (official explanatory note, not binding interpretation)",
        licence="NPC explanatory article; Art. 5 status unclear; quote only", redistributable="quote only",
        use="three conditions for applying Art. 8 to foreigners abroad"),
    "law_trademark2019_cnipa": dict(
        url="https://www.cnipa.gov.cn/art/2019/6/25/art_104_67808.html",
        what="中华人民共和国商标法 (2019 amendment, in force 2019-11-01), CNIPA site; served gzip-compressed (page.html.gz = bytes as received, page.html = decompressed)",
        publisher="国家知识产权局", status="verified", licence=STATE_TEXT,
        redistributable="text: yes; page HTML: no", use="Arts. 48, 57, 59"),
    "law_trademark2026_cnipa": dict(
        url="https://www.cnipa.gov.cn/art/2026/7/3/art_55_207047.html",
        what="CNIPA repost of 知识产权报 interview: 新法护航品牌发展 法治规范商标秩序 (Trademark Law revised 2026-06-26, Presidential Order 77, in force 2027-01-01)",
        publisher="国家知识产权局 / 知识产权报", status="verified (official site; interview, not the law text)",
        licence=NEWS, redistributable="no (quote only)", use="adoption date, effective date, scope of the 2026 revision"),
    "news_trademark2026_xinhua": dict(
        url="https://www.news.cn/politics/20260626/71b53c39cbc74d9e86bfdc638fce4ba8/c.html",
        what="新华网 2026-06-26: 人大常委会丨强化商标管理和保护 商标法完成修订",
        publisher="新华社", status="secondary (state news agency)", licence=NEWS, redistributable="no",
        use="cross-check of the 2026 revision"),
    "analysis_hankun_trademark2026": dict(
        url="https://www.hankunlaw.com/upload/portal/20260721/b21f0150391aa95b6f48074c16179e0c.pdf",
        what="汉坤法律评述 2026-07-14: 2026 新商标法修订解读：四大核心变化 (old Art. 48 vs new Art. 2 comparison table)",
        publisher="Han Kun Law Offices", status="secondary (law-firm analysis)", licence=NEWS + " Law-firm copyright.",
        redistributable="no", use="new Art. 2 definition of trademark use incl. internet use"),
    "news_stdaily_20261017": dict(
        url="https://www.stdaily.com/web/gdxw/2026-10/17/content_597933.html",
        what="科技日报/中国科技网 2026-10-17 repost of MSS WeChat: 国安机关发布案例提醒：开放地图不能“随手一标” (person in China annotated sensitive units on a foreign open-map platform)",
        publisher="科技日报社 (source: 国家安全部微信公众号)", status="secondary (state-media repost of MSS)",
        licence="Footer: \"Copyright © Science and Technology Daily, All Rights Reserved\"", redistributable="no",
        use="OSM-type open-map enforcement case"),
    "news_xinhua_20260113": dict(
        url="https://www.news.cn/politics/20260113/5fe35636f177440eb90777c23e71e0c8/c.html",
        what="新华网 2026-01-13 (from 央视新闻客户端): 警惕以学术交流为掩护开展非法测绘活动 国家安全机关发布提示",
        publisher="新华社 / 央视新闻", status="secondary (state media)", licence=NEWS, redistributable="no",
        use="MSS warning on illegal surveying by foreign entities"),
    "news_secrss_83070": dict(
        url="https://www.secrss.com/articles/83070",
        what="安全内参 2025-09-14 repost of MSS: 地理信息数据安全可能被忽视，但真的很重要 ('problem map' seizure, foreign GIS software)",
        publisher="安全内参 (source: 国家安全部)", status="secondary (repost of MSS)", licence=NEWS, redistributable="no",
        use="problem-map and geodata cases"),
    "news_secrss_71258": dict(
        url="https://www.secrss.com/articles/71258",
        what="安全内参 2024-10-16 repost of MSS: 某境外企业“借壳”国内测绘企业非法窃取测绘地理信息",
        publisher="安全内参 (source: 国家安全部)", status="secondary (repost of MSS)", licence=NEWS, redistributable="no",
        use="foreign company surveying via a licensed domestic firm"),
    "news_secrss_76950": dict(
        url="https://www.secrss.com/articles/76950",
        what="安全内参 2025-03-23 repost of MSS: 防范无线电跨境暗流 (radio amateur's foreign-supplied receiver sent ship positions abroad; pirate station case)",
        publisher="安全内参 (source: 国家安全部)", status="secondary (repost of MSS)", licence=NEWS, redistributable="no",
        use="receive-only equipment feeding abroad penalised; Criminal Law Art. 288 cited"),
    "osmwiki_china": dict(
        url="https://wiki.openstreetmap.org/w/index.php?title=China&action=raw",
        what="OpenStreetMap wiki page 'China' (raw wikitext): Legality and Coordinate system sections",
        publisher="OSM wiki contributors", status="secondary (community wiki)", licence=OSMWIKI,
        redistributable="yes with attribution + share-alike (CC BY-SA 2.0)", use="community view of legality; outdated 2003/2009 rules"),
    "wiki_geo_restrictions_en": dict(
        url="https://en.wikipedia.org/w/index.php?title=Restrictions_on_geographic_data_in_China&action=raw",
        what="English Wikipedia: Restrictions on geographic data in China (raw wikitext)",
        publisher="Wikipedia contributors", status="secondary", licence=WIKI,
        redistributable="yes with attribution + share-alike", use="GB 20263-2006 4.1 quote, GCJ-02 name, enforcement history"),
    "wiki_hongqiao_en": dict(
        url="https://en.wikipedia.org/w/index.php?title=Shanghai_Hongqiao_International_Airport&action=raw",
        what="English Wikipedia: Shanghai Hongqiao International Airport (raw wikitext), History section",
        publisher="Wikipedia contributors", status="secondary", licence=WIKI,
        redistributable="yes with attribution + share-alike", use="military use until 1963, civil reopening April 1964"),
    "wiki_nominative_use_en": dict(
        url="https://en.wikipedia.org/w/index.php?title=Nominative_use&action=raw",
        what="English Wikipedia: Nominative use (US trademark doctrine)", publisher="Wikipedia contributors",
        status="secondary", licence=WIKI, redistributable="yes with attribution + share-alike",
        use="three-part nominative-use test"),
    "scotus_jackdaniels_2023": dict(
        url="https://www.supremecourt.gov/opinions/22pdf/22-148_3e04.pdf",
        what="Jack Daniel's Properties, Inc. v. VIP Products LLC, 599 U.S. ___ (2023), decided 2023-06-08, slip opinion",
        publisher="Supreme Court of the United States", status="verified",
        licence="US federal government work (17 U.S.C. 105: no copyright in works of the US Government)",
        redistributable="yes", use="Rogers test not applicable when a mark is used as a source identifier"),
    "analysis_zhonglun_dsl_2021": dict(
        url="https://en.zhonglun.com/research/articles/52403.html",
        what="Zhong Lun Law Firm 2021-07-19: New Heights in Data Protection: What You Need to Know About DSL",
        publisher="Zhong Lun Law Firm", status="secondary (law-firm analysis)",
        licence="Footer: \"Copyright © Zhong Lun Law Firm All rights Reserved\"", redistributable="no",
        use="DSL Art. 2 extraterritorial reading"),
    "greatfire_osm": dict(
        url="https://en.greatfire.org/www.openstreetmap.org",
        what="GreatFire censorship test page for www.openstreetmap.org (last test 2026-08-24)",
        publisher="GreatFire.org", status="secondary (third-party measurement)", licence=NEWS,
        redistributable="no", use="openstreetmap.org blocked in mainland China since 2012-06-12"),
    "greatfire_github": dict(
        url="https://en.greatfire.org/github.com", what="GreatFire test page for github.com (last test 2026-11-11)",
        publisher="GreatFire.org", status="secondary (third-party measurement)", licence=NEWS,
        redistributable="no", use="github.com access from mainland China unreliable (80 % interference)"),
    "greatfire_liveatc": dict(
        url="https://en.greatfire.org/www.liveatc.net", what="GreatFire test page for www.liveatc.net (last test 2026-05-05)",
        publisher="GreatFire.org", status="secondary (third-party measurement)", licence=NEWS,
        redistributable="no", use="liveatc.net reachable from mainland China (not a legal statement)"),
    "gitclone_gov_takedowns": dict(
        url="https://github.com/github/gov-takedowns (git clone --depth 1 --sparse, folder China/, commit 7f376119afd963cb164c7640f5e050f899839fa3 of 2026-11-09; .git removed after reading)",
        what="GitHub's public log of government takedown requests: the 9 China notices (2016, 2019 MPS, 2021 BNIA)",
        publisher="GitHub, Inc.", status="verified (GitHub's own transparency record)",
        licence="No LICENSE file in the repository root (observed); notices are government letters; quote only",
        redistributable="no (quote only)", use="no China notice concerns maps, aviation or ADS-B (grep, observed)"),
    "gitclone_kwsnote": dict(
        url="https://github.com/Panic-W/KWSNote (git clone --depth 1, commit 842c5b1ac971bb4e8b2f71e1d9f143b55689c28c of 2024-08-03; pruned to one file)",
        what="Personal note 航空波段收听与录音.md by a Chinese hobbyist: LiveATC search finds no Chinese airport incl. ZSSS; opinion on listening legality",
        publisher="GitHub user Panic-W", status="unverified (personal note)",
        licence="No licence observed for the file; all rights reserved assumed", redistributable="no (quote only)",
        use="only evidence found on LiveATC coverage of ZSSS"),
}

NOT_KEPT = [
    dict(url="https://www.globalsecurity.org/intell/library/news/2025/intell-250323-globaltimes01.htm",
         reason="HTTP 402: site demands payment for AI/data-centre retrieval; response deleted, not paid, not used"),
    dict(url="https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32017R1001", reason="HTTP 404; EU trade mark regulation not read"),
    dict(url="https://www.morganlewis.com/pubs/2021/06/what-chinas-new-data-security-law-means-for-multinational-corporations",
         reason="HTTP 404; replaced by the Zhong Lun analysis"),
    dict(url="https://www.12339.gov.cn/article/h5_law_con/1", reason="connection reset (MSS reporting site)"),
    dict(url="https://ga.hainan.gov.cn/sgat/zmgzyw/202109/3a188c3bbbc44215b92a3b6661ac21c5.shtml", reason="connection reset"),
    dict(url="http://www.npc.gov.cn/wxzl/wxzl/2000-12/17/content_4680.htm", reason="served the NPC front page, not the law; deleted"),
    dict(url="https://ntpp.chinaairports.org.cn/uploads/file/20250807/1754530113657101.pdf",
         reason="connection reset; MH/T 3039-2025 civil-aviation data grading standard not read"),
    dict(url="http://web.archive.org/web/20190515050936/https://www.liveatc.net/search/?icao=zsss",
         reason="Wayback snapshot exists per archive.org/wayback/available, but web.archive.org is refused by the session proxy (403) / connection reset; not read"),
    dict(url="https://www.liveatc.net/search/?icao=ZSSS", reason="HTTP 403 Cloudflare challenge page ('Just a moment...'); not circumvented"),
    dict(url="https://github.com/tevelee/sky-watch (clone)", reason="only an IATA->ICAO map and LiveATC feeds for 4 non-Chinese airports; deleted as irrelevant"),
]

REUSED = [
    dict(path="refs/cache/china_law/law_dsl_npc/", what="Data Security Law (npc.gov.cn)", by="phase0 key adsb"),
    dict(path="refs/cache/china_law/law_cel2023_npc/", what="Counter-espionage Law 2023 (npc.gov.cn)", by="phase0 key adsb"),
    dict(path="refs/cache/china_law/law_radio_gongbao/", what="Radio Regulations 2016 (State Council Gazette)", by="phase0 key adsb"),
    dict(path="refs/cache/china_law/reg_ndsm_gongbao/", what="Network Data Security Management Regulations 2024", by="phase0 key adsb"),
    dict(path="refs/cache/china_law/law_copyright_mofcom/", what="Copyright Law 2020 (MOFCOM copy)", by="phase0 key adsb"),
    dict(path="refs/cache/china_law/caac_data_mgmt_2025/", what="CAAC Civil Aviation Data Management Measures (trial) 2025", by="phase0 key adsb"),
    dict(path="refs/cache/china_law/news_ce_cn_20240106/", what="MSS 2024-01-06 ADS-B statement (repost)", by="phase0 key adsb"),
    dict(path="refs/cache/osm/api_map_zsss/ and refs/cache/osm/api_map_tiles_geo/", what="OSM API extracts around ZSSS (scanned for military tags by tools/law/osm_sensitive.py)", by="phase0 keys geo/terrain"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def main():
    out = {"topic": "law: PRC surveying/mapping, map, data-security, radio, criminal, state-secrets and trademark law; "
                    "OSM, LiveATC and GitHub status (docs/phase0/law.md)",
           "checked": DATE, "written_by": "phase0 key law",
           "note": "All downloads are untrusted data and were only read as text. Legal texts are excluded from copyright "
                   "in the PRC (Copyright Law Art. 5(1)), so their TEXT may be quoted and redistributed; host-page HTML, "
                   "news and law-firm pages are the publishers' copyright: quote only. Nothing here may be used as "
                   "geometry or texture.",
           "sources": [], "not_kept": NOT_KEPT, "reused_from_other_keys": REUSED}
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        m = dict(META.get(d, {"what": "(no metadata)", "status": "unverified"}))
        files = []
        for dp, _, fns in os.walk(p):
            for fn in sorted(fns):
                fp = os.path.join(dp, fn)
                files.append({"path": os.path.relpath(fp, ROOT), "bytes": os.path.getsize(fp), "sha256": sha(fp)})
        m.update({"dir": d, "date_checked": DATE, "files": files})
        out["sources"].append(m)
    missing = sorted(set(META) - {s["dir"] for s in out["sources"]})
    if missing:
        raise SystemExit(f"metadata for missing dirs: {missing}")
    with open(os.path.join(ROOT, "SOURCES.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(len(out["sources"]), "sources,", len(NOT_KEPT), "not kept")


if __name__ == "__main__":
    main()
