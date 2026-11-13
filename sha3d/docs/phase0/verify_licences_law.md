# Phase 0 / verify_licences_law: adversarial re-check of the `adsb` and `law` results

Checked 2026-11-13, about 20:45-21:15Z, by re-opening each cited source in this session. Re-downloads are in the
session scratchpad, not in the repo. Nothing was committed. `sfo3d/`, `pc12/` and `hwd3d/` were not touched.

The aim was to refute. A row is `confirmed` only if I found the value or quote myself in a fresh download of the
cited source, a fresh git clone, or an official copy on another host.
* 32 re-downloads are **byte-identical** to the cached copies (same SHA-256). This includes the OpenSky coverage file
  and the mofcom retry.
* Most of the others differ only in nonces or cookie tokens: the size is the same.
* Two CNIPA pages came back gzip-encoded and were decompressed before checking.

## Verdict key

* **confirmed**: re-opened, and the value and quote are there. The status label is honest.
* **wrong**: the source says something else or more, or the arithmetic fails on the data.
* **not_confirmed**: I could not re-open the source, or the claim is an absence or inference with nothing to check.
* **status_mislabelled**: the value is right but the label overstates what was read. No row needed it: the
  `secondary` and `unverified` labels were honest throughout.

## Headline findings

1. **Wrong: Radio Regulations penalty (adsb and law).** Both reports say Art. 72(2) means "a fine of up to CNY 30,000".
   The text continues: "造成严重后果的，吊销无线电台执照，并处3万元以上10万元以下的罚款". With serious consequences
   the licence is revoked and the fine is **CNY 30,000-100,000**.
2. **Missed provision: Radio Regulations Art. 75(2)/(3).** Neither report cites it, but it is the most directly
   relevant radio rule.
   * Art. 75(2) covers "境外组织或者个人在我国境内进行电波参数测试或者电波监测" (foreign organisations or individuals
     testing or monitoring radio waves inside China).
   * Art. 75(3) covers "向境外组织或者个人提供涉及国家安全的境内电波参数资料" (giving foreign parties PRC radio
     parameter data that concerns national security).
   * The fine is CNY 30,000-100,000 if the party refuses to correct, and CNY 100,000-300,000 if the consequences are
     serious.
   * So "cases rest on CEL and DSL" is incomplete. Art. 75 does not name ADS-B, so "no ADS-B-specific law" still holds.
3. **Wrong: Criminal Law Art. 111 "5-year minimum" (law).** The article reads "处五年以上十年以下有期徒刑 … 情节较轻的，
   处五年以下有期徒刑、拘役、管制或者剥夺政治权利". A minor case has no 3-year minimum, so the Art. 8 threshold
   for foreigners abroad is met only for non-minor cases.
4. **Wrong: secret catalogue items 23-24 (law).** The quote is right, but the summary merges two items.
   * Item 23 is DEM/DSM: planar ≤10 m **or height ≤15 m**.
   * Item 24 is 3-D models, point clouds, oblique and real-scene imagery and navigation maps: planar ≤10 m **or
     relative object-height accuracy ≤5 %** (地物高度相对量测精度优于（含）5%). Both apply outside military zones over
     more than 25 km² contiguous.
   * The third column is the knowledge scope (approved holders and users, 保管单位及用户), not the producer. "Generated
     by licensed surveyors/military" misreads it.
   * The 5 % height test is easy for a modelled building, so R3 is if anything understated.
5. **Wrong: OSM military-object count (law).** On the cached extracts, `tools/law/osm_sensitive.py` finds **6
   distinct elements**, not 5: 3 rail ways (1.41, 1.61, 2.18 km) and 3 `landuse=military` areas (1.21, 3.17, 3.31 km),
   two of them named as armed-police units. That is also 4 features if the spur counts once. The distances and the
   武警 naming are right. Ids are withheld here as well.
