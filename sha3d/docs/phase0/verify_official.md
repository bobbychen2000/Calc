# Phase 0 / verify_official: adversarial re-check of the `aip` and `field` results

Checked 2026-11-13 by re-opening each cited source in this session. The re-downloads are in the session
scratchpad, not in the repo, and nothing was committed. `sfo3d/`, `pc12/` and `hwd3d/` were not touched.

The first aim was to refute. A row is `confirmed` only if I found the value or quote myself in the cited
source (or in a hash-identical re-download of it).

## Verdict key

* **confirmed**: I re-opened the source and the value and quote are there. The status label is honest.
* **wrong**: the source says something else, or the claim fails on the source's own data.
* **not_confirmed**: I could not re-open the source (403, WAF or timeout), or the claim is an inference with no
  source to check.
* **status_mislabelled**: the value is right but the status overstates what was read. (No row needed this
  verdict. Two rows are *under*-labelled, which is noted but not penalised.)

## Headline findings

1. **Wrong (aip, tower).** The AIP obstacle table **does** list the OSM control tower.
   * AD 2.10 row **031 "Control TWR", MAG 111°/520 m, 47 m, LGT** is in the mirror AD 2 text (layout line
     ~562, page AD 2-9).
   * Placed from the OSM centre of RWY18L/36R with VAR 5.77° W, that row lands **7 m** from OSM node
     3342630333 (`tower:type=aircraft_control`).
   * The aip claim "the OSM aircraft_control node is not in the obstacle list" is therefore false.
   * The cause: `derived_aip_zsss/obstacles.json` dropped that row. The "TOWER 145/1022, 48 m" row (ID 039) is a
     different structure.
   * The `field` key had this right ("Control TWR 111/520, 47 m"). The two reports contradict each other, and
     `field` is correct.
2. **Wrong (aip, obstacles).** The AD 2.10 tables number obstacles **001 to 122**, but `obstacles.json` holds
   only 114 rows.
   * My parse of the same text finds at least **9 rows missing** from the derived file:
     * 111/520 Control TWR;
     * four "Moving OBST" rows (190/1642, 357/1740, 188/2164, 350/2336);
     * four power plants (147/19609, 177/23378, 019/30231, 061/30315).
   * So the **nearest obstacle is the Control TWR at 520 m, not the building at 122°/892 m**.
   * The within-3 km count is at least **36**, not 31.
   * The 635 m row at 081°/16182 m is correct.
3. **Correction (aip, stands).** "161 stands" is the number of **designators** in the AD 2.20 3.2.6 table. The
   count itself is right: 13 + 68 + 33 + 19 + 19 + 9 = 161, with no duplicates.
   * Six of them are overlay or alternative designators, not separate stands:
     * 216E, 220E, 281E and 413E are the combined stands of AD 2.20 3.2.7. caacnews 2023 says each turns two
       code-C stands into one code-E stand.
     * 404C and 408C.
   * Physical stand positions are therefore about 155.
   * The `field` "54/161 = 33.5 % ≈ 34 %" match is weak evidence: 54/155 = 34.8 % also rounds to about 34 %.
4. **Reasoning slip (aip, ARP vs OurAirports).** The numbers are right: 174.6 m at 336° from the printed ARP,
   and 195.1 m at bearing 278° (west) from the OSM centre. The "outside the rounding box **in latitude**" argument
   is inconsistent with aip's own truncation inference.
   * If the AIP digits are truncated, the latitude box is 11.8'-11.9'. The OurAirports latitude, 11.886', is
     **inside** it.
   * OurAirports is outside the box in **longitude** (20.056' < 20.1') under either reading.
   * The conclusion (OurAirports is not the AIP ARP) still stands.
