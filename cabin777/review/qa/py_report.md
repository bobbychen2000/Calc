# PY (Premium Economy, ZIM) - area report

Owned file: `src/09b_py.js`. Shared edits, one line per key:
- `SEATMAT` py* in `src/09_seats.js`
- `PHOTO_GAIN` 17 in `src/03_tex.js`
- the py entries (the synthesis functions) in `test/make_swatches.py`, with `tex/tex_py_back.png` and `tex/tex_py_confetti.png`

## Scores (0-10)

| round | rater A (skeptic) | rater B (geometry first) | commit |
|---|---|---|---|
| r3 (start) | 5.8 (single rater) | - | - |
| w2 (after w1 fixes) | 5.0 | 5.6 | e7bb7d7 |
| w3 | 6.0 | 6.6 | 0ba3e28 |
| w4 | 6.5 | 7.0 | 39de8f0 |
| final fixes after w4 (not re-rated; round limit) | - | - | see git log "py w4" |

Both raters' w4 JSONs list no geometry high issue. Rater A kept one high issue on the fabric (too regular, and warmed
too far), and the final pass addresses it (see below). The target of 8.5 was **not reached**. The four-round limit in
the brief ended the loop while scores were still rising by about 0.5 per round.

## What changed

- **Fabric.** The r3 tile was a 140 px photo crop upsampled to 256 px, and it rendered as soft blobs. It is now drawn
  crisply in `make_swatches.py` (`synth_py_back`), keeping only the photo's mottling:
  - The real cabin photos (SANspotter 2023, The Alviator 2026) show short cream strokes in herringbone columns
    (alv_02, alv_17) on a lavender-grey ground.
  - They also show soft light and dark drifts, mixed stroke sizes and small dots.
  - The wings use elongated cream flecks.
  - Fabric, wing and flap colours are balanced against the wall in the real photos: fabric/wall 0.57-0.73,
    flap/back about 0.5, wing about equal to the back.
