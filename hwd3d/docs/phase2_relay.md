# Phase 2 / P1: relay, replay packs and taxi graph

Written 2026-11-13 by the P1 package. The binding interfaces are in `docs/phase2_fork_map.md` §2.1–2.3. This document
covers how to run each part, the endpoints, the provider terms and rate limits (with sources), the D1 rules, the
recorder's 46-s holes, the taxi graph, and the test results. Section 8 lists every place where P1 deviates from the
fork map.

Files (P1):

| File | What it is |
|---|---|
| `hwd_live_server.py` | Relay. A fork of `sfo3d/sfo_live_server.py` @ a967f9b; the header lists what was kept, changed and dropped. |
| `tools/live/recio.py` | Reader for recorder files (`.jsonl.gz`, and the rec_pack's `.jsonl.xz`). |
| `tools/live/build_stream.py` | Offline twin of the relay stream: rec_pack hours go through the relay's own `Hub` on a simulated clock. |
| `tools/live/build_replay.py` (alias `build_pack.py`) | Replay-pack builder, writing to `out/replay/`. |
| `tools/live/replay_shim.js` | In-page fake relay. Copied to `out/replay/replay_shim.js` at build time. |
| `tools/live/rank_hours.py` | Ranks rec_pack hours by HWD activity (counts only), to choose pack windows. |
| `tools/live/build_taxigraph.py` | Taxi-graph builder: writes `data/hwd_taxigraph.{json,js}` and, with `--plot`, `out/phase2/taxigraph*.png`. |
| `tools/live/test_relay.py` | Offline unit tests of the relay. |
| `tools/live/relay_smoke.py` | End-to-end smoke test (spawns the relay in replay mode, or uses `--url`). |
| `tools/live/test_shim.mjs` | Headless Chromium test of the shim. |
| `tools/live/test_taxigraph.py` | Contract test of the taxi graph. |
| `data/hwd_taxigraph.{json,js}` | Taxi graph (committed; ODbL). |
| `out/replay/**` | Generated and gitignored, never committed: packs, metas, `packs.json`, the shim copy, the `wx/` METAR cache, `hours_rank.json`, and `.state/` (the quota log; never served). |

---

## 1. How to run

```bash
cd hwd3d
# live: adsb.lol inside its quota, plus adsb.fi (personal non-commercial, live only)
python3 hwd_live_server.py                         # http://localhost:8000/ -> live.html
python3 hwd_live_server.py --host 0.0.0.0          # open it from a phone on the same Wi-Fi: http://<pc-ip>:8000/
python3 hwd_live_server.py --no-adsbfi             # adsb.lol only
ADSBLOL_API_KEY=... python3 hwd_live_server.py --adsblol-daily 7200   # with a feeder key (sent as x-api-key, never logged)
python3 hwd_live_server.py --ident type-only       # D1-mask every aircraft (anything that may be shown publicly)
python3 hwd_live_server.py --record refs/cache/local/rec   # also record adsb.lol answers (never adsb.fi; holds identities)

# replay of the committed sfo3d recordings (adsb.lol, ODbL), re-timed to wall time, through the same merge path
python3 hwd_live_server.py --replay rec_pack --from 2026-11-08T20:00Z [--until ...] [--speed 1] [--loop] [--lookahead 60]
python3 hwd_live_server.py --replay refs/cache/local/rec   # a directory of --record / record.py hours

# replay packs for the relay-less app / phone artifact (out/replay/, gitignored)
python3 tools/live/build_replay.py                 # both presets, --ident type-only (default)
python3 tools/live/build_replay.py --pack weekday --ident full    # local use only
python3 tools/live/build_replay.py --from 2026-11-07T20:00Z --minutes 45 --name sat
python3 tools/live/rank_hours.py                   # activity per rec_pack hour -> out/replay/hours_rank.json

# taxi graph (deterministic: same inputs -> identical bytes)
python3 tools/live/build_taxigraph.py [--plot] [--crop NAME:X,Z,HW] [--show-pavement]

# tests (all offline except where stated)
python3 tools/live/test_relay.py
python3 tools/live/relay_smoke.py                  # spawns --replay rec_pack on a free port 8700-8799
python3 tools/live/relay_smoke.py --url http://127.0.0.1:8000 --secs 22   # an already running relay (live: uses the network)
node tools/live/test_shim.mjs [--pack out/replay/pack_weekday.json.gz]
python3 tools/live/test_taxigraph.py
```

Polling is shared by all clients and stops 60 s after the last client request (`IDLE_AFTER`). With `--record`, it
never stops.

## 2. Endpoints

The contract is `docs/phase2_fork_map.md` §2.1. The relay's header docstring repeats it.

| Endpoint | Answer |
|---|---|
| `GET /` | 302 to `live.html`, query kept. |
| `GET /api/ping` | `{hwdlive: 1, v, mode: live\|replay, stream, delta, history, dataNow, center {lat, lon, radius_nm}, poll {adsblol_s, adsbfi, adsbfi_s, quota}, features {metar: 'KHWD', taf: null, ident, ident_endpoint, d1: 'dbFlags & 12', d1_mode, replay: null\|{src, from, until, speed, loop, lookahead_s}}, providers, attribution}` |
| `GET /api/adsb` | readsb jv2: `{now, dataNow, seq, total, _source, msg, ac: [...]}`. |
| `GET /api/stream[?delta=1][&history=S]` | SSE. `retry: 2000`; `event: adsb` (full); with delta, `event: delta` `{now, dataNow, seq, ac, gone}`; a full event on every seq gap and at least every 30 s; `: keepalive` every 15 s. `history=S` (S ≤ 120) first sends the full payloads of the last S s, oldest first. |
| `GET /api/metar?ids=KHWD[&format=json]` | KHWD METARs of the last 3 h, newest first. Header `X-Data-Now`. Replay serves only reports at or before the replay time, else 502. Any other station returns 400. |
| `GET /api/ident?key=K` | Identity of an aircraft that is in the current picture or was within the last 10 min. Masked keys answer `{key, masked: true, t, desc, category}` only. Any other key returns 404, so this is not a registry look-up service. |
| `GET /api/status` | Provider health, quota, latency, 429s, merge and hygiene counters, ident loader state, masked count, replay position. No identities. |
| `/api/gates`, `/api/routeset`, `/api/taf` | 404 (removed). |

Static serving: the hwd3d tree. Never served: `refs/`, `tools/`, `node_modules/`, `jobs/`, dotfiles and dot
directories, `__pycache__`, `docs/qa/ref`, and all of `out/` except `out/replay/` (where the pack, the shim and `wx/`
live; `out/replay/.state/` is a dot directory). Directory listings are off. `POST` returns 404.

Record fields: readsb fields as the providers send them, minus `dst`/`dir`, plus `_pt` (position time, epoch s, relay
clock), `_src` / `_prov` (`lol` / `fi`), `_veh`, `_drop`, `_dbalt`, `_masked` and `_mx {r, t, d, op}` (Mictronics,
unmasked aircraft only).

## 3. Data sources, terms and rate limits

Checked 2026-11-13. Each source was fetched once and its sha256 recorded.

| Source | Quote | Where |
|---|---|---|
| **adsb.lol API** (primary) | "No key: **500 requests/day per IP**." "anonymous (30 days, no account): 500/day; adhoc (free, request form): 1,000/day; feeder (free, by feeding the network): 7,200/day, 20 GB/month …". "Over quota returns `429` with a `Retry-After` header. Unkeyed traffic is limited per IP; the daily window is a fixed 24h bucket, not midnight UTC." 429 body: "The window that tripped is named in the body (per-second, per-minute, per-hour or per-day for unkeyed traffic …)". `/v2/point/{lat}/{lon}/{radius}`: `x-quota: metered`, radius integer 0–250. Licence: "The license for the API as well as all data ADSB.lol makes public is ODbL." | `https://api.adsb.lol/api/openapi.json`, info.version 0.0.2, sha256 `b850e0b4…e0b3d3` |
| adsb.lol docs page | "no key: 500 requests/day per IP … over quota returns 429 with Retry-After; **the daily window resets at 00:00 UTC**." This contradicts the OpenAPI's "not midnight UTC". | `https://www.adsb.lol/docs/open-data/api`, sha256 `53f9eb0d…ee318` |
| adsb.lol, observed | The sfo3d recorder (4–11 Nov 2026, unkeyed) got a 429 after about 10 polls in 4,782 of 5,541 one-minute bursts, yet made 54,537 OK polls in 6.84 days (≈7,970 a day). So the 500/day limit was not enforced then, or is newer. sfo3d's research (`sfo3d/docs/research/realtime_feeds.md` row 1) quoted the same URL and info.version as "You can use the API for free …". A 200 answer carries no quota header. | `refs/cache/adsb/hwd_events.json` sampling; one probe 2026-11-13 |
| **adsb.fi open data** (optional, live only) | "The public endpoints are rate limited to 1 request per second". "Requests returning a 400, 401, 403, 404, or 429 status code count toward the limit." "adsb.fi open data is for personal, non-commercial use only. You may not license, sell, rent, or lease any part of the data or the service." "You must cite adsb.fi and include a link to our home page." | `github.com/adsbfi/opendata` README @ 9fe1c9a, sha256 `f7dfc426…d447b` |
| **readsb dbFlags** | "military = dbFlags & 1; interesting = dbFlags & 2; PIA = dbFlags & 4; LADD = dbFlags & 8;" | `github.com/wiedehopf/readsb` `README-json.md` @ dev 88877b9, sha256 `abb581d9…2b30` |
| **aviationweather.gov** (METAR) | "Set a custom user agent …"; "Wait between consecutive requests — maximum 100 requests per minute."; "The weather database currently allows access to up to the previous 30 days of data." `taf?ids=KHWD` returns `[]` (no KHWD TAF; fork map §2.1). | `https://aviationweather.gov/data/api/`, sha256 `0878d710…3a86`. US Government work, public domain. |
| **Mictronics aircraft database** (identity) | ODC-By 1.0. Local copy `refs/cache/local/registry/mictronics_lookup.json` (commit 479e4d0, 455,928 aircraft). Its `flags` field is military / interesting, not LADD/PIA (Phase 1 finding, relay header). | `docs/ATTRIBUTION.md`, `tools/registry/mictronics_db.py` |

How the relay stays inside these limits:
- **adsb.lol.**
  - One request in flight, at the HWD ARP, 8 NM.
  - The base period is 6.5–7.5 s (under the ~10 per minute that tripped the recorder).
  - A `Quota` object keeps the relay's own log of request times, persisted in `out/replay/.state/adsblol_quota.json`
    (times only). It caps the rolling 24 h at 475 (500 minus 5 % for other users of this IP). A rolling count ≤ cap
    keeps any fixed 24-h bucket ≤ cap, whether the bucket starts at midnight UTC or not, so both readings above are
    satisfied.
  - The period stretches to `horizon / remaining` (`--adsblol-horizon`, 3,600 s by default), so the remaining budget
    lasts about an hour of watching. With 475 left the period is 7.6 s. After 1 h of continuous watching it is about
    20 s, after 2 h about 56 s.
  - `Retry-After` is honoured in full, up to 24 h.
  - Each 429 raises an adaptive floor ×1.5; each success lowers it ×0.9.
  - Polling runs only while a client is connected (in `--record` mode adsb.lol keeps polling for the recording; adsb.fi
    still polls only while a client is connected - fix round 1).
  - The quota file is merged before every request and on every save (max of both logs, under a lock file with
    `O_EXCL`, stale after 10 s), so two relay processes on one machine share one budget (fix round 1;
    `test_two_processes_share_the_file`).
  - **What this means for a viewer (fix round 1, also in the About panel and the status pill).** The 475-request day
    lasts about 3 h of continuous watching. The first hour polls every 7-20 s, the second every 20-60 s, then the
    period grows to minutes and, once the rolling 24 h is spent, to about one request an hour until the oldest requests
    age out. Between slow polls aircraft are kept for the snapshot TTL and dead-reckoned; airborne tracks fade out after
    20 s without a report. With adsb.fi on (live, personal use) the picture stays fresh every 2 s regardless; a feeder
    key (`--adsblol-daily 7200`) keeps adsb.lol at the 6.5-7.5 s floor all day. The status pill shows the current poll
    period from `/api/ping`.
  - The snapshot TTL is max(45 s, 1.5 × the expected period + 5 s), so aircraft do not vanish between slow polls.
  - With a feeder key (`--adsblol-daily 7200`) the period stays at the 6.5–7.5 s floor.
- **adsb.fi.** Every 2.0 s, about 0.3 s after an even second (half the documented 1 request/s). Never recorded, never
  packed, never in a committed file. The relay shows its attribution while it is used.
- **METAR.**
  - One upstream JSON request serves both formats.
  - TTL is 60 s from hh:56 to hh:01 and 300 s otherwise, with conditional requests.
  - KHWD routine METARs are at **hh:54**: 215 of 215 routine reports from 4–13 Nov 2026, plus 40 SPECIs. They reach the
    API 4.08 / 4.21 / 4.37 min later (p10 / p50 / p90 of `receiptTime − obsTime`, one AWC request on 13 Nov). The
    fork map's "[verify] :54" is confirmed.
  - Replay serves cached reports from `out/replay/wx/`, or makes one targeted request per hour slot within AWC's
    30-day window.
- **User-Agent:** `hwd-live-3d-relay/0.1 (personal non-commercial visualisation; python-stdlib)`. It carries no name and
  no repository URL.

## 4. D1 and identity

- **Rule.** A record is masked when `dbFlags & 4` (PIA) or `dbFlags & 8` (LADD), per the readsb quote in §3.
  - The flag is OR-ed over every provider record of the aircraft.
  - It is sticky for the relay process: once seen, the aircraft stays masked until restart.
  - Military (`& 1`) and interesting (`& 2`) do not mask.
  - The Mictronics `flags` field is not used.
- **What masking does.** It is the last merge step.
  - Removes `flight`, `r`, `ownOp`, `year`, `squawk`, `dbFlags`, `_mx` and `_dbalt`.
  - Keeps `t`, `desc`, `category`, `emergency` and the kinematics.
  - Sets `hex` to `x` + 8 hex characters of HMAC-SHA256(per-process random salt, hex). The salt is never written.
  - Sets `_masked` to `'d1'` (flagged LADD / PIA) or `'type-only'` (the relay or pack masks everyone); the UI says
    "Identity withheld · LADD / PIA" only for `'d1'` and "Identity not shown in this recording" for `'type-only'` (fix
    round 1: every type-only track used to claim LADD / PIA enrolment).
- **Late flag (fix round 1).** In `--ident full` an aircraft is published under its real key until some provider's record
  carries the flag (the two providers' databases can disagree; adsb.fi v3 does carry `dbFlags`: one request on
  2026-11-13, 2 of 78 records). When `D1.newly` gains a key, the Hub drops its `/api/ident` entry, removes every
  `?history` payload that holds it, counts `d1_late_flag`, and sends `event: forget` (`{"forget": [keys], "seq"}`) on the
  open SSE streams only - never in the full snapshot or the history, so a client that never saw the key does not learn
  it. `feed.js StreamFeed onForget` -> `traffic.forget(keys)` drops the track and its identity at once.
  `test_late_flag_purges_ident_history_and_tells_clients` covers it.
- **Late flag, fix round 2.** The SSE-only path missed two cases. A client that polls `/api/adsb` because its stream
  failed never heard the forget. And only the last forget event was kept, so a stream that missed two merges saw one.
  - The Hub now keeps every forget event for 10 min (`forget_evs`: seq, wall time, and for each key the seq at which it
    was first published).
  - `/api/adsb?since=<seq>` adds `"forget": [keys]` to the snapshot, for every event after `since` whose key had been
    published to the client by then (first seq ≤ since). A client that never saw the key still does not learn it.
  - The SSE loop sends every pending event since the client's last seq.
  - `feed.js` polls with `?since=` once it knows a seq, and `traffic.forget` marks the track `maskWhy: 'd1'`.
  - Covered by `test_forget_reaches_pollers_and_every_pending_event`: two late flags, one poller, one stream, and a
    flag before publication. Against the spawned replay relay, `api/adsb?since=<seq>` and a malformed `since` both
    answer the snapshot (200), with 0 console errors.
- **`--record` guard, fix round 2.** The fix-round-1 rule lower-cased the path. On a case-sensitive file system that
  let `Refs/Cache/Local/rec` (not gitignored) through.
  - `record_dir_check` now resolves the real path and compares it case-sensitively: inside hwd3d only
    `refs/cache/local/…` or `out/…` (not `out/replay/…`).
  - It then asks git: `git check-ignore -q --no-index` on a would-be recording file must say the path is ignored. Outside
    any work tree the directory is allowed; without git only the path rule applies.
  - Covered by `test_record_dir_case_sensitive_and_git_ignored`, which refuses `Refs/Cache/Local/rec`, `OUT/REPLAY/rec`,
    `Out/rec`, `out/replay/rec`, `out/Replay/rec`, `tools/rec`, `refs/cache/adsb/rec` and `../hwd_rec_probe`. A CLI
    probe with `--record Refs/Cache/Local/rec` exits 1 and creates nothing.
- **`--ident type-only`** masks every aircraft, including `~` (non-ICAO) addresses.
- **`/api/ident`** answers type only for masked keys, and 404 for keys not in the picture.
- **Packs.** `build_replay.py` defaults to `type-only`, for anything that may be distributed (fork map §2.2, risk R11).
  - A leak check walks every string of the written pack against the window's original hex addresses, registrations,
    callsigns, operators and Mictronics registrations. It reports counts only. A pack that fails is deleted.
  - `--ident full` (local use only) checks that none of the flagged aircraft's identities appear.
- **Committed outputs.** No committed P1 file holds a per-aircraft identity:
  - packs, recordings, `wx/` and `hours_rank.json` live in gitignored `out/`;
  - `data/hwd_taxigraph.*` holds only aggregated spot positions. `test_taxigraph.py` checks that no hex,
    registration or callsign field appears.

## 5. Replay and the recorder's 46-s holes

**What the recordings are.**
- `sfo3d/refs/cache/rec_pack/adsblol_*.jsonl.xz` @ a967f9b: adsb.lol `/v2/point` answers around SFO, trimmed to 25 NM
  and 18,000 ft (111 hours, 4 Nov 17Z – 11 Nov 13Z 2026; 10 hours have no OK poll).
- HWD is 12.3 NM from SFO, so any window of 12.7 NM or less around HWD lies inside the trim.
- The recorder polled about every 1.3 s until refused (HTTP 429) after about 10 polls, then waited for the next minute.
  So only about 14 s of each minute is observed, followed by a hole of about 46 s (at most 52.4 s in the pack windows).

**Relay replay (`--replay`).**
- Hours are streamed in time order through the same `Hub` and re-timed to wall time.
- `dataNow` is the recording time, used by the Sun, lights and METAR clock.
- Each answer is cut to the relay radius.
- The snapshot TTL is 75 s (`REPLAY_SNAP_TTL`, divided by `--speed`), so aircraft persist through a hole: their records
  simply stop changing.
- `features.replay.lookahead_s` defaults to 60.

**Packs (`hwd-pack/1`, fork map §2.2).**
- Each event lists every aircraft present; an absent key is gone. `d` holds per-aircraft field deltas.
- The header also has `filter`, `d1`, `sampling`, `holes_note`, `attribution`, `center` and `metar` (the window's KHWD
  reports from aviationweather.gov, cached in `out/replay/wx/`).
- `pack.json.gz` is the default (weekend). `packs.json` indexes all packs.

| Pack | Window | Events | Keys | Masked (flagged) | gz / JSON | OK polls / 429 | Gap p50 / p90 / max | Gaps > 30 s / > 55 s | Aircraft per poll (median / max) |
|---|---|---|---|---|---|---|---|---|---|
| weekend (default) | Sun 8 Nov 20:00–21:00Z (12–13 PST) | 592 | 142 | 142 (8) | 0.26 / 1.5 MB | 593 / 60 | 1.3 / 46.1 / 52.4 s | 60 / 0 | 24 / 31 |
| weekday | Mon 9 Nov 21:00–22:00Z (13–14 PST) | 590 | 111 | 111 (7) | 0.20 / 1.2 MB | 592 / 60 | 1.3 / 3.6 / 51.1 s | 59 / 0 | 20 / 30 |

Leak check: weekend 0 of 378 original identity strings found; weekday 0 of 288. Each pack has 5 KHWD METARs. The
filter is 8 NM and 5,000 ft MSL, or on the ground.

**Window choice** (`tools/live/rank_hours.py`, counts only).
- Definitions:
  - **ground**: distinct aircraft reporting `ground` within 1.5 km of the ARP;
  - **transitions**: ground → airborne changes within 2.5 km, seen between consecutive fixes (the holes hide some);
  - **area**: distinct aircraft within 8 NM at ≤ 5,000 ft or on the ground.
- Sun 8 Nov 20Z has the most aircraft on the ground (26) and in the area (142) of any hour, with 14 transitions. Sat 7
  Nov 20Z (22 / 125 / 19) is a close second.
- Mon 9 Nov 21Z has 18 transitions (pattern work), second among weekday hours after Wed 4 Nov 23Z (19). It has 15 on
  the ground and 111 in the area.
- **Every hour of the recording is west flow** (PLAN §3). No east-flow window exists yet.

**How the app must handle the holes** (binding for P3/P4):
- **Do not dead-reckon across a hole.** At 70 kt an aircraft covers about 1.7 km in 46 s, a whole pattern leg.
- **Display `lookahead_s` (60 s) behind the stream head.** Every hole of 55 s or less then lies between two real
  fixes. Interpolate them: Hermite in the air, along `data/hwd_taxigraph.json` on the ground.
- **At start-up**, both the relay (`/api/stream?history=60`) and the shim send the last `lookahead_s` + 5 s of payloads
  at once, so the first frame does not wait 60 s. During the first minute the display time can still precede an
  aircraft's first fix; hold that first fix.
- **Live mode (polled every 7–60 s)** benefits from the same delay. With adsb.fi on (every 2 s), a smaller delay
  suffices.

**The shim** (`out/replay/replay_shim.js`, an ES module).
- Call `installReplay({url, loop})` before `detectRelay()`.
- It patches `fetch` for `api/ping|adsb|metar|ident|status` (other `api/*` → 404) and `EventSource` for `api/stream`.
- `now` and `_pt` are shifted to wall time; `dataNow` keeps the recording clock.
- The replay clock starts `lookahead_s` into the window.
- A new stream first gets the last `lookahead_s` + 5 s of payloads. Live payloads that arrive meanwhile are queued
  behind them.
- METAR is filtered to the replay time.
- Soft loop: one empty payload (`msg: 'replay restarts'`), then the window again, with `seq` still increasing.
- Gzip is detected by its magic bytes.

## 6. Taxi graph (`data/hwd_taxigraph.{json,js}`, `hwd-taxigraph/1`)

**Contract.** Fork map §2.3. It is a superset of sfo3d's: `edges`, `ways[].kind`, `halfWidth` and `aprons` keep
`TaxiNet` working.

**Additions beyond the map:**
- `hangars[]` (access sides);
- `inputs` (sha256 of all three inputs);
- `rules` (every constant);
- per-connector `mode` (`straight` | `dogleg` | `air`), `naip_m`, `clear_m`;
- node kinds `runway_edge` (a taxi line crossing a runway outline) and `hangar`;
- link flag `air: true`;
- way `conn:island` / `conn:air`, with `air_only` on the latter.

**Inputs.** Rules and constants are in the builder header.
- `data/hwd_airport.json`.
- The Phase 1 OSM pin `refs/cache/osm/overpass_khwd_at_20261112T000000Z.json`. Only three things are read from it: the
  aerodrome boundary, the 9 `amenity=parking` areas and the 7 `barrier=fence` ways.
- NAIP 2024 (`refs/cache/naip/naip_2024_hwd_rgb.jpg`, through `tools/imagery/paintline.Naip`), for the Phase 1 grey
  test.

**Why the extra inputs.** On the first build, using `hwd_airport.json` alone, the graph had 4 components and 25
unreachable spots:
- OSM digitised three taxilane groups without a join: the helipads west of the Green Ramp, and two groups on the east
  ramp;
- OSM aprons stop short of hangar fronts and of the taxiway edge (by up to about 13 m);
- two helicopter spots are on an isolated pad south of 10R/28L.

**Pavement rule for connectors.**
- **Pavement.** OSM aprons, taxi lines (width / 2 + 0.5 m) and helipads, minus car parks.
- **NAIP grey.** Accepted only inside the aerodrome boundary and outside car parks, and for at most 15 m per connector.
  A longer stretch is used only when it is the element's only way in, and is then flagged `naip_long` (none at
  present).
