# Exterior area report (`src/11_exterior.js`)

## Scores

| round | commit | rater A (skeptic) | rater B (geometry) |
|---|---|---|---|
| r2 (previous) | – | 5.2 (single rater) | – |
| w1 (fresh re-rate of the r2 build) | – | 4.4 | 5.0 |
| w2 | c7ad1fa | 5.0 | 6.6 |
| w3 | 8220ed6 | 5.7 | 7.1 |
| w4 (wave 1 final) | a38dde8 (+ 970ccfa and a final low-item commit) | 6.1 | 7.4 |
| w5x (second-opinion pair, before wave 3) | – | 6.0 | 6.7 |
| w5 (wave 3) | ea0e6a1 | 6.6 | 7.0 |
| w6 | wave-3 w5 fix commits | 6.8 | 7.1 |
| w7 | wave-3 w6 fix commit | 6.8 | 7.1 |
| final | w7 fixes (unrated) | – | – |

Four rounds, the loop maximum. Both raters say the remaining gap to 8.5 is mostly lighting-owned (`12_scene.js`
SKIES, the exterior shading in `04_shaders.js`), and I have handed it over in `from_exterior.md`:

- the pale day sky
- no cloud-deck bounce in the exterior ambient (the sunset canoes glow cream)
- sun-side exposure clipping on the white cowl
- the sunset palette
- the night beacon

Final per-detail scores for what this file controls are 6 to 8.5. The registration scores 8.5, and the planform,
tip height and bending 7.5.

## What changed (all in `buildExterior` / `WING`)

- **Right-wing registration JA795A.** Dark grey block capitals, 1.4 m tall, at 50 % chord from s 13.5 outboard. The J is
  inboard and the glyph tops point toward the leading edge, so it reads upright from the aft K seats. I verified this on
  zoomed photos (both raters first called it upside down; that was perspective). It is drawn with `wingLine` strokes
  from a small stroke font.
- **Canoes.**
  - Wing paint with a small flank fill and a darker belly (they had been dark slate).
  - Smooth rounded teardrop sections with tapered cruise tails and a rounded tip of about 8 cm (the r2 blunt tail came
    from a flaps-down ground photo).
  - The outboard pair moved to s 14.7 / 20.4, the outboard-flap supports.
- **Pylon.** A broad, low forward fairing hump in cowl colour, about 1.2 m wide and blending over 20 sections into a
  saddle under the leading edge. The strut stays in wing grey, and only the strut keeps the flank fill.
