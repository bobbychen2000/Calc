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
