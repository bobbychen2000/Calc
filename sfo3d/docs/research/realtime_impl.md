# Real-time implementation: relay, recorder, replay (step 1)

Status 24 Sep 2026 ~15:40 UTC. Scope: `sfo_live_server.py` (the local relay), `tools/live/record.py` / `recio.py`
(the recorder and its reader), `tools/live/test_relay.py` (offline unit tests), `tools/live/relay_smoke.py`
(end-to-end test of a running relay). The design follows `realtime_feeds.md` (§5), `traffic_audit.md` (§4.3, §6.2)
and `gate_truth.md` (§7, §8). "Observed" = measured here, with the file or time; "inferred" = reasoning.

## 1. Endpoints (all JSON unless noted; `/api/*` never cached, gzip when the client accepts it)

| Endpoint | Content |
|---|---|
| `/api/ping` | `{sfolive: 1, v, mode: live\|replay, stream, delta, features: {gates, routes, metar, replay}, providers, attribution}` |
| `/api/adsb` | Latest merged list, readsb `jv2` shape: `{ac: [...], now (ms), seq, total, _source}` |
| `/api/stream` | Server-Sent Events. `event: adsb` = the full list (same JSON as `/api/adsb`) per merged update. `?delta=1`: a full list first, then `event: delta` `{now, seq, ac: [changed records], gone: [keys]}`; a full list is re-sent when a client missed a seq and every 30 s. A snapshot that changes nothing (duplicate) is not pushed. `retry: 2000`; `: keepalive` every 15 s. |
| `/api/gates[?cs=A,B]` | flysfo flight-status plan, parsed (§4). |
| `POST /api/routeset` | adsb.lol routeset request/response format; 503 (never an empty 200) when no source works, so clients do not cache "no route". |
| `/api/metar?ids=KSFO[&format=json]` | aviationweather.gov, cached 60 s. In replay: the cached METAR observed ≤ 90 min before the replay time, else an error (never today's weather). |
| `/api/status` | Per provider: requests, ok, 429, errors, duplicates, latency p50/p90, request−`now` lag, adsb.fi phase, adaptive floor, `last_10min` {requests, ok, http429, ok_per_min}; merge counters; gates and routes state. |

Per aircraft the relay adds: `_src` (provider of the position: `lol`/`fi`), `_prov` (providers listing it, e.g.
`fi+lol`), `_pt` (absolute position time, epoch s), `_veh: 1` (sticky ground-vehicle flag), `_drop` (surface fields
removed). Non-ICAO `~` ids are kept (`~abc123`); two providers' `~` ids more than 2 km apart become `~id` and
`~id@fi`/`@lol`.

## 2. Polling (shared by the relay and the recorder: `Poller`)

- **adsb.lol** `GET https://api.adsb.lol/v2/point/37.6188/-122.3754/40`: every 1.0–1.5 s (random), one request in
  flight, keep-alive, identifying User-Agent `sfo-live-3d-relay/0.3 (+https://github.com/bobbychen2000/Calc; personal
  non-commercial visualisation)`. HTTP 429: wait 2 s, then 4, 8, 16, 30 s (feeds §5.1), or Retry-After if longer.
- **Adaptive floor (new).** Observed 24 Sep 15:13–15:21Z with the plain back-off: 79 requests, **61 × 429** (77 %),
  18 OK. After every back-off the first request at the normal cadence was refused again
  (`refs/cache/rec/adsblol_20260924_15`). adsb.lol's README says limits are "dynamic based on the environment load"
  (feeds §3.1), so each 429 now raises a minimum interval ×1.5 (≥ 2 s, ≤ 30 s) and each success lowers it ×0.9 until
  it is below the normal period again. Observed 15:25–15:37Z with the floor: 39 requests, **13 × 429** (33 %), 26 OK
  — the same ~2.2 OK/min as before with half the requests and a fifth of the refusals. adsb.lol grants this egress IP
  only ~2 snapshots/min today (it was ~80 % OK at 1 Hz during 07:28–09:15Z, feeds §4), so **adsb.fi is the position
  source for most aircraft now** (live test: 106 of 114 positions from adsb.fi). The merge makes this automatic.
- **adsb.fi** `GET https://opendata.adsb.fi/api/v3/lat/37.6188/lon/-122.3754/dist/40`: every 2.0 s at an even second
  + 0.3 s (its snapshot changes on even seconds, feeds §4.2); the phase moves 0.1 s later if > 30 % of 30 responses
  are the previous snapshot. Errors: 4, 8, 16, 32, 60 s. Observed 15:25–15:37Z: 356 requests, 356 OK, 0 × 429,
  0 duplicates, request start − `now` p50 0.30 s, latency p50 176 ms.
- The relay polls only while a client asked for data in the last 60 s (`--record` polls always). The recorder and the
  relay use the same IP: stop the recorder while testing the relay live.

## 3. Merge and hygiene (`Hub._merge_one`)

1. Position candidates per key: `pt = now − seen_pos` of each provider's latest snapshot (snapshots older than 45 s
   are ignored). MLAT/TIS-B/other positions are skipped while an ADS-B/ADS-R position < 10 s old exists, and rejected
   if they imply > 1.5 × gs × dt + 50 m of motion from the last accepted position (traffic_audit §6.2.2).
