# Requests after review round 4 (static geometry), 26 Sep 2026

From: static-geometry workflow. The data changes of this round are in `docs/research/stands_rebuild.md` §14. Everything
below is in files I do not own. `static_geometry_round3.md` stays valid; its items that round 4 found still open are
restated here, with what the data now provides.

## 1. js/live/gates.js — draw the DATA bridges (critical; open since round 2, escalated to the owner)

Status 26 Sep ~02:00 UTC: the bridges workflow's UNCOMMITTED working tree of gates.js (docs/requests/bridges_*.md) now
builds walkways from `walkW`, drums at `rotundaW` / `rotundaMaxR`, rest poses at `stowW`, honours `extRange` /
`dockTypesOut`, docks alternative positions through `sharesBridgesOf` and draws the threshold bar on the landing side.
Until it is committed and re-audited, the round-4 measurements below describe what HEAD renders. The items below
remain the acceptance criteria; the `sharedBridges` / `altGates` fields from airport.js are optional (gates.js already
resolves `sharesBridgesOf` itself).

Review round 4 replicated `prepBridge` / `pose` (gates.js:88-111, unchanged since 24 Sep 19:36) against the data:
- app rotunda vs data rotunda: 116 of 128 bridges more than 1.5 m apart, 43 more than 10 m (A1 L2 20.7 m, F12-F21
  19-20 m: the app puts the drum at the facade where NAIP shows it at the end of a ~20 m walkway along the facade);
- the rendered bridges collide: B11S L1 through B11 L1 (15-25 m2), rotunda drums 3.3-4.8 m apart at G2-G7 / A9, L1/L2
  walkways overlapping at 14 stands, docked L1 through the resting L2 at G7 / F15, rest tunnels through floodlight
  masts 58 / 61 / 62 / 63 (with the data stow no mast is within 0.8 m of a bridge), rest tunnels inside the wide body
  at B5S / B11S / B16S (12-16 m2).

The data (checked by `tools/stands/check_stands.py`: 0 bridge overlaps, rest poses clear of every accepted aircraft,
swing-feasible) gives per bridge, via `standGates()`: `walkW`, `rotundaW`, `rotundaMaxR`, `stowW`, `stowLen`,
`extRange`, `dockTypesOut`, `tunnelEndW`, `cabW` / `cabPose`, `cabTurnDeg` / `cabOption`. Please implement round 3 §1
items 1-5 unchanged: fixed walkway along `walkW`; drum at `rotundaW`, radius `min(2.45, rotundaMaxR)`; rest pose =
tunnel rotunda -> `stowW`; dock only inside `extRange` (+-1 m) and not for `dockTypesOut`; drop
`fixedLen = clamp(D - 27, 3.5, 70)` and the "second bridge 7 m aft" rule.

New in round 4:
- **Alternative positions** (B5S, B16S, C9V): `standGates()` now gives such a gate `sharedBridges` (the SAME bridge
  objects as its base gate's `bridges`; not copied, so a bridge is still drawn once, by the base gate) and
  `sharedFrom` (base id); the base gate lists `altGates`. Please dock a shared bridge to whichever of base /
  alternative is occupied (data dockings: B5 -> B5S 24.1-24.4 m, B16 -> B16S 25.2-25.6 m, C9 -> C9V 20.6 m); when
  neither docks, it rests at `stowW` (which clears the alternative position's aircraft).
- Rest-pose fields added: `swing_arc_deg` (all rest + docked directions fit in this arc; <= 175 deg everywhere),
  `stow_from_walkway_deg`, `stow_clear_m` (distance to the wings of the observed types) and `stow_note` where the rest
  pose is closer to an observed wing than the ICAO clearance (F14 / F17 / F19 / F21 L1: evidence conflicts, listed).
- The data's geometry is OSM-traced ROOFS (`bridge_geom_note`): likely ~1.3-2.1 m east of the true structures;
  NAIP cannot resolve it. Use the data as it is; do not add a lean correction of your own.

## 2. js/live/traffic.js — the SFO-allocation path and types_ok (major)

`standFits(pg, T, icao, false)` (traffic.js:85, :985) ignores `types_ok` for SFO's own allocation. With the class
limits alone, F19 (EL; e.g. a B772 / B77L, never planned there) and F20 (a 737 MAX) come 1.9 m apart. The data now
marks such stands `types_ok_all_paths: true` (F19, F20): please honour `typesOk` on every path when that flag is set
(an SFO allocation outside it then falls back to geometric matching / free parking). `airport.js` passes the flag as
`g.typesOkAllPaths`. Every other pair clears 3 m on the SFO path (check_stands APP view: 1 issue).

Per-family stops: this round adds INFERRED `type_stops` (src starts with "inferred"): (a) at F5, F11-F14, F17, F19, F21
the short narrow-body families stop 1-8 m short so that their wings clear the L1 rotunda / walkway (the aircraft SFO
parks there are longer, or stop short per ADS-B); (b) at E12 the A320 / A220 / E-Jet families take the B737 family's
ADS-B stop (-17.5 m, n = 4) so that E10 / E12, which SFO plans at the same time 66 times, clear 4.5 m. `stopAlong`
already honours them; please keep `updatePark` using the family stop when docking (it does: `dockComplete`).

## 3. js/shaders/ground.js + js/three/ground.js — threshold bar (major, round 3 §2, still open)

NAIP: the 10 ft bar lies on the LANDING side at all eight ends (+1.5..+1.9 m); the shader draws it at -1.52 m at
28R / 28L / 1L / 1R and not at all at 10L / 10R / 19R / 19L. Draw `band(xt, 0.0, 3.05)` at every end.

## 4. js/aircraft/types.js — winglet spans (round 3 §3, still open)

757-200/-300 41.1 m, 767-300ER 50.9 m with winglets (Boeing, cached `refs/cache/boeing3v/wingletspans.pdf`).
