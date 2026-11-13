# Phase 0 / adsb: live and historical flight data for ZSSS

**Errata (2026-11-13, from the verification reports).** Corrected in place below; see `verify_licences_law.md`
(headline findings 1, 2, 6, 8 and rows A2, A5, A10, A33, A43, A46):
- Nearest non-PRC locations: the Korean **Ieodo Ocean Research Station** (a sea platform) at about **378 km** (no
  receiver known there), then Gageodo about 476 km, Marado about 511 km, Dongyin (Matsu) about 543 km and Jeju 548 km,
  not Jeju first. Ieodo lies inside the 455 km FL350 horizon, so only cruise-level traffic could be seen from there.
  The low-level conclusion is unchanged (headline 6, A46).
- The ground radio horizon is about **29 km** for an aircraft antenna at 0 m; the 38 km figure assumes about 5 m (A46).
- adsb.lol publishes no start date for its metering. "New since Sep 2026" is inferred from sfo3d's capture of the old
  text on 2026-09-24 (A2).
- OpenSky Terms 3(i) require aircraft identifiers (and sensor locations) to be anonymised in any publication (A10).
- The Shanghai Airport statement page answered curl with HTTP 200; only the home page failed (headline 8, A43).
- Radio Regs Art. 72: up to CNY 30,000, or with serious consequences licence revocation plus CNY 30,000-100,000;
  Art. 75(2)/(3) (foreign radio monitoring inside the PRC; supplying security-related radio data abroad: CNY
  30,000-100,000, serious 100,000-300,000) was missed (headlines 1-2, A33).
- globe_history has three release tags per day (prod, staging, mlatonly), not one (A5).
- Redaction for the public repo: per-record data from the ADS-B Exchange samples (callsigns, hex codes, positions,
  altitudes, speeds, `nic`, `rssi`) and per-cell OpenSky coverage values are replaced by aggregates. The ADSBx AUP
  forbids publishing its data, and the samples are "for testing and evaluation". Per-record details stay local in
  `refs/cache/adsb_terms/`. They remain in earlier git history; whether to rewrite it is the owner's decision.

Checked on 2026-11-13. All downloads were made that day between 20:18Z and 20:38Z. Each cached source has its URL,
UTC save time, SHA-256, quoted licence and a redistribution flag in a `SOURCES.json`:
- `sha3d/refs/cache/adsb_terms/SOURCES.json`: provider terms, coverage data and probes.
- `sha3d/refs/cache/china_law/SOURCES.json`: PRC laws, CAAC documents and news reports.

The scope is which sources could drive "SHA Live 3D" with real traffic at Shanghai Hongqiao (SHA / ZSSS), on what
terms, and why open ADS-B coverage there is close to nil. This is not legal advice. Where the text below reads a law,
it says what the text says and labels any interpretation as inferred.

Labels used below:
- **observed**: we measured it, or read it in a primary source.
- **inferred**: our interpretation.
- **secondary**: from someone else's report.

Distances are measured from the OurAirports point (31.198104 N, 121.33426 E). The sibling key `aip.md` found that this
point lies 174 m from the AIP ARP. At the 20 to 800 km scales used here, that offset does not matter.

## Verdict (short)

1. **No open source gives observed ZSSS traffic today, and none is likely to.**
   - The lead measured this, and the measurement was not repeated here [secondary: lead]:
     - At 2026-11-13 18:59Z, adsb.lol, adsb.fi and OpenSky all returned 0 aircraft within 40 nm.
     - The adsb.lol globe_history archive held 0 traces within 150 km on 2026-11-10 and 2026-11-12. It held 2 traces
       on 2026-11-08.
   - Three further, independent checks agree (observed):
     - **OpenSky coverage map, 2026-11-12.** OpenSky's own coverage data has **no cell within 233 km** of ZSSS. The
       nearest cells are at 29 N, and the lowest altitude reported in them is 6.5 km or more.
     - **ADS-B Exchange free sample, 2026-11-01 02:00Z and 06:00Z.** The nearest real ADS-B position was **106 to
       119 km** away, at 6,850 ft or higher. The only records nearer ZSSS have message source `other`, which readsb
       defines as "quality / source is unknown". They all carry `nic` 0 and one constant `rssi`, and one is flagged
       "ground" while moving at 370 kt. They are not usable as observations (inferred). (Aggregates only; per-record
       details stay local, see C5.)
     - **AvioADSB, 2026-11-13 20:33Z (04:33 local).** It returned 0 aircraft within 100 nm. That hour is quiet at
       night, so this check is weak on its own.
2. **Why the gap exists.** Two causes combine.
   - **Political and legal.** Since 2020, PRC state security has treated volunteer ADS-B receivers that feed foreign
     sites as a national-security threat:
     - The CCTV report of 2021-10-31 said "hundreds of sets" were seized.
     - The Ministry of State Security (MSS) statement of 2024-01-06 described a nationwide crackdown. It cited the
       Counter-espionage Law and the Data Security Law.
     - Flightradar24 left Chinese app stores in early November 2021 [secondary].
   - **Physical.** Approach and ground traffic can only be received within about 30 to 100 km (radio horizon: about
     29 km for an aircraft on the ground with a 0 m antenna, 38 km with 5 m, 101 km at 1,000 ft). Every receiver that
     could see ZSSS below about 3,000 ft would therefore have to stand in or near Shanghai, inside the PRC. The
     nearest non-PRC locations are the Korean Ieodo Ocean Research Station, a sea platform about 378 km away (no
     receiver is known there), then Gageodo (about 476 km), Marado (about 511 km), Dongyin in Matsu (about 543 km),
     Jeju (548 km), Taiwan (Keelung 676 km) and Kyushu (823 km). From there, only cruise-level traffic is visible:
     Ieodo lies inside the 455 km FL350 horizon, the others near or beyond its edge (inferred).
3. **Terms changed recently. Re-check them before relying on any sfo3d assumption.**
   - **adsb.lol now meters its API.** Without a key the limit is "500 requests/day per IP". adsb.lol publishes no
     start date; that it is new since September 2026 is inferred from sfo3d's capture of the old text on 2026-09-24.
     Feeder keys get 7,200 a day. Sponsor plans range from EUR 20 to 999 a month. The data licence is still **ODbL**
     (API and archive), and feeders' input is CC0.
   - **airplanes.live returns 403** to anyone who does not feed it. A third party reports that it went
     contributor-only in September 2026 [secondary].
   - **OpenSky** needs a written licence for "any operational capacity — including integration into a live product,
     service, or automated system".
   - **adsb.fi** is "personal, non-commercial use only", with no licensing of the data.
   - **ADS-B Exchange** forbids publishing or redistributing its data. Its free samples are "for testing and
     evaluation".
4. **Alternatives.** Only commercial position feeds could give "observed" ZSSS traffic:
   - VariFlight DataWorks: Chinese, ADS-B, area queries return "Current airborne flights", quote-based price.
   - Satellite ADS-B: Aireon (for example through FlightAware AeroAPI Premium, minimum $1,000/month) or Spire
     (custom pricing).

   Each forbids redistribution without a contract. Ground and stand-level observation is unverified for all of them.
   - **Airport flight-information pages** give reported times and terminals. The Shanghai Airport Authority statement
     forbids redistribution without written authorisation.
   - **Schedules** (OAG, Cirium, airline timetables) give only scheduled or inferred traffic.
