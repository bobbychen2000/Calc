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
