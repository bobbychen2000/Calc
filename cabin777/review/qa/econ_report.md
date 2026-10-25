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

## Wave 3c (fresh eyes, 2026-10-24)

Started on head 2c1eb9d, after the lighting loop's round 1 (2913db8) fixed the economy-block darkening. Budget: 5 rounds.

| round | rater A | rater B | mean | note |
|---|---|---|---|---|
| w14 (2c1eb9d, baseline under the new light) | 7.2 | 7.5 | 7.35 | econ unchanged since ced028f; gap analysis `econ_gap14.json` |
| w15 (f9c2e2e) | 7.7 | 7.6 | 7.65 | photo-cut fabric tiles + gap14 items 1-4 |
| w16 (2e3ebfa) | 7.7 | 7.8 | 7.75 | fleck snow fixed close up, lost at distance |
| w17 (b9489fe) | 7.9 | 8.0 | 7.95 | best round; hero row as y_47300, J arm |
| w18 (9cf4598) | 7.9 | 8.0 | 7.95 | budget reached; fleck / cover overshot |
| wG (295e953, confirmation) | 7.9 | 8.0 | 7.95 | the shipped state (level with the best rounds) |

The 8.5 target was not reached; no high-severity issue is open.

### What changed in wave 3c
- **Fabrics, cut straight from the official photos** (the user's request; `make_swatches.py` `Y_PHOTO` / `y_photo()`).
  The six re-syntheses of w5-w13 are gone. Tick, diamond and mosaic come from the y_47306 close-up (scaled from the
  0.255 m cover), the fleck from the y_47300 front row. The processing:
  - lighting removed by normalised convolution over fabric pixels only (no dark rims from the shell / window);
  - seamless by a minimum-error seam cut over a 12 px overlap (image quilting), then a wrap-padded bicubic resize
    (a plain resize left dark corner dots, a Fourier resample rang round the flecks);
  - a second wrap blur flattens the tile-scale shading (it repeated as a grid of squares);
  - per-tile contrast exponent / soft floor calibrated on the photo's own p10 / p50 / p90;
  - the diamond crop is de-foreshortened (1.34x in x), the mosaic rows levelled 3 deg; tick columns lifted 1.6x
    (minification); fleck cores kept over the ground, near-neutral tint.
  Both raters marked the mosaic and diamond fixed in w15 (they had been at 6-6.5 since w5).
- **Headrest** 2.5 cm higher (back ~3 cm above the fold, y_47300-47303); the back top rolls over a lowered shell cap, so
  the white rim head-on is gone; the far-LOD hood sits under the back top (every far back had a white cap).
- **Cover** slate #2d3248 r 0.5 (was navy #3a4060). **Pads** paired as y_47300: fleck back / tick pad, tick back /
  fleck pad. No tick strip on fleck backs.
- **Fabric mix**: fleck on a third of the backs; the q15 hero row reads tick / fleck / tick / fleck as y_47300.
- **Pillow** ~10 cm full with a concave top edge. **Pan** a 5 cm bullnose tucking to a narrower base, in a grey tray set
  5 cm back. **Arm** support one swept flat J moulding (2.5 x 5.6 cm). **Hood** 0.374 wide, upper back 1 cm wider, so
  the white hood sides hide head-on.
- **Triangles**: 3-seat unit 27.2k -> ~28.4k (+4 %).

### Shared-file edits (each named in its commit)
- `09_seats.js`: SEATMAT `yFabric`, `yFabricB`, `yFabricD`, `yCover`.
- `test/make_swatches.py`: the econ section (`Y_PHOTO`, `y_photo`, `_wrap_cut`, `_wrap_resize`, `_gblur`); the old
  `synth_y_tick` / `y_diamond` / `y_fleck` / `y_mosaic` synthesis removed. `tex/tex_y_*.png`, `tex/sizes.json` Y entries.

### Still open
- **Tick columns at row distance** (q15 column CV ~0.08 vs 0.24): mip filtering; a mip bias / anisotropic filtering on
  the photo fabric layers is asked of lighting in `from_econ.md` (it would also cure the side-panel smear).
- **Cover sheen**: one flat value cannot match both head-on (wG L62 vs 37-47) and grazing (L41 vs 65-83); the silver-grey
  grazing sheen of the leatherette needs a sheen lobe (lighting, `from_econ.md`); then the base can go back to ~#2a2f45.
- **Fleck shape**: the 3.4 mm/px source makes round dots, not 3-5 mm petals; a frontal close-up would fix it (question 18).
- **Diamond**: soft (2 mm/px oblique source), ground a little grey.
- Cover hang (question 17), pans all tick (y_47300 shows some mosaic pans), pillow seam, bezel dots.

Before/after sheet: `econ_before_after_w3c.jpg` (own renders: 2c1eb9d vs 295e953, with the paired ANA photos).

## Wave 3d (plateau breaker, 2026-10-24)

Started on 295e953 (wave 3c final, wG A 7.9 / B 8.0). A fresh calibrated round (w19) and a gap analyst (`econ_gap19.json`),
then four fix rounds, the brief's cap.

| round | rater A | rater B | mean | note |
|---|---|---|---|---|
| w19 (295e953, baseline) | 7.8 | 8.0 | 7.9 | unchanged code; gap analysis `econ_gap19.json` |
| w20 (027a1f2) | 7.7 | 7.9 | 7.8 | C arm, hidden hem fixed, re-cut tiles; the smooth r 0.38 cover read as a monitor head-on (A high), tile boost overshot |
| w21 (b0edece) | 7.9 | 8.2 | 8.05 | cover navy satin, flat arm plate + deep end panel, boost halved |
| w22 (eac092a) | 7.9 | 8.1 | 8.0 | light hem band read as a chin head-on; the lighting -0.5 photo mip bias landed (tick speckle) |
| w23 (066375f) | 8.0 | 8.2 | 8.1 | **best round, shipped**; hem dark, rolled foot only; tiles compensated for the mip bias |

The 8.5 target was not reached. No high-severity issue is open. Per detail at w23, B reaches 8.5 or more on armrests (8.7)
and belts, and 8.0-8.4 on most else. Both raters' lowest details are the diamond (7.7), the fleck close up (A 7.6), the pan
(7.7-7.8) and the legs (7.5-7.7).

### What changed in wave 3d
- **Armrests (regular rows): one C moulding, open at the front.** It is made of the arm, a 2.1 cm rear sweep and a flat
  ~2.2 x 6 cm lower plate at pan height (y_47303, sans b_ss_18). At the block ends a deep ~11-13 cm panel has a swept-up
  lower-rear corner. The grey front bracket, white paddle and aisle-end side panel now appear only on exit rows (y_47302
  shows the exit / bulkhead arms). B scored the armrests 7.9 at w19 and 8.7 at w23.
- **Headrest cover.**
  - The hem, stitch and mark had been quads 6-9 mm *behind* the plate since w10, so they never rendered (found by A in
    w19). They are now lofted over the plate along its slope.
  - The hem is a dark band with a lighter rolled foot (close-up lift 1.5x, y_47306 1.45x; head-on a one-row lip).
  - `yCover` is #222842, r 0.52, smooth (LAYER.none), with a ~2.5 mm bow. q15 middle covers measure L59, B/R 1.66
    (y_47300: 53, 1.84). At w19 they were L68 / 1.54. The r 0.38 trial in w20 was L91 / 1.31.
- **Pillow.** 0.33 x 0.27 (0.77 of the back, y_47300), 4 cm higher and 4 deg more upright, with a pillow-coloured piped
  seam.
- **Fabric tiles** (`make_swatches.py`, still cut straight from the official photos):
  - The y_47306 tick crop leaned 7 deg (oblique seat), so its columns cancelled over a back. It is now rotated upright.
  - The tick tile is 0.29 m (~13 mm pitch), floor 0.10, strokes pulled 20 % toward the ground.
  - The 0.5-2.5 cm band gets a log-luminance boost (tick 0.1, fleck 0.6, mosaic 0.6), plus fine-grain damping.
  - The fleck floor is 0.15, its cores exp 1.2 and less blue. q15 fleck B/R is 2.48-2.53 (y_47300 2.50-2.58).
  - `yFabricD` is #444d6b and `yFabricB` is #5f6ba0.
- **Triangles.** econ3 28,485 -> 28,891 (+1.4 %); econ4 37,208 -> 37,948 (+2.0 %); far LOD unchanged.

### Shared-file edits (each named in its commit)
- `09_seats.js`: SEATMAT `yCover`, `yFabricB`, `yFabricD`.
- `test/make_swatches.py`: the econ section.
- `tex/tex_y_tick.png`, `tex_y_fleck.png`, `tex_y_mosaic.png`, and `tex/sizes.json` (y_tick).

### Still open (w23a / w23b)
- **Cover off-axis** (both raters, every round): the body is L34-38 at grazing angles against 86-134 in y_47306. Only a
  cover-only sheen lobe in the shader can make it navy head-on *and* silver-grey at an angle. Every roughness value tried
  (0.3-0.62) trades one view for the other. This is with lighting (`from_econ.md`, w19).
- **Tick:** strokes still cover ~0.12 bright vs 0.083 (q15). The next step is a stroke factor of 0.65, or no mip bias on
  layer 16.
- **Fleck close up:** merged blobs (median 8 px vs 3 px, coverage 0.29 vs 0.13). The fix is Poisson-thinning the cores
  with a fixed seed while keeping the row-distance contrast (exp back to 1.05).
- **Diamond:** washed out after the bluer base. Raise the lattice contrast ~1.25x.
- **Low items:** a darker pillow with weave, the end-panel top curve and recessed border line, bezel dots, a padded
  pocket flap, the hood side band and the legs.
- **QA cameras** (integration): q15 / q16 do not frame y_47300 / y_47301. The gap analyst estimated +0.2-0.3 from a
  matched q15 alone. The camera for that is in `from_econ.md`.

Before/after sheet: `econ_before_after_w3d.jpg` (own renders: w19 295e953 vs w23 066375f, q15 / q16 / arm / headrest).

## Wave 3e (matched cameras, 2026-10-24)

Started on 860d18f (wave 3d final, w23 A 8.0 / B 8.2 on the old cameras). Four rated rounds, the brief's cap, plus one
measured regression fix.

| round | rater A | rater B | mean | note |
|---|---|---|---|---|
| w24 (d433091, econ code = 066375f) | 8.0 | 7.8 | 7.9 | **new q15-q17 cameras**; the matched q15 exposed the pan order, cover and pillow proportions |
| w25 (5146ec6) | 8.0 | 8.0 | 8.0 | pan order as y_47300, cover 2 cm shorter, pillow lower / flatter, warm arms; diamond 1.25x and fleck thinning overshot |
| w26 (432144c) | 8.0 | 8.1 | 8.05 | **best round**; diamond 1.05x, fleck keep 0.8, tick stroke rims eased, pillow dog-ears |
| w27 (10ffbc6) | 7.9 | 8.0 | 7.95 | diamond pans on their own layer 34; base colour not corrected for the lower gain -> pan 1.8x too light (high) |
| w28 (ed2e6ec, unrated) | - | - | - | regression fix: layer 34 gain 0.8, base #414862; q15 diamond pan L79 / B/R 1.85 / p90/50 1.34 / bright 0.06 vs y_47300 74 / 1.81 / 1.37 / 0.08 |

The old and new camera scores are not directly comparable: w24 re-rated the unchanged w23 code 0.2 lower on the matched
q15. The 8.5 target was not reached. Shipped state: w28 (w26 plus the tick-pan colour, the pillow and the corrected
diamond pan). Both raters' w27 numbers for everything except the diamond pan and pillow corners were at or better than
w26.

### What changed in wave 3e
- **QA cameras (shared: `test/qa.js`).**
  - q15 frames y_47300: row 34 D-G from (0, 1.45, 48.05), pitch -0.30, near clip 1.25, which drops row 33 cleanly.
    Seat pitch is 162 px in the render against 154 px in the photo. The integration camera from the door-4 cross aisle
    showed the galley monitors, so it was not used.
  - q16 is now in the right aisle looking aft, with the triple block on the left as in y_47301.
  - q17 is in the right aisle looking outboard at H-K, with seat-back screens on the left as in y_47303.
  - Both q16 and q17 are still wider and closer in the photos, which were shot with ~80 deg lenses against the
    engine's fixed 64 deg.
- **Pans.** The econPan list is reordered (same mix), so the hero row reads tick / tick / diamond / mosaic. Diamond
  pans use a new photo layer 34 (the y_diamond tile at 0.8 gain, shared `03_tex.js`) with base #414862. Tick pans are
  #535b7d.
- **Headrest cover.** The plate starts 2 cm higher and is 0.245 wide; the hem, foot, stitch, mark and far-LOD box
  moved with it.
- **Pillow.**
  - Half-height 0.11, 3.5 cm lower and tipped back 6 deg, so it rests on the pan.
  - Softer dog-ear corners, waist halved, fuller dome.
  - Pillow-coloured 2 mm piping, `yPillow` #394260.
- **Tiles** (`make_swatches.py`).
  - Tick: strokes 0.72 toward the ground, with each stroke's rim eased 60 %.
  - Fleck: Poisson-thinned with a fixed seed, ~20 % of the components dropped and filled with their local ground,
    exponent 1.0, peak 1.25x.
  - Diamond: lattice 1.05x.
- **Other.** Buckle covers #9da2a9. Arms are warm light grey (`SEATMAT` arm / armPad / armPost).

### Still open (w27a / w27b)
- **Cover off-axis (lighting):** navy and 2.4-3.5x too dark at grazing angles, slightly light head-on. Both raters
  rank it the biggest mismatch visible at thumbnail size.
- **Far rows light and snowy in q16 (lighting):** fade the -0.5 mip bias and the photo-tile contrast with distance
  (w26b-3 / w27b-3).
- **Tick at row distance (A):** p90/p10 2.5 against 3.4-3.6, from soft strokes after the rim easing. A wants the rim at
  0.65 and a deeper ground; B scores the tick at 8.4.
- **Diamond backs at row distance:** stars bold, light-star share 0.23 against 0.12. Splitting the tile into star 0.75x
  and weave 1.15x is the next step.
- **Cover height:** B measures it ~25 % too tall head-on; A finds y_47300 and y_47306 in conflict (question 21).
- **Pillow:** A says the corners are now too round; both find it too blue (B/R 2.15-2.27 against 1.97-2.05) and without
  weave.
- **Mosaic pan:** a step light and blue (L93 against 81).
- **Low items, carried:** the cover foot crease, belts and the silver tongue, bezel dots, the pocket and the legs.

Before/after sheet: `econ_before_after_w3e.jpg` (own renders: w24 066375f code vs w27 10ffbc6 at the matched cameras,
q15 / q16 / e4 / e1, with the ANA photos).

## Wave 3f (2026-10-24/25)

Started on 0f172d3 (econ code ed2e6ec, the unrated w28 diamond-pan fix, plus lighting round 2). One fresh calibrated round
(w29) and three fix rounds (w30-w32), the brief's cap of four.

| round | rater A | rater B | mean | note |
|---|---|---|---|---|
| w29 (0f172d3, baseline) | 7.9 | 8.1 | 8.0 | w28 diamond-pan fix confirmed (L80 vs 82); lighting r2 invisible at the econ cameras (q15 diff 0.08) |
| w30 (d26609f) | 8.1 | 8.2 | 8.15 | q15 camera matched to y_47300 (back tops y225 vs 233); tick ground deepened per channel (near-black / ultramarine close up) |
| w31 (befdc88) | 8.0 | 8.3 | 8.15 | luminance-only deepening (close-up fixed, row distance washed); cover takes lighting's SHEEN flag; lighting r3 snapshot lifts the seat level 5-10 % |
| w32 (cf457a8) | 8.0 | 8.4 | 8.2 | **best round**; diamond stars back, one arm bar head-on, pillow dog-ears; the new pan-joint seam filler read as a navy rail (medium, both) |
| final (this commit) | - | - | - | w32 with the filler removed (joints as rated in w31), diamond pan #464a68 (w32a-3), dead stroke-tint line dropped |

The 8.5 target was not reached. B reaches 8.5 or more on armrests (8.6), pillow (8.5) and fabric mix (8.5); A's lowest
details are tick (7.8), fleck (7.8), legs (7.5) and pan / front (7.5, the filler, now reverted). No high-severity issue
was raised in any round. Shipped: w32 minus the filler (a revert to the w31-rated state for that one part).

### What changed in wave 3f
- **QA camera (shared: `test/qa.js` q15):** (0, 1.55, 48.05), pitch -0.26. That's 10 cm higher and flatter than wave 3e,
  so the backs, covers, pillows and seat centres now sit within 5-10 px of y_47300 and the raters can measure the same
  boxes.
- **Headrest pads:** tick backs alternate a light cloudy pad (y_47300 seat D, L119-128, diamond tile on layer 34 at a
  light base) and a dark fleck pad (seat F) by seat pair (`econHead(F, k, rot)`, shared with the far LOD).
- **Headrest cover:** takes lighting r3's `SHEEN` flag (`yCover.l = LAYER.none + SHEEN`). q16 covers go from L55 to
  67-81 (y_47301 67-108); head-on is unchanged.
- **Pans:**
  - 2.5 cm wider (0.455) with straighter side walls; the inner joints went from 11-23 px to 4-14 px.
  - The mosaic pans get their own base `ECON_PAN_C` #525977, at B/R 1.69-1.70 vs 1.69-1.72.
  - The diamond pans are #464a68 at layer-34 gain 0.9 (stars visible again; L75 vs 75).
- **Armrests:** 0.054 -> 0.047 wide, now 21-26 px vs 23-25 head-on. The nose is 2 cm shorter. On regular rows the lower
  plate is dark grey #66686e, so head-on it reads as one light bar as in y_47300. The arm is #bfbcb8.
- **Pillow:** bow-tie waist on both long edges (0.12), corner pull 0.45 with a cube law, so the dog-ears read in e4b and
  q15. Dome exponent 0.6, `yPillow` #3a4159 (B/R 2.0 vs 2.0).
- **Tiles (`make_swatches.py`):**
  - Diamond: star band (> 4 px) 0.7x, fine weave 1.15x. q15 back coverage went from 0.23 to 0.11 (photo 0.12).
  - Fleck: tighter second flattening, peak 1.35.
  - Tick: the w30 per-channel deepening reached the q15 contrast (3.1-3.5) but went near-black close up (e4 p90/p10 7.1).
    The final tile deepens luminance only, down to 0.42x the median, with a column profile of 0.5, stroke rim 0.5 and band
    boost 0.45. That gives e4 4.8-5.0 (photo 4.1) and q15 backs 2.7-2.8 (photo 3.2-3.5).
  - The tick tile is stored greyscale, so a stroke tint has to come from the material, not the tile (w32a-2).
- **Triangles:** econ3 28,955 and econ4 38,012, the same as at the start of the wave (the seam filler was the only
  addition and it was removed). Far LOD is unchanged.

### Shared-file edits (each named in its commit)
- `09_seats.js`: SEATMAT `yPillow`, `arm`, `yCover` (SHEEN flag).
- `03_tex.js`: `PHOTO_GAIN` 34 (0.9).
- `test/make_swatches.py` econ section, `tex/tex_y_tick.png`, `tex_y_diamond.png`, `tex_y_fleck.png`.
- `test/qa.js`: the q15 camera.

### Still open (w32a / w32b)
- **Cover height (medium, both raters, every round):** h/w 0.85-0.88 against 0.67-0.75 in y_47300; y_47306 and b_ss_13
  hang it lower. This is question 21, and it is now the largest econ-owned mismatch.
- **Tick at row distance:** the tile can't fix this without crushing the close-up. Lighting has been asked for a -0.25
  mip bias on layer 16 alone (`from_econ.md`, w31). The alternative is a stroke tint in the material.
- **Diamond stars on pans:** at about half the photo's contrast (bright 0.02-0.06 vs 0.07).
- **Pan joints:** the outer ones are still 4-6 px dark. The next try is to widen the pans 6-8 mm per side and check the
  plate, not to add a filler.
- **Fleck:** distance contrast 0.9x, with a faint repeated cloud.
- **Light pad:** coarse motif close up.
- **Arm:** still ends ~30 px low head-on.
- **Carried small parts:** cover foot crease, belts mid-pan, bezel dots, pocket, legs.
- **Lighting:** seat level lifted 5-10 % by the r3 snapshot; far-row snow; triplanar smear on back tops and pads in q16;
  covers still short of the off-axis level (q16 L67 vs 108).

Before/after sheet: `econ_before_after_w3f.jpg` (own renders only: w29 vs final; q15, q16, q17, e4, e1).

## Wave 3g (2026-10-25): geometry focus (pan / front, under-seat, far rows)

Started on 2d42289 (wave 3f final). Rater A had held at 8.0 for about eight rounds while the work went into the fabric
tiles, and A's lowest w32 details were geometry. This wave ran one fresh calibrated round plus a gap analysis (w33,
`econ_gap33.json`), then three fix rounds (w34-w36), the cap of four.

