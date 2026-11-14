# Phase 0 / law: legal constraints on a public repo and a public web app that show Shanghai Hongqiao (SHA / ZSSS) in 3-D

**Errata (2026-11-13, from the verification reports).** Corrected in place below; see
`verify_licences_law.md` (headline findings 1-5, rows L11, L14, L22, L24, A33):
- OSM military / armed-police objects near ZSSS: **6 distinct elements** (3 rail ways, 3 `landuse=military` areas),
  not 5. Ids stay withheld (headline 5, L22).
- Radio Regs Art. 72: fine up to CNY 30,000, **or, with serious consequences, licence revocation plus CNY
  30,000-100,000** (headline 1, L24).
- Radio Regs Art. 75(2)/(3) was missed: foreign organisations or individuals monitoring radio inside the PRC, or
  supplying security-related PRC radio data abroad: CNY 30,000-100,000 (after refusing to correct), serious cases
  CNY 100,000-300,000 (headline 2).
- Radio Regs Art. 41: users must not deliberately receive signals outside their licence, nor spread, publish or use
  **unintentionally** received information; the qualifier is kept throughout (A33).
- Criminal Law Art. 111 has **no universal 5-year minimum**: minor cases get under 5 years. The Art. 8 threshold for
  foreigners abroad (minimum of 3 years or more) is met only for non-minor cases (headline 3, L14).
- Secret catalogue items 23 and 24 are separate: item 23 (DEM/DSM) planar ≤10 m **or** height ≤15 m; item 24 (3-D
  models, point clouds etc.) planar ≤10 m **or** relative object-height ≤5 %; both outside military zones and over
  more than 25 km² contiguous. The catalogue's third column is the knowledge scope (approved holders and users), not
  the producer, so the argument "made by licensed surveyors, so our model is not such a product" is weakened. The
  verifier rates R3 as, if anything, understated (headline 4, L11).

KEY = law. Checked 2026-11-13. Written for the owner and the lead.

**This is not legal advice.** It is a reading of primary texts plus some secondary analysis. The owner is a non-Chinese
individual outside China; the owner's own country was not assumed. Where the text below reads a law, the quoted words are
the law's. Every conclusion about what the law means for this project is marked **[inferred]**.

Labels used:
- **[verified]**: primary or official text read.
- **[secondary]**: Wikipedia, OSM wiki, news, law firms, or a sibling report's secondary row.
- **[unverified]**: a single non-authoritative source, or a search summary.
- **[contradicted]**: sources disagree; both are given.
- **[obs]**: observed by us in data. **[inferred]**: our reading.

Caches:
- `sha3d/refs/cache/law/` (30 sources, plus `SOURCES.json` with URL, date, hash, licence and redistribution status; 10
  failed or refused fetches are listed under `not_kept`).
- Reused, not copied: `sha3d/refs/cache/china_law/` (Data Security Law, Counter-espionage Law, Radio Regulations, NDSM
  Regulations, Copyright Law, CAAC data measures, MSS 2024 statement), cached by key `adsb`.
- Scripts are outside the download dirs:
  - `sha3d/tools/law/fetch.sh`: download plus log.
  - `sha3d/tools/law/write_sources.py`: writes SOURCES.json.
  - `sha3d/tools/law/docx_text.py`
  - `sha3d/tools/law/osm_sensitive.py`: lists OSM objects that the PRC rules bar from public maps.
- Run any of them with `python3 -I`.

Related sibling reports:
- `docs/phase0/adsb.md` §3: ADS-B in China, with the 2021 and 2024 state-security cases.
- `docs/phase0/aip.md`: the eAIP and the ARP.
- `docs/phase0/fleet.md` §4.2: trademark notice.
- `docs/phase0/geo.md`: GCJ-02 check of OSM.

## 0. Bottom line

1. **Nothing we plan is done inside China. That is the main protection.**
   - The Surveying and Mapping Law covers surveying "在中华人民共和国领域" (in PRC territory) [verified].
   - The Map Management Regulations cover public maps and internet map services "在中华人民共和国境内" (inside China)
     [verified].
   - A model compiled abroad from foreign open data (OSM, Sentinel-2, Copernicus DEM, foreign ADS-B aggregators) is
     outside the plain territorial scope of both [inferred].
   - The real exposure lies with **anyone inside China who helps us**: photos, GPS tracks, receivers, audio streams, OSM
     edits. State security has acted against exactly such people in 2021, 2024, 2025 and 2026 [secondary: MSS statements
     reposted by state media].
2. **Several things would be unlawful if our 3-D model were published inside China:**
   - It needs map review and a 审图号 (map approval number) (Map Regs Arts. 15, 22) [verified].
   - Map data servers must be in China (Art. 34) [verified].
   - Public maps of places in China must have planar accuracy "不优于10米" (no better than 10 m) (Public Map Content
     Specification 2023, item 19) [verified].
   - The model would be accurate to a few metres in WGS-84 [inferred], so the app cannot be "the same app, also for
     China".
   - GCJ-02 is how licensed Chinese map providers meet the secrecy-processing rules. **No primary text we read names
     GCJ-02** [verified absence]. Its algorithm "国家认定的地理信息保密处理技术算法及参数" (the state-designated
     secrecy-processing algorithm and parameters) is classified 机密 (confidential) [verified: 2020 catalogue item 3;
     the link to GCJ-02 is inferred].
3. **Publishing WGS-84 coordinates of a Chinese civil airport from outside China**: no provision targets this directly.
   - No law or regulation we read regulates it as such [verified absence].
   - The reach is indirect, through extraterritorial "harm to national security" clauses:
     - Data Security Law Art. 2 [verified];
     - Network Data Security Management (NDSM) Regulations Art. 2 [verified];
     - Criminal Law Art. 8, which requires a minimum sentence of 3 years and dual criminality [verified]; Art. 111
       meets that threshold only in non-minor cases (§2.5);
     - the State Secrets Law's concern with data "汇聚、关联" (aggregation and linkage) (Art. 36) [verified].
   - For a civil airport that is a public facility, and shown from open foreign data, the likelihood of action against
     a foreign individual abroad looks low [inferred].
4. **Civil airports are not on the list of things banned from public maps. Military facilities, including military
   rail spurs and barracks, are** [verified, item 20(1)].
   - Item 20(5) also bars the important facilities of military-civil joint-use (军民合用) airports.
   - ZSSS is "CIVIL/4E" in the AIP [secondary via aip.md]. Its military use ended in 1963–64 [secondary: Wikipedia].
   - **But OSM around ZSSS contains 6 military-tagged elements** [obs; ids, names, positions and distances withheld on
     purpose]: 3 rail ways tagged `usage=military` and 3 military / armed-police areas.
   - These must be filtered out before anything is rendered, labelled or committed.
5. **OSM is blocked in mainland China** (GreatFire, since 2012) [secondary].
   - The OSM wiki says the project is effectively illegal there [secondary].
   - MSS's October 2026 case shows a person in China being investigated for tagging sensitive units on a "境外开放地图平台"
     (a foreign open-map platform) [secondary].
   - Using OSM data abroad is fine (licensing is a separate question). Contributing PRC edits is the risky part.
6. **ATC audio: no lawful, verified live source for ZSSS exists.**
   - Receive-only stations need no licence (Radio Regs Art. 27(2)) [verified].
   - But station users "不得传播、公布或者利用无意接收的信息" (must not spread, publish or use information received
     unintentionally) (Art. 41; Art. 72: fine up to CNY 30,000, or with serious consequences licence revocation plus
     CNY 30,000–100,000) [verified].
   - Art. 75(2)/(3) also covers foreign organisations or individuals monitoring radio inside China, and supplying
     security-related PRC radio data abroad: CNY 30,000–100,000, serious cases CNY 100,000–300,000 [verified].
   - A Chinese hobbyist's 2024 note says LiveATC lists **no** Chinese airport, ZSSS included [unverified]. We could not
     open LiveATC: Cloudflare 403, and the Wayback Machine is refused by the session proxy.
   - Recommendation: no ATC-audio toggle for SHA [inferred].
7. **Airline liveries (China Eastern, Shanghai Airlines, Spring, Juneyao).**
   - The PRC Trademark Law defines "use" as use "在…商业活动中，用于识别商品来源" (in commercial activities, to
     identify the source of goods) (2019 Art. 48; same core in the 2026 revision, Art. 2, in force 2027-01-01)
     [verified / secondary].
   - A non-commercial depiction that does not brand the app is not trademark use in that sense [inferred].
   - Under US law, *Jack Daniel's* (2023) removes the Rogers shield only when a mark is used "as a source identifier"
     [verified].
   - Keep the sfo3d notice, don't monetise, and keep airline marks out of the app's own name and icon [inferred].

