# >>> NOTE TO ALL AREAS (wave 3, 2026-10-24 16:00 UTC) - lighting is mid-iteration <<<

The lighting loop's round-1 fixer is still editing `04_shaders.js` / `12_scene.js`. Commits 282136c and 9f2d20e are
snapshots of its unfinished work. They raise the exposure (boarding 1.38, cruise 1.12) and add a crevice term
(`amb *= mix(0.4, 1.0, smoothstep(0.06, 0.5, ao))`) plus a lower AO weight on faces that do not look up. Together these
darken the dense economy / PY seat block (from_econ w10, HIGH: q15 fabric L -36 %, q18 hood -31 %).
- **Do not retune your SEATMAT colours or fabric gains to compensate.** The lighting loop will fix the regression in the
  lighting code; from_econ w10 is queued as high for its next round.
- If your rating round falls between now and the next lighting commit, note it in your report and judge geometry and
  materials in the studio renders, which are unaffected.

# >>> CORRECTION FOR ROOM (wave 2) - READ FIRST <<<

**Restore the boarding bundle that e45db15 removed.** The line "pillows only, no wrapped duvet" in the first wave-2 brief was an
integrator default. It was never the user's decision, and it was withdrawn in c308f51. The user asked for judgement calls,
and the rule is that real in-flight photos win. tpg_31 and tpg_42 show the folded duvet and pad in clear plastic under
the pillows at boarding, so keep `roomBundle` (5a42e29) in the boarding (non-bed) state. The current `WORKER_BRIEF.md`
says the same.

# Items from lighting + integration

## To suite (replies to `questions_suite.md`)

1. **Centre-suite width: keep 1.10 m.**
   - 14 CFR 25.815 requires passenger aisles of at least 20 in (0.508 m) from 25 in above the floor, on aircraft with 20 or more passenger seats. [V]
   - The suite walls stand 1.30 m tall, so the whole aisle height counts.
   - Widening the centre suites to 1.20 m would leave 0.46 m aisles, which the rule does not allow. [D]
   - Keep the pill-mirror pier as the slim strip, or shift its visible face inboard within the 1.10 m.
2. **Divider toggle.** Yes, please keep `suiteUnit({divider: 1})` for the raised panel. The integrator will add a raise/lower control to the seat card in `13_app.js`. Default stays lowered.
3. **Closed doors.** Please add a `doors` option to `suiteUnit`, with 0 = parked open (default) and 1 = closed leaf positions. Keep it geometry-only, so the integrator can wire an open/close control on the seat card in `13_app.js`.

## To lighting (the integrator's own fixer)

- **Blue sidewall band, depending on mood.**
  - `boarding` is the default mood and should match ANA's official photos (c_27312, y_47300, py_37302), which show white sidewalls and window belt with no blue band. [V]
  - In-flight trip photos show the saturated blue band. These are `cruise` and night scenes, so the band belongs to `cruise` and `sleep`. [V]
  - Keep `boarding` `sideLed` near-white.
- **Sun patches on beds and seats.** q04 shows hard white ovals from the window sun on the Suite bed. Soften their edges and cap the intensity so the fabric keeps its texture. Seen in the q04 before/after renders.

## To room (wave 2)

- The wave-1 room session (5a42e29) recorded evidence-based decisions in `questions_room.md`, including the wrapped duvet and pad bundle at boarding from tpg_31/42. Keep them. They supersede the "no wrapped duvet" line in the first version of the wave-2 brief, which is now corrected.

## To suite and room (seat-card toggles are wired: f2bfdf2)

- `13_app.js` now builds `seatVariantGeo(meshKey, {bed, doors, divider})` (`09_seats.js`) for the occupied unit.
  - Room `doors` works already (65166ef).
  - Suite `divider` works. When raised, the neighbouring centre suite is redrawn too.
  - Suite `doors`: the "Close door" button is already there. Implement `suiteUnit({doors: 1})` and it takes effect with no other change.
  - Combinations the viewer can reach: `bed` + `doors`, and `divider` with either (centre suites). Please make sure they combine cleanly.
- The prebuilt `bed_*` meshes are gone. Bed geometry now comes from the same variant path (`{bed: true}`), so render your bed mode via `seatVariantGeo` or the `UNITS` entries.

# Items from the lighting fixer (QA r1, light group)

The r1 light changes (04_shaders.js / 12_scene.js) are: boarding exposure 1.38 / cruise 1.12 with a black-only toe, a
crevice term limited to low pockets (below ~0.75 m, not up-facing, not the sidewall), the lens band / bin shade only in
the seat zones (none over doors, galleys, lavs), cove-LED specular line lights, a superellipse sun gate per pane, a sun
soft-clip on pale faces, warm-dim amber phase at seat level, a neutral night. Re-check your area in the renders after
this commit, but judge material albedos in the studio first.

## To room (`09_seats.js` SEATMAT, shared one-line keys)
- **Charcoal shells read flat matte; no sheen line on the cap rims** (lighting r1 medium). Evidence: c_27312 bright sheen
  lines along the rounded charcoal cap rims and monitor-shell edges (shell back #5c626a, dark side #4e4f55); tlfl_IMG_9217
  specular streaks on the cap rails; q06 shell_top_L (150-180, 330-345) #626874, cap #474c56 with no highlight.
  The cove LED line lights are now in the interior specular (mainFS `coveSpec`), but at r 0.45-0.46 the lobe is broad.
  **Fix:** `jShell` r 0.46 -> 0.34 and `jCap` r 0.45 -> 0.34 (satin). Target: shell top edges about 1.3x the face.

## To suite (`09_seats.js` SEATMAT / `09d_suite.js`)
- **`fShell` r 0.45 -> 0.34** for the same sheen lines (lighting r1 medium; omaat_f2 / f5 shell rims).
- **Bed sheet / duvet too bright under cabin light** (lighting r1 low). q04 bed shade (520-560, 320-360) #e0dfdd L224,
  sun patch L246; omaat_f59 (real THE Suite bed) #d8bfa2 L194. The shader now soft-clips the sun on pale faces, but at L224
  without sun the ACES shoulder leaves no room for a patch. **Fix:** sheet albedo about #d4cfc6 (renders ~L200-205),
  duvet a step darker; the patch then reads as soft light, not clipped white.

## To econ (`09_seats.js` SEATMAT)
- **`yShell` r 0.42 -> 0.34** (satin white shells and armrests; lighting r1 medium). Evidence: y_47303 armrest tops p50
  189-194, p99 248-251 (glossy streaks); y_47300 satin armrests. The cove specular needs the narrower lobe to show.
- **yCover (headrest flap) lighter** (integration r1 medium). Evidence: y_47301 flaps (460-580, 400-520) #3a3e5d L63,
  y_47300 #393e5b L63, y_47306 flap face #445072 L80 vs q16 flaps #232a48 L42 (rated on `#343a52`; econ w7 has since set
  `#474c5e`). **Fix:** re-measure q16 flaps after this lighting commit; target face about #3a4060 (L60-65), still darker
  than the Y fabric mean. Note from_econ w10 (the economy darkening from the snapshot commits) is addressed in the
  lighting code (low-face-only AO weight / crevice), so do not retune the fabrics to the snapshot renders.

## To ceiling/bins (`08_bins.js`)
- **Z-fight dashes on the lower lip of an outboard bin near door 3** (integration r1 low). Evidence:
  scratchpad/integ/shots3/w04_d3_cross.png (bin right, y ~185 px), crops w04_bin.png / z04_psu.png: irregular dark dashes
  along ~0.6 m of the lip, flicker while walking; c_27312 / y_47300 lips are clean. **Fix:** find the strip whose end
  coincides with the door-3 zone boundary (seamR / band / lens on the outboard module ending at z ~32.0-33.3) and offset it
  1.5 mm off the body along the face normal, or shorten it 2 cm at the zone end; re-render z04 at DPR 2.

## To exterior (`11_exterior.js`)
- **Sun-side cowl still near white in day look-outs (from_exterior 10, medium) - lighting can not take it further.**
  Evidence: x11K look-out (scratchpad render, day, extSun 0.6): cowl sun side (380-460, 330-450) #d8dde0 L220, shaded side
  #84898e; alv_ANA77W_NH211_26K cowl #9fabb7-#a9c0ce. The same exterior sun renders the wing #b6bcc2 against the photos'
  #c0ccd4, so a lower extSun (0.3 would put the cowl near L196) takes the wing to ~L115. **Fix in the cowl material:**
  albedo about #8c9298 (from #a6a9ad) and/or a rougher cowl (less sun sheen), so the sun side lands near #a9c0ce while the
  wing keeps its level. FYI, done in lighting r1: sunset skyTop [0.28, 0.34, 0.60] / extSun 0.25 (26K wing grey-blue,
  was royal blue), the beacon only on down-facing faces (canoe flanks dark), sunset deck blue (haze / cloudLit).

# Items from the lighting fixer (QA r2, light group; 2026-10-24)

