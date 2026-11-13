# SHA Live 3D (Shanghai Hongqiao, ZSSS): Phase 0 plan

Status: Phase 0 (research and plan) written 2026-11-13. There is no app code, no models and no renders yet. **The
go/no-go question has a clear answer: no open ADS-B source sees Hongqiao (§3).** That changes the scope, so work stops
here until the owner decides (§6, Q1).

This is a sibling of `sfo3d/` (SFO Live 3D). Its fork base is sfo3d commit **e3218d6**. It does not modify `sfo3d/`,
`pc12/` or `hwd3d/`. Anything that belongs in sfo3d goes to `docs/requests_to_sfo3d.md`. The Hayward fork
(`origin/claude/hwd-live-3d`, `hwd3d/docs/PLAN.md` and `phase2_fork_map.md`) was read as a pattern only.

Evidence: eight research reports and two adversarial verification reports are in `docs/phase0/`. They are the
detailed sources for every row below:

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
| `verify_official.md`, `verify_licences_law.md` | Adversarial verification. Their corrections are already applied in this plan. |

Status labels used below:

| Label | Meaning |
|---|---|
| **verified** | Primary or official source read. |
| **AIP (mirror)** | AIP value read in an unofficial mirror copy (EFF 2026-07-08), because the official eAIP needs a login (§1, Q2). |
| **secondary** | Wikipedia, OurAirports, news. |
| **obs** | Our own measurement. |
| **inf** | Inferred. |

---

## 1. Verified facts

All rows were checked on 2026-11-13.

