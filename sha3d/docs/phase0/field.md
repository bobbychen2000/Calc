# Phase 0: field layout and operations at SHA / ZSSS, from sources other than the AIP (KEY = field)

Research note for SHA Live 3D. Checked on **2026-11-13**. Times are Beijing time (UTC+8) unless marked UTC.

**Where things are**
- Downloads: `sha3d/refs/cache/field/<source>/`, one folder per source. Each folder has a `SOURCES.json` with:
  - the URL and the date checked;
  - the licence, quoted;
  - whether we may redistribute;
  - the size and sha256 of each file.
- `refs/cache/` is gitignored. Nothing in this key may be redistributed except the Chinese Wikipedia text (CC BY-SA 4.0).
- Scripts: `sha3d/tools/field/`. Each runs with `python3 -I` from `sha3d/`, outside the download folders, and uses only the standard library (PIL for image tiles).
  - `xlsx_rows.py`: reads the CAAC spreadsheets.
  - `siac_briefs.py`: parses the monthly briefs.
  - `summarise_traffic.py`: writes `refs/cache/field/derived_field/traffic_summary.json`.
  - `saa_airlines.py`: parses the airline-by-terminal directory.
  - `osm_features.py`: lists the airport features in the OSM extract.
  - `html_text.py`, `img_tiles.py`: helpers.
  - `write_sources.py`: writes every `SOURCES.json`.
- I did not touch `sfo3d/`, `pc12/` or `hwd3d/`.
- No Google, Baidu or Amap imagery was used, and no geometry was produced, so GCJ-02 does not arise. The OSM positions quoted below are WGS-84, from the cache that the `geo` key downloaded.

**Legend**
- **[obs]**: read or measured by me in the cited original, this session.
- **[inf]**: my inference from observations. The reasoning is given.
- Status uses the owner's scale:
  - **verified**: a primary or official source was read.
  - **secondary**: only a secondary source, such as Wikipedia, OSM, news or a trade blog.
  - **unverified**: not checked against an original.
  - **contradicted**: the sources disagree. Both are given.
- "AIP cross-check" means I compared against the `aip` key's derived files in `refs/cache/aip/derived_aip_zsss/`. I did not re-read the AIP myself; that is the `aip` key's job.

---

## 0. Summary for the lead

### 0.1 The ADS-B denominator
These figures are the denominator for the ADS-B "fraction of movements seen" measurement. One movement is one take-off or one landing.

| Period | Movements/day | Source (status) |
|---|---|---|
| 2023 | **731.0** | 266,813 / 365, CAAC bulletin (verified) |
| 2024 | **752.2** | 275,288 / 366 (leap year), CAAC (verified) |
| 2025 | **774.5** | 282,692 / 365, CAAC (verified) |
| Jan–Sep 2026 | **783.4** (monthly 757–806) | 213,867 / 273, SIAC monthly briefs (verified) |
| Sep 2026, latest month | **792.3** | 23,770 / 30, SIAC (verified) |
| Winter 2026/27 schedule (25 Oct 2026 – 27 Mar 2027) | **802 planned** | Shanghai Airport Authority via 上观新闻 (secondary) |

What a typical November 2026 day should hold [inf]:
- About **780–800 movements**: roughly 390–400 arrivals and 390–400 departures.
- About **6.2 %** to or from outside the mainland: roughly 19 international and 30 Hong Kong / Macau / Taiwan movements.
- About **5.5 non-commercial GA movements**. The SIAC "other" residual averaged 5.5 per day in Jan–Sep 2026.

Counting rule [inf]: one take-off or one landing is one movement. This is consistent with:
- the ICAO usage;
- the SIAC tables, where the route classes plus GA add up to the total;
- the caacnews figure of about 535 bridge "客班" per day at a 72 % bridge rate, which implies about 740 movements per day. That matches mid-2023.

I found no CAAC text that defines the counting rule.

Time-of-day window:
- **No scheduled flights 00:00–06:00 local (16:00–22:00 UTC)**. This has been policy since the winter 2010/11 season. Delayed and diverted flights may still operate.
- Coordinated slot window **06:00–02:00** (CAAC, 2011).
- A trip-support guide gives a **runway curfew 00:01–06:00** (secondary).
- Our coverage clock should therefore run over 06:00–24:00 local. Late delays spill past midnight.

Hourly profile:
- **No published hourly profile was found.** Known points:
  - peak hour up to **59** movements (2021, caacnews);
  - declared capacity **43/h** (CAAC, 2011);
  - a reported 2023 rise to 48 → **50/h**, which I could not trace to a primary source (unverified).
- The mean over the 18 operating hours is about **44/h** [inf].
- The SAA public flight board has a JSON endpoint, but it answered scripted requests with a WAF 403. I did not try to get around it (see §8).

### 0.2 Layout in one paragraph
- **Runways.** Two close-spaced parallel runways, **365 m apart**: east **18L/36R** (3,400 m, the original) and west **18R/36L** (3,300 × 60 m, opened **11 March 2010**). Normal mode is **"东落西起"**: land on the east runway, take off from the west one.
- **Terminals.** **T1** is east of the runways: renovated 2014–2018 and fully reopened **15 Oct 2018**. **T2** is west of the runways: opened **16 March 2010**, 362,600 m², attached to the Hongqiao rail and metro hub.
- **Contact stands.** **54** contact (bridge) stands, about 34 % of all stands. By my count from the SAA gate maps and the AIP cross-check, that is 13 at T1 and 41 at T2.
- **T1 gates.**
  - International, Hong Kong, Macau and Taiwan: **T01–T15**.
  - Domestic: **T16–T27**. Spring Airlines, Hebei Airlines and XiamenAir use T1.
  - Bus gates: T03–T08, T16–T19 and T22–T25.
