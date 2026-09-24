# ATC audio toggle: verified frequencies, LiveATC feeds, terms and UI (KSFO)

Research for objective item 7 in `CLAUDE.md` (the "ATC audio toggle", via LiveATC) and `docs/HANDOFF.md` P2 #9.
Compiled 24 Sep 2026 (07:30–08:15 UTC) by Claude. No code or data files were changed.

**Evidence tags.** Every fact carries one of these tags:

| Tag | Meaning |
|---|---|
| **[FAA]** | Read by me in an FAA primary publication: Chart Supplement, NASR 28-day subscription or d-TPP chart. |
| **[AirNav]** | AirNav.com, which republishes FAA NASR data. |
| **[LATC-arch]** | A liveatc.net page as captured by the Internet Archive (capture date given). liveatc.net itself could not be read from here (§2.1). |
| **[LATC-live]** | Observed on LiveATC's stream servers on 24 Sep 2026, from HTTP response headers only. |
| **[3P]** | Another third party. |
| **[INF]** | My inference. Not stated by any source. |
| **[UNVERIFIED]** | Could not be checked against an original source. |

Local copies of every source are in `refs/cache/atc/` (gitignored). The file list is in §6.

---------------------------------------------------------------------------------------------------------------------

## 0. Summary

1. **FAA frequencies (current editions):**
   - D-ATIS 118.85 (113.7 and 115.8 are also listed; see §1.1 for a conflict).
   - Clearance Delivery / pre-taxi clearance 118.2, plus PDC and CPDLC.
   - Ground 121.8 (primary) and 124.25 (secondary).
   - Tower 120.5 (only one VHF tower frequency is published; UHF 269.1).
   - NorCal Approach:
     - 134.5 on every SFO approach plate;
     - 128.325, 133.95 and 128.575 as initial contact, depending on the arrival (STAR);
     - the Chart Supplement also lists 120.9.
   - NorCal Departure 135.1 (SE–W) and 120.9 (NW–E).

   Sources: Chart Supplement SW, effective 0901Z 3 Sep 2026 to 0901Z 29 Oct 2026; NASR effective 2026-09-03; d-TPP cycle 2609 (3 Sep – 1 Oct 2026). **[FAA]**
2. **LiveATC** lists **16 feeds** on its KSFO page. This comes from the 23 Jun 2026 archive capture, the latest that exists. **[LATC-arch]**
   - All the mounts in the handoff exist: `ksfo_twr`, `ksfo_gnd`, `ksfo_gnd_twr`, `ksfo_app2_l`, `koak_dep`.
   - Nine mounts answered live on 24 Sep 2026 with their names in the stream metadata. **[LATC-live]**
   - LiveATC's frequency labels include five frequencies that **no FAA publication lists for SFO**: 128.65 "Tower (secondary)"; 120.35 / 133.175 / 135.65 on the finals; 127.975 for departures. **[UNVERIFIED]**
   - Two FAA-published approach frequencies are **not carried by any KSFO feed**: 134.5 and 128.575.
3. **LiveATC terms:**
   - personal, non-commercial use only;
   - "consult LiveATC.net prior to linking directly to any of the audio streams";
   - no "dedicated desktop or mobile application designed to make the LiveATC.net Services directly available" without consent;
   - no making the services "available over a network (other than LiveATC.net's network)";
   - and on every page: "**Audio streams may not be used in any third-party products.**"

   Source: the terms page as captured 10 Jul 2026, "Last Modified: February 1, 2009". **[LATC-arch]**
4. **Can our page play LiveATC in an `<audio>` element?**
   - **Technically yes.** The streams are `audio/mpeg` with `Access-Control-Allow-Origin: *`, and LiveATC's own player is a plain `<audio>` element. **[LATC-live, LATC-arch]**
   - **Contractually no**, not without LiveATC's written permission.
   - We cannot iframe LiveATC's player either: its pages send `X-Frame-Options: SAMEORIGIN`. **[LATC-arch]**

   **Recommendation:**
   - Open LiveATC's own player page, `https://www.liveatc.net/hlisten.php?mount=<mount>&icao=ksfo`, in a new tab or window.
   - Credit LiveATC with a prominent link.
   - Never proxy, record or probe the streams from our relay.
   - Ask LiveATC for permission if in-app playback is wanted.
5. **The toggle** should:
   - pick a feed by role;
   - open LiveATC;
   - **highlight the live aircraft that are likely on that frequency**, inferred from the `traffic.js` phase plus position (§4);
   - label every frequency as FAA-verified or "LiveATC label only";
   - offer an **audio-delay slider** (0–30 s). LiveATC's FAQ says the delay is "typically less than 20 seconds", so without it the visuals run ahead of what the user hears.

---------------------------------------------------------------------------------------------------------------------

## 1. KSFO frequencies from the FAA (task a)

### 1.1 Chart Supplement (d-CS). This is the frequency list pilots use.

**Source:** *Chart Supplement, Southwest U.S.*, cover: "Effective 0901Z 3 SEP 2026 to 0901Z 29 OCT 2026". SFO is on printed page 275 ("CALIFORNIA 275", continued on 276). The next edition is 29 Oct 2026.
- Full volume: https://aeronav.faa.gov/Upload_313-d/supplements/CS_SW_20260903.pdf (linked from the d-CS page https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dafd/, which lists "CS SW Sep 03 2026" as the current edition and "Oct 29 2026" as the next).
- SFO pages only: https://aeronav.faa.gov/afd/03sep2026/sw_275_03SEP2026.pdf, found by the d-CS search https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dafd/search/results/?cycle=2609&ident=SFO ("Procedure effective date: 0901Z Sep 03 - 0901Z Oct 29, 2026").

The COMMUNICATIONS block reads as follows. I checked the text extraction against a render of the page, `refs/cache/atc/cs_sfo_comms.png`. **[FAA]**

```
COMMUNICATIONS: D–ATIS 118.85 115.8 113.7 650–821–0677/1677/2677 UNICOM 122.95
®NORCAL APP CON 120.9  128.325  134.5  133.95
TOWER 120.5 GND CON 121.8  124.25 CLNC DEL 118.2 PRE TAXI CLNC 118.2
®NORCAL DEP CON 135.1 (SE–W) 120.9 (NW–E)
CPDLC (LOGON KUSA)
PDC
AIRSPACE: CLASS B See VFR Terminal Area Chart.
```

Other items on the same pages:
- Header: "SAN FRANCISCO INTL (SFO)(KSFO) … N37º37.13´ W122º22.53´ … NOTAM FILE SFO".
- Remarks: "Due to obstructed vision, SFO twr is able to provide only limited arpt tfc ctl svc on Twy A between gates 88 and 89 … the twr is una to dtrm if acft pulling into gate F11 are at the hook–up spot or in the gate … Twy A btn gates F20 and F21".
- "ASSC in use. Operate transponders with altitude reporting mode and ADS–B (if equipped) enabled on all airport surfaces." Relevant to us: aircraft are asked to keep ADS-B on while on the surface. **[FAA]**

**Conflict inside the Chart Supplement (unresolved) [FAA]:**
- 115.8 and 113.7 are listed as D-ATIS frequencies.
- The navaid entries for those same frequencies are "(VL) (L) VORW/DME 115.8 SFO" (p. 276) and "POINT REYES … (VH) (DH) VORW/DME 113.7 PYE" (p. 247 of the volume).
- The CS legend defines "W … Without voice on radio facility frequency" (PDF p. 30; the legend text is font-encoded and was decoded).

So whether the ATIS can be heard on the VOR frequencies is unclear. A third-party D-ATIS text read at 0656Z on 24 Sep also said "SFO DME OTS, SFO VOR OTS" **[3P, atis.info; NOTAMs not checked]**. **For the app, show 118.85 as the ATIS voice frequency.**

### 1.2 NASR (FAA 28-day subscription). This adds the use code and sectorisation behind each frequency.

**Source:** NASR subscription effective 2026-09-03 (next 2026-10-01). Listed at https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/2026-09-03/.
- `FRQ.csv` from https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_FRQ_CSV.zip.
- `ATC_*.csv` from https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_ATC_CSV.zip.

There are 106 rows with `SERVICED_FACILITY = SFO`, all `EFF_DATE 2026/09/03`. They are extracted to `refs/cache/atc/nasr_frq_sfo_20260903.csv`. **[FAA]**

| Position | Freq (VHF) | UHF | NASR `FREQ_USE` / `SECTORIZATION` | Facility |
|---|---|---|---|---|
| D-ATIS | 118.85, 113.7, 115.8 | — | `D-ATIS` | SFO ATCT |
| Clearance Delivery / pre-taxi | 118.2 | — | `CD PRE TAXI CLNC` | SFO ATCT |
| Ground (primary) | 121.8 | — | `GND/P` | SFO ATCT |
| Ground (secondary) | 124.25 | — | `GND/S` | SFO ATCT |
| Tower (local control) | 120.5 | 269.1 | `LCL/P` | SFO ATCT |
| Emergency | 121.5 | — | `EMERG` | SFO ATCT |
| UNICOM | 122.95 | — | `UNICOM` | SFO |
| NorCal Approach, primary | 128.325 | (254.25, 310.8)¹ | `APCH/P` | NCT (Northern California TRACON) |
| NorCal Approach, primary "IC" | 134.5 | 338.2 | `APCH/P IC` | NCT |
| NorCal Approach, secondary | 133.95 | (251.05)¹ | `APCH/S` | NCT |
| NorCal Departure | 135.1 | 307.2 | `DEP/P`, `SE-W` | NCT |
| NorCal Departure | 120.9 | 323.2 | `DEP/P`, `NW-E` | NCT |

¹ NASR stores each UHF frequency as a separate row with the same use code; it does not pair UHF with VHF. The charts do pair them:
- 128.325 with **254.3** (ALWYS, DYAMD, MODESTO, YOSEM);
- 133.95 with **317.6** (BDEGA and the other north/west STARs);
- 134.5 with 338.2;
- 135.1 with 307.2;
- 120.9 with 323.2. **[FAA]**