- **Rejected legs.** A leg is rejected if it:
  - crosses more than 6 m of NAIP non-grey (measured: paint, aircraft and shadows make runs of 5 m or less, while grass
    inside an OSM apron polygon made a 22-m run);
  - crosses a fence;
  - enters a runway outline;
  - passes within 1.0 m of a building or hangar.

**Results** (2026-11-13, input sha256: airport `554d1e9f…`, OSM `fc792197…`, NAIP `e646ef8e…`):

| Item | Value |
|---|---|
| Ways | 147: 61 taxiways, 78 taxilanes, 2 runways, 6 connector ways |
| Nodes, links, edges | 742 nodes, 841 links, 2,270 edges (≤ 50 m) |
| Node kinds | junction 384, spot 161, hangar 67, runway 33, end 32, runway_edge 31, hold 18, helipad 16 |
| Components | **1** |
| Spots | **177 / 177 connected and reachable from both runways** (fixed-wing over pavement links only; helicopter spots may use air links) |
| Helipads | 9 / 9 |
| Hangars | 34 / 34 with at least one reachable side (67 of 76 sides tried) |
| Holds | 18 / 18 attached and reachable |
| Connector modes | 248 straight, 3 dog-leg (RE048N669 behind a hangar, two hangar sides), 2 air (PW049S181, PW072S220 on the isolated pad) |
| Spot connector length | p50 9.8 m, p90 51.0 m, max 117.3 m |
| NAIP-only bridging | 22 legs, 208.7 m in total |
| Islands joined | 8.1 m, 11.7 m and 19.1 m |
| Junction vertices shared by ≥ 2 open ways | 165 (167 counting closed ways). Phase 1's "166 shared + 1 fork" counts all ways (fork map §2.3 reconciliation). |
| Crossings noded / gaps joined / dead ends | 1 / 1 / 32 |
| Lengths | taxiway 9,490 m, taxilane 6,316 m, runway 2,683 m, connector 5,780 m. 55 taxi links lie inside a runway outline. |
| Wingspan limits | A1 30.48 m (100 ft), Z1 28.65 m (94 ft) |
| Sanity checks | Links through buildings 0; taxi links crossing fences 0 |
| Determinism | Two builds give byte-identical `.json` and `.js` |

