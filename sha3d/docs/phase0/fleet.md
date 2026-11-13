# Phase 0: fleet and type mix at ZSSS, and the aircraft models we need (KEY = fleet)

Research note for SHA Live 3D. Checked on **2026-11-13**.

**Where things are**
- Downloads: `sha3d/refs/cache/fleet/<source>/` and `sha3d/refs/cache/models/<source>/`. Each folder has a `SOURCES.json` with the URL, the date, the quoted licence, whether we may redistribute, and a sha256 per file. All of `refs/cache/` is gitignored.
- Scripts: `sha3d/tools/fleet/`. Every script that reads a download runs with `python3 -I` from outside the download folders.
- I did not touch `sfo3d/`, `pc12/` or `hwd3d/`. No Google, Baidu or Amap imagery was used, and no geometry was involved, so GCJ-02 does not arise here.

**Legend**
- **[obs]**: I measured it, or read it in the cited original, in this session.
- **[inf]**: inferred or reasoned from observations.
- **[unverified]**: not checked against an original.

Fact status uses the owner's scale:
- **verified**: primary or official source read.
- **secondary**: only a secondary source.
- **unverified**: no source checked.
- **contradicted**: the sources disagree; both are given.

---

## 0. Summary

### 0.1 No ADS-B near ZSSS, so the type mix is an estimate
- **[obs]** The `adsb` key scanned adsb.lol daily archives for traces within 150 km of the ARP (`refs/cache/adsb/zsss_*.json.gz`):
  - 2026-11-08: 66,788 traces worldwide, **2** within 150 km. Both were overflights at FL311–FL391 (9N-ALZ A332 "HIM226" and VN-A634 A321 "VJC982").
  - 2026-11-10: **0** of 75,360.
  - 2026-11-12: **0** of 73,533.
- So there is **no** observed SHA traffic in open ADS-B data. **Every type-mix number below is an ESTIMATE.**

### 0.2 Who flies at SHA
- **Hubs and bases [secondary]**: China Eastern (MU), Shanghai Airlines (FM) and Juneyao Air (HO) are hubbed at SHA; Spring Airlines (9C) has a base there.
- **Primary support**:
  - **[verified]** China Eastern calls Shanghai its "core hub".
  - **[verified]** Shanghai Airlines is a wholly-owned CES subsidiary with a "Hongqiao Base".
- **Route share [secondary]**: Wikipedia lists 25 passenger airlines with 205 airline–destination pairs at SHA. The four Shanghai carriers hold 153 of them (**75 %**): MU 66, FM 42, 9C 23, HO 22.
- **International and regional routes**: only Tokyo-Haneda, Seoul-Gimpo, Taipei-Songshan, Hong Kong and Macau.
- **Sichuan Airlines** is **not** listed at SHA.

### 0.3 Type mix (estimate)

| Family | Estimate A: route pairs × fleet | Sample B: 139 aircraft in 2024–26 Commons photos at SHA | **Working range [inf]** |
|---|---|---|---|
| A320 family | 46 % | 45 % | **45–55 %** |
| 737 family | 37 % | 23 % | **23–37 %** |
| Wide-bodies (A330 > 787 > A350 > 777) | 14 % | 26 % | **10–20 %** |
| COMAC C919 | 1 % | 5 % | **1–5 %** |
| COMAC C909 / ARJ21 | 2 % | 0 % | **0–2 %** |
| E-Jets (Tianjin Airlines) | <1 % | 0 % | <1 % |
| Business jets | – | 1 aircraft (ACJ319 VP-CYW) | ~1 %; FBO data unavailable [unverified] |

Details are in §1.4.

### 0.4 Models
- **We already cover everything except COMAC.**
  - sfo3d holds 23 converted models. Every ICAO type expected at SHA maps onto one, except **C919** (ICAO `C919`) and **C909/ARJ21** (ICAO `AJ27`; the C909 rename did not change the designator **[verified, ICAO Doc 8643]**).
  - Of the 23 models, 20 are FlightGear models (FGMEMBERS via FlightAirMap) under GPL-2.0 (A380 with a CC BY-NC 3.0 caveat). The 737-800 and the two 777s come from FGMEMBERS directly, also GPL-2.0.
- **Open models for COMAC [obs]**:
  - FlightGear (FGAddon trunk, 676 aircraft) has no C919 or ARJ21. GitHub has no FlightGear one.
  - Two downloadable **CC BY 4.0** Sketchfab models exist:
    - "C919 B" by juarturo: 88k faces, untextured. The same file is in GitHub `AlstonZhuang/comac` with a `license.txt` that quotes CC-BY-4.0.
    - "ARJ21" by DL.123: 608k faces, white model.
  - All other C919 models found are unlicensed, non-commercial or paid.
- **Dimensions [verified]**: COMAC publishes ACAPs with full dimensions for both types (C919 R9 2025-10-17; C909 R13 2025-12-24) and a C919 three-view DWG. They are proprietary: use for measurement only (§3.4).
- **ARJ21 → C909 [verified]**:
  - COMAC's product pages now say "C909".
  - The C909 ACAP cover reads "C909 (ARJ21-700)".
  - CES's 2026 interim report notes "COMAC added the commercial name of C909 to ARJ21 aircraft model."
  - The timing (Zhuhai air show, Nov 2024) is **secondary** (Wikipedia citing FlightGlobal).

### 0.5 New work, in priority order (details in §5)
1. **C919 model.** Candidate: CC BY 4.0 "C919 B". Fallback: fit our A320 model to the ACAP.
2. **C909 model.** Candidate: CC BY 4.0 "ARJ21". Fallback: fit our CRJ900 model to the ACAP.
3. **Liveries** for about 15 new brands, the four Shanghai carriers first. Existing CES / CCA / CSN liveries need extending to their narrow-bodies, C919 and C909.

---

## 1. Airlines at SHA, hub status, fleets

### 1.1 Airlines serving SHA
Source: the Wikipedia "Airport destination list", article revision 1385154959 (2026-11-12) **[secondary]**. Parsed by `tools/fleet/wiki_dest.py`.