5. **eAIP terms: absence confirmed, with additions.** I fetched `index.7f3eba16.js` (hash-identical to the
   cache) and all 25 lazy chunks. Searching them for copyright, licence, terms, agreement, disclaimer, 版权, 协议,
   声明, 免责, 转载, 授权 and 同意 finds only third-party library licences and the ICP number.
   * The registration form has no terms checkbox.
   * Two items were **not reported** by the aip key:
     * The site banner string reads "Trial Phase: Data Unavailable for Formal Operation. Verify Before Use" (试运行阶段：数据暂不可用于正式运行，使用前请自行核查).
     * An order and invoice module bills "AIP China" purchases in USD to the "Aeronautical Information Service
       Center Air Traffic Management Bureau. CAAC" ("Thank you for your purchase of AIP China"). The invoice has
       a mailing address, so this is probably a printed subscription.
   * Neither item grants any reuse right. "Treat as all rights reserved, reference only" remains the right
     working rule. It is an inference, not legal advice.
   * `publication/listByLoginPage` still returns an empty list.
6. **Not confirmed.** Three claims rest on sources I could not open:
   * WGS-84 for AIP China: the ICAO IP03 PDF returns 403 behind a Cloudflare challenge, and WebFetch also gets
     403. A web search again gave only a summary.
   * The "48 → 50/h" capacity of 2023: no primary source was found by me either.
   * The SAA flight-board WAF behaviour: not re-tested.
7. **Everything else in the focus list was re-found in the source.** That covers identity, the ARP value, runway
   data, hours, frequencies, the movement statistics, the NOTAMs and the AIRAC dates.

## Verdicts: `aip` key

