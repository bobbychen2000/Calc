# Hayward Live 3D (KHWD): Phase 0 plan

Status: Phase 0 (research and plan only) written 2026-11-12. No code, models or renders yet. Phase 0 was kept lean
because of the owner's weekly usage limit (resets Fri 13 Nov 2026 11:00Z).

This project is a sibling of `sfo3d/` (SFO Live 3D). It forks from sfo3d at commit **a967f9b**. It does not modify
`sfo3d/` or `pc12/`. Anything that belongs in sfo3d goes to `hwd3d/docs/requests_to_sfo3d.md`.

The owner wrote "hawaard executive airport". The FAA source confirms the reading below (§1, first row), and nothing
contradicts it.

---

## 1. Verified facts

All rows were checked on 2026-11-12. "NASR" means the FAA NASR 28-day subscription CSV, cycle effective 2026-10-29,
downloaded from `https://nfdc.faa.gov/webContent/28DaySub/extra/29_Oct_2026_{APT,ATC,FRQ}_CSV.zip`. The HWD rows are
committed in `refs/cache/faa/nasr_2026-10-29_HWD.json`. "AL-5015" means the FAA airport diagram, cycle 2611
(29 Oct–26 Nov 2026), from `https://aeronav.faa.gov/d-tpp/2611/05015ad.pdf`, committed in
`refs/cache/faa/05015ad_2611.pdf`. Both are U.S. Government works in the public domain.

| Fact | Value | Source |
|---|---|---|
| Identity | FAA LID **HWD**, ICAO **KHWD**, "HAYWARD EXEC", Hayward, Alameda County, CA. Public use, owned by the City of Hayward. Activated 1947/05. | NASR APT_BASE |
| ARP | 37.65893166 N, −122.12173888 E (3rd-party survey 2023-07-05) | NASR APT_BASE |
| Field elevation | 52.1 ft (diagram: 52) | NASR, AL-5015 |
| Magnetic variation | 15° E (epoch 2005); diagram: −0.1°/yr | NASR, AL-5015 |
| Runway 10R/28L | 5,694 × 150 ft, asphalt, grooved, MIRL. S-30 / D-75 (×1000 lb). Marking PIR (precision). True alignment 120° / 300°. | NASR APT_RWY / APT_RWY_END, AL-5015 |
| 10R end | 37.66204722, −122.12979350, elev 27.7 ft. **Displaced threshold 826 ft** at 37.66091861, −122.12731986. VASI V4R, 3.0°, TCH 25 ft. REIL. | NASR APT_RWY_END |
| 28L end | 37.65426300, −122.11273616, elev 52.1 ft. **Displaced threshold 676 ft** at 37.65518672, −122.11475980. VASI V4L, **4.0°**, TCH 35 ft. LOC/DME. REIL. | NASR APT_RWY_END |
| Runway 10L/28R | 3,108 × 75 ft, asphalt, MIRL, S-13. Marking NPI (non-precision). | NASR |
| 10L end | 37.66247844, −122.12726369, elev 28.1 ft. PAPI P4L, 3.0°, TCH 29 ft. Left-hand traffic. | NASR |
| 28R end | 37.65822866, −122.11795213, elev 37.1 ft. PAPI P4L, 3.0°, TCH 44 ft. **Right-hand traffic**. | NASR |
| Traffic pattern | 10R right-hand; 10L and 28L left-hand; 28R right-hand. TPA 600 ft AGL, except 800 ft AGL for 10L/28R. | NASR RIGHT_HAND_TRAFFIC_PAT_FLAG, APT_RMK E147 |
| Tower | FAA-operated ATCT (`TWR_OPERATOR_CODE` F), call "HAYWARD". **Hours 0700–2100 local.** When the tower is closed, 10L/28R is closed, CTAF is 120.2, and MIRL 10R/28L is preset to low (pilot-controlled). | NASR ATC_BASE, FRQ, APT_RMK |
| Frequencies | Tower 120.2 (primary; also CTAF) and 118.9 (secondary; in NASR and in the Chart Supplement, "TOWER 120.2 118.9 (1500–0500Z‡)", but not on the diagram; *corrected 2026-11-12, Phase 1 review*), 257.8 UHF. Ground 121.4. Clearance 128.05. ATIS 126.7 (24 h, phone 510-786-3988). UNICOM 122.95. NorCal Approach/Departure 124.4 (primary), 125.35 and 134.5 (secondary). | NASR FRQ, AL-5015, Chart Supplement SW (29 Oct 2026) |
| Surface ADS-B | "SAID in use. Operate transponders with altitude reporting mode and ADS-B (if equipped) enabled on all airport surfaces." This explains the good ground coverage in §3. | AL-5015, NASR ATC_RMK |
| Taxiways on diagram | A, A1, B, C, D, E, F, Z, Z1. Z1 is closed to wingspans over 94 ft; A1 is closed to wingspans over 100 ft. "TWY A NOT VSB FM ATCT BTN TWY B & C." | AL-5015, NASR APT_RMK |
| Hot spots | HS 1–HS 5 on the diagram | AL-5015 |
| Named areas | West Hangars, East Hangars, FBO ramps (×3: AL-5015 prints "FBO RAMP" three times; *corrected 2026-11-12, Phase 1 review*), GA Transient Ramp, Terminal/Airport Administration, TWR, Fire Station, 28L Run-up | AL-5015 |
| Helicopters | "Transient helicopter TFC use helipads west of Green Ramp lctd at base of ATCT." | NASR APT_RMK |
| Other remarks | Lighted distance-remaining signs: 10R on the north side, 28L on the south side. 155-ft energy-complex stack 1.5 NM SW (do not overfly below 1,000 ft MSL). Noise abatement in effect. Beacon WG (white–green), SS–SR. Segmented circle and lighted windsock. | NASR APT_RMK, APT_BASE |
| Fuel and services | 100LL, Jet A, UL94 (self-serve island). Major airframe and powerplant repair. Charter, instruction, rental. Transient tie-downs available. | NASR APT_BASE / APT_RMK |
| Based aircraft and operations | FY2024 (Oct 2023 – Sep 2024): **446 based aircraft** (325 single-engine, 46 jet, 44 multi-engine, 31 helicopter); **110,158 operations**, of which local GA 68,733 and itinerant GA 39,425, air taxi 1,779, military 193, air carrier 28 (62 % local). Overflights 39,695. Whether the TAF based-aircraft counts equal the Form 5010 entries is not verified. | FAA Terminal Area Forecast 2025, `refs/cache/faa/taf/taf2025_HWD.json` (checked 2026-11-13) |
| ADS-B recordings cover HWD | `sfo3d/refs/cache/rec_pack` is trimmed to **25 nm** (46 km, not 74 km) and 18,000 ft of SFO. HWD's ARP is 22.7 km (12.3 nm) from SFO, so it is inside. | `sfo3d/refs/cache/README.md`; own computation |

