// ------------------------------------------------------------------
// Scene assembly: meshes, ambient-visibility volume, sun shadows, lighting moods, window shades, rendering
// ------------------------------------------------------------------
const MOODS = {
  // boarding = the ANA photo look: neutral-cool white LED light, high key (ref/ana y_47300, c_27312, py_37302)
  // QA r1: two LED circuits. led = ceiling cove (stays near-white in boarding/cruise: aisle ceiling + aisle-side bins lit
  // white), sideLed = the lens under the outboard bins, ANA's saturated blue sidewall band fading to white at the window
  // belt [V: tlfl_IMG_9217 #5b5cc4 (cruise), sany_10 #5466e8 / sany_12 #4c5edc (boarding), roame_7672 #5e7fef].
  // hemiBot lowered and exposure raised with the fill/AO rework (u_fill 0.7 -> 0.45) so mean tones stay put while
  // undersides, footwells and the floor darken [V: tlfl_IMG_9217 PSU underside #615c5d, c_27312 footwell #2d2c30]
  // QA r2: sideLed raised so the band under the outboard bins reads saturated blue now that the shader cuts the white
  // hemi / bounce / wash inside the band [V: tlfl_IMG_9217 #5d5eca at the lens, #867db2 at the window tops; sany_12
  // boarding #4c5edc]
  // QA r3: the sRGB display encode, AO_TUNE (unoccluded hemisphere share 0.15 -> 0.22, emitter cells under the bins)
  // and the THE Suite lift raise the shadowed faces, so the exposures come down (boarding 1.40 -> 1.20, cruise 1.15 ->
  // 1.0), set on the photo's material tones at HEAD: q06 charcoal shells #42454f (c_27312 #394049-#414755), aisle ash
  // ends #bbb9b3 (#bdbaab-#cfcabd), window wall #d2d4d5 (#cacdd2); q15 window-block backs #566aa0 (y_47300 #415385-
  // #4d5e8c); q03 console #594d45 (omaat_f11 #514537) [D renders, V photos].
  // Boarding keeps the white sidewall of ANA's official photos (c_27312, y_47300, py_37302, sans_14 at HND: no blue
  // band; from_integration / from_shell 1): a near-white lens with a light band cut. The saturated blue band that runs
  // down past the windows is the in-service cruise look: the lens alone lights the wall under the bins (bandCut 0.8),
  // 0.2 of it at the belt [V: tlfl_IMG_9217 #5c5dc6, belt #736a88; sany_12 #556df7, window line #5362e0; stwis_img_6082
  // #1961f9]; sideLed from the ACES inverse of #5467ef at the lens [D]. Boarding vs blue: questions_lighting.md 1
  // QA r1 (light), tonal range: with the crevice term in mainFS (near-blacks only where ao < 0.5) the exposures go up,
  // boarding 1.20 -> 1.38, cruise 1.00 -> 1.12: whites stopped at 225-239 and mid-tones sat 10-15 % low [V: p99 / % >235
  // c_27312 255 / 7.2 %, y_47301 254 / 9.5 %, py_37301 246 / 6.5 % vs q06 238 / 1.5 %, q16 228 / 0.4 %, q14 237 / 1.3 %;
  // Y fabric mean L66 (y_47300) vs 56] (integration r1). Boarding lens cool white and brighter, bandCut 0.15: the band
  // from the lens to the window tops is the brightest part of the official photos' wall, slightly cool [V: y_47301
  // #f0f1f5 / #ebeaf0, y_47300 #e3e7ed / #dee3ef (B-R +5..17), c_27312 #eaedf0 vs q16 #d3d3d3, q15 #c6c7c7]
  // Cruise band: lighter and less saturated, fading out by the window belt (sideLow 0.10) and off the reveals next to
  // the glass (mainFS nearPane) [V: sany_22 #5f70e4 / #666cb3 (L107-117, s0.40-0.58); sany_12 #4d62e2; tlfl_IMG_9217
  // lens #5c67e7, wall top #5a59b9; tlfl_IMG_9206 band #7371bd / #686ad1 (h239-241); ucr_the-room-takeoff #6f88da, upper
  // #7d89be, belt #858897; was c03 #5c6ae5 / q16 #2334e1 (s0.84)] (lighting + integration r1). sideLed hue between the
  // raters' two fits (h~232) [D]; bandCut 0.8 kept: the suggested 0.55 washed the band to #9896d6 (L156 s0.30), 0.75
  // with the new tone read L127-157 s0.39-0.47 (c16) [D renders]
  // QA r3 (light): boarding sideLed [0.42, 0.46, 0.55] -> [0.48, 0.53, 0.66]: the economy window wall was neutral and
  // ~9 % under the official photo, whose wall under the lens is the brightest, slightly cool band [V: y_47300 #e2e4eb
  // L228-231 (B-R +9..11) vs q15 #d2d3d3 L210 (B-R 0); bins already matched, L214] -> q15 L222-223 [D render r3]
  // QA r4 (light): shaded whites cool blue-grey, lit faces unchanged: hemiBot [0.36, 0.37, 0.40] -> [0.31, 0.35, 0.47], wash
  // [0.25, 0.26, 0.28] -> [0.23, 0.255, 0.32] (with the crown x1.1 in mainFS) [V: y_47303 crown #a7adc2 (B-R +27) vs q17
  // #b2b3b3 (+1); py_37301 reveal sides #9ba6bc / #a0abbf (+33) vs q14 #bfbfc0; y_47301 wall #c2c9db (+25) vs q16 #d3d4d5;
  // c_27312 PSU band #c4c9cf (+11) vs q06 #e0e1e1]; binLo 0.8: the outboard bin doors' lower face (mainFS binK) [V: c_27312
  // bins L190-199 p10 168 vs q06 L211-218 p10 197; y_47301 L189 vs q16 L216] (lighting r4 medium x2). The raters' 0.72 also
  // took the q15 bins under y_47300's (L220 -> 209, p10 197 -> 177 vs photo L216 p10 200), whose bins are evenly lit [D]
  // QA L8 (light + integration): the r4 cool shift kept for the window side only: hemiBot / wash act on the sidewall, the
  // reveals and (half) the outboard bin doors (mainFS coolW); the seat level and the rest take hemiBotN / washN, the pre-r4
  // values [V: q06 seat zone B-R +16 vs c_27312 +8, shell tops +23 vs +11; q15 bins +8 vs y_47300 +0..+2; q16 wall +10 vs
  // y_47301 +14 kept] (integration L8 low, lighting L8 medium). tubSky [share, level]: the upper window tub takes the day
  // glow's hue at 0.6 of its light (mainFS) [V: y_47303 upper tub #a4a9be L170 (B-R +25) vs q17 L188-208 (+3..+7)]. sideLed
  // [0.48, 0.53, 0.66] -> [0.50, 0.57, 0.78], so the band under the lens keeps its blue after the ACES shoulder [V: y_47300
  // lens band rows 130-140 #e3eaf4 / #e2e8f5 (B-R +14..+18) vs q15 #dadbdd (+2)] (lighting L8 medium) [D renders fixL8]
  // QA L13 (integration medium, lighting run 4): beltK 0.55 = the ambient the flat window-belt lining keeps (mainFS u_beltK:
  // 0.55-1.6 m, facing in, under a lens, not the tubs, seen near head-on; with it the day-belt term drops 0.5 -> 0.15 there),
  // and sideLow 0 (was the 0.4 default): the lens light fades out over 0.95-1.55 m, so the pier falls from the lens to a
  // light grey at the window as in the photos instead of rising flat white to the sill in the ACES shoulder [V: y_47303 pier
  // 237 / 210 / 184 / 176 to the window centre; c_27300 pier L205; omaat_f8 THE Suite wall L202 vs q17 pier 235-241, q08
  // pier p50 241, q05 wall L240]. Tested [D fixL13 r_vB55S]: q08 pier p50 241 -> 209, q17 pier 229 -> 191 monotonic, its
  // surround p50 / p75 198 / 226 -> 193 / 211 (photo 183 / 199), q05 wall 240 -> 211; L235-245 share q03 12.5 -> 4.3 %, q08
  // 10.5 -> 2.1 %; the tubs (q17 176 / 159 / 162 vs y_47303 182 / 167 / 155), the far belt (q16 p90 237) and seat level held.
  // The analysts' 0.62 (gap4 SA, ungated) and 0.55 without sideLow 0 (gap4_mat beltLV: q17 pier flat 211-213 below row 60) [D]
  // QA L14 (lighting run 4): the belt dimming is now the same for every viewer (mainFS: no N.V or eye-distance gate) and acts on
  // the cabin ambient only, so beltK 0.55 -> 0.62 and lensLo [1.25, 1.30]: the lens wash fades in from 1.25 m (was 0.95), just
  // under the bins, so the pier falls from the lens as in the photo [V: y_47303 rows 24-96 189 / 181 / 174 / 170 / 172 vs q17
  // L14 195 / 186 / 184 / 186 / 191 -> 193 / 180 / 172 / 173 / 182; c_27300 pier L205 vs q08 209 -> 198; c_27312 far-left
  // wall 146-216 vs q06 236 -> 210]; lensLo 1.40 overshot (q17 rows 36-60 158 / 154) [D fixL14 t1]. seatCool / bleed / hueW /
  // tubHue: the cool cast of the official PY / Y photos at seat level, through the tone curve and in the lower window tub
  // (mainFS, QA L14); bleed = the seat-block blue at unit luminance (hue only: the gap analysis's [0.86, 0.95, 1.30] took 4 %
  // off the seat level, q18 median 169 -> 167 vs y_47305 183) [V: y_47300 seat back #2f3d66; B-R by luma band 175-200 /
  // 200-220 / 220-235 y_47303 +26 / +24 / +17 vs q17 +10 / +6 / +3 -> +21 / +19 / +15] [D gapT14 WBC / TUB; fixL14 t2]
  // QA lighting final touch (after the per-area final confirm on 1430d42): seatCool 1 -> 0.35 and bleed [0.90, 0.99, 1.36] ->
  // [0.965, 0.996, 1.13] (a third of L14's hue shift): the PY / Y seat level read denim / violet and the white seat plastics
  // blue [V: q14 PY back (260-400, 300-500) B/R 1.39 vs py_37301-03 1.22-1.36 -> 1.31; q15 back B/R 2.38 -> 2.19 (pre-L14 2.09);
  // q17 armrests B-R +14 -> +5 (y_47303 armrest 185 / 184 / 191); q15 seat-level whites +16 -> +8 (y_47300 -3)] (from_py /
  // from_econ final confirm, medium). fjCool (mainFS u_fjCool) = [THE Suite cool cut, THE Suite belt K, THE Room cool cut, THE
  // Room shell-post window fill]: THE Suite keeps the neutral shadow light, no belt dimming and a neutral lens wash, and its
  // bowls no tub-sky hue [V: f_17313 wall 226 / 228 / 227, bowl +1 and lighter than the wall vs q05 wall 199 / 204 / 214, s09
  // bowl +26]; THE Room takes 2/3 of the cool wash [V: c_27316 wall B-R +5..+12 vs b_jClose / s05 +14]; its posts by the wall
  // are no longer dimmed as the lining [V: c_27316 post L114-121 vs q07 L51-96] (from_suite / from_shell / from_room) [D touch]
  boarding: { label: 'Boarding', hemiTop: [0.97, 0.99, 1.03], hemiBot: [0.31, 0.35, 0.47], wash: [0.23, 0.255, 0.32], hemiBotN: [0.36, 0.37, 0.40], washN: [0.25, 0.26, 0.28], tubSky: [1.0, 0.6], led: [1.0, 0.98, 0.92], sideLed: [0.50, 0.57, 0.78], bandCut: 0.15, sideLow: 0, beltK: 0.62, lensLo: [1.25, 1.30], seatCool: 0.35, bleed: [0.965, 0.996, 1.13], tubHue: 0.8, hueW: [0.8, 0.72, 0.86], fjCool: [1, 1, 0.33, 1], binLo: 0.8, k: 1.05, exposure: 1.38, toe: 1 },
  // QA r2 (light): cruise sideLow 0.10 -> 0.30, the lavender wash reaches the window belt in THE Suite (the reveals by
  // the glass stay near-white through mainFS nearPane) [V: ml_DSC_1939-1 wall column y45 #6e9bfc (B-R +141), y150
  // #7a89be, belt y240 #888db0 (+40) vs cF03 belt #cccccf (+3)]
  // QA r4 (light): binLo 0.8 as boarding: in flight the cove-washed vault is clearly brighter than the bins [V:
  // lalf_room_119 vault L163 vs bins L97, lalf_room_120 vault L193 vs bins L120-158; c06 vault L157 vs bins L198-203]
  // QA L8 (light): the bins are the dim layer under the cove-lit vault in every in-flight photo: hemiBot [0.24, 0.24, 0.28]
  // -> [0.18, 0.18, 0.22], binLo 0.8 -> 0.45, ctrLo 0.5 (the centre bins' doors / undersides, mainFS binK) and fillLift 0.25
  // (the bin doors' small-e lift stayed at the Boarding level) [V: lalf_room_119 outboard bins #5f7692 L116 / #5b636f L98,
  // centre-bin underside #4c4e56 L79, vault #b7b1a2 L177; sany_22 centre-bin underside L68-85; tlfl_IMG_9217 #625c5a L94
  // vs c06 bins L183 / 176 under a vault at L221, c15 centre-bin underside L183] (lighting L8 medium). The raters' fit
  // (binLo 0.65, fillLift 0.45) gave c06 bins L155 / 161, c15 L166; 0.45 / 0.5 / 0.3 gave c06 L118 / 147, c15 L134 [D renders
  // fixL8 t1]; seat-level thirds move <= 2 L
  // QA L11 (light low): the overhead white balance neutral-warm: hemiTop [0.86, 0.88, 0.98] (B/R 1.14) -> [0.89, 0.885, 0.87]
  // (same luma 0.883, B/R 0.98) and a neutral hemiBotN / washN for the faces away from the window side (mainFS coolW; Cruise had
  // none, so the cool hemiBot / wash reached the bins and the seat level): the bins read lavender-grey, B-R +10..+13 (c06,
  // c15, c16), where the in-flight cove-lit overheads are neutral to warm [V: B-R lalf_room_119 bins -11 / vault -18, sany_22
  // outboard -12 / -10 / centre -7, lalf_room_4 -11, lalf_room_120 -7 / -27, tlfl_IMG_9217 -12 / -2; median of six ~-2]; the
  // lens band (sideLed) keeps its hue (question 7). The cove glints (mainFS coveC, from hemiTop) turn neutral-warm with it
  // [D gapT pC, L11rateL cN]
  // QA L13 (integration medium, lighting run 4): beltK 0.55 as Boarding (sideLow 0.30 kept: it carries the lavender belt):
  // cF03 below-window wall (90-150, 360-460) L199 B-R +26 -> L167 +35 [V: ml_DSC_1939-1 below the windows L146-186, B-R
  // +42..+71; target <= 175] [D fixL13]
  // QA L14 (lighting run 4): beltK 0.55 -> 0.32 with the dimming now on the cabin ambient only (mainFS): the lavender lens light
  // under the bins stays whole, so the upper wall keeps its blue [V: ml_DSC_1939-1 upper wall L153 s0.63 B-R +105 vs cF03 L109
  // +79 -> 119 +92] and the cabin light under it drops further: belt (90-150, 360-460) L167 +35 -> 149 +63 [V: L146-186, +42..+71],
  // frame median 108 -> 108 [V: 97]; at 0.48 (the analysis' estimate) the median rose to 113 [D fixL14 t2 C48 / C40 / C32]
  cruise: { label: 'Cruise', hemiTop: [0.89, 0.885, 0.87], hemiBot: [0.18, 0.18, 0.22], wash: [0.25, 0.26, 0.30], hemiBotN: [0.195, 0.19, 0.185], washN: [0.27, 0.265, 0.26], led: [1.0, 0.98, 0.92], sideLed: [0.08, 0.14, 1.35], bandCut: 0.8, sideLow: 0.30, beltK: 0.32, binLo: 0.45, ctrLo: 0.5, fillLift: 0.25, k: 0.95, exposure: 1.12, toe: 1 },
  // QA r2 (light): ANA's full-blue phase (safety video, after take-off, early night): cove LED, sidewall lens and vault
  // saturated blue-violet, the seat zone washed blue and dim, the galley ends warm (monFill), the screens lighting their
  // surround [V: sany_47 (SANspotter Y) cove #1d21bd / #2227cb s0.85, crown #181a39, seat backs #171a7a, galley #776349,
  // mean 29/28/81; ml_DSC_1945 (MileLion, THE Suite during the safety video) sidewall #5a61b2, console top #3b3e6e,
  // ottoman #454987, mean 81/79/111; ml_DSC_1946 bulkhead #493f97; ml_IMG_20200208_0717146 lavender-blue console].
  // Levels [D]: the raters' fit ([0.05, 0.06, 0.30] hemi, vault [0.04, 0.05, 0.35]) read 1.7x the sany_47 mean (bl16f
  // 50/60/139, crown #1a207e) with the THE Suite ottoman at L23 (ml #454987 L77) and the wall over-saturated (#7184eb vs
  // #5a61b2), so a darker deep-blue top (hemiTop, vault: crown #181a39), a lavender seat level (lowTint / lowGain, ml
  // ottoman / console G/R ~1.05, B/R ~1.9) and a weaker lens; emisGain as Night (signs dimmed). Second pass: the two
  // photos are exposed ~2x apart (sany_47 mean 29/28/81, ml_DSC_1945 81/79/111), exposure 1.7 sits between them, the
  // bin doors' fill lift at 0.4 (sany_47 dark bins under bright cove lines), seat level x1.6 (b8: Y mean 49/56/124,
  // F ottoman L26) [D renders]
  // QA r4 (light): the door / galley ends warm-lit, not blue: monFill [0.06, 0.05, 0.035] -> [0.20, 0.16, 0.10] and the
  // hemi x0.4 outside the seat zones (monHemi, mainFS) [V: sany_47 galley / door end #564a4d h346 s0.14, door zone
  // ~#776349 vs bl16 #393e6f h235]; scrOff 0.7: ~30 % of the seat screens lit [V: sany_47 ~6 of 25] (lighting r4 low x2)
  // QA L8 (light): vault [0.025, 0.028, 0.10] -> [0.018, 0.020, 0.060]: the vault centre between the cove lines read lighter
  // and more saturated than the photo's dark crown [V: sany_47 crown (400-560, 0-150) #141631 L24 s0.58 vs blue06 (430-520,
  // 0-60) #22266c L43 s0.68; the bins and cove already matched]; the raters' [0.016, 0.018, 0.065] read L32 s0.71 [D render
  // fixL8 v3] (lighting L8 low)
  // QA L10 (light medium): fLow = the seat-level light inside the open-topped THE Suite (mainFS u_fLow, F zone only): the suite
  // interior read 0.17-0.23 of the matched window wall where both MileLion photos show it at 0.36-0.47, violet-grey [V:
  // ml_DSC_1945 aisle-side box (80-230, 330-600) #2a243c L40, table L37, aisle pier L48; ml_DSC_1946 table L40 vs blueF03
  // L16 / 20 / 22]; 2.5 per the raters' scratch test (4.0 overshot: ottoman L97, whose top already reads ~1.2x the photos in
  // Boarding) [D fixL10]
  // QA L12 (light low): monFill [0.20, 0.16, 0.10] -> [0.24, 0.19, 0.11], monHemi 0.4 -> 0.1: the 40 % blue hemi the door / galley
  // ends kept outweighed the warm fill, so they read violet-grey under the blue cove lines [V: sany_47 door zones #836d4c L112
  // h36 B-R -56, #66574e L90 h22 B-R -25 vs bl16 door-4 zone #746a79 L110 h281 B-R +5, blue15 door-5 sides B-R +15 / +17];
  // monHemi 0 alone read too dark (bl16 L93); the THE Suite front wall keeps its half fill (fWall) [D L12rateL xbA / xbB]
  // QA L13 (integration detail, lighting run 4): darker overhead between the cove lines: fillLift 0.4 -> 0.25, binLo / ctrLo
  // 0.6 (the bin doors' lower faces, mainFS binK), vault [0.018, 0.020, 0.060] -> [0.016, 0.018, 0.045]: the bin faces read
  // evenly lit and the crown lighter and more saturated than the photo's dark grey-navy [V: sany_47 crown L25, outboard bins
  // L17, bins p50 25 vs blue15 crown L34, outboard bins L32; bl16 bins p50 39] -> blue15 crown 24, outboard bins 21; frames
  // vs sany_47 (cmp score) bl16 62 -> 50, blue15 68 -> 65, blue06 81 -> 82 (median 29 -> 21, top third 48 -> 41 vs 30 / 32),
  // blueF03 168 -> 168 [D gap4 r/BL; fixL13 r_bl]. The crown stays blue where the photo's is near-neutral (hue not closed)
  blue: { label: 'Blue', hemiTop: [0.035, 0.04, 0.21], hemiBot: [0.008, 0.009, 0.035], wash: [0.015, 0.015, 0.07], led: [0.06, 0.08, 1.0], sideLed: [0.05, 0.06, 0.70], bandCut: 0.8, sideLow: 0.6, vault: [0.016, 0.018, 0.045], lowTint: [1.8, 1.7, 1.0], lowGain: 1.6, fLow: 2.5, fillLift: 0.25, binLo: 0.6, ctrLo: 0.6, monFill: [0.24, 0.19, 0.11], monHemi: 0.1, cove: 0.35, k: 1, exposure: 1.7, screenGain: 0.6, scrSpill: 1, scrOff: 0.7, emisGain: 0.55, strips: true },
  // dining / sunrise, QA r2: ANA's amber phase is a saturated amber LED line on the bin lens and cove, amber-washed bin
  // faces and a much darker lower cabin, not a beige high key [V: ff_door-gap lens #ffa43d (h32 s0.76), bins #955b2d /
  // #673e1e (s ~0.7)]. Sunrise uses the same levels with a pinker LED [A: no ANA sunrise photo]
  // QA r3: led / sideLed inverted through ACES for #ffa33c at the cove / lens gains (the r2 [1, 0.22, 0.02] put G at
  // ~1.5 before ACES and clipped to lemon #fce04f) [D]; hemi softened (the ceiling and bins read #d9b77d / #b87130 at
  // s 0.4-0.7, not saturated orange) and the dim vault wash takes its own warm-beige colour [V: ff_seat-with-door-closed
  // ceiling #d9b77d, bins #7f6440; ff_door-gap bins #945a2a / #b87130]; lowTint neutralises the amber below 1.25 m
  // (hemi x lowTint = [0.81, 0.78, 0.72]) so seat-level ash stays grey and brighter than the bins [V: ff_door-gap ash
  // #afafaf / #acb1ba (s <= 0.08), grey shell #6f7982]; the lens light reaches the wall less red (sideWall) and not past
  // the window tops (sideLow 0) [A: no amber-phase sidewall photo, questions_lighting.md 2]
  // QA r1 (light): the amber reaches seat level, warm and dimmer, in every real photo of the phase: lowTint [1.3, 2.6,
  // 6.5] -> [1.0, 1.35, 2.0] (hemi x lowTint ~h28; [1, 1.25, 1.8] rendered the ash #624023 s0.64, a little over the
  // photos' s0.5-0.6) and 0.6 gain below 1.25 m (lowGain: d07 lower third L132 -> 90); lens light on the wall
  // down to half way past the windows (sideLow 0.5) in the hemi's amber (sideWall = hemiTop / sideLed share: the
  // sideLed that renders the clipped lens #ffa33c is near-red below the clip, and with the cool day window light it
  // left the lower wall pink, #635655 h6; sideWall 1 tried, salmon) [V: ff_seat-with-door-closed ash cabinet #ab7f58, shell #251f17, ottoman #2e2219;
  // ff_door-gap ash #b29f84 / #6b5946 at 1024 px; ucr_the-room-cabin ash #ae7134 / #885635, sidewall #ba895b-#bb8a60,
  // reveal shadow #b48357, bottom third L55; kn_room_35 ash fronts #804e10-#8f5c20] (lighting r1)
  // QA r2 (light + integration): (1) fillLift 0.35: the small-e fill lift on the PSU band / bin doors no longer glows tan
  // [V: ff_door-gap PSU band #603b1d L65, ucr_the-room-cabin #6f482a L79 vs q21 #ad7c42]; (2) vault [0.40, 0.15, 0.045]
  // (G/R 0.38, the led hue) so the door domes and the vault stay saturated after ACES [V: ucr ceiling #c89552 s0.59, far
  // door zone #c28440 s0.67 vs q21 #e8cf99 s0.34]; (3) lensCore: the lens core clips pale yellow, the frame's highlight
  // [V: ucr lens #fefed6, ff_door-gap #fefeb6]; (4) seat level brighter and less fiery: lowGain 0.6 -> 0.9, lowTint
  // [1.0, 1.35, 2.0] -> [1.0, 1.5, 2.6] (light G/R ~0.6, B/R ~0.4 on the ash), sideWall [0.4, 2.4, 4.5] -> [0.4, 2.8, 7.0],
  // sideLow 0.5 -> 0.65 [V: ucr ash #ae7136 L122 / #895636 L95, pier #bc895e L145, reveal #b58459; ff_seat-with-door-
  // closed ash cabinet #ab7f58 L133 vs dining_room ash #593717 L60 s0.74]; (5) screens spill at half the night level.
  // Tuned on renders [D]: the raters' fillLift 0.35 left the band at L100 (q21), so 0.15; lowGain 0.9 left the
  // dining_room ash at L84 and lowTint [1.0, 1.5, 2.6] read s0.4-0.5 against ucr's foreground ash #9a6330 s0.69, so
  // lowGain 1.4 (the photos are auto-exposed: seat level ~0.7-0.85 of the ceiling, the render 0.55) with lowTint [1.0,
  // 1.42, 2.3]; vault x0.9 (q21 door dome L164 s0.64 vs ucr #c89552 L156)
  // QA r3 (light, high): the amber light ordering was upside down: r2's seat-level lift (lowTint [1.0, 1.42, 2.3] x1.4,
  // sideWall [0.4, 2.8, 7.0]) read pale cream (s0.23-0.39) under a dark brown overhead, while every photo of the phase
  // has the cove-washed ceiling and bins brightest and seat level darker in the same amber [V: ucr_the-room-cabin vault
  // #c69a58 L159 s0.55, bin faces #ca9754 L158, bin undersides #855a2b L96, wall #b7855a L141 s0.51, ash #a0652e L110
  // s0.71; ff_seat-with-door-closed ceiling #d6ae72; kn_room_36 reveals #68411b, ash #7b4710 s0.87]. Now lowTint [1.0,
  // 1.08, 1.2] x0.8 (raters' fit), the vault wash floored at e 0.14 (mainFS u_vaultE) in a paler vault hue [0.32, 0.145,
  // 0.047] (G/R 0.45, was 0.38), hemiBot x1.4 (bin undersides), sideWall [0.6, 2.2, 4.2] / bandCut 0.2 (the wall under
  // the lens less red). Renders r3 [D]: dd (12H) ash #8f602e L103 s0.68 (was #b89c70 L160 s0.39), wall at the window
  // tops #b07f50 L134 s0.54, bin undersides L74-84 (photo L96; the vault is out of this frame); d06 vault L140-147 s0.64
  // (was L68-73 s0.80), bins L152-163; q21 door dome #cd9e51 s0.60 (ucr #c89552 s0.59), closed-shade pier L139-174
  // s0.57-0.65 (was L161-199 s0.32-0.42)
  // QA r4 (light): binLift [0.055, 0.04, 0.02], 0.6 of the lighting rater's hemiBot step [0.21, 0.10, 0.035] -> [0.30,
  // 0.165, 0.07], applied only above ~1.6 m in the seat zones (mainFS): the bin faces seen from a seat read dark and
  // over-saturated (dd #86582a L95 s0.69, d06 #835325 L90 s0.71) where the photos show them as the bright, soft-amber
  // layer [V: ff_seat-with-door-closed bins #b99662 L154 s0.47; ucr_the-room-cabin bins from below #b3834b L138 s0.58;
  // PSU band kept dark: ff_door-gap #603b1d L65, ucr #6f482a L79]; on the whole hemiBot it also lifted the seat level and
  // the door zones (q21 median 134 -> 142 vs ucr 86); the full step also took d06 (frame median 77 -> 89, kn_room_35 68)
  // past the level both raters had matched, and the integration rater reads the dd bins (L101) inside the photos' L76-124,
  // so 0.6 of it [D renders fixL7] (lighting r4 medium)
  // QA r4 (light): tub: the recessed window tub keeps LIGHT_TUNE.tubWash of a pier's light where the window light is dim
  // (mainFS tubRef) [V: ucr_the-room-cabin reveals L124-137 vs wall L147; q21 tub #b06a35 L117 s0.70 beside a pier at L190]
  // (lighting r4 medium)
  // QA L8 (light): binLift on the bin door faces only (mainFS: outboard binO and centre cBin, not the undersides / PSU band)
  // and at 2x the raters' full step, [0.055, 0.04, 0.02] -> [0.22, 0.15, 0.07] (G/R 0.68, paler than hemiBot, so the bins
  // desaturate): restricted to the doors, the step no longer lifts the seat level or the door zones; the raters' full step
  // moved the dd left bins only L89 -> 96 [V: ucr_the-room-cabin outboard bins #9e7240 L120 s0.59; ff_seat-with-door-closed
  // bins #b99662 L154 s0.47 vs dd #7e5227 L89 s0.69] -> d06 left bins L102 s0.66 -> L113 s0.62, right L135 -> 147 s0.56,
  // median 81 (rater cap 85); dd (seated, mostly undersides, which keep the r4 level) L89 -> 93; q21 median 135 (cap 138)
  // [D renders fixL8 final2] (lighting L8 medium)
  // QA L9 (light): ctrLift 3: the centre bins' doors take 3x binLift (mainFS), so they reach the outboard doors' level
  // [V: ucr_the-room-cabin centre-bin doors #c79352 L154 s0.59 vs dd #a3773f L125, d06 centre L113 vs outboard L147];
  // a uniform x1.5 / x2 binLift took the d06 outboard doors past the photos (L155 / 161 vs 154) [D L9rate] (lighting L9 medium)
  // QA L11 (light): hueK 0.6 = the share of hue-preserving tone in the upper mid-tones (mainFS u_hueK): per-channel ACES turned
  // the cove-lit amber yellower as it brightened [V: hue by luma band L100-150 / 150-200 ucr_the-room-cabin h28.9 / 34.1 vs dd
  // h34.4 / 39.9; ucr wall h26-28 vs dd h33.5]; seat level (< sRGB ~97) and the lens core (> 0.95) unchanged [D gapT pD]
  // QA L12 (light low + integration medium): dayN 0.75 = the share by which the window belt beside an open day pane turns
  // daylight-neutral (mainFS u_dayN; 0 with the shades closed and at sunset) [V: kn_room_35 / 36 open-pane surround #a49b98 /
  // #aea9a7 s0.04-0.07 vs dF03 wall #ddb298 s0.31] [D gapT3 V2]
  // QA L13 (light medium, lighting run 4): sideLow 0.65 -> 0 (Sunrise 0.5 -> 0): the lens light now fades out over 0.95-1.55 m
  // (mainFS mix(u_sideLow, 1, ...)), so the wall falls off below the window: it ran flat at 1.0x of the wall under the lens down
  // to ~0.4 m and was the brightest surface of q21 (L186 vs bins L146, ceiling L163) [V: ucr_ana-business-class-wing-view wall
  // L109 -> 89 -> 63 by the console (0.58-0.82x, h31-34); sany_42 L118 -> 92 -> 82 (0.69x); ucr_the-room-cabin wall L137-147
  // under the bins L154-158 and the vault L159]. The r2 / r3 lens level below the window carried the amber at seat level
  // when lowTint [1.3, 2.6, 6.5] neutralised the hemi there; with lowTint [1.0, 1.08, 1.2] the hemi keeps the amber, so the
  // falloff is a level ramp, not a hue cut (q21 h27 -> h31-32 s0.40-0.44) [D L13rateL xv, gap4 r/AM; fixL13]
  dining: { label: 'Dining', hemiTop: [0.62, 0.30, 0.11], hemiBot: [0.21, 0.10, 0.035], binLift: [0.22, 0.15, 0.07], ctrLift: 3.0, wash: [0.30, 0.14, 0.05], led: [0.55, 0.042, 0.009], sideLed: [1.25, 0.10, 0.02], sideLow: 0, sideWall: [0.6, 2.2, 4.2], bandCut: 0.2, vault: [0.32, 0.145, 0.047], vaultE: [0.14, 1], lowTint: [1.0, 1.08, 1.2], lowGain: 0.8, fillLift: 0.15, lensCore: [0, 0.55, 0.15], scrSpill: 0.5, tub: true, k: 0.9, exposure: 1.3, strips: true, hueK: 0.6, dayN: 0.75 },
  // night, QA r2: THE Room in service at night is near-black and neutral-warm; the light comes from the IFE screens, the
  // warm strip under each screen, small white reading lamps and amber PSU lamps [V: ucr_room-night-lighting ceiling
  // #1e1915, sidewall #24211c, bins #322a1f, PSU lamp #9e5e38, strip #ffeb97, mean RGB 39/34/33]. The blue night refs
  // used in r1 (roame_7672, sany_10) were boarding shots on the ground (daylight in the windows), so not the night scene
  // QA r3: cove / lens saturated amber (was warm white) [V: stwis_img_6223 cove #dc9340 / #b0671a (h25-32, s0.71-0.85),
  // ucr PSU lamp #9f5e39], the lens light kept to the upper wall (ucr sidewall #24211c); vault wash the same amber hue
  // (G/R 0.36, as the photo's dim amber h25-30), mid-vault <= #2a2219 [D]; hemi unchanged (image mean already matches
  // ucr 39/35/33)
  // QA r1 (light): the r3 amber came from one cove sample (stwis_img_6223) and washed the vault and the whole sidewall
  // orange (#26150a / #301607, s0.73-0.87); none of the four real night photos looks like that. Neutral-warm cove and
  // vault (G/R ~0.85; vault 0.020 rendered the mid-vault L12 vs ucr #211a14 L27 at the same place, so 2.5x), a cool-grey
  // dim lens light down the wall (sideLow 0.6), and a dim neutral fill in the galley /
  // door zones (monFill: #c8c0b4 at ~0.25 of the boarding level, after exposure) [V: ucr_room-night-lighting ceiling
  // #352f2a / #16110e (s0.2-0.38), bins #312820, sidewall #23201c, lower sidewall #4f515b, far galley wall #645f57;
  // sany_40 ceiling #42413d-#605d5f (s <= 0.08), sidewall #434c67-#8d9bc1] (lighting r1); hemi, screens, strips unchanged.
  // Exposure 2.2 -> 2.5: q20 median L25 vs ucr 30, and economy at night (sany_40, median L58) read about half as bright
  // as the photo (wall L25-43 vs #494f67 L80, ceiling L39 vs #474647 L71) [D: renders r1b]
  // QA r2 (light): the IFE screens light their surround (scrSpill 1, mainFS u_scrP) [V: ml_IMG_20200208_1919534 THE Suite
  // housing #251e1e, ucr_room-night-lighting near wall #302218]; emisGain 0.55 = the r2 night sign level
  // QA r3 (light): led [0.050, 0.042, 0.034] -> [0.030, 0.025, 0.020] and the cove / vault wash capped at e 0.09
  // (vaultE): the cove panel over the outboard bins was the brightest surface after the screens [V: ucr_room-night-
  // lighting ceiling L13-55 throughout vs q20 panel #a39a8c L155]; with the screen spill kept below 1.5 m (mainFS) the
  // bins are back to warm dark [V: ucr outboard bins #2f271e L40 h31]: q20 centre bins #33302c L49 h29 (was #424448
  // L68 h225), outboard #2a2724 L40 h30, cove panel L69 (was L117), mid-vault L28, median 32 [D render r3]
  // QA r4 (light): (1) the cove LED lines warm and at half level (led [0.030, 0.025, 0.020] -> [0.030, 0.021, 0.009]; mainFS
  // caps the line's e at 0.5 when vaultE.y < 0.1) [V: sany_25 pale-yellow line core #fef2ad; ucr_room-night-lighting no lit
  // cove line, upper band p99 58 vs q20 #dcdcda L220]; (2) vaultE cap 0.09 -> 0.045: the seat-zone vault eFn went from
  // 0.02-0.08 to 0.06-0.13 (07b polish B), so the cap bound across the vault (vault mid L29 -> 62, above the bins L41) [V:
  // ucr ceiling L13-55, bins ~L43] (from_ceiling polish B); (3) scrOff 0.7: ~30 % of the seat screens lit [V: sany_40
  // < 1/3 lit; ucr only the passenger's own] (lighting r4 low)
  // QA L11 (light low): sideLed [0.018, 0.021, 0.032] (B/R 1.8) -> [0.022, 0.021, 0.020]: the window wall read cool-blue where
  // the night photos are neutral to warm [V: B-R ucr_room-night-lighting window wall (650-930, 220-330) -4..0, ml_IMG_20200208_
  // 1915537 window side -13, ml_1919534 -14 vs q20 +15, nF03 +15]; the level comes mostly from the other terms (a dimmer lens,
  // [0.016, 0.015, 0.014] with sideLow 0.4, moved the q20 wall only L66 -> 61), so only the hue [D L11rateL xnA / xnB]. A cooler
  // economy night (question 8) would be a zone tint, not this shared lens colour
  // QA L12 (light): scrCol [0.30, 0.40, 0.55] (B/R 1.83) -> [0.34, 0.40, 0.47] (same luma) and scrWall 0.5 = the share of the
  // screen spill the sidewall faces lose (mainFS u_scrWall): the window wall's level and cool cast came from the spill, not the
  // lens [V: ucr_room-night-lighting wall L47 B-R 0; ml_IMG_20200208_1915537 window wall L67 B-R -15, under-screen L40 B-R -3
  // vs q20 wall L67 B-R +5, nF03 L75 +6, under-screen +9]; the colour between the base and a warm [0.42, 0.40, 0.36] (N1,
  // under-screen -23) at ml's -3 [D gapT3 N3: q20 wall L55 B-R -5, frame mean 33 (ucr 35); nF03 wall L60 -5]. Blue keeps the
  // calibrated spill (the wall factor there took blueF03's wall 96 -> 88 vs ml_DSC_1945 L103, N2)
  sleep: { label: 'Night', hemiTop: [0.030, 0.027, 0.024], hemiBot: [0.010, 0.009, 0.008], wash: [0.012, 0.010, 0.008], led: [0.030, 0.021, 0.009], sideLed: [0.022, 0.021, 0.020], sideLow: 0.6, vault: [0.050, 0.043, 0.035], vaultE: [0, 0.045], monFill: [0.060, 0.055, 0.047], cove: 0.35, k: 1, exposure: 2.5, readingLights: true, strips: true, screenGain: 0.6, scrSpill: 1, scrOff: 0.7, emisGain: 0.55, scrCol: [0.34, 0.40, 0.47], scrWall: 0.5 },
  // QA r1 (light): sunrise follows dining at seat level (sideWall = hemiTop share, sideLow 0.5). QA r2: as dining, the
  // fill lift off the PSU band (fillLift 0.15), the saturated vault, the pale lens core, lowGain 0.6 -> 1.4 and lowTint
  // [1.0, 1.3, 1.6] -> [1.0, 1.4, 1.95] [A: no ANA sunrise photo; dining's sources and levels]
  // QA r3 (light): as dining (lowTint [1.0, 1.08, 1.2] x0.8, hemiBot x1.4, vault floor / hue, bandCut 0.2) [A: no ANA
  // sunrise photo; dining's sources]
  // QA r4 (light): binLift and tub as dining [A: no ANA sunrise photo; dining's sources]. QA L8: binLift as dining. QA L9:
  // ctrLift as dining. QA L11: hueK as dining. QA L12: dayN as dining. QA L13: sideLow 0.5 -> 0 as dining [A: no sunrise photo]
  wake: { label: 'Sunrise', hemiTop: [0.62, 0.30, 0.16], hemiBot: [0.21, 0.10, 0.05], binLift: [0.22, 0.15, 0.07], ctrLift: 3.0, wash: [0.30, 0.14, 0.07], led: [0.55, 0.05, 0.03], sideLed: [1.2, 0.11, 0.06], sideLow: 0, sideWall: [0.42, 2.25, 2.2], bandCut: 0.2, vault: [0.32, 0.145, 0.047], vaultE: [0.14, 1], lowTint: [1.0, 1.08, 1.2], lowGain: 0.8, fillLift: 0.15, lensCore: [0, 0.55, 0.15], tub: true, k: 0.9, exposure: 1.3, hueK: 0.6, dayN: 0.75 },
};
// winExp: the view behind the glass at interior exposure; cabin photos show day windows near-white with a glowing
// reveal (tlfl_IMG_9217 / 9518, pane ~#eef3f8) [V]; eases back to 1 when the eye is at the window (looking out)
const SKIES = {
  // QA r3: winExp 1.6 -> 4.0: day panes must be the brightest thing in a cabin view, near-white against the wall
  // [V: c_27316 pane #ffffff vs wall #d1d1d1-#e2e2e2; y_47300 #fcfcfb; tlfl_IMG_9217 #fefefc]; 3.0 (rater) still left the
  // deep-blue sky reading #c4d8eb in the q03 pane [D]. Deeper day sky for the look-out view (winExp eases to 1 at the
  // window) [V: F-GSQR_1/_2 zenith #114892-#2472ca, from_exterior 2].
  // Exterior w5 (user: deep-blue cruise sky): zenith / horizon fitted with skyK 12 to #8fb8e6 (1 deg) #5d8cc4 (3) #3a66a0
  // (8.5) #2a4f86 (15) #1f4274 (25), between F-GSQR_1 and _2 [V photos, D fit].
  // QA L11 (integration): winExp 4.0 -> 5.5 with the pane transmittance now before the tone curve (LIGHT_TUNE.glassT): the
  // cloud deck in the economy panes still sat just under the clip [V: y_47303 pane L252 vs q17 pane boxes p50 248; share > L250
  // q03 0.2 % vs f_17306 2.1 %] -> q17 252 / 253, q03 1.0 %, frame means within 0.5 L; the look-out view keeps 1 [D fixL11 w55,
  // after]; 7 flattened the deck to 255 with no frame gain [D w7]
  // extBounce = the lit deck seen by the exterior's undersides (0.55 x cloudLit) and extSun the exterior's sun scale
  // (the sun side of the cowl saturated at 5.2) [D: from_exterior 1 / 6; alv_ANA77W_NH211_26K cowl #9fabb7-#a9c0ce]
  day: { label: 'Day', sunEl: 30, sunAz: -60, sun: [5.2, 4.9, 4.4], zenith: [0.019, 0.05, 0.095], horizon: [0.20, 0.37, 1.0], skyK: 12, haze: [0.55, 0.66, 0.85], cloudLit: [1.25, 1.25, 1.25], cloudShade: [0.62, 0.68, 0.78], skyTop: [0.55, 0.68, 0.95], skyBot: [0.55, 0.55, 0.58], extBounce: [0.69, 0.69, 0.69], extSun: 0.6, winGlow: [0.45, 0.52, 0.62], winExp: 5.5, lookExt: 0.04, sunVis: 1, night: 0, sheer: 1.0 },
  // QA r3: dim blue-grey deck under a narrow orange horizon band, blue upper sky [V: Air_France_777-300ER_Greenland_
  // Sunrise deck #50595d-#646a67, band #d2a46d, sky #9cabaa; Emirates_77W_wing_view / alv_7282 zenith #527dc2]; dark cool
  // deck bounce and a grazing sun at 0.35 on the exterior, so the wing takes the sky colour (from_exterior 3)
  // QA r1 (light): a dim blue deck, not flat grey (haze / cloudLit), and a lighter, greyer exterior sky fill with a
  // weaker grazing sun (extSun 0.35 -> 0.25) so the wing reads grey-blue, not royal blue [V: omaat_f73 dusk deck #3d608b
  // (s0.56), sky #346cb1, thin warm horizon band; alv_7282 wing ~#6f83b7 vs s26K #3a4474] (lighting r1, from_exterior 8;
  // the suggested skyTop [0.22, 0.25, 0.42] rendered the 19A wing mauve-grey #615564 h287 under the red sun [D])
  sunset: { label: 'Sunset', sunEl: 5, sunAz: 110, sun: [4.2, 2.2, 0.9], zenith: [0.08, 0.14, 0.42], horizon: [1.1, 0.55, 0.30], haze: [0.10, 0.15, 0.24], cloudLit: [0.08, 0.12, 0.20], cloudShade: [0.018, 0.024, 0.034], skyTop: [0.28, 0.34, 0.60], skyBot: [0.4, 0.26, 0.2], extBounce: [0.07, 0.08, 0.10], extSun: 0.25, winGlow: [0.22, 0.12, 0.08], sunVis: 1, night: 0, sheer: 0.7 },
  night: { label: 'Night', sunEl: 38, sunAz: -40, sun: [0.07, 0.08, 0.12], zenith: [0.004, 0.006, 0.016], horizon: [0.02, 0.028, 0.05], haze: [0.018, 0.022, 0.036], cloudLit: [0.05, 0.055, 0.07], cloudShade: [0.012, 0.014, 0.02], skyTop: [0.02, 0.025, 0.04], skyBot: [0.01, 0.01, 0.015], extBounce: [0.028, 0.030, 0.038], extSun: 1, winGlow: [0.0, 0.0, 0.0], sunVis: 0, night: 1, sheer: 0.06 },
};
// QA r3 ambient-occlusion tuning [D: q06 / q15 / q03 / q05 / q14 against c_27312, y_47300, omaat_f11, f_17313,
// py_37301]: hemi = unoccluded share of the hemisphere fill (was 0.15), bounce = interreflection gain, emitLens /
// emitCtr = sky value of the air under the outboard bins (sidewall lens band) and under the centre bins, kAttF = voxel
// attenuation inside THE Suite zone (1.35 elsewhere), fLift = share of the AO lifted toward 1 inside the suites (shader)
// QA r3 (integration): azim / slope = sweep azimuths and cells sideways per layer (was 8 / 1), floorBlur = layers that
// take two extra i / k blur passes (computeAO). The raters' slope 0.5 (63 deg rays) also opened the economy row gaps:
// q15 foreground pans L67 -> 75 and bottom band < 30 26 -> 20 % (y_47300 pans L78 at 0.85x the render's exposure, econ
// w34: pans 15-25 % light); at slope 1 they hold (L68, 26.6 %) and the 16 bilinear azimuths + floor blur keep the
// aisle clean (q06 aisle p10 51, 1 % < 30) [D renders r3s]
const AO_TUNE = { hemi: 0.22, bounce: 1.0, emitLens: 0.45, emitCtr: 0.35, kAttF: 0.8, fLift: 0.35, azim: 16, slope: 1, floorBlur: 5 };
// QA r1 (light): cove = gain of the two cove LED line lights in the interior specular (mainFS coveSpec) [D: rim
// highlight ~1.3x the face on THE Room shell caps (c_27312), armrest p99 >= 240 (y_47303)]
// QA r3 (integration): sheen = gain of the grazing sheen lobe on SHEEN materials (mainFS) [D: q17 / q16 flaps against
// y_47303 / y_47301, q15 head-on unchanged]
// QA r4: tubWash = floor of the recessed window tub, as a share of a pier's hemi + wash (lighting r4: amber reveals
// vs ucr_the-room-cabin) [D], in the moods with tub: true (the amber phase) only: in Night and Blue it lit the tubs
// flat and pale beside dark piers (q20 tub pixels L28 -> 55 vs ucr_room-night-lighting L23; bl16 / blue06 / nF03 alike,
// fixL7 after4) [D]; lookOut = interior exposure cut at the glass (integration r4: q12 vs ucr wing view) [D]
// QA L8 (integration): ssao = [disc radius m, strength, bias m, range m] of the screen-space contact AO (mainFS ssaoF,
// depth pre-pass in render), ssaoMix = its weight on the diffuse ambient, ssaoAng = angle bias, ssaoDither = per-pixel turn (L9: 1 = interleaved gradient noise; off)
// [D renders fixL8 ss1-f3: the integration rater's strength 0.7 / range 0.15 moved the q06 thin dark-line share only 1.81
// -> 2.00 % (c_27312 4.77) and q13 0.55 -> 0.58 (py_37302 2.77); strength 6 / range 0.10 / mix 0.9 reach q06 ~3.5, q13 ~1.6]
// QA L9 (integration medium): range 0.10 -> 0.07 m with full weight only up to ssaoIn x the range (2 cm; mainFS ssaoF), so
// the fixed disc no longer prints stepped ghost outlines 1-10 cm behind the THE Suite monitor and the THE Room headrest
// flaps [V: omaat_f13, c_27315]; ssaoDither stays 0 (a per-pixel turn drew dot grain without a blur pass) [D fixL9]. ssaoLow
// = the extra disc / range scale below the headrests, off the sidewall (mainFS kR; lighting L9 low: PY contact darks) [D]
// ssaoEase = the AO-volume range over which the contact AO eases in (mainFS sW; L8 [0.05, 0.4]): with the far taps gone the
// frames read 1-3 L lighter than L8 (q06 p5 28 -> 31, c_27312 16); [0.02, 0.25] lets it reach the lower pockets again and
// holds q09 p5 at 32 (c_27314 36; [0, 0.12] took it to 30) [D fixL9 tss6]
// QA L10 (integration medium): ssaoTaps 8 -> 12 (every third one only where the capped disc spans > 10-14 px, mainFS ssaoF) and
// ssaoCap = the disc (and range) capped at 16 px on screen (aft of THE Room only above the seat backs), strength 6 -> 8: the
// stepped bands above the THE Room headrest flaps and the hard stripes on surfaces near the eye are gone (q10 x 650 rows
// 378-410 mean L68 -> 82, rows 398-410 54 -> 75, 380-384 63 -> 86; L8 83-94; y_aisle_fwd row 300: 13 steps > 6 L, max 101 ->
// 8 / 53, as without the AO) and some contact lines come back (thin dark-line share q03 1.37 -> 1.51 %, q05 1.22 -> 1.26,
// q06 2.49 -> 2.68, in-flight omaat_f2 / f5 / f11 / f13 / f40 1.79-2.85; q13 0.73 -> 1.01) with f_ink_seated row 320 at 147
// (>= 130: no monitor ghost frame); frame time at Sharp +1-4 %. Tried [D fixL10 t1-t19]: a 12 px cap (bands gone but q03 1.08 %), the raters' ssaoIn 0.55 (q03
// 1.43-1.51 % but the monitor's stepped ghost frame back: f_ink row 320 114-124), an exp(-k occ) response (lines lost: q03
// 0.75 %), a 3.5 cm disc (curtain steps 21), the range unscaled by the cap (ghosts: f_ink 108, y_aisle_fwd max step 132), a
// tap weight by height over the face plane (f_ink 156-162 but q03 0.89-1.13 %), 12-16 taps everywhere (frame time +7-11 %), the
// cap on the PY / economy seats as well (q14 frame 1 L lighter, its seat shells' shade gone). The per-pixel turn with a
// depth-aware blur would smooth the rest but needs new full-screen passes (not in this run's brief; questions_lighting 13)
// QA L11 (integration + shell): glassT = the day-pane transmittance, applied to the sky and the exterior before the tone curve
// (mainFS / skyFS u_glassT) instead of the old display-space multiply pass (now x-ray only), which capped a clipped day sky at
// 255 x tint (shell w18's [0.985, 0.99, 1.0]: G 252; the old [0.93, 0.95, 0.96]: G 242, the most frequent pixel value in q03 /
// q07) [V: c_27316 pane #ffffff, y_47300 #fcfcfb, y_47301 pane L251; p99 c_27312 255, y_47301 254 vs q16 247]. Value = 07_shell's
// pane tint (w18) raised to 2.4: below the clip the ACES + sRGB slope makes a pre-tone x t^2.4 ~ the display x t, so every pane
// below sRGB ~225 and the look-out view keep the shell-rated level (q12 frame mean 124.9 -> 124.9, wing 152 -> 151) while a
// bright sky clips (q14 pane p50 249 -> 253; share > L250 q09 0.18 -> 0.67 %, q14 0.45 -> 1.20 %, q16 0.77 -> 1.13 %) [D fixL11
// v1]; the old tint^2.4 [0.84, 0.884, 0.906] also took the q12 view back to its L11 level (mean 122.4) but the sub-clip panes
// under the shell's (q17 pane p50 248 -> 245, q07 share > L235 7.7 -> 7.4 % vs c_27316 9.0 %) [D fixL11 a1]. rim = the cove-line
// rim lobe (mainFS u_rimK: gain on the fillets, 1 = lobe on the material roughness, metal cut) [D gap3 v_rimG2, fixL11]
// QA lighting final touch (from_shell fA-2, from_exterior final confirm, low): in the look-out (eye at the glass) the window-belt
// dimming lifts to 1 (render(): u_beltK), so the lining round the pane is not charcoal [V: q12 surround (100-180, 250-350) L123
// at L13 -> 70 vs ucr_ana-business-class-wing-view surround L104-125], and the day exterior takes SKIES.day lookExt (4 %) less
// exposure there [V: w17K near wing 214-217 vs KN41 187 / 195 / 208; w19A stays at 170 / 179 / 195]. lookOut 0.85 -> 0.86 (L14's
// 0.85 made up for the belt dimming on the lining, now lifted here): at 0.85 the frame-edge reveal (0-120) read 133 [V: ucr
// L104-110] [D touch v3 at 0.85: q12 post 70 -> 113, reveal 110 -> 133, pier (120-290) 87 -> 109, frame mean 116.5 -> 122.8]
// QA L14 (lighting run 4): lookOut 0.86 -> 0.85. The window-belt dimming (mainFS u_beltK) is now the same for every viewer, so
// it also reaches the lining seen at grazing from the look-out eye, which L13's N.V gate had left out: q12 frame mean 116.4 ->
// 114.2, left reveal (0-120) L112 -> 100 [V: ucr_ana-business-class-wing-view reveal L104-110]; at 0.85 the frame mean is back to
// 116.4 and the reveal reads 103 [D fixL14 t5 LK86 / LK85 / LK84]
const LIGHT_TUNE = { cove: 1.0, sheen: 1.35, sheenTint: 0.3, tubWash: 0.7, lookOut: 0.86, ssao: [0.05, 8, 0.006, 0.07], ssaoMix: 0.9, ssaoAng: 0.25, ssaoDither: 0, ssaoIn: 0.3, ssaoLow: 0.5, ssaoEase: [0.02, 0.25], ssaoTaps: 12, ssaoCap: 16, glassT: [0.964, 0.976, 1.0], rim: [2.0, 1, 0] };
// QA r3 (integration): floor contact map (computeAO): cell size (m; 6 m x 59 m -> 200 x 1973 texels, under the 2048
// texture minimum), marking height above the floor and the darkening at a base (mainFS) [D]
const CONTACT = { cell: 0.03, h: 0.2, k: 0.55 };
// Shade states per window: 0 open, 1 half (manual) / sheer (electric), 2 closed (manual) / blackout (electric)
const SHADE_STATE = {
  label: (w, lv) => (w.electric ? ['open', 'sheer blind', 'blackout'] : ['open', 'half down', 'closed'])[lv],
  T: (w, lv) => (lv === 0 ? [0.92, 0.92, 0.92] : w.electric ? (lv === 1 ? [0.30, 0.29, 0.27] : [0.02, 0.02, 0.02]) : (lv === 1 ? [0.92, 0.92, 0.92] : [0.03, 0.03, 0.03])),
  open: (w, lv) => (lv === 0 ? 1 : lv === 1 ? (w.electric ? 0.35 : 0.55) : 0),
};