| round | rater A | rater B | mean | note |
|---|---|---|---|---|
| w33 (2d42289, baseline) | 7.8 | 8.1 | 7.95 | under-seat and pan front measured closely for the first time; joints 8-13 px again without the filler |
| w34 (8ee9c1c) | 8.0 | 8.2 | 8.1 | pan rebuilt (square in plan, 3 cm front roll), dark under-seat, tube legs, half-disc pouch, far LOD extras |
| w35 (6df71f4) | 8.1 | 8.3 | 8.2 | joints closed (2-4 px vs 2), cover foot 3 cm higher (question 24), aisle-end plate under the arm |
| w36 (eb4c09f) | 8.2 | 8.4 | 8.3 | **best round of any wave**; cover 0.22 wide (1.03x head-on), far fabrics flat, belts shorter |
| final (this commit) | - | - | - | w36 with the pouch recoloured cool smoky grey (w36a-5 / w36b-2: the w36 brown core read as a bowl) |

The 8.5 target was not reached. B gives 8.5 or more to armrests (8.8), headrest pad + cover (8.7), seat pan / front (8.7),
diamond (8.5) and fabric mix (8.5); A to fabric mix (8.6), pan / front (8.5). No high-severity issue in any round.

Detail moves w33 -> w36 (A / B): pan / front 7.6 / 7.8 -> 8.5 / 8.7; legs / under-seat 7.0 / 7.4 -> 8.3 / 8.2; headrest
pad + cover 7.9 / 7.8 -> 8.4 / 8.7; armrests 7.8 / 8.6 -> 8.3 / 8.8; far rows 7.5 / 7.6 -> 7.5 / 7.7 (unchanged).