Reference only, not verified as an FAA fact and not to be committed: the City of Hayward "Airport Layout Map"
(revised Feb 2020; `https://www.hayward-ca.gov/sites/default/files/documents/Airport-Layout-Map.pdf`, sha256
e030241a…, no open licence). It names hangar rows A–Q, EX1 and EX2; FBOs APP Jet Center and Meridian Hayward; Green Ramp;
Transient Parking; helipads; Hot Spot 3 transient parking; and Self-Serve Fuel. OSM uses the same hangar letters (§2).
A search snippet says the city leases 206 hangars and 116 tie-downs, but the city page it came from now returns 404,
so that figure is **unverified**.

## 2. Data inventory and licences

| Data | Source | Licence | Status / use |
|---|---|---|---|
| Runways, thresholds, lights, frequencies, tower hours | FAA NASR | Public domain | Extracted and committed |
| Taxiway topology, hot spots, named areas | FAA AL-5015 (d-TPP 2611) | Public domain | Committed. **The cycle must be refreshed**: the next cycle starts 26 Nov 2026. |
| Chart Supplement (A/FD) page for HWD | FAA d-CS, SW volume | Public domain | **To fetch** in Phase 1: cross-check tower hours, noise rules and any pattern notes. |
| Airfield geometry: 2 runways, 65 taxiways, 78 taxilanes, 9 aprons, 9 helipads, 18 holding positions, 34 hangars (named A–Q, EX1, EX2, Savage Aviation, Absolute Aero, Bud Field Aviation), windsock | OpenStreetMap (Overpass mirror overpass.private.coffee; overpass-api.de reset the connection) | ODbL 1.0 | Counted only. Phase 1 will pin a dated extract and commit it, as in sfo3d. **No `aeroway=parking_position` (tie-down) nodes exist.** |
| Imagery for measurement (paint, tie-down rows, hangar doors) | USDA NAIP 2024 CA, 0.6 m | Public domain | The sfo3d cache holds only the SFO quads (m_3712221/22/29/30), so the HWD quads **must be fetched**. sfo3d's `tools/imagery` pipeline can be reused. |
| Elevation (runway slope 0.3–0.4 % up to the east; field elevation 28–52 ft) | USGS 3DEP 1 m lidar | Public domain | Optional, Phase 2 |
| ADS-B history | sfo3d `rec_pack` (adsb.lol) | ODbL 1.0 | Analysed (§3). Only aggregate outputs are committed. |
| ADS-B live feed | adsb.lol (ODbL); adsb.fi (personal, non-commercial; may not be relicensed) | as stated | Same relay design as sfo3d. Do not publish adsb.fi-derived records (sfo3d OD-11 precedent). |
| Registration, owner and type | FAA Releasable Aircraft Database (`ReleasableAircraft.zip`) | Public domain | **Not obtainable here** (2026-11-12/13): registry.faa.gov answers automated downloads with an Akamai "Access Denied" page, and the Internet Archive copy (snapshot 2026-11-11) is unreachable through this session's egress proxy. Neither block is worked around. A browser download by a person into `refs/cache/local/registry/` still works with `tools/registry/`. |
| Registration, type, model, operator (used instead) | Mictronics aircraft database, GitHub export, commit 479e4d0 (2026-11-08) | ODC-By 1.0 (attribution) | **Done.** `tools/registry/mictronics_db.py`; lookup local only (D1). At HWD: 191 of 216 ICAO-addressed on-field aircraft found; registration 190/190 and type 189/190 agree with their own broadcasts; all 26 ICAO-style callsigns resolve to a named operator. No year, engine or registrant fields. |
| Based aircraft, annual operations | FAA Terminal Area Forecast 2025 (used instead of the Form 5010 PDF, which ADIP serves only behind a page token and reCAPTCHA) | Public domain | **Done.** `refs/cache/faa/taf/taf2025_HWD.json` (§1). |
| Aircraft models | FlightGear aircraft (c172p, PA-28, SR22, Bonanza, helicopters, bizjets …) | Mostly GPL-2.0+, **per-aircraft licence to verify** | Phase 3. sfo3d holds no GA models. Our own **PC-12** (`pc12/out/pc12.glb`, own work) can be reused. |
| Tower, hangar and FBO building appearance | Wikimedia Commons photos (only those with an open licence) and NAIP | CC / public domain | Reference only unless openly licensed |
| ATC audio | LiveATC.net | **Terms unread**: liveatc.net returns HTTP 403 to automated fetches | A search snippet lists three KHWD feeds (Ground 121.4; Tower 118.9; Tower 120.2). Mounts and terms are **unverified**. See Question Q2. |
| Weather | aviationweather.gov METAR KHWD (NOAA, public domain) | Public domain | Phase 2 |
| Google imagery | — | Licensed | Reference only, never a texture |

