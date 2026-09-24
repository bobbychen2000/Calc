# Request: use the rebuilt stand data (data/sfo_stands.json, 24 Sep 2026)

> **Updated after review round 1:** see `docs/requests/static_geometry_round1.md`. `name` is the gate number again
> (A1, A4, A13, E10, E11, E13, G13; only B5S, B11S, B16S, C9V keep AODB names), bridges carry rest poses (`stow`),
> `rotunda_max_r`, `cab_pose`, walkways; stands carry `len_max`, `a380`, `tight_with`, `leadin`. Rows below that
> mention E10U / A1V / G13S as ids are superseded.

From: stands & bridges workflow (owner of `data/sfo_stands.*`, `tools/stands/`, `js/live/airport.js`). Details:
`docs/research/stands_rebuild.md` §8 (field list). The file stays backward compatible; these changes in files I do not
own would make use of it.

| File (owner) | Change | Why |
|---|---|---|
| `js/live/traffic.js` `blocked()` / `matchGate()` | Skip a stand while any stand named in `g.excl` is occupied (and treat occupying it as blocking them). Keep the existing oversize rule for the rest. | Alternative positions (B5/B5S, B11/B11S, B16/B16S, C9/C9V) and B4/B5S, B10/B11S, B15/B16S, C11/C9V overlap physically. `standGates` passes `excl` and `altOf`. |
| `js/live/traffic.js` `gateScore` / `ANT` | The ADS-B antenna median of parked aircraft lies 8.8 m (median) behind the stand nose, but A320-family aircraft (JetBlue, American, Frontier, Alaska) report within 1 m of the nose; narrow bodies on wide-body stands stop 20-31 m short of the wide-body nose (A319 at G7, B39M at F15, B738 at F21) - beyond the 20 m along tolerance. Consider a per-family antenna offset and a larger along tolerance (or a second stop point) on wide-body stands. | stands_rebuild.md §3.2, §7 |
| `js/live/gates.js` `prepBridge` | Use the real bridge geometry when present: `b.rotundaW` (world [x, z], the rotunda from OSM) instead of `attach + (D - 27) * u`, and the fixed walkway polyline `walk` (the 2-D audit shows L1/L2 walkways of the same stand colliding because both are derived from the attach point). Third bridges (A380 upper deck at A6, A11, G13S) are in `s.bridges_upper` (`door: 3`), kept out of `bridges` until the model can dock an upper-deck door (A388 U1) and park them otherwise. An alternative position (`alt_of`) with `shares_bridges_of: X` should dock stand X's bridges. | bridges now attach at the real building points; rotundas are measured |
| `js/live/gates.js`, `js/live/ui.js` (labels) | Display `g.gate` (e.g. `B5` for stand `B5S`, `E10` for `E10U`) on signs and in the UI; keep `g.name` as the id. | SFO's AODB names carry suffix letters |
| `js/live/ui.js` / `js/live/about.js` | Show the OSM credit: "Stand and jet-bridge data © OpenStreetMap contributors, ODbL" (+ the other notices in docs/ATTRIBUTION.md). | ODbL §4.3 (the stand file is an ODbL Derivative Database) |
| `js/live/traffic.js` persistence | Stand ids changed (e.g. `C11` is a different place now, `E10` -> `E10U`, new `B8`, `B20`, `B22`, `B24`, `C9`, `D6`, `E2`, `E12`, `F7`, `F9`, `F18`, `F21`, ...). Bump the `sfolive.parked.v2` key. | stale parked positions would snap to wrong stands |
| `js/live/ground.js` | Optional: `STANDS.positions` (unnamed OSM parking positions with heading, zone apron/north/west) as snap targets for parked aircraft that match no named stand. | realistic cargo / maintenance / remote parking |
| `CLAUDE.md`, `docs/HANDOFF.md` (owner) | Data table: `sfo_stands.js` = 108 contact stands (incl. 4 alternative positions), 132 OSM bridges (129 main-deck + 3 upper-deck), 309 NAIP red boxes, made by `tools/stands/build_stands.py` (ODbL). Checks: `python3 tools/stands/check_stands.py` (the `tools/sat/check*.py` commands still work as wrappers). | documentation |
| `js/shaders/ground.js` (owner) | Blast-pad chevrons observed on NAIP: apex spacing ~30.5 m, first apex ~17 m beyond the runway end (shader: 29.7 m / 15 m). 10L/10R now have pads (269 m / 231 m) via `END_ZONES`. | stands_rebuild.md §6 |
