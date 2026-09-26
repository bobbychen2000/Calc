# Requests from the bridges workflow to the real-time workflow, 26 Sep 2026

From: owner of `js/live/gates.js` bridge geometry / animation (answers `realtime_round1.md` §1 a-e).
Nothing below needs a change for the app to work; items 1-3 make the engine and `tools/live/invariants.mjs` see the
bridges the app now draws.

## What changed in gates.js (your §1)

- **a. Rest pose**: every bridge rests at the stand data's `stowW` (tunnel end = cab pivot at rest, cab straight on the
  tunnel; clear +1 m of the envelope of every type the stand, its alternative positions and neighbours accept). The rest
  pose no longer depends on the aircraft type.
- **Docking path**: a joint path (rotunda swing, telescoping extension, cab turn, height) from the rest pose to a
  stand-off point 1.5 m out on the door normal, then a creep to the door. The path is checked against the parked
  aircraft (its drawn pose); if the direct path would cross it, a retract-swing-extend path is used; if none is clear, or
  the Oshkosh AeroTech datasheet limits (operational extension of the bridge's model +-1 m, cab 92.5 cw / 32.5 ccw or
  the optional 185 deg cab, rotunda swing 175 deg) or a tunnel slope over 1:4 (FAA AC 150/5220-21C §3.4.b(6)) forbid
  the docking, the bridge stays at rest (`docks(g, b)` is then false). Undocking is the same path backwards (backs off
  the door first), without vertical travel.
- **b. `extension(g)`**: 0 = every bridge of the stand at rest .. 1 = docked. Please use it instead of
  `gateSys.anims.get(G.id)?.k ?? (G.acType ? 1 : 0)` (app.js `traffic.bridgeK`). `anims` entries keep `.k`.
- **c. Undock time**: timed from the Oshkosh AeroTech Jetway sell sheet (2025) rates - horizontal travel up to
  27 m/min, cab rotation 145 deg/min, lift 1.09 m/min - plus a 0.15 m/s creep off the door (inferred). Median ~50 s,
  90th percentile ~90 s for a docking (arrivals include vertical pre-positioning); undocking has no vertical travel and
  is shorter. `undockTime(g)` returns the seconds for the current occupant. `setOccupant(g, null, animate, now, pose,
  icao, { undockS })` accepts a requested duration but never goes faster than the sheet's rates. The old fixed 16 s was
  faster than any apron-drive bridge can retract.
- **d. Alternative (MARS) positions**: the base stand's bridges dock the aircraft on the alternative position when
  their datasheet limits and a clear path allow it (B5S / B16S / C9V); their rest poses are clear of it by construction.
- **e.** unchanged: a new pose while docked snaps.

## 1. `js/live/app.js`

`traffic.bridgeK = (g) => gateSys.extension(bridgeGate(g))`.

## 2. `tools/live/invariants.mjs`

- `bridgeBoxes()` re-derives the old bridge (straight walkway attach -> rc, drum r 2.45, tunnel from rc + 2.2 m, cab
  -1.8..+2.35 m). Please use `gsys.solids(g, b, k)` (oriented boxes `{c:[x,z], u, hl, hw, lo, hi}` with WORLD heights
  - subtract GROUND_Y - and `part`, `round` = radius for the drum and pedestal): walkways follow the mapped polylines,
  sections telescope, the stair and drive column are included.
- `animStep()`: call `gsys.step(now)` (it also records the height a retracted bridge rests at).
- `doorW()` uses `T.doors[i] + 0.5` / `T.R + 0.15`; gates.js docks `doorOf()` (T.dockX1 / dockX2, T.dockHW + 0.15), so
  `bridge.misdock` can report up to ~1 m that is only the checker's door formula - import `doorOf` from gates.js.
- A patched copy with the first two changes is what I ran (numbers in the bridges report); nothing in tools/ was edited.
