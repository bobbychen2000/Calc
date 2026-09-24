# Economy (Recaro) - area report

Owned file: `src/09a_econ.js`. Shared-file edits (all noted in the commits):
- `src/09_seats.js`: SEATMAT Y values; new `armPost`; the econ `seatPickBox`; an econ row-variant key suffix in `buildSeats`/`econGeo`.
- `src/03_tex.js`: `LAYER_PARAMS[11]` albedo.
- `test/make_swatches.py`: the y_diamond entry, plus an optional name filter so a single tile can be re-cut.
- `tex/tex_y_diamond.png`.

## Scores

| round | rater A (skeptic) | rater B (geometry) | mean | high issues |
|---|---|---|---|---|
| r3 (start) | 5.5 (single rater) | - | 5.5 | 1 |
| w2 | 6.2 | 6.0 | 6.1 | 2 |
| w3 | 6.8 | 6.4 | 6.6 | 1 |
| w4 | 7.0 | 7.0 | 7.0 | 1 (A: tray arms inverted; fixed after the rating) |

Round 1 used the r3 rating as the brief says. I stopped after four rounds, the brief's maximum. Every round gained at
least 0.3, but the 8.5 target was not reached. The w4 findings (tray arms, tray face, pocket, headrest on mosaic seats,
hem, socket clearance, far-LOD depth offsets, pedals) were fixed after the w4 rating and are not re-rated. The
before/after sheet is `econ_before_after.jpg`.

## What changed
- **Fabric**
  - The diamond variant is now a crisp, near-touching stepped (ikat) lattice synthesised on the real tick weave. Before, it
    was a blurry upsampled crop that read as snowflakes.
    - Period 0.13 m, diamonds ~0.08 x 0.074 m, 8 mm steps, lift (2.4, 2.0, 1.4) [D] (y_47306, y_47302).
    - Diamond seats keep the tick weave on the pan.
  - The Y base colour is greyer (#6a79a8). q15 now renders #333e63 against the y_47300 photo #323e64; it was #2c3763.
  - The mosaic albedo is 1.5, so q15 p10/p90 is 41/107, the same as the photo.
  - The fabric mix varies row by row (a/b/c mesh-key suffix; the far LOD keeps the pattern).
- **Headrest**
  - The cushion is now separate, ~0.2 m tall and ~0.065 m proud, in the dash fabric. On mosaic-back seats it uses the tick
    weave so it stays visible.
  - The fabric back rises ~0.06 m above the cushion to a rounded top (y_47306, sanspotter 13).
  - The leatherette cover is one smooth piece: a plate, an overlapping fold, and a hem tucked back.
- **Rear shell**
  - A sculpted hood caps the seat top. From behind, only a thin blue rim shows (sanspotter 15/25-28).
  - The glass is 0.85 of the hood width, with ~0.03 m of shell above the bezel (y_47305).
  - The tray band under the hood is narrower (0.345), and the skirt runs below the pan top.
- **Screen and handset**
  - The screen stack is raised.
  - The handset is black, with a release key, a D-pad + OK, +/- and four colour keys, docked 0.02 below the bezel.
- **Tray and pocket**
  - The tray reaches up under the hood lip and carries the pictogram placard, dark latch and cup recess. The long "stow
    and latch" placard and a metal rail run along its foot.
  - Flat arms drop from hinge blocks at the rail ends to off-white barrel hubs.
  - The portrait universal AC socket (lit USB, green LED) sits at the upper left.
  - The literature pocket is a bulging grey flap with piping, over a see-through black net, with the purple-headed
    B777-300 safety card showing.
- **Seat front**
  - The armrest front is one continuous grey bracket with a pivot ring at pan height, and the paddle hangs from it.
  - The pillow is a domed superellipse in a lighter navy.
  - The life-vest pouch is a dark saucer with a red strap.
  - White seat-electronics boxes sit under each seat, a low baggage bar runs across the front legs, and the aisle-end
    button strip is black.
- **Footrest:** clamped, wider hangers; ribbed 0.15 m pedals with dark end caps.
- **Triangles:** econ3 near LOD 16,202 -> 24,068, far LOD 1,386 -> 1,716 (near LOD is used only close to the camera).

## Sources
- The official ANA Y pages, `ref/ana/y_47300`-`47307`.
- 61 in-service SANspotter photos of the 212-seat NH7 (2023), `ref/web/econ/sans_*`, gitignored. Sampled colours and
  measurements are in `econ_w2a/b`, `econ_w3a/b` and `econ_w4a/b.json`.

## Open issues
- **Lighting (lighting owner):** the shells and tray are ~30 % darker than the photos from a seat, and a sun-shaft hairline
  crosses a seat back in q15. Both are filed in `from_econ.md`.
- **Low, not done:**
  - The pillow has no seam.
  - Each footrest hanger is still two straight links.
  - The tick fabric looks like broad strokes on the nearest seat tops (texture filtering).
  - The inside of the diamonds still reads slightly as a knit.
- **Questions:** in `questions_econ.md`. They cover the coat hook vs the in-service fittings, the magazine vs the safety
  card, the belt colour, the overall seat-back height (no drawing found; the back top is now ~1.31-1.36 m) and the
  cover shade.
