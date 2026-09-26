# Requests from the bridges / runway-paint workflow to the engine (three.js) workflow, 26 Sep 2026

From: owner of `js/live/gates.js`, `js/world/gates.js`, `js/shaders/ground.js` (runway paint). The bridge geometry and
animation changed completely inside `LiveGateSystem`; `js/three/bridges.js` keeps working unchanged because it only
converts `items()` (same `{mesh, prog: 'obj' | 'sign' | 'objI'}` records, `sprites`, `atlas.map`).

## 1. `js/three/ground.js`: threshold bar - done here (surgical edit), please keep

`endMarkings()` now draws the 10 ft bar at EVERY runway end on the landing side of the (displaced) threshold, between
the edge markings: `band(xt, 0.0, 3.05, fw) * band(ay, -1.0, 29.27, fw)` (was `band(xt, -3.05, 0.0) * step(ay, 30)` and
only when `disp > 1`). Source: FAA AC 150/5340-1M Chg 1, §2.9.1.2 (required where a displaced threshold, blast pad,
stopway, EMAS or aligned taxiway precedes the threshold - at SFO all eight ends), §2.9.1.3 ("on the landing portion of
the runway ... the entire runway threshold bar marking is on the portion of the runway available for landing"), §2.9.1.5
(10 ft / 3.1 m wide, between the runway edges or edge markings). NAIP 2024 imaged bar centres +0.9..+1.9 m on the landing
side at all 8 ends (docs/drawings/report.md), model centre now +1.52 m. That is the only line changed in js/three.

## 2. `js/three/ground.js`: blast-pad chevrons (not changed by me - please apply)

`js/shaders/ground.js` now uses first apex 17.0 m beyond the runway end and a 30.48 m (100 ft) pitch
(`q = xb - abs(dv) - 17.0; k = floor(q / 30.48 + 0.5); f = q - k * 30.48`), measured on NAIP 2024 (static_geometry_round2.md;
AC 150/5340-1M Fig. A-9: 100 ft spacing). js/three/ground.js still has 15.0 / 29.7 (~line 311). Same change there.

## 3. `js/live/gates.js` new public surface (informational)

- `gateSys.solids(g, b, k)`: the drawn bridge as oriented boxes `{c:[x,z], u, hl, hw, lo, hi (world y), part, round?}`.
- `gateSys.extension(g)` (0 rest .. 1 docked), `gateSys.undockTime(g)` (s), `gateSys.step(now)` (advances the docking
  animations; `items()` calls it).
- Upper-deck (A380 U1L) bridges of A6 / A11 / G13 are drawn from `g.bridgesUpper` (read from `data/sfo_stands.js`);
  they appear in `items()` like the others.
