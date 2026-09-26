# Requests from the real-time workflow — review round 2 (26 Sep 2026)

Owner of this file: the real-time workflow (`sfo_live_server.py`, `tools/live/**`, `js/live/{feed,traffic,ground,app,ui,entry,about,atc,stats}.js`).
Each item names the workflow that owns the file concerned. "Observed" = measured on the relay-merge replay of the
recording (`tools/live/invariants.mjs`), with the time and aircraft; "inferred" = reasoning.

## 1. Jet bridges (aircraft workflow: `js/live/gates.js`)

### 1a. A fast retraction for a departing aircraft (API request)

The engine now retracts a departing aircraft's bridge on the FIRST push evidence (one report of motion backward out of a
docked stand, or a push-back flagged against the reported nose) and asks for a short retraction:
`onGateChange(g, null, { fast: true, s: 5 })` (traffic.js `FAST_UNDOCK_S`). Reason (review round 2, critical): the real
bridge is retracted before the push-back starts, but ADS-B shows the departure only once the push is under way; with the
datasheet rates (`setOccupant(g, null)` -> 60-80 s for a wide-body) every push-back was drawn 1-2 min behind the data
(AIC4174 B77W at A1, 25 Sep 18:40Z: held 80 s, then 110-145 m behind for 3 min).

`gates.js` has no option for this, so `app.js` (and `tools/live/invariants.mjs`) shorten the retraction animation that
`setOccupant` has just created (`anims.get(g.id)`: `from = current k`, `t0 = now`, `dur = s * 1000 * k`). Please add a
supported entry point, e.g. `hurryUndock(g, seconds, now)` (the engine calls `gateSys.hurryUndock` when it exists), or an
`opts.maxS` on `setOccupant(g, null, …)`. The retraction path itself is unchanged (the same plan, played faster).

### 1b. `extension(g)` is now used

`app.js` / `invariants.mjs` read `gateSys.extension(g)` (1 only when a bridge actually docks the occupant) instead of
`anims` + `acType`. No action needed; noted so that its contract stays.

## 2. Pavement (static workflow: `js/live/airport.js` mask, `data/sfo_pavement.*`, `data/sfo_taxigraph.js`)

### 2a. The 118° corridor across runways 1L/1R (unverified; please check)

Review round 2 (major) found that real departures consistently taxi and queue along a straight corridor at true heading
118.1° crossing 1L and 1R between the terminal and the runway intersection, and that it is in neither the rendered mask
nor the OSM taxi-graph union, so every departure using it is drawn on grass:
- raw `adsb_icao` positions, constant true_heading 118.1°: UAL189 B77W 24 Sep 07:57:30-07:58:14Z from world (-169, 369)
  to (101, 512) m; ANA107 B77W 08:20:46-08:21:32Z;
- `offpave.union` hot-spot cells from (-275, 300) to (100, 500) world (37.6161,-122.3785 to 37.6143,-122.3743): 30 aircraft
  in 1.2 h (24 Sep 15:23-16:35Z); cell (-100, 400) had 13,628 aircraft-frames at 10 Hz, 1,474 of them moving (a queue).
- The reviewer notes that NAIP 2024 shows grass there and that OSM taxiway `W` (edited 2026-05-11) runs parallel about
  66 m north of the ADS-B path. A consistent 66 m offset of many aircraft's GNSS positions is not plausible (elsewhere the
  map matching snaps reports within 10 m), so either `W` is mapped in the wrong place or the pavement is newer than NAIP 2024.
- The current FAA airport diagram is available: AL-375 (FAA) SFO, cycle 2610, effective 01 OCT 2026 - 29 OCT 2026,
  `https://aeronav.faa.gov/d-tpp/2610/00375ad.pdf` (downloaded 26 Sep 2026 03:50Z, HTTP 200, 287,886 B). It shows taxiway
  `W` parallel to the 10/28 runways, crossing both 1L and 1R (hold bars on each side) south of the 1/19 x 10/28
  intersection, from the boarding area B/C apron (taxiways B, Y) to taxiway L -- i.e. the corridor exists; its exact
  position is the question (the diagram's scale cannot settle 66 m by eye).

Please register the diagram (or newer imagery) against the world frame, decide where `W` really is, and add its pavement
and taxi-graph edge; the earlier request (`realtime_round1.md` §3) and the NAIP-traced centreline in `sfo_details.js`
(`static_geometry_round2.md`) are about the same crossing.

### 2b. North cargo apron

`ATN3300` B763 parked at world (-1306, -1761) for 1.5 h off both pavement sources (NAIP shows pavement there); earlier
cases KAL214 B748, CSB805 B762, EVA629 at (-1248, -2169), (-1128, -2040), (-1027, -1870). Please add the apron.

## 3. Stand spacing (static workflow: `data/sfo_stands.json`)

`clear.stand` (both aircraft stationary, closer than ICAO Annex 14 §3.13.6: 4.5 m code C, 7.5 m code D-F), review round 2:
- AAL166 A321 at B25 / AAL2334 B738 at B24: 2.56 m for 13 min;
- F6 / F7 E75L pairs: 3.96-4.3 m;
- AAR212 / SAS935 A359 at A9 / A5: 6.98 m.
Please check these stands (positions, `tight_with`, `excl`, `types_ok`) against imagery.

## 4. Aircraft type database (for whoever owns `js/live/lookup.js` / type resolution; information)

The two ADS-B databases can both be wrong where SFO's record is right. Verified case: N670QX (Horizon, hex a8dd2c) is
`E195 'EMBRAER ERJ-190-200'` in the adsb.fi database (adsb.lol: no type), SFO lists its flights as E175, and the FAA registry
(`refs/cache/faa/MASTER.txt`, ReleasableAircraft of 23 Sep 2026: N670QX, serial 17001032, MFR MDL CODE 3260415 =
`EMBRAER S A ERJ 170-200 LR` in ACFTREF.txt) says E175 (ICAO E75L). In the other direction, SFO lists the base variant for
MAX / neo aircraft (16 of 141 mainline callsigns on 25 Sep 19-20Z: e.g. SWA3409 N8954Q database B38M vs SFO B738, JBU833
N2157J A21N vs A321), so SFO's type must not simply override the database. The relay now flags the conflict (the regional
alias is no longer vetoed by it) and the card shows both; an FAA-registry tie-breaker for N-registered aircraft would settle
such conflicts from the primary source.