## 3. Type mix and coverage, measured from the existing recordings

Method: `tools/phase0/hwd_mix.py` and `hwd_cov.py`, run over all 111 adsb.lol hours in
`sfo3d/refs/cache/rec_pack` (4 Nov 17Z – 11 Nov 13Z 2026; 101 hours had successful polls; median about 590 polls per
hour). Raw output is in `refs/cache/adsb/*_summary.txt`. "On field" means within 1.5 km of the ARP and below 150 ft
AGL, which includes `alt_baro: "ground"`. All local times are PST (UTC−8).

- **243 distinct aircraft on the field** during the week; 196 of them reported `ground`. Per local day: 72, 83, 23*, 81,
  73, 43*, 7* (*partial recording days).
- **Type mix on the field** (approximate, by ICAO type designator):

  | Class | Share | Main types |
  |---|---|---|
  | Piston singles | ~51 % (≈125) | C172 42, C152 7, C182 7, P28A 5, C72R 4, S22T 4, C150 4, M20P 4, DA40 3, SR22 3, C210 3, plus RV, Citabria, Bonanza, Pitts, Long-EZ … |
  | Unknown type | ~16 % (38) | mostly TIS-B or anonymous targets |
  | Business jets | ~16 % (≈40) | E55P 5, GLF4 4, C510 3, G280, C56X, GLEX, CL60, E50P, GLF5, C25M, HDJT, SF50, F2TH, FA50, F900, C680 … |
  | Twins and turboprops | ~11 % (≈27) | **PC12 6**, DA62, P180, BE50, P46T, C425, BE20, TBM7/9, MU2 … |
  | Helicopters | ~7 % (16) | B06 4, EC45 3, R44 3, A109 2, EC30, B407, R22, H60 |

  The PC-12 is the most common turbine type, so the `pc12/` model is worth reusing.