| Fact | Value | Source | Status |
|---|---|---|---|
| Identity | **ZSSS / SHA, "SHANGHAI/Hongqiao" (上海/虹桥)**. No source contradicts the owner's choice. | CAAC eAIP public chart list `https://www.eaipchina.cn/eaip/airportChart/listPublish`; SAA code list (avinex.com) | verified |
| Official eAIP access | The AIP is free but needs a **registered login**. AD 2 ZSSS (AMDT 11/2026, eff. 28 Oct 2026) was **not** read. AMDT 12/2026 (eff. 26 Nov 2026) changes the WDI positions at ZSSS. No licence or terms of use are published, so treat the AIP as reference only. | `https://www.eaipchina.cn/` | verified |
| ARP | **N31°11.8′ E121°20.1′** (31.19667, 121.33500), "Centre of RWY18L/36R". It is published only to 0.1′ (about ±90 m). | AD 2.2 (mirror) | AIP (mirror) |
| OurAirports ARP | 31.198104, 121.33426 is **174 m from the AIP ARP** (bearing 336°). It is a generic point between the runways, **not** the official ARP. Identity is unaffected, but sha3d will use the AIP definition (runway-centre based) once it is read from the official eAIP. | ourairports-data `airports.csv` | **contradicted** (minor) |
| Datum | AD 2 states none. AIP China GEN 2.1 reportedly moved to WGS-84 in 2012 (ICAO APAC paper; HTTP 403). OSM is WGS-84 at ZSSS (row "GCJ-02 check"). | ICAO APAC 2012 IP03 | unverified |
| Elevation / variation | AD ELEV **3.0 m**; VAR 5°46′W (2017), −42″/yr. Height datum unstated: possibly Wusong (= 1985 national + 1.680 m). The DEM gives 1.5 m (EGM2008); the EGM2008 geoid N is +11.24 m. | AD 2.2 (mirror); terrain.md | AIP (mirror); inf |
| Hours / curfew | AD **H24**. **No scheduled flights 00:00–06:00 local** since winter 2010/11 (delays and diversions allowed). No landings on 18R/36L 1600–2300 UTC. No towing across runways 2200–1600 UTC. | AD 2.3 (mirror); news.sina.cn 2010 | AIP (mirror); secondary |
| RWY 18L/36R (east) | 3400 × 45 m, asphalt with concrete ends. 177.34° true. THR and END each displaced 100 m. TORA 3300, LDA 3200. THR elevations 2.1 m / 2.7 m. **Threshold coordinates not published** ("Nil"). | AD 2.12/2.13 (mirror); OSM way 16714125 (177.34°, agrees) | AIP (mirror) |
| RWY 18R/36L (west) | 3300 × 60 m, concrete. Opened 11 Mar 2010. THR displaced 300 m, END 150 m. SWY 150 m, CWY 60 × 300 m. TORA 3150, LDA 2850. | AD 2.12 (mirror); avinex.com | AIP (mirror); verified (date) |
| Runway layout | **Close-spaced parallels, 365 m apart, north ends aligned** (OSM: 365.2 m). Order W→E: TWY C, 36L, TWY B, 36R, TWY A. Usual mode is east landings, west take-offs (东落西起). | AD 2 (mirror); eAIP situation sheet (official); CAAC 2010; caacnews 2021 | verified / secondary |
| Lighting | PALS CAT I at all four ends. PAPI 3° (left on 18L/18R, right on 36R/36L). No TDZ lights. RCLL and REDL. RWSL with THL and REL. Stop bars on the rapid exits. | AD 2.14 (mirror) | AIP (mirror) |
| Taxiways | A, A1–A4, B, B1–B8, BN, BS, C, C1–C4, D, D3–D17, H1–H7, K1–K7 (no K3), L01, N, S, T1, T6. End-around routes N (BN→N) and S (BS→S), 23 m wide, for spans ≤ 36 m. | AD 2.9 / chart (mirror); caacnews 2021 | AIP (mirror) |
| Stands | **161 designators ≈ 155 physical stands**; 6 are alternatives or overlays (216E, 220E, 281E, 413E, 404C, 408C). Series 1xx (T1), 2xx (T2), 3xx (incl. business 310–312), 4xx, 5xx, 6xx, plus temporary TP01–TP08. All taxi-in, push-back. The largest is 248 (B747-8). **No stand coordinates in the AIP.** | APDC chart (mirror) | AIP (mirror) |
| Contact stands / bridges | **54 stands have VDGS** (13 at T1, 41 at T2). caacnews gives 54 contact stands. So the bridge stands are inferred to equal the VDGS stands. The 2010 T2 bridge count is contradicted (43 vs 45). | AD 2 (mirror); caacnews 2023 | inf |
| Stands in OSM | **164 `parking_position` nodes with ref** (101–608). 149 refs agree with the AIP. Only in OSM: 238A, 239, 240A, 258, 259A, 301–309, 604. Only in the AIP: the E/C overlays, 414–416, 514–516. 159 of 164 are also in the X-Plane Gateway (median 5.8 m apart). The 2026 APDC notes "Stand number adjusted". | OSM API; Gateway 107152 | obs |
| Terminals | **T1** (renovated 2014–2018, 130,000 m², international/HMT at islands A/B, Spring etc. at D; gates T01–T27). **T2** (opened 16 Mar 2010, 362,600 m²; gates 21–75). Airlines per terminal are on an undated SAA page. | avinex.com (SAA) | verified |
| Tower | OSM `aircraft_control` node 3342630333 at 31.19667, 121.34153 (east side) = AIP obstacle "Control TWR", 111° MAG / 520 m from the RWY18L/36R centre, **47 m**, lit. Its form and year are unknown, so photos are needed. Frequencies TWR(E) 118.1 and TWR(W) 118.65: whether these are one cab or two is unknown. | OSM; AD 2.10 (mirror) | secondary (verifier-corrected) |
| Frequencies | ATIS 132.25 (D-ATIS). DEL 121.75 (0000–1200 UTC, DCL). GND(E) 121.6, GND(W) 121.9. TWR(E) 118.1, TWR(W) 118.65. APN(E) 121.675, APN(W) 121.95. Shanghai APP 125.4 / 126.65 (H24). | AD 2.18 (mirror) | AIP (mirror) |
| Movements | 2023 **266,813**; 2024 **275,288**; 2025 **282,692** (774.5/day). Jan–Sep 2026: 783.4/day (monthly 757–806). Winter 2026/27 plan: 802/day. International 2.5 % plus HK/Macau/Taiwan 3.9 % (2025, CAAC). | CAAC 民航机场生产统计公报 xlsx 2023–2025; SIAC monthly briefs | verified |
| Capacity | Declared 43/h (2011). The 2023 increase to 48→50/h is unconfirmed. Observed peak 59/h (2021). No published hourly profile. | CAAC 2016 doc; caacnews | verified / secondary / unverified |
| Business aviation | FBO and terminal opened 2010 (3,100 m² terminal, 4,500 m² hangar, 3 stands, then a SAA + Hawker Pacific JV). The current operator is unverified. | avinex.com | verified (2010) |
| GCJ-02 check | **OSM at ZSSS is WGS-84.** Measured OSM − Sentinel-2: dx −3.1/−1.6 m, dy −1.0/−0.1 m (two scenes, 54 and 43 straight runs, ±0.7 m). The predicted GCJ-02 shift would be about 484 m (+434 E, −214 N). NDVI search over ±900 m is minimal at (0,0). Absolute accuracy is limited to about ±10 m by the Sentinel-2 geolocation spec. Changesets name only Bing/Maxar/Esri/Mapbox, never Baidu/Amap. | geo.md, `docs/phase0/geo_overlay.jpg` | obs |
| OSM state | Aerodrome relation 21913346 was re-created **2026-11-06**, so OSM is being edited now: pin by ID and date. Missing: jet bridges, runway/taxiway surface polygons, threshold nodes, hold designators and building heights. Only 27 % of taxiway ways have a ref. Some centrelines are 5–13 m off the imaged pavement. **6 military or armed-police elements lie 1.2–3.3 km from the ARP** (ids withheld). | OSM API, `tools/law/osm_sensitive.py` | obs |
| Fleet | Hub carriers China Eastern (MU), Shanghai Airlines (FM) and Juneyao (HO); base of Spring (9C). These four hold 75 % of airline–destination pairs (secondary). Estimated type mix: A320 family 45–55 %, 737 23–37 %, wide-bodies 10–20 %, C919 1–5 %, C909 (= ARJ21; ICAO AJ27) 0–2 %. **This is an estimate, not a measurement** (§3). | fleet.md; COMAC; ICAO Doc 8643 | secondary / inf |
| ATC audio | **No lawful verified ZSSS source.** LiveATC returns 403 to automated reads, and a 2024 note says it lists no Chinese airport (unverified). Under PRC Radio Regulations Art. 41, users must not spread received information (Art. 72: fines up to CNY 30k, or 30–100k if serious). Art. 75 covers foreign monitoring inside the PRC. | law.md, verify_licences_law.md | verified (law) / unverified (LiveATC) |