| Airline (IATA/ICAO) | SHA dests | SHA role (source) | Notes |
|---|---|---|---|
| China Eastern (MU/CES) | 66 | hub (WP infobox); "core hub" Shanghai (CES interim report 2026) | group incl. FM, KN, ex-OTT |
| Shanghai Airlines (FM/CSH) | 42 | hub (WP); has a "Shanghai Airlines Hongqiao Base on Suining Road" (CES interim 2026) | wholly-owned by CES; all-Boeing |
| Spring Airlines (9C/CQH) | 23 | operating base (WP SHA infobox; Spring article: bases incl. SHA and PVG); HQ in Changning, Shanghai | all A320 family |
| Juneyao Air (HO/DKH) | 22 | hub (WP; Juneyao article: hubs SHA and PVG) | A320 family + 787-9 |
| XiamenAir (MF/CXA) | 10 | focus city SHA (WP XiamenAir infobox) | mostly 737 |
| China Southern (CZ/CSN) | 7 | – | |
| Air China (CA/CCA) | 6 | – | incl. Taipei-Songshan |
| Shandong (SC/CDG) | 6 | – | all 737 |
| Hainan (HU/CHH) | 4 | – | |
| Shenzhen (ZH/CSZ) | 3 | – | |
| China United (KN/CUA) | 2 | – | CES subsidiary, 737 |
| One destination each | 1 | – | Air Macau (NX/AMU), ANA (NH), Asiana (OZ), Cathay Pacific (CX/CPA), Chengdu Airlines (EU/UEA), China Airlines (CI/CAL), EVA Air (BR/EVA), Hebei (NS/HBH), Hong Kong Airlines (HX/CRK), Japan Airlines (JL/JAL), Korean Air (KE/KAL), Lucky Air (8L/LKE), Tianjin (GS/GCR), Xizang (TV/TBA) |

**[obs]** The following are **not** in the SHA list:
- Sichuan Airlines (its subsidiary Chengdu Airlines flies CTU–SHA).
- Any cargo-only airline.

**[unverified]** SHA's freighter traffic (if any) was not researched. The 445,265 t of 2025 cargo (CAAC figure quoted in Wikipedia) could be largely belly cargo.

### 1.2 Fleets: primary figures (issuer filings on HKEXnews) [verified]

| Group (date) | Total | A320 fam | 737 fam | A330 | A350 | 787 | 777 | 747 | C919 | C909 | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| China Eastern group (30 Sep 2026) | 837 | 396 | 278 | 56 | 20 | 18 | 20 (-300ER) | – | **17** | **32** | CES operating data Sep 2026 |
| China Eastern group (30 Jun 2026) | 833 | 393 | 277 | 56 | 20 | 18 | 20 | – | 17 | 32 | CES Interim Report 2026 |
| China Southern group (30 Sep 2026) | 978 | 418 | 393 | 25 | 20 | 35 | 34 (incl. freighters [inf]) | – | **13** | **40** | CSN key operating data Sep 2026 |
| Air China group (30 Jun 2026) | 972 (+3 business jets in the total) | 373 | 420 | 49 | 30 | 14 | 28 | 9 | **11** | **35** | Air China Interim Report 2026 (974 at 30 Sep 2026, no type split) |

What the groups include:
- **CES group** includes Shanghai Airlines and China United **[verified]**. CES's notes say the A320 series covers "A319, A320, A320NEO, A321, A321NEO", and the B737 series covers "B737-700, B737-800, B737-8".
- **Air China group** includes Shenzhen, Shandong, Air Macau, Dalian and Inner Mongolia **[secondary, WP]**.

### 1.3 Airline fleets: secondary figures (Wikipedia "Current fleet" tables) [secondary]

Revisions are in each `SOURCES.json`. Parsed by `tools/fleet/wiki_fleet.py`.

**The four Shanghai carriers**

| Airline | In service | Fleet mix |
|---|---|---|
| China Eastern mainline | 685 | A319 31; A320 134; A320neo 123; A321 74; A321neo 30; A330-200 30; A330-300 26; A350-900 20; 737-700 36; 737-800 100; 737 MAX 8 5; 777-300ER 20; 787-9 7; **C909 32**; **C919 17** (88 on order) |
| Shanghai Airlines | 88 | 737-700 4; 737-800 57; 737 MAX 8 17; 787-9 10. C909: 5 on order |
| Spring Airlines | 135 (infobox: 140 in Aug 2026) | A320ceo 75; A320neo 48; A321neo 12 |
| Juneyao Air | 103 (infobox: 105 in Oct 2026) | A320 30; A320neo 22; A321 27; A321neo 14; 787-9 10 |

**Other carriers at SHA**

| Airline | Fleet |
|---|---|
| XiamenAir | 737-800 110, 737 MAX 8 28, 787-8/-9 12, A320neo/A321neo 22 |
| Hainan | 737-800 126, MAX 8 32, 787-8/-9 38, A330 29 |
| Shenzhen | A320 family 112, 737 86, A330-300 6, A350 1 |
| Shandong | 737 135 |
| China United | 737 60 |
| Tianjin | A320 family 44, A330-200 4, **E190 38, E195 17** |
| Lucky | A320 family 14, A330 4, 737 33 |
| Hebei | 737-800 28 |
| Chengdu | A320 family 51, **C909 30** |
| Air Macau | A320 family 23 |
| Hong Kong Airlines | A320/321 20, A330-300 7 |
| Xizang | A319/A319neo/A320 48, A330-200 5 |

**[secondary]** OTT Airlines, the CES subsidiary formed for COMAC types, made its first flight SHA→PEK on 28 Dec 2020 and "was merged into China Eastern Airlines in September 2024". This explains CES's 32 C909s.

### 1.4 Type mix at SHA: ESTIMATE (no ADS-B; see §0.1)

**Estimate A** (`tools/fleet/type_mix_estimate.py`) **[inf]**:
- **Method:** each airline's share of the 205 SHA airline–destination pairs, multiplied by its passenger-fleet share per family. Fleets come from §1.2/§1.3.
- **Assumptions** for six foreign carriers (CX, JL, NH, OZ, and part of BR and HX) are marked "assumed/unverified" in the script.
- **Limits:** it ignores frequencies (the PEK/PKX/CAN/SZX shuttles dominate movements). It also assumes each airline uses its whole fleet evenly. That overstates the 737 share (Shanghai Airlines and the other 737 operators fly a few dense routes) and understates trunk-route wide-bodies.
- **Result:** A320 family 45.5 %; 737 family 37.1 %; A330 5.8 %; 787 5.3 %; C909 2.1 %; A350 1.5 %; 777 1.2 %; C919 0.9 %; 767 0.5 %; E-Jet 0.3 %. Wide-bodies total 14.2 %.

**Sample B** (`tools/fleet/commons_sha_sample.py`) **[obs]** (photo titles; selection-biased):
- **Source:** Wikimedia Commons file **titles** (no images read) of aircraft photographed at or on approach to SHA, from three main sets:
  - 4300streetcar, "on final approach to Shanghai Hongqiao", May 2026 and June 2025.
  - Benlisquare, "on final approach towards SHA", shot 2026-05-03.
  - Windmemories and others, "at SHA", 2024.