- **Sources of on-field fixes:** 1090 ADS-B 89.5 %, UAT re-broadcast (`adsr_*`) 9.8 %, TIS-B 0.6 %, `adsb_other` 0.1 %,
  MLAT ≈0. The dominant source per aircraft: 184 aircraft 1090 ADS-B, 32 UAT, 23 TIS-B, 4 anonymous.
- **Identity:** 27 aircraft (11 %) have non-ICAO or anonymous addresses (`~` prefix). 34 have no registration, 38 no
  type, 27 no callsign. In 186 of 243 the callsign *is* the registration; ICAO-style callsigns are rare (CXK, BYF,
  TWY, GDG, CTP, PXT, EJA, EJM, NJZ, JTL, FFL, XSN …). Flags: **LADD on 33 aircraft (14 %)**, PIA on 1, military on 1.
- **Position quality on the ground:** NACp is 10–11 for 74 % of fixes and 8–9 for 18 %. NACp 0 or absent (TIS-B or
  degraded) for 8 %.
- **Track continuity while taxiing** (ground fixes moving faster than 3 kt): median gap between fixes 1.3 s, p90 11.5 s,
  p99 52 s. 10 % of gaps exceed 10 s, so dead reckoning has to bridge these gaps along the taxi graph.
  *Correction (Phase 1, G4):* these figures describe the **recorder**, not the airborne coverage. The sfo3d recorder
  polls adsb.lol about every 1.3 s until it is rate-limited (HTTP 429), which happens after 10 polls in 4,782 of
  5,541 one-minute bursts. It then waits for the next minute, so only about 14 s of every 60 s is observed and each
  minute has a hole of about 46 s. In addition, 17 outages exceed 600 s and 9 of the 111 hour files are empty. The
  true ADS-B update rate at HWD is therefore not measured. The live relay must poll within adsb.lol's rate limit, and
  the replay must interpolate across 46 s holes. Details: `docs/phase1_data_report.md`, `refs/cache/adsb/hwd_events.json`.
- **Parked aircraft keep transmitting:** 143 aircraft logged 20 or more stationary ground fixes over more than 10 min.
  Parking positions can therefore be learned from the data, as sfo3d did with `adsb_parked.py`.
- **Pattern work:** 18 aircraft made 6 or more ground-to-air transitions in the week (touch-and-goes or closed
  traffic); 25 more made 2–5.
- **Runway use:** low airborne fixes (below 400 ft AGL, faster than 40 kt) were 92 % westbound (runways 28), 0.5 %
  eastbound. This was one west-wind week; the east flow also needs a test.
- **Hours:** on-field activity starts at 07 PST, peaks 11–15, continues after the tower closes at 21, and is near zero
  from 01–06.
- **Altitude reporting:** low fixes within 1 nm include both `ground` and airborne; no ground fixes beyond 1 nm. Note
  that OAK arrivals (B38M/B737/B763/E75L …) pass within 3 nm below 3,000 ft. They must not be classified as HWD
  traffic.

Conclusion: coverage is far better than the brief feared, largely because SAID requires surface ADS-B. The real gaps
are TIS-B and anonymous targets (about 10 % of aircraft, with no type or registration), 10–50 s holes while taxiing,
and the LADD question.

## 4. Architecture

