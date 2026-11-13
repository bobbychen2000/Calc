# Phase 0 / aip: official aerodrome data for ZSSS (AIP China)

Date checked: 2026-11-13 (all downloads that day; UTC times and SHA-256 are in each `SOURCES.json` under
`sha3d/refs/cache/aip/`). Scope: what the CAAC AIP says about Shanghai Hongqiao (SHA / ZSSS), whether we can
read it, and whether we may redistribute it.

## Verdict (short)

* **The official eAIP AD 2 ZSSS text and charts could not be read from the official site.** The AIP sits behind a
  login on https://www.eaipchina.cn/.
  * The login page says: "The China Aeronautical Information Publication (AIP) can be registered and accessed free
    of charge via this website." Registering needs a user ID, an e-mail address and an organisation class.
  * Without a session token the package API answers `{"retCode":0,"data":null,"retMsg":"login has expired"}`.
    This holds for `/eaip/package/listPage` and for `/datasetPackage/datasetPackage/listValidDataset` (the AIP
    dataset).
  * I did not register. Registering needs the owner's details and an owner decision.
  * Headless Chromium (Playwright) got `HTTP 502 "upstream request failed"` from the sandbox proxy for
    `https://www.eaipchina.cn/` and `/config.js`. Plain curl got 200 for the same URLs. I did not try to work
    around the 502.
* **Official items that ARE public, read and saved:**
  * The **NOTAM Summary of Nov 2026** (ATMB AIS, NOTAM in force on 2026-11-02 07:06 UTC). It establishes the
    current AIRAC: **AIP China AMDT NR.11/2026, effective 1600 UTC 28 Oct 2026**. AMDT NR.12/2026 follows at
    1600 UTC 25 Nov 2026; for ZSSS it brings "WDI LCA CHANGED". The summary also holds 19 ZSSS NOTAMs.
  * The **ZSSS "AD Situation Awareness" arrival-alert sheet** (official, "Not for Navigational Purposes"). It is
    the only ZSSS chart on the public page.
* **Next-best source: an unofficial copy of the AIP.**
  * The full **AD 2 ZSSS text (AD 2.1-2.23, 65 pages)** and **all AD 2.24 charts** of the **EAIP2026-07** edition
    are mirrored by a hobbyist chart site, chart.wuhanqing.cn.
  * The AD 2 pages are dated "2026-6-1 ... EFF2607081600". The charts are EFF2606101600, and EFF2607081600 for the
    parking chart 2P-1.
  * The content has the official page furniture ("中华人民共和国航空资料汇编 AIP CHINA ... 中国民用航空局 CAAC"). It
    agrees with the official NOTAMs wherever the two overlap: the 18L/36R DTHR, taxiway names, and stands 101,
    267, 316-342.
  * It is **at least 4 AIRAC cycles old** and **not authenticated**. Every value from it is marked `secondary`.
  * www.caac.gov.cn: HTTPS was reset by the proxy, while plain HTTP worked. Its search is a JavaScript app. I found
    no CAAC publication there with ZSSS aerodrome data.
* **Key values (AIP EFF 2026-07-08, secondary).**

  | Item | Value |
  |---|---|
  | ARP | **N31°11.8' E121°20.1'**, "Center of RWY18L/36R" |
  | Elevation | 3.0 m |
  | Magnetic variation | 5°46'W (2017), -42" per year |
  | Aerodrome hours | **H24** |
  | RWY 18L/36R | **3400 x 45** ASPH (CONC ends), 177.34° GEO; THR and END both displaced 100 m; LDA 3200 |
  | RWY 18R/36L | **3300 x 60** CONC, 177.33° GEO; THR displaced 300 m, END displaced 150 m; SWY 150 m; LDA 2850 |
  | Centreline spacing | 365 m, with the north ends aligned |
  | Stands | **161** in the stand-limits table (101-608 series), plus temporary stands TP01-TP08 |
  | VDGS stands | **54**: 101-127 (T1) and 221-275 (T2) |

  **THR coordinates are "Nil" in AD 2.12.** The AIP does not publish runway threshold or stand coordinates for
  ZSSS. The ZSSS waypoint list also has no runway points.