- **T2 gates.** Domestic gates **21–75**. Bus gates: 41–45 and 51–55.
- **Gate and stand numbers** [inf]: T1 gate Txx appears to use stand 1xx, and T2 gate nn appears to use stand 2nn.
- **Other buildings**:
  - **business-aviation base** (opened 26 March 2010), south of T1 on the east side;
  - **China Eastern Technics Hongqiao maintenance base** and hangar, south-west, south of T2 (OSM);
  - **control tower** about 0.5 km east-south-east of the centre of 18L/36R, near T1 (OSM and AIP cross-check).

### 0.3 Check of the working hypothesis
- **SHA = ZSSS = Hongqiao: no contradiction found.**
  - The Shanghai Airport Authority's own flight-board code list says `{ Code: 'SHA', Name: '虹桥机场' }` [obs, primary].
  - The CAAC eAIP situational-awareness listing (`aip` key) says `airportCode ZSSS, SHANGHAI/Hongqiao`.
  - CAAC statistics call it 上海/虹桥.
- **OurAirports ARP 31.198104 N, 121.33426 E**: confirmed as the value in the cached OurAirports `airports.csv` [obs]. This is a secondary source; the AIP ARP is for the `aip` key.
  - The English Wikipedia infobox gives 31°11′53″N 121°20′11″E, which is 31.19806 N, 121.33639 E.
  - That point is about **200 m east** of the OurAirports point. The OurAirports point lies between the two runways; the Wikipedia point is near the east runway [inf].
  - Both are secondary, so this is not a contradiction of the hypothesis. It is a reason to use the AIP ARP.

---

## 1. Traffic statistics (CAAC "民航机场生产统计公报" and SIAC)

### 1.1 CAAC annual bulletins [obs]
- **Source.** The CAAC statistics listing `https://www.caac.gov.cn/XXGK/XXGK/TJSJ/index_1216.html` links the 2025, 2024 and 2023 bulletins. Each bulletin page carries a PDF and attachment 1, 全国民用运输机场吞吐量排名 (an xlsx).
- **2025 attachment 2.** The 2025 bulletin adds attachment 2, 全国枢纽机场分航线吞吐量, which splits traffic by route class.
- **Mainland totals.** The bulletin's row "合计" equals the bulletin's 飞机起降 (all aircraft movements), not 运输起降 (transport movements). For 2025 that is 12,447,526, the "1244.8 万架次".
  - So the per-airport 起降架次 are **all movements, including GA** [inf, from the totals matching].

| Year | Passengers (rank) | YoY | Cargo t (rank) | Movements (rank) | YoY | Per day |
|---|---|---|---|---|---|---|
| 2023 | 42,492,745 (7) | +188.8 % | 363,218.687 (10) | **266,813** (11) | +117.5 % (2022: 122,668) | 731.0 |
| 2024 | 47,944,067 (9) | +12.8 % | 427,652.279 (10) | **275,288** (11) | +3.2 % | 752.2 |
| 2025 | 50,151,025 (8) | +4.6 % | 445,265.539 (11) | **282,692** (11) | +2.7 % | 774.5 |

**2025 by route class** (CAAC attachment 2, row 上海/虹桥):
- Movements:
  - total 282,692;
  - domestic, including Hong Kong / Macau / Taiwan (HMT): 275,714, of which HMT 10,905;
  - international: 6,978.
  - **International 2.47 %, HMT 3.86 %, together 6.33 %.**
- Passengers:
  - total 50,151,025;
  - international 1,290,845;
  - HMT 2,111,683.
  - **International and HMT together: 6.78 %.**

### 1.2 SIAC (上海国际机场股份有限公司, 600009.SH) reports [obs]
SIAC has operated SHA since the 2022–24 restructuring; its annual report says that 虹桥机场公司 is a 100 % subsidiary. Its annual reports and monthly 运输生产情况简报 split SHA traffic into:
- 境内 (mainland);
- 境外 (outside the mainland), divided into 国际 (international) and 港澳台 (Hong Kong, Macau, Taiwan);
- a residual. The residual is explained in each table's note: "因存在其他形式的飞行（不以营利为目的的通用航空飞行），所以部分项目分项数字之和与总计数存在差异" (other, non-commercial GA flights cause the gap).

| Year | Total | Mainland | International | HMT | GA residual | Outside-mainland share |
|---|---|---|---|---|---|---|
| 2023 | 266,813 | 252,413 | 4,622 | 7,790 | 1,988 | 4.65 % (international routes resumed 26 Mar 2023) |
| 2024 | 275,288 | 256,041 | 6,677 | 10,591 | 1,979 | 6.27 % |
| 2025 | 282,692 | 263,315 | 6,747 | 10,787 | 1,843 | 6.20 % |

**Monthly 2026** (`siac_briefs.py`; Hongqiao block of each brief):

| Month | Movements | /day | YoY | International | HMT | GA residual |
|---|---|---|---|---|---|---|
| 2025-12 | 23,510 | 758.4 | −0.37 % | 557 | 936 | 110 |
| 2026-01 | 24,074 | 776.6 | +0.56 % | 592 | 938 | 179 |
| 2026-02 | 22,555 | 805.5 | +3.09 % | 523 | 850 | 120 |
| 2026-03 | 24,683 | 796.2 | +2.39 % | 608 | 955 | 157 |
| 2026-04 | 23,688 | 789.6 | +2.91 % | 578 | 922 | 151 |
| 2026-05 | 23,622 | 762.0 | −1.22 % | 577 | 942 | 170 |
| 2026-06 | 22,715 | 757.2 | −0.40 % | 563 | 883 | 172 |
| 2026-07 | 24,530 | 791.3 | +2.93 % | 581 | 909 | 220 |
| 2026-08 | 24,230 | 781.6 | −0.86 % | 534 | 926 | 185 |
| 2026-09 | 23,770 | 792.3 | +2.19 % | 566 | 904 | 159 |