## 1. PRC Surveying and Mapping Law (测绘法, 2017 revision) [verified]

Source: npc.gov.cn copy. Adopted 2017-04-27, in force 2017-07-01 (Art. 68).

- **What counts as surveying (Art. 2):** "本法所称测绘，是指对自然地理要素或者地表人工设施的形状、大小、空间位置及其属性等进行测定、采集、表述，以及对获取的数据、信息、成果进行处理和提供的活动。"
  ("Surveying" means measuring, collecting and representing the shape, size, spatial position and attributes of natural
  features or man-made surface facilities, and processing and providing the data obtained.)
  - The definition is broad: "表述" (representation), "处理" (processing) and "提供" (providing) are included.
  - A 3-D airport model is a 表述 of 地表人工设施 (man-made surface facilities) [inferred].
- **Territorial scope (Art. 2):** "在中华人民共和国领域和中华人民共和国管辖的其他海域从事测绘活动，应当遵守本法。"
  (Surveying in PRC territory and PRC-administered waters must comply with this law.)
- **Foreigners (Art. 8):**
  - "外国的组织或者个人在中华人民共和国领域…从事测绘活动，应当经国务院测绘地理信息主管部门会同军队测绘部门批准" (foreign
    organisations or individuals surveying in PRC territory need approval from the State Council surveying authority
    together with the military surveying department);
  - and "应当与中华人民共和国有关部门或者单位合作进行，并不得涉及国家秘密和危害国家安全。" (must work with a Chinese
    partner, must not touch state secrets and must not endanger national security).
- **Penalty for foreigners (Art. 51):**
  - "…责令停止违法行为，没收违法所得、测绘成果和测绘工具，并处十万元以上五十万元以下的罚款" (stop the activity;
    confiscation of gains, survey results and tools; fine of CNY 100,000–500,000);
  - "情节严重的，并处五十万元以上一百万元以下的罚款，限期出境或者驱逐出境" (serious cases: fine of CNY 500,000–1 million,
    order to leave or expulsion).
- **Map content (Art. 38):** "地图的编制、出版、展示、登载及更新应当遵守国家有关地图编制标准、地图内容表示、地图审核的规定。"
  (compiling, publishing, displaying, posting and updating maps must follow the national map standards, content rules
  and review rules.)
  - Internet map providers "应当使用经依法审核批准的地图" (must use maps reviewed and approved under law).
- **National systems (Arts. 5, 10, 52):**
  - Surveying must use "国家规定的测绘基准和测绘系统" (the datums and systems prescribed by the state) (Art. 5).
  - Art. 52 penalises building a GIS "采用不符合国家标准的基础地理信息数据" (on basic geographic data that does not meet
    national standards).
  - These bind actors in China; for a foreign repo they explain why domestic products are not WGS-84 [inferred].
- **Interim Measures on foreign surveying in China** (外国的组织或者个人来华测绘管理暂行办法, 2007, amended 2011 and
  2019) [verified]:
  - Art. 6: a joint venture is required.
  - Art. 7 bars even joint ventures from, among other things, "真三维地图的编制" (compiling true-3-D maps) and
    "导航电子地图编制" (compiling navigation e-maps).
  - Art. 19: "未经依法批准将测绘成果携带或者传输出境的，…处3万元以下罚款" (carrying or transmitting survey results
    abroad without approval: fine up to CNY 30,000).
- **What it means [inferred]:**
  - We must not survey anything in China, or ask anyone to: no site visit with GNSS or a drone, no commissioned photos or
    measurements, no "please walk stand 12 with a GPS logger".
  - Compiling from foreign open data abroad is outside Art. 2's territorial scope.
  - Wikipedia's summary "private surveying and mapping activities have been illegal in mainland China since 2002" refers
    to activity in China [secondary].

## 2. Map Management Regulations (2016), Public Map Content Specification (2023), state-secret catalogue (2020), GCJ-02

### 2.1 Map Management Regulations (地图管理条例, State Council Order 664) [verified]

Signed 2015-11-26, in force 2016-01-01 (Art. 58).

- **Scope (Art. 2):** "在中华人民共和国境内从事向社会公开的地图的编制、审核、出版和互联网地图服务以及监督检查活动，应当遵守本条例。"
  (compiling, reviewing and publishing public maps, and internet map services, inside China.)
- **Banned content (Art. 8):** includes "（二）危害国家安全、损害国家荣誉和利益的" (endangering national security or
  harming national honour and interests) and "（三）属于国家秘密的" (state secrets).
- **Map review (Arts. 15, 16):**
  - Art. 15: "国家实行地图审核制度。向社会公开的地图，应当报送有审核权的测绘地理信息行政主管部门审核。但是，景区图、街区图、地铁线路图等内容简单的地图除外。"
    (the state runs map review; public maps must be submitted, except simple maps such as scenic-area, street-block and
    metro maps.)
  - Art. 16: whoever displays or posts a non-publication map submits it ("由展示者或者登载者送审").
- **审图号 (Art. 22):** approved maps must "显著标注审图号" (show the approval number prominently).
- **Servers (Art. 34):** "互联网地图服务单位应当将存放地图数据的服务器设在中华人民共和国境内" (internet map services
  must keep their map-data servers inside China).
- **Uploads (Art. 55):** "通过互联网上传标注了含有按照国家有关规定在地图上不得表示的内容的，责令改正，给予警告，可以处10万元以下的罚款"
  (uploading annotations with content barred from maps: correction, warning, fine up to CNY 100,000).
  - This is the provision that matters for OSM edits made from China [inferred].
- **Penalty (Art. 54):** an internet map service using unreviewed maps: warning, fine up to CNY 200,000.

### 2.2 Public Map Content Specification (公开地图内容表示规范, 自然资规〔2023〕2号, 2023-02-06) [verified]

Text from the State Council Gazette 2023 No. 11.

| Item | Text (quoted) | Our data / plan [inferred] |
|---|---|---|
| 2 | "公开地图或者附着地图图形产品的内容表示，应当遵守本规范。" (public maps and products bearing map graphics must follow this specification) | No territorial words in the item itself; its legal basis (Map Regs Art. 2) is territorial |
| 18 | "用于公共服务的设施，可在地图上表示其名称等可公开属性信息。" (facilities for public service may be shown with their name and other publishable attributes) | A civil airport is a public-service facility: it may be shown |
| 19 | "表现地为我国境内的地图平面精度应当不优于10米（不含），高程精度应当不优于15米（不含）" (maps of places in China: planar accuracy no better than 10 m, height accuracy no better than 15 m) | Our model is metre-level WGS-84 (OSM agrees with Sentinel-2 to about ±10 m, geo.md). Copernicus DEM LE90 is 1.92 m (terrain.md). Both exceed the in-China public threshold. |
| 20(1) | "军用机场、港口、码头，营区…军用公路、铁路专用线…等直接用于军事目的的各种军事设施" (military airports, ports and docks, barracks, military roads and rail spurs, and other military facilities) must not be shown | **OSM around ZSSS has a military rail spur and military/armed-police areas [obs]: filter them** |
| 20(5) | "军民合用机场、港口、码头的重要设施" (the important facilities of joint military-civil airports, ports and docks) | ZSSS is civil (§2.6); not applicable unless that changes |
| 20(6) | "卫星导航定位基准站" (GNSS reference stations) | Don't model or label any |
| 21(6) | attributes of "电力、电讯、通信等重要设施" (power, telecom and communications facilities) must not be shown | Don't attribute radar, navaid or power installations beyond what the AIP publishes [inferred] |
| 22 | "遥感影像，地面分辨率不得优于0.5米" (remote-sensing imagery: ground resolution no better than 0.5 m) | Sentinel-2 at 10 m is fine; commercial 30 cm imagery would not be (in China) |
| 23 | valid 5 years from issue; **repeals** the 2003 and 2009 rules | The OSM wiki still cites the 2003/2009 rules ("any locations more precise than 50 meters") → **outdated** |

### 2.3 State-secret catalogue for surveying (测绘地理信息管理工作国家秘密范围的规定, 自然资发〔2020〕95号) [verified]

MFA-hosted copy. In force 2020-07-01.

