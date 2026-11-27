# Phase 3 design review (adversarial)

Review of `docs/phase3/design.md` (699 lines, 2026-11-27), written 2026-11-27. Docs only: no code, data, tool, job or
CLAUDE.md file was changed, nothing was rendered or committed.

**Method.** Every claim about code or data was checked in the files, and the line numbers are those of 2026-11-27. The
Phase 2 fix-round-3 agents were editing `gate_system.js`, `gates.js` and `shell.js` at the same time. The designer's
scratch scripts were re-run (`out/phase3_design/route_check.mjs`, `pave_check.mjs`) and reproduce the stated numbers.
Five scratch experiments of my own are in `out/phase3_design/review/` (gitignored):

| Script | What it does |
|---|---|
| `ground_demand.py` | simultaneous on-ground demand of the tier-2 airframes, by side and body |
| `crossing_mc.py` | Monte Carlo of the §4.6 crossing rule |
| `flow_check.mjs` | which end-around each landing direction uses |
| `undock_times.mjs` | can the gate engine run in node? |
| METAR latency one-liner | receipt latency measured from the cached AWC JSON |

**No per-flight data here (OD4).** Only counts and quantiles appear. `ground_demand.py` reads the local
`refs/cache/observed_elsewhere/` tables and prints aggregates only.

**Severity.**
- **High:** breaks an owner rule (OD4), the stated architecture (purity or determinism), or a definition-of-done item.
  Fix before the packages start.
- **Medium:** a plausibility or interface hole that a package would discover late.
- **Low:** accuracy or polish.

---

## Summary

| # | Sev | Finding (short) |
|---|---|---|
| H1 | high | The gate engine is stateful and keyed to its `now`. A backward jump leaves stale animations, and there is no reset API. No Phase 3 package owns `gate_system.js`. |
| H2 | high | The push start is gated by the runtime `pushClearEta`. That is not a function of (plan, t) and differs between play and scrub. The design also uses the wrong API (`setOccupant(null)` instead of `undockEarly`). |
| H3 | high | Stand capacity on the T2 side. Tier 2 alone needs 81 / 95 aircraft at once there, against 86 usable non-B stands; wide-bodies need 19 against 17 wide-capable stands. The design's 135 is an all-airport total that hides this. |
| H4 | high | The OD4 identity audit regex misses about 35 % of the registration formats and every IATA flight number, and the design itself introduces IATA numbers. The tier-3 rows to be committed contradict "no hit". |
| H5 | high | OD4: `?identity=0` is undefined (hide the fields, or drop tier 2?). Leak paths are open: the harness `RELAY=` proxy, the 3-D registration decal, and tier-2 timings in public renders. |
| M1 | med | "Never needs a METAR that has not yet arrived" is false: AWC receipt latency reaches 21 min, plus the 10 min relay interval and the 1 min poll. |
| M2 | med | Runway direction change: old-direction movements continue up to about 25 min while new-direction ones start, so finals and climb-outs face each other head-on. No airborne test catches it. |
| M3 | med | Link reservations by time gap do not give spatial queues: w = d / v at v = 0, and aircraft stop on top of each other at holds. |
| M4 | med | Crossing rule plus commit order: T1 departures wait a median 3-4 min and a P90 of 14-15 min at the 21:00 peak (Monte Carlo). |
| M5 | med | Floats in the commit fold: reservation times come from trajectories with fillet trigonometry, which contradicts §1.4. V8 against JSC cannot be tested here. |
| M6 | med | Stand handover: an arrival can commit before the previous occupant's departure, and origin holds can overrun the next on-block. "Cannot deadlock" is unproven. |
| M7 | med | Night-stoppers get full ground equipment, and stairs plus buses at remote stands, all night: the gate engine has no "cold" occupant. |
| M8 | med | The UI needs sfo3d's Track shape (`hex`, `disp`, `info`, `cs`). `AcState` has none of them, and `aircraft.js` reads `SHA.traffic.tracks` for the registration decal. |
| M9 | med | The fill weights (complement of tier 2) are applied unchanged on days without tier 2, which biases the airline and wide-body mix on 25 of 27 days. |
| M10 | med | Seeded delays are applied to tier-2 times that already are actual (inferred) times. |
| M11 | med | Runway and weather consistency: the shell's runway line is computed differently from the sim's R(t); the live METAR poll overwrites a replay day's weather; the rule switch and `runwayMode` have a `tMs` trap. |
| M12 | med | The overlay field `icao`: in the source tables it is the 24-bit address (the type is `t`). The schema invites copying it, against the stated "no ICAO address". |
| M13 | med | Option A push kinematics are unspecified: tail-first travel and the push-turn at the junction. The "by rule" extension was never tested (the scratch hard-codes link ids). |
| M14 | med | Package sizes are about half of realistic. The integrator (2.5 h) has no bundler. Phase 2 jobs and `?park=` regress with traffic on. Interfaces are not frozen (snapshot `days[]`, UI track). |
| L1-L12 | low | ROT reference point and rapid-exit set; AIP lane-rule transcription; end-around side against flow; replay-day METAR gaps; the 5 s clamp reason; `bodies.js` radians; day-cut continuity; tier-3 numbers against Q10 f; relay endpoint hardening; artifact liveries and offline phone test; hourly test at the bank edges; memory and main-thread budget. |

---

## High

### H1. The gate engine is stateful, keyed to wall / sim `now`, and has no reset; no package owns the needed changes

**Claim** (design.md:120-121): "A backward jump re-uses the committed trajectories. Only the gate system is reset:
`setOccupant(..., animate = false)` for every stand, then one rebuild."

**Evidence.**
- `setOccupant` with `animate = false` never touches `this.anims`. An animation is created only on the
  `g.bridge && animate && ...` branches (`gate_system.js:2012-2024`, `dockFrom` :2116). With `animate = false` the
  old entry stays, and `extension(g)` returns `a.k` while one exists (:1988).
