# Requests from the real-time workflow — close-out of the 4 Nov 2026 review

From: owner of `sfo_live_server.py`, `tools/live/**`, `js/live/{feed,traffic,ground,app,ui,entry,about,atc,stats}.js`,
`live.html`, `live.css`, `livetest.mjs`, `jobs/**` (except `jobs/extract2d.mjs`), `docs/research/realtime_impl.md`.
Evidence: `tools/live/invariants.mjs` at 10 Hz on the relay-merge replay of the new recording (`refs/cache/rec`, 4 Nov
17:43–18:33Z, checked 17:48:04–18:33:28Z), positions in the world frame (`wgs84ToWorld`). What changed on my side:
`docs/research/realtime_impl.md`, "Step 6". "Observed" = measured on that replay; "inferred" = reasoning.

## 1. Static workflow (`js/live/airport.js` mask, `data/sfo_pavement.*`, `data/sfo_taxigraph.js`)

Still open from `realtime_round2.md` §2a/§2b, restated with this recording (observed, review 4 Nov + my re-run):

- `offpave.mask` 24,512 frames, 27 aircraft (gear point off the rendered mask but on OSM); `offpave.union` 412 frames,
  15 aircraft (off both).
- **FBO / GA ramp**: LXJ392 E55P N392FX parked 25 min at world (−667, −962) = 37.62747, −122.38300 — on the OSM apron,
  off the rendered mask.
- **Taxi routes off the mask** (on OSM): (−902, 1197), (−905, 1100), (−1116, 902), (−1149, 1070) — AAL1732, UAL2322 and
  others taxiing out on the A / B / M area south of the B pier.
- **1L/1R crossing (taxiway W)**: cell (−350, 275) = 37.61633, −122.37940, off the mask AND the OSM net: 275 frames, all
  moving, 8 aircraft (SWA160, SKW5510, ACA739, UAL2177, JBU15, DAL361, DAL2078, SWA191) — the same corridor as §2a
  (FAA diagram AL-375 shows W crossing both runways; its exact position is the question asked there).
- Smaller cells off both: (−650, −175) and (−625, −275) (JAL2, UAL876), (−1300, −150) (UAL643), (−1500, −125) (SIA31).

Please add the FBO/GA ramp and the taxiway pieces above to the mask, and taxiway W across 1L/1R to the mask and the
taxi graph once its position is settled.

## 2. Bridges workflow (`js/live/gates.js`)

### 2a. `hurryUndock` no longer honours the requested duration (bridge.orphan)

`hurryUndock(g, s)` now runs `max(s, T)` with `T` = the path time at the datasheet's maximum rates. The traffic engine
learns of a departure only when its push-back is already under way (the real bridge was retracted BEFORE the push; the
data cannot show that), so it asks for `FAST_UNDOCK_S` = 5 s and holds the body at most `HOLD_CAP_MS` = 6 s
(`realtime_round2.md` §1a: holding it for the full retraction drew every push-back 1–2 min behind the data).