Relevant 秘密/机密 (secret/confidential) entries:
- **Item 3 (机密, long-term):** "国家认定的地理信息保密处理技术算法及参数" (the state-designated secrecy-processing
  algorithm and its parameters).
- **Item 22 (秘密):** "军事禁区以外平面精度优于10米或者地面分辨率优于0.5米、且连续覆盖范围超过25平方千米的正射影像"
  (outside military zones: orthophotos better than 10 m planar accuracy or 0.5 m resolution, covering more than
  25 km² contiguously).
- **Item 23 (秘密):** DEM/DSM "军事禁区以外平面精度优于（含）10米或高程精度优于（含）15米、且连续覆盖范围超过25平方千米"
  (outside military zones: planar accuracy 10 m or better, **or** height accuracy 15 m or better, covering more than
  25 km² contiguously).
- **Item 24 (秘密), a separate item:** "军事禁区以外平面精度优于（含）10米或地物高度相对量测精度优于（含）5%、且连续覆盖范围超过25平方千米的三维模型、点云、倾斜影像、实景影像、导航电子地图等实测成果"
  (outside military zones: measured 3-D models, point clouds, oblique imagery, real-scene imagery, navigation e-maps
  and similar, with 10 m planar accuracy or better, **or** relative object-height accuracy of 5 % or better, covering
  more than 25 km² contiguously). Its height test is relative (5 %), not the 15 m of item 23.
- **Item 25 (秘密):** "与军事、国家安全相关的国民经济重要设施精度优于（含）±10米的点位坐标及其名称属性" (point
  coordinates, accurate to ±10 m or better, plus names and attributes, of important economic facilities related to
  the military or national security).
- **Note 1:** these secrets are "由从事测绘地理信息活动的测绘资质单位、军队测绘部门（单位）产生" (arise at licensed
  surveying units and military surveying departments), which must mark them under the catalogue without seeking
  separate classification authority.
- **Third column (知悉范围, knowledge scope):** lists the approved holders and users ("…批准的测绘成果保管单位及用户"),
  not the producer [verified, re-read in the cached PDF].
- **Art. 5:** the rule itself is "按照工作秘密管理" (managed as a work secret).

**Reading [inferred]:**
- Item 24 is about *measured* products (实测成果). Note 1 says where such secrets arise and who marks them; neither it
  nor the third column limits the items to products made by licensed Chinese surveyors. So the argument "our model is
  *derived* abroad from foreign open data, so it is not such a product" is **weak**: only the word 实测 (measured)
  still separates us from item 24.
- A model of a Chinese airport plus surroundings above 25 km², at metre accuracy, has the **same shape** as a 秘密
  (secret) product. Any modelled building height will meet the 5 % relative-height test of item 24, so the verifier
  rates R3 as, if anything, understated (verify_licences_law.md headline 4).
- Whether an airport is a facility "related to military or national security" (item 25) is not defined anywhere we read.
- A conservative design keeps the detailed model's contiguous extent **under 25 km²**: the aerodrome plus a margin.
  The aerodrome boundary is in OSM.

### 2.4 GCJ-02: what the law says and what it doesn't

- No primary text we read (Surveying Law, Map Regs, 2023 Specification, 2020 catalogue) names GCJ-02 or requires a
  coordinate offset as such [verified absence].
- The legal hooks are indirect:
  - map review (Map Regs Art. 15);
  - the 10 m accuracy cap (Spec item 19);
  - secret results must be "经…进行保密技术处理" (put through secrecy-technical processing) before use in maps (Map Regs
    Art. 13; Spec item 17);
  - the national standard GB 20263-2006 §4.1: "Technical spatial processing must be applied to electronic navigational
    maps prior to publication, sales, redistribution, and usage." [secondary: Wikipedia's translation; the standard was
    not read].
- Wikipedia: "Chinese regulations require that approved map service providers in China use a specific coordinate
  system, called GCJ-02". Its official name is "地形图非线性保密处理算法" (topographic-map non-linear secrecy-processing
  algorithm) [secondary].
- **For us [inferred]:**
  - GCJ-02 is a requirement on licensed publishers in China, not on a foreign repository.
  - Our rule "never mix GCJ-02 into WGS-84" is a data-quality rule, and consistent with the law.
  - Catalogue item 3 makes the *official* algorithm 机密 (confidential).
  - `tools/geo/gcj02.py` holds the widely published, unofficial "eviltransform" approximation (Wikipedia lists open-source
    versions in many languages).
  - Keeping that file in a public repo is a small, deliberate risk: owner decision D8.

### 2.5 Publishing WGS-84 coordinates of a Chinese facility, outside China

- **Not found:** no PRC law or regulation we read regulates foreign publication abroad of coordinates of a Chinese
  civil facility as such [verified absence].
  - Map Regs, Surveying Law, CAAC data measures (Art. 3: "在中华人民共和国境内…", inside China) and Radio Regs (Art. 2)
    are all territorial.
- **Extraterritorial hooks** [verified texts]:
  - DSL Art. 2(2): "在中华人民共和国境外开展数据处理活动，损害中华人民共和国国家安全、公共利益或者公民、组织合法权益的，依法追究法律责任。"
    (data processing abroad that harms PRC national security, public interests, or the lawful rights of citizens or
    organisations is pursued under law.)
    - DSL Art. 3: processing includes "公开" (making public).
  - NDSM Regulations Art. 2(3): same wording for network data.
  - Criminal Law Art. 8: a foreigner's crime abroad "对中华人民共和国国家或者公民" (against the PRC state or citizens),
    where "最低刑为三年以上有期徒刑" (the minimum sentence is 3 years or more), "可以适用本法，但是按照犯罪地的法律不受处罚的除外"
    (PRC law may apply, except where the act is not punishable where it was committed).
    - Art. 111 (supplying state secrets or intelligence to foreign organisations or persons): 5–10 years, but
      "情节较轻的，处五年以下有期徒刑、拘役、管制或者剥夺政治权利" (minor cases: under 5 years, criminal detention,
      public surveillance or deprivation of political rights). There is no universal 5-year minimum, so the Art. 8
      threshold is met only for non-minor cases.
  - State Secrets Law (2024) Art. 36: "防範數據匯聚、關聯引發的泄密風險" (guard against leaks caused by data aggregation
    and linkage; quoted as rendered by the gov.cn traditional-character gateway).
- **Official caution, observed [secondary via aip.md fact 21]:** the eAIP's AD 2.12 for ZSSS gives **no** threshold
  coordinates ("Nil" for all four).
  - The state chooses not to publish precise runway-end coordinates. OSM and our model will show them [inferred].
- **Reading [inferred]:**
  - These hooks need "harm to national security" (or a secret, or a crime with a minimum of 3 years or more, i.e. a
    non-minor Art. 111 case).
  - A civil airport is a facility the 2023 Specification lets public maps show (item 18).
  - Its geometry is already in OSM, Google, X-Plane and elsewhere.
  - So the realistic consequences for a foreign individual are blocking and refused entry, not prosecution. Those need
    an owner decision on travel (D11).

### 2.6 Is Hongqiao, or any part of it, "sensitive"?

- AD 2.2 class "CIVIL/4E" [secondary: aip.md row 14, AIP mirror].
- History:
  - Wikipedia: "Its military use continued after being handed over to the Republic of China … and, later, the People's
    Republic of China government. From late 1963, it was rebuilt for civilian use and was reopened in April 1964."
    [secondary]
  - A Chinese chronology (sohu, via search summary only) says 1963 "扩建为军民合用的国际机场" (expanded into a joint
    military-civil international airport) and that it became civil-only around 1971 [unverified].
  - The two disagree on dates only. Both say it is civil now.
- No source we read lists ZSSS as a 军民合用机场 (joint military-civil airport) [verified absence in what we read; not
  proof].
- **OSM, observed** (`tools/law/osm_sensitive.py` on the OSM API extracts in `refs/cache/osm/`, dated 2024-01 to
  2026-02):
  - **6 distinct elements tagged military** (4 features if the 3 rail ways count once):
    - 3 rail ways tagged `usage=military` (class military);
    - 3 `landuse=military` areas: 2 armed police (by name), 1 military.
  - Their names, ids, coordinates and distances are **deliberately not reproduced in this public document** (details
    local only: refs/cache/osm/, via the script).
  - Under item 20(1) these must not appear on a public map of China.
  - The MSS October 2026 case (§4) shows that annotating such units is treated as a security matter [inferred].
  - **Filter before rendering:** `landuse=military`, `military=*`, `usage=military`, and names containing 部队 (army
    unit), 武警 (armed police), 军 (military), 营区 (barracks).
  - Also never commit derived files that contain them.

