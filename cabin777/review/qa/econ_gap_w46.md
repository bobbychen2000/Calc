# Econ gap analysis, w46 (commit 01d3461; w45 A 8.4 / B 8.5, target 8.5+ from both)

Question: which 3-5 changes would most raise economy toward 8.5 for rater A? Constraint: no large triangle growth.
Scratch evidence (crops, scripts) is in
`/tmp/claude-0/-home-user-Calc/2fb1f2ef-fbd7-5fb9-b7d2-14a3db7265c8/scratchpad/gap46/`:
`backs_left.png` (y_47303 | q17 seat backs), `pocket.png` (lower back, 3x), `head.png` (q17 heads + e4 / e3), `belt.png`
(y_47303 | q17 pans + e11), `far.png` (y_47301 | q16 mid rows).
All stats are PIL/numpy on the 930x575 photos and the r46 / s46 renders. L = mean(R,G,B).

## Why the low details have not moved

The econ report says "neither rater names a concrete defect in the tray, back silhouette or rear shell", and those
details have held at A 7.9 / 8.0 / 8.0 for 6+ rounds. The defects are measurable. A vertical L profile down the near-left
seat back in q17 (x 60-120) and in y_47303 (x 65-105) shows the difference:

| Zone (top to bottom) | y_47303 | q17 |
|---|---|---|
| Under the handset / hood lip | 50 px shelf-shadow band, p10 12-26, dark (L<40) share 0.21-0.38 | none |
| Tray | L 155-194, p10 77-155 (latch, placard and tilt shading) | 90 px dead-flat panel, L 170-175, p10 = p90 within 5 |
| Pocket | p90 224-241 (card and elastic highlights) over a mid-grey mesh (median 51-108, p10 14-25) | thin white flap, then a black band with p10 2-5 |

So the rear of the seat has no value structure: no shelf, no pouch, no mesh. Only camera-independent features are used
here. The q17 camera is ~20 deg more edge-on, but the shelf and pocket also show in s46 `e6_lowback` / `e2_back`.

## Ranked changes

### 1. Silhouette: a real hood shelf, and a bulging pocket pouch. Expected +0.08-0.10 (A: back silhouette 8.0 -> 8.2, tray / pocket 7.9 -> 8.2), about +40 triangles per seat.

**Evidence.**
- **Hood shelf.** y_47303 (`backs_left.png`, `pocket.png`) shows the screen hood ending in a near-horizontal underside
  lip just below the handset. Its shadow is the darkest band on the back after the screen (dark share 0.21-0.38).
  - In `RS` (09a_econ.js:95-97), the hood goes from z 0.086 at y 0.44 to 0.106 at 0.49 to 0.12 at 0.53. That is a
    3.4 cm forward step spread over 9 cm of height: a ~20 deg ramp that lights the same as the tray.
  - The renders show no shadow line: q17 L 170-175 straight through, and e6 the same.
- **Pocket.** In y_47303 and y_47302 the literature pocket is a pouch whose net bows ~4-6 cm aft at the bottom, and the
  card and magazine stand in its mouth. In e6 / q17 our net is a flat 7 cm band at 1.1-2.4 cm proud
  (`on(0.05, 0.016 + 0.008*sin)`, line 263).

**Cheapest fix (09a_econ.js).**
- **`RS`, lines 95-96.** Replace `[0.44, 0.086, 0.04, 0.345, 0.016], [0.49, 0.106, 0.06, 0.37, 0.015]` with
  `[0.44, 0.086, 0.04, 0.345, 0.016], [0.478, 0.087, 0.04, 0.345, 0.016], [0.492, 0.117, 0.074, 0.372, 0.012]`, and keep
  `[0.53, 0.12, 0.08, 0.376, 0.015]`. This gives a 3 cm underside over 1.4 cm of height, which shadows under the PSU
  light. It adds one ring.
- **Tray latch, line 228.** Change `on(0.47, 0.012)` to `on(0.462, 0.012)` so it sits just under the new lip rather
  than inside it. The tray top is at 0.4705, which is unchanged.
- **Net bow, line 263.** Change `0.016 + 0.008 * Math.sin(u * Math.PI)` to
  `0.016 + 0.022 * Math.sin(u * Math.PI) * (1.2 - u2)`. Here `u2` is the strand's height fraction.
  - Simpler, with the same triangles: tilt each strand quad with `M4.trs(..., 0, -12 * DEG)` about x, so the net's
    foot stands ~1.5 cm further aft than its top.
  - Raise the horizontal strands' `dz` (line 264) from 0.022 to `0.022 + 0.012 * (1 - j / 10)`.
- **Flap bulge, line 254.** Change the centre ring depth from 0.022 to 0.034, so the flap and its piping read as a
  padded pouch top (y_47307 shows a padded leatherette flap with a welt).

