# Gate truth: the gate SFO itself publishes for each flight, and what it says about our stands

Research for the "Parking" objective: the app labels a parked aircraft with the gate/stand its ADS-B position matches in
`data/sfo_stands.json`. This note finds an authoritative, internet-checkable source of the gate each flight actually
uses at SFO, reads its terms, tests our stand names and positions against it on live traffic, and recommends how to
show and validate gates in the app.

Written 24 Sep 2026 (UTC) by a research agent. Tool: `tools/live/gatecheck.py`. Third-party downloads are cached in
`refs/cache/gate_truth/` (gitignored). **Observed** = seen in a file or response I fetched (URL given). **Inferred** =
my interpretation. **Not verified** = could not be checked.

## 1. Answer in brief

- **The authoritative, internet-checkable source is SFO's own flight-status data.**
  - The page is https://www.flysfo.com/flight-info/flight-status. Its JSON is https://www.flysfo.com/flysfo/api/flight-status.
  - It gives every flight's **gate** and SFO's **stand allocation with times** (`stands[]`, AODB names such as `B24`, `E10U`, `12-5`). The stand list follows the aircraft through tows.
  - Anyone can check it in a browser. No key is needed.
  - Terms: **none published**. robots.txt does not exclude the path, and the only legal page is "Privacy & Cookie Use". It is an undocumented endpoint, not an offered API.
  - For a live relay, ask SFO first. For occasional verification, the tool fetches it gzip-compressed (0.5 MB), at most every 10 min.
- **Official gate lists.**
  - Printed terminal maps (flysfo.com/maps/static-maps): 114 gate labels. A1–A15, B1–B27, C1–C11, D1–D12, D14–D18, E2–E13, F5–F22, G1–G14.
  - DataSF dataset `chfu-j7tc` (PDDL, monthly): 106 gates used on 18–31 Aug 2026.
  - flysfo's stand names add 11 suffixed stands and 22 remote/hardstand codes.
- **Empirical test on 15 parked aircraft (00:30–01:50 PDT): our stand *names* equal SFO's numbers every time the geometry matched (10 of 10).**
  - Agreed with SFO's stand window: 5. With the gate: 1. Consistent by same-type allocation (no callsign): 2.
  - Geometry right but refused by our size limits: 2 (777-200 span bug in `types.js`; B5 wrongly class B).
  - No stand where SFO had one: 3. B24 is merged into our B25; the aircraft SFO had at C11 stood ~34 m from our C11 (and 30.5 m laterally off our C10) [corrected by verifier: was "C11 is ~31 m off"]; B16 is class B and 16 m off.
  - Inconclusive: 1 (E6, heading 37° off). Unverifiable: 1 (return to ramp).
- **Our stand *set* is incomplete.**
  - SFO's plan puts two aircraft at the same time on gates that we merge into one stand, for 13 gate pairs in 11 of our stands. F9 (185 operations in the 13 days of DataSF data, 18–31 Aug) is missing entirely. [corrected by verifier: was "two weeks"]
  - We have 89 contact stands against SFO's 106 used gate numbers.
