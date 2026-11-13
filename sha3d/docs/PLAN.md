# SHA Live 3D (Shanghai Hongqiao, ZSSS): Phase 0 plan

Status: Phase 0 (research and plan only), 2026-11-13. There is no app code, no models and no renders yet. Two findings
stop the work here until the owner decides (§6):

1. **No open ADS-B source sees Hongqiao at any hour** (§3). Live observed traffic is not possible from open data, so
   the scope must change (Q1).
2. **The working ARP is contradicted.** The OurAirports point given in the brief is 174 m from the AIP ARP, and the AIP
   itself was read only in an unofficial mirror (§1). The brief says to stop and ask (Q0).

This is a sibling of `sfo3d/` (SFO Live 3D). The fork base is sfo3d commit **e3218d6**. It does not modify `sfo3d/`,
`pc12/` or `hwd3d/`. Anything that belongs in sfo3d goes to `docs/requests_to_sfo3d.md`. The Hayward fork
(`origin/claude/hwd-live-3d` at eb34f7d) was read as a pattern (§4, Q7).

Evidence: eight research reports, two adversarial verification reports and one plan critique, all in `docs/phase0/`:

| Report | Contents |
|---|---|
| `aip.md` | CAAC AIP |
| `field.md` | Layout, statistics |
| `geo.md` | OSM, GCJ-02 check |
| `terrain.md` | DEM, land cover, imagery |
| `adsb.md` | Feeds, terms, China background |
| `law.md` | PRC law, ATC audio, trademarks |
| `fleet.md` | Airlines, type mix, models |
| `arch.md` | Reuse map |
| `verify_official.md`, `verify_licences_law.md` | Adversarial verification |

Where a verifier corrected a research report, the correction wins. The reports carry errata headers.

Status labels:

| Label | Meaning |
|---|---|
| **verified** | Primary or official source read. |
| **AIP (mirror)** | AIP value read in an unofficial mirror (EFF 2026-07-08). The official eAIP needs a login (Q2). |
| **secondary** | Wikipedia, OurAirports, news. |
| **obs** | Our measurement. |
| **inf** | Inferred. |
| **unverified** | Not established. |
| **contradicted** | Sources disagree. |

---

## 1. Facts and their status

Checked on 2026-11-13 unless the row says otherwise. Two sources recur, so they are given here once:

- **eAIP** = `https://www.eaipchina.cn/` (official, CAAC).
- **Mirror** = `https://chart.wuhanqing.cn/Terminal/ZSSS-上海虹桥/AD 2.24 Charts related to an aerodrome.pdf` and the
  chart PDFs beside it (unofficial copy of AIP EFF 2026-07-08, no licence, kept local only).

AIP content appears here as short cited facts only. Whole AIP lists are kept local (Q2).