- Jan–Sep 2026: **213,867 movements in 273 days = 783.4/day**. The GA residual is 5.5/day.
- The October brief is due around 15 Nov 2026 and was not yet published when checked.

**CAAC and SIAC disagree slightly on route class for 2025** (contradicted, minor):
- International: CAAC 6,978, SIAC 6,747.
- HMT: CAAC 10,905, SIAC 10,787.
- The totals agree (282,692). The gap is probably classification: CAAC has no GA column, and mixed-route flights may be classed differently [inf]. For shares, use either source and say which.

### 1.3 Typical daily movements, capacity and hourly profile
- **Winter 2026/27 schedule**: 日均计划执行航班 … 虹桥机场 **802** 架次 (planned daily average), per Shanghai Airport Authority via 上观新闻, 2026-10-24 (secondary).
  - The same release: 国内高频快线(每天出港12架次及以上)达到9条, i.e. 9 domestic shuttle routes with 12 or more daily departures each.
- **Design capacity.** The expansion was designed for **40 M passengers, 1 Mt cargo and 300,000 movements a year** (Shanghai government, 2010; verified).
  - SIAC 2025 repeats "设计满足年旅客吞吐量 4,000 万人次".
  - 2025 had 50.15 M passengers, so SHA runs **above its passenger design capacity**. Movements are at 94 % of the 300k design figure [inf].
- **Declared hourly capacity.** CAAC 局发明电〔2011〕3401号: "上海虹桥机场43架次", coordination window "06:00 至次日02:00" (verified).
  - A later rise to 48 and then **50/h (2023)** appears only in a search summary of secondary reports. **Unverified.**
- **Actual peak.** "航班小时高峰达59架次" (caacnews 2021-10-09; secondary, official-sector press).
- **Hourly profile.** None published that I could find. Shape [inf]:
  - zero scheduled 00–06;
  - an early bank of departures from 06:00, because of overnighting aircraft;
  - a dense day of business "shuttle" flights;
  - late arrivals before 24:00.
  - caacnews 2023 notes "早出晚归" (early out, late back) and that each bridge sees a group of flights "基本每隔2个小时" (roughly every 2 hours).
  - Mean over 18 h ≈ 802 / 18 ≈ **44.6/h**.

---

## 2. Terminals T1 and T2

### 2.1 History
- **T2** opened at 00:00 on **16 March 2010** [verified, SAA and CAAC].
  - Size: 36.26 万 m², i.e. 362,600 m².
  - 80 check-in counters and 47 security lanes.
  - **43** bridges per CAAC, or **45** per the Shanghai government. See §3; the two are contradicted.
  - The first departure, MU5101, took off "从3月11日新启用的第2跑道" (from runway 2, newly opened on 11 March).
- **Opening split (2010).** "除春秋航空公司及往返日本、韩国的国际包机航班仍在1号航站楼运营外，其余航空公司全部迁至2号航站楼运营" (all airlines moved to T2 except Spring Airlines and the Japan/Korea charters, which stayed at T1). That is ">90 %" of flights at T2 [verified, Shanghai government press conference 2010-03-11].
- **T1 renovation.**
  - Announced 2014-10-30.
  - Spring Airlines moved from building A to building B on 6 Nov 2014.
  - Construction fully started **20 Dec 2014** [verified, SAA].
  - Plan: building A first, then building B.
  - T1 area 8万 m² → 13万 m² (80,000 → 130,000 m²); T1 design capacity **10 M passengers a year** [verified, SAA 2014].
  - T1 role: "国际航班备降和为两国（日本、韩国包机）三地（港、澳、台）航班及国内航空公司航班运行提供保障" (international diversions, Japan/Korea and Hong Kong/Macau/Taiwan flights, plus domestic airlines).
- **Building A** reopened **26 March 2017** (secondary, en/zh Wikipedia). One sentence of the zh article says "3月16日", so the date is slightly uncertain.
- **T1 fully reopened 15 Oct 2018** [verified, SAA]:
  - Spring Airlines moved from the A island to the **D island** (domestic);
  - international and HMT flights use the **A and B islands**.
  - zh-Wikipedia gives 20.37万 m² including the transport centre (secondary).
- **Older history** (secondary):
  - T1 was built 1984 and extended 1988 and 1994 (zh-Wikipedia, citing The Paper 2014).
  - The original terminal and control tower opened in 1964 (en-Wikipedia).
- **International flights.** Suspended 25 Mar 2020 and resumed 26 Mar 2023 (secondary). SIAC's 2023 table shows 境外 from 2023 with no prior-year figure [obs].

### 2.2 Which airlines use which terminal (SAA airline directory, undated live page) [obs, verified]

| Terminal | Airline (check-in island) |
|---|---|
| **SHA T1** (15 airlines) | MU China Eastern (B), FM Shanghai Airlines (B), CA Air China (A), 9C Spring (D), NS Hebei (D), MF XiamenAir (D), CI China Airlines (B), NX Air Macau (A), KE Korean Air (A), CX Cathay Pacific (A), BR EVA Air (B), HX Hong Kong Airlines (A), OZ Asiana (B), NH ANA (B), JL JAL (A) |
| **SHA T2** (14 airlines) | MU (B, C, D, F), FM (B, C, D, F), CZ China Southern (D), CA (A), KN China United (B), HO Juneyao (E), SC Shandong (A), HU Hainan (A), EU Chengdu (B), ZH Shenzhen (A), GS Tianjin (A), TV Tibet (A), 8L Lucky (A), Y8 Suparna/金鹏 (A) |