### 2.7 Our open data against the in-China thresholds [inferred]

| Data | Its accuracy (sibling reports) | In-China public-map threshold | Note |
|---|---|---|---|
| Sentinel-2 L2A | 10 m GSD; OSM fit ±10 m (geo.md) | imagery ≤0.5 m resolution (item 22): OK | used only as reference/texture if licensed |
| Copernicus DEM GLO-30 | LE90 1.92 m on the ZSSS tile (terrain.md) | heights ≤15 m accuracy (item 19); 秘密 above 25 km² outside military zones (cat. 23); the catalogue does not limit this to Chinese-produced data (§2.3) | foreign product, globally distributed; keep the detailed terrain extent small (D2) |
| OSM geometry | metre-level (geo.md) | 10 m (item 19) | public abroad; filter military (§2.6) |
| ADS-B positions | GNSS-grade | not a map rule; DSL/CEL frame (§3) | see adsb.md |

## 3. Data Security Law, Counter-espionage Law 2023, related rules: aircraft positions and airport data

Primary texts were read in `refs/cache/china_law/` [verified]. The ADS-B case history is in `adsb.md` §3. In short:

- **DSL** (in force 2021-09-01):
  - Art. 2(2) is extraterritorial (quoted in §2.5).
  - Art. 3: "数据处理，包括数据的收集、存储、使用、加工、传输、提供、公开等" (processing includes collecting, storing,
    using, processing, transmitting, providing and publishing).
  - Art. 32: "任何组织、个人收集数据，应当采取合法、正当的方式，不得窃取或者以其他非法方式获取数据。" (any organisation
    or individual collecting data must use lawful and proper means and must not steal or otherwise illegally obtain
    data.)
- **Counter-espionage Law** (revised 2023-04-26, in force 2023-07-01):
  - Art. 4(3) espionage includes foreign organisations or individuals "窃取、刺探、收买、非法提供国家秘密、情报以及其他关系国家安全和利益的文件、数据、资料、物品"
    (stealing, spying out, buying or illegally providing state secrets, intelligence and other documents, data, materials
    or items concerning national security and interests).
  - Art. 66 lets the MSS order foreigners to leave or deport them; a deported person "十年内不准入境" (may not re-enter
    for ten years).
- **NDSM Regulations** (in force 2025-01-01) Art. 62(4): "重要数据" (important data) is data "特定领域、特定群体、特定区域或者达到一定精度和规模"
  (in particular fields, groups or areas, or reaching a certain precision and scale) whose leak "可能直接危害国家安全" (may
  directly endanger national security).
- **CAAC Civil Aviation Data Management Measures (trial, 2025):**
  - Art. 3 scope: "在中华人民共和国境内进行民航数据的收集…公开等数据处理活动" (collecting … publishing civil-aviation
    data inside China).
  - Art. 5 includes data "通过收集、监测等方式获取并用于民用航空活动的原始数据及其衍生数据" (raw and derived data
    obtained by collection or monitoring and used for civil aviation).
  - Art. 31 promises an important-data catalogue. It was not found, so whether flight tracks are "important data" is
    **unverified**.