## 2. Data inventory and licences

| Data | Source | Licence (quoted in the reports) | Redistribute? | Use / status |
|---|---|---|---|---|
| Runways, stands, frequencies, lighting, hours | CAAC eAIP AD 2 ZSSS | none published; treat as all rights reserved | **no** (facts cited with source only) | Needs login (Q2). Values above come from a mirror copy kept local in `refs/cache/aip/`, not committed. |
| Airfield geometry, stands 101–608, taxiways, aprons, buildings, tower | OpenStreetMap (API, 2026-11-13) | ODbL 1.0 | yes, with the share-alike and attribution terms; **after the sensitive-feature filter** (law R2) | Main geometry source. Extract is local; committed once filtered (Q3). |
| Optical imagery | Copernicus Sentinel-2 L2A (Earth Search COGs), scenes 2026-10-14 and 2026-02-21 | Sentinel Data Legal Notice: reproduction, distribution and adaptation free | yes: "Contains modified Copernicus Sentinel data 2026" | Crops committed with this plan (`refs/cache/s2/`). 10 m: alignment and ground colour, not markings. |
| SAR imagery 0.35 m | Umbra Open Data, 2024-06-02 spotlight | CC BY 4.0 | yes, with attribution | The only open sub-metre image of the airfield. Outlines only (radar; 3–4 m east GEC offset). Q6. |
| DEM | Copernicus DEM GLO-30 (tile N31E121, EGM2008) | COP-DEM-GLO-30-F licence (free; notice required) | yes (crop, with notice) | Airfield heights are airport-edited 0.5 m planes: useful for surroundings only. |
| Land cover | ESA WorldCover 2021 v200 | CC BY 4.0 | yes | Surroundings materials; it misclassifies airfield grass as cropland. |
| Statistics | CAAC statistics bulletins, SIAC briefs | none published | no (facts only) | Denominator for coverage. |
| ADS-B archive | adsb.lol globe_history (GitHub releases) | ODbL 1.0 | yes | Coverage measurement (§3); `refs/cache/adsb/`. |
| ADS-B live | adsb.lol API | ODbL 1.0; **now 500 requests/day per IP without a key** (published; our 509 keyless requests on 13 Nov met only 6 sporadic 429s, so no hard cut-off was observed) | yes | Near-zero value at ZSSS (§3). Our recorder now polls every 180 s to stay within the published quota. |
| ADS-B live | adsb.fi | personal non-commercial; no licensing | **no** | Measurement only, never committed. |
| ADS-B live | OpenSky | written licence needed for live/operational use; identifiers anonymised in publications | **no** | Measurement only. |
| ADS-B live | airplanes.live | contributors only since Sep 2026 (secondary) | – | Not usable. |
| Commercial feeds | VariFlight DataWorks, Aireon via FlightAware AeroAPI Premium (≥ $1,000/month), Spire | contract; no redistribution | **no** | Only path to observed airborne traffic (Q1). |
| Aircraft models | sfo3d's 23 converted models (FlightGear, GPL-2.0; A380 with a CC BY-NC caveat) | per model | as sfo3d | Covers every SHA type **except C919 and C909**. |
| COMAC models | Sketchfab "C919 B" (CC BY 4.0; also in GitHub `AlstonZhuang/comac`) and "ARJ21" (CC BY 4.0, 608k faces, needs an account) | CC BY 4.0, but **uploader-declared** (provenance unproven) | yes if accepted | Q5. Fallback: fit our A320 or CRJ900 models to the COMAC ACAP dimensions (ACAPs are proprietary; measurement only). |
| Liveries | own re-drawings | trademarks of the airlines and COMAC | as sfo3d (non-commercial notice) | Q5. |
| Google / Baidu / Amap | – | licensed | **never** | Not used, even as reference, so far. |

