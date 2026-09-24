# Weather for SFO Live 3D: METAR/TAF decoding, physically based rendering parameters, SFO climatology and live sources

Research for the owner's request for "lighting, day/night support, weather support". This document covers the
**weather** part. It explains how to decode every METAR group that changes what the scene should look like, how
to turn each decoded value into a rendering parameter with a physical justification, what SFO weather is really like,
and where live data can come from and under which terms. Nothing in `js/` or `data/` was changed.

Written 24 Sep 2026 (UTC) by a research agent. Tools: `tools/env/metar_decode.py` (decoder and METAR-to-render mapping),
`tools/env/test_metar_decode.py` (38 unit tests on 58 real KSFO reports), and `tools/env/ksfo_climatology.py`
(10-year statistics). Downloads are in `refs/cache/weather/` (gitignored).

**Tags.**
- **[V]** verified: read in a source I fetched, quoted, URL given.
- **[M]** measured: computed by our tools from real data.
- **[I]** inferred: my modelling choice or interpretation. Open to correction.
- **[2nd]** secondary: the original could not be fetched, so this comes from a source that cites it.
- **[NV]** not verified.

---------------------------------------------------------------------------------------------------------------------

## 1. Answer in brief

1. **The live app's METAR parser misreads fractional visibility.** Do not build weather rendering on it. `js/livedata.js`
   `parseMetar` matches `/\b(\d{1,2})SM\b/`, so the regex finds the digits after the slash **[M, run with node]**:
   - `M1/4SM` (fog, less than ¼ mile) is read as **4 SM**;
   - `1 1/4SM` is read as **4 SM**;
   - `1/2SM` is read as **2 SM**.

   It also ignores `VV` (vertical visibility), so an indefinite ceiling reads as no cloud. Other groups are dropped:
   gusts, RVR, present weather, all remarks. The fog in `js/live/app.js` also has two caps:
   - density is capped at 0.004 m⁻¹ (visibility is floored at 800 m);
   - `T ≥ 1 − 0.97` keeps at least 3 % of the scene visible at any distance.

   So even a correct `M1/4SM` could not render as fog. `tools/env/metar_decode.py` is the reference replacement. It passes all
   38 tests (section 2.8). It also decoded all 107,075 rows of the two IEM KSFO downloads (2016–2025 and Sep 2025–Sep
   2026, which overlap) with no leftover tokens except malformed rows in the archive.
2. **Live mode cannot fetch METARs from the browser.** The aviationweather.gov Data API page says **[V]**:
   "Cross-origin resource sharing is not permitted at this time." Its response carries no `Access-Control-Allow-Origin`
   header **[M]**. `js/live/feed.js` `fetchMetar()` falls back to that URL when there is no relay, so that call can
   never succeed in a browser. The relay's `/api/metar` is required. api.weather.gov and atis.info do send
   `access-control-allow-origin: *` **[M]**.
3. **Visibility → extinction must use the ASOS algorithm, and it is different by day and by night.** KSFO's
   visibility comes from ASOS. The NWS ASOS algorithm uses Koschmieder's law with contrast threshold **ε = 0.055** by
   day, and a simplified Allard's law (25 cd light, CDB = 0.084 mi⁻¹) at night. Rasmussen et al. 1999 **[V]** and the
   ASOS User's Guide **[V]**: "the day calculation will provide a visibility from 1/2 to 1/3 of that derived by the night
   equation". So σ_day = 2.90 / V, and at night the same reported V means **1.2–2.4 times more extinction** from 10 SM down to
   ¼ SM, and 2.7 times at ⅛ SM (table in 3.1).
   Koschmieder's own ε = 0.02 (3.912 / V, what the app uses now) and the WMO MOR 5 % (2.996 / V) are **not** what KSFO
   reports. "10SM" is a lower bound only ("10 miles or greater", ASOS guide **[V]**).
4. **Cloud amounts are cumulative.** Under FAA Order JO 7900.5E §10.7, BKN/OVC/SCT/FEW is "the summation amount of sky cover
   for any given layer", covering that layer and every layer below it **[V]**. The app currently treats each layer's
   amount as independent coverage. It also renders only the lowest non-FEW layer. The decoder converts the amounts to
   per-layer coverage (section 3.4).
5. **SFO's weather is mostly marine stratus, not fog.** This comes from 87,533 routine METARs, 2016–2025 **[M]**.
   - Ceilings below 2,500 ft, or visibility below 5 SM, occur in 19–24 % of hours from May to September. They peak at
     04–08 local time: 38–52 % of hours in Jul–Aug. They fall to about 5 % from 13:00 to 16:00.
   - Summer low ceilings have a median of 1,100 ft (p10 700 ft, p90 1,900 ft).
   - On summer mornings that are low at 07:56, the stratus lifts or clears by a median of **10:56 local** (IQR 09:56–11:56).
   - True fog (FG, visibility below ⅝ SM) is rare: at most 0.6 % of hours, in Dec/Jan. It occurs at 02–10 local and peaks at 05–08.
   - Rain falls in 8–9 % of hours from Dec to Mar, and in ~0.1 % in Jun–Aug.
   - Thunder is almost absent.

   This matches the FAA/MIT Lincoln Laboratory account: stratus "forms in the San Francisco Bay area overnight and
   dissipates during the middle to late morning", May–September **[V]**.
6. **The runway configuration cannot be derived from the METAR alone.** SFO says the West Plan (arrive 28L/R, depart
   1L/R) is used "95-98% of the time" and the Southeast Plan "less than 5%" **[V]**. Our wind data agree: a tailwind
   of 5 kt or more on runway 28 occurs in 5.5 % of hours **[M]**. But the approach type depends on more than weather:
   - Quiet Bridge / Tipp Toe visual approaches require "SFO 2500'/5" **[V]**, but the traffic time of day also matters;
   - a construction closure matters: the D-ATIS says "RY 1L, 1R CLSD" **[M]**, and SFO's travel alert says "The runway
     is expected to reopen in early October 2026" **[V]**.

   The D-ATIS of 23–24 Sep shows the whole cycle in VFR weather: ILS 28R/28L single-stream at night, then Quiet Bridge
   only, then simultaneous visuals from 06:56 PDT **[M]**. Take the runway configuration from the D-ATIS text or from the
   observed ADS-B flow, not from the wind.
7. **The ATIS wind is magnetic; the METAR wind is true.** In the 24 D-ATIS broadcasts of 23–24 Sep, all 22 with a
   non-calm wind in both reports show the ATIS direction as the METAR direction minus 10°, at the same speed (e.g.
   METAR `03006KT` ↔ ATIS `02006KT`) **[M]**. The other two: 07:56Z was calm in both; at 08:56Z the ATIS said `00000KT`
   where the METAR had `28003KT`. The 10° offset is consistent with the 14° E variation (AirNav) rounded to 10°. JO
   7900.5E §13.10 says the METAR direction is "true" **[V]**. The windsock and cloud drift must use the **METAR** wind.
8. **Sources and terms.**

   | Source | Terms and access |
   |---|---|
   | aviationweather.gov | NWS public domain. 100 requests/min, at most 400 entries per request. A custom User-Agent is asked for. Responses carry `cache-control: max-age=60` **[V/M]**. KSFO METARs reach the API 4.1–4.4 min after observation (p10–p90). **[corrected by verifier]** About 8 % of routine METARs arrived 6.6–28.6 min late, and one SPECI 89 min late (see 5.1). |
   | api.weather.gov | Public domain; "User Agent is required". The rate limit is not public. Also serves 5-minute unaugmented ASOS data **[V/M]**. |
   | atis.info D-ATIS | **No terms, licence or rate limit are published anywhere on the site.** Its only statement is "Do not use for real world flight planning or navigation." **[V]** It stays third-party/optional. |
   | IEM ASOS archive | Public domain, attribution appreciated **[V]**. Rate-limited in practice: it returned "Too many requests from your IP address" to a second quick query **[M]**. |

---------------------------------------------------------------------------------------------------------------------

## 2. Decoding (task a)

### 2.1 Standards used (all fetched)

| Source | Version | Role |
|---|---|---|
| FAA Order **JO 7900.5E** "Surface Weather Observing", with Change 1, https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf | Issued 2020-01-15; Chg 1 dated 7/1/2021. The FAA order registry says "Status Active" and that it cancels JO 7900.5D. | **Primary coding standard** for FAA and FAA-contract observers. KSFO reports are ASOS (AO2) with human augmentation. |
| **FMH-1** (Federal Meteorological Handbook No. 1) | The 2019 edition's official URL (https://www.icams-portal.gov/resources/ofcm/fmh/FMH1/fmh1_2019.pdf) returns `InvalidObjectState … DEEP_ARCHIVE` (AWS S3 cold storage). web.archive.org is blocked by the egress proxy. Only **FCM-H1-2005** (mirror at met.nps.edu) could be read. | Cross-reference only. JO 7900.5E is newer and agrees on every group used here **[NV for the 2019 text]**. |
| **AIM** (Aeronautical Information Manual) 7-1-7, 7-1-13…17, 7-1-28, 7-1-29, https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html | "Effective: 7/9/2026, Change 3" (AIM index page) | Pilot-facing key; flight categories; RVR. |
| aviationweather.gov Data API, https://aviationweather.gov/data/api/ and OpenAPI https://aviationweather.gov/data/schema/openapi.yaml | Page footer "v4.31"; OpenAPI `version: "v4.0"` | Endpoints, formats, limits (section 5.1). |

### 2.2 Body groups that matter for visuals

Every row below is quoted from JO 7900.5E chapter 13 **[V]**. The last column says what the renderer does with it.

| Group | Coding rule (JO 7900.5E) | Rendering use |
|---|---|---|
| Type / modifier | `METAR`/`SPECI`; "AUTO … fully automated report with no human intervention"; "COR must be entered … when a corrected METAR or SPECI is transmitted" (13.6, 13.9) | SPECI = a significant change; apply it immediately. KSFO reports carry no `AUTO` (only 21 of 96,367 reports in 2016–2025 had it) **[M]**, so observers augment them. |
| Wind `dddff(f)Gfmfm(fm)KT dndndnVdxdxdx` | "The true direction, ddd, from which the wind is blowing is coded in tens of degrees". Gusts `G`. "VRB … whenever the wind speed is 6 knots or less". Variable direction with more than 6 kt: `21010KT 180V240`, coded clockwise. "Calm wind is coded as 00000KT." (13.10) | Windsock, flags, water waves, cloud drift direction (section 3.7). **True north.** |
| Visibility `VVVVVSM` | "A space is coded between whole numbers and fractions … Only automated stations may use an 'M' to indicate 'less than'" (13.11). Automated values, Table 13-3: M1/4, 1/4, 1/2, 3/4, 1, 1 1/4, 1 1/2, 1 3/4, 2, 2 1/2, 3, 4 … 10. Manual values add 1/16…7/8 steps and 11–35. | Extinction coefficient (section 3.1). `P6SM` appears in TAFs ("above 6 miles in TAF Plus6SM", AIM 7-1-28 **[V]**). |
| RVR `RDRDR/VRVRVRVRFT`, `…VnVnVnVnVVxVxVxVxFT` | "increments of 100 feet up to 1,000 feet, … 200 feet from 1,000 … to 3,000 feet and … 500 feet from 3,000 feet to 6,000 feet … If the RVR is less than its lowest reportable value … preceded by M … greater than its highest … P" (13.12). Long-line RVR "is the highest RVR achievable for the measured visibility at the touchdown zone … at runway light intensity step five" (8.2j). AIM 7-1-13: RVR is reported "when the prevailing visibility is less than one mile and/or the RVR is 6,000 feet or less". | Optional: how far runway edge lights stay visible along 28R. **KSFO reports RVR for 28R only**: 1,079 reports in 2016–2025, no other runway **[M]**. |
| Present weather `w'w'` | Table 13-4 columns: intensity or proximity (`-`, none, `+`, `VC`), descriptor (MI PR BC DR BL SH TS FZ), precipitation (DZ RA SN SG IC PL GR GS UP), obscuration (BR FG FU VA DU SA HZ PY), other (PO SQ FC SS DS). At most three groups (13.13). | Precipitation particles, fog and mist layers, haze/smoke tint, lightning (sections 3.3–3.8). |
| Sky `NsNsNshshshs`, `VVhshshs`, `CLR`, `SKC` | Table 13-5: FEW ">0 - 2/8", SCT "3/8 - 4/8", BKN "5/8 - 7/8", OVC "8/8", VV = 8/8. Heights "in hundreds of feet above the surface". Height increments (Table 13-6): nearest 100 ft up to 5,000; nearest 500 ft up to 10,000; nearest 1,000 ft above. "CLR … no clouds are detected at or below 12,000 feet" (automated). "Automated sky condition sensors may truncate … to 3 layers … No more than 6 layers" (13.14). CB/TCU appended. | Cloud layers, sun occlusion, diffuse light (section 3.4). |
| Temperature/dew point `T'T'/T'dT'd` | Whole °C, `M` for below zero (13.15). | Humidity (haze growth, window fogging); T-group gives tenths. |
| Altimeter `APHPHPHPH` | Inches of mercury × 100 (13.16). | Already used as QNH for barometric altitude (`docs/research/realtime_feeds.md` 4.6). |

