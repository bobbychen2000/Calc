# Economy: questions for the user (never blocking; current choice in brackets)

1. Coat hook: the official photo y_47303 shows a round recess beside the handset; SANspotter's 2023 NH7 photos
   (sans 15) show two small light fittings under the hood instead. [kept: round recess at the right, a placard at the left]
2. Pocket contents: blue ANA magazine (y_47303) or the purple "B777-300" safety card (sanspotter 20/21)? [both shown]
3. Belts: cerulean in y_47303, slate-looking in y_47302 - are they mixed or is that lighting? [cerulean everywhere]
4. Overall seat-back height: no drawing found. The back now rises to ~1.31 m above the floor at upright
   (~0.87 m along the back from the pan crease, measured on y_47302). A Recaro CL3710 drawing would confirm it.
5. Headrest cover shade varies between the official photos (#272d48 to #475273). [w5: #343a52 base, rendered L ~59 vs
   y_47300 52; the lighter covers in y_47306 / 47303 are grazing-light sheen]
6. (w5) Blankets in plastic bags on every seat at boarding (sans 13 / 14, flight-report NH5): show them, or keep ANA's
   clean-cabin look? [clean cabin, as in the official photos; the user's THE Room decision also drops the wrapped duvet]
7. (w5) Footrest: sans 23 shows two white hangers close together at the seat centre, y_47304 a bowed arm landing on the
   pedal joint. [w5: hangers moved to the centreline, no hanger at the pedal outer ends] A photo from your seat would
   confirm it.
8. (w5) Belt colour again (question 3): rater A reads y_47302 / 47301 as charcoal. [still cerulean, darker #2e4c86
   after the w5 B measurement of y_47303 #325495]
9. (w6) Fabric mix: the in-service photos (sans 12 / 13, fr57325) show mostly petal-fleck and diamond seats with few tick
   seats; ANA's showroom photos show all four about evenly. [kept: 40 % fleck, 20 % each of tick / mosaic / diamond]
10. (w6) Belt colour (questions 3 / 8): rater B reads in-service fr57325 124108 and y_47302 as charcoal. [still blue, darker
   #243a66 after w6 B measured #588ed0 rendered vs y_47303 #38578c; one SEATMAT line to switch to charcoal #34373e]
11. (w6) Coat hook: rater A sees an off-white mushroom knob on the hood side in sans 22. Which side? [not modelled yet]
12. (w6) Headrest cover width: y_47300 ~0.6 of the cushion, sans 13 ~0.8 (wide-angle). [0.255 m = 0.72 of a 0.355 pad]
13. (wave 3 final) Fabric close-ups: the four Y fabrics are synthesised from ~1 mm/px official photos. The raters' diamond
   and mosaic targets contradicted each other from round to round. A 1:1 close-up photo of each fabric (yours, or from a
   trip) would let `make_swatches.py` cut real tiles. [shipped: the w11-rated tiles]
14. (wave 3) Headrest cover leatherette: slate grey-blue (y_47301 #555975, y_47306 #475273) or dark navy (head-on
   y_47300)? [#3a4060, dark; slate at an angle is a lighting / sheen question]
15. (wave 3) Are the headrests raised in the y_47300 hero shot (the pad top is the back top there) and lowered in
   y_47306? [modelled lowered, back ~5.5 cm above the cover fold; head-on a ~1.5 cm white hood rim shows]
16. (wave 3) Regular-row aisle ends: an open frame under the J armrest (y_47303) or a solid white panel (y_47301)? [solid
   panel]
17. (wave 3c, w15 B) Headrest cover hang: in y_47300 the flap ends at the pad bottom; in y_47306 it hangs ~3 cm below it.
   [modelled as y_47306, the close-up]. Question 15 (raised headrests) is now answered the other way: the w14 gap analysis
   found the back ~0-4 cm above the cover fold in y_47300 / 47301 / 47302 and only ~5.5 cm in y_47306, so the headrest
   now sits 2.5 cm higher (back ~3 cm above the fold).
18. (wave 3c) Fabric tiles are now cut straight from your official photos (y_47306 tick / diamond / mosaic, y_47300
   fleck). The diamond's only usable source is the oblique left seat of y_47306 (~2 mm/px), so it is soft up close; a
   frontal close-up of a diamond seat (and of a fleck seat) would sharpen both.
19. (wave 3d) Headrest cover sheen: the covers are navy head-on (y_47300) but silver-grey at grazing angles (y_47301 /
   47303 / 47306). One material can't do both without a cover-only sheen term in the shader, which belongs to the lighting
   area. May lighting add one? [shipped: navy satin #222842 r 0.52, right head-on and too dark at an angle]
20. (wave 3d) Cover length: is the y_47300 short cover (it ends inside the pad) the default, or the long cover that real
   photos show hanging below the pad (b_ss_13, y_47306)? [kept long, as in the real photos]
21. (wave 3e) Headrest cover height: at the matched y_47300 camera rater B measures the cover ~25 % too tall (h/w 0.87
   vs 0.70-0.77), while the y_47306 close-up shows it slightly too short and b_ss_13 hangs it 2-3 cm below the pad. Is
   y_47300's short cover a showroom setting? [shortened 2 cm in w25, then kept]
22. (wave 3e) Q16 / q17 still don't frame y_47301 / y_47303 closely: the photos use ~80 deg lenses and the app's walk
   camera is fixed at 64 deg horizontal. Should `test/qa.js` get a per-view FOV (like `window.__near`)? That's an
   integration call. [framed as closely as 64 deg allows]
23. (wave 3f) Re question 21: with q15 now matched to y_47300, both raters measure the cover 1.3-1.45x too tall head-on
   (h/w 0.85-0.88 vs 0.67-0.75) in every round. It is the largest econ mismatch left. Should the short y_47300 cover be the
   default, with the long overhang of y_47306 / b_ss_13 kept for a lowered headrest only? [kept long]
24. (wave 3g, w35) Re questions 21 / 23: decided on the evidence. The real head-on sans 13 near seat and y_47300 both show
   the cover ending level with the pad foot at h/w ~0.7 (ours 0.85-0.88), so its foot is now 3 cm higher. y_47306's longer
   hang is a lowered headrest. [shortened]
25. (wave 3h, both raters) Belts: tucked away under the pillow as in the y_47300 hero shot, or laid across the pans as in
   y_47302 / y_47303 and the trip reports? [tucked under the pillow edge, only the buckle shows]
26. (wave 3i, w41a-1) Headrest cover width: the matched head-on y_47300 gives ~0.22 m (1.03x), but in the q17 / y_47303
   side view the headrest wing hides half our cover (29-48 px per row vs 66-88). Is the real cover wider, wrapping
   round the wings? [kept 0.22]
27. (wave 3i, w42a-1) Lumbar pillows: y_47300 has one on every seat, including the side blocks; y_47301 / y_47303 show
   none on the side-block seats, where the belts are laid out. Are pillows on the side blocks a showroom setting?
   [kept on every seat]. Question 25 (belts) is now answered both ways: draped on the side blocks, tucked on the centre
   block.
28. (wave 3j, w44a-2 / w44b-3, re question 27) Lumbar pillows on the 3-seat side blocks: the three official photos
   disagree. y_47301 and y_47303 show the side-block seats bare, with the belts laid out; y_47300 shows a pillow on the
   left side-block seat (B: not the right one). Both raters default to bare. [w44: removed from the side blocks, near and far
   LOD; the 4-seat centre block keeps them, as in the y_47300 hero row]
29. (wave 3k, w46b) Belt colour: y_47303 shows teal tongue straps, but y_47300's side-block straps look dark. Is teal
   right on every seat? [kept teal everywhere; it measures right in q16 / q17]
30. (wave 3k, w48) Back height: at the landmark-matched q17 camera the backs read ~6 cm tall. The back is now 4.5 %
   shorter (top ~1.28 m). Is there a published overall height for this Recaro seat to confirm it? [shortened on photo
   evidence]
31. (wave 3l, w49) Headrest height: y_47300 (head-on) puts the cover close under the back top, with h/w ~0.7. y_47303 (side)
   shows the cover lower and larger on the back. The raters agree that one cover position cannot match both photos. Was
   the 6-way headrest set at different heights in the two shoots? [kept a compromise; w49 leans toward y_47303, and both
   raters flag the q15 h/w of 0.86-0.92 as a regression]
