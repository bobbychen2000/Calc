# Polish D (py, econ, room): integration L8-L11 hand-offs

Source items: `from_integration.md`, "Lighting run 2, L11 ... items for the area owners" and the L9 / L10 sections
addressed to py / room / econ. Metrics are my own re-implementation of the integration rater's scripts (thin highlight
share: L > 235 with 9 px density < 0.45, which reproduces their numbers to ±0.02; thin dark share: L < 9 px median − 30
with density < 0.45, which is not their definition, so compare its numbers only with each other).

| # | item | area | result |
|---|---|---|---|
| 1 | PY outline darks (medium): shell-rim reveal, cushion gap strips, leg-rest hinge gap, console split line | py | **partly done.** w16 tried all of it, and both raters failed it (A 8.3 / B 8.1, one high issue each). The shell-rim strip came through the rounded shell side as a black stripe, and the cushion side strips read as floating black rods. In w17 both are removed. Kept: a soft 24 mm #3a3f4c band under the cushion nose (behind the skirt), a dark gap under the hinge roller, 1 cm dark foot plates under the console and aisle shroud, and a 6 mm console side split line. q13 thin dark 2.39 -> 2.42 %, so the outline-dark gap to the photos is essentially still open. In-flight-level outlines would need real recessed joints (cut geometry), not proud strips. |
| 2 | PY rim highlights (low): rounder edges, pyShell r 0.42 -> 0.30 | py | **done.** pyShell r 0.30, pyArm 0.45 -> 0.38, pyArmPad 0.40 -> 0.32 (all PY-only keys); console body / nose seg 2, aisle shroud seg 3. q13 thin highlights 0.16 -> 0.24 % (target 0.45 not reached); q14 0.38 -> 0.38. Rated w17 A 8.5 / B 8.5 with no high issue. |
| 3a | shared SEATMAT `arm` r 0.45 -> 0.26, `armPad` 0.50 -> 0.32 | econ | **tested, reverted (not rated).** It lifted the q15 / q16 armrest faces 2-5 L, but the thin-highlight share did not move: q15 0.61 -> 0.61 %, q16 0.65 -> 0.65 %. Side-by-side crops were indistinguishable. With no evidence of a gain, econ stays at w51, and no econ round (w52) was run. A streak on these arms needs a cove-specular change on the lighting side. |
| 3b | shared SEATMAT `jCap` r 0.34 -> 0.26 | room | **tested, reverted.** It lifted a flat cap face in q09 (830-925, 340-410) by +16 L (125.9 -> 142.1), breaking the 5 L rule, and q06 thin highlights stayed at 0.94 -> 0.95 %. Instead, the capRail geometry became a 9 mm round edge with seg 3 (both w19 raters: keep; soft rolled sheen, though rater A still sees no thin line like c_27314's). |
| 4a | THE Room recessed toe kick (low) | room | **done.** `KICK` {h 0.08, d 0.02, #1c1d20 r 0.7}: under both aisle armrest housings (`roomAisleAsh` sides) and the tall ash monument ends, whose ash panel and frame now start at 0.08. Rated w19 A 8.5 / B 8.5, no high or medium issue (A: shell bases ~7 -> 8.2). |
| 4b | 11A footwell white hairline (low) | room | **done.** Traced to the 45° chamfer of the low console block at the footwell mouth (`gRBox(0.16, 0.22, ...)` at x -0.505), lit by the cove. Now a square `gBox`. Crop box (590-615, 330-412) of the seated 11A footwell view: 48 px > L200 -> 0, max L246 -> 129. |

Rounds: room w19 (A 8.5 / B 8.5, kept, 89168b6), py w16 (A 8.3 / B 8.1, high issues, not kept), py w17 (A 8.5 / B 8.5,
kept). Triangles per unit mesh: room O/E 12166 / 9590 -> 13426 / 11042 (+12.5 %); py py2 / py4 15934 / 32986 -> 17086 /
35710 (+7-8 %, w17); econ unchanged.

Open, suggested by raters (unrated, not done): room kick height 0.10 and a thin silver rail over it (w19 A, c_27312); PY
cushion-nose band as a graded crease (#4a505e, 0.036 tall, w17 A medium); orange-peel in the pyShell specular at r 0.30
(w17 B low).
