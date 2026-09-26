# Requests from the bridges workflow to the 2-D drawing workflow (jobs/extract2d.mjs, tools/drawing/*), 26 Sep 2026

From: owner of `js/live/gates.js` bridge geometry and `js/shaders/ground.js` runway paint. The extraction still works
(the part labels it infers from `bridgeGeo()` emission order are kept where possible), but these changes make the audit
describe what the app now draws.

## 1. Bridge parts: use `gateSys.solids(g, b, k)`

`bridgeGeo()` now draws: the fixed walkway along the mapped polyline (`walkW`, first segment a tube, the others slabs
- the extractor names the later segments `box`), the rotunda drum with radius `b.rotR` (<= 2.45 m, the data's
`rotundaMaxR`, clear of the terminal outline - labelled `cyl` when not 2.45), a rotunda corridor slab (`box`), two or
three telescoping tunnel sections (`tunnel1..n`; the AT2 models have two), the cab bubble (cylinder r 1.55, `cyl`), the
cab, and the service landing + stair beside the outer tunnel aft of the cab. `gateSys.solids(g, b, k)` returns the same
parts as oriented boxes `{c:[x,z], u, hl, hw, lo, hi (world y), part, round?, seg?}` with the proper names (walkway with
`seg`, rotunda, pedestal, neck, tunnel1..n, column, cab, stair) - using it avoids the emission-order heuristics.

## 2. Upper-deck bridges

A6 / A11 / G13 also draw their A380 upper-deck bridge (`g.bridgesUpper`, door 3; `gateSys.bridgesOf(g)` = main + upper).
Please include them (they dock only an A388, U1L door).

## 3. Kinematics rows

- tunnel-stretch: sections now keep their length and telescope (outer section fixed to the cab, A fixed to the rotunda
  corridor, B centred), so the check should report 0 once it measures the sections.
- tunnel-slope: the label "PBB slope limit 1:12 (ADA / ABA 410.1)" is not the rule for boarding bridges. FAA AC
  150/5220-21C §2.2.d(3)(b) / Figure 6: recommended 1:16-1:20, max 1:12 unassisted, 1:8 for runs <= 5 ft, 1:4 assisted
  ("the level landing requirement does not apply ... to PBBs"); §3.4.b(6): beyond 1:4 a ramp must be mated. gates.js
  targets 1:12 (it picks the rotunda height per bridge to minimise the docked slope) and does not dock beyond 1:4.
  Please report > 1:12 as "exceeds unassisted access" (WARNING) and > 1:4 as the limit. The slope runs from the end of
  the level rotunda corridor (`b.m.F` from the rotunda centre) to the cab floor at the pivot (`pose().cab`), not from
  the rotunda centre.
- the pose's `cab` is now the cab PIVOT (the cab's front / closure is 2.2-2.4 m beyond it on `facing`).

## 4. Runway threshold bar (`meta.paint.dispBar`, measure.py, report.py)

`js/shaders/ground.js` (and the one line in js/three/ground.js) now draw the 10 ft bar at every end on the landing side:
`band(xt, 0.0, 3.05, fw) * band(ay, -1.0, 29.27, fw)` (AC 150/5340-1M Chg 1 §2.9.1.2-2.9.1.5). `jobs/extract2d.mjs`
replicates `dispBar: [-3.05, 0]` and checks for the string `band(xt, -3.05, 0.0` (paintCheck); measure.py / report.py
say "draws a bar only at displaced thresholds, centred 1.525 m on the approach side". Please change to `[0, 3.05]` at all
eight ends (model centre +1.52 m; your NAIP measurements +0.9..+1.9 m).

## 5. ENVELOPE scenario: place each type at its stop point (`type_stops`)

`audit.py` puts every accepted type with its nose on the stand nose. The data's `type_stops` say where each family
stops (`js/live/traffic.js` parks there, and `gates.js` docks there); at F12 / F14 / F17 / F19 / F21 the stand data
records that the 737 / A320 / E-Jet families stop 2-13 m short precisely because at the stand nose "wings / engines /
tailplane ... came up to 4.5 m inside" the fixed bridge parts. The remaining `envelope-rest-bridge` COLLISION rows
(F17 / F19 / F21 / F14 with `b736`, the whole fixed bridge incl. walkway and pedestal inside the envelope) are this
placement, not a bridge pose. Please shift each type's placement by `type_stops[family].along` (traffic.js
`stopAlong`); `gates.js` exports nothing new for this.

## 6. `oversize-rest-bridge`, `bridge-aircraft` DOCK rows

Docked poses: `gates.js` does not dock a type whose docking path it cannot clear (`docks(g, b)` false, the bridge
stays at rest) - `bridgeParts(gp, b, 1)` for such a type draws the REST pose, which is correct; please treat
`docks === false` as "rest" in the DOCK scenarios (it already records `docks`).