| Fact | Value | Source URL | Status |
|---|---|---|---|
| Identity | **ZSSS / SHA, "SHANGHAI/Hongqiao" (上海/虹桥).** No source contradicts the owner's choice. | eAIP `…/eaip/airportChart/listPublish`; SAA code list `https://www.avinex.com/cn/js/Avinex/flight/oldFlight.js` | verified |
| Official eAIP | Free, but needs a **registered login**, so AD 2 ZSSS was **not** read. AMDT 11/2026 is effective 1600 UTC 28 Oct 2026. AMDT 12/2026 (1600 UTC 25 Nov = 26 Nov local) changes the WDI positions at ZSSS. No licence or terms are published. The site shows "Trial Phase: Data Unavailable for Formal Operation. Verify Before Use" and has an "AIP China" purchase module. | eAIP; NOTAM summary `…/eaip/homeFile/NOTAM_SUMMARY/NOTAM%20Summary%20In%20Nov.2026/2026-11.zip` | verified |
| AIP ARP | **N31°11.8′ E121°20.1′**, "Centre of RWY18L/36R". Printed only to 0.1′ (about ±90 m), and apparently truncated. | Mirror AD 2.2 | AIP (mirror) |
| Brief's working ARP | OurAirports 31.198104, 121.33426 is **174 m from the AIP ARP** (bearing 336°) and 195 m from the OSM centre of RWY18L/36R (31.19785, 121.33629). It is not the AIP ARP. Wikipedia (about 200 m east) and X-Plane (about 160 m) give other points. → **Q0.** | `https://davidmegginson.github.io/ourairports-data/airports.csv` | **contradicted** |
| Horizontal datum | AD 2 states none. GEN 2.1 reportedly moved to WGS-84 in 2012 (ICAO paper returned HTTP 403). OSM at ZSSS is WGS-84 (row "GCJ-02 check"). | `https://www.icao.int/APAC/Meetings/2012_AAITF_7/IP03%20China_Transition%20to%20WGS84.pdf` | unverified |
| Elevation / variation | AD ELEV **3.0 m**; VAR 5°46′W (2017), −42″/yr. The height datum is unstated, perhaps Wusong (= 1985 national + 1.680 m). DEM 1.5 m (EGM2008); geoid N = +11.24 m. | Mirror AD 2.2; `https://cdn.proj.org/us_nga_egm08_25.tif`; terrain.md | AIP (mirror); inf |
| Hours / night | AD **H24**. No landings on 18R/36L 1600–2300 UTC (except alternates). No towing across runways 2200–1600 UTC. **No scheduled flights 00:00–06:00 local**; delays and diversions are allowed. Planned in 2010; in force per shhqcbd 2012 and caacnews 2023. | Mirror AD 2.3; `https://news.sina.cn/sa/2010-06-26/detail-ikmxzfmk0135400.d.html`; verify_official.md | AIP (mirror); secondary |
| Current NOTAMs | RWY 18L/36R closed 1700–2200 UTC daily, 10–29 Nov 2026. Stand 267 closed 14–21 Nov. Works at TWY A/K1 (SUP 21/26). | eAIP NOTAM summary (above) | verified |
| RWY 18L/36R (east) | 3400 × 45 m, asphalt with concrete ends, 177.34° true. THR and END each displaced 100 m. TORA 3300, LDA 3200. **Threshold coordinates not published** ("Nil"). | Mirror AD 2.12/2.13; OSM way 16714125 (177.34°) | AIP (mirror) |
| RWY 18R/36L (west) | 3300 × 60 m, concrete, 177.33° true. THR displaced 300 m, END 150 m. TORA 3150, LDA 2850. Opened 11 Mar 2010. | Mirror AD 2.12; `https://www.avinex.com/xwg/info_itemid_19498.html` | AIP (mirror); verified (date) |
| Runway layout | **Close parallels 365 m apart, north ends aligned** (AIP). OSM: 363.6–365.4 m; OSM north ends 17 m apart in latitude. Order W→E: TWY C, 36L, TWY B, 36R, TWY A. Usual mode: east runway landings, west take-offs (东落西起). | Mirror; eAIP sheet `…/eaip/airportChartFile/ZSSS/en/ZSSS上海虹桥.pdf`; `https://www.caac.gov.cn/PHONE/XWZX/MHYW/201003/t20100316_12580.html`; caacnews 2021 (below) | AIP (mirror); verified (order); secondary (mode) |
| Lighting | PALS CAT I at all four ends. PAPI 3°. No TDZ lights. RCLL, REDL, RWSL (THL and REL). Stop bars on rapid exits. | Mirror AD 2.14 | AIP (mirror) |
| Taxiways | Main designators A, B, C, D with numbered links. Runway crossings H1–H7. Rapid exits from A and B (e.g. A2, A3, B3, B4). End-around routes N and S, 23 m wide (caacnews). AIP: spans < 36 m normal, 36–65 m restricted, ≥ 65 m forbidden. About 60 designators in all. | Mirror AD 2; `http://www.caacnews.com.cn/1/3/202110/t20211009_1331872.html` | AIP (mirror); secondary |
| Stands | **161 designators ≈ 155 physical stands** (6 overlays or alternatives). Series 1xx (T1), 2xx (T2), 3xx (incl. business 310–312), 4xx, 5xx, 6xx, plus temporary TP01–TP08. All taxi-in, push-back. The largest is 248 (B747-8). **No stand coordinates in the AIP.** | Mirror APDC `…/ZSSS-2P-1-APDC.pdf` | AIP (mirror) |
| Contact vs remote | **54 stands have VDGS** (13 at T1, 41 at T2). caacnews gives 54 contact stands, so the bridge stands are inferred to be the VDGS stands. That leaves about **101 remote stands**. T2 in 2010: 43 bridges (CAAC) vs 45 bridges and 8 MARS stands (Shanghai government). SAA maps imply 45 T2 bridge gates against 41 VDGS stands. Bus gates: T1 T03–T08, T16–T19, T22–T25; T2 41–45, 51–55. Gate→stand rule Txx→1xx, nn→2nn. | Mirror AD 2; `http://www.caacnews.com.cn/special/2023nzt/7624/2020mhcy1/2020cybzmhj/202308/t20230818_1369755.html`; `https://www.shanghai.gov.cn/nw9822/20200906/0001-9822_395090.html`; `https://www.avinex.com/uploadfiles/2023/10/20231016170510286.jpg` | inf; **contradicted** (bridge count) |
| Stands in OSM | **164 `parking_position` nodes with ref.** 149 refs match the AIP. 15 are OSM-only (238A, 239, 240A, 258, 259A, 301–309, 604). The AIP has 12 designators with no OSM node (the E/C overlays, 414–416, 514–516). 159 of 164 also appear in the X-Plane Gateway (median 5.8 m apart). The 2026 APDC says "Stand number adjusted". | `https://api.openstreetmap.org/api/0.6/map?bbox=121.300,31.168,121.362,31.226` (2026-11-13); `https://gateway.x-plane.com/apiv1/scenery/107152` | obs |
| Terminals | **T1:** renovated 2014–2018, planned 130,000 m² (SAA 2014); international/HMT at islands A/B, Spring etc. at D; gates T01–T27. **T2:** opened 16 Mar 2010, 362,600 m²; gates 21–75. Airlines per terminal come from an undated SAA page. | `https://www.avinex.com/xwg/info_itemid_18946.html`, `…/info_itemid_19498.html`, `https://www.avinex.com/airlines/index.html` | verified (dates); secondary (area) |
| Tower | OSM `aircraft_control` node 3342630333 (31.19667, 121.34153, east side) = AIP obstacle "Control TWR", 111° MAG / 520 m from the RWY18L/36R centre, **47 m**, lit. OSM also has two untyped towers in the south-west (added 2026-11-06), possibly a West TWR. Form and year unknown. | `https://api.openstreetmap.org/api/0.6/node/3342630333`; Mirror AD 2.10 | secondary (verifier-corrected); unverified (west tower) |
| Main frequencies | ATIS 132.25. GND(E) 121.6, GND(W) 121.9. TWR(E) 118.1, TWR(W) 118.65. Shanghai APP 125.4 / 126.65. Whether E/W means one cab or two is unknown. | Mirror ADC chart | AIP (mirror) |
| Movements | 2023 **266,813**; 2024 **275,288**; 2025 **282,692** (774.5/day). Jan–Sep 2026: 783.4/day (monthly 757–806). Winter 2026/27 plan: 802/day. 2025 international 6,978 + HMT 10,905 (CAAC) vs 6,747 + 10,787 (SIAC); the totals agree. | CAAC `https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/P020260226360830390937.xlsx` (and the 2024/2023 files, field.md); SIAC `https://pdf.dfcfw.com/pdf/H2_AN202610141830452855_1.pdf`; `http://news.sina.com.cn/minsheng/2026-10-24/doc-iniwhxpu1437622.shtml` | verified; **secondary** (802 plan); contradicted (route split, minor) |
| Capacity, hourly profile | Declared 43/h (2011). The rise to 48→50/h (2023) is unconfirmed. Observed peak 59/h (2021). **No published hourly profile**; the 06–24 mean is about 44.6/h (inf). | `https://www.caac.gov.cn/XXGK/XXGK/ZFGW/201602/t20160224_29138.html`; caacnews 2021 | verified; unverified; inf |
| Business aviation | FBO opened 2010: terminal 3,100 m², hangar 4,500 m², 3 stands; then a SAA + Hawker Pacific JV. Current operator unverified. | `https://www.avinex.com/xwg/info_itemid_19492.html` | verified (2010) |
| GCJ-02 check | **OSM at ZSSS is WGS-84.** OSM − Sentinel-2: dx −3.1 / −1.6 m, dy −1.0 / −0.1 m, ±0.7 m (two scenes, 54 and 43 straight runs). The predicted GCJ-02 shift is about 484 m (+434 m E, −214 m N). An NDVI search over ±900 m is minimal at (0,0). Absolute accuracy is limited to about ±10 m by the Sentinel-2 geolocation spec. Changesets name only Bing, Maxar, Esri and Mapbox. | `https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_51RUQ_20261014_0_L2A`; `docs/phase0/geo_overlay.jpg` | obs |
| OSM state | Aerodrome relation 21913346 was re-created **2026-11-06**, so pin by ID and date. Missing: jet bridges, surface polygons, threshold nodes, hold designators, building heights. Only 27 % of taxiway ways have a ref. Some centrelines are 5–13 m off the imaged pavement. **6 military or armed-police elements lie 1.2–3.3 km from the ARP** (ids withheld). | `https://api.openstreetmap.org/api/0.6/relation/21913346/full`; `tools/law/osm_sensitive.py` | obs |
| Fleet | Hub carriers China Eastern (MU), Shanghai Airlines (FM) and Juneyao (HO); Spring (9C) has a base. These four hold 75 % of airline–destination pairs. International routes are few (Haneda, Gimpo, Songshan, Hong Kong, Macau). **Type mix (estimate, not a measurement):** A320 family 45–55 %, 737 23–37 %, wide-bodies 14–26 %, C919 1–5 %, C909 (= ARJ21, ICAO AJ27) 0–2 %. | `https://en.wikipedia.org/wiki/Shanghai_Hongqiao_International_Airport`; airline filings; ICAO Doc 8643 (fleet.md §6) | secondary / inf |
| ATC audio | **No lawful verified ZSSS source.** LiveATC returns 403 to automated reads; a 2024 note says it lists no Chinese airport (unverified). PRC Radio Regulations Art. 41: station users must not deliberately receive signals outside their licence, nor spread, publish or use *unintentionally* received information. Art. 72: fines up to CNY 30k, or 30–100k if serious. Art. 75: foreign monitoring inside the PRC. | law.md §5; verify_licences_law.md | verified (law); unverified (LiveATC) |

