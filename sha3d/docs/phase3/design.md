# Phase 3 design: the ZSSS traffic simulator

Design task for PLAN §7 Phase 3 (A), written 2026-11-27; **revision 2 (2026-11-27)** answers every finding of the
adversarial review `docs/phase3/design_review.md` (5 high, 14 medium, 12 low; table in the last section). Docs only: no
code, data, tool, job or CLAUDE.md file was changed, nothing was rendered or committed. Owner decisions OD0-OD4 and the
§6b working defaults apply.

**Labels.** [obs] read in the code or data in this session, or measured by a scratch script; [inf] a design choice or an
inferred value; **AIP (mirror)** a short cited fact from the unofficial mirror (OD3). Line numbers are those of
2026-11-27. Phase 2 fix agents were editing `js/live/gates.js`, `gate_system.js` and `shell.js` while this was written,
so each reference also names the function.

**Scratch scripts** (gitignored, `out/phase3_design/`):

| Script | What it checks |
|---|---|
| `route_check.mjs` | edge-based router on `data/sha_taxigraph.json`: reachability, lengths, crossings, end-arounds, table size |
| `pave_check.mjs` | taxi-graph centrelines, stop nodes and gear tracks on the drawn pavement polygons; extent edge on final |
| `gate_times.mjs` (rev. 2) | runs `LiveGateSystem` **in node** with a WebGL / 2-D canvas stub; dock, undock, hurried undock and push-clear times per contact stand; reproduces the backward-jump defect (H1) |
| `capacity.py` (rev. 2) | stand capacity per side × size class; tier-2 on-ground demand per side under three readings (local data, aggregates only) |
| `optA_push.mjs` (rev. 2) | option A as a real push (tail first + push-turn), found by rule, with gear and tail points on pavement |
| `crossing_mc2.py`, `crossing_mc3.py` (rev. 2) | 18L/36R crossing waits under the review's fixes and under the revised rule (synthetic) |

The reviewer's scripts are in `out/phase3_design/review/` (`ground_demand.py`, `crossing_mc.py`, `flow_check.mjs`,
`undock_times.mjs`).

**No per-flight data here.** Counts and quantiles only; no callsign, flight number, registration, ICAO address or
per-flight time appears in this file (OD4). Label examples use placeholders (`MUnnnn`, `CESnnnn`, `B-nnnn`).

---

## 0. Decisions in brief

| Topic | Decision |
|---|---|
| Architecture | **A direct kinematic simulator** (`js/sim/*`, pure ES modules, also run by node). Every movement gets a time-parameterised trajectory, and the scene is a pure function of (day plan, inputs, t). It feeds **sha3d's own stand, bridge, GSE and aircraft pipeline** through a new **gate and time adapter** (`js/live/gate_sync.js` + additive `gate_system.js` methods): `resetTo`, sim-time `items()`, a "cold" occupant, and a static gate-timing table. sfo3d's report-ingesting `Traffic` engine is **not forked**; its limits and formulas are reused as cited priors. **This departs from the plan of record** (PLAN §7 (A) "the same traffic … pipeline as sfo3d"; arch.md §3.6 "adapt" for `traffic.js`): owner question Q0. |
| Time | One `SimClock`: live = wall clock; replay = anchor + speed; snapshot = the snapshot instant, paused. The operating day runs 04:00-04:00 UTC+8. Runway direction R(t) uses a report only from `receiptTime` + 12 min (`obsTime` + 20 min for archive-only days). Movements are committed in a fixed, dependency-respecting order with order-independent seeds. Commit-time arithmetic is integer cm / ms plus `Math.sqrt` only, on geometry baked offline. |
| Day plan | Built **in the browser** (and in node for tests) from committed aggregates (`data/sha_sim_inputs.js`). Tier-2 identities are merged from a **local overlay** only. `?identity=0` ≡ overlay = null: the public plan, with no tier-2 slot and no tier-2 time. |
| Capacity | Checked **per side (T1 / T2) × size class** at every minute, with an explicit overflow order. Unseen continuations of observed airframes are turnarounds, not night-stops, unless they fall at the day's edges. |
| Identity | The public plan has airline and type only (inf). Identity comes from `GET /api/observed_elsewhere?day=` (relay) or `window.SHA_IDENTITY` (private artifact only). An **exact-match audit** against the local identity set gates every commit; the harness refuses the endpoint unless `IDENTITY=1`, and refuses `IDENTITY=1` for output under `docs/`. |
| Routing | Edge-based Dijkstra over the committed `turns` table. The 14 one-way stands use **option A as a push**: tail first over two-way lanes to the next junction, then a push-turn of the tail into the one-way branch; found by rule (14 / 14 freed, `optA_push.mjs`). Routes and their integer geometry come from a precomputed table (`data/sha_routes.js`), including the F4552 closure variant. |
| Conflicts | **Prioritised reservations**: exclusive **blocks** (spatial queues), no-stop junction boxes and runway strips, runway resources, a directional **flow corridor** per side, stands. A later commit adapts to earlier trajectories only; every commit has a feasible fallback. |
| Packages | **A** plan and identity, **B** routing and kinematics, **E** gate and time adapter + harness, **C1** scheduler core, **C2** day suite, **D** app and UI, **F** artifact and delivery; then the integrator. Waves: (after Phase 2 fix round 3 is committed) A ∥ B ∥ E, then C1 ∥ C2 ∥ D ∥ F. About 6-8 h per package. |
| Owner questions | Q0 the architecture deviation (default: proceed); Q1 flight numbers on unobserved days (default: off); Q1b published HKG / TSA flight numbers on their own date (default: on); Q2 a rolling observed-elsewhere scan (default: not scheduled). |

---

## 1. Architecture

### 1.1 Options and why the kinematic simulator wins

| Option | What it would take | Verdict |
|---|---|---|
| **A. Synthetic reports → forked sfo3d engine** | Emit ~1 Hz pseudo-ADS-B records from the plan into `Traffic.ingest` (`sfo3d/js/live/traffic.js:562`). The engine infers phase, runway and stand from kinematics (header :1-16), smooths through a 1-3 s display delay (`DELAY_MS`, :32-33) and Hermite sampling, and drives bodies with bounded acceleration (`ctlGround` :2776, `ctlAir` :3028). | **Rejected.** (1) It is causal and stateful: `ingest(payload, recvNow = Date.now())` keeps a wall-clock offset (:562-565), report buffers, phase history and parked memory (`Track`, :350-368), and staleness ages. The scene at t needs every report from the day start, so a scrub replays hours. (2) The 5 s clamp in `update` (:2200) matters only below 12 fps at ×60; the real blockers are (1) [corrected, review L5]. (3) It *infers* what the plan already knows: the stand by `matchGate` / `gateScore` (:1687-1718) can differ from the plan's stand; touchdown and liftoff come from SFO-tuned thresholds (`TD_PRED_M`, `LIFTOFF_KT`, :149-154). (4) De-SFO-ing costs XL (arch.md §3.6): module-scope `STANDS` import (:21), `GEOID_M` (:31), the `inAirport` box (:276), and 58 lines matching `planFor|flysfo|offBlock|inBlock`. (5) Silent docking, re-acquisition and coverage-gap logic (`silentDock` :1986-2081, `stationary` :1543-1638, `reacqOutlier` :692) have no purpose without feed gaps. `TaxiNet` (:279-313) is a map-matcher and pavement test, not a router: routing is new code in every option, and `sha_taxigraph.json` already carries TaxiNet's fields (`edges`, `halfWidth`, `ways`, `aprons`, `leadins`). |
| **B. Direct kinematic simulator** | Each movement becomes a trajectory: segments with (t0, t1, s0, v0, a) along a baked path, plus air segments. `stateAt(t)` is a binary search per active movement. Stands, bridges and lights are driven from plan events. | **Chosen.** Deterministic, no history, any speed and any jump; the plan's stand and runway are used as they are; testable in node (§5). |
| **C. Hybrid** | B for simulated traffic, plus sfo3d's engine for observed records. | Only a thin hybrid is kept: the relay's rare observed adsb.lol records (`SHA.observed`, overflights at FL300+, PLAN §3) are drawn by the traffic extension as airborne dead-reckoned aircraft tagged `obs`, **only while the clock is live** (rev. 2, review L12). Forking 3,247 lines for an empty feed is not justified. |

**Relation to the plan of record.** PLAN §7 (A) asks for "the same traffic, physics and stand pipeline as sfo3d", and
arch.md §3.6 marks `traffic.js` "adapt: keep ingest hygiene, Hermite + dead reckoning, the kinematic body, the airliner
phase machine …". This design keeps the stand and bridge contract, the aircraft and light rendering, the phase
vocabulary and the physical limits, but replaces the report classifier and its body controller with planned
trajectories. That is a change of the plan of record, so it is put to the owner as **Q0** (§9.2), not only argued here.

### 1.2 What is reused (and from where)

| Reused piece | Source (read) | How |
|---|---|---|
| Stand stop convention, nose tip, docking | `js/live/gate_system.js` `noseGearX` :136, `standTip` :146, `setOccupant` :1999, `undockEarly` :2255, `hurryUndock` :2294, `pushClearEta` :2312, `step` :2380, `items` :2407; CLAUDE.md "Conventions"; gates.md §11 | Only through the gate adapter (§1.5, package E). For 238A / 259A the calls go to the base stand (`g.sharesBridgesOf`, gates.js `shaGates`). Remote stands get stairs and a bus from the same calls (`remoteGeo` :1731, `placeVehicles` :2429). |
| Model placement | `js/live/gates.js` `park()` :188-205 (pose :197) | `ac.pos = tip − dir × T.xMain`, `ac.fwd = dir`: the DEBUG park formula, which is the traffic contract. |
| Aircraft rendering, LOD | `js/live/aircraft.js` `LiveAircraft` (lodDist / farDist / shadowDist :39, `items` :170, `registration()` :128-133) | One `LiveAircraft` per airframe, `id` = the airframe id (so the registration decal reads `SHA.traffic.tracks`, §3). |
| Exterior lights | `js/env/aircraft_lights.js` `lightPhase` :95, `aircraftLightStates` :110 | The sim emits sfo3d's display-phase vocabulary (gate, parked, pushback, taxi, holding, lineup, takeoff, departure, approach, final, landing). |
| Labels, list, card | `sfo3d/js/live/traffic.js` `phaseLabel` :3212, `category` :3240; sha3d `traffic_api.js` (stubs); `ui.js` `renderList` :154, `renderCard` :175 | `js/live/labels.js` (D) builds a frozen `UiTrack` (§7.1) and re-implements phaseLabel / category for it; `traffic_api.js` re-exports them. |
| Physical priors | `sfo3d/js/live/traffic.js` `ctlGround` caps :2795 (taxi 1.8 / 2.0 m/s², rolls 3.3), steering radius 0.27 × wheelbase :2782, `attitude` :3129-3154, `LIFTOFF_KT` :154, `DOCK_WAIT_MS` 20 s :70 | Copied as cited `inf` priors into `js/sim/perf.js` as **integers** (cm/s, cm/s², ms). Aircraft-type values observed at SFO, a sea-level field like ZSSS; no airfield value is carried over. |
| Body overlap tests | `sfo3d/js/live/ground.js` `samples` / `inside` / `bodyOf` / `overlaps` :155-195 | Forked into `js/sim/bodies.js` for the test suite. `hv(h)` there takes **radians** (:16) and `bodyOf` imports `antOf` from `traffic.js` (:14, :187): the fork uses `geo.js` `hdgVec` (degrees) and the nose tip, and drops `antOf` (review L6). |
| Runway rule | `js/env/wx/metar_zsss.js` `RULES` :171, `assignRunways(dir, tMs, closed)` :178, `runwayMode(reports, {rule, start, tMs, closed})` :196 | `js/sim/runway.js` filters the reports by availability itself, calls `runwayMode(list, {rule, start, tMs: null})` for the **direction only**, then `assignRunways(dir, t, closed)` with the real t (review M11: `runwayMode` uses one `tMs` for the report filter and the night hour). |
| Frame, runways | `js/geo.js` `hdgVec` :65, `groundY` :84, `initGeo` / `RUNWAY_ENDS` :113-138 | Geometry for approaches, line-up and take-off (baked offline, §4.1). |

### 1.3 Module map

```
data/sha_sim_inputs.js  data/sha_routes.js  data/sha_gate_times.js  data/sha_stands.js  data/sha_taxigraph.js  data/sha_snapshot.js
        |  (window globals, injected by js/live/entry.js; never imported at module scope - arch.md R4)
js/sim/plan.js + alloc.js + identity.js ── buildDayPlan(...) -> DayPlan                       (A)
js/sim/router.js + perf.js + path.js + traj.js ── routes, integer geometry, trajectories      (B)
js/sim/runway.js + notam.js + resv.js + sched.js + sim.js ── createSim(...) -> Sim            (C1)
js/live/gate_sync.js + gate_system.js (resetTo, setService, GSE cache) + gates.js time source (E)
js/live/traffic.js (extension 'traffic', order 60) + sim_clock.js + time_bar.js + labels.js   (D)
   ├─ LiveAircraft per airframe (scene.add), tug mesh, UiTrack list / card / labels (ui.js)
   ├─ gate sync: gate_sync.apply(sim.events(tA, tB)) or gate_sync.resetTo(t, sim.stateAt(t).stands)
   └─ env: envCore.setTraffic({displayTime}) so that the sun and the METAR follow sim time
tools/sim/test_day.mjs + pave.mjs + day_report.mjs ── the day suite in node                    (C2)
tools/live/build_artifact.mjs + jobs/artifact.mjs ── the private artifact                     (F)
```