- `step(now)` clamps `u` to [0, 1] (:2383). After a backward jump, an animation whose `t0` lies in the "future"
  holds its start pose until sim time reaches `t0` again.
- The same is true of `parks` (`t0`, :2235), `settles` (:2389), `g._parkHold.until` (:2028),
  `g._incoming.until` (`expectArrival` :2208-2215) and `g._early` (`undockEarly` :2249-2255). All of them hold sim
  timestamps after the first call with sim time.
- There is no reset method. The only initialisation is in the constructor (:701); a grep for `anims.clear`,
  `parks.clear` or `reset` finds nothing.
- `scene.js:30` calls `gateSys.items(Date.now())` today. The DEBUG `park()` and `unpark()` in `gates.js:203` / :212
  pass `Date.now()`. With sim time in `items()`, the two clocks mix.
- The engine cannot even be constructed in node: `new LiveGateSystem(gates)` throws "Cannot read properties of
  undefined (reading 'createVertexArray')" (`out/phase3_design/review/undock_times.mjs`). The sim's node test suite
  therefore cannot use it (see H2).
- The design lists `gate_system.js` in no package's "edits allowed" column (§7.2). §6.4 and §9.1-5 defer every change
  to "the gates owner", but there is no gates package in Phase 3.

**Fix.**
- Add a Phase 3 owner of `js/live/gate_system.js`, `js/live/gates.js` and `js/scene.js:30`. This is a small P3-E
  "gate and time adapter" in wave 2, or part of P3-D with those files added to its list. It delivers:
  1. `resetTo(t, occupants)`: clears `anims`, `parks` and `settles` and every `_parkHold`, `_incoming` and `_early`,
     restores `b.hRest = b.h0` and `b._parkQ`, then snaps every stand to `occupants`.
  2. `items(now)` driven by the sim clock. The DEBUG park is off while traffic runs (see M14).
  3. The "cold" occupant of M7.
  4. A static duration table (H2).
- Call `resetTo` on every jump backward, and on every jump forward of more than 120 s.

### H2. The push start depends on runtime gate state; wrong undock API

**Claim** (design.md:372-375):
- `setOccupant(g, null)` at off-block − 150 s;
- "the push starts only when `gateSys.pushClearEta(g, t) ≤ 0`, else it waits (≤ 60 s)".

**Evidence.**
- `pushClearEta` (`gate_system.js:2306-2328`) reads the running animation (`a.t0`, `a.dur`, `animK`). That
  animation exists only if the stand was animated, not snapped. Its timing depends on when `setOccupant` / `hurryUndock`
  were called and on which animation was running.
- A ×1 play, a ×60 play (snap above ×60, design §6.2) and a jump therefore give different push starts. That breaks
  "the scene is a pure function of (day plan, inputs, t)" (§0) and "phone, laptop and artifact agree".
- The sim (`js/sim/*`, node) cannot call it at all (H1). So the wait happens either:
  - in the display, where the sim says "pushing" while the aircraft is shown waiting; or
  - not at all.
- The engine's documented departure API is `undockEarly(g, now)` (:2235-2255). It keeps the aircraft as the occupant
  (`g._early`, its type and pose), so the neighbours' bridges (`parkOcc` :2132-2143) and the GSE keep-out still see
  the parked aircraft during the retraction.
- `setOccupant(g, null)` declares the stand empty 150 s before the aircraft leaves:
  - the neighbours' rest poses may swing into it (`parkChoose`);
  - remote-stand stairs and the bus disappear at once (`remoteGeo` :1731 draws them only while `g.acType`).

**Fix.**
- Make every gate-related duration a sim input, never a runtime query. Build a table `undockClear_s[stand][typeKey]`:
  - its value is the `pushClearEta` from the docked state, i.e. `hurryPlans(undockPlans(g), 1).T` together with
    `pushHitK`, both deterministic functions of the static geometry;
  - compute it once per boot in the browser after the gates are prepared (P3-E), or offline with a GL stub, and hand
    it to `createSim`.
- The sim schedules undock = off-block − max(150 s, table + 10 s). The gate sync calls
  `undockEarly(g, t_undock)` there and `setOccupant(g, null)` only when the push starts.
- If the display lags after a jump, `hurryUndock` catches up. That is visual only; the push is never delayed by it.

### H3. T2-side stand capacity: tier 2 alone exceeds it; the aggregate figure hides it

**Claim** (design.md:169-177): night-stoppers are capped at 0.9 × 135 usable non-B stands; expected 80-120. §9.1-4 calls
it "tight".

**Evidence** (`out/phase3_design/review/ground_demand.py`).
- The script takes tier 2 only: consistent records with `t_sha`, same registration. Intervals run from the inferred
  landing to the inferred take-off, which roughly equals the allocator's [on − 10 min, off + 10 min], since the
  ±10 min buffers offset the taxi times.
- Side rule: T1 = 9C / NS / MF plus any non-mainland far end (field.md:200-217).

| Day | T2 max at once | T2 wide-body max | T2 at 04:00 | T1 max at once |
|---|---|---|---|---|
| 10 Nov | **81** | **19** | 68 | 32 |
| 12 Nov | **95** | **19** | 75 | 30 |

- Capacity (`sha_stands.json`, my count):
  - T2 side (T2 apron 2, west and south-west remote aprons): **86** non-B stands usable at once (91 non-B stands
    minus the 238/238A and 240/240A pairs), plus 5 class B.
  - Wide-capable T2 stands (E / EL / D): **17**. One of them is D (52 m), which takes no A330, 787 or 777. B77W needs
    EL: 5 stands on the T2 side.
  - T1 side: 49 non-B stands.
- So on 12 Nov tier 2 alone overflows the T2 side by about 9 aircraft at peak, and the wide-capable T2 stands by 2.
  The fill then adds about 30 % more movements. The "135" figure counts the T1 side, where only 30-32 are needed.