Notes:
- NASR does not define the "IC" suffix. I checked the NASR `FRQ DATA LAYOUT.pdf` and the CS abbreviation list. **[UNVERIFIED meaning]**
- **NASR does not list 120.9 as an approach frequency**, only as DEP/P (NW-E) and CLASS B (NW). The Chart Supplement *does* print 120.9 in the NORCAL APP CON list. AirNav follows NASR: "NORCAL APPROACH: 128.325 134.5 133.95". **[FAA, AirNav]**
- `ATC_BASE.csv` fields: `TWR_HRS 24`, `TWR_CALL SAN FRANCISCO`, `PRIMARY_APCH_RADIO_CALL NORCAL`, `APCH_P_PROVIDER NCT`, `DEP_P_PROVIDER NCT`. **[FAA]**
- `ATC_ATIS.csv` has **one** ATIS for SFO: `ATIS_NO 1`, `DESCRIPTION D-ATIS`, `ATIS_HRS 24`. The phone numbers "650-821-0677/1677/2677" are in `ATC_RMK.csv`. **No separate arrival or departure ATIS frequency is published.** **[FAA]**
  - The datalink D-ATIS was a single "combined" message (INFO K) at 0656Z on 24 Sep. Source: https://atis.info/api/KSFO **[3P]**.
  - Whether SFO splits it into ARR and DEP messages in daytime is **[UNVERIFIED]**.
  - LiveATC's `ksfo_atis` feed lists only 118.850.
- Class B sector frequencies (VFR services), from NASR: 120.9 NW, 125.35 NE-E, 127.0 NORTH, 133.95 SOUTH, 134.5 EAST, 135.1 WEST. **[FAA]** This explains why 127.0 appears in LiveATC's "Dep" feeds. **[corrected by verifier]** This is only a partial explanation. NASR also lists 127.0 for OAK, as `CLASS C NORTH` and as the frequency of the OAK **NIMITZ DP**. That explains 127.0 on the joint `koak_dep` "NORCAL Departure (KSFO/KOAK)" feed more directly. Which facility the 127.0 audio actually serves is **[UNVERIFIED]**.

### 1.3 d-TPP charts (approach plates, STARs, DPs, airport diagram). These give the frequency pilots actually tune on each procedure.

**Source:** d-TPP cycle 2609. Every chart footer reads "SW-2, 03 SEP 2026 to 01 OCT 2026".
- Search: https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dtpp/search/results/?cycle=2609&ident=SFO
- Charts: `https://aeronav.faa.gov/d-tpp/2609/00375<name>.pdf`.

I downloaded all 45 SFO charts and read their comms strips. The ILS RWY 28L strip was also checked visually: `refs/cache/atc/il28l_comms.png`. **[FAA]**

> **[corrected by verifier]** The d-TPP search result is paginated ("Showing results 1–50 of 54"). Page 2 (https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dtpp/search/results/?cycle=2609&ident=SFO&page=2) lists four more SFO departure procedures that this report missed. So cycle 2609 has **49** SFO chart PDFs (`00375*.pdf`), not 45. The four are SNTNA TWO (RNAV), SSTIK FIVE (RNAV), TRUKN TWO (RNAV) and WESLA FIVE (RNAV), saved in `refs/cache/atc_verify/dtpp2609_extra/`. Their NORCAL DEP CON frequencies match NASR (see the DP table below), and none of them contains any of the LiveATC-only frequencies in §1.5, so the frequency picture does not change.

- **All 22 SFO approach plates** (6 ILS, 4 GLS, 8 RNAV (GPS), 2 RNAV (RNP), and the two charted visuals, QUIET BRIDGE VISUAL RWY 28R and TIPP TOE VISUAL RWY 28L/R) carry the same strip. I checked each file:
  - "D-ATIS 113.7 115.8 118.85";
  - "NORCAL APP CON **134.5** 338.2";
  - "SAN FRANCISCO TOWER **120.5** 269.1";
  - "GND CON **121.8**".
  - Example: https://aeronav.faa.gov/d-tpp/2609/00375il28l.pdf