**Plots.** `out/phase2/taxigraph.png` (whole field over NAIP 2024, UTM north up) and the close-ups `_west`, `_east`,
`_centre`, `_south`, `_helipads_w`, `_ramp_e`, `_heli_s`, `_ne_fbo`. I looked at each one. What they show:
- the tie-down rows of the Green Ramp, each spot on a short connector to its row lane;
- the hangar rows with side connectors;
- the three islands joined over pavement;
- the air links on the south pad drawn dashed;
- no connector over grass, buildings or car parks.

The helicopter spot PE114N224 (3 ADS-B sessions) joins along the paved band at the edge of a grass strip: grey test
saturation 0.11–0.14 against a threshold of 0.16.

## 7. Test results (2026-11-13)

| Test | Result |
|---|---|
| `test_relay.py` | 18 / 18 OK. Covers merge, hygiene, D1 (LADD/PIA masked, military not, sticky, flag from either provider, type-only), Mictronics fill, ident subset, Quota (rolling cap, period, persistence, Retry-After in full), snapshot TTL, serving rules (incl. `__pycache__`), window filter, METAR replay cache, xz reader. |
| `relay_smoke.py` (replay rec_pack 8 Nov 20Z, ×4, 40 s) | PASS, 33 / 33 checks. 30 events (2 full + 28 delta). Median 24 aircraft per event; no event emptied the picture. Delta reconstruction equalled `/api/adsb` at 19 / 19 sampled seqs. 29 records inside 8 NM; 3 masked, all `x`+8 hex with no identity field. `?history=60` sent 33 payloads at once. ident masked → type only; unknown key 404. METAR 4 reports, none after the replay time. Removed endpoints 404; deny rules 404; pack 200. |
| `relay_smoke.py --url` against a **live** relay (22 s) | PASS. adsb.lol 5 / 5 OK, p50 latency 193 ms, period 7.7 s, quota 466 of 475 left. adsb.fi 19 / 19 OK, p50 150 ms, every 2.0 s. 4 aircraft at 03:30 PST. Mictronics ready (455,928). Live METAR newest `METAR KHWD 131054Z AUTO …`. |
| `test_shim.mjs` (Chromium, weekend and weekday packs) | PASS on both. `installReplay` 44 ms. First stream payload 45 ms after load, carrying every pack event of the first 60 s at once (11 for weekday). Head `now` is wall time; `now − dataNow` is constant. Display time (head − 60 s) is bracketed by real fixes for 24 / 25 (weekend) and 18 / 19 (weekday) aircraft. All keys `x`+8 hex with no identity field. Soft loop on a 12-s synthetic pack: restart, traffic again, seq increasing. |
| `test_taxigraph.py` | 9 / 9 OK. Covers format and licence header, `.js` = `.json`, link ends on nodes, lengths, no air links in `edges`, ways = open OSM ways, closed = closed ways, A1/Z1 spans, one component, all spots, helipads and hangars reachable from both runways, holds within 15 m of their bar, runway links inside outlines, connectors clear of buildings and fences, no identity strings. |
| `build_replay.py` | Both packs built in 5.7 s; leak check OK (0 found). |