### What changed in wave 3g
- **Pan (gap33-2, w33a-3, w33b-1/2, w34a-1):** a custom loft replaces `cushionSecs` (5 cm roll on all four sides opened
  a ~0.13 m V between neighbours, the dark joints). 0.478 wide, square in plan, 1.0 cm side roll, 3.2 cm front roll over a
  near-vertical fabric face, 8.5 cm thick, bottom tuck, 5 deg. No filler. Sources: sans 13 / 18, y_47302, y_47300.
- **Under-seat (gap33-1, w33a-1):** dark tray #2c2f35 closing the pan base, side beams and spreader tubes dark metal
  #3a3d44, pan-front stiffener removed (y_47302 #222631 under the pan, sans 13 / 23 near-black). Baggage bar stays silver.
- **Legs (gap33-3):** slim round silver tubes (rear post, raked front strut, floor rail) with dark track fittings
  (y_47303 aisle feet, sans 23). Cheaper than the old boxes.
- **Life-vest pouch (w33a-2, w33b-3):** a flat half-disc hanging face-forward, tipped 25 deg, with a red strap and blue tag;
  final colour cool smoky grey with a dark vest core (y_47302 crop).
- **Electronics box:** light grey #c8cacc with a dark display and blue LED, hanging from the tray just behind the pan face.
  The under-seat SEB box is charcoal.