6. **Wrong: radio-horizon "nearest non-PRC sites" (adsb).** Jeju (548 km) is not the nearest.
   * By great circle from the AIP ARP, the nearer sites are:
     * Gageodo (KR), about 476 km;
     * Marado (KR), about 511 km;
     * Dongyin, Matsu (ROC), about 543 km;
     * the Ieodo Ocean Research Station (KR sea platform), about **378 km**. That is inside the 455 km FL350 horizon
       claimed for a 50 m mast.
   * The horizon formula numbers check: 455 km and 101 km. The "ground ~38 km" figure needs an aircraft antenna about
     5 m up; with 0 m it is 29 km.
   * The conclusion (no low-level coverage from outside the PRC) stands. High-level traffic over ZSSS is in theory
     within range of KR sites.
7. **Not re-openable:**
   * LiveATC (Cloudflare 403). A Playwright attempt was refused by this session's permission classifier as bot-check
     circumvention, so I did not pursue it.
   * airplanes.live terms (Cloudflare 403).
   * shanghaiairport.com home page (connection failed).
   * The lead's multi-GB globe_history scan (not re-run).
8. **Additions:**
   * OpenSky Terms 3(i): "For any publication or other disclosure, You will anonymize or de-identify … aircraft
     identifiers, sensor locations". This applies even to permitted research use.
   * The globe_history README says its data also comes from "FlyItalyADSB and TheAirTraffic.com". Each day has three
     release tags (prod, staging, mlatonly), not one.
   * The Shanghai Airport statement page answered curl with HTTP 200 today. The inventory note "unreachable by curl" no
     longer holds for that page.
   * The cached ADSBx `*.json.gz` files are plain JSON.

## adsb key