5. **MLAT and UAT do not matter.**
   - China's transport and general aviation use 1090ES (CAAC ADS-B plan).
   - 468 of 565 China-registered aircraft in the ADSBx sample sent ADS-B, 415 of them version 2.
   - MLAT needs four or more receivers that see the same aircraft, and there are none near ZSSS.

## 1. Coverage evidence

| # | Check | Result | Status |
|---|---|---|---|
| C1 | Live point queries, adsb.lol / adsb.fi / OpenSky, 40 nm, 2026-11-13 18:59Z | 0 aircraft each | secondary (lead; `refs/cache/live/`) |
| C2 | adsb.lol globe_history, full day, 150 km | 2026-11-08: 2 traces of 66,788; 2026-11-10: 0 of 75,360; 2026-11-12: 0 of 73,533 | secondary (lead; `refs/cache/adsb/*.log`) |
| C3 | Nearest covered area seen live | about 31.5 N, 117-119 E (Hefei / Nanjing) | secondary (lead) |
| C4 | OpenSky coverage API, day 2026-11-12 (`/api/range/coverage?day=1794441600`), ground-based ADS-B, 0.2 deg cells, value = lowest altitude seen | 92,484 cells worldwide; **0 cells within 233 km of ZSSS**; 18 cells within 300 km, all at 28.6-29.4 N, lowest altitudes 6,546-11,918 m; the nearest cell with a lowest altitude below 3,000 m is 434 km away. The mainland interior (100-115 E, 25-35 N) has 0 cells. Northern China (35-42 N, 112-122 E) has about 500 cells, the lowest at ground level. (Aggregates only; per-cell values stay local in `refs/cache/adsb_terms/opensky_coverage_api/`.) | verified (own measurement on OpenSky's published coverage data) |
| C5 | ADS-B Exchange free sample `readsb-hist` 2026-11-01 02:00:00Z and 06:00:00Z | Aggregates only. 02:00Z: 8,316 aircraft worldwide; nearest `adsb_icao` position to ZSSS 119 km (6,850 ft); no `other` record within 100 km. 06:00Z: 7,927 aircraft; nearest `adsb_icao` positions 106 km (two aircraft, 6,925 and 14,650 ft). Within 100 km only 4 records with message source `other` (nearest 19.9 km; 3 flagged "ground", two of those with ground speeds of 220 and 370 kt), all with `nic` 0 and the same `rssi`. The 4-degree box that contains ZSSS (28-32 N / 120-124 E) held 3 `adsb_icao` aircraft at 02:00Z (lowest 3,075 ft, 157 km away) and 5 at 06:00Z (lowest 6,925 ft). The box north of it (32-36 N / 120-124 E) had a lowest altitude of 34,100 ft (02:00Z). Low-level `adsb_icao` aircraft (below 3,000 ft or on the ground, within 20 km of the airport), 02:00Z / 06:00Z: Hong Kong VHHH 12 / 19, Taipei Taoyuan RCTP 10 / 6, Nanjing ZSNJ 1 / 1, Xi'an ZLXY 1 / 1, so mainland low-level coverage is thin. Per-record details (callsigns, hex, positions, speeds) stay local in `refs/cache/adsb_terms/adsbx_sample_20261101/`; the ADSBx AUP forbids publishing them. | verified (own measurement on ADSBx sample data; "for testing and evaluation") |
| C6 | AvioADSB `/v1/point/31.198104/121.33426/100`, 2026-11-13 20:33:16Z | `{"ac":[],"total":0}` | verified (own probe), weak: 04:33 local |
| C7 | airplanes.live `/v2/point/31.198/121.334/5`, 2026-11-13 20:21:32Z | HTTP 403 `{"error": "Please contact us at contact@airplanes.live. Your email MUST include any links, a description of the project, and any information you deem appropriate."}` (JSON from the application, behind Cloudflare) | verified (own probe) |

**Inferred from C4 and C5: ADS-B Exchange has no better coverage at ZSSS than adsb.lol.**
- The `other` records near Shanghai look like a third-party feed that was injected into ADSBx, not reception by its own
  feeders:
  - every record has the same `rssi`;
  - every record has `nic` 0;
  - `gs` and `track` are integers;
  - "ground" is reported at 370 kt;
  - `messages` counts run to tens of millions.
- readsb's documentation gives the meaning of `type: other`: "miscellaneous data received via Basestation / SBS
  format, quality / source is unknown."
- Do not treat such records as observed positions.

**Radio horizon (inferred).** The standard 4/3-earth horizon is d ≈ 4.12 (√h₁ + √h₂) km, with h in metres. For a
receiver at 50 m:

| Aircraft height | Horizon |
|---|---|
| FL350 | 455 km |
| FL200 | 351 km |
| 3,000 ft | 154 km |
| 1,000 ft | 101 km |
| On the ground (antenna 5 m) | 38 km (theoretical; buildings cut this) |
| On the ground (antenna 0 m) | 29 km |

The nearest non-PRC locations (great circle from the AIP ARP, verify_licences_law.md A46) are the Ieodo Ocean
Research Station (Korean sea platform) about 378 km, Gageodo about 476 km, Marado about 511 km, Dongyin (Matsu, ROC)
about 543 km and Jeju 548 km; then Keelung 676 km, Taipei 680 km, Nagasaki 823 km, Naha 829 km and Incheon 839 km. No
receiver is known at Ieodo. Ieodo is inside the 455 km FL350 horizon, so a receiver there could in theory see
cruise-level traffic over ZSSS, but none of these places can see ZSSS approach or ground traffic. Only receivers
inside the PRC could. The OpenSky cells at 29 N (6.5-12 km altitude) fit receivers in Taiwan seeing cruise traffic
near their range limit (inferred). The covered area near Hefei and Nanjing (C3, C5) shows that at least one feeder
inside the mainland still reports to adsb.lol and ADSBx (inferred).

## 2. Provider terms (as published on 2026-11-13)

### 2.1 adsb.lol

API terms are in the live OpenAPI description (version 0.0.2, `adsblol_openapi/openapi.json`):
> "No key: **500 requests/day per IP**. A free key raises it: anonymous (30 days, no account): 500/day; adhoc (free,
> request form): 1,000/day; feeder (free, by feeding the network): 7,200/day, 20 GB/month, and the raw re-api;
> sponsor plans: up to 360,000/day"

> "Over quota returns `429` with a `Retry-After` header. Unkeyed traffic is limited per IP; the daily window is a fixed
> 24h bucket, not midnight UTC."

> "The license for the API as well as all data ADSB.lol makes public is ODbL"

- **Metered and free paths.** `/v2/` and `/1/trace/` are metered. The `/0/` paths and `/api/0/{my,routeset}` are free.
- **Contradiction on the daily window.** The docs page (`/docs/open-data/api`) says "the daily window resets at 00:00
  UTC". The OpenAPI says "a fixed 24h bucket, not midnight UTC". Status: **contradicted** within adsb.lol's own pages.
- **What changed.** sfo3d's research of 2026-09-24 (`sfo3d/docs/research/realtime_feeds.md` §3.1) quoted the old text,
  "You can use the API for free. In the future, you will require an API key …". adsb.lol states no start date for the
  metering, and its changelog does not list the key work, so "since September 2026" is our inference from that
  capture. **The sfo3d design of 1 request per second through a relay (86,400 a day) no longer fits any free tier.**
- **Sponsor plans** (`/sponsor`): clearance EUR 20/month (24,000 requests/month), tower EUR 50 (72,000/month,
  "included with feeder"), approach EUR 99, center EUR 499, oceanic EUR 999 ("real-time firehose").

