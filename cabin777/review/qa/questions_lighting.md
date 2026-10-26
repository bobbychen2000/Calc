# Questions for the user (lighting area)

1. **Default Boarding look: white sidewall or the blue band?** The raters disagree, and so do the photos.
   - White: ANA's official photos of this cabin (c_27312, y_47300, py_37302, f_17300) and SANspotter's boarding photo at
     HND (sans_14) show a white sidewall and window belt with no blue. The shell worker and the integration note in
     `from_integration.md` ask for Boarding to stay white.
   - Blue: in-service boarding photos (sany_10, sany_12) and the in-flight photos (tlfl_IMG_9217, stwis_img_6082) show
     ANA's saturated blue running from the bin lens down past the windows. The lighting rater (r3) wants that look in
     Boarding too.
   - QA r3 choice: **Boarding stays white** (it is the default view and is rated against the official photos), and
     **Cruise** carries the saturated blue band down past the windows. If you would rather open the page on the blue
     look, the only change is `MOODS.boarding.sideLed` / `bandCut` in `src/12_scene.js` (copy them from `cruise`).
2. **Amber (Dining) phase at seat level.** The only in-service amber photos (ff_door-gap, ff_seat-with-door-closed)
   show amber bins, cove and lens, a soft warm-beige ceiling and neutral grey surfaces at seat height. The model now does
   exactly that. If you have a photo of the whole THE Room cabin in the amber phase (aisle view), it would pin down how
   far the amber reaches down the sidewall; at the moment the amber stays within ~0.5 m of the bin lens.
3. **Night: one neutral level, or also a warm phase?** (QA r1) The r3 amber night came from one cove sample and read
   orange; the real night photos the raters cite (ucr_room-night-lighting, sany_40, sany_25) show a neutral-warm,
   near-grey cabin, so **Night** is now neutral (cove / vault G/R ~0.85, cool-grey wall, lit galley ends). sany_25 shows a
   separate warm phase (only the cove line gold #9a8152, vault centre <= #1a1511, no amber on the walls). Would you like
   that as an extra mood (e.g. "Night, warm")? Also: the economy night photo (sany_40, median L58) is about twice as bright
   as THE Room's (ucr, median L30); the model has one night level for the whole cabin, set between them (THE Room view
   q20 median L30). Say if economy should be brighter than business at night.
4. **New "Blue" mood (QA r2): which photo should set its level?** ANA's full-blue phase is now a mood chip. The two
   in-service photos of it are exposed about 2x apart: SANspotter's economy shot (sany_47, mean RGB 29/28/81, dark crown,
   only the cove lines bright) and MileLion's THE Suite during the safety video (ml_DSC_1945, mean 81/79/111, lavender
   walls, lit ottoman). The mood sits between them (economy view mean ~45/50/113, the suite ottoman still darker than
   in ml_DSC_1945). Say if it should follow one of them, or if you have a photo of the blue phase in THE Room.