## 2. Data inventory and licences

| Data | Source | Licence | Redistribute? | Use / status |
|---|---|---|---|---|
| Runways, stands, frequencies, lighting, hours | CAAC eAIP AD 2 ZSSS (official, login) and an unofficial mirror | none published; treat as all rights reserved | **no**; short cited facts only (Q2) | Mirror PDFs and derived tables are local in `refs/cache/aip/`. Earlier commits put whole lists in `aip.md`; they are now cut to summaries, but remain in git history (Q2). |
| Airfield geometry, 164 stand nodes, taxiways, buildings, tower | OpenStreetMap API, 2026-11-13 | ODbL 1.0 | yes, after the sensitive-feature filter (Q3) | Main geometry source. The extract is local until filtered. |
| Optical imagery | Copernicus Sentinel-2 L2A (Earth Search COGs), 2026-10-14 and 2026-02-21 | Sentinel Data Legal Notice: reproduction, distribution and adaptation free | yes: "Contains modified Copernicus Sentinel data 2026" | Committed crops (`refs/cache/s2/`, 6.8 × 7.9 km = 53 km²; see R3). Alignment and ground colour; 10 m is too coarse for markings. |
| SAR imagery 0.35 m | Umbra Open Data, 2024-06-02 | CC BY 4.0 | yes, with attribution | Outlines only (radar; GEC about 3–4 m east of OSM). Q6. |
| Historical optical 2.5–5 m | CNES SPOT World Heritage, 2011–2013 | **contradicted** (Etalab 2.0 vs non-commercial) | no until resolved | Q6. |
| DEM | Copernicus DEM GLO-30 (N31E121, EGM2008) | COP-DEM-GLO-30-F (free; notice required) | yes (crop, with notice) | Airfield heights are airport-edited planes: surroundings only. Crop extent per Q3. |
| Land cover | ESA WorldCover 2021 v200 | CC BY 4.0 | yes | Surroundings materials (airfield grass is misclassified as cropland). |
| Cross-check geometry | X-Plane Gateway 107152; OurAirports | unverified (Gateway terms unread; OurAirports TLS failed) | no | Cross-check only. |
| Statistics, airport and press pages | CAAC bulletins, SIAC reports, SAA pages and gate maps, caacnews (its terms forbid downloads), Sina, Shanghai government | none published | no (facts and short quotes only) | Denominators, layout facts. |
| Shanghai Airport flight board | SAA FIDS | the statement forbids redistribution without written authorisation; blocked by a WAF | no | Not used. Q10. |
| Photos and text | Wikipedia (CC BY-SA 4.0), Wikimedia Commons (per file) | per file | text yes with attribution; photos reference only | Type-mix sample B, livery and tower reference. |
| ADS-B archive | adsb.lol globe_history (GitHub releases) | ODbL 1.0 | yes under ODbL; committing PRC traffic is Q3 | Coverage (§3). Committed: the filtered extracts (two foreign overflight traces) and the 1° grid. |
| ADS-B live | adsb.lol API | ODbL 1.0; **500 requests/day per IP without a key** (published). The window is contradicted: a fixed 24 h bucket (OpenAPI) vs 00:00 UTC (docs). | yes | Near-zero value at ZSSS. Our first run broke this quota (§3); now one poll per 180 s. |
| ADS-B live | adsb.fi | personal non-commercial; no licensing | **no** | Local measurement only. |
| ADS-B live | OpenSky | written agreement needed for any automated or live use; identifiers anonymised in publications | **no** | One 2.4 h probe, then dropped (§3). |
| ADS-B samples | ADS-B Exchange readsb-hist 2026-11-01 | AUP: no publishing or redistribution; samples "for testing and evaluation" | **no** | Evaluated in aggregate only. Per-record details are local (cut from `adsb.md`). |
| ADS-B live | airplanes.live | contributors only since Sep 2026 (secondary) | – | Not usable. |
| Commercial feeds | VariFlight DataWorks (written contract, no redistribution: quoted); FlightAware AeroAPI (Premium ≥ $1,000/month; Personal tier personal/academic only: quoted); Aireon, Spire (terms not read) | contract | **no** | Only path to observed airborne traffic (Q1 B). |
| Weather | a ZSSS METAR/TAF source | **not yet chosen or checked** | – | Runway mode in Q1 A. Phase 1. |
| Marking standards | ICAO Annex 14 Vol I (ICAO copyright, sold); the CAAC aerodrome standard (designation unverified, "MH 5001?") | not obtained | quote only | Needed for ICAO/CAAC markings (Q11). |
| Aircraft models | sfo3d's 23 converted models (FlightGear GPL-2.0; A380 has a CC BY-NC caveat) | per model | as sfo3d | Covers every expected SHA type except C919 and C909. |
| COMAC models | Sketchfab "C919 B" (CC BY 4.0, also in GitHub `AlstonZhuang/comac`), "ARJ21" (CC BY 4.0, 608k faces, needs an account) | CC BY 4.0, but **uploader-declared** | yes if accepted | Q5. |
| COMAC dimensions | COMAC ACAPs (C919 R9, C909 R13) | "shall not be reproduced, quoted, disclosed or used … for any purposes" without written authorisation | **no** | Local only. Whether even measurement-only use is acceptable is Q5. Figures quoted earlier in `fleet.md` are removed (still in git history). |
| Liveries | own re-drawings | trademarks of the airlines and COMAC | as sfo3d (non-commercial notice) | Q5. |
| Google / Baidu / Amap | – | licensed | **never** for geometry or texture | Allowed only as visual reference, logged per use (Q6). Baidu and Amap imagery is GCJ-02-offset. Not used so far. |