## 3. ADS-B coverage and type mix: measured

Method:
- `tools/adsb/globe_scan.py` streams adsb.lol's complete daily archives (about 3.75 GB a day, every aircraft
  worldwide) and keeps every trace within **150 km** of ZSSS.
- `tools/adsb/globe_grid.py` maps distinct aircraft per 1° cell over East Asia (`docs/phase0/coverage_map_20261112.png`).
- `tools/rec/live_rec.py` polls the three open live APIs (60 NM radius) within their limits.

The results are in the next table. Scanned days are UTC days, which cover every local hour (UTC+8).

| Window | Source | Aircraft near ZSSS | Ground / below 10,000 ft | Movements at SHA in the window | Fraction seen |
|---|---|---|---|---|---|
| 2026-11-08, full day | adsb.lol archive | 2 (single points at FL311 and FL391, 142–147 km away: HIM226 A332, VJC982 A321) | 0 | about 783 | **0 %** |
| 2026-11-10, full day | adsb.lol archive | 0 of 75,360 traces | 0 | about 783 | **0 %** |
| 2026-11-12, full day | adsb.lol archive | 0 of 73,533 traces | 0 | about 783 | **0 %** |
| 2026-11-13 19:08–21:23Z (03–05 local, quiet hours) | adsb.lol / adsb.fi / OpenSky live, 60 NM | 1 / 2 / 0 (two B789s cruising at FL300–FL390, 53–85 km away) | 0 | night | – |
| 2026-11-12 | OpenSky's own coverage data (adsb.md) | nearest cell 233 km away, at ≥ 6.5 km altitude | 0 | – | – |
| 2026-11-01 sample | ADS-B Exchange free sample (adsb.md) | nearest real ADS-B position 106–119 km away, at ≥ 6,850 ft | 0 | – | – |

- **By hour:** zero in every hour of every scanned day.
- **Airborne vs ground:** zero ground and zero low-level positions. The only positions within 150 km are a handful of
  cruise-level points at the edge.