### 2. Value: pocket mesh mid-grey not black, ANA-blue card, tray tilt. Expected +0.04-0.05 (A: tray / pocket 8.2 -> 8.4), 0 triangles.

**Evidence.**
- **Mesh.** On y_47303's near pocket the strands read light: median L 68-102, p90 180-194, holes p10 14-25. In q17
  our net is a black band with p10 2-5 and strands near L 45-110.
  - The cause is the strand colour `#34363c` (lines 263-264) and the back panel `#121316` (line 260).
  - Rater B's w44b and A's tray score both say the pocket reads as a black slot. e6 shows it as a black grille strip
    under every tray.
- **Card.** The saturated pixels in the pocket zone are blue in y_47303: mean (62,83,132), G > R, 2051 px. In q17 they
  are violet: (62,62,112), R = G, 435 px, from the purple header `#5b3a8e` (line 251).
  - The y_47302 wall cards (B777-300) also have a blue header over a green strip.

**Cheapest fix.**
- Line 260: back `#121316` -> `#24262c`.
- Lines 263-264: strands `#34363c` -> `#9a9ea6`, r 0.6. The hems on line 265 stay dark.
- Line 251: card header `#5b3a8e` -> `#2f62b0`.
  - Add one `gQuad(0.21, 0.006)` in `#3a9a5a` under it (y 0.180, dz 0.0178), +2 triangles.
  - Sanspotter shows purple on some cards, but the official photos win for colour.
- Tray, line 220: tilt 4 deg, bottom proud (`M4.mul(on(0.353, 0.009), M4.trs(0, 0, 0, -4 * DEG))`). Its face then
  takes a top-to-bottom gradient as in y_47303 (tray p10 77-155).

### 3. Value: hide the dark-grey under-arm plates in q17. Expected +0.03 (A: armrests 8.3 -> 8.4, pan / front unchanged), 0 triangles.

**Evidence.** In the q17 right block (x 430-930, y 230-470) there are 1400 low-saturation dark-grey px (S < 0.2,
L 50-110). The matching y_47303 block (x 470-930, y 280-500) has 547.
- The excess is four rounded grey pills: plate L 58-75, (66,71,85), sitting under every regular-row arm
  (`belt.png`, right).
- In y_47303 the zone under each arm is pan fabric and strap. No plate shows.
- The `ECON_PLATE` loft (line 359, regular rows: y 0.48-0.54, z -0.125 to -0.362) stands 1-7 cm above the pan top
  (0.47-0.477) and runs nearly the full arm length.

**Cheapest fix (line 359, regular-row branch only).**
- Drop it 2.5 cm: y values 0.48/0.488/0.51/0.532/0.54 -> 0.455/0.463/0.485/0.507/0.515.
- Shorten the nose: z1 -0.335/-0.353/-0.362 -> -0.30/-0.315/-0.32.
- Change `ECON_PLATE` `#66686e` -> `#55575d`.
- Head-on (q15) the arm-to-pan gap still shows a grey sliver, so w31's y_47300 match holds.
- Check: q17 grey px in the right block <= 800; q15 under-arm box unchanged within 5 L.

### 4. Material / surface: the hood's raised perimeter lip and screen recess. Expected +0.03-0.05 (A: rear shell 8.0 -> 8.2, screen / handset 8.0 -> 8.1), about +48 triangles per seat.

**Evidence.** A horizontal L profile in y_47305 just under the bezel (y 470) reads 153 | 200-215 rim | 178-184 field
| 195-200 centre | 168 | 198-213 rim.
- There is a ~1.6 cm light lip along each side of the hood face, a shaded valley inside it, and the shell rolling to
  L 153 at the extreme edge.
- e5 at the same place reads a dead-flat 201-204 from edge to edge (only the corner radius at x 120 / 500).
- Above the bezel (y 40), the photo shell has a gentle gradient (197 -> 218 -> 201). e5 has none.
- This plastic-moulding relief is what makes the photo's back read as a moulded shell, not a panel.

**Cheapest fix.**
- After line 201, add
  `for (const s of [-1, 1]) B.add(gRBox(0.016, 0.30, 0.006, 0.005, 2), on(0.69, 0.0005, s * 0.176), SEATMAT.yShell);`.
  These are side lips standing 6 mm proud, catching light on their inner bevel.
- Add a thin top lip: `gRBox(0.33, 0.012, 0.005, 0.004, 1)` at `on(0.846, 0.0005)`.
- Optionally inset the bezel 3 mm (`on(SY, -0.0035)` and `-0.0005` on the glass, lines 199-201), so the frame ring
  shadows on its top edge as in y_47305.

### 5. Missing part / layout: belts as in y_47303, not a symmetric mid-pan V. Expected +0.03-0.04 (A: belts 8.55 -> 8.7), net +3 boxes per drape seat.