- The design's preference order puts the overflow on the other side's remote apron "(bus)": T2 passengers bused
  across both runways every day. The alternative is "unplaced", so their flights silently vanish from the scene, and
  the `byHour` test may still pass on the plan counts.
- The AIP combined wide-body positions 216E, 220E, 281E and 413E are listed but unplaced (`sha_stands.json`
  `aip_facts.combined`; `counts.aip_overlays_unplaced` 6). They are exactly how a real T2 would absorb wide-bodies.

**Fix.**
- P3-A's `test_plan.mjs` checks capacity per side × class (narrow / wide / EL) at every minute and reports the overflow
  by side and class, not one total.
- Decide and document an overflow policy, in this order:
  1. a wide-body on two adjacent C stands as a combined position: only where Phase 1 can place one; otherwise this is
     a data request to `tools/airport/build_stands.py`;
  2. the 4 OSM `positions` without a ref (hangar apron / east remote), for night-stoppers only;
  3. cross-side remote with a bus, counted and labelled;
  4. unplaced, which must also remove the movement from the counted plan.
- Lower the night-stop scaling on the T2 side so that tier 2 plus fill fits. Give the result per side in `plan.md`.

### H4. OD4 identity audit: the regex misses a third of the registrations and all IATA flight numbers

**Claim** (design.md:604-605): "A grep over every committed new file for `\bB-\d{4}\b`, `\b[A-Z]{3}\d{1,4}[A-Z]?\b`
callsign patterns and 6-hex addresses has no hit outside the placeholders." The integrator repeats it on the whole diff
(:633).

**Evidence** (format classes only, from the local tables, counts over both days):
- registrations: 709 of 1,120 records have the form `B-` + 4 digits. The other 37 % do not match `\bB-\d{4}\b`:
  - `B-` + 3 digits + letter: 157;
  - `B-` + 2 digits + 2 letters: 156;
  - `B-` + 2 digits + letter + digit: 58;
  - `B-` + 3 letters (Hong Kong / Macau): 18;
  - 2 letters + 4 digits (other states): 8.
- The design adds an IATA `flight` field to the overlay (:279, from `data/lookup.js` `AIRLINES`, e.g. `CES` → `MU`).
  Its labels use `MUnnnn` (:493). The audit regex does not match IATA numbers at all: 2-character designators, some of
  them digit-letter.
- The 6-hex pattern matches colours and hashes everywhere in `js/`, so the audit drowns in false hits and gets ignored.
- §8 commits HKG / TSA rows in `data/sha_sim_inputs.js`: published flight numbers and times. These are
  redistributable (sources_sim.md:83-84, 469), but they are real flight numbers in a committed file. The acceptance
  "no hit" is then either false or the regex is blind to them.

**Fix.**
- Replace the regex audit with an **exact-match audit** (`tools/sim/audit_identity.py`, local, prints counts only).
  - It loads every `cs`, derived flight number, `r` and 24-bit address from `refs/cache/observed_elsewhere/*.json`
    (and the `scan/` files).
  - It searches every staged file, the whole `git diff --cached`, PNG text chunks and `docs/**`.
  - It runs as the integrator's gate, and the lead runs it before each commit.
- Keep a broadened regex as a second net, for docs and jobs only:
  - `\bB-[0-9A-Z]{3,5}\b`;
  - `\b(?:[A-Z]{2}|[A-Z][0-9]|[0-9][A-Z])[0-9]{2,4}\b`;
  - `\b[A-Z]{3}[0-9]{1,4}[A-Z]?\b`.
- Allow-list the tier-3 rows explicitly: a file list plus a `SOURCES_sim.json` entry naming them as published
  schedule facts, not observed-elsewhere data. See also L8.

### H5. OD4: `?identity=0` is undefined, and three leak paths stay open

**Claim** (design.md:293-294): "`?identity=0` drops them: used by every job that renders for `docs/`". Risk 1 (:658-662)
lists `?identity=0`, synthetic mocks and the grep.

**Evidence.**
1. **Undefined meaning.**
   - If `identity=0` only hides fields, the tier-2 slots stay: `oe:<uid>` with `t_sha` times, real rotations, airline
     and type. A docs render then shows, for example, an A21N of one airline landing at an inferred real-flight time.
     That is per-flight timing derived from observed-elsewhere data in a committed image (the task's OD4 rule
     includes per-flight times).
   - Only "overlay = null" gives the public plan (:295-297).
2. **The harness relay proxy.**
   - `livetest.mjs:34-35` proxies every `/api/*` path to `RELAY=`. The new endpoint is on by default whenever the
     local file exists (§3), so `RELAY=… OUT=docs/… node livetest.mjs jobs/*.mjs` fetches real identities.
   - The existing `jobs/integration.mjs` live scene runs exactly this way (sha3d CLAUDE.md "Harness", the
     `RELAY=` line).
3. **The 3-D registration decal.**
   - `LiveAircraft.registration()` (`js/live/aircraft.js:128-133`) paints the registration on the fuselage. It takes
     it from the livery, or from `window.SHA.traffic.tracks.get(this.id).info.reg`.
   - If P3-D exposes tier-2 tracks under that name, or puts `reg` into the livery, every close render shows a real
     registration in the image. The design mentions only labels and cards.

**Fix.**
- Define `?identity=0` ≡ `overlay = null`: the public plan, no tier-2 slots, no `rep:` slots.
- In `livetest.mjs`, refuse `/api/observed_elsewhere` (answer `{available: false}`) unless `IDENTITY=1`, and refuse
  `IDENTITY=1` when `OUT` is under `docs/`.
- `jobs/traffic.mjs` asserts `SHA.sim.plan.tiers.oe === 0 && !SHA.sim.plan.tiers.rep` before every shot.
- Give the registration decal its own switch: only for tier 2, only with identity on, and off by default for every job.