- **The coverage map** shows one feeder cluster around Hefei/Nanjing (31–32 N, 116–119.9 E). Nothing appears east of
  120 E. Ground positions appear only at Hong Kong, Taipei, Korea, Japan and a few isolated sites.
- **Why** (adsb.md):
  - Since 2021 PRC state security has seized volunteer ADS-B receivers that feed foreign sites. CCTV reported
    "hundreds of sets" in 2021, and an MSS statement in 2024 cited the Counter-espionage and Data Security Laws.
  - Low-level traffic is visible only within about 40–100 km. The nearest non-PRC site, the Korean Ieodo station, is
    about 378 km away.
- **The live recorder** keeps running about 30 h, so it also covers the daytime peak (06:00–24:00 local). Its result
  will be appended. It cannot change the conclusion: the archive days already include every local hour.
- **Type mix:** it cannot be measured, so §1 gives an estimate from route pairs × fleets and from a photo sample.
- **Conclusion: SHA cannot show "live traffic at real positions" from open data.** This is the go/no-go case the
  brief anticipated. Options are in §6, Q1.

## 4. Architecture: what to reuse and what is new

Same stack as sfo3d:
- plain ES modules and a custom WebGL2 renderer (or the three.js `live3.html` path; Q7);
- offline Python data tools;
- a stdlib Python relay;
- a snapshot/replay artifact.

Each forked file records its sfo3d commit (e3218d6) in its header. Hayward's de-SFO-ed modules (geo frame with degree
headings, `site.js`, the generic relay User-Agent, pack and replay shim) are used as **patterns**. Their code is not
copied unless the owner prefers a second donor (arch.md §0).

| Area | Reuse from sfo3d (copy and adapt) | New for SHA |
|---|---|---|
| Geo frame | `js/geo.js` pattern | Frame on the AIP ARP; runway grid at 177.34°/357.34° true; NE-aligned close parallels; vertical datum chain (AIP/Wusong → EGM2008 → ellipsoid; geoid +11.24 m) |
| Renderer, shaders, environment | `gl.js`, `renderer.js`, `js/shaders/*`, `js/env/*` | METAR decoder must cut ICAO trend groups (NOSIG/BECMG/TEMPO); ZSSS METAR source |
| Markings and signs | `markings.js`, `signs.js`, ground shader glyph atlas | **ICAO Annex 14 / CAAC parameter table** replacing FAA constants (designation font, threshold stripes, aiming point, TDZ, displaced-threshold arrows, holding positions, stand markings, bilingual signs where verified). arch.md §4 |
| Airfield data | builder pattern of `tools/build_*` | Builders from OSM (filtered) + AIP facts + Sentinel-2. No NAIP, FAA NASR or flysfo. |
| Stands, jet bridges, GSE | `gates.js` (bridges, VDGS, GSE), stand model, `standFits` classes | 155 stands from OSM refs × AIP (class, span limit); bridges at the 54 VDGS stands (inf); remote-stand bus and stairs GSE |
| Traffic and physics | `traffic.js`, `ground.js` (solid planforms), heading inference | Depends on Q1. Either a schedule-driven simulator labelled *scheduled/inferred* feeding the same pipeline, or a licensed feed. Never unlabeled synthetic traffic. |
| Aircraft | `models.js`, 23 `.sfom` models, fitting, existing CES/CCA/CSN/CPA/EVA/CAL/JAL/ANA/KAL liveries | C919 and C909 models; liveries for Shanghai Airlines, Spring, Juneyao, then about 11 more |
| Relay and artifact | `sfo_live_server.py` design, snapshot mode, `livetest.mjs` | `sha_live_server.py`; snapshot/replay content depends on Q1 |
| Must not leak | SFO ARP, headings 117.83/27.83, `GROUND_Y`, `GEOID_M` 32.29, FAA tables, flysfo plan logic (92 lines in `traffic.js`), the owner's repo URL in the relay User-Agent | – |

Effort (arch.md §7, rough): Phase 2 is about 1.5–2.5 × hwd3d's, because the airliner systems are kept but must be
de-SFO-ed.

## 5. Risks

1. **No observed traffic** (§3). Every live, replay and stand-learning feature inherited from sfo3d is blocked without
   a decision.