Same stack as sfo3d: plain ES modules, a custom WebGL2 renderer, offline Python data tools, a stdlib Python relay and
a snapshot/replay artifact. Copy modules from sfo3d@a967f9b into `hwd3d/` and record the origin in each file header.

| Area | Reuse from sfo3d (copy and adapt) | New for HWD |
|---|---|---|
| Renderer and shaders | `js/gl.js`, `renderer.js`, `math.js`, `geom.js`, `js/shaders/*` (ground, objects, aircraft_real, post, env), `js/env/*` sun/METAR/night | Smaller scene; tune the shadow cascades for small aircraft |
| Geo frame | `js/geo.js` pattern | A new frame centred on the HWD ARP, with the runway grid at 120°/300° true and NASR ends and displaced thresholds |
| Airfield | `markings.js`, `signs.js`, `world.js`, ground-bake pipeline, `tools/imagery` (NAIP paint and pavement) | GA marking set (PIR on 10R/28L, NPI on 10L/28R, displaced-threshold arrows, run-up area, tie-down rows and chains, hangar taxilanes), distance-remaining signs, VASI/PAPI/REIL/MIRL, beacon, segmented circle, windsock, helipads |
| Buildings | `terminals.js` parametric pattern | Tower, T-hangar and box-hangar rows from OSM footprints plus NAIP (door rhythm), FBO buildings, fire station, fuel island |
| Traffic | `traffic.js` (Hermite interpolation, dead reckoning, heading inference, parked persistence), `ground.js` (solid-planform physics), `feed.js`, `lookup.js` | **Phase classifier for GA**: closed traffic, touch-and-go, stop-and-go, low approach, go-around, run-up (stationary at the 28L run-up pad), helicopter hover-taxi and helipad ops, after-hours CTAF ops. OAK-traffic exclusion. Taxi graph from OSM taxiways and taxilanes. |
| Parking | the stand-matching idea in `traffic.js` and the `adsb_parked.py` method | **New parking model** with no jet bridges or gates: tie-down spots (inferred from NAIP and ADS-B stays, `src: obs|inf`), T-hangar and box-hangar bays (aircraft can go *inside*: hide or door-open state), FBO ramp spots, helipads. Designation by row letter where it exists. |
| GSE | `gates.js` GSE collision checks | Fuel trucks (Jet A and 100LL), tugs, golf carts; no bridges |
| Models | `models.js` loader, `.sfom` converter, `js/aircraft/fit.js` BIZ sizing | GA models: C172 first (it is about 17 % of all aircraft), PA-28, SR22, C182, Bonanza, DA40/62, PC-12 (ours), bizjet set, helicopters (B06, EC135, R44). N-number registrations drawn on the fuselage. |
| ATC | `atc.js` link-out design | KHWD feeds after the owner's answer on LiveATC (Q2) |
| Relay and artifact | `sfo_live_server.py` design, snapshot mode, `livetest.mjs` harness | `hwd_live_server.py`; replay pack built from adsb.lol only |

## 5. Risks

1. **LADD privacy.** 14 % of the aircraft on the field ask the FAA to limit the display of their data. Showing their
   registration in a public app and a public repo is a policy question for the owner (Q1). Until then, aggregate data
   only; nothing per aircraft is committed.
2. **LiveATC terms** cannot be read automatically (HTTP 403). The owner rejects synthetic voice, so the ATC toggle
   depends on Q2.
3. **No official tie-down designations.** OSM has no parking positions, and the city's layout map shows only hangar
   letters. Tie-down numbering may need a source from the owner or the airport office (Q3).
4. **GA model licences.** FlightGear GA aircraft have mixed licences (most are GPL; some are CC-BY-NC or unclear).
   Each one must be verified before use (the A220 precedent in sfo3d).
5. **Small aircraft at 1–1.5 m position error** relative to a 9 m wingspan: parking snap and solid-body separation
   need tighter tolerances than for airliners.
6. **Unknown types** (16 %) need a neutral but plausible fallback model chosen from the ADS-B emitter category (A1, A7 …),
   with the guess marked as inferred.
7. **Chart cycle drift.** AL-5015 2611 expires 26 Nov 2026. The ALP update that began in 2022 may change layout.
8. **Usage budget.** Fidelity at sfo3d level is expensive. The phases below are ordered so that each one delivers
   something usable.
