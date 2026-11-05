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