2. The freshest position wins; within 0.05 s the better source type, then adsb.lol. Fields of the *same* report
   (|Δt| ≤ 0.2 s) missing from the winner are filled from the other provider (e.g. `true_heading`, `nav_qnh`).
3. Identity fields (`flight squawk emergency category r t desc ownOp year dbFlags …`) from the freshest record that has
   them; database fields prefer the position winner; `desc/ownOp/year` prefer adsb.fi (adsb.lol omits them).
4. On the ground: `track`, `track_rate` and every field listed in `mlat[]` (except lat/lon) are dropped
   (traffic_audit §4.3: surface `track` is unreliable). Positions older than 60 s move to `lastPosition`.
5. Vehicles: emitter category C1–C7 or type SERV/GRND → `_veh` stays set for that key (traffic_audit F8).

## 4. SFO gates (`/api/gates`, flysfo.com)

- Fetched only when a client asks, at most every 10 min (shared with `tools/live/gatecheck.py` through the newest
  cached file), gzip, identifying UA, raw JSON cached locally in `refs/cache/gate_truth/` (gitignored);
  `--no-sfo-gates` disables it. Attribution text in `/api/ping`. No terms are published (gate_truth §7); ask SFO before
  depending on it publicly.
- **Conditional GET: not possible.** Observed 15:24:24Z: HTTP 200, 790,568 B gzip on the wire, 17,159,930 B JSON,
  3.05 s, **no `ETag` or `Last-Modified`** offered. The relay sends validators only if a response offers them.