Observed, same traffic code, only gates.js differing: with the gates.js the 4 Nov reviewer ran (18:34Z) `bridge.orphan`
0 frames; with the working-tree gates.js (modified 20:06Z) **874–890 frames, 13 stands** — a bridge still > 50 %
extended with no aircraft within 10 m of its door target: E13/1 18 s (k 0.64, no aircraft near), G13/1 + G13/2 10 s
(door 23 m away), E12/1 9 s, D1/1 7 s, G9/1 + G9/2 7 s (SIA31's push from G9, 17:50:13Z), F21/1, E11/1, E6/1, B9/1, D10/1.

Inferred: on the screen these bridges hang extended toward an aircraft that is already pushing back. Please either
honour `s` for a departure's undock (the request is only made for departures and removals: `opt.fast`), or tell me the
duration you will use and I will hold the body until the cab is off the door (the trade-off is a lag of `T − 6 s`
behind the data on every push-back; the review asked for neither the lag nor the orphan).

### 2b. G8 bridge 1 rest cab vs a B77W at the stop (information)

With UAL1180 B77W at G8 the rest cab of bridge 1 is 2.1 m (0.9 R fuselage samples) from the fuselage at the B777
family stop and 0.9 m at 1.2 m past it (`tools/live/invariants.mjs` counted 4 fuselage points of its rectangular
fuselage inside the cab at 1.2 m past, 368 frames). The engine no longer lets a body run past its stop point (see
realtime_impl.md Step 6), so nothing is needed; noted because the raw reports of this aircraft at G8 lie ~9 m further
in than the B777 stop (median z 67 vs 76.6 m): either the B777 stop or the app's antenna offset for the 777
(0.2 L = 14.7 m, `traffic.js antOf`) is off for this airframe — see §3.

## 3. Aircraft / static workflows: antenna reference of the B777 (question)

`static_fixup.md` §1.6 measured the per-family ADS-B reference (A32x 1.8 m behind the nose, B737 9.4, E-Jets 13.4, A220
5.7 m). The B777 is not in that list. UAL1180 N2352U (B77W) parked at G8 on 4 Nov 17:51–17:52Z reported a median position
~9.6 m further along the stand axis than the app's B777 stop + 0.2 L antenna offset would put it. Please add the B777
(and B787 / A350) family references when you next run the per-family medians, so `antOf` can use them.

---------------------------------------------------------------------------------------------------------------------

# Round 2 (fix round of the close-out review, 2026-11-05): what changed, numbers, requests

Evidence: `tools/live/invariants.mjs` at 10 Hz on the relay-merge replay of **every recorded hour** (`refs/cache/rec`,
4 Nov 17:43:04 – 5 Nov 02:29:58Z, checked 17:48:04Z on: 8.70 h, 313,148 frames; 257 push-backs from contact stands), fed
with `gates_full` (the `/api/gates` payloads the browser gets; invariants.mjs now reads them lazily — a full day is ~1 MB of
JSON per minute — and keeps every engine event, `--events`). "Before" = the code at the start of this round (frozen copy:
js/live, js/aircraft, js/world, data, tools/live of 5 Nov 02:27Z, today's gates.js); "after" = the working tree. The
reviewer's 45-min window (17:48–18:33Z) was re-run traced for the cases named in the findings. Scratch scripts and outputs:
`scratchpad/r2/` (dep_signals.mjs, dep_join.py, cmp.py, run_inv.sh, run_trace.sh). One flysfo snapshot was fetched with
`tools/live/gatecheck.py fetch` (05 Nov 02:49:44Z, cached in `refs/cache/gate_truth/`, gitignored, listed by sync.py as
before) to measure SFO's actual off-block times. No browser renders.

## Departure timing measured on the recording (realtime-v6, bridges-v1)

For each of the 257 push-backs from contact stands, the raw reports of that aircraft at its stand before the push
(observed; `dep_signals.mjs` + `dep_join.py`, push = first raw motion > 2 m, else the engine's off-block):

| Signal | n | lead before the push, s (p10 / p25 / p50 / p75 / p90) | note |
|---|---|---|---|
| transponder on again at the stand (first report after > 10 min silence) | 223 of 257 (87 %) | 9 / 44 / 138 / 369 / 1,173 | 26 > 15 min, 9 > 30 min, 0 > 60 min |
| first report at the stand with the departure callsign | 257 | 3 / 40 / 148 / 516 / 1,701 | appears with the transponder |
| first report with the departure squawk | 245 | 8 / 47 / 152 / 516 / 1,408 | idem |
| the 28 that kept transmitting since arrival: callsign change / squawk change | 18 / 25 | 18–115 min / 5–38 min before the push | too early to time a retraction |
| SFO scheduled off-block (as of the 18:01Z snapshot) | 100 | push − sched: −1,794 / −265 / 96 / 754 / 5,261 | within 5 min for 38 of 100 |
| SFO actual off-block (02:49Z snapshot) | 62 | push − actual: 12 / 54 / 153 / 324 / 837 | published only after the event |

Inferred: the only usable early signal in the data is the transponder coming on at the stand. traffic.js
`departureSignal()` = that (`xpdrOnAt`: a parked aircraft heard again where it is parked after ≥ 10 min of silence, or a
track first heard parked ≥ 10 min after the feed started). On it, `earlyUndock()` → `onGateChange(g, null, {early})` →
gates.js `undockEarly()` (sheet rates; the aircraft stays drawn on its stand). An aircraft already signalled when it settles
is not docked at all. A signal with no push within `EARLY_MAX_MS` = 30 min (4 % of the leads), or the aircraft falling
silent again at its stand, is taken back (`cancelEarly` → syncBridge re-docks → gates.js `redock`). On the replay (after):
203 signals (120 retractions of a docked bridge, 83 no-dock), 175 (86 %) followed by the push within 30 min (lead p10 / p50
/ p90 39 / 170 / 873 s), 28 not; 42 taken back (36 silent again, 6 no push in 30 min).

The fallback hold (ctlGround): `pushClearEta(G) > 0` **or** `extension(G) > 0.5` (the owner's rule: a departure never
leaves its bridge > 50 % extended), ≤ `HOLD_MAX_MS` 60 s (never reached on the replay), with the retraction hurried
(gates.js `hurryUndock`) as soon as the body is held while its target moves; the body then catches up at ≤ 1 m/s over the
push speed. A re-placement (fade) of a body whose bridge is still out waits the same way (`cutHeldForBridge`). The squeeze
fallback (`a.dur = s * 1000 * k`) is gone from app.js and invariants.mjs.

## Dispositions (numbers: all hours before → after unless "window")

| Finding | Disposition | Root cause / change | Evidence |
|---|---|---|---|
| realtime-v1 (major) JAL2 wrong-way swing into A1 | fixed | `dockPath()` replaces the Bezier: the body's own unicycle drive from its pose and heading, single turn when it fits, R 12–60 m, aligned ≥ max(8 m, 0.25 L) before the stop; else a straight drive (stop ≤ 30° off the nose) or no silent dock. Target heading = the drive's heading; steering aims at the drive's main-gear track 0.5 R + 4 m ahead (`o.look`) — with the old 5 m look-ahead the B77W turned at its 8 m steering limit and snaked ±10°. | window trace 868056: body heading 28.1 → 22 → 14.8 → −1.1 → −14.8 → −22.0 → −20.3, one left turn at ≤ 3.3°/s, body ≤ 3 m from its target (before: 29.7 → 54.6 → −68.0 → −19, 13.8°/s, 24.5 m); raw 28.1 → 343.1 single left turn. 4 other silent docks unchanged (SKW6276, AAL76, AAL1849; SKW5970 is now data-driven). All hours: silent docks 58 → 49, 12 straight, 84 refused (no drive fits) |
| realtime-v2 (major) pavement | rejected here (static data) | the remaining cells are off the rendered mask AND the OSM net; the drawn positions follow the data (the gear points are the reported tracks). | all hours: offpave.mask 567,115 → 566,714 frames (263 aircraft), offpave.union 147,399 → 147,147 (158). Cells for the static track below (§R2.3) |
| realtime-v3 (minor) push recognised late | fixed | a track never seen moving forward (`fwdSeen`: a chord within 60° of the nose, or > 10 kt; kept in the turn memo) is a push-back on its first chord against the nose; a candidate report moves along its chord (no forward dead reckoning); a push stand found on a later report is written into the off-block event. | window off-blocks: UAL2322 B2 18:18:33.4 → 18:18:26.8, SKW5510 F5 18:04:22.0 → 18:04:16.0 (stand F5 kept), UAL2177 E7 18:12:29.5 → 18:12:26.4; UAL875 B11S 18:29:40.8 unchanged (its first chords were < 3 m). gnd.spin window 15 → 14. All hours: pushFirstSeen 150, pushCand 225 → 65 |
| realtime-v4 (minor) overshoot + reverse | fixed | the silent-dock speed profile stays under √(2·0.5·remaining); dead reckoning into a stop mark brakes at 0.5 m/s²; a body at rest up to 12 m in front of the data's parked pose is accepted while it is not > 2 m past the type's stop mark and not in a rest bridge. | window: SKW5970 F5 overshoot 2.8 → ~1 m past the mark, reversal 2.6 m (before) / 9 m (intermediate) → 0; AAL1849 B20 reversal 0.6 m → 0 (0.8 m past, accepted). All hours gnd.reverse 196 frames / 13 aircraft → 260 / 4 (EIN961 83 frames at a 22:54:53Z data glitch that re-placed 5 aircraft at once) |
| realtime-v5 (minor) fade re-placements | partly fixed | push ends: tow pivot about the main gear (≤ 1.5°/s, then the < 8 m residual is accepted); stands: residual up to 4 m / 15° accepted outside rest bridges, ×1.5 lock heading tolerance while docked, lock kept once the departure is signalled; heading-less parked bodies keep their drawn heading. **Rejected** for VJT720 / EJM750: their 90° / 93° change is the first true_heading report (VJT720 298.1° after 239 s of heading-less reports, EJM750 300.9° after 111 s) — the guess is corrected, not kept. | window cut.gnd_sfo 8 → 2 (only those two). All hours cut.gnd_sfo 208 events / 133 aircraft → 141 / 92; cut_repark 184 → 117 |
| realtime-v6 (minor) bridge > 50 % extended after the push | fixed (12 ghost cases left) | see "Departure timing" above: early undock on the transponder signal, hold until pushClearEta 0 and extension ≤ 0.5, hurried retraction, re-placements held. Remaining: 12 bridges (G7, G13, G1, E8 ...) docked to a SILENT aircraft that a live arrival drives into (GroundPhysics ghost → removed at once, k 0.99, 17–24 s of hurried retraction); the early removal I added (arrival heading into that stand) did not catch them — those ghosts were not the stand's occupant of record. | all hours bridge.orphan 14,395 frames / 88 stands → 1,824 / 12; bridge.attached.moving 0 → 0; window 973 → 0. Cost: lag.gnd_30m 19,848 → 24,811 frames (97 → 116 aircraft; e.g. UAL543 / AAL491 / UAL1046 pushes held 30–60 s), bridgeHoldMoving 1,146 s over 279 off-blocks; holdCapped 0 |
| realtime-v7 (minor) card shows the later departure | fixed | `planFor`: for a same-number turn, the record of the stand the aircraft is at; off a stand, the arrival while its block-in is pending (< 10 min ago or ahead). | card replay ab3a0c (UAL743): 'SFO → MCO' 1,513 rows → 'GEG → SFO · per SFO', 'Gate E6 · per SFO ✓ (arrival gate)'; the VRS note that remains is genuine (VRS says BOI → SFO) |
| realtime-v8 (minor) line-up / roll start | partly fixed | 'Lined up' only once the drawn body is within 15° of the runway heading (displayPhase); a rolling target while the label still says lined up counts as roll lag in the checker. The ramp of the back-dated start was tried and **reverted**: it made lag.roll 507 → 557 and lag.air 0 → 202 frames (window) — the body accelerates less toward a ramped target. The fixer's "~4 s late" claim is **refuted**: AAL1732's rolling report (17:58:35.66Z) was sent by the relay at 36.83 (1.2 s); the lag comes from the 8.6 s report gap in which the roll began. | all hours rwy.lineup_hdg 224 frames / 41 aircraft → 0; lag.roll_100m 2,242 → 2,242; gnd.acc.runway 15,289 → 15,289 |
| orch-2 (major) F19 / F20 1.9 m on SFO's path | fixed | `standFits` applies `types_ok` on SFO's path where `types_ok_all_paths` (F19, F20); `blocked()` honours `excl_types` both ways (`exclTypeHits`; `'@N:T'` entries; a silent neighbour is replaced like `excl`); `docking()` skips blocked stands. The checker's APP model (tools/stands/geom.py `accepted_types(app_rule=True)`) now models the same rule — a one-line change in the static track's file, see §R2.3. | `python3 tools/sat/check.py`: APP ISSUES 1 → 0, ISSUES 0 → 0. Unit test (scratch t_excl.mjs): 10/10 (F19 B772 blocks F18 / F20 and back; C9 B763 ↔ C11; C8 B752 ↔ C10; a silent neighbour does not block SFO's path) |

## Found on the all-hours replay and fixed (not in the findings)

| Class | Before → after (all hours) | Root cause / change |
|---|---|---|
| bridge.hit.fus / hit_at_rest | 52,379 / 51,856 frames (11 aircraft) → 310 / 322 (6) | (1) `gateByName` matched SFO's **C9V** (the MARS position for a 767) to **C9** (C9 is C9V's base and comes first): DAL672 B763 was parked 11.6 m beside C9's lead-in with C9 L1's rest cab in its fuselage for 68 min. Exact name first now. (2) UAL878 B77W came to rest 1.1 m past G8's stop with G8 L1's drive column / stair in its fuselage for 18 min: a rest pose past the stop is accepted only outside the rest bridges (`fusInRestBridge`). |
| building | 486 → 0 | (same; AAR212 / DLH455 A359) |
| overlap.gnd | 1,646 frames (30 pairs) → 660 (24) | a body driving into its stand (data already stopped there, body not yet at the pose) was checked by GroundPhysics at its stand pose; now it is a moving body, so a silent aircraft in its way is removed before the contact (EVA028 through EVA018 at A1, 1,283 m², gone). Left: N7378S / VJT720 (both parked, 1 m², free parking), AAL2651 / AAL2846, JAL2 / KLM373 ... |
| phase.gate_far_from_stand | 520 → 213 | (the C9V and silent-dock fixes) |
| clear.taxi | 265 → 169 | |

## Unchanged, with the reason

- `lag.gnd_30m.other_airfield`, `cut.*_other`, `vert.float.other_airfield`, `air.*`, `rwy.roll_hdg`, `gnd.acc.runway`:
  untouched code paths (other airfields, air, runway rolls); identical counts.
- `clear.stand` 90,121 → 91,127: JTL904 / LXJ511 business jets 2.98 m apart for 97 min (free parking at the FBO ramp,
  below the 3 m code A/B clearance; GroundPhysics keeps them non-overlapping only), UAL2416 / UAL638 at D7 / D6 3.86 m
  (surveyed stands, static data).
- Runway truth: landings 273, take-offs 284 — 0 missed, 0 wrong runway, both runs.

## R2.1 Bridges track (`js/live/gates.js`)

1. The Round 2 API is used as specified: `undockEarly` on traffic.js `earlyUndock` (`opt.early`), `redock` via the same-type
   `setOccupant`, `hurryUndock` on `opt.fast`, `pushClearEta` / `undockEta` / `extension` as `traffic.pushClearEta` /
   `undockEta` / `bridgeK`. bridge.orphan 14,395 → 1,824 frames; 0 in the review window.
2. Rest bridges touched by aircraft on the replay (after; each `k` 0 = at rest): D5 L1 tunnel by UAL626 A319 taxiing past at
   2.6 m/s (21:51:50Z, 149 frames, world (−490, 234)); G5 L1 cab by DLH454 A359 creeping in (20:38:45Z, 46); A2 L2 tunnel by
   KLM373 B772 at the gate (20:23:27Z, 38); E9 L1 cab by UAL2262 (00:24:01Z, 33); G1 L2 tunnel by UAL59's wing (00:19:56Z,
   35). Please check whether these rest poses clear the stands' lead-ins / neighbouring taxilanes; I will trace the bodies.
3. G8 L1 at rest is ~2 m from a B777 at its stop (drive column, stair): any overshoot meets it (UAL878, 4 Nov 02:12Z).

## R2.2 Aircraft / static: B777 antenna (unchanged request §3)

## R2.3 Static track (`tools/stands/*`, `data/sfo_pavement.*`, the mask)

1. **tools/stands/geom.py** `accepted_types(app_rule=True)`: one line changed by me so that the APP view models the new
   standFits (types_ok on SFO's path where `types_ok_all_paths`); please keep it and update the docstrings of geom.py /
   check_stands.py (lines 7–11: "no types_ok on SFO's path" is no longer true for F19 / F20). `excl_types` needs nothing in
   the checker (the APP pairs are ≥ 3 m now).
2. Off both the mask and the OSM net, all hours (after; cells of 25 m, frames / aircraft): (−550, −350) 37.62196,
   −122.38167 553 / 30 (FFT1229, DAL977, ASA613 ... all moving); (−550, −375) 315 / 29; (−525, −375) 263 / 24;
   (−650, −175) 155 / 15; (−350, 300) 153 / 14 (taxiway W across 1L/1R); (−1450, −175) 37.62038, −122.39186 870 / 12
   (UAL1175, UAL369, ANA7 — G/F apron edge); (−1050, 1025) 633 / 7 (south of pier B); (−1400, −50) 252 / 7; (−600, −250)
   115 / 7; (−800, −925) FBO ramp. Please add them, or tell me which are not pavement.

---------------------------------------------------------------------------------------------------------------------

# Round 2 of closeout2 (5 Nov 2026): fixes for the verifier findings v1–v10 of wf_14fa97a9

What changed is in `docs/research/realtime_impl.md`, "Step 8". The numbers come from `tools/live/invariants.mjs`, run at
10 Hz on the relay-merge replay of the recording, with `gates_full`:
- Stream: `tools/live/build_stream.py --gates-full` over `refs/cache/rec`, built at the start of this round.
- Span: 4 Nov 17:43:04Z to 5 Nov 08:59:58Z, checked from 17:48:04Z: **15.20 h, 547,145 frames**, 415 landings and 429
  take-offs.
- The verifier's run was 8.7 h. The hours recorded after 09:00Z on 5 Nov are NOT in this replay: "before" and "after"
  must run on the same stream, and one pair of 24-h runs takes about 5 h on the shared 4 CPUs. Anyone can rebuild it
  with `build_stream.py`.
- "Before" = a frozen copy of the tree at the start of this round: traffic.js `c4e94ad2…`, which is the code the verifier
  ran.
- "After" = a frozen copy of the final code: traffic.js `4ff3753c…`, ground.js `0a5d8f0b…`.
- Both use the same gates.js (`6a0aef2d…`) and the same data. Both use this round's invariants.mjs, so every class
  compares one to one.
- Targeted window traces were run for the named cases (scratch `r3/t_*`).
- `python3 tools/sat/check.py`: APP ISSUES 0, ISSUES 0, WARNINGS 17. Unit test of the stand rules (scratch
  `r3/scripts/t_excl3.mjs`, which calls `blocked` / `matchGate` / `occupy` directly): 8/8.
- No browser renders.

## New checker classes (tools/live/invariants.mjs)

They read the engine's own flags, so they do not depend on the code root.

| Class | Meaning |
|---|---|
| `bridge.dock_flap` (+ `meta.flap`) | A dock within 30 s of the previous undock at the same stand, one count per event. `meta.flap` also holds docks / undocks / locks / unlocks per track. |
| `bridge.parked_undocked` | At rest at a contact stand for > 180 s with bridges < 50 % extended, not signalled / leaving / pushing. The engine never asked for its bridge. |
| `bridge.refused` | The same, but the engine asked and gates.js docks none of the stand's bridges at the drawn pose. |
| `rwy.lineup_hdg` | Now reads the ENGINE's phase at display time (v7). The old label-based count is `rwy.lineup_hdg.label`. |
| `--allkeys cls,…` | Lists every key of those classes in the report (`all`), not only the top 12. |

## Classes and counters (all hours, before → after)

| Class | before frames / keys | after frames / keys |
|---|---|---|
| `bridge.orphan` | 4,672 / 23 | 5,323 / 31 |
| `bridge.hit.fus` | 2,036 / 12 | 1,717 / 7 |
| `bridge.hit_at_rest` | 1,296 / 11 | 873 / 7 |
| `bridge.hit.wing` | 297 / 3 | 35 / 1 |
| `bridge.hit.tail` | 386 / 2 | 383 / 1 |
| `bridge.dock_flap` | 31,177 / 7 | 0 / 0 |
| `bridge.parked_undocked` | 48,967 / 5 | 1 / 1 |
| `bridge.refused` | 6,987,287 / 101 | 1,079,108 / 19 |
| `building` | 803 / 1 | 803 / 1 |
| `overlap.gnd` | 1,471 / 50 | 948 / 35 |
| `clear.stand` | 300,555 / 18 | 414,634 / 12 |
| `clear.taxi` | 322 / 51 | 209 / 36 |
| `cut.gnd_sfo` | 261 / 163 | 280 / 173 |
| `gnd.reverse` | 260 / 4 | 10 / 3 |
| `gnd.spin` | 235 / 53 | 256 / 52 |
| `gnd.acc.taxi` | 506 / 115 | 497 / 114 |
| `lag.gnd_30m` | 45,191 / 173 | 40,953 / 170 |
| `phase.gate_far_from_stand` | 334 / 8 | 368 / 8 |
| `phase.flicker` | 395 / 127 | 384 / 124 |
| `rwy.lineup_hdg` | 337 / 59 | 337 / 59 |
| `rwy.lineup_hdg.label` | 0 / 0 | 0 / 0 |
| `rwy.roll_hdg` | 557 / 16 | 557 / 16 |
| `lag.roll_100m` | 3,305 / 23 | 3,305 / 23 |
| `offpave.mask` | 1,375,355 / 377 | 1,375,584 / 377 |
| `offpave.union` | 471,050 / 236 | 471,479 / 237 |

Unchanged (identical counts): `air.acc`, `air.lat`, `air.turn`, `air.vacc`, `cut.air_other`, `cut.air_sfo`, `cut.gnd_other`, `gnd.jerk`, `gnd.speed.taxi`, `lag.air_150m`, `phase.gndphase_in_air`, `phase.pushback_forward`, `rwy.change.final`, `rwy.truth.landing_extra`, `rwy.truth.landing_missed`, `rwy.truth.takeoff_extra`, `vert.float.other_airfield`.
Other changed: `gnd.acc.runway` 22,834 / 222 → 22,799 / 222; `lag.gnd_30m.other_airfield` 316,884 / 254 → 317,219 / 255.

| Engine counter | before | after |
|---|---|---|
| meta.flap docks | 31,628 | 445 |
| meta.flap undocks | 31,585 | 402 |
| meta.flap locks | 40,161 | 2,063 |
| meta.flap unlocks | 40,091 | 1,992 |
| meta.flap dockFlaps | 31,177 | 0 |
| meta.flap lockFlaps | 38,190 | 102 |
| silentDocks | 64 | 73 |
| silentDockHere | - | 13 |
| silentDockStraight | 17 | 18 |
| silentDockBehind | 151 | 96 |
| silentDockConflict | - | 12 |
| silentDockHolds | - | - |
| movingLost | 1,002 | 995 |
| ghostAhead | 21 | 18 |
| ghostAheadKept | - | 511 |
| aheadSkipPlan | - | 30 |
| bridgeAhead | - | 49 |
| drop_ghost | 46 | 32 |
| drop_replaced | 33 | 27 |
| dropWaitCut | - | 11 |
| earlyUndocks | 186 | 212 |
| earlyNoDock | 119 | 97 |
| earlyCancelled | 68 | 57 |
| restAccepted | 140 | 87 |
| restAcceptedPast | 304 | 338 |
| restNoBridge | - | 11 |
| restInBridgeOff | - | 1 |
| unlockReach | - | - |
| parkAtStopReach | - | 150 |
| intoTerminal | - | 56 |
| drOvershoot | - | 78 |
| firstAtStand | - | 3 |
| inBlockStale | - | 20 |
| towPivotS | 2,342 | 1,962 |
| cutHeldForBridge | 26 | 29 |
| cut_repark | 204 | 189 |
| inBlockDup | 4 | 2 |
| exclTypeConflict | - | 2 |
| sfoStandRefused | - | 1 |

## Dispositions (v1–v10 of the wf_14fa97a9 verifier; numbers are all hours, before → after, unless "window")

| Finding | Disposition | Root cause / change | Evidence |
|---|---|---|---|
| v1 (major) ghost-ahead removals of aircraft that were really parked | fixed | **Root cause:** the round-2 rule removed a silent occupant whenever an arrival 300–400 m away headed roughly toward its stand. It used the callsign `planStand` and needed only ≥ 2 min of silence, and silence proves nothing at a stand.<br>**Now** an occupant is removed ahead of an arrival only when both hold:<br>(1) Geometry: the arrival's own report is on that stand's lead-in, ≤ max(60 m, 1.5 L) short of the stop, lateral ≤ 4 m + 8 %, within 20° of the stand heading (`onLeadInClose`).<br>(2) SFO's evidence that the occupant left (`stalePlanGone`): its departure's actual block-out is past, or all its stand windows there have ended, or SFO allocates the stand to the arrival's own ARRIVAL record now and lists no window of the occupant there.<br>The arrival's stand comes from its arrival record (`arrStand`), never from `planStand`. Without evidence the occupant stays drawn and at most its bridge starts back (v10). | 'ahead' removals 21 → 18, each with evidence (evidence: window 12, alloc 5, blockout 1).<br>Removed occupants heard again later at the same stand: 13 aircraft / 801 aircraft-min → 0 / 0. The verifier counted 10 / 506 on 8.7 h.<br>exclType removals 3 → 0.<br>The duplicate / repeated in-blocks are gone: UAL194 G6, UAL2610 E12, UAL300 F19, ASA595 B13, UAL2225 F21, UAL2262 E9, UAL755 F17, UAL1777 E2, UAL1149 D15, UAL2400 D12, UAL796 F21, SKW250X B24.<br>UAL2262 no longer enters E9 L1's rest cab. |
| v2 (major) rest acceptance vs lock tolerance: dock / undock flapping | fixed | **One tolerance.** The lock keeps the parked-pose estimate it was accepted against (`lock.ref`). It is released only when the estimate has moved by more than LOCK_M / LOCK_DEG since then AND lies outside them from the lock.<br>**Bridge reach** is part of the acceptance:<br>- A rest pose with a residual at a contact stand is kept only where the stand's L1 bridge docks it, or where the bridge cannot dock the parked pose either (`restDockOk`). `traffic.canDock` = gates.js `makePlan` on that pose, hooked in app.js and invariants.mjs.<br>- A lock the bridge cannot reach is released when the parked pose is reachable (`lockOutOfReach`).<br>- Reports up to 15 m short of the stop are parked at the stop when only the stop is in reach (`updatePark`, inferred).<br>**Checker:** new classes `bridge.dock_flap`, `bridge.parked_undocked` and `bridge.refused`, plus `meta.flap`. | docks / undocks / locks / unlocks: 31,628 / 31,585 / 40,161 / 40,091 → 445 / 402 / 2,063 / 1,992 (meta.flap).<br>bridge.dock_flap 31,177 → 0. DAL2267 C5 (18,089 pairs) and SKW5970 F5 (13,086) → 0.<br>bridge.parked_undocked 48,967 frames / 5 → 1 frame / 1.<br>bridge.refused 6.99 M frames / 101 aircraft → 1.08 M frames / 19 aircraft. What is left is listed in R3.2. |
| v3 (major) silent docks lost at / just past the stop | fixed | (1) **'here'**: a silent arrival already at the stop (−3 m ≤ along < 3 m, lateral < 3 m, < 15° off) is docked where it is (`path.here`).<br>(2) **Dead reckoning** of an arrival stops at the stop mark of the contact stand whose lead-in its last report is on (`drStand`: ≤ 150 m out, lateral ≤ 8 m + 10 %, ≤ 35°, SFO's stand preferred). This holds with or without a dock or a matched stand.<br>(3) An arrival matched to its stand only after it went silent now logs its in-block (`silent: 'stale'`). | In-blocked again: DAL1920 C11 19:08:18Z, UAL1905 D7 19:29:28Z, SWA2766 D6 21:35:41Z, AAL3176 B27 21:50:26Z.<br>UAL1372 D8 19:14:49Z: it stopped 3.8 m short of D8's stop and 3.4 m beside its lead-in (raw reports), so neither 'here' nor a straight drive applies. It is placed at D8 when it goes stale, and its in-block is now logged (window `t_ual1372_a5b`; R3.1 asks about D8's lead-in).<br>silentDocks 64 → 73 (here 13); movingLost 1,002 → 995; stale in-blocks 20: 19 arrivals with no in-block at all before, plus UAL1914 D15, now logged at its arrival (00:56Z) instead of 01:58Z after a false removal. 16 of them later push from that same stand. |
| v4 (major) long silent drives through other aircraft | fixed | The drive is checked against every aircraft drawn on the ground: planforms every 3 m along the path, no margin (`driveConflict`).<br>- A conflict refuses the docking.<br>- One that appears during the drive holds it (`silentHold`: the next 20 m checked every 0.5 s, the drive clock frozen).<br>A silent docking waits DOCK_WAIT_MS before its bridge moves, like a reported arrival. That wait is the window in which resuming data can still move the aircraft. A silent aircraft cannot confirm its stop any other way. | UAL2225 A319 no longer drives through UAL1554 (that overlap, 77 frames → 0). It is re-placed 72.7 m back when the data resumes; that jump is in the data itself.<br>silentDockConflict refusals 12; silentDockHolds 0. |
| v5 (major) orch-2 stand rules contradicted by the recording | fixed (data questions → static track, R3.1) | `excl_types` no longer block (`blocked()`) and no longer remove a silent neighbour (`occupy()`). A conflict is logged (`excl-type-conflict`) and only steers a silent docking's geometric candidates.<br>`types_ok` on SFO's path also accepts a smaller member of a listed type's stop-point family (`typesOkHas`: same `familyOf`, span and length ≤ a listed type; B38M under B39M at F19).<br>Refused SFO allocations are logged (`sfo-stand-refused`). | UAL626 B38M F19 in-block 19:02:44Z (src sfo) is back. UAL2467 F20 20:47:56Z is back.<br>exclType removals → 0: UAL2358 stays at F19 from 20:16Z; DAL363 stays at C8 23:21–00:31Z; UAL574 stays at F20.<br>excl-type-conflict 2: UAL2467 F20 vs F19 B772, ACA566 C10 vs C8 B752. sfo-stand-refused 1: UAL649 D5, 'class'.<br>`check.py`: APP ISSUES 0, ISSUES 0. `t_excl3.mjs` 8/8. `TR.__standFits` never existed; the test now goes through `matchGate` / `blocked` / `occupy`. |
| v6 (minor) 'silent' early cancel plus a 30-min block | fixed (retraction delay deferred) | A 'silent' cancel now needs XPDR_OFF_MS (10 min) without a report at the stand (before: `tr.stale`, 75 s). It uses up the signal (`xpdrOnAt` cleared) without blocking the next one. Only 'no push' blocks. | Cancels: silent 60 → 20, no push 8 → 17. Cancel followed by the push within 30 min: 40 → 13.<br>**Deferred:** moving the retraction start toward the measured lead.<br>- The only usable early signal is the transponder coming on at the stand: lead p10 / p50 / p90 33 / 169 / 982 s before the push.<br>- SFO's scheduled off-block is too noisy (push − sched: p10 −30 min, p90 +88 min; Round 2 table).<br>Delaying the start would leave the bridge > 50 % out at more pushes. |
| v7 (minor) `rwy.lineup_hdg` drop came from relabelling | metric fixed; steering change rejected (evidence) | `rwy.lineup_hdg` now reads the engine's phase at display time (`tr.phaseAt`), not the label. The label count is kept as `rwy.lineup_hdg.label`. | Engine-phase count: 337 frames / 59 aircraft in both runs, max 10 frames (1.0 s) per episode. Each is the last second of the turn onto the runway at < 0.5 m/s (SKW5937, SKW6440, UAL901: 10 frames each). The body does reach the runway heading, so the steering is not changed.<br>rwy.lineup_hdg.label 0. rwy.roll_hdg and lag.roll_100m unchanged. |
| v8 (minor) first report rolls the body forward | fixed | The first reports of a slow ground track (< 8 kt) carry no velocity until one gives a chord (`dirUnknown`). A first moving report without a heading at a contact stand takes the stand's heading (nose in) and may be a push (`firstAtStand`, `pushOk`). | Window on the final code (`t_v8_a6`): UAL2322 at B2 stays at (−997.4, 588.6) until its push starts at 18:18:29.5Z, so 0 m of forward roll (was 3.3 m). Off-block 18:18:26.8Z.<br>Off-block events 431 → 430; pushFirstSeen 190 → 189. |
| v9 (minor) tow pivot; re-placement held for the bridge | fixed | (1) The tow pivot runs only while the machine phase is push-back, or ≤ TOW_MS (90 s) after it (`towOn`).<br>(2) A re-placement waits for the bridge only while the data is within CUT_HOLD_M (100 m). Otherwise the bridge is hurried and the body fades at once. | towPivotS 2,342 → 1,962 s. cutHeldForBridge 26 → 29.<br>UAL2480 B752 at F22, 22:43:36Z: the body fades at once (its 156-frame lag.gnd_30m episode is gone). The cost is that its bridge retracts behind it: bridge.orphan F22 153 frames. |
| v10 (minor) dispositions that hold; v6 orphans still open | partly | v2 (pavement, static data) and the VJT720 / EJM750 rejections stand: offpave.mask 1,375,355 → 1,375,584 frames, offpave.union 471,050 → 471,479, untouched code.<br>**v6 remainder (orphans).** A ghost a live arrival drives into is no longer removed early without evidence (v1). Instead:<br>(a) Its bridge retracts as soon as the arrival is on that stand's lead-in. This covers the lead-in it docks to, SFO's stand for its arrival record, and the occupied stand whose lead-in its report is on (`leadInOccupied`: ≤ 90 m, ≤ 4 m + 6 %, ≤ 20°, < 10 kt). The retraction runs at the sheet's maximum rates (`retractAhead`, event `bridge-ahead`) and is skipped when SFO's plan contradicts it on both counts: the arrival is put at another stand AND the occupant is listed there now (`planAt`). The bridge docks again 90 s after the arrival was last seen there.<br>(b) A removed ghost that still waits for its bridge fades at once when the arrival reaches it (ground.js `dropWaitCut`), so it is never driven through. | bridge.orphan 4,672 frames / 23 keys → 5,323 frames / 31 keys (after4, before the contact fade: 3,753 / 22). The verifier's 1,824 / 12 was on 8.7 h.<br>bridge-ahead retractions 49: the arrival took that stand 30 times, another stand 17, none 2; 20 re-docked after "arrival gone".<br>overlap.gnd 1,471 / 50 → 948 / 35.<br>Left: ghosts with no forewarning. Example: G7 at 20:39:40Z, where UAL900 turned off the apron lane straight into G7, whose lead-in is short and perpendicular to the lane. The bridge then retracts from an empty stand in 10–26 s. |

## Found on the all-hours replay and fixed (not in the findings)

| Case | Root cause | Change |
|---|---|---|
| Bridges that cannot reach the drawn pose (`bridge.refused`: 101 aircraft, 6.99 M frames before) | The rest and lock acceptance took poses a few metres off the stop without asking the bridge. | `restDockOk`, `lockOutOfReach`, `updatePark` stop-in-reach (v2 row). |
| SWA375 B38M at D3, 04:33Z: fuselage in D3 L1's rest cab for 75 s (`bridge.hit.fus` 753 frames) | It came to rest 2.4 m / 11° short of its parked pose before the stand was matched. The off-stand "it is there" rest rule did not look at rest bridges; the at-stand rule has done so since round 1. | `restBridgeMove`: off a stand, a body whose fuselage is in a rest bridge while the reported pose is clear creeps on or is re-placed. |
| ANZ8 / UAL900 at G7, 20:40Z: the replaced occupant was driven through for 35 s (`overlap.gnd` 348 frames, intermediate run) | A removed body waits until its bridge is ≤ 30 % extended, and GroundPhysics ignored bodies being removed. | ground.js: such a body fades at once when a live aircraft drives into it (`dropWaitCut`). |
| Bridge-ahead retractions for arrivals that went elsewhere: 26 of 57 on an intermediate run, among them UAL1114 at E3 three times in 35 min (E3's lead-in lies along the E-pier alley) | Geometry alone (on the lead-in, ≤ 90 m, ≤ 20°) cannot tell E3's lead-in from the alley. | Skipped when SFO's plan contradicts the retraction on both counts: it puts the arrival at another stand AND lists the occupant at that stand now (`planAt`). Result: 19 of 49, UAL1114 / E3 gone. Either signal alone dropped 9 needed retractions (all-hours bridge.orphan 5,965). |
| Found on intermediate runs of this round and fixed before the final run: SWR39 A333 first heard pushing out of G5 with no heading (driven nose-first into the pier with the guessed 0°); UAL888 B772 at G3, a GNSS jump of 11 m along the nose drew it into the terminal for 16 s; EVA018 B77W into A1, the 1 m drive margin refused the silent docking and the dead-reckoned body swung into the B pier when the data came back behind it | — | `firstAtStand` / `pushNoseGuess`; `intoTerminal`; no drive margin plus `drOvershoot` (a dead-reckoned body that the next report puts ≥ 25 m behind or beside is re-placed with a fade, not driven back). |

## Trade-offs left, with the reason

- **`bridge.orphan` 5,323 frames / 31 keys (after4, before the contact fade: 3,753 / 22).** Each case is a ghost: a silent occupant that left unseen and is removed when a live arrival
  drives in. A bridge then retracts at the sheet's maximum rates from an empty stand for 10–26 s.
  - Holding the ghost until its bridge is clear (intermediate run) cost a 35-s overlap with the arrival
    (`overlap.gnd` 1,471 → 2,421). A collision is worse than a bridge retracting late, so the ghost now fades at contact.
  - Removing the ghost earlier needs evidence that it left, and v1 forbids removing on silence alone.
  - Retracting at the end of SFO's stand window would leave many really parked aircraft without a bridge: push minus
    scheduled off-block reaches p90 +88 min, and 87 % of departures are silent at the stand.
  - By stand: A1 530 (2 bridges), G7 500 (2), G9 420 (2), G13 392 (2), A2 364 (2), G5 238, B10 227, E12 201, E3 180, G1 176 (2), B8 156, F22 153, E5 122, B11S 116, F19 113, B12 104, B5 98, F7 72, F16 66, B26 54, B27 52, B19 48, F20 48, B24 45, E6 16.
- **`clear.stand` 300,555 / 18 → 414,634 / 12.** The new case is F7 / F8 E75L at their type stops, 4.38 m apart (code C needs 4.5 m): SKW5440 and
  SKW5631 from 03:30Z. Before, both were parked short of the stop, where their bridges did not reach (`bridge.refused`:
  SKW5440 F8 227,596 frames, SKW5631 F7 196,121). This is the static question in R3.1 item 3.
- **`cut.gnd_sfo` 261 / 163 → 280 / 173.** These are the `drOvershoot` fades (78). Before, the body was driven back in a U-turn, which put
  EVA018 into the B pier.
- **Bridge-ahead retractions that re-dock** (20 of 49). The bridge moves out and back at an aircraft that stays parked. That
  is harmless, but it is not what a real bridge does.
- **`bridge.hit.fus` 2,036 / 12 → 1,717 / 7 (hit_at_rest 1,296 / 11 → 873 / 7).** Left:
  - UAL29D B789 at G13 (04:18Z, cab at k 0.68, also in "before": a docking cab into the fuselage);
  - DAL545 B739 taxiing past C4 L1's rest tunnel (07:09Z, 2 m/s);
  - UAL917 B772 pushing past G4 L2's rest cab (06:54Z);
  - KLM373 B772 at A2 against L2's rest tunnel (20:23Z);
  - DAL672 C9 (15 frames);
  - SWA375 D3 (30 frames, the last second of its taxi-in; the 75-s rest in the cab is fixed);
  - UAL1336 E9 (12 frames).

  These are rest-pose or docking-path questions for the bridges track. The rest poses were sent to them in Round 2 §R2.1
  item 2.

## R3.1 Static track (`data/sfo_stands.*`, `tools/stands/*`)

1. **excl_types contradicted by the recording (obs).** SFO parked, and the ADS-B reports place, these pairs together:
   F19 B772 (UAL2358 / UAL300, 20:16–21:55Z) beside F20 B752 (UAL2467 until 20:51Z; UAL574 / UAL1808 21:03–22:44Z), and
   C8 B752 (DAL363, 23:21–00:31Z) beside C10 BCS3 (ACA566, 00:05–00:53Z). traffic.js no longer enforces `excl_types`; it
   logs each case (`excl-type-conflict`: UAL2467 F20 vs F19 B772, ACA566 C10 vs C8 B752 on this replay). Please re-check the
   F19 / F20 and C8 / C10 geometry (stop points, lead-in headings) against these observed pairs: either the drawn poses are
   too close or the exclusions are not SFO's rule.
2. **types_ok family.** F19 lists B39M but not B38M; SFO planned UAL626 B38M at F19 (18:49–20:08Z) and it parked there.
   traffic.js now accepts a shorter member of a listed type's stop-point family (B38M under B39M; `typesOkHas`). I have NOT
   changed `tools/stands/geom.py accepted_types(app_rule=True)`; check.py gives APP ISSUES 0 either way (B38M at F19 is
   4.31 m from F20, 5.44 m from F18). Please either add B38M to F19's `types_ok` (and to any other stand that lists a MAX 9
   but not the MAX 8) or model the dominance there, so that the APP view stays one-to-one with traffic.js.
3. **E-Jet antenna reference (static_fixup.md §1.6, unchanged).** traffic.js uses `ANT = 0.2 L` (6.3 m on an E75L); your
   per-stand median is 13.4 m. The E-Jets parked at F5 / F7 / F8 / F9 sat 6.7–12 m short of the type stop, where their
   bridges do not reach them; traffic.js now parks them at the stop when only the stop is in reach (`updatePark`, inferred).
   At their stops F7 and F8 E75L are 4.38 m apart (`clear.stand`, need 4.5 m for code C; SKW5440 / SKW5631 03:30Z). Please
   confirm which of the two (the `type_stops` E-Jet stop points or the antenna offset) should carry the 7 m difference, and
   the F7 / F8 E-Jet stop clearance.
4. **D5 class.** SFO allocated D5 to UAL649 (06:55:09Z) and standFits refused it on the stand class (`sfo-stand-refused`,
   'class'). Please check D5's class / types against that allocation.
5. **D8 lead-in (obs).** UAL1372 A320 (a5a2cc), allocated D8 by SFO, crept in at 0.5 kt on track 281°. Its last report
   (19:14:50Z) was at 37.617525, −122.380471. That is 3.8 m short of the app's A320 stop for D8 and **3.4 m beside the
   stand line** (D8 hdg −79.5° in the world frame). Its departure report at 20:22:40Z was 3.5 m beside the line too. Please
   check D8's stand line against these reports.

## R3.2 Bridges track (`js/live/gates.js`)

1. **The stand's L1 bridge refuses the type at its STOP pose.** `makePlan` was run on the type's stop pose (scratch
   `r3/scripts/refstop.mjs`) for every (stand, type) left in `bridge.refused` after this round:
   F5 E75L (L1 slope 1:1.9, limit 1:4; SKW5929 131,267 frames, SKW5572, SKW5970), F5 B38M (1:2.4; UAL1274), G7 B738 (1:4.0; UAL1931), G8 B738 (1:3.7; UAL1243).
   If those slopes are the sheet's limits, these types should not be docked there, and the static track's `types_ok`
   should say so. Otherwise please widen the plan.
2. **The stop pose docks, the drawn pose does not** (the aircraft rests a few metres off its stop):
   G6 B38M / B39M (UAL1272, UAL469), G8 B38M (UAL2313), F19 B772 (UAL2358), G5 B753 (UAL373), F13 B739 (UAL2117), D11 CRJ7 (JZA840), D14 A320 (UAL677) at the stand pose; A13 B39M (UAL1118), B20 A321 (AAL2651), D7 A320 (UAL2416), F9 E170 (SKW5899), A9 B789 (EVA007) at their own reported pose.
   The engine side is mine (`updatePark` / `restDockOk` do not catch these yet). Please tell me if a pose tolerance in
   `makePlan` is the better place.
3. **API use.** As in Round 2; `undockEarly` now also takes `{ early: true, why: 'ahead' }` — a silent occupant's bridge
   retracting ahead of a live arrival on its lead-in (`retractAhead`), followed by `hurryUndock` (`fast`) — and `redock`
   (same-type `setOccupant`) when the arrival goes elsewhere (90 s after it was last seen on that lead-in).

## R3.3 Aircraft / static: antenna references

The B777 antenna question (§3) is still open; the E-Jet one is R3.1 item 3.

---------------------------------------------------------------------------------------------------------------------

# Round 3 (close-out round 3, fix round 1, 7 Nov 2026): findings realtime-1 … realtime-17

What changed is in `docs/research/realtime_impl.md`, "Step 9" (items 1–21); every change carries a "close-out round 3,
realtime-N" comment. Evidence:
- **Harness** (realtime-12): `tools/live/invariants.mjs` at 10 Hz, with the app's building grid (`buildingGrid(AIRPORT, 2,
  B3D_INTEGRATION.physics)`: the 3-D assets' footprints) and the bridges' own aircraft solid (gates.js `acHit`: tapered
  nose, wings, engines, swept tailplane; new class `bridge.hit.eng`). The same harness and data run before and after, so
  every class compares one to one.
- **Streams** (realtime-12): every recorded hour, `tools/live/build_stream.py --gates-full`. Segment A: 4 Nov 17:43Z – 6 Nov
  06:32Z, checked from 17:48:04Z, 1,322,125 frames. Segment B: 7 Nov 01:33 – 07:00Z, checked
  from 01:38:30Z, 192,885 frames. The gap between them is the machine's restart. SFO's plan
  (flysfo) exists in the cache only up to the 5 Nov 02:49Z snapshot. Later hours replay without it, as the app does when
  flysfo is unavailable, and every rule that needs SFO's evidence (block-out, windows, arrival record) is silent there.
- **Before** = a frozen copy of the tree at the start of this round: traffic.js `4ff3753c`, ground.js `0a5d8f0b`, app.js
  `39c5bc16`, the old taxi graph (`a093a28e`).
- **After** = the final code: traffic.js `80c8334c`, ground.js `9c33d2ff`, app.js `f3556b24`, the rebuilt
  `data/sfo_taxigraph.js` (`20d25128`).
- Both runs use gates.js `a93cce58`, invariants.mjs `cf6b186a` and the building footprints of
  `data/buildings3d/integration.js` `c869b8f3` (the integration track has changed that file since; the harness keeps the copy
  frozen with the roots). Roots and md5s: scratch `c3/realtime/root_before`, `root_after8` (`md5.txt`).
- The container restarted at 12:41Z, 14:41Z and 18:41Z on 7 Nov and at 02:42Z on 8 Nov, and each restart killed the replays that were running. The all-hours
  run on `root_after6` (18:46–21:21Z) found one new regression (item 20 below), and the run on `root_after7` (21:40Z – 00:11Z) one more
  (item 21). The final after runs ran on `root_after8`: segment A 00:11–02:30Z on 8 Nov, segment B 02:45–03:07Z (re-run after the
  02:42Z restart; its classes, events and counters equal the `root_after7` run of segment B).
- Window traces (`--trace hex`) for every named case. Scratch `c3/realtime/w/*`: one directory per window, `out.txt` and
  `trace.err`.
- No browser renders: nothing visual changed except the error overlay and the vehicle label.

## Dispositions

| Finding | Status | Root cause → change | Numbers (all hours, before → after; A = 4–6 Nov, B = 7 Nov) |
|---|---|---|---|
| realtime-1 (major) lock without an absolute bound | fixed | syncBridge kept a lock while the parked pose stayed within 6 m of the lock's REFERENCE, so the body could sit residual + 6 m off. Now a lock is released when it is further from the CURRENT parked pose than max(LOCK_M, residual accepted at lock time + 2 m) or max(LOCK_DEG, residual + 3°); lock.ref still damps the flapping. The accepted residual counts up to `LOCK_R0_MAX` (12 m, the largest rest residual the controller accepts): uncapped, a lock taken 60.7 m from its reference after a silent docking (EIN961 A333 at B5S) was kept for 99 min. | parked samples with the lock > 6 m from the parked pose: A 1,032 min > 6 m (97 > 8 m), max 60.69 m → 444 min > 6 m (311 > 8 m), max 60.69 m; B 265 min > 6 m (19 > 8 m), max 11.58 m → 10 min > 6 m (10 > 8 m), max 8.69 m. SWR35G (G5) is no longer removed. The re-locks left at 7–12 m (EVA008 G13, ACA743 D11) are bodies at the type's stop mark with the parked ESTIMATE short of it: the round-2 acceptance rule (body ≤ 2 m past the stop) |
| realtime-2 (major) removal on silence alone | fixed | Four paths removed aircraft that were still there: `silentDock` free(), `stationary()`, the ground ghost and the 8-h expiry. (a) A silent occupant now goes only on SFO's evidence (`stalePlanGone`). That evidence is a departure's actual block-out from THIS stand, every SFO window at the stand ended (ended means window end ≤ the plan's `fetched_at`), or the stand allocated to the arrival. None of it counts once the transponder was heard after that time. (b) `occupy()` logs `stale-replaced`. (c) No 8-h expiry at a contact stand. (d) ground.js at a stand removes a ghost only for a fuselage overlap (≥ 6 samples), never while SFO lists it there (`planHere`). A dead-reckoned body stops 3 m short of a parked aircraft that must stay (`drHold`). (e) Physical exclusivity still counts as evidence: a silent occupant of a mutually exclusive stand last heard before an aircraft whose own newer reports put it on the other stand no longer blocks it, and `occupy()` replaces it (Step 9 item 20). | parked aircraft removed and heard parked at that stand again: A 40 aircraft / 3,230 aircraft-min → 1 aircraft / 76 aircraft-min; B 1 aircraft / 18 aircraft-min → 0 aircraft / 0 aircraft-min |
| realtime-3 (major) ghost drawn on a newly parked aircraft | fixed | A replaced occupant now fades at once when its replacement is heard parked at the stand (`dropNow`). ground.js tests waiting ghosts against fixed and free bodies (`dropWaitFixed`). syncBridge undocks a stand's bridges from the previous aircraft before it docks a different one (`undockOther`). An arrival whose approach already retracted the ghost's bridge removes it at first contact (Step 9 item 16). | `overlap.gnd` A 14,366 / 103 → 5,400 / 93; B 415 / 22 → 98 / 22. G13 UAL1227 / UAL29D and G10 ANA108 / ANZ7 are no longer in the keys |
| realtime-4 (major) parked where the bridge cannot reach | fixed | updatePark: any pose the L1 bridge cannot dock (short by any distance, or its own heading / offset) is replaced by the type's stop pose when that pose docks (`parkAtStopReach`). The ≤ 15 m and stand-mode preconditions are gone. A lock refused after the dock is released. | `bridge.refused` A 2,313,837 / 41 → 903,402 / 13; B 609,822 / 10 → 189,381 / 2. Left (C3.2 item 1): stands where the STOP pose is refused too, which is the bridges' own geometry: F5 E75L (slope), F15 B39M ("L1 neck x walkway") |
| realtime-5 (major) aircraft in the terminal | fixed | The 803-frame key was UAL917 B772 (aa6b7e) pushing from G4, not UAL1180. `docking()` had given it G4's lead-in on its first motion report and kept it through the push. `target()`'s lead-in pull (no lateral cap) then dragged the push target 150 m into the G pier. Now a push-back or departure gets no lead-in, and the pull applies only inside the lead-in corridor. | `building` A 1,080 / 4 → 113 / 1; B 519 / 2 → 519 / 2. UAL917 is gone; window 5 Nov 06:30–07:30Z: building 797 → 0, G4 cab / G7 walkway hits 1,294 + 401 → 0. Left (not a push): A, UAL1757 B789 taxiing (one wing sample, 113 frames, as before); B, SWA1083 dead reckoning (Step 9 item 18) and AMX664 (1 wing point while moving, C3.5) |
| realtime-6 bridge-ahead at occupants that stay | fixed | The bridge retracts ahead only on positive evidence: SFO's arrival record for that stand, the arrival close on its lead-in (`onLeadInClose`), or SFO's evidence that the occupant left. Without it the bridge stays docked and the contact fade handles a real arrival. This round's realtime-10 rewrite had dropped the gate again; it is restored (Step 9 item 17). | A 106 bridge-ahead, 40 re-docked ('arrival gone') → 100 bridge-ahead, 29 re-docked ('arrival gone'); B 26 bridge-ahead, 8 re-docked ('arrival gone') → 20 bridge-ahead, 0 re-docked ('arrival gone') |
| realtime-7 'no push' cancels | fixed | EARLY_MAX_MS is now 60 min (the measured tail: signal → push up to 56 min). 'No push' fires only when the transponder has not reported at the stand for XPDR_LIVE_MS (2 min) AND SFO lists no off-block ahead. `_earlyBlock` is removed. | A 48 'no push' cancels, 32 followed by the push within 30 min → 7 'no push' cancels, 2 followed by the push within 30 min; B 8 'no push' cancels, 4 followed by the push within 30 min → 3 'no push' cancels, 0 followed by the push within 30 min |
| realtime-8 silent docks | fixed | The invented drive is capped at max(60 m, 1.5 L), or 150 m into SFO's own arrival stand. A newer stationary report away from the stand undoes the silent dock: no lock, no in-block (`silentDockContradicted`). | A 149 silent docks, drive p50 25.4 / p90 92.4 / max 202.2 m; in-block then 'stand-left' within 5 min 5 → 149 silent docks, drive p50 19.3 / p90 81.5 / max 141.9 m; in-block then 'stand-left' within 5 min 0; B 25 silent docks, drive p50 19.4 / p90 72 / max 100.6 m; in-block then 'stand-left' within 5 min 0 → 26 silent docks, drive p50 19.4 / p90 65.3 / max 77.9 m; in-block then 'stand-left' within 5 min 0 |
| realtime-9 drOvershoot scope | fixed | drOvershoot now applies only to a body that is dead-reckoning (`disp.extrap > 0`): not in push-back, not still, not locked, no bridge on. | A 161 drOvershoot (41 in push-back, 31 at a stand / locked) → 69 drOvershoot (0 in push-back, 1 at a stand / locked); B 26 drOvershoot (4 in push-back, 4 at a stand / locked) → 11 drOvershoot (0 in push-back, 0 at a stand / locked) |
| realtime-10 bridge.orphan at ghost removal | partly | With SFO's evidence the silent occupant goes before the contact. SFO's actual block-out removes it at once (`stale-blockout`), and the bridge-ahead starts 400 m out on SFO's arrival record or block-out (AHEAD_EV_M). Without SFO's plan (segment B and after 5 Nov 02:49Z in A) the only evidence is the arrival close on the lead-in, so the bridge retracts later and an empty stand still shows it retracting for some seconds. No overlap stays the hard rule. | `bridge.orphan` A 16,241 / 65 → 15,754 / 76; B 2,618 / 18 → 2,960 / 19 |
| realtime-11 bodies touching rest bridges | partly | Every named key was traced. UAL917 (G4 cab, G7 walkway) is realtime-5. At UAL59 G1, two multipath fixes 28 m out were taken as motion; the first motion candidate must now be reachable from rest. At N14541 D7, a garbage parked heading released the stand; now the position alone decides 'stand-left' at a contact stand. DAL545 and KLM373 are gone with the lock bound and the push fixes. On the new all-hours harness: AAL1430 at B26 (one stray fix released the stand: `reacqOutlier`, Step 9 item 15) and AAL2436 at B24 (a false push from GNSS wander: push-undo, item 19). | `bridge.hit.fus` A 1,923 / 13 → 762 / 10; B 182 / 3 → 138 / 3; `hit.wing` A 5,986 / 3 → 0; B 73 / 2 → 0; `hit.eng` A 28 / 2 → 0; B 28,742 / 2 → 0; `hit.tail` A 382 / 1 → 0; B 0 → 0; `hit_at_rest` A 7,100 / 14 → 501 / 8; B 14,742 / 4 → 138 / 3. Left: see "Trade-offs left" |
| realtime-12 harness | fixed | invariants.mjs now uses the app's building grid with the 3-D assets' footprints, and tests bridge solids against gates.js `acHit` (new `bridge.hit.eng`). The planform has a tapered nose, the tailplane at 0.35 R and engines. The streams cover every recorded hour (A + B). The misdock branch's crash (`doorOf` without nose / f) is fixed. | the harness for every number here |
| realtime-13 retired pavement / relocated W | fixed | `build_taxigraph.py` applies the static track's OSM decision list (`osmBase.updates`): 19 ways added, including relocated W 1562117372 and J 1562117374; 5 retired ways dropped. It also exports the retired pavement rings. `TaxiNet.paved` and `prepPolys` leave the retired pavement out. | taxi graph 262 ways / 4,060 segments (`data/sfo_taxigraph.js` rebuilt) |
| realtime-14 API hooks | fixed | parseCallsign(flight, {vehicle, category, icao}), re-parsed when tr.vehicle flips. The ui headline shows `tr.cs.label`. liveryForAirline(al, reg, hex, icao). modelNote: generic airframe label and the three-engine note. b772 / b77w are in MODEL_KEYS. setOccupant gets {freighter}. gatecheck.py takes bizjet length / span from fit.js BIZ. | node check (scratch `c3/realtime/scripts/hooks_check.mjs`): OPS12 / N312QX → vehicle, label "Airfield vehicle"; isFreighter FDX B763 true, UAL B763 false; gatecheck types table regenerated |
| realtime-15 marker / onFatal | fixed | markerSprites records carry `marker: true`. `R.onFatal = (html) => ui.fail(html)`. ui.fail shows a #fatal overlay after load (live.css). | grep of js/live/app.js, ui.js, live.css |
| realtime-16 extract2d stale | fixed | dispBar is [0, 3.05] and the shader's paintCheck string `band(xt, 0.0, 3.05` is used. Bridges come from gateSys.bridgesOf(g), the three upper-deck A380 bridges included, with per-pose `solids()`. Each bridge exports rotR / Hr / Hb / HrPinned / ownClip. Retired taxiway polygons are left out (`taxiwaysRetired`), and stands carry their typeStops. | SOFTGL=1 livetest run of jobs/extract2d.mjs, exit 0 in 250 s: out/draw/scene2d.json 9.4 MB, 110 stands, 131 bridges (3 upper), 524 poses all with solids, paintCheck all true |
| realtime-17 snapshot licence (owner decided 2026-11-08: keep as is) | closed (owner) | Documented default kept [inf]: data/snapshot.js unchanged (LICENCE CONFLICT row, docs/ATTRIBUTION.md). The new `tools/live/build_snapshot.py` writes an adsb.lol-only candidate (ODbL, provider on every record, METARs) to out/live/. | `--at 2026-11-04T19:30:00Z`: 115 aircraft, 3 METARs; owner question in C3.6 |

## Classes (all hours, before → after; frames / keys)

| Class | A before | A after | B before | B after |
|---|---|---|---|---|
| `bridge.dock_flap` | 10 / 2 | 2 / 2 | 0 | 0 |
| `bridge.hit.eng` | 28 / 2 | 0 | 28,742 / 2 | 0 |
| `bridge.hit.fus` | 1,923 / 13 | 762 / 10 | 182 / 3 | 138 / 3 |
| `bridge.hit.tail` | 382 / 1 | 0 | 0 | 0 |
| `bridge.hit.wing` | 5,986 / 3 | 0 | 73 / 2 | 0 |
| `bridge.hit_at_rest` | 7,100 / 14 | 501 / 8 | 14,742 / 4 | 138 / 3 |
| `bridge.misdock` | 0 | 0 | 32,408 / 1 | 26,405 / 1 |
| `bridge.orphan` | 16,241 / 65 | 15,754 / 76 | 2,618 / 18 | 2,960 / 19 |
| `bridge.parked_undocked` | 1 / 1 | 1 / 1 | 2 / 1 | 0 |
| `bridge.refused` | 2,313,837 / 41 | 903,402 / 13 | 609,822 / 10 | 189,381 / 2 |
| `building` | 1,080 / 4 | 113 / 1 | 519 / 2 | 519 / 2 |
| `clear.stand` | 996,145 / 41 | 1,166,171 / 45 | 51,886 / 5 | 34,302 / 4 |
| `clear.taxi` | 632 / 101 | 638 / 96 | 107 / 24 | 150 / 25 |
| `cut.gnd_sfo` | 605 / 332 | 577 / 328 | 93 / 67 | 88 / 68 |
| `gnd.acc.runway` | 54,366 / 439 | 54,367 / 439 | 9,202 / 90 | 9,202 / 90 |
| `gnd.acc.taxi` | 1,017 / 235 | 1,055 / 241 | 145 / 36 | 153 / 38 |
| `gnd.jerk` | 108 / 63 | 113 / 65 | 18 / 14 | 19 / 14 |
| `gnd.reverse` | 78 / 9 | 274 / 10 | 2 / 1 | 2 / 1 |
| `gnd.spin` | 566 / 110 | 541 / 112 | 48 / 15 | 43 / 13 |
| `lag.gnd_30m` | 81,475 / 326 | 83,673 / 323 | 7,457 / 55 | 8,451 / 55 |
| `lag.gnd_30m.other_airfield` | 765,698 / 453 | 765,687 / 453 | 42,527 / 57 | 42,527 / 57 |
| `offpave.mask` | 906,931 / 577 | 517,661 / 578 | 104,072 / 146 | 35,442 / 146 |
| `offpave.union` | 14,139 / 297 | 14,321 / 299 | 1,261 / 53 | 1,274 / 53 |
| `overlap.gnd` | 14,366 / 103 | 5,400 / 93 | 415 / 22 | 98 / 22 |
| `phase.flicker` | 827 / 253 | 836 / 254 | 138 / 52 | 142 / 54 |
| `phase.gate_far_from_stand` | 1,518 / 14 | 279 / 12 | 3 / 1 | 3 / 1 |

Per-finding metrics (scratch `c3/realtime/scripts/an_c3.py`, `tab_c3.py`):

```
## segment A: 2026-11-04T17:48:04.000Z .. 2026-11-06T06:31:36.530Z, frames 1,322,125 / 1,322,125
- removed_heard_back: {"n": 40, "aircraft_min": 3230} -> {"n": 1, "aircraft_min": 76}
- fade_why: {"ghost": 95, "replaced": 42, "expired": 59} -> {"ghost": 88, "replaced": 37, "expired": 25}
- locks_at_stand: {"n": 1208, "gt6m": 7, "max": 60.69} -> {"n": 1157, "gt6m": 10, "max": 60.69}
- parked_lock_vs_park: {"samples_min": 117978, "gt6m_min": 1032, "gt8m_min": 97, "max": 60.69} -> {"samples_min": 123353, "gt6m_min": 444, "gt8m_min": 311, "max": 60.69}
- early_cancel: {"silent": 54, "no push": 48, "arrival gone": 40} -> {"silent": 67, "arrival gone": 29, "no push": 7}
- no_push_followed_by_push_30min: {"n": 32, "of": 48} -> {"n": 2, "of": 7}
- bridge_ahead: {"n": 106, "arrival_gone_redock": 40} -> {"n": 100, "arrival_gone_redock": 29}
- early_lead_s: {"n": 492, "p50": 213, "p90": 1729, "gt10min": 132} -> {"n": 525, "p50": 204, "p90": 1752, "gt10min": 139}
- silent_docks: {"n": 149, "here": 26, "p50": 25.4, "p90": 92.4, "max": 202.2} -> {"n": 149, "here": 27, "p50": 19.3, "p90": 81.5, "max": 141.9}
- silent_inblock_then_left_5min: {"n": 5, "of": 140} -> {"n": 0, "of": 113}
- drOvershoot: {"n": 161, "push": 41, "at_stand_or_locked": 31} -> {"n": 69, "push": 0, "at_stand_or_locked": 1}
- flap: {"docks": 1030, "undocks": 964, "locks": 4736, "unlocks": 4614, "dockFlaps": 10, "lockFlaps": 254} -> {"docks": 966, "undocks": 898, "locks": 4695, "unlocks": 4583, "dockFlaps": 2, "lockFlaps": 248}
- counters changed: aheadNoEvidence None -> 181, aheadSkipPlan 30 -> None, bridgeAhead 106 -> 100, bridgeHoldMoving 4078.399999997386 -> 3625.399999997798, bridgeHoldS 4078.699999997386 -> 3625.699999997798, bridgeHurried 306 -> 281, buildingVeto 1072 -> 444, callsignChanges 753 -> 796, creeps 295 -> 157, cutHeldForBridge 43 -> 40, cut_err 3992 -> 3988, cut_gap 6058 -> 6040, cut_repark 422 -> 414, docks 1042 -> 978, drHold None -> 10, drOvershoot 151 -> 66, dropWaitCut 12 -> 4, dropWaitFixed None -> 1, drop_expired 59 -> 25, drop_ghost 95 -> 88, drop_replaced 42 -> 37, earlyCancelled 142 -> 103, earlyHurried 54 -> 57, earlyNoDock 215 -> 188, earlyUndocks 498 -> 531, early_xpdr 498 -> 531, expireKeptAtStand None -> 3926, fadeOuts 11281 -> 11234, fastUndocks 265 -> 171, firstAtStand 8 -> 7, ghostAhead 19 -> 12, ghostAheadKept 767 -> 2343, inBlockDup 3 -> 5, inBlockStale 31 -> 37, intoTerminal 153 -> 158, locks 15596 -> 6207, motionHeld 8378 -> 8576, motionUnreachable None -> 21, movingLost 2444 -> 2443, parkAtStopReach 349 -> 360, parkFrozen 142641 -> 142795, physMaskUnlocks None -> 13, physUnlocks 10733 -> 1442, pushCand 172 -> 174, pushChordRejected 134 -> 133, pushEarly 684 -> 686, pushFirstSeen 459 -> 453, pushHintFalse 58 -> 40, pushHints 182 -> 140, pushStandInferred 94 -> 93, pushUndone None -> 1, reacqOutConfirmed None -> 29, reacqOutHeld None -> 38, reacqParked 1650 -> 1692, reacquire 430 -> 429, rejects 1908 -> 1905, restAccepted 189 -> 180, restAcceptedPast 776 -> 780, restNoBridge 36 -> 22, silentDockBehind 100 -> 91, silentDockConflict 12 -> 9, silentDockCont 62 -> 24, silentDockContradicted None -> 40, silentDockFar None -> 18, silentDockHere 26 -> 27, silentDockHolding 520 -> 401, silentDockOccupied None -> 37594, silentDockStraight 36 -> 41, silentDockUndone 55 -> 51, staleKeptAtStand None -> 410, standLeftSlow 11 -> 4, towPivotS 4396.799999998464 -> 4408.699999998507, turnMemo 306 -> 303, undocks 362 -> 269, unlocks 105 -> 119
## segment B: 2026-11-07T01:38:30.000Z .. 2026-11-07T06:59:58.582Z, frames 192,885 / 192,885
- removed_heard_back: {"n": 1, "aircraft_min": 18} -> {"n": 0, "aircraft_min": 0}
- fade_why: {"ghost": 27, "replaced": 2} -> {"ghost": 22, "replaced": 1}
- locks_at_stand: {"n": 256, "gt6m": 0, "max": 5.25} -> {"n": 251, "gt6m": 1, "max": 6.62}
- parked_lock_vs_park: {"samples_min": 17809, "gt6m_min": 265, "gt8m_min": 19, "max": 11.58} -> {"samples_min": 17918, "gt6m_min": 10, "gt8m_min": 10, "max": 8.69}
- early_cancel: {"arrival gone": 8, "no push": 8, "silent": 13} -> {"silent": 17, "no push": 3}
- no_push_followed_by_push_30min: {"n": 4, "of": 8} -> {"n": 0, "of": 3}
- bridge_ahead: {"n": 26, "arrival_gone_redock": 8} -> {"n": 20, "arrival_gone_redock": 0}
- early_lead_s: {"n": 80, "p50": 234, "p90": 1678, "gt10min": 22} -> {"n": 83, "p50": 226, "p90": 1678, "gt10min": 23}
- silent_docks: {"n": 25, "here": 5, "p50": 19.4, "p90": 72, "max": 100.6} -> {"n": 26, "here": 6, "p50": 19.4, "p90": 65.3, "max": 77.9}
- silent_inblock_then_left_5min: {"n": 0, "of": 25} -> {"n": 0, "of": 19}
- drOvershoot: {"n": 26, "push": 4, "at_stand_or_locked": 4} -> {"n": 11, "push": 0, "at_stand_or_locked": 0}
- flap: {"docks": 210, "undocks": 152, "locks": 897, "unlocks": 835, "dockFlaps": 0, "lockFlaps": 44} -> {"docks": 198, "undocks": 139, "locks": 896, "unlocks": 836, "dockFlaps": 0, "lockFlaps": 44}
- counters changed: aheadNoEvidence None -> 68, bridgeAhead 26 -> 20, bridgeHoldMoving 547.700000000056 -> 467.9000000000379, bridgeHoldS 547.700000000056 -> 467.9000000000379, bridgeHurried 41 -> 32, callsignChanges 109 -> 110, creeps 68 -> 41, cutHeldForBridge 5 -> 4, cut_gap 459 -> 452, cut_repark 70 -> 72, docks 219 -> 206, drHold None -> 2, drOvershoot 17 -> 11, drop_ghost 27 -> 22, drop_replaced 2 -> 1, earlyCancelled 29 -> 20, earlyHurried 11 -> 8, earlyNoDock 46 -> 47, earlyUndocks 88 -> 91, early_xpdr 88 -> 91, fadeOuts 1124 -> 1121, fastUndocks 32 -> 24, ghostAheadKept 148 -> 91, inBlockDup None -> 1, inBlockStale 4 -> 5, intoTerminal 11 -> 13, locks 952 -> 1011, motionHeld 1347 -> 1336, motionUnreachable None -> 3, parkFrozen 21728 -> 21735, physMaskUnlocks None -> 6, physUnlocks None -> 66, pushEarly 120 -> 119, pushHintFalse 11 -> 8, pushHints 25 -> 20, pushUndone None -> 1, reacqOutConfirmed None -> 1, reacqOutHeld None -> 4, reacqParked 328 -> 331, restAccepted 55 -> 41, restAcceptedPast 153 -> 162, restNoBridge 9 -> 10, silentDockCont 15 -> 8, silentDockContradicted None -> 8, silentDockHere 5 -> 6, silentDockOccupied None -> 7526, silentDockUndone 5 -> 4, silentDocks 25 -> 26, staleKeptAtStand None -> 1, standLeftSlow 1 -> None, towPivotS 781.5000000001091 -> 776.500000000108, turnMemo 59 -> 54, undocks 40 -> 30, unlocks 16 -> 14
```

## Found in this round and fixed (not in the findings)

- **realtime-6's evidence gate was lost again within this round.** Rewriting the retraction line for realtime-10 (AHEAD_EV_M)
  dropped the gate. Without SFO's plan (segment B), bridge-ahead fired on geometry alone, and 8 of 28 retractions re-docked:
  B3 three times, for ASA arrivals continuing to B6 along B3's lead-in. The gate is restored, and `aheadNoEvidence` counts
  the skips.
- **One stray fix released a stand** (AAL1430 B26, Step 9 item 15): `reacqOutlier`, counters `reacqOutHeld` A 38 / B 4,
  `reacqOutConfirmed` A 29 / B 1.
- **A false push from GNSS wander kept an aircraft off its stand for 10 min** (AAL2436 B24, item 19): push-undo, counter
  `pushUndone` A 1 / B 1.
- **SFO's evidence, checked against the data** (item 14): `stalePlanGone` had taken a linked departure's block-out from
  another stand (AA2651 B20 / AA1930 B25) and stand-window ends that SFO had not yet seen end. The cache's last flysfo
  snapshot is 12–13 h old, and these expired UAL2123 E12, UAL1800 F17 and UAL1609 E9 while they were parked.
- **The ghost rules at a stand** (items 14, 16): a fuselage overlap is required, never while SFO lists the aircraft there. A
  dead-reckoned body holds 3 m short of an aircraft that must stay. An arrival driving in removes a ghost at first contact.
- **A silent aircraft on a mutually exclusive stand blocked a newer one** (item 20; found on the all-hours run of `root_after6`,
  where `overlap.gnd` in segment A rose to 38,225 frames, 33,556 of them one key). UAL2 B789 was last heard at B5S on 5 Nov
  16:56Z; ASA331 B738 was heard parked at B4 (MARS-exclusive with B5S) at 22:20Z and silent there until its push [obs]. Without
  SFO's plan the silent B789 blocked B4, so ASA331 never got the stand and the B789 was drawn through it for 56 min. A silent
  occupant of an exclusive stand last heard before the other aircraft's own newest fix no longer blocks it. Window 5 Nov
  16:50–23:30Z: `overlap.gnd` 34,565 → 1,745 frames (that key 33,553 → 733: the 73 s until ASA331's in-block),
  `bridge.orphan` 3,133 → 3,238 (B5S's bridge retracting after the B789 fades), every other class unchanged.
- **An aircraft towed while silent waited 20 s at its raw pose** (item 21; found on the run of `root_after7`). UAL2615 B738
  was kept at D15 from 5 Nov 05:31Z (realtime-2). Its transponder came on at E7 at 14:05:56Z (UAL2042, towed while silent
  [obs]), and as a track once seen moving it waited for 20 s of stationary reports before its stand was matched: drawn with the
  fuselage in the E-pier footprint for 16 s. A track heard again stationary elsewhere after its transponder was off now counts
  as heard there for the first time. Window 5 Nov 05:25–14:10Z: `building` 164 → 0 frames (in-block at E7 20 s earlier),
  every other class unchanged within 2 frames. All hours (segment A, `root_after7` → `root_after8`): `building` 365 / 3 →
  113 / 1 (UAL2042 E7 164 and SKW6001 F9 88 frames gone). The cost is a label lag: four tracks heard again elsewhere
  (UAL2042, SKW6001, UAL2480, ASA619) keep their old stand's `gate` label for 2 frames (0.2 s) at the re-acquisition
  (`phase.gate_far_from_stand` 271 / 8 → 279 / 12, the same 2-frame lag N535UW already showed), and SKW6001 has one
  `bridge.dock_flap` frame at F9 (1 / 1 → 2 / 2). The bodies are drawn at their reports in those frames.
- **The stray-fix rule's first form held a real fix** (EIN961 A333, B5S, 4 Nov 22:54Z; found on the partial after-run). After
  a silent docking whose data pose lay 60 m back on the lead-in, `reacqOutlier` held EIN961's first fix AT the B5S stop, and
  the body backed up 60 m. The rule now applies only to an aircraft parked on its OWN data, and never to a fix inside the
  stand's own limits. With the `LOCK_R0_MAX` cap above, the 60.7 m lock lasts one sample.
- **invariants.mjs**: the misdock branch crashed on 7 Nov 06:0xZ (`doorOf` without nose / f).

## Trade-offs left, with the reason

- **`bridge.orphan` without SFO's plan.** Bridge-ahead needs positive evidence (realtime-6). Without SFO's plan, that
  evidence is only the arrival close on the lead-in (≤ 60 m / 1.5 L). The bridge of a ghost therefore retracts late, and
  the stand shows it retracting after the contact fade for a few seconds. With SFO's evidence it starts 400 m out.
- **`lag.gnd_30m`** (A 81,475 / 326 → 83,673 / 323; B 7,457 / 55 → 8,451 / 55). In segment B most of the change is one push-back: JBU134 A321 from B20
  (7 Nov 06:29Z), first heard 43 m out at 3.2 kt. It is now drawn at push speed, 39 m behind its reports for 113 s, where
  drOvershoot used to re-place it with a fade; realtime-9 keeps push-backs out of drOvershoot.
- **`building`: SWA1083 B737** (7 Nov 04:09:32Z, last report at 9 kt west of the C pier, then silent until its departure).
  It was dead-reckoned 113 m straight on for 24 s and stopped by the building veto with its wing in the C-pier footprint
  for 18 s, before the lost-track fade. The veto samples the wing leading edge only; denser samples did not catch it
  (window 182 → 182). The fix is a dead reckoning that follows the taxi graph or brakes ahead of a building, next round.
- **A silent occupant at the newcomer's own stand fades only at its in-block.** Realtime-2 retired the removal of a silent
  occupant on an arrival's mere motion (it removed aircraft that were still parked). Where the arrival stops on the stand and
  goes quiet within 20 s (G6 UAL1272 / UAL927, E8 UAL1363 / UAL1385, 5 Nov 01:47Z and 04:54Z), the stand is matched only when
  it goes stale (~75 s), and the two are drawn overlapped until then: G6 1,131 frames, E8 968, F16 389, and the 734 left of ASA331 / UAL2 at B4 / B5S (segment A after). Next round: an aircraft whose own fixes
  stop inside a silent occupant's stand limits takes the stand at once.
- **A false push minutes after an in-block** (UAL2282 E6, 7 Nov 02:31:24Z, 12 s after its in-block; GNSS wander). Push-undo
  restores the stand after 74 s, but the wandering body touched E6 L1's rest tunnel for 80 frames meanwhile. Next round: a
  push within minutes of the in-block should count only once it leaves the parking by more than 0.6 L.
- **`bridge.misdock` UAL8217 B738 F16** (7 Nov 06:15Z, 26,405 frames, err 1.7 m against the 1.5 m threshold). The drawn
  body is 1.5 m from its parked pose and the bridge is docked at the parked pose: inside the lock bound of realtime-1.
- **`bridge.refused` / `clear.stand`**: the bridges' and stands' geometry, see C3.1 / C3.2.

## Requests (Round 3)

### C3.1 Static track (`data/sfo_stands.*`, `tools/stands/*`)

1. **F5 E-Jets** (`bridge.refused`, SKW5631 / SKW5572 / SKW5929 / SKW5970). F5's L1 bridge refuses the E75L at its STOP
   pose: slope 1:2.5 against the 1:4 limit (scratch `r3/scripts/refstop.mjs`). If that is the sheet's limit, F5's `types_ok`
   should leave out the E-Jets. SFO parks them there, and the app then draws them without a bridge, which is what
   `bridge.refused` counts.
2. **F19 / F20 clearance** (`clear.stand` 33,793 frames in B). UAL2171 B772 at F19 and UAL2364 B752 at F20 (7 Nov 06:03Z)
   are both at their stop poses and 5.0 m apart, where code E needs 7.5 m. SFO parked them together, the same pattern as
   R3.1 item 1 of Round 2. Please re-check the F19 / F20 stops and lead-in headings against these observed pairs.
3. **Neighbour pairs parked together, sub-metre short of the clearance** (`clear.stand`, segment A). These aircraft are each
   heard at their own stand at arrival and departure [obs], and are drawn at their stand poses: F7 / F8 E75L + E75L, wingtip gap
   4.38 m against 4.5 m (SKW5631 / SKW5440, 5 Nov 03:30Z, 409,524 frames); A5 / A9 A359 + B77W 6.94 m against 7.5 m (AAR212 /
   CAL004, 146,779 frames); A9 / A10 A359 + A359 7.12 m (SIA34 / AAR212); F20 / F21 B752 + B752 7.10 m (UAL548 / UAL574, 4 Nov
   21:07Z). The class grew (996,145 → 1,166,171 frames) only because such pairs are no longer expired after 8 h of silence
   (realtime-2). Please check those stops, lead-in headings and lateral offsets: SFO parks these pairs together, so the drawn
   poses should clear.
4. **C5 / C7 with an A333 at C5.** DAL1412 A333 (a3c51a) reported parked 11 m from C5's nose (5 Nov 20:46–22:09Z, at
   −646.5, 367.7 in the world frame) [obs]. C5 is class CL, so the engine leaves it unassigned and draws it where its reports
   put it. The B739 / B738 at C7 (DAL940, DAL1060; 21:30Z, 21:54Z) [obs] has its nose 44.4 m from it, and the half spans add up
   to 48.0 m. Before, the wings were drawn overlapped (`overlap.gnd` 9,136 + 757 frames, the largest key of segment A). Now
   they are drawn clear, but only 0.35 m apart against 7.5 m (`clear.stand` 26,589 frames). Please check C5's class, whether
   C5 / C7 have a wide-body combination, and their nose points / headings against this pair (window scratch
   `c3/realtime/w/t_dal1412`).
5. **Antenna references in motion.** `antenna_ref.families` is measured at the stop. Please check the large ones (B757
   17.1 m n 7, EJET 13.6 m n 19) on moving traffic before they are used for every body. A 17.1 m B757 reference put a
   holding B752 onto an A359 parked at G5 (4 Nov 20:41Z); traffic.js uses the references for parked noses only (`antPark`).
6. **R4.1 of static_closeout answered**: R4.1.1 (`antPark`, parked only, as above), R4.1.2 (`typesOkHas` refuses
   `typesOkUnsafe`), R4.1.3 (`excl-type-conflict` logged only), R4.1.5 (N199TH: mask-first placement, not in
   `offpave.mask` any more), R3.2.1 / R4.4 (retired pavement subtracted in `TaxiNet.paved` and the taxiway polygons).

### C3.2 Bridges track (`js/live/gates.js`)

1. **The stand's L1 bridge refuses the type at its STOP pose**: F15 B39M "L1 neck x walkway (fixed bridge parts)", L2 "no
   second-bridge door" (UAL1363, 7 Nov 01:47–04:27Z, 93,722 frames); F5 E75L slope 1:2.5 (C3.1 item 1). If the B39M is
   SFO's type at F15, the plan should find a neck angle that clears the walkway.
2. **R3.3 of bridges answered**: the engine undocks a stand's bridges from the previous aircraft before it docks a
   DIFFERENT one (`undockOther`).
3. **Marginal rest-pose contacts left** (window traces): DAL672 B763 at C9 against C9 L1's rest cab (2 sample points, 31
   frames, the aircraft at its own reported pose), SWA375 B38M at D3 against D3 L1's rest cab (1 point, 12 frames).

### C3.3 Aircraft track

The API hooks of aircraft_closeout.md §2 are wired (realtime-14): `parseCallsign(flight, {vehicle, category, icao})`,
`liveryForAirline(al, reg, hex, icao)`, the generic airframe label and the three-engine note, b772 / b77w in MODEL_KEYS,
`setOccupant(…, {freighter})`.

### C3.4 Engine / environment

`markerSprites` records carry `marker: true`. `R.onFatal = (html) => ui.fail(html)`, and `ui.fail` shows an overlay after
load (realtime-15).

### C3.5 Integration track (`data/buildings3d/integration.js` physics footprints)

`building` in segment B: AMX664 B39M taxiing at (−1328, 535) in the world frame (7 Nov 03:48:51Z, 337 frames), with ONE wing
sample in a footprint while it follows its reports on the taxilane west of the A pier. Please check whether a 3-D asset's
footprint reaches over that taxilane there (the harness uses the `c869b8f3` copy of integration.js).

### C3.6 Owner (realtime-17, needs_owner)

`data/snapshot.js` mixes adsb.fi and adsb.lol records without a per-record provider, and adsb.fi's terms forbid licensing
its data. The file is unchanged: the documented default is to keep it, with the LICENCE CONFLICT row in
docs/ATTRIBUTION.md [inf]. A candidate is ready: `python3 tools/live/build_snapshot.py --at <UTC>` writes an adsb.lol-only
snapshot to `out/live/snapshot_adsblol.js`, with ODbL, the provider on every record, attribution and the KSFO METARs of
that time. For example, `--at 2026-11-04T19:30:00Z` gives 115 aircraft within 60 km and 3 METARs. **Question:** keep the
file, replace it with an adsb.lol-only candidate (which hour?), or remove it from the public repository?
**Owner decision (2026-11-08): keep as is.** data/snapshot.js stays unchanged; the candidate builder stays available.

### C3.7 Lead

Please commit:
- `tools/live/build_snapshot.py` (new);
- `tools/live/build_taxigraph.py` and the rebuilt `data/sfo_taxigraph.js` (262 ways; 19 come from the OSM update extract,
  ODbL as before);
- js/live/traffic.js, ground.js, app.js, ui.js, entry.js, live.css, jobs/extract2d.mjs, tools/live/invariants.mjs and
  tools/live/gatecheck.py;
- `docs/research/realtime_impl.md` Step 9.