class Scene {
  constructor(gl, opts = {}) {
    this.gl = gl;
    this.q = opts.quality || 'high';
    const t0 = performance.now();
    this.layout = buildLayout();
    buildAtlas(this.layout);
    this.tex = {
      detail: gl.textureArray(buildDetailLayers(256), 256),
      photo: gl.textureArray(buildPhotoLayers(256), 256),
      atlas: gl.texture2D(ATL.canvas, { srgb: false }),
      cloud: gl.texture2D(buildCloudNoise(256), { w: 256, h: 256 }),
    };
    this.shell = buildShell(gl, this.layout);
    this.bins = buildBins(gl, this.layout);
    const sr = buildSeats(gl, this.layout);
    this.seats = sr.meshes; this.seatGroups = sr.groups;
    this.mono = buildMonuments(gl, this.layout);
    this.ext = buildExterior(gl);
    this.progs = {
      main: gl.program(SH.mainVS, SH.mainFS),
      depth: gl.program(SH.depthVS, SH.depthFS),
      sky: gl.program(SH.skyVS, SH.skyFS),
      glass: gl.program(SH.mainVS, SH.glassFS),
      glow: gl.program(SH.glowVS, SH.glowFS),
    };
    this.emptyVAO = gl.gl.createVertexArray();
    gl.use(this.progs.main); gl.set('u_fillLift', 1); gl.set('u_sheen', LIGHT_TUNE.sheen); gl.set('u_sheenTint', LIGHT_TUNE.sheenTint); gl.set('u_vaultE', [0, 1]);   // the studio may draw before the first cabin frame
    gl.set('u_binLo', 1); gl.set('u_ctrLo', 1); gl.set('u_ctrLift', 1); gl.set('u_monHemi', 1); gl.set('u_fLow', 1);   // QA r4: neutral values for the same reason
    gl.set('u_glassT', [1, 1, 1]); gl.set('u_hueK', 0); gl.set('u_rimK', [0, 0, 0]); gl.set('u_dayN', 0); gl.set('u_scrWall', 0); gl.set('u_beltK', 1); gl.set('u_seatCool', 0); gl.set('u_bleed', [1, 1, 1]); gl.set('u_lensLo', [0.95, 1.30]); gl.set('u_tubHue', 0); gl.set('u_hueW', [0, 0.86, 0.97]); gl.set('u_fjCool', [0, 0, 0, 0]);   // QA L11: no pane tint, plain ACES, no rim lobe (the studio draws with u_exterior 1)
    this.buildGlows();
    const sm = this.shell.meshes;
    this.opaque = [
      sm.shell, sm.upper, sm.revealR, sm.revealL, sm.shadeBtns,
      sm.shade_manual, sm.shade_sheer, sm.shade_blackout, sm.shadeRail_manual, sm.shadeRail_sheer, sm.shadeRail_blackout,
      ...Object.values(this.bins), ...Object.values(this.seats), this.mono.mesh,
    ];
    this.computeAO();
    this.winTex = null;
    this.winLevels = this.layout.windows.map(() => 0);
    this.mood = 'cruise'; this.sky = 'day'; this.globalShade = 0;
    this.xray = false;
    this.shadowDirty = true;
    this.updateWindowLUT();
    this.buildTime = performance.now() - t0;
  }