5. **Window sun patches: physical or toned down?** (QA r3) The integration rater asks for sun patches at most 1.3x the
   fabric around them (q14 PY seat back; ANA's official PY photos py_37301 / 37303 show no patch at all). Real sun through
   a 777 window is several times the cabin light, so a physical patch reads much brighter. QA r3 softens the edges (a ~5 cm
   penumbra) and caps the interior sun at 1.5 (was 2.0); the q14 patch now reads 1.48x the fabric (L207 on L140). Say if you
   would rather have the official-photo look (fainter patches, cap ~0.8: every sun patch in the cabin gets weaker) or keep
   them physical.

## Lighting run 2 (raters L7, 2026-10-25)

6. **Boarding colour cast: ANA's official photos or the in-service look?** ANA's official photos (y_47300 / 47301 / 47303,
   py_37301, c_27312) show cool blue-grey shadows on the white plastics (B-R +11 to +33), and the model follows them (run 2
   cools the shaded whites in Boarding). Photos taken on board on the ground (omaatJ_oj_r31 / r37) and in flight (lalf_119 /
   120, kn_room_1, the omaat_f THE Suite set) are warm (R-B +10 to +23). Should Boarding keep the official photos' cool
   balance, or move toward the warmer in-service look? (Both raters ask this.)
7. **Cruise: which in-flight look?** Live and Let's Fly (lalf_room_119 / 120) shows a pale sky-blue band (#658cb6), a
   warm-white vault and mid-grey bins. tlfl_IMG_9217 and sany_22 show the saturated periwinkle band (#5b5cc4-#5f70e4) that
   the Cruise preset uses now. Should Cruise follow one of them, or should there be two presets?
8. **Economy at night: cooler and brighter than THE Room?** (extends 3) sany_40 shows economy at night with cool grey-blue
   bins and ceiling (#525562, L86), a blue-lit lower sidewall and a warm galley end, about 1.7x as bright as THE Room's night
   photo (ucr). The model has one Night level for the whole cabin (economy inherits THE Room's warm-dark look). Should
   economy get its own, cooler and brighter night level? Related: sany_40 shows faint lit cove lines along the bin tops in
   economy, the THE Room night photo none; a per-zone night LED level would allow both.
9. **Sunset through open shades.** In q21 the panes show a blue-grey cloud deck under an amber cabin. No ANA photo of the
   amber phase with open shades at sunset was found. Is a warm orange horizon band expected in those windows?

## Lighting run 2 (raters L8, 2026-10-25)

10. **Contact shading on phones?** Run L8 adds a small screen-space contact shadow (the dark lines where cushions meet
    shells, seats meet the floor and panels meet). It needs an extra depth pass, so it is on only at the **Sharp**
    render quality; phones open on **Balanced** and keep their frame rate, without those lines. Should Balanced get it
    too (about one more geometry pass per frame), or stay as it is?
11. **Upper window tubs in Boarding: cool blue-grey, as in ANA's official photos?** With the shades open in daylight,
    Boarding now gives the upper part of each window tub the sky's blue-grey (y_47303: #a4a9be, B-R +25) instead of the
    cream reveal's neutral white. It follows the official photos' cool balance (question 6). If you prefer the warmer
    in-service look, `MOODS.boarding.tubSky` in `src/12_scene.js` set to `[0, 1]` turns it off.

## Lighting run 2 (raters L9, 2026-10-25)

12. **Amber (Dining) phase: how saturated at seat height?** (updates question 2) The two in-service photos of THE Room in
    the amber phase disagree below the bins. Upgraded Points' cabin photo (ucr_the-room-cabin) shows the ash panels a
    saturated amber (s 0.61-0.72), and the model matches it now (s 0.67). Frequent Flier's two photos
    (ff_seat-with-door-closed, ff_door-gap) show them much greyer (s 0.03-0.50), and the integration rater asks for that
    look (s 0.45-0.52). Neutralising the seat-level light that far (`MOODS.dining.lowTint` [1.0, 1.4, 2.2] x0.7) moves the
    sunset view away from ucr (its bottom third s 0.57 -> 0.43, ucr 0.56), so it has not been changed. Which photo should
    set the seat level? If you prefer the greyer look, the one-line change is `lowTint: [1.0, 1.4, 2.2], lowGain: 0.7` in
    `MOODS.dining` (and `wake`) in `src/12_scene.js`.

## Lighting run 2 (raters L10, 2026-10-25)

13. **A blur pass for the contact shading at Sharp?** (follows question 10) The contact shading now takes 16 samples per
    pixel in a disc capped at 16 px on screen. That removed the stepped dark bands above the THE Room headrest flaps and
    the hard stripes on surfaces close to the eye, and brought back some of the THE Suite contact lines. The remaining
    gap (THE Suite thin dark-line share 1.3-1.5 % against 1.8-2.9 % in the in-flight photos) would need a wider sampling
    window, which brings back stepped ghost copies of the bulkhead monitor's outline unless the result is smoothed. The
    smoothing needs two extra full-screen passes (an AO target and a depth-aware blur), only at Sharp. This run's brief
    ruled out new full-screen passes, so it has not been done. Should Sharp get those two passes (phones on Balanced
    would still pay nothing)?

## Lighting run 3 (after the L11 rating, 2026-10-26)

14. **Rim highlights on phones?** (follows question 10) The PY and economy seats now catch thin highlight lines from the cove
    lights along their rounded rims and armrests, as in the photos. Like the contact shading, this costs a little per pixel
    (about 3-4 % of the frame in the test renderer), so it is on only at the **Sharp** quality; phones open on **Balanced**
    without it. Should Balanced get it too?

## Lighting run 4 (after the L13 rating, 2026-10-26)

15. **How bright should the window wall be close up: ANA's official renders or in-flight photos?** In Boarding and Cruise,
    the wall between and below the windows used to read flat white in every seat view. The integration rater compared it with
    in-flight photos and ANA's own economy and THE Room seat photos (y_47303, c_27300; OMAAT's THE Suite photos), where that
    wall is a light grey that darkens from the bin light down to the window (about L176-215). This run follows those photos
    for the wall within about 4 m of the eye; the far wall across the cabin keeps its brightness. Some official renders keep
    the near wall brighter than that (f_17313 behind THE Suite about L223-228, f_17304 L203-230), so the suite views sit a
    little under those two renders now. If you would rather match the official renders, the one-line change is
    `beltK: 0.55` -> `0.7` in `MOODS.boarding` (and `cruise`) in `src/12_scene.js`, or `1` to turn it off.
