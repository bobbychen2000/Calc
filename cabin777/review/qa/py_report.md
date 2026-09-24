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
| final fixes after w4 (not re-rated; round limit) | - | - | this commit |

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
