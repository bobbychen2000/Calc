# Aircraft door / docking fields (from the aircraft-types workflow), 24 Sep 2026

From: owner of `js/aircraft/**`, `js/live/aircraft.js`, `js/live/models.js` and the docking math in `js/live/gates.js`.
Evidence: `docs/research/aircraft_models_check.md` §0, `python3 tools/models/check_dims.py` (0 unexplained flags).

What changed for everybody who reads `TYPES`:

- `T.doors` are now passenger-door **centres** from the manufacturers' documents (1L, 2L, ...; optional doors in
  `T.doorsOpt`). Before, they were ~1-3 m too far forward and `gates.js` added 0.5 m.
- New per-type fields (written by `js/aircraft/fit.js`, which `js/live/aircraft.js` and `js/live/gates.js` import):
  `T.dockX1` (door 1L station the bridge docks to: the rendered door of the imported model where it has one),
  `T.dockSill` (door-1 sill above the ground, published), `T.dockHW` (rendered fuselage half width at the door),
  `T.dockX2` / `T.dockSill2` (the door the second bridge docks to; null = only one bridge docks), `T.H`, `T.crown`, `T.sill`.
- `T.Hc` (fuselage centre-line height) is now the seated height of the imported model (door sill / fuselage top), not a
  value derived from the fin height; `T.xMain`, `T.xNose`, `T.track` are the documented gear stations.
- `gates.js` exports `doorOf(nose, f, T, which)` (world door point + left vector) for anyone who needs the docking point.

Requests:

| File (owner) | Request |
|---|---|
| `js/world/gates.js` (legacy scene, not the live app) | `doorX = T.doors[0]` is now the centre (correct); use `T.dockSill ?? T.Hc - 0.3 * T.R` for the sill instead of `T.Hc - 0.3 * T.R`. |
| `js/live/gates.js` bridge geometry (static-geometry requests round 1) | Item 4 (L2 only to a door ahead of the wing) is done in the docking math: `docks()` docks the second bridge only when `T.dockX2` is set; the 767-300 (door 2 optional, D6-58328 §2.7.1) gets one bridge. Items 1-3, 5-8 (rotunda, walkway, rest pose, extension/turn limits, REF_TYPE) are bridge geometry and are left to its owner; `REF_TYPE.F = 'a388'` would now dock-prep at 6.32 m. |
| `js/live/traffic.js` | Unknown designators (E290, E295, A318, CRJX, B778) now return `null` from `typeForIcao` (no verified dimensions; marker), where they used to borrow the E190 / A319 / CRJ900 / 777-300ER airframe. |
