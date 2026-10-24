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