| # | Fact (claimed) | Verdict | Evidence (re-opened 2026-11-13) |
|---|---|---|---|
| A1 | eAIP needs login; package APIs answer "login has expired"; Playwright 502, curl 200 | confirmed | curl `/` 200 (873 B, after one reset); POST `{}` to `/eaip/package/listPage` and `/datasetPackage/datasetPackage/listValidDataset` → `{"retCode":0,"data":null,"retMsg":"login has expired"}`; Playwright `chromium.launch()` → 502 "upstream request failed" (reproduced, not worked around). The "free of charge" sentence is the `login.tip` i18n string in `index.7f3eba16.js`; the page itself could not be rendered. |
| A2 | No licence/terms/copyright on public eAIP pages; footer = ICP no. only | confirmed (absence; see headline 5 for the trial-phase banner and the purchase module) | `index.7f3eba16.js` sha256 c1ac222e… = cache; 25 chunks fetched; ICP "京ICP备14005333号-1" in chunks 516 and 594; offline footer "中国民用航空局空中交通管理局 ATMB，CAAC". |
| A3 | AMDT 11/2026 eff. 1600 UTC 28 Oct 2026; AMDT 12/2026 eff. 1600 UTC 25 Nov 2026 with "WDI LCA CHANGED AT … (ZSSS)" | confirmed | NOTAM Summary Nov 2026 zip re-downloaded, sha256 d82456e9… = cache. A4854/26 and A5342/26 quotes are verbatim. Addition: the AMDT 11/2026 main-changes list names no ZSSS item. |
| A4 | Identity ZSSS / SHA, 上海/虹桥 SHANGHAI/Hongqiao | confirmed | `airportChart/listPublish` returns `"airportCode":"ZSSS","airportCnName":"上海/虹桥","airportEnName":"SHANGHAI/Hongqiao"` (createTime 2025-02-14). Sheet title "HONGQIAO INTL（SHA）ARRIVAL ALERT". Mirror AD 2.1: "ZSSS/SHA-上海/虹桥". |
| A5 | W→E order TWY C, 36L, TWY B, 36R, TWY A | confirmed | Official sheet re-downloaded (sha256 d2991832… = cache, PDF created 2025-09-04); page 1 rendered and viewed: labels left to right in the north-facing view are C, 36L, B, 36R, A. Page 2 (south-facing) shows the reverse. |
| A6 | ARP N31°11.8' E121°20.1', "Center of RWY18L/36R" (secondary, mirror) | confirmed | Mirror AD 2 PDF re-downloaded (sha256 05e6fca2… = cache, 65 pp, "EFF2607081600"). AD 2.2 item 1 matches verbatim; also in the 2A-1 ADC header. Label `secondary` is honest. |
| A7 | ARP digits match truncation of the OSM centre (N31°11.871' E121°20.177') | confirmed (inference) | OSM API way 16714125 ends: (31.2131135, 121.3354641) and (31.1825842, 121.3371157). Centre = 11.8709', 20.1774'. Rounding would give 11.9'/20.2'. This is an inference: OSM is not the survey. |
| A8 | Datum WGS-84 (GEN 2.1 via AMDT 4/12) | not_confirmed | ICAO IP03 PDF: HTTP 403 (Cloudflare challenge) by curl and by WebFetch. Only a search summary again. Label `unverified` is honest. |
| A9 | OurAirports 31.198104, 121.33426 is 174.3 m at 336° from the AIP ARP, outside its box in latitude, 195.5 m from the OSM centre | confirmed with correction | OurAirports `airports.csv` re-fetched: row 27225 matches. My numbers: 174.6 m at 336.2°; 195.1 m at 278°. Correction: under aip's own truncation reading, OA latitude 11.886' is inside 11.8-11.9'; OA is outside only in longitude (20.056'). The conclusion is unchanged. |
| A10 | ELEV 3.0 m, 32.0 °C (JUL), VAR 5°46'W (2017) -42" | confirmed | Mirror AD 2.2 items 3 and 5 verbatim. |
| A11 | Aerodrome H24; no landing 18R/36L 1600-2300 UTC (except ALTN); no towing across RWYs 2200-1600 UTC | confirmed | AD 2.3 item 1 "H24"; AD 2.20 2.1.6 (CN: "每日 0 点-7 点"); 2.2.6 (CN: "0600-2400（北京时）"). |
| A12 | 18L/36R 3400×45, ASPH 100-3300 with CONC ends, 177.34°/183°, PCR 1030/R/A/W/T, THR/END displaced 100 m, TORA/TODA/ASDA 3300, LDA 3200, THR coordinates Nil, elevations as listed | confirmed | Mirror AD 2.12/2.13 verbatim. OSM way bearing 177.35°. |
| A13 | 18R/36L 3300×60 CONC, PCR 880/R/A/W/T, THR 300 m / END 150 m displaced, SWY 150×60, CWY 60×300, TORA 3150 TODA 3210 ASDA 3300 LDA 2850; RCL spacing 365 m, north ends aligned | confirmed | Mirror AD 2.12/2.13 verbatim. My OSM spacing is 364.4 m; the north-end latitudes differ by 17 m. |
| A14 | Lighting (PALS CAT I + SFL, PAPI 474 m / 393 m, MEHT 22.3/19.5 m, RCLL 30 m, REDL 60 m, no TDZ) | confirmed | Mirror AD 2.14 lines ~1380-1467. |
| A15 | Taxiway list and ROUTE-NORTH/SOUTH | confirmed (quotes) | AD 2.8 "23m : A, B, B1-B8, BN, BS, C, C1-C4, D, …"; AD 2.20 2.3.3 "ROUTE-NORTH: TWY BN→ TWY N". The full list was not re-enumerated. |
| A16 | 161 stands (1xx 13, 2xx 68, 3xx 33, 4xx 19, 5xx 19, 6xx 9) + TP01-TP08; largest 248 ≤68.4 | confirmed with correction | I transcribed AD 2.20 3.2.6 independently and got the same 161 designators. Correction: 216E, 220E, 281E, 413E (combined stands, 3.2.7) and 404C, 408C are overlay or alternative designators, so physical stands ≈ 155. |
| A17 | VDGS at 54 stands (13 T1 + 41 T2); bridge = VDGS is inference | confirmed | AD 2.9 sentence verbatim; 2 + 7 + 2 + 2 = 13 and 18 + 6 + 17 = 41. AD 2.20 3.5.1 has only "boarding bridge stand", with no list. |
| A18 | AIP-only 216E 220E 281E 404C 408C 413E 414-416 514-516; OSM-only 238A 239 240A 258 259A 301-309 604; 149 common | confirmed | Overpass (overpass.kumi.systems, data base 2026-07-15) `aeroway=parking_position` refs (164) vs my AIP list gives exactly these sets and 149 common. overpass-api.de was reset; the live OSM API was not re-queried for stands. |
| A19 | ATS frequencies (ATIS 132.25; DEL 121.75 (121.55) 0000-1200; GND(E) 121.6, GND(W) 121.9 (121.575); TWR(E) 118.1 (124.3), TWR(W) 118.65 (118.25); APN 121.675/121.95 (121.55); APP01-14; Pujiang 130.75); 2019 GND(W) 121.85 | confirmed | Mirror AD 2.18 and the 2A-1 header verbatim. opennav ZSSS-1A (EFF1907171600) re-downloaded: "121.85(121.9)(W)". |
| A20 | Two TWRs; tower obstacle "TOWER 145/1022 48" is near T1; **OSM aircraft_control node is not in the obstacle list** | **wrong** | AD 2.10 row 031 "Control TWR 111/520 47 LGT (RWY18L ILS/DME missed approach)" exists. Computed position 31.19662, 121.34156 is 7 m from OSM node 3342630333 (31.1966742, 121.3415341). The 145/1022 row (ID 039) is a separate "TOWER" 665 m away. "East TWR and West TWR" (AD 2.20 3.2.1.3) is confirmed. |
| A21 | No A-SMGCS/SMR/MLAT remark; SSR mandatory; AD 2.22 §4 "Radar procedures and/or ADS-B procedures" without ADS-B rule; no ZSSS ADS-B NOTAM | confirmed | Mirror grep for SMGCS, MLAT, multilat, SMR, 场面, 多点: none. Lines 1898 and 3774 verbatim. NOTAM summary: the ADS-B NOTAMs concern Kunming, Lhasa and ZSLY only. |
| A22 | 114 obstacle rows; 31 within 3 km; nearest building 122°/892 m, 52 m; 635 m in the 15-50 km band | **wrong** (count and nearest) | IDs run 001-122. My parse finds 123 bearing/distance rows; 9 are missing from `obstacles.json` (see headline 2). The nearest is Control TWR 111/520, 47 m. Within 3 km: ≥ 36. The 081/16182 635 m row is correct. |
| A23 | NOTAMs: F4551 (18L/36R CLSD 1700-2200 daily 11-10 → 11-29, cross via H4/H7), F4313 stand 267 CLSD 11-14 1700 → 11-21 1000, F4516 A/K1 works (SUP 21/26), F4301 RET distances, F3192 LID | confirmed | Same NOTAM zip; all texts verbatim. Count detail: 17 F-series NOTAMs have A) ZSSS. F4548-F4550 had already expired on 11-09. |
| A24 | Mirror cites no CAAC permission; Commons file tagged {{PD-China}} (term-expiry text) | confirmed | Mirror repo cloned (commit 060c116e, 2026-09-15). README has no licence or permission text, only "新增全部公开的 `EAIP2026-07.V1.3_Web` 全中国EAIP航图". Commons raw: `date=2026-03-15`, `source=eaipchina.cn`, `{{PD-China}}`. Template text: "…in China because its term of copyright has expired." |

