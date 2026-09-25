# Requests from the real-time workflow after review round 1 (24 Sep 2026, ~22:30 UTC)

From: real-time workflow (owner of `js/live/traffic.js`, `ground.js`, `feed.js`, `app.js`, `ui.js`, `stats.js`,
`atc.js`, `sfo_live_server.py`, `tools/live/**`). Evidence: `tools/live/invariants.mjs` on the relay-merge replay of
`refs/cache/rec` (24 Sep 07:27-10:28Z and 15:13-21:59Z); positions in the world frame (`wgs84ToWorld`).
What changed on my side is in `docs/research/realtime_impl.md` ("Step 4").

## 1. `js/live/gates.js` (aircraft workflow)

The engine now docks a bridge only once the drawn aircraft has come to rest at its parked pose, to exactly that
drawn pose (`tr.dockPose`, passed as `pose` to `setOccupant`), and retracts it (`setOccupant(g, null)`) before the
aircraft moves; the drawn aircraft waits until the bridge is back (it reads the extension, see b).

a. **Rest pose clear of the aircraft (critical, review round 1).** `pose()` parks the cab at
   `rc + parkDir * min(15, reach - 2)`: 2 m short of the *reference* type's L1 door, which is inside or next to the
   fuselage of the aircraft at that stand (or a neighbour's). Every parked aircraft whose bridge is retracted (before
   docking: `DOCK_DELAY` 12 s + `DOCK_TIME` 22 s; after undocking, until push-back) is drawn through its own
   retracted cab/tunnel. Reviewer evidence: `bridge.hit.fus` 156,108 frames, e.g. UAL862 B77W through the B5 tunnel
   at k = 0 (15:55Z), UAL876 B772 in the B11 tunnel, DAL1053 in the C10 walkway. The stand data already carries a rest
   pose per bridge (`b.stowW`, from `stow` in `data/sfo_stands.json`: "a rest pose for the tunnel end clear of every
   aircraft the stand takes", stands_rebuild.md §8) plus `rotundaW` / `walkW`; please retract to `stowW`.
b. **Extension as an API.** The engine needs the current extension of a stand's bridges (0 retracted .. 1 docked) to
   hold a departing aircraft until its bridge is clear. `js/live/app.js` reads it today as
   `gateSys.anims.get(g.id)?.k ?? (g.acType ? 1 : 0)` — an internal. A method `extension(g)` would be safer.
c. **Undock time.** `UNDOCK_TIME` 16 s is the time a departing aircraft is held at the stand after its first
   confirmed movement (the relay sees the push only when it starts). If real apron-drive bridges retract faster
   (please check a manufacturer figure), an option in `setOccupant` (e.g. `{ undockS }`) would shorten the wait.
d. **Alternative (MARS) positions.** B5S / B16S / C9V (`shares_bridges_of`) have no bridges of their own; `app.js`
   now docks the base stand's bridges (B5 / B16 / C9) to the aircraft parked on the alternative position (the
   `setOccupant` call goes to the base stand's gate object with the alternative aircraft's pose). Please check that
   `prepBridge`'s rotunda / walkway of the base stand can reach the wide-body door on the alternative position, and that
   the retracted base-stand bridge stays clear of that aircraft (a).
e. `setOccupant` with the same type and a new pose while docked snaps the bridge (no animation). The engine never does
   this any more (a pose change > 6 m / 10 deg undocks first and re-docks after the aircraft has settled), so no change
   is needed; noted for completeness.

## 2. Aircraft rendering (aircraft workflow: `js/aircraft/*`, `js/live/aircraft.js`)

Re-placements (a coverage gap, re-acquisition, a parked-pose correction that cannot be driven) are now fades:
`tr.disp.alpha` goes 1 -> 0 in 0.4 s, the body is moved, then 0 -> 1. `app.js` can only toggle `LiveAircraft.visible`
(`alpha >= 0.5`), so today it is a cut. A per-instance opacity (dithered alpha) would make it a real fade.

## 3. Pavement and taxi graph (static workflow: `data/sfo_pavement.*`, `js/live/airport.js` mask, `data/sfo_taxigraph.js`)

Review round 1 (major): departures between the terminal and runways 1L/1R cross an area that is neither in the rendered
pavement mask nor within 40 m of an OSM taxi edge, perpendicular to 1L/1R at about 780-880 m along them, from
(-350, 275) to (100, 500) world: 37.616104,-122.378549 (-275, 300) ... 37.614527,-122.374868 (50, 475). 31-33
aircraft crossed it in 18-19Z alone. Please check the crossing on imagery and add the taxiway (and re-run
`tools/live/build_taxigraph.py` if the OSM extract changes).

## 4. Stand spacing (static workflow)

