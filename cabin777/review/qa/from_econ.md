# From econ (09a_econ.js) to other areas

## To lighting / integration (04_shaders.js, 12_scene.js)
- **Economy rear shells are under-lit in the seated view** (econ w2 rater B). In q18_seat35C the off-white Recaro shells
  render ~30 % darker than in y_47305 / sanspotter 15 (shell #c8c9cb-ish in the photo under cabin light). Suggested fix: cap
  the AO-volume darkening on seat-back rear faces (e.g. clamp ao >= 0.75 for the `yShell` material) or add ~15 % fill from
  the PSU downlights.
- **Hairline light streak across a seat back in q15_econFronts** (thin bright diagonal line on the right-hand foreground
  seat). It looks like a window sun-shaft projection: clamp the shafts to the floor and sidewall, or soften their edge
  (smoothstep width ~0.05 m).
- **w4 re-measure (still open):** the q18 hood reads L 136 against 193 in y_47305, and the tray reads L 132 against
  195-208 in sanspotter 20, so the seat backs are ~30 % too dark from a seat (econ_w4b.json). The seat materials already
  match the photo albedos (`yShell` #d9dbde, `yTray` #cfd2d6), so the gap is shading/AO.
- **Plastic grain (03_tex.js layer 4, shared):** in harsh light the off-white shells read slightly as stucco. A ~40 %
  lower normal amplitude on layer 4 would fix it, but it affects every area, so I left it to the integrator.
- **w5, done by econ in `04_shaders.js` (one token, please keep):** the main shader's `uniform vec4 u_layer[25]` is now
  `u_layer[${N_LAYERS}]`, because econ added detail layer 25 (`LAYER.yFleck`, the petal-fleck Y fabric) in `03_tex.js`.
  No visual change for other layers.
- **w5 note:** after the r3 AO lift (hemi 0.30) the w2-w4 lighting items above are resolved for economy: the q18 hood
  now reads L 181 vs 192 in y_47305 (econ_w5b). The economy fabrics were re-tuned to the new light, so please ping
  `from_integration.md` if the seat-zone exposure changes again.
- **w6, done by econ in `03_tex.js` (shared, one line per key):** new photo layer 26 `LAYER.yMosaicP` ('y_mosaic',
  `N_LAYERS` 27, `PHOTO_ENC`/`LAYER_PARAMS` 26, `L[26] = L[11]` fallback) - the Y dash-checker mosaic tile replaces the
  procedural layer 11 on the seats. Layer 11 itself is unchanged.
- **w6 to lighting (`04_shaders.js`), low:** the photo fabrics smear into stretched diagonal streaks on ~45 deg faces
  (economy back-top roll, seat-back sides; q17 foreground, econ_w6b issue 10). The triplanar blend `pow(abs(N), 4)` mixes
  two projections ~50/50 there; for photo layers (>= 16) a sharper blend, e.g. `pow(abs(N), vec3(10.0))`, would fix it.
- **w6 to integration (`test/qa.js`), low:** q15_econFronts looks down ~24 deg from 1.62 m, while y_47300 is near level from
  headrest height, so q15 hides the pans, pillows and armrests and over-weights the back tops (econ_w6a / w6b). Suggested
  `walk(0, 1.25, 46.05, Math.PI, -0.12)`. q17_econBacks does not match the y_47303 viewpoint either (y_47303 is a side view
  of the window block from the aisle at ~1.6 m looking left / down).
- **w6 to lighting, low:** from the seat the hood still reads a little dark: q18 L 174 vs y_47305 192 / sans 15 ~230.
- **w10 to lighting, HIGH (regression from 282136c / 9f2d20e):** the lighting snapshot commits darkened the whole economy
  block. Same econ code (e735ea3) rendered before and after them, same crops: q15 fabric L50 55 -> 35 and 45 -> 28
  (y_47300 46-99), q18 seated-view hood L50 166 -> 114 (y_47305 178-198). q17's view of the backs and the studio renders
  are unchanged, so it is the in-cabin occlusion / non-up-facing weighting or the crevice term in `04_shaders.js`, hitting
  the dense 3-4-3 seat block (econ_w10b issue 1). Please fix in the lighting code; econ will not re-tune SEATMAT to it.
- **w14 (wave 3c) to lighting, medium:** at row distance the darkest tones of the economy block are lifted ~50 %
  (q15 rows 2-4 L p5/p10 58/61 against 38/44 in y_47300; econ_gap14 notForEcon). The gaps between rows and under the
  headrests need more AO / contact shadow. Econ will not darken the fabrics to compensate.
- **w14 to lighting, low:** the slate headrest covers have no grazing sheen: q16 near cover p90/p50 1.57 against 2.55 on
  the y_47301 near cover. A sheen lobe for `LAYER.leather` at low roughness would give the silver-grey edge in
  y_47301 / 47303. Econ set `yCover` to r 0.5.
- **w14 to integration (`test/qa.js`), still open:** q15 / q17 / q18 do not match y_47300 / y_47303 / y_47305 (see w6),
  so the pans, pillows and the new J arm beam are never compared in-cabin.
- **w17 to lighting (`04_shaders.js`), medium:** the Y tick stitch columns (~1.25 cm pitch) wash out under minification
  at row distance (q15 column CV 0.06-0.08 vs 0.24 in y_47300) even with the column profile doubled in the tile. A mip
  bias of about -0.5 to -1 (or anisotropic filtering) on the photo fabric layers 16 / 24 / 25 / 26 would keep them, and
  would also stop the smear on the seat side panels at grazing angles (w17 A + B). The q16 near seat is also ~2x too
  light (L50 87 vs 40 in y_47301; the same fabric measures right in q15), so it is exposure, not the material.
- **w19 (wave 3d) to integration (`test/qa.js`), medium, largest single lever left for economy (econ_gap19 notForEcon):**
  q15 does not frame y_47300. A camera that matches it almost exactly: door-4 cross aisle (0, 1.62, 44.45), pitch -0.20,
  near clip 1.45 m to cut the galley (fine-tune z ~44.85, clip ~1.1, pitch ~-0.16); the gap analyst's `M4.perspective`
  override leaked into the next view, so restore it or add an app-level near-plane override. In the matched view the
  back colours already match (tick #4b5b89 vs #4b5d8d, fleck #2e3a61 vs #2d3c67). q16 / q17 are still mismatched too.
- **w19 to lighting (`04_shaders.js`), low:** texture LOD bias ~-0.75 on photo fabric layers 16 / 24 / 25 / 26 (row-distance
  contrast); a sheen lobe for the leatherette cover (studio e4 L18 vs 34-52 in y_47306); in the matched view the darkest
  fabric tones are lifted (tick back p10 28 vs 12-19 L*), partly row-to-row occlusion.
- **w23 (wave 3d) to lighting, medium:** the -0.5 photo mip bias (thanks) made the Y tick speckle at row distance
  (q15 bright 0.12-0.14 vs 0.083 in y_47300; q16 row 2 0.19 vs 0.064). Econ compensated in the tile. If you can, exempt
  layer 16 (y_tick) from the bias; the fleck / mosaic layers are fine with it. The cover sheen lobe (w19 item) is still the
  largest open econ material item: covers read L34-38 at grazing angles vs 86-134 in y_47306.

## w27 (wave 3e) to lighting / integration
- **Cover sheen (carried from w19):** still both raters' top unscored item (e4 cover L34 against 83-124 in y_47306).
- **Far-row snow in q16 (w26b-3 / w27b-3):** rows 3+ read p90/50 2.2 and bright 0.28-0.31 against 1.61 / 0.13 in
  y_47301. Fade the -0.5 photo mip bias and the tile contrast with distance in `04_shaders.js` (~l.192).
- **`photoBase` and layer gain:** `photoBase` lifts a colour for a full-gain tile (mean 2c = 2/ENC). A layer with
  PHOTO_GAIN g < 1 then renders 1/(1-g+2g/ENC) x 2/ENC too light (1.8x at 0.45). Econ layer 34 compensates in its
  colour. A gain argument on `photoBase` would make this automatic for every lower-gain photo layer.
- **Per-view FOV in `test/qa.js`:** see questions_econ 22.

## w31 (wave 3f) to lighting / integration
- **Cover sheen lobe:** still the top unscored item in w29 / w30 (A and B both: q16 near cover L54 against 108 in
  y_47301, e4 L34-40 against 83-131 in y_47306). Thanks for queuing it for round 3.
- **Tick (layer 16) mip bias -0.25:** the tick tile is exempt from the -0.5 photo bias, and its stitch-column contrast
  fades at row distance. A w30 tile that reached the q15 contrast (back p90/p10 3.1-3.5 against y_47300 3.2-3.5) went
  near-black close up (e4 p10 20 against 42 in y_47306), so it can't be fixed in the tile alone. w31 sits between the two
  (column profile 0.5, luminance-only deepening). A -0.25 bias on layer 16 alone would close the remaining distance gap
  (rater B, w29b-2).
- **Far-row snow / triplanar smear (w29a-L2, w30b-10):** carried. The new light headrest pad on tick backs (y_47300
  seat D) also smears on the nearest q16 back tops.
- **SHEEN flag on yCover (econ, f75ed94+):** the r3 snapshot (00948cd) had the lobe in `04_shaders.js` but no material
  carried the flag, so econ set `yCover.l = LAYER.none + SHEEN` (09_seats.js, its own SEATMAT line). At `sheen` 0.84, the
  q16 cover pixels go from L55 to L81 (y_47301 67-108). q15 head-on and e4 (~25 deg off-normal) are unchanged. If lighting
  also sets this line, keep one copy.

## w34 / w35 (wave 3g) to lighting
- **Dark gaps between mid and far rows (w34a-4, w33a-7):** in q15, 2.7 % of the pixels above the hero row are below L50,
  against 12.5 % in y_47300. Up to 9.5 m these rows are the full-detail seats, and the under-pan zone is now near-black
  geometry (#2c2f35 tray, dark beams, 8ee9c1c), so the remaining gap is the AO / shadow between seat rows (pans and
  legroom under the backs in front). Please check the AO volume's occlusion strength at seat-pan height in the economy
  zone.
- **Seat-level lift (w34a / w34b, both raters):** foreground pans L97-108 against L78-93 in y_47300 (15-25 % light).
  Carried from w31b-8 / w32b-6.
- **Far-row snow:** carried (see w31).

## w36 (wave 3g, final) to lighting / integration
- **Mid-row snow (medium, both raters, four rounds):** the q15 / q16 mid rows (3-8 rows back) are inside the 9.5 m seat
  LOD switch (`updateSeatLOD`, `12_scene.js` near 9.5), so they render the photo tiles, which alias to white snow (q15
  band L98 vs 92, p90/p10 3.5 vs 5.9, B/R 1.33 vs 1.48). Econ's far LOD now carries flat per-fabric mean colours
  (`econFarMat`, eb4c09f). Either fade the photo-layer albedo contrast with distance (~4-8 m), or give econ groups a nearer
  switch (`nearK` ~0.5, ~5 m). Integration's call; econ's far geometry is ready for either.
- **Cover off-axis:** q17 covers #313e73 vs y_47303 #808fb2 (rater A w36a-2); the SHEEN lobe could be stronger at grazing.