## Verdicts: `field` key

| # | Fact (claimed) | Verdict | Evidence (re-opened 2026-11-13) |
|---|---|---|---|
| F1 | SHA = 虹桥机场 (SAA code list) | confirmed | `avinex.com/cn/js/Avinex/flight/oldFlight.js`: `{ Code: 'SHA', Name: '虹桥机场' }`. |
| F2 | OurAirports 31.198104, 121.33426; en-wiki point ~200 m east (secondary) | confirmed | OA row re-fetched. en-wiki raw `{{coord\|31\|11\|53\|N\|121\|20\|11\|E…}}` is 202.6 m at 91.5° from OA, and 24.8 m from the OSM centre of 18L/36R. |
| F3 | Movements 2025 282,692 (rank 11, +2.7 %) | confirmed | CAAC ranking xlsx (fetched over HTTP; HTTPS reset): `('上海/虹桥', 8, 50151025, 47944067, 4.6, 11, 445265.539, 427652.279, 4.1, 11, 282692, 275288, 2.7)`. |
| F4 | Movements 2024 275,288 (rank 11, +3.2 %) | confirmed | 2024 xlsx row `… 11, 275288, 266813, 3.2`. |
| F5 | Movements 2023 266,813 (rank 11, +117.5 %) | confirmed | 2023 xlsx row `… 11, 266813, 122668, 117.5`. |
| F6 | Passengers 42,492,745 / 47,944,067 / 50,151,025 | confirmed | Same three rows. |
| F7 | Cargo 363,218.687 / 427,652.279 / 445,265.539 t | confirmed | Same three rows. |
| F8 | 2025 international 6,978 (2.47 %), HMT 10,905 (3.86 %); passengers 1,290,845 + 2,111,683 = 6.78 % | confirmed | Hub-by-route xlsx row `(… 282692, 275714, 10905, 6978)`; percentages recomputed. |
| F9 | SIAC 2025: mainland 263,315, international 6,747, HMT 10,787, GA residual 1,843 (contradicts CAAC split) | confirmed | SIAC 2025 annual report (pdf.dfcfw.com, 187 pp), lines ~520-524 and the GA note verbatim. The contradiction with F8 is real. |
| F10 | Jan-Sep 2026 213,867 / 273 d = 783.4/day; Sep 23,770 = 792.3/day | confirmed | All 9 monthly briefs re-downloaded. Hongqiao totals 24,074; 22,555; 24,683; 23,688; 23,622; 22,715; 24,530; 24,230; 23,770 → sum 213,867. Sep outside-mainland 1,470/23,770 = 6.2 %. |
| F11 | Winter 2026/27 plan 802/day; 9 domestic routes with ≥ 12 daily departures (secondary) | confirmed | Sina 2026-10-24 (author 上观新闻): "日均计划执行航班2511架次…虹桥机场802架次"; "国内高频快线(每天出港12架次及以上)达到9条". |
| F12 | Design capacity 40 M passengers / 1 Mt / 300,000 movements | confirmed | shanghai.gov.cn press conference page, verbatim. |
| F13 | Declared capacity 43/h; coordination 06:00-02:00 (2011) | confirmed | CAAC notice "关于公布航班时刻协调机场容量标准的通知" (dated 二〇一一, posted 2016): "上海虹桥机场43架次" and "06:00 至次日02:00". It may be outdated, as `field` says. |
| F14 | Declared capacity 48 → 50/h (2023) | not_confirmed | No primary source found (a web search found none). Label `unverified` is honest. |
| F15 | Peak hour 59 (secondary) | confirmed | caacnews 2021-10-09 article (read in memory, not saved): "航班小时高峰达59架次". |
| F16 | No scheduled flights 00-06 since winter 2010/11; delays and diversions allowed; trip guide "0001-0600" curfew | confirmed (secondary) | Sina 2010-06-26 quotes verbatim. The 2010 article reports a *planned* change (title "拟", "有望"); its implementation is shown by shhqcbd 2012 "继续实施零时至6时不安排计划航班". Universal Weather blog: "Runway curfew from 0001 to 0600 local". |
| F17 | Runway 2 (18R/36L) 3,300 × 60 m, opened 11 Mar 2010 | confirmed | SAA news 19498 (2010-03-16): "1条长3300米、宽60米的平行跑道" and "3月11日新启用的第2跑道". |
| F18 | Spacing 365 m (1993 plan 1,700 m) | confirmed | CAAC 2010-03-16: "将1993规划的1700米间距的远距离跑道改为国内首个365米间距的近距离跑道". |
| F19 | Runway 1 3,400 m, original; east runway overhauled Jun-Nov 2011 (secondary) | confirmed | en-wiki "It only had one {{Cvt\|3400\|m\|ftin}} runway at the time". The overhaul ("2011年6月15日…11月16日完工") is in **zh**-wiki, not the cited en-wiki URL. |
| F20 | Mode "东落西起" (secondary) | confirmed | caacnews 2021 verbatim; consistent with AIP AD 2.20 2.1.1. |
| F21 | End-around taxiways S 1,620 m, N 1,603 m, 23 m | confirmed | caacnews 2021 verbatim. |
| F22 | T2 opened 16 Mar 2010; 362,600 m²; 80 counters; 47 lanes | confirmed | SAA 19498 and CAAC 2010 verbatim. |
| F23 | T2 bridges: CAAC 43 vs Shanghai government 45 (contradicted) | confirmed | Both quotes verbatim. SAA 19498 also says "43座登机桥". |
| F24 | T1 renovation from 20 Dec 2014; 8万 → 13万 m²; 10 M passengers; full reopening 15 Oct 2018 (9C at D; international/HMT at A/B) | confirmed | SAA 19191 (2014-12-20), 19196 (2014-10-30) and 18946 (2018-10-15), all verbatim. The JSON row cites only 18946, which supports only the 2018 part. |
| F25 | Airlines by terminal: T1 15, T2 14 (undated page) | confirmed | Parsed `#company3` and `#company4` of `avinex.com/airlines/index.html`; same codes and islands. |
| F26 | Gates: T1 T01-T15 international/HMT, T16-T27 domestic, bus gates T03-T08/T16-T19/T22-T25; T2 21-75, bus gates 41-45/51-55; bridge gates 13 and 45 inferred | confirmed | Both SAA JPGs re-downloaded and viewed. The bridge-gate counts are inferences, as the text says. |
| F27 | 54 contact stands ≈ 34 % (caacnews 2023); matches the AIP's 54 VDGS stands of 161 | confirmed (numbers); match is inference | caacnews 2023-08-18: "只有54个廊桥机位", "约 为 34%", "4组组合机位…2个C类机位组合成1个E类机位". See A16: 161 includes overlays. |
| F28 | Control tower at OSM node 3342630333 31.196674, 121.341534; agrees with AIP "Control TWR 111/520, 47 m" (status unverified) | confirmed (under-labelled) | OSM API node re-read. The AIP row exists and computes 7 m from the node (see A20). `secondary` would be the fair label. This row is correct and A20 is not. |
| F29 | Business-aviation base opened 26 Mar 2010: 3,100 m² FBO, 4,500 m² hangar, 3 stands, 6,000/yr, SAA + Hawker Pacific JV | confirmed | SAA 19492 verbatim. OSM way 469610770 "虹桥公务机楼" centroid 31.18877, 121.34207. |
| F30 | China Eastern Technics Hongqiao base and hangar (OSM) | confirmed | OSM ways 1576040006 and 327613444 at 31.1845, 121.3276. |
| F31 | 2025 visual approaches, point merge; 91.7 % on-time | confirmed | SIAC 2025 annual report lines ~437-443. |
| F32 | No hourly profile; SAA flight board behind WAF 403 | not_confirmed | Not re-tested (absence claim, no source to open). |