### 1.4 Time model

- **Operating day.** Local 04:00 → 04:00 next day, i.e. 20:00Z → 20:00Z, the window `observed_elsewhere.py` uses
  (`window_utc` of the local tables [obs]). The cut falls in the night pause (PLAN §6b Q10 e; AIP (mirror) AD 2.3).
- **SimClock** (`js/live/sim_clock.js`): `live` t = `Date.now()`; `replay` t = t_anchor + (wall − wall_anchor) × speed,
  speed ∈ {0, 1, 10, 60}; `snapshot` starts paused at `SHA_SNAPSHOT.now` and plays as a replay. URL `?sim=<ISO>`,
  `?speed=`, `?day=`; the existing `?t=` stays environment-only.
- **The environment follows the clock** (D): `AppEnv.setTraffic({displayTime})` (`app_env.js:44`); `DataClock.trafficTime`
  returns the fixed snapshot instant in snapshot mode (`clock.js:82`), so that branch asks the sim clock when one is set;
  a scrubbed or replayed clock sets `overridden` (live = "latest report wins", `app_env.js:56`); the extension calls
  `app.applyEnv(Date.now(), true)` on every jump and every 30 s of sim time (`app.js:244` does it every 30 s of wall
  time). **Replay-day weather** (rev. 2, review M11): while the clock shows a day other than today, the 60 s relay poll
  (`app.js:196-197`) must not call `envCore.setReports`; the env takes that day's list from `SHA_SNAPSHOT.days[]`.
- **Report availability** (rev. 2, review M1). A report counts for R(t) from
  `avail = receiptTime + 12 min` (AWC JSON; 10 min relay interval `sha_live_server.py:57` + 60 s client poll
  `relay.js:14` + 1 min margin), or `obsTime + 20 min` when the list has no receipt time (IEM-only replay days).
  `receiptTime` is a property of the report, identical on every device, and both the relay (`METAR_KEEP` :102) and the
  snapshot builder (`KEEP_M` :26) keep it. Measured receipt latency (`refs/cache/metar` AWC JSON, n = 97): p50 5.5, p90
  6.8, max 21.1 min; 8.2 % exceed 12 min, which is why the rule keys on receipt, not observation. A relay outage can still
  split live devices; `Sim.hashes()` shows it (§6.1 day line).
- **Runway timeline R(t)** (`js/sim/runway.js`): the rule is stepped in `obsTime` order over the reports with
  `avail ≤ t` and `obsTime ≥ t0 − 2 h`, starting from the "into the wind" direction of the first such report (a fixed
  anchor, not "36 when no report", relay_ui.md open issue 6). The night hour and closures use the real t (§1.2). The rule
  (tail-wind or into-the-wind, both inf: 78.1 % / 80.5 % out of sample, sources_sim.md §5.2) is part of `plan.hash`;
  changing it in Settings re-commits the day.