---

## Medium

### M1. METAR availability latency: 15 min is not enough for "never needs a METAR that has not yet arrived"

**Claim** (design.md:92-96, 106-107): with a 15 min latency, "any device with the same report list gets the same R(t)",
and in live mode a commit "never needs a METAR that has not yet arrived".

**Evidence.**
- Path of a report: AWC `receiptTime` − `obsTime`, then the relay fetch every 10 min (`sha_live_server.py:57`), then
  the client poll every 60 s (`js/live/relay.js:14`).
- Receipt latency in the cached AWC JSON (`refs/cache/metar/awc_metar_zsss_24h.json` + `snapshot_20261120/metar_24h.json`,
  n = 97): **p50 5.5 min, p90 7.0, max 21.1**.
- A report is therefore in the browser up to about 16.5 min after `obsTime` at p50 in the worst case, and up to 32 min
  at the maximum.
- A live device that commits at t_c with the report observed at t_c − 15 still missing takes the previous direction. A
  device loaded later takes the new one.
- With 0.55 direction changes a day (`sources_sim_wx_stats.json` `rule_iem.changes_per_day`), divergence is rare but
  real. The stated invariant is false.

**Fix.**
- Use AWC `receiptTime`, which is a property of the report and the same on every device: R(t) uses reports with
  `receiptTime ≤ t − 12 min` (10 min relay + 1 min poll + margin).
- For IEM-only replay days, which have no receipt time, use `obsTime + 20 min`.
- Document that a relay outage can still split live devices. `plan.hash` and the commit hash already show it.

### M2. Runway direction change: opposite-direction finals and climb-outs coexist for about 20-25 min

**Claim** (design.md:107-109): "A runway change during taxi or on final keeps the committed runway: the AIP tolerance for
downwind operation 'for short time' during a change (AD 2.20 2.1.2) covers it."

**Evidence.**
- Commit times: departures at off-block − 5 min (roll at about t_c + 13-25 min: push, start-up 90 s, taxi median
  2,261 m); arrivals at touchdown − 20 min (the 12 km final starts about touchdown − 3 min).
- After a change at t_s, old-direction departures roll until about t_s + 25 min. New-direction arrivals are on a 12 km
  final from about t_s + 17 min. An old-direction 18R departure climbing straight out south (§4.4: straight, fade at
  15 km) meets new 36R arrivals descending northbound.
- The same happens with an old 18L arrival and a new 36L departure climbing north.
- The AIP clause allows downwind landing and take-off "for short time"; it does not allow opposite-direction traffic in
  the same corridor.
- §4.5 runway resources cover only [threshold − 2 NM, vacated] per runway. §5 has no airborne check, so this ships
  unseen about every second day.

**Fix.**
- Add a "flow corridor" resource per runway pair with a direction tag. It spans the approach from 12 km to the
  threshold and the climb-out to 15 km. Reservations of opposite directions may not overlap.
- New-direction movements wait for the last old-direction one, as ATC does when it stops arrivals before a switch.
- Departures committed in the old direction that have not reached the holding point may be re-routed to the new end.
  This is deterministic, because R(t) is known at commit time.
- Add an airborne check to `test_day.mjs`: minimum 3-D distance between airborne pairs, with a target of ≥ 2.5 NM
  laterally or 1,000 ft vertically.

### M3. Time-gap link reservations do not produce spatial queues

**Claim** (design.md:409-413): same direction FIFO "entry and exit gaps ≥ (L_leader + 60 m) / v_follower". Junctions use
w = (span / 2 + 15 m) / v.

**Evidence.**
- At holds, line-up queues and crossing queues, v → 0, so the gaps diverge. Two aircraft that enter a link 30 s
  apart can both decelerate to the same stop point. Nothing in the scheme gives the follower a stop position behind
  the leader.
- §5's render list asks for "the 36L holding queue" and M4 predicts crossing queues, so this case is common, not an
  edge.

**Fix.**
- The leader is committed before the follower, so the follower can be constrained against the leader's known
  trajectory: s_f(t) ≤ s_l(t) − (L_l / 2 + L_f / 2 + gap) on every shared link and across links via the route
  offsets. This is deterministic and pure; it is not runtime car-following.
- Hold nodes get a storage length and queue positions. Junction windows are computed from the trajectories' distance
  (enter / clear the junction box), not from d / v.

### M4. The crossing rule with arrivals-first commit order gives long holds at the peak

**Claim** (design.md:440-442): "T1 departures cross 18L/36R at H1 / H4 / H7 when no arrival is within 2 NM and the
runway is clear (≤ 40 s)".

**Evidence.**
- Commit order: a departure commits at off-block − 5 min and reaches the crossing about 10-13 min later. Every arrival
  touching down within about 20 min of that commit is already committed, so crossings always yield.
- `out/phase3_design/review/crossing_mc.py`:
  - arrivals at the profile rate (33.7 / h at 21:00 local), ≥ 72 s apart;
  - crossing window = previous arrival vacated (+50 s) to next arrival at 2 NM (51 s), minus 40 s.
- Waits (s):

  | Hour | Rate | Crossings / h | mean / p50 / p90 / p99, serial | mean / p50 / p90 / p99, batched |
  |---|---|---|---|---|
  | 21:00 | 33.7 arr / h | 5 | 370 / 253 / 929 / 1,602 | 318 / 200 / 820 / 1,490 |
  | 16:00 | 27.3 arr / h | 7 | 229 / 139 / 595 / 1,149 | not recorded |
  | 10:00 | 23 arr / h | 7 | 152 / 86 / 416 / 809 | not recorded |

- The crossing queues block taxiways A and B between H1, H4 and H7 (M3).

**Fix.**
- Allow a crossing behind a landing aircraft once it has passed the crossing node: the usual practice, and the runway
  need not be fully clear.