2. **Official AIP unread.** All AD 2 values come from a mirror copy at least four AIRAC cycles old. AMDT 12 (26 Nov)
   changes ZSSS. Q2.
3. **No sub-metre open optical imagery.** Jet bridges, paint and hold lines cannot be surveyed the SFO way; they will
   be standards-driven and marked `inf`.
4. **PRC legal exposure** (law.md §8; not legal advice). The main protection is that nothing is done inside China.
   - **R1, high:** anyone in the PRC who helps us (receivers, photos, GNSS tracks, audio, OSM edits) faces real
     enforcement. Never solicit this.
   - **R2, medium:** OSM military or armed-police features near ZSSS. Filter them, never draw or label them.
   - **R3, low:** a metre-accurate 3-D model of a PRC airport resembles item 24 of the 2020 surveying secret
     catalogue (3-D models with planar accuracy ≤ 10 m or relative height accuracy ≤ 5 %, over > 25 km² contiguous).
     Mitigation: keep the detailed extent at or below 25 km² (the aerodrome is about 6.7 km²).
   - **R4, low:** an app reachable in the PRC is an unreviewed map service. Do not target the PRC.
   - **R10, low:** travel by the owner or contributors to the PRC after publishing.
5. **Model provenance.** The CC BY COMAC models are uploader-declared. COMAC's ACAP terms forbid reproduction.
6. **Terms drift.** adsb.lol became metered and airplanes.live became contributor-only within the last two months.
   OpenSky requires a licence for live use. Re-check every term at build time.
7. **OSM churn.** The aerodrome relation is a week old, and the stand numbers were "adjusted" in 2026.
8. **Vertical datum.** Mixing AIP, Wusong, EGM2008 and ellipsoid heights would make aircraft float or sink.
9. **Usage budget.** sfo3d-level fidelity is expensive. The phases below each deliver something usable.

## 6. Questions for the owner

- **Q1 (go/no-go: traffic source).** Open ADS-B sees nothing at Hongqiao, at any hour. Options:
  - **(A) "Simulated Hongqiao" (recommended baseline).**
    - Traffic is generated from a schedule and labelled *scheduled / inferred* everywhere: tags, About panel, legend.
    - Runway direction comes from the real ZSSS METAR wind. Stands come from type rules on the real stand list.
    - Schedule source:
      - (A1) a licensed schedule (OAG or Cirium; cost; not redistributable);
      - (A2) a hand-built "typical day" from public aggregate statistics and airline timetables, entered as facts;
      - (A3) synthetic traffic at realistic rates.
    - Any rare observed aircraft (high overflights) can be overlaid as *observed*.
    - Identity: registration and operator would be inferred, never presented as real.
  - **(B) Licensed commercial feed** (VariFlight DataWorks; Aireon via FlightAware, at least $1,000/month).
    - It needs a written contract for public display, and no recorded data in the public repo.
    - Ground and stand coverage is unverified even there.
    - We would first ask vendors about coverage below 1,000 ft and on the ground, and about their datum. That needs
      your identity.
  - **(C) Change airport** to one with open coverage (the ADSBx sample shows ground coverage at Hong Kong VHHH and
    Taipei Taoyuan RCTP; not yet checked in adsb.lol).
  - **(D) Static Hongqiao.** Airport fidelity only, with no traffic claims, until a source exists.
  - **Not recommended:** a receiver in Shanghai or recruiting feeders there, because it puts people in the PRC at risk.
- **Q2 (official AIP).** The CAAC eAIP is free but needs a registered account. Will you register one and download AD 2
  ZSSS plus the charts yourself (recommended; an agent cannot hold your credentials)? May individual AIP facts (runway
  data, stand designators, frequencies) be cited with source in the public repo, with the PDFs kept local? Until then,
  is the unofficial mirror acceptable as an interim reference?
- **Q3 (legal posture).** Do you accept the residual PRC-law risk of a public, metre-accurate WGS-84 model built abroad
  from open data? Recommended defaults, each your call:
  - scene extent: the aerodrome plus about 1 km, at or below 25 km²;
  - filter all military, armed-police, police, prison and GNSS-station features;
  - a CONTRIBUTING rule: no data collection inside the PRC;
  - hosting outside the PRC only;
  - no PRC traffic recordings committed beyond what Q1 needs;
  - keep `tools/geo/gcj02.py` (unofficial algorithm) out of the repo;
  - whether to take professional advice before any travel to the PRC or Hong Kong.