- **Relay METAR look-back** (A): `WX_HOURS` 12 → 26 (`sha_live_server.py:58`), same single upstream call (`hours=`).
- **Commit order** (rev. 2, review M6). Every movement has a commit time:
  - departure: t_c = planned off-block − 5 min;
  - arrival: t_c = max(planned touchdown − 20 min, t_c(departure of the stand's previous occupant) + 1 ms).

  Commits run in (t_c, id) order; the day is a deterministic fold. In live mode a movement is committed once t ≥ t_c.
  The dependency term moves an arrival's commit after its stand's departure, so the arrival knows when the stand is
  free (§4.5). With the 20 min stand buffer the departure's commit is still ≥ 17 min before that arrival's touchdown,
  i.e. before its final starts (touchdown − 3.3 min).
- **Direction switch events** (rev. 2, review M2). When R(t) changes at t_s, a `switch:<t_s>` event enters the fold at
  t_s: departures committed in the old direction whose line-up is later than t_s + 8 min [inf] are re-planned from
  their position at t_s to the new end (the past part of their trajectory is kept); everything else keeps its committed
  runway, and the flow corridor (§4.5) keeps opposite-direction traffic apart. The AIP tolerance for a short downwind
  operation during a change (AD 2.20 2.1.2) covers the movements that keep the old end.
- **Seeds and integer arithmetic** (rev. 2, review M5). `seed(day) = fnv1a32('sha3d-plan|v' + PLAN_VERSION + '|' + day)`;
  each draw uses `splitmix32(seed ^ hash(slot) ^ PURPOSE)`, independent of processing order. Everything that a commit
  decides is computed from **integers baked offline** (§4.1: lengths, fillet trims, arc lengths and radii in cm, speeds
  in cm/s) with `+ − × ÷`, `Math.round` / `floor` and `Math.sqrt`, all correctly rounded in IEEE 754. No `sin`, `cos`,
  `atan2`, `exp`, `pow` or `Math.hypot` (not correctly rounded in V8 or JavaScriptCore) runs inside a commit. Display
  evaluation (positions, headings, attitude) may use them. Live-routed fallbacks use the same integer pipeline.
- **Jump cost.** `stateAt(t)` = `commitUntil(t)` (incremental forward, cached) + a binary search per active movement.
  With the route table a commit is a lookup plus reservations: target ≤ 0.3 s per day on a laptop, ≤ 1.5 s on a phone,
  measured by C1. Plan building (allocation, rotations) has its own budget (≤ 0.2 s laptop). Commits run **time-sliced**
  (≤ 6 ms per frame, generator-based) with a "Preparing the day…" note (review L12).
- **Backward and long jumps** (rev. 2, review H1): committed trajectories are re-used; the gate engine is reset with
  `gate_sync.resetTo(t, sim.stateAt(t).stands)` (§1.5) on every backward jump and every forward jump > 120 s.

### 1.5 Gate engine coupling (new, package E; review H1, H2, M7)

**Findings confirmed.** [obs]
- `setOccupant(..., animate = false)` never touches `this.anims` (only the `animate` branches create an entry,
  `gate_system.js:2013-2026`), and `extension(g)` returns the stale entry's `k` (:1994). `step(now)` clamps `u` to [0, 1]
  (:2383). `parks`, `settles`, `g._parkHold.until` (setOccupant), `g._incoming.until` (`expectArrival` :2214) and
  `g._early` (`undockEarly` :2255) all hold the time they were given. There is no reset method (constructor :700).
- Reproduced in node (`gate_times.mjs`): after a docking at sim 10:00 and a jump back to 09:00 with `animate = false`
  on the then-empty stand, the docking animation entry remains, its `t0` 3,612 s in the future.
- `scene.js:30` calls `gateSys.items(Date.now())`; the DEBUG `park()` / `unpark()` pass `Date.now()` (gates.js :203,
  :212).
- `pushClearEta` (:2312) reads the running animation, so it differs between ×1 play, ×60 play and a jump.
- Night-stoppers would get full GSE all night: `build()` places vehicles for every occupied, non-animating bridge stand
  (:2361) and `remoteGeo` for every occupied remote stand (:1731); `setOccupant` `opts` carry only `freighter` /
  `early` / `undockS`.
- **The engine does run in node** with a WebGL and 2-D canvas stub (`gate_times.mjs`: `initGL({getContext})` with a
  Proxy context, `document.createElement` stub): constructed in 746 ms, all 56 bridge stands docked and undocked for
  their class reference type without error. The review's "cannot be constructed in node" holds only without the stub.

**Static gate-timing table** `data/sha_gate_times.js/.json` (E, `tools/sim/build_gate_times.mjs`, node + `tools/sim/gl_stub.mjs`):
per contact stand × model type key that the allocator may put there, `[dock_s, undock_s, hurry_s, pushClear_s]`:
- `dock_s`: on-block → docked, including `DOCK_DELAY` 12 s (:276);
- `undock_s`: `undockTime(g)` (:1996), the retraction at the sheet's normal rates;
- `hurry_s`: `undockEta` from docked (`hurryPlans(undockPlans(g), 1).T`);
- `pushClear_s`: `pushClearEta` from docked (`pushHitK` against the straight push sweep).

Measured for the class references (56 stands): dock p50 58.7 s, p90 80.5, max 132; undock p50 46.7, p90 68.5, max 120;
hurried p50 30.4, max 52.6; push clear p50 1.0, max 1.5 s [obs, approximate: terminal outlines without the `WALL_H`
override, no pavement map]. The file carries the sha256 of its inputs (`gate_system.js`, `gates.js`, `sha_stands.json`,
`types.js`); the browser adapter re-computes 5 sampled stands at boot and logs a mismatch (display only: the sim keeps
the table, so every device agrees).

**Rules the sim applies (C1) with the table** (H2):
- undock at off-block − U, U = max(150 s, `undock_s` + 15 s); the engine call is `undockEarly(g, t_undock)`, which keeps
  the aircraft as the occupant (`g._early`) for the neighbours' bridges and the GSE keep-out;
- `setOccupant(g, null)` only when the push starts; the push starts at off-block and never waits on the runtime;
- dock at on-block + 20 s (sfo3d `DOCK_WAIT_MS`), docked at on-block + 20 s + `dock_s`;
- if the display lags after a jump, `hurryUndock` catches up; that is visual only.

**Adapter API** (E; additive methods, existing ones unchanged; §7.1): `resetTo(t, occupants)` clears `anims`, `parks`,
`settles`, every `_parkHold`, `_incoming`, `_early`, restores `b.hRest = b.h0` and `b._parkQ`, then sets every stand to
its state at t (docked / docking or undocking at the phase given by the table, re-created as animations with sim-time
`t0`, early, empty); `setService(g, 'turn' | 'cold', t)`; a per-stand GSE placement cache (invalidated by the stand and
its `nearStands`); `items()` driven by a time source (`gateSys.now()`, sim time while traffic runs). The DEBUG park is
off while traffic runs (§6.3).

---

## 2. The day plan

### 2.1 Tiers and inputs (OD2 order)

| Tier | Source | What a slot gets | Days |
|---|---|---|---|
| 1 observed at ZSSS | relay `--adsb` (adsb_icao only) | drawn airborne, `obs`, live clock only; not part of the plan | rare overflights (PLAN §3) |
| 2 observed elsewhere | local `refs/cache/observed_elsewhere/sha_observed_<day>.json`: 542 / 550 movements with `consistency` ∈ {`track_consistent`, `far_end_match`} and a `t_sha` on 10 / 12 Nov [obs counts] | callsign, flight number, registration, ICAO type (field `t`), operator, role, SHA time `t_sha` (inf) with its own `sigma_s`, far end; real rotations | 10 and 12 Nov 2026 only |
| 3 published | HKIA (DATA.GOV.HK) 13 Nov: 6 + 7 SHA movements; TSA (Taiwan OGDL) 14 Nov: 4 + 4 [obs, sources_sim.md §1.2] | flight number(s), far-end scheduled time; SHA time = far-end ∓ block time (inf); type only where TSA gives it | 13 / 14 Nov only (§2.6, owner Q1b) |
| 3 published facts | CAAC daily total (783.4 Jan-Sep 2026; 802 winter plan [sec]), SAA airline-terminal page (field.md §2.2), fleets (fleet.md §1), AIP (mirror) rules, NOTAM summary | targets and rules | all days |
| 4 inferred | hourly profile (`sources_sim_hourly.json`), airline weights and type mix (aggregates), turnaround distribution | airline + ICAO type + times + stand + rotation | the fill on every day |

`data/sha_sim_inputs.js` (`window.SHA_SIM_INPUTS`, built by `tools/sim/build_sim_inputs.py`) holds:
- the hourly arrival and departure profiles and the daily targets per date range;
- **two airline weight sets** (rev. 2, review M9):
  - `complement` (observed days): ∝ DB SHA callsigns − identified distinct callsigns per airline
    (`observed_elsewhere_stats.json` `db_sha_callsigns_by_airline`, `distinct_callsigns_by_airline`), leaning the fill
    to the blind routes (on 10 Nov: CES 31 % of the residual against 39 % identified and 34 % in the DB);
  - `fullDay` (every other day): the expected per-airline shares of a whole observed-day plan, i.e.
    (identified + complement × fill count) / total, averaged over the two days;
- the type mix per airline in the same two sets, cells < 3 merged into "other" so that no small cell points to one
  flight; the wide-body share is halved **only in `complement`** (the blind routes' narrow-body bias,
  observed_elsewhere.md §5.4);
- the turnaround quantiles (same-airframe pairs 81 / 106 / 134 min P10 / P50 / P90) and the per-type minimum
  turnaround (narrow 35 min, wide 60 min [inf]);
- the airline → terminal rules, the HKG / TSA rows (section `published`, allow-listed, §3), the NOTAM effect records
  (§2.5), and the delay distribution.

### 2.2 Algorithm (`js/sim/plan.js` `buildDayPlan`)

1. **Target per hour** h: `target_h = profile_h × total(day) / Σprofile`, arrivals and departures balanced to total/2
   each (the B1-scaled profile has 408 arrivals against 375 departures, a coverage artefact [inf]).
2. **Tier 2** (only with an overlay): every identified movement becomes a slot `oe:<uid>` (`uid` = archive day + index,
   not an identity [obs format]); arrival on-block = t_sha + taxi-in estimate; departure off-block = t_sha − (taxi-out +
   queue) estimate (route-table medians per stand group). **No seeded delay** (rev. 2, review M10): `t_sha` is already
   an inferred actual time (observed_elsewhere.md: inferred take-off − scheduled off-block +5 to +42 min); a tier-2
   movement moves only by the scheduler's holds, and `day_report.mjs` reports the distribution of |sim − t_sha|.
3. **Tier 3** slots `pub:<n>` for the date, unless covered by a tier-2 slot with the same flight number.
4. **Continuations of observed airframes** (rev. 2, review H3). An observed departure whose arrival was not seen
   starts parked only if it is before 11:00 local [inf: first bank + minimum turn]; otherwise it gets an inferred
   arrival at t − (drawn turnaround ≥ the type minimum). An observed arrival whose departure was not seen stays to t1
   only if it is after 19:00 local; otherwise it gets an inferred departure at t + drawn turnaround. Continuations are
   tier 4 (airline and type only, no registration) and count toward the hour's target. Evidence (`capacity.py`): read
   as whole-day occupancies (the review's upper reading) the tier-2 airframes need 81 / 95 aircraft at once on the
   T2 side (wide 19 / 19) on 10 / 12 Nov; read as turnarounds they need 59 / 65 (wide 13 / 14); closed pairs alone
   need 31 / 26.
5. **Fill:** `fill_h = max(0, target_h − tier2_h − tier3_h − continuation_h)` per role; times uniform within the hour
   (seeded); airline from `complement` (observed days) or `fullDay` (other days); type from that airline's mix in the
   same set.
6. **Rotations.** Tier 2 by registration (165 / 159 pairs, gap median 112 / 110 min [obs, local aggregate]). Fill
   departures are paired greedily, in time order, with an earlier unpaired fill arrival of the same airline and type
   family, gap in [minimum turn, 6 h] nearest a drawn turnaround. Unpaired departures are night-stoppers (parked from
   t0); unpaired arrivals stay to t1.
7. **Night-stop count per side** = min(the side's share of the cumulative-flow bound, 0.85 × usable(side)), where the
   balanced profile needs at least 78 aircraft on the ground at 04:00 [obs, computed] and usable(side) is in §2.4.
8. **Delays** (seeded, **tiers 3 and 4 only**): 80 % within ±10 min, 15 % +15-60 min, 5 % +60-120 min [inf: CAAC
   on-time statistics not read]. An arrival delayed past 01:00 local while F4551 is in force is diverted to Pudong
   (inf; listed in the day summary, not drawn). A departure may push after midnight (Q10 e).
9. **Stand allocation** (§2.4); movements that end unplaced are **removed** from `plan.movements` and counted
   (`plan.stats.unplaced`), so every count test runs on drawn movements. The plan is frozen: `plan.hash` = fnv1a over its
   canonical JSON (including the runway rule and the weight set).
10. **Day-cut continuity** (rev. 2, review L7): `buildDayPlan(D + 1)` takes the end state of a **standalone**
    `buildDayPlan(D)` (parked airframes by stand and type family) and prefers to place its night-stoppers there. One
    level deep, so plan(D + 1) stays a pure function of the D and D + 1 inputs; a day change costs two plan builds. At
    04:00 only the unmatched stands change (2 s cross-fade).

### 2.3 Terminal, type and model rules

- **Terminal.** T1 serves 9C, NS and MF (domestic) and every international or HMT flight; T2 serves all other domestic
  flights (SAA directory, field.md §2.2 [obs]; reading [inf]). International and HMT are 6.3 % of the 2025 movements
  (PLAN §1); in tier 2 they are known from the far end; in the fill they are drawn at that rate for MU, FM, CA and the
  foreign carriers.
- **Stand groups** [inf, from `area` and bus service, stands.md §5]: **T1 side** = the 13 T1 contact stands, the east
  apron north of T1 (30) and the east remote apron along A (16); **T2 side** = the 45 T2 contact stands, the 25 T2
  remote stands, the west (13) and south-west (10) remote aprons; the business apron (12, class B) takes generic
  business jets only (default 4 a day [inf], `bizPerDay`).
- **Types without a model.** C919 is 6.4 % of the observed movements (observed_elsewhere.md §5.4); `TYPE_MODELS` has no
  C919 or AJ27 entry (`fit.js:68-69`). The sim keeps the real ICAO type (`icao`) and draws a stand-in (`model`: A320 for
  C919, CRJ900 for C909 / AJ27); the card says "3D model: Airbus A320 stand-in (no C919 model until Phase 4)" [inf]. The
  stand class uses the real span (C919 35.8 m [sec]); the gate-timing table uses the drawn model, whose doors the bridges
  meet.

### 2.4 Stand allocation (`js/sim/alloc.js`)

Interval scheduling over `plan.stands[name] = [{from, to, mv, af}]`, in rotation order (on-block time, tier 2 first):
- **Fit:** type span ≤ stand `maxSpan` and length ≤ `maxLen` (gates.js `shaGates`: the gate objects' own limits).
- **Buffer:** [on − 10 min, off + 10 min] free [inf]. The 5 exclusive pairs (`excl`) are mutually exclusive.
  NOTAM-closed stands are skipped (267, 14-21 Nov, F4313).
- **Capacity per side × class** (rev. 2, review H3), from `sha_stands.json` (`capacity.py` [obs]):

  | Side | Stands | Non-B | Usable at once (exclusive pairs) | A330 / B787 fit | A350 / B77W fit |
  |---|---|---|---|---|---|
  | T1 | 59 | 49 | 49 | 18 | 18 |
  | T2 | 93 | 88 | 84 (4 pairs) | 16 (B763 also on the class D stand: 17) | 5 |
  | Business | 12 | 0 | - | 0 | 0 |

  `test_plan.mjs` evaluates the occupancy per side × {narrow, A330/B787, A350/B77W} at every minute and reports the
  maximum against the capacity, never one airport total.
- **Preference order:** own side contact stand of the smallest fitting class (keep E / EL for wide-bodies) → own side
  remote → overflow.
- **Overflow order** [inf]:
  1. AIP combined wide-body positions (215 + 216 → 216E, 219 + 220 → 220E, 280 + 281 → 281E, 412 + 413 → 413E,
     AD 2.20 3.2.7, `aip_facts.combined`) **only when the stand data places them**; today they are unplaced
     (`counts.aip_overlays_unplaced` 6), so this is a data request to `tools/airport/build_stands.py` (Phase 1 owner),
     listed in `docs/phase3/plan.md`;
  2. the 4 OSM `positions` without a ref (east remote apron, hangar apron …), narrow-body night-stoppers only;
  3. the other side's remote stands (T2 overflow → east remote apron / east apron; wide-bodies to the T1-side EL
     stands), counted (`plan.stats.crossSide`) and labelled on the card "parked on the east remote apron (overflow,
     inferred)";
  4. unplaced: removed from the plan and counted (target 0 on the test days).
- **Bridge share:** caacnews reports about 72-76 % (field.md §3.1); the allocator reports the contact share per side;
  test band 60-85 % [inf].
- **Adjacency** ("no simultaneous movements at adjacent stands", AIP (mirror) AD 2.20 3.2.2.1, `aip_facts.adjacent`)
  is a scheduling constraint (§4.5). Neighbours from `cls_evidence.neighbours`.
- **No towing by default** (all stands "Taxi in, Push back", AD 2.20 3.2.6; towing across runways forbidden 2200-1600
  UTC). An optional `towLong` (> 4 h at a contact stand → tow to a remote stand on the same side) is off.
- **The plan's stand is a preference.** The committed stand can differ when a departure's holds extend the stand's
  occupancy (§4.5 handover): the arrival is then re-allocated at its commit by the same order.

### 2.5 Runways, NOTAMs, night

- **Mode:** AD 2.20 2.1.1, segregated: 18L/36R arrivals, 18R/36L departures (`assignRunways` :178).
- **Direction:** R(t) (§1.4). Night: no landings on 18R/36L 1600-2300 UTC except alternates (AD 2.20 2.1.6, already in
  `assignRunways`).
- **NOTAM effects** (derived records only: ids, windows, targets; sources_sim.md §4.2; `js/sim/notam.js`):

  | NOTAM | Applied as |
  |---|---|
  | F4551/26 | 18L/36R closed 1700-2200 UTC daily, 10-29 Nov: `closed` for `assignRunways`; crossings only at H4 / H7 |
  | F4552/26 | the listed taxi links closed in the same window: `closedLinks(t)`; routes from the table's **F4552 variant** (baked by B), live routing only for closures the table does not know |
  | F4313/26 | stand 267 closed, 14 Nov 1700Z - 21 Nov 1000Z |
  | F4301/26 | the first rapid exits from the DTHR (§4.2) |
  | F4275/76/26 | works north of DTHR 18L: no effect on movements |

  The About panel carries the summary's date: "in force 2026-11-02 07:06Z; later NOTAMs not known".
- **Night pause:** nothing scheduled 01:00-05:59; departures start at 06:00 from 18R/36L. The scene shows the
  night-stoppers parked, **cold** (no GSE, stairs or buses; bridges stay docked at contact stands [inf]), lights off.

### 2.6 Days other than the observed days, and the label rules

- **Identity only where observed for that day.** On any day other than 10 and 12 Nov there are no tier-2 slots: the
  plan is tier 4 (plus tier 3 on 13 / 14 Nov), every aircraft shows airline and type, and **no registration is ever
  shown for a tier-4 slot, a continuation or another day** (PLAN Q10 f).
- **Live mode on a normal day** (e.g. today, 27 Nov) is therefore fully inferred; identities appear in the replays of
  10 and 12 Nov; the UI says so (§6.1 day line).
- **Tier 3 on its own date** (rev. 2, review L8). The PLAN §6b Q10 f default reads "identity is shown only where
  observed (labelled 'observed elsewhere'), otherwise airline and type only". Showing a **published** HKG / TSA flight
  number on 13 / 14 Nov rests on OD2 item 3 (binding: "schedules where their terms allow"): it is the published
  schedule of that date, not an invented identity. Because it widens the Q10 f default, it is owner question **Q1b**
  (recommended: on, own date only, no registration, type only where TSA publishes it).
- **Repeating flight numbers on other days** (proposal, default OFF, owner question Q1): with the Settings switch
  "Flight numbers seen on other days", an inferred slot on another day may show a flight number only if that flight was
  observed on **every** observed day (10 and 12 Nov) within ±20 min of the same local time, with the same airline and
  role; the local builder inserts it as `rep:<flight>` (tier `rep`, type as observed if identical, registration never).
  It needs the local overlay, so the public build never has it.
  - 3-D label `MUnnnn*`; list chip `seen other days`; card line: "Flight number seen at about this time on 10 and 12 Nov
    2026 (observed elsewhere, open ADS-B outside the Shanghai coverage gap). It was not observed today: today's flight,
    time and aircraft are simulated."
  - Tier-3 rows on other dates use the same switch and the line "Flight number from the published Hong Kong airport
    schedule of 13 Nov 2026 (Airport Authority Hong Kong, via DATA.GOV.HK); not confirmed for today."

---

## 3. Identity data flow (OD4)

| Item | Where | Committed? |
|---|---|---|
| Public plan inputs (aggregates, HKG / TSA rows, NOTAM effects) | `data/sha_sim_inputs.js/.json` | yes (licences §8; the `published` section allow-listed) |
| The public plan itself | built at run time; never written to disk except as aggregate statistics | n/a |
| Identity source | `refs/cache/observed_elsewhere/sha_observed_<day>.json` | **no** (gitignored) |
| Overlay served locally | `GET /api/observed_elsewhere?day=YYYY-MM-DD` (relay); `/api/ping` `features.identity: [days]` | n/a |
| Overlay in the private artifact | `<script>window.SHA_IDENTITY = {...}</script>` inlined into `out/artifact/` only with `--identity` | **no** |
| Local plan or identity dumps | `out/plan/`, `out/phase3/local/` only | **no** |

- **`?identity=0` ≡ overlay = null** (rev. 2, review H5): the page neither fetches nor reads an overlay; the plan is the
  public plan: no `oe:` slot, no `rep:` slot, no tier-2 time, rotation or continuation. Hiding fields is never used as a
  substitute. Every job that writes under `docs/` uses it.
- **Overlay schema** (`tools/sim/observed_overlay.py` `overlay(day)`, A; rev. 2, review M12):
  ```
  {v: 1, day, tier: 'oe', note: 'observed elsewhere, SHA time inferred', licence: 'ODbL 1.0 (adsb.lol), VRS CC0, Mictronics ODC-By',
   records: [{uid, role, airline, cs, flight, reg, type, operator, far, t_sha, sigma_s}]}
  ```
  - `type` is copied from the source field **`t`**. The source field `icao` is the **24-bit address** in all 1,120
    records (6-hex) and is never read; nor are `evidence`, `segs`, `first`, `last`, `est`, `src`.
  - Only `consistency` ∈ {`track_consistent`, `far_end_match`} with a `t_sha`.
  - `flight` from the callsign through the airline prefix table (`data/lookup.js` `AIRLINES`).
  - `test_observed_overlay.py` asserts the field allow-list, `type` ~ `^[A-Z][A-Z0-9]{1,3}$`, and that no value
    matches `^[0-9a-f]{6}$`.
- **Relay rules** (A edits `sha_live_server.py`; rev. 2, review L9): an API endpoint, not a static path (the static
  allow-list `ALLOW` :351 is unchanged; `refs/` stays unservable); `day` must match `^\d{4}-\d{2}-\d{2}$` **and** be in
  the list of local files, else `{available: false}`; `--no-identity` switches it off; with a `--host` other than
  loopback the endpoint answers `{available: false}` unless `--identity-lan` is also given; the banner says which.
- **Harness gate** (E edits `livetest.mjs`; review H5): `/api/observed_elsewhere` is answered `{available: false}` —
  also through the `RELAY=` proxy (:34-35) — unless `IDENTITY=1`; `IDENTITY=1` with an `OUT` under `sha3d/docs/` exits
  with an error. `MOCK_RELAY=1` serves **synthetic** overlay records only (placeholder airline `XXX`, registrations such as
  `ZZ-SIM1` and callsigns `XXXSIM1`, outside every real format).
- **In-page assertion** (D, `jobs/traffic.mjs`): before every shot `SHA.traffic.identity === 'none'`,
  `SHA.sim.plan.tiers.oe === 0` and `!SHA.sim.plan.tiers.rep`.
- **The registration decal** (`aircraft.js` `registration()` :128-133 reads the livery's `reg`, else
  `SHA.traffic.tracks.get(id).info.reg`): `UiTrack.info.reg` exists only for tier-2 tracks with an overlay; the livery
  never gets a `reg`. With identity on, the local app shows the real registration on the fuselage (OD4: shown locally);
  with `identity=0` there is none to paint.
- **Exact-match audit** (rev. 2, review H4; `tools/sim/audit_identity.py`, A; local, prints counts and file paths only):
  - identity set from every `refs/cache/observed_elsewhere/*.json` and `scan/` file: callsigns, derived IATA flight
    numbers, registrations (all formats: 709 of 1,120 records are `B-` + 4 digits, the other 411 are `B-` + 3 digits +
    letter, `B-` + 2 digits + 2 letters, `B-` + 2 digits + letter + digit, `B-` + 3 letters, or 2 letters + 4 digits),
    24-bit addresses, and every `t_sha` as epoch s and ms;
  - searched: every staged file, the whole `git diff --cached`, PNG text chunks, and `docs/**`;
  - **allow-list**: matches inside `data/sha_sim_inputs.*` section `published` are allowed only for flight numbers that
    also occur in the tier-3 source files (`refs/cache/schedules_open/`), and only if no registration, callsign, address
    or `t_sha` occurs there; `SOURCES_sim.json` names that section "published schedule facts, not observed-elsewhere
    data";
  - it is the integrator's gate and the lead runs it before every commit;
  - a second net for `docs/**` and `jobs/**`: `\bB-[0-9A-Z]{3,5}\b`,
    `\b(?:[A-Z]{2}|[A-Z][0-9]|[0-9][A-Z])[0-9]{2,4}\b`, `\b[A-Z]{3}[0-9]{1,4}[A-Z]?\b`, minus an allow-list of ICAO type
    designators (`types.js`), NOTAM ids (`F\d{4}/\d{2}`), stand names and taxiway designators.
- **Public checkout without `refs/cache`:** no overlay → the identical public plan, the same code path as a non-observed
  day. A test asserts that the public 12 Nov plan has no field other than airline, type, model, times, stand and tier.

---

## 4. Ground and air movement

### 4.1 Routing on `sha_taxigraph` (`js/sim/router.js`, B)

- **State and transitions.** State = (link, exit node); transitions only from `turns[node]` (≤ 90° + 10°, one-way
  respected, crossings only on the AIP list; at a push end any lane direction, the tail being turned: taxigraph
  `routing.turns` [obs]). `use: runway` links are not taxi links, `status: construction` is skipped, `use: stand` only for
  its own stand, push links only as the first leg, `arrival` / `departure` one-way use per role.
- **AIP lane rules copied from the data** (rev. 2, review L2; taxigraph `rules.facts`): arrival-only Y1-Y3;
  departure-only M1-M6, L11-L17; **one aircraft at a time on any of Y1-Y3, M1-M6, L15-L17** (AD 2.20 3.1.5); crossings
  of 18R/36L via H1-H7 and of 18L/36R via H1, H4, H7 (2.2.5); no vacating via H3, H4, H5 (2.3.2); turns ≤ 90° (2.3.1);
  span ≥ 36 m **mainly cross 18R (36L) via H2 (H6)** (2.3.3).
- **Measured on the committed graph** [obs, `route_check.mjs`]: arrivals 164 / 164 stands from all 4 landing ends;
  departures 150 / 164 to all 4 ends; the 14 one-way stands (stands.md §6) fail all 4.
- **Option A as a push** (rev. 2, review M13). The push link is extended **tail first** over up to two apron lanes
  (motion turns ≤ 100°, ≤ 60 m) to a junction J, where a push-turn (≤ 100°) swings the tail into a branch X; the aircraft
  then taxis forward through J as if it had arrived via X (geometric turns ≤ 100° at J, the normal rules afterwards).
  The router searches this **by rule** (the shortest run that reaches all four take-off ends; no link ids). Measured
  (`optA_push.mjs` [obs]):
  - 14 / 14 stands freed; the runs use **two-way lanes only** (10 distinct links, 246 m in total, 7.2-59.4 m per stand);
    the tail swings 3-67° into the one-way segment that stands.md §6 names (for 227 and 238A a neighbouring one-way link);
  - pushes become 134-191 m (median 149; 7 of 14 above the 150 m long-push flag), longer than the 100-143 m of the
    stands.md forward-taxi reading, which ran against the one-way tags;
  - 0 of 2,196 samples (nose gear, main gear ±3.8 m, tail point; A321 reference, 20 m push-turn radius, approximate
    kinematics) off the drawn pavement.
  - B re-tests it with the exact swept planform per stand class (§5) and reserves the run, J and the swing branch for the
    whole push plus the 90 s start-up (§4.5).
- **Route lengths:** departures to the west runway median 2,261 m, P90 3,034 m, max 3,716 m; arrivals from the east
  runway median 1,129 m, P90 2,098 m. 142 of 328 departure routes cross 18L/36R (at H1 / H4 / H7).
- **End-around preference** (AIP (mirror) AD 2.20 2.3.3: ROUTE-NORTH (BN → N) / ROUTE-SOUTH (BS → S) normally H24 for
  arrivals to the west apron; span < 36 m normal, 36-65 m limited, ≥ 65 m forbidden; ≥ 36 m mainly cross via H2 / H6):
  - arrivals to west-side stands from the east runway get a 5 km cost per 18R/36L crossing when span < 36 m: 186 of 200
    such routes use N/BN or S/BS (extra length median 1,667 m); spans 36-65 m cross at H2 (south flow) / H6 (north flow);
  - **which end-around** (rev. 2, review L3): the AIP mirror text (local copy, AD 2.20 2.3.3.1-2) names both routes
    without a flow rule and adds visual screens 388 m beyond each 18R/36L end and four compulsory holding points HP1-HP4
    on them. So the shortest route stays, and the end-around segments inside an **18R/36L end box** (behind the start of
    roll: jet blast; beyond the far end: the low climb-out) become runway resources of the departures (§4.5), with an
    inferred holding point before each box (HP1-HP4 are not in the data). In north flow 56 of 100 west-side arrivals take
    ROUTE-SOUTH (review `flow_check.mjs`): they wait at that hold during a 36L roll start.
- **Route table** `data/sha_routes.js` (`tools/sim/build_routes.mjs`, the same router in node, deterministic):
  - departures: 164 stands × 4 take-off ends; arrivals: per stand × landing end × the exits the exit model can pick
    (two per side, §4.2); plus the **F4552 variant** for the routes that use a link closed by it;
  - routes as link-id arrays plus per-route integer offsets; about 1,300-2,000 routes, 0.3-0.6 MB [inf] (the fully
    enumerated table is 8,528 routes, about 2 MB [obs]);
  - **baked integer geometry** (rev. 2, review M5): per link the core length; per allowed transition (link in, node, link
    out) the fillet trims on both links, the arc length and the radius, all in **integer cm**; per link the block
    boundaries (§4.5); per runway end the integer final and take-off geometry. The browser commit needs no trigonometry;
    positions for display are evaluated from the same data with floats;
  - the file carries the taxigraph's sha256 (and `SOURCES_routes.json`, B); on a mismatch, or for an unknown closure, the
    router routes live with the same integer pipeline and caches.
- **Holds:** runway-holding positions OSM 37 [obs] + 34 inferred at 90 m (`hold_inf`). Every route marks the crossing
  holds, the line-up hold and the end-box holds. Arrivals stop 5 s [inf] before turning onto the lead-in (AD 2.20
  3.2.2.2, `aip_facts.stop_before_leadin`).

### 4.2 Runway entry and exit choice

- **Exits** (`router.exits(end)`), from the runway end [obs]: 18L: B4 1,977 m, A3 2,073, B5 2,337, A4 2,407, B6 2,737;
  36R: A2 1,851, B3 2,069, A1 2,274, B2 2,409, B1 2,826; west runway: 18R B8 / C3 1,942, C4 2,296; 36L B7 / C2 1,972,
  C1 2,315. They agree with F4301 (first rapid exits from the DTHR: 18L 1,850 m B4 / 1,890 m A3; 36R 1,715 m A2 /
  1,950 m B3) within about 20-85 m once the 100 m displacement is removed. **Unnamed rapid links before the F4301 first
  exits** (18L at 1,549 m, 36R at 1,744 m from the end, `route_check.mjs`) are excluded (rev. 2, review L1).
- **Model** [inf]: touchdown at the PAPI abeam point (`papi.inward_of_dthr_m`: 474 m on 18L/36R, 393 m on 18R/36L) ± 60
  m; decelerate at a_dec(type) (narrow 2.0, wide 1.7 m/s², with braking from touchdown) to 20 m/s at the exit; A-side
  exits for T1 and the east aprons, B-side for T2 and the west aprons; the first exit on that side the stopping distance
  reaches, else the second (seeded 70 / 30 when both are reachable).
- **ROT** (rev. 2, review L1) is measured as the AIP states it: "within 50 s **after touchdown** via the first or second
  rapid exit" (AD 2.20 2.1.4.2), touchdown → tail clear of the runway-holding position.
- **Entries:** wide-bodies line up at the full-length end connector; code C may use the intersection 18R via H2 / 36L
  via H6 (AD 2.20 2.1.7; TORA 2,988 m, `aip_facts.declared_m.intersection`), seeded p = 0.3 [inf]; line-up within 60 s of
  the holding position (AD 2.20 2.1.5).

### 4.3 Pushback, start-up, bridges

- **Push.** Along `stands[].push.pts` (the reversed own lead-in to the first lane, median 81 m), at 1.2 m/s with
  0.3 m/s² [inf]; the tail is then turned onto the lane in the direction the departure route needs (`tail_headings`).
  Option A stands push on as §4.1. AIP short facts (232-235 / 262-265 / 286-290 to holding points on L12 / L13 / L14,
  401-416 to L11): L11, L12 and L14 are not in OSM, so those pushes end at the first lane (data flags, stands.md §5).
- **Tug.** A towbarless tug mesh (new, D; about 7 × 3.5 × 1.7 m [inf]) under the nose gear from push start to push end
  + 20 s, then drives 30 m away and fades.
- **Start-up.** At the push end the aircraft holds 90 s [inf] with the beacon on, then taxis.
- **Bridges, stairs, bus** (rev. 2, review H2, M7): from the gate-timing table (§1.5): dock at on-block + 20 s; undock
  with `undockEarly` at off-block − max(150 s, `undock_s` + 15 s); `setOccupant(g, null)` at push start; the push never
  waits on the runtime. **Service windows** [inf]: `turn` from on-block to on-block + 30 min and from off-block − 45 min
  to off-block; in between, an airframe on the ground longer than 100 min is **cold** (`setService(g, 'cold')`: no GSE,
  stairs or bus; bridges stay docked at contact stands). Night-stoppers are cold until off-block − 45 min.

### 4.4 Speeds, accelerations, turn radii (`js/sim/perf.js`, `path.js`, `traj.js`)

| Quantity | Value [inf unless noted] | Basis |
|---|---|---|
| Taxi, straight, on taxiways A / B / C / D | ≤ 12 m/s (≈ 23 kt) narrow, 10 m/s wide | common practice; under sfo3d's caps |
| Apron taxilanes | ≤ 7 m/s; lead-in ≤ 3 m/s, last 15 m ≤ 1 m/s to the stop | as above |
| Turns | v ≤ √(a_lat R), a_lat = 1.0 m/s² | comfort bound |
| Longitudinal, taxi | +1.0 / −1.5 m/s², jerk ≤ 1 m/s³ (display smoothing only) | below sfo3d `ctlGround` caps 1.8 / 2.0 (traffic.js:2795) |
| Minimum radius | R_min = 0.27 × wheelbase; junction fillets R = 45 m (narrow) / 55 m (wide), cut to the room on the legs, never < 1.6 R_min | traffic.js:2782 and :457 (`Rlo`) |
| Rapid exit | entry ≤ 25 m/s, decelerating | ICAO RET design speed 93 km/h for code 3/4 (from memory: unverified) |
| Take-off | accelerate 2.0 (narrow) / 1.7 (wide) m/s² to Vlof = `LIFTOFF_KT` (traffic.js:154) or 150 / 165 kt by length; rotate 3°/s to 8°; liftoff | sfo3d prior; roll ≤ TORA − 400 m checked |
| Climb-out | γ = 7° to 3,000 ft, straight on the runway heading; fade at 15 km | the SID turn "at 200 m" of 36L/36R (AD 2.20 1.5) has no published direction here: not drawn |
| Approach | 3° glide path to the PAPI abeam point (TCH ≈ 25 / 21 m), straight-in from 12 km; Vapp 135-145 kt by type; gear down by 600 m AGL, flaps by speed (sfo3d `attitude` :3149-3152) | AIP (mirror) PAPI 3° (aip_facts) |
| Flare, landing | flare from 12 m, touchdown sink 1 m/s, decel as §4.2 | sfo3d `attitude` flare rule (:3135) |

- **Why the approach starts at 12 km.** The extent ends only 1,850 / 1,860 / 1,990 / 2,230 m before the DTHR of 18L /
  36R / 18R / 36L [obs, `pave_check.mjs`]: aircraft would pop in on very short final. An airborne simulated aircraft is
  not ground detail, so the Q3 extent rule does not apply [inf].
- **Path build.** The baked route geometry (§4.1) gives s in cm with v_max(s) per piece (link kind, fillet radius);
  the speed profile is a forward-backward pass with accel and brake limits and stop points (holds, block waits); the
  result is piecewise constant-acceleration segments with integer ms boundaries (`t = (−v0 + √(v0² + 2 a d)) / a`).
- **Gear tracks.** OSM junctions have no fillets (stands.md §6): the ±4 m gear tracks of the raw centrelines leave
  pavement on 12 links (110 m), ±6.5 m on 15 links (195 m) [obs]. Fillets move the main gear inside the corner, so the
  test samples the actual gear points (§5).

### 4.5 Separation and conflicts: prioritised reservations

Every committed movement writes reservations; a later commit must fit around all of them. Resources:
- **Blocks** (rev. 2, review M3). B splits every link into blocks of ≥ 60 m (a shorter link is one block); a block is
  occupied from the nose entering to the tail leaving + 5 s, and is exclusive. A follower therefore waits at the end of
  the last free block behind its leader: a **spatial queue** with stop positions, at v = 0 included. The follower's
  profile is built against the leader's committed trajectory (pure and deterministic, not runtime car-following):
  compute the free profile, find the first block whose window conflicts, add a stop at that block's entry until the
  leader's tail leaves, recompute; ≤ 10 iterations [inf].
- **Two-way links** are exclusive for the whole link against the opposite direction (no head-on meeting on a lane).
- **No-stop zones:** junction boxes (the fillet region + 15 m) and runway strips are blocks in which no stop may be
  planned: a movement enters only when it can traverse the whole no-stop sequence (e.g. crossing hold → first block
  beyond the runway).
- **Runway resources:** per runway, arrival occupancy [threshold − 30 s, vacated], departure [line-up, past the far
  crossing node], crossing [enter strip, clear strip]; the **18R/36L end boxes** of the end-arounds (§4.1) are blocked
  for [line-up − 10 s, roll start + 40 s] at the start end and [liftoff, liftoff + 30 s] at the far end [inf].
- **Flow corridor** (rev. 2, review M2): one resource per side of the field (north, south), covering both runways'
  approach from 12 km and climb-out to 15 km. Each airborne segment reserves it with a tag (inbound / outbound). A
  corridor holds one tag at a time, with ≥ 120 s between the last movement of one tag and the first of the other [inf].
  In normal segregated flow each corridor carries one tag, so only a direction switch makes it bind: the first
  new-direction arrivals wait for the last old-direction climb-out to pass 15 km, as ATC stops arrivals before a change.
- **One-at-a-time lanes:** Y1-Y3, M1-M6, L15-L17 (AD 2.20 3.1.5, §4.1).
- **Adjacent stands:** no simultaneous entry / push / one in and one out at neighbouring stands (§2.4).
- **Stands, holds included** (rev. 2, review M6): the occupancy [on-block, off-block (+ push clear)] is a reservation.
  A departure that cannot leave waits **at its stand** up to the next occupant's planned on-block − 10 min; beyond that
  it pushes and waits on a lane block outside every no-stop zone. Because the arrival commits after its stand's
  departure (§1.4), it sees the final occupancy and is re-allocated at its commit if the stand is not free.

**Why planning always completes.** Every earlier reservation is a finite interval, and every commit has a feasible
fallback: a departure can wait at its stand or on a lane block; an arrival can hold in the air (its touchdown moves
later; the corridor and runway resources are re-checked). The dependency order means no commit ever needs a stand that
a later commit releases. The unresolvable case (no fallback within 2 h) is counted and the movement dropped from the
day (`stats.dropped`, target 0). `test_day.mjs` checks the result (§5).

**Rejected:** runtime reactive spacing (car-following: not a pure function of t); check-only (no avoidance: overlaps on
the shared parallels A / B at peak); full multi-agent optimisation (unnecessary at about 800 movements a day, harder to
make deterministic).

### 4.6 Runway operations

- **Arrivals on the east runway.** Threshold spacing ≥ max(5 km, wake minimum) and the previous arrival vacated
  (AIP (mirror) AD 2.22 4.1: 5 km within 10 NM if the leader vacates within 50 s on a dry runway). Wake minima from
  ICAO Doc 4444 from memory (unverified): Heavy → Medium 5 NM, Heavy → Heavy 4 NM; categories in `perf.js`. Peak demand
  33.7 arrivals/h = 107 s mean spacing against 69 s at 5 km and 140 kt.
- **Departures on 18R/36L.** ≥ 60 s between departures, 120 s behind a Heavy [inf, Doc 4444 from memory]. No roll start
  within [touchdown − 40 s, touchdown + 10 s] of an arrival on the 365 m parallel [inf].
- **Crossings of 18L/36R** (rev. 2, review M4). The original "no arrival within 2 NM and runway clear" rule with
  arrivals committed first gives long waits (review `crossing_mc.py`: 21:00 median 253 s, P90 929 s). Revised rule [inf;
  Doc 4444 7.10 from memory: a landing aircraft does not cross the threshold until the runway is clear]:
  - the crossing must be complete ≥ 10 s before the next arrival crosses the threshold (`crossClearS` 10);
  - it may start behind the landing aircraft once that aircraft has passed the crossing node (near-end crossing:
    threshold + 12 s), or at threshold + 20 s for a node beyond the arrival's committed exit (its trajectory proves it
    never gets there);
  - waiting crossers at one node cross as a batch (40 s + 15 s per extra aircraft).

  Monte Carlo (`crossing_mc3.py`, synthetic, 20,000-28,000 crossings): 21:00 p50 13 s, p90 56 s, p99 70 s; 16:00
  p50 2 s, p90 54 s; 10:00 p50 0 s, p90 51 s. The review's gap-stretch fix is **not** the default: with the old 2 NM rule
  `crossing_mc2.py` gave p90 818 s with batching and 1,461 s with stretching in the saturated 21:00 hour; it stays an
  optional parameter `stretchForCrossers` (off). `day_report.mjs` reports crossing waits; target p90 ≤ 5 min.
  Never vacate via H3 / H4 / H5 (AD 2.20 2.3.2). Wide-body arrivals cross 18R/36L at H2 / H6 between departures.
- **Direction switch:** §1.4 (event) and §4.5 (corridor).
- **Go-around:** optional, `goAroundRate` default 0 [inf].
- **Low visibility.** CAT I PALS only (AIP (mirror) AD 2.14). Below an RVR / visibility of 550 m, arrivals hold or divert
  [inf]; 84 reports in 3.9 years were below 1,500 m (sources_sim.md §5.2).

---

## 5. Physical plausibility and the test suite

`tools/sim/test_day.mjs` (C2) runs a whole day in node; `js/sim/*` imports only `js/geo.js`, `js/aircraft/types.js` and
`js/env/wx/metar_zsss.js` (all three import in node 22 [obs]); the gate-timing table is data. Days and plans:
1. 12 Nov, public; 2. 20 Nov (the snapshot day), public; 3. a summer south-flow day from the IEM archive [inf choice];
4. a day with a direction switch at a peak hour (from the IEM archive); 5. 12 Nov with the local overlay (local run
only; counts only).

| Check | Rule | Target |
|---|---|---|
| Counts per hour (rev. 2, review L11) | **scheduled** take-offs and landings vs the profile; **simulated** (delayed) ones vs the profile convolved with the delay distribution | \|n_h − target_h\| ≤ max(2, 0.1 target_h) per hour; day total ±2 % |
| Night | movements 01:00-05:59 | only delayed ones; no arrival 01:00-06:00 while F4551 is in force |
| Stands (rev. 2, review M6) | occupancy intervals incl. 10 min buffer **and holds**, excl pairs, closures, span / length fit; per side × class maxima vs capacity | 0 violations; 0 double occupancy; unplaced 0 on days 1-4 |
| Taxi separation | min planform distance between two moving aircraft (forked `overlaps` with margin); block exclusivity | ≥ 10 m [inf]; following gap ≥ 60 m while v > 2 m/s |
| Queues (review M3) | stopped aircraft at a hold or block boundary | 0 planform overlaps between stopped aircraft |
| Wingtip vs parked | taxiing planform vs parked planforms | reported against MH 5001-2021 table 4.9.5 (`caac_markings.js` `separation`); ≥ 4.5 m (C) / 7.5 m (D-F) except the 25 stand pairs already tighter (stands.md §3) |
| Runway | never two aircraft inside one runway strip except an arrival rolling out behind a crossing that has cleared, and a departure behind a vacated arrival | 0 incursions |
| Airborne (rev. 2, review M2) | opposite-direction airborne pairs in one flow corridor at the same time; same-runway in-trail pairs | 0; ≥ 5 km at the threshold, ≥ 2.5 NM or 1,000 ft in-trail (the segregated parallel pair is checked by the runway rule) |
| Wake / spacing | arrival pairs at the threshold, departure pairs at the roll start | 100 % |
| ROT (review L1) | touchdown → tail clear of the runway-holding position | ≤ 50 s for ≥ 90 %, ≤ 70 s for all |
| Crossing waits (review M4) | wait at the crossing hold | p90 ≤ 5 min |
| Pavement | every main-gear and nose-gear point, sampled at 1 s, inside the drawn pavement polygons (`tools/sim/pave.mjs`: `sha_airport.surfaces` + aprons + helipads + `sha_buildings3d` airside / stand-head fills, the inputs of gates.js `vectorPavement`); option A pushes with the swept planform | 0 points off |
| Kinematics | \|a\| within caps, R ≥ R_min, no position step > v·dt + 0.1 m, heading continuous, speeds ≤ the link-kind limits | 0 violations |
| Determinism (review M5) | two runs; a run from t0 vs `commitUntil` in 3 jumps; node vs Chromium (`jobs/traffic.mjs` computes the hashes in the page) | identical `plan.hash`, commit hash and state hashes at 50 sample times. **WebKit (iOS) is not installed here** (`/opt/pw-browsers`: Chromium only): JavaScriptCore agreement is **untested**, and the doc says so until a WebKit run exists |
| Cost | full-day commit; plan build; `stateAt` with the peak count | ≤ 300 ms; ≤ 200 ms; ≤ 2 ms (node, this sandbox) |
| Memory (review L12) | heap after a full-day commit | ≤ 40 MB [inf] |

- **Pavement baseline.** `pave_check.mjs` [obs]: link centrelines sampled every 5 m leave 18 of ~25,500 samples off, on
  9 links (worst 35 m on one east-apron lane near x 314, z −985); the 164 push links and all stop nodes are on pavement.
  In the browser, `world.pavedAt` needs a canvas; E exposes gates.js `vectorPavement` as `SHA.qa.pavedVec(x, z)` (review
  L6), and the harness compares `pave.mjs` with it on 10,000 points (0 disagreements expected: the same polygons).
- **Gate adapter tests** (E, `tools/sim/test_gate_sync.mjs`, node + GL stub): `resetTo` after a backward jump leaves no
  animation, park or hold with a future time; a forward play and a jump to the same t give the same engine state
  (extension per stand, occupants, services); `undockEarly` at the table's lead leaves `extension(g) = 0` before the
  push starts for every stand × type in the table.
- **Render checks** (D, `jobs/traffic.mjs`, `SOFTGL=1`, deviceScaleFactor 1, `identity=0`): overview at 21:00 local
  (peak) and 07:30 (morning bank); stand 233 docking (on-block, +20 s, +60 s), undock and push; remote stand 404 with
  stairs and bus, and the same stand cold at night; option A push at 238A (top, `debug=push`); `rwy:36R` with two
  spaced arrivals; the 36L holding queue; an H4 crossing; an end-around arrival on S; 02:00 night (parked, cold); a
  backward scrub (no stale bridge); phone time bar and card; laptop list and card.

---

## 6. UI

### 6.1 Labels, list, card (exact texts)

| Tier | 3-D label (`ui.updateLabels`) | List row (`renderList`) | Card source line |
|---|---|---|---|
| `oe` | `MUnnnn` / sub `A21N` | flight · type · chips `obs elsewhere` + `inf` | "Identity observed elsewhere: open ADS-B saw this flight outside the Shanghai coverage gap on 12 Nov 2026. Its time at Hongqiao is inferred (±N min, 1σ). Stand, taxi route, runway and position are simulated." N = the record's own `sigma_s` / 60, rounded (rev. 2, review M10). Rows: Callsign `CESnnnn`, Registration `B-nnnn`, Operator, Type |
| `pub` | `MUnnnn` / sub `A333` | chip `published` + `inf` | "Flight number from the published Hong Kong airport schedule of 13 Nov 2026 (Airport Authority Hong Kong, via DATA.GOV.HK). Its time at Hongqiao is inferred from it; type and registration are not published." (TSA: "…Taipei Songshan Airport schedule of 14 Nov 2026 (CAA Taiwan, OGDL v1.0)…") |
| `inf` | `CES · A321` (italic, dimmer) | `China Eastern · A321` + chip `inf` | "Simulated flight (inferred): airline and type follow the Hongqiao mix. No flight number or registration is known for it." |
| `rep` (switch on) | `MUnnnn*` | chip `seen other days` + `inf` | text of §2.6 |
| continuation of an `oe` airframe | airline · type | chip `inf` | "Same aircraft as the observed arrival MUnnnn (12 Nov 2026), parked here by inference. This departure was not observed: no flight number or registration is shown." |

- **UiTrack** (rev. 2, review M8; frozen in §7.1): `labels.js` builds it from `AcState` and `labelFor`; `ui.js` reads
  `tr.disp.valid`, `tr.stale`, `tr.cs.display`, `tr.info.reg`, `tr.hex`, `I.icao`, `I.altBaro`, `D.gs`, `tr.gate`,
  `tr.cs.airline.name`, `tr.type.full` (`ui.js:154-195`), so every one of them is defined; `hex` = the airframe id, never
  shown (the title always comes from `cs.display`). `phaseLabel(tr, now)` is called with **sim time** (D edits
  `ui.js:159, 179`).
- **Every card** also shows: phase, stand (gate label; "overflow, inferred" where §2.4 put it), runway, speed,
  altitude, "Source: inferred (simulated)" (`ui.js` maps `tr.src === 'inf'`, :164), the model note (stand-ins, §2.3).
- **Stand card:** "Occupant: …", service (turn / cold) and the next planned movement.
- **Legend line** `traffic` (replacing "Traffic: none yet", shell.js `legendLines`): "**Traffic:** simulated from a day
  plan `inf`: every position, stand, taxi route and runway is inferred. Real identities appear only on days with flights
  observed elsewhere (open ADS-B outside the Shanghai coverage gap): `obs elsewhere`, time at Hongqiao inferred. No
  registration is invented."
- **Day line** in the note: "Identities: N flights observed elsewhere on this day (local data)" or "No real identities
  for this day: flights observed elsewhere exist for 10 and 12 Nov 2026 only." Plus a small "plan · commit" hash pair
  (first 6 hex of each) so two devices can be compared.
- **Runway line** (rev. 2, review M11): while traffic runs, the shell's runway line reads `SHA.sim.runway(t)` (latency,
  start anchor, NOTAM closures) instead of its own `runwayMode(E.reports, {rule, tMs})` (`shell.js:85`); without traffic
  it keeps its Phase 2 behaviour. The rule switch (`shell.js:200`) re-commits the day.
- **About** gains a "Simulated traffic" section: the tiers, the hourly profile basis, the runway rule and its agreement,
  the NOTAM date, the overflow and cold-stand rules, the attribution lines of §8, and "JavaScriptCore agreement untested".

### 6.2 Status pill and time controls

- **Pill** (rev. 2, review L12): `Live weather · simulated traffic` (relay, t = now); `Replay ×10 · 12 Nov`;
  `Snapshot · 20 Nov` (paused) / `Snapshot ▶ ×1`. The clock shows sim time UTC+8 (`shell.js` `tShown` :97).
- **Time bar** (`js/live/time_bar.js`): laptop: day select (today in live mode, the replay days of `SHA_SNAPSHOT.days`),
  a slider over 04:00-04:00 with hour ticks and the night band, play / pause, ×1 / ×10 / ×60, "Live". Phone portrait: a
  44 px row above the sheet peek with play / pause, speed and "Live"; tapping the clock opens the slider. Keys: space,
  `[` `]`, `L`.
- **Speed.** Up to ×60 the bridges animate at sim time; above ×60, or on a jump > 120 s, `gate_sync.resetTo` snaps.

### 6.3 Settings and URL

- "Show simulated traffic": `?traffic=1|0` overrides; the default is `window.SHA_TRAFFIC_DEFAULT ?? true`. The harness
  sets `SHA_TRAFFIC_DEFAULT = false` through `page.addInitScript` unless `TRAFFIC=1` (E), so every Phase 2 job
  (`jobs/views.mjs:32`, `gates.mjs:193`, `markings.mjs:23`, `buildings.mjs:46`, `ui.mjs:15`, `integration.mjs:65, 82`)
  renders as before without being edited (rev. 2, review M14).
- `?park=` and traffic exclude each other: with `?park=` the traffic extension does not start (note "DEBUG ?park=:
  traffic off"), and `SHA.qa.park` refuses while traffic runs.
- "Flight numbers seen on other days" (off, §2.6). `?identity=0` (§3). The runway rule switch exists (shell.js).

### 6.4 Performance budget

- **Aircraft count.** 80-120 night-stoppers plus the day's turnarounds: at most about 150 airframes; moving at peak
  about 13-15, up to about 25 with queues [inf].
- **LOD:** existing `LiveAircraft` (real model ≤ `lodDist`, one-draw body beyond, none past 14 km); the extension caps
  real models to the nearest N per tier (low 12, medium 24, high 40, ultra 80); the selected aircraft is always real.
  Shadows within `shadowDist` (700-2,500 m). Labels: at most 30, every 100 ms.
- **CPU.** `stateAt` ≤ 2 ms laptop; target ≤ +4 ms JS frame time at peak (Phase 2: 2-4 ms, integration.md §4).
- **Gate rebuilds** (review M7): every `setOccupant` / `setService` marks the engine dirty, and `build(now, true)`
  re-places the GSE of every occupied stand (:2350-2370). With the per-stand GSE cache (E) only the changed stand and
  its neighbours are re-placed; target full rebuild ≤ 30 ms on the laptop tier, measured by E at 130 occupied stands.
  D batches gate events per frame (one rebuild).
- **Memory** (review L12): commits keep compact segments and per-block times only; 1 m path samples are built lazily for
  the active movements (LRU of 60); no per-movement Float32Array path is kept for the day (about 40 kB each would be
  about 30 MB).
- **Phone frame time** is unmeasured (integration.md open issue): measured with the harness iPhone 15 profile at the low
  tier, and stated as such.

---

## 7. Implementation packages

Interfaces are frozen by this section; packages code against them and may add fields, never rename them.

### 7.1 Interfaces

```js
// ---- inputs and plan (A)
// js/sim/inputs.js   simInputs(win = globalThis) -> SimInputs
SimInputs = { v: 1, built, src: 'inf', profile: {arr: [24], dep: [24], basis}, totals: [{from, to, perDay, basis}],
  weights: {complement: {airline: w}, fullDay: {airline: w}}, typeMix: {complement: {airline: {icao: n}}, fullDay: {...}},
  turnaround: {p10, p50, p90, minNarrowS, minWideS}, terminals: {T1: [...airlines], intl: [...]}, delays: {...},
  published: {hkg: [{flight, role, far, tFar, day}], tsa: [...], src}, notams: [{id, kind, target, windows}], params: {...} }
// js/sim/plan.js     buildDayPlan({day, inputs, stands, overlay = null, notams, gateTimes, prevEnd = null, opts}) -> DayPlan
DayPlan = { v: 1, day, t0, t1, seed, hash, version, rule, weightSet: 'complement' | 'fullDay', src: 'inf',
  tiers: {oe, pub, rep, inf, cont}, stats: {byHour, bySide: {T1: {max, cap, wideMax, wideCap, elMax, elCap}, T2: {...}},
    contactShare, crossSide, unplaced, diverted},
  airframes: [{id: 'af:17', airline, icao, model, tier, reg /* only with an overlay */}],
  movements: [{id: 'm:0123', slot: 'oe:<uid>' | 'pub:<n>' | 'rep:<flight>' | 'inf:<n>' | 'cont:<n>', role: 'arr' | 'dep',
    af, airline, icao, model, wake, tier, tSched, tRwy, delayS, stand, side, contact, overflow, prev, next,
    startsParked, endsParked, ident /* overlay key | null */, sigmaS /* oe only */}],
  stands: {'<name>': [{from, to, mv, af, service: [{from, to, mode}]}]}, closures: {stands, windows}, notes }
// js/sim/identity.js checkOverlay(obj) -> Overlay | null;  labelFor(movement, overlay, opts) -> {title, label, sub, chips, lines}
Overlay = { v: 1, day, tier: 'oe', note, licence, records: [{uid, role, airline, cs, flight, reg, type, operator, far, t_sha, sigma_s}] }

// ---- routing and kinematics (B); all lengths cm, speeds cm/s, times ms (integers)
// js/sim/router.js   makeRouter(taxigraph, {table, closedLinks}) -> {departure(stand, end), arrival(exitId, stand), exits(end)}
Route = { kind: 'dep' | 'arr', stand, end, exitId, links: [[linkId, fromNode]], lenCm,
  pieces: [{kind: 'line' | 'arc', lenCm, rCm, vmaxCms, linkId}], blocks: [{id, s0Cm, s1Cm, noStop}],
  push: {lenCm, optionA: {run: [linkId], node, swing: linkId, turnDeg} | null},
  holds: [{sCm, node, kind: 'rwyhold' | 'lineup' | 'leadin' | 'endbox'}], crossings: [{runway, node, sCm, nearEnd}], lineup: {node, sCm} }
// js/sim/perf.js     perfOf(icao) -> {wake, vappCms, vlofCms, aToCms2, aDecCms2, taxiMaxCms, spanCm, lenCm, wheelbaseCm, src: 'inf', basis}
// js/sim/traj.js     groundTraj(route, perf, t0, {vStart, vEnd, stops}) -> Traj; approachTraj(end, perf, tTd); takeoffTraj(end, entry, perf, tRoll);
//                    evalTraj(traj, t, out) -> pose   (display: floats allowed)
Traj = { t0, t1, segs: [{t0, t1, s0Cm, v0Cms, aCms2, kind}], route /* ref */, phases: [[t, phase]] }
pose = { x, y, z, hdg, pitch, roll, gs, vs, ground, gear, flaps, spoilers, phase }

// ---- gate engine (E)
// data/sha_gate_times.js  window.SHA_GATE_TIMES
GateTimes = { v: 1, inputs_sha256_16, src: 'inf', note, stands: {'<name>': {'<typeKey>': [dock_s, undock_s, hurry_s, pushClear_s]}} }
// js/live/gate_system.js (additive)  resetTo(t, occupants); setService(g, 'turn' | 'cold', t); now (time source)
// js/live/gate_sync.js   createGateSync(gateSys, gates) -> { apply(events), resetTo(t, standStates), info() }
// js/live/gates.js       export gateTimes(sys, gates, typeKeys) -> GateTimes;  SHA.qa.pavedVec(x, z)

// ---- scheduler (C1)
// js/sim/sim.js      createSim({plan, router, perf, gateTimes, wx: {reports}, notams, params}) -> Sim
Sim.commitUntil(t, budgetMs = Infinity) -> {done, committed, pending}
Sim.stateAt(t) -> {t, aircraft: [AcState], stands: Map<name, StandState>, runway: RunwayState}
Sim.runway(t) -> RunwayState = {dir, flow, arr, dep, closed, rule, report, switchedAt, tag: 'inf'}
Sim.events(tA, tB) -> [{t, kind: 'onblock' | 'dock' | 'docked' | 'service' | 'undock' | 'pushstart' | 'pushend' | 'offblock' | 'takeoff' | 'touchdown' | 'switch', mv, stand, data}]
Sim.hashes() -> {plan, commit};  Sim.stats() -> aggregate counters (waits, crossings, crossSide, dropped)
AcState = { id: af, mv, airline, icao, model, tier, phase, stand, runway, src: 'inf', ...pose }
StandState = { af, typeKey, icao, freighter, pose: {nose: [x, z], dir: [dx, dz]}, state: 'empty' | 'docking' | 'docked' | 'early' | 'pushing',
               since /* ms, sim */, service: 'turn' | 'cold' }

// ---- app (D)
// js/live/sim_clock.js new SimClock({mode, t0, t1, now}) -> {now(wall), mode, speed, setT(t), setSpeed(k), live(), onJump(fn)}
UiTrack = { hex: af, id: af, src: 'inf' | 'obs', tier, stale: false, cat: 'arr' | 'dep' | 'ground' | 'other', phase,
  disp: {valid: true, x, y, z, ground, gs, hdg}, info: {icao, reg /* oe + overlay only */, altBaro /* ft | null */, flight},
  cs: {display, airline: {name}} | null, type: {full}, gate: {name, label} | null, chips, lines, modelNote }
window.SHA.traffic = { tracks: Map<af, UiTrack>, identity: 'on' | 'none', sim, plan: {day, hash, tiers, stats} }
// URL: ?traffic=1|0  ?sim=<ISO>  ?speed=0|1|10|60  ?day=YYYY-MM-DD  ?identity=0

// ---- snapshot (A writes, D reads); data/sha_snapshot.js
SHA_SNAPSHOT = { ...existing fields, traffic: {kind: 'sim', day: 'YYYY-MM-DD', planVersion},
  days: [{day /* operating day, 04:00 local start */, t0, t1, src: 'awc' | 'iem' | 'awc+iem', complete: bool,
          metars: [{obsTime, receiptTime /* ISO | null */, rawOb}], notes}] }
```

### 7.2 Packages

| | Owns (new files) | Edits allowed | Depends on | Size |
|---|---|---|---|---|
| **P3-A** Plan, identity, inputs | `tools/sim/{build_sim_inputs,observed_overlay,test_observed_overlay,audit_identity}.py`, `tools/sim/test_plan.mjs`, `js/sim/{rng,inputs,plan,alloc,identity}.js`, `data/sha_sim_inputs.js/.json`, `data/SOURCES_sim.json`, `docs/phase3/plan.md` (+ aggregate plots) | `sha_live_server.py`, `tools/live/test_relay.py`, `tools/live/build_snapshot.py` (+ regenerated `data/sha_snapshot.js/.json`) | sources only; `gateTimes` optional (stub) | 7 h |
| **P3-B** Routing and kinematics | `js/sim/{router,perf,path,traj,bodies}.js`, `tools/sim/{build_routes,test_router,test_traj}.mjs`, `data/sha_routes.js/.json`, `data/SOURCES_routes.json`, `docs/phase3/movement.md` | none | taxigraph, stands, airport | 7 h |
| **P3-E** Gate and time adapter + harness | `js/live/gate_sync.js`, `tools/sim/{build_gate_times,gl_stub,test_gate_sync}.mjs`, `data/sha_gate_times.js/.json`, `jobs/gate_sync.mjs`, `docs/phase3/gates_time.md` | `js/live/gate_system.js` (additive methods only), `js/live/gates.js`, `js/scene.js` (:30 time source), `livetest.mjs` | Phase 2 fix round 3 committed | 6 h |
| **P3-C1** Scheduler core | `js/sim/{runway,notam,resv,sched,sim}.js`, `tools/sim/test_sched.mjs`, `docs/phase3/schedule.md` | none | A (`DayPlan`), B (router, traj, routes), E (`GateTimes`) | 8 h |
| **P3-C2** Day suite | `tools/sim/{pave,test_day,day_report,fixture_sim}.mjs`, `docs/phase3/day_suite.md` (+ aggregate plots) | none | B (traj); C1 for the final runs (until then `fixture_sim.mjs`) | 5 h |
| **P3-D** App and UI | `js/live/{traffic,sim_clock,time_bar,labels,sim_stub}.js`, `jobs/traffic.mjs`, `docs/phase3/app.md` + renders | `js/live/traffic_api.js`, `js/live/entry.js`, `live.html`, `js/env/clock.js`, `js/env/app_env.js`, `js/live/app.js`, `js/live/ui.js`, `js/live/shell.js`, `js/live/about.js`, `live.css` | A, E; C1 through `sim_stub.js` (deleted at integration) | 8 h |
| **P3-F** Artifact and delivery | `tools/live/build_artifact.mjs`, `jobs/artifact.mjs`, `docs/phase3/artifact.md` | none (output in `out/artifact/`) | D (the app), E (harness); spike independent | 5 h |
| **Integrator** | `docs/phase3/integration.md` | wiring only, after the owners finish; deletes `sim_stub.js`; proposes CLAUDE.md edits to the lead | all | 4 h |

File ownership is disjoint: no file appears in two rows. Requests across packages go through the lead (e.g. D needs
a harness option → E). `js/live/aircraft.js` is read, not edited (the decal works through `SHA.traffic.tracks`).

**Order.**
- **Gate:** Phase 2 fix round 3 (`gate_system.js`, `gates.js`, `shell.js`) is committed by the lead before E and D start.
- **Wave 1:** A ∥ B ∥ E.
- **Wave 2:** C1 ∥ C2 ∥ D ∥ F. C2 develops against B's trajectories and `fixture_sim.mjs`, D against `sim_stub.js`
  (the frozen `Sim` interface), F starts with a 30 min publish spike.
- **Integrator** last. Critical path B → C1 → integrator (about 19 h plus waits).

**Acceptance criteria.**
- **P3-A**
  - `test_plan.mjs`: scheduled day totals within ±2 % and hourly within the §5 band; 0 slots 01:00-05:59 except
    delays; every type valid in `TYPE_MODELS` or with a stand-in `model`; 0 overlap / excl / class / closure violations;
    occupancy per side × class within capacity or counted overflow, unplaced 0 on 12 and 20 Nov; contact share per side
    reported (60-85 %); a non-observed day's airline and type mix within ±3 points of the observed days' full plans
    (`fullDay`); 0 tier-2 delays; identical hash on two builds; plan build ≤ 200 ms (node).
  - The public 12 Nov plan has no identity field; with the overlay, tier 2 = the identified count minus the
    out-of-window ones (counted) and the continuations are reported per side.
  - `test_observed_overlay.py`: field allow-list, `type` format, no 6-hex value, `{available: false}` without files, bad
    `day`, non-loopback host without `--identity-lan`; the relay tests still pass, plus 4 new.
  - `audit_identity.py` runs on the package's own diff with 0 hits outside the allow-list.
  - `data/sha_snapshot.*` carries `days[]` for 10 / 12 / 13 / 14 / 20 Nov with `complete` true: one-off AWC pull for
    13 Nov 18:00Z - 14 Nov 20:00Z and 19 Nov 18:00Z - 20 Nov 20:00Z (the AWC database keeps 30 days; two requests, at most
    one per 10 min), since the local cache ends 14 Nov about 05:00Z and the snapshot list stops at its instant (review L4).
- **P3-B**
  - 164 / 164 × 4 departure and arrival ends (option A for the 14, found by rule, same runs as `optA_push.mjs` or
    shorter); 0 runway-link use outside line-up; 0 off-list crossings; 0 foreign lead-ins; 0 turns > 100°.
  - Option A pushes: swept planform and every gear point on pavement for each stand's class reference.
  - End-around for ≥ 90 % of span < 36 m west-side arrivals, never for ≥ 65 m; 36-65 m via H2 / H6.
  - Route table deterministic (md5 twice), ≤ 0.6 MB, with the F4552 variant; baked integer geometry reproduces the float
    path length within 1 cm per piece.
  - `test_traj.mjs`: trajectories within the §4.4 limits; take-off roll ≤ TORA − 400 m; ROT from touchdown ≤ 50 s for
    ≥ 90 % of type × exit cases; glide path 3.0° ± 0.1°; no transcendental function on the commit path (a test wraps
    `Math.sin` / `cos` / `atan2` / `hypot` / `exp` / `pow` and asserts 0 calls during `groundTraj` timing).
- **P3-E**
  - `test_gate_sync.mjs` (§5) passes; `sha_gate_times.json` built in node, deterministic, all 56 bridge stands × their
    fitting model keys; boot check in the page agrees with the table on the sampled stands.
  - `items()` uses sim time while traffic runs; DEBUG park keeps `Date.now()` and is refused while traffic runs.
  - `setService(g, 'cold')` removes GSE, stairs and bus; full rebuild ≤ 30 ms at 130 occupied stands (laptop tier,
    measured); `SHA.qa.pavedVec` exported.
  - `livetest.mjs`: `TRAFFIC` default off, `IDENTITY` gate (also through `RELAY=`), refusal under `docs/`, synthetic
    overlay mock, METAR 26 h mock; every Phase 2 job runs unchanged with a clean console (`jobs/views.mjs` smoke run).
- **P3-C1**: `test_sched.mjs` on scripted cases (queue at a hold, crossing batch, handover with a held departure,
  direction switch at a peak, F4551 window, end-box hold); 0 reservation violations; commit ≤ 300 ms per day (node);
  `Sim` interface exactly as §7.1.
- **P3-C2**: every row of the §5 table on days 1-4 (day 5 locally, counts only); `day_report.mjs` writes only aggregates
  to `docs/phase3/`; the pave.mjs / `pavedVec` comparison run through the harness.
- **P3-D**
  - Snapshot, live (`RELAY=` real relay, `IDENTITY` unset) and replay scenes run with a clean console;
    `body.no-traffic` is removed; the list counts equal `stateAt`; the in-page hashes equal node's.
  - Bridges dock 20-60 s after on-block plus the table's `dock_s`, are clear before the push, and no bridge animates
    after a backward scrub; stairs and bus at remote stands; cold stands at night.
  - Card texts exactly as §6.1; the runway line equals `SHA.sim.runway(t)`; a replay day keeps its own METARs for 5 min
    of live polling; the time bar works on `DEVICE='iPhone 15'` and 1280 × 720.
  - JS frame time at peak within budget (§6.4); `?traffic=0` reproduces Phase 2; `?park=` turns traffic off.
  - Renders of §5 made and looked at; every render for `docs/` uses `identity=0` with the in-page assertion.
- **P3-F**
  - Spike first: a 3-file ES-module page in `out/artifact/spike/` served by the harness with the artifact's restrictions
    (every request outside the payload blocked) decides **module-tree publish** (default; the Artifact tool takes up to
    255 supporting files per publish, 511 per version, 16 MB per text file) or a vendored bundler
    (esbuild is not installed here; `require.resolve('esbuild')` fails) - recorded in `artifact.md`.
  - `build_artifact.mjs` assembles `out/artifact/` (≤ 16 MB per file): the 64 `js/**` modules (1.4 MB), the data
    scripts, the SHA-relevant `.sfom` models as `.wasm` supporting files (`SHA_MODEL_EXT`, entry.js :43) and the
    SHA-relevant `-lo.webp` liveries (`SHA_LIVERY_BASE`; the full `-lo` set is 184 files, 3.8 MB; review L10);
    `SHA_IDENTITY` inlined only with `--identity`.
  - `jobs/artifact.mjs`: the built artifact on `DEVICE='iPhone 15'` and 1280 × 720 with every outside request blocked:
    loads, plays a replay, shows the card; with and without `--identity` (the identity run's output stays in
    `out/phase3/local/`).
- **Integrator:** removes the D stub and wires `createSim`; runs all node tests and harness scenes; runs
  `audit_identity.py` on the whole commit set; writes `docs/phase3/integration.md`; proposes CLAUDE.md edits; the lead
  publishes the artifact (private) and commits.

---

## 8. Committed vs local, licences

| File | Commit? | Licence / attribution |
|---|---|---|
| `js/sim/*.js`, `js/live/{traffic,sim_clock,time_bar,labels,gate_sync}.js`, `tools/sim/*`, `jobs/traffic.mjs`, `jobs/gate_sync.mjs`, `jobs/artifact.mjs`, `tools/live/build_artifact.mjs` | yes | repository code; `bodies.js` carries "forked from sfo3d@e3218d6 js/live/ground.js" |
| `data/sha_sim_inputs.js/.json` | yes | Per section, like `aip_facts`. Aggregates derived from adsb.lol archives: ODbL 1.0, "Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL" (licence quote in `refs/cache/observed_elsewhere/SOURCES.json`: "license: ODbL 1.0 , use it freely, just keep it open."). VRS counts: CC0 1.0. HKG rows (section `published`): DATA.GOV.HK Terms, "You are allowed to browse, download, distribute, reproduce, hyperlink to, and print the Data for both commercial and non-commercial purposes on a free-of-charge basis on condition that … you shall also give proper attribution to the Government, the Relevant Organisations and DATA.GOV.HK"; attribution "Flight information: Airport Authority Hong Kong, via DATA.GOV.HK". TSA rows: Taiwan OGDL v1.0, "不限目的、時間及地域 … 重製、散布、公開傳輸 … 本條款與「創用CC授權 姓名標示 4.0 國際版本」相容"; attribution "Taipei Songshan Airport, CAA Taiwan, OGDL v1.0" (both `refs/cache/schedules_open/*/SOURCES.json`: redistributable true). NOTAM effect records: ids, windows and targets only (OD3 short facts). CAAC totals, SAA terminal list: facts. |
| `data/sha_routes.js/.json`, `data/SOURCES_routes.json` | yes | ODbL 1.0: a derived database of OSM through `sha_taxigraph.json` |
| `data/sha_gate_times.js/.json` | yes | derived from `sha_stands.json` (ODbL) and the gate engine; src inf |
| `data/sha_snapshot.js/.json` (`days[]` METARs) | yes | "Weather: NOAA/NWS Aviation Weather Center; Iowa Environmental Mesonet, Iowa State University. Not official NOAA material." (`refs/cache/metar/SOURCES.json`: redistributable) |
| `data/SOURCES_sim.json` | yes | every input with URL, date, sha256 and licence quote; names the `published` section as published schedule facts |
| `docs/phase3/*.md`, aggregate plots, renders made with `identity=0` | yes | - |
| `refs/cache/observed_elsewhere/**`, the overlay, `out/plan/`, `out/artifact/`, `out/phase3/local/` | **no** | OD4: identities never committed |
| `refs/cache/notam/**`, `refs/cache/aip/**` | **no** | eAIP / mirror, no licence (OD3) |

---

## 9. Risks and owner questions

### 9.1 Risks

1. **Identity leaking into the public repo.** Paths: a render with labels or a fuselage decal, a debug dump, a test
   fixture from real records, a one-flight aggregate cell, the harness relay proxy, a pixel text no audit can read.
   Mitigations: `identity=0` ≡ overlay null for every docs job, asserted in the page; the harness gate; synthetic mocks;
   cells < 3 merged; the exact-match audit (identity set, `t_sha` values, PNG text) before every commit.
2. **Gate engine coupling.** E adds methods to a 2,597-line engine that Phase 2 is still fixing; `resetTo` must rebuild
   mid-animation states exactly. Mitigations: E starts after fix round 3 is committed; additive methods only; node tests
   with the GL stub; the table's input hash.
3. **Stand capacity and plausibility on the T2 side.** 84 usable stands, 16 A330-capable and 5 B77W-capable against a
   tier-2 demand of 59-65 (13-14 wide) as turnarounds, plus the fill: tight. Overflow goes to the east side by bus
   (inferred; the real bus practice is unknown) and is counted and labelled.
4. **Determinism across engines.** Integer commits remove the known float risk, but JavaScriptCore is untested here;
   a relay outage can split live devices. The day line shows both hashes.
5. **Plausibility is inferred.** Runway rule 78-80 % out of sample; the type mix leans to trunk routes; stands by rule;
   the crossing and corridor rules are from memory of Doc 4444 (unverified). All labelled `inf`.
6. **Performance on the phone.** 150 airframes, the commit fold, GSE rebuilds and the time-sliced commit are unmeasured
   on a real device; the harness iPhone profile runs llvmpipe on a desktop CPU.
7. **Graph geometry.** Missing fillets (gear tracks off on 12-15 links), 9 centreline segments off the drawn pavement,
   87 long pushes plus 7 option A pushes over 150 m. If the fillets do not fix the pavement test, B reports the links
   to the taxigraph owner (outside Phase 3).
8. **NOTAM staleness.** The summary is from 2 Nov; F4551 ends 29 Nov; later NOTAMs are unknown ("later NOTAMs not
   known" in About).
9. **Schedule risk.** About 50 package-hours; C1 is the critical path; the artifact route (module tree vs bundler) is
   decided by F's spike.
10. **Stand-in models.** C919 drawn as an A320 until Phase 4, labelled.

### 9.2 Questions for the owner (binding decisions only)

- **Q0 (plan of record): replace sfo3d's report-driven traffic engine.** PLAN §7 (A) and arch.md §3.6 planned to adapt
  sfo3d's `traffic.js` (ingest, Hermite, phase machine, TaxiNet, matchGate). This design keeps sfo3d's stand, bridge,
  aircraft, light and physics pieces but drives them from planned trajectories, because a report classifier would only
  re-infer the plan and cannot be scrubbed (§1.1). **Recommended default: proceed with the kinematic simulator.**
- **Q1 (OD4 / Q10 f): flight numbers on days they were not observed.** A flight number seen at the same time on both
  observed days is very probably a daily schedule, but its operation today is not observed. May the app show it on
  other days, labelled "seen … on 10 and 12 Nov 2026 … not observed today", never with a registration?
  **Recommended default: no** (the setting exists, off; it needs the local overlay).
- **Q1b (OD2-3 / Q10 f): published flight numbers on their own date.** The HKG (13 Nov) and TSA (14 Nov) open schedules
  give real flight numbers for those dates under redistributable licences. Q10 f says "identity is shown only where
  observed". **Recommended default: show them on their own date only**, labelled "published schedule", no registration,
  type only where published; reversible by one switch.
- **Q2 (scope of the observed-elsewhere data).** Identities exist only for 10 and 12 Nov. A rolling scan
  (`tools/adsb/scan_callsigns.py` on each new daily adsb.lol archive, about 3.5 GiB streamed per day, ODbL, no API quota)
  would give identities for yesterday's replay. **Recommended default: not scheduled**; days are added when you ask.

---

## Resolution of the design review

Every finding of `docs/phase3/design_review.md` (2026-11-27). "Accepted (changed)" means the fix differs from the
review's proposal; the reason is in the row.

| Id | Decision | What changed (section) |
|---|---|---|
| H1 | Accepted (changed) | New package **P3-E** owns `gate_system.js` (additive), `gates.js`, `scene.js:30`, `livetest.mjs` and the new `gate_sync.js`: `resetTo(t, occupants)`, sim-time `items()`, `setService` (cold), GSE cache, DEBUG park off while traffic runs; reset on every backward jump and forward jump > 120 s (§1.4, §1.5, §7.2). Defect reproduced in node (`gate_times.mjs`: stale entry 3,612 s in the future). Changed: the review's "cannot be constructed in node" is true only without a stub; with a WebGL / canvas stub it runs (746 ms), so E builds the timing table and its tests in node. |
| H2 | Accepted | Static `data/sha_gate_times.js` (dock / undock / hurried / push-clear per stand × model, measured p50 58.7 / 46.7 / 30.4 / 1.0 s); undock with `undockEarly` at off-block − max(150 s, undock + 15 s); `setOccupant(null)` at push start; the push never waits on `pushClearEta` (§1.5, §4.3). |
| H3 | Accepted (changed) | Capacity per side × class with a table and a per-minute test (§2.4, §5); overflow order (combined positions as a data request, the 4 ref-less positions, cross-side remote labelled, unplaced removed from the plan); night-stops per side. Changed: the review's 81 / 95 is an upper reading that treats unseen continuations as whole-day stays; read as turnarounds tier 2 needs 59 / 65 (wide 13 / 14) on the T2 side, so the plan now turns unseen continuations into turnarounds except at the day's edges (§2.2 step 4; `capacity.py`). T2 usable at once is 84 (4 exclusive pairs) by our side grouping. |
| H4 | Accepted | Exact-match audit `tools/sim/audit_identity.py` against the local identity set (all registration formats, callsigns, flight numbers, addresses, `t_sha`), staged files, diff, PNG text, `docs/**`; the broadened regex as a second net with an allow-list of type designators, NOTAM ids, stands and taxiways (the raw patterns hit every `A321`); explicit allow-list of the `published` section (§3, §7.2 A). |
| H5 | Accepted | `?identity=0` ≡ overlay = null (§3); harness gate on the endpoint (also through `RELAY=`) and refusal of `IDENTITY=1` under `docs/` (E); in-page assertion before every shot (D); the decal reads `UiTrack.info.reg`, present only for tier 2 with an overlay (§3). |
| M1 | Accepted | Availability = `receiptTime` + 12 min (`obsTime` + 20 min without receipt); measured 8.2 % of receipts > 12 min (§1.4). |
| M2 | Accepted (changed) | Directional **flow corridor** per side (one tag at a time, 120 s apart) and a `switch` event that re-plans old-direction departures not yet near line-up (§1.4, §4.5); airborne check and a direction-switch test day (§5). Changed: a corridor per side covering both runways (head-on meetings involve the parallel runway), and the airborne target excludes the segregated parallel pair. |
| M3 | Accepted (changed) | Exclusive **blocks** (≥ 60 m) with stop positions, built against the leader's committed trajectory; no-stop junction boxes and runway strips; queue test (§4.5, §5). Changed: blocks instead of a continuous s-offset constraint; same effect, integer and simpler. |
| M4 | Accepted (changed) | Revised crossing rule (runway clear 10 s before the next arrival's threshold; start behind the landing aircraft; batches): p90 56 s at 21:00 (`crossing_mc3.py`); crossing-wait target p90 ≤ 5 min (§4.6, §5). Changed: the gap-stretch fix is not the default (no gain with the 2 NM rule in `crossing_mc2.py`); optional parameter, off. |
| M5 | Accepted | Geometry baked offline as integer cm (lengths, fillet trims, arc lengths, radii, blocks); commits use + − × ÷, round and `Math.sqrt` only; a test asserts no transcendental call on the commit path; JavaScriptCore agreement stated as untested (§1.4, §4.1, §5). |
| M6 | Accepted | Arrival commit after its stand's departure commit; origin holds capped at the next on-block − 10 min, then a lane wait; arrival re-allocated at commit; "always completes" argued from fallbacks; double-occupancy test (§1.4, §4.5, §5). |
| M7 | Accepted | `setService(g, 'turn' | 'cold')`, service windows (on-block + 30 min, off-block − 45 min), night-stoppers cold; per-stand GSE cache with a measured rebuild budget (§1.5, §4.3, §6.4). |
| M8 | Accepted | Frozen `UiTrack` with every field `ui.js` reads; sim time for `phaseLabel`; `SHA.traffic.tracks` defined (§6.1, §7.1). |
| M9 | Accepted | Two weight and type-mix sets, `complement` (observed days) and `fullDay` (other days); wide-body halving only in `complement`; mix test (§2.1, §2.2, §7.2 A). |
| M10 | Accepted | No seeded delay for tier 2; |sim − t_sha| reported; the card shows the record's own σ (§2.2, §6.1). |
| M11 | Accepted | Shell runway line from `SHA.sim.runway(t)`; the rule in `plan.hash` with a re-commit on change; `runwayMode` for the direction only, then `assignRunways(dir, t, closed)`; no relay METAR overwrite on a replay day (§1.2, §1.4, §6.1). |
| M12 | Accepted | Overlay field `type` from the source's `t`; source `icao` (24-bit address) never read; format tests (§3). |
| M13 | Accepted (changed) | Option A modelled as a real push (tail first over two-way lanes, push-turn into the one-way branch, forward taxi as if arrived via it), found by rule: 14 / 14 freed, pushes 134-191 m, 0 of 2,196 gear and tail samples off pavement (`optA_push.mjs`); swept-planform test and reservation of run, junction and swing branch (§4.1, §4.3, §4.5). Changed: the rule is "shortest tail-first run that frees all four ends", not "≤ 50 m against the direction"; the runs differ from stands.md's forward-taxi segments. |
| M14 | Accepted | Packages re-cut and re-sized (A 7, B 7, E 6, C1 8, C2 5, D 8, F 5 h, integrator 4 h); new **P3-E** (gate / time adapter, harness defaults) and **P3-F** (artifact with a publish spike: module tree vs bundler); C split into C1 / C2; `TRAFFIC` default off in the harness and `?park=` excludes traffic, so the Phase 2 jobs need no edit; snapshot `days[]`, `UiTrack`, gate adapter and `GateTimes` frozen in §7.1; B owns `SOURCES_routes.json` (§6.3, §7). |
| L1 | Accepted | ROT from touchdown; unnamed rapid links before the F4301 first exits excluded (§4.2, §5). |
| L2 | Accepted | Lane rules copied from `rules.facts`: one at a time on Y1-Y3, M1-M6, L15-L17; ≥ 36 m mainly cross via H2 / H6 (§4.1). |
| L3 | Accepted (changed) | The local AIP mirror (AD 2.20 2.3.3) names both end-arounds with no flow rule, plus visual screens 388 m beyond each 18R/36L end and HP1-HP4; so no side rule, but end boxes as departure resources with holds before them (§4.1, §4.5). |
| L4 | Accepted | One-off AWC pull for 13-14 Nov and 19-20 Nov into `days[]` with `complete` flags (§7.2 A). |
| L5 | Accepted | Rejection reason restated: wall-clock offset in `ingest`, report buffers and staleness are the blockers; the 5 s clamp only below 12 fps at ×60; TaxiNet is a map-matcher (§1.1). |
| L6 | Accepted (changed) | `bodies.js` converts to degrees and drops `antOf` (§1.2). Changed: `pave.mjs` reads the same polygon inputs in node and E exposes `vectorPavement` as `SHA.qa.pavedVec` for a 10,000-point comparison, instead of importing gates.js's function (it needs the extensions' pavement hooks) (§5). |
| L7 | Accepted | One-level warm start from a standalone plan(D) end state; a day change costs two plan builds (§2.2 step 10). |
| L8 | Accepted | Basis stated (OD2-3) and owner question Q1b added; allow-list for the committed rows (§2.6, §3, §9.2). |
| L9 | Accepted | `day` validated by format and file list; `--identity-lan` required beyond loopback (§3). |
| L10 | Accepted | SHA-relevant `-lo.webp` liveries in the payload; offline phone test of the built artifact with every outside request blocked (§7.2 F). |
| L11 | Accepted | Scheduled counts vs the profile, delayed counts vs the profile convolved with the delays (§5). |
| L12 | Accepted | Compact segments, lazy path samples (LRU), time-sliced commits, plan-build budget, memory target; tier 1 only while live; pill "Live weather · simulated traffic" (§1.1, §1.4, §6.2, §6.4). |
| Owner point | Accepted | The architecture deviation is owner question Q0 and stated in §0 and §1.1. |