**Definitions that decide fog vs mist vs haze [V]** (JO 7900.5E 9.3 and 13.13e; AIM 7-1-15):
- **FG**: "reduces horizontal visibility to less than 5/8 SM".
- **BR** (mist): "reduces visibility to less than 7 SM, but greater than or equal to 5/8 SM".
- **MIFG** (shallow fog): "visibility at 6 feet above the ground is 5/8 SM or more and the apparent visibility in the fog layer is less than 5/8 SM".
- **BCFG** (patches) and **PRFG** (partial): "may be reported when visibility is equal to or greater than 7 miles".
- **VC**: "between 5 and 10 SM" for everything but precipitation, "up to 10 SM" for precipitation.
- HZ and FU are "reported only when the prevailing visibility is restricted to less than 7 statute miles".
- Squall **SQ**: "wind speed increases by at least 16 knots and is sustained at 22 knots or more for at least 1 minute" (9.4b).
- Drizzle: "fine drops … (diameter less than 0.02 inch/0.5 mm) very close together"; rain drops are larger (9.2).

### 2.3 Remarks that matter for visuals (JO 7900.5E 13.17–13.58) [V]

| Remark | Format and meaning | Rendering use |
|---|---|---|
| `AO2` | "automated stations with a precipitation discriminator" (13.21) | — |
| `PK WND dddff(f)/(hh)mm` | Peak wind since the last METAR (13.22) | Gust envelope for windsock and flags. |
| `WSHFT (hh)mm [FROPA]` | Wind shift, frontal passage (13.23) | Front passing: switch the cloud deck and rain. |
| `TWR VIS v` / `SFC VIS v` | Tower or surface visibility. When both are observed, "the lower value (if less than 4 miles) must be reported as prevailing visibility in the body … the other value must be a remark" (8.3, 13.24) | Height-dependent fog. Tower visibility above surface visibility means a shallow fog layer (e.g. KSFO 13 Nov 2016: `1/2SM … BCFG VV002 … TWR VIS 6` **[M]**). |
| `VIS vnVvx` | Variable prevailing visibility (13.25) | Animate the fog density between the two values. |
| `VIS [DIR] v` | Sector visibility (13.26) | Directional fog bank (e.g. `VIS NW 1/2` with 10SM prevailing). |
| `VIS v [LOC]` | Second visibility sensor (13.27) | — |
| `CIG hnVhx` | "Variable Ceiling Height … CIG 005V010". Required when a ceiling below 3,000 ft varies by the Table 10-5 amounts: at least 200 ft for ceilings of 1,000 ft or less, 400 ft up to 2,000 ft, 500 ft up to 3,000 ft (10.17, 13.34) | Ragged stratus base. |
| `CIG hhh [LOC]` | "Ceiling Height at Second Location" (13.38). KSFO uses `CIG 030 RWY L10` (122 reports) **[M]**. | Lower cloud over one part of the field. |
| `w'w' NsNsNshshshs` | Obscuration, e.g. "FG SCT000", "FU BKN020" (13.35) | Smoke layer aloft, fog hiding part of the sky. |
| `NsNsNs(hshshs) V NsNsNs` | Variable sky condition (13.36) | Coverage flicker. |
| `[OCNL/FRQ/CONS] LTG[IC/CC/CG/CA] [LOC]` | Frequency: OCNL "Less than 1 flash/minute", FRQ "About 1 to 6 flashes/minute", CONS "More than 6 flashes/minute" (Table 13-7). ASOS lightning detection (ALDARS): TS within 5 NM of the ARP, VCTS at 5–10 NM, "LTG DSNT" at 10–30 NM (13.28b). | Lightning flash rate and direction. |
| `RAB05E30`, `TSB0159E30`… | Precipitation and thunderstorm begin/end times (13.29, 13.30) | Wet-surface state machine: "ended at mm" starts the drying clock. |
| `CB`, `TCU`, `ACSL`, `VIRGA` | Significant clouds (13.33, 13.37) | Towering clouds, virga shafts. |
| `PRESRR` / `PRESFR` | Pressure rising or falling rapidly (13.39) | — |
| `SLPppp` | "tens, units, and tenths of the sea-level pressure in hectopascals … 998.2 hectopascals would be coded as 'SLP982'" (13.40). The leading 9 or 10 is implicit; the decoder picks the value nearer the altimeter. | — |
| `Prrrr` | "water equivalent of all precipitation that has occurred since the last METAR … in hundredths of an inch" (13.46) | **Measured rain rate** (section 3.5). |
| `6RRRR`, `7RRRR` | 3/6-hour and 24-hour precipitation. "A trace is coded '60000'" (13.48, 13.49) | Puddle depth over time. |
| `TsnTTTsnTdTdTd` | Hourly temperature and dew point to 0.1 °C; sign digit 1 means below 0 °C (13.52) | Humidity. |
| `1…`, `2…`, `4……`, `5appp` | 6-hour max/min, 24-hour max/min, 3-hour pressure tendency (13.53–13.56) | — |
| `PWINO PNO FZRANO TSNO VISNO CHINO RVRNO` | Sensor not operating (13.57) | Tells the renderer a value is missing, not zero. |
| `$` | "ASOS/AWOS-C detects that maintenance is needed" (13.58) | Present in about half of KSFO reports (4,881 of 10,708 in the last year) **[M]**. Treat the data as valid. |

**Non-uniform conditions.** JO 7900.5E 10.15 says: "When non-uniform sky conditions are observed … the observer must
describe the condition in the remarks … For example, CIG LWR N would indicate that ceilings are lower to the north." [V]

### 2.4 "FG BNK" does not occur at KSFO; "FG IN GAP W" does

- **`FG BNK` / `FOG BANK`: 0 occurrences** in 96,367 KSFO reports from 2016–2025, and 0 in the last year **[M]**. It is
  not an FAA-coded remark: JO 7900.5E has no such entry, and a search of the text finds none **[V]**. It could only
  appear as observer plain language. The decoder still records it (`rmk.fog_bank`) if it ever appears.
- **`FG IN GAP W` / `FOG IN GAP W`: 96 reports.** 42 in 2017 and 31 in 2018, then rare. Peak months are August (31) and
  July (15) **[M]**.
  **[corrected by verifier]** The 96 are all reports, including SPECIs: 75 `FG IN GAP W`, 19 `FOG IN GAP W` and
  2 `FG IN GAP NW`. The per-year and per-month figures count **routine METARs only** (87 reports). Over all 96 reports
  the counts are 45 in 2017, 33 in 2018 (UTC year), August 32 and July 16. The "gap" to the west of SFO is the terrain gap the marine layer flows through. Its name, the San
  Bruno Gap, is **[I]**: the remark itself does not name it. The count depends on observer habit, so do not use it
  as a climatology. When present, it should add a westward fog bank on the horizon (`rmk.fog_in_gap`).
- Other KSFO plain language seen **[M]**:
  - `VIS LWR W` (29×, "visibility lower west"); **[corrected by verifier]** 26× exactly `VIS LWR W`, plus
    `VIS LWR W-NW`, `VIS LWR NW` and `VIS LWR NW-NE` once each (29 `VIS LWR` in all);
  - `BINOVC` (13×, breaks in overcast);
  - `FU DSNT E`, `FU FEW004`;
  - `TS DSIPTD`;
  - typos: `A02` for `AO2` (76×), `ALDQS`, `MOVE`, `RAEMM` (end time missing).

  The decoder handles all of them.

### 2.5 KSFO specifics that change the decoding

- **Routine METARs are issued at hh:56.** 87,533 of the 87,672 hours in 2016–2025 have a report at :56 **[M]**. Any
  other minute is a SPECI or a correction.
- **ASOS site coordinates.** AWC gives 37.6196, −122.3656, elevation 2 m. api.weather.gov gives
  −122.36558, 37.61961, elevation 3.048 m **[V]**. In our world frame that is 868 m east and 89 m north of the ARP
  **[M, tools/geo_frame.py]**. The ASOS User's Guide says "most primary visibility sensors were placed near the touchdown
  zone (TDZ) of the primary instrument runway" **[V]**. KSFO's own sensor positions are **[NV]**.
- **Secondary ceilometer** "RWY L10": `CIG 030 RWY L10` and `CHINO RWY L10` **[M]**. Its location, probably
  runway 10L, is **[I]**.
- **Cloud heights are above field elevation** ("in hundreds of feet above the surface", JO 7900.5E 10.8). SFO field
  elevation is 13.1 ft / 4.0 m surveyed (AirNav, `refs/cache/atc/airnav_ksfo.txt`) **[V]**. World-y of a cloud base = `GROUND_Y + h × 0.3048`.
