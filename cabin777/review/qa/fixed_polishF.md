# Polish F (py, monuments): integration L13 hand-offs

Source items: `from_integration.md`, "Lighting run 3, L13 (final rating of the run: lighting 8.1, integration 8.0): items
for the area owners", To py (medium, integration rater) and To monuments (medium, integration rater). The low "To py"
item (thin dark-line share) is the same work as the medium one.

| # | item | area | result |
|---|---|---|---|
| 1 | PY reads as clean CG: outline darks about half the photos', short rim highlights, lifted lower bands | py | **partly done, kept (w19 A 8.6 / B 8.5).** The joint where the back fabric meets the grey shell is now a recessed seam: a 3 mm round bead (`PYGROOVE` #3e434d r 0.9) on the line where the back cushion's outer face enters the shell's front surface, computed per height from the two lofts (`seamPath`, `shellSD`, `secAt` in `09b_py.js`), 32 steps, its centre sunk 1 mm into the shell. Only a 1-3 px sliver shows (q14 foreground L 41-70, py_37303 dip L 60-65); no stripe on the shell sides and no rods on the cushion (the w16 failures). Why the integration snippet's placement could not work: the bolsters and ears stop ~5 mm short of the shell, so the real junction is the back cushion's side (x ~0.20-0.22), and a strip at the shell's outer edge (w / 2 - 0.004) is what pierced the rounded side in w16. The console cubby mouths are darker (#2a2c30 -> #16181c; p5 median L 19 -> 7). Not done: the headrest lower-edge groove (the flap and ears cover that edge in every rated view) and the leg-rest underside (no view shows it). Metrics: q13 thin darks 2.42 -> 2.46 %, q14 3.78 -> 3.86 % (py_37302 4.18 / py_37301 6.13 % on the same metric); thin highlights unchanged (q13 0.29 %). Both raters say the rest of the dark-line gap is in the fabric pleats and crevices, not at the seam. |
| 1a | w18 round | py | **not kept.** The first bead was `gTube(r 0.004, 4 sides, 16 steps)`: 8 mm across, square, standing proud of the curved rim, #2a2e36. It read as a black cord on the q14 foreground seat (A 8.1 high / B 8.3 medium). A console-face dark panel beside the cushion had no visible effect and a matching shroud panel showed as a stripe; both were dropped before rating. A lighter nose-crease step (#4a505e, rater A's w17 medium) sat entirely under the cushion overhang and changed no pixel; removed in w19. |
| 2 | Door-3 bar follows ANA's 2019 render while an in-service photo shows a galley face | monuments | **done, kept (w22b A 8.7 / B 8.9).** Confirmed first: OMAAT's ANA THE Room review (NH109 JFK-HND, Jan 2020) places omaat_j32 in "a small snack bar between the middle and rear business class cabins" (door 3); a real 2019 Traffic News press photo (87790 ph18) shows the same carcass with the blind down; KN Aviation (knav_31) shows the monitor over open bays with water bottles. The bar's upper unit now uses the welcome galley's photo-derived face as a shared `serviceFace` (ovens + control panel, monitor over two open bays with brewer and water bottles, tall glass-door cabinet), on a warm-charcoal carcass (#3a3835), blind rolled up, counter #0e0e0f r 0.4; bottle shelf, narrow fridge and tumblers dropped. q11 upper face p50 30 -> 54 (photo 53), counter p50 79 -> 53 (photo 31-39). The door-2 welcome galley is pixel-identical. |

Rounds: py w18 (A 8.1 / B 8.3, high, not kept), py w19 (A 8.6 / B 8.5, kept); monuments w22b (A 8.7 / B 8.9, kept;
files `monuments_w22b_a.json` / `_b.json` because `monuments_w22b.json` is the w22 rater-B file).

Triangles: py2 17722 -> 19306, py4 35710 -> 38878 per unit mesh (+8.9 %); monuments 119.6k -> 119.2k; whole scene
opaque 1.910M -> 1.915M.

Open (low, rated): the PY cushion-front band is still a flat stripe (A medium, carried from w17: lighten the band itself
to ~#4a505e / 0.036 tall, since anything behind it is hidden by the overhang); the seam bead darkens to L 23-40 in the
shaded bottom of q14; the w15 PY lows. Monuments: smoked-glass pane (needs a transparent material), thin cabinet stiles,
flat bright control panel, flat white nosing (rounded satin rail #b8babc m 0.7), crushed open bays (lighting).