## 3. ADS-B coverage and type mix: measured

**Method.**

| Tool | What it does |
|---|---|
| `tools/adsb/globe_scan.py` | Streams adsb.lol's daily `prod` archives (3.3–3.6 GiB per day, every aircraft worldwide) and keeps every trace within **150 km** of ZSSS. |
| `tools/adsb/globe_grid.py` | Counts distinct aircraft per 1° cell over East Asia (`docs/phase0/coverage_map_20261112.png`). |
| `tools/rec/live_rec.py` | Polls the live APIs: adsb.lol and adsb.fi within 60 NM; OpenSky over a 30.2–32.2 N × 120.2–122.5 E box. |

**About the live recorder.**
- The first run (19:08–21:21Z on 13 Nov) polled adsb.lol every 15 s: about 507 keyless requests in 2.2 h. That
  **broke adsb.lol's published 500/day quota**. It drew 6 HTTP 429s and 20 connection resets, plus one more 429 after
  the fix. We treat the published quota as binding.
- Since 21:21Z the recorder polls adsb.lol every 180 s. adsb.fi stays at 15 s, within its 1 per second limit.
- OpenSky was dropped at about 21:30Z, because its Terms require a written agreement for automated use.
- The recorder runs about 28 h more, locally only. None of its raw data is committed.

**Daily results.** UTC days cover every local hour (UTC+8).