Reading [inf]:
- At T1:
  - islands A and B are international and HMT;
  - island D is domestic, for 9C, NS and MF;
  - MU, FM and CA appear there only for their international and HMT flights.
- T2 is all-domestic.
- The page is undated and may contain stale rows, such as KN and Y8. Cross-check against the `fleet` key's route data.

---

## 3. Gates, contact stands and remote stands

### 3.1 Primary statements
- **Contact stands and bridge rate** (caacnews 2023-08-18; official-sector press, secondary):
  - "虹桥机场廊桥机位比例占机场总机位数比例较低、约为34%" (contact stands are about 34 % of all stands);
  - "在只有54个廊桥机位的条件下，每天保障约535个客班靠桥…日均廊桥机位周转航班已达10架次" (only 54 contact stands, about 535 bridge flights a day, about 10 per bridge stand);
  - "在夜间不安排航班计划的情况下" (no flights scheduled at night);
  - total bridge rate about **72 %**, then 76.5 % in the week of 17–23 Jul 2023;
  - "T2指廊端8个廊桥机位" (8 contact stands at the T2 pier ends);
  - "启用了4组组合机位，组合机位可以将2个C类机位组合成1个E类机位" (4 combined stands, each making one code-E stand from two code-C);
  - "改造15个B类机位结构，增加了小C类公务机专用停机位" (15 code-B stands rebuilt as small code-C stands for business jets).
- **T2 bridges, 2010: 43 or 45** (contradicted):
  - CAAC 2010-03-16: "47条安检通道和43座登机桥，且近机位比例达到70%以上" (43 bridges, over 70 % contact-stand ratio).
  - Shanghai government 2010-03-11: "2号航站楼设有45座登机桥，是1号航站楼的3倍，近机位比例超过70%，其中8个机位可以同时停靠3种机型组合的混合式桥位" (45 bridges, three times T1, 8 multi-aircraft-ramp-system stands).
  - Possible reconciliation [inf]: 45 bridge **gates**, 43 **bridges**, because some MARS stands share bridges.

### 3.2 Gate numbering from the SAA terminal flow diagrams (2023) [obs; counts inf]
The diagrams are SAA schematics, not to scale. Use them as **reference only**.

**T1** (`sha_t1_dep_2f.jpg`):
- Legend: "T01–T15 国际、港澳台登机口" (international and HMT gates) and "T16–T27 国内登机口" (domestic gates).
- Labelled bus-gate ranges: "远机位 T03-T08", "远机位 T16-T19" and "远机位 T22-T25".
- By elimination, **13 bridge gates** [inf]:
  - international: T01, T02 and T09–T15;
  - domestic: T20, T21, T26 and T27.

**T2** (`sha_t2_dep_m2.jpg`):
- Legend: "21–75 国内出口" (domestic gates 21–75).
- Labelled bus-gate ranges: "远机位 41-45" and "远机位 51-55".
- By elimination, **45 bridge gates** [inf]: 21–40, 46–50 and 56–75.
- Layout [inf]:
  - north pier: gates 21–40;
  - central frontage: 46–50;
  - south pier: 56–75.
  - zh-Wikipedia captions the south pier "南指廊（56-75登机口）" (secondary).
- T2 check-in islands are A–H on 3F. Departures airside is on M2.

### 3.3 AIP cross-check (from the `aip` key's `stands.json`, not re-read by me)
- The AIP list has **161** stands. **54** have VDGS:
  - **T1: 13** (101, 102, 109–115, 120, 121, 126, 127);
  - **T2: 41** (221–238, 240, 246, 248, 250, 256, 257, 259–275).
- **54 VDGS stands = caacnews' 54 contact stands.** 54/161 = 33.5 %, which matches "约为34%".
- T1 bridge gates (T01, T02, T09–T15, T20, T21, T26, T27) map one-to-one onto stands 101, 102, 109–115, 120, 121, 126 and 127.
- **Inferred rule: gate Txx → stand 1xx (T1), gate nn → stand 2nn (T2).**
- T2 gates 39, 47, 49 and 58 have no stand 239, 247, 249 or 258 in the AIP list. They are probably second gates on shared or MARS stands [inf].
- Remote stands ≈ 161 − 54 = **107** [inf]. Stands 3xx–6xx in the AIP list are remote or cargo stands; their roles are for the `aip` key.

---

## 4. Control tower(s)
- **Location** [secondary, OSM; AIP cross-check]:
  - OSM node 3342630333 is `man_made=tower, tower:type=aircraft_control` at **31.196674 N, 121.341534 E** (WGS-84), on the T1 (east) side.
  - The `aip` key's AD 2.10 table lists "Control TWR | 111/520 | 47 | LGT", i.e. MAG bearing 111° and 520 m from the centre of RWY 18L/36R, height or elevation 47 m.
  - From the OurAirports threshold midpoint of 18L/36R, the OSM node lies 543 m away on a true bearing of about 104°. That is about 110° magnetic with roughly 6° W variation, so **the AIP obstacle and the OSM node are the same tower** [inf].