| # | Fact | Verdict | Evidence / correction |
|---|---|---|---|
| A1 | adsb.lol API licence ODbL | confirmed | OpenAPI (hash-identical): "The license for the API as well as all data ADSB.lol makes public is [ODbL](…)". The quote drops only the link markup. `info.license` = "Open Data Commons Open Database License (ODbL) v1.0". |
| A2 | Quota 500/day no key; adhoc 1,000; feeder 7,200; sponsor ≤360,000; 429 + Retry-After | confirmed | All in the OpenAPI description. Note: "(new since Sep 2026)" is inferred from sfo3d's 2026-09-24 capture of the older text. adsb.lol states no start date, and the changelog does not list key work. |
| A3 | Quota window contradicted | confirmed | OpenAPI: "a fixed 24h bucket, not midnight UTC". Docs page: "the daily window resets at 00:00 UTC". |
| A4 | Sponsor plans | confirmed | /sponsor: clearance €20, 24,000/mo; tower €50, 72,000/mo, "included with feeder"; oceanic €999, "real-time firehose". |
| A5 | globe_history ODbL, 2056 GiB | confirmed | Fresh clone, same commit 5959c79. README line 3 quote present. RELEASES.md sums to 2,105,580 MiB = 2056.2 GiB (966 assets, 2025-12-14 to 2026-11-12). Nuance: 3 release tags per day, not "one release per day"; README "Each release is 1 day of flight data". |
| A6 | Historical docs ODbL 1.0 | confirmed | "license: ODbL 1.0 , use it freely, just keep it open." |
| A7 | Feeders CC0 | confirmed | Privacy page quote present. |
| A8 | adsb.fi personal non-commercial, no licensing, cite + link, 1 req/s | confirmed | Fresh clone, same commit 9fe1c9a. README lines 46, 53-54. |
| A9 | OpenSky operational use needs written agreement | confirmed | Terms (hash-identical): Tl;dr quote verbatim. |
| A10 | OpenSky no redistribution outside institute | confirmed | Terms 3(iii) quote verbatim. Addition: 3(i) requires anonymising aircraft identifiers for any publication. |
| A11 | OpenSky FAQ vs Terms contradicted | confirmed | FAQ §7 quote verbatim. The Terms are the binding "AGREEMENT". |
| A12 | OpenSky anonymous REST: latest state, 10 s, 400 credits/day, OAuth2 only | confirmed | REST doc: quote; credit table "Anonymous 400 Daily"; "OpenSky exclusively supports the OAuth2 … flow. Basic authentication … no longer accepted." |
| A13 | OpenSky coverage 2026-11-12 | confirmed | Re-fetched, hash-identical, 92,484 cells. Recomputed: nearest cell 233.1 km, so 0 within 233 km; 18 within 300 km at 28.6-29.4 N with altitude 6,546-11,918 m; 0 cells in 25-35 N, 100-115 E. |
| A14 | airplanes.live API 403 JSON | confirmed | Re-probed about 20:50Z: same 164-byte body, "Please contact us at contact@airplanes.live. Your email MUST include …". |
| A15 | airplanes.live contributor-only since Sep 2026 | confirmed (as secondary) | WebFetch of FlightTracker#123 (third-party issue, 2026-10-20): "In September 2026, airplanes.live moved their API to be contributor-only". The secondary label is right. |
| A16 | airplanes.live terms unreadable | not_confirmed | Still a Cloudflare challenge (403). The "unverified" label is honest. |
| A17 | ADSBx AUP, Last Updated April 17, 2026 | confirmed | Quote and "Last Updated: April 17, 2026" present. |
| A18 | ADSBx Community API $10/mo, 10,000 requests, non-commercial | confirmed | Dev hub: "What you get for $10/mo. 10,000 requests … 500ms updates"; "built for non-commercial use"; Enterprise for commercial. |
| A19 | ADSBx samples for testing and evaluation | confirmed | Quote present. |
| A20 | ADSBx coverage near ZSSS 2026-11-01 | confirmed | Recomputed on the cached files: 06Z nearest adsb_icao 106.2 km (14,650 ft) and 106.3 km (6,925 ft); 02Z 119.3 km (6,850 ft). Closer records are all `other` with nic 0; the nearest is 19.9 km, "ground" at 370 kt. Low level (<3,000 ft or ground, within 20 km): VHHH 12/19, RCTP 10/6, but ZSNJ and ZLXY only 1 aircraft each, so "low-level coverage at Nanjing, Xi'an" is thin. |
| A21 | readsb `other` = unknown source | confirmed | README-json quote present. |
| A22 | ADSBHub no use restrictions; must feed | confirmed | Terms items 1 and 3 verbatim. |
| A23 | AvioADSB CC BY-NC 4.0; anonymous 100/day; probe 0 | confirmed | Docs quote; table "Anonymous … 100 / day (UTC) … ≤ 100 nm". The cached probe is `total 0`, now = 1794601997 = 2026-11-13 20:33:17Z. Not re-probed. |
| A24 | Lead's live and archive measurement | not_confirmed | The cached `zsss_2026.11.10_prod.json.gz` agrees (75,360 traces, r 150 km, 0 traces). I did not re-run the 3.5 GB release scan. The secondary label is honest. |
| A25 | 2021 CCTV case | confirmed (as secondary) | thepaper (hash-identical, CCTV source, 2021-11-01): "2020年以来…", "查获数百套境外机构在我国违规布设的设备", "依法暂扣了其持有的设备,并进行了严肃批评教育". |
| A26 | FR24 not downloadable in China | confirmed (as secondary) | RFA 2021-11-05: "现时中国境内不能下载服务应用程式". |
| A27 | 2024-01-06 MSS statement | confirmed (as secondary) | ce.cn (hash-identical): quote present; "航空枢纽附近投放"; "依法对有关人员进行处罚". It quotes the CEL and DSL wording **without article numbers**, so "cites Art. 4" (risk R2) is our mapping. It also says each device sent about 1,000 flights and 130,000 positions a day. |
| A28 | CEL 2023 Art. 4(3) | confirmed | npc.gov.cn (hash-identical): Art. 4(3) quote verbatim. |
| A29 | DSL Art. 2 extraterritorial | confirmed | Quote verbatim (Art. 2 para. 2). |
| A30 | DSL Art. 32 | confirmed | Quote verbatim. |
| A31 | Order 790 Art. 62(4), in force 2025-01-01 | confirmed | gov.cn Gazette: "第790号", "2025年1月1日起施行", Art. 62(4) verbatim. |
| A32 | Radio Regs Art. 27(2) | confirmed | Art. 27 item (二) 单收无线电台（站） is exempt. Order 672, in force 2016-12-01. A quick search found no later revision. |
| A33 | Radio Regs Art. 41 / 72(2) fine up to CNY 30,000 | **wrong** | Art. 41 is verbatim, and it binds "使用无线电台（站）的单位或者个人". Art. 72 also says: serious consequences mean licence revocation plus **CNY 30,000-100,000**. Also missed: Art. 75(2)/(3), foreign radio monitoring inside the PRC, CNY 30k-100k, serious 100k-300k. |
| A34 | No ADS-B-specific PRC law | not_confirmed | An absence claim, honestly labelled. Counter-evidence to the "rests on CEL and DSL" part: Radio Regs Art. 75(2)/(3), above. |
| A35 | CAAC Data Measures: important/core data catalogue | confirmed | PDF (hash-identical): Art. 31 quote (pdftotext shows "９" for commas). Art. 3 limits the scope to the PRC. 试行, "自印发之日起施行". A web search found no published catalogue, but found a 2026-09 CAAC/NDA data-governance plan (search snippet only, unverified). |
| A36 | 1090ES for transport and GA; UAT for some training aircraft; full operation by 2020 | confirmed | Plan PDF (hash-identical): "运输航空采用…1090ES数据链", "通用航空采用国际民航组织标准的1090ES数据链", the UAT training-aircraft sentence, and "到2020年底,实现ADS-B OUT全面运行" (a plan target). |
| A37 | China-block equipage, ADSBx 02Z | confirmed | Recomputed: 565 hexes in 780000-7BFFFF; 468 adsb_icao, 415 of them v2; 73 mode_s; 1 mlat. |
| A38 | VariFlight no redistribution; "Source: VariFlight"; PRC courts | confirmed | Terms (hash-identical): quote verbatim; "Source: VariFlight" mandated for authorised non-commercial sharing; exclusive jurisdiction of the People's Court at the place of execution (Hefei High-tech District). |
| A39 | VariFlight ADS-B area query, trajectories, registration, quote pricing, 14-day trial | confirmed | ADS-B page (hash-identical): area, trajectory and registration queries; "14-Days Free Trial". The "customised quotation" text is on the flight-status FAQ page (cached), not on the ADS-B page. |
| A40 | Aireon "gate-to-gate, surface-to-space" | confirmed | Quote present (URL now redirects to /about/our-technology/). It is a vendor claim. |
| A41 | FlightAware AeroAPI tiers | confirmed | "Storage and distribution of derivative works for personal or academic purposes only"; $5 free/month; Personal 10 result sets/minute; Aireon "Included in Premium"; Premium $1,000/month minimum. |
| A42 | Spire custom pricing | confirmed | Quote present (hash-identical). |
| A43 | Shanghai Airport statement | confirmed | /wzaqzc/ answered curl with HTTP 200: no-redistribution quote verbatim; "本网站所提供信息仅供参考". The inventory note "unreachable by curl" no longer holds for this page. |
| A44 | Shanghai Airport flight widget fields | not_confirmed | Home page connection failed. The "unverified" label is honest. |
| A45 | Copyright Law Art. 5 | confirmed | mofcom on retry (hash-identical to the cache) and gov.cn: "本法不适用于：（一）法律、法规…及其官方正式译文". |
| A46 | Radio horizon and nearest non-PRC sites | **wrong** (in part) | Horizon numbers check (454.7 and 101.1 km). Ground 38 km assumes a ~5 m antenna (29 km at 0 m). Nearer non-PRC sites than Jeju 548 km: Gageodo about 476 km, Marado about 511 km, Dongyin (Matsu, ROC) about 543 km, Ieodo station (KR platform) about 378 km. Keelung (676 km) is also nearer than Taipei. |

