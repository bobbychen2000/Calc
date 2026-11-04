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
