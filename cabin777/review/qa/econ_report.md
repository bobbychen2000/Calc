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

## Wave 3 (2026-10-24)

### Scores

| round | rater A | rater B | mean | note |
|---|---|---|---|---|
| w6 (start of wave 3, cc096b3) | 6.6 | 6.8 | 6.7 | the w5 ratings had rated the state *before* cc096b3 |
| w7 | 6.9 | 7.2 | 7.05 | |
| w8 | 7.3 | 7.4 | 7.35 | |
| w9 | 7.3 | 7.3 | 7.3 | |
| w10 | 7.2 | 7.4 | 7.3 | plateau; gap analysis `econ_gap10.json` |
| w11 | 7.3 | 7.5 | 7.4 | best round |
| w12 | 7.2 | 7.4 | 7.3 | |
| w13 | 7.2 | 7.3 | 7.25 | fourth plateau round: stop |
| wF (confirmation, ced028f) | 7.2 | 7.5 | 7.35 | the shipped state |

Stopped under the plateau rule: four rounds after the plateau, two in a row gaining < 0.2. The 8.5 target was not
reached; no open high-severity issue.

**The w5 "regression".** The w5 ratings were committed in cc096b3 but rated the state before it. The drop from w4 (7.0) came
from the lighting r3 AO lift, which made the fabrics 1.6-2x too light; cc096b3 corrected that. Nothing was reverted.

**Shipped state (ced028f).** From w11 to w13 the fabric-tile edits oscillated between the raters' targets and each round
rated lower. The final state therefore keeps the w11-rated tiles (from 1373ab7), plus the non-fabric fixes from w11-w13
that both raters marked fixed. The confirmation rating wF put it level with the best round.

### What changed in wave 3
- **Back.** A crowned loft (`econCrownLoft`) with ~4.5 cm rolled side edges replaces the flat slab. The hood is 0.40 wide and
  flat with tight corners (bezel 0.79-0.84 of it, y_47305 0.81-0.86). The shell cap sits over the back top, 7 mm above the
  fabric, so the coplanar z-fight is gone and only a thin navy rim shows from behind. The back is ~0.44 wide at headrest
  height, with a darker tick centre strip from the pad top to the back top (y_47306).
- **Headrest.**
  - The pad is U-shaped, with round wing bolsters ~2 cm proud of a recessed cover, and sits 0.025 lower so the back rises
    ~5.5 cm above it.
  - Each pad uses a different weave from its back (y_47306), except that fleck backs keep fleck pads (y_47300 4x crop).
  - The cover is 0.255 wide and bowed, with a rolled fold, a hem band with a light stitch, and its foot tipped forward. It
    is darker leather (`yCover` #3a4060, r 0.62).
- **Fabrics** (`test/make_swatches.py`):
  - New photo layer 26, the `y_mosaic` dash mosaic, replaces the procedural layer 11.
  - `y_diamond` uses ceil step quantisation; floor had grown every diamond by one step.
  - `y_fleck` is the petal fleck.
  - `synth_y_tick` adds column structure to the tick weave.
  - Pans mix independently of the backs (`econPan`, y_47300).
  - The 6-cycle mix puts tick on ~half the backs (y_47300 / 47301).
  - Tick pans are more saturated (`ECON_PAN`).
- **Pillow.** Wider (0.8 of the pan), plain and flat. The sphere poles moved to the side tips; on the face, a pole had read
  as a tuft.
- **Seat back, lower.**
  - Two mesh pouches with dark hems and a charcoal centre strap.
  - The safety card shows its white half under the purple header.
  - Faint grey tray pictograms; the black and red ones had read as a 3-port box.
  - Glossy dark-grey bezel with a frame ring.
  - Handset ~25 % wider (0.47-0.49 of the bezel, y_47305 0.50).
  - Coat-hook knob on the hood side, lower and aft (sans 22).
- **Front and structure.**
  - Smooth lofted footrest hangers with a silver joint (y_47304, sans 23).
  - Teal tongue strap and navy buckle strap (y_47303).
  - Armrest tilted 4 deg nose down, with a slim raked post.
  - Soft contact creases at the back / shell junction.
- **Triangles.** 1,001,836 at the start of wave 3, 1,026,656 now (+2.5 %; the budget is +25 %).

### Shared-file edits (each named in its commit)
- `09_seats.js`: SEATMAT `yFabric`, `yFabricB`, `yFabricC`, `yFabricD`, `yHead`, `yCover`, `yBelt`, `yPillow`.
- `03_tex.js`: `LAYER.yMosaicP` 26, `N_LAYERS` 27, and `PHOTO_LAYERS` / `PHOTO_ENC` / `LAYER_PARAMS` 26.
- `test/make_swatches.py`: the econ functions.
- `tex/tex_y_*.png`.

### Still open (wF)
- **Fabrics.** Synthesised tiles cannot match the real weaves exactly. The raters' targets for the diamond and mosaic
  contradicted each other from round to round. A 1:1 close-up photo of each fabric would settle it (question 13).
- **Headrest covers.** Head-on they are still a shade bright against the backs (0.79-1.0 vs 0.54-0.86 in y_47300). Seen at
  an angle, the photos show a slate grey-blue (question 14).
- **Back top.** A ~1.5 cm white hood rim shows head-on in q15. Fixing it depends on whether the y_47300 headrests are
  raised (question 15).
- **Armrests.** They still read as boxy on a post. y_47303 shows a J sweep.
- **For other areas** (`from_econ.md`):
  - the q15 / q17 cameras do not match y_47300 / y_47303;
  - fabrics smear on 45 deg faces (triplanar blend);
  - the q16 near fabric is too light.

### Sources
- Official ANA Y pages, `ref/ana/y_47300`-`47307`.
- SANspotter NH7 2023 set `sans_12`-`43` and flight-report 57325 (NH5, JA794A), in `ref/web/econ/` (gitignored). The URLs
  are in the rating JSONs.