The historical archive (globe_history) has its own terms:
- The docs page says: "license: ODbL 1.0, use it freely, just keep it open."
- The repo README (`adsblol/globe_history_2026`, commit 5959c79 of 2026-11-13) says: "This database is made available
  under the Open Database License: http://opendatacommons.org/licenses/odbl/1.0/." It adds that the data includes
  "ADSB.lol feeders and friends, FlyItalyADSB and TheAirTraffic.com".
- On feeders, the README says: "By feeding adsb.lol, you agree to the extent possible under law, to waive all
  copyright and related or neighboring rights to your data, associating your work with the CC0 license." The privacy
  page says the same.
- The archive's size is stated as "2056 GiB" for 2026. The README says "Each release is 1 day of flight data"; each
  day has three release tags (prod, staging, mlatonly).

**Redistribution.** It is allowed under ODbL 1.0:
- **Attribution (§4.3).** A notice is needed, for example: "Contains information from ADSB.lol (https://adsb.lol),
  made available under the ODbL." This wording is already in `refs/cache/adsb/SOURCES.json`.
- **Share-alike (§4.4).** It applies to derived databases that are publicly used.

### 2.2 adsb.fi

Source: the README of `adsbfi/opendata` (commit 9fe1c9a, 2026-05-17). The adsb.fi web pages answered 403 behind a
Cloudflare challenge.

The terms:
> "adsb.fi open data is for personal, non-commercial use only. You may not license, sell, rent, or lease any part of
> the data or the service. The data and the service are provided as-is, without any warranty. You must cite adsb.fi
> and include a link to our home page."

The limits: "The public endpoints are rate limited to 1 request per second". Invalid requests (400, 401, 403, 404 and
429) also count toward that limit.

Consequence: adsb.fi records cannot go into anything we publish under ODbL. This is the same conflict as sfo3d's OD-11.

### 2.3 OpenSky Network

**Terms of Use** (`opensky_terms/terms-of-use.html`):
> "Operational REST API use: Use of the REST API in any operational capacity — including integration into a live
> product, service, or automated system (even if only internal) — requires a previous written agreement, even for
> non-profit or governmental entities."

> §1: "solely for the purpose of non-profit research and non-profit education."

> §3(i): "For any publication or other disclosure, You will anonymize or de-identify personally-identifiable
> information, aircraft identifiers, sensor locations and other data identified in Supplemental provisions (if any)."

> §3(iii): "You will not distribute, disclose, transfer or otherwise make available the data set(s) to any person other
> than those employed by your institute …"

> §3(vi): "The REST API is provided for non-profit research and educational use only."

**FAQ** (`opensky_faq/faq.html`):
> "You can freely use the API for personal and non-profit applications but any commercial use requires our consent."

**Does the FAQ contradict the Terms?** Status: **contradicted in emphasis**.
- The FAQ reads more permissively than the Terms, which require a written licence for any live product even when it is
  non-profit.
- Follow the binding Terms. The Terms state that they are "legally binding under the laws of the Swiss Confederation".

**Anonymous REST is technically allowed.** The REST documentation says:
> "Anonymous users (unauthenticated, bucketed by IP): Only the most recent state vectors are available … Time
> resolution is 10 seconds"

- Anonymous users get 400 credits a day per endpoint bucket.
- A `/states/all` request over a box of 25 sq° or less costs 1 credit.
- "OpenSky exclusively supports the OAuth2 client credentials flow. Basic authentication with username and password is
  no longer accepted."

**Legal reading.** Anonymous access does not lift the Terms. Inferred: a live ZSSS page counts as "integration into a
live product", so a written licence is needed. A one-off research probe, like the lead's, is within the Terms.

**Coverage in China.**
- The FAQ says OpenSky has "the best coverage in Europe and the US".
- OpenSky's own coverage data for 2026-11-12 (C4) shows nothing within 233 km of ZSSS.

### 2.4 airplanes.live

**Observed.**
- The API returns 403 with the "contact us … description of the project" message (C7).
- `/api-guide/`, `/api`, `/api-docs/` and `/terms-of-use/` all return 403 to curl and to WebFetch.
- web.archive.org is unreachable from here.

**Why the 403** [secondary]:
- A GitHub issue opened 2026-10-20 (`ColinWaddell/FlightTracker#123`, read with WebFetch) says: "In September 2026,
  airplanes.live moved their API to be contributor-only" and "using the API from an IP address that isn't already
  feeding them data will always return a 403."
- A web-search summary of the new `/api` page mentions a Free tier of 500 requests/day, a Contributor tier of
  8,640/day and a Business tier ("Contact Us") [unverified: the page itself was not readable].
- sfo3d's research says the open-access API guide ("No SLA No Uptime Guarantee Non-Commercial Use … rate limited to 1
  request per second") disappeared between 16 and 26 Aug 2026 [secondary: sfo3d `realtime_feeds.md` §3.3, Wayback].

**Verdict.** It is unusable without feeding (impossible for ZSSS) or written permission. The terms of use are unverified.

### 2.5 ADS-B Exchange (JETNET)

**Acceptable Use Policy** ("Last Updated: April 17, 2026"). The customer shall not:
> "Publish, resell, transmit, broadcast, distribute the Services or data acquired from the Services."

**Community API** (developer hub):
> "What you get for $10/mo. 10,000 requests Real-time aircraft position data: 500ms updates"

The hub adds: "If you start hitting limits or need commercial use, we have Enterprise options".

**Enterprise and data products.** These are API, streaming ("updates every 250ms") and daily data. Terms are on
contract and redirect to `jetnet.com/legal/terms-of-use`.

**Free samples:**
> "we offer free access to the first-of-the-month data sets for testing and evaluation … Complete data from the 1st of
> each month are made available free of charge."

We used two snapshots only for evaluation (C5). They must not be redistributed or used in the product, and this
report gives only aggregates from them.

**Verdict.** No: redistribution is forbidden, and the coverage at ZSSS is no better (C5).

### 2.6 Other networks with open or semi-open terms

| Network | Terms (quoted) | Access | Status for ZSSS |
|---|---|---|---|
| **ADSBHub** | "Every ADSBHub user has to share data feed at least one ADS-B station." "There are no restrictions on how the users will use the data. Everybody is allowed to publish the data for free or to use it for commercial purposes." | SBS TCP stream, only to IPs that feed | You must feed to get data; the coverage near ZSSS is unknown, and adsb.lol's README lists it as an open network. A feeder inside China is ruled out (section 3). |
| **AvioADSB** (a "SkyLink API company") | "Data is licensed CC BY-NC 4.0"; credit "Data: AvioADSB (CC BY-NC 4.0)"; free API "for personal, education and research use" | Anonymous: 1 request/10 s, 100/day, radius ≤ 100 nm; contributor 10,000/month | 0 aircraft at 04:33 local (C6); non-commercial only |
| FlyItalyADSB, TheAirTraffic | feed into adsb.lol (README) | via adsb.lol | covered by the adsb.lol results |
| VRS standing data (routes in adsb.lol `routeset`) | CC0 1.0 [secondary: sfo3d `realtime_feeds.md` §3.1] | free path | schedule-derived guesses, not observations. Our probe on 2026-11-13 got HTTP 201 with an empty body, even for a control callsign (BAW283): inconclusive. |