The r2 light changes (04_shaders.js / 12_scene.js / 13_app.js) are: amber moods with the small-e fill lift cut to 0.35
(PSU band / bin doors no longer glow tan), a saturated amber vault, a pale-yellow lens core and brighter seat level; IFE
screen spill light in Night / Blue / Dining; a new **Blue** mood (ANA's full-blue phase); a floor / underside pocket term
(contact shadows under the seats); the AO floor above 1.8 m only in the seat zones (galley upper banks); a closed shade
keeps the band light of the wall; photo tiles sampled at mip bias -0.5; the look-out eye at the glass. Re-check your area
after this commit; judge albedos in the studio first.

## To shell (`src/07_shell.js`) + shared `src/03_tex.js` / `test/make_swatches.py`
- **THE Room carpet has no visible texture** (lighting r2 medium). `carpetJ` uses the procedural fabric layer 1, which
  averages out at aisle distance, so the aisle reads as flat brown paint. Evidence: q06 aisle (500-580, 420-560) #443834,
  high-pass std (luminance minus a 9x9 blur) 0.6; c_27312 aisle (470-550, 420-560) #3a3131, high-pass std 10.6, fine dark
  heather with light flecks, slightly more mauve (h352 vs h14). **Fix:** `test/make_swatches.py`: cut a `j_carpet` tile
  from ref/ana c_27312 (aisle, about 470-550 x 420-560, flattened and tileable; a closer crop from c_27315 / c_27316 if it
  tiles better); `03_tex.js` (shared, one line per key): new photo layer `jCarpet` (PHOTO_LAYERS, PHOTO_GAIN ~1.0,
  LAYER_PARAMS scale ~3/m); `07_shell.js`: `carpetJ: { c: '#3d3335', l: LAYER.jCarpet }`. Target: q06 aisle mean about
  #3d3435 with high-pass std 8-11.

## To room (`src/09c_room.js`, or shared `03_tex.js` LAYER_PARAMS 2)
- **THE Room padded header band reads as hammered metal** (integration r2 medium). `SEATMAT.jBand` (LAYER.leather) shows
  deep ~4 mm worley dimples at seat-eye distance. Evidence: cruise_seat5K (`__sit('12H', Math.PI*0.5+0.6, -0.15)`, cruise)
  band (100-400, 260-420) high-pass(sigma 6) std / mean 0.156, facets L60-130; the c_27315 header band behind the headrest
  is smooth with soft gradients; tlfl_IMG_9397 (THE Room console at ~0.4 m) 0.013-0.035. **Fix:** 09c_room.js l.22
  `jBand: { c: '#656b73', r: 0.45, l: LAYER.plastic }` (satin, as jShell); or, shared, `LAYER_PARAMS[2]` [9, 0.32, 0.14,
  0.3] -> [9, 0.12, 0.08, 0.3] (also tames jHead / fFlap / fLeather / yCover close-ups, the econ "stucco" note). Target:
  band local contrast <= 0.04 at the cruise_seat5K camera.
- **FYI:** the seat mood strips now take their colour in `12_scene.js` (`'#ffc860'`, the warm-yellow LED of
  ucr_room-night-lighting #ffee94 / #fde98c instead of cream #eee3c2); `SEATMAT.moodGlow` is no longer read by any mesh,
  so you may delete it or leave it.

## To suite (`src/09d_suite.js`)
- **The bed sheet still clips in bed mode** (integration r2 medium; repeat of the r1 note). The pad cushion and the
  turned-down bare-sheet corner are still `'#f0efea'` and the duvet `'#d2cec6'`. Evidence: q04 sheet in shade (440-520,
  320-380) #e1e1de L225, sun patch (600-650, 240-280) #f4f3f1 L243, 15.1 % of the frame > 235; f_17304 bed #bbbbbc L187,
  4.3 % > 235; omaat_f59 (real THE Suite bed) #e2c9ab L204. **Fix:** bed branch, pad cushion (l.297) and bare-sheet corner
  (l.308) `'#f0efea'` -> `'#d6d2ca'`; duvet `duv` (l.303) `'#d2cec6'` -> `'#c4c0b8'`; leave the folded flap `'#b9b5ad'`.
  Targets: q04 sheet shade L200-205, sun patch <= L232, frame > 235 under 6 %.
- **No dark pocket under the ottoman in the seated view** (integration r2 low). The ottoman base is a near-flush vertical
  face, so there is no recess for the crevice / pocket terms to darken. Evidence: q03 ottoman top (380-600, 420-480) L137,
  below (400-600, 545-572) #413c3a L61, ratio 0.45; omaat_f11 (same seated view): top (420-840, 620-720) L114, recess under
  the plinth (400-840, 800-880) #1c1610 L23, ratio 0.20, a thin grey plinth at y 750-775. **Fix:** seat-mode ottoman:
  shrink the base box under the cushion to a 0.03 m plinth and set the support back >= 0.12 m from the cushion front, so a
  recess opens at floor level. The r2 floor / underside pocket term then darkens it. Target: q03 under / top ~0.25.

## To monuments (`src/10_mono.js`)
- **F front loose drapes from door 1 turned cool light grey** (integration r2 low). Evidence: q01 L5 curtain (400-470,
  100-500) #515053 L81 h240 (the L4 render was warm dark brown); omaat_f40 drapes (20-140, 150-600) #433f3c L63 and
  (640-740, 160-320) #423c3a L61, warm h ~25; curtainFF's own comment cites omaatF_40 #4c4644 / #423c3b. **Fix:**
  `curtainFF: { c: '#6d6b6b' }` -> `'#5f5650'` (warm grey, same r / layer). Target: q01 curtain about #4a4440 (L65-72,
  h15-30).
- **FYI (from_monuments w9b / w13-15):** the white band over the galley upper compartments came from the lighting AO floor
  (`ao >= 0.85` from 1.8 to 2.0 m), which now acts only in the seat zones; re-check m01 / m09 / m12 / q19.

## To ceiling/bins (`src/08_bins.js`)
- **Z-fight dashes on the lower lip of the right outboard bin at door 3, unchanged since r1** (integration r2 low).
  Evidence: scratchpad/ir2/out7/w04_d3_cross.png (DPR 2, `__app.setView([2.3,1.62,32.7], Math.PI/2, -0.10)`): irregular
  dark streaks at (1330-1600, 365-385) px, same place and shape as r1 (shots3/w04_d3_cross.png); c_27312 / y_47300 lips
  are clean. **Fix:** find the coplanar strip (seam / band / lens) of the outboard module that ends at the door-3 zone
  boundary (z ~32.1); offset it 1.5 mm along the face normal or end it 0.02 m short of the zone end. Re-render w04 / z04
  at DPR 2.
- **Bin lens size (lighting r2 medium, your call):** the lens is now lit with a pale-yellow core in the amber moods
  (`u_lensCore`), but the 0.045 x 0.006 m box is ~1 px at 930 px. Evidence: q21 lens row y 279-281 peak #fbbd61 L196 vs
  L175-180 above / below; the photos' brightest pixels are on the lens (ucr #fefed6, ff_door-gap #fefeb6). Suggested:
  0.06 x 0.008 m.
- **Reply to from_ceiling w13 (bins clip near-white at QA framing):** the outboard / centre bin doors are lifted by their
  own small emission (`BINMAT.doorC` eFn 0.14-0.20, `band` 0.16) through mainFS's fill lift (`base * e * 3`, i.e. +42-60 %
  of the albedo in the white moods), on top of the cabin light. Lowering that eFn is the lever if the seam cores are lost.

- **Reply to from_ceiling w13 (door domes do not follow their baked tone):** layer-12 emission is `u_vault` / `u_led` x e x 6
  and ignores the vertex colour by design (the bake only scales the 0.3 diffuse share), so the crown follows its `eFn`
  (0.06 at the crown, 0.20 at the wall), not the x0.64 bake. Since r2 the lighting AO floor (>= 0.85 from 1.8 m) no
  longer lifts the door zones, which takes some light off the dome. The lever left is the dome `eFn` at the crown
  (e.g. 0.06 -> 0.03-0.04) in `07b_ceiling.js`.

## To shell (`src/07_shell.js`), FYI (replies to from_shell)
- **w10a closed blackout:** done in lighting (a shade row in the window LUT; nearPane only as far as the shade lets the
  window light in): sJ (`__app.setView([-1.3,1.6,26.0], Math.PI/2-0.25, -0.1)`, blackouts) shade 0.56 -> 0.59-0.78 of the
  pier. **w10b / w12 tub crown:** done (the crown 0.32-0.62 m above the pane centre takes the window light): oY crown
  0.69 -> 0.86 of the pier, darkest just above the opening at 0.71. **Reveal test:** only faces recessed behind the lining
  circle (R 2.935, yc 0.92) count as reveal now; if you move the lining off that circle, tell lighting.
- **w12 / w15 creams neutral, w15 door glass, w15 dado grille:** not changed this round (see fixed_integration.md).

## To all areas, FYI: new mood `blue`
- 'Blue' is ANA's full-blue phase (sany_47, ml_DSC_1945): saturated blue cove / lens, dark blue-violet crown, lavender
  seat level, warm galley ends, screens lighting their surround. Rate your area in it only if a reference photo shows it.

## To exterior (`review/qa/exterior_views.js`, FYI)
- **from_exterior 15 done in `13_app.js` lookOut:** the eye is now at `side * 2.72`, y 1.10, pitch 0.06 rad lower, for
  every look-out. Drop the `[-0.06, 0.12, -0.06]` offsets on w26K / w30K, or they apply twice.
- **from_exterior 14 / 16:** the exterior sky reflection now scales with the baked albedo (luminance / 0.39, clamped
  0.5-1, metals exempt), so your near-to-far ramp also ramps the grazing reflection.

# Items from the lighting fixer (QA r3, light group; 2026-10-25)

The r3 light changes (`04_shaders.js` / `12_scene.js`) are:
- AO: the volume sweeps 16 azimuths read bilinearly (was 8: 4 axis + 4 diagonal), still at one cell per layer, with two
  extra floor blur passes. The carpet reads a 4-tap mean, so the periodic diagonal wedges across the THE Room aisle are
  gone.
- Floor: a 3 cm contact map (thin dark line where seats, shells, monuments and the wall meet the carpet). The floor pocket
  term now acts only under seat pans (floor 0.5), so the Y / PY legroom is no longer crushed.
- Amber moods: seat level darker and amber, a vault floor, bin undersides lifted.
- Night: the vault / cove wash is capped, and the screen spill stops at 1.5 m.
- Boarding: a cooler, brighter lens wash.
- Sun patches: a softer pane gate and wider PCF, cap 1.5.
- Photo tiles: the far-row contrast fades with distance.
- New material flag `SHEEN` (04_shaders.js): add it to a layer (`l: LAYER.none + SHEEN`) for a grazing sheen lobe on satin
  leatherette (`LIGHT_TUNE.sheen` 1.35).

Re-check your area after this commit; judge albedos in the studio first.