- **Result:** 139 distinct registrations dated 2024–2026. A320 family 62 (45 %), 737 family 32 (23 %), A330 20 (14 %), 787 13 (9 %), C919 7 (5 %), A350 3 (2 %), 777 2 (1 %). **No C909** and no E-Jet.
- **Bias:** spotters favour wide-bodies, C919s and special liveries, so the wide-body and C919 shares are likely too high.
- **Notable observations:**
  - CES 777-300ER B-2025 and CES A350-900 B-324X on approach to SHA (May 2026).
  - Juneyao 787-9s B-1115, B-20EQ, B-208A, B-226N.
  - CES C919s B-919G, B-919H, B-657S, B-65A0, B-65AH; China Southern C919 B-658P.
  - Korean Air A330-300 HL7584; China Airlines A330 B-18361; EVA Air 787-10 B-17808.
  - Hong Kong Airlines A320 B-LPU and A330-300 B-LNP; Xizang A330-200 B-1046.
  - A corporate **Airbus A319 VP-CYW**, 2026-05-03.

**Working range [inf]:**
- A320 family 45–55 %.
- 737 family 23–37 % (mainly FM, MF, SC, KN, HU and CES 737s).
- Wide-bodies 10–20 %: A330 first, then 787 (FM, HO, HU, MF, BR), A350 (CES, CA, CX), 777-300ER (CES, CA) and rarely 747-8 or 767.
- C919 1–5 %, growing. CES operates its C919s from SHA: MU9191 SHA–PEK was the first commercial C919 flight **[verified COMAC / secondary route]**, and the type is on SHA–HKG daily in NW25 **[secondary, AeroRoutes]**.
- C909 0–2 %. CES has 32, but none were seen in the photo sample.
- E190/E195 <1 % (Tianjin Airlines).
- Business jets about 1 % **[unverified]**.

**To replace this estimate:**
- a schedule (OAG / CAAC slot data, not available here);
- the `adsb` key's recordings, if ZSSS coverage ever appears;
- or the `live` key's own MLAT/ADS-B feed.

### 1.5 Business aviation at SHA [secondary / unverified]
- **Universal Weather, "Shanghai, China: 2026 Business Aviation Destination Guide"** (20 Feb 2026) on ZSSS:
  - It has "a dedicated FBO with integrated CIQ processing".
  - "No GA takeoffs between 0700 and 0900 local".
  - "Runway curfew from 0001 to 0600 local".
  - No operator is named. **[secondary]**
- **Operator history:**
  - AIN 2012, "FBO Profile: Shanghai Hawker Pacific Business Aviation Service Centre" (title only readable). **[secondary]**
  - AIN 2023 headline: "International Bizav Arrivals Suspended at Shanghai Hongqiao Airport". **[secondary]**
- **[obs]** Jet Aviation's location list (jetaviation.com/locations/, read 2026-11-13) has **no** Shanghai entry. The current FBO operator is **unverified**.
- **[obs]** One corporate ACJ319, VP-CYW, was photographed on approach to SHA on 2026-05-03 (Commons title).
- **Coverage:** business-jet types are already covered by sfo3d's generic CRJ200-based airframe for 36 ICAO business-jet types plus E135/E145 (`sfo3d/js/aircraft/fit.js` `BIZ`, 38 entries). ACJ319 / BBJ map to the A319 / 737 models.

---

## 2. Model inventory we already have (sfo3d, read-only) [verified: read in the repo]

`sfo3d/data/models/manifest.json` lists 23 models (`*.sfom`). Licences come from `sfo3d/docs/ATTRIBUTION_models.md`.

### 2.1 The models

| Model key | Built as | Source | Licence |
|---|---|---|---|
| a319, a320, a321 | A319 / A320 / A321 | FAM ← FGMEMBERS/A320-family @0b928542 | GPL-2.0 (COPYING) |
| a333 | A330-300 | FAM ← FGMEMBERS/A330-300 @7d930769 | GPL-2.0 |
| a359 | A350-900 | FAM ← FGMEMBERS/A350XWB @407f422a | GPL-2.0 |
| a388 | A380-800 | FAM ← FGMEMBERS/A380-omega @ffb200c2 | GPL-2.0 **and CC-BY-NC-3.0 caveat** ("may therefore still be non-commercial only") |
| b738 | 737-800 | FGMEMBERS/737-800 @9126249 | GPL-2.0 |
| b744, b748 | 747-400, 747-8 | FAM ← FGMEMBERS | GPL-2.0 |
| b752, b763, b788 | 757-200, 767-300, 787-8 | FAM ← FGMEMBERS | GPL-2.0 ("or later" for 757) |
| b772, b77w | 777-200ER, 777-300ER | FGMEMBERS/777 @371a354 (FGAddon LICENSE GPL v2) | GPL-2.0 |
| bcs1, bcs3 | A220-100/-300 | FAM ← FGMEMBERS/CSeries | GPL-2.0 |
| crj2, crj7, crj9 | CRJ200/700/900 | FAM ← FGMEMBERS | GPL-2.0 |
| e170, e75l, e190 | E170/E175/E190 | FAM ← FGMEMBERS/E-jet-family | GPL-2.0 (texture watermark noted) |
| md11 | MD-11 | FAM ← FGMEMBERS/MD-11 | GPL-2.0 or later |

### 2.2 ICAO designators mapped and SHA coverage
- **Mapped** (`sfo3d/js/aircraft/types.js` `ICAO_TYPES`, model per type in `fit.js` `TYPE_MODEL`):
  - B736/B737/B738/B739, B37M/B38M/B39M/B3XM
  - A319/A19N/A320/A20N/A321/A21N
  - B752/B753, B762/B763/B764
  - B772/B77L/B773/B77W/B779
  - B788/B789/B78X, B744/B74F/B748
  - A332/A333/A338/A339, A359/A35K, A388
  - BCS1/BCS3, E170/E75L/E75S/E190/E195
  - CRJ2/CRJ7/CRJ9, MD11
  - plus 38 business-jet and ERJ-135/145 designators via the generic CRJ200 airframe (`BIZ`).