- **Shell.** The top is now a rounded arch at headrest height, square-shouldered so the wings never show from behind.
  The shells are lighter (#7e8084). The screen housing stands about 2.5 cm proud.
- **Literature pocket.** It sits low, just above the footrest: a full-width tray lip, a flat panel, and a shallow mesh
  window with a stitched border (alv_05, san_10).
- **Console:**
  - The face is 0.12 m wide and the cushion 0.43 m (this is a compromise, see question 1).
  - Two open cubbies; the upper is about 1.5 times the lower.
  - Right-angled royal-blue corner triangles.
  - Two universal AC/USB sockets, a lower block, and the red life-vest tab with its blue buckle (alv_08/09, py_37306).
  - A dark stitched leatherette lid with a light-grey two-cup tray at the nose (alv_18).
  - Seat-letter plaques and buttons on the nose sides.
- **Rear of the seat:**
  - One fold-down footrest: two ribbed pads on an axle, a centre hub and one arm (alv_05/06).
  - A floor-standing silver bottle bin with two recessed cups and a placard (alv_07).
  - Light aluminium diagonal leg struts.
- **Leg rest.** A dark hinge roller and side links (py_37301).
- **Details:**
  - The gooseneck is thicker, with a 38x115 mm head angled forward and the lens on its side (py_37305, alv_17).
  - The silver coat hook sits inboard.
  - Hem stitch on the flap.
  - Slate shroud caps.
  - The black crease line on the backs is removed.
- **Layout agreement.** `PY.sp` = 0.5525, equal to `05_layout` pySp. The r3 geometry was 2-3 cm off the seat ids and
  eye points.
- **Triangles** (hi-LOD): py2 went from 10592 to 11802 and py4 from 20228 to 23226 (about +15 %). The mid-LOD went from
  5712 to 6028. The far LOD is unchanged at 928.

## Sources

- The ANA official py_37301-06 photos in `ref/ana`.
- 37 real trip-report photos in `ref/web/py`, gitignored, listed in `INDEX.md`:
  - SANspotter NH108 2023 (JA793A, seat 26G): https://www.sanspotter.com/ana-777-300er-premium-economy/
  - The Alviator NH211 2026: https://thealviator.com/2026/09/ana-777-premium-economy-review/
- Each value in the code carries a `[V]`/`[D]`/`[A]` tag and its photo reference.

## Where the raters were not followed, and why

- **Console width.** Both raters measured the console at 0.13-0.15 m. At the layout's 0.5525 m seat spacing that leaves
  a cushion under 0.42 m, so the model uses 0.12 m (question 1).
- **Leg colour.** Rater A saw champagne legs; rater B wanted cool aluminium. The model uses a light warm aluminium
  (#bab7ae).
- **Flap colour.** Rater A wanted it greyer and rater B bluer. The model takes the middle, B/R about 1.4.
- **Not done:**
  - Placard text: it needs an atlas entry in `06_atlas.js`, which this area does not own.
  - Flap drape.
  - A larger (0.33 m) fabric tile: page size, question 2.

## Items for other areas

These are in `from_py.md`:
- The q13_pyFront camera sits inside the partition. The replacement camera is given.
- A PY seat-back QA view.
- A bulkhead monitor check for the monuments area.

## Open questions

These are in `questions_py.md`:
1. The real seat or console width, or the seat spacing from an aeroLOPA drawing.
2. Which fabric generation to follow, or whether to use a larger repeat.
3. Confirm the bulkhead monitors for row 25.

## Wave 3 (2026-10-24)

Start: a1 (3469e77), which redid PY to follow ANA's official photos (user decision), unrated. The wave-3 cap of six rounds
(w5-w10) was reached at **8.2 / 8.2**: the 8.5 target was **not** met, but every round gained and no high issue is left.

| round | rater A | rater B | mean | fixed in |
|---|---|---|---|---|
| w5 (a1 as committed) | 6.4 | 6.8 | 6.6 | 19f1188 |
| w6 | 6.6 | 7.0 | 6.8 | 9d9a406 |
| w7 | 7.0 | 7.4 | 7.2 | 2162647 |
| w8 | 7.5 | 7.4 | 7.45 | 91d6ceb |
| w9 | 7.8 | 8.0 | 7.9 | 3f7a731 |
| w10 | 8.2 | 8.2 | 8.2 | post-rating fixes (gooseneck, net, pan bar), not re-rated |

w5 dropped 0.15 against w4 (6.75), less than the 0.3 regression guard. The w10 round fell inside the lighting
mid-iteration (from_integration 56bb5c7: the PY/Y block renders ~20-35 % dark); per that note no material was retuned for
it, and both raters judged colour in the studio renders.

### What changed
- **Back fabric** (`synth_py_back`), the high issue of w5-w7: from a crisp white barcode, via a too-soft one-tone
  version (w5), to a three-tone mosaic. Light cells and a navy dash set on its own band between the rows, dark- and
  light-dominant cells, 2x2-cell brick patches, rows at random pitch around 8.2 mm (no corduroy beat), varied dash lengths,
  mild mottle and fine grain. Steel grey-blue base `#7e8593` (saturation ~0.2, py_37301/03/05). q14 against py_37301:
  contrast 0.60-0.74 vs 0.65, dark share 0.12-0.15 vs 0.14-0.18.
- **Headrest:** the 0.29 x 0.225 navy flap is a single sheet, its edges lying over the ears. Short, puffy, domed ears
  sit beside it (not in front), with a gap above shortened bolsters. The narrower headrest gives a neck step. The ear tile
  has a dark weave under brighter, angular sakura petals.
- **Shell:** tapers to ~0.47 around the screen (shell/bezel 1.18 vs 1.14-1.17), with a continuous soft arch rim above
  the fabric. A darker rear skin follows the shell (py_37304 #42474f). The screen sits in a 2 cm dark frame, raised so the
  rim above it is ~0.19 of the bezel height.
- **Rear of the seat:** a moulded literature bucket with a smile lip, a dark mouth and a net on its bulge (san_20 / 26).
  The bottle bin has a dark housing and a chunky brushed cup block. The footrest hangs on two vertical arms. Legs are
  aluminium grey.
- **Console:** blue-slate body (`pyArm` `#4f5a76`). The lid runs to a flush cup nose with recessed wells. The seat
  side has a dark recessed panel with a lit button strip.
- **Gooseneck:** a slim 13 mm arm along the shell flank as a smooth Bezier. The chrome head hangs near-vertical at
  mid-back, ~9 cm from the neighbour's.
- **Other parts:** the aisle shroud has its own darker material. The leg-rest roller is chunkier, with end caps and
  soft flutes. Seam-shadow welts run along the bolster edges.
- **Triangles** (hi LOD, `__app.scene` seat groups): 157.8k -> 196.0k (+24 %, within the 25 % budget). The shell loft
  density was kept at 3 to stay inside it.

### Open (from w10, not done)
- Low: the wing-petal contrast. A calls it fixed (p90/p50 1.27-1.47 vs 1.25-1.63); B still measures about half of
  py_37305's spread.
- Low: the flap aspect. A measures it as too tall and B as slightly squat, so it is left as is.
- Low: the back cloth reads crisper than py_37305 close up (B), and the saturation is ~35 % below the official photos
  (A). Retune only after the lighting loop lands.
- Low: from a standing eye behind the row, a thin navy over-top strip and the ear tops show at the shell corners (B).
- Handed off: blank placards (integration atlas, from_py.md item 3), a rear-facing QA view (item 4), and the sun diamond
  on the 26A back plus the overall PY darkening (lighting).

### Sources
- ANA py_37301-37306 (ref/ana).
- SANspotter 2023 JA793A, san_00-30 (ref/web/py, https://www.sanspotter.com/ana-777-300er-premium-economy/).
- GourmetFlyer, ANA A380 PY: same ZIM hardware, different fabric; b_gf_a380_* (https://gourmetflyer.com/?p=5106).
- The Alviator, Business Traveller and Flickr were blocked from the sandbox this wave, so the alv_* photos cited in
  wave 1 were not re-checked.
- Before/after: `py_before_after.jpg` (own renders only).

## Wave 3b, plateau breaker (w11-w14)

Start: 1432360 (the w10 post-rating fixes, unrated). The 4-round cap of the plateau rule was reached at **8.4 / 8.4**.
The 8.5 target was met by rater B in w13 (8.5) but not by both in the same round. No high issue was raised in any round.
The last two rounds gained less than 0.2, so the stop rule applies too.

| round | rater A | rater B | mean | fixed in |
|---|---|---|---|---|
| w11 (1432360) | 8.1 | 8.3 | 8.2 | 270fdf2, 315110d (+ gap analysis `py_gap_w11.md`) |
| w12 (315110d) | 8.2 | 8.4 | 8.3 | 99b6600 |
| w13 (99b6600) | 8.3 | 8.5 | 8.4 | e3268a7 |
| w14 (e3268a7) | 8.4 | 8.4 | 8.4 | post-rating fixes (ears, weave, petal spacing, colours), not re-rated |

### What changed
- **Two seat trims (gap analysis, the biggest gain).**
  - ANA alternates two trims. Trim A has a dash-weave back and cushion with petal ears. Trim B has a petal back and
    cushion with dash-weave ears.
  - Evidence: py_37302's foreground seat (a centre-block aisle seat) is B, SANspotter 26G is B (san_12) and 26F is A, and
    both seats of the py_37301 window pair are A.
  - Model: B on the centre block's aisle seats D / G, also in the far LOD (`pyUnit` / `pyUnitFar`; questions 10).
- **Back weave (`synth_py_back`).**
  - The w11 "pixel bricks" are redrawn as blocks woven from fine thread floats (~1.9 mm pitch, 5-10 mm floats).
  - The ends are tapered, the brick-patch mask is blurred, and the rows are steadier.
  - The contrast went soft in w11, was raised in w12-w13 and slightly overshot. After w14 the light gain is 1.75, with
    wider blocks (~0.6 of the row, py_37301).
- **Petal fabrics.**
  - `py_confetti` (the trim-B back, 0.09 m tile) has 50 cream-grey 2-3:1 slivers on a plain mottled ground, with no dash
    rows and no round specks.
  - The ears have their own tile `py_ear` on the new detail layer 31: notched, pointed, log-normal chips plus small bright
    flecks (py_37305).
- **Literature pocket (san_26, b_san_20).**
  - A dark recess ~0.62 of the frame width runs down the lower back, with a rear holder plate and a wide leaflet.
  - The open tray sits at its foot. Its grey front is lofted across x so the top edge follows a deep smile rim, and a
    mesh band follows the smile.
- **Smaller changes:**
  - The navy over-top strip is removed.
  - The ears are broader and flatter.
  - The flap uses the faint plastic grain instead of leather, which was 2-4x the photo.
  - The console side panel is darker, and the console a little less blue (`#545b6e`).
  - The gooseneck hose is 19 mm.
  - The PY bezel is `#2a2c33`.
- **Triangles** (hi LOD, `__app.scene` seat groups): 196.0k at the wave-3b start, 194.6k at the end. Savings came from 3
  footrest ribs instead of 5 and from the pocket boxes.

### Open (from w14, low unless marked)
- Medium (A + B): the ear chips read as polka dots. The post-rating tile adds pointed tips, wider notches, log-normal
  sizes and bright flecks; this is not re-rated.
- Low: the back weave contrast overshot slightly in w13-w14 (p90/p50 1.37 vs 1.25). The post-rating fix lowers the gain
  to 1.75.
- Low: the trim-B petal repeat showed a Y-cluster motif. The post-rating fix uses seed 17 and 21 px spacing.
- Low: the pocket colours. B wants the holder and recess lighter, while A wants the tray rim darker; they are left as is.
  A wants the pocket another ~7 cm lower, while B says only a few cm of shell is left; it is left as is.
- Low: the flap is dead flat (no grain or seam), and the cushion is blocky up close (p5).
- Handed off: blank placards and the leaflet header (atlas), the sun rhombus on 26B and the cobalt cast in q13 (lighting),
  and the q13b camera, which sits inside the seat in front (`from_py.md` items 6-8).

### Sources
- ANA py_37301-37306 (ref/ana).
- SANspotter 2023 san_00-30 / b_san_* (ref/web/py, https://www.sanspotter.com/ana-777-300er-premium-economy/).
- Before/after sheet `py_before_after.jpg`: w11 start vs w14, own renders only.

## Wave 3c, confirm (w15): target met

w15 rated the wave-3b post-rating fixes (46a988d), unrated until now, under the lighting loop's round 1 (2913db8). Both
raters scored **8.5**, and neither raised a high issue, so PY meets the bar. As the brief says, no further rounds were
run and no code was changed.

| round | rater A | rater B | mean | commit |
|---|---|---|---|---|
| w15 (46a988d) | 8.5 | 8.5 | 8.5 | target met, no high issue |

### Calibration (w14 issues)
- **Ear chips read as polka dots** (w14 medium, A + B): fixed. In p4 there are 102-104 chips against 110 in py_37305,
  with elongation 1.63 against 1.65 and cover 14-16 % against 16-17 %.
- **Back weave contrast:** fixed for A and partly fixed for B. p8 gives p90/p50 1.34 against 1.26-1.28 and high-pass
  0.19-0.20 against 0.18-0.19 (w14: 1.39 / 0.22).
- **Ear ground too blue:** fixed. It renders #4a4d5b against #4e505f.
- **Trim-B Y clusters:** fixed at q13 distance.

### Left open (medium for B, low for A; none high)
- **Trim-B ears** (`SEATMAT.pyWingB`) render darker than their back, at an ear/back lightness ratio of 0.84 against
  1.0-1.3 in the photos (B, medium). B suggests `photoBase('#828a9c', 'py_back')`.
- **Trim-A back dashes** are about 1.5-2x too long, which leaves soft coarse bricks close up (B medium, A low). B
  suggests `synth_py_back` with cols 11 and light ln N(17, 2.5).
- **Low items:** about 0.11 m of plain shell under the pocket (A wants `py0` 0.20), the pocket colours, the flat navy
  flap, angular rather than five-lobed ear shards, and the busy ears at cabin distance.
- **Handed off:** blank placards and leaflet (atlas), and the lighting items in `from_py.md` (wave 3c).

Ratings: `py_w15a.json`, `py_w15b.json`. Triangles are unchanged at 194.6k.

## Polish D (w16-w17): integration L9-L11 hand-offs

| round | rater A | rater B | result |
|---|---|---|---|
| w16 | 8.3 | 8.1 | high issue each: the shell-rim reveal showed as a black stripe down the shell side, and the cushion side strips read as black rods. Not kept. |
| w17 | 8.5 | 8.5 | no high issue: kept |

- **Kept (w17):** pyShell r 0.42 -> 0.30, pyArm 0.45 -> 0.38, pyArmPad 0.40 -> 0.32 (shared `09_seats.js`, PY-only keys);
  rounder console body, nose and aisle shroud; dark foot plates under the console and shroud; a 6 mm console side split
  line; a soft #3a3f4c band under the cushion nose; a dark gap under the hinge roller.
- **Removed after w16:** the shell-rim reveal and the cushion side gap strips.
- **Metrics:** q13 thin highlights 0.16 -> 0.24 % (target 0.45 %); thin darks barely moved. Outline darks remain the open
  gap. Closing it would need real recessed joints rather than proud strips.
- **Open:** the nose band should be a graded crease (A, medium; #4a505e, 0.036 tall); orange-peel in the shell specular
  (B, low); the w15 lows (trim-B ears, trim-A dash length, pocket frame).
- Triangles: py2 15.9k -> 17.1k, py4 33.0k -> 35.7k per unit mesh. Ratings `py_w16a/b.json`, `py_w17a/b.json`.
  Log: `fixed_polishD.md`.

## Polish F (w18-w19): integration L13 "PY reads as clean CG"

| round | rater A | rater B | result |
|---|---|---|---|
| w18 | 8.1 | 8.3 | seam bead 8 mm and square: a black cord on the q14 foreground seat (A high). Not kept. |
| w19 | **8.6** | **8.5** | 3 mm round bead, sunk 1 mm, #3e434d: no high or medium new issue. Kept. |

- **Kept (w19):** a recessed seam where the back fabric enters the shell, computed from the two lofts (`seamPath`,
  `shellSD`, `secAt`; `PYBACK` / `PYBOL` / `PYEAR` are now shared section constants); darker console cubby mouths.
  The w16 artefacts (stripe through the shell side, rods on the cushion) did not come back.
- **Metrics:** q14 foreground seam 1-3 px at L 41-70 (py_37303 dip L 60-65). Thin darks q13 2.42 -> 2.46 %, q14
  3.78 -> 3.86 % against 4.18 / 6.13 % in the official photos; the rest of the gap is fabric pleats and crevices.
- **Open:** the cushion-front band is a flat stripe (A medium, carried from w17); the bead is dark in the shaded bottom
  of q14 (low); the w15 lows (trim-B ears, trim-A dash length, pocket frame, flat flap, shell orange-peel).
- Triangles: py2 17.7k -> 19.3k, py4 35.7k -> 38.9k per unit mesh. Ratings `py_w18a/b.json`, `py_w19a/b.json`.
  Log: `fixed_polishF.md`.

## Final confirm (on 1430d42, after lighting runs 2-4)

| round | rater A | rater B | result |
|---|---|---|---|
| final | **8.5** | **8.5** | no high issue: PY confirmed, no code changed |

- **What changed since w19:** nothing in PY. Since w19 (b8e0734) only `04_shaders.js` and `12_scene.js` have changed.
  - Studio views p1-p8 are pixel-identical to w19.
  - In q13 and q14, only lighting moved: mean |dL| is 0.5 and 2.9.
- **Calibration:** every w18/w19 high or medium issue is still fixed. Nothing regressed.
  - Seam bead: within 0-3 L of w19.
  - Flat cushion-front band: still open (A medium, B low).
- **New, from lighting:** the cool white balance pushes PY fabric blue. Fabric B/R rose in both views, against 1.22-1.36 in py_37301-03:
  - q14: 1.27 -> 1.39
  - q13: 1.36 -> 1.49

  Rater A rates this medium and rater B low. It is routed to `from_py.md` (final confirm). PY `SEATMAT` is left unchanged because the studio colours match the photos.
- **Triangles:** unchanged from w19. py2 is 19.3k and py4 38.9k per unit mesh.
- **Ratings:** `py_final_a.json`, `py_final_b.json`.

## Final confirm 2 (on 8467f01, after the lighting final touch)

| round | rater A | rater B | result |
|---|---|---|---|
| confirm2 | **8.5** | **8.6** | no high issue: PY confirmed, no code changed |

- **What changed since 1430d42:** nothing in PY (only `04_shaders.js`, `12_scene.js`, `07_shell.js`). Studio views p1-p8
  are pixel-identical to 1430d42. In q13 / q14 the seats shift only by a uniform white-balance change
  (about +1.5 / +0.1 / −4.8 RGB); no new stripes, seams or dark artefacts (mean |dL| 0.17 / 0.48).
- **Routed lighting items (`from_py.md` "Final confirm"):**
  - Cool cast on PY fabric: **fixed.** q14 mid back B/R 1.39 -> 1.30 (target 1.30), q13 front back 1.49 -> 1.38
    (photos 1.22-1.36; 0.02 above, low), at unchanged L and contrast. Shell and console moved the same way.
  - Diamond sun patch on the q14 window-seat back: not changed (lighting, low; L 179 against 124 on the next back).
- **Calibration:** the w18 seam-bead high and the w16 rods / shell stripe stay fixed. Open: the flat cushion-front
  band (A medium, B low), the dark bead low in q14, and the w15 / w17 lows.
- **Triangles:** unchanged. **Ratings:** `py_confirm2_a.json`, `py_confirm2_b.json`.

## Back cushion form (confirm 3)

Target: the cabin-wide medium from integration rating L16 ("the PY back cushion still reads as a flat CG panel") and
rater A's medium on the flat cushion-front band.

| round | rater A | rater B | result |
|---|---|---|---|
| confirm3 | **8.6** (was 8.5) | **8.7** (was 8.6) | no high issue; the back reads as a cushion. Kept. |

- **Changed (`09b_py.js` only; the shared `09_seats.js` is untouched):**
  - **Back face (`pyBackGeo` / `pyBackDz`).** The back cushion's front edge is now subdivided and displaced, instead of being a flat rounded-rectangle loft. It has:
    - a 1.5 cm transverse crown;
    - a 1.2 cm valley at |x| 0.11 that rises 3 cm into each bolster;
    - a 4 cm lumbar crown that rises quickly from 6 cm and falls slowly to about 0.47 m.

    The sides and the rear stay the rounded rectangle that the seam bead and shell code expect, and the hourglass welts follow the new surface.
  - **Baked cavity shade (`pyBackShade`).** This is vertex colour on the same mesh: up to 22 % darker in the valley, 12 % on the bolster flank and low on the back, and 5 % lighter on the upper back. It is needed because the cabin fill is a hemisphere term: sideways slopes alone barely shade (candidates with geometry only kept q13 at 34-35 L).
  - No separate strips or reveals were added, so the w16 failure does not come back.
  - **Cushion-front band.** It is now one 36 mm box whose vertex colour grades from #5a6170 at its foot to #3a3f4c under the nose. In p5 at x 150 it ramps from L 40 to 51, where it used to be a flat L 33. It adds no triangles.
- **Metrics (baseline / candidate, same lighting head):**

  | metric | baseline | candidate | photo |
  |---|---|---|---|
  | q13 back range (7 px box blur, p90-p10, box 190-340 x 420-570) | 37 L | 48 L | py_37302: 60 L by this method, 53 L quoted by L16 |
  | q14 mid-back range (rater B) | 36 L | 53 L | – |
  | thin-dark, q13 | 7.61 % | 7.72 % | 13.11 % |
  | thin-dark, q14 | 10.05 % | 9.97 % | 13.11 % |

  q14 thin-dark meets the 70 % target and q13 does not: the remaining gap is fine pleats and stitching, not flatness.
  Matched-region colour holds the hue: q14 mid-back B/R moves from 1.297 to 1.301 (photos 1.22-1.36), and L drops by about 4 because of the cavity shade.
- **Triangles:**
  - py2: 19,306 -> 20,242 (+4.85 %)
  - py4: 38,878 -> 40,750
  - near LOD py2: 8,752 -> 9,036
  - far LOD: unchanged at 928
- **Open (all low):**
  - The q13 centre-seat right welt goes near-black where it lies in the shaded valley at the waist (A).
  - The fabric fleck smears a little on the steep valley and lumbar walls (A).
  - The valley shade runs almost the full height of the back. Rater B suggests tapering it above the waist and widening it to 0.035.
  - The lumbar makes a small hump in the p7 silhouette. Rater B suggests lt 0.38 or lumbar 0.032.
  - The band is still darker than the photo crease.
  - The w15 to w19 carry-overs remain.
- Ratings are in `py_confirm3_a.json` and `py_confirm3_b.json`.

## Final confirm (publish)

Head 7a2c8b9, after lighting L17 (PY white balance) and L18 (PY rear wall, PY top band); baseline e67f1a9 (confirm 3).

| round | rater A | rater B | result |
|---|---|---|---|
| confirm4 | **8.6** (= confirm3) | **8.7** (= confirm3) | no high or medium issue: PY confirmed, no code changed |

- **What changed since e67f1a9:** nothing in PY. The studio views p1-p8 are pixel-identical. The q13 / q14 seat-back boxes are
  byte-identical (B/R 1.383 / 1.301). Pixels with |delta| > 8: 21.2 % in q13 and 8.1 % in q14. All of them are environment
  (bins, ceiling, rear wall, curtains, glass), above y 200 in q13 and above y 326 in q14.
- **Context:** the cooler surround matches the photo hue: the q13 rear wall B-R went from +4 to +10.5 (py_37302 +9 to +11). The
  fabric-to-wall luminance ratio went from 0.55 to 0.61 (photo 0.57). Both raters judge that the seats sit slightly better in
  context.
- **Lighting notes (not scored, not routed as a blocker):** the PY walls and top band are now about 30-35 L under the photos
  (rear wall L 187 against 219-226). The PY fabric is still about 10-35 L darker than the photos. The q14 sun diamond is
  unchanged at L 163.
- **Open (all low, carried over from confirm 3):**
  - the q13 waist-valley welt;
  - the full-height valley shade;
  - the p7 lumbar hump;
  - the fleck smear;
  - the cushion-front band;
  - the q13 thin-dark measure (59 % of the photo);
  - small trim items.
- **Triangles:** unchanged. **Ratings:** `py_confirm4_a.json`, `py_confirm4_b.json`.