9. **The sample week is not representative**: it was one west-flow week in November. East flow and summer peaks still
   need recording.

## 6. Questions for the owner

- **Q1 (LADD):** For aircraft flagged LADD, should the app hide the registration (show only the type), or show
  everything as public ADS-B sites like adsb.lol do? And should the repo commit any per-aircraft data?
- **Q2 (ATC audio):** LiveATC blocks automated reads of its feed list and terms. Could you open
  https://www.liveatc.net/search/?icao=KHWD and LiveATC's terms page and paste the KHWD mounts and the
  embedding/linking terms? Is a link-out to LiveATC's own player (the sfo3d plan) acceptable?
- **Q3 (tie-downs):** Do you have, or may we ask the airport office (510-293-8669) for, the tie-down row and spot
  numbering? Otherwise tie-downs will be labelled by hangar row letter or zone and marked inferred.
- **Q4 (reference imagery):** As at SFO, could you send Google Maps screenshots of the West Hangars, East Hangars,
  both FBO ramps and the transient/Green Ramp (reference only)? NAIP at 0.6 m may not resolve tie-down chains.
- **Q5 (models):** Is a FlightGear GPL C172 or PA-28 acceptable as the base for the most common types, as with the
  airliners?
- **Q6 (scope):** Should the camera and traffic scope include OAK arrivals overhead and nearby fields, or only HWD
  traffic?

### 6a. Working defaults (2026-11-12)

The owner asked me to "use your best judgement to proceed". Until the owner answers otherwise, these defaults apply.
Each can be reversed.

- **D1 (LADD/PIA):** the app shows the type only, with no registration, callsign or operator, for aircraft that carry
  the LADD or PIA flag. **No committed file holds a per-aircraft identity** (hex, registration or callsign) derived
  from ADS-B. Parked-stay and coverage outputs are aggregated into positions, type classes and counts. FAA registry
  look-ups run locally or in the relay from a fetched copy that is not committed.
- **D2 (ATC):** a link-out only, to LiveATC's KHWD search page `https://www.liveatc.net/search/?icao=KHWD`. No
  embedded stream, and no mount names until they are verified. No synthetic audio.
- **D3 (tie-downs):** tie-down and ramp spots are inferred from NAIP 2024 (painted rows and tie-down marks) and from
  ADS-B parked stays, marked `src: 'inf'` or `'obs'` with the evidence. Labels use the hangar row letter or zone
  ("West tie-downs row 3") and are never presented as official numbers.
- **D4 (imagery):** NAIP only for now. Screenshots will be used as reference if the owner sends them.
- **D5 (models):** FlightGear GPL-2.0+ models are acceptable, following the sfo3d airliner precedent. Each model's
  licence file is checked; anything without a clear open licence is replaced by a procedural or own model.
- **D6 (scope):** the app shows all traffic within about 5 nm and below 3,000 ft AGL. Only aircraft whose track
  touches the HWD runways, taxiways or ramps, or flies the HWD pattern, are classified as HWD traffic. Other traffic
  (OAK and SFO arrivals) is drawn as overflights.

### 6b. Owner decisions (2026-11-13), binding

These came from the owner directly. They **supersede** anything earlier in this plan, in `CLAUDE.md` or in any agent
prompt that says "everything must work on a phone" or asks for phone performance.

- **OD1 (one quality level only):** build **only the full-feature version**, at the highest resolution and with the
  most complex shading. There is **no phone-friendly "lite" version**: no `quality=low` path, no reduced shading,
  geometry, texture size or render scale for phones. Performance is judged by the owner **on a laptop**. Do not spend
  effort on phone GPU frame time, memory or battery.