- **High clouds.** The automated ceilometer reports nothing above 12,000 ft (`CLR`). KSFO reports such as `SCT200` and
  `BKN250` therefore come from the observer **[V: 13.14b "layers above 12,000 feet are not reported by automated sky
  condition sensors"]**.

### 2.6 TAF

The AIM 7-1-28 key [V] defines:
- `FM` groups ("changes are expected at: 2-digit date, 2-digit hour, and 2-digit minute");
- `TEMPO`, `BECMG` and `PROB30/40` with a `DDhh/DDhh` window;
- `P6SM`;
- `WS010/31022KT` (low-level wind shear);
- a valid period "either 24 hours or 30 hours".

The KSFO TAF fetched at 19:3xZ was `TAF KSFO 241725Z 2418/2524 …`: issued 17:25Z, valid for 30 hours **[M]**.
`decode_taf()` splits the TAF into these periods and decodes each one with the METAR body parser. Use: a forecast
scrubber, and the expected stratus onset time (for example `FM251200 … SCT010`).

### 2.7 aviationweather.gov JSON fields

The JSON gives, per report: `rawOb`, `obsTime`, `receiptTime`, `reportTime`, `temp`, `dewp`, `wdir` (number, or `"VRB"`),
`wspd`, `wgst`, `visib` (`"10+"` or a number), `altim` (hPa), `slp`, `clouds[{cover, base}]`, `fltCat`, `metarType`,
`presTend`, `maxT`, `minT`, `qcField`, `lat`, `lon`, `elev` **[M, 141 KSFO reports]**. The OpenAPI schema also
lists `wxString` ("Encoded present weather string"), `vertVis`, `precip`, `pcp3hr`, `pcp6hr`, `pcp24hr` and `snow`
**[V]**. None of the 141 reports had weather, so those fields were not seen **[NV in practice]**. The JSON drops RVR
and most remarks. **Always decode `rawOb` ourselves.** `altim` is rounded:
`realtime_feeds.md` #28 shows A2986 → 1011.3 where 29.86 × 33.8639 = 1011.18 hPa.

### 2.8 The decoder and its tests

`tools/env/metar_decode.py` (stdlib only):
- `decode_metar(raw, ref)` → dict with body groups, `rmk{…}`, `ceiling_ft`, `flight_category` (AIM 7-1-7) and
  `rel_humidity_pct`. Unknown tokens are kept in `unparsed`, unrecognised remark text in `rmk.plain`.
- `decode_taf(raw)`;
- `render_params(decoded, night)` (section 3);
- `extinction_from_visibility(V, night)`.

`tools/env/test_metar_decode.py` runs 38 tests with Python's unittest; all pass **[M]**.
- **30 real KSFO reports from 20–24 Sep 2026** (`tools/env/fixtures/ksfo_recent_20260920_24.txt`): the aviationweather.gov
  API response, fetched 2026-09-24 19:37:06Z. The expected values were written by hand.
  - They cover calm wind, gusts, PK WND, COR, SPECI, CLR and 1–4 layers.
  - They include the IFR/LIFR boundary case: `OVC005` is IFR, not LIFR.
  - They include the 6/24-hour temperatures, pressure tendency, PRESFR, VISNO and `$`.
  - The last days had **no** present weather, so a second fixture was added.
- **28 archived KSFO reports** with weather (`fixtures/ksfo_archive_wx.txt`, IEM archive):
  - fog: `M1/4SM R28R/1000V1400FT FG VV002`, BCFG, PRFG, VCFG, the "FG BKN000" remark, TWR/SFC VIS;
  - rain: `+RA BR SQ` with G63;
  - thunderstorms: `-TSRA … BKN044CB … FRQ LTGICCCCG SE`, `GRRA` with `GR LESS THAN 1/4`;
  - drizzle, `FU DSNT E`, `CIG 004V010`, `CIG 030 RWY L10`, `VIS 1/2V2 1/2`, `220V280`, `VRB03KT`, `CHINO RWY L10`.
- **FAA coding examples** (JO 7900.5E chapter 13) and the **AIM 7-1-28 key** example (`SLP045` = 1004.5 hPa,
  `T01820159` = 18.2/15.9 °C). The FAA examples are coded into one synthetic report, one group per paragraph.
- **Render checks.** The night/day visibility ratios reproduce Rasmussen 1999's statements: "a little less than twice"
  at 0.5 mi, "more than 2.4 times" below 0.1 mi. Also checked: layer summation, windsock limits, the rain rate from a
  SPECI's `Prrrr`.

Mutation check **[M]**:
- shifting the T-group decode by 0.1 °C fails 33 tests;
- scaling visibility by 1 % fails 42 tests.

A sweep over all 107,075 rows of the two IEM downloads (2016–2026, overlapping) leaves only malformed archive rows
unparsed. Examples:
`KSFO 121856Z 9012 10 …`, TAF text stored as METAR, `10SMSM`.

---------------------------------------------------------------------------------------------------------------------

## 3. From decoded METAR to rendering parameters (task b)

`render_params()` implements this section. The renderer needs one environment state, updated per METAR or SPECI and
interpolated over about 60 s:
`{extinction(z), fog layer, cloud layers[], sun visibility, diffuse ratio, precip{kind, rate, drops/m³, fall speed},
surface wetness, wind{dir, speed, gust, variability}, lightning, aerosol tint}`.

### 3.1 Visibility → extinction coefficient

**Physics [V].**
- Koschmieder: a black target against the horizon sky loses contrast as C = e^(−σR). Visibility is the range where C
  falls to the observer's threshold ε, so V = −ln ε / σ. Rasmussen et al. 1999, J. Appl. Meteor. 38:1542–1563,
  https://opensky.ucar.edu/system/files/2024-08/articles_15245.pdf, eq. 21: "The contrast threshold e of the observer's
  eye usually is assumed to be constant at 0.02 or 0.055."
- WMO defines Meteorological Optical Range with 5 %: "Length of path in the atmosphere required to reduce the luminous
  flux in a collimated beam from an incandescent lamp, at a colour temperature of 2 700 K, to 5 per cent of its original
  value". WMO OSCAR, https://space.oscar.wmo.int/variables/view/meteorological_optical_range_mor_surface. The CIE ILV
  17-31-018 entry says the same (https://cie.co.at/eilvterm/17-31-018).
- **What KSFO actually reports.** Rasmussen 1999 §6c: "The U.S. National Weather Service visibility algorithm for its
  ASOS systems uses Koschmieder's Eq. (21) with e = 0.055 to estimate day visibility, and the simplified Allard's law
  [(24)] with I0 = 25 candles and CDB = 0.084 mi-1 to estimate night visibility." Eq. 24: Vn = (I0/CDB) e^(−σVn).
- The ASOS User's Guide (March 1998), https://www.weather.gov/media/asos/aum-toc.pdf, §4.2:
  - "For a given extinction coefficient, the day calculation will provide a visibility from 1/2 to 1/3 of that
    derived by the night equation. Therefore, an abrupt change in visibility may be reported after sunrise or
    sunset";
  - "ASOS computes a running 10-minute harmonic mean";
  - "Visibilities of 10 miles or greater are reported as '10SM'".
- FMH-1 (2005) RVR tables are also built on day contrast thresholds of "5.5 Percent" and "5.0 Percent" **[V]**.
- **Verifier note (not a refutation).** The ASOS constants (ε = 0.055, I₀ = 25 cd, CDB = 0.084 mi⁻¹) come from
  Rasmussen 1999, a peer-reviewed paper *describing* the NWS algorithm. The NWS algorithm specification itself was not
  located; a web search did not find it, and the ASOS User's Guide gives no numeric constants. So the constants are
  secondary. The two sources also disagree in size. With R99's constants, night V / day V at fixed σ is 2.66 at
  0.05 mi, 2.45 at 0.1 mi, 1.97 at 0.5 mi, 1.77 at 1 mi, 1.31 at 5 mi and 1.13 at 10 mi. That matches the guide's
  "1/2 to 1/3" only below about 0.3 mi. The σ table below follows R99; if the NWS spec is found, re-check it.

**Mapping [V formula; M numbers].** σ_day = −ln(0.055)/V = 2.900/V. σ_night = ln(I0 / (CDB·V_mi)) / V_mi, converted to m⁻¹.

| Reported | V (m) | σ day, ASOS (m⁻¹) | σ night, ASOS (m⁻¹) | night/day | σ with ε = 0.02 (m⁻¹) | σ used by the app now |
|---|---|---|---|---|---|---|
| 10 SM | 16,093 | ≤ 1.80e-4 (lower bound) | ≤ 2.11e-4 | 1.17 | 2.43e-4 | 8.8e-5 (assumes 40 km) |
| 5 SM | 8,047 | 3.60e-4 | 5.08e-4 | 1.41 | 4.86e-4 | 4.4e-4 |
| 3 SM | 4,828 | 6.01e-4 | 9.52e-4 | 1.59 | 8.10e-4 | 7.3e-4 |
| 1 SM | 1,609 | 1.80e-3 | 3.54e-3 | 1.96 | 2.43e-3 | 2.2e-3 |
| 1/2 SM | 805 | 3.60e-3 | 7.94e-3 | 2.20 | 4.86e-3 | 3.6e-3 (capped) |
| 1/4 SM | 402 | 7.21e-3 | 1.76e-2 | 2.44 | 9.72e-3 | 3.6e-3 (capped); `M1/4SM` is parsed as 4 SM → 5.5e-4 |

What the renderer should do **[I]**:
- Use the ASOS day or night inversion, then feed σ to the aerial-perspective and fog model. Both the TSL port
  (`js/three/sky.js`) and `common.js applyFog` take a sea-level density.
- Remove the 0.004 cap and the 0.97 opacity cap.
- For `10SM`, σ is only an upper bound. Use the clear-air aerosol of the sky model, e.g. the Mie term
  `mie: 21e-6`, and clamp it to at most 1.8e-4 m⁻¹. Do not assume a fixed 40 km.
- Visibility between 7 and 10 SM with no obscuration coded is "hazy but unspecified". JO 7900.5E only requires HZ/BR
  below 7 SM.
- The reported value is a 10-minute harmonic mean at one sensor. Directional remarks (`VIS NW 1/2`, `VIS LWR W`) and
  tower/surface visibility should shape the 3-D field around that mean. A heterogeneous field is **[I]**.

### 3.2 Day/night switching

- ASOS [V]: "A photocell on the visibility sensor turns on at dawn or off at dusk at a light level between 0.5 and
  3 foot candles (deep twilight). This function determines whether the sensor uses the day or night equation."
- 0.5–3 fc is 5–32 lux. Mapping that to sun elevation needs a twilight illuminance model. I recommend blending
  σ_day → σ_night between sun elevations of about −1° and −5° **[I, NV]**. The real sensor switches abruptly, so
  reported visibility can jump at dusk (ASOS guide).
- Night rendering needs the night σ so that runway, approach and taxiway lights fade at the right distance. Allard's law
  is the physics of seeing lights: E = I₀e^(−σR)/R². The lighting research should use the same σ for its light-halo
  and fade model **[I]**.

### 3.3 Height structure: marine layer, fog and mist

Observed facts:
- Summer low ceilings at KSFO have a median of 1,100 ft (p10 700 ft, p90 1,900 ft) **[M]**.
- MIT Lincoln Laboratory ATC-319 (2006), https://archive.ll.mit.edu/mission/aviation/publications/publication-files/atc-reports/Clark_2006_ATC-319_WW-15318.pdf:
  "For cloud depths typical of marine stratus (usually less than 1000 feet) …"; the Local Model relies on "the base of
  the inversion height … presumed to be an estimate of the cloud top height" **[V]**.
- ASOS VV: "unknown hits … primarily caused by precipitation and fog that mask the base of the clouds … processed as a
  vertical visibility (VV)" **[V, ASOS guide 4.1]**.

Recommended profile **[I]**. Use three slabs instead of today's single exponential (`uFog.y = 1/700`):

1. **Sub-cloud layer**, from the ground to the ceiling (or to VV). Constant σ equal to the surface σ from 3.1: the
   marine boundary layer is well mixed below the stratus.
2. **Cloud slab**, from the base to the base plus depth. The depth comes from the Oakland 12Z/00Z sounding's inversion
   base when available (section 5.5), else 1,000 ft.
   - In-cloud extinction is σ_c ≈ 3·LWC / (2·ρ_w·r_eff), assuming an extinction efficiency of about 2 for droplets
     much larger than the wavelength **[I, textbook relation]**.
   - With LWC 0.1–0.5 g m⁻³ and r_eff 6–10 µm, σ_c ≈ 0.025–0.075 m⁻¹, an in-cloud visual range of 40–120 m. The
     values are **[2nd/I]**. *Verifier note:* this range pairs low LWC with small r_eff and high LWC with large r_eff.
     Taking the extremes independently gives 0.015–0.125 m⁻¹ (visual range 23–190 m with ε = 0.055). MODIS–MISR marine-stratocumulus r_eff is 4–17 µm (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6988446/).
   - This matters when the camera follows an arrival through the deck.
3. **Free troposphere** above the inversion: clear-air σ.

Fog cases:
- `FG` + `VVhhh`: a surface fog layer at least VV deep **[V meaning, I depth]**. Surface σ from visibility. VV = 100–200 ft
  in all KSFO FG cases we saw.
- `MIFG`: fog below 6 ft only (JO 7900.5E).
- `BCFG` / `PRFG`: patchy. Use a noise-masked fog volume, keep prevailing visibility for the clear parts, and use any
  sector remark for direction.
- `BR` without FG: surface σ from visibility, filling the sub-cloud layer.
- `TWR VIS` above `SFC VIS`: fog shallower than the tower cab.

KSFO's tower cab height is in the tower research, not verified here **[NV]**.

### 3.4 Clouds: coverage, heights, sun occlusion, diffuse light

- **Summation principle [V].** JO 7900.5E 10.4o: "The summation amount of sky cover for any given layer is the sum of
  the sky cover of the layer being evaluated, plus the sky cover of all lower layers … No layer can have a summation
  amount greater than 8/8ths." Example from Table 10-3: "5/8 sky cover at 1,000 feet, 2/8 sky cover at 5,000 feet,
  1/8 sky cover at 30,000 feet" → `BKN010 BKN050 OVC300`.
- **Per-layer coverage [I].** Take the middle of each okta range: FEW 1.25/8, SCT 3.5/8, BKN 6/8, OVC 8/8. Then own_i =
  1 − (1 − C_i)/(1 − C_{i−1}), assuming random overlap. Example: `FEW006 BKN012` → FEW 0.156, BKN own 0.70. The
  probability of seeing the sun is 0.25.
- **Heights.** Base = ground + h (AGL). Table 13-6 resolution: ±50 ft below 5,000 ft; ±250 ft to 10,000 ft; ±500 ft above.
- **Thickness.** Not in the METAR. Low stratus: marine-layer depth (3.3). Mid/high layers: use the renderer's default
  and mark it **[I]**.
- **Cloud types.** Only CB and TCU are coded. Anything else (Ac, Ci) is **[I]** from height:
  - below 6,500 ft: stratiform;
  - 6,500–20,000 ft: mid-level;
  - above 20,000 ft: cirriform.
- **Sun and sky light.**
  - Direct sun: occluded wherever a cloud layer's coverage map intersects the sun ray. The existing `cloudShadow` does
    this for one layer; extend it to N layers.
  - Global irradiance under N oktas: the empirical Kasten & Czeplak (1980) ratio G(N)/G(0) = 1 − 0.75 (N/8)^3.4
    **[2nd]**. The original (Solar Energy 24:177–189) could not be fetched. ScienceDirect returns 403, and the formula
    was only seen in secondary summaries. A NASA education page gives the related "P = 990 (1-0.75F³) watts/m²"
    (https://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf) **[V]**.
  - Use K–C only to set the overall exposure and sky/ambient scale. Under OVC it gives 25 % of clear-sky global light,
    all of it diffuse.
- **Cloud drift.** The METAR wind is at 10 m. Wind at the cloud level is not in the METAR. The app currently uses
  `2.5 × surface + 1 m/s` **[I, unverified]**. Better: the OAK sounding's wind at the base height (section 5.5), or the
  TAF `WS` group when present.

### 3.5 Precipitation particles

Intensity classes, JO 7900.5E Table 9-4 (rain rate) [V]:
- light "Up to 0.10 inch per hour" (≤ 2.5 mm/h);
- moderate "0.11 inch to 0.30 inch per hour" (2.8–7.6 mm/h);
- heavy "More than 0.30 inch per hour" (> 7.6 mm/h).

Visual criteria, Table 9-2:
- light rain: drops "easily seen";
- moderate: "spray is observable just above pavements";
- heavy: "Rain seemingly falls in sheets … heavy spray to height of several inches".

Drizzle and snow are graded by **visibility**, not rate (Table 9-5):
- light: visibility > ½ mile;
- moderate: > ¼ to ½ mile;
- heavy: ≤ ¼ mile.

**Rate.** Use `Prrrr` when present. It is the water since the last METAR. For a SPECI at hh:mm, divide by
(mm − 56) mod 60 minutes, because KSFO's routine METAR is at :56 **[M]**.
- Example: `SPECI 170810Z … +RA … P0036` = 0.36 in in 14 min = **39 mm/h** **[M]**.
- Without `Prrrr`, use the geometric middle of the Table 9-4 class **[I]**.

**Drop population [V formula, GN07].** Garg & Nayar, "Vision and Rain", IJCV 2007,
https://www.cs.columbia.edu/CAVE/publications/pdfs/Garg_IJCV07.pdf, quotes the Marshall–Palmer (1948) distribution:
- "N(a) = 8 × 10⁶ e^(−8200 h^−0.21 a), where, h is the rain rate given in mm/hr, a is the radius of the drop in meters";
- terminal velocity (Gunn & Kinzer 1949): "v = 200 √a".

In diameter form, Λ = 4.1 R^−0.21 mm⁻¹ and N₀ = 8,000 m⁻³ mm⁻¹. The median-volume diameter is D₀ = 3.67/Λ, a property of
the exponential distribution. The values below are **[M]**:

> **[corrected by verifier]** N₀ = 8,000 m⁻³ mm⁻¹ does **not** follow from the Garg & Nayar formula quoted above. Their
> radius form, 8 × 10⁶ m⁻⁴ per metre of radius, converts to 4,000 m⁻³ mm⁻¹ per mm of diameter (da = 0.5 × 10⁻³ dD).
> Integrated as printed, it gives **half** the drop counts in this table (976 instead of 1,951 drops/m³ at 1 mm/h).
> 8,000 m⁻³ mm⁻¹ (0.08 cm⁻⁴) is the usual textbook Marshall–Palmer value, and it is what `render_params` uses.
> However, neither Marshall & Palmer (1948) nor a glossary stating it could be fetched here: the AMS glossary returned a
> Cloudflare 403 and Wikipedia a 429. Treat N₀, and so the two drop-count columns, as **[2nd/NV]**. Λ, D₀ and the fall
> speeds do not depend on N₀ and stand.

| Rate (mm/h) | Class | Drops > 0.5 mm per m³ | All drops per m³ | D₀ (mm) | Fall speed at D₀ (m/s) |
|---|---|---|---|---|---|
| 1 | light | 251 | 1,951 | 0.90 | 4.2 |
| 5 | moderate | 634 | 2,736 | 1.26 | 5.0 |
| 10 | heavy | 894 | 3,165 | 1.45 | 5.4 |
| 25 | heavy | 1,352 | 3,836 | 1.76 | 5.9 |

What the renderer should do **[I]**:
- Streak length = v × exposure time (Garg & Nayar model streaks this way).
- Particle count in a camera-attached volume = density × volume. Scale it down for the screen-space budget and keep the
  ratio between classes.
- Drizzle: diameter < 0.5 mm (JO 7900.5E), falling at about 1–2 m/s **[I]**. Render as a dense fine mist of particles
  with no visible streaks. Drizzle's visual weight is mostly in σ, which the visibility already gives.
- Showers (`SH`) are cellular: modulate the rate in space and time.
- `TS`: lightning at the Table 13-7 rate. It is at the station if in the body, 5–10 NM away for VCTS, and on the horizon
  in the given direction for `LTG DSNT`.
- Hail `GR`/`GS`: rare (2 reports in 10 years **[M]**).
  **[corrected by verifier]** 3 reports in 2016–2025, all SPECIs and none routine: `GRRA` on 2 Mar 2024 04:48Z
  (hail), and `-RAGS` on 6 Mar 2016 and `RAGS` on 23 Jan 2017 (small hail/snow pellets).

### 3.6 Wet surfaces, puddles, darkening

METAR inputs **[V meaning]**:
- present precipitation;
- `RAB..`/`RAE..` times;
- `Prrrr` (0.01 in resolution; `P0000` means less than 0.01 in);
- `6RRRR` / `60000` (trace).

Wetness state machine **[I]**:
- `wet` rises towards 1 at a rate proportional to the rain rate.
- `puddle` accumulates from the precipitation total in mm, minus drainage.
- Drying starts at the `…E mm` time. It is faster with sun, wind and a large temperature–dew point spread.

The drying constants are **not sourced**. Calibrate them against reference photos or video (open question 5).

Material response. Sébastien Lagarde, "Water drop 3b – Physically based wet surfaces" (2013),
https://seblagarde.wordpress.com/2013/04/14/water-drop-3b-physically-based-wet-surfaces/ **[V]**:
- **Darkening.** "We lerp between no attenuation (1.0) and full attenuation (0.2) based on porosity", i.e.
  `Diffuse *= lerp(1, lerp(1, 0.2, porosity), wetLevel)`. The cause, from Jensen et al.: "The subsurface scattering is
  the most significant reason why materials are darker when wet". For asphalt in driving simulators, Nakamae et al.
  "use a factor between 0.1 and 0.3 to attenuate the diffuse albedo".
- **Specular.** Glossiness rises with wetness. For a thin water layer, "a slight smoothing of the normal and a slight
  boost in specular"; for puddles, "totally flat and have blended to water properties". A water layer uses a flat
  normal, blended progressively from the normal map as the layer deepens. The water spectrum is "approximate as
  constant 0.02".
- **Drying.** "When drying, the specular reflection disappears but the diffuse reflection still darker than the dry
  surface".

For SFO **[I]**:
- Runways and taxiways: asphalt and grooved concrete, medium porosity.
- Puddles collect in paint-free low areas. Our pavement bake has no slope data, so use noise masks.
- The ground bake (`bakeGround`) is static. Wetness must be a dynamic uniform in the ground shader, not re-baked.

### 3.7 Wind: windsock, flags, gusts

- **Direction.** The METAR is true north (JO 7900.5E 13.10) **[V]**. The D-ATIS reads 10° lower in every non-calm
  pair of 23–24 Sep (22 of 22) **[M]**; its wind is magnetic, SFO variation 14° E (AirNav) **[V]**. Never drive visuals
  from the ATIS wind.
- **Windsock.** FAA AC 150/5345-27F (12/15/2021), https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-27F-Wind-Cone.pdf
  **[V]**:
  - 3.2.2: "Design the taper or the fabric windsock from the throat to the trailing end to cause the windsock to fully
    extend when exposed to a wind of 15 knots";
  - 3.5: "moves freely about the vertical shaft … when subjected to wind of 3 knots … or more and indicate the true
    wind direction within ±5 degrees";
  - sizes: 8 ft × 18 in throat (Size 1) and 12 ft × 36 in (Size 2);
  - fabric "natural (white), yellow, or orange";
  - lighted versions provide "a minimum of 2 foot-candles".
  - AC 150/5345-27E, the version named in the task, is **cancelled**.
  - The shape between 3 and 15 kt is not specified. The decoder uses a linear extension (0 at 3 kt, 1 at 15 kt)
    **[I]**. Calibrate it on video.
  - AirNav: "Wind indicator: lighted" **[V]**.
  - Positions: OSM has one `aeroway=windsock` at 37.6245391, −122.3871016 (ODbL) **[V]**. That is probably incomplete;
    positions are for the airfield-lighting work **[NV]**.
- **Gusts.** Between METARs, animate speed as a noise process between `ff` and `Gfmfm`, with `PK WND` as the maximum
  since the last METAR **[I process, V bounds]**.
  - `dndndnVdxdxdx`: the direction wanders within that sector.
  - `VRB` (≤ 6 kt): random slow direction.
  - `00000KT`: the sock hangs.
- **Water.** Waves and wind already exist (`world.waterU.uWind`); drive them with the METAR wind **[existing]**.

### 3.8 Haze and smoke tint

JO 7900.5E 9.3 **[V]**:
- Haze: "Dark objects viewed through this veil tend to have a bluish tinge while bright objects, such as the sun or
  distant lights, tend to have a dirty yellow or reddish hue … When haze is present and the sun is well above the
  horizon, its light may have a peculiar silvery tinge."
- Smoke: "the disk of the sun at sunrise and sunset appears very red. The disk may have an orange tinge when the sun
  is above the horizon. Evenly distributed smoke from distant sources generally has a light grayish or bluish
  appearance."

Renderer **[I]**:
- HZ: σ from visibility with a high-single-scattering-albedo aerosol, bluish in-scatter.
- FU: σ from visibility plus absorption; lower the single-scattering albedo and redden the transmitted sun.
- `FU BKN020`-style remarks put the smoke layer aloft.

At KSFO, HZ/FU hours cluster in Nov 2018 (270 h), Sep 2020 (146 h) and Aug 2020 (70 h) **[M]**. Those dates coincide
with major Northern California wildfire smoke episodes; the cause is **[I]**, not checked against a source.

### 3.9 Temperature and dew point

Take temperature and dew point from the `T` group to 0.1 °C. Relative humidity uses the Magnus form (Alduchov & Eskridge
1996 coefficients, **[2nd]** — not fetched).

Uses **[I]**:
- a spread of 2 °C or less with visibility below 7 SM supports BR/FG;
- humidity feeds aerosol swelling (haze whitening);
- cold-soaked aircraft glass fogging is optional.

---------------------------------------------------------------------------------------------------------------------

## 4. SFO climatology (task c)

### 4.1 Data

- **Reports.** Iowa Environmental Mesonet ASOS archive for SFO, 2016-01-01 to 2025-12-31: 96,367 reports, of which
  87,533 are routine METARs at hh:56. They were decoded with our decoder; rows the IEM synthesised from GHCN-hourly are
  dropped. Local time is America/Los_Angeles. Reproduce with `python3 tools/env/ksfo_climatology.py [--fetch]`; the
  output is in `refs/cache/weather/ksfo_climatology.{md,json}`.
- **Licence.** IEM: "The materials found on this website are in the public domain and may be used freely by anyone for
  any lawful purpose. Attributing the Iowa Environmental Mesonet of Iowa State University would be appreciated."
  (https://mesonet.agron.iastate.edu/disclaimer.php) **[V]**.
- **Climate normals.** NCEI 1991–2020 normals for station USW00023234 "SAN FRANCISCO INTL AP, CA US" **[V]**, from
  https://www.ncei.noaa.gov/access/services/data/v1?dataset=normals-monthly-1991-2020&stations=USW00023234. Annual
  precipitation 19.64 in; mean temperature 58.7 °F. Monthly precipitation:

  | Month | Precipitation (in) | Days ≥ 0.01 in |
  |---|---|---|
  | Jan | 3.89 | 10.9 |
  | Feb | 3.96 | 10.8 |
  | Mar | 2.73 | 10.3 |
  | Dec | 4.14 | 11.1 |
  | Jul | 0.00 | 0.0 |
  | Aug | 0.04 | 0.4 |

### 4.2 Monthly frequencies (% of routine hourly METARs) [M]

Legend:
- "Below 2500/5": ceiling below 2,500 ft or visibility below 5 SM, i.e. below the charted visual-approach minimums in 4.5.
- "Precip": RA, DZ, GR, GS, UP, SN, PL or TS.

| Month | n | CIG<1000 | CIG<2500 | CIG≤3000 | VIS<3 | below 2500/5 | FG | BR | HZ/FU | precip | TS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Jan | 7434 | 3.7 | 14.9 | 19.7 | 2.2 | 16.9 | 0.6 | 5.6 | 0.6 | 9.4 | 0.0 |
| Feb | 6787 | 1.4 | 9.5 | 13.1 | 1.4 | 10.8 | 0.1 | 3.5 | 0.3 | 8.7 | 0.0 |
| Mar | 7404 | 1.8 | 11.6 | 15.7 | 1.0 | 12.6 | 0.1 | 2.6 | 0.2 | 8.6 | 0.0 |
| Apr | 7193 | 2.5 | 15.4 | 18.9 | 0.2 | 15.8 | 0.0 | 1.1 | 0.1 | 3.0 | 0.0 |
| May | 7420 | 5.5 | 24.0 | 26.2 | 0.1 | 24.1 | 0.0 | 0.4 | 0.3 | 1.3 | 0.0 |
| Jun | 7194 | 6.9 | 19.3 | 20.1 | 0.0 | 19.3 | 0.0 | 0.2 | 0.1 | 0.1 | 0.0 |
| Jul | 7406 | 8.3 | 22.2 | 22.3 | 0.0 | 22.2 | 0.0 | 0.0 | 0.1 | 0.1 | 0.0 |
| Aug | 7434 | 8.1 | 23.6 | 24.1 | 0.1 | 23.9 | 0.0 | 0.2 | 1.2 | 0.1 | 0.1 |
| Sep | 7195 | 5.9 | 19.7 | 21.2 | 1.5 | 20.3 | 0.1 | 1.1 | 2.6 | 0.4 | 0.0 |
| Oct | 7428 | 3.1 | 10.9 | 13.0 | 0.6 | 11.6 | 0.1 | 1.7 | 0.7 | 1.8 | 0.0 |
| Nov | 7202 | 2.9 | 11.5 | 14.7 | 3.0 | 14.5 | 0.3 | 3.5 | 4.6 | 4.2 | 0.0 |
| Dec | 7436 | 5.9 | 17.3 | 21.5 | 3.7 | 19.2 | 0.6 | 7.8 | 1.3 | 8.8 | 0.0 |

### 4.3 Diurnal cycle: below 2,500 ft / 5 SM, % by month and local clock hour of the :56 report [M]

| Month | 00 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Jan | 15 | 18 | 18 | 20 | 20 | 22 | 20 | 22 | 25 | 23 | 23 | 19 | 17 | 16 | 14 | 11 | 11 | 12 | 12 | 13 | 13 | 13 | 15 | 15 |
| Feb | 10 | 10 | 12 | 13 | 13 | 14 | 15 | 16 | 17 | 14 | 14 | 10 | 8 | 7 | 8 | 8 | 7 | 10 | 11 | 10 | 7 | 8 | 8 | 10 |
| Mar | 12 | 12 | 12 | 14 | 14 | 16 | 16 | 19 | 18 | 19 | 15 | 13 | 9 | 10 | 8 | 8 | 9 | 9 | 11 | 10 | 12 | 11 | 14 | 12 |
| Apr | 19 | 19 | 22 | 24 | 25 | 25 | 24 | 25 | 26 | 22 | 16 | 11 | 10 | 9 | 6 | 6 | 7 | 11 | 11 | 8 | 11 | 13 | 14 | 16 |
| May | 29 | 32 | 35 | 35 | 38 | 38 | 39 | 37 | 39 | 32 | 23 | 19 | 14 | 10 | 9 | 10 | 9 | 9 | 12 | 15 | 20 | 24 | 23 | 27 |
| Jun | 21 | 27 | 28 | 33 | 32 | 32 | 35 | 36 | 31 | 23 | 17 | 11 | 8 | 6 | 5 | 5 | 7 | 9 | 10 | 15 | 16 | 18 | 20 | 19 |
| Jul | 26 | 29 | 32 | 38 | 41 | 45 | 47 | 44 | 38 | 24 | 17 | 9 | 6 | 5 | 5 | 6 | 6 | 8 | 11 | 13 | 16 | 19 | 22 | 23 |
| Aug | 25 | 30 | 35 | 41 | 46 | 48 | 50 | 52 | 46 | 30 | 17 | 12 | 9 | 5 | 5 | 5 | 5 | 8 | 12 | 13 | 15 | 20 | 20 | 24 |
| Sep | 23 | 29 | 32 | 33 | 34 | 35 | 37 | 38 | 38 | 28 | 18 | 12 | 10 | 8 | 5 | 6 | 8 | 9 | 9 | 12 | 12 | 14 | 16 | 21 |
| Oct | 12 | 15 | 17 | 16 | 16 | 17 | 21 | 20 | 21 | 20 | 15 | 11 | 5 | 5 | 5 | 4 | 3 | 6 | 5 | 6 | 7 | 8 | 10 | 13 |
| Nov | 15 | 15 | 17 | 18 | 17 | 21 | 23 | 20 | 21 | 19 | 19 | 16 | 11 | 12 | 10 | 9 | 7 | 8 | 9 | 9 | 12 | 12 | 12 | 14 |
| Dec | 20 | 24 | 23 | 24 | 27 | 26 | 25 | 28 | 28 | 28 | 24 | 18 | 18 | 15 | 14 | 12 | 11 | 11 | 13 | 11 | 12 | 15 | 16 | 18 |

**Summer marine stratus, Jun–Sep [M]:**
- Ceilings below 3,000 ft: n = 6,389, p10 700 ft, median 1,100 ft, p90 1,900 ft.
- Of 1,220 summer days, 519 (43 %) had a ceiling below 2,500 ft at 07:56 local.
- On those days, the first :56 report with no ceiling below 2,500 ft came at a median of **10:56** (p25 09:56, p75
  11:56). 25 days stayed low past 19:56.
- Evening return: on 281 days that were clear at 14:56 and went low later, onset came at a median of 20:56
  (p25 18:56, p75 22:56).

**Fog (FG)** is a winter night and morning phenomenon. Reports by local hour, 00 to 23:
[2, 3, 7, 8, 10, 18, 18, 22, 21, 11, 10, 3, 2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1] **[M]**.

These numbers match the primary narrative, MIT Lincoln Laboratory ATC-252 (Clark & Wilson, 25 June 1996),
https://archive.ll.mit.edu/mission/aviation/publications/publication-files/atc-reports/atc-252.pdf **[V]**:
- "the local airspace is prone to regular occurrences of low ceiling conditions due to intrusion of marine stratus cloud,
  which is present along the Pacific coast much of the time from May through September. Typically, the stratus cloud
  forms in the San Francisco Bay area overnight and dissipates during the middle to late morning … A similar (though
  less frequent) problem exists in the evening when the onset of clouds can interfere with the final arrival peak of
  the day."
- "Aircraft arriving at SFO from all directions are merged together in the approach zone approximately 5-15 miles to
  the east-southeast of the airport … this merger occurs at an altitude of approximately 3500 feet … When aircraft are
  not able to see one another in this merger zone due to visual obstruction (cloud, haze, precipitation), the
  approaching aircraft must be staggered."

The NWS forecast office (MTR) Area Forecast Discussion discusses marine-layer depth daily. On 24 Sep 2026 it said:
"Marine layer is pretty much non-existent overnight"; "The lack of a better defined marine layer has resulted in VFR
conditions regionwide". Source: api.weather.gov `/products/types/AFD/locations/MTR`, fetched 2026-09-24 **[V]**.
Today's 12Z Oakland sounding shows a surface-based inversion: 15.8 °C at the surface, 25.2 °C at 453 m. That is
consistent with no stratus **[M]**.

### 4.4 Wind [M]

| Month | W 230–320° | SE–S 090–220° | other | calm | VRB | gust | ≥ 20 kt | tailwind ≥ 5 kt on 28 / 01 / both |
|---|---|---|---|---|---|---|---|---|
| Jan | 25.6 | 33.4 | 20.4 | 19.7 | 0.8 | 6.3 | 3.0 | 13.9 / 12.6 / 3.4 |
| Feb | 42.2 | 25.8 | 15.5 | 15.7 | 0.8 | 11.5 | 5.6 | 10.7 / 17.0 / 4.2 |
| Mar | 50.9 | 27.4 | 11.9 | 8.7 | 1.0 | 12.2 | 4.9 | 9.4 / 26.4 / 3.9 |
| Apr | 73.4 | 12.8 | 8.0 | 5.0 | 0.8 | 16.1 | 10.1 | 3.1 / 32.4 / 1.4 |
| May | 80.0 | 9.9 | 6.3 | 3.0 | 0.8 | 19.3 | 11.7 | 1.8 / 41.0 / 0.9 |
| Jun | 82.9 | 5.8 | 7.9 | 2.9 | 0.6 | 18.2 | 12.1 | 0.6 / 32.0 / 0.3 |
| Jul | 85.8 | 3.4 | 7.9 | 2.0 | 0.9 | 10.8 | 6.4 | 0.2 / 19.8 / 0.1 |
| Aug | 82.7 | 4.9 | 8.4 | 3.2 | 0.8 | 10.2 | 5.7 | 0.5 / 21.3 / 0.3 |
| Sep | 75.1 | 8.6 | 9.2 | 6.3 | 0.8 | 8.0 | 4.5 | 1.0 / 21.0 / 0.4 |
| Oct | 58.3 | 14.5 | 13.5 | 12.9 | 0.9 | 3.9 | 2.2 | 4.0 / 14.3 / 1.5 |
| Nov | 37.1 | 27.3 | 16.6 | 18.2 | 0.8 | 3.9 | 1.5 | 7.7 / 10.4 / 2.3 |
| Dec | 23.0 | 32.5 | 23.5 | 20.1 | 1.0 | 5.3 | 2.1 | 13.2 / 10.9 / 3.1 |

Annual: tailwind ≥ 5 kt on runway 28 in 5.5 % of hours, on runway 01 in 21.6 %, on both in 1.8 %; calm 9.8 %.

Jun–Aug mean wind speed by local hour, 00 to 23:
9.1, 8.5, 8.1, 7.6, 7.2, 7.0, 6.7, 6.3, 6.9, 8.3, 9.6, 11.3, 13.2, 15.1, 16.9, 17.6, 17.9, 17.4, 16.3, 14.7, 13.2, 11.8, 10.7, 9.9 kt.
The afternoon sea breeze peaks at 16:00–17:00 at about 18 kt; the minimum is at dawn.

Runway true headings (28 = 297.83°, 01 = 27.83°) come from the airport grid in `CLAUDE.md` / `js/geo.js`.

### 4.5 How SFO chooses its runway configuration

- **SFO (flysfo.com, "Runway Constraints, Flight Patterns, and Operations",
  https://www.flysfo.com/about/airport-operations/policies-regulations/runway-constraints, fetched 2026-09-24) [V]:**
  - "95-98% of the time, winds blow from the west or north at SFO … This operational flow is called the West Plan.
    While operating under SFO's West Plan: primary departure runways are 1L/R facing north. primary arrival runways are
    28L/R facing west."
  - "Less than 5% of the time, winds blow from the southeast at SFO … Southeast Plan … primary departure runways are
    10L/R facing east. primary arrival runways are 19L/R facing south."
  - "In fair weather, currently, SFO can accommodate approximately 45 arrivals per hour … SFO's runways are only 750
    feet apart, so aircraft must arrive single-file. This reduces the airport's arrival rate to approximately 36 per
    hour."
  - Note: the raw wind is westerly in only 60 % of hours **[M]**. The "95-98 %" is operational, not a wind statistic. It
    matches our tailwind statistic (5.5 %).
- **FAA JO 7110.65 3-5-1 [V]**: "Assign the runway/s most nearly aligned with the wind when 5 knots or more, or the
  'calm wind' runway when less than 5 knots unless: Use of another runway is operationally advantageous. A Runway Use
  Program is in effect." (https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_5.html)
- **Charted visual approaches** (FAA d-TPP cycle 2609, "SW-2, 03 SEP 2026 to 01 OCT 2026",
  `refs/cache/atc/dtpp2609/`) **[V]**:
  - QUIET BRIDGE VISUAL RWY 28R ("Orig 09JUL26"): "Weather Minimums: SFO 2500'/5 or SFO 1000'/3 with 5 SM visibility
    in eastern quadrant (030° to 120°)." "NOTE: Closely spaced parallel approaches may be in progress to Runway 28L
    utilizing I-SFO."
  - TIPP TOE VISUAL RWY 28L/R ("Amdt 3 24MAR22"): the same SFO minimums "and San Mateo AWOS 2400'/5 (If AWOS
    inoperative, SQL 2400'/5)". "NOTE: Closely spaced parallel visual approaches may be in progress."
  - So the METAR can tell when visuals are **impossible**: ceiling < 2,500 ft or visibility < 5, unless the
    eastern-quadrant clause applies. That is the "below 2500/5" column in 4.2 and 4.3.
- **Observed D-ATIS, 23 Sep 19:56Z – 24 Sep 18:56Z** (https://atis.info/api/history/KSFO, third party) **[M]**. The
  weather was VFR the whole time.

  | Local time (PDT) | ATIS | Approach in use |
  |---|---|---|
  | until 21:56 | Z–I | "SIMUL VISUAL APPROACH RWY 28L AND QUIET BRIDGE VISUAL RWY 28R" |
  | 22:56–23:56 | J–K | "ILS RY 28R APP IN USE" |
  | 00:56–02:56 | M–O | "ILS RY 28L APP IN USE" |
  | 03:56–05:56 | Q–S | "QUIET BRIDGE VA RY 28R" |
  | from 06:56 | T onwards | simultaneous visuals again |

  Departures used "RWYS 28L, 28R" throughout, because "RY 1L, 1R CLSD". The SFO travel alert says [V]: "ongoing runway
  closures for construction work … The runway is expected to reopen in early October 2026".
- **Recommendation [I].** Priority order for the scene's runway configuration:
  1. **observed ADS-B flow** (arrivals and departures per runway in the last 20 min; the traffic engine already
     classifies runway ends);
  2. the D-ATIS text, if the owner accepts the third-party source;
  3. METAR wind with the 3-5-1 rule, as the fallback for snapshot mode.

  Visual vs ILS matters for the lighting work: approach-light intensity and PAPI use.

---------------------------------------------------------------------------------------------------------------------

## 5. Real-time sources (task d)

### 5.1 aviationweather.gov Data API (NOAA/NWS Aviation Weather Center) [V unless tagged]

Source: https://aviationweather.gov/data/api/ (page "v4.31"); OpenAPI https://aviationweather.gov/data/schema/openapi.yaml;
fetched 2026-09-24.

- Endpoints:
  - `GET /api/data/metar?ids=KSFO&format=raw|json|geojson|xml|iwxxm|decoded&hours=N` (default `hours` 1.5; `taf=true`
    adds the TAF; `date=`);
  - `GET /api/data/taf?ids=KSFO&format=…&time=valid|issue`;
  - also PIREP, SIGMET, G-AIRMET, CWA, station info.
- Quoted limits:
  - "The weather database currently allows access to up to the previous 30 days of data."
  - "All requests are rate limited to 100 requests per minute."
  - "Most endpoints return a maximum of 400 entries". Observed: `hours=720` returned 399 lines ending on 10 Sep, so it
    is capped **[M]**.
  - "Cross-origin resource sharing is not permitted at this time."
  - "Undocumented query parameter requests are restricted and will result in an error."
  - "Set a custom user agent to prevent automated filtering inadvertently blocking valid traffic."
  - "Exceeding request limits will result in access being blocked."
  - "Status code 204 is returned for valid requests with no data available."
- Cache files: `/data/cache/metars.cache.csv.gz` "Once a minute"; `tafs.cache.xml.gz` "Every 10 minutes".
- Response headers **[M]**: `cache-control: max-age=60`, an `etag`, no `access-control-allow-origin`.
- Latency **[M]**, 141 KSFO reports: METAR `receiptTime − obsTime` p10 4.1, median 4.2, p90 4.4 min (one COR 28.6 min).
  SPECIs 3.1–5.0 min.
  > **[corrected by verifier]** The percentiles are right (recomputed from `refs/cache/weather/metar_json_120h.json`
  > and a fresh 120 h fetch: p10 4.12, median 4.22, p90 4.39 min over 117 routine METARs). The outliers are wrong:
  > the 28.6 min report (`METAR KSFO 231456Z`) is **not** a COR (the only COR, `202356Z COR`, took 4.3 min), and
  > **9** routine METARs, about 8 %, arrived 6.6–28.6 min late (e.g. 200756Z 20.7 min, 210356Z 20.9 min). SPECIs were
  > 3.1–5.0 min except `SPECI KSFO 200301Z`, which arrived **89.4 min** late. The relay should keep polling after
  > hh:03 and must tolerate a missing routine METAR for up to about 30 min.
- Terms: NWS web content "is in the public domain, unless specifically noted otherwise, and may be used without charge
  for any lawful purpose so long as you do not: 1) claim it is your own …, 2) use it in a manner that implies an
  endorsement or affiliation with NOAA/NWS, or 3) modify its content and then present it as official government
  material." (https://www.weather.gov/disclaimer) **[V]**. AWC-specific terms beyond the API page's usage rules were not
  found **[NV]**.
- **Relay policy [I]:**
  - `/api/metar` fetches `metar?ids=KSFO&format=raw&hours=3` (and the TAF), with a UA of the form
    `sfo3d-relay/<ver> (<contact>)`.
  - Poll every 60 s from hh:59 to hh:03 (the routine METAR arrives about 4 min after :56), otherwise every 5 min to
    catch SPECIs. That is well under 1 request/min, against a limit of 100/min.
  - Honour `max-age=60` and the ETag.
  - Serve the last good report with its age.
  - Replay mode (already specified in `realtime_impl.md`) only uses reports observed at or before the replay time.

### 5.2 NWS API api.weather.gov [V]

Documentation: https://www.weather.gov/documentation/services-web-api (fetched 2026-09-24).

- Quotes:
  - "A User Agent is required to identify your application … If you include contact information (website or email), we
    can contact you if your string is associated to a security event. This will be replaced with an API key in the
    future."
  - "All of the information presented via the API is intended to be open data, free to use for any purpose."
  - "The rate limit is not public information, but allows a generous amount for typical use. If the rate limit is
    execeed a request will return with an error, and may be retried after the limit clears (typically within 5
    seconds). Proxies are more likely to reach the limit, whereas requests directly from clients are not likely."
- Observed **[M]**:
  - `access-control-allow-origin: *`; `cache-control: public, max-age=73, s-maxage=300`.
  - `/stations/KSFO/observations` returns **5-minute** observations (18:40–19:30Z) with `rawMessage` empty and
    `CLR` at 3,810 m, where the METAR said `SCT200`. So they are **unaugmented** sensor data.
  - Visibility read 6,437 m (4 SM) at 19:00–19:10Z. The 18:56Z METAR said 10SM, and no 4 SM value was sent as a METAR
    or SPECI.
- Use **[I]**: only for sub-hourly wind in the browser without the relay. Do not use it for clouds, visibility or
  weather.

### 5.3 D-ATIS (atis.info)

- **What the site publishes [V]**, https://atis.info/, API docs in the site bundle:
  - "Base URL https://atis.info/api … GET /stations … GET /all … GET /:airport … GET /history/:airport Returns the
    historical D-ATIS data for the specified airport (limited to the last 24 hours)."
  - The footer: "Do not use for real world flight planning or navigation."
  - The page and bundle carry **no terms of use, licence, attribution request, rate limit, or operator identity**.
    The site is behind Cloudflare.
  - `datis.clowd.io/api/KSFO` 302-redirects to it (`atc.md`).
  - Responses send `access-control-allow-origin: *` **[M]**.
- **Status.** The earlier "atis.info terms were unverified" is now "**no terms exist to verify**". It stays third party
  and optional; the owner decides (open question 3). Where the underlying FAA D-ATIS text comes from is **[NV]**.
- **Use [I].** Runway configuration and approach type (4.5), with the construction and closure notes. Never use it for
  wind (magnetic, 3.7).

### 5.4 Iowa Environmental Mesonet (IEM)

- Archive: `https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=SFO&data=metar&…`. Public domain,
  attribution appreciated **[V]**.
- A second request within about a minute returned "Too many requests from your IP address, slow down." **[M]**
- Rows tagged `IEM_GHCNH` are synthesised; drop them.
- Use: test fixtures and climatology only. Not needed live.

### 5.5 Marine-layer depth (optional live input)

- The Oakland (KOAK) radiosonde at 00Z/12Z gives the inversion base, which is the stratus top.
- Mirror: IEM `https://mesonet.agron.iastate.edu/json/raob.py?station=KOAK&ts=YYYYMMDDHHMM` (fetched for 2026-09-24 12Z,
  124 levels) **[M]**.
- The NWS primary distribution route was not checked **[NV]**. MIT ATC-319 used the "Oakland sounding" the same way
  **[V]**.
- Relay use **[I]**: fetch twice a day; use the inversion base for cloud thickness (3.3) and the wind at the cloud base
  for cloud drift (3.4).

---------------------------------------------------------------------------------------------------------------------

## 6. Recommendations (priority order)

1. **Replace `parseMetar`.** Port `tools/env/metar_decode.py` `decode_metar` to `js/live/wx/metar.js` and run the same 58
   fixtures in a node test. It fixes fractions, M/P prefixes, VV, RVR, weather groups and remarks. This is the only
   blocker for fog and rain rendering.
2. **Add the `/api/metar` relay endpoint as specified in 5.1.** Remove the browser fallback to aviationweather.gov in
   `feed.js`, which is blocked by CORS. Add `/api/taf`. `/api/datis` is optional (owner's call).
3. **Environment state from `render_params` (section 3)**, fed to the three.js r186 TSL renderer:
   - (a) σ from the ASOS day/night inversion; drop the 0.004 and 0.97 caps; treat 10SM as a bound;
   - (b) three-slab vertical profile: sub-cloud mist, cloud slab, clear air;
   - (c) N cloud layers with de-summed coverage and a per-layer shadow;
   - (d) exposure and ambient from the sun-visibility probability and K–C;
   - (e) GPU rain particles with Marshall–Palmer densities, streaks from the fall speed, drizzle as mist;
   - (f) wetness and puddle uniforms in the ground and objects shaders, using the Lagarde model;
   - (g) lightning flashes at the Table 13-7 rate;
   - (h) haze and smoke tint.
4. **Windsocks.** Direction from the METAR true wind; extension 0 at 3 kt and 1 at 15 kt (AC 150/5345-27F); gusts
   between `ff` and `G`; the envelope from PK WND. Positions go to the airfield-lighting and details work (OSM has
   only one).
5. **Runway configuration from observed ADS-B flow, not weather** (4.5). The METAR "below 2500/5" flag decides only
   whether visual approaches are possible.
6. **Snapshot mode.** Store the 3 METARs *and* the TAF with the snapshot (`data/snapshot.js` already has 3 METARs).
   Add a "weather presets" menu built from the real archive fixtures, such as "Fog 8 Nov 2025 13:56Z",
   "Squall 25 Dec 2025", "Marine layer 23 Sep 2026 07:56 PDT". The artifact then shows real SFO weather, not invented
   weather.
7. **QA views.** One harness view per weather regime:
   - summer stratus at 08:00 PDT from the tower;
   - fog at night from the 28R approach;
   - moderate rain on the apron;
   - clear sunset.

   Compare against reference photos, which must first be collected with licence notes.

---------------------------------------------------------------------------------------------------------------------

## 7. Open questions for the owner

1. **FMH-1 (2019).** The official PDF is in AWS cold storage and the Wayback Machine is blocked here. If you can
   download https://www.icams-portal.gov/resources/ofcm/fmh/FMH1/fmh1_2019.pdf in a browser, please share it. I will
   diff it against JO 7900.5E. No change is expected for the groups used.
2. **Kasten & Czeplak (1980).** Can you get the paper (Solar Energy 24:177–189) to confirm the exponent 3.4? Otherwise
   I will fit a curve to KSFO-area pyranometer data if you want one.
3. **D-ATIS via atis.info.** No terms are published. Do you accept a third-party, unlicensed feed for the runway
   configuration display with a "not for navigation" label, or should we rely on ADS-B flow only?
4. **Windsock positions and colour at SFO.** OSM has one. Should the airfield-lighting research survey them, e.g. from
   your Google Maps screenshots (reference only)?
5. **Drying rate and puddle look.** There is no authoritative source for SFO pavement drying. May I calibrate against
   webcam or photo sequences if you can point to a licensable source?
6. **Weather presets in the artifact.** Is a menu of real archived SFO weather (with the date shown) acceptable in
   snapshot mode, or should the artifact show only the recorded snapshot's weather?

---------------------------------------------------------------------------------------------------------------------

## 8. Files

| File | What |
|---|---|
| `tools/env/metar_decode.py` | Decoder (METAR/SPECI/TAF) + `render_params` + ASOS extinction inversion; CLI `--fetch`, `--render`, `--night` |
| `tools/env/test_metar_decode.py` | 38 unittest cases; `python3 tools/env/test_metar_decode.py` |
| `tools/env/fixtures/ksfo_recent_20260920_24.txt` | 30 KSFO reports from aviationweather.gov (fetched 2026-09-24T19:37:06Z) |
| `tools/env/fixtures/ksfo_archive_wx.txt` | 28 archived KSFO weather reports (IEM) |
| `tools/env/ksfo_climatology.py` | Section 4 tables; `--fetch` downloads the 10-year IEM file |
| `refs/cache/weather/` | Everything fetched: API pages and OpenAPI; JO 7900.5E; FMH-1 2005; ASOS guide; AC 150/5345-27F; MIT LL ATC-252/319; Rasmussen 1999; Garg & Nayar 2007; Lagarde; NCEI normals; flysfo pages; D-ATIS now and 24 h history; NWS obs, AFD and OAK sounding; IEM CSVs; climatology outputs |

## 9. Sources (all fetched 2026-09-24 unless noted)

- FAA Order JO 7900.5E w/ Chg 1: https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf.
  Registry: https://www.faa.gov/regulations_policies/orders_notices/index.cfm/go/document.information/documentID/1036970
- AIM (effective 7/9/2026, Change 3), chapter 7 section 1: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html
- FAA JO 7110.65 3-5-1 and 2-9-3: https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_5.html,
  https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap2_section_9.html
- FMH-1 2005 (mirror): https://met.nps.edu/~bcreasey/mr3222/files/labs/3-Fed-Met-Handbook-sfc-wx-obs-FMH1.pdf.
  The 2019 official URL is not retrievable (see 2.1).
- ASOS User's Guide (1998): https://www.weather.gov/media/asos/aum-toc.pdf
- aviationweather.gov Data API: https://aviationweather.gov/data/api/, https://aviationweather.gov/data/schema/openapi.yaml
- NWS API: https://www.weather.gov/documentation/services-web-api; NWS disclaimer: https://www.weather.gov/disclaimer
- Rasmussen et al. 1999: https://opensky.ucar.edu/system/files/2024-08/articles_15245.pdf
- WMO OSCAR MOR: https://space.oscar.wmo.int/variables/view/meteorological_optical_range_mor_surface; CIE: https://cie.co.at/eilvterm/17-31-018
- Garg & Nayar 2007: https://www.cs.columbia.edu/CAVE/publications/pdfs/Garg_IJCV07.pdf
- Lagarde 2013: https://seblagarde.wordpress.com/2013/04/14/water-drop-3b-physically-based-wet-surfaces/
- FAA AC 150/5345-27F: https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-27F-Wind-Cone.pdf
- MIT LL ATC-252 (1996): https://archive.ll.mit.edu/mission/aviation/publications/publication-files/atc-reports/atc-252.pdf.
  ATC-319 (2006): https://archive.ll.mit.edu/mission/aviation/publications/publication-files/atc-reports/Clark_2006_ATC-319_WW-15318.pdf
- flysfo.com runway constraints: https://www.flysfo.com/about/airport-operations/policies-regulations/runway-constraints.
  Construction alert: https://www.flysfo.com/flight-info/alerts-advisories/travel-impact-faa-reduced-arrival-rates-and-runway-construction
- FAA d-TPP 2609 SFO visual approach charts: cached in `refs/cache/atc/dtpp2609/00375quietbridge_vis28r.pdf` and
  `00375tipptoe_vis28lr.pdf` (see `atc.md` for the download URLs)
- NCEI 1991–2020 normals: https://www.ncei.noaa.gov/access/services/data/v1?dataset=normals-monthly-1991-2020&stations=USW00023234
- IEM ASOS archive and disclaimer: https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py, https://mesonet.agron.iastate.edu/disclaimer.php
- atis.info: https://atis.info/api/KSFO, https://atis.info/api/history/KSFO
- Secondary: MODIS–MISR r_eff (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6988446/); NASA S'COOL cloud-cover formula
  (https://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf)

---------------------------------------------------------------------------------------------------------------------

## Verification (adversarial check)

This check was run on 24 Sep 2026, 20:40–21:10Z, by an independent verifier. Every cited source that could be reached
was fetched again, into the verifier's scratch directory, not `refs/cache/`. The tools and tests were run again, and key
statistics were recomputed with an independent regex parser that does not use `metar_decode.py`. Nothing in `js/`,
`data/` or `tools/` was changed, and nothing was committed. Statements that turned out wrong are corrected inline above,
marked **[corrected by verifier]**.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | `js/livedata.js` `parseMetar` reads `M1/4SM` and `1 1/4SM` as 4 SM and `1/2SM` as 2 SM | **confirmed** | Ran in node: `visSM` = 4, 4 and 2. `3/4SM` also gives 4. With `VV002` the result has `clouds: []` and there is no gust field. The regex is `/\b(\d{1,2})SM\b/` (line 10). |
| 2 | Fog capped at 0.004 m⁻¹ and at 97 % opacity; the app uses 3.912/V | **confirmed** | `js/live/app.js:125,129`: `Math.max(800, visSM*1609)`, `Math.min(3.912/vis, 0.004)*0.9` (0.0036 in effect) and `fog.w = 0.97`. `js/shaders/common.js:64` has `T = max(T, 1.0 - uFog.w)`. The "app now" column of the 3.1 table recomputes exactly. |
| 3 | The live app renders one cloud layer (the lowest non-FEW) with an independent per-layer coverage | **confirmed** | `app.js` `main = layers.find(c => c.cover !== 'FEW')` feeds a single `uCloud` vec4, and `COVER` maps each amount separately. |
| 4 | aviationweather.gov: "Cross-origin resource sharing is not permitted at this time"; 100 requests/min; 400 entries; custom UA; 30 days; footer v4.31; no ACAO; `max-age=60` | **confirmed** | https://aviationweather.gov/data/api/ fetched again; all quotes match verbatim, footer "v4.31". A GET with `Origin: https://example.com` and an OPTIONS preflight both returned no `access-control-allow-origin`; `cache-control: max-age=60` and an `etag` are present. `js/live/feed.js:144` falls back to that URL, so it fails in a browser. The cache files update "Once a minute" and TAFs "Every 10 minutes" (verbatim). OpenAPI `version: "v4.0"`, and `wxString` is "Encoded present weather string". The cached `hours=720` response has 400 reports. |
| 5 | Median METAR latency 4.2 min (p10 4.1, p90 4.4); "one COR 28.6 min"; SPECIs 3.1–5.0 min | **partly refuted** | Percentiles confirmed: 4.12, 4.22 and 4.39 min over 117 routine METARs, in both the cached and a fresh 120 h JSON. However, the 28.6 min report is not a COR, 9 routine METARs took 6.6–28.6 min, and `SPECI KSFO 200301Z` took 89.4 min. Corrected in 1.8 and 5.1. |
| 6 | ASOS uses Koschmieder with ε = 0.055 by day and simplified Allard (I₀ = 25 cd, CDB = 0.084 mi⁻¹) at night (Rasmussen 1999) | **confirmed as quoted; constants are secondary** | https://opensky.ucar.edu/system/files/2024-08/articles_15245.pdf fetched again; §6c and the Fig. 24 caption quote match. The statements "a little less than twice" (0.5 mi) and "more than 2.4 times" (< 0.1 mi) also match, and my recomputation gives 1.97 and 2.45. The NWS algorithm specification was not located (web search), so the constants rest on this secondary paper. See the note in 3.1. |
| 7 | ASOS User's Guide: "1/2 to 1/3", "running 10-minute harmonic mean", "10 miles or greater", photocell at 0.5–3 fc, visibility sensors near the TDZ | **confirmed** | https://www.weather.gov/media/asos/aum-toc.pdf fetched again (918,728 bytes); all quoted. Caveat: the "1/2 to 1/3" ratio is not consistent with R99's constants above about 0.3 mi (note in 3.1). |
| 8 | Extinction table in 3.1 (day, night, ratio 1.17 → 2.44, and 2.68 at ⅛ SM; the ε = 0.02 and app columns) | **confirmed** | Recomputed every cell independently; all match to the printed precision. |
| 9 | WMO MOR 5 %, and CIE says the same | **confirmed** | WMO OSCAR page fetched again, definition verbatim. The CIE e-ILV 17-31-018 page says "attenuate by 95 %", which is equivalent. |
| 10 | JO 7900.5E: summation principle (10.4o / 10.7), wind "true" (13.10), VRB ≤ 6 kt, visibility coding, FG/BR/MIFG/BCFG/VC/HZ/FU definitions, squall, RVR increments, Table 13-7 lightning, ALDARS 5/10 NM, Tables 9-2/9-4, 13-5, 13-6, haze/smoke tints, SLP982, trace 60000, P-group, CIG 005V010, FG SCT000/FU BKN020, $, 12,000 ft limit | **confirmed** | https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf downloaded again (4,864,356 bytes) and text-searched. Every quote was found verbatim or with trivial differences ("1 minute" is verbatim in 9.4b). The summation text is at both 10.4o ("Summation Amount") and 10.7 ("Summation Layer Amount"), so both citations are valid. The registry page shows "Status Active" and cancels JO 7900.5D (2016-12-20). |
| 11 | AIM "Effective: 7/9/2026, Change 3"; 7-1 TAF/METAR key quotes (Plus6SM, 24/30 h, FM, RVR reporting) | **confirmed** | The AIM index and chap7_section_1 were fetched again; the quotes are verbatim. |
| 12 | FMH-1 2019 official PDF is in AWS DEEP_ARCHIVE; 2005 mirror has 5.5 %/5.0 % RVR tables | **confirmed** | The icams-portal URL returned 403 `InvalidObjectState … DEEP_ARCHIVE`. The met.nps.edu mirror is FCM-H1-2005 (September 2005), and both table titles are found. |
| 13 | Climatology tables 4.2, 4.3, 4.4, summer ceilings, clearing and onset times, FG by hour, RVR 28R only, remark counts | **confirmed** | `python3 tools/env/ksfo_climatology.py` run again on the cached IEM CSV reproduces every table exactly. An independent regex parser gives the same monthly "below 2500/5", the Jul/Aug hourly rows, FG ≤ 0.63 % (Jan), summer ceilings n = 6,389 / 700 / 1,100 / 1,900, clearing quartiles 09:56/10:56/11:56 with 25 never cleared, onset 18:56/20:56/22:56 on 281 days, tailwind ≥ 5 kt on 28 in 5.48 %, and HZ/FU clusters of 270/146/70 h. RA alone is 8.5–9.3 % Dec–Mar. |
| 14 | Routine METARs at :56 (87,533 of 87,672 hours); AUTO in 21 reports; `$` in 4,881 of 10,708 | **confirmed** | 87,533 hours have a :56 report; 10 years are 87,672 hours. `AUTO` appears in 21 reports (20 in the body). `$` appears in 4,881 of 10,708. |
| 15 | "FG BNK" never appears; "FG/FOG IN GAP W" 96 reports (42 in 2017, 31 in 2018; Aug 31, Jul 15) | **partly refuted (minor)** | 0 matches for `BNK` anywhere: confirmed. Of the 96, 2 are `FG IN GAP NW`, and the per-year and per-month figures come from routine METARs only (87 reports). Corrected in 2.4. |
| 16 | Other plain language: `VIS LWR W` 29×, `BINOVC` 13×, `A02` 76×, `CIG 030 RWY L10` (122) | **partly refuted (minor)** | `BINOVC` 13 and `A02` 76 confirmed. `VIS LWR W` is exactly 26×; 29 is all `VIS LWR` (corrected in 2.4). `CIG hhh RWY L10` appears 122×, of which `CIG 030` is 6; 122 is the count of the format, not of the example value. `CHINO RWY L10` appears 57×. |
| 17 | Hail GR/GS: 2 reports in 10 years | **refuted (minor)** | 3 reports, all SPECIs: `GRRA` (2024-03-02 04:48Z), `-RAGS` (2016-03-06) and `RAGS` (2017-01-23). Corrected in 3.5. |
| 18 | ATIS wind = METAR minus 10° in all 22 non-calm pairs, same speed | **confirmed** | https://atis.info/api/history/KSFO fetched again and paired with METARs. All 22 non-calm pairs in 23 Sep 19:56Z – 24 Sep 18:56Z show −10°, and the new 24 Sep 19:56Z broadcast also does (35008 ↔ 34008). 07:56Z was calm in both; at 08:56Z the ATIS said 00000KT against METAR 28003KT. AirNav variation "14E (2015)". |
| 19 | D-ATIS approach cycle (visuals → ILS 28R → ILS 28L → Quiet Bridge → visuals), VFR throughout, departures 28L/28R, "RY 1L, 1R CLSD" | **confirmed** | The broadcast-by-broadcast table reproduces the time bands exactly. None of the 25 METARs in the window had a ceiling below 3,000 ft or visibility below 5 SM. |
| 20 | flysfo.com: West Plan "95-98% of the time", Southeast "Less than 5%", 45 and 36 arrivals/h; alert "reopen in early October 2026" | **confirmed** | Both pages fetched again; the quotes are verbatim. Note: the alert does not name the runway. Linking it to 1L/1R comes from the D-ATIS and is **[I]**. |
| 21 | Quiet Bridge 28R "Orig 09JUL26" and Tipp Toe 28L/R "Amdt 3 24MAR22" minimums "SFO 2500'/5 or SFO 1000'/3 … eastern quadrant (030° to 120°)", SQL/San Mateo AWOS 2400'/5 | **confirmed** | https://aeronav.faa.gov/d-tpp/2609/00375quietbridge_vis28r.pdf and `…tipptoe_vis28lr.pdf` downloaded again, byte-identical to the cache. The text is verbatim, and the cycle is "SW-2, 03 SEP 2026 to 01 OCT 2026". |
| 22 | JO 7110.65 3-5-1 runway selection quote | **confirmed** | chap3_section_5.html fetched again; the quote is verbatim. |
| 23 | MIT LL ATC-252 and ATC-319 quotes | **confirmed** | Both PDFs downloaded again. The ATC-252 introduction has the quoted text verbatim ("25 June 1996", Clark & Wilson), as do the "5-15 miles", "3500 feet" and "must be staggered" passages. ATC-319 has "usually less than 1000 feet" and "base of the inversion height". |
| 24 | AC 150/5345-27F: 15 kt full extension; 3 kt / ±5°; Size 1/2 dimensions; white/yellow/orange; 2 fc; 27E cancelled | **confirmed** | The PDF was downloaded again. It is dated 12/15/2021 and the header says "Change: 1". Every quote is verbatim, including "AC 150/5345-27E … dated September 26, 2013, is canceled". |
| 25 | Garg & Nayar: Marshall–Palmer radius form and v = 200√a; table of drop densities | **quotes confirmed; N₀ unverifiable** | The quotes are verbatim. However, the diameter-form N₀ = 8,000 used in the table is 2× the conversion of the quoted formula. The original value (MP 1948, 0.08 cm⁻⁴) could not be fetched (AMS 403, Wikipedia 429). Corrected note in 3.5. |
| 26 | Lagarde 2013 quotes | **confirmed** | The post was fetched again; all seven quotes are verbatim. |
| 27 | NCEI 1991–2020 normals USW00023234: annual 19.64 in, 58.7 °F, monthly table | **confirmed** | The v1 API was queried again (monthly and annualseasonal). Name "SAN FRANCISCO INTL AP, CA US"; all values match, and the monthly values sum to 19.64. |
| 28 | Licences: IEM public domain, attribution appreciated; NWS disclaimer; NWS API UA and rate-limit quotes | **confirmed** | The disclaimer and API documentation pages were fetched again; the quotes are verbatim (including the site's "execeed" typo). |
| 29 | api.weather.gov and atis.info send `access-control-allow-origin: *` | **confirmed** | Both return `*` when an Origin header is sent. atis.info `/api/history` omitted the header when no Origin was sent, which is normal for browser CORS. |
| 30 | api.weather.gov serves 5-minute unaugmented observations (empty `rawMessage`, `CLR` 3,810 m vs METAR SCT200, spurious 4 SM) | **confirmed** | A fresh fetch shows 5-minute stamps with `rawMessage` "" and `CLR` at 3,810 m, while the 19:56Z METAR has SCT200. At 20:00Z it read 6,437 m while the METAR said 10SM, the same artefact. The `cache-control` differs per response (`max-age=300, s-maxage=120` today), so the printed value is one sample only. |
| 31 | atis.info publishes no terms, licence or rate limit | **confirmed (to the extent checkable)** | The SPA routes in the bundle are only `/`, `/:station` and `/api`. The only statement is "Do not use for real world flight planning or navigation." `/terms`, `/tos`, `/privacy` and `/about` all return the same 1,532-byte shell. |
| 32 | Station coordinates; 868 m E and 89 m N of the ARP | **confirmed** | api.weather.gov gives −122.36558, 37.61961, 3.048 m, and AWC stationinfo gives 37.61961, −122.36561, elev 2. `js/geo.js llToWorld` gives x = 868.4 and z = −89.3. |
| 33 | MTR AFD quotes of 24 Sep; OAK 12Z sounding 15.8 °C at the surface, 25.2 °C at 453 m | **confirmed** | The AFD issued 2026-09-24T17:33Z contains both quotes verbatim. IEM raob KOAK 202609241200: 15.8 °C at 3 m and 25.2 °C at 452.6 m. |
| 34 | NASA S'COOL "P = 990 (1-0.75F³)"; MODIS–MISR r_eff 4–17 µm; OSM windsock at 37.6245391, −122.3871016 | **confirmed** | The PDF was fetched again. PMC6988446 says "ranges from 4 to 17 μm". An Overpass query over SFO returns exactly one `aeroway=windsock` node at those coordinates. |
| 35 | Kasten & Czeplak exponent 3.4; Alduchov & Eskridge Magnus coefficients | **unverifiable** | The originals were not fetched; the report already tags both **[2nd]**. |
| 36 | IEM returns "Too many requests from your IP address" to a quick second query | **unverifiable** | Not re-tested, to avoid loading the shared service. |
| 37 | 38 tests pass; 30 + 28 real fixtures; mutation check (T-group +0.1 °C fails 33; visibility ×1.01 fails 42) | **confirmed** | `python3 tools/env/test_metar_decode.py`: 38 OK. All 30 recent fixtures appear verbatim in a fresh AWC 120 h fetch, and all 28 archive fixtures match IEM rows verbatim with the same timestamps. The two mutations were applied to scratch copies and gave exactly 33 and 42 failures. |
| 38 | Decoder sweep over 107,075 archive rows leaves only malformed rows unparsed | **confirmed** | 107,075 = 96,367 + 10,708 non-GHCNH rows. No exceptions; 19 rows have leftover tokens, all malformed (`9012 10`, TAF text stored as a METAR, `10SMSM`, `VRB/05`, `BKN0080`, `SCT1040`, `FWE025`, winds without `KT`). |

**Overall.** The report's key findings hold. The parser bug, fog caps, CORS block, ASOS day/night inversion, cumulative
cloud amounts, climatology, runway-use facts, ATIS magnetic wind and KSFO remark facts were all reproduced against
re-fetched primary sources or recomputed data. Corrections:
- the latency outliers: the 28.6 min report is not a COR, about 8 % of routine METARs are late, and one SPECI took 89 min;
- the hail count;
- the fog-in-gap and `VIS LWR W` breakdowns;
- the Marshall–Palmer N₀: the drop counts are 2× what the cited Garg & Nayar formula gives, and the textbook value used
  could not be fetched.

Caveats: the ASOS constants rest on Rasmussen 1999 (secondary) and disagree in size with the ASOS guide's "1/2 to 1/3".
The in-cloud σ range assumes that LWC and r_eff co-vary.