**Commercial aggregators not checked in detail:** Flightradar24, FlightAware, RadarBox/AirNav, Wingbits, Plane Finder.
- sfo3d recorded on 2026-09-24 that FR24's Terms forbid using its API "to supplement or backfill any other near-time or
  real-time flight data" [secondary: Wayback capture of 2026-08-16, in sfo3d `realtime_feeds.md` §3.7].

## 3. China: legal and political background

### 3.1 What happened (timeline)

**2020 to 2021: discovery and seizures.** A CCTV report was broadcast around 2021-10-31. Its text is reproduced by
澎湃新闻 on 2021-11-01, the 7th anniversary of the Counter-espionage Law [secondary: state-media repost of CCTV]:
> "2020年以来，国家安全机关接连发现，多个境外机构在我国境内开设网站，并在微博、贴吧、论坛、QQ群、视频网站等多个平台推送广告，利用我国国内航空和无线电爱好者群体，以免费提供设备、共享航空信息数据等为诱饵，广泛招募志愿者，协助其搜集我国各类飞行器航空数据等信息，并非法向境外传输。"

> "办案人员告诉记者，这套设备叫ADS_B信号接收设备，可以跟踪所有配备该系统的飞机。"

> "日前，国家安全机关会同监管部门在全国范围内组织开展专项查处，查获数百套境外机构在我国违规布设的设备。"

> "国家安全机关依法暂扣了其持有的设备，并进行了严肃批评教育。"

**How the volunteers were treated.** They were not prosecuted in that report: their devices were "temporarily
withheld" and they received "serious criticism and education".

**The coverage claim in the report:**
> "设备的覆盖半径可达到300到400公里，仅需300台左右，就可以实现对我国全空域飞机的信号监测"

**Flightradar24 removed from Chinese app stores (November 2021)** [secondary: RFA 2021-11-05; SCMP and other media
via web search]:
> RFA: "现时中国境内不能下载服务应用程式"

SCMP 3155895, as summarised by web search, quotes FR24 saying Apple had removed the app and that "Chinese authorities
have not been in touch" [unverified: SCMP was not readable here].

**The CCTV report did not name the company.** The 2021 text reads "某境外公司" and "境外机构" (observed). The link
to Flightradar24 was made by foreign media.

**2024-01-06: the MSS statement.** The Ministry of State Security WeChat account published a statement. It was
reposted by 上观新闻 and 中国经济网, and by 央视新闻 and 光明网 [secondary: state-media reposts; the WeChat original
was not read]:
> "近期，国家安全机关工作发现，多个境外机构以免费提供设备、共享航空信息为诱饵，依托网络社交平台面向境内航空爱好者精准招募“志愿者”，并跨境邮寄设备，指挥“志愿者”在我境内非法采集、向境外秘密传输我国飞行器飞行数据。"

> "这些境外机构在我国渤海、东海、南海周边省份大量投放此类设备，不仅窃取民用航空数据，甚至还能窃取军用航空器等敏感数据信息。"

> "国家安全机关会同有关部门在全国范围内开展了专项打击，及时查获数百套已在境内投放的设备，依法对有关人员进行处罚。"

The statement then quotes two laws:
- The Counter-espionage Law: "…窃取、刺探、收买、非法提供关系国家安全和利益的数据，属于间谍行为。"
- The Data Security Law: "任何组织、个人收集数据，应当采取合法、正当的方式，不得窃取或者以其他非法方式获取数据。"

**Shanghai is in scope.** Shanghai borders the East China Sea (东海), one of the three sea regions the MSS names
(inferred).

**The two statements differ.** The 2024 text says the authorities imposed penalties ("依法对有关人员进行处罚"). The
2021 text said they used criticism and education.

### 3.2 Laws and regulations (primary texts read)

| Instrument | Provision | Text (quoted) | Status |
|---|---|---|---|
| 反间谍法 Counter-espionage Law, revised 2023-04-26, in force 2023-07-01 (npc.gov.cn) | Art. 4(3) | "间谍组织及其代理人以外的其他境外机构、组织、个人实施或者指使、资助他人实施，或者境内机构、组织、个人与其相勾结实施的窃取、刺探、收买、非法提供国家秘密、情报以及其他关系国家安全和利益的文件、数据、资料、物品…的活动" | verified |
| 数据安全法 Data Security Law, adopted 2021-06-10, in force 2021-09-01 (npc.gov.cn) | Art. 2 (extraterritorial) | "在中华人民共和国境外开展数据处理活动，损害中华人民共和国国家安全、公共利益或者公民、组织合法权益的，依法追究法律责任。" | verified |
| same | Art. 3 | "本法所称数据，是指任何以电子或者其他方式对信息的记录。" | verified |
| same | Art. 21 (important data catalogues) | "国家数据安全工作协调机制统筹协调有关部门制定重要数据目录…各地区、各部门应当…确定本地区、本部门以及相关行业、领域的重要数据具体目录" | verified |
| same | Art. 32 | "任何组织、个人收集数据，应当采取合法、正当的方式，不得窃取或者以其他非法方式获取数据。" | verified |
| 网络数据安全管理条例 Network Data Security Management Regulations, State Council Order 790, in force 2025-01-01 (gov.cn Gazette) | Art. 62(4) | "重要数据，是指特定领域、特定群体、特定区域或者达到一定精度和规模，一旦遭到篡改、破坏、泄露或者非法获取、非法利用，可能直接危害国家安全、经济运行、社会稳定、公共健康和安全的数据。" | verified |
| same | Art. 37 | important data "确需向境外提供的，应当通过国家网信部门组织的数据出境安全评估"; data that has not been notified or published as important data "不需要将其作为重要数据申报" | verified |
| 无线电管理条例 Radio Regulations, State Council / CMC Order 672, in force 2016-12-01 (gov.cn Gazette 2016 No. 35) | Art. 27(2) | a radio-station licence is required, "但设置、使用下列无线电台（站）的除外：…（二）单收无线电台（站）" (receive-only stations are exempt) | verified |
| same | Art. 41 | "使用无线电台（站）的单位或者个人不得故意收发无线电台执照许可事项之外的无线电信号，不得传播、公布或者利用无意接收的信息。" | verified |
| same | Art. 72(2) | penalty for "故意收发无线电台执照许可事项之外的无线电信号，传播、公布或者利用无意接收的信息": correction, confiscation of illegal gains, a fine of up to CNY 30,000; "造成严重后果的，吊销无线电台执照，并处3万元以上10万元以下的罚款" (serious consequences: licence revoked plus CNY 30,000-100,000) | verified |
| same | Art. 75(2)/(3) | "（二）境外组织或者个人在我国境内进行电波参数测试或者电波监测；（三）向境外组织或者个人提供涉及国家安全的境内电波参数资料": correction; on refusal, confiscation and CNY 30,000-100,000; serious consequences CNY 100,000-300,000 | verified (added from verify_licences_law.md) |
| 民航数据管理办法（试行） CAAC Civil Aviation Data Management Measures (trial), published 2025-03 (caac.gov.cn PDF) | Arts. 14, 31 | data are graded "一般数据、重要数据、核心数据"; "民航局数据统筹管理部门…制定民航领域重要数据和核心数据目录" | verified (text); the catalogue itself was not found, so whether flight-track or ADS-B data are listed is unverified |
| 著作权法 Copyright Law (2020 amendment), Art. 5 (MOFCOM law-database copy) | Art. 5(1) | "本法不适用于：（一）法律、法规，国家机关的决议、决定、命令和其他具有立法、行政、司法性质的文件，及其官方正式译文" | verified (government mirror; NCAC original unreachable) |

