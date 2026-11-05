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
