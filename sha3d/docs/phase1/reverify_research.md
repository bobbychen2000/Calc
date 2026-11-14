# C2 re-verify: Fix round 1 of research B1–B3

Written 2026-11-14. Owner decisions OD0–OD3 and the working defaults of `docs/PLAN.md` §6a/§6b apply. This report
checks the "Fix round 1" section of `docs/phase1/verify_research.md` independently. Where possible I did not reuse the
fixer's or C2's code. I recounted from the local per-flight tables, wrote my own heading, span, sequence and
air-time tests, scanned every committable text file for identifiers taken from the local tables, opened the owner
sample, and compared the photo credits with C2's cached Commons API answer.

**Labels:** **[obs]** = measured or read in this session. **[inf]** = inferred by a stated rule.

| Verdict | Meaning |
|---|---|
| **fixed** | The finding is resolved and the new numbers reproduce. |
| **partly** | Resolved where the fixer looked, but something is left. |
| **not fixed** / **regressed** | Still wrong, or made worse. |

**Rules kept**
- No call to api.adsb.lol or OpenSky. No network access was needed: every check ran on local files.
- Every script that reads downloads or the per-flight tables ran with `python3 -I`.
- This report gives aggregates only: no callsign, flight number, registration, ICAO address or per-flight time. The two
  remnants found in §2 are described by file and line, not repeated.
- I wrote only under `sha3d/`: this report and the check scripts in `tools/verify/reverify/`. Nothing was committed.
  `git status` shows no change in `sfo3d/`, `pc12/` or `hwd3d/`.

---

## 0. Verdicts in brief

| Finding (C2 §6) | Verdict | Evidence (§) |
|---|---|---|
| B1 #1: wrong-leg records; "all within ±20 min" | **fixed** | No record spans more than 2.1 h (was 7 over 4 h). My own heading test and C2's both find exactly 8 records over 90°: all departures to Shenzhen, first seen 15–26 km from ZGSZ. My sequence test (global air-time line) gives 0 impossible pairs; C2's gives 3, all of the Urumqi artefact the fixer describes. The wording is now 1-σ (§1.3). |
| B1 #2: M1 σ in-sample | **fixed** | The code takes M1 σ from leave-one-route-out (China) and from max(HKG–TPE, distance-band k-fold) (other). The values used per movement match the stats JSON. My own leave-one-route-out gives 16–23 min depending on the estimator, so 19.5–20.7 is out of sample, but rests on one dominant route. M1 is picked for 5 / 16 movements, none with a Chinese far end (§1.4). |
| B1 #3: per-flight statements in `observed_elsewhere.md` | **fixed** in the B1 files; **partly** across `docs/` | The B1 report, stats JSON and figure are clean. `verify_research.md` still names one observed callsign (line 259, C2's text) and one checked flight number (line 393, the fix-round text). Both are in the local observed tables (§2). |
| B1 #5: identified share | **fixed** | 542 / 550 = 69.2 / 70.2 % reproduce. The "upper figure; about 65–70 % defensible" reading is in the summary, §1.6, §7 and the stats JSON (§1.1). |
| B1 #6: 900–1,300 km China arrival bias | **fixed** | Removed for 56 / 71 arrivals (−6.6 / −4.5 min). The other-class 650–900 km bin (+2.4 / +2.1 min) covers 4 / 3 arrivals. The P90 cost is stated. The nested rule is sound (§1.5). |
| B1 #7: registry, inverse search, contradictions, 228 / 240 | **fixed** (one wording slip) | All as stated, except "half the contradictions are at the SHA end": the count is 4 of 10 (2 of 4, 2 of 6) (§1.1). |
| B1 re-run, stats, `src` / `evidence` | **fixed** | All 1,120 local records have a `src` dict (values `obs`, `inf` or null) and an `evidence` block. Every inferred field is `inf`; every record with an observed far-end event has `far_end_event: obs` (§1.1). |
| B1 owner sample (local) | **fixed** | 40 rows, git-ignored. 5 rows spot-checked field by field, and all 40 match an identified record exactly. It is deliberately spread, not random, and the README does not say so (§3). |
| B2 #4: runway rule in / out of sample | **fixed** | C2's script re-run: 86.3 / 78.0 / 80.4 % on 168 hints, against B2's 86.4 / 78.1 / 80.5 % on 169. `RunwayDirectionIntoWind` exists and matches the description (§4.1). |
| B2 #9: NOTAM table | **fixed** | `sources_sim.md` and the plate name only F4551, F4552, F4313, F4301, F4275/76 and the AMDT 12 trigger. They are paraphrased, and the F4552 link list is gone (§4.2). |
| B2 #10: Hong Kong and METAR wording | **fixed** | Both in `sources_sim.md` and `SOURCES_sim.json`; the NWS and IEM statements are quoted (§4.3). |
| B2 hourly profile | **fixed** | ×1.435, busiest hour 56.7 at 21 h, 408.2 + 375.2 = 783.4 reproduce from the B1 aggregates (§4.4). |
| B3 #8: photo credits | **fixed** | `photos_credits.md`: 23 rows, each matching C2's live Commons API answer on title, file page, licence, licence URL and author. 06 and 25 are listed as left out. "Scaled, not cropped" is true: PIL `thumbnail` on 1280 px renditions. Captions 09, 15, 18 and 19 are correct (§5.1). |
| B3 #11: layover factor | **fixed** | 1.2763 in the report, both tools and both JSON files. cot 38.08° = 1.27626; 42.7 m gives 33.46 m (§5.2). |