- **OD2 (artifact on an iPhone):** the published artifact link must still **open and be usable on an iPhone**. The
  layout must fit the screen and touch must work, but the rendering is not reduced or tuned for the phone ("no need to
  optimize it"). The existing phone layout (bottom sheet, touch targets) stays as the layout; only performance work for
  phones is dropped.
- **OD3 (videos):** make **two videos**, each with a camera **following one aircraft through a landing and/or a
  take-off at HWD**: one **Cirrus SF50 Vision Jet** and one **Pilatus PC-12**. They use real recorded tracks and the
  full-quality renderer, and they need detailed SF50 and PC-12 models. This moves those two types to the front of
  Phase 3. D1 still applies to anything shown in the videos.

**Orchestrator decisions under the owner's delegation (2026-11-13).** The owner delegated these judgements; they are
recorded here next to OD1–OD3 but did not come from the owner directly, and **the owner may overrule them**.

- **(a) FAA DRS.** The FAA DRS public web viewer (no login, no key, no bot check) is the FAA's intended public interface
  for type certificate data sheets. Values read there from TCDS A00018CH (SF50) and E3GL (FJ33-5A) are **obs** with the
  TCDS citation, not "inf (DRS)" (`tools/models/sf50/SF50_FACTS.md`, `docs/phase3_sf50.md` §9).
- **(b) Digitised manufacturer-drawing measurements stay local.** Readings digitised from the Pilatus drawing
  190.10.40.432 / Model Building Plan sheets and from the Cirrus AFM figures (outline tables, per-butt-line water lines,
  window centres, raster registrations and scales) are never committed. They live in the gitignored
  `refs/cache/local/models/{pilatus_pc12_meas,afm_sf50_meas}.json` (each with a `src` note). Committed files keep only
  the fitted model parameters with a one-line basis, as `pc12/` does, and published dimensions (type certificates, FAA
  ACD, manufacturer spec pages). `tools/models/test_models.mjs` reports the checks that need the local files as SKIP in a
  clean clone (`docs/phase3_models.md` §12–14). **Scope in time:** (b) applies to the tree from Phase 3a fix round 3
  (commit b0d55c1) on. The earlier pushed checkpoint bd22c60 still holds a few such readings (raster scales and
  registration numbers, a handful of per-butt-line water lines) in its history; history is not rewritten without the
  owner's explicit permission (no force-push), so that is left to the owner.

## 7. Phased task list

Each phase ends with commits, a push, and renders shown to the owner. No scored QA loop starts without the owner's
approval.

- **Phase 1 – data foundation.**
  - Pin and commit the OSM extract.
  - Fetch the NAIP 2024 HWD quads, the Chart Supplement page and the FAA aircraft registry.
  - Build `data/hwd_airport.*`: runways from NASR, taxiways and taxilanes from OSM snapped to NAIP paint, hangars,
    helipads, holds.
  - Write the ADS-B parked-stay analysis to propose tie-down spots and FBO spots (`src` obs/inf).
  - Write the cross-check script against AL-5015.
- **Phase 2 – app skeleton.**
  - Fork the renderer, geo frame, world and markings into `hwd3d/js/`.
  - Write `hwd_live_server.py` with adsb.lol first and adsb.fi live-only.
  - Build the snapshot and replay pack from the adsb.lol hours.
  - Write the GA phase classifier and taxi graph, and exclude OAK traffic.
  - Show the first renders.
- **Phase 3 – aircraft.**
  - First (OD3): detailed **SF50** (procedural, from published dimensions) and **PC-12** (from our `pc12/` model),
    then the two follow-cam videos of a real recorded landing / take-off for each.
  - Verify licences and convert C172, PA-28, SR22, C182, a bizjet set and three helicopters.
  - Add N-number decals, lights, gear and shadows, and a category fallback for unknown types.
- **Phase 4 – airport fidelity.**
  - Tower, hangar rows (T and box) with doors, FBOs, fuel island, fire station.
  - FAA markings and signs including distance-remaining signs, VASI/PAPI/REIL/MIRL, beacon, segmented circle,
    windsock.
  - Tie-downs with ropes and chains; GSE (fuel trucks, tugs).
- **Phase 5 – physics and behaviour.**
  - Solid-body separation, pavement-only placement, hangar entry/exit.
  - Pattern work, run-ups, hover-taxi; test against the replay.
- **Phase 6 – QA and delivery.**
  - Adversarial visual QA passes, after the owner approves.
  - ATC link-out (after Q2), About/credits panel with ODbL, NAIP and FAA notices.
  - Standalone app plus relay, full quality only (OD1); artifact in snapshot/replay mode whose layout works on an
    iPhone (OD2, no phone performance tuning).