  // ---------------- ambient visibility volume ----------------
  computeAO() {
    // ~8.3 cm voxels (QA r1: 10 cm cells could not resolve the 0.1 m footwells / console gaps) [D]
    const nx = 72, ny = 34, nz = 712;
    const min = [-3.0, 0, 2.6], size = [6.0, 2.8, 59.2];
    const cell = [size[0] / nx, size[1] / ny, size[2] / nz];
    const occ = new Float32Array(nx * ny * nz);
    const solid = new Uint8Array(nx * ny * nz);   // bins, monuments and the space outside the wall (not seat voxels)
    const idx = (i, j, k) => (k * ny + j) * nx + i;
    const box = (x0, x1, y0, y1, z0, z1, d = 1) => {
      const i0 = Math.max(0, Math.floor((x0 - min[0]) / cell[0])), i1 = Math.min(nx - 1, Math.floor((x1 - min[0]) / cell[0]));
      const j0 = Math.max(0, Math.floor((y0 - min[1]) / cell[1])), j1 = Math.min(ny - 1, Math.floor((y1 - min[1]) / cell[1]));
      const k0 = Math.max(0, Math.floor((z0 - min[2]) / cell[2])), k1 = Math.min(nz - 1, Math.floor((z1 - min[2]) / cell[2]));
      for (let k = k0; k <= k1; k++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) { const q = idx(i, j, k); occ[q] = Math.min(1, occ[q] + d); if (d >= 1) solid[q] = 1; }
    };
    // local box of a unit (room / suite) -> world
    const boxL = (s, x0, x1, y0, y1, z0, z1, d = 1) => {
      const a = localToWorld(s, [x0, y0, z0]), b = localToWorld(s, [x1, y1, z1]);
      box(Math.min(a[0], b[0]), Math.max(a[0], b[0]), y0, y1, Math.min(a[2], b[2]), Math.max(a[2], b[2]), d);
    };
    // seats: voxelise the real instanced geometry (surface samples every ~5 cm, each adds partial occupancy) so
    // footwells, seat undersides, shell corners and console gaps get soft occlusion that matches their shapes
    const dOcc = 0.34, step2 = 0.05 * 0.05;
    // QA r3 (integration): floor contact map, CONTACT.cell cells over the AO extent: 1 where a seat / monument / the
    // sidewall stands on the carpet (seat surface samples below CONTACT.h), one [1/4, 1/2, 1/4] pass, read by mainFS on
    // the carpet only. The 8 cm AO volume cannot hold the thin dark line at each shell / seat base [V: kn_room_1 aisle
    // centre L34, shell-base edge L33 with a thin line; omaatJ_oj_r31 dark base line ~20 px at 1200 px; c_27312 a dark
    // line along every monument base]; width / depth [D]
    const cx = Math.round(size[0] / CONTACT.cell), cz = Math.round(size[2] / CONTACT.cell), con = new Float32Array(cx * cz);
    const markC = (x, z) => {
      const i = Math.floor((x - min[0]) / CONTACT.cell), k = Math.floor((z - min[2]) / CONTACT.cell);
      if (i >= 0 && k >= 0 && i < cx && k < cz) con[k * cx + i] = 1;
    };
    const mark = (x, y, z) => {
      const i = Math.floor((x - min[0]) / cell[0]), j = Math.floor((y - min[1]) / cell[1]), k = Math.floor((z - min[2]) / cell[2]);
      if (i < 0 || j < 0 || k < 0 || i >= nx || j >= ny || k >= nz) return;
      const q = idx(i, j, k); occ[q] = Math.min(1, occ[q] + dOcc);
    };
    for (const g of Object.values(this.seatGroups || {})) {
      const P = g.geo.pos, I = g.geo.idx;
      const samples = [];   // local-space sample points of this unit, reused for every instance
      for (let t = 0; t < I.length; t += 3) {
        const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
        const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2];
        const vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
        const cx = uy * vz - uz * vy, cy = uz * vx - ux * vz, cz = ux * vy - uy * vx;
        const area = 0.5 * Math.hypot(cx, cy, cz);
        const n = Math.min(64, Math.ceil(area / step2));
        for (let m = 0; m < n; m++) {
          let r1 = ((m * 0.618034 + t * 0.1234) % 1), r2 = ((m * 0.754878 + t * 0.4321) % 1);
          if (r1 + r2 > 1) { r1 = 1 - r1; r2 = 1 - r2; }
          samples.push(P[a] + ux * r1 + vx * r2, P[a + 1] + uy * r1 + vy * r2, P[a + 2] + uz * r1 + vz * r2);
        }
      }
      for (const M of g.mats) for (let q = 0; q < samples.length; q += 3) {
        const x = samples[q], y = samples[q + 1], z = samples[q + 2];
        const wx = M[0] * x + M[4] * y + M[8] * z + M[12], wy = M[1] * x + M[5] * y + M[9] * z + M[13], wz = M[2] * x + M[6] * y + M[10] * z + M[14];
        mark(wx, wy, wz);
        if (wy > -0.05 && wy < CONTACT.h) markC(wx, wz);   // (parked instances sit far below the floor)
      }
    }
    for (const zn of this.layout.zones) {
      if (zn.type !== 'seat') continue;
      box(1.46, 2.95, 1.60, 2.30, zn.z0, zn.z1); box(-2.95, -1.46, 1.60, 2.30, zn.z0, zn.z1);
      box(-0.83, 0.83, 1.84, 2.34, zn.z0, zn.z1);
    }
    for (const m of this.layout.mon) if (m.h > 0) box(m.x0, m.x1, 0, m.h, m.z0, m.z1);
    for (const m of this.layout.mon) if (m.h > 0) for (let z = m.z0; z <= m.z1; z += CONTACT.cell * 0.5) for (let x = m.x0; x <= m.x1; x += CONTACT.cell * 0.5) markC(x, z);
    { const xw = wallAt(0.05)[0]; for (let k = 0; k < cz; k++) for (let i = 0; i < cx; i++) if (Math.abs(min[0] + (i + 0.5) * CONTACT.cell) > xw - CONTACT.cell) con[k * cx + i] = 1; }
    for (let j = 0; j < ny; j++) {
      const y = min[1] + (j + 0.5) * cell[1];
      const xw = wallAt(Math.min(y, 2.3))[0];
      for (let i = 0; i < nx; i++) { const x = min[0] + (i + 0.5) * cell[0]; if (Math.abs(x) > xw) for (let k = 0; k < nz; k++) { occ[idx(i, j, k)] = 1; solid[idx(i, j, k)] = 1; } }
    }
    // QA r3: THE Suite geometry occludes less (kAtt 0.8 in the F zone): the 1.3 m shells are open-topped under the
    // bright ceiling, and the ottoman / console / pier read near-black next to a white wall where the daylight photos
    // show mid-tones [V: f_17300, omaat_f2 / f5 / f11 ottoman #9f8c85, console #514537; q03 #312f2d]
    const kAtt = 1.35, kAttF = AO_TUNE.kAttF;
    const fz = this.layout.zones.find((zn) => zn.cls === 'F');
    const kf0 = fz ? Math.floor((fz.z0 - min[2]) / cell[2]) : -1, kf1 = fz ? Math.floor((fz.z1 - min[2]) / cell[2]) : -1;
    const att = new Float32Array(occ.length);
    for (let q = 0; q < occ.length; q++) { const k = Math.floor(q / (nx * ny)); att[q] = Math.exp(-(k >= kf0 && k <= kf1 && !solid[q] ? kAttF : kAtt) * occ[q]); }
    // QA r3: emitter cells. The sweep only sees the ceiling, so everything under the outboard bins read 0 (window seats,
    // the inside of THE Suite) although the sidewall lens, the lit bin undersides and the windows light it. Air cells in
    // the lens band (y 1.30-1.60, |x| 1.55 to the wall) count as sky at 0.45 and the strip under the centre bins
    // (y 1.74-1.84, |x| < 0.83) at 0.35, in the seat zones (bins above) [D: probe of the volume; q05 ottoman 62 -> 98 L
    // vs f_17313 97, q14 median 68 -> 114 vs py_37301 117; 0.55 overshot the suite caps under the lens]
    const emit = new Float32Array(occ.length);
    for (const zn of this.layout.zones) {
      if (zn.type !== 'seat') continue;
      const k0 = Math.max(0, Math.floor((zn.z0 - min[2]) / cell[2])), k1 = Math.min(nz - 1, Math.floor((zn.z1 - min[2]) / cell[2]));
      for (let j = 0; j < ny; j++) {
        const y = min[1] + (j + 0.5) * cell[1];
        const xw = wallAt(y)[0];
        for (let i = 0; i < nx; i++) {
          const ax = Math.abs(min[0] + (i + 0.5) * cell[0]);
          const e = y > 1.30 && y < 1.60 && ax > 1.55 && ax < xw ? AO_TUNE.emitLens : y > 1.74 && y < 1.84 && ax < 0.83 ? AO_TUNE.emitCtr : 0;
          if (e) for (let k = k0; k <= k1; k++) { const q = idx(i, j, k); if (!solid[q]) emit[q] = e; }
        }
      }
    }
    const acc = new Float32Array(nx * ny * nz);
    // QA r3 (integration): AO_TUNE.azim sweep azimuths (was 8: 4 axis + 4 diagonal) stepping AO_TUNE.slope cells
    // sideways per layer, read bilinearly. Each of the 8 sweeps carried 1/8 of the oblique sky, so every 1.15-1.3 m THE
    // Room shell threw a dark 1.0-1.3 m wedge across the 0.55 m aisle, periodic at each seat pair [V: q06 aisle p10 20,
    // 34 % < 30 vs c_27312 p10 41, 5.5 %; kn_room_1 no stain beyond the contact line]; vertical share 0.28 kept [D]
    const dirs = [[0, 0, 0.28]];
    for (let a = 0; a < AO_TUNE.azim; a++) {
      const t = (a + 0.5) * 2 * Math.PI / AO_TUNE.azim;
      dirs.push([Math.cos(t) * AO_TUNE.slope, Math.sin(t) * AO_TUNE.slope, 0.72 / AO_TUNE.azim]);
    }
    const layerA = new Float32Array(nx * nz), layerB = new Float32Array(nx * nz);
    for (const [ox, oz, wgt] of dirs) {
      let prev = layerA, cur = layerB;
      prev.fill(1);
      const fx = Math.floor(ox), fz = Math.floor(oz), tx = ox - fx, tz = oz - fz;
      const w00 = (1 - tx) * (1 - tz), w10 = tx * (1 - tz), w01 = (1 - tx) * tz, w11 = tx * tz;
      // visibility one layer up at (pi, pk): outside the wall 0, past the cabin ends open
      const vAt = (pi, pk) => (pi < 0 || pi >= nx ? 0 : pk < 0 || pk >= nz ? 1 : prev[pk * nx + pi]);
      for (let j = ny - 1; j >= 0; j--) {
        for (let k = 0; k < nz; k++) for (let i = 0; i < nx; i++) {
          const pi = i + fx, pk = k + fz;
          let V = w00 * vAt(pi, pk);
          if (w10) V += w10 * vAt(pi + 1, pk);
          if (w01) V += w01 * vAt(pi, pk + 1);
          if (w11) V += w11 * vAt(pi + 1, pk + 1);
          const q = idx(i, j, k);
          if (emit[q] > V) V = emit[q];
          acc[q] += wgt * V;
          cur[k * nx + i] = V * att[q];
        }
        const t = prev; prev = cur; cur = t;
      }
    }
    // QA r3: three separable [1/4, 1/2, 1/4] passes (i, j, k) smooth the 9-direction sweep's V-shaped wedges on flat
    // walls (q19 closet faces vs py_37302 uniform bulkhead); solid cells (walls, bins, monuments) are not averaged in,
    // so the faces next to them do not darken [D]
    // QA r3 (integration): two more i / k passes on the lowest AO_TUNE.floorBlur layers (y < 0.42 m), where the carpet
    // and the seat bases read the volume: the 3-tap blur is one cell wide, the shell wedges ~6 [D]
    const tmp = new Float32Array(acc.length), nb = AO_TUNE.floorBlur;
    const passes = [[0, nx, 1, ny], [1, ny, nx, ny], [2, nz, nx * ny, ny], [0, nx, 1, nb], [2, nz, nx * ny, nb], [0, nx, 1, nb], [2, nz, nx * ny, nb]];
    for (const [di, n, stride, jn] of passes) {
      tmp.set(acc);
      for (let k = 0; k < nz; k++) for (let j = 0; j < jn; j++) for (let i = 0; i < nx; i++) {
        const q = idx(i, j, k);
        if (solid[q]) continue;
        const c = di === 0 ? i : di === 1 ? j : k;
        const a = c > 0 && !solid[q - stride] ? tmp[q - stride] : tmp[q];
        const b = c < n - 1 && !solid[q + stride] ? tmp[q + stride] : tmp[q];
        acc[q] = 0.25 * a + 0.5 * tmp[q] + 0.25 * b;
      }
    }
    const vis = new Uint8Array(nx * ny * nz);
    for (let q = 0; q < acc.length; q++) vis[q] = Math.round(clamp(acc[q], 0, 1) * 255);
    this.ao = { tex: this.gl.texture3D(vis, nx, ny, nz), min, size };
    const ct = new Uint8Array(cx * cz), cb = new Float32Array(cx * cz);
    for (let k = 0; k < cz; k++) for (let i = 0; i < cx; i++) {
      const q = k * cx + i;
      cb[q] = 0.25 * (i > 0 ? con[q - 1] : con[q]) + 0.5 * con[q] + 0.25 * (i < cx - 1 ? con[q + 1] : con[q]);
    }
    for (let k = 0; k < cz; k++) for (let i = 0; i < cx; i++) {
      const q = k * cx + i;
      ct[q] = Math.round(255 * clamp(0.25 * (k > 0 ? cb[q - cx] : cb[q]) + 0.5 * cb[q] + 0.25 * (k < cz - 1 ? cb[q + cx] : cb[q]), 0, 1));
    }
    const gl = this.gl.gl;
    if (!this.contactTex) this.contactTex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.contactTex);
    for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, cx, cz, 0, gl.RED, gl.UNSIGNED_BYTE, ct);
    this.contact = [min[0], min[2], cx * CONTACT.cell, cz * CONTACT.cell];
  }

  buildGlows() {
    const gl = this.gl;
    const q = raw();
    q.p.push(-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0); q.n.push(0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1);
    q.u.push(0, 0, 1, 0, 1, 1, 0, 1); q.i.push(0, 1, 2, 0, 2, 3);
    const b = new Builder(); b.add(q, null, { c: '#ffffff' });
    this.glowMesh = gl.mesh(b.build(), { name: 'glow', instances: [] });
    this.readingMesh = gl.mesh(b.build(), { name: 'reading', instances: [] });
    const mats = [], tints = [];
    for (const l of this.ext.lights) { mats.push(M4.trs(l.p[0], l.p[1], l.p[2], 0, 0, 0, l.s, l.s, l.s)); tints.push([...l.c, l.blink]); }
    gl.setInstances(this.glowMesh, mats, tints);
    const rnd = mulberry32(42);
    const rm = [], rt = [];
    // flat 16-gon oval facing down, 0.10 m fore-aft x 0.045 m across
    const oval = raw();
    oval.p.push(0, 0, 0); oval.n.push(0, -1, 0); oval.u.push(0.5, 0.5);
    for (let k = 0; k < 16; k++) {
      const a = (k / 16) * Math.PI * 2;
      oval.p.push(Math.sin(a) * 0.0225, 0, Math.cos(a) * 0.05); oval.n.push(0, -1, 0); oval.u.push(0.5 + Math.sin(a) / 2, 0.5 + Math.cos(a) / 2);
      oval.i.push(0, 1 + k, 1 + ((k + 1) % 16));
    }
    fixWinding(oval);
    const lens = new Builder();
    // QA r1: a small lit lens (4 cm sprite) at the lamp + a warm pool on the seat from the shader spot term, not a floating
    // halo [V: tlfl_IMG_9377 / roame_7672 dimmed cabins: small lens, pool of light on the seat]
    this.spots = [];
    for (const s of this.layout.seats) {
      if (rnd() > 0.18) continue;
      let p, t;
      if (s.kind === 'room') { p = localToWorld(s, s.odd ? [0.03, 1.02, -1.18] : [-0.07, 1.02, 1.18]); t = localToWorld(s, s.odd ? [-0.24, 0.55, -0.75] : [0.20, 0.55, 0.75]); }
      else if (s.kind === 'suite') { p = localToWorld(s, [0.1, 1.06, -0.2]); t = localToWorld(s, [-0.1, 0.55, -0.55]); }
      else {
        const y = Math.abs(s.x) < 1.1 ? 1.82 : binBottomY(s.x * 0.92) - 0.03;
        p = [s.x * 0.92, y, s.z - (s.kind === 'py' ? 0.5 : 0.45)]; t = [s.x, 0.62, s.z - 0.3];
      }
      rm.push(M4.trs(p[0], p[1], p[2], 0, 0, 0, 0.04, 0.04, 0.04)); rt.push([2.4, 2.0, 1.4, 0]);
      this.spots.push({ p, t });
      // amber PSU lamp above each lit seat. QA r3: a crisp emissive oval lens (0.10 x 0.045 m) flush under the PSU
      // plus a 3 cm core sprite, not a 7 cm halo floating in front of the bin [V: ucr_room-night-lighting sharp ~2:1
      // oval lenses, core #ac6437, small halo; size A; e 0.25 gives the #ac6437 core at the night gains D]
      const px = s.x * 0.92, ctr = Math.abs(px) < 1.1;
      const py = ctr ? CBIN_Y - 0.011 : binBottomY(px) - 0.0085;
      const pz = s.kind === 'econ' || s.kind === 'py' ? p[2] + 0.12 : s.z;
      rm.push(M4.trs(px, py - 0.004, pz, 0, 0, 0, 0.03, 0.03, 0.03)); rt.push([1.1, 0.6, 0.3, 0]);
      lens.add(oval, M4.trs(px, py, pz, 0, 0, ctr ? 0 : -TILT_O * Math.sign(px)), { c: '#c07040', r: 0.4, e: 0.25 });
    }
    gl.setInstances(this.readingMesh, rm, rt);
    this.psuLensMesh = gl.mesh(lens.build(), { name: 'psuLens', castShadow: false });
    // THE Room seat mood strips: warm LED line under each monitor bezel (bottom edge 0.645 m) and along the ottoman
    // toe line under the footwell mouth, SEATMAT.moodGlow [V: ucr_room-night-lighting strip under the screen #ffeb97;
    // upperclassroom review: mood lighting under the TV and the ottoman; strip sizes D from the 0.64 m bezel / 0.43 m
    // footwell mouth]. Their light on the console / footwell is the shader strip term (u_stripP, nearest 8)
    // QA r2 (light / integration): the strip LED is saturated warm yellow, not cream: '#ffc860' over SEATMAT.moodGlow's
    // '#ffd9a0' (which only this mesh uses), e 0.25 kept [V: ucr_room-night-lighting strip top-40 px #ffee94 s0.42 /
    // #fde98c vs q20 #eee3c2 s0.18, d06 #eee2c0]
    const glow = { ...SEATMAT.moodGlow, c: '#ffc860' };
    const sb = new Builder();
    this.strips = [];
    for (const s of this.layout.seats) {
      if (s.kind !== 'room') continue;
      const [xm, zf, dir, xo, zm] = s.odd ? [-0.245, MON.zO, -1, -0.345, MON.zO] : [0.21, MON.zE, 1, 0.34, MON.zE];
      // QA r1 (light): the screen strip moved 0.642 -> 0.580, just under the sill lip, which the room w8 raise of the
      // monitor sill to y 0.583-0.667 put over it (from_room w8) [V: tpg_53 bezel borders]
      for (const [x, y, z, w] of [[xm, 0.580, zf + dir * 0.02, 0.56], [xo, 0.03, zm - dir * 0.02, 0.40]]) {
        sb.add(gBox(w, 0.006, 0.012), M4.mul(unitXF(s), M4.trs(s.mir ? -x : x, y, z)), glow);
        const c = localToWorld(s, [x, y, z]), e = localToWorld(s, [x + w / 2, y, z]);
        this.strips.push({ p: c, a: V3.sub(e, c) });
      }
    }
    this.stripMesh = gl.mesh(sb.build(), { name: 'moodStrips', castShadow: false });
    this.buildScreens();
    this.buildScreenMask();
  }

  // QA r4 (light): per-screen on / off for the dark moods (mainFS u_scrMask): each seat screen's footprint on the floor
  // plan (4 cm cells, R8, nearest) holds a hash of its centre in 0-0.996; texels without a screen hold 1 (always on).
  // A mood's scrOff (0.7 in Night / Blue) switches the screens below it off, and their spill with them (render)
  // [V: sany_40 economy at night < 1/3 of the seat-back screens lit; sany_47 blue phase ~6 of 25; ucr_room-night-lighting
  // only the passenger's own screen]. Footprint: the screen's width (area at 16:9) + 4 cm across, its tilt depth + 5 cm
  // along the normal [D]
  buildScreenMask() {
    const cell = 0.04, x0 = -3.0, z0 = CAB.zFront - 1.0, nx = Math.ceil(6.0 / cell), nz = Math.ceil((CAB.zAft - CAB.zFront + 2.0) / cell);
    const m = new Uint8Array(nx * nz).fill(255);
    // buildScreens may split a wide screen (THE Suite 0.95 m) into touching clusters: they share one group (root) and hash
    const W = (q) => Math.sqrt(q.a * 16 / 9) / 2;
    this.screens.forEach((q, i) => { q.g = q.g ?? q; for (const r of this.screens.slice(i + 1)) if (r.g === undefined && V3.dot(q.n, r.n) > 0.9 && V3.len(V3.sub(q.p, r.p)) < W(q) + W(r)) r.g = q.g; });
    for (const q of this.screens) {
      const g = q.g, hs = Math.sin(Math.round(g.p[0] * 40) * 12.9898 + Math.round(g.p[2] * 40) * 78.233) * 43758.5453;
      q.h = Math.min(0.996, hs - Math.floor(hs));
      const nh = Math.hypot(q.n[0], q.n[2]) || 1, u = [q.n[0] / nh, q.n[2] / nh], t = [-u[1], u[0]];
      const hw = Math.sqrt(q.a * 16 / 9) / 2 + 0.04, hd = Math.sqrt(q.a * 9 / 16) / 2 * Math.abs(q.n[1]) + 0.05, r = Math.hypot(hw, hd);
      for (let k = Math.floor((q.p[2] - r - z0) / cell); k <= Math.ceil((q.p[2] + r - z0) / cell); k++) {
        for (let i = Math.floor((q.p[0] - r - x0) / cell); i <= Math.ceil((q.p[0] + r - x0) / cell); i++) {
          if (i < 0 || k < 0 || i >= nx || k >= nz) continue;
          const dx = x0 + (i + 0.5) * cell - q.p[0], dz = z0 + (k + 0.5) * cell - q.p[2];
          if (Math.abs(dx * t[0] + dz * t[1]) <= hw && Math.abs(dx * u[0] + dz * u[1]) <= hd) m[k * nx + i] = Math.round(q.h * 255);
        }
      }
    }
    const G = this.gl, gl = G.gl;
    this.scrMaskTex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.scrMaskTex);
    for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, nx, nz, 0, gl.RED, gl.UNSIGNED_BYTE, m);
    this.scrMaskR = [x0, z0, nx * cell, nz * cell];
    G.use(this.progs.main); G.tex('u_scrMask', 7, this.scrMaskTex); G.set('u_scrMaskR', this.scrMaskR);
  }

  // QA r2 (light): IFE screens as area lights for the dimmed moods (mainFS u_scrP / u_scrN): the screen quads
  // (layer 13) of each seat unit, clustered into screens (centre, outward normal, area), then placed per instance.
  // Read from the geometry, so they follow the builders: THE Suite 43 in (0.952 x 0.535), THE Room monitor
  // (0.531 x 0.299), PY 0.345 x 0.194 and Y 0.294 x 0.166 seat-back screens; handsets (< 0.02 m2) left out
  buildScreens() {
    this.screens = [];
    for (const g of Object.values(this.seatGroups || {})) {
      const P = g.geo.pos, Nn = g.geo.nrm, Mt = g.geo.mat, I = g.geo.idx, cl = [];
      for (let t = 0; t < I.length; t += 3) {
        const a = I[t], b = I[t + 1], c = I[t + 2];
        if (Mt[a * 4 + 2] !== 13) continue;
        const pa = [P[a * 3], P[a * 3 + 1], P[a * 3 + 2]], pb = [P[b * 3], P[b * 3 + 1], P[b * 3 + 2]], pc = [P[c * 3], P[c * 3 + 1], P[c * 3 + 2]];
        const area = 0.5 * V3.len(V3.cross(V3.sub(pb, pa), V3.sub(pc, pa)));
        const ctr = V3.scale(V3.add(V3.add(pa, pb), pc), 1 / 3), n = V3.norm([Nn[a * 3], Nn[a * 3 + 1], Nn[a * 3 + 2]]);
        let q = cl.find((k) => V3.len(V3.sub(V3.scale(k.c, 1 / k.a), ctr)) < 0.35 && V3.dot(V3.norm(k.n), n) > 0.8);
        if (!q) cl.push(q = { c: [0, 0, 0], n: [0, 0, 0], a: 0 });
        q.c = V3.add(q.c, V3.scale(ctr, area)); q.n = V3.add(q.n, V3.scale(n, area)); q.a += area;
      }
      for (const k of cl) {
        if (k.a < 0.02) continue;
        const c = V3.scale(k.c, 1 / k.a), n = V3.norm(k.n);
        for (const M of g.mats) {
          this.screens.push({
            p: [M[0] * c[0] + M[4] * c[1] + M[8] * c[2] + M[12], M[1] * c[0] + M[5] * c[1] + M[9] * c[2] + M[13], M[2] * c[0] + M[6] * c[1] + M[10] * c[2] + M[14]],
            n: V3.norm([M[0] * n[0] + M[4] * n[1] + M[8] * n[2], M[1] * n[0] + M[5] * n[1] + M[9] * n[2], M[2] * n[0] + M[6] * n[1] + M[10] * n[2]]),
            a: k.a,
          });
        }
      }
    }
  }

  // shade geometry for one window (no upload when batch = true)
  applyShade(i, level, batch) {
    const w = this.layout.windows[i];
    const S = this.shell.shades, G = this.gl;
    const put = (mesh, j, m) => { if (batch) mesh.idata.set(m, j * 20); else G.setMatrix(mesh, j, m); };
    if (w.electric) {
      const js = S.sheer.list.indexOf(i), jb = S.blackout.list.indexOf(i);
      const ms = shadeMats(w, level >= 1 ? 1 : 0, 0), mb = shadeMats(w, level >= 2 ? 1 : 0, -0.012);
      put(S.sheer.panel, js, ms.panel); put(S.sheer.rail, js, ms.rail);
      put(S.blackout.panel, jb, mb.panel); put(S.blackout.rail, jb, mb.rail);
    } else {
      const j = S.manual.list.indexOf(i);
      const m = shadeMats(w, [0, 0.5, 1][level], 0);
      put(S.manual.panel, j, m.panel); put(S.manual.rail, j, m.rail);
    }
  }
  setWindow(i, level) {
    this.winLevels[i] = level;
    this.applyShade(i, level, false);
    this.updateWindowLUT();
    this.shadowDirty = true;
  }
  setAllWindows(level) {
    this.globalShade = level;
    for (let i = 0; i < this.winLevels.length; i++) { this.winLevels[i] = level; this.applyShade(i, level, true); }
    const S = this.shell.shades, G = this.gl;
    for (const k of ['manual', 'sheer', 'blackout']) for (const m of [S[k].panel, S[k].rail]) G.setInstancesRaw(m, m.idata, m.instances);
    this.updateWindowLUT();
    this.shadowDirty = true;
  }
  updateSheerTint() {
    const k = SKIES[this.sky].sheer;
    const m = this.shell.shades.sheer.panel;
    for (let i = 0; i < m.instances; i++) { m.idata[i * 20 + 16] = k; m.idata[i * 20 + 17] = k; m.idata[i * 20 + 18] = k; }
    this.gl.setInstancesRaw(m, m.idata, m.instances);
  }
  updateWindowLUT() {
    // QA r3: 4096 texels (1.4 cm, was 5.8 cm) and 0 between the windows: the skin is opaque, so the sun only enters
    // through a pane (was 0.92 everywhere, leaving the shadow map alone to stop it: hairline streaks on the seat backs,
    // q15). Rows 0 / 1 (left / right): rgb = shade transmittance over the glass +-0.127 m (CAB.win.w, 10 in [V]) plus
    // 3 cm, alpha = the reveal glow, full over +-0.22 m and cosine-feathered to 0 at +-0.30 m (was a hard 0.48 m block:
    // pale rectangles round each window, from_shell 2). QA r1 (light): row 2 = zone row, r / g = |dz| / half-width to
    // the nearest left / right pane (/4; the shader gates the sun with a rounded-pane superellipse, no hard z edge),
    // b = 1 under the outboard bins / lens (seat zones, as 08_bins builds them; eased over 0.25 m at the zone ends)
    // QA r2 (light): row 3 = shade row, r / g = the left / right shade transmittance / 0.92 over the +-0.30 m reveal span
    // (mainFS nearPane: a closed shade keeps the lens / band light of the wall round it; from_shell w10a)
    const N = 4096, d = new Uint8Array(N * 4 * 4);
    const z0 = this.ao ? this.ao.min[2] : 2.6, z1 = z0 + 59.2, dz = (z1 - z0) / N, hw = CAB.win.w / 2;
    for (let x = 0; x < N; x++) {
      const z = z0 + (x + 0.5) * dz, o = (2 * N + x) * 4;
      d[o] = d[o + 1] = 255;
      let m = 0;
      for (const zn of this.layout.zones) {
        if (zn.type !== 'seat') continue;
        const e = clamp((z - zn.z0 + 0.10) / 0.25, 0, 1) * clamp((zn.z1 + 0.10 - z) / 0.25, 0, 1);
        m = Math.max(m, e * e * (3 - 2 * e));
      }
      d[o + 2] = Math.round(m * 255);
    }
    let open = 0;
    this.layout.windows.forEach((w, i) => {
      const lv = this.winLevels[i];
      const T = SHADE_STATE.T(w, lv);
      open += SHADE_STATE.open(w, lv);
      const r = w.side > 0 ? 1 : 0;
      const a = Math.floor((w.z - 0.30 - z0) / dz), b = Math.ceil((w.z + 0.30 - z0) / dz);
      for (let x = Math.max(0, a); x <= Math.min(N - 1, b); x++) {
        const u = Math.abs(z0 + (x + 0.5) * dz - w.z), o = (r * N + x) * 4, oz = (2 * N + x) * 4 + r;
        const gw = u < 0.22 ? 1 : 0.5 + 0.5 * Math.cos(Math.PI * clamp((u - 0.22) / 0.08, 0, 1));
        if (u < hw + 0.03) for (let c = 0; c < 3; c++) d[o + c] = Math.max(d[o + c], Math.round(T[c] * 255));
        if (u < 0.30) d[(3 * N + x) * 4 + r] = Math.max(d[(3 * N + x) * 4 + r], Math.round(clamp(T[1] / 0.92, 0, 1) * 255));
        d[o + 3] = Math.max(d[o + 3], Math.round(gw * 255));
        d[oz] = Math.min(d[oz], Math.round(clamp(u / hw / 4, 0, 1) * 255));
      }
    });
    this.openness = open / Math.max(1, this.layout.windows.length);
    const gl = this.gl.gl;
    if (!this.winTex) {
      this.winTex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, this.winTex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }
    gl.bindTexture(gl.TEXTURE_2D, this.winTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, N, 4, 0, gl.RGBA, gl.UNSIGNED_BYTE, d);
    this.winZ = [z0, z1];
  }

  sunDir() {
    const s = SKIES[this.sky];
    const el = s.sunEl * DEG, az = s.sunAz * DEG;
    return V3.norm([Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el)]);
  }

  // QA L8 (integration): depth target for the screen-space AO pre-pass (as GL.shadowTarget, but sampled as a plain depth
  // texture: no compare mode, nearest; 24 bit, since 16 bit steps ~8 mm at 4 m with the 0.03 m near plane)
  depthTarget(w, h) {
    const gl = this.gl.gl;
    if (this.sDepth) { gl.deleteTexture(this.sDepth.tex); gl.deleteFramebuffer(this.sDepth.fb); }
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.DEPTH_COMPONENT24, w, h);
    for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, t, 0);
    gl.drawBuffers([gl.NONE]);
    gl.readBuffer(gl.NONE);
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return { tex: t, fb, w, h, ok };
  }

  // sun shadow map. QA r3: fitted to a cabin slice round the camera (zc +-11 m: ~4x the texel density of the whole
  // 59 m cabin, so the sun-patch edges no longer stair-step [V: omaat_f57 / f58 soft patches]); render() re-fits it when
  // the slice centre moves 2 m. No zc (studio) = the whole cabin. Seats outside the slice are left out of the pass
  renderShadow(zc) {
    const G = this.gl, gl = G.gl;
    const L = this.sunDir();
    const full = zc === undefined;
    const za = full ? 2.6 : clamp(zc - 11, 2.6, 50.6), zb = full ? 61.6 : za + 22;
    const center = [0, 1.2, (za + zb) / 2];
    const view = M4.lookAt(V3.add(center, V3.scale(L, 45)), center, Math.abs(L[1]) > 0.95 ? [0, 0, 1] : [0, 1, 0]);
    const corners = [];
    for (const x of [-3.1, 3.1]) for (const y of [-0.1, 2.6]) for (const z of [za, zb]) corners.push(M4.point(view, [x, y, z]));
    const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    for (const c of corners) for (let a = 0; a < 3; a++) { mn[a] = Math.min(mn[a], c[a]); mx[a] = Math.max(mx[a], c[a]); }
    const ex = mx[0] - mn[0], ey = mx[1] - mn[1];
    const W = Math.min(4096, G.maxTex);
    const H = clamp(Math.ceil((W * ey / ex) * 1.15 / 64) * 64, 256, Math.min(2048, G.maxTex));
    if (!this.shadow || this.shadow.w !== W || this.shadow.h !== H) this.shadow = G.shadowTarget(W, H);
    const proj = M4.ortho(mn[0] - 0.05, mx[0] + 0.05, mn[1] - 0.05, mx[1] + 0.05, -mx[2] - 1, -mn[2] + 1);
    this.shadowMat = M4.mul(proj, view);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.shadow.fb);
    gl.viewport(0, 0, W, H);
    gl.clear(gl.DEPTH_BUFFER_BIT);
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.POLYGON_OFFSET_FILL);
    gl.polygonOffset(2.0, 3.0);
    G.use(this.progs.depth);
    G.set('u_viewProj', this.shadowMat);
    for (const g of Object.values(this.seatGroups)) {
      let buf = g.master, n = g.n;
      if (!full) {
        buf = g.hiBuf || (g.hiBuf = new Float32Array(g.n * 20)); n = 0;
        for (let i = 0; i < g.n; i++) {
          const o = i * 20, z = g.master[o + 14];
          if (g.master[o + 13] > -10 && z > za - 1.5 && z < zb + 1.5) { buf.set(g.master.subarray(o, o + 20), n * 20); n++; }
        }
      }
      G.setInstancesRaw(g.hi, buf, n); if (g.lo) G.setInstancesRaw(g.lo, g.master, 0); g.dirty = true;
    }
    for (const m of this.opaque) if (m.castShadow && m.visible) G.draw(m);
    gl.disable(gl.POLYGON_OFFSET_FILL);
    gl.enable(gl.CULL_FACE);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    this.shadowDirty = false;
    this.shadowZ = full ? null : zc;
  }

  render(cam, w, h, time) {
    const G = this.gl, gl = G.gl;
    G.stats.calls = 0; G.stats.tris = 0;
    const sky = SKIES[this.sky], mood = MOODS[this.mood];
    const zc = clamp(cam.pos[2] + cam.fwd[2] * 5, 2.6, 61.6);   // slice centre 5 m ahead of the eye
    if (this.shadowDirty || this.shadowZ == null || Math.abs(zc - this.shadowZ) > 2) this.renderShadow(zc);
    const lc = this.lodCam;
    const moved = !lc || V3.len(V3.sub(lc.pos, cam.pos)) > 0.35 || V3.dot(lc.fwd, cam.fwd) < 0.985 || lc.xray !== this.xray;
    if (moved || Object.values(this.seatGroups).some((g) => g.dirty)) {
      const cosCull = Math.cos(Math.min(Math.PI * 0.95, cam.halfDiag + 0.35));
      updateSeatLOD(G, this.seatGroups, cam, { cosCull: this.xray ? -2 : cosCull, near: this.xray ? 0 : 9.5 });
      this.lodCam = { pos: [...cam.pos], fwd: [...cam.fwd], xray: this.xray };
    }
    const vp = M4.mul(cam.proj, cam.view);
    // QA L8 (integration): depth pre-pass at the canvas size for the screen-space contact AO (mainFS ssaoF): the opaque
    // cabin, depth only, through the shadow depth program (a vertex pass; the depth-only fill is cheap). Only at the Sharp
    // quality (ssaoOn, 13_app.js: phones open on Balanced and keep their frame time); not in x-ray [D]
    let ssao = !this.xray && this.q !== 'low' && this.ssaoOn !== false && LIGHT_TUNE.ssao[1] > 0;
    if (ssao) {
      const sw = w, sh = h;
      if (!this.sDepth || this.sDepth.w !== sw || this.sDepth.h !== sh) this.sDepth = this.depthTarget(sw, sh);
      ssao = this.sDepth.ok;
    }
    if (ssao) {
      const sw = this.sDepth.w, sh = this.sDepth.h;
      gl.bindFramebuffer(gl.FRAMEBUFFER, this.sDepth.fb);
      gl.viewport(0, 0, sw, sh);
      gl.clear(gl.DEPTH_BUFFER_BIT);
      G.use(this.progs.depth);
      G.set('u_viewProj', vp);
      for (const m of this.opaque) G.draw(m);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    }
    gl.viewport(0, 0, w, h);
    if (this.xray) gl.clearColor(0.043, 0.07, 0.125, 1); else gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const L = this.sunDir();
    const op = this.openness ?? 1;
    const lookK = this.xray ? 0 : clamp((Math.abs(cam.pos[0]) - 2.66) / 0.06, 0, 1);   // the look-out share (eye at the glass)
    const winExp = this.xray ? 1 : 1 + ((sky.winExp || 1) - 1) * (1 - lookK);
    const winGlow = sky.winGlow.map((v) => v * (0.15 + 0.85 * op));
    const P = this.progs.main;
    G.use(P);
    G.set('u_viewProj', vp);
    G.set('u_camPos', cam.pos);
    G.set('u_sunDir', L);
    G.set('u_sunCol', sky.sun);
    G.set('u_shadowMat', this.shadowMat);
    G.tex('u_shadow', 0, this.shadow.tex);
    G.set('u_shadowTexel', [1 / this.shadow.w, 1 / this.shadow.h]);
    const k = mood.k;
    G.set('u_hemiTop', mood.hemiTop.map((v) => v * k));
    G.set('u_hemiBot', mood.hemiBot.map((v) => v * k));
    G.set('u_wash', mood.wash);
    G.set('u_hemiBotN', (mood.hemiBotN || mood.hemiBot).map((v) => v * k)); G.set('u_washN', mood.washN || mood.wash);   // QA L8: neutral shadow light away from the windows
    // QA L14: the cool shadow light's hue at the neutral light's level, for the PY / Y seat level (mainFS seatC, MOODS seatCool)
    const lumOf = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    const toLum = (c, ref) => c.map((v) => v * lumOf(ref) / Math.max(lumOf(c), 1e-6));
    G.set('u_hemiBotS', toLum(mood.hemiBot.map((v) => v * k), (mood.hemiBotN || mood.hemiBot).map((v) => v * k))); G.set('u_washS', toLum(mood.wash, mood.washN || mood.wash));
    G.set('u_led', mood.led);
    G.set('u_sideLed', mood.sideLed || mood.led);
    G.set('u_vault', mood.vault || mood.led);
    G.set('u_lowTint', mood.lowTint || [1, 1, 1]);
    G.set('u_aoTune', [AO_TUNE.hemi, AO_TUNE.bounce]);
    const fz = this.layout.zones.find((zn) => zn.cls === 'F');
    G.set('u_fZone', fz ? [fz.z0, fz.z1, AO_TUNE.fLift] : [0, 0, 0]);
    G.set('u_bandCut', mood.bandCut ?? 0.65); G.set('u_sideLow', mood.sideLow ?? 0.4); G.set('u_sideWall', mood.sideWall || [1, 1, 1]);
    G.set('u_lowGain', mood.lowGain ?? 1); G.set('u_fLow', mood.fLow ?? 1); G.set('u_monFill', mood.monFill || [0, 0, 0]); G.set('u_cove', LIGHT_TUNE.cove * (mood.cove ?? 1)); G.set('u_sheen', LIGHT_TUNE.sheen); G.set('u_sheenTint', LIGHT_TUNE.sheenTint);
    G.set('u_toe', mood.toe ?? 0);
    G.set('u_glassT', [1, 1, 1]); G.set('u_hueK', mood.hueK ?? 0); G.set('u_dayN', mood.dayN ?? 0); G.set('u_beltK', (mood.beltK ?? 1) + (1 - (mood.beltK ?? 1)) * lookK); G.set('u_seatCool', mood.seatCool ?? 0); G.set('u_bleed', mood.bleed || [1, 1, 1]); G.set('u_lensLo', mood.lensLo || [0.95, 1.30]); G.set('u_tubHue', mood.tubHue ?? 0); G.set('u_hueW', mood.hueW || [0, 0.86, 0.97]); G.set('u_fjCool', mood.fjCool || [0, 0, 0, 0]); G.set('u_rimK', this.q !== 'low' && this.ssaoOn !== false ? LIGHT_TUNE.rim : [0, 0, 0]); G.set('u_sLowZ', this.layout.z20 ?? 0);   // QA L11: pane tint only on the exterior (below), amber hue-preserving tone, cove rim lobe (Sharp only, as the contact AO: scene.ssaoOn, 13_app.js)
    G.set('u_extBounce', [0, 0, 0]);
    // reading-light pools: the 8 lit lamps nearest the eye [A: count, a phone-sized loop]
    const sp = new Float32Array(32), st = new Float32Array(32);
    if (mood.readingLights && !this.xray) {
      const near = this.spots.map((q) => [V3.len(V3.sub(q.p, cam.pos)), q]).sort((a, b) => a[0] - b[0]).slice(0, 8);
      near.forEach(([, q], i) => { sp.set([...q.p, 1], i * 4); st.set([...q.t, 0], i * 4); });
    }
    G.set('u_spotP', sp); G.set('u_spotT', st);
    G.set('u_spotCol', [1.0, 0.85, 0.65].map((v) => v * 0.5));   // warm lamp colour [V: tlfl_IMG_9377], gain [A]
    // seat mood strips light the console top / footwell only in the dimmed moods (#ffd9a0 x 0.25 = SEATMAT.moodGlow)
    const spp = new Float32Array(32), spa = new Float32Array(32);
    if (mood.strips && !this.xray) {
      const near = this.strips.map((q) => [V3.len(V3.sub(q.p, cam.pos)), q]).sort((a, b) => a[0] - b[0]).slice(0, 8);
      near.forEach(([, q], i) => { spp.set([...q.p, 1], i * 4); spa.set([...q.a, 0], i * 4); });
    }
    G.set('u_stripP', spp); G.set('u_stripA', spa);
    G.set('u_stripCol', [0.25, 0.173, 0.087]);
    // QA r2 (light): screen spill, the 6 screens nearest the eye; colour = the mean IFE picture radiance: the screen
    // emission (SEATMAT.screen e 0.9 x 4 x screenGain, mainFS layer 13) x a mean picture of ~0.75 x [0.30, 0.40, 0.55]
    // (cool-neutral), i.e. 2.7 x screenGain x [0.30, 0.40, 0.55], x scrSpill (Night / Blue 1, Dining 0.5, else 0)
    // [D: the raters' hue; x1 left the nF03 housing L12 vs ml_IMG_20200208_1919534 L32]
    const scp = new Float32Array(24), scn = new Float32Array(24);
    const spill = this.xray ? 0 : mood.scrSpill || 0;
    // QA r4 (light): screens below mood.scrOff are off (mainFS u_scrMask), except the nearest one within 1.8 m that faces
    // the eye (the passenger's own screen, seated or standing at the seat); only lit screens spill
    const scrOff = this.xray ? 0 : mood.scrOff || 0;
    let own = null;
    if (scrOff > 0) {
      let bd = 1.8;
      for (const q of this.screens) {
        const d = V3.sub(cam.pos, q.p), l = V3.len(d);
        if (l < bd && V3.dot(d, q.n) > 0) { bd = l; own = q; }
      }
    }
    G.set('u_scrOff', scrOff);
    // the own screen's group (all its clusters): bounding sphere = centre of the members, radius to the farthest member's
    // corner (half the diagonal at 16:9) + 5 cm
    let ownS = [0, 0, 0, 0];
    if (own) {
      const mem = this.screens.filter((q) => q.g === own.g), c = V3.scale(mem.reduce((a, q) => V3.add(a, q.p), [0, 0, 0]), 1 / mem.length);
      const r = Math.max(...mem.map((q) => V3.len(V3.sub(q.p, c)) + Math.hypot(Math.sqrt(q.a * 16 / 9), Math.sqrt(q.a * 9 / 16)) / 2)) + 0.05;
      ownS = [...c, r * r];
    }
    G.set('u_scrOwn', ownS);
    G.tex('u_scrMask', 7, this.scrMaskTex); G.set('u_scrMaskR', this.scrMaskR);
    if (spill > 0) {
      const lit = scrOff > 0 ? this.screens.filter((q) => (own && q.g === own.g) || q.h >= scrOff) : this.screens;
      const near = lit.map((q) => [V3.len(V3.sub(q.p, cam.pos)), q]).sort((a, b) => a[0] - b[0]).slice(0, 6);
      near.forEach(([, q], i) => { scp.set([...q.p, q.a], i * 4); scn.set([...q.n, 0], i * 4); });
    }
    G.set('u_scrP', scp); G.set('u_scrN', scn);
    G.set('u_scrCol', (mood.scrCol || [0.30, 0.40, 0.55]).map((v) => v * 2.7 * (mood.screenGain || 0.8) * spill)); G.set('u_scrWall', mood.scrWall ?? 0);   // QA L12: Night spill colour / wall share
    G.set('u_fillLift', mood.fillLift ?? 1); G.set('u_lensCore', mood.lensCore || [0, 0, 0]); G.set('u_vaultE', mood.vaultE || [0, 1]);
    G.set('u_winGlow', winGlow);
    G.tex('u_ao', 1, this.ao.tex, gl.TEXTURE_3D);
    G.set('u_aoMin', this.ao.min);
    G.set('u_aoSize', this.ao.size);
    G.tex('u_contact', 6, this.contactTex); G.set('u_contactR', this.contact); G.set('u_contactK', CONTACT.k);
    G.tex('u_detail', 2, this.tex.detail, gl.TEXTURE_2D_ARRAY);
    G.tex('u_photo', 5, this.tex.photo, gl.TEXTURE_2D_ARRAY); G.set('u_photoOn', PHOTO_PIX ? 1 : 0);
    const lp = new Float32Array(N_LAYERS * 4);
    for (const [kk, v] of Object.entries(LAYER_PARAMS)) lp.set(v, +kk * 4);
    G.set('u_layer', lp);
    G.tex('u_atlas', 3, this.tex.atlas);
    G.set('u_screenStep', ATL.screenStep);
    G.set('u_emisGain', mood.emisGain ?? 1.0);
    G.set('u_screenGain', mood.screenGain || 0.8);   // QA r2 night 0.35 -> 0.6: the screen stays the brightest element [V: ucr_room-night-lighting]
    G.tex('u_win', 4, this.winTex);
    G.set('u_winZ', this.winZ);
    G.set('u_R', CAB.R + 0.10);
    G.set('u_yc', CAB.yc); G.set('u_winY', [CAB.win.yc, CAB.win.h / 2]);
    // QA r4 (integration): looking out (eye past the lining, |x| 2.45-2.70; lookOut puts it at 2.72) the interior takes
    // the exterior's exposure scale, x0.15 (LIGHT_TUNE.lookOut; x0.14 before L14): winExp eases to 1 there, and at mood.exposure the reveal and lining read
    // brighter than the daylight sky behind the pane (q12 reveal L225-228, 61 % clipped vs sky L139) where a camera
    // exposed for the view shows them mid-tone below the sky [V: ucr_ana-business-class-wing-view reveal #816242-#7d6b55
    // L104-110, sky #4bb5fb L157]; seated window views (|x| < 2.45) are untouched [D]
    // QA L14 (integration, lighting run 4): both ramps (this and winExp above) are keyed to the glass, |x| 2.66-2.72, not
    // 2.45-2.70 / 2.0-2.45: the PY / economy window-seat eyes stand at |x| 2.61-2.655 (13_app seatEye; THE Room 2.35, THE Suite
    // 2.235), so 24 of the 212 seats (25-27 A/K and 18 economy) rendered their seated view at x0.30-0.44 of the cabin exposure
    // with winExp 1, and the THE Room / THE Suite window seats at winExp 2.0-3.15: the 26A tour stop read mean 87, p50 66
    // [V: py_37301 p50 118; c_27316 near pane L255] (no seat eye lies past 2.66; the look-out eye is at 2.72) [D gapL14m seat_lo]
    G.set('u_exposure', mood.exposure * (1 - LIGHT_TUNE.lookOut * lookK));
    G.set('u_binLo', mood.binLo ?? 1); G.set('u_ctrLo', mood.ctrLo ?? 1); G.set('u_ctrLift', mood.ctrLift ?? 1); G.set('u_monHemi', mood.monHemi ?? 1); G.set('u_tubWash', mood.tub ? LIGHT_TUNE.tubWash : 0); G.set('u_tubSky', mood.tubSky || [0, 1]); G.set('u_binLift', (mood.binLift || [0, 0, 0]).map((v) => v * mood.k));
    // QA L8 (integration): screen-space contact AO inputs (mainFS ssaoF); strength 0 switches it off
    G.set('u_ssao', ssao ? LIGHT_TUNE.ssao : [0, 0, 0, 0]);
    if (ssao) {
      G.tex('u_sDepth', 8, this.sDepth.tex); G.set('u_sRes', [w, h, this.sDepth.w, this.sDepth.h]);
      G.set('u_sProj', [cam.proj[0], cam.proj[5], cam.proj[10], cam.proj[14]]);
      G.set('u_sFwd', cam.fwd); G.set('u_sRight', cam.right); G.set('u_sUp', cam.up); G.set('u_sDither', LIGHT_TUNE.ssaoDither ?? 1); G.set('u_sMix', LIGHT_TUNE.ssaoMix ?? 0.8); G.set('u_sAng', LIGHT_TUNE.ssaoAng ?? 0.35); G.set('u_sLow', LIGHT_TUNE.ssaoLow ?? 0); G.set('u_sIn', LIGHT_TUNE.ssaoIn ?? 0.5); G.set('u_sEase', LIGHT_TUNE.ssaoEase || [0.05, 0.4]); G.set('u_sTap', [LIGHT_TUNE.ssaoTaps ?? 8, LIGHT_TUNE.ssaoCap ?? 0]);
    }
    G.set('u_fill', this.fill ?? 0.45);   // QA r1: 0.7 flattened AO and the ceiling-to-floor falloff [V: c_27312 shell gradients]
    G.set('u_exterior', 0);
    G.set('u_skyTop', sky.skyTop);
    G.set('u_skyBot', sky.skyBot);
    G.set('u_detailOn', this.q === 'low' ? 0 : 1);
    for (const m of this.opaque) {
      if (this.xray && (m.layer === 'upper')) continue;
      G.draw(m);
    }
    // QA r3: the THE Room mood strips are lit only in the dimmed moods (day photos c_27312 / ff_seat-with-door-closed
    // show nothing lit under the monitor; ucr_room-night-lighting at night does) [V]; PSU amber lenses with the reading lamps
    if (mood.strips) G.draw(this.stripMesh);
    if (mood.readingLights && !this.xray) G.draw(this.psuLensMesh);
    if (!this.xray) {
      G.set('u_exterior', 1);
      G.set('u_exposure', winExp * (1 - (sky.lookExt || 0) * lookK));   // QA lighting final touch: SKIES lookExt (above)
      // exterior: cloud-deck bounce and a lower sun (from_exterior 1 / 6: the sun side of the cowl saturated at 5.2)
      G.set('u_extBounce', sky.extBounce);
      G.set('u_sunCol', sky.sun.map((v) => v * sky.extSun));
      // up to two exterior lights with a `light` gain light the airframe at night, blinking like their glow sprite
      const pp = new Float32Array(8), pc = new Float32Array(6);
      let np = 0;
      for (const l of this.ext.lights) {
        if (!l.light || !sky.night || np > 1) continue;
        const on = l.blink > 1.5 ? ((time * 0.9 + l.blink) % 1 >= 0.92 ? 1 : 0) : 1;
        pp.set([...l.p, 1], np * 4); pc.set(l.c.map((v) => v * l.light * on), np * 3); np++;
      }
      G.set('u_extPtP', pp); G.set('u_extPtC', pc);
      G.set('u_glassT', LIGHT_TUNE.glassT); G.set('u_hueK', 0); G.set('u_dayN', 0);   // QA L11: seen through the pane (transmittance before the tone curve); plain ACES outside
      G.draw(this.ext.mesh);
      G.set('u_extBounce', [0, 0, 0]); G.set('u_extPtP', new Float32Array(8)); G.set('u_glassT', [1, 1, 1]);   // the studio (same program) keeps its plain fill and no tint
    }
    G.set('u_toe', 0); G.set('u_fillLift', 1); G.set('u_vaultE', [0, 1]);   // ... and its plain tone, fill lift and vault (14_studio renders through the same program)
    G.set('u_scrOff', 0); G.set('u_binLo', 1); G.set('u_ctrLo', 1); G.set('u_ctrLift', 1); G.set('u_monHemi', 1); G.set('u_fLow', 1); G.set('u_tubWash', 0); G.set('u_binLift', [0, 0, 0]); G.set('u_tubSky', [0, 1]); G.set('u_hueK', 0); G.set('u_dayN', 0); G.set('u_scrWall', 0); G.set('u_beltK', 1); G.set('u_seatCool', 0); G.set('u_bleed', [1, 1, 1]); G.set('u_lensLo', [0.95, 1.30]); G.set('u_tubHue', 0); G.set('u_hueW', [0, 0.86, 0.97]); G.set('u_fjCool', [0, 0, 0, 0]);   // (QA r4) all screens lit, no cabin-only terms
    G.set('u_ssao', [0, 0, 0, 0]);   // (QA L8) no screen-space AO in the studio
    gl.depthFunc(gl.LEQUAL);
    gl.depthMask(false);
    const S = this.progs.sky;
    G.use(S);
    G.set('u_invViewProj', M4.invert(vp));
    G.set('u_camPos', cam.pos);
    G.set('u_sunDir', L);
    G.set('u_time', time);
    G.set('u_zenith', sky.zenith); G.set('u_horizon', sky.horizon); G.set('u_haze', sky.haze); G.set('u_skyK', sky.skyK || 0);
    G.set('u_sunTint', sky.sun.map((v) => v / 5));
    G.set('u_night', sky.night);
    G.set('u_cloudLit', sky.cloudLit); G.set('u_cloudShade', sky.cloudShade);
    G.set('u_exposure', winExp); G.set('u_toe', mood.toe ?? 0);
    G.set('u_sunVis', sky.sunVis); G.set('u_glassT', LIGHT_TUNE.glassT);   // QA L11: the pane transmittance before the tone curve
    G.tex('u_cloud', 0, this.tex.cloud);
    gl.bindVertexArray(this.emptyVAO);
    if (!this.xray) gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.depthFunc(gl.LESS);
    gl.enable(gl.BLEND);
    gl.disable(gl.CULL_FACE);
    // QA L11 (integration + shell): the display-space glass multiply only in x-ray (no sky / exterior behind the panes there);
    // the cabin view applies the pane transmittance before the tone curve (LIGHT_TUNE.glassT, above), so a day pane can clip
    // to white: the multiply capped it at 255 x tint [V: c_27316 pane #ffffff, y_47300 #fcfcfb] (one blended pass fewer)
    if (this.xray) {
      gl.blendFunc(gl.DST_COLOR, gl.ZERO);
      G.use(this.progs.glass);
      G.set('u_viewProj', vp);
      G.draw(this.shell.meshes.glassR); G.draw(this.shell.meshes.glassL);
    }
    gl.blendFunc(gl.ONE, gl.ONE);
    G.use(this.progs.glow);
    G.set('u_viewProj', vp);
    G.set('u_camRight', cam.right); G.set('u_camUp', cam.up);
    G.set('u_time', time);
    if (sky.night && !this.xray) G.draw(this.glowMesh);
    if (mood.readingLights) G.draw(this.readingMesh);
    gl.enable(gl.CULL_FACE);
    gl.disable(gl.BLEND);
    gl.depthMask(true);
  }
}