**New, low or cosmetic** (§6): the two remnants above; route-level M1/M2 offsets that a per-bin σ does not show; the
owner sample's spread is not stated; long Commons titles clip on the contact sheet; a stale code comment.

---

## 1. B1, recounted from the local tables [obs]

Script: `tools/verify/reverify/rv_b1.py`. It reads `refs/cache/observed_elsewhere/sha_observed_<day>.json` and `.csv`.
Airport positions come from the local OurAirports file. It shares no code with `tools/adsb/`.

### 1.1 Counts

| Quantity | Fix round 1 (report / stats JSON) | My recount: 10 Nov / 12 Nov |
|---|---|---|
| Rows on a VRS SHA route (JSON = CSV) | 558 / 562 | 558 / 562 |
| Identified (consistent track or far-end match) | 542 / 550 | **542 / 550**; the same set as the rows with a method |
| Arrivals / departures | 282 / 260, 287 / 263 | 282 / 260, 287 / 263 |
| Share of 783.4; of 802 | 69.2 / 70.2 %; 67.6 / 68.6 % | 69.2 / 70.2 %; 67.6 / 68.6 % |
| Distinct aircraft; registration or type empty | 232 / 248; 0 | 232 / 248; 0 |
| Duplicate callsign + role | – | 0 / 0 |
| DB-check classes | 132 / 118 far-end match; 2+2 / 4+2 far-end + SHA-end mismatches | Same. Contradictions: 4 of 136 and 6 of 124. 4 of the 10 are at the SHA end, so "half" overstates it slightly. |
| Far-end event observed | 132 / 118 | 132 / 118 |
| Nearest fix P10 / P25 / median / P75 / P90 / max | 213 / 247 / 588 / 854 / 1,110 / 1,238 and 214 / 244 / 625 / 907 / 1,113 / 1,235 km | Same. > 900 km: 114 / 142 (report 114 / 143, a boundary case); > 1,300 km: 0. |
| Type mix, 1,092 movements | 44.0 / 23.9 / 25.6 / 6.4 % | 44.0 / 23.9 / 25.6 / 6.4 % |
| Identified per hour, 06–24 local | 29.8 / 30.2 | 29.8 / 30.2 |
| Per airline (two-day mean) | CES 212, CQH 62, CSH 59, DKH 51 … | 211.5, 61.5, 58.5, 50.5. The figure rounds CSH to 58 and the table to 59. |
| `src` / `evidence` on every record | claimed | **0 records missing or malformed**, 1,120 checked. The CSV is a flat export with `reg_src` / `type_src` and `evidence_summary`; the full `src` dict is in the JSON. |

**Identified share.** The numbers reproduce. The upper-figure reading (HK and Taipei checked officially, domestic
labels resting on the DB) appears in the summary, §1.6 and §7 of `observed_elsewhere.md` and in the stats JSON
`readings.identified_share`. Fixed.

### 1.2 σ statements