- **ATC positions.** Two tower positions, "TWR(E) 118.1 (124.3)" and "TWR(W) 118.65 (118.25)", H24 (AIP cross-check).
  - caacnews 2021 quotes "华东空管虹桥塔台" (the East China ATMB Hongqiao Tower).
  - **Whether there are two cab buildings or one is not established**: unverified. The OSM extract has only one aircraft-control tower. It also has two `man_made=tower` ways next to the 东航之家 complex (31.1876 N, 121.3261 E), which are probably not ATC [inf].
- **Year and height of the current building: unverified.**
  - en-Wikipedia (secondary): "In 1964, the original Terminal 1 and the control tower opened" and "its former control tower was renovated sometime after Pudong Airport opened".
  - No primary source found.

## 5. Runways and their history

| Item | Value | Status |
|---|---|---|
| Runway 1 (east, 18L/36R) | 3,400 m. The original runway; the only one until 2010 | secondary (Wikipedia). Length also in OurAirports. Dimensions are for the `aip` key |
| Runway 2 (west, 18R/36L) | **3,300 m × 60 m**, opened **2010-03-11** | verified (SAA 2010: "1条长3300米、宽60米的平行跑道"; "3月11日新启用的第2跑道") |
| Spacing | **365 m**. China's first close-spaced parallels; the 1993 plan had 1,700 m | verified (SAA, CAAC, Shanghai government: "将1993年规划的1700米间距的远距离跑道改为国内首个365米间距的近距离跑道") |
| Taxiways added in 2010 | "1条长3300米、宽60米的平行跑道和3条平行滑行道" (3 parallel taxiways) | verified (Shanghai government 2010) |
| Normal runway use | **"东落西起"**: east 18L/36R landings, west 18R/36L take-offs | secondary (caacnews 2021). 2012 Shanghai transport commission: "西跑道用于起飞" |
| East runway overhaul | 15 Jun – 16 Nov 2011, pavement and lighting | secondary (zh-Wikipedia citing 东方早报) |
| End-around taxiways | South **1,620 m**, north **1,603 m**, both **23 m** wide. For wingspan ≤ 36 m. South opened **2021-10-09**; north planned early Dec 2021. About 60 % of flights expected to use them | secondary (caacnews 2021) |
| Recent | 2025: "虹桥机场成功实施目视进近运行模式，结合近距平行跑道优化、点融合飞行程序" (visual approaches, close-parallel optimisation, point-merge) | verified (SIAC annual report 2025) |

## 6. Night operations
- **2010 decision.** From the winter 2010/11 season (28 Oct 2010), no scheduled flights 00:00–06:00 [secondary, Sina 2010-06-26]:
  - "对虹桥机场不再安排夜间零时至6时的计划航班" (no scheduled flights from midnight to 06:00);
  - "零时后延误航班、备降航班等起降不受限制" (delayed and diverted flights after midnight are not restricted).