**Not found.** No PRC law or regulation names ADS-B reception or the sharing of aircraft positions specifically
(observed: none in the texts read, and none in searches). The closest general radio rule is Radio Regs Art. 75(2)/(3):
foreign radio monitoring inside the PRC, and supplying security-related PRC radio data abroad.

**How the authorities frame it.** The 2021 and 2024 statements cite the Counter-espionage Law (supplying data
"关系国家安全和利益" to foreign organisations) and the Data Security Law's collection rule (our Art. 32), applied to the
cross-border feed. They quote the wording without article numbers; the article mapping is ours. They do not rest on
the act of reception itself (observed in the statements). This list is incomplete: Radio Regs Art. 75(2)/(3) also
covers foreign radio monitoring inside the PRC (inferred).

### 3.3 What this means for sha3d (inferred, not legal advice; owner's decision)

- **Receiving without a station licence.** Art. 27(2) exempts receive-only stations. But Art. 41 forbids
  deliberately receiving signals outside the licence and "传播、公布或者利用无意接收的信息" (spreading, publishing or
  using unintentionally received information). Art. 75(2)/(3) covers radio monitoring inside the PRC on behalf of
  foreign parties. In addition, the security services treat a feed sent abroad as espionage-relevant.
  **Anyone in the PRC who ran a receiver feeding our project, or adsb.lol or similar, would carry real legal risk.**
  Do not set one up, ask anyone to, or buy one for anyone.
