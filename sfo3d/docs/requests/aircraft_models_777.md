# Aircraft identity round 2: requests to other owners (from the aircraft / liveries workflow), 26 Sep 2026

From: owner of `js/aircraft/**`, `js/live/aircraft.js`, `js/live/lookup.js`, `js/live/models.js`, `js/shaders/aircraft*.js`,
`data/models/**`, `data/liveries/**`, `tools/models/**`, `tools/liveries/**`. Details: `docs/research/liveries_impl.md` §9.

What changed for everybody:

- **Two new models: `b772` (777-200ER) and `b77w` (777-300ER)**, FlightGear 777 series (FGMEMBERS/777 @371a354, GPL-2.0:
  the FGAddon original carries the GPL-2.0 `LICENSE`, svn trunk/Aircraft/777 r19240). They carry their own gear
  (oleos compressed to the published fuselage height by `js/aircraft/fit.js`). `TYPE_MODEL`: B772 / B773 on `b772`, B77L /
  B77W / B779 on `b77w`. `js/live/models.js` gives both a default source (same rule as `entry.js`), so they load today.
- `data/models/manifest.js` `MODEL_FEATURES` gained `under` (skin height grid above the main gear), `wing.engLow`,
  `wing.tipY`, `wing.htY`, `wing.htSemi`; the FG 737-800 now has door objects (`doorLF` 1L centre 5.25 m rendered).
- New stretch operations in `js/live/models.js applyStretch` (and the Python port `tools/liveries/common.py`): `tipCut`,
  `engScale`, `wingLift`, `htLift`, `squash`, `gearUp`. Anything that re-implements the stretch (three.js renderer)
  must apply them in the same order, or import `applyStretch`.
- `LiveAircraft` now paints the **registration** (runtime decal, `js/shaders/aircraft_real.js uReg*`), draws procedural
  **sharklets / 737 MAX split tips** at the model's wing tip, and treats **freighters** by operator / type / database
  description (`js/live/lookup.js isFreighter`).

| File (owner) | Request |
|---|---|
| `js/live/entry.js` | Add `'b772', 'b77w'` to `MODEL_KEYS` (and to the standalone packaging / artifact model list). `models.js` already resolves them with the same rule, so this is for the embed path and consistency. |
| `js/live/app.js` `modelNote` | Add `b772: '777-200ER', b77w: '777-300ER'` to the base-name table (today it prints "undefined" for the 777s), and the livery sentence can drop "Livery colours simplified." for aircraft with a brand bake (`liveryTextureFor(ac.liv.brand, m.m, m.t)` non-null). |
| `js/live/traffic.js` | (repeat of `liveries_brand.md`) pass `I.reg`, `tr.hex`, `I.icao` to `liveryForAirline`, so the livery carries the registration of non-US aircraft too (G-VOWS, JA864J, A7-AMI: the registration decal reads `ac.liv.reg`; until then `LiveAircraft.registration()` reads `window.SFO.traffic.tracks.get(hex).info.reg`, a debug hook). Also expose `tr.info.desc` (already there) — `LiveAircraft.freighter()` reads it the same way. |
| `js/live/app.js` / engine | When calling `gateSys.setOccupant(g, type, animate, now, pose, icao, opts)`, pass `opts.freighter = isFreighter({airline, icaoType, desc})` (`js/live/lookup.js`): a freighter gets only the door-1 bridge (777F / 747-400F / MD-11F have no second passenger door). |
| `tools/live/invariants.mjs` `doorW` | The `bridge.misdock` invariant still docks at `T.doors[i] + 0.5` with `T.R`: import `doorOf` from `js/live/gates.js` (it docks at `T.dockX1/2` = door CENTRE or the model's own door, cab floor `T.dockSill`, fuselage side `T.dockHW + 0.15`) so the check uses the formula the bridges use (A320: 5.54 vs 5.08 m today). |
| `js/three/aircraft.js` | Same stretch operations as above; the registration decal and tip devices are drawn by the legacy renderer only (reference implementation in `js/live/aircraft.js` / `js/shaders/aircraft_real.js`). Exact duplicate triangles are dropped at load (`js/live/models.js decodeModel`) and normals repaired (`repairNormals`). |