| Window | Source | Aircraft within 150 km | Airborne < 10,000 ft | Ground | SHA movements in window | Fraction seen |
|---|---|---|---|---|---|---|
| 2026-11-08 UTC day | adsb.lol `prod` | 2 of 66,788 traces (3 cruise points: HIM226 A332 FL391 at 147 km; VJC982 A321 FL311 at 147 and 142 km) | 0 | 0 | about 780–800 | **0 %** |
| 2026-11-10 UTC day | adsb.lol `prod` | 0 of 75,360 traces | 0 | 0 | about 780–800 | **0 %** |
| 2026-11-12 UTC day | adsb.lol `prod` | 0 of 73,533 traces | 0 | 0 | about 780–800 | **0 %** |
| 2026-11-13 19:08–21:23Z (03–05 local) | adsb.lol / adsb.fi / OpenSky live | 1 / 2 / 0 (two B789s at FL300–FL390, 53–85 km away) | 0 | 0 | night (none scheduled) | – |
| 2026-11-12 | OpenSky's own coverage data | nearest cell 233 km away, at ≥ 6.5 km altitude | 0 | 0 | – | – |
| 2026-11-01 sample | ADS-B Exchange (aggregate) | nearest real ADS-B position 106–119 km away, at ≥ 6,850 ft | 0 | 0 | – | – |

**By local hour (UTC+8), all three archive days.**

| Local hour | 00–04 | 05 | 06 | 07–23 |
|---|---|---|---|---|
| Ground positions | 0 | 0 | 0 | 0 |
| Airborne < 10,000 ft | 0 | 0 | 0 | 0 |
| Airborne ≥ 10,000 ft (distinct aircraft, within 150 km) | 0 | 1 (9 Nov) | 1 (9 Nov) | 0 |
| SHA movements (inf: none scheduled 00–06; mean about 44.6/h 06–24) | about 0 | about 0 | about 45 | about 45 each |
| Fraction of SHA movements seen | – | – | 0 % | 0 % |

- The `prod` release was scanned for all three days. For 12 Nov the **MLAT-only release** was also scanned: 0 of
  36,826 traces within 150 km. It is a single `.tar`, which made the first attempt fail. The staging release of 12 Nov
  is being scanned and will be appended; it is expected to duplicate `prod`.
- **Coverage map, 12 Nov.**
  - The nearest covered area is a feeder cluster around Hefei/Nanjing, at 31–32 N and 116–119.9 E. Low-level aircraft
    appear there only at 116–118 E.
  - Other mainland low-level clusters are around Beijing and Xi'an.
  - The 29–33 N band east of 120 E (Shanghai) is empty. Further south, on the Zhejiang coast (26–28 N, 120–121 E),
    only airborne aircraft appear.
  - Ground positions appear in the 1° cells containing Hong Kong, Shenzhen and Macau (556 distinct aircraft) and
    Taipei Taoyuan/Songshan (332). They also appear over Korea and Japan, and in two isolated mainland cells
    (1 aircraft each).
- **Why** (adsb.md):
  - Since 2021, PRC state security has seized volunteer receivers that feed foreign sites ("hundreds of sets", CCTV
    2021; MSS statement 2024).
  - Low-level traffic is visible only within about 30–100 km: about 29–38 km for an aircraft on the ground, about
    100 km at 1,000 ft. The nearest non-PRC location is the Korean Ieodo platform, about 378 km away, with no receiver
    known there. From Korean sites only cruise-level traffic over ZSSS would be in range.
- **Type mix:** it cannot be measured from ADS-B. §1 gives an estimate from route pairs × fleets (A) and a photo sample
  (B). Ways to measure it are in Q9.
- **Conclusion: SHA cannot show "live traffic at real positions" from open data.** This is the case the brief
  anticipated. Options are in Q1.

## 4. Architecture: what to reuse and what is new

The stack is the same as sfo3d:
- plain ES modules and a custom WebGL2 renderer, or the three.js `live3.html` path (Q7);
- offline Python data tools;
- a stdlib Python relay;
- a snapshot/replay artifact.

Each forked file records its donor and commit in its header.

**Donors.** The brief names sfo3d e3218d6 as the base and Hayward as a pattern, so this plan defaults to sfo3d only.
arch.md §0 recommends otherwise: also fork hwd3d @ eb34f7d, which has already de-SFO-ed these pieces:
- the geo frame with degree headings;
- `site.js` and `grid.js`;
- `render_env.js`;
- the generic-User-Agent relay;
- `build_pack.py` and `replay_shim.js`;
- `livetest.mjs`.

That route would be faster. It is offered as Q7.

