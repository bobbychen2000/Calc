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

---------------------------------------------------------------------------------------------------------------------

# Step 4 — review round 1 fixes (24 Sep 22:00Z – 25 Sep 17:30Z)

Scope: `js/live/traffic.js`, `ground.js`, `app.js`, `tools/live/invariants.mjs` (final `traffic.js` md5 c3981bd7; the full-run numbers are for 067f86c5, the verification subset for 4f779128). The review (21 findings, adversarial,
on the relay-merge replay of `refs/cache/rec`, code `traffic.js` md5 b91c9f19) is answered below finding by finding.
Most of the engine work was done by the previous run of this step (interrupted by a usage limit; its edits are in the
WIP commits 64ffe00 and a8e0538); this run re-verified every item on the real traffic, fixed what was still wrong, and
added the items of §2–§3.
Method: every change was traced on the real aircraft the review named (`invariants.mjs --trace <hex>`, which now also
prints lock / bridge / leaving state and the engine's events for that hex), then the whole recording was re-checked.
The replay is deterministic: the same code and data give identical counts (checked: two runs of 4.2 h agreed in every
class except `offpave.*`, which changed only because `data/sfo_pavement.js` changed between them).

## 1. Findings

| # | Finding (review round 1) | Status | What changed | Evidence (replay) |
|---|---|---|---|---|
| 1 | Bridge docks to the first pose estimate, never follows it (critical) | fixed | The engine docks only once the drawn body has come to rest at its parked pose (`syncBridge` lock), to exactly that drawn pose (`tr.dockPose` → `app.js poseST`); an estimate change > 6 m / 10° unlocks, retracts and re-docks after the body has settled; small changes keep the lock (the real aircraft did not move) | `bridge.misdock` 1,416,822 → 0 frames |
| 2a | Push-back drags the fuselage through the docked bridge (critical) | fixed | Confirmed motion sets `leaving`: the bridge retracts first and the body is held (brakes ≤ 1.5 m/s²) until the extension is 0 (`holdBridge`, `traffic.bridgeK` from `app.js`) | `bridge.attached.moving` 4,948 → 0 |
| 2b | Retracted cab/tunnel inside parked aircraft (critical) | open — gates.js (not owned) | Request `docs/requests/realtime_round1.md` §1a (use the data's `stowW`); new informational class `bridge.hit_at_rest` isolates it | `bridge.hit.fus` 122,531 frames (13,299/h against 22,622/h), of which 65,730 with the bridge fully retracted; the rest are retraction frames (the cab is interpolated straight from the door to the rest point) |
| 2c | MARS alternates (B5S/B16S/C9V) ignore `shares_bridges_of` (critical) | fixed on the engine side | `app.js bridgeGate()`: an alternative position docks its base stand's bridges; the retracted base-stand bridge clearing the alternative's aircraft is gates.js (§1d) | SJX011 A359 at B5S: B5 bridge docked to it; its push-back still crosses the retracted B5 tunnel (rest pose) |
| 3 | Silent aircraft kept as ghosts on taxiways (critical) | fixed | A track that goes silent while taxiing / pushing / lined up / holding on a taxiway or runway is faded out after 45 s (moving) or 75 s; only aircraft parked at a stand or on a ramp are kept; a remembered aircraft a live one drives into is removed (`GroundPhysics`, `stale-replaced`) | `overlap.gnd` 2,880 → 195; `clear.taxi` 313 → 44 |
| 4 | Push-back latch clamps a taxiing aircraft to 1 m/s (critical) | fixed | Push without a heading ends when the chord agrees with the nose again or above 10 kt; the push speed clamp never goes below the target's own forward speed + 0.5 m/s; the ground reset is a fade | a6bbef 07:42Z: no teleport, no loop (`teleport` 1,347 → 0) |
| 5 | First motion out of a nose-in stand driven forward into the terminal (critical) | fixed | At a contact stand the first motion is a push-back unless the chord is clearly along the nose (`report()`); building veto in `ctlGround` (the nose / tail never enters a building: it stops at the face) | `building` 14,858 → 37 |
| 6 | Bizjet take-off rolls out-accelerate the body → 200 m teleport (critical) | fixed | Roll acceleration 5 m/s² for light/business jets (3.3 airliners), speed-change feed-forward, a runway roll is never hard-reset (error > 600 m → fade) | `gnd.acc.runway` 352 → 0; `teleport` 1,347 → 0 |
| 7 | E175 first seen mid-rollout stays 'Takeoff roll' for 40 min (critical) | fixed | A cold-start 'takeoff' that decelerates or is below 40 kt within 90 s becomes a late landing; 'takeoff' times out after 20 s slow / 90 s; `M.rwy` cleared at in-block | SKW3007/SKW3463 a178ae 15:13:41Z: `touchdown 28L late` at 15:13:43.9, exit, in-block B7 (SFO) 15:17:36 |
| 8 | Parked body stuck 6.5 m / 21° off; re-acquired parked aircraft driven across the stand (major) | fixed | One distance for hold/tow; a body stopped > 10 s off its stop target is re-placed with a fade; a parked aircraft heard again within 15 m keeps its parking (no drive) | `phase.gate_far_from_stand` 1,902 → 131 |
| 9 | 'Airborne' flag at the gate lifts parked aircraft (major) | fixed | An 'airborne' report inside SFO below 30 kt (50 kt right after a ground report) at field altitude is a ground report (rotorcraft excluded) | `vert.float` 1,070 → 0; `phase.gndphase_in_air` 43 → 0 |
| 10 | Unpaved 1L/1R crossing (major) | data — not owned | Request `realtime_round1.md` §3 (static workflow); `data/sfo_details.js` now has "1 NAIP-traced E-W crossing of 1L/1R that OSM lacks" (static_geometry_round2.md) | `offpave.union` 334,309 frames (per h 36,283; review 47,234/h) |
| 11 | False go-arounds, final runway flips (major) | fixed | 'final' needs a jet/turboprop (or A2-A5), identified, at approach speed, descending ≥ 300 ft/min; go-around only from < 1,500 ft; the runway is shown as the pair until firm, a firm runway changes only at ≥ 0.99 for 20 s | go-arounds: 6 true go-arounds detected with the right runway (6), 0 missed, 0 extra; `rwy.change.final` 14 → 0 |
| 12 | Pose snaps at first sight, 0.4 m/s instant stops (major) | fixed | A body first seen standing stays hidden until its parked pose has settled (≤ 10 s) and fades in; re-placements fade out/in (0.4 s); braking ramp | `hdg.flip` 429 → 1; `jump.gnd_1_20m` 301 → 0; `gnd.acc.taxi` 12,820 → 313 |
| 13 | Unmatched parked aircraft inside buildings; stand pairs closer than ICAO (major) | fixed (engine); data for spacing | Nearest-valid-pose search widened to 15 m; database types contradicting the transponder category replaced (DAL1053 A333 → BCS3, SFO); stand spacing F6/F7, G1/G2, G2/G5 → static workflow | `building` 14,858 → 37; `clear.stand` 46,661 (F6/F7 E75L 3.96–4.38 m at the stand poses) |
| 14 | Bridges dock to invisible aircraft (major) | fixed | Docks only for an aircraft with a 3-D airframe; category-conflicting database types resolved (PA27 → A21N) | `bridge.orphan` 56,897 → 684 (the rest: bridges retracting after their aircraft was removed) |
| 15 | Teleports after data gaps (minor) | fixed | A gap > 30 s (ground) / 15 s (air) is a fade re-placement; the card says "no data N s" | `teleport` 1,347 → 0; `jump.air_5_20m` 594 → 0 |
| 16 | Implausible air kinematics, GA floating at other fields (minor) | fixed | Altitude steps > 6,000 ft/min accepted only after 3 consistent reports; vertical speed capped; GA 'airborne' < 50 kt at low altitude = ground | `air.vs` 4,833 → 334; `vert.float.other_airfield` 74,235 → 2,608 |
| 17 | Checker notes | extended | `invariants.mjs`: trace prints lock / bridge / leaving / stop error and the engine events of the traced aircraft; `bridge.hit_at_rest`; a retracting bridge's own aircraft counts as its own (cab at its door); no-slip point of type-less aircraft = the engine's (8 m) | — |
| 18 | Push-back inferred on every restart without a heading (UAL888) (major) | fixed | Inferred only at a stand / parking position for the first movement after in-block; one off-block per turn | 0 `phase.pushback_forward` frames (review 639) |
| 19 | Route/runway text kept after a callsign change at the gate (major) | fixed | A new flight number clears the route (re-requested), the direction and the arrival runway row | `setInfo` clears `tr.route` / direction on a new flight number (`counters.callsignChanges` 4 + 6 in the 16:45–18:05Z chunks, e.g. AAL76 → AAL16); `app.js` re-requests routes for tracks whose route is undefined; the Runway row shows the landing runway only while the flight is the arrival |
| 20 | Gate lost on every silent minute; parked bodies jump (major) | fixed | Heard again within 15 m of its parking at < 3 kt = the same parking (gate, pose, bridge kept); motion out of a stop needs two consistent reports (parked multipath never moves the body) | 382 in-blocks for 371 aircraft in the full run; 11 aircraft with more than one, all at push-back time (a push that paused, or a 'forward' first motion before the push) plus DAL1053 / UAL869 re-matched to the same stand after 20 s — none from silent minutes (review: AAL177 ×4, JBU633 ×5, AAL179/166 ×6, ACA739/740 ×5). The paused-push case is fixed in the final code (§2). Parked GNSS wander no longer moves the pose (§2) |
| 21 | Wrong database type drawn (DAL1053 A333 is a BCS3) (major) | fixed | `resolveType`: a database type whose wake class contradicts the emitter category is replaced by the other provider's type or SFO's (`typeSrc` shown on the card) | DAL1053 (A333 in both databases, category A3) drawn as BCS3 from SFO's record, in-block C11 16:52:15Z (SFO's stand). Without SFO's record (snapshot mode, `--no-sfo-gates`) the database type stays, flagged on the card |

## 2. Also found while re-checking (this step)

- **A bridge that never docked (UAL2 B789, G8, 24 Sep 15:20–16:41Z).** Arrivals close up to their stop mark at 0.3–0.6 m/s,
  which reads as stationary: the aircraft locked, the bridge was called, then the confirmed 7 m creep counted as a
  "forward off-block" and set `leaving`, which was cleared only by 20 s of stationary reports — the transponder went
  silent 15 s later, so the bridge stayed retracted (against the fuselage) for the whole turn. Now `creepToStop()`:
  forward along a contact stand's lead-in, < 3 kt, not past the stop point = not an off-block and not leaving; `leaving`
  clears after 8 s stationary (5 min after a real off-block) or when the aircraft goes silent at its stand; an arrival's
  bridge waits `DOCK_WAIT_MS` 20 s after the body came to rest (plus gates.js `DOCK_DELAY` 12 s), and never while a
  confirmed moving report lies ahead of the display [inferred design value: engines off / beacon off before a bridge
  approaches]. Trace after the fix: locked 15:20:44.8, crept 7 m, re-locked 15:21:07, bridge called 15:21:27, docked
  (k = 1) by 15:22:30.
- **A sparse track shown as fade re-placements (UAL718 A320 into B11, 17:55:49–17:56:09Z).** Reports 10–14 s apart: the
  two moving candidates needed to confirm motion were reset after 12 s, so a real 21 m move was drawn as two
  fade-out/fade-in re-placements. The candidate window is 25 s, and a stop report that follows a moving candidate counts.
- **Reversing at 2.9 m/s without a push-back in the data (SKW3450 E75L, no true heading, 16:35Z).** The inferred-push
  catch-up is limited to the target's speed + 0.7 m/s (≥ 1 m/s); a body moving backwards is labelled "Pushback".
- **Labels follow the drawn body**: "Landed" becomes "Taxiing" once the body is > 40 m off the centreline, "Pushback"
  becomes "Taxiing" when the body rolls forward (both were `phase.*` contradictions in the review).
- **Air**: vertical speed ≤ 6,000 ft/min (or the reported rate × 1.1) with a vertical error > 200 m re-placed by a fade;
  heading-vs-track crab changes ≤ 1.5°/s (4°/s below 15 m) and is kicked out below 10 m on final — the crab filter had
  added up to 6.7°/s to the drawn turn rate of E175 departures (9–10°/s shown, `air.turn`).
- **Other airfields**: "airborne" below 50 kt and below ~255 ft MSL (`alt_geom` < 150 ft HAE) is a ground report (GA
  landing rolls at Palo Alto / San Carlos were drawn as 0 kt floats, `vert.float.other_airfield`).
- **Parked pose frozen at the stand while the transponder says 0 kt.** 20 s after in-block, reports below 0.5 kt no longer
  move the parked pose or the stand choice (position wander near the terminal is ±15–25 m at 0 kt); a report ≥ 0.5 kt
  (a slow tow) or confirmed motion unfreezes it, and a stand is left only after the pose has misfit it for 20 s and not
  within a minute of in-block. AAL177 (A321, SFO stand B16, 07:46Z): before, the 0.0 kt reports wandered 24 m toward
  B15, the body was re-placed three times and the stand flipped B16 → B15 → B16; now one in-block, B16, for the night.
  A parked aircraft heard again after silence is the same parking when it is within 15 m **or still inside its stand's
  limits** (AAL179/AAL166 at B25, 19:17:31Z: the first fix after silence lay 16 m off, the gate was released, the bridge
  retracted and re-docked; now one in-block for the turn).
- **Stops without a reported heading**: the drawn body's own heading is kept (no inferred heading target), so an aircraft
  like UAL888 (B772, no `true_heading`) no longer fades out and back in at each of its taxi stops because the heading
  guessed from the last reports differed from the body by 20–52°.
- **In-air re-acquisition** after a gap: an error within ~2 s of flight is flown out, not faded (SWA2980 / UAL2259 had
  been faded for 30 m at 150 m/s); the re-acquisition flag is spent once the body is close. Leaving the slow-target
  (point-follower) controller keeps the velocity direction and carries the heading difference in the crab term.
- **Any slow non-push motion in the first 10 min after in-block at a contact stand is a creep** (UAL984 B77W at G8:
  a 'forward off-block' 26 s after in-block kept its bridge retracted against the fuselage for 46 min).
- **A push-back that pauses on the lead-in is not a new in-block** (UAL1111 at E7, 15:38:19–15:39:09Z: off-block,
  in-block E7, off-block). The stand an aircraft pushed from is not matched again for 10 min, so its bridge cannot
  come out again either.
- **Snapshot mode (the artifact build)**: the 90 s reload of the recorded instant re-places moving aircraft with a fade
  instead of removing them (a pop every 90 s). `jobs/snaptest.mjs` (SOFTGL=1, 100-150 s, before and after the last
  engine changes): 48 tracks, 9 gates, no page errors. Live path: `jobs/relaytest.mjs` against
  `sfo_live_server.py --replay refs/cache/rec --from 2026-09-24T17:40Z --routes off --no-sfo-gates`: SSE stream,
  129 tracks, 21 stands matched (UAL888@G5, UAL35@G3, AAL76@B25, UAL2649@D16 ...), stats line
  `28L ↓2 ↑0 · 28R ↓1 ↑0`, status `Live · 1.3 s`, no page errors (the 503s are the disabled routes / gates).

## 3. Requests from the static workflow answered (static_geometry_round1/2.md, stands_rebuild.md)

- `standFits`: the A380 / 747-8 / 777-9 clause only on stands with `a380` (A6, A11, G13), not on every EL stand;
  `types_ok` (E10/E12, F19/F20) honoured for geometric matching (SFO's own allocation is still followed).
- Per-family stop points (`type_stops`: B737, A320, EJET, A220 on 9 stands): the stand score expects the nose there, and
  the parked pose uses it when the aircraft's own reports agree within 6 m; a pose short of the stop that touches an
  occupied neighbour moves to the stop (`GroundPhysics` → `tr.shortBlocked`; counter `shortBlocked`).
- SFO-plan path: skips a stand whose mutually exclusive stand (`excl`) is occupied by a live aircraft; a silent one
  there is replaced (`stale-replaced`, `excl`).
- `conflict` stands (D3, D4, D8, D9): the stand score tolerates the documented offset (lateral + |lat_med| + 2 m,
  heading + |dhdg_med|) instead of matching such an aircraft to a neighbouring stand.
- Persistence key `sfolive.parked.v4` (stand names changed back to gate numbers).

## 4. Metrics (tools/live/invariants.mjs, 10 Hz, every drawn frame)

Review round 1: code `traffic.js` b91c9f19, 6.9 h checked (the reviewer's own run). Final: code of this step, 9.2 h checked (24 Sep 07:37:30–10:28Z, 15:23:40–19:27Z, 19:40–21:59Z; each chunk after a 10 min warm-up). The windows differ, so the per-hour rates are the comparison. Frames at 10 Hz; episodes in brackets.

| class | review round 1 | per h | final | per h |
|---|---|---|---|---|
| `air.acc` | 211 (48) | 31 | 562 (101) | 61 |
| `air.lat` | 78 (11) | 11 | 70 (2) | 8 |
| `air.turn` | 4,386 (197) | 636 | 408 (12) | 44 |
| `air.vacc` | 852 (537) | 123 | 1,324 (843) | 144 |
| `air.vs` | 4,833 (41) | 700 | 334 (24) | 36 |
| `bridge.attached.moving` | 4,948 (98) | 717 | 0 (0) | 0 |
| `bridge.hit.fus` | 156,108 (226) | 22,622 | 122,531 (50) | 13,299 |
| `bridge.hit.tail` | 165 (7) | 24 | 0 (0) | 0 |
| `bridge.hit.wing` | 28,318 (33) | 4,104 | 0 (0) | 0 |
| `bridge.hit_at_rest` | 0 (0) | 0 | 65,730 (46) | 7,134 |
| `bridge.misdock` | 1,416,822 (155) | 205,316 | 0 (0) | 0 |
| `bridge.orphan` | 56,897 (173) | 8,245 | 684 (10) | 74 |
| `building` | 14,858 (10) | 2,153 | 37 (1) | 4 |
| `clear.stand` | 47,090 (13) | 6,824 | 46,661 (10) | 5,064 |
| `clear.taxi` | 313 (52) | 45 | 44 (9) | 5 |
| `gnd.acc.runway` | 352 (112) | 51 | 0 (0) | 0 |
| `gnd.acc.taxi` | 12,820 (2610) | 1,858 | 313 (101) | 34 |
| `gnd.jerk` | 5,192 (1437) | 752 | 46 (25) | 5 |
| `gnd.lat` | 237 (80) | 34 | 1 (1) | 0 |
| `gnd.reverse` | 1,896 (69) | 275 | 341 (25) | 37 |
| `gnd.slide` | 59,771 (680) | 8,662 | 2,190 (109) | 238 |
| `gnd.slip` | 5,577 (101) | 808 | 23 (1) | 2 |
| `gnd.speed.taxi` | 0 (0) | 0 | 61 (1) | 7 |
| `gnd.spin` | 464 (53) | 67 | 135 (43) | 15 |
| `gnd.yaw` | 21 (20) | 3 | 0 (0) | 0 |
| `hdg.flip` | 429 (422) | 62 | 1 (1) | 0 |
| `jump.air_5_20m` | 594 (594) | 86 | 0 (0) | 0 |
| `jump.gnd_1_20m` | 301 (261) | 44 | 0 (0) | 0 |
| `offpave.mask` | 1,352,296 (957) | 195,965 | 594,606 (1714) | 64,534 |
| `offpave.union` | 325,948 (734) | 47,234 | 334,309 (911) | 36,283 |
| `overlap.gnd` | 2,880 (34) | 417 | 195 (5) | 21 |
| `phase.final_on_ground_slow` | 49 (1) | 7 | 0 (0) | 0 |
| `phase.flicker` | 181 (158) | 26 | 354 (332) | 38 |
| `phase.gate_far_from_stand` | 1,902 (9) | 276 | 131 (5) | 14 |
| `phase.gndphase_in_air` | 43 (3) | 6 | 0 (0) | 0 |
| `phase.pushback_forward` | 639 (55) | 93 | 0 (0) | 0 |
| `phase.rwyphase_off_runway` | 119 (16) | 17 | 0 (0) | 0 |
| `rwy.change.final` | 14 (14) | 2 | 0 (0) | 0 |
| `teleport` | 1,347 (681) | 195 | 0 (0) | 0 |
| `vert.float` | 1,070 (20) | 155 | 0 (0) | 0 |
| `vert.float.other_airfield` | 74,235 (301) | 10,758 | 2,608 (248) | 283 |
| `vert.lowfly` | 110 (2) | 16 | 0 (0) | 0 |

Classes that did not improve: `air.acc` (61/h against 31/h) is mostly the light / business jets' take-off acceleration
(≤ 5 m/s², the cap finding 6 asked for) carried through liftoff for ~2 s (C56X, GLF5, C700 climb-outs, 18 frames each at
4.7 m/s² against the checker's airborne 3 m/s²) and 3.5 m/s² braking in the last metre above the runway before the drawn
touchdown (AAL1949, SKW4798); `air.vacc` (144/h against 123/h) is light aircraft landing at other fields; `phase.flicker`
(38/h against 26/h, 332 single short episodes, e.g. `holding` ↔ `taxi` at queue stops) is label-only and not yet traced;
`gnd.speed.taxi` is one CL35 at 37 kt 153 m from the 28R centreline (VJA310, 20:52Z, high-speed exit); `building` is one
episode of 3.7 s (DAL1053 at C11, 17:11Z, released and re-matched to its stand within 20 s after a ≥ 0.5 kt report).
`clear.stand` and `offpave.*` are data (§5).

Runway events against the independent raw-data detector (final run):

| | truth | matched | right runway | missed | engine-only |
|---|---|---|---|---|---|
| Landings | 229 | 229 | 229 | 0  | 9 |
| Take-offs | 233 | 232 | 232 | 1 LXJ486 | 16 |
| Go-arounds | 6 | 6 | 6 | 0  | 0 |

Engine-only runway events are E175/CRJ/GLF movements the raw detector cannot see (§5). Review round 1 had 22 'true' go-arounds from its detector, which counted E175 take-offs (fixed in the checker since), and 6 engine-only go-arounds of VFR / helicopter / anonymous traffic.

The last changes (stops without a reported heading, in-air re-acquisition threshold, no re-in-block after a paused push-back) came after that run; they were checked on 24 Sep 15:23:40–16:05Z and 18:05–18:47Z (1.4 h, same data), the code of the run above against the final code:

| class | code of the full run | final code |
|---|---|---|
| `air.acc` | 99 | 99 |
| `air.turn` | 20 | 20 |
| `air.vacc` | 296 | 296 |
| `air.vs` | 9 | 9 |
| `bridge.hit.fus` | 31,083 | 31,083 |
| `bridge.hit_at_rest` | 6,802 | 6,802 |
| `bridge.orphan` | 254 | 234 |
| `gnd.acc.taxi` | 41 | 41 |
| `gnd.jerk` | 14 | 14 |
| `gnd.lat` | 1 | 1 |
| `gnd.reverse` | 79 | 79 |
| `gnd.slide` | 403 | 403 |
| `gnd.spin` | 30 | 30 |
| `offpave.mask` | 153,116 | 152,998 |
| `offpave.union` | 72,453 | 72,362 |
| `phase.flicker` | 71 | 71 |
| `phase.gate_far_from_stand` | 11 | 11 |
| `vert.float.other_airfield` | 434 | 434 |
| re-parks with a fade (`counters.cut_repark`) | 59 | 58 |
| gap re-placements (`cut_gap`) | 485 | 376 |
| error re-placements (`cut_err`) | 390 | 394 |
| landings matched (truth) | 50 | 50 |
| takeoffs matched (truth) | 45 | 45 |
| goarounds matched (truth) | 1 | 1 |

Three small changes followed that check and were verified on the aircraft that prompted them (same code otherwise): a
'forward' off-block no longer blocks the stand (UAL755 at F17 20:09Z: a missed push start; the paused-push fix still
holds for UAL1111, one off-block); a parked aircraft heard again inside its stand's limits keeps its parking (AAL166 at
B25: one in-block instead of two; every invariant class in 18:50–19:20Z unchanged); and slow motion at a contact stand
in the first 10 min after in-block that is not a push-back is a creep, not an off-block (UAL984 B77W at G8, 20:22:34Z:
a 'forward off-block' 26 s after in-block had kept its bridge from docking for 46 min — 27,600 `bridge.hit_at_rest`
frames against its own retracted cab; now one in-block and docked; 24 Sep 20:15–20:40Z: 894 `bridge.hit.fus` frames
in the whole window).

The step-2 replay metrics (`tools/live/replay_engine.mjs` + `replay_score.py`, 24 Sep 15:25:30–16:44:58Z, SFO plan as deployed; previous partial code vs this step's code before the last changes):

| Metric | previous run (a8e0538) | this step |
|---|---|---|
| Phase agreement at display time | 0.953 | 0.952 |
| Arrival / departure runway correct | 57/57 · 45/45 | 57/57 · 45/45 |
| Go-arounds (truth 1, AAL2885 28R) | 1 | 1 |
| Stands vs SFO's allocation | 0.959 | 0.959 |
| Position error p50/p99 m: taxiing · parked · air < 10 NM · air far | 1.17/24.72 · 1.46/12.86 · 4.2/126.29 · 5.3/39.25 | 1.17/24.73 · 1.46/13.18 · 4.2/125.97 · 5.3/39.25 |
| Behind real time p50 m: taxi · air < 10 NM | 15.73 · 287.38 | 15.73 · 287.38 |
| Display delay p50 | 3.0 s | 3.0 s |
| Teleports · overlap frames · in-building frames | 0 · 0 · 0 | 0 · 0 · 0 |
| Exceedance frames: air turn > 7°/s | 465 | 84 |
| Engine events: in-block · off-block | 85 · 60 | 83 · 59 |

The display stays 3.0 s behind real time on the public feeds (median report age; the adaptive delay's maximum), so an arrival at 140 kt is drawn ~290 m behind where it is now; the step-2 fixed 1.5 s variant halved that at 7.7× the ground jerk exceedances. Lower latency needs a feeder account or own receiver (realtime_feeds.md §3).

## 5. Not changed, with evidence

- **Truth-side mismatches, not engine errors.** `rwy.truth.*_extra`: E175/CRJ landings and take-offs the raw detector
  cannot see (their air/ground flag flips at ~50 kt, so there is no fast ground report; documented in the checker
  header). `rwy.truth.takeoff_missed` LXJ486 (GLF4, 24 Sep 21:54Z): it *landed* on 28R — raw reports decelerate from
  110 to 45 kt airborne-flagged, first 'ground' at 45.5 kt (21:54:06), then one 'airborne' report at 45.2 kt (21:54:08),
  which the detector reads as a take-off; the engine logged `touchdown 28R decel a=316 m` at 21:53:50 and the exit
  after 44 s. DAL495A (17:17Z, "missed" in the review): matched in the full run (engine `liftoff 28L` at 17:18:07.8); it
  shows as missed only when a checked window ends less than 120 s after it (the checker drops the last 120 s).
- **Bridges at rest inside parked aircraft** (`bridge.hit_at_rest`) and the retraction path through the fuselage: the
  rest pose and the animation are `js/live/gates.js` (aircraft workflow), which still parks the cab at
  `rc + parkDir * min(15, reach - 2)` and does not read the data's `stowW`. Request restated with numbers in
  `docs/requests/realtime_round1.md` ("Status 25 Sep"). The engine side (dock to the drawn pose, hold until retracted,
  MARS alternates) is done. The dock wait added here (20 s) keeps an arrival next to its retracted cab 20 s longer.
- **Pavement / stand spacing** (`offpave.*`, `clear.stand`): data of the static workflow (1L/1R crossing, north cargo
  apron; F6/F7 E75L pair 3.96–4.38 m at the stand poses against ICAO code C 4.5 m, G2/G5 B77W 7.08 m against 7.5 m).
- **Slow repositioning (`gnd.slide`)**: a parked body up to 3 m / 10° from a refined parked pose is towed at ≤ 0.5 m/s
  instead of being re-placed; kept by design (a fade for a 1 m correction would be more visible than the tow).
- **Display delay** stays adaptive 1–3 s (settles at 3 s on the public feeds): step 2 measured the fixed 1.5 s variant
  with 7.7× more ground jerk exceedances and worse position errors; lower latency needs a feeder account or own receiver
  (realtime_feeds.md §3).