- **GE90 nacelle.**
  - Inboard strake: a 1.3 × 0.26 m plate at 25° with a dark root seam, inside the middle cowl panel.
  - Upper access-panel ring.
  - Cowl albedo #b3b4b5 with a baked top-to-lower normal falloff (0.55–1). This matches the ANA 11A shade side
    (#8d96a6 → #78889a).
- **Wing surface.**
  - Wider bare-metal slat nose band.
  - A spanwise splice and chordwise butt-joint seams.
  - ±5 % tone per skin panel.
  - Faint fastener lines along the front and rear spars.
  - 8 static dischargers per side.
  - A flush, brighter nav light.
  - Gear stripe 0.46 m wide.
- **Triangles:** 21,824 → 24,568 (+2.7k) for the whole exterior mesh (both wings and both engines).

## Sources

In-cabin photos are in `ref/web/exterior/`, gitignored:

- ANA 777-300ER, seat 11A: NH212 (lalf_*_136/137, seat proof _127).
- ANA JA795A, seat 26K: NH211 2026 (alv_*_7242/7250/7282/7329/7331/7345, seat proof).
- Wikimedia Commons: Air France F-GSQR cabin views; Emirates sunset view; GE90 window views (F-GSQS, PIA, "Leaving Sri
  Lanka"); Boeing_777 ground views.
- Cathay B-KQZ GE90 close-ups.
- YouTube stills: EVA, United, Turkish and Emirates 777-300ERs.

Geometry and data sources:

- Boeing D6-58329-2 ACAP (planform, stations; already in the file header).
- NASA CR-1998-196709 (outboard-flap support stations).

## Open questions

See `questions_exterior.md`: which airframe to show, the ANA yellow ice spot, a GE90 logo, and the day-sky look.

Renders are in `exterior_before_after.jpg`. Row 1 is the round-2 build, row 2 the final build from the same seats,
and row 3 the right side (JA795A registration) plus night.

## Wave 3 (2026-10-24)

Three rated rounds (w5-w7). The mean went 6.35 (w5x) -> 6.8 -> 6.95 -> 6.95. It is above the wave-1 best (6.75) every round,
but w6 and w7 each gained under 0.2, so the loop stopped on the brief's rule. The final commit lands the w7 fixes both raters
agreed on and is not rated. Neither rater found a high-severity issue in w6 or w7. The exterior is 24,568 -> 25,160
triangles (+2.4 %).

### What changed (all in `src/11_exterior.js`)

- **JA795A.** The ink is near-black navy `#0f1a30`, matte (ink/skin 0.15-0.23 rendered against 0.07-0.41 in the photos). The
  stroke is mitred at the corners (`wingLine` now offsets by the averaged normal / cos), 0.28 m wide at a 1.05 m pitch.
- **Cowl.** The splits are dark hairlines `#5f646a`. The lip has its own neutral satin material. The inlet liner is neutral
  grey, graded from the lit lip to dark at the fan. The access panel is a near-square rounded rectangle on the inlet cowl,
  0.88 m aft. The strake is a thin chine with a baked shadow band on the cowl below it (the black root box that flickered is
  gone). A GE monogram (ring + G E) sits low on the inboard fan cowl, 1.7 m aft and 50 deg below the horizontal (ANA videos
  IQCFQpV_T1A and eX2WMn0xe48, KN Aviation 7A). It is block letters, not the script swirl.
- **Canoes.** Pods deepest at the TE, about 0.3 of their length behind it. The keel runs straight to a small rounded point,
  and the flank grades from the lit top to the keel. The tail went through three shapes (w5 spike, w6 blunt, w7 bullet) before
  both raters agreed on this one.
- **Wing.** 14 static dischargers (9 on the aileron, 5 on the rake; Sam Chui _37). The aileron runs to s 30.4. The spoiler
  hinge line and breaks are faint (`#505357`, 22 mm), and only the TE gaps are near-black. The rivet rows sit a shade under
  the paint. Spoilers, flaps and ailerons are 0.90-0.96 darker and bluer than the fixed skin (KN Aviation 41). There are small
  dull-red placards and a row of LE heads inboard of s 17.5. Panel tone jitter is 0.15.
- **Lights.** The nav light is a small point (s 1.0) and redder.

### Sources added in wave 3

KN Aviation ANA 777-300ER reviews (knaviation.net; `a5_kn_*`, `b5_knav_*`), TPG ZGriff-63, Sam Chui _36/_37, and the ANA
YouTube window videos IQCFQpV_T1A and eX2WMn0xe48. All are in `ref/web/exterior/` (gitignored).

### Still open

- **GE mark.** It is block letters, not the script monogram. No passenger view shows it.
- **Skin.** Cleaner than the photos: no grime, and only a few stencils.
- **Lighting-owned.** Sunset blue cast, the belly beacon washing the canoes red, sun-side cowl clipping, and the royal-blue
  reveals. All are in `from_exterior.md` items 8-11.

The before/after sheet `exterior_before_after.jpg` has the wave-3 start build in row 1 and the final build in row 2, from the
same seats.

## Wave 3b, plateau breaker (2026-10-24, w8-w11)

| round | build rated | rater A | rater B | mean |
|---|---|---|---|---|
| w8 | e05c5e2 (wave-3 final, w7 fixes) | 7.0 | 7.3 | 7.15 |
| w9 | 764d796 (w8 big-ticket work) | 7.3 | 7.6 | 7.45 |
| w10 | b1dec68 (w9 fixes) | 7.0 | 7.6 | 7.3 |
| w11 | 0629727 (w10 fixes) | 7.3 | 7.8 | 7.55 |
| final | w11 fixes (51e3979 + this commit) | – | – | – |

The loop stopped at the 4-round cap of the plateau breaker, below 8.5 for both raters and with no high-severity issue open. w11 is
the best round so far (mean 7.55, against 6.95 at the end of wave 3). The exterior is 25,160 -> 27,136 triangles (+7.9 % in wave 3).

### Gap analysis (`exterior_gap_w8.md`)
It found three frame-wide problems, ahead of the marks the raters kept citing:
1. The wing was too dark and too blue (0.61-0.79 of the cloud luma, against 0.65-0.96 in the ANA photos).
2. The skin was 3-5x too uniform.
3. The canoe section was wrong (the photos show a flat lit top facet over a darker flank).

### What changed (all in `src/11_exterior.js` unless noted)
- **Wing skin as panels.** The upper skin is built per span interval with duplicated vertices on the spoiler, flap, flaperon and
  aileron box edges (`wingBreaks`, `WING_SPAN_BREAKS`). Each panel now has its own flat tone and a +-1.5 deg sheen tilt. Vertex
  colour had smeared the w5-w7 jitter into gradients nobody could see.
- **Photo grime layer.** New photo layer 27, `tex/tex_x_skin.png`, cut by `test/make_swatches.py x_skin` from the sunlit flap of
  JA795A (alv IMG_7250). Panel lines and specks are median-filtered out, the tile is high-passed, smeared along the flow and skewed
  dark, and it is stored at SD 0.12. `PHOTO_GAIN[27]` 0.22 renders it at about 2.6 %. Added to that: grime on the hinge rows (-7 %)
  and the flap TE (-7 %), the flaps behind the engine darker (-4 %), and a soft TE grime band.
- **Paint.** #76787a, r 0.72, m 0.05, replacing #636466 at r 0.5, which mirrored the sky blue. The ramp runs 1.12 near -> 0.80 far.
- **Canoes.** Chined sections (r = min(w * 0.3, d * 0.25)), the top line falling 0.28 m to the tip, a tip that closes on a near-zero
  ring, no grime layer, and a bake of 1 / 0.92 / 0.5 from top through flank to belly. **Bug found by rater A in w10:** from w8 on, a
  zero-size first loft ring defeated gLoft's ring-0 orientation check, so all 8 canoes rendered inside out. That was the bright keel
  band and the charcoal flanks of w8-w10. The fix (`rise` >= 0.06) was checked with an outward-normal probe: 290/290 vertices face out.
- **GE monogram.** Script G and E with four rim swashes curling in through the ring, a small block "GE" wordmark aft on the left
  engine, and strokes half-sunk so they read as paint (knav 7A _9).
- **Inlet.** Grey spinner #8a8e94 (knav _9), blades #3e4248, and a darker graded liner, so the fan is no longer a void.
- **Smaller items.** JA795A strokes 0.23 m at a 1.10 m pitch, muted placards, 0.02 m spoiler breaks, a straight splice and straight
  rear fastener rows.

### Shared-file edits
- `src/03_tex.js`: N_LAYERS 28, `LAYER.xSkin`, and the `PHOTO_LAYERS`, `PHOTO_GAIN` and `LAYER_PARAMS` 27 entries.
- `test/make_swatches.py`: `x_skin`.
- `tex/sizes.json`.

### Hand-offs to lighting (`from_exterior.md` 14)
The grazing sky reflection (`specEnv`, `u_skyTop*1.2`) ignores the baked colour, so the far wing still renders brighter than the
near flap in w19A (L178 against L161; KN41 runs 192 near -> 145 far). Both raters put the fix at about +0.3. Items 8-11 (sunset
blue, beacon wash, cowl clipping) are still open. Items 12-13 were withdrawn: they were the canoe bug.

### Left at the cap (each about +0.1-0.3 per the w11 raters)
- **Canoe flanks from the A side.** They render at 0.52 of the skin against 0.72-0.77 in KN41. The w11 bake lifts them; this is
  unrated.
- **Pylon fairing.** It could be a little larger and crisper (ridge 0.70 m, width 1.35 m).
- **Control-surface gaps.** About twice the photo width near the camera.
- **Short dark streaks behind the canoes on the flaps.**
- **Camera.** The registration sits under the shade rail in 26K and 30K.

### Sources added
The wave-3 set was re-downloaded into `ref/web/exterior/` (gitignored). The URLs are in the rating JSONs.

The before/after sheet `exterior_before_after.jpg` has the wave-3b start (e05c5e2) in row 1 and the final build in row 2, from the
same seats and studio cameras. Review cameras are in `review/qa/exterior_views.js` and `review/spec_ext.json`.

## Wave 3c (2026-10-24, w12-w15)

| round | build rated | rater A | rater B | mean |
|---|---|---|---|---|
| w12 | 0c53815 (wave-3b final, w11 fixes unrated) | 7.3 | 7.6 | 7.45 |
| w13 | e616802 (w12 fixes) | 7.6 | 7.8 | 7.7 |
| w14 | f5575d0 (w13 fixes) | 7.6 | 7.9 | 7.75 |
| w15 | ab4fea0 (w14 fixes) | 7.8 | 8.0 | 7.9 |
| final | w15 fixes (this commit, unrated) | – | – | – |

The loop stopped at its 4-round cap. Neither rater reached 8.5, and neither found a high-severity issue in w13-w15. w15 is the best round so
far (7.9, against 7.55 in w11). The w12 drop came from the unrated w11 canoe flank floor (0.92), which turned the sunlit K-side pods
skin-white; the w12 fixes replaced it. Exterior triangles: 27,136 -> 29,440 (+8.5 % this wave; +17 % over the wave-3 start of 25,160).

### What changed (all in `src/11_exterior.js`)
- **Sun-side cowl (from_integration 10).** Cowl r 0.3 -> 0.5, plus a bake that darkens nacelle faces turned to the day sun (x0.7 at
  full n.L). w11K sun side L227 -> L202; the 11A shade side keeps L159 / L142 (LALF _136 L133-148). A flat albedo cut was tried and
  dropped: through the winExp 4 + ACES shoulder it needed ~0.4x linear and took the 11A shade side to L89-103.
- **Canoes.** Baked by normal, depth below the wing's lower skin and the day-sun term, with a 1.65x lift on the sun-away (+x) flanks
  and the outboard pods x1.25. K side (w26K) flank 0.94 -> 0.57 of the skin (_7250 0.54); A side (w19A) 0.61 -> 0.65-0.81 of the
  flap (KN41 0.72-0.85). The crown rolls into the flank, the width tapers like the depth, and the tail rings are round.
- **Inlet.** Liner #585e65 graded by depth and by up-facing normal (w11A L8-25 at worst in w13-w14, now 37-51), three acoustic-panel
  joint rings, matte fan-case disc, blades with sheen, lighter spinner, rougher lip.
- **Pylon fairing.** Ridge 0.70 m, width 1.35 m, crisper shoulders, a flank shade, and a domed nose that starts a quarter along the fan
  cowl (x 1.65), not on the inlet split.
- **Wing.** TE / hinge gaps taper 20 -> 35 mm from root to s 20 (near gaps 4-6 px -> 2-3 px); two short, fading streaks on the flaps
  behind each canoe, on the skin layer; outboard roughness 0.72 -> 0.92 (it took only ~4 L off the far skin).
- **Access panel.** A single stadium outline, lighter (a twin panel read as an "8", w14).
- **Review cameras.** w26K / w30K put the eye at the glass, as in the alv 26K photos, so JA795A is no longer under the shade rail.

### Hand-offs
- `from_exterior.md` 15: the app's `lookOut` framing in the aft K seats (13_app.js, camera at the glass).
- `from_exterior.md` 16 (= 14): the wing near-far value. Both raters still rate it the largest single lever (w19A near flap L163,
  far skin L172; KN41 194 -> 146). It needs the exterior `specEnv` scaled by the baked albedo in `04_shaders.js`.
- Item 10 is done (`fixed_exterior.md`).

### Left at the cap (low, about +0.05-0.1 each per the w15 raters)
Pylon saddle near x 3.6-4.2 (LALF _137); the inlet edge just inside the lip still ~1.7x too dark from 11A and the blades unreadable from
the window angles; the crown-to-flank step on the K-side canoes within ~4 px; access-panel outline a little dark.

### Open questions
`questions_exterior.md` 10-11: a straight-on GE90 fan-face photo, and the day-sun-specific bakes.

The before/after sheet `exterior_before_after.jpg` has the wave-3c start (r12, 0c53815) in row 1 and the w15 build in row 2. The w26K
camera differs between the rows (moved to the glass in w12).

## Wave 3d (2026-10-24, w16-w19)

| round | build rated | rater A | rater B | mean |
|---|---|---|---|---|
| w16 | 0f172d3 (wave-3c final + lighting r2, unrated "final" fixes) | 7.7 | 8.1 | 7.9 |
| w17 | 5eaed93 (gap w16 items 1-4) | 7.8 | 8.2 | 8.0 |
| w18 | 9cac06c (w17 fixes + cowl mottle) | 8.0 | 8.4 | 8.2 |
| w19 | 8f452e0 (w18 fixes) | 8.1 | **8.5** | 8.3 |
| final | w19 low fixes (this commit, unrated) | – | – | – |

The loop stopped at its 4-round cap. Rater B reached 8.5 in w19; rater A is at 8.1. Neither rater found a high-severity issue in
any round, and w19 holds only low issues. Every round gained (+0.1, +0.2, +0.1), and w19 is the best round so far (mean 8.3,
against 7.9 in w15). Exterior triangles: 29,440 -> 29,980 (+1.8 % this wave; +19 % over the wave-3 start of 25,160, cap +25 %).

The gap analysis (`exterior_gap_w16.md`) found that the lighting loop's albedo-scaled sky reflection was a no-op on the wing (its
normaliser 0.39 sits under the #76787a paint's luma 0.47). It also found that the near-far reversal was diffuse, not specular, so
exterior fixed it in albedo (from_exterior 17).

### What changed
All of these are in `src/11_exterior.js` unless noted.
- **Near-far value.** The skin ramp is now 1.22 -> 0.66 over s 5-20. In w19A the near flap went 162 -> 173 and the far skin
  169 -> 162, so the order is now right. B measured the far/near ratio at about 0.70 (KN41 0.75); A still wants more and puts the
  remaining gap on the grazing sky specular (lighting).
- **Fastener rows.**
  - A new dot layer 35 (`tex/tex_x_rivet.png`, synthetic 25 mm pitch, `make_swatches.py x_rivet`) is laid on 28 mm strips along
    the near spoiler hinges, the flap noses, mid-flap, and either side of each spoiler break.
  - The strips carry the skin ramp and sit just under the panel, at a dot gain of 3.2.
  - w17's 50 mm pale strips read as zippers and were fixed in w18.
  - Next to them sit hinge-fitting smudges: a pointed dark head with a fading tail, jittered.
- **Pylon forward fairing.**
  - Remodelled as a low blister: dome, then a saddle, then a single rise into the strut. The flanks are tent-tapered (x0.65,
    t^1.5) into the cowl, built from 10 loft segments.
  - The flank shade fades out at the foot, so the foot takes the cowl's value (from 6.9-7.5 to 8.0 / 8.1).
- **Cowl.**
  - A weathering mottle on a new photo layer 36 (`tex/tex_x_cowl.png`, cut from LALF 11A _136, isotropic, gain 0.25).
  - An upper fan-cowl hinge line running split to split, as a 2 cm band (final). The 5 mm tube dashed at range.
- **Tip.** A flush nav lens with the glow inside the fairing, and 7 finer, lighter static dischargers instead of the 14-pin comb.
- **Canoes.** The day-sun cut now applies to the flanks only, so the K-side crown stays lit (0.78 -> about 1.0 of the skin).
- **Inlet.** The liner is graded by a pwl (lip end held for 11A, fan end darker for 11K, 66 -> 52); the access panel is lighter.
- **Review cameras.** The w26K / w30K offsets were dropped, because `lookOut` now puts the eye at the glass. Every studio render
  now sets `CABIN_PAGE`; the r16 studio shots came from the stale `dist/`.

### Shared-file edits
- `src/03_tex.js`: N_LAYERS 37, `LAYER.xRivet` / `xCowl`, and the `PHOTO_LAYERS`, `PHOTO_GAIN` and `LAYER_PARAMS` 35 / 36 entries.
- `test/make_swatches.py`: `x_rivet` and `x_cowl`.
- `tex/sizes.json`.

### Left at the cap (low, from the w19 raters)
- **Pylon dome.** It is flat-topped and has lost the shallow saddle (B). The foot still steps to the cowl by 15-28 L (the final
  fix lifts it +8 %, unrated).
- **Fastener dots.** They are 0.94 of the panel against about 0.80 in KN41. The dots are sub-pixel at window range, so gain alone
  barely moves them.
- **Far canoe pods.** On the K side they are 0.52-0.60 of the skin against 0.58-0.72 in _7250 (partly sun height, lighting).
- **Fixed scores.** Planform 7.5 and livery 7.5 / 7.7 have not moved since wave 3b. Neither rater names a geometric defect; they are
  A's main brake on reaching 8.5.

The before/after sheet `exterior_before_after.jpg` shows the wave-3d start (r16) in row 1 and the final build in row 2. The views are
w19A, w13A, w26K, w11A and n19A. It holds own renders only.

## Wave 3e (2026-10-25, w20-w22): confirm and polish

| round | build rated | rater A | rater B | mean |
|---|---|---|---|---|
| w20 | befdc88 (wave-3d final fixes 8b29416, first rating) | 8.3 | 8.5 | 8.4 |
| w21 | aa173a1 (w20 fixes) | 8.4 | 8.6 | 8.5 |
| w22 | 5aac2bd (w21 fixes) | **8.5** | **8.7** | 8.6 |

**The exterior meets the bar.** Both raters are at 8.5 or above in w22, neither found a high-severity issue in any round of this
wave, and A's only medium issue (the square raked tip, w20) is fixed. Every round gained 0.1 and none regressed (the w26K / w30K /
w11K differences between rounds are the lighting loop's cloud deck). Exterior triangles: 29,980 -> 30,004 (+19 % over the
wave-3 start of 25,160, cap +25 %).

### What changed (all in `src/11_exterior.js`, no shared files)
- **Raked tip.** The trailing edge used to run straight to STA 49.05 and end in a square 0.55 m tip chord. It now curves forward
  through six points into a ~0.20 m tip (KN41 / _7331 show a point). `WING.crest` lifts the last 1.3 m by up to 0.12 m so the outer
  LE sweeps up into the tip. Note: this departs from the ACAP tip station 49.11 quoted in the header (it reads as the tip TE);
  real photos win on geometry per the brief. Planform A 7.5 -> 7.8, B 7.5 -> 8.1.
- **Pylon fairing.** The dome front is rounded (`pow(smooth(1.65, 2.45), 0.6)`; it was a flat top with a chamfer), with a small dip
  after the crown and hB^2.0 for a shallow saddle. The flank shade is graded up from the foot, and a 3 cm dark crease runs at the
  foot. A 8.1 -> 8.3; A accepts the flat flank because _137 shows the same.
- **Smudges.** The head is lighter (#484b4f) and the body steps down in two tapers (0.76 / 0.83 / 0.92 of the panel; it used to jump
  from 0.65 to 0.90).
- **Fastener rows.** The strip is #4e5053, so the rows read 0.80-0.85 of the panel (KN41 0.80). w17's worry about stitching in
  the far views did not show up in w22.
- The w20 round also confirmed the wave-3d final fixes: the 2 cm hinge band no longer dashes (0.83-0.91 of the cowl).

### Left open (low, nothing worth +0.3 per either rater)
- **Tip upsweep.** It is still shorter than in KN41 (A: start the lift at s 29.5 and raise it to 0.20 m; B: 0.18 from s 30.8). A
  side-on 17-20A photo would settle it (question 13).
- **Pylon foot crease.** It reads 0.97 of the flank against 0.89 in _137 (B: `0.16 * (1 - smooth(0, 0.06, dr))`).
- **Saddle.** It barely shows in the silhouette (B: saddle factor 0.30 -> 0.38).
- **Unchanged scores.** Livery 7.7-8.0, lights 7.5-7.7 and nacelle colour / inlet 8.0 have not moved for several rounds.

The before/after sheet `exterior_before_after.jpg` shows the wave-3e start (r20) in row 1 and the w22 build in row 2. The views
are w19A, w13A, c_nacelle_left and w17A. Row 3 is a plan close-up of the tip, w21 against w22. It holds own renders only. Ratings
are in `exterior_w20*.json` to `exterior_w22*.json`.