## Redistribution conclusion (re-checked)

* eaipchina.cn publishes no licence, terms or copyright grant on any page or script reachable without login.
  * The registration code has no terms step.
  * A "trial phase, verify before use" banner exists.
  * An "AIP China" purchase invoice exists (USD, payable to the AIS Center, ATMB CAAC).
* The mirror and Commons copies carry no CAAC permission. The Commons {{PD-China}} tag is inapplicable to a
  2026-03-15 chart.
* CAAC statistics pages, SIAC filings, SAA pages and Sina carry no reuse licence. caacnews explicitly forbids
  download ("未经协议授权，禁止下载使用", verbatim on the 2021 page).
* The aip and field rule (cite facts with source and date; keep files, charts and transcribed tables local) is
  supported by what I re-read. Whether an AIP is an "administrative document" under PRC Copyright Law art. 5 was
  **not checked** by either key or by me.

## Re-downloads used (session scratchpad, not committed)

All under `/tmp/claude-0/-home-user-Calc/cb074753-b403-5e5e-9177-97bfce1ffb76/scratchpad/dl/`:

* `eaip/` (shell, bundle, 25 chunks, API answers, `sa/zsss_en.pdf`, `notam/2026-11.zip`)
* `mirror/` (AD 2 PDF, 2A-1, 2P-1)
* `opennav/1A.pdf`
* `oa/` (OurAirports)
* `osm/` (API map tile, Overpass parking positions)
* `caac/` (4 xlsx)
* `siac/` (annual report + 9 briefs)
* `saa/` (pages + 2 gate maps)
* `misc/` (shanghai.gov.cn, CAAC 2010/2011, Sina 2010/2026)
* `wiki/` (en/zh wikitext, Commons)
* `gh/repo/README.md`

caacnews pages were read in memory only.