## law key

| # | Fact | Verdict | Evidence / correction |
|---|---|---|---|
| L1 | Surveying Law Art. 2 | confirmed | npc.gov.cn (hash-identical): both sentences verbatim. |
| L2 | Surveying Law Art. 8 / 51 | confirmed | Art. 8 quote verbatim (approval by the State Council surveying authority with military surveying); Art. 51: CNY 100k-500k, serious 500k-1M plus expulsion. |
| L3 | Foreign-surveying Measures Art. 7, 19 | confirmed | gov.cn: Art. 7(5) "…真三维地图的编制", 7(6) "导航电子地图编制"; Art. 19 "处3万元以下罚款". |
| L4 | Map Regs Art. 2 (Order 664, 2016-01-01) | confirmed | Quote verbatim; "第664号"; "2016年1月1日起施行". |
| L5 | Map Regs Arts. 15, 22, 34 | confirmed | Art. 15 review (simple maps exempt); Art. 22 审图号; Art. 34 servers in the PRC, verbatim. |
| L6 | Map Regs Art. 55 | confirmed | Verbatim. |
| L7 | Public Map Spec 2023 item 19 | confirmed | gov.cn Gazette (hash-identical): verbatim; it also caps contour intervals at 20 m. |
| L8 | Spec item 20 | confirmed | 20(1) military airports, 营区, 军用公路、铁路专用线; 20(5) 军民合用机场…重要设施; 20(6) GNSS base stations; item 18 public-service facilities. Civil airports are not listed. |
| L9 | Spec items 22-23 | confirmed | 0.5 m imagery cap; "有效期5年"; repeals 国测法字〔2003〕1号 and 国测图字〔2009〕2号. |
| L10 | Secret catalogue item 3 | confirmed | mfa.gov.cn PDF (hash-identical, 自然资源发〔2020〕95号): "国家认定的地理信息保密处理技术算法及参数 机密 长期". The GCJ-02 link is labelled inferred, which is honest. |
| L11 | Secret catalogue items 23-24 | **wrong** (summary) | The quote is right. The summary merges the two items; see headline 4. Item 24's height test is relative object height ≤5 %, not 15 m. The third column lists approved holders, not producers. |
| L12 | GCJ-02 basis (Wikipedia) | confirmed (as secondary) | Wikitext (hash-identical) has the quote, GB 20263-2006 §4.1 and 地形图非线性保密处理算法. |
| L13 | State Secrets Law 2024 Art. 36 | confirmed | big5.gov.cn: "防範數據匯聚、關聯引發的泄密風險" in Art. 36. |
| L14 | Criminal Law Art. 8 / Art. 111 | **wrong** (Art. 111) | Art. 8 is verbatim. Art. 111 is 5-10 years, but "情节较轻的，处五年以下有期徒刑、拘役、管制或者剥夺政治权利", so there is no universal 5-year minimum. Text as amended to Amendment XII (2023-12-29). |
| L15 | DSL Art. 2(2), Art. 3 | confirmed | Art. 3 "数据处理，包括数据的收集、存储、使用、加工、传输、提供、公开等". |
| L16 | CEL Art. 4(3), 66 | confirmed | Art. 66: "自被驱逐出境之日起十年内不准入境", decided by the State Council national security authority. |
| L17 | CAAC Measures Art. 3, 31 | confirmed | As A35. Whether flight tracks are important data is still unknown. |
| L18 | MSS 2025-03 radio case | confirmed (as secondary) | secrss repost of MSS, dated 2025-03-23: both sentences verbatim. These were ship positions, not aircraft. |
| L19 | MSS 2026-10 open-map case | confirmed (as secondary) | stdaily, 2026-10-17, source "国家安全部微信公众号": both fragments verbatim; "依法对其开展审查"; "不转发、不扩散任何标注有涉密地理信息的地图内容". |
| L20 | OSM blocked in mainland China | confirmed (as secondary) | GreatFire: quote verbatim; "interference … since 2012-06-12". |
| L21 | OSM wiki legality view | confirmed (as secondary) | Wikitext (hash-identical) quote verbatim. The licence footer is CC BY-SA 2.0, as stated. |
| L22 | Military-tagged OSM objects near ZSSS | **wrong** (count) | 6 distinct OSM elements (3 rail ways at 1.41-2.18 km; 3 landuse areas at 1.21, 3.17 and 3.31 km, 2 named as armed police), not 5. Distances and naming are right. |
| L23 | Hongqiao civil/military status | confirmed (as secondary) | The re-downloaded wuhanqing AIP mirror shows "CIVIL/4E". Wikipedia: "From late 1963, it was rebuilt for civilian use and was reopened in April 1964." The 1963-1971 joint use is still unverified. |
| L24 | Radio Regs Art. 27(2), 41, 72 | **wrong** (penalty) | As A33: Art. 72 rises to CNY 30k-100k plus licence revocation. Art. 75(2)/(3) is missed. |
| L25 | LiveATC feeds for ZSSS | not_confirmed | KWSNote (fresh clone, commit 842c5b1) line 25 verbatim. liveatc.net/search/?icao=ZSSS still returns 403. The archive.org availability API confirms a snapshot `20190515050936` exists; its content could not be read. Whether a ZSSS feed exists today is not established. GreatFire says liveatc.net was reachable from the mainland on 2026-05-05. |
| L26 | Trademark Law 2019 Art. 48 | confirmed | cnipa (gzip-decoded): verbatim. |
| L27 | Trademark Law 2026 revision | confirmed | cnipa interview: adopted 2026-06-26, 第七十七号主席令, "将于2027年1月1日起施行", internet use in scope. The interview does not number the article; "new Art. 2" comes from elsewhere (probably the Han Kun PDF, not re-opened). |
| L28 | Jack Daniel's v. VIP | confirmed | supremecourt.gov PDF (hash-identical): quote verbatim; the noncommercial exclusion "does not shield … a designation of source". |
| L29 | GitHub gov-takedowns China | confirmed | Fresh sparse clone, same commit 7f37611: 9 files (2016 ×1, 2019 MPS ×6, 2021 BNIA ×2); no map, 地图, 航空, ADS-B, flight or 测绘 hits; README quote verbatim. |
| L30 | AIP Nil threshold coordinates | confirmed (as secondary) | The re-downloaded mirror AD 2.12 shows "Nil" under "THR coordinates & RWY end coordinates & THR geoid undulation". This agrees with verify_official A12. |

## Inventory and redistributability claims

* **Confirmed:**
  * adsb.lol API and globe_history: ODbL. Redistribution is allowed with attribution; share-alike applies to
    derivative databases, while produced works such as rendered scenes need only the notice.
  * adsb.fi, OpenSky, ADSBx, VariFlight and Shanghai Airport: no redistribution.
  * ADSBHub: redistribution allowed, but only for users who feed.
  * AvioADSB: CC BY-NC 4.0, so non-commercial use with attribution.
  * AeroAPI Personal: personal and academic use only.
  * PRC law texts: excluded from copyright by Art. 5(1).
  * Wikipedia: CC BY-SA 4.0 (footer re-read). OSM wiki: CC BY-SA 2.0 (footer re-read).
  * US Supreme Court opinion: a US government work.
* **Not confirmed:**
  * airplanes.live: the terms are unreadable.
  * CAAC PDFs: their Art. 5 status is inferred. The 2025 Measures are a 规范性文件 and probably fall under it.
* **Correction:** the Shanghai Airport statement page is reachable by curl. Only the home page failed.