- **Q4 (ATC audio).** No lawful verified source exists. Drop the toggle for SHA (recommended)? If you can open
  `https://www.liveatc.net/search/?icao=ZSSS` in a browser, a screenshot would settle whether any feed exists.
- **Q5 (models and liveries).** COMAC models:
  - use the CC BY 4.0 "C919 B" / "ARJ21" despite their unproven provenance, or fit our A320 and CRJ900 to COMAC's
    published dimensions;
  - may we create a Sketchfab account for the ARJ21 download;
  - paint the "COMAC C919" title or not.

  Liveries: same non-commercial posture as sfo3d? The four Shanghai carriers first?
- **Q6 (imagery).** Sentinel-2 (10 m) as ground texture and the Umbra 0.35 m SAR (CC BY 4.0) as the outline reference?
  Jet bridges, paint and signs would then be placed from standards and marked `inf`. Do you have openly licensed
  higher-resolution imagery or official apron charts?
- **Q7 (renderer and quality).** Build on `live.html` (WebGL2, as Hayward did) or start on sfo3d's three.js
  `live3.html`? Does Hayward's "one quality level, full features; the artifact only has to open and work on an
  iPhone" (OD1/OD2) also apply here, or does the original brief's "must work on a phone" stand?
- **Q8 (language).** English only, or bilingual Chinese/English labels and signs where verified?

## 7. Phased task list

Each phase ends with a commit, a push and renders shown to you. No scored QA loop starts without your approval.

- **Phase 1: data foundation.** This phase is independent of Q1 except for the traffic parts.
  - Pin and filter the OSM extract (sensitive-feature filter, Q3) and commit it with SOURCES.json.
  - Build `data/sha_airport.*` from OSM, AIP facts and Sentinel-2:
    - runways from the AIP dimensions and displaced thresholds on the OSM centrelines;
    - taxiways and holds;
    - 155 stands cross-checked OSM × AIP, with class from the span limits;
    - bridge stands (inf);
    - buildings, tower, FBO and the China Eastern base.
  - Write the vertical-datum chain.
  - Re-fit the OSM taxiway centrelines that are 5–13 m off the Sentinel-2 pavement.
  - Read the official AD 2 when Q2 allows; re-check after AMDT 12 (26 Nov).
  - Draw overlay plates of our data on Sentinel-2 and Umbra, with deviation call-outs.
- **Phase 2: app skeleton.**
  - Fork the renderer, geo frame, world, markings (ICAO/CAAC table) and gates into `sha3d/js/`.
  - Write `sha_live_server.py` within the current provider terms.
  - Build the static scene; first renders.
- **Phase 3: traffic per Q1.**
  - (A) A schedule-driven simulator through the same traffic, physics and stand pipeline, every aircraft tagged
    `inferred`. Taxi routing on the OSM graph, pushback, the night pause, runway mode from METAR.
  - (B) A licensed-feed adapter.
  - In both cases: replay packs, and the snapshot artifact.
- **Phase 4: aircraft.**
  - C919 and C909 models (Q5).
  - Liveries for CES, CSH, CQH and DKH, then others.
  - Lights, gear and shadows as in sfo3d.
- **Phase 5: airport fidelity.**
  - T1 and T2 piers, the tower (photos needed), jet bridges with VDGS, remote stands with stairs and buses, the FBO.
  - ICAO/CAAC markings, signs and lighting from AD 2.14 (PALS, PAPI, RCLL, RWSL).
  - Surroundings (canals, Hongqiao hub, WorldCover).
- **Phase 6: physics, QA and delivery.**
  - Solid bodies, pavement-only placement, spacing.
  - Adversarial visual QA passes, after your approval.
  - About/credits panel with the ODbL, Copernicus, Umbra and model notices.
  - Standalone app plus relay, and the artifact in snapshot/replay mode, both usable on a phone.
- **Later:** cinematic tracking films (as for SFO).
