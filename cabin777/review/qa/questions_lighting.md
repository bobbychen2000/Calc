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
