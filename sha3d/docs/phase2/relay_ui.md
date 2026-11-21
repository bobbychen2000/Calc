# Phase 2e: relay, modes, UI shell, About

Date: 2026-11-20. Package P2e of Phase 2 (docs/PLAN.md §7: "Write `sha_live_server.py` within current terms", "Build
the Observed/Inferred layer"). Fork base: sfo3d @ **e3218d6**, plain WebGL2 `live.html` path (working default Q7).
Nothing in `sfo3d/`, `pc12/` or `hwd3d/` was modified; nothing was committed.

A previous attempt was interrupted on 2026-11-14. `git diff 8ca06f7` showed no edits to this package's files from it
(`relay.js`, `about.js`, `entry.js`, `ui.js` were still the core's), so the package was done from the core commit.

Tags: **obs** (seen in a source or measured), **inf** (inferred: a rule, default or placeholder).

## 1. Result

| Item | State |
|---|---|
| `sha_live_server.py` (stdlib relay) | done: `/api/ping {shalive: 1}`, `/api/metar?ids=ZSSS` and `/api/taf` (aviationweather.gov, raw text kept, at most one upstream request per 10 min each, cached), `/api/adsb` (adsb.lol, **off unless `--adsb`**, at most one request per 180 s, a 24 h cap that survives restarts, only `adsb_icao` records, each labelled `src: 'obs'`), `/api/status`; generic User-Agent; no OpenSky, no adsb.fi; static allow-list. Unit test: 7 tests pass against a local mock. Smoke test against the real AWC API passed. |
| METAR decoding for ZSSS | done: `js/env/wx/metar_zsss.js`, the JS twin of `tools/wx/metar_zsss.py`. It decodes the raw text in the report units (m/s, metres, hPa) and keeps the trend apart. It equals the Python reference on 1,675 + 69,104 reports. |
| Runway-in-use rule | done: the tail-wind rule, with the parameter-free "into the wind" fallback switchable in Settings. Reproduces 146/169 and 136/169 (sources_sim.md §5.2). Exposed for Phase 3 as `SHA.runwayMode()`, the `sha:runway` event and the module exports. |
| Modes | done: `live` (a relay answers), `snapshot` (static, no network: recorded METARs and a TAF from `data/sha_snapshot.js`, empty traffic set), `auto` = live if the relay answers, else snapshot. A requested relay that does not answer gives the snapshot and a red "Relay offline" pill. |
| UI shell | done: phone portrait bottom sheet and laptop side panel (from sfo3d `ui.js`); status pill by mode; weather and runway lines; the Observed / Inferred legend; stand labels, stand card and stand search; Settings with the runway rule; an About panel with every notice. No ATC audio toggle (Q4). |
| Renders | `docs/phase2/ui_phone_*.png` (iPhone 15 emulation, 393 × 659, deviceScaleFactor 1) and `ui_laptop_*.png` (1440 × 900), §9. I looked at all of them. |

## 2. File map

| File | Status | What |
|---|---|---|
| `sha_live_server.py` | **new**, forked from sfo3d@e3218d6 `sfo_live_server.py` (design and helpers) | the relay (§3) |
| `tools/live/test_relay.py` | **new** | unit test with a local mock of AWC and adsb.lol (§3.5) |
| `tools/live/build_snapshot.py` | **new** | builds `data/sha_snapshot.js/.json` from a cached AWC download (§5.2) |
| `data/sha_snapshot.js`, `.json` | **new**, generated | the snapshot mode's recorded weather (window.SHA_SNAPSHOT) |
| `js/env/wx/metar_zsss.js` | **new** | ZSSS decoder, runway rules, `runwayMode()`, `assignRunways()`, `windText()` (§4) |
| `tools/wx/test_metar_zsss_js.mjs` | **new** | JS vs Python on every report; agreement figures (§4.3) |
| `js/live/shell.js` | **new** | the UI shell extension `shell` (order 90): status, weather and runway lines, legend, stand labels and card, relay TAF / ADS-B polls, QA hooks (§6) |
| `js/live/relay.js` | rewritten (this package's file) | relay client: detection state, METAR / TAF / ADS-B fetches |
| `js/live/about.js` | rewritten (this package's file) | About panel with every notice, the mode line, the credit line (§6.6) |
| `js/live/entry.js` | adapted | modes, snapshot injection, imports `shell.js` |
| `js/live/ui.js` | adapted | legend box, stand labels and card, stand rows in the search, Settings runway rule, popover close buttons |
| `js/live/app.js` | small edits (core file) | `hooks.status`, the snapshot instant into `AppEnv`, `app.cfg` / `app.mode` / `app.hooks`; the core's `?legend=1` line removed (the shell owns the legend) |
| `js/env/presets.js` | small edit (core file) | `setSnapshotWx()`: the snapshot reports are injected rather than imported; `export let` bindings |
| `js/env/wx/metar.js` | one-line addition (core file) | `metarSummary()` also returns `qnhHpa` and `trend` (core open issue 8) |
| `live.html` | one line | loads `data/sha_snapshot.js` |
| `live.css` | adapted | legend box, stand labels, stand rows and card, About lead and close button, phone sheet sizes; the core's `#legend` slot rules replaced |
| `livetest.mjs` | small edit (core harness) | `DEVICE='iPhone 15'` (Playwright descriptor, deviceScaleFactor 1); the mock relay also answers `/api/taf` and, with `MOCK_ADSB=1`, `/api/adsb` |
| `jobs/ui.mjs` | **new** | UI renders and checks (§9) |

## 3. The relay (`sha_live_server.py`)

```
python3 sha_live_server.py [--port 8000] [--host 127.0.0.1]      -> http://localhost:8000/ (302 to /sha3d/live.html?relay=1)
python3 sha_live_server.py --adsb [--adsb-radius-nm 60] [--adsb-daily-max 200]
python3 sha_live_server.py --no-metar                              (never contacts aviationweather.gov)
```

### 3.1 What was kept from sfo3d and what was removed

- **Kept (design):**
  - the one-off urllib client with a fixed User-Agent (it honours HTTPS_PROXY / NO_PROXY);
  - the METAR upstream cache with conditional requests;
  - the gzip static cache, the deny-by-default static rules and no directory listings;
  - the handler shape;
  - the `/api/ping` contract the app detects.
- **Removed:**
  - the SFO ARP and the 40 NM radius;
  - the FAA registry;
  - the flysfo gate plan (`/api/gates`);
  - the KSFO METAR / TAF schedule;
  - the adsb.fi poller (its terms forbid relicensing; not even optional);
  - OpenSky (never called);
  - the SSE stream and multi-provider merge (one provider, at most one request per 180 s: polling `/api/adsb` is enough);
  - the SFO replay and the route lookups;
  - the `live3.html` redirect;
  - the owner's repository URL in the User-Agent.

### 3.2 Endpoints and limits

| Endpoint | Upstream | Limit | Notes |
|---|---|---|---|
| `/api/ping` | none | – | `{shalive: 1, v, mode: 'live', dataNow, features: {metar, taf, adsb, replay: null}, adsb_min_interval_s, wx_min_interval_s, providers, attribution, ua}` |
| `/api/metar?ids=ZSSS[&format=json]` | `aviationweather.gov/api/data/metar?ids=ZSSS&format=json&hours=12` | **one request per 10 min**; conditional `If-None-Match` / `If-Modified-Since`; after an error the last good list is kept and the next attempt again waits 10 min | JSON keeps only `{icaoId, metarType, obsTime, reportTime, receiptTime, rawOb}`, newest first. The lossy AWC weather fields are **dropped**: `wspd` is knots rounded from MPS, `visib` is "6+" for 9999, `wdir` is "VRB" (sources_sim.md §3.3), so nothing downstream can use them. `format=raw` gives the raw lines. Only ZSSS is relayed (400 otherwise: no open proxy). Headers `X-Wx-Fetched`, `X-Wx-Upstream-Error`. |
| `/api/taf?ids=ZSSS[&format=json]` | `.../taf?ids=ZSSS&format=json` | one request per 10 min | `{icaoId, issueTime, bulletinTime, validTimeFrom, validTimeTo, rawTAF}` |
| `/api/adsb` | `api.adsb.lol/v2/point/31.1978/121.3363/60` | **OFF unless `--adsb`.** Opportunistic: a request happens only inside a client's call, when the last one is at least 180 s old. The 180 s floor cannot be lowered (`--adsb-interval 30` becomes 180). After a 429 or an error the interval doubles up to 1 h, and Retry-After is honoured. At most `--adsb-daily-max` (default **200** of the 500 keyless per day) in any 24 h, counted in `out/relay/.state/` so a restart cannot reset it. | Only `type: 'adsb_icao'` records are relayed, each with `src: 'obs'`, `_src: 'adsb.lol'` and `_pt` (absolute position time). Every other type (mlat, tisb_*, adsr_*, other, mode_s ...) is dropped and only counted in `excluded`. `dst` / `rssi` are dropped. Off: `{enabled: false, ac: []}`, and nothing is sent upstream. |
| `/api/status` | none | – | cache ages, request counts, last codes and errors, quota use, UA |

All endpoints are also under `/sha3d/api/...`, where the page's relative `api/...` URLs land.

**User-Agent:** `sha-live-3d-relay/0.1 (personal non-commercial visualisation; python-stdlib)`. It carries no names, no
e-mail and no repository URL. aviationweather.gov asks for a custom UA; this one is honest and generic (the hwd3d
pattern).

**Attribution strings** (in `/api/ping` and the About panel):
- `metar`: "Weather: NOAA/NWS Aviation Weather Center (https://aviationweather.gov) data; the ZSSS reports are issued by
  the CAAC aviation meteorological service. Not official NOAA material."
- `adsb`: "... contains information from ADSB.lol (https://adsb.lol), made available under the Open Database License
  (ODbL 1.0 ...). Only ADS-B (adsb_icao) records are shown as observed."

### 3.3 Static files

The relay serves the **repository root**, so that the app's `../sfo3d/data/models/` resolves. It uses an allow-list:
- `sha3d/live.html`, `sha3d/live.css`, `sha3d/js/**`, `sha3d/data/**`;
- `sfo3d/data/models/**`, `sfo3d/data/liveries/**` (the aircraft models are loaded by URL, not copied).

Everything else is 404:
- `refs/` (third-party caches), `tools/`, `docs/`, `out/`, `jobs/`;
- the relay source, the other projects, `.git`, dot files and `..` paths;
- directory listings.

### 3.4 Real-world smoke test (2026-11-20 22:29Z)

`/api/metar` got 24 ZSSS reports (newest `METAR ZSSS 202200Z VRB01MPS CAVOK 06/00 Q1028 NOSIG`) and `/api/taf` got
`TAF ZSSS 201510Z 2018/2124 32004MPS 8000 SCT030 ...`. That was one upstream request each; repeated calls were served
from the cache.

### 3.5 Unit test

`python3 -I sha3d/tools/live/test_relay.py` runs in 1.5 s, **7/7 pass**. It starts the relay as a subprocess on a free port
against a local mock of the AWC and adsb.lol APIs; nothing leaves the machine. It checks:
- `/api/ping` (`shalive` 1, features, attribution, UA format), also under `/sha3d/api/`;
- the mocked METARs come back newest first with the raw text, without `wspd` / `visib` / `clouds`;
- `format=raw` gives the raw lines;
- **one upstream METAR request for five client calls**, and one for the TAF;
- other stations are refused (400) and do not reach the upstream;
- `/api/adsb` off by default, with **no upstream request**;
- with `--adsb`:
  - only the `adsb_icao` record is relayed, labelled obs;
  - mlat / other / tisb_icao are counted in `excluded`;
  - `--adsb-interval 30` is raised to 180;
  - three more calls inside 180 s cause no further upstream request;
  - after a restart on the same state directory the quota log still blocks a new request;
- every upstream request carries the generic UA, without "github", "@", URLs or "contact";
- the static allow-list, the deny cases (including `%2e%2e`) and the `/` redirect with the query kept.

## 4. METAR decoding and the runway-in-use rule

### 4.1 Decoder (`js/env/wx/metar_zsss.js`)

The core already cut the trend in `js/env/wx/metar.js`, which the renderer's EnvState uses. That decoder converts the
wind to knots rounded to 0.1, so 1 MPS becomes 1.9 kt, which is 0.977 m/s back. That shifts the runway rule's 1.5 / 4.0 m/s
thresholds. The new module is a line-by-line twin of `tools/wx/metar_zsss.py`:
- it decodes the **raw text**, never the AWC JSON fields;
- it keeps the units as reported: `speed_ms`, `gust_ms` (and `speed_kt`), `vis_m` (9999 → 10,000 with `vis_ge`), `qnh_hpa`;
- it decodes `trend[]` (NOSIG, or BECMG / TEMPO with FM / TL / AT and their own elements) **apart from the
  observation**. A BECMG or TEMPO group is never drawn as the current sky; the env stack uses metar.js, which also cuts
  the trend.

The UI's weather line and clock use this decoder. Example: `METAR 0400Z (observed): 330° 6 m/s · CAVOK · Q1027 ·
13/-5 °C · trend NOSIG not applied`.

### 4.2 Runway rule

- `RunwayDirection` [inf] (default): keep the current direction while its tail wind, gusts included, is ≤ 1.5 m/s. Turn
  after two consecutive reports above 1.5 m/s, or one above 4.0 m/s. Calm or VRB keeps the direction.
- `RunwayDirectionIntoWind` [inf] (fallback): the direction with a head wind; |headwind| < 0.5 m/s keeps the current one.
- `runwayMode(reports, {rule, start, tMs, closed})` steps the rule over every report at or before `tMs`, in time order,
  as a live simulator sees them. It returns `{dir, flow, arr, dep, notes, rule, ruleLabel, reason, report, history,
  tag: 'inf'}`.
- `assignRunways(dir, tMs, closed)` maps the direction to the AIP (mirror) AD 2.20 2.1.1 segregated mode: 18L/36R
  arrivals, 18R/36L departures. With 18L/36R closed:
  - by day, a single-runway operation on 18R/36L [inf];
  - from 1600 to 2300 UTC, no landings, per AD 2.20 2.1.6.

  NOTAMs themselves are applied by the traffic phase (sources_sim.md §4); `closed` is the hook.

### 4.3 Check against the Python reference

`node sha3d/tools/wx/test_metar_zsss_js.mjs` (6 s):
```
decode: 1675 reports (examples 9, snapshot + AWC 30 d 1666) compared with metar_zsss.py
IEM: 69104 reports; decode differences 0; rule directions equal to Python after every report
hints 169: tail-wind rule 146/169 = 86.4 %, into the wind 136/169 = 80.5 %
all passed
```
The agreement figures equal sources_sim.md §5.2. The IEM and AWC 30-day files are local (`refs/cache/metar/`). Without
them the test still runs on the 9 built-in examples (MPS / KT / A-group / CAVOK / RVR / WS / trend / missing groups) and
the 11 snapshot reports, and skips the archive part.

## 5. Modes

### 5.1 `js/live/entry.js`

`?mode=` or `window.SHA_MODE`, default `auto`:

| Mode | When | Time | Weather | Traffic | Status pill |
|---|---|---|---|---|---|
| `live` | a relay answers `/api/ping {shalive: 1}` (`?relay=1`; the relay's `/` adds it) | wall clock | relay METAR (polled every 60 s; the relay asks AWC at most every 10 min) and TAF (every 15 min) | none yet. Observed ADS-B only with `--adsb`: `SHA.observed`, count in the pill | green "Live weather · METAR 2200Z" |
| `snapshot` | no relay (or `?mode=snapshot`) | the snapshot instant (`?t=` still overrides the environment time) | the recorded METARs and the TAF in force at that instant | the snapshot's set: **empty** (`traffic.kind: 'empty'`). Phase 3 puts a replay set of simulated, inferred traffic there | purple "Snapshot · 20 Nov" |
| (relay requested, absent) | `?relay=1`, but no answer | as snapshot | as snapshot | as snapshot | red "Relay offline", the reason in the tooltip and the About mode line |
| `live` without a relay | `?mode=live` | wall clock | none (clear default) | none | grey "Static scene · no relay" (the core's Phase 2 behaviour, kept for QA) |

### 5.2 The snapshot data

`python3 -I tools/live/build_snapshot.py --fetch` was run once on 2026-11-20. It made 3 requests to
aviationweather.gov: the METARs of the last 24 h, the current TAF, and the TAF issued last before the snapshot instant
(`time=issue&date=20261120_0415`). A first run had asked `date=<now>` and got only the current TAF, so it was re-run.
The files are in `refs/cache/metar/snapshot_20261120/`, listed in `refs/cache/metar/SOURCES.json`, which marks them
redistributable with the attribution; they are local unless added with `git add -f`.

Without `--fetch` the script builds from the cache, deterministically.

- **Instant:** 2026-11-20 04:15Z (12:15 CST) [inf choice: a daylight scene on the last full local day of the window].
- **Reports:** 11 METARs at or before it (`192300Z` ... `METAR ZSSS 200400Z 33006MPS 300V360 CAVOK 13/M05 Q1027
  NOSIG`) and one TAF (`TAF ZSSS 200301Z 2006/2112 31004MPS 8000 SCT030 ...`).
- **Runway:** the inferred direction is north flow: arrivals 36R, departures 36L (wind 330°/6 m/s).
- **Kept fields:** only the identity / time fields and the raw text.

**The other packages' QA renders are not affected.** Their jobs pass `?t=2026-11-14T03:00:00Z`, which is before the
earliest snapshot report (19 Nov 23:00Z). There is no report before it and no TAF issued by then, so the scene keeps the
clear default sky, as before. This is why a recent recording was chosen over the 13-14 Nov sample, whose 03:00Z report
has rain and BKN006.

## 6. UI shell

### 6.1 Layout (from sfo3d `ui.js`)

- **Phone (≤ 760 px, portrait, touch):**
  - top bar: brand icon, status pill, clock;
  - a horizontally scrolling view bar (Overview / T2 / T1 / Runways / Tower / Top / Settings / About);
  - the credit line under it;
  - a **bottom sheet**: the peek shows the grab handle, the tabs and the weather and runway lines; it opens with the
    search and the list;
  - the legend chip sits above the sheet; the card replaces it while open.
- **Laptop:** the top bar, the view buttons on the right, a **side panel** on the left (tabs, weather and runway lines,
  search, list), the legend bottom-left, the card bottom-right, the credit line bottom-right.

### 6.2 Status pill and clock

- The pill follows the mode (§5.1); its tooltip explains it, and a tap opens About.
- The clock shows CST and the weather in the report's units. At 761-1480 px the core CSS hides the clock's weather part,
  so the panel's first line repeats it.
- The panel note has two lines:
  - `METAR 0400Z (observed): 330° 6 m/s · CAVOK · Q1027 · 13/-5 °C · trend NOSIG not applied`;
  - `Runway in use (inferred): north flow · arr 36R · dep 36L · tail-wind rule`.

### 6.3 Observed / Inferred legend

A box with the key line (`obs` observed, `inf` inferred) that opens a per-layer body: airfield, stand labels, markings
and signs, buildings, weather and runway, traffic.
- Lines for the markings and terminals packages appear only when those extensions are registered.
- What other packages appended under `?legend=1` (for example the gates line on bridges seen on SAR vs OSM-only) is kept
  as an extra line.
- `?legend=1` opens it, and the open / closed state is remembered (`shalive.legend`).
- `ui.el.legend` is still the body element, so the gates package's `prev + mine` append keeps working.
  `ui.addLegendLine(key, html)` is the new API.

### 6.4 Stand labels, card and search

- **Labels:** every 100 ms the 164 stands are projected with the renderer's camera.
  - A label is shown when the stand is within 250 m + 1.35 × the orbit distance (500-2,600 m) and the orbit distance is
    under 3.2 km; there are no labels in the overview.
  - Nearest first; overlapping labels are hidden, at most 90.
  - Each label shows the stand number from OSM (obs) and the class letter: green when Sentinel-2 showed a wide-body there
    (`cls_src` obs, 25 stands), amber when set by rule (inf, 139).
  - Remote stands have a dashed border. Touch padding is larger on coarse pointers.
  - "Show labels" in Settings hides them.
- **Card:** a tap or click on a label opens the stand card, without moving the camera. It shows:
  - the area and contact / remote, with the bus service (inf) for remote stands;
  - position: the OSM node (obs); heading of the lead-in line (obs);
  - class and span limit, with the class chip;
  - bridges: how many were seen on Umbra SAR vs from OSM gate nodes only;
  - push-back: distance along the lead-in (inf);
  - a provenance note.

  "Fly to stand" flies the camera there.
- **Search:** the list search also matches stand numbers and areas ("25" → 250, 256-259A).

### 6.5 Settings

The core settings (lighting, quality, labels, other traffic) plus **Runway direction rule**: tail-wind rule (default) or
into the wind (fallback), remembered as `shalive.rwyrule`.

### 6.6 About panel (`js/live/about.js`)

It opens with the statement that **Hongqiao traffic is simulated and inferred, not observed**: no movement was seen in
three full days of the open adsb.lol archive. Phase 3 aircraft will be labelled inf, "observed elsewhere" flights lend
identity and timing, and live ADS-B near Shanghai would be obs. Then come the current mode line and "Observed and
inferred" with the two chips. "Weather and runway in use" covers raw-text decoding, the trend not applied, the rule with
its in-sample and out-of-sample agreement, the fallback, and the AIP segregated mode.

Sources and licences, one item each:
- OpenStreetMap (ODbL 1.0, our files are Derivative Databases);
- Copernicus Sentinel 2023-2026 (modified);
- the Copernicus DEM GLO-30 notice ("produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence
  and Space GmbH 2014-2018 ...");
- Umbra SAR Open Data (CC BY 4.0, modified);
- ESA WorldCover 2021 (CC BY 4.0);
- ADSB.lol (ODbL 1.0; live only with the relay's option, adsb_icao only);
- VRS standing data (CC0 1.0);
- the Mictronics aircraft database (ODC-By 1.0);
- NOAA/NWS AWC and the Iowa Environmental Mesonet: "Not official NOAA material", with the CAAC met service as the
  originator;
- the AIP (mirror) short-facts notice: unofficial mirror, EFF 2026-07-08, reference only, no lists reproduced, not covered
  by the ODbL;
- CAAC MH 5001-2021 cited parameters with clause numbers (© CAAC, not reproduced; presence and placement at ZSSS
  inferred);
- the aircraft models (FlightGear GPL-2.0 via FlightAirMap-3dmodels, the 737-800 / 777 sources, the A380 CC BY-NC
  caveat, where the corresponding source is);
- the airline trademark notice;
- the fonts (SIL OFL 1.1).

The panel ends with "Not included" (no ATC audio, no flight-board data, no Google / Baidu / Amap imagery, no OpenSky
data), the controls, and "Not for navigation ... Not affiliated with or endorsed by CAAC, the Shanghai airport authority,
any airline or any data provider".

Other packages may append sections; terminals adds "Buildings and surroundings". The shell moves the tail ("Not included",
"Controls", the disclaimer) after them. The credit line has an "About & licences" link. `jobs/ui.mjs` checks that the
panel contains each of the 16 required notices; all are present.

## 7. Hooks for other packages and for Phase 3

- **Runway:**
  - `window.SHA.runwayMode()` gives the current inferred mode `{dir, flow, arr, dep, notes, rule, reason, report,
    history, tag: 'inf'}`;
  - `SHA.setRunwayRule('tailwind' | 'intowind')`;
  - the window event `sha:runway` (`detail` = the mode) fires on every change of direction or rule;
  - module `js/env/wx/metar_zsss.js`: `decode`, `components`, `RunwayDirection`, `RunwayDirectionIntoWind`,
    `runwayMode`, `assignRunways` (`closed` = the NOTAM hook), `windText`.
- **Observed traffic:** `SHA.observed = {enabled, ac: [adsb_icao records, src 'obs'], fetched, excluded, next}` in live
  mode with `--adsb`. `js/live/relay.js` has `fetchAdsb()`, `fetchTaf()` and `fetchMetarList()`; the core polls the
  METAR.
- **Mode:** `app.mode` / `app.cfg.modeInfo` (`mode`, `relay`, `relayInfo`, `relayWanted`, `relayError`, `snapshot`);
  `app.cfg.snapshot.traffic` is where Phase 3 puts its replay set.
- **UI:**
  - `app.hooks.status`;
  - `ui.addLegendLine(key, html)`, `ui.setLegend(html)` (body), `ui.openLegend(on)`;
  - `ui.setStands(list)`, `ui.renderStandCard(s)`, `ui.onStand`, `ui.onExtraSetting`;
  - `ui.setNote(text)` is the shell's: weather and runway lines.
- **QA (`SHA.qa`):** `selectStand(n, fly)`, `closeCard`, `openAbout`, `openSettings`, `openLegend`, `sheet`, `search`,
  `standLabels`, `runway`, `mode`.
- **Harness:** `DEVICE='iPhone 15'`, `MOCK_RELAY=1` (ping, METAR, TAF), `MOCK_ADSB=1`, `RELAY=http://...` (a real relay),
  `jobs/ui.mjs` (`SCENES=snapshot,offline,live`).

## 8. Rules carried

- **No OpenSky.** adsb.lol was **not contacted** in this package: its path was tested only against the local mock. The
  relay default is OFF; enabled, it allows at most one request per 180 s and 200 per 24 h, persisted.
- **aviationweather.gov requests in this package:** 2 (relay smoke test), 3 + 3 (snapshot, two runs), and 2 per relay
  start for the renders. That is far below its 100 per minute, and the relay caps itself at one METAR and one TAF request
  per 10 min.
- **User-Agent:** generic in the relay and in `build_snapshot.py` (`sha-live-3d-tools/0.1 (...)`). The unit test asserts
  the format and the absence of URLs, e-mail and "github".
- **No FAA marking, sign or lighting constant** was added. This package draws no airfield elements; CAAC MH 5001-2021 is
  cited in the About panel and legend only.
- **Observed vs inferred:** the `src` fields are shown as chips, in the legend, on the labels and in the card. The
  runway mode is tagged `inf`. Relay ADS-B records carry `src: 'obs'` and only `adsb_icao` qualifies.
- **No ATC audio toggle** (Q4); the About panel says why.
- **Untouched and uncommitted:** `sfo3d/`, `pc12/`, `hwd3d/` are untouched (`git status` clean there); nothing committed.

## 9. Renders (deviceScaleFactor 1)

```
SOFTGL=1 DEVICE='iPhone 15' RELAY=http://127.0.0.1:8792 SCENES=snapshot,offline,live OUT=docs/phase2 PREFIX=ui_phone node livetest.mjs jobs/ui.mjs
SOFTGL=1 W=1440 H=900       RELAY=http://127.0.0.1:8792 SCENES=snapshot,offline,live OUT=docs/phase2 PREFIX=ui_laptop node livetest.mjs jobs/ui.mjs
```
Phone = Playwright's "iPhone 15" descriptor (393 × 659 CSS px, iPhone UA, touch, `isMobile`) at deviceScaleFactor 1, low
quality tier (the app's mobile default). Laptop = 1440 × 900, high tier. Snapshot scenes use the default page (no `?t=`:
the snapshot instant, 12:15 CST on 20 Nov); live scenes went through a real `sha_live_server.py` on the current ZSSS
reports (22:30Z = 06:30-07:00 CST on 21 Nov, dawn); the offline scene blocks the relay API. Render times on this sandbox
(llvmpipe): about 1.5 min for the phone set, 7-8 min for the laptop set.

| Render (phone / laptop) | What I checked |
|---|---|
| `ui_*_snapshot_overview` | Status "Snapshot · 20 Nov", clock 12:15 (CST), two note lines (METAR 0400Z 330° 6 m/s CAVOK Q1027 13/-5 °C, trend NOSIG not applied; runway north flow, arr 36R, dep 36L, tail-wind rule); legend chip; credit line with "About & licences". Phone: bottom sheet peek holds the grab, tabs and both lines (4 rows at 11.5 px); the view bar scrolls sideways; the credit line sits under it. Laptop: side panel shrinks to its content while there is no traffic. |
| `ui_*_legend` | Legend open: six layer lines with obs / inf chips. Phone: full-width above the sheet; laptop: bottom-left beside / below the panel. Text readable at both sizes. |
| `ui_*_t2_labels` | T2 view with stand labels: laptop 34 labels (both piers, the west and south-west aprons, remote 212-217 / 410 / 413 dashed), phone 15 (overlaps hidden). Green class letters where Sentinel-2 showed a wide-body (e.g. 250 EL, 256 E, 283 EL), amber elsewhere. Labels sit on the stop nodes at the pier fingers; none floats over grass. |
| `ui_*_stand_card_label` | A real tap (phone: touchscreen) / click (laptop) on a visible label opened the card (phone 256, laptop 250); the label turns purple (selected). Card rows: OSM node (obs), lead-in heading (obs), class + span limit (chip by `cls_src`), bridges (seen on SAR or OSM-only), push-back (inf), provenance note. |
| `ui_*_stand_card_fly` | "Fly to stand" frames the stand from ahead-left. Phone: the card shrinks to its title and buttons ("details" re-opens it) so the stand stays visible above it; laptop: the full card stays bottom-right. |
| `ui_*_search_stands` | Search "25": a "Stands (6)" section (250, 256, 257, 258, 259, 259A) with class, chip and contact / remote; phone sheet opened. |
| `ui_*_settings` | Lighting, quality, labels, **Runway direction rule** (tail-wind default / into the wind), other traffic. No ATC audio control anywhere. |
| `ui_*_about`, `ui_*_about_licences`, `ui_*_about_end` | Top: the "simulated and inferred, not observed" statement and the mode line; middle: every licence notice (the job checks 16 required strings, all present); end: terminals' "Buildings and surroundings" section, then Not included / Controls / disclaimer (the shell moved the tail after it). Phone: full-width sheet, sticky close button. |
| `ui_*_relay_offline` | `?relay=1` with the relay API answering 503: the app falls back to the snapshot (same weather and runway lines) and the pill is red "Relay offline"; the job prints `check: relay requested but absent -> snapshot + Relay offline ok`. |
| `ui_*_live`, `ui_*_live_about` | `?relay=1` through the real relay: green "Live weather", clock 06:53 / 07:01 CST (dawn light, real time), METAR 2230Z VRB 1 m/s CAVOK Q1028 6/0 °C, runway north flow kept on calm / VRB (reason `keep (calm/VRB/missing)`); the About mode line says "Live through the local relay: ZSSS weather (METAR / TAF) on; observed ADS-B (adsb.lol) off". |

All phone renders: nothing overflows horizontally, the pill text ellipsises before the clock, touch targets (view
buttons, legend header, card buttons, labels) are at least about 30 px high.

## 10. Open issues

1. **Laptop width 761-1480 px hides the clock's weather text** (core CSS); the panel's first note line repeats it, so
   nothing is lost, but the clock alone shows only the time. At 1440 px the status pill's date sub-line is hidden too
   (core CSS hides `.prov` below 1720 px); the snapshot date is therefore in the pill text ("Snapshot · 20 Nov").
2. **Phone view bar scrolls sideways**: Settings and About sit off-screen to the right on a 393 px screen (core design).
   About is also reachable from the status pill and the credit line's "About & licences" link; Settings only by scrolling
   the bar. A bottom-sheet "more" menu could replace the icons on phones.
3. **Observed ADS-B is not drawn yet**: in live mode with `--adsb` the shell polls `/api/adsb` and keeps
   `SHA.observed` (count in the pill), but there is no traffic engine to draw or list aircraft (Phase 3). The relay side is
   unit-tested against a mock; the browser side was checked against the harness mock (`MOCK_RELAY=1 MOCK_ADSB=1`:
   `SHA.observed.ac` = the one adsb_icao record, pill tooltip "observed ADS-B on"), never against a real adsb.lol answer,
   deliberately (no adsb.lol request was made in this package).
4. **Inferred elements are not yet drawn distinctly in 3-D** (PLAN §4: "drawn distinctly"): the legend, labels, cards and
   About carry the obs / inf distinction, but bridges, paint, signs and buildings render the same whatever their source.
   A "provenance tint" overlay (as sfo3d's `?qa=prov`) would be the next step and needs each package's items to carry
   `src` (gates and markings items already do).
5. **Snapshot instant is a choice** [inf]: 12:15 CST on the last full local day of the downloaded window (20 Nov 2026,
   CAVOK, north flow). Re-run `tools/live/build_snapshot.py --fetch [--at ISO]` to refresh it; that makes 3 requests to
   aviationweather.gov. The source files in `refs/cache/metar/snapshot_20261120/` are redistributable per SOURCES.json but
   local until the lead adds them with `git add -f`; `data/sha_snapshot.js` alone is enough for the app.
6. **Runway rule starts at 36** when there is no earlier report (no preferred direction is published); with only 11
   snapshot reports (5 h) or 12 h from the relay, a light-wind start keeps that default. NOTAM closures (e.g. F4551/26,
   18L/36R closed 1700-2200 UTC until 29 Nov) are not applied: `assignRunways(dir, t, closed)` is the hook for Phase 3.
7. **Two decoders**: the renderer's EnvState still uses `js/env/wx/metar.js` (knots internally, trend cut), the UI and
   the runway rule use `metar_zsss.js` (report units). Both cut the trend; only the latter is verified against the Python
   reference on the ZSSS archive.
8. **Relay scope**: no SSE stream, no replay of recordings, no `/api/routeset` (VRS) yet; Phase 3 decides what the
   simulator needs from the relay. The relay binds to 127.0.0.1 by default; `--host 0.0.0.0` exposes it on the LAN
   (allow-listed static files and the three APIs only).
9. **Google Fonts** are still linked by `live.html` (core open issue 9; a phone in mainland China may not reach them); the
   About credits the fonts "when the browser can load them". Self-hosting the two OFL fonts would remove the dependency.
10. **Render weight**: the 26 `ui_*.png` files total about 18 MB at deviceScaleFactor 1; the lead may keep a subset.
11. **Interaction with other packages' QA**: the default page is now in snapshot mode. Their jobs pass
    `?t=2026-11-14T03:00:00Z`, before the earliest snapshot report, so their scenes keep the clear default sky. Checked
    with a page load at that time: mode snapshot, `wx.none: true`, no report, no TAF, note "Weather: no report (clear
    default sky)". Their renders were not re-run here. A job that wants the old wall-clock behaviour without a relay can
    pass `?mode=live`.
12. **OD4 (2026-11-20, added to PLAN.md while this package ran):** flights observed elsewhere are to be shown locally,
    read at run time from the gitignored `refs/cache/observed_elsewhere/`. The relay never serves `refs/` as static files
    (allow-list); Phase 3 should add an API endpoint such as `/api/observed_elsewhere` to `sha_live_server.py` that reads
    the local cache and returns only what the app shows, labelled "observed elsewhere, SHA time inferred". The About text
    already describes that tier.