- **SHA coverage [inf]:** every type in §1 maps onto these models except **C919** and **AJ27 (C909/ARJ21)**. ICAO designators were checked in Doc 8643 (§3.3).
- **Liveries already in sfo3d** (`sfo3d/data/liveries/manifest.json`):
  - CES and CCA (777-300ER only, "procedural"), CSN (787-9).
  - CPA, CAL, EVA, JAL, ANA, KAL, AAR.
  - Nothing for CSH, CQH, DKH, CXA, CHH, CSZ, CDG, CUA, CRK, AMU, GCR, LKE, HBH, UEA or TBA.

---

## 3. COMAC C919 and C909 (ARJ21): open models, licences, published dimensions

### 3.1 Search log [obs]

**GitHub repository search**

| Query | Result |
|---|---|
| `C919` | 59 repos; no 3-D aircraft model with a licence (see 3.2) |
| `ARJ21` | 5 repos, none a model |
| `C909` | 33 repos, none relevant |
| `comac` | 232 repos, none a model |
| `C919 flightgear`, `ARJ21 flightgear`, `COMAC 3d model` | 0 |

**GitHub code search**

| Query | Result |
|---|---|
| `C919 extension:ac`, `ARJ21 extension:ac`, `ARJ21 extension:obj` | 0 |
| `C919 extension:gltf` | one hit: `AlstonZhuang/comac` `public/models/aircraft/scene.gltf` |
| `C919 path:Models` | only `sidi762/followme_e-tron` (a FlightGear follow-me car livery named C919) |

**FlightGear**
- FGAddon trunk `Aircraft/` (sourceforge, 676 directories): no C919, ARJ21 or COMAC.
- The FlightGear China group (`FGPRC-FlightGearChina`, 2 repos) has no aircraft.

**Sketchfab API v3** (searched `C919`, `ARJ21`, `C909`, `comac`, airline names; downloadable and all models)

| Model (uid) | Author | Licence | Downloadable | Faces | Verdict |
|---|---|---|---|---|---|
| **"C919 B"** (d7f372558e1c48fca54c145f2a491fc4) | juarturo | **CC BY 4.0**: "Author must be credited. Commercial use is allowed." | yes | 88,320 | **candidate** (white, untextured) |
| **"ARJ21"** (1d2d165256ea48bdbc420388bb6807a5) | DL.123 | **CC BY 4.0** (same wording) | yes | 607,816 | **candidate** (description "art/飞机白模" = white model; needs decimation) |
| "COMAC" (1c985f090e154ded93f9acd4d2be7a47) | MatheusCIASC | CC BY 4.0 | yes | 141,083 | **not an aircraft** (thumbnail shows an exhibition booth) |
| "COMAC C919" (48f17e7d3ff247eb8c1ca9513399db3e) | thaweverything | none | no | 1.76 M | excluded: "Non-Commercial / Educational Use Only" |
| "Comac C919-100" (7d5559cf3fa9408bac86f708eff22eea) | jsong.js.us | none | no | 280k | excluded: "Available for purchase on CGTrader" |
| "Comac C919 3D Model" / "Comac C919 Airplane" | 3devok | none | no | 425k | excluded (store models) |

### 3.2 Repositories cloned (shallow, blob-less, only licence/README checked out) [obs]
All clones are in `refs/cache/models/gh_*`. Commits and blob ids are in each `SOURCES.json`.