- **Data processing outside China.** It is in scope of the Data Security Law where it "harms" PRC national security
  (Art. 2).
  - Showing civil airliner positions at a civil airport, from data that is already public abroad (for example,
    adsb.lol's ODbL archive), is far from the cases above. Those cases involved deploying hardware and moving data
    across the border.
  - So the risk to a repository outside China looks low, but it is not zero.
  - We cannot rule out that flight-track data counts as "important data" under a catalogue: CAAC's catalogue is not
    public.
  - Avoid anything that looks like collecting or aggregating PRC aviation data. Display only, and use no military or
    state-aircraft filters (inferred).
- **Data from Chinese providers.** VariFlight, Amap and others may deliver coordinates in GCJ-02. Under the owner's
  rule, check each position source for a GCJ-02 offset before use, and never mix such data with WGS-84 (inferred).

## 4. Alternative sources: what each can support

| Source | What it gives | Observed or scheduled | Access, price | Terms (quoted) | Verdict |
|---|---|---|---|---|---|
| **VariFlight DataWorks** (飞常准) ADS-B API | area query: "Current airborne flights within the selected area"; flight trajectory; registration lookup; "nearly 10 years of historical flight data" | observed **airborne** positions (ground not offered in the query table) | pricing "flexible plans: pay-as-you-go … enterprise subscriptions"; "14-day free trial prior to formal commercial engagement"; real-time trial "for business users only" [secondary: search summary] | "absent a formalized, written contract … they shall not … cache for unauthorized redistribution, repackaging, or commercially resell our proprietary APIs, ADS-B streams"; attribution "Source: VariFlight"; jurisdiction "the People's Court … at the place of execution" | the only domestic option for observed positions; needs a contract for public display; GCJ-02 check needed |
| **VariFlight flight status** | "Real-time gate and check-in counter data, live schedule updates"; "refreshed every 15-30 seconds, sourced directly from global aviation authorities, airports, airlines, and ADS-B trackers" | reported events (times, gates); no positions | as above | as above | gate truth if licensed; stand numbers unverified |
| **Aireon** (Iridium NEXT payloads) | AireonSTREAM: "global, gate-to-gate, surface-to-space ATS surveillance quality data" (vendor claim) | observed (airborne for certain; surface unverified) | for ANSPs and data partners; price on contract | not published | expensive; surface claim and update rate unverified for ZSSS |
| **FlightAware AeroAPI** | Personal tier: "Current flight status and tracks"; "Aireon Space-Based ADS-B" only in Premium ("Contact us to enable"; $1,000/month minimum) | tracks: mixed sources (unknown for China) | Personal: up to $5 free a month, "10 result sets/minute"; Standard: $100/month minimum; Premium: $1,000/month minimum | Personal: "Storage and distribution of derivative works for personal or academic purposes only" | possible per-flight check (status, gate?) on Personal; satellite positions only on Premium. The 2016 VariFlight-FlightAware data exchange (环球旅讯, 2016-11-02) suggests FlightAware has Chinese data, but it is old [secondary]. |
| **Spire Aviation** | "Satellite and terrestrial ADS-B data … Historical API … Flight tracking data stream" | observed (airborne; surface unverified) | "Contact us directly for custom pricing" | not read | commercial only |
| **Shanghai Airport Authority** flight query (shanghaiairport.com) | departures and arrivals for Pudong and Hongqiao; template fields seen: 航空公司, 主航班号, 计划时间, 出发地/目的地, 候机楼. No gate or stand field was visible (data rendered client-side). | reported schedule and status; no positions | free web page; the home page reset the connection to curl and was read with WebFetch; the statement page (`/wzaqzc/`) answered curl with HTTP 200 on re-check (verify_licences_law.md A43) | 网站声明: "非经本公司书面授权，任何人不得将本网站的交易资讯、行业资讯、服务资讯等讯息进行再传播。"; "本网站所提供信息仅供参考" | no redistribution without written authorisation; scraping not permitted (inferred); at most a manual reference |
| **CAAC open data** | data.caac.gov.cn is unreachable here. CAAC publishes statistics; the CAAC ADS-B plan states ADS-B information services "为航空企业全面提供", i.e. for aviation enterprises only | aggregates; not per-flight | — | — | no observed traffic for the public |
| **OAG / Cirium / airline timetables / AeroDataBox** | schedules, sometimes FIDS times and gates | scheduled / inferred | commercial (AeroDataBox: "Can I resell your API or any data from it? No" [secondary: sfo3d §3.8]) | licence-bound | scheduled or inferred traffic only |
| **adsb.lol archive** (ODbL) | daily traces | observed, but empty near ZSSS (C2) | free | ODbL 1.0 | nothing to replay |

**What can count as "observed" at ZSSS:**
- **Positions.** Only a commercial position feed gives them: VariFlight ADS-B, Aireon (for example through FlightAware
  Premium) or Spire. Their airborne coverage near Shanghai is plausible but unverified. **Ground, taxi and stand
  coverage is unverified for all of them.** VariFlight's area query explicitly returns airborne flights.
- **Event times.** Airport FIDS pages and VariFlight or FlightAware status can give observed times (actual off-block,
  take-off, landing, gate). The motion between those events would still be inferred.
- **Everything else** (schedules, routes, runway use from METAR wind) is scheduled or inferred.

## 5. MLAT and UAT

- **UAT does not apply.** The CAAC ADS-B plan (2015 revision) says:
  > "运输航空采用国际民航组织标准的 1090ES 数据链。"

  > "通用航空采用国际民航组织标准的 1090ES 数据链。"

  It mentions 978 MHz UAT only for "部分用于航空教学训练的航空器" (as of 2014). The same plan targets "到 2020 年底，实现
  ADS-B OUT 全面运行" for transport aviation.
- **MLAT does not apply.**
  - MLAT needs at least four time-synchronised receivers with a common view of the aircraft. Seeing ground traffic
    would need several receivers within tens of kilometres. There are none near ZSSS.
  - The fleet already broadcasts ADS-B. In the ADSBx sample, 468 of 565 aircraft with a Chinese 24-bit address
    (780000-7BFFFF) were `adsb_icao`, 415 of them ADS-B version 2. Only 59-73 were Mode S without position, and only
    1-2 were MLAT (observed).
  - So MLAT would add almost nothing even if receivers existed (inferred). It is the same conclusion as sfo3d's §2.

## 6. Honest options for the owner

1. **"Simulated Hongqiao" mode (recommended baseline).**
   - Traffic is generated from a schedule. It is explicitly labelled *scheduled / inferred*:
     - runway direction from the ZSSS METAR wind;
     - stands assigned by type rules;
     - movement times taken from the schedule.
   - It needs a schedule source we may use:
     - (a) a licensed schedule (OAG or Cirium; cost; no redistribution);
     - (b) a hand-built "typical day" made from public aggregate statistics (CAAC monthly movements) and airline
       timetables, entered manually as facts. Whether that is acceptable under the publishers' terms needs checking;
     - (c) no real schedule at all: synthetic traffic at realistic rates, flagged as synthetic.
   - No legal exposure in China.
2. **Opportunistic adsb.lol (ODbL) overlay.**
   - Poll adsb.lol for whatever is visible (today: high-altitude traffic at 100-450 km at best) and show it as
     *observed* when present, together with option 1.
   - It must fit "500 requests/day per IP": one poll every 3 minutes. Otherwise it needs a feeder key, which is
     impossible for ZSSS, or a sponsor plan (EUR 20-999 a month).
   - Attribution text as in 2.1. It will almost never show ZSSS approach or ground traffic.
3. **Licensed commercial feed for observed airborne positions.**
   - Choices: VariFlight DataWorks (domestic; airborne ADS-B and gate data; quote-based) or Aireon (for example
     through FlightAware Premium, $1,000/month minimum, "contact us").
   - Public display needs a written contract under each provider's terms, and **no recorded data may enter the public
     repository**.
   - Ground and stand-level observation is still unverified, so the stand logic stays inferred.
   - Before signing, ask the vendor for: ZSSS coverage below 1,000 ft and on the ground; the coordinate datum (WGS-84
     or GCJ-02); and the update rate.
4. **Replay of history.** There is none worth having: the open archive is empty near ZSSS. ADSBx history is
   commercial, and its free samples are for evaluation only, with low-level coverage no better than adsb.lol.
5. **Not recommended: our own receiver in Shanghai, or recruiting feeders there.** Sections 3.1 and 3.3 explain why.
   It would put a person in the PRC at risk, and it would also conflict with the owner's privacy rule.
6. **Out of scope, for the owner to weigh.** If real live traffic is the point of the project, the ADSBx sample shows
   aircraft on the ground at Hong Kong (VHHH) and Taipei Taoyuan (RCTP) (C5, counts only). A different airport would
   have a live feed; ZSSS will not with open data. Coverage at those airports was seen only in the ADSBx sample and has not been
   checked in adsb.lol.

## 7. Facts table

| # | Topic | Value | Source URL | Date checked | Quote | Status |
|---|---|---|---|---|---|---|
| F1 | adsb.lol API licence | ODbL (API and all public data) | https://api.adsb.lol/api/openapi.json | 2026-11-13 | "The license for the API as well as all data ADSB.lol makes public is ODbL" | verified |
| F2 | adsb.lol API quota without key | 500 requests/day per IP; 429 + Retry-After over quota | https://api.adsb.lol/api/openapi.json | 2026-11-13 | "No key: **500 requests/day per IP**." | verified |
| F3 | adsb.lol daily window | fixed 24 h bucket vs reset at 00:00 UTC | https://api.adsb.lol/api/openapi.json ; https://www.adsb.lol/docs/open-data/api/ | 2026-11-13 | "a fixed 24h bucket, not midnight UTC" / "the daily window resets at 00:00 UTC" | contradicted |
| F4 | adsb.lol feeder tier | 7,200/day, 20 GB/month, re-api | https://api.adsb.lol/api/openapi.json | 2026-11-13 | "feeder (free, by feeding the network): 7,200/day, 20 GB/month" | verified |
| F5 | adsb.lol sponsor plans | EUR 20 (clearance) … EUR 999 (oceanic) a month | https://www.adsb.lol/sponsor | 2026-11-13 | "clearance … €20"; "oceanic … €999" | verified |
| F6 | globe_history licence | ODbL 1.0 | https://github.com/adsblol/globe_history_2026 (README, commit 5959c79) | 2026-11-13 | "This database is made available under the Open Database License: http://opendatacommons.org/licenses/odbl/1.0/." | verified |
| F7 | globe_history docs | ODbL 1.0; one day per release, three release tags per day (prod, staging, mlatonly) | https://www.adsb.lol/docs/open-data/historical/ | 2026-11-13 | "license: ODbL 1.0 , use it freely, just keep it open." | verified |
| F8 | adsb.lol feeder input | CC0 waiver | https://www.adsb.lol/docs/privacy-license/ | 2026-11-13 | "you agree … to waive all copyright and related or neighboring rights to the data you are sharing, under the CC0 license" | verified |
| F9 | adsb.lol archive sources | ADSB.lol feeders, FlyItalyADSB, TheAirTraffic | globe_history_2026 README | 2026-11-13 | "This includes data from ADSB.lol feeders and friends, FlyItalyADSB and TheAirTraffic.com" | verified |
| F10 | adsb.fi terms | personal, non-commercial; no licensing; cite with link | https://github.com/adsbfi/opendata (README, commit 9fe1c9a) | 2026-11-13 | "adsb.fi open data is for personal, non-commercial use only. You may not license, sell, rent, or lease any part of the data or the service." | verified |
| F11 | adsb.fi rate limit | 1 request/s | same | 2026-11-13 | "The public endpoints are rate limited to 1 request per second" | verified |
| F12 | OpenSky operational use | written agreement needed, even non-profit | https://opensky-network.org/about/terms-of-use | 2026-11-13 | "Use of the REST API in any operational capacity — including integration into a live product, service, or automated system (even if only internal) — requires a previous written agreement" | verified |
| F13 | OpenSky redistribution | not allowed outside one's institute | same, §3(iii) | 2026-11-13 | "You will not distribute, disclose, transfer or otherwise make available the data set(s) to any person other than those employed by your institute" | verified |
| F13a | OpenSky publication | aircraft identifiers and sensor locations must be anonymised in any publication | same, §3(i) | 2026-11-13 | "For any publication or other disclosure, You will anonymize or de-identify personally-identifiable information, aircraft identifiers, sensor locations" | verified (added from verify_licences_law.md) |
| F14 | OpenSky FAQ vs Terms | FAQ more permissive | https://opensky-network.org/about/faq | 2026-11-13 | "You can freely use the API for personal and non-profit applications but any commercial use requires our consent." | contradicted (vs F12) |
| F15 | OpenSky anonymous REST | latest state only, 10 s resolution, 400 credits/day | https://openskynetwork.github.io/opensky-api/rest.html | 2026-11-13 | "Anonymous users (unauthenticated, bucketed by IP): Only the most recent state vectors are available … Time resolution is 10 seconds" | verified |
| F16 | OpenSky auth | OAuth2 client credentials only | same | 2026-11-13 | "OpenSky exclusively supports the OAuth2 client credentials flow. Basic authentication with username and password is no longer accepted." | verified |
| F17 | OpenSky coverage near ZSSS, 2026-11-12 | 0 cells within 233 km; nearest at 28.6-29.4 N with min alt 6.5-12 km | https://opensky-network.org/api/range/coverage?day=1794441600 | 2026-11-13 | (data: 92,484 cells; nearest at 233 km; per-cell values kept local) | verified (own measurement) |
| F18 | OpenSky stated coverage | best in Europe and US | https://opensky-network.org/about/faq | 2026-11-13 | "have the best coverage in Europe and the US" | verified |
| F19 | airplanes.live API | 403 "contact us" | https://api.airplanes.live/v2/point/31.198/121.334/5 | 2026-11-13 | "Please contact us at contact@airplanes.live. Your email MUST include any links, a description of the project" | verified (own probe) |
| F20 | airplanes.live contributor-only | since Sep 2026 | https://github.com/ColinWaddell/FlightTracker/issues/123 | 2026-11-13 | "In September 2026, airplanes.live moved their API to be contributor-only" | secondary |
| F21 | airplanes.live terms | unreadable (403 everywhere) | https://airplanes.live/terms-of-use/ | 2026-11-13 | — | unverified |
| F22 | ADS-B Exchange AUP | no publishing or redistribution | https://www.adsbexchange.com/acceptable-use-policy/ | 2026-11-13 | "Publish, resell, transmit, broadcast, distribute the Services or data acquired from the Services." | verified |
| F23 | ADS-B Exchange Community API | $10/month, 10,000 requests, non-commercial | https://www.adsbexchange.com/community/developer-hub/ | 2026-11-13 | "What you get for $10/mo. 10,000 requests" | verified |
| F24 | ADS-B Exchange samples | 1st of month free "for testing and evaluation" | https://www.adsbexchange.com/data-products/sample-data/ | 2026-11-13 | "we offer free access to the first-of-the-month data sets for testing and evaluation" | verified |
| F25 | ADSBx coverage near ZSSS (2026-11-01) | nearest `adsb_icao` 106-119 km at ≥ 6,850 ft; only `other` records closer (aggregates; records kept local) | https://samples.adsbexchange.com/readsb-hist/2026/11/01/060000Z.json.gz | 2026-11-13 | (data) | verified (own measurement) |
| F26 | readsb `type: other` | source unknown | https://raw.githubusercontent.com/wiedehopf/readsb/dev/README-json.md | 2026-11-13 | "other: miscellaneous data received via Basestation / SBS format, quality / source is unknown." | verified |
| F27 | ADSBHub terms | feed to get; no use restrictions | https://www.adsbhub.org/howtogetdata.php | 2026-11-13 | "There are no restrictions on how the users will use the data. Everybody is allowed to publish the data for free or to use it for commercial purposes." | verified |
| F28 | AvioADSB licence | CC BY-NC 4.0 | https://avioadsb.org/docs/api | 2026-11-13 | "Free for personal and research use, CC BY-NC 4.0." | verified |
| F29 | AvioADSB near ZSSS | 0 aircraft within 100 nm at 20:33Z | https://avioadsb.org/v1/point/31.198104/121.33426/100 | 2026-11-13 | `{"ac":[],"msg":"No error",…,"total":0}` | verified (own probe; night) |
| F30 | 2021 CCTV case | "hundreds of sets" seized nationwide | https://www.thepaper.cn/newsDetail_forward_15170866 | 2026-11-13 | "查获数百套境外机构在我国违规布设的设备" | secondary (state-media repost) |
| F31 | 2021 treatment of volunteers | devices withheld, "criticism and education" | same | 2026-11-13 | "国家安全机关依法暂扣了其持有的设备，并进行了严肃批评教育" | secondary |
| F32 | 2021 device described | ADS-B receiver; data to servers abroad | same | 2026-11-13 | "这套设备叫ADS_B信号接收设备，可以跟踪所有配备该系统的飞机" | secondary |
| F33 | FR24 app unavailable in China | November 2021 | https://www.rfa.org/mandarin/Xinwen/wul1105c-11052021053208.html | 2026-11-13 | "现时中国境内不能下载服务应用程式" | secondary |
| F34 | 2024 MSS statement | nationwide crackdown; penalties; Bohai, East and South China Sea provinces | http://www.ce.cn/xwzx/shgj/gdxw/202401/06/t20240106_38856111.shtml | 2026-11-13 | "这些境外机构在我国渤海、东海、南海周边省份大量投放此类设备"; "依法对有关人员进行处罚" | secondary (state-media repost of MSS WeChat) |
| F35 | MSS cites laws | Counter-espionage Law, Data Security Law | same | 2026-11-13 | "《中华人民共和国数据安全法》规定，任何组织、个人收集数据，应当采取合法、正当的方式" | secondary |
| F36 | Counter-espionage Law Art. 4(3) | supplying data concerning national security to foreign organisations = espionage | http://www.npc.gov.cn/c2/c30834/202304/t20230426_429064.html | 2026-11-13 | "窃取、刺探、收买、非法提供国家秘密、情报以及其他关系国家安全和利益的文件、数据、资料、物品" | verified |
| F37 | Data Security Law Art. 2 | applies to processing abroad that harms PRC security | http://www.npc.gov.cn/npc/c2/c30834/202106/t20210610_311888.html | 2026-11-13 | "在中华人民共和国境外开展数据处理活动，损害中华人民共和国国家安全…的，依法追究法律责任" | verified |
| F38 | Data Security Law Art. 32 | lawful collection | same | 2026-11-13 | "任何组织、个人收集数据，应当采取合法、正当的方式，不得窃取或者以其他非法方式获取数据。" | verified |
| F39 | "Important data" definition | Order 790 Art. 62(4) | https://www.gov.cn/gongbao/2024/issue_11646/202410/content_6980863.html | 2026-11-13 | "重要数据，是指特定领域、特定群体、特定区域或者达到一定精度和规模…可能直接危害国家安全…的数据" | verified |
| F40 | Radio Regulations Art. 27(2) | receive-only stations exempt from licence | https://www.gov.cn/gongbao/content/2016/content_5148745.htm | 2026-11-13 | "但设置、使用下列无线电台（站）的除外：…（二）单收无线电台（站）" | verified |
| F41 | Radio Regulations Art. 41 | no deliberate reception outside the licence; no dissemination or use of unintentionally received information | same | 2026-11-13 | "不得传播、公布或者利用无意接收的信息" | verified |
| F42 | CAAC important-data catalogue | required by the CAAC measures; not found publicly | http://www.caac.gov.cn/XXGK/XXGK/GFXWJ/202503/P020250331376967414116.pdf | 2026-11-13 | "制定民航领域重要数据和核心数据目录" | verified (measures) / unverified (catalogue content) |
| F43 | China uses 1090ES | transport and general aviation | http://www.caac.gov.cn/XXGK/XXGK/ZFGW/201601/P020160125652058562641.pdf | 2026-11-13 | "运输航空采用国际民航组织标准的 1090ES 数据链。" | verified |
| F44 | ADS-B OUT target | full operation by end 2020 | same | 2026-11-13 | "到 2020 年底，实现 ADS-B OUT 全面运行" | verified |
| F45 | Chinese fleet ADS-B equipage (sample) | 468/565 adsb_icao, 415 v2 (02:00Z) | ADSBx sample 2026-11-01 | 2026-11-13 | (data) | verified (own measurement) |
| F46 | VariFlight redistribution | needs written contract | https://dataworks.variflight.com/terms-of-use/ | 2026-11-13 | "absent a formalized, written contract … they shall not use any automated means to scrape, cache for unauthorized redistribution, repackaging, or commercially resell our proprietary APIs, ADS-B streams" | verified |
| F47 | VariFlight ADS-B area query | airborne flights only | https://dataworks.variflight.com/products/real-time-aircraft-tracking-adsb/ | 2026-11-13 | "Current airborne flights within the selected area" | verified |
| F48 | VariFlight pricing | quote / plans; 14-day trial | https://dataworks.variflight.com/about-us/faq/ | 2026-11-13 | "We offer flexible plans: pay-as-you-go for small-scale users, and enterprise subscriptions" | verified |
| F49 | Aireon claim | "gate-to-gate, surface-to-space" | https://aireon.com/our-technology | 2026-11-13 | "AireonSTREAM provides global, gate-to-gate, surface-to-space ATS surveillance quality data" | verified (as a vendor claim; performance at ZSSS unverified) |
| F50 | FlightAware AeroAPI | Personal: personal/academic derivative works; Aireon only in Premium | https://www.flightaware.com/commercial/aeroapi/ | 2026-11-13 | "Storage and distribution of derivative works for personal or academic purposes only"; "Aireon Space-Based ADS-B* Not included in Personal Not included in Standard Included in Premium" | verified |
| F51 | Spire pricing | custom | https://spire.com/plans/ | 2026-11-13 | "Contact us directly for custom pricing." | verified |
| F52 | Shanghai Airport site statement | no redistribution without written authorisation | https://www.shanghaiairport.com/wzaqzc/index.html | 2026-11-13 | "非经本公司书面授权，任何人不得将本网站的交易资讯、行业资讯、服务资讯等讯息进行再传播。" | verified (read with WebFetch; not cached; curl got HTTP 200 on re-check, verify_licences_law.md A43) |
| F53 | Shanghai Airport flight widget fields | airline, flight number, scheduled time, origin/destination, terminal; gate/stand not seen | https://www.shanghaiairport.com/ | 2026-11-13 | "航空公司 … 主航班号 … 候机楼" (template) | verified (fields); gate/stand unverified |
| F54 | VariFlight-FlightAware data exchange | strategic cooperation announced 2016-11-02 | https://www.traveldaily.cn/article/108758 | 2026-11-13 | "飞常准将推进与FlightAware之间的航班跟踪数据交流" | secondary (old) |
| F55 | Copyright Law Art. 5 | laws and regulations not protected | https://ipr.mofcom.gov.cn/law/detail.shtml?id=1969 | 2026-11-13 | "本法不适用于：（一）法律、法规…及其官方正式译文" | verified |

## 8. Risks

- **R1: no observed traffic.** Every live, replay and stand-learning feature inherited from sfo3d depends on ADS-B
  coverage that does not exist at ZSSS. Plan the product around option 1 of section 6.
- **R2: legal exposure in the PRC** for anyone who hosts or feeds a receiver (2021 and 2024 MSS actions). Never solicit
  it.
- **R3: the DSL's extraterritorial clause** (Art. 2) and an unpublished CAAC important-data catalogue. The risk of
  publishing aggregated PRC flight tracks cannot be fully assessed. Keep displays transient and avoid building a
  dataset of Chinese flight tracks in the public repository (inferred).
- **R4: terms drift.**
  - adsb.lol went from "free" to metered (500 requests/day) between 2026-09-24 (sfo3d's capture) and 2026-11-13. It
    publishes no start date.
  - airplanes.live went contributor-only in Sep 2026.
  - OpenSky tightened its terms.
  - Re-check all terms at build time. The sfo3d relay design (1 Hz) is over quota.
- **R5: mixing licences.** ODbL (adsb.lol), non-commercial (adsb.fi, AvioADSB CC BY-NC, AeroAPI Personal),
  no-redistribution (ADSBx, VariFlight, OpenSky, FR24) and airport terms cannot all be combined in one published
  artefact. Keep per-record provenance, as in sfo3d.
- **R6: GCJ-02.** Chinese commercial sources may return GCJ-02 coordinates (inferred). That would put aircraft
  hundreds of metres off in a WGS-84 scene. Check this before any integration.
- **R7: misleading "observed" labels.** ADSBx and other aggregators contain `type: other` records of unknown origin,
  with impossible fields (ground at 370 kt). Treat only `adsb_icao` (and perhaps `mlat`) as observed positions.
- **R8: blocked or slow access from this sandbox.**
  - The shanghaiairport.com home page, data.caac.gov.cn, ncac.gov.cn and web.archive.org reset the connection. (The
    shanghaiairport.com statement page answered HTTP 200 on re-check.)
  - airplanes.live, adsb.fi and SCMP return 403.
  - Some facts above are therefore secondary or unverified.
- **R9: the owner's privacy.** Any key request (adsb.lol adhoc form, VariFlight, FlightAware) needs the owner's
  details. Do not use them without the owner's consent. Use a generic User-Agent.

## 9. Questions for the owner

1. **Is a scheduled or inferred "simulated Hongqiao" acceptable as the main mode?** It would be clearly labelled, with
   observed traffic only when some is present. Or is live observed traffic essential? If it is, ZSSS needs a paid
   contract, or option 6.6 (another airport).
2. **Would you consider a paid feed** (VariFlight DataWorks or FlightAware Premium / Aireon)? It would mean a
   contract, a budget, and recorded data kept out of the public repository. Do you want us to ask vendors about ZSSS
   coverage below 1,000 ft and on the ground, and about their datum?
3. **Which schedule source may we use** for the simulation: licensed (OAG or Cirium), manual from public timetables, or
   purely synthetic rates?
4. **Do you accept the residual legal risk** of showing PRC civil traffic from foreign open data (DSL Art. 2 and an
   unknown important-data catalogue)? Or should sha3d avoid live PRC data altogether?
5. **adsb.lol quota.** Do you accept 1 poll every 3 minutes, which fits 500 requests/day? Or do you want a sponsor key
   (EUR 20-50 a month)? Its value at ZSSS is near zero (C1-C5).
6. **May we write to airplanes.live** (contact with a project description), or ask OpenSky for an operational
   licence? Either would need the owner's identity.
7. **May we use Shanghai Airport Authority FIDS data** as manually read reference facts, for example terminal per
   airline? Its statement forbids redistribution without written authorisation. Or should we request that
   authorisation?

## 10. Files

- This report: `sha3d/docs/phase0/adsb.md`.
- Caches:
  - `sha3d/refs/cache/adsb_terms/`, 31 sources: provider pages, the OpenSky coverage JSON for 2026-11-12, two ADSBx
    sample snapshots, and probe logs.
  - `sha3d/refs/cache/china_law/`, 19 sources: laws, CAAC PDFs and news pages.
  - Each has a `SOURCES.json`. `adsb_terms/SOURCES.json` also lists `read_not_cached` (WebFetch-only and 403 pages).
- Redistributable: only our own probe logs, the PRC legal texts (Copyright Law Art. 5) and the ODbL README and licence
  texts of globe_history. **Keep everything else local.** This includes the ADSBx samples and the OpenSky coverage data,
  and any per-record listing from them: public docs carry aggregates only (ADSBx AUP; OpenSky Terms 3(i) and 3(iii)).
- Scripts used: kept in the session scratchpad and run with `python3 -I`; not part of the repository.
  - `os_cov.py`: OpenSky coverage cells.
  - `adsbx_snap.py`, `adsbx_other.py`, `adsbx_grid.py`, `adsbx_cn.py`: ADSBx sample analysis.
  - `mk_sources.py`: writes the `SOURCES.json` files.