- **Recommendation.**
  1. Fix the stand set: split, add F9, fix classes, fix the 777-200 span.
  2. Then show "Gate X · SFO" from the flysfo stand window through the relay (with SFO's permission), with our position match as a fallback and a verified tick when both agree.
  3. Give the owner one-click deep links to flysfo.com and FlightAware for manual checks.
  4. Run `gatecheck.py` on every recording as a QA metric.

## 2. Sources evaluated

| Source | What it gives | Real time? | Access | Terms (quoted, with URL) | Verdict |
|---|---|---|---|---|---|
| **flysfo.com flight status** (SFO's own site), JSON `https://www.flysfo.com/flysfo/api/flight-status` | Per flight: marketing callsign (e.g. `UAL2847`), **gate**, **stand allocation list with start/end times** (`stands[]`), terminal, belt, type, arr↔dep turn link. No registration. | Yes. `last_update` minute stamp; the snapshot spans about 4 h back to 12 h ahead. | No key. The official page https://www.flysfo.com/flight-info/flight-status loads it in the browser. About 10.6–11.6 MB of JSON; about 0.54 MB gzipped on the wire (the 0.23 MB figure is our own re-compressed cache file). [corrected by verifier] | **No terms of use found.** The footer links only "Privacy & Cookie Use" (https://www.flysfo.com/privacy-cookie-policy), and `/terms-of-use` returns 404. robots.txt (https://www.flysfo.com/robots.txt) does not disallow `/flysfo/api/`. The endpoint is undocumented, not a published API. | **Best source.** It is the airport's own gate and stand plan. Use for verification at low rates, and ask SFO before building a live dependency (§7). |
| **DataSF "SFO Gate and Stand Assignment Information"** (`chfu-j7tc`), https://data.sfgov.org/Transportation/SFO-Gate-and-Stand-Assignment-Information/chfu-j7tc | Actual time, airline, flight, ARR/DEP, terminal, **gate**, remark | No. "Publishing frequency: Monthly". Rows were observed from 2026-08-18 23:55 to 2026-08-31 23:59 (13,999 rows, loaded 2026-09-02). | Socrata API, no key | Licence **PDDL** (`"license": {"name": "Open Data Commons Public Domain Dedication and License"}`, metadata https://data.sf.gov/api/views/chfu-j7tc.json) | **Official and freely licensed**, but a month late and gates only. Good for the official gate-number list and usage counts, and for checking recorded days after the fact. |
| **SFO printable terminal maps**, https://www.flysfo.com/maps/static-maps | Passenger gate (hold-room) numbers per boarding area | n/a | PDF | Same site terms as above (none published) | **Official gate-number list** (§4) |
| **FlightAware website** (flight pages) | Gate and terminal per flight, when the airline or airport provides them | Yes | Browser only | "you may only access the Website with a human-operated interactive web browser and not with any program, collection agent, or "robot" … including … 'scraping'" and "All no-charge, web-based FlightAware products, APIs, and data are licensed solely for personal use". Last updated July 16, 2026. https://www.flightaware.com/about/termsofuse | **The owner can check by hand.** Automated use is not allowed. |
| **FlightAware AeroAPI** | `gate_origin`, `gate_destination`, `terminal_*` (OpenAPI spec https://www.flightaware.com/commercial/aeroapi/resources/aeroapi-openapi.yml). Gates only, no stands. | Yes | API key | Personal tier: "Per-query usage fees (up to $5 free per month, or $10 free per month for ADS-B feeders)", "10 result sets/minute", "Storage and distribution of derivative works for personal or academic purposes only". https://www.flightaware.com/commercial/aeroapi/ | A licensed option for the owner's own relay, within the free quota at low volume. Its gate source at SFO is not verified. |
| **AeroDataBox** | `gate`, `terminal`, `baggageBelt`, and **aircraft `reg`** per flight (OpenAPI https://doc.aerodatabox.com/docs/openapi-direct-v1.json) | Yes | API key (direct / API.Market / RapidAPI) | Pricing page (via WebFetch summary, not verbatim): free Basic trial of 400 units/month; "You cannot give, sell, or pass any third party access to the AeroDataBox API or to the data it returns." https://aerodatabox.com/pricing/ | Possible. It links tail number to flight, but it is not the only candidate: AeroAPI flight objects also carry `registration` ("Aircraft registration (tail number) of the aircraft, when known.", same OpenAPI spec as above) [corrected by verifier]. Gate coverage at SFO is **not verified**. |
| **Aviationstack** | Flight status; the FAQ mentions "terminals, gates" (via WebFetch summary) | Yes | API key | Free plan: "100 Requests", "Non-Commercial Use" (via WebFetch summary of https://aviationstack.com/pricing) | Too small a quota. Gate field **not verified** (docs page did not render). |
| **Cirium / FlightStats Flex** | Flight status with "terminal, gate and baggage carousel" (https://developer.flightstats.com/api-docs/flightstatus/v2/flight) | Yes | Account | Evaluation: "Free", "30-day trial period", "Maximum 20,000 total (lifetime)" calls (https://developer.flightstats.com/getting-started, via WebFetch) | Commercial. Evaluation only. |
| **United (united.com)** | Gate on flight status pages | Yes | Browser | **Not verified.** The terms page returned HTTP 503. | Manual check only |
| **FAA SWIM** | STDDS carries ASDE-X / ASSC / STARS / RVR / EFSTS / TDLS (https://www.faa.gov/air_traffic/technology/swim/stdds). None is a gate-assignment system. | Yes | SWIFT portal; approval needed | "CDM is provided on a limited basis from limited sources … Your request will be reviewed in accordance with FAA policy" (https://www.faa.gov/air_traffic/technology/swim/products/get_connected) | **Not a gate source** for us. That TFDM/CDM data would carry SFO gates is not verified. |

How the flysfo endpoint was found (observed):
- The page HTML loads `/modules/custom/flysfo_flight_status/js/dist/assets/index.js`.
- That bundle calls `/flysfo/api/flight-status`, `/flysfo/api/flight-status-update`, `/flysfo/api/system-terminals`, `/flysfo/api/checkins` and `/modules/custom/flysfo_flight_status/data/airlines.json`.
- The table's gate column reads `gate.gate_number`.
- At 07:32 UTC, `flight-status-update` returned byte-identical content to `flight-status`: the same `last_update`, 2,054 records.
- Response headers: `cache-control: must-revalidate, no-cache, private`, `x-generator: Drupal 11`.
- The page takes the query parameters `?type=departures|arrivals&search=<text>`. In the bundle, the initial `flight_kind` filter and `globalFilter` come from `location.search`. This makes a deep link like `https://www.flysfo.com/flight-info/flight-status?type=departures&search=2847`. *Observed in code, not tested in a browser* (Chromium was not allowed).

## 3. The flysfo record, and what "gate" and "stand" mean at SFO

One record, observed (`AS/3360/A/2026-09-23`), trimmed:
`"callsign":"ASA3360","gate":{"gate_number":"B7"},"stands":[{"stand":{"stand_name":"B7"},"start_time":"2026-09-23T20:22:00-07:00","end_time":"2026-09-23T21:21:00-07:00"}],"linked_flight_id":"AS/3306/D/2026-09-23","aircraft_transport_type":{"icao_code":"E75L"}`.

- **Records.** The 07:32 UTC snapshot had 2,054 records.
  - 631 are operating flights; the rest are code-share duplicates with `is_code_share: true`.
  - Scheduled block times run from 23 Sep 20:33 to 24 Sep 12:30 PDT.
- **Callsign.** The callsign is the *marketing* carrier's ICAO code plus the flight number. For example, SkyWest-operated United Express appears as `UAL5339`, while its ADS-B callsign is `SKW…`. The tool matches regional operators (SKW, RPA, ASH, ENY, QXE…) by flight number.
- **`stands[]`.** This lists the aircraft's stand allocations for the whole turn, with times. The arrival and the linked departure carry the same list.
  - Example: AC745/AC738 is `[C10 21:04–06:30, D11 07:00–08:30]`, which is a tow from C10 to D11.
  - Counts: 462 flights have 1 stand, 56 have 2, 15 have 3, and 98 have none (mostly future flights).
- **Gate vs stand (observed).**
  - For single-stand flights, the stand base name equals the gate number in 383 of 407 cases in the 07:32 snapshot, and 462 of 488 in the three snapshots merged.
  - Of the 24 exceptions in the 07:32 snapshot, 23 were flights still to come. Examples: UA1329 has gate D15 but stand D6; UA2158 has gate E3 but stand G104; UA5790 has gate F9 but stand 6-4.
  - *Inferred:* passenger gates and the stand plan are maintained separately and can disagree for future flights. The stand window covering "now" is the better truth for a parked aircraft.
- **Stand names SFO uses** (all snapshots so far):
  - Contact stands are named like the gates. Some have a suffix letter: `A1V A4T A13V B5S B11S B16S C9V E10U E11U E13T G13S`.
    - The suffixed stand is never occupied at the same time as its base stand: 0 overlaps for B5S/B5, B11S/B11, B16S/B16 and C9V/C9 across the three snapshots. The other bases were not seen together with their suffix.
    - Several suffixed stands take wider aircraft than their base stand (observed in the feed):
      - `B5S` takes an A359 (Starlux JX11) where `B5` takes A321s;
      - `B11S` takes an A332 where `B11` takes an A319 or A320;
      - `B16S` takes a B763 or B77W where `B16` takes an A321, B738 or B739;
      - `C9V` takes a B763 or B76W where `C9` takes a B752.
    - *Inferred:* the suffix marks an alternative stop position of the same stand, often a wide-body one (MARS style). The meaning of the letters is **not verified**; searches found no public definition.
  - Remote stands: `2-1 2-2A 2-2B 6-1 6-2 6-4 9-5 9-6 12-1…12-5 41-08 41-09A 41-11 41-13 41-16 41-18 41-21 G104 G105`.
    - *Inferred:* `<plot>-<n>` hardstands, where 41 is probably the United maintenance area. Their locations are **not verified**.
    - G104/G105 match our remote stands G104/G105. Our G103 was not seen.

## 4. Official gate numbers per boarding area vs our stand names

Sources:
- **Map**: gate labels printed in the map area of the official terminal maps, extracted from the PDFs by `gatecheck.py gates` and checked visually.
  - T1: https://www.flysfo.com/sites/default/files/2025-11/251027_SFO_Tabloid_Face%20A_T1_Web.pdf (effective 11/2025).
  - T2: https://www.flysfo.com/sites/default/files/2025-11/251027_SFO_Tabloid_Face%20A_T2_Web.pdf.
  - T3: https://www.flysfo.com/sites/default/files/2025-11/251027_SFO_Tabloid_Face%20A_T3_Web.pdf.
  - INTL: https://www.flysfo.com/sites/default/files/2026-09/260701_SFO_Tabloid_Face%20A_INTL_WEB.pdf (effective 7/2026).
- **DataSF**: gates with operations 18–31 Aug 2026, with the count of operations.
- **AODB**: stand names in the flysfo feed.

Counts in the first column: map / DataSF / AODB / ours. DataSF entries are `gate·operations`.

| Area | Official map gates | DataSF gates used 18–31 Aug 2026 (ops) | AODB stand names (flysfo, 3 snapshots 24 Sep) | Ours: stand (aliases) |
|---|---|---|---|---|
| A (15/12/12/10) | A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14 A15 | A1·79 A2·91 A4·51 A5·58 A6·92 A8·102 A9·79 A10·83 A11·87 A12·82 A13·63 A15·55 | A1V A2 A4T A5 A6 A8 A9 A10 A11 A12 A13V A15 | A1 A2 A3(A4) A5 A6(A7) A8 A9 A10 A11(A13) A15(A12/A14) |
| B (27/26/29/22) | B1 B2 B3 B4 B5 B6 B7 B8 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | B2·82 B3·180 B4·25 B5·63 B6·173 B7·195 B8·165 B9·175 B10·32 B11·81 B12·153 B13·156 B14·122 B15·44 B16·63 B17·174 B18·147 B19·95 B20·114 B21·135 B22·172 B23·155 B24·135 B25·159 B26·129 B27·119 | B2 B3 B4 B5 B5S B6 B7 B8 B9 B10 B11 B11S B12 B13 B14 B15 B16 B16S B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 | B1 B2 B3 B4 B5 B6(B7/B8) B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19(B20) B21 B23(B22) B25(B24) B26 B27 |
| C (11/10/11/9) | C1 C2 C3 C4 C5 C6 C7 C8 C9 C10 C11 | C1·144 C3·147 C4·129 C5·161 C6·170 C7·150 C8·139 C9·152 C10·47 C11·87 | C1 C3 C4 C5 C6 C7 C8 C9 C9V C10 C11 | C1 C3 C4 C5 C6 C7(C9) C8 C10 C11 |
| D (17/14/14/13) | D1 D2 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 D17 D18 | D1·195 D3·237 D4·220 D5·187 D6·140 D7·162 D8·155 D9·167 D10·167 D11·159 D12·171 D14·177 D15·168 D16·162 | D1 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D14 D15 D16 | D1(D2) D3 D4 D5(D6) D7 D8 D9 D10 D11 D12 D14 D15 D16 |
| E (12/12/12/10) | E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 | E2·170 E3·167 E4·189 E5·182 E6·178 E7·194 E8·168 E9·171 E10·180 E11·180 E12·175 E13·162 | E2 E3 E4 E5 E6 E7 E8 E9 E10U E11U E12 E13T | E3(E2) E4 E5 E6 E7 E8 E9 E10 E11 E13(E12) |
| F (18/18/18/14) | F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | F5·207 F6·218 F7·196 F8·176 F9·185 F10·169 F11·127 F12·170 F13·123 F14·158 F15·115 F16·161 F17·160 F18·83 F19·146 F20·159 F21·156 F22·122 | F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 | F5 F6 F8(F7) F10 F11 F12 F13 F14 F15 F16 F17(F18) F19 F20 F22(F21) |
| G (14/14/13/14) | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G11 G12 G13 G14 | G1·86 G2·102 G3·69 G4·97 G5·105 G6·110 G7·56 G8·101 G9·98 G10·96 G11·18 G12·45 G13·108 G14·3 | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10 G13S G104 G105 | G1 G2 G3 G4 G5 G6 G7 G8 G9 G10(G14) G12(G11/G13) G103 G104 G105 |


Reading the table:
- **Where names agree.** Where a stand of ours exists, its name is an official gate number. The exceptions are A3 and B1: both are hold-room labels on the maps, but neither is used as a stand in DataSF or AODB. G103 is not seen anywhere.
- **Merged stands.** Other official numbers exist in our data only as an *alias* of another stand: A4, A7, A12, A13, A14, B7, B8, B20, B22, B24, C9, D2, D6, E2, E12, F7, F18, F21, G11, G13 and G14.
- **Proof that some merges are wrong.** SFO's stand plan puts two different aircraft (different turns) on two members of one of our merged stands **at the same time**, overlapping by more than 10 minutes (see the next table). This proves they are physically separate stands.
  - Of those overlaps, the ones already under way when a snapshot was taken are the strongest evidence. They cover **13 gate pairs in 11 of our stands**: A11|A13, A12|A15, B6|B7, B6|B8, B7|B8, B19|B20, B22|B23, B24|B25, C7|C9, D5|D6, E2|E3, F7|F8 and F17|F18.
  - For E12|E13 and F21|F22 the overlap is only planned (future).
  - For A3|A4, A6|A7, D1|D2, G10|G14 and G11|G12|G13 there is no evidence either way yet.
- **Missing stands.** Map gates missing from our data altogether: C2, D17, D18, F9. **F9 had 185 operations in two weeks**, and C2, D17 and D18 had none.

| Our stand (class, src) | Gate pair | Allocations seen | Simultaneous (>10 min, different turns) | of which already under way at fetch | Example (PDT; AODB stand, type) |
|---|---|---|---|---|---|
| G10 (EL, obs) | G10/G14 | 5/0 | 0 | 0 | - |
| G12 (EL, obs) | G12/G11 | 0/0 | 0 | 0 | - |
| G12 (EL, obs) | G12/G13 | 0/7 | 0 | 0 | - |
| G12 (EL, obs) | G11/G13 | 0/7 | 0 | 0 | - |
| A3 (EL, inf) | A3/A4 | 0/2 | 0 | 0 | - |
| A6 (EL, obs) | A6/A7 | 2/0 | 0 | 0 | - |
| A11 (EL, obs) | A11/A13 | 4/2 | **3** (2 distinct turn pairs) [corrected by verifier] | 2 (1 distinct: PR104/105 A35K at A11 with OZ211 A359 at A13V, 23 20:57–23:33) [corrected by verifier] | 24 10:45–24 12:25: JL/1/D/2026-09-24 at A11 (B77W) and TK/289/A/2026-09-24 at A13V (A359) |
| A15 (C, obs) | A15/A12 | 2/3 | **3** | 2 | 23 21:12–23 22:54: AM/664/A/2026-09-23 at A15 (B738) and LO/37/A/2026-09-23 at A12 (B788) |
| A15 (C, obs) | A15/A14 | 2/0 | 0 | 0 | - |
| A15 (C, obs) | A12/A14 | 3/0 | 0 | 0 | - |
| C7 (CL, obs) | C7/C9 | 5/3 | **4** | 2 | 24 09:53–24 10:29: DL/1053/A/2026-09-24 at C7 (BCS3) and DL/668/A/2026-09-24 at C9V (B76W) |
| B19 (B, inf) | B19/B20 | 3/3 | **2** | 1 | 23 22:27–23 23:15: DL/681/A/2026-09-23 at B19 (A321) and AA/1430/A/2026-09-23 at B20 (A321) |
| B23 (C, obs) | B23/B22 | 6/8 | **3** | 1 | 24 12:39–24 13:27: AA/1851/A/2026-09-24 at B23 (A321) and AA/1022/D/2026-09-24 at B22 (B738) |
| B25 (C, inf) | B25/B24 | 6/5 | **6** | 2 | 24 11:48–24 12:19: AA/2334/D/2026-09-24 at B25 (B738) and AA/166/D/2026-09-24 at B24 (A321) |
| B6 (C, obs) | B6/B7 | 4/4 | **4** | 2 | 24 08:46–24 09:27: AS/3007/D/2026-09-24 at B6 (E75L) and AS/1501/A/2026-09-24 at B7 (B738) |
| B6 (C, obs) | B6/B8 | 4/5 | **4** | 2 | 24 07:00–24 08:23: AS/1411/D/2026-09-24 at B6 (B739) and AS/424/D/2026-09-24 at B8 (B39M) |
| B6 (C, obs) | B7/B8 | 4/5 | **3** | 2 | 23 21:03–23 21:21: AS/3306/D/2026-09-23 at B7 (E75L) and AS/2362/A/2026-09-23 at B8 (E75L) |
| D5 (C, obs) | D5/D6 | 7/6 | **4** | 2 | 23 21:13–23 22:39: UA/412/D/2026-09-23 at D5 (A319) and WN/1330/A/2026-09-23 at D6 (B738) |
| D1 (C, obs) | D1/D2 | 5/0 | 0 | 0 | - |
| E13 (C, obs) | E13/E12 | 1/5 | **1** | 0 | 24 12:53–24 13:50: UA/1791/D/2026-09-24 at E13T (B39M) and UA/5218/A/2026-09-24 at E12 (E75L) |
| E3 (C, inf) | E3/E2 | 5/6 | **6** | 1 | 24 13:14–24 13:50: UA/4734/A/2026-09-24 at E3 (E75L) and UA/4715/D/2026-09-24 at E2 (E75L) |
| F22 (E, obs) | F22/F21 | 3/7 | **1** | 0 | 24 09:04–24 10:10: UA/246/A/2026-09-24 at F22 (B753) and UA/1372/A/2026-09-24 at F21 (B39M) |
| F17 (D, obs) | F17/F18 | 7/5 | **3** | 1 | 24 09:24–24 10:08: UA/1164/D/2026-09-24 at F17 (B39M) and UA/5502/A/2026-09-24 at F18 (CRJ2) |
| F8 (B, obs) | F8/F7 | 6/4 | **4** | 1 | 23 20:06–23 20:43: UA/5392/D/2026-09-24 at F8 (E75L) and UA/5256/A/2026-09-23 at F7 (E75L) |

## 5. Empirical check: parked aircraft now, ADS-B vs SFO's published stand

Method:
- **ADS-B.** The recorder ran 07:27–08:53 UTC on 24 Sep 2026 (00:27–01:53 PDT: late arrivals and the international departure bank).
  - `gatecheck.py check --every 60 --still 60 --js` evaluated every minute.
  - A parked aircraft is on the ground, below 1 kt and stationary for 60 s or more.
  - Its position is the median of its stationary reports over the last 5 min.
- **SFO.** Three flysfo snapshots, merged (07:32, 08:14 and 08:53 UTC; `last_update` "Sep 24 at 12:32 am" to "01:52 am").
- **Stand matching** is the app's own algorithm. Running the app's JS `Traffic.matchGate` in node on the same 30 evaluated reports gave **the same stand in 30/30**.
- **Excluded:** 13 evaluations of aircraft that were off-stand: pushed back and waiting (PAL105, CAL003, EVA027, EVA017, SJX011, ANA107, CMP383, UAL189 after push, UAL2847 after push), or holding in the alley (UAL1146, N533DT, N990AK), or UAL1947 at 07:37 stopped ~77 m short of D16 before pulling in. [corrected by verifier: was 12; the UAL1947 07:37 row was not listed]
- Raw rows: `refs/cache/gate_truth/check_20260924.json` (gitignored).

| # | UTC (PDT) | Flight (ADS-B callsign) | Reg | Type | Published by SFO (flysfo): gate / stand at that time | Our matched stand (aliases), src/class | Offset from our stand's expected antenna point: lateral / along / distance (m) | Agree? |
|---|---|---|---|---|---|---|---|---|
| 1 | 07:30 (00:30) | .N968JT | N968JT | A321 | no callsign; stand allocation at our stand: B18: B6/116/D/2026-09-24 (A321), B18: B6/277/A/2026-09-23 (A321) | B18, inf/C | +5.0 / -4.8 / 6.9 | occupancy-type-match |
| 2 | 07:30 (00:30) | AAL2506 | N437AN | A21N | gate B24 / stand B24 (AA/2506/A/2026-09-23; AA/2722/D/2026-09-24) | none (nearest B25) | +26.1 / -3.0 / 26.3 | no-match |
| 3 | 07:30 (00:30) | AAL2856 | N980UY | A321 | gate B23 / stand B23 (AA/2856/A/2026-09-23; AA/304/D/2026-09-24) | B23 (B22), obs/C | +4.0 / -4.7 / 6.2 | agree |
| 4 | 07:30 (00:30) | ACA738 | C-FDUW | BCS3 | gate C10/D11 / stand C10 (AC/745/A/2026-09-23; AC/738/D/2026-09-24) | C10, inf/C | -5.6 / -4.4 / 7.1 | agree |
| 5 | 07:30 (00:30) | DAL2635 | N316DU | BCS3 | gate C11 / stand C11 (DL/2635/A/2026-09-23; DL/2721/D/2026-09-24) | none (nearest C10) | +30.5 / -4.1 / 30.8 | no-match |
| 6 | 07:30 (00:30) | JBU515 | N937JB | A321 | gate B21 / stand B21 (B6/515/A/2026-09-23; B6/434/D/2026-09-24) | B21, inf/C | +6.0 / -10.6 / 12.2 | agree |
| 7 | 07:30 (00:30) | UAL2847 | N14541 | A21N | gate D8 / stand - (UA/2123/A/2026-09-23; UA/2847/D/2026-09-24) | D8, obs/C | +1.1 / -10.3 / 10.4 | agree (gate) |
| 8 | 07:31 (00:31) | (none) | N161AA | A321 | no callsign; stand allocation at our stand: B26: AA/2116/D/2026-09-24 (A321), B26: AA/2522/A/2026-09-23 (A321) | B26, obs/CL | +3.7 / -7.1 / 8.0 | occupancy-type-match |
| 9 | 07:37 (00:37) | UAL189 | N2341U | B77W | gate G5 / stand G5 (UA/189/D/2026-09-24) | G5, obs/EL | +1.8 / -5.5 / 5.8 | agree |
| 10 | 07:44 (00:44) | UAL367 | N47450 | B39M | gate E6 / stand E6 (UA/367/A/2026-09-24; UA/2168/D/2026-09-24) | none (nearest E6) | +11.3 / -7.9 / 13.8 | no-match |
| 11 | 07:46 (00:46) | UAL604 | N776UA | B772 | gate F22 / stand - (UA/604/D/2026-09-24) | none (nearest F22) | -0.4 / -2.1 / 2.1 | class-rejected (geometry matches F22, published gate F22) |
| 12 | 07:49 (00:49) | AAL177 | N107NN | A321 | gate B16 / stand B16 (AA/177/A/2026-09-24; AA/234/D/2026-09-24) | none (nearest B16) | -15.8 / -11.1 / 19.3 | no-match |
| 13 | 08:03 (01:03) | UAL1947 | N57478 | B39M | gate - / stand - | D16, obs/C | +5.8 / +0.6 / 5.8 | no allocation at our stand; same-type allocations: 12-2,A12,B15,B6,B8,E6 |
| 14 | 08:18 (01:18) | UAL2106 | N47446 | B39M | gate E10 / stand E10U (UA/2106/A/2026-09-24; UA/2647/D/2026-09-24) | E10, obs/C | +2.7 / +4.7 / 5.4 | agree |
| 15 | 08:50 (01:50) | JBU413 | N943JT | A321 | gate B5 / stand B5 (B6/413/A/2026-09-24; B6/316/D/2026-09-24) | none (nearest B5) | -0.2 / -1.8 / 1.8 | no-match (class-rejected; geometry matches B5) |

Reading it:
- **Names: no wrong name in 15 aircraft.** Whenever our geometry matched a parked aircraft, the stand's name was the one SFO publishes for that aircraft.
  - With a stand window from SFO: #3 B23, #4 C10, #6 B21, #9 G5, #14 E10 (SFO: E10U).
  - With the gate: #7 D8.
  - Through SFO's allocation of the same airline and type to that stand (no callsign on the transponder): #1 B18 and #8 B26.
  - Geometry matched but the app refused the aircraft type: #11 F22 and #15 B5.
  - This answers the task's question: **our stand names are SFO's official gate numbers**, not merely nearby hold rooms, at least for these 10 stands.
- **Failures come from the stand set, class limits and aircraft size, not from names.**
  - **#2 B24 (A21N): no stand.** Our B24 is an alias of B25. The aircraft stood 26 m beside our B25 and 23 m beside our B23. SFO had it on B24 while an E175 was on B25, so B24 is a separate stand.
    - Observed anchor: 37.610126 N, 122.386249 W (world −955.1, 963.3), NACp 9, 41 reports with a 1.3 m spread at 07:30. No heading was reported.
  - **#5 C11 (BCS3): no stand.** The aircraft stood 30.5 m laterally from our C10, with its true heading 5.3° off C10's, and about 34 m from our C11 (whose heading, 244.0°, is 48.5° off the reported 292.5°) [corrected by verifier: was "within 5°" and "33 m"]. It is not at the place our C11 describes, and our C10/C11 geometry needs re-survey.
    - Observed anchor: median antenna position 37.614853 N, 122.381844 W (world −566.7, 438.7), true heading 292.5°, NACp 10, 70 reports.
  - **#12 B16 (A321): no stand.**
    - Our B16 is class B (CRJ/E175, span ≤ 28.5 m), but SFO parks A321s there (AA177 and AA234; DL B739 on 23 Sep).
    - The aircraft was also 15.8 m laterally off our lead-in, heading 101°.
    - SFO's `B16S` variant takes a B763 or B77W.
    - Observed anchor: 37.611625 N, 122.386188 W (world −949.8, 797.0), heading 101°. This one is noisy: the reports spread over 35 m.
  - **#15 B5 (A321): position matches (0.2 m / 1.8 m), refused by class.** Our B5 is class B. SFO parks JetBlue A321s on B5 and an A359 on `B5S`. [corrected by verifier: "geometry perfect" overstated — the reported true heading is 53.4° vs our B5's inferred 27.8° (25.6° off, inside the app's 35° gate), from only 6 stationary reports at the end of the recording; B5's heading may also need checking.]
  - **#11 F22 (B772): geometry matches (0.4 m / 2.1 m, heading 2.5° off), refused by class.** This is the `types.js` 777-200 span bug (§6.1). Our stand was right. [corrected by verifier: heading was given as 2°]
  - **#10 E6 (B39M): inconclusive.**
    - The aircraft stopped at a true heading of 154.7°, 37° off our E6 heading (117.8°), 11 m laterally, and its transponder went off about 15 s after it stopped (gs 0.2 kt at 07:43:24, last report 07:43:38 UTC) [corrected by verifier: was "1 min later"].
    - Our E6 is `inf`, with the grid heading. The observed stands on that side have 139.6° (E10) and 154.7° (E13), so E6's heading is probably wrong (inferred).
  - **#13 D16 (UAL1947): unverifiable.**
    - UA1947 SFO→MCO went off block at 23:58 PDT but has no airborne time in the feed. ADS-B shows it taxiing near the runway 28 ends at 07:31 UTC and back on the ramp at our D16 by 07:40.
    - All three snapshots still show it "Departing" from E10 (stand E10U until 23:58), and no stand at D16 until 06:53.
    - Inferred: a return to the ramp that the feed did not reflect. **The published data can lag irregular operations.**
    - [added by verifier] ADS-B also shows it left D16 at ~08:04 UTC, taxied back to the runway 28 ends by 08:16 and departed at ~08:20 UTC (01:20 PDT); it was at 18,100 ft (baro) about 75 km south-east of SFO by 08:30. A fresh flysfo snapshot at 09:34 UTC (`last_update` "Sep 24 at 02:30 am") still shows UA1947 "Departing" from E10 with no runway time, which strengthens the lag finding.
- **Position error of a correct match.**
  - Lateral: |mean| 3.0 m, max 6.0 m (n = 10: the agreeing and geometry-only rows).
  - Along the lead-in: mean **−4.7 m**, median −4.8 m, range −10.6 to +4.7 m. Negative means the report lies ahead of the expected antenna point (nose − 0.2·L).
  - Parked reports scatter by up to about 31 m (AAL2506: NACp 8–9; largest bounding-box side of its gs < 1 kt reports in a 20-min window from 07:51 UTC; 37 m diagonal over 07:28–08:52) [corrected by verifier: was "about 27 m"]. The app should therefore match on a robust, median position rather than on the latest report.

## 6. Recommendation for showing and validating gates live

### 6.1 First fix the stand set; our names are SFO's gate numbers

This is advice for whoever owns `data/` and `tools/sat/`. I did not change them.

- **Names.** Keep naming stands by SFO gate number.
  - Every one of our stands that a parked aircraft matched carried the number SFO publishes for that aircraft (§5).
  - Where our data differs, the difference is merging, not misnaming.
- **Split the stands proven separate** by simultaneous allocations already under way (§4): B6|B7|B8, B19|B20, B22|B23, B24|B25, C7|C9, D5|D6, E2|E3, F7|F8, F17|F18, A11|A13 and A12|A15.
  - E12|E13 and F21|F22 are likely too: SFO plans simultaneous use, but only in the future so far.
  - Each needs its own lead-in, stop point, class and bridge.
  - Where a wide-body position overlaps two narrow-body positions (MARS style: F17 takes a B39M while F18 takes a CRJ2), model them as overlapping stands. The existing "an oversize aircraft blocks its neighbours" logic can then arbitrate.
  - The ADS-B positions in §5 of aircraft SFO places at B24 and C11 are observed anchors for two of these missing stands.
- **Add F9.** It is on the T3 map and had 185 operations in 13 days (18 Aug 23:55 – 31 Aug 23:59) [corrected by verifier: was "14 days"].
- **Rename and prune.**
  - A3 → A4: A3 is only a hold-room label, and SFO's stand is A4 or A4T.
  - B1: no operations; keep it as a sign only.
  - C2, D17 and D18 are hold-room labels only (no operations).
- **Suffixed stand names.** Display A1V, A4T, A13V, B5S, B11S, B16S, C9V, E10U, E11U, E13T and G13S by their base gate number. Inferred: they are alternative stop positions of the same stand.
- **Remote stands.** SFO uses 2-1, 2-2A, 2-2B, 6-1, 6-2, 6-4, 9-5, 9-6, 12-1…12-5, 41-08…41-21, G104 and G105. We have only G103–G105, and G103 was not seen.
  - Survey them from live data. When SFO's window says an aircraft is on remote stand X and ADS-B shows it stationary, the position is an **observed** stand position, independent of imagery. For example, a new `src: 'obs-live'`.
  - The `--json` rows of `gatecheck.py` already carry `published_stand`, lat/lon, heading and type for this. Running it on each day's recording would build the set.
- **Aircraft size table (`js/aircraft/types.js`).**
  - `TYPES.b772` is derived from `b77w` and keeps the 777-300ER span of 64.8 m.
  - The 777-200 span is **199 ft 11 in (60.93 m)**, and its length is 209 ft 1 in (63.73 m). Source: Boeing D6-58329, *777-200/300 Airplane Characteristics for Airport Planning*, §2.2.1, p. 15, read from the mirror http://wpage.unina.it/fabrnico/DIDATTICA/PGV/Specifiche_Esercitazioni/B777/Manuale%20777_23.pdf. Boeing's own URL, https://www.boeing.com/content/dam/boeing/boeingdotcom/commercial/airports/acaps/777-200-200ER-300_Rev_E.pdf, returned 404 to me.
    - [corrected by verifier] Boeing's original is available at the current path https://www.boeing.com/content/dam/boeing/v2/airports/acaps/777-200-200ER-300_Rev_E.pdf (linked from https://www.boeing.com/commercial/airports/plan-manuals). D6-58329 **Rev E, December 2024**, §2.2.1 "General Dimensions: Model 777-200", p. 2-8, shows the same 199 FT 11 IN (60.93 M) span and 209 FT 1 IN (63.73 M) length. Cite Boeing, not the mirror.
  - As a result, `standFits` refuses every 777-200/-200ER at class-E stands. Observed: UAL604 (B772) stood 0.4 m off the F22 lead-in with its heading 2.5° off [corrected by verifier: was "within 2°"], SFO had it at F22, and the app matched nothing.
  - `B77L` (777-200LR/F, 64.8 m) is right as it is. [corrected by verifier] But `B77L` has no type of its own: it maps to `TYPES.b772` in both `ICAO_MAP` (`js/aircraft/types.js`) and `TYPE_MODELS` (`js/live/aircraft.js`). Setting the `b772` span to 60.93 m on its own would therefore make every B77L 60.93 m. B77L needs a separate entry with the 777-200LR span of 212 ft 7 in (64.80 m), per Boeing D6-58329-2 Rev G §2.2.1, p. 2-3 (https://www.boeing.com/content/dam/boeing/v2/airports/acaps/777-200LR-300ER-F_Rev_G.pdf).
- **ADS-B reference point.** On the contact stands that agreed, the report was on average **4.7 m ahead** of where the app expects the antenna (nose − 0.2·L). The median is 4.8 m; n = 10; the along-track errors range from −10.6 to +4.7 m.
  - Either `ANT = 0.2` is too large for narrow-bodies or the stop points sit too far back.
  - The sample is small. Re-measure with more days before changing `ANT`.

### 6.2 Live gate label in the app

1. **Relay (`sfo_live_server.py`).** Add `/api/gates`. **Only after SFO agrees (§7)**, or as an owner-only opt-in at human page-view rates.
   - It fetches `https://www.flysfo.com/flysfo/api/flight-status` with gzip (~0.5 MB) at most every 10 minutes, and keeps the last copy.
   - It serves:
     - `byCallsign`: ICAO callsign → `{arr, dep: {flight, gate, stands: [{name, from, to}]}}`, with the regional-operator mapping by flight number;
     - `byStand`: stand → the turn allocated there now.
2. **Order of truth for a parked aircraft's label.** Always show the source.
   1. The SFO stand window that covers now, for this aircraft's callsign: "Gate B23 · SFO".
      - If our matched stand agrees, add a tick.
      - If it disagrees, show SFO's number and log a data defect. Do not silently snap.
   2. Otherwise the gate of its arrival or next departure: "Gate D8 · SFO (gate)".
   3. Otherwise our position match: "Stand B18 · from position".
3. **Tie-breaking.** Use SFO's stand as a prior in `matchGate` only when the ADS-B position is ambiguous between neighbouring stands that both pass the geometry test. Never override geometry.
4. **Identity.** The flysfo data has no registrations, so the callsign is the key.
   - Transponders often drop the callsign at the gate. Keep the last callsign from the track: `gatecheck.py` looks back 4 h, and the app already keeps tracks.
   - Map SKW/RPA/ENY/QXE/ASH… to UA/AA/DL/AS by flight number. flysfo lists SkyWest-operated United Express as `UAL5339`.
5. **Snapshot / artifact mode.** Do not embed flysfo data: there is no licence. DataSF (PDDL) can be embedded for a recorded day once that month is published. August was loaded on 2 Sep.

### 6.3 Checking by hand online

Per selected aircraft, show two links:
- `https://www.flysfo.com/flight-info/flight-status?type=arrivals|departures&search=<flight number>`. The parameters are read by the page's code; not tested in a browser.
- `https://www.flightaware.com/live/flight/<ICAO callsign>`.

Both are human-browser uses:
- FlightAware's terms allow human browser use.
- flysfo.com publishes no restrictive terms.

For the stand rather than the gate, open `https://www.flysfo.com/flysfo/api/flight-status` in a browser (10 MB JSON) and search for the callsign: the `stands` array holds the allocations with times.

### 6.4 QA metric

Run `gatecheck.py check --every 60 --js --json …` over each recording, and track the share of `agree` among parked aircraft on contact stands. The target is 100 %.
- Every `no-match` or `DISAGREE` points at a stand-geometry, stand-set or aircraft-size defect. This run found examples of each.
- The feed only reaches about 4 h back. A full day therefore needs one fetch every ≤ 4 h: about 6 fetches a day, far below a person refreshing the page.


## 7. Terms summary and what not to do

- **flysfo.com JSON.**
  - Observed: no terms of use are published, and robots.txt does not exclude the API path. It is the airport's own public flight-status data.
  - Inferred: occasional personal verification at the rate of a human reloading the page is the same load as a page view. `gatecheck.py fetch` refuses to run more often than every 10 minutes, sends gzip, and uses an identifying User-Agent.
  - Not verified: whether SFO permits a continuous relay. **Ask SFO** through https://www.flysfo.com/about/contact-sfo before building a live dependency.
  - Do not republish the data. It stays in `refs/cache/`, like the ADS-B recordings.
- **DataSF.** PDDL (public domain dedication). Safe to use and to ship derived data, with attribution as a courtesy.
- **FlightAware website.** Manual use only (quoted above). AeroAPI Personal is a licensed alternative for personal use.
- **SFO terminal maps.** Use them for reference (gate numbers). Do not embed them as textures or images in the app. No licence is stated.

## 8. Tool

```bash
python3 tools/live/gatecheck.py fetch                 # one flysfo snapshot -> refs/cache/gate_truth/ (>= 10 min apart)
python3 tools/live/gatecheck.py check                 # parked aircraft at the last recorded second vs published stands
python3 tools/live/gatecheck.py check --every 60 --still 60 --js --json out.json
        # every minute of the recording; one row per aircraft/stand episode; --js also runs the app's own matchGate
python3 tools/live/gatecheck.py gates                 # official names (maps, DataSF, AODB) vs data/sfo_stands.json
```

What the tool reimplements:
- `js/geo.js` `llToEN`, exactly: ARP 37.6188056, −122.3754167; 110 990 m/deg latitude; 111 320·cos(lat) m/deg longitude; world x = E, z = −N.
- `traffic.js` `standFits`, `gateScore` and `matchGate`:
  - the antenna point is nose − 0.2·L along the stand heading;
  - the lateral limit is min(18, 0.35·span_max + 4) m and the along-track limit is 20 m;
  - the score is |lat| + 0.35·|along|;
  - a reported true heading must be within 35° of the stand heading;
  - positions on taxiway polygons or runways are excluded.
- `airport.js` `CLASS_MAX`.
- Aircraft lengths and spans from `js/aircraft/types.js` and `js/live/aircraft.js`, dumped with node.

Other behaviour:
- It does not reproduce the app's occupancy arbitration or neighbour blocking. It reports the best stand and the runner-up instead.
- An aircraft counts as parked when it is on the ground, below 1 kt, and has stayed within 5 m for at least 120 s (the default; this run used `--still 60`).
- Its position is the median of its stationary reports over the last 5 minutes.
- All cached flysfo snapshots are merged, the newest version of each flight winning, because each snapshot only reaches about 4 h back.
- Callsigns are compared without zero padding: the ADS-B `CAL003` is flysfo's `CAL3`.
- A transponder that drops its callsign at the gate is identified by the last callsign seen in the previous 4 h.
- An arrival record is ignored if the aircraft moved after that arrival's block-in time. This covers a re-used flight number or a tow.

## 9. Not verified / open

- **Is automated use of the flysfo JSON allowed?** No terms are published. Permission from SFO is not verified; ask via https://www.flysfo.com/about/contact-sfo.
- **What `stands[]` times are.** Their exact meaning (actual vs planned) is not verified.
  - Past starts equal actual block-in, e.g. AS3360 at 20:22.
  - Many ends are round planned times (06:00, 06:30).
- **Suffix letters V/T/S/U** on SFO stand names: meaning not verified. No public definition was found.
- **Remote-stand codes** (2-x, 6-x, 9-x, 12-x, 41-xx): locations not verified.
- **Gate vs stand disagreement.** For 24 of 407 single-stand flights (26 of 488 merged), the gate and stand differ (e.g. UA1329 has gate D15 but stand D6). Which one is right is not verified. They are mostly future flights.
- **UAL1947 (N57478).** SFO→MCO went off block at 23:58 PDT, taxied to the runway 28 ends, came back and parked at our D16 by 00:40 PDT. flysfo still showed "Departing" and no D16 allocation at 01:52 am. The actual stand is unverifiable from the feed. This shows the feed can lag irregular operations.
- **Other flight APIs.** AeroDataBox, Aviationstack and Cirium gate coverage and accuracy at SFO were not tested (no keys). The Aviationstack gate field was not seen in its docs.
- **United.com terms.** Not verified (HTTP 503).
- **DataSF coverage.** The description says the data "starts 1/1/2015", but the endpoint returned only 2026-08-18 → 2026-08-31 (13,999 rows). Whether older data is archived elsewhere is not verified.
- **The overnight sample is small** (00:30–01:50 PDT). Repeat during the 06:00–10:00 PDT bank for statistics per pier.
- **Side finding (resolved).** At 07:30 UTC, the `tools/live/recio.py` of that time yielded 0 records for `refs/cache/rec/adsbfi_20260924_07.jsonl.gz`.
  - The file's first gzip member had been written by an earlier recorder instance and failed with "invalid block type". The second member started at byte 34,154.
  - The committed `recio.py` (dbdaf2b) now resynchronises at the next gzip header.
  - At 08:56 it and `gatecheck.py`'s own member-by-member reader agree: 1,899 / 1,237 lines for hour 07 (adsb.fi / adsb.lol).

## Verification (adversarial check)

An independent verifier checked this report on 24 Sep 2026, 09:30–10:00 UTC. It re-fetched every cited source it could reach and re-ran the tool. Fresh downloads are in `refs/cache/gate_truth_verify/` (gitignored).

The re-run used an isolated copy of `tools/live/gatecheck.py`, pointed at a separate cache (`refs/cache/gate_truth_verify/rerun/`), so the author's cache was not overwritten. It re-dumped the app type table with node and ran `check --every 60 --still 60 --js` over the author's window (07:30:18–08:52:18 UTC), plus `gates`.
- The 30 rows reproduced **exactly**: stand, published stand, errors and verdicts.
- The app's own `Traffic.matchGate` agreed on 30/30.
- The `gates` output reproduced every list and count. Only the example column of the simultaneity table differs between runs, because `simultaneous()` iterates a Python `set`, whose order changes with hash randomisation.

Inline fixes are marked **[corrected by verifier]**.

| # | Claim | Verdict | Evidence (re-fetched / re-run) |
|---|---|---|---|
| 1 | Flight-status JSON at `https://www.flysfo.com/flysfo/api/flight-status`; no key needed; loaded by `/modules/custom/flysfo_flight_status/js/dist/assets/index.js` | Confirmed | 09:34 UTC fetch returned 200 without a key: 538,443 B gzip on the wire, 11,584,371 B JSON, 2,223 records, 691 operating. The bundle (byte-identical to the author's copy) contains exactly the five endpoints listed, and `accessor:"gate.gate_number"`. |
| 2 | Headers `cache-control: must-revalidate, no-cache, private` and `x-generator: Drupal 11` | Confirmed | Same headers on the 09:34 fetch (`x-generator: Drupal 11 (https://www.drupal.org)`). |
| 3 | Fields `callsign`, `gate.gate_number`, `stands[]`, `linked_flight_id`, `aircraft_transport_type`; no registration | Confirmed | Walked every key of 200 records: no key contains `reg` or `tail`. |
| 4 | Spans about 4 h back to 12 h ahead | Confirmed | 09:34 UTC snapshot (02:30 am PDT): scheduled times 22:35 to 14:30 PDT. |
| 5 | `flight-status-update` byte-identical to `flight-status` at 07:32 | Confirmed (nuance) | The two decompressed files are byte-identical (same `last_update` 12:32 am, 2,054 records). The update file was fetched at 07:34:18, not 07:32. |
| 6 | Query parameters `?type=&search=` feed the initial filters | Confirmed in code (not tested in a browser) | The bundle contains `new URLSearchParams(location.search)`, then `l.get("type")` for the `flight_kind` filter and `l.get("search")` for `globalFilter`. |
| 7 | No flysfo terms of use; `/terms-of-use` returns 404; footer's only legal link is "Privacy & Cookie Use"; robots.txt does not disallow `/flysfo/api/` | Confirmed | `/terms-of-use`, `/terms`, `/terms-use`, `/terms-and-conditions`, `/website-terms-use` and `/copyright` all return 404. `/legal` returns 403 with the "page … no longer available" body. The footer's legal/policy link is only `/privacy-cookie-policy` (the rest are navigation, Accessibility and Public Notices). The privacy page has no use restriction. robots.txt disallows only Drupal core/admin/search/user paths. No terms page appears in the site URL list. Whether SFO permits automated use remains **unverifiable**. |
| 8 | 07:32 snapshot: 2,054 records, 631 operating; stands per flight 462/56/15/98; blocks 20:33→12:30 PDT | Confirmed | Recomputed from the cached snapshot. |
| 9 | Stand name = gate number for 383/407 single-stand flights (462/488 merged); 23 of 24 exceptions still to come; UA1329 D15→D6, UA2158 E3→G104, UA5790 F9→6-4 | Confirmed | Recomputed. "Still to come" = no actual block time. |
| 10 | AS/3360 record; AC745/AC738 towed C10 21:04–06:30 → D11 07:00–08:30 | Confirmed | Found verbatim in the merged snapshots. |
| 11 | 11 suffixed stands and 22 remote codes; the suffix is never occupied together with its base; B5S A359 (JX11), B11S A332, B16S B763/B77W, C9V B763/B76W | Confirmed | Recomputed. 0 overlaps for every suffix/base pair that has data. The meaning of the suffix letters remains **unverifiable**. |
| 12 | SkyWest-operated United Express appears as `UAL5339` in flysfo, while ADS-B says `SKW…` | Partly unverifiable | `UAL5339` exists in flysfo, but the feed does not name the operator. No SKW/RPA/ENY/QXE/ASH callsign occurs anywhere in the recording to 09:37 UTC (overnight), so the regional mapping in `gatecheck.py` has never been exercised. |
| 13 | Zero-padding: ADS-B `CAL003` = flysfo `CAL3` | Confirmed | flysfo carries `CAL3`, `EVA27` and `SJX11`. |
| 14 | DataSF `chfu-j7tc` licence PDDL; "Publishing frequency: Monthly"; description says it "starts 1/1/2015"; only 13,999 rows 2026-08-18 23:55 → 08-31 23:59; loaded 2 Sep | Confirmed | `https://data.sf.gov/api/views/chfu-j7tc.json` gives `"license": {"name": "Open Data Commons Public Domain Dedication and License"}`, licenseId `PDDL`, "Publishing frequency": "Monthly" (and "Data change frequency": "Daily"). The SoQL summary returned n=13999, first 2026-08-18T23:55, last 2026-08-31T23:59, data_loaded_at 2026-09-02T10:03:53, all in month 2026-08. The period is 13 days, not "two weeks"/"14 days" (fixed inline). |
| 15 | DataSF: 106 gates used, with the per-gate counts in the §4 table (e.g. F9·185, G14·3) | Confirmed | The `$group=gate` query reproduces all 106 gates and every count in the §4 table exactly. |
| 16 | Terminal map PDFs at the four URLs, "Effective 11/2025" and "Effective 7/2026"; 114 gate labels A1–A15, B1–B27, C1–C11, D1–D12, D14–D18, E2–E13, F5–F22, G1–G14 | Confirmed | Fresh downloads are byte-identical to the cached ones. Each PDF prints "Effective 11/2025" or "Effective 7/2026". Word extraction plus a rendered crop of T1 show C2 and B1 as map labels. The union is 114. No copyright or licence text on the static-maps page or the PDFs. |
| 17 | Our data: 89 contact stands and remote G103–G105; aliases per §4; A3/B1/G103 unused; C2, D17, D18, F9 missing; the 21 alias-only numbers | Confirmed | Read from `data/sfo_stands.json` and the re-run `gates` output. |
| 18 | 13 gate pairs in 11 of our stands with simultaneous allocations already under way; E12\|E13 and F21\|F22 only in future plans; none for A3\|A4, A6\|A7, D1\|D2, G10\|G14, G11\|G12\|G13 | Confirmed (counting nuance) | Recomputed, listing every under-way overlap. Each of the 13 pairs has ≥1 distinct pair of turns under way. The counts are record-level: for A11\|A13 the arrival and departure records of the PR104/105 turn carry different end times (00:30 vs 00:32), so 3/2 are really 2/1 distinct turn pairs (fixed inline). All other pairs' counts equal distinct turn-pair counts. Every example in the table exists. Some examples name the turn's arrival id while the allocation sits on the linked departure record (e.g. UA/246/A → F22 is on UA/2827/D). The evidence is SFO's *plan* (start = actual block-in), not an observation. |
| 19 | 15 parked aircraft; per-row values in the §5 table | Confirmed (with fixes) | The re-run is identical to `check_20260924.json`. Excluded rows: 13, not 12 (UAL1947 at 07:37 was left out; fixed). #5 C11: 34 m from our C11, not 33, and 5.3° from C10, not "within 5°" (fixed). #11 F22: heading 2.5° off, not 2° (fixed). #15 B5: position 0.2/1.8 m, but heading 53.4° vs stand 27.8° (25.6° off), so "geometry perfect" is overstated (fixed). #10 E6: transponder off about 15 s after stopping, not 1 min (fixed). |
| 20 | "No wrong name; 10 of 10" | Confirmed (nuance) | 8 of the 10 are tied to SFO by callsign: 5 stand windows, 1 gate, and 2 geometry-only rows whose published gate/stand is F22/B5. The other 2 (#1 B18, #8 B26) have no callsign and are consistent only by same-airline, same-type allocation. |
| 21 | Position error on correct matches (n=10): lateral \|mean\| 3.0 m, max 6.0 m; along mean −4.7 m, median −4.8 m, range −10.6 to +4.7 m; negative = ahead of the expected antenna point | Confirmed | Recomputed: lateral mean \|·\| 3.05 m, max 6.0 m; along mean −4.66 m, median −4.75 m, range −10.6/+4.7 m. Sign checked against `traffic.js` `gateScore` (`along = -(r·d)`, with d the nose direction), so negative means the report lies nose-ward of nose − 0.2·L. |
| 22 | Parked reports scatter by up to about 27 m (AAL2506, NACp 8–9) | Refuted (magnitude) | AAL2506's gs < 1 kt reports, 07:28–08:52 UTC, NACp 8/9/none: largest bounding-box side in any 20-min window 31.0 m (window from 07:51), diagonal 36.8 m, 95th-percentile distance from the median 23.6 m. Fixed to ~31 m. The recommendation to use a median position stands, and is stronger. |
| 23 | UAL1947: off-block 23:58 PDT, near the rwy 28 ends at 07:31 UTC, at D16 by 07:40; flysfo still "Departing" from E10U | Confirmed (incomplete) | Track: stationary about 206 m from the 28L end 07:28–07:30, moving 07:31, 77 m from D16 at 07:35, 10–11 m at 08:02. The report omitted that it **left D16 about 08:04 and departed about 08:20 UTC** (18,100 ft by 08:30). The flysfo 09:34 UTC snapshot still shows "Departing", with no runway time (added inline). |
| 24 | `gatecheck.py` reimplements `llToEN` exactly (ARP 37.6188056, −122.3754167; 110,990; 111,320·cos lat) and `standFits` / `gateScore` / `matchGate` (ANT 0.2, latMax min(18, 0.35·span + 4), along 20, score \|lat\| + 0.35\|along\|, 35° heading gate), plus `CLASS_MAX` | Confirmed | Compared line by line with `js/geo.js` l.3–9, `js/live/traffic.js` l.19–26 and 354–380, and `js/live/airport.js` l.54. The ARP also matches AirNav KSFO "37-37-07.7000N 122-22-31.5000W … 37.6188056,-122.3754167 (estimated)" (https://www.airnav.com/airport/KSFO). |
| 25 | `TYPES.b772` inherits the 64.8 m span of the 777-300ER, so `standFits` rejects every B772 at class-E stands | Confirmed | `types.js` l.140: `derive('b77w', 'Boeing 777-200ER', 63.73, …)` keeps `wing.span` 64.8. Class E: 64.8 > 61 + 0.6 and maxSpan 61 < 64, so rejected. With 60.93 m it would fit (60.93 ≤ 61.6, L 63.73 ≤ 70). |
| 26 | 777-200 span 199 ft 11 in (60.93 m), length 209 ft 1 in, from D6-58329 §2.2.1 p. 15 (mirror); Boeing URL 404 | Figures confirmed; source statement refuted | Mirror page 15 (Oct 2004 edition) rendered and read. The old Boeing path does return 404, but Boeing's **current** URL `…/content/dam/boeing/v2/airports/acaps/777-200-200ER-300_Rev_E.pdf` returns 200 (Rev E, Dec 2024), and its p. 2-8 shows the same 60.93 m / 63.73 m. Fixed inline. |
| 27 | "`B77L` (64.8 m) is right as it is" | Confirmed, but the fix is incomplete | 777-200LR span 212 ft 7 in (64.80 m) confirmed on Boeing D6-58329-2 Rev G p. 2-3. However, B77L maps to `TYPES.b772` in `ICAO_MAP` and `TYPE_MODELS`, so the recommended span fix would break B77L unless it gets its own entry (added inline). |
| 28 | Our B5 and B16 are class B; E6 is `inf` with the grid heading 117.8°; observed E10 139.6° and E13 154.7° | Confirmed | Read from `data/sfo_stands.json`. |
| 29 | FlightAware terms quotes; "Last Updated: July 16, 2026" | Confirmed | https://www.flightaware.com/about/termsofuse re-fetched; both quotes are verbatim. The first quote is preceded on the page by "With the exception of FlightAware data feeds and APIs,". |
| 30 | AeroAPI Personal tier: "up to $5 free per month, or $10 free per month for ADS-B feeders", "10 result sets/minute", "personal or academic purposes only"; `gate_origin`/`gate_destination`/`terminal_*`, no stands | Confirmed | Re-fetched https://www.flightaware.com/commercial/aeroapi/ and the OpenAPI yml. |
| 31 | AeroDataBox is "the only candidate that links tail number to flight" | Refuted | The AeroAPI OpenAPI flight objects contain `registration`: "Aircraft registration (tail number) of the aircraft, when known." Fixed inline. The AeroDataBox spec does have `gate`, `terminal`, `baggageBelt` and `reg`. |
| 32 | AeroDataBox Basic: 400 units/month; "You cannot give, sell, or pass any third party access…" | Confirmed | https://aerodatabox.com/pricing/: "Basic Free 7-day trial Free Free forever API units / month § 400"; the resale quote is verbatim. |
| 33 | Aviationstack free plan "100 Requests", "Non-Commercial Use"; FAQ mentions "terminals, gates"; gate field not seen in docs | Confirmed / unverifiable | The pricing page matches. The documentation page ends in a redirect loop (50 redirects), so the gate field remains **unverifiable**. |
| 34 | Cirium Flex: "terminal, gate and baggage carousel"; evaluation "Free", "30-day trial period", "Maximum 20,000 total (lifetime)" | Confirmed | Both developer.flightstats.com pages re-fetched; text matches. |
| 35 | FAA SWIM: STDDS carries ASDE-X/ASSC/STARS/RVR/EFSTS/TDLS; CDM quotes | Confirmed | Both faa.gov pages re-fetched. The ellipsis in the CDM quote spans other list items. That TFDM/CDM would carry SFO gates remains **unverifiable**. |
| 36 | united.com terms not verified (HTTP 503) | Unverifiable | Two plausible terms URLs failed with HTTP/2 INTERNAL_ERROR from this network. |
| 37 | `recio.py` (dbdaf2b) resyncs at the next gzip header; 1,899 / 1,237 hour-07 lines, agreeing with the `gatecheck.py` reader | Confirmed | `tools/live/recio.py` l.5–20 has the resync logic; counts recomputed with both readers. |
| 38 | Recommendations (split stands, add F9, fix classes, relay only with SFO's permission, no embedding of flysfo data) | Supported | They rest on items 7, 15–18 and 25–28, which hold, with the B77L caveat. Splitting stands relies on SFO's plan data, not on observed simultaneous parking. The ADS-B `ANT` change is correctly left pending more data. |

**Overall.** No key fact was fabricated. The endpoint, fields, terms, licence, gate lists, per-gate counts, simultaneity counts and the whole empirical table reproduce, and the app-vs-reimplementation cross-check reproduces 30/30.

Refuted or corrected:
- the Boeing-source statement (the original is online);
- "AeroDataBox is the only source with registrations" (AeroAPI has them too);
- the parked-scatter magnitude (31 m, not 27 m);
- several small numeric or wording slips: C11 distance, heading differences, excluded count, E6 transponder timing, "14 days", the A11|A13 double count, and the wire size.

Two omissions were added:
- The recommended `b772` span fix must not be applied to B77L, which shares that type.
- UAL1947 departed after its return to the ramp.

Still unverifiable:
- SFO's permission for automated use of flysfo;
- the meaning of the stand suffix letters;
- the locations of the remote stands;
- whether `stands[]` end times are actual or planned;
- the regional-carrier callsign mapping;
- the Aviationstack gate field;
- the united.com terms.