Stationary pairs closer than the ICAO Annex 14 §3.13.6 clearance (4.5 m code C, 7.5 m D-F), both in their stand pose:
F6/F7 (SKW4639 / SKW5519 E75L, 3.84 m), G1/G2 (UAL892 B789 / UAL838 B77W, 6.55 m), B4/B5 (JBU413 / a6bbef, 1.38 m).
Please check these stands' positions / `tight_with` / `excl` against imagery.

## 5. ADS-B position reference (answer to `stands_rebuild.md` request, row 2)

Done in `traffic.js`: `antOf(T)` = 0.06 L for the Airbus A318-A321 family (their parked reports lie a median ~2.5 m
behind the stand nose; 46 stays of AAL, JBU, FFT, UAL, DAL, ASA, ACA), 0.2 L for everything else (Boeing, Embraer,
A220: 6-17 m). Every consumer (bodies, bridge poses, stand scoring, models) uses it. The larger along tolerance for
narrow bodies on wide-body stands is not changed yet.


## Status 25 Sep 2026 (~18:30 UTC), after the round-1 fixes on the engine side

Measured with `tools/live/invariants.mjs` over 9.2 h of the relay-merge replay (24 Sep 07:37-10:28Z, 15:23-19:27Z,
19:40-21:59Z), engine `traffic.js` md5 067f86c5; details in `docs/research/realtime_impl.md` Step 4.

**§1a (gates.js rest pose) is still the largest open item and has no owner in practice.** `aircraft_docking_fields.md`
(aircraft workflow) leaves "rest pose, rotunda, walkway, extension/turn limits" to "its owner", and
`static_geometry_round2.md` asks the same of gates.js; nobody has changed `pose()`. Numbers now:
- `bridge.hit.fus` 122,531 frames; of these 65,730 (54 %) with the bridge fully retracted (new class
  `bridge.hit_at_rest`): the cab/tunnel at `rc + parkDir * min(15, reach - 2)` against the aircraft parked at the stand
  (before docking and after undocking), or against the aircraft of the MARS alternate position. The rest are retraction
  frames: `pose()` interpolates the cab straight from the door to the rest point, which sweeps the tunnel through the
  aircraft it leaves (e.g. SJX011 A359 at B5S, 24 Sep 07:40Z, B5 tunnel). Examples at rest: UAL984 B77W at G8 (cab at rest against the fuselage, 27,600 frames, 20:27Z), UAL876 B772 on B11S (B11 tunnel, 25,221 frames, 16:03Z), ASA811 A332 on B11S (2,938), UAL862 B77W on B5S (B5 tunnel, 1,049), CPA870 B77W at A5, UAL892 B789 at G1, JAL58 B789 at A12, TZP26 B788 at A12 (cab, 375-463 frames each: the minute before docking).
- Engine-side facts for the implementer: the engine calls `setOccupant(g, type, animate, now, pose)` only when the
  drawn aircraft has been at rest 20 s (arrivals; at once for aircraft first seen parked), and `setOccupant(g, null)`
  before it moves; it holds the aircraft until `anims.get(g.id).k` is 0. A rest pose at the data's `b.stowW` and a
  retraction that first backs the cab away from the door along the door normal would remove both classes.
- Please also expose `extension(g)` (§1b); the engine reads `anims` directly today.

**Static workflow (stand spacing, pavement)**:
- `clear.stand` 46,661 frames: both aircraft stationary at their stand poses closer than ICAO Annex 14 §3.13.6:
  F6/F7 E75L + E75L 3.96-4.38 m (code C 4.5 m), G2/G5 B77W + B77W 7.08 m (code E 7.5 m); also FFT1159 A21N / JBU1034 A20N at B18 / B17, 0.93 m (20:22Z) -- please check B17/B18 against the A321neo envelope.
- `offpave.union` 334,309 (36,283/h against 47,234/h in review round 1) frames: the unmapped north cargo apron (KAL214 B748, CSB805 B762, EVA629 at (-1248,-2169), (-1128,-2040), (-1027,-1870)) and the 1L/1R crossing between the terminal and runways 1L/1R (departures SKW5907, UAL1062, UAL583, UAL2498, DAL606 ... around (-150..-90, 375..411) world, i.e. 37.6153,-122.3769, replay of 24 Sep 15:25-16:45Z): still off the rendered mask ∪ OSM taxi net there, although `sfo_details.js` now carries the NAIP-traced crossing centreline (static_geometry_round2.md) -- please add its pavement.

**Done on the engine side from the static requests** (`static_geometry_round1.md`, `round2.md`, `stands_rebuild.md`):
`standFits` honours `a380` (A6/A11/G13 only) and `types_ok`; per-family `type_stops` in the stand score and the parked
pose; a stop-short pose that touches an occupied neighbour moves to the stop; the SFO-plan path skips stands whose
`excl` partner is occupied by a live aircraft (a silent one there is replaced); `conflict` stands tolerate their
documented offset; persistence key `sfolive.parked.v4`.