- Batch all aircraft waiting at H1 / H4 / H7 into one gap.
- At an arrival's commit, if the plan shows two or more T1 departures reaching a crossing in the next 10 min, stretch
  that arrival's spacing to 2 × 5 km. This is deterministic, because the plan is known.
- `day_report.mjs` reports crossing waits; target p90 ≤ 5 min [inf].

### M5. Floats inside the commit fold

**Claim** (design.md:110-113): scheduler decisions compare integer milliseconds and data route lengths, "never
`Math.sin` / `exp` results … Trajectory evaluation (display only) may use floats".

**Evidence.**
- The reservation windows (link entry and exit, junction windows, runway slots) come from the trajectory's speed
  profile: v_max from curvature, accel / brake passes, arcs.
- The arcs are built at runtime: "every vertex turn > 3° gets a tangent arc" (:397-401), which needs trigonometry for
  the turn angle and tangent length. So trajectory **construction** is part of the commit, not display only.
- `Math.sin`, `Math.cos`, `Math.atan2` and `Math.acos` are not correctly rounded in V8 or JSC. A near-tie at an
  integer-ms boundary flips.
- The sandbox has only Chromium (`/opt/pw-browsers`: no WebKit), so the claimed phone agreement cannot be tested here.

**Fix.**
- `tools/sim/build_routes.mjs` (node, once) bakes every route's geometry: arc points, cumulative s at 1 m and v_max(s)
  as integers (cm, cm/s), and the per-link s offsets.
- The runtime commit uses only + − × ÷ and `Math.sqrt` (IEEE-exact) on those integers.
- Live-routed fallbacks (closed links) use the same integer pipeline in JS.
- Add a WebKit run to the determinism test when WebKit is installed; otherwise state the claim as untested.

### M6. Stand handover: the arrival may commit before the departing occupant, and "cannot deadlock" is unproven

**Claim** (design.md:419-423): "Because commits are sequential and only later movements adapt, planning cannot deadlock".
The fallback "is to hold at the origin (delay the off-block)".

**Evidence.**
- With the ±10 min buffers (:210), the tightest handover has departure off-block = arrival on-block − 20 min. Its
  departure commit is on-block − 25 min.
- The arrival commits at touchdown − 20 = on-block − (taxi-in + 20) = on-block − 25..35 min (arrival routes 1.1-3.3 km,
  end-around +1.7 km).
- So in tight handovers the arrival commits **first**. If the departure then needs an origin hold, it must adapt and
  extend its stand occupancy. The fold cannot move the already-committed arrival, and the stand is then double-occupied.
- Example: a hold because the arriving aircraft itself occupies the departure's first lane, or the adjacent-stand rule.
- The alternative is a pushed departure that cannot leave its lane: a circular wait.