**Evidence (`belt.png`).**
- **y_47303 near seats:**
  - The latch (grey cover + silver tongue) lies on the rear half of the pan near one armrest.
  - The teal tongue strap comes out of the cushion / armrest gap and falls over the pan front with slack, near
    vertical in the image (10-13 px wide at x 780-830, y 360-380, per w44b-5).
  - The navy strap runs diagonally across the pan front.
  - Metal adjusters show bright (202,224,243).
- **q17 / e11:** both straps run from the rear creases to a latch at z -0.40 (mid-pan front), a flat V repeated on
  every seat. Only every second seat's navy end crosses the lip.
- A's w45a-3 asks for the same thing ("tongue hangs vertically from the cushion gap").

**Cheapest fix (drape block, lines 292-316).**
- `zl = -0.40` -> `zl = -0.21`, and `xl = x0 + s0 * 0.14` with `s0 = (opts.hk % 2) ? 1 : -1`. That puts the latch on
  the rear pan near an armrest, alternating sides.
- **Tongue strap (teal).**
  - One box from the anchor `(x0 - s0 * 0.2, z -0.12)` to `(x0 - s0 * 0.19, z -0.44)` along the arm side.
  - Then the existing three over-lip boxes (lines 308-310) moved to `x0 - s0 * 0.19`, in teal and on every seat.
  - Lengthen the hanging box to 0.045 and give it 4 deg yaw, so it reads slack.
- **Navy strap.** One box from the latch to the pan front at `x0 + s0 * 0.02, z -0.47`. That is the diagonal across
  the front.
- **Adjuster.** Add one `gRBox(0.05, 0.006, 0.018)` in `SEATMAT.buckle` on the teal strap at z -0.33.
- Check: q17 teal px >= 2000 (photo 3785; w45 1629); there is no V apex at mid-pan in e11.

## The open medium item: the q17 headrest cover strip

The camera re-match is assumed done, so this covers only what geometry still differs.

- **Proportions are already right.** The plate foot is 1.35 cm proud of the wing front at y 0.71 (cover z -0.1155 vs
  wing front -0.102, line 122 / 137) and tipped 12 deg forward of the back. The head-on width (0.22, 71-74 px in q15)
  matches. With y_47303's higher, more frontal view, the plate should open to most of the photo's ~120 x 95 px flap.
  Do not widen or thicken it.
- **What still differs is tone, not shape.** The q17 cover band reads L 191, B/R 1.17 against the photo's 162 / 1.37
  (the additive SHEEN at grazing, `SEATMAT.yCover` `LAYER.none + SHEEN`, shared / lighting). The pale band is what
  makes it read as a "strip".
  - If it stays pale after the camera fix, the cheapest econ-side fix is a darker, bluer foot hem: line 148
    `#2a3049` -> `#20263f`, height 0.019 -> 0.028.
  - That gives the flap a visible lower edge, the dark hem y_47303 shows.
  - The sheen gain itself is the integrator's.
- **Wing depth.** The wing's visible side face (10 cm deep, line 122 `d` 0.0875-0.1) is larger than the narrow roll
  beside the flap in y_47303. Its rear 3 cm is buried in the back (back front z ~ -0.03), so cutting depth does not
  shrink what shows.
  - Leave the wings alone unless the matched q17 still shows < 60 % of the photo's cover px in rows y 110-160.
  - In that case, the next step is the plate foot 1.5 cm further forward (line 137, z at y 0.625 -0.133 -> -0.148,
    0.648 -> -0.138), as w44b-1 proposed.

## Not ranked

- **Far-LOD rows (8.1):** the q16 / y_47301 cover colours match (render covers L 56-76, B/R 1.9-2.1, against the
  photo's 54-115 and 1.6-2.3). The remaining gap is the boxy far headrest without wing humps (line 431). Splitting it
  into a centre box + two 0.05 wing boxes adds ~24 triangles per far seat, for maybe +0.02.
- **Armrest colour:** y_47302 arm top L 193 / B/R 0.98 against wall 212 / 0.98. That matches `arm` `#bfbcb8`, so no
  change.

## Expected outcome

Items 1-4 lift A's four stuck details (tray 7.9, silhouette 8.0, rear shell 8.0, screen 8.0) by ~0.2-0.4 each. That is
about +0.07 on A's detail mean (8.28 -> ~8.35) and, with item 5 and the camera fix on the cover, a realistic A overall of
8.5. B's lowest details are the same (7.8 / 8.1 / 8.1 / 8.2), so B should hold at 8.5 or gain. Total triangle growth is
about 90-100 per near seat (tens of thousands of triangles across ~116 seats, before LOD), with nothing on the far LOD.
