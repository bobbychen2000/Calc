# Requests from the bridges workflow to the static-geometry workflow (data/sfo_stands.*, js/live/airport.js), 26 Sep 2026

From: owner of `js/live/gates.js` bridge geometry. gates.js now draws the DATA bridges (static_geometry_round1-3 §1 are
done): fixed walkway along `walkW`, rotunda at `rotundaW` (drum radius `min(2.45, rotundaMaxR)`, also kept 0.2 m off the
terminal outline, never below 1.5 m), rest pose at `stowW`, telescoping sections of the bridge's `model` (`ext_range`),
docking only inside the model's operational range +-1 m, the standard / optional cab turn (`cabOption`, sense from
`cab_convention`), `dockTypesOut`, and upper-deck bridges (A380 U1L). Checked with a numeric clearance check of every
bridge at rest, along every docking path and docked, for every accepted type at every stand (incl. alternatives and
neighbours), against aircraft, other bridges, the terminal outline (sfo_buildings) and the 70 masts: the remaining
findings are data questions:

| # | Item | Evidence |
|---|---|---|
| 1 | **B2 L1 rotunda is 0.63 m from its facade point** (`walk` = 2 points 0.63 m apart) and ~1.7 m from the Harvey Milk Terminal 1 hall outline: no drum of 1.5 m radius fits, and the rotunda corridor grazes the hall outline (2-3 samples of 0.5 m) whenever the bridge docks. Other two-node ways got a rotunda 3.0 m out (round 3); please do the same here or check the outline. | gates.js clamps the drum to 1.5 m |
| 2 | **A15 L1 walkway**: its second segment crosses the ramp-level complex outline (4 samples of 0.5 m, part of complex ring 2). gates.js trims only a leading part that lies inside the building. | |
| 3 | **A6 upper-deck bridge cannot reach the A380's U1L door**: 47.2 m from its rotunda (U1L at 20.94 m from the nose, Airbus AC380 FIGURE-2-7-0-991-002) - the longest datasheet model reaches 41.4 m. It stays at rest. Please re-check the "A7 Jetway" override / the A380 stop at A6. | |
| 4 | **A11 upper-deck bridge**: `stow_len` 9.85 m, but the only models that reach U1L (27.5 m) retract to >= 15.15 m (AT3 58/116). gates.js rests it on the `stow` direction at 15.15 m (checked clear). A `stow` consistent with a model that reaches the docking would remove the guess. | |
| 5 | **`standGates()` does not pass `bridges_upper`**: gates.js reads them from `data/sfo_stands.js` itself (`g.bridgesUpper`). Passing them (e.g. `bridgesUpper`, same fields as `bridges`) would keep one source. | |
| 6 | **Rotunda centreline** (the 175 deg swing is about it) is not in the data; gates.js takes the middle of the arc holding the rest pose and all dockings when it fits 175 deg, else the walkway direction. A mapped/imaged value would be better. | |
| 7 | **Heights are not in the data**: gates.js uses a departure level of 5.4 m at the facade (the terminal model's ramp level is 0-5 m), a fixed walkway sloping <= 1:12 to the rotunda, and per bridge the rotunda floor that minimises the docked tunnel slope (and keeps the drum 0.3 m above the wings of the stand's aircraft). Result: 30 % of the (bridge, accepted type) dockings slope more than 1:12, 12 % more than 1:8, 28 of 3,397 would exceed 1:4 and are not docked (G7 / G8 CRJ, A5 / E7 / G1 / G4 odd types). If SFO's departure levels / rotunda heights can be sourced, they would replace the inference. | |
| 8 | `stow` was checked with a 2.9 m tunnel / 3.6 x 3.3 m cab footprint; the drawn bridge also has a service stair beside the outer tunnel aft of the cab (sheet option C / D, up to 2.7 m from the axis). gates.js chooses its side so it meets nothing; no data change needed. | |
