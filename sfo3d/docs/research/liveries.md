# Liveries at SFO: who flies what, brand ≠ callsign, current (2026) liveries, and openly-licensed textures

Status: research note, 24 Sep 2026. Tools written for this note, all under `tools/models/`:

- `sfo_census.py`: operator / brand / type census;
- `build_brands.py`: registration → brand table;
- `livery_sources.py`: which open livery textures fit our models' UV layouts;
- `check_dims.py`: model dimensions, see `aircraft_models_check.md`.

Generated tables go to `tools/models/out/`. Third-party downloads are in `refs/cache/` (gitignored). Nothing in `data/` or `js/` was modified.

Provenance tags used below:

- **O**: official source (manufacturer, airline newsroom, government data).
- **S**: reputable secondary source (trade press, the airline museum, a forum count).
- **K**: my own knowledge or reading of a texture; **not verified** against a source.
- **inf**: inferred from observed data.

## 1. What flies at SFO (census)

### 1.1 Official: SFO Air Traffic Landings Statistics, Aug 2025 – Jul 2026 (O)

The dataset is DataSF `fpux-q53t` (https://data.sf.gov/d/fpux-q53t), licence ODC-PDDL 1.0, last period 2026-07. It holds landings self-reported by the airlines, split into *operating* and *published* (marketing) airline, and by aircraft model. That split is exactly the brand-versus-callsign question.

In those 12 months there were 189,132 passenger landings. Reproduce with `python3 tools/models/sfo_census.py` (it caches `refs/cache/sfo/landings_12m.json`).

| Published (brand) | Operating | Landings | Share | Models (landings) |
|---|---|---|---|---|
| United Airlines | United Airlines | 77,565 | 41.0 % | B38M 13,206 · B39M 13,070 · B738 10,340 · B772 7,298 · A320 6,553 · B739 6,231 · A319 4,858 · B789 3,413 · A21N 3,372 · "B773" 3,277 · B752 2,970 · B753 2,629 |
| United Airlines (**United Express**) | SkyWest | 22,354 | 11.8 % | E175 16,959 · CRJ2 2,793 · CRJ7 2,602 |
| Delta Air Lines | Delta | 13,873 | 7.3 % | B739 4,265 · B738 1,970 · B763 1,793 · B752 1,507 · A21N 1,483 · BCS3 813 · A319 599 · BCS1 522 · A321 384 · B753 250 · A320 168 · A332 69 |
| American Airlines | American | 11,698 | 6.2 % | A321 5,625 · B738 2,316 · A21N 2,150 · B38M 1,213 · A320 369 |
| Alaska Airlines | Alaska | 11,205 | 5.9 % | B739 3,800 · B39M 3,676 · B738 2,659 · B38M 536 · A21N 295 · A332 177 · B737 61 |
| Southwest | Southwest | 9,652 | 5.1 % | B737 3,985 · B38M 3,180 · B738 2,487 |
| Alaska Airlines (regional) | SkyWest | 6,721 | 3.6 % | E175 |
| JetBlue | JetBlue | 4,376 | 2.3 % | A321 3,287 · A21N 1,075 |
| Frontier | Frontier | 3,434 | 1.8 % | A20N 1,883 · A21N 1,206 · A321 212 · A320 133 |
| Alaska Airlines (regional) | Horizon | 2,985 | 1.6 % | E175 |
| Air Canada | Air Canada | 2,561 | 1.4 % | B38M 1,518 · BCS3 817 · A320 160 · A321 61 |
| American Airlines (**American Eagle**) | SkyWest | 1,864 | 1.0 % | E175 |
| EVA Air | EVA | 1,089 | 0.6 % | "B773" 965 · B789 124 |
| Aeroméxico | Aeroméxico | 1,019 | 0.5 % | B38M 693 · B738 171 · B39M 154 |
| Cathay Pacific | Cathay | 884 | 0.5 % | "B773" 498 · A359 386 |
| TACA International (flies as **Avianca**) | TACA | 864 | 0.5 % | A20N 857 |
| Delta Air Lines (**Delta Connection**) | SkyWest | 792 | 0.4 % | E175 |
| Singapore Airlines | SIA | 731 | 0.4 % | A359 |
| Japan Airlines | JAL | 730 | 0.4 % | B789 399 · "B773" 211 · B788 120 |
| ANA | ANA | 729 | 0.4 % | "B773" |
| British Airways | BA | 708 | 0.4 % | A388 358 · "B773" 347 |
| Lufthansa | Lufthansa | 707 | 0.4 % | B748 299 · A359 206 · A388 149 · B744 53 |
| Air Canada (**Air Canada Express**) | Jazz | 633 | 0.3 % | CRJ9 |
| Air India | Air India | 588 | 0.3 % | "B773" 440 · B772 148 |
| Breeze | Breeze | 585 | 0.3 % | BCS3 |
| WestJet | WestJet | 581 | 0.3 % | B737 225 · B738 203 · B38M 153 |
| Turkish | THY | 563 | 0.3 % | A359 |
| Virgin Atlantic | VIR | 535 | 0.3 % | B789 459 · "A350" 76 |
| Air France | AFR | 516 | 0.3 % | "B773" 362 · A359 134 |
| Hawaiian | Hawaiian | 476 | 0.3 % | A21N 302 · A332 174 |
| Copa | Copa | 444 | 0.2 % | B39M |
| Sun Country | Sun Country | 410 | 0.2 % | B738 |
| ZIPAIR, Korean Air, Starlux, PAL, China Airlines, Emirates, Swiss, Asiana, KLM, Aer Lingus, French Bee, **Porter** (E295), SAS, Air NZ, Qatar, TAP, Air Premia, Flair, ITA, China Southern, Vietnam, Fiji, Condor, China Eastern, Qantas, Iberia, Air China, LOT | | 211–365 each (fewer than 211 below ITA) | | |

Notes on the data:

- **"B773" is SFO's own model code.** In this dataset it covers 777-300 and 777-300ER. The ADS-B type for those aircraft is B77W (for example EVA B-16705 and B-16733 in the recorder, and Cathay B-KQF (CPA870) in the snapshot) [corrected by verifier: B-KQF is a Cathay Pacific registration, not EVA]. "A350" is likewise the dataset's code, not an ICAO designator.
- **Freighters** are listed separately: ATI, FedEx, ABX, 21 Air B762/B763; China Airlines, Atlas and EVA B772F (B77L); AirZeta, Korean, Kalitta B744/B748. They are out of scope here but need liveries too.
- **Regionals that never appear at SFO** in these 12 months: Republic, Mesa, Envoy (1 landing), PSA, Endeavor, GoJet, CommuteAir, Piedmont.

### 1.2 Observed by our recorder and the snapshot (O, observed today)

`tools/models/sfo_census.py` also reads `refs/cache/rec/*.jsonl.gz` and `data/snapshot.js`. It counts aircraft on the ground within 3.5 km of the ARP, or below 2500 ft within 8 km.

At 08:22 UTC on 24 Sep (01:22 PDT) it had seen 77 airframes. [corrected by verifier: 43 of these came from the overnight recorder, up to 08:22 UTC. The other 34 were seen only in the daytime snapshot of 23 Sep, so the set is not "mostly red-eyes".] The recorder keeps running; re-run the census for a daytime picture. Every observed type is in the table above.

The snapshot (23 Sep, 10:51 PDT) contains SkyWest airframes of **three different brands**:

| Callsign | Registration | Brand |
|---|---|---|
| SKW249R | N510SY | American Eagle |
| SKW3490 | N171SY | Alaska |
| SKW3047 | N408SY | Alaska |
| SKW485Y | N125SY | United Express |
| SKW6001 | N148SY | United Express |

[corrected by verifier] The **live** app does not paint them United. `js/live/traffic.js` calls `liveryForAirline()` in `js/live/lookup.js`, and `SKW` is in neither `FAM` nor `SAME` there, so every SkyWest aircraft gets the `NEUTRAL` grey/white scheme. `AIRLINE_LIVERY.SKW = 'UAL'` in `js/aircraft/fleet.js` only affects the cinematic renderer (`js/scene.js`, `js/shots.js`). In both apps the brand is still wrong for every SkyWest airframe.

## 2. Brand determination: registration → brand (the livery follows the airframe)

### 2.1 Source and result (O / inf)

**Source (O).** US DOT / BTS, *Marketing Carrier On-Time Performance (Beginning January 2018)*, months 2026-05, 2026-06 and 2026-07. The files are https://transtats.bts.gov/PREZIP/On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_2026_<M>.zip (US government work, public domain). Every domestic flight row carries `Tail_Number`, `IATA_Code_Operating_Airline` and `Marketing_Airline_Network`.

For a regional airframe, the marketing network is the brand painted on it:

| Operator | Network | Brand |
|---|---|---|
| OO | UA | United Express |
| OO | AS | Alaska (regional) |
| OO | DL | Delta Connection |
| OO | AA | American Eagle |

Cross-checks:

- The FAA Releasable Aircraft Database gives type and registered owner (https://registry.faa.gov/database/ReleasableAircraft.zip, downloaded 24 Sep 2026).
- The SFO pairs in §1.1 confirm which combinations occur at SFO.

**Result.** There are 1,519 regional tails over the 11 regional operators [corrected by verifier: the tool lists 11 operators, but only 10 have rows in 2026-05..07; Air Wisconsin (ZW) has none]. **Exactly one** (N738EV, a SkyWest CRJ550, FAA model CL-600-2C11: 165 AA and 55 UA flights) flew for more than one network in three months, so a tail → brand table is a sound rule. The FAA *owner* field is **not** enough: SkyWest's own E175s are registered to "SKYWEST AIRLINES INC" whichever partner they fly for.

**Tool.** `python3 tools/models/build_brands.py [YYYY_M …]` writes `tools/models/out/regional_brands.json`, which holds:

- `tails`: registration → operator, brand, share, flights, SFO flights, FAA type, owner (observed);
- `series`: contiguous registration blocks with a single brand (inferred; a fallback for airframes not in the BTS months).

### 2.2 The rule, in order

1. **Look up the tail in `regional_brands.json` (observed).** Refresh it monthly; BTS publishes with a lag of about 2 months.
2. **Otherwise apply the series fallback (inf, derived from the observed tails).** These are the SFO-relevant blocks:

   | Operator / type | Registration block | Brand | Tails observed |
   |---|---|---|---|
   | SkyWest E175 | N103SY – N168SY | United Express | 53 |
   | SkyWest E175 | N170SY – N199SY | Alaska | 27 |
   | SkyWest E175 | N200SY – N213SY | United Express | 11 |
   | SkyWest E175 | N240SY – N327SY | Delta Connection | 81 |
   | SkyWest E175 | N400SY – N431SY | Alaska | 16 |
   | SkyWest E175 | N501SY – N521SY | American Eagle | 20 |
   | SkyWest E175 | N626SY – N639SY, N601UX – N625UX | United Express | 12 + 25 |
   | SkyWest E175 | N603CZ – N614CZ | Delta Connection | 6 |
   | SkyWest E175 | N8xxxx / N78361 (United-owned) | United Express | 20 |
   | SkyWest E170 | N702SY – N732SY | United Express | 5 |
   | Horizon E175 | N620QX – N671QX, N652MK | Alaska | 49 |
   | SkyWest CRJ200 | N4xxSW, N9xxSW, N9xxEV, N4xxCA, N2xxPS, N6xxBR, N8xxAS | United Express (all 52 + 19 + … observed tails) | |

   The boundary N168SY/N170SY is sharp: UA's highest observed tail is N168SY and AS's lowest is N170SY.

3. **SkyWest CRJ700 and CRJ550 have no clean series.** The N6xxSK and N7xxSK blocks are interleaved between AA, DL and UA:
   - N705SK–N742SK and N744SK–N774SK are AA;
   - N779SK–N797SK are UA;
   - N703SK and N776SK are DL.

   [corrected by verifier] The AA ranges above hold only for the CRJ700s (CL-600-2C10). By registration alone they are wrong: they contain CRJ550s (CL-600-2C11) of other brands, namely N712SK (DL), N738SK (DL), N762SK (UA), N767SK (UA), N768SK (DL), N771SK (UA) and N773SK (UA). The N7xxSK block also contains N743SK, a UA CRJ700. ADS-B codes both types as CRJ7, so the conclusion stands: use the per-tail table.

   Use the per-tail table only. The CRJ550 is FAA model CL-600-2C11, "Regional Jet Series 550" (FAA TCDS A21EA); ADS-B databases code it as CRJ7.
4. **Canadian regionals** are not in BTS:
   - **Jazz** (callsign JZA): every airframe flies as **Air Canada Express** (S: SFO pair Air Canada / Jazz Aviation, CRJ9 only).
   - **Porter**: brand = Porter.
5. **Last resort (inf).** Use the callsign's airline for mainline callsigns. For a regional callsign with no table hit, use the operator's majority brand at SFO: SkyWest E175 → United Express (119 of 235 SkyWest E175 tails with at least one SFO flight in BTS 2026-05..07 are UA [corrected by verifier: was "119 of 284"]; by DataSF landings UA is 16,959 of 26,336 SkyWest E175 landings, 64 %); CRJ2 → United Express.

   Mark such aircraft `brand_src: 'inf'` so that the owner's observed/inferred rule holds.

## 3. Current (2026) liveries: the frequent brands at SFO

**Colour values.**

- Official values exist only where an airline publishes brand guidelines, and those are screen/print brand colours, **not paint specifications**. Paints such as American's grey or Lufthansa's special blue differ.
- For rendering, pick values by sampling several official press photos taken in daylight (as a reference measurement, not a texture). Keep the official hex as the "brand" value.
- Where only names are official, the name is given. Third-party hex values are flagged **unverified**.

### 3.1 US brands (about 15)

**1. United Airlines, mainline.** 2019 "blue" evolution of the globe livery (O).

- Source: United newsroom, 24 Apr 2019, https://united.mediaroom.com/2019-04-24-Out-with-the-Gold-in-with-the-Blue-United-Airlines-Unveils-its-Next-Fleet-Paint-Design.
- Colours (O): "Three shades – **Rhapsody Blue, United Blue and Sky Blue**". The "lower half of the body will be painted **Runway Gray**".
- Tail (O): "a gradient in the three shades of blue", with the globe logo "predominantly in Sky Blue".
- Engines and wingtips (O): "painted **United Blue**".
- Swoop (O): the Dreamliner "swoop … added to all aircraft in **Rhapsody Blue**". It separates the white upper fuselage from the grey belly.
- Titles (O): "United's name will appear larger". "Connecting people. Uniting the world." is painted near the door.
- Hex: **none published** (no official United brand guideline found). #005DAA ("United blue") appears only on third-party sites: **unverified**.
- **Fleet mid-transition.** The older "Globe" (2010 post-merger, gold-accented globe) livery is still flying. An Airliners.net fleet thread (S, community count, **unverified**) states that 24 wide-bodies and 117 narrow-bodies were repainted in 2025 and 166 mainline aircraft were still in the Globe livery.
- **Special liveries.** Per-airframe exceptions exist:
  - "Mountain Ascent" on United Express E175 N645SY, Sep 2026 (S, worldairlinenews.com 2026-09-04);
  - the "Coastliner" A321neo subfleet: "bright shades of blue wrapping the back third of the aircraft and United's name spelled out on its belly" (S, AirlineGeeks 2026-03-24).

  Keep a per-registration override table.
- Types at SFO: B38M, B39M, B738, B739, B772, B77W, B789, B78X, A319, A320, A21N, B752, B753.
- Winglet / sharklet paint follows "wingtips … United Blue" (O). The engine-cowl lip colour is not specified.

**2. United Express** (SkyWest E175 / CRJ200 / CRJ550 / CRJ700) (O / K).

- The same 2019 design was applied to regional aircraft "throughout the year" (O, same release). The titles read "UNITED EXPRESS" (K).
- Rear-engined CRJs have no underwing engines. The nacelle colour on the CRJ and the E175 is **not verified**.
- Older regional aircraft still carry the 2010 Globe style (K; the FlightGear `ERJ175/UnitedExpress.png` is that older style).
- Per-tail brand: §2.

**3. Alaska Airlines, narrow-bodies (737-800/-900/-9, and the E175 flown by SkyWest and Horizon).** 2016 brand (O).

- Source: Alaska newsroom, 25 Jan 2016, https://news.alaskaair.com/alaska-airlines/about-brand-refresh/.
- Colours (O): new colours in the parka fur-lining of the tail's Alaska Native portrait:
  - "**tropical green**" (for Hawai'i, Costa Rica and international destinations);
  - blues "**breeze, midnight, atlas and calm**".
- Titles (O): a streamlined italic "Alaska" wordmark. The tail portrait is modernised with an "expanded ruff".
- Hex (**not from an official host**): Alaska Brand Guidelines 2019 R13, of which only a Scribd copy was found. It gives digital values Midnight #01426A, Atlas #0074C8 and Breeze #00C7E6; tropical green and calm are unknown. Treat as **unverified** until the original is obtained.
- Fuselage layout (K, from the FlightGear `N563AS.png` texture):
  - white fuselage;
  - large midnight "Alaska" titles forward;
  - midnight tail with the portrait;
  - aurora-colour sweep on the aft fuselage.

  Verify against official photos.
- **2026 status (O / S).** The narrow-body "Chester" (tail-portrait) livery stays. Alaska's statement (S, Airways Magazine / Live and Let's Fly, quoting the Alaska press kit https://news.alaskaair.com/images-videos/alaska-airlines-global-livery/) says:
  - "the core Alaska Airlines brand expression remains the character … on the tail of narrowbody aircraft flying throughout North America";
  - the new "Global" livery is for the 787 fleet only.

  [corrected by verifier] The quoted wording is not on the two cited pages (the Airways article and the Alaska press kit). The substance is confirmed by an official Alaska source, https://news.alaskaair.com/destinations/alaska-airlines-continues-international-expansion-with-new-flights-to-london-and-reykjavik-from-seattle-with-a-first-look-at-our-new-global-experience/, which says: "The Alaska Native on Alaska narrowbody aircraft and Pualani on all Hawaiian Airlines' aircraft flying to, from and within the Hawaiian Islands are not going away." Airways confirms the Global livery "will be applied to the entire 787 fleet".
- Horizon- and SkyWest-operated E175s wear the same Alaska livery (K; operated-by marking not verified).

**4. Alaska 787 "Global" livery** (not expected at SFO in 2026; noted for completeness) (O).

- "inspiration from the … Aurora Borealis, featuring a palette of deep midnight blues and lush emerald greens" (press kit above). The belly, engine and winglet details are not published.
- The ex-Hawaiian 787-9s were repainted into this livery (S, Simple Flying).

**5. Hawaiian Airlines** (A321neo, A330-200 at SFO). 2017 livery (O).

- Source: Hawaiian release of 1 May 2017, archived at https://news.alaskaair.com/releases/hawaiian-airlines-unveils-new-brand-and-livery/.
- Pualani on the tail, now larger and "liberat[ed] … from the floral holding shape", framed by a sunrise.
- Palette (O): "**purple, fuchsia and coral**".
- Lei elements accentuate the fuselage contours.
- Hex: none official found.
- **2026 status (S):** the Hawaiian brand stays on the A321, A330 and 717 (same Alaska statement). The ex-Hawaiian 787s are now Alaska Global.

**6. Delta Air Lines** (B739, B738, B763, B752, B753, A21N, A321, A319, A320, BCS1, BCS3, A332). 2007 "Onward and Upward" livery (S/O).

- Colours: Delta Brand Guidelines, 29 May 2018 (O; a copy hosted at waatbp.oneclub.org/wp-content/uploads/2024/08/Delta_Brand_Guidelines.pdf, p.31):

  [corrected by verifier] The PDF's host is the One Club for Creativity awards site, not a Delta host, and news.delta.com does not link to it. The values sit on PDF page 32, in the "Color Palette" section, which starts at printed page 31. Delta's own news hub, https://news.delta.com/delta-air-lines-logos-and-brand-guidelines, has an October 2016 palette image (`/sites/default/files/pb%200424%20Delta%20Brand%20Guidlines_MediaProfessionals2_Page_09.png`). That image confirms **Delta Blue #003366 / Pantone 654c** and **Delta Red #C01933 / Pantone 187c** from an official host. Light Red #E01933 and Dark Red #991933 are only in the third-party-hosted 2018 PDF.

  | Name | Hex | Pantone | Role |
  |---|---|---|---|
  | **Delta Blue** | **#003366** | PMS 654C | primary |
  | **Delta Red** | **#C01933** | PMS 187C | |
  | **Delta Light Red** | **#E01933** | PMS 186C | widget / supergraphic |
  | **Delta Dark Red** | **#991933** | PMS 202C | widget / supergraphic |
  | Groundspeed Graphite and cool greys | #63666A, #888B8D, #A7A8AA, #D0D0CE | | |

- Layout (S, Delta Flight Museum, deltamuseum.org, "Mainline Livery 1929–Present"):
  - "3-dimensional red widget logo … 'Onward and Upward'";
  - "In May 2015, Delta added its name in white to the blue belly".
- Layout (S, trade press):
  - a "Euro white" upper fuselage, with a dark-blue wave over the belly;
  - a navy tail with the red widget.
- Nacelles are dark blue (K, from the FlightGear `767-300ER/DAL.png` and `737-800/DAL.png`: **verify**).
- Special liveries: Team USA / Milano Cortina 2026 A350 (O, news.delta.com).

**7. Delta Connection** (SkyWest E175 at SFO). Delta livery with "DELTA CONNECTION" titles (K; the FlightGear `ERJ175/Delta.png` shows that). **Verify** against an official photo.

**8. American Airlines** (A321, A21N, B738, B38M, A320 at SFO). 2013 livery with the 2021 "Silver Eagle" paint update (O/S).

- Source (O): American newsroom, 17 Jan 2013, https://news.aa.com/news/news-details/2013/American-Airlines-Debuts-New-Modern-Look/default.aspx.
  - "Silver mica paint was chosen …"
  - "The new tail, with stripes flying proudly …"
  - A new Flight Symbol ("the eagle, the star, the 'A'").
  - Core colours "red, white and blue … updated".
  - The first American Eagle aircraft in the livery flew in Feb 2013.
- 2021 update (S, Simple Flying):
  - the "Silver Eagle" grey **without mica** on repaints and all new deliveries;
  - the eagle logo was added to narrow-body winglets.

  This is why paint hue differs between airframes.
- Titles (S, Business Traveller 2013): "American" in big thin grey letters ahead of the wing.
- Hex (**unverified**): "AA Blue" #0078D2 (RGB 0/120/210) appears in a 2015 American advertising-guidelines PDF, of which only an unofficial copy was found (slideshare).
- Special liveries: centenary retro "Flagship" 777-300 N735AT, first flight Nov 2025 (O, news.aa.com 2025).

**9. American Eagle** (SkyWest E175 N501SY–N521SY at SFO). American livery with "American Eagle" titles (O: the 2013 release says Eagle aircraft adopt the livery; the titles are K).

**10. Southwest** (B737, B38M, B738). 2014 "Heart" livery (O).

- Source: Southwest release, 8 Sep 2014, https://investors.southwest.com/news-events/press-releases/detail/900/southwest-airlines-unveils-its-new-look-same-heart.
  - "the Southwest name on the side of the fuselage";
  - "the Heart on the aircraft belly";
  - "vibrant color palate and striped tail".
- Colour names (S, Dallas Morning News 2014-09-08, quoting Southwest): **Bold Blue, Warm Red, Sunrise Yellow, Summit Silver**.
- Hex (**unverified**, third party): Bold Blue #304CB2 (PMS 2126 C).
- Specials: "Independence One" and "Liberty One" for America250 (O, 2025–26), and state "One" aircraft.

**11. JetBlue** (A321, A21N). 2023 livery, being rolled out through the paint cycle (O).

- Source: JetBlue release, 14 Jun 2023, news.jetblue.com (link in §6).
  - "A blue allover fuselage";
  - "Iconic tailfin patterns … extended to embrace the body and belly";
  - the pattern and JetBlue logo on the belly;
  - "Colorful winglets … refreshed palette of accent colors";
  - "refresh all of its current standard liveries as part of its normal aircraft painting cycle".
- **Mid-transition:** the older white-fuselage, patterned-tail aircraft remain (inf from the O statement).
- Hex: none official found.

**12. Frontier** (A20N, A21N) (S).

- Each aircraft has its own animal on the tail, with the animal's name on the nose.
- A green "FRONTIER" title (the Saul Bass "F") since 2014–15.
- Source: Simple Flying guide; the official list of tails is https://www.flyfrontier.com/plane-tails/ (not fetched).
- Per-registration animal: **unverified**.

**13. Breeze** (BCS3). Revealed 13 Sep 2021 (O: Airbus release, https://www.airbus.com/en/newsroom/press-releases/2021-09-breeze-airways-reveals-new-a220-livery-confirms-order-for-20). The release has **no textual description**; the colours (navy / white / "breeze" blue) are **unverified**.

**14. Sun Country** (B738). 2018 livery (S, Star Tribune).

- A blue base with orange stripes and the retained sun logo. It is the "Tide Pod" design chosen by employee vote.
- A 2026 retro special exists (O, suncountryairlines.gcs-web.com).

**15. Air Canada Express (Jazz CRJ900) and Air Canada:** see §3.2. **Porter** (E195-E2): not researched in detail (**unverified**).

### 3.2 International brands at SFO (the 12 most frequent, plus notes)

| # | Brand (SFO types) | Current livery, essentials | Colour values | Source (provenance) |
|---|---|---|---|---|
| 1 | **Air Canada** (B38M, BCS3, A320; Air Canada Express CRJ9) | 2017 livery: ice-white fuselage; tail, engine cowls, belly and typeface in **black**; red maple-leaf rondelle on the tail, on the inner nacelles and on the belly. Designer Winkreative. | **AC Red #F01428** (PMS 1795 C, RGB 240/20/40); **AC Black #000000** | O: aircanada.com media page "Air Canada Unveils New Livery Inspired by Canada" (9 Feb 2017, no details in the page itself); colours O: *Air Canada Foundation usage guideline*, aircanada.com/content/dam/aircanada/portal/Legacy/foundation/ACF_Guidelines_en.pdf; layout S: CBC / AirlineGeeks. Express: same livery with "Air Canada Express" (K) |
| 2 | **EVA Air** (B77W, B789) | Updated livery (2015): white fuselage, pearlescent white paint, darker green belly, green tail with the orange globe, orange removed from the rudder | none official | S: AirlineReporter 2015-11 "EVA Air Shows Off New Livery" |
| 3 | **Aeroméxico** (B38M, B738, B39M) | Navy "Caballero Águila" tail. An updated, more human-faced Caballero Águila was unveiled 28 Aug 2024 (90th anniversary) on E190 XA-IAC and "will gradually be applied" to the fleet, so the fleet is **mid-transition**. Special "Kukulcán" 737-9. | none | S: breitflyte / Simple Flying, 2024. The fuselage layout is **not verified** |
| 4 | **Cathay Pacific** (B77W, A359) | 2015 refresh: all-green tail with the white brushwing; "Cathay Pacific green, grey and white"; an enlarged brushwing on the nose; name above the windows; one light-grey band along the fuselage. Fleet repainted over about 5 years. | none | O: news.cathaypacific.com "New era begins for Cathay Pacific as airline unveils changes to aircraft livery" (1 Nov 2015); details S: AirlineGeeks |
| 5 | **Avianca** (TACA El Salvador A20N) | 2023 brand: lowercase "avianca" wordmark in a brighter red; the fuselage stays white; the tail symbol is slightly altered and the orange removed, so the tail uses two colours. The red tail and red nacelles continue (S). Older (2013) and 2023 aircraft coexist, so the fleet is mid-transition (inf). | none | O: avianca.com/en/about-us/av-news/2023/october-18/; S: Aeroflap, AirlineGeeks 2026-07-31 |
| 6 | **Singapore Airlines** (A359) | Midnight-blue and gold: gold Kris bird on a midnight-blue tail; white fuselage; blue "SINGAPORE AIRLINES" titles; blue and gold cheatlines. Essentially unchanged since 1972 / 1987. | none | S: AirlineGeeks 2026-08-21, Simple Flying |
| 7 | **Japan Airlines** (B789, B77W, B788) | 2011 "Tsurumaru" red crane on the tail; plain white fuselage; black "JAPAN AIRLINES" titles above the windows | none | S: Japan Times 2011-03-01, AirlineGeeks 2025-09-12 |
| 8 | **ANA** (B77W) | "Triton Blue" (since 1982): white and grey fuselage, blue stripe under the windows, blue tail with "ANA" | none | O: ANA 70th-anniversary archive, https://www.ana.co.jp/group/en/70th/archives/ap13/; S: AirlineGeeks 2026-09-18 |
| 9 | **British Airways** (A388, B77W) | Chatham Dockyard Union-flag tail; bright-white upper fuselage; midnight-blue belly; red "Speedwing" / Speedmarque; titles under the window line. Colours: pearl grey, midnight blue, brilliant red. | none | S: Simple Flying, key.aero "How British Airways got its latest livery" |
| 10 | **Lufthansa** (B748, A359, A388, B744) | 2018 "Lufthansa blue": dark-blue tail wrapping onto the aft fuselage, with a white crane (silver ring); the grey underbody replaced by white; yellow demoted to a secondary colour. The fleet is mid-transition to 2018 paint (K: some 747-400s retire in the old colours). | hex **unverified** (#05164D third-party) | O: lufthansagroup.com/en/newsroom/releases/fleet/heritage-meets-the-future-lufthansa-presents-a-new-brand-design.html; S: dezeen 2018-02-05, Business Traveller |
| 11 | **Air India** (B77W, B772) | 2023 livery [corrected by verifier: "The Vista" is the name of the new logo symbol, not of the livery]: palette of **deep red, aubergine and gold**; gold window-frame motif; chakra-inspired pattern; "Air India Sans". First aircraft: A350 in Dec 2023. The fleet is **mid-transition**; legacy aircraft are still in the old livery (inf). | names only | O: airindia.com newsroom "A new Air India is unveiled …" (10 Aug 2023) |
| 12 | **WestJet** (B737, B738, B38M) | 2018 livery (first on the 787-9, 737 MAX 8 from June 2018): white fuselage, teal/blue scheme, maple leaf on the tail. [added by verifier: the release says it will "gradually appear across WestJet's entire fleet … as aircraft are repainted in their normal cycle", so older aircraft may still be mid-transition] | none | O: westjet.mediaroom.com 2018-05-08 "WestJet unveils its Dreamliner 'Spirit of Canada'"; S: AirlineGeeks 2024-11-01 |
| — | Turkish (A359) | White fuselage, blue titles, grey tulip mid-to-aft, red tail with the logo in a circle (since 2010) | — | S |
| — | Virgin Atlantic (B789, A35K) | 2019 "Flying Icons" (five figures replace the Flying Lady) on metallic-grey fuselage with purple titles and a metallic red tail | — | S: Virgin.com, Johnson Banks |
| — | Air France (B77W, A359) | Eurowhite fuselage, tricolour tail stripes | — | S |
| — | Korean Air (B78X, B77W) | **New livery 11 Mar 2025**: metallic sky-blue paint, bold "KOREAN" logotype, cheatline replaced by a flowing curve, dark-blue Taegeuk. The fleet is **mid-transition** from the 1984 livery. | — | S: samchui.com, TTG Asia, Simple Flying (Korean Air newsroom not fetched) |
| — | Emirates (A388), Copa (B39M), Starlux (A359), ZIPAIR (B788), PAL, China Airlines, Swiss, Asiana, KLM, Porter (E295) | not researched in this pass | — | **unverified** |

## 4. Openly-licensed livery textures that fit our models

### 4.1 Where our models come from, and the licence (O)

- `tools/convert_models.py` takes 20 models from **Ysurac/FlightAirMap-3dmodels** @0906d9b (FAM) and `b738` from **FGMEMBERS/737-800** @9126249.
- FAM pins its FlightGear sources as git submodules (gitlinks without a `.gitmodules`). For example, `a320/A320-family` → FGMEMBERS/A320-family @0b928542.
- `tools/models/livery_sources.py` compares the FAM `.glb` embedded textures with the textures at the pinned FlightGear commit, pixel for pixel (64×64 grey, mean absolute difference).

| Our key | FAM file | FlightGear source @ pinned commit | Licence file at that commit | Embedded texture = FG texture? |
|---|---|---|---|---|
| a319, a320, a321 | a320/glTF2/A319/A320/A321.glb | A320-family @0b928542 | COPYING (GPL-2.0) | Same UV layout, different paint. FAM's "A320-NWA.png" holds an Airbus house scheme on the FG NWA template (mad 0.15; visually identical layout). A321-House mad 0.005 |
| a333 | a333/glTF2/A333.glb | A330-300 @7d930769 | COPYING (GPL-2.0) | identical (mad 0.000) |
| a359 | a350/glTF2/A350.glb | A350XWB @407f422a | COPYING (GPL-2.0) | identical. The FG `.ac` changed after the pin, so HEAD liveries may not fit |
| a388 | a380/glTF2/A380.glb | A380-omega @ffb200c2 | COPYING (GPL-2.0) **[corrected by verifier: see the caveat below the table]** | identical except the fuselage `F-WWDD` (no same-name file). `.ac` changed after the pin |
| b744 | b744/glTF2/B747.glb | 747-400 @99e62214 | COPYING (GPL-2.0) | identical |
| b748 | b748/glTF2/B748.glb | 747-8i @3f7bcacb | LICENSE (GPL-2.0) | identical |
| b752 | b752/glTF2/B752.glb | 757-200 @363ac0b9 | LICENSE ("GPL v2 or later") | textures unnamed in the glb, no match. FG has no livery PNGs at the pin. `.ac` changed after the pin |
| b763 | b767/glTF2/B763.glb | 767 @a31798b2 | COPYING (GPL-2.0) | identical wing; the TFL livery mad 0.05 (re-encoded) |
| b788 | b788/glTF2/B788.glb | 787-8 @c0f1f92f | COPYING (GPL-2.0) | identical |
| bcs1, bcs3 | bcs1/glTF2/BCS1/BCS3.glb | **CSeries @8a8223f3** | **COPYING (GPL-2.0)** | cs300.png identical; the BCS1 node names equal the CS100.ac object names. **This resolves the HANDOFF licence question for the A220 models** |
| crj2 | crj2/glTF2/CRJ2.glb | CRJ-200 @24fc7611 | COPYING.txt (GPL-2.0) | identical (UAX.png, a United Express scheme) |
| crj7, crj9 | crj9/glTF2/CRJ7/CRJ9.glb | CRJ700-family @4862db2f | LICENSE ("All models, textures, markup and scripts licensed under the GNU GPL, version 2 or above") + GPL-2 + FDL-1.3 (docs) | identical |
| e170, e75l, e190 | e190/glTF2/E170/E75L/E190.glb | E-jet-family @9a9b6d06 | License.txt (GPL-2.0) | identical |
| md11 | md11/glTF2/MD11.glb | MD-11 @c88139fc | LICENSE ("GPL v2 or later") | identical. `.ac` changed after the pin |
| b738 | FG 737-800 .ac files directly | 737-800 @9126249 | LICENSE (GPL-2.0) | same source |

**A380 licence caveat [corrected by verifier].** At the pin, A380-omega also has a `License/` directory holding `README`, `cc-by-nc-3.0.txt` and `gpl-2.0.txt`. `License/README` (`git show ffb200c2:License/README`) says that until 31 May 2015:

> "All work (the textures, flightdeck, new systems, parts of the FDM, and instruments) done by the following authors - Toryx, Tapaninen, Muraleedharan - are shared under the CC-BY-NC v3.0 license."

The relicensing note above it is by IH-COL, 1 June 2015. It relays only Narendran Muraleedharan's ("Omega") consent: "Omega has accepted to release all of his work under GPL license code". That consent was itself relayed second-hand, as a forum post quoting a Facebook post: https://forum.flightgear.org/viewtopic.php?f=4&t=26400&p=244775. There is no record that Toryx or Tapaninen relicensed their textures. Our A380 textures are `wing.png`, `tail.png`, `extra.png` and `rr_fan.png`, plus the untraced `F-WWDD`. So their GPL status is **unverified**, and they may still be CC-BY-NC 3.0 (non-commercial only). The `livery_sources.py` licence regex does not see files inside `License/`.

The E-jet-family liveries (e.g. `ERJ175/UnitedExpress.png`, `ERJ175/Delta.png`) are watermarked "Made by theomegahangar.yolasite.com". Their repository is GPL-2.0 (`License.txt`), and the same 2015 relay covers Omega's own work.

**GPL caveat.** GPL-2.0 covers the copyright in the textures. It does **not** license the airlines' **trademarks** (names, logos, tail art) painted on them.

The app deliberately uses "generic schemes; no logos or wordmarks" (`js/aircraft/fleet.js`), and `convert_models.py neutralize()` strips saturated paint from the textures. Whether to show real logos is a decision for the owner (§7). It is a trademark and publicity question, not a copyright one.

### 4.2 Which liveries fit which UV layout (checked by contact sheets of the actual textures)

A livery fits a model if it was painted for the same FlightGear model file (same UV unwrap). I checked this visually: default texture next to candidate liveries, sheets in the session scratchpad; regenerate them with the tool.

| Our model | Liveries at the pinned commit that fit, for SFO brands (file) | Currency (K: compared with §3) | Do not fit |
|---|---|---|---|
| **b738** (737 family, all B73x/B3xM) | `Liveries-800/AAL.png` (American 2013 ✓), `N563AS.png` (Alaska 2016 ✓), `DAL.png` (Delta ✓; [corrected by verifier] the 2007–2015 variant: its navy belly has no white "DELTA" title, which Delta added in May 2015 per the Delta Flight Museum), `UAL.png` (United 2010 Globe = legacy livery), `KAL.png` (old Korean), `CAL.png` (China Airlines), `AVA.png` (Avianca, pre-2023), `KLM*.png`, `THY-800.png`, `ASA.png` (Alaska pre-2016) | AAL, Alaska, DAL current; UAL legacy (still on a minority of United aircraft) | — |
| **a319/a320/a321** | root `Models/A320-*.png`: `A320-UAL.png`, `A320-UAL2.png`, `A319-UAL.png` (United, older), `A320-DAL.png` (Delta ✓), `A320-BAW.png` (BA ✓), `A320-ACA.png` (Air Canada pre-2017), `A320-AVA.png` (Avianca 2013), `A320-AFR*.png`, `A320-SWR.png`, `A320-PAL.png`, `A320-DLH.png` | DAL, BAW current | the per-variant folders `A319-111/`, `A320-211/`, `A320-231/` (for example `A320-231/JBU.png`) are later models: layout **not checked**, assume not |
| **e75l / e170 / e190** | `ERJ175/UnitedExpress.png` (2010 Globe style, legacy), `ERJ175/Delta.png` (Delta Connection ✓), `ERJ175/AirCanada.png` (pre-2017), `ERJ170/Delta.png`, `ERJ190/ACA.png` | Delta Connection current; United Express legacy; no Alaska, American Eagle or Horizon E175 texture exists | each E-Jet length has its own layout; a livery only fits its own length |
| **crj7 / crj9** | `CRJ900/SKW.png` (Delta Connection CRJ900 ✓), `CRJ900/JZA*.png` (Air Canada Jazz, the 2005–2011 "Jazz" scheme: legacy) | no Air Canada Express (2017) texture | `CRJ700/`, `CRJ700ER/` folders (not checked) |
| **crj2** | `SKW.png` (older SkyWest/United Express), `JZA_*.png` (Jazz, legacy) | none current | — |
| **b788** | `AAL.png` (American ✓), `AIC-SA.png` (Air India Star Alliance special) | American current | `DAL-Livery.png` (1024 px, different layout) |
| **b763** | `767-300ER/UAL.png` (United, older; layout not viewed), `DAL.png` (Delta ✓), `ACA.png` (pre-2017), `BAW.png`, `ANA.png`, `AFR.png`, `AMX-skyteam.png`, `JAL.png`, `KLM.png` | DAL current | — |
| **a359** | `AFR.png`, `AVA.png`, `QTR.png` | AFR current | **`CPA.png`** (Cathay) has a different layout: it does not fit our A350 |
| **a333** | `A330-343/`: `CPA.png`, `SIA.png`, `SWR.png`, `THY.png`, `VIR.png`, `DLH.png`, `ACA.png`; `A330-323/DAL.png`, `KAL.png` | mixed, mostly legacy | — |
| **b748** | `748I/DLH.png` (Lufthansa pre-2018), `DLH_retro.png`, `BAW_fuselage.png`, `Klm_fuselage.png`, `Afr_fuselage.png`; `748F/CPA.png`, `KAL-cargo.png` | none current for Lufthansa (2018 blue) | — |
| **b744** | `Liveries/DLH.png`, `BAW.png`, `CPA.png`, `KAL.png`, `UAL*.png`, `DAL.png`, `CAL.png`, `EVA.png` (layout not viewed) | mostly legacy | — |
| **bcs1 / bcs3** | CSeries: only Bombardier/demo, `swiss.png`, `BTI.png` (airBaltic), `merlion.png` | no Delta, JetBlue, Air Canada or Breeze A220 texture | — |

**Summary.**

- Open FlightGear textures that are both current in 2026 and UV-compatible exist only for:
  - American (737-800, 787-8);
  - Alaska (737-800, N563AS);
  - Delta (737-800, A320, 767-300ER, E175, CRJ900);
  - British Airways (A320).
- **United mainline and United Express (2019 livery), Southwest, JetBlue (2023), Air Canada (2017), Alaska-branded E175 and American Eagle E175 have no fitting open texture.** Together that is about 75 % of SFO landings [corrected by verifier: it is 67.7 % (128,078 of 189,132), or 68.1 % with Air Canada Express. The brands that do have a current, fitting texture (American, Alaska mainline, Delta, Delta Connection, BA) make up 20.2 % of landings. Counting only the types those textures actually fit (737 family, A320 family, 767, 787, E175) gives 13.6 %. The BA A320 texture adds nothing, because BA flies only the A388 and B77W at SFO]. For these, the procedural/neutralised livery with parametric colours (§5) is the only licence-clean route.

### 4.3 How our converted models keep textures

- `convert_models.py` keeps UVs (quantised u16 per vertex) and one texture per material. It **neutralises** paint on the base, fin, engine and gear-door zones (`neutralize()`: saturated pixels plus enclosed lettering → the skin white level).
- The runtime shader (`js/shaders/aircraft_real.js`) then applies the parametric livery colours (`uLivTop/Belly/Tail/Engine/Stripe`, `uBellyLine`, `uTailStyle`) by zone.
- So the UV unwrap survives, and a FlightGear livery can be dropped in as a replacement texture for the same model, if the texture is *not* neutralised. Textures are 1024–4096 px PNG (2–6 MB each), which matters against the 16 MB artifact budget.
- Every model keeps its zones (base / fin / engine / gear / gdoor / glass / light / pylon). The b738 model also keeps its real gear.

## 5. Recommendations

1. **Brand rule.**
   - Ship `tools/models/out/regional_brands.json`, reduced to SFO-relevant tails (~290 entries), into the app data.
   - Replace `AIRLINE_LIVERY.SKW = 'UAL'` with: tail → brand, then series fallback, then operator majority.
   - Add `QXE` (Horizon) → Alaska, `JZA` → Air Canada Express, and `TAI` → Avianca (TACA flies Avianca colours).
   - [corrected by verifier] In the live app the change belongs in `js/live/lookup.js` (`liveryForAirline`, `SAME`), which currently leaves SKW on `NEUTRAL`. `fleet.js` is only used by the cinematic renderer. `QXE → 'ASA'` already exists in `lookup.js` `SAME`; `JZA` and `TAI` are missing.
   - Keep `brand_src: 'obs' | 'inf'`.
   - Refresh the table monthly (BTS lag ~2 months).
2. **Parametric liveries per brand (licence-clean).**
   - Encode §3 as data: base, belly (colour + line height), tail colours or gradient, nacelle, winglet, stripe/swoop, title colour and position.
   - Use the official brand hex where one exists (Delta, Air Canada). Otherwise use photo-sampled paint colours, recorded as `measured` with the photo URL.
   - Add per-registration overrides for special liveries (United "Mountain Ascent" N645SY, American retro N735AT, Southwest "One" aircraft, Delta Team USA A350).
   - Add per-airline transition flags: United Globe vs 2019, Korean 1984 vs 2025, Aeroméxico 2024, Air India 2023, JetBlue 2023, Avianca 2023. Where a per-tail truth is not available, render the new livery (the majority by 2026, inf) and mark it `inf`.
3. **Textures.**
   - Where a current, fitting GPL texture exists (§4.2), `convert_models.py` could emit an optional un-neutralised livery texture per airline, keyed by model.
   - **Decide the trademark question first** (§7).
   - Keep the GPL notice and source link (FGMEMBERS repo + commit) next to each shipped texture.
4. **Before publishing any page:** list the model and texture sources and their licences in an about box. GPL-2.0 requires the source to be offered for the derived model files.

## 6. Sources (URLs)

**Data**
- DataSF / SFO Air Traffic Landings Statistics: https://data.sf.gov/d/fpux-q53t (API `https://data.sf.gov/resource/fpux-q53t.json`), ODC-PDDL 1.0
- BTS Marketing Carrier On-Time Performance: https://transtats.bts.gov/PREZIP/On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_2026_7.zip (and `_2026_5`, `_2026_6`)
- FAA Releasable Aircraft Database: https://registry.faa.gov/database/ReleasableAircraft.zip
- ICAO Doc 8643 designators (OpenSky mirror): https://s3.opensky-network.org/data-samples/metadata/doc8643AircraftTypes.csv
- tar1090-db (the adsb.fi / adsb.lol aircraft database): https://github.com/wiedehopf/tar1090-db (branch `csv`, commit d9459d7, 21 Sep 2026)
- FAA TCDS A21EA (CL-600-2C11 = Regional Jet Series 550): FAA DRS, https://drs.faa.gov (not fetched; from a search summary, **S**)

**Liveries**
- United, 2019: https://united.mediaroom.com/2019-04-24-Out-with-the-Gold-in-with-the-Blue-United-Airlines-Unveils-its-Next-Fleet-Paint-Design
- United Express E175 "Mountain Ascent": https://worldairlinenews.com/2026/09/04/united-airlines-unveils-a-new-mountain-ascent-livery-on-n645sy/
- United Coastliner: https://airlinegeeks.com/2026/03/24/united-details-sweeping-fleet-upgrade-premium-expansion/
- United repaint count (forum): https://www.airliners.net/forum/viewtopic.php?t=1507131
- Alaska 2016: https://news.alaskaair.com/alaska-airlines/about-brand-refresh/
- Alaska Global livery: https://news.alaskaair.com/images-videos/alaska-airlines-global-livery/ ; https://www.airwaysmag.com/new-post/in-photos-alaska-airlines-new-global-livery
- Alaska Brand Guidelines 2019 R13 (unofficial copy): https://www.scribd.com/document/500332867/Alaska-Brand-Guidlines-2019-R13
- Hawaiian 2017: https://news.alaskaair.com/releases/hawaiian-airlines-unveils-new-brand-and-livery/
- Delta brand guidelines 2018: https://waatbp.oneclub.org/wp-content/uploads/2024/08/Delta_Brand_Guidelines.pdf ; Delta logos page: https://news.delta.com/delta-air-lines-logos-and-brand-guidelines ; Delta Flight Museum: https://deltamuseum.org/research/history/delta-brand/aircraft-livery/mainline-livery-1029-present
- American 2013: https://news.aa.com/news/news-details/2013/American-Airlines-Debuts-New-Modern-Look/default.aspx ; Silver Eagle: https://simpleflying.com/american-airlines-updated-livery-many-unaware/ ; centenary retro: https://news.aa.com/news/news-details/2025/American-Airlines-unveils-special-Flagship-livery-ahead-of-centennial-year-CENT-10/default.aspx
- Southwest 2014: https://investors.southwest.com/news-events/press-releases/detail/900/southwest-airlines-unveils-its-new-look-same-heart ; colour names: https://www.dallasnews.com/business/airlines/2014/09/08/we-have-more-on-the-new-southwest-airlines-colors/
- JetBlue 2023: https://news.jetblue.com/latest-news/press-release-details/2023/JetBlue-Introduces-Its-Boldest-Bluest-Plane--Ever--With-Livery-Refresh-Reflecting-Its-Role-as-Industry-Disruptor/default.aspx
- Frontier tails: https://simpleflying.com/frontier-airlines-animal-tail-liveries-guide/ , https://www.flyfrontier.com/plane-tails/
- Breeze: https://www.airbus.com/en/newsroom/press-releases/2021-09-breeze-airways-reveals-new-a220-livery-confirms-order-for-20
- Sun Country: https://www.startribune.com/first-look-at-the-new-paint-job-on-sun-country-s-airplanes/499049761
- Air Canada: https://www.aircanada.com/ca/en/aco/home/about/media/new-livery.html ; colours: https://www.aircanada.com/content/dam/aircanada/portal/Legacy/foundation/ACF_Guidelines_en.pdf ; layout: https://www.cbc.ca/news/business/air-canada-colours-1.3974114
- EVA Air: https://www.airlinereporter.com/2015/11/eva-air-shows-off-new-livery-vision-future/
- Aeroméxico 2024: https://www.breitflyte.com/post/aeromexico-unveils-new-aircraft-livery-as-part-of-90th-anniversary-celebration
- Cathay Pacific: https://news.cathaypacific.com/new-era-begins-for-cathay-pacific-as-airline-unveils-changes-to-aircraft-livery-141164 ; https://airlinegeeks.com/2015/11/01/cathay-pacific-unveils-a-new-livery/
- Avianca 2023: https://www.avianca.com/en/about-us/av-news/2023/october-18/ ; https://www.aeroflap.com.br/en/the-airline-will-make-a-new-change-to-its-logo-see-what-the-painting-will-look-like-on-the-planes/ ; https://airlinegeeks.com/2026/07/31/livery-of-the-week-avianca/
- Singapore Airlines: https://airlinegeeks.com/2026/08/21/livery-of-the-week-singapore-airlines/
- JAL: https://www.japantimes.co.jp/news/2011/03/01/business/jal-revives-crane-logo-in-return-to-basics/
- ANA: https://www.ana.co.jp/group/en/70th/archives/ap13/
- British Airways: https://www.key.aero/article/how-british-airways-got-its-latest-livery ; https://simpleflying.com/british-airways-livery-evolution/
- Lufthansa: https://www.lufthansagroup.com/en/newsroom/releases/fleet/heritage-meets-the-future-lufthansa-presents-a-new-brand-design.html ; https://www.dezeen.com/2018/02/05/lufthansa-airline-updates-yellow-100-year-old-logo-livery-redesign/
- Air India: https://www.airindia.com/in/en/newsroom/press-release/a-new-air-india-is-unveiled--representing-bold-new-india-on-the-.html
- WestJet: https://westjet.mediaroom.com/2018-05-08-WestJet-unveils-its-Dreamliner-Spirit-of-Canada-to-the-world
- Korean Air 2025: https://samchui.com/2025/03/12/korean-air-unveils-new-corporate-identity-and-aircraft-livery/
- Virgin Atlantic: https://www.virgin.com/about-virgin/latest/hello-virgin-atlantics-new-flying-icons

**Models and textures**
- https://github.com/Ysurac/FlightAirMap-3dmodels (0906d9b)
- FGMEMBERS repos: A320-family, A330-300, A350XWB, A380-omega, 747-400, 747-8i, 757-200, 767, 787-8, CSeries, CRJ-200, CRJ700-family, E-jet-family, MD-11, 737-800 (https://github.com/FGMEMBERS/<name>, commits as in §4.1), cloned blobless into `refs/cache/src/fg/`

## 7. Open questions for the owner

1. **Trademarks.** GPL textures from FlightGear carry real airline names, logos and tail art. Do you want real brand marks rendered, or should we keep brand-coloured but logo-free schemes (the current policy)? This decides whether §4.2 textures are usable at all.
2. **United legacy vs 2019 livery per tail.** No open per-registration source was found. Is rendering every United aircraft in the 2019 livery acceptable (the majority in 2026, inf), or should we collect a per-tail list?
3. **E175 wing per tail.** Should E75L airframes get the 28.65 m long-wing geometry? The ADS-B databases code all US E175s as E75L, but older SkyWest airframes (FAA model "ERJ 170-200 LR") may be the 26.00 m winglet version, while "LL" may be the enhanced wingtip. That is **unverified**; the UK CAA TCDS link returned 404.

   [corrected by verifier] "LL" is **not** the wingtip. ANAC TCDS EA-2003T05-24 (5 Feb 2018, https://sistemas.anac.gov.br/certificacao/Produtos/Espec/EA-2003T05-24i.pdf) lists "ERJ 170-200 LL, approved on 05 February 2018" with "70 Passengers (170-200 LL)", so LL is the 70-seat model. The E175 APM §2.2.2 gives the 28.65 m span "on aircraft with extended wingtip or Post-Mod SB 0170-57-0058". The TCDS applies the later certification amendments to "S/N 17000376 thru 17000378, 17000381 thru 17000388, 17000390, 17000392 and on, or with post-mod SB 170-57-0058". Inferred from these two documents: an E175 has the long wing if its S/N is in that range or it has the SB.

   The FAA MASTER (23 Sep 2026) serials show that every SkyWest E175 in the BTS months (265 airframes, e.g. N125SY 17000440, N408SY 17000902) and all 49 Horizon E175s are in the long-wing range. Only the Delta-owned N603–614CZ (S/N 17000181–17000198) fall below it; they are short-wing unless retrofitted. tar1090-db codes those as E75L too.
4. **Official colour values.** Only Delta and Air Canada publish values we could fetch from an official host. [corrected by verifier: for Delta only Blue #003366 and Red #C01933 come from an official host (the news.delta.com palette image). The 2018 PDF with the Light and Dark Reds is hosted by a third party. The Air Canada values come from the Air Canada Foundation logo guideline (Dec 2017) on aircanada.com, which is a logo spec, not a paint spec.] For the others, may we measure paint colours from official press photos (reference only, recorded with URL), or will you supply brand guideline documents?
5. **Alaska Brand Guidelines 2019.** The hex values come from an unofficial Scribd copy. Can you obtain the original?

## Verification (adversarial check)

Independent re-check, 24 Sep 2026, done by re-fetching the sources and re-running the computations (scratch work in the verifier's session scratchpad; nothing in `data/` or `js/` touched).

- **Methods.**
  - DataSF: re-queried with SoQL aggregation, a different code path from `sfo_census.py`.
  - BTS: recounted with a separate script over the three monthly CSVs. The cached zips match the live BTS `Content-Length` and `Last-Modified` headers.
  - Licences: licence files read with `git show <pin>:<file>` in every FGMEMBERS clone.
  - Web pages: fetched with curl, or with WebFetch where the host returned 403 to curl.
- **Verdicts.** "confirmed" means the source says it. "refuted" means corrected inline and marked **[corrected by verifier]**. "unverifiable" means the source was not reachable or not checked.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | 189,132 passenger landings Aug 2025–Jul 2026; UA 41.0 %, SkyWest-for-UA 11.8 %, DL 7.3 %, AA 6.2 %, AS 5.9 %, WN 5.1 %, SkyWest-for-AS 3.6 %, … and the model breakdowns in §1.1 | confirmed | SoQL `sum(landing_count)` with `activity_period between 202508 and 202607 and landing_aircraft_type='Passenger'` gives 189132. Every pair total and model count in the §1.1 table rows checked matches. |
| 2 | DataSF fpux-q53t licence ODC-PDDL 1.0 | confirmed | `https://data.sf.gov/api/views/fpux-q53t.json`: licenseId `PDDL`, "Open Data Commons Public Domain Dedication and License". Rows updated 22 Sep 2026. |
| 3 | Republic, Mesa, PSA, Endeavor, GoJet, CommuteAir, Piedmont 0 landings; Envoy 1 | confirmed | DataSF operating-airline sums. |
| 4 | "B773" example "EVA B-KQF" | **refuted** | B-KQF is CPA870 (Cathay) in `data/snapshot.js`. The EVA B77Ws seen are B-16705 and B-16733 (recorder). |
| 5 | 77 airframes observed by 08:22 UTC, "mostly red-eyes" | **refuted (framing)** | 43 from the recorder up to 08:22 UTC plus 34 more only in the 23 Sep daytime snapshot; the union is 77. |
| 6 | Snapshot SKW249R N510SY = AA, N171SY/N408SY = AS, N125SY/N148SY = UA | confirmed | BTS 2026-05..07: N510SY AA 458/458 flights; N171SY AS 515; N408SY AS 516; N125SY UA 394; N148SY UA 417. |
| 7 | "The app currently paints them all United because `fleet.js` SKW='UAL'" | **refuted** | The live app uses `js/live/lookup.js` `liveryForAirline`. SKW is in neither `FAM` nor `SAME`, so it gets `NEUTRAL`. `fleet.js` is imported only by `js/scene.js` and `js/shots.js`. `QXE→ASA` already exists in `SAME`. |
| 8 | 1,519 regional tails; only N738EV multi-network | confirmed | Independent recount: 1519 tails, one multi-network tail, N738EV {AA 165, UA 55}, FAA model CL-600-2C11 (CRJ550). |
| 9 | "…over the 11 regional operators" | **refuted (minor)** | Only 10 operators have rows: OO 537, YX 215, MQ 187, 9E 145, OH 145, PT 71, YV 60, C5 56, G7 54, QX 49. ZW has 0. |
| 10 | BTS files are the official files | confirmed | Cached zip sizes 37262815 / 37040545 / 38717338 bytes equal the live `transtats.bts.gov/PREZIP` Content-Length. |
| 11 | SkyWest E175 series N103–168SY UA (53), N170–199 AS (27), N200–213 UA (11), N240–327 DL (81), N400–431 AS (16), N501–521 AA (20), N626–639 UA (12), N601–625UX UA (25), N603–614CZ DL (6), E170 N702–732SY UA (5); boundary N168/N170 sharp | confirmed | Recomputed runs by registration number and FAA model. |
| 12 | CRJ700/550 "N705SK–N742SK and N744SK–N774SK are AA" | **refuted (as registration blocks)** | These ranges hold DL and UA CRJ550s: N712SK DL, N738SK DL, N762SK UA, N767SK UA, N768SK DL, N771SK UA, N773SK UA. They hold only for CL-600-2C10. The per-tail-table conclusion stands. |
| 13 | CRJ200 SkyWest tails all United Express | confirmed | 85 of 85 CL-600-2B19 tails are UA. |
| 14 | "119 of 284 SkyWest E175 tails seen at SFO are UA" | **refuted** | 119 of 235 (tails with ≥1 SFO flight in BTS). 284 is not reproducible. |
| 15 | FAA owner field ≠ brand; SkyWest-owned E175s registered to SKYWEST AIRLINES INC | confirmed | Of the SkyWest-operated E175s: 219 "SKYWEST AIRLINES INC", 1 "SKY WEST AIRLINES INC" (N125SY), 45 United-owned, 6 Delta-owned. The SkyWest-owned ones fly for all four brands. |
| 16 | CRJ550 = FAA model CL-600-2C11 "Regional Jet Series 550" | confirmed; TCDS number unverifiable | Federal Register 2023-00130 abstract: "Model CL-600-2C11 (Regional Jet Series 550) airplanes". "A21EA" not re-read; search results show A21EA and A21EA-1. |
| 17 | United 2019 livery quotes (Rhapsody/United/Sky Blue, Runway Gray, gradient tail, logo "predominantly in Sky Blue", engines and wingtips United Blue, swoop, larger name, "Connecting people. Uniting the world.", regional aircraft "throughout the year") | confirmed | All phrases are verbatim at united.mediaroom.com (HTTP 200). |
| 18 | United Express E175 N645SY "Mountain Ascent" | confirmed (S) | worldairlinenews.com 2026-09-04: "Applied to an Embraer E175 … N645SY", flown by SkyWest. N645SY is not yet in the FAA MASTER of 23 Sep 2026 or in BTS. |
| 19 | United "Coastliner" special livery | confirmed (S) | AirlineGeeks 2026-03-24: "bright shades of blue wrapping the back third of the aircraft and United's name spelled out on its belly". |
| 20 | United repaint count (Airliners.net) | unverifiable | Not fetched. |
| 21 | Alaska 2016 colours "tropical green", "breeze, midnight, atlas and calm", expanded ruff, wordmark | confirmed | news.alaskaair.com, 25 Jan 2016, verbatim. |
| 22 | Alaska: tail-portrait livery stays on narrow-bodies; Global livery is 787-only | confirmed in substance; **quote refuted** | The quoted sentence is not on the cited Airways page or the press kit. An official Alaska release says the Alaska Native on narrow-bodies and Pualani on Hawaiian aircraft "are not going away". Airways: Global livery "applied to the entire 787 fleet". |
| 23 | Alaska Global livery "Aurora Borealis … deep midnight blues and lush emerald greens" | confirmed | Alaska press kit page, verbatim. |
| 24 | Hawaiian 2017: "purple, fuchsia and coral", Pualani "liberat[ed]" from the floral "holding shape", lei | confirmed | news.alaskaair.com archive of the 1 May 2017 release, verbatim. |
| 25 | Delta hex #003366 / PMS 654C, #C01933 / 187C, #E01933 / 186C, #991933 / 202C, greys #63666A #888B8D #A7A8AA #D0D0CE; Delta Brand Guidelines 29 May 2018 | confirmed (values) | The PDF re-downloaded from waatbp.oneclub.org is SHA-1-identical to the cache. The values are on PDF p.32; the TOC gives "Color Palette" at p.31. |
| 26 | Delta values "fetched from an official host" | **partly refuted** | The PDF host is oneclub.org, and news.delta.com has no link to it. The news.delta.com palette image (Oct 2016) confirms only Blue #003366 and Red #C01933 officially. |
| 27 | Air Canada AC Red #F01428 / PMS 1795 C / RGB 240-20-40, AC Black #000000 | confirmed | aircanada.com `ACF_Guidelines_en.pdf` re-downloaded, SHA-1-identical. It is the Air Canada *Foundation* logo guideline (Dec 2017), not a paint spec. |
| 28 | Air Canada 2017 layout: black tail, engines and belly; red leaf on fin; Winkreative | confirmed (S) | CBC 9 Feb 2017: "The tail, engines and undersides are black, but the red maple leaf icon will be on the fin … Winkreative". |
| 29 | Air Canada "ice-white", rondelle on inner nacelles and belly | unverifiable | Not in CBC; the aircanada.com media page has no description. |
| 30 | American 2013 quotes (silver mica, "stripes flying proudly", flight symbol, core colours, Eagle adopts livery) | confirmed | news.aa.com, 17 Jan 2013 (via WebFetch; curl gets 403). "the eagle, the star, the 'A'" is a paraphrase. "First Eagle aircraft Feb 2013" is not in the release (unverified). |
| 31 | American 2021 Silver Eagle paint without mica; eagle on narrow-body winglets | confirmed (S) | Simple Flying page. |
| 32 | American "Flagship" retro 777-300 N735AT, first flight Nov 2025 | confirmed | news.aa.com release of 15 Oct 2025: "a Boeing 777-300 next month". |
| 33 | Southwest 2014 quotes; colour names Bold Blue, Warm Red, Sunrise Yellow, Summit Silver | confirmed | investors.southwest.com release verbatim; Dallas News 2014-09-08 verbatim. |
| 34 | JetBlue 2023 quotes ("blue allover fuselage", "embrace the body and belly", winglets, "normal aircraft painting cycle") | confirmed | news.jetblue.com, 14 Jun 2023 (via WebFetch). |
| 35 | Breeze: Airbus release has no livery description | confirmed | airbus.com, 13 Sep 2021 (via WebFetch). |
| 36 | Cathay 2015: "Cathay Pacific green, grey and white", brushwing | confirmed | news.cathaypacific.com, 1 Nov 2015. |
| 37 | Lufthansa 2018 new brand design | confirmed | Official release, 07.02.2018 (web.archive copy; live page 403): "Dark blue becomes the leading brand color - yellow accentuates". "Grey underbody replaced with white" is from dezeen (S) only. |
| 38 | Air India 2023 "The Vista" livery; deep red, aubergine, gold; chakra pattern; Air India Sans; first A350 Dec 2023 | confirmed, **name corrected** | Release (web.archive): "The Vista" is the logo symbol. The palette, pattern, font and "December 2023 … first Airbus A350" are verbatim. |
| 39 | WestJet 2018 livery | confirmed; **addition** | westjet.mediaroom.com, 8 May 2018. The same release says the livery will "gradually appear … as aircraft are repainted in their normal cycle", so the fleet may be mid-transition. |
| 40 | Korean Air new identity 11 Mar 2025; Aeroméxico 28 Aug 2024 on E190 XA-IAC, "gradually" | confirmed (S) | samchui.com 2025-03-12. Search results (Simple Flying, AJOT, aviacionaldia). The cited breitflyte URL now returns 404. |
| 41 | EVA 2015 livery: darker green belly, orange removed from rudder | confirmed (S); "pearlescent" unverified | AirlineReporter 2015-11. |
| 42 | Every model source is FGMEMBERS at the listed pins, with the listed licence files | confirmed, **except A380** | All 14 pins exist in the FGMEMBERS clones (`git cat-file -t` → commit) with COPYING/LICENSE/License.txt as listed. CRJ700-family LICENSE and the 757/MD-11 "or any later version" text are verbatim. |
| 43 | A380-omega is GPL-2.0 | **refuted / unverified** | `License/README` at ffb200c2 records the textures as CC-BY-NC 3.0 until 31 May 2015. The relicensing relays only Omega's consent via a forum repost of a Facebook message. |
| 44 | A220 licence resolved: FAM bcs1 gitlink → FGMEMBERS/CSeries @8a8223f3 (COPYING GPL-2.0); cs300.png identical; BCS1 node names = CS100.ac names | confirmed, strengthened | Gitlink `160000 commit 8a8223f3…`. COPYING = GPL v2. The 6 named nodes are present in both files (71 shared names). BCS1 `cs100.png` = `Models/bombardier.png` (mad 0.0008); engines, interior and chrome mad 0.000. |
| 45 | FG texture list: AAL 2013, N563AS Alaska 2016, UAL 2010 Globe, ERJ175 UnitedExpress Globe, ERJ175 Delta Connection | confirmed | Viewed the textures at the pins. No Alaska, Horizon or American Eagle E175 livery exists at the pin or at HEAD. |
| 46 | `737-800/DAL.png` is current Delta | **partly refuted** | The belly has no white "DELTA" title, which Delta added in May 2015 (deltamuseum.org, verbatim). The texture dates from 2016-06-18 but paints the 2007–2015 variant. |
| 47 | Brands without a fitting open texture ≈ 75 % of landings | **refuted** | 67.7 % (128,078 / 189,132); 68.1 % with Air Canada Express. |
| 48 | (Summary) fitting textures exist for ≈ 25 % of SFO landings | **refuted** | 20.2 % at brand level (AA, AS mainline, DL, DL Connection, BA); 13.6 % for the types the textures fit. The BA A320 texture contributes 0 (BA flies A388 and B77W at SFO). |
| 49 | E175 "LL" is probably the enhanced wingtip | **refuted** | ANAC TCDS EA-2003T05-24: LL is a 70-passenger model (approved 5 Feb 2018). The long wing is set by S/N (17000376+, with exceptions) or SB 170-57-0058 (inf, from the TCDS and APM §2.2.2). |
| 50 | tar1090-db codes N125SY E75L "(long wing)" | confirmed | Clone at d9459d7 (21 Sep 2026): `A067EC;N125SY;E75L;00;EMBRAER ERJ-170-200 (long wing)`. It also codes N603CZ (S/N 17000181, probably short-wing) as E75L. |
| 51 | Third-party hex values (United #005DAA, Alaska Scribd, American #0078D2, Southwest #304CB2, Lufthansa #05164D) | unverifiable | Not re-fetched; the report already flags them as unverified. |
| 52 | Frontier, Sun Country, Singapore, JAL, ANA, BA, Virgin, Turkish, Air France details | unverifiable / partly | Sun Country (Star Tribune 429) and key.aero not reachable. ANA "Triton Blue" 1982, Virgin "Flying Icons" / "Flying Lady", Singapore blue-and-gold and JAL crane pages exist and match in substance. |

**Net effect on the recommendations.**
- The brand rule (§2) and its data are sound. Fix the SkyWest mapping in `js/live/lookup.js`, not only in `fleet.js`.
- The licence-clean parametric route (§5.2) is even more clearly necessary: textures cover only 13.6 % of landings, not 25 %.
- Treat the A380 textures as possibly non-commercial (CC-BY-NC 3.0) until the owner decides.
- Only Delta Blue and Red are official-host values for Delta.