- **`AlstonZhuang/comac`** @957bdc44 (2024-08-12). A Vue admin template with an aircraft model.
  - Repo `LICENSE` is MIT ("Copyright (c) 2017-present PanJiaChen", the template's).
  - `public/models/aircraft/license.txt` covers the model and quotes: "This work is based on "C919 B" (https://sketchfab.com/3d-models/c919-b-d7f372558e1c48fca54c145f2a491fc4) by juarturo (https://sketchfab.com/juarturo) licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)".
  - So the CC BY "C919 B" can be fetched with `git clone` (`scene.glb` 5.04 MB, blob c8696c75; `scene.gltf` blob 476dbe5e) without a Sketchfab account.
  - **Note [obs]:** while reading blob sizes, git fetched the blobs into the clone's object store. They are not checked out and nothing was converted.
  - **Reading the glTF JSON only** (`tools/fleet/gltf_bbox.py`, accessor min/max) **[obs]**:
    - Sketchfab export with 156 meshes, 11 materials, no textures. Bounding box 7.78 × 2.32 × 7.98 units (span × height × length).
    - So **the model is not to scale**: span/length = 0.974, against ACAP 35.80/38.90 = 0.920, and height/length 0.290 against 0.307.
    - **[inf]** It needs the same "fit to published dimensions" step sfo3d applies to every model.
- **`459605823/vis-c919`** @11893893: `public/vis/c919.glb` (994 KB). **No licence file**, so all rights reserved by default. Excluded.
- **`caleseele/c919-autonomy`** @2f8bfeff: README says the model is self-made with Blender scripts ("模型由本仓库脚本生成") and "三维结构模型 / GLB / 涂装贴图不在公开站点发布". No GLB in the tree and **no licence file**. Excluded.
- **`WenmuWenmu/C919`, `WenmuWenmu/C919wing`**: a 3-file Flask app with an HTML page each. Not models.

### 3.3 Names, designators, status

| Item | Value | Status |
|---|---|---|
| ICAO Doc 8643 designators | `C919` = "C-919" (L2J, WTC M); **`AJ27`** = "ARJ-21-700", **"C-909"** and "CBJ-909" (L2J, WTC M) | verified (ICAO service JSON) |
| C909 name | COMAC product page "C909 ... obtained the Type Certificate (TC) from Civil Aviation Administration of China (CAAC) on December 30th, 2014"; ACAP cover "C909 (ARJ21-700)"; CES interim 2026 note 5: "COMAC added the commercial name of C909 to ARJ21 aircraft model." | verified |
| Rename date | Wikipedia: "the jet was rebranded as the C909 in November 2024" (cites FlightGlobal 12 Nov 2024, Zhuhai air show) | secondary |
| C919 service entry | COMAC: "The world's first C919 aircraft was delivered on December 9th, 2022, and successfully completed its first commercial flight on May 28th, 2023." Wikipedia: MU9191 departed Shanghai Hongqiao for Beijing Capital | verified / secondary |

### 3.4 Published dimensions (COMAC ACAPs, for a procedural fallback and for fitting) [verified]

- **C919**: ACAP C919-SVV19-50009-00, R9 2025-10-17, §02-02 "General Aircraft Dimensions" (Issue 003, 2025-10-17), p. 35 of the PDF. The figure values were read from the rendered drawing.
- **C909**: ACAP TP-E700051 (PMC ARJ21-SVV19-50009-00), R13 2025-12-24, §02-02 "General Dimensions" (Issue 003, 2025-12-24), p. 29. Heights come from §02-03 "Ground Clearances".

| Dimension | C919 | C909 (ARJ21-700) | For comparison: our model base |
|---|---|---|---|
| Overall length | **38.90 m** | **33.46 m** | A320 37.57 m / CRJ900 36.2 m [secondary] |
| Wing span | **35.80 m** (STD and ER, §03 Table 1) | **27.29 m** | A320neo 35.80 m [secondary] / CRJ900 24.9 m [secondary] |
| Height | **11.95 m** (three-view). Ground-clearance table, vertical tail: 12.21 m (OEW, fwd CG, 15 °C) down to 11.88 m (MTW, aft CG) | Vertical-tail top **8.606 m** (OEW, 15 °C); 8.476–8.600 m at MTW | – |
| Horizontal tail span | 12.60 m | 10.50 m | – |
| Wheelbase | 13.47 m | 14.88 m | – |
| Main-gear track | 7.62 m (outer tyre edges 8.98 m) | 4.68 m (outer 5.80 m) | – |
| Nose to nose-gear | 5.28 m | 2.30 m | – |
| Fuselage width | 3.96 m | 3.34 m (plan); 3.61 m depth dimension in the side view | – |
| Engine centreline from fuselage centreline | 6.13 m | rear-fuselage pods (not dimensioned in plan) | – |
| Seats / range (COMAC product page) | 158–192 seats, 4,075–5,555 km | 78–97 seats, 2,225–3,700 km | – |
| MTOW STD / ER | 75,100 / 78,900 kg | 40,500 / 43,500 kg | – |
| Engines | 2 × CFM LEAP-1C (ACAP text) | 2 × GE CF34-10A [secondary, WP] | – |

**Licence of these documents [verified]**
- ACAP front matter: "COMMERCIAL AIRCRAFT CORPORATION OF CHINA, LTD. PROPRIETARY, CONFIDENTIAL, AND/OR TRADE SECRET". It also says "The information contained herein shall not be reproduced, quoted, disclosed or used directly or indirectly, in whole or in part for any purposes, except with prior written authorization by COMAC."
- COMAC site terms: "未经中国商飞公司或相关权利人事先的书面许可，您不得以任何方式擅自复制、传播、出版、转帖、改编或陈列本网站的内容。" The limited licence excludes "（3）衍生性的使用本网站及其内容".
- The PDFs and DWG stay in the gitignored cache and are **not redistributable**. I quote only figure labels and numbers here.
- **Owner decision needed:** whether measured numbers from a manufacturer document may drive a published model. This is the same practice as sfo3d's use of the Boeing and Airbus ACAPs ("measurement only"), but COMAC's wording is stricter.

**Contradicted:** C909 height and span.
- Wikipedia gives height **8.44 m** and span **27.28 m**.
- The ACAP gives 8.606 m (vertical-tail top at OEW) and 27.29 m.
- Use the ACAP.

**Procedural fallback (no new third-party geometry) [inf]:**
- **C919** ≈ our GPL A320 model, fitted with `fit.js` plugs: +1.33 m length, same 35.80 m span, +0.19 m height.
- **C909** ≈ our GPL CRJ900 model, fitted the way `BIZ` fits business jets: uniform scale to 33.46 m, outer wing stretched to 27.29 m, fin to 8.6 m.
- Both are recognisable but not faithful:
  - C919: 6-window cockpit, LEAP-1C nacelles and integrated winglets.
  - C909: supercritical wing with winglets, rear-mounted CF34s, MD-80-like T-tail.
  - The C919 three-view DWG (`refs/cache/fleet/comac_c919_3view/`, AutoCAD 2013–2017, not converted; LibreDWG would be needed) could give plan and side outlines for measurement.

---

## 4. Liveries (reference only) and trademark note

### 4.1 Current liveries of the four Shanghai carriers
The photos are Commons thumbnails in `refs/cache/fleet/commons_livref_thumbs/` (author and licence per file in `SOURCES.json`). They were looked at, not traced. Colours below are by eye and approximate.

| Carrier | Livery facts (source, status) | What the 2024–26 photos show [obs] |
|---|---|---|
| **China Eastern (CES)** | Boeing release, Everett, 24 Sep 2014: "China Eastern debuted its new livery on the new 777-300ER – a change to its 25-year old livery." It describes the logo as "a swallow consisting of two capital letters, C and E" **[verified, OEM press release]**. WP: "On 9 September 2014, China Eastern introduced a new logo and new livery." **[secondary]** | A320neo B-32AA and C919 B-919G at SHA, May 2026: all-white aircraft; white fin with the red-over-blue swallow; blue "CHINA EASTERN" and red "中國東方航空" (traditional characters) above the forward windows; small red swallow on the winglet; white nacelles; "COMAC C919" small type title aft on the C919. Same scheme on A320neo and C919. |
| **Shanghai Airlines (CSH)** | WP: "The logo is a white crane on a red vertical tail fin." and (CES article) "Shanghai Airlines retained its brand and livery." **[secondary]** | 737 MAX 8 B-1381 (SHA, 2024) and 787-9 B-208X (PVG, 2025): white upper fuselage; red cheatline from the nose along the lower forward fuselage, widening into an all-red rear fuselage and red fin with the white crane; red winglets with the crane; black calligraphic "上海航空" and black "SHANGHAI AIRLINES". |
| **Spring Airlines (CQH)** | WP: logo of "three overlapping and intersecting S's"; gallery caption "An Airbus A320-214 in the current 2021 livery". A flight-sim add-on page describes the 2021 livery as a yellow-green gradient tail without "ch.com" **[unverified]**. | A321neo B-326Q and A320neo B-32MX on approach to SHA, May 2026: white fuselage; **solid green fin with the yellow 3S**; large green script "Ch.com" on the rear fuselage; green "春秋航空" forward; green sharklets with the yellow S; green S on the nacelles. **contradicted**: the 2026 photos do not show the gradient tail called "current" on Wikipedia. Two schemes may coexist; check more photos before drawing. |
| **Juneyao Air (DKH)** | Juneyao press release via PR Newswire, Shanghai, 16 Jul 2018: "Juneyao Airlines' first Boeing 787 aircraft will be delivered with a colorful Chinese peony-themed livery." The same release says the "Chinese Red" livery of its A320/321s continues on the 787s (paraphrased by the fetch tool) **[verified, issuer release]**. | A321 B-1647 at SHA (May 2026) and A320neo B-32EY at PVG (Dec 2025), standard scheme: white fuselage; crimson fin with a gold circular emblem; crimson nacelles with the gold emblem; crimson sharklets; red "JUNEYAO AIR" and "吉祥航空". A321neo B-30EQ and 787-9 B-1115 carry peony/floral art on the rear fuselage (WP calls B-20D1's "Colorful Floral" a special livery). |

**Other brands needed at SHA** (not yet in sfo3d): XiamenAir, Hainan, Shenzhen, Shandong, China United, Hong Kong Airlines, Air Macau, Tianjin, Lucky, Hebei, Chengdu, Xizang. Existing sfo3d brands need new types:
- CES on A320 family, 737, A330, A350, 787, C919 and C909.
- CCA and CSN on narrow-bodies, A330 and C919.
- CPA, CAL, EVA and KAL on A330 / 787-10.

### 4.2 Trademark note [verified]
- **Airline marks:** airline names, logos and liveries are trademarks of their owners. The sfo3d notice applies unchanged: "Airline names, logos and liveries are trademarks of their respective owners. They are re-drawn here for a non-commercial depiction of real traffic; no endorsement is implied." (`sfo3d/docs/ATTRIBUTION_models.md`).
- **COMAC marks:** COMAC states that "the ARJ21 name and logo containing "ARJ21" and the C909 name and logo containing "C909" and the C919 name and logo containing "C919" are all trademarks owned by the Commercial Aircraft Corporation of China, Ltd." (ACAP front matter).
  - Using the type names to label traffic is nominative. The "COMAC C919" title painted on the aft fuselage, if reproduced, is a COMAC mark.
  - Owner to decide; the safe default is to leave it off.
- **Licences:** CC BY / GPL cover copyright only, not trademarks.

---

## 5. New models needed, in priority order

| # | Type (ICAO) | Why (evidence) | Best open source | Licence status | Fallback |
|---|---|---|---|---|---|
| 1 | **COMAC C919** (`C919`) | CES is the main SHA carrier and runs its C919s from SHA: first commercial flight MU9191 SHA–PEK, 28 May 2023 [verified / secondary]; SHA–HKG daily NW25 [secondary]. 7 distinct C919s in the 2024–26 SHA photo sample, incl. China Southern [obs]. 41 in the big-three fleets (17 CES, 13 CSN, 11 CA group) [verified]. | Sketchfab "C919 B" by juarturo; the same file in `AlstonZhuang/comac` | **CC BY 4.0, open** (credit line quoted in §3.2). Risks: (a) unknown provenance of a free Sketchfab upload; (b) not to scale, needs fitting; (c) no textures: we paint our own atlas as sfo3d does. | A320 model (GPL-2.0) fitted to the ACAP (§3.4) |
| 2 | **COMAC C909 / ARJ21** (`AJ27`) | 32 in CES (ex-OTT, whose hub was SHA per WP), 40 CSN, 35 CA group, 30 Chengdu [verified / secondary]. **0** in the SHA photo sample [obs], so low SHA frequency [inf]. | Sketchfab "ARJ21" by DL.123 (608k faces) | **CC BY 4.0, open**, but downloading needs a Sketchfab account (owner decision). Not on GitHub. Same provenance risk. | CRJ900 model (GPL-2.0) fitted to the ACAP (§3.4), like the `BIZ` generic airframes |
| 3 | (optional) A330-900neo (`A339`) | CES has 25 on order (WP) | – | – | already mapped to a333 |
| – | Everything else seen at SHA | A319/A320/A321 (ceo, neo), 737-700/800/MAX 8, A330-200/300, A350-900, 787-8/9/10, 777-300ER, 747-8, 767-300, E190/E195, business jets | existing sfo3d models (GPL-2.0) | as in §2 | – |

**Liveries are the larger job:** 12 new brands plus extensions (§4.1). The four Shanghai carriers come first: CES, CSH, CQH, DKH.

---

## 6. Facts table

Date checked for every row: **2026-11-13**.

| # | Topic | Value | Source URL | Quote (verbatim, short) | Status |
|---|---|---|---|---|---|
| 1 | ADS-B near ZSSS | 2 traces within 150 km on 2026-11-08 (both cruise overflights); 0 on 11-10; 0 on 11-12 | https://github.com/adsblol/globe_history_2026/releases (via `refs/cache/adsb/`) | "2026.11.08 prod: scanned 66788 traces, 2 within 150.0 km" (scan log) | verified [obs] |
| 2 | SHA hubs / bases | Hub for MU, FM, HO; operating base for 9C | https://en.wikipedia.org/w/index.php?title=Shanghai_Hongqiao_International_Airport&oldid=1385154959 | "Hongqiao Airport is the corporate headquarters and a major hub for China Eastern Airlines, Shanghai Airlines, and Juneyao Air, as well as a major operating base for Spring Airlines." | secondary |
| 3 | SHA international routes | Only HND, GMP, TSA, HKG, MFM | same | "as well as five international routes to central Tokyo's Haneda Airport, central Seoul's Gimpo International Airport, central Taipei Songshan Airport, Hong Kong International Airport, and Macau's Macau International Airport" | secondary |
| 4 | SHA airlines | 25 airlines, 205 airline–destination pairs; MU 66, FM 42, 9C 23, HO 22 | same (destination list) | (parsed table) | secondary |
| 5 | SHA 2025 traffic | 50,151,025 passengers; 282,692 movements; 445,265.5 t cargo | WP infobox citing http://www.caac.gov.cn/XXGK/XXGK/TJSJ/202602/P020260226360830390937.xlsx | "stat2_data = 282,692" | secondary (CAAC file not fetched) |
| 6 | CES hub | Shanghai is CES's core hub | https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0923/2026092300276.pdf | "The Group has built its route network system around four major hubs: Shanghai, Beijing, Kunming, and Xi'an." | verified |
| 7 | FM ownership | Wholly-owned subsidiary of CES; has a Hongqiao base | same | "Shanghai Airlines ... a wholly-owned subsidiary of the Company"; "Shanghai Airlines Hongqiao Base on Suining Road" | verified |
| 8 | CES group fleet | 837 at 30 Sep 2026: 777-300ER 20, 787 18, A350-900 20, A330 56, A320 series 396, 737 series 278, C919 17, C909 32 | https://www1.hkexnews.hk/listedco/listconews/sehk/2026/1015/2026101501062.pdf | "As of the end of September 2026, the Group operated a total of 837 aircraft." | verified |
| 9 | CSN group fleet | 978 at 30 Sep 2026: A350 20, A330 25, A320 418, 787 35, 777 34, 737 393, C909 40, C919 13 | https://www1.hkexnews.hk/listedco/listconews/sehk/2026/1015/2026101500876.pdf | "As of the end of September 2026, the Group operated a fleet of 978 commercial aircrafts" | verified |
| 10 | CA group fleet | 972 at 30 Jun 2026: A320 373, A330 49, A350 30, B737 420, B747 9, B777 28, B787 14, C909 35, C919 11, business jets 3 | https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0923/2026092300452.pdf | "the Group had a total of 972 aircraft with an average age of 10.60 years" | verified |
| 11 | Spring fleet | A320ceo 75, A320neo 48, A321neo 12 (table 135); infobox 140 | https://en.wikipedia.org/w/index.php?title=Spring_Airlines&action=raw | "fleet_size = 140" | secondary (internal mismatch 135/140) |
| 12 | Juneyao fleet | A320 30, A320neo 22, A321 27, A321neo 14, 787-9 10 (table 103; infobox 105, Oct 2026) | https://en.wikipedia.org/w/index.php?title=Juneyao_Air&action=raw | "fleet_size = 105 (As of October 2026)" | secondary |
| 13 | FM fleet | 737-700 4, 737-800 57, 737 MAX 8 17, 787-9 10; C909 5 on order | https://en.wikipedia.org/w/index.php?title=Shanghai_Airlines&action=raw | (table) | secondary |
| 14 | OTT Airlines | Merged into CES Sep 2024; first flight SHA→PEK 28 Dec 2020 | https://en.wikipedia.org/w/index.php?title=OTT_Airlines&action=raw | "was merged into China Eastern Airlines in September 2024" | secondary |
| 15 | ARJ21 → C909 | COMAC markets the ARJ21 as C909 | https://english.comac.cc/products/c909/ ; CES interim 2026 (row 6 URL) | "COMAC added the commercial name of C909 to ARJ21 aircraft model." | verified |
| 16 | Rename date | November 2024 (Zhuhai air show) | https://en.wikipedia.org/w/index.php?title=Comac_C909&action=raw (cites flightglobal.com, 12 Nov 2024) | "the jet was rebranded as the C909 in November 2024" | secondary |
| 17 | ICAO designators | C919 → `C919`; ARJ-21-700, C-909, CBJ-909 → `AJ27` | https://doc8643.icao.int/external/aircrafttypes | "ModelFullName": "C-909", ... "Designator": "AJ27" | verified |
| 18 | C919 service entry | Delivered 9 Dec 2022; first commercial flight 28 May 2023 | https://english.comac.cc/products/ca/ | "successfully completed its first commercial flight on May 28th, 2023" | verified |
| 19 | First C919 flight from SHA | MU9191 SHA→PEK, 28 May 2023 | https://en.wikipedia.org/w/index.php?title=Comac_C919&action=raw | "MU9191 departing from Shanghai Hongqiao Airport and arriving at Beijing Capital Airport" | secondary |
| 20 | C919 on SHA–HKG | MU721/722 daily, C919, NW25 | https://www.aeroroutes.com/eng/251022-munw25shahkg | "MU721 SHA0800 – 1050HKG 919 D" | secondary |
| 21 | C919 dimensions | L 38.90, span 35.80, H 11.95, HT 12.60, wheelbase 13.47, track 7.62 m | https://www.comac.cc/fujian/c919acap_en.pdf (R9 2025-10-17, §02-02) | figure labels "38.90 m", "35.80 m", "11.95 m" | verified |
| 22 | C909 dimensions | L 33.46, span 27.29, HT 10.50, wheelbase 14.88, track 4.68 m; fin top 8.606 m (OEW 15 °C) | https://www.comac.cc/fujian/c909acap_en.pdf (R13 2025-12-24, §02-02, §02-03) | figure labels "33.46m", "27.29m" | verified |
| 23 | C909 height / span | WP 8.44 m / 27.28 m vs ACAP 8.606 m / 27.29 m | Comac_C909 wikitext vs row 22 | "{{convert|8.44|m..." | contradicted |
| 24 | C919 / C909 seats and range | 158–192 seats, 4,075–5,555 km / 78–97 seats, 2,225–3,700 km | https://english.comac.cc/products/ca/ ; https://english.comac.cc/products/c909/ | "a layout of 78 to 97 seats and a range of 2,225 to 3,700 kilometers" | verified |
| 25 | COMAC document licence | Proprietary; no reproduction, quoting or use without written authorisation | ACAP PDFs (rows 21–22); https://www.comac.cc/bottom/201401/13/t20140113_1340598.shtml | "shall not be reproduced, quoted, disclosed or used directly or indirectly ... except with prior written authorization by COMAC" | verified |
| 26 | COMAC trademarks | COMAC, ARJ21, C909, C919 names and logos | ACAP front matter | "are all trademarks owned by the Commercial Aircraft Corporation of China, Ltd." | verified |
| 27 | Open C919 model | "C919 B" by juarturo, CC BY 4.0, 88,320 faces, downloadable | https://sketchfab.com/3d-models/c919-b-d7f372558e1c48fca54c145f2a491fc4 (API: https://api.sketchfab.com/v3/models/d7f372558e1c48fca54c145f2a491fc4) | "Author must be credited. Commercial use is allowed." | verified (licence as declared by the uploader) |
| 28 | Same model on GitHub | `AlstonZhuang/comac` `public/models/aircraft/scene.glb` + `license.txt` | https://github.com/AlstonZhuang/comac (commit 957bdc44) | "licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)" | verified |
| 29 | C919 B scale | Not to scale: span/length 0.974 (ACAP 0.920) | `tools/fleet/gltf_bbox.py` on the glTF JSON | – | verified [obs] |
| 30 | Open ARJ21 model | "ARJ21" by DL.123, CC BY 4.0, 607,816 faces, downloadable, white model | https://sketchfab.com/3d-models/arj21-1d2d165256ea48bdbc420388bb6807a5 | "art/飞机白模" (description) | verified (uploader-declared) |
| 31 | Unlicensed C919 models | thaweverything (non-commercial), jsong.js.us (paid), 3devok (store), `459605823/vis-c919` (no licence), `caleseele/c919-autonomy` (no licence, GLB not published) | see §3.1–3.2 | "Non-Commercial / Educational Use Only" | verified [obs] |
| 32 | FlightGear | No C919 / ARJ21 in FGAddon trunk (676 aircraft) | https://sourceforge.net/p/flightgear/fgaddon/HEAD/tree/trunk/Aircraft/ | – | verified [obs] |
| 33 | sfo3d models | 23 models; GPL-2.0 (FGMEMBERS via FAM), A380 CC BY-NC caveat | `sfo3d/docs/ATTRIBUTION_models.md`, `sfo3d/data/models/manifest.json` | "may therefore still be non-commercial only" | verified (repo) |
| 34 | SHA photo sample | 139 aircraft (2024–26): A320 fam 45 %, 737 23 %, A330 14 %, 787 9 %, C919 5 %, A350 2 %, 777 1 %, C909 0 | https://commons.wikimedia.org/w/api.php (search; titles) | e.g. "China Eastern Comac C919 B-919G on final approach to Shanghai Hongqiao May 2026 1.jpg" | secondary [obs] (biased) |
| 35 | Type mix at SHA | A320 fam 45–55 %, 737 23–37 %, wide-body 10–20 %, C919 1–5 %, C909 0–2 %, biz ~1 % | derived (§1.4) | – | unverified (estimate; no ADS-B) |
| 36 | Business jet at SHA | ACJ319 VP-CYW on approach, 2026-05-03 | Commons file "Airbus A319 (VP-CYW) on final approach towards SHA.jpg" | – | secondary [obs] |
| 37 | SHA FBO | "a dedicated FBO with integrated CIQ processing"; no GA departures 0700–0900 | https://www.universalweather.com/blog/shanghai-china-2026-business-aviation-destination-guide/ | "No GA takeoffs between 0700 and 0900 local" | secondary |
| 38 | FBO operator | Historically Shanghai Hawker Pacific Business Aviation Service Centre; Jet Aviation lists no Shanghai site today | https://backend.ainonline.com/aviation-news/business-aviation/2012-09-02/fbo-profile-shanghai-hawker-pacific-business-aviation ; https://www.jetaviation.com/locations/ | "FBO Profile: Shanghai Hawker Pacific Business Aviation Service Centre" (title) | unverified (current operator) |
| 39 | CES livery | 2014 livery, swallow logo of C and E | https://boeing.mediaroom.com/2014-09-24-Boeing-China-Eastern-Airlines-Celebrate-Delivery-of-Airlines-First-777-300ER | "China Eastern debuted its new livery on the new 777-300ER – a change to its 25-year old livery." | verified (OEM release) |
| 40 | FM livery | White crane on red fin; brand kept after the merger | https://en.wikipedia.org/w/index.php?title=Shanghai_Airlines&action=raw | "The logo is a white crane on a red vertical tail fin." | secondary + [obs] photos |
| 41 | 9C livery | 3S logo; "current 2021 livery" (WP) vs solid green tail with "Ch.com" in May 2026 photos | https://en.wikipedia.org/w/index.php?title=Spring_Airlines&action=raw ; Commons B-326Q, B-32MX | "three overlapping and intersecting S's" | contradicted |
| 42 | HO livery | "Chinese Red"; peony-themed 787 | https://tass.com/press-releases/1013334/amp (PR Newswire, 16 Jul 2018) | "Juneyao Airlines' first Boeing 787 aircraft will be delivered with a colorful Chinese peony-themed livery." | verified (issuer release) |
| 43 | Typo in the SHA article | Citation title says "C929"; AeroRoutes' title says C919 | SHA wikitext ref → https://www.aeroroutes.com/eng/240110-mujan24shapkx | "China Eastern Adds COMAC C929 Shanghai - Beijing Service in Jan 2024" | contradicted (WP typo) |
| 44 | SHA coordinate (not this key) | WP infobox 31°11′53″N 121°20′11″E = 31.198056, 121.336389, about 203 m east of the OurAirports ARP hypothesis 31.198104, 121.33426 | SHA wikitext (row 2 URL) | "coordinates = {{coord|31|11|53|N|121|20|11|E" | contradicted (secondary vs secondary; AIP key to settle) |

---

## 7. Risks and open points
- **No observed traffic.** The type mix is an estimate. Schedules (OAG/Cirium) or a working ZSSS feed are needed before tuning model priorities further.
- **Licences**
  - The COMAC ACAP and DWG terms forbid reproduction, quoting and "derivative use". Using their numbers to fit a published model needs the owner's decision.
  - The Sketchfab CC BY models are uploader-declared. Provenance is not provable: they could be rips of commercial models. The "ARJ21" download needs a Sketchfab login.
- **Model quality**
  - "C919 B" is not to scale and has no textures.
  - "ARJ21" is 608k faces, about 10× our budget, so it needs decimation.
  - The GPL A320/CRJ fallbacks are visibly wrong in detail.
- **Livery state is uncertain.** Spring's tail (gradient against solid green), Juneyao's floral rear fuselage (special or new standard) and CES's traditional-character title need more photos before drawing.
- **Trademarks:** airline and COMAC marks; see §4.2.
- **Gaps not researched:** freighters at SHA; helicopters; the current FBO operator; cross-border business-aviation status.

## 8. Files
- **Docs:** `sha3d/docs/phase0/fleet.md` (this file).
- **Scripts** (`sha3d/tools/fleet/`):
  - `wiki_dest.py`: SHA destination list.
  - `wiki_fleet.py`: Wikipedia fleet tables.
  - `type_mix_estimate.py`: Estimate A.
  - `commons_sha_sample.py`: Sample B.
  - `sketchfab_list.py`, `commons_list.py`: listings.
  - `gltf_bbox.py`: glTF JSON bbox.
  - `write_sources.py`: writes all `SOURCES.json`.
- **Caches** (`sha3d/refs/cache/fleet/`):
  - `comac_c919_acap/`, `comac_c909_acap/`, `comac_c919_3view/`, `comac_ccc/`, `comac_en/`, `comac_cn/`, `comac_terms/`
  - `hkex_ces_opdata_202609/`, `hkex_ces_interim_2026/`, `hkex_cca_opdata_202609/`, `hkex_cca_interim_2026/`, `hkex_csn_opdata_202609/`
  - `icao_doc8643/`
  - `wikipedia_*` (24 articles, incl. `wikipedia_sha/`)
  - `commons_livref/` (API JSON), `commons_livref_thumbs/` (reference photos)
- **Caches** (`sha3d/refs/cache/models/`):
  - `sketchfab_<uid>/` (API JSON and thumbnail; 5 models)
  - `gh_AlstonZhuang_comac/`, `gh_459605823_vis-c919/`, `gh_caleseele_c919-autonomy/`, `gh_WenmuWenmu_C919/`, `gh_WenmuWenmu_C919wing/`