- **Reaffirmed** in 2012: "继续实施零时至6时不安排计划航班" (Shanghai transport commission's reply, reposted on the Hongqiao CBD government site; secondary). Again in 2023: "夜间不安排航班计划" (caacnews; secondary).
- **Trip-support guide** (Universal Weather, 2026-02-20; secondary):
  - "Runway curfew from 0001 to 0600 local";
  - "No GA takeoffs between 0700 and 0900 local";
  - "CIQ operating hours from 0800 to 2200 local".
- **Aerodrome hours.** Tower H24 (AIP cross-check). So this is a **scheduling restriction, not an aerodrome closure** [inf].

## 7. Cargo, maintenance and business aviation
- **Cargo.** 445,265.5 t in 2025 (CAAC). About 8.7 % of it is international or HMT by tonnage (SIAC: 2.19 + 1.67 万 t out of 44.53 万 t).
  - The 2010 expansion included a 货运站 (cargo station) (SAA). **Its location is not established.**
  - SHA is a belly-cargo airport [inf]. The SAA flight board does show a cargo-flight tab (货班).
- **China Eastern Technics (东航技术) Hongqiao base** (secondary):
  - OSM labels "东方航空技术有限公司虹桥维修基地" at 31.18447 N, 121.32763 E and a hangar way "中国东方航空公司机库" at 31.18424 N, 121.32765 E. That is the west side, south of T2, next to "东航基地西区" and the 东航之家 headquarters complex.
  - News (wenhui 2020, caacnews 2022) refers to a Hongqiao base with a heavy-check (定检) department.
  - Note that China Eastern's new "Asia's largest" wide-body hangar (opened 2026-09) is at **Lingang/Pudong, not SHA** (secondary).
- **Other hangars** (OSM, unnamed): 31.2050 N, 121.3461 E; 31.2048 N, 121.3446 E; 31.2105 N, 121.3397 E. These are north-east of the airport. OSM also has **3 helipads** at about 31.210 N, 121.339 E, and the **Juneyao Air building** at 31.1895 N, 121.3470 E.
- **Business-aviation base** [verified, SAA 2010-03-26]:
  - opened **26 March 2010**;
  - FBO terminal 3,100 m²;
  - hangar 4,500 m², holding 4–5 mid-size business jets;
  - annex about 2,000 m²;
  - 3 dedicated stands;
  - capacity 6,000 business-jet movements a year;
  - plus "60个以上公务机停放机位" (more than 60 business-jet parking positions available) for the Expo;
  - operated by the JV "上海霍克太平洋公务航空地面服务有限公司" (SAA and Hawker Pacific).
- **Business-aviation terminal position.** OSM "虹桥公务机楼" (business-aviation terminal) is at **31.18877 N, 121.34207 E**, on the east side south of T1 (secondary). OSM also has "虹桥东区 VVIP" at 31.19386 N, 121.34150 E.
- **Current FBO operator: unverified.** Jet Aviation's 2022 APAC network PDF lists a Hongqiao FBO at "No. 99 Yingbin Road #7" (secondary; Jet Aviation acquired Hawker Pacific in 2018, also unverified). Universal Aviation also advertises handling at ZSSS.

## 8. What I could not get, and why
- **shanghaiairport.com / shairport.com time out**, but the same Shanghai Airport Authority site answers at **www.avinex.com**: same ICP 沪ICP备05007027号, same content. Connections reset often; retries work.
- **SAA flight-board JSON** (`/AvinexApi/OldFlightHandler.aspx`, action GetData) would give a scheduled day's hourly profile, but a scripted POST returned **HTTP 403 from the site's WAF (jiasule)**. I did not try to get around it and kept no data.
- **SSE query API** needs a Referer header and answered "系统繁忙". I used the Eastmoney PDF mirror of the same filings instead. The documents carry the SSE announcement header (证券代码 600009, 公告编号). The sha256 is in `SOURCES.json`.
- **caacnews.com.cn terms** say "未经协议授权，禁止下载使用" (no download or use without an agreement). I read the two articles, recorded the hash of what was fetched and short quotes, and **deleted the local copies**.
- **Control-tower height and year, and the current cargo-terminal location**: no primary source found.
- **zh-Wikipedia revision id**: the API returned 429 (rate limit). The retrieval time is recorded instead.

---

## 9. Facts table

Date checked for every row: **2026-11-13**.

| # | Topic | Value | Source URL | Quote (short, verbatim) | Status |
|---|---|---|---|---|---|
| 1 | SHA identity | SHA = 虹桥机场 in SAA's own code list | https://www.avinex.com/cn/js/Avinex/flight/oldFlight.js | "{ Code: 'SHA', Name: '虹桥机场' }" | verified |
| 2 | OurAirports ARP | 31.198104, 121.33426 | https://davidmegginson.github.io/ourairports-data/airports.csv (`ourairports_runways` cache) | "ZSSS","large_airport","Shanghai Hongqiao International Airport",31.198104,121.33426 | secondary |
| 3 | Movements 2025 | 282,692 (rank 11), +2.7 % | https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/P020260226360830390937.xlsx | "上海/虹桥 \| 8 \| 50151025 … \| 11 \| 282692 \| 275288 \| 2.7" | verified |
| 4 | Movements 2024 | 275,288 (rank 11), +3.2 % | https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202503/P020250314353470214193.xlsx | "上海/虹桥 \| 9 \| 47944067 … \| 11 \| 275288 \| 266813 \| 3.2" | verified |
| 5 | Movements 2023 | 266,813 (rank 11), +117.5 % | https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202403/P020241227527614591507.xlsx | "上海/虹桥 \| 7 \| 42492745 … \| 11 \| 266813 \| 122668 \| 117.5" | verified |
| 6 | Passengers 2023/24/25 | 42,492,745 / 47,944,067 / 50,151,025 | same three xlsx files | (rows above) | verified |
| 7 | Cargo 2023/24/25 | 363,218.687 / 427,652.279 / 445,265.539 t | same three xlsx files | (rows above) | verified |
| 8 | 2025 movements by route | Domestic incl. HMT 275,714 (HMT 10,905), international 6,978 → 6.33 % outside the mainland | https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/P020260226360830545167.xlsx | "上海/虹桥 \| 50151025 \| 48860180 \| 2111683 \| 1290845 \| … \| 282692 \| 275714 \| 10905 \| 6978" | verified |
| 9 | 2025 route split, SIAC | Mainland 263,315; international 6,747; HMT 10,787; GA residual 1,843 | https://pdf.dfcfw.com/pdf/H2_AN202604291821768752_1.pdf | "-国际航线 6,747 … -港澳台航线 10,787" | contradicted (vs #8: international 6,978, HMT 10,905; totals agree) |
| 10 | Monthly Sep 2026 | 23,770 movements; international 566, HMT 904 | https://pdf.dfcfw.com/pdf/H2_AN202610141830452855_1.pdf | "虹桥国际机场 … 总计 23,770 2.19" | verified |
| 11 | Jan–Sep 2026 | 213,867 in 273 days = 783.4/day | 9 SIAC briefs (`siac_monthly_briefs/SOURCES.json`) | (derived, `traffic_summary.json`) | verified (sum is inf) |
| 12 | Planned daily, winter 2026/27 | 802 movements/day | http://news.sina.com.cn/minsheng/2026-10-24/doc-iniwhxpu1437622.shtml | "日均计划执行航班2511架次…其中浦东机场1709架次、虹桥机场802架次" | secondary |
| 13 | Design capacity | 40 M passengers, 1 Mt cargo, 300,000 movements/yr | https://www.shanghai.gov.cn/nw9822/20200906/0001-9822_395090.html | "按满足年旅客吞吐量4000万人次、货邮吞吐量100万吨和飞机起降量30万架次设计建设" | verified |
| 14 | Declared hourly capacity (2011) | 43/h; coordination 06:00–02:00 | https://www.caac.gov.cn/XXGK/XXGK/ZFGW/201602/t20160224_29138.html | "上海虹桥机场43架次…其他机场协调时段均为06:00 至次日02:00" | verified (may be outdated) |
| 15 | Declared hourly capacity (2023) | 48 → 50/h | (search summary only; no primary found) | — | unverified |
| 16 | Peak hour observed | 59 movements | http://www.caacnews.com.cn/1/3/202110/t20211009_1331872.html | "航班小时高峰达59架次" | secondary |
| 17 | Night rule | No scheduled flights 00:00–06:00 since winter 2010/11; delays and diversions allowed | https://news.sina.cn/sa/2010-06-26/detail-ikmxzfmk0135400.d.html | "不再安排夜间零时至6时的计划航班…零时后延误航班、备降航班等起降不受限制" | secondary |
| 18 | Night rule, reaffirmed | 2012 | https://www.shhqcbd.gov.cn/yshj/csyx/sndt/3803.html | "继续实施零时至6时不安排计划航班、正常情况下西跑道仅用于起飞" | secondary |
| 19 | Curfew, trip-support | 00:01–06:00 runway curfew; no GA take-offs 07–09 | https://www.universalweather.com/blog/shanghai-china-2026-business-aviation-destination-guide/ | "Runway curfew from 0001 to 0600 local" | secondary |
| 20 | Runway 2 | 3,300 × 60 m, opened 11 Mar 2010 | https://www.avinex.com/xwg/info_itemid_19498.html | "1条长3300米、宽60米的平行跑道…从3月11日新启用的第2跑道缓缓起飞" | verified |
| 21 | Runway spacing | 365 m (1,700 m in the 1993 plan) | https://www.caac.gov.cn/PHONE/XWZX/MHYW/201003/t20100316_12580.html | "改为国内首个365米间距的近距离跑道" | verified |
| 22 | Runway use | Land east 18L/36R, take off west 18R/36L | http://www.caacnews.com.cn/1/3/202110/t20211009_1331872.html | "通常的主用模式是“东落西起”" | secondary |
| 23 | End-around taxiways | S 1,620 m, N 1,603 m, 23 m wide; S opened 2021-10-09 | same | "1620米长的南段绕滑和1603米长的北段绕滑，宽度均为23米" | secondary |
| 24 | Runway 1 | 3,400 m, the original runway | https://en.wikipedia.org/wiki/Shanghai_Hongqiao_International_Airport (`fleet/wikipedia_sha` cache) | "It only had one {{Cvt\|3400\|m\|ftin}} runway at the time" (wikitext) | secondary |
| 25 | T2 opening | 16 Mar 2010; 362,600 m² | https://www.avinex.com/xwg/info_itemid_19498.html | "新建1座36.26万平方米的2号航站楼" | verified |
| 26 | T2 bridges | 43 bridges vs 45 bridges | CAAC 2010 (#21 URL); Shanghai government (#13 URL) | "43座登机桥" / "2号航站楼设有45座登机桥" | contradicted |
| 27 | T1 renovation | Started 20 Dec 2014; T1 design 10 M passengers/yr | https://www.avinex.com/xwg/info_itemid_19191.html | "2014年12月20日…全面开工…年旅客吞吐量设计能力为1000万人次" | verified |
| 28 | T1 area | 8万 → 13万 m² | https://www.avinex.com/xwg/info_itemid_19196.html | "现有面积8万平方米，改造后将增至13万平方米" | verified |
| 29 | T1 building A reopening | 26 Mar 2017 | en/zh Wikipedia | "On 26 March 2017, Building A of Terminal 1 was fully renovated and reopened" | secondary |
| 30 | T1 full reopening | 15 Oct 2018; Spring Airlines at D island; international and HMT at A and B | https://www.avinex.com/xwg/info_itemid_18946.html | "春秋航空航班从1号航站楼A岛转至D岛运营，全部为国内航班；其它航空公司国际、港澳台航班在A岛、B岛运营" | verified |
| 31 | Airlines per terminal | T1: 15 airlines; T2: 14 airlines (§2.2) | https://www.avinex.com/airlines/index.html | tab "虹桥机场1号航站楼" … "中国春秋航空公司 … 值机柜台： D" | verified (page undated) |
| 32 | T1 gates | T01–T15 international/HMT, T16–T27 domestic; bus gates T03–T08, T16–T19, T22–T25 | https://www.avinex.com/uploadfiles/2023/10/20231016170418478.jpg | "T01—T15 国际、港澳台登机口" / "远机位 T03-T08" | verified (13 bridge gates: inf) |
| 33 | T2 gates | 21–75 domestic; bus gates 41–45, 51–55 | https://www.avinex.com/uploadfiles/2023/10/20231016170510286.jpg | "21—75 国内出口" / "远机位 41-45" / "远机位 51-55" | verified (45 bridge gates: inf) |
| 34 | Contact stands | 54, about 34 % of all stands | http://www.caacnews.com.cn/special/2023nzt/7624/2020mhcy1/2020cybzmhj/202308/t20230818_1369755.html | "在只有54个廊桥机位的条件下" / "约为34%" | secondary (agrees with the AIP's 54 VDGS stands out of 161) |
| 35 | Gate→stand rule | Txx→1xx, nn→2nn | AIP cross-check (`aip/derived_aip_zsss/stands.json`) and #32/#33 | — | unverified (inf) |
| 36 | Tower position | 31.196674 N, 121.341534 E | https://api.openstreetmap.org/api/0.6/map?bbox=121.300,31.168,121.362,31.226 (`osm/api_map_zsss` cache), node 3342630333 | "man_made=tower, tower:type=aircraft_control" | secondary (agrees with AIP AD 2.10 "111/520") |
| 37 | Tower height and year | Not found. AIP obstacle 47 m; "1964 control tower" | en-Wikipedia | "In 1964, the original Terminal 1 and the control tower opened" | unverified |
| 38 | Business-aviation base | Opened 26 Mar 2010; 3,100 m² terminal, 4,500 m² hangar, 3 stands, 6,000 movements/yr | https://www.avinex.com/xwg/info_itemid_19492.html | "1座3100平方米的公务机候机楼，1座4500平方米…机库…3个专用的公务机上下客停机位" | verified |
| 39 | Business-aviation operator in 2010 | JV SAA + Hawker Pacific | same | "合资组建上海霍克太平洋公务航空地面服务有限公司" | verified (2010); current operator unverified |
| 40 | China Eastern maintenance base | 31.18447 N, 121.32763 E (west side) | OSM cache, way 1576040006 / hangar way 327613444 | "东方航空技术有限公司虹桥维修基地" / "中国东方航空公司机库" | secondary |
| 41 | Visual approaches and point-merge | Introduced by 2025 | https://pdf.dfcfw.com/pdf/H2_AN202604291821768752_1.pdf | "虹桥机场成功实施目视进近运行模式，结合近距平行跑道优化、点融合飞行程序等" | verified |
| 42 | On-time departure rate 2025 | 91.7 % (domestic passenger flights) | same | "浦东、虹桥机场 2025 年国内客班放行正常率分别达到 93.15%、91.7%" | verified |
| 43 | GA in totals | Non-commercial GA counted in totals: about 1,800–2,000/yr, 5.5/day in 2026 | SIAC briefs and annual reports | "因存在其他形式的飞行（不以营利为目的的通用航空飞行）" | verified (counts inf) |

---

## 10. Inventory (what is cached, and whether we may redistribute it)

| Folder | Data | Licence (quoted in SOURCES.json) | Redistribute |
|---|---|---|---|
| `caac_bulletin_2023/2024/2025` | Bulletin PDFs, ranking xlsx, 2025 hub-by-route xlsx, bulletin pages | "版权所有：中国民用航空局" (copyright CAAC); no reuse licence | no (cite figures) |
| `caac_news_t2_opening_2010`, `caac_slot_capacity_2016` | CAAC pages | same | no |
| `caacnews_bridge_rate_2023`, `caacnews_end_around_2021` | **Hash and quotes only**; copies deleted | "未经协议授权，禁止下载使用" | no |
| `siac_annual_2023/2024/2025`, `siac_interim_2023`, `siac_esg_2025`, `siac_monthly_briefs` | SIAC statutory filings via the Eastmoney mirror | No licence stated | no |
| `saa_airline_directory`, `saa_news_*`, `saa_terminal_flow_maps` | SAA pages and terminal schematics | No licence on the pages; SAA logo on images | no; reference only, never geometry or texture |
| `shgov_press_t2_2010`, `shgov_en_sha_record_2025` | Shanghai government pages | No licence in page text | no |
| `shhqcbd_noise_2012` | Hongqiao CBD government page (newspaper repost) | "版权所有：上海虹桥国际中央商务区管理委员会" | no |
| `sina_2010_night_slots`, `sina_saa_w2026_season` | News pages | "新浪公司 版权所有" (Sina, all rights reserved) | no |
| `zhwiki_sha` | zh-Wikipedia wikitext | CC BY-SA 4.0 | yes, with attribution |
| `derived_field` | Our parsed tables and traffic summary | Facts derived from the above | figures yes; files no |

## 11. Risks
1. **Denominator drift.** Daily movements vary by about ±3 % month to month (757–806/day in 2026) and more by weekday. Scale the "fraction seen" to the **same day's** schedule if we can get one. Otherwise use about 780 for 2026 and state the error bar.
2. **GA and positioning flights.** These are in the totals (about 5/day) but not in the scheduled 802/day. Air-to-ground positioning flights and test flights also fall into this gap.
3. **Hourly profile unknown.** The only primary-adjacent data are the 06:00–02:00 coordination window, the 00–06 no-schedule rule and the 59/h peak. Any hourly shape is an inference until we have a schedule or ADS-B days.
4. **Gate/stand numbering is inferred.** The Txx→1xx and nn→2nn rule comes from matching SAA diagrams to the `aip` key's stand list. The SAA maps are schematic.
5. **T2 bridge count is contradicted (43 vs 45, 2010)**, and today's 41 T2 contact stands differ from both. Use the AIP (54 VDGS stands) and imagery for geometry.
6. **SAA airline directory is undated** and may include stale airlines (KN, Y8).
7. **The tower building is not documented.** Height and form are unknown, and so is whether the AIP's TWR(E) and TWR(W) are one cab or two. Modelling it needs imagery or photos (reference only) or another primary source.
8. **Licences.** CAAC, SIAC and SAA give no reuse licence, and caacnews forbids downloads. Ship only facts with citations, never the files.
9. **Network fragility.** www.avinex.com and www.caac.gov.cn reset connections often, and the SAA flight board is behind a WAF. Any live use of these hosts by the app is risky.

## 12. Questions for the owner
1. **Hourly profile and daily denominator.** May we use a licensed or commercial schedule source (OAG, Cirium, FlightAware AeroAPI) for a per-day schedule? The SAA public flight board blocks scripted access, and I did not get around it. The alternative is the monthly SIAC average (about 780–800/day) and an inferred profile.
2. **What counts as a "movement" for the ADS-B fraction?** Scheduled passenger and cargo flights only (about 797/day, the total minus about 5 GA), or every take-off and landing (the CAAC/SIAC total)?
3. **Control tower.** Can you supply photos or a design reference for the Hongqiao tower (height, cab shape)? No primary source gives its height or year. We know only its position (OSM and AIP) and an AIP obstacle value of 47 m.
4. **Night window.** Should the simulation treat 00:00–06:00 as "no scheduled traffic, but delays and diversions possible", as the 2010 rule says, or as a hard curfew, as trip-support guides call it?
5. **caacnews articles.** Their terms forbid downloading. I kept only quotes and hashes. Is that acceptable, or should we drop caacnews as a source altogether?