- **Airport diagram** (https://aeronav.faa.gov/d-tpp/2609/00375ad.pdf): "D-ATIS 113.7 115.8 118.85 · SAN FRANCISCO TOWER 120.5 269.1 · GND CON 121.8 · CLNC DEL 118.2 · CPDLC".
- **STARs:** the first NorCal Approach frequency after Oakland Center.

| STAR (current chart) | NORCAL APP CON | Previous controller on chart (Oakland Center) | Chart |
|---|---|---|---|
| ALWYS THREE (RNAV) | 128.325 | 134.37 | `00375alwys.pdf` |
| DYAMD FIVE (RNAV) | 128.325 | 134.37 | `00375dyamd.pdf` |
| MODESTO NINE | 128.325 | 134.375 | `00375modesto.pdf` |
| YOSEM THREE (RNAV) | 128.325 | 134.375 | `00375yosem.pdf` |
| BDEGA FOUR (RNAV) | 133.95 | 125.85 | `00375bdega.pdf` |
| STLER FOUR (RNAV) | 133.95 | 125.85 | `00375stler.pdf` |
| PIRAT THREE (RNAV) (SFO/OAK) | 133.95 | 134.15 | `00375pirat.pdf` |
| POINT REYES THREE | 133.95 | (chart also lists SJC/SQL/RHV/PAO/NUQ ATIS) | `00375pointreyes.pdf` |
| STINS FOUR | 133.95 | by transition: (MUSTANG) 134.45, (RED BLUFF) 134.975, (ROSEBURG, FORTUNA) 119.975 | `00375stins.pdf` |
| BIG SUR THREE | 128.575 | 125.45 | `00375bigsur.pdf` |
| SERFR FOUR (RNAV) | 128.575 | 134.55 | `00375serfr.pdf` |
| WWAVS TWO (RNAV) | 128.575 | 134.55 | `00375wwavs.pdf` |
| RISTI ONE (RNAV) | 134.5 | — | `00375risti.pdf` |

  NASR `FRQ.csv` assigns the same frequency to each STAR name. So does AirNav, e.g. "SERFR STAR: 128.575", "RISTI STAR: 134.5". **[FAA, AirNav]**
- **Departure procedures (DPs):** "NORCAL DEP CON" on the chart.

| DP (charted under SFO in cycle 2609) | NORCAL DEP CON |
|---|---|
| CIITY THREE (RNAV), NIITE FOUR (RNAV), SAN FRANCISCO FIVE | 120.9 |
| GNNRR THREE (RNAV), MOLEN NINE, SAHEY FOUR (RNAV), SEGUL ONE (RNAV) | 135.1 |
| GAP SEVEN | "135.1 307.2 (SE-W) 120.9 323.2 (NW-E)" |
| SNTNA TWO (RNAV), TRUKN TWO (RNAV) **[added by verifier; page 2 of the d-TPP listing]** | 120.9 323.2 |
| SSTIK FIVE (RNAV), WESLA FIVE (RNAV) **[added by verifier; page 2 of the d-TPP listing]** | 135.1 307.2 |

  NASR also has DP-frequency rows for names that are **not** charted under SFO or OAK in d-TPP 2609. I checked the OAK search results too. **[corrected by verifier]** The names are DUMB, EUGEN, FOGGG, GAPP, LUVVE, OFFSHORE, PORTE, QUIET, REBAS, SEAGUL and SHORELINE. The original list also included SEGUL, SNTNA, SSTIK, TRUKN and WESLA, but those five *are* charted under SFO in cycle 2609: SEGUL ONE is on page 1 of the listing and the other four are on page 2. GAPP (135.1, SE-W) is probably the SE-W half of GAP SEVEN, which the chart prints as 135.1 (SE-W) **[INF, verifier]**. The remaining names are possibly stale rows or procedures charted elsewhere **[UNVERIFIED]**. None changes the frequency picture: each is 120.9 or 135.1. OFFSHORE and SEAGUL have only a UHF 307.2 row, which is 135.1's UHF pair.

### 1.4 AirNav cross-check

**Source:** https://www.airnav.com/airport/KSFO ("FAA INFORMATION EFFECTIVE 03 SEPTEMBER 2026"). It matches NASR exactly:
- "SAN FRANCISCO GROUND: 121.8 124.25"
- "SAN FRANCISCO TOWER: 120.5 269.1"
- "NORCAL APPROACH: 128.325 134.5 133.95"
- "NORCAL DEPARTURE: 120.9 ;NW-E 135.1 ;SE-W"
- "CLEARANCE DELIVERY: 118.2"
- "PRE-TAXI CLEARANCE: 118.2"
- "D-ATIS: 113.7 115.8 118.85"
- "IC: 134.5"
- the per-STAR and per-DP lines, and the Class B list. **[AirNav]**

### 1.5 What the FAA does *not* publish for SFO

LiveATC's feed labels (§2.2) include the frequencies below. I searched every California row of NASR `FRQ.csv` and the text of all 45 SFO charts for them. **[FAA search, negative result]** *(The verifier repeated the search over all 49 charts, including the 4 DPs this report missed (§1.3), and over the CS page. It found none of these frequencies.)*

| LiveATC label | Freq | FAA status |
|---|---|---|
| "San Francisco Tower (secondary)" / "(alternate/backup)" | 128.65 | Not published for SFO. NASR has 128.65 only for NTD (Point Mugu). |
| "NORCAL Approach (Foster Sector, SFO 28R Final)" | 120.35 | Not published for SFO. NASR has 120.35 only as LAX CD/P. |
| "NORCAL Approach (Foster Sector, SFO 28R Final)" | 133.175 | Not in NASR for California at all. |
| "NORCAL Approach (Woodside Sector, SFO 28L Final)" | 135.65 | Not published for SFO. NASR has it as NCT APCH/S and DEP/P for SQL (San Carlos). **[corrected by verifier]** It also lists 135.65 as the LAX `D-ATIS DEP`, so "SQL only" was wrong. The "not for SFO" point stands. |
| "NORCAL Departure (Southwest Departures)" | 127.975 | Not in NASR for California. |
| "KSFO Ramp A (East) / Ramp G (West) / Shadow Ramp" | 127.575 / 119.225 / 131.000 | Ramp control is not an FAA facility. No official SFO source found. |
| "San Francisco Ground/Gate Hold" | 124.25 | FAA publishes 124.25 as GND/S. The "gate hold" use is LiveATC's label only. |

These are plausible controller-assigned sector frequencies. Controllers issue them in flight, so they need not appear in publications. But they are **[UNVERIFIED]**. The only way to confirm them is to hear a controller issue them, for example "contact NorCal one three five point six five", on LiveATC's own archive. **The app must show them as "LiveATC label, not FAA-verified".**

LiveATC's labels are also partly stale. It labels 133.95 as "Boulder Sector, **BSR2** STAR" and 128.325 as "Niles Sector, **MOD2** STAR". The current charts are BIG SUR **THREE**, whose NorCal contact is **128.575**, not 133.95, and MODESTO **NINE** (128.325). **[FAA vs LATC-arch]**

---------------------------------------------------------------------------------------------------------------------

## 2. LiveATC feeds for KSFO (task b)

### 2.1 How the data was obtained (and what failed)

- **Every path on liveatc.net is behind a Cloudflare challenge.** This includes `/search/`, `/play/*.pls`, `/hlisten.php`, `/legal/` and even `/robots.txt`.
  - curl gets `HTTP/2 403` with `cf-mitigated: challenge`.
  - WebFetch gets a 403 too.
  - `m.liveatc.net` does not resolve: WebFetch reports `ENOTFOUND`, and the proxy's CONNECT gets a 502.
  - forums.liveatc.net and archive.liveatc.net also return 403. **[observed 24 Sep 2026]**
- **Internet Archive (Wayback Machine) captures** were used instead. It was intermittently offline (503 or reset) and rate-limited (429), and succeeded on retry:
  - KSFO airport page, **captured 23 Jun 2026 20:32:22 UTC**. This is the latest capture; others are dated 2025-01 to 2026-01-01. https://web.archive.org/web/20260623203222/https://www.liveatc.net/search/?icao=ksfo
  - Terms of Use, captured 10 Jul 2026: https://web.archive.org/web/20260710203412/https://www.liveatc.net/legal/
  - FAQ, captured 23 Jun 2026: https://web.archive.org/web/20260623203228/https://www.liveatc.net/faq/
  - `ksfo_twr.pls`, captured 16 Nov 2025: https://web.archive.org/web/20251116093900/https://www.liveatc.net/play/ksfo_twr.pls
  - `hlisten.php?mount=ksfo_twr&icao=ksfo`, captured 11 Dec 2025: https://web.archive.org/web/20251211093953/https://www.liveatc.net/hlisten.php?mount=ksfo_twr&icao=ksfo
- **Search-engine index:** page titles confirm the `hlisten.php` URL pattern and several mount and feed names. Examples: "Listening to: KSFO NORCAL App 28L/R" = `hlisten.php?mount=ksfo_app2_l&icao=ksfo`; "KSFO Dep 120.9/127.0" = `ksfo_dep1`; "SFO Fleet Week" = `kn_se`. **[3P]**
- **Live check of the stream servers (24 Sep 2026, 07:36–07:43 UTC).**
  - The stream redirector `d.liveatc.net` is *not* behind the challenge. `http://d.liveatc.net/<mount>` answers `302` to `https://s1-bos.liveatc.net/<mount>?nocache=…` or `https://s1-fmt2.liveatc.net/…`. It does this even for nonexistent mounts.
  - On the node, a real mount answers `200 audio/mpeg` with Icecast `icy-name`/`icy-description` headers, and a fake mount answers `404`. I used HEAD requests only, so no audio was transferred.
  - Several requests died with "connection reset". The agent proxy logged these as its own tunnel failures (`ws_closed_mid_exchange`), not refusals by LiveATC, so they are **inconclusive**.
  - A GET of the Icecast `status-json.xsl` was refused (403 "Request forbidden by administrative rules").
  - **Disclosure:** I made about 65 automated HEAD requests before I had read the Terms of Use. Clause 3.13 of those terms restricts automated access (§3.1). I stopped probing once I had read it. The app must not probe or monitor the streams automatically.

### 2.2 KSFO feed list

Columns: mount (primary key), feed title and frequencies with LiveATC's labels (23 Jun 2026 capture), and the live probe on 24 Sep. The 23 Jun data is parsed into `refs/cache/atc/liveatc_ksfo_feeds_20260623.json`. **[LATC-arch]**

- "Status (23 Jun)" is LiveATC's own "Feed Status" / "Listeners" at capture time. **[LATC-arch]**
- "Probe (24 Sep)" is the HTTP result and `icy-name` from the stream server. **[LATC-live]**

| Mount | Feed title (23 Jun 2026) | Frequencies (LiveATC labels) | Status (23 Jun) | Probe (24 Sep, UTC) |
|---|---|---|---|---|
| `ksfo_twr` | KSFO Tower | 120.500 San Francisco Tower; 128.650 San Francisco Tower (secondary) | UP, 21 listeners | 200, icy-name "KSFO Tower", 16 kbit/s, mono 22.05 kHz (07:40:57) |
| `ksfo_gnd` | KSFO Ground | 121.800 San Francisco Ground | UP, 3 | 200, "KSFO Ground", 16 kbit/s |
| `ksfo_gnd_twr` | KSFO Ground/Tower | 121.800 Ground; 120.500 Tower | UP, 3 | 200, "KSFO Ground/Tower", icy-br 64 |
| `ksfo_twr2` | KSFO Tower/Ground | 121.800 Ground; 124.250 Ground/Gate Hold; 120.500 Tower; 128.650 Tower (secondary) | UP, 2 | 200, "KSFO Tower/Ground", icy-br 64 |
| `ksfo_gnd2` | KSFO Del/Gnd (Alt)/Twr (Alt) | 118.200 Clearance Delivery; 124.250 Ground/Gate Hold; 128.650 Tower (alternate/backup) | UP, 3 | not probed |
| `ksfo_atis` | KSFO D-ATIS | 118.850 KSFO Digital ATIS | UP, 1 | 200 audio/mpeg but no icy headers: inconclusive |
| `ksfo_app2_l` | KSFO NORCAL App 28L/R | 120.350 and 133.175 (Foster Sector, SFO 28R Final); 135.650 (Woodside Sector, SFO 28L Final) | UP, 4 | proxy reset ×2: inconclusive |
| `ksfo_app2_r` | KSFO NORCAL BSR2/MOD2 Arrivals | 133.950 (Boulder Sector, BSR2 STAR); 128.325 (Niles Sector, MOD2 STAR) | UP, 4 | not probed |
| `ksfo_app2` | KSFO NORCAL App 28L/R + BSR/MOD STARs | the five frequencies of `_l` and `_r` combined | UP, 2 | proxy reset: inconclusive |
| `ksfo_dep1` | KSFO Dep 120.9/127.0 | 127.000 "NORCAL Approach"; 120.900 NORCAL Departure | UP, 0 | 200, icy-name **"NORCAL Dep (NE)"**, 32 kbit/s |
| `ksfo_dep2` | KSFO Dep 135.1 | 127.975 and 135.100 NORCAL Departure | UP, 0 | 200 without icy headers once, then reset: inconclusive |
| `koak_dep` | NORCAL Departure (KSFO/KOAK) | NE departures: 120.900, 127.000; SW departures: 127.975, 135.100. The page notes: "Southwest departures on left channel - Northeast Departures on right channel" | UP, 4 | 200, "NORCAL Departure (KSFO/KOAK)", icy-br 64 |
| `ksfo_ramp` | KSFO Ramp | 127.575 Ramp A (East); 119.225 Ramp G (West); 131.000 Shadow Ramp | UP, 0 | 200, "KSFO Ramp", 16 kbit/s |
| `ksfo_co` | KSFO Company Channels | (none listed) | UP, 0 | 200, "KSFO Company Channels" |
| `zoa_sfo` | ZOA Oakland Center (35/40/41) | 134.150 / 127.800 / 125.850 (Sectors 35 / 40 / 41) | UP, 4 | 200, "ZOA Oakland Center (35/40/41)" |
| `zoa_35` | ZOA Oakland Center (35) | 134.150 Sector 35, 355.600 UHF, ARINC 131.950, "Beaver Control" military discretes | UP, 7 | not probed |

Other points:
- `kn_se` ("SFO Fleet Week" in the search index) returned **404** on 24 Sep. It is presumably seasonal **[INF]**.
- Guessed names `ksfo_app`, `ksfo_dep` and `ksfo_del` also return 404. They do not exist.
- `ksfo_app2` appears to be `ksfo_app2_l` and `ksfo_app2_r` combined, like the explicit left/right split of `koak_dep` **[INF]**.
- "UP" does not guarantee audio. LiveATC's FAQ: "Sometimes a feed may show as 'Up' but have no audio." **[LATC-arch]**
- Feed titles change. `ksfo_dep1` was titled "KSFO Dep 120.9/127.0" on 23 Jun, but its stream announced "NORCAL Dep (NE)" on 24 Sep. **Key the app on the mount name, not the title.** **[LATC-arch vs LATC-live]**

**Handoff (P2 #9) check:**

| Handoff claim | Result |
|---|---|
| `ksfo_twr` (120.5) | Exists; also carries 128.65 |
| `ksfo_gnd` (121.8) | Exists |
| NorCal Approach `ksfo_app2_l` | Exists. It carries the *final* sectors (120.35 / 133.175 / 135.65, all LiveATC-only), **not** the published 134.5 |
| Departure `koak_dep` | Exists. It covers both departure sectors in stereo |
| `ksfo_gnd_twr` | Exists |

### 2.3 Coverage matrix: FAA frequency to the LiveATC mounts that carry it (per the 23 Jun 2026 labels)

| Role | FAA freq | Carried by | Gap / note |
|---|---|---|---|
| ATIS | 118.85 | `ksfo_atis` | — |
| Clearance / pre-taxi | 118.2 | `ksfo_gnd2` | Many airline clearances go by PDC or CPDLC (both published), so clearance audio is sparse **[INF]** |
| Ground (P) | 121.8 | `ksfo_gnd`, `ksfo_gnd_twr`, `ksfo_twr2` | — |
| Ground (S) | 124.25 | `ksfo_gnd2`, `ksfo_twr2` | — |
| Tower | 120.5 | `ksfo_twr`, `ksfo_gnd_twr`, `ksfo_twr2` | — |
| Tower (LiveATC only) | 128.65 | `ksfo_twr`, `ksfo_twr2`, `ksfo_gnd2` | Not FAA-published |
| Approach, arrivals from the east (ALWYS/DYAMD/MODESTO/YOSEM) | 128.325 | `ksfo_app2`, `ksfo_app2_r` | — |
| Approach, arrivals from the north and west (BDEGA/STLER/PIRAT/POINT REYES/STINS) | 133.95 | `ksfo_app2`, `ksfo_app2_r` | — |
| Approach, arrivals from the south (BIG SUR/SERFR/WWAVS) | 128.575 | **none** | Not covered by any KSFO feed |
| Approach, plates and RISTI | 134.5 | **none** | Not covered by any KSFO feed |
| Approach finals (LiveATC only) | 120.35 / 133.175 (28R), 135.65 (28L) | `ksfo_app2_l`, `ksfo_app2` | Not FAA-published |
| Departure NW–E | 120.9 | `ksfo_dep1`, `koak_dep` (right channel) | — |
| Departure SE–W | 135.1 | `ksfo_dep2`, `koak_dep` (left channel) | — |
| "Departure" 127.0 | 127.0 | `ksfo_dep1`, `koak_dep` (right channel) | NASR: SFO Class B NORTH. LiveATC: NE departures. **[corrected by verifier]** NASR also lists 127.0 as OAK Class C NORTH and the OAK NIMITZ DP |
| "Departure" 127.975 | 127.975 | `ksfo_dep2`, `koak_dep` (left channel) | Not FAA-published |
| Ramp | (LiveATC labels only) | `ksfo_ramp` | Not FAA; unverified |

### 2.4 Stream mechanics (for reference only; do not use without permission)

- The playlist `ksfo_twr.pls` (captured 16 Nov 2025) contains `File1=http://d.liveatc.net/ksfo_twr`, `Title1=KSFO Tower`. **[LATC-arch]**
- LiveATC's own player page `hlisten.php` (captured 11 Dec 2025) is an ad-supported page (Google Publisher Tags) with a MediaElement.js player:

  ```html
  <audio id="player2" crossorigin="anonymous" preload="auto" src="https://s1-bos.liveatc.net/ksfo_twr?nocache=2025121109395354837" type="audio/mp3" controls="controls" autoplay="true">
  ```

  It is followed by a Web Audio peak meter and the note "If stream doesn't start automatically press the play button". **[LATC-arch]**
- The airport page opens this player with `onClick="myHTML5Popup('ksfo_twr','ksfo')"`, i.e. as a popup window. **[LATC-arch]**
- Stream response headers seen on 24 Sep:
  - `content-type: audio/mpeg`
  - `ice-audio-info: channels=1;samplerate=22050;bitrate=16` (ksfo_twr)
  - `access-control-allow-origin: *`
  - `access-control-allow-methods: GET, OPTIONS, SOURCE, PUT, HEAD, STATS`
  - `cache-control: no-cache, no-store`
  - `server: LiveATC`

  **[LATC-live]**
- Framing:
  - The original `hlisten.php` response carried `X-Frame-Options: SAMEORIGIN` (Wayback header `x-archive-orig-x-frame-options`, 11 Dec 2025).
  - The KSFO page, served via Cloudflare, carried the same header on 23 Jun 2026.
  - So **neither page can be embedded in an iframe** on our origin. **[LATC-arch]**
- Latency. LiveATC FAQ: "Transmissions have to traverse this path: feeder -> main audio server -> slave audio server -> listener. Delay depends on a number of factors, but delay is typically less than 20 seconds for most listeners." **[LATC-arch]**

---------------------------------------------------------------------------------------------------------------------

## 3. LiveATC terms, and whether we may play, link or embed (task c)

### 3.1 Verbatim terms

**Source:** https://www.liveatc.net/legal/ as captured 10 Jul 2026 (https://web.archive.org/web/20260710203412/https://www.liveatc.net/legal/). The full terms are "(EFFECTIVE AS OF FEBRUARY 1, 2009)" and footed "Last Modified: February 1, 2009". The full text is in `refs/cache/atc/liveatc_legal_20260710.txt`. **[LATC-arch]**

From the plain-English summary at the top of the page, which says it "is not a legal document":

> 2) LiveATC.net is for non-commercial (personal) use only - that means you can't use LiveATC.net and the audio streams here for personal gain, financial or otherwise.
>
> 3) You can't produce and distribute a dedicated desktop or mobile application designed to make the LiveATC.net Services directly available, without the consent of or a contract with LiveATC.net.
>
> 4) Since there are only limited numbers of connections available for streams, and because the site is funded through advertising and donations, you agree to consult LiveATC.net prior to linking directly to any of the audio streams. When you do link you agree to give credit to LiveATC.net with a prominent link to www.liveatc.net.
>
> 10) You will only access the LiveATC.net web site with an interactive web browser (or other authorized agents, which include general purpose media players) and not with any program, collection agent, or "robot" for the purpose of automated retrieval of content, unless you are granted permission by LiveATC.net to do so.

