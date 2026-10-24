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