| Area | Reuse (copy and adapt) | New for SHA |
|---|---|---|
| Geo frame | `js/geo.js` pattern (hwd3d's version if Q7 allows) | Origin per **Q0**. Runway grid 177.34° (18L/36R) and 177.33° (18R/36L) true; close parallels about 365 m apart. Vertical datum chain: AIP/Wusong → EGM2008 → ellipsoid (N = +11.24 m). |
| Renderer, shaders, environment | `gl.js`, `renderer.js`, `js/shaders/*`, `js/env/*` | The METAR decoder must cut ICAO trend groups (NOSIG/BECMG/TEMPO). The fixed KSFO report minute goes. ZSSS METAR source (Phase 1). |
| Markings and signs | `markings.js`, `signs.js`, ground-shader glyph atlas | **One ICAO Annex 14 / CAAC parameter table** shared by the GLSL and three.js paths, replacing the FAA constants. Every parameter is still **unverified**: arch.md §4 was written from memory, and the standards are not yet obtained (Q11). |
| Airfield data | builder pattern of `tools/build_*` | Builders from OSM (filtered), AIP facts and Sentinel-2/Umbra. No NAIP, FAA NASR or flysfo. |
| Stands, jet bridges, GSE | `gates.js` (bridges, VDGS, GSE), stand model, `standFits` classes | 155 physical stands: 149 placed from OSM refs that match the AIP; 6 (414–416, 514–516) without an OSM node stay unplaced or `inf` until the official chart; 15 OSM-only refs to reconcile. Class from AIP span limits. Bridges at the 54 VDGS stands (`inf`). Remote stands with buses and stairs. |
| Traffic and physics | `traffic.js`, `ground.js` (solid planforms), heading inference | Depends on Q1. Either a schedule-driven simulator feeding the same pipeline, every aircraft tagged *scheduled/inferred*, or a licensed-feed adapter. Never unlabelled synthetic traffic. Only `adsb_icao` (and MLAT) records may count as observed, never `type: other`. |
| Observed vs inferred in the app | – | An **Observed / Inferred layer and legend**. Inferred airport elements (bridges, paint, signs, tower form) and inferred traffic are drawn distinctly and listed in the About panel. |
| Aircraft | `models.js`, the 23 `.sfom` models, fitting. Existing liveries: CES/CCA (777-300ER only), CSN (787-9 only), CPA, EVA, CAL, JAL, ANA, KAL, AAR. | C919 and C909 models. Liveries: Shanghai Airlines, Spring, Juneyao, then 12 more brands, plus CES/CCA/CSN on narrow-bodies, A330, C919 and C909. |
| Relay and artifact | `sfo_live_server.py` design (or hwd3d's relay, Q7), snapshot mode, `livetest.mjs` | `sha_live_server.py` within current provider terms. Snapshot/replay content depends on Q1. |
| Must not leak | SFO ARP, headings 117.83/27.83, `GROUND_Y`, `GEOID_M` 32.29, FAA tables, flysfo plan logic (92 lines in `traffic.js`), SFO data imported at module scope (`gates.js`, `signs.js`, `traffic.js`: inject instead), degree/radian mixing, the owner's repository URL in User-Agents or sha3d docs | – |

Effort (arch.md §7, rough, inferred): the hwd3d-style packages P0–P4, which correspond to this plan's Phases 1–3, are
about 1.5–2.5 × hwd3d's roughly 20 package-hours.

## 5. Risks

1. **No observed traffic** (§3). Every live, replay and stand-learning feature inherited from sfo3d is blocked until
   Q1 is answered.
2. **Official AIP unread.** All AD 2 values come from a mirror at least four AIRAC cycles old, and the official site
   itself carries a "Trial Phase … Verify Before Use" banner. AMDT 12 (26 Nov) changes ZSSS. The ARP is too coarse
   to be a frame origin (Q0, Q2).
3. **No sub-metre open optical imagery.** Bridges, paint and holds cannot be surveyed the SFO way. They will be
   standards-driven and `inf` unless Q6 allows more.
4. **PRC legal exposure** (law.md §8; not legal advice). The main protection is that nothing is done inside China.
   - **R1, high for the person concerned:** anyone in the PRC who helps us (receivers, photos, GNSS tracks, audio, OSM
     edits) faces real enforcement. Never solicit or accept this.
   - **R2, medium:** OSM military or armed-police features near ZSSS. Filter them; never draw or label them.
   - **R3, low to medium:** a metre-accurate 3-D model of a PRC airport has the shape of item 24 of the 2020
     surveying secret catalogue: 3-D models with planar accuracy ≤ 10 m or relative height accuracy ≤ 5 %, over
     more than 25 km² contiguous. The verifier rates this as if anything understated, because any modelled building
     meets the 5 % test, so the extent is the only safeguard.
     - The convex hull of the OSM aerodrome polygon with a 1 km buffer is 23.5 km² (computed). A rectangle with a
       1 km margin is 31.9 km², which is too large.
     - Already beyond a 25 km² default: the committed Sentinel-2 crops (53 km²; item 22 concerns imagery better than
       10 m accuracy or 0.5 m resolution) and the 20 km DEM and WorldCover crops (local; the DEM has the shape of
       item 23).
     - These are globally distributed foreign products. If you choose the 25 km² default in Q3, the crops will be cut
       to that extent.
   - **R4, low:** an app reachable in the PRC is an unreviewed map service. Do not target the PRC (hosting, ICP,
     Chinese-language promotion).
   - **R5, low for the owner:** showing PRC flight positions from foreign aggregators falls under the Data Security
     Law Art. 2. Keep to the airport vicinity, civil traffic only, no long archives.
   - **Also:** trademarks and copyright in architecture or photos (R8/R9); no national borders or route maps (R11);
     travel to the PRC or Hong Kong after publishing (R10).
5. **Licence mixing.** ODbL, non-commercial and no-redistribution feeds cannot share one published artefact, so keep
   per-record provenance. Chinese commercial feeds may deliver GCJ-02: test before any use.
6. **Model provenance and terms.** The CC BY COMAC models are uploader-declared. COMAC's ACAP terms forbid
   reproduction, quoting and any use without written authorisation.
7. **Terms drift.**
   - adsb.lol's API is now metered. sfo3d's capture of 2026-09-24 still showed free use, so the change is inferred to
     be recent; no start date is published.
   - airplanes.live is reported to have gone contributor-only in Sep 2026 (secondary).
   - OpenSky needs a licence for automated use.
   - Re-check all terms at build time.
8. **OSM churn.** The aerodrome relation is a week old, and the stand numbers were "adjusted" in 2026.
9. **Vertical datum.** Mixing AIP, Wusong, EGM2008 and ellipsoid heights makes aircraft float or sink.
10. **Code coupling** (arch R3–R7): FAA geometry in both renderer paths, module-scope SFO data, untested
    no-flysfo paths, degree/radian mixing, METAR trend groups.
11. **Fonts and CDNs** (e.g. Google Fonts) may not load in the PRC. This affects typography only.
12. **Legal drift.** The PRC Trademark Law revision takes effect 2027-01-01, and the Public Map Specification expires
    about 2028.
13. **Material already pushed to the public repo before review** (now cut in the working tree, still in history):
    - transcribed AIP lists in `aip.md`;
    - per-record ADS-B Exchange sample data in `adsb.md`;
    - COMAC ACAP figures in `fleet.md`.

    Whether to rewrite history is your call (Q2).
14. **Usage budget.** sfo3d-level fidelity is expensive, so each phase below delivers something usable.

## 6. Questions for the owner

Q0 and Q1 block everything else.

- **Q0 (ARP and scene origin; stop-and-ask).** Your working ARP, 31.198104 N 121.33426 E (OurAirports), is **174 m**
  from the AIP ARP N31°11.8′ E121°20.1′. The AIP value was read only in an unofficial mirror, is printed to about
  ±90 m, and is defined as the centre of RWY18L/36R. Which scene origin do you want?
  - (a) the printed AIP value;
  - (b) the RWY18L/36R centre computed from the OSM runway ends, 31.19785 N 121.33629 E (it matches the AIP definition
    and both runway ends are imaged);
  - (c) wait until the official AD 2.2 is read (Q2).

  The frame origin does not change any geometry: everything is built in WGS-84. It only defines the local metre grid.
- **Q1 (go/no-go: traffic source).** Open ADS-B sees nothing at Hongqiao. Options:
  - **(A) "Simulated Hongqiao" (recommended baseline).**
    - Traffic is generated from a schedule and labelled *scheduled/inferred* everywhere.
    - Runway mode follows the AIP (east landings, west take-offs) and current NOTAMs, with the direction from the ZSSS
      METAR wind. The METAR source is not yet checked (Phase 1).
    - Stands are matched by AIP span class and the airline-per-terminal list, unless Q10 names a source.
    - Schedule:
      - (A1) licensed (OAG or Cirium; cost; not redistributable);
      - (A2) a hand-built "typical day" from aggregate statistics and airline timetables (whether the publishers'
        terms allow this still needs checking);
      - (A3) synthetic traffic at realistic rates.
    - Any rare observed overflight can be overlaid as *observed*.
  - **(B) Licensed commercial feed.**
    - VariFlight DataWorks, or Aireon via FlightAware Premium (at least $1,000/month).
    - Needs a written contract for public display; no recorded data in the public repo.
    - Ground and stand coverage is unverified even there. Asking vendors needs your identity.
  - **(C) Change airport.** adsb.lol's grid shows ground coverage in the cells containing Hong Kong (556 aircraft;
    the same cell holds Shenzhen and Macau) and Taipei Taoyuan/Songshan (332). Airport-level coverage is not yet
    measured.
  - **(D) Static Hongqiao.** Airport fidelity only, no traffic claims, until a source exists.
  - **Not recommended:** a receiver in Shanghai or recruiting feeders there (R1).
- **Q2 (official AIP and published AIP content).**
  - The eAIP is free but needs an account. Will you register and download AD 2 ZSSS and its charts yourself? An agent
    must not hold your credentials.
  - May short AIP facts be cited with source in the public repo?
  - Whole AIP lists were already pushed in `aip.md` (now cut to summaries). Keep them out, and should history be
    rewritten? That would need your explicit approval.
  - Is the unofficial mirror acceptable as an interim reference?
- **Q3 (legal posture).** Do you accept the residual PRC-law risk of a public, metre-accurate WGS-84 model built abroad
  from open data? Recommended defaults, each your call:
  - detailed extent = convex hull of the aerodrome + 1 km buffer (23.5 km²); crops cut to match;
  - filter military, armed-police, police, prison and GNSS-station features;
  - CONTRIBUTING rule: no data collection inside the PRC;
  - no OSM edits at ZSSS from us (or aeroway-only, never sensitive features);
  - hosting outside the PRC;
  - PRC traffic recordings in the repo: none, or radius ≤ 30 km, altitude cap, civil only, limited duration;
  - may the local live recorder keep running until it ends (it records PRC airspace locally, uncommitted)?
  - `tools/geo/gcj02.py` (unofficial algorithm) stays local; the committed `geo_overlay.py` and `s2_osm_align.py`
    import it, so the GCJ check is not reproducible from the repo: commit it, or publish the predicted shift as a
    constant;
  - a takedown contact for airlines and COMAC: which address may be published, if any;
  - a professional legal opinion, and advice before any travel to the PRC or Hong Kong;
  - caacnews (its terms forbid downloads): keep short quotes or drop it.
- **Q4 (ATC audio).** No lawful verified source exists. Drop the toggle for SHA (recommended)? If you open
  `https://www.liveatc.net/search/?icao=ZSSS` in a browser, a screenshot would settle whether any feed exists.
- **Q5 (models and liveries).**
  - C919/C909: use the CC BY 4.0 Sketchfab models despite their unproven provenance, or fit our A320/CRJ900? COMAC's
    ACAP terms forbid even quoting the dimensions, so a fit needs your decision. The ACAP figures that were quoted in
    `fleet.md` have been cut.
  - May we create a Sketchfab account for the ARJ21 download?
  - Paint the "COMAC C919" title or not?
  - Same non-commercial livery posture as sfo3d? The four Shanghai carriers first?
- **Q6 (imagery and reference).**
  - Sentinel-2 as ground texture, and the Umbra SAR (CC BY 4.0) as the outline reference?
  - May we use Google imagery as visual reference only, never traced, for example to confirm which stands have
    bridges?
  - Pursue SPOT World Heritage (licence contradicted)?
  - Can you provide openly licensed high-resolution imagery, official apron charts, or licensed photos or a design
    reference of the tower(s)? Only existing open-licence photos would be used; nothing solicited from the PRC.
- **Q7 (renderer, quality, donors).**
  - `live.html` (WebGL2, like Hayward) or sfo3d's three.js `live3.html`?
  - Does Hayward's "one quality level, full features; the artifact only has to open and work on an iPhone" (OD1/OD2)
    apply here, or does the brief's "must work on a phone" stand?
  - May hwd3d @ eb34f7d be a second code donor (arch.md's recommendation), or sfo3d only?
- **Q8 (language).** English only, or bilingual Chinese/English labels and signs where verified? A Chinese-language UI
  or promotion moves the app closer to the PRC map rules (law.md §7).
- **Q9 (type mix).** It cannot be measured from open ADS-B. Options:
  - (a) a licensed schedule with equipment codes (same as Q1 A1);
  - (b) one hand-read day of the SAA flight board as reference facts, if its terms allow;
  - (c) accept the estimate for model priorities.
- **Q10 (feeds, stands, definitions).**
  - (a) adsb.lol: one poll per 180 s within the quota, or a sponsor key (EUR 20–50/month)?
  - (b) May we contact airplanes.live or ask OpenSky for a licence? Both need your identity.
  - (c) Stand allocation: the SAA flight board by hand (terms), a request for written authorisation, or type and
    terminal rules only?
  - (d) Does "movement" for the coverage fraction mean all take-offs and landings (about 783/day) or scheduled flights
    only?
  - (e) Night: "no scheduled flights 00–06, delays allowed" (the sources) rather than a hard curfew?
  - (f) In simulated mode, show airline and type only, or also invented registrations (clearly marked)?
- **Q11 (standards).** Can you provide ICAO Annex 14 Vol I and the CAAC aerodrome standard, or approve buying them?
  Without them, every marking and sign parameter stays `inf`.

## 7. Phased task list

Each phase ends with a commit, a push and renders shown to you. No scored QA loop starts without your approval.

- **Phase 1: data foundation.** It needs Q0, Q2 and Q3, but not Q1.
  - Pin and filter the OSM extract; commit it with SOURCES.json.
  - Read the official AD 2 (Q2); re-check after AMDT 12 (26 Nov).
  - Obtain the marking standards (Q11) and choose a ZSSS METAR source; verify its terms.
  - Build `data/sha_airport.*`:
    - runways from the AIP dimensions and displaced thresholds on the OSM centrelines;
    - taxiways and holds;
    - stands (149 placed, 6 `inf`, 15 OSM-only flagged);
    - bridge stands (`inf`);
    - buildings, tower, FBO and the China Eastern base.
  - Write the vertical-datum chain.
  - Re-fit the OSM centrelines that are 5–13 m off the imagery (local only, per Q3).
  - Cut the imagery and DEM crops to the Q3 extent.
  - Draw overlay plates of our data on Sentinel-2 and Umbra, with deviation call-outs.
- **Phase 2: app skeleton.**
  - Fork the renderer, geo frame, world, markings (one ICAO/CAAC table) and gates; inject the data.
  - Write `sha_live_server.py` within current terms.
  - Build the Observed/Inferred layer.
  - First renders of the static scene.
- **Phase 3: traffic per Q1.**
  - (A) A schedule-driven simulator through the same traffic, physics and stand pipeline, tagged `inferred`:
    - taxi routing on the OSM graph;
    - pushback;
    - the night pause (Q10 e);
    - runway mode from the AIP, NOTAMs and METAR.
  - (B) A licensed-feed adapter.
  - In both cases: replay packs and the snapshot artifact.
- **Phase 4: aircraft.**
  - C919 and C909 models (Q5).
  - Liveries for CES, CSH, CQH and DKH first.
  - Lights, gear and shadows as in sfo3d.
- **Phase 5: airport fidelity.**
  - T1 and T2 piers, the tower(s), jet bridges with VDGS, remote stands with stairs and buses, the FBO.
  - ICAO/CAAC markings, signs and lighting from AD 2.14 (PALS, PAPI, RCLL, RWSL).
  - Surroundings within the Q3 extent.
- **Phase 6: physics, QA and delivery.**
  - Solid bodies, pavement-only placement, spacing.
  - Adversarial visual QA, after your approval.
  - About/credits panel: ODbL, Copernicus, Umbra and model notices, and the Observed/Inferred legend.
  - Standalone app plus relay, and the snapshot/replay artifact, both usable on a phone.
- **Later:** cinematic tracking films (as for SFO).