| | Report | My recount: 10 Nov / 12 Nov |
|---|---|---|
| 1-σ median (P10–P90) | 9.4 (4.1–12.2) / 8.0 (4.0–11.4) min | 9.4 (4.1–12.2) / 8.0 (4.0–11.4) |
| Largest 1-σ | 18.6 / 16.2 min | 18.6 / 16.2 |
| Share with 1-σ ≤ 5 / 10 / 15 min | 26 / 51 / 92 % and 18 / 68 / 94 % | 26.4 / 50.6 / 91.5 % and 18.4 / 68.2 / 94.4 % |
| Share ≤ 19 min | all | 100 % / 100 % |

The report now says "1-σ is ≤ 10 min for 51–68 % … and ≤ 19 min for all. These are 1-σ values, not error bounds",
in the summary, §4 and §7. The stats JSON carries the same `sigma_note`. Fixed.

### 1.3 Wrong-leg records

| Test | Result on the Fix round 1 tables |
|---|---|
| **Span** (first to last fix of the identified record) | Longest 2.06 / 2.02 h. 0 records over 4 h (was 7). 0 records over the leg air time + 30 min. |
| **Heading**, my own: track at the fix nearest SHA against the bearing to SHA (arrivals) or from SHA (departures) | **8 over 90°** (3 / 5). All are SHA→Shenzhen departures first seen 15–25 km from ZGSZ at 4,500–7,800 ft, 102–147° off. No arrival is over 90°. |
| **Heading**, C2's `b1_heading2.py` re-run | The same 8 (16–26 km from ZGSZ). 0 records over 3 h. |
| **Sequence**, my own: same aircraft, consecutive SHA events; departure→arrival must allow 2 × air time (global M1 line) + 30 min, beyond 2 combined σ; arrival→departure ≥ 25 min | **0 impossible pairs** in 300 departure→arrival and 371 arrival→departure pairs. Turnaround minimum 45 min, P5 74, median 116. |
| **Sequence**, C2's `b1_sequence.py` re-run | 3 impossible pairs, all SHA–Urumqi round trips (638–649 min against 672). C2's test uses the China air-time line stretched to 3,272 km; the global line needs about 552 min. So these are artefacts of the test, as the fixer says. |

**The 8 Shenzhen-pattern departures.** These are not wrong legs: the landing at ZGSZ is observed on 6 of them, and
M1 and M2 differ by only 0.39–0.53 combined σ (§1.6). Leaving them untested within 60 km of the far end is reasonable.
They share the Shenzhen-departure offset in §1.6.

### 1.4 M1 σ out of sample [obs, code]