Network use by these tests on 2026-11-13: adsb.lol 5 relay requests plus 1 OpenAPI fetch; adsb.fi 19; aviationweather.gov
2 (the live smoke test and one 9-day METAR history). The earlier interrupted run of this package made 4 adsb.lol
requests (in the quota log).

## 8. Deviations from the fork map, open items, requests

**Deviations** (for the orchestrator):
1. **`/api/ident` exists.** The workflow brief asks for an identity endpoint backed by Mictronics. The map (§2.1) said
   no endpoint. It answers only for keys in the current picture (10 min) and never with identity for masked keys.
   Inline `_mx` is kept as the map specifies.
2. **Pack builder name.** It is `tools/live/build_replay.py` (brief), with `build_pack.py` as an alias (map). Its
   outputs are the map's: `out/replay/pack.json.gz`, `pack_meta.json`, `replay_shim.js`. Defaults differ from the map
   example: radius 8 NM (the relay's) rather than 6, and ceiling 5,000 ft MSL rather than 4,000.
3. **Taxi-graph inputs.** The graph also reads the OSM pin and NAIP 2024 (§6), and has the extra fields and node kinds
   listed in §6.
4. **adsb.lol cadence.** It is not a flat 6 s but a budget of 475 per rolling 24 h stretched over `--adsblol-horizon`
   (§3), because the published unkeyed quota is 500/day.

**Open items, not verified:**
- Whether adsb.lol enforces 500/day per IP today. The docs say so; the recorder's week did not hit it. The relay is
  conservative either way.
- Which of the two daily-window statements of adsb.lol is right (fixed 24-h bucket, or 00:00 UTC reset). The rolling
  cap satisfies both.
- Whether a 429 counts against the adsb.lol quota (the relay counts it).
- Hangar door sides are unknown (NAIP shows no doors). Access uses both long sides [inf].
- The NAIP grey test cannot tell an unmapped landside car park from an apron when OSM has no `amenity=parking` there.
  The 15-m cap limits the effect.
- No east-flow replay window exists in the recordings.
- Pack METARs come from AWC's 30-day look-back. After about 8 Dec 2026, a rebuild of these windows will find no METAR
  unless `out/replay/wx/` is kept. The archive alternative (e.g. Iowa Environmental Mesonet) and its terms were not
  checked.

**Request for sfo3d** (to be moved to `docs/requests_to_sfo3d.md` by the orchestrator, which owns that file): sfo3d's
relay polls adsb.lol about every 1.0–1.5 s unkeyed. Since at least 2026-11-13, adsb.lol's OpenAPI (0.0.2) publishes
"No key: 500 requests/day per IP". sfo3d could adopt this relay's `Quota` scheduler, or a feeder key.