From the Agreement itself:

> 2.1 License Grante. LiveATC.net grants to you a limited, non-exclusive, non-transferable license to access and use the LiveATC.net Services for personal non-commercial purposes only. […] ANY USE OF THE LIVEATC.NET SERVICES NOT SPECIFICALLY PERMITTED UNDER THIS AGREEMENT IS STRICTLY PROHIBITED.
>
> 3. RESTRICTIONS — You agree that you will not: […]
> 3.3 make the LiveATC.net Services available over a network (other than LiveATC.net's network) where it could be used by others;
> 3.4 make the LiveATC.net Services directly available via any other dedicated desktop or mobile commercial application, for profit or not; […]
> 3.13 access the LiveATC.net web site with other than an interactive web browser (or other authorized software agents, which include general purpose media players) or with any program, collection agent, or "robot" for the purpose of automated retrieval of content, unless you are granted permission by LiveATC.net to do so. […]
> 3.15 link directly to any of the audio streams without consulting with LiveATC.net. When you do link you agree to give credit to LiveATC.net with a prominent link to www.liveatc.net; […]
>
> 4. COPYRIGHTS — As between you and LiveATC.net, you acknowledge that LiveATC.net owns or has a license to all title and copyrights in and to the LiveATC.net Services. […]
>
> 13.5 This Agreement will be governed by the laws of the State of Massachusetts. […]

The footer on every captured LiveATC page (legal, FAQ, KSFO):

> All Content Copyright© 2002-2026, LiveATC.net LLC, All Rights Reserved.
> **Audio streams may not be used in any third-party products.**
> LiveATC.net is not affiliated with the FAA or any other aviation authority.

The KSFO airport page adds "NOTICE — Unauthorized use prohibited. See LiveATC.net Terms of Service". Support is reached through "our support form". The search index lists it at https://www.liveatc.net/ct/contact.php **[3P; page itself not readable]**.

The terms were read from a capture, not the live page. The live page might have changed after 10 Jul 2026. It was last modified in 2009, so a change is unlikely, but that is **[UNVERIFIED]**.

### 3.2 What this means for SFO Live 3D

This is my reading of the terms, not legal advice. **[INF]**

| Option | Technically possible? | Allowed by the LiveATC terms? | Verdict |
|---|---|---|---|
| `<audio src="https://d.liveatc.net/ksfo_twr">` in our page | Yes: `audio/mpeg`, CORS `*`. This is exactly what LiveATC's own player does | **No.** It links directly to a stream (3.15: consult first) and uses the stream in a third-party product (footer). It arguably also makes the Services "directly available" through our app (summary item 3, clause 3.4) | Only with **written permission** from LiveATC |
| Web Audio (visualiser, ducking) on that stream | Yes, with `crossorigin="anonymous"` | As above | Only with permission |
| Proxy or relay the stream through `sfo_live_server.py` | Yes | **No.** 3.3 bars making the Services available "over a network (other than LiveATC.net's network)", and 3.13 bars automated retrieval | **Never** |
| Record the audio, or align it with ADS-B server-side | Yes | **No** (3.13; the footer) | **Never** |
| `<iframe src="…/hlisten.php?…">` | **No**: `X-Frame-Options: SAMEORIGIN` | — | Impossible |
| Link to `.pls` or `d.liveatc.net/<mount>` (a direct stream link, opens the OS media player) | Yes | 3.15: "consult with LiveATC.net" first, plus prominent credit | Only after consulting LiveATC |
| **Link out to LiveATC's own player page** `https://www.liveatc.net/hlisten.php?mount=<mount>&icao=ksfo` (new tab or window), or to https://www.liveatc.net/search/?icao=ksfo | Yes | The terms restrict links *directly to the audio streams*. These are LiveATC web pages, with their ads and attribution intact. The terms do not restrict linking to them. Out of courtesy, still credit LiveATC and tell them | **Recommended default** |
| Automated feed-status checks (for "UP/DOWN" badges) | Yes: the stream redirector and nodes answer | **No** (3.13, unless permitted) | Do not do this. Show "status: see LiveATC" |

- **Personal and non-commercial use.** The LiveATC licence covers the *listener's* personal use (2.1). If SFO Live 3D is ever distributed publicly or commercially, even the link-out should be cleared with LiveATC first. **[INF]**
- **Snapshot / Claude-artifact build.** The artifact's CSP already blocks external fetches, so in-app audio is impossible there anyway. Whether the artifact sandbox allows opening an external link (`target=_blank`) is **[UNVERIFIED]**. If it does not, show the URL as text.

### 3.3 Alternative sources

1. **LiveATC, with permission.** Ask through the support form. The request should cover:
   - in-app `<audio>` playback with credit and LiveATC's link, for personal, non-commercial use;
   - whether linking to `hlisten.php` from the app is acceptable;
   - optionally, an approved way to show feed status.

   Draft:

   > Subject: Permission request — linking/playing KSFO feeds in a personal, non-commercial 3D airport viewer
   > I'm building a personal, non-commercial 3D visualisation of SFO driven by public ADS-B data. I'd like an "ATC" button that opens your KSFO player pages (hlisten.php?mount=ksfo_twr etc.) with a prominent "Audio: LiveATC.net" credit and link. Optionally, I'd like to play the stream inside the page via an HTML5 audio element (no relaying, recording or automated access). May I do either? Happy to follow any conditions you set.
2. **Broadcastify.** It is not an option without a commercial licence.
   - Its Terms (https://www.broadcastify.com/terms/, captured 10 Sep 2026, "Last Updated: July 22, 2026") §9 require "a commercial license from Broadcastify, regardless of who is performing it, the scale involved, or the stated purpose" for any of the following:

     > (d) Any redistribution, relay, rebroadcast, re-streaming, or embedding of Broadcastify live audio to or on behalf of any other person, application, website, device, or service.

     They add: "A use does not become permitted because it is limited in scale, unpaid, or characterized as personal, hobby, … non-commercial … or one-time". Licences come through https://bcfy.io. **[3P, via Wayback: https://web.archive.org/web/20260910062306/https://www.broadcastify.com/terms/]**
   - Its SFO scanner feed 3561 ("SFO Airport - KSFO and Oakland Center", from the search index) showed "Invalid Feed ID" in a 15 Aug 2025 capture. It is probably gone **[UNVERIFIED today]**.
   - broadcastify.com returns 403 to curl.
3. **The user's own receiver.** This is the only source with no third-party terms. An airband SDR in radio range of SFO would feed the local relay, and the app would play it in `<audio>` on the user's own devices. US law:
   - 18 U.S.C. §2511(2)(g): "It shall not be unlawful under this chapter or chapter 121 of this title for any person— … (ii) to intercept any radio communication which is transmitted— … (IV) by any marine or aeronautical communications system". Source: https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title18-section2511&num=0&edition=prelim
   - 47 U.S.C. §605(a) still restricts *divulging or publishing* intercepted communications to others: "No person not being authorized by the sender shall intercept any radio communication and divulge or publish the existence, contents, substance, purport, effect, or meaning of such intercepted communication to any person". Its closing exception covers communications "transmitted by any station for the use of the general public, which relates to ships, aircraft, vehicles, or persons in distress". Source: https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title47-section605&num=0&edition=prelim

   **[FAA-independent primary law text; interpretation not legal advice]** Personal reception is clearly lawful. Streaming to other people is a question for a lawyer. Whether the user is within radio range of SFO is **[UNVERIFIED]**.
4. **The FAA.** I found no FAA product that publishes live ATC audio **[UNVERIFIED negative]**. The FAA publishes frequencies (§1) but not audio.
5. **Text instead of audio.** The D-ATIS text (for example https://atis.info/api/KSFO, which datis.clowd.io redirects to) could be shown in an "ATIS" card. It is third-party and its **terms were not checked [UNVERIFIED]**. Treat it as optional.

---------------------------------------------------------------------------------------------------------------------

## 4. Recommended toggle behaviour (task d)

This section is design guidance. The frequency *facts* are sourced above. The phase-to-frequency *assignment* rules are **[INF]**: controllers hand aircraft off at points they choose, and those points are not published.

### 4.1 Controls

- **"ATC" button** in the top bar. `ui.js` already has the view buttons plus Settings and About there. It opens a sheet, which should be a bottom sheet on phones.
- **Feed picker, grouped by role.** Each row shows:
  - the role;
  - the mount's frequencies, each with a badge: **FAA** (CS, NASR or plate) or **LiveATC label**;
  - "Listen on LiveATC ↗".

  Defaults:

  | Role | Default mount | Alternatives |
  |---|---|---|
  | Tower | `ksfo_twr` | `ksfo_gnd_twr`, `ksfo_twr2` |
  | Ground | `ksfo_gnd` | `ksfo_gnd_twr`, `ksfo_twr2` |
  | Clearance | `ksfo_gnd2` | — |
  | Approach, finals | `ksfo_app2_l` | `ksfo_app2` (finals + arrivals) |
  | Approach, arrivals | `ksfo_app2_r` | `ksfo_app2` |
  | Departure | `koak_dep` (both sectors) | `ksfo_dep1` (NE), `ksfo_dep2` (SW) |
  | ATIS | `ksfo_atis` | — |
  | Ramp | `ksfo_ramp` | — |
  | Center | `zoa_sfo` | — |

- **Opening the feed.** Use `window.open('https://www.liveatc.net/hlisten.php?mount=' + mount + '&icao=ksfo', 'liveatc', 'noopener')`. On phones this opens a new tab, which mirrors LiveATC's own `myHTML5Popup` popup.
  - The user presses Play on LiveATC's page, because autoplay is blocked without a user gesture. LiveATC's page itself says "If stream doesn't start automatically press the play button".
  - Whether iOS Safari and Android Chrome keep that tab's audio playing while the user returns to our tab is **[UNVERIFIED]**. Test on the user's phone.
- **Credit line.** Show "ATC audio: LiveATC.net" linking to https://www.liveatc.net whenever the toggle is on.
- **Status.** Do not show LiveATC feed status; that would need automated access. Show "Feed status is shown on LiveATC" and the date of our mount list (23 Jun 2026).
- **"Tuned" state.** Picking a feed makes it the app's *tuned* feed even though the audio plays elsewhere. It drives the highlighting in §4.2. Remember the choice per device in `localStorage`, like the other `sfolive.*` settings in `app.js`.
- **Audio-delay slider (0–30 s, default 0).** The 3D and list then show traffic as of *now − delay*, which lines the visuals up with the audio.
  - LiveATC's delay is "typically less than 20 seconds" **[LATC-arch]**.
  - Our own ADS-B pipeline delay has not been measured here **[UNVERIFIED]**.
  - Offer a hint: "If you hear a clearance before the aircraft moves, increase the delay".
  - Without the slider the scene runs visibly *ahead* of the audio, which defeats the "real-time" goal.

### 4.2 "Likely on this frequency" highlighting

Each track gets an inferred ATC role from its `traffic.js` phase. Aircraft whose role matches the tuned feed get:
- a highlight ring;
- a frequency chip on the label, e.g. "TWR 120.5";
- an "On <feed> (N)" filter in the list.

Always word it as "likely".

| `tr.phase` (`traffic.js`) and extra condition | Inferred role | Frequency shown | Feeds that match |
|---|---|---|---|
| `gate` / `parked` at SFO, callsign present, departure expected (route origin SFO), not `stale` | Clearance (low confidence; many use PDC or CPDLC) | 118.2 **[FAA]** | `ksfo_gnd2` |
| `gate` / `parked`, otherwise | — (not on frequency) | — | — |
| `pushback`; `taxi` or `holding` inside apron (non-movement) polygons | Ramp **[INF: which ramp is unknown]** | LiveATC labels 127.575 / 119.225 / 131.0 **[UNVERIFIED]** | `ksfo_ramp` |
| `taxi`, or `holding` off-runway, on taxiways (movement area) | Ground | 121.8 (124.25 secondary) **[FAA]** | `ksfo_gnd`, `ksfo_gnd_twr`, `ksfo_twr2` (`ksfo_gnd2` carries 124.25) |
| `holding` on a runway (line up and wait), `takeoff`, `landing` while still on the runway | Tower | 120.5 **[FAA]** | `ksfo_twr`, `ksfo_gnd_twr`, `ksfo_twr2` |
| `landing` after the runway exit (`runwayAt` false) **[corrected by verifier]** This state cannot occur. In `traffic.js` (lines 261–265) `landing` is set only while `runwayAt()` is truthy and gs > 30 kt. After the exit, or once below 30 kt, the phase becomes `taxi` with `tr.landedAt` set. Use "`taxi` with `landedAt` recent" for this rule | Ground | 121.8 | as Ground |
| `final`, along-track distance to threshold ≤ about 6 nm (around the FAF; measure it per runway from the plates) | Tower **[INF handoff]** | 120.5 | Tower feeds |
| `final` beyond about 6 nm | Approach, final sector | 28R: 120.35 / 133.175; 28L: 135.65; other runways unknown. All **[LiveATC label only]**. Published: 134.5 **[FAA]** | `ksfo_app2_l`, `ksfo_app2` |
| `approach` (arrival not yet on final) | Approach feeder, chosen by entry direction **[INF]**: from the E → 128.325 (ALWYS/DYAMD/MODESTO/YOSEM); from the N or W → 133.95 (BDEGA/STLER/PIRAT/POINT REYES/STINS); from the S → 128.575 (BIG SUR/SERFR/WWAVS); RISTI → 134.5 | per STAR chart **[FAA]** | 128.325 and 133.95 → `ksfo_app2_r`, `ksfo_app2`. 128.575 and 134.5 → **no feed**: say so ("not covered by LiveATC") |
| `departure`, first ~1–2 min after `liftoffAt` or below ~2,500 ft **[INF]** | Tower, then Departure (show both) | 120.5 → 135.1 / 120.9 | Tower feeds and `koak_dep` |
| `departure` afterwards | Departure. Pick the sector from the route destination bearing: SE–W → 135.1, NW–E → 120.9. The bearings between those sectors are ambiguous: show both **[INF from the "(SE–W)/(NW–E)" labels]** | 135.1 / 120.9 **[FAA]** | `koak_dep` (L = SW, R = NE); `ksfo_dep2` / `ksfo_dep1` |
| `enroute`, `ground-other`, or `dirSFO === 'other'` (OAK/SJC traffic, overflights) | not SFO. Optionally Oakland Center | — | `zoa_sfo` (optional) |

Notes on the rules:
- **Departure sector.** Use the destination bearing, not the current track. The daytime snapshot (`data/snapshot.js`, 23 Sep 2026 10:51 PDT) has 5 climbing aircraft within 40 nm (from any airport). One was still near SFO on a 300° runway-heading track (UAL893, 2.8 nm, 1,650 ft). Two were on 128.6° and 132.2° tracks, just short of the SE–W sector's 135° start. So a track-based rule would misfile 3 of 5 **[observed in our data]**. Destinations come from the adsb.lol routeset already used by `feed.js` and `traffic.js` `routeDirection`.
- **Expected list sizes** **[INF, illustrative]**. I bucketed the same snapshot with crude thresholds, not the app's classifier:
  - ground: stationary if gs < 2 kt, taxiing if < 35 kt, else runway;
  - airborne: "tower" if < 6 nm and < 3,000 ft, otherwise climbing or descending by vertical rate beyond ±300 ft/min.

  Of 48 aircraft:
  - 25 stationary at gates or parked;
  - 8 taxiing (Ground/Ramp);
  - 3 on Tower (runway, short final or initial climb);
  - 5 descending (Approach);
  - 4 climbing (Departure);
  - 3 level or other.

  The lists are short enough to show every aircraft by name.
- **"Talking now" cannot be known.** The app has no access to the audio (and must not have any without permission), so it cannot show who is transmitting.
- **Tuned-frequency set.** Store the feed's frequency list with the mount, e.g. `{mount:'ksfo_twr', freqs:[{f:120.5, src:'faa-cs'}, {f:128.65, src:'liveatc-label'}]}`. Tag each frequency with its source so the `src: 'obs' | 'inf'` discipline of the stand data carries over.

### 4.3 Data maintenance

- Generate the FAA frequency table each cycle from NASR `FRQ.csv` (`SERVICED_FACILITY == 'SFO'`) and from the d-TPP comms strips (§1.2–1.3). The extraction code is in §6.
- Next dates:
  - NASR and d-TPP: 1 Oct 2026;
  - Chart Supplement: 29 Oct 2026.
- The LiveATC mount list must be refreshed by a human with a browser. The file would go in `data/`, which I did not touch as instructed. Suggested fields:

  `{mount, title, freqs[], src:'liveatc-archive-2026-06-23', verified:'2026-09-24 stream headers'}`

---------------------------------------------------------------------------------------------------------------------

## 5. Open questions (need the owner or a human with a browser)

1. **LiveATC permission.** Will LiveATC allow in-app `<audio>` playback, or at least confirm that linking to `hlisten.php` is fine? This needs the owner to send the §3.3 request.
2. **Current KSFO feed list.** Is the 23 Jun 2026 list (the latest capture) still current? Please open https://www.liveatc.net/search/?icao=ksfo in a browser and confirm the 16 mounts, their frequencies and their status. Several mounts could not be confirmed live today: `ksfo_app2_l`, `ksfo_app2`, `ksfo_app2_r`, `ksfo_gnd2`, `ksfo_atis`, `ksfo_dep2` and `zoa_35`.
3. **LiveATC-only frequencies.** Are 128.65 (tower secondary), 120.35 / 133.175 (28R final), 135.65 (28L final) and 127.975 (SW departures) real current NorCal or SFO frequencies? No FAA publication lists them for SFO. They could be confirmed by hearing a hand-off to them on LiveATC's archive.
4. **Frequency coverage gaps.** 128.575 (south arrivals: BIG SUR, SERFR, WWAVS) and 134.5 (the published approach frequency; RISTI) are on no LiveATC KSFO feed. Is that still true?
5. **"IC" in NASR.** What does "IC" mean in NASR `APCH/P IC` (134.5)? It is not defined in the NASR layout or the CS abbreviations.
6. **120.9 as approach.** Why does the Chart Supplement list 120.9 under NORCAL APP CON while NASR and AirNav list it only as departure / Class B?
7. **ATIS on the VORs.** Is the ATIS audible on 113.7 and 115.8, given the "VORW" (without voice) navaid entries and today's "SFO VOR OTS" ATIS remark? And does SFO split its D-ATIS into arrival and departure messages by day? (It was "combined" at 0656Z.)
8. **Stale DP rows in NASR.** NASR DP-frequency rows (SSTIK, TRUKN, WESLA and others) have no chart in d-TPP 2609. Are they stale? **[corrected by verifier]** SSTIK, TRUKN, WESLA and SNTNA *are* charted, on page 2 of the d-TPP 2609 SFO listing, and so is SEGUL. The rows still without a chart are DUMB, EUGEN, FOGGG, GAPP, LUVVE, OFFSHORE, PORTE, QUIET, REBAS, SEAGUL and SHORELINE.
9. **Ramp.** Where is the ramp / movement-area boundary at SFO, and which ramp-tower frequency applies to which apron? No official source was found. This is needed for the Ramp role.
10. **Handoff points.** Where exactly do the Approach → Tower and Tower → Departure handoffs happen at SFO? They are not published. The §4.2 thresholds are guesses to tune.
11. **Mobile audio.** On the user's phone (iOS or Android), does LiveATC's player keep playing in a background tab while our app is in front?
12. **Artifact links.** Does the Claude-artifact sandbox permit opening external links?
13. **Own receiver.** Would the owner consider their own airband receiver? Are they within radio range of SFO?

---------------------------------------------------------------------------------------------------------------------

## 6. Method, files and reproduction

All downloads are in `refs/cache/atc/` (gitignored by `.gitignore` `refs/`).

| File | What | Original URL |
|---|---|---|
| `CS_SW_20260903.pdf`, `sw_275_03SEP2026.pdf`, `cs_sfo_comms.png`, `sw_SFO_notices_03SEP2026.pdf` | Chart Supplement SW, 3 Sep – 29 Oct 2026; SFO pages; rendered comms block; SFO notices (noise only, no frequencies) | aeronav.faa.gov links in §1.1 |
| `nasr_FRQ_CSV_20260903.zip`, `nasr_ATC_CSV_20260903.zip`, `nasr_frq_sfo_20260903.csv`, `FRQ_DATA_LAYOUT.pdf`, `ATC_DATA_LAYOUT.pdf` | NASR 2026-09-03 | nfdc.faa.gov links in §1.2 |
| `dtpp2609/00375*.pdf` (45), `il28l_comms.png` | d-TPP 2609 charts for SFO. **[corrected by verifier]** These are 45 of 49. The other 4 (SNTNA, SSTIK, TRUKN, WESLA) are in `refs/cache/atc_verify/dtpp2609_extra/` | `https://aeronav.faa.gov/d-tpp/2609/…` |
| `airnav_ksfo.html/.txt` | AirNav KSFO | https://www.airnav.com/airport/KSFO |
| `wb_search_ksfo.html/.txt`, `liveatc_ksfo_feeds_20260623.json` | LiveATC KSFO page, capture of 23 Jun 2026, and its parsed feed table | §2.1 |
| `liveatc_legal_20260710.html/.txt`, `wb_faq.html`, `liveatc_faq_20260623.txt`, `wb_ksfo_twr.pls`, `wb_hlisten_ksfo_twr.html` | LiveATC terms, FAQ, playlist and player page (captures) | §2.1 |
| `mount_probe_20260924T074225Z.json`, `mount_probe_20260924T074333Z.json` | Stream-server HEAD results, 24 Sep 2026 | `http://d.liveatc.net/<mount>` → `https://s1-*.liveatc.net/<mount>` |
| `wb_bcfy_terms.html`, `broadcastify_terms_20260910.txt`, `wb_bcfy_3561.html` | Broadcastify terms (Last Updated July 22, 2026) and the feed 3561 capture | §3.3 |
| `usc18_2511_house.html`, `usc47_605_house.html` | US Code text | uscode.house.gov links in §3.3 |
| `datis_ksfo.json` | Third-party D-ATIS text, 24 Sep 0656Z | https://atis.info/api/KSFO |

To extract the SFO frequencies from NASR (for the per-cycle table in §4.3):

```python
import zipfile, csv, io
z = zipfile.ZipFile('refs/cache/atc/nasr_FRQ_CSV_20260903.zip')
rows = [r for r in csv.DictReader(io.TextIOWrapper(z.open('FRQ.csv'), encoding='latin-1')) if r['SERVICED_FACILITY'] == 'SFO']
for r in rows: print(r['FACILITY'], r['FREQ'], r['FREQ_USE'], r['SECTORIZATION'])
```

PDF text was read with `pypdf` / `pymupdf`, installed into the session scratchpad only.

Tools not available here: the liveatc.net website (Cloudflare challenge for curl and WebFetch), m.liveatc.net (no DNS), broadcastify.com (403), Common Crawl (proxy tunnel failures), and archive.ph (connection reset).

---------------------------------------------------------------------------------------------------------------------

## Verification (adversarial check)

This check was done on 24 Sep 2026, 08:20–08:55 UTC, by an independent verifier agent. Every FAA, AirNav, Internet Archive, Broadcastify and US Code source cited above was fetched again from its original URL. The re-fetched FAA files are **byte-identical** to the cached copies in `refs/cache/atc/`: `sw_275_03SEP2026.pdf`, the SFO notices, the NASR `FRQ`/`ATC` CSV zips and all 45 `dtpp2609/00375*.pdf`. The Wayback captures of the KSFO page, the terms, the FAQ and `hlisten.php` are also byte-identical after gunzip. The full CS volume matched by `Content-Length` (49,209,653 B) and was read from the cache.

The verifier **did not** contact liveatc.net or its stream servers. Clauses 3.5 and 3.13 of the terms, and this report's own §4 rule, forbid automated access. So every **[LATC-live]** claim was checked only against the probe files the author saved, `mount_probe_*.json`. New downloads are in `refs/cache/atc_verify/`, which is gitignored.

| # | Claim (section) | Verdict | Evidence |
|---|---|---|---|
| 1 | CS SW edition "Effective 0901Z 3 SEP 2026 to 0901Z 29 OCT 2026". SFO is on printed p.275–276. The next edition is 29 Oct (§1.1) | confirmed | Cover of `CS_SW_20260903.pdf`. The d-CS page lists "CS SW Sep 03 2026 / Oct 29 2026", and the d-CS search returns `sw_275_03SEP2026.pdf` ("0901Z Sep 03 - 0901Z Oct 29, 2026"). |
| 2 | COMMUNICATIONS block text (D–ATIS 118.85 115.8 113.7 … NORCAL APP CON 120.9 128.325 134.5 133.95 … TOWER 120.5 GND CON 121.8 124.25 CLNC DEL 118.2 PRE TAXI CLNC 118.2 … NORCAL DEP CON 135.1 (SE–W) 120.9 (NW–E), CPDLC (LOGON KUSA), PDC) | confirmed | Text layer of the re-fetched page 275 matches word for word. `cs_sfo_comms.png` was also viewed. |
| 3 | CS header coordinates and remarks (gates 88/89, F11, F20/F21, "ASSC in use … ADS–B … enabled on all airport surfaces") | confirmed | Same page. NASR `ATC_RMK.csv` carries the same remarks. |
| 4 | "(VL) (L) VORW/DME 115.8 SFO" on p.276; PYE "(VH) (DH) VORW/DME 113.7" on p.247; legend "W … Without voice on radio facility frequency" on PDF p.30 | confirmed | p.276 of `sw_275`. Printed p.247 is PDF index 248 of the volume. The legend on PDF p.30 is font-shifted (glyph +29) and decodes to "W=… Without voice on radio facility frequency." |
| 5 | NASR 2026-09-03 has 106 rows with `SERVICED_FACILITY = SFO`, all `EFF_DATE 2026/09/03`, with the uses and sectors in the §1.2 table | confirmed | Re-downloaded `03_Sep_2026_FRQ_CSV.zip` and re-ran the §6 snippet: 106 rows, the same uses, and UHF 254.25/310.8 (APCH/P) and 251.05 (APCH/S). The NASR index page shows "Current … September 03, 2026" and "Preview … October 01, 2026". |
| 6 | NASR lists 120.9 only as DEP/P NW-E, CLASS B NW and DPs, never as approach | confirmed | NASR rows. AirNav (re-fetched 08:48Z) "NORCAL APPROACH: 128.325 134.5 133.95". |
| 7 | `ATC_BASE`: TWR_HRS 24, TWR_CALL SAN FRANCISCO, NORCAL, NCT/NCT. `ATC_ATIS`: one D-ATIS, 24 h. Phone numbers are in `ATC_RMK` | confirmed | Re-downloaded `03_Sep_2026_ATC_CSV.zip`. |
| 8 | "IC" in `APCH/P IC` is not defined in the NASR layout or the CS abbreviations | confirmed (meaning still unverified) | `FRQ DATA LAYOUT.pdf`, `CSV_README.pdf` and the CS front matter (decoded) have no "IC" entry. NASR uses it 562 times (`APCH/P DEP/P IC` 423, `APCH/P IC` 100, `LCL/P IC` 25, …). A web search suggests "initial contact", but no FAA source was found, so the [UNVERIFIED] tag stays. |
| 9 | Class B sector frequencies 120.9 NW, 125.35 NE-E, 127.0 NORTH, 133.95 SOUTH, 134.5 EAST, 135.1 WEST | confirmed | NASR rows. AirNav "CLASS B:" line. |
| 10 | All 22 SFO IAPs (6 ILS, 4 GLS, 8 RNAV (GPS), 2 RNAV (RNP), 2 visuals) carry D-ATIS 113.7 115.8 118.85, NORCAL APP CON 134.5 338.2, TOWER 120.5 269.1 and GND CON 121.8. Footers read "SW-2, 03 SEP 2026 to 01 OCT 2026" | confirmed | Text of each re-fetched plate. The count of 22 matches the d-TPP listing (IAP rows). |
| 11 | Airport diagram strip | confirmed | `00375ad.pdf`: "PDC CPDLC 118.2 CLNC DEL 121.8 GND CON 120.5 269.1 SAN FRANCISCO TOWER 113.7 115.8 118.85 D-ATIS". The chart also prints PDC. |
| 12 | STAR table: NORCAL APP CON 128.325 (ALWYS/DYAMD/MODESTO/YOSEM), 133.95 (BDEGA/STLER/PIRAT/POINT REYES/STINS), 128.575 (BIG SUR/SERFR/WWAVS), 134.5 (RISTI). Oakland Center frequencies as listed. UHF pairs 254.3 and 317.6 | confirmed | Text of the 14 STAR PDFs, for example SERFR "128.575 254.25 NORCAL APP CON 134.55 290.5 OAKLAND CENTER". NASR per-STAR rows agree. The "from the east/north/south" grouping is the author's gloss; the verifier checked it only loosely against the transition names **[INF]**. |
| 13 | "I downloaded all 45 SFO charts" (§1.3, §1.5, §6) | **refuted** | The d-TPP 2609 SFO search has **54 results on 2 pages**. Page 2 lists SNTNA TWO, SSTIK FIVE, TRUKN TWO and WESLA FIVE (all RNAV DPs), so there are **49** `00375*.pdf` charts. Their DEP CON frequencies are 120.9, 135.1, 120.9 and 135.1, which match NASR. Corrected inline in §1.3, §1.5, §5 and §6. |
| 14 | The DP frequencies that were listed (CIITY/NIITE/SAN FRANCISCO 120.9; GNNRR/MOLEN/SAHEY/SEGUL 135.1; GAP "135.1 307.2 (SE-W) 120.9 323.2 (NW-E)") | confirmed | Chart text. |
| 15 | NASR DP rows "not charted under SFO or OAK": the list included SEGUL, SNTNA, SSTIK, TRUKN and WESLA | **refuted** (for those 5) | SEGUL ONE is on page 1 of the SFO listing and the other four are on page 2. The OAK 2609 listing (48 results, one page) has none of the 16 names. Corrected inline. |
| 16 | AirNav quotes (§1.4) | confirmed | https://www.airnav.com/airport/KSFO re-fetched 08:48Z: "FAA INFORMATION EFFECTIVE 03 SEPTEMBER 2026". Every quoted line, including "IC: 134.5", "GAP DP 120.9 ;NW-E" and "GAPP DP 135.1 ;SE-W", is present. |
| 17 | 128.65 (CA: only NTD), 120.35 (CA: only LAX CD/P), 133.175 (no CA rows), 127.975 (no CA rows); ramp 127.575/119.225 (no CA rows) and 131.0 (in no row at all); none on any SFO chart or the CS page | confirmed | Full `FRQ.csv` search, plus a text search of all 49 charts and CS p.275–276. |
| 18 | 135.65 is in NASR "for SQL (San Carlos) only" | **refuted** (minor) | NASR California also has `LAX D-ATIS DEP 135.65`. It is still not published for SFO. Corrected inline. |
| 19 | The Wayback KSFO capture of 23 Jun 2026 20:32:22 is the latest | confirmed | CDX for `www.liveatc.net/search/?icao=ksfo`, including its `KSFO` and non-www variants: the latest capture is 20260623203222. The captures in 2025 and 2026 run from 2025-01-16 to 2026-01-01 and then 2026-06-23, which matches the report. (There are older captures back to 2024.) |
| 20 | 16 mounts, with the titles, frequencies, labels, "UP" status and listener counts in §2.2 | confirmed | The `id_` capture, gunzipped, is byte-identical to `wb_search_ksfo.html`. The 16 `myHTML5Popup('<mount>','ksfo')` calls map in page order to the 16 titles, and the frequency tables match §2.2 exactly, including the koak_dep left/right note. |
| 21 | Stale LiveATC labels (BSR2, MOD2) against the current BIG SUR THREE (128.575) and MODESTO NINE (128.325) | confirmed | Archived labels compared with the 2609 STAR charts. |
| 22 | 134.5 and 128.575 are carried by no KSFO feed | confirmed (per the 23 Jun labels only) | Neither frequency is in any of the 16 frequency tables. What the feeds actually carry is **[UNVERIFIED]**. |
| 23 | Terms quotes: summary items 2, 3, 4 and 10; clauses 2.1 (including the "Grante" typo), 3.3, 3.4, 3.13, 3.15, 4 and 13.5; "(EFFECTIVE AS OF FEBRUARY 1, 2009)"; "Last Modified: February 1, 2009"; footer | confirmed (verbatim) | All 18 quoted strings appear verbatim in the 10 Jul 2026 capture, which the CDX shows is the latest (earlier: 28 May, 29 Jun). Clause numbering was checked. |
| 24 | Row "Record the audio … No (3.13; the footer)" (§3.2) | confirmed, with a nuance | Clause **3.2** bars copying or storing tracks "without giving credit", so it permits credited copying, and the Agreement does not flatly ban recording. The "Never" verdict for our *server-side* recording still holds on 3.13 (automated retrieval), 3.3 and the footer. Clause 3.9 ("training and entertainment purposes only") is also relevant and was not cited. |
| 25 | Footer on the legal, FAQ and KSFO pages | confirmed | Present once in each of the three captures. |
| 26 | FAQ quotes (latency "typically less than 20 seconds"; "may show as 'Up' but have no audio") | confirmed (punctuation nit) | 23 Jun 2026 capture. The original has a line break, not a period, after "listener", and uses double quotes around "Up". |
| 27 | `X-Frame-Options: SAMEORIGIN` on `hlisten.php` (11 Dec 2025) and on the KSFO page (23 Jun 2026) | confirmed (archived) / unverifiable (live) | `x-archive-orig-x-frame-options: SAMEORIGIN` on both captures, and also on the legal and FAQ captures. The current live headers could not be read. |
| 28 | `hlisten.php` uses `<audio id="player2" crossorigin="anonymous" … src="https://s1-bos.liveatc.net/ksfo_twr?nocache=…">`, MediaElement.js, Google Publisher Tags, a peak meter and "If stream doesn't start automatically press the play button". The `.pls` has `File1=http://d.liveatc.net/ksfo_twr` | confirmed | The captures (byte-identical to the cache) contain `mediaelement-and-player.min.js`, `gpt.js`/`googletag`, `AudioContext`/`PeakMeter`, and the exact `<audio>` tag and `.pls` lines. |
| 29 | "Nine mounts answered live … with their names" (§0, §2.1) | unverifiable (8 of 9 supported) | The saved probe files show 200 with `icy-name` for 8 mounts: ksfo_gnd, ksfo_gnd_twr, ksfo_twr2, ksfo_dep1, koak_dep, ksfo_co, ksfo_ramp and zoa_sfo. For **ksfo_twr**, both saved attempts (07:41:38, 07:42:40) were proxy resets. The quoted "200, KSFO Tower, 16 kbit/s, 22.05 kHz (07:40:57)" is not in any saved file. It was not re-probed (terms 3.13). |
| 30 | §2.4 stream headers: `ice-audio-info … bitrate=16 (ksfo_twr)`, `access-control-allow-methods: GET, OPTIONS, SOURCE, PUT, HEAD, STATS`, `cache-control: no-cache, no-store` | unverifiable | The saved probes record `content-type: audio/mpeg`, `access-control-allow-origin: *` and `server: LiveATC` (confirmed). `ice-audio-info channels=1;samplerate=22050;bitrate=16` appears for ksfo_gnd, ksfo_co and ksfo_ramp, not ksfo_twr. `probe_mounts.py` did not save allow-methods or cache-control. |
| 31 | Redirector returns 302 even for fake mounts; fake mounts, `kn_se`, `ksfo_app`, `ksfo_dep` and `ksfo_del` return 404; `status-json.xsl` returns 403 "Request forbidden by administrative rules" | confirmed (saved evidence) | `mount_probe_*.json` (zzzz_fake1 and ksfo_fake2 have a redirect and then 404) and `s1-bos_status.json`. |
| 32 | `m.liveatc.net` does not resolve | confirmed | `dns.google/resolve?name=m.liveatc.net` returns `"Status":3` (NXDOMAIN, SOA liveatc.net on Cloudflare). www and d resolve to Cloudflare IPs. |
| 33 | liveatc.net is behind a Cloudflare challenge; the proxy logged the resets as `ws_closed_mid_exchange` | unverifiable | Deliberately not re-tested (terms 3.13). The proxy's `recentRelayFailures` buffer now starts at 07:44:40Z, after the 07:41–07:43 probes, and shows only web.archive.org and index.commoncrawl.org entries. |
| 34 | Search-index titles (`ksfo_app2_l` = "KSFO NORCAL App 28L/R", `kn_se` = "SFO Fleet Week") and `/ct/contact.php` | confirmed **[3P]** | WebSearch result titles, for example "Listening to: SFO Fleet Week … LiveATC.net" at `hlisten.php?mount=kn_se&icao=ksfo` and "Contact LiveATC.net" at `/ct/contact.php`. |
| 35 | Broadcastify terms: "Last Updated: July 22, 2026"; §9 "…regardless of who is performing it, the scale involved, or the stated purpose"; item (d) verbatim; "A use does not become permitted because it is limited in scale, unpaid, or characterized as personal, hobby, …"; bcfy.io | confirmed | Re-fetched https://web.archive.org/web/20260910062306id_/https://www.broadcastify.com/terms/, the latest capture per CDX (earlier: 8 Sep, 19 Aug, 8 Aug). The section heading reads "9. PROGRAMMATIC ACCESS, AUTOMATED USE, AND COMMERCIAL LICENSING". |
| 36 | Broadcastify feed 3561 showed "Invalid Feed ID" (capture of 15 Aug 2025) | confirmed | CDX 20250815153801 (200) and the cached capture. Its status today is unverifiable. |
| 37 | 18 U.S.C. §2511(2)(g)(ii)(IV) and 47 U.S.C. §605(a) quotes | confirmed | uscode.house.gov re-fetched. The only difference is that the site renders "person-" / "transmitted-" with a hyphen where the report has an em dash. |
| 38 | Third-party D-ATIS "INFO K 0656Z … combined … SFO DME OTS, SFO VOR OTS"; datis.clowd.io redirects to atis.info | confirmed **[3P]** | Cached JSON. A live re-fetch at 08:48Z returned "INFO M 0756Z", type `combined`, with "ILS RWY 28R OTS, SFO DME OTS, SFO VOR OTS". `datis.clowd.io/api/KSFO` returns 302 to `atis.info/api/KSFO`. |
| 39 | Snapshot buckets: 48 aircraft = 25 stationary, 8 taxiing, 3 Tower, 5 descending, 4 climbing, 3 level/other. 5 climbing within 40 nm. UAL893 at 2.8 nm, 1,650 ft, 300°. Tracks 128.6° and 132.2° | confirmed | Re-ran the author's `bucket.py` and an independent WGS-84 geodesic recomputation: UAL893 2.8 nm / 1650 ft / 300.04°, UAL1164 128.59°, SKW249R 132.17°. |
| 40 | "a track-based rule would misfile 3 of 5" | unverifiable (inference) | The count depends on the author's assumption that "SE–W" begins at exactly 135°; a compass SE octant starts at 112.5°. It also depends on destinations, which the report does not give, and the aircraft are "from any airport". |
| 41 | "Feed titles change … `ksfo_dep1` … announced 'NORCAL Dep (NE)'" | unverifiable | `icy-name` is set by the feeder's source client. It is a different field from the web page title, so the evidence shows the two *differ*, not that either *changed*. Keying on the mount name is still the right recommendation. |
| 42 | "127.0 … explains why 127.0 appears in LiveATC's Dep feeds" (Class B NORTH) | partially refuted (incomplete) | NASR also has OAK `CLASS C NORTH 127.0` and OAK `NIMITZ DP 127.0`, which fit the joint KSFO/KOAK departure feed. Corrected inline in §1.2 and §2.3. |
| 43 | §4.2 row "`landing` after the runway exit (`runwayAt` false) → Ground" | **refuted** | `js/live/traffic.js` lines 261–265 set `landing` only when `runwayAt()` is truthy and gs > 30 kt; otherwise a moving aircraft is `taxi` or `pushback`. Corrected inline: use `taxi` with a recent `landedAt`. |
| 44 | The code identifiers the design relies on (`traffic.js` phases, `stale`, `liftoffAt`, `dirSFO`, `routeDirection`; the `sfolive.*` localStorage store in `app.js`; Settings and About buttons in `ui.js`) | confirmed | grep of `js/live/`, which was not modified. |
| 45 | Handoff P2 #9 mounts `ksfo_twr`, `ksfo_gnd`, `ksfo_app2_l`, `koak_dep`, `ksfo_gnd_twr` | confirmed | `docs/HANDOFF.md` line 170, checked against the archived feed list. |
| 46 | Next cycles: NASR and d-TPP on 1 Oct 2026, CS on 29 Oct 2026 | confirmed | NASR index ("Preview … October 01, 2026"), the d-TPP page ("Oct 01 2026–Oct 29 2026") and the d-CS page. |
| 47 | Our ADS-B pipeline delay "has not been measured" (§4.1) | now measured (supports the delay slider) | Recorder data `refs/cache/rec/*` (07:28–08:50 UTC, 24 Sep). adsb.fi: receive time minus server `now` has p50 0.80 s and p90 1.66 s; `seen_pos` has p50 1.2 s and p90 4.7 s. adsb.lol: receive minus `now` ≈ 0 s (p50 −0.08 s, so the clocks are near-synchronous); `seen_pos` p50 1.1 s. Positions are therefore about 1–3 s old at receipt, against LiveATC's "typically less than 20 seconds", so the visuals *do* lead the audio. This excludes the app's own interpolation lag **[observed; app-side lag not measured]**. |
| 48 | Recommendation: link out to `hlisten.php`, credit LiveATC, and never embed, proxy, record or probe without permission (§0.4, §3.2) | confirmed as a reading of the terms (not legal advice) | It rests on claims 23–28, which are all confirmed. 3.15 restricts only links "directly to any of the audio streams"; `hlisten.php` is a LiveATC web page with its ads. The in-app `<audio>` "No" follows from 3.15 and the footer. |

**Summary.** No frequency, terms quote, licence quote or mount name was refuted. The FAA frequency set, the LiveATC feed list and the terms quotes all hold against the original sources. Refuted, and corrected inline:
- the chart count (45 → 49): four SFO DPs on page 2 of the d-TPP listing were missed;
- the "not charted" NASR DP list: SEGUL, SNTNA, SSTIK, TRUKN and WESLA are charted;
- "135.65 … SQL only";
- the dead `landing`-after-exit rule.

Not verifiable without contacting LiveATC, which the verifier deliberately avoided:
- the ksfo_twr live probe (so "nine" live mounts is supported only for eight);
- three of the §2.4 stream headers;
- the Cloudflare behaviour;
- current, as opposed to archived, headers and terms.