- **Headrest cover (question 24):** foot 3 cm higher (h/w 0.88 -> 0.70 vs 0.72 in y_47300; the real head-on sans 13 also
  ends it at the pad foot), then 0.245 -> 0.22 wide (both raters 1.15-1.17x -> 1.03x). Hem, foot tube, stitch, mark and
  the far cover follow.
- **Arms:** aisle-end lower plate ~8 cm deep (was 13) and 4.5 cm higher, so it meets the arm (3-5 px gap vs 2-8).
- **Belts:** buckle nearer the crease, strap 0.19 at 30 deg, grey buckle cover #7d828a.
- **Pans colour:** tick #4b537a, diamond #44496b, mosaic #444c72.
- **Far LOD:** new pan box, dark under-pan block, baggage bar, arm plates (grey; white on block ends), box pillow, and flat
  per-fabric mean colours on the generic weave layer (`econFarMat`).
- **Studio:** `review/spec_econ.json` gains e10_under and e11_panedge.
- **Triangles:** econ3 28,955 -> 28,545, econ4 38,012 -> 37,556 (the tube legs are cheaper than the boxes); far3 1,716 ->
  1,824, far4 2,284 -> 2,416 (+6 %).

### Still open (w36a / w36b)
- **Mid / far rows snowy, no dark row gaps (medium, both, four rounds):** q15 band L98 vs 92, 2.9 % of pixels below L50 vs
  13 %. These rows sit inside the 9.5 m LOD switch, so the flat far fabrics never reach them. Lighting / integration call:
  fade the photo-tile contrast with distance (4-8 m), or switch econ to the far LOD from ~5 m (`from_econ.md`).