**Fix.**
- Order by dependency: t_c(arrival) = max(touchdown − 20 min, t_c(previous occupant's departure) + 1 ms). This stays
  deterministic.
- Cap origin holds at the next occupant's on-block − 10 min. Beyond that the departure pushes and holds on a lane or a
  remote holding point (reservation), or the arrival is re-allocated at its commit.
- `test_day.mjs` adds "no stand double occupancy, holds included".

### M7. Night-stoppers and the gate engine: full ground equipment all night

**Evidence.**
- `build(now, true)` places the vehicles for every occupied bridge stand that is not animating (`gate_system.js:2361`:
  `if (g.acType) this.placeVehicles(g, Ps)`). `remoteGeo` places them for every occupied remote stand (:1731).
- `placeVehicles` (:2423-2525) draws, seeded, belt loaders, a baggage train, catering, fuel and a GPU, and at remote
  stands two stairs and one or two buses. There is no service or "cold" option. `setOccupant` `opts` only carries
  `freighter` / `early` / `undockS`.
- The 80-120 night-stoppers would show stairs, buses and GSE from 04:00 to their departure.
- Each `setOccupant` also triggers a full rebuild that re-places the GSE of every occupied stand (§6.4). With about
  130 occupied stands that is the cost to measure first.

**Fix** (the gate owner of H1):
- `setOccupant(..., {service: 'turn' | 'cold'})`;
- service windows in the plan: on-block + 0-30 min and off-block − 45..0 min. A night-stopper is cold until 45 min
  before departure;
- cache the GSE placement per stand, invalidated only by that stand or its neighbours.

### M8. UI interface: `ui.js` expects sfo3d's Track shape

**Evidence.**
- `ui.js:154-170` (`renderList`) reads `tr.disp.valid`, `tr.stale`, `tr.cs.display`, `tr.info.reg`, `tr.hex` (the row
  key `data-hex`), `I.icao`, `I.altBaro`, `D.gs` and `tr.gate`.
- `renderCard` (:175-195) reads the same plus `tr.cs.airline.name` and `tr.type.full`.
- `phaseLabel(tr, now)` is called with `Date.now()` (:159, 179).
- `AcState` (design.md:579) has none of these. Feeding it in directly throws on `tr.disp.valid`. Without `cs.display`
  the row and card titles fall back to `tr.hex.toUpperCase()`, which would print the internal id ("AF:17").
- `aircraft.js:131` reads `window.SHA.traffic.tracks` for the decal (H5).

**Fix.** Freeze a `UiTrack` view in §7.1, built by `labels.js` from `AcState` and `labelFor`:
`{hex: af id, src, tier, chips, disp: {valid, x, y, z, ground, gs}, info: {icao, reg (overlay only), altBaro, flight},
cs: {display, airline: {name}}, type: {full}, gate, phase}`. Pass sim time as `now`. Decide whether
`SHA.traffic.tracks` exists (it drives the decal, H5).

### M9. Fill weights are a complement of tier 2 but are used on days without tier 2

**Claim** (design.md:140-144): the fill airline weight ∝ DB SHA callsigns − identified distinct callsigns. The fill's
wide-body share is halved "for the blind routes' narrow-body bias".

**Evidence** (`docs/phase1/observed_elsewhere_stats.json`, 10 Nov; committed aggregates):
- DB 1,376 callsigns; identified 542; residual 834.

| Airline | Residual-weighted fill | Identified | DB |
|---|---|---|---|
| CES | 260 / 834 = **31 %** | 39 % | 34 % |
| CSH | 149 / 834 = **18 %** | 11 % | 15 % |
| CDG | **4.9 %** | 1.7 % | 3.6 % |

- On every day other than 10 and 12 Nov the fill **is** the whole day (§2.6), so these residual shares and the halved
  wide-body share become the day's mix. That under-represents the largest carrier and the wide-bodies on 25 of 27 days
  of November.

**Fix.**
- Use two weight sets in `sha_sim_inputs.js`:
  - `complement` for observed days;
  - `fullDay` for every other day = the expected per-airline counts of an observed-day plan (identified +
    complement × fill count), and likewise for the type mix.
- `test_plan.mjs` compares a non-observed day's airline and type mix with the observed days' full plans.

### M10. Delays are applied to tier-2 times that are already actual

**Evidence.**
- Step 7 (design.md:178-182) delays "each slot", seeded: 15 % by +15-60 min and 5 % by +60-120 min. Step 2 sets tier-2
  times from `t_sha`.
- `t_sha` is the inferred actual landing or take-off (observed_elsewhere.md:406-414: inferred take-off − scheduled
  off-block +5 to +42 min). Delays are already in it.
- Delaying it again moves an "observed elsewhere" flight up to 2 h away from its inferred time while the card still
  says "Its time at Hongqiao is inferred (±9 min)".

**Fix.**
- Delays only for tier 3, which has published scheduled times (use their actual times where published), and tier 4.
- Tier 2 moves only by the scheduler's holds.
- The card shows the record's own `sigma_s` instead of the fixed ±9.

### M11. Runway and weather consistency between the UI, the env and the sim

**Evidence.**
- **The runway line.** The shell computes it with `runwayMode(E.reports, {rule: S.rule, tMs: st.tEnv})` (`shell.js:85`):
  no latency, no `start` anchor (default '36'), no NOTAM `closed`.
  - The sim's R(t) has all three (§1.4, §2.5), so the note can say "arr 18L" while traffic lands on 36R. During F4551
    (closed 1700-2200Z) the shell still shows 18L/36R arrivals.
  - The Settings rule switch (`shell.js:200`, localStorage `rwyrule`) changes the sim per device; the design does not
    say the plan re-commits or that the rule enters `plan.hash`.
- **A `runwayMode` trap.** `runwayMode(reports, {tMs})` uses `tMs` both to filter reports and for `assignRunways`' night
  hour (`metar_zsss.js:196-216`). Passing t − 15 min shifts the 1600-2300Z night rule by 15 min.
- **The replay-day weather.** `app.js:196-197` polls the relay every 60 s and calls `envCore.setReports(L)`. In live
  mode a replay of 12 Nov (chosen in the time bar, §6.2) gets today's METARs back within a minute.

**Fix.**
- The shell's runway line reads `SHA.sim.runway(t)`. The rule switch triggers a re-commit and is part of `plan.hash`.
- P3-C calls `runwayMode` only for the direction, then `assignRunways(dir, t, closed)`.
- While the sim clock shows a day other than today, the relay poll must not replace `envCore.reports`; the env takes
  that day's list from `sha_snapshot.js` `days[]`. This is an `app.js` edit, which P3-D owns.

### M12. Overlay schema: `icao` means the 24-bit address in the source

**Evidence.**
- In `sha_observed_<day>.json` the field `icao` holds 6-hex addresses (all 1,120 records match the 6-hex pattern) and
  the ICAO type is `t`.
- The overlay schema (design.md:279) has `icao` and states "No ICAO 24-bit address" (:282). `DayPlan`, `AcState` and
  `perfOf(icao)` use `icao` for the type.
- An implementer who copies `icao` through ships the address to the browser, the LAN and the artifact, and every type
  lookup fails.

**Fix.**
- Rename to `type` in the overlay, or map `t` → `icao` explicitly.
- `test_observed_overlay.py` asserts the type field matches `^[A-Z][A-Z0-9]{1,3}$` and that no field matches
  `^[0-9a-f]{6}$`.

### M13. Option A: the push kinematics are unspecified and the "by rule" extension is untested

**Evidence.**
- `route_check.mjs` frees the 14 stands with a hard-coded `NEED` map of 7 link ids. Over those links (opened) it allows
  any direction, and at every node touching them it replaces the committed `turns` table with geometric turns of
  ≤ 100°.
- That is **forward taxi against the one-way tag**, not a push. In a real option A push:
  - the aircraft moves tail-first over the segment;
  - it reaches the junction with its nose pointing back along the lane;
  - it needs a push-turn of 180° − (taxi turn) there, with the tail swung into the branch opposite the departure
    direction.
- Whether that branch or apron exists and is paved for the swept tail and main gear was not checked.
- The claimed rule "shortest against-direction lane run ≤ 50 m that opens all four ends" (design.md:315-316) was not
  run. stands.md:283-290 gives the expected outcome: 7 segments, 107.9 m, pushes of 100-143 m.

**Fix.**
- P3-B builds option A pushes as a reversed path over the extension plus an explicit push-turn at the junction. It
  tests the swept planform and every gear point on pavement for the 14 stands, and checks that the rule reproduces the
  7 segments.
- The reservation covers the lane extension, the junction and the swing branch for the whole push and the 90 s
  start-up.

### M14. Package sizes, integrator scope, Phase 2 regressions and unfrozen interfaces

**Evidence.**
- **Sizes.** Each 3.5-4 h package carries several hard parts:
  - A: allocator with classes, exclusions, closures and rotations; the plan; the identity texts; relay endpoint and
    tests; the snapshot builder;
  - B: edge router with option A, fillet paths, approach / flare / take-off trajectories, the route table;
  - C: reservations, queues (M3), crossings (M4), handover (M6), the flow corridor (M2), NOTAM link mapping
    (F4552: "sections of TWY A, B and H between H4 and H7"), a 10-check day suite on 4 days;
  - D: 12 edited files plus a time bar and about 14 render scenes on llvmpipe at about 1-1.5 s per frame.

  Each is about 2× under. C is the critical path.
- **Integrator.**
  - The design asks for sfo3d's `phone_artifact.sh` pattern, but that script inlines an **esbuild bundle of the
    three.js app** (`sfo3d/tools/build3/build.mjs --app`, `phone_artifact_page.py:8`).
  - sha3d is 64 unbundled modules (1.4 MB), and the sandbox has no esbuild (`require.resolve('esbuild')` fails; no
    `node_modules`).
  - Liveries are also needed (L10).

  2.5 h is not enough.
- **Phase 2 regressions.**
  - The Phase 2 jobs compose their own URLs (`jobs/views.mjs:32`, `gates.mjs:188`, `markings.mjs:23`,
    `buildings.mjs:46`, `ui.mjs:15`, `integration.mjs:65`/:82). None passes `?traffic=0` and no P3 package owns them,
    so every Phase 2 render changes.
  - `?park=` plus traffic both call `setOccupant` on the same stands.
- **Unfrozen interfaces.**
  - The new snapshot schema (`days[]`, `traffic: {kind: 'sim', day}`) is written by A and read by D, but is not in
    §7.1.
  - `UiTrack` (M8) and the gate adapter (H1, H2, M7) are missing.
  - `data/sha_routes.*` (B) needs a SOURCES entry, but `SOURCES_sim.json` belongs to A.

**Fix.**
- Add P3-E (gate / time adapter plus harness defaults: `livetest.mjs` injects `traffic=0` unless `TRAFFIC=1`, and the
  traffic extension stays off while `?park=` is set) and P3-F (the artifact builder: a module-tree publish, which the
  Artifact tool allows as up to 255 supporting files, or a vendored bundler, decided first) in wave 2.
- Split C into C1 (runway, NOTAM, reservations) and C2 (day suite, report, pave).
- Re-estimate at about 6-8 h per package.
- Freeze the snapshot `days[]` schema, `UiTrack` and the gate adapter API in §7.1. B writes `data/SOURCES_routes.json`.

---

## Low

**L1. ROT reference point and exits.**
- The AIP clause is "vacate within 50 s **after touchdown** via the first or second rapid exit" (sources_sim.md:339,
  taxigraph `rules.facts.rapid_exit`).
- The design measures from the threshold (design.md:353, §5), about 7 s stricter. Wide-bodies at 1.7 m/s² on 18L
  reach B4 at 20 m/s only with braking from touchdown (about 52 s from the threshold).
- `router.exits(end)` also returns unnamed rapid links (`route_check.mjs` prints 18L `null@1549`, 36R `null@1744`).
  These lie before F4301's "first rapid exits" (B4 / A3, A2 / B3).
- Fix: measure ROT from touchdown, and restrict the exit model to the F4301 / named exits.

**L2. AIP lane rules mis-transcribed.**
- The AIP list is "no two aircraft at the same time on any of **Y1-Y3, M1-M6, L15-L17**" (taxigraph
  `rules.facts.departure_only`). The design has "L13, L15-L17" (design.md:416).
- Also not applied: "aircraft ≥ 36 m mainly cross RWY18R (36L) via H2 (H6)" (`rules.facts.route_north_south`).
- Fix: copy both rules from the data block, not from memory.

**L3. End-around side against the flow.**
- With the design's crossing penalty (`out/phase3_design/review/flow_check.mjs`):
  - north flow (36R landings): 56 of 100 west-side arrivals take ROUTE-SOUTH (BS → S), past the south end where 36L
    departures start their roll;
  - south flow: 11 of 100 take ROUTE-NORTH, past the 18R start of roll.
- AD 2.20 2.3.3 in the local mirror should settle which route goes with which flow. At least add a jet-blast
  reservation behind the start of roll.

**L4. Replay-day METAR coverage.**
- 14 Nov (operating day 13 Nov 20:00Z - 14 Nov 20:00Z) is covered only to 14 Nov 05:25Z (IEM ends 13 Nov 23:50Z;
  the AWC 30-day pull was made on 14 Nov).
- The 20 Nov snapshot list stops at its instant.
- A one-off AWC pull now (its 30-day window still covers 14 Nov) is needed. Say so in P3-A.

**L5. Rejection reason (2) is overstated.**
- The 5 s clamp (`sfo3d traffic.js:2200`) bites at ×60 only below 12 fps.
- The real blockers are the wall-clock offset in `ingest(payload, recvNow = Date.now())` (:562-565), the report
  buffers (`Track` :350) and the staleness ages.
- The conclusion stands. Also note that sfo3d's `TaxiNet` (:279-313) is a map-matcher and pavement test, not a
  router: routing is new code either way. `sha_taxigraph.json` already has TaxiNet's fields (`edges`, `halfWidth`,
  `ways`, `aprons`, `leadins`).

**L6. Fork hygiene.**
- sfo3d `ground.js` `hv(h)` takes **radians** (:16) and `bodyOf` imports `antOf` from `traffic.js` (:14, :187).
  `js/sim/bodies.js` must convert to degrees (`hdgVec`) and drop `antOf` (CLAUDE.md "degree / radian mixing").
- `tools/sim/pave.mjs` duplicates `gates.js` `vectorPavement` (fix round 3, not exported). Export it instead (gate
  owner, H1).

**L7. Day-cut continuity.**
- Instead of a 2 s cross-fade at 04:00 (§9.1-9), let `buildDayPlan(D + 1)` take the end state of `buildDayPlan(D)`:
  parked airframes, stands, types. Only one level deep, so it stays deterministic.

**L8. Tier-3 flight numbers and the §6b Q10 f default.**
- The default reads "identity is shown only where observed (labelled 'observed elsewhere'), otherwise airline and type
  only" (PLAN §6b). Showing published HKG / TSA flight numbers on 13 / 14 Nov rests on OD2 item 3. State that, or
  add it to owner question Q1.
- The committed rows need the H4 allow-list.

**L9. Relay endpoint hardening.**
- Validate `?day=` with `^\d{4}-\d{2}-\d{2}$` against the file list.
- With `--host` other than loopback, serve identities only with an explicit `--identity-lan`, not just a banner line
  (design.md:289-290).

**L10. Artifact payload and test.**
- The livery textures are missing from the payload. They load from `../sfo3d/data/liveries/`
  (`js/aircraft/liveries.js:28`; the `-lo.webp` set is 184 files, 3.6 MB).
- There is no acceptance test of the built artifact: the harness with `DEVICE='iPhone 15'` and every request outside
  the artifact files blocked (the CSP).

**L11. Hourly count test at the bank edges.**
- Delays move 22:00-23:00 departures into 23:00-00:00 (target 7.2 → 1.4 / h, `sources_sim_hourly.json`). A band of
  max(2, 10 %) fails there by construction.
- Test the scheduled counts against the profile, and the delayed counts against the profile convolved with the delay
  distribution.

**L12. Memory and main-thread budget.**
- `Traj.path` keeps s, x, z and heading at 1 m for every movement (§7.1). At about 2.5 km per taxi route that is
  about 40 kB per movement, about 30 MB a day, before any approach sampling.
- Plan building (allocation, rotations) is not in the ≤ 1.5 s phone budget, and a day change re-plans on the main
  thread.
- Fix: keep compact segments plus per-link times at commit, build path samples lazily for the active movements (LRU),
  commit in time slices.
- Also: draw observed airborne aircraft (tier 1) only while the clock is live; in the pill, say "Live weather ·
  simulated traffic", not "Live · simulated".

---

## Claims checked and found correct

- **sfo3d `traffic.js` lines.** `ingest` :562, `DELAY_MS` :32-33, `DOCK_WAIT_MS` :70, `TD_PRED_M` / `LIFTOFF_KT`
  :152-154, `inAirport` :276, `STANDS` import :21, `GEOID_M` :31, `Track` :350, `reacqOutlier` :692, `stationary`
  :1543, `gateScore` / `matchGate` :1687 / :1718, `silentDock` :1986, the clamp :2200, `ctlGround` :2776 (R_min
  :2782, caps :2795), `ctlAir` :3028, `attitude` :3129, `phaseLabel` :3212, `category` :3240.
- The file has 3,247 lines and 58 lines match `planFor|flysfo|offBlock|inBlock`.
- **sha3d gate engine lines.** `noseGearX` :136, `standTip` :146, `DOCK_DELAY` 12 s :276, `setOccupant` :1993, `step`
  :2374, `items` :2401. `gates.js` `park()` :188, pose :197, `sharesBridgesOf` :201.
- **Env and app.**
  - `AppEnv.setTraffic` `app_env.js:44`; live means "latest report wins" :56.
  - `DataClock.trafficTime` snapshot branch `clock.js:82`.
  - `applyEnv` every 30 s `app.js:241`; `QUALITY` `shadowDist` 700-2,500 m.
  - `metar_zsss.js` `RULES` :171, `assignRunways` :178 (the night rule is already in it), `runwayMode` :196.
  - `geo.js` `hdgVec` :65, `groundY` :84, `initGeo` :113.
- **Imports and sizes.**
  - `js/aircraft/types.js`, `js/geo.js` and `js/env/wx/metar_zsss.js` import in node 22. `TYPE_MODELS` has no C919 or
    AJ27; A21N → a321 and B38M → b738.
  - `sha_live_server.py`: `WX_HOURS = 12` :58, `WX_MIN_INTERVAL` 600 s :57. AWC accepts `hours=168` (sources_sim.md:189).
  - The ui.js row and card use `tr.src === 'inf'` (:164, :190).
- **Data.**
  - 164 stands: 27 class B, 5 exclusive pairs, 135 non-B usable at once.
  - Stand groups 13 / 30 / 16 / 45 + 25 / 13 / 10 / 12.
  - Push median 81 m; 87 over the 1.5 × class-length mark.
  - Option A: 14 stands; F4551 / F4552 / F4313 / F4301 as in sources_sim.md:303-307.
  - Identified movements 542 / 550 (my count of the local tables). Night-stop flow bound 77.8 (recomputed from
    `sources_sim_hourly.json`).
- **The designer's scratch results, reproduced.**
  - 1,312 queries in 1.9 s; 0 departure and 0 arrival failures with option A.
  - Median departure 2,261 m, arrival 1,129 m; 142 / 328 departure routes cross 18L/36R.
  - 186 / 200 end-around with the penalty; full table 8,528 routes, about 2 MB.
  - Pavement: 18 of 25,509 centreline samples off; stop nodes 0 off; gear tracks off on 12 / 15 links.
  - The extent edge is 1,850-2,230 m before the displaced thresholds.
- **design.md itself is clean.** It has no callsign, registration, flight number, address or per-flight time; a grep
  with the broadened H4 patterns finds only "2026".

## Owner-facing points the hand-back should carry

- **The architecture deviation.** PLAN §7 (A) says "through the same traffic, physics and stand pipeline as sfo3d", and
  arch.md:251 maps `traffic.js` as "adapt / keep the phase machine, TaxiNet, matchGate …". The design rejects the
  sfo3d engine. The reasons are sound (L5 aside), but this changes the plan of record and should be stated to the
  owner, not only argued in §1.1.
- **Q1 / Q2 as written are fine.** Add the tier-3 point of L8 to Q1.