- The first request waits up to 20 s for the first fetch instead of answering with an empty plan.
- Payload: `flights` (compact records: kind A/D, callsign, flight number, airline, type, gate, terminal,
  `stands [[name, from, to]]`, scheduled/estimated/actual block, runway and AOD times, route, linked turn, code-shares),
  `byCallsign` (normalised callsign → `{flights, arr, dep, stand: {name, base, from, to}}`), `aliases`, `byStand`
  (SFO stand name → `{base, now: [turn windows covering now], next: [≤ 2 upcoming]}`), `verify` (deep-link templates for
  flysfo and FlightAware, for the owner's manual check).
- Callsign normalisation: ICAO code + number without leading zeros + suffix (`CAL003` → `CAL3`, gate_truth §8).
- **Regional callsigns → marketing flights** (`aliases`), decided from data, not from an assumed partner table:
  candidates are non-regional flysfo callsigns with the same number; score +2 if the ADS-B type agrees (−1 if not),
  +2 if the VRS route shares an airport with the flysfo flight and includes KSFO (−2 if not); mapped only when the top
  score is unique and ≥ 0; the checks are in the payload. `E175` (flysfo) = `E75L/E75S` (ICAO Doc 8643).
  **Observed 15:24Z (first real test; the overnight recording had no regional callsigns, gate_truth verification
  #12):** 8 of 8 regional callsigns on the feed resolved to a single candidate — SKW5394/5471/5562/6014 → UAL,
  SKW3463 → ASA, SKW6274 → AAL6274 (type E175/E75L), QXE2418 → ASA2418 (over UAL2418 by type + route), with type and
  route agreeing for 6; SKW5790 and SKW5777 → UAL with type agreeing but the VRS route differing (score 0).
- Replay: the union of the cached snapshots fetched ≤ 30 min after the replay time; times re-mapped to the replay clock.

## 5. Routes (`POST /api/routeset`)

- adsb.lol routeset API first. **Re-probed 24 Sep 15:17Z: still HTTP 201 with a 0-byte body** (traffic_audit F5).
  After 3 failures it is skipped for 30 min.
- Fallback: adsb.lol's static mirror of the VRS standing data, `https://vrs-standing-data.adsb.lol/routes.csv.gz` +
  `airports.csv.gz` (4.5 MB, `Last-Modified` 20 Sep 2026, ETag offered), downloaded once, re-validated daily,
  cached in `refs/cache/routes/`. **Terms verified 15:17Z:** the mirror's `LICENSE` is CC0 1.0 Universal; its README
  says "All data from https://github.com/vradarserver/standing-data/"; the upstream `LICENSE` is also CC0 1.0.
- Only definite answers are cached (per callsign per UTC day). `plausible` is recomputed with a proper cross-track test
  (max(50 NM, 20 % of the leg)); `_sfo` = origin/destination/stop.
- Observed in the live test: 100 callsigns answered in 2.9 s, 54 known, 33 via SFO, all from the mirror.

## 6. Recorder

- `tools/live/record.py [hours]` uses the relay's `Poller` and `RecordWriter`: one gzip JSON-lines file per provider per
  UTC hour, each line `{t: request start, tr: response received, p, code, d | err, ra}` (so receive time and HTTP status
  are logged; adsb.fi v3 at 0.5 Hz). A summary per provider every 10 min in `recorder.log`.
- Running: PID in `refs/cache/rec/recorder.pid`, restarted 24 Sep 15:25:02Z for 14 h with
  `setsid nohup python3 tools/live/record.py 14 >> refs/cache/rec/recorder.log 2>&1 < /dev/null &`. Stop only that PID
  (`kill $(cat refs/cache/rec/recorder.pid)`; SIGTERM closes the gzip member). Gap: 15:21:32–15:25:02Z (relay live test).
- **Reader bug fixed** (`recio.py`): when a file held a cleanly closed member followed by another (a recorder restart
  within the hour), the end of the first member was computed from the end of the *file* instead of the end of the read
  chunk, so every later member was silently dropped (the 15h files read 236 of 302 adsb.fi records). Covered by
  `test_relay.py RecIO`.

## 7. Tests

- `python3 tools/live/test_relay.py` — 16 offline tests (merge, freshest wins, same-report fill, MLAT hold/jump, surface
  hygiene, sticky vehicles, `~` ids, lastPosition, deltas, gates parsing, normalisation, E175, routes mirror,
  plausibility, adsb.fi slots, back-off, adaptive floor, multi-member recordings). All pass.
- `python3 tools/live/relay_smoke.py http://127.0.0.1:PORT 60 --delta` — against a running relay: SSE events and
  spacing, provenance, delta stream rebuilt and compared with a parallel full stream at every seq, status, METAR,
  routes, gates and aliases.
- Results (24 Sep):
  - Live, 15:21–15:24Z, 150 s: 79 events (one per adsb.fi snapshot, spacing p50 2.0 s), 114 aircraft, 53 within 3 NM
    (50 on the ground, 12 vehicles), position age p50 2.2 s; delta rebuild = full stream at 79/79 seqs; METAR, routes,
    gates OK.
  - Replay 07:30Z (night) and 15:14Z (day, 2×): 38–45 events/40 s, delta rebuild identical at every seq; gates in replay
    show the plan of the time (e.g. AAL2506 B24, AAL2856 B23, ACA738 C10, DAL2635 C11 at 07:30Z — the stands SFO
    published, gate_truth §5); replay METAR 0656Z for 07:30Z and 1456Z for 15:14Z.
  - App on the relay (livetest `RELAY=` proxy, `jobs/relaytest.mjs`, replay 15:14Z): 95–98 tracks, 13 stand matches,
    routes from the mirror. Against SFO's plan at that time the app agrees for AAL2799 B26, ASA1329 B9, DAL1421 C7,
    FFT3308 B17 and disagrees for ACA738 (app C10, SFO window D11: the C10 → D11 tow of gate_truth §3). With
    `SOFTGL=1` each frame takes 4–7 s, the first feed response is handled ~50 s after load and tracks go stale in the
    gaps, so use `WAIT` ≥ 150000 and judge staleness only with a GPU.

## 8. Open points

- adsb.lol's grant to this IP is ~2 snapshots/min today; if it stays so, the effective update rate is adsb.fi's 0.5 Hz
  (positions ≤ 2.3 s old at the relay). A feeder account or own receiver (feeds §3) would lift it.
- The app (`js/live/app.js`, `feed.js`) still polls `/api/adsb` every 5 s with a 7.5 s display delay (traffic_audit F9);
  switching it to `/api/stream?delta=1` is the next step.
- flysfo: permission from SFO not obtained (gate_truth §7).

---------------------------------------------------------------------------------------------------------------------

# Step 2 — the traffic engine (24 Sep 2026, ~17:50 UTC)

Scope: `js/live/traffic.js` (rewritten), `ground.js`, `feed.js`, `app.js`, `ui.js`, `entry.js`, `about.js`, new
`stats.js`, `live.css`; tools `tools/live/build_stream.py`, `build_taxigraph.py`, `replay_engine.mjs`, `replay_score.py`,
`replay_engine_all.sh`; generated `data/sfo_taxigraph.js` (see `docs/requests/traffic_engine_data.md` §1).
Design sources: `traffic_audit.md` §6, `realtime_feeds.md`, `gate_truth.md` §6. "Observed" = measured on the replay.
Relay change in this step: aircraft-database fields (`r t desc ownOp year dbFlags`) now come from adsb.fi when it has
them — the two providers' databases disagreed for C-FDUW (BCS3 vs BCS1) and the position winner alternates, which made
the type flicker; the engine additionally accepts a type change only after 5 consistent reports. `test_relay.py`: 16/16.

## 1. What the engine does

- **Feed.** `StreamFeed` (feed.js) reads the relay's `/api/stream?delta=1` (SSE), keeps the full list across `adsb`/`delta`
  events and hands it to the engine after every event; it falls back to polling `/api/adsb` every second when there is
  no stream. The direct-provider `Feed` stays for the no-relay case (CORS usually blocks it). Position time = the
  relay's `_pt` (else `now − seen_pos`). ADS-B lat/lon → world with `geo.wgs84ToWorld` (guarded fallback to `llToWorld`).
- **Display delay.** Starts at 1.5 s and adapts in 1–3 s to the median age the newest report reaches before the next one
  arrives (+0.3 s), changing ≤ 0.1 s per s. Observed today: **3.0 s**, because adsb.lol grants this IP ~2 snapshots/min
  and adsb.fi's snapshot steps every 2 s (step 1 §2). A fixed 1.5 s was also measured (§3): positions 1.5 s fresher
  but p99 errors 2–3× larger and 8× more jerk exceedances, so the adaptive rule stays.
- **Target.** Hermite interpolation between reports (tangents = reported gs × direction, rejected when inconsistent with
  the chord; velocities are the reports' own, not the noisy Hermite derivative); dead reckoning ≤ 5 s (constant turn
  rate), then on the ground a smooth stop, in the air straight flight until the track goes stale.
- **Kinematic body (no teleports, no morphing).** The drawn aircraft follows the target:
  - ground: a bicycle model — the **main-gear centre** cannot slip sideways and the nose swings around it (push-back
    turns pivot about the main gear); turning radius of the main-gear centre ≥ 0.27 × wheelbase (≈ 75° nose-wheel
    steering, design value), lateral acceleration ≤ 2.5 m/s², yaw rate ≤ 20°/s, longitudinal −3.5…+3 m/s², jerk
    ≤ 2 m/s³, critically damped along-track loop (ω 0.45 rad/s, catch-up ≤ 3 m/s), pure-pursuit steering; reverses only
    in push-back / tow; U-turn instead of reversing when the target is behind; a stopped aircraft moved to a refined
    parked pose is towed (≤ 0.5 m/s, ≤ 2°/s, ramped) or, in its first 30 s on screen, simply placed;
  - air: bank ≤ 30° (45° light aircraft), turn ≤ 6°/s (12°/s light), along-track ≤ 0.2 g (0.35 g within 1.5 m of the
    runway), vertical ≤ 0.2 g; rotorcraft (category A7) follow as a point; crab from true heading vs track;
  - touchdown: the wheels descend to the runway (no vertical jump); frames are sub-stepped at ≤ 0.1 s from the real
    elapsed time, so slow frames / software rendering do not change the physics.
- **Flight-phase state machine (data time, kinematic, not the transponder flag).** approach → final (Bayesian runway
  posterior, σ = 25 m + 0.012|a|, prior from this page's own touchdowns of the last 30 min) → flare → touchdown
  (deceleration ≥ 1.6 kt/s on two intervals past 100 m; the day recording showed flare deceleration up to 1.39 kt/s,
  SKW5562 CRJ2) → rollout → exit (|c| > 45 m) → taxi-in → docking along the stand lead-in → parked; push-back →
  taxi-out → line-up → take-off roll (≥ 50 kt, or ≥ 1.2 kt/s from ≥ 12 kt; back-dated to the roll start) → liftoff
  (vr ≥ 192 ft/min twice, ≥ 500 once, or alt_geom +50 ft) → climb → departure; go-around (≥ 150 ft above the lowest
  point and ≥ 500 ft/min, never after touchdown); rejected take-off; cold starts mid-roll; "late" landings acquired on
  the runway (back-dated); departures that happened inside a data gap. The E175's flag switches at ~50 kt, not 100 kt
  (observed: SKW6014/SKW5777/QXE2418 first airborne report at 47–54 kt) — the machine never uses the flag as an event.
  Labels and aircraft configuration follow the phase **at display time** (history of data-time transitions).
- **Vertical.** `alt_geom` + 32.29 m (EGM96 at the ARP) − 0.8 × crown height (antenna); QNH-corrected baro with a
  learned bias as fallback. Below ~300 ft on final it blends into a 3° line to the 1,020 ft aiming point
  (FAA AC 150/5340-1M §2.6, via HANDOFF) with a flare from 30 ft that floats to the predicted (770 m, observed median)
  or detected touchdown point.
- **Surface.** Surface `track` ignored; position jumps rejected (3 consistent jumps = re-acquire); taxiing reports are
  map-matched to the OSM taxiway/taxilane graph (lateral snap ≤ 10 m, heading ≤ 35°, continuity bonus); parked aircraft
  use the median of their reports with 4 m / 5° hysteresis; heading of an aircraft first seen still without a heading:
  runway departure direction, taxiway centreline facing the nearest runway, **OSM stand lead-in line**, stand, building
  face, terminal core. Vehicles (category C1–C7, SERV/GRND/TWR, `adsb_icao_nt`, relay `_veh`) and identity-less `~`
  ground targets (inferred) are ground vehicles: amber markers, vehicle kinematics, only in search.
- **Stands.** 1) SFO's allocation from the relay (`/api/gates`, callsign → stand window, regional aliases) when the
  aircraft is within 70 m of that stand; 2) geometry + reported heading (≤ 35°) + physical fit; `aodb`/`gate`/`excl`/
  `alt_of` of the rebuilt stand records are used (AODB names, mutually exclusive stands). Parked on the lead-in line at
  the aircraft's own stop mark (stop bars differ by type; never past the surveyed stop point), or in its own reported
  pose when that differs by > 8° / 6 m and is clear of buildings and neighbours. An aircraft whose transponder goes off
  while docking completes the docking. A remembered (silent) aircraft is removed when a live one stands in its place.
  Card: "Gate X · SFO ✓" and one-click checks on flysfo.com and FlightAware.
- **GroundPhysics.** Pavement = rendered mask ∪ OSM aprons ∪ 7.6 m taxiway strips (the `app.js` order bug that nulled
  the mask is fixed); stand-parked aircraft are checked against each other (an own-pose parking yields to the stand
  pose); free parked aircraft get the nearest valid pose ≤ 6 m away (never beyond the report scatter); moving ones a
  fading target offset — all corrections act on the target, so they are driven, not slid.
- **Statistics.** `stats.js` from the engine's events: arrivals/departures per runway, go-arounds, ROT, taxi times;
  one line in the panel ("28L ↓4 ↑12 · … (last N min)"); `window.SFO.stats()`.

## 2. How it was validated (real traffic, headless)

`sh tools/live/replay_engine_all.sh FROM UNTIL DIR` (needs `CANVAS_MODULE`, see `replay_engine.mjs`):
1. `build_stream.py` replays the recorder files through the relay's **own** `Hub` merge on a simulated clock → the exact
   SSE event sequence a browser would have received, plus SFO's plan as `/api/gates` served it (`gates.jsonl.gz`).
2. `replay_events.py` → ground truth (definitions in its header; offline estimates from the same ADS-B).
3. `replay_engine.mjs` runs `parsePayload` → `Traffic` → `GroundPhysics` unmodified at 10 Hz and measures every frame:
   ground kinematics at the main-gear centre, air kinematics at the reference point, teleports (frame displacement
   > (|v| + 5 m/s)·dt + 1 m, excluding re-acquisition after a data gap), planform overlaps, gear points off pavement,
   airframe points in buildings.
4. `replay_score.py` → phase agreement at display time, runway and event timing, displayed touchdown point, position
   error, stand vs SFO, physics. Variants: with SFO's plan (as deployed), without it (independent stand check), and a
   fixed 1.5 s delay.

## 3. Results — 24 Sep 2026 15:25:30–16:44:58Z (80 min of daytime traffic; `refs/cache/replay_day3`)

2,538 relay events; 57 arrivals, 45 departures, 1 go-around, 94 in-blocks, 70 off-blocks in the engine's own events.

| Metric | With SFO plan (deployed) | No plan | Fixed 1.5 s delay |
|---|---|---|---|
| Display delay (median) | 3.0 s | 3.0 s | 1.5 s |
| Phase agreement at display time (all rows / excl. definitional "air-other") | 0.955 / 0.977 | 0.955 / 0.977 | 0.954 |
| per phase: final · approach · rollout · takeoff · departure · taxi · pushback · still | 0.895 · 0.954 · 0.960 · 0.815 · 0.956 · 0.991 · 0.765 · 0.997 | same | 0.896 · 0.954 · 0.934 · 0.782 · 0.953 · 0.990 · 0.759 · 0.997 |
| Arrival runway correct | **57 / 57** | 57 / 57 | 57 / 57 |
| Departure runway correct | **45 / 45** | 45 / 45 | 45 / 45 |
| Go-arounds (truth 1: AAL2885 28R 15:51Z) | **1 detected, 0 false** | same | same |
| Touchdown time − truth estimate (p10/p50/p90) | −4.5 / +0.1 / +2.3 s | same | same |
| Liftoff time − truth estimate | +0.1 s (same estimator: not independent) | same | same |
| Displayed touchdown point − truth (p50 / p90) | 97 / 323 m | same | 100 / 353 m |
| Position error p50/p99: taxiing · parked · air < 10 NM · air far | 1.3/24 · 1.6/25 · 4.3/156 · 5.3/40 m | same | 1.9/64 · 2.5/26 · 6.7/184 · 6.3/61 m |
| Behind real time (p50): taxi · air < 10 NM | 16 m · 289 m | same | 9 m · 151 m |
| Stands vs SFO's allocation (visits ≥ 10 s): agree / disagree / no stand shown | **69 / 3 / 15** (95.8 %) | 69 / 3 / 16 (95.8 %) | 69 / 3 / 15 |
| Teleports (unexplained resets) | 8 (all GA/bizjet, air or other airports) | 8 | 15 |
| Re-acquisitions after data gaps / first placements | 54 | 54 | 59 |
| Planform overlap (aircraft-frames at 10 Hz) | 196 (≈ 20 s: SKW5596/UAL822 10 s, EJA777 bizjet pairs 9 s) | 136 | 130 |
| Gear off pavement (mask ∪ OSM) / of 3.16 M ground aircraft-frames | 127,524 (4.0 %; 83 % = 3 cargo aircraft on the unmapped north cargo apron) | same | 161,792 |
| Airframe inside a building | **0** | 0 | 0 |
| Ground kinematics p99 / p99.9: along · lateral accel · jerk · yaw rate · sideslip | 1.4/3.0 m/s² · 0.6/1.9 m/s² · 2.6/18 m/s³ · 6.9/18°/s · 1.6/2.0° | same | 1.4/3.0 · 0.8/2.5 · 25/50 · 8.1/20 · 1.8/2.0 |
| Air kinematics p99: along · lateral · vertical accel · turn rate | 2.0 · 5.7 · 2.0 m/s² · 5.6°/s | same | same |
| Exceedance frames (ground > 3.5 m/s² along, > 3 lat, > 6 m/s³ jerk, > 25°/s yaw, > 5° slip) | 393 · 38 · 1,405 · 4 · 4 | same | 755 · 68 · 10,848 · 5 · 5 |
| Tow seconds (slow re-positioning of stopped aircraft) | 1,669 s over 80 min, all aircraft | 1,604 s | 2,071 s |

Reading the table:
- Every runway, every touchdown/liftoff and the one go-around were right; the one runway-change event (UAL2820
  16:08Z, 28R → 28L) ended on the truth's runway (28L).
- Stand disagreements: ACA738 (engine C10, SFO D11 — the known C10 → D11 tow, gate_truth §3), UAL1329 (F21 vs D6,
  24 m lateral of the stand: inferred to be a holding position, not a stand), UAL1896 (E5 vs D5). "No stand shown" are mostly
  docking-in-progress visits of 30–170 s; long ones: DAL1053 at SFO's C11 for 16 min (the C11 survey, audit F7),
  SKW5596 at G7 (G7 was held by a remembered silent aircraft until it was replaced).
- Phase residuals are mostly timing: take-off roll starts are recognised after ≥ 12 kt (back-dated), push-backs of
  aircraft without a true heading are recognised after the first chord, "final" is declared at posterior ≥ 0.9.
- Air p99 errors come from liftoff/transition transients of bizjets and one helicopter (C6556) far from any runway.
- Truth caveats: the touchdown estimate for E175/CRJ is weak (their flag flips at ~50 kt), so the displayed-touchdown
  outliers (SKW6052 2 km, SKW5519 1.2 km) are truth-side; the liftoff "truth" uses the same climb rule as the engine.

Earlier window (15:13–15:45Z, with the recorder's 15:21:32–15:25:02 gap): arrivals 18/18, departures 12/12 runway
correct, stands 36 agree / 2 disagree, overlaps 88 frames, 0 in buildings.

Browser checks (headless Chromium, `SOFTGL=1`): `jobs/relaytest.mjs` against `sfo_live_server.py --replay … --from
15:40Z`: SSE stream, 122–128 aircraft, SFO-plan gates, stats line "28L ↓2 ↑0 · 28R ↓1 ↑0 …", delay 1.8 → 3.0 s;
`jobs/snaptest.mjs` (snapshot mode, the artifact build): 48 tracks, 9 gates, no page errors.

## 4. Open points

- adsb.lol's throttling keeps the delay at 3 s; with a feeder account or own receiver (realtime_feeds §3) the same rule
  would settle near 1.5 s.
- The north cargo apron is missing from both pavement sources (request §2); stand survey evidence (request §3).
- Push-back and take-off-roll recognition lag a few seconds; slow towing of stopped aircraft (1,669 s in total over the
  80 min) remains where later reports move a stopped aircraft's pose.
- The UI stats line counts only what the page has seen since it opened; the ATC toggle is a separate step.

---------------------------------------------------------------------------------------------------------------------

# Step 3 — the UI (24 Sep 2026, ~19:00 UTC)

Scope: `js/live/ui.js`, `app.js`, `about.js`, `stats.js`, new `atc.js`, `traffic.js` (two small additions), `feed.js`
(route airports keep lat/lon), `live.css`; test `jobs/uitest.mjs`. Sources: `atc.md`, `gate_truth.md` §6,
`realtime_feeds.md` §1 (attribution), `docs/ATTRIBUTION.md`.

## 1. What was added

- **Status bar** `Live · 3.0 s · adsb.fi + adsb.lol`: how far the scene runs behind real time (the engine's adaptive
  interpolation delay plus the ATC audio delay) and the providers of the last merged update (relay `_source`). The
  tooltip adds the aircraft count and the split. Snapshot mode: `Recorded · 23 Sep 10:51 PDT`.
- **Detail card**: airline, callsign (+ SFO's IATA flight number when the relay has the plan), type, phase, tail,
  route (adsb.lol/VRS; else SFO's origin/destination marked "per SFO"), **Runway** (on final / lined up / take-off roll /
  departed hh:mm / landed hh:mm, from the engine's own detection), **Gate**:
  - `Gate F21 · per SFO ✓ (departure gate)` when the observed stand is any stand SFO lists for this callsign's arrival
    or departure with a window within ±45 min of now (or its passenger gate when SFO lists no stand). A turn with a
    tow has two stands (observed: UAL1329 arrival D6, departure F21), so both count;
  - `Stand B12 · from position` + `SFO says D6 arrival 8:57–10:48 AM · F21 departure …` when none matches;
  - `SFO … · not parked at a known stand yet` when the aircraft has no stand yet;
  - **Check** links: `https://www.flysfo.com/flight-info/flight-status?type=arrivals|departures&search=<number>` (the
    number SFO lists, i.e. the marketing number for regional callsigns; parameters observed in SFO's page code,
    gate_truth §2, not tested in a browser) and `https://www.flightaware.com/live/flight/<callsign>` (human use per
    FlightAware's terms);
  - altitude, speed, vertical rate, squawk, operator, **ATC** (likely position, e.g. `TWR 120.5 → DEP 135.1`), **Data**:
    age of the newest position, its provider (adsb.lol / adsb.fi, MLAT flagged), hex.
- **Runway sheet** (tap the stats line under the tabs): configuration in use inferred from the last 20 min of observed
  landings/take-offs (no ATIS read); arrivals / departures / go-arounds per runway in the last 60 min with the time of
  the last movement; last-10-min counts; rejected take-offs; **now**: on the runway, holding short (within 150 m of a
  centreline — the 76 hold bars in `data/sfo_details.js` lie 75–96 m from it), taxiing out, on final per runway with
  distance; go-around list (time, flight, type, runway, lowest altitude); medians of runway occupancy, taxi-in, taxi-out
  (with sample counts); latest 12 movements. Rows select the aircraft. All counts use **scene time**: an event is shown
  only once the 3D view (and the audio, with a delay) has reached it.
- **ATC sheet** (`ATC` pill in the top bar; `atc.js`): the 16 LiveATC KSFO mounts of the 23 Jun 2026 capture grouped by
  role (Tower, Ground, Clearance, Approach finals, Approach arrivals, Departure, ATIS, Ramp, Center, Other), each
  frequency badged **FAA** (published for SFO; tooltip = the publication) or **LiveATC label** (dashed; not found in any
  FAA source for SFO, atc.md §1.5); `Listen on LiveATC ↗` is a plain link to LiveATC's own player page
  `https://www.liveatc.net/hlisten.php?mount=<mount>&icao=ksfo` (new tab; never an `<audio>` element, stream URL,
  proxy or status probe — atc.md §3.2); `Highlight` tunes the feed: aircraft likely on it get a green ring and a
  frequency chip on their 3D label and list row, and are listed in the sheet. FAA approach frequencies no feed carries
  (128.575, 134.5) are listed. Credit line "ATC audio: LiveATC.net". The tuned mount and delay are remembered per device.
- **Likely-on-frequency rules** (atc.md §4.2, [INF]): gate/parked with a departure expected → Clearance 118.2 (low);
  push-back, or taxi/holding inside an OSM apron polygon → Ramp; taxi/holding elsewhere → Ground 121.8; line-up,
  take-off, landing roll, go-around → Tower 120.5; final ≤ 6 nm → Tower, beyond → Approach finals (28R 133.175/120.35,
  28L 135.65, LiveATC labels); approach → feeder by the origin airport's bearing (else the entry bearing): east
  30–125° → 128.325, south 125–240° → 128.575 (no feed), north/west → 133.95; departure → Tower for 90 s or below
  2,500 ft, then 135.1 (destination bearing 135–270°) / 120.9 (315–90°) / both in between.
  Limitation: only 18 OSM apron polygons exist (9 of 33 ground aircraft of the snapshot fall inside), so most ramp
  movements are attributed to Ground; the ramp/movement boundary is unknown (atc.md §5 Q9).
- **Audio delay 0–30 s** (`Traffic.audioDelay`, `displayTime = now − delay − audioDelay`): the whole scene — aircraft,
  phases, labels, stats, clock and jet-bridge docking (stand changes are queued by the delay) — runs that much later.
  A change > 2 s re-places every body at its target (an explicit jump in time; counted in `counters.timeJumps`);
  smaller changes are ramped at ≤ 0.25 s per s.
- **About / attribution**: the exact ADS-B notice of realtime_feeds §1, the notices of `docs/ATTRIBUTION.md` (OSM ODbL,
  SFO Museum CDLA, USDA NAIP, FAA NASR / AL-375, SFO DataSF), FAA frequency editions, flysfo (with the `--no-sfo-gates`
  switch), LiveATC, NOAA, model licences. The footer line carries the ADS-B/ODbL credit on every screen.
- **Phones**: the ATC and runway sheets are bottom sheets (78 vh) that hide the card while open; the ATC pill sits in the
  top bar.

## 2. Verification (headless Chromium, SOFTGL=1)

`jobs/uitest.mjs` (`node livetest.mjs jobs/uitest.mjs`; env `MODE`, `RELAY`, `MOBILE/W/H/DPR`, `SHOTS`, `TUNE`):
- **Snapshot mode** (the artifact build, no network): page loads, card/stats/ATC sheets render, 16 feeds with 24 FAA and
  16 LiveATC-label badges, links are `hlisten.php` pages, highlighting the Ground feed marks 22 labels, a 10 s delay
  moves the scene to 11.5 s behind and the status to `Recorded … · +10 s`; no page errors.
- **Gate rows vs SFO** on real traffic (every aircraft at a stand with a callsign, three page loads at replay times
  ~15:44Z, ~16:22Z, ~16:30Z): 15/15, 12/12 (+2 without an SFO record) and 10/10 "per SFO ✓", 0 "SFO says …". This uses
  SFO's plan (the engine's stand choice prefers it, step 2 §1); the independent no-plan agreement is step 2's 95.8 %.
- **Real traffic** (relay `--replay refs/cache/rec --from 2026-09-24T15:40Z`, desktop 1280×720): status
  `Live · 3.0 s · adsb.fi + adsb.lol`; stats line `28L ↓2 ↑1 · 28R ↓2 ↑0 · go-arounds 0 · ROT 24 s (last 4 min)`; sheet:
  configuration "Landing 28L · 28R · Departing 28L", on runway UA291 28L, holding short UA717, finals 28L (UA2274 2.5 nm,
  UA653 9.0 nm) and 28R (OO5596 5.8 nm, AA2885 13.0 nm); likely per feed ksfo_twr 5, ksfo_gnd 27, ksfo_app2_r 15,
  koak_dep 3, ksfo_gnd2 7; delay 10 s → scene 13.0 s behind; no page errors.
- Phone (390×844, DPR 2) and desktop screenshots: `out/live/ui_phone_live_{card,stats,atc}.png`,
  `ui_desk_live_{card,atc}.png`, `ui_phone_final_atc.png`, `ui_desk_final_card.png`. Fixed after looking at them: the
  status pill truncated to "Live · …" on phones (providers now hidden there, kept in the tooltip), the runway line was
  below the phone peek (peek raised to 128 px), the top bar overlapped the view buttons at 1280 px (views move down
  below 1440 px, providers hidden below 1720 px), a linked SFO departure number (UA336 for arrival UAL1095) was shown
  as if it were the flight's own number.

## 3. Engine fixes found through the UI (traffic.js)

The runway sheet showed "Landing 28R · 10R · 28L" and a rejected take-off for UAL1372 on real traffic:
- **Touchdown by the ground flag only at ≥ 40 kt.** UAL1469 (B753) taxiing at 16 kt east of 28L sent airborne-flagged
  reports, entered "final 10R" and was counted as a 10R landing when the flag returned (also in the step-2 day replay:
  `touchdown … rwy 10R, how flag, gs 16`). Below 40 kt the spurious final now becomes taxi, no event.
- **Cold start on a runway at speed.** A page opened while an aircraft is on its landing roll saw one fast report,
  started a take-off roll and then logged a "rejected take-off" when it slowed. Now the first report of a new track on
  a runway at > 40 kt is not classified until the second one, and a "take-off" entered from a cold start that
  decelerates within 30 s becomes a late landing. Checked with cold starts at 16:21:33Z and 16:21:38Z (UAL1372 rolling
  out on 28L): `touchdown UAL1372 28L late`, no rejected take-off.
- Day replay 15:25:30–16:44:58Z re-scored (`refs/cache/replay_day3/score_engine_ui.json`): arrivals 57/57 and departures
  45/45 runway-correct, go-around 1/1, stands vs SFO 95.8 %, phase agreement 0.955, teleports 8, overlap frames 196 —
  identical to step 2; touchdown events 59 → 58 (the false 10R one removed).