- **Cover off-axis (medium, A):** navy in q17 (#313e73) vs silver-grey in y_47303 (#808fb2); sheen lobe strength (lighting).
- **Pans a step blue after the lighting snapshot 69d3b46** (B/R 1.99-2.08 vs 1.74-1.87); tick pan contrast 2.9 vs 4.7.
  The colour moved with the lighting in each of the last three rounds, so it is left until lighting settles.
- **Low, carried:** belts still read as a V head-on (y_47303 shows webbing on the pan, y_47300 none), pillow a flat plaque,
  fleck specks haloed, aisle-end member not one J bracket, tray / pocket.

Before/after sheet: `econ_before_after_w3g.jpg` (own renders only: w33 2d42289 vs w36 eb4c09f; q15, q16, q17, e10, e11,
e1, e4).

## Wave 3h (2026-10-25): confirm and polish

Started on 8b965a4 (wave 3g final plus a lighting snapshot). One fresh calibrated round (w37), then two fix rounds
(w38-w39), the cap of three. The 8.5 bar was not reached; no high-severity issue in any round.

| round | rater A | rater B | mean | note |
|---|---|---|---|---|
| w37 (8b965a4, baseline) | 8.2 | 8.4 | 8.3 | = w36; tick contrast up from lighting 8b965a4, pouch grey (28ea1d8) |
| w38 (6a120ff, + lighting 9624e60) | 8.3 | 8.4 | 8.35 | pans less blue, belts under the pillow, pillow darker, far LOD keeps the photo tiles |
| w39 (a4ad504) | 8.3 | 8.4 | 8.35 | pouch face up-forward, belt hardware under the pillow edge, pillow #363d57, fleck -10 % |
| final (this commit) | - | - | - | w39 with the fleck darkening halved (w39a-3: it hit backs E / G, L49-50 vs 54-60) |

B gives 8.5 or more to tick (8.5), diamond (8.5), mosaic (8.5), fabric mix (8.5), headrest pad + cover (8.7), armrests
(8.8), pan / front (8.7); A to mosaic (8.5), fabric mix (8.6), pan / front (8.5). Lowest: far rows (A 7.5 / B 7.9),
tray / pocket (7.9 / 7.8), back silhouette and rear shell (8.0 / 8.1).

### What changed in wave 3h
- **Pans:** ECON_PAN #4b537a -> #4d5472, ECON_PAN_C #444c72 -> #474e69 (B/R 1.99-2.06 -> 1.84-1.88 vs 1.74-1.82). The
  ~10 L darkening of the near pans in w38 came from lighting 9624e60 (w38b-6) and is not compensated here.
- **Belts:** hardware tucked under the pillow edge (y 0.465, z -0.17, x +-0.012), navy-grey buckle cover #3a3f52, straps
  0.10 (were 0.19 at 30 deg). B: light pixels at the pillow foot 1012 vs photo 882 (w37 ~1600).
- **Pillow:** SEATMAT.yPillow #3a4159 -> #363d57 (L48 vs 46-62).
- **Life-vest pouch:** it now swings down-forward with its face up-forward (the w38 50 deg version was edge-on and
  back-face culled from the high front views), 35 deg, lighter shell #767983 / core #5e6068, strap and tag on its face.
- **Far LOD:** `econFarMat` keeps each fabric's photo tile on a base x0.92 (the flat mean colours of w36 read as plain
  royal-blue blocks). A nearer econ LOD switch (nearK 0.45, ~4.3 m) was tried and reverted: the rows became flat blocks.
- **Fleck:** SEATMAT.yFabricD #444d6b -> #424b68 (final; w39 #3e4662 overshot on the fleck backs).

### Still open (w39a / w39b)
- **Far rows (medium A / low B, seven rounds):** seat pixels only, L88 vs 84, p90/p10 2.57 vs 3.72, L<50 4 % vs 13 %. Part
  of the old far-box gap was framing (our end wall above y~165 where y_47300 still shows seats). The remaining lack of
  dark row gaps is the AO / exposure question in `from_econ.md`; both raters suggest a 1 cm dark strip under the far
  head box as an econ-side try.
- **Cover off-axis (medium A):** q17 L60 B/R 2.40 vs y_47303 L153 / 1.47; needs the grazing sheen (lighting).
- **Tick back F (low A):** L90 vs 70 (A had mislabelled it as fleck through w38).
- **Low, carried:** belt strap stubs either side of the buckle (A wants the silver tongue visible again), pillow a flat
  plaque, pouch opaque, aisle-end member not one J bracket, black tray lip under the pan front.

Before/after sheet: `econ_before_after_w3h.jpg` (own renders only: w37 8b965a4 vs w39 a4ad504; q15, q16, q17, e10, e7,
e1).