* **ARP vs OurAirports.** The OurAirports point (31.198104, 121.33426) is **174 m** from the AIP ARP as printed
  (31.196667, 121.335000).
  * The AIP ARP is given only to 0.1', which is +/-92 m N-S and +/-79 m E-W.
  * The OurAirports point lies **outside** that rounding box in latitude (0.086' north).
  * The AIP defines the ARP as the centre of RWY18L/36R. OurAirports sits between the two runways, **196 m** west
    of the OSM centre of RWY18L/36R.
  * So the working hypothesis "OurAirports = official ARP" is **contradicted**. The OurAirports point is a generic
    airport point, not the AIP ARP.
* **Licence: no terms of use or copyright notice is published on any public page of the eAIP.** Nothing in the
  site shell, the JS strings, the footer (ICP number only), the AD 2 text or the charts states one.
  * Without a stated licence, the default is all rights reserved (CAAC).
  * **Nothing from the AIP or its mirrors may go into the public repo**: not the PDFs, not chart images, not tables
    transcribed from them.
  * Facts may be cited and measured as reference.
  * A Commons copy of a 2026 CAAC chart is tagged {{PD-China}}. That tag's own text is about copyright term expiry,
    which cannot apply to a 2026 chart, so it is no evidence of a free licence.

## Sources (IDs used in the facts table)

| ID | Source | Official? | Saved in `refs/cache/aip/` |
|---|---|---|---|
| E0 | https://www.eaipchina.cn/: page shell, `config.js`, JS bundle `js/index.7f3eba16.js` + chunks, API answers | yes (CAAC ATMB AIS) | `eaip_site_shell/` |
| E1 | https://www.eaipchina.cn/eaip/airportChartFile/ZSSS/en/ZSSS%E4%B8%8A%E6%B5%B7%E8%99%B9%E6%A1%A5.pdf (listed by POST https://www.eaipchina.cn/eaip/airportChart/listPublish) | yes | `eaip_ad_situation_zsss/` |
| E2 | https://www.eaipchina.cn/eaip/homeFile/NOTAM_SUMMARY/NOTAM%20Summary%20In%20Nov.2026/2026-11.zip (listed by POST https://www.eaipchina.cn/eaip/homeFile/listPublish) | yes | `eaip_notam_summary_2026-11/` |
| M1 | https://chart.wuhanqing.cn/Terminal/ZSSS-%E4%B8%8A%E6%B5%B7%E8%99%B9%E6%A1%A5/AD%202.24%20Charts%20related%20to%20an%20aerodrome.pdf: AD 2.1-2.23 text, EFF2607081600 | no (mirror of AIP) | `wuhanqing_mirror_eaip2026-07_zsss/` |
| M2 | https://chart.wuhanqing.cn/Terminal/ZSSS-%E4%B8%8A%E6%B5%B7%E8%99%B9%E6%A1%A5/ZSSS-2A-1-ADC.pdf: aerodrome chart 2A-1, EFF2606101600 | no (mirror) | same |
| M3 | https://chart.wuhanqing.cn/Terminal/ZSSS-%E4%B8%8A%E6%B5%B7%E8%99%B9%E6%A1%A5/ZSSS-2P-1-APDC.pdf: aircraft parking chart 2P-1, EFF2607081600 | no (mirror) | same; also 2A-2, 2R-1..5 (ground movement / LVO routes), 0G-1..3 (VDGS pilot instructions), 0W-1, 0C-1, 1D-1, 6A-1/2 |
| O1 | https://opennav.jp/pdf/ZSSS/ZSSS-1A.pdf (+1B, 2A, 2B, 4A): AIP charts of 2013/2019, superseded | no (mirror) | `opennav_zsss_charts_2021/` |
| OA | https://davidmegginson.github.io/ourairports-data/airports.csv (row 27225 ZSSS) | no | `../ourairports_runways/` (fetched by the geo task) |
| OSM | OSM API map tile, runway-end nodes as listed in `docs/phase0/geo.md` section 5 | no | `../osm/api_map_zsss/` |
| W | https://en.wikipedia.org/w/index.php?title=Shanghai_Hongqiao_International_Airport&action=raw | no | not saved |
| C | https://commons.wikimedia.org/w/index.php?title=File:Shanghai_Hongqiao_Airport_CAAC_Chart.png&action=raw | no | `commons_caac_chart_zsss/` (image itself: HTTP 429, not saved) |

Derived (ours, from M1): `refs/cache/aip/derived_aip_zsss/` (`stands.json`, `obstacles.json`, text/tables), made
by `sha3d/tools/aip/extract_ad2.py`. The ARP/geometry numbers come from `sha3d/tools/aip/arp_check.py`.

## Facts table

Date checked is 2026-11-13 for every row.

Status key:

* `verified`: read on the official CAAC site.
* `secondary`: read in the unofficial AIP copy (M1-M3, O1) or in OurAirports, OSM or Wikipedia.
* `unverified`: not read in any primary text.
* `contradicted`: sources disagree; both values are given.

Quotes are verbatim from the source text: pdftotext output, or the JSON body.

| # | Topic | Value | Source | Date | Quote | Status |
|---|---|---|---|---|---|---|
| 1 | eAIP access | AIP needs a (free) registered login; not read | E0 | 2026-11-13 | "The China Aeronautical Information Publication (AIP) can be registered and accessed free of charge via this website." / API: `"retMsg":"login has expired"` | verified |
| 2 | eAIP public items | Login page offers without login: Flight Routes Information, NOTAM Summary, "AD Situation Awareness(Not for navigation)", AIP dataset page (dataset list itself needs login) | E0 | 2026-11-13 | `login:{title:{flightRoutes:"Flight Routes Information",notam:"NOTAM Summary",adSituation:"AD Situation Awareness(Not for navigation)",login:"eAIP Login"}` | verified |
| 3 | eAIP terms / copyright | None published on public pages; footer shows only an ICP licence number; offline mode credits "中国民用航空局空中交通管理局 ATMB，CAAC" | E0 (chunk 516, 594) | 2026-11-13 | `"京ICP备14005333号-1"` | verified (absence observed on public pages; terms behind login unknown) |
| 4 | Current AIRAC | AIP China AMDT NR.11/2026 effective 1600 UTC 28 Oct 2026; next AMDT NR.12/2026 effective 1600 UTC 25 Nov 2026 | E2 (A.pdf, NOTAM A4854/26, A5342/26) | 2026-11-13 | "AIP CHINA AMENDMENT NR.11/2026(2026-9-17) WILL BE EFFECTIVE FROM 1600UTC ON 28 OCT 2026." / "AIP CHINA AMENDMENT NR.12/2026(2026-10-15) WILL BE EFFECTIVE FROM 1600UTC ON 25 NOV 2026." | verified |
| 5 | Pending ZSSS change | AMDT 12/2026 changes the wind-direction-indicator locations at ZSSS | E2 (A5342/26) | 2026-11-13 | "6.WDI LCA CHANGED AT SHANGHAI/HONGQIAO AIRPORT(ZSSS)." | verified |
| 6 | Identity | ZSSS / SHA, SHANGHAI/Hongqiao | E0 API (`airportChart/listPublish`), E1, M1 AD 2.1 | 2026-11-13 | `"airportCode":"ZSSS","airportCnName":"上海/虹桥","airportEnName":"SHANGHAI/Hongqiao"`; E1: "HONGQIAO INTL（SHA）ARRIVAL ALERT"; M1: "ZSSS/SHA-上海/虹桥 SHANGHAI/Hongqiao" | verified (official list + sheet); AD 2.1 wording secondary |
| 7 | Runway / taxiway order (W to E) | TWY C, RWY 36L, TWY B, RWY 36R, TWY A (landing north) | E1 | 2026-11-13 | "TWY C 36L TWY B 36R TWY A" / "Pilots confuse RWYs 36L/R and TWY A/B/C" | verified |
| 8 | ARP | N31°11.8' E121°20.1' (= 31.196667 N, 121.335000 E as printed), site "Center of RWY18L/36R" | M1 AD 2.2-1; same on M2 and on O1 (2019) | 2026-11-13 | "N31°11.8′ E121°20.1′ ... Center of RWY18L/36R" | secondary |
| 9 | ARP precision (inferred) | 0.1' = +/-92 m N-S, +/-79 m E-W. OSM centre of RWY18L/36R is N31°11.871' E121°20.177': the AIP digits match truncation, not rounding (rounding would give 11.9'/20.2'). | M1 + OSM, `tools/aip/arp_check.py` | 2026-11-13 | (computed) | inferred |
| 10 | Datum | AD 2 ZSSS states no datum. GEN 2.1 not readable (login). AIP China reportedly moved to WGS-84 in 2011-2012. | M1 (absence); ICAO APAC 2012 paper https://www.icao.int/APAC/Meetings/2012_AAITF_7/IP03%20China_Transition%20to%20WGS84.pdf returned HTTP 403, seen only as a search-result summary | 2026-11-13 | search summary: "Amendment Nr.4/12 (effective 5 April 2012) the content of GEN 2.1 item 3 'Geodetic reference datum' is to be revised to 'WGS-84'" (not verbatim from the PDF) | unverified |
| 11 | ARP vs OurAirports | OurAirports 31.198104, 121.33426 lies 174.3 m from the printed AIP ARP (bearing 336° true), outside its 0.1' box in latitude, and 195.5 m from the OSM centre of RWY18L/36R (the AIP's ARP definition) | OA + M1 + OSM | 2026-11-13 | OA row: `27225,"ZSSS",...,31.198104,121.33426,10,...` | contradicted (OA is not the AIP ARP) |
| 12 | Elevation / temperatures | AD ELEV 3.0 m; reference temperature 32.0 °C (JUL); mean low 1.4 °C (JAN); geoid undulation blank | M1 AD 2.2-3/4 | 2026-11-13 | "3.0 m/32.0℃(JUL)/1.4℃(JAN)" | secondary (OA 10 ft = 3.0 m agrees) |
| 13 | Magnetic variation | 5°46'W (2017), annual change -42"; charts show VAR5.8°W | M1 AD 2.2-5; M2 | 2026-11-13 | "5°46′W(2017)/-42″" | secondary |
| 14 | Location / operator / class | 253° GEO, 13.3 km from Renmin Square; operator Shanghai Hongqiao International Airport Company, Ltd.; IFR-VFR; CIVIL/4E | M1 AD 2.2-2/6/7/8 | 2026-11-13 | "253°GEO, 13.3km from Renmin square" / "CIVIL/4E" | secondary |
| 15 | Hours (AD 2.3) | Aerodrome H24; customs, health, AIS/ATS/MET briefing, ATS, fuel, handling, security, de-icing "HS or O/R". No curfew in AD 2.3. | M1 AD 2.3 | 2026-11-13 | "AD Operational hours ... H24" | secondary |
| 16 | Night restriction | No landing on RWY18R/36L 1600-2300 UTC daily (except alternates); no towing across runways 2200-1600 UTC | M1 AD 2.20 2.1.6, 2.2.6 | 2026-11-13 | "Aircraft is forbidden to land on RWY18R/36L from UTC 1600 to 2300 daily(except alternate)." | secondary |
| 17 | RWY 18L/36R | 3400 x 45 m; 177.34° GEO / 183° MAG (18L), 357.34° / 003° (36R); ASPH 100-3300 m, CONC 0-100 and 3300-3400 m; PCR 1030/R/A/W/T (ASPH), 880/R/B/W/T (CONC); shoulders 7.5 m; blast pads 60 x 60 m; strip 3320 x 300; RESA 240 x 120; SWY/CWY nil | M1 AD 2.12 | 2026-11-13 | "177.34°GEO 18L 3400×45 PCR 1030/R/A/W/T ... ASPH" | secondary (OSM azimuth 177.337° agrees) |
| 18 | RWY 18R/36L | 3300 x 60 m CONC; 177.33° GEO / 183° MAG, 357.33° / 003°; PCR 880/R/A/W/T; SWY 150 x 60 (CONC); CWY 60 x 300; strip 3420 x 300; RESA 240 x 150; blast pads 120 x 75; grooved full length | M1 AD 2.12 | 2026-11-13 | "177.33°GEO PCR 880/R/A/W/T 18R 3300×60 CONC/CONC" | secondary (OSM 177.306°) |
| 19 | Runway geometry | RCL spacing 365 m, north ends aligned | M1 AD 2.12 remarks | 2026-11-13 | "The distance between RCL18R/36L and RCL18L/36R is 365m, and their north ends aligned." | secondary (OSM gives 365.2 m) |
| 20 | Displaced thresholds | 18L and 36R THR displaced 100 m and ENDs displaced 100 m inwards (CONC); 18R and 36L THR displaced 300 m, ENDs displaced 150 m | M1 AD 2.12 remarks; M2 note 1 | 2026-11-13 | "THR18L displaced 100m inwards." ... "THR18R displaced 300m inwards." ... "ENDs of RWY18R/36L displaced 150m inwards" | secondary (official NOTAM F4275/26 also refers to "RWY18L DTHR") |
| 21 | THR coordinates | **Not published**: column "THR coordinates & RWY end coordinates & THR geoid undulation" = Nil for all four | M1 AD 2.12 | 2026-11-13 | "18L 3400×45 PCR ... Nil" | secondary |
| 22 | THR / TDZ elevations | 18L THR 2.1, DTHR 2.0, TDZ 2.3; 36R THR 2.7, DTHR 2.6, TDZ 2.8; 18R THR 2.6, DTHR 2.6, TDZ 2.6; 36L THR 2.6, DTHR 2.7, TDZ 2.6 (m) | M1 AD 2.12; M2 | 2026-11-13 | "THR 2.1m DTHR 2.0m TDZ 2.3m" | secondary |
| 23 | Declared distances | 18L & 36R: TORA/TODA/ASDA 3300, LDA 3200 (from T1 / H7: 3188); 18R & 36L: TORA 3150, TODA 3210, ASDA 3300, LDA 2850 (from H2 / H6: 2988/3048/3138) | M1 AD 2.13 | 2026-11-13 | "18L 3300 3300 3300 3200 THR displaced 100m inwards,END displaced 100m inwards" | secondary |
| 24 | Approach / runway lighting | All four: PALS CAT I with SFL (900 m; 840 m for 18R); green THR + WBAR; PAPI 3° (18L left 474 m inside DTHR, MEHT 22.3 m; 36R right 474 m, 22.3 m; 18R left 393 m, 19.5 m; 36L right 393 m, 19.5 m); no TDZ lights; RCLL 30 m spacing; REDL 60 m; red RENL; 18R/36L 150 m red SWY lights | M1 AD 2.14 | 2026-11-13 | "PALS CAT Ⅰ ... PAPI LEFT 474m inward DTHR18L 3° 22.3m ... TDZ LGT LEN Nil" | secondary |
| 25 | WDI (to change 2026-11-26) | 18L: 90 m E of RCL, 450 m inside THR18L; 36R: same; 18R/36L: 120 m E of RCL, 380 m inside THR | M1 AD 2.15 | 2026-11-13 | "18L: 90m E of RCL, 450m inward THR18L, LGT." | secondary, superseded by AMDT 12/2026 |
| 26 | SMGCS / RWSL | Guidance signs at all TWY/RWY intersections and holding positions; guide lines everywhere; THLs on all 4 runway ends; RELs on H1-H7 (18R/36L) and H1, T1, H4, H7, T6 (18L/36R); stop bars on rapid-exit TWYs; Type A runway guard lights. **No A-SMGCS, SMR or multilateration remark in AD 2 ZSSS.** | M1 AD 2.9, AD 2.20 2.8 | 2026-11-13 | "RELs(RWY18L/36R: TWY H1, T1, H4, H7, T6; RWY18R/36L: TWY H1-H7)" | secondary (absence of A-SMGCS text observed in M1 only) |
| 27 | ADS-B / transponder | SSR transponder mandatory; AD 2.22 section 4 is titled "Radar procedures and/or ADS-B procedures" but contains no ADS-B-specific rule; no ZSSS ADS-B NOTAM in force | M1 AD 2.20 1.1, AD 2.22 4; E2 | 2026-11-13 | "Take-off/landing aircraft without SSR transponder are forbidden." | secondary (NOTAM part verified) |
| 28 | Runway use | 18R/36L mainly departures, 18L/36R mainly arrivals; cross 18R/36L via H1-H7, 18L/36R via H1, H4, H7; landing aircraft must not vacate via H3, H4, H5; vacate within 50 s | M1 AD 2.20 2.1-2.3 | 2026-11-13 | "RWY18R/36L mainly used for departure; RWY18L/36R mainly used for arrival" | secondary |
| 29 | End-around taxiways | ROUTE-NORTH (TWY BN then N) and ROUTE-SOUTH (BS then S), normally H24 for arrivals to the west apron; wingspan < 36 m normal, 36-65 m limited, >= 65 m forbidden; visual screens 388 m beyond the 18R/36L ends | M1 AD 2.20 2.3.3 | 2026-11-13 | "ROUTE-NORTH: TWY BN→ TWY N; ROUTE-SOUTH: TWY BS→ TWY S." | secondary |
| 30 | Taxiways (AD 2.8) | A, A1-A4, B, B1-B8, BN, BS, C, C1-C4, D, D3-D17, H1-H7, K1, K2, K4-K7, L01, N, S, T1, T6. Widths 23-60 m (A, B, C, D 23 m; D9, D13 60 m). CONC except BN/BS ASPH. Rapid exits B7, B8, C1-C4 grooved. | M1 AD 2.8-2/6 | 2026-11-13 | "23m : A, B, B1-B8, BN, BS, C, C1-C4, D, ..." / "B7, B8, C1, C2, C3, C4: Rapid exit TWY grooved in full length" | secondary |
| 31 | Apron taxilines | Y1-Y3, M1-M6, L16, D, L01 (wingspan <= 68.4 m); L10, L11, L15, L17-L19 (< 65); L12-L14, L20 (< 36); L08 (< 31). Y1-Y3 arrivals only; M1-M6 and L11-L17 departures only. | M1 AD 2.20 3.1 | 2026-11-13 | "TWY Y1-Y3 are only used for arrival, and TWY M1-M6, L11-L17 are only used for departure." | secondary |
| 32 | Aprons | Apron Nr.2 (T2, west: 212-290), Nr.4 (401-416, NW), Nr.6 (601-608, SW), east aprons (101-127 at T1, 310-342 incl. business apron 310-312, 501-525); apron CONC, PCR 750-970 | M1 AD 2.8-1, M3 | 2026-11-13 | "PCR 940/R/B/W/T : Apron Nr. 4, 6, Stands Nr. 286-290" | secondary |
| 33 | Stand list | 161 stands. 1xx (13): 101, 102, 109-115, 120, 121, 126, 127. 2xx (68): 212-238 incl. 216E, 220E; 240, 246, 248, 250, 256, 257, 259-290 incl. 281E. 3xx (33): 310-342. 4xx (19): 401-416 incl. 404C, 408C, 413E. 5xx (19): 501, 502, 504, 506, 508, 510, 511, 514-525. 6xx (9): 601-603, 604A, 604B, 605-608. Plus temporary TP01-TP08. Combined stands: 215/216/216E, 219/220/220E, 280/281/281E, 412/413/413E. | M1 AD 2.20 3.2.6-3.2.8 (`derived_aip_zsss/stands.json`) | 2026-11-13 | "248 ≤68.4 Taxi in, Push back" ... "310-312 ＜31 ＜33 Taxi in, Push back" | secondary |
| 34 | Stand sizes | Largest: 248 (<= 68.4 m span; B747-8 normal stand; 250, 411, 511 with restrictions). < 65 m: 102, 111, 112, 126, 127, 216E, 220E, 250, 281E, 283, 284, 313-315, 406, 411, 413E, 414-416, 501, 502, 504, 506, 508, 510, 603, 606. Most others < 36 m. All "Taxi in, Push back". | M1 AD 2.20 2.5.1, 3.2.6 | 2026-11-13 | "B747-8 can normally use stand Nr.248 or use stand Nr. 250, 411 or 511 with restrictions" | secondary |
| 35 | VDGS stands | 54: 101, 102, 109-115, 120, 121, 126, 127 (T1, VDGS guide III; 112 guide II) and 221-238, 240, 246, 248, 250, 256, 257, 259-275 (T2, ZSSS DGS chart 0G); other stands marshaller | M1 AD 2.9-1, AD 2.20 3.2.2.3; M (0G-1..3) | 2026-11-13 | "Visual docking guidance system at aircraft stands Nr. 101, 102, 109-115, 120, 121, 126, 127, 221-238, 240, 246, 248, 250, 256, 257, 259-275, Marshalling assistance for other aircraft stands." | secondary |
| 36 | Jet bridges | AIP has **no list** of bridge (contact) stands; AD 2.20 3.5.1 only distinguishes "boarding bridge stand" and "remote stand". Bridge stands = the 54 VDGS stands is an **inference**. | M1 AD 2.20 3.5.1 | 2026-11-13 | "The aircraft parking on boarding bridge stand shall turn off APU and use bridge 400Hz power supply" | secondary (list: inferred) |
| 37 | Stand coordinates | **None published** (no stand-coordinate table in AD 2 or on 2P-1, 2R-x) | M1, M3 | 2026-11-13 | (absence) | secondary |
| 38 | Stand ID signs | Stands with ID sign boards listed (101-127 ... 601-608, not all stands) | M1 AD 2.9-1 | 2026-11-13 | "Aircraft stand identification sign boards at stands Nr. 101, 102, 109-115, ..." | secondary |
| 39 | AIP stands vs OSM | AIP-only: 216E, 220E, 281E, 404C, 408C, 413E, 414, 415, 416, 514, 515, 516. OSM-only refs: 238A, 239, 240A, 258, 259A, 301-309, 604. Other 149 refs agree. | M1 + OSM map tile | 2026-11-13 | (computed) | contradicted (OSM has old/renumbered stands; the AIP 2P-1 says "Changes: Stand number adjusted") |
| 40 | Frequencies | ATIS 132.25 (D-ATIS, H24); Delivery 121.75 (121.55), 0000-1200 UTC, DCL; GND(E) 121.6 (121.575), GND(W) 121.9 (121.575); TWR(E) 118.1 (124.3), TWR(W) 118.65 (118.25); APN(E) 121.675 (121.55), APN(W) 121.95 (121.55); Shanghai Approach APP01-APP14 (H24: APP02 125.4, APP05 126.65; others by ATC: 120.3, 125.85, 123.8, 126.3, 121.1, 127.75, 121.375, 125.625, 119.075, 119.975, 120.825, 124.725); AOC "Pujiang" 130.75; EMG 121.5 | M1 AD 2.18; M2/M3 headers | 2026-11-13 | "TWR(E):118.1 (124.3) ... TWR(W):118.65 (118.25)" / "GND(W):121.9 (121.575)" | secondary |
| 41 | Frequency change since 2019 | GND(W) 121.85 (121.9) in 2019 became 121.9 (121.575) in 2026; APN(E)/APN(W) did not exist on the 2019 chart | O1 1A (EFF1907171600) vs M2 | 2026-11-13 | O1: "GND 121.6(118.1)(E) 121.85(121.9)(W)" | contradicted (time change; 2026 value supersedes) |
| 42 | Two towers | "East TWR and West TWR"; position and height of the control towers **not published** in AD 2. AD 2.10 lists a "TOWER 145°MAG/1022 m, 48 m" from the RWY18L/36R centre. That point is computed at 31.19087, 121.34329, near Terminal 1, 665 m from the OSM `aircraft_control` node. The OSM tower (110° MAG / 516 m) is not in the obstacle list. | M1 AD 2.20 3.2.1.3, AD 2.10; OSM | 2026-11-13 | "transferred from GND to TWR or between the East TWR and West TWR" / "TOWER TOWER 145/1022 48" | secondary (which tower is which: unverified) |
| 43 | Tower control area | Within 10 km W and 7 km E of RCL, SFC-QNH 300 m; TL 3600 m, TA 3000 m (ZSSS/ZSPD region) | M1 AD 2.17 | 2026-11-13 | "Within 10km west of RCL and 7km east of RCL as the landing track or ILS established from north or south." | secondary |
| 44 | Obstacles | 114 rows (MAG bearing/distance from the centre of RWY18L/36R). Within 15 km: 31 rows within 3 km, the nearest being a building at 122°/892 m, 52 m. Farther rows (15-50 km band) include a 635 m building at 081° MAG/16182 m (inferred: the Lujiazui towers). | M1 AD 2.10 (`derived_aip_zsss/obstacles.json`) | 2026-11-13 | "Obstacles within 15km of the center of RWY18L/36R" | secondary |
| 45 | Nav aids | ILS CAT I all four ends: 18L IPK 111.3 (GP 332.3), 36R IWB 110.3 (GP 335.0), 18R IHQ 110.9 (GP 330.8), 36L ISH 111.7 (GP 333.5), GP 3°, RDH 15 m; VOR/DME SHA 117.2 (7 m W of RCL, 1064 m outside DTHR18L); NDB PK 208 | M1 AD 2.19 | 2026-11-13 | "Hongqiao VOR/DME SHA 117.2 MHz CH 119X ... 7m W of RCL, 1064m outside DTHR18L" | secondary |
| 46 | RET distances (temporary) | From DTHR: 18L to B4 1850 m, A3 1890 m; 36R to B3 1950 m, A2 1715 m; vacate within 50 s | E2 F4301/26 (2026-10-14 to 2026-12-14) | 2026-11-13 | "RWY18L TWY B4 1,850M" | verified |
| 47 | Current closures (NOTAM) | RWY18L/36R CLSD 1700-2200 UTC daily 2026-11-10 to 11-29, crossing via H4/H7, with listed TWY closures; stand 267 CLSD 2026-11-14 1700 to 11-21 1000; TWY A / K1 intersection works (SUP 21/26); WIP 120-960 m north of the RWY18L DTHR | E2 F4551/26, F4552/26, F4313/26, F4516/26, F4275/26, F4276/26 | 2026-11-13 | "RWY18L/36R CLSD.ACFT SHALL CROSS RWY18L/36R VIA TWY H4,H7." / "PARKING STAND NR.267 CLSD." | verified |
| 48 | Stand allocation via datalink | LID trial: Shanghai APP sends arrival procedure, runway and parking stand by datalink 50 min before landing (stand "for reference only") | E2 F3192/26 | 2026-11-13 | "THE LID INFORMATION WILL INCLUDE EXPECTED ARRIVAL PROCEDURE, TRANSITION(ON REQUIRED), LANDING RUNWAY, AND PARKING STAND" | verified |
| 49 | Licence of mirror | Mirror cites no CAAC permission; its README calls the charts "public" | M1 repo README (git clone of WuHanqing2005/chart.wuhanqing.cn) | 2026-11-13 | "新增全部公开的 `EAIP2026-07.V1.3_Web` 全中国EAIP航图" | secondary |
| 50 | Commons copy licence | A 2026-03-15 CAAC chart on Commons is tagged {{PD-China}}; that template covers term expiry (50 years), so it is inapplicable | C | 2026-11-13 | "This image is now in the public domain in China because its term of copyright has expired." | contradicted (tag vs chart date) |
| 51 | Wikipedia | Coordinates 31°11'53"N 121°20'11"E (24 m from the OSM centre of RWY18L/36R); 18L/36R 3,400 m asphalt; 18R/36L 3,300 m concrete; elevation 3 m | W | 2026-11-13 | "coordinates = {{coord\|31\|11\|53\|N\|121\|20\|11\|E" | secondary |

## 1. Access to the official eAIP (what was tried, exactly)

1. **curl `https://www.eaipchina.cn/`** returned 200: an 873-byte Vue single-page-app shell. `config.js` sets
   `host: "https://www.eaipchina.cn", port: "/eaip", datasetPort: "/datasetPackage", serverMode: "outerline"`.
2. **Playwright Chromium** (`chromium.launch()`, no options) returned **502**, body `upstream request failed`. It did
   this twice, for `/` and for `/config.js`. The response came from the sandbox egress proxy, not from the site, and
   the proxy status listed no CONNECT failure for the host. The proxy classifier stopped further header experiments
   as "bot check circumvention", so none were made.
3. I read the **JS bundle** (`js/index.7f3eba16.js` and its 25 lazy chunks, curl).
   * The router marks only `/management` children as `requireAuth`.
   * The eAIP viewer `/eAIP` loads packages through `/package/listPage` with a `token` header taken from
     `sessionStorage`.
   * The login page calls three public endpoints with an empty JSON body: `/publication/listByLoginPage`,
     `/homeFile/listPublish` and `/airportChart/listPublish`.
4. **Public endpoints (POST `{}`):**
   * `airportChart/listPublish` lists 20 "AD situation awareness" files. One is ZSSS (`ZSSS上海虹桥.pdf`,
     createTime 2025-02-14). Downloaded: 2 pages, "ARRIVAL ALERT" for landing north and landing south. The PDF
     itself is dated 2025-09-04.
   * `homeFile/listPublish` lists the NOTAM summaries and Flight Routes Information Nr.2603-2611. I downloaded the
     Nov 2026 NOTAM summary (9 series PDFs).
   * `publication/listByLoginPage` returned an empty list.
5. **Login-only endpoints:**
   * `/eaip/package/listPage` and `/datasetPackage/datasetPackage/listValidDataset` both return
     `"login has expired"`.
   * `/eaip/package/listByGroupYear` and `/datasetPackage/meta/AIP-DS` return `"service request failed"`.
   * File downloads in the viewer append `?token=<session token>`.
6. **Registration form fields:** User ID, Password, E-mail, Organisation class (Airline, Airport, General Aviation,
   Government Agency, Public Agency, Data Service Provider, Air Traffic Management) and Organisation. The site also
   says: "The original eAlP account cannot be logged in, please register again". **Owner decision needed.**
7. **www.caac.gov.cn:**
   * HTTPS was reset by the proxy, three tries (`ws_closed_mid_exchange` in the proxy status). Plain HTTP
     `http://www.caac.gov.cn/index.html` answered 200.
   * The site search (`/so/s`) is a JS front end to `so-gov.cn`. I did not drive it.
   * Web searches restricted to caac.gov.cn found no ZSSS aerodrome-data publication. CAAC's site publishes
     statistics and regulations, not AIP content.

## 2. The AIP copy used (M1-M3) and how far to trust it

* **Origin.** chart.wuhanqing.cn is a personal hobby site; its GitHub repo was sparse-cloned for `files.json` and
  README only.
  * It republishes the full "EAIP2026-07.V1.3_Web" terminal chart set, which includes, per airport, the AD 2 text
    as "AD 2.24 Charts related to an aerodrome.pdf".
  * The AD 2 PDF is a Word export (created 2026-05-12). Every page carries "2026-6-1 ... 中国民用航空局 CAAC ...
    EFF2607081600".
* **Consistency with the official items we could read.**
  * The official NOTAMs (E2) use the same designators: RWY18L DTHR, TWY H1-H7, A2-A4, B1-B8, K1-K7, T6, C1-C4,
    D9, D10, and stands 101, 267, 316-322, 338-342.
  * The official arrival-alert sheet (E1) shows the same W-E order: C, 36L, B, 36R, A.
* **Age.** AMDT 09, 10 and 11/2026 have taken effect since 2026-07-08, and AMDT 12/2026 is due 2026-11-26.
  * Known changes since then: SUP 21/26 (TWY A/K1 works) and the WDI move (AMDT 12).
  * Anything else changed by AMDT 09-11 is **unknown** until the current eAIP is read.
* **2019 vs 2026 (O1 vs M1-M3), observed changes.**
  * Chart numbering: AD2.24-1A became 2A-1.
  * PCN became PCR.
  * Stand renumbering: the 2013 parking chart's 1-99 / 401-413 / 917-924 became the 101-608 series.
  * GND(W) frequency changed, and APN(E)/APN(W) were added.
  * 18L/36R strip changed from 3520 x 300 to 3320 x 300. The ADC note "Changes: ELEV, Chart number" also shows
    threshold elevations re-surveyed.
  * The 2013 parking chart (O1 2A) is obsolete; it is kept only as history.

## 3. Stands: what the AIP gives and does not give

* **Given (secondary):**
  * The designators of all 161 stands and 8 temporary stands.
  * The wingspan limit of each stand, plus a fuselage limit for 310-312.
  * The entry mode of each stand: all "Taxi in, Push back".
  * Combined-stand groups and push-back end points (EOP/EOT).
  * Which stands have VDGS (54) and which have ID sign boards.
  * B747-8 stands, and the stands with 400 Hz ground power.
  * The parking chart 2P-1, which shows the layout schematically.
* **Not given:**
  * Stand coordinates.
  * Stop-line positions.
  * Which stands have jet bridges. Inferred: the 54 VDGS stands at T1 (101-127) and T2 (221-275).
  * Bridge counts per stand.
* So stand positions must come from OSM (164 stand nodes) and imagery, labelled `obs`/`inf` as in sfo3d. The AIP
  list is the authority for **which designators exist**.
* **OSM differences to fix or flag:**
  * OSM has 301-309, 238A, 240A, 259A, 258, 239 and 604, which are not in the AIP.
  * The AIP has 414-416, 514-516, 404C, 408C, 413E, 216E, 220E and 281E, which are not in OSM.

## 4. Copyright / redistribution

* **Observed.**
  * eaipchina.cn publishes no licence, terms of use or copyright statement on any page reachable without login.
  * The AD 2 text and charts carry no copyright line, only "中国民用航空局 CAAC".
  * The registration terms, if any, are behind the account step.
* **Inferred (not legal advice).** With no grant, treat everything as CAAC copyright, all rights reserved.
  * PRC Copyright Law art. 5 excludes "documents of a legislative, administrative or judicial nature". Whether an
    AIP counts is not settled, and I did not read the law text in this task (unverified).
  * The Commons {{PD-China}} tag on a 2026 CAAC chart is a mis-tag.
  * The unofficial mirrors cite no permission.
* **Rule for sha3d.**
  * All AIP material and anything transcribed from it stays in gitignored `refs/cache/aip/`, including
    `derived_aip_zsss/`.
  * The public repo may carry our own geometry: OSM-based (ODbL) and imagery-measured.
  * Docs may cite AIP facts with source and date. Short factual citations are reasonable; tables or chart images
    are not.
  * This needs an owner decision before anything AIP-derived ships.

## 5. Observed vs inferred (summary)

* **Observed:**
  * All quotes above, the eAIP API answers, the NOTAM texts and the AD 2 text of the mirror copy.
  * Stand counts and lists parsed from the AD 2 tables.
  * OSM-AIP set differences, computed distances and azimuths.
* **Inferred:**
  * That the mirror copy is a faithful copy of the official AIP (consistent with E1/E2, not authenticated).
  * That the AIP ARP digits are truncated.
  * That VDGS stands equal bridge stands.
  * That the AD 2.10 "TOWER" is the old Terminal 1 tower.
  * That AIP coordinates are WGS-84 (AD 2 states no datum).
* **Not checked:**
  * Current AMDT 11/2026 content.
  * GEN 2.1 datum text.
  * AD 1.1 VDGS guides.
  * ENR ADS-B rules.
  * The SUP 21/26 content.

## 6. Risks and open questions

* The authoritative, current AD 2 ZSSS is unread. The values here are from an unauthenticated copy that is 4 AIRAC
  cycles old.
* The AIP publishes no threshold or stand coordinates. Sub-10 m placement must come from OSM and Sentinel-2
  (`geo.md`), not from the AIP.
* Redistribution is undefined. Treat it as forbidden.
* RWY18L/36R is closed nightly 1700-2200 UTC until 2026-11-29 (NOTAM). Live ADS-B tonight will show only 18R/36L
  in use during those hours.