**Code** (`tools/adsb/observed_elsewhere.py`, `run` and `one_movement`):
- China: `airc = (a, b, sig(val['M1_cn_loro']))`, from leave-one-route-out residuals.
- Other far ends: `m1_sigma_other` = max(the held-out HKG–TPE σ, 1.4826 × median |error| of the 10-fold-by-route test
  in the route's distance band).
- The in-sample values are kept only as `in_sample_s` in the stats JSON.
- A stale comment above the k-fold block still says "cross-check only (not used for sigma)".

**Values carried by the records** (M1 candidate σ, every movement with an observed far-end event):

| | 10 Nov | 12 Nov | Stats JSON |
|---|---|---|---|
| China (LORO) | 1,244 s = 20.7 min (94 movements) | 1,172 s = 19.5 min (78) | 1,244 / 1,172 |
| Other, < 800 km | 448 s = 7.5 min | 423 s = 7.05 min | 448 / 423 |
| Other, 800–1,500 km | 712 s = 11.9 min | 488 s = 8.1 min | 712 / 488 |
| Other, 1,500–2,500 km | 1,128 s = 18.8 min | 1,062 s = 17.7 min | 1,128 / 1,062 |
| Other, > 2,500 km | not used | not used | 1,336 / 1,233 s (22.3 / 20.6 min) |

- **Method choice.** In every one of the 250 movements with both estimates, the pick is the smaller σ, and the
  record's σ equals the picked estimate's σ.
- **M1 picks:** 5 / 16, all to Songshan, Hong Kong or Macau. **0 M1 picks have a Chinese far end.**
- The report's "other far ends 7–19 min" leaves out the > 2,500 km band (20.6–22.3 min). No SHA far end that far takes
  M1, so it does not matter here.

**Independent leave-one-route-out** (`rv_m1loro.py`: my own calibration set from the scan files, with my own fits):

| Day | China flights / routes | Estimator | In-sample σ | LORO σ | LORO median \|e\| |
|---|---|---|---|---|---|
| 10 Nov | 72 / 6 (53 on Shenzhen–Xi'an) | Theil–Sen | 16.2 min | **21.7 min** | 14.7 min |
| | | OLS | 20.4 | 19.3 | 13.0 |
| 12 Nov | 71 / 5 (53 on Shenzhen–Xi'an) | Theil–Sen | 14.7 | **16.0** | 10.8 |
| | | OLS | 20.5 | 23.2 | 15.6 |

The calibration counts match B1's 72 / 71. The code's Huber values (20.7 / 19.5 min) lie inside my 16–23 min range,
so they are genuine out-of-sample values. But one route holds 74 % of the China set, so the number moves by ±4 min with
the estimator. The report already says the China set is small. It does not change any pick.

### 1.5 Bias removal

- **Counts in the records.** China 900–1,300 km arrivals carry `bias_removed` of −6.6 min (56 movements, 10 Nov) and
  −4.5 min (71, 12 Nov). Other-class 650–900 km arrivals carry +2.4 / +2.1 min (4 / 3). No other bin is corrected.
  This matches the report and `m2_bias_removed_movements`.
- **The nested rule** (`bias_correct`, `bias_used`) does what the report says. Each airport is corrected with the median
  of the other airports' errors, and removal requires a ≥ 5 % σ gain and a ≥ 2 min bias.
- **A pattern that looks odd but is not a bug.** In bins with a tiny pooled bias, the nested σ nearly doubles (e.g.
  China arrivals 200–300 km: 5.4 → 10.3 min). That happens when one airport dominates a bin and its errors differ from
  the others'. The rule then correctly declines to remove the bias.
- **The P90 cost** (20.7 → 24.6 and 20.2 → 25.9 min) is stated in §4.2, §4 and §7 of the report.

### 1.6 New cross-check: M1 against M2 where both exist [obs]

`rv_m1m2.py` compares the two estimates on the 132 / 118 movements whose far-end event was observed. The errors of
the two methods are probably positively correlated, so this test is lenient. Still:

| | 10 Nov | 12 Nov |
|---|---|---|
| Median \|M1 − M2\| | 9.8 min | 8.4 min |
| Within 1 combined σ / 2 combined σ | 91 % / 98 % | 85 % / 99 % |

**Overall the stated σ is not understated.** Two groups show systematic offsets, though:

| Group | n (two days) | Median M1 − M2 | Pick | Reading [inf] |
|---|---|---|---|---|
| SHA → Shenzhen departures | 76 | **−9.7 / −9.2 min** (range −17 to +1) | M2 (σ 11.4–12.2) | M2's 900–1,300 km departure bin has a stated, unremoved +4.8 / +5.3 min bias (too late). The sign agrees. These are the largest single far-end group (91–96 a day). |
| Xi'an → SHA arrivals | 41 | **+19.0 / +18.0 min** (range +11 to +29) | M2 (last fix 184–314 km out, σ 3.4–8.1 min, median 5.3) | Probably the China M1 line: about 128 min for 1,230 km, fitted mostly on Shenzhen–Xi'an. It is not picked, so no record is affected. |

Both offsets are within about 1 σ of the stated values, so this is not a defect of the fix. It does show route-level
effects that a per-bin σ cannot see. See §6, item 3.

---

## 2. Per-flight data in committable files [obs]

**Scope.** All files under `sha3d/docs/` and `sha3d/data/`: 80 files, of which 44 are text (`md`, `json`, `js`).
Phase 0 and `PLAN.md` are tracked. `docs/phase1/` and `data/` are untracked and meant to be committed. I also scanned
`tools/`.

**Method** (`rv_scan.py`):
- The exact sets from the local tables: 610 callsigns, the 610 IATA flight numbers derived from them, 383 registrations
  and 383 ICAO addresses.
- Generic patterns: callsign-like, flight-number-like (with an optional space), B- registrations, JA/HL registrations.
- Searches for epoch and ISO timestamps of 9–13 Nov.
- A walk of every list in `observed_elsewhere_stats.json`.
- The PNG text chunks of every image, and a visual check of `observed_elsewhere.png`.

| Where | Hits | Reading |
|---|---|---|
| `observed_elsewhere.md`, `observed_elsewhere_stats.json`, `observed_elsewhere.png` | **none** | Clean. The stats JSON has no per-flight list. Its only timestamps are the day windows and the VRS commit time. |
| `sources_sim.md`, `SOURCES_sim.json`, `sources_sim_*.json` | airline-code counts only ("MU 110, FM 80 …") | Clean. The record sketch uses placeholders. |
| `data/` (airport, stands, taxi graph) | none | Clean. |
| `photos_credits.md` (and `tools/photos`, `tools/fleet`) | registrations and two flight numbers inside Commons file titles from 2016–2023 | Not observed-elsewhere data. These are the titles of the works, needed for attribution. |
| `docs/phase0/fleet.md`, `field.md` (tracked) | registrations from public photos; historical flight numbers from news | Phase 0 public facts, with no times from our scan. |
| **`verify_research.md` line 259** (C2 §3.4) | **a callsign that is in the local observed tables**, with "does not match the observed record in type or time" | **Remnant.** The sentence says this flight was observed elsewhere on the scan days, and gives negative facts about its type and time. Replace it with "the sketch (placeholder callsign / type / time)". |
| **`verify_research.md` line 393** (Fix round 1, "Rules kept") | **a flight number** (written with a space) whose callsign is in the local observed tables and is one of the four in the schedule check | **Remnant.** With its public schedule and the report's landing range (−32 to +18 min), this bounds the flight's inferred landing time. Replace it with "one public schedule page (FlightMapper)". |
| `verify_research.md` line 219, `fleet.md` line 37 | "CI 78.4–94.1", "MU 66 …" | Pattern false positives. |

No ICAO address and no per-flight time appears anywhere. The fixer's regex scan covered "the committed B1 files"
only, which is why it missed the two remnants in `verify_research.md`. Both are low severity, but they break the
letter of the §6b default.

---

## 3. The owner sample (local) [obs]

`refs/cache/observed_elsewhere/sample_for_owner.csv` exists. It is git-ignored (`refs/cache/*`, confirmed with `git
check-ignore`). `README_sample_for_owner.md` sits beside it, and the folder's SOURCES.json says "WITHHELD".

| Check | Result |
|---|---|
| Rows, columns | 40 rows; the 11 columns listed in the README; no empty cell |
| Spread | 21 operators, 14 ICAO types, 19 local hours, 20 arrivals and 20 departures, 26 M2 and 14 M1. As claimed. |
| Spot check: rows 1, 6, 18, 27 and 40 (first, first M1, a later arrival, a 12 Nov row, last) | All 11 fields of each row (registration, type, operator, far end, direction, inferred local time, σ, method, nearest-fix km, consistency, evidence prefix) match the JSON record exactly. Each record's `src` marks the SHA time `inf` and the callsign `obs`. |
| All 40 rows | Each matches one identified record exactly (callsign, registration, inferred minute). |
| Obs / inf explanation | The README states per column what is observed and what is inferred, the 1-σ caveat and the M1/M2 meaning. |

**Sensible, with one caveat.** The sample is spread by design, not random. 14 of 40 rows are M1 against 1.9 % of all
movements; 13 of 40 are foreign carriers against 4 %; 24 rows come from 12 Nov. One row falls on local 13 Nov: a
post-midnight arrival of the 12 Nov operating day. The README should say in one line that the sample over-represents
M1 and foreign carriers, so the owner does not read it as typical.

---

## 4. B2 [obs]

### 4.1 Runway rule

I re-ran C2's `tools/verify/wx_check.py` (own parser) on the four IEM CSVs:

| Variant | C2 re-run (168 hints, 59 days) | B2 Fix round 1 (169 hints, 60 days) |
|---|---|---|
| Chosen rule, in sample | 145 / 168 = 86.3 % (bootstrap 78.4–94.1 %) | 146 / 169 = 86.4 % (78.3–94.7 %) |
| Same family, leave one day out | 131 / 168 = 78.0 % | 132 / 169 = 78.1 % |
| Into the wind | 135 / 168 = 80.4 % | 136 / 169 = 80.5 % |
| Literal 3 / 5 m/s | 64.9 % | 65.1 % |
| Chosen minus into the wind, 95 % CI | −0.7 to +13.8 pp | −0.7 to +13.1 pp (bootstrap noise) |

- The one-hint difference (99 against 98 for RWY 36) is consistent throughout.
- `sources_sim.md` §0 and §5.2 show in-sample and out-of-sample results side by side and say the advantage is not
  established. §7 repeats it.
- `metar_zsss.RunwayDirectionIntoWind` keeps the direction while |headwind| < 0.5 m/s and when calm, VRB or missing, as
  described. It ignores gusts.

### 4.2 NOTAM table

- **`sources_sim.md` §4.2** lists F4551, F4552, F4313, F4301, F4275/26, F4276/26 and the AIRAC AMDT 12 trigger.
  - Each is a paraphrase. F4552 now reads "17 short links … (names in the local JSON)", not the list.
  - None of the other 11 local NOTAM ids (17 in the summary) appears in B2's files.
  - No verbatim NOTAM text (Q/E lines, NOTAM abbreviations) was found.
- **The redrawn plate** `sources_sim_notam.png` shows the same 6 NOTAMs and the AMDT 12 line.
- **Observation, not a B2 issue:** C2's own `verify_research.md` §3.3 still names three non-applied NOTAMs: one with
  its crane height and position, a range "the previous phase", and one by id. These are short facts in a check table,
  acceptable under OD3. They could be trimmed to B2's set for consistency.
- **Still open:** the AD 2.20 quotes remain flagged for the owner's OD3 check.

### 4.3 Wording

- **Hong Kong.** `sources_sim.md`, "Rules we kept", says: "Hong Kong is a Special Administrative Region of the PRC
  with its own legal system". Downloading DATA.GOV.HK open data is not "data collection inside the PRC" in the §6b
  sense.
- **METAR status.** §3.1 and `SOURCES_sim.json` describe the reports as "NOAA/NWS (AWC) data" and "IEM archive". They
  quote the NWS and IEM statements, note that the AWC API page states no licence, and say the reports originate with
  the CAAC met service. "Public domain" appears only inside the hosts' quotes.

### 4.4 Hourly profile

From the B1 aggregates in the stats JSON: mean 546.0 identified a day, scale 783.4 / 546.0 = 1.4348, and day totals
408.2 arrivals + 375.2 departures. The busiest hour is 21 h with 56.7; 07 h has 28.7 departures and 1.4 arrivals.
`sources_sim_hourly.json` and §2.2 agree within rounding (408.3 / 375.1).

---

## 5. B3 [obs]

### 5.1 Credits and contact sheet

`rv_credits.py` compares `docs/phase1/photos_credits.md` with C2's cached live Commons API answer
(`refs/cache/verify_c2/commons/api_25.json`, independent of B3's SOURCES.json):

| Check | Result |
|---|---|
| Rows | 23 (01–05, 07–24), the photos on the sheet |
| Title, Commons file-page URL (decoded) | 23 / 23 match the API titles |
| Licence short name and licence URL | 23 / 23 match: CC BY 4.0 × 3, CC BY-SA 4.0 × 14, CC BY-SA 3.0 × 4, public domain × 2 (file-page link given) |
| Author | 23 / 23 match the API Artist. For 15 the API field holds the name plus a camera sentence; for 18 the name with leading whitespace. The credits now show the clean name. |
| Restrictions | none set |
| Left out | 06 (identifiable people) and 25 (GFDL 1.2 only), both listed under "Not on the sheet" with author and licence |
| Modification notice | on every row and in the sheet footer: "scaled down … whole frame, not cropped; caption added" |
| "Scaled, not cropped" | true: `contact_sheet.py` uses PIL `thumbnail` (keeps the aspect ratio), and all 23 sheet photos are 1280 px renditions |
| Compilation licence | CC BY-SA 4.0. BY-SA 3.0 inclusion is explained; BY 4.0 and PD files keep their own terms. |

**On the sheet:**
- Tile 09 reads "T2 airside: curtain wall, fixed links, bridge (2013)".
- Tiles 15 and 18 show clean author lines.
- Tile 19's Japanese author name renders.
- The footer points to `docs/phase1/photos_credits.md`.
- **Cosmetic:** long Commons titles run past their tile and are clipped where the next tile starts (01, 04, 05, 08,
  22). The full titles are in the credits file, so the attribution is complete.

### 5.2 Layover factor

- cot 38.08° = 1.27626.
- The text now says 1.2763 in `standards_refs.md`, `umbra_layover.py`, `heights_summary.py`,
  `b3_building_heights.json` and `stand_sar.json`. `b3_umbra_layover.json` keeps the exact K = 1.27627.
- 42.7 m of layover gives 33.46 m, stated as 33.5 m. No height changes.
- 1.2748 now appears only in C2's original text and in B3's change note.

---

## 6. What is left (ranked)

| # | Severity | Item | Suggested fix |
|---|---|---|---|
| 1 | low | `verify_research.md` line 259 names a callsign that is in the local observed tables, with a statement about its observed record (§2). | Replace with a placeholder ("the sketch's placeholder callsign, type and time"). |
| 2 | low | `verify_research.md` line 393 names a flight number from the B1 schedule check; with the public schedule and the report's range it bounds that flight's inferred time (§2). | Drop the flight number ("one public schedule page, FlightMapper"). Extend the regex scan to all of `docs/`. |
| 3 | low | M1/M2 cross-check: SHA→Shenzhen departures differ by −9 to −10 min (76 movements, M2 picked, sign agrees with the stated +5 min bin bias); Xi'an arrivals by +18 to +19 min (41, M1 line suspect, not picked) (§1.6). | State the route-level offsets in §4 of the report. Optionally, where both estimates exist, combine them by inverse variance, or add a route-level bias check for the 900–1,300 km departure bin. |
| 4 | low | The owner sample over-represents M1 (35 % against 1.9 %) and foreign carriers (33 % against 4 %), and the README does not say so (§3). | Add one line to `README_sample_for_owner.md`. |
| 5 | cosmetic | "Half the contradictions are at the SHA end": it is 4 of 10. The China M1 σ (19.5–20.7 min) moves by ±4 min with the estimator, because one route holds 74 % of the set (§1.1, §1.4). | Say "4 of 10". Mention the estimator sensitivity next to "small China set". |
| 6 | cosmetic | A stale comment in `observed_elsewhere.py` ("cross-check only (not used for sigma)") above the k-fold that now feeds M1 σ. The "7–19 min" summary omits the unused > 2,500 km band. | Update the comment. |
| 7 | cosmetic | Contact sheet: long Commons titles clip at the tile edge (§5.1). | Truncate with an ellipsis or wrap. The credits file is complete. |
| – | open (unchanged) | Domestic SHA-vs-PVG labels are not officially verified. The AD 2.20 quote set needs the owner's OD3 check. The per-flight tables stay local until the owner reviews the sample. | Owner decisions. |

None of these reverses a fix. All 11 C2 findings and the four added fix-round items (B1 re-run, owner sample, hourly
profile, NOTAM plate) are resolved. Only the per-flight hygiene of `verify_research.md` itself is incomplete.

---

## 7. Files and reproduce

| Path | What | Committable? |
|---|---|---|
| `docs/phase1/reverify_research.md` | this report (aggregates only) | yes |
| `tools/verify/reverify/rv_b1.py` | recount, σ, span, heading and sequence tests, `src` / `evidence` check | yes (no data inside; prints far-end codes and angles to the terminal) |
| `tools/verify/reverify/rv_m1m2.py` | M1 against M2 where both exist | yes |
| `tools/verify/reverify/rv_m1loro.py` | own China leave-one-route-out (Theil–Sen and OLS) from the scan files | yes |
| `tools/verify/reverify/rv_scan.py` | identifier and pattern scan of committable files | yes (prints hits with context to the terminal) |
| `tools/verify/reverify/rv_credits.py` | photo credits against the cached Commons API answer | yes |

From `sha3d/`:
```
python3 -I tools/verify/reverify/rv_b1.py refs/cache/observed_elsewhere refs/cache/ourairports_runways/airports.csv
python3 -I tools/verify/reverify/rv_m1m2.py refs/cache/observed_elsewhere
python3 -I tools/verify/reverify/rv_m1loro.py refs/cache
python3 -I tools/verify/reverify/rv_scan.py . docs data      # also: . tools
python3 -I tools/verify/reverify/rv_credits.py .
python3 -I tools/verify/b1_heading2.py refs/cache && python3 -I tools/verify/b1_sequence.py refs/cache
python3 -I tools/verify/wx_check.py refs/cache/metar/iem_zsss
```

**Attribution for numbers derived here.** ADS-B: contains information from ADSB.lol (https://adsb.lol), ODbL 1.0.
Routes: VRS standing data (CC0). Airports: OurAirports (public domain). Weather: Iowa Environmental Mesonet, Iowa State
University. Photo metadata: Wikimedia Commons API.