- **MSS actions** [secondary: state-media reposts]:
  - **2024-01:** foreign organisations recruited volunteers to deploy receivers "在我国境内航空枢纽附近" (near aviation
    hubs in China), collecting aircraft "型号、高度、经度、纬度、速度、航向" (type, altitude, longitude, latitude, speed,
    heading). "依法对有关人员进行处罚" (the people involved were penalised under law).
  - **2025-03** (radio): a hobbyist near a naval port set up a free foreign receiver that collected "船舶位置动态信息" (ship
    position data) and sent it abroad over Wi-Fi. "国家安全机关依法没收了郑某从事违法活动的设备，并对其实施了处罚" (state
    security confiscated Zheng's equipment and penalised him). The same pattern as ADS-B.
  - **2024-10:** a foreign company used a licensed Chinese firm, "以开展汽车智能驾驶研究为掩护" (under cover of
    autonomous-driving research), to survey; "B公司将测绘所得数据转移出境" (company B moved the survey data abroad).
  - **2025-09:** a domestic exporter's game-card map with wrong borders was seized as a "问题地图" (problem map).
  - **2026-01:** warning against illegal surveying "以学术交流、商务合作、文旅考察为掩护" (under cover of academic
    exchange, business cooperation or tourism).
- **Reading [inferred]:**
  - Every enforced case involves **activity in China**: hardware, surveying, annotation, export.
  - A foreign display of positions taken from foreign aggregators is several steps removed. It is not nothing, though:
    the data at its origin is what MSS calls illegally collected.
  - Showing it publicly is "公开" (publishing) under DSL Art. 3.
  - Keep the footprint small:
    - show civil traffic at and near the airport;
    - keep no long archive of PRC airspace;
    - no "interesting / military / state aircraft" features;
    - no solicitation of feeders.
  - `tools/rec/live_rec.py` records a 60 NM radius around ZSSS. Before any such recording is **committed** for snapshot
    mode, crop it to the airport vicinity and to civil traffic (D5).

## 4. OpenStreetMap and China

- **Blocked:** GreatFire, 2026-11-13: "As of the last test on 2026-08-24, http://www.openstreetmap.org is 100% blocked
  in mainland China". Interference recorded "since 2012-06-12". 70 of 72 tested OSM URLs are blocked, including
  `tile.` and `api.` [secondary].
- **OSM wiki (China, Legality):** "This seems to outlaw the entire OSM project and any participation or contribution."
  [secondary]
  - It also says of the Map Regs: "prohibits storing map data out of China. That's the entire OSM right there."
  - Its content rules are the 2003/2009 versions, repealed in 2023 (§2.2) → **outdated**.
- **Enforcement case, MSS 2026-10-17** [secondary: 科技日报 (Science and Technology Daily) repost of the MSS WeChat
  account]:
  - "许某…开始接触境外开放地图平台，并违法“翻墙”访问…多次标注军队等涉密敏感单位的位置信息" (Xu began using a foreign
    open-map platform, illegally getting round the firewall, and repeatedly tagged the locations of army and other
    classified, sensitive units).
  - Advice given: "不在地图平台标注任何涉及军事基地、涉密单位的地理信息" (don't tag any military bases or classified
    units on map platforms) and "不转发、不扩散任何标注有涉密地理信息的地图内容" (don't forward or spread any map
    content that tags classified geographic information).
  - The platform is not named. "境外开放地图平台" plus "翻墙" fits OSM [inferred].
- **Reading [inferred]:**
  1. Using OSM data abroad is lawful under ODbL; the attribution and share-alike duties are a separate key.
  2. Offering an OSM-based map *inside* China would be an unreviewed public map, against Map Regs Arts. 15 and 34.
  3. Contributors in China take the risk under Map Regs Art. 55 and the MSS practice above.
  4. Our own OSM edits from abroad, if any, should stick to aeroway corrections and never add sensitive features (D7).
  5. An app that fetches `tile.openstreetmap.org` at runtime will not load for users in China. Self-hosted tiles from
     OSM data avoid that technically, but not legally (point 2).

## 5. ATC audio

- **Radio Regulations** (无线电管理条例, State Council / CMC Order 672, in force 2016-12-01) [verified]:
  - Art. 2: scope is use of frequencies and stations "在中华人民共和国境内" (inside China).
  - Art. 27(2): licence exemption for "单收无线电台（站）" (receive-only stations).
  - Art. 41: "使用无线电台（站）的单位或者个人不得故意收发无线电台执照许可事项之外的无线电信号，不得传播、公布或者利用无意接收的信息。"
    (users of radio stations must not deliberately transmit or receive signals outside their licence, and must not
    spread, publish or use information received unintentionally.)
  - Art. 72(2): correction, confiscation of illegal gains, fine up to CNY 30,000; "造成严重后果的，吊销无线电台执照，并处3万元以上10万元以下的罚款"
    (with serious consequences: licence revocation plus a fine of CNY 30,000–100,000).
  - Art. 75: "（二）境外组织或者个人在我国境内进行电波参数测试或者电波监测；（三）向境外组织或者个人提供涉及国家安全的境内电波参数资料"
    ((2) foreign organisations or individuals testing or monitoring radio waves inside China; (3) giving foreign
    organisations or individuals PRC radio-parameter data concerning national security): correction; on refusal,
    confiscation of the equipment and a fine of CNY 30,000–100,000; serious consequences CNY 100,000–300,000.
    - Art. 75 does not name ADS-B, but it is the radio rule closest to a foreign-run receiver in China [inferred].
- **Criminal Law Art. 288** [verified]: setting up or using a station without permission, "干扰无线电通讯秩序，情节严重的"
  (disrupting radio communications, in serious cases), up to 3 years. This concerns transmitters and interference, not
  listening.
- **Hobbyist view** [unverified, personal note on GitHub, 2024]: "根据国内的现行法律，未禁止公众守听民航空管频率，但禁止擅自发射"
  (under current domestic law, the public is not prohibited from listening to civil ATC frequencies, but transmitting
  without permission is prohibited).
  - That squares with Art. 27(2), but not with **publishing** what is received: Art. 41 forbids deliberately receiving
    signals outside the licence, and spreading, publishing or using unintentionally received information [inferred].
- **LiveATC coverage of ZSSS:**
  - The same note: "中国机场暂时都搜不到（ZBAA, ZBAD, ZSPD, ZGGG, ZSSS, VMMC）" (no Chinese airport can be found at
    the moment) [unverified].
  - Our own checks:
    - `liveatc.net/search/?icao=ZSSS` returns a Cloudflare "Just a moment..." 403 [obs]. Not circumvented.
    - archive.org reports a Wayback snapshot of that search (2019-05-15), but web.archive.org is refused by this
      session's proxy [obs].
    - Web search found no ZSSS feed, only third-party pages linking generically to LiveATC [secondary].
  - GreatFire says liveatc.net was reachable from mainland China at its last test (2026-05-05) [secondary]. That is a
    network fact, not a legal one.
- **Reading [inferred]:**
  - A ZSSS stream would need a receiver in or near Shanghai publishing received ATC audio. That is the act Art. 41
    forbids (for unintentionally received information; deliberate reception outside a licence is barred too), and
    the profile MSS acted on in 2025.
  - So we must not encourage, fund or embed one.
  - The sfo3d ATC toggle should be **absent or disabled for SHA**. If wanted, a plain outbound link to LiveATC's search
    page is the most that can be justified (D4).
  - We never re-stream any audio ourselves.

## 6. Airline liveries and trademarks

- **PRC Trademark Law (2019)** [verified, CNIPA text]:
  - Art. 48: "本法所称商标的使用，是指将商标用于商品、商品包装或者容器以及商品交易文书上，或者将商标用于广告宣传、展览以及其他商业活动中，用于识别商品来源的行为。"
    (trademark use means putting the mark on goods, packaging or trade documents, or in advertising, exhibitions or other
    commercial activities, to identify the source of goods.)
  - Art. 57(1)–(2): infringement is unauthorised use "在同一种商品上" (on the same goods) or on similar goods causing
    confusion.
- **2026 revision** [verified for dates via CNIPA; secondary for text via Han Kun]:
  - Adopted 2026-06-26 (Presidential Order 77), in force **2027-01-01**.
  - New Art. 2 keeps "用于识别和区分商品来源" (to identify and distinguish the source of goods) and adds
    "包括通过互联网等信息网络实施的使用行为" (including use through the internet and other information networks).
- **Copyright:**
  - Logos and livery artwork can be 美术作品 (works of fine art) (Copyright Law Art. 3(4)) [verified].
  - Art. 24(10) allows "对设置或者陈列在公共场所的艺术作品进行临摹、绘画、摄影、录像" (copying, drawing,
    photographing or filming art works placed in public places) [verified].
  - Whether painted aircraft or terminal architecture fall under it is untested here [inferred].
- **US** (only if the owner's or the host's law is US; not assumed):
  - Nominative use lets one refer to a mark if (1) the product "cannot be readily identified without using the
    trademark", (2) only as much is used "as is necessary", and (3) nothing suggests "sponsorship or endorsement"
    [secondary: Wikipedia].
  - *Jack Daniel's v. VIP Products* (2023-06-08): "When a mark is used as a source identifier, the First Amendment does
    not demand a threshold inquiry." The noncommercial-use exclusion does not shield use "as a designation of source"
    [verified].
- **Reading [inferred]:**
  - Depicting real aircraft in their real liveries, non-commercially, without using any airline mark as the app's own
    branding, is outside PRC "trademark use" and inside the conventional fair-reference space abroad.
  - The airlines' copyright in logo artwork is the larger theoretical claim. In practice it is settled by takedown on
    request.
  - Keep the sfo3d notice (fleet.md §4.2): "Airline names, logos and liveries are trademarks of their respective owners.
    They are re-drawn here for a non-commercial depiction of real traffic; no endorsement is implied."
  - Add a contact for takedown requests.

## 7. GitHub and hosting

- GitHub publishes government takedowns "which led to content removal based on local law" [verified, `github/gov-takedowns`
  README].
  - The China folder holds 9 notices: 2016; MPS 2019 (six); BNIA (Beijing Network Industry Association) 2021 (two).
  - **None concerns maps, aviation or ADS-B** [obs: grep over the folder at commit `7f37611` of 2026-11-09].
  - The MPS letters ask GitHub, failing removal, to make content invisible to "来自中国IP地址的访问用户" (visitors from
    Chinese IP addresses) [verified].
- GitHub: "As of the last test on 2026-11-11, http://github.com is 80% disrupted in mainland China" [secondary,
  GreatFire].
- **Reading [inferred]:**
  - The likely official response to an objectionable foreign repo is a takedown request to GitHub, limited to China, or
    blocking. Personal action against a foreign owner abroad is unlikely.
  - Don't host the app or its data in mainland China; don't get an ICP filing; don't make a Chinese-language marketing
    push. Each of these would bring Map Regs Art. 2 into play.

## 8. Risk table

Likelihood is our judgement [inferred]. "PRC" means mainland China.

| # | Risk | Who it affects | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| R1 | Someone in the PRC helps us (ADS-B receiver, ATC stream, photos, GNSS tracks, drone, stand measurements, OSM edits) | that person | **High if it happens** (cases 2021, 2024, 2025, 2026) | fines, confiscation, detention; espionage framing | Never solicit or accept PRC-side data collection. State it in CONTRIBUTING. No feeder programme, no "send us photos". |
| R2 | Rendering, labelling or committing military / armed-police features near ZSSS (in OSM now) | owner, users who share screenshots, the repo | Medium (they are in OSM near ZSSS) | complaint, block, takedown request | Filter by tag and name in the OSM import (§2.6). Never label. CI check with `osm_sensitive.py` logic. |
| R3 | A metre-accurate WGS-84 3-D model of a PRC airport in a public repo | owner (mainly if travelling to the PRC), repo | Low (civil, public facility, data already public abroad); the verifier rates this as, if anything, understated: any modelled building meets the 5 % height test of catalogue item 24, and the "not made by licensed surveyors" argument is weak (§2.3) | entry refusal or questioning; repo block | Derive only from open foreign data. Keep the detailed extent ≤ aerodrome + margin (≤25 km² contiguous). No measured data from the PRC. No secret-catalogue shapes (DSM/point clouds of the city). |
| R4 | The app is used inside the PRC and counts as an unreviewed public map or internet map service | owner; users in the PRC | Low (enforcement = blocking) | block; in theory Map Regs Art. 54 fines | Don't target the PRC: no PRC hosting/CDN, no ICP, no Chinese-language promotion. "Not a map; not for navigation" notice. |
| R5 | Showing live and recorded PRC flight positions from foreign aggregators | owner (DSL Art. 2); data feeders | Low for the owner; high for feeders | as R1/R10 | Airport vicinity only, civil only, no long archives, no military/state highlighting. Crop recordings before committing (D5). See adsb.md. |
| R6 | ATC audio for ZSSS | stream provider in the PRC; owner if re-streaming | High for a provider; none if we drop the feature | Art. 41/72 fines (up to CNY 100k with licence revocation if serious); Art. 75 for foreign monitoring (up to CNY 300k); security framing | Drop the toggle for SHA (D4). |
| R7 | GCJ-02 approximation code in a public repo | owner | Very low (widely published) | reputational / takedown | Keep it out of the published app; decide on the repo (D8). Never convert data with it. |
| R8 | Airline trademarks or logo copyright (CES, CSH, CQH, DKH) | owner | Low (non-commercial depiction) | takedown request | sfo3d notice; no monetisation; no marks in the app name or icon; takedown contact. |
| R9 | Copyright in terminal architecture or in photos used as textures | owner | Low | takedown | Model geometry ourselves; never texture from photos or Google/Baidu/Amap imagery. |
| R10 | Owner or contributors travel to the PRC (or Hong Kong, not researched) after publishing | owner | Low, but uncertain | questioning, exit/entry bans (CEL Art. 66) | Owner decision (D11); optional professional advice before travel. |
| R11 | A "problem map": any national borders drawn wrongly by PRC standards (world view, route lines) | owner, PRC users | Low | block, seizure of exported goods (2025 case) | Draw no national borders; airport-local scene only. |
| R12 | Legal facts drift: OSM wiki and Wikipedia cite repealed rules; the 2023 Specification expires about 2028; the Trademark Law changes on 2027-01-01 | lead | Certain | wrong assumptions | Re-check before release; this report dates every quote. |

## 9. Decisions the owner must make

- **D1:** Accept the residual PRC-law risk of a public, metre-accurate WGS-84 3-D model of ZSSS, built abroad from open
  data (R3)? Yes or no.
- **D2:** Scene extent.
  - (a) Aerodrome plus about 1 km, with the contiguous detailed area ≤25 km²: recommended, conservative.
  - (b) A wider city/terrain context (larger area, higher R3).
- **D3:** Sensitive-feature filter for OSM and any other source: drop military, armed-police, police, prison and GNSS
  reference stations, and never label them. Recommended yes.
- **D4:** ATC audio for SHA.
  - (a) No toggle: recommended.
  - (b) A plain external link to LiveATC's search page, with "no feed known".
  - (c) Other: needs a lawful source, and none is known.
- **D5:** Live and snapshot data.
  - May recordings of PRC traffic be committed to the public repo at all?
  - If yes: radius (for example ≤30 km), altitude cap, civil-only filter, and duration.
  - The adsb.md decisions on providers also apply.
- **D6:** A CONTRIBUTING rule: no data collection inside the PRC, and no contributions of PRC-side photos, GNSS tracks,
  receivers or audio. Recommended yes.
- **D7:** OSM upstream edits at ZSSS from abroad: none, or aeroway-only (never sensitive features)?
- **D8:** Keep `tools/geo/gcj02.py`, the unofficial approximation, in the public repo, or keep it local?
- **D9:** Liveries: accept the non-commercial depiction posture with the sfo3d notice and a takedown contact for the four
  Shanghai carriers (and COMAC marks, fleet.md)?
- **D10:** Hosting and audience: hosts outside the PRC only? Chinese-language UI or not?
- **D11:** Personal travel risk for the owner and named contributors. Should anyone travelling take professional advice
  first?
- **D12:** Commission a professional legal opinion in the owner's jurisdiction and/or the PRC before public launch?

## 10. Facts table

| # | Topic | Value | Source URL | Date checked | Quote | Status |
|---|---|---|---|---|---|---|
| L1 | Surveying Law: definition of surveying | measuring, collecting, representing, processing and providing data on natural and man-made features | http://www.npc.gov.cn/zgrdw/npc/xinwen/2017-04/27/content_2020927.htm | 2026-11-13 | "本法所称测绘，是指对自然地理要素或者地表人工设施的形状、大小、空间位置及其属性等进行测定、采集、表述，以及对获取的数据、信息、成果进行处理和提供的活动。" | verified |
| L2 | Surveying Law: territorial scope | PRC territory and waters | same | 2026-11-13 | "在中华人民共和国领域和中华人民共和国管辖的其他海域从事测绘活动，应当遵守本法。" | verified |
| L3 | Surveying Law Art. 8: foreigners | approval from the State Council authority with the military, a Chinese partner, no secrets | same | 2026-11-13 | "应当与中华人民共和国有关部门或者单位合作进行，并不得涉及国家秘密和危害国家安全。" | verified |
| L4 | Surveying Law Art. 51: penalty | CNY 100k–500k; serious: 500k–1M plus expulsion | same | 2026-11-13 | "情节严重的，并处五十万元以上一百万元以下的罚款，限期出境或者驱逐出境" | verified |
| L5 | Surveying Law Art. 38: maps | maps follow national standards, content rules and review | same | 2026-11-13 | "地图的编制、出版、展示、登载及更新应当遵守国家有关地图编制标准、地图内容表示、地图审核的规定。" | verified |
| L6 | Surveying Law: dates | revised 2017-04-27, in force 2017-07-01 | same | 2026-11-13 | "本法自2017年7月1日起施行。" | verified |
| L7 | Foreign-surveying measures Art. 7 | joint ventures may not compile true-3-D or navigation maps | https://www.gov.cn/zhengce/2019-08/13/content_5711393.htm | 2026-11-13 | "（五）地形图…和真三维地图的编制；（六）导航电子地图编制" | verified |
| L8 | Foreign-surveying measures Art. 19 | survey results taken abroad without approval: fine up to CNY 30k | same | 2026-11-13 | "未经依法批准将测绘成果携带或者传输出境的，由国务院自然资源主管部门处3万元以下罚款" | verified |
| L9 | Map Regs: order and dates | Order 664, signed 2015-11-26, in force 2016-01-01 | https://www.gov.cn/zhengce/content/2015-12/14/content_10403.htm | 2026-11-13 | "《地图管理条例》已经2015年11月11日国务院第111次常务会议通过，现予公布，自2016年1月1日起施行。" | verified |
| L10 | Map Regs Art. 2: scope | inside the PRC | same | 2026-11-13 | "在中华人民共和国境内从事向社会公开的地图的编制、审核、出版和互联网地图服务以及监督检查活动，应当遵守本条例。" | verified |
| L11 | Map Regs Art. 15: map review | public maps reviewed; simple maps exempt | same | 2026-11-13 | "向社会公开的地图，应当报送有审核权的测绘地理信息行政主管部门审核。但是，景区图、街区图、地铁线路图等内容简单的地图除外。" | verified |
| L12 | Map Regs Art. 22: 审图号 | must be shown | same | 2026-11-13 | "经审核批准的地图，应当在地图或者附着地图图形的产品的适当位置显著标注审图号。" | verified |
| L13 | Map Regs Art. 34: servers | map-data servers in the PRC | same | 2026-11-13 | "互联网地图服务单位应当将存放地图数据的服务器设在中华人民共和国境内" | verified |
| L14 | Map Regs Art. 55: uploads | uploading barred content: fine up to CNY 100k | same | 2026-11-13 | "通过互联网上传标注了含有按照国家有关规定在地图上不得表示的内容的，责令改正，给予警告，可以处10万元以下的罚款" | verified |
| L15 | Public Map Content Spec: identity | 自然资规〔2023〕2号, 2023-02-06 | https://www.gov.cn/zhengce/zhengceku/2023-02/17/content_5741977.htm | 2026-11-13 | "发文字号： 自然资规〔2023〕2号 … 成文日期： 2023年02月06日" | verified |
| L16 | Spec item 19: accuracy cap | ≤10 m planar, ≤15 m height for maps of the PRC | https://www.gov.cn/gongbao/content/2023/content_5752310.htm | 2026-11-13 | "表现地为我国境内的地图平面精度应当不优于10米（不含），高程精度应当不优于15米（不含）" | verified |
| L17 | Spec item 20(1): military | military airports, barracks, military rail spurs etc. barred | same | 2026-11-13 | "军用机场、港口、码头，营区、训练场、试验场…军用公路、铁路专用线" | verified |
| L18 | Spec item 20(5): joint-use airports | important facilities of military-civil airports barred | same | 2026-11-13 | "（五）军民合用机场、港口、码头的重要设施；" | verified |
| L19 | Spec item 18: public facilities | may show name and public attributes | same | 2026-11-13 | "用于公共服务的设施，可在地图上表示其名称等可公开属性信息。" | verified |
| L20 | Spec item 22: imagery | ≤0.5 m resolution | same | 2026-11-13 | "表现地为我国境内的遥感影像，地面分辨率不得优于0.5米" | verified |
| L21 | Spec item 23: validity and repeal | 5 years; repeals the 2003 and 2009 rules | same | 2026-11-13 | "本规范自颁布之日起实施，有效期5年。…（国测法字〔2003〕1号）和…（国测图字〔2009〕2号）同时废止。" | verified |
| L22 | Secret catalogue item 3 | the secrecy-processing algorithm is 机密 | https://www.mfa.gov.cn/wjb_673085/zzjg_673183/bjhysws_674671/bhflfg/ldbjchxgfl/202303/P020230313534680395614.pdf | 2026-11-13 | "国家认定的地理信息保密处理技术算法及参数 机密 长期" | verified |
| L23 | Secret catalogue items 23 and 24 (separate) | item 23 DEM/DSM: planar ≤10 m or height ≤15 m; item 24 3-D models, point clouds etc.: planar ≤10 m or relative object-height ≤5 %; both outside military zones, >25 km² contiguous = 秘密 | same | 2026-11-13 | "…且连续覆盖范围超过 25 平方千米的三维模型、点云、倾斜影像、实景影像、导航电子地图等实测成果 秘密" | verified |
| L24 | Secret catalogue item 25 | ±10 m coordinates of important facilities related to the military or security = 秘密 | same | 2026-11-13 | "与军事、国家安全相关的国民经济重要设施精度优于（含）±10 米的点位坐标及其名称属性" | verified |
| L25 | Secret catalogue Note 1: where secrets arise | at licensed surveyors and military surveying units, which mark them; the third column (知悉范围) is the knowledge scope (approved holders and users), not the producer, and neither limits the items to their products | same | 2026-11-13 | "国家秘密事项由从事测绘地理信息活动的测绘资质单位、军队测绘部门（单位）产生" | verified |
| L26 | GCJ-02 legal basis | GB 20263-2006 §4.1 (via Wikipedia); official name | https://en.wikipedia.org/w/index.php?title=Restrictions_on_geographic_data_in_China&action=raw | 2026-11-13 | "Technical spatial processing must be applied to electronic navigational maps prior to publication, sales, redistribution, and usage." / "地形图非线性保密处理算法" | secondary |
| L27 | GCJ-02 in the primary texts | not named in the Surveying Law, Map Regs, 2023 Spec or 2020 catalogue | the four above | 2026-11-13 | (absence) | verified (absence) |
| L28 | State Secrets Law: definition | matters concerning security and interests, set by legal procedure | http://big5.www.gov.cn/gate/big5/www.gov.cn/yaowen/liebiao/202402/content_6934648.htm | 2026-11-13 | "國家秘密是關係國家安全和利益，依照法定程序確定，在一定時間內只限一定範圍的人員知悉的事項。" | verified |
| L29 | State Secrets Law Art. 36 | aggregation risk | same | 2026-11-13 | "防範數據匯聚、關聯引發的泄密風險" | verified |
| L30 | Criminal Law Art. 8 | foreigners abroad: minimum 3 years, dual criminality | https://fgk.chinatax.gov.cn/zcfgk/c100009/c5212248/content.html | 2026-11-13 | "外国人在中华人民共和国领域外对中华人民共和国国家或者公民犯罪，而按本法规定的最低刑为三年以上有期徒刑的，可以适用本法，但是按照犯罪地的法律不受处罚的除外。" | verified (official government mirror; consolidated 2023-12-29) |
| L31 | Criminal Law Art. 111 | supplying secrets or intelligence abroad: 5–10 years; minor cases under 5 years (no universal 5-year minimum) | same | 2026-11-13 | "为境外的机构、组织、人员窃取、刺探、收买、非法提供国家秘密或者情报的，处五年以上十年以下有期徒刑" … "情节较轻的，处五年以下有期徒刑、拘役、管制或者剥夺政治权利" | verified |
| L32 | NPC Q&A on Art. 8 | must target the PRC or its citizens | http://www.npc.gov.cn/zgrdw/npc/flsyywd/flwd/2002-04/17/content_292709.htm | 2026-11-13 | "一是针对中华人民共和国国家或者公民犯罪，如犯罪的对象直接危害了我国国家的安全和利益" | verified (explanatory) |
| L33 | DSL Art. 2(2) | extraterritorial if harm | http://www.npc.gov.cn/npc/c2/c30834/202106/t20210610_311888.html | 2026-11-13 | "在中华人民共和国境外开展数据处理活动，损害中华人民共和国国家安全、公共利益或者公民、组织合法权益的，依法追究法律责任。" | verified |
| L34 | DSL Art. 3 | processing includes publishing | same | 2026-11-13 | "数据处理，包括数据的收集、存储、使用、加工、传输、提供、公开等。" | verified |
| L35 | DSL reading by a PRC firm | applies to foreign individuals | https://en.zhonglun.com/research/articles/52403.html | 2026-11-13 | "The DSL not only applies to domestic companies in China, but also covers data-related activities conducted by foreign entities and individuals." | secondary |
| L36 | CEL Art. 4(3) | supplying data concerning security to foreign organisations = espionage | http://www.npc.gov.cn/c2/c30834/202304/t20230426_429064.html | 2026-11-13 | "窃取、刺探、收买、非法提供国家秘密、情报以及其他关系国家安全和利益的文件、数据、资料、物品" | verified |
| L37 | CEL Art. 66 | foreigners: order to leave, deportation, 10-year entry ban | same | 2026-11-13 | "自被驱逐出境之日起十年内不准入境" | verified |
| L38 | NDSM Regs Art. 62(4) | important data includes precision and scale | https://www.gov.cn/gongbao/2024/issue_11646/202410/content_6980863.html | 2026-11-13 | "重要数据，是指特定领域、特定群体、特定区域或者达到一定精度和规模…可能直接危害国家安全…的数据" | verified |
| L39 | CAAC data measures Art. 3 | scope: inside the PRC | http://www.caac.gov.cn/XXGK/XXGK/GFXWJ/202503/P020250331376967414116.pdf | 2026-11-13 | "在中华人民共和国境内进行民航数据的收集 、 存储 、 使用 、 加工 、 传输 、 提供 、 公开等数据处理活动及其监管" (pdftotext spacing kept) | verified |
| L40 | CAAC important-data catalogue | promised (Art. 31); not found | same | 2026-11-13 | "制定民航领域重要数据和核心数据目录" | verified (text); catalogue unverified |
| L41 | MSS 2024 ADS-B statement | receivers near aviation hubs; penalties | http://www.ce.cn/xwzx/shgj/gdxw/202401/06/t20240106_38856111.shtml | 2026-11-13 | "远程指导“志愿者”在我国境内航空枢纽附近投放，以实现对周边一定范围内飞机的型号、高度、经度、纬度、速度、航向等信息的自动采集" | secondary |
| L42 | MSS 2025 radio case | receive-only device sent ship positions abroad; penalised | https://www.secrss.com/articles/76950 | 2026-11-13 | "该设备搜集了军港附近海域大量船舶位置动态信息，并通过Wi-Fi实时向境外传输…国家安全机关依法没收了郑某从事违法活动的设备，并对其实施了处罚。" | secondary |
| L43 | MSS 2024 surveying case | foreign company via a licensed PRC firm, data exported | https://www.secrss.com/articles/71258 | 2026-11-13 | "以开展汽车智能驾驶研究为掩护，在我国内非法开展地理信息测绘活动" | secondary |
| L44 | MSS 2025 problem map | wrong borders on an exported product, seized | https://www.secrss.com/articles/83070 | 2026-11-13 | "属于典型的“问题地图”。该批物品已被依法扣留处理。" | secondary |
| L45 | MSS 2026-01 warning | illegal surveying under academic, business or tourism cover | https://www.news.cn/politics/20260113/5fe35636f177440eb90777c23e71e0c8/c.html | 2026-11-13 | "常以学术交流、商务合作、文旅考察为掩护，在我关键领域、重点目标处开展非法测绘活动" | secondary |
| L46 | MSS 2026-10 open-map case | a person in the PRC tagged sensitive units on a foreign open map | https://www.stdaily.com/web/gdxw/2026-10/17/content_597933.html | 2026-11-13 | "开始接触境外开放地图平台，并违法“翻墙”访问…多次标注军队等涉密敏感单位的位置信息" | secondary |
| L47 | MSS 2026-10 advice | don't tag or forward maps with sensitive info | same | 2026-11-13 | "不转发、不扩散任何标注有涉密地理信息的地图内容" | secondary |
| L48 | OSM blocked in the PRC | 100 % blocked (last test 2026-08-24), since 2012 | https://en.greatfire.org/www.openstreetmap.org | 2026-11-13 | "As of the last test on 2026-08-24, http://www.openstreetmap.org is 100% blocked in mainland China" | secondary |
| L49 | OSM wiki on legality | project effectively illegal in the PRC | https://wiki.openstreetmap.org/w/index.php?title=China&action=raw | 2026-11-13 | "This seems to outlaw the entire OSM project and any participation or contribution." | secondary |
| L50 | OSM wiki precision rule | "50 meters" (2009 rule), repealed in 2023 | same + L21 | 2026-11-13 | "no prisons, drug rehabs, dams, or any locations more precise than 50 meters" | contradicted: the 2023 Spec repealed the 2009 rule; the current cap is 10 m (L16) |
| L51 | ZSSS class | CIVIL/4E | aip.md row 14 (AIP mirror M1) | 2026-11-13 | "CIVIL/4E" | secondary |
| L52 | ZSSS military history | military until 1963; civil reopening April 1964 | https://en.wikipedia.org/w/index.php?title=Shanghai_Hongqiao_International_Airport&action=raw | 2026-11-13 | "From late 1963, it was rebuilt for civilian use and was reopened in April 1964." | secondary |
| L53 | ZSSS joint-use history | 1963 joint military-civil, civil-only from about 1971 | https://www.sohu.com/a/15058612_119207 (search summary only) | 2026-11-13 | "将虹桥机场扩建为军民合用的国际机场" | unverified |
| L54 | AIP withholds threshold coordinates | Nil for 18L/36R/18R/36L | aip.md row 21 | 2026-11-13 | "Nil" | secondary |
| L55 | Military-tagged OSM objects near ZSSS | 6 distinct elements (3 rail ways tagged `usage=military`; 3 `landuse=military` areas, 2 of them armed police) | `refs/cache/osm/` (OSM API extracts, ODbL) via `tools/law/osm_sensitive.py` | 2026-11-13 | ids, names, coordinates and distances deliberately withheld | obs |
| L56 | Radio Regs Art. 27(2) | receive-only stations need no licence | https://www.gov.cn/gongbao/content/2016/content_5148745.htm | 2026-11-13 | "（二）单收无线电台（站）" | verified |
| L57 | Radio Regs Art. 41 | no deliberate reception outside the licence; no spreading, publishing or use of unintentionally received information | same | 2026-11-13 | "不得传播、公布或者利用无意接收的信息" | verified |
| L58 | Radio Regs Art. 72(2) | fine up to CNY 30k; serious: licence revoked plus CNY 30k–100k | same | 2026-11-13 | "（二）故意收发无线电台执照许可事项之外的无线电信号，传播、公布或者利用无意接收的信息" (with "可以并处3万元以下的罚款；造成严重后果的，吊销无线电台执照，并处3万元以上10万元以下的罚款") | verified |
| L58a | Radio Regs Art. 75(2)/(3) | foreign radio monitoring in the PRC, or supplying security-related PRC radio data abroad: CNY 30k–100k after refusing to correct; serious CNY 100k–300k | same | 2026-11-13 | "（二）境外组织或者个人在我国境内进行电波参数测试或者电波监测；（三）向境外组织或者个人提供涉及国家安全的境内电波参数资料" | verified (added from verify_licences_law.md) |
| L59 | Criminal Law Art. 288 | unlicensed stations disrupting radio: up to 3 years | https://fgk.chinatax.gov.cn/zcfgk/c100009/c5212248/content.html | 2026-11-13 | "擅自设置、使用无线电台（站），或者擅自使用无线电频率，干扰无线电通讯秩序，情节严重的，处三年以下有期徒刑" | verified |
| L60 | Hobbyist view on listening | listening not prohibited; transmitting is | https://github.com/Panic-W/KWSNote (file 航空波段收听与录音.md, commit 842c5b1) | 2026-11-13 | "根据国内的现行法律，未禁止公众守听民航空管频率，但禁止擅自发射" | unverified |
| L61 | LiveATC and ZSSS | no Chinese airport found on LiveATC (2024) | same | 2026-11-13 | "中国机场暂时都搜不到（ZBAA, ZBAD, ZSPD, ZGGG, ZSSS, VMMC）" | unverified |
| L62 | LiveATC reachable by us | 403 Cloudflare challenge | https://www.liveatc.net/search/?icao=ZSSS | 2026-11-13 | "<title>Just a moment...</title>" | obs |
| L63 | Wayback copy of the LiveATC search | exists (2019-05-15) but not readable here | https://archive.org/wayback/available?url=liveatc.net/search/?icao=ZSSS | 2026-11-13 | "http://web.archive.org/web/20190515050936/https://www.liveatc.net/search/?icao=zsss" | obs (content unverified) |
| L64 | LiveATC from the PRC | reachable at the last test 2026-05-05 | https://en.greatfire.org/www.liveatc.net | 2026-11-13 | "As of the last test on 2026-05-05 (6 mo ago), it was reachable in mainland China." | secondary |
| L65 | Trademark Law 2019 Art. 48 | use = commercial source identification | https://www.cnipa.gov.cn/art/2019/6/25/art_104_67808.html | 2026-11-13 | "本法所称商标的使用，是指…将商标用于广告宣传、展览以及其他商业活动中，用于识别商品来源的行为。" | verified |
| L66 | Trademark Law 2026 revision | adopted 2026-06-26, Order 77, in force 2027-01-01 | https://www.cnipa.gov.cn/art/2026/7/3/art_55_207047.html | 2026-11-13 | "新修订的商标法将于2027年1月1日起施行" | verified (official site, interview) |
| L67 | 2026 law, new Art. 2 | adds internet use; keeps source identification | https://www.hankunlaw.com/upload/portal/20260721/b21f0150391aa95b6f48074c16179e0c.pdf | 2026-11-13 | "前款所称商标的使用，包括通过互联网等信息网络实施的使用行为。" | secondary (law-firm comparison table) |
| L68 | Copyright Law Art. 24(10) | copying art works in public places allowed | https://ipr.mofcom.gov.cn/law/detail.shtml?id=1969 | 2026-11-13 | "（十）对设置或者陈列在公共场所的艺术作品进行临摹、绘画、摄影、录像" | verified (government mirror) |
| L69 | US nominative use | three-part test | https://en.wikipedia.org/w/index.php?title=Nominative_use&action=raw | 2026-11-13 | "The user does nothing to suggest sponsorship or endorsement by the trademark holder." | secondary |
| L70 | US Jack Daniel's (2023) | Rogers is not a threshold test when a mark is used as a source identifier | https://www.supremecourt.gov/opinions/22pdf/22-148_3e04.pdf | 2026-11-13 | "When a mark is used as a source identifier, the First Amendment does not demand a threshold inquiry." | verified |
| L71 | GitHub China takedowns | 9 notices, none about maps or aviation | https://github.com/github/gov-takedowns (China/, commit 7f37611) | 2026-11-13 | README: "This repository contains official government requests which led to content removal based on local law." | verified (record) / obs (topic grep) |
| L72 | GitHub from the PRC | 80 % disrupted (2026-11-11) | https://en.greatfire.org/github.com | 2026-11-13 | "As of the last test on 2026-11-11, http://github.com is 80% disrupted in mainland China" | secondary |
| L73 | sfo3d trademark notice | text reused for SHA | `sfo3d/docs/ATTRIBUTION_models.md` (via fleet.md §4.2) | 2026-11-13 | "They are re-drawn here for a non-commercial depiction of real traffic; no endorsement is implied." | secondary (sibling report) |

## 11. Not verified, and why

- **The LiveATC feed list for ZSSS:** Cloudflare 403, and Wayback is refused by the proxy. The only evidence is a 2024
  personal note. Ask the owner to open `https://www.liveatc.net/search/?icao=ZSSS` in a browser and send a screenshot.
- **The CAAC important-data catalogue and MH/T 3039-2025** (civil-aviation data grading standard): the host reset the
  connection.
- **The GB 20263-2006 text:** seen only through Wikipedia.
- **The 2026 Trademark Law full text:** only the official interview and a law-firm comparison table were read.
- **The ZSSS military history** in Chinese sources: search summary only.
- **Hong Kong SAR law** (relevant only if the owner travels there) and the owner's home-country law were not researched.

## 12. Files

- Cached: `sha3d/refs/cache/law/*/` plus `sha3d/refs/cache/law/SOURCES.json`.
- Redistributable:
  - the PRC legal texts (law and regulation text only, under Copyright Law Art. 5(1));
  - the US Supreme Court opinion (US government work);
  - Wikipedia and OSM-wiki wikitext (CC BY-SA, with attribution).
- Not redistributable: news, law-firm and GreatFire pages, the KWSNote file, and the GitHub notices. Quote only.
- Scripts: `sha3d/tools/law/fetch.sh`, `fetch_log.tsv`, `write_sources.py`, `docx_text.py`, `osm_sensitive.py`.