## To ceiling/bins (`src/08_bins.js`)
- **Sky shows through a hairline between the outboard-bin lens and the sidewall lining** (lighting r3 medium; lighting cannot
  fix it). A continuous 1-2 px line runs along the lens / wall junction for the whole cabin: sky-blue under the day sky,
  navy under the night sky (the background). It flickers while walking and is worst in the dim warm moods. Evidence:
  scratchpad lq3/dd_tr.png (crop of d_room_dining, `__sit('12H',0.25,-0.05)`, dining, shades closed): 1863 px of
  #5e9ccc-#73a4c7 along the junction; lq3/ddn_tr.png (night sky): no blue, the line turns navy. Real photos show a
  continuous lens on the wall (ucr_the-room-cabin, ff_door-gap #ffa43d lens directly on the wall). **Fix:** l.260
  `gBox(0.045, 0.006, L)` at `(2.80 * side, 1.607)` -> `gBox(0.07, 0.006, L)` at `x 2.81 * side`, so its outer edge laps
  1-2 cm behind the lining (or shell extends the lining 2 cm up behind the lens). Check: seated in 12H, day and night skies,
  zero sky pixels along the junction.
- **Aisle vault darker than the bin doors in the white moods** (integration r3 medium). Lighting moved the bin AO floor
  0.85 -> 0.72 (04_shaders.js), but at q06 / q16 the bin faces are not AO-limited (q06 bins L221-223 before and after), so
  their brightness is the door fill lift. Evidence: q06 vault mid (480-515, 20-60) L194 and centre-bin side L181 vs bin
  faces L219-239; q16 vault L191 vs bins L219-229. In the photos the vault is the brighter one: c_27312 aisle ceiling
  (600-660, 5-40) L236, bins L190-210; y_47301 ceiling L225-241 vs bins L190-195; sany_10 vault L206-217 vs centre bin face
  L173. Vault / bin ratio is 1.15-1.37 in the photos and 0.83-0.87 in the model; bin high-pass std 0.2-1.3 vs 16-38.
  **Fix:** `07b_ceiling.js` seat-zone vault eFn `ax < 0.73 ? 0.08 : 0.02 + 0.03*exp(-max(xg-ax,0)/0.18)` ->
  `ax < 0.73 ? 0.14 : 0.10 + 0.10*exp(-max(xg-ax,0)/0.35)`; `08_bins.js` `doorC` eFn 0.14-0.20 -> 0.07-0.12. Targets:
  q06 / q16 vault mid L215-228; outboard bin faces L200-210 with high-pass std >= 8; q15 bins no lower than L205
  (y_47300 L217).
- **Door-3 bin-lip z-fight, third round** (integration r3 low). The dashes are still on the lower lip of the right outboard
  bin. Evidence: scratchpad integ3/r2/z04_binlip.png (`__app.setView([2.3, 1.62, 32.7], Math.PI/2-0.45, 0.25)`) and
  integ3/z04_lip.png: irregular grey / white dashes along ~0.5 m of the lip at y 370-385 px. **Fix:** offset the seam /
  band / lens strip of the outboard module that ends at the door-3 zone boundary (z ~32.0-33.3) by 1.5 mm along the face
  normal, or end it 2 cm short. Re-render z04 at DPR 2.
- **Night, FYI:** the trough grille bars (`07b_ceiling.js` `CEILMAT.troughRim`, e 0.2) take the lamp branch, so they stay
  white at night while the cove behind them is dark (q20 grille edges ~L250; ucr_room-night-lighting ceiling L13-55). At
  e 0.19 they would follow the cabin light like the other fill-lifted parts.

## To room (`src/09_seats.js` SEATMAT, shared one-line keys)
- **THE Room charcoal shells read slate / blue-grey, 1.3-1.6x too light against the ash** (lighting r3 medium +
  integration r3 medium; the two raters asked for darker and for more neutral, this value meets both). Evidence:
  - q06 shell side faces (0-120, 380-560) #545e69 L93 s0.20 and (668-678, 380-560) #3e424a; cap tops (690-850, 340-350)
    #7b808a L128. Lighting r3 leaves these unchanged.
  - c_27312 shell sides #26272c-#3c3d4b L39-62 and caps #61697f-#6b7b95 L105-121; omaatJ_oj_r31 / r37 shells #41423c /
    #3a3731 (L55-65).
  - kn_room_1 shell back #454546 (s0.02); kn_cabin8 header #4a4c4d (s0.05) vs q09 #4e5460 (s0.19).
  - Ash-to-shell ratio: 2.2-3.0 in the photos, 1.3-1.6 in the model.
  - `jShell` '#595d64' / `jCap` '#5c6066' are themselves blue (s ~0.11), and the boarding light is cool-neutral (c_27312
    walls), so they render s0.13-0.20.
  **Fix:** `jShell` c '#595d64' -> '#4b4c4f', `jCap` '#5c6066' -> '#505154', `jShellIn` '#4a4d53' -> '#434446' (keep r 0.34 /
  0.5). Targets: q06 vertical shell faces L55-75 at s <= 0.08, cap tops L105-120 with the rim sheen line still visible,
  aisle ash L150-175 unchanged.

## To econ (`src/09_seats.js` SEATMAT), FYI
- **Cover sheen:** the lobe gain is `LIGHT_TUNE.sheen` 1.35 (was 0.84 when you took the flag in befdc88).
  - q17 flaps (655-700, 175-235) / (860-910, 140-200): #737c9c L125 / #6e799a L122, s0.26-0.28. Before the flag they were
    L81 / L77. y_47303 reads #69779d L119 / #879cc6 L155; the integration target is L130-150.
  - q16 covers (190-260, 240-300) / (40-130, 350-440): L108-112, at the top of y_47301's L67-108.
  - q15 head-on covers are unchanged (L61-83).
  - If q16 now reads over y_47301, say so in from_econ. Lighting will not retune the gain again without a rating.
- **w34 row gaps / seat-level lift:** your w34 rating (8ee9c1c) had the r3 snapshot's AO at 63 deg (`slope` 0.5), which
  opened the row gaps. The final AO is back at 45 deg (16 azimuths). q15 foreground pans are back from L75 to L68
  (box 150-800 x 500-575). The frame's < 30 share is 8.6 % against 10.0 % in y_47300, with p5 22 in both. Please re-rate
  the row gaps on this commit.
- **Armrest gloss** (lighting r3 low): with `arm` r 0.30 / `armPad` r 0.38 tried in a scratch build, plus the cove line
  lights at 1.3, q15 armrest p99 moved only 225 -> 229 (y_47300 254). The photo's glossy streaks reflect the lit aisle
  vault, a broad area light the env model does not hold. No SEATMAT change is asked for.

## To shell (`src/07_shell.js`) + shared `src/03_tex.js` / `test/make_swatches.py`
- **THE Room carpet texture, third request** (lighting r3 low + integration r3 medium). With the AO wedges gone the aisle
  is now even (q06 aisle (500-590, 370-560) #433936 L60, p10 51, 1 % < 30) but flat: high-pass std 0.5 vs c_27312 11.8
  (fine dark heather with light flecks), omaatJ_oj_r37 4.0. The level is also above the photo (c_27312 aisle mean 53.7), so
  the darker albedo matters. **Fix:** `test/make_swatches.py` cuts a `j_carpet` tile from ref/ana c_27312 (aisle, about
  470-550 x 420-560, flattened, tileable); `03_tex.js` (shared, one line per key) adds a photo layer `jCarpet`
  (PHOTO_GAIN ~1.0, LAYER_PARAMS scale ~3/m); `07_shell.js` l.33 `carpetJ: { c: '#3d3335', l: LAYER.jCarpet }`. Target:
  q06 aisle mean about #3d3435 (L50-55), high-pass std 4-11.

## To suite (`src/09d_suite.js`)
- **Bed sheet still clips, third request** (integration r3 medium). The sun cap is now 1.5 (was 2.0), but the patch cannot
  read as light while the sheet sits at L227 without sun. q04 (this round's lighting): sheet in shade (440-520, 320-380)
  #e3e2e0 L227, sun patch (600-650, 240-280) #f5f4f2 L244, 15.9 % of the frame > 235; f_17304 4.3 % > 235; omaat_f59 real bed
  #ddc5a7 L200. **Fix:** l.297 pad cushion and l.308 bare-sheet corner '#f0efea' -> '#d6d2ca'; l.303 duvet '#d2cec6' ->
  '#c4c0b8'; leave the folded flap '#b9b5ad'. Targets: sheet in shade L200-205, sun patch <= L232, frame > 235 under 6 %.
- **Ottoman recess still shallow** (integration r3 low). q03 ottoman top (380-600, 420-480) L137, below (400-600, 545-572)
  #2c2a29 L43, ratio 0.31; omaat_f11 (same seated view) top L115, recess #1c1610 L24, ratio 0.21. **Fix:** seat-mode
  ottoman base box -> a 0.03 m plinth, support set back >= 0.12 m from the cushion front. Target under / top 0.22-0.25.

## To monuments (`src/10_mono.js`)
- **F front drapes cool light grey, third request** (integration r3 low). q01 curtain (400-470, 100-500) #515053 L81 h267
  vs omaat_f40 drapes (20-140, 150-600) #433f3c L64 h20 (warm; omaat_f2 the same). **Fix:** l.92 `curtainFF` c '#6d6b6b' ->
  '#5f5650' (same r / layer). Target: q01 curtain about #4a4440, L65-72, h15-30.

# lighting run 2, L7 (lighting fixer, 2026-10-25)

Raters L7 (lighting 6.8, integration 6.9) rated c0817a2; this run started on 836b636, which already holds polish B. The light
changes of this run (`04_shaders.js` / `12_scene.js`, logged in fixed_integration.md) - re-check your area on this commit:
- Boarding: cooler shadow light (hemiBot [0.31, 0.35, 0.47], wash [0.23, 0.255, 0.32]); the tub crown takes 1.1 of the day
  window light (was 0.7). Shaded whites move B-R +2..+5 toward the official photos' blue-grey (q17 / q14 L175-195 band +19 -> +22 / +9 -> +14,
  q16 wall +5 -> +10); lit faces and fabric hues hold.
- Boarding / Cruise: the outboard bin doors' lower, inboard-down face takes x0.8 hemi + bounce (`binLo`, crest x1).
- Dining / Sunrise: bins and undersides above 1.6 m in the seat zones get a warm lift (`binLift`); the recessed window tub
  (`MAT.reveal` faces only: not the shades, the tunnel lining or the seals) keeps at least 0.7 of a pier's light where the
  window light is dim (sunset, closed shades; `tubRef`, mood flag `tub`), over the shell's tub bake. Night and Blue keep the
  bake as it was (the floor lit their tubs flat and pale).
- Night: cove lines warm and at half level, vault cap 0.045. Night / Blue: ~70 % of the seat screens off (per-screen hash;
  the screen nearest the eye that faces it stays on), spill only from lit screens.
- Blue: the door / galley / lav zones warm (monFill [0.20, 0.16, 0.10], hemi x0.4 outside the seat zones).
- Look-out view: the interior at x0.14 exposure once the eye is past the lining.
- SHEEN lobe: (1 - N.V)^2 (was ^3), tinted 0.3 toward the fabric hue (yCover).

## To room / econ / py (`src/09_seats.js` SEATMAT, shared one-line keys): thin rim highlights (integration r4 medium)
- **Problem:** the rounded edges of the charcoal shells, caps, cap rails, seat-back shells and armrests carry thin clipped
  highlights in every official photo; in the model they are soft or missing.
- **Evidence:** thin-highlight share (L > 235 with 9 px clip density < 0.45; scratchpad qa/fixL7/tools/thin.py) q06 1.03 %,
  q16 0.64, q13 0.17, q17 0.47, q09 0.42, q15 0.52 against c_27312 2.20, y_47301 2.50, py_37302 1.47, y_47303 1.68,
  c_27314 1.18, y_47300 1.10.
- **Lighting tried and reverted** a gain on the two cove line lights (coveSpec) three ways: x2.5 on rough < 0.5 (q06 thin 1.29 %,
  but the bin crests clipped, +3.5 % px > 235, and the q03 screen glared); x4 below 1.5 m on rough < 0.5 (the PY flaps,
  pyCover r 0.45, went L72-82 -> 90-117 against py_37302 L61-87; d06 median 77 -> 83, q14 140 -> 145); x4 on rough <= 0.36 at
  rounded edges only (no measurable change: q06 0.98 %, q09 0.45, q13 0.14; the normal-mapped jBand sparkled in dd). The
  highlight width is set by the material roughness and the edge radii, not by the light level.
- **Fix (integration's proposal):** `jCap`, `jRail`, the econ `arm`, `pyShell` r 0.34-0.45 -> ~0.24-0.28 (one line each), and
  rounder cap / armrest edges where the geometry is a hard chamfer. Keep the fabrics and covers as they are. Targets: thin
  share >= 1.1 % in q06 / q16 / q17 / q09; face means within 5 L; no sparkle on fabric.

## To ceiling/bins (`src/08_bins.js`), FYI: vault / bin order (integration r4 high, lighting r4 medium)
- This run (`binLo` 0.8, boarding / cruise), box means before -> after (photo): q06 right outboard bins (600-930, 10-110)
  L216 -> 205 (c_27312 196) under a vault at L232 (221); q16 left bins L220 -> 210 (y_47301 209); q15 bins L225 -> 218
  (y_47300 218; p10 202 -> 189 vs 200); c06 cruise right bins L188 -> 176 under a vault at L221.
- Still short: the door faces are smooth (high-pass 1.6-3.4 against 6-21 in the photos), and the q06 bins sit ~10 L over
  c_27312. The lighting factor stops at 0.8 because the raters' 0.72 took the q15 bins to L209, p10 177 (y_47300 is evenly
  lit: L216, p10 200). Levers left are yours: the door albedo `#d6d8dc` -> `#cdd0d4` (integration exp2), or a baked
  crest-to-lip grade on the door face.
- Night grille (integration r4 medium, `07b_ceiling.js` troughRim): done by polish B (e 0.19). q20 grille (515-575, 0-120)
  top-40 L114, max 131 at the start of this run; L83, max 94 (warm #5c5241) with this run's night cove cap (target <= L135).

## To room (`src/09c_room.js`): recessed black toe-kick (integration r4 low)
- **Problem:** the aisle-side kick under the ash panels (roomAisleAsh / monument end, gRBox 0.045 x 0.10 'shell') is flush, even
  2.5 mm proud, and charcoal; the photos show a recessed black toe-kick, the deepest contact line along both aisles.
- **Evidence:** q06 aisle profile (row 500) kick L40-48 next to the carpet at L55-59; c_27312 (row 480) kick L5-7 under each ash
  panel with a thin light lip above; ucr_ana-business-class-aisle.jpg: a black recessed band ~0.08-0.10 m tall under every panel.
- **Fix:** 09c_room.js l.478 (and the matching kicks under roomAisleAsh): set the kick 0.02 m back from the ash face (0.565 ->
  0.545 on that side's normal), height 0.08, material { c: '#1c1d20', r: 0.7 }. The lighting contact map then darkens its foot.
  Target: kick L10-25 in q06.

## To room (`src/09c_room.js`): white hairline in the 11A footwell (integration r4 low)
- **Problem:** seat mode in 11A shows a bright 1-2 px line at the joint between the footwell floor and its right side panel; it
  flickers when the camera moves (a gap to a lit face behind, or an exposed edge).
- **Evidence:** `__sit('11A', Math.PI, -0.75)`: pixels (597-614, 384-462) #f4f5f6 L244 on a footwell at L7-37; c_27316 and
  ff_ana-the-room-business-class-footwell.jpg show dark, unbroken footwell edges (L6).
- **Fix:** in the rear-facing seat's footwell builder, extend the footwell floor 0.01 m under the side panel, or drop the side
  panel 0.005 m into the floor, so the faces overlap. Check at DPR 2 in the same view.

## To monuments (`src/10_mono.js`): THE Suite ink-cloud print reads as smudges (integration r4 low)
- **Problem:** the front-wall print is baked into vertex colours on a 0.1 m grid and renders as blurred grey smudges at seated eye
  level, not as cloud forms.
- **Evidence:** q03 wall std 12.5 -> 26.4 since L5 (overall contrast right: p5-p95 119-198 vs omaat_f13 92-218);
  omaat_f40 / omaat_f13 / f_17306 show crisp scalloped cumulus edges on a pale ground.
- **Fix:** inkWall grid 0.1 -> 0.04 m and a sharper cloud mask (t = smoothstep(0.42, 0.50, n), keeping the core '#6a665f'), or an
  atlas canvas texture with hard scalloped edges. Target: the same p5-p95 range, edge gradients <= 3 cm.

## To ceiling/bins and integration, FYI (integration r4 low): door-3 bin-lip dashes
- Polish B (d2627ff) traced them by colour tests to the J centre PSU housings seen edge-on from the door-3 cross-aisle, not a
  z-fight. Lighting has nothing to add (no MSAA this round). Integration: re-check on that evidence before a fifth hand-off.

## To shell (`src/07_shell.js`), FYI
- Done by polish B and checked on this run's before renders: the THE Room carpet tile (q06 aisle high-pass 5.9 vs c_27312 6.2,
  L56 vs 49) and the sky hairline at the bin / lining junction (dd: 0 sky-blue px in (600-930, 60-210)).
- The tub bake (x0.38-0.55 just above the bezel, `tubShade`) now meets a lighting floor in the amber moods (Dining / Sunrise)
  where the window light is dim (sunset, closed shades): `tubRef` in mainFS, on `MAT.reveal` (no layer, r 0.45) only. With
  the shades open in daylight, and in every white, Night and Blue view, your bake stands unchanged. If you change the reveal's
  roughness or give it a detail layer, tell lighting: the floor keys on them (04_shaders.js tubB).
## To integration (`test/qa.js`), FYI: view order changes the renders
- **Problem:** `applyMood('sleep')` (13_app.js) closes every shade, and qa.js's per-view reset (boarding / day) does not reopen
  them. In a run with q20 ahead of q06, every later view renders with closed shades (q03 / q14 / q17 changed 15-17 % of pixels
  against the same build in the canonical order).
- **Fix:** add `__app.scene.setAllWindows(0)` to the per-view reset in qa.js (as `scratchpad/qa/fixL7/tools/shots.js` does),
  or keep rendering in the canonical order (q20 then q21, which reopens them).

# lighting run 2, L8 (lighting fixer, 2026-10-25)

Raters L8 (lighting 7.3, integration 7.6). The items below are other areas' files; the lighting changes of this run are
logged in fixed_integration.md ("Lighting run 2, L8").

## To econ (`src/09_seats.js` SEATMAT, shared one-line keys): streak highlights on the rounded white plastics (integration L8 low)
- **Owner:** econ (with room / py for their keys). **Severity:** low.
- **Problem:** the rounded white plastics (econ armrests, PY shells) and the THE Room charcoal caps carry no thin streak
  highlights. Lighting tried the cove line lights three ways in L7 (`coveSpec` gains, reverted); the streak width is set by
  the roughness, so this is a SEATMAT hand-off.
- **Evidence:** armrest p99 192-218 against 244-254 in y_47300; thin-highlight share 0.16-0.98 % against 1.10-2.50 % across
  the official photos.
- **Fix:** one line per key: econ `arm` r 0.45 -> 0.26 and `armPad` r 0.50 -> 0.32; room `jCap` r 0.34 -> 0.26 (`jRail` is
  already brushed metal at 0.26); py `pyShell` r 0.42 -> 0.30. Keep the fabrics and covers as they are. Targets: thin share
  >= 1.1 % in q06 / q16 / q15; q15 armrest p99 >= 238; face means within 5 L.

## To room / py / econ (`09c_room.js`, `09b_py.js`, `09a_econ.js` + shared SEATMAT keys): rims that can catch the cove line (integration L8 medium)
- **Owners:** room (`09c_room.js` capRail and shell edges), py (`09b_py.js` shell / arm edges), econ (`09a_econ.js` shell /
  arm rims); shared SEATMAT one-line keys. **Severity:** medium.
- **Problem:** thin specular rim highlights on shells, caps and armrests are still 2-9x too sparse; furniture edges read
  matte and the seats lose their outline. Lighting tried three cove-rim gains and reverted all of them (fixL7). The cap
  rails are a single 6 mm chamfer (`gRBox(..., 0.006, seg 1)`), so their normals never sweep through the reflection of the
  cove line and there is no thin specular line to raise. In the photos every rounded cap, shell rim and armrest carries one.
- **Fix:**
  - `09c_room.js` l.92 capRail: `gRBox(w + 0.006, 0.02, d + 0.006, 0.009, 3)`; the same for the shell top edges (r >= 8 mm,
    seg 3).
  - `09b_py.js` / `09a_econ.js`: the shell and arm top-edge `gRBox` radii >= 8 mm with seg 3.
  - Shared SEATMAT keys, one line each: `jCap` r 0.34 -> 0.24, `pyShell` r 0.42 -> 0.30, `yShell` r 0.42 -> 0.30, `arm` r
    0.45 -> 0.32. Leave the fabrics alone.
  - If that is still short, lighting can re-try its earlier `LIGHT_TUNE.cove` x2.5 gated to rough < 0.35 (bins and
    screens excluded): tell lighting in from_room / from_py / from_econ.
- **Targets:** thin-highlight share >= 1.1 % in q06 / q16 / q17 / q09 and >= 0.8 % in q13; face means within 5 L.

## To monuments (`src/10_mono.js`): THE Suite ink-cloud print (integration L8 medium, raised from low)
- **Owner:** monuments (`10_mono.js` inkWall / `MONMAT.inkCloud`). **Severity:** medium (unchanged for four rounds; it
  fills the top of the hero view from every THE Suite seat: q03, nF03, f_ink_seated).
- **Problem:** the print is baked into vertex colours on a 0.1 m grid with a 0.22-wide ramp, so the clouds render as dark,
  colourless, blurred blobs that read as smoke stains or dirt: 2.5x the photo's contrast, no hue, no edge detail. The real
  wall is a pale warm ground with low-contrast cumulus whose speckled edges are crisp.
- **Fix (`inkWall`):**
  - Grid 0.1 -> 0.03 m: `nx = ceil((x1 - x0) / 0.03)`, `ny = ceil(H / 0.03)`.
  - Cloud mask `t = smoothstep(0.44, 0.52, n + 0.10 * (fbm(x / 0.05, y / 0.05, 256, 2, 29) - 0.5)) * lowY`; the
    high-frequency term gives the speckled edge.
  - `MONMAT.inkCloud` '#6a665f' -> '#b3ad9f', about 30 L under the '#dddbd0' ground (the omaatF_2 p10 #a8a399 already cited
    in the comment).
  - If the vertex budget objects, bake the same field into an atlas canvas panel instead.
- **Targets (f_ink_seated):** print range p5-p95 <= 40, hue h35-45 s0.06-0.14, fine std >= 4; q03 top band range <= 45.

## To room (`src/09c_room.js`): recessed near-black toe-kick (integration L8 low, unchanged)
- **Owner:** room (kick under the aisle ash panels and the monument ends). **Severity:** low.
- **Problem:** the THE Room shell base is a flush navy-grey band, not a recessed near-black toe-kick.
- **Fix:** `09c_room.js` l.480 (`gRBox(0.045, 0.10, ...)` at x 0.565) and the matching kicks under `roomAisleAsh` (l.223,
  the `ashFrameX` family): set the kick 0.02 m back from the ash face (0.565 -> 0.545 along that side's normal), height 0.08,
  material `{ c: '#1c1d20', r: 0.7 }`. The contact map then darkens its foot (and this run's screen-space AO its top edge).
  Target: q06 kick L10-25.

## To room (`src/09c_room.js`): white hairline in the 11A footwell (integration L8 low, unchanged)
- **Owner:** room (rear-facing seat footwell floor / side panel). **Severity:** low.
- **Problem:** a white 1-2 px hairline runs along the 11A footwell floor / side-panel joint.
- **Fix:** in the rear-facing footwell builder, make the faces overlap instead of meeting at an edge: extend the footwell
  floor 0.01 m under the side panel, or sink the side panel 0.005 m into the floor. Re-check the same view at DPR 2: 0 px >
  L120 in that box.

## To ceiling/bins (`src/08_bins.js`): grey fragments on the right outboard bin lip at door 3 (integration L8 low)
- **Owner:** ceiling/bins (door-3 zone end of the outboard run, or the PSU instances there). **Severity:** low.
- **Problem:** irregular grey fragments with PSU-like dots along about 0.5 m of the right outboard bin lip at door 3. Polish B
  attributed them to the centre PSU housings seen edge-on and made no change; they are still visible.
- **Fix:** (1) hide the centre PSU meshes in that view (filter `scene.opaque` by mesh name) to confirm which mesh pokes
  through; (2) then end that PSU / band run 0.05 m before the door-3 zone boundary (`fitModules` z1 - 0.05), or drop it 2 mm
  along its face normal. Re-render z04 at DPR 2.

# lighting run 2, L9 (lighting fixer, 2026-10-25)

Raters L9 (lighting 7.6, integration 7.6). The items below are other areas' files; the lighting changes of this run are
logged in fixed_integration.md ("Lighting run 2, L9").

## To econ (`src/09_seats.js` SEATMAT, shared one-line keys): streak highlights on the rounded white plastics (integration L9 low, carried from L8)
- **Owner:** econ (with room / py for their keys). **Severity:** low.
- **Problem:** the rounded white plastics (econ armrests, PY shells) and the THE Room charcoal caps carry no thin streak
  highlights. This is the L8 SEATMAT hand-off; it has not landed.
- **Evidence:** thin-highlight share q06 0.86 % vs c_27312 2.20 %, q16 0.55 % vs y_47301 2.50 %, q15 0.61 % vs y_47300
  1.10 %, q13 0.16 % vs py_37302 1.47 %, q09 0.39 % vs c_27314 1.18 %.
- **Fix:** one line per key: econ `arm` r 0.45 -> 0.26, `armPad` r 0.50 -> 0.32; room `jCap` r 0.34 -> 0.26; py `pyShell`
  r 0.42 -> 0.30. **Targets:** thin share >= 1.1 % in q06 / q16 / q15; q15 armrest p99 >= 238; face means within 5 L.

## To py (`src/09b_py.js`) and room (`src/09c_room.js`): cm-scale dark gaps at the seat joints (integration L9 medium)
- **Owners:** py (`pySeat` / `pyUnit`); room for the same fix in `09c_room.js`. **Severity:** medium.
- **Problem:** the PY seat (back fabric, bolsters, shell, cushion, console, leg rest) is lofted as one continuous closed
  surface, so it has almost no crevices for the contact AO to find. py_37302 / 37301 show a dark 0.5-1 cm gap or welt at
  cushion / console, cushion front / leg rest, the shell's front rim / back fabric, the console panel splits and the seat
  foot on the carpet; those outline every PY seat. Stronger AO is not the lever: L8's stronger settings crushed q09's darks
  under the photo, and this run's lighting L9 item (a 1.5x disc / range below 0.85 m, off the sidewall) did not close it:
  q13 reads 0.73 % after this run's contact-AO changes (fixed_integration.md, L9).
- **Evidence:** PY outline darks 0.2-0.33x the photos' (thin dark-line share q13 0.91 % vs py_37302 2.77 %, q14 0.58 % vs
  py_37301 3.15 %); THE Room 0.5-0.6x.
- **Fix (`09b_py.js` pySeat), modelled on the econ tuck crease (`09a_econ.js`, the w11 B loft with `{ c: '#283052', r: 0.95 }`):**
  1. After the shell loft (l.50), a dark reveal along each side where the shell's front rim meets the back fabric, e.g.
     `for (const sd of [-1, 1]) loftAt(B, ds.filter(([y]) => y < 0.93).map(([y, d, w]) => SEC(y, 0.008, 0.012, zr(y) - d + 0.012, 0.003, sd * (w / 2 - 0.006))), BH, { c: '#1f2228', r: 0.9 }, 1);`
  2. A 1 cm dark gap strip (`gRBox` 0.012 high, `{ c: '#1c1e23', r: 0.9 }`) along the cushion sides against the console,
     and one at the cushion front / leg-rest hinge.
  3. In `pyUnit`, a 6 mm dark split line on each console face.
  - `09c_room.js`: the same 6 mm dark reveals between the seat cushion / back and the shell, and on the shell panel splits.
- **Targets:** thin dark-line share >= 1.8 % in q13 / q14, >= 3.6 % in q06, >= 2.4 % in q09; q13 frame p5 <= 38; face
  means within 5 L.

## To room / py / econ (`09c_room.js`, `09b_py.js`, `09a_econ.js` + shared SEATMAT keys): rims that can catch the cove line (integration L9 medium, unchanged for three rounds)
- **Owners:** room (`09c_room.js` capRail and shell top edges), py (`09b_py.js` shell / arm edges), econ (`09a_econ.js`
  shell / arm rims); shared SEATMAT one-line keys. **Severity:** medium.
- **Problem:** thin specular rim highlights on shells, caps and armrests are still 2-5x too sparse, so furniture edges read
  matte. The cap rails are a single 6 mm chamfer, so their normals never sweep through the reflection of the cove line and
  no thin highlight can form. In the photos every rounded cap, shell rim and armrest carries one.
- **Fix:**
  1. `09c_room.js` l.92 capRail: `gRBox(w + 0.006, 0.02, d + 0.006, 0.009, 3)`; the shell top edges the same (radius >= 8
     mm, seg 3).
  2. `09b_py.js` / `09a_econ.js`: the shell and arm top-edge `gRBox` radii >= 8 mm with seg 3.
  3. Shared SEATMAT keys, one line each: `jCap` r 0.34 -> 0.24, `pyShell` r 0.42 -> 0.30, `yShell` r 0.42 -> 0.30, `arm` r
     0.45 -> 0.32.
- **Targets:** thin-highlight share >= 1.1 % in q06 / q16 / q17 and >= 0.8 % in q09 / q13; face means within 5 L.

## To monuments (`src/10_mono.js`): THE Suite ink-cloud print (integration L9 medium, unchanged for five rounds)
- **Owner:** monuments (`10_mono.js` inkWall / `MONMAT.inkCloud`). **Severity:** medium. It fills the top of the hero view
  from every THE Suite seat (q03, f_ink_seated).
- **Problem:** the print is baked into vertex colours on a 0.1 m grid with a 0.22-wide ramp, so it renders as dark,
  colourless, blurred blobs (grey smoke stains): 2.6x the photo's contrast, almost no hue, a third of its edge detail. The
  real wall is a pale warm ground with low-contrast cumulus with crisp, speckled edges. (This run's contact-AO change took
  the dark frame round the bulkhead monitor off this wall: f_ink_seated row 320 beside the monitor L68 -> 156; the clouds
  themselves are the print.)
- **Fix (`inkWall`):**
  1. Grid 0.1 -> 0.03 m: `nx = ceil((x1 - x0) / 0.03)`, `ny = ceil(H / 0.03)`.
  2. Cloud mask `t = smoothstep(0.44, 0.52, n + 0.10 * (fbm(x / 0.05, y / 0.05, 256, 2, 29) - 0.5)) * lowY`; the
     high-frequency term gives the speckled edge.
  3. `MONMAT.inkCloud` '#6a665f' -> '#b3ad9f', about 30 L under the '#dddbd0' ground.
  4. If the vertex budget objects, bake the same field into an atlas canvas panel instead.
- **Targets (f_ink_seated):** range p5-p95 <= 40; h35-45, s0.06-0.14; fine std >= 4; q03 top boxes range <= 45.

## To room (`src/09c_room.js`): recessed toe-kick and the 11A footwell hairline (integration L9 low, both unchanged since L7)
- **Owner:** room. **Severity:** low.
- **Problem:** (1) the THE Room shell base is a flush navy-grey band, not a recessed near-black toe-kick (under the aisle
  ash panels and the monument ends); (2) a white hairline runs along the 11A rear-facing footwell floor / side-panel joint.
- **Fix:**
  1. Kick: at `09c_room.js` l.480 (`gRBox(0.045, 0.10, ...)` at x 0.565) and the matching kicks under `roomAisleAsh` (the
     `ashFrameX` family), set the kick 0.02 m back from the ash face (0.565 -> 0.545 along that side's normal), height
     0.08, material `{ c: '#1c1d20', r: 0.7 }`.
  2. Footwell: make the faces overlap instead of meeting at an edge: extend the footwell floor 0.01 m under the side panel,
     or sink the side panel 0.005 m into the floor.
- **Targets:** kick recess L <= 15 with a contact line; 0 px > L120 in the footwell box at DPR 2.

## To ceiling/bins (`src/08_bins.js`): grey fragments on the right outboard bin lip at door 3 (integration L9 low, carried from L7 / L8)
- **Owner:** ceiling/bins (the door-3 end of the outboard run, or the PSU instances there). **Severity:** low.
- **Problem:** irregular grey fragments with PSU-like dots run along about 0.5 m of the right outboard bin lip at door 3.
- **Fix:** (1) hide the centre PSU meshes in that view (filter `scene.opaque` by mesh name) to confirm which mesh shows
  through; (2) then end that PSU / band run 0.05 m before the door-3 zone boundary (`fitModules` z1 - 0.05), or drop it 2 mm
  along its face normal. Re-render z04 at DPR 2.

# lighting run 2, L10 (lighting fixer, 2026-10-25)

Raters L10 (lighting 7.7, integration 7.6). The items below are other areas' files; the lighting changes of this run are
logged in fixed_integration.md ("Lighting run 2, L10"). None of the L8 / L9 hand-offs below has landed: no commit has
touched 09a_econ.js, 09b_py.js, 09c_room.js, 10_mono.js, 07_shell.js or 08_bins.js since L9.

## To py (`src/09b_py.js`): cm-scale dark joints that outline every PY seat (integration L10 medium, carried from L9)
- **Owner:** py (`pySeat` / `pyUnit`). **Severity:** medium.
- **Problem:** this round's in-flight check isolates PY. THE Room and economy now sit inside the in-flight photos' thin
  dark-line range; PY is at 0.4x of it (0.23x of the official photos). The PY back fabric, bolsters, shell, cushion, console
  and leg rest are lofted as one closed surface, so neither the AO nor the photo-matched materials can draw the 0.5-1 cm dark
  joints that outline every PY seat in py_37301 / 37302 and sanpy_11 / 13 / 14: cushion to console, cushion front to leg
  rest, shell front rim to back fabric, console panel splits, seat foot on the carpet. The lighting fixer traced the
  remaining gap to this geometry: the screen-space AO finds no crevice to darken (lighting L9 / L10).
- **Evidence:** thin dark-line share q13 0.73 % vs py_37302 2.77 %, q14 0.67 % vs py_37301 3.15 %; q14 p5 56 vs 31; q13
  mean 137 vs 129.
- **Fix (`09b_py.js` pySeat), modelled on the econ tuck crease (`09a_econ.js` w11 B loft, `{ c: '#283052', r: 0.95 }`):**
  1. After the shell loft (l.50), a dark reveal on each side where the shell's front rim meets the back fabric, e.g.
     `for (const sd of [-1, 1]) loftAt(B, ds.filter(([y]) => y < 0.93).map(([y, d, w]) => SEC(y, 0.008, 0.012, zr(y) - d + 0.012, 0.003, sd * (w / 2 - 0.006))), BH, { c: '#1f2228', r: 0.9 }, 1);`
  2. 1 cm dark gap strips (`gRBox` 0.012 high, `{ c: '#1c1e23', r: 0.9 }`) along the cushion sides against the console,
     and at the cushion front / leg-rest hinge.
  3. In `pyUnit`, a 6 mm dark split line on each console face and a 1 cm dark foot plate under each leg.
- **Targets:** q13 / q14 thin dark-line share >= 1.6 % (>= 1.8 % for the official-photo match); q13 p5 <= 38; face means
  within 5 L.

## To econ / room / py (`src/09_seats.js` SEATMAT, shared one-line keys): streak highlights on rounded plastics (integration L10 low, carried from L8 / L9)
- **Owners:** econ (`arm`, `armPad`), room (`jCap`), py (`pyShell`). **Severity:** low.
- **Problem:** the rounded white plastics (econ armrests, PY shells) and the THE Room charcoal caps still have no thin
  streak highlights; the SEATMAT roughness hand-off from L8 / L9 has not landed.
- **Evidence:** thin-highlight share q06 0.86 % vs c_27312 2.20 %, q16 0.59 % vs y_47301 2.50 %, q15 0.61 % vs y_47300
  1.10 %, q13 0.16 % vs py_37302 1.47 %, q09 0.41 % vs c_27314 1.18 %.
- **Fix:** one line per key: `arm` r 0.45 -> 0.26, `armPad` r 0.50 -> 0.32 (econ); `jCap` r 0.34 -> 0.26 (room); `pyShell`
  r 0.42 -> 0.30 (py). **Targets:** thin-highlight share >= 1.1 % in q06 / q16 / q15; q15 armrest p99 >= 238; face means
  within 5 L.

## To room / py / econ (`09c_room.js`, `09b_py.js`, `09a_econ.js`): rims that can catch the cove line (integration L10 low, downgraded from medium)
- **Owners:** room (`capRail`, shell top edges), py (shell / arm edges), econ (shell / arm rims); shared SEATMAT keys.
  **Severity:** low. The gap is against the official studio photos only: against in-flight photos THE Room, economy and
  THE Suite are inside the range; PY is the only clear miss.
- **Problem:** thin specular rim highlights on caps, shell rims and arms are 2-4x sparser than in the official photos. The
  cap rails are a single 6 mm chamfer, so their normals never sweep through the reflection of the cove line.
- **Fix:** (1) `09c_room.js` l.92 capRail: `gRBox(w + 0.006, 0.02, d + 0.006, 0.009, 3)`; (2) `09b_py.js`: shell and arm
  top-edge `gRBox` radius >= 8 mm, seg 3; (3) one shared SEATMAT key: `pyShell` r 0.42 -> 0.32.
- **Targets:** q13 thin-highlight share >= 0.45 %; q06 / q16 stay within the in-flight range; face means within 5 L.

## To monuments (`src/10_mono.js`): THE Suite ink-cloud print (integration L10 medium, unchanged for six rounds)
- **Owner:** monuments (`inkWall`; `MONMAT.inkCloud` / `inkGround`). **Severity:** medium.
- **Problem:** the print fills the top of the hero view from every THE Suite seat (q03, q05, f_ink_seated) and is the first
  thing seen in the in-service photos omaat_f2 / f40 / f13. It is baked into vertex colours on a 0.1 m grid with a 0.22-wide
  ramp toward #6a665f, so it renders as soft, dark, colourless smudges (grey smoke stains): 2-3x the photos' contrast, a third
  of their saturation and 30-40 L darker on average. The real wall is a pale warm ground with low-contrast cumulus clouds
  with crisp, speckled edges.
- **Fix (`inkWall`):**
  1. Grid 0.1 -> 0.03 m: `nx = ceil((x1 - x0) / 0.03)`, `ny = ceil(H / 0.03)`.
  2. Crisp, speckled edges: `t = smoothstep(0.44, 0.52, n + 0.10 * (fbm(x / 0.05, y / 0.05, 256, 2, 29) - 0.5)) * lowY`.
  3. `MONMAT.inkCloud` '#6a665f' -> '#b3ad9f', about 30 L under the '#dddbd0' ground, with a slight warm hue (s ~0.10).
  4. If the vertex count objects, bake the same field into an atlas canvas panel (like the 'washi' panel in `06_atlas.js`)
     and map it with washiUV.
- **Targets (f_ink_seated):** range <= 40 and mean L >= 185; h35-45, s0.07-0.13; fine >= 2; q03 top boxes range <= 45.

## To shell (`src/07_shell.js`) (+ lighting): day window panes capped below white (integration L10 low)
- **Owners:** shell (07_shell.js l.754, the glass tints); lighting for the alternative in step 2 (12_scene.js SKIES.day
  winExp and the glass blend). **Severity:** low.
- **Problem:** the glass pass multiplies the already display-encoded frame by the pane tint [0.93, 0.95, 0.96]
  (`gl.blendFunc(DST_COLOR, ZERO)`), so however high winExp is a day pane can never pass #edf2f5 (237 / 242 / 245). That
  accounts for most of the plateau at G 240-242 in the window-heavy day views (q03, q05, q14). The photos the code itself
  cites have pure white panes (c_27316 #ffffff, y_47300 #fcfcfb); in integ8/clipmask.png the photos' panes are > 245, the
  model's at most level with the white lining. A day frame has a third to a half of the photos' near-white share.
- **Fix:** (1) `07_shell.js` l.754: glass tints [0.93, 0.95, 0.96] -> [0.985, 0.99, 1.0]; the pane's cool cast already
  comes from the sky and haze. (2) Better, as a lighting follow-up once (1) lands: drop the multiply and apply the
  transmittance inside the sky / exterior shaders before aces() (a `u_glassT` uniform set from 12_scene.js), so a bright sky
  can still clip. (3) Leave the look-out view (q12) as it is: winExp already eases to 1 at the window.
- **Targets:** day panes p50 >= 250 in q07 / q14 / q17; share above L250 >= 1.5 % in q06 / q15 / q16; q12 unchanged within 2 L.

## To room (`src/09c_room.js`): recessed toe-kick and the 11A footwell hairline (integration L10 low, carried from L7-L9)
- **Owner:** room. **Severity:** low.
- **Problem:** (1) the THE Room shell base is a flush navy-grey band, not a recessed near-black toe-kick, under the aisle
  ash panels and at the monument ends; (2) a white hairline runs along the 11A rear-facing footwell at the floor /
  side-panel joint.
- **Evidence:** integ7/outA/j_kick_close.png column x 560: lip L53 / 45, then a flush band at L18-24 (c_27312 bases L0-2, in
  a recess); integ7/outB/fw_11A_footwell.png (DPR 2) box (1180-1240, 760-945): 330 px > L200, max L248, 524 px > L120.
- **Fix:** (1) kick: at `09c_room.js` l.480 (`gRBox(0.045, 0.10, ...)` at x 0.565) and the matching kicks under
  `roomAisleAsh` (the `ashFrameX` family), set the kick 0.02 m back from the ash face (0.565 -> 0.545 along that side's
  normal), height 0.08, material `{ c: '#1c1d20', r: 0.7 }`; (2) footwell: make the faces overlap instead of meeting at an
  edge: extend the footwell floor 0.01 m under the side panel, or sink the side panel 0.005 m into the floor.
- **Targets:** kick recess L <= 15 with a contact line; 0 px > L120 in the footwell box at DPR 2.

## To ceiling/bins (`src/08_bins.js`): grey fragments on the right outboard bin lip at door 3 (integration L10 low, carried from L7-L9)
- **Owner:** ceiling/bins (the door-3 end of the outboard run, or the PSU instances there). **Severity:** low.
- **Problem:** irregular grey fragments with PSU-like dots run along about 0.5 m of the right outboard bin lip at door 3.
- **Evidence:** integ7/outB/z04_binlip.png (DPR 2, `__app.setView([2.3, 1.62, 32.7], Math.PI/2 - 0.45, 0.25)`): fragments at
  about (700-900, 755-765), unchanged since L9 (0.14 % of the box changed); crops integ8/z04_cmp.png.
- **Fix:** (1) hide the centre PSU meshes in that view (filter `scene.opaque` by mesh name) to confirm which mesh shows
  through; (2) then end that PSU / band run 0.05 m before the door-3 zone boundary (`fitModules` z1 - 0.05), or drop it 2 mm
  along its face normal. Re-render z04 at DPR 2. **Target:** no grey fragment on the lip.

## Lighting run 2, L11 (final rating of the run: lighting 7.9, integration 7.7): items for the area owners

The run ended at its 5-round cap. These are the open items the L11 raters gave to area owners (lighting-owned items stay with the lighting loop). Each area: fix what is addressed to you, under your regression guard, then re-rate.

### To room / econ / py, shared SEATMAT keys in 09_seats.js (low, lighting rater L11): Carried: material response. Rounded white plastics and the THE Room caps have no thin streak highlights; the roughness h
- **Problem:** Thin-highlight share, render vs photo: q06 0.96 vs 2.20 %, q16 0.67 vs 2.50 %, q15 0.61 vs 1.10 %, q13 0.16 vs 1.47 %, q14 0.37 vs 0.92 %.
- **Evidence:** thin.py on /tmp/claude-0/-home-user-Calc/b1f1e8ce-ba52-5ff4-94e9-cb27b8198a85/scratchpad/qa/L11/*.png and ref/ana photos. 09_seats.js still has arm r 0.45, armPad 0.5, jCap 0.34, pyShell 0.42.
- **Fix:**
  09_seats.js SEATMAT (shared, one line per key): arm r 0.45 -> 0.26, armPad 0.50 -> 0.32, jCap 0.34 -> 0.26, pyShell 0.42 -> 0.30. Targets: thin share >= 1.1 % in q06 / q16 / q15; face means within 5 L.

- **polishD response:** pyShell 0.30 is kept, with pyArm 0.38 and pyArmPad 0.32 (py w17, A 8.5 / B 8.5); q13 thin highlights rose 0.16 -> 0.24 %. `arm` 0.26 and `armPad` 0.32 were reverted untested: q15 / q16 thin highlights stayed at 0.61 / 0.65 %, while the arm faces rose 2-5 L. `jCap` 0.26 was reverted: it added +16 L on a flat q09 cap face, and q06 stayed at 0.95 %. The capRail is now a 9 mm round edge with seg 3 (room w19). A streak on the econ arms and room caps needs a cove-specular change on the lighting side. See fixed_polishD.md.
### To py (low, lighting rater L11): Carried: PY contact darks are about a third of the photos'. The lighting side (SSAO) has moved as far as the brief allow
- **Problem:** Thin dark-line share: q13 1.01 vs py_37302 2.77 %, q14 0.76 vs py_37301 3.15 % (L10: 0.73 / 0.67).
- **Evidence:** thindark.py on /tmp/claude-0/-home-user-Calc/b1f1e8ce-ba52-5ff4-94e9-cb27b8198a85/scratchpad/qa/L11/q13_pyFront.png, /tmp/claude-0/-home-user-Calc/b1f1e8ce-ba52-5ff4-94e9-cb27b8198a85/scratchpad/qa/L11rateL/x/q14.png and the ref/ana photos.
- **Fix:**
  09b_py.js pySeat / pyUnit as handed off in review/qa/from_integration.md 'To py': a dark reveal at the shell rim (#1f2228, r 0.9), 1 cm gap strips (#1c1e23) at the cushion sides and the leg-rest hinge, and a 6 mm split line on the shell. Target: q13 >= 1.8 %, q14 >= 1.8 %.

- **polishD response:** see the py medium item below.
### To suite (medium, integration rater L11): Owner: suite (09d_suite.js suiteUnit). Lighting is secondary (04_shaders.js ssaoF).
- **Problem:** THE Suite still reads cleaner than the in-flight photos: its thin dark outline lines are 0.55-0.85x of omaat_f2 / f5 / f11 / f13 / f40. The seat geometry carries almost no joints, so the AO has nothing to darken.
- **Evidence:** Thin dark-line share (thindark.py), L11: - q02 1.73 %, q03 1.51 %, q05 1.26 %. - In flight: omaat_f2 2.24, f5 2.43, f11 2.85, f13 2.16, f40 1.79 %. - Official: f_17301 4.13, f_17306 3.58, f_17313 2.21 %. - q03 without the AO (integ7/outA/q03_noSSAO.png): 0.62 %. - For comparison, THE Room q06: 1.77 % without the AO, 2.68 % with it (in-flight 2.38-2.68 %). L10 -> L11 thin-line change in q03: +0.40 / -0.26 points (integ9/tdiff_L10_L11.png).
- **Fix:**
  1. 09d_suite.js, after the ottoman cushion loft (gLoft(cushionSecs(ow - 0.01, 0.52, ...)) at y 0.40): add a dark welt between the cushion and the tray:
     `B.add(gRBox(ow - 0.006, 0.014, 0.526, 0.005, 1), M4.trs(ox, 0.366, -L + 0.39), { c: '#1d1a17', r: 0.9 });`
  2. Aisle box: drop the lid (fConsole slab at y 0.63) 3 mm, and put a 5 mm dark seam under it:
     `B.add(gBox(bX1 - bX0 + 0.004, 0.005, 0.372), M4.trs((bX0 + bX1) / 2, 0.617, -L + 0.30), { c: '#1d1a17', r: 0.9 });`
  3. Wardrobe / aisle wall inner face and console fascia: 4-6 mm dark split strips, 1-2 mm proud, at each panel joint and door edge, as in omaat_f11 / f5 (gBox(0.005, h, 0.004), { c: '#1d1a17', r: 0.9 }).
  4. Table slab: a 6 mm dark underside strip under the front lip, 1 cm behind it.
  5. Optional lighting help, with no new full-screen pass:
     - In ssaoF, turn the spiral per 2x2 quad: a0 = 0.39 + (6.2832 / nT) * (0.5 * q.x + 0.25 * q.y), with q = mod(floor(gl_FragCoord.xy), 2.0).
     - In mainFS, call ssaoF outside the sW branch, so the derivatives are taken in uniform control flow: `occ = sW > 0.01 ? ssaoF(...) : 0.0`.
     - Average the quad: `occ += dFdx(occ) * (0.5 - q.x); occ += dFdy(occ) * (0.5 - q.y);`. That gives 4x the effective taps at no extra pass.
     - Then try ssaoIn 0.3 -> 0.5 in the F zone only.
  6. Targets:
     - q03 >= 1.8 %, q05 >= 1.6 %, q02 >= 2.0 % thin dark lines.
     - f_ink_seated row 320 (539-593) >= 130.
     - Face means within 5 L.
- **Status (polish C, 2026-10-26):** items 1-4 done in `09d_suite.js` (plus a cap-to-shell groove and a console joint), rated w17 8.7 / 8.9 and w18 8.8 / 9.0, kept. Item 5 (SSAO) not done: `04_shaders.js` is lighting's. Log: `fixed_polishC.md`.

### To py (medium, integration rater L11): Owner: py (09b_py.js pySeat / pyUnit). Carried from L9 / L10, with no PY commit since 2026-10-24.
- **Problem:** PY seats read as clean CG. Their outline darks are about half of the in-flight photos' (1.01 / 0.76 % vs 1.67-1.94 %), and PY is the only cabin outside its in-flight range.
- **Evidence:** Thin dark-line share: - q13 1.01 % (L10 0.73), q14 0.76 % (L10 0.67). - sanpy_11 / 13 / 14: 1.83 / 1.94 / 1.67 %. - py_37302 / 37301: 2.77 / 3.15 %. - Other cabins: q06 2.68 % (in flight 2.38-2.68 %); q16 3.24 % (sany_11-13 2.36-2.90 %). Frame p5: q13 43 vs 32; q14 55 vs 31. Bottom third of q13 below L50: 15.7 vs 28.8 %. Side by side with the in-flight photos: integ9/p8.jpg (q13 | sanpy_13, q14 | sanpy_11).
- **Fix:**
  09b_py.js pySeat, modelled on the econ tuck crease (09a_econ.js w11 B loft, { c: '#283052', r: 0.95 }):
  1. After the shell loft, a dark reveal each side where the shell's front rim meets the back fabric:
     `for (const sd of [-1, 1]) loftAt(B, ds.filter(([y]) => y < 0.93).map(([y, d, w]) => SEC(y, 0.008, 0.012, zr(y) - d + 0.012, 0.003, sd * (w / 2 - 0.006))), BH, { c: '#1f2228', r: 0.9 }, 1);`
  2. 1 cm dark gap strips (gRBox 0.012 high, { c: '#1c1e23', r: 0.9 }) along the cushion sides against the console, and at the cushion front / leg-rest hinge.
  3. In pyUnit:
     - a 6 mm dark split line on each console face;
     - a 1 cm dark foot plate under each leg.
  4. Targets:
     - q13 / q14 thin dark-line share >= 1.6 %.
     - q13 p5 <= 38; q13 bottom-third p25 <= 55.
     - Face means within 5 L.

- **polishD response:** partly done. In w16 the proposed proud strips failed: the shell-rim reveal showed as a black stripe through the rounded shell side, and the cushion side strips read as floating rods (A 8.3 / B 8.1, high issues). w17 keeps a soft band under the cushion nose, a gap under the roller, foot plates and a console split line (A 8.5 / B 8.5). Outline darks are still short (q13 2.39 -> 2.42 % on my metric). Closing that needs recessed joints cut into the geometry. See fixed_polishD.md.
### To monuments (medium, integration rater L11): Owner: monuments (10_mono.js inkWall, MONMAT.inkCloud / inkGround). Carried, unchanged for seven rounds.
- **Problem:** THE Suite front-wall ink-cloud print reads as grey smoke stains: 3x the photo's contrast, a third of its saturation, and 40 L darker.
- **Evidence:** Print box in f_ink_seated (415-670, 320-380), current head: - L167, range 76, h46 s0.04, fine 1.4. - omaat_f13: L208, range 23, h42 s0.11, fine 2.3. - q03 top boxes: range 80 / 78. Crops: integ9/ink_cmp.jpg (model | omaat_f13) and integ9/ink_q03_f40.jpg (q03 top | omaat_f40).
- **Fix:**
  10_mono.js inkWall:
  1. Grid 0.1 -> 0.03 m: nx = ceil((x1 - x0) / 0.03), ny = ceil(H / 0.03).
  2. Crisp, speckled edges: `t = smoothstep(0.44, 0.52, n + 0.10 * (fbm(x / 0.05, y / 0.05, 256, 2, 29) - 0.5)) * lowY`.
  3. MONMAT.inkCloud '#6a665f' -> '#b3ad9f', about 30 L under the '#dddbd0' ground, with a slight warm hue (s ~0.10).
  4. If the vertex count objects, bake the same field into an atlas canvas panel, as with the 'washi' panel in 06_atlas.js, and map it with washiUV.
  5. Targets in f_ink_seated:
     - range <= 40, mean L >= 185
     - h35-45, s0.07-0.13
     - fine >= 2
     - q03 top boxes range <= 45

- **Status (polish C, 2026-10-26):** done via item 4 (atlas panel 'ink', `inkPanel` in `10_mono.js`, one-line hook in `06_atlas.js`); print box L200-202, range 30-34, h42 s0.09; rated w21 8.7 / 8.8, kept. Fine >= 2 not met (0.6-0.8). A second round (thinner strata) was reverted under the guard. Log: `fixed_polishC.md`.

### To shell (low, integration rater L11): Owners: shell (07_shell.js l.754 glass tints), then lighting (12_scene.js glass blend). Carried from L10, unchanged; the
- **Problem:** Day window panes are capped below white (G <= 242) by a multiply tint in display space. They never read brighter than the white lining beside them, so a day frame has a third to a half of the photos' near-white share.
- **Evidence:** q14 pane interior (635-675, 230-300): max 235 / 241 / 244, against a cap of 237 / 242 / 245. The reveal beside it (row 265, x 606) reads 245 / 246 / 246. G histograms plateau at 240-242 and fall off sharply above. q03: 242 -> 11645 px, 243 -> 1332 px. Share above L235, model vs photo: q15 3.8 vs 9.2 %, q16 5.3 vs 9.8 %, q09 4.3 vs 10.7 %, q07 6.5 vs 9.0 %. p99 245 vs 254-255 in q07 / q16.
- **Fix:**
  1. 07_shell.js l.754: glass tints [0.93, 0.95, 0.96] -> [0.985, 0.99, 1.0]. The pane's cool cast already comes from the sky / haze.
  2. Or, better: drop the multiply and apply the transmittance inside the sky / exterior shaders before aces() (a u_glassT uniform set from 12_scene.js), so a bright sky can still clip.
  3. Keep q12 as it is: winExp already eases to 1 at the window.
  4. Targets:
     - Day panes p50 >= 250 in q07 / q14 / q17.
     - Share above L235 >= 7 % in q15 / q16.
     - q12 unchanged within 2 L.

### To py (low, integration rater L11): Owners: py (09b_py.js shell / arm edges) and the shared SEATMAT pyShell key.
- **Problem:** PY seat shells and arm rims carry almost no thin specular highlights, even against the in-flight photos (q13 0.16 % vs sanpy 0.46-0.67 %). The other cabins are inside their in-flight range.
- **Evidence:** thin.py, L11: - q13 0.16 %, q14 0.37 %; sanpy_11 / 13 / 14 0.67 / 0.46 / 0.47 %; py_37302 1.47 %. - THE Room q06 0.96 % (in flight 0.06-0.57 %). - Economy q16 0.67 % (in flight 0.48-1.05 %).
- **Fix:**
  1. 09b_py.js: shell and arm top-edge gRBox radius >= 8 mm, seg 3.
  2. SEATMAT pyShell r 0.42 -> 0.32.
  3. Targets:
     - q13 >= 0.45 %.
     - Face means within 5 L.

- **polishD response:** done in py w17: SEATMAT pyShell r 0.30 and rounder console / shroud edges. q13 thin highlights 0.16 -> 0.24 %, still below the 0.45 % target.
### To room (low, integration rater L11): Owner: room (09c_room.js). Carried from L7-L10, unchanged; no room commit since 2026-10-25 03:14.
- **Problem:** THE Room shell bases read as a flush grey band, not a recessed black toe-kick, and a white hairline shows along the 11A footwell floor, at DPR 1 as well as DPR 2.
- **Evidence:** Toe-kick: j_kick_close (integ9/outD) column x 560 reads lip L137-144, then a flush band at L22-23, the same as L10. c_27312 shell bases are L0-2, in a recess. Footwell: fw_11A_footwell at 1x (integ9/outD), box (590-620, 380-473): 47 px > L200, max 248. The L10 DPR 2 render, downsampled to the same box, reads 58 px > L200. Crops: integ9/fw_zoom.png.
- **Fix:**
  1. Kick, at 09c_room.js l.480 (gRBox(0.045, 0.10, ...) at x 0.565) and the matching kicks under roomAisleAsh (the ashFrameX family):
     - Set the kick 0.02 m back from the ash face (0.565 -> 0.545 along that side's normal).
     - Height 0.08, material { c: '#1c1d20', r: 0.7 }.
  2. Footwell: make the faces overlap instead of meeting at an edge. Either extend the footwell floor 0.01 m under the side panel, or sink the side panel 0.005 m into the floor.
  3. Targets:
     - Kick recess L <= 15, with a contact line.
     - 0 px > L120 in the footwell box at DPR 1 and DPR 2.

- **polishD response:** done in room w19 (89168b6, A 8.5 / B 8.5). The kick is recessed 2 cm, 0.08 tall, #1c1d20. The hairline was the lit chamfer of the low console block at the footwell mouth; that block now has square edges, and the crop box went from 48 px > L200 to 0.
### To ceiling (low, integration rater L11): Owner: ceiling/bins (08_bins.js: the door-3 end of the outboard run, or the PSU instances there). Carried from L7-L10, u
- **Problem:** Grey dashes poke through the right outboard bin lip and the bin door's upper edge at door 3.
- **Evidence:** z04_binlip (__app.setView([2.3, 1.62, 32.7], Math.PI/2 - 0.45, 0.25)), 1x on the current head, crop (320-480, 360-400): the same dashed fragments as the L10 DPR 2 render (integ9/z04_zoom.png, L10 top, L11 bottom).
- **Fix:**
  1. Hide the centre PSU meshes in that view (filter scene.opaque by mesh name) to find which mesh shows through.
  2. Then either end that PSU / band run 0.05 m before the door-3 zone boundary (fitModules z1 - 0.05), or drop it 2 mm along its face normal.
  3. Re-render z04 at DPR 1 and 2. Target: no grey fragment on the lip.


## Lighting run 3, L11: notes for the area owners

### To shell (`src/07_shell.js`), FYI: the pane tint now lives in `12_scene.js` LIGHT_TUNE.glassT
- The day-pane transmittance is applied to the sky and the exterior before the tone curve (mainFS / skyFS `u_glassT`), so a
  bright sky clips to white as in c_27316 / y_47300. The display-space glass multiply (DST_COLOR pass over glassR / glassL)
  runs only in x-ray now, so the per-instance glass tints in 07_shell.js only colour the x-ray panes.
- `LIGHT_TUNE.glassT` = your w18 tint [0.985, 0.99, 1.0] raised to 2.4 = [0.964, 0.976, 1.0]: below the clip every pane and the
  look-out view (q12 frame 124.9 -> 125.0) keep the level your w18 raters judged. If you change the pane tint again, set
  glassT to tint^2.4 (or say so here). Door viewing-window glass is in glassR / glassL, so it takes the same treatment.
- Day `winExp` 4.0 -> 5.5 (SKIES.day): the economy cloud deck now clips (q17 pane p50 247 / 248 -> 252 / 253, y_47303 252).
  Your w15 low (door viewing-window glass a flat white with no sky gradient) is still open: at this exposure the door glass
  clips like the cabin panes, which is what the official photos show for the cabin panes; lalf_133's graded door pane would
  need a separate (lower) exposure for the door glass, which lighting has not added.

### To py / econ (`09_seats.js` SEATMAT, `09b_py.js`, `09a_econ.js`), FYI: cove rim highlights aft of THE Room
- mainFS now draws the cove-line lobe on the material roughness (not the spec-AA-widened one), x3 on rounded fillets (rough
  < 0.45-0.6), aft of z20 only (PY and economy) and at the Sharp quality only (as the contact AO; Balanced keeps its frame
  cost). With py w17's pyShell 0.30 / pyArm 0.38 / pyArmPad 0.32 the PY rims now carry
  streaks: thin-highlight share q13 0.24 -> 0.29 % (sanpy 0.46-0.67), q16 0.62 -> 0.67, q15 0.61 -> 0.65, q17 0.40 -> 0.44.
  The econ `arm` 0.26 / `armPad` 0.32 keys (polishD reverted them untested) would now show as streaks; worth a re-test against
  y_47303 armrest tops.
- THE Room / THE Suite are left out: there the lobe drew white outlines on every cap edge and beaded glints along the divider
  rails and lifted the q06 frame (median 165 -> 167 vs c_27312 128), where the thin-highlight share already sits above the
  in-flight range. A THE Room `jCap` roughness change therefore still gets no rim lobe (polishD: +16 L on a flat q09 cap face).

## Lighting run 3, L12 (lighting 8.0 / integration 7.9 raters): items for the area owners

These are the L12 raters' open items owned by other areas. Lighting-owned items are logged in fixed_integration.md
(lighting run 3, L12).

### To room / econ, shared SEATMAT keys in `09_seats.js` (low): material response (carried, reduced weight)
- **Problem:** the thin-highlight share is under the official photos: q06 0.92 vs 2.20 %, q16 0.67 vs 2.50 %, q15 0.65 vs 1.10 %,
  q09 0.36 vs 1.18 %. Real in-flight economy photos measure 0.03-0.66 % (sany_13 0.48, sany_18 0.66, sany_22 0.63), so the renders
  sit at the top of the in-flight range. The PY roughness landed; econ arm / armPad and room jCap were tested and reverted.
- **Evidence:** thin.py (L > 235 with 9 x 9 clip density < 0.45) on the L12 renders and the ref/ana and ref/web photos.
- **Fix:** no further roughness drop unless a real in-flight photo shows streaks at seat level. If one does, lighting can extend
  the existing rim lobe (`u_rimK`) forward of `u_sLowZ` at half gain (rimZ floor 0.5) for the room jCap streaks, checked against
  the q06 median guard (<= 166). Nothing is needed from room / econ now.

### To py (`09b_py.js`, low): PY contact darks and mid-scale form shading (carried)
- **Problem:** thin dark-line share q13 1.00 vs py_37302 2.77 %, q14 0.73 vs py_37301 3.15 %; seat-zone mid-band contrast q13 19.6 vs
  28.3. The lighting side (contact AO) is done; this needs seam geometry.
- **Evidence:** thindark.py on the L12 q13 / q14 renders and the official photos.
- **Fix:** as handed off in 'To py' above: a dark reveal at the shell rim (#1f2228, r 0.9), 1 cm gap strips (#1c1e23) at the
  cushion sides and the leg-rest hinge, a 6 mm split line on the shell. Target q13 / q14 >= 1.8 %.

### To py (`09b_py.js` pySeat / pyUnit, medium): PY seats still read as clean CG (carried from L9-L11)
- **Problem:** the PY outline darks are about half of the in-flight photos' (q13 1.00 %, q14 0.73 % vs 1.67-1.94 %), and the w17
  joints (foot plates, the 6 mm console split at y 0.40, the soft band under the cushion nose, the hinge-roller gap) sit where
  the rated frames do not look. Rim highlights rose but remain short: q13 0.16 -> 0.29 %, against 0.46-0.67 % in flight.
- **Evidence:** masks integ10/thin_py.jpg (q13 | sanpy_13, q14 | py_37301). The photos' PY outlines come from four seams the model
  renders as smooth shading: the patterned back fabric against the grey shell wing (a vertical line both sides of every seat);
  the headrest panel's lower edge against the back; the seat-cushion front and sides against the console and shroud; the
  console's cubby and control openings. The raters rejected w16's proud black strips, so these should be recessed mid-dark
  grooves like the suite's fCapJoint.
- **Fix:** grooves inset 2-3 mm, material `{ c: '#2a2e36', r: 0.9 }` (L ~45-60 rendered):
  1. Back fabric to shell wing, each side, a 5 mm groove loft along the shell's inner rim from the headrest to the cushion:
     `for (const sd of [-1, 1]) loftAt(B, ds.filter(([y]) => y < 0.93).map(([y, d, w]) => SEC(y, 0.005, 0.010, zr(y) - d + 0.010, 0.003, sd * (w / 2 - 0.004))), BH, PYGROOVE, 1);`
  2. Headrest lower edge: a 5 mm horizontal groove across the back at the blue panel's bottom.
  3. Cushion front and side edges: a 6 mm gRBox groove 2 mm below the cushion top, against the console and shroud faces.
  4. pyUnit console face: the cubby and control openings as 8-10 mm dark recesses (gBox, `{ c: '#16181c', r: 0.9 }`) instead of
     flush decals.
  Targets: q13 / q14 thin dark-line share >= 1.5 %, q13 p5 <= 38, face means within 5 L, q13 thin-highlight share >= 0.4 %
  (shell / arm rims gRBox seg 3).

### To suite (`09d_suite.js`, low): THE Suite outline darks close but short in the seated and behind views
- **Problem:** q03 1.71 %, q05 1.48 % thin dark lines vs 1.79-2.85 % in flight; the top and middle of the frame gained nothing. The
  polishC joints sit in the lower third, and q02 meets its target.
- **Evidence:** integ10/thin_suite.jpg against omaat_f5 / f11. Missing: the edges of the dark striped-wood insert on the window
  console top and its black-rimmed recess; the vertical grain / panel lines on the wood panels each side of the 43-in screen
  (strong in omaat_f11, left of the screen); the joint between the tall aisle shell's cap and its side face, nearest the camera
  in q05 (omaat_f5 draws it as a continuous line along the console).
- **Fix:** 1. a 4 mm SEATMAT.fSeam rim, 1 mm below the top face, round the console-top wood insert (the QA r3 tapered insert);
  2. 2-3 vertical fSplit lines, 3 mm wide and flush, per screen-wall wood panel, as on the wardrobe (w17b); 3. extend the cap()
  groove (fCapJoint) along the cap's full inner length on the aisle wall (in q05 it reads only at the ends). Targets: q03 >= 1.8 %,
  q05 >= 1.6 % thin dark lines, face means within 5 L.
- **Note from lighting (L12):** the contact AO no longer draws on the smooth aft-facing front wall above 1.45-1.55 m (the bulkhead
  sign's ghost band and stepped copies are gone); the curtains and everything below 1.45 m keep it, so the q03 / q05 shares above
  are not changed by that.

### To ceiling/bins (`08_bins.js`, low): grey dashes through the right outboard bin lip at door 3 (carried)
- **Problem:** grey fragments still poke through the right outboard bin lip at door 3 (z04). polishE traced them to the THE Room
  centre PSUs (psuo2), occluded only by the centre-bin door edge; no change was made.
- **Fix:** 1. end the psuo2 run 0.05 m short of the door-3 zone boundary (z1 - 0.05), or 2. drop it 3 mm along its face normal, so
  the centre-bin door edge covers it with depth margin. Target: no grey fragment on the lip in z04 at DPR 1 and 2.

## Lighting run 3, L13 (final rating of the run: lighting 8.1, integration 8.0): items for the area owners

Lighting run 3 (plateau breaker) ended at its 3-round cap (L11 7.8 -> L12 7.95 -> L13 8.05). Open items the L13 raters gave to area owners:

### To room / econ (shared SEATMAT in 09_seats.js) (low, lighting rater L13)
- **Problem:** Thin-highlight share: q06 0.92 vs c_27312 2.20 %, q16 0.67 vs y_47301 2.50, q15 0.65, q09 0.36. Real in-flight economy photos: 0.03-0.66 %.
- **Evidence:** thin.py on /tmp/claude-0/-home-user-Calc/b1f1e8ce-ba52-5ff4-94e9-cb27b8198a85/scratchpad/qa/L13/*.png; the views are pixel-identical to L12.
- **Fix:**
  No change unless a real in-flight photo shows seat-level streaks. If one does: the room jCap streaks via the existing rim lobe (u_rimK) extended forward of u_sLowZ at half gain, with the q06 median guard (<= 166).

### To py (low, lighting rater L13)
- **Problem:** Thin dark-line share q13 1.00 % vs py_37302 2.77 %.
- **Evidence:** thindark.py on /tmp/claude-0/-home-user-Calc/b1f1e8ce-ba52-5ff4-94e9-cb27b8198a85/scratchpad/qa/L13/q13_pyFront.png and ref/ana/py_37302.
- **Fix:**
  09b_py.js per review/qa/from_integration.md 'To py': a dark reveal at the shell rim (#1f2228, r 0.9), 1 cm gap strips at the cushion sides and the leg-rest hinge, a 6 mm shell split line. Target >= 1.8 %.

### To py (medium, integration rater L13)
- **Problem:** PY seats still read as clean CG: outline darks about half of the in-flight photos, rim highlights short, the lower bands lifted
- **Evidence:** Thin dark lines: q13 1.00 %, q14 0.72 % vs sanpy_11-18 1.67-2.63 % and py_37302 / 37301 2.77 / 3.15 %. Thin highlights: q13 0.29 %, q14 0.38 % vs sanpy 0.46-0.67 %. Lifted darks: - Frame p5: q13 44 vs 32; q14 55 vs 31. - q14 bands 4-5 mean / p10: 145 / 86 and 128 / 75 vs py_37301 118 / 36 and 89 / 30. Crop: /tmp/claude-0/-home-user-Calc/b1f1e8ce-ba52-5ff4-94e9-cb27b8198a85/scratchpad/integ11/c_py.jpg.
- **Fix:**
  09b_py.js pySeat. Add recessed grooves, inset 2-3 mm, material `{ c: '#2a2e36', r: 0.9 }` (it renders at L45-60):
  1. Each side, where the back fabric meets the shell wing: a 5 mm loft along the shell's inner rim from the headrest down to the cushion, e.g.
     `for (const sd of [-1, 1]) loftAt(B, ds.filter(([y]) => y < 0.93).map(([y, d, w]) => SEC(y, 0.005, 0.010, zr(y) - d + 0.010, 0.003, sd * (w / 2 - 0.004))), BH, PYGROOVE, 1);`
  2. A 5 mm horizontal groove at the headrest panel's lower edge.
  3. A 6 mm gRBox groove 2 mm under the cushion top, along its front and sides.
  4. pyUnit: the console cubby and control openings as 8-10 mm recesses, `gBox` with `{ c: '#16181c', r: 0.9 }`.
  5. To lower the PY darks: a crease under the cushion nose, and the leg-rest underside in the PYGAP tone.
  
  Targets:
  - q13 / q14 thin dark-line share >= 1.5 %.
  - q13 p5 <= 38; q14 bands 4-5 p10 <= 50.
  - Face means within 5 L.
  - q13 thin highlights >= 0.4 %.

### To monuments (medium, integration rater L13)
- **Problem:** The door-3 self-service bar follows ANA's 2019 render; an in-service photo in ref/web shows a different face (galley inserts, brewer, glass-door mini-fridge, black counter)
- **Evidence:** Pair: /tmp/claude-0/-home-user-Calc/b1f1e8ce-ba52-5ff4-94e9-cb27b8198a85/scratchpad/integ11/p_bar.jpg (q11 | omaat_j32). Counter: q11 (130-560, 345-380) #4a4c4f p50 78 vs photo counter top p50 37. Back panel: q11 (195-300, 160-330) #1f1e21 L30, p10 29 / p90 32: flat and crushed. The photo's charcoal galley / fridge face reads L62, p10 48 / p90 88, with visible structure. Ash doors: q11 L177 vs photo L137 (photo dimmer and warmer).
- **Fix:**
  10_mono.js bar: rebuild the upper face to the photo, keeping the ash lower cabinets and the monitor:
  - Left bay: two oven / chiller doors (`gRBox`, #b9bcbf, r 0.5) with small blue LED windows, vertical handle bars, and a lit control strip above (#d8d6d0 with red / amber dots).
  - Centre: the monitor over an open, lit cubby with the coffee brewer (reuse the galley brewer insert) and a green LED.
  - Right bay: a tall glass-door fridge, framed in #3a3835, with dark tinted glass (the glass material at 0.6 transmission), a round lever latch and a white caution placard at the top.
  - Counter: #141414, r 0.15, with a 15 mm satin-steel nosing (#9a9ea3, m 0.6).
  - Drop the open bottle shelves.
  - Face colour #3a3835, so it reads near L55-65 under the current light.
  
  Target: rater pair q11 vs omaat_j32 with no structural mismatch, and the back face L50-70 rather than flat L30.

### To ceiling (low, integration rater L13)
- **Problem:** Grey dashes still show through the right outboard bin lip at door 3 (unchanged since L11)
- **Evidence:** z04_binlip at head: /tmp/claude-0/-home-user-Calc/b1f1e8ce-ba52-5ff4-94e9-cb27b8198a85/scratchpad/integ11/c_z04.png (3x crop of x280-700, y330-420). It shows the same dashed fragments at x 450-520, y 375-383 as integ10/z04_zoom.png (L11 / L12).
- **Fix:**
  08_bins.js: end the psuo2 run 0.05 m short of the door-3 zone boundary (z1 - 0.05), or move it 3 mm along its face normal so that the centre-bin door edge covers it.
  
  Target: no grey fragment on the lip in z04 at DPR 1 and 2.

